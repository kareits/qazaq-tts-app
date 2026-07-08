"""API endpoints."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.api.schemas import (
    HealthResponse,
    SplitRequest,
    SplitResponse,
    TTSRequest,
    TTSResponse,
    VoicesResponse,
)
from app.config import CACHE_DIR, MAX_TEXT_LENGTH, TTS_RATE_LIMIT
from app.rate_limit import limiter
from app.services import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Backend health check. Responds instantly even during synthesis because it
    does not touch the model directly (engine state is read from the service
    layer without blocking)."""

    return HealthResponse(
        status="ok",
        device="cpu",
        model_loaded=tts_service.is_model_loaded(),
        active_engine=tts_service.active_engine(),
        max_text_length=MAX_TEXT_LENGTH,
    )


@router.get("/voices", response_model=VoicesResponse)
async def voices() -> VoicesResponse:
    """List of available TTS engine voices."""

    return VoicesResponse(voices=tts_service.list_voices())


@router.post("/split", response_model=SplitResponse)
async def split(request: SplitRequest) -> SplitResponse:
    """Split text into sentences (to display clickable sentences on the frontend
    BEFORE synthesis). Uses the same function as /api/tts."""

    return SplitResponse(**tts_service.split(request.text))


def _sentence_range_dict(body: TTSRequest) -> dict | None:
    return (
        {"from": body.sentence_range.from_, "to": body.sentence_range.to}
        if body.sentence_range is not None
        else None
    )


# `request: Request` is required by slowapi to read the client IP. The rate limit
# guards the CPU-expensive synthesis from abuse (per client IP).
@router.post("/tts", response_model=TTSResponse)
@limiter.limit(TTS_RATE_LIMIT)
async def tts(request: Request, body: TTSRequest) -> TTSResponse:
    """Synthesize audio from text (or a sentence range). Inference is
    non-blocking (thread pool + semaphore=1), so /api/health responds even during
    synthesis."""

    if not tts_service.is_model_loaded():
        raise HTTPException(status_code=503, detail="TTS-модель не загружена")

    sentence_range = _sentence_range_dict(body)

    try:
        result = await tts_service.synthesize(
            text=body.text,
            voice=body.voice,
            fmt=body.format,
            sentence_range=sentence_range,
        )
    except ValueError as exc:
        # Input validation errors (empty text, limit, voice, range).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Synthesis error")
        raise HTTPException(status_code=500, detail=f"Ошибка синтеза: {exc}") from exc

    return TTSResponse(**result)


@router.post("/tts/stream")
@limiter.limit(TTS_RATE_LIMIT)
async def tts_stream(request: Request, body: TTSRequest) -> StreamingResponse:
    """Streaming synthesis with progress (Server-Sent Events). Emits `data: {...}`
    events — progress as each sentence becomes ready plus the final result.
    Inference is non-blocking; /api/health responds even during synthesis."""

    if not tts_service.is_model_loaded():
        raise HTTPException(status_code=503, detail="TTS-модель не загружена")

    sentence_range = _sentence_range_dict(body)

    async def event_gen():
        try:
            async for event in tts_service.synthesize_stream(
                text=body.text,
                voice=body.voice,
                fmt=body.format,
                sentence_range=sentence_range,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except ValueError as exc:
            payload = {"type": "error", "detail": str(exc)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming synthesis error")
            payload = {"type": "error", "detail": f"Ошибка синтеза: {exc}"}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/audio/{filename}")
async def get_audio(filename: str) -> FileResponse:
    """Serve a ready-made audio file from the cache with a header so the browser
    can download it (attachment; filename=...)."""

    file_path = CACHE_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Аудиофайл не найден")

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
