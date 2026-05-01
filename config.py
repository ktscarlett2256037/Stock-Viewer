"""
config.py — App-wide constants.
Change things here; never hardcode them elsewhere.
"""

# ── Horizon → lookback in trading days ──────────────────────────────────────
HORIZON_DAYS: dict[str, int] = {
    "Last Day":   78,     # 5-min bars in a session
    "Last Week":  5,
    "Last Month": 22,
    "6 Months":   126,
    "1 Year":     252,
    "5 Years":    1260,
    "MAX":        9999,   # resolved to len(df) at runtime
}

# ── Default tickers / benchmarks ────────────────────────────────────────────
DEFAULT_TICKER    = "SBIN.NS"
DEFAULT_BENCHMARK = "^NSEI"
BENCHMARK_OPTIONS = ["^NSEI", "^NSEBANK", "^BSESN"]

# ── Risk parameters ──────────────────────────────────────────────────────────
DEFAULT_RISK_FREE_RATE = 0.065   # 6.5 % — current Indian 10Y approx
VAR_CONFIDENCE_LEVELS  = [0.95, 0.99]
TRADING_DAYS_PER_YEAR  = 252

# ── Alpha Vantage endpoints ──────────────────────────────────────────────────
AV_BASE = "https://www.alphavantage.co/query"

# ── Demo data shape ──────────────────────────────────────────────────────────
DEMO_PERIODS = 2000
DEMO_META = {
    "h52":  1254.70,
    "l52":   900.00,
    "mcap": 54_500,
    "pe":     25.4,
    "pb":      3.2,
    "div_yield": 1.8,
}
