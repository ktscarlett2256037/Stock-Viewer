"""
tabs/tab3_alpha.py — Alpha & Performance Lab
The "Is this stock actually a good investment?" view.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.momentum import daily_returns
from analytics.performance import (
    sharpe_ratio, sortino_ratio, jensens_alpha,
    information_ratio, beta, cumulative_return, cagr,
)
from ui.components import section_header, callout, metric_with_help
from ui.theme import PLOTLY_LAYOUT, CYAN, BLUE, YELLOW, RED, GREEN, MUTED


def render(data: pd.DataFrame, bench_data: pd.DataFrame | None, cfg: dict) -> None:
    rf    = cfg["rf_rate"]
    rets  = daily_returns(data["close"])

    # ── Align benchmark ──────────────────────────────────────────────────────
    if bench_data is not None:
        merged = pd.merge(
            data[["Date", "close"]],
            bench_data.rename(columns={"bench_close": "bench"}),
            on="Date", how="inner",
        )
        bench_rets = merged["bench"].pct_change().dropna()
        stock_rets = merged["close"].pct_change().dropna()
        has_bench  = True
    else:
        has_bench  = False
        stock_rets = rets

    # ── Risk-adjusted ratio cards ────────────────────────────────────────────
    section_header("Risk-Adjusted Performance")

    sharpe  = sharpe_ratio(stock_rets, rf)
    sortino = sortino_ratio(stock_rets, rf)
    total_r = cumulative_return(stock_rets)
    annualr = cagr(data["close"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_with_help(
            "Sharpe Ratio", f"{sharpe:.2f}",
            "Excess return per unit of total risk. >1 = good, >2 = excellent.",
        )
    with c2:
        metric_with_help(
            "Sortino Ratio", f"{sortino:.2f}",
            "Like Sharpe, but only penalises downside volatility. More investor-friendly.",
        )
    with c3:
        metric_with_help(
            "CAGR", f"{annualr*100:.1f}%",
            "Compound Annual Growth Rate over the selected period.",
        )
    with c4:
        metric_with_help(
            "Period Return", f"{total_r*100:.1f}%",
            "Total return from the start of the selected horizon.",
        )

    # ── Jensen's Alpha / Beta ────────────────────────────────────────────────
    if has_bench:
        section_header("Benchmark Comparison",
                       f"vs. {cfg['benchmark']} | Risk-free rate: {rf*100:.1f}%")

        alpha_val, beta_val = jensens_alpha(stock_rets, bench_rets, rf)
        ir_val              = information_ratio(stock_rets, bench_rets)

        c1, c2, c3 = st.columns(3)
        with c1:
            metric_with_help(
                "Jensen's Alpha (α)", f"{alpha_val*100:.2f}%",
                "Annual excess return not explained by market exposure. Positive = skill.",
                delta="Positive α ✓" if alpha_val > 0 else "Negative α",
            )
        with c2:
            metric_with_help(
                "Beta (β)", f"{beta_val:.2f}",
                "Sensitivity to benchmark moves. β=1 = moves 1:1 with market. β>1 = amplified.",
            )
        with c3:
            metric_with_help(
                "Information Ratio", f"{ir_val:.2f}",
                "Consistency of alpha generation vs. benchmark. >0.5 = strong.",
            )

        # ── Relative performance chart ──────────────────────────────────────
        section_header("Indexed Performance (Base = 100)")
        stock_idx = (1 + stock_rets).cumprod() * 100
        bench_idx = (1 + bench_rets).cumprod() * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=merged["Date"].iloc[1:], y=stock_idx,
            line=dict(color=CYAN, width=2),
            name=cfg["ticker"],
            fill="tonexty",
            fillcolor="rgba(0,255,204,0.05)",
        ))
        fig.add_trace(go.Scatter(
            x=merged["Date"].iloc[1:], y=bench_idx,
            line=dict(color=YELLOW, width=1.5, dash="dot"),
            name=cfg["benchmark"],
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT, height=350,
            yaxis_title="Indexed Return (Base 100)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Callout if underperforming
        if alpha_val < 0:
            callout(
                f"Negative Jensen's Alpha ({alpha_val*100:.2f}%). "
                "The stock has underperformed the benchmark after adjusting for market risk. "
                "You may be better off just buying the index.",
                "warn",
            )
    else:
        callout("Benchmark data unavailable — enable an API key for relative analysis.", "warn")

    # ── Valuation Snapshot ───────────────────────────────────────────────────
    section_header("Valuation Snapshot")
    meta = cfg.get("meta", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("P/E Ratio",     meta.get("pe",        "—"))
    col2.metric("P/B Ratio",     meta.get("pb",        "—"))
    col3.metric("Dividend Yield",
                f"{meta.get('div_yield', '—')}%" if meta.get("div_yield") else "—")

    if not any([meta.get("pe"), meta.get("pb")]):
        callout(
            "Valuation data (P/E, P/B) requires a premium data source. "
            "In demo mode, these are simulated values.",
            "info",
        )
