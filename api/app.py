"""
api/app.py
----------
FastAPI REST backend exposing the simulation engine.

Usage:
    uvicorn api.app:app --reload --port 8000
    Then visit: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.simulate import run_full_simulation
from engine.fund_selector import get_universe

app = FastAPI(
    title="MF Wealth Lab API",
    description="Indian Mutual Fund Monte Carlo Wealth Simulator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    monthly_sip:     float = Field(50000,   gt=0,    description="Monthly SIP in ₹")
    years:           int   = Field(20,      ge=1, le=40, description="Investment horizon in years")
    initial_lumpsum: float = Field(0,       ge=0,    description="One-time lumpsum in ₹")
    inflation_rate:  float = Field(0.06,    ge=0, le=0.20)
    equity_pct:      float = Field(60,      ge=0, le=100)
    hybrid_pct:      float = Field(20,      ge=0, le=100)
    debt_pct:        float = Field(15,      ge=0, le=100)
    passive_pct:     float = Field(5,       ge=0, le=100)
    top_n:           int   = Field(5,       ge=1, le=10)
    n_sims:          int   = Field(10000,   ge=1000, le=50000)


class SimulationResponse(BaseModel):
    portfolio_params: Dict
    outcomes:         Dict
    cone:             Dict
    portfolio_table:  list


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "MF Wealth Lab API v1.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


@app.post("/simulate", response_model=SimulationResponse, tags=["Simulation"])
def simulate(req: SimulationRequest):
    """
    Run a full Monte Carlo wealth simulation.

    Supply your SIP, horizon, and asset class allocation (percentages).
    Returns percentile outcomes, wealth cone paths, and portfolio composition.
    """
    total_pct = req.equity_pct + req.hybrid_pct + req.debt_pct + req.passive_pct
    if total_pct == 0:
        raise HTTPException(400, "At least one asset class must have non-zero allocation.")

    allocation = {
        "Equity":  req.equity_pct  / 100,
        "Hybrid":  req.hybrid_pct  / 100,
        "Debt":    req.debt_pct    / 100,
        "Passive": req.passive_pct / 100,
    }

    try:
        result = run_full_simulation(
            monthly_sip     = req.monthly_sip,
            years           = req.years,
            allocation      = allocation,
            initial_lumpsum = req.initial_lumpsum,
            inflation_rate  = req.inflation_rate,
            n_sims          = req.n_sims,
            top_n           = req.top_n,
        )
    except Exception as e:
        raise HTTPException(500, str(e))

    return result


@app.get("/funds", tags=["Data"])
def get_funds(
    asset_class: Optional[str] = None,
    top_n:       int           = 5,
):
    """
    Return the top fund universe used in simulations.
    Filter by asset_class: Equity | Hybrid | Debt | Passive
    """
    universe = get_universe(top_n=top_n)
    if asset_class:
        universe = universe[universe["Asset_Class"] == asset_class]

    cols = ["Scheme Name", "Category Name", "Asset_Class",
            "AuM (Cr)", "5Y", "Volatility", "Composite_Score"]
    return universe[cols].to_dict(orient="records")


@app.get("/categories", tags=["Data"])
def get_categories():
    """Return all fund categories with their asset class mapping."""
    from engine.config import ASSET_CLASS_MAP
    return [{"category": k, "asset_class": v} for k, v in ASSET_CLASS_MAP.items()]
