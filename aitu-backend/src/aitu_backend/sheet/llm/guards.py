"""The phase 14 guards of the LLM step: two rules added to the checker in the product chain.

* :func:`beam_floor`: a model can drift into answers without beam tags (two Sonnet subagents did, 0 % of the short
  notes beamed in 17 windows), and the next window copies the beamless context.
* :func:`beam_overlaps`: a beam group whose figures do not fit its positions; the engine then makes two voices of one
  hand (20 of the 125 Sonnet windows of phase 14).

The research chain (``experiments/E07-pop-songs/pop.py``) imports them from here.
"""

from __future__ import annotations

from collections import defaultdict

from aitu_backend.sheet.sheet.common import figure_quarters
from aitu_backend.sheet.sheet.data import Sheet

__all__ = ["BEAM_FLOOR", "BEAM_MIN_NOTES", "beam_floor", "beam_overlaps", "guard_errors"]

# Phase 14: two Sonnet subagents stopped writing beam tags (0 % of the short notes beamed in 17 windows, and the next
# window copied the beamless context); accepted windows are at 43-100 %, Opus whole songs at 75-100 %.
BEAM_FLOOR = 0.3
BEAM_MIN_NOTES = 20


def beam_floor(sheet: Sheet, floor: float = BEAM_FLOOR) -> list[str]:
    """Phase 14: an answer with 20 or more eighths and shorter notes of which fewer than 30 % carry a beam tag."""
    short = [n for n in sheet.notes if n.figure >= 8 and not n.grace]
    if not floor or len(short) < BEAM_MIN_NOTES:
        return []
    beamed = sum(n.beam is not None for n in short)
    if beamed >= floor * len(short):
        return []
    return [
        f"only {beamed} of {len(short)} eighths and shorter notes have a beam tag (b...): write the beam groups "
        "as the rules ask (one tag per group, in each hand)"
    ]


def beam_overlaps(sheet: Sheet) -> list[str]:
    """Phase 14: a note of a beam group that lasts past the next note of its group (figure and position do not fit,
    e.g. two sixteenths at 2+2/3 and 2+3/4 in 6/8, or triplet positions with plain eighths). The engine then makes
    two voices out of one hand."""
    groups: dict[tuple, list] = defaultdict(list)
    for n in sheet.notes:
        if n.beam is not None and not n.grace and n.time is not None:
            groups[(n.staff, n.beam)].append(n)
    out = []
    for (staff, beam), ns in sorted(groups.items()):
        times = sorted({n.time for n in ns})
        for n in sorted(ns, key=lambda n: n.time):
            q = figure_quarters(n.figure, n.dots)
            if n.tuplet:
                a, b = (int(x) for x in n.tuplet.split("/"))
                q = q * b / a
            nxt = next((t for t in times if t > n.time), None)
            if nxt is not None and n.time + q > nxt:
                bar = next((b for b in sheet.bars if b.start <= n.time < b.start + b.dur), None)
                out.append(
                    f"bar {bar.label if bar else '?'}, {'R' if staff == 1 else 'L'} beam b{beam}: the note at "
                    f"f{n.frame} lasts longer than the distance to the next note of its group: make the figures "
                    "and the positions agree (in 6/8 an eighth is 1/3 of a beat; triplets need the (t3 mark)"
                )
                break
    return out


def guard_errors(sheet: Sheet, *, floor: float = BEAM_FLOOR, overlaps: bool = True) -> list[str]:
    """Both guards (``floor=0`` or ``overlaps=False`` turns one off)."""
    return beam_floor(sheet, floor) + (beam_overlaps(sheet) if overlaps else [])
