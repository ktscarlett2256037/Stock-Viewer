"""
analytics/risk.py — Tail-risk and volatility metrics.

All functions are pure: Series/DataFrame → scalar or Series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from config import TRADING_DAYS_PER_YEAR


# ── Volatility ────────────────────────────────────────────────────────────────

def realized_volatility(returns: pd.Series, annualize: bool = True) -> float:
    """Annualized standard deviation of log returns."""
    vol = returns.std()
    return vol * np.sqrt(TRADING_DAYS_PER_YEAR) if annualize else vol


def rolling_volatility(returns: pd.Series, window: int = 21) -> pd.Series:
    """Rolling annualized volatility."""
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def ewma_volatility(returns: pd.Series, lam: float = 0.94) -> pd.Series:
    """
    RiskMetrics EWMA volatility (approximates GARCH conditional vol).
    λ = 0.94 is J.P. Morgan's daily default.
    """
    sq = returns ** 2
    var_series = sq.ewm(alpha=1 - lam, adjust=False).mean()
    return np.sqrt(var_series) * np.sqrt(TRADING_DAYS_PER_YEAR)


# ── Value at Risk ─────────────────────────────────────────────────────────────

def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical (non-parametric) VaR.
    Returns the loss as a *positive* number (e.g. 0.032 = 3.2 % loss).
    """
    return float(-np.percentile(returns.dropna(), (1 - confidence) * 100))


def parametric_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Normal-distribution VaR.
    Returns the loss as a *positive* number.
    """
    mu, sigma = returns.mean(), returns.std()
    return float(-(mu + stats.norm.ppf(1 - confidence) * sigma))


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    CVaR / Expected Shortfall — average loss *beyond* the VaR threshold.
    Returns positive number.
    """
    var      = historical_var(returns, confidence)
    tail     = returns[returns <= -var]
    return float(-tail.mean()) if len(tail) else var


# ── Drawdown ──────────────────────────────────────────────────────────────────

def drawdown_series(close: pd.Series) -> pd.Series:
    """Returns a Series of drawdown from the running peak (negative values)."""
    peak = close.cummax()
    return (close - peak) / peak


def max_drawdown(close: pd.Series) -> float:
    """Peak-to-trough % decline (positive number, e.g. 0.35 = 35 % drawdown)."""
    return float(-drawdown_series(close).min())


def drawdown_recovery(close: pd.Series) -> dict:
    """
    Returns dict with keys:
      max_dd         : float
      in_recovery    : bool  (True if still below peak)
      recovery_pct   : float (0.0–1.0 fraction recovered from trough)
    """
    dd     = drawdown_series(close)
    mdd    = max_drawdown(close)
    curr   = dd.iloc[-1]
    trough = dd.min()

    return {
        "max_dd":      mdd,
        "in_recovery": curr < 0,
        "recovery_pct": (curr - trough) / (-trough) if trough < 0 else 1.0,
    }


# ── Return distribution ───────────────────────────────────────────────────────

def distribution_stats(returns: pd.Series) -> dict:
    """Skewness, excess kurtosis, Jarque-Bera p-value."""
    clean = returns.dropna()
    jb_stat, jb_p = stats.jarque_bera(clean)
    return {
        "skewness": float(clean.skew()),
        "kurtosis": float(clean.kurt()),   # excess kurtosis (normal = 0)
        "jb_pvalue": float(jb_p),
        "is_normal": jb_p > 0.05,
    }
