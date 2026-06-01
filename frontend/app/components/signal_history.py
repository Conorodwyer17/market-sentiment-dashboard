import plotly.graph_objects as go
from dash import dcc

from app.components.header import COLORS


def make_signal_history(snapshots: list, ticker: str) -> dcc.Graph:
    fig = go.Figure()

    if snapshots:
        dates = [s.get("computed_at", "")[:10] for s in snapshots]
        scores = [s.get("composite_signal") for s in snapshots]

        fig.add_trace(go.Scatter(
            x=dates, y=scores,
            fill="tozeroy",
            line={"color": "#74b9ff", "width": 2},
            fillcolor="rgba(116, 185, 255, 0.15)",
            name="Signal",
        ))

        # Threshold lines
        fig.add_hline(y=65, line_color=COLORS["bullish"], line_dash="dot",
                      line_width=1, annotation_text="Bullish",
                      annotation_font_color=COLORS["bullish"])
        fig.add_hline(y=40, line_color=COLORS["bearish"], line_dash="dot",
                      line_width=1, annotation_text="Bearish",
                      annotation_font_color=COLORS["bearish"])

    fig.update_layout(
        title=f"{ticker} — Signal Score History",
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["background"],
        font={"color": COLORS["text_primary"]},
        xaxis={"showgrid": False, "color": COLORS["text_secondary"]},
        yaxis={"showgrid": True, "gridcolor": COLORS["accent"],
               "color": COLORS["text_secondary"], "range": [0, 100]},
        margin={"l": 40, "r": 20, "t": 40, "b": 20},
        showlegend=False,
    )

    return dcc.Graph(figure=fig, id="signal-history-chart", style={"height": "220px"})
