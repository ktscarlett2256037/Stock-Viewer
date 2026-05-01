"""
tabs/tab1_pulse.py — Market Pulse & Momentum
"""
from __future__ import annotations
import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

from analytics.momentum import rsi, sma, volume_surge_ratio, daily_returns
from ui.components import section_header, callout, metric_with_help
from ui.theme import PLOTLY_LAYOUT, CYAN, YELLOW, RED, GREEN, MUTED, BLUE


def _fetch_news(symbol: str) -> list[dict]:
    try:
        ticker = yf.Ticker(symbol)
        return ticker.news[:3] if ticker.news else []
    except:
        return []


def render(data: pd.DataFrame, cfg: dict) -> None:
    returns  = daily_returns(data["close"])
    ltp      = data["close"].iloc[-1]
    ma20     = sma(data["close"], 20).iloc[-1]
    rsi_val  = rsi(data["close"]).iloc[-1]
    surge    = volume_surge_ratio(data["volume"]).iloc[-1]

    section_header("Price Momentum")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_with_help(
            "RSI (14)", f"{rsi_val:.1f}",
            "Relative Strength Index. >70 = overbought, <30 = oversold.",
            delta="Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral"),
        )
    with c2:
        metric_with_help(
            "20D MA", f"₹{ma20:,.2f}",
            "20-Day Moving Average. Price above = bullish bias.",
            delta="Above MA ↑" if ltp > ma20 else "Below MA ↓",
        )
    with c3:
        metric_with_help(
            "Vol Surge", f"{surge:.1f}×",
            "Today's volume vs. 20-day average. >2× = unusual activity.",
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

    section_header("Price & Volume")
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.02,
    )

    fig.add_trace(go.Candlestick(
        x=data["Date"],
        open=data["open"], high=data["high"],
        low=data["low"],   close=data["close"],
        name="Price",
        increasing_line_color=GREEN,
        decreasing_line_color=RED,
    ), row=1, col=1)

    ma20_series = sma(data["close"], 20)
    fig.add_trace(go.Scatter(
        x=data["Date"], y=ma20_series,
        line=dict(color=YELLOW, width=1.4, dash="dot"),
        name="20D MA",
    ), row=1, col=1)

    colors = [GREEN if c >= o else RED
              for c, o in zip(data["close"], data["open"])]
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["volume"],
        marker_color=colors, opacity=0.6,
        name="Volume",
    ), row=2, col=1)

    rsi_series = rsi(data["close"])
    fig.add_trace(go.Scatter(
        x=data["Date"], y=rsi_series,
        line=dict(color=CYAN, width=1.5),
        name="RSI (14)",
    ), row=3, col=1)

    for level, col_ in [(70, RED), (30, GREEN), (50, MUTED)]:
        fig.add_hline(y=level, line_dash="dot", line_color=col_, opacity=0.5, row=3, col=1)

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=700,
        xaxis_rangeslider_visible=False,
        yaxis=dict(title="Price (₹)", gridcolor="#1e2230"),
        yaxis2=dict(title="Volume",   gridcolor="#1e2230"),
        yaxis3=dict(title="RSI",      gridcolor="#1e2230", range=[0, 100]),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── News Headlines ──────────────────────────────────────────────────────
    section_header("Latest News")

    if not cfg.get("demo_mode"):
        news = _fetch_news(cfg["ticker"])
        if news:
            for item in news:
                title     = item.get("title", "No title")
                publisher = item.get("publisher", "")
                link      = item.get("link", "#")
                ts        = item.get("providerPublishTime", 0)
                date_str  = datetime.datetime.fromtimestamp(ts).strftime("%d %b %Y") if ts else ""

                st.markdown(
                    f"""<div class="news-card">
                        <div class="news-title"><a href="{link}" target="_blank" 
                        style="color:#e6edf3;text-decoration:none;">{title}</a></div>
                        <div class="news-meta">{publisher} &nbsp;·&nbsp; {date_str}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            callout("No recent headlines found for this ticker.", "info")
    else:
        callout("📰 News headlines are available in live mode (disable Demo Mode).", "info")

    ticker_clean = cfg["ticker"].replace(".NS", "").replace(".BO", "")
    st.link_button("🔍 More news on Google", 
                   f"https://news.google.com/search?q={ticker_clean}+NSE+stock&hl=en-IN")
