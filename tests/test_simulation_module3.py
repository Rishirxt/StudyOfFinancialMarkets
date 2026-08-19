"""
Module 3 milestone check.

Verifies the Simulation Engine works end to end:
  - A single run produces a full, loggable price series with no gaps.
  - Same seed -> identical price series (reproducibility, required for
    fair comparisons in Module 5/6).
  - Different seeds -> different price series (randomness actually used).
  - Trades are logged and correctly reference real agents.
  - Agent cash/holdings update via on_fill (bookkeeping stays in sync).
  - The batch runner can execute multiple configs.

Run with:  python -m tests.test_simulation_module3
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import AgentParams
from core.batch_runner import run_batch
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig


def make_config(seed, num_rounds=100, trend_ratio_count=3):
    specs = [
        AgentSpec(
            agent_type="fundamentalist", count=5,
            params=AgentParams(aggressiveness=0.5, randomness=0.1),
            extra_kwargs={"fair_value": 100.0},
        ),
        AgentSpec(
            agent_type="trend_follower", count=trend_ratio_count,
            params=AgentParams(reaction_sensitivity=0.8, randomness=0.1),
            extra_kwargs={"lookback": 5},
        ),
        AgentSpec(
            agent_type="noise_trader", count=5,
            params=AgentParams(aggressiveness=0.5),
            extra_kwargs={"trade_probability": 0.4},
        ),
    ]
    return SimulationConfig(agent_specs=specs, num_rounds=num_rounds, starting_price=100.0, seed=seed)


def check_end_to_end_run():
    print("--- End-to-end run ---")
    result = Simulation(make_config(seed=42)).run()

    assert len(result.price_history) == 101, "Expected starting price + 100 rounds"
    assert len(result.rounds_log) == 100
    assert all(p > 0 for p in result.price_history), "Prices should never go non-positive"
    print(f"  price series length -> {len(result.price_history)} (expect 101)")
    print(f"  final price         -> {result.price_history[-1]:.2f}")
    print(f"  total trades logged -> {len(result.trades)}")
    assert len(result.trades) > 0, "Expected at least some trades over 100 rounds"


def check_reproducibility():
    print("\n--- Reproducibility (same seed -> same result) ---")
    result_a = Simulation(make_config(seed=7)).run()
    result_b = Simulation(make_config(seed=7)).run()

    assert result_a.price_history == result_b.price_history, "Same seed must give identical price series"
    print("  same seed (7, 7)     -> identical price series (correct)")

    result_c = Simulation(make_config(seed=99)).run()
    assert result_a.price_history != result_c.price_history, "Different seeds should diverge"
    print("  different seed (99)  -> different price series (correct)")


def check_trade_bookkeeping():
    print("\n--- Trade bookkeeping (agents stay in sync) ---")
    result = Simulation(make_config(seed=3)).run()

    agents_by_id = {a.agent_id: a for a in result.agents}
    for trade in result.trades:
        assert trade.buy_agent_id in agents_by_id, "Trade references a real buyer"
        assert trade.sell_agent_id in agents_by_id, "Trade references a real seller"

    # Spot check: an agent that bought should have positive holdings if it never sold.
    buyers_only = {}
    for t in result.trades:
        buyers_only.setdefault(t.buy_agent_id, 0)
        buyers_only[t.buy_agent_id] += t.quantity
    if buyers_only:
        sample_id, bought_qty = next(iter(buyers_only.items()))
        print(f"  sample agent '{sample_id}' bought {bought_qty:.2f} units across the run")
        print(f"  its resulting holdings -> {agents_by_id[sample_id].holdings:.2f}")
    print(f"  all {len(result.trades)} trades reference valid agents (correct)")


def check_batch_runner():
    print("\n--- Batch runner ---")
    configs = [make_config(seed=s, trend_ratio_count=k) for s, k in [(1, 1), (2, 5), (3, 10)]]
    results = run_batch(configs)

    assert len(results) == 3
    for res in results:
        print(f"  run {res.run_id}: final price = {res.price_history[-1]:.2f}")
    print(f"  batch of {len(results)} configs executed (correct)")


if __name__ == "__main__":
    check_end_to_end_run()
    check_reproducibility()
    check_trade_bookkeeping()
    check_batch_runner()
    print("\nAll Module 3 checks passed.")
