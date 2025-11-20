#!/bin/bash
# scripts/init-models.sh

echo "📥 Initializing models..."

# Ждем запуска Ollama
echo "Waiting for Ollama to start..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done

echo "✅ Ollama is ready"

# Загрузка LLM модели
echo "Downloading LLM model: ${LLM_MODEL:-llama3.2:3b}"
ollama pull ${LLM_MODEL:-llama3.2:3b}

echo "✅ Models initialized successfully!"