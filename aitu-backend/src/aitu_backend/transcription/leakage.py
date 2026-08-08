"""Onset leakage: a key that is already sounding "re-onsets" on another key's attack.

An onset-detection head listens for a broadband transient. A piano chord *is* a
broadband transient, so when a chord lands on top of a note that is still ringing,
the head can fire for the ringing pitch too. The post-processor then closes that
note and opens a new one at the chord's instant, and the model reports two events
where the player struck one key once.

Observed in ``When I Was Your Man`` at 12.3 s::

    Sol-3  11.8964 -> 12.3000  v73     one G3, held for a quarter
    Sol-3  12.3140 -> 12.7100  v66     <- the same G3, split in two
    Do-4   12.3067 -> 13.1200  v87   } the chord whose attack caused the split
    Mi-4   12.3073 -> 13.1200  v82   }

The offset at 12.3000 and the re-onset at 12.3140 are 14 ms apart. **No pianist
can re-articulate a key in 14 ms** — the damper has to fall and the hammer has to
be re-cocked — so the second event is not a performance, it is a detector artifact.
Left alone it quantises into the chord's column and the score prints a Do-Mi-Sol
chord where the music has a Do-Mi chord followed by a Sol.

Four conditions, and why each is needed
---------------------------------------

Every one of these was added because the rule without it fired on a note the
player really struck. The numbers quoted are from the reference file, 1117 events.

**1. The two events abut.** Offset-to-re-onset within ``max_gap_seconds``.
Necessary, but nowhere near sufficient: this engine's offsets are weak — a note is
usually reported as ringing until the next thing happens — so 716 of its 1079
consecutive same-pitch pairs abut within 20 ms, most of them genuine repeats.

**2. Asymmetric company.** The suspect onset ``B`` coincides with some other key's
attack, and the onset it would merge into, ``A``, did not. When a chord is
genuinely re-struck every note in it re-onsets together, so the previous strike of
that pitch sat in a chord too and nothing is merged. A phantom is asymmetric by
construction: it is born from a chord its predecessor was not part of.

**3. ``B`` lags the cluster that caused it.** Struck-together keys arrive within a
millisecond or so of each other; a leaked detection is a secondary response to
somebody else's transient and shows up a few milliseconds behind *all* of them.
This is what rescues the anticipated bass note::

    Re-3   8.0592 ->  9.8300  v97     lands 135 ms before the chord at 8.194
    Re-3   9.8385 -> 11.4947  v96     <- REAL: the whole D7 chord re-strikes here
    La-3   9.8376   Do-4 9.8376   Re-2 9.8401   Fa-3 9.8440

Re-3 satisfies conditions 1 and 2 and is not a phantom at all. It is *inside* the
cluster's own spread (-5.5 ms relative to the last arrival), where the Sol-3
phantom sits 6.7 ms behind the last of its two.

**4. ``B`` is quieter than ``A``.** A leaked onset has little real energy at that
pitch, so the velocity regression scores it low; a genuine re-strike in the same
passage is played about as hard as the one before it. The Sol-3 phantom drops
73 -> 66; the Re-3 re-strike holds 97 -> 96, and the G2 at 22.9957 s — another real
re-strike that clears conditions 1 and 2 — actually rises 82 -> 83.

Together the four keep **8 of 1117 events** (0.7%) on the reference file, all of
the same shape. That is deliberately high-precision and low-recall: a phantom that
survives is a wrong note on the page, which is visible and can be merged by hand,
while a false merge silently deletes a note the player played. When in doubt this
module does nothing.

This runs on note events, in seconds, **before** anything meets a grid — the only
place where "14 ms" is still a number rather than a rounding decision.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from aitu_backend.transcription.engine import NoteEvent


@dataclass(frozen=True)
class LeakageConfig:
    """Thresholds of the leakage rule. Seconds and MIDI velocity, not columns."""

    #: Largest offset-to-re-onset gap still treated as "the same key never stopped".
    #: 40 ms is comfortably above this engine's 5-20 ms abutting gaps and far below
    #: the ~130 ms of the fastest repeated note anyone writes.
    max_gap_seconds: float = 0.040

    #: How close another key's attack must be to count as coincident.
    coincidence_seconds: float = 0.040

    #: A re-onset that *precedes* its predecessor's offset by more than this is
    #: overlapping rather than abutting, which means something else is going on.
    max_overlap_seconds: float = 0.010

    #: How far behind the last coincident attack the suspect onset must sit.
    #: Measured chord spread on the reference file: median 3.1 ms, p99 12.9 ms —
    #: but the *last* two arrivals of a chord are a median 0.9 ms apart, and it is
    #: that trailing distance this compares against.
    min_lag_seconds: float = 0.003

    #: How much quieter the suspect onset must be than the note it merges into.
    min_velocity_drop: int = 3

    def validate(self) -> None:
        if self.max_gap_seconds < 0 or self.coincidence_seconds < 0:
            raise ValueError("Leakage thresholds must be non-negative")
        if self.min_lag_seconds < 0 or self.min_velocity_drop < 0:
            raise ValueError("Leakage thresholds must be non-negative")


#: Applied unless a caller says otherwise.
DEFAULT_LEAKAGE = LeakageConfig()


@dataclass(frozen=True)
class Merge:
    """One phantom absorbed back into the note it was split from."""

    midi_note: int
    #: Where the surviving note begins.
    kept_start: float
    #: Where the phantom claimed a new strike. This is the onset that disappears.
    phantom_start: float
    #: Offset-to-re-onset distance, seconds.
    gap_seconds: float
    #: How many other keys attacked within the coincidence window.
    co_onsets: int
    #: How far behind the last of them the phantom arrived, seconds.
    lag_seconds: float
    #: Velocity lost against the note it merges into, always positive.
    velocity_drop: int

    def describe(self) -> str:
        return (
            f"MIDI {self.midi_note} at {self.phantom_start:.4f}s merged into "
            f"{self.kept_start:.4f}s (gap {self.gap_seconds * 1000:.1f}ms, "
            f"{self.co_onsets} co-onset(s), lag {self.lag_seconds * 1000:.1f}ms, "
            f"velocity -{self.velocity_drop})"
        )


@dataclass
class LeakageReport:
    """What the filter did, in enough detail to argue with."""

    merges: list[Merge] = field(default_factory=list)

    @property
    def merged(self) -> int:
        return len(self.merges)

    def describe(self) -> str:
        if not self.merges:
            return "no leaked re-onsets found."
        pitches = sorted({merge.midi_note for merge in self.merges})
        return (
            f"{self.merged} leaked re-onset(s) merged back "
            f"across {len(pitches)} pitch(es) (MIDI {pitches})."
        )


def merge_leaked_onsets(
    events: list[NoteEvent],
    config: LeakageConfig | None = None,
) -> tuple[list[NoteEvent], LeakageReport]:
    """Absorb phantom re-onsets into the notes they were split from.

    Returns a new event list — the input is never mutated — sorted the way
    :func:`~aitu_backend.transcription.events_to_matrix.events_to_raw_matrix`
    wants it, plus a report naming every merge and the evidence for it.

    A merged note keeps the **earlier** onset, its velocity and its identity, and
    takes the **later** offset: the phantom was never a strike, only a seam in the
    middle of one note, so what survives is the note the player actually played.

    Decided in one pass over the original events, applied in a second. Nothing is
    judged against a note that another merge already lengthened, so the result
    does not depend on iteration order and a second run is a no-op. Consecutive
    seams in one long note therefore heal only when *each* of them independently
    earns it — which is the conservative reading, and the intended one.
    """
    config = config or DEFAULT_LEAKAGE
    config.validate()
    report = LeakageReport()
    if len(events) < 2:
        return list(events), report

    # One sorted table of every original onset, for the coincidence test.
    onsets = sorted((event.start, event.midi_note) for event in events)
    starts = [start for start, _ in onsets]

    def coincident(time: float, exclude_midi: int) -> list[float]:
        """Onset times of *other* keys within the coincidence window of ``time``."""
        window = config.coincidence_seconds
        first = bisect.bisect_left(starts, time - window)
        last = bisect.bisect_right(starts, time + window)
        return [start for start, midi in onsets[first:last] if midi != exclude_midi]

    by_pitch: dict[int, list[NoteEvent]] = {}
    for event in events:
        by_pitch.setdefault(event.midi_note, []).append(event)
    for group in by_pitch.values():
        group.sort(key=lambda event: event.start)

    # Pass 1: judge every original adjacent pair on its own.
    leaked: dict[int, set[int]] = {}
    for midi, group in by_pitch.items():
        for index in range(1, len(group)):
            before, suspect = group[index - 1], group[index]

            gap = suspect.start - before.end
            if not -config.max_overlap_seconds <= gap <= config.max_gap_seconds:
                continue
            company = coincident(suspect.start, midi)
            if not company or coincident(before.start, midi):
                continue
            lag = suspect.start - max(company)
            if lag < config.min_lag_seconds:
                continue
            drop = before.velocity - suspect.velocity
            if drop < config.min_velocity_drop:
                continue

            leaked.setdefault(midi, set()).add(index)
            report.merges.append(
                Merge(
                    midi_note=midi,
                    kept_start=before.start,
                    phantom_start=suspect.start,
                    gap_seconds=gap,
                    co_onsets=len(company),
                    lag_seconds=lag,
                    velocity_drop=drop,
                )
            )

    # Pass 2: absorb each phantom into whatever note now precedes it.
    kept: list[NoteEvent] = []
    for midi, group in by_pitch.items():
        phantoms: set[int] = leaked.get(midi, set())
        current = group[0]
        for index in range(1, len(group)):
            candidate = group[index]
            if index in phantoms:
                current = NoteEvent(
                    midi_note=midi,
                    start=current.start,
                    end=max(current.end, candidate.end),
                    velocity=current.velocity,
                )
                continue
            kept.append(current)
            current = candidate
        kept.append(current)

    kept.sort(key=lambda event: (event.start, event.midi_note))
    report.merges.sort(key=lambda merge: (merge.phantom_start, merge.midi_note))
    return kept, report


__all__ = [
    "DEFAULT_LEAKAGE",
    "LeakageConfig",
    "LeakageReport",
    "Merge",
    "merge_leaked_onsets",
]
