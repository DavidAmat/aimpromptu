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

**2. Asymmetric company.** The suspect onset ``B`` coincides with
``min_company_margin`` more other attacks than the onset it would merge into,
``A``, **and none of them is a key that attacked alongside ``A`` too**. A phantom
is asymmetric by construction: it is born from a chord its predecessor was not
part of.

Both halves are needed and each was put there by a measurement. Until 2026-08-10
this asked for ``A`` to have *no* company at all, which is too literal — a Si-b2
phantom survived because one unrelated key attacked 33 ms after its predecessor.
But a margin alone lets a genuine chord re-strike through: when the whole D7 chord
re-articulates at 9.838 s each of its notes sees two more neighbours than before.
The pitches give it away. It is the *same* chord, so the two sets overlap; a
phantom's do not.

**3. ``B`` sits near the cluster that caused it.** A leaked detection is a
secondary response to somebody else's transient, so it lands within a few
milliseconds of that attack — behind it, level with it, or a little ahead. The
window is one-sided only on the near side: ``lag_ahead_seconds`` bounds how far
*ahead* it may sit, and any distance behind is allowed.

This test used to demand the suspect arrive at least 3 ms **behind**, which was
one file's accident. Chopin's four phantoms arrive at -1.3, -8.2 and -11.5 ms and
walked straight through it.

The anticipated bass note the old floor protected::

    Re-3   8.0592 ->  9.8300  v97     lands 135 ms before the chord at 8.194
    Re-3   9.8385 -> 11.4947  v96     <- REAL: the whole D7 chord re-strikes here
    La-3   9.8376   Do-4 9.8376   Re-2 9.8401   Fa-3 9.8440

is now refused by condition 2 instead, and for the better reason: the whole chord
re-strikes at 9.838, so ``A`` sat in a chord of its own and the company margin is
not met.

**4. ``B`` is quieter than ``A``.** A leaked onset has little real energy at that
pitch, so the velocity regression scores it low; a genuine re-strike in the same
passage is played about as hard as the one before it. The Sol-3 phantom drops
73 -> 66; the Re-3 re-strike holds 97 -> 96, and the G2 at 22.9957 s — another real
re-strike that clears conditions 1 and 2 — actually rises 82 -> 83.

Together the four keep **8 of 1117 events** (0.7%) on the reference file, all of
the same shape. On Chopin's Nocturne Op. 9 no. 1 they merge 15 of 1864 events and
leave every note of the printed first three bars standing.

That is deliberately high-precision and low-recall: a phantom that
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

    #: How far *ahead* of the cluster's last arrival the suspect may sit and still be judged a
    #: phantom. Behind it, any distance is allowed.
    #:
    #: Replaces a one-sided ``min_lag_seconds`` of 3 ms, which demanded the suspect arrive *behind*
    #: the chord that caused it because the Mr Blue Sky phantom did (+6.7 ms). On Chopin's Nocturne
    #: Op. 9 no. 1 three phantoms arrive at −1.3, −8.2 and −11.5 ms — level with the cluster or
    #: slightly ahead of it — and were all let through. Which side of the attack a secondary
    #: detection lands on is a property of the model's receptive field, not of the playing, so
    #: demanding one sign was over-fitting to one file.
    #:
    #: The old floor also carried a second job: it protected an *anticipated* bass note, played
    #: 5.5 ms inside the cluster's own spread, from being merged. That job now belongs to
    #: :attr:`min_company_margin`, which refuses it for the better reason — the whole chord
    #: re-struck there, so its predecessor sat in a chord too.
    #:
    #: This does **not** widen the rule on its own: paired with the old ``onset_threshold`` of 0.3
    #: it merged away a real Fa4, because a phantom sitting beside that note inflated its company
    #: count. It is safe at :data:`~aitu_backend.transcription.engine.DEFAULT_ONSET_THRESHOLD`,
    #: where that phantom never exists.
    lag_ahead_seconds: float = 0.012

    #: How many *more* keys must attack alongside the suspect than alongside the note it would merge
    #: into.
    #:
    #: The asymmetry test used to demand the predecessor had **no** company at all, which is too
    #: literal. A Si-b2 phantom was let through because one unrelated key attacked 33 ms after its
    #: predecessor — not a chord, but enough to fail a test asking for zero. A margin says what the
    #: rule always meant: the suspect is born from a chord its predecessor was not part of.
    #:
    #: 2 rather than 1. At 1 the rule fires on a note whose predecessor merely had one fewer
    #: neighbour, which is noise; at 2 it wants a real difference in company. The measurement that
    #: fixes it: at :data:`~aitu_backend.transcription.engine.DEFAULT_ONSET_THRESHOLD` the surviving
    #: Chopin phantom has a margin of 2 and the real Fa4 beside it has a margin of 1.
    min_company_margin: int = 2

    #: How many keys may attack alongside **both** the suspect and the note it would merge into.
    #:
    #: Counting company is not enough on its own, and a fixture caught it: when the whole D7 chord
    #: re-articulates in *When I Was Your Man*, each of its notes sees two more neighbours than its
    #: predecessor did and clears the margin. What gives it away is *which* keys those are — the
    #: same ones both times, because it is the same chord struck twice.
    #:
    #: A phantom cannot look like that. It is born from a chord its predecessor was not part of, so
    #: the two sets are disjoint. Zero shared keys is the rule; the field exists so a caller can
    #: loosen it rather than to be tuned.
    max_shared_company: int = 0

    #: How much quieter the suspect onset must be than the note it merges into.
    min_velocity_drop: int = 3

    def validate(self) -> None:
        if self.max_gap_seconds < 0 or self.coincidence_seconds < 0:
            raise ValueError("Leakage thresholds must be non-negative")
        if self.min_velocity_drop < 0:
            raise ValueError("Leakage thresholds must be non-negative")
        if self.lag_ahead_seconds < 0 or self.min_company_margin < 1:
            raise ValueError(
                "lag_ahead_seconds must be non-negative and min_company_margin at least 1"
            )


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

    def coincident(time: float, exclude_midi: int) -> list[tuple[float, int]]:
        """``(onset time, key)`` of *other* keys within the coincidence window of ``time``.

        The key travels with the time because condition 2 asks not only how many keys attacked
        alongside the suspect but **which** — a chord struck twice shares its pitches, a phantom
        and its predecessor do not.
        """
        window = config.coincidence_seconds
        first = bisect.bisect_left(starts, time - window)
        last = bisect.bisect_right(starts, time + window)
        return [(start, midi) for start, midi in onsets[first:last] if midi != exclude_midi]

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
            if not company:
                continue
            earlier = coincident(before.start, midi)
            if len(company) - len(earlier) < config.min_company_margin:
                continue
            shared = {midi for _, midi in company} & {midi for _, midi in earlier}
            if len(shared) > config.max_shared_company:
                continue
            lag = suspect.start - max(start for start, _ in company)
            if lag < -config.lag_ahead_seconds:
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
