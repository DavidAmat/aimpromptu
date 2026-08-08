"""Chord and arpeggio grouping, on raw times, before anything is snapped to a column.

A chord is one rhythmic event even when the three keys land eight milliseconds apart. If those eight
milliseconds are left in, they dominate the low end of the distribution of gaps between onsets and
the peak the user is asked to name disappears under them.

The grouping runs on the **raw float timestamps** and never on columns (D-04). Two onsets 39 ms
apart can straddle a frame boundary, so "same column, therefore same chord" is true or false
depending on where the pair happens to fall in the piece. Grouping first and snapping the whole
group together removes that dependency: the group has one onset time, and that one time picks the
column.

The window is **one frame wide** and follows ``frameMs`` (D-04). One parameter controls the whole
convergence step, so a piece rendered at 20 ms groups at 20 ms and nothing else has to be adjusted.

The rule is **non-chaining**. A group is opened by an onset and admits every later onset within the
window of the group's *first* onset, never of the previous one. Chaining would let a fast run
swallow itself one small hop at a time until half a bar was one chord.

Ported from ``poc-onset-duration-distribution/scripts/common.py::collapse_attacks``, which is the
tested implementation the measurement in ``RESULTS.md`` was produced with. The difference here is
that this returns the whole group rather than only its start time, because the pipeline needs to
know which notes belong together, not just when the attack happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.transcription.engine import NoteEvent

__all__ = [
    "DEFAULT_GROUP_WINDOW_MS",
    "OnsetGroup",
    "group_onsets",
    "group_start_seconds",
]

#: Onsets within one frame of the group's first onset are one attack (D-04). The window is the frame
#: length, so it moves with the per-piece parameter rather than being a second number to keep in step.
DEFAULT_GROUP_WINDOW_MS = DEFAULT_FRAME_MS


@dataclass
class OnsetGroup:
    """One attack: every note struck close enough together to be read as a single event.

    ``start_seconds`` is the raw onset of the **first** note in the group, not an average. It is the
    single time that decides the group's column, so keeping it exact keeps the snapping honest.
    """

    #: Position in the piece, counting from 0. Becomes ``groupId`` in the score payload (D-04).
    index: int
    #: Raw onset of the first note in the group, in seconds.
    start_seconds: float
    events: list[NoteEvent] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.events)

    @property
    def spread_ms(self) -> float:
        """How far apart the first and last notes of the attack are, in milliseconds.

        Never more than the window. Useful for diagnosing an arpeggio that was rolled slowly enough
        to be split into two attacks.
        """
        if not self.events:
            return 0.0
        return (max(event.start for event in self.events) - self.start_seconds) * 1000.0

    @property
    def midi_notes(self) -> list[int]:
        return sorted(event.midi_note for event in self.events)


def group_onsets(
    events: list[NoteEvent],
    window_ms: float = DEFAULT_GROUP_WINDOW_MS,
) -> list[OnsetGroup]:
    """Collect note events into attacks, on raw times, without chaining.

    Events are read in order of onset, and ties are broken by MIDI note so that the result does not
    depend on the order the engine happened to emit. An empty list gives an empty list.

    Raises ``ValueError`` if the window is not a positive number of milliseconds, because a window of
    zero silently turns every note of a chord into its own attack and the failure would only show up
    much later, as a histogram with a large spike near zero.
    """
    if window_ms <= 0:
        raise ValueError(f"The grouping window must be a positive number of ms, got {window_ms}")
    if not events:
        return []

    window_seconds = window_ms / 1000.0
    ordered = sorted(events, key=lambda event: (event.start, event.midi_note))

    groups: list[OnsetGroup] = []
    current = OnsetGroup(index=0, start_seconds=ordered[0].start, events=[ordered[0]])
    for event in ordered[1:]:
        if event.start - current.start_seconds > window_seconds:
            groups.append(current)
            current = OnsetGroup(index=len(groups), start_seconds=event.start, events=[event])
        else:
            current.events.append(event)
    groups.append(current)
    return groups


def group_start_seconds(groups: list[OnsetGroup]) -> list[float]:
    """The attack times, in order. This is what the interval statistics in Phase 2 measure."""
    return [group.start_seconds for group in groups]
