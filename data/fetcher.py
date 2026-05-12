from __future__ import annotations
import time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from pathlib import Path
from config import HORIZON_DAYS
from data.mock import make_demo_ohlcv, make_demo_meta

# ── File cache (persists across reruns within same container) ──────────────
CACHE_DIR = Path("/tmp/stock_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_MAX_AGE = 60 * 60 * 20   # 20 hours — refresh once per trading day

_name_cache: dict[str, str] = {}

def _cache_path(symbol: str) -> Path:
    safe = symbol.replace(".", "_").replace("^", "X").replace("=", "Y")
    return CACHE_DIR / f"{safe}.parquet"

def _read_file_cache(symbol: str) -> pd.DataFrame:
    p = _cache_path(symbol)
    if not p.exists():
        return pd.DataFrame()
    age = time.time() - p.stat().st_mtime
    if age > CACHE_MAX_AGE:
        return pd.DataFrame()   # stale — refetch
    try:
        return pd.read_parquet(p)
    except Exception:
        return pd.DataFrame()

def _write_file_cache(symbol: str, df: pd.DataFrame):
    try:
        df.to_parquet(_cache_path(symbol))
    except Exception:
        pass

def get_company_name(symbol: str) -> str:
    if symbol in _name_cache:
        return _name_cache[symbol]
    try:
        info = yf.Ticker(symbol).info
        name = info.get("longName") or info.get("shortName") or symbol.replace(".NS", "")
        _name_cache[symbol] = name
        return name
    except Exception:
        fallback = symbol.replace(".NS", "").replace(".BO", "")
        _name_cache[symbol] = fallback
        return fallback

def _download(symbol: str) -> pd.DataFrame:
    """Fetch 5 years of daily data. One call per ticker per day."""
    try:
        df = yf.download(symbol, period="5y", interval="1d",
                         progress=False, auto_adjust=True)
        if not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns={
        "Date":"Date","Datetime":"Date",
        "Open":"open","High":"high",
        "Low":"low","Close":"close","Volume":"volume",
    })
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    keep = [c for c in ["Date","open","high","low","close","volume"] if c in df.columns]
    return df[keep].dropna().reset_index(drop=True)

def _slice(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    n = HORIZON_DAYS.get(horizon, len(df))
    return df.tail(min(n, len(df))).reset_index(drop=True)

def _get_data(symbol: str) -> pd.DataFrame:
    """Cache-first fetch. Yahoo Finance only called when cache is missing or stale."""
    # 1. File cache (fast, no network)
    cached = _read_file_cache(symbol)
    if not cached.empty:
        return cached

    # 2. Yahoo Finance (network, may be rate limited)
    raw = _download(symbol)
    if raw.empty:
        return pd.DataFrame()

    df = _clean(raw)
    _write_file_cache(symbol, df)   # save for next 20 hours
    return df

def _get_meta(symbol: str, df: pd.DataFrame) -> dict:
    meta = {"h52": df["high"].tail(252).max(), "l52": df["low"].tail(252).min(),
            "mcap": None, "pe": None, "pb": None, "div_yield": None}
    try:
        info = yf.Ticker(symbol).info
        meta.update({
            "h52":       info.get("fiftyTwoWeekHigh",  meta["h52"]),
            "l52":       info.get("fiftyTwoWeekLow",   meta["l52"]),
            "mcap":      info.get("marketCap"),
            "pe":        info.get("trailingPE"),
            "pb":        info.get("priceToBook"),
            "div_yield": round((info.get("dividendYield") or 0) * 100, 2),
        })
    except Exception:
        pass
    return meta

@st.cache_resource(ttl=72000, show_spinner="Loading price data…")
def fetch_ohlcv(symbol: str, api_key: str, horizon: str,
                is_demo: bool = False) -> tuple[pd.DataFrame | None, dict]:
    if is_demo:
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    df = _get_data(symbol)
    if df.empty:
        st.warning(f"⚠️ Could not fetch **{symbol}** — showing demo data. Try again in a few minutes.")
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    return _slice(df, horizon), _get_meta(symbol, df)

@st.cache_resource(ttl=72000, show_spinner="Loading benchmark…")
def fetch_benchmark(symbol: str, api_key: str,
                    is_demo: bool = False) -> pd.DataFrame | None:
    if is_demo:
        return make_demo_ohlcv()[["Date","close"]].rename(columns={"close":"bench_close"})
    df = _get_data(symbol)
    if df.empty:
        return None
    return df[["Date","close"]].rename(columns={"close":"bench_close"})

@st.cache_resource(ttl=72000, show_spinner="Loading macro factors…")
def fetch_macro_factors(period: str = "1y", is_demo: bool = False) -> pd.DataFrame:
    if is_demo:
        return _demo_macro()
    symbols = {"India_VIX":"^INDIAVIX","Brent_Crude":"BZ=F","USD_INR":"USDINR=X"}
    frames = {}
    for name, sym in symbols.items():
        df = _get_data(sym)
        if not df.empty:
            frames[name] = df[["Date","close"]].rename(columns={"close":name}).set_index("Date")
    if not frames:
        return _demo_macro()
    combined = pd.concat(frames.values(), axis=1).ffill().dropna()
    return combined.reset_index().rename(columns={"index":"Date"})

def _demo_macro() -> pd.DataFrame:
    base = make_demo_ohlcv()
    rng  = np.random.default_rng(7)
    n    = len(base)
    return pd.DataFrame({
        "Date": base["Date"],
        "India_VIX":   rng.normal(0.0,    0.05,  n).cumsum() + 15,
        "Brent_Crude": rng.normal(0.0002, 0.012, n).cumsum() + 85,
        "USD_INR":     rng.normal(0.00005,0.003, n).cumsum() + 83.5,
    })
