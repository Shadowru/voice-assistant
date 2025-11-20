# frontend/Dockerfile
FROM nginx:alpine

# Копирование конфигурации Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Копирование статических файлов
COPY static/ /usr/share/nginx/html/

# Экспорт портов
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]