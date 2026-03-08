"""
engine/fund_selector.py
-----------------------
Loads real fund data, maps to asset classes,
and selects top 5 funds per sub-category.

Fixes applied:
  1. Index Funds/ETFs filtered to domestic broad-market only
     (excludes Gold, Silver, US/NASDAQ/S&P, Sectoral ETFs)
  2. Fund of Funds excluded from Passive (mostly international wrappers)
  3. Sectoral/Thematic excluded from core Equity (too concentrated)
  4. Retirement/Childrens funds excluded (hybrid wrappers with lock-in)
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "mutual_fund_final_screener.csv"

# Broad asset class mapping
ASSET_CLASS_MAP = {
    "Large Cap Fund":                                 "Equity",
    "Mid Cap Fund":                                   "Equity",
    "Small Cap Fund":                                 "Equity",
    "Flexi Cap Fund":                                 "Equity",
    "Multi Cap Fund":                                 "Equity",
    "Large & Mid Cap Fund":                           "Equity",
    "ELSS":                                           "Equity",
    "Focused Fund":                                   "Equity",
    "Dividend Yield Fund":                            "Equity",
    "Value Fund":                                     "Equity",
    "Contra Fund":                                    "Equity",
    "Aggressive Hybrid Fund":                         "Hybrid",
    "Conservative Hybrid Fund":                       "Hybrid",
    "Dynamic Asset Allocation or Balanced Advantage": "Hybrid",
    "Multi Asset Allocation":                         "Hybrid",
    "Equity Savings":                                 "Hybrid",
    "Arbitrage Fund":                                 "Debt",
    "Liquid Fund":                                    "Debt",
    "Ultra Short Duration Fund":                      "Debt",
    "Low Duration Fund":                              "Debt",
    "Short Duration Fund":                            "Debt",
    "Medium Duration Fund":                           "Debt",
    "Medium to Long Duration Fund":                   "Debt",
    "Long Duration Fund":                             "Debt",
    "Dynamic Bond Fund":                              "Debt",
    "Corporate Bond Fund":                            "Debt",
    "Banking and PSU Fund":                           "Debt",
    "Gilt Fund":                                      "Debt",
    "Gilt Fund with 10 year constant duration":       "Debt",
    "Floater Fund":                                   "Debt",
    "Credit Risk Fund":                               "Debt",
    "Money Market Fund":                              "Debt",
    "Overnight Fund":                                 "Debt",
    "Index Funds/ETFs":                               "Passive",   # filtered below
    # Excluded from core universe:
    # "Sectoral/Thematic" → Other (too concentrated, survivorship bias)
    # "Fund of Funds"     → Other (mostly international wrappers)
    # "Retirement Fund"   → Other (lock-in products)
    # "Childrens Fund"    → Other (lock-in products)
}

# Keywords that identify NON-domestic-broad-market index funds
# Any Index Fund/ETF whose name contains these strings is excluded from Passive
PASSIVE_EXCLUSION_KEYWORDS = [
    "gold", "silver", "nasdaq", "s&p", "fang", "us equity", "global",
    "international", "world", "china", "europe", "japan", "commodity",
    "oil", "energy", "auto", "bank", "pharma", "it ", "infra",
    "financial", "consumption", "realty", "media", "fmcg", "metal",
    "manufacturing", "psu", "cpse", "bharat 22", "defence", "healthcare",
    "artificial intelligence", "technology etf", "innovation",
]

FALLBACK_RETURN = {
    "Equity":  0.130,
    "Hybrid":  0.105,
    "Debt":    0.075,
    "Passive": 0.125,
    "Other":   0.090,
}
FALLBACK_VOL = {
    "Equity":  0.160,
    "Hybrid":  0.100,
    "Debt":    0.030,
    "Passive": 0.150,
    "Other":   0.100,
}

TOP_N = 5   # top funds per sub-category


def _is_domestic_broad_passive(scheme_name: str) -> bool:
    """Return True only for broad domestic index funds (Nifty 50, Sensex, Nifty Next 50 etc.)"""
    name_lower = scheme_name.lower()
    for kw in PASSIVE_EXCLUSION_KEYWORDS:
        if kw in name_lower:
            return False
    return True


def load_and_clean(csv_path: str = None) -> pd.DataFrame:
    path = csv_path or DATA_PATH
    df = pd.read_csv(path)

    # Drop xlsx artefact columns
    junk = [c for c in df.columns if ".xlsx" in c]
    df.drop(columns=junk, inplace=True, errors="ignore")

    # Asset class mapping
    df["Asset_Class"] = df["Category Name"].map(ASSET_CLASS_MAP).fillna("Other")

    # Filter Index Funds/ETFs: keep only domestic broad-market passives
    passive_mask = df["Asset_Class"] == "Passive"
    df.loc[passive_mask & ~df["Scheme Name"].apply(_is_domestic_broad_passive), "Asset_Class"] = "Other"

    # Best available return (5Y preferred, fallback 3Y, then category mean)
    df["Return_Used"] = df["5Y"].fillna(df["3Y"])
    for ac, ret in FALLBACK_RETURN.items():
        df.loc[df["Return_Used"].isna() & (df["Asset_Class"] == ac), "Return_Used"] = ret

    # Volatility fallback
    df["Vol_Used"] = df["Volatility"]
    for ac, vol in FALLBACK_VOL.items():
        df.loc[df["Vol_Used"].isna() & (df["Asset_Class"] == ac), "Vol_Used"] = vol

    return df


def select_universe(df: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """
    Top N funds per sub-category, ranked by Composite_Score.
    Excludes 'Other' asset class entirely.
    """
    return (
        df[df["Asset_Class"] != "Other"]
        .sort_values("Composite_Score", ascending=False)
        .groupby("Category Name")
        .head(top_n)
        .reset_index(drop=True)
    )


def get_universe(csv_path: str = None) -> pd.DataFrame:
    return select_universe(load_and_clean(csv_path))


def get_asset_class_stats(universe: pd.DataFrame) -> pd.DataFrame:
    return (
        universe.groupby("Asset_Class")
        .agg(
            mean_return=("Return_Used", "mean"),
            mean_vol=("Vol_Used", "mean"),
            fund_count=("Scheme Name", "count"),
        )
        .reset_index()
    )


if __name__ == "__main__":
    u = get_universe()
    print(f"Clean universe: {len(u)} funds\n")
    print(get_asset_class_stats(u).to_string(index=False))
    print(f"\nPassive funds in universe:")
    print(u[u["Asset_Class"] == "Passive"][["Scheme Name", "Return_Used", "Vol_Used"]].to_string(index=False))
