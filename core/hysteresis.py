"""Continuous parameter-ramp experiment for measuring market hysteresis."""

from dataclasses import dataclass

import numpy as np

from core.agent import AgentParams
from core.simulation import Simulation
from core.simulation_config import AgentSpec, SimulationConfig
from core.validation import excess_kurtosis, returns_from_prices


@dataclass(frozen=True)
class HysteresisTolerances:
    price_shift_pct: float = 0.05
    volatility_ratio_low: float = 0.90
    volatility_ratio_high: float = 1.10


DEFAULT_TOLERANCES = HysteresisTolerances()


@dataclass
class RampSchedule:
    baseline_value: float = 0.2
    peak_value: float = 3.0
    hold_before: int = 500
    ramp_up_rounds: int = 250
    hold_at_peak: int = 250
    ramp_down_rounds: int = 250
    hold_after: int = 500

    def __post_init__(self):
        if min(self.hold_before, self.ramp_up_rounds, self.hold_at_peak,
               self.ramp_down_rounds, self.hold_after) < 1:
            raise ValueError("All schedule phases must contain at least one round")
        if self.baseline_value < 0 or self.peak_value < 0:
            raise ValueError("Sensitivity values must be non-negative")
        if self.peak_value == self.baseline_value:
            raise ValueError("Peak sensitivity must differ from baseline")

    @property
    def total_rounds(self):
        return self.hold_before + self.ramp_up_rounds + self.hold_at_peak + self.ramp_down_rounds + self.hold_after

    @property
    def phase_boundaries(self):
        return {
            "pre_baseline": (1, self.hold_before),
            "ramp_up": (self.hold_before + 1, self.hold_before + self.ramp_up_rounds),
            "peak": (self.hold_before + self.ramp_up_rounds + 1,
                     self.hold_before + self.ramp_up_rounds + self.hold_at_peak),
            "ramp_down": (self.hold_before + self.ramp_up_rounds + self.hold_at_peak + 1,
                          self.hold_before + self.ramp_up_rounds + self.hold_at_peak + self.ramp_down_rounds),
            "post_baseline": (self.hold_before + self.ramp_up_rounds + self.hold_at_peak + self.ramp_down_rounds + 1,
                              self.total_rounds),
        }

    def value_at(self, round_number: int) -> float:
        if round_number < 1 or round_number > self.total_rounds:
            raise ValueError("round_number is outside the schedule")
        b, u, h, d = self.hold_before, self.ramp_up_rounds, self.hold_at_peak, self.ramp_down_rounds
        if round_number <= b:
            return self.baseline_value
        if round_number <= b + u:
            return self.baseline_value + (round_number - b) / u * (self.peak_value - self.baseline_value)
        if round_number <= b + u + h:
            return self.peak_value
        if round_number <= b + u + h + d:
            return self.peak_value + (round_number - b - u - h) / d * (self.baseline_value - self.peak_value)
        return self.baseline_value

    def window_pre_baseline(self):
        return self.phase_boundaries["pre_baseline"]

    def window_post_baseline(self):
        return self.phase_boundaries["post_baseline"]


def classify_hysteresis(price_shift_pct, volatility_ratio, tolerances=DEFAULT_TOLERANCES):
    price_changed = not np.isfinite(price_shift_pct) or abs(price_shift_pct) >= tolerances.price_shift_pct
    volatility_changed = (not np.isfinite(volatility_ratio) or
                          volatility_ratio < tolerances.volatility_ratio_low or
                          volatility_ratio > tolerances.volatility_ratio_high)
    return bool(price_changed or volatility_changed)


def build_hysteresis_config(schedule, trend_follower_count=8, fundamentalist_count=8, noise_count=8, seed=42):
    trend_params = AgentParams(reaction_sensitivity=schedule.baseline_value, randomness=0.15)
    specs = [
        AgentSpec("fundamentalist", fundamentalist_count, AgentParams(aggressiveness=0.5, randomness=0.15), {"fair_value": 100.0}),
        AgentSpec("trend_follower", trend_follower_count, trend_params, {"lookback": 5}),
        AgentSpec("noise_trader", noise_count, AgentParams(aggressiveness=0.6), {"trade_probability": 0.4}),
    ]
    return SimulationConfig(agent_specs=specs, num_rounds=schedule.total_rounds, starting_price=100.0,
                            seed=seed, experiment_type="hysteresis"), trend_params


def make_schedule_hook(schedule, target_params):
    applied = []
    def hook(round_number):
        value = schedule.value_at(round_number)
        target_params.reaction_sensitivity = value
        applied.append((round_number, value))
    hook.applied_values = applied
    return hook


def _window_stats(prices):
    prices = np.asarray(prices, dtype=float)
    returns = returns_from_prices(prices) if len(prices) > 1 else np.array([])
    return {
        "mean_price": float(np.mean(prices)),
        "price_volatility": float(np.std(prices)),
        "return_volatility": float(np.std(returns)) if len(returns) else 0.0,
        "excess_kurtosis": excess_kurtosis(returns) if len(returns) > 3 else 0.0,
        "mean_absolute_return": float(np.mean(np.abs(returns))) if len(returns) else 0.0,
    }


@dataclass
class HysteresisResult:
    schedule: RampSchedule
    price_history: list
    applied_sensitivity: list
    pre_stats: dict
    post_stats: dict
    tolerances: HysteresisTolerances = DEFAULT_TOLERANCES

    @property
    def pre_mean_price(self): return self.pre_stats["mean_price"]
    @property
    def post_mean_price(self): return self.post_stats["mean_price"]
    @property
    def pre_volatility(self): return self.pre_stats["return_volatility"]
    @property
    def post_volatility(self): return self.post_stats["return_volatility"]
    @property
    def pre_kurtosis(self): return self.pre_stats["excess_kurtosis"]
    @property
    def post_kurtosis(self): return self.post_stats["excess_kurtosis"]
    @property
    def price_shift_pct(self):
        return abs(self.post_mean_price - self.pre_mean_price) / abs(self.pre_mean_price) * 100 if self.pre_mean_price else float("inf")
    @property
    def price_shift(self): return self.post_mean_price - self.pre_mean_price
    @property
    def volatility_ratio(self): return self.post_volatility / self.pre_volatility if self.pre_volatility else (1.0 if self.post_volatility == 0 else float("inf"))
    @property
    def hysteresis_detected(self): return classify_hysteresis(self.price_shift_pct, self.volatility_ratio, self.tolerances)

    def as_dict(self):
        return {
            "pre_ramp_price": self.pre_mean_price, "post_ramp_price": self.post_mean_price,
            "price_shift_pct": self.price_shift_pct,
            "pre_ramp_volatility": self.pre_volatility, "post_ramp_volatility": self.post_volatility,
            "volatility_ratio": self.volatility_ratio,
            "pre_ramp_kurtosis": self.pre_kurtosis, "post_ramp_kurtosis": self.post_kurtosis,
            "hysteresis_detected": self.hysteresis_detected,
        }


def run_hysteresis_experiment(schedule, seed=42, tolerances=DEFAULT_TOLERANCES, **config_kwargs):
    config, params = build_hysteresis_config(schedule, seed=seed, **config_kwargs)
    hook = make_schedule_hook(schedule, params)
    result = Simulation(config, round_hook=hook).run()  # one market, one order book, no restart
    pre_start, pre_end = schedule.window_pre_baseline()
    post_start, post_end = schedule.window_post_baseline()
    # History index r is the close after round r; bounds are inclusive rounds.
    pre_stats = _window_stats(result.price_history[pre_start:pre_end + 1])
    post_stats = _window_stats(result.price_history[post_start:post_end + 1])
    return HysteresisResult(schedule, result.price_history, hook.applied_values, pre_stats, post_stats, tolerances)


def run_hysteresis_across_seeds(schedule, seeds, tolerances=DEFAULT_TOLERANCES, **config_kwargs):
    return [run_hysteresis_experiment(schedule, seed=s, tolerances=tolerances, **config_kwargs) for s in seeds]


def summarize_seed_results(results, seeds):
    shifts = np.asarray([r.price_shift_pct for r in results], dtype=float)
    ratios = np.asarray([r.volatility_ratio for r in results], dtype=float)
    return {
        "seeds": list(seeds), "mean_price_shift_pct": float(np.mean(shifts)),
        "median_price_shift_pct": float(np.median(shifts)),
        "mean_volatility_ratio": float(np.mean(ratios)),
        "price_shift_std_pct": float(np.std(shifts)), "volatility_ratio_std": float(np.std(ratios)),
        "hysteresis_seed_count": sum(r.hysteresis_detected for r in results),
        "consistent_hysteresis_detected": bool(results and all(r.hysteresis_detected for r in results)),
    }
