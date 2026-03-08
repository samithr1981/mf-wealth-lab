"""
Generate a sample mutual fund dataset for testing.
Replace this with your real AMC factsheet data.
"""

import pandas as pd
import numpy as np

np.random.seed(42)

CATEGORIES = {
    "Large Cap": ("Equity", 0.13, 0.14),
    "Mid Cap": ("Equity", 0.16, 0.20),
    "Small Cap": ("Equity", 0.18, 0.25),
    "Flexi Cap": ("Equity", 0.14, 0.16),
    "ELSS": ("Equity", 0.14, 0.17),
    "Aggressive Hybrid": ("Hybrid", 0.12, 0.13),
    "Balanced Hybrid": ("Hybrid", 0.10, 0.10),
    "Arbitrage": ("Debt", 0.065, 0.02),
    "Liquid": ("Debt", 0.07, 0.005),
    "Short Duration": ("Debt", 0.075, 0.03),
    "Corporate Bond": ("Debt", 0.08, 0.04),
    "Nifty 50 Index": ("Passive", 0.13, 0.14),
    "Nifty Next 50 Index": ("Passive", 0.14, 0.18),
    "Nifty Midcap 150 Index": ("Passive", 0.15, 0.20),
}

AMCS = ["Axis MF", "SBI MF", "ICICI Pru", "HDFC MF", "Mirae Asset",
        "Kotak MF", "DSP MF", "Nippon MF", "Franklin", "UTI MF"]

rows = []
for category, (asset_class, base_ret, base_vol) in CATEGORIES.items():
    for amc in AMCS:
        ret_5y = base_ret + np.random.normal(0, 0.02)
        ret_3y = ret_5y + np.random.normal(0, 0.015)
        vol    = base_vol + np.random.normal(0, 0.01)
        vol    = max(vol, 0.001)
        sharpe = (ret_5y - 0.065) / vol
        aum    = np.random.uniform(500, 50000)

        rows.append({
            "Scheme Name":    f"{amc} {category} Fund",
            "AMC":            amc,
            "Category Name":  category,
            "Asset_Class":    asset_class,
            "AuM (Cr)":       round(aum, 1),
            "3Y":             round(ret_3y, 4),
            "5Y":             round(ret_5y, 4),
            "Volatility":     round(vol, 4),
            "Sharpe_Ratio":   round(sharpe, 3),
        })

df = pd.DataFrame(rows)

# Composite Score: 40% 5Y return + 30% 3Y return + 20% Sharpe - 10% volatility
def zscore(s):
    return (s - s.mean()) / s.std()

df["Composite_Score"] = (
    0.40 * zscore(df["5Y"]) +
    0.30 * zscore(df["3Y"]) +
    0.20 * zscore(df["Sharpe_Ratio"]) -
    0.10 * zscore(df["Volatility"])
).round(4)

df.to_csv("mutual_fund_screener.csv", index=False)
print(f"Generated {len(df)} fund records → mutual_fund_screener.csv")
print(df.head())
