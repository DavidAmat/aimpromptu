"""Note events -> the wall-clock piano matrix.

A column is a fixed slice of wall clock, 40 ms by default, and no tempo takes part (D-01). Onsets
round to the nearest column (D-02), which makes the result depend on the recording and on nothing
else: the same audio gives the same columns, every time, with no number for anybody to type in.

Three rules decide what reaches the grid, in this order:

* **Notes shorter than one column are dropped** (D-05). A note that does not last a single frame is
  the engine's octave-masking artifact rather than something a person played.
* **Near-simultaneous onsets are grouped first, on raw times** (D-04, see
  :mod:`aitu_backend.transcription.grouping`), and the whole group snaps to one column together.
  Grouping after snapping would be phase-dependent, because two notes 39 ms apart can fall either
  side of a boundary.
* **The sustain written into the grid is measured and complete**, from the note's own release
  (D-06). Nothing is cut here: a redonda has no length until the user names a peak, so the cap is
  applied when the score payload is built. The sustain is also not the printed length of the note,
  which is the gap to the next onset in the same hand. The two must never be derived from each
  other.

One filter runs before placement: :mod:`aitu_backend.transcription.leakage` merges phantom
re-onsets, a ringing key that the model split in two at another key's attack, because that
judgement needs the events in seconds. By the time they are columns a 14 ms seam and a genuine
repeated note look identical.

The tempo-based builder that used to sit beside this one was deleted in P4.2, together with the
granularity hierarchy it placed notes on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aitu_backend.matrix.keys import KEY_COUNT, build_grand_piano_rows, midi_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.time_grid import (
    DEFAULT_FRAME_MS,
    MS_PER_SECOND,
    frame_count_for_duration,
    frame_of_seconds,
)
from aitu_backend.matrix.validator import normalize, validate
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import ONSET, SUSTAIN, MatrixProcessingStep
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.artifacts import (
    DEFAULT_ARTIFACTS,
    ArtifactConfig,
    ArtifactReport,
    drop_artifacts,
)
from aitu_backend.transcription.grouping import group_onsets
from aitu_backend.transcription.leakage import (
    DEFAULT_LEAKAGE,
    LeakageConfig,
    LeakageReport,
    merge_leaked_onsets,
)


def shift_events(events: list[NoteEvent], offset_seconds: float) -> list[NoteEvent]:
    """Move every event earlier by ``offset_seconds``, dropping what falls before 0.

    Used for range-limited transcription: the engine sees a clip that starts at
    the range start, so its times are already relative — but when the engine is
    given the whole file and the caller wants a range, this rebases them.
    """
    shifted: list[NoteEvent] = []
    for event in events:
        start = event.start - offset_seconds
        end = event.end - offset_seconds
        if end <= 0:
            continue
        shifted.append(
            NoteEvent(
                midi_note=event.midi_note,
                start=max(0.0, start),
                end=end,
                velocity=event.velocity,
            )
        )
    return shifted


def note_names_of(events: list[NoteEvent]) -> list[str]:
    """Spanish names of the events that fit on the keyboard. For logs and tests."""
    names = build_grand_piano_rows()
    result: list[str] = []
    for event in events:
        try:
            result.append(names[midi_to_row(event.midi_note)])
        except ValueError:
            continue
    return result


@dataclass
class TimeBuildReport:
    """What happened while placing events on a wall-clock grid, including what was refused."""

    matrix: PianoMatrix
    #: Attacks found by the grouping step. One chord counts once.
    groups: int = 0
    #: Column -> the raw onset time of the attack that landed there, in seconds.
    #:
    #: This is how the exact playing survives the snap. Phase 2 measures the gaps between these
    #: values rather than between column indices (D-07), and Phase 3 uses them for the printed
    #: length of a note. Without it the only gap available downstream would be a whole number of
    #: frames, and a 211 ms gap would arrive as 200.
    attack_seconds: dict[int, float] = field(default_factory=dict)
    #: ``(column, row)`` -> the raw onset time of that particular key, in seconds.
    #:
    #: Finer than :attr:`attack_seconds`, and needed because grouping runs before the hand split. A
    #: column's group time is the earliest onset in it whichever hand played it, so a right-hand
    #: note 20 ms behind a left-hand one inherits the left hand's time and its gap to the next
    #: right-hand note comes out 20 ms short — enough to change a fusa into a semifusa. Per hand,
    #: the gap has to be measured from that hand's own attack.
    event_seconds: dict[tuple[int, int], float] = field(default_factory=dict)
    #: Column -> the sequential number of that attack. Becomes ``groupId`` in the payload (D-04).
    #: Shared across both hands, because the grouping ran before the split.
    group_id: dict[int, int] = field(default_factory=dict)
    placed: int = 0
    #: Events whose MIDI note fell outside the 88 keys.
    dropped_out_of_range: list[int] = field(default_factory=list)
    #: Events that landed past the end of the grid.
    dropped_past_end: int = 0
    #: Notes shorter than one frame, refused per D-05.
    dropped_sub_frame: int = 0
    #: Notes shortened because the next strike of the same key arrived first.
    truncated: int = 0
    #: Phantom re-onsets merged away before placement. See :mod:`.leakage`.
    leakage: LeakageReport = field(default_factory=LeakageReport)
    #: Notes too short to have been played, removed first. See :mod:`.artifacts`.
    artifacts: ArtifactReport = field(default_factory=ArtifactReport)

    @property
    def lossless(self) -> bool:
        return not self.dropped_out_of_range and self.dropped_past_end == 0

    def describe(self) -> str:
        parts = [f"{self.placed} note(s) placed in {self.groups} attack(s)"]
        if self.dropped_sub_frame:
            parts.append(f"{self.dropped_sub_frame} shorter than one frame")
        if self.dropped_out_of_range:
            names = sorted(set(self.dropped_out_of_range))
            parts.append(f"{len(self.dropped_out_of_range)} outside the 88 keys (MIDI {names})")
        if self.dropped_past_end:
            parts.append(f"{self.dropped_past_end} past the end of the grid")
        if self.truncated:
            parts.append(f"{self.truncated} shortened by a re-strike")
        if self.leakage.merged:
            parts.append(f"{self.leakage.merged} leaked re-onset(s) merged")
        if self.artifacts.dropped:
            parts.append(
                f"{len(self.artifacts.dropped)} artifact(s) dropped "
                f"({self.artifacts.octave_phantoms} phantom octaves)"
            )
        return "; ".join(parts) + "."


def events_to_time_matrix(
    events: list[NoteEvent],
    duration_seconds: float,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    group_window_ms: float | None = None,
    title: str | None = None,
    leakage: LeakageConfig | None = DEFAULT_LEAKAGE,
    artifacts: ArtifactConfig | None = DEFAULT_ARTIFACTS,
    reporter: BaseProgress | None = None,
) -> TimeBuildReport:
    """Place note events on a wall-clock grid. No tempo, anywhere.

    The steps, in the order they have to run:

    1. Drop the engine's artifacts, then merge phantom re-onsets. Both judgements need the events in
       seconds, so they run before anything is snapped.
    2. Drop notes shorter than one frame (D-05).
    3. Group near-simultaneous onsets on raw times, one frame wide (D-04). ``group_window_ms``
       overrides that only for tests; leaving it unset keeps the window and the frame in step.
    4. Snap each group to one column, and write the full measured sustain (D-02, D-06).

    A new onset always wins over a sustain that is still running on the same key, so two overlapping
    events on one key become two notes with the first shortened. That is the same simplification the
    1.x builder makes and it is what ``report.truncated`` counts.

    The sustain is measured from the note's own release, not from the group's, and it is stored in
    full. Capping it at a redonda needs a ladder, and no ladder exists yet: until the user has said
    "one negra = X ms" there is no way to know whether a long sustain is a redonda. The cap is
    applied in Phase 3, where the passage and its ladder are known (D-06). A chord whose notes are
    released at different moments keeps that difference in the grid, because the grid is a record of
    what was played.
    """
    window_ms = frame_ms if group_window_ms is None else group_window_ms
    frames = frame_count_for_duration(duration_seconds, frame_ms)
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    report = TimeBuildReport(
        matrix=PianoMatrix.time_based(
            grid,
            frame_ms=frame_ms,
            processing_step=MatrixProcessingStep.RAW,
            title=title,
        )
    )

    progress = default_reporter(reporter)
    if artifacts is not None:
        report.artifacts = drop_artifacts(events, artifacts)
        events = report.artifacts.kept
    if leakage is not None:
        events, report.leakage = merge_leaked_onsets(events, leakage)

    # D-05. A note that does not last one frame cannot be drawn and was almost certainly never
    # played; the artifact filter above catches most of them, and this catches the rest at whatever
    # frame length this piece uses.
    playable: list[NoteEvent] = []
    for event in events:
        if event.duration * MS_PER_SECOND < frame_ms:
            report.dropped_sub_frame += 1
        else:
            playable.append(event)

    groups = group_onsets(playable, window_ms=window_ms)
    report.groups = len(groups)

    with progress.stage("events", total=max(1, len(groups))) as stage:
        for group in groups:
            start = frame_of_seconds(group.start_seconds, frame_ms)
            if start >= frames:
                report.dropped_past_end += len(group.events)
                stage.advance()
                continue
            # Two attacks can still land in one column when the grid is coarser than the grouping
            # window. The first one owns the column, so the recorded time stays the earliest.
            report.attack_seconds.setdefault(start, group.start_seconds)
            report.group_id.setdefault(start, len(report.group_id))
            for event in sorted(group.events, key=lambda item: item.midi_note):
                try:
                    row = midi_to_row(event.midi_note)
                except ValueError:
                    report.dropped_out_of_range.append(event.midi_note)
                    continue

                known = report.event_seconds.get((start, row))
                report.event_seconds[start, row] = (
                    event.start if known is None else min(known, event.start)
                )

                end = min(frames, max(start + 1, frame_of_seconds(event.end, frame_ms)))
                if grid[row, start] != 0 or (
                    end > start + 1 and np.any(grid[row, start + 1 : end])
                ):
                    report.truncated += 1

                grid[row, start] = ONSET
                if end > start + 1:
                    grid[row, start + 1 : end] = SUSTAIN
                report.placed += 1
            stage.advance()

    matrix = report.matrix.with_grid(grid)
    violations = validate(matrix)
    if violations:
        matrix = normalize(matrix)
    report.matrix = matrix
    return report
