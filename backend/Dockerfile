# backend/Dockerfile
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Метаданные
LABEL maintainer="your-email@example.com"
LABEL description="Voice Assistant Backend with Whisper, LLM, and TTS"

# Переменные окружения
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH="/usr/local/cuda/bin:${PATH}" \
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    build-essential \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    && rm -rf /var/lib/apt/lists/*

# Установка pip для Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Создание симлинков
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Создание рабочей директории
WORKDIR /app

# Создание необходимых директорий
RUN mkdir -p /app/models/whisper \
    /app/models/tts \
    /app/logs \
    /app/cache \
    && chmod -R 777 /app/logs /app/models /app/cache

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN python3.11 -m pip install --upgrade pip setuptools wheel && \
    python3.11 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    python3.11 -m pip install -r requirements.txt

# Копирование кода приложения
COPY . .

# Установка прав доступа
RUN chmod +x /app/*.py || true

# Экспорт портов
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Копирование entrypoint скрипта
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Установка netcat для проверки портов
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Использование entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]