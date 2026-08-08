"""Build the demo pieces the rhythm work is reviewed on.

These are written by hand rather than transcribed, because a review needs a piece whose right answer
is known before the app is opened. A real recording tells you the sheet looks plausible; a piece
whose every onset was placed on purpose tells you whether the sheet is *right*.

Two pieces are made:

* **Even and swung** — a straight run against a shuffled one, for the peak plot. A straight piece
  gives one tall pile, a shuffled one gives two whose lengths add up to a beat.
* **Classical mix** — the hard one. The left hand plays tresillos all the way through while the
  right hand enters a beat-and-a-half late and plays everything else, so the two hands never line
  up and the left-hand notes fall between the right-hand ones. That interleaving is what most of
  classical piano writing looks like and is where a page either reads or falls apart.

Run it with the backend's own environment so the pieces land in the same store the app reads:

    uv run python scripts/make_demo_pieces.py

Then pick the piece by name in **Playground → Upload / Input → the audio library**. Running it twice
replaces the pieces rather than adding a second copy of each.
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aitu_backend.audio import store  # noqa: E402
from aitu_backend.storage import paths  # noqa: E402
from aitu_backend.transcription import pipeline  # noqa: E402

SAMPLE_RATE = 16_000

#: Fixed so re-running gives the same piece rather than a second copy of it.
EVEN_AND_SWUNG_UUID = "11111111-1111-4111-8111-111111111111"
CLASSICAL_MIX_UUID = "22222222-2222-4222-8222-222222222222"


@dataclass(frozen=True)
class Note:
    """One key, in seconds. ``start`` is the attack; ``end`` is the release."""

    midi: int
    start: float
    end: float


# --------------------------------------------------------------------------- the classical mix

#: The beat of the classical piece. Every length below is written as a fraction of it, so changing
#: this one number moves the whole piece without changing a single figure on the page.
#:
#: 480 ms rather than something brisker because the piece contains a run of fusas, an eighth of a
#: beat each. At a negra of 300 those land 37 ms apart, under the default 40 ms column, and the
#: grouping rule quite correctly reads them as chords — two notes that close together were played
#: together. At 480 a fusa is 60 ms and the run reads as a run at the resolution the app opens on.
NEGRA = 0.480

#: The left hand's tresillo. Three of these fill one negra, and 100 ms is a poor corchea (150) and a
#: poor semicorchea (75) — which is the entire reason tresillos have to be recognised rather than
#: rounded. See D-32.
TRESILLO = NEGRA / 3

#: How far behind the left hand the right hand enters. Half a beat, so the two hands interleave for
#: the whole piece instead of sharing columns.
RIGHT_HAND_DELAY = NEGRA / 2

#: How much of its own length a note actually sounds for. Under 1 so consecutive notes on the same
#: key are two attacks rather than one long one; the printed figure comes from the gap to the next
#: onset (D-14) and not from this.
SOUNDING = 0.85

#: A left-hand line climbing two octaves and coming back down, sixteen notes.
#:
#: Shaped to be one long beam that nothing can split by itself. The package already breaks a beam at
#: a returning low note — a figure that comes back to its bottom C is two gestures and is grouped as
#: two without being asked. This line has no interior low note: it climbs, turns once at the top,
#: and descends. Every rule available sees one run, so it prints as one beam of sixteen.
#:
#: A reader looking at it still wants it in two, at the turn. That judgement is not derivable from
#: the notes, and it is what "break the beam here" is for.
ARPEGGIO = (36, 40, 43, 48, 52, 55, 60, 64, 60, 55, 52, 48, 43, 40, 38, 36)


def classical_mix() -> tuple[str, list[Note]]:
    """The left hand in tresillos throughout, the right hand in everything else, half a beat late."""
    # The right hand: one of each thing the page has to be able to draw.
    right = [
        # negras, then a held blanca
        (72, NEGRA),
        (74, NEGRA),
        (76, 2 * NEGRA),
        # four corcheas, which have to beam as one run
        (77, NEGRA / 2),
        (79, NEGRA / 2),
        (81, NEGRA / 2),
        (79, NEGRA / 2),
        # a tresillo in the right hand too, against the left hand's
        (83, TRESILLO),
        (81, TRESILLO),
        (79, TRESILLO),
        # a dotted negra, then a negra
        (77, NEGRA * 1.5),
        (76, NEGRA),
        # two corcheas and four semicorcheas under one beam, with a second beam level on the four
        (74, NEGRA / 2),
        (76, NEGRA / 2),
        (77, NEGRA / 4),
        (79, NEGRA / 4),
        (77, NEGRA / 4),
        (76, NEGRA / 4),
        # a negra, then a run of fusas: three beam levels
        (74, NEGRA),
        *[(midi, NEGRA / 8) for midi in (72, 74, 76, 77, 79, 77, 76, 74)],
        # a blanca, two more tresillos, a negra, and a redonda
        (72, 2 * NEGRA),
        *[(midi, TRESILLO) for midi in (74, 76, 77, 79, 77, 76)],
        (74, NEGRA),
        (72, 4 * NEGRA),
    ]
    notes: list[Note] = []
    clock = RIGHT_HAND_DELAY
    for midi, length in right:
        notes.append(sound(midi, clock, length))
        clock += length

    # The left hand's tresillos run under all of that, and stop where it stops. Counted from the
    # right hand's length so neither hand is left playing alone for a page.
    tresillos_end = clock
    beat = 0.0
    while beat + NEGRA <= tresillos_end:
        for step, midi in enumerate((48, 55, 52)):
            notes.append(sound(midi, beat + step * TRESILLO, TRESILLO))
        beat += NEGRA

    # Then the two long runs, one in corcheas and one in semicorcheas, with the right hand holding
    # above them. Sixteen notes each and no boundary inside either, so each is one beam of sixteen —
    # which is exactly what nobody wants to read, and what "break the beam here" is for.
    for length in (NEGRA / 2, NEGRA / 4):
        for step, midi in enumerate(ARPEGGIO):
            notes.append(sound(midi, clock + step * length, length))
        held = len(ARPEGGIO) * length
        # A negra to close the run. Without it the two runs are one unbroken row of beamable notes
        # and beam as a single group of thirty-two: a beam stops at the first note that cannot be
        # under one, and this is that note.
        notes.append(sound(ARPEGGIO[0], clock + held, NEGRA))
        notes.append(Note(midi=79, start=round(clock, 6), end=round(clock + held + NEGRA, 6)))
        clock += held + NEGRA

    return "Classical mix: tresillos, runs and holds", notes


# --------------------------------------------------------------------------- even and swung


#: How a shuffled pair divides its beat: long, then short.
#:
#: Measured off a real recording rather than chosen. A player does not swing to an exact ratio, and
#: the number matters: at 63/37 both halves are nearer a corchea than anything else and both print
#: as one, which is what a printed sheet of a swung piece shows (D-12). At a hard 2:1 the short half
#: is exactly a semicorchea and prints as one, which is also correct and is a different rhythm.
SWING_LONG = 0.63


def even_and_swung() -> tuple[str, list[Note]]:
    """A straight run, then the same notes shuffled. One pile on the plot, then two."""
    notes: list[Note] = []
    clock = 0.0
    line = (72, 74, 76, 77, 79, 77, 76, 74)

    for _ in range(2):  # straight: every gap the same
        for midi in line:
            notes.append(sound(midi, clock, NEGRA / 2))
            clock += NEGRA / 2

    clock += NEGRA
    for _ in range(2):  # swung: long, short, long, short
        for index, midi in enumerate(line):
            share = SWING_LONG if index % 2 == 0 else 1 - SWING_LONG
            notes.append(sound(midi, clock, NEGRA * share))
            clock += NEGRA * share

    # A held bass under both, so the piece has two hands.
    notes.append(sound(48, 0.0, clock))
    return "Even and swung", notes


# --------------------------------------------------------------------------- writing them out


def sound(midi: int, start: float, length: float) -> Note:
    return Note(midi=midi, start=round(start, 6), end=round(start + length * SOUNDING, 6))


def write_piece(audio_uuid: str, alias: str, title: str, notes: list[Note]) -> None:
    """Replace this piece in the store: its audio, its metadata and its raw events."""
    directory = paths.audio_dir(audio_uuid)
    if directory.exists():
        shutil.rmtree(directory)

    duration = math.ceil(max(note.end for note in notes)) + 1.0
    stored = store.create(
        alias=alias,
        source="recording",
        extension="wav",
        audio_uuid=audio_uuid,
        original_filename=f"{alias}.wav",
    )
    render_wav(stored.directory / "original.wav", notes, duration)
    shutil.copyfile(stored.directory / "original.wav", stored.directory / "normalized.wav")
    store.update(audio_uuid, duration_seconds=duration, sample_rate=SAMPLE_RATE)

    events_path = pipeline.events_path(audio_uuid)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "durationSeconds": duration,
                "title": title,
                "events": [
                    {
                        "midiNote": note.midi,
                        "start": note.start,
                        "end": note.end,
                        "velocity": 64,
                    }
                    for note in sorted(notes, key=lambda note: (note.start, note.midi))
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"{alias}: {len(notes)} notes, {duration:.1f} s — {audio_uuid}")


def render_wav(path: Path, notes: list[Note], duration: float) -> None:
    """A plain sine per note with a short attack and a decay, mixed and clipped.

    Deliberately dull. The audio exists so the **Play the recording** button has something to play
    against the page (D-29); it is not trying to sound like a piano.
    """
    samples = [0.0] * int(duration * SAMPLE_RATE)
    for note in notes:
        frequency = 440.0 * 2 ** ((note.midi - 69) / 12)
        first = int(note.start * SAMPLE_RATE)
        count = max(1, int((note.end - note.start) * SAMPLE_RATE))
        for offset in range(count):
            index = first + offset
            if index >= len(samples):
                break
            seconds = offset / SAMPLE_RATE
            attack = min(1.0, seconds / 0.005)
            decay = math.exp(-seconds * 4.0)
            samples[index] += 0.22 * attack * decay * math.sin(2 * math.pi * frequency * seconds)

    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32000)) for value in samples
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(frames)


def main() -> None:
    paths.ensure_data_tree()
    title, notes = even_and_swung()
    write_piece(EVEN_AND_SWUNG_UUID, "even-and-swung", title, notes)
    title, notes = classical_mix()
    write_piece(CLASSICAL_MIX_UUID, "classical-mix", title, notes)
    print("\nOpen Playground → Upload / Input and pick one from the audio library.")


if __name__ == "__main__":
    main()
