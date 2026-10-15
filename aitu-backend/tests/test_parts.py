"""From other projects, and the parts of a project (implementation 02, Phase 10, plan sections
8.4, 10.4 and 14.1).

A project made of passages of other projects is a run of pastes into empty parts: one part per run
of sequential passages, a new part at each subheader. These tests pin what the reader sees: the
notes, the key and the audio of each passage where it lands, the parts in their order with their
titles, and the joins and splits that move music between parts without losing a note.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from aitu_backend.audio import formats, store
from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import Part, Project
from aitu_backend.editing import paste
from aitu_backend.main import create_app
from aitu_backend.schemas.rhythm import Fingering
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription import pipeline
from test_paste import note, pitch_at, sheet, tone_part


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture()
def sources(tmp_path: Path) -> tuple[str, str]:
    """``A``: 8 s at 440 Hz in Bb, a note every second from Do-5; ``B``: 6 s at 220 Hz in C, a note
    every second from Do-4."""
    first = tone_part(
        tmp_path, "Clocks", 8.0, 440.0, [note(72 + i, i * 1.0, i * 1.0 + 0.5) for i in range(8)]
    )
    pipeline.save_rhythm(
        first,
        sheet(
            keySignature="Bb",
            fingers=[Fingering(hand="right", startFrame=75, row=75 - 21, finger=3)],
        ),
    )
    second = tone_part(
        tmp_path, "Yellow", 6.0, 220.0, [note(60 + i, i * 1.0, i * 1.0 + 0.5) for i in range(6)]
    )
    pipeline.save_rhythm(second, sheet(keySignature="C"))
    return first, second


def starts(part: str) -> list[tuple[int, float]]:
    events = pipeline.load_note_events(part)
    assert events is not None
    return [(event.midi_note, round(event.start, 3)) for event in events.events]


def parts_of(client: TestClient, project: str) -> list[tuple[str, str | None, float]]:
    answer = client.get(f"/projects/{project}/parts")
    assert answer.status_code == 200, answer.text
    return [(row["id"], row["subheader"], row["durationMs"]) for row in answer.json()["parts"]]


def compose(client: TestClient, **body: object) -> dict:
    answer = client.post("/projects/compose", json=body)
    assert answer.status_code == 201, answer.text
    return answer.json()


def step_state(client: TestClient, part: str, step: str) -> str:
    steps = client.get(f"/pieces/{part}/status").json()["steps"]
    return next(item["state"] for item in steps if item["step"] == step)


# ------------------------------------------------------------------ From other projects


def test_from_other_projects_makes_one_part_per_subheader(
    client: TestClient, sources: tuple[str, str]
) -> None:
    clocks, yellow = sources
    before = {clocks: starts(clocks), yellow: starts(yellow)}
    row = compose(
        client,
        title="Coldplay mashup",
        kind="integratedPlaylist",
        passages=[
            {"part": clocks, "fromMs": 2000, "toMs": 4000},
            {"part": yellow, "join": "sequential"},
            {"part": clocks, "fromMs": 0, "toMs": 1000, "join": "subheader", "subheader": "Coda"},
        ],
    )
    assert row["kind"] == "integratedPlaylist" and row["title"] == "Coldplay mashup"
    project = row["id"]
    found = parts_of(client, project)
    assert [(subheader, length) for _, subheader, length in found] == [
        ("Clocks", 8000.0),
        ("Coda", 1000.0),
    ]
    first, second = found[0][0], found[1][0]
    assert first == project and row["parts"] == [first, second]

    # The first part: Clocks 0:02–0:04, then the whole of Yellow, one piano matrix.
    assert starts(first) == [(74, 0.0), (75, 1.0)] + [(60 + i, 2.0 + i) for i in range(6)]
    assert starts(second) == [(72, 0.0)]
    saved = pipeline.load_rhythm(first)
    assert saved is not None
    # It reads in Bb as Clocks did, then in C where Yellow starts (column 50 = 2 s).
    assert saved.key_signature == "Bb"
    assert [(c.from_column, c.key_signature) for c in saved.key_changes] == [(50, "C")]
    # Clocks' fingering at 3 s is 1 s into the passage.
    assert [(f.start_frame, f.row) for f in saved.fingers] == [(25, 75 - 21)]
    # Every step is ready: the parts open on their Sheet step.
    for part in (first, second):
        assert step_state(client, part, "sheet") == "ready"

    # The audio is ranges of the stored files, none copied: 440 Hz, then 220 Hz from 2 s.
    used = set(bundle.read_timeline(first).audio) | set(bundle.read_timeline(second).audio)
    stored = set(bundle.read_timeline(clocks).audio) | set(bundle.read_timeline(yellow).audio)
    assert used <= stored
    rate, samples = formats.read_wav(store.get(first).normalized_path)
    assert len(samples) == 8 * rate
    for seconds, pitch in ((0.5, 440), (1.5, 440), (2.5, 220), (7.5, 220)):
        assert pitch_at(samples, rate, seconds) == pytest.approx(pitch, abs=12), seconds

    # The sources did not change; the project says what it was made from and keeps no history.
    assert {clocks: starts(clocks), yellow: starts(yellow)} == before
    origin = bundle.read_project(project).origin or {}
    assert [(one["part"], one["join"]) for one in origin["composedFrom"]] == [
        (clocks, "sequential"),
        (yellow, "sequential"),
        (clocks, "subheader"),
    ]
    assert not (paths.history_dir() / project).exists()
    listed = {item["id"]: item for item in client.get("/projects").json()}
    assert listed[project]["kind"] == "integratedPlaylist"


def test_a_song_of_one_part_has_no_subheader(client: TestClient, sources: tuple[str, str]) -> None:
    clocks, yellow = sources
    row = compose(
        client,
        title="Two songs",
        passages=[{"part": yellow, "fromMs": 0, "toMs": 2000}, {"part": clocks}],
    )
    assert row["kind"] == "song"
    assert [(subheader, length) for _, subheader, length in parts_of(client, row["id"])] == [
        (None, 10000.0)
    ]


def test_a_passage_that_cannot_be_put_in_leaves_nothing_behind(
    client: TestClient, sources: tuple[str, str]
) -> None:
    clocks, _ = sources
    empty = bundle.create_project(owner_id=users.ensure_master_user(), title="Nothing yet").id
    listed = {item["id"] for item in client.get("/projects").json()}
    answer = client.post(
        "/projects/compose",
        json={"title": "x", "passages": [{"part": clocks}, {"part": empty}]},
    )
    assert answer.status_code == 409, answer.text
    assert "nothing in it" in answer.json()["detail"]
    assert {item["id"] for item in client.get("/projects").json()} == listed
    missing = client.post(
        "/projects/compose", json={"title": "x", "passages": [{"part": "not-a-part"}]}
    )
    assert missing.status_code == 404


# ------------------------------------------------------------------ the parts


def test_parts_are_renamed_reordered_joined_and_split(
    client: TestClient, sources: tuple[str, str]
) -> None:
    clocks, yellow = sources
    row = compose(
        client,
        title="Medley",
        kind="integratedPlaylist",
        passages=[
            {"part": clocks, "fromMs": 0, "toMs": 2000},
            {"part": yellow, "fromMs": 0, "toMs": 2000, "join": "subheader"},
            {"part": clocks, "fromMs": 4000, "toMs": 6000, "join": "subheader"},
        ],
    )
    project = row["id"]
    one, two, three = (part for part, _, _ in parts_of(client, project))

    renamed = client.patch(f"/projects/{project}/parts/{two}", json={"subheader": "  Bridge  "})
    assert renamed.status_code == 200
    assert [subheader for _, subheader, _ in parts_of(client, project)] == [
        "Clocks",
        "Bridge",
        "Clocks",
    ]

    moved = client.put(f"/projects/{project}/parts", json={"order": [three, one, two]})
    assert moved.status_code == 200, moved.text
    assert [part for part, _, _ in parts_of(client, project)] == [three, one, two]
    with session() as db:
        positions = dict(
            db.execute(select(Part.id, Part.position).where(Part.project_id == project)).all()
        )
    assert positions == {three: 0, one: 1, two: 2}
    assert client.get(f"/projects/{project}").json()["parts"] == [three, one, two]
    bad = client.put(f"/projects/{project}/parts", json={"order": [three, one]})
    assert bad.status_code == 422

    # Joining the project's own part to the one before it keeps the project's part: the music of
    # the part before goes in at its start.
    joined = client.post(f"/projects/{project}/parts/{one}/join")
    assert joined.status_code == 200, joined.text
    assert joined.json()["part"] == one
    assert [(p, s, d) for p, s, d in parts_of(client, project)] == [
        (one, "Clocks", 4000.0),
        (two, "Bridge", 2000.0),
    ]
    assert starts(one) == [(76, 0.0), (77, 1.0), (72, 2.0), (73, 3.0)]
    assert not paths.part_dir(one).parent.joinpath(three).exists()
    with session() as db:
        assert db.get(Part, three) is None

    # Split at 2 s: what follows becomes a new part right after it.
    split = client.post(
        f"/projects/{project}/parts/{one}/split", json={"atMs": 2000, "subheader": "Again"}
    )
    assert split.status_code == 200, split.text
    new = split.json()["part"]
    assert [(p, s, d) for p, s, d in parts_of(client, project)] == [
        (one, "Clocks", 2000.0),
        (new, "Again", 2000.0),
        (two, "Bridge", 2000.0),
    ]
    assert starts(one) == [(76, 0.0), (77, 1.0)]
    assert starts(new) == [(72, 0.0), (73, 1.0)]
    rate, samples = formats.read_wav(store.get(new).normalized_path)
    assert pitch_at(samples, rate, 0.5) == pytest.approx(440, abs=12)
    for part in (one, new):
        assert step_state(client, part, "sheet") == "ready"

    # A split must fall inside the part; the first part has nothing before it to join.
    assert (
        client.post(f"/projects/{project}/parts/{one}/split", json={"atMs": 5000}).status_code
        == 409
    )
    assert client.post(f"/projects/{project}/parts/{one}/join").status_code == 409
    other = compose(client, title="Other", passages=[{"part": yellow}])["id"]
    assert client.post(f"/projects/{project}/parts/{other}/join").status_code == 404


def test_a_version_of_the_library_does_not_change_its_parts(client: TestClient) -> None:
    owner = users.ensure_master_user()
    library = bundle.create_project(owner_id=owner, title="Kept", layer="private").id
    assert (
        client.patch(f"/projects/{library}/parts/{library}", json={"subheader": "x"}).status_code
        == 403
    )
    assert client.put(f"/projects/{library}/parts", json={"order": [library]}).status_code == 403
    assert client.get(f"/projects/{library}/parts").status_code == 200


def test_the_part_that_carries_the_projects_id_stays(sources: tuple[str, str]) -> None:
    clocks, _ = sources
    with pytest.raises(ValueError):
        bundle.remove_part(clocks, clocks)
    with session() as db:
        assert db.get(Project, clocks) is not None


# ------------------------------------------------------------------ the cut


def test_a_cut_takes_a_stretch_out_and_moves_what_follows(
    client: TestClient, sources: tuple[str, str]
) -> None:
    clocks, _ = sources
    files = {
        name: (paths.part_dir(clocks) / name).read_bytes()
        for name in ("notes.pmn", "sheet.json", "timeline.json")
    }
    done = paste.cut(clocks, 2000, 4000)
    assert (done.from_ms, done.to_ms, done.notes_removed) == (2000, 4000, 2)
    assert starts(clocks) == [(72, 0.0), (73, 1.0), (76, 2.0), (77, 3.0), (78, 4.0), (79, 5.0)]
    assert done.duration_seconds == pytest.approx(6.0)
    # The fingering at 3 s was inside the stretch; the audio of the stretch is a cut.
    saved = pipeline.load_rhythm(clocks)
    assert saved is not None and saved.fingers == []
    assert bundle.cuts_of(bundle.read_timeline(clocks)) == [(200, 400)]
    assert step_state(client, clocks, "sheet") == "ready"
    # Undone like a paste: the part comes back to the byte.
    assert client.post(f"/time/{clocks}/versions/{done.before_version}/restore").status_code == 200
    for name, body in files.items():
        assert (paths.part_dir(clocks) / name).read_bytes() == body, name
