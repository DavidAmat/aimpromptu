"""Sonnet writes the sheet of a part in the background, window by window (implementation 03, Phase 5; plan 3.6).

:func:`start` submits one job per part (key ``sheet-llm:<part>``; a second start returns the running one). The job:

1. reads the notes with their starting hands (``pipeline.starting_hands``) and runs the LLM step of Phase 4
   (``sheet.llm.frames.write_frames``) with GPT-6.1 Terra at medium (``sheet_llm.OpenAIComplete``; Sonnet 5.5 until
   implementation 04-3, Phase 5);
2. keeps the sheet of the moment in memory (:class:`LiveRun`): the reference request first (the page shows the
   sheet it had, its first segment being improved), then the algorithm with Sonnet's reference figure, then each
   window's decisions as it comes back (``assemble`` of the parts so far and the algorithm's parts for the rest);
3. sends an ``event: sheet`` message on the job's stream at each of those moments, so the page reads the sheet again;
4. at the end writes the hands of the sheet into ``notes.pmn`` (the numeric truth, plan section 3.7; the hands that
   were saved before go to the part's history first), with the notes the windows left out and added for the rules
   of simplicity (implementation 04, Phase 3: one step of undo, ``edits.record_run``), and the sheet into
   ``sheet.f1`` (:mod:`.store`). When no
   window was written by Sonnet (no credits, no network), the hands stay as they were and ``sheet.f1`` keeps the
   algorithm's sheet, so the page does not start again by itself; it says nothing alarming (plan section 3.8).

:func:`start_level` writes the song, or a range, again at a level (implementation 04-3, Phase 4): the plan of the
song, then batches that see the batches before them (``sheet.llm.levels.write_level``); the notes it left out, added
and moved to the other hand are one step of undo (``edits.apply_level``). A level of the whole sheet runs in a new
project, the level copy (``library.flow.level_copy``), made by the route before the job starts.

:func:`start_stretch` writes one stretch again with the user's words (implementation 03, Phase 7), of both hands or
of one (implementation 04, Phase 4: the other hand fixed). :func:`start_simplify` simplifies one hand, or both, over
the whole song, batch after batch (implementation 04, Phase 4): the notes it leaves out and adds are one step of undo.

The notes may change while Sonnet works (the Notes step). The job then stores what it wrote for the notes it read,
without touching the hands, and the page lays it on the current notes (``build.reapply``). A part deleted while Sonnet
works stops the requests at the next one (:class:`PartGone`): no credits are spent on a project that is gone.
"""

from __future__ import annotations

import importlib.util
import threading
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np

from aitu_backend.editing import history
from aitu_backend.pmn import events_file
from aitu_backend.pmn.notes import HAND_LEFT, HAND_RIGHT
from aitu_backend.progress import BaseProgress
from aitu_backend.sheet.llm.frames import (
    PROMPT_VERSION,
    Complete,
    Part,
    WindowLog,
    _algorithm_part,
    assemble,
    simplify_windows,
    windows_of,
    write_frames,
    write_simplify,
    write_stretch,
)
from aitu_backend.sheet.proposal.frames import FramesProposal
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import carry_extras
from aitu_backend.transcription import jobs, pipeline

from . import build, edits, store

__all__ = [
    "Busy",
    "LiveRun",
    "available",
    "commit",
    "costs",
    "job_of",
    "live",
    "start",
    "start_level",
    "start_simplify",
    "start_stretch",
]

#: The job key of a part: one AI run at a time per part.
KEY = "sheet-llm:{}"
#: The name of the stream's messages (an ``EventSource`` listener of that name receives them).
EVENT = "sheet"
#: US dollars and seconds for the cost and the time the dialog shows before a run, measured with GPT-6.1 Terra at
#: medium (implementation 04-3, Phase 5, on the user's song of 1.3 minutes: a whole run of 7 requests $0.064 in 102 s,
#: Simplify of both hands in 3 batches $0.038 in 46 s, a stretch $0.024 in 26 s): the first request of a run writes
#: the instructions into the cache, then each window of a whole run (the reference request too), each batch of
#: Simplify (both hands count twice for the money, once for the time), a stretch.
USD_CACHE = 0.01
USD_WINDOW = 0.008
USD_BATCH = 0.005
USD_STRETCH = 0.015
SECONDS_WINDOW = 15
SECONDS_BATCH = 15
SECONDS_STRETCH = 30
#: A level run uses GPT-6.1 Terra at medium effort (implementation 04-3, Phase 5: the user's decision of 2026-10-30,
#: after the comparison with Sonnet 5.5 on 16 cases). Measured there: the plan of the song about $0.012 and 8 s; a
#: batch with all its replies (1.9 on average) about $0.023 and 41 s. The estimate the dialog shows rounds them up.
MODEL = "gpt-6.1-terra"
EFFORT = "medium"
LEVEL_MODEL, LEVEL_EFFORT = MODEL, EFFORT
USD_LEVEL_PLAN = 0.015
USD_LEVEL_BATCH = 0.025
SECONDS_LEVEL_PLAN = 10
SECONDS_LEVEL_BATCH = 45


def available() -> bool:
    """Whether the AI can be asked: an OpenAI key (the environment, or ``.env``) and the SDK installed. Every AI run
    uses GPT-6.1 Terra since implementation 04-3, Phase 5 (the user, 2026-10-30)."""
    from aitu_backend.sheet_llm import _openai_key  # noqa: PLC0415

    return bool(_openai_key()) and importlib.util.find_spec("openai") is not None


#: The level routes ask this one; the same check as every run since all of them use the same model.
level_available = available


def _complete(part_id: str, kind: str) -> Any:
    """The ``complete`` function of a run: GPT-6.1 Terra at medium effort, one cache key per part and kind of run."""
    from aitu_backend.sheet_llm import OpenAIComplete  # noqa: PLC0415 - the SDK only when it is used

    return OpenAIComplete(model=MODEL, effort=EFFORT, cache_key=f"{part_id}|{kind}")


def _level_complete(part_id: str, level: Any) -> Any:
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    return _complete(part_id, levels.level_name(level))


class PartGone(RuntimeError):
    """The part was deleted while Sonnet wrote its sheet: the chain stops asking, nothing is stored."""


def job_of(part_id: str) -> jobs.Job | None:
    return jobs.active(KEY.format(part_id))


@dataclass
class LiveRun:
    """The sheet of a part while Sonnet writes it."""

    part_id: str
    #: The sheet the page showed when the job started, and its segments: what is drawn during the reference request.
    before: str
    provisional: list[tuple[int, int]]
    algo: FramesProposal | None = None
    windows: list[tuple[int, int]] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    #: The user's own marks of the sheet before the run (fingers, figures set by hand, the grace note switch):
    #: kept on the sheet the AI writes (Phase 7).
    marks: dict = field(default_factory=dict)
    #: The sheet before the run: its titles, lyrics and settings stay on the sheet of the moment (Phase 8).
    extras: Any = None
    #: Simplify (implementation 04, Phase 4): the batches done; the others are ``working`` and ``waiting``.
    done: int = 0
    #: The hand the AI writes (1 right, 2 left) when it writes one hand only, Simplify or a stretch; the page veils
    #: only that staff. ``None``: both hands.
    staff: int | None = None
    _text: tuple[int, str] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def advanced(self, text: str) -> None:
        """One more batch of Simplify is done: ``text`` is the sheet now."""
        with self._lock:
            self.before, self.done = text, self.done + 1

    def started(self, algo: FramesProposal, windows: list[tuple[int, int]]) -> None:
        with self._lock:
            self.algo, self.windows, self._text = algo, list(windows), None

    def decided(self, part: Part) -> None:
        with self._lock:
            self.parts.append(part)

    def text(self) -> str:
        """The F1 frames text of the sheet now."""
        with self._lock:
            algo, parts, windows = self.algo, list(self.parts), list(self.windows)
            cached = self._text
        if algo is None:
            return self.before
        if cached is not None and cached[0] == len(parts):
            return cached[1]
        rest = [_algorithm_part(a, b, algo.sheet) for a, b in windows[len(parts) :]]
        sheet, _ = assemble(algo, build.with_marks(parts + rest, self.marks))
        if self.extras is not None:
            carry_extras(self.extras, sheet)
        text = f1.write(sheet, mode="frames")
        with self._lock:
            self._text = (len(parts), text)
        return text

    def segments(self) -> list[tuple[int, int, str]]:
        """Each segment and its state: ``llm`` or ``algorithm`` (decided), ``working`` (at Sonnet), ``waiting``."""
        with self._lock:
            if self.algo is None:
                return [
                    (a, b, "llm" if k < self.done else "working" if k == self.done else "waiting")
                    for k, (a, b) in enumerate(self.provisional)
                ]
            out = []
            for k, (a, b) in enumerate(self.windows):
                if k < len(self.parts):
                    out.append((a, b, "llm" if self.parts[k].source == "llm" else "algorithm"))
                else:
                    out.append((a, b, "working" if k == len(self.parts) else "waiting"))
            return out


_live: dict[str, LiveRun] = {}
_live_lock = threading.Lock()


def live(part_id: str) -> LiveRun | None:
    with _live_lock:
        return _live.get(part_id)


def start(part_id: str, *, complete: Callable[[], Complete] | None = None) -> jobs.Job:
    """Start the AI on a part, or return the run already going. ``complete`` makes the ``complete`` function
    (tests); by default GPT-6.1 Terra with the key of ``.env`` (:func:`_complete`)."""
    existing = job_of(part_id)
    if existing is not None:
        return existing

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes to write a sheet from.")
        header = stored.header
        store.taken(part_id)
        notes = pipeline.starting_hands(part_id)
        before = build.current(part_id)
        # A run again on a sheet the AI enhanced shows the current hands, the user's moves among them, as a
        # suggestion the AI may change (the user's answer of Phase 6, plan section 3.7). A first run reads the notes
        # without hands: the hands are then the hand split's, and the research found the LLM copies the hands it is
        # shown, errors included.
        shown = before.record is not None and before.record.enhanced
        drawn_before = f1.read(before.text)
        marks = build.user_marks(drawn_before)
        # A reference figure the user named with Transpose figures stays (rule 5): no reference request then. So does
        # the song's on the sheets of a passage of it (Record in Sheet, Phase 8B: the Current and the takes read alike).
        named = before.record is not None and before.record.reference in ("user", "song")
        run = LiveRun(
            part_id, before.text, build.windows(drawn_before), marks=marks, extras=drawn_before
        )
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _complete(part_id, "whole")
            reporter.send(EVENT, {"phase": "reference"})

            def on_start(algo: FramesProposal, windows: list[tuple[int, int]]) -> None:
                run.started(algo, windows)
                reporter.send(EVENT, {"phase": "windows", "done": 0, "total": len(windows)})

            def on_part(log: WindowLog, part: Part) -> None:
                run.decided(part)
                reporter.send(
                    EVENT,
                    {
                        "phase": "window",
                        "done": log.k + 1,
                        "total": len(run.windows),
                        "status": log.status,
                    },
                )

            def asked(system: str, messages: list[dict]) -> str:
                # A part deleted while Sonnet works (its project, or a check's temporary copy): no more requests.
                if not pipeline.has_events(part_id):
                    raise PartGone("The part was deleted while Sonnet wrote its sheet.")
                return ask(system, messages)

            song = write_frames(
                notes,
                asked,
                sid=part_id[:8],
                hands=shown,
                quarter_ms=drawn_before.quarter_ms if named else None,
                on_start=on_start,
                on_part=on_part,
            )
            if not pipeline.has_events(part_id):
                return {
                    "source": "gone",
                    "windows": 0,
                    "usd": round(float(getattr(ask, "usd", 0.0) or 0.0), 4),
                }
            calls = getattr(ask, "calls", [])  # the requests made, with their cost
            sources = [part.source for part in song.parts]
            sheet, text = song.sheet, song.text
            if marks:
                # The user's own marks stay (the user's answer of Phase 7); the AI's kinds are its new ones.
                sheet, _ = assemble(song.algo, build.with_marks(song.parts, marks))
            # So do the titles, the lyrics and the sheet's own settings (Phase 8).
            sheet = carry_extras(drawn_before, sheet)
            text = f1.write(sheet, mode="frames")
            record = store.Record(
                source=(
                    "llm"
                    if sources and all(s == "llm" for s in sources)
                    else "mixed" if "llm" in sources else "algorithm"
                ),
                windows=[[p.start, p.end, p.source] for p in song.parts],
                quarter_ms=song.quarter_ms,
                reference=(
                    before.record.reference
                    if named and before.record
                    else song.reference.get("source")
                ),
                model=getattr(ask, "model", None),
                prompt=PROMPT_VERSION + ("+hands" if shown else ""),
                usd=float(getattr(ask, "usd", 0.0) or 0.0),
                requests=len(calls),
                written=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                note=next((w.note for w in song.windows if w.note), None)
                or song.reference.get("note"),
                edited=bool(marks) or named,
            )
            commit(part_id, sheet, text, record, header.notes_revision, changes=song.changes())
            reporter.send(EVENT, {"phase": "saved", "source": record.source})
            return {
                "source": record.source,
                "windows": len(song.parts),
                "usd": round(record.usd, 4),
            }
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return jobs.submit(work, key=KEY.format(part_id), describe=lambda result: dict(result or {}))


def commit(
    part_id: str,
    sheet: Any,
    text: str,
    record: store.Record,
    notes_revision: int,
    *,
    changes: tuple[list[Any], list[Any]] | None = None,
) -> None:
    """Write the hands of the sheet into ``notes.pmn`` and the sheet into ``sheet.f1``, under the part's lock.
    ``changes`` = the notes the run left out and added (``FramesSong.changes``): marked removed and written into
    ``notes.pmn`` too (``edits.change_notes``), as one step of undo; the stored sheet is laid on the new notes.
    """
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            return
        header = stored.header
        before = store.load(part_id)
        earlier = before.record if before is not None and before.record.enhanced else None
        if earlier is not None and record.source != "llm":
            # Enhanced again, and the run did not finish every window (no credits, no network): the sheet the AI
            # wrote before stays whole, with its mark, rather than a sheet with some windows of the algorithm.
            earlier.note = record.note or "The new run did not finish; the earlier one is kept."
            store.save(part_id, before.text, earlier)
            build.forget(part_id)
            return
        record.runs = (earlier.runs if earlier is not None else 0) + (1 if record.enhanced else 0)
        if header.notes_revision != notes_revision:
            # The notes changed while Sonnet worked: keep its reading, lay it on the new notes when drawn.
            record.hands_revision = None
            store.save(part_id, text, record)
            edits.forget(part_id)
            return
        gone: dict[int, tuple[bool, bool]] = {}
        plain = text
        if record.source != "algorithm":
            left, added = changes or ([], [])
            if left or added:
                quarter = record.quarter_ms or 500.0
                gone = edits.change_notes(stored, {(n.frame, n.midi) for n in left}, added, quarter)
                record.left_out = sum(1 for _, now in gone.values() if now)
                record.added = len(gone) - record.left_out
            notes = events_file.notes_from_events(stored.events)
            hands = build.hands_of_sheet(sheet, notes)
            changed = [
                event
                for event in stored.events
                if event.id in hands and (event.hand != hands[event.id] or event.hand_guessed)
            ]
            for event in changed:
                event.hand = hands[event.id]
                event.hand_guessed = False
            if changed or gone:
                if header.hands_notes_revision > 0:
                    # The saved hands were decided before (Predict hands and the user's corrections): kept.
                    history.snapshot_notes(
                        part_id, reason="The AI wrote the hands of the sheet again"
                    )
                saved = pipeline.save_edit(
                    part_id,
                    stored.events,
                    stored.duration_seconds,
                    stored.title,
                    before=header,
                    notes_changed=bool(gone),
                    hands_changed=bool(changed),
                )
                header = saved.header
            if gone:
                # The sheet on the new notes (a column whose first note went may move by a frame), and, for undo, on
                # the notes without the run's changes.
                text = f1.write(
                    build.reapply(sheet, pipeline.starting_hands(part_id)), mode="frames"
                )
                undone = deepcopy(stored.events)
                for event in undone:
                    if event.id in gone:
                        event.removed = gone[event.id][0]
                notes = edits.starting(part_id, events_file.notes_from_events(undone))
                plain = f1.write(build.reapply(sheet, notes), mode="frames")
        record.hands_revision = header.hands_revision
        store.save(part_id, text, record)
        # The AI wrote the hands and the sheet again: the steps of undo and redo start again, with the notes it left
        # out and added as the first one.
        edits.record_run(part_id, gone, plain, text)
    build.forget(part_id)


class Busy(RuntimeError):
    """The AI already works on this part (a whole run, or another stretch)."""


def start_stretch(
    part_id: str,
    *,
    start: int,
    end: int,
    instruction: str = "",
    staff: int | None = None,
    picked: list[str] | None = None,
    complete: Callable[[], Complete] | None = None,
) -> jobs.Job:
    """The AI writes the columns ``[start, end)`` of the part's sheet again with the user's words (Phase 7, plan
    task 7.5): one window request (``sheet.llm.frames.write_stretch``), the hands of the sheet now shown as a
    suggestion. While it works the stretch is the one ``working`` segment of the page (its pale veil) and nothing can
    be edited (same job key as a whole run); its answer is stored as one step (``edits.apply_stretch``), or nothing
    when no reply was accepted (the summary of the job's ``done`` message says ``failed``). ``staff`` (1 or 2) or
    ``picked`` (the refs ``"<frame>:<midi>"`` of the notes picked) say what the user selected; with ``staff`` the
    stretch is of that hand only, and the other hand stays as it is (implementation 04, Phase 4)."""
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        notes_revision = stored.header.notes_revision
        drawn, current, notes = _as_drawn(part_id)
        run = LiveRun(part_id, drawn.text, [(start, end)], staff=staff if staff in (1, 2) else None)
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _complete(part_id, "stretch")
            reporter.send(EVENT, {"phase": "stretch", "start": start, "end": end})

            def asked(system: str, messages: list[dict]) -> str:
                if not pipeline.has_events(part_id):
                    raise PartGone(
                        "The part was deleted while the AI wrote a stretch of its sheet."
                    )
                return ask(system, messages)

            places = [p for p in (_place(ref) for ref in picked or []) if p is not None]
            sheet, log = write_stretch(
                current,
                notes,
                asked,
                start=start,
                end=end,
                instruction=instruction,
                staff=staff,
                picked=places or None,
                sid=part_id[:8],
            )
            usd = float(getattr(ask, "usd", 0.0) or 0.0)
            requests = len(getattr(ask, "calls", []))
            if sheet is None:
                return {"stretch": "failed", "usd": round(usd, 4), "note": log.note or None}
            words = " ".join(instruction.split())
            done = edits.apply_stretch(
                part_id,
                sheet,
                notes_revision=notes_revision,
                start=start,
                end=end,
                words=words,
                usd=usd,
                requests=requests,
                model=getattr(ask, "model", None),
                staff=staff,
            )
            reporter.send(EVENT, {"phase": "saved"})
            return {"stretch": "ok" if done else "stale", "usd": round(usd, 4)}
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return jobs.submit(work, key=KEY.format(part_id), describe=lambda result: dict(result or {}))


def _as_drawn(part_id: str) -> tuple[build.Drawn, Any, Any]:
    """The sheet drawn now, read, and the notes with the hands it draws (what the AI is shown)."""
    drawn = build.current(part_id)
    current = f1.read(drawn.text)
    notes = pipeline.starting_hands(part_id)
    side = build.hands_of_sheet(current, notes)
    code = {"right": HAND_RIGHT, "left": HAND_LEFT}
    notes.hand = np.array(
        [code.get(side.get(int(i), ""), h) for i, h in zip(notes.id, notes.hand)], dtype=np.int8
    )
    return drawn, current, notes


HANDS = {"right": 1, "left": 2, "both": None}


def start_simplify(
    part_id: str, *, hand: str, complete: Callable[[], Complete] | None = None
) -> jobs.Job:
    """The AI simplifies the ``hand`` (``right``, ``left`` or ``both``) of the part's sheet over the whole song
    (implementation 04, Phase 4; plan section 3.5): the rules of simplicity only, batch after batch, each batch seeing
    the changes made before it (``sheet.llm.frames.write_simplify``). While it works the page shows the sheet of the
    moment, its batches as segments (done, ``working``, ``waiting``), and nothing can be edited (same job key as a
    whole run). The notes it left out and added are stored at the end as one step (``edits.apply_simplify``). The
    summary of the job's ``done`` message: ``simplify`` (``ok``, ``none`` when nothing changed, ``stale`` when the
    notes changed meanwhile, ``failed`` when no batch was answered), ``hand``, ``added``, ``leftOut``, ``usd``.
    """
    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}.")
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    if not simplify_windows(f1.read(build.current(part_id).text), HANDS[hand]):
        raise ValueError("This hand has no notes.")

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        notes_revision = stored.header.notes_revision
        drawn, current, notes = _as_drawn(part_id)
        staff = HANDS[hand]
        run = LiveRun(part_id, drawn.text, simplify_windows(current, staff), staff=staff)
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _complete(part_id, "simplify")

            def asked(system: str, messages: list[dict]) -> str:
                if not pipeline.has_events(part_id):
                    raise PartGone("The part was deleted while the AI simplified its sheet.")
                return ask(system, messages)

            def on_batch(log: WindowLog, sheet: Any) -> None:
                run.advanced(f1.write(sheet, mode="frames"))
                reporter.send(
                    EVENT,
                    {
                        "phase": "batch",
                        "done": log.k + 1,
                        "total": len(run.provisional),
                        "status": log.status,
                    },
                )

            reporter.send(EVENT, {"phase": "simplify", "total": len(run.provisional)})
            out = write_simplify(
                current, notes, asked, staff=staff, sid=part_id[:8], on_batch=on_batch
            )
            usd = float(getattr(ask, "usd", 0.0) or 0.0)
            summary: dict[str, Any] = {"hand": hand, "usd": round(usd, 4), "added": 0, "leftOut": 0}
            note = next((w.note for w in out.windows if w.note), None)
            if note:
                summary["note"] = note
            if not pipeline.has_events(part_id):
                return {**summary, "simplify": "gone"}
            if out.windows and not any(w.status == "ok" for w in out.windows):
                return {**summary, "simplify": "failed"}
            counts = edits.apply_simplify(
                part_id,
                out.sheet,
                notes_revision=notes_revision,
                hand=hand,
                left={(c.frame, c.midi) for c in out.changes if not c.added},
                added=out.added,
                usd=usd,
                requests=len(getattr(ask, "calls", [])),
                model=getattr(ask, "model", None),
                lines=[c.line() for c in out.changes],
            )
            reporter.send(EVENT, {"phase": "saved"})
            if counts is None:
                return {**summary, "simplify": "stale"}
            changed = counts["added"] + counts["leftOut"]
            return {**summary, **counts, "simplify": "ok" if changed else "none"}
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return jobs.submit(work, key=KEY.format(part_id), describe=lambda result: dict(result or {}))


LEVEL_LABELS = {"both": "both hands", "right": "the right hand", "left": "the left hand"}


def start_level(
    part_id: str,
    *,
    level: str | dict[str, str],
    hand: str,
    start: int | None = None,
    end: int | None = None,
    patterns: list[str] | None = None,
    words: str = "",
    complete: Callable[[], Complete] | None = None,
) -> jobs.Job:
    """The AI writes the ``hand`` (``right``, ``left`` or ``both``) of the part's sheet again at ``level`` (one level,
    or one per hand: ``{"right": "hard", "left": "medium"}``), over the whole song or over ``[start, end)`` (a range),
    with the ``patterns`` selected in the catalog and the user's ``words`` (implementation 04-3, Phase 4; plan
    sections 5.4 and 5.8). A hand with no pattern selected or named gets the patterns of its level used when none is
    selected (``levels.run_refs``). While it works the page shows the sheet of the moment, its batches as segments;
    the end stores it as one step (``edits.apply_level``). The summary of the job's ``done`` message: ``level``
    (``ok``, ``failed`` when no batch was accepted, ``stale`` when the notes changed meanwhile, ``gone``), ``batches``
    and ``total``, ``usd``."""
    from aitu_backend.sheet.levels.grid import song_grid  # noqa: PLC0415
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}.")
    levels.hand_levels(level)
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    staffs = (1, 2) if HANDS[hand] is None else (HANDS[hand],)
    if not levels.level_windows(f1.read(build.current(part_id).text), staffs, start, end):
        raise ValueError("This hand has no notes here.")
    refs = levels.run_refs(level, staffs, list(patterns or []), words)

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        notes_revision = stored.header.notes_revision
        drawn, current, _ = _as_drawn(part_id)
        grid = song_grid(current)
        windows = levels.level_windows(current, staffs, start, end)
        run = LiveRun(part_id, drawn.text, windows, staff=HANDS[hand])
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _level_complete(part_id, level)

            def asked(system: str, messages: list[dict]) -> str:
                if not pipeline.has_events(part_id):
                    raise PartGone("The part was deleted while the AI wrote a level of its sheet.")
                return ask(system, messages)

            accepted: list[tuple[int, int]] = []
            written: list[Any] = []

            def on_plan(log: WindowLog) -> None:
                reporter.send(EVENT, {"phase": "plan", "status": log.status, "total": len(windows)})

            def on_batch(log: WindowLog, batch: Any) -> None:
                if log.status == "ok" and batch.sheet is not None:
                    accepted.append((log.start, log.end))
                    written.extend(n for n in batch.sheet.notes if n.staff in staffs)
                run.advanced(f1.write(_level_drawn(levels, current, written, accepted, staffs), mode="frames"))
                reporter.send(
                    EVENT,
                    {"phase": "batch", "done": log.k + 1, "total": len(windows), "status": log.status},
                )

            reporter.send(EVENT, {"phase": "level", "total": len(windows)})
            out = levels.write_level(
                current,
                asked,
                grid,
                level=level,
                staffs=staffs,
                patterns=[levels.catalog()[r] for r in refs],
                sid=part_id[:8],
                words=words,
                windows=windows,
                span=None if start is None and end is None else (windows[0][0], windows[-1][1]),
                on_plan=on_plan,
                on_batch=on_batch,
            )
            usd = float(getattr(ask, "usd", 0.0) or 0.0)
            requests = len(getattr(ask, "calls", []))
            summary: dict[str, Any] = {
                "hand": hand,
                "levelName": levels.level_name(level),
                "usd": round(usd, 4),
                "batches": len(accepted),
                "total": len(windows),
            }
            note = out.plan_log.note or next((log.note for log, _ in out.batches if log.note), "")
            if note:
                summary["note"] = note
            if "NoCredits" in note:
                summary["credits"] = "openai"
            if not pipeline.has_events(part_id):
                return {**summary, "level": "gone"}
            if not accepted:
                return {**summary, "level": "failed"}
            # The answers as the app draws them (beam groups, clefs, 8va and decoration notes by its rules), with
            # the figures the AI wrote kept as set by hand (a decoration note keeps the rule's).
            spliced = _level_drawn(levels, current, written, accepted, staffs)
            ours = [
                n
                for n in spliced.notes
                if n.staff in staffs and not n.grace and any(a <= n.frame < b for a, b in accepted)
            ]
            entry = {
                "level": level,
                "hand": hand,
                "start": accepted[0][0],
                "end": accepted[-1][1],
                "range": start is not None or end is not None,
                "prompt": levels.LEVEL_VERSION,
                "patterns": refs,
                "words": " ".join(words.split()),
                "plan": [section.line() for section in out.plan],
                "batches": [[log.start, log.end, log.status, log.replies] for log, _ in out.batches],
                "declared": [line for _, batch in out.batches for line in batch.declared.lines()],
            }
            done = edits.apply_level(
                part_id,
                spliced,
                notes_revision=notes_revision,
                start=accepted[0][0],
                end=accepted[-1][1],
                staff=HANDS[hand],
                wrote=ours,
                usd=usd,
                requests=requests,
                model=getattr(ask, "model", None),
                label=f"Level {levels.level_name(level)} with AI, {LEVEL_LABELS[hand]}",
                entry=entry,
            )
            reporter.send(EVENT, {"phase": "saved"})
            return {**summary, "level": "ok" if done else "stale"}
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return jobs.submit(work, key=KEY.format(part_id), describe=lambda result: dict(result or {}))


def _level_drawn(levels: Any, current: Any, written: list[Any], accepted: list[tuple[int, int]], staffs: tuple[int, ...]) -> Any:
    """The sheet with the batches accepted as the app draws the answers (``levels.drawn``, with the other hand's
    notes of those batches), the rest as it was: the sheet of the moment during a level run, and what is stored."""
    if not accepted:
        return current
    q = current.quarter_ms or 500.0
    keep = [n for n in current.notes if n.staff not in staffs and any(a <= n.frame < b for a, b in accepted)]
    answer = replace(current, notes=list(written))
    shown = levels.drawn(answer, q, key=current.key or 0, key_changes=list(current.key_changes), keep=keep)
    return levels.splice(current, list(shown.notes), accepted, staffs, reading=True)


def costs(part_id: str) -> dict[str, Any]:
    """What each run of the Enhance with AI dialog would cost, about, before it starts (the dialog shows it): the
    windows of a whole run, the batches of Simplify for each hand, in US dollars."""
    current = f1.read(build.current(part_id).text)
    whole = len(windows_of(current))
    out: dict[str, Any] = {
        "all": {
            "requests": whole + 1,
            "usd": round(USD_CACHE + (whole + 1) * USD_WINDOW, 2),
            "minutes": _minutes((whole + 1) * SECONDS_WINDOW),
        },
        "stretch": {"requests": 1, "usd": round(USD_CACHE + USD_STRETCH, 2), "minutes": _minutes(SECONDS_STRETCH)},
    }
    for hand, staff in HANDS.items():
        batches = len(simplify_windows(current, staff))
        usd = USD_CACHE + batches * USD_BATCH * (2 if staff is None else 1)
        out[f"simplify-{hand}"] = {
            "requests": batches,
            "usd": round(usd, 2),
            "minutes": _minutes(batches * SECONDS_BATCH),
        }
        out[f"level-{hand}"] = level_cost(current, hand)
    return out


def level_cost(current: Any, hand: str, start: int | None = None, end: int | None = None) -> dict[str, Any]:
    """About what a level run costs (implementation 04-3, Phase 4): the plan, then each batch."""
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    staffs = (1, 2) if HANDS[hand] is None else (HANDS[hand],)
    batches = len(levels.level_windows(current, staffs, start, end))
    seconds = SECONDS_LEVEL_PLAN + batches * SECONDS_LEVEL_BATCH
    return {
        "requests": batches + 1,
        "batches": batches,
        "usd": round(USD_LEVEL_PLAN + batches * USD_LEVEL_BATCH, 2),
        "minutes": _minutes(seconds),
    }


def _minutes(seconds: float) -> int:
    """About how many minutes a run takes, for the dialog: at least one."""
    return max(1, round(seconds / 60))


def _place(ref: str) -> tuple[int, int] | None:
    try:
        frame, midi = ref.split(":")
        return int(frame), int(midi)
    except ValueError:
        return None
