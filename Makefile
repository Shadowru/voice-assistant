# Makefile
.PHONY: help build up down logs restart clean check-dirs init-models debug

help:
	@echo "Voice Assistant Docker Commands:"
	@echo "  make build        - Build all containers"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs"
	@echo "  make restart      - Restart services"
	@echo "  make init-models  - Download models"
	@echo "  make check-dirs   - Check directories"
	@echo "  make debug        - Enter backend container"
	@echo "  make clean        - Remove all containers and volumes"

build:
	docker compose build

up:
	docker compose up -d
	@echo "⏳ Services starting..."
	@sleep 15
	@echo "✅ Services started. Open http://localhost"
	@make check-dirs

down:
	docker compose down

logs:
	docker compose logs -f backend

restart:
	docker compose restart backend

init-models:
	@echo "📥 Downloading models..."
	docker-compose exec ollama ollama pull llama3.2:3b
	@echo "✅ Models downloaded"

check-dirs:
	@echo "📁 Checking directories..."
	docker-compose exec backend ls -la /app/
	docker-compose exec backend ls -la /app/logs/ || echo "Logs directory issue"

debug:
	docker-compose exec backend bash

clean:
	docker-compose down -v
	docker system prune -f

# Полная переустановка
reinstall: clean build up init-models
	@echo "✅ Reinstallation complete"