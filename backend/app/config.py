"""Настройки приложения: пути, лимиты, CORS.

Значения читаются из переменных окружения (для контейнеров/прода) с разумными
дефолтами для локальной разработки.
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
    """Список из переменной окружения (через запятую). Пустая строка -> []."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# Корень backend-проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Пути можно переопределить (в Docker — на volume): STORAGE_DIR, MODELS_DIR.
STORAGE_DIR = _env_path("STORAGE_DIR", BASE_DIR / "storage")
CACHE_DIR = STORAGE_DIR / "cache"
TMP_DIR = STORAGE_DIR / "tmp"
MODELS_DIR = _env_path("MODELS_DIR", BASE_DIR / "models")

# storage/cache и storage/tmp не коммитятся в git (.gitignore), поэтому
# создаём их при старте приложения, если отсутствуют.
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Лимит длины входного текста (символов). Отдаётся во frontend через /api/health,
# чтобы не хардкодить его там же.
MAX_TEXT_LENGTH = _env_int("MAX_TEXT_LENGTH", 1000)

# Целевой пик для нормализации громкости синтезированного аудио. Разные голоса
# KazakhTTS2 выдают сигнал сильно разного уровня (female1 тихий, female2 громкий),
# поэтому финальный WAV нормализуется по пику к этому значению (< 1.0 — без
# клиппинга), чтобы громкость была ровной и разборчивой.
AUDIO_TARGET_PEAK = _env_float("AUDIO_TARGET_PEAK", 0.95)

# Длительность тишины между склеиваемыми предложениями (сек), 100–200 мс.
SEGMENT_SILENCE_SEC = _env_float("SEGMENT_SILENCE_SEC", 0.15)

# Версия модели — часть ключа кэша. При смене модели/логики синтеза увеличить,
# чтобы старый кэш инвалидировался.
MODEL_VERSION = os.getenv("MODEL_VERSION", "kazakhtts2-tacotron2-v1")

# Лимит размера кэша готовых аудио (байт). При превышении — LRU-очистка самых
# старых файлов по mtime.
CACHE_MAX_BYTES = _env_int("CACHE_MAX_BYTES", 500 * 1024 * 1024)  # 500 МБ

# Устройство инференса. По ТЗ проект CPU-only; вынесено в env на будущее.
TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")

# Голос по умолчанию (предзагружается при старте).
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "female1")

# Origins для CORS. По умолчанию — Vite dev server. В проде за одним доменом
# (frontend и API на одном origin) CORS не нужен — задать CORS_ORIGINS="".
CORS_ORIGINS = _env_list(
    "CORS_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
