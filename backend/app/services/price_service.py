import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.orm import Asset, PriceBar

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"


class RateLimitError(Exception):
    pass


class DataFetchError(Exception):
    pass


def _is_crypto(ticker: str) -> bool:
    return ticker.endswith("-USD")


def _av_crypto_symbol(ticker: str) -> str:
    """'BTC-USD' → 'BTC' for Alpha Vantage DIGITAL_CURRENCY_DAILY."""
    return ticker.replace("-USD", "")


async def fetch_equity_prices(ticker: str, api_key: str) -> list[dict]:
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "full",
        "apikey": api_key,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ALPHA_VANTAGE_BASE, params=params)
        response.raise_for_status()
        data = response.json()

    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage: invalid ticker {ticker}")
    if "Note" in data or "Information" in data:
        raise RateLimitError("Alpha Vantage daily limit reached")

    time_series = data.get("Time Series (Daily)", {})
    bars = []
    for date_str, values in time_series.items():
        bars.append({
            "date": date_str,
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": int(float(values["5. volume"])),
            "source": "alphavantage",
        })
    return sorted(bars, key=lambda x: x["date"])


async def fetch_crypto_prices(ticker: str, api_key: str) -> list[dict]:
    """ticker should be 'BTC-USD'; strips suffix for the API call."""
    symbol = _av_crypto_symbol(ticker)
    params = {
        "function": "DIGITAL_CURRENCY_DAILY",
        "symbol": symbol,
        "market": "USD",
        "apikey": api_key,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ALPHA_VANTAGE_BASE, params=params)
        response.raise_for_status()
        data = response.json()

    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage: invalid crypto ticker {ticker}")
    if "Note" in data or "Information" in data:
        raise RateLimitError("Alpha Vantage daily limit reached")

    time_series = data.get("Time Series (Digital Currency Daily)", {})
    bars = []
    for date_str, values in time_series.items():
        # Key names vary by response version; try both formats
        open_key = "1a. open (USD)" if "1a. open (USD)" in values else "1. open"
        high_key = "2a. high (USD)" if "2a. high (USD)" in values else "2. high"
        low_key = "3a. low (USD)" if "3a. low (USD)" in values else "3. low"
        close_key = "4a. close (USD)" if "4a. close (USD)" in values else "4. close"
        volume_key = "5. volume"
        bars.append({
            "date": date_str,
            "open": float(values[open_key]),
            "high": float(values[high_key]),
            "low": float(values[low_key]),
            "close": float(values[close_key]),
            "volume": int(float(values.get(volume_key, 0))),
            "source": "alphavantage",
        })
    return sorted(bars, key=lambda x: x["date"])


async def fetch_prices_yfinance_fallback(ticker: str) -> list[dict]:
    """Fallback via yfinance (Yahoo Finance). No API key required.

    Works for both US equities ('AAPL') and crypto pairs ('BTC-USD').
    """
    import asyncio
    import functools

    def _fetch_sync(t: str) -> list[dict]:
        import yfinance as yf
        df = yf.download(t, period="1y", interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"yfinance returned empty data for {t}")
        df = df.sort_index()
        # yfinance 0.2+ returns MultiIndex columns when single ticker;
        # flatten if needed
        if isinstance(df.columns, __import__('pandas').MultiIndex):
            df.columns = df.columns.get_level_values(0)
        bars = []
        for date, row in df.iterrows():
            bars.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
                "source": "yfinance",
            })
        return bars

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(_fetch_sync, ticker))
    except Exception as exc:
        raise DataFetchError(f"yfinance fallback failed for {ticker}: {exc}") from exc


async def _fetch_with_fallback(ticker: str, api_key: str) -> list[dict]:
    try:
        if _is_crypto(ticker):
            return await fetch_crypto_prices(ticker, api_key)
        return await fetch_equity_prices(ticker, api_key)
    except (RateLimitError, DataFetchError, ValueError) as exc:
        logger.warning("Alpha Vantage failed for %s (%s), trying yfinance", ticker, exc)
        return await fetch_prices_yfinance_fallback(ticker)


async def store_price_bars(ticker: str, bars: list[dict], session: AsyncSession) -> int:
    """Upsert price bars. Returns count of new rows inserted."""
    if not bars:
        return 0
    now = datetime.utcnow().isoformat() + "Z"
    inserted = 0
    for bar in bars:
        stmt = (
            sqlite_insert(PriceBar)
            .values(
                ticker=ticker,
                date=bar["date"],
                open=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=bar["volume"],
                source=bar["source"],
                fetched_at=now,
            )
            .on_conflict_do_nothing(index_elements=["ticker", "date"])
        )
        result = await session.execute(stmt)
        inserted += result.rowcount
    await session.commit()
    return inserted


class PriceService:
    def __init__(self, session_factory, api_key: str):
        self._session_factory = session_factory
        self._api_key = api_key

    async def fetch_and_store_all(self) -> None:
        """Scheduled job: fetch and store prices for all active assets.

        Spacing: Alpha Vantage free tier allows 5 requests/minute.
        A 13-second pause between calls keeps well under that limit.
        """
        import asyncio as _asyncio

        async with self._session_factory() as session:
            result = await session.execute(
                select(Asset).where(Asset.is_active == True)  # noqa: E712
            )
            assets = result.scalars().all()

        for i, asset in enumerate(assets):
            if i > 0:
                await _asyncio.sleep(13)   # ≤ 4.6 calls/min → under 5/min AV limit
            try:
                bars = await _fetch_with_fallback(asset.ticker, self._api_key)
                async with self._session_factory() as session:
                    count = await store_price_bars(asset.ticker, bars, session)
                logger.info("Stored %d new bars for %s", count, asset.ticker)
            except Exception as exc:
                logger.error("Failed to fetch prices for %s: %s", asset.ticker, exc)

    async def get_price_bars(
        self, ticker: str, days: int, session: AsyncSession
    ) -> list[PriceBar]:
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = await session.execute(
            select(PriceBar)
            .where(PriceBar.ticker == ticker, PriceBar.date >= cutoff)
            .order_by(PriceBar.date.asc())
        )
        return result.scalars().all()
