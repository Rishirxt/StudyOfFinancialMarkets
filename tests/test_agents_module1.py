"""
Module 1 milestone check.

We don't have a real order book yet (that's Module 2), so this test just
feeds each agent type a fabricated MarketState and checks that decide()
produces sensible, explainable orders:

  - Fundamentalist: should buy when price < fair value, sell when above,
    and do nothing when price == fair value.
  - TrendFollower: should buy after an upward run, sell after a downward
    one, and do nothing with flat/insufficient history.
  - NoiseTrader: should sometimes trade, sometimes not, with random side.

Run with:  python -m tests.test_agents_module1
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import AgentParams
from core.market_state import MarketState
from core.order import Side
from agents.fundamentalist import Fundamentalist
from agents.trend_follower import TrendFollower
from agents.noise_trader import NoiseTrader


def check_fundamentalist():
    print("--- Fundamentalist ---")
    agent = Fundamentalist("fund_1", fair_value=100.0, params=AgentParams(aggressiveness=1.0))

    # Case 1: price below fair value -> should BUY
    market = MarketState(round_number=1, last_price=90.0)
    order = agent.decide(market)
    assert order is not None and order.side == Side.BUY, "Expected BUY when underpriced"
    print(f"  underpriced (90 vs fv 100)  -> {order}")

    # Case 2: price above fair value -> should SELL
    market = MarketState(round_number=2, last_price=110.0)
    order = agent.decide(market)
    assert order is not None and order.side == Side.SELL, "Expected SELL when overpriced"
    print(f"  overpriced (110 vs fv 100) -> {order}")

    # Case 3: price at fair value -> should do nothing
    market = MarketState(round_number=3, last_price=100.0)
    order = agent.decide(market)
    assert order is None, "Expected no trade at fair value"
    print(f"  at fair value (100)        -> None (correct)")


def check_trend_follower():
    print("--- TrendFollower ---")
    agent = TrendFollower("trend_1", lookback=3, params=AgentParams(reaction_sensitivity=1.0))

    # Not enough history yet
    market = MarketState(round_number=1, last_price=100.0, price_history=[100.0])
    order = agent.decide(market)
    assert order is None, "Expected no trade with insufficient history"
    print("  insufficient history       -> None (correct)")

    # Upward trend -> should BUY
    history = [100.0, 102.0, 104.0, 106.0]
    market = MarketState(round_number=4, last_price=106.0, price_history=history)
    order = agent.decide(market)
    assert order is not None and order.side == Side.BUY, "Expected BUY on upward trend"
    print(f"  upward trend {history}    -> {order}")

    # Downward trend -> should SELL
    history = [100.0, 98.0, 96.0, 94.0]
    market = MarketState(round_number=4, last_price=94.0, price_history=history)
    order = agent.decide(market)
    assert order is not None and order.side == Side.SELL, "Expected SELL on downward trend"
    print(f"  downward trend {history}  -> {order}")


def check_noise_trader():
    print("--- NoiseTrader ---")
    agent = NoiseTrader("noise_1", trade_probability=0.5)
    market = MarketState(round_number=1, last_price=100.0)

    trades = [agent.decide(market) for _ in range(200)]
    trade_count = sum(1 for t in trades if t is not None)
    buy_count = sum(1 for t in trades if t is not None and t.side == Side.BUY)
    sell_count = sum(1 for t in trades if t is not None and t.side == Side.SELL)

    print(f"  200 rounds -> traded {trade_count} times (~{trade_count/200:.0%}, expect ~50%)")
    print(f"  of those: {buy_count} buys, {sell_count} sells (expect roughly balanced)")
    assert 60 < trade_count < 140, "Trade frequency far off expected ~50%"
    assert buy_count > 0 and sell_count > 0, "Expected both sides to appear"


if __name__ == "__main__":
    check_fundamentalist()
    print()
    check_trend_follower()
    print()
    check_noise_trader()
    print("\nAll Module 1 checks passed.")
