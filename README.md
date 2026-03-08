# 🚀 MF Wealth Lab — Mutual Fund Portfolio Simulator

A full-stack, institutional-grade **Monte Carlo wealth simulator** built on real Indian mutual fund data (890 schemes). Simulates 10,000 future wealth paths based on your SIP, time horizon, and risk profile.

---

## 📐 Architecture

```
mutual_fund_final_screener.csv
         ↓
  engine/fund_selector.py      ← Top fund universe per category
         ↓
  engine/portfolio_builder.py  ← Asset allocation + fund weights
         ↓
  engine/simulator.py          ← Monte Carlo (10,000 paths)
         ↓
  engine/wealth_outcomes.py    ← Percentile outcomes + FIRE targets
         ↓
  api/main.py                  ← FastAPI REST layer
         ↓
  frontend/app.py              ← Streamlit dashboard (interactive UI)
```

---

## Features

- **Real fund data** — 890 schemes across 38 categories (Equity, Hybrid, Debt, Passive)
- **Composite scoring** — ranks funds on return, risk-adjusted performance and consistency
- **Monte Carlo engine** — 10,000 simulations, monthly compounding with SIP
- **Wealth cone** — P10 / P50 / P90 outcome bands
- **FIRE calculator** — how many years to reach your target corpus
- **FastAPI backend** — clean REST API, Swagger docs at `/docs`
- **Streamlit frontend** — sliders, charts, downloadable results

---

## Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/mf-wealth-lab.git
cd mf-wealth-lab

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Streamlit UI (standalone — no API needed)
streamlit run frontend/app.py

# 4. OR run FastAPI backend separately
uvicorn api.main:app --reload
# Then open http://localhost:8000/docs
```

---

## Project Structure

```
mf_wealth_lab/
├── data/
│   └── mutual_fund_final_screener.csv   # 890 real fund records
├── engine/
│   ├── fund_selector.py                 # Fund universe builder
│   ├── portfolio_builder.py             # Allocation + weight engine
│   ├── simulator.py                     # Monte Carlo core
│   └── wealth_outcomes.py              # Outcome metrics + FIRE
├── api/
│   └── main.py                          # FastAPI app
├── frontend/
│   └── app.py                           # Streamlit dashboard
├── notebooks/
│   └── exploration.ipynb                # EDA notebook
├── requirements.txt
└── README.md
```

---

## Scoring Methodology

```
Composite Score = 0.40 x (5Y Return z-score)
               + 0.30 x (3Y Return z-score)
               + 0.20 x (Sharpe z-score)
               - 0.10 x (Volatility z-score)
```

Funds with missing 5Y data use 3Y return as proxy.

---

## Risk Profiles

| Profile         | Equity | Hybrid | Debt | Passive |
|-----------------|--------|--------|------|---------|
| Conservative    |  20%   |  20%   | 55%  |   5%    |
| Moderate        |  50%   |  20%   | 25%  |   5%    |
| Aggressive      |  65%   |  15%   | 10%  |  10%    |
| Very Aggressive |  75%   |  10%   |  5%  |  10%    |

---

## License

MIT
