"""
Batch runner — runs many SimulationConfigs and collects their results.
This is the piece Module 5 (phase diagram) and Module 6 (hysteresis)
build on top of: they generate a list of configs that vary specific
parameters (trend-follower ratio, reaction_sensitivity) and this
function is what actually executes the sweep.

Kept deliberately simple here in Module 3 — no parallelism yet. If
sweeps get slow once Module 5's grid gets large, this is the function
to parallelize (e.g. with concurrent.futures.ProcessPoolExecutor),
since each run is fully independent.
"""

from core.simulation import Simulation
from core.simulation_config import SimulationConfig
from core.simulation_result import SimulationResult


def run_batch(configs: list[SimulationConfig]) -> list[SimulationResult]:
    results = []
    for config in configs:
        sim = Simulation(config)
        results.append(sim.run())
    return results
