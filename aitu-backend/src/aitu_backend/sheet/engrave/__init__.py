"""The engine: F1 bars sheet -> SVG (+ cursor map and note ids, ``cursor.render_song``).

Modules: ``glyphs`` (SMuFL paths, the bundled Leipzig ``leipzig.json``), ``spacing`` (the measured spacing model,
``spacing_model.json``), ``layout`` (voices, rests, accidentals, stems, columns, lines, beams; ``set_style``), ``vrv``
(Verovio's drawing rules, the default style), ``svg`` (output), ``cursor`` (the render step of a song: SVG, cursor
map, system boxes, timings).
"""

from __future__ import annotations

from aitu_backend.sheet.engrave.layout import Engraving, Options, engrave, set_style
from aitu_backend.sheet.engrave.svg import to_svg
from aitu_backend.sheet.sheet.data import Sheet

__all__ = ["Options", "Engraving", "engrave", "render", "set_style", "to_svg"]


def render(sheet: Sheet, opts: Options | None = None, *, px_per_space: float = 10.0) -> str:
    return to_svg(engrave(sheet, opts), px_per_space=px_per_space)
