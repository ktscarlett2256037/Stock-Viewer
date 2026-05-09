from __future__ import annotations
import numpy as np
import pandas as pd
from config import DEMO_PERIODS, DEMO_META

def make_demo_ohlcv() -> pd.DataFrame:
    rng    = np.random.default_rng(42)
    n      = DEMO_PERIODS
    shocks = rng.normal(0.0003, 0.015, n)
    close  = 1000.0 * np.exp(np.cumsum(shocks))
    high   = close * (1 + rng.uniform(0.002, 0.025, n))
    low    = close * (1 - rng.uniform(0.002, 0.025, n))
    open_  = low + rng.uniform(0, 1, n) * (high - low)
    vol    = rng.integers(200_000, 5_000_000, n).astype(float)
    idx    = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="D")
    df     = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )
    df.index.name = "Date"
    return df.reset_index()

def make_demo_meta() -> dict:
    return dict(DEMO_META)
