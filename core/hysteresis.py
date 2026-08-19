"""
Hysteresis experiment (Module 6) — the project's primary novelty.

Research question: does an order-book-driven agent-based market exhibit
hysteresis when a destabilizing parameter is increased past the
instability threshold and then reversed — i.e. does the market return
to its original equilibrium, or settle into a different one?

Design: a SINGLE continuous simulation run, during which the trend-
follower reaction_sensitivity follows a piecewise-linear ramp:

    baseline -> ramp up -> peak (past instability) -> ramp down -> baseline

The order book, price history, and agent state all persist continuously
across the entire run — this continuity is what makes the experiment
meaningful. Independent runs per parameter value (Module 5's sweep)
cannot show path-dependence by construction, since each run starts
fresh; only a single evolving market can carry a "scar" from the peak
into the post-reversal baseline period.

We then compare the PRE-ramp baseline window against the POST-ramp
baseline window on two metrics:
  - mean price level (did the market settle at the same price?)
  - return volatility (did it become calmer/noisier than before?)

A meaningful difference between these two windows is evidence of
hysteresis. A close match is evidence the market is "elastic" and
returns to its original state. Both are legitimate, reportable
findings — this module does not assume which outcome is correct.
"""

from dataclasses import dataclass

import numpy as np

from core.agent import AgentParams
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig
from core.validation import excess_kurtosis, returns_from_prices


@dataclass
class RampSchedule:
    baseline_value: float
    peak_value: float
    hold_before: int
    ramp_up_rounds: int
    hold_at_peak: int
    ramp_down_rounds: int
    hold_after: int

    @property
    def total_rounds(self) -> int:
        return (self.hold_before + self.ramp_up_rounds + self.hold_at_peak
                + self.ramp_down_rounds + self.hold_after)

    def value_at(self, round_number: int) -> float:
        """Piecewise-linear schedule value at a given round."""
        r = round_number
        b, up, peak, down, after = (
            self.hold_before, self.ramp_up_rounds, self.hold_at_peak,
            self.ramp_down_rounds, self.hold_after,
        )

        if r <= b:
            return self.baseline_value
        r -= b
        if r <= up:
            frac = r / up if up > 0 else 1.0
            return self.baseline_value + frac * (self.peak_value - self.baseline_value)
        r -= up
        if r <= peak:
            return self.peak_value
        r -= peak
        if r <= down:
            frac = r / down if down > 0 else 1.0
            return self.peak_value + frac * (self.baseline_value - self.peak_value)
        return self.baseline_value

    def window_pre_baseline(self) -> tuple[int, int]:
        """Round range (inclusive) of the pre-ramp baseline period."""
        return (1, self.hold_before)

    def window_post_baseline(self) -> tuple[int, int]:
        """Round range (inclusive) of the post-reversal baseline period."""
        start = self.hold_before + self.ramp_up_rounds + self.hold_at_peak + self.ramp_down_rounds + 1
        return (start, self.total_rounds)


def build_hysteresis_config(
    schedule: RampSchedule,
    trend_follower_count: int = 8,
    fundamentalist_count: int = 8,
    noise_count: int = 8,
    seed: int = 42,
) -> tuple[SimulationConfig, AgentParams]:
    """
    Builds the config AND returns a direct reference to the trend-follower
    AgentParams instance — since agent_factory shares one AgentParams
    object across every agent built from the same spec, mutating this
    single object's reaction_sensitivity each round is enough to affect
    every trend-follower agent at once. This is what the round_hook
    closure below actually mutates.
    """
    trend_params = AgentParams(reaction_sensitivity=schedule.baseline_value, randomness=0.15)

    specs = [
        AgentSpec(
            agent_type="fundamentalist", count=fundamentalist_count,
            params=AgentParams(aggressiveness=0.5, randomness=0.15),
            extra_kwargs={"fair_value": 100.0},
        ),
        AgentSpec(
            agent_type="trend_follower", count=trend_follower_count,
            params=trend_params,
            extra_kwargs={"lookback": 5},
        ),
        AgentSpec(
            agent_type="noise_trader", count=noise_count,
            params=AgentParams(aggressiveness=0.6),
            extra_kwargs={"trade_probability": 0.4},
        ),
    ]

    config = SimulationConfig(
        agent_specs=specs, num_rounds=schedule.total_rounds, starting_price=100.0,
        seed=seed, experiment_type="hysteresis",
    )
    return config, trend_params


def make_schedule_hook(schedule: RampSchedule, target_params: AgentParams):
    """Returns a round_hook closure that mutates target_params.reaction_sensitivity
    according to the schedule, and records the applied value per round."""
    applied_values = []

    def hook(round_number: int):
        value = schedule.value_at(round_number)
        target_params.reaction_sensitivity = value
        applied_values.append((round_number, value))

    hook.applied_values = applied_values
    return hook


@dataclass
class HysteresisResult:
    schedule: RampSchedule
    price_history: list
    applied_sensitivity: list
    pre_mean_price: float
    post_mean_price: float
    pre_volatility: float
    post_volatility: float
    pre_kurtosis: float
    post_kurtosis: float

    @property
    def price_shift(self) -> float:
        return self.post_mean_price - self.pre_mean_price

    @property
    def price_shift_pct(self) -> float:
        return (self.price_shift / self.pre_mean_price) * 100

    @property
    def volatility_ratio(self) -> float:
        return self.post_volatility / self.pre_volatility if self.pre_volatility > 0 else float("nan")


def run_hysteresis_experiment(schedule: RampSchedule, seed: int = 42, **config_kwargs) -> HysteresisResult:
    config, trend_params = build_hysteresis_config(schedule, seed=seed, **config_kwargs)
    hook = make_schedule_hook(schedule, trend_params)

    result = Simulation(config, round_hook=hook).run()

    pre_start, pre_end = schedule.window_pre_baseline()
    post_start, post_end = schedule.window_post_baseline()

    # price_history[0] is the starting price before round 1, so
    # price_history[r] is the closing price AFTER round r.
    pre_prices = result.price_history[pre_start:pre_end + 1]
    post_prices = result.price_history[post_start:post_end + 1]

    pre_returns = returns_from_prices(pre_prices) if len(pre_prices) > 1 else np.array([])
    post_returns = returns_from_prices(post_prices) if len(post_prices) > 1 else np.array([])

    return HysteresisResult(
        schedule=schedule,
        price_history=result.price_history,
        applied_sensitivity=hook.applied_values,
        pre_mean_price=float(np.mean(pre_prices)),
        post_mean_price=float(np.mean(post_prices)),
        pre_volatility=float(np.std(pre_returns)) if len(pre_returns) else float("nan"),
        post_volatility=float(np.std(post_returns)) if len(post_returns) else float("nan"),
        pre_kurtosis=excess_kurtosis(pre_returns) if len(pre_returns) > 3 else float("nan"),
        post_kurtosis=excess_kurtosis(post_returns) if len(post_returns) > 3 else float("nan"),
    )


def run_hysteresis_across_seeds(schedule: RampSchedule, seeds: list[int], **config_kwargs) -> list[HysteresisResult]:
    """
    Repeat the experiment across multiple seeds — a single run is an
    anecdote; a repeatable pattern across seeds is evidence. This is
    what the Module 6 milestone check and final report should rely on,
    not any single seed's result.
    """
    return [run_hysteresis_experiment(schedule, seed=s, **config_kwargs) for s in seeds]