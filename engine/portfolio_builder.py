"""
engine/portfolio_builder.py
---------------------------
Builds a weighted portfolio from user's allocation preferences.

KEY FEATURE: fund_filter parameter controls how many top funds
per asset class are included in the portfolio.

  fund_filter = 3   →  top 3 funds per asset class  (most concentrated)
  fund_filter = 5   →  top 5 funds per asset class  (default)
  fund_filter = 7   →  top 7 funds per asset class
  fund_filter = 10  →  top 10 funds per asset class (most diversified)

Funds are selected by picking the best fund from each sub-category,
ranked by Composite_Score, until the fund_filter limit is reached.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Literal
import pandas as pd
import numpy as np
from engine.fund_selector import get_universe, get_asset_class_stats

RISK_PROFILES: Dict[str, Dict[str, float]] = {
    "Conservative":    {"Equity": 0.20, "Hybrid": 0.20, "Debt": 0.55, "Passive": 0.05},
    "Moderate":        {"Equity": 0.50, "Hybrid": 0.20, "Debt": 0.25, "Passive": 0.05},
    "Aggressive":      {"Equity": 0.65, "Hybrid": 0.15, "Debt": 0.10, "Passive": 0.10},
    "Very Aggressive": {"Equity": 0.75, "Hybrid": 0.10, "Debt": 0.05, "Passive": 0.10},
}

VALID_FUND_FILTERS = [3, 5, 7, 10]

# Max sub-categories available per asset class (from real data)
MAX_SUBCATS = {
    "Equity":  11,
    "Hybrid":  5,
    "Debt":    17,
    "Passive": 1,   # only 1 sub-cat; handled by taking top N funds within it
}


@dataclass
class PortfolioStats:
    allocation: Dict[str, float]
    expected_return: float
    volatility: float
    top_funds: pd.DataFrame
    asset_stats: pd.DataFrame
    fund_filter: int            # the filter used to build this portfolio


def _pick_top_n_funds(universe: pd.DataFrame, asset_class: str, n: int) -> pd.DataFrame:
    """
    Pick top N funds for an asset class using a diversified sub-category approach:
      - Rank sub-categories by their best fund's Composite_Score
      - Pick 1 fund per sub-category (the best one) in that order
      - Stop when N funds are collected
    This ensures diversification across sub-categories rather than
    clustering all N funds in the single best sub-category.
    """
    ac_funds = universe[universe["Asset_Class"] == asset_class].copy()
    if ac_funds.empty:
        return ac_funds

    # Rank sub-categories by their top fund's score
    subcat_ranking = (
        ac_funds.groupby("Category Name")["Composite_Score"]
        .max()
        .sort_values(ascending=False)
        .index.tolist()
    )

    selected = []
    # Round-robin: 1 fund per sub-cat until we hit N
    # If sub-cats exhausted before N, go to round 2 (2nd best per sub-cat), etc.
    round_num = 0
    while len(selected) < n:
        added_this_round = 0
        for subcat in subcat_ranking:
            if len(selected) >= n:
                break
            subcat_funds = ac_funds[ac_funds["Category Name"] == subcat]
            if round_num < len(subcat_funds):
                candidate = subcat_funds.iloc[[round_num]]
                selected.append(candidate)
                added_this_round += 1
        if added_this_round == 0:
            break   # no more funds available
        round_num += 1

    return pd.concat(selected, ignore_index=True) if selected else ac_funds.head(n)


def build_portfolio(
    risk_profile: str = "Moderate",
    custom_allocation: Optional[Dict[str, float]] = None,
    fund_filter: int = 5,
    csv_path: str = None,
) -> PortfolioStats:
    """
    Build a portfolio.

    Parameters
    ----------
    risk_profile     : one of Conservative / Moderate / Aggressive / Very Aggressive
    custom_allocation: override risk_profile with your own weights
                       e.g. {"Equity": 0.60, "Hybrid": 0.20, "Debt": 0.15, "Passive": 0.05}
    fund_filter      : 3, 5, 7, or 10 — max funds per asset class
    csv_path         : optional path to a different CSV
    """
    if fund_filter not in VALID_FUND_FILTERS:
        raise ValueError(f"fund_filter must be one of {VALID_FUND_FILTERS}, got {fund_filter}")

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

        selected_funds = _pick_top_n_funds(universe, ac, fund_filter)

        if selected_funds.empty:
            r = float(ac_stats.loc[ac, "mean_return"]) if ac in ac_stats.index else 0.10
            v = float(ac_stats.loc[ac, "mean_vol"])    if ac in ac_stats.index else 0.12
        else:
            r = selected_funds["Return_Used"].mean()
            v = selected_funds["Vol_Used"].mean()
            n = len(selected_funds)
            sf = selected_funds.copy()
            sf["Portfolio_Weight"] = round(ac_weight / n, 5)
            sf["AC_Allocation_%"]  = round(ac_weight * 100, 1)
            fund_rows.append(sf)

        blended_return += ac_weight * r
        blended_vol_sq += (ac_weight * v) ** 2

    top_funds   = pd.concat(fund_rows, ignore_index=True) if fund_rows else pd.DataFrame()
    blended_vol = np.sqrt(blended_vol_sq)

    return PortfolioStats(
        allocation=alloc,
        expected_return=round(blended_return, 5),
        volatility=round(blended_vol, 5),
        top_funds=top_funds,
        asset_stats=ac_stats.reset_index(),
        fund_filter=fund_filter,
    )


def compare_fund_filters(
    risk_profile: str = "Moderate",
    custom_allocation: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Run all 4 fund filter levels and return a comparison DataFrame.
    Useful for understanding how concentration affects expected outcomes.
    """
    rows = []
    for ff in VALID_FUND_FILTERS:
        p = build_portfolio(risk_profile, custom_allocation, fund_filter=ff)
        ac_counts = p.top_funds.groupby("Asset_Class")["Scheme Name"].count().to_dict()
        rows.append({
            "Fund Filter":        ff,
            "Total Funds":        len(p.top_funds),
            "Equity Funds":       ac_counts.get("Equity",  0),
            "Hybrid Funds":       ac_counts.get("Hybrid",  0),
            "Debt Funds":         ac_counts.get("Debt",    0),
            "Passive Funds":      ac_counts.get("Passive", 0),
            "Exp. Return":        f"{p.expected_return:.2%}",
            "Volatility":         f"{p.volatility:.2%}",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("FUND FILTER COMPARISON — Moderate Profile")
    print("=" * 70)
    df = compare_fund_filters("Moderate")
    print(df.to_string(index=False))

    print()
    for ff in VALID_FUND_FILTERS:
        print(f"\n{'─'*70}")
        print(f"TOP {ff} FUNDS PER ASSET CLASS — Moderate Profile")
        print(f"{'─'*70}")
        p = build_portfolio("Moderate", fund_filter=ff)
        cols = ["Asset_Class", "Category Name", "Scheme Name",
                "Return_Used", "Vol_Used", "Portfolio_Weight"]
        cols = [c for c in cols if c in p.top_funds.columns]
        df_show = p.top_funds[cols].copy()
        df_show["Return_Used"]      = df_show["Return_Used"].map("{:.1%}".format)
        df_show["Vol_Used"]         = df_show["Vol_Used"].map("{:.1%}".format)
        df_show["Portfolio_Weight"] = df_show["Portfolio_Weight"].map("{:.2%}".format)
        print(df_show.to_string(index=False))
