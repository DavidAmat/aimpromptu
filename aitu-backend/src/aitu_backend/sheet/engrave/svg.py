"""SVG output of an :class:`~aitu_backend.sheet.engrave.layout.Engraving`: glyph paths in ``<defs>``, one ``<use>``
per glyph, lines and beam polygons; user units are staff spaces."""

from __future__ import annotations

from xml.sax.saxutils import escape

from aitu_backend.sheet.engrave.glyphs import UNITS, box, path_d
from aitu_backend.sheet.engrave.layout import Engraving

__all__ = ["to_svg"]

#: The colour of the lyrics: a soft charcoal, as the old sheet printed them.
LYRIC_COLOR = "#3a3a3a"
#: The fonts of the lyrics pieces (``data.LYRIC_FONTS``), as the page loads them (`index.css`).
LYRIC_FAMILIES = {
    "lora": "Lora, Georgia, serif",
    "geist": "Geist, system-ui, sans-serif",
    "montserrat": "Montserrat, system-ui, sans-serif",
}


def _f(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


def to_svg(
    eng: Engraving,
    *,
    px_per_space: float = 10.0,
    color: str = "#000",
    colors: dict[str, str] | None = None,
    id_prefix: str = "",
    note_ids: bool = False,
) -> str:
    """``colors``: fill per class (the last word of a primitive's class), e.g. ``{"bad": "#c00"}``. ``id_prefix``:
    prefix of the glyph ids, so that several sheets can sit inline in one HTML page. ``note_ids``: every notehead
    (graces too) carries ``data-note="<frame>:<midi>"`` of its note (notes with a frame anchor), so that a player
    can light the notes it plays (a head that stands for merged unisons lists them all: ``[data-note~="31:82"]``).
    """
    used: set[str] = set()
    body: list[str] = []
    m = eng.margin
    for sysm in eng.systems:
        top = sysm.top
        off = {0: top, 1: top, 2: top + sysm.bass_top}
        body.append('<g class="system">')
        for p in sysm.prims:
            dy = off[p.staff]
            if p.kind == "g":
                name, x, y, s, rot = p.data
                used.add(name)
                k = s / UNITS
                tr = f"translate({_f(x + m)},{_f(y + dy)})"
                if rot:
                    tr += f" rotate({_f(rot)})"
                cls = f' class="{p.cls}"' if p.cls else ""
                fill = (colors or {}).get(p.cls.split()[-1]) if p.cls else None
                cls += f' fill="{fill}"' if fill else ""
                cls += f' data-note="{p.ref}"' if note_ids and p.ref else ""
                body.append(
                    f'<use xlink:href="#{id_prefix}{name}" transform="{tr} scale({k:.6f})"{cls}/>'
                )
            elif p.kind == "l":
                x1, y1, x2, y2, w, dash = p.data
                d = f' stroke-dasharray="{_f(dash[0])} {_f(dash[1])}"' if dash else ""
                body.append(
                    f'<line x1="{_f(x1 + m)}" y1="{_f(y1 + dy)}" x2="{_f(x2 + m)}" y2="{_f(y2 + dy)}" '
                    f'stroke-width="{_f(w)}"{d}/>'
                )
            elif p.kind == "p":
                pts = " ".join(f"{_f(x + m)},{_f(y + dy)}" for x, y in p.data)
                cls = f' class="{p.cls}"' if p.cls else ""
                body.append(f'<polygon points="{pts}"{cls}/>')
            elif p.kind == "e":
                x, y, r = p.data
                body.append(f'<circle cx="{_f(x + m)}" cy="{_f(y + dy)}" r="{_f(r)}"/>')
            elif p.kind == "z":
                segs, w = p.data
                d = " ".join(
                    seg[0]
                    + " "
                    + " ".join(
                        f"{_f(v + (m if i % 2 == 0 else dy))}" for i, v in enumerate(seg[1:])
                    )
                    for seg in segs
                )
                body.append(
                    f'<path d="{d}" stroke-width="{_f(w)}" stroke-linejoin="round" stroke-linecap="round"/>'
                )
            elif p.kind == "t":
                x, y, lines, size, index, first, end = p.data[:7]
                style = p.data[7] if len(p.data) > 7 else {}
                spans = "".join(
                    f'<tspan x="{_f(x + m)}" y="{_f(y + dy + k * 1.2 * size)}">{escape(line)}</tspan>'
                    for k, line in enumerate(lines)
                )
                family = LYRIC_FAMILIES.get(style.get("font", "lora"), LYRIC_FAMILIES["lora"])
                face = (' font-weight="700"' if style.get("bold") else "") + (
                    ' font-style="italic"' if style.get("italic", True) else ""
                )
                # The last line's baseline: a block dragged by hand is placed from it (``Lyric.dy``); ``data-width``
                # is the width its words were wrapped to.
                extra = f' data-base="{_f(y + dy + (len(lines) - 1) * 1.2 * size)}"'
                if style.get("width"):
                    extra += f' data-width="{_f(style["width"])}"'
                if style.get("part"):
                    extra += f' data-part="{style["part"]}"'
                body.append(
                    f'<text class="lyric" data-lyric="{index}" data-start="{first}" data-end="{end}"{extra} '
                    f'font-size="{_f(size)}" font-family="{family}"{face} '
                    f'fill="{LYRIC_COLOR}" stroke="none">{spans}</text>'
                )
            elif p.kind == "b":
                x, y0, y1 = p.data
                used.add("brace")
                b = box("brace")
                h = y1 - y0
                sy = h / (b.top - b.bottom) / UNITS
                sx = 1.0 / b.width / UNITS
                body.append(
                    f'<use xlink:href="#{id_prefix}brace" transform="translate({_f(x + m)},{_f(y1 + top)}) '
                    f'scale({sx:.6f},{sy:.6f})"/>'
                )
        body.append("</g>")
    defs = "".join(
        f'<path id="{id_prefix}{n}" transform="scale(1,-1)" d="{path_d(n)}"/>' for n in sorted(used)
    )
    w, h = eng.width, eng.height
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{_f(w * px_per_space)}" height="{_f(h * px_per_space)}" viewBox="0 0 {_f(w)} {_f(h)}">'
        f'<rect width="100%" height="100%" fill="#fff"/>'
        f'<defs>{defs}</defs><g fill="{color}" stroke="{color}" stroke-linecap="butt">'
        + "".join(
            b.replace("<use ", '<use stroke="none" ')
            .replace("<polygon ", '<polygon stroke="none" ')
            .replace("<circle ", '<circle stroke="none" ')
            for b in body
        )
        + "</g></svg>"
    )
