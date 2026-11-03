"""Copy this style, implementation 06, Phase 2 (plan section 4.3): the requests of the run, their checks, and the
marks the code copies. No storage here: ``part_sheet.job.start_style`` runs it and stores what it accepts.

The user edited a stretch by hand (the **reference**); the matcher (``sheet.style.match``) found the other places of
the song that play the same kind of passage (the **passages**), and the user ticked the ones to write again. The run:

1. **The check** (:func:`check_prompt`, :func:`read_check`): the first request. The AI reads the reference as the
   user wrote it and each passage as the sheet has it now, and answers one line per passage, ``keep`` or ``drop``,
   with a reason; it may move a passage's edges by at most ``EDGE_NEGRAS`` negras, never over the reference or
   another passage kept. At most ``MAX_CHECKS`` replies.
2. **The batches** (:func:`batch_prompt`, :func:`check_style`): one request per passage kept, in the order of the
   song. Each holds the user's words, the reference as written, the column map of the matcher and the shift, the
   passages written before in this run (the latest ``EARLIER_SHOWN``), the decided context, the target and the fixed
   hand, and the look-ahead. The AI writes the target the reference's way; it sets the figures; the notes it leaves
   out and adds are declared and limited by what the reference's way of writing needs (:func:`change_budget`); the
   melody of the right hand stays; the hard rules of every answer hold.
3. **The marks the code copies** (:func:`copy_marks`), on the sheet the job stores: the passage's own marks stay;
   a spelling set by hand goes to a note of the same pitch class at the matching column, moved by the shift; a
   finger and the decoration-note switch go to the same note; a clef set by hand goes to the matching stretch.

A conversation is a ``levels.Talk`` (the check is ``k`` -1, as the plan of a level run), so the history of the AI runs
keeps and shows it as a level run's.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Iterable

from aitu_backend.sheet.llm import frames
from aitu_backend.sheet.llm.frames import Complete, SkipWindow, WindowLog, _slice
from aitu_backend.sheet.llm.levels import Talk, _conversation, clock, read_declared, splice
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet

__all__ = [
    "EARLIER_SHOWN",
    "EDGE_NEGRAS",
    "MAX_CHECKS",
    "STYLE_VERSION",
    "Checked",
    "Passage",
    "StyleRun",
    "batch_prompt",
    "change_budget",
    "check_prompt",
    "check_style",
    "copy_marks",
    "read_check",
    "system_prompt",
    "write_again",
    "write_style",
]

PROMPT_DIR = Path(__file__).with_name("prompt") / "style"
STYLE_VERSION = (PROMPT_DIR / "VERSION").read_text(encoding="utf-8").strip()
MAX_CHECKS = 3
#: The check may move an edge of a passage by at most this many negras.
EDGE_NEGRAS = 2
#: The passages written before in the run that a batch sees, the latest ones.
EARLIER_SHOWN = 2
HANDS = {1: "right", 2: "left"}


def system_prompt() -> str:
    """The instructions of the whole run (the format, the hands, the beams, the clefs), then this run's, which
    override them where they differ (the figures, the notes changed)."""
    return frames.instructions().rstrip() + "\n\n" + (PROMPT_DIR / "instructions.md").read_text(encoding="utf-8")


def feedback(errors: list[str]) -> str:
    return (PROMPT_DIR / "feedback.md").read_text(encoding="utf-8").format(
        errors="\n".join(f"- {e}" for e in errors)
    )


def _who(staffs: tuple[int, ...]) -> str:
    return "both hands" if len(staffs) == 2 else f"the {HANDS[staffs[0]]} hand"


def _text(sheet: Sheet) -> str:
    return f1.write(sheet, mode="frames").strip()


def _shift_words(shift: int) -> str:
    if not shift:
        return "in the same key"
    return f"{abs(shift)} semitone{'s' if abs(shift) != 1 else ''} {'higher' if shift > 0 else 'lower'}"


@dataclass
class Passage:
    """A passage of the run: the matcher's place (``P{k + 1}``), its column map ``(staff, reference frame, passage
    frame)``, and the check's answer (kept or dropped, and why)."""

    k: int
    start: int
    end: int
    score: float = 0.0
    shift: int = 0
    columns: list[tuple[int, int, int]] = field(default_factory=list)
    keep: bool = True
    why: str = ""

    @property
    def name(self) -> str:
        return f"P{self.k + 1}"

    def to_json(self) -> dict:
        return {
            "k": self.k,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "shift": self.shift,
            "columns": [list(c) for c in self.columns],
            "keep": self.keep,
            "why": self.why,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Passage":
        return cls(
            k=int(data["k"]),
            start=int(data["start"]),
            end=int(data["end"]),
            score=float(data.get("score", 0.0)),
            shift=int(data.get("shift", 0)),
            columns=[tuple(int(x) for x in c) for c in data.get("columns", [])],
            keep=bool(data.get("keep", True)),
            why=str(data.get("why", "")),
        )


# ------------------------------------------------------------------ the check


def check_prompt(
    *,
    sid: str,
    sheet: Sheet,
    reference: tuple[int, int],
    passages: list[Passage],
    staffs: tuple[int, ...],
    words: str = "",
) -> str:
    """The first request of the run: the reference as the user wrote it, each passage as the sheet has it now (the
    hands rewritten), and how to answer."""
    a, b = reference
    q = (sheet.quarter_ms or 500.0) / FRAME_MS
    out = [f"# Copy this style, {_who(staffs)}, of song {sid}: the check of {len(passages)} passages"]
    if words.strip():
        out.append("## The user's words (of the utmost importance)\n\n" + words.strip())
    out.append(
        f"## The reference (f{a}-f{b}, {clock(a)}-{clock(b)}, {_who(staffs)}, as the user wrote it)\n\n```\n"
        + _text(_slice(sheet, a, b, staffs))
        + "\n```"
    )
    rows = []
    for p in passages:
        rows.append(
            f"### {p.name} f{p.start}-f{p.end} ({clock(p.start)}-{clock(p.end)}): similarity {p.score:.2f}, "
            f"{_shift_words(p.shift)}\n\n```\n" + _text(_slice(sheet, p.start, p.end, staffs)) + "\n```"
        )
    out.append("## The passages the app found (each as the sheet has it now)\n\n" + "\n\n".join(rows))
    out.append(
        "## Answer\n\nFor each passage, decide whether it is **the same kind of passage** as the reference: the same "
        "melody or the same accompaniment played again, with small changes (another note, another ending, more or "
        "less ornament, maybe in another key). Drop a passage that is another kind of passage (another melody, "
        "another section of the song), even when its rhythm is alike.\n\n"
        "Answer one block in triple backticks, one line per passage, in order, with a short reason after `|`:\n\n"
        "```\nP1 keep | the second chorus, the same melody\nP2 drop | the bridge: another melody\n```\n\n"
        f"A passage kept may get its frames when it really starts or ends a little earlier or later "
        f"(`P1 f1204-f1388 keep | ...`): each edge moves by at most {EDGE_NEGRAS} negras (about "
        f"{round(EDGE_NEGRAS * q)} frames), never over the reference (f{a}-f{b}) or another passage kept."
    )
    return "\n\n".join(out) + "\n"


_CHECK_LINE = re.compile(
    r"^\s*P(\d+)\s*(?:[:.]\s*)?(?:f(\d+)\s*-\s*f(\d+)\s+)?(keep|drop)\b\s*(?:[|:-]\s*(.*?))?\s*$",
    re.M | re.I,
)


def _fenced(reply: str) -> str:
    blocks = re.findall(r"```[a-zA-Z0-9_-]*[ \t]*\n(.*?)```", reply, re.S)
    return "\n".join(blocks) if blocks else reply


def read_check(
    reply: str,
    passages: list[Passage],
    *,
    reference: tuple[int, int],
    quarter_ms: float,
) -> tuple[list[str], list[Passage]]:
    """The problems of the check's answer (empty: accepted) and the passages with its decisions: every passage named
    once, ``keep`` or ``drop``; a kept passage's new frames within ``EDGE_NEGRAS`` negras of the matcher's, never over
    the reference or another kept passage."""
    by_k = {p.k: p for p in passages}
    seen: dict[int, Passage] = {}
    errs: list[str] = []
    edge = EDGE_NEGRAS * quarter_ms / FRAME_MS + 1
    for num, a, b, what, why in _CHECK_LINE.findall(_fenced(reply)):
        k = int(num) - 1
        if k not in by_k:
            errs.append(f"P{num} is not a passage of this check")
            continue
        if k in seen:
            errs.append(f"P{num} is answered twice")
            continue
        p = replace(by_k[k], keep=what.lower() == "keep", why=(why or "").strip())
        if a and b and p.keep:
            na, nb = int(a), int(b)
            if nb <= na:
                errs.append(f"P{num} f{na}-f{nb}: the end comes before the start")
            elif abs(na - p.start) > edge or abs(nb - p.end) > edge:
                errs.append(
                    f"P{num} f{na}-f{nb}: an edge moves more than {EDGE_NEGRAS} negras from f{p.start}-f{p.end}"
                )
            else:
                p.start, p.end = na, nb
        seen[k] = p
    for p in passages:
        if p.k not in seen:
            errs.append(f"{p.name} has no answer (write `{p.name} keep | why` or `{p.name} drop | why`)")
    kept = sorted((p for p in seen.values() if p.keep), key=lambda p: p.start)
    ra, rb = reference
    for p in kept:
        if p.start < rb and ra < p.end:
            errs.append(f"{p.name} f{p.start}-f{p.end} overlaps the reference f{ra}-f{rb}")
    for x, y in zip(kept, kept[1:]):
        if y.start < x.end:
            errs.append(f"{x.name} and {y.name} overlap (f{x.start}-f{x.end}, f{y.start}-f{y.end})")
    return errs, [seen.get(p.k, p) for p in passages]


# ------------------------------------------------------------------ a batch


def _column_map(passage: Passage, staffs: tuple[int, ...]) -> str:
    lines = []
    for st in staffs:
        pairs = [f"f{r}>f{t}" for s, r, t in passage.columns if s == st]
        if pairs:
            lines.append(f"{'R' if st == 1 else 'L'}: " + " ".join(pairs))
    return "\n".join(lines) or "(no column of the target matches one of the reference)"


def batch_prompt(
    *,
    sid: str,
    index: int,
    count: int,
    sheet: Sheet,
    reference: tuple[int, int],
    passage: Passage,
    staffs: tuple[int, ...],
    target: Sheet,
    fixed: Sheet | None,
    earlier: list[tuple[Passage, Sheet]] = (),
    context: Sheet | None = None,
    lookahead: Sheet | None = None,
    words: str = "",
) -> str:
    """The request of the passage ``index`` (0 = first) of the ``count`` passages kept."""
    a, b = passage.start, passage.end
    ra, rb = reference
    who = _who(staffs)
    out = [
        f"# Copy this style, {who}, of song {sid}: passage {index + 1} of {count} ({passage.name}, f{a}-f{b}, "
        f"{clock(a)}-{clock(b)})"
    ]
    if words.strip():
        out.append("## The user's words (of the utmost importance)\n\n" + words.strip())
    both = (
        ""
        if len(staffs) == 2
        else f" Both hands are shown; only the {HANDS[staffs[0]]} hand is copied, the other one stays as it is."
    )
    out.append(
        f"## The reference (f{ra}-f{rb}, as the user wrote it: write the target the same way)\n\n```\n"
        + _text(_slice(sheet, ra, rb, (1, 2)))
        + f"\n```\n\nIts figures, note names, chord shapes, beam groups, clefs and 8va lines, decoration notes and "
        f"ornaments are the way of writing to copy.{both}"
    )
    out.append(
        "## The column map (reference > target: the same place of the passage)\n\n"
        + _column_map(passage, staffs)
        + f"\n\nThe target plays the reference {_shift_words(passage.shift)}."
    )
    shown = list(earlier)[-EARLIER_SHOWN:]
    if shown:
        out.append(
            "## The passages written before in this run (as you wrote them)\n\n"
            + "\n\n".join(
                f"### {p.name} f{p.start}-f{p.end}\n\n```\n" + _text(s) + "\n```" for p, s in shown if s.notes
            )
        )
    if context is not None and context.notes:
        out.append("## Decided context (the sheet just before the passage)\n\n```\n" + _text(context) + "\n```")
    out.append(
        f"## Target ({who} as the sheet has {'them' if len(staffs) == 2 else 'it'} now: write "
        f"{'them' if len(staffs) == 2 else 'it'} again the reference's way)\n\n```\n" + _text(target) + "\n```"
    )
    if fixed is not None and fixed.notes:
        other = HANDS[3 - staffs[0]]
        out.append(
            f"## The {other} hand (fixed: it stays exactly as it is; do not write it)\n\n```\n" + _text(fixed) + "\n```"
        )
    if lookahead is not None and lookahead.notes:
        out.append(
            "## Look-ahead (the next notes as they are now; do not write them)\n\n```\n" + _text(lookahead) + "\n```"
        )
    out.append(
        "## Answer\n\nOne block in triple backticks: the two header lines of the target, the note lines of "
        f"f{a}-f{b - 1} ({who} only), the `# leave out` and `# add` lines of the notes you change, and one or two "
        "`# explain:` lines for the user (what you copied from the reference, and what you kept of the passage)."
    )
    return "\n\n".join(out) + "\n"


@dataclass
class Checked:
    """What :func:`check_style` found in one answer."""

    errors: list[str]
    sheet: Sheet | None = None
    left: Counter = field(default_factory=Counter)
    added: Counter = field(default_factory=Counter)
    explain: list[str] = field(default_factory=list)

    def declared(self) -> list[str]:
        return [f"leave out f{f} {frames._name(m)}" for f, m in sorted(self.left.elements())] + [
            f"add f{f} {frames._name(m)}" for f, m in sorted(self.added.elements())
        ]


def _columns(notes: Iterable[Note], staff: int) -> dict[int, list[Note]]:
    out: dict[int, list[Note]] = defaultdict(list)
    for n in notes:
        if n.staff == staff and not n.covered:
            out[n.frame].append(n)
    return out


def change_budget(target: Sheet, reference: Sheet, passage: Passage, staffs: tuple[int, ...]) -> int:
    """How many notes the answer may leave out and add in all: a tenth of the target (``frames.CHANGE_MIN`` at
    least), plus what the reference's way of writing asks for at the matching columns: the notes a target column has
    more than its reference column, the notes of a target column with no reference column, and the notes of a
    reference column with no target column (the reference plays there, the target not)."""
    most = max(frames.CHANGE_MIN, int(frames.CHANGE_SHARE * len(target.notes)))
    for st in staffs:
        mine = _columns(target.notes, st)
        ref = _columns(reference.notes, st)
        to_ref = {t: r for s, r, t in passage.columns if s == st}
        mapped = set(to_ref.values())
        for f, ns in mine.items():
            r = to_ref.get(f)
            most += len(ns) if r is None or r not in ref else max(0, len(ns) - len(ref[r]))
        most += sum(len(ns) for f, ns in ref.items() if f not in mapped)
    return most


def check_style(
    reply: str,
    target: Sheet,
    *,
    reference: Sheet,
    passage: Passage,
    staffs: tuple[int, ...],
    around: Sheet,
) -> Checked:
    """The problems of a passage's answer (empty: accepted). ``target``: the notes of the hands rewritten; ``reference``:
    the reference's notes as the user wrote them (both hands); ``around``: the sheet of the passage, both hands (the
    target's harmony)."""
    text = frames._block(reply)
    if not text.startswith("F1 frames"):
        return Checked(["the answer must be F1 frames (first line 'F1 frames frameMs=40 ...')"])
    try:
        sheet = f1.read(text)
    except f1.F1Error as exc:
        return Checked([f"parse error: {exc}"])
    a, b = passage.start, passage.end
    errs: list[str] = []
    no_hand = [n for n in sheet.notes if n.staff not in (1, 2)]
    if no_hand:
        errs.append(f"{len(no_hand)} notes without a hand (write them after L: or R:), first at f{no_hand[0].frame}")
    if len(staffs) == 1:
        other = [n for n in sheet.notes if n.staff in (1, 2) and n.staff != staffs[0]]
        if other:
            mine, theirs = ("R", "left") if staffs[0] == 1 else ("L", "right")
            errs.append(
                f"{len(other)} notes are written in the {theirs} hand, first at f{other[0].frame}: the {theirs} hand is "
                f"fixed; write only {mine}: notes"
            )
    outside = [n for n in sheet.notes if not a <= n.frame < b]
    if outside:
        errs.append(f"{len(outside)} notes are outside the passage f{a}-f{b - 1}, first at f{outside[0].frame}")
    want = Counter((n.frame, n.midi) for n in target.notes if not n.covered)
    got = Counter((n.frame, n.midi) for n in sheet.notes if not n.covered)
    say_left, say_added = frames.declared(reply)
    left, added = (want - got) & say_left, (got - want) & say_added

    def show(c: Counter) -> str:
        items = sorted(c.elements())[:8]
        return ", ".join(f"f{f} {frames._name(m)}" for f, m in items) + (" ..." if sum(c.values()) > 8 else "")

    if want - got - left:
        missing = want - got - left
        errs.append(
            f"{sum(missing.values())} notes of the target are missing: {show(missing)} (a note left out on purpose "
            "needs its line '# leave out f... pitch')"
        )
    extra = got - want - added
    if extra:
        errs.append(
            f"{sum(extra.values())} notes are not in the target: {show(extra)} (a note added on purpose needs its "
            "line '# add f... pitch')"
        )
    most = change_budget(target, reference, passage, staffs)
    changed = sum(left.values()) + sum(added.values())
    if changed > most:
        errs.append(
            f"the answer leaves out {sum(left.values())} notes and adds {sum(added.values())}, more than {most}: "
            "change only the notes the reference's way of writing asks for, and keep the passage's own notes"
        )
    # A note added has a name of the passage's harmony: of a note of the passage (both hands) within a negra of it.
    q = (around.quarter_ms or 500.0) / FRAME_MS
    for f, m in sorted(added.elements()):
        names = {n.midi % 12 for n in around.notes if abs(n.frame - f) <= q and not n.covered}
        if names and m % 12 not in names:
            errs.append(
                f"f{f} {frames._name(m)} is added, but its name is not in the passage's harmony there: an added note "
                "takes a name of the notes the passage plays around it"
            )
    if 1 in staffs:
        to_ref = {t for s, _, t in passage.columns if s == 1}
        answer_cols = _columns(sheet.notes, 1)
        for f, ns in sorted(_columns(target.notes, 1).items()):
            top = max(n.midi for n in ns)
            here = [n.midi for n in answer_cols.get(f, [])]
            if any(m == top or abs(m - top) == 12 for m in here):
                continue
            if f not in to_ref and (f, top) in left:
                continue  # the reference plays nothing at the matching place
            errs.append(
                f"f{f} {frames._name(top)} of the melody (the top note of the right hand) is missing: the melody keeps "
                "its frames and its pitches (or the same name an octave away)"
            )
            break
    if not no_hand:
        errs += frames._structure(sheet)
    return Checked(errs, sheet, left, added, read_declared(reply).explain)


# ------------------------------------------------------------------ the marks the code copies

_LETTERS = "CDEFGAB"
_NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
#: Letters up for each shift in semitones (a tone higher: one letter, Sib -> Do).
_STEPS = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 5, 9: 5, 10: 6, 11: 6}


def moved_name(step: str, shift: int, midi: int) -> tuple[str, int, int] | None:
    """The name of ``midi`` taken from a note named with ``step`` and moved by ``shift`` semitones (the letter moves
    with the interval): ``(step, alter, octave)``, or ``None`` when it would need a double sign."""
    letter = _LETTERS[(_LETTERS.index(step) + _STEPS[shift % 12]) % 7]
    diff = (midi % 12 - _NATURAL[letter]) % 12
    alter = diff if diff <= 6 else diff - 12
    if abs(alter) > 1:
        return None
    octave = (midi - _NATURAL[letter] - alter) // 12 - 1
    return letter, alter, octave


def copy_marks(
    sheet: Sheet,
    *,
    reference: Sheet,
    before: list[Note],
    passage: Passage,
    staffs: tuple[int, ...],
) -> Counter:
    """The user's marks on the notes of the passage in ``sheet`` (changed in place), plan section 4.4: the marks the
    passage had (``before``: its notes before the run) stay on the same notes; then, from the reference (its notes and
    its clefs set by hand, as the user wrote them) through the column map: a spelling to a note of the same pitch
    class moved by the shift, a finger and the decoration-note switch to the same note (the same pitch after the
    shift, the same hand). A mark is never put over one the passage has. Returns the counts copied."""
    counts: Counter = Counter()
    a, b = passage.start, passage.end
    own = {(n.frame, n.midi, n.staff): n for n in before}
    ref_at: dict[tuple[int, int], list[Note]] = defaultdict(list)
    for n in reference.notes:
        ref_at[(n.staff, n.frame)].append(n)
    to_ref = {(s, t): r for s, r, t in passage.columns}

    def matching(st: int, f: int) -> int | None:
        for d in (0, -1, 1, -2, 2):  # the drawn column of a chord moves when its first note is left out
            if (st, f + d) in to_ref:
                return to_ref[(st, f + d)]
        return None

    for i, n in enumerate(sheet.notes):
        if n.staff not in staffs or not a <= n.frame < b or n.covered:
            continue
        mine = own.get((n.frame, n.midi, n.staff))
        new = n
        if mine is not None:
            if mine.spelled:
                new = replace(new, step=mine.step, alter=mine.alter, octave=mine.octave, spelled=True)
            if mine.finger is not None:
                new = replace(new, finger=mine.finger)
            if mine.grace_rule is not None:
                new = replace(new, grace_rule=mine.grace_rule)
        r = matching(n.staff, n.frame)
        refs = ref_at.get((n.staff, r), []) if r is not None else []
        same = next((x for x in refs if x.midi + passage.shift == n.midi), None)
        if not new.spelled:
            spelled = next(
                (x for x in refs if x.spelled and (x.midi + passage.shift) % 12 == n.midi % 12), None
            )
            name = moved_name(spelled.step, passage.shift, n.midi) if spelled is not None else None
            if name is not None:
                new = replace(new, step=name[0], alter=name[1], octave=name[2], spelled=True)
                counts["spellings"] += 1
        if new.finger is None and same is not None and same.finger is not None:
            new = replace(new, finger=same.finger)
            counts["fingers"] += 1
        if new.grace_rule is None and same is not None and same.grace_rule is not None:
            new = replace(new, grace_rule=same.grace_rule)
            counts["switches"] += 1
        sheet.notes[i] = new
    # A clef set by hand in the reference: the passage's matching stretch gets it (its first and last mapped columns).
    ra = min((n.frame for n in reference.notes), default=0)
    rb = max((n.frame for n in reference.notes), default=-1) + 1
    for ca, cb, st, clef in reference.user_clefs:
        if st not in staffs or cb <= ra or ca >= rb:
            continue
        inside = sorted(t for s, r, t in passage.columns if s == st and ca <= r < cb)
        if not inside:
            continue
        pa, pb = inside[0], inside[-1] + 1
        if any(s == st and x < pb and pa < y for x, y, s, _ in sheet.user_clefs):
            continue
        sheet.user_clefs = sorted([*sheet.user_clefs, (pa, pb, st, clef)])
        counts["clefs"] += 1
    return counts


def copied_text(counts: Counter) -> str:
    """The marks copied, for the batch's log line: "3 spellings, 2 fingers copied"."""
    names = {"spellings": "spelling", "fingers": "finger", "switches": "decoration-note switch", "clefs": "clef"}
    parts = [f"{counts[k]} {v}{'s' if counts[k] != 1 else ''}" for k, v in names.items() if counts.get(k)]
    if not parts:
        return ""
    return (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]) + " copied"


# ------------------------------------------------------------------ the run in memory


@dataclass
class StyleRun:
    #: The passages with the check's answer (every passage of the run, kept or dropped).
    passages: list[Passage]
    check_log: WindowLog
    #: Each passage written: its log and its check.
    batches: list[tuple[WindowLog, Checked]]
    #: The answer notes of every passage accepted (the hands rewritten), in order.
    written: list[Note]
    talks: list[Talk] = field(default_factory=list)


def _reference_sheet(current: Sheet, reference: tuple[int, int]) -> Sheet:
    """The reference's notes as the user wrote them (both hands, with their marks and the clefs set by hand)."""
    a, b = reference
    out = replace(current, notes=[n for n in current.notes if a <= n.frame < b])
    out.user_clefs = [c for c in current.user_clefs if c[0] < b and a < c[1]]
    return out


def write_style(
    current: Sheet,
    complete: Complete,
    *,
    reference: tuple[int, int],
    passages: list[Passage],
    staffs: tuple[int, ...],
    sid: str = "song",
    words: str = "",
    checked: bool = False,
    todo: list[int] | None = None,
    written_before: list[Note] = (),
    done_before: list[tuple[int, int]] = (),
    earlier_before: list[tuple[Passage, Sheet]] = (),
    first_index: int = 0,
    count: int | None = None,
    limit: int | None = None,
    max_checks: int = MAX_CHECKS,
    on_check: Callable[[WindowLog, list[Passage]], None] | None = None,
    on_batch: Callable[[WindowLog, Checked, Passage], None] | None = None,
    on_talk: Callable[[Talk], None] | None = None,
) -> StyleRun:
    """The run in memory: the check (unless ``checked``: the passages carry its answer), then the passages kept, or
    the ones of ``todo`` (their ``k``), in the order of the song, each checked, at most ``max_checks`` replies. A
    passage refused every time keeps no answer, and the run goes on; an error of the AI itself (no credits) stops
    it. ``written_before``, ``done_before`` and ``earlier_before``: what an earlier part of the run wrote (the run goes
    on after its first passage); ``first_index`` the number of the first passage written here among ``count``."""
    system = system_prompt()
    quarter = current.quarter_ms or 500.0
    check_log = WindowLog(k=-1, start=reference[0], end=reference[1])
    talks: list[Talk] = []
    if not checked:
        messages = [
            {
                "role": "user",
                "content": check_prompt(
                    sid=sid, sheet=current, reference=reference, passages=passages, staffs=staffs, words=words
                ),
            }
        ]
        errs, decided, reply = ["no reply"], list(passages), ""
        try:
            while check_log.replies < max_checks:
                reply = complete(system, messages)
                check_log.replies += 1
                errs, decided = read_check(reply, passages, reference=reference, quarter_ms=quarter)
                if not errs:
                    break
                check_log.errors.append(errs)
                messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": feedback(errs)}]
            check_log.status = "failed" if errs else "ok"
        except Exception as exc:  # noqa: BLE001 (no credits, no network: nothing is written)
            errs = [str(exc)]
            check_log.status, check_log.note = "error", f"{type(exc).__name__}: {exc}"
        talk = Talk(-1, reference[0], reference[1], _conversation(messages, reply), check_log.status, check_log.errors)
        if not errs:
            passages = decided
            talk.explain = [f"{p.name} {'kept' if p.keep else 'dropped'}: {p.why}".rstrip(": ") for p in passages]
        talks.append(talk)
        if on_talk:
            on_talk(talk)
        if on_check:
            on_check(check_log, passages)
        if errs:
            return StyleRun(passages, check_log, [], [], talks)
    kept = sorted((p for p in passages if p.keep), key=lambda p: p.start)
    total = count or len(kept)
    if todo is not None:
        kept = [p for p in kept if p.k in set(todo)]
    if limit is not None:
        kept = kept[:limit]
    ref_sheet = _reference_sheet(current, reference)
    written: list[Note] = list(written_before)
    done: list[tuple[int, int]] = list(done_before)
    earlier: list[tuple[Passage, Sheet]] = list(earlier_before)
    out: list[tuple[WindowLog, Checked]] = []
    back = int(frames.CONTEXT_MS / FRAME_MS)
    ahead = int(frames.LOOKAHEAD_MS / FRAME_MS)
    for index, p in enumerate(kept, start=first_index):
        a, b = p.start, p.end
        log = WindowLog(k=index, start=a, end=b)
        now = splice(current, written, done, staffs) if done else current
        target = _slice(current, a, b, staffs)
        target.quarter_ms = current.quarter_ms
        fixed = _slice(current, a, b, tuple(s for s in (1, 2) if s not in staffs)) if len(staffs) == 1 else None
        around = _slice(current, a, b, (1, 2))
        around.quarter_ms = current.quarter_ms
        prompt = batch_prompt(
            sid=sid,
            index=index,
            count=total,
            sheet=current,
            reference=reference,
            passage=p,
            staffs=staffs,
            target=target,
            fixed=fixed,
            earlier=earlier,
            context=_slice(now, max(0, a - back), a, (1, 2)),
            lookahead=_slice(now, b, b + ahead, (1, 2)),
            words=words,
        )
        messages = [{"role": "user", "content": prompt}]
        result = Checked(["no reply"])
        reply = ""
        try:
            if not target.notes:
                raise SkipWindow("The passage holds no notes of the hands rewritten.")
            while log.replies < max_checks:
                reply = complete(system, messages)
                log.replies += 1
                result = check_style(reply, target, reference=ref_sheet, passage=p, staffs=staffs, around=around)
                if not result.errors:
                    break
                log.errors.append(result.errors)
                messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": feedback(result.errors)}]
            log.status = "failed" if result.errors else "ok"
        except SkipWindow as exc:
            log.status, log.note = "failed", str(exc)
        except Exception as exc:  # noqa: BLE001 (no credits, no network: the passages done stay)
            log.status, log.note = "error", f"{type(exc).__name__}: {exc}"
        talk = Talk(index, a, b, _conversation(messages, reply), log.status, log.errors, f1.write(target, mode="frames"))
        if log.status == "ok" and result.sheet is not None:
            mine = [n for n in result.sheet.notes if n.staff in staffs]
            written += mine
            done.append((a, b))
            earlier.append((p, replace(target, notes=sorted(mine, key=lambda n: (n.frame, n.staff, n.midi)))))
            talk.explain, talk.declared = result.explain, result.declared()
        talks.append(talk)
        if on_talk:
            on_talk(talk)
        out.append((log, result))
        if log.status == "error":
            break
        if on_batch:
            on_batch(log, result, p)
    return StyleRun(
        passages, check_log, out, sorted(written, key=lambda n: (n.frame, n.staff, n.midi)), talks
    )


def write_again(
    complete: Complete,
    system: str,
    talk: Talk,
    words: str,
    current: Sheet,
    *,
    reference: tuple[int, int],
    passage: Passage,
    staffs: tuple[int, ...],
    max_checks: int = MAX_CHECKS,
) -> tuple[Talk, Checked]:
    """A passage written again with the user's answer (as a level batch, ``levels.write_again``): its conversation
    goes on with the user's ``words``, each reply checked against the passage's target as it was in the run.
    ``current``: the sheet now (the reference as the user wrote it; the other hand)."""
    target = f1.read(talk.target)
    target.quarter_ms = current.quarter_ms
    a, b = talk.start, talk.end
    around = replace(_slice(current, a, b, tuple(s for s in (1, 2) if s not in staffs)), quarter_ms=current.quarter_ms)
    around.notes = sorted(list(around.notes) + list(target.notes), key=lambda n: (n.frame, n.staff, n.midi))
    ref_sheet = _reference_sheet(current, reference)
    answer = (PROMPT_DIR / "answer.md").read_text(encoding="utf-8").format(words=words.strip()).rstrip("\n")
    messages = list(talk.messages) + [{"role": "user", "content": answer}]
    out = Talk(talk.k, a, b, messages, "open", list(talk.errors), talk.target)
    result = Checked(["no reply"])
    replies = 0
    while replies < max_checks:
        reply = complete(system, messages)
        replies += 1
        messages.append({"role": "assistant", "content": reply})
        result = check_style(reply, target, reference=ref_sheet, passage=passage, staffs=staffs, around=around)
        if not result.errors:
            break
        out.errors.append(result.errors)
        messages.append({"role": "user", "content": feedback(result.errors)})
    if result.errors and messages[-1]["role"] == "user":
        messages.pop()  # the feedback no reply answered
    out.status = "failed" if result.errors else "ok"
    if not result.errors:
        out.explain, out.declared = result.explain, result.declared()
    return out, result
