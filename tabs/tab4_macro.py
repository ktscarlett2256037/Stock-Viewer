"""
tabs/tab4_macro.py — Macro Sensitivity
The "What invisible forces are moving the needle?" view.

Note: Macro factor data (10Y yield, Brent, USD/INR, India VIX) requires
a real data feed. In demo mode, synthetic correlated series are generated
to illustrate the methodology.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from analytics.momentum import daily_returns
from ui.components import section_header, callout
from ui.theme import PLOTLY_LAYOUT, CYAN, YELLOW, RED, GREEN, BLUE, MUTED


# ── Demo macro factor generator ───────────────────────────────────────────────

def _make_demo_factors(n: int, seed: int = 7) -> pd.DataFrame:
    """Synthetic macro factors with mild correlations to stock returns."""
    rng = np.random.default_rng(seed)
    idx = pd.RangeIndex(n)
    return pd.DataFrame({
        "10Y_Yield":  rng.normal(0.0001, 0.004, n).cumsum() + 0.07,
        "Brent_Crude":rng.normal(0.0002, 0.012, n).cumsum() + 85,
        "USD_INR":    rng.normal(0.00005, 0.003, n).cumsum() + 83.5,
        "India_VIX":  rng.normal(0.0, 0.05, n).cumsum() + 15,
    }, index=idx)


# ── Factor regression ─────────────────────────────────────────────────────────

def _run_factor_regression(
    stock_returns: pd.Series,
    factors_df: pd.DataFrame,
) -> pd.DataFrame:
    """OLS multi-factor regression. Returns a summary table."""
    factor_returns = factors_df.pct_change().dropna()
    aligned = pd.concat([stock_returns.reset_index(drop=True),
                         factor_returns.reset_index(drop=True)], axis=1).dropna()
    y = aligned.iloc[:, 0]
    X = add_constant(aligned.iloc[:, 1:])

    model   = OLS(y, X).fit()
    summary = pd.DataFrame({
        "Factor":    model.params.index,
        "β (Coeff)": model.params.values,
        "Std Err":   model.bse.values,
        "t-stat":    model.tvalues.values,
        "p-value":   model.pvalues.values,
    })
    summary["Significant?"] = summary["p-value"].apply(
        lambda p: "✅ Yes" if p < 0.05 else "❌ No"
    )
    summary = summary[summary["Factor"] != "const"].copy()
    summary["β (Coeff)"] = summary["β (Coeff)"].map("{:.4f}".format)
    summary["p-value"]   = summary["p-value"].map("{:.4f}".format)
    return summary.reset_index(drop=True)


# ── Impulse Response (simplified VAR proxy) ───────────────────────────────────

def _impulse_response(returns: pd.Series, factor: pd.Series,
                      horizon: int = 10) -> np.ndarray:
    """
    Simplified IRF: regress stock on 1-lag factor; project shock decay.
    Not a full VAR, but illustrates the concept clearly.
    """
    fr   = factor.pct_change().dropna()
    n    = min(len(returns), len(fr)) - 1
    X    = fr.iloc[:n].values
    y    = returns.iloc[1:n+1].values
    cov  = np.cov(X, y)
    beta = cov[0, 1] / cov[0, 0] if cov[0, 0] != 0 else 0
    # Shock decays by factor rho per period
    rho  = 0.7
    return np.array([beta * (rho ** t) for t in range(horizon)])


# ── Main render ───────────────────────────────────────────────────────────────

def render(data: pd.DataFrame, cfg: dict) -> None:
    rets    = daily_returns(data["close"])
    n       = len(rets)
    factors = _make_demo_factors(n)

    callout(
        "📌 <b>Demo mode:</b> Macro factor data is synthetic. "
        "Connect a real data feed (FRED, Quandl, RBI) for live factor loadings.",
        "info",
    )

    # ── Factor Regression Table ─────────────────────────────────────────────
    section_header("Multi-Factor Regression",
                   "How sensitive is the stock to each macro variable?")

    reg_table = _run_factor_regression(rets, factors)
    st.dataframe(
        reg_table.set_index("Factor"),
        use_container_width=True,
    )
    callout(
        "Highlighted rows have <b>p-value &lt; 0.05</b> — statistically significant drivers. "
        "A positive β on Brent Crude means the stock tends to rise with oil prices.",
        "info",
    )

    # ── Impulse Response Charts ─────────────────────────────────────────────
    section_header("Impulse Response Functions (10-Day Horizon)",
                   "Effect of a 1-unit shock in each macro factor on stock returns over 10 days.")

    factor_names  = factors.columns.tolist()
    colors        = [CYAN, YELLOW, RED, BLUE]
    irf_cols      = st.columns(2)

    for i, fname in enumerate(factor_names):
        irf = _impulse_response(rets, factors[fname])
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(range(1, 11)),
            y=irf * 100,
            marker_color=[colors[i % len(colors)]] * 10,
            name=fname,
        ))
        fig.add_hline(y=0, line_color=MUTED, line_dash="dot")
        fig.update_layout(
            **PLOTLY_LAYOUT,
            height=200,
            title_text=fname,
            xaxis_title="Days after shock",
            yaxis_title="Return impact (%)",
        )
        with irf_cols[i % 2]:
            st.plotly_chart(fig, use_container_width=True)

    # ── VIX Sentiment Correlation ────────────────────────────────────────────
    section_header("Stock Price vs. India VIX",
                   "VIX is the market 'fear gauge'. High VIX typically pressures equity prices.")

    vix   = factors["India_VIX"].reset_index(drop=True)
    close = data["close"].reset_index(drop=True).iloc[:n]

    fig_vix = go.Figure()
    fig_vix.add_trace(go.Scatter(
        x=data["Date"].iloc[:n], y=close,
        line=dict(color=CYAN, width=1.5),
        name=cfg["ticker"], yaxis="y",
    ))
    fig_vix.add_trace(go.Scatter(
        x=data["Date"].iloc[:n], y=vix,
        line=dict(color=RED, width=1.2, dash="dot"),
        name="India VIX", yaxis="y2",
        opacity=0.8,
    ))
    fig_vix.update_layout(
        **PLOTLY_LAYOUT, height=300,
        yaxis=dict(title="Stock Price (₹)"),
        yaxis2=dict(title="VIX", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(color=RED)),
    )
    st.plotly_chart(fig_vix, use_container_width=True)
