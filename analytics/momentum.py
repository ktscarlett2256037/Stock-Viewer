"""
analytics/momentum.py — Momentum & price-action indicators.

All functions are pure (pd.DataFrame → pd.Series / scalar).
No Streamlit or Plotly here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Wilder's RSI.
    Returns a Series aligned with `close`; first `window` values are NaN.
    """
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def vwap(data: pd.DataFrame) -> pd.Series:
    """
    Intraday VWAP (resets each day).
    Expects columns: high, low, close, volume.
    Returns a Series aligned with data index.
    """
    typical = (data["high"] + data["low"] + data["close"]) / 3
    cum_pv  = (typical * data["volume"]).cumsum()
    cum_v   = data["volume"].cumsum()
    return cum_pv / cum_v


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    return close.ewm(span=window, adjust=False).mean()


def bollinger_bands(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper_band, middle_band, lower_band)."""
    mid   = sma(close, window)
    std   = close.rolling(window).std()
    return mid + num_std * std, mid, mid - num_std * std


def volume_surge_ratio(volume: pd.Series, window: int = 20) -> pd.Series:
    """Current volume / rolling mean volume. >2 = surge."""
    return volume / volume.rolling(window).mean()


def daily_returns(close: pd.Series) -> pd.Series:
    return close.pct_change().dropna()
