from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.orm import NewsArticle, SentimentScore
from app.schemas.api_schemas import ArticleOut, NewsListResponse

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/{ticker}", response_model=NewsListResponse)
async def get_news(
    ticker: str,
    hours: int = Query(default=48, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> NewsListResponse:
    ticker = ticker.upper()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"

    # LEFT JOIN with sentiment_scores so each article carries its label
    stmt = (
        select(NewsArticle, SentimentScore.label.label("sentiment_label"))
        .outerjoin(SentimentScore, SentimentScore.article_id == NewsArticle.id)
        .where(NewsArticle.ticker == ticker, NewsArticle.published_at >= cutoff)
        .order_by(NewsArticle.published_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    articles: list[ArticleOut] = []
    for article, sentiment_label in rows:
        out = ArticleOut.model_validate(article)
        out.sentiment_label = sentiment_label
        articles.append(out)

    return NewsListResponse(ticker=ticker, articles=articles)
