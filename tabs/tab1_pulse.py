"""
tabs/tab1_pulse.py — Market Pulse & Momentum
The "What is happening right now?" view.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analytics.momentum import rsi, vwap, volume_surge_ratio, daily_returns
from ui.components import section_header, callout, metric_with_help
from ui.theme import PLOTLY_LAYOUT, CYAN, BLUE, YELLOW, RED, GREEN, MUTED


def render(data: pd.DataFrame, cfg: dict) -> None:

    returns = daily_returns(data["close"])

    # ── Inline KPIs ────────────────────────────────────────────────────────
    section_header("Price Momentum")
    c1, c2, c3, c4 = st.columns(4)

    rsi_val  = rsi(data["close"]).iloc[-1]
    vwap_val = vwap(data).iloc[-1]
    surge    = volume_surge_ratio(data["volume"]).iloc[-1]
    ltp      = data["close"].iloc[-1]

    with c1:
        metric_with_help(
            "RSI (14)", f"{rsi_val:.1f}",
            "Relative Strength Index. >70 = overbought, <30 = oversold.",
            delta="Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral"),
        )
    with c2:
        metric_with_help(
            "VWAP", f"₹{vwap_val:,.2f}",
            "Volume Weighted Average Price. Price above = bullish intraday bias.",
            delta="Above VWAP" if ltp > vwap_val else "Below VWAP",
        )
    with c3:
        metric_with_help(
            "Vol Surge", f"{surge:.1f}×",
            "Today's volume vs. 20-day average. >2× signals unusual activity.",
        )
    with c4:
        metric_with_help(
            "Daily Return", f"{returns.iloc[-1]*100:+.2f}%",
            "Percentage change vs. previous close.",
        )

    if rsi_val > 70:
        callout("RSI above 70 — momentum is stretched. Watch for mean reversion.", "warn")
    elif rsi_val < 30:
        callout("RSI below 30 — potential oversold bounce zone.", "warn")

    # ── Main chart: Candlestick + Volume + RSI ──────────────────────────────
    section_header("Price & Volume")
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.02,
    )

    # — Candlesticks —
    fig.add_trace(go.Candlestick(
        x=data["Date"],
        open=data["open"], high=data["high"],
        low=data["low"],   close=data["close"],
        name="Price",
        increasing_line_color=GREEN,
        decreasing_line_color=RED,
    ), row=1, col=1)

    # — VWAP overlay —
    fig.add_trace(go.Scatter(
        x=data["Date"], y=vwap(data),
        line=dict(color=YELLOW, width=1.2, dash="dot"),
        name="VWAP",
    ), row=1, col=1)

    # — Volume bars (colour by price action) —
    colors = [GREEN if c >= o else RED
              for c, o in zip(data["close"], data["open"])]
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["volume"],
        marker_color=colors,
        opacity=0.6,
        name="Volume",
        hovertemplate="%{y:,.0f}",
    ), row=2, col=1)

    # — RSI —
    rsi_series = rsi(data["close"])
    fig.add_trace(go.Scatter(
        x=data["Date"], y=rsi_series,
        line=dict(color=CYAN, width=1.5),
        name="RSI (14)",
    ), row=3, col=1)

    # RSI threshold lines
    for level, col_ in [(70, RED), (30, GREEN), (50, MUTED)]:
        fig.add_hline(y=level, line_dash="dot", line_color=col_,
                      opacity=0.5, row=3, col=1)

    # — Layout —
    fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0e1117",
    font=dict(family="JetBrains Mono, Courier New, monospace", size=11, color="#c9d1d9"),
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="#1a1e2e", bordercolor="#2a2e39", font_size=12),
    height=700,
    xaxis_rangeslider_visible=False,
    yaxis=dict(title="Price (₹)", gridcolor="#1e2230"),
    yaxis2=dict(title="Volume",   gridcolor="#1e2230"),
    yaxis3=dict(title="RSI",      gridcolor="#1e2230", range=[0, 100]),
)

    # ── News / Research Link ────────────────────────────────────────────────
    section_header("Market Intel")
    callout(
        "💡 <b>Pro tip:</b> Click a candle on the chart, note the date, "
        "then search for news around that date to understand the move.",
        "info",
    )

    ticker = cfg["ticker"].replace(".NS", "")
    news_url = f"https://news.google.com/search?q={ticker}+NSE+India&hl=en-IN"
    st.link_button("🔍 Research on Google News", news_url)
