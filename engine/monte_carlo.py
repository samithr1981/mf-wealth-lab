"""
engine/monte_carlo.py
---------------------
Monte Carlo wealth simulation engine.
Runs N_SIMULATIONS paths of monthly SIP compounding with
returns drawn from Normal(μ, σ) parameterised by portfolio params.
"""

import numpy as np
from typing import Dict, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.config import N_SIMULATIONS


def run_simulation(
    expected_return:  float,
    volatility:       float,
    monthly_sip:      float,
    years:            int,
    initial_lumpsum:  float = 0.0,
    inflation_rate:   float = 0.06,
    n_sims:           int   = N_SIMULATIONS,
    seed:             int   = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulate wealth accumulation via SIP + optional lumpsum.

    Parameters
    ----------
    expected_return : annual expected return (e.g. 0.12 for 12%)
    volatility      : annual volatility      (e.g. 0.14 for 14%)
    monthly_sip     : monthly investment in ₹
    years           : investment horizon
    initial_lumpsum : one-time lumpsum at t=0
    inflation_rate  : to compute real (inflation-adjusted) values
    n_sims          : number of simulation paths
    seed            : random seed for reproducibility

    Returns
    -------
    final_values      : array of shape (n_sims,) — nominal ₹ values
    all_paths         : array of shape (n_sims, months) — full wealth paths
    """
    if seed is not None:
        np.random.seed(seed)

    months      = years * 12
    monthly_mu  = expected_return / 12
    monthly_sig = volatility / np.sqrt(12)

    # Draw all random returns at once: shape (n_sims, months)
    rand_returns = np.random.normal(monthly_mu, monthly_sig, (n_sims, months))

    # Simulate wealth paths
    all_paths = np.zeros((n_sims, months))
    value     = np.full(n_sims, float(initial_lumpsum))

    for m in range(months):
        value = value * (1 + rand_returns[:, m]) + monthly_sip
        all_paths[:, m] = value

    final_values = all_paths[:, -1]

    return final_values, all_paths


def real_value(nominal: float, inflation: float, years: int) -> float:
    """Deflate nominal future value to today's purchasing power."""
    return nominal / ((1 + inflation) ** years)


def compute_outcomes(
    final_values: np.ndarray,
    years:        int,
    monthly_sip:  float,
    initial_lumpsum: float = 0.0,
    inflation_rate:  float = 0.06,
) -> Dict:
    """
    Compute summary statistics from simulation final values.
    """
    total_invested = monthly_sip * years * 12 + initial_lumpsum

    p10  = float(np.percentile(final_values, 10))
    p25  = float(np.percentile(final_values, 25))
    p50  = float(np.percentile(final_values, 50))
    p75  = float(np.percentile(final_values, 75))
    p90  = float(np.percentile(final_values, 90))
    mean = float(np.mean(final_values))

    prob_2x = float(np.mean(final_values >= 2 * total_invested))
    prob_5x = float(np.mean(final_values >= 5 * total_invested))

    return {
        "total_invested":   round(total_invested),
        "p10_nominal":      round(p10),
        "p25_nominal":      round(p25),
        "p50_nominal":      round(p50),
        "p75_nominal":      round(p75),
        "p90_nominal":      round(p90),
        "mean_nominal":     round(mean),
        "p10_real":         round(real_value(p10,  inflation_rate, years)),
        "p50_real":         round(real_value(p50,  inflation_rate, years)),
        "p90_real":         round(real_value(p90,  inflation_rate, years)),
        "prob_2x":          round(prob_2x * 100, 1),
        "prob_5x":          round(prob_5x * 100, 1),
        "xirr_median_approx": round(
            (p50 / total_invested) ** (1 / years) - 1, 4
        ) if total_invested > 0 else 0,
    }


def get_cone_paths(
    all_paths: np.ndarray,
    percentiles: Tuple = (10, 50, 90),
) -> Dict[str, np.ndarray]:
    """
    Extract percentile paths for wealth cone visualisation.
    Returns dict of {label: array_of_monthly_values}.
    """
    labels = ["pessimistic", "median", "optimistic"]
    return {
        label: np.percentile(all_paths, p, axis=0)
        for label, p in zip(labels, percentiles)
    }


if __name__ == "__main__":
    # Quick smoke test
    final_values, all_paths = run_simulation(
        expected_return = 0.12,
        volatility      = 0.14,
        monthly_sip     = 50_000,
        years           = 20,
        initial_lumpsum = 500_000,
        seed            = 42,
    )
    outcomes = compute_outcomes(final_values, 20, 50_000, 500_000)
    cone     = get_cone_paths(all_paths)

    print("\n💰 Simulation Results (₹50K SIP + ₹5L lumpsum, 20 years, 12% / 14% vol)")
    print(f"   Total Invested       : ₹{outcomes['total_invested']/1e7:.2f} Cr")
    print(f"   Pessimistic (P10)    : ₹{outcomes['p10_nominal']/1e7:.2f} Cr")
    print(f"   Median (P50)         : ₹{outcomes['p50_nominal']/1e7:.2f} Cr")
    print(f"   Optimistic (P90)     : ₹{outcomes['p90_nominal']/1e7:.2f} Cr")
    print(f"   Prob of 5x wealth    : {outcomes['prob_5x']}%")
    print(f"   Median XIRR (approx) : {outcomes['xirr_median_approx']*100:.1f}%")
    print(f"\n   Cone paths shape: {all_paths.shape}")
