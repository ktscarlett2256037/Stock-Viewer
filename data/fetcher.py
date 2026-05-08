from __future__ import annotations
import time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from config import HORIZON_DAYS
from data.mock import make_demo_ohlcv, make_demo_meta

# ── Ticker → Company name map for better news search ─────────────────────────
COMPANY_NAMES = {
    "SBIN.NS":      "State Bank of India",
    "RELIANCE.NS":  "Reliance Industries",
    "TCS.NS":       "Tata Consultancy Services",
    "INFY.NS":      "Infosys",
    "HDFCBANK.NS":  "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "AXISBANK.NS":  "Axis Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "LT.NS":        "Larsen Toubro",
    "WIPRO.NS":     "Wipro",
    "BAJFINANCE.NS":"Bajaj Finance",
    "MARUTI.NS":    "Maruti Suzuki",
    "TATAMOTORS.NS":"Tata Motors",
    "ADANIENT.NS":  "Adani Enterprises",
    "HINDUNILVR.NS":"Hindustan Unilever",
    "ITC.NS":       "ITC Limited",
    "SUNPHARMA.NS": "Sun Pharmaceutical",
    "ONGC.NS":      "Oil and Natural Gas Corporation",
    "NTPC.NS":      "NTPC Limited",
    "POWERGRID.NS": "Power Grid Corporation",
}

def get_company_name(symbol: str) -> str:
    """Return human-readable company name for news search."""
    if symbol in COMPANY_NAMES:
        return COMPANY_NAMES[symbol]
    try:
        name = yf.Ticker(symbol).info.get("longName") or \
               yf.Ticker(symbol).info.get("shortName")
        if name:
            return name
    except Exception:
        pass
    return symbol.replace(".NS", "").replace(".BO", "")


def _download(symbol: str, period: str, interval: str) -> pd.DataFrame:
    for attempt in range(3):
        try:
            df = yf.download(
                symbol, period=period, interval=interval,
                progress=False, auto_adjust=True,
            )
            if not df.empty:
                return df
        except Exception:
            if attempt < 2:
                time.sleep(8 * (attempt + 1))
                continue
            break
    return pd.DataFrame()


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns={
        "Date": "Date", "Datetime": "Date",
        "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    keep = [c for c in ["Date","open","high","low","close","volume"] if c in df.columns]
    return df[keep].dropna()


@st.cache_resource(ttl=86400, show_spinner="Fetching price data…")
def fetch_ohlcv(symbol: str, api_key: str, horizon: str,
                is_demo: bool = False) -> tuple[pd.DataFrame | None, dict]:

    if is_demo:
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    period_map = {
        "Last Day": "1d", "Last Week": "5d", "Last Month": "1mo",
        "6 Months": "6mo", "1 Year": "1y", "3 Years": "3y",
        "5 Years": "5y", "MAX": "max",
    }
    interval = "5m" if horizon == "Last Day" else "1d"
    period   = period_map.get(horizon, "1y")

    raw = _download(symbol, period, interval)
    if raw.empty:
        st.warning(f"⚠️ Could not fetch **{symbol}** — showing demo data.")
        return _slice(make_demo_ohlcv(), horizon), make_demo_meta()

    df   = _clean(raw)
    meta = {"h52": df["high"].max(), "l52": df["low"].min(),
            "mcap": None, "pe": None, "pb": None, "div_yield": None}

    # Fetch fundamentals separately — use .info for full ratio data
    try:
        info = yf.Ticker(symbol).info
        meta.update({
            "h52":       info.get("fiftyTwoWeekHigh",  df["high"].max()),
            "l52":       info.get("fiftyTwoWeekLow",   df["low"].min()),
            "mcap":      info.get("marketCap"),
            "pe":        info.get("trailingPE"),
            "pb":        info.get("priceToBook"),
            "div_yield": round((info.get("dividendYield") or 0) * 100, 2),
        })
    except Exception:
        pass

    return _slice(df, horizon), meta


@st.cache_resource(ttl=86400, show_spinner="Fetching benchmark…")
def fetch_benchmark(symbol: str, api_key: str,
                    is_demo: bool = False) -> pd.DataFrame | None:
    if is_demo:
        return make_demo_ohlcv()[["Date","close"]].rename(columns={"close":"bench_close"})

    raw = _download(symbol, period="1y", interval="1d")
    if raw.empty:
        return None
    return _clean(raw)[["Date","close"]].rename(columns={"close":"bench_close"})


@st.cache_resource(ttl=86400, show_spinner="Fetching macro factors…")
def fetch_macro_factors(period: str = "1y", is_demo: bool = False) -> pd.DataFrame:
    if is_demo:
        return _demo_macro()

    # Yield_10Y removed — no reliable free India yield source yet
    symbols = {
        "India_VIX":   "^INDIAVIX",
        "Brent_Crude": "BZ=F",
        "USD_INR":     "USDINR=X",
    }
    frames = {}
    for name, sym in symbols.items():
        raw = _download(sym, period=period, interval="1d")
        if not raw.empty:
            df = _clean(raw)[["Date","close"]].rename(columns={"close": name})
            frames[name] = df.set_index("Date")

    if not frames:
        return _demo_macro()

    combined = pd.concat(frames.values(), axis=1).ffill().dropna()
    return combined.reset_index().rename(columns={"index": "Date"})


def _slice(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    n = HORIZON_DAYS.get(horizon, len(df))
    return df.tail(min(n, len(df))).reset_index(drop=True)


def _demo_macro() -> pd.DataFrame:
    base = make_demo_ohlcv()
    rng  = np.random.default_rng(7)
    n    = len(base)
    return pd.DataFrame({
        "Date":        base["Date"],
        "India_VIX":   rng.normal(0.0, 0.05, n).cumsum() + 15,
        "Brent_Crude": rng.normal(0.0002, 0.012, n).cumsum() + 85,
        "USD_INR":     rng.normal(0.00005, 0.003, n).cumsum() + 83.5,
    })
