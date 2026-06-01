import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.header import COLORS


def make_asset_selector(assets: list) -> dbc.Card:
    options = [{"label": a["ticker"], "value": a["ticker"]} for a in assets]
    default = options[0]["value"] if options else None

    return dbc.Card(
        style={"backgroundColor": COLORS["card"], "border": "none", "padding": "12px"},
        children=[
            dbc.Row([
                # ── Asset dropdown ──────────────────────────────────
                dbc.Col([
                    html.Label("Asset", style={"color": COLORS["text_secondary"],
                                               "fontSize": "0.8rem", "marginBottom": "4px"}),
                    dcc.Dropdown(
                        id="asset-dropdown",
                        options=options,
                        value=default,
                        clearable=False,
                        style={"backgroundColor": COLORS["accent"],
                               "color": COLORS["text_primary"]},
                    ),
                ], width=4),

                # ── Period dropdown ─────────────────────────────────
                dbc.Col([
                    html.Label("Period", style={"color": COLORS["text_secondary"],
                                                "fontSize": "0.8rem", "marginBottom": "4px"}),
                    dcc.Dropdown(
                        id="period-dropdown",
                        options=[
                            {"label": "30 days", "value": 30},
                            {"label": "90 days", "value": 90},
                            {"label": "180 days", "value": 180},
                        ],
                        value=90,
                        clearable=False,
                        style={"backgroundColor": COLORS["accent"],
                               "color": COLORS["text_primary"]},
                    ),
                ], width=3),

                # ── Add ticker ──────────────────────────────────────
                dbc.Col([
                    html.Label("Add ticker", style={"color": COLORS["text_secondary"],
                                                    "fontSize": "0.8rem", "marginBottom": "4px"}),
                    dbc.InputGroup([
                        dbc.Input(
                            id="add-ticker-input",
                            placeholder="e.g. AMD",
                            debounce=False,
                            style={"backgroundColor": COLORS["accent"],
                                   "color": COLORS["text_primary"],
                                   "border": f"1px solid {COLORS['neutral']}",
                                   "textTransform": "uppercase"},
                            maxLength=10,
                        ),
                        dbc.Button(
                            "Add",
                            id="add-ticker-btn",
                            color="primary",
                            size="sm",
                            style={"backgroundColor": COLORS["accent"],
                                   "borderColor": COLORS["neutral"]},
                        ),
                    ], size="sm"),
                ], width=3),

                # ── Add error feedback ──────────────────────────────
                dbc.Col(
                    html.Div(id="add-ticker-feedback",
                             style={"color": COLORS["bearish"], "fontSize": "0.75rem",
                                    "marginTop": "22px"}),
                    width=2,
                ),
            ], className="g-2", align="end"),
        ],
    )
