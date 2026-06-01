import dash_bootstrap_components as dbc
from dash import html

from app.components.header import COLORS

_LABEL_COLORS = {
    "bullish": COLORS["bullish"],
    "bearish": COLORS["bearish"],
    "neutral": COLORS["neutral"],
    "insufficient_data": COLORS["neutral"],
}


def make_signal_summary(signal: dict | None) -> dbc.Card:
    if not signal:
        return dbc.Card(
            style={"backgroundColor": COLORS["card"], "border": "none", "padding": "20px"},
            children=[html.P("No signal data available",
                             style={"color": COLORS["text_secondary"]})],
        )

    label = signal.get("signal_label", "insufficient_data")
    score = signal.get("composite_signal")
    close = signal.get("close_price")
    rsi = signal.get("rsi_14")
    colour = _LABEL_COLORS.get(label, COLORS["neutral"])

    return dbc.Card(
        style={"backgroundColor": COLORS["card"], "border": "none", "padding": "20px"},
        children=[
            dbc.Row([
                dbc.Col([
                    html.Div(
                        f"{score:.1f}" if score is not None else "—",
                        style={"fontSize": "3rem", "fontWeight": "700",
                               "color": colour, "lineHeight": "1"},
                    ),
                    html.Div("Composite Score", style={"color": COLORS["text_secondary"],
                                                       "fontSize": "0.75rem"}),
                ], width=3),
                dbc.Col([
                    dbc.Badge(
                        label.upper().replace("_", " "),
                        style={"backgroundColor": colour, "fontSize": "0.9rem",
                               "padding": "8px 16px"},
                    ),
                ], width=3, className="d-flex align-items-center"),
                dbc.Col([
                    _stat("Price", f"${close:,.2f}" if close else "—"),
                    _stat("RSI (14)", f"{rsi:.1f}" if rsi else "—"),
                    _stat("Sentiment", f"{signal.get('sentiment_score', 0):+.3f}"),
                ], width=6),
            ]),
        ],
    )


def _stat(label: str, value: str) -> html.Div:
    return html.Div([
        html.Span(f"{label}: ", style={"color": COLORS["text_secondary"],
                                       "fontSize": "0.8rem"}),
        html.Span(value, style={"color": COLORS["text_primary"],
                                "fontWeight": "600", "fontSize": "0.85rem"}),
    ], style={"marginBottom": "4px"})
