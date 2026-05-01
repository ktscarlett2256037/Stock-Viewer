"""
Quantum Intelligence Terminal
==============================
Entry point. Handles sidebar config, data loading, and tab routing.
All business logic lives in analytics/, data/, ui/, and tabs/.
"""

import streamlit as st
from data.fetcher import fetch_ohlcv, fetch_benchmark
from ui.theme import inject_css
from ui.components import render_kpi_ribbon, render_sidebar
from tabs import tab1_pulse, tab2_risk, tab3_alpha, tab4_macro, tab5_portfolio

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="Quantum Terminal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

# ── Sidebar (persistent across all tabs) ────────────────────────────────────
cfg = render_sidebar()   # returns dict: ticker, benchmark, rf_rate, api_key, demo_mode, horizon

# ── Data layer (cached) ──────────────────────────────────────────────────────
price_data, meta = fetch_ohlcv(
    symbol=cfg["ticker"],
    api_key=cfg["api_key"],
    horizon=cfg["horizon"],
    is_demo=cfg["demo_mode"],
)

bench_data = fetch_benchmark(
    symbol=cfg["benchmark"],
    api_key=cfg["api_key"],
    is_demo=cfg["demo_mode"],
)

if price_data is None:
    st.error("⚠️ Terminal Connection Error — check your API key or enable Demo Mode.")
    st.stop()

# ── Header & KPI Ribbon ──────────────────────────────────────────────────────
st.markdown(f"## 🚀 Quantum Intelligence Terminal &nbsp; `{cfg['ticker']}`")
render_kpi_ribbon(price_data, meta)
st.divider()

# ── Tab routing ──────────────────────────────────────────────────────────────
TAB_LABELS = [
    "📡 Market Pulse",
    "🛡️ Risk & Volatility",
    "⚡ Alpha Lab",
    "🌐 Macro Sensitivity",
    "🧬 Portfolio Engine",
]

tabs = st.tabs(TAB_LABELS)

with tabs[0]:
    tab1_pulse.render(price_data, cfg)

with tabs[1]:
    tab2_risk.render(price_data, cfg)

with tabs[2]:
    tab3_alpha.render(price_data, bench_data, cfg)

with tabs[3]:
    tab4_macro.render(price_data, cfg)

with tabs[4]:
    tab5_portfolio.render(cfg)
