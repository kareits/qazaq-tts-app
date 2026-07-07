"""Pydantic-схемы API."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Ответ /api/health — должен приходить мгновенно даже во время синтеза."""

    status: str
    device: str
    model_loaded: bool
    active_engine: str | None
    max_text_length: int


class Voice(BaseModel):
    """Описание голоса для /api/voices."""

    id: str
    name: str
    language: str
    engine: str


class VoicesResponse(BaseModel):
    voices: list[Voice]


class SplitRequest(BaseModel):
    """Запрос /api/split."""

    text: str


class Sentence(BaseModel):
    """Предложение с смещениями в исходном тексте (для подсветки на frontend)."""

    index: int
    text: str
    char_start: int
    char_end: int


class SplitResponse(BaseModel):
    """Ответ /api/split. warning != null, если текст не похож на казахский."""

    sentences: list[Sentence]
    warning: str | None = None


class SentenceRange(BaseModel):
    """Диапазон подряд идущих предложений (включительно). Применяется на
    Этапах 5-6; на Этапе 4 принимается, но не используется."""

    from_: int = Field(alias="from")
    to: int

    model_config = {"populate_by_name": True}


class TTSRequest(BaseModel):
    """Запрос /api/tts."""

    text: str
    voice: str = "female1"
    # В MVP формат всегда mp3; параметр оставлен для будущего расширения.
    format: str = "mp3"
    engine: str = "kazakhtts2"
    sentence_range: SentenceRange | None = None


class Segment(BaseModel):
    """Тайминги одного предложения в итоговом аудио."""

    index: int
    char_start: int
    char_end: int
    start_sec: float
    end_sec: float


class TTSResponse(BaseModel):
    """Ответ /api/tts."""

    audio_url: str
    format: str
    voice: str
    engine: str
    cached: bool
    duration_sec: float
    segments: list[Segment]
