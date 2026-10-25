"""Editing the new sheet of a part, with undo and redo (implementation 03, Phase 6; plan section 3.7).

An edit never changes a drawing. It changes the stored truth, under the part's lock, and the page draws the sheet
again (``build.current``):

* the **hands** in ``notes.pmn``, the numeric truth of plan section 3.7: one hand per note, by note id. A part whose
  hands were never saved as a whole first gets the hand the sheet draws for every note, so that the notes the user
  did not touch keep their place;
* the **stored sheet** ``sheet.f1`` (the reading: beam groups, clefs, 8va, ornaments, armaduras) is laid again on the
  new hands in the same write (``build.reapply``) and stored for them, so it stays current and keeps its record (the
  **Enhanced with AI** mark). A sheet the algorithm wrote is not stored: it is a function of the notes and their
  hands (``propose_frames``).

Every edit is one **step** of the part's log, ``sheet.edits.json``: the hand of each note it changed, before and
after, and the lines of ``sheet.f1`` it changed, both ways. Undo puts a step's before back, redo its after. A step
touches only what is still as it left it: a note whose hand something else changed since keeps that hand, and a
``sheet.f1`` that changed since is not patched (it is laid again on the hands, case 2 of :mod:`.build`). The log is
a file, so it survives a reload and another page; it keeps :data:`LIMIT` steps. An AI run that writes the sheet
again and a new transcription start it again (:func:`forget`). It is not copied with the part (duplicate, export,
Save to library): a copy starts without steps.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn import events_file
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS
from aitu_backend.sheet.sheet.frames import drawn_columns
from aitu_backend.storage import locate, paths
from aitu_backend.transcription import pipeline, saved_hands

from . import build, store

__all__ = ["LIMIT", "Moved", "forget", "history", "move_hands", "redo", "undo"]

#: Steps kept in the log: far more than anyone walks back (the old sheet keeps 100 in the page).
LIMIT = 50

HANDS = ("right", "left")


@dataclass(frozen=True)
class Moved:
    #: Notes whose hand changed.
    moved: int
    #: Notes asked for that the sheet does not hold (a ``frame:midi`` with no live note at that column and key).
    unmatched: int


@dataclass
class _Step:
    label: str
    #: ``note id -> (hand before, guessed before, hand after, guessed after)``.
    hands: dict[int, tuple[str | None, bool, str | None, bool]] = field(default_factory=dict)
    #: The change of ``sheet.f1``: the hash of the text before and after, and the line patches both ways.
    sheet: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "hands": [[i, *change] for i, change in self.hands.items()],
            "sheet": self.sheet,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "_Step":
        return cls(
            label=str(payload.get("label") or "Edit"),
            hands={
                int(row[0]): (row[1], bool(row[2]), row[3], bool(row[4]))
                for row in payload.get("hands") or []
            },
            sheet=payload.get("sheet"),
        )


@dataclass
class _Log:
    done: list[_Step] = field(default_factory=list)
    undone: list[_Step] = field(default_factory=list)


# ------------------------------------------------------------------ the log


def _path(part_id: str):
    return paths.part_frames_edits_path(part_id)


def _load(part_id: str) -> _Log:
    try:
        raw = json.loads(_path(part_id).read_text(encoding="utf-8"))
    except (locate.NotFound, OSError, ValueError):
        return _Log()
    return _Log(
        done=[_Step.from_json(s) for s in raw.get("done") or []],
        undone=[_Step.from_json(s) for s in raw.get("undone") or []],
    )


def _save(part_id: str, log: _Log) -> None:
    path = _path(part_id)
    body = {
        "done": [s.to_json() for s in log.done[-LIMIT:]],
        "undone": [s.to_json() for s in log.undone[-LIMIT:]],
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def forget(part_id: str) -> None:
    """Start the log again: the AI wrote the sheet again, or new notes replaced the old ones."""
    try:
        _path(part_id).unlink(missing_ok=True)
    except locate.NotFound:
        pass


def history(part_id: str) -> dict[str, str | None]:
    """What the next undo and the next redo are about, for the two buttons to say (``None``: nothing)."""
    log = _load(part_id)
    return {
        "undo": log.done[-1].label if log.done else None,
        "redo": log.undone[-1].label if log.undone else None,
    }


# ------------------------------------------------------------------ the patches of sheet.f1


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _patch(before: list[str], after: list[str]) -> list[list[Any]]:
    """The replacements that turn ``before`` into ``after``: ``[first line, end line, new lines]``. An edit changes
    one stretch of the sheet, so the lines the two texts share at the start and at the end are left out and the rest
    is one replacement (a full diff took 30 ms on a song)."""
    head = 0
    while head < min(len(before), len(after)) and before[head] == after[head]:
        head += 1
    if head == len(before) == len(after):
        return []
    tail = 0
    while (
        tail < min(len(before), len(after)) - head
        and before[len(before) - 1 - tail] == after[len(after) - 1 - tail]
    ):
        tail += 1
    return [[head, len(before) - tail, after[head : len(after) - tail]]]


def _apply(lines: list[str], ops: list[list[Any]]) -> list[str]:
    out = list(lines)
    for i1, i2, new in reversed(ops):
        out[i1:i2] = new
    return out


def _sheet_change(before: str, after: str) -> dict[str, Any] | None:
    if before == after:
        return None
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    return {
        "before": _hash(before),
        "after": _hash(after),
        "forward": _patch(a, b),
        "back": _patch(b, a),
    }


# ------------------------------------------------------------------ the edits


def _notes_at(events: list) -> dict[tuple[int, int], list[int]]:
    """The live note ids at each drawn column and sounding key: what a notehead's ``data-note="<frame>:<midi>"``
    names (the column of its group of onsets, D-04, as ``build.hands_of_sheet`` reads it)."""
    live = events_file.notes_from_events(events).live()
    if len(live) == 0:
        return {}
    _, start = drawn_columns(live.on_ms)
    column = np.floor(np.round(start / FRAME_MS, 9) + 0.5).astype(np.int64)
    at: dict[tuple[int, int], list[int]] = {}
    for i in range(len(live)):
        at.setdefault((int(column[i]), int(live.key[i]) + LOWEST_MIDI), []).append(int(live.id[i]))
    return at


def _ref(ref: str) -> tuple[int, int] | None:
    try:
        frame, midi = ref.split(":")
        return int(frame), int(midi)
    except ValueError:
        return None


def _write_hands(part_id: str, stored: Any, *, before: Any) -> Any:
    return pipeline.save_edit(
        part_id,
        stored.events,
        stored.duration_seconds,
        stored.title,
        before=before,
        notes_changed=False,
        hands_changed=True,
        # The old sheet (vexflow-v2) draws from the same hands: a hand moved here does not make it stale, as a hand
        # moved there does not (``PUT /time/{uuid}/hands``).
        sheet_follows=True,
    )


def move_hands(part_id: str, refs: list[str], hand: str) -> Moved:
    """Give the notes ``refs`` (``"<frame>:<midi>"``, as the noteheads name them) to ``hand``: one step."""
    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}")
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        drawn = build.current(part_id)
        at = _notes_at(stored.events)
        wanted: set[int] = set()
        unmatched = 0
        for ref in refs:
            place = _ref(ref)
            ids = at.get(place) if place is not None else None
            if not ids:
                unmatched += 1
                continue
            wanted.update(ids)

        by_id = {event.id: event for event in stored.events if event.id is not None}
        was = {i: (e.hand, e.hand_guessed) for i, e in by_id.items()}
        if wanted and not saved_hands.hands_complete(stored.events):
            # The hands were never saved as a whole: every note first keeps the hand the sheet draws now.
            notes = events_file.notes_from_events(stored.events)
            for note_id, side in build.hands_of_sheet(f1.read(drawn.text), notes).items():
                event = by_id.get(note_id)
                if event is not None and (event.hand is None or event.hand_guessed):
                    event.hand, event.hand_guessed = side, False
        moved = 0
        for note_id in wanted:
            event = by_id[note_id]
            if event.hand != hand or event.hand_guessed:
                event.hand, event.hand_guessed = hand, False
                moved += 1
        if moved == 0:
            return Moved(0, unmatched)
        changes = {
            i: (*was[i], e.hand, e.hand_guessed)
            for i, e in by_id.items()
            if (e.hand, e.hand_guessed) != was[i]
        }
        saved = _write_hands(part_id, stored, before=stored.header)

        sheet_change = None
        kept = store.load(part_id)
        if kept is not None and kept.record.source != "algorithm":
            # The reading the user sees now, laid on the new hands and stored for them: the moved notes leave their
            # beam groups, the figures of their neighbours follow the new hands (``build.reapply``).
            after = f1.write(
                build.reapply(f1.read(drawn.text), pipeline.starting_hands(part_id)), mode="frames"
            )
            kept.record.hands_revision = saved.header.hands_revision
            store.save(part_id, after, kept.record)
            sheet_change = _sheet_change(drawn.text, after)
        build.forget(part_id)

        label = f"Move {'a note' if moved == 1 else f'{moved} notes'} to the {hand} hand"
        log = _load(part_id)
        log.done.append(_Step(label, changes, sheet_change))
        log.undone.clear()
        _save(part_id, log)
        return Moved(moved, unmatched)


def _saved(hand: str | None, guessed: bool) -> str | None:
    """The hand a person or the AI decided, or ``None``: a guessed hand (``save_edit``'s quick rule fills the notes
    without one once the hands were saved as a whole) is no decision, the split decides it."""
    return None if guessed else hand


def _walk(part_id: str, to: str) -> str | None:
    back = to == "undo"
    with pipeline.piece_lock(part_id):
        log = _load(part_id)
        steps = log.done if back else log.undone
        if not steps:
            return None
        step = steps.pop()
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        header = stored.header
        by_id = {event.id: event for event in stored.events if event.id is not None}
        changed = False
        for note_id, (hand_before, guessed_before, hand_after, guessed_after) in step.hands.items():
            event = by_id.get(note_id)
            now = (hand_after, guessed_after) if back else (hand_before, guessed_before)
            then = (hand_before, guessed_before) if back else (hand_after, guessed_after)
            # Only a note still as the step left it: a hand changed by something else since stays.
            if event is None or _saved(event.hand, event.hand_guessed) != _saved(*now):
                continue
            event.hand, event.hand_guessed = then
            changed = True
        revision = header.hands_revision
        if changed:
            revision = _write_hands(part_id, stored, before=header).header.hands_revision

        kept = store.load(part_id)
        change = step.sheet
        if (
            change is not None
            and kept is not None
            and kept.record.hands_revision == header.hands_revision
        ):
            # Patched only when sheet.f1 is the one the step left, for the hands it left: otherwise it is laid again
            # on the hands when drawn.
            expected, wanted, ops = (
                (change["after"], change["before"], change["back"])
                if back
                else (change["before"], change["after"], change["forward"])
            )
            if _hash(kept.text) == expected:
                text = "".join(_apply(kept.text.splitlines(keepends=True), ops))
                if _hash(text) == wanted:
                    kept.record.hands_revision = revision
                    store.save(part_id, text, kept.record)
        build.forget(part_id)
        (log.undone if back else log.done).append(step)
        _save(part_id, log)
        return step.label


def undo(part_id: str) -> str | None:
    """Take the last step back; its label, or ``None`` when there is none."""
    return _walk(part_id, "undo")


def redo(part_id: str) -> str | None:
    """Put the last step taken back again; its label, or ``None``."""
    return _walk(part_id, "redo")
