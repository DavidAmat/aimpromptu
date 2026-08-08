"""Schema 2.0 stubs for the time-based matrix — field names and the invariants they carry.

These models are not built by the pipeline yet (Phase 0). What this file protects is the thing the
parallel work depends on: the JSON field names the renderer reads, and the few rules the contract
states in prose so that a later phase cannot quietly break them.
"""

import json

import pytest
from pydantic import ValidationError

from aitu_backend.schemas.matrix import SparseCooMatrix
from aitu_backend.schemas.time_matrix import (
    DEFAULT_FRAME_MS,
    FIGURE_NEGRAS,
    FigureLadder,
    FigureName,
    LayoutHints,
    Passage,
    PrintedNote,
    TimeMatrixEnvelope,
    TimeMatrixProcessingStep,
    TimeScorePayload,
)


def empty_matrix(frames: int) -> SparseCooMatrix:
    return SparseCooMatrix(shape=[88, frames], rows=[], cols=[], onset=[])


def ladder(negra_ms: float = 320.0) -> FigureLadder:
    return FigureLadder(
        anchor_figure=FigureName.NEGRA,
        anchor_ms=negra_ms,
        ms_by_figure={figure: negras * negra_ms for figure, negras in FIGURE_NEGRAS.items()},
    )


def envelope(frames: int = 100) -> TimeMatrixEnvelope:
    return TimeMatrixEnvelope(
        frame_count=frames,
        duration_seconds=frames * DEFAULT_FRAME_MS / 1000.0,
        matrix_processing_step=TimeMatrixProcessingStep.TWO_HANDS,
        r_matrix=empty_matrix(frames),
        l_matrix=empty_matrix(frames),
    )


def payload(passages: list[Passage], frames: int = 100) -> TimeScorePayload:
    return TimeScorePayload(
        envelope=envelope(frames),
        passages=passages,
        notes=[],
        layout=LayoutHints(frame_group=25, frame_measure=100, silence_group_px=6.0),
    )


def one_passage(start: int, end: int, name: str = "p1") -> Passage:
    return Passage(
        id=name,
        start_frame=start,
        end_frame=end,
        ladder=ladder(),
        header_label="negra = 320 ms · ≈188 BPM",
    )


def test_a_frame_is_forty_milliseconds_and_carries_no_tempo():
    """D-01: the grid is wall clock. A tempo field would let a BPM back into the matrix."""
    env = envelope()
    assert env.frame_ms == DEFAULT_FRAME_MS == 40.0
    assert env.time_step_seconds == 0.04
    wire = env.model_dump(by_alias=True)
    assert "tempoBpm" not in wire
    assert "granularity" not in wire


def test_the_envelope_travels_as_camel_case():
    """The renderer reads these exact names; a rename here is a silent break over there."""
    wire = envelope().model_dump(by_alias=True)
    assert wire["schemaVersion"] == "2.0"
    assert wire["frameMs"] == 40.0
    assert wire["frameCount"] == 100
    assert wire["matrixProcessingStep"] == "two-hands"
    assert set(wire) >= {"rMatrix", "lMatrix", "durationSeconds", "sparse"}
    assert json.loads(envelope().model_dump_json(by_alias=True))["frameMs"] == 40.0


def test_both_hands_span_the_declared_frame_count():
    with pytest.raises(ValidationError, match="frameCount"):
        TimeMatrixEnvelope(
            frame_count=100,
            duration_seconds=4.0,
            matrix_processing_step=TimeMatrixProcessingStep.TWO_HANDS,
            r_matrix=empty_matrix(100),
            l_matrix=empty_matrix(99),
        )


def test_the_figure_vocabulary_is_closed_and_dotted_only_on_blanca_and_negra():
    """D-12: allowing a dotted corchea is what turns an even swing pair into a ragged mix."""
    dotted = sorted(f.value for f in FigureName if f.value.startswith("dotted"))
    assert dotted == ["dottedBlanca", "dottedNegra"]
    assert len(FigureName) == 9
    assert set(FIGURE_NEGRAS) == set(FigureName)


def test_a_ladder_carries_every_figure():
    """D-10: the backend sends all nine values so the renderer never re-derives one."""
    assert ladder().ms_by_figure[FigureName.CORCHEA] == 160.0
    incomplete = {FigureName.NEGRA: 320.0}
    with pytest.raises(ValidationError, match="msByFigure"):
        FigureLadder(anchor_figure=FigureName.NEGRA, anchor_ms=320.0, ms_by_figure=incomplete)


def test_a_passage_ends_after_it_starts():
    with pytest.raises(ValidationError):
        one_passage(40, 40)


def test_passages_tile_the_piece_with_no_gap_and_no_overlap():
    """D-21 depends on this: a passage that does not own its frames cannot bound a ladder change."""
    payload([one_passage(0, 40, "a"), one_passage(40, 100, "b")])

    with pytest.raises(ValidationError, match="no gap"):
        payload([one_passage(0, 40, "a"), one_passage(50, 100, "b")])
    with pytest.raises(ValidationError, match="no gap"):
        payload([one_passage(0, 60, "a"), one_passage(40, 100, "b")])
    with pytest.raises(ValidationError, match="passages cover"):
        payload([one_passage(0, 40, "a")])


def test_a_printed_note_names_its_hand_and_carries_its_fitting_error():
    note = PrintedNote(
        hand="left",
        row=39,
        start_frame=8,
        printed_frames=4,
        printed_ms_exact=163.0,
        figure=FigureName.CORCHEA,
        fit_error=0.0268,
        group_id=3,
    )
    wire = note.model_dump(by_alias=True)
    assert wire["printedFrames"] == 4
    assert wire["printedMsExact"] == 163.0
    assert wire["fitError"] == pytest.approx(0.0268)
    assert wire["groupId"] == 3
    with pytest.raises(ValidationError):
        PrintedNote(
            hand="single",
            row=39,
            start_frame=8,
            printed_frames=4,
            printed_ms_exact=163.0,
            figure=FigureName.CORCHEA,
            fit_error=0.0,
            group_id=3,
        )


def test_there_is_no_alignment_window_to_get_wrong():
    """D-24. Onsets that share a frame already share an x, so the renderer needs no window."""
    hints = LayoutHints(frame_group=25, frame_measure=100, silence_group_px=6.0)
    wire = hints.model_dump(by_alias=True)
    assert "alignWindowMs" not in wire
    assert wire["hideLeftHand"] is False and wire["hideRightHand"] is False


def test_a_one_hand_piece_is_two_hands_with_an_empty_left_matrix():
    """D-31 and issue I-02. One shape only, so every consumer stays on one code path."""
    right_only = TimeScorePayload(
        envelope=envelope(),
        passages=[one_passage(0, 100)],
        notes=[],
        layout=LayoutHints(
            frame_group=25, frame_measure=100, silence_group_px=6.0, hide_left_hand=True
        ),
    )
    assert right_only.envelope.l_matrix.is_empty()
    assert right_only.layout.hide_left_hand is True


def test_the_only_processing_step_is_two_hands():
    """There is no `raw` step: an unsplit matrix never leaves the backend."""
    assert [step.value for step in TimeMatrixProcessingStep] == ["two-hands"]
    assert envelope().model_dump(by_alias=True)["matrixProcessingStep"] == "two-hands"
