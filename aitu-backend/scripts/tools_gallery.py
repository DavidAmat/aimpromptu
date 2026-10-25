"""The Phase 7 gallery: each tool of the two toolboxes of the new sheet, on a real passage, before and after.

Implementation 03, Phase 7. Each case reads the sheet of a part as the page shows it (``part_sheet.build.current``),
makes one edit in memory with the functions the routes call (``part_sheet.reading``), lays it again on the notes
(``build.reapply``: the rules run, as after a real edit) and draws the passage before and after with the engine of
the new sheet. Nothing is written: the database is only read. Each case has one sentence that says what to look at.

    python scripts/tools_gallery.py --out ../context/implementations/03-apply-poc-research/gallery/phase-7

On the host, load ``.env`` first, or the script opens an empty ``.database/``. The page is ``DIR/index.html``.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from aitu_backend.part_sheet import build, reading
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline

SEVEN_YEARS = "1a16a836-62b9-483b-af46-d89d0ab1b2d8"


def ref(n: Note) -> str:
    return f"{n.frame}:{n.midi}"


def hand(sheet: Sheet, staff: int, a: int, b: int) -> list[Note]:
    return sorted(
        (n for n in sheet.notes if n.staff == staff and a <= n.frame < b and not n.covered),
        key=lambda n: (n.frame, n.midi),
    )


def at(sheet: Sheet, staff: int, frame: int) -> list[str]:
    return [ref(n) for n in hand(sheet, staff, frame, frame + 1)]


#: (section, part, first column, end column, title, what to look at, the edit)
Case = tuple[str, str, int, int, str, str, Callable[[Sheet], str]]

CASES: list[Case] = [
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "A figure set by hand",
        "The second note of the first group (La 5) is set to a negra. It leaves its beam group, so Si-b 5 before it "
        "prints its own flag and Sol 5 Fa 5 stay one group. Nothing moves: the spacing follows the time, not the "
        "figures.",
        lambda s: reading.set_figure(s, at(s, 1, 583), 4),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "Fingers on single notes and on a chord",
        "Finger 4 over La 5 (one number above a note of the upper staff), and 1 and 4 on the chord Sol 4 Re 5 at "
        "about 0:25: a column of numbers left of the chord, one at the height of each note.",
        lambda s: reading.set_fingers(s, at(s, 1, 583), [4])
        + "; "
        + reading.set_fingers(s, at(s, 1, 627), [4, 1]),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "A beam group cut in two",
        "The group of four corcheas is cut in front of its third note: two groups of two.",
        lambda s: reading.break_beam(s, at(s, 1, 589)),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "Two notes beamed by hand",
        "Si-b 5 and La 5 are beamed by hand as one group of their own: the group of four becomes two groups of "
        "two (Sol 5 Fa 5 stay together). Pressed again on the same two notes, the beam goes away.",
        lambda s: reading.join_beam(s, at(s, 1, 577) + at(s, 1, 583)),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "The grace note switch: on",
        "La 5 is written as a grace note of Sol 5 (a small slashed note just before it), although the rule wrote it "
        "as a corchea.",
        lambda s: reading.set_grace(s, at(s, 1, 583), "on"),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "The grace note switch: off",
        "The small Fa 5 before Do 5 (a grace note by the rule) is written as a normal note: a semicorchea (its "
        "own length) with its own column, so the line takes a little more room.",
        lambda s: reading.set_grace(s, at(s, 1, 635), "off"),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "A trill over three onsets",
        "Si-b 5, La 5 and Sol 5 become one held note (a blanca: its length now runs to Fa 5) with tr over it. The "
        "two onsets inside the trill stay in the notes and still play; they are not drawn.",
        lambda s: reading.set_ornament(s, at(s, 1, 577) + at(s, 1, 583) + at(s, 1, 589), "trill"),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "A mordent and a turn",
        "Two onsets written as a mordent (Si-b 5 and La 5: the mordent over Si-b 5), then a turn over Fa 5 and the "
        "notes after it in the hand (Sol 5, Fa 5).",
        lambda s: reading.set_ornament(s, at(s, 1, 577) + at(s, 1, 583), "mordent")
        + "; "
        + reading.set_ornament(s, at(s, 1, 596) + at(s, 1, 602), "turn"),
    ),
    (
        "The note toolbox",
        SEVEN_YEARS,
        560,
        700,
        "A rolled chord and a fermata",
        "The chord Sol 4 Re 5 is rolled (the wavy line left of it); the negra Do 5 after the grace note gets a "
        "fermata.",
        lambda s: reading.set_ornament(s, at(s, 1, 627), "arpeggio")
        + "; "
        + reading.set_ornament(s, at(s, 1, 639), "fermata"),
    ),
    (
        "The range toolbox",
        SEVEN_YEARS,
        560,
        700,
        "8va over the right hand",
        "The four high corcheas and the negra after them are written an octave lower under one 8va line: the ledger "
        "lines of Si-b 5 and La 5 go away.",
        lambda s: reading.set_ottava(s, 577, 610, 1, 1),
    ),
    (
        "The range toolbox",
        SEVEN_YEARS,
        4480,
        4700,
        "8vb under the left hand, in the bass clef",
        "The low notes of the left hand (Mi 2 and lower) under an 8vb line, written an octave higher than they "
        "sound: their ledger lines below the staff go away. Phase 7 allows an 8vb in the bass clef (the clef rules "
        "forbid only 8va there).",
        lambda s: reading.set_ottava(s, 4547, 4603, 2, -1),
    ),
    (
        "The range toolbox",
        SEVEN_YEARS,
        960,
        1120,
        "The treble clef for the left hand over a stretch",
        "The left hand plays high here (La 3 and above). It reads the treble clef from the start of the stretch and "
        "goes back to the bass clef after it (a small clef at each change).",
        lambda s: reading.set_clef(s, 1002, 1078, 2, "treble"),
    ),
    (
        "The range toolbox",
        SEVEN_YEARS,
        560,
        760,
        "An armadura for a stretch",
        "One bemol for the stretch: a becuadro cancels Mi-b and the new armadura keeps Si-b only, on both staves. "
        "No note of the stretch is a Mi-b, so no note needs a sign (a Mi-b would print its bemol, the user's rule "
        "1). After the stretch the two bemoles of the piece come back.",
        lambda s: reading.set_key(s, 602, 700, -1),
    ),
]


def banded(r: engine.Rendered, a: int, b: int) -> str:
    """The SVG of a render with a light band behind the columns [a, b) on each of its systems."""
    bands = []
    for box in r.systems:
        xs = [c["x"] for c in r.columns if c["system"] == box["index"] and a <= c["frame"] < b]
        if xs:
            x0, x1 = min(xs) - 1.0, max(xs) + 2.2
            bands.append(
                f'<rect x="{x0:.2f}" y="{box["top"]:.2f}" width="{x1 - x0:.2f}" '
                f'height="{box["bottom"] - box["top"]:.2f}" fill="#fff4cc"/>'
            )
    white = '<rect width="100%" height="100%" fill="#fff"/>'
    return r.svg.replace(white, white + "".join(bands), 1)


def _figure(cap: str, body: str) -> str:
    return (
        f'<figure><figcaption>{html.escape(cap)}</figcaption><div class="svg">{body}</div></figure>'
    )


def build_page(out: Path) -> list[str]:
    opts = engine.Options(width=110)
    sections: dict[str, list[str]] = defaultdict(list)
    index: list[str] = []
    problems: list[str] = []
    cache: dict[str, tuple[str, object]] = {}
    for no, (section, part, a, b, title, look, change) in enumerate(CASES, start=1):
        if part not in cache:
            cache[part] = (build.current(part).text, pipeline.starting_hands(part))
        text, notes = cache[part]
        before = f1.read(text)
        sheet = f1.read(text)
        label = change(sheet)
        after = build.reapply(sheet, notes)
        known = set(frames.check(before))
        broken = [p for p in frames.check(after) if p not in known]
        if broken:
            problems.append(f"{no}. {title}: {broken[:2]}")
        drawings = [
            _figure("Before", banded(engine.render_frames(before, opts, segment=(a, b)), a, b)),
            _figure(
                f"After: {label}", banded(engine.render_frames(after, opts, segment=(a, b)), a, b)
            ),
        ]
        anchor = f"c{no}"
        index.append(f'<li><a href="#{anchor}">{no}. {html.escape(title)}</a></li>')
        sections[section].append(
            f'<section id="{anchor}"><h3>{no}. {html.escape(title)}</h3>'
            f'<p class="look">{html.escape(look)}</p>{"".join(drawings)}</section>'
        )
    project = json.loads((paths.part_dir(SEVEN_YEARS).parents[1] / "project.json").read_text())
    page = (
        PAGE.replace("{{SONG}}", html.escape(project.get("title", "7 Years")))
        .replace("{{INDEX}}", "".join(index))
        .replace(
            "{{SECTIONS}}",
            "".join(
                f"<h2>{html.escape(name)}</h2>{''.join(items)}" for name, items in sections.items()
            ),
        )
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    return problems


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>New sheet: Phase 7 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { margin: 40px 0 8px; font-size: 20px; border-bottom: 1px solid var(--line); }
h3 { font-size: 16px; margin: 28px 0 4px; } .look { margin: 0 0 4px; max-width: 980px; }
figure { margin: 8px 0 14px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; } ol { columns: 2; font-size: 14px; }
</style></head><body><main>
<h1>The new sheet: the note and range tools</h1>
<p>Implementation 03, Phase 7. Each case is one press of a tool of the Sheet step on the AI's sheet of {{SONG}}
(My library), before and after, drawn as the page draws it. In the app the same press is one step of undo. The
band marks the passage. Please judge the drawing of each result.</p>
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="the folder of index.html")
    args = parser.parse_args()
    problems = build_page(args.out)
    for problem in problems:
        print("rule broken:", problem)
    print(f"{len(CASES)} cases, {len(problems)} with a broken rule -> {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
