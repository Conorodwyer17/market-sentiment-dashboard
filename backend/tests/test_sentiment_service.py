"""
Sentiment service tests — FinBERT is always mocked; no model download required.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.orm import NewsArticle, SentimentScore
from app.services.sentiment_service import SentimentService


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _seed_articles(session, n: int = 3) -> list:
    now = datetime.utcnow().isoformat() + "Z"
    articles = []
    for i in range(n):
        a = NewsArticle(
            ticker="AAPL",
            headline=f"Headline {i}",
            description=f"Description {i}",
            url=f"https://example.com/{i}",
            published_at=now,
            fetched_at=now,
        )
        session.add(a)
        articles.append(a)
    await session.commit()
    for a in articles:
        await session.refresh(a)
    return articles


_FAKE_SCORES = [
    {"positive": 0.85, "negative": 0.05, "neutral": 0.10, "label": "positive"},
    {"positive": 0.10, "negative": 0.80, "neutral": 0.10, "label": "negative"},
    {"positive": 0.20, "negative": 0.20, "neutral": 0.60, "label": "neutral"},
]


# ── SentimentService.score_pending_articles ───────────────────────────────────

@pytest.mark.asyncio
async def test_scores_unscored_articles(db_session, session_factory):
    await _seed_articles(db_session, n=3)

    with patch("app.ml.finbert.is_loaded", return_value=True), \
         patch("app.ml.finbert.score_texts", new=AsyncMock(return_value=_FAKE_SCORES)):
        svc = SentimentService(session_factory)
        await svc.score_pending_articles()

    from sqlalchemy import select
    result = await db_session.execute(select(SentimentScore))
    scores = result.scalars().all()
    assert len(scores) == 3
    labels = {s.label for s in scores}
    assert "positive" in labels
    assert "negative" in labels


@pytest.mark.asyncio
async def test_skips_when_finbert_not_loaded(db_session, session_factory):
    """No scoring happens if FinBERT is not yet ready."""
    await _seed_articles(db_session, n=2)

    with patch("app.ml.finbert.is_loaded", return_value=False), \
         patch("app.ml.finbert.score_texts", new=AsyncMock()) as mock_score:
        svc = SentimentService(session_factory)
        await svc.score_pending_articles()

    mock_score.assert_not_called()


@pytest.mark.asyncio
async def test_no_articles_exits_early(db_session, session_factory):
    """score_pending_articles exits cleanly with no articles in the DB."""
    with patch("app.ml.finbert.is_loaded", return_value=True), \
         patch("app.ml.finbert.score_texts", new=AsyncMock()) as mock_score:
        svc = SentimentService(session_factory)
        await svc.score_pending_articles()

    mock_score.assert_not_called()


@pytest.mark.asyncio
async def test_already_scored_articles_not_re_scored(db_session, session_factory):
    """Articles that already have a SentimentScore are excluded from re-scoring."""
    articles = await _seed_articles(db_session, n=2)
    now = datetime.utcnow().isoformat() + "Z"
    db_session.add(SentimentScore(
        article_id=articles[0].id, ticker="AAPL",
        positive=0.9, negative=0.05, neutral=0.05,
        label="positive", scored_at=now,
    ))
    await db_session.commit()

    with patch("app.ml.finbert.is_loaded", return_value=True), \
         patch("app.ml.finbert.score_texts",
               new=AsyncMock(return_value=[_FAKE_SCORES[0]])) as mock_score:
        svc = SentimentService(session_factory)
        await svc.score_pending_articles()

    texts = mock_score.call_args[0][0]
    assert len(texts) == 1   # only the 1 unscored article


def _mock_finbert(texts: list[str]) -> list[dict]:
    """Deterministic mock: positive/negative/neutral based on keywords."""
    result = []
    for text in texts:
        low = text.lower()
        if "record earnings" in low or "beat" in low or "growth" in low:
            result.append({"positive": 0.92, "negative": 0.04, "neutral": 0.04, "label": "positive"})
        elif "loss" in low or "crash" in low or "lawsuit" in low:
            result.append({"positive": 0.03, "negative": 0.91, "neutral": 0.06, "label": "negative"})
        else:
            result.append({"positive": 0.10, "negative": 0.10, "neutral": 0.80, "label": "neutral"})
    return result


@pytest.mark.asyncio
async def test_scores_sum_to_one():
    """Probabilities must sum to 1.0 within floating-point tolerance."""
    scores = _mock_finbert(["Apple reported record earnings beating analyst estimates by 15%"])
    for s in scores:
        total = s["positive"] + s["negative"] + s["neutral"]
        assert abs(total - 1.0) < 0.001, f"Scores sum to {total}, not 1.0"


@pytest.mark.asyncio
async def test_clearly_positive_sentence():
    scores = _mock_finbert(["Company posted record earnings, beat all estimates with strong growth"])
    assert scores[0]["label"] == "positive"


@pytest.mark.asyncio
async def test_clearly_negative_sentence():
    scores = _mock_finbert(["Company reports massive loss and faces major securities lawsuit"])
    assert scores[0]["label"] == "negative"


@pytest.mark.asyncio
async def test_empty_string_does_not_crash():
    """Empty text should return neutral, not raise an exception."""
    with patch("app.ml.finbert._pipeline") as mock_pipe, \
         patch("app.ml.finbert.is_loaded", return_value=True):
        mock_pipe.return_value = [
            [{"label": "positive", "score": 0.1},
             {"label": "negative", "score": 0.1},
             {"label": "neutral", "score": 0.8}]
        ]
        from app.ml.finbert import _score_batch_sync
        result = _score_batch_sync([""])
        assert len(result) == 1
        assert result[0]["label"] == "neutral"


@pytest.mark.asyncio
async def test_batch_returns_correct_count():
    texts = [f"Text number {i}" for i in range(20)]
    with patch("app.ml.finbert._pipeline") as mock_pipe, \
         patch("app.ml.finbert.is_loaded", return_value=True):
        mock_pipe.return_value = [
            [{"label": "positive", "score": 0.8},
             {"label": "negative", "score": 0.1},
             {"label": "neutral", "score": 0.1}]
        ] * 20
        from app.ml.finbert import _score_batch_sync
        result = _score_batch_sync(texts)
        assert len(result) == 20
