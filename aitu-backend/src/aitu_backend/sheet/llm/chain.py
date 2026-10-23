"""The LLM step over a whole song (product core since phase 15): piano matrix notation -> F1 bars sheet.

The same chain as the research harness (``experiments/E07-pop-songs/pop.py``, phases 7 and 14), in memory, with the
model behind one function::

    complete(system: str, messages: list[{"role": "user" | "assistant", "content": str}]) -> str

The product passes a function that calls its LLM (the Anthropic SDK with Sonnet 5.5 by default); the core imports no
SDK. One conversation per window: system = the frozen instructions; user = the window prompt; assistant = the reply
(the F1 bars text in one fenced block); after a rejected answer, user = the feedback with the checker's problems, and
the model writes the whole answer again. At most ``max_checks`` replies per window. A window that fails them all keeps
the algorithm's bars of its frames (``proposal``), and the next window starts after it without context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from aitu_backend.sheet.llm import prompts
from aitu_backend.sheet.llm.guards import guard_errors
from aitu_backend.sheet.llm.song import NextWindow, decided, join, next_window, snap, target_window
from aitu_backend.sheet.llm.windows import answer_text, check, cut_bars, strip_answer
from aitu_backend.sheet.proposal.pipeline import Proposal, propose
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Sheet
from aitu_backend.sheet.sheet.matrix import sheet_from_matrix
from aitu_backend.pmn.notes import Notes

__all__ = ["Complete", "SongSheet", "WindowLog", "frames_of", "write_song"]

Complete = Callable[[str, list[dict]], str]
MAX_CHECKS = 3


@dataclass
class WindowLog:
    k: int  # 0-based
    start: int  # first frame
    end: int  # frame after the target
    first_bar: int
    status: str = "open"  # "ok" | "failed"
    replies: int = 0
    errors: list[list[str]] = field(
        default_factory=list
    )  # the checker's problems of each rejected reply
    kept_until: int | None = None  # first frame of the next window


@dataclass
class SongSheet:
    sheet: Sheet  # the kept bars of every window, joined (bars sheet with frame anchors)
    text: str  # the same as F1 bars with frame anchors
    windows: list[WindowLog]
    algo: Proposal  # the algorithm's sheet (tempo of window 1, fallback of failed windows)

    @property
    def summary(self) -> dict:
        return {
            "windows": len(self.windows),
            "ok": sum(w.status == "ok" for w in self.windows),
            "ok_first_check": sum(w.status == "ok" and w.replies == 1 for w in self.windows),
            "failed": sum(w.status == "failed" for w in self.windows),
            "requests": sum(w.replies for w in self.windows),
        }


def frames_of(notes: Notes, *, key: int = 0) -> Sheet:
    """The song's frames sheet: every onset cell, no hand, key family spelling (what the LLM reads)."""
    bare = Notes.build(
        key=notes.key,
        on_ms=notes.on_ms,
        len_ms=notes.len_ms,
        hand=np.zeros(len(notes.key), np.int8),
    )
    return sheet_from_matrix(bare, key=key)


def write_song(
    notes: Notes,
    complete: Complete,
    *,
    key: int = 0,
    sid: str = "song",
    hand_sheet: Sheet | None = None,
    max_checks: int = MAX_CHECKS,
    guards: bool = True,
    max_windows: int | None = None,
    on_window: Callable[[WindowLog], None] | None = None,
) -> SongSheet:
    """The sheet of a song from its notes (``notes.pmn``) and key signature.

    ``hand_sheet`` (a frames sheet with hands) is the hand split the algorithm uses for the tempo of window 1 and the
    fallback; without it the notes' own hands are used. ``guards`` adds the phase 14 rules to the checker.
    ``on_window`` is called after each closed window (progress, logging)."""
    frames = frames_of(notes, key=key)
    last_frame = max(n.frame for n in frames.notes)
    algo = propose(notes, key=key, hand_sheet=hand_sheet, track=False)
    algo.sheet = snap(algo.sheet, frames)
    system = prompts.instructions()
    win: NextWindow | None = NextWindow(
        start=min(n.frame for n in frames.notes),
        first_bar=1,
        bar_frame=None,
        quarter_frames=algo.quarter_ms / 40.0,
        meter=algo.meter,
    )
    logs: list[WindowLog] = []
    parts: list[Sheet] = []
    context: str | None = None
    while win is not None:
        k = len(logs)
        target, look, end = target_window(frames, win.start, win.quarter_frames, win.meter)
        log = WindowLog(k=k, start=win.start, end=end, first_bar=win.first_bar)
        messages = [
            {
                "role": "user",
                "content": prompts.window_prompt(
                    sid=sid,
                    index=k,
                    target=target,
                    lookahead=look,
                    context=context,
                    first_bar=win.first_bar,
                    bar_frame=win.bar_frame,
                ),
            }
        ]
        answer, sheet, errs = "", None, ["no reply"]
        while log.replies < max_checks:
            reply = complete(system, messages)
            log.replies += 1
            answer = answer_text(
                reply
            )  # the fenced block of the reply (the harness: the answer file)
            errs, sheet = check(answer, target)
            if not errs and guards:
                errs = guard_errors(sheet)
            if not errs:
                break
            log.errors.append(errs)
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": prompts.feedback(errs)},
            ]
        if errs:
            log.status = "failed"
            parts.append(cut_bars(algo.sheet, win.start, end, 0))
            dec, answer, context = None, None, None
        else:
            log.status = "ok"
            dec = decided(
                strip_answer(answer), sheet, start=win.start, end=end, last=end > last_frame
            )
            context = dec.kept_text.strip() + "\n"
            parts.append(f1.read(context))
            log.kept_until = dec.next_start
        logs.append(log)
        if on_window:
            on_window(log)
        win = next_window(win, dec, end, answer, last_frame=last_frame)
        if max_windows and len(logs) >= max_windows:
            win = None
    sheet = join(parts)
    return SongSheet(
        sheet=sheet, text=f1.write(sheet, mode="bars", anchors=True), windows=logs, algo=algo
    )
