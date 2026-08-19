"""
Phase diagram experiment (Module 5).

Sweeps two key parameters — trend-follower count and reaction_sensitivity
— across a grid, runs the simulation at each grid point, and computes a
quantitative instability score. Aggregating these into a 2D matrix gives
the phase diagram: a heatmap showing the boundary between stable and
unstable market regimes.

This is the direct foundation for Module 6 (hysteresis): once we know
roughly where the instability boundary sits, Module 6 will deliberately
cross it and reverse the parameter to test for path-dependence.

Instability metric: primarily return volatility (std of log returns),
with excess kurtosis as a secondary signal (a market that has gone
unstable typically has both higher volatility AND fatter tails than a
calm one). Multiple seeds per grid point are averaged, since a single
run can be noisy — the phase diagram should reflect a genuine regime
property of the parameter combination, not one lucky/unlucky seed.
"""

from dataclasses import dataclass

import numpy as np

from core.agent import AgentParams
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig
from core.validation import excess_kurtosis, returns_from_prices


@dataclass
class GridPointResult:
    trend_follower_count: int
    reaction_sensitivity: float
    mean_volatility: float
    mean_excess_kurtosis: float
    seeds_used: list


def build_config(
    trend_follower_count: int,
    reaction_sensitivity: float,
    seed: int,
    num_rounds: int = 300,
    fundamentalist_count: int = 8,
    noise_count: int = 8,
) -> SimulationConfig:
    """
    Same population structure used in Module 4, but with trend-follower
    count and reaction_sensitivity exposed as the two axes to sweep —
    these are the dials that push the market toward instability.
    """
    specs = [
        AgentSpec(
            agent_type="fundamentalist", count=fundamentalist_count,
            params=AgentParams(aggressiveness=0.5, randomness=0.15),
            extra_kwargs={"fair_value": 100.0},
        ),
        AgentSpec(
            agent_type="trend_follower", count=trend_follower_count,
            params=AgentParams(reaction_sensitivity=reaction_sensitivity, randomness=0.15),
            extra_kwargs={"lookback": 5},
        ),
        AgentSpec(
            agent_type="noise_trader", count=noise_count,
            params=AgentParams(aggressiveness=0.6),
            extra_kwargs={"trade_probability": 0.4},
        ),
    ]
    return SimulationConfig(
        agent_specs=specs, num_rounds=num_rounds, starting_price=100.0, seed=seed,
        experiment_type="phase_diagram",
    )


def run_grid_point(
    trend_follower_count: int,
    reaction_sensitivity: float,
    seeds: list[int],
    num_rounds: int = 300,
) -> GridPointResult:
    """Run several seeds at one (trend_follower_count, reaction_sensitivity)
    combination and average the instability metrics."""
    volatilities = []
    kurtoses = []

    for seed in seeds:
        config = build_config(trend_follower_count, reaction_sensitivity, seed, num_rounds)
        result = Simulation(config).run()
        returns = returns_from_prices(result.price_history)
        if len(returns) < 2:
            continue
        volatilities.append(float(np.std(returns)))
        kurtoses.append(excess_kurtosis(returns))

    return GridPointResult(
        trend_follower_count=trend_follower_count,
        reaction_sensitivity=reaction_sensitivity,
        mean_volatility=float(np.mean(volatilities)) if volatilities else float("nan"),
        mean_excess_kurtosis=float(np.mean(kurtoses)) if kurtoses else float("nan"),
        seeds_used=seeds,
    )


def run_phase_diagram_sweep(
    trend_follower_counts: list[int],
    reaction_sensitivities: list[float],
    seeds: list[int],
    num_rounds: int = 300,
) -> list[GridPointResult]:
    """
    Full grid sweep — the core Module 5 deliverable. Returns a flat list
    of GridPointResults; use volatility_matrix() below to reshape into
    a 2D array for heatmap plotting.
    """
    results = []
    for tf_count in trend_follower_counts:
        for sensitivity in reaction_sensitivities:
            results.append(run_grid_point(tf_count, sensitivity, seeds, num_rounds))
    return results


def volatility_matrix(
    results: list[GridPointResult],
    trend_follower_counts: list[int],
    reaction_sensitivities: list[float],
) -> np.ndarray:
    """
    Reshape flat sweep results into a 2D matrix: rows = trend_follower_counts,
    columns = reaction_sensitivities. This is what you feed directly to
    matplotlib's imshow/pcolormesh for the phase diagram heatmap.
    """
    lookup = {(r.trend_follower_count, r.reaction_sensitivity): r.mean_volatility for r in results}
    matrix = np.zeros((len(trend_follower_counts), len(reaction_sensitivities)))
    for i, tf_count in enumerate(trend_follower_counts):
        for j, sensitivity in enumerate(reaction_sensitivities):
            matrix[i, j] = lookup[(tf_count, sensitivity)]
    return matrix
