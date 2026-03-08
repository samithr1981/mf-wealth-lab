"""
frontend/app.py
---------------
Streamlit dashboard for MF Wealth Lab.
Run: streamlit run frontend/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from engine.portfolio_builder import build_portfolio, RISK_PROFILES, compare_fund_filters, VALID_FUND_FILTERS
from engine.simulator import run_simulation
from engine.wealth_outcomes import compute_outcomes

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MF Wealth Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 MF Wealth Lab")
    st.caption("Monte Carlo Portfolio Simulator — 890 real Indian funds")
    st.divider()

    st.subheader("💰 SIP & Horizon")
    sip = st.number_input("Monthly SIP (₹)", min_value=500, max_value=500_000,
                           value=25_000, step=500)
    years = st.slider("Investment Horizon (years)", 3, 40, 20)
    initial_corpus = st.number_input("Initial Lump Sum (₹)", min_value=0,
                                      max_value=10_000_000, value=0, step=10_000)

    st.divider()
    st.subheader("🎯 Risk Profile")
    profile_mode = st.radio("Allocation mode", ["Preset Profile", "Custom"])

    if profile_mode == "Preset Profile":
        risk_profile = st.selectbox("Risk Profile", list(RISK_PROFILES.keys()), index=1)
        custom_alloc = None
    else:
        st.caption("Must sum to 100%")
        eq = st.slider("Equity %", 0, 100, 50)
        hy = st.slider("Hybrid %", 0, 100 - eq, 20)
        de = st.slider("Debt %",   0, 100 - eq - hy, 25)
        pa = 100 - eq - hy - de
        st.info(f"Passive: {pa}%")
        custom_alloc = {"Equity": eq/100, "Hybrid": hy/100, "Debt": de/100, "Passive": pa/100}
        risk_profile = "Custom"

    st.divider()
    st.subheader("🔥 FIRE Target")
    enable_fire = st.checkbox("Enable FIRE calculator")
    target_corpus = None
    if enable_fire:
        target_cr = st.number_input("Target corpus (₹ Cr)", min_value=0.1,
                                     max_value=1000.0, value=5.0, step=0.5)
        target_corpus = target_cr * 1e7

    st.divider()
    st.subheader("🔬 Fund Filter")
    fund_filter = st.select_slider(
        "Max funds per asset class",
        options=[3, 5, 7, 10],
        value=5,
        help="Controls how many top-ranked funds are selected per asset class (Equity / Hybrid / Debt / Passive)"
    )
    st.caption({
        3:  "⚡ Top 3 — concentrated, high-conviction",
        5:  "✅ Top 5 — balanced (recommended)",
        7:  "📊 Top 7 — broader diversification",
        10: "🌐 Top 10 — maximum spread",
    }[fund_filter])

    st.divider()
    n_sims = st.select_slider("Simulations", [1000, 5000, 10000, 25000, 50000], 10000)
    run_btn = st.button("🚀 Run Simulation", use_container_width=True, type="primary")

# ── Main ───────────────────────────────────────────────────────────────────────
st.title("Mutual Fund Wealth Simulator")
st.caption("Powered by 890 real Indian mutual fund records · Monte Carlo engine")

if not run_btn:
    st.info("Configure your SIP in the sidebar and click **Run Simulation** to see your wealth projection.")

    # Show fund universe summary
    from engine.fund_selector import get_universe, get_asset_class_stats
    u = get_universe()
    stats = get_asset_class_stats(u)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Funds in Universe", len(u))
    col2.metric("Asset Classes", u["Asset_Class"].nunique())
    col3.metric("Categories", u["Category Name"].nunique())
    col4.metric("Avg 5Y Return (Equity)",
                f"{u[u['Asset_Class']=='Equity']['Return_Used'].mean():.1%}")

    st.subheader("Fund Universe by Asset Class")
    fig = go.Figure(go.Bar(
        x=stats["Asset_Class"],
        y=stats["mean_return"] * 100,
        text=[f"{r:.1f}%" for r in stats["mean_return"] * 100],
        textposition="outside",
        marker_color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
    ))
    fig.update_layout(
        yaxis_title="Mean Expected Return (%)",
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.stop()

# ── Run simulation ─────────────────────────────────────────────────────────────
with st.spinner("Running 10,000 simulations..."):
    portfolio = build_portfolio(risk_profile=risk_profile, custom_allocation=custom_alloc,
                                fund_filter=fund_filter)
    sim = run_simulation(
        sip=sip,
        years=years,
        expected_return=portfolio.expected_return,
        volatility=portfolio.volatility,
        n_simulations=n_sims,
        initial_corpus=initial_corpus,
    )
    out = compute_outcomes(sim, target_corpus=target_corpus)

# ── KPI row ────────────────────────────────────────────────────────────────────
st.subheader("Wealth Outcomes")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Worst Case (P10)", f"₹{out.worst_case/1e7:.2f} Cr")
c2.metric("Median (P50)", f"₹{out.median/1e7:.2f} Cr")
c3.metric("Best Case (P90)", f"₹{out.best_case/1e7:.2f} Cr")
c4.metric("Total Invested", f"₹{out.total_invested/1e7:.2f} Cr")
c5.metric("Approx XIRR", f"{out.median_xirr_approx:.1%}")

if enable_fire and out.fire_year is not None:
    st.success(f"🔥 FIRE milestone: Median portfolio crosses ₹{target_cr:.1f} Cr at **Year {out.fire_year}**"
               f"  ·  Probability of hitting target: **{out.probability_of_target*100:.1f}%**")
elif enable_fire:
    st.warning(f"Target corpus of ₹{target_cr:.1f} Cr not reached in median scenario within {years} years.")

st.divider()

# ── Wealth cone ────────────────────────────────────────────────────────────────
months_axis = np.arange(sim.months + 1)
years_axis  = months_axis / 12

p10_path = np.percentile(sim.paths, 10, axis=0) / 1e7
p50_path = np.percentile(sim.paths, 50, axis=0) / 1e7
p90_path = np.percentile(sim.paths, 90, axis=0) / 1e7
invested  = (np.arange(sim.months + 1) * sip + initial_corpus) / 1e7

fig = go.Figure()
fig.add_trace(go.Scatter(x=years_axis, y=p90_path, name="Best (P90)",
                          line=dict(color="#2ecc71", dash="dash"), mode="lines"))
fig.add_trace(go.Scatter(x=years_axis, y=p50_path, name="Median (P50)",
                          line=dict(color="#3498db", width=3), mode="lines"))
fig.add_trace(go.Scatter(x=years_axis, y=p10_path, name="Worst (P10)",
                          line=dict(color="#e74c3c", dash="dash"),
                          fill="tonexty", fillcolor="rgba(52,152,219,0.15)", mode="lines"))
fig.add_trace(go.Scatter(x=years_axis, y=invested, name="Invested",
                          line=dict(color="#95a5a6", dash="dot"), mode="lines"))
if enable_fire and target_corpus:
    fig.add_hline(y=target_corpus / 1e7, line_dash="longdash",
                  line_color="orange", annotation_text=f"FIRE target ₹{target_cr:.1f} Cr")

fig.update_layout(
    title="Wealth Cone — 10,000 Monte Carlo Paths",
    xaxis_title="Years",
    yaxis_title="Portfolio Value (₹ Crore)",
    height=450,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)"),
)
st.plotly_chart(fig, use_container_width=True)

# ── Distribution of final wealth ──────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Final Wealth Distribution")
    final_cr = sim.final_values / 1e7
    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(
        x=final_cr,
        nbinsx=80,
        marker_color="#3498db",
        opacity=0.75,
        name="Simulations",
    ))
    fig2.add_vline(x=out.median/1e7, line_color="#2ecc71", line_width=2,
                   annotation_text="Median")
    fig2.add_vline(x=out.worst_case/1e7, line_color="#e74c3c", line_dash="dash",
                   annotation_text="P10")
    fig2.add_vline(x=out.best_case/1e7, line_color="#27ae60", line_dash="dash",
                   annotation_text="P90")
    fig2.update_layout(height=350, xaxis_title="₹ Crore",
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    st.subheader("Asset Allocation")
    alloc_labels = list(portfolio.allocation.keys())
    alloc_vals   = [v * 100 for v in portfolio.allocation.values()]
    fig3 = go.Figure(go.Pie(
        labels=alloc_labels,
        values=alloc_vals,
        hole=0.4,
        marker_colors=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
    ))
    fig3.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)

# ── Yearly milestones table ────────────────────────────────────────────────────
st.subheader("Year-by-Year Milestones")
milestones_display = out.yearly_milestones.copy()
milestones_display.index = milestones_display["Year"]
milestones_display = milestones_display.drop(columns=["Year"])
st.dataframe(milestones_display.style.format("{:.2f}"), use_container_width=True)

# ── Fund filter comparison ────────────────────────────────────────────────────
with st.expander("📊 Compare all fund filter levels (3 / 5 / 7 / 10)", expanded=False):
    st.caption("How does changing the number of funds affect return and volatility?")
    cmp_df = compare_fund_filters(risk_profile, custom_alloc)
    # Highlight the currently selected filter row
    def highlight_selected(row):
        color = "background-color: #1a4a7a; color: white" if row["Fund Filter"] == fund_filter else ""
        return [color] * len(row)
    st.dataframe(
        cmp_df.style.apply(highlight_selected, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Currently selected: **Top {fund_filter}** (highlighted above)")

# ── Top funds ─────────────────────────────────────────────────────────────────
st.subheader("Funds in Your Portfolio")
if len(portfolio.top_funds) > 0:
    display_cols = ["Scheme Name", "Category Name", "Asset_Class",
                    "AuM (Cr)", "Return_Used", "Vol_Used", "Composite_Score", "Portfolio_Weight"]
    display_cols = [c for c in display_cols if c in portfolio.top_funds.columns]
    df_show = portfolio.top_funds[display_cols].copy()
    df_show["Return_Used"]      = df_show["Return_Used"].map("{:.1%}".format)
    df_show["Vol_Used"]         = df_show["Vol_Used"].map("{:.1%}".format)
    df_show["Portfolio_Weight"] = df_show["Portfolio_Weight"].map("{:.2%}".format)
    df_show["AuM (Cr)"]         = df_show["AuM (Cr)"].map("₹{:,.0f} Cr".format)
    st.dataframe(df_show.rename(columns={
        "Return_Used": "Exp. Return", "Vol_Used": "Volatility",
        "Portfolio_Weight": "Weight", "AuM (Cr)": "AUM (₹ Cr)"
    }), use_container_width=True)

# ── Download ───────────────────────────────────────────────────────────────────
csv = out.yearly_milestones.to_csv(index=False)
st.download_button("⬇️ Download Milestones CSV", csv, "milestones.csv", "text/csv")
