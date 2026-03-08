"""
engine/simulate.py
------------------
High-level orchestrator: wires together fund selection,
portfolio building, and Monte Carlo simulation into a
single callable function used by the API and frontend.
"""

from typing import Dict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.portfolio_builder import build_portfolio, portfolio_params
from engine.monte_carlo import run_simulation, compute_outcomes, get_cone_paths
from engine.config import N_SIMULATIONS


def run_full_simulation(
    monthly_sip:     float,
    years:           int,
    allocation:      Dict[str, float] = None,
    initial_lumpsum: float = 0.0,
    inflation_rate:  float = 0.06,
    n_sims:          int   = N_SIMULATIONS,
    top_n:           int   = 5,
    seed:            int   = 42,
    csv_path         = None,
) -> Dict:
    """
    Full simulation pipeline.

    Returns
    -------
    dict with keys:
        portfolio_params   : blended return, vol, n_funds
        outcomes           : all percentile outcomes
        cone               : {pessimistic, median, optimistic} paths (monthly)
        portfolio_table    : list of dicts (fund-level detail)
    """
    # Step 1: Build portfolio
    portfolio = build_portfolio(allocation, csv_path, top_n)
    params    = portfolio_params(portfolio)

    # Step 2: Run Monte Carlo
    final_values, all_paths = run_simulation(
        expected_return  = params["expected_return"],
        volatility       = params["volatility"],
        monthly_sip      = monthly_sip,
        years            = years,
        initial_lumpsum  = initial_lumpsum,
        inflation_rate   = inflation_rate,
        n_sims           = n_sims,
        seed             = seed,
    )

    # Step 3: Compute outcomes
    outcomes = compute_outcomes(
        final_values, years, monthly_sip, initial_lumpsum, inflation_rate
    )

    # Step 4: Cone paths
    cone = get_cone_paths(all_paths)
    cone_serializable = {k: v.tolist() for k, v in cone.items()}

    # Step 5: Portfolio table for UI
    port_table = portfolio[
        ["Scheme Name", "Category Name", "Asset_Class", "5Y", "Volatility", "Fund_Weight"]
    ].rename(columns={"5Y": "Return_5Y"}).copy()
    port_table["Return_5Y"]  = (port_table["Return_5Y"] * 100).round(2)
    port_table["Volatility"] = (port_table["Volatility"] * 100).round(2)
    port_table["Fund_Weight"]= (port_table["Fund_Weight"] * 100).round(2)

    return {
        "portfolio_params":  params,
        "outcomes":          outcomes,
        "cone":              cone_serializable,
        "portfolio_table":   port_table.to_dict(orient="records"),
    }


if __name__ == "__main__":
    import json

    result = run_full_simulation(
        monthly_sip     = 50_000,
        years           = 20,
        allocation      = {"Equity": 0.60, "Hybrid": 0.20, "Debt": 0.15, "Passive": 0.05},
        initial_lumpsum = 1_000_000,
    )

    print("\n📊 Portfolio Params:")
    print(json.dumps(result["portfolio_params"], indent=2))

    print("\n💰 Wealth Outcomes:")
    o = result["outcomes"]
    print(f"   Total Invested  : ₹{o['total_invested']/1e7:.2f} Cr")
    print(f"   Pessimistic P10 : ₹{o['p10_nominal']/1e7:.2f} Cr  (real: ₹{o['p10_real']/1e7:.2f} Cr)")
    print(f"   Median P50      : ₹{o['p50_nominal']/1e7:.2f} Cr  (real: ₹{o['p50_real']/1e7:.2f} Cr)")
    print(f"   Optimistic P90  : ₹{o['p90_nominal']/1e7:.2f} Cr  (real: ₹{o['p90_real']/1e7:.2f} Cr)")
    print(f"   Prob 5x wealth  : {o['prob_5x']}%")
    print(f"   Median XIRR     : {o['xirr_median_approx']*100:.1f}%")

    print(f"\n📁 Portfolio: {result['portfolio_params']['n_funds']} funds")
    for f in result["portfolio_table"][:5]:
        print(f"   {f['Scheme Name'][:45]:45s}  {f['Asset_Class']:8s}  {f['Return_5Y']:5.1f}%  w={f['Fund_Weight']:.1f}%")
