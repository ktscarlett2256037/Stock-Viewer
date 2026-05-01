"""
ui/components.py — Reusable widgets shared across tabs.
Nothing here does any calculation — pure presentation glue.
"""

import pandas as pd
import streamlit as st
from config import (
    DEFAULT_TICKER, DEFAULT_BENCHMARK, BENCHMARK_OPTIONS,
    DEFAULT_RISK_FREE_RATE, HORIZON_DAYS,
)
from ui.theme import CYAN, RED, GREEN


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("### ⚙️ Terminal Settings")
        st.divider()

        demo_mode = st.checkbox("Demo Mode (random data)", value=False)

        st.divider()
        st.markdown("**Instrument**")
        ticker    = st.text_input("Ticker", value=DEFAULT_TICKER).upper().strip()
        horizon   = st.selectbox("Horizon", list(HORIZON_DAYS.keys()), index=4)

        st.divider()
        st.markdown("**Benchmarking**")
        benchmark = st.selectbox("Benchmark Index", BENCHMARK_OPTIONS,
                                 index=BENCHMARK_OPTIONS.index(DEFAULT_BENCHMARK))

        st.divider()
        st.markdown("**Risk Parameters**")
        rf_rate   = st.number_input(
            "Risk-Free Rate (%)", min_value=0.0, max_value=20.0,
            value=DEFAULT_RISK_FREE_RATE * 100, step=0.25,
            help="Used for Sharpe / Sortino / Jensen's Alpha calculations."
        ) / 100

    return {
        "ticker":    ticker,
        "horizon":   horizon,
        "benchmark": benchmark,
        "rf_rate":   rf_rate,
        "api_key":   "",
        "demo_mode": demo_mode,
    }


def render_kpi_ribbon(data: pd.DataFrame, meta: dict) -> None:
    curr  = data["close"].iloc[-1]
    prev  = data["close"].iloc[-2] if len(data) > 1 else curr
    delta = (curr - prev) / prev * 100

    avg_vol    = data["volume"].tail(20).mean()
    curr_vol   = data["volume"].iloc[-1]
    vol_surgeX = curr_vol / avg_vol if avg_vol else 1

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}", delta=f"{delta:+.2f}%")
    m2.metric("52W High", f"₹{meta.get('h52') or 0:,.2f}")
    m3.metric("52W Low",  f"₹{meta.get('l52') or 0:,.2f}")
    m4.metric(
        "Volume Surge", f"{vol_surgeX:.1f}×",
        delta="High" if vol_surgeX > 2 else "Normal",
        delta_color="inverse" if vol_surgeX > 2 else "off",
    )
    m5.metric("P/E Ratio", f"{meta.get('pe') or '—'}")


def section_header(title: str, help_text: str = "") -> None:
    st.markdown(
        f'<p class="qt-section">{title}'
        + (f' <span class="qt-help" title="{help_text}">ⓘ</span>' if help_text else "")
        + "</p>",
        unsafe_allow_html=True,
    )


def callout(text: str, kind: str = "info") -> None:
    css_class = {"info": "qt-callout", "warn": "qt-callout qt-warn",
                 "danger": "qt-callout qt-danger"}.get(kind, "qt-callout")
    st.markdown(f'<div class="{css_class}">{text}</div>', unsafe_allow_html=True)


def metric_with_help(label: str, value: str, help_text: str,
                     delta: str | None = None) -> None:
    st.metric(label=f"{label} ⓘ", value=value, delta=delta, help=help_text)
