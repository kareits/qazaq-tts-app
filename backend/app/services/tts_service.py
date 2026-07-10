"""TTS orchestration: normalization -> sentence splitting -> per-segment
synthesis -> concatenation -> mp3, with caching.

This module holds the single TTS engine instance (loaded once at application
startup) and a semaphore limiting concurrent syntheses to one (one CPU synthesis
at a time on a laptop). Heavy inference and conversion are called only via a
thread pool (asyncio.to_thread) so the event loop is never blocked — in
particular, /api/health responds instantly even during synthesis.

Sentence splitting uses the SINGLE function text_normalizer.split_sentences (the
same one that serves /api/split), so sentence boundaries and char offsets always
match between /api/split and /api/tts.

Note: user-facing validation messages (raised as ValueError and returned as API
error details) stay in Russian, matching the Russian UI.
"""

import asyncio
import logging
import os
import uuid

from app.config import (
    AUDIO_TARGET_PEAK,
    CACHE_DIR,
    DEFAULT_VOICE,
    MAX_TEXT_LENGTH,
    MODELS_DIR,
    SEGMENT_SILENCE_SEC,
    TMP_DIR,
    TTS_DEVICE,
)
from app.services import audio_service, cache_service, text_normalizer
from app.tts.kazakhtts2_engine import KazakhTTS2Engine

logger = logging.getLogger(__name__)

ENGINE_NAME = "kazakhtts2"

# The single engine instance and the concurrent-synthesis semaphore (= 1).
_engine: KazakhTTS2Engine | None = None
_semaphore = asyncio.Semaphore(1)


def init_engine() -> None:
    """Load the TTS engine. Called once at startup (lifespan)."""
    global _engine
    engine = KazakhTTS2Engine(
        MODELS_DIR, device=TTS_DEVICE, default_voice=DEFAULT_VOICE
    )
    engine.load()
    _engine = engine


def is_model_loaded() -> bool:
    return _engine is not None


def active_engine() -> str | None:
    return ENGINE_NAME if _engine is not None else None


def default_voice() -> str:
    return DEFAULT_VOICE


def list_voices() -> list[dict]:
    return _engine.available_voices() if _engine is not None else []


def split(text: str) -> dict:
    """Split text into sentences (for /api/split) + a language warning."""
    return {
        "sentences": text_normalizer.split_sentences(text),
        "warning": text_normalizer.kazakh_warning(text),
    }


def _select_range(sentences: list[dict], sentence_range: dict | None) -> list[dict]:
    """Select a sub-range of sentences [from..to] (inclusive), or all of them."""
    if sentence_range is None:
        return sentences
    lo = sentence_range["from"]
    hi = sentence_range["to"]
    if lo > hi:
        raise ValueError(f"Некорректный диапазон: from={lo} > to={hi}")
    if lo < 0 or hi >= len(sentences):
        raise ValueError(
            f"Диапазон {lo}..{hi} вне числа предложений (0..{len(sentences) - 1})"
        )
    return sentences[lo : hi + 1]


async def synthesize_stream(
    text: str,
    voice: str,
    fmt: str = "mp3",
    sentence_range: dict | None = None,
):
    """Async synthesis generator that yields progress events.

    Yields event dicts:
      {"type": "progress", "stage": ..., "done": k, "total": n, "percent": p}
      {"type": "done", "result": <meta for /api/tts>}
    Progress is honest: each 'synth' event arrives after the actual synthesis of
    the next sentence. Validation errors are raised as ValueError.
    """
    if _engine is None:
        raise RuntimeError("TTS-модель не загружена")
    if voice not in {v["id"] for v in list_voices()}:
        raise ValueError(f"Неизвестный голос '{voice}'")

    # Full normalization of the whole text — for the length limit and cache key.
    normalized_full = text_normalizer.normalize_text(text)
    if not normalized_full:
        raise ValueError("Текст пустой")
    if len(normalized_full) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Текст длиннее лимита в {MAX_TEXT_LENGTH} символов "
            f"(получено {len(normalized_full)})"
        )

    # The SINGLE splitting function (same as /api/split).
    all_sentences = text_normalizer.split_sentences(text)
    if not all_sentences:
        raise ValueError("Не удалось выделить ни одного предложения")
    selected = _select_range(all_sentences, sentence_range)

    range_key = (
        "full"
        if sentence_range is None
        else f"{sentence_range['from']}-{sentence_range['to']}"
    )
    key = cache_service.make_key(normalized_full, voice, ENGINE_NAME, fmt, range_key)

    # Cache: if ready-made audio exists, do not run synthesis.
    cached_meta = cache_service.get(key, fmt)
    if cached_meta is not None:
        logger.info("Cache hit (voice=%s, range=%s)", voice, range_key)
        yield {"type": "done", "result": {**cached_meta, "cached": True}}
        return

    mp3_filename = cache_service.audio_filename(key, fmt)
    mp3_path = CACHE_DIR / mp3_filename
    total = len(selected)
    tmp_wavs: list[str] = []
    final_wav = TMP_DIR / f"{uuid.uuid4().hex}.wav"

    try:
        # One synthesis at a time; steps go through a thread pool so the loop
        # is not blocked.
        async with _semaphore:
            logger.info(
                "Synthesizing %d sentences (voice=%s, range=%s)...",
                total,
                voice,
                range_key,
            )
            for i, sent in enumerate(selected):
                seg_wav = TMP_DIR / f"{uuid.uuid4().hex}.wav"
                # Collapse inner whitespace, then expand digit numbers into Kazakh
                # words for the model. Offsets/highlighting keep the original text.
                seg_text = text_normalizer.normalize_text(sent["text"])
                seg_text = text_normalizer.expand_numbers_kk(seg_text)
                await asyncio.to_thread(
                    _engine.synthesize, seg_text, voice, str(seg_wav)
                )
                tmp_wavs.append(str(seg_wav))
                # Segment synthesis takes most of the time — 0..90%.
                yield {
                    "type": "progress",
                    "stage": "synth",
                    "done": i + 1,
                    "total": total,
                    "percent": round((i + 1) / total * 90),
                }

            # Concatenation with a short silence between sentences + timings.
            timings = await asyncio.to_thread(
                audio_service.concat_segments,
                tmp_wavs,
                str(final_wav),
                SEGMENT_SILENCE_SEC,
            )
            yield {"type": "progress", "stage": "concat", "done": total,
                   "total": total, "percent": 93}

            # Loudness normalization of the final (concatenated) audio.
            await asyncio.to_thread(
                audio_service.normalize_wav_peak, str(final_wav), AUDIO_TARGET_PEAK
            )
            duration_sec = round(
                await asyncio.to_thread(
                    audio_service.get_wav_duration_sec, str(final_wav)
                ),
                3,
            )
            await asyncio.to_thread(
                audio_service.convert_wav_to_mp3, str(final_wav), str(mp3_path)
            )
            yield {"type": "progress", "stage": "encode", "done": total,
                   "total": total, "percent": 98}

            segments = [
                {
                    "index": sent["index"],
                    "char_start": sent["char_start"],
                    "char_end": sent["char_end"],
                    "start_sec": start,
                    "end_sec": end,
                }
                for sent, (start, end) in zip(selected, timings)
            ]

        meta = {
            "audio_url": f"/api/audio/{mp3_filename}",
            "format": fmt,
            "voice": voice,
            "engine": ENGINE_NAME,
            "cached": False,
            "duration_sec": duration_sec,
            "segments": segments,
        }
        # Store metadata next to the mp3 + run LRU eviction.
        cache_service.put(key, fmt, meta)
        yield {"type": "done", "result": meta}
    finally:
        # Remove all temporary WAVs (segments and the concatenation).
        for p in tmp_wavs:
            try:
                os.unlink(p)
            except OSError:
                pass
        final_wav.unlink(missing_ok=True)


async def synthesize(
    text: str,
    voice: str,
    fmt: str = "mp3",
    sentence_range: dict | None = None,
) -> dict:
    """Non-streaming synthesis (for POST /api/tts): drains the generator and
    returns the final result."""
    result: dict | None = None
    async for event in synthesize_stream(text, voice, fmt, sentence_range):
        if event["type"] == "done":
            result = event["result"]
    if result is None:
        raise RuntimeError("Синтез не вернул результат")
    return result
