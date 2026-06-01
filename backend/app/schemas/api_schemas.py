from pydantic import BaseModel


class AssetOut(BaseModel):
    id: int
    ticker: str
    name: str | None
    asset_type: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    assets: list[AssetOut]


class AssetCreateRequest(BaseModel):
    ticker: str
    name: str | None = None
    asset_type: str = "equity"   # 'equity' or 'crypto'


class PriceBarOut(BaseModel):
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str

    model_config = {"from_attributes": True}


class PriceListResponse(BaseModel):
    ticker: str
    bars: list[PriceBarOut]


class ArticleOut(BaseModel):
    id: int
    ticker: str
    headline: str
    description: str | None
    url: str | None
    published_at: str
    source_id: str | None
    sentiment_label: str | None = None   # joined from sentiment_scores

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    ticker: str
    articles: list[ArticleOut]


class SentimentSummaryResponse(BaseModel):
    ticker: str
    article_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    dominant_label: str


class SignalSnapshotOut(BaseModel):
    ticker: str
    computed_at: str
    close_price: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    macd_hist: float | None
    ma_20: float | None
    ma_50: float | None
    sentiment_score: float | None
    sentiment_article_count: int | None
    momentum_score: float | None
    composite_signal: float | None
    signal_label: str

    model_config = {"from_attributes": True}


class SignalHistoryResponse(BaseModel):
    ticker: str
    snapshots: list[SignalSnapshotOut]


class HealthResponse(BaseModel):
    status: str
    version: str
    finbert_loaded: bool
    finbert_status: str
    database: str
    disclaimer: str
