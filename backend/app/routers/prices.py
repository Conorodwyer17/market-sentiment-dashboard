from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.api_schemas import PriceBarOut, PriceListResponse
from app.services import cache_service
from sqlalchemy import select
from app.models.orm import PriceBar
from datetime import datetime, timedelta

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{ticker}", response_model=PriceListResponse)
async def get_prices(
    ticker: str,
    days: int = Query(default=90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> PriceListResponse:
    ticker = ticker.upper()
    cache_key = f"{ticker}:{days}"
    cached = cache_service.get_cached_prices(cache_key)
    if cached is not None:
        return PriceListResponse(ticker=ticker, bars=cached)

    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = await db.execute(
        select(PriceBar)
        .where(PriceBar.ticker == ticker, PriceBar.date >= cutoff)
        .order_by(PriceBar.date.asc())
    )
    bars = result.scalars().all()
    bar_dicts = [PriceBarOut.model_validate(b).model_dump() for b in bars]
    cache_service.set_cached_prices(cache_key, bar_dicts)
    return PriceListResponse(ticker=ticker, bars=bar_dicts)
