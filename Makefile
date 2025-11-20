# Makefile
.PHONY: help build up down logs restart clean ssl-init ssl-renew check

help:
	@echo "Voice Assistant Docker Commands:"
	@echo "  make build        - Build all containers"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show all logs"
	@echo "  make restart      - Restart services"
	@echo "  make ssl-init     - Initialize SSL certificates"
	@echo "  make ssl-renew    - Renew SSL certificates"
	@echo "  make ssl-prod     - Switch to production SSL"
	@echo "  make check        - Check service status"
	@echo "  make clean        - Remove all containers and volumes"

build:
	docker compose build

up:
	docker compose up -d
	@echo "⏳ Services starting..."
	@sleep 20
	@make check

down:
	docker compose down

logs:
	docker compose logs -f

logs-nginx:
	docker compose logs -f frontend

restart:
	docker compose restart

restart-nginx:
	docker compose restart frontend

ssl-init:
	@echo "🔐 Initializing SSL certificates..."
	@chmod +x scripts/init-letsencrypt.sh
	@./scripts/init-letsencrypt.sh

ssl-renew:
	@echo "🔄 Renewing SSL certificates..."
	docker compose run --rm certbot renew
	docker compose restart frontend

ssl-prod:
	@echo "⚠️  Switching to production SSL certificates..."
	@echo "This will obtain real SSL certificates from Let's Encrypt."
	@read -p "Continue? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@sed -i 's/STAGING=1/STAGING=0/' .env
	@make ssl-init

check:
	@echo "🔍 Checking services..."
	@docker compose ps
	@echo ""
	@echo "Backend health:"
	@curl -s http://localhost:8000/health | jq . || echo "Backend not responding"
	@echo ""
	@echo "Frontend (HTTP):"
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost/
	@echo ""
	@echo "Frontend (HTTPS):"
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://localhost/ -k || echo "HTTPS not available"

check-ssl:
	@echo "🔍 Checking SSL certificate..."
	@docker compose exec frontend openssl x509 -in /etc/letsencrypt/live/$(DOMAIN)/fullchain.pem -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After)"

clean:
	docker compose down -v
	docker system prune -f

# Полная переустановка
reinstall: clean build up
	@sleep 20
	@make check
	@echo "✅ Reinstallation complete"