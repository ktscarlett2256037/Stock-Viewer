"""
data/mock.py — Deterministic demo data. Cannot fail on array lengths.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from config import DEMO_PERIODS, DEMO_META


def make_demo_ohlcv() -> pd.DataFrame:
    rng = np.random.default_rng(42)

    # Build dates as a simple list — guaranteed DEMO_PERIODS length
    end   = pd.Timestamp.today().normalize()
    dates = [end - pd.Timedelta(days=(DEMO_PERIODS - 1 - i)) for i in range(DEMO_PERIODS)]

    mu     = 0.0003
    sigma  = 0.015
    shocks = rng.normal(mu, sigma, DEMO_PERIODS)
    close  = 1000.0 * np.exp(np.cumsum(shocks))
    high   = close * (1 + rng.uniform(0.002, 0.025, DEMO_PERIODS))
    low    = close * (1 - rng.uniform(0.002, 0.025, DEMO_PERIODS))
    open_  = low + rng.uniform(0, 1, DEMO_PERIODS) * (high - low)
    volume = rng.integers(200_000, 5_000_000, DEMO_PERIODS).astype(float)

    assert len(dates) == len(close) == DEMO_PERIODS, "Length mismatch in demo data"

    return pd.DataFrame({
        "Date":   dates,
        "open":   open_,
        "high":   high,
        "low":    low,
        "close":  close,
        "volume": volume,
    })


def make_demo_meta() -> dict:
    return dict(DEMO_META)
