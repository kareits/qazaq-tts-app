"""Работа с аудио: проверка ffmpeg, замер длительности WAV, конвертация в mp3.

Конвертация выполняется прямым вызовом ffmpeg через subprocess (pydub НЕ
используется — библиотека почти не поддерживается, прямой вызов надёжнее).
"""

import logging
import shutil
import subprocess

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def normalize_wav_peak(wav_path: str, target_peak: float) -> None:
    """Пиковая нормализация громкости WAV на месте.

    Масштабирует сигнал так, чтобы максимальная амплитуда стала равна
    target_peak (< 1.0 — без клиппинга). Применять к ФИНАЛЬНОМУ (уже склеенному)
    WAV, а не к отдельным сегментам, иначе между предложениями будут скачки
    громкости.
    """
    data, samplerate = sf.read(wav_path)
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if peak > 0:
        data = (data * (target_peak / peak)).astype(np.float32)
        sf.write(wav_path, data, samplerate)


def is_ffmpeg_available() -> bool:
    """Проверяет, что ffmpeg доступен в PATH. Вызывается при старте приложения."""

    return shutil.which("ffmpeg") is not None


def get_wav_duration_sec(wav_path: str) -> float:
    """Возвращает длительность WAV-файла в секундах."""

    info = sf.info(wav_path)
    return info.frames / info.samplerate


def concat_segments(
    wav_paths: list[str],
    out_path: str,
    silence_sec: float,
) -> list[tuple[float, float]]:
    """Склеить WAV-сегменты в один файл, вставив короткую тишину между ними.

    Возвращает тайминги (start_sec, end_sec) каждого сегмента в итоговом аудио
    (тишина между предложениями входит в промежутки, но не в сами сегменты).
    """
    if not wav_paths:
        raise ValueError("Нет сегментов для склейки")

    chunks: list[np.ndarray] = []
    timings: list[tuple[float, float]] = []
    samplerate: int | None = None
    silence: np.ndarray | None = None
    cursor = 0.0

    for i, path in enumerate(wav_paths):
        data, sr = sf.read(path)
        if samplerate is None:
            samplerate = sr
            silence = np.zeros(int(sr * silence_sec), dtype=np.float32)
        elif sr != samplerate:
            raise ValueError(
                f"Разная частота дискретизации сегментов: {sr} != {samplerate}"
            )

        start = cursor
        duration = len(data) / samplerate
        end = start + duration
        timings.append((round(start, 3), round(end, 3)))

        chunks.append(data.astype(np.float32))
        cursor = end

        # Тишина между предложениями (не после последнего).
        if i < len(wav_paths) - 1 and silence is not None and len(silence):
            chunks.append(silence)
            cursor += silence_sec

    full = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    sf.write(out_path, full, samplerate)
    return timings


def convert_wav_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "128k") -> None:
    """Конвертирует WAV в MP3 через прямой вызов ffmpeg.

    Бросает RuntimeError с понятным сообщением, если ffmpeg завершился с ошибкой.
    """

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",  # перезаписать файл назначения, если существует
            "-i", wav_path,
            "-b:a", bitrate,
            mp3_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Ошибка ffmpeg при конвертации %s -> %s: %s", wav_path, mp3_path, result.stderr)
        raise RuntimeError(f"Не удалось сконвертировать WAV в MP3: {result.stderr}")
