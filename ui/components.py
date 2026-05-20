import pandas as pd
import streamlit as st
from config import (
    DEFAULT_TICKER, DEFAULT_BENCHMARK, BENCHMARK_OPTIONS,
    DEFAULT_RISK_FREE_RATE, HORIZON_DAYS,
)


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## 📈 Stock-Dash")
        st.caption("Professional stock analysis terminal")
        st.divider()

        st.markdown("##### 🔍 Instrument")
        ticker  = st.text_input("Ticker Symbol", value=DEFAULT_TICKER,
                                help="Use NSE format e.g. SBIN.NS, RELIANCE.NS").upper().strip()
        horizon = st.selectbox("Time Horizon", list(HORIZON_DAYS.keys()), index=4)

        st.markdown("##### 📊 Benchmark")
        benchmark = st.selectbox("Index", BENCHMARK_OPTIONS,
                                 index=BENCHMARK_OPTIONS.index(DEFAULT_BENCHMARK))

        st.markdown("##### ⚙️ Parameters")
        rf_rate = st.number_input(
            "Risk-Free Rate (%)", min_value=0.0, max_value=20.0,
            value=DEFAULT_RISK_FREE_RATE * 100, step=0.25,
            help="Indian 10Y bond yield approximation"
        ) / 100

        st.caption("🔴 Live mode fetches real NSE data. Demo mode uses synthetic data and never rate-limits.")
        demo_mode = st.toggle("Demo Mode", value=False,
                              help="Use synthetic data instead of live Yahoo Finance feed")

        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

        st.caption("Data sourced from Yahoo Finance via yfinance.")

    return {
        "ticker":    ticker,
        "horizon":   horizon,
        "benchmark": benchmark,
        "rf_rate":   rf_rate,
        "api_key":   "",
        "demo_mode": demo_mode,
    }


def render_kpi_ribbon(data: pd.DataFrame, meta: dict) -> None:
    curr       = data["close"].iloc[-1]
    prev       = data["close"].iloc[-2] if len(data) > 1 else curr
    delta      = (curr - prev) / prev * 100
    avg_vol    = data["volume"].tail(20).mean()
    curr_vol   = data["volume"].iloc[-1]
    vol_surgeX = curr_vol / avg_vol if avg_vol else 1

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("LTP", f"₹{curr:,.2f}", delta=f"{delta:+.2f}%")
    m2.metric("52W High", f"₹{meta.get('h52') or 0:,.2f}")
    m3.metric("52W Low",  f"₹{meta.get('l52') or 0:,.2f}")
    m4.metric("Volume Surge", f"{vol_surgeX:.1f}×",
              delta="High" if vol_surgeX > 2 else "Normal",
              delta_color="inverse" if vol_surgeX > 2 else "off")
    m5.metric("P/E Ratio", f"{round(meta.get('pe'), 1) if meta.get('pe') else '—'}")


def section_header(title: str, help_text: str = "") -> None:
    st.markdown(
        f'<p class="qt-section">{title}'
        + (f' <span title="{help_text}">ⓘ</span>' if help_text else "")
        + "</p>", unsafe_allow_html=True,
    )


def callout(text: str, kind: str = "info") -> None:
    css_class = {"info": "qt-callout", "warn": "qt-callout qt-warn",
                 "danger": "qt-callout qt-danger"}.get(kind, "qt-callout")
    st.markdown(f'<div class="{css_class}">{text}</div>', unsafe_allow_html=True)


def metric_with_help(label: str, value: str, help_text: str,
                     delta: str | None = None) -> None:
    st.metric(label=label, value=value, delta=delta, help=help_text)
