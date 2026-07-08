"""FastAPI entry point: application, lifespan, CORS, rate limiting, metrics."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api.routes import router
from app.config import CORS_ORIGINS, METRICS_ENABLED
from app.rate_limit import limiter
from app.services import tts_service
from app.services.audio_service import is_ffmpeg_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if is_ffmpeg_available():
        logger.info("ffmpeg found on PATH")
    else:
        logger.error("ffmpeg not found on PATH! wav -> mp3 conversion will not work.")

    # The KazakhTTS2 model is loaded once at startup (not per request). If the
    # checkpoints are missing, do not crash the app: /api/health honestly reports
    # model_loaded=false and /api/tts returns 503.
    try:
        tts_service.init_engine()
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to load the KazakhTTS2 engine — /api/tts is unavailable"
        )

    logger.info("Backend started (KazakhTTS2)")
    yield
    logger.info("Backend shutting down")


app = FastAPI(title="iSoyle — Kazakh TTS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (per client IP) to protect the CPU from abuse. The global default
# limit is applied by the middleware; per-endpoint limits are on the routes.
app.state.limiter = limiter


def _rate_limit_handler(request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Слишком много запросов, попробуйте позже."})


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# Prometheus metrics at /metrics (internal — not proxied by Caddy under /api).
if METRICS_ENABLED:
    Instrumentator().instrument(app).expose(app, include_in_schema=False)

app.include_router(router)
