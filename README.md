# Kazakh TTS App

Локальное веб-приложение для синтеза речи из казахского текста (кириллица).
Работает полностью локально, без облачных API, на CPU.

- **Backend**: Python + FastAPI, движок **KazakhTTS2** (ESPnet2 Tacotron2 +
  вокодер ParallelWaveGAN), инференс на CPU.
- **Frontend**: React + Vite + TypeScript.
- **Аудио**: рабочий формат — wav, скачивание — mp3 (конвертация через ffmpeg).

Возможности: ввод казахского текста, выбор из 5 голосов, синтез (с прогрессом),
воспроизведение (Старт/Пауза/Стоп), подсветка текущего предложения синхронно со
звуком, выбор диапазона предложений для озвучки, скачивание mp3, кэширование.

## Требования

- **Python 3.10–3.11**
- **Node.js 18+** и npm
- **ffmpeg** в PATH (конвертация wav → mp3)
- ~1.5 ГБ места под модели (5 голосов), ~600 МБ трафика на их скачивание

## Установка и запуск

### 1. Backend

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
# parallel_wavegan ставится отдельно (его setup.py ломается в изолированной сборке):
pip install --no-build-isolation parallel_wavegan==0.6.1
# Скачать модели KazakhTTS2 (5 голосов) в backend/models/kazakhtts2/:
python scripts/download_kazakhtts2.py
# Запуск:
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

Backend поднимется на `http://127.0.0.1:8000` (Swagger: `/docs`). Модель грузится
один раз при старте. Подробности — в [backend/README.md](backend/README.md).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend откроется на `http://localhost:5173` и будет обращаться к backend на
`http://127.0.0.1:8000` (CORS настроен).

## Установка ffmpeg

- **Windows**: `winget install Gyan.FFmpeg` (или скачать сборку и добавить в PATH)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

Backend проверяет наличие ffmpeg при старте и пишет ошибку в лог, если его нет.

## Модели KazakhTTS2

Веса не хранятся в репозитории. Их скачивает `backend/scripts/download_kazakhtts2.py`
с серверов ISSAI (репозиторий [IS2AI/Kazakh_TTS](https://github.com/IS2AI/Kazakh_TTS))
и раскладывает в `backend/models/kazakhtts2/<voice>/`. Голоса: `female1`, `female2`,
`female3`, `male1`, `male2` (по умолчанию `female1`).

## Архитектура (ключевые правила)

- **Только CPU**: torch стоит CPU-сборкой; движок явно использует `device="cpu"`.
- **Неблокирующий инференс**: синтез идёт через thread pool с семафором = 1;
  `/api/health` отвечает мгновенно даже во время генерации.
- **Единая функция разбиения на предложения** — только на backend
  (`text_normalizer.split_sentences`), обслуживает и `/api/split`, и `/api/tts`,
  поэтому границы предложений и char-смещения всегда согласованы с подсветкой.
- **mp3 — единственный формат скачивания в MVP**; внутренний формат конвейера —
  wav; конвертация в mp3 — последний шаг через ffmpeg.
- **Кэш** готовых аудио по хэшу (текст+голос+движок+формат+версия+диапазон) с
  LRU-очисткой; тайминги сегментов — в json рядом с mp3.

## API (кратко)

`GET /api/health` · `GET /api/voices` · `POST /api/split` ·
`POST /api/tts` · `POST /api/tts/stream` (SSE с прогрессом) ·
`GET /api/audio/{filename}`. Подробно — в [backend/README.md](backend/README.md).

## Замечания

- **Качество**: это открытые чекпоинты KazakhTTS2 2022 г. — тембр/уровень голосов
  различаются; громкость выравнивается пиковой нормализацией. Улучшение качества
  (другие модели, дереверберация, ONNX) — после MVP.
- **CPU-инференс медленный** (секунды на предложение) — это нормально; UI
  показывает прогресс.
- **Числа и даты** лучше писать словами (подсказка есть в UI).
- **План Б (Windows)**: если сборка ESPnet/вокодера не удаётся на Windows —
  запускать backend в WSL2 (frontend остаётся на Windows, обращение по localhost).
  На эталонной машине нативная установка на Windows прошла успешно.

## Документы

- [docs/PLAN.md](docs/PLAN.md) — план разработки и статусы этапов
- [backend/README.md](backend/README.md) — детали backend
- `Kazakh_TTS_App_Specification.md` — исходное техническое задание
