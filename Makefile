# Makefile
.PHONY: help build up down logs restart clean init-models

help:
	@echo "Voice Assistant Docker Commands:"
	@echo "  make build        - Build all containers"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs"
	@echo "  make restart      - Restart services"
	@echo "  make init-models  - Download models"
	@echo "  make clean        - Remove all containers and volumes"

build:
	docker compose build --no-cache

up:
	docker compose up -d
	@echo "⏳ Services starting..."
	@sleep 10
	@echo "✅ Services started. Open http://localhost"

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

init-models:
	@echo "Downloading models..."
	docker compose exec ollama ollama pull llama3.2:3b
	@echo "✅ Models downloaded"

clean:
	docker compose down -v
	docker system prune -f

# Для CPU-only сборки
build-cpu:
	docker compose build --no-cache --build-arg DOCKERFILE=Dockerfile.cpu