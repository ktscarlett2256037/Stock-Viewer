"""
tabs/tab2_risk.py — Risk & Volatility Vault
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import norm

from analytics.momentum import daily_returns
from analytics.risk import (
    realized_volatility, rolling_volatility, ewma_volatility,
    historical_var, parametric_var, expected_shortfall,
    max_drawdown, drawdown_series, drawdown_recovery,
    distribution_stats,
)
from ui.components import section_header, callout, metric_with_help
from ui.theme import PLOTLY_LAYOUT, CYAN, BLUE, YELLOW, RED, GREEN, MUTED


def render(data: pd.DataFrame, cfg: dict) -> None:
    returns = daily_returns(data["close"])

    section_header("Volatility Summary")
    rv   = realized_volatility(returns)
    dd   = drawdown_recovery(data["close"])
    dist = distribution_stats(returns)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_with_help("Realized Vol", f"{rv*100:.1f}%",
                         "Annualised standard deviation of daily log returns.")
    with c2:
        metric_with_help("Max Drawdown", f"{dd['max_dd']*100:.1f}%",
                         "Largest peak-to-trough percentage decline.")
    with c3:
        metric_with_help("Skewness", f"{dist['skewness']:.2f}",
                         "Negative = left tail. Positive = right tail.")
    with c4:
        metric_with_help("Excess Kurtosis", f"{dist['kurtosis']:.2f}",
                         "Fat tails vs. normal distribution (normal = 0).")

    if dd["in_recovery"]:
        pct = dd["recovery_pct"] * 100
        callout(f"⚠️ Still {100 - pct:.0f}% away from recovering its peak.", "warn")

    section_header("Conditional Volatility (EWMA)",
                   "Captures volatility clustering. Spikes = stress periods.")
    ewma = ewma_volatility(returns)
    roll = rolling_volatility(returns)

    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(
        x=data["Date"].iloc[1:], y=ewma,
        line=dict(color=CYAN, width=1.8),
        name="EWMA Vol",
        fill="tozeroy",
        fillcolor="rgba(0,255,204,0.07)",
    ))
    fig_vol.add_trace(go.Scatter(
        x=data["Date"].iloc[1:], y=roll,
        line=dict(color=YELLOW, width=1.2, dash="dot"),
        name="Rolling 21D Vol",
    ))
    fig_vol.update_layout(
        **PLOTLY_LAYOUT,
        height=280,
        yaxis=dict(title="Annualised Volatility", tickformat=".0%", gridcolor="#1e2230"),
        xaxis=dict(gridcolor="#1e2230"),
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    section_header("Tail Risk Metrics")
    rows = []
    for cl in [0.95, 0.99]:
        h_var = historical_var(returns, cl)
        p_var = parametric_var(returns, cl)
        es    = expected_shortfall(returns, cl)
        rows.append({
            "Confidence":     f"{int(cl*100)}%",
            "Hist VaR (1D)":  f"{h_var*100:.2f}%",
            "Param VaR (1D)": f"{p_var*100:.2f}%",
            "CVaR / ES":      f"{es*100:.2f}%",
        })
    st.dataframe(pd.DataFrame(rows).set_index("Confidence"), use_container_width=True)
    callout(
        "VaR = minimum loss in worst scenarios. "
        "CVaR = average loss <b>beyond</b> that threshold — the more conservative measure.",
        "info",
    )

    section_header("Drawdown from Peak")
    dd_series = drawdown_series(data["close"])
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=data["Date"], y=dd_series * 100,
        line=dict(color=RED, width=1.5),
        fill="tozeroy",
        fillcolor="rgba(255,75,110,0.15)",
        name="Drawdown %",
    ))
    fig_dd.update_layout(
        **PLOTLY_LAYOUT,
        height=250,
        yaxis=dict(title="Drawdown (%)", ticksuffix="%", gridcolor="#1e2230"),
        xaxis=dict(gridcolor="#1e2230"),
    )
    st.plotly_chart(fig_dd, use_container_width=True)

    section_header("Return Distribution")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=returns * 100, nbinsx=60,
        marker_color=BLUE, opacity=0.7,
        name="Daily Returns", histnorm="probability density",
    ))
    mu_r, sigma_r = returns.mean() * 100, returns.std() * 100
    x_range = np.linspace(returns.min() * 100, returns.max() * 100, 300)
    fig_hist.add_trace(go.Scatter(
        x=x_range, y=norm.pdf(x_range, mu_r, sigma_r),
        line=dict(color=YELLOW, width=2), name="Normal Fit",
    ))
    fig_hist.update_layout(
        **PLOTLY_LAYOUT,
        height=280,
        xaxis=dict(title="Daily Return (%)", gridcolor="#1e2230"),
        yaxis=dict(title="Density", gridcolor="#1e2230"),
    )
    if not dist["is_normal"]:
        callout(
            f"Jarque-Bera rejects normality (p={dist['jb_pvalue']:.4f}). "
            "Fat tails detected — parametric VaR may underestimate real risk.",
            "warn",
        )
    st.plotly_chart(fig_hist, use_container_width=True)
