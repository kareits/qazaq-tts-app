# Backend: FastAPI + KazakhTTS2 (CPU). Модели и storage — на volume, не в образе.
FROM python:3.11-slim

# ffmpeg — для конвертации wav -> mp3 (subprocess). build-essential — компилятор
# для сборки C-расширения pyworld (на Linux нет готового wheel для cp311).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости отдельным слоем (кэш). torch/torchaudio — CPU-сборка через
# --extra-index-url в requirements.txt. parallel_wavegan ставится отдельно без
# изоляции сборки (его setup.py делает `import pip`).
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir wheel \
    && pip install --no-cache-dir --no-build-isolation parallel_wavegan==0.6.1

COPY app ./app
COPY scripts ./scripts

# Пути на volume; CPU-инференс; UTF-8 для русских логов.
ENV MODELS_DIR=/models \
    STORAGE_DIR=/storage \
    TTS_DEVICE=cpu \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
