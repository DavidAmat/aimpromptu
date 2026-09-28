"""MuScriptor's note events to the sparse form, one event at a time.

MuScriptor's ``transcribe()`` is a generator (Phase 1, ``pocs/poc-muscriptor/RESULTS.md`` section 2):

* ``NoteStartEvent(pitch, start_time, index, instrument)`` when a note begins,
* ``NoteEndEvent(end_time, start_event)`` when it ends, possibly several chunks later,
* ``ProgressEvent(completed, total)`` once up front and once per 5-second chunk.

Times are seconds on a 10 ms grid, so they become whole milliseconds with no rounding error. There
is no velocity: every note gets 64.

:class:`MuScriptorAssembler` takes the events as they arrive, which is what the live stream of Phase
4 needs: at any moment it can say which notes are closed and which are still open. A note's id is
given when its start arrives, in arrival order, so the id the browser sees during the stream is the
id of the saved note. The events may be the library's objects or the dictionaries of the Phase 1
``.events.jsonl`` files (``{"type": "NoteStartEvent", "pitch": ...}``).

``lag_correction_ms`` is the per-piece timing fix of Phase 1 (report section 3.3): it is subtracted
from every onset and release when the notes are taken, never while they stream, because it is known
only at the end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

from aitu_backend.pmn.notes import KEY_COUNT, LOWEST_MIDI, Notes

__all__ = ["MUSCRIPTOR_FRAME_MS", "MuScriptorAssembler", "from_muscriptor_events"]

#: MuScriptor's time step: every start and end time is a multiple of it.
MUSCRIPTOR_FRAME_MS = 10

#: The only instrument kept by default. Every transcription is conditioned on it (Q-3).
PIANO = "acoustic_piano"


def _kind(event: Any) -> str:
    if isinstance(event, dict):
        return str(event.get("type", ""))
    return type(event).__name__


def _get(event: Any, name: str) -> Any:
    return event[name] if isinstance(event, dict) else getattr(event, name)


def _ms(seconds: float) -> int:
    return int(round(float(seconds) * 1000.0))


@dataclass
class _Open:
    note_id: int
    key: int
    on_ms: int


@dataclass
class MuScriptorAssembler:
    """Collects MuScriptor events into notes. Feed it with :meth:`add`, read it with :meth:`notes`."""

    first_id: int = 0
    #: ``None`` keeps every instrument.
    instruments: tuple[str, ...] | None = (PIANO,)
    #: Chunks done and chunks in all, from the last ``ProgressEvent``.
    completed: int = 0
    total: int = 0
    #: Notes left out: outside the 88 keys, or of an instrument not kept.
    skipped: int = 0
    #: Notes that ended at their own onset and were given one MuScriptor frame.
    zero_length: int = 0
    _next_id: int = field(init=False)
    #: MuScriptor's start index -> the open note.
    _open: dict[int, _Open] = field(default_factory=dict, init=False)
    #: key -> MuScriptor start index of the note open on that key.
    _open_on_key: dict[int, int] = field(default_factory=dict, init=False)
    #: (id, key, onMs, lenMs) of every closed note, in the order they closed.
    _closed: list[tuple[int, int, int, int]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._next_id = self.first_id

    def add(self, event: Any) -> None:
        kind = _kind(event)
        if kind == "NoteStartEvent":
            self._start(event)
        elif kind == "NoteEndEvent":
            if isinstance(event, dict):
                index = int(event["start_event_index"])
            else:
                index = int(getattr(event, "start_event_index", None) or event.start_event.index)
            self._end(index, _ms(_get(event, "end_time")))
        elif kind == "ProgressEvent":
            self.completed = int(_get(event, "completed"))
            self.total = int(_get(event, "total"))

    def add_all(self, events: Iterable[Any]) -> "MuScriptorAssembler":
        for event in events:
            self.add(event)
        return self

    def _start(self, event: Any) -> None:
        instrument = _get(event, "instrument")
        midi = int(_get(event, "pitch"))
        if (self.instruments is not None and instrument not in self.instruments) or not (
            LOWEST_MIDI <= midi < LOWEST_MIDI + KEY_COUNT
        ):
            self.skipped += 1
            return
        key = midi - LOWEST_MIDI
        on_ms = _ms(_get(event, "start_time"))
        # One key sounds one note at a time: a new onset ends the note still open on its key.
        previous = self._open_on_key.get(key)
        if previous is not None:
            self._end(previous, on_ms)
        index = int(_get(event, "index"))
        self._open[index] = _Open(note_id=self._next_id, key=key, on_ms=on_ms)
        self._open_on_key[key] = index
        self._next_id += 1

    def _end(self, index: int, end_ms: int) -> None:
        note = self._open.pop(index, None)
        if note is None:  # already closed by a new onset on its key, or a skipped note
            return
        if self._open_on_key.get(note.key) == index:
            del self._open_on_key[note.key]
        length = end_ms - note.on_ms
        if length <= 0:
            self.zero_length += 1
            length = MUSCRIPTOR_FRAME_MS
        self._closed.append((note.note_id, note.key, note.on_ms, length))

    # ----------------------------------------------------------------- reading

    @property
    def open_notes(self) -> list[tuple[int, int, int]]:
        """``(id, key, onMs)`` of the notes still sounding, in id order."""
        return sorted((note.note_id, note.key, note.on_ms) for note in self._open.values())

    @property
    def closed_count(self) -> int:
        return len(self._closed)

    def closed_since(self, position: int) -> list[tuple[int, int, int, int]]:
        """``(id, key, onMs, lenMs)`` of the notes closed after the first ``position`` ones."""
        return self._closed[position:]

    def notes(self, *, end_ms: float | None = None, lag_correction_ms: float = 0.0) -> Notes:
        """Every note so far, in canonical order. Notes still open end at ``end_ms``.

        Without ``end_ms`` the open notes are left out. The lag correction moves every onset and
        release earlier by that many milliseconds (later when negative), never before 0.
        """
        rows = list(self._closed)
        if end_ms is not None:
            for note in self._open.values():
                rows.append(
                    (
                        note.note_id,
                        note.key,
                        note.on_ms,
                        max(MUSCRIPTOR_FRAME_MS, int(end_ms) - note.on_ms),
                    )
                )
        table = np.array(rows, dtype=np.float64).reshape(-1, 4)
        on = np.maximum(0.0, table[:, 2] - lag_correction_ms)
        end = np.maximum(on + 1.0, table[:, 2] + table[:, 3] - lag_correction_ms)
        return Notes(id=table[:, 0], key=table[:, 1], on_ms=on, len_ms=end - on).sorted()


def from_muscriptor_events(
    events: Iterable[Any],
    *,
    end_ms: float | None = None,
    lag_correction_ms: float = 0.0,
    first_id: int = 0,
    instruments: tuple[str, ...] | None = (PIANO,),
) -> Notes:
    """Every note of a finished MuScriptor run. A note never closed ends at ``end_ms``.

    Without ``end_ms`` such a note ends at the last time the run mentions.
    """
    assembler = MuScriptorAssembler(first_id=first_id, instruments=instruments)
    last = 0
    for event in events:
        assembler.add(event)
        for name in ("start_time", "end_time"):
            if (isinstance(event, dict) and name in event) or hasattr(event, name):
                last = max(last, _ms(_get(event, name)))
    return assembler.notes(
        end_ms=last if end_ms is None else end_ms, lag_correction_ms=lag_correction_ms
    )
