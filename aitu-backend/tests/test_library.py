"""The Private Library (implementation 02, Phase 6, plan sections 8.5, 10.2, 10.6, 15.1 and 15.2):
**Save to library**, the audio written again with only the ranges in use, the Edit copy, Replace
the version, Save as a new version, the history of a version, the songs, the artists and their
names, and who may do what."""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile
from sqlalchemy import select

from aitu_backend.audio import formats
from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import Project
from aitu_backend.main import create_app
from aitu_backend.pmn.events_file import PieceHeader
from aitu_backend.storage import audio_files, bundle, paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")

client = TestClient(create_app())
READING = {"anchorFigure": "negra", "anchorMs": 500.0, "frameMs": 40.0}


def tone_bytes(seconds: float, pitch: float = 220.0, rate: int = 16_000) -> bytes:
    samples = 0.3 * np.sin(2 * np.pi * pitch * np.arange(int(rate * seconds)) / rate)
    buffer = io.BytesIO()
    wavfile.write(buffer, rate, (samples * 32767).astype(np.int16))
    return buffer.getvalue()


def uploaded(seconds: float = 8.0, name: str = "Superestrella.wav", on: TestClient = client) -> str:
    answer = on.post("/audio/upload", files={"file": (name, tone_bytes(seconds), "audio/wav")})
    assert answer.status_code == 201, answer.text
    return answer.json()["uuid"]


def music(seconds: float) -> list[NoteEvent]:
    """A right hand every 250 ms over a left hand every second."""
    right = [
        NoteEvent(midi_note=72 + index % 5, start=index * 0.25, end=index * 0.25 + 0.2)
        for index in range(int(seconds * 4) - 1)
    ]
    left = [
        NoteEvent(midi_note=36 + (index % 2) * 7, start=float(index), end=index + 0.9)
        for index in range(int(seconds) - 1)
    ]
    return sorted(right + left, key=lambda event: (event.start, event.midi_note))


def make_ready(part: str, seconds: float, on: TestClient = client) -> None:
    """Notes, hands predicted and saved, a piano sheet written: the Sheet step is ready."""
    # Notes made from the audio as it is now, cuts included.
    header = PieceHeader(audio_revision=bundle.read_timeline(part).audio_revision)
    pipeline.save_note_events(part, music(seconds), seconds, "Superestrella", header=header)
    base = on.get(f"/pieces/{part}/notes").json()
    predicted = on.post(f"/pieces/{part}/hands/predict", json={"baseRevision": base["revision"]})
    assert predicted.status_code == 200, predicted.text
    body = predicted.json()
    ops = [
        {"op": "hand", "ids": [i for i, h in zip(body["id"], body["hand"]) if h == hand], "hand": hand}
        for hand in ("r", "l")
    ]
    saved = on.patch(f"/pieces/{part}/notes", json={"baseRevision": base["revision"], "ops": ops})
    assert saved.status_code == 200, saved.text
    assert on.put(f"/time/{part}/rhythm", json=READING).status_code == 200
    assert sheet_state(part, on) == "ready"


def sheet_state(part: str, on: TestClient = client) -> str:
    steps = on.get(f"/pieces/{part}/status").json()["steps"]
    return next(step["state"] for step in steps if step["step"] == "sheet")


def ready_project(seconds: float = 8.0, name: str = "Superestrella.wav") -> str:
    part = uploaded(seconds, name)
    make_ready(part, seconds)
    return part


def save(project: str, on: TestClient = client, **body: object) -> dict:
    answer = on.post(f"/projects/{project}/library", json=body)
    assert answer.status_code == 201, answer.text
    return answer.json()


def layer_of(project: str) -> str:
    with session() as db:
        row = db.get(Project, project)
        assert row is not None
        return row.layer


def notes_of(part: str) -> list[int]:
    return client.get(f"/pieces/{part}/notes").json()["onMs"]


# ------------------------------------------------------------------ saving


def test_save_moves_the_project_into_the_library_under_a_song() -> None:
    part = ready_project()
    folder = paths.project_dir(part)
    assert "/vault/" in str(folder)
    saved = save(part, song="Superestrella", artist="Aitana", version="original")
    assert saved["projectId"] == part
    assert layer_of(part) == "private"
    assert not folder.exists() and "/library/" in str(paths.project_dir(part))
    # The steps still open, with every step ready, and the notes are the same.
    assert sheet_state(part) == "ready"
    songs = client.get("/library/songs").json()
    assert [(row["title"], [a["name"] for a in row["artists"]], row["versions"]) for row in songs] == [
        ("Superestrella", ["Aitana"], 1)
    ]
    song = client.get(f"/library/songs/{saved['songId']}").json()
    assert [(v["name"], v["projectId"], v["step"]) for v in song["versions"]] == [
        ("original", part, "sheet")
    ]
    # It left the Personal Vault, and its row says which song and version it is.
    assert [row["id"] for row in client.get("/projects").json()] == []
    row = client.get(f"/projects/{part}").json()
    assert row["layer"] == "private"
    assert row["library"]["songTitle"] == "Superestrella"
    assert row["library"]["versionName"] == "original"
    entry = client.get(f"/audio/{part}").json()
    assert (entry["projectId"], entry["layer"]) == (part, "private")


def test_save_waits_for_a_saved_piano_sheet() -> None:
    part = uploaded()
    pipeline.save_note_events(part, music(8.0), 8.0, "x")
    answer = client.post(f"/projects/{part}/library", json={"song": "A", "version": "one"})
    assert answer.status_code == 409
    assert "piano sheet" in answer.json()["detail"]
    assert layer_of(part) == "vault"


def test_the_same_song_by_title_and_artist_gets_a_second_version() -> None:
    first = ready_project()
    second = ready_project(name="Other.wav")
    one = save(first, song="Superestrella", artist="Aitana", version="original")
    two = save(second, song="  superestrella ", artist="AITANA", version="easy")
    assert one["songId"] == two["songId"]
    third = ready_project(name="Third.wav")
    taken = client.post(
        f"/projects/{third}/library", json={"songId": one["songId"], "version": "Easy"}
    )
    assert taken.status_code == 409 and "already has a version" in taken.json()["detail"]
    # Another artist: another song with the same title.
    other = save(third, song="Superestrella", artist="Someone else", version="original")
    assert other["songId"] != one["songId"]
    assert len(client.get("/library/artists").json()) == 2


# ---------------------------------------------------------------- the audio (Q-3)


def test_the_audio_is_written_again_with_only_the_ranges_in_use(tmp_path: Path) -> None:
    part = uploaded(8.0)
    original = bundle.read_timeline(part).single_audio
    # Cut 1 s at the start and 2 s in the middle (frames of 10 ms).
    assert client.put(f"/audio/{part}/cuts", json={"cuts": [[0, 100], [400, 600]]}).status_code == 200
    revision = bundle.read_timeline(part).audio_revision
    _, before = formats.read_wav(paths.normalized_path(part))
    kept_before = np.concatenate([before[100 * 160 : 400 * 160], before[600 * 160 :]])
    make_ready(part, 5.0)
    notes_before = notes_of(part)

    save(part, song="Cut song", artist="Aitana", version="original")

    timeline = bundle.read_timeline(part)
    content_hash = timeline.single_audio
    assert content_hash != original
    assert timeline.audio[content_hash].format == "flac"
    assert timeline.audio[content_hash].frames == 500
    assert [(s.from_ms, s.to_ms) for s in timeline.segments] == [(0, 5000)]
    assert timeline.audio_revision == revision  # the audio of the piece did not change
    assert client.get(f"/audio/{part}/cuts").json()["cuts"] == []
    assert audio_files.info(original) is None  # no project uses the original any more
    assert not audio_files.file_path(original, "wav").exists()
    # The engine's audio is the joined audio the notes were made from, to the fade of the join.
    _, after = formats.read_wav(paths.normalized_path(part))
    assert len(after) == 500 * 160
    away_from_join = slice(0, 299 * 160)
    assert np.allclose(after[away_from_join], kept_before[away_from_join], atol=2 / 32767)
    assert notes_of(part) == notes_before
    assert sheet_state(part) == "ready"
    # The new file is a real audio file of 5 s.
    check = tmp_path / "check.wav"
    formats.normalize_to_wav(audio_files.file_path(content_hash, "flac"), check)
    rate, samples = formats.sample_count(check)
    assert abs(samples / rate - 5.0) < 0.01


def test_a_part_of_several_files_keeps_its_files_and_their_names() -> None:
    part = uploaded(4.0, "first.wav")
    added = client.post(
        f"/audio/{part}/add",
        files={"file": ("second.wav", tone_bytes(3.0, 440.0), "audio/wav")},
        data={"name": "The second"},
    )
    assert added.status_code == 201, added.text
    first, second = bundle.read_timeline(part).source_list()
    # The first file whole, and a cut inside the second.
    assert client.put(f"/audio/{part}/cuts", json={"cuts": [[500, 600]]}).status_code == 200
    make_ready(part, 6.0)
    save(part, song="Two files", artist="Aitana", version="original")

    timeline = bundle.read_timeline(part)
    files = timeline.source_list()
    assert files[0] == first and files[1] != second
    assert [timeline.audio[h].frames for h in files] == [400, 200]
    assert client.get(f"/audio/{part}/cuts").json()["cuts"] == []
    names = [row["name"] for row in client.get(f"/audio/{part}/files").json()["files"]]
    assert names == ["first", "The second"]
    _, joined = formats.read_wav(paths.normalized_path(part))
    assert len(joined) == 600 * 160
    assert audio_files.info(second) is None


def test_the_temporary_files_go_on_save() -> None:
    part = ready_project()
    owner = users.ensure_master_user()
    video = paths.tmp_dir() / str(owner) / part / "video"
    video.mkdir(parents=True)
    (video / "source.mp4").write_bytes(b"not a real video")
    staging = paths.project_dir(part) / "staging" / "session"
    staging.mkdir(parents=True)
    part_history = paths.saved_versions_dir(part) / "parts" / part / "v1"
    part_history.mkdir(parents=True)
    save(part, song="Clean", artist="Aitana", version="original")
    assert not (paths.tmp_dir() / str(owner) / part).exists()
    assert not (paths.project_dir(part) / "staging").exists()
    assert not (paths.saved_versions_dir(part) / "parts").exists()
    assert client.get(f"/audio/{part}").json()["hasVideo"] is False


# ------------------------------------------------------------ edit, replace, history


def test_a_version_is_changed_only_through_an_edit_copy() -> None:
    part = ready_project()
    saved = save(part, song="Superestrella", artist="Aitana", version="original")
    # Read only in place: the step routes refuse a change.
    assert client.patch(f"/audio/{part}", json={"alias": "x"}).status_code == 403
    assert client.delete(f"/projects/{part}").status_code == 403
    copy = client.post(f"/projects/{part}/edit")
    assert copy.status_code == 200, copy.text
    copy_row = copy.json()
    assert copy_row["layer"] == "vault" and copy_row["basedOn"] == part
    assert copy_row["editing"]["versionName"] == "original"
    assert copy_row["title"] == "Superestrella"
    # The copy already open is the one Edit opens again.
    assert client.post(f"/projects/{part}/edit").json()["id"] == copy_row["id"]
    song = client.get(f"/library/songs/{saved['songId']}").json()
    assert song["versions"][0]["editCopy"] == copy_row["id"]
    assert client.get("/library/songs").json()[0]["editing"] is True
    # The copy shares the audio: no bytes were copied.
    assert bundle.read_timeline(copy_row["id"]).audio == bundle.read_timeline(part).audio


def test_replace_the_version_keeps_the_ids_and_the_history_restores() -> None:
    part = ready_project()
    saved = save(part, song="Superestrella", artist="Aitana", version="original")
    before = notes_of(part)
    copy = client.post(f"/projects/{part}/edit").json()["id"]
    # Change the notes of the copy: delete the first note, then save its hands and sheet again.
    body = client.get(f"/pieces/{copy}/notes").json()
    edited = client.patch(
        f"/pieces/{copy}/notes",
        json={"baseRevision": body["revision"], "ops": [{"op": "delete", "ids": [body["id"][0]]}]},
    )
    assert edited.status_code == 200, edited.text
    assert client.put(f"/time/{copy}/rhythm", json=READING).status_code == 200
    assert sheet_state(copy) == "ready"
    after_edit = notes_of(copy)
    assert after_edit != before

    replaced = save(copy, replace=True)
    assert replaced == {"songId": saved["songId"], "versionId": saved["versionId"], "projectId": part}
    assert notes_of(part) == after_edit
    assert sheet_state(part) == "ready"
    assert client.get(f"/projects/{copy}").status_code == 404  # the copy is gone
    assert [row["id"] for row in client.get("/projects").json()] == []
    history = client.get(f"/library/versions/{saved['versionId']}/history").json()
    assert [(row["number"], row["reason"]) for row in history] == [(1, "Replaced by an edit")]

    restored = client.post(f"/library/versions/{saved['versionId']}/history/1/restore")
    assert restored.status_code == 200, restored.text
    assert notes_of(part) == before
    history = client.get(f"/library/versions/{saved['versionId']}/history").json()
    assert [row["number"] for row in history] == [2, 1]
    assert restored.json()["versions"][0]["history"] == 2


def test_save_as_a_new_version_from_an_edit_copy() -> None:
    part = ready_project()
    saved = save(part, song="Superestrella", artist="Aitana", version="original")
    copy = client.post(f"/projects/{part}/edit").json()["id"]
    taken = client.post(
        f"/projects/{copy}/library", json={"songId": saved["songId"], "version": "original"}
    )
    assert taken.status_code == 409
    second = save(copy, songId=saved["songId"], version="easy")
    assert second["projectId"] == copy and second["songId"] == saved["songId"]
    assert bundle.read_project(copy).based_on is None
    assert layer_of(copy) == "private"
    names = [v["name"] for v in client.get(f"/library/songs/{saved['songId']}").json()["versions"]]
    assert names == ["original", "easy"]
    # Both projects share the audio, and both still play.
    assert bundle.read_timeline(copy).audio == bundle.read_timeline(part).audio


def test_delete_a_version_and_a_song() -> None:
    part = ready_project()
    saved = save(part, song="Superestrella", artist="Aitana", version="original")
    copy = client.post(f"/projects/{part}/edit").json()["id"]
    content_hash = bundle.read_timeline(part).single_audio
    assert client.delete(f"/library/versions/{saved['versionId']}").status_code == 204
    assert client.get(f"/projects/{part}").status_code == 404
    # The copy stays as a project of its own, and keeps the audio.
    row = client.get(f"/projects/{copy}").json()
    assert row["basedOn"] is None and row["editing"] is None
    assert audio_files.info(content_hash) is not None
    song = client.get(f"/library/songs/{saved['songId']}").json()
    assert song["versions"] == []
    assert client.delete(f"/library/songs/{saved['songId']}").status_code == 204
    assert client.get("/library/songs").json() == []


def test_rename_a_song_and_a_version_and_give_the_song_its_artists() -> None:
    first = save(ready_project(), song="Superestrella", artist="Aitana", version="original")
    song_id = first["songId"]
    renamed = client.patch(f"/library/songs/{song_id}", json={"title": "Superestrella (live)"})
    assert renamed.json()["title"] == "Superestrella (live)"
    both = client.patch(f"/library/songs/{song_id}", json={"artists": ["Aitana", "Lola Índigo"]})
    assert [a["name"] for a in both.json()["artists"]] == ["Aitana", "Lola Índigo"]
    version = client.patch(f"/library/versions/{first['versionId']}", json={"name": "Acoustic"})
    assert version.json()["versions"][0]["name"] == "Acoustic"
    assert client.patch(f"/library/versions/{first['versionId']}", json={"name": " "}).status_code == 422


# -------------------------------------------------------------------- artists


def test_an_artist_has_several_names_and_two_artists_merge() -> None:
    one = save(ready_project(), song="ABC", artist="The Jackson 5", version="original")
    two = save(ready_project(name="b.wav"), song="I want you back", artist="Jackson Five", version="v")
    artists = client.get("/library/artists").json()
    assert [row["name"] for row in artists] == ["Jackson Five", "The Jackson 5"]
    keep = next(row["id"] for row in artists if row["name"] == "The Jackson 5")
    other = next(row["id"] for row in artists if row["name"] == "Jackson Five")

    merged = client.post(f"/library/artists/{other}/merge", json={"into": keep}).json()
    assert merged["name"] == "The Jackson 5"
    assert sorted(n["name"] for n in merged["names"]) == ["Jackson Five", "The Jackson 5"]
    assert merged["songs"] == 2 and [s["title"] for s in merged["songList"]] == ["ABC", "I want you back"]
    assert client.get(f"/library/artists/{other}").status_code == 404
    # A song still shows the name it was saved with.
    song = client.get(f"/library/songs/{two['songId']}").json()
    assert [a["name"] for a in song["artists"]] == ["Jackson Five"]
    assert song["artists"][0]["artistId"] == keep

    added = client.post(f"/library/artists/{keep}/names", json={"name": "Jackson 5"}).json()
    name_id = next(n["id"] for n in added["names"] if n["name"] == "Jackson 5")
    made_default = client.patch(
        f"/library/artists/{keep}/names/{name_id}", json={"isDefault": True}
    ).json()
    assert made_default["name"] == "Jackson 5"
    # A name of this artist now finds it when a song is saved.
    three = save(ready_project(name="c.wav"), song="ABC", artist="jackson 5", version="easy")
    assert three["songId"] == one["songId"]
    # Removing a name moves its songs to the default name; the default cannot be removed.
    five = next(n["id"] for n in made_default["names"] if n["name"] == "Jackson Five")
    assert client.delete(f"/library/artists/{keep}/names/{name_id}").status_code == 409
    assert client.delete(f"/library/artists/{keep}/names/{five}").status_code == 200
    song = client.get(f"/library/songs/{two['songId']}").json()
    assert [a["name"] for a in song["artists"]] == ["Jackson 5"]
    assert client.delete(f"/library/artists/{keep}").status_code == 409  # it has songs


# ---------------------------------------------------------------------- rights


@pytest.mark.real_login
def test_another_user_sees_nothing_of_the_library() -> None:
    master_id = users.ensure_master_user()
    users.set_password(master_id, "master-password")
    users.create_user("anna", "anna-password")

    def signed(name: str, password: str) -> TestClient:
        one = TestClient(create_app())
        assert one.post("/auth/login", json={"username": name, "password": password}).status_code == 200
        return one

    master = signed("master", "master-password")
    anna = signed("anna", "anna-password")
    part = uploaded(on=master)
    make_ready(part, 8.0, on=master)
    saved = save(part, on=master, song="Superestrella", artist="Aitana", version="original")

    assert anna.get("/library/songs").json() == []
    assert anna.get(f"/library/songs/{saved['songId']}").status_code == 404
    assert anna.get(f"/library/versions/{saved['versionId']}/history").status_code == 404
    assert anna.delete(f"/library/versions/{saved['versionId']}").status_code == 404
    assert anna.post(f"/projects/{part}/edit").status_code == 404
    assert anna.get("/library/artists").json() == []
    # The owner reads it and changes it only through a copy.
    assert master.patch(f"/audio/{part}", json={"alias": "x"}).status_code == 403
    assert master.post(f"/projects/{part}/edit").status_code == 200
    with session() as db:
        assert db.scalar(select(Project.layer).where(Project.id == part)) == "private"
