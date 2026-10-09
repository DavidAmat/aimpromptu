"""The marks of ``sheet.json`` moved, cut out and copied by column (implementation 02, Phase 8).

Every mark a reader puts on the piano sheet is keyed by a column (a frame of the sheet), either one
column (a fingering, a key change, a beam break) or a half-open range of them (an octave bracket, a
lyrics piece, a cue-size stretch). An edit that changes the length of a part has to move them in
the same write as the notes, or they stop pointing at the music they were put on (rule 2 as
changed by implementation 02, plan section 4). This module is the one list of those marks, so a
new kind of mark is added here once and every length change moves it:

* :func:`shift`: everything at or after a column moves later (a passage put in).
* :func:`cut_out`: a stretch is taken out and everything after it moves earlier (a passage pasted
  in place of a marked stretch).
* :func:`extract`: the marks of a stretch, counted from its first column (a copied passage).
* :func:`put_in`: those marks added at a column of another sheet.

The key changes, the clef changes and the speed changes are transitions, not ranges: what is in
force at a column is the last one before it. Moving them is the same as moving any other mark, but
copying them needs what is in force at the edges too; :mod:`aitu_backend.editing.paste` adds those.
"""

from __future__ import annotations

from typing import Any, Literal

from aitu_backend.schemas.rhythm import SavedRhythm

__all__ = ["POINTS", "RANGES", "count", "cut_out", "extract", "put_in", "shift"]

#: The marks on one column: ``(field, the column's attribute)``.
POINTS: tuple[tuple[str, str], ...] = (
    ("key_changes", "from_column"),
    ("clef_changes", "from_column"),
    ("speed_changes", "start_frame"),
    ("overrides", "start_frame"),
    ("beam_breaks", "start_frame"),
    ("beam_joins", "start_frame"),
    ("hidden_notes", "start_frame"),
    ("fingers", "start_frame"),
    ("grace_notes", "start_frame"),
    ("staff_gaps", "from_column"),
)
#: The marks over a half-open range of columns: ``(field, first column, end column)``.
RANGES: tuple[tuple[str, str, str], ...] = (
    ("trills", "start_frame", "end_frame"),
    ("lyrics", "from_column", "to_column"),
    ("cue_ranges", "from_column", "to_column"),
    ("ottavas", "from_column", "to_column"),
    ("spacings", "from_column", "to_column"),
    ("even_spacings", "from_column", "to_column"),
)
#: Ranges a passage put in the middle of them is not part of: they end where it starts. Splitting
#: them would print the words, or the trill's held note, twice.
_CUT_NOT_SPLIT = ("lyrics", "trills")

Straddle = Literal["widen", "tear"]


def _items(rhythm: SavedRhythm, field: str) -> list[Any] | None:
    return getattr(rhythm, field)


def count(rhythm: SavedRhythm | None) -> int:
    """How many marks a sheet carries (its title, key and other settings aside)."""
    if rhythm is None:
        return 0
    fields = [field for field, _ in POINTS] + [field for field, _, _ in RANGES]
    return sum(len(_items(rhythm, field) or []) for field in fields)


def shift(
    rhythm: SavedRhythm, at: int, by: int, *, straddle: Straddle = "widen"
) -> tuple[SavedRhythm, int]:
    """Every mark at or after column ``at`` moves ``by`` columns later. Returns the sheet and how
    many marks moved.

    A range across ``at`` **widens** (its end moves, so it still covers the notes it covered: a
    passage recorded into the piece belongs to it) or **tears** (it ends at ``at`` and, except a
    lyrics piece or a trill, goes on after the passage: a passage pasted from elsewhere is not part
    of it).
    """
    if by <= 0:
        return rhythm, 0
    moved = 0
    update: dict[str, Any] = {}
    for field, attr in POINTS:
        out = []
        for item in _items(rhythm, field) or []:
            if getattr(item, attr) >= at:
                item = item.model_copy(update={attr: getattr(item, attr) + by})
                moved += 1
            out.append(item)
        update[field] = out
    for field, first, end in RANGES:
        items = _items(rhythm, field)
        if items is None:
            continue
        out = []
        for item in items:
            start, stop = getattr(item, first), getattr(item, end)
            if start >= at:
                out.append(item.model_copy(update={first: start + by, end: stop + by}))
                moved += 1
            elif stop > at and straddle == "widen":
                out.append(item.model_copy(update={end: stop + by}))
                moved += 1
            elif stop > at:
                out.append(item.model_copy(update={end: at}))
                if field not in _CUT_NOT_SPLIT:
                    out.append(item.model_copy(update={first: at + by, end: stop + by}))
                moved += 1
            else:
                out.append(item)
        update[field] = out
    return rhythm.model_copy(update=update), moved


def cut_out(rhythm: SavedRhythm, start: int, stop: int) -> SavedRhythm:
    """Columns ``[start, stop)`` taken out: the marks on them go, a range that reaches into them
    is shortened, and everything after them moves ``stop - start`` columns earlier."""
    length = stop - start
    if length <= 0:
        return rhythm
    update: dict[str, Any] = {}
    for field, attr in POINTS:
        out = []
        for item in _items(rhythm, field) or []:
            column = getattr(item, attr)
            if column < start:
                out.append(item)
            elif column >= stop:
                out.append(item.model_copy(update={attr: column - length}))
        update[field] = out
    for field, first, end in RANGES:
        items = _items(rhythm, field)
        if items is None:
            continue
        out = []
        for item in items:
            a, b = getattr(item, first), getattr(item, end)
            new_a = a if a < start else (start if a < stop else a - length)
            new_b = b if b <= start else (start if b <= stop else b - length)
            if new_b > new_a:
                out.append(item.model_copy(update={first: new_a, end: new_b}))
        update[field] = out
    return rhythm.model_copy(update=update)


def extract(rhythm: SavedRhythm, start: int, stop: int) -> dict[str, list[Any]]:
    """The marks of columns ``[start, stop)``, counted from ``start``: a range that reaches out of
    the stretch is clipped to it. Keyed by field; the octave brackets are absent when the sheet
    never decided about them."""
    out: dict[str, list[Any]] = {}
    for field, attr in POINTS:
        out[field] = [
            item.model_copy(update={attr: getattr(item, attr) - start})
            for item in _items(rhythm, field) or []
            if start <= getattr(item, attr) < stop
        ]
    for field, first, end in RANGES:
        items = _items(rhythm, field)
        if items is None:
            continue
        clipped = []
        for item in items:
            a, b = max(getattr(item, first), start), min(getattr(item, end), stop)
            if b > a:
                clipped.append(item.model_copy(update={first: a - start, end: b - start}))
        out[field] = clipped
    return out


def put_in(rhythm: SavedRhythm, marks: dict[str, list[Any]], at: int) -> SavedRhythm:
    """``marks`` (from :func:`extract`) added to ``rhythm`` at column ``at``. The columns they
    land on must be free: the caller has moved the sheet's own marks out of the way first."""
    update: dict[str, Any] = {}
    for field, attr in POINTS:
        arriving = [
            item.model_copy(update={attr: getattr(item, attr) + at})
            for item in marks.get(field, [])
        ]
        if arriving:
            update[field] = sorted(
                [*(_items(rhythm, field) or []), *arriving], key=lambda item: getattr(item, attr)
            )
    for field, first, end in RANGES:
        if field not in marks or not marks[field]:
            continue
        arriving = [
            item.model_copy(update={first: getattr(item, first) + at, end: getattr(item, end) + at})
            for item in marks[field]
        ]
        update[field] = sorted(
            [*(_items(rhythm, field) or []), *arriving], key=lambda item: getattr(item, first)
        )
    return rhythm.model_copy(update=update)
