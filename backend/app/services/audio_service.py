"""Audio helpers: ffmpeg check, WAV duration, conversion to mp3.

Conversion is done by calling ffmpeg directly via subprocess (pydub is NOT used —
the library is barely maintained, a direct call is more reliable).
"""

import logging
import shutil
import subprocess

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def normalize_wav_peak(wav_path: str, target_peak: float) -> None:
    """Peak-normalize the WAV loudness in place.

    Scales the signal so the maximum amplitude equals target_peak (< 1.0 — no
    clipping). Apply it to the FINAL (already concatenated) WAV, not to individual
    segments, otherwise there would be loudness jumps between sentences.
    """
    data, samplerate = sf.read(wav_path)
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if peak > 0:
        data = (data * (target_peak / peak)).astype(np.float32)
        sf.write(wav_path, data, samplerate)


def is_ffmpeg_available() -> bool:
    """Check that ffmpeg is available on PATH. Called at application startup."""

    return shutil.which("ffmpeg") is not None


def get_wav_duration_sec(wav_path: str) -> float:
    """Return the WAV file duration in seconds."""

    info = sf.info(wav_path)
    return info.frames / info.samplerate


def concat_segments(
    wav_paths: list[str],
    out_path: str,
    silence_sec: float,
) -> list[tuple[float, float]]:
    """Concatenate WAV segments into one file, inserting a short silence between.

    Returns the (start_sec, end_sec) timing of each segment in the resulting audio
    (the silence between sentences falls into the gaps, not into the segments).
    """
    if not wav_paths:
        raise ValueError("No segments to concatenate")

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
                f"Segments have different sample rates: {sr} != {samplerate}"
            )

        start = cursor
        duration = len(data) / samplerate
        end = start + duration
        timings.append((round(start, 3), round(end, 3)))

        chunks.append(data.astype(np.float32))
        cursor = end

        # Silence between sentences (not after the last one).
        if i < len(wav_paths) - 1 and silence is not None and len(silence):
            chunks.append(silence)
            cursor += silence_sec

    full = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    sf.write(out_path, full, samplerate)
    return timings


def convert_wav_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "128k") -> None:
    """Convert WAV to MP3 by calling ffmpeg directly.

    Raises RuntimeError with a clear message if ffmpeg exits with an error.
    """

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",  # overwrite the destination file if it exists
            "-i", wav_path,
            "-b:a", bitrate,
            mp3_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(
            "ffmpeg error converting %s -> %s: %s", wav_path, mp3_path, result.stderr
        )
        raise RuntimeError(f"Failed to convert WAV to MP3: {result.stderr}")
