"""
data/fetcher.py — All data fetching via yfinance.
No API key required.
"""

from __future__ import annotations
import yfinance as yf
import pandas as pd
import streamlit as st
from config import HORIZON_DAYS
from data.mock import make_demo_ohlcv, make_demo_meta


@st.cache_data(ttl=3600, show_spinner="Fetching price data…")
def fetch_ohlcv(
    symbol: str,
    api_key: str,          # kept for signature compatibility, not used
    horizon: str,
    is_demo: bool = False,
) -> tuple[pd.DataFrame | None, dict]:

    if is_demo:
        return _slice_horizon(make_demo_ohlcv(), horizon), make_demo_meta()

    try:
        period_map = {
            "Last Day":   "1d",
            "Last Week":  "5d",
            "Last Month": "1mo",
            "6 Months":   "6mo",
            "1 Year":     "1y",
            "5 Years":    "5y",
            "MAX":        "max",
        }
        interval_map = {
            "Last Day": "5m",
        }

        period   = period_map.get(horizon, "1y")
        interval = interval_map.get(horizon, "1d")

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            st.error(f"No data found for {symbol}. Check the ticker symbol.")
            return None, {}

        df = df.reset_index().rename(columns={
            "Date":      "Date",
            "Datetime":  "Date",    # intraday uses Datetime
            "Open":      "open",
            "High":      "high",
            "Low":       "low",
            "Close":     "close",
            "Volume":    "volume",
        })
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df = df[["Date", "open", "high", "low", "close", "volume"]].dropna()

        # Pull fundamentals from yfinance info (this is the big upgrade)
        info = ticker.info
        meta = {
            "h52":       info.get("fiftyTwoWeekHigh"),
            "l52":       info.get("fiftyTwoWeekLow"),
            "mcap":      round(info.get("marketCap", 0) / 1e7),  # convert to Cr
            "pe":        info.get("trailingPE"),
            "pb":        info.get("priceToBook"),
            "div_yield": round(info.get("dividendYield", 0) * 100, 2),
        }
        return df, meta

    except Exception as exc:
        st.error(f"Data fetch failed: {exc}")
        return None, {}


@st.cache_data(ttl=3600, show_spinner="Fetching benchmark…")
def fetch_benchmark(
    symbol: str,
    api_key: str,
    is_demo: bool = False,
) -> pd.DataFrame | None:

    if is_demo:
        df = make_demo_ohlcv()[["Date", "close"]]
        return df.rename(columns={"close": "bench_close"})

    try:
        df = yf.Ticker(symbol).history(period="1y", interval="1d")
        if df.empty:
            return None
        df = df.reset_index().rename(columns={
            "Date": "Date", "Close": "bench_close"
        })
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        return df[["Date", "bench_close"]].dropna()

    except Exception as exc:
        st.warning(f"Benchmark fetch failed: {exc}")
        return None


def _slice_horizon(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    n = HORIZON_DAYS.get(horizon, len(df))
    return df.tail(min(n, len(df))).reset_index(drop=True)