"""
data/fetcher.py — Single place for ALL external data retrieval.

Rules:
  • Every public function is decorated with @st.cache_data.
  • No UI code here — only pandas DataFrames and plain dicts.
  • Demo-mode fallbacks live in data/mock.py (imported below).
"""

from __future__ import annotations

import requests
import pandas as pd
import streamlit as st
from config import AV_BASE, HORIZON_DAYS
from data.mock import make_demo_ohlcv, make_demo_meta


# ── OHLCV (price + volume) ────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Fetching price data…")
def fetch_ohlcv(
    symbol: str,
    api_key: str,
    horizon: str,
    is_demo: bool = False,
) -> tuple[pd.DataFrame | None, dict]:
    """
    Returns (ohlcv_df, meta_dict).
    ohlcv_df columns: Date, open, high, low, close, volume  (already sliced to horizon)
    meta_dict keys  : h52, l52, mcap, pe, pb, div_yield
    """
    if is_demo or not api_key:
        full, meta = make_demo_ohlcv(), make_demo_meta()
        return _slice_horizon(full, horizon), meta

    try:
        clean = symbol.replace(".NS", "").replace(".BO", "")
        if horizon == "Last Day":
            params = dict(
                function="TIME_SERIES_INTRADAY",
                symbol=f"NSE:{clean}",
                interval="5min",
                outputsize="full",
                apikey=api_key,
            )
            ts_key = "Time Series (5min)"
        else:
            params = dict(
                function="TIME_SERIES_DAILY",
                symbol=f"NSE:{clean}",
                outputsize="full",
                apikey=api_key,
            )
            ts_key = "Time Series (Daily)"

        resp = requests.get(AV_BASE, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        if ts_key not in raw:
            st.warning(f"Alpha Vantage returned: {list(raw.keys())}")
            return None, {}

        df = (
            pd.DataFrame.from_dict(raw[ts_key], orient="index")
            .astype(float)
            .reset_index()
            .rename(columns={
                "index":    "Date",
                "1. open":  "open",
                "2. high":  "high",
                "3. low":   "low",
                "4. close": "close",
                "5. volume":"volume",
            })
        )
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)

        meta = {
            "h52":      df["high"].tail(252).max(),
            "l52":      df["low"].tail(252).min(),
            "mcap":     None,   # not in AV free tier
            "pe":       None,
            "pb":       None,
            "div_yield":None,
        }
        return _slice_horizon(df, horizon), meta

    except Exception as exc:
        st.error(f"OHLCV fetch failed: {exc}")
        return None, {}


# ── Benchmark index ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Fetching benchmark…")
def fetch_benchmark(
    symbol: str,
    api_key: str,
    is_demo: bool = False,
) -> pd.DataFrame | None:
    """
    Returns a DataFrame with columns [Date, close] for the benchmark.
    Uses the same AV daily endpoint; returns demo data when in demo mode.
    """
    if is_demo or not api_key:
        return make_demo_ohlcv()[["Date", "close"]].rename(columns={"close": "bench_close"})

    try:
        params = dict(
            function="TIME_SERIES_DAILY",
            symbol=symbol,
            outputsize="full",
            apikey=api_key,
        )
        resp = requests.get(AV_BASE, params=params, timeout=15)
        resp.raise_for_status()
        raw  = resp.json()
        ts   = raw["Time Series (Daily)"]

        df = (
            pd.DataFrame.from_dict(ts, orient="index")[["4. close"]]
            .astype(float)
            .reset_index()
            .rename(columns={"index": "Date", "4. close": "bench_close"})
        )
        df["Date"] = pd.to_datetime(df["Date"])
        return df.sort_values("Date").reset_index(drop=True)

    except Exception as exc:
        st.warning(f"Benchmark fetch failed: {exc}")
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _slice_horizon(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    n = HORIZON_DAYS.get(horizon, len(df))
    n = min(n, len(df))
    return df.tail(n).reset_index(drop=True)
