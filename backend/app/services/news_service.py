import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Asset, NewsArticle

logger = logging.getLogger(__name__)

_NEWS_CACHE_MINUTES = 30


class NewsService:
    def __init__(self, api_key: str, session_factory):
        self._api_key = api_key
        self._session_factory = session_factory
        self._daily_limit_reached: bool = False
        self._limit_reset_date: datetime.date | None = None
        self._client = None

    def _get_client(self):
        if self._client is None:
            from newsdataapi import NewsDataApiClient
            self._client = NewsDataApiClient(apikey=self._api_key)
        return self._client

    def fetch_news(self, ticker: str, company_name: str | None = None) -> list[dict]:
        """
        Fetch latest news for a ticker from NewsData.io.
        Returns empty list if daily limit reached.
        """
        self.reset_daily_limit_if_needed()
        if self._daily_limit_reached:
            return []

        query = company_name if company_name else ticker
        try:
            response = self._get_client().latest_api(
                q=query,
                language="en",
                category="business,technology",
            )
        except Exception as exc:
            msg = str(exc).lower()
            if "429" in msg or "limit" in msg or "credit" in msg or "quota" in msg:
                self._daily_limit_reached = True
                self._limit_reset_date = datetime.utcnow().date()
                logger.warning("NewsData.io daily limit reached. Serving from cache.")
                return []
            raise

        articles = []
        for item in response.get("results", []) or []:
            articles.append({
                "headline": item.get("title") or "",
                "description": item.get("description") or "",
                "url": item.get("link") or "",
                "source_id": item.get("source_id") or "",
                "published_at": item.get("pubDate") or "",
            })
        return articles

    def reset_daily_limit_if_needed(self) -> None:
        today = datetime.utcnow().date()
        if self._limit_reset_date and self._limit_reset_date < today:
            self._daily_limit_reached = False
            self._limit_reset_date = None

    async def _recent_articles_exist(self, ticker: str, session: AsyncSession) -> bool:
        cutoff = (datetime.utcnow() - timedelta(minutes=_NEWS_CACHE_MINUTES)).isoformat() + "Z"
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.ticker == ticker, NewsArticle.fetched_at >= cutoff)
            .limit(1)
        )
        return result.scalar() is not None

    async def store_articles(
        self, ticker: str, articles: list[dict], session: AsyncSession
    ) -> int:
        if not articles:
            return 0
        now = datetime.utcnow().isoformat() + "Z"
        inserted = 0
        for art in articles:
            if not art.get("url"):
                continue
            stmt = (
                sqlite_insert(NewsArticle)
                .values(
                    ticker=ticker,
                    source_id=art.get("source_id", ""),
                    headline=art["headline"],
                    description=art.get("description", ""),
                    url=art["url"],
                    published_at=art.get("published_at", now),
                    fetched_at=now,
                )
                .on_conflict_do_nothing(index_elements=["ticker", "url"])
            )
            result = await session.execute(stmt)
            inserted += result.rowcount
        await session.commit()
        return inserted

    async def fetch_and_store_all(self) -> None:
        """Scheduled job: fetch and store news for all active assets."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Asset).where(Asset.is_active == True)  # noqa: E712
            )
            assets = result.scalars().all()

        for asset in assets:
            try:
                async with self._session_factory() as session:
                    if await self._recent_articles_exist(asset.ticker, session):
                        logger.debug("Skipping news fetch for %s — cached", asset.ticker)
                        continue
                articles = self.fetch_news(asset.ticker, asset.name)
                async with self._session_factory() as session:
                    count = await self.store_articles(asset.ticker, articles, session)
                logger.info("Stored %d new articles for %s", count, asset.ticker)
            except Exception as exc:
                logger.error("Failed to fetch news for %s: %s", asset.ticker, exc)

    async def get_recent_articles(
        self, ticker: str, hours: int, session: AsyncSession
    ) -> list[NewsArticle]:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.ticker == ticker, NewsArticle.published_at >= cutoff)
            .order_by(NewsArticle.published_at.desc())
        )
        return result.scalars().all()
