# Kazakh TTS Backend

Backend for synthesizing Kazakh speech on CPU. The engine is **KazakhTTS2**
(ESPnet2 Tacotron2 + ParallelWaveGAN vocoder), CPU inference.

## Install (Windows, PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
# parallel_wavegan is installed separately: its setup.py does `import pip`, which
# breaks in a modern pip isolated build.
pip install --no-build-isolation parallel_wavegan==0.6.1
```

macOS / Linux — similarly (`python3 -m venv .venv`, `source .venv/bin/activate`).

torch/torchaudio are installed as the CPU build via an extra PyTorch index that is
already declared in `requirements.txt` (`--extra-index-url`).

## Models (checkpoints)

The weights are not committed (`.gitignore`). They are downloaded by a script
(idempotent, stdlib only — can be run even before `pip install`):

```powershell
python scripts/download_kazakhtts2.py            # all 5 voices
python scripts/download_kazakhtts2.py female1    # only the selected ones
python scripts/download_kazakhtts2.py --force    # re-download
```

The script downloads from the ISSAI servers and lays them out in
`backend/models/kazakhtts2/<voice>/`:

```
<voice>/
  exp/tts_train_raw_char/config.yaml            # ESPnet2 TTS config
  exp/tts_train_raw_char/*.pth                  # Tacotron2 weights
  exp/tts_stats_raw_char/train/feats_stats.npz  # normalization stats
  vocoder/*.pkl                                 # ParallelWaveGAN checkpoint
  vocoder/config.yml
```

Voices: `female1`, `female2`, `female3`, `male1`, `male2` (default `female1`).
Source: the IS2AI/Kazakh_TTS repository, files at
`issai.nu.edu.kz/wp-content/uploads/2022/03/` (`kaztts_<voice>_tacotron2_*.zip`
and `parallelwavegan_<voice>_checkpoint.zip`).

## Run

```powershell
uvicorn app.main:app --reload
```

The backend comes up on `http://127.0.0.1:8000`. The model is loaded once at
startup (lifespan). If the checkpoints are missing, the app still starts but
`/api/health` reports `model_loaded: false` and `/api/tts` returns 503.

## API

- `GET /api/health` — state (status, device, model_loaded, active_engine,
  max_text_length). Responds instantly even during synthesis.
- `GET /api/voices` — list of voices.
- `POST /api/split` — `{text}` → sentences with char offsets
  (`{index, text, char_start, char_end}`) + `warning` if the text does not look
  like Kazakh Cyrillic. The same splitting function as in `/api/tts`.
- `POST /api/tts` — synthesis: `{text, voice, format, engine, sentence_range?}`
  → mp3 + per-segment timings. Inference is non-blocking (thread pool +
  semaphore=1). The result is cached (a repeated request — `cached: true`).
- `POST /api/tts/stream` — the same synthesis over Server-Sent Events, emitting
  progress events per sentence plus the final result.
- `GET /api/audio/{filename}` — serve a ready mp3 (attachment).

## System dependencies

- **ffmpeg** must be installed and on PATH — checked at startup (lifespan), used
  for wav → mp3 conversion.
- CPU inference is slow (seconds per sentence) — this is normal for the MVP.

## Inference technical notes

- The vocoder is loaded SEPARATELY (not via `vocoder_file` in `Text2Speech`); the
  normalized mel `out["feat_gen"]` is fed to it — that is the space the KazakhTTS2
  vocoder was trained in (the denormalized one yields near silence).
- `stats_file` in `config.yaml` is relative — at load time a runtime config with
  an absolute path is generated (without changing the process cwd).
- `parallel_wavegan` uses `scipy.signal.kaiser`, which moved to
  `scipy.signal.windows` in scipy≥1.13 — the engine installs a compatibility shim.
- Voice loudness varies a lot (female1 quiet, female2 loud), so the final WAV is
  peak-normalized to `AUDIO_TARGET_PEAK` (config) in
  `audio_service.normalize_wav_peak` before conversion to mp3.

## Plan B (if ESPnet does not build on Windows)

On this machine the native Windows install (Python 3.11) succeeded. If building
ESPnet/the vocoder fails on another machine — run the backend in WSL2 (the
frontend stays on Windows and talks to the backend over localhost).

## Implementation status

- Stage 1 (skeleton): `/api/health`.
- Stage 2 (audio pipeline): `audio_service.py`, `/api/audio/{filename}`.
- Stage 4 (KazakhTTS2): the engine (`app/tts/`), `tts_service.py` (non-blocking
  synthesis), `/api/voices`, `/api/tts`, loudness normalization.
- Stage 5 (normalization, segments, cache): `text_normalizer.py` (the single
  sentence-splitting function), `/api/split`, per-segment synthesis with
  concatenation and timings, `sentence_range`, `cache_service.py` (cache + json
  timings + LRU eviction). The temporary `/api/dev/test-audio` was removed.
```
