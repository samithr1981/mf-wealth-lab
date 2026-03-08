"""
engine/wealth_outcomes.py
-------------------------
Computes percentile outcomes, FIRE year, and milestone projections
from a SimulationResult.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from engine.simulator import SimulationResult, run_simulation


@dataclass
class WealthOutcome:
    worst_case: float       # P10
    median: float           # P50
    best_case: float        # P90
    total_invested: float
    median_gain: float      # absolute
    median_xirr_approx: float
    fire_year: Optional[int]         # year portfolio crosses target_corpus
    yearly_milestones: pd.DataFrame  # year, p10, p50, p90
    probability_of_target: Optional[float]  # % sims that beat target


def compute_outcomes(
    result: SimulationResult,
    target_corpus: float = None,
) -> WealthOutcome:

    total_invested = result.sip * result.months

    # Percentiles of final wealth
    p10 = float(np.percentile(result.final_values, 10))
    p50 = float(np.percentile(result.final_values, 50))
    p90 = float(np.percentile(result.final_values, 90))

    # Approximate XIRR for median outcome (simple CAGR proxy)
    years = result.months / 12
    median_xirr = (p50 / total_invested) ** (1 / years) - 1 if total_invested > 0 else 0

    # Yearly milestones
    milestone_rows = []
    for yr in range(1, int(years) + 1):
        idx = yr * 12
        slice_ = result.paths[:, idx]
        milestone_rows.append({
            "Year": yr,
            "P10 (₹ Cr)":  round(np.percentile(slice_, 10) / 1e7, 2),
            "P50 (₹ Cr)":  round(np.percentile(slice_, 50) / 1e7, 2),
            "P90 (₹ Cr)":  round(np.percentile(slice_, 90) / 1e7, 2),
        })
    milestones = pd.DataFrame(milestone_rows)

    # FIRE: first year median path crosses target
    fire_year = None
    prob_target = None
    if target_corpus:
        median_path = np.percentile(result.paths, 50, axis=0)
        crossings = np.where(median_path >= target_corpus)[0]
        if len(crossings):
            fire_year = int(crossings[0] / 12)
        prob_target = float((result.final_values >= target_corpus).mean())

    return WealthOutcome(
        worst_case=p10,
        median=p50,
        best_case=p90,
        total_invested=total_invested,
        median_gain=p50 - total_invested,
        median_xirr_approx=median_xirr,
        fire_year=fire_year,
        yearly_milestones=milestones,
        probability_of_target=prob_target,
    )


if __name__ == "__main__":
    from engine.portfolio_builder import build_portfolio

    port = build_portfolio("Aggressive")
    sim  = run_simulation(
        sip=25_000,
        years=20,
        expected_return=port.expected_return,
        volatility=port.volatility,
        seed=42,
    )
    out = compute_outcomes(sim, target_corpus=1e8)

    print(f"\n=== Wealth Outcomes (Aggressive, ₹25k SIP, 20Y) ===")
    print(f"  Worst (P10) : ₹{out.worst_case/1e7:.2f} Cr")
    print(f"  Median (P50): ₹{out.median/1e7:.2f} Cr")
    print(f"  Best   (P90): ₹{out.best_case/1e7:.2f} Cr")
    print(f"  Total Invested: ₹{out.total_invested/1e7:.2f} Cr")
    print(f"  Approx XIRR   : {out.median_xirr_approx:.1%}")
    if out.fire_year:
        print(f"  FIRE Year (₹1 Cr target): Year {out.fire_year}")
    print(f"  P(beat ₹1 Cr): {out.probability_of_target:.1%}")
    print()
    print(out.yearly_milestones.to_string(index=False))
