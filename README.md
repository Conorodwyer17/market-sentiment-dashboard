# Market Sentiment Dashboard

A full-stack web application that displays live financial market data, FinBERT news sentiment analysis, technical indicators, and a composite signal score — all running from a single `make up` command.

[![CI](https://github.com/YOUR_USERNAME/market-sentiment-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/market-sentiment-dashboard/actions/workflows/ci.yml)

> **Live demo:** https://your-backend.onrender.com *(update after deployment)*

---

## Honest Framing

> **This application is a research and educational tool. Signal scores are composite indicators combining price momentum and news sentiment. They do not predict future price movements. No trading decisions should be made based on this tool.**

This is not a disclaimer added for legal reasons — it is technically correct. Simple momentum and sentiment signals do not reliably predict prices.

---

## What It Does

| Feature | Detail |
|---------|--------|
| Price data | Alpha Vantage REST API (equities + crypto) with Stooq fallback |
| News data | NewsData.io official SDK |
| Sentiment | FinBERT (`ProsusAI/finbert`) running locally — no API key needed |
| Technical indicators | RSI (14), MACD (12/26/9), MA-20, MA-50 via pandas-ta |
| Signal score | 0–100 composite: 60% momentum + 40% sentiment |
| Frontend | Plotly Dash — auto-refreshes every 60 seconds |
| Storage | SQLite via SQLAlchemy async + Alembic migrations |
| Scheduling | APScheduler — prices every 15 min, news every 30 min |

---

## Quick Start

**Prerequisites:** Docker Desktop, two free API keys (see below), `make`.

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/market-sentiment-dashboard
cd market-sentiment-dashboard

# 2. Set up your .env file
cp .env.example .env
# Open .env and paste your two API keys — that's all you need to do manually

# 3. Start everything
make up
```

- Dashboard: http://localhost:8050
- API docs: http://localhost:8000/docs
- **First run:** FinBERT (~440 MB) downloads automatically. Sentiment scores appear 2–5 minutes after startup.

---

## API Keys

You need exactly two keys, both free:

**NewsData.io**
1. Go to https://newsdata.io
2. Click "Get API Key"
3. Register with your email (no credit card)
4. Copy the key (format: `pub_xxxx...`) into `.env` as `NEWSDATA_API_KEY=`

**Alpha Vantage**
1. Go to https://www.alphavantage.co/support/#api-key
2. Enter your email and click "GET FREE API KEY"
3. Your key appears immediately (format: 16-character alphanumeric)
4. Copy it into `.env` as `ALPHA_VANTAGE_API_KEY=`

Total time: ~2 minutes.

---

## Makefile Commands

```bash
make up      # Create data/ and models/ dirs, build and start all services
make down    # Stop all services
make build   # Rebuild images without cache
make test    # Run backend test suite
make logs    # Follow logs from all services
make clean   # Stop services, remove volumes, delete data/ and models/
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Browser  :8050                             │
│  Plotly Dash frontend                        │
│  Auto-refresh every 60s                      │
└──────────────────┬──────────────────────────┘
                   │ REST
┌──────────────────▼──────────────────────────┐
│  FastAPI backend  :8000                      │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Price   │  │  News    │  │ FinBERT  │  │
│  │ Service  │  │ Service  │  │(local ML)│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │        │
│  ┌────▼──────────────▼──────────────▼─────┐ │
│  │          SQLite database               │ │
│  │   (price_bars, news_articles,          │ │
│  │    sentiment_scores, signal_snapshots) │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  APScheduler: prices/signals every 15 min   │
│              news/sentiment every 30 min     │
└──────────────────────────────────────────────┘
```

---

## Project Structure

```
market-sentiment-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan handler
│   │   ├── core/                # Config, database, logging
│   │   ├── models/orm.py        # SQLAlchemy ORM (5 tables)
│   │   ├── schemas/             # Pydantic API response models
│   │   ├── routers/             # health, assets, prices, news, signals, sentiment
│   │   ├── services/            # Price, news, sentiment, signal, cache, scheduler
│   │   └── ml/finbert.py        # FinBERT singleton + async wrapper
│   ├── alembic/                 # Database migrations
│   └── tests/                   # Full test suite (all external calls mocked)
├── frontend/
│   ├── app/
│   │   ├── main.py              # Dash app entry point
│   │   ├── layout.py            # Page layout
│   │   ├── callbacks.py         # All interactivity + auto-refresh
│   │   ├── api_client.py        # Backend REST calls
│   │   └── components/          # 8 chart + UI components
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Signal Score Explanation

The composite signal (0–100) is calculated as:

```
composite = (momentum_score × 0.60) + (sentiment_normalised × 0.40)
```

Where:
- **Momentum score** = weighted average of RSI (30%), MACD histogram (40%), and MA position (30%)
- **Sentiment score** = time-weighted average of FinBERT scores for articles in the last 48 hours; articles older than 24 hours weighted at 0.5×
- **Signal label:** ≥65 = bullish, 40–64 = neutral, <40 = bearish

A minimum of 20 price bars is required for any indicator. With fewer bars, the label is `insufficient_data`.

---

## Running Tests

```bash
make test
# or directly:
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

All external API calls (Alpha Vantage, NewsData.io) are mocked. FinBERT is mocked in sentiment tests. Tests never make real network requests.

---

## Deployment on Render.com

**Backend:**
1. Push to GitHub
2. Render → New → Web Service → connect repo
3. Environment: **Docker** | Dockerfile path: `backend/Dockerfile`
4. Add environment variables: `NEWSDATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`
5. Add: `DATABASE_URL=sqlite+aiosqlite:////app/data/market_sentiment.db`
6. Deploy

**Frontend:**
1. Render → New → Web Service → same repo
2. Dockerfile path: `frontend/Dockerfile`
3. Add: `BACKEND_URL=https://your-backend.onrender.com`
4. Deploy

**Note:** Render free-tier services spin down after 15 minutes of inactivity and wake in 30–60 seconds. Expected for a portfolio project.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.111, Uvicorn 0.29 |
| ML | FinBERT (ProsusAI/finbert via HuggingFace Transformers 4.41) |
| Database | SQLite + SQLAlchemy 2.0 async + Alembic |
| Scheduling | APScheduler 3.10 |
| Price data | Alpha Vantage API + pandas-datareader (Stooq fallback) |
| News data | NewsData.io SDK 0.2 |
| Technical analysis | pandas-ta |
| Frontend | Plotly Dash 2.17, dash-bootstrap-components 1.6 |
| Containerisation | Docker Compose |
| CI | GitHub Actions |
