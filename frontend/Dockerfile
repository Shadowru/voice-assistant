# frontend/Dockerfile
FROM nginx:alpine

# Установка необходимых утилит
RUN apk add --no-cache \
    netcat-openbsd \
    bash \
    openssl \
    gettext

# Создание директорий
RUN mkdir -p /var/www/certbot /etc/nginx/templates

# Копирование конфигураций Nginx
COPY nginx.conf /etc/nginx/templates/nginx.conf.template
COPY nginx-ssl.conf /etc/nginx/templates/nginx-ssl.conf.template

# Копирование статических файлов
COPY static/ /usr/share/nginx/html/

# Копирование entrypoint скрипта
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Экспорт портов
EXPOSE 80 443

# Использование entrypoint
ENTRYPOINT ["/entrypoint.sh"]