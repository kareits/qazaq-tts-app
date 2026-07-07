"""Base TTS engine interface.

Engines are isolated from the API layer: FastAPI handlers work only through this
interface and know nothing about ESPnet/the vocoder.
"""

from abc import ABC, abstractmethod


class BaseTTSEngine(ABC):
    """Abstract TTS engine."""

    @abstractmethod
    def load(self) -> None:
        """Load the model(s) into memory. Called once at application startup
        (lifespan), not on every request."""

    @abstractmethod
    def synthesize(self, text: str, voice: str, output_wav_path: str) -> str:
        """Synthesize speech from text and save it as WAV at the given path.

        Blocking CPU operation — call it only via a thread pool, not directly in
        an async handler. Returns the path to the created WAV.
        """

    @abstractmethod
    def available_voices(self) -> list[dict]:
        """List of available voices: [{id, name, language, engine}, ...]."""
