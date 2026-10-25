"""The engine: F1 bars sheet -> SVG (+ cursor map and note ids, ``cursor.render_song``); F1 frames sheet (the new
sheet, no compases) -> SVG (``frames.render_frames``, implementation 03 Phase 3).

Modules: ``glyphs`` (SMuFL paths, the bundled Leipzig ``leipzig.json``), ``spacing`` (the measured spacing model,
``spacing_model.json``), ``layout`` (voices, rests, accidentals, stems, columns, lines, beams; ``set_style``), ``vrv``
(Verovio's drawing rules, the default style), ``svg`` (output), ``cursor`` (the render step of a song: SVG, cursor
map, system boxes, timings), ``frames`` (the layout of the new sheet without compases: columns, spacing, line
breaks; it draws with ``layout`` and ``vrv``).
"""

from __future__ import annotations

from aitu_backend.sheet.engrave.frames import engrave_frames, render_frames
from aitu_backend.sheet.engrave.layout import Engraving, Options, engrave, set_style
from aitu_backend.sheet.engrave.svg import to_svg
from aitu_backend.sheet.sheet.data import Sheet

__all__ = [
    "Options",
    "Engraving",
    "engrave",
    "engrave_frames",
    "render",
    "render_frames",
    "set_style",
    "to_svg",
]


def render(sheet: Sheet, opts: Options | None = None, *, px_per_space: float = 10.0) -> str:
    return to_svg(engrave(sheet, opts), px_per_space=px_per_space)
