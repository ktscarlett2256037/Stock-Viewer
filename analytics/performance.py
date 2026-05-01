"""
analytics/performance.py — Risk-adjusted performance metrics.

All functions are pure: Series → scalar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from config import TRADING_DAYS_PER_YEAR


def _annualize(r: float) -> float:
    """Annualize a daily mean return."""
    return r * TRADING_DAYS_PER_YEAR


def sharpe_ratio(returns: pd.Series, rf_rate: float = 0.065) -> float:
    """
    Annualised Sharpe Ratio.
    rf_rate: annual risk-free rate (e.g. 0.065 = 6.5 %).
    """
    rf_daily = rf_rate / TRADING_DAYS_PER_YEAR
    excess   = returns - rf_daily
    if excess.std() == 0:
        return np.nan
    return float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def sortino_ratio(returns: pd.Series, rf_rate: float = 0.065) -> float:
    """
    Annualised Sortino Ratio (penalises only downside deviation).
    """
    rf_daily  = rf_rate / TRADING_DAYS_PER_YEAR
    excess    = returns - rf_daily
    downside  = excess[excess < 0].std()
    if downside == 0:
        return np.nan
    return float(excess.mean() / downside * np.sqrt(TRADING_DAYS_PER_YEAR))


def jensens_alpha(
    stock_returns: pd.Series,
    bench_returns: pd.Series,
    rf_rate: float = 0.065,
) -> tuple[float, float]:
    """
    Jensen's Alpha via OLS regression: R_i - Rf = α + β(R_m - Rf) + ε

    Returns (alpha_annualised, beta).
    """
    rf_daily = rf_rate / TRADING_DAYS_PER_YEAR
    aligned  = pd.concat([stock_returns, bench_returns], axis=1).dropna()
    aligned.columns = ["stock", "bench"]

    xs = aligned["stock"] - rf_daily
    xm = aligned["bench"] - rf_daily

    slope, intercept, *_ = stats.linregress(xm, xs)
    alpha_annualised = float(intercept * TRADING_DAYS_PER_YEAR)
    return alpha_annualised, float(slope)


def information_ratio(
    stock_returns: pd.Series,
    bench_returns: pd.Series,
) -> float:
    """
    Information Ratio = mean(active return) / std(active return).
    Active return = stock return − benchmark return.
    """
    aligned = pd.concat([stock_returns, bench_returns], axis=1).dropna()
    aligned.columns = ["stock", "bench"]
    active = aligned["stock"] - aligned["bench"]
    if active.std() == 0:
        return np.nan
    return float(active.mean() / active.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def beta(stock_returns: pd.Series, bench_returns: pd.Series) -> float:
    """Market beta from OLS."""
    aligned = pd.concat([stock_returns, bench_returns], axis=1).dropna()
    aligned.columns = ["stock", "bench"]
    slope, *_ = stats.linregress(aligned["bench"], aligned["stock"])
    return float(slope)


def cumulative_return(returns: pd.Series) -> float:
    """Total return over the period (e.g. 0.42 = +42 %)."""
    return float((1 + returns).prod() - 1)


def cagr(close: pd.Series) -> float:
    """Compound Annual Growth Rate."""
    years = len(close) / TRADING_DAYS_PER_YEAR
    if years == 0:
        return np.nan
    return float((close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1)
