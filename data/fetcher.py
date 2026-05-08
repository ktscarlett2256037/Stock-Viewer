from __future__ import annotations

import time
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from config import HORIZON_DAYS
from data.mock import make_demo_ohlcv, make_demo_meta


# ── Shared session with browser headers ──────────────────────────────────────
# This stops Yahoo Finance from fingerprinting and rate-limiting the requests
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})


def _download(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """
    Single yf.download() call — more reliable than ticker.history().
    Retries 3 times with backoff. Returns empty DataFrame on failure.
    """
    for attempt in range(3):
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                session=_SESSION,
            )
            if not df.empty:
                return df
        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = any(x in msg for x in ["429", "rate", "too many", "requests"])
            if is_rate_limit and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            break
    return pd.DataFrame()


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns from yf.download and standardise names."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns={
        "Date":     "Date",
        "Datetime": "Date",
        "Open":     "open",
        "High":     "high",
        "Low":      "low",
        "Close":    "close",
        "Volume":   "volume",
    })
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    keep = [c for c in ["Date","open","high","low","close","volume"] if c in df.columns]
    return df[keep].dropna()


# ── Public fetch functions ────────────────────────────────────────────────────

@st.cache_resource(ttl=86400, show_spinner="Fetching price data…")
def fetch_ohlcv(
    symbol: str,
    api_key: str,
    horizon: str,
    is_demo: bool = False,
) -> tuple[pd.DataFrame | None, dict]:

    if is_demo:
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    period_map = {
        "Last Day":   "1d",  "Last Week": "5d",
        "Last Month": "1mo", "6 Months":  "6mo",
        "1 Year":     "1y",  "5 Years":   "5y",
        "MAX":        "max",
    }
    interval = "5m" if horizon == "Last Day" else "1d"
    period   = period_map.get(horizon, "1y")

    raw = _download(symbol, period, interval)

    if raw.empty:
        st.warning(f"⚠️ Could not fetch **{symbol}** from Yahoo Finance — showing demo data.")
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    df = _clean(raw)

    # Fundamentals — separate try so a failure here doesn't kill price data
    meta = make_demo_meta()
    meta.update({"h52": df["high"].max(), "l52": df["low"].min(), "mcap": None})
    try:
        info = yf.Ticker(symbol, session=_SESSION).fast_info
        meta.update({
            "h52":  getattr(info, "year_high",         df["high"].max()),
            "l52":  getattr(info, "year_low",          df["low"].min()),
            "mcap": getattr(info, "market_cap",        None),
            "pe":   getattr(info, "p_e_ratio",         None),
            "pb":   None,
            "div_yield": None,
        })
    except Exception:
        pass

    return _slice(df, horizon), meta


@st.cache_resource(ttl=86400, show_spinner="Fetching benchmark…")
def fetch_benchmark(
    symbol: str,
    api_key: str,
    is_demo: bool = False,
) -> pd.DataFrame | None:

    if is_demo:
        df = make_demo_ohlcv()[["Date", "close"]]
        return df.rename(columns={"close": "bench_close"})

    raw = _download(symbol, period="1y", interval="1d")
    if raw.empty:
        return None

    df = _clean(raw)[["Date", "close"]].rename(columns={"close": "bench_close"})
    return df.dropna()


@st.cache_resource(ttl=86400, show_spinner="Fetching macro factors…")
def fetch_macro_factors(period: str = "1y", is_demo: bool = False) -> pd.DataFrame:

    if is_demo:
        return _demo_macro()

    symbols = {
        "India_VIX":   "^INDIAVIX",
        "Brent_Crude": "BZ=F",
        "USD_INR":     "USDINR=X",
        "Yield_10Y":   "^TNX",
    }

    frames = {}
    for name, sym in symbols.items():
        raw = _download(sym, period=period, interval="1d")
        if not raw.empty:
            df = _clean(raw)[["Date", "close"]].rename(columns={"close": name})
            frames[name] = df.set_index("Date")

    if not frames:
        st.warning("Macro data unavailable — using demo data.")
        return _demo_macro()

    combined = pd.concat(frames.values(), axis=1).ffill().dropna()
    return combined.reset_index().rename(columns={"index": "Date"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slice(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    n = HORIZON_DAYS.get(horizon, len(df))
    return df.tail(min(n, len(df))).reset_index(drop=True)


def _demo_macro() -> pd.DataFrame:
    base = make_demo_ohlcv()
    n    = len(base)
    rng  = np.random.default_rng(7)
    return pd.DataFrame({
        "Date":        base["Date"],
        "India_VIX":   rng.normal(0.0, 0.05, n).cumsum() + 15,
        "Brent_Crude": rng.normal(0.0002, 0.012, n).cumsum() + 85,
        "USD_INR":     rng.normal(0.00005, 0.003, n).cumsum() + 83.5,
        "Yield_10Y":   rng.normal(0.0001, 0.004, n).cumsum() + 7.0,
    })
