"""
Validation against real markets — "stylized facts" check.

Two well-known statistical signatures of real financial markets that a
credible simulation should reproduce, at least directionally:

  1. Fat tails (excess kurtosis): real return distributions have far
     more extreme moves than a normal distribution predicts. A normal
     distribution has kurtosis = 3 ("excess kurtosis" = kurtosis - 3 = 0).
     Real markets typically show excess kurtosis well above 0.

  2. Volatility clustering: large price moves tend to cluster in time
     (calm periods and turbulent periods), which shows up as significant
     positive autocorrelation in squared/absolute returns, even when raw
     returns themselves show almost no autocorrelation. This is the
     "ARCH effect" and is one of the most robust empirical facts in
     finance.

This module computes both metrics for (a) the real reference dataset
bundled in data/reference_sp500.csv and (b) a simulated price series,
so they can be compared side by side.
"""

import os

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import acf

_REFERENCE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reference_sp500.csv")


def load_reference_returns() -> np.ndarray:
    """Daily log returns from the bundled real S&P 500 reference data (2000-2019)."""
    df = pd.read_csv(_REFERENCE_PATH, parse_dates=["date"])
    prices = df["close"].to_numpy()
    log_returns = np.diff(np.log(prices))
    return log_returns


def returns_from_prices(prices: list[float]) -> np.ndarray:
    """Daily log returns from a simulated price series."""
    prices = np.asarray(prices, dtype=float)
    return np.diff(np.log(prices))


def excess_kurtosis(returns: np.ndarray) -> float:
    """
    Excess kurtosis (kurtosis - 3). 0 = normal distribution.
    Real markets: typically well above 0 (fat tails).
    """
    return float(stats.kurtosis(returns, fisher=True, bias=False))


def volatility_clustering_score(returns: np.ndarray, lags: int = 10) -> dict:
    """
    Autocorrelation of squared returns at several lags — the standard
    diagnostic for volatility clustering (ARCH effects). Also computes
    the same for raw returns as a contrast: real markets show near-zero
    raw-return autocorrelation but significant squared-return
    autocorrelation. That contrast is the actual signature to look for,
    not just "is squared-return autocorrelation positive".
    """
    raw_acf = acf(returns, nlags=lags, fft=True)[1:]
    squared_acf = acf(returns ** 2, nlags=lags, fft=True)[1:]
    abs_acf = acf(np.abs(returns), nlags=lags, fft=True)[1:]

    # Approximate 95% significance band for autocorrelation under the
    # null of no autocorrelation, for a series of this length.
    n = len(returns)
    sig_band = 1.96 / np.sqrt(n)

    return {
        "raw_return_acf": raw_acf.tolist(),
        "squared_return_acf": squared_acf.tolist(),
        "abs_return_acf": abs_acf.tolist(),
        "significance_band": float(sig_band),
        "mean_raw_acf": float(np.mean(np.abs(raw_acf))),
        "mean_squared_acf": float(np.mean(squared_acf)),
    }


def validation_report(sim_prices: list[float]) -> dict:
    """
    Full side-by-side comparison: simulated vs. real reference data.
    This is the single entry point Module 4's milestone check and any
    later reporting/plotting code should call.
    """
    real_returns = load_reference_returns()
    sim_returns = returns_from_prices(sim_prices)

    return {
        "real": {
            "n_observations": len(real_returns),
            "excess_kurtosis": excess_kurtosis(real_returns),
            "volatility_clustering": volatility_clustering_score(real_returns),
        },
        "simulated": {
            "n_observations": len(sim_returns),
            "excess_kurtosis": excess_kurtosis(sim_returns),
            "volatility_clustering": volatility_clustering_score(sim_returns),
        },
    }
