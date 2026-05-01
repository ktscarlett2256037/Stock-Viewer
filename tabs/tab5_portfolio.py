from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.fetcher import fetch_ohlcv
from analytics.momentum import daily_returns
from analytics.portfolio import (
    correlation_matrix, portfolio_stats, risk_contribution,
    diversification_benefit, max_sharpe_weights, min_volatility_weights,
)
from ui.components import section_header, callout
from ui.theme import apply_layout, CYAN, YELLOW, RED, GREEN, BLUE

@st.cache_data(ttl=3600)
def _load_returns(tickers: tuple, api_key: str, demo: bool) -> pd.DataFrame:
    frames = {}
    for t in tickers:
        df, _ = fetch_ohlcv(t, api_key, "1 Year", is_demo=demo)
        if df is not None and len(df) > 20:
            frames[t] = daily_returns(df["close"]).reset_index(drop=True)
    return pd.DataFrame(frames).dropna()

def render(cfg: dict) -> None:
    section_header("Portfolio Construction")

    default_tickers = ["SBIN.NS", "INFY.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
    tickers = st.multiselect("Select up to 5 stocks", options=default_tickers,
                             default=default_tickers[:3], max_selections=5)

    if len(tickers) < 2:
        callout("Select at least 2 stocks to build a portfolio.", "warn")
        return

    rets_df = _load_returns(tuple(sorted(tickers)), cfg["api_key"], cfg["demo_mode"])
    if rets_df.empty or rets_df.shape[1] < 2:
        callout("Could not load enough data. Try demo mode.", "danger")
        return

    tickers = list(rets_df.columns)
    n       = len(tickers)
    mean_r  = rets_df.mean().values
    cov     = rets_df.cov().values
    vols    = rets_df.std().values

    mode = st.radio("Allocation Mode", ["Manual", "Max Sharpe", "Min Volatility"], horizontal=True)

    if mode == "Manual":
        st.markdown("**Set weights (must sum to 100%)**")
        weights_pct = []
        cols = st.columns(n)
        for i, (t, col_) in enumerate(zip(tickers, cols)):
            with col_:
                w = st.number_input(t, 0.0, 100.0, value=round(100/n, 1), step=1.0, key=f"w_{t}")
                weights_pct.append(w)
        if abs(sum(weights_pct) - 100) > 0.5:
            callout(f"Weights sum to {sum(weights_pct):.1f}% — must equal 100%.", "danger")
            return
        weights = np.array(weights_pct) / 100
    elif mode == "Max Sharpe":
        weights = max_sharpe_weights(mean_r, cov, cfg["rf_rate"])
        callout("✅ Weights optimised for maximum Sharpe Ratio.", "info")
    else:
        weights = min_volatility_weights(mean_r, cov)
        callout("✅ Weights optimised for minimum volatility.", "info")

    section_header("Portfolio Scorecard")
    ann_r, ann_v, sharpe = portfolio_stats(weights, mean_r, cov, cfg["rf_rate"])
    div_b                 = diversification_benefit(weights, vols, cov)
    risk_c                = risk_contribution(weights, cov)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Return", f"{ann_r*100:.1f}%")
    c2.metric("Portfolio Vol",   f"{ann_v*100:.1f}%")
    c3.metric("Sharpe Ratio",    f"{sharpe:.2f}")
    c4.metric("Diversification", f"{div_b*100:.1f}%")

    section_header("Risk Contribution")
    fig1 = go.Figure(go.Bar(
        x=tickers, y=risk_c*100,
        marker_color=[CYAN if r < 1/n*1.3 else RED for r in risk_c],
        text=[f"{r*100:.1f}%" for r in risk_c], textposition="outside",
    ))
    apply_layout(fig1, height=280,
        yaxis=dict(title="Risk Contribution (%)", gridcolor="#1e2230"),
        xaxis=dict(gridcolor="#1e2230"))
    st.plotly_chart(fig1, use_container_width=True)

    section_header("Correlation Heatmap")
    corr = correlation_matrix(rets_df)
    fig2 = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index,
        colorscale=[[0.0,"#ff4b6e"],[0.5,"#1a1e2e"],[1.0,"#00ffcc"]],
        zmin=-1, zmax=1,
        text=corr.round(2).values, texttemplate="%{text}", showscale=True,
    ))
    apply_layout(fig2, height=350)
    st.plotly_chart(fig2, use_container_width=True)
