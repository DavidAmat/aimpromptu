"""The reader's own decisions, saved with the piece and read back (P7.10, D-17, D-19, D-34).

Everything else about a score is derived from `events.json` on each request, so it can be thrown
away and rebuilt. What is stored here cannot be: nothing in a recording says which pile of gaps is
the beat, or where a phrase restarts. These tests pin that it survives a round trip, that it is one
per piece, and that a new transcription throws it away rather than pointing it at different notes.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.schemas.rhythm import KeyChange, SavedRhythm, SpeedChange
from aitu_backend.schemas.time_matrix import BeamBreak, FigureName, FigureOverride
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def transcribed(uuid_alias: str = "Piece") -> str:
    """An audio with recorded notes but no matrices, which is the whole stored form now."""
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create(uuid_alias, AudioSource.UPLOAD, "wav")
    pipeline.save_note_events(
        entry.uuid,
        [
            NoteEvent(midi_note=60 + index % 5, start=index * 0.32, end=index * 0.32 + 0.2)
            for index in range(8)
        ],
        duration_seconds=3.0,
        title=uuid_alias,
    )
    return entry.uuid


def a_reading(anchor_ms: float = 320.0) -> SavedRhythm:
    return SavedRhythm(
        hand="right",
        frame_ms=40,
        anchor_figure=FigureName.NEGRA,
        anchor_ms=anchor_ms,
        speed_changes=[SpeedChange(start_frame=144, anchor_ms=674.0)],
        overrides=[
            FigureOverride(hand="right", row=39, start_frame=8, figure=FigureName.SEMICORCHEA)
        ],
        beam_breaks=[BeamBreak(hand="left", start_frame=24)],
        key_signature="Bb",
        key_changes=[
            KeyChange(from_column=40, key_signature="D"),
            KeyChange(from_column=80, key_signature="Bb"),
        ],
    )


# ------------------------------------------------------------------------------- the round trip


def test_a_reading_comes_back_exactly_as_it_was_saved(client: TestClient) -> None:
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    read = client.get(f"/time/{uuid}/rhythm").json()

    assert read["anchorFigure"] == "negra"
    assert read["anchorMs"] == 320.0
    assert read["frameMs"] == 40
    assert read["keySignature"] == "Bb"
    assert read["keyChanges"] == [
        {"fromColumn": 40, "keySignature": "D"},
        {"fromColumn": 80, "keySignature": "Bb"},
    ]
    assert read["speedChanges"] == [{"startFrame": 144, "anchorMs": 674.0}]
    assert read["overrides"] == [
        {"hand": "right", "row": 39, "startFrame": 8, "figure": "semicorchea"}
    ]
    assert read["beamBreaks"] == [{"hand": "left", "startFrame": 24}]


def test_a_piece_with_no_saved_reading_says_so_rather_than_inventing_one(
    client: TestClient,
) -> None:
    """The screen starts from the plot when it gets this, which is the right blank state."""
    uuid = transcribed()
    response = client.get(f"/time/{uuid}/rhythm")
    assert response.status_code == 404
    assert "Name a gap" in response.json()["detail"]


def test_saving_twice_replaces_rather_than_accumulating(client: TestClient) -> None:
    """A rhythm is a decision, not a version. What a reader wants back is the last one."""
    uuid = transcribed()
    client.put(f"/time/{uuid}/rhythm", json=a_reading(320.0).model_dump(by_alias=True, mode="json"))
    client.put(f"/time/{uuid}/rhythm", json=a_reading(337.0).model_dump(by_alias=True, mode="json"))

    assert client.get(f"/time/{uuid}/rhythm").json()["anchorMs"] == 337.0
    assert len(list(pipeline.matrices_dir(uuid).glob("rhythm*.json"))) == 1


def test_a_reading_can_be_forgotten(client: TestClient) -> None:
    uuid = transcribed()
    client.put(f"/time/{uuid}/rhythm", json=a_reading().model_dump(by_alias=True, mode="json"))
    assert client.delete(f"/time/{uuid}/rhythm").status_code == 204
    assert client.get(f"/time/{uuid}/rhythm").status_code == 404


# ------------------------------------------------------------------------------- the guards


def test_a_rhythm_for_an_unknown_audio_is_a_404(client: TestClient) -> None:
    assert client.get("/time/nope/rhythm").status_code == 404
    assert (
        client.put("/time/nope/rhythm", json=a_reading().model_dump(by_alias=True, mode="json"))
    ).status_code == 404


def test_a_rhythm_cannot_be_saved_for_a_piece_that_was_never_transcribed(
    client: TestClient,
) -> None:
    """There would be nothing for the column numbers in it to refer to."""
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create("Silent", AudioSource.UPLOAD, "wav")
    response = client.put(
        f"/time/{entry.uuid}/rhythm", json=a_reading().model_dump(by_alias=True, mode="json")
    )
    assert response.status_code == 409
    assert "not been transcribed" in response.json()["detail"]


def test_transcribing_again_throws_the_reading_away(temp_store: Path) -> None:
    """The columns in a saved reading describe the notes that were there before.

    A new transcription is a different set of notes, so keeping the numbers would point them at
    music nobody chose. Better to ask the reader to name the gap again than to show them a reading
    that is quietly about something else.
    """
    uuid = transcribed()
    pipeline.save_rhythm(uuid, a_reading())
    assert pipeline.load_rhythm(uuid) is not None

    class OneNote:
        name = "stub"

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            return [NoteEvent(midi_note=60, start=0.0, end=0.5)]

    from aitu_backend.audio import store

    entry = store.get(uuid)
    entry.directory.mkdir(parents=True, exist_ok=True)
    entry.normalized_path.write_bytes(b"")

    pipeline.transcribe_audio(uuid, engine=OneNote())
    assert pipeline.load_rhythm(uuid) is None


def test_a_file_written_by_an_older_shape_reads_as_nothing_saved(temp_store: Path) -> None:
    """Losing a reading is a nuisance; refusing to open the piece over it would be worse."""
    uuid = transcribed()
    pipeline.rhythm_path(uuid).parent.mkdir(parents=True, exist_ok=True)
    pipeline.rhythm_path(uuid).write_text('{"anchorFigure": "negra"}', encoding="utf-8")
    assert pipeline.load_rhythm(uuid) is None


def test_the_reading_describes_itself_for_a_log(temp_store: Path) -> None:
    text = a_reading().describe()
    assert "negra = 320 ms at 40 ms/col" in text
    assert "1 speed change(s)" in text
    assert "1 note(s) renamed" in text
    assert "1 beam break(s)" in text


def test_a_reading_saved_before_keys_existed_still_loads(client: TestClient) -> None:
    """A stored file with no `keySignature` is not a broken file.

    The field was added after readings were already on disk, and a piece read in C is exactly what
    those readings were drawn in, so the absent value and C mean the same thing.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    del body["keySignature"]
    del body["keyChanges"]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    read = client.get(f"/time/{uuid}/rhythm").json()

    assert read["keySignature"] is None
    assert read["keyChanges"] == []
    assert read["anchorMs"] == 320.0


def test_octave_brackets_survive_a_round_trip(client: TestClient) -> None:
    """Brackets the reader placed come back, which they did not before 2026-09-13.

    The page has always *sent* `ottavas` in the save body. The model had no field for them and
    Pydantic ignores extras, so every bracket was dropped without an error and a reload showed a
    page with none. Nothing failed and nothing said so, which is why it lasted a month.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["ottavas"] = [
        {"kind": "8va", "hand": "right", "fromColumn": 12, "toColumn": 40, "hidden": False},
        {"kind": "15mb", "hand": "left", "fromColumn": 0, "toColumn": 12, "hidden": False},
    ]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    read = client.get(f"/time/{uuid}/rhythm").json()

    assert read["ottavas"] == body["ottavas"]


def test_a_hidden_bracket_comes_back_hidden(client: TestClient) -> None:
    """Hiding a bracket is a reading, so it is stored with the rest of one.

    The reader takes the dashed line off the page and the notes stay written an octave from where
    they sound. A reading that lost the flag would come back with every bracket drawn again — the
    one thing the reader had already said they did not want — while a reading that lost the bracket
    instead would come back with a wall of ledger lines. Both halves have to survive together.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["ottavas"] = [
        {"kind": "8va", "hand": "right", "fromColumn": 12, "toColumn": 40, "hidden": True},
    ]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    read = client.get(f"/time/{uuid}/rhythm").json()

    assert read["ottavas"][0]["hidden"] is True
    assert read["ottavas"][0]["kind"] == "8va"
    assert read["ottavas"][0]["toColumn"] == 40


def test_a_bracket_saved_before_hiding_existed_reads_as_drawn(client: TestClient) -> None:
    """A reading written before the flag had no way of saying so, and it meant drawn."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["ottavas"] = [{"kind": "8va", "hand": "right", "fromColumn": 12, "toColumn": 40}]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200

    assert client.get(f"/time/{uuid}/rhythm").json()["ottavas"][0]["hidden"] is False


def test_never_asked_and_asked_none_are_different_answers(client: TestClient) -> None:
    """`null` is "this reader was never asked"; `[]` is "asked, and none".

    The distinction is load-bearing rather than tidy. A reading saved before brackets were stored
    has no opinion, and the page may offer its own; a reader who cleared every bracket has one, and
    the page must not put them back.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body.pop("ottavas", None)
    client.put(f"/time/{uuid}/rhythm", json=body)
    assert client.get(f"/time/{uuid}/rhythm").json()["ottavas"] is None

    body["ottavas"] = []
    client.put(f"/time/{uuid}/rhythm", json=body)
    assert client.get(f"/time/{uuid}/rhythm").json()["ottavas"] == []


def test_a_bracket_that_ends_before_it_starts_is_refused(client: TestClient) -> None:
    """An inverted range reads as empty everywhere downstream, which is not a thing to store."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["ottavas"] = [{"kind": "8va", "hand": "right", "fromColumn": 40, "toColumn": 12}]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


def test_the_space_between_lines_survives_a_round_trip(client: TestClient) -> None:
    """How far apart the lines are drawn is a reading, so it is stored with the rest of one.

    A reader sets it because one fixed gap cannot be right for every piece: most sheets are mostly
    white space at it, and on a piece with high notes a low note of the left hand and a high note of
    the next line's right hand reach towards each other through it. Losing it on every reload would
    make the control not worth having, which is exactly what happened to octave brackets above.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["lineSpacing"] = 64

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["lineSpacing"] == 64


def test_a_reading_saved_before_the_spacing_existed_leaves_it_to_the_page(
    client: TestClient,
) -> None:
    """Absent means nobody was asked, and the page draws it with its own default.

    Stored as `null` rather than as the default number, for the same reason `ottavas` distinguishes
    the two: a value on disk says a reader chose it, and the page's own default may change.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body.pop("lineSpacing", None)

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["lineSpacing"] is None


def test_a_space_between_lines_no_drawing_could_use_is_refused(client: TestClient) -> None:
    """Out of range is a mistake, and a stored mistake would take the sheet down on every visit."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["lineSpacing"] = -1
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["lineSpacing"] = 400
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


def test_a_spread_line_survives_a_round_trip(client: TestClient) -> None:
    """One line opened out is a reading, and readings are stored.

    It is per line rather than per page because the reason for wanting it is per line: one wide
    chord needs room that every other line on the score would only waste. And it is keyed by a
    column rather than by a place down the page, because the sheet re-wraps to the window and "the
    third line" is different music at another width.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["staffGaps"] = [{"fromColumn": 0, "gap": 96}, {"fromColumn": 48, "gap": 64}]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["staffGaps"] == body["staffGaps"]


def test_a_reading_with_no_spread_line_reads_as_none(client: TestClient) -> None:
    """The common case, and the one every reading saved before this existed is in."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body.pop("staffGaps", None)

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["staffGaps"] == []


def test_a_spread_no_drawing_could_use_is_refused(client: TestClient) -> None:
    """The bounds are the drawing package's own, so a stored answer is always one it can draw."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["staffGaps"] = [{"fromColumn": 0, "gap": 10}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["staffGaps"] = [{"fromColumn": 0, "gap": 400}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["staffGaps"] = [{"fromColumn": -1, "gap": 96}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


def test_the_tightest_line_the_page_can_draw_is_saveable(client: TestClient) -> None:
    """The floor here has to be the one the handle on the page stops at, which is 24 px.

    ``MIN_STAFF_GAP`` in the drawing package is ``MIN_STAFF_GAP_SPACES`` (3) staff spaces of 8 px.
    This read 30 and a reader found what that costs: tighten one line past 30 and the whole reading
    became unsaveable — every later save of that piece answered 422 about a field the reader was not
    editing, so a figure renamed an hour later could not be kept either. A bound tighter than the
    one the page enforces is a trap rather than a validation.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["staffGaps"] = [{"fromColumn": 0, "gap": 24}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["staffGaps"] == body["staffGaps"]
    # And still nothing the page could never produce.
    body["staffGaps"] = [{"fromColumn": 0, "gap": 20}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


# ----------------------------------------------------- the clef, the joins and the note spacing


def test_a_clef_change_survives_a_round_trip(client: TestClient) -> None:
    """Which clef a hand prints is a reading, so it is stored with the rest of one.

    A left hand that spends a page above middle C reads better on a treble clef than under a stack
    of ledger lines or an octave bracket, and nothing in a recording says which of the three a
    reader wants. Stored as transitions, exactly as the key is: at any column each hand prints one
    clef, so two edits can never disagree about what is on the page.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["clefChanges"] = [
        {"hand": "left", "fromColumn": 40, "clef": "treble"},
        {"hand": "left", "fromColumn": 96, "clef": "bass"},
    ]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["clefChanges"] == body["clefChanges"]


def test_a_reading_with_no_clef_change_reads_as_the_two_a_piano_score_uses(
    client: TestClient,
) -> None:
    """The common case, and the one every reading saved before this existed is in."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body.pop("clefChanges", None)

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["clefChanges"] == []


def test_a_clef_nothing_could_print_is_refused(client: TestClient) -> None:
    """Two clefs exist on this page. A stored third would take the sheet down on every visit."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["clefChanges"] = [{"hand": "left", "fromColumn": 40, "clef": "alto"}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["clefChanges"] = [{"hand": "middle", "fromColumn": 40, "clef": "treble"}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


def test_beam_joins_survive_a_round_trip(client: TestClient) -> None:
    """The other half of a beam break, and it cannot be derived any more than a break can.

    Where a phrase restarts is a reading of the music and is stored as a break. Where it *does not*
    — a run the automatic rule would cut at its lowest note, which the player hears as one gesture —
    is the same kind of statement in the other direction, and is stored the same way.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["beamJoins"] = [
        {"hand": "right", "startFrame": 12},
        {"hand": "right", "startFrame": 16},
    ]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["beamJoins"] == body["beamJoins"]


def test_the_space_between_notes_survives_a_round_trip(client: TestClient) -> None:
    """The twin of the space between lines, one axis over, and stored for the same reason."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["noteSpacing"] = 14

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["noteSpacing"] == 14


def test_a_reading_saved_before_the_note_spacing_existed_leaves_it_to_the_page(
    client: TestClient,
) -> None:
    """Absent means nobody was asked, exactly as it does for the space between lines."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body.pop("noteSpacing", None)

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["noteSpacing"] is None


def test_a_space_between_notes_no_drawing_could_use_is_refused(client: TestClient) -> None:
    """Out of range is a mistake, and a stored mistake would take the sheet down on every visit."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["noteSpacing"] = -1
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["noteSpacing"] = 200
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


def test_an_even_spacing_run_survives_a_round_trip(client: TestClient) -> None:
    """A run set an equal distance apart is a reading, so it is stored with the rest of one.

    Nothing in a recording says whether a beam should be drawn evenly. The page measures each column
    from what is drawn in it and both staves share the column, so a run of even corcheas comes out
    unevenly spaced wherever the other hand needs room — which is truthful and reads as an uneven
    performance. Which of the two a reader prefers is theirs alone.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["evenSpacings"] = [
        {"hand": "right", "fromColumn": 8, "toColumn": 24, "scale": 1.0},
        {"hand": "left", "fromColumn": 40, "toColumn": 56, "scale": 1.6},
    ]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["evenSpacings"] == body["evenSpacings"]


def test_an_even_spacing_tighter_than_the_page_measured_is_kept(client: TestClient) -> None:
    """A run closed below one is the reader saying their own hand has room to spare.

    The widest gap in a run is usually wide because of the *other* hand, so evening a run to it makes
    the whole run as wide as its worst moment. Refusing to store the answer would be the file
    second-guessing something the reader can see on the page in front of them.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["evenSpacings"] = [{"hand": "right", "fromColumn": 8, "toColumn": 24, "scale": 0.55}]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["evenSpacings"] == body["evenSpacings"]


def test_an_even_spacing_no_drawing_could_use_is_refused(client: TestClient) -> None:
    """The bounds are the drawing package's own, so a stored answer is always one it can draw."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["evenSpacings"] = [{"hand": "right", "fromColumn": 8, "toColumn": 24, "scale": 0.1}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["evenSpacings"] = [{"hand": "right", "fromColumn": 8, "toColumn": 24, "scale": 9}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["evenSpacings"] = [{"hand": "right", "fromColumn": 24, "toColumn": 8, "scale": 1}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422


def test_a_reading_with_no_even_spacing_reads_as_none(client: TestClient) -> None:
    """The common case, and the one every reading saved before this existed is in."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body.pop("evenSpacings", None)

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    assert client.get(f"/time/{uuid}/rhythm").json()["evenSpacings"] == []


def test_where_a_lyric_was_placed_survives_a_round_trip(client: TestClient) -> None:
    """Where the words were dragged to, how wide the block was left and how large they print.

    A lyric is a block the reader moves and resizes now, so the placement is as much a decision
    about the piece as the words themselves — and nothing in a recording says any of it.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["lyrics"] = [
        {
            "fromColumn": 8,
            "toColumn": 24,
            "text": "do re mi",
            "offsetX": 42.5,
            "offsetY": -18.0,
            "width": 160.0,
            "fontSize": 18.0,
        }
    ]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    stored = client.get(f"/time/{uuid}/rhythm").json()["lyrics"][0]
    assert stored["offsetX"] == 42.5
    assert stored["offsetY"] == -18.0
    assert stored["width"] == 160.0
    assert stored["fontSize"] == 18.0


def test_a_lyric_nobody_has_moved_reads_back_with_no_placement(client: TestClient) -> None:
    """Absent is a block the page puts where it likes, which is what every older reading holds."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    body["lyrics"] = [{"fromColumn": 8, "toColumn": 24, "text": "do re mi"}]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    stored = client.get(f"/time/{uuid}/rhythm").json()["lyrics"][0]
    assert stored["offsetX"] is None
    assert stored["offsetY"] is None
    assert stored["width"] is None
    assert stored["fontSize"] is None


def test_a_lyric_block_no_drawing_could_use_is_refused(client: TestClient) -> None:
    """The bounds are the drawing package's own, so a stored mistake cannot reach the sheet."""
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    body["lyrics"] = [{"fromColumn": 8, "toColumn": 24, "text": "do re mi", "width": 4.0}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
    body["lyrics"] = [{"fromColumn": 8, "toColumn": 24, "text": "do re mi", "fontSize": 96.0}]
    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 422
