# Backend: FastAPI + KazakhTTS2 (CPU). Models and storage live on a volume,
# not in the image.
FROM python:3.11-slim

# ffmpeg — for wav -> mp3 conversion (subprocess). build-essential — a compiler
# to build the pyworld C extension (no prebuilt cp311 wheel on Linux).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies as a separate layer (cache). torch/torchaudio use the CPU build via
# --extra-index-url in requirements.txt. parallel_wavegan is installed separately
# without build isolation (its setup.py does `import pip`).
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir wheel \
    && pip install --no-cache-dir --no-build-isolation parallel_wavegan==0.6.1

COPY app ./app
COPY scripts ./scripts

# Paths on a volume; CPU inference; UTF-8 for logs.
ENV MODELS_DIR=/models \
    STORAGE_DIR=/storage \
    TTS_DEVICE=cpu \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
