"""
API endpoint tests — all external calls mocked; no real network, no real model.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.orm import Asset, NewsArticle, PriceBar, SignalSnapshot


# ── In-process test client with overridden DB ─────────────────────────────────

@pytest.fixture(scope="module")
def test_client():
    """
    TestClient backed by an in-memory SQLite DB.
    FinBERT loading and all scheduler jobs are skipped.
    """
    # StaticPool ensures all sessions share the same in-memory connection
    # so seeded data is visible to the request-scoped override_db sessions.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    loop = asyncio.new_event_loop()

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            now = datetime.utcnow().isoformat() + "Z"
            session.add(Asset(ticker="AAPL", asset_type="equity", is_active=True, created_at=now))
            session.add(PriceBar(
                ticker="AAPL", date="2025-01-02", open=150.0, high=155.0,
                low=149.0, close=152.0, volume=1_000_000,
                source="alphavantage", fetched_at=now,
            ))
            session.add(SignalSnapshot(
                ticker="AAPL", computed_at=now, close_price=152.0,
                rsi_14=55.0, composite_signal=62.0, signal_label="neutral",
                sentiment_article_count=0, momentum_score=60.0,
            ))
            session.add(NewsArticle(
                ticker="AAPL", headline="Test headline", description="Test desc",
                url="https://example.com/test", published_at=now, fetched_at=now,
            ))
            await session.commit()
        return factory

    factory = loop.run_until_complete(_setup())

    async def override_db():
        async with factory() as session:
            yield session

    # Replace the router's lifespan context directly so TestClient never
    # executes startup code (DB seeding, scheduler, API fetches).
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()

    loop.run_until_complete(engine.dispose())
    loop.close()


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_returns_200(test_client):
    r = test_client.get("/health")
    assert r.status_code == 200


def test_health_has_required_fields(test_client):
    data = test_client.get("/health").json()
    for field in ("status", "finbert_loaded", "finbert_status", "version", "disclaimer"):
        assert field in data


def test_health_disclaimer_present(test_client):
    data = test_client.get("/health").json()
    assert len(data["disclaimer"]) > 10


# ── /assets ───────────────────────────────────────────────────────────────────

def test_list_assets_returns_200(test_client):
    r = test_client.get("/assets")
    assert r.status_code == 200
    assert "assets" in r.json()


def test_add_duplicate_asset_returns_409(test_client):
    r = test_client.post("/assets", json={"ticker": "AAPL", "asset_type": "equity"})
    assert r.status_code == 409


# ── /prices ───────────────────────────────────────────────────────────────────

def test_prices_returns_200(test_client):
    r = test_client.get("/prices/AAPL")
    assert r.status_code == 200
    data = r.json()
    assert "bars" in data
    assert data["ticker"] == "AAPL"


# ── /news ─────────────────────────────────────────────────────────────────────

def test_news_returns_200(test_client):
    r = test_client.get("/news/AAPL")
    assert r.status_code == 200
    assert "articles" in r.json()




# ── /signals ─────────────────────────────────────────────────────────────────

def test_signal_returns_200(test_client):
    r = test_client.get("/signals/AAPL")
    assert r.status_code == 200
    data = r.json()
    assert "signal_label" in data
    assert "composite_signal" in data


def test_signal_unknown_ticker_returns_404(test_client):
    r = test_client.get("/signals/UNKNOWN_TICKER_XYZ")
    assert r.status_code == 404


def test_signal_history_returns_200(test_client):
    r = test_client.get("/signals/AAPL/history")
    assert r.status_code == 200
    assert "snapshots" in r.json()


# ── /sentiment ────────────────────────────────────────────────────────────────

def test_sentiment_summary_returns_200(test_client):
    r = test_client.get("/sentiment/AAPL/summary")
    assert r.status_code == 200
    data = r.json()
    assert "dominant_label" in data
    assert "article_count" in data
