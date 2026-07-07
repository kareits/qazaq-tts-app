"""Оркестрация TTS: нормализация -> разбиение на предложения -> посегментный
синтез -> склейка -> mp3, с кэшированием.

Здесь живёт единственный экземпляр TTS-движка (загружается один раз при старте
приложения) и семафор, ограничивающий число параллельных синтезов до одного
(на ноутбуке один CPU-синтез за раз). Тяжёлый инференс и конвертация вызываются
только через thread pool (asyncio.to_thread), чтобы не блокировать event loop —
в частности, /api/health отвечает мгновенно даже во время синтеза.

Разбиение на предложения выполняется ЕДИНОЙ функцией text_normalizer.split_sentences
(та же, что обслуживает /api/split), поэтому границы предложений и char-смещения
у /api/split и /api/tts всегда совпадают.
"""

import asyncio
import logging
import os
import uuid

from app.config import (
    AUDIO_TARGET_PEAK,
    CACHE_DIR,
    MAX_TEXT_LENGTH,
    MODELS_DIR,
    SEGMENT_SILENCE_SEC,
    TMP_DIR,
)
from app.services import audio_service, cache_service, text_normalizer
from app.tts.kazakhtts2_engine import DEFAULT_VOICE, KazakhTTS2Engine

logger = logging.getLogger(__name__)

ENGINE_NAME = "kazakhtts2"

# Единственный экземпляр движка и семафор параллельных синтезов (= 1).
_engine: KazakhTTS2Engine | None = None
_semaphore = asyncio.Semaphore(1)


def init_engine() -> None:
    """Загрузить TTS-движок. Вызывается один раз при старте (lifespan)."""
    global _engine
    engine = KazakhTTS2Engine(MODELS_DIR)
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
    """Разбить текст на предложения (для /api/split) + предупреждение о языке."""
    return {
        "sentences": text_normalizer.split_sentences(text),
        "warning": text_normalizer.kazakh_warning(text),
    }


def _select_range(sentences: list[dict], sentence_range: dict | None) -> list[dict]:
    """Выбрать поддиапазон предложений [from..to] (включительно) или все."""
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
    """Асинхронный генератор синтеза с событиями прогресса.

    Отдаёт словари-события:
      {"type": "progress", "stage": ..., "done": k, "total": n, "percent": p}
      {"type": "done", "result": <meta для /api/tts>}
    Прогресс честный: каждое событие 'synth' приходит после реального синтеза
    очередного предложения. Валидационные ошибки поднимаются как ValueError.
    """
    if _engine is None:
        raise RuntimeError("TTS-модель не загружена")
    if voice not in {v["id"] for v in list_voices()}:
        raise ValueError(f"Неизвестный голос '{voice}'")

    # Полная нормализация всего текста — для лимита длины и ключа кэша.
    normalized_full = text_normalizer.normalize_text(text)
    if not normalized_full:
        raise ValueError("Текст пустой")
    if len(normalized_full) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Текст длиннее лимита в {MAX_TEXT_LENGTH} символов "
            f"(получено {len(normalized_full)})"
        )

    # ЕДИНАЯ функция разбиения (та же, что у /api/split).
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

    # Кэш: если готовое аудио есть — не запускаем синтез.
    cached_meta = cache_service.get(key, fmt)
    if cached_meta is not None:
        logger.info("Кэш-хит (voice=%s, range=%s)", voice, range_key)
        yield {"type": "done", "result": {**cached_meta, "cached": True}}
        return

    mp3_filename = cache_service.audio_filename(key, fmt)
    mp3_path = CACHE_DIR / mp3_filename
    total = len(selected)
    tmp_wavs: list[str] = []
    final_wav = TMP_DIR / f"{uuid.uuid4().hex}.wav"

    try:
        # Один синтез за раз; шаги — через thread pool, чтобы не блокировать loop.
        async with _semaphore:
            logger.info(
                "Синтез %d предложений (voice=%s, range=%s)...",
                total,
                voice,
                range_key,
            )
            for i, sent in enumerate(selected):
                seg_wav = TMP_DIR / f"{uuid.uuid4().hex}.wav"
                # Для синтеза схлопываем внутренние пробелы; смещения не трогаем.
                seg_text = text_normalizer.normalize_text(sent["text"])
                await asyncio.to_thread(
                    _engine.synthesize, seg_text, voice, str(seg_wav)
                )
                tmp_wavs.append(str(seg_wav))
                # Синтез сегментов занимает основную часть времени — 0..90%.
                yield {
                    "type": "progress",
                    "stage": "synth",
                    "done": i + 1,
                    "total": total,
                    "percent": round((i + 1) / total * 90),
                }

            # Склейка с короткой тишиной между предложениями + тайминги.
            timings = await asyncio.to_thread(
                audio_service.concat_segments,
                tmp_wavs,
                str(final_wav),
                SEGMENT_SILENCE_SEC,
            )
            yield {"type": "progress", "stage": "concat", "done": total,
                   "total": total, "percent": 93}

            # Нормализация громкости финального (склеенного) аудио.
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
        # Сохраняем метаданные рядом с mp3 + LRU-очистка.
        cache_service.put(key, fmt, meta)
        yield {"type": "done", "result": meta}
    finally:
        # Убираем все временные WAV (сегменты и склейку).
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
    """Непотоковый синтез (для POST /api/tts): прогоняет генератор и возвращает
    итоговый результат."""
    result: dict | None = None
    async for event in synthesize_stream(text, voice, fmt, sentence_range):
        if event["type"] == "done":
            result = event["result"]
    if result is None:
        raise RuntimeError("Синтез не вернул результат")
    return result
