"""The wall-clock pipeline, in one place and in one order.

```text
raw onsets and sustains (events.json, kept forever)
  -> impose the granularity   group on raw times, snap to frames, keep the full sustain
  -> split the hands          everything after this point measures one hand at a time
  -> the two hand matrices: the hand split the new sheet starts from (`pipeline.starting_hands`)
```

That is the whole of it, and the order is fixed (D-31). Two properties are worth stating plainly
because every later phase depends on them.

**`frameMs` is a parameter.** A piece can be re-run at 20 or 30 ms and nothing structural changes:
the same raw events go in, the grouping window follows the frame length, and the result is the same
music on a finer or coarser grid. No step may assume 40.

**The split happens here, not later.** The new sheet (implementation 03) starts from one hand per
note, so the hands have to exist before anything is written.

The matrix that exists between those two steps, the whole keyboard before the split, never leaves
the backend. There is no `raw` step in the stored format: a piece is always two hands, and a
one-hand piece is two hands with one of them empty (contract §2).

Phase 4 rewires `pipeline.py` around this module and deletes the 1.x path beside it. Implementation
03, Phase 10 removed what this module built for the vexflow-v2 sheet (the score payload, the time
matrix envelope, the attack times of a hand).
"""

from __future__ import annotations

from dataclasses import dataclass

from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, validate_frame_ms
from aitu_backend.hands import progress as hand_progress
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN
from aitu_backend.transcription.artifacts import DEFAULT_ARTIFACTS, ArtifactConfig
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import TimeBuildReport, events_to_time_matrix
from aitu_backend.transcription.leakage import DEFAULT_LEAKAGE, LeakageConfig

__all__ = [
    "TimeHands",
    "impose_granularity_and_split",
    "pin_hands",
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
    # A note a reader has taken off the recording never reaches the grid. This is the one place it
    # is dropped, so every consumer of a matrix — the gap plot, the sheet, the printed page — agrees
    # about it without any of them having to know the flag exists.
    events = [event for event in events if not event.removed]
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
    # In hundredths: the beam search is the first 60, the second pass the rest (measured on three
    # pieces, the beam takes half to two thirds of the time). Only a change of a whole hundredth
    # is published, so a long piece sends at most a hundred ticks.
    with progress.stage("two-hands", total=100, message="inferring hands") as stage:
        done = 0

        def moved(part: str, fraction: float) -> None:
            nonlocal done
            at = int(fraction * 60) if part == "beam" else 60 + int(fraction * 40)
            if at > done:
                stage.advance(at - done, message="searching" if part == "beam" else "checking")
                done = at

        with hand_progress.listening(moved):
            hands = split_hands(build.matrix, method=hand_method)
        stage.advance(100 - done)
    pinned = pin_hands(hands.right, hands.left, events, build)
    return TimeHands(
        frame_ms=step,
        right=pinned[0],
        left=pinned[1],
        unsplit=build.matrix,
        build=build,
    )


def pin_hands(
    right: PianoMatrix,
    left: PianoMatrix,
    events: list[NoteEvent],
    build: TimeBuildReport,
) -> tuple[PianoMatrix, PianoMatrix]:
    """Move the notes a person has assigned a hand to onto that hand.

    The split is a guess made by an algorithm that cannot see the player's hands, and a pianist
    reading the page can often see at a glance where it is wrong. When they say so, the answer is
    written onto the note event itself and the matrix is built with it — so it is not an overlay
    that the drawing has to remember to apply, it is what the two hands *are* from here on. Every
    figure, beam, clef and octave bracket is then derived from the corrected matrix by the ordinary
    path, with nothing anywhere that could disagree with it.

    Applied after the inference rather than as a constraint inside it. The beam search would give a
    better answer if it knew the pins while it worked, but this is honest about what it is — the
    reader's correction laid over the guess — and it cannot make the search fail to converge or
    quietly change decisions the reader did not ask about.

    A note is found by the raw time it was played at, not by a column, so a pin survives a change of
    column length: the same correction holds at 20 ms as at 40.
    """
    pins = [event for event in events if event.hand in ("right", "left")]
    if not pins:
        return right, left

    # (row, seconds) -> column, from the record of where each key's own attack landed.
    where: dict[tuple[int, float], int] = {}
    for (column, row), seconds in build.event_seconds.items():
        where[row, round(seconds, 4)] = column

    planes = {"right": right, "left": left}
    for event in pins:
        row = event.midi_note - LOWEST_MIDI
        column = where.get((row, round(event.start, 4)))
        if column is None:
            continue
        source = next(
            (plane for plane in planes.values() if plane.cell(row, column) == ONSET),
            None,
        )
        target = planes[event.hand]
        if source is None or source is target:
            continue
        # Refused rather than merged when the far hand already strikes that key in that frame. The
        # two planes may not hold the same onset, and losing one of them would lose a note that was
        # really played.
        if target.cell(row, column) != SILENCE:
            continue
        follower = column
        while follower < source.frame_count and (
            follower == column or source.cell(row, follower) == SUSTAIN
        ):
            target.grid[row, follower] = source.grid[row, follower]
            source.grid[row, follower] = SILENCE
            follower += 1
    return right, left

