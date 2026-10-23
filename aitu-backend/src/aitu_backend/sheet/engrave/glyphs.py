"""Music font glyphs (SMuFL; Leipzig by default, Verovio's font) as SVG paths, read from the font data shipped with
Verovio (SIL OFL 1.1).

Every glyph is a path in font units (250 per staff space, y up from the baseline). Drawing a glyph is
one ``<use>`` of its path, so the SVG needs no font and renders the same in every viewer (resvg too).
Boxes are the font's own (``<font>.xml``), in staff spaces with y up, as vexflow-v2 uses them.

The drawing style (``layout.set_style``) sets the font and these options. Default style "verovio" (phase 10B): Leipzig
for every glyph, no exception. Style "op62" (user feedback, 2026-10-20; E09 README §9) uses Leland and two exceptions:

* ``GLYPH_FONT``: single glyphs from another font: the flats from Leipzig (Verovio's default font; the user prefers its
  pointed flat to Leland's rounded one).
* ``ENGRAVED``: the black and half noteheads are not taken from a font but drawn from the shapes measured on the
  Breitkopf & Härtel first edition of Chopin's Op. 62: a pointed oval (almond) 0.78 x 0.48 staff space (half-length
  x half-width), long axis tilted 43°, width profile (1 - |u|^1.35)^(1/2); the half note's hole a pointed slit
  0.48 x 0.22 tilted 64° (profile q 1.10). Origin as in SMuFL: left edge at x = 0, centre on the baseline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import json
import math

__all__ = [
    "G",
    "Box",
    "box",
    "path_d",
    "UNITS",
    "FONTS",
    "set_font",
    "font",
    "ENGRAVED",
    "GLYPH_FONT",
]

BUNDLE = Path(__file__).with_name(
    "leipzig.json"
)  # the Leipzig glyphs the engine uses (research: ``export_bundle``)


FONT_DATA: list = [
    None
]  # a function -> folder of SMuFL font data (Verovio's ``data``); set by the research package


def _data() -> Path:
    """Font data for fonts other than the bundled Leipzig (style "op62", research only: ``aitu_research.engrave``
    registers Verovio's data folder in ``FONT_DATA``)."""
    if FONT_DATA[0] is None:
        raise RuntimeError(
            "only the bundled Leipzig glyphs are in aitu_backend.sheet; other fonts need FONT_DATA"
        )
    return FONT_DATA[0]()


UNITS = 250.0  # font units per staff space
FONTS = (
    "Bravura",
    "Leipzig",
    "Leland",
)  # SMuFL fonts shipped with Verovio (Gootville, Petaluma: handwritten)
# Leland was the default from the phase 10 review (measured on 10 printed editions, its noteheads 1.30 x 1.10 staff
# spaces and heavier accidentals are the closest to print; E09 README §8) until phase 10B: the user then asked for
# Verovio's look, whose font is Leipzig (E10B README).
_FONT = ["Leipzig"]


GLYPH_FONT: dict[str, str] = (
    {}
)  # style "op62": {"accidentalFlat": "Leipzig", "accidentalDoubleFlat": "Leipzig"}
# measured on ia-chopin-op62-bh (E09 head_beam_measure.py, median of 3 126 black heads and 103 half notes)
# outline profiles from head_profile.py (q: 1.35 black, 1.10 hole; an ellipse is 2), sizes from head_calibrate.py
HEAD = {
    "a": 0.78,
    "b": 0.48,
    "tilt": 43.0,
    "q": 1.35,
    "hole_a": 0.48,
    "hole_b": 0.22,
    "hole_tilt": 64.0,
    "hole_q": 1.10,
}
ENGRAVED = {"on": False}  # style "op62": True


def set_font(name: str) -> None:
    """Switch the music font (every glyph path and box); the layout reads boxes when it runs."""
    if name not in FONTS:
        raise ValueError(f"unknown font {name}")
    _FONT[0] = name
    _boxes.cache_clear()
    path_d.cache_clear()


def set_engraved(on: bool) -> None:
    """Engraved (measured) noteheads on or off (off: the font's own)."""
    ENGRAVED["on"] = on
    path_d.cache_clear()


def _ellipse(
    a: float, b: float, tilt: float, cx: float, n: int = 72, reverse: bool = False, q: float = 2.0
) -> list[tuple[float, float]]:
    """Outline of a head: half-length ``a`` along an axis tilted ``tilt`` degrees, half-width ``b``; the width along the
    axis follows (1 - |u|^q)^(1/2) (q = 2: an ellipse; smaller q: the pointed ends of engraved heads).
    """
    t = math.radians(tilt)
    pts = []
    for k in range(n):
        ang = 2 * math.pi * k / n
        u = math.cos(ang)  # -1..1 along the axis (cosine spacing: dense at the ends)
        side = 1.0 if math.sin(ang) >= 0 else -1.0
        v = side * b * math.sqrt(max(0.0, 1 - abs(u) ** q))
        x, y = a * u, v
        pts.append((cx + x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t)))
    return pts[::-1] if reverse else pts


def _half_extent(a: float, b: float, tilt: float, q: float = 2.0) -> tuple[float, float]:
    pts = _ellipse(a, b, tilt, 0.0, n=360, q=q)
    return max(abs(x) for x, _ in pts), max(abs(y) for _, y in pts)


def _engraved_box(name: str) -> Box | None:
    if not ENGRAVED["on"] or name not in ("noteheadBlack", "noteheadHalf"):
        return None
    hw, hh = _half_extent(HEAD["a"], HEAD["b"], HEAD["tilt"], HEAD["q"])
    return Box(0.0, -hh, 2 * hw, hh)


def _engraved_path(name: str) -> str | None:
    if _engraved_box(name) is None:
        return None
    hw, _ = _half_extent(HEAD["a"], HEAD["b"], HEAD["tilt"], HEAD["q"])
    rings = [_ellipse(HEAD["a"], HEAD["b"], HEAD["tilt"], hw, n=144, q=HEAD["q"])]
    if name == "noteheadHalf":  # the hole winds the other way: non-zero fill leaves it empty
        rings.append(
            _ellipse(
                HEAD["hole_a"],
                HEAD["hole_b"],
                HEAD["hole_tilt"],
                hw,
                n=144,
                reverse=True,
                q=HEAD["hole_q"],
            )
        )
    return " ".join(
        "M " + " L ".join(f"{x * UNITS:.1f} {y * UNITS:.1f}" for x, y in ring) + " Z"
        for ring in rings
    )


def font() -> str:
    return _FONT[0]


G = {
    "brace": "E000",
    "gClef": "E050",
    "fClef": "E062",
    "gClefChange": "E07A",
    "fClefChange": "E07C",
    "noteheadWhole": "E0A2",
    "noteheadHalf": "E0A3",
    "noteheadBlack": "E0A4",
    "noteheadDoubleWhole": "E0A0",
    "augmentationDot": "E1E7",
    "flag8thUp": "E240",
    "flag8thDown": "E241",
    "flag16thUp": "E242",
    "flag16thDown": "E243",
    "flag32ndUp": "E244",
    "flag32ndDown": "E245",
    "flag64thUp": "E246",
    "flag64thDown": "E247",
    "accidentalFlat": "E260",
    "accidentalNatural": "E261",
    "accidentalSharp": "E262",
    "accidentalDoubleSharp": "E263",
    "accidentalDoubleFlat": "E264",
    "restDoubleWhole": "E4E2",
    "restWhole": "E4E3",
    "restHalf": "E4E4",
    "restQuarter": "E4E5",
    "rest8th": "E4E6",
    "rest16th": "E4E7",
    "rest32nd": "E4E8",
    "rest64th": "E4E9",
    "rest128th": "E4EA",
    "fermataAbove": "E4C0",
    "fermataBelow": "E4C1",
    "ornamentTrill": "E566",
    "ornamentTurn": "E567",
    "ornamentMordent": "E56D",
    "ottava": "E510",
    "ottavaAlta": "E511",
    "ottavaBassaVb": "E51C",
    "quindicesima": "E514",
    "quindicesimaBassaMb": "E51D",
    "tremolo1": "E220",
    "tremolo2": "E221",
    "tremolo3": "E222",
    "wiggleArpeggiatoUp": "EAA9",
    "timeSigCommon": "E08A",
    "timeSigCutCommon": "E08B",
}
for _d in range(10):
    G[f"timeSig{_d}"] = f"E08{_d}"
    G[f"tuplet{_d}"] = f"E88{_d}"


@dataclass(frozen=True)
class Box:
    """Glyph box in staff spaces, y up from the baseline (SMuFL convention)."""

    left: float
    bottom: float
    right: float
    top: float

    @property
    def width(self) -> float:
        return self.right - self.left


@lru_cache(maxsize=1)
def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8")) if BUNDLE.exists() else {}


@lru_cache(maxsize=4)
def _font_boxes(fnt: str) -> dict[str, Box]:
    if fnt == "Leipzig" and _bundle():
        return {code: Box(*g["box"]) for code, g in _bundle()["glyphs"].items()}
    text = (_data() / f"{fnt}.xml").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
        r'<g c="([0-9A-F]+)" x="([-\d.]+)" y="([-\d.]+)" w="([-\d.]+)" h="([-\d.]+)"', text
    ):
        c, x, y, w, h = m.group(1), *(float(v) / UNITS for v in m.groups()[1:])
        out[c] = Box(x, y, x + w, y + h)
    return out


@lru_cache(maxsize=1)
def _boxes() -> dict[str, Box]:
    return _font_boxes(_FONT[0])


def _font_of(name: str) -> str:
    return GLYPH_FONT.get(name, _FONT[0])


def box(name: str) -> Box:
    eng = _engraved_box(name)
    if eng is not None:
        return eng
    return _font_boxes(_font_of(name))[G.get(name, name)]


@lru_cache(maxsize=None)
def path_d(name: str) -> str:
    eng = _engraved_path(name)
    if eng is not None:
        return eng
    code = G.get(name, name)
    if _font_of(name) == "Leipzig" and code in _bundle().get("glyphs", {}):
        return _bundle()["glyphs"][code]["d"]
    text = (_data() / _font_of(name) / f"{code}.xml").read_text(encoding="utf-8")
    return " ".join(re.findall(r'\sd="([^"]+)"', text))
