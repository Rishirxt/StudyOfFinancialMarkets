"""Transparent performance-based switching between two trading rules."""

from collections import deque
from dataclasses import dataclass, field
import math
import random

import numpy as np

from agents.fundamentalist import Fundamentalist
from agents.trend_follower import TrendFollower
from core.agent import Agent, AgentParams
from core.market_state import MarketState
from core.order import Order
from core.validation import excess_kurtosis, returns_from_prices, volatility_clustering_score


@dataclass
class StrategySwitchingConfig:
    lookback_rounds: int = 20
    temperature: float = 0.002
    max_switch_probability: float = 0.25
    cooldown_rounds: int = 5

    def __post_init__(self):
        if self.lookback_rounds < 1 or self.cooldown_rounds < 1:
            raise ValueError("Herding lookback and cooldown must be positive")
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("Herding temperature must be finite and positive")
        if not math.isfinite(self.max_switch_probability) or not 0 <= self.max_switch_probability <= 1:
            raise ValueError("Maximum switching probability must be between zero and one")


class StrategySwitchingAgent(Agent):
    """An agent that can use either the fundamentalist or trend rule."""

    def __init__(
        self,
        agent_id: str,
        initial_strategy: str,
        params: AgentParams,
        fair_value: float = 100.0,
        lookback: int = 5,
        starting_price: float = 100.0,
        rng: random.Random | None = None,
    ):
        super().__init__(agent_id, params, rng=rng)
        if initial_strategy not in ("fundamentalist", "trend_follower"):
            raise ValueError("Strategy must be fundamentalist or trend_follower")
        self.strategy = initial_strategy
        self.previous_strategy: str | None = None
        self.strategy_changes: list[dict] = []
        self.strategy_profitability = {"fundamentalist": 0.0, "trend_follower": 0.0}
        self.time_in_strategy = {"fundamentalist": 0, "trend_follower": 0}
        self._last_equity = self.portfolio_value(starting_price)
        self._last_switch_round = 0
        self._fair_value = fair_value
        self._lookback = lookback
        self._rules = {
            "fundamentalist": Fundamentalist(agent_id, fair_value, params, rng=self.rng),
            "trend_follower": TrendFollower(agent_id, lookback, params=params, rng=self.rng),
        }

    def decide(self, market: MarketState) -> Order | None:
        return self._rules[self.strategy].decide(market)

    def record_close(self, mark_price: float) -> float:
        """Attribute marked-to-market P&L to the strategy active this round."""
        equity = self.portfolio_value(mark_price)
        pnl = equity - self._last_equity
        self.strategy_profitability[self.strategy] += pnl
        self._last_equity = equity
        self.time_in_strategy[self.strategy] += 1
        return pnl

    def consider_switch(self, round_number: int, performance: dict[str, float]) -> bool:
        if round_number - self._last_switch_round < self._cooldown_rounds:
            return False
        alternative = "trend_follower" if self.strategy == "fundamentalist" else "fundamentalist"
        difference = performance.get(alternative, 0.0) - performance.get(self.strategy, 0.0)
        probability = self._switch_probability(difference, self._temperature, self._max_probability)
        if self.rng.random() >= probability:
            return False

        old_strategy = self.strategy
        self.previous_strategy = old_strategy
        self.strategy = alternative
        self._last_switch_round = round_number
        self.strategy_changes.append({"round": round_number, "from": old_strategy, "to": alternative})
        return True

    @staticmethod
    def _switch_probability(score_difference: float, temperature: float, maximum: float) -> float:
        # Stable logistic transform, bounded by `maximum` even at extreme scores.
        z = max(-60.0, min(60.0, score_difference / temperature))
        return maximum / (1.0 + math.exp(-z))

    def configure_switching(self, config: StrategySwitchingConfig) -> None:
        self._temperature = config.temperature
        self._max_probability = config.max_switch_probability
        self._cooldown_rounds = config.cooldown_rounds


@dataclass
class StrategySwitchingController:
    agents: list[StrategySwitchingAgent]
    config: StrategySwitchingConfig = field(default_factory=StrategySwitchingConfig)
    performance_history: dict[str, deque] = field(init=False)
    cumulative_switches: int = 0
    history: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.performance_history = {
            strategy: deque(maxlen=self.config.lookback_rounds)
            for strategy in ("fundamentalist", "trend_follower")
        }
        for agent in self.agents:
            agent.configure_switching(self.config)

    def observe_close(self, round_number: int, mark_price: float) -> dict:
        round_profit = {"fundamentalist": [], "trend_follower": []}
        for agent in self.agents:
            delta = agent.record_close(mark_price)
            round_profit[agent.strategy].append(delta / max(agent.params.initial_cash, 1.0))

        for strategy, values in round_profit.items():
            if values:
                self.performance_history[strategy].append(sum(values) / len(values))
        scores = {
            strategy: (sum(values) / len(values) if values else 0.0)
            for strategy, values in self.performance_history.items()
        }
        switches = sum(agent.consider_switch(round_number, scores) for agent in self.agents)
        self.cumulative_switches += switches
        counts = {
            "fundamentalist": sum(a.strategy == "fundamentalist" for a in self.agents),
            "trend_follower": sum(a.strategy == "trend_follower" for a in self.agents),
            "switches_this_round": switches,
            "cumulative_switches": self.cumulative_switches,
            "strategy_profitability": scores,
        }
        self.history.append({"round": round_number, **counts})
        return counts


def run_herding_experiment(
    fundamentalist_count: int = 8,
    trend_follower_count: int = 8,
    noise_count: int = 8,
    num_rounds: int = 500,
    seed: int = 42,
    switching: StrategySwitchingConfig | None = None,
) -> dict:
    """Compare fixed and performance-switching populations under one config."""
    from core.simulation import Simulation
    from core.simulation_config import AgentSpec, SimulationConfig

    specs = [
        AgentSpec("fundamentalist", fundamentalist_count, AgentParams(aggressiveness=0.5, randomness=0.15), {"fair_value": 100.0}),
        AgentSpec("trend_follower", trend_follower_count, AgentParams(reaction_sensitivity=1.2, randomness=0.15), {"lookback": 5}),
        AgentSpec("noise_trader", noise_count, AgentParams(aggressiveness=0.6), {"trade_probability": 0.4}),
    ]
    config = SimulationConfig(specs, num_rounds=num_rounds, starting_price=100.0, seed=seed, experiment_type="herding_comparison")

    def summarize(strategy_config: StrategySwitchingConfig | None) -> dict:
        result = Simulation(config, strategy_switching=strategy_config).run()
        returns = returns_from_prices(result.price_history)
        clustering = volatility_clustering_score(returns, lags=min(10, max(1, len(returns) - 1)))
        raw_acf = np.nan_to_num(np.asarray(clustering["raw_return_acf"]), nan=0.0).tolist()
        squared_acf = np.nan_to_num(np.asarray(clustering["squared_return_acf"]), nan=0.0).tolist()
        absolute_acf = np.nan_to_num(np.asarray(clustering["abs_return_acf"]), nan=0.0).tolist()
        summary = {
            "volatility": float(np.std(returns)) if len(returns) else 0.0,
            "excess_kurtosis": excess_kurtosis(returns) if len(returns) > 3 and np.std(returns) > 0 else None,
            "raw_return_autocorrelation": raw_acf,
            "squared_return_autocorrelation": squared_acf,
            "absolute_return_autocorrelation": absolute_acf,
            "significance_band": clustering["significance_band"],
            "price_history": result.price_history,
            "strategy_history": result.strategy_history,
        }
        if strategy_config:
            summary["agent_strategies"] = [
                {
                    "agent_id": agent.agent_id,
                    "current_strategy": agent.strategy,
                    "previous_strategy": agent.previous_strategy,
                    "strategy_changes": agent.strategy_changes,
                    "strategy_profitability": agent.strategy_profitability,
                    "time_in_strategy": agent.time_in_strategy,
                }
                for agent in result.agents if isinstance(agent, StrategySwitchingAgent)
            ]
        return summary

    return {
        "fixed": summarize(None),
        "switching": summarize(switching or StrategySwitchingConfig()),
        "experiment_config": {
            "num_rounds": num_rounds,
            "seed": seed,
            "fundamentalist_count": fundamentalist_count,
            "trend_follower_count": trend_follower_count,
            "noise_count": noise_count,
        },
        "switching_config": {
            "lookback_rounds": (switching or StrategySwitchingConfig()).lookback_rounds,
            "temperature": (switching or StrategySwitchingConfig()).temperature,
            "max_switch_probability": (switching or StrategySwitchingConfig()).max_switch_probability,
            "cooldown_rounds": (switching or StrategySwitchingConfig()).cooldown_rounds,
        },
    }
