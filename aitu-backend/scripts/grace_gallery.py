"""The decoration-note rule of implementation 04, Phase 2: the study of My library and the gallery, old and new.

The old rule (implementation 03, Phase 2): one or two semicorcheas or shorter, two figures or more shorter than the
next note and sounding just before it, were grace notes. The new rule (the user's, plan section 3.1 of
``context/implementations/04-app-enhancements/04-plan.md``): only fusas or shorter are grace notes; one or two other
notes more than two figures shorter than the next note are written two figures shorter than it; a run of three or
more keeps its figures; two such notes that a stored sheet held as grace notes are beamed together. This script keeps
a copy of the old rule (:func:`rule`) to draw the sheets as they were.

* ``--study``: for every part of My library (``private``; ``--layers`` for others), the grace notes of the old rule
  and what the new rule makes of them (still grace notes, written with their own figure, written longer), the notes
  written longer that were not grace notes, what else changed (beam groups that hold no changed column, hands, 8va,
  spelling, clefs, armaduras: all should be 0), and the time of one drawing of a stored sheet, old and new.
* ``--out DIR``: the gallery, ``DIR/index.html``: each case a passage drawn with the old rule and with the new one
  (the engine of the new sheet, as the page draws it), one sentence on what to look at, and the list of the columns
  that changed, read from the data.

Nothing is written to the database: the sheets are computed (``part_sheet.build._compute``), never stored. On the host,
load ``.env`` first, or the script opens an empty ``.database/``; in the backend container it runs as it is::

    docker exec -i aimpromptu-backend-1 python scripts/grace_gallery.py --study
    docker exec -i aimpromptu-backend-1 python scripts/grace_gallery.py \\
        --out ../context/implementations/04-app-enhancements/gallery/phase-2
"""

from __future__ import annotations

import argparse
import html
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from aitu_backend.part_sheet import build, store
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.llm import frames as llm_frames
from aitu_backend.sheet.proposal import frames as proposal
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.common import spn
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.sheet.sheet.figures import NAMES, SPLIT, figure_of_ms
from aitu_backend.storage import bundle, locate

SEVEN_YEARS = "1a16a836-62b9-483b-af46-d89d0ab1b2d8"

# ------------------------------------------------------------------ the old rule


def old_find_graces(sheet: Sheet, quarter_ms: float, split: float = SPLIT) -> int:
    """``proposal.frames.find_graces`` as it was before implementation 04 (semicorcheas or shorter)."""
    count = 0
    for staff in (1, 2):
        cols = proposal._columns(sheet, staff)
        starts = [ns[0].on_ms for _, ns in cols]
        fig = [ns[0].figure for _, ns in cols]
        never = [any(n.fixed or n.grace_rule == "off" for n in ns) for _, ns in cols]
        forced = [
            not never[i] and any(n.grace_rule == "on" for n in ns) for i, (_, ns) in enumerate(cols)
        ]
        for k in range(1, len(cols)):
            if forced[k]:
                continue
            main = fig[k]
            chain = []
            j = k - 1
            while j >= 0 and not cols[j][1][0].grace:
                if forced[j]:
                    chain.append(j)
                    j -= 1
                    continue
                if never[j] or fig[j] < max(16, 4 * main):
                    break
                if figure_of_ms(starts[j + 1] - starts[j], quarter_ms, split) <= main:
                    break
                chain.append(j)
                j -= 1
            if chain and (len(chain) <= proposal.MAX_GRACES or any(forced[j] for j in chain)):
                for j in chain:
                    for n in cols[j][1]:
                        n.grace = "acc" if len(chain) == 1 else "unacc"
                        n.figure = 8 if len(chain) == 1 else 16
                        n.gslot = 0
                count += len(chain)
    return count


@contextmanager
def rule(name: str) -> Iterator[None]:
    """``old``: the rule before implementation 04; ``graces``: the new grace notes without the lengthening (the
    figure of each note by its own length); ``new``: today's code."""
    saved = (
        proposal.find_graces,
        proposal.lengthen_lone,
        llm_frames.find_graces,
        llm_frames.lengthen_lone,
    )
    if name == "old":
        proposal.find_graces = llm_frames.find_graces = old_find_graces
    if name in ("old", "graces"):
        proposal.lengthen_lone = llm_frames.lengthen_lone = lambda *args, **kwargs: 0
    try:
        yield
    finally:
        (
            proposal.find_graces,
            proposal.lengthen_lone,
            llm_frames.find_graces,
            llm_frames.lengthen_lone,
        ) = saved


def drawn(part: str, name: str) -> tuple[Sheet, float]:
    """The sheet of a part as the page draws it with a rule, and the seconds it took."""
    with rule(name):
        start = time.perf_counter()
        text = build._compute(part).text
        return f1.read(text), time.perf_counter() - start


# ------------------------------------------------------------------ comparing two sheets


def columns(sheet: Sheet) -> dict[tuple[int, int], list[Note]]:
    out: dict[tuple[int, int], list[Note]] = defaultdict(list)
    for n in sheet.notes:
        if not n.covered and n.staff in (1, 2):
            out[(n.staff, n.frame)].append(n)
    return out


def groups(sheet: Sheet) -> dict[tuple[int, int], frozenset[tuple[int, int]]]:
    """The beam group of each column, as the set of its columns."""
    members: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for n in sheet.notes:
        if n.beam is not None and not n.grace:
            members[(n.staff, n.beam)].add((n.staff, n.frame))
    return {c: frozenset(m) for m in members.values() for c in m}


STEP_NAMES = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}
FIGURE_NAMES = {**NAMES, None: "?"}


def name(n: Note) -> str:
    sign = "#" if n.alter > 0 else "-b" if n.alter < 0 else ""
    return f"{STEP_NAMES[n.step]}{sign} {n.octave}"


def clock(frame: int) -> str:
    seconds = frame * 0.04
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def compare(old: Sheet, graces: Sheet, new: Sheet) -> tuple[Counter, list[tuple[int, str]]]:
    """What the new rule changed, by kind, and one line per changed column ``(frame, text)``."""
    co, cg, cn = columns(old), columns(graces), columns(new)
    out: Counter = Counter()
    lines: list[tuple[int, str]] = []
    if set(co) != set(cn):
        out["columns differ"] += len(set(co) ^ set(cn))
    changed: set[tuple[int, int]] = set()
    for c in sorted(set(co) & set(cn), key=lambda c: (c[1], c[0])):
        hand = "right" if c[0] == 1 else "left"
        was, now, own = co[c][0], cn[c][0], cg[c][0]
        notes = " ".join(name(n) for n in sorted(cn[c], key=lambda n: n.midi))
        if was.grace and now.grace:
            out[f"grace {hand}: still a grace note"] += 1
            continue
        if now.grace:
            out["new grace notes"] += 1
            changed.add(c)
            lines.append((c[1], f"{clock(c[1])} {hand} hand {notes}: written, now a grace note"))
            continue
        if was.grace:
            changed.add(c)
            if now.figure != own.figure:
                out[f"grace {hand}: written longer"] += 1
                lines.append(
                    (
                        c[1],
                        f"{clock(c[1])} {hand} hand {notes}: grace note, now a {FIGURE_NAMES[now.figure]} "
                        f"(its own length: a {FIGURE_NAMES[own.figure]})",
                    )
                )
            else:
                out[f"grace {hand}: written, its own figure"] += 1
                lines.append(
                    (
                        c[1],
                        f"{clock(c[1])} {hand} hand {notes}: grace note, now a {FIGURE_NAMES[now.figure]}",
                    )
                )
            continue
        if now.figure != was.figure:
            changed.add(c)
            out[f"not a grace note: written longer ({hand})"] += 1
            lines.append(
                (
                    c[1],
                    f"{clock(c[1])} {hand} hand {notes}: a {FIGURE_NAMES[was.figure]}, now a "
                    f"{FIGURE_NAMES[now.figure]}",
                )
            )
    go, gn = groups(old), groups(new)
    for c in set(co) & set(cn):
        if c in changed or go.get(c) == gn.get(c):
            continue
        if not ((go.get(c) or frozenset()) | (gn.get(c) or frozenset())) & changed:
            out["beam groups changed elsewhere"] += 1
    by_note = {(n.frame, n.midi, n.staff): n for n in old.notes}
    for n in new.notes:
        o = by_note.get((n.frame, n.midi, n.staff))
        if o is None:
            out["notes moved"] += 1
        elif (o.ottava, o.step, o.alter, o.finger, o.fixed, o.grace_rule, o.ornaments) != (
            n.ottava,
            n.step,
            n.alter,
            n.finger,
            n.fixed,
            n.grace_rule,
            n.ornaments,
        ):
            out["8va, spelling or marks changed"] += 1
    if (old.clefs, sorted(old.clef_changes)) != (new.clefs, sorted(new.clef_changes)):
        out["clefs changed"] += 1
    if (old.key, sorted(old.key_changes)) != (new.key, sorted(new.key_changes)):
        out["armaduras changed"] += 1
    return out, lines


# ------------------------------------------------------------------ the study


def parts(layers: set[str]) -> Iterator[tuple[str, str, bool]]:
    for part in bundle.list_parts():
        try:
            where = locate.part(part)
            title = bundle.read_project(where.project_id).title
        except (locate.NotFound, OSError):
            continue
        if where.layer not in layers:
            continue
        kept = store.load(part)
        yield part, title, kept is not None


def study(layers: set[str]) -> None:
    total: Counter = Counter()
    times: list[tuple[float, float]] = []
    print(
        "| Song | Sheet | Grace notes, old (R / L) | Still grace notes | Written, own figure | Written longer "
        "| Others written longer | Grace notes, new | Anything else |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for part, title, stored in parts(layers):
        try:
            old, t_old = drawn(part, "old")
        except FileNotFoundError:
            continue
        graces, _ = drawn(part, "graces")
        new, t_new = drawn(part, "new")
        if stored:
            times.append((t_old, t_new))
        counts, _ = compare(old, graces, new)
        counts["old right"] = sum(
            1 for (st, _), ns in columns(old).items() if st == 1 and ns[0].grace
        )
        counts["old left"] = sum(
            1 for (st, _), ns in columns(old).items() if st == 2 and ns[0].grace
        )
        counts["new graces"] = sum(1 for ns in columns(new).values() if ns[0].grace)
        total.update(counts)
        still = counts["grace right: still a grace note"] + counts["grace left: still a grace note"]
        own = (
            counts["grace right: written, its own figure"]
            + counts["grace left: written, its own figure"]
        )
        longer = counts["grace right: written longer"] + counts["grace left: written longer"]
        others = (
            counts["not a grace note: written longer (right)"]
            + counts["not a grace note: written longer (left)"]
        )
        rest = {
            k: v
            for k, v in counts.items()
            if not k.startswith(("grace ", "not a grace", "old ", "new graces"))
        }
        print(
            f"| {title[:40]} | {'stored' if stored else 'algorithm'} | {counts['old right']} / "
            f"{counts['old left']} | {still} | {own} | {longer} | {others} | {counts['new graces']} | "
            f"{', '.join(f'{k} {v}' for k, v in rest.items()) or '-'} |"
        )
    print()
    for k, v in sorted(total.items()):
        print(f"{k}: {v}")
    if times:
        print(
            "one drawing of a stored sheet (s), old: "
            + ", ".join(f"{a:.2f}" for a, _ in times)
            + "; new: "
            + ", ".join(f"{b:.2f}" for _, b in times)
        )


# ------------------------------------------------------------------ the gallery

#: (part, first column, end column, title, what to look at)
CASES: list[tuple[str, int, int, str, str]] = [
    (
        SEVEN_YEARS,
        1802,
        2040,
        "The left hand of the image abuse-decoration-notes.png",
        "7 Years, the AI's sheet. Each short note of the left hand just before a blanca chord was a decoration "
        "note. It is a corchea now, two figures shorter than the blanca; before a negra chord it is a semicorchea "
        "(already two figures shorter, so its own figure). The right hand does not change.",
    ),
    (
        SEVEN_YEARS,
        2180,
        2303,
        "The right hand of the image abuse-decoration-notes-right.png",
        "7 Years, the AI's sheet. Fa 5 before the negra Do 5 and Si-b 4 before the chord were decoration notes: "
        "they are semicorcheas now, part of the melody. The short notes of the left hand before their chords too.",
    ),
    (
        "c0edc9b0-cd26-41a4-b53e-de8de001c470",
        1800,
        2070,
        "Fusas stay decoration notes, semicorcheas are written",
        "Moonlight Shadow, the AI's sheet. The decoration notes that are fusas or shorter stay. The ones that were "
        "semicorcheas are written now, as semicorcheas.",
    ),
    (
        "c0edc9b0-cd26-41a4-b53e-de8de001c470",
        340,
        420,
        "A run of fast notes before a negra stays as it is",
        "Moonlight Shadow. Semicorcheas, then a semifusa and a fusa, then a negra: a run of three or more fast "
        "notes stays written with its own figures, and its last notes are not written longer.",
    ),
    (
        "b80e6f5a-e027-4a40-a7b4-cb3c5a87ba68",
        1700,
        2140,
        "A left hand with a short note before each negra",
        "Birds of a Feather, the AI's sheet. The left hand plays a short note just before most negras. These "
        "were all decoration notes; now they are written semicorcheas. Before a blanca, a corchea.",
    ),
    (
        "92255337-9895-40a7-aa12-3b9cc81916ec",
        1240,
        1480,
        "Two corcheas before a redonda become two negras",
        "The One That Got Away, the AI's sheet. The right hand plays Sol# 4 and Fa# 4 as two corcheas, then a "
        "redonda chord. A corchea is three figures shorter than a redonda, so both are written as negras (the "
        "table of the rule: corchea before a redonda, a negra); Re# 4 before the next redonda too. The space "
        "between the notes still shows they are quick.",
    ),
    (
        "b2db46eb-b4c7-4f70-b203-1fe02f4c847d",
        330,
        530,
        "A semicorchea before a redonda becomes a negra",
        "99 Red Balloons, the algorithm's sheet. A short note just before a long one is written two figures "
        "shorter than it: before a redonda, a negra.",
    ),
    (
        "f285e4b7-ac53-480c-b1dc-fcee208c016e",
        1080,
        1330,
        "The algorithm's sheet: decoration notes that stay and ones that go",
        "Can't Stop the Feeling, the algorithm's sheet. The slashed decoration notes that stay are fusas or "
        "shorter. The left hand's pair before Do 3 (about 0:46) was two small decoration notes; it is two written "
        "semicorcheas now, with one beam.",
    ),
    (
        "f73116dd-1d88-4856-8f3e-63bbd4f5f7cb",
        3860,
        3960,
        "A beam group next to a written note",
        "2002, the algorithm's sheet. A note that was a decoration note is written now, so the beam groups "
        "around it are made again by the beam rules: the group before it gives its last note to the next group.",
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


def gallery(out: Path) -> list[str]:
    opts = engine.Options(width=110)
    cache: dict[str, tuple[str, Sheet, Sheet, Sheet]] = {}
    items: list[str] = []
    index: list[str] = []
    problems: list[str] = []
    for no, (part, a, b, title, look) in enumerate(CASES, start=1):
        if part not in cache:
            where = locate.part(part)
            song = bundle.read_project(where.project_id).title
            cache[part] = (
                song,
                drawn(part, "old")[0],
                drawn(part, "graces")[0],
                drawn(part, "new")[0],
            )
        song, old, graces, new = cache[part]
        known = set(frames.check(old))
        broken = [p for p in frames.check(new) if p not in known]
        if broken:
            problems.append(f"{no}. {title}: {broken[:2]}")
        _, lines = compare(old, graces, new)
        listed = [text for frame, text in lines if a <= frame < b]
        changes = (
            '<ul class="changes">' + "".join(f"<li>{html.escape(t)}</li>" for t in listed) + "</ul>"
            if listed
            else '<p class="changes">No column of the passage changed.</p>'
        )
        anchor = f"c{no}"
        index.append(f'<li><a href="#{anchor}">{no}. {html.escape(title)}</a></li>')
        items.append(
            f'<section id="{anchor}"><h3>{no}. {html.escape(title)}</h3>'
            f'<p class="song">{html.escape(song)}, {clock(a)} to {clock(b)}</p>'
            f'<p class="look">{html.escape(look)}</p>'
            + _figure(
                "Before: the old rule",
                banded(engine.render_frames(old, opts, segment=(a, b)), a, b),
            )
            + _figure(
                "Now: the new rule", banded(engine.render_frames(new, opts, segment=(a, b)), a, b)
            )
            + f"<details><summary>What changed in the passage (from the data)</summary>{changes}</details>"
            + "</section>"
        )
    page = PAGE.replace("{{INDEX}}", "".join(index)).replace("{{SECTIONS}}", "".join(items))
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    return problems


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decoration notes: Phase 2 gallery</title>
<style>
:root { color-scheme: only light; --ink: #1d1d1f; --soft: #5f6368; --line: #e3e3e6; }
body { margin: 0; background: #fff; color: var(--ink); font: 15px/1.5 system-ui, sans-serif; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin: 0 0 8px; } h3 { font-size: 16px; margin: 36px 0 2px; }
.song { margin: 0; color: var(--soft); font-size: 13px; } .look { margin: 4px 0; max-width: 980px; }
figure { margin: 8px 0 12px; } figcaption { font-size: 13px; color: var(--soft); margin-bottom: 4px; }
.svg { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.svg svg { display: block; max-width: none; } ol { columns: 2; font-size: 14px; }
details { font-size: 13px; color: var(--soft); } .changes { margin: 4px 0; }
</style></head><body><main>
<h1>Decoration notes: the new rule</h1>
<p>Implementation 04, Phase 2. Only a fusa or shorter (one or two of them) just before a note at least two figures
longer is a decoration note now. Any other lone short note just before a much longer note is written as a real note,
two figures shorter than that note (a semicorchea before a blanca is a corchea). A run of three or more fast notes
stays as it was. Each case shows a passage drawn with the old rule and with the new one, as the page draws it; the
band marks the passage. Nothing else of the sheet changes.</p>
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
    parser.add_argument("--out", type=Path, help="the folder of the gallery's index.html")
    args = parser.parse_args()
    if args.study:
        study(set(args.layers.split(",")))
    if args.out:
        problems = gallery(args.out)
        for problem in problems:
            print("rule broken:", problem)
        print(
            f"{len(CASES)} cases, {len(problems)} with a broken rule -> {args.out / 'index.html'}"
        )


if __name__ == "__main__":
    main()
