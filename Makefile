# Makefile
.PHONY: help build up down logs restart clean

help:
	@echo "Voice Assistant Docker Commands:"
	@echo "  make build    - Build all containers"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - Show logs"
	@echo "  make restart  - Restart services"
	@echo "  make clean    - Remove all containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started. Open http://localhost"

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

clean:
	docker-compose down -v
	docker system prune -f