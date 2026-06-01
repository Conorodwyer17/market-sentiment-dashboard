from collections import defaultdict

import plotly.graph_objects as go
from dash import dcc

from app.components.header import COLORS


def make_sentiment_chart(articles: list, ticker: str) -> dcc.Graph:
    """Stacked bar chart of daily positive/negative/neutral article counts."""
    fig = go.Figure()

    if articles:
        daily: dict[str, dict] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
        for a in articles:
            date = (a.get("published_at") or "")[:10]
            label = a.get("sentiment_label") or "neutral"
            if label in daily[date]:
                daily[date][label] += 1

        dates = sorted(daily.keys())
        for label, colour in [
            ("positive", COLORS["bullish"]),
            ("neutral", COLORS["neutral"]),
            ("negative", COLORS["bearish"]),
        ]:
            fig.add_trace(go.Bar(
                x=dates,
                y=[daily[d][label] for d in dates],
                name=label.capitalize(),
                marker_color=colour,
            ))

        fig.update_layout(barmode="stack")

    fig.update_layout(
        title=f"{ticker} — Daily Sentiment",
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["background"],
        font={"color": COLORS["text_primary"]},
        xaxis={"showgrid": False, "color": COLORS["text_secondary"]},
        yaxis={"showgrid": True, "gridcolor": COLORS["accent"],
               "color": COLORS["text_secondary"]},
        legend={"font": {"color": COLORS["text_secondary"]}},
        margin={"l": 40, "r": 20, "t": 40, "b": 20},
    )

    return dcc.Graph(figure=fig, id="sentiment-chart", style={"height": "220px"})
