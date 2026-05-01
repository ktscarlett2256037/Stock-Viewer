from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.momentum import daily_returns
from analytics.performance import (
    sharpe_ratio, sortino_ratio, jensens_alpha,
    information_ratio, cumulative_return, cagr,
)
from ui.components import section_header, callout, metric_with_help
from ui.theme import apply_layout, CYAN, YELLOW, RED, GREEN

def render(data: pd.DataFrame, bench_data, cfg: dict) -> None:
    rf    = cfg["rf_rate"]
    rets  = daily_returns(data["close"])

    has_bench = False
    if bench_data is not None:
        merged = pd.merge(data[["Date","close"]], bench_data, on="Date", how="inner")
        if len(merged) > 5:
            bench_rets = merged["bench_close"].pct_change().dropna()
            stock_rets = merged["close"].pct_change().dropna()
            has_bench  = True

    if not has_bench:
        stock_rets = rets

    section_header("Risk-Adjusted Performance")
    sharpe  = sharpe_ratio(stock_rets, rf)
    sortino = sortino_ratio(stock_rets, rf)
    total_r = cumulative_return(stock_rets)
    annualr = cagr(data["close"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_with_help("Sharpe Ratio", f"{sharpe:.2f}",
            "Excess return per unit of total risk. >1 = good, >2 = excellent.")
    with c2:
        metric_with_help("Sortino Ratio", f"{sortino:.2f}",
            "Like Sharpe but only penalises downside volatility.")
    with c3:
        metric_with_help("CAGR", f"{annualr*100:.1f}%",
            "Compound Annual Growth Rate over selected period.")
    with c4:
        metric_with_help("Period Return", f"{total_r*100:.1f}%",
            "Total return from start of selected horizon.")

    if has_bench:
        section_header(f"Benchmark Comparison vs {cfg['benchmark']}")
        alpha_val, beta_val = jensens_alpha(stock_rets, bench_rets, rf)
        ir_val              = information_ratio(stock_rets, bench_rets)

        c1, c2, c3 = st.columns(3)
        with c1:
            metric_with_help("Jensen's Alpha", f"{alpha_val*100:.2f}%",
                "Annual excess return not explained by market exposure.",
                delta="Positive ✓" if alpha_val > 0 else "Negative")
        with c2:
            metric_with_help("Beta (β)", f"{beta_val:.2f}",
                "Sensitivity to benchmark. β>1 = amplified market moves.")
        with c3:
            metric_with_help("Information Ratio", f"{ir_val:.2f}",
                "Consistency of outperformance. >0.5 = strong.")

        section_header("Indexed Performance (Base = 100)")
        stock_idx = (1 + stock_rets).cumprod() * 100
        bench_idx = (1 + bench_rets).cumprod() * 100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=merged["Date"].iloc[1:], y=stock_idx,
            line=dict(color=CYAN, width=2), name=cfg["ticker"]))
        fig.add_trace(go.Scatter(x=merged["Date"].iloc[1:], y=bench_idx,
            line=dict(color=YELLOW, width=1.5, dash="dot"), name=cfg["benchmark"]))
        apply_layout(fig, height=350,
            yaxis=dict(title="Indexed Return (Base 100)", gridcolor="#1e2230"),
            xaxis=dict(gridcolor="#1e2230"))
        st.plotly_chart(fig, use_container_width=True)

        if alpha_val < 0:
            callout(f"Negative Jensen's Alpha ({alpha_val*100:.2f}%). "
                    "Underperformed benchmark after adjusting for market risk.", "warn")
    else:
        callout("Benchmark data unavailable in demo mode.", "warn")

    section_header("Valuation Snapshot")
    meta = cfg.get("meta", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("P/E Ratio",      str(meta.get("pe") or "—"))
    c2.metric("P/B Ratio",      str(meta.get("pb") or "—"))
    c3.metric("Dividend Yield", f"{meta.get('div_yield') or '—'}%")
