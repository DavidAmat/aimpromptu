"""What an old ``sheet.json`` (vexflow-v2) wrote that the new sheet keeps (implementation 03, Phase 9).

``sheet.json`` holds the reading a person made on the old sheet. Two of its decisions already reach the new sheet
through the algorithm's input (Phase 5, :func:`.build.reading_of`): the armadura and a reference figure renamed with
Transpose figures. This module lays the others on a frames sheet:

* **what the user wrote about the whole sheet** (:func:`carry`, always, when the sheet has none of it yet): the title
  lines, the lyrics pieces (their frames, words, size, lift and width, converted as the page converts them,
  ``useFramesLyrics.ts``), and a space between lines other than the old default;
* **the user's marks on notes** (always: a new AI run keeps them too, the user's answer of Phase 7): figures set by
  hand (``fix``) and fingers;
* **beam breaks and joins**, only on a sheet the AI did not write: beams are the AI's kind (plan section 3.7).

What is not carried (:func:`dropped`): the clef changes and octave lines (the user's answer of 2026-10-26: the new clef
rules everywhere; 36 of the 47 old sheets had them from the old page's automatic first write), the spacing tools,
print smaller and the unplayed decorations (dropped in Phases 7 and 8), and the notes taken off the page, which the
old sheet already removed in ``notes.pmn``.

Old marks are keyed by the onset cell of a note (``startFrame``, ``fromColumn``: the 40 ms column of its onset); the
new sheet draws a note at the column of its chord (D-04), at most one frame before its cell. The functions here only
change the sheet; :func:`.build.with_legacy` settles it (the rules run again) and checks it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn.dense import columns_of
from aitu_backend.pmn.notes import Notes
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.sheet.sheet.data import FRAME_MS, TITLE_FIELDS, Sheet
from aitu_backend.sheet.sheet.frames import STAFF_OF, drawn_columns

from . import reading

__all__ = ["Cells", "carry", "dropped", "has_marks"]

#: Pixels of the old sheet's words per staff space of the new one: its 12 px default is the new 1.4 (as the page).
PX_PER_SPACE = 12 / 1.4
#: The old sheet's space between lines when nobody changed it (pixels), and the new one's (staff spaces).
OLD_LINE_SPACING, LINE_SPACE = 72.0, 5.0
#: The old figure names as figures of the new sheet; no puntillos (plan section 3.1): a dotted figure keeps its own.
FIGURES = {
    FigureName.REDONDA: 1,
    FigureName.BLANCA: 2,
    FigureName.DOTTED_BLANCA: 2,
    FigureName.NEGRA: 4,
    FigureName.DOTTED_NEGRA: 4,
    FigureName.CORCHEA: 8,
    FigureName.SEMICORCHEA: 16,
    FigureName.FUSA: 32,
    FigureName.SEMIFUSA: 64,
}
STAFF = {"right": 1, "left": 2}


def _lines(rhythm: SavedRhythm) -> float | None:
    """The space between lines of an old sheet, in staff spaces of the new one; ``None`` when nobody changed it."""
    px = rhythm.line_spacing
    if px is None or abs(px - OLD_LINE_SPACING) < 0.5:
        return None
    # The old default is the new default: a space chosen on the old sheet keeps its ratio to it.
    space = round(LINE_SPACE * px / OLD_LINE_SPACING * 2) / 2
    return min(reading.LINE_SPACE[1], max(reading.LINE_SPACE[0], space))


def has_marks(rhythm: SavedRhythm | None) -> bool:
    """Whether an old sheet holds anything :func:`carry` lays on the new one."""
    if rhythm is None:
        return False
    return bool(
        any(getattr(rhythm, name) for name in TITLE_FIELDS)
        or rhythm.lyrics
        or _lines(rhythm) is not None
        or rhythm.overrides
        or rhythm.fingers
        or rhythm.beam_breaks
        or rhythm.beam_joins
    )


def dropped(rhythm: SavedRhythm) -> Counter:
    """The old marks the new sheet does not carry, by kind (for the migration's report)."""
    out: Counter = Counter()
    for name, kind in (
        ("clef_changes", "clefs"),
        ("ottavas", "octave lines"),
        ("spacings", "spacing"),
        ("even_spacings", "even spacing"),
        ("staff_gaps", "staff gaps"),
        ("speed_changes", "speed changes"),
        ("cue_ranges", "print smaller"),
        ("grace_notes", "decorations"),
        ("trills", "trills"),
    ):
        out[kind] += len(getattr(rhythm, name) or [])
    if rhythm.note_spacing:
        out["note spacing"] += 1
    if rhythm.drop_decorative:
        out["hide decorative notes"] += 1
    return +out


@dataclass
class Cells:
    """Where the new sheet draws the note of an old mark: the onset cell of each live note (the old sheet's column)
    and the drawn column of its chord."""

    #: (onset cell, key) -> drawn frame
    by_key: dict[tuple[int, int], int]
    #: (staff, onset cell) -> drawn frame
    by_staff: dict[tuple[int, int], int]
    #: onset cell -> drawn frame (any note)
    by_cell: dict[int, int]

    @classmethod
    def of(cls, notes: Notes) -> "Cells":
        live = notes.live()
        cell, _ = columns_of(live, FRAME_MS)
        _, start = drawn_columns(live.on_ms)
        frame = np.floor(np.round(start / FRAME_MS, 9) + 0.5).astype(np.int64)
        by_key, by_staff, by_cell = {}, {}, {}
        for c, k, h, f in zip(cell, live.key, live.hand, frame):
            c, f = int(c), int(f)
            by_key[(c, int(k))] = f
            staff = STAFF_OF.get(int(h))
            if staff is not None:
                by_staff.setdefault((staff, c), f)
            by_cell[c] = min(f, by_cell.get(c, f))
        return cls(by_key, by_staff, by_cell)

    def frame(self, column: int) -> int:
        """The drawn frame of an old column that held a note, or the column itself."""
        return self.by_cell.get(column, column)


def _chord(sheet: Sheet, staff: int, frame: int | None) -> list:
    if frame is None:
        return []
    return [n for n in sheet.notes if n.staff == staff and n.frame == frame and not n.covered]


def carry(
    sheet: Sheet,
    rhythm: SavedRhythm,
    notes: Notes,
    *,
    ai: bool,
    beams: bool = True,
) -> Counter:
    """Lay the marks of an old sheet on ``sheet`` (changed in place); ``ai``: the AI wrote ``sheet`` (no beam marks
    then), ``beams=False`` leaves them out too. Returns what was carried, by kind, and what found no note
    (``"<kind> lost"``)."""
    out: Counter = Counter()
    scale = rhythm.frame_ms / FRAME_MS
    cells = Cells.of(notes)

    def column(value: int) -> int:
        return int(round(value * scale))

    if not sheet.titles:
        titles = {name: getattr(rhythm, name) for name in TITLE_FIELDS if getattr(rhythm, name)}
        if titles:
            reading.set_titles(sheet, titles)
            out["titles"] += len(sheet.titles)
    if not sheet.lyrics and rhythm.lyrics:
        pieces = []
        for one in sorted(rhythm.lyrics, key=lambda one: one.from_column):
            start, end = cells.frame(column(one.from_column)), column(one.to_column)
            if pieces and start < pieces[-1]["end"]:
                out["lyrics lost"] += 1  # over the frames of the piece before it
                continue
            pieces.append(
                {
                    "start": start,
                    "end": max(end, start + 1),
                    "text": one.text,
                    "size": None if one.font_size is None else one.font_size / PX_PER_SPACE,
                    "lift": round(-(one.offset_y or 0.0) / PX_PER_SPACE * 2) / 2,
                    "width": None if one.width is None else one.width / PX_PER_SPACE,
                }
            )
        try:
            reading.set_lyrics(sheet, pieces, None)
            out["lyrics"] += len(pieces)
        except reading.Refused:
            out["lyrics lost"] += len(pieces)
    space = _lines(rhythm)
    if sheet.line_space is None and space is not None:
        reading.set_line_space(sheet, space)
        out["space between lines"] += 1

    for one in rhythm.overrides:
        staff = STAFF[one.hand]
        chord = _chord(sheet, staff, cells.by_staff.get((staff, column(one.start_frame))))
        if not chord:
            out[
                "figures lost"
            ] += 1  # the hand plays nothing there now (a note moved to the other hand)
            continue
        for n in chord:
            n.figure, n.fixed, n.grace_rule = FIGURES[FigureName(one.figure)], True, None
        out["figures"] += 1
    for one in rhythm.fingers:
        place = cells.by_key.get((column(one.start_frame), one.row))
        midi = one.row + LOWEST_MIDI
        found = [n for n in _chord(sheet, STAFF[one.hand], place) if n.midi == midi]
        if not found:
            found = [n for n in _chord(sheet, 3 - STAFF[one.hand], place) if n.midi == midi]
        if not found:
            out["fingers lost"] += 1
            continue
        found[0].finger = one.finger
        out["fingers"] += 1

    if ai or not beams:
        return out
    for kind, marks in (("beam breaks", rhythm.beam_breaks), ("beam joins", rhythm.beam_joins)):
        for one in marks:
            staff = STAFF[one.hand]
            frame = cells.by_staff.get((staff, column(one.start_frame)))
            chord = _chord(sheet, staff, frame)
            if not chord:
                out[f"{kind} lost"] += 1
                continue
            before = [
                n
                for n in sheet.notes
                if n.staff == staff
                and n.frame is not None
                and n.frame < frame
                and not n.covered
                and not n.grace
            ]
            prior = max(before, key=lambda n: n.frame).beam if before else None
            beam = chord[0].beam
            # A break starts a new group inside one; a join puts a chord with the group of the chord before it. A
            # mark the new sheet's own groups already follow is kept as it is.
            joined = beam is not None and beam == prior
            if joined == (kind == "beam joins"):
                out[f"{kind} held"] += 1
                continue
            if kind == "beam joins" and prior is None:
                out[f"{kind} lost"] += 1  # the chord before it has no beam on the new sheet
                continue
            try:
                reading.break_beam(sheet, [f"{frame}:{chord[0].midi}"])
            except reading.Refused:
                out[f"{kind} lost"] += 1
                continue
            out[kind] += 1
    return out
