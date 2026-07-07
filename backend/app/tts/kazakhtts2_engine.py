"""KazakhTTS2 — основной и единственный TTS-движок (ESPnet2 Tacotron2 +
ParallelWaveGAN-вокодер), инференс на CPU.

Checkpoint'ы лежат локально в backend/models/kazakhtts2/<voice>/ и не коммитятся.
Раскладка одного голоса:
    <voice>/
      exp/tts_train_raw_char/config.yaml        # конфиг ESPnet2 TTS
      exp/tts_train_raw_char/*.pth              # веса Tacotron2
      exp/tts_stats_raw_char/train/feats_stats.npz  # статистика нормализации
      vocoder/*.pkl                             # чекпоинт ParallelWaveGAN
      vocoder/config.yml                        # конфиг вокодера

Особенности инференса (проверены смок-тестом):
- вокодер грузится ОТДЕЛЬНО (не через vocoder_file в Text2Speech), и в него
  подаётся НОРМАЛИЗОВАННЫЙ мел out["feat_gen"] — именно в этом пространстве
  обучался вокодер KazakhTTS2 (денормализованный даёт почти тишину);
- stats_file в config.yaml задан относительным путём, поэтому при загрузке
  генерируется рантайм-конфиг с абсолютным путём (без смены cwd процесса);
- parallel_wavegan использует scipy.signal.kaiser, перенесённую в
  scipy.signal.windows в scipy>=1.13 — ставим совместимый shim до импорта.
"""

import logging
import re
import threading
from pathlib import Path

import numpy as np
import scipy.signal
import soundfile as sf
import torch
import yaml

# Shim совместимости scipy>=1.13 для parallel_wavegan (до его импорта).
if not hasattr(scipy.signal, "kaiser"):
    from scipy.signal.windows import kaiser as _kaiser

    scipy.signal.kaiser = _kaiser

from app.tts.base import BaseTTSEngine

logger = logging.getLogger(__name__)

# Голос по умолчанию (грузится при старте приложения), если не задан явно.
DEFAULT_VOICE = "female1"

# Частота дискретизации моделей KazakhTTS2.
SAMPLE_RATE = 22050


class KazakhTTS2Engine(BaseTTSEngine):
    """TTS-движок KazakhTTS2 (по умолчанию CPU)."""

    def __init__(
        self,
        models_dir: Path,
        device: str = "cpu",
        default_voice: str = DEFAULT_VOICE,
    ) -> None:
        # Корень с голосами: models/kazakhtts2/
        self._root = Path(models_dir) / "kazakhtts2"
        self._device = device
        self._default_voice = default_voice
        self._fs = SAMPLE_RATE
        # Кэш загруженных моделей: voice -> (text2speech, vocoder)
        self._models: dict[str, tuple] = {}
        # Список доступных голосов (id), определяется при load().
        self._voices: list[str] = []
        # Ленивая загрузка голоса потокобезопасна (синтезы сериализованы
        # семафором=1, но подстрахуемся на случай прогрева).
        self._lock = threading.Lock()

    # --- Публичный интерфейс ---

    def load(self) -> None:
        """Обнаружить доступные голоса и предзагрузить голос по умолчанию."""
        self._voices = self._discover_voices()
        if not self._voices:
            raise RuntimeError(
                f"Не найдено ни одного голоса KazakhTTS2 в {self._root}. "
                "Скачайте checkpoint'ы (см. README)."
            )

        # Предзагружаем дефолтный голос (или первый доступный), чтобы модель
        # грузилась один раз при старте, а не на первый запрос.
        default = (
            self._default_voice
            if self._default_voice in self._voices
            else self._voices[0]
        )
        self._get_model(default)
        logger.info(
            "KazakhTTS2 загружен. Голоса: %s. Предзагружен: %s",
            ", ".join(self._voices),
            default,
        )

    def synthesize(self, text: str, voice: str, output_wav_path: str) -> str:
        """Синтезировать WAV из текста выбранным голосом. Блокирующая
        CPU-операция — вызывать только через thread pool."""
        if voice not in self._voices:
            raise ValueError(f"Неизвестный голос '{voice}'. Доступны: {self._voices}")

        text2speech, vocoder = self._get_model(voice)

        with torch.no_grad():
            out = text2speech(text.lower())
            # feat_gen — нормализованный мел, именно его ждёт вокодер.
            wav = vocoder.inference(out["feat_gen"]).view(-1).cpu().numpy()

        wav = wav.astype(np.float32)
        sf.write(output_wav_path, wav, self._fs)
        return output_wav_path

    def available_voices(self) -> list[dict]:
        return [
            {
                "id": v,
                "name": self._display_name(v),
                "language": "kk",
                "engine": "kazakhtts2",
            }
            for v in self._voices
        ]

    @property
    def sample_rate(self) -> int:
        return self._fs

    # --- Внутреннее ---

    def _discover_voices(self) -> list[str]:
        """Найти папки голосов с полным набором файлов (модель + вокодер)."""
        found: list[str] = []
        if not self._root.is_dir():
            return found
        for voice_dir in sorted(p for p in self._root.iterdir() if p.is_dir()):
            if self._voice_files(voice_dir) is not None:
                found.append(voice_dir.name)
        return found

    def _voice_files(self, voice_dir: Path) -> tuple[Path, Path, Path, Path] | None:
        """Вернуть (config, model.pth, stats.npz, vocoder.pkl) или None, если
        какого-то файла нет."""
        exp = voice_dir / "exp" / "tts_train_raw_char"
        config = exp / "config.yaml"
        stats = voice_dir / "exp" / "tts_stats_raw_char" / "train" / "feats_stats.npz"
        pth = next(iter(sorted(exp.glob("*.pth"))), None)
        pkl = next(iter(sorted((voice_dir / "vocoder").glob("*.pkl"))), None)
        if config.is_file() and stats.is_file() and pth and pkl:
            return config, pth, stats, pkl
        return None

    def _get_model(self, voice: str) -> tuple:
        """Вернуть загруженную пару (text2speech, vocoder), при необходимости
        загрузив её и закэшировав."""
        cached = self._models.get(voice)
        if cached is not None:
            return cached
        with self._lock:
            cached = self._models.get(voice)
            if cached is not None:
                return cached
            model = self._load_voice(voice)
            self._models[voice] = model
            return model

    def _load_voice(self, voice: str) -> tuple:
        """Загрузить Text2Speech и вокодер для голоса."""
        # Импорты тяжёлого стека — внутри метода, чтобы модуль импортировался
        # быстро, а ESPnet тянулся только при реальной загрузке модели.
        from espnet2.bin.tts_inference import Text2Speech
        from parallel_wavegan.utils import load_model as load_vocoder

        voice_dir = self._root / voice
        files = self._voice_files(voice_dir)
        if files is None:
            raise RuntimeError(f"Неполный набор файлов для голоса '{voice}' в {voice_dir}")
        config, pth, stats, pkl = files

        # config.yaml ссылается на stats_file относительным путём — готовим
        # рантайм-конфиг с абсолютным путём, чтобы не менять cwd процесса.
        runtime_config = self._prepare_runtime_config(config, stats)

        logger.info("Загрузка голоса '%s' (%s)...", voice, pth.name)
        text2speech = Text2Speech(
            train_config=str(runtime_config),
            model_file=str(pth),
            device=self._device,
            # Параметры декодирования Tacotron2 (как в оригинальном synthesize.py).
            threshold=0.5,
            minlenratio=0.0,
            maxlenratio=10.0,
            use_att_constraint=True,
            backward_window=1,
            forward_window=3,
        )
        vocoder = load_vocoder(str(pkl)).to(self._device).eval()
        vocoder.remove_weight_norm()
        return text2speech, vocoder

    @staticmethod
    def _prepare_runtime_config(config: Path, stats: Path) -> Path:
        """Создать рядом рантайм-копию config.yaml с абсолютным stats_file."""
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
        normalize_conf = data.get("normalize_conf") or {}
        normalize_conf["stats_file"] = str(stats.resolve())
        data["normalize_conf"] = normalize_conf
        runtime = config.with_name("config.runtime.yaml")
        runtime.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return runtime

    @staticmethod
    def _display_name(voice_id: str) -> str:
        """female1 -> 'Female 1', male2 -> 'Male 2'."""
        m = re.match(r"([a-zA-Z]+)(\d+)$", voice_id)
        if m:
            return f"{m.group(1).capitalize()} {m.group(2)}"
        return voice_id
