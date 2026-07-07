# Kazakh TTS App — development plan (current version)

## Context

Local web application for synthesizing Kazakh speech (Cyrillic) per the spec
`Kazakh_TTS_App_Specification.md`. Runs fully locally, on CPU, without cloud APIs.

**Important team decision:** the MMS fallback model (`facebook/mms-tts-kaz`) is
excluded from the project. ONLY KazakhTTS2 is used. Accordingly, Stage 3 from the
original spec is skipped, and KazakhTTS2 becomes the main and only engine.

Stack: Python 3.10–3.11, FastAPI + Uvicorn, PyTorch (CPU), ESPnet2 (KazakhTTS2),
soundfile/numpy, ffmpeg (subprocess, not pydub), React + Vite + TypeScript.

## Stage status

### ✅ Stage 1. Skeleton — DONE
- FastAPI backend + `/api/health`, CORS, config, requirements with pinned versions.
- React + Vite + TS frontend, frontend → backend connectivity check.
- git init, .gitignore, CLAUDE.md.

### ✅ Stage 2. Audio pipeline without a model — DONE
- `audio_service.py`: ffmpeg check, wav → mp3, duration measurement.
- `GET /api/audio/{filename}` (FileResponse, Content-Disposition: attachment).
- A temporary `POST /api/dev/test-audio` (test tone, to be removed in Stage 4/5).
- ffmpeg check at startup (lifespan).
- Frontend: generate test audio, play it, download the mp3.

### ⛔ Stage 3. MMS fallback — EXCLUDED
Not implemented. KazakhTTS2 is the only engine.

### ✅ Stage 4. KazakhTTS2 — DONE (the main and only engine)
- Models: Tacotron2 + ParallelWaveGAN vocoder, 5 voices (female1..3, male1..2) in
  `backend/models/kazakhtts2/<voice>/` (not committed).
- The stack was installed natively on Windows (Python 3.11): torch 2.12.1+cpu,
  torchaudio 2.11.0+cpu, espnet 202511, parallel_wavegan 0.6.1. Versions pinned in
  `requirements.txt` (+ a separate step for parallel_wavegan).
- `tts/base.py` (`BaseTTSEngine`) + `tts/kazakhtts2_engine.py`: the model is loaded
  once in the lifespan (default voice), the rest lazily; isolated from the API.
- `tts_service.py`: non-blocking synthesis (`asyncio.to_thread` + semaphore=1);
  `/api/health` responds in ~50 ms even during synthesis (verified).
- `/api/voices`, `/api/tts` (whole text → wav → mp3 + one timing segment);
  `/api/health` returns `model_loaded: true`, `active_engine: "kazakhtts2"`.
- Frontend: voice selection, text input, "Synthesize", playback, mp3 download
  (custom player and highlighting — Stage 6).
- **Key technical findings** (see the backend README): the vocoder is loaded
  separately and gets the normalized `feat_gen`; a runtime config with an absolute
  `stats_file`; a `scipy.signal.kaiser` shim for scipy≥1.13.
- The native Windows build succeeded — the WSL2 plan B was not needed.
- **Loudness normalization**: KazakhTTS2 voices produce very different signal
  levels (female1 ≈0.1, female2 ≈0.69 peak). Peak normalization of the final WAV
  to `AUDIO_TARGET_PEAK` (0.95) was added in `audio_service.normalize_wav_peak`,
  called in `tts_service` before conversion to mp3. All voices are brought to a
  single level (≈ −0.9 dB peak). Normalization is applied to the final
  (concatenated) audio, not per segment, so there are no loudness jumps between
  sentences in Stage 5.
- Residual quality (timbre/reverberation of individual speakers) is a property of
  the open 2022 KazakhTTS2 checkpoints; timbre improvement/dereverberation is
  post-MVP.

### ✅ Stage 5. Normalization, segments, cache — DONE
- `text_normalizer.py` — the SINGLE `split_sentences` function with
  char_start/char_end relative to the SOURCE text (serves both `/api/split` and
  `/api/tts` — boundaries always match). Verified on the spec example (0-14,
  15-25, 26-42). Plus `normalize_text` (trim/collapse) and a Kazakh-Cyrillic
  heuristic.
- `POST /api/split` — sentences + `warning` if the text is not Kazakh.
- Per-segment synthesis: each sentence → wav, concatenation into one wav with
  `SEGMENT_SILENCE_SEC`=0.15 s of silence between sentences, real `segments`
  timings in the `/api/tts` response (verified: gaps exactly 0.15 s). The
  temporary `/api/dev/test-audio` was removed.
- `cache_service.py` — cache keyed by
  `sha256(normalized_text + voice + engine + format + MODEL_VERSION + range)`;
  a json with timings next to the mp3; LRU eviction by mtime when `CACHE_MAX_BYTES`
  (500 MB) is exceeded. Verified: a repeated request — `cached: true` in ~28 ms
  vs ~16 s.
- `sentence_range` in `/api/tts` — synthesis of the selected range; segment indices
  and char offsets are preserved as the originals (for highlighting in Stage 6).
- Loudness normalization is applied to the final (concatenated) audio.
- `/api/health` stays non-blocking during multi-segment synthesis (~15 ms,
  verified).

### ✅ Stage 6. Player and text synchronization — DONE
- The frontend is split into components per the spec: `api/ttsApi.ts` (types +
  client), `VoiceSelect`, `TextInput` (counter + hint), `SentenceView`,
  `AudioPlayer` (hidden `<audio>`, forwardRef), `PlayerControls`, `DownloadButton`;
  state orchestration — in `App.tsx`.
- `SentenceView`: sentences from `/api/split` as clickable spans; click — select
  one, Shift-click — extend the range (from..to model), click again — clear; on
  text change the selection/markup is reset, `/api/split` is called again with a
  500 ms debounce.
- `sentence_range` from the selection goes to `/api/tts` (whole text if nothing is
  selected).
- Custom Start/Pause/Stop player (native controls hidden); buttons disabled without
  audio; progress bar and timecode.
- Highlighting of the current sentence via `timeupdate` (start_sec ≤ t < end_sec),
  freezes on pause, cleared on Stop and at the end.
- Click-to-seek: clicking a sentence seeks to its `start_sec`.
- typecheck passes; Vite HMR applies changes cleanly; interactivity — for the
  user's visual check.

### Stage 7. UX polish (in progress)
1. ✅ Generation indicator: a **progress bar with percentages** over the honest
   stream (SSE `POST /api/tts/stream`) — a progress event arrives after the actual
   synthesis of each sentence (30/60/90% for 3 sentences, then concat 93%, encode
   98%). Error block (text from the API) — present.
2. ✅ mp3 download button.
3. ✅ Hints ("numbers as words"), character counter.
4. ✅ Look and feel: the dark "Keshki dala" theme (flag palette — blue #00AFCA +
   gold #FEC50C), the oyu-ornek ornament (a subtle accent), a sun mark, a gold glow
   of the current sentence. Russian interface.
5. ✅ Playback speed slider (0.1–3.0, step 0.1, default 1.0) driving
   `audio.playbackRate`.

Streaming synthesis: `tts_service.synthesize_stream` (an async event generator),
`POST /api/tts/stream` (StreamingResponse/SSE). The non-streaming `POST /api/tts`
is kept (a wrapper over the generator). Non-blocking health during the stream is
confirmed (~25 ms).

### MVP finalization — DONE
- `backend/scripts/download_kazakhtts2.py` — a cross-platform idempotent script to
  download the 5 voices (stdlib only). Models install reproducibly on any machine.
- Root `README.md` — full install/run (backend venv + ffmpeg + parallel_wavegan +
  the model script + frontend), architecture, API, the WSL2 plan B.

## Definition of Done (MVP) — ✅ MET

All spec items (except the excluded MMS fallback) are closed:
- ✅ backend locally on CPU; `/api/health` responds during synthesis;
- ✅ frontend locally; Kazakh text input → audio synthesis;
- ✅ Start/Pause/Stop playback; highlighting of the current sentence in sync;
- ✅ selecting a range of consecutive sentences and synthesizing only them;
- ✅ mp3 download;
- ✅ KazakhTTS2 — the main and only engine;
- ✅ long text is split into segments; timings in the API;
- ✅ cache with LRU (a repeated request — from cache);
- ✅ README with instructions (ffmpeg, the WSL2 plan B, the model script).

Beyond the spec: streaming synthesis with a progress bar (SSE), loudness
normalization, Kazakh UI styling (dark theme + ornament), a playback speed slider.

## Post-MVP ideas (do not start without confirmation)

- Change the default voice (female2/female3 sound cleaner than female1).
- Automated tests (pytest): the single splitting function, cache/LRU,
  sentence_range.
- KazEmoTTS (emotions), ONNX export (CPU speedup), Latin script (transliteration),
  word-level highlighting (forced alignment), batch generation of long texts.
- Server deployment and an Android (Google Play) app — see
  [DEPLOYMENT.md](DEPLOYMENT.md).

## Key architectural rules (cross-cutting)

- venv only in `backend/.venv`; package versions pinned in `requirements.txt`.
- Non-blocking inference: thread pool + semaphore = 1; the model is loaded once at
  startup; `/api/health` always responds instantly.
- A single sentence-splitting function on the backend; the frontend uses only the
  result of `/api/split`.
- mp3 is the only download format in the MVP; the internal format is wav;
  conversion at the end via ffmpeg; the `format` parameter is reserved.
- Do not commit: `models/`, `.venv`, `storage/cache`, `storage/tmp`,
  `node_modules`, `dist`.
- Code comments and docstrings are in English; user-facing UI text and API error
  messages stay in Russian; log via `logging`, not `print`; API logic and TTS
  inference are not mixed.
