"""The Phase 4 gallery: passages of the 10 viewer songs written by the algorithm and by Sonnet, side by side.

Implementation 03, Phase 4, task 4.6. It reads a run of ``scripts/llm_sheet.py`` (``<database>/lab/sheet-llm/<run>/``:
``<part>.f1`` is Sonnet's sheet, ``<part>-algorithm.f1`` the algorithm's with the same reference figure, and
``summary.json``) and draws each case with the new engine (``engrave.frames``, the lines of the whole song that hold
the passage, the passage on a light band). Each case has one sentence that says what to look at.

    python scripts/llm_gallery.py --run viewer-1 --out ../context/implementations/03-apply-poc-research/gallery/phase-4
    python scripts/llm_gallery.py --run viewer-1 --find      # list the passages where the two sheets differ most

On the host, load ``.env`` first, or the script opens an empty ``.database/``. The page is ``DIR/index.html``.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Sheet
from aitu_backend.sheet.sheet.figures import NAMES
from aitu_backend.storage import bundle, paths

#: (section, part, first column, end column, title, what to look at)
CASES: list[tuple[str, str, int, int, str, str]] = [
    (
        "Beam groups",
        "2ed0f379",
        800,
        1050,
        "A repeated bass pattern: one group per repetition",
        "Left hand: an octave bass pattern that repeats. Sonnet makes one group of four notes for each repetition, "
        "so the eye sees the same shape again and again; the algorithm runs groups of seven and eight notes across "
        "the repetitions. The right hand's repeated notes are in groups of four too.",
    ),
    (
        "Beam groups",
        "43faf78e",
        1800,
        2050,
        "An arpeggio that rises and falls",
        "Left hand: a broken chord that goes up and comes down. Sonnet makes one group for each rise and fall and "
        "cuts where the next chord starts; the algorithm cuts at other places. The clef changes inside the "
        "arpeggio are rule clef.L4 (see the section on clefs).",
    ),
    (
        "Beam groups",
        "1a16a836",
        4300,
        4550,
        "Short-long pairs in the melody",
        "Right hand: a semicorchea beamed to the corchea after it, the rhythm of the melody. A pair of two figures "
        "is allowed by your rule (one note of another figure may open a group). The left hand's small notes "
        "before its chords are acciaccaturas by the rule (octaves played unevenly).",
    ),
    (
        "Beam groups",
        "b80e6f5a",
        3900,
        4150,
        "Chords in groups, and the left hand kept in its clef",
        "Right hand: repeated chords grouped by four, then a new group where the chord changes. Left hand: the "
        "algorithm moves some chords to the right hand (a bass clef in the upper staff) and jumps to the treble "
        "clef; Sonnet keeps the bass and chord pattern in the left hand, in the bass clef.",
    ),
    (
        "Hands",
        "4cb9cb38",
        1500,
        1750,
        "Low chords of the accompaniment go to the left hand",
        "The algorithm gives low chords to the right hand, below the treble staff with ledger lines. Sonnet "
        "gives them to the left hand (a bass note and a chord, beamed in pairs), and the right hand keeps the "
        "melody. 224 notes of this song changed hand, the most of the 10 songs.",
    ),
    (
        "Hands",
        "c0edc9b0",
        1150,
        1400,
        "A clean split between melody and accompaniment",
        "The algorithm puts very low notes in the right hand (five ledger lines below the staff) and makes the "
        "left hand jump between clefs. Sonnet keeps the melody and its chords in the right hand and the "
        "accompaniment in the left hand, in the bass clef. The wavy line before a wide chord is a rolled chord "
        "(arp), which Sonnet wrote 85 times in this song.",
    ),
    (
        "Hands",
        "3c8d4cfa",
        3900,
        4150,
        "A right hand that stays in the treble clef",
        "In the second line the algorithm gives a low note to the right hand and needs a bass clef in the upper "
        "staff for it; Sonnet gives that note to the left hand, and both staves keep their clef.",
    ),
    (
        "Hands",
        "92255337",
        2150,
        2400,
        "Chords that belong to the left hand",
        "The algorithm moves the chords of the accompaniment to the right hand and changes the upper staff to the "
        "bass clef twice; Sonnet keeps them in the left hand under a right hand that stays in the treble clef.",
    ),
    (
        "Clefs and 8va (a question for you)",
        "f4c4de9a",
        1450,
        1700,
        "A high cover: long 8va lines, and a left hand that changes clef often",
        "This cover is played high. The right hand is under 8va lines (Sonnet marked the high notes; the app "
        "joins nearby 8va notes into one line). The left hand alternates low notes and high chords about twice a "
        "second, and your rule clef.L4 puts the low notes in the bass clef and the chords in the treble clef, so "
        "the clef changes very often. Do you want this, or the chords in the bass clef with ledger lines?",
    ),
    (
        "Figures of staccato notes (a question for you)",
        "68e277fe",
        600,
        850,
        "Short notes become fusas and semifusas",
        "The left hand plays short detached notes a corchea apart. Their figure comes from their own length "
        "(your rule), so they are fusas and semifusas with three or four beams, which reads as a very fast "
        "passage. Sonnet cannot change figures: they are a rule of the app.",
    ),
]


def run_dir(name: str) -> Path:
    return paths.lab_dir() / "sheet-llm" / name


def load(run: Path, short: str) -> tuple[Sheet, Sheet]:
    return f1.read((run / f"{short}.f1").read_text()), f1.read(
        (run / f"{short}-algorithm.f1").read_text()
    )


def beam_pairs(sheet: Sheet, a: int, b: int) -> set[tuple[int, int, int]]:
    """(staff, frame, next frame) of consecutive columns of one hand joined by a beam, inside [a, b)."""
    out = set()
    for staff in (1, 2):
        cols: dict[int, set] = defaultdict(set)
        for n in sheet.notes:
            if n.staff == staff and not n.grace and not n.covered and a <= n.frame < b:
                cols[n.frame].add(n.beam)
        fr = sorted(cols)
        for x, y in zip(fr, fr[1:]):
            if cols[x] & cols[y] - {None}:
                out.add((staff, x, y))
    return out


def differences(llm: Sheet, algo: Sheet, a: int, b: int) -> dict:
    hands = {(n.frame, n.midi): n.staff for n in algo.notes}
    moved = sum(
        1
        for n in llm.notes
        if a <= n.frame < b and hands.get((n.frame, n.midi), n.staff) != n.staff
    )
    pl, pa = beam_pairs(llm, a, b), beam_pairs(algo, a, b)
    clefs = lambda s: {c for c in s.clef_changes if a <= c[0] < b}  # noqa: E731
    return {
        "moved": moved,
        "beams": len(pl ^ pa),
        "clefs": len(clefs(llm) ^ clefs(algo)),
        "keys": len(
            {k for k in llm.key_changes if a <= k[0] < b}
            ^ {k for k in algo.key_changes if a <= k[0] < b}
        ),
    }


def find(run: Path) -> None:
    rows = json.loads((run / "summary.json").read_text())
    for r in rows:
        short = r["part"][:8]
        llm, algo = load(run, short)
        last = max(n.frame for n in llm.notes)
        best = []
        for a in range(0, last, 50):
            d = differences(llm, algo, a, a + 250)
            best.append((d["moved"] + d["beams"] + 3 * d["clefs"] + 5 * d["keys"], a, d))
        best.sort(key=lambda x: -x[0])
        shown = []
        for score, a, d in best:
            if all(abs(a - s) >= 250 for _, s, _ in shown):
                shown.append((score, a, d))
            if len(shown) == 3:
                break
        print(short, [(a, round(a * 0.04), d) for _, a, d in shown])


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


def _time(ms: float) -> str:
    return f"{int(ms // 60000)}:{int(ms % 60000 // 1000):02d}"


def _figure(cap: str, body: str) -> str:
    return (
        f'<figure><figcaption>{html.escape(cap)}</figcaption><div class="svg">{body}</div></figure>'
    )


def _table(rows: list[dict], titles: dict[str, str]) -> str:
    head = (
        "<tr><th>Song</th><th>Reference figure (negra)</th><th>Windows accepted (first check)</th>"
        "<th>Requests</th><th>Cost</th><th>Time</th><th>Same hand as the research's Sonnet</th>"
        "<th>Same hand: the algorithm</th><th>Beam groups kept / cut / removed by the figures</th></tr>"
    )
    body = []
    for r in rows:
        info = r["info"]
        vs, va = r.get("vsRecorded", {}), r.get("algorithmVsRecorded", {})
        body.append(
            f"<tr><td>{html.escape(titles.get(r['part'], r['part'][:8]))}</td>"
            f"<td>{r['quarterMs']:.0f} ms ({r['reference']['source']}; research Sonnet "
            f"{r.get('recordedQuarterMs') or '-'} ms)</td>"
            f"<td>{r['ok']} of {r['windows']} ({r['ok_first_check']})</td><td>{r['requests']}</td>"
            f"<td>${r['usd']:.2f}</td><td>{r['requestSeconds'] / 60:.1f} min</td>"
            f"<td>{vs.get('sameHand', 0) * 100:.1f} %</td><td>{va.get('sameHand', 0) * 100:.1f} %</td>"
            f"<td>{info.get('beams: groups kept', 0)} / {info.get('beams: groups cut', 0)} / "
            f"{info.get('beams: groups removed', 0)}</td></tr>"
        )
    return f"<table>{head}{''.join(body)}</table>"


def build(run: Path, out: Path) -> None:
    rows = json.loads((run / "summary.json").read_text())
    parts = bundle.list_parts(layers=["private"])
    titles = {}
    for r in rows:
        project = json.loads((paths.part_dir(r["part"]).parents[1] / "project.json").read_text())
        titles[r["part"]] = project.get("title", "")
    opts = engine.Options(width=130)
    sections: dict[str, list[str]] = defaultdict(list)
    index = []
    cache: dict[str, tuple[Sheet, Sheet]] = {}
    for no, (section, short, a, b, title, look) in enumerate(CASES, start=1):
        if short not in cache:
            cache[short] = load(run, short)
        llm, algo = cache[short]
        pid = next(p for p in parts if p.startswith(short))
        drawings = [
            _figure(
                "The algorithm (Phase 2), with the same reference figure",
                banded(engine.render_frames(algo, opts, segment=(a, b)), a, b),
            ),
            _figure(
                "Sonnet 5.5 (prompt version 5)",
                banded(engine.render_frames(llm, opts, segment=(a, b)), a, b),
            ),
        ]
        anchor = f"c{no}"
        index.append(f'<li><a href="#{anchor}">{no}. {html.escape(title)}</a></li>')
        notes = [n for n in llm.notes if a <= n.frame < b]
        when = _time(min(n.frame for n in notes) * 40)
        figs = ", ".join(f"{NAMES[k]} {round(llm.quarter_ms * 4 / k)} ms" for k in (4, 8, 16))
        d = differences(llm, algo, a, b)
        sections[section].append(
            f'<section id="{anchor}"><h3>{no}. {html.escape(title)}</h3>'
            f'<p class="look">{html.escape(look)}</p>'
            f'<p class="where">{html.escape(titles.get(pid, short))}, from {when} (columns f{a} to f{b - 1}). '
            f"Reference figure: {figs}. Differences in the passage: {d['moved']} notes in another hand, "
            f"{d['beams']} beam joins, {d['clefs']} clef changes.</p>{''.join(drawings)}</section>"
        )
    page = (
        PAGE.replace("{{TABLE}}", _table(rows, titles))
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


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>New sheet: Phase 4 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; --tint: #f6f6f8; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { margin: 40px 0 8px; font-size: 20px; border-bottom: 1px solid var(--line); }
h3 { font-size: 16px; margin: 28px 0 4px; } .look { margin: 0 0 4px; max-width: 980px; }
.where { color: var(--soft); margin: 0 0 8px; font-size: 13px; }
figure { margin: 8px 0 14px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; }
table { border-collapse: collapse; font-size: 13px; margin: 12px 0; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 4px 8px; text-align: left; vertical-align: top; }
th { background: var(--tint); } ol { columns: 2; font-size: 14px; }
</style></head><body><main>
<h1>The new sheet: Sonnet 5.5 and the algorithm</h1>
<p>Implementation 03, Phase 4. Sonnet 5.5 reads each song window by window (12 to 16 seconds) and decides the hands,
the beam groups, the clefs and 8va, the ornaments and the armadura of each passage; it also chose the reference figure
of each song. The app then computes the figures, the grace notes and the accidentals by its rules, cuts a beam
group where the figures break it (one figure per group), and joins nearby 8va notes into one line. Each case shows the same passage written by the algorithm
(the sheet the app shows at once) and by Sonnet (what replaces it, segment by segment). The band marks the passage.
Please judge the beam groups (the criteria of the plan, section 3.11, and the maximum of 8 notes), the hands and the
clefs.</p>
{{TABLE}}
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="the run folder of scripts/llm_sheet.py")
    parser.add_argument("--out", type=Path, help="the folder of index.html")
    parser.add_argument(
        "--find", action="store_true", help="list the passages where the sheets differ most"
    )
    args = parser.parse_args()
    if args.find:
        find(run_dir(args.run))
    else:
        build(run_dir(args.run), args.out)


if __name__ == "__main__":
    main()
