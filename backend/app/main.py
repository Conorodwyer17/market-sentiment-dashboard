import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.logging import configure_logging
from app.ml import finbert
from app.models.orm import Asset
from app.routers import assets, health, news, prices, sentiment, signals
from app.services.news_service import NewsService
from app.services.price_service import PriceService
from app.services.scheduler import create_scheduler
from app.services.sentiment_service import SentimentService
from app.services.signal_service import SignalService

configure_logging()
logger = logging.getLogger(__name__)


async def _seed_default_assets() -> None:
    """Insert default equity and crypto assets if the table is empty."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Asset).limit(1))
        if result.scalar() is not None:
            return

        now = datetime.utcnow().isoformat() + "Z"
        for ticker in settings.equity_tickers:
            session.add(Asset(
                ticker=ticker, asset_type="equity", is_active=True, created_at=now
            ))
        for ticker in settings.crypto_tickers:
            session.add(Asset(
                ticker=ticker, asset_type="crypto", is_active=True, created_at=now
            ))
        await session.commit()
        logger.info("Seeded %d default assets", len(settings.all_tickers))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    await _seed_default_assets()

    # Begin FinBERT download in background (doesn't block startup)
    finbert.start_loading()

    price_svc = PriceService(AsyncSessionLocal, settings.alpha_vantage_api_key)
    news_svc = NewsService(settings.newsdata_api_key, AsyncSessionLocal)
    sentiment_svc = SentimentService(AsyncSessionLocal)
    signal_svc = SignalService(AsyncSessionLocal)

    scheduler = create_scheduler(price_svc, news_svc, sentiment_svc, signal_svc)
    scheduler.start()

    # Run an initial data fetch immediately so the dashboard has data on first load
    logger.info("Running initial data fetch…")
    await price_svc.fetch_and_store_all()
    await news_svc.fetch_and_store_all()
    await signal_svc.compute_and_store_all()

    logger.info("Backend startup complete")
    yield

    # ── Shutdown ──
    scheduler.shutdown(wait=False)
    await engine.dispose()
    logger.info("Backend shutdown complete")


app = FastAPI(
    title="Market Sentiment Dashboard API",
    description=(
        "Live price data, FinBERT news sentiment, technical indicators, "
        "and composite signal scores. "
        "RESEARCH TOOL ONLY — signals do not predict price movements."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(prices.router)
app.include_router(news.router)
app.include_router(signals.router)
app.include_router(sentiment.router)
