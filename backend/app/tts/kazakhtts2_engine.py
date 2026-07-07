"""KazakhTTS2 — the main and only TTS engine (ESPnet2 Tacotron2 +
ParallelWaveGAN vocoder), CPU inference.

Checkpoints live locally in backend/models/kazakhtts2/<voice>/ and are not
committed. Layout of a single voice:
    <voice>/
      exp/tts_train_raw_char/config.yaml        # ESPnet2 TTS config
      exp/tts_train_raw_char/*.pth              # Tacotron2 weights
      exp/tts_stats_raw_char/train/feats_stats.npz  # normalization stats
      vocoder/*.pkl                             # ParallelWaveGAN checkpoint
      vocoder/config.yml                        # vocoder config

Inference specifics (verified by a smoke test):
- the vocoder is loaded SEPARATELY (not via vocoder_file in Text2Speech), and the
  NORMALIZED mel out["feat_gen"] is fed to it — that is the space the KazakhTTS2
  vocoder was trained in (the denormalized one yields near silence);
- stats_file in config.yaml is a relative path, so at load time a runtime config
  with an absolute path is generated (without changing the process cwd);
- parallel_wavegan uses scipy.signal.kaiser, which moved to scipy.signal.windows
  in scipy>=1.13 — we install a compatibility shim before importing it.
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

# scipy>=1.13 compatibility shim for parallel_wavegan (before importing it).
if not hasattr(scipy.signal, "kaiser"):
    from scipy.signal.windows import kaiser as _kaiser

    scipy.signal.kaiser = _kaiser

from app.tts.base import BaseTTSEngine

logger = logging.getLogger(__name__)

# Default voice (loaded at application startup) if none is set explicitly.
DEFAULT_VOICE = "female1"

# Sample rate of the KazakhTTS2 models.
SAMPLE_RATE = 22050


class KazakhTTS2Engine(BaseTTSEngine):
    """KazakhTTS2 TTS engine (CPU by default)."""

    def __init__(
        self,
        models_dir: Path,
        device: str = "cpu",
        default_voice: str = DEFAULT_VOICE,
    ) -> None:
        # Root with voices: models/kazakhtts2/
        self._root = Path(models_dir) / "kazakhtts2"
        self._device = device
        self._default_voice = default_voice
        self._fs = SAMPLE_RATE
        # Cache of loaded models: voice -> (text2speech, vocoder)
        self._models: dict[str, tuple] = {}
        # List of available voice ids, determined in load().
        self._voices: list[str] = []
        # Lazy per-voice loading is thread-safe (syntheses are serialized by the
        # semaphore=1, but guard against warm-up races too).
        self._lock = threading.Lock()

    # --- Public interface ---

    def load(self) -> None:
        """Discover available voices and preload the default one."""
        self._voices = self._discover_voices()
        if not self._voices:
            raise RuntimeError(
                f"No KazakhTTS2 voice found in {self._root}. "
                "Download the checkpoints (see README)."
            )

        # Preload the default voice (or the first available one) so the model is
        # loaded once at startup, not on the first request.
        default = (
            self._default_voice
            if self._default_voice in self._voices
            else self._voices[0]
        )
        self._get_model(default)
        logger.info(
            "KazakhTTS2 loaded. Voices: %s. Preloaded: %s",
            ", ".join(self._voices),
            default,
        )

    def synthesize(self, text: str, voice: str, output_wav_path: str) -> str:
        """Synthesize a WAV from text with the chosen voice. Blocking CPU
        operation — call only via a thread pool."""
        if voice not in self._voices:
            raise ValueError(f"Unknown voice '{voice}'. Available: {self._voices}")

        text2speech, vocoder = self._get_model(voice)

        with torch.no_grad():
            out = text2speech(text.lower())
            # feat_gen is the normalized mel, exactly what the vocoder expects.
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

    # --- Internal ---

    def _discover_voices(self) -> list[str]:
        """Find voice folders with a complete set of files (model + vocoder)."""
        found: list[str] = []
        if not self._root.is_dir():
            return found
        for voice_dir in sorted(p for p in self._root.iterdir() if p.is_dir()):
            if self._voice_files(voice_dir) is not None:
                found.append(voice_dir.name)
        return found

    def _voice_files(self, voice_dir: Path) -> tuple[Path, Path, Path, Path] | None:
        """Return (config, model.pth, stats.npz, vocoder.pkl) or None if any file
        is missing."""
        exp = voice_dir / "exp" / "tts_train_raw_char"
        config = exp / "config.yaml"
        stats = voice_dir / "exp" / "tts_stats_raw_char" / "train" / "feats_stats.npz"
        pth = next(iter(sorted(exp.glob("*.pth"))), None)
        pkl = next(iter(sorted((voice_dir / "vocoder").glob("*.pkl"))), None)
        if config.is_file() and stats.is_file() and pth and pkl:
            return config, pth, stats, pkl
        return None

    def _get_model(self, voice: str) -> tuple:
        """Return the loaded (text2speech, vocoder) pair, loading and caching it
        if needed."""
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
        """Load Text2Speech and the vocoder for a voice."""
        # Heavy-stack imports are inside the method so the module imports fast and
        # ESPnet is pulled in only when a model is actually loaded.
        from espnet2.bin.tts_inference import Text2Speech
        from parallel_wavegan.utils import load_model as load_vocoder

        voice_dir = self._root / voice
        files = self._voice_files(voice_dir)
        if files is None:
            raise RuntimeError(f"Incomplete file set for voice '{voice}' in {voice_dir}")
        config, pth, stats, pkl = files

        # config.yaml references stats_file via a relative path — prepare a runtime
        # config with an absolute path so we do not change the process cwd.
        runtime_config = self._prepare_runtime_config(config, stats)

        logger.info("Loading voice '%s' (%s)...", voice, pth.name)
        text2speech = Text2Speech(
            train_config=str(runtime_config),
            model_file=str(pth),
            device=self._device,
            # Tacotron2 decoding params (as in the original synthesize.py).
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
        """Create a runtime copy of config.yaml next to it with an absolute
        stats_file."""
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
