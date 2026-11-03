"""The clef rule of implementation 04-7: the study of My library and the gallery, old rule and new.

The old rule (the clef rules version 4, implementation 03): the cheapest path over the columns of each hand, three
states a hand (right: treble, treble with 8va, bass; left: bass, treble, treble with 8va), never 8va in the bass clef,
a left-hand note four ledger lines or more above the bass staff forces the treble clef, no shortest stretch. The new
rule (the user's, 2026-11-03, plan section 4.1 of ``context/implementations/04-app-enhancements/04-7-plan.md``): a
hand changes to its other clef only for a whole passage, ``CLEF_MIN`` (5) of its columns or more; a shorter stretch
stays in the hand's own clef, with ledger lines and an octave line (left 8va in the bass clef, right 8vb in the treble
clef) for the notes too far for them; a clef the user set by hand stays. This script keeps a copy of the old rule
(:func:`rule`) to draw the sheets as they were.

* ``--study``: for every part of My library (``private``; ``--layers`` for others), drawn as the page draws it
  (``part_sheet.build._compute``) with the old rule and the new one: the clef changes of each hand, the notes under
  8va and 8vb of each hand, the short stretches of the other clef (1 to 4 columns) before and after, the short
  stretches the new rule took away or kept, the seconds of one drawing, and the check that nothing but clefs and
  octave lines changed (every other field of every note and of the sheet). Then the stretches of the left hand's
  treble clef by length, old rule (plan section 3.3), and the parts with clefs set by hand, by name.
* ``--out DIR``: the gallery, ``DIR/index.html``: each case a passage drawn with the old rule and with the new one
  (the app's engraver), one sentence on what to look at, and the list of the columns that changed, from the data.

Nothing is written to the database: the sheets are computed, never stored. In the backend container::

    docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/clef_study.py --study
    docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/clef_study.py \\
        --out ../context/implementations/04-app-enhancements/gallery/04-7
"""

from __future__ import annotations

import argparse
import html
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Iterator

from aitu_backend.part_sheet import build, edits, store
from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.llm import frames as llm_frames
from aitu_backend.sheet.proposal import frames as proposal
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.storage import bundle, locate

# ------------------------------------------------------------------ the old rule

OLD_STATES = {
    1: [("G2", 0, 0.0), ("G2", 1, proposal.OTTAVA_COST), ("F4", 0, proposal.CLEF_PREFER)],
    2: [
        ("F4", 0, 0.0),
        ("G2", 0, proposal.CLEF_PREFER),
        ("G2", 1, proposal.CLEF_PREFER + proposal.OTTAVA_COST),
    ],
}


def old_fits(below_above: list[tuple[int, int]], staff: int, ottava: int) -> bool:
    """The limit of the old rule: only the left hand in the bass clef, no note four ledger lines above the staff."""
    return not (staff == 2 and max(a for _, a in below_above) >= proposal.BASS_LIMIT)


def no_short_clefs(sheet: Sheet) -> dict:
    return {
        "short clef stretches": 0,
        "short stretches kept": 0,
        "notes under a new line": 0,
        "grace lines matched": 0,
    }


#: The counts of the last ``short_clefs`` of a drawing (the one on the sheet the page draws).
LAST: dict = {}


def counted_short_clefs(sheet: Sheet) -> dict:
    info = SHORT_CLEFS(sheet)
    LAST.clear()
    LAST.update(info)
    return info


SHORT_CLEFS = proposal.short_clefs


@contextmanager
def rule(name: str) -> Iterator[None]:
    """``old``: the clef rules before 04-7; ``new``: today's code (with the counts of :data:`LAST`)."""
    saved = (
        proposal.STATES,
        proposal._fits,
        proposal.short_clefs,
        build.short_clefs,
        edits.short_clefs,
        llm_frames.OTTAVA_LOWEST,
    )
    short = no_short_clefs if name == "old" else counted_short_clefs
    if name == "old":
        proposal.STATES, proposal._fits = OLD_STATES, old_fits
        llm_frames.OTTAVA_LOWEST = {"G2": 72}
    proposal.short_clefs = build.short_clefs = edits.short_clefs = short
    LAST.clear()
    try:
        yield
    finally:
        (
            proposal.STATES,
            proposal._fits,
            proposal.short_clefs,
            build.short_clefs,
            edits.short_clefs,
            llm_frames.OTTAVA_LOWEST,
        ) = saved


@dataclass
class Drawing:
    sheet: Sheet
    seconds: float
    source: str
    short: dict


def drawn(part: str, name: str) -> Drawing:
    """The sheet of a part as the page draws it with a rule, the seconds it took, and the counts of the step."""
    with rule(name):
        start = time.perf_counter()
        d = build._compute(part)
        seconds = time.perf_counter() - start
        return Drawing(f1.read(d.text), seconds, d.source, dict(LAST))


# ------------------------------------------------------------------ reading a sheet

HANDS = {1: "right", 2: "left"}
OWN = {1: "G2", 2: "F4"}
CLEF_WORD = {"G2": "treble", "F4": "bass"}


def columns(sheet: Sheet, staff: int) -> list[tuple[int, list[Note]]]:
    cols: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        if n.staff == staff and not n.covered:
            cols[n.frame].append(n)
    return sorted(cols.items())


def track(sheet: Sheet, staff: int) -> list[tuple[int, str, list[Note]]]:
    """Each column of a hand with the clef in force there."""
    cols = columns(sheet, staff)
    clefs = proposal._track(sheet, staff, [f for f, _ in cols])
    return [(f, c, ns) for (f, ns), c in zip(cols, clefs)]


@dataclass
class Stretch:
    staff: int
    first: int  # frame of its first column
    last: int  # frame of its last column
    main: int  # columns that are not grace notes
    columns: int
    high: bool  # left: a note B4 or higher; right: a note D3 or lower


def stretches(sheet: Sheet, staff: int) -> list[Stretch]:
    """The stretches of a hand in its other clef."""
    out: list[Stretch] = []
    cur: list[tuple[int, list[Note]]] = []
    for f, clef, ns in track(sheet, staff) + [(None, OWN[staff], [])]:
        if clef != OWN[staff] and f is not None:
            cur.append((f, ns))
            continue
        if cur:
            notes = [n for _, ns_ in cur for n in ns_]
            # a note written BASS_LIMIT ledger lines or more outside the own staff (left: Bb4 or B4 and higher;
            # right: D3 or lower), as plan section 3.3 counted
            side = 1 if staff == 2 else 0
            high = any(
                proposal._ledger(n, OWN[staff], 0)[side] >= proposal.BASS_LIMIT for n in notes
            )
            main = sum(1 for _, ns_ in cur if any(not n.grace for n in ns_))
            out.append(Stretch(staff, cur[0][0], cur[-1][0], main, len(cur), high))
            cur = []
    return out


def lines(sheet: Sheet, staff: int, sign: int) -> int:
    return sum(
        1
        for n in sheet.notes
        if n.staff == staff and not n.covered and (n.ottava > 0 if sign > 0 else n.ottava < 0)
    )


def changes(sheet: Sheet, staff: int) -> int:
    return sum(1 for _, st, _ in sheet.clef_changes if st == staff)


def graces_off(sheet: Sheet) -> int:
    """Grace columns whose octave line is not the one of their main column (the engraver draws them under the main
    column's line, so they read an octave off)."""
    out = 0
    for staff in (1, 2):
        cols = columns(sheet, staff)
        for i, (_, ns) in enumerate(cols):
            if not all(n.grace for n in ns):
                continue
            j = i + 1
            while j < len(cols) and all(n.grace for n in cols[j][1]):
                j += 1
            if j < len(cols) and any(n.ottava != cols[j][1][0].ottava for n in ns):
                out += 1
    return out


NOTE_SKIP = {"ottava"}
SHEET_SKIP = {"notes", "clefs", "clef_changes"}


def others(old: Sheet, new: Sheet) -> Counter:
    """What changed besides the clefs and the octave lines: should be nothing. One thing follows from a line: a
    grace column with two lines inside it is stored as two grace slots (F1 writes one line a token), so when its
    notes take one line (``proposal.frames._grace_lines``) their ``gslot`` may change; only there it is not
    counted (``gslot of a grace chord split by its lines`` counts those notes)."""
    out: Counter = Counter()
    split: set[tuple[int, int]] = set()
    lines: dict[tuple[int, int], set[int]] = defaultdict(set)
    for n in old.notes:
        if n.grace and not n.covered:
            lines[(n.frame, n.staff)].add(n.ottava)
    split = {c for c, o in lines.items() if len(o) > 1}

    def key(n: Note) -> tuple:
        return (n.frame, n.staff, n.midi, n.covered, n.eid or "", n.gslot)

    a, b = sorted(old.notes, key=key), sorted(new.notes, key=key)
    if len(a) != len(b):
        out["notes count"] += abs(len(a) - len(b))
    for x, y in zip(a, b):
        skip = NOTE_SKIP | ({"gslot"} if (x.frame, x.staff) in split else set())
        if (x.frame, x.staff) in split and x.gslot != y.gslot:
            out["gslot of a grace chord split by its lines"] += 1
        dx = {k: v for k, v in asdict(x).items() if k not in skip}
        dy = {k: v for k, v in asdict(y).items() if k not in skip}
        if dx != dy:
            for k in dx:
                if dx[k] != dy.get(k):
                    out[f"note {k}"] += 1
    for f in fields(Sheet):
        if f.name not in SHEET_SKIP and getattr(old, f.name) != getattr(new, f.name):
            out[f"sheet {f.name}"] += 1
    return out


def kind(d: Drawing, part: str) -> str:
    record = store.load(part)
    if record is None or d.source == "algorithm":
        return "rule"
    r = record.record
    if r.source == "mixed" or r.levels:
        return "level"
    if r.source == "llm":
        return f"AI p{r.prompt or '?'}"
    return "edited" if r.edited else r.source


# ------------------------------------------------------------------ the study


def parts(layers: set[str]) -> Iterator[tuple[str, str]]:
    for part in bundle.list_parts():
        try:
            where = locate.part(part)
            title = bundle.read_project(where.project_id).title
        except (locate.NotFound, OSError):
            continue
        if where.layer in layers:
            yield part, title


#: The parts with clefs set by hand before the mark (plan section 3.3), and what Phase 2 read in their undo logs.
BY_HAND = {
    "c33860b5": "My Way: the right hand's own clef (treble) set twice",
    "946c21f2": "20 de enero, a level copy: the left hand's own clef (bass) set",
    "7b9a41e4": "20 de enero, a level copy: the treble clef for the left hand at f1998, 6 columns",
}


def study(layers: set[str]) -> None:
    total: Counter = Counter()
    lengths: dict[str, Counter] = defaultdict(Counter)
    times: list[tuple[str, float, float]] = []
    print(
        "| Song | Part | Sheet | Clef changes R / L, old -> new | 8va R / L, old -> new | 8vb R / L, new "
        "| Short stretches R / L, old -> new | Taken away / kept | s old / new | Anything else |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    count = 0
    for part, title in parts(layers):
        try:
            drawn(part, "old")  # a first drawing warms the caches of the notes, so the two times compare
        except FileNotFoundError:
            continue
        old = drawn(part, "old")
        new = drawn(part, "new")
        count += 1
        k = kind(new, part)
        total[f"sheets {k}"] += 1
        so, sn = old.sheet, new.sheet
        st = {
            (w, s): [x for x in stretches(d, s) if x.main < proposal.CLEF_MIN]
            for w, d in (("old", so), ("new", sn))
            for s in (1, 2)
        }
        for x in stretches(so, 2):
            group = "rule" if k == "rule" else "AI" if k.startswith("AI") else k
            size = x.columns
            band = "1-2" if size <= 2 else "3-4" if size <= 4 else "5-8" if size <= 8 else "9+"
            lengths[group][band] += 1
            lengths[group]["all"] += 1
            if size <= 4 and x.high:
                lengths[group]["1-4 with B4 or higher"] += 1
            mb = (
                "1-2"
                if x.main <= 2
                else "3-4" if x.main <= 4 else "5-8" if x.main <= 8 else "9+"
            )
            lengths[group][f"main {mb}"] += 1
        rest = others(so, sn)
        row = {
            "cc": (changes(so, 1), changes(so, 2), changes(sn, 1), changes(sn, 2)),
            "va": (lines(so, 1, 1), lines(so, 2, 1), lines(sn, 1, 1), lines(sn, 2, 1)),
            "vb": (lines(sn, 1, -1), lines(sn, 2, -1)),
            "sh": (
                len(st[("old", 1)]),
                len(st[("old", 2)]),
                len(st[("new", 1)]),
                len(st[("new", 2)]),
            ),
        }
        total["clef changes R old"] += row["cc"][0]
        total["clef changes L old"] += row["cc"][1]
        total["clef changes R new"] += row["cc"][2]
        total["clef changes L new"] += row["cc"][3]
        total["8va R old"] += row["va"][0]
        total["8va L old"] += row["va"][1]
        total["8va R new"] += row["va"][2]
        total["8va L new"] += row["va"][3]
        total["8vb R new"] += row["vb"][0]
        total["8vb L new"] += row["vb"][1]
        total["short R old"] += row["sh"][0]
        total["short L old"] += row["sh"][1]
        total["short R new"] += row["sh"][2]
        total["short L new"] += row["sh"][3]
        total["graces off their main line old"] += graces_off(so)
        total["graces off their main line new"] += graces_off(sn)
        total["grace lines matched"] += new.short.get("grace lines matched", 0)
        total["taken away"] += new.short.get("short clef stretches", 0)
        total["kept"] += new.short.get("short stretches kept", 0)
        total["notes under a new line"] += new.short.get("notes under a new line", 0)
        total.update({f"else: {k_}": v for k_, v in rest.items()})
        rest.pop("gslot of a grace chord split by its lines", None)
        known = set(frames.check(so))
        broken = [p for p in frames.check(sn) if p not in known]
        total["new problems of frames.check"] += len(broken)
        times.append((k, old.seconds, new.seconds))
        cc, va, vb, sh = row["cc"], row["va"], row["vb"], row["sh"]
        print(
            f"| {title[:34]} | {part[:8]} | {k} | {cc[0]} / {cc[1]} -> {cc[2]} / {cc[3]} "
            f"| {va[0]} / {va[1]} -> {va[2]} / {va[3]} | {vb[0]} / {vb[1]} "
            f"| {sh[0]} / {sh[1]} -> {sh[2]} / {sh[3]} "
            f"| {new.short.get('short clef stretches', 0)} / {new.short.get('short stretches kept', 0)} "
            f"| {old.seconds:.2f} / {new.seconds:.2f} "
            f"| {', '.join(f'{a} {b}' for a, b in rest.items()) or '-'}"
            f"{'; check: ' + '; '.join(broken[:2]) if broken else ''} |"
        )
    print()
    print(f"parts: {count}")
    for k_, v in sorted(total.items()):
        print(f"{k_}: {v}")
    print()
    print("The left hand's treble stretches, old rule, by columns (all; 'main': without grace columns):")
    for group, c in lengths.items():
        print(f"  {group}: " + ", ".join(f"{a} {b}" for a, b in sorted(c.items())))
    print()
    print("The parts with clefs set by hand (any layer):")
    ids = {p[:8]: p for p in bundle.list_parts()}
    for short, what in BY_HAND.items():
        part = ids.get(short)
        if part is None:
            print(f"- {short}: not found")
            continue
        title = bundle.read_project(locate.part(part).project_id).title
        old, new = drawn(part, "old").sheet, drawn(part, "new").sheet
        moved = changed_columns(old, new)
        kept = [
            f"{HANDS[x.staff]} hand {CLEF_WORD[OTHER_OF[x.staff]]} clef f{x.first}-f{x.last} ({x.main} columns)"
            for st in (1, 2)
            for x in stretches(new, st)
            if x.first <= 2033 and x.last >= 1998 or short != "7b9a41e4"
        ]
        print(
            f"- {short} {title} ({locate.part(part).layer}): {what}. Columns whose clef or line changed: "
            f"{len(moved)}; anything else: {dict(others(old, new)) or 'nothing'}; stretches of the other clef "
            f"now{' (near f1998)' if short == '7b9a41e4' else ''}: {'; '.join(kept) or 'none'}"
        )
    print()
    for group in sorted({k_ for k_, _, _ in times}):
        olds = [a for k_, a, _ in times if k_ == group]
        news = [b for k_, _, b in times if k_ == group]
        print(
            f"seconds of one drawing, {group}: old {min(olds):.2f} to {max(olds):.2f} "
            f"(mean {sum(olds) / len(olds):.2f}); new {min(news):.2f} to {max(news):.2f} "
            f"(mean {sum(news) / len(news):.2f})"
        )


OTHER_OF = {1: "F4", 2: "G2"}


# ------------------------------------------------------------------ the gallery


def changed_columns(old: Sheet, new: Sheet) -> list[tuple[int, int, str]]:
    """Each column whose clef or octave line changed: ``(frame, staff, text)``, read from the data."""
    out = []
    for staff in (1, 2):
        to = {f: (c, ns) for f, c, ns in track(old, staff)}
        tn = {f: (c, ns) for f, c, ns in track(new, staff)}
        for f in sorted(set(to) & set(tn)):
            (co, no), (cn, nn) = to[f], tn[f]
            lo = sorted({n.ottava for n in no})
            ln = sorted({n.ottava for n in nn})
            if co == cn and lo == ln:
                continue
            notes = " ".join(spn(n) for n in sorted(nn, key=lambda n: n.midi))
            out.append(
                (
                    f,
                    staff,
                    f"{clock(f)} f{f} {HANDS[staff]} hand {notes}: {describe(co, lo)} -> {describe(cn, ln)}",
                )
            )
    return sorted(out)


def describe(clef: str, ottavas: list[int]) -> str:
    line = {1: " 8va", -1: " 8vb", 2: " 15ma", -2: " 15mb", 0: ""}
    return CLEF_WORD[clef] + "".join(line[o] for o in ottavas)


def spn(n: Note) -> str:
    sign = "#" if n.alter > 0 else "b" if n.alter < 0 else ""
    return f"{n.step}{sign}{n.octave}"


def clock(frame: int) -> str:
    seconds = frame * 0.04
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def regions(
    cols: list[tuple[int, int, str]], gap: int = 150
) -> list[tuple[int, int, list[tuple[int, int, str]]]]:
    """The changed columns grouped into passages (``gap`` frames apart at most)."""
    out: list[tuple[int, int, list[tuple[int, int, str]]]] = []
    for c in cols:
        if out and c[0] - out[-1][1] <= gap:
            a, _, items = out[-1]
            out[-1] = (a, c[0], items + [c])
        else:
            out.append((c[0], c[0], [c]))
    return out


SUPERESTRELLA_AI = "f4c4de9a-b52a-490f-bb3a-0a4baaf6816b"
DIE_YOUNG = "e578f3c0-d4c1-4353-b80e-8b745b786597"

#: (part, first column, end column, title, what to look at), chosen from the study (the Phase 3 report)
CASES: list[tuple[str, int, int, str, str]] = [
    (
        SUPERESTRELLA_AI,
        30,
        330,
        "The AI's sheet: high chords of the left hand",
        "Superestrella, the AI's sheet (the sheet that changes most). The AI wrote the left hand's chords F#4 A#4 "
        "C#5 and F#4 B4 D#5 in the treble clef, one to four at a time, with a clef change before and after each. "
        "Now the left hand stays in the bass clef: each chord is under an 8va line, written an octave lower, "
        "inside the staff.",
    ),
    (
        SUPERESTRELLA_AI,
        1520,
        1780,
        "One 8va line over several columns",
        "Superestrella, the AI's sheet. Where two marked columns are close, the columns between them go under the "
        "same line when they stay readable there (G#3 is written G#2, on the staff): one line instead of many "
        "short ones. At its end, the small grace chord B4 D#5 and its note F#4 are under the line together.",
    ),
    (
        "43faf78e-1fb3-4edb-9f41-85072cbbe999",
        1650,
        1860,
        "The AI's sheet: single high notes",
        "Halleluyah, the AI's sheet. The left hand's single C5 and A4 notes were each in the treble clef. Now they "
        "stay in the bass clef: A4 with three ledger lines, C5 under 8va.",
    ),
    (
        "a585f9eb-36a1-49a0-9f0c-2626f3d292da",
        100,
        300,
        "A sheet never enhanced: lone high notes and a chord",
        "Superestrella, the sheet of the rule (never enhanced). Lone B4 and D#5 notes and the chord F#3 B3 D#4 B4 "
        "of the left hand stay in the bass clef under 8va.",
    ),
    (
        DIE_YOUNG,
        4900,
        5000,
        "A wide chord under the 8va line",
        "Die Young, the sheet of the rule. The left hand's chord B2 E3 B4 G#5 fits under the line: B2 is written "
        "B1, two ledger lines below the bass staff, G#5 is written G#4, three above.",
    ),
    (
        DIE_YOUNG,
        40,
        160,
        "The right hand: a short low stretch in the treble clef under 8vb",
        "Die Young, the sheet of the rule. The right hand had four columns in the bass clef (G#3, B2, C#3, C#3 "
        "G#3). Now they stay in the treble clef: G#3 with ledger lines, the others under an 8vb line (written an "
        "octave higher).",
    ),
    (
        "e3d7c376-5767-4243-aea8-1b5a8f8bd88f",
        3900,
        4000,
        "The right hand: a low passage of 6 columns takes the bass clef",
        "What Makes You Beautiful, the sheet of the rule. Six right-hand columns down to C#3: a whole passage, so "
        "the right hand changes to the bass clef for them, where before it read four ledger lines below the "
        "treble staff.",
    ),
    (
        "bef90052-3c70-4998-bfe9-49ec5369ae89",
        4860,
        4960,
        "No change: notes too high even for the 8va line",
        "Bonfire Heart, the sheet of the rule. Three left-hand C6 notes would stand four ledger lines above the bass "
        "staff even under 8va, so this short treble stretch stays as it was (the study counts it as kept).",
    ),
    (
        "7b9a41e4-738d-4d9f-8ded-fef406ebbd5d",
        1790,
        2045,
        "Your treble clef stays; a short one goes",
        "20 de enero, your level copy (Personal Vault). You set the treble clef for the left hand at 1:19.92 by "
        "hand: a stretch of 6 columns, which stays. Before it, a stretch of four low notes (C3, E3, A3, E3) was in "
        "the treble clef; it goes back to the bass clef.",
    ),
    (
        "946c21f2-883c-4678-8710-c4e5145f6f9f",
        1870,
        2045,
        "No change: passages of 5 and 6 columns keep the treble clef",
        "20 de enero, another level copy (Personal Vault). The left hand's two treble stretches have 5 and 6 "
        "columns: whole passages, so they keep the treble clef.",
    ),
    (
        "56543911-f14e-4936-92e4-ed1bdd278c54",
        3030,
        3110,
        "Both hands in one place",
        "Grace Kelly, the sheet of the rule. The right hand's G2 G3 was in the bass clef: now the treble clef under "
        "8vb. The left hand's chord F#4 B4 D5 F#5 was in the treble clef: now the bass clef under 8va.",
    ),
]


def banded(r: engine.Rendered, spans: list[tuple[int, int]]) -> str:
    """The SVG of a render with a light band behind the changed columns ``spans`` on each of its systems."""
    bands = []
    for box in r.systems:
        for a, b in spans:
            xs = [c["x"] for c in r.columns if c["system"] == box["index"] and a <= c["frame"] <= b]
            if xs:
                x0, x1 = min(xs) - 1.5, max(xs) + 2.5
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


def find(part: str, around: int | None = None) -> None:
    """Print the changed passages of one part (to choose the cases)."""
    old, new = drawn(part, "old").sheet, drawn(part, "new").sheet
    for a, b, items in regions(changed_columns(old, new)):
        if around is not None and not (a - 400 <= around <= b + 400):
            continue
        print(f"--- f{a} to f{b} ({clock(a)} to {clock(b)}), {len(items)} columns")
        for _, _, text in items[:14]:
            print("   ", text)


def gallery(out: Path, width: float) -> list[str]:
    opts = engine.Options(width=width)
    cache: dict[str, tuple[str, Sheet, Sheet]] = {}
    items: list[str] = []
    index: list[str] = []
    problems: list[str] = []
    for no, (part, a, b, title, look) in enumerate(CASES, start=1):
        if part not in cache:
            where = locate.part(part)
            song = bundle.read_project(where.project_id).title
            cache[part] = (song, drawn(part, "old").sheet, drawn(part, "new").sheet)
        song, old, new = cache[part]
        known = set(frames.check(old))
        broken = [p for p in frames.check(new) if p not in known]
        if broken:
            problems.append(f"{no}. {title}: {broken[:2]}")
        rest = others(old, new)
        rest.pop("gslot of a grace chord split by its lines", None)
        if rest:
            problems.append(f"{no}. {title}: other changes {dict(rest)}")
        listed = [(f, st, t) for f, st, t in changed_columns(old, new) if a <= f < b]
        spans = [(f, f) for f, _, _ in listed]
        changes = (
            '<ul class="changes">'
            + "".join(f"<li>{html.escape(t)}</li>" for _, _, t in listed)
            + "</ul>"
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
                banded(engine.render_frames(old, opts, segment=(a, b)), spans),
            )
            + _figure(
                "Now: the new rule",
                banded(engine.render_frames(new, opts, segment=(a, b)), spans),
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
<title>The clef rule: 04-7 gallery</title>
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
<h1>The clef rule: a passage of 5 columns or more</h1>
<p>Implementation 04-7. A hand changes to its other clef only for a whole passage, 5 of its columns or more. A
shorter stretch stays in the hand's own clef: ledger lines, and an octave line for the notes too far for them (the
left hand: 8va over the bass clef; the right hand: 8vb under the treble clef). A clef set by hand stays. Each case
shows a passage drawn by the app with the old rule and with the new one; the yellow band marks the columns whose
clef or octave line changed. Nothing else of the sheet changes.</p>
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
    parser.add_argument("--find", help="print the changed passages of one part (its id)")
    parser.add_argument("--around", type=int, help="with --find: only the passages near this frame")
    parser.add_argument("--out", type=Path, help="the folder of the gallery's index.html")
    parser.add_argument("--width", type=float, default=110.0, help="the gallery's staff width")
    args = parser.parse_args()
    if args.study:
        study(set(args.layers.split(",")))
    if args.find:
        find(args.find, args.around)
    if args.out:
        problems = gallery(args.out, args.width)
        for problem in problems:
            print("problem:", problem)
        print(f"{len(CASES)} cases, {len(problems)} problems -> {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
