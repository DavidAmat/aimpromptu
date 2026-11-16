"""The LLM writes the sheet of a part in the background, window by window (implementation 03, Phase 5; plan 3.6).

:func:`start` submits one job per part (key ``sheet-llm:<part>``; a second start returns the running one). The job:

1. reads the notes with their starting hands (``pipeline.starting_hands``) and runs the LLM step of Phase 4
   (``sheet.llm.frames.write_frames``) with the model chosen, or the setting's (``llm_models``, the one table of the
   models; ``sheet_llm`` holds the clients);
2. keeps the sheet of the moment in memory (:class:`LiveRun`): the reference request first (the page shows the
   sheet it had, its first segment being improved), then the algorithm with the LLM's reference figure, then each
   window's decisions as it comes back (``assemble`` of the parts so far and the algorithm's parts for the rest);
3. sends an ``event: sheet`` message on the job's stream at each of those moments, so the page reads the sheet again;
4. at the end writes the hands of the sheet into ``notes.pmn`` (the numeric truth, plan section 3.7; the hands that
   were saved before go to the part's history first), with the notes the windows left out and added for the rules
   of simplicity (implementation 04, Phase 3: one step of undo, ``edits.record_run``), and the sheet into
   ``sheet.f1`` (:mod:`.store`). When no
   window was written by the LLM (no credits, no network), the hands stay as they were and ``sheet.f1`` keeps the
   algorithm's sheet, so the page does not start again by itself; it says nothing alarming (plan section 3.8).

:func:`start_level` writes the song, or a range, again at a level (implementation 04-3, Phase 4): the plan of the
song, then batches that see the batches before them (``sheet.llm.levels.write_level``); the notes it left out, added
and moved to the other hand are one step of undo (``edits.apply_level``). A level of the whole sheet runs in a new
project, the level copy (``library.flow.level_copy``), made by the route before the job starts.

:func:`start_stretch` writes one stretch again with the user's words (implementation 03, Phase 7), of both hands or
of one (implementation 04, Phase 4: the other hand fixed).

The notes may change while the LLM works (the Notes step). The job then stores what it wrote for the notes it read,
without touching the hands, and the page lays it on the current notes (``build.reapply``). A part deleted while the LLM
works stops the requests at the next one (:class:`PartGone`): no credits are spent on a project that is gone.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import os
import threading
from collections import Counter, OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np

from aitu_backend import llm_models
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
    split_windows,
    windows_of,
    write_frames,
    write_stretch,
)
from aitu_backend.sheet.proposal.frames import FramesProposal
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS, carry_extras
from aitu_backend.transcription import jobs, pipeline

from . import build, edits, runs, store

__all__ = [
    "Busy",
    "LiveRun",
    "available",
    "batch_plan",
    "commit",
    "costs",
    "job_of",
    "live",
    "start",
    "start_level",
    "start_stretch",
    "stop",
]

#: The job key of a part: one AI run at a time per part.
KEY = "sheet-llm:{}"
#: The name of the stream's messages (an ``EventSource`` listener of that name receives them).
EVENT = "sheet"
#: US dollars and seconds for the cost and the time the dialog shows before a run, measured with
#: ``llm_models.MEASURED_WITH`` at medium (implementation 04-3, Phase 5, on the user's song of 1.3 minutes: a whole run
#: of 7 requests $0.064 in 102 s, a stretch $0.024 in 26 s): the first request of a run writes the instructions into
#: the cache, then each window of a whole run (the reference request too), a stretch. Another model: times its ratio
#: (``llm_models.ratio``).
USD_CACHE = 0.01
USD_WINDOW = 0.008
USD_STRETCH = 0.015
SECONDS_WINDOW = 15
SECONDS_STRETCH = 30
#: A level run, measured there too: the plan of the song about $0.012 and 8 s; a batch with all its replies (1.9 on
#: average) about $0.023 and 41 s. The estimate the dialog shows rounds them up.
USD_LEVEL_PLAN = 0.015
USD_LEVEL_BATCH = 0.025
SECONDS_LEVEL_PLAN = 10
SECONDS_LEVEL_BATCH = 45


def available(model: str | None = None) -> bool:
    """Whether the LLM can be asked with ``model`` (the setting's by default, ``llm_models.resolve``): the key of its
    provider (the environment; for OpenAI also ``.env``) and its SDK installed."""
    from aitu_backend.sheet_llm import _openai_key  # noqa: PLC0415

    if llm_models.provider(llm_models.resolve(model)) == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY")) and importlib.util.find_spec("anthropic") is not None
    return bool(_openai_key()) and importlib.util.find_spec("openai") is not None


def level_available(model: str | None = None) -> bool:
    """The level routes ask this one: the same check as every run."""
    return available(model)


def _complete(part_id: str, kind: str, model: str | None = None) -> Any:
    """The ``complete`` function of a run: the model chosen, or the setting's, at the table's effort
    (``llm_models``); an OpenAI one with one cache key per part and kind of run."""
    name = llm_models.resolve(model)
    if llm_models.provider(name) == "anthropic":
        from aitu_backend.sheet_llm import ClaudeComplete  # noqa: PLC0415

        return ClaudeComplete(model=name)
    from aitu_backend.sheet_llm import OpenAIComplete  # noqa: PLC0415 - the SDK only when it is used

    return OpenAIComplete(model=name, cache_key=f"{part_id}|{kind}")


def _level_complete(part_id: str, level: Any, model: str | None = None) -> Any:
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    return _complete(part_id, levels.level_name(level), model)


class Stopped(RuntimeError):
    """The user pressed **Stop** in the panel of the run (2026-10-30): no more requests; what was written stays, and
    **Revert** takes it back."""


#: The parts whose run the user asked to stop, and what the end of a run adds to its summary (``before``: the
#: snapshot **Revert** puts back).
_stop_asked: set[str] = set()
_meta: dict[str, dict[str, Any]] = {}


def stop(part_id: str) -> bool:
    """Ask the part's AI run to stop before its next request (the one it waits for ends first). ``False``: none
    runs."""
    if job_of(part_id) is None:
        return False
    _stop_asked.add(part_id)
    return True


def _check_stop(part_id: str) -> None:
    if part_id in _stop_asked:
        raise Stopped("Stopped by the user.")


def _begin(part_id: str) -> int:
    """The start of a run that changes the part: the part as it is now kept for **Revert**."""
    before = edits.snapshot_before_run(part_id)
    _meta[part_id] = {"before": before}
    return before


class PartGone(RuntimeError):
    """The part was deleted while the LLM wrote its sheet: the chain stops asking, nothing is stored."""


def job_of(part_id: str) -> jobs.Job | None:
    return jobs.active(KEY.format(part_id))


def _submit(part_id: str, work: Callable[[BaseProgress], dict[str, Any]]) -> jobs.Job:
    """Run ``work`` as the part's AI job. The titles the user writes while it works are kept by every save of the run
    (``store.keep_titles``) until it ends, when the sheet's own titles hold again (the user, 2026-10-30)."""

    def run(reporter: BaseProgress) -> dict[str, Any]:
        try:
            out = work(reporter)
            # The snapshot Revert puts back, and whether the user stopped the run.
            extra = {**_meta.get(part_id, {}), **({"stopped": True} if part_id in _stop_asked else {})}
            return {**out, **extra} if isinstance(out, dict) else out
        finally:
            store.forget_titles(part_id)
            _meta.pop(part_id, None)
            _stop_asked.discard(part_id)

    return jobs.submit(run, key=KEY.format(part_id), describe=lambda result: dict(result or {}))


@dataclass
class LiveRun:
    """The sheet of a part while the LLM writes it."""

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
    #: A run in batches (a level, a stretch in batches): the batches done; the others are ``working`` and ``waiting``.
    done: int = 0
    #: The hand the AI writes (1 right, 2 left) when it writes one hand only (a level or a stretch); the page veils
    #: only that staff. ``None``: both hands.
    staff: int | None = None
    #: For each batch done: written (``True``) or kept as it was (the check refused it, or the run stopped).
    outcomes: list[bool] = field(default_factory=list)
    _text: tuple[int, str] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def advanced(self, text: str, ok: bool = True) -> None:
        """One more batch is done (a level, a stretch in batches): ``text`` is the sheet now."""
        with self._lock:
            self.before, self.done = text, self.done + 1
            self.outcomes.append(ok)

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
        """Each segment and its state: ``llm`` or ``algorithm`` (decided), ``working`` (at the LLM), ``waiting``."""
        with self._lock:
            if self.algo is None:
                return [
                    (
                        a,
                        b,
                        ("llm" if k >= len(self.outcomes) or self.outcomes[k] else "algorithm")
                        if k < self.done
                        else "working" if k == self.done else "waiting",
                    )
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


def start(
    part_id: str,
    *,
    complete: Callable[[], Complete] | None = None,
    model: str | None = None,
    batches: int | None = None,
) -> jobs.Job:
    """Start the AI on a part, or return the run already going. ``complete`` makes the ``complete`` function
    (tests); by default the ``model`` chosen (or the setting's) with the key of ``.env`` (:func:`_complete`).
    ``batches``: the windows are that many, of about the same time (``split_windows``; the user's choice)."""
    existing = job_of(part_id)
    if existing is not None:
        return existing

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes to write a sheet from.")
        header = stored.header
        _begin(part_id)
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
            ask = complete() if complete is not None else _complete(part_id, "whole", model)
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
                _check_stop(part_id)
                # A part deleted while the LLM works (its project, or a check's temporary copy): no more requests.
                if not pipeline.has_events(part_id):
                    raise PartGone("The part was deleted while the AI wrote its sheet.")
                return ask(system, messages)

            song = write_frames(
                notes,
                asked,
                sid=part_id[:8],
                hands=shown,
                quarter_ms=drawn_before.quarter_ms if named else None,
                windows=split_windows(drawn_before, batches) if batches else None,
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

    return _submit(part_id, work)


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
            # The notes changed while the LLM worked: keep its reading, lay it on the new notes when drawn.
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
    model: str | None = None,
    batches: int | None = None,
) -> jobs.Job:
    """The AI writes the columns ``[start, end)`` of the part's sheet again with the user's words (Phase 7, plan
    task 7.5): one window request (``sheet.llm.frames.write_stretch``), the hands of the sheet now shown as a
    suggestion. While it works the stretch is the one ``working`` segment of the page (its pale veil) and nothing can
    be edited (same job key as a whole run); its answer is stored as one step (``edits.apply_stretch``), or nothing
    when no reply was accepted (the summary of the job's ``done`` message says ``failed``). ``staff`` (1 or 2) or
    ``picked`` (the refs ``"<frame>:<midi>"`` of the notes picked) say what the user selected; with ``staff`` the
    stretch is of that hand only, and the other hand stays as it is (implementation 04, Phase 4). ``batches`` (the
    user's choice, 2026-10-30): the stretch in that many requests of about the same time, one after the other, each
    seeing the ones before it as written; a batch that fails keeps its notes, and the whole is one step."""
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        notes_revision = stored.header.notes_revision
        _begin(part_id)
        drawn, current, notes = _as_drawn(part_id)
        one = staff if staff in (1, 2) else None
        subs = (
            split_windows(current, batches, staffs=(one,) if one else (1, 2), start=start, end=end)
            if batches and batches > 1
            else []
        ) or [(start, end)]
        run = LiveRun(part_id, drawn.text, subs, staff=one)
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _complete(part_id, "stretch", model)
            reporter.send(EVENT, {"phase": "stretch", "start": start, "end": end, "total": len(subs)})

            def asked(system: str, messages: list[dict]) -> str:
                _check_stop(part_id)
                if not pipeline.has_events(part_id):
                    raise PartGone(
                        "The part was deleted while the AI wrote a stretch of its sheet."
                    )
                return ask(system, messages)

            places = [p for p in (_place(ref) for ref in picked or []) if p is not None]
            sheet, log, accepted = current, None, 0
            for k, (a, b) in enumerate(subs):
                try:
                    written, log = write_stretch(
                        sheet,
                        notes,
                        asked,
                        start=a,
                        end=b,
                        instruction=instruction,
                        staff=staff,
                        picked=[p for p in places if a <= p[0] < b] or None,
                        sid=part_id[:8],
                    )
                except ValueError:  # a batch with no note of the hand: nothing to write there
                    written = None
                if written is not None:
                    sheet, accepted = written, accepted + 1
                run.advanced(f1.write(sheet, mode="frames"), written is not None)
                reporter.send(EVENT, {"phase": "batch", "done": k + 1, "total": len(subs)})
                if log is not None and log.status == "error":
                    break  # no credits, no network: the next batches would fail the same way
            if not accepted:
                sheet = None
            usd = float(getattr(ask, "usd", 0.0) or 0.0)
            requests = len(getattr(ask, "calls", []))
            if sheet is None:
                return {"stretch": "failed", "usd": round(usd, 4), "note": (log.note if log else None) or None}
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
            return {
                "stretch": "ok" if done else "stale",
                "usd": round(usd, 4),
                "batches": accepted,
                "total": len(subs),
            }
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return _submit(part_id, work)


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
    exact: bool = False,
    complete: Callable[[], Complete] | None = None,
    model: str | None = None,
    batches: int | None = None,
    strict: list[str] | None = None,
    first: bool = False,
    chords: str = "",
) -> jobs.Job:
    """The AI writes the ``hand`` (``right``, ``left`` or ``both``) of the part's sheet again at ``level`` (one level,
    or one per hand: ``{"right": "hard", "left": "medium"}``), over the whole song or over ``[start, end)`` (a range),
    with the ``patterns`` selected in the catalog and the user's ``words`` (implementation 04-3, Phase 4; plan
    sections 5.4 and 5.8). A hand with no pattern selected or named gets the patterns of its level used when none is
    selected (``levels.run_refs``), unless ``exact``: then a hand with none is written by its level's rules only.
    While it works the page shows the sheet of the moment, its batches as segments; the end stores it as one step
    (``edits.apply_level``). The summary of the job's ``done`` message: ``level`` (``ok``, ``failed`` when no batch
    was accepted, ``stale`` when the notes changed meanwhile, ``gone``), ``batches`` and ``total``, ``usd``, ``run``
    (the id of its log).

    Implementation 04-5: ``strict``, the patterns ticked Strict; every conversation with the AI goes into the run's
    log (:mod:`.runs`) as it ends. ``first`` (the routes, the user, 2026-10-31): a run of two batches or more writes
    the plan and its first batch only, stores it and waits (``waiting`` in the summary and the log): the user checks
    it, answers the AI (:func:`again_batch`) or goes on (:func:`continue_level`). ``chords``: the song's chords as a
    guitar guide gives them (the user, 2026-10-31), in the system prompt of every request."""
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}.")
    levels.hand_levels(level)
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    staffs = _staffs(hand)
    if not levels.level_windows(f1.read(build.current(part_id).text), staffs, start, end):
        raise ValueError("This hand has no notes here.")
    refs = levels.run_refs(level, staffs, list(patterns or []), words, exact=exact)
    hard = sorted({r for r in strict or [] if r in refs})

    def work(reporter: BaseProgress) -> dict[str, Any]:
        windows = levels.level_windows(f1.read(build.current(part_id).text), staffs, start, end, batches)
        chosen = [levels.catalog()[r] for r in refs]
        log = runs.create(
            part_id,
            {
                "level": level,
                "hand": hand,
                "start": start,
                "end": end,
                "patterns": refs,
                "strict": hard,
                "words": " ".join(words.split()),
                "model": llm_models.resolve(model),
                "windows": [list(w) for w in windows],
                "prompt": levels.LEVEL_VERSION,
                "chords": chords.strip(),
            },
            levels.system_prompt(level, chosen, staffs, frozenset(hard), chords),
        )
        todo = windows[:1] if first and len(windows) > 1 else windows
        return _level_work(part_id, reporter, log, todo, complete=complete)

    return _submit(part_id, work)


def _staffs(hand: str) -> tuple[int, ...]:
    return (1, 2) if HANDS[hand] is None else (HANDS[hand],)


def continue_level(part_id: str, run_id: str, *, complete: Callable[[], Complete] | None = None) -> jobs.Job:
    """**Go on with the other batches** of a run that waits after its first batch (implementation 04-5): the batches
    not written yet, with the run's plan and rules, each seeing the batches before it; one step of undo. **Revert**
    then puts back the part as it was before the first batch."""
    log = runs.load(part_id, run_id)
    if log is None:
        raise LookupError("No such run.")
    if log["state"] != "waiting":
        raise ValueError("This run is not waiting for you.")
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    seen = {(b["start"], b["end"]) for b in log["batches"]}
    if log.get("kind") == "style":  # Copy this style (implementation 06): the passages kept not written yet
        rest = [
            int(p["k"])
            for p in sorted(log["passages"], key=lambda p: p["start"])
            if p.get("keep", True) and (p["start"], p["end"]) not in seen
        ]

        def go_on(reporter: BaseProgress) -> dict[str, Any]:
            return _style_work(part_id, reporter, log, rest, complete=complete)

        return _submit(part_id, go_on)
    todo = [tuple(w) for w in log["request"]["windows"] if tuple(w) not in seen]

    def work(reporter: BaseProgress) -> dict[str, Any]:
        return _level_work(part_id, reporter, log, todo, complete=complete)

    return _submit(part_id, work)


def _level_work(
    part_id: str,
    reporter: BaseProgress,
    log: dict[str, Any],
    todo: list[tuple[int, int]],
    *,
    complete: Callable[[], Complete] | None,
) -> dict[str, Any]:
    """The batches ``todo`` of the run whose log is ``log``: the plan first when the log has none yet (a new run),
    then the batches, stored as one step. The batches of the run already written (a run that goes on after its first
    batch) are read from the sheet: the next batches see them, and the page shows them written."""
    from aitu_backend.sheet.levels.grid import song_grid  # noqa: PLC0415
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    req = log["request"]
    level, hand, refs, hard, words = req["level"], req["hand"], req["patterns"], req["strict"], req["words"]
    staffs = _staffs(hand)
    stored = pipeline.load_note_events(part_id)
    if stored is None:
        raise FileNotFoundError("This part has no notes.")
    notes_revision = stored.header.notes_revision
    if "before" in log:
        _meta[part_id] = {"before": log["before"]}  # Revert goes back to before the first batch
    else:
        log["before"] = _begin(part_id)
    drawn, current, _ = _as_drawn(part_id)
    grid = song_grid(current)
    windows = [tuple(w) for w in req["windows"]]
    chosen = [levels.catalog()[r] for r in refs]
    allowed = set(refs)
    plan = rules = None
    done_before = [(b["start"], b["end"]) for b in log["batches"] if b["status"] == "ok"]
    if log.get("plan") and log["plan"]["status"] == "ok":
        p = log["plan"]
        _, plan = levels.read_plan(p["messages"][-1]["content"], allowed, staffs, p["start"], p["end"], frozenset(hard))
        rules = [levels.Rule(r["text"], r["source"], r.get("ref")) for r in log["rules"]]
    written_before = [n for n in current.notes if n.staff in staffs and any(a <= n.frame < b for a, b in done_before)]
    first_index = windows.index(todo[0]) if todo else 0
    run = LiveRun(part_id, drawn.text, windows, staff=HANDS[hand])
    run.done, run.outcomes = first_index, [True] * first_index
    log["state"] = "running"
    runs.save(part_id, log)
    with _live_lock:
        _live[part_id] = run
    try:
        ask = complete() if complete is not None else _level_complete(part_id, level, req.get("model"))
        usd0 = float(log.get("usd", 0.0))
        requests0 = int(log.get("requests", 0))

        def asked(system: str, messages: list[dict]) -> str:
            # A Stop of a level run keeps the batches already accepted and saved (on the level copy; the song does
            # not change), and **Revert** removes the whole run. The user's answer of 2026-11-03 (04-7): keep it so.
            _check_stop(part_id)
            if not pipeline.has_events(part_id):
                raise PartGone("The part was deleted while the AI wrote a level of its sheet.")
            return ask(system, messages)

        accepted: list[tuple[int, int]] = []
        written: list[Any] = []

        def on_plan(wlog: WindowLog) -> None:
            reporter.send(EVENT, {"phase": "plan", "status": wlog.status, "total": len(windows)})

        def on_batch(wlog: WindowLog, batch: Any) -> None:
            if wlog.status == "ok" and batch.sheet is not None:
                accepted.append((wlog.start, wlog.end))
                written.extend(n for n in batch.sheet.notes if n.staff in staffs)
            run.advanced(
                f1.write(_level_drawn(levels, current, written, accepted, staffs), mode="frames"),
                wlog.status == "ok" and batch.sheet is not None,
            )
            reporter.send(EVENT, {"phase": "batch", "done": wlog.k + 1, "total": len(windows), "status": wlog.status})

        def on_talk(talk: Any) -> None:
            log["usd"] = round(usd0 + float(getattr(ask, "usd", 0.0) or 0.0), 4)
            log["requests"] = requests0 + len(getattr(ask, "calls", []))
            if talk.k < 0:
                log["rules"] = (
                    [r.to_json() for r in levels.read_rules(talk.messages[-1]["content"])] if talk.status == "ok" else []
                )
            else:
                log["rules"] += [{"text": x, "source": f"batch {talk.k + 1}", "ref": None} for x in talk.rules]
            runs.update(part_id, log, talk)

        reporter.send(EVENT, {"phase": "level", "total": len(windows)})
        span = None if req.get("start") is None and req.get("end") is None else (windows[0][0], windows[-1][1])
        try:
            out = levels.write_level(
                current,
                asked,
                grid,
                level=level,
                staffs=staffs,
                patterns=chosen,
                sid=part_id[:8],
                words=words,
                windows=list(todo),
                plan=plan,
                rules=rules,
                span=span,
                on_plan=on_plan,
                on_batch=on_batch,
                strict=frozenset(hard),
                on_talk=on_talk,
                written_before=written_before,
                done_before=done_before,
                first_index=first_index,
                count=len(windows),
                guide=req.get("chords", ""),
            )
        except BaseException:
            log["state"] = "stopped"
            runs.save(part_id, log)
            raise
        usd = float(getattr(ask, "usd", 0.0) or 0.0)
        requests = len(getattr(ask, "calls", []))
        log["usd"], log["requests"] = round(usd0 + usd, 4), requests0 + requests
        left = len(windows) - first_index - len(todo)
        waiting = bool(accepted) and left > 0 and part_id not in _stop_asked
        log["state"] = (
            "stopped" if part_id in _stop_asked else "waiting" if waiting else "done" if accepted or done_before else "failed"
        )
        runs.save(part_id, log)
        summary: dict[str, Any] = {
            "hand": hand,
            "levelName": levels.level_name(level),
            "usd": round(usd, 4),
            "batches": len(accepted) + len(done_before),
            "total": len(windows),
            "run": log["id"],
        }
        if waiting:
            summary["waiting"] = True
        note = out.plan_log.note or next((wlog.note for wlog, _ in out.batches if wlog.note), "")
        if note:
            summary["note"] = note
        if "NoCredits" in note:
            summary["credits"] = "openai"
        if not pipeline.has_events(part_id):
            return {**summary, "level": "gone"}
        if not accepted:
            return {**summary, "level": "failed"}
        # The answers as the app draws them (beam groups, clefs, 8va and decoration notes by its rules), with the
        # figures the AI wrote kept as set by hand (a decoration note keeps the rule's).
        spliced = _level_drawn(levels, current, written, accepted, staffs)
        ours = [n for n in spliced.notes if n.staff in staffs and not n.grace and any(a <= n.frame < b for a, b in accepted)]
        entry = {
            "level": level,
            "hand": hand,
            "start": accepted[0][0],
            "end": accepted[-1][1],
            "range": req.get("start") is not None or req.get("end") is not None,
            "prompt": levels.LEVEL_VERSION,
            "patterns": refs,
            "strict": hard,
            "run": log["id"],
            "words": words,
            "plan": [section.line() for section in out.plan],
            "batches": [[wlog.start, wlog.end, wlog.status, wlog.replies] for wlog, _ in out.batches],
            "declared": [line for _, batch in out.batches for line in batch.declared.lines()],
        }
        part = ", batch 1" if waiting else ", the other batches" if first_index else ""
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
            label=f"Level {levels.level_name(level)} with AI, {LEVEL_LABELS[hand]}{part}",
            entry=entry,
        )
        reporter.send(EVENT, {"phase": "saved"})
        return {**summary, "level": "ok" if done else "stale"}
    finally:
        with _live_lock:
            _live.pop(part_id, None)


def again_batch(
    part_id: str, run_id: str, k: int, words: str, *, complete: Callable[[], Complete] | None = None
) -> jobs.Job:
    """**Write this batch again** (implementation 04-5, the user, 2026-10-31): batch ``k`` (0 = first) of a run with a
    log goes on with the user's answer (``levels.write_again``), is checked against the notes it had before the run,
    and replaces that stretch of its hands on the sheet as one step of undo. Its explanation and rules in the log are
    the new ones, and the answer is kept with the batch. A run waiting after its first batch keeps waiting."""
    from aitu_backend.sheet.levels.grid import song_grid  # noqa: PLC0415
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    log = runs.load(part_id, run_id)
    if log is None:
        raise LookupError("No such run.")
    if log.get("kind") == "style":
        return _again_style(part_id, log, k, words, complete)
    old = next((b for b in log["batches"] if b["k"] == k), None)
    if old is None or not old.get("target") or not old.get("messages"):
        raise LookupError("This batch has no conversation to answer.")
    if not words.strip():
        raise ValueError("Write your answer to the AI first.")
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    req = log["request"]
    level, hand, hard = req["level"], req["hand"], frozenset(req["strict"])
    staffs = _staffs(hand)

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        notes_revision = stored.header.notes_revision
        _begin(part_id)
        drawn, current, _ = _as_drawn(part_id)
        a, b = old["start"], old["end"]
        target = f1.read(old["target"])
        kept = [n for n in current.notes if not (n.staff in staffs and a <= n.frame < b)]
        before = replace(current, notes=kept + [n for n in target.notes if n.staff in staffs]).sort()
        grid = song_grid(before)
        run = LiveRun(part_id, drawn.text, [(a, b)], staff=HANDS[hand])
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _level_complete(part_id, level, req.get("model"))

            def asked(system: str, messages: list[dict]) -> str:
                _check_stop(part_id)
                return ask(system, messages)

            reporter.send(EVENT, {"phase": "level", "total": 1})
            talk = levels.Talk(
                old["k"], a, b, old["messages"], old["status"], list(old.get("errors", [])), old["target"]
            )
            try:
                again, result = levels.write_again(
                    asked, log["system"], talk, words, before, grid, level=level, staffs=staffs,
                    allowed=set(req["patterns"]), strict=hard, guide=req.get("chords", ""),
                )
            except Exception as exc:  # noqa: BLE001 (no credits, no network: the batch stays as it is)
                return {"level": "failed", "again": k + 1, "run": run_id, "note": f"{type(exc).__name__}: {exc}",
                        **({"waiting": True} if log["state"] == "waiting" else {})}
            usd = float(getattr(ask, "usd", 0.0) or 0.0)
            requests = len(getattr(ask, "calls", []))
            ok = again.status == "ok" and result.sheet is not None
            answers = list(old.get("answers", [])) + [{"words": " ".join(words.split()), "at": runs._now()}]
            entry_talk = again.to_json() | {"answers": answers}
            if not ok:  # the batch on the sheet stays the earlier answer: its explanation too
                entry_talk.update(status=old["status"], explain=old["explain"], rules=old["rules"], declared=old["declared"])
            log["batches"] = sorted([x for x in log["batches"] if x["k"] != k] + [entry_talk], key=lambda x: x["k"])
            if ok:
                source = f"batch {k + 1}"
                log["rules"] = [r for r in log["rules"] if r["source"] != source] + [
                    {"text": x, "source": source, "ref": None} for x in again.rules
                ]
            log["usd"] = round(float(log.get("usd", 0.0)) + usd, 4)
            log["requests"] = int(log.get("requests", 0)) + requests
            runs.save(part_id, log)
            summary: dict[str, Any] = {
                "hand": hand, "levelName": levels.level_name(level), "usd": round(usd, 4), "batches": int(ok),
                "total": 1, "run": run_id, "again": k + 1,
            }
            if log["state"] == "waiting":
                summary["waiting"] = True
            if not ok:
                run.advanced(drawn.text, False)
                return {**summary, "level": "failed"}
            written = [n for n in result.sheet.notes if n.staff in staffs]
            spliced = _level_drawn(levels, current, written, [(a, b)], staffs)
            run.advanced(f1.write(spliced, mode="frames"), True)
            ours = [n for n in spliced.notes if n.staff in staffs and not n.grace and a <= n.frame < b]
            entry = {
                "level": level, "hand": hand, "start": a, "end": b, "range": True, "prompt": levels.LEVEL_VERSION,
                "patterns": req["patterns"], "strict": req["strict"], "run": run_id, "again": k + 1,
                "words": " ".join(words.split()), "plan": [], "batches": [[a, b, "ok", len(again.errors) + 1]],
                "declared": again.declared,
            }
            done = edits.apply_level(
                part_id, spliced, notes_revision=notes_revision, start=a, end=b, staff=HANDS[hand], wrote=ours,
                usd=usd, requests=requests, model=getattr(ask, "model", None),
                label=f"Batch {k + 1} written again with AI", entry=entry,
            )
            reporter.send(EVENT, {"phase": "saved"})
            return {**summary, "level": "ok" if done else "stale"}
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return _submit(part_id, work)


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


# ------------------------------------------------------------------ Copy this style (implementation 06, Phase 2)

#: A Copy this style run: the check of the passages, then each passage, first taken from the level run's numbers (a
#: batch prompt of about the same size); measured in Phase 4 and written back. Another model: times its ratio.
USD_STYLE_CHECK = 0.015
USD_STYLE_BATCH = 0.025
SECONDS_STYLE_CHECK = 10
SECONDS_STYLE_BATCH = 45
STYLE_LABELS = {"both": "both hands", "right": "the right hand", "left": "the left hand"}

#: The song's grid and chords for the matcher, per part: about half a second to compute, and the dialog asks again
#: when the hand changes. Keyed by the drawn sheet and the notes' revision.
_style_cache: "OrderedDict[str, tuple[tuple[str, int], Any]]" = OrderedDict()
_style_lock = threading.Lock()


def _style_inputs(part_id: str) -> tuple[Any, Any, Any, Any]:
    """The sheet drawn now, the part's notes with the removed ones (the reference as played), the song's grid and
    its chords."""
    from aitu_backend.sheet.levels.grid import song_grid  # noqa: PLC0415
    from aitu_backend.sheet.levels.harmony import chords  # noqa: PLC0415

    drawn = build.current(part_id)
    stored = pipeline.load_note_events(part_id)
    if stored is None:
        raise FileNotFoundError("This part has no notes.")
    key = (hashlib.sha1(drawn.text.encode("utf-8")).hexdigest(), int(stored.header.notes_revision or 0))
    with _style_lock:
        hit = _style_cache.get(part_id)
    current = f1.read(drawn.text)
    notes = events_file.notes_from_events(stored.events)
    if hit is not None and hit[0] == key:
        grid, cs = hit[1]
    else:
        grid = song_grid(current)
        cs = chords(current, grid)
        with _style_lock:
            _style_cache[part_id] = (key, (grid, cs))
            _style_cache.move_to_end(part_id)
            while len(_style_cache) > 8:
                _style_cache.popitem(last=False)
    return current, notes, grid, cs


def style_cost(passages: int, model: str | None = None) -> dict[str, Any]:
    """About what a Copy this style run over ``passages`` passages costs: the check, then each passage."""
    usd_ratio, time_ratio = llm_models.ratio(llm_models.resolve(model))
    return {
        "requests": passages + 1 if passages else 0,
        "usd": round((USD_STYLE_CHECK + passages * USD_STYLE_BATCH) * usd_ratio, 2) if passages else 0.0,
        "minutes": _minutes((SECONDS_STYLE_CHECK + passages * SECONDS_STYLE_BATCH) * time_ratio) if passages else 0,
    }


def _reference_columns(current: Any, staffs: tuple[int, ...], start: int, end: int) -> int:
    return len({n.frame for n in current.notes if n.staff in staffs and start <= n.frame < end and not n.grace})


def style_passages(
    part_id: str, *, start: int, end: int, hand: str, model: str | None = None
) -> dict[str, Any]:
    """The passages of the song like the reference ``[start, end)`` of the ``hand`` (the dialog's list, free: code
    only, ``sheet.style.match.similar``), in the order of the song, with the cost and the minutes of a run over all
    of them, and ``costs``, the same for each number of passages ticked. ``tooLong``: the reference is longer than
    ``BATCH_MAX_S`` (a batch must fit one request); ``tooShort``: it holds too few columns to find anything."""
    from aitu_backend.sheet.style import match  # noqa: PLC0415

    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}.")
    staffs = _staffs(hand)
    current, notes, grid, cs = _style_inputs(part_id)
    too_long = (end - start) * FRAME_MS / 1000 > BATCH_MAX_S
    too_short = _reference_columns(current, staffs, start, end) < match.REF_COLUMNS
    found = [] if too_long or too_short else match.similar(current, notes, start, end, staffs, grid=grid, harmony=cs)
    return {
        "reference": [start, end],
        "hand": hand,
        "model": llm_models.resolve(model),
        "passages": [{"start": m.start, "end": m.end, "score": m.score, "shift": m.shift} for m in found],
        "threshold": match.THRESHOLD,
        "max": match.STYLE_MAX,
        "tooLong": too_long,
        "tooShort": too_short,
        **style_cost(len(found), model),
        # What a run costs with each number of passages ticked, none first: the dialog follows the ticks with no request.
        "costs": [style_cost(n, model) for n in range(len(found) + 1)],
    }


def start_style(
    part_id: str,
    *,
    start: int,
    end: int,
    hand: str,
    passages: list[tuple[int, int]],
    words: str = "",
    model: str | None = None,
    first: bool = True,
    complete: Callable[[], Complete] | None = None,
) -> jobs.Job:
    """**Copy this style** (implementation 06, plan section 4.3): the reference ``[start, end)`` of the ``hand``, the
    passages the user ticked (``[first frame, end frame)``, as the dialog listed them), the user's ``words``. The job
    asks the check of the passages, then writes each passage kept in the order of the song; with ``first`` (the
    routes) it writes the check and the first passage, stores them and waits (``waiting``), as a level run; **Go on
    with the other batches** is :func:`continue_level`. One step of undo; the log ``ai-runs/<id>.json`` has ``kind``
    ``style``. The summary of the job's ``done`` message: ``style`` (``ok``, ``dropped`` when the check dropped every
    passage, ``failed``, ``stale``, ``gone``), ``batches``, ``total``, ``dropped``, ``usd``, ``run``."""
    from aitu_backend.sheet.llm import style  # noqa: PLC0415
    from aitu_backend.sheet.style import match  # noqa: PLC0415

    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}.")
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    if not passages:
        raise ValueError("Tick a passage first.")
    if len(passages) > match.STYLE_MAX:
        raise ValueError(f"At most {match.STYLE_MAX} passages.")
    if end <= start:
        raise ValueError("The reference is empty.")
    if (end - start) * FRAME_MS / 1000 > BATCH_MAX_S:
        raise ValueError("Select a shorter stretch.")
    staffs = _staffs(hand)
    current, notes, grid, cs = _style_inputs(part_id)
    if _reference_columns(current, staffs, start, end) < match.REF_COLUMNS:
        raise ValueError("Select a longer stretch.")
    places = sorted((int(a), int(b)) for a, b in passages)
    for a, b in places:
        if b <= a:
            raise ValueError("A passage is empty.")
        if a < end and start < b:
            raise ValueError("A passage overlaps the reference.")
        if (b - a) * FRAME_MS / 1000 > BATCH_MAX_S:
            raise ValueError("A passage is too long.")
    if any(y[0] < x[1] for x, y in zip(places, places[1:])):
        raise ValueError("Two passages overlap.")
    found = match.ranked(current, notes, start, end, staffs, grid=grid, harmony=cs, floor=0.0)
    matched = match.of_places(found, places)
    if any(m is None for m in matched):
        raise ValueError("The notes changed since the list was made: open it again.")
    plist = [
        style.Passage(k, a, b, m.score, m.shift, list(m.columns))
        for k, ((a, b), m) in enumerate(zip(places, matched))
        if m is not None
    ]

    def work(reporter: BaseProgress) -> dict[str, Any]:
        log = runs.create(
            part_id,
            {
                "hand": hand,
                "start": start,
                "end": end,
                "words": " ".join(words.split()),
                "model": llm_models.resolve(model),
                "prompt": style.STYLE_VERSION,
                "windows": [[p.start, p.end] for p in plist],
            },
            style.system_prompt(),
            kind="style",
        )
        log["passages"] = [p.to_json() for p in plist]
        runs.save(part_id, log)
        return _style_work(part_id, reporter, log, None, complete=complete, limit=1 if first else None)

    return _submit(part_id, work)


def _style_drawn(current: Any, answers: list[tuple[Any, Any]], staffs: tuple[int, ...]) -> Any:
    """``current`` with each passage accepted taken from its answer as the AI wrote it (``frames.splice``, as a
    stretch: its hands, beam groups, clefs, 8va and figures; the user's marks of a note kept), the other hand kept
    when one hand is rewritten. Not settled: the store lays the rules on it."""
    from aitu_backend.sheet.llm import frames as llm_frames  # noqa: PLC0415

    sheet = current
    keep = None if len(staffs) == 2 else 3 - staffs[0]
    for p, answer in answers:
        sheet = llm_frames.splice(sheet, answer, p.start, p.end, keep=keep)
    return sheet


def _style_work(
    part_id: str,
    reporter: BaseProgress,
    log: dict[str, Any],
    todo: list[int] | None,
    *,
    complete: Callable[[], Complete] | None,
    limit: int | None = None,
) -> dict[str, Any]:
    """The passages of a Copy this style run: the check first when the log has none yet, then the passages kept
    (``todo``: their ``k``; ``limit``: at most that many, the first passage first), stored as one step with the marks
    the code copies. The passages written before (a run that goes on) are read from the sheet."""
    from aitu_backend.sheet.llm import style  # noqa: PLC0415
    from aitu_backend.sheet.llm.frames import _slice  # noqa: PLC0415

    req = log["request"]
    hand, words = req["hand"], req["words"]
    staffs = _staffs(hand)
    reference = (int(req["start"]), int(req["end"]))
    stored = pipeline.load_note_events(part_id)
    if stored is None:
        raise FileNotFoundError("This part has no notes.")
    notes_revision = stored.header.notes_revision
    if "before" in log:
        _meta[part_id] = {"before": log["before"]}  # Revert goes back to before the first passage
    else:
        log["before"] = _begin(part_id)
    drawn, current, _ = _as_drawn(part_id)
    passages = [style.Passage.from_json(p) for p in log["passages"]]
    checked = bool(log.get("plan")) and log["plan"]["status"] == "ok"
    done_before = [(b["start"], b["end"]) for b in log["batches"] if b["status"] == "ok"]
    kept = sorted((p for p in passages if p.keep), key=lambda p: p.start)
    if todo is not None:
        wanted = set(todo)
        first_index = next((i for i, p in enumerate(kept) if p.k in wanted), len(kept))
    else:
        first_index = 0
    written_before = [n for n in current.notes if n.staff in staffs and any(a <= n.frame < b for a, b in done_before)]
    earlier_before = [
        (p, _slice(current, p.start, p.end, staffs)) for p in kept if (p.start, p.end) in set(done_before)
    ]
    windows = [(p.start, p.end) for p in (kept if checked else sorted(passages, key=lambda p: p.start))]
    run = LiveRun(part_id, drawn.text, windows, staff=HANDS[hand])
    run.done, run.outcomes = first_index, [True] * first_index
    log["state"] = "running"
    runs.save(part_id, log)
    with _live_lock:
        _live[part_id] = run
    try:
        ask = complete() if complete is not None else _complete(part_id, "style", req.get("model"))
        usd0 = float(log.get("usd", 0.0))
        requests0 = int(log.get("requests", 0))

        def asked(system: str, messages: list[dict]) -> str:
            # A Stop keeps the passages already accepted (the rule of 04-7); Revert removes the whole run.
            _check_stop(part_id)
            if not pipeline.has_events(part_id):
                raise PartGone("The part was deleted while the AI copied a style on its sheet.")
            return ask(system, messages)

        answers: list[tuple[Any, Any]] = []

        def on_check(wlog: WindowLog, decided: list[Any]) -> None:
            log["passages"] = [p.to_json() for p in decided]
            now_kept = sorted((p for p in decided if p.keep), key=lambda p: p.start)
            req["windows"] = [[p.start, p.end] for p in now_kept]
            with run._lock:
                run.provisional = [(p.start, p.end) for p in now_kept]
            runs.save(part_id, log)
            reporter.send(
                EVENT, {"phase": "check", "status": wlog.status, "kept": len(now_kept), "total": len(decided)}
            )

        def on_batch(wlog: WindowLog, result: Any, p: Any) -> None:
            ok = wlog.status == "ok" and result.sheet is not None
            if ok:
                answers.append((p, result.sheet))
            run.advanced(f1.write(_style_drawn(current, answers, staffs), mode="frames"), ok)
            reporter.send(
                EVENT, {"phase": "batch", "done": wlog.k + 1, "total": len(req["windows"]), "status": wlog.status}
            )

        def on_talk(talk: Any) -> None:
            log["usd"] = round(usd0 + float(getattr(ask, "usd", 0.0) or 0.0), 4)
            log["requests"] = requests0 + len(getattr(ask, "calls", []))
            runs.update(part_id, log, talk)

        reporter.send(EVENT, {"phase": "style", "total": len(passages), "checking": not checked})
        try:
            out = style.write_style(
                current,
                asked,
                reference=reference,
                passages=passages,
                staffs=staffs,
                sid=part_id[:8],
                words=words,
                checked=checked,
                todo=todo,
                written_before=written_before,
                done_before=done_before,
                earlier_before=earlier_before,
                first_index=first_index,
                limit=limit,
                on_check=on_check,
                on_batch=on_batch,
                on_talk=on_talk,
            )
        except BaseException:
            log["state"] = "stopped"
            runs.save(part_id, log)
            raise
        usd = float(getattr(ask, "usd", 0.0) or 0.0)
        requests = len(getattr(ask, "calls", []))
        log["usd"], log["requests"] = round(usd0 + usd, 4), requests0 + requests
        passages = out.passages
        kept = sorted((p for p in passages if p.keep), key=lambda p: p.start)
        dropped = sum(not p.keep for p in passages)
        tried = {(w.start, w.end): w.status for w, _ in out.batches}
        left = len(kept) - first_index - len(out.batches)
        stopped = part_id in _stop_asked
        waiting = bool(answers) and left > 0 and not stopped
        check_failed = out.check_log.status != "ok" and not checked
        log["state"] = (
            "stopped"
            if stopped
            else "failed"
            if check_failed
            else "waiting"
            if waiting
            else "done"
            if answers or done_before or not kept
            else "failed"
        )
        runs.save(part_id, log)
        summary: dict[str, Any] = {
            "hand": hand,
            "usd": round(usd, 4),
            "batches": len(answers) + len(done_before),
            "total": len(kept),
            "dropped": dropped,
            "run": log["id"],
        }
        if waiting:
            summary["waiting"] = True
        note = out.check_log.note or next((w.note for w, _ in out.batches if w.note), "")
        if note:
            summary["note"] = note
        if "NoCredits" in note:
            summary["credits"] = "openai"
        if not pipeline.has_events(part_id):
            return {**summary, "style": "gone"}
        if check_failed:
            return {**summary, "style": "failed"}
        if not kept:
            return {**summary, "style": "dropped"}
        if not answers:
            return {**summary, "style": "failed"}
        spliced = _style_drawn(current, answers, staffs)
        ref_sheet = style._reference_sheet(current, reference)
        total_copied: Counter = Counter()
        for p, _answer in answers:
            before = [n for n in current.notes if n.staff in staffs and p.start <= n.frame < p.end]
            counts = style.copy_marks(spliced, reference=ref_sheet, before=before, passage=p, staffs=staffs)
            total_copied.update(counts)
            for b in log["batches"]:
                if (b["start"], b["end"]) == (p.start, p.end):
                    b["copied"] = dict(counts)
                    b["copiedText"] = style.copied_text(counts)
        runs.save(part_id, log)
        ours = [
            n
            for _, answer in answers
            for n in answer.notes
            if n.staff in staffs and not n.covered
        ]
        accepted = sorted((p.start, p.end) for p, _ in answers)
        entry = {
            "hand": hand,
            "reference": [reference[0], reference[1]],
            "words": words,
            "prompt": style.STYLE_VERSION,
            "run": log["id"],
            "passages": [
                [p.start, p.end, "dropped" if not p.keep else tried.get((p.start, p.end), "waiting"), p.why]
                for p in sorted(passages, key=lambda p: p.start)
                if (p.start, p.end) not in set(done_before)
            ],
            "copied": dict(total_copied),
        }
        part = ", passage 1" if waiting and not first_index else ", the other passages" if first_index else ""
        done = edits.apply_style(
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
            label=f"Copy this style with AI, {STYLE_LABELS[hand]}{part}",
            entry=entry,
        )
        reporter.send(EVENT, {"phase": "saved"})
        return {**summary, "style": "ok" if done else "stale"}
    finally:
        with _live_lock:
            _live.pop(part_id, None)


def _again_style(part_id: str, log: dict[str, Any], k: int, words: str, complete: Callable[[], Complete] | None) -> jobs.Job:
    """**Write this batch again** for a passage of a Copy this style run (as :func:`again_batch` for a level batch):
    its conversation goes on with the user's answer, checked as in the run, and replaces the passage as one step."""
    from aitu_backend.sheet.llm import levels, style  # noqa: PLC0415

    old = next((b for b in log["batches"] if b["k"] == k), None)
    if old is None or not old.get("target") or not old.get("messages"):
        raise LookupError("This batch has no conversation to answer.")
    if not words.strip():
        raise ValueError("Write your answer to the AI first.")
    if job_of(part_id) is not None:
        raise Busy("The AI is already enhancing this sheet.")
    req = log["request"]
    hand = req["hand"]
    staffs = _staffs(hand)
    reference = (int(req["start"]), int(req["end"]))
    passage = next(
        (
            style.Passage.from_json(p)
            for p in log["passages"]
            if (int(p["start"]), int(p["end"])) == (old["start"], old["end"])
        ),
        None,
    )
    if passage is None:
        raise LookupError("This batch has no passage.")
    run_id = log["id"]

    def work(reporter: BaseProgress) -> dict[str, Any]:
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        notes_revision = stored.header.notes_revision
        _begin(part_id)
        drawn, current, _ = _as_drawn(part_id)
        a, b = old["start"], old["end"]
        run = LiveRun(part_id, drawn.text, [(a, b)], staff=HANDS[hand])
        with _live_lock:
            _live[part_id] = run
        try:
            ask = complete() if complete is not None else _complete(part_id, "style", req.get("model"))

            def asked(system: str, messages: list[dict]) -> str:
                _check_stop(part_id)
                return ask(system, messages)

            reporter.send(EVENT, {"phase": "style", "total": 1})
            talk = levels.Talk(old["k"], a, b, old["messages"], old["status"], list(old.get("errors", [])), old["target"])
            waiting = {"waiting": True} if log["state"] == "waiting" else {}
            try:
                again, result = style.write_again(
                    asked, log["system"], talk, words, current, reference=reference, passage=passage, staffs=staffs
                )
            except Exception as exc:  # noqa: BLE001 (no credits, no network: the passage stays as it is)
                return {"style": "failed", "again": k + 1, "run": run_id, "note": f"{type(exc).__name__}: {exc}", **waiting}
            usd = float(getattr(ask, "usd", 0.0) or 0.0)
            requests = len(getattr(ask, "calls", []))
            ok = again.status == "ok" and result.sheet is not None
            answers = list(old.get("answers", [])) + [{"words": " ".join(words.split()), "at": runs._now()}]
            entry_talk = again.to_json() | {"answers": answers}
            if not ok:  # the passage on the sheet stays the earlier answer: its explanation too
                entry_talk.update(status=old["status"], explain=old["explain"], declared=old["declared"])
            summary: dict[str, Any] = {"hand": hand, "usd": round(usd, 4), "batches": int(ok), "total": 1, "run": run_id,
                                       "again": k + 1, **waiting}
            if not ok:
                log["batches"] = sorted([x for x in log["batches"] if x["k"] != k] + [entry_talk], key=lambda x: x["k"])
                log["usd"] = round(float(log.get("usd", 0.0)) + usd, 4)
                log["requests"] = int(log.get("requests", 0)) + requests
                runs.save(part_id, log)
                run.advanced(drawn.text, False)
                return {**summary, "style": "failed"}
            spliced = _style_drawn(current, [(passage, result.sheet)], staffs)
            before = [n for n in current.notes if n.staff in staffs and a <= n.frame < b]
            counts = style.copy_marks(
                spliced, reference=style._reference_sheet(current, reference), before=before, passage=passage,
                staffs=staffs,
            )
            entry_talk |= {"copied": dict(counts), "copiedText": style.copied_text(counts)}
            log["batches"] = sorted([x for x in log["batches"] if x["k"] != k] + [entry_talk], key=lambda x: x["k"])
            log["usd"] = round(float(log.get("usd", 0.0)) + usd, 4)
            log["requests"] = int(log.get("requests", 0)) + requests
            runs.save(part_id, log)
            run.advanced(f1.write(spliced, mode="frames"), True)
            ours = [n for n in result.sheet.notes if n.staff in staffs and not n.covered]
            entry = {
                "hand": hand, "reference": [reference[0], reference[1]], "words": " ".join(words.split()),
                "prompt": style.STYLE_VERSION, "run": run_id, "again": k + 1,
                "passages": [[a, b, "ok", passage.why]], "copied": dict(counts),
            }
            done = edits.apply_style(
                part_id, spliced, notes_revision=notes_revision, start=a, end=b, staff=HANDS[hand], wrote=ours,
                usd=usd, requests=requests, model=getattr(ask, "model", None),
                label=f"Passage {k + 1} written again with AI", entry=entry,
            )
            reporter.send(EVENT, {"phase": "saved"})
            return {**summary, "style": "ok" if done else "stale"}
        finally:
            with _live_lock:
                _live.pop(part_id, None)

    return _submit(part_id, work)


def costs(part_id: str) -> dict[str, Any]:
    """What each run of the Enhance with AI dialog would cost, about, before it starts (the dialog shows it): the
    windows of a whole run, a stretch, a level of each hand, in US dollars."""
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
    for hand in HANDS:
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


#: The longest batch the user may choose, in seconds of music: one request must still answer a whole batch.
BATCH_MAX_S = 90.0
#: The shortest one, about: a batch needs a few notes to be worth a request.
BATCH_MIN_S = 3.0


def batch_plan(
    part_id: str,
    *,
    run: str,
    hand: str = "both",
    start: int | None = None,
    end: int | None = None,
    batches: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """The batches a run of Enhance with AI would make (the user, 2026-10-30), for the dialog's preview on the sheet:
    ``run`` ``all`` (Write it all again), ``level`` (of the whole song, or of ``[start, end)``) or ``stretch``; the
    ``hand`` rewritten. ``batches`` (by default as many as the run makes today, one for a stretch, within ``min`` and
    ``max``) cut at about the same time (``split_windows``), which is what the run uses when the dialog sends that
    number. Also the cost and the minutes with ``model``: the run's estimate for the batches it makes today, half of
    it following the number of requests and half the music, times the model's ratio (``llm_models.ratio``)."""
    from aitu_backend.sheet.llm import levels  # noqa: PLC0415

    name = llm_models.resolve(model)
    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}.")
    staffs = (1, 2) if HANDS[hand] is None or run == "all" else (HANDS[hand],)
    current = f1.read(build.current(part_id).text)
    if run == "all":
        default = len(windows_of(current))
        usd, seconds = USD_CACHE + (default + 1) * USD_WINDOW, (default + 1) * SECONDS_WINDOW
        start = end = None
    elif run == "level":
        default = len(levels.level_windows(current, staffs, start, end))
        usd, seconds = USD_LEVEL_PLAN + default * USD_LEVEL_BATCH, SECONDS_LEVEL_PLAN + default * SECONDS_LEVEL_BATCH
    elif run == "stretch":
        if start is None or end is None:
            raise ValueError("A stretch needs its frames.")
        default = 1
        usd, seconds = USD_CACHE + USD_STRETCH, SECONDS_STRETCH
    else:
        raise ValueError(f"No run {run!r}.")
    whole = split_windows(current, 1, staffs=staffs, start=start, end=end)
    if not whole:
        raise ValueError("This hand has no notes here.")
    span_s = (whole[0][1] - whole[0][0]) * FRAME_MS / 1000
    low = max(1, math.ceil(span_s / BATCH_MAX_S))
    high = max(low, min(60, int(span_s // BATCH_MIN_S) or 1))
    default = min(high, max(low, default or 1))
    count = min(high, max(low, batches or default))
    windows = split_windows(current, count, staffs=staffs, start=start, end=end)
    usd_ratio, time_ratio = llm_models.ratio(name)
    scale = 0.5 + 0.5 * len(windows) / default
    return {
        "run": run,
        "hand": hand,
        "model": name,
        "windows": [[a, b] for a, b in windows],
        "count": len(windows),
        "default": default,
        "min": low,
        "max": high,
        "seconds": round(span_s / max(1, len(windows)), 1),
        "usd": round(usd * scale * usd_ratio, 2),
        "minutes": _minutes(seconds * scale * time_ratio),
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
