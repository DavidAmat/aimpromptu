#!/usr/bin/env python
"""Move the pieces of ``aitu-backend/data/`` into ``.database/`` (implementation 02, plan section 8.9).

Run once, on a copy first::

    cd aitu-backend
    AITU_DATABASE_DIR=/tmp/aitu-trial uv run --no-sync python ../scripts/migrate/to_database.py \\
        --report /tmp/aitu-trial-report.json
    uv run --no-sync python ../scripts/migrate/to_database.py --report ../migration-report.json

What it does, in order:

1. Opens ``.database/`` (``AITU_DATABASE_DIR``): the tables, the folders, the master user (from
   ``AITU_MASTER_USERNAME``).
2. For each ``data/audio/<uuid>/``: a project of one part whose id is the uuid (P-6). The audio
   file goes to the audio store by its hash, ``events.json`` becomes ``notes.pmn`` (checked note by
   note against the old file), ``rhythm.json`` becomes ``sheet.json``, the cuts become the
   timeline, ``normalized.wav``, ``waveform.json`` and the joined audio go to the cache, and
   ``history/vN/`` goes to ``.database/history/`` with a timeline instead of a copy of the audio.
3. A piece of the seed list (``scripts/seed/youtube-library/``) goes to the master user's Private
   Library, under a private song and a private artist, version name "original". Every other piece
   goes to the master user's Personal Vault.
4. A piece with a video: the video folder goes to ``tmp/<masterId>/<uuid>/video/``.
5. ``data/frame-examples/*.json`` goes to ``lab/frame-examples/``.
6. A report: counts, sizes, and every piece it could not move, with the reason.

The plan says "each piece with notes"; the two pieces with audio and no notes are moved too (one
has a calibrated video), so nothing of the old store is left behind.

**Safe to run twice**: a piece whose project exists is skipped, and so is an example already in
Lab. **It never writes into** ``aitu-backend/data/``, which the user deletes after checking the app.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "aitu-backend" / "src"))

from sqlalchemy import select  # noqa: E402

from aitu_backend.audio.frames import FRAME_MS, frame_count  # noqa: E402
from aitu_backend.audio import formats  # noqa: E402
from aitu_backend.db.database import engine, session  # noqa: E402
from aitu_backend.db.models import (  # noqa: E402
    Artist,
    ArtistName,
    PrivateVersion,
    Song,
    SongArtist,
)
from aitu_backend.db.tools import refresh_step  # noqa: E402
from aitu_backend.db.users import ensure_master_user  # noqa: E402
from aitu_backend.pmn import events_file  # noqa: E402
from aitu_backend.schemas.metadata import AudioMetadata  # noqa: E402
from aitu_backend.storage import audio_files, bundle, locate, paths  # noqa: E402
from aitu_backend.storage.bundle import AudioEntry, PartSource, Timeline  # noqa: E402

SEED_DIR = REPO / "scripts" / "seed" / "youtube-library"
VERSION_NAME = "original"
#: Derived files worth keeping: making them again costs ffmpeg time on the first open.
CACHE_FILES = ("normalized.wav", "waveform.json")
PART_FILES = ("music-version.json", "audio-mismatches.json", "needs-rederivation.json")


# ----------------------------------------------------------------------- the seed


def seed_songs(seed_dir: Path = SEED_DIR) -> dict[str, tuple[str, str | None]]:
    """``uuid -> (title, artist)`` for every piece of the seed list. ``artist`` may be ``None``:
    the handwritten list names no artist on some lines."""
    state_path, library_path = seed_dir / "seed-state.json", seed_dir / "library.json"
    if not state_path.is_file() or not library_path.is_file():
        return {}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    library = json.loads(library_path.read_text(encoding="utf-8"))
    by_url = {piece["url"]: piece for piece in library.get("pieces", [])}
    songs: dict[str, tuple[str, str | None]] = {}
    for url, download in state.get("downloads", {}).items():
        piece = by_url.get(url)
        if download.get("uuid") and piece:
            songs[download["uuid"]] = (piece["title"], piece.get("artist"))
    return songs


def _private_artist_name(db: Any, owner: int, name: str) -> int:
    """The id of the owner's private artist name ``name``, made with its artist when missing."""
    found = db.scalar(
        select(ArtistName.id)
        .join(Artist, ArtistName.artist_id == Artist.id)
        .where(
            Artist.scope == "private", Artist.owner_id == owner, ArtistName.name == name
        )
    )
    if found is not None:
        return int(found)
    artist = Artist(scope="private", owner_id=owner)
    db.add(artist)
    db.flush()
    artist_name = ArtistName(artist_id=artist.id, name=name, is_default=True)
    db.add(artist_name)
    db.flush()
    return int(artist_name.id)


def file_as_song(owner: int, project_id: str, title: str, artist: str | None) -> int:
    """A private song (and artist) for the project, with the version "original"."""
    with session() as db:
        song = Song(scope="private", owner_id=owner, title=title)
        db.add(song)
        db.flush()
        if artist:
            db.add(
                SongArtist(
                    song_id=song.id,
                    artist_name_id=_private_artist_name(db, owner, artist),
                )
            )
        db.add(
            PrivateVersion(
                song_id=song.id, version_name=VERSION_NAME, project_id=project_id
            )
        )
        return int(song.id)


# ---------------------------------------------------------------------- the notes


def _rows(payload: dict[str, Any]) -> list[tuple[Any, ...]]:
    """Every note of a payload as the pipeline reads it (ids assigned as on every read)."""
    items = payload.get("events", [])
    ids, _ = events_file.assign_ids(
        (item.get("id") for item in items), int(payload.get("nextId") or 0)
    )
    return [
        (
            note_id,
            int(item["midiNote"]),
            float(item["start"]),
            float(item["end"]),
            int(item.get("velocity", 64)),
            item.get("hand"),
            bool(item.get("handGuessed", False)),
            bool(item.get("removed", False)),
        )
        for note_id, item in zip(ids, items)
    ]


def move_notes(source: Path, target: Path) -> int:
    """``events.json`` to ``notes.pmn``, checked: every note, the header, the length and the title
    read back equal. Returns the number of notes. Raises ``ValueError`` on any difference.
    """
    old = events_file.read_payload(source)
    if old is None:
        raise ValueError(f"{source.name} cannot be read")
    events_file.write_payload(target, old)
    new = events_file.read_payload(target)
    assert new is not None
    if _rows(old) != _rows(new):
        raise ValueError(f"{source} reads differently as notes.pmn")
    if events_file.header_from_payload(old) != events_file.header_from_payload(new):
        raise ValueError(f"{source}: the header reads differently as notes.pmn")
    if round(float(old["durationSeconds"]), 6) != new["durationSeconds"] or old.get(
        "title"
    ) != new.get("title"):
        raise ValueError(f"{source}: the length or the title reads differently")
    return len(old.get("events", []))


# ---------------------------------------------------------------------- the audio


def _measure(normalized: Path) -> int | None:
    if not normalized.is_file():
        return None
    _, samples = formats.sample_count(normalized)
    return frame_count(samples)


def store_audio(original: Path, normalized: Path) -> tuple[str, AudioEntry]:
    frames = _measure(normalized)
    extension = original.suffix.lstrip(".").lower()
    content_hash = audio_files.add_file(
        original, extension, duration_ms=None if frames is None else frames * FRAME_MS
    )
    return content_hash, AudioEntry(format=extension, frames=frames)


def _original_of(folder: Path) -> Path | None:
    found = sorted(folder.glob("original.*"))
    return found[0] if found else None


# ---------------------------------------------------------------------- a piece


def move_piece(
    folder: Path, owner: int, songs: dict[str, tuple[str, str | None]]
) -> dict[str, Any]:
    """One ``data/audio/<uuid>/`` to one project. Returns its row of the report."""
    uuid = folder.name
    metadata = AudioMetadata.model_validate_json(
        (folder / "metadata.json").read_text("utf-8")
    )
    seed = songs.get(uuid)
    layer = "private" if seed else "vault"
    row: dict[str, Any] = {"uuid": uuid, "title": metadata.alias, "layer": layer}

    bundle.create_project(
        owner_id=owner,
        title=metadata.alias,
        source=PartSource(
            kind=metadata.source.value,
            format=metadata.format,
            original_filename=metadata.original_filename,
            duration_seconds=metadata.duration_seconds,
            sample_rate=metadata.sample_rate,
            url=metadata.source_url,
            source_audio_uuid=metadata.source_audio_uuid,
            source_time_range=(
                metadata.source_time_range.model_dump(by_alias=True)
                if metadata.source_time_range
                else None
            ),
        ),
        layer=layer,
        project_id=uuid,
        frame_ms=metadata.frame_ms,
        created_at=metadata.created_at,
    )
    part_dir, cache_dir = paths.part_dir(uuid), paths.part_cache_dir(uuid)

    # The audio and its timeline.
    original = _original_of(folder)
    timeline = Timeline(audio_revision=metadata.audio_revision)
    if original is not None:
        content_hash, entry = store_audio(original, folder / "normalized.wav")
        timeline = timeline.model_copy(
            update={
                "audio": {content_hash: entry},
                "segments": bundle.segments_for_cuts(
                    content_hash, metadata.cuts, entry.frames
                ),
            }
        )
        row["audio"] = content_hash
        row["audioBytes"] = original.stat().st_size
        if bundle.cuts_of(timeline) != list(metadata.cuts):
            raise ValueError(
                f"the cuts {metadata.cuts} do not read back from the timeline"
            )
    bundle.write_timeline(uuid, timeline)
    row["cuts"] = len(metadata.cuts)

    for name in CACHE_FILES:
        if (folder / name).is_file():
            shutil.copy2(folder / name, cache_dir / name)
    for path in folder.glob("piece-r*.*"):
        shutil.copy2(path, cache_dir / path.name)

    # The notes and the sheet.
    matrices = folder / "matrices"
    row["notes"] = (
        move_notes(matrices / "events.json", part_dir / "notes.pmn")
        if (matrices / "events.json").is_file()
        else None
    )
    row["sheet"] = (matrices / "rhythm.json").is_file()
    if row["sheet"]:
        shutil.copy2(matrices / "rhythm.json", part_dir / "sheet.json")
    for name in PART_FILES:
        if (matrices / name).is_file():
            shutil.copy2(matrices / name, part_dir / name)

    # The history: notes and sheet as they are now stored, the audio by its hash.
    row["history"] = 0
    for version in sorted((folder / "history").glob("v*")):
        target = paths.history_version_dir(uuid, int(version.name[1:]))
        target.mkdir(parents=True, exist_ok=True)
        if (version / "events.json").is_file():
            move_notes(version / "events.json", target / "notes.pmn")
        if (version / "rhythm.json").is_file():
            shutil.copy2(version / "rhythm.json", target / "sheet.json")
        if (version / "snapshot.json").is_file():
            shutil.copy2(version / "snapshot.json", target / "snapshot.json")
        old_audio = _original_of(version)
        if old_audio is not None:
            content_hash, entry = store_audio(old_audio, version / "normalized.wav")
            snapshot = Timeline(
                audio={content_hash: entry},
                segments=bundle.segments_for_cuts(content_hash, [], entry.frames),
            )
            (target / "timeline.json").write_text(
                snapshot.model_dump_json(by_alias=True, indent=2) + "\n",
                encoding="utf-8",
            )
        row["history"] += 1
    staging = folder / "staging"
    if staging.is_dir() and any(staging.iterdir()):
        row["stagingSkipped"] = sorted(path.name for path in staging.iterdir())

    # The video, a temporary file of its owner.
    if (folder / "video").is_dir():
        shutil.copytree(folder / "video", paths.video_dir(uuid), dirs_exist_ok=True)
        row["video"] = True

    bundle.sync_audio_refs(uuid)
    row["step"] = refresh_step(uuid)
    keep_times(folder, uuid)
    if seed:
        row["song"], row["artist"] = seed
        row["songId"] = file_as_song(owner, uuid, *seed)
    return row


def _mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.is_file() else None


def keep_times(folder: Path, uuid: str) -> None:
    """Give the new files the times of the old ones, so "when it changed" on the Projects page is
    still when the piece changed, not when it was migrated. ``project.json`` takes the newest time
    of the old folder's own files (what the page showed before), ``notes.pmn`` the time of
    ``events.json``, ``timeline.json`` the time of ``metadata.json``."""
    import os  # noqa: PLC0415
    from datetime import datetime, timezone  # noqa: PLC0415

    own = [child.stat().st_mtime for child in folder.iterdir() if child.is_file()]
    if own:
        changed = datetime.fromtimestamp(max(own), tz=timezone.utc)
        project = bundle.read_project(uuid)
        bundle.write_project(project.model_copy(update={"updated_at": changed}), touch=False)
    part = paths.part_dir(uuid)
    pairs = {
        paths.project_json_path(uuid): max(own) if own else None,
        part / "notes.pmn": _mtime(folder / "matrices" / "events.json"),
        part / "timeline.json": _mtime(folder / "metadata.json"),
    }
    for target, when in pairs.items():
        if when is not None and target.is_file():
            os.utime(target, (when, when))


def move_examples(source: Path) -> int:
    target = paths.frame_examples_root()
    target.mkdir(parents=True, exist_ok=True)
    moved = 0
    for path in sorted(source.glob("*.json")) if source.is_dir() else []:
        if not (target / path.name).exists():
            shutil.copy2(path, target / path.name)
            moved += 1
    return moved


def _size(folder: Path) -> int:
    return sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())


def migrate(data_dir: Path, seed_dir: Path = SEED_DIR) -> dict[str, Any]:
    engine()
    paths.ensure_database_tree()
    owner = ensure_master_user()
    songs = seed_songs(seed_dir)
    report: dict[str, Any] = {
        "source": str(data_dir),
        "target": str(paths.database_dir()),
        "masterUserId": owner,
        "moved": [],
        "skipped": [],
        "failed": [],
    }
    audio_root = data_dir / "audio"
    for folder in sorted(audio_root.iterdir()) if audio_root.is_dir() else []:
        if not (folder / "metadata.json").is_file():
            report["failed"].append({"uuid": folder.name, "reason": "no metadata.json"})
            continue
        try:
            locate.part(folder.name)
            report["skipped"].append(
                {"uuid": folder.name, "reason": "already in .database/"}
            )
            continue
        except locate.NotFound:
            pass
        try:
            report["moved"].append(move_piece(folder, owner, songs))
        except (
            Exception
        ) as exc:  # noqa: BLE001 - one bad piece must not stop the others
            report["failed"].append(
                {"uuid": folder.name, "reason": f"{type(exc).__name__}: {exc}"}
            )
            try:
                bundle.delete_project(folder.name)
            except locate.NotFound:
                pass
    report["examples"] = move_examples(data_dir / "frame-examples")
    moved = report["moved"]
    report["counts"] = {
        "pieces": len(moved) + len(report["skipped"]) + len(report["failed"]),
        "moved": len(moved),
        "skipped": len(report["skipped"]),
        "failed": len(report["failed"]),
        "vault": sum(1 for row in moved if row["layer"] == "vault"),
        "privateLibrary": sum(1 for row in moved if row["layer"] == "private"),
        "withNotes": sum(1 for row in moved if row["notes"] is not None),
        "notes": sum(row["notes"] or 0 for row in moved),
        "withSheet": sum(1 for row in moved if row["sheet"]),
        "withCuts": sum(1 for row in moved if row["cuts"]),
        "withVideo": sum(1 for row in moved if row.get("video")),
        "historyVersions": sum(row["history"] for row in moved),
        "songs": sum(1 for row in moved if row.get("songId")),
    }
    report["sizes"] = {
        "sourceBytes": _size(data_dir) if data_dir.is_dir() else 0,
        "databaseBytes": _size(paths.database_dir()),
        "audioStoreBytes": _size(paths.audio_store_dir()),
        "audioFiles": sum(
            1 for path in paths.audio_store_dir().iterdir() if path.is_file()
        ),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source", type=Path, default=None, help="default: aitu-backend/data"
    )
    parser.add_argument("--report", type=Path, help="write the report here as JSON")
    args = parser.parse_args()
    report = migrate(args.source or paths.data_dir())
    text = json.dumps(report, indent=2, default=str)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("counts", "sizes", "failed", "skipped")},
            indent=2,
        )
    )
    sys.exit(1 if report["failed"] else 0)


if __name__ == "__main__":
    main()
