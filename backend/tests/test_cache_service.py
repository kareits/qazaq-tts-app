"""Tests for the cache key and LRU eviction."""

import os
import time

from app.services import cache_service


def test_make_key_is_deterministic_and_input_sensitive():
    base = cache_service.make_key("текст", "female3", "kazakhtts2", "mp3", "full")
    assert base == cache_service.make_key(
        "текст", "female3", "kazakhtts2", "mp3", "full"
    )
    # A change in any component changes the key.
    assert base != cache_service.make_key("текст2", "female3", "kazakhtts2", "mp3", "full")
    assert base != cache_service.make_key("текст", "female2", "kazakhtts2", "mp3", "full")
    assert base != cache_service.make_key("текст", "female3", "mms", "mp3", "full")
    assert base != cache_service.make_key("текст", "female3", "kazakhtts2", "wav", "full")
    assert base != cache_service.make_key("текст", "female3", "kazakhtts2", "mp3", "0-1")


def test_put_get_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path)
    key, fmt = "abc123", "mp3"
    # get() requires both the audio file and the json to exist.
    (tmp_path / f"{key}.{fmt}").write_bytes(b"fake mp3 bytes")
    meta = {"audio_url": f"/api/audio/{key}.mp3", "duration_sec": 1.2, "segments": []}
    cache_service.put(key, fmt, meta)
    assert cache_service.get(key, fmt) == meta


def test_get_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path)
    assert cache_service.get("missing", "mp3") is None
    # audio present but json missing → still None
    (tmp_path / "half.mp3").write_bytes(b"x")
    assert cache_service.get("half", "mp3") is None


def test_enforce_limit_evicts_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_service, "CACHE_MAX_BYTES", 1000)

    # Three pairs of ~502 bytes each (total ~1506 > 1000) with increasing mtime.
    for i, name in enumerate(["old", "mid", "new"]):
        (tmp_path / f"{name}.mp3").write_bytes(b"x" * 500)
        (tmp_path / f"{name}.json").write_text("{}")
        stamp = time.time() + i
        os.utime(tmp_path / f"{name}.mp3", (stamp, stamp))
        os.utime(tmp_path / f"{name}.json", (stamp, stamp))

    cache_service.enforce_limit()

    remaining = {p.stem for p in tmp_path.glob("*.mp3")}
    assert "new" in remaining  # newest kept
    assert "old" not in remaining  # oldest evicted first
    total = sum(p.stat().st_size for p in tmp_path.glob("*"))
    assert total <= 1000
