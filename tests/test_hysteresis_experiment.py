import numpy as np
from unittest.mock import patch

import core.hysteresis as hysteresis_module
from core.hysteresis import (
    HysteresisTolerances, RampSchedule, classify_hysteresis,
    run_hysteresis_across_seeds, run_hysteresis_experiment,
    summarize_seed_results,
)


def small_schedule():
    return RampSchedule(0.2, 1.4, 20, 10, 8, 10, 20)


def test_schedule_phases_and_parameter_reversal():
    schedule = small_schedule()
    assert schedule.total_rounds == 68
    assert schedule.value_at(1) == 0.2
    assert schedule.value_at(20) == 0.2
    assert np.isclose(schedule.value_at(25), 0.8)
    assert schedule.value_at(30) == 1.4
    assert schedule.value_at(38) == 1.4
    assert np.isclose(schedule.value_at(43), 0.8)
    assert np.isclose(schedule.value_at(48), 0.2)
    assert np.isclose(schedule.value_at(68), 0.2)
    assert schedule.phase_boundaries == {
        "pre_baseline": (1, 20), "ramp_up": (21, 30), "peak": (31, 38),
        "ramp_down": (39, 48), "post_baseline": (49, 68),
    }


def test_classification_respects_configurable_tolerances():
    tol = HysteresisTolerances(0.05, 0.9, 1.1)
    assert not classify_hysteresis(0.01, 1.0, tol)
    assert classify_hysteresis(0.06, 1.0, tol)
    assert classify_hysteresis(0.01, 0.89, tol)
    assert classify_hysteresis(0.01, 1.11, tol)


def test_windows_timeseries_and_continuity_are_actual_run_output():
    schedule = small_schedule()
    original_simulation = hysteresis_module.Simulation
    with patch.object(hysteresis_module, "Simulation", wraps=original_simulation) as simulation_factory:
        result = run_hysteresis_experiment(schedule, seed=42)
    simulation_factory.assert_called_once()
    assert len(result.price_history) == schedule.total_rounds + 1
    assert len(result.applied_sensitivity) == schedule.total_rounds
    assert result.applied_sensitivity[0] == (1, schedule.value_at(1))
    assert result.applied_sensitivity[-1] == (schedule.total_rounds, schedule.baseline_value)
    assert result.pre_stats["mean_price"] == np.mean(result.price_history[1:21])
    assert result.post_stats["mean_price"] == np.mean(result.price_history[49:69])
    assert set(result.pre_stats) == {"mean_price", "price_volatility", "return_volatility", "excess_kurtosis", "mean_absolute_return"}


def test_multiseed_and_identical_seed_are_deterministic():
    schedule = small_schedule()
    first = run_hysteresis_experiment(schedule, seed=123)
    second = run_hysteresis_experiment(schedule, seed=123)
    assert first.price_history == second.price_history
    assert first.pre_stats == second.pre_stats
    seeds = [42, 123, 456]
    results = run_hysteresis_across_seeds(schedule, seeds)
    summary = summarize_seed_results(results, seeds)
    assert summary["seeds"] == seeds
    assert summary["hysteresis_seed_count"] == sum(r.hysteresis_detected for r in results)
    assert summary["mean_price_shift_pct"] == np.mean([r.price_shift_pct for r in results])
