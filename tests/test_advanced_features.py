"""Regression tests for interactive trading, herding, leverage, and halts."""

import json
import math
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agents.fundamentalist import Fundamentalist
from agents.human_trader import HumanTrader
from agents.leveraged_trader import LeveragedTrader, TraderStatus
from backend.api import app
from core.agent import Agent, AgentParams
from core.herding import StrategySwitchingAgent, StrategySwitchingConfig, StrategySwitchingController
from core.human_trading import HumanOrderError, HumanOrderManager
from core.market_state import MarketState
from core.order import Order, OrderType, Side
from core.order_book import OrderBook
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig
from core.circuit_breaker import CircuitBreaker


class PassiveAgent(Agent):
    def decide(self, market):
        return None


class HumanOrderTests(unittest.TestCase):
    def setUp(self):
        self.book = OrderBook()
        self.human = HumanTrader(params=AgentParams(initial_cash=1000, initial_holdings=3))
        self.seller = PassiveAgent("seller")
        self.buyer = PassiveAgent("buyer")
        self.agents = {a.agent_id: a for a in (self.human, self.seller, self.buyer)}
        self.manager = HumanOrderManager(self.human, self.book, self.agents)

    def test_market_buy_fill_and_portfolio_history(self):
        self.book.submit(Order("seller", Side.SELL, OrderType.LIMIT, 2, 100), 1)
        result = self.manager.submit("buy", "market", 2, None, 2)
        self.assertEqual(result["status"], "filled")
        self.assertEqual(self.human.holdings, 5)
        self.assertEqual(self.human.cash, 800)
        self.assertEqual(len(self.human.trade_history), 1)
        self.assertEqual(self.human.trade_history[0]["side"], "buy")

    def test_market_sell_fill_updates_portfolio(self):
        self.book.submit(Order("buyer", Side.BUY, OrderType.LIMIT, 2, 100), 1)
        result = self.manager.submit("sell", "market", 2, None, 2)
        self.assertEqual(result["status"], "filled")
        self.assertEqual(self.human.holdings, 1)
        self.assertEqual(self.human.cash, 1200)
        self.assertEqual(self.human.trade_history[0]["side"], "sell")

    def test_limit_buy_and_sell_rest_in_shared_book(self):
        buy = self.manager.submit("buy", "limit", 1, 90, 1)
        self.assertEqual(buy["status"], "accepted")
        self.assertEqual(self.book.best_bid(), 90)
        sell = self.manager.submit("sell", "limit", 1, 110, 1)
        self.assertEqual(sell["status"], "accepted")
        self.assertEqual(self.book.best_ask(), 110)

    def test_partial_fill_uses_price_time_priority(self):
        self.book.submit(Order("seller", Side.SELL, OrderType.LIMIT, 1, 100), 1)
        second = PassiveAgent("seller2")
        self.agents[second.agent_id] = second
        self.book.submit(Order("seller2", Side.SELL, OrderType.LIMIT, 1, 101), 1)
        result = self.manager.submit("buy", "market", 3, None, 2)
        self.assertEqual(result["status"], "partially_filled")
        self.assertEqual([f["price"] for f in result["fills"]], [100, 101])
        self.assertEqual(self.human.holdings, 5)
        self.assertAlmostEqual(self.human.cash, 799)

    def test_rejects_insufficient_cash_and_holdings(self):
        with self.assertRaises(HumanOrderError):
            self.manager.submit("buy", "limit", 11, 100, 1)
        with self.assertRaises(HumanOrderError):
            self.manager.submit("sell", "market", 4, None, 1)

    def test_rejects_invalid_quantity_and_limit_price(self):
        for quantity in (0, -1, float("nan")):
            with self.assertRaises(HumanOrderError):
                self.manager.submit("buy", "market", quantity, None, 1)
        for price in (None, 0, -2, float("inf")):
            with self.assertRaises(HumanOrderError):
                self.manager.submit("buy", "limit", 1, price, 1)

    def test_circuit_halt_rejects_order(self):
        with self.assertRaisesRegex(HumanOrderError, "halted"):
            self.manager.submit("buy", "market", 1, None, 1, halted=True)


class CircuitBreakerTests(unittest.TestCase):
    def test_threshold_and_exact_halt_duration(self):
        cb = CircuitBreaker(5, lookback_window=1, halt_duration=3)
        self.assertFalse(cb.check_and_update(1, [100, 104.99]))
        self.assertTrue(cb.check_and_update(2, [100, 106]))
        self.assertTrue(cb.check_and_update(3, [100, 106]))
        self.assertTrue(cb.check_and_update(4, [100, 106]))
        self.assertFalse(cb.check_and_update(5, [100, 106]))
        self.assertEqual(cb.state.halt_count, 1)
        self.assertEqual(cb.state.total_halted_rounds, 3)
        self.assertEqual(cb.state.halt_events[0]["round"], 2)
        self.assertEqual(cb.state.resume_events[0]["round"], 5)

    def test_invalid_configuration_rejected(self):
        for args in ((0, 1, 1), (5, 0, 1), (5, 1, 0)):
            with self.assertRaises(ValueError):
                CircuitBreaker(*args)


class HerdingTests(unittest.TestCase):
    def _config(self, seed):
        return SimulationConfig([
            AgentSpec("fundamentalist", 3, AgentParams(aggressiveness=0.5, randomness=0.15), {"fair_value": 100}),
            AgentSpec("trend_follower", 3, AgentParams(reaction_sensitivity=1.2, randomness=0.15), {"lookback": 5}),
            AgentSpec("noise_trader", 3, AgentParams(aggressiveness=0.6), {"trade_probability": 0.4}),
        ], num_rounds=50, seed=seed)

    def test_switching_deterministic_seed_and_metrics(self):
        cfg = StrategySwitchingConfig(lookback_rounds=5, temperature=0.001, max_switch_probability=0.6, cooldown_rounds=2)
        a = Simulation(self._config(9), strategy_switching=cfg).run()
        b = Simulation(self._config(9), strategy_switching=cfg).run()
        c = Simulation(self._config(10), strategy_switching=cfg).run()
        self.assertEqual(a.price_history, b.price_history)
        self.assertEqual(a.strategy_history, b.strategy_history)
        self.assertNotEqual(a.price_history, c.price_history)
        self.assertEqual(len(a.strategy_history), 50)
        self.assertTrue(any(agent.strategy_changes for agent in a.agents if isinstance(agent, StrategySwitchingAgent)))
        for item in a.strategy_history:
            self.assertEqual(item["fundamentalist"] + item["trend_follower"], 6)

    def test_probability_is_bounded_and_cooldown_applies(self):
        cfg = StrategySwitchingConfig(temperature=0.001, max_switch_probability=0.7, cooldown_rounds=3)
        self.assertLess(StrategySwitchingAgent._switch_probability(-1e10, cfg.temperature, cfg.max_switch_probability), 1e-20)
        self.assertAlmostEqual(StrategySwitchingAgent._switch_probability(1e10, cfg.temperature, cfg.max_switch_probability), 0.7)
        agent = StrategySwitchingAgent("a", "fundamentalist", AgentParams(), starting_price=100)
        controller = StrategySwitchingController([agent], StrategySwitchingConfig(max_switch_probability=1, cooldown_rounds=3))
        with patch.object(agent.rng, "random", return_value=0.1):
            first = controller.observe_close(1, 100)
            second = controller.observe_close(2, 100)
            third = controller.observe_close(3, 100)
            fourth = controller.observe_close(4, 100)
        self.assertEqual(first["switches_this_round"], 0)
        self.assertEqual(second["switches_this_round"], 0)
        self.assertEqual(third["switches_this_round"], 1)
        self.assertEqual(fourth["switches_this_round"], 0)


class LeverageLifecycleTests(unittest.TestCase):
    def test_margin_call_liquidation_recorded(self):
        trader = LeveragedTrader("lev", params=AgentParams(initial_cash=1000, initial_holdings=10), margin_call_threshold=0.3)
        trader.cash = -250
        trader.update_risk(4, 50)
        self.assertEqual(trader.status, TraderStatus.LIQUIDATING)
        order = trader.decide(MarketState(4, 50, [50]))
        self.assertEqual(order.side, Side.SELL)
        trader.on_fill(Side.SELL, 10, 50)
        self.assertEqual(trader.liquidation_quantity, 10)
        self.assertTrue(any(e["type"] == "liquidation_fill" for e in trader.events))

    def test_bankrupt_agent_only_submits_forced_closeout(self):
        trader = LeveragedTrader("lev", params=AgentParams(initial_cash=100, initial_holdings=2))
        trader.cash = -200
        book = OrderBook()
        book.submit(Order("lev", Side.BUY, OrderType.LIMIT, 1, 40), 1)
        trader.update_risk(7, 50, book)
        self.assertEqual(trader.status, TraderStatus.BANKRUPT)
        self.assertIsNone(book.best_bid())
        order = trader.decide(MarketState(8, 50, [50]))
        self.assertEqual(order.side, Side.SELL)
        trader.on_fill(Side.SELL, 2, 50)
        self.assertEqual(trader.status, TraderStatus.BANKRUPT)
        self.assertTrue(any(e["type"] == "bankruptcy" for e in trader.events))

    def test_leverage_cap_and_no_implicit_short_sales(self):
        trader = LeveragedTrader("lev", params=AgentParams(initial_cash=1000, reaction_sensitivity=100), leverage_ratio=2)
        market = MarketState(2, 100, [100, 110], best_ask=100)
        order = trader.decide(market)
        self.assertIsNotNone(order)
        self.assertLessEqual(order.quantity * 100, 2000 + 1e-8)
        no_position = LeveragedTrader("short", params=AgentParams(initial_cash=1000))
        falling = MarketState(2, 90, [100, 90])
        self.assertIsNone(no_position.decide(falling))


class APIAndWebSocketTests(unittest.TestCase):
    def test_websocket_rejects_malformed_initial_configuration(self):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/simulate-live") as ws:
                ws.send_text("not json")
                message = ws.receive_json()
                self.assertEqual(message["type"], "error")

    def test_rest_endpoints_validate_and_return_json(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/api/health").json(), {"status": "ok"})
            self.assertEqual(client.post("/api/simulate", json={"num_rounds": 0}).status_code, 422)
            common = {"fundamentalist_count": 0, "trend_follower_count": 0, "noise_count": 0, "num_rounds": 3, "seed": 4}
            live = client.post("/api/simulate-live", json=common)
            self.assertEqual(live.status_code, 200, live.text)
            self.assertEqual(len(live.json()["price_history"]), 4)
            wealth = client.post("/api/agent-wealth", json=common)
            self.assertEqual(wealth.status_code, 200, wealth.text)
            leverage = client.post("/api/simulate-leverage", json={**common, "leveraged_count": 0})
            self.assertEqual(leverage.status_code, 200, leverage.text)
            self.assertIsNone(leverage.json()["cascade_amplification"]["volatility_ratio"])
            circuit = client.post("/api/simulate-circuit-breaker", json={**common, "leveraged_count": 0})
            self.assertEqual(circuit.status_code, 200, circuit.text)
            self.assertIsNone(circuit.json()["regulatory_effect"]["volatility_reduction_pct"])
            self.assertEqual(circuit.json()["protected"]["circuit_breaker"]["total_halted_rounds"], 0)

    def test_order_sent_after_last_round_is_rejected(self):
        config = {
            "fundamentalist_count": 0, "trend_follower_count": 0, "noise_count": 0,
            "num_rounds": 1, "round_delay_ms": 100, "human_enabled": True,
        }
        with TestClient(app) as client:
            with client.websocket_connect("/ws/simulate-live") as ws:
                ws.send_json(config)
                self.assertEqual(ws.receive_json()["type"], "init")
                round_message = ws.receive_json()
                self.assertEqual(round_message["round"], 1)
                ws.send_json({"type": "human_order", "order": {
                    "side": "buy", "order_type": "market", "quantity": 1,
                }})
                done = ws.receive_json()
                self.assertEqual(done["type"], "done")
                self.assertEqual(done["human_order_results"][0]["status"], "rejected")
                self.assertIn("Session ended", done["human_order_results"][0]["error"])

    def test_herding_endpoint_json_metrics(self):
        with TestClient(app) as client:
            response = client.post("/api/herding-experiment", json={"num_rounds": 25, "seed": 3})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["experiment_config"]["num_rounds"], 25)
        self.assertEqual(body["experiment_config"]["seed"], 3)
        for mode in ("fixed", "switching"):
            self.assertIn("volatility", body[mode])
            self.assertIn("squared_return_autocorrelation", body[mode])
            self.assertTrue(all(math.isfinite(x) for x in body[mode]["raw_return_autocorrelation"]))

    def test_live_websocket_human_limit_uses_same_order_book(self):
        config = {
            "fundamentalist_count": 0, "trend_follower_count": 0, "noise_count": 0,
            "leveraged_count": 0, "num_rounds": 4, "round_delay_ms": 25,
            "circuit_breaker_enabled": True, "circuit_breaker_threshold_pct": 50,
            "circuit_breaker_lookback": 1, "circuit_breaker_halt_duration": 2,
            "human_enabled": True, "herding_enabled": False,
        }
        with TestClient(app) as client:
            with client.websocket_connect("/ws/simulate-live") as ws:
                ws.send_text(json.dumps(config))
                self.assertEqual(ws.receive_json()["type"], "init")
                ws.send_json({"type": "human_order", "order": {
                    "side": "buy", "order_type": "market", "quantity": 0,
                }})
                ws.send_json({"type": "human_order", "order": {
                    "side": "buy", "order_type": "limit", "quantity": 1, "price": 90,
                }})
                found_order = False
                found_rejection = False
                while True:
                    message = ws.receive_json()
                    if message["type"] == "error":
                        self.fail(f"websocket returned an error: {message}")
                    if message["type"] == "round":
                        found_order |= any(result.get("status") == "accepted" for result in message.get("human_order_results", []))
                        found_rejection |= any(result.get("status") == "rejected" for result in message.get("human_order_results", []))
                        found_order |= any(level["price"] == 90 for level in message["order_book"]["bids"])
                    if message["type"] == "done":
                        break
                self.assertTrue(found_order)
                self.assertTrue(found_rejection)

    def test_live_combined_session_executes_human_buy_and_sell(self):
        config = {
            "fundamentalist_count": 4, "trend_follower_count": 2, "noise_count": 8,
            "leveraged_count": 1, "num_rounds": 100, "round_delay_ms": 5,
            "circuit_breaker_enabled": True, "circuit_breaker_threshold_pct": 50,
            "circuit_breaker_lookback": 3, "circuit_breaker_halt_duration": 2,
            "human_enabled": True, "herding_enabled": True, "seed": 27,
        }
        observed_trade_sides = set()
        sell_sent = False
        with TestClient(app) as client:
            with client.websocket_connect("/ws/simulate-live") as ws:
                ws.send_json(config)
                self.assertEqual(ws.receive_json()["type"], "init")
                ws.send_json({"type": "human_order", "order": {
                    "side": "buy", "order_type": "market", "quantity": 0.5,
                }})
                while True:
                    message = ws.receive_json()
                    if message["type"] == "error":
                        self.fail(message["message"])
                    if message["type"] in ("round", "halt"):
                        observed_trade_sides.update(trade["side"] for trade in message.get("human_trade_updates", []))
                        portfolio = message.get("human_portfolio") or {}
                        holdings = portfolio.get("holdings", 0)
                        if holdings > 0 and not sell_sent:
                            ws.send_json({"type": "human_order", "order": {
                                "side": "sell", "order_type": "market", "quantity": holdings,
                            }})
                            sell_sent = True
                        elif holdings == 0 and not observed_trade_sides and message["round"] % 4 == 0:
                            ws.send_json({"type": "human_order", "order": {
                                "side": "buy", "order_type": "market", "quantity": 0.5,
                            }})
                        elif holdings > 0 and sell_sent and "sell" not in observed_trade_sides:
                            ws.send_json({"type": "human_order", "order": {
                                "side": "sell", "order_type": "market", "quantity": holdings,
                            }})
                    if message["type"] == "done":
                        break
        self.assertIn("buy", observed_trade_sides)
        self.assertIn("sell", observed_trade_sides)

    def test_live_circuit_breaker_halt_has_no_trades_or_price_drift(self):
        config = {
            "fundamentalist_count": 0, "trend_follower_count": 0, "noise_count": 6,
            "num_rounds": 40, "round_delay_ms": 0, "seed": 11,
            "circuit_breaker_enabled": True, "circuit_breaker_threshold_pct": 0.01,
            "circuit_breaker_lookback": 1, "circuit_breaker_halt_duration": 2,
        }
        saw_halt = False
        saw_resume = False
        last_price = 100.0
        with TestClient(app) as client:
            with client.websocket_connect("/ws/simulate-live") as ws:
                ws.send_json(config)
                self.assertEqual(ws.receive_json()["type"], "init")
                while True:
                    message = ws.receive_json()
                    if message["type"] == "error":
                        self.fail(message["message"])
                    if message["type"] == "halt":
                        saw_halt = True
                        self.assertEqual(message["num_trades"], 0)
                        self.assertAlmostEqual(message["price"], last_price)
                    if message["type"] == "round" and message.get("circuit_breaker", {}).get("resume_events"):
                        saw_resume = True
                    if message["type"] in ("round", "halt"):
                        last_price = message["price"]
                    if message["type"] == "done":
                        break
        self.assertTrue(saw_halt)
        self.assertTrue(saw_resume)


if __name__ == "__main__":
    unittest.main()
