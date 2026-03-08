"""
engine/portfolio_builder.py
---------------------------
Builds weighted portfolio from user's allocation preferences.
Returns blended expected return and volatility for simulation.
"""

from dataclasses import dataclass
from typing import Dict
import pandas as pd
import numpy as np
from engine.fund_selector import get_universe, get_asset_class_stats

# ── Risk profiles ──────────────────────────────────────────────────────────────
RISK_PROFILES: Dict[str, Dict[str, float]] = {
    "Conservative":    {"Equity": 0.20, "Hybrid": 0.20, "Debt": 0.55, "Passive": 0.05},
    "Moderate":        {"Equity": 0.50, "Hybrid": 0.20, "Debt": 0.25, "Passive": 0.05},
    "Aggressive":      {"Equity": 0.65, "Hybrid": 0.15, "Debt": 0.10, "Passive": 0.10},
    "Very Aggressive": {"Equity": 0.75, "Hybrid": 0.10, "Debt": 0.05, "Passive": 0.10},
}


@dataclass
class PortfolioStats:
    allocation: Dict[str, float]        # asset class → weight
    expected_return: float              # annualised blended return
    volatility: float                   # annualised blended volatility
    top_funds: pd.DataFrame             # fund-level breakdown with weights
    asset_stats: pd.DataFrame           # asset class stats


def build_portfolio(
    risk_profile: str = "Moderate",
    custom_allocation: Dict[str, float] = None,
    csv_path: str = None,
) -> PortfolioStats:
    """
    Build a portfolio given a risk profile or custom allocation dict.
    custom_allocation example: {"Equity": 0.60, "Hybrid": 0.20, "Debt": 0.15, "Passive": 0.05}
    """
    alloc = custom_allocation or RISK_PROFILES.get(risk_profile, RISK_PROFILES["Moderate"])

    # Normalise weights to 1.0
    total = sum(alloc.values())
    alloc = {k: v / total for k, v in alloc.items()}

    universe = get_universe(csv_path)
    ac_stats = get_asset_class_stats(universe)
    ac_stats = ac_stats.set_index("Asset_Class")

    # Blended portfolio return and volatility
    blended_return = 0.0
    blended_vol_sq = 0.0  # simple weighted variance (no cross-correlation for now)

    for ac, weight in alloc.items():
        if ac in ac_stats.index:
            r = ac_stats.loc[ac, "mean_return"]
            v = ac_stats.loc[ac, "mean_vol"]
        else:
            r, v = 0.10, 0.12   # safe default
        blended_return += weight * r
        blended_vol_sq += (weight * v) ** 2

    blended_vol = np.sqrt(blended_vol_sq)

    # Fund-level weights
    fund_rows = []
    for ac, ac_weight in alloc.items():
        funds_in_ac = universe[universe["Asset_Class"] == ac]
        if len(funds_in_ac) == 0:
            continue
        per_fund_weight = ac_weight / len(funds_in_ac)
        funds_in_ac = funds_in_ac.copy()
        funds_in_ac["Portfolio_Weight"] = round(per_fund_weight, 5)
        funds_in_ac["AC_Allocation_%"] = round(ac_weight * 100, 1)
        fund_rows.append(funds_in_ac)

    top_funds = pd.concat(fund_rows, ignore_index=True) if fund_rows else pd.DataFrame()

    return PortfolioStats(
        allocation=alloc,
        expected_return=round(blended_return, 5),
        volatility=round(blended_vol, 5),
        top_funds=top_funds,
        asset_stats=ac_stats.reset_index(),
    )


if __name__ == "__main__":
    for profile in RISK_PROFILES:
        p = build_portfolio(profile)
        print(f"{profile:18s} → Return: {p.expected_return:.1%}  Vol: {p.volatility:.1%}")
