"""The wall-clock pipeline, in one place and in one order.

```text
raw onsets and sustains (events.json, kept forever)
  -> impose the granularity   group on raw times, snap to frames, keep the full sustain
  -> split the hands          everything after this point measures one hand at a time
  -> the two hand matrices, ready to be measured (Phase 2) and labelled (Phase 3)
```

That is the whole of it, and the order is fixed (D-31). Two properties are worth stating plainly
because every later phase depends on them.

**`frameMs` is a parameter.** A piece can be re-run at 20 or 30 ms and nothing structural changes:
the same raw events go in, the grouping window follows the frame length, and the result is the same
music on a finer or coarser grid. No step may assume 40.

**The split happens here, not later.** Gaps between onsets are measured per hand, because the gaps
between a right-hand run and a held left-hand chord are not a rhythm and would bury the peak the
user is meant to name. So the hands have to exist before anything is measured.

The matrix that exists between those two steps, the whole keyboard before the split, never leaves
the backend. There is no `raw` step in the stored format: a piece is always two hands, and a
one-hand piece is two hands with one of them empty (contract §2).

Phase 4 rewires `pipeline.py` around this module and deletes the 1.x path beside it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.passages import ladder_ranges, one_passage
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, validate_frame_ms
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import SparseCooMatrix
from aitu_backend.notation.figures import onset_columns, printed_notes_of_hand
from aitu_backend.schemas.time_matrix import (
    FigureLadder,
    FigureOverride,
    LayoutHints,
    Passage,
    TimeMatrixEnvelope,
    TimeMatrixProcessingStep,
    TimeScorePayload,
)
from aitu_backend.transcription.artifacts import DEFAULT_ARTIFACTS, ArtifactConfig
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import TimeBuildReport, events_to_time_matrix
from aitu_backend.transcription.leakage import DEFAULT_LEAKAGE, LeakageConfig

__all__ = [
    "TimeHands",
    "attack_seconds_of_hand",
    "attack_times_of_hand",
    "impose_granularity_and_split",
    "layout_hints_for",
    "to_score_payload",
    "trim_to_music",
    "to_time_envelope",
]


@dataclass
class TimeHands:
    """What the pipeline produces: two aligned hand matrices on a wall-clock grid."""

    frame_ms: float
    right: PianoMatrix
    left: PianoMatrix
    #: The whole keyboard before the split. Kept for diagnostics; never stored or sent.
    unsplit: PianoMatrix
    build: TimeBuildReport

    @property
    def frame_count(self) -> int:
        return self.right.frame_count

    @property
    def duration_seconds(self) -> float:
        return self.frame_count * self.frame_ms / 1000.0

    @property
    def is_right_hand_only(self) -> bool:
        return self.left.is_empty() and not self.right.is_empty()

    @property
    def is_left_hand_only(self) -> bool:
        return self.right.is_empty() and not self.left.is_empty()

    def describe(self) -> str:
        return (
            f"{self.frame_count} columns of {self.frame_ms:g} ms; {self.build.describe()[:-1]}; "
            f"split into {len(self.right.active_rows())} right and "
            f"{len(self.left.active_rows())} left keys."
        )


def impose_granularity_and_split(
    events: list[NoteEvent],
    duration_seconds: float,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    hand_method: str | None = None,
    title: str | None = None,
    leakage: LeakageConfig | None = DEFAULT_LEAKAGE,
    artifacts: ArtifactConfig | None = DEFAULT_ARTIFACTS,
    reporter: BaseProgress | None = None,
) -> TimeHands:
    """Raw events in, two hand matrices out. The only two steps, in order.

    Re-running with a different ``frame_ms`` starts again from the same events and produces the same
    music on a different grid. Nothing is carried over, so there is no state that could only make
    sense at one frame length.
    """
    step = validate_frame_ms(frame_ms)
    build = events_to_time_matrix(
        events,
        duration_seconds,
        frame_ms=step,
        title=title,
        leakage=leakage,
        artifacts=artifacts,
        reporter=reporter,
    )
    progress = default_reporter(reporter)
    # Named so the progress bar shows it. The old `derive` wrapped the split in a
    # stage of its own, and losing it would make the bar jump from the events
    # straight to the end on the slowest step of a long piece.
    with progress.stage("two-hands", total=1, message="inferring hands") as stage:
        hands = split_hands(build.matrix, method=hand_method)
        stage.advance()
    return TimeHands(
        frame_ms=step,
        right=hands.right,
        left=hands.left,
        unsplit=build.matrix,
        build=build,
    )


def to_time_envelope(
    hands: TimeHands,
    *,
    duration_seconds: float | None = None,
    title: str | None = None,
    key_signature: str | None = None,
) -> TimeMatrixEnvelope:
    """The stored and transmitted form: always two hands (contract §2).

    A one-hand piece is not a different shape. It is two hands with one of them empty, and the
    renderer is told to hide that staff through :func:`layout_hints_for`. Keeping one shape means
    every consumer, every stored file and every test stays on one code path.
    """
    return TimeMatrixEnvelope(
        frame_ms=hands.frame_ms,
        frame_count=hands.frame_count,
        duration_seconds=hands.duration_seconds if duration_seconds is None else duration_seconds,
        title=title if title is not None else hands.right.title,
        key_signature=key_signature,
        matrix_processing_step=TimeMatrixProcessingStep.TWO_HANDS,
        r_matrix=_coo(hands.right),
        l_matrix=_coo(hands.left),
    )


def layout_hints_for(
    hands: TimeHands,
    *,
    frame_group: int = 25,
    frame_measure: int = 100,
    silence_group_px: float = 6.0,
) -> LayoutHints:
    """Which staves to draw, and the two wall-clock aggregation levels above the frame.

    The defaults are one second and four seconds at 40 ms. They are frame counts rather than
    durations, so a piece at 20 ms should halve them to keep the dashed lines in the same place on
    the clock.
    """
    return LayoutHints(
        frame_group=frame_group,
        frame_measure=frame_measure,
        silence_group_px=silence_group_px,
        hide_left_hand=hands.is_right_hand_only,
        hide_right_hand=hands.is_left_hand_only,
    )


def _coo(matrix: PianoMatrix) -> SparseCooMatrix:
    return matrix.to_coo_payload()


def attack_seconds_of_hand(hands: TimeHands, hand: str) -> dict[int, float]:
    """Column -> when **this hand** really attacked in it, in seconds.

    Not the column's group time. Grouping runs before the hand split (D-31), so a column's group
    time is the earliest onset in it whichever hand played it. A right-hand note played 20 ms behind
    a left-hand one shares its column and would inherit its time, which shortens the gap to the next
    right-hand note by 20 ms — a third of a fusa, and enough to print one as a semifusa. Every gap
    in D-14 is a gap within one hand, so it is measured from that hand's own attack.

    The group time remains the fallback for a column with no per-key record, which happens for a
    matrix loaded from disk rather than built in this run.
    """
    matrix = hands.right if hand == "right" else hands.left
    rows_at: dict[int, list[int]] = {}
    for column in onset_columns(matrix):
        rows_at[column] = list(matrix.onsets_in_column(column))

    own: dict[int, float] = {}
    for (column, row), seconds in hands.build.event_seconds.items():
        if row in rows_at.get(column, ()):
            known = own.get(column)
            own[column] = seconds if known is None else min(known, seconds)
    return {
        **{
            column: hands.build.attack_seconds[column]
            for column in rows_at
            if column in hands.build.attack_seconds
        },
        **own,
    }


def attack_times_of_hand(hands: TimeHands, hand: str) -> list[float]:
    """When this hand attacked, in seconds, in order.

    The raw time the attack was really played at, not the start of its column. Phase 2 measures the
    gaps between these values, which is what D-07 asks for: the snap is undone by looking the time
    back up rather than by multiplying a column index.
    """
    matrix = hands.right if hand == "right" else hands.left
    seconds = attack_seconds_of_hand(hands, hand)
    return [
        seconds.get(column, column * hands.frame_ms / 1000.0) for column in onset_columns(matrix)
    ]


def to_score_payload(
    hands: TimeHands,
    ladder: FigureLadder,
    *,
    passages: list[Passage] | None = None,
    overrides: list[FigureOverride] | None = None,
    layout: LayoutHints | None = None,
    title: str | None = None,
    key_signature: str | None = None,
    duration_seconds: float | None = None,
    trim_trailing_silence: bool = True,
) -> TimeScorePayload:
    """Everything the renderer draws, assembled from the two hands and one named ladder.

    The figure of every note is decided here, not in the renderer (contract §6), so the ladder, the
    proportional comparison and the closed vocabulary all live on one side. The renderer draws what
    it is told and applies the per-note overrides on top.

    ``passages`` defaults to a single passage covering the piece, which is what a user gets before
    they have drawn any boundary.

    Silence after the last note is cut off. A recording often runs on for several seconds after the
    playing stops, and drawing that gives a page of empty staff with nothing on it. The recording is
    untouched; only the sheet stops where the music does.
    """
    hands = trim_to_music(hands) if trim_trailing_silence else hands
    tiles = passages or one_passage(hands.frame_count, ladder)
    ranges = ladder_ranges(tiles)
    tail = hands.duration_seconds if duration_seconds is None else duration_seconds

    notes = []
    tuplet_id = 0
    for hand, matrix in (("right", hands.right), ("left", hands.left)):
        printed = printed_notes_of_hand(
            matrix,
            hand,
            ranges,
            attack_seconds=attack_seconds_of_hand(hands, hand),
            group_id=hands.build.group_id,
            frame_ms=hands.frame_ms,
            tail_seconds=tail,
            # Numbered across the whole piece, so the two hands cannot claim the same tresillo.
            tuplet_start_id=tuplet_id,
        )
        used = [note.tuplet_id for note in printed if note.tuplet_id is not None]
        tuplet_id = max(used) + 1 if used else tuplet_id
        notes.extend(printed)
    notes.sort(key=lambda note: (note.start_frame, note.hand, note.row))

    return TimeScorePayload(
        envelope=to_time_envelope(
            hands,
            duration_seconds=duration_seconds,
            title=title,
            key_signature=key_signature,
        ),
        passages=tiles,
        notes=notes,
        overrides=overrides or [],
        layout=layout or layout_hints_for(hands),
    )


def trim_to_music(hands: TimeHands) -> TimeHands:
    """The same hands, ending where the last note stops sounding.

    A page of empty staff is not a rest, it is a recording that kept running. The audio still knows
    its own length, and playback still uses it; this only decides where the sheet ends.
    """
    sounding = np.nonzero(np.any(hands.unsplit.grid != 0, axis=0))[0]
    if sounding.size == 0:
        return hands
    end = int(sounding[-1]) + 1
    if end >= hands.frame_count:
        return hands
    return TimeHands(
        frame_ms=hands.frame_ms,
        right=hands.right.slice_frames(0, end),
        left=hands.left.slice_frames(0, end),
        unsplit=hands.unsplit.slice_frames(0, end),
        build=hands.build,
    )
