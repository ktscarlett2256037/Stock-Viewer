"""
analytics/portfolio.py — Multi-asset portfolio construction.

Scipy-based Mean-Variance optimisation.
No Streamlit / Plotly here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import TRADING_DAYS_PER_YEAR


def correlation_matrix(returns_df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix of a returns DataFrame (columns = tickers)."""
    return returns_df.corr()


def portfolio_stats(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    rf_rate: float = 0.065,
) -> tuple[float, float, float]:
    """
    Returns (annualised_return, annualised_volatility, sharpe_ratio).
    weights must sum to 1.
    """
    ret = float(np.dot(weights, mean_returns) * TRADING_DAYS_PER_YEAR)
    vol = float(np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(TRADING_DAYS_PER_YEAR))
    sharpe = (ret - rf_rate) / vol if vol else np.nan
    return ret, vol, sharpe


def risk_contribution(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
) -> np.ndarray:
    """
    Percentage risk contribution of each asset.
    Returns array summing to 1.
    """
    port_vol = np.sqrt(weights @ cov_matrix @ weights)
    marginal = cov_matrix @ weights
    contrib  = weights * marginal / port_vol
    return contrib / contrib.sum()


def diversification_benefit(
    weights: np.ndarray,
    vols: np.ndarray,
    cov_matrix: np.ndarray,
) -> float:
    """
    % risk reduced by combining assets vs. a weighted-average of standalone vols.
    (1 - portfolio_vol / weighted_avg_vol)
    """
    weighted_avg = float(np.dot(weights, vols))
    port_vol     = float(np.sqrt(weights @ cov_matrix @ weights))
    return 1.0 - port_vol / weighted_avg if weighted_avg else 0.0


# ── Optimisers ────────────────────────────────────────────────────────────────

def _base_minimize(
    objective,
    n: int,
    constraints: list,
    bounds,
) -> np.ndarray:
    init = np.full(n, 1 / n)
    result = minimize(
        objective, init,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500},
    )
    return result.x if result.success else init


def _standard_setup(n: int):
    bounds      = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    return bounds, constraints


def max_sharpe_weights(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    rf_rate: float = 0.065,
) -> np.ndarray:
    """Tangency portfolio: maximise Sharpe ratio."""
    n = len(mean_returns)
    bounds, constraints = _standard_setup(n)

    def neg_sharpe(w):
        r, v, _ = portfolio_stats(w, mean_returns, cov_matrix, rf_rate)
        return -((r - rf_rate) / v) if v else 1e9

    return _base_minimize(neg_sharpe, n, constraints, bounds)


def min_volatility_weights(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
) -> np.ndarray:
    """Global Minimum Variance portfolio."""
    n = len(mean_returns)
    bounds, constraints = _standard_setup(n)

    def port_vol(w):
        return np.sqrt(w @ cov_matrix @ w)

    return _base_minimize(port_vol, n, constraints, bounds)


def target_return_weights(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    target_annual_return: float,
) -> np.ndarray:
    """Minimum variance for a given target annual return."""
    n = len(mean_returns)
    bounds, constraints = _standard_setup(n)
    target_daily = target_annual_return / TRADING_DAYS_PER_YEAR
    constraints.append({
        "type": "eq",
        "fun":  lambda w: np.dot(w, mean_returns) - target_daily,
    })

    def port_vol(w):
        return np.sqrt(w @ cov_matrix @ w)

    return _base_minimize(port_vol, n, constraints, bounds)
