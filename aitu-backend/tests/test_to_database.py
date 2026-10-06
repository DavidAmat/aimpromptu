"""The migration of `aitu-backend/data/` into `.database/`, on a fixture tree (implementation 02,
Phase 3, plan section 8.9)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from scipy.io import wavfile
from sqlalchemy import select

from aitu_backend.audio import store
from aitu_backend.db.database import session
from aitu_backend.db.models import ArtistName, PrivateVersion, Project, Song, SongArtist
from aitu_backend.db.tools import check
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription import pipeline

SEED = "aaaaaaaa-0000-4000-8000-000000000001"
PLAIN = "bbbbbbbb-0000-4000-8000-000000000002"
VIDEO = "cccccccc-0000-4000-8000-000000000003"
BROKEN = "dddddddd-0000-4000-8000-000000000004"


def load_script() -> ModuleType:
    path = paths.repo_root() / "scripts" / "migrate" / "to_database.py"
    spec = importlib.util.spec_from_file_location("to_database", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wav(path: Path, seconds: float, pitch: float = 220.0) -> None:
    rate = 16_000
    samples = 0.2 * np.sin(2 * np.pi * pitch * np.arange(int(rate * seconds)) / rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, rate, (samples * 32767).astype(np.int16))


def events(count: int, *, ids: bool = True) -> dict:
    rows = [
        {
            **({"id": index} if ids else {}),
            "midiNote": 60 + index % 12,
            "start": round(index * 0.2501, 4),
            "end": round(index * 0.2501 + 0.15, 4),
            "velocity": 64,
            **({"hand": "left"} if index % 3 == 0 else {}),
            **({"removed": True} if index == 1 else {}),
        }
        for index in range(count)
    ]
    return {
        "schemaVersion": "1.1",
        "durationSeconds": 3.0,
        "title": "T",
        "events": rows,
    }


def piece(root: Path, uuid: str, alias: str, **extra: object) -> Path:
    folder = root / "audio" / uuid
    folder.mkdir(parents=True)
    metadata = {
        "uuid": uuid,
        "alias": alias,
        "source": "youtube",
        "format": "wav",
        "durationSeconds": 3.0,
        "sampleRate": 16000,
        "sourceUrl": f"https://www.youtube.com/watch?v={uuid[:4]}",
        "createdAt": "2026-09-15T18:54:51Z",
        **extra,
    }
    (folder / "metadata.json").write_text(json.dumps(metadata))
    wav(folder / "original.wav", 3.0)
    wav(folder / "normalized.wav", 3.0)
    return folder


@pytest.fixture()
def tree(tmp_path: Path) -> tuple[Path, Path]:
    """Four pieces: one of the seed list with cuts, a sheet and history; one with old notes and no
    ids; one with a video and no notes; one that cannot be read. And the seed list."""
    data = tmp_path / "data"
    seed = piece(
        data, SEED, "Superestrella", cuts=[[0, 10], [290, 300]], audioRevision=1
    )
    (seed / "matrices").mkdir()
    (seed / "matrices" / "events.json").write_text(json.dumps(events(12)))
    (seed / "matrices" / "rhythm.json").write_text(json.dumps({"anchorMs": 217.1}))
    (seed / "matrices" / "music-version.json").write_text(json.dumps({"version": 2}))
    (seed / "waveform.json").write_text("{}")
    history = seed / "history" / "v1"
    history.mkdir(parents=True)
    (history / "events.json").write_text(json.dumps(events(5)))
    wav(history / "original.wav", 2.0, 330.0)
    wav(history / "normalized.wav", 2.0, 330.0)

    plain = piece(data, PLAIN, "Come on Eileen")
    (plain / "matrices").mkdir()
    old = events(7, ids=False)
    old["schemaVersion"] = "1.0"
    (plain / "matrices" / "events.json").write_text(json.dumps(old))

    video = piece(data, VIDEO, "Perfect")
    (video / "video").mkdir()
    (video / "video" / "source.mp4").write_bytes(b"video")
    (video / "video" / "calibration.json").write_text("{}")

    broken = data / "audio" / BROKEN
    broken.mkdir(parents=True)
    (broken / "metadata.json").write_text("{not json")

    (data / "frame-examples").mkdir()
    (data / "frame-examples" / "7years.json").write_text("{}")

    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    url = f"https://www.youtube.com/watch?v={SEED[:4]}"
    (seed_dir / "seed-state.json").write_text(
        json.dumps({"downloads": {url: {"uuid": SEED}}})
    )
    (seed_dir / "library.json").write_text(
        json.dumps(
            {"pieces": [{"url": url, "title": "Superestrella", "artist": "Aitana"}]}
        )
    )
    return data, seed_dir


def test_every_piece_is_moved_and_the_broken_one_is_reported(
    tree: tuple[Path, Path],
) -> None:
    script = load_script()
    report = script.migrate(*tree)
    assert report["counts"]["moved"] == 3 and report["counts"]["failed"] == 1
    assert report["failed"][0]["uuid"] == BROKEN
    assert report["counts"]["privateLibrary"] == 1 and report["counts"]["vault"] == 2
    assert report["examples"] == 1
    assert (paths.frame_examples_root() / "7years.json").is_file()
    assert check().problems == []


def test_a_piece_keeps_its_notes_cuts_sheet_and_history(
    tree: tuple[Path, Path],
) -> None:
    load_script().migrate(*tree)
    data, _ = tree
    metadata = store.read_metadata(SEED)
    assert metadata.alias == "Superestrella" and metadata.audio_revision == 1
    assert metadata.cuts == [(0, 10), (290, 300)]
    assert metadata.source_url == f"https://www.youtube.com/watch?v={SEED[:4]}"
    stored = pipeline.load_note_events(SEED)
    assert stored is not None and len(stored.events) == 12
    assert [event.removed for event in stored.events].count(True) == 1
    assert pipeline.load_rhythm(SEED) is None or pipeline.rhythm_path(SEED).is_file()
    assert json.loads(pipeline.rhythm_path(SEED).read_text()) == {"anchorMs": 217.1}
    assert json.loads(paths.music_version_path(SEED).read_text()) == {"version": 2}
    entry = store.get(SEED)
    assert (
        entry.original_path.read_bytes()
        == (data / "audio" / SEED / "original.wav").read_bytes()
    )
    assert entry.has_normalized() and entry.waveform_path.is_file()
    snapshot = paths.history_version_dir(SEED, 1)
    assert sorted(path.name for path in snapshot.iterdir()) == [
        "notes.pmn",
        "timeline.json",
    ]
    (old_audio,) = json.loads((snapshot / "timeline.json").read_text())["audio"]
    assert old_audio in bundle.used_hashes(SEED)


def test_old_notes_get_the_ids_every_reader_gave_them(tree: tuple[Path, Path]) -> None:
    load_script().migrate(*tree)
    stored = pipeline.load_note_events(PLAIN)
    assert [event.id for event in stored.events] == list(range(7))
    assert stored.header.next_id == 7


def test_the_seed_piece_is_a_song_of_the_private_library(
    tree: tuple[Path, Path],
) -> None:
    load_script().migrate(*tree)
    with session() as db:
        assert db.get(Project, SEED).layer == "private"
        assert db.get(Project, PLAIN).layer == "vault"
        song = db.scalar(select(Song))
        assert (song.scope, song.title) == ("private", "Superestrella")
        name = db.scalar(
            select(ArtistName.name)
            .join(SongArtist)
            .where(SongArtist.song_id == song.id)
        )
        assert name == "Aitana"
        version = db.scalar(select(PrivateVersion))
        assert (version.version_name, version.project_id) == ("original", SEED)
    assert paths.project_dir(SEED).parent == paths.layer_dir(1, "private")


def test_the_video_is_a_temporary_file_of_its_owner(tree: tuple[Path, Path]) -> None:
    load_script().migrate(*tree)
    assert paths.video_source_path(VIDEO) == (
        paths.tmp_dir() / "1" / VIDEO / "video" / "source.mp4"
    )
    assert paths.video_source_path(VIDEO).read_bytes() == b"video"
    assert pipeline.load_note_events(VIDEO) is None


def test_running_it_twice_changes_nothing(tree: tuple[Path, Path]) -> None:
    script = load_script()
    script.migrate(*tree)
    before = sorted(
        str(path) for path in paths.database_dir().rglob("*") if path.is_file()
    )
    again = script.migrate(*tree)
    assert again["counts"]["moved"] == 0 and again["counts"]["skipped"] == 3
    after = sorted(
        str(path) for path in paths.database_dir().rglob("*") if path.is_file()
    )
    assert after == before
    with session() as db:
        assert len(list(db.scalars(select(Song)))) == 1


def test_the_source_is_never_written(tree: tuple[Path, Path]) -> None:
    data, _ = tree
    before = {path: path.stat().st_mtime_ns for path in data.rglob("*")}
    load_script().migrate(*tree)
    assert {path: path.stat().st_mtime_ns for path in data.rglob("*")} == before
