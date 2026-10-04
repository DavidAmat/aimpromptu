"""The operations of the piano roll visualization, applied to the notes of a piece.

Plan section 6.4. The page never sends the whole piece: it sends a list of operations on notes
named by their id, and the backend applies them in order.

========== ==================================================== =======================
``op``     Fields                                               Changes
========== ==================================================== =======================
``move``   ``id``, ``onMs``, ``lenMs``, optional ``key``        the notes (move, resize)
``delete`` ``ids``                                              the notes (marked removed)
``restore````ids``                                              the notes (put back)
``add``    ``tempId`` (negative), ``key``, ``onMs``, ``lenMs``, the notes
           optional ``hand``
``hand``   ``ids``, ``hand`` (``r`` or ``l``)                   the hands
========== ==================================================== =======================

A deleted note is marked removed, not dropped: it keeps its id, so it can be put back, and every
view leaves it out. Times are milliseconds of the piece.

**One key sounds one note at a time.** After the operations, on every key an operation touched, a
note that runs into the next onset of its key is shortened to that onset, which is the rule of the
piano roll visualization (plan section 9.5). Two notes of one key that start at the same time are
refused: one of them would have no length. Keys no operation touched are left as they are.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.matrix.keys import KEY_COUNT, LOWEST_MIDI
from aitu_backend.transcription.engine import NoteEvent

#: Two onsets of one key closer than this are the same onset, in milliseconds.
SAME_ONSET_MS = 0.5

#: A note may end this much after the piece, in milliseconds: the wire rounds to whole ms.
END_TOLERANCE_MS = 1.0

_HANDS = {"r": "right", "l": "left"}


class _Op(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class MoveOp(_Op):
    op: Literal["move"]
    id: int = Field(..., ge=0)
    on_ms: float = Field(..., alias="onMs", ge=0)
    len_ms: float = Field(..., alias="lenMs", gt=0)
    #: A move with Shift held also changes the key.
    key: int | None = Field(None, ge=0, lt=KEY_COUNT)


class DeleteOp(_Op):
    op: Literal["delete"]
    ids: list[int] = Field(..., min_length=1)


class RestoreOp(_Op):
    op: Literal["restore"]
    ids: list[int] = Field(..., min_length=1)


class AddOp(_Op):
    op: Literal["add"]
    #: The page's own name for the new note, negative so it can never be a real id. The answer
    #: gives the id the backend chose for it.
    temp_id: int = Field(..., alias="tempId", lt=0)
    key: int = Field(..., ge=0, lt=KEY_COUNT)
    on_ms: float = Field(..., alias="onMs", ge=0)
    len_ms: float = Field(..., alias="lenMs", gt=0)
    hand: Literal["r", "l"] | None = None


class HandOp(_Op):
    op: Literal["hand"]
    ids: list[int] = Field(..., min_length=1)
    hand: Literal["r", "l"]


Operation = Annotated[Union[MoveOp, DeleteOp, RestoreOp, AddOp, HandOp], Field(discriminator="op")]


class EditRefused(ValueError):
    """An operation that cannot be applied. The message is shown to the user as it is."""


@dataclass
class Applied:
    """What the operations did. The events list given was changed in place."""

    notes_changed: bool = False
    hands_changed: bool = False
    #: ``tempId -> the new note``; the note gets its id when it is saved.
    added: dict[int, NoteEvent] = field(default_factory=dict)
    #: Notes the backend changed beyond what an operation asked: shortened by the same-key rule.
    adjusted: list[NoteEvent] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.notes_changed or self.hands_changed


def apply_ops(events: list[NoteEvent], duration_ms: float, ops: list[Operation]) -> Applied:
    """Apply ``ops`` in order to ``events`` (changed in place). Raises :class:`EditRefused`."""
    by_id = {event.id: event for event in events if event.id is not None}
    applied = Applied()
    touched: set[int] = set()  # Python ids of the note objects an operation placed or moved
    keys: set[int] = set()  # MIDI notes to check for the same-key rule

    def note(note_id: int, where: str, *, live: bool = False) -> NoteEvent:
        event = by_id.get(note_id)
        if event is None:
            raise EditRefused(f"{where}: there is no note {note_id} in this piece.")
        if live and event.removed:
            raise EditRefused(f"{where}: note {note_id} was deleted. Restore it first.")
        return event

    def check_span(on_ms: float, len_ms: float, where: str) -> None:
        if on_ms + len_ms > duration_ms + END_TOLERANCE_MS:
            raise EditRefused(
                f"{where}: the note would end at {on_ms + len_ms:.0f} ms, after the end of the "
                f"piece ({duration_ms:.0f} ms)."
            )

    for index, op in enumerate(ops, start=1):
        where = f"Operation {index} ({op.op})"
        if isinstance(op, MoveOp):
            event = note(op.id, where, live=True)
            check_span(op.on_ms, op.len_ms, where)
            keys.add(event.midi_note)
            if op.key is not None:
                event.midi_note = op.key + LOWEST_MIDI
            event.start = op.on_ms / 1000.0
            event.end = (op.on_ms + op.len_ms) / 1000.0
            keys.add(event.midi_note)
            touched.add(id(event))
            applied.notes_changed = True
        elif isinstance(op, DeleteOp):
            for note_id in op.ids:
                event = note(note_id, where)
                if not event.removed:
                    event.removed = True
                    applied.notes_changed = True
        elif isinstance(op, RestoreOp):
            for note_id in op.ids:
                event = note(note_id, where)
                if event.removed:
                    event.removed = False
                    keys.add(event.midi_note)
                    touched.add(id(event))
                    applied.notes_changed = True
        elif isinstance(op, AddOp):
            if op.temp_id in applied.added:
                raise EditRefused(f"{where}: tempId {op.temp_id} is used twice.")
            check_span(op.on_ms, op.len_ms, where)
            event = NoteEvent(
                midi_note=op.key + LOWEST_MIDI,
                start=op.on_ms / 1000.0,
                end=(op.on_ms + op.len_ms) / 1000.0,
                hand=_HANDS[op.hand] if op.hand else None,
            )
            events.append(event)
            applied.added[op.temp_id] = event
            keys.add(event.midi_note)
            touched.add(id(event))
            applied.notes_changed = True
            applied.hands_changed = applied.hands_changed or op.hand is not None
        elif isinstance(op, HandOp):
            hand = _HANDS[op.hand]
            for note_id in op.ids:
                event = note(note_id, where)
                if event.hand != hand or event.hand_guessed:
                    event.hand = hand
                    event.hand_guessed = False
                    applied.hands_changed = True

    applied.adjusted = _one_note_per_key(events, keys, touched)
    events.sort(key=lambda event: (event.start, event.midi_note))
    return applied


def _one_note_per_key(
    events: list[NoteEvent], keys: set[int], touched: set[int]
) -> list[NoteEvent]:
    """Shorten a note that runs into the next onset of its key, on the keys an operation touched.

    Only a pair where one of the two notes was placed or moved by an operation is changed, so an
    overlap already in an old transcription stays as it was.
    """
    adjusted: list[NoteEvent] = []
    for midi in keys:
        row = sorted(
            (event for event in events if event.midi_note == midi and not event.removed),
            key=lambda event: (event.start, event.id if event.id is not None else -1),
        )
        for earlier, later in zip(row, row[1:]):
            if id(earlier) not in touched and id(later) not in touched:
                continue
            if (later.start - earlier.start) * 1000.0 < SAME_ONSET_MS:
                raise EditRefused(
                    f"Two notes of key {midi - LOWEST_MIDI} would start at the same time "
                    f"({earlier.start * 1000.0:.0f} ms). One key sounds one note at a time."
                )
            if earlier.end > later.start:
                earlier.end = later.start
                adjusted.append(earlier)
    return adjusted
