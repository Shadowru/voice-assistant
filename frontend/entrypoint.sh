#!/bin/bash
# frontend/entrypoint.sh

set -e

echo "🌐 Starting Nginx with SSL support..."

# Переменные окружения
DOMAIN=${DOMAIN:-localhost}
EMAIL=${EMAIL:-admin@example.com}
STAGING=${STAGING:-1}

echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo "Staging: $STAGING"

# Ожидание готовности backend
echo "⏳ Waiting for backend to be ready..."
until nc -z backend 8000; do
    echo "Backend is not ready yet..."
    sleep 2
done
echo "✅ Backend is ready"

# Проверка наличия SSL сертификатов
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✅ SSL certificates found, using HTTPS configuration"
    envsubst '${DOMAIN}' < /etc/nginx/templates/nginx-ssl.conf.template > /etc/nginx/nginx.conf
else
    echo "⚠️  SSL certificates not found, using HTTP configuration"
    echo "Run 'make ssl-init' to obtain SSL certificates"
    envsubst '${DOMAIN}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/nginx.conf
fi

# Проверка конфигурации Nginx
echo "🔍 Testing Nginx configuration..."
nginx -t

# Запуск Nginx
echo "🚀 Starting Nginx server..."
exec nginx -g 'daemon off;'