"""
api/main.py
-----------
FastAPI backend — exposes simulation as REST endpoints.
Run: uvicorn api.main:app --reload
Docs: http://localhost:8000/docs
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import numpy as np

from engine.portfolio_builder import build_portfolio, RISK_PROFILES
from engine.simulator import run_simulation
from engine.wealth_outcomes import compute_outcomes

app = FastAPI(
    title="MF Wealth Lab API",
    description="Monte Carlo mutual fund portfolio simulator built on 890 real Indian fund records.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ─────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    sip: float = Field(25000, ge=500, le=500000, description="Monthly SIP in ₹")
    years: int = Field(20, ge=1, le=40, description="Investment horizon in years")
    risk_profile: str = Field("Moderate", description="Conservative / Moderate / Aggressive / Very Aggressive")
    initial_corpus: float = Field(0, ge=0, description="Lump sum already invested")
    target_corpus: Optional[float] = Field(None, description="FIRE target in ₹ (optional)")
    custom_allocation: Optional[Dict[str, float]] = Field(
        None,
        description='Custom weights e.g. {"Equity":0.60,"Hybrid":0.20,"Debt":0.15,"Passive":0.05}'
    )
    n_simulations: int = Field(10000, ge=1000, le=50000)


class SimulateResponse(BaseModel):
    worst_case_cr: float
    median_cr: float
    best_case_cr: float
    total_invested_cr: float
    median_gain_cr: float
    median_xirr_pct: float
    fire_year: Optional[int]
    probability_of_target_pct: Optional[float]
    expected_return_pct: float
    volatility_pct: float
    allocation: Dict[str, float]
    yearly_milestones: list


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "MF Wealth Lab API is running"}


@app.get("/profiles", tags=["Config"])
def get_profiles():
    """Return available risk profiles and their asset allocations."""
    return RISK_PROFILES


@app.post("/simulate", response_model=SimulateResponse, tags=["Simulation"])
def simulate(req: SimulateRequest):
    """Run Monte Carlo simulation and return wealth outcomes."""
    portfolio = build_portfolio(
        risk_profile=req.risk_profile,
        custom_allocation=req.custom_allocation,
    )
    sim = run_simulation(
        sip=req.sip,
        years=req.years,
        expected_return=portfolio.expected_return,
        volatility=portfolio.volatility,
        n_simulations=req.n_simulations,
        initial_corpus=req.initial_corpus,
    )
    out = compute_outcomes(sim, target_corpus=req.target_corpus)

    return SimulateResponse(
        worst_case_cr=round(out.worst_case / 1e7, 3),
        median_cr=round(out.median / 1e7, 3),
        best_case_cr=round(out.best_case / 1e7, 3),
        total_invested_cr=round(out.total_invested / 1e7, 3),
        median_gain_cr=round(out.median_gain / 1e7, 3),
        median_xirr_pct=round(out.median_xirr_approx * 100, 2),
        fire_year=out.fire_year,
        probability_of_target_pct=(
            round(out.probability_of_target * 100, 1) if out.probability_of_target is not None else None
        ),
        expected_return_pct=round(portfolio.expected_return * 100, 2),
        volatility_pct=round(portfolio.volatility * 100, 2),
        allocation={k: round(v * 100, 1) for k, v in portfolio.allocation.items()},
        yearly_milestones=out.yearly_milestones.to_dict(orient="records"),
    )


@app.get("/top-funds", tags=["Funds"])
def top_funds(
    asset_class: Optional[str] = Query(None, description="Filter by Equity/Hybrid/Debt/Passive"),
    top_n: int = Query(10, ge=1, le=50),
):
    """Return top-ranked funds from the screener universe."""
    from engine.fund_selector import get_universe
    universe = get_universe()
    if asset_class:
        universe = universe[universe["Asset_Class"] == asset_class]
    cols = ["Scheme Name", "Category Name", "Asset_Class", "AuM (Cr)",
            "3Y", "5Y", "Volatility", "Sharpe_Ratio", "Composite_Score"]
    cols = [c for c in cols if c in universe.columns]
    return universe[cols].head(top_n).to_dict(orient="records")
