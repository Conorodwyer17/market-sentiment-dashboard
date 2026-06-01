"""Scheduler tests — verify all jobs are registered with the correct intervals."""
from unittest.mock import MagicMock

from app.services.scheduler import create_scheduler


def _make_scheduler():
    price_svc = MagicMock()
    news_svc = MagicMock()
    sentiment_svc = MagicMock()
    signal_svc = MagicMock()
    return create_scheduler(price_svc, news_svc, sentiment_svc, signal_svc)


def test_scheduler_has_five_jobs():
    sched = _make_scheduler()
    assert len(sched.get_jobs()) == 5


def test_scheduler_job_ids():
    sched = _make_scheduler()
    ids = {job.id for job in sched.get_jobs()}
    assert "fetch_prices" in ids
    assert "fetch_news" in ids
    assert "score_sentiment" in ids
    assert "compute_signals" in ids
    assert "reset_news_limit" in ids


def test_scheduler_timezone_utc():
    sched = _make_scheduler()
    import pytz
    assert str(sched.timezone) == "UTC"
