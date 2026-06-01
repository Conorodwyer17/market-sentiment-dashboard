import os
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
_TIMEOUT = 10


def _get(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_health() -> dict | None:
    return _get("/health")


def get_assets() -> list:
    data = _get("/assets")
    return data.get("assets", []) if data else []


def get_signal(ticker: str) -> dict | None:
    return _get(f"/signals/{ticker}")


def get_prices(ticker: str, days: int = 90) -> list:
    data = _get(f"/prices/{ticker}", params={"days": days})
    return data.get("bars", []) if data else []


def get_news(ticker: str, hours: int = 48) -> list:
    data = _get(f"/news/{ticker}", params={"hours": hours})
    return data.get("articles", []) if data else []


def get_signal_history(ticker: str, days: int = 30) -> list:
    data = _get(f"/signals/{ticker}/history", params={"days": days})
    return data.get("snapshots", []) if data else []


def get_sentiment_summary(ticker: str) -> dict | None:
    return _get(f"/sentiment/{ticker}/summary")


def add_asset(ticker: str, asset_type: str = "equity") -> dict | None:
    """POST /assets — returns the created asset dict or None on error."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/assets",
            json={"ticker": ticker.upper(), "asset_type": asset_type},
            timeout=_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return r.json()
        return None
    except Exception:
        return None
