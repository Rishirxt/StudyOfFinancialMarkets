"""
Module 5 milestone check.

Verifies:
  - A small grid sweep runs end to end and produces a well-formed matrix.
  - Instability (volatility) generally increases as trend-follower
    count/sensitivity increases — the expected direction of the effect,
    even if not perfectly monotonic at every single grid point (multiple
    seeds are averaged specifically to reduce, not eliminate, noise).
  - Produces a phase diagram heatmap image as the milestone deliverable.

Run with:  python -m tests.test_phase_diagram_module5
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.phase_diagram import run_phase_diagram_sweep, volatility_matrix


def check_small_grid_sweep():
    print("--- Small grid sweep (sanity check) ---")
    trend_follower_counts = [0, 4, 8, 12]
    reaction_sensitivities = [0.2, 1.0, 2.0, 3.0]
    seeds = [1, 2, 3]

    results = run_phase_diagram_sweep(
        trend_follower_counts, reaction_sensitivities, seeds, num_rounds=250
    )
    assert len(results) == len(trend_follower_counts) * len(reaction_sensitivities)
    print(f"  ran {len(results)} grid points ({len(trend_follower_counts)}x{len(reaction_sensitivities)}, "
          f"{len(seeds)} seeds each)")

    matrix = volatility_matrix(results, trend_follower_counts, reaction_sensitivities)
    print(f"  matrix shape -> {matrix.shape} (expect (4, 4))")
    assert matrix.shape == (4, 4)
    assert not np.isnan(matrix).any(), "No grid point should fail to produce a volatility value"

    # Directional check: the extreme corner (many trend-followers, high
    # sensitivity) should show higher volatility than the calm corner
    # (no trend-followers, low sensitivity) -- the core expected effect.
    calm_corner = matrix[0, 0]
    extreme_corner = matrix[-1, -1]
    print(f"  calm corner (0 trend-followers, sensitivity=0.2)   -> volatility {calm_corner:.4f}")
    print(f"  extreme corner (12 trend-followers, sensitivity=3.0) -> volatility {extreme_corner:.4f}")
    assert extreme_corner > calm_corner, \
        "More trend-follower influence should produce higher volatility than a calm baseline"
    print("  extreme corner shows higher volatility than calm corner (correct direction)")

    return results, trend_follower_counts, reaction_sensitivities, matrix


def generate_heatmap(matrix, trend_follower_counts, reaction_sensitivities, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(matrix, cmap="inferno", aspect="auto", origin="lower")
    ax.set_xticks(range(len(reaction_sensitivities)))
    ax.set_xticklabels(reaction_sensitivities)
    ax.set_yticks(range(len(trend_follower_counts)))
    ax.set_yticklabels(trend_follower_counts)
    ax.set_xlabel("Trend-follower reaction sensitivity")
    ax.set_ylabel("Trend-follower count")
    ax.set_title("Phase diagram: return volatility (instability metric)")
    fig.colorbar(im, ax=ax, label="mean return volatility")
    plt.tight_layout()
    plt.savefig(out_path, dpi=130)
    print(f"  saved heatmap -> {out_path}")


if __name__ == "__main__":
    results, tf_counts, sensitivities, matrix = check_small_grid_sweep()
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phase_diagram_small.png")
    generate_heatmap(matrix, tf_counts, sensitivities, out_path)
    print("\nAll Module 5 (small grid) checks passed.")
