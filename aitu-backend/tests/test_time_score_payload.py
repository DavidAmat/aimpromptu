"""Figures, passages and the payload the renderer draws.

`test_the_worked_example_at_00_46_prints_three_equal_corcheas` is success criterion 1 of the PRD,
run on the recording the whole refactor was designed from.
"""

import json
from pathlib import Path

import pytest

from aitu_backend.matrix.keys import midi_to_row
from aitu_backend.matrix.ladder import build_ladder
from aitu_backend.matrix.passages import (
    ladder_ranges,
    one_passage,
    passages_from_boundaries,
    shift_passage,
    split_passage,
    with_ladder,
)
from aitu_backend.schemas.time_matrix import BeamBreak, FigureName, FigureOverride
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import (
    impose_granularity_and_split,
    to_score_payload,
)

TREBLE, BASS = 72, 41
NEGRA_MS = 320.0


def note(start_ms: float, midi: int, length_ms: float = 150.0) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def ladder(negra_ms: float = NEGRA_MS):
    return build_ladder(FigureName.NEGRA, negra_ms)


def run(events, duration_seconds=6.0, **kwargs):
    kwargs.setdefault("artifacts", None)
    kwargs.setdefault("leakage", None)
    return impose_granularity_and_split(events, duration_seconds, **kwargs)


def even_run(count: int = 6, gap_ms: float = 160.0):
    """A run of even corcheas at negra = 320."""
    return [note(index * gap_ms, TREBLE + index % 4) for index in range(count)]


# --------------------------------------------------------------------------- figures


def test_the_printed_length_is_the_gap_to_the_next_onset_in_the_same_hand():
    """D-14. Not the release: these notes last 150 ms each but are printed 160 apart."""
    score = to_score_payload(run(even_run()), ladder())
    printed = [n for n in score.notes if n.hand == "right"]
    assert [n.printed_ms_exact for n in printed[:4]] == pytest.approx([160.0] * 4)
    assert all(n.figure == FigureName.CORCHEA for n in printed[:4])


def test_the_gap_is_measured_between_the_real_times_not_between_columns():
    """A 211 ms gap must stay 211, not become 200 because a column is 40 ms wide."""
    score = to_score_payload(run([note(0, TREBLE), note(211, TREBLE + 2)]), ladder(337.0))
    first = min(score.notes, key=lambda n: n.start_frame)
    assert first.printed_ms_exact == pytest.approx(211.0, abs=0.5)
    assert first.figure == FigureName.CORCHEA


def test_a_held_note_under_a_run_stays_long_on_the_other_hand():
    """Success criterion 6: the left hand is not cut by what the right hand plays."""
    events = [note(0, BASS, 1200.0)] + even_run(6)
    score = to_score_payload(run(events, duration_seconds=1.2), ladder())
    left = [n for n in score.notes if n.hand == "left"]
    right = [n for n in score.notes if n.hand == "right"]
    assert len(left) == 1
    assert left[0].printed_ms_exact > max(n.printed_ms_exact for n in right)
    assert left[0].figure in {FigureName.BLANCA, FigureName.DOTTED_BLANCA, FigureName.REDONDA}


def test_no_note_is_ever_printed_longer_than_a_redonda():
    """D-15 and D-06: the cap is applied here, where a redonda finally has a length."""
    score = to_score_payload(run([note(0, BASS, 5000.0)], duration_seconds=8.0), ladder())
    assert score.notes[0].printed_ms_exact == pytest.approx(4 * NEGRA_MS)
    assert score.notes[0].figure == FigureName.REDONDA


def test_the_notes_of_a_chord_share_a_group_and_a_figure():
    score = to_score_payload(
        run([note(0, TREBLE), note(8, TREBLE + 4), note(320, TREBLE)]), ladder()
    )
    chord = [n for n in score.notes if n.start_frame == 0]
    assert len(chord) == 2
    assert len({n.group_id for n in chord}) == 1
    assert len({n.figure for n in chord}) == 1


def test_every_note_reports_how_well_its_figure_fits():
    score = to_score_payload(run(even_run()), ladder())
    exact = [n for n in score.notes if n.printed_ms_exact == pytest.approx(160.0)]
    assert exact and all(n.fit_error == pytest.approx(0.0, abs=1e-9) for n in exact)


# --------------------------------------------------------------------------- passages


def test_a_piece_starts_as_one_passage_covering_everything():
    score = to_score_payload(run(even_run()), ladder())
    assert len(score.passages) == 1
    assert score.passages[0].start_frame == 0
    assert score.passages[0].end_frame == score.envelope.frame_count
    assert score.passages[0].header_label == "negra = 320 ms · ≈188 BPM"


def test_the_sheet_stops_where_the_music_stops():
    """A recording that runs on after the last note should not print a page of empty staff."""
    hands = run(even_run(6), duration_seconds=20.0)
    score = to_score_payload(hands, ladder())
    assert hands.frame_count == 500
    assert score.envelope.frame_count < 60
    assert score.envelope.r_matrix.shape[1] == score.envelope.frame_count
    assert score.envelope.l_matrix.shape[1] == score.envelope.frame_count

    untrimmed = to_score_payload(hands, ladder(), trim_trailing_silence=False)
    assert untrimmed.envelope.frame_count == hands.frame_count


def test_passages_drawn_by_hand_tile_the_piece():
    passages = passages_from_boundaries(100, [40, 70], [ladder(320), ladder(400), ladder(300)])
    assert [(p.start_frame, p.end_frame) for p in passages] == [(0, 40), (40, 70), (70, 100)]
    assert [p.id for p in passages] == ["p1", "p2", "p3"]


def test_a_boundary_outside_the_piece_is_refused():
    with pytest.raises(ValueError, match="inside the piece"):
        passages_from_boundaries(100, [0], [ladder(), ladder()])
    with pytest.raises(ValueError, match="ladder"):
        passages_from_boundaries(100, [40], [ladder()])


def test_changing_one_passage_ladder_moves_nothing_outside_it():
    """D-21, checked the way the decision asks: by comparing the notes, not by inspection."""
    hands = run(even_run(12), duration_seconds=2.0)
    frames = to_score_payload(hands, ladder()).envelope.frame_count
    half = frames // 2
    passages = passages_from_boundaries(frames, [half], [ladder(320), ladder(320)])

    before = to_score_payload(hands, ladder(), passages=passages)
    after = to_score_payload(hands, ladder(), passages=with_ladder(passages, "p2", ladder(640)))

    early_before = [n for n in before.notes if n.start_frame < half]
    early_after = [n for n in after.notes if n.start_frame < half]
    assert [(n.start_frame, n.row, n.figure) for n in early_before] == [
        (n.start_frame, n.row, n.figure) for n in early_after
    ]
    assert [n.start_frame for n in before.notes] == [n.start_frame for n in after.notes]

    late_before = {n.figure for n in before.notes if n.start_frame >= half}
    late_after = {n.figure for n in after.notes if n.start_frame >= half}
    assert late_before != late_after


def test_a_figure_shift_renames_a_passage_without_moving_a_note():
    """D-18. Every column is identical afterwards; only the glyphs change."""
    hands = run(even_run(8))
    passages = one_passage(to_score_payload(hands, ladder()).envelope.frame_count, ladder())
    before = to_score_payload(hands, ladder(), passages=passages)
    after = to_score_payload(hands, ladder(), passages=shift_passage(passages, "p1", 1))

    assert [n.start_frame for n in before.notes] == [n.start_frame for n in after.notes]
    assert after.passages[0].ladder.anchor_figure == FigureName.BLANCA
    assert after.passages[0].ladder.anchor_ms == NEGRA_MS
    assert {n.figure for n in before.notes} != {n.figure for n in after.notes}


def test_a_passage_can_be_cut_in_two_and_still_tiles():
    passages = split_passage(one_passage(100, ladder()), "p1", 40, ladder(400))
    assert [(p.start_frame, p.end_frame) for p in passages] == [(0, 40), (40, 100)]
    assert passages[1].ladder.anchor_ms == 400.0
    assert ladder_ranges(passages)[1][2].anchor_ms == 400.0


def test_a_cut_outside_the_passage_is_refused():
    with pytest.raises(ValueError, match="not inside"):
        split_passage(one_passage(100, ladder()), "p1", 200)


# --------------------------------------------------------------------------- payload


def test_the_payload_carries_everything_the_renderer_needs():
    hands = run(even_run())
    override = FigureOverride(
        hand="right", row=midi_to_row(TREBLE), start_frame=0, figure=FigureName.NEGRA
    )
    score = to_score_payload(hands, ladder(), overrides=[override], title="Test")
    wire = json.loads(score.model_dump_json(by_alias=True))

    assert wire["schemaVersion"] == "2.0"
    assert wire["envelope"]["frameMs"] == 40.0
    assert wire["envelope"]["matrixProcessingStep"] == "two-hands"
    assert wire["passages"][0]["headerLabel"] == "negra = 320 ms · ≈188 BPM"
    assert wire["overrides"][0]["figure"] == "negra"
    assert set(wire["layout"]) == {
        "frameGroup",
        "frameMeasure",
        "silenceGroupPx",
        "hideLeftHand",
        "hideRightHand",
    }
    assert wire["notes"][0]["printedFrames"] >= 1


def test_the_notes_are_ordered_the_way_the_contract_says():
    score = to_score_payload(run([note(0, BASS, 900.0)] + even_run()), ladder())
    keys = [(n.start_frame, n.hand, n.row) for n in score.notes]
    assert keys == sorted(keys)


def test_an_override_is_carried_but_changes_nothing_else():
    """D-17. The backend stores it; the renderer applies it to exactly one glyph."""
    hands = run(even_run())
    plain = to_score_payload(hands, ladder())
    override = FigureOverride(
        hand="right", row=midi_to_row(TREBLE), start_frame=0, figure=FigureName.REDONDA
    )
    with_override = to_score_payload(hands, ladder(), overrides=[override])
    assert [(n.start_frame, n.figure) for n in plain.notes] == [
        (n.start_frame, n.figure) for n in with_override.notes
    ]
    assert with_override.overrides == [override]


def test_the_frame_length_does_not_change_which_figures_are_printed():
    """`frameMs` is a layout parameter. A corchea stays a corchea at 20, 30 or 40 ms."""
    events = even_run(8)
    figures = {
        step: [n.figure for n in to_score_payload(run(events, frame_ms=step), ladder()).notes]
        for step in (40, 30, 20)
    }
    assert figures[40] == figures[30] == figures[20]


# --------------------------------------------------------------------------- the real piece

POC_DATA = Path(__file__).resolve().parents[2] / "poc-onset-duration-distribution" / "data"


@pytest.mark.skipif(not POC_DATA.exists(), reason="the PoC transcription is not in this checkout")
def test_the_worked_example_at_00_46_prints_three_equal_corcheas():
    """**Success criterion 1.** The case the whole refactor exists to fix.

    On the printed sheet the F5, E5 and C5 at 00:46 are three corcheas. The old pipeline wrote them
    as semicorchea, dotted corchea, semicorchea, and did so every time the figure appeared, because
    a shuffled beat has no representation on a power-of-two grid at any resolution.

    Here the three are labelled from the raw gaps by proportion, so all three come out as corcheas
    even though they were played 120, 217 and 122 ms apart.
    """
    payload = json.loads((POC_DATA / "events.json").read_text())
    events = [
        NoteEvent(midi_note=item["midiNote"], start=item["start"], end=item["end"])
        for item in payload["events"]
    ]
    hands = impose_granularity_and_split(events, float(payload["durationSeconds"]))
    score = to_score_payload(hands, build_ladder(FigureName.NEGRA, 337.0))

    # 41.625 / 41.752 / 41.963 s on the segment clock is 00:46 on the video clock.
    wanted = {
        "F5": (midi_to_row(77), 1041),
        "E5": (midi_to_row(76), 1044),
        "C5": (midi_to_row(72), 1049),
    }
    printed = {}
    for name, (row, column) in wanted.items():
        found = [n for n in score.notes if n.row == row and abs(n.start_frame - column) <= 1]
        assert found, f"{name} was not printed anywhere near column {column}"
        printed[name] = found[0]

    assert [printed[name].figure for name in ("F5", "E5", "C5")] == [FigureName.CORCHEA] * 3
    assert all(note.hand == "right" for note in printed.values())


def test_a_beam_break_names_a_note_and_nothing_else():
    """D-34. The twin of a figure override: it changes grouping, not music.

    Deliberately only a hand and a column. A break that also carried a figure, or a run length,
    would be two decisions in one field and the second would go stale the moment the ladder changed.
    """
    wire = BeamBreak(hand="left", start_frame=318).model_dump(by_alias=True)
    assert wire == {"hand": "left", "startFrame": 318}


def test_a_score_carries_the_breaks_the_reader_asked_for():
    payload = to_score_payload(run(even_run()), ladder())
    regrouped = payload.model_copy(
        update={"beam_breaks": [BeamBreak(hand="right", start_frame=payload.notes[2].start_frame)]}
    )

    wire = regrouped.model_dump(by_alias=True)
    assert wire["beamBreaks"] == [{"hand": "right", "startFrame": payload.notes[2].start_frame}]
    # Absent by default: a piece nobody has regrouped says so by having none.
    assert payload.model_dump(by_alias=True)["beamBreaks"] == []
