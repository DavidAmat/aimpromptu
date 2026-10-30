"""The LLM step of the new sheet (implementation 03, Phase 4): notes -> F1 frames sheet, window by window.

The bars chain (:mod:`aitu_backend.sheet.llm.chain`, the research's) asks for F1 bars; the product sheet has no
compases, and Phase 2 made the figures, the grace notes and the spelling rules of the app. What is left to the LLM
(plan section 4, Phase 4): the **hands**, the **beam groups** (plan section 3.11), the **clefs and 8va** (the
left-hand rules, version 4), the **ornaments**, the **armadura of each passage** (rule 6), and the **reference
figure** (section 3.3), asked once before the windows with the gaps between onsets described in words.

The chain, behind the same function as the bars chain::

    complete(system: str, messages: list[{"role": "user" | "assistant", "content": str}]) -> str

1. **The reference figure** (unless given): one conversation with the peaks of the gaps between onsets
   (:func:`gap_peaks`) and the start of the song; the reply is ``quarterMs=NNN``. A reply without a usable
   value keeps the pulse estimate of the algorithm.
2. **The algorithm** (``proposal.frames.propose_frames``) with the starting hands and that reference figure: the
   figures the input shows, and the fallback of a window.
3. **Windows** (:func:`windows_of`): 12 to 16 s, at most ``MAX_ONSETS`` onsets, each ending after the longest
   pause in that range. They depend only on the notes, so they are known before any request, and every answer is
   kept whole (no part of a window is decided again). One conversation per window: the target (the notes without
   hands, with the figures of the rule), a look-ahead, and from the second window on the end of the previous
   answer as decided context. :func:`check_answer` lists the problems; a rejected reply gets the feedback and the
   model writes the whole answer again, at most ``MAX_CHECKS`` replies.
4. **The sheet** (:func:`assemble`): the hands, beams, clefs, 8va, ornaments and armaduras of each window (the
   LLM's, or the algorithm's for a failed one) on the notes; then the rules: figures from the lengths capped at
   the next onset of the hand (they need the LLM's hands), grace notes and lone short notes written longer
   (implementation 04, Phase 2), beam groups cut where the figures break them (one figure per group,
   :func:`trim_beams`), and the spelling. ``frames.check`` holds on the result.

A ``complete`` that raises :class:`SkipWindow` fails that window only (a refusal); any other exception (no
credits, no network) keeps the algorithm for that window and every later one, and is reported in the result.

Two requests of the user work on the sheet as it is now: :func:`write_stretch` (implementation 03, Phase 7) writes
one stretch again with the user's words, both hands or one (implementation 04, Phase 4: the other hand fixed), and
:func:`write_simplify` (implementation 04, Phase 4) applies the rules of simplicity only to one hand or both, over
the whole song, in batches about twice as long as a window. A Simplify batch answers only the notes it leaves out
and adds, with why (:func:`check_simplify`), and sees every change made before it, the earlier passage most like it
(:func:`like_before`) and the end of the previous batch as simplified.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np

from aitu_backend.pmn.notes import Notes
from aitu_backend.sheet.proposal.frames import (
    BASS_LIMIT,
    FramesProposal,
    _ledger,
    assign_figures,
    clefs_and_ottavas,
    find_graces,
    lengthen_lone,
    propose_frames,
    respell,
)
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet import frames as frames_mod
from aitu_backend.sheet.sheet.common import parse_spn, spn
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet, carry_extras
from aitu_backend.sheet.sheet.figures import FIGURES, figure_of_ms, nominal_ms, steps
from aitu_backend.sheet.sheet.pitch import pitch_to_midi
from aitu_backend.sheet.sheet.spelling import spell

__all__ = [
    "Complete",
    "FramesSong",
    "Part",
    "SkipWindow",
    "WindowLog",
    "assemble",
    "Change",
    "Simplified",
    "beam_pairs",
    "check_answer",
    "check_simplify",
    "declared",
    "feedback",
    "gap_peaks",
    "instructions",
    "like_before",
    "like_columns",
    "renamed",
    "read_reference",
    "places",
    "reference_prompt",
    "simplicity",
    "simplify_prompt",
    "simplify_windows",
    "splice",
    "stretch_request",
    "trim_beams",
    "window_prompt",
    "windows_of",
    "write_frames",
    "write_simplify",
    "write_stretch",
]

Complete = Callable[[str, list[dict]], str]

PROMPT_DIR = Path(__file__).with_name("prompt") / "frames"
PROMPT_VERSION = "7"  # prompt/frames/VERSION
WINDOW_MS = (12000.0, 16000.0)  # a window ends after the longest pause in this range
MAX_ONSETS = 200
LOOKAHEAD_MS = 4000.0
CONTEXT_MS = 4000.0
MAX_CHECKS = 3
REFERENCE_MS = (150.0, 2000.0)  # a reference figure outside this range is not used
BEAM_FLOOR = 0.3  # the phase 14 guard: at least 30 % of 20 or more beamable notes in a group
BEAM_MIN_NOTES = 20
# Prompt 6 (implementation 04, Phase 3): what a whole-song window may leave out and add for the rules of simplicity
CHANGE_SHARE = 0.1  # of the target's notes, at most
CHANGE_MIN = 4  # the limit of a small window
NEAR = 12  # semitones: a note left out keeps a note of its column this near; a note added is this near one
PATTERN_COLUMNS = (
    8  # the columns of the hand before and after an added note that may give its pitch name
)


class SkipWindow(Exception):
    """Raised by ``complete`` when one request cannot be answered (a refusal): that window keeps the algorithm."""


@lru_cache(maxsize=1)
def instructions() -> str:
    """The system prompt (version 5), the same for the reference request and every window."""
    return (PROMPT_DIR / "instructions.md").read_text(encoding="utf-8")


def feedback(errors: list[str]) -> str:
    template = (PROMPT_DIR / "feedback.md").read_text(encoding="utf-8")
    return template.format(errors="\n".join(f"- {e}" for e in errors)).rstrip("\n")


# ------------------------------------------------------------------ the reference figure


def gap_peaks(
    sheet: Sheet, *, most: int = 6, floor: float = 0.03
) -> tuple[list[tuple[float, float]], int]:
    """The peaks of the gaps between the measured onsets of consecutive drawn columns (both hands): ``[(ms, share of the gaps)]``, the
    largest share first, and the number of gaps. A peak is a local maximum of the histogram on a log scale (bins of
    a twelfth of an octave, smoothed); its share counts the gaps within 12 % of its centre."""
    starts: dict[int, float] = (
        {}
    )  # the measured onset of each drawn column (40 ms steps would split a peak)
    for n in sheet.notes:
        on = n.on_ms if n.on_ms is not None else n.frame * FRAME_MS
        starts[n.frame] = min(starts.get(n.frame, on), on)
    gaps = np.diff(np.array([starts[f] for f in sorted(starts)], dtype=float))
    gaps = gaps[(gaps >= FRAME_MS) & (gaps <= 4000)]
    if len(gaps) < 2:
        return [], len(gaps)
    edges = 2 ** np.arange(np.log2(FRAME_MS) - 1 / 24, np.log2(4000) + 1 / 12, 1 / 12)
    hist, _ = np.histogram(gaps, bins=edges)
    smooth = np.convolve(hist, [1, 2, 1], mode="same")
    peaks: list[tuple[float, float]] = []
    for i in np.argsort(-smooth, kind="stable"):
        if smooth[i] == 0:
            break
        if (i > 0 and smooth[i - 1] > smooth[i]) or (
            i + 1 < len(smooth) and smooth[i + 1] > smooth[i]
        ):
            continue
        centre = float(np.sqrt(edges[i] * edges[i + 1]))
        near = gaps[np.abs(gaps / centre - 1) <= 0.12]
        if not len(near) or any(abs(c / centre - 1) <= 0.15 for c, _ in peaks):
            continue
        share = len(near) / len(gaps)
        if share >= floor:
            peaks.append((float(np.median(near)), share))
        if len(peaks) >= most:
            break
    return sorted(peaks, key=lambda p: -p[1]), len(gaps)


def reference_prompt(sheet: Sheet, start: Sheet, sid: str = "song") -> str:
    """The question of the reference figure: the peaks of the gaps and the start of the song (no hands, no
    figures)."""
    peaks, count = gap_peaks(sheet)
    lines = [
        f"- about {round(ms / 10) * 10:g} ms: {share * 100:.0f} % of the gaps"
        for ms, share in peaks
    ]
    bare = Sheet(
        notes=[replace(n, staff=0, figure=None, beam=None) for n in start.notes],
        clefs={1: "G2", 2: "F4"},
        key=start.key,
    )
    return (
        f"# The reference figure of song {sid}\n\n"
        f"## The gaps between onsets\n\nThe time from one onset to the next (any hand) over the whole song, "
        f"{count} gaps; the peaks:\n\n" + "\n".join(lines or ["- (too few onsets)"]) + "\n\n"
        "## The start of the song (the first window, without hands and figures)\n\n```\n"
        + f1.write(bare, mode="frames").strip()
        + '\n```\n\n## Answer\n\nChoose the length of one quarter note in ms, as the section "The reference '
        'figure" of your instructions says. Reply with one block in triple backticks that holds the line '
        "`quarterMs=NNN` and one line `# why: ...`.\n"
    )


_REFERENCE = re.compile(r"quarterMs\s*=\s*([0-9]+(?:\.[0-9]+)?)")


def read_reference(reply: str) -> float | None:
    found = _REFERENCE.findall(reply)
    if not found:
        return None
    q = float(found[-1])
    return q if REFERENCE_MS[0] <= q <= REFERENCE_MS[1] else None


# ------------------------------------------------------------------ windows


def windows_of(
    sheet: Sheet,
    *,
    span: tuple[float, float] = WINDOW_MS,
    max_onsets: int = MAX_ONSETS,
) -> list[tuple[int, int]]:
    """The windows of a frames sheet as ``(first frame, end frame)``, end exclusive. A window starts at its first
    column and ends among the ends from ``span[0]`` to ``span[1]`` after its start (when ``max_onsets`` onsets come
    first, from 75 % of that point): at an end that no beam group of the sheet crosses when one exists, and there
    after the longest pause (the time between two columns, either hand; ties: the later end)."""
    counts = Counter(n.frame for n in sheet.notes)
    cols = sorted(counts)
    spans: dict[tuple[int, int], list[int]] = defaultdict(list)
    for n in sheet.notes:
        if n.beam is not None:
            spans[(n.staff, n.beam)].append(n.frame)
    inside = Counter()  # columns that a beam group crosses (a group goes on after them)
    for fs in spans.values():
        for c in cols[bisect_left(cols, min(fs)) + 1 : bisect_left(cols, max(fs)) + 1]:
            inside[c] += 1
    out: list[tuple[int, int]] = []
    i = 0
    while i < len(cols):
        start, total, j = cols[i], 0, i
        while j < len(cols):
            if j > i and (cols[j] - start) * FRAME_MS > span[1]:
                break
            if j > i and total + counts[cols[j]] > max_onsets:
                break
            total += counts[cols[j]]
            j += 1
        if j >= len(cols):
            out.append((start, cols[-1] + 1))
            break
        reach = (cols[j] - start) * FRAME_MS
        low = span[0] if reach >= span[1] else 0.75 * reach
        cands = [k for k in range(i + 1, j + 1) if (cols[k] - start) * FRAME_MS >= low] or [j]
        k = max(cands, key=lambda k: (-inside[cols[k]], cols[k] - cols[k - 1], k))
        out.append((start, cols[k]))
        i = k
    return out


def _part(sheet: Sheet, a: int, b: int) -> list[Note]:
    return [n for n in sheet.notes if a <= n.frame < b]


def _own_figures(notes: Notes, quarter_ms: float) -> dict[tuple[int, int, int], int]:
    """The figure of each note by the rule with the starting hands, before grace notes: ``(staff, midi, frame)`` ->
    figure (what the input shows; a grace note shows the figure of its own length)."""
    sheet = frames_mod.from_notes(notes)
    assign_figures(sheet, quarter_ms)
    return {(n.staff, n.midi, n.frame): n.figure for n in sheet.notes}


def _shown(
    notes: list[Note],
    *,
    key: int,
    clefs: dict[int, str],
    quarter_ms: float,
    hands: bool,
    figures: dict[tuple[int, int, int], int],
) -> Sheet:
    """Notes as the LLM reads them: no hand (unless ``hands``), the figure of the rule, spelled in ``key``."""
    out = []
    for n in notes:
        step, alter, octave = spell(n.midi, key)
        out.append(
            Note(
                time=None,
                staff=n.staff if hands else 0,
                step=step,
                alter=alter,
                octave=octave,
                figure=figures.get((n.staff, n.midi, n.frame), n.figure),
                frame=n.frame,
            )
        )
    return Sheet(notes=out, clefs=dict(clefs), key=key, quarter_ms=quarter_ms).sort()


def _ranges(sheet: Sheet) -> list[str]:
    out = []
    for staff, name in ((2, "L"), (1, "R")):
        ns = [n for n in sheet.notes if n.staff == staff and not n.covered]
        if not ns:
            out.append(f"{name}: no notes")
            continue
        lo, hi = min(ns, key=lambda n: n.midi), max(ns, key=lambda n: n.midi)
        out.append(
            f"{name}: {spn(lo.step, lo.alter, lo.octave)}-{spn(hi.step, hi.alter, hi.octave)}"
        )
    return out


# ------------------------------------------------------------------ places to check (prompt 6)

RUN_COLUMNS = 6  # a run of fewer columns is no pattern
RUN_SHARE = 0.6  # the shape of the pattern holds at least this share of the run's columns


def _hand_columns(notes: list[Note], staff: int) -> list[tuple[int, list[Note]]]:
    cols: dict[int, list[Note]] = defaultdict(list)
    for n in notes:
        if n.staff == staff and not n.covered:
            cols[n.frame].append(n)
    return [(f, sorted(ns, key=lambda n: n.midi)) for f, ns in sorted(cols.items())]


def _onset(ns: list[Note]) -> float:
    return min(n.on_ms if n.on_ms is not None else n.frame * FRAME_MS for n in ns)


def _shape(ns: list[Note]) -> str:
    keys = sorted({n.midi for n in ns})
    if len(keys) == 1:
        return "single"
    return "octave" if len(keys) == 2 and keys[1] - keys[0] == 12 else "chord"


def _names(ns: list[Note]) -> str:
    return "+".join(spn(n.step, n.alter, n.octave) for n in sorted(ns, key=lambda n: n.midi))


def far_quick(
    notes: list[Note], quarter_ms: float
) -> list[tuple[int, list[Note], list[Note], list[Note]]]:
    """simple.2: the quick columns of one hand (a grace note, or a semicorchea or shorter two figures or more shorter
    than the next column of that hand and sounding less than a corchea before it) with notes more than ``NEAR``
    semitones from every note of that next column, and another note near it (a single quick note stays): ``(frame,
    the quick column, its far notes, the main column)``."""
    out = []
    for staff in (1, 2):
        cols = _hand_columns(notes, staff)
        for (f, quick), (_, main) in zip(cols, cols[1:]):
            fq, fm = quick[0].figure or 0, main[0].figure or 0
            if not (quick[0].grace and not main[0].grace) and (
                fq < 16 or not fm or fq < 4 * fm or _onset(main) - _onset(quick) >= quarter_ms / 2
            ):
                continue
            far = [q for q in quick if min(abs(q.midi - m.midi) for m in main) > NEAR]
            if far and len(far) < len({q.midi for q in quick}):
                out.append((f, quick, far, main))
    return out


def broken_octaves(
    notes: list[Note], quarter_ms: float
) -> list[tuple[int, int, str, list[tuple[int, list[Note]]]]]:
    """simple.1: the runs of one hand (``RUN_COLUMNS`` columns or more of corcheas or shorter, each less than a negra
    after the one before) whose columns are octaves, or single notes, at ``RUN_SHARE`` or more, with columns of the
    other of the two shapes: ``(first frame, last frame, the run's shape, the odd columns)``. Runs of chords are left
    out: the notes of a melody over chords change from one column to the next by themselves."""
    out = []
    for staff in (1, 2):
        cols = [(f, ns) for f, ns in _hand_columns(notes, staff) if not ns[0].grace]
        runs: list[list[tuple[int, list[Note]]]] = []
        for f, ns in cols:
            fast = (ns[0].figure or 0) >= 8
            if fast and runs and runs[-1] and _onset(ns) - _onset(runs[-1][-1][1]) < quarter_ms:
                runs[-1].append((f, ns))
            else:
                runs.append([(f, ns)] if fast else [])
        for run in runs:
            if len(run) < RUN_COLUMNS:
                continue
            shapes = Counter(_shape(ns) for _, ns in run)
            main, count = shapes.most_common(1)[0]
            other = {"octave": "single", "single": "octave"}.get(main)
            odd = [(f, ns) for f, ns in run if _shape(ns) == other]
            if odd and count >= RUN_SHARE * len(run):
                out.append((run[0][0], run[-1][0], main, odd))
    return out


def places(notes: list[Note], quarter_ms: float) -> list[str]:
    """The places of a window the rules of simplicity are about, found by the app (:func:`far_quick`,
    :func:`broken_octaves`), one line each for the window prompt; the hands are the ones the notes have now.
    """
    out = []
    for f, quick, far, main in far_quick(notes, quarter_ms):
        out.append(
            f"- f{f}: {_names(quick)} is quick, just before {_names(main)} at f{main[0].frame} in the same hand; "
            f"{_names(far)} is more than an octave from it (simple.2)"
        )
    for a, b, shape, odd in broken_octaves(notes, quarter_ms):
        what = ", ".join(f"f{f} {_names(ns)}" for f, ns in odd)
        out.append(
            f"- f{a} to f{b}: a run of {'octaves' if shape == 'octave' else 'single notes'} in one hand, with "
            f"{'single notes' if shape == 'octave' else 'octaves'} at {what} (simple.1)"
        )
    return out


def window_prompt(
    *,
    sid: str,
    index: int,
    count: int,
    target: Sheet,
    lookahead: Sheet,
    context: Sheet | None,
    request: str | None = None,
    check: list[str] | None = None,
    fixed: Sheet | None = None,
) -> str:
    """The prompt of window ``index`` (0 = first) of ``count``. ``context`` = the end of the previous answer (with
    its hands and tags), or ``None``. ``request`` = the user's request for one stretch (:func:`write_stretch`): the
    stretch is the target, the sheet before it the context. ``check`` = the places the rules of simplicity are
    about (:func:`places`). ``fixed`` = the other hand of a stretch of one hand (implementation 04, Phase 4): shown
    after the target, never written."""
    lo, hi = min(n.frame for n in target.notes), max(n.frame for n in target.notes)
    if request is None:
        out = [f"# Window {index + 1} of {count} of song {sid} (frames f{lo}-f{hi})"]
        before = "the end of the previous window, as you wrote it"
    else:
        out = [f"# A stretch of song {sid} to write again (frames f{lo}-f{hi})"]
        before = "the sheet just before the stretch, as it is now"
    if context is not None and context.notes:
        out.append(
            f"## Decided context ({before})\n\n```\n"
            + f1.write(context, mode="frames").strip()
            + "\n```\n\nRange of each hand in it: "
            + "; ".join(_ranges(context))
            + "."
        )
    title = (
        "## Target (write all of these notes)"
        if request is None
        else "## Target (this stretch of the sheet as it is now: write it again as the user asks)"
    )
    out.append(title + "\n\n```\n" + f1.write(target, mode="frames").strip() + "\n```")
    if fixed is not None and fixed.notes:
        hand = "left" if fixed.notes[0].staff == 2 else "right"
        out.append(
            f"## The {hand} hand in this stretch (fixed: do not write it, it stays exactly as it is)\n\n```\n"
            + f1.write(fixed, mode="frames").strip()
            + "\n```"
        )
    if request is None and any(n.staff in (1, 2) for n in target.notes):
        # A run again on the numeric truth (``write_frames(hands=True)``, implementation 03, Phase 6): the user's
        # answer is that the LLM may change any hand, the user's moves included.
        out.append(
            "The target shows the current hand of each note (written in an earlier run; the user may have moved "
            "some). Read them as a suggestion: keep the hands that follow the rules, and change any that does not."
        )
    if check:
        out.append(
            "## Places to check (rules of simplicity)\n\nThe app found these places in the target. Look at each one "
            "and apply simple.1 or simple.2 when it makes the sheet simpler to read and to play; the target may "
            "have other places too.\n\n" + "\n".join(check)
        )
    if lookahead.notes:
        out.append(
            "## Look-ahead (do not write these)\n\n```\n"
            + f1.write(lookahead, mode="frames").strip()
            + "\n```"
        )
    if request is not None:
        out.append(request)
    out.append(
        "## Answer\n\nWrite the target in F1 frames with hands, as one block in triple backticks. Start with the "
        "two header lines of the target; the second line may change `key=` or `clefs:` when the passage starts "
        "with another key signature or clef."
        + (
            " End with the `# leave out` and `# add` lines of the notes you change by the rules of simplicity, if "
            "any."
            if request is None
            else ""
        )
    )
    return "\n\n".join(out) + "\n"


# ------------------------------------------------------------------ the checker


def _block(reply: str) -> str:
    """The F1 frames text of a reply: the fenced block that holds it, else the text from 'F1 frames'."""
    for b in re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", reply, re.S):
        if "F1 frames" in b:
            return b[b.find("F1 frames") :]
    i = reply.find("F1 frames")
    return reply[i:] if i >= 0 else reply


def _name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


def _structure(sheet: Sheet) -> list[str]:
    """Beam groups (at most ``frames.MAX_BEAM`` notes, two or more, consecutive notes of one hand), 8va in the
    bass clef, no note four or more ledger lines above its staff (clef.L3 for the left hand in the bass clef, the
    algorithm's hard limit; clef.L5 and clef.6 under 8va otherwise), and ``orn`` after an ornament. Grace notes are a rule of the app, so the prompt does not ask for
    them; a column tagged ``grace`` may sit inside a group, as ``frames.check`` allows."""
    errs: list[str] = []
    for staff, hand in ((1, "R"), (2, "L")):
        cols: dict[int, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff:
                cols[n.frame].append(n)
        frames = sorted(cols)
        members: dict[int, list[int]] = defaultdict(list)
        for i, f in enumerate(frames):
            for b in {n.beam for n in cols[f] if n.beam is not None}:
                members[b].append(i)
        for b, idx in sorted(members.items()):
            where = f"{hand} b{b} at f{frames[idx[0]]}"
            if len(idx) > frames_mod.MAX_BEAM:
                errs.append(
                    f"{where}: a beam group of {len(idx)} notes; a group has at most {frames_mod.MAX_BEAM} "
                    "notes (a chord counts as one): cut it"
                )
            if len(idx) < 2:
                errs.append(f"{where}: a beam group of one note")
            gap = next(
                (
                    i
                    for i in range(idx[0], idx[-1] + 1)
                    if i not in idx and not all(n.grace for n in cols[frames[i]])
                ),
                None,
            )
            if gap is not None:
                errs.append(
                    f"{where}: the group skips the {hand} note at f{frames[gap]} (a group joins consecutive "
                    "notes of one hand)"
                )
        for i, f in enumerate(frames):
            if any(n.covered for n in cols[f]):
                before = [g for g in frames[:i] if not all(n.covered for n in cols[g])]
                if not before or not any(n.ornaments for n in cols[before[-1]]):
                    errs.append(
                        f"{hand} at f{f}: 'orn' with no ornament (tr, mord, turn) before it"
                    )
            if any(n.ottava for n in cols[f]) and frames_mod._clef_at(sheet, staff, f) == "F4":
                errs.append(
                    f"{hand} at f{f}: 8va in the bass clef (never; use the treble clef first)"
                )
        # clef.L3 and clef.6: no note four or more ledger lines above its staff (the first two places of each)
        high = []
        for f in frames:
            clef = frames_mod._clef_at(sheet, staff, f)
            top = max(cols[f], key=lambda n: n.midi)
            # a note already under 8va is not checked: only a 15ma line would lower it more
            if not top.covered and not top.ottava and _ledger(top, clef, 0)[1] >= BASS_LIMIT:
                high.append((f, top, clef))
        for f, top, clef in high[:2]:
            name = spn(top.step, top.alter, top.octave)
            if clef == "F4":
                errs.append(
                    f"{hand} at f{f}: {name} is four or more ledger lines above the bass staff; write it in "
                    "the treble clef (clef.L3)"
                )
            else:
                errs.append(
                    f"{hand} at f{f}: {name} is four or more ledger lines above the treble staff; write it "
                    "under 8va (clef.L5, clef.6)"
                )
        if len(high) > 2:
            errs.append(
                f"{hand}: {len(high) - 2} more notes four or more ledger lines above their staff"
            )
    return errs


_DECLARED = re.compile(r"^\s*#\s*(leave out|add)\s+f(\d+)\s+([A-G][#b]*-?\d+)", re.M)


def declared(text: str) -> tuple[Counter, Counter]:
    """The changes an answer declares in its comment lines (prompt 6, section "Simplicity"): the notes it leaves out
    (``# leave out f1822 G2``) and the notes it adds (``# add f4556 D1``), as ``(frame, midi)`` counts.
    """
    out: dict[str, Counter] = {"leave out": Counter(), "add": Counter()}
    for what, frame, pitch in _DECLARED.findall(text):
        try:
            out[what][(int(frame), pitch_to_midi(*parse_spn(pitch)))] += 1
        except ValueError:
            continue
    return out["leave out"], out["add"]


def simplicity(target: Sheet, answer: Sheet, left: Counter, added: Counter) -> list[str]:
    """The limits of prompt 6 on the notes a whole-song window leaves out and adds (plan section 4.3), as problems.
    A note left out keeps a note of the answer in its column within an octave (its hand still plays there). A note
    added joins a column where its hand plays a note of the target, within an octave of one of them, with the pitch
    name of a note of that column or of the ``PATTERN_COLUMNS`` columns of that hand before and after it. At most
    ``CHANGE_SHARE`` of the target's notes change (``CHANGE_MIN`` at least)."""
    errs: list[str] = []
    for f, m in sorted(left.elements()):
        if not any(n.frame == f and abs(n.midi - m) <= NEAR for n in answer.notes):
            errs.append(
                f"f{f} {_name(m)} is left out and no note of its column stays within an octave of it: leave out "
                "only an extra note of a pattern or the far note of a quick chord, never a whole column of a hand"
            )
    kept = Counter((n.frame, n.midi) for n in target.notes)
    for f, m in sorted(added.elements()):
        note = next(n for n in answer.notes if (n.frame, n.midi) == (f, m))
        hand = sorted(
            {n.frame for n in answer.notes if n.staff == note.staff and kept[(n.frame, n.midi)]}
        )
        here = [
            n.midi
            for n in answer.notes
            if n.frame == f and n.staff == note.staff and kept[(n.frame, n.midi)]
        ]
        if not here:
            errs.append(
                f"f{f} {_name(m)} is added where its hand plays no note of the target: an added note only "
                "completes a column of its hand (the missing note of an octave or of a repeated chord)"
            )
            continue
        i = bisect_left(hand, f)
        around = set(hand[max(0, i - PATTERN_COLUMNS) : i + PATTERN_COLUMNS + 1])
        names = {
            n.midi % 12
            for n in answer.notes
            if n.staff == note.staff and n.frame in around and kept[(n.frame, n.midi)]
        }
        if min(abs(m - x) for x in here) > NEAR or m % 12 not in names:
            errs.append(
                f"f{f} {_name(m)} is added, but it is not the missing note of a pattern: an added note is within "
                "an octave of a note of its column and has the name of a note of that column or of the same "
                "pattern around it"
            )
    changed = sum(left.values()) + sum(added.values())
    most = max(CHANGE_MIN, int(CHANGE_SHARE * len(target.notes)))
    if changed > most:
        errs.append(
            f"the answer leaves out {sum(left.values())} notes and adds {sum(added.values())}, more than {most} "
            "(a tenth of the target): change only the columns that break a pattern and the far notes of quick "
            "chords, and write every other note as it is"
        )
    return errs


def check_answer(
    reply: str,
    target: Sheet,
    *,
    drop: bool = False,
    free: tuple[int, int] | None = None,
    simplify: bool = False,
    hand: int | None = None,
) -> tuple[list[str], Sheet | None]:
    """The problems of a reply for a window (empty: accepted) and the parsed answer. ``drop=True`` (a stretch the
    user asked for, Phase 7) accepts an answer that leaves notes of the target out: they are taken off the sheet.
    ``free=(start, end)`` also accepts notes that are not in the target, at a frame of ``[start, end)`` and a key of
    the piano: they are added to the notes (a changed pitch is a note left out and a note added). ``simplify=True``
    (a whole-song window, prompt 6) accepts the notes the answer declares it leaves out or adds, within the limits
    of :func:`simplicity`; a note missing or added without its comment line is still a problem. ``hand`` (1 or 2:
    a stretch of one hand, implementation 04, Phase 4) refuses a note written in the other hand, which is fixed.
    """
    text = _block(reply)
    if not text.startswith("F1 frames"):
        return ["the answer must be F1 frames (first line 'F1 frames frameMs=40 ...')"], None
    try:
        sheet = f1.read(text)
    except f1.F1Error as exc:
        return [f"parse error: {exc}"], None
    errs: list[str] = []
    no_hand = [n for n in sheet.notes if n.staff not in (1, 2)]
    if no_hand:
        errs.append(
            f"{len(no_hand)} notes without a hand (write them after L: or R:), first at f{no_hand[0].frame}"
        )
    if hand in (1, 2):
        other = [n for n in sheet.notes if n.staff in (1, 2) and n.staff != hand]
        if other:
            mine, theirs = ("R", "left") if hand == 1 else ("L", "right")
            errs.append(
                f"{len(other)} notes are written in the {theirs} hand, first at f{other[0].frame}: the {theirs} "
                f"hand is fixed in this stretch; write only {mine}: notes"
            )
    want = Counter((n.frame, n.midi) for n in target.notes)
    got = Counter((n.frame, n.midi) for n in sheet.notes)

    def show(c: Counter) -> str:
        items = sorted(c.elements())[:8]
        return ", ".join(f"f{f} {_name(m)}" for f, m in items) + (
            " ..." if sum(c.values()) > 8 else ""
        )

    left, added = Counter(), Counter()
    if simplify:
        say_left, say_added = declared(reply)  # inside the block, or just after it
        left, added = (want - got) & say_left, (got - want) & say_added
        if not no_hand:
            errs += simplicity(target, sheet, left, added)
    if want - got - left and not drop:
        errs.append(
            f"{sum((want - got - left).values())} onsets of the target are missing: {show(want - got - left)}"
            + (
                " (a note left out on purpose needs its line '# leave out f... pitch')"
                if simplify
                else ""
            )
        )
    extra = got - want - added
    if free is not None:
        extra = Counter(
            {
                (f, m): k
                for (f, m), k in extra.items()
                if not (free[0] <= f < free[1] and 21 <= m <= 108)
            }
        )
    if extra:
        where = (
            "outside the stretch"
            if free is not None
            else "not in the target (wrong frame or pitch)"
        )
        errs.append(
            f"{sum(extra.values())} onsets are {where}: {show(extra)}"
            + (" (a note added on purpose needs its line '# add f... pitch')" if simplify else "")
        )
    if drop and not sheet.notes:
        errs.append(
            "the answer leaves out every note of the target: keep the notes the user did not ask to take off"
        )
    if not no_hand:
        errs += _structure(sheet)
    return errs, sheet


def beam_floor(sheet: Sheet) -> list[str]:
    """The phase 14 guard, for the new sheet: of the pairs of consecutive notes of one hand that could share a beam
    (both eighths or shorter by the rule's figures, of one figure, no more than an eighth apart), 20 or more, fewer
    than 30 % are joined. A short note followed by a long gap has nothing to join: it is not counted.
    """
    quarter_ms = sheet.quarter_ms or 500.0
    pairs = joined = 0
    for staff in (1, 2):
        cols: dict[int, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff and not n.grace and not n.covered:
                cols[n.frame].append(n)
        seq = [ns for _, ns in sorted(cols.items())]
        for a, b in zip(seq, seq[1:]):
            gap = (
                b[0].on_ms - a[0].on_ms
                if a[0].on_ms is not None and b[0].on_ms is not None
                else None
            )
            if gap is None or a[0].figure != b[0].figure or (a[0].figure or 0) < 8:
                continue
            if figure_of_ms(gap, quarter_ms) < 8:
                continue
            pairs += 1
            joined += a[0].beam is not None and a[0].beam == b[0].beam
    if pairs < BEAM_MIN_NOTES or joined >= BEAM_FLOOR * pairs:
        return []
    return [
        f"only {joined} of {pairs} pairs of consecutive eighths or shorter notes of one figure are joined by a "
        "beam: write the beam groups as the rules ask (b tags in each hand)"
    ]


# ------------------------------------------------------------------ decisions of a window, and the sheet


@dataclass
class Part:
    """The decisions of one window: for each note of the window (the algorithm's sheet, by position) the decided
    note (hand and tags), the clefs and the armadura at its start, and the changes inside it."""

    start: int
    end: int
    source: str  # "llm" | "algorithm"
    notes: dict[int, Note]  # index in the base sheet -> decided note
    clefs: dict[int, str]
    key: int
    clef_changes: list[tuple[int, int, str]] = field(default_factory=list)
    key_changes: list[tuple[int, int]] = field(default_factory=list)
    #: Notes the answer added (prompt 6, the rules of simplicity; a stretch, Phase 7): not in the base sheet.
    added: list[Note] = field(default_factory=list)


def _state_at(clefs, clef_changes, key, key_changes, frame: int) -> tuple[dict[int, str], int]:
    """The clefs and the armadura in force at ``frame`` (changes at or before it)."""
    now = dict(clefs)
    for f, staff, c in sorted(clef_changes, key=lambda c: c[0]):
        if f <= frame:
            now[staff] = c
    k = key
    for f, kk in sorted(key_changes):
        if f <= frame:
            k = kk
    return now, k


def _answer_part(start: int, end: int, base: Sheet, answer: Sheet) -> Part:
    pool: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, n in enumerate(base.notes):
        if start <= n.frame < end:
            pool[(n.frame, n.midi)].append(i)
    notes, added = {}, []
    for n in sorted(answer.notes, key=lambda n: (n.frame, n.midi, n.staff)):
        if pool[(n.frame, n.midi)]:
            notes[pool[(n.frame, n.midi)].pop(0)] = n
        elif start <= n.frame < end and n.staff in (1, 2):
            added.append(n)  # a note the answer added has no place in the base
    return Part(
        start=start,
        end=end,
        source="llm",
        notes=notes,
        clefs=dict(answer.clefs),
        key=answer.key or 0,
        clef_changes=[c for c in answer.clef_changes if start <= c[0] < end],
        key_changes=[k for k in answer.key_changes if start <= k[0] < end],
        added=added,
    )


def _algorithm_part(start: int, end: int, algo: Sheet) -> Part:
    clefs, key = _state_at(algo.clefs, algo.clef_changes, algo.key or 0, algo.key_changes, start)
    return Part(
        start=start,
        end=end,
        source="algorithm",
        notes={i: n for i, n in enumerate(algo.notes) if start <= n.frame < end},
        clefs=clefs,
        key=key,
        clef_changes=[c for c in algo.clef_changes if start < c[0] < end],
        key_changes=[k for k in algo.key_changes if start < k[0] < end],
    )


def placed(base: Sheet, part: Part, quarter_ms: float) -> list[Note]:
    """The notes ``part`` added, with an onset and a length: the onset of the column they join (the first of its
    notes in the base sheet; their frame when no note is there), and the length of the longest note of their hand in
    that column (an octave or a chord completed sounds with it), or of the figure the answer wrote.
    """
    out = []
    for n in part.added:
        column = [
            (base.notes[i], d) for i, d in part.notes.items() if base.notes[i].frame == n.frame
        ]
        hand = [b.len_ms for b, d in column if d.staff == n.staff and b.len_ms]
        on = min((b.on_ms for b, _ in column if b.on_ms is not None), default=n.frame * FRAME_MS)
        length = (
            max(hand) if hand else nominal_ms(n.figure if n.figure in FIGURES else 8, quarter_ms)
        )
        out.append(replace(n, on_ms=on, len_ms=length))
    return out


def one_figure(run: list[int], fig: list[int]) -> list[list[int]]:
    """Cut consecutive columns of a written group into groups of one figure (the user's rule of Phase 2): one
    single note of a figure one step away may open or close a group, never sit inside it. Unlike the algorithm's
    ``proposal.frames._uniform``, the odd note may stand next to a single note of the group's figure, so a
    sixteenth beamed to the eighth after it (a short-long pair, common in pop rhythms) stays one group; the
    algorithm needed two notes of the group's figure for an octave played unevenly, which the grace rule now
    takes."""
    runs: list[list[int]] = []
    for i in run:
        if runs and fig[runs[-1][0]] == fig[i]:
            runs[-1].append(i)
        else:
            runs.append([i])
    groups: list[tuple[list[int], bool]] = []  # (columns, holds an odd note)
    for r in runs:
        if groups:
            members, odd = groups[-1]
            near = abs(steps(fig[r[0]], fig[members[-1]])) == 1
            if not odd and near and len(r) == 1:  # one odd note closes the group
                groups[-1] = (members + r, True)
                continue
            if not odd and near and len(members) == 1:  # one odd note opens this run
                groups[-1] = (members + r, True)
                continue
        groups.append((r, False))
    return [g for g, _ in groups]


def trim_beams(sheet: Sheet) -> Counter:
    """Cut the beam groups of a sheet where the rule's figures break them: no grace note, ornament onset, or
    negra and longer in a group; consecutive notes of one hand; one figure per group with one odd note at an edge
    at most (:func:`one_figure`); two notes or more. Group numbers become unique per hand. Returns the counts.
    """
    why: Counter = Counter()
    counter = 0
    for staff in (1, 2):
        cols: dict[int, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff:
                cols[n.frame].append(n)
        main = [
            (f, ns)
            for f, ns in sorted(cols.items())
            if any(not n.grace and not n.covered for n in ns)
        ]
        fig = [next(n.figure for n in ns if not n.grace and not n.covered) for _, ns in main]
        groups: dict[int, list[int]] = defaultdict(list)
        for i, (_, ns) in enumerate(main):
            beams = Counter(
                n.beam for n in ns if n.beam is not None and not n.grace and not n.covered
            )
            if beams:
                groups[beams.most_common(1)[0][0]].append(i)
        for ns in cols.values():
            for n in ns:
                n.beam = None
        for _, idx in sorted(groups.items(), key=lambda g: g[1][0]):
            why["groups written"] += 1
            keep = [i for i in idx if fig[i] >= 8]
            runs: list[list[int]] = []
            for i in keep:
                if runs and runs[-1][-1] + 1 == i:
                    runs[-1].append(i)
                else:
                    runs.append([i])
            parts = [p for run in runs for p in one_figure(run, fig) if len(p) >= 2]
            if parts == [idx]:
                why["groups kept"] += 1
            elif not parts:
                why["groups removed"] += 1
            else:
                why["groups cut"] += 1
            for p in parts:
                counter += 1
                for i in p:
                    for n in main[i][1]:
                        if not n.grace and not n.covered:
                            n.beam = counter
    why["groups"] = counter
    return why


def beam_pairs(
    sheet: Sheet, pairs: list[tuple[list[Note], list[Note]]], graces: set[tuple[int, int, int]]
) -> int:
    """Two short notes written just before a longer one (``proposal.frames.lengthen_lone``) that a stored sheet held
    as grace notes (``graces``: ``(staff, midi, frame)``; the rule before implementation 04, Phase 2) and that are in
    no beam group: beamed together, when both are corcheas or shorter of one figure or of two figures one step apart
    (:func:`one_figure`). The AI never grouped a grace note, so they would print two flags side by side. Only once:
    a sheet stored again holds them as written notes, and a beam the user takes away later stays away. Returns how
    many pairs were beamed."""
    counter = max((n.beam for n in sheet.notes if n.beam is not None), default=0)
    done = 0
    for first, second in pairs:
        notes = first + second
        figs = (first[0].figure, second[0].figure)
        if any(n.beam is not None or n.grace for n in notes) or min(figs) < 8:
            continue
        if any((n.staff, n.midi, n.frame) not in graces for n in notes):
            continue
        if abs(steps(max(figs), min(figs))) > 1:
            continue
        counter += 1
        for n in notes:
            n.beam = counter
        done += 1
    return done


OTTAVA_JOIN_MS = 2000.0  # two 8va lines of one hand closer than this become one
OTTAVA_LOWEST = 72  # C5: under 8va it is written C4, one ledger line below the treble staff


def join_ottavas(sheet: Sheet) -> int:
    """One 8va line instead of several short ones: two 8va notes of one hand less than ``OTTAVA_JOIN_MS`` apart, in
    the treble clef, with every note between them at C5 or higher (written no lower than C4 under the line), put
    those notes under 8va too. Sonnet marks single high notes (clef.6), which draws one bracket per note. Returns
    how many gaps were joined."""
    joined = 0
    for staff in (1, 2):
        cols: dict[int, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff:
                cols[n.frame].append(n)
        frames = sorted(cols)
        marked = [i for i, f in enumerate(frames) if any(n.ottava == 1 for n in cols[f])]
        for a, b in zip(marked, marked[1:]):
            if b == a + 1 or (frames[b] - frames[a]) * FRAME_MS >= OTTAVA_JOIN_MS:
                continue
            between = [n for f in frames[a + 1 : b] for n in cols[f]]
            treble = all(frames_mod._clef_at(sheet, staff, f) == "G2" for f in frames[a : b + 1])
            if treble and all(n.midi >= OTTAVA_LOWEST and n.ottava == 0 for n in between):
                for n in between:
                    n.ottava = 1
                joined += 1
    return joined


def assemble(
    algo: FramesProposal, parts: list[Part], *, clefs: str = "llm", join: bool = True
) -> tuple[Sheet, dict]:
    """The sheet from the decisions of every window (``parts`` in order, covering the song: the notes of the base
    sheet each part decided, and the notes it added, :func:`placed`; a note of the base no part decided was left
    out), then the rules:
    figures, grace notes, lone short notes written longer, beam groups cut by the figures, spelling.
    ``clefs="rule"`` replaces the windows' clefs and 8va by the algorithm's rule on the decided hands
    (``proposal.frames.clefs_and_ottavas``). ``join=False`` keeps the 8va lines as decided (a stored sheet laid
    again: its lines were joined when it was written, and a line the user took away must not come back). The
    user's marks of a decided note (implementation 03, Phase 7: a finger, a figure set by hand, the grace note
    switch) are kept. Returns the sheet and the counts.
    """
    base = algo.sheet
    quarter_ms = algo.quarter_ms
    out: list[Note] = []
    beam_id: dict[tuple, int] = {}
    clef_changes: list[tuple[int, int, str]] = []
    key_changes: list[tuple[int, int]] = []
    clefs = dict(parts[0].clefs) if parts else dict(base.clefs)
    key = parts[0].key if parts else (base.key or 0)
    graces: set[tuple[int, int, int]] = set()  # the grace notes of a stored sheet laid again
    for k, p in enumerate(parts):
        now, kk = _state_at(clefs, clef_changes, key, key_changes, p.start)
        if k:
            clef_changes += [
                (p.start, st, c) for st, c in sorted(p.clefs.items()) if now.get(st) != c
            ]
            if p.key != kk:
                key_changes.append((p.start, p.key))
        clef_changes += p.clef_changes
        key_changes += p.key_changes
        for i, d in p.notes.items():
            n = base.notes[i]
            if d.grace:
                graces.add((d.staff, n.midi, n.frame))
            b = None
            if d.beam is not None and d.staff in (1, 2):
                b = beam_id.setdefault((k, d.staff, d.beam), len(beam_id) + 1)
            out.append(
                replace(
                    n,
                    staff=d.staff,
                    figure=d.figure if d.fixed else None,
                    grace=None,
                    gslot=0,
                    beam=b,
                    ornaments=tuple(d.ornaments),
                    covered=d.covered,
                    ottava=d.ottava,
                    finger=d.finger,
                    fixed=d.fixed,
                    grace_rule=d.grace_rule,
                )
            )
        for n in placed(base, p, quarter_ms):
            b = None
            if n.beam is not None:
                b = beam_id.setdefault((k, n.staff, n.beam), len(beam_id) + 1)
            out.append(replace(n, figure=None, grace=None, gslot=0, beam=b, fixed=False))
    # one note per hand, key and column (two notes that moved into one hand), the longer kept
    keep: dict[tuple[int, int, int], Note] = {}
    for n in out:
        k3 = (n.staff, n.midi, n.frame)
        if k3 not in keep or (n.len_ms or 0) > (keep[k3].len_ms or 0):
            keep[k3] = n
    sheet = Sheet(
        notes=list(keep.values()),
        clefs=clefs,
        clef_changes=_collapse(clef_changes, clefs),
        key=key,
        key_changes=_collapse_keys(key_changes, key),
    )
    sheet.quarter_ms = quarter_ms
    assign_figures(sheet, quarter_ms)
    for staff in (
        1,
        2,
    ):  # an ornament onset takes the figure of the note it belongs to (it is not drawn)
        last = 8
        for n in sorted(
            (n for n in sheet.notes if n.staff == staff), key=lambda n: (n.frame, n.covered)
        ):
            if n.covered:
                n.figure = last
            else:
                last = n.figure
    info: dict = {"grace columns": find_graces(sheet, quarter_ms)}
    pairs: list[tuple[list[Note], list[Note]]] = []
    info["lengthened columns"] = lengthen_lone(sheet, quarter_ms, pairs=pairs)
    info.update({f"beams: {k}": v for k, v in trim_beams(sheet).items()})
    info["pairs beamed"] = beam_pairs(sheet, pairs, graces)
    respell(sheet)
    if clefs == "rule":
        info.update({f"clefs: {k}": v for k, v in clefs_and_ottavas(sheet).items()})
    elif join:
        info["8va lines joined"] = join_ottavas(sheet)
    for n in sheet.notes:
        n.hand_known = True
    sheet.sort()
    info["problems"] = frames_mod.check(sheet)
    return sheet, info


def _collapse(
    changes: list[tuple[int, int, str]], clefs: dict[int, str]
) -> list[tuple[int, int, str]]:
    """Clef changes in order, without the ones that change nothing (the last one of a column wins)."""
    last: dict[tuple[int, int], str] = {}
    for f, st, c in sorted(changes, key=lambda c: c[0]):
        last[(f, st)] = c
    now = dict(clefs)
    out = []
    for (f, st), c in sorted(last.items()):
        if now.get(st) != c:
            out.append((f, st, c))
            now[st] = c
    return out


def _collapse_keys(changes: list[tuple[int, int]], key: int) -> list[tuple[int, int]]:
    last = dict(sorted(changes))
    out, now = [], key
    for f, k in sorted(last.items()):
        if k != now:
            out.append((f, k))
            now = k
    return out


# ------------------------------------------------------------------ the chain


@dataclass
class WindowLog:
    k: int  # 0-based
    start: int  # first frame
    end: int  # end frame (exclusive)
    status: str = (
        "open"  # "ok" | "failed" | "skipped" (no request: max_windows or after an error) | "error"
    )
    replies: int = 0
    errors: list[list[str]] = field(
        default_factory=list
    )  # the checker's problems of each rejected reply
    note: str = ""  # the exception of a request that could not be made


@dataclass
class FramesSong:
    sheet: Sheet  # the product sheet (F1 frames), valid by ``frames.check`` unless ``info["problems"]``
    text: str
    windows: list[WindowLog]
    algo: FramesProposal  # the algorithm with the same reference figure (the fallback, the input's figures)
    quarter_ms: float
    reference: dict  # {"source": "llm" | "given" | "algorithm", "reply": ..., "estimate": the pulse estimate}
    info: dict
    parts: list[Part]

    def changes(self) -> tuple[list[Note], list[Note]]:
        """The notes the windows left out (of the base sheet, in a window the AI wrote) and the notes they added
        (:func:`placed`), for ``notes.pmn`` (prompt 6, the rules of simplicity)."""
        base = self.algo.sheet
        left, added = [], []
        for p in self.parts:
            if p.source != "llm":
                continue
            left += [
                n
                for i, n in enumerate(base.notes)
                if p.start <= n.frame < p.end and i not in p.notes
            ]
            added += placed(base, p, self.quarter_ms)
        return left, added

    @property
    def summary(self) -> dict:
        return {
            "windows": len(self.windows),
            "ok": sum(w.status == "ok" for w in self.windows),
            "ok_first_check": sum(w.status == "ok" and w.replies == 1 for w in self.windows),
            "failed": sum(w.status == "failed" for w in self.windows),
            "skipped": sum(w.status in ("skipped", "error") for w in self.windows),
            "requests": sum(w.replies for w in self.windows)
            + (1 if self.reference.get("source") == "llm" else 0),
        }


def _context(part: Part, answer: Sheet, start: int) -> Sheet:
    """The end of an accepted answer (its last ``CONTEXT_MS``), with the clefs and armadura in force there."""
    cut = max(part.start, start - int(CONTEXT_MS / FRAME_MS))
    clefs, key = _state_at(part.clefs, part.clef_changes, part.key, part.key_changes, cut)
    notes = [replace(n, grace=None, gslot=0) for n in answer.notes if n.frame >= cut]
    return Sheet(
        notes=notes,
        clefs=clefs,
        key=key,
        clef_changes=[c for c in part.clef_changes if c[0] > cut],
        key_changes=[k for k in part.key_changes if k[0] > cut],
        quarter_ms=answer.quarter_ms,
    ).sort()


def write_frames(
    notes: Notes,
    complete: Complete,
    *,
    sid: str = "song",
    key: int | None = None,
    key_changes: list[tuple[int, int]] | None = None,
    quarter_ms: float | None = None,
    hands: bool = False,
    max_checks: int = MAX_CHECKS,
    guards: bool = True,
    max_windows: int | None = None,
    only: set[int] | None = None,
    simplify: bool = True,
    on_window: Callable[[WindowLog], None] | None = None,
    on_start: Callable[[FramesProposal, list[tuple[int, int]]], None] | None = None,
    on_part: Callable[[WindowLog, Part], None] | None = None,
) -> FramesSong:
    """The new sheet of a part by the LLM. ``notes`` carry the starting hands (the saved hands and the hand split):
    the algorithm uses them for the input's figures and for the fallback. ``hands=True`` shows them to the LLM
    (a run again on the numeric truth, plan section 3.7); by default the LLM reads the notes without hands, as the
    research measured best. ``key`` fixes the armadura of the algorithm (the header of window 1); ``quarter_ms``
    skips the reference request. ``max_windows`` limits the requests (later windows keep the algorithm); ``only``
    asks only the windows of those indexes (0 = first; a test of some passages). ``simplify`` lets the windows leave
    out and add notes for the rules of simplicity (prompt 6, :func:`check_answer`; ``FramesSong.changes``).
    ``on_start(algo, windows)`` is called once the reference figure is known, before the first window request, and
    ``on_part(log, part)`` after each window with its decisions (the piece-by-piece view of the Sheet step, plan
    section 3.6: ``assemble`` of the parts so far, the algorithm's parts for the rest, is the sheet at that moment).
    """
    system = instructions()
    plain = frames_mod.from_notes(notes)
    reference: dict = {}
    if quarter_ms is None:
        from aitu_backend.sheet.proposal import beat

        cols = np.array([n.frame for n in plain.notes])
        midi = np.array([n.midi for n in plain.notes])
        estimate = float(beat.estimate(cols, midi)[0][0])
        reference = {"source": "algorithm", "estimate": estimate}
        first = min(n.frame for n in plain.notes)
        start = Sheet(notes=_part(plain, first, first + int(WINDOW_MS[1] / FRAME_MS)), key=key or 0)
        try:
            reply = complete(
                system, [{"role": "user", "content": reference_prompt(plain, start, sid)}]
            )
            reference["reply"] = reply
            q = read_reference(reply)
            if q is not None:
                quarter_ms, reference["source"] = q, "llm"
        except SkipWindow as exc:
            reference["note"] = str(exc)
        except (
            Exception
        ) as exc:  # noqa: BLE001 (no credits, no network: the algorithm keeps the song)
            reference["note"] = f"{type(exc).__name__}: {exc}"
            reference["stopped"] = True
        if quarter_ms is None:
            quarter_ms = estimate
    else:
        reference = {"source": "given"}
    algo = propose_frames(notes, key=key, key_changes=key_changes, quarter_ms=quarter_ms)
    base = algo.sheet
    wins = windows_of(base)
    if on_start:
        on_start(algo, wins)
    figures = _own_figures(notes, quarter_ms)
    logs: list[WindowLog] = []
    parts: list[Part] = []
    stopped = bool(reference.get("stopped"))
    context: Sheet | None = None
    clefs, kk = dict(base.clefs), base.key or 0
    for k, (a, b) in enumerate(wins):
        log = WindowLog(k=k, start=a, end=b)
        target_notes = _part(base, a, b)
        if (
            stopped
            or (max_windows is not None and k >= max_windows)
            or (only is not None and k not in only)
        ):
            log.status = "skipped"
        else:
            shown = dict(key=kk, clefs=clefs, quarter_ms=quarter_ms, hands=hands, figures=figures)
            target = _shown(target_notes, **shown)
            look = _shown(_part(base, b, b + int(LOOKAHEAD_MS / FRAME_MS)), **shown)
            messages = [
                {
                    "role": "user",
                    "content": window_prompt(
                        sid=sid,
                        index=k,
                        count=len(wins),
                        target=target,
                        lookahead=look,
                        context=context,
                        check=places(target_notes, quarter_ms) if simplify else None,
                    ),
                }
            ]
            errs, answer = ["no reply"], None
            try:
                while log.replies < max_checks:
                    reply = complete(system, messages)
                    log.replies += 1
                    errs, answer = check_answer(reply, target, simplify=simplify)
                    if not errs and guards:
                        trial = _answer_part(a, b, base, answer)
                        sheet, _ = assemble(algo, [trial])
                        errs = beam_floor(sheet)
                    if not errs:
                        break
                    log.errors.append(errs)
                    messages += [
                        {"role": "assistant", "content": reply},
                        {"role": "user", "content": feedback(errs)},
                    ]
                log.status = "failed" if errs else "ok"
            except SkipWindow as exc:
                log.status, log.note = "failed", str(exc)
            except (
                Exception
            ) as exc:  # noqa: BLE001 (the requests stop; the algorithm keeps the rest)
                log.status, log.note = "error", f"{type(exc).__name__}: {exc}"
                stopped = True
        if log.status == "ok" and answer is not None:
            part = _answer_part(a, b, base, answer)
            context = _context(part, answer, b)
        else:
            part = _algorithm_part(a, b, base)
            context = None
        parts.append(part)
        clefs, kk = _state_at(part.clefs, part.clef_changes, part.key, part.key_changes, b)
        logs.append(log)
        if on_part:
            on_part(log, part)
        if on_window:
            on_window(log)
    sheet, info = assemble(algo, parts)
    return FramesSong(
        sheet=sheet,
        text=f1.write(sheet, mode="frames"),
        windows=logs,
        algo=algo,
        quarter_ms=float(quarter_ms),
        reference=reference,
        info=info,
        parts=parts,
    )


# ------------------------------------------------------------------ one stretch, with the user's request (Phase 7)

#: The user's words in a stretch request, at most (the page limits the field to the same).
REQUEST_CHARS = 1000
#: Picked notes named one by one in the request, at most; more are counted.
PICKED_NAMED = 40


def stretch_request(
    instruction: str,
    *,
    staff: int | None = None,
    picked: list[str] | None = None,
    start: int | None = None,
    end: int | None = None,
) -> str:
    """The section of a stretch prompt that says what the user asked (implementation 03, Phase 7, plan task 7.5):
    their words first (the user's rule: they are of the utmost importance for this passage), the purpose behind them
    (a sheet simpler to read and to play, with uniform patterns), what they picked (one hand's notes of the stretch,
    or some of its notes, named ``f120 C5``), and what the answer may change: hands, beams, clefs and 8va, ornaments,
    which notes stay, their pitches, added notes and the figures. ``staff`` (1 or 2) is a stretch of that hand only
    (implementation 04, Phase 4): the target holds its notes, and the other hand is fixed."""
    one = staff in (1, 2)
    if one:
        mine, other = ("right", "left") if staff == 1 else ("left", "right")
        what = (
            f"The user chose the {mine} hand only: the target holds its notes, and the {other} hand, shown apart, "
            f"stays exactly as it is. Write only {'R' if staff == 1 else 'L'}: notes, and keep every note of the "
            f"target in the {mine} hand."
        )
    else:
        what = "The user picked the whole target, both hands."
    if picked:
        named = ", ".join(picked[:PICKED_NAMED]) + (
            f" and {len(picked) - PICKED_NAMED} more" if len(picked) > PICKED_NAMED else ""
        )
        what = (what + " " if one else "") + f"The user picked these notes of the target: {named}."
    words = " ".join(instruction.split())[:REQUEST_CHARS]
    if not words:
        return (
            "## The user's request\n\nThe user asked you to write this stretch of the sheet again, with no words "
            f"of their own. {what} Write the target as you always do; keep every note of it."
        )
    hands = (
        f"write every note in the {mine} hand (the {other} hand is fixed); join or cut beam groups; change clefs "
        "and 8va; add or remove ornaments;\n"
        if one
        else "move notes from one hand to the other; join or cut beam groups; change clefs and 8va; add or remove "
        "ornaments;\n"
    )
    inside = f"f{start} to f{end - 1}" if start is not None and end is not None else "the stretch"
    return (
        "## The user's request: it comes before everything else\n\n"
        "The user is editing this exact passage and wrote an instruction for it. **Their instruction is of the "
        "utmost importance**: it says what they want here, and it overrides your usual choices and the general "
        "rules of your instructions (the hands, the beam groups, the clefs, the ornaments, which notes are written, "
        "their pitches and their figures). Follow it exactly and completely; do not keep the target as it is when "
        f"the instruction asks for a change. {what}\n\nTheir instruction:\n\n> {words}\n\n"
        "**The purpose behind it.** A user who edits a passage almost always wants it **simpler to read and to "
        "play**. Before you write, decide which notes and figures make this passage simplest to read and to play "
        "while doing exactly what the instruction says, and prefer uniform, repeating patterns:\n\n"
        "- apply the instruction to every note of the passage it is about, not only where it is easy;\n"
        "- keep the same pitch for the same role: when octaves become single notes, every note of that line takes "
        "the pitch the octaves keep (if Mi 1 + Mi 2 octaves become Mi 2, a lone Mi 1 of the same line becomes Mi 2 "
        "too), unless the instruction says otherwise;\n"
        '- when the instruction names a figure ("negras"), write that figure everywhere it applies, and leave out '
        "the notes it no longer needs.\n\n"
        "**What you may do to follow it:**\n\n"
        f"- {hands}"
        "- take notes off the sheet: a note of the target that you leave out of your answer is taken off the "
        "sheet;\n"
        f"- change a pitch or add notes: write a note at any frame from {inside} with the pitch you want; it is "
        "added to the notes of the part (the audio does not change). A changed pitch is the old note left out and "
        "the new one written at the same frame;\n"
        "- set figures: the figure you write for a note is the figure the sheet prints. When a note keeps its "
        "figure, write the one the target shows.\n\n"
        f"What you cannot do: write a note outside {inside}. When the instruction asks to keep something (the "
        "rhythm, the figures, the beam groups, a hand), keep it as the target has it. Only the format of the answer "
        "and these limits stay hard rules: a beam group has at most 8 notes, no note four or more ledger lines "
        "above its staff, no 8va in the bass clef."
    )


def _strip_marks(n: Note) -> Note:
    """A note as the LLM may read it: without the user's marks, which the format of the prompt does not have."""
    return replace(n, grace=None, gslot=0, finger=None, fixed=False, grace_rule=None)


def write_stretch(
    current: Sheet,
    notes: Notes,
    complete: Complete,
    *,
    start: int,
    end: int,
    instruction: str = "",
    staff: int | None = None,
    picked: list[tuple[int, int]] | None = None,
    sid: str = "song",
    max_checks: int = MAX_CHECKS,
    guards: bool = True,
) -> tuple[Sheet | None, WindowLog]:
    """Write the columns ``[start, end)`` of ``current`` again with the user's ``instruction`` (implementation 03,
    Phase 7, plan task 7.5): one window conversation whose target is the stretch, both hands, with the hands of
    ``current`` shown as a suggestion; the sheet before it is the decided context and the music after it the
    look-ahead. ``notes`` carry the hands of ``current``. ``staff`` (1 or 2) or ``picked`` (``(frame, midi)`` of
    the notes picked) say what the user selected; with ``staff`` the stretch is of that hand only (implementation
    04, Phase 4): the target holds its notes, the other hand is shown apart, the checker refuses a note in it, and
    :func:`splice` keeps it as it is. Returns the sheet with the stretch spliced in (:func:`splice`;
    not settled: lay it on the notes to run the rules) or ``None`` when no reply was accepted, and the window log.
    A ``complete`` that raises stops at once (the log says why)."""
    quarter_ms = current.quarter_ms or 500.0
    algo = propose_frames(
        notes, key=current.key or 0, key_changes=list(current.key_changes), quarter_ms=quarter_ms
    )
    base = algo.sheet
    if not _part(base, start, end):
        raise ValueError("The stretch holds no notes.")
    clefs, key = _state_at(
        current.clefs, current.clef_changes, current.key or 0, current.key_changes, start
    )
    shown = dict(
        key=key,
        clefs=clefs,
        quarter_ms=quarter_ms,
        hands=True,
        figures=_own_figures(notes, quarter_ms),
    )
    # The target is the stretch as the user sees it (hands, beam groups, clefs, 8va, ornaments): the user's words are
    # about it ("keep the beam groups"). A stretch of one hand holds that hand; the other is shown apart.
    one = staff if staff in (1, 2) else None

    def stretch_of(keep: Callable[[int], bool]) -> Sheet:
        return Sheet(
            notes=[
                _strip_marks(n) for n in current.notes if start <= n.frame < end and keep(n.staff)
            ],
            clefs=clefs,
            key=key,
            clef_changes=[c for c in current.clef_changes if start < c[0] < end and keep(c[1])],
            key_changes=[k for k in current.key_changes if start < k[0] < end],
            quarter_ms=quarter_ms,
        ).sort()

    target = stretch_of(lambda staff: one is None or staff == one)
    if not target.notes:
        raise ValueError("The stretch holds no notes of this hand.")
    fixed = stretch_of(lambda staff: staff != one) if one is not None else None
    drop = bool(" ".join(instruction.split()))
    look = _shown(_part(base, end, end + int(LOOKAHEAD_MS / FRAME_MS)), **shown)
    cut = max(0, start - int(CONTEXT_MS / FRAME_MS))
    before_clefs, before_key = _state_at(
        current.clefs, current.clef_changes, current.key or 0, current.key_changes, cut
    )
    context = Sheet(
        notes=[_strip_marks(n) for n in current.notes if cut <= n.frame < start],
        clefs=before_clefs,
        key=before_key,
        clef_changes=[c for c in current.clef_changes if cut < c[0] < start],
        key_changes=[k for k in current.key_changes if cut < k[0] < start],
        quarter_ms=quarter_ms,
    ).sort()
    names = {
        (n.frame, n.midi): f"f{n.frame} {spn(n.step, n.alter, n.octave)}" for n in target.notes
    }
    request = stretch_request(
        instruction,
        staff=staff,
        picked=[names[p] for p in sorted(set(picked or [])) if p in names] or None,
        start=start,
        end=end,
    )
    messages = [
        {
            "role": "user",
            "content": window_prompt(
                sid=sid,
                index=0,
                count=1,
                target=target,
                lookahead=look,
                context=context,
                request=request,
                fixed=fixed,
            ),
        }
    ]
    system = instructions()
    log = WindowLog(k=0, start=start, end=end)
    errs, answer = ["no reply"], None
    try:
        while log.replies < max_checks:
            reply = complete(system, messages)
            log.replies += 1
            errs, answer = check_answer(
                reply, target, drop=drop, free=(start, end) if drop else None, hand=one
            )
            if not errs and guards:
                sheet, _ = assemble(algo, [_answer_part(start, end, base, answer)])
                errs = beam_floor(sheet)
            if not errs:
                break
            log.errors.append(errs)
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": feedback(errs)},
            ]
        log.status = "failed" if errs else "ok"
    except SkipWindow as exc:
        log.status, log.note = "failed", str(exc)
    except Exception as exc:  # noqa: BLE001 (no credits, no network: the sheet stays as it is)
        log.status, log.note = "error", f"{type(exc).__name__}: {exc}"
    if log.status != "ok" or answer is None:
        return None, log
    return splice(current, answer, start, end, keep=None if one is None else 3 - one), log


def splice(
    current: Sheet, answer: Sheet, start: int, end: int, *, keep: int | None = None
) -> Sheet:
    """``current`` with its columns ``[start, end)`` taken from ``answer``: the notes (hands and tags), the clefs
    and the armadura there; the clefs and the armadura in force at ``end`` come back after it. The user's marks of
    a note (a finger, a figure set by hand, the grace note switch) stay on it: the AI never writes them. ``keep``
    (1 or 2) is a staff that stays as ``current`` has it (the fixed hand of a stretch of one hand): its notes,
    beams and clefs. Not settled: the figures, grace notes and spelling are the rule's work
    (``part_sheet.build.reapply``).
    """
    marks = {(n.frame, n.midi): n for n in current.notes if start <= n.frame < end}
    top = max((n.beam for n in current.notes if n.beam is not None), default=0)
    inside = []
    for n in answer.notes:
        if not start <= n.frame < end or n.staff == keep:
            continue
        own = marks.get((n.frame, n.midi))
        inside.append(
            replace(
                n,
                beam=None if n.beam is None else n.beam + top,
                finger=own.finger if own else None,
                fixed=own.fixed if own else False,
                figure=own.figure if own is not None and own.fixed else n.figure,
                grace_rule=own.grace_rule if own else None,
                on_ms=own.on_ms if own else n.on_ms,
                len_ms=own.len_ms if own else n.len_ms,
            )
        )
    frames = sorted(n.frame for n in current.notes)
    first = frames[0] if frames else start
    after = any(f >= end for f in frames)
    clefs_end, key_end = _state_at(
        current.clefs, current.clef_changes, current.key or 0, current.key_changes, end
    )
    clefs, key = dict(current.clefs), current.key or 0
    clef_changes = [c for c in current.clef_changes if not start <= c[0] < end or c[1] == keep]
    key_changes = [k for k in current.key_changes if not start <= k[0] < end]
    written = {st: c for st, c in answer.clefs.items() if st != keep}
    if start <= first:
        clefs, key = {**clefs, **written}, answer.key or 0
    else:
        clef_changes += [(start, st, c) for st, c in sorted(written.items())]
        key_changes.append((start, answer.key or 0))
    clef_changes += [c for c in answer.clef_changes if start < c[0] < end and c[1] != keep]
    key_changes += [k for k in answer.key_changes if start < k[0] < end]
    if after:
        for st, c in clefs_end.items():
            if not any(f == end and s == st for f, s, _ in clef_changes):
                clef_changes.append((end, st, c))
        if not any(f == end for f, _ in key_changes):
            key_changes.append((end, key_end))
    out = Sheet(
        notes=[n for n in current.notes if not start <= n.frame < end or n.staff == keep] + inside,
        clefs=clefs,
        clef_changes=_collapse(clef_changes, clefs),
        key=key,
        key_changes=_collapse_keys(key_changes, key),
        quarter_ms=current.quarter_ms,
    )
    return carry_extras(current, out).sort()


# ------------------------------------------------------------------ Simplify (implementation 04, Phase 4)

#: One batch of Simplify: about twice a window of a whole run (one hand is less text, and the answer is a few lines).
SIMPLIFY_MS = (24000.0, 32000.0)
SIMPLIFY_ONSETS = 300
#: The end of the previous batch, as simplified, that a batch sees (a whole run sees ``CONTEXT_MS``).
SIMPLIFY_CONTEXT_MS = 8000.0
#: An earlier passage like the batch: columns per n-gram, and the share of the batch's columns it matches at least.
LIKE_GRAM = 4
LIKE_SHARE = 0.3
#: The columns before and after a column that find the same place in the earlier passage like the batch.
SAME_PLACE = 2
HAND_NAMES = {1: "right hand", 2: "left hand", None: "both hands"}


@dataclass
class Change:
    """A note Simplify left out or added, and why (the AI's words)."""

    frame: int
    midi: int
    staff: int
    added: bool
    pitch: str  # as the AI wrote it
    why: str = ""

    def line(self) -> str:
        what = "add" if self.added else "leave out"
        why = f": {self.why}" if self.why else ""
        return f"- f{self.frame} {what} {self.pitch} ({'R' if self.staff == 1 else 'L'}){why}"


@dataclass
class Simplified:
    #: The sheet with the changes, not settled (``part_sheet.build.reapply`` lays it on the notes).
    sheet: Sheet
    changes: list[Change]
    windows: list[WindowLog]
    #: The notes added, with a length (``part_sheet.edits.change_notes``).
    added: list[Note]


def simplify_windows(sheet: Sheet, staff: int | None) -> list[tuple[int, int]]:
    """The batches of Simplify over the notes of one hand (``staff``) or of both (``None``): :func:`windows_of` with
    ``SIMPLIFY_MS``, each ending after a pause of that hand."""
    hand = Sheet(
        notes=[n for n in sheet.notes if staff is None or n.staff == staff],
        clefs=dict(sheet.clefs),
        key=sheet.key,
    )
    return windows_of(hand, span=SIMPLIFY_MS, max_onsets=SIMPLIFY_ONSETS) if hand.notes else []


def _like_columns_of(sheet: Sheet, staff: int | None) -> dict[int, list[int]]:
    """The keys of each column of the hand (or of both), frame -> midis: the columns :func:`like_before` compares."""
    cols: dict[int, list[int]] = defaultdict(list)
    for n in sheet.notes:
        if (staff is None or n.staff == staff) and not n.covered:
            cols[n.frame].append(n.midi)
    return cols


def like_columns(
    sheet: Sheet, staff: int | None, start: int, end: int, like: tuple[int, int]
) -> dict[int, list[int]]:
    """Each column of the batch ``[start, end)`` and the columns at the same place of the earlier passage like it
    (``like``, from :func:`like_before`): the columns of ``like`` with the same ``SAME_PLACE`` columns before and
    after (the same keys), frame -> frames. Found by what surrounds them, not by counting: a repeat with a column
    more or less elsewhere still lines up."""
    cols = _like_columns_of(sheet, staff)
    frames = sorted(cols)
    keys = [tuple(sorted(cols[f])) for f in frames]

    def around(i: int) -> tuple:
        return tuple(keys[i - SAME_PLACE : i] + keys[i + 1 : i + 1 + SAME_PLACE])

    places: dict[tuple, list[int]] = defaultdict(list)
    for i in range(bisect_left(frames, like[0]), bisect_left(frames, like[1])):
        if i >= SAME_PLACE:
            places[around(i)].append(frames[i])
    return {
        frames[i]: places[around(i)]
        for i in range(bisect_left(frames, start), bisect_left(frames, end))
        if i >= SAME_PLACE and places.get(around(i))
    }


def like_before(
    sheet: Sheet, staff: int | None, start: int, end: int, before: int
) -> tuple[int, int] | None:
    """The earlier passage most like the columns ``[start, end)`` of the hand (or both): as many columns, ending
    before the frame ``before``, with the most columns in a run of ``LIKE_GRAM`` columns that the batch also holds
    (the same keys); ``LIKE_SHARE`` of them at least, ties to the latest. A chorus that repeats is found; a
    passage made of the same octave played again matches too, and that is a pattern as well. ``(first frame, end
    frame)``, or ``None``."""
    cols = _like_columns_of(sheet, staff)
    frames = sorted(cols)
    keys = [tuple(sorted(cols[f])) for f in frames]
    i0, i1, last = (bisect_left(frames, f) for f in (start, end, before))
    size = i1 - i0
    if size < 2 * LIKE_GRAM or last < size:
        return None
    want = {tuple(keys[i : i + LIKE_GRAM]) for i in range(i0, i1 - LIKE_GRAM + 1)}
    hit = np.zeros(last, dtype=np.int64)
    for i in range(last - LIKE_GRAM + 1):
        if tuple(keys[i : i + LIKE_GRAM]) in want:
            hit[i : i + LIKE_GRAM] = 1
    sums = np.concatenate([[0], np.cumsum(hit)])
    best = max(range(last - size + 1), key=lambda i: (sums[i + size] - sums[i], i))
    if sums[best + size] - sums[best] < LIKE_SHARE * size:
        return None
    return frames[best], frames[best + size - 1] + 1


def _slice(sheet: Sheet, start: int, end: int, staffs: tuple[int, ...]) -> Sheet:
    """The notes of ``staffs`` in ``[start, end)`` as the LLM reads them (no user's marks), with the clefs and the
    armadura in force at ``start``."""
    clefs, key = _state_at(
        sheet.clefs, sheet.clef_changes, sheet.key or 0, sheet.key_changes, start
    )
    return Sheet(
        notes=[
            _strip_marks(n) for n in sheet.notes if start <= n.frame < end and n.staff in staffs
        ],
        clefs=clefs,
        key=key,
        clef_changes=[c for c in sheet.clef_changes if start < c[0] < end and c[1] in staffs],
        key_changes=[k for k in sheet.key_changes if start < k[0] < end],
        quarter_ms=sheet.quarter_ms,
    ).sort()


def simplify_prompt(
    *,
    sid: str,
    staff: int | None,
    index: int,
    count: int,
    target: Sheet,
    context: Sheet | None,
    lookahead: Sheet | None,
    so_far: list[Change],
    like: Sheet | None = None,
    like_changes: list[Change] | None = None,
    check: list[str] | None = None,
) -> str:
    """The prompt of batch ``index`` (0 = first) of ``count`` of Simplify: the rules of simplicity only, on the notes
    of ``target`` (one hand, or both), the hands and the reading fixed. What the batch sees of the earlier ones (the
    user's request: the batches are auto-regressive): every change so far with its reason (``so_far``), the earlier
    passage most like this one as simplified, with its changes (``like``, :func:`like_before`), and the end of the
    previous batch as simplified (``context``). The answer is the change lines only (:func:`check_simplify`).
    """
    lo, hi = min(n.frame for n in target.notes), max(n.frame for n in target.notes)
    who = HAND_NAMES[staff]
    stays = (
        f" The {HAND_NAMES[3 - staff]} does not change."
        if staff in (1, 2)
        else " No note moves to the other hand."
    )
    out = [
        f"# Simplify the {who} of song {sid}: batch {index + 1} of {count} (frames f{lo}-f{hi})",
        f"The user asked the app to simplify the {who} of the whole song, batch after batch, by the rules of "
        'simplicity only (section "Simplicity": simple.1 uniform patterns, simple.2 the amateur pianist, within '
        "simple.3 and simple.4). The hands, the beam groups, the clefs and the figures are decided and stay as they "
        f"are: you only choose the notes to leave out and to add.{stays}",
        "simple.3 asks to keep the name of each note; here that is a recommendation with one exception. A note may "
        "change its name (one note left out and one added in the same column of a hand) when that makes this "
        "passage the same as the earlier passage like it, which has the new note at the same place; say so in the "
        'reason. Example: "# leave out f1200 A3: the chorus has A2+F3 here every other time" with "# add f1200 F3: '
        'as in the earlier chorus". Without an earlier passage like this one that has it, keep the name.',
    ]
    if index:
        if so_far:
            out.append(
                "## The simplifications so far (the earlier batches of this song)\n\n"
                + "\n".join(c.line() for c in so_far)
                + "\n\nMake the same choices again: where this batch repeats a passage of the song, simplify it the "
                "same way (the same notes added or left out); where an earlier batch kept a pattern as it was, keep "
                "it too."
            )
        else:
            out.append(
                "## The simplifications so far\n\nNone: the earlier batches of this song needed no change."
            )
    if like is not None and like.notes:
        a, b = min(n.frame for n in like.notes), max(n.frame for n in like.notes)
        done = (
            "Its changes:\n\n" + "\n".join(c.line() for c in like_changes)
            if like_changes
            else "It needed no change."
        )
        out.append(
            f"## An earlier passage like this one (f{a}-f{b}, as simplified)\n\n```\n"
            + f1.write(like, mode="frames").strip()
            + f"\n```\n\n{done}"
        )
    if context is not None and context.notes:
        out.append(
            "## Decided context (the end of the previous batch, as simplified)\n\n```\n"
            + f1.write(context, mode="frames").strip()
            + "\n```"
        )
    out.append(
        f"## Target (the {who} of this batch, as the sheet has it now)\n\n```\n"
        + f1.write(target, mode="frames").strip()
        + "\n```"
    )
    if check:
        out.append(
            "## Places to check (rules of simplicity)\n\nThe app found these places in the target. Look at each one "
            "and apply simple.1 or simple.2 when it makes the sheet simpler to read and to play; the target may "
            "have other places too.\n\n" + "\n".join(check)
        )
    if lookahead is not None and lookahead.notes:
        out.append(
            "## Look-ahead (the next notes; do not change them)\n\n```\n"
            + f1.write(lookahead, mode="frames").strip()
            + "\n```"
        )
    out.append(
        "## Answer\n\nWrite only the notes you change, one line each, as one block in triple backticks:\n\n"
        "```\n# leave out f120 G2: the quick G2+G3 before Bb3+D4 makes the hand jump (simple.2)\n"
        "# add f240 D1: D2 alone in a run of D1+D2 octaves (simple.1)\n```\n\n"
        "Each line gives the frame and the pitch of one note, then, after a colon, why in a few words. A note left "
        "out is a note of the target; a note added joins a column of the target where its hand plays. When the "
        "batch needs no change, write the one line `# no change`. Do not write the notes of the target."
    )
    return "\n\n".join(out) + "\n"


_CHANGE = re.compile(r"^\s*#\s*(leave out|add)\s+f(\d+)\s+([A-G][#b]*-?\d+)(.*)$", re.M)
_NO_CHANGE = re.compile(r"#\s*no change", re.I)


def check_simplify(
    reply: str,
    target: Sheet,
    *,
    like: Sheet | None = None,
    aligned: dict[int, list[int]] | None = None,
) -> tuple[list[str], list[Change]]:
    """The problems of a Simplify reply (empty: accepted) and its changes. The reply is the change lines (``# leave
    out f120 G2: why``, ``# add f240 D1: why``) or ``# no change``. A note left out is a note of the target; a note
    added is not, and joins a column of the target, in the hand of the nearest note of that column (Simplify of
    one hand: that hand); then the limits of prompt 6 (:func:`simplicity`). A note whose name changes (a column of
    a hand that loses a note and gains one of a name it did not have) is accepted only when the earlier passage like
    this one (``like``, as simplified) has the new note at the same place (``aligned``: the batch's frame -> its
    frames, :func:`like_columns`): the user's decision after the Phase 4 gallery."""
    lines = _CHANGE.findall(reply)
    if not lines:
        if _NO_CHANGE.search(reply):
            return [], []
        return [
            "write only the change lines ('# leave out f... pitch: why', '# add f... pitch: why'), or the one line "
            "'# no change'"
        ], []
    want = Counter((n.frame, n.midi) for n in target.notes)
    staff_of = {(n.frame, n.midi): n.staff for n in target.notes}
    key = target.key or 0
    errs: list[str] = []
    left, added = Counter(), Counter()
    changes: list[Change] = []
    read = []
    for what, frame, pitch, rest in lines:
        try:
            read.append((what, int(frame), pitch, pitch_to_midi(*parse_spn(pitch)), rest))
        except (ValueError, KeyError, IndexError):
            errs.append(f"f{frame} {pitch}: not a pitch name")
    for what, f, pitch, m, rest in sorted(read, key=lambda r: r[0] != "leave out"):
        why = rest.strip().lstrip(":-–— ").strip()
        if what == "leave out":
            if left[(f, m)] >= want[(f, m)]:
                errs.append(f"f{f} {pitch} is left out, but it is not a note of the target")
                continue
            left[(f, m)] += 1
            changes.append(Change(f, m, staff_of[(f, m)], False, pitch, why))
            continue
        column = [n for n in target.notes if n.frame == f]
        if not column:
            errs.append(
                f"f{f} {pitch} is added where the target has no note: an added note joins a column of the target"
            )
            continue
        if added[(f, m)] or want[(f, m)] > left[(f, m)]:
            errs.append(f"f{f} {pitch} is added, but the target already has it there")
            continue
        added[(f, m)] += 1
        staff = min(column, key=lambda n: (abs(n.midi - m), n.staff)).staff
        changes.append(Change(f, m, staff, True, pitch, why))
    if errs:
        return errs, []
    gone = Counter(left)
    notes = []
    for n in target.notes:
        if gone[(n.frame, n.midi)]:
            gone[(n.frame, n.midi)] -= 1
            continue
        notes.append(n)
    for c in changes:
        if c.added:
            step, alter, octave = spell(c.midi, key)
            notes.append(Note(None, c.staff, step, alter, octave, frame=c.frame))
    answer = Sheet(notes=notes, clefs=dict(target.clefs), key=key).sort()
    errs = simplicity(target, answer, left, added) + renamed(target, changes, like, aligned or {})
    return errs, ([] if errs else changes)


def renamed(
    target: Sheet, changes: list[Change], like: Sheet | None, aligned: dict[int, list[int]]
) -> list[str]:
    """The notes whose name a Simplify answer changes without the earlier passage like this one to back it, as
    problems (see :func:`check_simplify`)."""
    out = []
    gone = {(c.frame, c.staff) for c in changes if not c.added}
    for c in changes:
        if not c.added or (c.frame, c.staff) not in gone:
            continue
        names = {n.midi % 12 for n in target.notes if n.frame == c.frame and n.staff == c.staff}
        if c.midi % 12 in names:
            continue
        same = set(aligned.get(c.frame, ()))
        if like is not None and any(
            n.frame in same and (n.staff, n.midi) == (c.staff, c.midi) for n in like.notes
        ):
            continue
        out.append(
            f"f{c.frame} {c.pitch} takes the place of a note of another name: keep the name of each note "
            "(simple.3), unless the earlier passage like this one has this note at the same place"
        )
    return out


def _changed(
    sheet: Sheet, found: list[Change], lengths: dict[tuple[int, int], float | None]
) -> Sheet:
    """``sheet`` with the changes of one batch: each note added written like the nearest note of its hand in its
    column (figure, beam group, 8va), as long as the longest of them (``lengths``: ``(frame, midi)`` -> ms of the
    notes); each note left out taken off (one at its frame, key and hand)."""
    new = []
    for c in found:
        column = [
            n for n in sheet.notes if n.frame == c.frame and n.staff == c.staff and not n.covered
        ]
        if not c.added or not column:
            continue
        model = min(column, key=lambda n: abs(n.midi - c.midi))
        _, key = _state_at(
            sheet.clefs, sheet.clef_changes, sheet.key or 0, sheet.key_changes, c.frame
        )
        step, alter, octave = spell(c.midi, key)
        length = max((lengths.get((n.frame, n.midi)) or 0 for n in column), default=0) or None
        new.append(
            replace(
                model,
                step=step,
                alter=alter,
                octave=octave,
                grace=None,
                gslot=0,
                ornaments=(),
                finger=None,
                fixed=False,
                grace_rule=None,
                len_ms=length,
            )
        )
    notes = list(sheet.notes)
    for c in found:
        if c.added:
            continue
        place = (c.frame, c.midi, c.staff)
        i = next((i for i, n in enumerate(notes) if (n.frame, n.midi, n.staff) == place), None)
        if i is not None:
            notes.pop(i)
    return replace(sheet, notes=notes + new).sort()


def simplify_feedback(errors: list[str]) -> str:
    """The message after a rejected Simplify reply."""
    return (
        "The checker did not accept your answer:\n"
        + "\n".join(f"- {e}" for e in errors)
        + "\n\nWrite the corrected change lines again, as one block in triple backticks."
    )


def write_simplify(
    current: Sheet,
    notes: Notes,
    complete: Complete,
    *,
    staff: int | None = None,
    sid: str = "song",
    max_checks: int = MAX_CHECKS,
    on_start: Callable[[list[tuple[int, int]]], None] | None = None,
    on_batch: Callable[[WindowLog, Sheet], None] | None = None,
) -> Simplified:
    """Simplify the sheet ``current`` (the user's request after the Phase 3 gallery; plan section 3.5): the rules of
    simplicity only, on one hand (``staff`` 1 or 2) or on both (``None``), batch after batch
    (:func:`simplify_windows`). The hands, the beams, the clefs and the other hand do not change; each batch answers
    the notes it leaves out and adds (:func:`check_simplify`), and sees every change made before it
    (:func:`simplify_prompt`). ``notes`` carry the hands of ``current`` (the lengths of the notes added).
    ``on_start(batches)`` once, ``on_batch(log, sheet)`` after each batch with the sheet of the moment. A batch
    that fails keeps its notes; a ``complete`` that raises another error than :class:`SkipWindow` stops the rest.
    """
    staffs = (1, 2) if staff is None else (staff,)
    quarter_ms = current.quarter_ms or 500.0
    wins = simplify_windows(current, staff)
    if on_start:
        on_start(wins)
    lengths = {(n.frame, n.midi): n.len_ms for n in frames_mod.from_notes(notes).notes}
    system = instructions()
    work = replace(current, notes=list(current.notes))
    changes: list[Change] = []
    logs: list[WindowLog] = []
    stopped = False
    back = int(SIMPLIFY_CONTEXT_MS / FRAME_MS)
    for k, (a, b) in enumerate(wins):
        log = WindowLog(k=k, start=a, end=b)
        found: list[Change] = []
        if stopped:
            log.status = "skipped"
        else:
            target = _slice(current, a, b, staffs)
            like = like_before(current, staff, a, b, max(0, a - back))
            like_sheet = _slice(work, *like, staffs) if like else None
            aligned = like_columns(current, staff, a, b, like) if like else {}
            prompt = simplify_prompt(
                sid=sid,
                staff=staff,
                index=k,
                count=len(wins),
                target=target,
                context=_slice(work, max(0, a - back), a, staffs) if k else None,
                lookahead=_slice(current, b, b + int(LOOKAHEAD_MS / FRAME_MS), staffs),
                so_far=changes,
                like=like_sheet,
                like_changes=[c for c in changes if like and like[0] <= c.frame < like[1]],
                check=places(
                    [n for n in current.notes if a <= n.frame < b and n.staff in staffs], quarter_ms
                ),
            )
            messages = [{"role": "user", "content": prompt}]
            errs = ["no reply"]
            try:
                while log.replies < max_checks:
                    reply = complete(system, messages)
                    log.replies += 1
                    errs, found = check_simplify(reply, target, like=like_sheet, aligned=aligned)
                    if not errs:
                        break
                    log.errors.append(errs)
                    messages += [
                        {"role": "assistant", "content": reply},
                        {"role": "user", "content": simplify_feedback(errs)},
                    ]
                log.status = "failed" if errs else "ok"
            except SkipWindow as exc:
                log.status, log.note = "failed", str(exc)
            except Exception as exc:  # noqa: BLE001 (no credits, no network: the batches done stay)
                log.status, log.note = "error", f"{type(exc).__name__}: {exc}"
                stopped = True
        if log.status == "ok" and found:
            work = _changed(work, found, lengths)
            changes += found
        logs.append(log)
        if on_batch:
            on_batch(log, work)
    added = {(c.frame, c.midi, c.staff) for c in changes if c.added}
    return Simplified(
        sheet=work,
        changes=changes,
        windows=logs,
        added=[n for n in work.notes if (n.frame, n.midi, n.staff) in added],
    )
