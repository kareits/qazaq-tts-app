# Plan: server deployment + mobile app (Google Play)

This document describes the move from the local MVP to a server-hosted service and
to an Android app on Google Play. It is a plan, not an implementation — move
through the stages upon confirmation.

## Context and key constraints

- The **KazakhTTS2** engine is heavy: torch (CPU) + ESPnet + vocoder, ~1.5 GB of
  weights (5 voices), venv ~3 GB. CPU inference — **seconds per sentence**,
  concurrent syntheses limited by a semaphore = 1 per process.
- Two consequences follow that shape the whole architecture:
  1. **The mobile app cannot run the model on-device** → it is a thin client to
     the server API (synthesis on the server).
  2. **The server is CPU-intensive** → a queue/limits are needed, otherwise public
     access can easily be overwhelmed (and CPU time costs money).

## License and commercial use (checked)

**Bottom line: commercial use is allowed, subject to attribution.**

- The KazakhTTS2 models are under **CC-BY-4.0** (the `LICENSE.md` file in
  IS2AI/Kazakh_TTS; confirmed by the GitHub API `SPDX: CC-BY-4.0` and the license
  text — standard, unmodified). CC-BY-4.0 **explicitly permits commercial use**;
  the obligation is attribution.
- The `README` adds: (a) an ethical restriction (do not generate obscene/offensive/
  discriminatory content), (b) an attribution requirement (paper title, author,
  organization). Both are easy to comply with.
- The dataset on HuggingFace has no explicit license, but we do **not distribute**
  the corpus (we use only the pretrained models under CC-BY-4.0).
- Dependencies are permissive: ESPnet (Apache-2.0), parallel_wavegan (MIT), PyTorch
  (BSD), FastAPI/uvicorn/pydantic (MIT/BSD). ffmpeg is called as an external binary
  (subprocess, no linking) — GPL does not propagate to our code; for commercial use
  prefer an LGPL ffmpeg build or require the system one.

**Required actions for a commercial release:**
1. Attribution in the app (an "About" screen/credits), in the store listing, and in
   the repository: cite the KazakhTTS2 papers (Mussakhojayeva et al., LREC 2022,
   arXiv:2201.05771) and KazakhTTS (Interspeech 2021), the author, and ISSAI,
   Nazarbayev University.
2. State that the model is used unmodified (or note the changes — CC-BY requires it).
3. Add the ethical clause to the app's Terms of Service.

**Residual risks (resolve before launch):**
- The ambiguity "pure CC-BY vs the added ethical restriction" — obtain **written
  confirmation from ISSAI** (issai@nu.edu.kz / the paper authors) for commercial
  use and agree on the attribution wording.
- Legal review before a commercial launch (I am not a lawyer; the above is a
  factual analysis, not legal advice).

## ⚠️ Other items to close BEFORE publishing

1. **KazakhTTS2 license** — checked above (CC-BY-4.0, commercial allowed with
   attribution; written ISSAI confirmation is desirable).
2. **Privacy**: the local MVP had the advantage "text never leaves the device". In
   the hosted/mobile version **text goes to the server** — a privacy policy and
   disclosure in Play Data Safety are needed.
3. **Abuse/cost**: without rate limiting/captcha/keys, public synthesis can be used
   for DoS and "burn" CPU. Limits are needed.

## Recorded decisions (from the user)

- **Product: commercial** → the license check is priority #1 (done above; written
  ISSAI confirmation is desirable).
- **Mobile: Capacitor** (see Part B).
- **Hosting: recommend** → recommendation: own VPS (see A0).

---

## Part A. Server deployment

### A0. Target platform and sizing
- Recommendation: **own VPS** (Hetzner/DigitalOcean/Selectel) — cheapest for CPU
  load. No GPU needed.
- Minimum: 2–4 vCPU, 4–8 GB RAM (model ~0.5–1 GB in memory + torch), 15+ GB SSD
  (models ~2 GB + venv + cache). More vCPU = faster single synthesis (torch threads)
  and more workers.
- Alternative: Fly.io / Cloud Run — but watch out for the "cold start" (model load
  ~5 s) and keep the instance "warm".

### A1. Containerization (Docker)
- **Backend Dockerfile** (`python:3.11-slim`): install ffmpeg, system dependencies,
  `pip install -r requirements.txt`, separately
  `pip install --no-build-isolation parallel_wavegan==0.6.1`, copy `app/`. Do **not**
  bake the models into the image (1.5 GB) — mount a volume or download on first
  start with `scripts/download_kazakhtts2.py` into the volume.
- **Frontend**: a multi-stage build (`node` → `npm run build` → static `dist/`
  files), served by nginx/Caddy.
- **docker-compose**: services `backend` (uvicorn/gunicorn), `proxy` (Caddy/nginx),
  a shared volume for `storage/cache` and `models`.

### A2. Reverse proxy + HTTPS
- **Caddy** (auto-HTTPS via Let's Encrypt) or nginx + certbot.
- Single-domain layout (no CORS): `/` → frontend static, `/api/*` → backend. Then
  the frontend and the API are one origin, no CORS needed.
- SSE (`/api/tts/stream`) through the proxy: disable buffering (`X-Accel-Buffering:
  no` is already returned; for nginx — `proxy_buffering off`).

### A3. Production configuration (code changes)
- Move settings into **environment variables** (some are currently hardcoded):
  - `CORS_ORIGINS` (prod domain instead of localhost),
  - `MAX_TEXT_LENGTH`, `CACHE_MAX_BYTES`, cache path,
  - number of workers, device (keep cpu).
- Replace the hardcoded `http://127.0.0.1:8000` on the frontend with a configurable
  `VITE_BACKEND_URL` (or a relative path for a single domain).

### A4. Process model and concurrency
- Uvicorn/Gunicorn with N workers; **each worker loads the model** (memory ×N). A
  semaphore=1 per process → N concurrent syntheses = N workers.
- Start: 1–2 workers behind the proxy. Growing load → a **task queue** (Celery/RQ +
  Redis) with a worker pool: the API enqueues a task and streams progress via
  SSE/polling (our per-segment progress is already there), synthesis runs in a
  worker.
- Cache shared across workers: one volume (or S3 object storage for horizontal
  scaling). LRU is already there.

### A5. Security and abuse protection
- **Rate limiting** (nginx `limit_req` / Caddy / slowapi), timeouts, request size
  limit (text length is already capped).
- Optional: API key/captcha/per-IP quotas for public access.
- Logs to stdout (already via `logging`), aggregation; no PII stored.

### A6. Observability and CI/CD
- Monitoring via `/api/health`; optional metrics (Prometheus), errors (Sentry).
- **GitHub Actions** (implemented):
  - `.github/workflows/ci.yml` — on every push/PR to main: backend tests (pytest)
    and frontend lint (oxlint) + build (tsc + vite).
  - `.github/workflows/docker-publish.yml` — CD: builds and pushes the backend and
    web images to GHCR (ghcr.io) on release tags `v*` or manual dispatch (with GHA
    layer caching). Deployment on the server is then `docker compose pull && up -d`.

### Part A — stages
- ✅ **A-1. Docker artifacts** (built and verified end-to-end): `backend/Dockerfile`
  (python:3.11-slim + ffmpeg + **build-essential** to build the `pyworld` C
  extension on Linux + deps + parallel_wavegan), `frontend/Dockerfile` (Vite build
  → Caddy) + `frontend/Caddyfile` (static + reverse-proxy `/api`, SSE without
  buffering via `flush_interval -1`), `docker-compose.yml` (single domain, `models`/
  `storage` volumes), `.dockerignore`, `.env.example`. Verified locally:
  `docker compose up -d` → `http://localhost` serves the frontend, `/api/*` is
  proxied to the backend (model loaded, 5 voices), synthesis and SSE progress go
  through Caddy. Models are loaded into the volume by `download_kazakhtts2.py` (or
  by copying from the host).
- ✅ **A-2. Env config**: the backend reads `CORS_ORIGINS`, `MAX_TEXT_LENGTH`,
  `CACHE_MAX_BYTES`, `MODELS_DIR`, `STORAGE_DIR`, `TTS_DEVICE`, `DEFAULT_VOICE`,
  `AUDIO_TARGET_PEAK`, `SEGMENT_SILENCE_SEC`, `MODEL_VERSION` from the environment
  (defaults = local development). Frontend — `VITE_BACKEND_URL` (empty → relative
  paths). Runtime check: local dev works without regressions.
- ▶️ A-3. VPS + domain + `docker compose up` + HTTPS; e2e check (needs a server).
- ✅ **CI/CD** (GitHub Actions): `ci.yml` (backend pytest + frontend lint/build on
  push/PR) and `docker-publish.yml` (build & push images to GHCR on `v*` tags /
  manual dispatch).
- ✅ **A-4. Rate limiting + monitoring**:
  - Rate limiting via slowapi (per client IP): `/api/tts` and `/api/tts/stream`
    limited by `TTS_RATE_LIMIT` (default 10/min), a generous global
    `DEFAULT_RATE_LIMIT` (240/min) for the rest; `429` on excess. The real client
    IP comes from `X-Forwarded-For` (uvicorn `--forwarded-allow-ips=*`, safe as the
    backend is internal-only). In-memory store — fine for one uvicorn worker; use
    Redis for multiple.
  - Prometheus metrics at `/metrics` (internal — not proxied by Caddy under
    `/api`, so not publicly exposed); scrape from the internal network.
  - Docker `HEALTHCHECK` on the backend (`/api/health`); `web` waits for
    `service_healthy`. Persistent cache/models volumes already in compose.
  - Verified: 10×200 then 429; `/metrics` served internally but not via Caddy;
    backend reports `healthy`. Tests: 19 passed (added rate-limit/metrics test).
- A-5. (as load grows) a Celery/RQ + Redis queue (Redis also enables shared
  rate-limit state across workers).

---

## Part B. Mobile app (Google Play)

### B0. Architectural decision
A thin client to the server API (synthesis on the server from Part A). On-device is
only a distant prospect (see B5).

### B1. Technology choice — **Capacitor selected**
- **Capacitor (selected)** — wraps the current React app in a native shell, reuses
  all frontend code, adds native features: audio, file download/share, splash/icon,
  offline handling, push. The best balance of effort and quality.
- **TWA (Bubblewrap)** — the fastest: publishes the hosted PWA as an Android app.
  Needs an HTTPS site, a PWA manifest/service worker, Digital Asset Links. Minimal
  code, UX = web.
- **React Native / native Kotlin** — overkill for a thin client.

### B2. Frontend changes for mobile
- Configurable API base URL (prod server).
- mp3 download → native (Capacitor Filesystem/Share) instead of `<a download>`.
- Audio: the HTML5 `<audio>` works in the webview; optionally a native player/media
  session with background playback.
- Verify responsive layout on a phone (currently fairly responsive), offline and
  error states, retries.
- Icon/splash in the Kazakh style (reuse the sun + ornament).

### B3. Google Play requirements
- A Play Console account ($25 one-time), Play App Signing, package id, versions.
- A **privacy policy** (mandatory) — disclose that text is sent to the server for
  synthesis; the **Data Safety** form.
- Content rating questionnaire; target API level; the listing (512 icon, feature
  graphic, screenshots, descriptions in KZ/RU/EN).

### B4. Build and release (for Capacitor)
`npm run build` → `npx cap sync android` → Android Studio → a signed **AAB** →
Play Console: internal testing → closed testing → production.

### B5. On-device in the future (post-MVP, optional)
If privacy becomes a hard requirement — convert the acoustic model and the vocoder
to **ONNX/TFLite**, bundle one voice (~120 MB), inference on the device. This is a
separate large R&D effort (matches the post-MVP ONNX item of the spec).

### Part B — stages
- B-1. Set up a configurable API URL + mobile layout/states.
- B-2. Wrap in Capacitor, add native audio/download/icon.
- B-3. Privacy policy + Data Safety + listing.
- B-4. Internal testing → closed → production.

---

## Overall order (recommendation)
1. **Server first** (Part A) — the mobile client needs a working public API.
2. Close the critical items: **model license**, privacy, limits.
3. Then the **mobile client** (Part B) on top of the ready API.
4. As load grows — a task queue; if privacy is required — on-device R&D.

## Remaining decisions
- Platform and budget; is there a domain/HTTPS?
- Expected number of concurrent users? (drives workers/queue.)

(Answered: product is commercial; mobile approach is Capacitor; hosting — own VPS
recommended.)
