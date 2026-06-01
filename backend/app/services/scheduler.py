from apscheduler.schedulers.asyncio import AsyncIOScheduler


def create_scheduler(
    price_service,
    news_service,
    sentiment_service,
    signal_service,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        price_service.fetch_and_store_all,
        "interval", minutes=15,
        id="fetch_prices", max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        news_service.fetch_and_store_all,
        "interval", minutes=30,
        id="fetch_news", max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        sentiment_service.score_pending_articles,
        "interval", minutes=30,
        id="score_sentiment", max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        signal_service.compute_and_store_all,
        "interval", minutes=15,
        id="compute_signals", max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        news_service.reset_daily_limit_if_needed,
        "cron", hour=0, minute=1,
        id="reset_news_limit",
    )

    return scheduler
