"""Schema 2.0 contracts for the time-based matrix, mirrored in TypeScript.

Read alongside ``context/implementations/time-based-concept/contract.md``, which is the frozen
interface between this package and ``@aimpromptu/grid-notation``, and ``decisions.md`` in the same
folder for the ``D-nn`` ids cited below.

What changes. A matrix column stops being a note figure and becomes a fixed number of milliseconds
(``frameMs``, 40 by default, D-01). No BPM takes part in building the matrix. The rhythmic figure
becomes a label the user chooses by naming a peak in the distribution of gaps between onsets
(D-09, D-10), so a wrong figure moves nothing on the page.

These models are Phase 0 stubs: nothing in the pipeline builds them yet. They exist so this package
and the renderer compile against the same field names while the backend phases and the renderer
phases are implemented in parallel. The TypeScript mirror is ``vexflow-v2/src/matrix/types.ts``.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aitu_backend.matrix.keys import KEY_COUNT
from aitu_backend.schemas.matrix import SparseCooMatrix

#: Length of one matrix column in milliseconds (D-01). Provisional: 40 ms is right for a slow
#: passage and coarse for a fast one, so it is configurable per piece and lives in the envelope.
DEFAULT_FRAME_MS = 40.0

#: The window that groups near-simultaneous onsets into one attack follows the frame length (D-04),
#: so a piece rendered at 20 ms groups at 20 ms. There is no second window: onsets that share a frame
#: already share one x on the page (D-24), which is why ``alignWindowMs`` no longer exists.


class FigureName(str, Enum):
    """The closed figure vocabulary (D-12).

    Dots exist on ``blanca`` and ``negra`` only. That restriction is deliberate: with the dotted
    corchea banned, a swing pair of 211 ms and 125 ms both resolve to ``corchea``, which is what the
    printed sheet shows. Allowing the dot pulls the long half of the pair to a dotted corchea and
    recreates the ragged mix this refactor removes.

    This is not the same vocabulary as ``Granularity`` in ``schemas/matrix.py``. That enum names the
    resolution of a column and disappears from the grid in Phase 4; this one names a printed figure.
    """

    REDONDA = "redonda"
    BLANCA = "blanca"
    DOTTED_BLANCA = "dottedBlanca"
    NEGRA = "negra"
    DOTTED_NEGRA = "dottedNegra"
    CORCHEA = "corchea"
    SEMICORCHEA = "semicorchea"
    FUSA = "fusa"
    SEMIFUSA = "semifusa"


#: Length of each figure in negras. A ladder is this table scaled by the anchor the user named, so
#: naming one peak fixes every other figure by proportion (D-10). Building the ladder is P2.3's job;
#: the table lives here because it is part of the vocabulary, not of the fitting.
FIGURE_NEGRAS: dict[FigureName, float] = {
    FigureName.REDONDA: 4.0,
    FigureName.BLANCA: 2.0,
    FigureName.DOTTED_BLANCA: 3.0,
    FigureName.NEGRA: 1.0,
    FigureName.DOTTED_NEGRA: 1.5,
    FigureName.CORCHEA: 0.5,
    FigureName.SEMICORCHEA: 0.25,
    FigureName.FUSA: 0.125,
    FigureName.SEMIFUSA: 0.0625,
}

#: Longest figure that is ever printed (D-15). A longer gap prints a redonda and the
#: remainder is silence.
MAX_PRINTED_FIGURE = FigureName.REDONDA

#: Which staff a printed note belongs to. Unlike ``Hand`` in ``schemas/matrix.py`` there is no
#: ``single`` member: the score payload is always produced after the hand split (D-31).
PrintedHand = Literal["right", "left"]


class TimeMatrixProcessingStep(str, Enum):
    """Where a 2.0 matrix sits in the pipeline. There is only one place it can be.

    ``raw``, ``collapsed`` and ``clean`` are all gone. There is one grid, so there is nothing to
    collapse to, and the hands are split immediately after the grid is built (D-31), so a matrix
    that has not been split never leaves the backend.
    """

    TWO_HANDS = "two-hands"


class TimeMatrixEnvelope(BaseModel):
    """Everything needed to interpret one wall-clock matrix (contract §2).

    There is always exactly one shape: two hands. A one-hand piece is two hands with an empty
    ``lMatrix`` and a hide-hand flag in the layout hints, which keeps every consumer on one code
    path.

    Cell values keep their 1.x meaning: ``1`` onset, ``-1`` measured sustain, ``0`` silence. The
    sustain is stored **in full**: capping it at a redonda needs a ladder, and no ladder exists until
    the user has named a peak, so the cap is applied when the score payload is built (D-06). The
    sustain is a *measurement* and never decides a printed figure, which comes from D-14 instead.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_version: Literal["2.0"] = Field("2.0", alias="schemaVersion")
    sparse: Literal[True] = True

    #: Length of one column in milliseconds (D-01).
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    frame_count: int = Field(..., alias="frameCount", ge=0)
    #: Wall-clock length of the source audio. ``frame_count * frame_ms`` may exceed it by under one
    #: frame, because the last onset is rounded to a whole column.
    duration_seconds: float = Field(..., alias="durationSeconds", ge=0)

    title: str | None = None
    key_signature: str | None = Field(None, alias="keySignature")

    matrix_processing_step: TimeMatrixProcessingStep = Field(
        TimeMatrixProcessingStep.TWO_HANDS, alias="matrixProcessingStep"
    )
    #: Both are always present. A right-hand-only piece carries an empty ``lMatrix`` and sets
    #: ``LayoutHints.hide_left_hand``; there is no single-matrix form.
    r_matrix: SparseCooMatrix = Field(..., alias="rMatrix")
    l_matrix: SparseCooMatrix = Field(..., alias="lMatrix")

    @model_validator(mode="after")
    def _check_frames(self) -> "TimeMatrixEnvelope":
        for name, matrix in (("rMatrix", self.r_matrix), ("lMatrix", self.l_matrix)):
            if matrix.shape[1] != self.frame_count:
                raise ValueError(
                    f"{name} spans {matrix.shape[1]} frames but frameCount is {self.frame_count}"
                )
        return self

    @property
    def time_step_seconds(self) -> float:
        """Seconds per column. Derived from ``frame_ms``, never stored separately."""
        return self.frame_ms / 1000.0


class FigureLadder(BaseModel):
    """The millisecond value of every figure, fixed by one figure the user named (D-09, D-10).

    The app never chooses a ladder. Interval statistics fix it only up to a rational factor: a beat
    and twice that beat explain the same gaps equally well, so the app presents and the user
    decides.

    ``ms_by_figure`` is always complete. Sending all nine values means the renderer never re-derives
    them and the two sides cannot disagree.
    """

    model_config = ConfigDict(populate_by_name=True)

    anchor_figure: FigureName = Field(..., alias="anchorFigure")
    anchor_ms: float = Field(..., alias="anchorMs", gt=0)
    ms_by_figure: dict[FigureName, float] = Field(..., alias="msByFigure")

    @model_validator(mode="after")
    def _check_complete(self) -> "FigureLadder":
        missing = sorted(figure.value for figure in FigureName if figure not in self.ms_by_figure)
        if missing:
            raise ValueError(f"msByFigure must carry every figure; missing {missing}")
        for figure, ms in self.ms_by_figure.items():
            if ms <= 0:
                raise ValueError(f"msByFigure[{figure.value}] must be positive, got {ms}")
        return self


class Passage(BaseModel):
    """A stretch of the piece with its own ladder (D-19, D-20, D-21).

    Boundaries are drawn by hand; there is no automatic segmentation in v1. They are keyed by frame,
    and frames are absolute wall clock, so changing a passage's ladder relabels its notes and moves
    nothing, inside the passage or outside it.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    start_frame: int = Field(..., alias="startFrame", ge=0)
    #: Exclusive.
    end_frame: int = Field(..., alias="endFrame", gt=0)
    ladder: FigureLadder
    #: What the header prints, for example ``negra = 320 ms · ≈188 BPM`` (D-20).
    header_label: str = Field(..., alias="headerLabel")

    @model_validator(mode="after")
    def _check_range(self) -> "Passage":
        if self.end_frame <= self.start_frame:
            raise ValueError(
                f"passage {self.id!r} ends at frame {self.end_frame}, "
                f"which is not after its start frame {self.start_frame}"
            )
        return self


class PrintedNote(BaseModel):
    """One glyph the renderer draws, with its figure already resolved by this package.

    Choosing the figure happens here and not in the renderer, so the ladder, the proportional
    comparison (D-11) and the closed vocabulary (D-12) all live in one place.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    #: 0..87, row 0 = MIDI 21.
    row: int = Field(..., ge=0, lt=KEY_COUNT)
    start_frame: int = Field(..., alias="startFrame", ge=0)
    #: Onset to next onset in the same hand, in frames (D-14), capped at one redonda (D-15).
    printed_frames: int = Field(..., alias="printedFrames", ge=1)
    #: The same gap in milliseconds before snapping, so the UI can show the fitting error.
    printed_ms_exact: float = Field(..., alias="printedMsExact", ge=0)
    figure: FigureName
    #: ``abs(log2(printedMsExact / ladder.msByFigure[figure]))``. Shown to the user, never used for
    #: layout: the column is the same width whichever figure is printed.
    fit_error: float = Field(..., alias="fitError", ge=0)
    #: Members of one chord group share this (D-04).
    group_id: int = Field(..., alias="groupId", ge=0)
    #: How many notes this one is grouped with against the beat, or ``None`` for an ordinary note.
    #:
    #: Only ``3`` for now: a *tresillo*, three notes played in the time the ladder gives to two.
    #: The figure is the ordinary one, so a tresillo of corcheas carries ``figure = corchea``; what
    #: makes it a tresillo is this number and the bracket the renderer draws from it.
    tuplet: int | None = Field(None, ge=2)
    #: The three notes of one tresillo share this. ``None`` when the note is not in one.
    tuplet_id: int | None = Field(None, alias="tupletId", ge=0)


class FigureOverride(BaseModel):
    """A figure the user set by hand for one note (D-17).

    It changes that one glyph and nothing else: no reflow, no renumbering, no effect on any other
    note. That is only possible because the figure no longer decides where anything sits.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    row: int = Field(..., ge=0, lt=KEY_COUNT)
    start_frame: int = Field(..., alias="startFrame", ge=0)
    figure: FigureName


class BeamBreak(BaseModel):
    """A note the reader asked to start a new beam group (D-34).

    The twin of :class:`FigureOverride`, and kept for the same reason: it changes how the page is
    grouped and nothing about the music. A long run climbing through an arpeggio has no boundary any
    rule can find — one hand, one key, one clef, no tuplet — so it beams as a single shapeless slope
    with stems reaching across two octaves. Where the phrase actually restarts is a reading of the
    music, not a property of it, and this is the only place that reading can come from.

    Keyed by the note's own column, not by its position in the run, so it survives a ladder change:
    renaming the figures moves nothing in time, and the break stays where the reader put it.
    """

    model_config = ConfigDict(populate_by_name=True)

    hand: PrintedHand
    start_frame: int = Field(..., alias="startFrame", ge=0)


class LayoutHints(BaseModel):
    """Wall-clock aggregation levels and spacing hints for the renderer (D-23, D-24, D-27).

    ``frame_group`` and ``frame_measure`` have no musical meaning. They are UI units: a group is
    what the user can select, a measure is where a dashed vertical line is drawn. There are no bar
    lines and no time signature (D-28).

    There is no alignment window here. Onsets played near-simultaneously were grouped on the raw
    times before snapping, so they already share a frame, and one frame is one x (D-24).
    """

    model_config = ConfigDict(populate_by_name=True)

    #: Frames per selectable group, for example 25 at 40 ms = 1 second.
    frame_group: int = Field(..., alias="frameGroup", gt=0)
    #: Frames per dashed line, for example 100 at 40 ms = 4 seconds.
    frame_measure: int = Field(..., alias="frameMeasure", gt=0)
    #: Pixels a fully silent frame group collapses to (D-23), so a five-second rest reads as a few
    #: closely spaced dashed lines instead of five seconds of blank page.
    silence_group_px: float = Field(..., alias="silenceGroupPx", gt=0)
    #: Draw one staff only. Set for a one-hand piece, whose other matrix is empty.
    hide_left_hand: bool = Field(False, alias="hideLeftHand")
    hide_right_hand: bool = Field(False, alias="hideRightHand")


class TimeScorePayload(BaseModel):
    """What the renderer consumes (contract §5).

    Passages tile the piece with no gaps and no overlaps. A piece with one ladder has exactly one
    passage covering every frame.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_version: Literal["2.0"] = Field("2.0", alias="schemaVersion")
    envelope: TimeMatrixEnvelope
    #: Ordered, tiling, non-overlapping.
    passages: list[Passage]
    #: Both hands, ordered by ``(startFrame, hand, row)``.
    notes: list[PrintedNote]
    overrides: list[FigureOverride] = Field(default_factory=list)
    #: Notes the reader asked to start a new beam (D-34). Grouping only; no note changes.
    beam_breaks: list[BeamBreak] = Field(default_factory=list, alias="beamBreaks")
    layout: LayoutHints

    @model_validator(mode="after")
    def _check_passages_tile(self) -> "TimeScorePayload":
        frame_count = self.envelope.frame_count
        if not self.passages:
            if frame_count:
                raise ValueError(f"a score of {frame_count} frames needs at least one passage")
            return self
        expected_start = 0
        for passage in self.passages:
            if passage.start_frame != expected_start:
                raise ValueError(
                    f"passage {passage.id!r} starts at frame {passage.start_frame}; passages must "
                    f"tile the piece with no gap and no overlap, so it must start at "
                    f"{expected_start}"
                )
            expected_start = passage.end_frame
        if expected_start != frame_count:
            raise ValueError(
                f"passages cover {expected_start} frames but the matrix has {frame_count}"
            )
        return self
