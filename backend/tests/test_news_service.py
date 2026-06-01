from unittest.mock import MagicMock, patch

import pytest

from app.services.news_service import NewsService
from app.models.orm import NewsArticle


def _make_service(session_factory=None):
    return NewsService(api_key="fake_key", session_factory=session_factory)


def test_parse_newsdata_response(mock_newsdata_response):
    """NewsData.io response is correctly parsed."""
    svc = _make_service()
    mock_client = MagicMock()
    mock_client.latest_api.return_value = mock_newsdata_response
    svc._client = mock_client

    articles = svc.fetch_news("AAPL")
    assert len(articles) == 5
    assert all("headline" in a for a in articles)
    assert all("url" in a for a in articles)


def test_rate_limit_flag_set_on_429():
    """Rate limit flag is set when API raises a 429-style error."""
    svc = _make_service()
    mock_client = MagicMock()
    mock_client.latest_api.side_effect = Exception("429 Too Many Requests — daily limit")
    svc._client = mock_client

    result = svc.fetch_news("AAPL")
    assert result == []
    assert svc._daily_limit_reached is True


def test_rate_limit_flag_blocks_further_calls():
    """Once flag is set, API is not called again."""
    svc = _make_service()
    mock_client = MagicMock()
    svc._client = mock_client
    svc._daily_limit_reached = True

    result = svc.fetch_news("MSFT")
    mock_client.latest_api.assert_not_called()
    assert result == []


@pytest.mark.asyncio
async def test_no_duplicate_articles(db_session):
    """Storing the same article URL twice does not create duplicates."""
    svc = _make_service()
    articles = [
        {"headline": "Test", "description": "", "url": "https://example.com/1",
         "source_id": "ex", "published_at": "2025-01-01 12:00:00"},
    ]
    await svc.store_articles("AAPL", articles, db_session)
    await svc.store_articles("AAPL", articles, db_session)

    from sqlalchemy import select
    result = await db_session.execute(
        select(NewsArticle).where(NewsArticle.ticker == "AAPL")
    )
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_recent_articles(db_session):
    """get_recent_articles returns only articles within the time window."""
    from datetime import datetime, timedelta
    svc = _make_service()
    now = datetime.utcnow()
    old = (now - timedelta(hours=50)).isoformat() + "Z"
    recent = now.isoformat() + "Z"

    articles_new = [{"headline": "New", "description": "", "url": "https://example.com/new",
                     "source_id": "ex", "published_at": recent}]
    articles_old = [{"headline": "Old", "description": "", "url": "https://example.com/old",
                     "source_id": "ex", "published_at": old}]

    await svc.store_articles("AAPL", articles_new, db_session)
    await svc.store_articles("AAPL", articles_old, db_session)

    results = await svc.get_recent_articles("AAPL", hours=48, session=db_session)
    assert len(results) == 1
    assert "New" in results[0].headline


@pytest.mark.asyncio
async def test_recent_articles_exist_check(db_session):
    """_recent_articles_exist returns False when no recent articles."""
    svc = _make_service()
    exists = await svc._recent_articles_exist("AAPL", db_session)
    assert exists is False


def test_reset_daily_limit_if_needed():
    """Daily limit flag is cleared when the date advances."""
    from datetime import date
    svc = _make_service()
    svc._daily_limit_reached = True
    svc._limit_reset_date = date(2024, 1, 1)   # old date
    svc.reset_daily_limit_if_needed()
    assert svc._daily_limit_reached is False
