"""Application settings: paths, limits, CORS.

Values are read from environment variables (for containers/production) with sane
defaults for local development.
"""

import os
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw) if raw else default


def _env_list(name: str, default: list[str]) -> list[str]:
    """List from an environment variable (comma-separated). Empty string -> []."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# Backend project root.
BASE_DIR = Path(__file__).resolve().parent.parent

# Paths can be overridden (in Docker — onto a volume): STORAGE_DIR, MODELS_DIR.
STORAGE_DIR = _env_path("STORAGE_DIR", BASE_DIR / "storage")
CACHE_DIR = STORAGE_DIR / "cache"
TMP_DIR = STORAGE_DIR / "tmp"
MODELS_DIR = _env_path("MODELS_DIR", BASE_DIR / "models")

# storage/cache and storage/tmp are not committed to git (.gitignore), so create
# them at application startup if missing.
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Input text length limit (characters). Returned to the frontend via /api/health
# so it is not hardcoded there too.
MAX_TEXT_LENGTH = _env_int("MAX_TEXT_LENGTH", 1000)

# Target peak for loudness normalization of synthesized audio. KazakhTTS2 voices
# produce very different signal levels (female1 quiet, female2 loud), so the final
# WAV is peak-normalized to this value (< 1.0 — no clipping) for even, intelligible
# loudness.
AUDIO_TARGET_PEAK = _env_float("AUDIO_TARGET_PEAK", 0.95)

# Silence duration between concatenated sentences (seconds), 100–200 ms.
SEGMENT_SILENCE_SEC = _env_float("SEGMENT_SILENCE_SEC", 0.15)

# Model version — part of the cache key. Bump it when the model/synthesis logic
# changes so the old cache is invalidated.
MODEL_VERSION = os.getenv("MODEL_VERSION", "kazakhtts2-tacotron2-v1")

# Size limit of the ready-made audio cache (bytes). When exceeded — LRU eviction
# of the oldest files by mtime.
CACHE_MAX_BYTES = _env_int("CACHE_MAX_BYTES", 500 * 1024 * 1024)  # 500 MB

# Inference device. Per the spec the project is CPU-only; exposed via env for the
# future.
TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")

# Default voice (preloaded at startup).
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "female3")

# CORS origins. Default — the Vite dev server. In production behind a single
# domain (frontend and API on one origin) CORS is not needed — set CORS_ORIGINS="".
CORS_ORIGINS = _env_list(
    "CORS_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)

# Rate limiting (per client IP) to protect the CPU from abuse. Applied by slowapi.
# RATE_LIMIT_ENABLED can be set to "0" to disable (e.g., in tests). TTS_RATE_LIMIT
# guards the expensive synthesis endpoints; DEFAULT_RATE_LIMIT is a generous
# global safety net for the rest.
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1") != "0"
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "240/minute")
TTS_RATE_LIMIT = os.getenv("TTS_RATE_LIMIT", "10/minute")

# Expose Prometheus metrics at /metrics (internal — not proxied by Caddy).
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "1") != "0"
