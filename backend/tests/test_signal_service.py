"""
Signal service tests — all boundary conditions from the spec.
Uses lightweight mock ORM objects; no database required.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.signal_service import (
    _ma_subscore,
    _macd_subscore,
    _rsi_subscore,
    compute_signal,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_price_bars(n: int, start_close: float = 150.0, trend: float = 0.5):
    """Build n fake PriceBar-like objects with a configurable trend."""
    base = datetime(2024, 1, 1)
    bars = []
    for i in range(n):
        close = start_close + i * trend
        bars.append(SimpleNamespace(
            date=(base + timedelta(days=i)).strftime("%Y-%m-%d"),
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1_000_000,
        ))
    return bars


def _make_sentiment_scores(n: int, positive: float, negative: float):
    now = datetime.utcnow()
    scores = []
    for i in range(n):
        scores.append(SimpleNamespace(
            positive=positive,
            negative=negative,
            neutral=round(1.0 - positive - negative, 4),
            label="positive" if positive > negative else "negative",
            scored_at=(now - timedelta(hours=i)).isoformat() + "Z",
        ))
    return scores


# ── composite_signal range ────────────────────────────────────────────────────

def test_composite_signal_in_range_bullish():
    bars = _make_price_bars(60, trend=1.0)
    scores = _make_sentiment_scores(5, positive=0.85, negative=0.05)
    result = compute_signal("AAPL", bars, scores)
    assert 0 <= result["composite_signal"] <= 100


def test_composite_signal_in_range_bearish():
    bars = _make_price_bars(60, trend=-1.0)
    scores = _make_sentiment_scores(5, positive=0.05, negative=0.85)
    result = compute_signal("AAPL", bars, scores)
    assert 0 <= result["composite_signal"] <= 100


# ── signal_label values ───────────────────────────────────────────────────────

def test_signal_label_values():
    valid = {"bullish", "neutral", "bearish", "insufficient_data"}
    for trend in (1.5, 0.0, -1.5):
        bars = _make_price_bars(60, trend=trend)
        scores = _make_sentiment_scores(5, positive=0.5, negative=0.3)
        result = compute_signal("X", bars, scores)
        assert result["signal_label"] in valid


def test_insufficient_data_when_fewer_than_20_bars():
    bars = _make_price_bars(15)
    result = compute_signal("AAPL", bars, [])
    assert result["signal_label"] == "insufficient_data"
    assert result["composite_signal"] is None


# ── sentiment defaults ────────────────────────────────────────────────────────

def test_sentiment_defaults_to_zero_with_fewer_than_3_articles():
    bars = _make_price_bars(30)
    result = compute_signal("AAPL", bars, _make_sentiment_scores(2, 0.9, 0.05))
    assert result["sentiment_score"] == 0.0


# ── bullish / bearish signals with clear data ─────────────────────────────────

def test_bullish_with_clearly_bullish_data():
    bars = _make_price_bars(60, start_close=100.0, trend=2.0)
    scores = _make_sentiment_scores(5, positive=0.90, negative=0.02)
    result = compute_signal("AAPL", bars, scores)
    assert result["signal_label"] == "bullish"


def test_bearish_with_clearly_bearish_data():
    # Strongly downward trend — close will go negative so cap it
    bars = _make_price_bars(60, start_close=200.0, trend=-3.0)
    scores = _make_sentiment_scores(5, positive=0.02, negative=0.92)
    result = compute_signal("AAPL", bars, scores)
    assert result["signal_label"] == "bearish"


# ── sub-score functions ───────────────────────────────────────────────────────

@pytest.mark.parametrize("rsi,expected", [
    (20, 75.0), (35, 60.0), (50, 50.0), (60, 60.0), (80, 25.0), (None, 50.0),
])
def test_rsi_subscore(rsi, expected):
    assert _rsi_subscore(rsi) == expected


@pytest.mark.parametrize("hist,expected", [
    (1.0, 75.0), (0.0, 50.0), (-0.5, 25.0), (None, 50.0),
])
def test_macd_subscore(hist, expected):
    assert _macd_subscore(hist) == expected


@pytest.mark.parametrize("close,ma20,ma50,expected", [
    (110, 100, 90, 80.0),    # above both — strong uptrend
    (110, 100, 105, 55.0),   # above 20, below 50
    (95, 100, 90, 45.0),     # below 20, above 50
    (85, 100, 105, 20.0),    # below both — strong downtrend
    (110, 100, None, 70.0),  # no ma_50
    (None, 100, 90, 50.0),   # no close
])
def test_ma_subscore(close, ma20, ma50, expected):
    assert _ma_subscore(close, ma20, ma50) == expected


def test_all_subscores_in_range():
    for rsi in [None, 10, 30, 50, 70, 90]:
        assert 0 <= _rsi_subscore(rsi) <= 100
    for hist in [None, -5.0, 0.0, 5.0]:
        assert 0 <= _macd_subscore(hist) <= 100
    for close, ma20, ma50 in [(100, 90, 80), (80, 90, 95), (None, None, None)]:
        assert 0 <= _ma_subscore(close, ma20, ma50) <= 100
