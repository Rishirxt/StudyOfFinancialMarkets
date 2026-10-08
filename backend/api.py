"""
FastAPI backend (Module 7) — exposes the existing core/ simulation engine
to the React frontend over REST and WebSocket. No simulation logic lives here;
every endpoint is a thin wrapper that builds a config, calls the existing
core/ module, and serializes the result to JSON.

New in this version:
  - WebSocket /ws/simulate-live — streams simulation round-by-round so the
    frontend can animate the market in real time
  - /api/simulate-leverage — runs the leverage/margin-call experiment
  - /api/simulate-circuit-breaker — runs the circuit breaker experiment
  - /api/agent-wealth — returns per-agent wealth trajectories

Run with:  uvicorn backend.api:app --reload --port 8000
(run from the project root, i.e. the folder containing backend/ and core/)
"""

import asyncio
import json
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import numpy as np

from agents.leveraged_trader import LeveragedTrader
from core.agent import AgentParams
from core.agent_factory import build_population
from core.candles import trades_to_candles
from core.circuit_breaker import CircuitBreaker
from core.hysteresis import RampSchedule, run_hysteresis_experiment
from core.market_state import MarketState
from core.order import Side
from core.order_book import OrderBook
from core.phase_diagram import run_phase_diagram_sweep, volatility_matrix
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig

app = FastAPI(title="Agent-Based Market Simulation API")

# Allow local frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------

class SimulateRequest(BaseModel):
    fundamentalist_count: int = 8
    trend_follower_count: int = 6
    noise_count: int = 8
    reaction_sensitivity: float = 1.2
    num_rounds: int = 300
    candle_window: int = 10
    seed: int = 42


class LiveSimulateRequest(BaseModel):
    fundamentalist_count: int = 8
    trend_follower_count: int = 6
    noise_count: int = 8
    leveraged_count: int = 0
    reaction_sensitivity: float = 1.2
    num_rounds: int = 200
    candle_window: int = 5
    seed: int = 42
    round_delay_ms: int = 250  # ms to wait between rounds for animation (slower, realistic pacing)
    # Circuit breaker params (set enabled=True to activate)
    circuit_breaker_enabled: bool = False
    circuit_breaker_threshold_pct: float = 5.0
    circuit_breaker_lookback: int = 5
    circuit_breaker_halt_duration: int = 3
    # Leverage params
    leverage_ratio: float = 3.0
    margin_call_threshold: float = 0.3


class LeverageExperimentRequest(BaseModel):
    fundamentalist_count: int = 8
    trend_follower_count: int = 6
    noise_count: int = 8
    leveraged_count: int = 4
    leverage_ratio: float = 3.0
    margin_call_threshold: float = 0.3
    reaction_sensitivity: float = 1.2
    num_rounds: int = 250
    seed: int = 42


class CircuitBreakerExperimentRequest(BaseModel):
    fundamentalist_count: int = 8
    trend_follower_count: int = 6
    noise_count: int = 8
    leveraged_count: int = 4
    reaction_sensitivity: float = 1.5
    num_rounds: int = 250
    threshold_pct: float = 4.0
    lookback: int = 5
    halt_duration: int = 3
    seed: int = 42


class PhaseDiagramRequest(BaseModel):
    trend_follower_counts: list[int] = Field(default=[0, 4, 8, 12])
    reaction_sensitivities: list[float] = Field(default=[0.2, 1.0, 2.0, 3.0])
    seeds: list[int] = Field(default=[1, 2, 3])
    num_rounds: int = 250


class HysteresisRequest(BaseModel):
    baseline_value: float = 0.3
    peak_value: float = 3.0
    hold_before: int = 150
    ramp_up_rounds: int = 150
    hold_at_peak: int = 100
    ramp_down_rounds: int = 150
    hold_after: int = 150
    seed: int = 1


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def build_agent_specs(req: LiveSimulateRequest) -> list[AgentSpec]:
    specs = [
        AgentSpec(
            agent_type="fundamentalist",
            count=req.fundamentalist_count,
            params=AgentParams(aggressiveness=0.5, randomness=0.15),
            extra_kwargs={"fair_value": 100.0},
        ),
        AgentSpec(
            agent_type="trend_follower",
            count=req.trend_follower_count,
            params=AgentParams(reaction_sensitivity=req.reaction_sensitivity, randomness=0.15),
            extra_kwargs={"lookback": 5},
        ),
        AgentSpec(
            agent_type="noise_trader",
            count=req.noise_count,
            params=AgentParams(aggressiveness=0.6),
            extra_kwargs={"trade_probability": 0.4},
        ),
    ]
    if req.leveraged_count > 0:
        specs.append(AgentSpec(
            agent_type="leveraged_trader",
            count=req.leveraged_count,
            params=AgentParams(
                initial_cash=10_000.0,
                reaction_sensitivity=req.reaction_sensitivity,
                randomness=0.15,
            ),
            extra_kwargs={
                "lookback": 5,
                "leverage_ratio": req.leverage_ratio,
                "margin_call_threshold": req.margin_call_threshold,
            },
        ))
    return specs


def agent_type_label(agent_id: str) -> str:
    if agent_id.startswith("fundamentalist"):
        return "fundamentalist"
    if agent_id.startswith("trend_follower"):
        return "trend_follower"
    if agent_id.startswith("leveraged_trader"):
        return "leveraged_trader"
    return "noise_trader"


# ---------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    specs = [
        AgentSpec(
            agent_type="fundamentalist", count=req.fundamentalist_count,
            params=AgentParams(aggressiveness=0.5, randomness=0.15),
            extra_kwargs={"fair_value": 100.0},
        ),
        AgentSpec(
            agent_type="trend_follower", count=req.trend_follower_count,
            params=AgentParams(reaction_sensitivity=req.reaction_sensitivity, randomness=0.15),
            extra_kwargs={"lookback": 5},
        ),
        AgentSpec(
            agent_type="noise_trader", count=req.noise_count,
            params=AgentParams(aggressiveness=0.6),
            extra_kwargs={"trade_probability": 0.4},
        ),
    ]
    config = SimulationConfig(
        agent_specs=specs, num_rounds=req.num_rounds, starting_price=100.0, seed=req.seed,
    )
    result = Simulation(config).run()
    candles = trades_to_candles(result.trades, window_size=req.candle_window, last_known_price=config.starting_price)

    return {
        "run_id": result.run_id,
        "price_history": result.price_history,
        "candles": [
            {
                "window_start": c.window_start_round,
                "window_end": c.window_end_round,
                "open": c.open, "high": c.high, "low": c.low, "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ],
        "total_trades": len(result.trades),
        "final_price": result.price_history[-1],
        "order_book_snapshot": result.order_book.snapshot() if result.order_book else None,
    }


@app.post("/api/phase-diagram")
def phase_diagram(req: PhaseDiagramRequest):
    results = run_phase_diagram_sweep(
        req.trend_follower_counts, req.reaction_sensitivities, req.seeds, req.num_rounds,
    )
    matrix = volatility_matrix(results, req.trend_follower_counts, req.reaction_sensitivities)
    return {
        "trend_follower_counts": req.trend_follower_counts,
        "reaction_sensitivities": req.reaction_sensitivities,
        "volatility_matrix": matrix.tolist(),
    }


@app.post("/api/hysteresis")
def hysteresis(req: HysteresisRequest):
    schedule = RampSchedule(
        baseline_value=req.baseline_value,
        peak_value=req.peak_value,
        hold_before=req.hold_before,
        ramp_up_rounds=req.ramp_up_rounds,
        hold_at_peak=req.hold_at_peak,
        ramp_down_rounds=req.ramp_down_rounds,
        hold_after=req.hold_after,
    )
    result = run_hysteresis_experiment(schedule, seed=req.seed)
    return {
        "price_history": result.price_history,
        "applied_sensitivity": result.applied_sensitivity,
        "pre_window": schedule.window_pre_baseline(),
        "post_window": schedule.window_post_baseline(),
        "pre_mean_price": result.pre_mean_price,
        "post_mean_price": result.post_mean_price,
        "price_shift_pct": result.price_shift_pct,
        "pre_volatility": result.pre_volatility,
        "post_volatility": result.post_volatility,
        "volatility_ratio": result.volatility_ratio,
    }


# ---------------------------------------------------------------------
# Live & Experiment REST endpoints
# ---------------------------------------------------------------------

def compute_metrics(prices: list[float]) -> dict:
    if not prices:
        val = 100.0
        return {
            "volatility": 0.0,
            "max_drawdown_pct": 0.0,
            "min_price": round(val, 2),
            "max_price": round(val, 2),
            "final_price": round(val, 2),
        }
    arr = np.asarray(prices, dtype=float)
    if not np.all(np.isfinite(arr)) or np.any(arr <= 0):
        raise ValueError("Prices must be finite and strictly positive")
    if len(arr) < 2:
        val = arr[0]
        return {
            "volatility": 0.0,
            "max_drawdown_pct": 0.0,
            "min_price": round(val, 2),
            "max_price": round(val, 2),
            "final_price": round(val, 2),
        }
    # Use log returns consistently with validation, phase-diagram, and
    # hysteresis experiments. Keep full precision for ratios downstream.
    returns = np.diff(np.log(arr))
    vol = float(np.std(returns)) if len(returns) > 0 else 0.0

    cummax = np.maximum.accumulate(arr)
    drawdowns = (arr - cummax) / np.maximum(cummax, 1e-6)
    max_dd = float(abs(np.min(drawdowns))) * 100.0

    return {
        "volatility": vol,
        "max_drawdown_pct": round(max_dd, 2),
        "min_price": round(float(np.min(arr)), 2),
        "max_price": round(float(np.max(arr)), 2),
        "final_price": round(float(arr[-1]), 2),
    }


def run_live_simulation_sync(req: LiveSimulateRequest) -> dict:
    specs = build_agent_specs(req)
    config = SimulationConfig(
        agent_specs=specs,
        num_rounds=req.num_rounds,
        starting_price=100.0,
        seed=req.seed,
    )

    random.seed(config.seed)
    order_book = OrderBook()
    agents = build_population(config.agent_specs)
    agents_by_id = {a.agent_id: a for a in agents}

    cb = None
    if req.circuit_breaker_enabled:
        cb = CircuitBreaker(
            price_move_threshold_pct=req.circuit_breaker_threshold_pct,
            lookback_window=req.circuit_breaker_lookback,
            halt_duration=req.circuit_breaker_halt_duration,
        )

    price_history = [config.starting_price]
    trades_log = []
    candle_buffer = []
    current_candle_start = 1
    candles = []
    margin_calls_log = []
    wealth_samples = []

    for r in range(1, config.num_rounds + 1):
        halted = False
        if cb is not None:
            halted = cb.check_and_update(r, price_history)

        market = MarketState(
            round_number=r,
            last_price=price_history[-1],
            price_history=price_history[:],
            best_bid=order_book.best_bid(),
            best_ask=order_book.best_ask(),
        )

        orders_this_round = 0
        trades_this_round = []

        if not halted:
            shuffled_agents = agents[:]
            random.shuffle(shuffled_agents)

            for agent in shuffled_agents:
                order = agent.decide(market)
                if order is None:
                    continue
                order.round_submitted = r
                orders_this_round += 1

                fills = order_book.submit(order, r)
                for trade in fills:
                    buyer = agents_by_id[trade.buy_agent_id]
                    seller = agents_by_id[trade.sell_agent_id]
                    buyer.on_fill(Side.BUY, trade.quantity, trade.price)
                    seller.on_fill(Side.SELL, trade.quantity, trade.price)
                    trades_this_round.append(trade)

                if isinstance(agent, LeveragedTrader) and agent.in_margin_call:
                    margin_calls_log.append({
                        "round": r,
                        "agent_id": agent.agent_id,
                        "cash": round(agent.cash, 2),
                        "holdings": round(agent.holdings, 4),
                        "price": round(market.last_price, 2),
                    })

            trades_log.extend(trades_this_round)
            candle_buffer.extend(trades_this_round)

        if trades_this_round:
            new_price = trades_this_round[-1].price
        else:
            mid = order_book.mid_price()
            new_price = mid if mid is not None else price_history[-1]

        price_history.append(new_price)

        if r - current_candle_start + 1 >= req.candle_window or r == config.num_rounds:
            if candle_buffer:
                prices = [t.price for t in candle_buffer]
                candles.append({
                    "window_start": current_candle_start,
                    "window_end": r,
                    "open": candle_buffer[0].price,
                    "high": max(prices),
                    "low": min(prices),
                    "close": candle_buffer[-1].price,
                    "volume": sum(t.quantity for t in candle_buffer),
                })
            else:
                candles.append({
                    "window_start": current_candle_start,
                    "window_end": r,
                    "open": new_price,
                    "high": new_price,
                    "low": new_price,
                    "close": new_price,
                    "volume": 0,
                })
            candle_buffer = []
            current_candle_start = r + 1

        if r % 5 == 0 or r == config.num_rounds:
            by_type = {}
            for a in agents:
                t = agent_type_label(a.agent_id)
                by_type.setdefault(t, []).append(a.portfolio_value(new_price))
            wealth_samples.append({
                "round": r,
                "averages": {t: round(float(np.mean(vals)), 2) for t, vals in by_type.items()},
            })

    final_wealth = [
        {
            "id": a.agent_id,
            "type": agent_type_label(a.agent_id),
            "cash": round(a.cash, 2),
            "holdings": round(a.holdings, 4),
            "portfolio_value": round(a.portfolio_value(price_history[-1]), 2),
            "in_margin_call": getattr(a, "in_margin_call", False),
        }
        for a in agents
    ]

    metrics = compute_metrics(price_history)

    return {
        "price_history": price_history,
        "candles": candles,
        "total_trades": len(trades_log),
        "final_price": round(price_history[-1], 4),
        "order_book_snapshot": order_book.snapshot(),
        "agent_wealth": final_wealth,
        "wealth_samples": wealth_samples,
        "margin_calls": margin_calls_log,
        "margin_call_count": len(margin_calls_log),
        "metrics": metrics,
        "circuit_breaker": {
            "halt_count": cb.state.halt_count if cb else 0,
            "halt_events": cb.state.halt_events if cb else [],
        } if cb else None,
    }


@app.post("/api/simulate-live")
def simulate_live_post(req: LiveSimulateRequest):
    return run_live_simulation_sync(req)


@app.post("/api/simulate-leverage")
def simulate_leverage_post(req: LeverageExperimentRequest):
    base_req = LiveSimulateRequest(
        fundamentalist_count=req.fundamentalist_count,
        trend_follower_count=req.trend_follower_count + req.leveraged_count,
        noise_count=req.noise_count,
        leveraged_count=0,
        reaction_sensitivity=req.reaction_sensitivity,
        num_rounds=req.num_rounds,
        seed=req.seed,
    )
    base_res = run_live_simulation_sync(base_req)

    lev_req = LiveSimulateRequest(
        fundamentalist_count=req.fundamentalist_count,
        trend_follower_count=req.trend_follower_count,
        noise_count=req.noise_count,
        leveraged_count=req.leveraged_count,
        leverage_ratio=req.leverage_ratio,
        margin_call_threshold=req.margin_call_threshold,
        reaction_sensitivity=req.reaction_sensitivity,
        num_rounds=req.num_rounds,
        seed=req.seed,
    )
    lev_res = run_live_simulation_sync(lev_req)

    return {
        "baseline": {
            "price_history": base_res["price_history"],
            "metrics": base_res["metrics"],
            "candles": base_res["candles"],
        },
        "leveraged": {
            "price_history": lev_res["price_history"],
            "metrics": lev_res["metrics"],
            "candles": lev_res["candles"],
            "margin_calls": lev_res["margin_calls"],
            "margin_call_count": lev_res["margin_call_count"],
        },
        "cascade_amplification": {
            "volatility_ratio": round(lev_res["metrics"]["volatility"] / max(base_res["metrics"]["volatility"], 1e-6), 3),
            "drawdown_ratio": round(lev_res["metrics"]["max_drawdown_pct"] / max(base_res["metrics"]["max_drawdown_pct"], 1e-6), 3),
            "margin_calls_triggered": lev_res["margin_call_count"],
        },
    }


@app.post("/api/simulate-circuit-breaker")
def simulate_circuit_breaker_post(req: CircuitBreakerExperimentRequest):
    unprot_req = LiveSimulateRequest(
        fundamentalist_count=req.fundamentalist_count,
        trend_follower_count=req.trend_follower_count,
        noise_count=req.noise_count,
        leveraged_count=req.leveraged_count,
        reaction_sensitivity=req.reaction_sensitivity,
        num_rounds=req.num_rounds,
        seed=req.seed,
        circuit_breaker_enabled=False,
    )
    unprot_res = run_live_simulation_sync(unprot_req)

    prot_req = LiveSimulateRequest(
        fundamentalist_count=req.fundamentalist_count,
        trend_follower_count=req.trend_follower_count,
        noise_count=req.noise_count,
        leveraged_count=req.leveraged_count,
        reaction_sensitivity=req.reaction_sensitivity,
        num_rounds=req.num_rounds,
        seed=req.seed,
        circuit_breaker_enabled=True,
        circuit_breaker_threshold_pct=req.threshold_pct,
        circuit_breaker_lookback=req.lookback,
        circuit_breaker_halt_duration=req.halt_duration,
    )
    prot_res = run_live_simulation_sync(prot_req)

    return {
        "unprotected": {
            "price_history": unprot_res["price_history"],
            "metrics": unprot_res["metrics"],
            "candles": unprot_res["candles"],
        },
        "protected": {
            "price_history": prot_res["price_history"],
            "metrics": prot_res["metrics"],
            "candles": prot_res["candles"],
            "circuit_breaker": prot_res["circuit_breaker"],
        },
        "regulatory_effect": {
            "volatility_reduction_pct": round(
                ((unprot_res["metrics"]["volatility"] - prot_res["metrics"]["volatility"]) /
                 max(unprot_res["metrics"]["volatility"], 1e-6)) * 100, 2
            ),
            "drawdown_reduction_pct": round(
                ((unprot_res["metrics"]["max_drawdown_pct"] - prot_res["metrics"]["max_drawdown_pct"]) /
                 max(unprot_res["metrics"]["max_drawdown_pct"], 1e-6)) * 100, 2
            ),
            "total_halts": prot_res["circuit_breaker"]["halt_count"] if prot_res["circuit_breaker"] else 0,
        },
    }


@app.post("/api/agent-wealth")
def agent_wealth_post(req: LiveSimulateRequest):
    res = run_live_simulation_sync(req)
    return {
        "wealth_samples": res["wealth_samples"],
        "final_wealth": res["agent_wealth"],
        "price_history": res["price_history"],
    }


# ---------------------------------------------------------------------
# WebSocket — live simulation streaming
# ---------------------------------------------------------------------

@app.websocket("/ws/simulate-live")
async def simulate_live(websocket: WebSocket):
    """
    Streams the simulation round-by-round over WebSocket so the frontend
    can animate a live market. Each message is a JSON object with:
      - type: "round" | "candle" | "halt" | "margin_call" | "done" | "error"
      - round: int
      - price: float
      - best_bid: float | null
      - best_ask: float | null
      - spread: float | null
      - num_trades: int
      - order_book: {bids: [...], asks: [...]}
      - agent_wealth: [{id, type, cash, holdings, portfolio_value, in_margin_call}]
      - candle: candlestick data when a new candle closes (type="candle")
      - circuit_breaker: {triggered, halt_count} if circuit breaker is active
    """
    await websocket.accept()

    try:
        # Receive configuration from the client
        raw = await websocket.receive_text()
        req_data = json.loads(raw)
        req = LiveSimulateRequest(**req_data)

        specs = build_agent_specs(req)
        config = SimulationConfig(
            agent_specs=specs,
            num_rounds=req.num_rounds,
            starting_price=100.0,
            seed=req.seed,
        )

        random.seed(config.seed)
        order_book = OrderBook()
        agents = build_population(config.agent_specs)
        agents_by_id = {a.agent_id: a for a in agents}

        # Set up circuit breaker if enabled
        cb = None
        if req.circuit_breaker_enabled:
            cb = CircuitBreaker(
                price_move_threshold_pct=req.circuit_breaker_threshold_pct,
                lookback_window=req.circuit_breaker_lookback,
                halt_duration=req.circuit_breaker_halt_duration,
            )

        price_history = [config.starting_price]
        trades_log = []
        candle_buffer = []  # trades since last candle close
        current_candle_start = 1
        candle_window = req.candle_window

        # Send initial state
        await websocket.send_json({
            "type": "init",
            "num_rounds": req.num_rounds,
            "starting_price": config.starting_price,
            "agent_counts": {
                "fundamentalist": req.fundamentalist_count,
                "trend_follower": req.trend_follower_count,
                "noise_trader": req.noise_count,
                "leveraged_trader": req.leveraged_count,
            },
            "circuit_breaker_enabled": req.circuit_breaker_enabled,
        })

        for r in range(1, config.num_rounds + 1):
            # Check circuit breaker
            halted = False
            if cb is not None:
                halted = cb.check_and_update(r, price_history)

            market = MarketState(
                round_number=r,
                last_price=price_history[-1],
                price_history=price_history[:],
                best_bid=order_book.best_bid(),
                best_ask=order_book.best_ask(),
            )

            orders_this_round = 0
            trades_this_round = []
            margin_call_agents = []

            if not halted:
                shuffled_agents = agents[:]
                random.shuffle(shuffled_agents)

                for agent in shuffled_agents:
                    order = agent.decide(market)
                    if order is None:
                        continue
                    order.round_submitted = r
                    orders_this_round += 1

                    fills = order_book.submit(order, r)
                    for trade in fills:
                        buyer = agents_by_id[trade.buy_agent_id]
                        seller = agents_by_id[trade.sell_agent_id]
                        buyer.on_fill(Side.BUY, trade.quantity, trade.price)
                        seller.on_fill(Side.SELL, trade.quantity, trade.price)
                        trades_this_round.append(trade)

                    # Track margin-called leveraged traders
                    from agents.leveraged_trader import LeveragedTrader
                    if isinstance(agent, LeveragedTrader) and agent.in_margin_call:
                        margin_call_agents.append(agent.agent_id)

                trades_log.extend(trades_this_round)
                candle_buffer.extend(trades_this_round)

            if trades_this_round:
                new_price = trades_this_round[-1].price
            else:
                mid = order_book.mid_price()
                new_price = mid if mid is not None else price_history[-1]

            price_history.append(new_price)

            # Build agent wealth snapshot
            agent_wealth = [
                {
                    "id": a.agent_id,
                    "type": agent_type_label(a.agent_id),
                    "cash": round(a.cash, 2),
                    "holdings": round(a.holdings, 4),
                    "portfolio_value": round(a.portfolio_value(new_price), 2),
                    "in_margin_call": getattr(a, "in_margin_call", False),
                }
                for a in agents
            ]

            # Check if we close a candle
            new_candle = None
            if r - current_candle_start + 1 >= candle_window or r == config.num_rounds:
                if candle_buffer:
                    prices = [t.price for t in candle_buffer]
                    new_candle = {
                        "window_start": current_candle_start,
                        "window_end": r,
                        "open": candle_buffer[0].price,
                        "high": max(prices),
                        "low": min(prices),
                        "close": candle_buffer[-1].price,
                        "volume": sum(t.quantity for t in candle_buffer),
                    }
                else:
                    # Quiet window — flat candle at last price
                    new_candle = {
                        "window_start": current_candle_start,
                        "window_end": r,
                        "open": new_price,
                        "high": new_price,
                        "low": new_price,
                        "close": new_price,
                        "volume": 0,
                    }
                candle_buffer = []
                current_candle_start = r + 1

            ob_snap = order_book.snapshot(levels=8)

            msg = {
                "type": "halt" if halted else "round",
                "round": r,
                "price": round(new_price, 4),
                "best_bid": ob_snap.get("bids", [{}])[0].get("price") if ob_snap.get("bids") else None,
                "best_ask": ob_snap.get("asks", [{}])[0].get("price") if ob_snap.get("asks") else None,
                "spread": ob_snap.get("spread"),
                "num_orders": orders_this_round,
                "num_trades": len(trades_this_round),
                "order_book": ob_snap,
                "agent_wealth": agent_wealth,
                "candle": new_candle,
                "margin_call_agents": margin_call_agents,
            }

            if cb is not None:
                msg["circuit_breaker"] = {
                    "is_halted": cb.state.is_halted,
                    "halt_remaining": cb.state.halt_remaining,
                    "halt_count": cb.state.halt_count,
                    "halt_events": cb.state.halt_events[-5:],  # last 5 events
                }

            await websocket.send_json(msg)

            # Pace the simulation for animation
            if req.round_delay_ms > 0:
                await asyncio.sleep(req.round_delay_ms / 1000.0)

        # Final summary
        final_snapshot = order_book.snapshot()
        await websocket.send_json({
            "type": "done",
            "total_rounds": config.num_rounds,
            "final_price": round(price_history[-1], 4),
            "total_trades": len(trades_log),
            "order_book": final_snapshot,
            "circuit_breaker_summary": {
                "halt_count": cb.state.halt_count if cb else 0,
                "halt_events": cb.state.halt_events if cb else [],
            },
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
