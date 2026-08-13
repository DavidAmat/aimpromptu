"""Trills: two pitches alternating quickly, suggested as a ``tr`` rather than printed as a storm.

Detection is a suggestion. A missed trill costs nothing; a wrong one hides real notes. The rule
is therefore narrow: one hand, two pitches a whole tone or closer, at least six alternations,
even gaps, each short enough to be an ornament.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.matrix.keys import midi_to_row
from aitu_backend.matrix.ladder import build_ladder
from aitu_backend.notation.trills import (
    apply_trills,
    find_trills,
    find_trills_in_hands,
    to_trill_mark,
)
from aitu_backend.schemas.time_matrix import FigureName, TrillMark
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import impose_granularity_and_split, to_score_payload
from aitu_backend.storage import paths

LOWER = 72  # Do-5
UPPER = 74  # Re-5
GAP_S = 0.08
NOTE_S = 0.05


def strike(midi: int, start: float, hand: str = "right") -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start, end=start + NOTE_S, hand=hand)


def alternation(count: int, *, start: float = 0.4, gap: float = GAP_S, hand: str = "right"):
    """``count`` notes alternating lower/upper, starting on the lower pitch."""
    return [
        strike(LOWER if index % 2 == 0 else UPPER, start + index * gap, hand)
        for index in range(count)
    ]


# --------------------------------------------------------------------------- the rule


def test_six_alternations_of_a_whole_tone_are_a_trill():
    """Seven notes, six pitch changes: the minimum the task asks for."""
    found = find_trills(alternation(7))
    assert len(found) == 1
    assert found[0].alternations == 6
    assert found[0].lower_midi == LOWER
    assert found[0].upper_midi == UPPER
    assert found[0].hand == "right"


def test_five_alternations_are_not_a_trill():
    """A mordent or a short turn is left as written."""
    assert find_trills(alternation(6)) == []


def test_a_little_human_unevenness_is_still_a_trill():
    times = [0.40, 0.475, 0.560, 0.635, 0.720, 0.800, 0.875]
    events = [strike(LOWER if index % 2 == 0 else UPPER, time) for index, time in enumerate(times)]
    assert len(find_trills(events)) == 1


def test_uneven_gaps_are_not_a_trill_however_fast_they_are():
    times = [0.40, 0.46, 0.60, 0.66, 0.80, 0.86, 1.00]
    events = [strike(LOWER if index % 2 == 0 else UPPER, time) for index, time in enumerate(times)]
    assert find_trills(events) == []


def test_a_minor_third_is_not_a_trill():
    events = [
        strike(LOWER if index % 2 == 0 else LOWER + 3, 0.4 + index * GAP_S) for index in range(8)
    ]
    assert find_trills(events) == []


def test_a_repeated_note_is_not_a_trill():
    events = [strike(LOWER, 0.4 + index * GAP_S) for index in range(8)]
    assert find_trills(events) == []


def test_a_slow_alternation_is_not_a_trill():
    """200 ms is a measured figure, not an ornament."""
    assert find_trills(alternation(8, gap=0.20)) == []


def test_a_chord_is_not_a_trill():
    """Near-simultaneous notes are one attack, not an alternation."""
    events = []
    clock = 0.4
    for index in range(8):
        events.append(strike(LOWER if index % 2 == 0 else UPPER, clock))
        clock += 0.010
    assert find_trills(events) == []


def test_two_hands_are_scanned_separately():
    right = alternation(8, start=0.4, hand="right")
    # A different pair, so the two streams cannot merge into one.
    left = [strike(48 if index % 2 == 0 else 50, 0.41 + index * GAP_S, "left") for index in range(8)]
    found = find_trills(right + left)
    assert {trill.hand for trill in found} == {"right", "left"}


def test_runs_do_not_overlap():
    """Sixteen notes of one trill are one run, not two sliding windows."""
    found = find_trills(alternation(16))
    assert len(found) == 1
    assert found[0].note_count == 16


def test_a_removed_note_does_not_join_a_trill():
    events = alternation(8)
    events[3] = events[3].model_copy(update={"removed": True})
    assert find_trills(events) == []


# --------------------------------------------------------------------------- the page


def test_accepting_a_trill_prints_one_held_lower_note():
    """The storm leaves the page; one lower pitch remains, held for the run."""
    after = strike(76, 0.4 + 8 * GAP_S + 0.3)
    events = alternation(8) + [after]
    hands = impose_granularity_and_split(events, duration_seconds=2.0)
    found = find_trills_in_hands(events, hands)
    assert len(found) == 1
    mark = to_trill_mark(found[0])

    before = to_score_payload(hands, build_ladder(FigureName.NEGRA, 320.0))
    storm = [
        note
        for note in before.notes
        if note.hand == "right" and note.row in {midi_to_row(LOWER), midi_to_row(UPPER)}
    ]
    assert len(storm) >= 7

    collapsed = apply_trills(hands, [mark])
    after_score = to_score_payload(collapsed, build_ladder(FigureName.NEGRA, 320.0))
    remaining = [
        note
        for note in after_score.notes
        if note.hand == "right"
        and note.row in {midi_to_row(LOWER), midi_to_row(UPPER)}
        and mark.from_column <= note.start_frame < mark.to_column
    ]
    assert len(remaining) == 1
    assert remaining[0].row == midi_to_row(LOWER)
    assert remaining[0].start_frame == mark.from_column


def test_the_recording_is_untouched_when_a_trill_is_applied():
    events = alternation(8)
    hands = impose_granularity_and_split(events, duration_seconds=2.0)
    found = find_trills_in_hands(events, hands)
    original_onsets = int((hands.right.grid == 1).sum())
    apply_trills(hands, [to_trill_mark(found[0])])
    assert int((hands.right.grid == 1).sum()) == original_onsets


def test_trill_mark_round_trips_through_the_schema():
    mark = TrillMark(
        hand="right",
        from_column=10,
        to_column=18,
        lower_row=51,
        upper_row=53,
        alternations=6,
    )
    dumped = mark.model_dump(by_alias=True)
    assert dumped == {
        "hand": "right",
        "fromColumn": 10,
        "toColumn": 18,
        "lowerRow": 51,
        "upperRow": 53,
        "alternations": 6,
    }
    assert TrillMark.model_validate(dumped) == mark


# --------------------------------------------------------------------------- over HTTP


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def transcribed_trill() -> str:
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource
    from aitu_backend.transcription import pipeline

    entry = store.create("Trill", AudioSource.UPLOAD, "wav")
    after = strike(76, 0.4 + 8 * GAP_S + 0.4)
    pipeline.save_note_events(
        entry.uuid,
        alternation(8) + [after],
        duration_seconds=2.5,
        title="Trill",
    )
    return entry.uuid


def test_the_score_suggests_a_trill_and_accepting_it_collapses_the_page(client: TestClient) -> None:
    uuid = transcribed_trill()
    suggested = client.get(f"/time/{uuid}/score", params={"anchorMs": 320.0}).json()
    marks = suggested["trillSuggestions"]
    assert len(marks) == 1
    storm = [
        note
        for note in suggested["notes"]
        if note["row"] in {midi_to_row(LOWER), midi_to_row(UPPER)}
    ]
    assert len(storm) >= 7

    collapsed = client.post(
        f"/time/{uuid}/score",
        json={"anchorMs": 320.0, "trills": marks},
    ).json()
    assert collapsed["trillSuggestions"] == []
    remaining = [
        note
        for note in collapsed["notes"]
        if note["row"] in {midi_to_row(LOWER), midi_to_row(UPPER)}
        and marks[0]["fromColumn"] <= note["startFrame"] < marks[0]["toColumn"]
    ]
    assert len(remaining) == 1
    assert remaining[0]["row"] == midi_to_row(LOWER)

    from aitu_backend.transcription import pipeline

    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    assert len(stored.events) == 9
