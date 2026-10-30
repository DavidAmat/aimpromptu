"""The whole song simplification by levels (implementation 04-3, Phase 3): the prompts, the plan of the song, the
check of an answer, and a run in memory.

A **level run** writes a passage or the whole song again at a level (easy, medium, hard; super hard later) with the
patterns the user chose in the catalog (the gallery of patterns of Phase 2, numbered inside each hand and level). It
breaks three limits of Simplify on purpose (plan section 5.2): it adds notes at new times (a bass note, then a
chord), leaves out many notes (octavas the song does not need, artifacts), and moves notes from one hand to the
other. So it has its own prompts, answer and check:

1. **The system prompt** of a run (:func:`system_prompt`): the shared part (``prompt/levels/shared.md``), the part of
   the level (``easy.md``, ``medium.md``, ``hard.md``) and the patterns of the run (:class:`Pattern`: the ones the
   user selected and the ones the words name, each with its number, name, one line and a short example in F1 frames
   text). The same for every request of the run, so it is cached.
2. **The plan of the song** (:func:`plan_prompt`, :func:`read_plan`): one request with a summary of the whole song
   (:func:`song_summary`: per stretch the chords the app found, the measures of each hand, the earlier stretch that
   sounds the same); the answer splits the song into sections, each with the pattern of each hand rewritten.
3. **The batches** (:func:`batch_prompt`), one after the other: the plan, the chords and the grid of the batch, the
   end of the previous batch as written, the earlier passage most like this one as written, the target and the
   look-ahead. The answer is the notes of the hands rewritten in F1 frames text (hands and figures only: the app
   draws beams, clefs, 8va and decoration notes by its rules), and the declared lines: the pattern of each hand,
   and each note of the melody line left out (``# not melody``, ``# artifact``), with why.
4. **The check** (:func:`check_level`, code, no AI): the format; the melody kept; the harmony kept; the notes per
   column and the span of each hand within the level; the hand motion within the level; the patterns declared and
   allowed; every new note on the grid. A reply that fails gets the problems back (:func:`level_feedback`), at most
   ``MAX_CHECKS`` replies.

:func:`write_level` runs the plan and the batches in memory (Phase 3's tests; Phase 4 stores the result). The
numbers of the limits come from the measures of the gallery (Phase 3 report, section 4).
"""

from __future__ import annotations

import json
import re
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

import numpy as np

from aitu_backend.pmn.notes import HAND_LEFT, HAND_RIGHT, Notes
from aitu_backend.sheet.levels.grid import Grid
from aitu_backend.sheet.levels.hands import Measures, measure, melody, place_line
from aitu_backend.sheet.levels.harmony import Chord, chords, pitch_name
from aitu_backend.sheet.llm.frames import (
    LOOKAHEAD_MS,
    SkipWindow,
    WindowLog,
    _block,
    _name,
    _slice,
    like_before,
    windows_of,
)
from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet
from aitu_backend.sheet.sheet.figures import FIGURES, nominal_ms

__all__ = [
    "LEVELS",
    "LEVEL_VERSION",
    "Batch",
    "Declared",
    "LevelRun",
    "Limits",
    "Pattern",
    "Section",
    "batch_prompt",
    "check_level",
    "level_feedback",
    "load_patterns",
    "plan_prompt",
    "read_declared",
    "read_plan",
    "refs_in",
    "song_summary",
    "system_prompt",
    "to_notes",
    "write_level",
]

Complete = Callable[[str, list[dict]], str]

PROMPT_DIR = Path(__file__).with_name("prompt") / "levels"
#: The levels of this plan, from the easiest. Super hard comes later: add it here and write ``super-hard.md``.
LEVELS = ("easy", "medium", "hard")
LEVEL_VERSION = (PROMPT_DIR / "VERSION").read_text(encoding="utf-8").strip()
HANDS = {1: "right", 2: "left"}
STAFF = {"right": 1, "left": 2}
#: A batch: 16 to 24 s (a level answer writes every note of its hands, as a whole run's window does, so a batch is
#: shorter than a batch of Simplify), at most this many onsets.
LEVEL_MS = (16000.0, 24000.0)
LEVEL_ONSETS = 260
#: The end of the previous batch, as written, that a batch sees.
CONTEXT_MS = 6000.0
#: The stretches of the song summary of the plan request.
SUMMARY_MS = (6000.0, 10000.0)
#: The negras of a pattern's example given in the prompt (the start of the example).
EXAMPLE_NEGRAS = 8
MAX_CHECKS = 3
#: The share of the melody line of a batch that may be declared not melody, at most.
MELODY_DROP_SHARE = 0.5
#: Seconds: an artifact is more than an octava above the median of the melody line this near, or has no note of
#: the melody line this near (plan section 5.5).
ARTIFACT_S = 3.0
#: The share of the left-hand notes of a chord's stretch that may be outside the chord (passing notes), at most.
OUTSIDE_SHARE = {"easy": 0.15, "medium": 0.25, "hard": 0.4}


@dataclass(frozen=True)
class Limits:
    """What one level allows, per column and per batch (the measures of the gallery: Phase 3 report, section 4).
    ``right_long`` is the most right-hand notes on a negra or longer; ``right`` on shorter figures."""

    right: int
    right_long: int
    right_span: int
    left: int
    left_span: int
    #: The widest range of the left hand inside two negras (a low note, then its chord).
    left_reach: int
    #: Moves of the left hand per negra (hand tracker), at most.
    left_moves: float
    #: The grid of new notes: "corchea" or "semicorchea".
    grid: str
    #: The shortest figure of a new note (a decoration note is a thirty-second or shorter).
    shortest: int


LIMITS = {
    "easy": Limits(1, 1, 0, 3, 9, 24, 0.75, "corchea", 16),
    "medium": Limits(2, 3, 9, 3, 12, 28, 1.25, "corchea", 16),
    "hard": Limits(3, 4, 12, 4, 12, 31, 2.0, "semicorchea", 64),
}


# ------------------------------------------------------------------ the patterns of a run


@dataclass
class Pattern:
    """A pattern of the catalog: ``ref`` "left medium 2", its name, its line, and its example in F1 frames text."""

    ref: str
    hand: str
    level: str
    number: int
    name: str
    line: str
    example: str

    def text(self, negras: int = EXAMPLE_NEGRAS) -> str:
        """The pattern for the prompt: its number, name and line, and the start of its example (``negras``
        negras, both hands: the other hand shows what the pattern goes with)."""
        ex = f1.read(self.example)
        q = ex.quarter_ms or 500.0
        first = min((n.frame for n in ex.notes), default=0)
        end = first + int(round(negras * q / FRAME_MS))
        cut = replace(ex, notes=[n for n in ex.notes if n.frame < end]).sort()
        body = f1.write(_bare(cut), mode="frames").strip()
        return f"### {self.ref}: {self.name}\n\n{self.line}\n\n```\n{body}\n```"


def _bare(sheet: Sheet) -> Sheet:
    """The notes with their hands and figures only (no beams, clefs, 8va or decoration notes): what an answer
    writes."""
    notes = [
        replace(n, beam=None, ottava=0, grace=None, gslot=0, ornaments=(), finger=None, fixed=False, grace_rule=None)
        for n in sheet.notes
        if not n.covered
    ]
    return replace(sheet, notes=notes, clefs={1: "G2", 2: "F4"}, clef_changes=[]).sort()


def load_patterns(catalog: Path) -> dict[str, Pattern]:
    """The patterns of a catalog folder (``patterns.json`` and the F1 files of the examples next to it, the gallery
    of Phase 2), by ``ref``. The example of a pattern is its first one."""
    data = json.loads((catalog / "patterns.json").read_text(encoding="utf-8"))
    out = {}
    for p in data["patterns"]:
        ex = next((e for e in p["examples"] if e.get("f1") and (catalog / e["f1"]).exists()), None)
        if ex is None:
            continue
        out[p["ref"]] = Pattern(
            ref=p["ref"],
            hand=p["hand"],
            level=p["level"],
            number=p["number"],
            name=p["name"],
            line=p["line"],
            example=(catalog / ex["f1"]).read_text(encoding="utf-8"),
        )
    return out


_REF = re.compile(r"\b(?:(left|right)\s+)?(easy|medium|hard|super hard)\s+(\d+)\b", re.I)


def refs_in(words: str, hands: tuple[str, ...] = ("left", "right")) -> list[str]:
    """The patterns the user's words name ("medium 2", "left hard 3"), as refs. A number without a hand names the
    pattern of that number in each hand of ``hands`` (the hands the run rewrites)."""
    out: list[str] = []
    for hand, level, number in _REF.findall(words):
        for h in [hand.lower()] if hand else list(hands):
            ref = f"{h} {level.lower()} {int(number)}"
            if ref not in out:
                out.append(ref)
    return out


Level = str | dict[str, str]


def hand_levels(level: Level) -> dict[int, str]:
    """The level of each hand: one level for both (``"hard"``), or one per hand (``{"right": "hard", "left":
    "medium"}``: the user's choice of 2026-10-30, a level per hand), as ``{staff: level}``."""
    out = {1: level, 2: level} if isinstance(level, str) else {STAFF[h]: v for h, v in level.items()}
    for v in out.values():
        if v not in LEVELS:
            raise ValueError(f"unknown level {v!r}")
    return out


def level_name(level: Level) -> str:
    """``hard``, or ``hard for the right hand and medium for the left hand``."""
    lv = hand_levels(level)
    if len(set(lv.values())) == 1:
        return next(iter(lv.values()))
    return " and ".join(f"{lv[s]} for the {HANDS[s]} hand" for s in sorted(lv))


def _hand_part(level: str, hand: str) -> str:
    """The section of ``<level>.md`` about one hand (from its heading "## The <hand> hand at <level>")."""
    text = (PROMPT_DIR / f"{level}.md").read_text(encoding="utf-8")
    start = text.index(f"## The {hand} hand at {level}")
    nxt = text.find("\n## ", start + 1)
    return text[start : nxt if nxt >= 0 else len(text)].rstrip()


def instructions(level: Level) -> str:
    """The shared part, then the part of the level, or of each hand's level when they differ."""
    shared = (PROMPT_DIR / "shared.md").read_text(encoding="utf-8").rstrip()
    lv = hand_levels(level)
    if lv[1] == lv[2]:
        return shared + "\n\n" + (PROMPT_DIR / f"{lv[1]}.md").read_text(encoding="utf-8").rstrip()
    head = (
        f"# The levels of this run: {lv[1]} for the right hand, {lv[2]} for the left hand\n\n"
        "The user chose a level for each hand. The two hands are still written together, as one piano part: a note "
        "that the transcription put in the wrong hand goes to the hand where it belongs, and each hand then follows "
        "its own level below. A hand that plays more must not make the other hand harder: they fit together."
    )
    return "\n\n".join([shared, head, _hand_part(lv[1], "right"), _hand_part(lv[2], "left")])


def system_prompt(level: Level, patterns: list[Pattern]) -> str:
    """The system prompt of a run: the shared part, the part of the level (or of each hand's level), and the
    patterns of the run (left hand first)."""
    hand_levels(level)
    ordered = sorted(patterns, key=lambda p: (p.hand != "left", LEVELS.index(p.level) if p.level in LEVELS else 9, p.number))
    body = "\n\n".join(p.text() for p in ordered) or "No pattern was chosen."
    return (
        instructions(level)
        + "\n\n# The patterns of this run\n\nThe user chose these patterns in the catalog. Use only these, adapted to "
        "the song (see \"The patterns\" above).\n\n"
        + body
        + "\n"
    )


def level_feedback(errors: list[str]) -> str:
    template = (PROMPT_DIR / "feedback.md").read_text(encoding="utf-8")
    return template.format(errors="\n".join(f"- {e}" for e in errors)).rstrip("\n")


# ------------------------------------------------------------------ what the prompts show


def clock(frame: int) -> str:
    s = int(frame * FRAME_MS / 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def chord_text(cs: list[Chord], key: int) -> str:
    """``f1042 E (bass E) · f1073 C#m (bass C#)``."""
    out = []
    for c in cs:
        bass = f" (bass {pitch_name(c.bass, key)})" if c.bass is not None and c.bass != c.root else ""
        out.append(f"f{c.start} {c.name(key)}{bass}")
    return " · ".join(out) or "none found"


def measure_text(m: Measures, sheet: Sheet, staff: int, start: int, end: int) -> str:
    if not m.notes:
        return "nothing"
    return (
        f"{m.notes_s:.1f} notes/s, up to {m.chord_max} notes in a column (widest {m.span} semitones), range "
        f"{m.reach} in two negras, {m.moves_s:.1f} moves/s ({m.big_moves_s:.1f} big); hand over "
        f"{place_line(sheet, staff, start, end, most=4)}"
    )


#: The pattern of a hand that keeps the notes of a simple stretch and makes only its rhythm regular.
KEEP = "keep"
#: The share of the left-hand onsets of an answer that are onsets of the left hand now (within a frame), at least.
RHYTHM_SHARE = 0.7
#: A simple stretch: the hand plays at most this many keys, inside this range (single notes, an octava, one small
#: chord again and again).
SIMPLE_NOTES = 3
SIMPLE_SPAN = 12


@dataclass
class Simple:
    """A stretch of one chord where one hand is already simple (the user, 2026-10-30): it plays at most
    ``SIMPLE_NOTES`` keys inside one octava (E2 again and again, an octava E2-E3, a held fifth). A level keeps its
    notes and makes only its rhythm regular."""

    staff: int
    start: int
    end: int
    keys: tuple[int, ...]  # every key the hand plays there
    columns: int
    single: bool


def _plain_cols(sheet: Sheet, staff: int, start: int, end: int) -> list[tuple[int, tuple[int, ...]]]:
    cols: dict[int, set[int]] = defaultdict(set)
    for n in sheet.notes:
        if n.staff == staff and not n.covered and not n.grace and start <= n.frame < end:
            cols[n.frame].add(n.midi)
    return [(f, tuple(sorted(ms))) for f, ms in sorted(cols.items())]


def simple_stretches(sheet: Sheet, staff: int, cs: list[Chord], start: int, end: int) -> list[Simple]:
    """The stretches of ``[start, end)`` (one per chord) where the hand ``staff`` is simple (:class:`Simple`)."""
    out = []
    for c in cs:
        a, b = max(c.start, start), min(c.end, end)
        cols = _plain_cols(sheet, staff, a, b)
        if not cols:
            continue
        keys = sorted({m for _, ms in cols for m in ms})
        if len(keys) <= SIMPLE_NOTES and keys[-1] - keys[0] <= SIMPLE_SPAN:
            single = all(len(ms) == 1 for _, ms in cols)
            out.append(Simple(staff, a, b, tuple(keys), len(cols), single))
    return out


def simple_text(stretches: list[Simple], key: int) -> str:
    """``f33-f159 E2 · f159-f191 F#3+C#4`` (neighbours with the same notes joined)."""
    from aitu_backend.sheet.sheet.common import spn  # noqa: PLC0415
    from aitu_backend.sheet.sheet.spelling import spell  # noqa: PLC0415

    joined: list[list] = []
    for st in stretches:
        if joined and joined[-1][1] == st.start and joined[-1][2] == st.keys:
            joined[-1][1] = st.end
        else:
            joined.append([st.start, st.end, st.keys])
    return " · ".join(
        f"f{a}-f{b} " + "+".join(spn(*spell(m, key)) for m in keys) for a, b, keys in joined
    )


def song_summary(sheet: Sheet, grid: Grid, staffs: tuple[int, ...]) -> tuple[str, list[tuple[int, int]]]:
    """The summary of the whole song for the plan request: one line per stretch (``SUMMARY_MS``, ending at a pause):
    its frames and clock, the chords, the measures of each hand, and the earlier stretch that sounds the same
    (:func:`like_before` on the right hand, or on the hand rewritten). Returns the text and the stretches."""
    rows = windows_of(sheet, span=SUMMARY_MS, max_onsets=10**6)
    cs = chords(sheet, grid)
    key = sheet.key or 0
    staff = 1 if 1 in staffs else 2
    lines = []
    for a, b in rows:
        here = [c for c in cs if a <= c.start < b] or [c for c in cs if c.start < a < c.end][:1]
        parts = [f"f{a}-f{b} ({clock(a)}-{clock(b)}): chords {' '.join(c.name(key) for c in here) or '-'}"]
        for st in (1, 2):
            parts.append(f"{'R' if st == 1 else 'L'}: {measure_text(measure(sheet, st, a, b, grid), sheet, st, a, b)}")
        if 2 in staffs:
            simple = simple_stretches(sheet, 2, [c for c in cs if c.start < b and c.end > a], a, b)
            if simple:
                parts.append(f"L simple (keep): {simple_text(simple, key)}")
        like = like_before(sheet, staff, a, b, a)
        if like:
            parts.append(f"sounds like f{like[0]}-f{like[1]}")
        lines.append(" | ".join(parts))
    return "\n".join(lines), rows


# ------------------------------------------------------------------ the plan of the song


@dataclass
class Section:
    index: int
    start: int
    end: int
    #: The pattern ref of each hand rewritten ("left easy 2"), or None for a hand that is not rewritten.
    left: str | None
    right: str | None
    why: str = ""

    def line(self) -> str:
        hands = " ".join(f"{h[0].upper()}={getattr(self, h)}" for h in ("left", "right") if getattr(self, h))
        return f"S{self.index} f{self.start}-f{self.end} {hands} | {self.why}".rstrip(" |")


_SECTION = re.compile(
    r"^\s*S(\d+)\s+f(\d+)\s*-\s*f(\d+)\s+(.*?)(?:\|(.*))?$", re.M
)
_HAND_REF = re.compile(r"\b([LR])\s*=\s*((?:left|right)\s+(?:easy|medium|hard|super hard)\s+\d+|keep)\b", re.I)


def plan_prompt(
    *,
    sid: str,
    level: Level,
    staffs: tuple[int, ...],
    summary: str,
    start: int,
    end: int,
    words: str = "",
) -> str:
    who = "both hands" if len(staffs) == 2 else f"the {HANDS[staffs[0]]} hand only"
    fixed = (
        ""
        if len(staffs) == 2
        else f" The {HANDS[3 - staffs[0]]} hand stays exactly as it is: plan only the {HANDS[staffs[0]]} hand."
    )
    lv = hand_levels(level)
    hands = " ".join(f"{'L' if s == 2 else 'R'}={HANDS[s]} {lv[s]} 1" for s in sorted(staffs, reverse=True))
    out = [
        f"# The plan of the song {sid}: level {level_name(level)}, {who}",
        f"The user asked to write the song again at the level {level_name(level)}, {who}.{fixed} Before the "
        "batches, plan the "
        f"whole song (f{start}-f{end}, {clock(start)}-{clock(end)}). Below, one line per stretch of the song: its "
        "frames and clock, the chords the app found in the notes, how each hand plays now (the measures of the hand "
        "tracker), and, when the app found it, the earlier stretch that sounds the same.",
    ]
    if words.strip():
        out.append(
            "## The user's words (of the utmost importance: they override the usual choices)\n\n" + words.strip()
        )
    out.append("## The song\n\n" + summary)
    out.append(
        "## Answer\n\nSplit the song into sections: a section is one or more stretches that the pianist plays with the "
        "same patterns (an intro, a verse, a chorus). A passage that repeats gets the same patterns as the first time. "
        "Choose few sections and few changes of pattern: the pianist reads the song more easily when the left hand "
        "keeps one pattern for most of it. Write one line per section, in order, as one block in triple backticks:\n\n"
        f"```\nS1 f{start}-f780 {hands} | the intro: why, in a few words\nS2 f780-f1440 {hands} | ...\n```\n\n"
        f"The sections cover f{start} to f{end} with no gap; each begins where the one before ends, on the first "
        "frame of a stretch. Each pattern is the ref of one pattern of this run (\"left easy 2\"), of the hand it "
        "is for, or `keep` for a left hand that the summary marks simple (\"L=keep\"): it keeps its notes and makes "
        "only its rhythm regular. For the other left-hand sections, choose the pattern whose rhythm is nearest to "
        "what the left hand plays now."
    )
    return "\n\n".join(out) + "\n"


def read_plan(
    reply: str, allowed: set[str], staffs: tuple[int, ...], start: int, end: int
) -> tuple[list[str], list[Section]]:
    """The sections of a plan reply, and its problems (empty: accepted): in order, from ``start`` to ``end`` with no
    gap, a pattern of the run for each hand rewritten."""
    text = "\n".join(re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", reply, re.S)) or reply
    found = _SECTION.findall(text)
    if not found:
        return ["write one line per section: 'S1 f33-f780 L=left easy 2 R=right easy 2 | why'"], []
    errs: list[str] = []
    out: list[Section] = []
    for k, (idx, a, b, hands, why) in enumerate(found, start=1):
        a, b = int(a), int(b)
        refs = {h.upper(): r.lower() for h, r in _HAND_REF.findall(hands)}
        sec = Section(k, a, b, refs.get("L"), refs.get("R"), (why or "").strip())
        for staff in staffs:
            h = HANDS[staff]
            ref = getattr(sec, h)
            if ref is None:
                errs.append(f"S{idx}: no pattern for the {h} hand ({h[0].upper()}=...)")
            elif ref == KEEP:
                continue
            elif ref not in allowed:
                errs.append(f"S{idx}: {ref} is not a pattern of this run")
            elif not ref.startswith(h):
                errs.append(f"S{idx}: {ref} is a pattern of the other hand")
        for staff in (1, 2):
            if staff not in staffs and getattr(sec, HANDS[staff]):
                errs.append(f"S{idx}: the {HANDS[staff]} hand stays as it is; write no pattern for it")
                setattr(sec, HANDS[staff], None)
        if b <= a:
            errs.append(f"S{idx}: f{a}-f{b} is empty")
        out.append(sec)
    if out and abs(out[0].start - start) > 2:
        errs.append(f"the first section must begin at f{start}")
    if out and abs(out[-1].end - end) > 2:
        errs.append(f"the last section must end at f{end}")
    for s, t in zip(out, out[1:]):
        if s.end != t.start:
            errs.append(f"S{s.index} ends at f{s.end} but S{t.index} begins at f{t.start} (no gap, no overlap)")
    return errs, ([] if errs else out)


# ------------------------------------------------------------------ a batch


def batch_prompt(
    *,
    sid: str,
    level: Level,
    staffs: tuple[int, ...],
    index: int,
    count: int,
    target: Sheet,
    fixed: Sheet | None,
    plan: list[Section],
    cs: list[Chord],
    grid: Grid,
    start: int,
    end: int,
    context: Sheet | None = None,
    like: Sheet | None = None,
    lookahead: Sheet | None = None,
    words: str = "",
) -> str:
    """The prompt of batch ``index`` (0 = first) of ``count``: the notes of ``[start, end)`` to write again."""
    key = target.key or 0
    who = "both hands" if len(staffs) == 2 else f"the {HANDS[staffs[0]]} hand"
    out = [
        f"# Level {level_name(level)}, {who}, of song {sid}: batch {index + 1} of {count} (f{start}-f{end}, "
        f"{clock(start)}-{clock(end)})"
    ]
    if words.strip():
        out.append("## The user's words (of the utmost importance)\n\n" + words.strip())
    here = [s for s in plan if s.start < end and s.end > start]
    out.append(
        "## The plan of the song (your plan; the sections of this batch are marked)\n\n"
        + "\n".join(("> " if s in here else "  ") + s.line() for s in plan)
    )
    out.append("## The chords of this batch (found by the app in the notes)\n\n" + chord_text(cs, key))
    simple = simple_stretches(target, 2, cs, start, end) if 2 in staffs else []
    if simple:
        out.append(
            "## Simple stretches of the left hand (keep their notes: `# pattern L f...-f...: keep`; make only the "
            "rhythm regular)\n\n" + simple_text(simple, key)
        )
    fine = [HANDS[s] for s in staffs if LIMITS[hand_levels(level)[s]].grid == "semicorchea"]
    half = (
        ""
        if not fine
        else ", or half way between two of them (a semicorchea)"
        if len(fine) == len(staffs)
        else f", or, in the {fine[0]} hand, half way between two of them (a semicorchea)"
    )
    out.append(
        "## The grid of this batch\n\nThe negras, each with the other corcheas of its time in parentheses. A new "
        "note starts on one of these frames"
        + half
        + ", or at the frame of a note of the target.\n\n"
        + grid.text(start, end)
    )
    ms = []
    for st in (1, 2):
        m = measure(target if st in staffs else (fixed or target), st, start, end, grid)
        ms.append(f"- {'R' if st == 1 else 'L'} now: {measure_text(m, target if st in staffs else (fixed or target), st, start, end)}")
    out.append("## How the hands play now (hand tracker)\n\n" + "\n".join(ms))
    if like is not None and like.notes:
        a, b = min(n.frame for n in like.notes), max(n.frame for n in like.notes)
        out.append(
            f"## An earlier passage like this one (f{a}-f{b}, as you wrote it)\n\nWrite the same passage the same way.\n\n```\n"
            + f1.write(_bare(like), mode="frames").strip()
            + "\n```"
        )
    if context is not None and context.notes:
        out.append(
            "## Decided context (the end of the previous batch, as you wrote it)\n\n```\n"
            + f1.write(_bare(context), mode="frames").strip()
            + "\n```"
        )
    out.append(
        f"## Target ({who} as the sheet has them now: write {'them' if len(staffs) == 2 else 'it'} again)\n\n```\n"
        + f1.write(_bare(target), mode="frames").strip()
        + "\n```"
    )
    if fixed is not None and fixed.notes:
        other = HANDS[3 - staffs[0]]
        out.append(
            f"## The {other} hand (fixed: it stays exactly as it is; do not write it)\n\n```\n"
            + f1.write(_bare(fixed), mode="frames").strip()
            + "\n```"
        )
    if lookahead is not None and lookahead.notes:
        out.append(
            "## Look-ahead (the next notes as they are now; do not write them)\n\n```\n"
            + f1.write(_bare(lookahead), mode="frames").strip()
            + "\n```"
        )
    hand_lines = " and ".join(
        f"`# pattern {'L' if s == 2 else 'R'} f{start}-f{end}: <{HANDS[s]} pattern>`" for s in sorted(staffs, reverse=True)
    )
    out.append(
        "## Answer\n\nWrite the batch at the level, as one block in triple backticks: the two header lines of the "
        f"target, the note lines of f{start}-f{end} ({who} only), then the declared lines: {hand_lines} (one line per "
        "pattern used, with the frames where it is used), and one line for each note of the melody line that you "
        "leave out (`# not melody f1084 E4: why`, `# artifact f863 D#7: why`)."
    )
    return "\n\n".join(out) + "\n"


# ------------------------------------------------------------------ the answer and its check


@dataclass
class Declared:
    #: ``(hand "L"/"R", start, end, ref)``
    patterns: list[tuple[str, int, int, str]] = field(default_factory=list)
    #: ``(frame, midi, kind "not melody"/"artifact", pitch as written, why)``
    dropped: list[tuple[int, int, str, str, str]] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [f"pattern {h} f{a}-f{b}: {r}" for h, a, b, r in self.patterns]
        out += [f"{k} f{f} {p}: {w}" for f, _, k, p, w in self.dropped]
        return out


_PATTERN = re.compile(
    r"^\s*#\s*pattern\s+([LR])\s+f(\d+)\s*-\s*f(\d+)\s*:\s*((?:left|right)\s+(?:easy|medium|hard|super hard)\s+\d+|keep)\b",
    re.M | re.I,
)
_DROP = re.compile(r"^\s*#\s*(not melody|artifact)\s+f(\d+)\s+([A-G][#b]*-?\d+(?:\s*,\s*[A-G][#b]*-?\d+)*)(.*)$", re.M | re.I)


def read_declared(reply: str) -> Declared:
    from aitu_backend.sheet.sheet.common import parse_spn  # noqa: PLC0415
    from aitu_backend.sheet.sheet.pitch import pitch_to_midi  # noqa: PLC0415

    d = Declared()
    for h, a, b, ref in _PATTERN.findall(reply):
        d.patterns.append((h.upper(), int(a), int(b), " ".join(ref.lower().split())))
    for kind, frame, pitches, rest in _DROP.findall(reply):
        why = rest.strip().lstrip(":-– ").strip()
        for p in re.split(r"\s*,\s*", pitches):
            try:
                m = pitch_to_midi(*parse_spn(p))
            except (ValueError, KeyError, IndexError):
                continue
            d.dropped.append((int(frame), m, kind.lower(), p, why))
    return d


@dataclass
class Batch:
    """What the check found in one answer: its problems, the parsed notes, the declared lines and the measures."""

    errors: list[str]
    sheet: Sheet | None = None
    declared: Declared = field(default_factory=Declared)
    measures: dict[int, Measures] = field(default_factory=dict)
    melody: int = 0
    melody_dropped: int = 0
    new_notes: int = 0


def _cols(sheet: Sheet, staff: int) -> dict[int, list[Note]]:
    out: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        if n.staff == staff and not n.covered:
            out[n.frame].append(n)
    return out


def _show(items: list[str], most: int = 6) -> str:
    return ", ".join(items[:most]) + (f" and {len(items) - most} more" if len(items) > most else "")


#: A left-hand chord whose top note is at least this (C4), with no right-hand note of the melody within a negra,
#: carries the melody (:func:`hidden_line`).
HIDDEN_LOW = 60


def hidden_line(target: Sheet, artifacts: set[int]) -> list[Note]:
    """The top notes of the left-hand chords (two notes or more, top at ``HIDDEN_LOW`` or above) where the right hand
    plays no note within one negra, apart from the right-hand columns at ``artifacts`` (frames declared artifacts):
    the riff of 99 Red Balloons (plan section 5.1: the right hand takes over notes that help the left hand)."""
    near = (target.quarter_ms or 500.0) / FRAME_MS
    right = [n.frame for n in target.notes if n.staff == 1 and not n.grace and not n.covered
             and not any(abs(n.frame - f) <= 1 for f in artifacts)]
    out = []
    for f, ns in sorted(_cols(target, 2).items()):
        if len(ns) < 2 or any(n.grace for n in ns):
            continue
        top = max(ns, key=lambda n: n.midi)
        if top.midi >= HIDDEN_LOW and not any(abs(r - f) <= near for r in right):
            out.append(top)
    return out


def _far_above(n: Note, line: list[Note], target: Sheet, artifacts: set[tuple[int, int]]) -> bool:
    """True when ``n`` may be an artifact (plan section 5.5): more than an octava above the median of the other
    notes of the melody line within ``ARTIFACT_S`` seconds that are not declared artifacts; or, with no such note,
    more than an octava above every other note of either hand that near (the riff of 99 Red Balloons: the melody line
    is only the high chords, and the music is in the left hand)."""
    near = int(ARTIFACT_S * 1000 / FRAME_MS)
    around = [
        x.midi for x in line if x is not n and abs(x.frame - n.frame) <= near and (x.frame, x.midi) not in artifacts
    ]
    if around:
        return n.midi > float(np.median(around)) + 12
    gone = {f for f, _ in artifacts} | {n.frame}  # a right-hand column whose top is an artifact goes with it
    rest = [
        x.midi
        for x in target.notes
        if abs(x.frame - n.frame) <= near and not (x.staff == 1 and any(abs(x.frame - f) <= 1 for f in gone))
    ]
    return not rest or n.midi > max(rest) + 12


def check_level(
    reply: str,
    target: Sheet,
    *,
    level: Level,
    staffs: tuple[int, ...],
    grid: Grid,
    cs: list[Chord],
    allowed: set[str],
    start: int,
    end: int,
) -> Batch:
    """The check of a batch answer (plan section 5.5). ``target`` holds the notes of ``[start, end)`` of the hands
    rewritten as the sheet has them; ``cs`` the chords of the batch; ``allowed`` the refs of the run."""
    levels = hand_levels(level)
    lims = {s: LIMITS[v] for s, v in levels.items()}
    text = _block(reply)
    if not text.startswith("F1 frames"):
        return Batch(["the answer must be F1 frames (first line 'F1 frames frameMs=40 ...')"])
    try:
        sheet = f1.read(text)
    except f1.F1Error as exc:
        return Batch([f"parse error: {exc}"])
    sheet.quarter_ms = target.quarter_ms
    d = read_declared(reply)
    out = Batch([], sheet, d)
    errs = out.errors
    q = target.quarter_ms or 500.0
    # the format
    no_hand = [n for n in sheet.notes if n.staff not in (1, 2)]
    if no_hand:
        errs.append(f"{len(no_hand)} notes without a hand (write them after L: or R:), first at f{no_hand[0].frame}")
    other = [n for n in sheet.notes if n.staff in (1, 2) and n.staff not in staffs]
    if other:
        h = HANDS[other[0].staff]
        errs.append(f"{len(other)} notes in the {h} hand, first at f{other[0].frame}: the {h} hand is fixed; do not write it")
    outside = [n for n in sheet.notes if not start <= n.frame < end]
    if outside:
        errs.append(f"{len(outside)} notes outside f{start}-f{end}, first at f{outside[0].frame}")
    if not sheet.notes:
        errs.append("the answer has no notes")
        return out
    if no_hand or other:
        return out
    # the melody: each note of the right hand's top line stays at its frame (or one frame from it), the same pitch
    # or the same name an octave away, unless declared; where the right hand has no melody, the top notes of the
    # left-hand chords are the melody (the riff), and they go to the right hand
    if 1 in staffs and 2 in staffs:
        artifact_frames = {f for f, _, k, *_ in d.dropped if k == "artifact"}
        hidden = hidden_line(target, artifact_frames)
        right = _cols(sheet, 1)
        said = {(f, m) for f, m, *_ in d.dropped}
        lost = []
        for n in hidden:
            here = [x.midi for f in (n.frame - 1, n.frame, n.frame + 1) for x in right.get(f, [])]
            if n.midi in here or n.midi + 12 in here or (n.frame, n.midi) in said:
                continue
            lost.append(f"f{n.frame} {_name(n.midi)}")
        out.melody += len(hidden)
        if lost:
            errs.append(
                f"{len(lost)} top notes of the left-hand chords are missing from the right hand: {_show(lost)}. "
                "Where the right hand has no melody (only artifacts, or nothing), these top notes are the melody: "
                "play each one in the right hand, at its pitch or an octava higher, or declare it "
                "('# not melody f... pitch: why')"
            )
    if 1 in staffs:
        line = melody(target, start, end)
        right = _cols(sheet, 1)
        said = {(f, m): k for f, m, k, *_ in d.dropped}
        artifacts = {k for k, v in said.items() if v == "artifact"}
        missing, not_artifact, dropped, not_melody = [], [], 0, 0
        for n in line:
            here = [x.midi for f in (n.frame - 1, n.frame, n.frame + 1) for x in right.get(f, [])]
            if n.midi in here or n.midi - 12 in here or n.midi + 12 in here:
                continue
            kind = said.get((n.frame, n.midi))
            if kind is None:
                missing.append(f"f{n.frame} {_name(n.midi)}")
                continue
            if kind == "artifact" and not _far_above(n, line, target, artifacts):
                not_artifact.append(f"f{n.frame} {_name(n.midi)}")
                continue
            dropped += 1
            not_melody += kind == "not melody"
        out.melody, out.melody_dropped = out.melody + len(line), dropped
        if not_artifact:
            errs.append(
                f"{len(not_artifact)} notes declared artifacts are part of the melody line: {_show(not_artifact)}. An "
                f"artifact is more than an octava above the melody around it ({ARTIFACT_S:g} s before and after), or, "
                "where the melody line has nothing else, more than an octava above every other note; keep these notes"
            )
        if missing:
            errs.append(
                f"{len(missing)} notes of the melody line are missing: {_show(missing)}. Keep each one at its frame "
                "(a shorter or longer figure is fine), or declare it ('# not melody f... pitch: why' or "
                "'# artifact f... pitch: why')"
            )
        if line and not_melody > MELODY_DROP_SHARE * len(line):
            errs.append(
                f"{not_melody} of the {len(line)} notes of the melody line are declared not melody: keep most of the "
                f"melody (at most {int(MELODY_DROP_SHARE * 100)} %)"
            )
    # the harmony: at each chord, the lowest left-hand note of its first left-hand column has the bass of the
    # original or the root; most left-hand notes are notes of the chord or of the original stretch
    if 2 in staffs:
        left = _cols(sheet, 2)
        frames = sorted(left)
        wrong_bass, foreign, total = [], 0, 0
        orig_pcs = defaultdict(set)
        for n in target.notes:
            for c in cs:
                if c.start <= n.frame < c.end:
                    orig_pcs[c.start].add(n.midi % 12)
        for c in cs:
            inside = [f for f in frames if max(c.start, start) - 1 <= f < min(c.end, end)]
            if not inside or c.bass is None:
                continue
            first = inside[0]
            if first - c.start <= q / FRAME_MS * 1.05 or c.start < start:
                low = min(n.midi for n in left[first]) % 12
                if low not in (c.bass, c.root):
                    wrong_bass.append(
                        f"f{first} {_name(min(n.midi for n in left[first]))} (the chord {c.name(target.key or 0)} at "
                        f"f{c.start} has the bass {pitch_name(c.bass, target.key or 0)})"
                    )
            ok = c.tones | orig_pcs[c.start]
            for f in inside:
                for n in left[f]:
                    total += 1
                    foreign += n.midi % 12 not in ok
        if wrong_bass:
            errs.append(
                f"{len(wrong_bass)} chords begin on another bass: {_show(wrong_bass, 4)}. The lowest left-hand note "
                "where a chord begins keeps the bass of the song (or the root of the chord)"
            )
        if total and foreign > OUTSIDE_SHARE[levels[2]] * total + 1:
            errs.append(
                f"{foreign} of the {total} left-hand notes are outside the chords of the song: keep the harmony "
                "(the left-hand companion changes the way the chord is played, not the chord)"
            )
    # playable at the level, per column
    for staff in staffs:
        hand = "R" if staff == 1 else "L"
        lim = lims[staff]
        bad = []
        for f, ns in sorted(_cols(sheet, staff).items()):
            ms = sorted(n.midi for n in ns)
            fig = min(n.figure or 4 for n in ns)
            most = (lim.right_long if fig <= 4 else lim.right) if staff == 1 else lim.left
            span = lim.right_span if staff == 1 else lim.left_span
            if len(ms) > most:
                bad.append(f"f{f} {len(ms)} notes")
            elif ms[-1] - ms[0] > span:
                bad.append(f"f{f} a span of {ms[-1] - ms[0]} semitones")
        if bad:
            what = (
                f"at most {lim.right} notes on short figures and {lim.right_long} on a negra or longer, within "
                f"{lim.right_span} semitones"
                if staff == 1
                else f"at most {lim.left} notes within {lim.left_span} semitones"
            )
            errs.append(f"{hand}: {len(bad)} columns are beyond the level ({what}): {_show(bad)}")
    # hand motion
    for staff in (1, 2):
        if staff in staffs:
            out.measures[staff] = measure(sheet, staff, start, end, grid)
    if 2 in staffs:
        lim = lims[2]
        m = out.measures[2]
        if m.moves_q > lim.left_moves:
            errs.append(
                f"L: the hand moves {m.moves_q:.2f} times per negra (at most {lim.left_moves} at this level): keep "
                "the hand in one position until the chord changes"
            )
        if m.reach > lim.left_reach:
            errs.append(
                f"L: the hand covers {m.reach} semitones inside two negras (at most {lim.left_reach} at this level): "
                "bring the low notes nearer to the chords"
            )
    if 1 in staffs:
        before = measure(target, 1, start, end, grid)
        if out.measures[1].moves_q > before.moves_q + 0.1:
            errs.append(
                f"R: the hand moves {out.measures[1].moves_q:.2f} times per negra, more than the sheet now "
                f"({before.moves_q:.2f}): the right hand must not move more than before"
            )
    # the patterns declared
    for staff in staffs:
        h = "R" if staff == 1 else "L"
        mine = [p for p in d.patterns if p[0] == h]
        if not mine:
            errs.append(f"declare the pattern of the {HANDS[staff]} hand: '# pattern {h} f{start}-f{end}: <ref>'")
        for _, a, b, ref in mine:
            if ref == KEEP:
                continue
            if ref not in allowed:
                errs.append(f"{ref} is not a pattern of this run")
            elif not ref.startswith(HANDS[staff]):
                errs.append(f"{ref} is a pattern of the other hand")
    # never harder than the sheet now: a simple stretch of the left hand keeps its notes, never more of them in time;
    # and the left hand follows the rhythm it plays now (the user, 2026-10-30)
    for staff in [s_ for s_ in staffs if s_ == 2]:
        harder = []
        for st in simple_stretches(target, staff, cs, start, end):
            now = _plain_cols(sheet, staff, st.start, st.end)
            other = sorted({m for _, ms in now for m in ms} - set(st.keys))
            where = f"f{st.start}-f{st.end}"
            if other:
                harder.append(f"{where} adds {', '.join(_name(m) for m in other)}")
            elif st.single and any(len(ms) > 1 for _, ms in now):
                harder.append(f"{where} plays chords where the sheet plays single notes")
            if len(now) > st.columns:
                harder.append(f"{where} has {len(now)} onsets where the sheet has {st.columns}")
        if harder:
            h = "R" if staff == 1 else "L"
            errs.append(
                f"{h}: {len(harder)} simple stretches are made harder: {_show(harder, 4)}. Where the sheet plays "
                "single notes or one chord again and again, keep its notes ('# pattern "
                f"{h} f...-f...: keep') and only make the rhythm regular, with as many onsets or fewer"
            )
    if 2 in staffs:
        now_on = [f for f, _ in _plain_cols(target, 2, start, end)]
        ans_on = [f for f, _ in _plain_cols(sheet, 2, start, end)]
        more = []
        for c in cs:
            a_, b_ = max(c.start, start), min(c.end, end)
            k_now = sum(a_ <= f < b_ for f in now_on)
            k_ans = sum(a_ <= f < b_ for f in ans_on)
            if k_ans > k_now:
                more.append(f"f{a_}-f{b_} {k_ans} onsets where the sheet has {k_now}")
        if more:
            errs.append(
                f"L: {len(more)} chords have more left-hand onsets than the sheet now: {_show(more, 4)}. A level "
                "simplifies the rhythm the left hand plays; it never adds onsets"
            )
        on_now = sum(any(abs(f - g) <= 1 for g in now_on) for f in ans_on)
        if ans_on and on_now < RHYTHM_SHARE * len(ans_on):
            errs.append(
                f"L: only {on_now} of the {len(ans_on)} left-hand onsets are onsets of the left hand now (at least "
                f"{int(RHYTHM_SHARE * 100)} %): follow the rhythm the left hand plays now, simplified (keep its main "
                "onsets, leave out the fast ones); do not invent another rhythm, such as an arpeggio in corcheas "
                "where it plays a negra and two corcheas"
            )
    # the time of new notes, and their figures
    before = {(n.frame, n.midi, n.staff) for n in target.notes}
    off, short = [], []
    for n in sheet.notes:
        if (n.frame, n.midi, n.staff) in before:
            continue
        out.new_notes += 1
        lim = lims.get(n.staff, lims[1])
        if not grid.on_grid(n.frame, lim.grid):
            off.append(f"f{n.frame} {_name(n.midi)}")
        if n.figure and n.figure > lim.shortest:
            short.append(f"f{n.frame} {_name(n.midi)}:{n.figure}")
    if off:
        errs.append(
            f"{len(off)} new notes are not on the grid: {_show(off)}. Start a new note on a frame of the grid, "
            "or at the frame of a note of the target"
        )
    if short:
        errs.append(
            f"{len(short)} new notes are shorter than the level allows (a figure shorter than a semicorchea becomes a "
            f"decoration note): {_show(short)}"
        )
    return out


# ------------------------------------------------------------------ the notes of an answer, and a run in memory


def to_notes(sheet: Sheet, quarter_ms: float, *, keep: list[Note] = ()) -> Notes:
    """The notes of an answer (and ``keep``, the notes of a fixed hand), as ``Notes`` for the app's rules: each at
    its frame, as long as its figure (the length the answer wrote)."""
    rows = [n for n in list(sheet.notes) + list(keep) if not n.covered and n.staff in (1, 2)]
    return Notes(
        id=np.arange(1, len(rows) + 1),
        key=[n.midi - 21 for n in rows],
        on_ms=[n.frame * FRAME_MS for n in rows],
        len_ms=[max(nominal_ms(n.figure if n.figure in FIGURES else 4, quarter_ms), 30.0) for n in rows],
        hand=[HAND_RIGHT if n.staff == 1 else HAND_LEFT for n in rows],
    )


def drawn(sheet: Sheet, quarter_ms: float, *, key: int, key_changes=None, keep: list[Note] = ()) -> Sheet:
    """The answer as the app draws it: its notes through the algorithm's rules (figures from the lengths capped at
    the next onset of the hand, decoration notes, beam groups, spelling, clefs and 8va)."""
    return propose_frames(
        to_notes(sheet, quarter_ms, keep=keep), key=key, key_changes=key_changes, quarter_ms=quarter_ms
    ).sheet


@dataclass
class LevelRun:
    level: Level
    staffs: tuple[int, ...]
    plan: list[Section]
    plan_log: WindowLog
    batches: list[tuple[WindowLog, Batch]]
    #: The answer notes of every batch accepted (the hands rewritten), in order.
    written: Sheet


def write_level(
    current: Sheet,
    complete: Complete,
    grid: Grid,
    *,
    level: Level,
    staffs: tuple[int, ...],
    patterns: list[Pattern],
    sid: str = "song",
    words: str = "",
    windows: list[tuple[int, int]] | None = None,
    plan: list[Section] | None = None,
    max_checks: int = MAX_CHECKS,
    on_batch: Callable[[WindowLog, Batch], None] | None = None,
) -> LevelRun:
    """A level run in memory: the plan of the song (unless ``plan`` is given), then the batches (``windows``, or the
    batches of the whole song), each checked, at most ``max_checks`` replies. A batch that fails keeps no answer."""
    system = system_prompt(level, patterns)
    allowed = {p.ref for p in patterns}
    notes = [n for n in current.notes if not n.covered]
    start, end = min(n.frame for n in notes), max(n.frame for n in notes) + 1
    plan_log = WindowLog(k=-1, start=start, end=end)
    if plan is None:
        summary, _ = song_summary(current, grid, staffs)
        messages = [{"role": "user", "content": plan_prompt(sid=sid, level=level, staffs=staffs, summary=summary, start=start, end=end, words=words)}]
        plan = []
        errs = ["no reply"]
        while plan_log.replies < max_checks:
            reply = complete(system, messages)
            plan_log.replies += 1
            errs, plan = read_plan(reply, allowed, staffs, start, end)
            if not errs:
                break
            plan_log.errors.append(errs)
            messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": level_feedback(errs)}]
        plan_log.status = "failed" if errs else "ok"
        if errs:
            return LevelRun(level, staffs, [], plan_log, [], replace(current, notes=[]))
    wins = windows or [
        (a, b)
        for a, b in windows_of(
            Sheet(notes=[n for n in current.notes if n.staff in staffs], clefs=dict(current.clefs), key=current.key),
            span=LEVEL_MS,
            max_onsets=LEVEL_ONSETS,
        )
    ]
    cs_all = chords(current, grid)
    written: list[Note] = []
    done: list[tuple[int, int]] = []
    out: list[tuple[WindowLog, Batch]] = []
    back = int(CONTEXT_MS / FRAME_MS)
    for k, (a, b) in enumerate(wins):
        log = WindowLog(k=k, start=a, end=b)
        target = _slice(current, a, b, staffs)
        target.quarter_ms = current.quarter_ms
        fixed = _slice(current, a, b, tuple(s for s in (1, 2) if s not in staffs)) if len(staffs) == 1 else None
        cs = [c for c in cs_all if c.start < b and c.end > a]
        like = like_before(current, staffs[0] if len(staffs) == 1 else None, a, b, max(0, a - back))
        like_sheet = None
        if like and any(s <= like[0] and like[1] <= e for s, e in done):
            like_sheet = replace(current, notes=[n for n in written if like[0] <= n.frame < like[1]])
        context = None
        if done and done[-1][1] == a:
            context = replace(current, notes=[n for n in written if a - back <= n.frame < a])
        prompt = batch_prompt(
            sid=sid,
            level=level,
            staffs=staffs,
            index=k,
            count=len(wins),
            target=target,
            fixed=fixed,
            plan=plan,
            cs=cs,
            grid=grid,
            start=a,
            end=b,
            context=context,
            like=like_sheet,
            lookahead=_slice(current, b, b + int(LOOKAHEAD_MS / FRAME_MS), (1, 2)),
            words=words,
        )
        messages = [{"role": "user", "content": prompt}]
        result = Batch(["no reply"])
        try:
            while log.replies < max_checks:
                reply = complete(system, messages)
                log.replies += 1
                result = check_level(
                    reply, target, level=level, staffs=staffs, grid=grid, cs=cs, allowed=allowed, start=a, end=b
                )
                if not result.errors:
                    break
                log.errors.append(result.errors)
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": level_feedback(result.errors)},
                ]
            log.status = "failed" if result.errors else "ok"
        except SkipWindow as exc:
            log.status, log.note = "failed", str(exc)
        except Exception as exc:  # noqa: BLE001 (no credits, no network: the batches done stay)
            log.status, log.note = "error", f"{type(exc).__name__}: {exc}"
            out.append((log, result))
            break
        if log.status == "ok" and result.sheet is not None:
            written += [n for n in result.sheet.notes if n.staff in staffs]
            done.append((a, b))
        out.append((log, result))
        if on_batch:
            on_batch(log, result)
    return LevelRun(level, staffs, plan, plan_log, out, replace(current, notes=sorted(written, key=lambda n: (n.frame, n.staff, n.midi))))
