"""
Simulation configuration.

AgentSpec describes "how many of this agent type, with what parameters"
so a whole population can be declared as data rather than code. This is
what makes Module 5's parameter sweep and Module 6's hysteresis
forward/reverse experiment possible: you generate many SimulationConfigs
programmatically (varying trend_follower ratio / reaction_sensitivity)
instead of hand-writing a new population every time.
"""

import uuid
from dataclasses import dataclass, field

from core.agent import AgentParams


@dataclass
class AgentSpec:
    agent_type: str          # "fundamentalist" | "trend_follower" | "noise_trader"
    count: int
    params: AgentParams = field(default_factory=AgentParams)
    # Extra constructor kwargs specific to that agent type
    # (e.g. fair_value for Fundamentalist, lookback for TrendFollower).
    extra_kwargs: dict = field(default_factory=dict)


@dataclass
class SimulationConfig:
    agent_specs: list[AgentSpec]
    num_rounds: int = 200
    starting_price: float = 100.0
    seed: int | None = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    # Free-form label for the experiment this run belongs to
    # (e.g. "phase_diagram", "hysteresis_forward") — populates
    # EXPERIMENT_CONFIG.experiment_type in the ER diagram.
    experiment_type: str = "single_run"
