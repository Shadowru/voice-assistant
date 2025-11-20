# backend/voice_assistant.py
import numpy as np
import torch
from faster_whisper import WhisperModel
import ollama
from TTS.api import TTS
import asyncio
import logging
from typing import Optional, Dict
import os
from silero_vad import load_silero_vad, get_speech_timestamps
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self):
        self.whisper_model = os.getenv("WHISPER_MODEL", "base")
        self.llm_model = os.getenv("LLM_MODEL", "llama3.2:3b")
        self.tts_model = os.getenv("TTS_MODEL", "tts_models/ru/ruslan/tacotron2-DDC")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        
        self.whisper = None
        self.vad_model = None
        self.tts = None
        self.redis_client = None
        
        self.audio_buffer = []
        self.sample_rate = 16000
        self.conversation_history = []
        
        self.whisper_loaded = False
        self.llm_loaded = False
        self.tts_loaded = False
    
    async def initialize(self):
        """Инициализация всех моделей"""
        try:
            # Redis для кэширования
            self.redis_client = await redis.from_url(
                "redis://redis:6379",
                encoding="utf-8",
                decode_responses=True
            )
            
            # Whisper STT
            logger.info(f"Loading Whisper model: {self.whisper_model}")
            self.whisper = WhisperModel(
                self.whisper_model,
                device="cuda" if torch.cuda.is_available() else "cpu",
                compute_type="float16" if torch.cuda.is_available() else "int8",
                download_root="/app/models/whisper"
            )
            self.whisper_loaded = True
            logger.info("Whisper model loaded")
            
            # VAD
            logger.info("Loading Silero VAD")
            self.vad_model = load_silero_vad()
            logger.info("VAD model loaded")
            
            # TTS
            logger.info(f"Loading TTS model: {self.tts_model}")
            self.tts = TTS(
                model_name=self.tts_model,
                progress_bar=False
            )
            if torch.cuda.is_available():
                self.tts.to("cuda")
            self.tts_loaded = True
            logger.info("TTS model loaded")
            
            # Проверка Ollama
            logger.info("Checking Ollama connection")
            ollama_client = ollama.Client(host=self.ollama_host)
            models = ollama_client.list()
            logger.info(f"Available Ollama models: {models}")
            self.llm_loaded = True
            
            logger.info("All models initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Проверка готовности всех компонентов"""
        return self.whisper_loaded and self.llm_loaded and self.tts_loaded
    
    async def process_audio_stream(self, audio_chunk: bytes) -> Optional[Dict]:
        """Обработка входящего аудио потока"""
        try:
            # Конвертация в numpy
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            self.audio_buffer.extend(audio_np)
            
            # VAD проверка (каждые 500ms)
            if len(self.audio_buffer) > self.sample_rate * 0.5:
                audio_tensor = torch.FloatTensor(self.audio_buffer)
                
                speech_timestamps = get_speech_timestamps(
                    audio_tensor,
                    self.vad_model,
                    sampling_rate=self.sample_rate,
                    threshold=0.5
                )
                
                # Проверка окончания речи
                if speech_timestamps and self._is_speech_ended(speech_timestamps):
                    return await self._process_complete_utterance()
            
            return None
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            return None
    
    def _is_speech_ended(self, timestamps) -> bool:
        """Определение окончания речи (пауза > 700ms)"""
        if not timestamps:
            return False
        
        last_speech_end = timestamps[-1]['end']
        buffer_length = len(self.audio_buffer)
        silence_duration = (buffer_length - last_speech_end) / self.sample_rate
        
        return silence_duration > 0.7
    
    async def _process_complete_utterance(self) -> Dict:
        """Полная обработка: STT -> LLM -> TTS"""
        audio_data = np.array(self.audio_buffer)
        self.audio_buffer = []
        
        # 1. Speech-to-Text
        user_text = await self._transcribe(audio_data)
        if not user_text.strip():
            return None
        
        logger.info(f"User: {user_text}")
        
        # 2. LLM Response
        assistant_text = await self._get_llm_response(user_text)
        logger.info(f"Assistant: {assistant_text}")
        
        # 3. Text-to-Speech
        audio_response = await self._synthesize_speech(assistant_text)
        
        return {
            "user_text": user_text,
            "assistant_text": assistant_text,
            "audio": audio_response
        }
    
    async def _transcribe(self, audio: np.ndarray) -> str:
        """Транскрипция аудио через Whisper"""
        try:
            segments, info = self.whisper.transcribe(
                audio,
                language="ru",
                beam_size=5,
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250
                }
            )
            
            text = " ".join([segment.text for segment in segments])
            return text.strip()
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    async def _get_llm_response(self, text: str) -> str:
        """Получение ответа от LLM через Ollama"""
        try:
            # Проверка кэша
            cache_key = f"llm:{hash(text)}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.info("Using cached LLM response")
                return cached
            
            # Добавление в историю
            self.conversation_history.append({
                "role": "user",
                "content": text
            })
            
            # Ограничение истории (последние 10 сообщений)
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            # Запрос к Ollama
            client = ollama.Client(host=self.ollama_host)
            response = client.chat(
                model=self.llm_model,
                messages=self.conversation_history,
                stream=False
            )
            
            assistant_text = response['message']['content']
            
            # Добавление ответа в историю
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_text
            })
            
            # Кэширование
            await self.redis_client.setex(cache_key, 3600, assistant_text)
            
            return assistant_text
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "Извините, произошла ошибка при обработке запроса."
    
    async def _synthesize_speech(self, text: str) -> bytes:
        """Синтез речи через TTS"""
        try:
            # Генерация аудио
            wav = self.tts.tts(text=text, language="ru")
            
            # Конвертация в int16 bytes
            audio_array = np.array(wav)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            return audio_int16.tobytes()
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""
    
    async def process_text(self, text: str) -> Dict:
        """Обработка текстового запроса (без аудио)"""
        assistant_text = await self._get_llm_response(text)
        return {
            "user_text": text,
            "assistant_text": assistant_text
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Cleanup completed")