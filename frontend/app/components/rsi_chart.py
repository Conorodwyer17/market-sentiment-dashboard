import plotly.graph_objects as go
from dash import dcc

from app.components.header import COLORS


def _compute_rsi(closes: list[float], period: int = 14) -> list[float | None]:
    if len(closes) < period + 1:
        return [None] * len(closes)
    rsi = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi.append(100 - (100 / (1 + rs)))
    return rsi


def make_rsi_chart(bars: list, ticker: str) -> dcc.Graph:
    fig = go.Figure()

    if bars:
        dates = [b["date"] for b in bars]
        closes = [b["close"] for b in bars]
        rsi_values = _compute_rsi(closes)

        fig.add_trace(go.Scatter(
            x=dates, y=rsi_values,
            line={"color": "#a29bfe", "width": 2},
            name="RSI 14",
        ))

        # Overbought / oversold zones
        fig.add_hrect(y0=70, y1=100, fillcolor=COLORS["bearish"], opacity=0.08, line_width=0)
        fig.add_hrect(y0=0, y1=30, fillcolor=COLORS["bullish"], opacity=0.08, line_width=0)
        fig.add_hline(y=70, line_color=COLORS["bearish"], line_dash="dot", line_width=1)
        fig.add_hline(y=30, line_color=COLORS["bullish"], line_dash="dot", line_width=1)

    fig.update_layout(
        title=f"{ticker} — RSI (14)",
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["background"],
        font={"color": COLORS["text_primary"]},
        xaxis={"showgrid": False, "color": COLORS["text_secondary"]},
        yaxis={"showgrid": True, "gridcolor": COLORS["accent"],
               "color": COLORS["text_secondary"], "range": [0, 100]},
        margin={"l": 40, "r": 20, "t": 40, "b": 20},
        showlegend=False,
    )

    return dcc.Graph(figure=fig, id="rsi-chart", style={"height": "220px"})
