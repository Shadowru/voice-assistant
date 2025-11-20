# backend/server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
import os
from pathlib import Path
from voice_assistant import VoiceAssistant
from prometheus_client import Counter, Histogram, generate_latest
import time

# Создание директории для логов
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Метрики Prometheus
REQUEST_COUNT = Counter('voice_requests_total', 'Total voice requests')
REQUEST_LATENCY = Histogram('voice_request_latency_seconds', 'Request latency')
ACTIVE_CONNECTIONS = Counter('active_websocket_connections', 'Active WebSocket connections')

app = FastAPI(title="Voice Assistant API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальный экземпляр ассистента
assistant = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при старте"""
    global assistant
    logger.info("Starting Voice Assistant API...")
    logger.info(f"Python version: {os.sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        logger.info("Initializing Voice Assistant...")
        assistant = VoiceAssistant()
        await assistant.initialize()
        logger.info("✅ Voice Assistant initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Voice Assistant: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    global assistant
    logger.info("Shutting down Voice Assistant...")
    if assistant:
        await assistant.cleanup()
    logger.info("Voice Assistant shutdown complete")

@app.get("/")
async def root():
    return {
        "message": "Voice Assistant API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if assistant and assistant.is_ready():
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "models": {
                    "whisper": assistant.whisper_loaded,
                    "llm": assistant.llm_loaded,
                    "tts": assistant.tts_loaded
                },
                "timestamp": time.time()
            }
        )
    return JSONResponse(
        status_code=503,
        content={
            "status": "unhealthy",
            "message": "Assistant not ready",
            "timestamp": time.time()
        }
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для голосового взаимодействия"""
    await websocket.accept()
    ACTIVE_CONNECTIONS.inc()
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    logger.info(f"New WebSocket connection: {client_id}")
    
    try:
        while True:
            # Получение аудио данных
            data = await websocket.receive_bytes()
            REQUEST_COUNT.inc()
            
            start_time = time.time()
            
            # Обработка через ассистента
            result = await assistant.process_audio_stream(data)
            
            # Отправка результата
            if result:
                # Текстовый ответ пользователя
                if result.get("user_text"):
                    await websocket.send_json({
                        "type": "transcript",
                        "content": result["user_text"]
                    })
                
                # Текстовый ответ ассистента
                if result.get("assistant_text"):
                    await websocket.send_json({
                        "type": "response",
                        "content": result["assistant_text"]
                    })
                
                # Аудио ответ
                if result.get("audio"):
                    await websocket.send_bytes(result["audio"])
            
            # Метрика задержки
            latency = time.time() - start_time
            REQUEST_LATENCY.observe(latency)
            logger.debug(f"Request processed in {latency:.2f}s")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        ACTIVE_CONNECTIONS.dec()

@app.post("/api/text")
async def text_endpoint(request: dict):
    """REST endpoint для текстового взаимодействия"""
    try:
        text = request.get("text", "")
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "Text is required"}
            )
        
        result = await assistant.process_text(text)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Text processing error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/models")
async def list_models():
    """Список загруженных моделей"""
    if not assistant:
        return JSONResponse(
            status_code=503,
            content={"error": "Assistant not initialized"}
        )
    
    return {
        "whisper": {
            "loaded": assistant.whisper_loaded,
            "model": assistant.whisper_model
        },
        "llm": {
            "loaded": assistant.llm_loaded,
            "model": assistant.llm_model,
            "host": assistant.ollama_host
        },
        "tts": {
            "loaded": assistant.tts_loaded,
            "model": assistant.tts_model
        }
    }

@app.post("/api/reset")
async def reset_conversation():
    """Сброс истории разговора"""
    if assistant:
        assistant.conversation_history = []
        return {"message": "Conversation history cleared"}
    return JSONResponse(
        status_code=503,
        content={"error": "Assistant not initialized"}
    )