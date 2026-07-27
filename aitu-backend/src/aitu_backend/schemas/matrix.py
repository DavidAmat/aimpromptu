"""Canonical piano-matrix contracts, defined once and mirrored in TypeScript.

Read alongside ``context/music/notation-logic/01-matrix-notation-logic.md`` and
``02-notation-spec.md``.

Two orientations, on purpose:

* **Sparse COO (the wire and storage form)** is ``88 x N``: ``rows`` are keys
  (``La-0`` … ``Do-8``), ``cols`` are time frames. This matches the existing
  ``MatrixScore`` contract and ``scipy.sparse``.
* **Dense (export/import only)** is ``N x 88``: one row per **time frame**, one
  column per **key** — the orientation the Matrix tab displays, and the reason
  the envelope calls its convenience fields ``columnHeaders`` (88 key labels)
  and ``rowTimestamps`` (N frame times).

The converters below own that transposition so nothing else has to think about
it. Dense values are ``1`` onset, ``-1`` sustain, ``0`` silence.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aitu_backend.matrix.keys import (
    KEY_COUNT,
    build_grand_piano_rows,
    build_grand_piano_rows_en,
)


class Granularity(str, Enum):
    """Temporal resolution of one matrix column, named after the note figure.

    ``beats`` is measured in negras (quarter notes): the project's beat unit,
    per Appendix A of the matrix notation logic.
    """

    REDONDA = "redonda"
    BLANCA = "blanca"
    NEGRA = "negra"
    CORCHEA = "corchea"
    SEMICORCHEA = "semicorchea"
    FUSA = "fusa"
    SEMIFUSA = "semifusa"

    @property
    def beats(self) -> float:
        """Duration of one column in beats (negra = 1.0)."""
        return GRANULARITY_BEATS[self]

    def seconds(self, tempo_bpm: float) -> float:
        """Wall-clock seconds per column at ``tempo_bpm``."""
        if tempo_bpm <= 0:
            raise ValueError("tempoBpm must be positive")
        return self.beats * (60.0 / tempo_bpm)


#: Beats (negras) per column for each granularity.
GRANULARITY_BEATS: dict[Granularity, float] = {
    Granularity.REDONDA: 4.0,
    Granularity.BLANCA: 2.0,
    Granularity.NEGRA: 1.0,
    Granularity.CORCHEA: 0.5,
    Granularity.SEMICORCHEA: 0.25,
    Granularity.FUSA: 0.125,
    Granularity.SEMIFUSA: 0.0625,
}

#: Coarse -> fine. Collapsing walks this list one step at a time (Task 2.2.1).
GRANULARITY_HIERARCHY: list[Granularity] = [
    Granularity.REDONDA,
    Granularity.BLANCA,
    Granularity.NEGRA,
    Granularity.CORCHEA,
    Granularity.SEMICORCHEA,
    Granularity.FUSA,
    Granularity.SEMIFUSA,
]

#: Short codes used in version folder names (`v2_gn`). See Task 1.3.2.
GRANULARITY_CODES: dict[Granularity, str] = {
    Granularity.REDONDA: "gr",
    Granularity.BLANCA: "gb",
    Granularity.NEGRA: "gn",
    Granularity.CORCHEA: "gc",
    Granularity.SEMICORCHEA: "gsc",
    Granularity.FUSA: "gf",
    Granularity.SEMIFUSA: "gsf",
}

CODE_TO_GRANULARITY: dict[str, Granularity] = {
    code: gran for gran, code in GRANULARITY_CODES.items()
}


class MatrixProcessingStep(str, Enum):
    """Where a matrix sits in the pipeline (Epic 4)."""

    RAW = "raw"
    COLLAPSED = "collapsed"
    CLEAN = "clean"
    TWO_HANDS = "two-hands"


class Hand(str, Enum):
    """Which hand a matrix belongs to. ``SINGLE`` = not yet split."""

    SINGLE = "single"
    LEFT = "left"
    RIGHT = "right"


#: Cell values in the dense form.
ONSET = 1
SUSTAIN = -1
SILENCE = 0


class SparseCooMatrix(BaseModel):
    """88 x N piano matrix in COO form, sorted by ``(col, row)``.

    Only active cells travel. ``onset[i]`` equals ``rows[i]`` when the cell is a
    struck onset, or ``-1`` when it is a sustain — the distinction that separates
    one held note from repeated strikes.
    """

    model_config = ConfigDict(populate_by_name=True)

    format: Literal["binary-coo"] = "binary-coo"
    #: ``[rowCount, columnCount]``; rowCount is always 88.
    shape: list[int]
    rows: list[int]
    cols: list[int]
    onset: list[int]

    @model_validator(mode="after")
    def _check_arrays(self) -> "SparseCooMatrix":
        if len(self.shape) != 2:
            raise ValueError(f"shape must be [rowCount, columnCount], got {self.shape}")
        if self.shape[0] != KEY_COUNT:
            raise ValueError(f"A piano matrix has {KEY_COUNT} rows, got {self.shape[0]}")
        if self.shape[1] < 0:
            raise ValueError("columnCount cannot be negative")
        if not (len(self.rows) == len(self.cols) == len(self.onset)):
            raise ValueError(
                "rows, cols and onset must be parallel arrays "
                f"(got {len(self.rows)}, {len(self.cols)}, {len(self.onset)})"
            )
        for index, (row, col, onset) in enumerate(zip(self.rows, self.cols, self.onset)):
            if not 0 <= row < self.shape[0]:
                raise ValueError(f"rows[{index}] = {row} outside 0..{self.shape[0] - 1}")
            if not 0 <= col < self.shape[1]:
                raise ValueError(f"cols[{index}] = {col} outside 0..{self.shape[1] - 1}")
            if onset != row and onset != -1:
                raise ValueError(
                    f"onset[{index}] must be rows[{index}] ({row}) for an onset or -1 "
                    f"for a sustain, got {onset}"
                )
        return self

    @property
    def frame_count(self) -> int:
        """Number of time frames (columns)."""
        return self.shape[1]

    def is_empty(self) -> bool:
        return not self.rows


class KeyLabel(BaseModel):
    """One matrix key, labelled in both languages the UI shows."""

    model_config = ConfigDict(populate_by_name=True)

    #: Spanish solfège, the notation contract form: ``Fa#-5``.
    es: str
    #: English scientific pitch: ``F#5``.
    en: str
    #: Matrix row index, 0 = ``La-0``.
    row: int


def key_labels() -> list[KeyLabel]:
    """The 88 key labels in canonical row order."""
    spanish = build_grand_piano_rows()
    english = build_grand_piano_rows_en()
    return [KeyLabel(es=es, en=en, row=row) for row, (es, en) in enumerate(zip(spanish, english))]


class PianoMatrixEnvelope(BaseModel):
    """Everything needed to interpret one exported or imported matrix.

    One hand carries ``matrix``; two hands carry ``rMatrix`` + ``lMatrix`` with
    equal frame counts. ``sparse`` selects which payload is populated: the COO
    fields, or ``denseMatrix`` (N x 88).
    """

    model_config = ConfigDict(populate_by_name=True)

    tempo_bpm: float = Field(..., alias="tempoBpm", gt=0)
    time_step_seconds: float = Field(..., alias="timeStepSeconds", gt=0)
    granularity: Granularity
    matrix_processing_step: MatrixProcessingStep = Field(..., alias="matrixProcessingStep")
    #: True when the COO payload is used; False when ``denseMatrix`` is.
    sparse: bool = True

    matrix: SparseCooMatrix | None = None
    r_matrix: SparseCooMatrix | None = Field(None, alias="rMatrix")
    l_matrix: SparseCooMatrix | None = Field(None, alias="lMatrix")

    #: Dense grid, **frames x keys** — one row per time frame. Only when ``sparse`` is False.
    dense_matrix: list[list[int]] | None = Field(None, alias="denseMatrix")
    #: Same, for the two-hands dense export.
    dense_r_matrix: list[list[int]] | None = Field(None, alias="denseRMatrix")
    dense_l_matrix: list[list[int]] | None = Field(None, alias="denseLMatrix")

    #: 88 key labels for the dense columns. Convenience for humans reading the JSON.
    column_headers: list[KeyLabel] | None = Field(None, alias="columnHeaders")
    #: Start time in seconds of each dense row.
    row_timestamps: list[float] | None = Field(None, alias="rowTimestamps")

    title: str | None = None
    key_signature: str | None = Field(None, alias="keySignature")

    @model_validator(mode="after")
    def _check_payload(self) -> "PianoMatrixEnvelope":
        if self.sparse:
            self._check_sparse_payload()
        else:
            self._check_dense_payload()
        if self.column_headers is not None and len(self.column_headers) != KEY_COUNT:
            raise ValueError(
                f"columnHeaders must label all {KEY_COUNT} keys, got {len(self.column_headers)}"
            )
        return self

    def _check_sparse_payload(self) -> None:
        one_hand = self.matrix is not None
        two_hand = self.r_matrix is not None and self.l_matrix is not None
        if one_hand == two_hand:
            raise ValueError(
                "A sparse envelope carries either `matrix` (one hand) or both "
                "`rMatrix` and `lMatrix` (two hands), never both or neither."
            )
        right, left = self.r_matrix, self.l_matrix
        if right is not None and left is not None and right.shape[1] != left.shape[1]:
            raise ValueError(
                "rMatrix and lMatrix must span the same number of time frames "
                f"(got {right.shape[1]} vs {left.shape[1]})."
            )

    def _check_dense_payload(self) -> None:
        one_hand = self.dense_matrix is not None
        two_hand = self.dense_r_matrix is not None and self.dense_l_matrix is not None
        if one_hand == two_hand:
            raise ValueError(
                "A dense envelope carries either `denseMatrix` (one hand) or both "
                "`denseRMatrix` and `denseLMatrix` (two hands), never both or neither."
            )
        for name, grid in (
            ("denseMatrix", self.dense_matrix),
            ("denseRMatrix", self.dense_r_matrix),
            ("denseLMatrix", self.dense_l_matrix),
        ):
            if grid is None:
                continue
            for index, frame in enumerate(grid):
                if len(frame) != KEY_COUNT:
                    raise ValueError(
                        f"{name}[{index}] must have {KEY_COUNT} key columns, got {len(frame)}"
                    )
                for value in frame:
                    if value not in (ONSET, SUSTAIN, SILENCE):
                        raise ValueError(
                            f"{name}[{index}] contains {value}; only 1, -1 and 0 are valid"
                        )
        right, left = self.dense_r_matrix, self.dense_l_matrix
        if right is not None and left is not None and len(right) != len(left):
            raise ValueError(
                "denseRMatrix and denseLMatrix must span the same number of time frames "
                f"(got {len(right)} vs {len(left)})."
            )

    @property
    def frame_count(self) -> int:
        """Number of time frames, whichever payload is present."""
        for sparse in (self.matrix, self.r_matrix, self.l_matrix):
            if sparse is not None:
                return sparse.shape[1]
        for dense in (self.dense_matrix, self.dense_r_matrix, self.dense_l_matrix):
            if dense is not None:
                return len(dense)
        return 0

    @property
    def two_hands(self) -> bool:
        return self.r_matrix is not None or self.dense_r_matrix is not None
