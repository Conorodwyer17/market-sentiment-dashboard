from cachetools import TTLCache

# 5-minute TTL cache for signal snapshots and price summaries
_signal_cache: TTLCache = TTLCache(maxsize=100, ttl=300)
_price_cache: TTLCache = TTLCache(maxsize=100, ttl=300)


def get_cached_signal(ticker: str) -> dict | None:
    return _signal_cache.get(ticker)


def set_cached_signal(ticker: str, data: dict) -> None:
    _signal_cache[ticker] = data


def get_cached_prices(key: str) -> list | None:
    return _price_cache.get(key)


def set_cached_prices(key: str, data: list) -> None:
    _price_cache[key] = data
