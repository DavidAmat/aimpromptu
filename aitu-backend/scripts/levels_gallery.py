"""The whole song simplification by levels (implementation 04-3, Phase 3): the gallery of the test passages.

For each passage of a part: the passage as the app draws the sheet now (a band over it, the frame marks of the
sheet), the chords the app finds, and the measures of each hand (the hand tracker of ``sheet.levels.hands``); then,
for each level that a run in ``--runs`` holds, the AI's version drawn by the app's rules (``sheet.llm.levels.drawn``)
with its measures, the patterns and the notes it declared, the replies and the cost. The page also lists the
patterns of each level's run (drawn by the gallery of Phase 2) and links the prompts.

Nothing is written but the page. In the backend container::

    docker exec -i aimpromptu-backend-1 python scripts/levels_gallery.py --part c0e39afe-... \\
        --out ../context/implementations/04-app-enhancements/gallery/04-3-phase-3 [--runs runs.json]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from aitu_backend.part_sheet import build
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.levels.grid import song_grid
from aitu_backend.sheet.levels.hands import measure
from aitu_backend.sheet.levels.harmony import chords
from aitu_backend.sheet.llm import levels as L
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Sheet

from simplicity_gallery import banded

#: The test passages of 99 Red Balloons (plan task 3.1): first frame, end frame, name, why.
PASSAGES = [
    (
        33,
        539,
        "The intro",
        "The calm start: the melody alone in the right hand over a few bass notes. The sheet is already almost easy; "
        "the levels must keep it calm and give the left hand its pattern.",
    ),
    (
        783,
        1042,
        "The riff with the high chords",
        "The passage of the image 99-red-ballons-issue.png: the left hand plays chords of up to 7 notes over three "
        "octavas (E1 to E4), while the right hand plays only the chords D#7-E7 (under 8va) and D#6-E6.",
    ),
    (
        1042,
        1414,
        "After the riff (the image of the whole song)",
        "The passage of the image whole-song-simplification.png (its first line starts at f990): dense chords in "
        "both hands, octavas in the left hand that jump on every note, decoration notes.",
    ),
    (
        1826,
        2296,
        "The right hand high",
        "The melody around E6-G#6 with chords under it in the right hand, and a left hand in octavas that moves "
        "about once per negra.",
    ),
]

#: The patterns proposed for the tests of each level (the user may change them before any AI call).
SELECTION = {
    "easy": ["left easy 2", "left easy 1", "left easy 3", "left easy 12", "right easy 2", "right easy 1"],
    "medium": ["left medium 15", "left medium 2", "left medium 7", "left medium 10", "right medium 1", "right medium 14"],
    "hard": ["left hard 11", "left hard 1", "left hard 8", "left hard 4", "right hard 1", "right medium 1"],
}

COLS = [
    ("notes_s", "notes/s"),
    ("chord_max", "most notes in a column"),
    ("span", "widest column (semitones)"),
    ("reach", "range in two negras"),
    ("moves_q", "moves per negra"),
    ("moves_s", "moves/s"),
    ("big_moves_s", "big moves/s"),
    ("pattern", "repeated shape"),
]


def measures_table(rows: list[tuple[str, dict]]) -> str:
    head = "".join(f"<th>{html.escape(t)}</th>" for _, t in COLS)
    body = "".join(
        f"<tr><th>{html.escape(name)}</th>" + "".join(f"<td>{m.get(k, '')}</td>" for k, _ in COLS) + "</tr>"
        for name, m in rows
    )
    return f'<table class="m"><tr><th></th>{head}</tr>{body}</table>'


def _figure(cap: str, body: str) -> str:
    return f'<figure><figcaption>{html.escape(cap)}</figcaption><div class="svg">{body}</div></figure>'


def passage_section(no: int, sheet: Sheet, whole: engine.Rendered, grid, a: int, b: int, name: str, why: str,
                    runs: dict) -> str:
    key = sheet.key or 0
    cs = [c for c in chords(sheet, grid) if c.start < b and c.end > a]
    rows = [(f"{h} hand now", measure(sheet, st, a, b, grid).row()) for st, h in ((1, "Right"), (2, "Left"))]
    parts = [
        f'<section id="p{no}"><h2>{no}. {html.escape(name)} <span class="fr">f{a}-f{b} '
        f"({L.clock(a)}-{L.clock(b)})</span></h2>",
        f'<p class="look">{html.escape(why)}</p>',
        f'<p class="chords"><b>Chords found by the app:</b> {html.escape(L.chord_text(cs, key))}</p>',
    ]
    seg = engine.render_frames(sheet, engine.Options(width=130), segment=(a, b), note_ids=False)
    parts.append(_figure("The sheet now (the band marks the passage)", banded(seg, a, b)))
    for key, run in runs.items():
        if not key.endswith(f"|{a}"):
            continue
        label = run.get("label", key.split("|")[0]).capitalize()
        status = "" if run.get("status", "ok") == "ok" else " (the check refused the last reply: drawn as written)"
        rows.append((f"{label}: right", run["measures"].get("1", {})))
        rows.append((f"{label}: left", run["measures"].get("2", {})))
        said = "".join(f"<li>{html.escape(x)}</li>" for x in run.get("declared", []))
        errs = "".join(
            f"<li>Reply {i + 1}: {html.escape('; '.join(e))}</li>" for i, e in enumerate(run.get("errors", []))
        )
        body = engine.render_frames(f1.read(run["text"]), engine.Options(width=130), note_ids=False).svg if run.get("text") else "no answer"
        parts.append(
            _figure(
                f"{label}{status}: {run.get('model', 'AI')}, {run.get('replies', 1)} replies, ${run.get('usd', 0):.3f}; "
                f"melody line {run.get('melody', 0)} notes, {run.get('melody_dropped', 0)} declared not melody or artifact",
                body,
            )
            + (f"<details open><summary>What the AI declared</summary><ul>{said}</ul></details>" if said else "")
            + (f"<details><summary>What the check refused before</summary><ul>{errs}</ul></details>" if errs else "")
        )
    parts.append(measures_table(rows))
    parts.append("</section>")
    return "\n".join(parts)


def patterns_section(catalog: Path, rel: str) -> str:
    data = json.loads((catalog / "patterns.json").read_text())
    by_ref = {p["ref"]: p for p in data["patterns"]}
    out = ['<section id="patterns"><h2>The patterns proposed for each level</h2>',
           '<p class="look">Only the example of these patterns goes into the prompt of each level (the start of its first '
           "example, both hands). The drawings are the ones of the gallery of patterns.</p>"]
    for level, refs in SELECTION.items():
        out.append(f"<h3>{level.capitalize()}</h3><div class=\"pats\">")
        for ref in refs:
            p = by_ref[ref]
            ex = p["examples"][0]
            out.append(
                f'<div class="pat"><b>{html.escape(ref.capitalize())}</b>: {html.escape(p["name"])}'
                f'<div class="line">{html.escape(p["line"])}</div>'
                f'<img src="{rel}/{html.escape(ex["f1"][:-3] + ".svg")}" alt="{html.escape(p["name"])}"></div>'
            )
        out.append("</div>")
    out.append("</section>")
    return "\n".join(out)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Levels: Phase 3 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { font-size: 19px; margin: 40px 0 4px; } h3 { font-size: 16px; margin: 20px 0 4px; }
.fr { color: var(--soft); font-weight: normal; font-size: 14px; }
.look { margin: 4px 0; max-width: 980px; } .chords { font-size: 13px; color: var(--soft); max-width: 1200px; }
figure { margin: 8px 0 12px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; } details { font-size: 13px; color: var(--soft); }
table.m { border-collapse: collapse; font-size: 13px; margin: 8px 0; }
table.m th, table.m td { border: 1px solid var(--line); padding: 3px 8px; text-align: right; }
table.m th { background: #f6f6f7; font-weight: 600; } table.m tr > th:first-child { text-align: left; }
.pats { display: grid; grid-template-columns: repeat(auto-fill, minmax(440px, 1fr)); gap: 12px; }
.pat { border: 1px solid var(--line); border-radius: 6px; padding: 8px; font-size: 13px; }
.pat img { width: 100%; margin-top: 6px; } .line { color: var(--soft); }
</style></head><body><main>
<h1>Levels on 99 Red Balloons: the test passages</h1>
{{INTRO}}
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""

INTRO = """<p class="look">Implementation 04-3, Phase 3. These are the passages of 99 Red Balloons (the project
c0e39afe, the sheet as it is now) on which the prompts of the levels easy, medium and hard will be tested. Each
passage shows the sheet now with a band over it, the chords the app finds in the notes, and the measures of each
hand: notes per second, the most notes in one column and the widest column, the range of the hand inside two negras,
how often the hand tracker moves the hand (per negra and per second; a big move is more than 7 semitones), and the
share of negras whose shape repeats. The gallery of patterns gives the same measures by level: the left hand moves
at most 0.6 times per negra at easy, up to about 1.4 at medium and 2.0 at hard.</p>
<p class="look">The prompts: <a href="prompts/system-easy.md">easy</a>, <a href="prompts/system-medium.md">medium</a>,
<a href="prompts/system-hard.md">hard</a> (each one is the shared part, the part of the level and its patterns);
<a href="prompts/plan-easy.md">the request for the plan of the song</a>; <a href="prompts/batch-easy-1042.md">a batch
request</a> (passage 3 at easy).</p>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--runs", type=Path, help="JSON of the AI runs: {'level|start': {...}}")
    parser.add_argument("--catalog", type=Path,
                        default=Path("../context/implementations/04-app-enhancements/gallery/04-3-phase-2"))
    args = parser.parse_args()
    sheet = f1.read(build.current(args.part).text)
    grid = song_grid(sheet)
    data = json.loads(args.runs.read_text()) if args.runs else {}
    runs, meta = data.get("runs", {}), data.get("meta", {})
    whole = None
    sections, index = [], []
    for name, m in meta.items():
        plan = "".join(f"<li>{html.escape(x)}</li>" for x in m.get("plan", []))
        sections.append(
            f'<section id="plan-{name}"><h2>The run {html.escape(name)}: '
            f'{html.escape(L.level_name(m["level"]))}</h2><p class="look">Patterns: {html.escape(", ".join(m["refs"]))}. '
            f"Cost of the run: ${m['usd']:.3f} (the plan request ${m['plan_usd']:.3f}), {m['seconds']} s.</p>"
            f"<p class=\"look\">The plan of the song the AI wrote (the first request):</p><ul>{plan}</ul></section>"
        )
        index.append(f'<li><a href="#plan-{name}">The run {html.escape(name)} and its plan</a></li>')
    for no, (a, b, name, why) in enumerate(PASSAGES, start=1):
        sections.append(passage_section(no, sheet, whole, grid, a, b, name, why, runs))
        index.append(f'<li><a href="#p{no}">{html.escape(name)}</a> (f{a}-f{b})</li>')
    sections.append(patterns_section(args.catalog, "../04-3-phase-2"))
    index.append('<li><a href="#patterns">The patterns proposed for each level</a></li>')
    args.out.mkdir(parents=True, exist_ok=True)
    page = PAGE.replace("{{INTRO}}", INTRO).replace("{{INDEX}}", "".join(index)).replace("{{SECTIONS}}", "\n".join(sections))
    (args.out / "index.html").write_text(page)
    print(f"wrote {args.out / 'index.html'} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
