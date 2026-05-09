"""
Runs daily via GitHub Actions.
Fetches data for common NSE tickers and saves as CSV files.
The Streamlit app reads these files instead of hitting Yahoo Finance.
"""
import yfinance as yf
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(exist_ok=True)

TICKERS = [
    "SBIN.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "LT.NS", "WIPRO.NS",
    "BAJFINANCE.NS", "MARUTI.NS", "TATAMOTORS.NS", "ITC.NS", "SUNPHARMA.NS",
    "^NSEI", "^NSEBANK", "^BSESN",          # benchmarks
    "^INDIAVIX", "BZ=F", "USDINR=X",        # macro factors
]

for ticker in TICKERS:
    try:
        df = yf.download(ticker, period="5y", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            print(f"SKIP {ticker} — empty")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        safe = ticker.replace(".", "_").replace("^", "").replace("=", "")
        df.to_csv(CACHE_DIR / f"{safe}.csv")
        print(f"OK   {ticker}")
    except Exception as e:
        print(f"FAIL {ticker}: {e}")

# Save metadata
meta = {"updated_at": datetime.utcnow().isoformat(), "tickers": TICKERS}
(CACHE_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
print("Done.")
