"""Notes too short to have been played: the masking artifact, removed at source.

What this is
------------

Transcribing an octave is the hardest thing a piano model does. Every partial of
the upper note lands on an even partial of the lower one, so the upper note adds
almost no new spectral evidence and the model has to infer it from the attack
transient alone. It gets it wrong in both directions: sometimes it misses the
upper note, and sometimes it invents a note an octave *below* the real bass —
David's ``Fa-1`` under a played ``Fa-2``/``Fa-3``.

The invented ones give themselves away by their length. Measured on Mr Blue Sky
(2751 events), the durations are cleanly bimodal:

======================  =======
Duration                Events
======================  =======
4 – 16 ms               78
**16 – 32 ms**          **0**
32 ms and up            2673
======================  =======

Nothing at all in between. The short cluster is not a tail of the real
distribution, it is a separate population — and one that could not be a played
note anyway: a hammer needs tens of milliseconds to produce a tone a listener
can place, and the fastest real note in this piece is 32 ms. Of those 78, all 78
coincide with another attack and 51 sit exactly one or two octaves below a note
in that same attack. That is the masking artifact, named and counted.

Why it runs first
-----------------

Before the hand split, because one phantom bass note wrecks it. A played
``Fa-2``/``Fa-3`` octave with a phantom ``Fa-1`` under it spans two octaves,
which no hand can hold, so the splitter is forced to give ``Fa-3`` to the right
hand — and from there the whole assignment unravels. Removing the phantom is
the difference between the splitter solving the problem the player posed and
solving one the model invented.

Before the leakage filter too (:mod:`.leakage`), whose asymmetry test asks which
other keys attacked alongside a suspect note. Artifacts in that answer are noise.

Why the floor is where it is
----------------------------

**20 ms, and it must not be raised much.** The floor is set to sit inside the
empty band, as far from the real notes as from the artifacts. It is tempting to
push it to 40 ms — nothing in *this* file would notice — and that would be a
trap: the ByteDance offsets this was measured on are long, because they follow
the pedal rather than the key. An engine that reports true key release gives much
shorter notes for the same music. Transkun, on this same audio, returns notes of
34 – 85 ms for a passage ByteDance calls 200 – 1700 ms. A 40 ms floor would
silently delete a third of a Transkun transcription. 20 ms is below anything any
engine will call a real note and above the entire artifact cluster.

Nothing is deleted from ``events.json``: that file is the engine's verbatim
output and stays that way. This filter runs on the way out, so every rebuild
gets it — including the files transcribed before it existed — and so the raw
falling view can still show what was discarded when asked.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aitu_backend.transcription.engine import NoteEvent


@dataclass(frozen=True)
class ArtifactConfig:
    """When a note is too short to have been played."""

    #: Notes shorter than this are candidates. See the module docstring for why
    #: raising it is dangerous: engines that report true key release, rather
    #: than pedal release, legitimately emit 35 ms notes.
    min_duration_seconds: float = 0.020
    #: How close another attack must be for the masking mechanism to explain
    #: this note. The artifact is created *by* a struck chord, so one has to be
    #: there; a short note alone in silence is something else and is kept.
    coincidence_seconds: float = 0.050
    #: Set false to disable the corroboration and drop on duration alone.
    require_coincident_attack: bool = True


DEFAULT_ARTIFACTS = ArtifactConfig()


@dataclass(frozen=True)
class DroppedNote:
    """One discarded note and why it looked like an artifact."""

    event: NoteEvent
    #: Semitones to the nearest note struck alongside it, above this one.
    #: ``12`` or ``24`` is the octave-masking signature.
    octave_below: int | None

    def describe(self) -> str:
        relation = f", {self.octave_below} semitones under a struck note" if self.octave_below else ""
        return f"MIDI {self.event.midi_note} at {self.event.start:.3f}s, " f"{self.event.duration * 1000:.1f} ms{relation}"


@dataclass
class ArtifactReport:
    """What survived, what did not, and what the discards looked like."""

    kept: list[NoteEvent] = field(default_factory=list)
    dropped: list[DroppedNote] = field(default_factory=list)
    #: Short notes kept because nothing was struck alongside them — the masking
    #: mechanism cannot explain those, so they are somebody else's problem.
    kept_isolated: int = 0

    @property
    def octave_phantoms(self) -> int:
        return sum(1 for note in self.dropped if note.octave_below is not None)

    def describe(self) -> str:
        if not self.dropped:
            return f"No artifacts; {len(self.kept)} note(s) kept."
        parts = [
            f"{len(self.dropped)} artifact(s) dropped of {len(self.kept) + len(self.dropped)}",
            f"{self.octave_phantoms} an exact octave under a struck note",
        ]
        if self.kept_isolated:
            parts.append(f"{self.kept_isolated} short but isolated, kept")
        return "; ".join(parts) + "."


def _octave_below(event: NoteEvent, neighbours: list[NoteEvent], window: float) -> int | None:
    """``12`` or ``24`` when a note that far above was struck alongside this one."""
    for other in neighbours:
        if other is event or abs(other.start - event.start) > window:
            continue
        distance = other.midi_note - event.midi_note
        if distance in (12, 24):
            return distance
    return None


def drop_artifacts(
    events: list[NoteEvent],
    config: ArtifactConfig = DEFAULT_ARTIFACTS,
) -> ArtifactReport:
    """Remove notes too short to have been played, keeping a record of each.

    Order is not disturbed: what comes back is the input minus the discards.
    """
    report = ArtifactReport()
    if not events:
        return report

    ordered = sorted(events, key=lambda event: event.start)
    starts = [event.start for event in ordered]

    # A short list per candidate rather than a scan of everything: the window is
    # 50 ms and a piece has thousands of notes.
    import bisect  # noqa: PLC0415

    for event in events:
        if event.duration >= config.min_duration_seconds:
            report.kept.append(event)
            continue

        window = config.coincidence_seconds
        low = bisect.bisect_left(starts, event.start - window)
        high = bisect.bisect_right(starts, event.start + window)
        neighbours = [other for other in ordered[low:high] if other is not event]

        if config.require_coincident_attack and not neighbours:
            report.kept.append(event)
            report.kept_isolated += 1
            continue

        report.dropped.append(
            DroppedNote(event=event, octave_below=_octave_below(event, neighbours, window))
        )

    return report
