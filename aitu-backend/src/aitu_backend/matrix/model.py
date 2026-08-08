"""``PianoMatrix`` — the in-memory object every other matrix module manipulates.

Backed by a dense ``numpy`` ``int8`` array of shape ``88 x N`` (row = key,
col = time frame), with ``1`` onset, ``-1`` sustain, ``0`` silence.

Why dense in memory when the wire and disk forms are sparse: the operations this
epic needs — collapse, clean, split, transpose, slice — are all whole-array
numpy work, and 88 x N int8 is 88 bytes per frame, i.e. ~1 MB for two hours of
fusas at 120 BPM. Sparsity buys nothing at that size and costs vectorization.
The COO form is produced on the way out (:meth:`to_coo_payload`,
:meth:`save_npz`) and consumed on the way in.

Timing follows ``context/music/notation-logic/01-matrix-notation-logic.md``:
a beat is a **negra**, ``beats_per_column`` comes from the granularity, and
``time_step_seconds = beats_per_column * 60 / tempo_bpm``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from aitu_backend.matrix.keys import KEY_COUNT, build_grand_piano_rows, note_to_row
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, seconds_per_frame, validate_frame_ms
from aitu_backend.schemas.matrix import (
    GRANULARITY_HIERARCHY,
    ONSET,
    SILENCE,
    SUSTAIN,
    Granularity,
    MatrixProcessingStep,
    PianoMatrixEnvelope,
    SparseCooMatrix,
)

#: The granularity ladder, coarse -> fine, as plain strings.
HIERARCHY: list[str] = [granularity.value for granularity in GRANULARITY_HIERARCHY]

#: The three legal cell values.
CELL_VALUES = (SILENCE, ONSET, SUSTAIN)


def beats_per_column(granularity: Granularity | str) -> float:
    """Duration of one column in beats (negra = 1.0)."""
    return Granularity(granularity).beats


def seconds_per_column(granularity: Granularity | str, tempo_bpm: float) -> float:
    """``beats_per_column * 60 / tempo_bpm`` — the derived ``time_step_seconds``."""
    return Granularity(granularity).seconds(tempo_bpm)


@dataclass
class PianoMatrix:
    """An 88 x N piano matrix plus the metadata needed to interpret it.

    Construct with :meth:`empty`, :meth:`from_dense`, :meth:`from_coo_payload`
    or :meth:`load_npz`. ``grid`` is owned by the instance — callers that mutate
    it must re-run the validator (Task 2.1.2).
    """

    grid: np.ndarray
    granularity: Granularity
    tempo_bpm: float
    processing_step: MatrixProcessingStep = MatrixProcessingStep.RAW
    key_signature: str | None = None
    title: str | None = None
    #: Filled by Task 2.4.1 when the matrix belongs to one hand.
    hand: str | None = field(default=None)
    #: Length of one column in milliseconds. When this is set the matrix is a **time matrix**: its
    #: columns are wall clock, ``granularity`` and ``tempo_bpm`` no longer describe anything, and
    #: asking for a beat value raises. Build one with :meth:`time_based`. See D-01.
    frame_ms: float | None = field(default=None)

    def __post_init__(self) -> None:
        self.grid = np.asarray(self.grid, dtype=np.int8)
        if self.grid.ndim != 2 or self.grid.shape[0] != KEY_COUNT:
            raise ValueError(f"A piano matrix is {KEY_COUNT} x N, got shape {self.grid.shape}")
        if self.tempo_bpm <= 0:
            raise ValueError(f"tempo_bpm must be positive, got {self.tempo_bpm}")
        if self.frame_ms is not None:
            self.frame_ms = validate_frame_ms(self.frame_ms)
        self.granularity = Granularity(self.granularity)
        self.processing_step = MatrixProcessingStep(self.processing_step)
        illegal = set(np.unique(self.grid).tolist()) - set(CELL_VALUES)
        if illegal:
            raise ValueError(f"Illegal cell values {sorted(illegal)}; only 1, -1 and 0 are allowed")

    @property
    def is_time_based(self) -> bool:
        """True when a column is a fixed slice of wall clock rather than a note figure."""
        return self.frame_ms is not None

    # ------------------------------------------------------------ constructors

    @classmethod
    def empty(
        cls,
        frame_count: int,
        granularity: Granularity | str = Granularity.SEMICORCHEA,
        tempo_bpm: float = 60.0,
        **kwargs: object,
    ) -> "PianoMatrix":
        """A silent matrix of ``frame_count`` frames."""
        if frame_count < 0:
            raise ValueError("frame_count cannot be negative")
        grid = np.zeros((KEY_COUNT, frame_count), dtype=np.int8)
        return cls(grid=grid, granularity=Granularity(granularity), tempo_bpm=tempo_bpm, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def time_based(
        cls,
        grid: np.ndarray | list[list[int]],
        frame_ms: float = DEFAULT_FRAME_MS,
        **kwargs: object,
    ) -> "PianoMatrix":
        """A matrix whose columns are wall clock, not note figures (D-01).

        The 1.x fields still exist on the object because the storage layer, the hand splitter and
        the editing operations all read them, and they leave in Phase 4. They carry placeholders
        here and nothing may use them for timing: :attr:`time_step_seconds` comes from ``frame_ms``,
        and :attr:`beats_per_column` raises, because a frame has no beat value.
        """
        array = np.asarray(grid, dtype=np.int8)
        defaults: dict[str, object] = {
            "granularity": Granularity.SEMIFUSA,
            "tempo_bpm": 60.0,
        }
        defaults.update(kwargs)
        return cls(grid=array, frame_ms=validate_frame_ms(frame_ms), **defaults)  # type: ignore[arg-type]

    @classmethod
    def time_based_from_coo(
        cls,
        payload: SparseCooMatrix | dict,
        frame_ms: float = DEFAULT_FRAME_MS,
        **kwargs: object,
    ) -> "PianoMatrix":
        """Read a stored wall-clock matrix back from the wire format.

        The pair to :meth:`time_based`: the frame length comes from the folder
        the file was found in, and no tempo takes part.
        """
        dense = cls.from_coo_payload(payload).grid
        return cls.time_based(dense, frame_ms=frame_ms, **kwargs)

    @classmethod
    def from_dense(
        cls,
        dense: np.ndarray | list[list[int]],
        granularity: Granularity | str = Granularity.SEMICORCHEA,
        tempo_bpm: float = 60.0,
        *,
        frames_as_rows: bool = False,
        **kwargs: object,
    ) -> "PianoMatrix":
        """Build from a dense grid.

        ``frames_as_rows=False`` (default) expects the **88 x N** orientation.
        ``frames_as_rows=True`` expects the **N x 88** JSON export orientation
        and transposes it — the one place that flip is allowed to happen here.
        """
        array = np.asarray(dense, dtype=np.int8)
        if frames_as_rows:
            array = array.T
        return cls(grid=array, granularity=Granularity(granularity), tempo_bpm=tempo_bpm, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_coo_payload(
        cls,
        payload: SparseCooMatrix | dict,
        granularity: Granularity | str = Granularity.SEMICORCHEA,
        tempo_bpm: float = 60.0,
        **kwargs: object,
    ) -> "PianoMatrix":
        """Build from the Task 1.3.1 wire format."""
        model = (
            payload
            if isinstance(payload, SparseCooMatrix)
            else SparseCooMatrix.model_validate(payload)
        )
        grid = np.zeros((model.shape[0], model.shape[1]), dtype=np.int8)
        for row, col, onset in zip(model.rows, model.cols, model.onset):
            grid[row, col] = ONSET if onset != -1 else SUSTAIN
        return cls(grid=grid, granularity=Granularity(granularity), tempo_bpm=tempo_bpm, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_envelope(cls, envelope: PianoMatrixEnvelope) -> "PianoMatrix":
        """Build the one-hand matrix carried by an envelope."""
        common = {
            "granularity": envelope.granularity,
            "tempo_bpm": envelope.tempo_bpm,
            "processing_step": envelope.matrix_processing_step,
            "key_signature": envelope.key_signature,
            "title": envelope.title,
        }
        if envelope.matrix is not None:
            return cls.from_coo_payload(envelope.matrix, **common)  # type: ignore[arg-type]
        if envelope.dense_matrix is not None:
            return cls.from_dense(envelope.dense_matrix, frames_as_rows=True, **common)  # type: ignore[arg-type]
        raise ValueError("Envelope carries no one-hand matrix (it is probably two-hands)")

    @classmethod
    def load_npz(
        cls,
        path: Path,
        granularity: Granularity | str = Granularity.SEMICORCHEA,
        tempo_bpm: float = 60.0,
        **kwargs: object,
    ) -> "PianoMatrix":
        """Read a matrix persisted by :meth:`save_npz`."""
        from aitu_backend.storage.matrix_store import load_matrix

        return cls.from_coo_payload(load_matrix(path), granularity, tempo_bpm, **kwargs)

    # --------------------------------------------------------------- geometry

    @property
    def frame_count(self) -> int:
        """Number of time frames (columns)."""
        return int(self.grid.shape[1])

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.grid.shape[0]), int(self.grid.shape[1])

    @property
    def time_step_seconds(self) -> float:
        """Seconds per column.

        On a time matrix this is ``frame_ms / 1000`` and nothing else takes part. On a 1.x matrix it
        is still ``beats_per_column * 60 / tempo_bpm``, which is the calculation this refactor
        removes.
        """
        if self.frame_ms is not None:
            return seconds_per_frame(self.frame_ms)
        return seconds_per_column(self.granularity, self.tempo_bpm)

    @property
    def beats_per_column(self) -> float:
        """How many negras one column lasts. A time matrix has no answer to this.

        The question only makes sense when the column *is* a note figure. Raising here is what stops
        a beat value leaking back into the layout through a module that was written before the
        refactor.
        """
        if self.frame_ms is not None:
            raise ValueError(
                "A time matrix has no beats per column: a frame is "
                f"{self.frame_ms} ms of wall clock, not a note figure."
            )
        return beats_per_column(self.granularity)

    @property
    def duration_seconds(self) -> float:
        return self.frame_count * self.time_step_seconds

    def is_empty(self) -> bool:
        """True when no key sounds anywhere."""
        return not bool(np.any(self.grid))

    # ----------------------------------------------------------- timing math

    def frame_to_time(self, frame: int) -> float:
        """Start time in seconds of a frame. Frame ``0`` starts at ``0.0``."""
        return frame * self.time_step_seconds

    def time_to_frame(self, seconds: float) -> int:
        """Frame containing ``seconds``, floored — the frame that is sounding."""
        if seconds < 0:
            raise ValueError("Time cannot be negative")
        return int(seconds // self.time_step_seconds)

    def frames_for_seconds(self, seconds: float) -> int:
        """How many frames a duration of ``seconds`` spans, rounded to nearest."""
        if seconds < 0:
            raise ValueError("Duration cannot be negative")
        return int(round(seconds / self.time_step_seconds))

    def frame_to_beats(self, frame: int) -> float:
        """Position of a frame in beats (negras) from the start."""
        return frame * self.beats_per_column

    # -------------------------------------------------------------- accessors

    def cell(self, row: int, column: int) -> int:
        return int(self.grid[row, column])

    def row_of(self, note: str) -> int:
        """Row index of a Spanish note name, e.g. ``"Do-4"``."""
        return note_to_row(note)

    def row_for_note(self, note: str) -> np.ndarray:
        """The whole row for a note name, as a view."""
        return self.grid[note_to_row(note)]

    def active_rows(self) -> list[int]:
        """Row indices that sound at least once, ascending."""
        return np.nonzero(np.any(self.grid != SILENCE, axis=1))[0].astype(int).tolist()

    def onsets_in_column(self, column: int) -> list[int]:
        """Row indices struck in ``column``."""
        return np.nonzero(self.grid[:, column] == ONSET)[0].astype(int).tolist()

    def key_names(self) -> list[str]:
        """The canonical 88 Spanish key names, row order."""
        return build_grand_piano_rows()

    # ------------------------------------------------------------ conversions

    def to_dense(self, frames_as_rows: bool = False) -> list[list[int]]:
        """Dense grid as plain lists. ``frames_as_rows`` gives the N x 88 export form."""
        array = self.grid.T if frames_as_rows else self.grid
        return array.astype(int).tolist()

    def to_array(self) -> np.ndarray:
        """A copy of the backing array, so callers cannot mutate this matrix."""
        return self.grid.copy()

    def to_coo_payload(self) -> SparseCooMatrix:
        """The Task 1.3.1 wire format, sorted by ``(col, row)``."""
        # Iterating column-major yields (col, row) order directly.
        cols, rows = np.nonzero(self.grid.T)
        rows_list = rows.astype(int).tolist()
        cols_list = cols.astype(int).tolist()
        onset = [
            row if self.grid[row, col] == ONSET else -1 for row, col in zip(rows_list, cols_list)
        ]
        return SparseCooMatrix(
            shape=[self.shape[0], self.shape[1]],
            rows=rows_list,
            cols=cols_list,
            onset=onset,
        )

    def to_envelope(self, sparse: bool = True) -> PianoMatrixEnvelope:
        """Wrap this matrix in the export envelope."""
        return PianoMatrixEnvelope(
            tempo_bpm=self.tempo_bpm,
            time_step_seconds=self.time_step_seconds,
            granularity=self.granularity,
            matrix_processing_step=self.processing_step,
            sparse=sparse,
            matrix=self.to_coo_payload() if sparse else None,
            dense_matrix=None if sparse else self.to_dense(frames_as_rows=True),
            key_signature=self.key_signature,
            title=self.title,
        )

    def save_npz(self, path: Path) -> Path:
        """Persist as compressed sparse ``.npz`` (see `storage/matrix_store.py`)."""
        from aitu_backend.storage.matrix_store import save_matrix

        return save_matrix(path, self.to_coo_payload())

    # -------------------------------------------------------------- structure

    def copy(self) -> "PianoMatrix":
        """Deep copy — the grid is copied, not shared."""
        return PianoMatrix(
            grid=self.grid.copy(),
            granularity=self.granularity,
            tempo_bpm=self.tempo_bpm,
            processing_step=self.processing_step,
            key_signature=self.key_signature,
            title=self.title,
            hand=self.hand,
            frame_ms=self.frame_ms,
        )

    def with_grid(self, grid: np.ndarray, **overrides: object) -> "PianoMatrix":
        """A new matrix with a different grid, keeping (or overriding) metadata."""
        fields: dict[str, object] = {
            "granularity": self.granularity,
            "tempo_bpm": self.tempo_bpm,
            "processing_step": self.processing_step,
            "key_signature": self.key_signature,
            "title": self.title,
            "hand": self.hand,
            "frame_ms": self.frame_ms,
        }
        fields.update(overrides)
        return PianoMatrix(grid=np.asarray(grid, dtype=np.int8), **fields)  # type: ignore[arg-type]

    def slice_frames(self, start: int, end: int) -> "PianoMatrix":
        """Columns ``[start, end)`` as a new matrix.

        The slice is taken as-is: a note held across ``start`` keeps its ``-1``
        opening cell. Promoting that orphan sustain to an onset is the
        validator's ``normalize`` (Task 2.1.2), so the policy lives in one place.
        """
        if not 0 <= start <= end <= self.frame_count:
            raise ValueError(f"Frame range [{start}, {end}) outside 0..{self.frame_count}")
        return self.with_grid(self.grid[:, start:end].copy())

    def __len__(self) -> int:
        return self.frame_count

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PianoMatrix):
            return NotImplemented
        return (
            self.frame_ms == other.frame_ms
            and self.granularity == other.granularity
            and self.tempo_bpm == other.tempo_bpm
            and self.processing_step == other.processing_step
            and self.shape == other.shape
            and bool(np.array_equal(self.grid, other.grid))
        )

    def __repr__(self) -> str:
        timing = (
            f"{self.frame_ms:g} ms/frame"
            if self.frame_ms is not None
            else f"{self.granularity.value}, {self.tempo_bpm} BPM"
        )
        return (
            f"PianoMatrix({self.shape[0]}x{self.shape[1]}, {timing}, "
            f"{self.processing_step.value}, "
            f"{int(np.count_nonzero(self.grid))} active cells)"
        )
