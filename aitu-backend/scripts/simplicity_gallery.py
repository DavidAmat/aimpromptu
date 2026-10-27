"""The rules of simplicity of implementation 04, Phase 3: the study of My library, and the gallery of 7 Years.

The plan (section 4.3 of ``context/implementations/04-app-enhancements/04-plan.md``) asks the AI, from prompt version
6, for uniform patterns (a single note in a run of octavas, or an octava in a run of single notes, made to fit) and
for the amateur pianist (a quick chord before a main note keeps only the notes near it: no quick jump of one hand).
This script finds both in the sheets as the page draws them, by two plain rules that only count:

* **a broken pattern**: in one hand, a run of six or more columns of corcheas or shorter, each sounding less than a
  negra after the one before, whose columns have one shape (a single note, an octava, another chord) at 60 % or
  more, and some columns of another shape (:func:`broken`);
* **a far quick chord**: a column of one hand, a semicorchea or shorter, two figures or more shorter than the next
  column of that hand and sounding less than a corchea before it, with a note more than an octave from every note of
  that next column (:func:`far_quick`). A quick chord that also has a note near the main note can lose the far one;
  a single far quick note cannot (its column would be empty).

* ``--study``: for every part of My library (``private``; ``--layers`` for others), both counts, the notes a fix
  would change at most (one per odd column, one per far note) and the largest share of one window's notes.
* ``--case PART FIRST END``: the columns of one passage, both hands, one line each.
* ``--out DIR --after PART``: the gallery, ``DIR/index.html``: the passages of the images and the other places
  that changed, the sheet of 7 Years (``--before``, the My library version, prompt 5) above the sheet of ``PART``
  (a temporary copy enhanced with prompt 6), as the page draws them, each with what changed, read from the data.

Nothing is written to the database. In the backend container::

    docker exec -i aimpromptu-backend-1 python scripts/simplicity_gallery.py --study
"""

from __future__ import annotations

import argparse
import html
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator

from aitu_backend.part_sheet import build, store
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.llm import frames as llm_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.storage import bundle, locate

SEVEN_YEARS = "1a16a836-62b9-483b-af46-d89d0ab1b2d8"

STEP_NAMES = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}

RUN_COLUMNS = 6  # a run of fewer columns is no pattern
RUN_SHARE = 0.6  # the shape of the pattern holds at least this share of the run's columns
FAR = 12  # semitones: more than an octave from every note of the main column


def name(n: Note) -> str:
    sign = "#" if n.alter > 0 else "-b" if n.alter < 0 else ""
    return f"{STEP_NAMES[n.step]}{sign} {n.octave}"


def clock(frame: int) -> str:
    seconds = frame * 0.04
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def columns(sheet: Sheet, staff: int) -> list[tuple[int, list[Note]]]:
    cols: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        if n.staff == staff and not n.covered:
            cols[n.frame].append(n)
    return [(f, sorted(ns, key=lambda n: n.midi)) for f, ns in sorted(cols.items())]


def shape(ns: list[Note]) -> str:
    keys = sorted({n.midi for n in ns})
    if len(keys) == 1:
        return "single"
    if len(keys) == 2 and keys[1] - keys[0] == 12:
        return "octava"
    return "chord"


def _start(ns: list[Note]) -> float:
    return min(n.on_ms if n.on_ms is not None else n.frame * 40.0 for n in ns)


def broken(sheet: Sheet) -> list[dict]:
    """The runs of one hand with a pattern and columns that break it (see the module)."""
    quarter = sheet.quarter_ms or 500.0
    out = []
    for staff in (1, 2):
        cols = [(f, ns) for f, ns in columns(sheet, staff) if not ns[0].grace]
        runs: list[list[tuple[int, list[Note]]]] = []
        for f, ns in cols:
            fast = (ns[0].figure or 0) >= 8
            if runs and fast and runs[-1] and _start(ns) - _start(runs[-1][-1][1]) < quarter:
                runs[-1].append((f, ns))
            else:
                runs.append([(f, ns)] if fast else [])
        for run in runs:
            if len(run) < RUN_COLUMNS:
                continue
            shapes = Counter(shape(ns) for _, ns in run)
            main, count = shapes.most_common(1)[0]
            odd = [(f, ns) for f, ns in run if shape(ns) != main]
            if odd and count >= RUN_SHARE * len(run):
                out.append(
                    {
                        "staff": staff,
                        "first": run[0][0],
                        "last": run[-1][0],
                        "columns": len(run),
                        "pattern": main,
                        "odd": [(f, shape(ns), "+".join(name(n) for n in ns)) for f, ns in odd],
                    }
                )
    return out


def far_quick(sheet: Sheet) -> list[dict]:
    """The quick columns of one hand with a note far from the main column after them (see the module)."""
    quarter = sheet.quarter_ms or 500.0
    out = []
    for staff in (1, 2):
        cols = columns(sheet, staff)
        for (f, quick), (g, main) in zip(cols, cols[1:]):
            fq, fm = quick[0].figure or 0, main[0].figure or 0
            if quick[0].grace and not main[0].grace:
                pass  # a decoration note is quick by the rule
            elif fq < 16 or not fm or fq < 4 * fm or _start(main) - _start(quick) >= quarter / 2:
                continue
            far = [q for q in quick if min(abs(q.midi - m.midi) for m in main) > FAR]
            if far:
                out.append(
                    {
                        "staff": staff,
                        "frame": f,
                        "main": g,
                        "quick": "+".join(name(n) for n in quick),
                        "far": "+".join(name(n) for n in far),
                        "to": "+".join(name(n) for n in main),
                        "droppable": len(far) < len(quick),
                    }
                )
    return out


def parts(layers: set[str]) -> Iterator[tuple[str, str, bool]]:
    for part in bundle.list_parts():
        try:
            where = locate.part(part)
            title = bundle.read_project(where.project_id).title
        except (locate.NotFound, OSError):
            continue
        if where.layer not in layers:
            continue
        yield part, title, store.load(part) is not None


def study(layers: set[str]) -> None:
    total: Counter = Counter()
    print(
        "| Song | Sheet | Notes | Broken runs (R / L) | Odd columns | Far quick (chords / single) | "
        "Largest share of a window |"
    )
    print("|---|---|---|---|---|---|---|")
    for part, title, stored in parts(layers):
        try:
            sheet = f1.read(build._compute(part).text)
        except FileNotFoundError:
            continue
        runs, far = broken(sheet), far_quick(sheet)
        odd = [f for r in runs for f, _, _ in r["odd"]]
        changes = Counter(odd) + Counter(x["frame"] for x in far if x["droppable"])
        share = 0.0
        for a, b in llm_frames.windows_of(sheet):
            inside = sum(1 for n in sheet.notes if a <= n.frame < b)
            changed = sum(k for f, k in changes.items() if a <= f < b)
            share = max(share, changed / inside if inside else 0.0)
        right = sum(r["staff"] == 1 for r in runs)
        chords = sum(x["droppable"] for x in far)
        total.update(
            {
                "songs": 1,
                "notes": len(sheet.notes),
                "broken runs, right": right,
                "broken runs, left": len(runs) - right,
                "odd columns": len(odd),
                "far quick chords": chords,
                "far quick single notes": len(far) - chords,
            }
        )
        print(
            f"| {title[:40]} | {'stored' if stored else 'algorithm'} | {len(sheet.notes)} | {right} / "
            f"{len(runs) - right} | {len(odd)} | {chords} / {len(far) - chords} | {share * 100:.1f} % |"
        )
    print()
    for k, v in total.items():
        print(f"{k}: {v}")


def case(part: str, first: int, end: int) -> None:
    sheet = f1.read(build._compute(part).text)
    for f, ns in columns(sheet, 1) + columns(sheet, 2):
        if first <= f < end:
            hand = "R" if ns[0].staff == 1 else "L"
            print(
                f"f{f} {clock(f)} {hand}: "
                + " ".join(f"{name(n)}:{n.figure}{'g' if n.grace else ''}" for n in ns)
            )
    for r in broken(sheet):
        if first <= r["first"] < end or first <= r["last"] < end:
            print("broken:", r)
    for x in far_quick(sheet):
        if first <= x["frame"] < end:
            print("far quick:", x)


# ------------------------------------------------------------------ the gallery

#: (first column, end column, title, what to look at)
CASES: list[tuple[int, int, str, str]] = [
    (
        1760,
        1870,
        "The image complex-fast-notes.png",
        "The left hand played Sol 2 + Sol 3 as a quick semicorchea just before the chord Si-b 3 + Re 4: a jump of more "
        "than an octave down and up again. With prompt 6 the AI leaves out Sol 2 (the amateur pianist rule) and "
        "keeps Sol 3, next to the chord.",
    ),
    (
        5170,
        5280,
        "The same quick chord later in the song",
        "The same passage at 3:29: Sol 2 left out again, Sol 3 kept.",
    ),
    (
        4490,
        4610,
        "The image left-patterns.png",
        "The left hand plays a run of octavas Re 1 + Re 2 in semicorcheas, with three single Re 2 inside it, and a "
        "single Re 3 before it among octavas Re 2 + Re 3. With prompt 6 the AI adds the missing lower notes (the "
        "rules of simplicity): every column of the run is an octava, and its beam groups are even (4, 4, 5). La 1 "
        "starts the run and stays a single note.",
    ),
    (
        1802,
        2040,
        "The image abuse-decoration-notes.png",
        "The left hand's short notes before blanca chords (Phase 2: written notes, no decoration notes). Prompt 6 "
        "writes this passage again; the only note it changes here is the Sol 2 of case 1 (at 1:12.88).",
    ),
    (
        2180,
        2303,
        "The image abuse-decoration-notes-right.png",
        "The right hand's short notes before a negra (Phase 2: written semicorcheas). Nothing is added or left out "
        "here either.",
    ),
]


def _drawn(part: str) -> Sheet:
    return f1.read(build.current(part).text)


def changes(before: Sheet, after: Sheet, a: int, b: int) -> list[str]:
    """What changed in the columns ``[a, b)``: notes left out and added, hands, figures; from the data."""
    old = {(n.frame, n.midi): n for n in before.notes if a <= n.frame < b}
    new = {(n.frame, n.midi): n for n in after.notes if a <= n.frame < b}
    hand = {1: "right hand", 2: "left hand"}
    out = [
        f"f{f} ({clock(f)}): {name(old[(f, m)])} left out, {hand[old[(f, m)].staff]}"
        for f, m in sorted(old.keys() - new.keys())
    ]
    out += [
        f"f{f} ({clock(f)}): {name(new[(f, m)])} added, {hand[new[(f, m)].staff]}"
        for f, m in sorted(new.keys() - old.keys())
    ]
    for k in sorted(old.keys() & new.keys()):
        o, n = old[k], new[k]
        if o.staff != n.staff:
            out.append(f"f{k[0]}: {name(n)} moved to the {hand[n.staff]}")
        elif o.figure != n.figure:
            out.append(f"f{k[0]}: {name(n)} figure {o.figure} -> {n.figure}")
    return out


def gallery(out: Path, before_part: str, after_part: str) -> list[str]:
    before, after = _drawn(before_part), _drawn(after_part)
    opts = engine.Options(width=110)
    record = store.load(after_part).record
    problems = [p for p in frames_mod.check(after) if p not in set(frames_mod.check(before))]
    items, index = [], []
    for no, (a, b, title, look) in enumerate(CASES, start=1):
        listed = changes(before, after, a, b)
        text = (
            '<ul class="changes">' + "".join(f"<li>{html.escape(t)}</li>" for t in listed) + "</ul>"
            if listed
            else '<p class="changes">No note of the passage was added, left out, moved or given another figure.</p>'
        )
        index.append(f'<li><a href="#c{no}">{no}. {html.escape(title)}</a></li>')
        items.append(
            f'<section id="c{no}"><h3>{no}. {html.escape(title)}</h3>'
            f'<p class="song">7 Years, {clock(a)} to {clock(b)}</p><p class="look">{html.escape(look)}</p>'
            + _figure(
                "Before: the AI with prompt 5 (the My library version)",
                banded(engine.render_frames(before, opts, segment=(a, b)), a, b),
            )
            + _figure(
                "Now: the AI with prompt 6 (a test copy)",
                banded(engine.render_frames(after, opts, segment=(a, b)), a, b),
            )
            + f"<details open><summary>What changed in the passage (from the data)</summary>{text}</details></section>"
        )
    every = changes(before, after, 0, 10**6)
    added = [t for t in every if " added," in t or " left out," in t]
    summary = (
        f"<p>The whole song with prompt 6: {record.added} notes added and {record.left_out} left out (all of them "
        f"below), {sum(' figure ' in t for t in every)} figures different (the AI chose the reference figure "
        f"{record.quarter_ms:g} ms this time, 480 ms before), {sum(' moved to ' in t for t in every)} hands moved; "
        f"{len(problems)} new problems by the sheet's rules. Cost of the run: ${record.usd:.2f}.</p><ul>"
        + "".join(f"<li>{html.escape(t)}</li>" for t in added)
        + "</ul>"
    )
    page = (
        PAGE.replace("{{SUMMARY}}", summary)
        .replace("{{INDEX}}", "".join(index))
        .replace("{{SECTIONS}}", "".join(items))
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    return problems


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


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simplicity: Phase 3 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h3 { font-size: 16px; margin: 36px 0 2px; }
.song { margin: 0; color: var(--soft); font-size: 13px; } .look { margin: 4px 0; max-width: 980px; }
figure { margin: 8px 0 12px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; } details { font-size: 13px; color: var(--soft); }
.changes { margin: 4px 0; }
</style></head><body><main>
<h1>Simplicity in the AI's sheet: 7 Years</h1>
<p>Implementation 04, Phase 3. The AI's prompt version 6 asks for uniform patterns (the rules of simplicity) and for
sheets an amateur pianist can play (no quick jump of one hand), and lets the AI add and leave out a few notes for
them, within limits a check holds. Each case shows a passage as the AI wrote it with prompt 5 (the My library
version, drawn with the decoration-note rule of Phase 2) and with prompt 6 (a temporary copy, deleted after); the
band marks the passage.</p>
{{SUMMARY}}
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--study", action="store_true", help="the counts of every part")
    parser.add_argument(
        "--layers", default="private", help="the layers of the study (comma separated)"
    )
    parser.add_argument("--case", nargs=3, metavar=("PART", "FIRST", "END"), help="one passage")
    parser.add_argument("--out", type=Path, help="the folder of the gallery's index.html")
    parser.add_argument("--before", default=SEVEN_YEARS, help="the part with the sheet of prompt 5")
    parser.add_argument("--after", help="the part with the sheet of prompt 6 (a temporary copy)")
    args = parser.parse_args()
    if args.study:
        study(set(args.layers.split(",")))
    if args.case:
        case(args.case[0], int(args.case[1]), int(args.case[2]))
    if args.out:
        for problem in gallery(args.out, args.before, args.after):
            print("rule broken:", problem)
        print(f"{len(CASES)} cases -> {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
