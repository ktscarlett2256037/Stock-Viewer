import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
* { font-family: 'Inter', sans-serif !important; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="stMetricValue"] { font-size: 1.25rem !important; color: #00ffcc; }
[data-testid="stMetricLabel"] { font-size: 0.72rem !important; color: #8892a4; }
[data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
.stMetric { background-color: #11141d; padding: 12px !important; border-radius: 6px; border: 1px solid #2a2e39; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: #0e1117; border-bottom: 1px solid #2a2e39; }
.stTabs [data-baseweb="tab"] { padding: 8px 16px; border-radius: 4px 4px 0 0; font-size: 0.82rem; color: #8892a4; }
.stTabs [aria-selected="true"] { background-color: #1a1e2e !important; color: #00ffcc !important; border-bottom: 2px solid #00ffcc; }
.qt-callout { background: #11141d; border-left: 3px solid #00ffcc; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 0.82rem; color: #c9d1d9; margin: 6px 0; }
.qt-warn { border-left-color: #f0c040; }
.qt-danger { border-left-color: #ff4b6e; }
.qt-section { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.10em; text-transform: uppercase; color: #8892a4; margin: 18px 0 8px 0; }
.news-card { background: #11141d; border: 1px solid #2a2e39; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px; }
.news-title { font-size: 0.88rem; font-weight: 500; color: #e6edf3; }
.news-meta { font-size: 0.75rem; color: #8892a4; margin-top: 4px; }
hr { border-color: #2a2e39 !important; }
"""

def inject_css() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

def apply_layout(fig, height: int = 400, **kwargs):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0e1117",
        font=dict(family="Inter, sans-serif", size=11, color="#c9d1d9"),
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#1a1e2e", bordercolor="#2a2e39", font_size=12),
        height=height,
    )
    if kwargs:
        fig.update_layout(**kwargs)
    return fig

PLOTLY_LAYOUT = {}
CYAN   = "#00ffcc"
BLUE   = "#00ccff"
YELLOW = "#f0c040"
RED    = "#ff4b6e"
GREEN  = "#00e676"
GREY   = "#2a2e39"
MUTED  = "#8892a4"
