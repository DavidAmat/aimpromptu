"""The project bundle, the audio timeline and the audio store (implementation 02, Phase 3, plan
sections 8.3 and 8.5, P-3)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile
from sqlalchemy import select

from aitu_backend.audio import store
from aitu_backend.db.database import session
from aitu_backend.db.models import AudioFile, AudioRef, Part, Project
from aitu_backend.db.users import ensure_master_user
from aitu_backend.editing import history
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import AudioEntry, Segment, Timeline
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent


def tone(
    folder: Path, seconds: float, name: str = "tone.wav", pitch: float = 220.0
) -> Path:
    rate = 16_000
    samples = 0.3 * np.sin(2 * np.pi * pitch * np.arange(int(rate * seconds)) / rate)
    path = folder / name
    wavfile.write(path, rate, (samples * 32767).astype(np.int16))
    return path


def a_part(folder: Path, seconds: float = 2.0, title: str = "Piece") -> str:
    """A part with a stored, measured 16 kHz WAV (its own normalized copy) and one note."""
    part = store.create(title, AudioSource.UPLOAD, "wav").uuid
    normalized = tone(paths.part_cache_dir(part), seconds, "normalized.wav")
    store.replace_original(part, normalized, "wav", keep_cuts=False)
    store.update(part, duration_seconds=seconds, sample_rate=16_000)
    pipeline.save_note_events(
        part, [NoteEvent(midi_note=60, start=0.1, end=0.5)], seconds, title
    )
    return part


# ------------------------------------------------------------------ the timeline


@pytest.mark.parametrize(
    "cuts",
    [
        [],
        [(0, 10)],
        [(10, 20)],
        [(190, 200)],
        [(0, 10), (50, 60), (190, 200)],
        [(0, 200)],
    ],
)
def test_cuts_and_segments_convert_both_ways(cuts: list[tuple[int, int]]) -> None:
    segments = bundle.segments_for_cuts("h", cuts, 200)
    timeline = Timeline(
        audio={"h": AudioEntry(format="wav", frames=200)}, segments=segments
    )
    assert bundle.cuts_of(timeline) == cuts


def test_the_segments_are_the_kept_ranges_in_ms() -> None:
    segments = bundle.segments_for_cuts("h", [(0, 316), (26022, 26351)], 26351)
    assert [(s.from_ms, s.to_ms) for s in segments] == [(3160, 260220)]


def test_a_file_not_measured_yet_is_one_open_segment() -> None:
    assert bundle.segments_for_cuts("h", [], None) == [
        Segment(audio="h", from_ms=0, to_ms=None)
    ]
    timeline = Timeline(
        audio={"h": AudioEntry(format="mp3")},
        segments=bundle.segments_for_cuts("h", [], None),
    )
    assert bundle.cuts_of(timeline) == []
    with pytest.raises(ValueError, match="length of the audio"):
        bundle.segments_for_cuts("h", [(1, 2)], None)


def test_a_part_with_no_audio_has_no_cuts_and_refuses_one(tmp_path: Path) -> None:
    part = store.create("Empty", AudioSource.COMPOSED, "wav").uuid
    assert store.read_metadata(part).cuts == []
    with pytest.raises(ValueError, match="nothing to cut"):
        store.set_cuts(part, [(1, 2)])


def test_cuts_are_stored_in_the_timeline_of_the_part(tmp_path: Path) -> None:
    part = a_part(tmp_path, seconds=2.0)
    store.set_cuts(part, [(10, 20)])
    stored = json.loads(paths.part_timeline_path(part).read_text())
    (content_hash,) = stored["audio"]
    assert stored["audioRevision"] == 1
    assert stored["audio"][content_hash] == {"format": "wav", "frames": 200}
    assert stored["segments"] == [
        {"audio": content_hash, "fromMs": 0, "toMs": 100},
        {"audio": content_hash, "fromMs": 200, "toMs": 2000},
    ]
    assert store.read_metadata(part).cuts == [(10, 20)]


# ---------------------------------------------------------------- the bundle


def test_a_new_project_has_its_bundle_and_its_rows(tmp_path: Path) -> None:
    part = store.create(
        "My tune", AudioSource.YOUTUBE, "mp3", source_url="https://x"
    ).uuid
    project = json.loads(paths.project_json_path(part).read_text())
    assert (
        project["id"] == part
        and project["title"] == "My tune"
        and project["kind"] == "song"
    )
    assert project["ownerId"] == ensure_master_user()
    assert project["parts"] == [
        {
            "id": part,
            "subheader": None,
            "source": {
                "kind": "youtube",
                "format": "mp3",
                "originalFilename": None,
                "durationSeconds": None,
                "sampleRate": None,
                "url": "https://x",
                "sourceAudioUuid": None,
                "sourceTimeRange": None,
            },
        }
    ]
    with session() as db:
        row = db.get(Project, part)
        assert (row.layer, row.title, row.owner_id) == (
            "vault",
            "My tune",
            ensure_master_user(),
        )
        assert [
            p.id for p in db.scalars(select(Part).where(Part.project_id == part))
        ] == [part]


def test_the_title_is_the_alias_and_stays_in_step_with_its_row(tmp_path: Path) -> None:
    part = a_part(tmp_path)
    store.rename(part, "Renamed")
    assert bundle.read_project(part).title == "Renamed"
    with session() as db:
        assert db.get(Project, part).title == "Renamed"


def test_the_same_audio_is_stored_once(tmp_path: Path) -> None:
    first = store.create("a", AudioSource.UPLOAD, "mp3").uuid
    second = store.create("b", AudioSource.UPLOAD, "mp3").uuid
    one = store.save_original(first, io.BytesIO(b"same bytes"), "mp3")
    two = store.save_original(second, io.BytesIO(b"same bytes"), "mp3")
    assert one == two
    assert [path.name for path in paths.audio_store_dir().iterdir()] == [one.name]
    with session() as db:
        assert len(list(db.scalars(select(AudioFile)))) == 1
        assert len(list(db.scalars(select(AudioRef)))) == 2


def test_a_duplicate_has_new_ids_and_shares_the_audio(tmp_path: Path) -> None:
    part = a_part(tmp_path)
    paths.staging_session_dir(part, "s1").mkdir(parents=True)
    history.snapshot_notes(part)
    store.write_waveform(part, {"points": 1})

    copy = bundle.duplicate_project(part, title="Copy")
    (copy_part,) = [entry.id for entry in copy.parts]
    assert copy.id == copy_part != part
    assert store.read_metadata(copy_part).alias == "Copy"
    assert store.get(copy_part).original_path == store.get(part).original_path
    assert store.get(copy_part).has_normalized()
    assert pipeline.load_note_events(copy_part).events[0].midi_note == 60
    assert not paths.staging_root(copy_part).exists() or not any(
        paths.staging_root(copy_part).iterdir()
    )
    assert not paths.part_history_dir(copy_part).exists()
    assert len(list(paths.audio_store_dir().iterdir())) == 1
    with session() as db:
        assert {ref.project_id for ref in db.scalars(select(AudioRef))} == {
            part,
            copy.id,
        }


def test_deleting_keeps_the_audio_another_project_uses(tmp_path: Path) -> None:
    part = a_part(tmp_path)
    copy = bundle.duplicate_project(part)
    original = store.get(part).original_path
    store.delete(part)
    assert not store.exists(part) and not paths.history_dir().joinpath(part).exists()
    assert original.is_file()
    with pytest.raises(locate.NotFound):
        locate.part(part)

    store.delete(copy.id)
    assert not original.exists()
    with session() as db:
        assert list(db.scalars(select(AudioFile))) == []
        assert list(db.scalars(select(Project))) == []


def test_a_lost_normalized_copy_is_written_again(tmp_path: Path) -> None:
    part = a_part(tmp_path)
    paths.normalized_path(part).unlink()
    assert store.get(part).has_normalized()


def test_a_new_audio_file_keeps_the_old_one_for_the_history(tmp_path: Path) -> None:
    part = a_part(tmp_path)
    old = store.get(part).original_path
    history.snapshot_current(part)
    store.replace_original(part, tone(tmp_path, 3.0, "longer.wav", 330.0), "wav")
    new = store.get(part).original_path
    assert new != old and old.is_file()
    snapshot = paths.history_version_dir(part, 1)
    assert sorted(path.name for path in snapshot.iterdir()) == [
        "notes.pmn",
        "timeline.json",
    ]
    with session() as db:
        refs = set(db.scalars(select(AudioRef.hash).where(AudioRef.project_id == part)))
    assert refs == {old.stem, new.stem}


def test_the_duplicate_route(tmp_path: Path) -> None:
    client = TestClient(create_app())
    part = a_part(tmp_path)
    answer = client.post(f"/projects/{part}/duplicate", json={"title": "bench copy"})
    assert answer.status_code == 201
    body = answer.json()
    assert body["title"] == "bench copy" and body["parts"] == [body["id"]]
    assert client.get(f"/pieces/{body['id']}/status").status_code == 200
    assert client.post("/projects/nope/duplicate").status_code == 404


def test_delete_unused_keeps_a_file_in_use(tmp_path: Path) -> None:
    part = a_part(tmp_path)
    content_hash = store.get(part).original_path.stem
    assert audio_files.delete_unused([content_hash]) == []
    assert audio_files.file_path(content_hash, "wav").is_file()
