"""Базовый интерфейс TTS-движка.

Движки изолированы от API-слоя: обработчики FastAPI работают только через этот
интерфейс, ничего не зная о ESPnet/вокодере.
"""

from abc import ABC, abstractmethod


class BaseTTSEngine(ABC):
    """Абстрактный TTS-движок."""

    @abstractmethod
    def load(self) -> None:
        """Загрузить модель(и) в память. Вызывается один раз при старте
        приложения (lifespan), не на каждый запрос."""

    @abstractmethod
    def synthesize(self, text: str, voice: str, output_wav_path: str) -> str:
        """Синтезировать речь из текста и сохранить в WAV по указанному пути.

        Блокирующая CPU-операция — вызывать только через thread pool, а не
        напрямую в асинхронном обработчике. Возвращает путь к созданному WAV.
        """

    @abstractmethod
    def available_voices(self) -> list[dict]:
        """Список доступных голосов: [{id, name, language, engine}, ...]."""
