import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Asset, PriceBar, SentimentScore, SignalSnapshot

logger = logging.getLogger(__name__)


# ── Sub-score functions ───────────────────────────────────────────────────────

def _rsi_subscore(rsi: float | None) -> float:
    if rsi is None:
        return 50.0
    if rsi < 30:
        return 75.0   # Oversold — potential upside
    elif rsi < 45:
        return 60.0
    elif rsi <= 55:
        return 50.0   # Neutral zone
    elif rsi <= 70:
        return 60.0
    else:
        return 25.0   # Overbought — potential downside


def _macd_subscore(macd_hist: float | None) -> float:
    if macd_hist is None:
        return 50.0
    if macd_hist > 0:
        return 75.0   # Bullish momentum
    elif macd_hist == 0:
        return 50.0
    else:
        return 25.0   # Bearish momentum


def _ma_subscore(
    close: float | None, ma_20: float | None, ma_50: float | None
) -> float:
    if close is None or ma_20 is None:
        return 50.0
    above_20 = close > ma_20
    if ma_50 is None:
        return 70.0 if above_20 else 30.0
    above_50 = ma_20 > ma_50
    if above_20 and above_50:
        return 80.0   # Strong uptrend
    elif above_20 and not above_50:
        return 55.0
    elif not above_20 and above_50:
        return 45.0
    else:
        return 20.0   # Strong downtrend


# ── Core computation ──────────────────────────────────────────────────────────

def compute_signal(
    ticker: str, price_bars: list, sentiment_scores: list
) -> dict:
    """
    Compute composite signal score for a ticker.

    Args:
        ticker: Asset ticker string
        price_bars: List of PriceBar ORM objects, ordered by date ascending
        sentiment_scores: List of SentimentScore ORM objects from last 48 hours

    Returns:
        Dictionary matching SignalSnapshot schema
    """
    result = {
        "ticker": ticker,
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "close_price": None,
        "rsi_14": None,
        "macd": None,
        "macd_signal": None,
        "macd_hist": None,
        "ma_20": None,
        "ma_50": None,
        "sentiment_score": None,
        "sentiment_article_count": len(sentiment_scores),
        "momentum_score": None,
        "composite_signal": None,
        "signal_label": "insufficient_data",
    }

    if len(price_bars) < 20:
        return result

    df = pd.DataFrame([
        {"date": b.date, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in price_bars
    ])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    result["close_price"] = float(df["close"].iloc[-1])

    # RSI (14-period) — Wilder smoothing via EWM
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    rsi_series = 100 - (100 / (1 + avg_gain / avg_loss.replace(0, float("nan"))))
    if not pd.isna(rsi_series.iloc[-1]):
        result["rsi_14"] = float(rsi_series.iloc[-1])

    # MACD (12, 26, 9)
    ema_fast = df["close"].ewm(span=12, adjust=False).mean()
    ema_slow = df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    if not any(pd.isna([macd_line.iloc[-1], macd_signal.iloc[-1], macd_hist.iloc[-1]])):
        result["macd"] = float(macd_line.iloc[-1])
        result["macd_signal"] = float(macd_signal.iloc[-1])
        result["macd_hist"] = float(macd_hist.iloc[-1])

    if len(df) >= 20:
        result["ma_20"] = float(df["close"].rolling(20).mean().iloc[-1])
    if len(df) >= 50:
        result["ma_50"] = float(df["close"].rolling(50).mean().iloc[-1])

    # Momentum score (0–100)
    rsi_sub = _rsi_subscore(result["rsi_14"])
    macd_sub = _macd_subscore(result["macd_hist"])
    ma_sub = _ma_subscore(result["close_price"], result["ma_20"], result["ma_50"])

    result["momentum_score"] = round(
        (rsi_sub * 0.30) + (macd_sub * 0.40) + (ma_sub * 0.30), 2
    )

    # Sentiment score (−1 to +1)
    if len(sentiment_scores) >= 3:
        now = datetime.utcnow()
        weighted_sum = 0.0
        weight_total = 0.0
        for s in sentiment_scores:
            score = s.positive - s.negative
            age_hours = (
                now - datetime.fromisoformat(s.scored_at.rstrip("Z"))
            ).total_seconds() / 3600
            weight = 0.5 if age_hours > 24 else 1.0
            weighted_sum += score * weight
            weight_total += weight
        result["sentiment_score"] = (
            round(weighted_sum / weight_total, 4) if weight_total > 0 else 0.0
        )
    else:
        result["sentiment_score"] = 0.0

    # Composite signal (0–100)
    sentiment_normalised = ((result["sentiment_score"] + 1) / 2) * 100
    result["composite_signal"] = round(
        (result["momentum_score"] * 0.60) + (sentiment_normalised * 0.40), 2
    )

    if result["composite_signal"] >= 65:
        result["signal_label"] = "bullish"
    elif result["composite_signal"] >= 40:
        result["signal_label"] = "neutral"
    else:
        result["signal_label"] = "bearish"

    return result


# ── Service class ─────────────────────────────────────────────────────────────

class SignalService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def compute_and_store_all(self) -> None:
        """Scheduled job: compute and store signal snapshots for all active assets."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Asset).where(Asset.is_active == True)  # noqa: E712
            )
            assets = result.scalars().all()

        for asset in assets:
            try:
                await self._compute_and_store_one(asset.ticker)
            except Exception as exc:
                logger.error("Signal computation failed for %s: %s", asset.ticker, exc)

    async def _compute_and_store_one(self, ticker: str) -> None:
        from datetime import timedelta
        from app.services.price_service import PriceService

        async with self._session_factory() as session:
            cutoff_48h = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

            price_result = await session.execute(
                select(PriceBar)
                .where(PriceBar.ticker == ticker)
                .order_by(PriceBar.date.asc())
            )
            price_bars = price_result.scalars().all()

            sentiment_result = await session.execute(
                select(SentimentScore)
                .where(
                    SentimentScore.ticker == ticker,
                    SentimentScore.scored_at >= cutoff_48h,
                )
            )
            sentiment_scores = sentiment_result.scalars().all()

        snapshot_data = compute_signal(ticker, price_bars, sentiment_scores)

        async with self._session_factory() as session:
            session.add(SignalSnapshot(**snapshot_data))
            await session.commit()
        logger.info(
            "Signal for %s: %s (%.1f)",
            ticker,
            snapshot_data["signal_label"],
            snapshot_data.get("composite_signal") or 0,
        )

    async def get_latest_snapshot(
        self, ticker: str, session: AsyncSession
    ) -> SignalSnapshot | None:
        result = await session.execute(
            select(SignalSnapshot)
            .where(SignalSnapshot.ticker == ticker)
            .order_by(SignalSnapshot.computed_at.desc())
            .limit(1)
        )
        return result.scalar()

    async def get_snapshot_history(
        self, ticker: str, days: int, session: AsyncSession
    ) -> list[SignalSnapshot]:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        result = await session.execute(
            select(SignalSnapshot)
            .where(
                SignalSnapshot.ticker == ticker,
                SignalSnapshot.computed_at >= cutoff,
            )
            .order_by(SignalSnapshot.computed_at.asc())
        )
        return result.scalars().all()
