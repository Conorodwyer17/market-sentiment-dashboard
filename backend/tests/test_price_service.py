from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio

from app.services.price_service import (
    DataFetchError,
    PriceService,
    RateLimitError,
    _fetch_with_fallback,
    fetch_equity_prices,
    fetch_prices_yfinance_fallback,
    store_price_bars,
)
from app.models.orm import PriceBar


@pytest.mark.asyncio
async def test_parse_av_response(mock_alpha_vantage_response):
    """Alpha Vantage JSON is correctly parsed into bar dicts."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_alpha_vantage_response
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(
                get=AsyncMock(return_value=mock_resp)
            )
        )
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        bars = await fetch_equity_prices("AAPL", "fake_key")

    assert len(bars) == 90
    assert bars[0]["date"] < bars[-1]["date"]   # ascending order
    assert all(k in bars[0] for k in ("open", "high", "low", "close", "volume", "source"))
    assert bars[0]["source"] == "alphavantage"


@pytest.mark.asyncio
async def test_yfinance_fallback_triggered_on_rate_limit():
    """yfinance fallback is called when Alpha Vantage raises RateLimitError."""
    rate_limit_resp = {"Note": "API call frequency exceeded."}
    fallback_bars = [
        {"date": "2025-01-01", "open": 100.0, "high": 105.0, "low": 99.0,
         "close": 102.0, "volume": 5000, "source": "yfinance"}
    ]
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = rate_limit_resp
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "app.services.price_service.fetch_prices_yfinance_fallback",
            new=AsyncMock(return_value=fallback_bars),
        ) as mock_fallback:
            result = await _fetch_with_fallback("AAPL", "fake_key")

    mock_fallback.assert_called_once_with("AAPL")
    assert result == fallback_bars


@pytest.mark.asyncio
async def test_invalid_ticker_raises_value_error():
    """Alpha Vantage error response raises ValueError for bad tickers."""
    error_resp = {"Error Message": "Invalid API call."}
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = error_resp
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(ValueError, match="invalid ticker"):
            await fetch_equity_prices("INVALID_TICKER_XYZ", "fake_key")


@pytest.mark.asyncio
async def test_yfinance_fallback_returns_bars():
    """yfinance fallback correctly parses DataFrame into bar dicts."""
    import pandas as _pd
    dates = _pd.to_datetime(["2025-01-02", "2025-01-03"])
    df = _pd.DataFrame({
        "Open": [100.0, 101.0],
        "High": [105.0, 106.0],
        "Low": [99.0, 100.0],
        "Close": [102.0, 103.0],
        "Volume": [1_000_000, 1_200_000],
    }, index=dates)
    df.index.name = "Date"

    with patch("yfinance.download", return_value=df):
        bars = await fetch_prices_yfinance_fallback("AAPL")

    assert len(bars) == 2
    assert bars[0]["source"] == "yfinance"
    assert bars[0]["date"] == "2025-01-02"
    assert bars[0]["close"] == 102.0


@pytest.mark.asyncio
async def test_fetch_crypto_prices():
    """fetch_crypto_prices parses DIGITAL_CURRENCY_DAILY response correctly."""
    from app.services.price_service import fetch_crypto_prices
    crypto_response = {
        "Time Series (Digital Currency Daily)": {
            "2025-01-02": {
                "1a. open (USD)": "50000.0",
                "2a. high (USD)": "52000.0",
                "3a. low (USD)": "49000.0",
                "4a. close (USD)": "51000.0",
                "5. volume": "12345",
            },
            "2025-01-01": {
                "1a. open (USD)": "48000.0",
                "2a. high (USD)": "51000.0",
                "3a. low (USD)": "47000.0",
                "4a. close (USD)": "50000.0",
                "5. volume": "10000",
            },
        }
    }
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = crypto_response
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        bars = await fetch_crypto_prices("BTC-USD", "fake_key")

    assert len(bars) == 2
    assert bars[0]["date"] < bars[1]["date"]   # ascending
    assert bars[0]["close"] == 50000.0
    assert bars[0]["source"] == "alphavantage"


@pytest.mark.asyncio
async def test_crypto_rate_limit_uses_fallback():
    """Crypto rate limit falls back to yfinance."""
    from app.services.price_service import _fetch_with_fallback
    rate_limit_resp = {"Information": "Rate limit reached."}
    fallback_bars = [{"date": "2025-01-01", "open": 50000.0, "high": 52000.0,
                      "low": 49000.0, "close": 51000.0, "volume": 0, "source": "yfinance"}]
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = rate_limit_resp
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "app.services.price_service.fetch_prices_yfinance_fallback",
            new=AsyncMock(return_value=fallback_bars),
        ) as mock_fb:
            result = await _fetch_with_fallback("BTC-USD", "fake_key")

    mock_fb.assert_called_once_with("BTC-USD")
    assert result[0]["source"] == "yfinance"


@pytest.mark.asyncio
async def test_price_service_get_price_bars(db_session, session_factory):
    """get_price_bars filters correctly by ticker and date range."""
    from datetime import datetime, timedelta
    from app.services.price_service import PriceService
    svc = PriceService(session_factory, "fake_key")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    old_date = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
    bars_data = [
        {"date": old_date, "open": 100.0, "high": 105.0, "low": 99.0,
         "close": 102.0, "volume": 1000, "source": "yfinance"},
        {"date": today, "open": 110.0, "high": 115.0, "low": 109.0,
         "close": 112.0, "volume": 2000, "source": "yfinance"},
    ]
    await store_price_bars("AAPL", bars_data, db_session)
    result = await svc.get_price_bars("AAPL", days=30, session=db_session)
    # Only today's bar is within 30 days
    assert len(result) == 1
    assert result[0].date == today


@pytest.mark.asyncio
async def test_no_duplicate_price_bars(db_session):
    """Storing the same bars twice does not create duplicates."""
    bars = [
        {"date": "2025-01-01", "open": 100.0, "high": 105.0, "low": 99.0,
         "close": 102.0, "volume": 1000, "source": "alphavantage"},
    ]
    await store_price_bars("AAPL", bars, db_session)
    await store_price_bars("AAPL", bars, db_session)

    from sqlalchemy import select
    result = await db_session.execute(
        select(PriceBar).where(PriceBar.ticker == "AAPL")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
