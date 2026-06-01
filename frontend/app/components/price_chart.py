import plotly.graph_objects as go
from dash import dcc

from app.components.header import COLORS


def make_price_chart(bars: list, ticker: str) -> dcc.Graph:
    if not bars:
        fig = go.Figure()
        fig.update_layout(
            title=f"{ticker} — No price data",
            paper_bgcolor=COLORS["card"],
            plot_bgcolor=COLORS["card"],
            font={"color": COLORS["text_primary"]},
        )
        return dcc.Graph(figure=fig, id="price-chart", style={"height": "350px"})

    dates = [b["date"] for b in bars]
    closes = [b["close"] for b in bars]

    # Moving averages
    def rolling_mean(values, n):
        return [
            sum(values[max(0, i - n + 1): i + 1]) / min(i + 1, n)
            if i >= n - 1 else None
            for i in range(len(values))
        ]

    ma20 = rolling_mean(closes, 20)
    ma50 = rolling_mean(closes, 50)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=dates,
        open=[b["open"] for b in bars],
        high=[b["high"] for b in bars],
        low=[b["low"] for b in bars],
        close=closes,
        increasing_line_color=COLORS["chart_up"],
        decreasing_line_color=COLORS["chart_down"],
        name=ticker,
        showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=ma20,
        line={"color": COLORS["chart_ma20"], "width": 1.5},
        name="MA 20",
        connectgaps=False,
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=ma50,
        line={"color": COLORS["chart_ma50"], "width": 1.5},
        name="MA 50",
        connectgaps=False,
    ))

    fig.update_layout(
        title=f"{ticker} — Price",
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["background"],
        font={"color": COLORS["text_primary"]},
        xaxis={"showgrid": False, "color": COLORS["text_secondary"]},
        yaxis={"showgrid": True, "gridcolor": COLORS["accent"],
               "color": COLORS["text_secondary"]},
        legend={"font": {"color": COLORS["text_secondary"]}},
        margin={"l": 40, "r": 20, "t": 40, "b": 20},
        xaxis_rangeslider_visible=False,
    )

    return dcc.Graph(figure=fig, id="price-chart", style={"height": "350px"})
