"""The stored notes of a part (rule 1), in the shape of ``events.json``, to the sparse form and back.

Since implementation 02, Phase 3, the file on disk is ``notes.pmn`` (:mod:`.notes_file`, the
portable ``.pmn`` version 2). This module still works in the shape of ``events.json``, which every
reader knows, and converts at the file boundary (:func:`read_payload`, :func:`write_payload`); an
``events.json`` of an older layout is still read as it is.

The shape: ``durationSeconds``, ``title`` and one object
per note with ``midiNote``, ``start`` and ``end`` in seconds, ``velocity``, and ``hand`` and
``removed`` when they are set. Plan section 6.3 adds three things:

* ``id`` on every note: the stable identity the piano roll edits address. An old file has none; it
  gets ``0, 1, 2 ...`` in file order when it is read, which gives the same ids on every read because
  nothing is written, and the ids are stored at the next save.
* the header: ``notesRevision``, ``handsRevision``, ``audioRevision``, ``engine`` and
  ``lagCorrectionMs`` (plan section 8), plus ``nextId``, the first id no note has used, so a deleted
  note's id is never given again. An old file reads with the defaults of :class:`PieceHeader`.
* ``hand`` on every note once the hand split is saved, and ``handGuessed`` on a note whose hand
  came from the quick rule for an added note (plan section 8.3). Before Phase 5 ``hand`` was only
  the reader's pin, and it still is on a piece whose hands were never saved as a step.

Nothing here writes on a read. ``schemaVersion`` becomes ``"1.1"`` when a file is saved.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

import numpy as np

from aitu_backend.pmn.notes import (
    DEFAULT_VELOCITY,
    HAND_CODES,
    HAND_NAMES,
    KEY_COUNT,
    LOWEST_MIDI,
    Notes,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from aitu_backend.transcription.engine import NoteEvent

__all__ = [
    "EVENTS_SCHEMA_VERSION",
    "Piece",
    "PieceHeader",
    "assign_ids",
    "events_from_notes",
    "header_from_payload",
    "notes_from_events",
    "piece_from_payload",
    "piece_to_payload",
    "read_header",
    "read_piece",
    "write_piece",
]

#: Written on every save. ``1.0`` files (no ids, no header) are read exactly as before.
EVENTS_SCHEMA_VERSION = "1.1"

#: Seconds in the file keep four decimals (0.1 ms), as they always have.
SECONDS_DECIMALS = 4


@dataclass(frozen=True)
class PieceHeader:
    """The revisions and the facts about how the notes were made (plan sections 6.3 and 8)."""

    #: Goes up when a transcription finishes or a notes edit is saved. An old file has one
    #: transcription, so it reads as 1.
    notes_revision: int = 1
    #: Goes up when anything in the file changes: the notes or a hand (plan section 8.2). The piano
    #: sheet records the value it was saved for in ``rhythm.json``.
    hands_revision: int = 0
    #: The ``notesRevision`` the hands were last saved for as a whole (every live note with a
    #: hand). 0 means the hands of these notes were never saved as a step: the hand split then runs
    #: on each read, as before implementation 08 (D-31, changed in Phase 5).
    hands_notes_revision: int = 0
    #: The ``audioRevision`` of ``metadata.json`` the notes were transcribed from.
    audio_revision: int = 0
    #: Which engine made the notes, for example ``muscriptor-large``. ``None`` when not recorded.
    engine: str | None = None
    #: The per-piece timing fix already subtracted from every onset and release (Phase 1 report 3.3).
    lag_correction_ms: float = 0.0
    #: The first id no note of this piece has used.
    next_id: int = 0

    #: ``events.json`` keys of the fields above.
    KEYS = {
        "notes_revision": "notesRevision",
        "hands_revision": "handsRevision",
        "hands_notes_revision": "handsNotesRevision",
        "audio_revision": "audioRevision",
        "engine": "engine",
        "lag_correction_ms": "lagCorrectionMs",
        "next_id": "nextId",
    }

    def to_json(self) -> dict[str, Any]:
        values = asdict(self)
        return {key: values[name] for name, key in self.KEYS.items()}


@dataclass
class Piece:
    """What ``events.json`` holds, with the notes in the sparse form."""

    notes: Notes
    header: PieceHeader
    duration_ms: float
    title: str | None = None
    #: Notes of the file outside the 88 keys. The sparse form cannot hold them; none exists today.
    outside_keyboard: int = 0


def header_from_payload(payload: dict[str, Any]) -> PieceHeader:
    """The header of a file, with the defaults for anything an old file does not carry.

    ``next_id`` also accounts for the ids the notes are given on read, so reading the header alone
    and reading the whole piece always agree on the next free id.
    """
    defaults = PieceHeader()
    values: dict[str, Any] = {}
    for name, key in PieceHeader.KEYS.items():
        value = payload.get(key)
        values[name] = getattr(defaults, name) if value is None else value
    _, next_id = assign_ids(
        (item.get("id") for item in payload.get("events", [])), int(values["next_id"])
    )
    return PieceHeader(
        notes_revision=int(values["notes_revision"]),
        hands_revision=int(values["hands_revision"]),
        hands_notes_revision=int(values["hands_notes_revision"]),
        audio_revision=int(values["audio_revision"]),
        engine=values["engine"],
        lag_correction_ms=float(values["lag_correction_ms"]),
        next_id=next_id,
    )


def assign_ids(ids: Iterable[int | None], next_id: int) -> tuple[list[int], int]:
    """Keep every id that is set and unique; give the others ``next_id, next_id + 1 ...``.

    Returns the ids and the new ``next_id``. A repeated id (a note copied by a splice, for example)
    keeps its first holder and the copy gets a new one, so two notes never share an identity.
    """
    wanted = list(ids)
    taken = {int(value) for value in wanted if value is not None}
    counter = max([next_id, *(value + 1 for value in taken)])
    seen: set[int] = set()
    out: list[int] = []
    for value in wanted:
        if value is None or int(value) in seen:
            out.append(counter)
            counter += 1
        else:
            out.append(int(value))
        seen.add(out[-1])
    return out, counter


def piece_from_payload(payload: dict[str, Any]) -> Piece:
    """The parsed JSON of ``events.json`` to a :class:`Piece`. Raises ``ValueError`` on a bad file."""
    items = payload.get("events", [])
    header = header_from_payload(payload)
    # The same call `header_from_payload` makes, so the ids and the header's next id agree.
    ids, _ = assign_ids((item.get("id") for item in items), int(payload.get("nextId") or 0))
    try:
        midi = np.fromiter((int(item["midiNote"]) for item in items), np.int64, len(items))
        start = np.fromiter((float(item["start"]) for item in items), np.float64, len(items))
        end = np.fromiter((float(item["end"]) for item in items), np.float64, len(items))
        velocity = np.fromiter(
            (int(item.get("velocity", DEFAULT_VELOCITY)) for item in items), np.int64, len(items)
        )
        hand = np.fromiter((HAND_CODES[item.get("hand")] for item in items), np.int8, len(items))
        removed = np.fromiter(
            (bool(item.get("removed", False)) for item in items), bool, len(items)
        )
        guessed = np.fromiter(
            (bool(item.get("handGuessed", False)) for item in items), bool, len(items)
        )
        duration_ms = float(payload["durationSeconds"]) * 1000.0
    except (KeyError, TypeError) as exc:
        raise ValueError(f"events.json is not readable: {exc!r}") from exc

    on_ms = np.round(start * 1000.0, 6)
    len_ms = np.round(end * 1000.0, 6) - on_ms
    inside = (midi >= LOWEST_MIDI) & (midi < LOWEST_MIDI + KEY_COUNT)
    notes = Notes(
        id=np.asarray(ids, dtype=np.int64)[inside],
        key=(midi - LOWEST_MIDI)[inside],
        on_ms=on_ms[inside],
        len_ms=len_ms[inside],
        hand=hand[inside],
        velocity=velocity[inside],
        removed=removed[inside],
        hand_guessed=guessed[inside],
    )
    return Piece(
        notes=notes,
        header=header,
        duration_ms=duration_ms,
        title=payload.get("title"),
        outside_keyboard=int((~inside).sum()),
    )


def _seconds(values_ms: np.ndarray) -> list[float]:
    return np.round(values_ms / 1000.0, SECONDS_DECIMALS).tolist()


def piece_to_payload(piece: Piece) -> dict[str, Any]:
    """A :class:`Piece` to the JSON of ``events.json``, in the order of its notes."""
    notes = piece.notes
    header = replace(piece.header, next_id=max(piece.header.next_id, notes.next_id))
    rows: list[dict[str, Any]] = []
    for note_id, midi, start, end, velocity, hand, removed, guessed in zip(
        notes.id.tolist(),
        notes.midi.tolist(),
        _seconds(notes.on_ms),
        _seconds(notes.end_ms),
        notes.velocity.tolist(),
        notes.hand.tolist(),
        notes.removed.tolist(),
        notes.hand_guessed.tolist(),
    ):
        rows.append(_row(note_id, midi, start, end, velocity, HAND_NAMES[hand], removed, guessed))
    return _payload(rows, header, piece.duration_ms / 1000.0, piece.title)


def _row(
    note_id: int,
    midi: int,
    start: float,
    end: float,
    velocity: int,
    hand: str | None,
    removed: bool,
    hand_guessed: bool = False,
) -> dict[str, Any]:
    return {
        "id": note_id,
        "midiNote": midi,
        "start": start,
        "end": end,
        "velocity": velocity,
        # Only when set, which keeps the file the size it was for the notes nobody touched.
        **({"hand": hand} if hand else {}),
        **({"handGuessed": True} if hand and hand_guessed else {}),
        **({"removed": True} if removed else {}),
    }


def _payload(
    rows: list[dict[str, Any]], header: PieceHeader, duration_seconds: float, title: str | None
) -> dict[str, Any]:
    return {
        "schemaVersion": EVENTS_SCHEMA_VERSION,
        "durationSeconds": round(float(duration_seconds), 6),
        "title": title,
        **header.to_json(),
        "events": rows,
    }


# ----------------------------------------------------------------------- files


def read_payload(path: Path) -> dict[str, Any] | None:
    """The stored notes at ``path`` in the shape of ``events.json``, or ``None`` when unreadable.

    ``notes.pmn`` is converted (:func:`~aitu_backend.pmn.notes_file.from_pmn`); an ``events.json``
    is returned as it is.
    """
    from aitu_backend.pmn import notes_file  # noqa: PLC0415 - notes_file imports this module

    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and notes_file.is_pmn(payload):
            payload = notes_file.from_pmn(payload)
    except (ValueError, OSError, KeyError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


_load_json = read_payload


def read_header(path: Path) -> PieceHeader:
    """The header of the file at ``path``, or the defaults when there is no readable file."""
    payload = _load_json(path)
    if payload is None:
        return PieceHeader()
    return header_from_payload(payload)


def read_piece(audio_uuid_or_path: str | Path) -> Piece | None:
    """The piece of a part id (or of a ``notes.pmn`` path), or ``None`` when unreadable."""
    path = _path_of(audio_uuid_or_path)
    payload = _load_json(path)
    if payload is None:
        return None
    try:
        return piece_from_payload(payload)
    except ValueError:
        return None


def write_piece(audio_uuid_or_path: str | Path, piece: Piece) -> Path:
    path = _path_of(audio_uuid_or_path)
    return write_payload(path, piece_to_payload(piece))


def write_payload(path: Path, payload: dict[str, Any]) -> Path:
    """Write through a temporary file, so a reader never sees half a piece.

    A ``.pmn`` path is written as ``notes.pmn`` version 2; any other path as ``events.json``.
    """
    from aitu_backend.pmn import notes_file  # noqa: PLC0415 - notes_file imports this module

    path.parent.mkdir(parents=True, exist_ok=True)
    body = notes_file.to_pmn(payload) if path.suffix == ".pmn" else payload
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(body, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)
    return path


def _path_of(audio_uuid_or_path: str | Path) -> Path:
    if isinstance(audio_uuid_or_path, Path):
        return audio_uuid_or_path
    from aitu_backend.transcription.pipeline import events_path  # noqa: PLC0415 - avoids a cycle

    return events_path(audio_uuid_or_path)


# ------------------------------------------------------------------ NoteEvent


def notes_from_events(events: list["NoteEvent"], *, next_id: int = 0) -> Notes:
    """The pipeline's ``NoteEvent`` list to the sparse form. Events without an id get new ones."""
    ids, _ = assign_ids((event.id for event in events), next_id)
    inside = [LOWEST_MIDI <= event.midi_note < LOWEST_MIDI + KEY_COUNT for event in events]
    kept = [event for event, keep in zip(events, inside) if keep]
    return Notes(
        id=[note_id for note_id, keep in zip(ids, inside) if keep],
        key=[event.midi_note - LOWEST_MIDI for event in kept],
        on_ms=np.round([event.start * 1000.0 for event in kept], 6),
        len_ms=np.round([event.end * 1000.0 for event in kept], 6)
        - np.round([event.start * 1000.0 for event in kept], 6),
        hand=[HAND_CODES[event.hand] for event in kept],
        velocity=[event.velocity for event in kept],
        removed=[event.removed for event in kept],
        hand_guessed=[event.hand_guessed for event in kept],
    )


def events_from_notes(notes: Notes) -> list["NoteEvent"]:
    """The sparse form to the pipeline's ``NoteEvent`` list, ids kept."""
    from aitu_backend.transcription.engine import NoteEvent  # noqa: PLC0415 - avoids a cycle

    return [
        NoteEvent(
            id=note_id,
            midi_note=midi,
            start=start,
            end=end,
            velocity=velocity,
            hand=HAND_NAMES[hand],
            hand_guessed=guessed,
            removed=removed,
        )
        for note_id, midi, start, end, velocity, hand, removed, guessed in zip(
            notes.id.tolist(),
            notes.midi.tolist(),
            _seconds(notes.on_ms),
            _seconds(notes.end_ms),
            notes.velocity.tolist(),
            notes.hand.tolist(),
            notes.removed.tolist(),
            notes.hand_guessed.tolist(),
        )
    ]


def payload_from_events(
    events: list["NoteEvent"],
    header: PieceHeader,
    duration_seconds: float,
    title: str | None,
) -> dict[str, Any]:
    """The JSON of ``events.json`` straight from a ``NoteEvent`` list, ids assigned.

    The pipeline's writers still hold ``NoteEvent`` objects, and a note outside the 88 keys must
    survive a save even though the sparse form cannot hold it. Each event's ``id`` is set in place,
    so the caller's objects carry the identity that was stored.
    """
    ids, next_id = assign_ids((event.id for event in events), header.next_id)
    rows = []
    for event, note_id in zip(events, ids):
        event.id = note_id
        rows.append(
            _row(
                note_id,
                event.midi_note,
                round(event.start, SECONDS_DECIMALS),
                round(event.end, SECONDS_DECIMALS),
                event.velocity,
                event.hand,
                event.removed,
                event.hand_guessed,
            )
        )
    return _payload(rows, replace(header, next_id=next_id), duration_seconds, title)
