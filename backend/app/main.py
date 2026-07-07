"""Точка входа FastAPI: приложение, lifespan, CORS."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import CORS_ORIGINS
from app.services import tts_service
from app.services.audio_service import is_ffmpeg_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if is_ffmpeg_available():
        logger.info("ffmpeg найден в PATH")
    else:
        logger.error(
            "ffmpeg не найден в PATH! Конвертация wav -> mp3 работать не будет."
        )

    # Модель KazakhTTS2 грузится один раз при старте (не на каждый запрос).
    # Если checkpoint'ы отсутствуют — не валим приложение, /api/health честно
    # покажет model_loaded=false, а /api/tts вернёт 503.
    try:
        tts_service.init_engine()
    except Exception:  # noqa: BLE001
        logger.exception(
            "Не удалось загрузить TTS-движок KazakhTTS2 — /api/tts недоступен"
        )

    logger.info("Backend запущен (Этап 4: KazakhTTS2)")
    yield
    logger.info("Backend останавливается")


app = FastAPI(title="Kazakh TTS App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
