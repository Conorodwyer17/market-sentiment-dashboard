from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.orm import SignalSnapshot
from app.schemas.api_schemas import SignalHistoryResponse, SignalSnapshotOut
from app.services import cache_service

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/{ticker}", response_model=SignalSnapshotOut)
async def get_signal(
    ticker: str, db: AsyncSession = Depends(get_db)
) -> SignalSnapshotOut:
    ticker = ticker.upper()
    cached = cache_service.get_cached_signal(ticker)
    if cached:
        return cached

    result = await db.execute(
        select(SignalSnapshot)
        .where(SignalSnapshot.ticker == ticker)
        .order_by(SignalSnapshot.computed_at.desc())
        .limit(1)
    )
    snapshot = result.scalar()
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No signal data for {ticker}")

    out = SignalSnapshotOut.model_validate(snapshot)
    cache_service.set_cached_signal(ticker, out)
    return out


@router.get("/{ticker}/history", response_model=SignalHistoryResponse)
async def get_signal_history(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> SignalHistoryResponse:
    ticker = ticker.upper()
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    result = await db.execute(
        select(SignalSnapshot)
        .where(
            SignalSnapshot.ticker == ticker,
            SignalSnapshot.computed_at >= cutoff,
        )
        .order_by(SignalSnapshot.computed_at.asc())
    )
    return SignalHistoryResponse(ticker=ticker, snapshots=result.scalars().all())
