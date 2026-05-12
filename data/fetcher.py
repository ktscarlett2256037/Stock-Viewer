from __future__ import annotations
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from config import HORIZON_DAYS
from data.mock import make_demo_ohlcv, make_demo_meta

_name_cache: dict[str, str] = {}

def _session():
    from curl_cffi import requests as cffi
    return cffi.Session(impersonate="chrome110")

def get_company_name(symbol: str) -> str:
    if symbol in _name_cache:
        return _name_cache[symbol]
    try:
        info = yf.Ticker(symbol).info
        name = info.get("longName") or info.get("shortName") or symbol.replace(".NS","")
        _name_cache[symbol] = name
        return name
    except Exception:
        fallback = symbol.replace(".NS","").replace(".BO","")
        _name_cache[symbol] = fallback
        return fallback

def _download(symbol: str, period: str, interval: str) -> pd.DataFrame:
    # Try with curl_cffi Chrome session first
    try:
        sess = _session()
        df = yf.download(symbol, period=period, interval=interval,
                         session=sess, progress=False, auto_adjust=True)
        if not df.empty:
            return df
    except Exception:
        pass
    # Plain fallback
    try:
        df = yf.download(symbol, period=period, interval=interval,
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

@st.cache_resource(ttl=43200, show_spinner="Fetching price data…")
def fetch_ohlcv(symbol: str, api_key: str, horizon: str,
                is_demo: bool = False) -> tuple[pd.DataFrame | None, dict]:
    if is_demo:
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    period_map = {
        "Last Day":"1d","Last Week":"5d","Last Month":"1mo",
        "6 Months":"6mo","1 Year":"1y","3 Years":"3y",
        "5 Years":"5y","MAX":"max",
    }
    interval = "5m" if horizon == "Last Day" else "1d"
    raw = _download(symbol, period_map.get(horizon, "1y"), interval)

    if raw.empty:
        st.warning(f"⚠️ Could not fetch **{symbol}** — check the ticker (e.g. SBIN.NS)")
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    df = _clean(raw)
    return _slice(df, horizon), _get_meta(symbol, df)

@st.cache_resource(ttl=43200, show_spinner="Fetching benchmark…")
def fetch_benchmark(symbol: str, api_key: str,
                    is_demo: bool = False) -> pd.DataFrame | None:
    if is_demo:
        return make_demo_ohlcv()[["Date","close"]].rename(columns={"close":"bench_close"})
    raw = _download(symbol, "1y", "1d")
    if raw.empty:
        return None
    return _clean(raw)[["Date","close"]].rename(columns={"close":"bench_close"})

@st.cache_resource(ttl=43200, show_spinner="Fetching macro factors…")
def fetch_macro_factors(period: str = "1y", is_demo: bool = False) -> pd.DataFrame:
    if is_demo:
        return _demo_macro()
    symbols = {"India_VIX":"^INDIAVIX","Brent_Crude":"BZ=F","USD_INR":"USDINR=X"}
    frames = {}
    for name, sym in symbols.items():
        raw = _download(sym, period, "1d")
        if not raw.empty:
            df = _clean(raw)[["Date","close"]].rename(columns={"close": name})
            frames[name] = df.set_index("Date")
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
