.PHONY: up down build test clean logs

# Create required directories and start all services
up:
	mkdir -p data models
	docker-compose up --build -d
	@echo "Dashboard starting at http://localhost:8050"
	@echo "API docs at http://localhost:8000/docs"
	@echo "Note: FinBERT model downloads on first run (~440MB, 2-5 minutes)"

# Stop all services
down:
	docker-compose down

# Rebuild images without cache
build:
	docker-compose build --no-cache

# Run backend tests
test:
	cd backend && pip install -r requirements-dev.txt && pytest tests/ -v --tb=short

# View logs
logs:
	docker-compose logs -f

# Remove all containers, volumes, and local data
clean:
	docker-compose down -v
	rm -rf data/ models/
	@echo "All data cleared"
