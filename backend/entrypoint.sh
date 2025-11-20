#!/bin/bash
# backend/entrypoint.sh

set -e

echo "🚀 Starting Voice Assistant Backend..."

# Создание необходимых директорий
mkdir -p /app/logs /app/models/whisper /app/models/tts /app/cache
chmod -R 777 /app/logs /app/models /app/cache

echo "📁 Directories created:"
ls -la /app/

# Проверка Python версии
echo "🐍 Python version:"
python --version

# Проверка установленных пакетов
echo "📦 Installed packages:"
pip list | grep -E "(whisper|torch|TTS|ollama|silero)"

# Проверка CUDA (если доступна)
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 GPU Info:"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
else
    echo "⚠️  No GPU detected, running on CPU"
fi

# Ожидание готовности зависимых сервисов
echo "⏳ Waiting for dependencies..."

# Ожидание Redis
until nc -z redis 6379; do
    echo "Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

# Ожидание Ollama
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama..."
    sleep 2
done
echo "✅ Ollama is ready"

# Запуск приложения
echo "🎬 Starting application..."
exec python -m uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info