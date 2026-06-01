from fastapi import APIRouter
from app.ml import finbert
from app.schemas.api_schemas import HealthResponse

router = APIRouter(tags=["health"])

_DISCLAIMER = (
    "Research tool only. Signal scores combine price momentum and news sentiment analysis. "
    "They do not predict future price movements. Not financial advice."
)
_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    loaded = finbert.is_loaded()
    loading = finbert.is_loading()
    if loaded:
        status = "ready"
    elif loading:
        status = "downloading"
    else:
        status = "not_started"

    return HealthResponse(
        status="healthy",
        version=_VERSION,
        finbert_loaded=loaded,
        finbert_status=status,
        database="connected",
        disclaimer=_DISCLAIMER,
    )
