"""Настройки приложения: пути, лимиты, CORS."""

from pathlib import Path

# Корень backend-проекта
BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_DIR = BASE_DIR / "storage"
CACHE_DIR = STORAGE_DIR / "cache"
TMP_DIR = STORAGE_DIR / "tmp"
MODELS_DIR = BASE_DIR / "models"

# storage/cache и storage/tmp не коммитятся в git (.gitignore), поэтому
# создаём их при старте приложения, если отсутствуют.
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Лимит длины входного текста (символов). Отдаётся во frontend через /api/health,
# чтобы не хардкодить его там же.
MAX_TEXT_LENGTH = 1000

# Целевой пик для нормализации громкости синтезированного аудио. Разные голоса
# KazakhTTS2 выдают сигнал сильно разного уровня (female1 тихий, female2 громкий),
# поэтому финальный WAV нормализуется по пику к этому значению (< 1.0 — без
# клиппинга), чтобы громкость была ровной и разборчивой.
AUDIO_TARGET_PEAK = 0.95

# Длительность тишины между склеиваемыми предложениями (сек), 100–200 мс.
SEGMENT_SILENCE_SEC = 0.15

# Версия модели — часть ключа кэша. При смене модели/логики синтеза увеличить,
# чтобы старый кэш инвалидировался.
MODEL_VERSION = "kazakhtts2-tacotron2-v1"

# Лимит размера кэша готовых аудио (байт). При превышении — LRU-очистка самых
# старых файлов по mtime.
CACHE_MAX_BYTES = 500 * 1024 * 1024  # 500 МБ

# Origins, с которых разрешены запросы от frontend (Vite dev server).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
