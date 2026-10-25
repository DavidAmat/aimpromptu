"""The render step of the song viewer (phase 14): F1 bars text -> SVG, cursor map and timings.

The **cursor map** ties the drawn sheet to the audio: one row per note column of the engraving with its system, x
(SVG user units, staff spaces, margin included) and the audio time in ms (the frame anchors of its notes, 40 ms per
frame; a rest-only column, or a column of notes without anchors, gets a time interpolated from its neighbours), and
one box per system (top and bottom y, left and right x of the staff lines). A player moves a line between two
columns by the audio time. Each notehead of the SVG names its note (``data-note="<frame>:<midi>"``): the notes of a
column are the ones whose frame is the column's ``ms / 40``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from fractions import Fraction

from aitu_backend.sheet.engrave.layout import Engraving, Options, engrave
from aitu_backend.sheet.engrave.svg import to_svg
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS, Sheet

__all__ = ["Rendered", "render_song", "cursor_map"]


@dataclass
class Rendered:
    svg: str
    columns: list[dict]  # system, bar (label), x, ms
    systems: list[dict]  # top, bottom, left, right (SVG user units)
    width: float  # SVG user units (staff spaces)
    height: float
    bars: int
    timings: dict  # parse_ms, layout_ms, svg_ms, total_ms


def _time_frames(sheet: Sheet) -> dict[Fraction, float]:
    """Sheet time -> the first anchored frame of the notes that start there (graces left out)."""
    out: dict[Fraction, float] = {}
    for n in sheet.notes:
        if n.grace or n.frame is None or n.time is None:
            continue
        out[n.time] = min(out.get(n.time, n.frame), n.frame)
    return out


def cursor_map(eng: Engraving, sheet: Sheet) -> tuple[list[dict], list[dict]]:
    frames = _time_frames(sheet)
    m = eng.margin
    cols = [
        {
            "system": c["system"],
            "bar": c["label"],
            "x": round(c["x"] + m, 3),
            "t": c["time"],
            "ms": frames[c["time"]] * FRAME_MS if c["time"] in frames else None,
        }
        for c in eng.columns
    ]
    known = [i for i, c in enumerate(cols) if c["ms"] is not None]
    for i, c in enumerate(cols):  # interpolate by sheet time between the known neighbours
        if c["ms"] is not None:
            continue
        lo = max((k for k in known if k < i), default=None)
        hi = min((k for k in known if k > i), default=None)
        if lo is not None and hi is not None and cols[hi]["t"] > cols[lo]["t"]:
            r = float((c["t"] - cols[lo]["t"]) / (cols[hi]["t"] - cols[lo]["t"]))
            c["ms"] = cols[lo]["ms"] + r * (cols[hi]["ms"] - cols[lo]["ms"])
        else:
            c["ms"] = (
                cols[lo]["ms"] if lo is not None else (cols[hi]["ms"] if hi is not None else 0.0)
            )
    for c in cols:
        del c["t"]
        c["ms"] = round(c["ms"], 1)
    systems = [
        {
            "top": round(s.top + s.ymin, 3),
            "bottom": round(s.top + s.ymax, 3),
            "staff_top": round(s.top, 3),
            "staff_bottom": round(s.top + s.bass_top + 4, 3),
            "left": round(m, 3),
            "right": round(m + s.width, 3),
        }
        for s in eng.systems
    ]
    return cols, systems


def render_song(
    text: str, opts: Options | None = None, *, px_per_space: float = 10.0, note_ids: bool = True
) -> Rendered:
    """F1 bars text -> :class:`Rendered`, with the time of each part of the step. ``note_ids``: each notehead carries
    ``data-note="<frame>:<midi>"`` (phase 15), so a player can light the notes of the column it plays.
    """
    t0 = time.perf_counter()
    sheet = f1.read(text)
    t1 = time.perf_counter()
    eng = engrave(sheet, opts or Options(width=130))
    t2 = time.perf_counter()
    svg = to_svg(eng, px_per_space=px_per_space, note_ids=note_ids)
    t3 = time.perf_counter()
    cols, systems = cursor_map(eng, sheet)
    t4 = time.perf_counter()
    ms = {
        "parse_ms": (t1 - t0) * 1e3,
        "layout_ms": (t2 - t1) * 1e3,
        "svg_ms": (t3 - t2) * 1e3,
        "cursor_ms": (t4 - t3) * 1e3,
        "total_ms": (t4 - t0) * 1e3,
    }
    return Rendered(
        svg=svg,
        columns=cols,
        systems=systems,
        width=eng.width,
        height=eng.height,
        bars=len(sheet.bars),
        timings={k: round(v, 2) for k, v in ms.items()},
    )
