import dash_bootstrap_components as dbc
from dash import html

COLORS = {
    "background": "#1a1a2e",
    "card": "#16213e",
    "accent": "#0f3460",
    "bullish": "#00b894",
    "bearish": "#d63031",
    "neutral": "#636e72",
    "text_primary": "#dfe6e9",
    "text_secondary": "#b2bec3",
    "warning_bg": "#fdcb6e",
    "warning_text": "#2d3436",
    "chart_ma20": "#74b9ff",
    "chart_ma50": "#fd79a8",
    "chart_up": "#00b894",
    "chart_down": "#d63031",
}


def make_header() -> dbc.Container:
    return dbc.Container(
        fluid=True,
        style={"backgroundColor": COLORS["accent"], "padding": "0"},
        children=[
            dbc.Row([
                dbc.Col(
                    html.H3(
                        "Market Sentiment Dashboard",
                        style={"color": COLORS["text_primary"], "margin": "0",
                               "padding": "12px 0", "fontWeight": "600"},
                    ),
                    width=True,
                ),
            ], style={"padding": "0 20px"}),

            # Mandatory disclaimer banner
            dbc.Alert(
                [
                    html.Strong("Research tool only. "),
                    "Signal scores combine price momentum and news sentiment analysis. "
                    "They do not predict future price movements. Not financial advice.",
                ],
                color="warning",
                style={
                    "borderRadius": "0",
                    "margin": "0",
                    "padding": "8px 20px",
                    "fontSize": "0.85rem",
                    "backgroundColor": COLORS["warning_bg"],
                    "color": COLORS["warning_text"],
                    "border": "none",
                },
            ),

            # Backend connection error banner (hidden by default)
            dbc.Alert(
                "Backend connection error — displaying cached data",
                id="backend-error-banner",
                color="danger",
                is_open=False,
                dismissable=False,
                style={"borderRadius": "0", "margin": "0", "padding": "8px 20px",
                       "fontSize": "0.85rem", "border": "none"},
            ),

            # FinBERT loading banner (hidden by default)
            dbc.Alert(
                "FinBERT model loading — sentiment scores will appear shortly",
                id="finbert-loading-banner",
                color="info",
                is_open=False,
                dismissable=False,
                style={"borderRadius": "0", "margin": "0", "padding": "8px 20px",
                       "fontSize": "0.85rem", "border": "none"},
            ),
        ],
    )
