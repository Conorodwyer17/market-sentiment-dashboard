FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory with correct permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Create models directory for FinBERT cache
RUN mkdir -p /app/models && chmod 777 /app/models

# Run Alembic migrations before starting
ENTRYPOINT ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
