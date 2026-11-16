"""Copy this style, implementation 06, Phase 1: the study of the matcher and its gallery (plan section 4.8 of
``context/implementations/06-copy-this-style/06-plan.md``).

The matcher (``sheet.style.match``) finds the passages of a song like a reference the user selects. This script runs
it on the songs of My library and shows what it finds, so that the user can choose its numbers (the threshold, the
weights, the lengths, the shifts):

* ``--find PART``: the phrases of a part (a phrase starts after a pause of the right hand) and the places each one
  finds, to choose the references of the study.
* ``--study``: for each reference of :data:`CASES`, the places found with their score, its parts and the shift; the
  same with no shift searched and with the notes marked removed left out; the seconds. Then, for the six songs of
  plan section 3.1, the 8-second passages that find another passage (the measure ``like_before`` had there).
* ``--out DIR``: the gallery, ``DIR/index.html``: each reference drawn by the app, under it each passage kept and
  the best places under the threshold, one above the other, with the score.

Nothing is written to the database: the sheets are computed, never stored. In the backend container::

    docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/style_study.py --study
    docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/style_study.py \\
        --out ../context/implementations/06-copy-this-style/gallery/phase-1
"""

from __future__ import annotations

import argparse
import html
import time
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from aitu_backend.part_sheet import build
from aitu_backend.pmn import events_file
from aitu_backend.pmn.notes import Notes
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.levels.grid import Grid, song_grid
from aitu_backend.sheet.levels.harmony import Chord, chords
from aitu_backend.sheet.llm import frames as llm_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS, Sheet
from aitu_backend.sheet.style import match
from aitu_backend.storage import bundle, locate
from aitu_backend.transcription import pipeline

HANDS = {(1,): "the right hand", (2,): "the left hand", (1, 2): "both hands"}
SONGS = {
    "1a16a836": "7 Years (AI sheet)",
    "f3680cb8": "Titanium",
    "68e277fe": "Shut Up and Dance",
    "c33860b5": "My Way, piano cover",
    "a585f9eb": "Superestrella, piano cover",
    "b2db46eb": "99 Red Balloons",
}
#: A pause of the right hand this long (negras) or more starts a phrase (``--find``).
PAUSE = 1.5


@dataclass
class Song:
    part: str
    title: str
    sheet: Sheet
    notes: Notes
    grid: Grid
    harmony: list[Chord]
    seconds: dict[str, float]


@lru_cache(maxsize=None)
def song(prefix: str) -> Song:
    part = next(p for p in bundle.list_parts() if p.startswith(prefix))
    title = bundle.read_project(locate.part(part).project_id).title
    t = time.perf_counter()
    sheet = f1.read(build.current(part).text)
    seconds = {"sheet": time.perf_counter() - t}
    t = time.perf_counter()
    notes = events_file.notes_from_events(pipeline.load_note_events(part).events)
    seconds["notes"] = time.perf_counter() - t
    t = time.perf_counter()
    grid = song_grid(sheet)
    seconds["grid"] = time.perf_counter() - t
    t = time.perf_counter()
    harmony = chords(sheet, grid)
    seconds["chords"] = time.perf_counter() - t
    return Song(part, title, sheet, notes, grid, harmony, seconds)


def clock(frame: int) -> str:
    seconds = frame * FRAME_MS / 1000
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def found(s: Song, start: int, end: int, staffs, **kw) -> list[match.Match]:
    return match.ranked(
        s.sheet, kw.pop("notes", s.notes), start, end, staffs, grid=s.grid, harmony=s.harmony, **kw
    )


def line(m: match.Match) -> str:
    p = m.parts
    shift = f" shift {m.shift:+d}" if m.shift else ""
    return (
        f"f{m.start}-f{m.end} ({clock(m.start)}) {m.score:.2f}{shift} [rhythm {p['rhythm']:.2f}, contour "
        f"{p['contour']:.2f}, classes {p['classes']:.2f}, harmony {p['harmony']:.2f}, steps {p['steps']:.0f}]"
    )


# ------------------------------------------------------------------ choosing the references


def phrases(s: Song, staffs) -> list[int]:
    """The first frame of each phrase: a column of the right hand after a pause of ``PAUSE`` negras or more."""
    q = (s.sheet.quarter_ms or 500) / FRAME_MS
    cols = sorted({n.frame for n in s.sheet.notes if n.staff == 1 and not n.grace})
    return [b for a, b in zip([-10**6] + cols, cols) if b - a >= PAUSE * q]


def find(prefix: str, staffs, negras: int) -> None:
    s = song(prefix)
    q = (s.sheet.quarter_ms or 500) / FRAME_MS
    print(f"{s.title} ({s.part[:8]}), {HANDS[staffs]}, phrases of about {negras} negras")
    for a in phrases(s, staffs):
        b = int(a + negras * q)
        top = [m for m in found(s, a, b, staffs, floor=0.45, limit=8)]
        print(f"  ref f{a}-f{b} ({clock(a)}): " + "; ".join(
            f"f{m.start} {m.score:.2f}{f' s{m.shift:+d}' if m.shift else ''}" for m in top
        ))


# ------------------------------------------------------------------ the references of the study

#: (song, first frame, end frame, hands, what it is); chosen with ``--find`` (the Phase 1 report)
CASES: list[tuple[str, int, int, tuple[int, ...], str]] = [
    ("1a16a836", 577, 769, (1,), "a phrase at 0:23 that comes back often"),
    ("1a16a836", 877, 1069, (1,), "a phrase at 0:35"),
    ("1a16a836", 877, 1069, (1, 2), "the same phrase, both hands"),
    ("c33860b5", 145, 453, (1,), "the first phrase of the melody"),
    ("c33860b5", 676, 984, (1,), "a phrase at 0:27"),
    ("c33860b5", 2217, 2525, (1,), "a phrase at 1:28"),
    ("c33860b5", 609, 1222, (1, 2), "a long reference of 25 seconds, both hands"),
    ("c33860b5", 609, 1222, (2,), "the same long reference, the left hand"),
    ("a585f9eb", 1742, 2094, (1,), "a phrase at 1:09"),
    ("a585f9eb", 590, 942, (1,), "a phrase at 0:23"),
    ("f3680cb8", 1385, 1670, (1,), "a phrase at 0:55"),
    ("f3680cb8", 570, 855, (1, 2), "a phrase at 0:22, both hands"),
]


def study() -> None:
    print("## The references\n")
    for prefix, a, b, staffs, what in CASES:
        s = song(prefix)
        t = time.perf_counter()
        every = found(s, a, b, staffs, floor=0.3, limit=24)
        seconds = time.perf_counter() - t
        kept = [m for m in every if m.score >= match.THRESHOLD][: match.STYLE_MAX]
        flat = found(s, a, b, staffs, floor=0.3, limit=24, shifts=(0,))
        live = found(s, a, b, staffs, floor=0.3, limit=24, notes=None)
        print(f"### {SONGS[prefix]}: {what}, {HANDS[staffs]}, f{a}-f{b} ({clock(a)} to {clock(b)})\n")
        print(f"- the matcher: {seconds * 1000:.0f} ms; kept {len(kept)} at {match.THRESHOLD} or more")
        for m in every[:16]:
            mark = "kept" if m in kept else "under"
            print(f"  - {mark} {line(m)}")
        print(f"- no shift searched: kept {sum(m.score >= match.THRESHOLD for m in flat)}; "
              f"the best places {', '.join(f'f{m.start} {m.score:.2f}' for m in flat[:6])}")
        print(f"- the removed notes left out: kept {sum(m.score >= match.THRESHOLD for m in live)}; "
              f"the best places {', '.join(f'f{m.start} {m.score:.2f}' for m in live[:6])}")
        print()
    print("## The 8-second passages (plan section 3.1)\n")
    print("| Song | Passages | like_before R / L | Earlier found R / L | Any found R / L | Seconds: sheet, grid, chords, matcher |")
    print("|---|---|---|---|---|---|")
    for prefix, name in SONGS.items():
        s = song(prefix)
        frames = sorted({n.frame for n in s.sheet.notes})
        first, last = frames[0], frames[-1]
        size = int(8000 / FRAME_MS)
        cuts = list(range(first, last - size // 2, size))
        counts = {k: [0, 0] for k in ("like", "earlier", "any")}
        spent = 0.0
        for a in cuts:
            b = a + size
            for k, st in enumerate((1, 2)):
                if llm_frames.like_before(s.sheet, st, a, b, a) is not None:
                    counts["like"][k] += 1
                t = time.perf_counter()
                hits = found(s, a, b, (st,), floor=match.THRESHOLD, limit=match.STYLE_MAX)
                spent += time.perf_counter() - t
                counts["any"][k] += bool(hits)
                counts["earlier"][k] += any(m.end <= a for m in hits)
        sec = s.seconds
        per = spent / (2 * len(cuts)) * 1000
        print(
            f"| {name} (`{prefix}`) | {len(cuts)} | {counts['like'][0]} / {counts['like'][1]} "
            f"| {counts['earlier'][0]} / {counts['earlier'][1]} | {counts['any'][0]} / {counts['any'][1]} "
            f"| {sec['sheet']:.2f}, {sec['grid']:.2f}, {sec['chords']:.2f}, {per:.0f} ms |"
        )


# ------------------------------------------------------------------ the gallery


def piece(s: Song, a: int, b: int) -> Sheet:
    """The passage ``[a, b)`` alone, both hands, with the clefs and the armadura in force at ``a``."""
    part = llm_frames._slice(s.sheet, a, b, (1, 2))
    return replace(part, lyrics=[], titles={})


def drawing(s: Song, a: int, b: int, width: float) -> str:
    return engine.render_frames(piece(s, a, b), engine.Options(width=width), note_ids=False).svg


def figure(cap: str, body: str, cls: str = "") -> str:
    return (
        f'<figure class="{cls}"><figcaption>{cap}</figcaption><div class="svg">{body}</div></figure>'
    )


def gallery(out: Path, width: float, below: int) -> None:
    sections, index = [], []
    for no, (prefix, a, b, staffs, what) in enumerate(CASES, start=1):
        s = song(prefix)
        every = found(s, a, b, staffs, floor=0.3, limit=24)
        kept = sorted([m for m in every if m.score >= match.THRESHOLD][: match.STYLE_MAX], key=lambda m: m.start)
        under = [m for m in every if m.score < match.THRESHOLD][:below]
        title = f"{SONGS[prefix]}: {what}, {HANDS[staffs]}"
        anchor = f"r{no}"
        index.append(f'<li><a href="#{anchor}">{no}. {html.escape(title)}</a> ({len(kept)} kept)</li>')
        body = [
            f'<section id="{anchor}"><h2>{no}. {html.escape(title)}</h2>',
            f'<p class="song">The reference: f{a}-f{b}, {clock(a)} to {clock(b)}. Compared: {HANDS[staffs]}. '
            f"Kept: {len(kept)} passages at {match.THRESHOLD} or more; then the best {len(under)} places under it.</p>",
            figure(f"<b>The reference</b> f{a}-f{b} ({clock(a)})", drawing(s, a, b, width), "ref"),
        ]
        for m in kept:
            body.append(figure(f"<b>Kept, {m.score:.2f}</b> {html.escape(line(m))}", drawing(s, m.start, m.end, width), "kept"))
        for m in under:
            body.append(figure(f"<b>Not kept, {m.score:.2f}</b> {html.escape(line(m))}", drawing(s, m.start, m.end, width), "under"))
        body.append("</section>")
        sections.append("".join(body))
    page = (
        PAGE.replace("{{INDEX}}", "".join(index))
        .replace("{{SECTIONS}}", "".join(sections))
        .replace("{{THRESHOLD}}", str(match.THRESHOLD))
        .replace("{{WEIGHTS}}", ", ".join(f"{k} {v}" for k, v in match.WEIGHTS.items()))
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"{len(CASES)} references -> {out / 'index.html'}")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Copy this style: the passages the code finds (06, Phase 1)</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h2 { font-size: 18px; margin: 48px 0 2px; }
.song { margin: 0 0 8px; color: var(--soft); font-size: 13px; }
figure { margin: 8px 0 14px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
figcaption b { color: var(--ink); }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.ref .svg { border: 2px solid #3b6fd8; } .under .svg { border-style: dashed; background: #fafafa; }
.svg svg { display: block; max-width: none; } ol { font-size: 14px; }
</style></head><body><main>
<h1>Copy this style: the passages the code finds</h1>
<p>Implementation 06, Phase 1. For each reference (blue frame), the passages of the song the code finds like it, in
the order of the song. A score is from 0 to 1; a passage at
{{THRESHOLD}} or more is kept (it would be in the dialog's list, ticked). Under the kept ones, with a dashed frame, the
best places under the line: they would not be in the list. The parts of a score: the rhythm on the song's grid, the
contour (the steps of the top line, or of the lowest for the left hand), the pitch classes, the harmony of the song;
weights {{WEIGHTS}}. "shift +2" means the passage plays the reference a tone higher. Each passage is drawn alone,
from its first column.</p>
<p>What to look at: is each kept passage the same kind of passage as the reference? Is a passage under the line one
you would want in the list?</p>
<ol>{{INDEX}}</ol>
{{SECTIONS}}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--find", help="the phrases of a part (the first characters of its id) and what they find")
    parser.add_argument("--hands", default="1", help="with --find: 1, 2 or 12")
    parser.add_argument("--negras", type=int, default=24, help="with --find: the length of a phrase")
    parser.add_argument("--study", action="store_true", help="the numbers of the study")
    parser.add_argument("--out", type=Path, help="the folder of the gallery's index.html")
    parser.add_argument("--width", type=float, default=150.0, help="the gallery's staff width")
    parser.add_argument("--below", type=int, default=3, help="the places under the threshold shown")
    args = parser.parse_args()
    if args.find:
        find(args.find, tuple(int(c) for c in args.hands), args.negras)
    if args.study:
        study()
    if args.out:
        gallery(args.out, args.width, args.below)


if __name__ == "__main__":
    main()
