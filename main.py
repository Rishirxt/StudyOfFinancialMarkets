"""
main.py — end-to-end demo using the real Simulation engine (Module 3),
which wires Module 1's agents together with Module 2's real limit order
book. This replaces the earlier naive_clear() placeholder entirely.

Run with:  python main.py
"""

from core.agent import AgentParams
from core.candles import trades_to_candles
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig


def build_default_config(seed: int = 42) -> SimulationConfig:
    """A small, mixed population — same mix used in the Module 3 tests."""
    agent_specs = [
        AgentSpec(
            agent_type="fundamentalist", count=5,
            params=AgentParams(aggressiveness=0.5, randomness=0.1),
            extra_kwargs={"fair_value": 100.0},
        ),
        AgentSpec(
            agent_type="trend_follower", count=3,
            params=AgentParams(reaction_sensitivity=0.8, randomness=0.1),
            extra_kwargs={"lookback": 5},
        ),
        AgentSpec(
            agent_type="noise_trader", count=5,
            params=AgentParams(aggressiveness=0.5),
            extra_kwargs={"trade_probability": 0.4},
        ),
    ]
    return SimulationConfig(
        agent_specs=agent_specs,
        num_rounds=200,
        starting_price=100.0,
        seed=seed,
    )


def run_demo():
    config = build_default_config()
    print(f"Running simulation '{config.run_id}' — "
          f"{sum(s.count for s in config.agent_specs)} agents, {config.num_rounds} rounds...\n")

    result = Simulation(config).run()

    for r in result.rounds_log:
        if r.round_number % 20 == 0 or r.round_number == 1:
            print(f"round {r.round_number:>3}: price = {r.price:>8.2f}  "
                  f"spread = {str(r.spread):>6}  trades = {r.num_trades}")

    print(f"\nFinal price: {result.price_history[-1]:.2f}")
    print(f"Price range: {min(result.price_history):.2f} - {max(result.price_history):.2f}")
    print(f"Total trades: {len(result.trades)}")

    candles = trades_to_candles(result.trades, window_size=10, last_known_price=config.starting_price)
    print(f"\nGenerated {len(candles)} candles (window=10 rounds):")
    for c in candles[:5]:
        print(f"  {c}")
    if len(candles) > 5:
        print(f"  ... ({len(candles) - 5} more)")

    return result


if __name__ == "__main__":
    run_demo()
