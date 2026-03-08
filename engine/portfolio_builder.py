"""
engine/portfolio_builder.py
---------------------------
Builds a weighted portfolio from user's allocation preferences.
Distributes weight across TOP 5 funds per sub-category only.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd
import numpy as np
from engine.fund_selector import get_universe, get_asset_class_stats

RISK_PROFILES: Dict[str, Dict[str, float]] = {
    "Conservative":    {"Equity": 0.20, "Hybrid": 0.20, "Debt": 0.55, "Passive": 0.05},
    "Moderate":        {"Equity": 0.50, "Hybrid": 0.20, "Debt": 0.25, "Passive": 0.05},
    "Aggressive":      {"Equity": 0.65, "Hybrid": 0.15, "Debt": 0.10, "Passive": 0.10},
    "Very Aggressive": {"Equity": 0.75, "Hybrid": 0.10, "Debt": 0.05, "Passive": 0.10},
}

# Within each asset class, how many sub-categories to pick (by rank)
# and how many top funds per sub-category
TOP_SUBCATEGORIES = {
    "Equity":  {"n_subcat": 6,  "n_funds": 1},  # 6 sub-cats × 1 fund = 6 equity funds
    "Hybrid":  {"n_subcat": 3,  "n_funds": 1},  # 3 sub-cats × 1 fund = 3 hybrid funds
    "Debt":    {"n_subcat": 5,  "n_funds": 1},  # 5 sub-cats × 1 fund = 5 debt funds
    "Passive": {"n_subcat": 3,  "n_funds": 1},  # 3 sub-cats × 1 fund = 3 passive funds
}


@dataclass
class PortfolioStats:
    allocation: Dict[str, float]
    expected_return: float
    volatility: float
    top_funds: pd.DataFrame
    asset_stats: pd.DataFrame


def _pick_top_funds_for_class(universe: pd.DataFrame, asset_class: str) -> pd.DataFrame:
    """
    For a given asset class, pick the single best fund from each of
    the top-ranked sub-categories (by median Composite_Score of the sub-cat).
    This gives a well-diversified but compact selection.
    """
    ac_funds = universe[universe["Asset_Class"] == asset_class].copy()
    if ac_funds.empty:
        return ac_funds

    cfg = TOP_SUBCATEGORIES.get(asset_class, {"n_subcat": 5, "n_funds": 1})

    # Rank sub-categories by their best fund's Composite_Score
    subcat_score = (
        ac_funds.groupby("Category Name")["Composite_Score"]
        .max()
        .sort_values(ascending=False)
    )
    top_subcats = subcat_score.head(cfg["n_subcat"]).index.tolist()

    selected = []
    for subcat in top_subcats:
        subcat_funds = ac_funds[ac_funds["Category Name"] == subcat]
        selected.append(subcat_funds.head(cfg["n_funds"]))

    return pd.concat(selected, ignore_index=True) if selected else ac_funds.head(5)


def build_portfolio(
    risk_profile: str = "Moderate",
    custom_allocation: Optional[Dict[str, float]] = None,
    csv_path: str = None,
) -> PortfolioStats:
    alloc = custom_allocation or RISK_PROFILES.get(risk_profile, RISK_PROFILES["Moderate"])
    total = sum(alloc.values())
    alloc = {k: v / total for k, v in alloc.items()}

    universe = get_universe(csv_path)
    ac_stats  = get_asset_class_stats(universe).set_index("Asset_Class")

    blended_return = 0.0
    blended_vol_sq = 0.0

    fund_rows = []
    for ac, ac_weight in alloc.items():
        if ac_weight == 0:
            continue

        # Pick compact, diversified fund set for this asset class
        selected_funds = _pick_top_funds_for_class(universe, ac)

        if selected_funds.empty:
            # Fallback to asset class stats
            r = ac_stats.loc[ac, "mean_return"] if ac in ac_stats.index else 0.10
            v = ac_stats.loc[ac, "mean_vol"]    if ac in ac_stats.index else 0.12
        else:
            r = selected_funds["Return_Used"].mean()
            v = selected_funds["Vol_Used"].mean()
            n = len(selected_funds)
            per_fund_weight = ac_weight / n
            sf = selected_funds.copy()
            sf["Portfolio_Weight"]  = round(per_fund_weight, 5)
            sf["AC_Allocation_%"]   = round(ac_weight * 100, 1)
            fund_rows.append(sf)

        blended_return += ac_weight * r
        blended_vol_sq += (ac_weight * v) ** 2

    blended_vol = np.sqrt(blended_vol_sq)
    top_funds   = pd.concat(fund_rows, ignore_index=True) if fund_rows else pd.DataFrame()

    return PortfolioStats(
        allocation=alloc,
        expected_return=round(blended_return, 5),
        volatility=round(blended_vol, 5),
        top_funds=top_funds,
        asset_stats=ac_stats.reset_index(),
    )


if __name__ == "__main__":
    print("=== Portfolio Stats by Risk Profile ===\n")
    for profile in RISK_PROFILES:
        p = build_portfolio(profile)
        print(f"{profile:20s} → Return: {p.expected_return:.2%}  Vol: {p.volatility:.2%}  Funds: {len(p.top_funds)}")
    print()

    print("=== Aggressive Portfolio — Fund List ===")
    p = build_portfolio("Aggressive")
    cols = ["Scheme Name", "Asset_Class", "Category Name", "Return_Used", "Vol_Used", "Portfolio_Weight"]
    cols = [c for c in cols if c in p.top_funds.columns]
    print(p.top_funds[cols].to_string(index=False))
