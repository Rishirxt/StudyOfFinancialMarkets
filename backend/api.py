"""
FastAPI backend (Module 7) — exposes the existing core/ simulation engine
to the React frontend over REST. No simulation logic lives here; every
endpoint is a thin wrapper that builds a config, calls the existing
core/ module, and serializes the result to JSON.

Run with:  uvicorn backend.api:app --reload --port 8000
(run from the project root, i.e. the folder containing backend/ and core/)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.agent import AgentParams
from core.candles import trades_to_candles
from core.hysteresis import RampSchedule, run_hysteresis_experiment
from core.phase_diagram import run_phase_diagram_sweep, volatility_matrix
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig

app = FastAPI(title="Agent-Based Market Simulation API")

# Allow local frontend dev servers and keep direct cross-origin calls working
# if the frontend is pointed at the backend without the Vite proxy.
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
# Endpoints
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

