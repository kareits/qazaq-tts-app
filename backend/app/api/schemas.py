"""Pydantic API schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response of /api/health — must return instantly even during synthesis."""

    status: str
    device: str
    model_loaded: bool
    active_engine: str | None
    max_text_length: int


class Voice(BaseModel):
    """Voice description for /api/voices."""

    id: str
    name: str
    language: str
    engine: str


class VoicesResponse(BaseModel):
    voices: list[Voice]


class SplitRequest(BaseModel):
    """Request of /api/split."""

    text: str


class Sentence(BaseModel):
    """A sentence with offsets into the source text (for frontend highlighting)."""

    index: int
    text: str
    char_start: int
    char_end: int


class SplitResponse(BaseModel):
    """Response of /api/split. warning != null if the text does not look Kazakh."""

    sentences: list[Sentence]
    warning: str | None = None


class SentenceRange(BaseModel):
    """Range of consecutive sentences (inclusive)."""

    from_: int = Field(alias="from")
    to: int

    model_config = {"populate_by_name": True}


class TTSRequest(BaseModel):
    """Request of /api/tts."""

    text: str
    voice: str = "female1"
    # In the MVP the format is always mp3; the parameter is kept for future use.
    format: str = "mp3"
    engine: str = "kazakhtts2"
    sentence_range: SentenceRange | None = None


class Segment(BaseModel):
    """Timing of a single sentence within the final audio."""

    index: int
    char_start: int
    char_end: int
    start_sec: float
    end_sec: float


class TTSResponse(BaseModel):
    """Response of /api/tts."""

    audio_url: str
    format: str
    voice: str
    engine: str
    cached: bool
    duration_sec: float
    segments: list[Segment]
