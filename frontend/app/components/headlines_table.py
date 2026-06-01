import dash_bootstrap_components as dbc
from dash import html

from app.components.header import COLORS

_BADGE_COLORS = {
    "positive": "success",
    "negative": "danger",
    "neutral": "secondary",
}


def make_headlines_table(articles: list, ticker: str) -> dbc.Card:
    if not articles:
        return dbc.Card(
            style={"backgroundColor": COLORS["card"], "border": "none", "padding": "16px"},
            children=[
                html.H6(f"{ticker} — Recent Headlines",
                        style={"color": COLORS["text_primary"]}),
                html.P("No recent news available",
                       style={"color": COLORS["text_secondary"]}),
            ],
        )

    rows = []
    for art in articles[:20]:   # cap at 20 rows
        label = art.get("sentiment_label") or "neutral"
        url = art.get("url") or "#"
        headline = art.get("headline") or "(no headline)"
        published = (art.get("published_at") or "")[:10]

        rows.append(html.Tr([
            html.Td(
                html.A(headline, href=url, target="_blank",
                       style={"color": COLORS["text_primary"], "fontSize": "0.82rem"}),
                style={"width": "75%"},
            ),
            html.Td(
                dbc.Badge(label.capitalize(), color=_BADGE_COLORS.get(label, "secondary"),
                          style={"fontSize": "0.7rem"}),
                style={"textAlign": "center"},
            ),
            html.Td(
                published,
                style={"color": COLORS["text_secondary"], "fontSize": "0.75rem",
                       "whiteSpace": "nowrap"},
            ),
        ], style={"borderBottom": f"1px solid {COLORS['accent']}"}))

    return dbc.Card(
        style={"backgroundColor": COLORS["card"], "border": "none", "padding": "16px"},
        children=[
            html.H6(f"{ticker} — Recent Headlines",
                    style={"color": COLORS["text_primary"], "marginBottom": "12px"}),
            html.Table(
                [html.Tbody(rows)],
                style={"width": "100%", "borderCollapse": "collapse"},
            ),
        ],
    )
