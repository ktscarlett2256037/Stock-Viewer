from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from analytics.momentum import daily_returns
from ui.components import section_header, callout
from ui.theme import apply_layout, CYAN, YELLOW, RED, BLUE, MUTED

def _make_demo_factors(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "10Y_Yield":   rng.normal(0.0001, 0.004, n).cumsum() + 0.07,
        "Brent_Crude": rng.normal(0.0002, 0.012, n).cumsum() + 85,
        "USD_INR":     rng.normal(0.00005, 0.003, n).cumsum() + 83.5,
        "India_VIX":   rng.normal(0.0, 0.05, n).cumsum() + 15,
    })

def _run_regression(stock_returns, factors_df):
    fr      = factors_df.pct_change().dropna()
    n       = min(len(stock_returns), len(fr)) - 1
    aligned = pd.concat([stock_returns.reset_index(drop=True)[:n],
                         fr.reset_index(drop=True)[:n]], axis=1).dropna()
    y = aligned.iloc[:, 0]
    X = add_constant(aligned.iloc[:, 1:])
    model = OLS(y, X).fit()
    df = pd.DataFrame({
        "Factor":    model.params.index,
        "β Coeff":   model.params.values.round(4),
        "p-value":   model.pvalues.values.round(4),
        "Significant": ["✅" if p < 0.05 else "❌" for p in model.pvalues.values],
    })
    return df[df["Factor"] != "const"].reset_index(drop=True)

def render(data: pd.DataFrame, cfg: dict) -> None:
    rets    = daily_returns(data["close"])
    n       = len(rets)
    factors = _make_demo_factors(n)

    callout("📌 Macro factor data is synthetic in demo mode. Connect FRED or Quandl for live data.", "info")

    section_header("Multi-Factor Regression")
    st.dataframe(_run_regression(rets, factors).set_index("Factor"), use_container_width=True)
    callout("✅ rows have p-value &lt; 0.05 — statistically significant macro drivers.", "info")

    section_header("Impulse Response (10-Day Horizon)")
    colors = [CYAN, YELLOW, RED, BLUE]
    cols   = st.columns(2)
    for i, fname in enumerate(factors.columns):
        fr   = factors[fname].pct_change().dropna()
        nn   = min(len(rets), len(fr)) - 1
        X    = fr.values[:nn]
        y    = rets.values[1:nn+1]
        beta = np.cov(X, y)[0,1] / np.var(X) if np.var(X) else 0
        irf  = [beta * (0.7 ** t) for t in range(10)]
        fig  = go.Figure()
        fig.add_trace(go.Bar(x=list(range(1,11)), y=[v*100 for v in irf],
            marker_color=colors[i % 4], name=fname))
        fig.add_hline(y=0, line_color=MUTED, line_dash="dot")
        apply_layout(fig, height=200,
            xaxis=dict(title="Days after shock", gridcolor="#1e2230"),
            yaxis=dict(title="Impact (%)", gridcolor="#1e2230"))
        fig.update_layout(title_text=fname)
        with cols[i % 2]:
            st.plotly_chart(fig, use_container_width=True)

    section_header("Stock Price vs India VIX")
    vix   = factors["India_VIX"].reset_index(drop=True)
    close = data["close"].reset_index(drop=True).iloc[:n]
    fig   = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"].iloc[:n], y=close,
        line=dict(color=CYAN, width=1.5), name=cfg["ticker"]))
    fig.add_trace(go.Scatter(x=data["Date"].iloc[:n], y=vix,
        line=dict(color=RED, width=1.2, dash="dot"), name="India VIX", yaxis="y2"))
    apply_layout(fig, height=300,
        yaxis=dict(title="Stock Price (₹)", gridcolor="#1e2230"),
        yaxis2=dict(title="VIX", overlaying="y", side="right", showgrid=False))
    st.plotly_chart(fig, use_container_width=True)
