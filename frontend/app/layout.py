import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.header import COLORS, make_header


def make_layout() -> html.Div:
    return html.Div(
        style={"backgroundColor": COLORS["background"], "minHeight": "100vh",
               "fontFamily": "'Segoe UI', sans-serif"},
        children=[
            # Auto-refresh every 60 seconds
            dcc.Interval(id="refresh-interval", interval=60_000, n_intervals=0),

            # Stores for sharing data between callbacks
            dcc.Store(id="assets-store"),

            make_header(),

            dbc.Container(
                fluid=True,
                style={"padding": "16px"},
                children=[
                    # Asset selector row — populated by callback after initial load
                    html.Div(id="asset-selector-container", style={"marginBottom": "12px"}),

                    # Signal summary
                    html.Div(id="signal-summary-container", style={"marginBottom": "12px"}),

                    # Price chart (full width)
                    dbc.Row([
                        dbc.Col(html.Div(id="price-chart-container"), width=12),
                    ], className="mb-3"),

                    # RSI | Sentiment | Signal history
                    dbc.Row([
                        dbc.Col(html.Div(id="rsi-chart-container"), width=4),
                        dbc.Col(html.Div(id="sentiment-chart-container"), width=4),
                        dbc.Col(html.Div(id="signal-history-container"), width=4),
                    ], className="mb-3"),

                    # Headlines table
                    dbc.Row([
                        dbc.Col(html.Div(id="headlines-container"), width=12),
                    ]),
                ],
            ),
        ],
    )
