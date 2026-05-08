HORIZON_DAYS: dict[str, int] = {
    "Last Day":   78,
    "Last Week":  5,
    "Last Month": 22,
    "6 Months":   126,
    "1 Year":     252,
    "3 Years":    756,
    "5 Years":    1260,
    "MAX":        9999,
}

DEFAULT_TICKER         = "SBIN.NS"
DEFAULT_BENCHMARK      = "^NSEI"
BENCHMARK_OPTIONS      = ["^NSEI", "^NSEBANK", "^BSESN"]
DEFAULT_RISK_FREE_RATE = 0.065
VAR_CONFIDENCE_LEVELS  = [0.95, 0.99]
TRADING_DAYS_PER_YEAR  = 252
AV_BASE                = "https://www.alphavantage.co/query"
DEMO_PERIODS           = 2000
DEMO_META = {
    "h52": 1254.70, "l52": 900.00, "mcap": 54_500,
    "pe": 25.4, "pb": 3.2, "div_yield": 1.8,
}
