"""The Phase 3 gallery: passages of My library drawn by vexflow-v2, by the bars engine and by the new engine.

Implementation 03, Phase 3, task 3.7. Each case is a passage of a library song (columns ``[a, b)``) with one
sentence that says what to look at. Three drawings per case, one above the other:

* **today's sheet (vexflow-v2)**: a screenshot of the app's Sheet step of that library version, taken by
  ``aitu-frontend/scripts/vexflow-passages.mjs`` from the ``cases.json`` this script writes (the page shows a
  placeholder until the screenshot exists);
* **the bars engine** (research phase 15): the bars algorithm (``proposal.propose``) on the same starting hands,
  the compases that hold the passage;
* **the new engine** (``engrave.frames``): the algorithm's new sheet (``propose_frames``) of the whole song drawn
  without compases at 130 staff spaces, and the lines that hold the passage shown (``render_frames(segment=...)``),
  the passage on a light band: the lines look as they will in the song.

    python scripts/frames_gallery.py --out DIR
    node ../aitu-frontend/scripts/vexflow-passages.mjs --cases DIR/cases.json --out DIR/vexflow

On the host, load ``.env`` first, or the script opens an empty ``.database/``. The page is ``DIR/index.html``.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.engrave.layout import Options as BarsOptions
from aitu_backend.sheet.engrave.layout import engrave
from aitu_backend.sheet.engrave.svg import to_svg
from aitu_backend.sheet.proposal import propose
from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet.data import Sheet
from aitu_backend.sheet.sheet.figures import NAMES
from aitu_backend.sheet.sheet.pmn import key_of_sheet_json
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription.pipeline import starting_hands

#: (section, part, first column, end column, title, what to look at, variant)
CASES = [
    (
        "Spacing",
        "4cb9cb38",
        1240,
        1420,
        "A busy right hand over a quiet left hand",
        "The right hand plays semicorcheas and the left hand one chord now and then. The stretch gets the room the "
        "right hand needs; each left-hand chord sits under the right-hand note it sounds with, and the left hand "
        "has blank space after it (no silencio, and the chord stays a negra).",
        None,
    ),
    (
        "Spacing",
        "1a16a836",
        177,
        420,
        "Both hands together: one vertical line per moment",
        "What sounds together is on one vertical line in both hands. Semicorcheas are closer together than "
        "corcheas, and corcheas closer than the half notes of the left hand, in proportion to their time (the "
        "measured spacing of printed editions).",
        None,
    ),
    (
        "Spacing",
        "3c8d4cfa",
        1960,
        2180,
        "A pause where neither hand plays is drawn short",
        "About 3 seconds pass with no new note in either hand (the redonda of the right hand still sounds). Up to "
        "a blanca the gap follows the measured spacing; the time beyond it keeps only 30 % of the width it would "
        "add, so the line does not fill with blank paper. The playback cursor will move faster over it.",
        None,
    ),
    (
        "Spacing",
        "2ed0f379",
        960,
        1100,
        "Beam groups in both hands, and a sign on every altered note",
        "Both hands play corcheas that start at different moments. Every onset of either hand gets its own "
        "vertical line, and the beams of each hand stay whole. There is no compás, so every note outside the "
        "armadura carries its sign each time (rule 1); after a Re becuadro, the next Re# of the same group prints "
        "its sostenido again (rule 7).",
        None,
    ),
    (
        "Elements",
        "c0edc9b0",
        480,
        640,
        "Grace notes",
        "A grace note is drawn small just before its note and takes no vertical line of its own: the main note "
        "stays on the line of the moment it sounds.",
        None,
    ),
    (
        "Elements",
        "f4c4de9a",
        30,
        220,
        "Clef changes and 8va",
        "The left hand changes clef inside the line (a small clef before the chord), and the right hand is under an "
        "8va line. These clefs come from the algorithm's starting hands; the LLM decides hands and clefs in Phase 4.",
        None,
    ),
    (
        "Elements",
        "56543911",
        3020,
        3120,
        "A grace note before a clef change keeps its clef",
        "The right-hand grace chord sounds before the change to the bass clef, so it is written in the treble clef, "
        "then comes the small bass clef, then the main note.",
        None,
    ),
    (
        "Elements",
        "56543911",
        480,
        680,
        "An armadura change inside a line",
        "Sol mayor changes to Do mayor: a becuadro cancels the Fa# on both staves, with room around it so that it "
        "does not read as a sign of the next chord. The second drawing adds a thin double line before the change "
        "(not a compás line): which one reads better?",
        "key_line",
    ),
]

WHOLE = ("1a16a836", "7 Years, the whole song")


# ------------------------------------------------------------------ passages


def bars_passage(sheet: Sheet, a: int, b: int) -> Sheet:
    """The compases of a bars sheet that hold the notes of columns [a, b)."""
    starts = [bar.start for bar in sheet.bars]

    def bar_of(t: Fraction) -> int:
        return max(0, sum(1 for s in starts if s <= t) - 1)

    held = [bar_of(n.time) for n in sheet.notes if n.frame is not None and a <= n.frame < b]
    lo, hi = min(held), max(held)
    t0 = sheet.bars[lo].start
    t1 = sheet.bars[hi].start + sheet.bars[hi].dur
    clefs = dict(sheet.clefs)
    for t, st, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if t <= t0:
            clefs[st] = c
    return Sheet(
        notes=[replace(n) for n in sheet.notes if t0 <= n.time < t1],
        bars=sheet.bars[lo : hi + 1],
        clefs=clefs,
        clef_changes=[c for c in sheet.clef_changes if t0 < c[0] < t1],
    )


def banded(r: engine.Rendered, a: int, b: int) -> str:
    """The SVG of a render with a light band behind the columns [a, b) on each of its systems."""
    bands = []
    for k, box in enumerate(r.systems):
        xs = [c["x"] for c in r.columns if c["system"] == box["index"] and a <= c["frame"] < b]
        if xs:
            x0, x1 = min(xs) - 1.0, max(xs) + 2.2
            bands.append(
                f'<rect x="{x0:.2f}" y="{box["top"]:.2f}" width="{x1 - x0:.2f}" '
                f'height="{box["bottom"] - box["top"]:.2f}" fill="#fff4cc"/>'
            )
    white = '<rect width="100%" height="100%" fill="#fff"/>'
    return r.svg.replace(white, white + "".join(bands), 1)


# ------------------------------------------------------------------ the page


def _time(ms: float) -> str:
    return f"{int(ms // 60000)}:{int(ms % 60000 // 1000):02d}"


def _figure(cap: str, body: str) -> str:
    return (
        f'<figure><figcaption>{html.escape(cap)}</figcaption><div class="svg">{body}</div></figure>'
    )


def build(out: Path) -> None:
    parts = bundle.list_parts(layers=["private"])
    cache: dict[str, tuple] = {}

    def song(short: str) -> tuple:
        pid = next(p for p in parts if p.startswith(short))
        if pid not in cache:
            notes = starting_hands(pid)
            sheet_path = paths.part_sheet_path(pid)
            sheet_json = json.loads(sheet_path.read_text()) if sheet_path.exists() else {}
            project = json.loads((paths.part_dir(pid).parents[1] / "project.json").read_text())
            bars = propose(notes, key=key_of_sheet_json(sheet_json), track=True).sheet
            cache[pid] = (pid, propose_frames(notes).sheet, bars, project.get("title", ""))
        return cache[pid]

    sections: dict[str, list[str]] = defaultdict(list)
    index, listed = [], []
    opts = engine.Options(width=130)
    for no, (section, short, a, b, title, look, variant) in enumerate(CASES, start=1):
        pid, sheet, bars, name = song(short)
        new = banded(engine.render_frames(sheet, opts, segment=(a, b)), a, b)
        old = to_svg(engrave(bars_passage(bars, a, b), BarsOptions(width=130)))
        drawings = [
            _figure(
                "Today's sheet (vexflow-v2, the app's Sheet step)",
                f'<img src="vexflow/case-{no}.png" alt="not captured yet">',
            ),
            _figure("The bars engine (research, with compases)", old),
            _figure(
                "The new engine (no compases): the lines of the song that hold the passage", new
            ),
        ]
        if variant == "key_line":
            lined = engine.Options(width=130, key_line=True)
            drawings.append(
                _figure(
                    "The new engine with a thin double line before the armadura change",
                    banded(engine.render_frames(sheet, lined, segment=(a, b)), a, b),
                )
            )
        listed.append({"case": no, "part": pid, "first": a, "end": b})
        anchor = f"c{no}"
        index.append(f'<li><a href="#{anchor}">{no}. {html.escape(title)}</a></li>')
        notes = [n for n in sheet.notes if a <= n.frame < b]
        when = _time(min(n.on_ms for n in notes))
        figs = ", ".join(f"{NAMES[k]} {round(sheet.quarter_ms * 4 / k)} ms" for k in (4, 8, 16))
        sections[section].append(
            f'<section id="{anchor}"><h3>{no}. {html.escape(title)}</h3>'
            f'<p class="look">{html.escape(look)}</p>'
            f'<p class="where">{html.escape(name)}, from {when} (columns f{a} to f{b - 1}). '
            f"Reference figure: {figs}.</p>{''.join(drawings)}</section>"
        )
    pid, sheet, _, name = song(WHOLE[0])
    whole = engine.render_frames(sheet, opts)
    sections["The whole song"].append(
        f'<section id="whole"><h3>{html.escape(WHOLE[1])}</h3>'
        '<p class="look">The new engine on a whole song: lines break where no beam group is cut, at the longest '
        "pause once a line is 80 % full, so that a segment that the LLM changes later moves the lines after it "
        f"as little as possible. {whole.lines} lines, drawn in about "
        f"{round(whole.timings['total_ms'])} ms.</p>"
        f'{_figure("The new engine", whole.svg)}</section>'
    )
    index.append('<li><a href="#whole">The whole song</a></li>')
    page = PAGE.replace("{{INDEX}}", "".join(index)).replace(
        "{{SECTIONS}}",
        "".join(
            f"<h2>{html.escape(name)}</h2>{''.join(items)}" for name, items in sections.items()
        ),
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "cases.json").write_text(json.dumps(listed, indent=1), encoding="utf-8")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>New sheet: Phase 3 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; --tint: #f6f6f8; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { margin: 40px 0 8px; font-size: 20px; border-bottom: 1px solid var(--line); }
h3 { font-size: 16px; margin: 28px 0 4px; } .look { margin: 0 0 4px; max-width: 980px; }
.where { color: var(--soft); margin: 0 0 8px; font-size: 13px; }
figure { margin: 8px 0 14px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; } .svg img { display: block; max-width: none; zoom: 0.5; }
ol { columns: 2; font-size: 14px; }
</style></head><body><main>
<h1>The new sheet: the engine without compases</h1>
<p>Implementation 03, Phase 3. The same passages of My library drawn three ways: today's sheet in the app
(vexflow-v2), the research engine with compases, and the new engine, which has no compases, no tempo, no silencios and
no puntillos. In the new engine both hands share one vertical line per moment, the room of a stretch comes from the
notes that need it in either hand, and empty time is drawn short. The notes themselves (hands, figures, beam groups,
clefs) come from the algorithm of Phase 2, so they can differ from today's sheet; please judge the look and the
spacing here. The LLM writes the notes in Phase 4.</p>
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="the folder of index.html")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
