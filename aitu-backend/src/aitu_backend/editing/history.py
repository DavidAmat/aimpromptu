"""Snapshots of ``events.json`` (and the audio) taken before an accepted splice.

The live piece is still one ``events.json`` per audio uuid — that is the current
storage, and this module does not change it. Accepting an edit copies the
previous musical state into ``history/vN/`` and advances a counter beside the
file. Playground ``vN_f<frameMs>`` folders are left alone.
"""

from __future__ import annotations

import json
import shutil

from aitu_backend.audio import store
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline


def current_version(audio_uuid: str) -> int:
    path = paths.music_version_path(audio_uuid)
    if not path.is_file():
        return 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return int(payload.get("version", 1))
    except (ValueError, OSError, TypeError):
        return 1


def _write_version(audio_uuid: str, version: int) -> None:
    path = paths.music_version_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": version}) + "\n", encoding="utf-8")


def snapshot_current(audio_uuid: str) -> int:
    """Copy the live piece into ``history/vN/`` and return the new version number."""
    version = current_version(audio_uuid)
    dest = paths.history_version_dir(audio_uuid, version)
    dest.mkdir(parents=True, exist_ok=True)
    events = pipeline.events_path(audio_uuid)
    if events.is_file():
        shutil.copy2(events, dest / "events.json")
    rhythm = pipeline.rhythm_path(audio_uuid)
    if rhythm.is_file():
        shutil.copy2(rhythm, dest / "rhythm.json")
    entry = store.get(audio_uuid)
    if entry.has_normalized():
        shutil.copy2(entry.normalized_path, dest / "normalized.wav")
    original = entry.original_path
    if original is not None and original.is_file():
        shutil.copy2(original, dest / original.name)
    nxt = version + 1
    _write_version(audio_uuid, nxt)
    return nxt


def load_mismatches(audio_uuid: str) -> list[dict]:
    path = paths.audio_mismatches_path(audio_uuid)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return list(payload.get("windows", []))
    except (ValueError, OSError):
        return []


def add_mismatch(audio_uuid: str, start_seconds: float, end_seconds: float) -> None:
    windows = load_mismatches(audio_uuid)
    windows.append({"startSeconds": start_seconds, "endSeconds": end_seconds})
    path = paths.audio_mismatches_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"windows": windows}, indent=2) + "\n", encoding="utf-8")
