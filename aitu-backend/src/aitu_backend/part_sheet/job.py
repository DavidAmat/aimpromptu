"""Sonnet writes the sheet of a part in the background, window by window (implementation 03, Phase 5; plan 3.6).

:func:`start` submits one job per part (key ``sheet-llm:<part>``; a second start returns the running one). The job:

1. reads the notes with their starting hands (``pipeline.starting_hands``) and runs the LLM step of Phase 4
   (``sheet.llm.frames.write_frames``) with Sonnet 5.5 (``sheet_llm.ClaudeComplete``);
2. keeps the sheet of the moment in memory (:class:`LiveRun`): the reference request first (the page shows the
   sheet it had, its first segment being improved), then the algorithm with Sonnet's reference figure, then each
   window's decisions as it comes back (``assemble`` of the parts so far and the algorithm's parts for the rest);
3. sends an ``event: sheet`` message on the job's stream at each of those moments, so the page reads the sheet again;
4. at the end writes the hands of the sheet into ``notes.pmn`` (the numeric truth, plan section 3.7; the hands that
   were saved before go to the part's history first) and the sheet into ``sheet.f1`` (:mod:`.store`). When no
   window was written by Sonnet (no credits, no network), the hands stay as they were and ``sheet.f1`` keeps the
   algorithm's sheet, so the page does not start again by itself; it says nothing alarming (plan section 3.8).

The notes may change while Sonnet works (the Notes step). The job then stores what it wrote for the notes it read,
without touching the hands, and the page lays it on the current notes (``build.reapply``). A part deleted while Sonnet
works stops the requests at the next one (:class:`PartGone`): no credits are spent on a project that is gone.
"""

from __future__ import annotations

import importlib.util
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from aitu_backend.editing import history
from aitu_backend.pmn import events_file
from aitu_backend.progress import BaseProgress
from aitu_backend.sheet.llm.frames import (
    PROMPT_VERSION,
    Complete,
    Part,
    WindowLog,
    _algorithm_part,
    assemble,
    write_frames,
)
from aitu_backend.sheet.proposal.frames import FramesProposal
from aitu_backend.sheet.sheet import f1
from aitu_backend.transcription import jobs, pipeline

from . import build, store

__all__ = ["LiveRun", "available", "commit", "job_of", "live", "start"]

#: The job key of a part: one Sonnet run at a time per part.
KEY = "sheet-llm:{}"
#: The name of the stream's messages (an ``EventSource`` listener of that name receives them).
EVENT = "sheet"


def available() -> bool:
    """Whether Sonnet can be asked: an API key in the environment and the SDK installed."""
    return (
        bool(os.environ.get("ANTHROPIC_API_KEY"))
        and importlib.util.find_spec("anthropic") is not None
    )


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
    _text: tuple[int, str] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

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
        sheet, _ = assemble(algo, parts + rest)
        text = f1.write(sheet, mode="frames")
        with self._lock:
            self._text = (len(parts), text)
        return text

    def segments(self) -> list[tuple[int, int, str]]:
        """Each segment and its state: ``llm`` or ``algorithm`` (decided), ``working`` (at Sonnet), ``waiting``."""
        with self._lock:
            if self.algo is None:
                return [
                    (a, b, "working" if k == 0 else "waiting")
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


def _complete() -> Any:
    from aitu_backend.sheet_llm import (
        ClaudeComplete,
    )  # noqa: PLC0415 - the SDK only when it is used

    return ClaudeComplete()


def start(part_id: str, *, complete: Callable[[], Complete] | None = None) -> jobs.Job:
    """Start Sonnet on a part, or return the run already going. ``complete`` makes the ``complete`` function
    (tests); by default Claude with the key of ``.env``."""
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
        run = LiveRun(part_id, before.text, build.windows(f1.read(before.text)))
        with _live_lock:
            _live[part_id] = run
        try:
            ask = (complete or _complete)()
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

            song = write_frames(notes, asked, sid=part_id[:8], on_start=on_start, on_part=on_part)
            if not pipeline.has_events(part_id):
                return {
                    "source": "gone",
                    "windows": 0,
                    "usd": round(float(getattr(ask, "usd", 0.0) or 0.0), 4),
                }
            calls = getattr(ask, "calls", [])  # the requests made, with their cost
            sources = [part.source for part in song.parts]
            record = store.Record(
                source=(
                    "llm"
                    if sources and all(s == "llm" for s in sources)
                    else "mixed" if "llm" in sources else "algorithm"
                ),
                windows=[[p.start, p.end, p.source] for p in song.parts],
                quarter_ms=song.quarter_ms,
                reference=song.reference.get("source"),
                model=getattr(ask, "model", None),
                prompt=PROMPT_VERSION,
                usd=float(getattr(ask, "usd", 0.0) or 0.0),
                requests=len(calls),
                written=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                note=next((w.note for w in song.windows if w.note), None)
                or song.reference.get("note"),
            )
            commit(part_id, song.sheet, song.text, record, header.notes_revision)
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


def commit(part_id: str, sheet: Any, text: str, record: store.Record, notes_revision: int) -> None:
    """Write the hands of the sheet into ``notes.pmn`` and the sheet into ``sheet.f1``, under the part's lock."""
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
            return
        if record.source != "algorithm":
            notes = events_file.notes_from_events(stored.events)
            hands = build.hands_of_sheet(sheet, notes)
            changed = [
                event
                for event in stored.events
                if event.id in hands and (event.hand != hands[event.id] or event.hand_guessed)
            ]
            if changed:
                if header.hands_notes_revision > 0:
                    # The saved hands were decided before (Predict hands and the user's corrections): kept.
                    history.snapshot_notes(
                        part_id, reason="The AI wrote the hands of the sheet again"
                    )
                for event in changed:
                    event.hand = hands[event.id]
                    event.hand_guessed = False
                saved = pipeline.save_edit(
                    part_id,
                    stored.events,
                    stored.duration_seconds,
                    stored.title,
                    before=header,
                    notes_changed=False,
                    hands_changed=True,
                )
                header = saved.header
        record.hands_revision = header.hands_revision
        store.save(part_id, text, record)
    build.forget(part_id)
