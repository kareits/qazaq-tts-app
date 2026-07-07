# Kazakh TTS App

Local web application for synthesizing speech from Kazakh text (Cyrillic).
Runs fully locally, without cloud APIs, on CPU.

## Stack

- **Backend**: Python 3.10–3.11, FastAPI + Uvicorn, PyTorch (CPU build).
  The only TTS engine is KazakhTTS2 (ESPnet2, ISSAI). The MMS fallback engine
  was dropped from the project — we use KazakhTTS2 only.
- **Audio**: the pipeline working format is wav; conversion to mp3 only via
  `subprocess` + ffmpeg (do not use pydub). ffmpeg must be on PATH.
- **Frontend**: React + Vite + TypeScript.

## Key rules

- **venv**: all Python dependencies are installed into `backend/.venv`. Activate
  it before `pip install` and before running `uvicorn`. Pin package versions in
  `requirements.txt` (ESPnet is version-sensitive).
- **Non-blocking inference**: TTS inference is called only via
  `asyncio.to_thread` (or `run_in_executor`), never directly inside a FastAPI
  handler. Concurrent syntheses are limited by a semaphore = 1. `/api/health`
  must respond instantly even during synthesis. The model is loaded once at
  startup (lifespan), not on every request.
- **Single sentence-splitting function**: splitting text into sentences happens
  ONLY on the backend (`text_normalizer.py`) and serves both `/api/split` and
  `/api/tts`. The frontend never splits text itself — it only uses the result of
  `/api/split`, otherwise highlighting and range selection break due to diverging
  boundaries.
- **mp3 is the only download format in the MVP**. The internal working format is
  wav (synthesis and segment concatenation); conversion to mp3 is the final step
  via ffmpeg. The `format` parameter is kept in the API for future extension
  (wav, ogg, m4a), but the format choice is not shown in the UI in the first
  stage.
- Do not commit model weights (`backend/models/`), `.venv`,
  `backend/storage/cache`, `backend/storage/tmp`, `node_modules`, `dist`.
- **Code comments and docstrings are in English.** The UI is multilingual
  (ru/kk/en, default ru) via the frontend i18n layer (`src/i18n/`) — add new UI
  strings as translation keys, not hardcoded text. Backend API error messages stay
  in Russian. Log errors via `logging`, not `print`.
- Do not mix API logic and TTS inference (engines are isolated in `app/tts/`).

## Stage order

Development follows the spec stages (`Kazakh_TTS_App_Specification.md`): 1 —
skeleton, 2 — audio pipeline without a model, 4 — KazakhTTS2 (the main and only
engine), 5 — normalization/segments/cache, 6 — player and synchronization,
7 — UX. Stage 3 (MMS fallback) was dropped by team decision. Move to the next
stage only after user confirmation.
