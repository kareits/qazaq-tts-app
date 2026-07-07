# Kazakh TTS App

Local web application for synthesizing speech from Kazakh text (Cyrillic). Runs
fully locally, without cloud APIs, on CPU.

- **Backend**: Python + FastAPI, the **KazakhTTS2** engine (ESPnet2 Tacotron2 +
  ParallelWaveGAN vocoder), CPU inference.
- **Frontend**: React + Vite + TypeScript.
- **Audio**: working format is wav, download format is mp3 (conversion via ffmpeg).

Features: Kazakh text input, choice of 5 voices, synthesis (with progress),
playback (Start/Pause/Stop), highlighting of the current sentence in sync with
the audio, selecting a sentence range to synthesize, mp3 download, caching.

## Requirements

- **Python 3.10–3.11**
- **Node.js 18+** and npm
- **ffmpeg** on PATH (wav → mp3 conversion)
- ~1.5 GB of space for the models (5 voices), ~600 MB of download traffic

## Install and run

### 1. Backend

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
# parallel_wavegan is installed separately (its setup.py breaks in an isolated build):
pip install --no-build-isolation parallel_wavegan==0.6.1
# Download the KazakhTTS2 models (5 voices) into backend/models/kazakhtts2/:
python scripts/download_kazakhtts2.py
# Run:
uvicorn app.main:app --reload
```

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pip install --no-build-isolation parallel_wavegan==0.6.1
python scripts/download_kazakhtts2.py
uvicorn app.main:app --reload
```

The backend comes up on `http://127.0.0.1:8000` (Swagger: `/docs`). The model is
loaded once at startup. Details — in [backend/README.md](backend/README.md).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend opens on `http://localhost:5173` and talks to the backend at
`http://127.0.0.1:8000` (CORS configured).

## Installing ffmpeg

- **Windows**: `winget install Gyan.FFmpeg` (or download a build and add it to PATH)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

The backend checks for ffmpeg at startup and logs an error if it is missing.

## KazakhTTS2 models

The weights are not stored in the repository. `backend/scripts/download_kazakhtts2.py`
downloads them from the ISSAI servers (repository
[IS2AI/Kazakh_TTS](https://github.com/IS2AI/Kazakh_TTS)) and lays them out in
`backend/models/kazakhtts2/<voice>/`. Voices: `female1`, `female2`, `female3`,
`male1`, `male2` (default `female1`).

> KazakhTTS2 license — **CC-BY-4.0** (commercial use allowed with attribution).
> Attribution requirements and details — in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Server deployment (Docker)

Production layout: **single domain** — Caddy serves the frontend static assets
and proxies `/api` to the backend (auto-HTTPS), so no CORS is needed. Files:
`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` +
`frontend/Caddyfile`.

```bash
cp .env.example .env          # set SITE_ADDRESS (domain for HTTPS)
docker compose build
docker compose run --rm backend python scripts/download_kazakhtts2.py  # models into a volume (~600 MB, once)
docker compose up -d
```

Locally it opens on `http://localhost`. For production set the domain in `.env`
(`SITE_ADDRESS=tts.example.kz`) — Caddy issues the TLS certificate itself.

Configuration via backend environment variables: `CORS_ORIGINS` (empty for a
single domain), `MAX_TEXT_LENGTH`, `CACHE_MAX_BYTES`, `DEFAULT_VOICE`,
`MODELS_DIR`, `STORAGE_DIR`, `TTS_DEVICE`. Frontend: `VITE_BACKEND_URL` (empty →
relative paths). The full plan (VPS provisioning, rate limiting, scaling, mobile
app) — in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Architecture (key rules)

- **CPU only**: torch is the CPU build; the engine explicitly uses `device="cpu"`.
- **Non-blocking inference**: synthesis runs through a thread pool with a
  semaphore = 1; `/api/health` responds instantly even during generation.
- **Single sentence-splitting function** — backend only
  (`text_normalizer.split_sentences`), serving both `/api/split` and `/api/tts`,
  so sentence boundaries and char offsets are always consistent with highlighting.
- **mp3 is the only download format in the MVP**; the pipeline's internal format
  is wav; conversion to mp3 is the final step via ffmpeg.
- **Cache** of ready audio keyed by a hash (text+voice+engine+format+version+range)
  with LRU eviction; segment timings are in a json next to the mp3.

## API (brief)

`GET /api/health` · `GET /api/voices` · `POST /api/split` ·
`POST /api/tts` · `POST /api/tts/stream` (SSE with progress) ·
`GET /api/audio/{filename}`. Details — in [backend/README.md](backend/README.md).

## Notes

- **Quality**: these are the open 2022 KazakhTTS2 checkpoints — voice timbre/level
  varies; loudness is evened out with peak normalization. Quality improvements
  (other models, dereverberation, ONNX) — after the MVP.
- **CPU inference is slow** (seconds per sentence) — this is normal; the UI shows
  progress.
- **Numbers and dates** are better written as words (there is a hint in the UI).
- **Plan B (Windows)**: if building ESPnet/the vocoder fails on Windows — run the
  backend in WSL2 (the frontend stays on Windows, talking over localhost). On the
  reference machine the native Windows install succeeded.

## Documents

- [docs/PLAN.md](docs/PLAN.md) — development plan and stage statuses
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — server deployment and mobile app plan
- [backend/README.md](backend/README.md) — backend details
- `Kazakh_TTS_App_Specification.md` — original specification (in Russian)
