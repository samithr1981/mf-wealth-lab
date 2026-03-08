"""
engine/config.py
Central configuration for the MF Wealth Lab.
"""

from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_PATH  = BASE_DIR / "data" / "mutual_fund_final_screener.csv"

# ── Fund selection ────────────────────────────────────────────────────────────
TOP_N_PER_CATEGORY = 5      # top N funds selected per sub-category

# ── Simulation ────────────────────────────────────────────────────────────────
N_SIMULATIONS   = 10_000
RISK_FREE_RATE  = 0.065     # 6.5% p.a. (RBI repo-linked)

# ── Default portfolio allocation (must sum to 1.0) ────────────────────────────
DEFAULT_ALLOCATION = {
    "Equity":  0.60,
    "Hybrid":  0.20,
    "Debt":    0.15,
    "Passive": 0.05,
}

# ── Asset class mapping (Category Name → Asset Class) ────────────────────────
ASSET_CLASS_MAP = {
    "Large Cap Fund":                                  "Equity",
    "Large & Mid Cap Fund":                            "Equity",
    "Mid Cap Fund":                                    "Equity",
    "Small Cap Fund":                                  "Equity",
    "Flexi Cap Fund":                                  "Equity",
    "Multi Cap Fund":                                  "Equity",
    "Focused Fund":                                    "Equity",
    "ELSS":                                            "Equity",
    "Contra Fund":                                     "Equity",
    "Dividend Yield Fund":                             "Equity",
    "Value Fund":                                      "Equity",
    "Sectoral/Thematic":                               "Equity",
    "Aggressive Hybrid Fund":                          "Hybrid",
    "Conservative Hybrid Fund":                        "Hybrid",
    "Dynamic Asset Allocation or Balanced Advantage":  "Hybrid",
    "Multi Asset Allocation":                          "Hybrid",
    "Equity Savings":                                  "Hybrid",
    "Arbitrage Fund":                                  "Debt",
    "Banking and PSU Fund":                            "Debt",
    "Corporate Bond Fund":                             "Debt",
    "Credit Risk Fund":                                "Debt",
    "Dynamic Bond Fund":                               "Debt",
    "Floater Fund":                                    "Debt",
    "Gilt Fund":                                       "Debt",
    "Gilt Fund with 10 year constant duration":        "Debt",
    "Liquid Fund":                                     "Debt",
    "Long Duration Fund":                              "Debt",
    "Low Duration Fund":                               "Debt",
    "Medium Duration Fund":                            "Debt",
    "Medium to Long Duration Fund":                    "Debt",
    "Money Market Fund":                               "Debt",
    "Overnight Fund":                                  "Debt",
    "Short Duration Fund":                             "Debt",
    "Ultra Short Duration Fund":                       "Debt",
    "Index Funds/ETFs":                                "Passive",
    "Fund of Funds":                                   "Other",
    "Childrens Fund":                                  "Other",
    "Retirement Fund":                                 "Other",
}
