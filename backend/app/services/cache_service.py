"""Cache of ready-made audio with LRU eviction.

Cache key: hash(normalized_text + voice + engine + format + model_version +
sentence_range). If the file exists, synthesis is skipped (cached: true). Next to
the mp3 a json with metadata (segment timings, etc.) is stored under the same
name. When the cache size limit is exceeded, the oldest files (by mtime) are
removed.
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
    """Build the cache key (hex sha256)."""
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
    """Return stored metadata if both the audio and the json exist, else None.

    Refreshes the files' mtime (a "recently used" mark for LRU).
    """
    audio = _audio_path(key, fmt)
    meta = _meta_path(key)
    if not (audio.is_file() and meta.is_file()):
        return None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Corrupted cache json %s — ignoring", meta)
        return None
    # Refresh access time for LRU.
    now = time.time()
    for p in (audio, meta):
        try:
            p.touch()
        except OSError:
            pass
    _ = now
    return data


def put(key: str, fmt: str, meta: dict) -> None:
    """Store the json metadata next to the already-written audio and run LRU."""
    _meta_path(key).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    enforce_limit()


def enforce_limit() -> None:
    """LRU eviction: while the total cache size exceeds the limit, remove the
    oldest (by mtime) pairs (audio + json)."""
    files = [p for p in CACHE_DIR.glob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    if total <= CACHE_MAX_BYTES:
        return

    # Group by "key" (name without extension), sort by access time.
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
        logger.info("LRU cache eviction: removed %s", _stem)
