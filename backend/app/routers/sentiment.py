from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.orm import SentimentScore
from app.schemas.api_schemas import SentimentSummaryResponse

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get("/{ticker}/summary", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    ticker: str,
    hours: int = Query(default=48, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> SentimentSummaryResponse:
    ticker = ticker.upper()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    result = await db.execute(
        select(SentimentScore).where(
            SentimentScore.ticker == ticker,
            SentimentScore.scored_at >= cutoff,
        )
    )
    scores = result.scalars().all()

    if not scores:
        return SentimentSummaryResponse(
            ticker=ticker,
            article_count=0,
            positive_pct=0.0,
            negative_pct=0.0,
            neutral_pct=0.0,
            dominant_label="neutral",
        )

    n = len(scores)
    pos = sum(1 for s in scores if s.label == "positive") / n * 100
    neg = sum(1 for s in scores if s.label == "negative") / n * 100
    neu = sum(1 for s in scores if s.label == "neutral") / n * 100
    dominant = max(("positive", pos), ("negative", neg), ("neutral", neu), key=lambda x: x[1])[0]

    return SentimentSummaryResponse(
        ticker=ticker,
        article_count=n,
        positive_pct=round(pos, 1),
        negative_pct=round(neg, 1),
        neutral_pct=round(neu, 1),
        dominant_label=dominant,
    )
