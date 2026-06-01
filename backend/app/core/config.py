from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    newsdata_api_key: str = ""
    alpha_vantage_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:////app/data/market_sentiment.db"
    transformers_cache: str = "/app/models"
    log_level: str = "INFO"
    default_equity_tickers: str = "AAPL,MSFT,GOOGL,NVDA,TSLA"
    default_crypto_tickers: str = "BTC-USD,ETH-USD"

    @property
    def equity_tickers(self) -> list[str]:
        return [t.strip() for t in self.default_equity_tickers.split(",") if t.strip()]

    @property
    def crypto_tickers(self) -> list[str]:
        return [t.strip() for t in self.default_crypto_tickers.split(",") if t.strip()]

    @property
    def all_tickers(self) -> list[str]:
        return self.equity_tickers + self.crypto_tickers


settings = Settings()
