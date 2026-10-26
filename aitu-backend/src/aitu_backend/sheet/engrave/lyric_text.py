"""The words of a lyrics block: how wide they are, and where they wrap (implementation 03, Phase 8A++).

The engine draws the lyrics and has no text metrics of its own. ``lyric_fonts.json`` holds the advance width of each
character in each face of the lyrics fonts (Lora, Geist, Montserrat; normal, italic, bold, bold italic), measured in
the browser from the app's own font files (``aitu-frontend/scripts/measure-lyric-fonts.mjs``). With it the engine
wraps a block's words to its width once, and the page, the line heights and the PDF all print the same lines. A
character the table does not hold counts as an ``n``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

__all__ = ["text_width", "wrap"]

_TABLE = Path(__file__).with_name("lyric_fonts.json")


@lru_cache(maxsize=1)
def _table() -> tuple[str, dict[str, dict[str, list[int]]]]:
    data = json.loads(_TABLE.read_text(encoding="utf-8"))
    return data["chars"], data["fonts"]


@lru_cache(maxsize=24)
def _widths(font: str, bold: bool, italic: bool) -> tuple[dict[str, float], float]:
    chars, fonts = _table()
    face = ("bold" if bold else "") + ("italic" if italic else "") or "normal"
    widths = fonts.get(font, fonts["lora"])[face]
    table = {c: w / 1000.0 for c, w in zip(chars, widths)}
    return table, table["n"]


def text_width(
    text: str, size: float, font: str = "lora", bold: bool = False, italic: bool = True
) -> float:
    """The width of one line of words, in the units of ``size`` (staff spaces)."""
    table, other = _widths(font, bold, italic)
    return size * sum(table.get(c, other) for c in text)


def wrap(
    text: str,
    width: float | None,
    size: float,
    font: str = "lora",
    bold: bool = False,
    italic: bool = True,
) -> list[str]:
    """The lines of a block: one per ``\\n`` of its words, and with a ``width`` each of those wrapped at the spaces
    so that no line is wider (a word wider than the block keeps a line of its own)."""
    out: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if width is None or width <= 0 or len(words) < 2:
            out.append(" ".join(words) if width else paragraph)
            continue
        line = words[0]
        for word in words[1:]:
            longer = f"{line} {word}"
            if text_width(longer, size, font, bold, italic) <= width:
                line = longer
            else:
                out.append(line)
                line = word
        out.append(line)
    return out
