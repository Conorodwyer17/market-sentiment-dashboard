"""
Shared test fixtures for the market-sentiment-dashboard backend.

All external API calls (Alpha Vantage, NewsData.io, FinBERT) are mocked.
Tests never make real network requests.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base


# ── Event loop ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── In-memory database ────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """In-memory SQLite session, schema created fresh for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(scope="function")
def session_factory(db_session):
    """Returns a callable that yields the same in-memory session."""
    class _Factory:
        def __call__(self):
            return _CtxMgr(db_session)

    class _CtxMgr:
        def __init__(self, s):
            self._s = s
        async def __aenter__(self):
            return self._s
        async def __aexit__(self, *_):
            pass

    return _Factory()


# ── Mock API responses ────────────────────────────────────────────────────────

def _make_av_daily_response(ticker: str, days: int = 90) -> dict:
    series = {}
    base = datetime(2025, 1, 1)
    for i in range(days):
        d = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        series[d] = {
            "1. open": f"{150 + i * 0.1:.4f}",
            "2. high": f"{155 + i * 0.1:.4f}",
            "3. low": f"{148 + i * 0.1:.4f}",
            "4. close": f"{152 + i * 0.1:.4f}",
            "5. volume": "1000000",
        }
    return {"Time Series (Daily)": series}


@pytest.fixture
def mock_alpha_vantage_response():
    return _make_av_daily_response("AAPL", 90)


@pytest.fixture
def mock_newsdata_response():
    return {
        "status": "success",
        "results": [
            {
                "title": f"Headline {i}",
                "description": f"Description {i}",
                "link": f"https://example.com/article-{i}",
                "source_id": "example",
                "pubDate": "2025-06-01 12:00:00",
            }
            for i in range(5)
        ],
    }


@pytest.fixture
def mock_finbert_output():
    """Pre-computed FinBERT-style output: list of label-score dicts."""
    return [
        [
            {"label": "positive", "score": 0.90},
            {"label": "negative", "score": 0.05},
            {"label": "neutral", "score": 0.05},
        ]
    ]
