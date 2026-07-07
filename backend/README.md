# Kazakh TTS Backend

Backend синтеза казахской речи на CPU. Движок — **KazakhTTS2** (ESPnet2
Tacotron2 + вокодер ParallelWaveGAN), инференс на CPU.

## Установка (Windows, PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
# parallel_wavegan ставится отдельно: его setup.py делает `import pip`, что
# ломается в изолированной сборке современного pip.
pip install --no-build-isolation parallel_wavegan==0.6.1
```

macOS / Linux — аналогично (`python3 -m venv .venv`, `source .venv/bin/activate`).

torch/torchaudio ставятся в CPU-сборке через дополнительный индекс PyTorch,
он уже прописан в `requirements.txt` (`--extra-index-url`).

## Модели (checkpoint'ы)

Веса не коммитятся (`.gitignore`). Скачиваются скриптом (идемпотентно,
только stdlib — можно запускать даже до `pip install`):

```powershell
python scripts/download_kazakhtts2.py            # все 5 голосов
python scripts/download_kazakhtts2.py female1    # только выбранные
python scripts/download_kazakhtts2.py --force    # перекачать заново
```

Скрипт качает с серверов ISSAI и раскладывает в
`backend/models/kazakhtts2/<voice>/`:

```
<voice>/
  exp/tts_train_raw_char/config.yaml            # конфиг ESPnet2 TTS
  exp/tts_train_raw_char/*.pth                  # веса Tacotron2
  exp/tts_stats_raw_char/train/feats_stats.npz  # статистика нормализации
  vocoder/*.pkl                                 # чекпоинт ParallelWaveGAN
  vocoder/config.yml
```

Голоса: `female1`, `female2`, `female3`, `male1`, `male2` (по умолчанию
`female1`). Источник: репозиторий IS2AI/Kazakh_TTS, файлы на
`issai.nu.edu.kz/wp-content/uploads/2022/03/` (`kaztts_<voice>_tacotron2_*.zip`
и `parallelwavegan_<voice>_checkpoint.zip`).

## Запуск

```powershell
uvicorn app.main:app --reload
```

Backend поднимается на `http://127.0.0.1:8000`. Модель грузится один раз при
старте (lifespan). Если checkpoint'ов нет — приложение стартует, но
`/api/health` покажет `model_loaded: false`, а `/api/tts` вернёт 503.

## API

- `GET /api/health` — состояние (status, device, model_loaded, active_engine,
  max_text_length). Отвечает мгновенно даже во время синтеза.
- `GET /api/voices` — список голосов.
- `POST /api/split` — `{text}` → предложения с char-смещениями
  (`{index, text, char_start, char_end}`) + `warning`, если текст не похож на
  казахскую кириллицу. Та же функция разбиения, что и в `/api/tts`.
- `POST /api/tts` — синтез: `{text, voice, format, engine, sentence_range?}`
  → mp3 + посегментные тайминги. Инференс неблокирующий (thread pool +
  семафор=1). Результат кэшируется (повторный запрос — `cached: true`).
- `GET /api/audio/{filename}` — отдача готового mp3 (attachment).

## Системные зависимости

- **ffmpeg** должен быть установлен и доступен в PATH — проверяется при старте
  (lifespan), конвертация wav → mp3.
- Инференс на CPU медленный (секунды на предложение) — это нормально для MVP.

## Технические заметки по инференсу

- Вокодер грузится ОТДЕЛЬНО (не через `vocoder_file` в `Text2Speech`), в него
  подаётся нормализованный мел `out["feat_gen"]` — именно в этом пространстве
  обучался вокодер KazakhTTS2 (денормализованный даёт почти тишину).
- `stats_file` в `config.yaml` относительный — при загрузке генерируется
  рантайм-конфиг с абсолютным путём (без смены cwd процесса).
- `parallel_wavegan` использует `scipy.signal.kaiser`, перенесённую в
  `scipy.signal.windows` в scipy≥1.13 — движок ставит совместимый shim.
- Громкость голосов сильно разная (female1 тихий, female2 громкий), поэтому
  финальный WAV нормализуется по пику к `AUDIO_TARGET_PEAK` (config) в
  `audio_service.normalize_wav_peak` перед конвертацией в mp3.

## План Б (если ESPnet не собирается на Windows)

На данной машine нативная установка на Windows (Python 3.11) прошла успешно.
Если на другой машине сборка ESPnet/вокодера не удаётся — запускать backend в
WSL2 (frontend остаётся на Windows и обращается к backend по localhost).

## Статус реализации

- Этап 1 (каркас): `/api/health`.
- Этап 2 (audio pipeline): `audio_service.py`, `/api/audio/{filename}`.
- Этап 4 (KazakhTTS2): движок (`app/tts/`), `tts_service.py` (неблокирующий
  синтез), `/api/voices`, `/api/tts`, нормализация громкости.
- Этап 5 (нормализация, сегменты, кэш): `text_normalizer.py` (единая функция
  разбиения на предложения), `/api/split`, посегментный синтез со склейкой и
  таймингами, `sentence_range`, `cache_service.py` (кэш + json тайминги +
  LRU-очистка). Временный `/api/dev/test-audio` удалён.
