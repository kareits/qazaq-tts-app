"""Кэш готовых аудио с LRU-очисткой.

Ключ кэша: hash(normalized_text + voice + engine + format + model_version +
sentence_range). Если файл есть — синтез не запускается (cached: true). Рядом с
mp3 хранится json с метаданными (тайминги сегментов и т.п.) под тем же именем.
При превышении лимита размера кэша удаляются самые старые файлы по mtime.
"""

import hashlib
import json
import logging
import time
from pathlib import Path

from app.config import CACHE_DIR, CACHE_MAX_BYTES, MODEL_VERSION

logger = logging.getLogger(__name__)


def make_key(
    normalized_text: str,
    voice: str,
    engine: str,
    fmt: str,
    sentence_range: str,
) -> str:
    """Сформировать ключ кэша (hex sha256)."""
    raw = "\x1f".join(
        [normalized_text, voice, engine, fmt, MODEL_VERSION, sentence_range]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def audio_filename(key: str, fmt: str) -> str:
    return f"{key}.{fmt}"


def _audio_path(key: str, fmt: str) -> Path:
    return CACHE_DIR / audio_filename(key, fmt)


def _meta_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get(key: str, fmt: str) -> dict | None:
    """Вернуть сохранённые метаданные, если аудио и json существуют, иначе None.

    Обновляет mtime файлов (отметка «недавно использован» для LRU).
    """
    audio = _audio_path(key, fmt)
    meta = _meta_path(key)
    if not (audio.is_file() and meta.is_file()):
        return None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Повреждён json кэша %s — игнорируем", meta)
        return None
    # Обновляем время доступа для LRU.
    now = time.time()
    for p in (audio, meta):
        try:
            p.touch()
        except OSError:
            pass
    _ = now
    return data


def put(key: str, fmt: str, meta: dict) -> None:
    """Сохранить json-метаданные рядом с уже записанным аудио и почистить LRU."""
    _meta_path(key).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    enforce_limit()


def enforce_limit() -> None:
    """LRU-очистка: пока суммарный размер кэша превышает лимит, удалять самые
    старые по mtime пары (audio + json)."""
    files = [p for p in CACHE_DIR.glob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    if total <= CACHE_MAX_BYTES:
        return

    # Группируем по «ключу» (имя без расширения), сортируем по времени доступа.
    stems: dict[str, list[Path]] = {}
    for p in files:
        stems.setdefault(p.stem, []).append(p)
    ordered = sorted(
        stems.items(),
        key=lambda kv: min(p.stat().st_mtime for p in kv[1]),
    )

    for _stem, group in ordered:
        if total <= CACHE_MAX_BYTES:
            break
        for p in group:
            try:
                size = p.stat().st_size
                p.unlink()
                total -= size
            except OSError:
                pass
        logger.info("LRU-очистка кэша: удалён %s", _stem)
