"""Note events -> the raw piano matrix.

The raw matrix is built at **fusa** granularity, always, whatever the user
finally wants to see. It is the immutable source every recompute starts from
(Task 2.2.1), so it is deliberately the finest resolution the project allows
short of semifusa — fine enough to keep the performance, coarse enough that a
five-minute piece stays a few thousand columns.

Placement follows Appendix C via :mod:`aitu_backend.matrix.approximation`:
onsets snap to the nearest column, durations round to the nearest column and
are then expressible in at most two figures.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aitu_backend.matrix.approximation import DEFAULT_ONSET_TOLERANCE, snap_note
from aitu_backend.matrix.keys import KEY_COUNT, build_grand_piano_rows, midi_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import normalize, validate
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import ONSET, SUSTAIN, Granularity, MatrixProcessingStep
from aitu_backend.transcription.engine import NoteEvent

#: The raw matrix is always built here. See the module docstring.
RAW_GRANULARITY = Granularity.FUSA


@dataclass
class BuildReport:
    """What happened while placing events, including what could not be placed."""

    matrix: PianoMatrix
    placed: int = 0
    #: Events whose MIDI note fell outside the 88 keys.
    dropped_out_of_range: list[int] = field(default_factory=list)
    #: Events that landed past the end of the grid.
    dropped_past_end: int = 0
    #: Notes shortened because the next strike of the same key arrived first.
    truncated: int = 0

    @property
    def lossless(self) -> bool:
        return not self.dropped_out_of_range and self.dropped_past_end == 0

    def describe(self) -> str:
        parts = [f"{self.placed} note(s) placed"]
        if self.dropped_out_of_range:
            names = sorted(set(self.dropped_out_of_range))
            parts.append(f"{len(self.dropped_out_of_range)} outside the 88 keys (MIDI {names})")
        if self.dropped_past_end:
            parts.append(f"{self.dropped_past_end} past the end of the grid")
        if self.truncated:
            parts.append(f"{self.truncated} shortened by a re-strike")
        return "; ".join(parts) + "."


def column_count(
    duration_seconds: float,
    tempo_bpm: float,
    granularity: Granularity = RAW_GRANULARITY,
) -> int:
    """How many columns an audio of this length needs. Always at least 1."""
    if duration_seconds <= 0:
        raise ValueError(f"Duration must be positive, got {duration_seconds}")
    step = granularity.seconds(tempo_bpm)
    return max(1, int(np.ceil(duration_seconds / step)))


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


def events_to_raw_matrix(
    events: list[NoteEvent],
    duration_seconds: float,
    tempo_bpm: float,
    *,
    granularity: Granularity = RAW_GRANULARITY,
    tolerance: float = DEFAULT_ONSET_TOLERANCE,
    title: str | None = None,
    reporter: BaseProgress | None = None,
) -> BuildReport:
    """Place note events onto a fresh raw matrix.

    Rules, in order of precedence:

    * A note outside the 88 keys is **dropped and reported**, never wrapped.
    * A note whose onset lands past the last column is dropped and reported;
      the grid is sized from the audio, so this means the engine hallucinated
      past the end.
    * **A new onset always wins over a carried sustain**, per the transition
      rules — so two overlapping events on the same key become two notes, the
      first shortened. That is the same simplification Appendix B makes.
    """
    frames = column_count(duration_seconds, tempo_bpm, granularity)
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    report = BuildReport(
        matrix=PianoMatrix(
            grid=grid,
            granularity=granularity,
            tempo_bpm=tempo_bpm,
            processing_step=MatrixProcessingStep.RAW,
            title=title,
        )
    )

    progress = default_reporter(reporter)
    # Sorting by start means a later onset always overwrites an earlier tail.
    ordered = sorted(events, key=lambda event: (event.start, event.midi_note))

    with progress.stage("events", total=max(1, len(ordered))) as stage:
        for event in ordered:
            try:
                row = midi_to_row(event.midi_note)
            except ValueError:
                report.dropped_out_of_range.append(event.midi_note)
                stage.advance()
                continue

            snapped = snap_note(
                row,
                event.start,
                event.duration,
                granularity,
                tempo_bpm,
                tolerance=tolerance,
            )
            start = snapped.start_column
            if start >= frames:
                report.dropped_past_end += 1
                stage.advance()
                continue

            end = min(frames, snapped.end_column)
            if grid[row, start] != 0 or (end > start + 1 and np.any(grid[row, start + 1 : end])):
                report.truncated += 1

            grid[row, start] = ONSET
            if end > start + 1:
                grid[row, start + 1 : end] = SUSTAIN

            report.placed += 1
            stage.advance()

    matrix = report.matrix.with_grid(grid)
    # Strict-mode check, then normalize: placement cannot legally produce an
    # orphan sustain, but a future engine or a hand-built event list might.
    violations = validate(matrix)
    if violations:
        matrix = normalize(matrix)
    report.matrix = matrix
    return report


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
