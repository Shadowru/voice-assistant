#!/bin/bash
# scripts/start.sh

echo "🚀 Starting Voice Assistant..."

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Проверка NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️  Warning: NVIDIA GPU not detected. Running on CPU (slower)."
fi

# Создание директорий
mkdir -p backend/models/{whisper,tts}
mkdir -p backend/logs

# Запуск с docker-compose
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

# Проверка здоровья
echo "🔍 Checking service health..."
docker-compose ps

# Загрузка моделей
echo "📥 Downloading models (this may take a while)..."
docker-compose run --rm model-downloader

echo "✅ Voice Assistant is ready!"
echo "🌐 Open http://localhost in your browser"
echo ""
echo "📊 Monitoring:"
echo "   - Logs: docker-compose logs -f"
echo "   - Metrics: http://localhost:8000/metrics"
echo "   - Health: http://localhost:8000/health"