from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.orm import Asset
from app.schemas.api_schemas import AssetCreateRequest, AssetListResponse, AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
async def list_assets(db: AsyncSession = Depends(get_db)) -> AssetListResponse:
    result = await db.execute(select(Asset).order_by(Asset.ticker))
    return AssetListResponse(assets=result.scalars().all())


@router.post("", response_model=AssetOut, status_code=201)
async def add_asset(
    body: AssetCreateRequest, db: AsyncSession = Depends(get_db)
) -> AssetOut:
    ticker = body.ticker.upper().strip()
    existing = await db.execute(select(Asset).where(Asset.ticker == ticker))
    if existing.scalar():
        raise HTTPException(status_code=409, detail=f"Asset {ticker} already exists")

    asset = Asset(
        ticker=ticker,
        name=body.name,
        asset_type=body.asset_type,
        is_active=True,
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset
