"""
Agent factory — builds a concrete list of Agent instances from
AgentSpecs. Kept separate from Simulation itself so it's independently
testable and reusable by the Module 5 batch runner.
"""

from agents.fundamentalist import Fundamentalist
from agents.trend_follower import TrendFollower
from agents.noise_trader import NoiseTrader
from agents.leveraged_trader import LeveragedTrader
from core.herding import StrategySwitchingAgent, StrategySwitchingConfig, StrategySwitchingController
from core.simulation_config import AgentSpec

_AGENT_CLASSES = {
    "fundamentalist": Fundamentalist,
    "trend_follower": TrendFollower,
    "noise_trader": NoiseTrader,
    "leveraged_trader": LeveragedTrader,
}


def build_population(
    agent_specs: list[AgentSpec],
    strategy_switching: StrategySwitchingConfig | None = None,
    rng=None,
) -> list:
    agents = []
    for spec in agent_specs:
        if spec.agent_type not in _AGENT_CLASSES:
            raise ValueError(
                f"Unknown agent_type '{spec.agent_type}'. "
                f"Expected one of {list(_AGENT_CLASSES)}."
            )
        agent_cls = _AGENT_CLASSES[spec.agent_type]
        for i in range(spec.count):
            agent_id = f"{spec.agent_type}_{i}"
            if strategy_switching and spec.agent_type in ("fundamentalist", "trend_follower"):
                kwargs = spec.extra_kwargs
                agent = StrategySwitchingAgent(
                    agent_id=agent_id,
                    initial_strategy=spec.agent_type,
                    params=spec.params,
                    rng=rng,
                    fair_value=kwargs.get("fair_value", 100.0),
                    lookback=kwargs.get("lookback", 5),
                )
                agent.configure_switching(strategy_switching)
                agents.append(agent)
            else:
                agents.append(agent_cls(
                    agent_id=agent_id,
                    params=spec.params,
                    rng=rng,
                    **spec.extra_kwargs,
                ))
    return agents
