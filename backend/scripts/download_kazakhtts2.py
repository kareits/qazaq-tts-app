"""Download and lay out KazakhTTS2 checkpoints (5 voices).

Model weights are not committed to git — this script downloads them from the
ISSAI servers and lays them out in backend/models/kazakhtts2/<voice>/ in the
structure KazakhTTS2Engine expects. Idempotent: already-installed voices are
skipped (use --force to re-download).

Usage (from the backend folder, ideally with .venv activated):
    python scripts/download_kazakhtts2.py            # all voices
    python scripts/download_kazakhtts2.py female1 male1
    python scripts/download_kazakhtts2.py --force    # re-download

Depends only on the standard library (urllib, zipfile) — can be run before
installing requirements.
"""

import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "https://issai.nu.edu.kz/wp-content/uploads/2022/03"

VOICES = ["female1", "female2", "female3", "male1", "male2"]

# Models root: backend/models/kazakhtts2 (the script lives in backend/scripts).
MODELS_ROOT = Path(__file__).resolve().parent.parent / "models" / "kazakhtts2"


def _tts_url(voice: str) -> str:
    return f"{BASE_URL}/kaztts_{voice}_tacotron2_train.loss.ave.zip"


def _vocoder_url(voice: str) -> str:
    return f"{BASE_URL}/parallelwavegan_{voice}_checkpoint.zip"


def _download(url: str, dst: Path) -> None:
    print(f"    downloading {url}")
    with urllib.request.urlopen(url) as resp, open(dst, "wb") as out:
        shutil.copyfileobj(resp, out)
    print(f"    saved {dst.stat().st_size / 1024 / 1024:.1f} MB")


def _find(root: Path, name: str) -> Path | None:
    return next(iter(sorted(root.rglob(name))), None)


def _find_glob(root: Path, pattern: str) -> Path | None:
    return next(iter(sorted(root.rglob(pattern))), None)


def _is_installed(voice: str) -> bool:
    """A voice is considered installed when all key files are in place."""
    d = MODELS_ROOT / voice
    exp = d / "exp" / "tts_train_raw_char"
    stats = d / "exp" / "tts_stats_raw_char" / "train" / "feats_stats.npz"
    return (
        (exp / "config.yaml").is_file()
        and stats.is_file()
        and _find_glob(exp, "*.pth") is not None
        and _find_glob(d / "vocoder", "*.pkl") is not None
    )


def install_voice(voice: str, force: bool) -> None:
    if not force and _is_installed(voice):
        print(f"[{voice}] already installed — skipping")
        return

    print(f"[{voice}] installing…")
    dst = MODELS_ROOT / voice
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tts_zip = tmp_path / "tts.zip"
        voc_zip = tmp_path / "voc.zip"
        _download(_tts_url(voice), tts_zip)
        _download(_vocoder_url(voice), voc_zip)

        ex_tts = tmp_path / "tts"
        ex_voc = tmp_path / "voc"
        with zipfile.ZipFile(tts_zip) as z:
            z.extractall(ex_tts)
        with zipfile.ZipFile(voc_zip) as z:
            z.extractall(ex_voc)

        config = _find(ex_tts, "config.yaml")
        pth = _find_glob(ex_tts, "*.pth")
        stats = _find(ex_tts, "feats_stats.npz")
        meta = _find(ex_tts, "meta.yaml")
        vpkl = _find_glob(ex_voc, "*.pkl")
        vyml = _find(ex_voc, "config.yml")
        if not (config and pth and stats and vpkl and vyml):
            raise RuntimeError(
                f"[{voice}] not all required files were found in the archives "
                f"(config={config}, pth={pth}, stats={stats}, pkl={vpkl}, yml={vyml})"
            )

        # Lay out into the structure expected by the engine.
        (dst / "exp" / "tts_train_raw_char").mkdir(parents=True, exist_ok=True)
        (dst / "exp" / "tts_stats_raw_char" / "train").mkdir(parents=True, exist_ok=True)
        (dst / "vocoder").mkdir(parents=True, exist_ok=True)

        shutil.copy2(config, dst / "exp" / "tts_train_raw_char" / "config.yaml")
        shutil.copy2(pth, dst / "exp" / "tts_train_raw_char" / pth.name)
        shutil.copy2(stats, dst / "exp" / "tts_stats_raw_char" / "train" / "feats_stats.npz")
        if meta:
            shutil.copy2(meta, dst / "meta.yaml")
        shutil.copy2(vpkl, dst / "vocoder" / vpkl.name)
        shutil.copy2(vyml, dst / "vocoder" / "config.yml")

    print(f"[{voice}] done → {dst}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download KazakhTTS2 models")
    parser.add_argument(
        "voices",
        nargs="*",
        metavar="VOICE",
        help=f"which voices to download (default: all: {', '.join(VOICES)})",
    )
    parser.add_argument(
        "--force", action="store_true", help="re-download even installed voices"
    )
    args = parser.parse_args()

    voices = args.voices or VOICES
    unknown = [v for v in voices if v not in VOICES]
    if unknown:
        parser.error(
            f"unknown voices: {', '.join(unknown)}. Available: {', '.join(VOICES)}"
        )
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Models directory: {MODELS_ROOT}\n")

    for voice in voices:
        try:
            install_voice(voice, args.force)
        except Exception as exc:  # noqa: BLE001
            print(f"[{voice}] ERROR: {exc}", file=sys.stderr)
            return 1
    print("\nDone. Voices:", ", ".join(voices))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
