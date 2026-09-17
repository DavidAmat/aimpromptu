"""The piano overlay: per-key borders become every key and its lane.

Task 2.1.1 of implementation 04, rewritten by implementation 05 (V-37, V-38).
The user drags one rectangle over the piano area and the app finds every key
inside it; this module takes the :class:`Calibration` that came out — the border
of every key along the top edge of that rectangle — and answers, for every key
the picture shows, its type, its MIDI pitch, its left and right border in
picture x, its midpoint, and its vertical lane.

Three rules it obeys and never bends:

* **The pitch class comes from the black key pattern, the octave from the user**
  (V-10). Nothing here looks at a colour.
* **A lane is the key widened by a margin on both sides** (V-13), and the margin
  is measured in the **local** white key width — the width of the key being
  read — because perspective makes one white key wider than another (V-38).
* **A lane is a vertical strip of the picture** whatever the camera did to the
  piano, because the rectangles fall straight down the picture (V-39). So a
  border is turned into a picture x by projecting the top edge of the rectangle
  onto the horizontal: ``x = rect.x + u · cos(angle)``.

The frontend has the same geometry in `src/video/overlayGeometry.ts`, because
the calibration UI has to redraw it on every drag and a round trip per drag is
not a UI. `tests/test_video_geometry.py` and
`aitu-frontend/scripts/check-geometry.ts` both assert against
`tests/fixtures/video/geometry-fixture.json`, so the two cannot drift apart
without a check failing.
"""

from __future__ import annotations

import math

from aitu_backend.matrix.keys import CHROMATIC_EN, CHROMATIC_ES
from aitu_backend.schemas.video import (
    WHITE_PITCH_CLASSES,
    WHITE_WITH_BLACK_AFTER,
    Calibration,
    Geometry,
    KeyLane,
    PianoKey,
)

#: The lane margin of V-13, in local white key widths. Attribution has a measured
#: margin of 0.33 white key widths, so this is safe.
DEFAULT_LANE_MARGIN = 0.25


def top_edge_x(cal: Calibration, u: float) -> float:
    """The picture x under a point ``u`` along the top edge of the rectangle."""
    return cal.piano_rect.x + u * math.cos(math.radians(cal.piano_rect.angle))


def top_edge_u(cal: Calibration, x: float) -> float:
    """The inverse: how far along the top edge a picture x sits."""
    return (x - cal.piano_rect.x) / math.cos(math.radians(cal.piano_rect.angle))


def white_borders(cal: Calibration) -> list[float]:
    """The picture x of every white key border, left to right: one more than the keys."""
    return [top_edge_x(cal, u) for u in cal.white_borders]


def _name(midi: int) -> tuple[str, str]:
    """English and Spanish name of a MIDI pitch, from the canonical tables."""
    octave = midi // 12 - 1
    pitch_class = midi % 12
    return f"{CHROMATIC_EN[pitch_class]}{octave}", f"{CHROMATIC_ES[pitch_class]}-{octave}"


def keys(cal: Calibration) -> list[PianoKey]:
    """Every key the picture shows, sorted by pitch.

    The white keys come from their borders. A black key sits between two white
    keys whose pitch classes differ by two semitones — that is the whole rule,
    and it is why no black key appears between Mi and Fa or between Si and Do —
    and its own borders are the next entry of the calibration's list.
    """
    borders = white_borders(cal)
    out: list[PianoKey] = []

    first_index = WHITE_PITCH_CLASSES.index(cal.first_white_pitch_class)
    whites: list[tuple[int, int]] = []  # (midi, index of that white key)
    for i in range(len(borders) - 1):
        step = first_index + i
        octave = cal.first_white_octave + step // 7
        midi = 12 * (octave + 1) + WHITE_PITCH_CLASSES[step % 7]
        whites.append((midi, i))
        name_en, name_es = _name(midi)
        out.append(
            PianoKey(
                midi=midi,
                kind="white",
                name_en=name_en,
                name_es=name_es,
                left=borders[i],
                right=borders[i + 1],
                mid=(borders[i] + borders[i + 1]) / 2,
            )
        )

    slot = 0
    for midi_a, _ in whites[:-1]:
        if midi_a % 12 not in WHITE_WITH_BLACK_AFTER:
            continue
        black = cal.black_borders[slot]
        slot += 1
        black_midi = midi_a + 1
        left, right = top_edge_x(cal, black.left), top_edge_x(cal, black.right)
        name_en, name_es = _name(black_midi)
        out.append(
            PianoKey(
                midi=black_midi,
                kind="black",
                name_en=name_en,
                name_es=name_es,
                left=left,
                right=right,
                mid=(left + right) / 2,
            )
        )

    out.sort(key=lambda k: k.midi)
    return out


def local_widths(cal: Calibration) -> dict[int, float]:
    """The local white key width of every key, by MIDI pitch (V-38).

    A white key's own width; for a black key, the mean width of the two white
    keys it stands between. This is the unit for every length that is about one
    key: the lane margin, the extent window and the width gate.
    """
    all_keys = keys(cal)
    white_width = {k.midi: k.right - k.left for k in all_keys if k.kind == "white"}
    out: dict[int, float] = {}
    for key in all_keys:
        if key.kind == "white":
            out[key.midi] = white_width[key.midi]
        else:
            out[key.midi] = (white_width[key.midi - 1] + white_width[key.midi + 1]) / 2
    return out


def lanes(cal: Calibration, margin: float = DEFAULT_LANE_MARGIN) -> list[KeyLane]:
    """One vertical lane per key, widened by ``margin`` local white key widths (V-13)."""
    widths = local_widths(cal)
    return [
        KeyLane(
            midi=k.midi,
            kind=k.kind,
            x0=k.left - margin * widths[k.midi],
            x1=k.right + margin * widths[k.midi],
            mid=k.mid,
        )
        for k in keys(cal)
    ]


def geometry(cal: Calibration, margin: float = DEFAULT_LANE_MARGIN) -> Geometry:
    """The keys and their lanes in one answer — what the wire carries."""
    return Geometry(keys=keys(cal), lanes=lanes(cal, margin), margin=margin)


def guard_band_px(cal: Calibration, default_keys: float = 1.75) -> float:
    """How many rows above the upper line are not trusted (V-08, V-24).

    A video measures it from the motion of the roll and stores it. A screenshot
    has no motion to measure it from, so it falls back to the measured default of
    1.75 median white key widths — the median over the 21 examples was 1.73.
    """
    if cal.guard_band > 0:
        return cal.guard_band
    return default_keys * cal.white_width


def default_octave_for(white_count: int) -> int:
    """The octave to offer for the leftmost white key, from how many keys there are.

    88 keys start at A0 and 61 start at C2, which covers what these videos draw.
    It is a default the user can change, never an inference (V-10).

    The thresholds sit below the counts they stand for on purpose. A whole piano
    is 52 white keys, but the overlay is cut to the keys the picture shows and a
    screenshot often crops one or two off an end — so a 50 white key overlay is a
    whole piano, and guessing a five octave keyboard for it puts every name two
    octaves out.
    """
    if white_count >= 45:
        return 0
    if white_count >= 30:
        return 2
    return 3
