"""
tabs/tab5_portfolio.py — Portfolio Engine & Optimizer
The "How do I build the perfect machine?" view.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.fetcher import fetch_ohlcv
from analytics.momentum import daily_returns
from analytics.portfolio import (
    correlation_matrix, portfolio_stats, risk_contribution,
    diversification_benefit, max_sharpe_weights,
    min_volatility_weights, target_return_weights,
)
from analytics.performance import sharpe_ratio, jensens_alpha, information_ratio
from ui.components import section_header, callout
from ui.theme import PLOTLY_LAYOUT, CYAN, YELLOW, RED, GREEN, BLUE, MUTED


# ── Fetch returns for all tickers ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Fetching portfolio data…")
def _load_portfolio_returns(tickers: tuple, api_key: str, demo: bool) -> pd.DataFrame:
    """Returns a DataFrame of daily returns, one column per ticker."""
    frames = {}
    for t in tickers:
        df, _ = fetch_ohlcv(t, api_key, "1 Year", is_demo=demo)
        if df is not None and len(df) > 20:
            frames[t] = daily_returns(df["close"]).reset_index(drop=True)
    return pd.DataFrame(frames).dropna()


# ── Main render ───────────────────────────────────────────────────────────────

def render(cfg: dict) -> None:

    section_header("Portfolio Construction")

    # ── Ticker Selector ──────────────────────────────────────────────────────
    default_tickers = ["SBIN.NS", "INFY.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
    tickers = st.multiselect(
        "Select up to 5 stocks",
        options=default_tickers + [cfg["ticker"]],
        default=default_tickers[:3],
        max_selections=5,
    )

    if len(tickers) < 2:
        callout("Select at least 2 stocks to build a portfolio.", "warn")
        return

    # ── Load data ────────────────────────────────────────────────────────────
    rets_df = _load_portfolio_returns(
        tuple(sorted(tickers)), cfg["api_key"], cfg["demo_mode"]
    )
    if rets_df.empty or rets_df.shape[1] < 2:
        callout("Could not load enough data. Try demo mode.", "danger")
        return

    available_tickers = list(rets_df.columns)
    n = len(available_tickers)

    # ── Allocation Mode ──────────────────────────────────────────────────────
    mode = st.radio(
        "Allocation Mode", ["Manual", "Max Sharpe", "Min Volatility"],
        horizontal=True,
    )

    mean_r = rets_df.mean().values
    cov    = rets_df.cov().values
    vols   = rets_df.std().values

    if mode == "Manual":
        st.markdown("**Set weights (must sum to 100%)**")
        weights_pct = []
        cols = st.columns(n)
        for i, (t, col_) in enumerate(zip(available_tickers, cols)):
            with col_:
                w = st.number_input(t, 0.0, 100.0,
                                    value=round(100 / n, 1), step=1.0, key=f"w_{t}")
                weights_pct.append(w)
        total = sum(weights_pct)
        if abs(total - 100) > 0.5:
            callout(f"Weights sum to {total:.1f}% — must equal 100%.", "danger")
            return
        weights = np.array(weights_pct) / 100

    elif mode == "Max Sharpe":
        weights = max_sharpe_weights(mean_r, cov, cfg["rf_rate"])
        callout("✅ Optimal weights computed to maximise the Sharpe Ratio (Tangency Portfolio).", "info")

    else:  # Min Volatility
        weights = min_volatility_weights(mean_r, cov)
        callout("✅ Optimal weights computed to minimise portfolio volatility (GMV Portfolio).", "info")

    # ── Portfolio Scorecard ──────────────────────────────────────────────────
    section_header("Portfolio Scorecard")
    ann_r, ann_v, sharpe = portfolio_stats(weights, mean_r, cov, cfg["rf_rate"])
    div_benefit           = diversification_benefit(weights, vols, cov)
    risk_contrib          = risk_contribution(weights, cov)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Return (Ann.)", f"{ann_r*100:.1f}%")
    c2.metric("Portfolio Volatility",   f"{ann_v*100:.1f}%")
    c3.metric("Sharpe Ratio",           f"{sharpe:.2f}")
    c4.metric("Diversification Benefit",f"{div_benefit*100:.1f}%",
              help="% of risk 'cancelled out' by combining assets.")

    # ── Weights table ────────────────────────────────────────────────────────
    section_header("Allocation Breakdown")
    alloc_df = pd.DataFrame({
        "Ticker":           available_tickers,
        "Weight":           [f"{w*100:.1f}%" for w in weights],
        "Risk Contribution":[f"{r*100:.1f}%" for r in risk_contrib],
    })
    st.dataframe(alloc_df.set_index("Ticker"), use_container_width=True)

    # ── Risk Contribution Bar Chart ──────────────────────────────────────────
    fig_rc = go.Figure(go.Bar(
        x=available_tickers,
        y=risk_contrib * 100,
        marker_color=[CYAN if r < 1/n * 1.3 else RED for r in risk_contrib],
        text=[f"{r*100:.1f}%" for r in risk_contrib],
        textposition="outside",
    ))
    fig_rc.update_layout(
        **PLOTLY_LAYOUT, height=280,
        yaxis_title="Risk Contribution (%)",
        title="Risk Contribution by Asset",
    )
    st.plotly_chart(fig_rc, use_container_width=True)

    # ── Correlation Heatmap ──────────────────────────────────────────────────
    section_header("Correlation Heatmap",
                   "Lower correlations = better diversification benefit.")
    corr = correlation_matrix(rets_df)

    fig_hm = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.index,
        colorscale=[
            [0.0,  "#ff4b6e"],
            [0.5,  "#1a1e2e"],
            [1.0,  "#00ffcc"],
        ],
        zmin=-1, zmax=1,
        text=corr.round(2).values,
        texttemplate="%{text}",
        showscale=True,
    ))
    fig_hm.update_layout(**PLOTLY_LAYOUT, height=350)
    st.plotly_chart(fig_hm, use_container_width=True)
