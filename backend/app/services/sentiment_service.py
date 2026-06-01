import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import finbert
from app.models.orm import NewsArticle, SentimentScore

logger = logging.getLogger(__name__)


class SentimentService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def score_pending_articles(self) -> None:
        """Scheduled job: score all news articles that have no sentiment score yet."""
        async with self._session_factory() as session:
            # Articles not yet scored
            scored_ids_result = await session.execute(select(SentimentScore.article_id))
            scored_ids = {row[0] for row in scored_ids_result.fetchall()}

            result = await session.execute(select(NewsArticle))
            articles = [a for a in result.scalars().all() if a.id not in scored_ids]

        if not articles:
            return

        if not finbert.is_loaded():
            logger.info("FinBERT not ready — skipping sentiment scoring")
            return

        texts = [
            (a.headline or "") + (" " + a.description if a.description else "")
            for a in articles
        ]
        scores = await finbert.score_texts(texts)

        now = datetime.utcnow().isoformat() + "Z"
        async with self._session_factory() as session:
            for article, score in zip(articles, scores):
                session.add(SentimentScore(
                    article_id=article.id,
                    ticker=article.ticker,
                    positive=score["positive"],
                    negative=score["negative"],
                    neutral=score["neutral"],
                    label=score["label"],
                    scored_at=now,
                ))
            await session.commit()
        logger.info("Scored %d articles", len(articles))

    async def get_ticker_scores(
        self, ticker: str, hours: int, session: AsyncSession
    ) -> list[SentimentScore]:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        result = await session.execute(
            select(SentimentScore)
            .where(SentimentScore.ticker == ticker, SentimentScore.scored_at >= cutoff)
            .order_by(SentimentScore.scored_at.desc())
        )
        return result.scalars().all()
