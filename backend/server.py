# backend/server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
from voice_assistant import VoiceAssistant
from prometheus_client import Counter, Histogram, generate_latest
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

#Prometheus
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

assistant = None

@app.on_event("startup")
async def startup_event():
    global assistant
    logger.info("Initializing Voice Assistant...")
    try:
        assistant = VoiceAssistant()
        await assistant.initialize()
        logger.info("Voice Assistant initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Voice Assistant: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global assistant
    if assistant:
        await assistant.cleanup()
    logger.info("Voice Assistant shutdown complete")

@app.get("/")
async def root():
    return {"message": "Voice Assistant API", "status": "running"}

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
                }
            }
        )
    return JSONResponse(status_code=503, content={"status": "unhealthy"})

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint"""
    await websocket.accept()
    ACTIVE_CONNECTIONS.inc()
    logger.info(f"New WebSocket connection: {websocket.client}")
    
    try:
        while True:
            data = await websocket.receive_bytes()
            REQUEST_COUNT.inc()
            
            start_time = time.time()
            
            result = await assistant.process_audio_stream(data)
            
            if result:
                await websocket.send_json({
                    "type": "transcript",
                    "content": result.get("user_text", "")
                })
                
                await websocket.send_json({
                    "type": "response",
                    "content": result.get("assistant_text", "")
                })
                
                if result.get("audio"):
                    await websocket.send_bytes(result["audio"])
            
            latency = time.time() - start_time
            REQUEST_LATENCY.observe(latency)
            logger.info(f"Request processed in {latency:.2f}s")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))
    finally:
        ACTIVE_CONNECTIONS.dec()

@app.post("/api/text")
async def text_endpoint(text: str):
    """REST endpoint ��� ���������� ��������������"""
    try:
        result = await assistant.process_text(text)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Text processing error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})