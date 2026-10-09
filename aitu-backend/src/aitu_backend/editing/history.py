"""Snapshots of a part taken before an accepted splice or a new transcription replaced it.

Accepting an edit copies the previous musical state of the part into
``.database/history/<projectId>/parts/<partId>/vN/`` and advances a counter in the part's folder
(``music-version.json``). A snapshot holds ``notes.pmn``, ``sheet.json`` and ``timeline.json``. The
audio is not copied: the timeline names the stored files (``.database/audio/``), which never
change, and ``audio_refs`` counts the snapshot's files as used by the project, so they are never
deleted under it (implementation 02, plan section 8.5).
"""

from __future__ import annotations

import json
import shutil

from aitu_backend.audio import sources
from aitu_backend.storage import bundle, locate, paths
from aitu_backend.storage.bundle import PartSource
from aitu_backend.transcription import pipeline, split_cache

#: The part's entry of ``project.json`` (where its audio came from, the names of its files), kept
#: with a snapshot so a restore gives the files their names back (Phase 8).
SOURCE_FILE = "source.json"


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
    """Copy the live part (notes, sheet, audio timeline) into ``vN/``; return the new version."""
    version = current_version(audio_uuid)
    dest = paths.history_version_dir(audio_uuid, version)
    dest.mkdir(parents=True, exist_ok=True)
    for source in (
        pipeline.events_path(audio_uuid),
        pipeline.rhythm_path(audio_uuid),
        paths.part_timeline_path(audio_uuid),
    ):
        if source.is_file():
            shutil.copy2(source, dest / source.name)
    project_id = locate.part(audio_uuid).project_id
    part = bundle.read_project(project_id).part(audio_uuid)
    (dest / SOURCE_FILE).write_text(
        part.source.model_dump_json(by_alias=True, exclude_none=True) + "\n", encoding="utf-8"
    )
    bundle.sync_audio_refs(project_id)
    nxt = version + 1
    _write_version(audio_uuid, nxt)
    return nxt


def snapshot_notes(audio_uuid: str) -> int:
    """Copy ``notes.pmn`` and ``sheet.json`` into ``vN/`` and return the new version.

    Called before a new transcription replaces them (implementation 08, plan section 8.3): before
    this, a new transcription deleted the saved sheet with no copy. The audio is not copied, unlike
    :func:`snapshot_current`, because a transcription does not change it. The version counter is
    the same, so the two kinds of snapshot never share a folder.
    """
    version = current_version(audio_uuid)
    dest = paths.history_version_dir(audio_uuid, version)
    dest.mkdir(parents=True, exist_ok=True)
    for source in (pipeline.events_path(audio_uuid), pipeline.rhythm_path(audio_uuid)):
        if source.is_file():
            shutil.copy2(source, dest / source.name)
    (dest / "snapshot.json").write_text(
        json.dumps({"reason": "a new transcription replaced these notes"}) + "\n",
        encoding="utf-8",
    )
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


class NoSuchVersion(LookupError):
    """No snapshot of that number, or one that cannot be put back whole."""


def restore(audio_uuid: str, version: int) -> int:
    """Put snapshot ``version`` of the part back: its notes, its sheet, its audio timeline and the
    names of its files. The current state is kept first as the next snapshot, and its number is
    returned, so the same call takes the restore back (an undo, then a redo, Phase 8).

    Only a snapshot of :func:`snapshot_current` (it has a timeline) can be put back whole. A file
    the snapshot did not have (no sheet saved then) is deleted. The caller holds
    :func:`pipeline.piece_lock`.
    """
    folder = paths.history_version_dir(audio_uuid, version)
    if not (folder / "timeline.json").is_file():
        raise NoSuchVersion(f"This part has no earlier state {version} to go back to.")
    kept = current_version(audio_uuid)
    snapshot_current(audio_uuid)
    targets = (
        pipeline.events_path(audio_uuid),
        pipeline.rhythm_path(audio_uuid),
        paths.part_timeline_path(audio_uuid),
    )
    for target in targets:
        saved = folder / target.name
        if saved.is_file():
            # A new modification time: the hand split is cached by the notes file's time.
            shutil.copyfile(saved, target)
        else:
            target.unlink(missing_ok=True)
    project_id = locate.part(audio_uuid).project_id
    source = folder / SOURCE_FILE
    if source.is_file():
        with bundle.project_lock(project_id):
            project = bundle.read_project(project_id)
            project.part(audio_uuid).source = PartSource.model_validate_json(
                source.read_text(encoding="utf-8")
            )
            bundle.write_project(project)
    forget_derived(audio_uuid)
    bundle.sync_audio_refs(project_id)
    bundle.step_changed(audio_uuid)
    return kept


def forget_derived(audio_uuid: str) -> None:
    """The derived files of the part's audio and notes, which no longer match: written again on
    the next request. Each file's own 16 kHz copy is kept; it does not change."""
    cache = paths.part_cache_dir(audio_uuid)
    for stale in [*cache.glob("piece-r*.*"), cache / "waveform.json", cache / "normalized.wav"]:
        stale.unlink(missing_ok=True)
    sources.clear(audio_uuid)
    split_cache.forget(audio_uuid)
