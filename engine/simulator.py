"""
engine/simulator.py
-------------------
Monte Carlo simulation engine.
Runs N simulations of monthly SIP wealth accumulation.
Returns full path matrix and final value distribution.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationResult:
    paths: np.ndarray           # shape (n_simulations, n_months+1)
    final_values: np.ndarray    # shape (n_simulations,)
    months: int
    sip: float
    expected_return: float
    volatility: float
    n_simulations: int


def run_simulation(
    sip: float,
    years: int,
    expected_return: float,     # annualised
    volatility: float,          # annualised
    n_simulations: int = 10_000,
    initial_corpus: float = 0.0,
    seed: Optional[int] = None,
) -> SimulationResult:
    """
    Monte Carlo SIP simulation.

    Each month:
        value = value * (1 + monthly_return) + sip
    Monthly return ~ Normal(expected_return/12, volatility/sqrt(12))
    """
    if seed is not None:
        np.random.seed(seed)

    months = years * 12
    monthly_mean = expected_return / 12
    monthly_std  = volatility / np.sqrt(12)

    # Draw all random returns at once: (n_simulations, months)
    returns = np.random.normal(monthly_mean, monthly_std, size=(n_simulations, months))

    # Build wealth paths
    paths = np.zeros((n_simulations, months + 1))
    paths[:, 0] = initial_corpus

    for m in range(months):
        paths[:, m + 1] = paths[:, m] * (1 + returns[:, m]) + sip

    return SimulationResult(
        paths=paths,
        final_values=paths[:, -1],
        months=months,
        sip=sip,
        expected_return=expected_return,
        volatility=volatility,
        n_simulations=n_simulations,
    )


if __name__ == "__main__":
    result = run_simulation(
        sip=25_000,
        years=20,
        expected_return=0.12,
        volatility=0.14,
        n_simulations=10_000,
        seed=42,
    )
    vals = result.final_values / 1e7  # in Crores
    print(f"P10 (Worst):  ₹{np.percentile(vals, 10):.2f} Cr")
    print(f"P50 (Median): ₹{np.percentile(vals, 50):.2f} Cr")
    print(f"P90 (Best):   ₹{np.percentile(vals, 90):.2f} Cr")
