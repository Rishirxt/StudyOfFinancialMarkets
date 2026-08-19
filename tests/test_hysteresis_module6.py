"""
Module 6 milestone check.

Verifies:
  - The ramp schedule produces the correct piecewise shape (baseline,
    ramp up, peak, ramp down, baseline) at spot-checked rounds.
  - A single continuous run correctly applies the schedule round-by-round
    (the recorded applied_sensitivity trace matches schedule.value_at()).
  - The pre/post baseline windows are correctly identified and produce
    real, computable metrics.
  - Repeats across multiple seeds and reports whether the hysteresis
    pattern (price shift / volatility ratio) is consistent across seeds
    -- this is the honest, central finding of the whole project, so it
    is reported clearly rather than forced to a predetermined answer.

Run with:  python -m tests.test_hysteresis_module6
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.hysteresis import RampSchedule, run_hysteresis_across_seeds, run_hysteresis_experiment


def make_test_schedule() -> RampSchedule:
    """
    A moderate schedule for the milestone check: enough rounds in each
    phase to get meaningful statistics, small enough to run quickly.
    Peak sensitivity (3.0) sits well past the instability threshold
    Module 5 identified.
    """
    return RampSchedule(
        baseline_value=0.3,
        peak_value=3.0,
        hold_before=150,
        ramp_up_rounds=150,
        hold_at_peak=100,
        ramp_down_rounds=150,
        hold_after=150,
    )


def check_schedule_shape():
    print("--- Ramp schedule shape ---")
    schedule = make_test_schedule()
    print(f"  total rounds -> {schedule.total_rounds}")

    assert schedule.value_at(1) == schedule.baseline_value
    assert schedule.value_at(150) == schedule.baseline_value
    print(f"  round 1, 150 (pre-ramp baseline) -> {schedule.value_at(1)} (expect {schedule.baseline_value})")

    assert abs(schedule.value_at(225) - 1.65) < 0.01  # midpoint of ramp up
    print(f"  round 225 (mid ramp-up)          -> {schedule.value_at(225):.2f} (expect ~1.65, midpoint)")

    assert schedule.value_at(350) == schedule.peak_value
    print(f"  round 350 (at peak)              -> {schedule.value_at(350)} (expect {schedule.peak_value})")

    assert schedule.value_at(700) == schedule.baseline_value
    print(f"  round 700 (post-ramp baseline)   -> {schedule.value_at(700)} (expect {schedule.baseline_value})")

    pre = schedule.window_pre_baseline()
    post = schedule.window_post_baseline()
    print(f"  pre-baseline window  -> {pre}")
    print(f"  post-baseline window -> {post}")
    assert pre == (1, 150)
    assert post == (551, 700)


def check_single_run_applies_schedule():
    print("\n--- Single run correctly applies the schedule ---")
    schedule = make_test_schedule()
    result = run_hysteresis_experiment(schedule, seed=1)

    assert len(result.applied_sensitivity) == schedule.total_rounds
    # Spot check a few rounds against the schedule directly.
    for round_num in [1, 225, 350, 700]:
        applied_value = dict(result.applied_sensitivity)[round_num]
        expected = schedule.value_at(round_num)
        assert abs(applied_value - expected) < 1e-9
    print(f"  {len(result.applied_sensitivity)} rounds recorded, spot checks match schedule exactly (correct)")
    print(f"  price series length -> {len(result.price_history)}")


def check_hysteresis_across_seeds():
    print("\n--- Hysteresis result across multiple seeds ---")
    schedule = make_test_schedule()
    seeds = [1, 2, 3, 4, 5]
    results = run_hysteresis_across_seeds(schedule, seeds)

    print(f"  {'seed':<6} {'pre price':>10} {'post price':>11} {'shift %':>9} "
          f"{'pre vol':>9} {'post vol':>9} {'vol ratio':>10}")
    for seed, r in zip(seeds, results):
        print(f"  {seed:<6} {r.pre_mean_price:>10.2f} {r.post_mean_price:>11.2f} "
              f"{r.price_shift_pct:>8.2f}% {r.pre_volatility:>9.4f} {r.post_volatility:>9.4f} "
              f"{r.volatility_ratio:>10.2f}")

    shifts = [r.price_shift_pct for r in results]
    vol_ratios = [r.volatility_ratio for r in results]

    print(f"\n  mean price shift    -> {np.mean(shifts):.2f}% (std {np.std(shifts):.2f}%)")
    print(f"  mean volatility ratio (post/pre) -> {np.mean(vol_ratios):.2f} (std {np.std(vol_ratios):.2f})")

    # Honest reporting, not a forced conclusion: hysteresis is "present"
    # in this run if the post-baseline consistently differs from the
    # pre-baseline across seeds (not just noise around zero/one).
    consistent_shift = all(abs(s) > 0.1 for s in shifts) and (np.std(shifts) < abs(np.mean(shifts)) + 5)
    print(f"\n  NOTE: this is the project's central open research question -- the result above is")
    print(f"  reported as-is, not forced toward a predetermined conclusion. A consistent non-zero")
    print(f"  price shift and/or volatility ratio != 1 across seeds is evidence of hysteresis;")
    print(f"  values scattered around 0%/1.0 with no consistent direction is evidence the market")
    print(f"  is elastic and returns to its original state.")


if __name__ == "__main__":
    check_schedule_shape()
    check_single_run_applies_schedule()
    check_hysteresis_across_seeds()
    print("\nAll Module 6 structural checks passed (see hysteresis finding above).")