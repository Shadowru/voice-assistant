#!/bin/bash
# scripts/init-letsencrypt.sh

set -e

# Загрузка переменных окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DOMAIN=${DOMAIN:-example.com}
EMAIL=${EMAIL:-admin@example.com}
STAGING=${STAGING:-1}  # 1 для тестового режима, 0 для продакшена

echo "🔐 Initializing Let's Encrypt for $DOMAIN"
echo "Email: $EMAIL"
echo "Staging mode: $STAGING"

# Создание необходимых директорий
mkdir -p certbot/conf certbot/www

# Проверка существующих сертификатов
if [ -d "certbot/conf/live/$DOMAIN" ]; then
    read -p "Existing certificates found for $DOMAIN. Remove and continue? (y/N) " decision
    if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
    rm -rf certbot/conf/live/$DOMAIN
    rm -rf certbot/conf/archive/$DOMAIN
    rm -rf certbot/conf/renewal/$DOMAIN.conf
fi

# Загрузка рекомендуемых параметров TLS от Certbot
echo "📥 Downloading recommended TLS parameters..."
curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "certbot/conf/options-ssl-nginx.conf"
curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "certbot/conf/ssl-dhparams.pem"

# Создание dummy сертификата для первоначального запуска Nginx
echo "🔧 Creating dummy certificate for $DOMAIN..."
mkdir -p "certbot/conf/live/$DOMAIN"
docker-compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:4096 -days 1\
    -keyout '/etc/letsencrypt/live/$DOMAIN/privkey.pem' \
    -out '/etc/letsencrypt/live/$DOMAIN/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "✅ Dummy certificate created"

# Запуск Nginx с dummy сертификатом
echo "🚀 Starting nginx..."
docker-compose up -d frontend

# Удаление dummy сертификата
echo "🗑️  Deleting dummy certificate for $DOMAIN..."
docker-compose run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/$DOMAIN && \
  rm -rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

# Запрос настоящего сертификата
echo "📜 Requesting Let's Encrypt certificate for $DOMAIN..."

# Параметры для staging или production
if [ $STAGING != "0" ]; then
    STAGING_ARG="--staging"
    echo "⚠️  Using Let's Encrypt staging server (test mode)"
else
    STAGING_ARG=""
    echo "✅ Using Let's Encrypt production server"
fi

# Получение сертификата
docker-compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d $DOMAIN -d www.$DOMAIN" certbot

echo "✅ Certificate obtained successfully!"

# Перезагрузка Nginx с новым сертификатом
echo "🔄 Reloading nginx with new certificate..."
docker-compose restart frontend

echo ""
echo "✅ SSL setup complete!"
echo "🌐 Your site should now be available at:"
echo "   https://$DOMAIN"
echo ""
echo "📝 Note: If you used staging mode (STAGING=1), the certificate is not trusted."
echo "   Set STAGING=0 in .env and run this script again for a production certificate."