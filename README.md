# 🚀 Quantum Intelligence Terminal

A professional-grade stock analysis platform built with Streamlit.

## Project Structure

```
quantum_terminal/
│
├── app.py                   ← Entry point. Thin orchestrator only.
├── config.py                ← All constants (horizons, defaults, risk params)
├── requirements.txt
│
├── data/                    ← LAYER 1: Data retrieval
│   ├── __init__.py
│   ├── fetcher.py           ← All API calls (Alpha Vantage). Cached.
│   └── mock.py              ← Demo data generator (GBM random walk)
│
├── analytics/               ← LAYER 2: Pure math. No UI, no API calls.
│   ├── __init__.py
│   ├── momentum.py          ← RSI, VWAP, SMA, EMA, Bollinger Bands
│   ├── risk.py              ← VaR, CVaR, Drawdown, EWMA vol, distribution stats
│   ├── performance.py       ← Sharpe, Sortino, Jensen's Alpha, IR, CAGR, Beta
│   └── portfolio.py         ← Correlation, MVO optimisation, risk contribution
│
├── ui/                      ← LAYER 3: Presentation only.
│   ├── __init__.py
│   ├── theme.py             ← All CSS + Plotly colour/layout defaults
│   └── components.py        ← Sidebar, KPI ribbon, callout boxes, helpers
│
└── tabs/                    ← LAYER 4: Tab views. Calls analytics + ui only.
    ├── __init__.py
    ├── tab1_pulse.py        ← 📡 Market Pulse & Momentum
    ├── tab2_risk.py         ← 🛡️  Risk & Volatility Vault
    ├── tab3_alpha.py        ← ⚡ Alpha & Performance Lab
    ├── tab4_macro.py        ← 🌐 Macro Sensitivity (Econometrics)
    └── tab5_portfolio.py    ← 🧬 Portfolio Engine & Optimizer
```

## Dependency Rules (strict layering)

```
tabs → analytics, ui       ✅
tabs → data                ❌  (tabs never call fetcher directly)
analytics → data           ❌  (analytics are pure functions)
ui → analytics             ❌  (ui never does math)
app.py → everything        ✅  (only app.py wires layers together)
```

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## API Key

Get a free Alpha Vantage key at https://alphavantage.co  
Enter it in the sidebar, or enable **Demo Mode** to use synthetic data.

## Adding a New Indicator

1. Add the pure function to the relevant `analytics/` module
2. Import it in the tab that needs it
3. Display it using helpers from `ui/components.py`
4. Done — no changes needed to `app.py`
