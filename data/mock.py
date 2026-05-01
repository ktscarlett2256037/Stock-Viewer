"""
data/mock.py — Deterministic-ish demo data so the app looks great without an API key.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime
from config import DEMO_PERIODS, DEMO_META


def make_demo_ohlcv() -> pd.DataFrame:
    """
    Returns a 2000-row OHLCV DataFrame with a realistic random-walk close
    so charts look natural rather than uniform noise.
    """
    rng   = np.random.default_rng(42)           # fixed seed → reproducible
    dates = pd.date_range(end=datetime.now(), periods=DEMO_PERIODS, freq="B")

    # Geometric Brownian Motion for close price
    mu    = 0.0003
    sigma = 0.015
    shocks = rng.normal(mu, sigma, DEMO_PERIODS)
    close = 1000.0 * np.exp(np.cumsum(shocks))

    high   = close * (1 + rng.uniform(0.002, 0.025, DEMO_PERIODS))
    low    = close * (1 - rng.uniform(0.002, 0.025, DEMO_PERIODS))
    open_  = low + rng.uniform(0, 1, DEMO_PERIODS) * (high - low)
    volume = rng.integers(200_000, 5_000_000, DEMO_PERIODS)

    return pd.DataFrame({
        "Date":   dates,
        "open":   open_,
        "high":   high,
        "low":    low,
        "close":  close,
        "volume": volume.astype(float),
    })


def make_demo_meta() -> dict:
    return dict(DEMO_META)
