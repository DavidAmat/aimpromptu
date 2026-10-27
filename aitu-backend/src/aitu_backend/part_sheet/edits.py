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

Phase 7 adds the other edits, each one step:

* **reading edits** (:func:`edit_reading`, the functions of :mod:`.reading`: figures, fingers, beams, the grace
  note switch, ornaments, the armadura, clefs and 8va of a stretch): the sheet drawn now is changed, laid again on
  the notes (``build.reapply``, so the rules run and keep the decisions), checked to still hold what was asked, and
  stored. A sheet the algorithm wrote is then stored too, marked ``edited`` (``store.Record``);
* **notes taken off the page** (:func:`remove_notes`): marked removed in ``notes.pmn``, as the Notes step does; the
  step keeps which notes, and undo puts them back;
* **a stretch the AI wrote again** with the user's words (:func:`apply_stretch`, from ``job.start_stretch``): its
  hands and its sheet, as one step.

Phase 8B adds **a paste** (:func:`paste_passage`): a copied passage put in at a frame, or over a marked stretch, with
its notes, its sheet and its audio, everything after it moved (``editing.paste``). The paste keeps the part as it was
as a snapshot of its history, so its step holds two versions, not changes: undo puts the snapshot back (which keeps
the pasted state as the next one), redo puts that one back. The steps before it stay valid after its undo.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np

from aitu_backend.editing import history as part_history
from aitu_backend.editing import paste
from aitu_backend.matrix.keys import KEY_COUNT, LOWEST_MIDI
from aitu_backend.pmn import events_file
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import FRAME_MS, Sheet
from aitu_backend.sheet.sheet.figures import FIGURES, nominal_ms
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.sheet.sheet.frames import drawn_columns
from aitu_backend.storage import locate, paths
from aitu_backend.transcription import pipeline, saved_hands

from . import build, reading, store

__all__ = [
    "LIMIT",
    "Moved",
    "Pasted",
    "Transposed",
    "add_note",
    "apply_stretch",
    "change_notes",
    "edit_reading",
    "forget",
    "history",
    "move_hands",
    "note_ends",
    "paste_passage",
    "preview_reading",
    "record_run",
    "record_version",
    "redo",
    "remove_notes",
    "transpose_notes",
    "undo",
]

#: The highest key of the piano (MIDI).
HIGHEST_MIDI = LOWEST_MIDI + KEY_COUNT - 1

#: Steps kept in the log: far more than anyone walks back (the old sheet keeps 100 in the page).
LIMIT = 50

HANDS = ("right", "left")

#: The step of the notes a whole AI run added and left out (implementation 04, Phase 3).
RUN_LABEL = "Notes the AI added and left out"


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
    #: ``note id -> (removed before, removed after)``: notes taken off the page (Phase 7).
    removed: dict[int, tuple[bool, bool]] = field(default_factory=dict)
    #: ``note id -> (key before, key after)`` (MIDI): notes transposed (Phase 8).
    keys: dict[int, tuple[int, int]] = field(default_factory=dict)
    #: A paste (Phase 8B): ``[the snapshot undo puts back, the one redo puts back]`` of the part's history (the
    #: second is known after the first undo). Each walk puts one back and keeps the other state as a new snapshot.
    versions: list[int] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "hands": [[i, *change] for i, change in self.hands.items()],
            "sheet": self.sheet,
            "removed": [[i, *change] for i, change in self.removed.items()],
            "keys": [[i, *change] for i, change in self.keys.items()],
            "versions": self.versions,
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
            removed={
                int(row[0]): (bool(row[1]), bool(row[2])) for row in payload.get("removed") or []
            },
            keys={int(row[0]): (int(row[1]), int(row[2])) for row in payload.get("keys") or []},
            versions=[int(v) for v in payload["versions"]] if payload.get("versions") else None,
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


def note_ends(events: list) -> dict[str, int]:
    """The frame each drawn note stops sounding at, by its notehead's ref ``"<frame>:<midi>"`` (the keyboard panel of
    Phase 8 lights the keys still held under the cursor); two notes of one key and column: the longer.
    """
    at = _notes_at(events)
    by_id = {event.id: event for event in events if event.id is not None}
    return {
        f"{frame}:{midi}": int(round(max(by_id[i].end for i in ids) * 1000 / FRAME_MS))
        for (frame, midi), ids in at.items()
    }


def _ref(ref: str) -> tuple[int, int] | None:
    try:
        frame, midi = ref.split(":")
        return int(frame), int(midi)
    except ValueError:
        return None


def _write_hands(
    part_id: str, stored: Any, *, before: Any, hands: bool = True, notes: bool = False
) -> Any:
    return pipeline.save_edit(
        part_id,
        stored.events,
        stored.duration_seconds,
        stored.title,
        before=before,
        notes_changed=notes,
        hands_changed=hands,
        # The old sheet (vexflow-v2) draws from the same hands: a hand moved here does not make it stale, as a hand
        # moved there does not (``PUT /time/{uuid}/hands``).
        sheet_follows=True,
    )


def _record(step: _Step, part_id: str) -> None:
    log = _load(part_id)
    log.done.append(step)
    log.undone.clear()
    _save(part_id, log)


def _ids_of(events: list, refs: list[str]) -> tuple[set[int], int]:
    """The live note ids that ``refs`` name, and how many refs named none."""
    at = _notes_at(events)
    wanted: set[int] = set()
    unmatched = 0
    for ref in refs:
        place = _ref(ref)
        ids = at.get(place) if place is not None else None
        if not ids:
            unmatched += 1
            continue
        wanted.update(ids)
    return wanted, unmatched


def move_hands(part_id: str, refs: list[str], hand: str) -> Moved:
    """Give the notes ``refs`` (``"<frame>:<midi>"``, as the noteheads name them) to ``hand``: one step."""
    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}")
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        drawn = build.current(part_id)
        wanted, unmatched = _ids_of(stored.events, refs)

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
        if kept is not None and kept.record.decided:
            # The reading the user sees now, laid on the new hands and stored for them: the moved notes leave their
            # beam groups, the figures of their neighbours follow the new hands (``build.reapply``).
            after = f1.write(
                build.reapply(f1.read(drawn.text), pipeline.starting_hands(part_id)), mode="frames"
            )
            kept.record.hands_revision = saved.header.hands_revision
            store.save(part_id, after, kept.record)
            build.mark_settled(part_id, after)
            sheet_change = _sheet_change(drawn.text, after)
        build.forget(part_id)

        label = f"Move {'a note' if moved == 1 else f'{moved} notes'} to the {hand} hand"
        _record(_Step(label, changes, sheet_change), part_id)
        return Moved(moved, unmatched)


def remove_notes(part_id: str, refs: list[str]) -> Moved:
    """Take the notes ``refs`` off the page: marked removed in ``notes.pmn`` (a transcriber's note made of a pedal
    blur, for example), as the Notes step does; one step, which puts them back. ``Moved.moved`` counts them.
    """
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        drawn = build.current(part_id)
        wanted, unmatched = _ids_of(stored.events, refs)
        by_id = {event.id: event for event in stored.events if event.id is not None}
        gone = {i: (False, True) for i in wanted if not by_id[i].removed}
        if not gone:
            return Moved(0, unmatched)
        for i in gone:
            by_id[i].removed = True
        saved = _write_hands(part_id, stored, before=stored.header, hands=False, notes=True)
        sheet_change = None
        kept = store.load(part_id)
        if kept is not None and kept.record.decided:
            after = f1.write(
                build.reapply(f1.read(drawn.text), pipeline.starting_hands(part_id)), mode="frames"
            )
            kept.record.hands_revision = saved.header.hands_revision
            store.save(part_id, after, kept.record)
            build.mark_settled(part_id, after)
            sheet_change = _sheet_change(drawn.text, after)
        build.forget(part_id)
        k = len(gone)
        label = f"Take {'a note' if k == 1 else f'{k} notes'} off the page"
        _record(_Step(label, {}, sheet_change, gone), part_id)
        return Moved(k, unmatched)


def edit_reading(
    part_id: str,
    change: Callable[[Sheet], str],
    holds: Callable[[Sheet], str | None] | None = None,
) -> str | None:
    """One reading edit (Phase 7): ``change`` changes the sheet drawn now and returns the step's label (or raises
    ``reading.Refused``). The result is laid again on the notes, so the rules run with the new decision, and
    ``holds`` says why the settled sheet does not hold what was asked (``None``: it does); then it is stored, the
    record marked ``edited``, and the step written. Returns the label, or ``None`` when nothing changed.
    """
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        drawn, label, settled, after = _settled(part_id, change, holds)
        if after == drawn.text:
            return None
        kept = store.load(part_id)
        record = (
            kept.record
            if kept is not None
            else store.Record(source="algorithm", quarter_ms=drawn.quarter_ms)
        )
        record.edited = True
        record.hands_revision = stored.header.hands_revision
        if settled.quarter_ms != drawn.quarter_ms:
            # Transpose figures (Phase 8): the user named the reference figure; a new AI run keeps it.
            record.quarter_ms, record.reference = settled.quarter_ms, "user"
        store.save(part_id, after, record)
        build.mark_settled(part_id, after)
        build.forget(part_id)
        _record(_Step(label, {}, _sheet_change(drawn.text, after)), part_id)
        return label


def preview_reading(
    part_id: str,
    change: Callable[[Sheet], str],
    holds: Callable[[Sheet], str | None] | None = None,
) -> tuple[str, str]:
    """What :func:`edit_reading` would store, without storing it (the preview of Transpose figures, Phase 8): the
    step's label and the sheet's text."""
    _, label, _, after = _settled(part_id, change, holds)
    return label, after


def _settled(
    part_id: str, change: Callable[[Sheet], str], holds: Callable[[Sheet], str | None] | None
) -> tuple[Any, str, Sheet, str]:
    drawn = build.current(part_id)
    sheet = f1.read(drawn.text)
    known = set(frames.check(sheet))
    label = change(sheet)
    settled = build.reapply(sheet, pipeline.starting_hands(part_id))
    why = holds(settled) if holds is not None else None
    if why:
        raise reading.Refused(why)
    # A safety net: an edit never leaves the sheet breaking a rule of the product it did not break before.
    broken = [p for p in frames.check(settled) if p not in known]
    if broken:
        raise reading.Refused(f"The sheet would break one of its rules: {broken[0]}.")
    return drawn, label, settled, f1.write(settled, mode="frames")


def apply_stretch(
    part_id: str,
    spliced: Sheet,
    *,
    notes_revision: int,
    start: int,
    end: int,
    words: str,
    usd: float,
    requests: int,
    model: str | None,
) -> bool:
    """Store a stretch the AI wrote again (Phase 7, ``job.start_stretch``): the hands of ``spliced`` into
    ``notes.pmn``, the notes of the stretch it left out taken off the page (removed in ``notes.pmn``, as
    :func:`remove_notes` does: the user asked for it, for example single notes instead of octaves), and the sheet,
    settled on them, into ``sheet.f1``, as one step. A sheet the algorithm wrote becomes ``mixed`` (the AI wrote part
    of it: **Enhanced with AI**). Returns ``False`` without writing when the notes changed while the AI worked.
    """
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None or stored.header.notes_revision != notes_revision:
            return False
        drawn = build.current(part_id)
        kept_places = {(n.frame, n.midi) for n in spliced.notes if start <= n.frame < end}
        shown = {
            (n.frame, n.midi): n.figure for n in f1.read(drawn.text).notes if start <= n.frame < end
        }
        now_places = set(shown)
        quarter = spliced.quarter_ms or drawn.quarter_ms or 500.0
        added = [
            n
            for n in spliced.notes
            if start <= n.frame < end and (n.frame, n.midi) not in now_places
        ]
        gone = change_notes(stored, now_places - kept_places, added, quarter)
        by_id = {event.id: event for event in stored.events if event.id is not None}
        notes = events_file.notes_from_events(stored.events)
        hands = build.hands_of_sheet(spliced, notes)
        was = {i: (e.hand, e.hand_guessed) for i, e in by_id.items()}
        complete = saved_hands.hands_complete(stored.events)
        for note_id, side in hands.items():
            event = by_id.get(note_id)
            if event is None:
                continue
            # Every note the sheet holds gets its hand when the hands were never saved as a whole; else the
            # changed ones.
            if not complete or event.hand != side or event.hand_guessed:
                event.hand, event.hand_guessed = side, False
        changes = {
            i: (*was[i], e.hand, e.hand_guessed)
            for i, e in by_id.items()
            if (e.hand, e.hand_guessed) != was[i]
        }
        revision = stored.header.hands_revision
        if changes or gone:
            revision = _write_hands(
                part_id, stored, before=stored.header, hands=bool(changes), notes=bool(gone)
            ).header.hands_revision
        notes_now = pipeline.starting_hands(part_id)
        settled = build.reapply(spliced, notes_now)
        # The figures the AI wrote are the ones the sheet prints, as set by hand, where the rule now gives another
        # one: the notes may have changed under them (a chord without its octave is shorter), and the user's words
        # may ask to keep the figures or to set others. A note the AI wrote that the rule makes a grace note is
        # written as the AI wrote it, unless it was a grace note already. Notes are found a frame or two away too
        # (the drawn column of a chord moves when its first note is taken off).
        wrote = {
            (n.frame, n.midi): n.figure
            for n in spliced.notes
            if start <= n.frame < end and n.figure in FIGURES
        }
        graces = {
            (n.frame, n.midi)
            for n in f1.read(drawn.text).notes
            if n.grace and start <= n.frame < end
        }

        def written(place: tuple[int, int]) -> tuple[int | None, tuple[int, int]]:
            for d in (0, -1, -2, 1, 2):
                near = (place[0] + d, place[1])
                if near in wrote:
                    return wrote[near], near
            return None, place

        fixed = 0
        for n in settled.notes:
            if n.covered or n.frame is None:
                continue
            figure, place = written((n.frame, n.midi))
            if figure is None or (n.grace and place in graces):
                continue
            if n.grace or n.figure != figure:
                n.figure, n.fixed, n.grace_rule = figure, True, None
                fixed += 1
        if fixed:
            settled = build.reapply(settled, notes_now)
        after = f1.write(settled, mode="frames")
        kept = store.load(part_id)
        record = (
            kept.record
            if kept is not None
            else store.Record(source="algorithm", quarter_ms=drawn.quarter_ms)
        )
        if record.source == "algorithm":
            record.source = "mixed"
        record.edited = record.edited or fixed > 0
        record.usd += usd
        record.requests += requests
        record.model = model or record.model
        written = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record.stretches.append([start, end, words, round(usd, 4), written])
        record.hands_revision = revision
        store.save(part_id, after, record)
        build.forget(part_id)
        _record(
            _Step("Enhance a stretch with AI", changes, _sheet_change(drawn.text, after), gone),
            part_id,
        )
        return True


def change_notes(
    stored: Any, left: set[tuple[int, int]], added: list[Any], quarter_ms: float
) -> dict[int, tuple[bool, bool]]:
    """Notes the AI left out and added (a stretch, Phase 7; the rules of simplicity of a whole run, implementation 04,
    Phase 3), changed in ``stored.events`` (not written): the live notes at the drawn columns and keys ``left``
    marked removed, as :func:`remove_notes` does; each note of ``added`` (sheet notes) a new note at the onset of the
    column it joins (or of its frame), as long as its measured length or its figure, in the hand of its staff, as
    loud as the notes of its column. Returns the step's ``note id -> (removed before, removed after)``: undo takes
    the added notes off again and puts the others back."""
    by_id = {event.id: event for event in stored.events if event.id is not None}
    at = _notes_at(stored.events)
    gone = {i: (False, True) for place in left for i in at.get(place, []) if not by_id[i].removed}
    for i in gone:
        by_id[i].removed = True
    onset: dict[int, float] = {}
    loud: dict[int, list[int]] = {}
    for (column, _), ids in at.items():
        onset[column] = min([onset.get(column, float("inf"))] + [by_id[i].start for i in ids])
        loud.setdefault(column, []).extend(by_id[i].velocity for i in ids)
    every = [e.velocity for e in stored.events if not e.removed]
    next_id = max([stored.header.next_id, *(i + 1 for i in by_id)])
    for n in sorted(added, key=lambda n: (n.frame, n.midi)):
        begin = onset.get(n.frame, n.frame * FRAME_MS / 1000)
        length = n.len_ms or nominal_ms(n.figure if n.figure in FIGURES else 8, quarter_ms)
        velocity = loud.get(n.frame) or every
        stored.events.append(
            NoteEvent(
                id=next_id,
                midi_note=n.midi,
                start=begin,
                end=begin + length / 1000,
                velocity=int(np.median(velocity)) if velocity else 64,
                hand="right" if n.staff == 1 else "left",
            )
        )
        gone[next_id] = (True, False)
        next_id += 1
    stored.events.sort(key=lambda event: (event.start, event.midi_note))
    return gone


def record_run(part_id: str, gone: dict[int, tuple[bool, bool]], plain: str, after: str) -> None:
    """The steps start again after a whole AI run (it wrote the hands and the sheet again), with one step when the
    run left out or added notes (implementation 04, Phase 3): its undo puts those notes back as they were, and the
    sheet back to ``plain`` (the AI's sheet laid on the notes without its changes); redo makes them again.
    """
    forget(part_id)
    if gone:
        _record(_Step(RUN_LABEL, {}, _sheet_change(plain, after), gone), part_id)


@dataclass(frozen=True)
class Transposed:
    label: str
    #: Notes moved, and notes that would leave the 88 keys (taken off the page).
    moved: int
    outside: int
    #: The sheet as it is (or would be, for a preview) after the move.
    text: str


def transpose_notes(part_id: str, semitones: int, *, preview: bool = False) -> Transposed:
    """Transpose notes (Phase 8, the sheet toolbox): every note of the part ``semitones`` higher, in ``notes.pmn``,
    and the stored sheet with it (its armaduras moved, the decisions kept on their notes, the clefs fitted where a
    note reads four ledger lines or more from its staff). No time moves and each note keeps its hand. A note that
    would leave the 88 keys is taken off the page. One step; ``preview`` writes nothing."""
    if not semitones:
        raise reading.Refused("Choose two different keys.")
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        drawn = build.current(part_id)
        keys: dict[int, tuple[int, int]] = {}
        gone: dict[int, tuple[bool, bool]] = {}
        moved = 0
        for event in stored.events:
            if event.id is None:
                continue
            target = event.midi_note + semitones
            if LOWEST_MIDI <= target <= HIGHEST_MIDI:
                keys[event.id] = (event.midi_note, target)
                event.midi_note = target
                moved += not event.removed
            elif not event.removed:
                gone[event.id] = (False, True)
                event.removed = True
        sheet = f1.read(drawn.text)
        reading.transpose_sheet(sheet, semitones)
        notes = events_file.notes_from_events(stored.events)
        settled = build.reapply(sheet, starting(part_id, notes))
        build.fit_clefs(settled, reading.far_notes(settled))
        after = f1.write(settled, mode="frames")
        steps = abs(semitones)
        label = f"Transpose {steps} semitone{'' if steps == 1 else 's'} {'up' if semitones > 0 else 'down'}"
        if preview:
            return Transposed(label, moved, len(gone), after)
        saved = _write_hands(part_id, stored, before=stored.header, hands=False, notes=True)
        kept = store.load(part_id)
        record = (
            kept.record
            if kept is not None
            else store.Record(source="algorithm", quarter_ms=drawn.quarter_ms)
        )
        record.edited = True
        record.hands_revision = saved.header.hands_revision
        store.save(part_id, after, record)
        build.forget(part_id)
        _record(_Step(label, {}, _sheet_change(drawn.text, after), gone, keys), part_id)
        return Transposed(label, moved, len(gone), after)


def starting(part_id: str, notes: Any) -> Any:
    """The starting hands of the part (the saved hands, the hand split for the rest) for ``notes`` not yet saved:
    the same ids, so the hands of the notes as they are now are laid on them."""
    now = pipeline.starting_hands(part_id)
    by_id = {int(i): h for i, h in zip(now.id, now.hand)}
    notes.hand = np.array(
        [by_id.get(int(i), h) for i, h in zip(notes.id, notes.hand)], dtype=np.int8
    )
    return notes.live()


def add_note(part_id: str, frame: int, midi: int, hand: str, length_ms: float | None) -> str:
    """A note added on the keyboard panel (Phase 8): into ``notes.pmn`` at the onset of the drawn column ``frame``
    (or at the frame itself when no column is there), in ``hand``, ``length_ms`` long (``None``: a negra of the
    reference figure). One step; undo takes it off again."""
    if hand not in HANDS:
        raise ValueError(f"No hand {hand!r}")
    if not LOWEST_MIDI <= midi <= HIGHEST_MIDI:
        raise reading.Refused("That key is not on the piano.")
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise FileNotFoundError("This part has no notes.")
        drawn = build.current(part_id)
        at = _notes_at(stored.events)
        by_id = {event.id: event for event in stored.events if event.id is not None}
        if at.get((frame, midi)):
            raise reading.Refused("That key is already struck there.")
        column = [by_id[i].start for (f, _), ids in at.items() if f == frame for i in ids]
        begin = min(column) if column else frame * FRAME_MS / 1000
        quarter = drawn.quarter_ms or 500.0
        length = (length_ms if length_ms and length_ms > 0 else quarter) / 1000
        inside = [e.velocity for e in stored.events if not e.removed and abs(e.start - begin) < 4.0]
        next_id = max([stored.header.next_id, *(i + 1 for i in by_id)])
        stored.events.append(
            NoteEvent(
                id=next_id,
                midi_note=midi,
                start=begin,
                end=begin + length,
                velocity=int(np.median(inside)) if inside else 64,
                hand=hand,
            )
        )
        stored.events.sort(key=lambda event: (event.start, event.midi_note))
        saved = _write_hands(part_id, stored, before=stored.header, hands=True, notes=True)
        sheet_change = None
        kept = store.load(part_id)
        if kept is not None and kept.record.decided:
            after = f1.write(
                build.reapply(f1.read(drawn.text), pipeline.starting_hands(part_id)), mode="frames"
            )
            kept.record.hands_revision = saved.header.hands_revision
            store.save(part_id, after, kept.record)
            build.mark_settled(part_id, after)
            sheet_change = _sheet_change(drawn.text, after)
        build.forget(part_id)
        label = "Add a note"
        _record(_Step(label, {}, sheet_change, {next_id: (True, False)}), part_id)
        return label


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
        if step.versions is not None:
            # A paste: the snapshot of the other side put back; the state left is kept as the next one.
            undo_to, redo_to = step.versions
            kept = part_history.restore(part_id, undo_to if back else redo_to)
            step.versions = [undo_to, kept] if back else [kept, redo_to]
            build.forget(part_id)
            (log.undone if back else log.done).append(step)
            _save(part_id, log)
            return step.label
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
        put_back = False
        for note_id, (key_before, key_after) in step.keys.items():
            event = by_id.get(note_id)
            if event is None or event.midi_note != (key_after if back else key_before):
                continue
            event.midi_note = key_before if back else key_after
            put_back = True
        for note_id, (removed_before, removed_after) in step.removed.items():
            event = by_id.get(note_id)
            now_removed = removed_after if back else removed_before
            if event is None or bool(event.removed) != now_removed:
                continue
            event.removed = removed_before if back else removed_after
            put_back = True
        revision = header.hands_revision
        if changed or put_back:
            revision = _write_hands(
                part_id, stored, before=header, hands=changed, notes=put_back
            ).header.hands_revision

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


@dataclass(frozen=True)
class Pasted:
    label: str
    #: Where the passage went and how long it is, in ms of the part.
    at_ms: float
    length_ms: float
    #: The notes it put in, the notes after it that moved, the notes of a stretch pasted over that went.
    notes_in: int = 0
    notes_moved: int = 0
    notes_removed: int = 0


def paste_passage(
    part_id: str,
    source: str,
    from_ms: float,
    to_ms: float,
    *,
    at_ms: float,
    replace_to_ms: float | None = None,
) -> Pasted:
    """Paste ``[from_ms, to_ms)`` of the part ``source`` into this part at ``at_ms`` (or over ``[at_ms,
    replace_to_ms)``): one step, whose undo puts the part back as it was. Raises ``paste.PasteError``.
    """
    passage = paste.read_passage(source, from_ms, to_ms)
    done = paste.paste(part_id, passage, at_ms=at_ms, replace_to_ms=replace_to_ms)
    build.forget(part_id)
    seconds = done.length_ms / 1000
    length = f"{seconds:.1f} s" if seconds < 10 else f"{round(seconds)} s"
    label = f"Paste {length} over a stretch" if replace_to_ms is not None else f"Paste {length}"
    record_version(part_id, label, done.before_version)
    return Pasted(
        label, done.at_ms, done.length_ms, done.notes_in, done.notes_moved, done.notes_removed
    )


def record_version(part_id: str, label: str, before_version: int) -> None:
    """One step for a change that kept the part as it was as a snapshot of its history (a paste, a promotion of
    Record in Sheet): its undo puts that snapshot back."""
    with pipeline.piece_lock(part_id):
        _record(_Step(label, versions=[before_version, 0]), part_id)


def undo(part_id: str) -> str | None:
    """Take the last step back; its label, or ``None`` when there is none."""
    return _walk(part_id, "undo")


def redo(part_id: str) -> str | None:
    """Put the last step taken back again; its label, or ``None``."""
    return _walk(part_id, "redo")
