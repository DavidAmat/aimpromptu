"""The projects of the Personal Vault (implementation 02, Phase 5, plan sections 8.3, 8.5, 10.1):
the `/projects` routes, the step kept in the table, **add audio** (several files in one timeline),
and the `.aitu` export and import with its round trip."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile
from sqlalchemy import select

from aitu_backend.audio import formats, store
from aitu_backend.db.database import session
from aitu_backend.db.models import AudioFile, Project
from aitu_backend.db.users import ensure_master_user
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.storage import audio_files, bundle, exchange, paths
from aitu_backend.storage.bundle import AudioEntry, Segment, Timeline
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

client = TestClient(create_app())


def tone_bytes(seconds: float, pitch: float = 220.0, rate: int = 16_000) -> bytes:
    samples = 0.3 * np.sin(2 * np.pi * pitch * np.arange(int(rate * seconds)) / rate)
    buffer = io.BytesIO()
    wavfile.write(buffer, rate, (samples * 32767).astype(np.int16))
    return buffer.getvalue()


def uploaded(seconds: float = 2.0, name: str = "first.wav", pitch: float = 220.0) -> str:
    """A project made the way the Source step makes one: an upload, normalized and measured."""
    answer = client.post(
        "/audio/upload", files={"file": (name, tone_bytes(seconds, pitch), "audio/wav")}
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["uuid"]


def with_notes(part: str, seconds: float = 2.0) -> None:
    pipeline.save_note_events(part, [NoteEvent(midi_note=60, start=0.1, end=0.5)], seconds, "x")


def stored_step(project_id: str) -> str | None:
    with session() as db:
        return db.scalar(select(Project.step).where(Project.id == project_id))


# ------------------------------------------------------------------ the list


def test_the_list_is_the_personal_vault_newest_change_first() -> None:
    owner = ensure_master_user()
    older = bundle.create_project(owner_id=owner, title="Older").id
    library = bundle.create_project(owner_id=owner, title="In the library", layer="private").id
    newer = uploaded(name="Newer.wav")
    rows = client.get("/projects").json()
    ids = [row["id"] for row in rows]
    assert ids == [newer, older]
    assert rows[0]["title"] == "Newer"
    assert rows[0]["parts"] == [newer]
    assert rows[0]["source"] == "upload" and rows[0]["layer"] == "vault"
    both = client.get("/projects", params=[("layer", "vault"), ("layer", "private")]).json()
    assert {row["id"] for row in both} == {newer, older, library}


def test_a_new_empty_project_opens_on_its_source_step() -> None:
    made = client.post("/projects", json={"title": ""})
    assert made.status_code == 201
    row = made.json()
    assert row["step"] == "source" and row["hasNotes"] is False
    status = client.get(f"/pieces/{row['id']}/status").json()
    assert status["resume"] == "source"
    assert [step["enabled"] for step in status["steps"]] == [True, False, False, False, False]


def test_the_step_is_stored_and_worked_out_again_only_after_a_change() -> None:
    part = uploaded()
    assert client.get(f"/projects/{part}").json()["step"] == "audio"
    assert stored_step(part) == "audio"
    with_notes(part)
    assert stored_step(part) is None  # the notes changed: the stored step is forgotten
    assert client.get(f"/projects/{part}").json()["step"] == "notes"
    assert stored_step(part) == "notes"


def test_rename_and_delete() -> None:
    part = uploaded()
    renamed = client.patch(f"/projects/{part}", json={"title": "  Clocks  "})
    assert renamed.status_code == 200 and renamed.json()["title"] == "Clocks"
    assert bundle.read_project(part).title == "Clocks"
    assert client.patch(f"/projects/{part}", json={"title": "   "}).status_code == 422
    content_hash = bundle.read_timeline(part).single_audio
    folder = paths.project_dir(part)
    assert client.delete(f"/projects/{part}").status_code == 204
    assert not folder.exists()
    assert audio_files.info(content_hash) is None  # no other project used it
    assert client.get(f"/projects/{part}").status_code == 404


def test_a_duplicate_is_a_new_project_with_the_same_audio() -> None:
    part = uploaded()
    with_notes(part)
    copy = client.post(f"/projects/{part}/duplicate", json={}).json()
    assert copy["id"] != part
    assert bundle.read_timeline(copy["id"]).audio == bundle.read_timeline(part).audio
    assert client.get(f"/projects/{copy['id']}").json()["step"] == "notes"


# ------------------------------------------------------------- several files


def test_the_axis_of_several_files_and_its_cuts_convert_both_ways() -> None:
    files = [("a", 100), ("b", 50), ("a", 100)]  # the same file may come twice
    for cuts in ([], [(90, 110)], [(0, 100)], [(100, 150)], [(140, 160), (240, 250)], [(5, 245)]):
        timeline = Timeline(
            audio={
                "a": AudioEntry(format="wav", frames=100),
                "b": AudioEntry(format="wav", frames=50),
            },
            sources=["a", "b", "a"],
            segments=bundle.segments_for_axis(files, cuts),
        )
        assert bundle.cuts_of(timeline) == cuts, cuts


def test_a_cut_across_a_join_is_two_segments() -> None:
    segments = bundle.segments_for_axis([("a", 100), ("b", 50)], [(90, 110)])
    assert segments == [
        Segment(audio="a", from_ms=0, to_ms=900, source=0),
        Segment(audio="b", from_ms=100, to_ms=500, source=1),
    ]


def test_add_audio_appends_a_file_and_keeps_the_cuts() -> None:
    part = uploaded(2.0)
    assert client.put(f"/audio/{part}/cuts", json={"cuts": [[10, 20]]}).status_code == 200
    with_notes(part)
    before = client.get(f"/audio/{part}/cuts").json()
    added = client.post(
        f"/audio/{part}/add", files={"file": ("second.wav", tone_bytes(1.0, 440.0), "audio/wav")}
    )
    assert added.status_code == 201, added.text

    cuts = client.get(f"/audio/{part}/cuts").json()
    assert cuts["totalFrames"] == 300
    assert cuts["cuts"] == [[10, 20]]
    assert cuts["audioRevision"] == before["audioRevision"] + 1
    assert cuts["notesStale"] is True
    assert cuts["files"] == [
        {"name": "first.wav", "startFrame": 0, "frames": 200},
        {"name": "second.wav", "startFrame": 200, "frames": 100},
    ]
    timeline = bundle.read_timeline(part)
    assert len(timeline.sources or []) == 2 and len(timeline.audio) == 2

    # normalized.wav is the two files end to end, on whole frames.
    entry = store.get(part)
    rate, samples = formats.read_wav(entry.normalized_path)
    assert rate == 16_000 and len(samples) == 300 * 160
    assert entry.metadata.duration_seconds == pytest.approx(3.0)

    # The Audio step plays the joined original.
    original = client.get(f"/audio/{part}/file", params={"original": "true"})
    assert original.status_code == 200
    assert original.headers["content-type"] == "audio/flac"


def test_a_cut_across_the_join_of_two_files_is_saved_and_played() -> None:
    part = uploaded(2.0)
    client.post(
        f"/audio/{part}/add", files={"file": ("b.wav", tone_bytes(1.0, 440.0), "audio/wav")}
    )
    revision = client.get(f"/audio/{part}/cuts").json()["audioRevision"]
    saved = client.put(
        f"/audio/{part}/cuts", json={"cuts": [[190, 210]], "baseRevision": revision}
    ).json()
    assert saved["cuts"] == [[190, 210]] and saved["pieceFrames"] == 280
    segments = bundle.read_timeline(part).segments
    assert [(s.from_ms, s.to_ms) for s in segments] == [(0, 1900), (100, 1000)]
    played = client.get(f"/audio/{part}/file")
    assert played.status_code == 200 and played.headers["content-type"] == "audio/flac"


def test_a_file_that_cannot_be_read_is_refused_and_not_kept() -> None:
    part = uploaded()
    with session() as db:
        before = set(db.scalars(select(AudioFile.hash)))
    answer = client.post(
        f"/audio/{part}/add", files={"file": ("broken.wav", b"not audio at all", "audio/wav")}
    )
    assert answer.status_code == 422
    with session() as db:
        assert set(db.scalars(select(AudioFile.hash))) == before
    assert len(bundle.read_timeline(part).audio) == 1


def test_a_new_single_file_after_several_forgets_the_others() -> None:
    part = uploaded(2.0)
    client.post(f"/audio/{part}/add", files={"file": ("b.wav", tone_bytes(1.0), "audio/wav")})
    clip = paths.part_cache_dir(part) / "spliced.wav"
    clip.write_bytes(tone_bytes(3.0, 330.0))
    store.replace_original(part, clip, "wav")
    timeline = bundle.read_timeline(part)
    assert timeline.sources is None and len(timeline.audio) == 1
    assert bundle.read_project(part).parts[0].source.added == []


# ------------------------------------------------------------- export, import


def exported(project_id: str) -> zipfile.ZipFile:
    answer = client.get(f"/projects/{project_id}/export")
    assert answer.status_code == 200
    assert answer.headers["content-disposition"].endswith('.aitu"')
    return zipfile.ZipFile(io.BytesIO(answer.content))


def part_files(archive: zipfile.ZipFile) -> list[dict[str, bytes]]:
    project = json.loads(archive.read("project.json"))
    return [
        {
            name: archive.read(f"parts/{entry['id']}/{name}")
            for name in exchange.PART_FILES
            if f"parts/{entry['id']}/{name}" in archive.namelist()
        }
        for entry in project["parts"]
    ]


def audio_of(archive: zipfile.ZipFile) -> dict[str, bytes]:
    return {name: archive.read(name) for name in archive.namelist() if name.startswith("audio/")}


def a_full_project() -> str:
    part = uploaded(2.0, "Clocks.wav")
    client.post(f"/audio/{part}/add", files={"file": ("bridge.wav", tone_bytes(1.0), "audio/wav")})
    client.put(f"/audio/{part}/cuts", json={"cuts": [[10, 20]]})
    with_notes(part, 3.0)
    pipeline.save_rhythm(part, SavedRhythm(anchor_ms=500.0, frame_ms=40.0))
    return part


def test_export_import_and_export_again_give_the_same_notes_sheet_and_audio() -> None:
    part = a_full_project()
    first = exported(part)
    assert json.loads(first.read("export.json"))["format"] == "aimpromptu-project"
    assert set(part_files(first)[0]) == {"notes.pmn", "sheet.json", "timeline.json"}
    assert len(audio_of(first)) == 2

    imported = client.post(
        "/projects/import",
        files={"file": ("Clocks.aitu", _bytes(first), "application/octet-stream")},
    )
    assert imported.status_code == 201, imported.text
    row = imported.json()
    assert row["id"] != part and row["title"] == "Clocks" and row["layer"] == "vault"
    assert bundle.read_project(row["id"]).origin == {"importedFrom": part}

    second = exported(row["id"])
    assert part_files(second) == part_files(first)
    assert audio_of(second) == audio_of(first)
    # The imported project works: its audio, its cuts and its notes are there.
    cuts = client.get(f"/audio/{row['id']}/cuts").json()
    assert cuts["cuts"] == [[10, 20]] and cuts["totalFrames"] == 300
    status = client.get(f"/pieces/{row['id']}/status").json()
    assert status == {**client.get(f"/pieces/{part}/status").json(), "audioUuid": row["id"]}


def _bytes(archive: zipfile.ZipFile) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as copy:
        for name in archive.namelist():
            copy.writestr(name, archive.read(name))
    return out.getvalue()


def _project_count() -> int:
    with session() as db:
        return len(list(db.scalars(select(Project.id))))


@pytest.mark.parametrize(
    "damage",
    ["not a zip", "no manifest", "damaged audio", "missing audio", "bad notes"],
)
def test_an_import_that_is_not_a_project_is_refused_and_leaves_nothing(damage: str) -> None:
    part = a_full_project()
    archive = exported(part)
    names = archive.namelist()
    audio_names = [name for name in names if name.startswith("audio/")]
    out = io.BytesIO()
    if damage == "not a zip":
        body = b"hello"
    else:
        with zipfile.ZipFile(out, "w") as copy:
            for name in names:
                data = archive.read(name)
                if damage == "no manifest" and name == "export.json":
                    continue
                if damage == "missing audio" and name == audio_names[0]:
                    continue
                if damage == "damaged audio" and name == audio_names[0]:
                    data = data[:-10] + b"0123456789"
                if damage == "bad notes" and name.endswith("notes.pmn"):
                    data = b'{"format": "something else"}'
                copy.writestr(name, data)
        body = out.getvalue()
    projects = _project_count()
    with session() as db:
        hashes = set(db.scalars(select(AudioFile.hash)))
    answer = client.post("/projects/import", files={"file": ("x.aitu", body, "application/zip")})
    assert answer.status_code == 422
    assert _project_count() == projects
    with session() as db:
        assert set(db.scalars(select(AudioFile.hash))) == hashes


def test_the_name_of_an_export_is_the_title() -> None:
    assert exchange.export_name("Clocks / live: 2") == "Clocks live 2.aitu"
    assert exchange.export_name("") == "Untitled project.aitu"


def test_a_project_of_another_user_cannot_be_exported(tmp_path: Path) -> None:
    from aitu_backend.db import users  # noqa: PLC0415

    anna = users.create_user("anna", "anna-password")
    hers = bundle.create_project(owner_id=anna.id, title="Hers").id
    assert client.get(f"/projects/{hers}/export").status_code == 404
    assert client.delete(f"/projects/{hers}").status_code == 404
    assert hers not in [row["id"] for row in client.get("/projects").json()]


def test_a_video_file_becomes_a_project_with_its_video(tmp_path: Path) -> None:
    import subprocess  # noqa: PLC0415

    if not formats.ffmpeg_available():
        pytest.skip("ffmpeg is not installed")
    video = tmp_path / "piano.mp4"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10"]
        + ["-f", "lavfi", "-i", "sine=frequency=440", "-t", "2", "-shortest", str(video)],
        check=True,
    )
    answer = client.post(
        "/video/upload", files={"file": ("piano.mp4", video.read_bytes(), "video/mp4")}
    )
    assert answer.status_code == 201, answer.text
    part = answer.json()["audioUuid"]
    assert client.get(f"/audio/{part}").json()["hasVideo"] is True
    row = client.get(f"/projects/{part}").json()
    assert row["hasVideo"] is True and row["title"] == "piano"
    status = client.get(f"/pieces/{part}/status").json()
    notes = next(step for step in status["steps"] if step["step"] == "notes")
    assert notes["reason"] == "Read the notes of the video to see them."
    # Reading needs the piano fitted first.
    assert client.post(f"/video/{part}/read").status_code == 409
    refused = client.post("/video/upload", files={"file": ("notes.txt", b"x", "text/plain")})
    assert refused.status_code == 422
    # The video is a temporary file of the part, deleted with the project.
    folder = paths.video_dir(part)
    assert folder.is_dir()
    client.delete(f"/projects/{part}")
    assert not folder.exists()


def test_add_audio_needs_a_first_file() -> None:
    empty = client.post("/projects", json={}).json()["id"]
    answer = client.post(
        f"/audio/{empty}/add", files={"file": ("b.wav", tone_bytes(1.0), "audio/wav")}
    )
    assert answer.status_code == 409


def test_the_source_of_a_part_lists_the_added_files() -> None:
    part = uploaded(1.0, "a.wav")
    client.post(f"/audio/{part}/add", files={"file": ("b.wav", tone_bytes(1.0), "audio/wav")})
    source = bundle.read_project(part).parts[0].source
    assert source.original_filename == "a.wav"
    assert [added.original_filename for added in source.added] == ["b.wav"]
    assert source.duration_seconds == pytest.approx(1.0)
    assert store.read_metadata(part).duration_seconds == pytest.approx(2.0)
    assert AudioSource(source.kind) is AudioSource.UPLOAD
