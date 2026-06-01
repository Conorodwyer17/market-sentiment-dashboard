from dash import Input, Output, State, callback, no_update

from app import api_client
from app.components.asset_selector import make_asset_selector
from app.components.headlines_table import make_headlines_table
from app.components.price_chart import make_price_chart
from app.components.rsi_chart import make_rsi_chart
from app.components.sentiment_chart import make_sentiment_chart
from app.components.signal_history import make_signal_history
from app.components.signal_summary import make_signal_summary


@callback(
    Output("assets-store", "data"),
    Output("asset-selector-container", "children"),
    Output("backend-error-banner", "is_open"),
    Input("refresh-interval", "n_intervals"),
)
def refresh_assets(n):
    assets = api_client.get_assets()
    backend_error = len(assets) == 0
    selector = make_asset_selector(assets)
    return assets, selector, backend_error


@callback(
    Output("finbert-loading-banner", "is_open"),
    Input("refresh-interval", "n_intervals"),
)
def check_finbert(n):
    health = api_client.get_health()
    if health is None:
        return False
    return not health.get("finbert_loaded", True)


@callback(
    Output("signal-summary-container", "children"),
    Input("asset-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_signal_summary(ticker, n):
    if not ticker:
        return make_signal_summary(None)
    return make_signal_summary(api_client.get_signal(ticker))


@callback(
    Output("price-chart-container", "children"),
    Input("asset-dropdown", "value"),
    Input("period-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_price_chart(ticker, days, n):
    if not ticker:
        return make_price_chart([], "—")
    bars = api_client.get_prices(ticker, days or 90)
    return make_price_chart(bars, ticker)


@callback(
    Output("rsi-chart-container", "children"),
    Input("asset-dropdown", "value"),
    Input("period-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_rsi_chart(ticker, days, n):
    if not ticker:
        return make_rsi_chart([], "—")
    bars = api_client.get_prices(ticker, days or 90)
    return make_rsi_chart(bars, ticker)


@callback(
    Output("sentiment-chart-container", "children"),
    Output("headlines-container", "children"),
    Input("asset-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_news_panels(ticker, n):
    if not ticker:
        return make_sentiment_chart([], "—"), make_headlines_table([], "—")
    articles = api_client.get_news(ticker, hours=48)
    return make_sentiment_chart(articles, ticker), make_headlines_table(articles, ticker)


@callback(
    Output("signal-history-container", "children"),
    Input("asset-dropdown", "value"),
    Input("refresh-interval", "n_intervals"),
)
def update_signal_history(ticker, n):
    if not ticker:
        return make_signal_history([], "—")
    history = api_client.get_signal_history(ticker, days=30)
    return make_signal_history(history, ticker)


@callback(
    Output("assets-store", "data", allow_duplicate=True),
    Output("asset-selector-container", "children", allow_duplicate=True),
    Output("add-ticker-feedback", "children"),
    Output("add-ticker-input", "value"),
    Input("add-ticker-btn", "n_clicks"),
    State("add-ticker-input", "value"),
    prevent_initial_call=True,
)
def add_ticker(n_clicks, ticker_raw):
    """POST a new ticker to the backend, then refresh the asset selector."""
    if not n_clicks or not ticker_raw:
        return no_update, no_update, "", no_update

    ticker = ticker_raw.strip().upper()
    if not ticker:
        return no_update, no_update, "Enter a ticker symbol.", no_update

    result = api_client.add_asset(ticker)
    if result is None:
        # POST failed — could be duplicate (409) or invalid
        return no_update, no_update, f"Could not add {ticker}. Check the symbol or it may already be tracked.", ""

    # Refresh asset list after successful add
    assets = api_client.get_assets()
    selector = make_asset_selector(assets)
    return assets, selector, f"✓ {ticker} added — data fetches on next scheduler tick (≤15 min).", ""
