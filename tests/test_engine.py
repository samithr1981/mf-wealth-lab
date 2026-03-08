"""
tests/test_engine.py
Smoke tests for the simulation engine.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest


def test_monte_carlo_runs():
    from engine.monte_carlo import run_simulation, compute_outcomes
    final, paths = run_simulation(0.12, 0.14, 50000, 10, seed=42, n_sims=1000)
    assert len(final) == 1000
    assert paths.shape == (1000, 120)
    assert np.all(final > 0)


def test_outcomes_sensible():
    from engine.monte_carlo import run_simulation, compute_outcomes
    final, _ = run_simulation(0.12, 0.14, 50000, 20, seed=42, n_sims=1000)
    out = compute_outcomes(final, 20, 50000)
    assert out["p10_nominal"] < out["p50_nominal"] < out["p90_nominal"]
    assert 0 <= out["prob_5x"] <= 100


def test_fund_selector_loads():
    from engine.fund_selector import get_universe
    u = get_universe()
    assert len(u) > 10
    assert "Asset_Class" in u.columns
    assert set(u["Asset_Class"].unique()).issubset(
        {"Equity", "Hybrid", "Debt", "Passive", "Other"}
    )


def test_portfolio_builder():
    from engine.portfolio_builder import build_portfolio, portfolio_params
    port = build_portfolio({"Equity": 0.6, "Hybrid": 0.2, "Debt": 0.15, "Passive": 0.05})
    params = portfolio_params(port)
    assert params["n_funds"] > 0
    assert 0 < params["expected_return"] < 0.5
    assert 0 < params["volatility"] < 0.5


def test_full_simulation():
    from engine.simulate import run_full_simulation
    result = run_full_simulation(50000, 10, n_sims=500, seed=42)
    assert "outcomes" in result
    assert "cone" in result
    assert "portfolio_table" in result
    assert result["outcomes"]["p50_nominal"] > result["outcomes"]["p10_nominal"]
