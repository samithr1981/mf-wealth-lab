"""
engine/fund_selector.py
-----------------------
Loads real fund data, maps to asset classes,
and selects top-ranked funds per category.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "mutual_fund_final_screener.csv"

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
    "Sectoral/Thematic":                              "Equity",
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
    "Index Funds/ETFs":                               "Passive",
    "Fund of Funds":                                  "Passive",
    "Retirement Fund":                                "Hybrid",
    "Childrens Fund":                                 "Hybrid",
}

FALLBACK_RETURN = {"Equity": 0.130, "Hybrid": 0.105, "Debt": 0.075, "Passive": 0.125, "Other": 0.090}
FALLBACK_VOL    = {"Equity": 0.160, "Hybrid": 0.100, "Debt": 0.030, "Passive": 0.155, "Other": 0.100}

TOP_N = 5


def load_and_clean(csv_path: str = None) -> pd.DataFrame:
    path = csv_path or DATA_PATH
    df = pd.read_csv(path)

    # Drop xlsx artefact columns
    junk = [c for c in df.columns if ".xlsx" in c]
    df.drop(columns=junk, inplace=True, errors="ignore")

    # Asset class mapping
    df["Asset_Class"] = df["Category Name"].map(ASSET_CLASS_MAP).fillna("Other")

    # Best available return
    df["Return_Used"] = df["5Y"].fillna(df["3Y"])
    for ac, ret in FALLBACK_RETURN.items():
        df.loc[df["Return_Used"].isna() & (df["Asset_Class"] == ac), "Return_Used"] = ret

    # Volatility fallback
    df["Vol_Used"] = df["Volatility"]
    for ac, vol in FALLBACK_VOL.items():
        df.loc[df["Vol_Used"].isna() & (df["Asset_Class"] == ac), "Vol_Used"] = vol

    return df


def select_universe(df: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
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
        .agg(mean_return=("Return_Used", "mean"),
             mean_vol=("Vol_Used", "mean"),
             fund_count=("Scheme Name", "count"))
        .reset_index()
    )


if __name__ == "__main__":
    u = get_universe()
    print(f"Universe: {len(u)} funds")
    print(get_asset_class_stats(u).to_string(index=False))
