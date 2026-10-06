"""``notes.pmn``, the stored notes of a part: the portable ``.pmn`` file, version 2 (implementation
02, plan P-5 and section 8.3).

Version 1 (:mod:`.portable`) is the export of implementation 08: the live notes as columns. Version
2 is the same file with what ``events.json`` kept beside the notes, so the file in the bundle is the
file in the export and nothing is converted on the way out::

    {"format": "aimpromptu-pmn", "version": 2,
     "lowestMidi": 21, "keys": 88, "frameMs": 10, "timeUnit": "ms",
     "durationMs": 189560, "title": "Superestrella",
     "notesRevision": 3, "handsRevision": 12, "handsNotesRevision": 3, "audioRevision": 0,
     "engine": "muscriptor-large", "lagCorrectionMs": 0.0, "nextId": 1874,
     "id": [0, 1], "key": [39, 43], "onMs": [3070, 3363], "lenMs": [1220, 587],
     "hand": "rl", "velocity": [64, 64],
     "removed": [1], "handGuessed": []}

* Every note is in the columns, **in the order of the part**, the removed ones too (they can be put
  back). ``removed`` and ``handGuessed`` list note ids.
* Times are milliseconds with up to three decimals (a microsecond): ``events.json`` kept four
  decimals of seconds (0.1 ms), and the two pieces written by hand
  (``scripts/make_demo_pieces.py``) six, so every part converts to version 2 and back with every
  number equal. A MuScriptor part has whole milliseconds only.
* ``outside`` holds, as ``events.json`` rows, any note outside the 88 keys. None exists; the key is
  there so such a note would survive a save, as it did before.

The rest of the backend still reads and writes the shape of ``events.json`` (a list of note rows in
seconds): :func:`to_pmn` and :func:`from_pmn` convert at the file boundary, in
:mod:`.events_file`. The reader of :mod:`.portable` reads this file as an export (live notes only).
"""

from __future__ import annotations

from typing import Any

from aitu_backend.pmn.columns import HAND_CHARS, decode_hands
from aitu_backend.pmn.events_file import (
    EVENTS_SCHEMA_VERSION,
    PieceHeader,
    assign_ids,
    header_from_payload,
)
from aitu_backend.pmn.notes import HAND_CODES, HAND_NAMES, KEY_COUNT, LOWEST_MIDI
from aitu_backend.pmn.portable import FORMAT, FRAME_MS

__all__ = ["NOTES_VERSION", "from_pmn", "is_pmn", "to_pmn"]

NOTES_VERSION = 2
MS_DECIMALS = 3
#: Seconds read back with six decimals: the most any stored part has.
READ_SECONDS_DECIMALS = 6
DURATION_MS_DECIMALS = 3


def _ms(value: float) -> float | int:
    rounded = round(float(value), MS_DECIMALS)
    return int(rounded) if rounded.is_integer() else rounded


def is_pmn(body: dict[str, Any]) -> bool:
    return body.get("format") == FORMAT


def to_pmn(payload: dict[str, Any]) -> dict[str, Any]:
    """The JSON of ``events.json`` (any schema version) to the body of ``notes.pmn``.

    Notes without an id get the ids every reader of the old file gave them (:func:`assign_ids` in
    file order), and the header gets the defaults an old file reads with, so nothing changes.
    """
    rows = payload.get("events", [])
    header = header_from_payload(payload)
    ids, _ = assign_ids((row.get("id") for row in rows), int(payload.get("nextId") or 0))
    columns: dict[str, list[Any]] = {key: [] for key in ("id", "key", "onMs", "lenMs", "velocity")}
    hands: list[str] = []
    removed: list[int] = []
    guessed: list[int] = []
    outside: list[dict[str, Any]] = []
    for note_id, row in zip(ids, rows):
        midi = int(row["midiNote"])
        if not LOWEST_MIDI <= midi < LOWEST_MIDI + KEY_COUNT:
            outside.append({**row, "id": note_id})
            continue
        on_ms = round(float(row["start"]) * 1000.0, MS_DECIMALS)
        end_ms = round(float(row["end"]) * 1000.0, MS_DECIMALS)
        columns["id"].append(note_id)
        columns["key"].append(midi - LOWEST_MIDI)
        columns["onMs"].append(_ms(on_ms))
        columns["lenMs"].append(_ms(round(end_ms - on_ms, MS_DECIMALS)))
        columns["velocity"].append(int(row.get("velocity", 64)))
        hand = row.get("hand")
        hands.append(HAND_CHARS[HAND_CODES[hand]])
        if row.get("removed"):
            removed.append(note_id)
        if hand and row.get("handGuessed"):
            guessed.append(note_id)
    duration_ms = round(float(payload["durationSeconds"]) * 1000.0, DURATION_MS_DECIMALS)
    body: dict[str, Any] = {
        "format": FORMAT,
        "version": NOTES_VERSION,
        "lowestMidi": LOWEST_MIDI,
        "keys": KEY_COUNT,
        "frameMs": FRAME_MS,
        "timeUnit": "ms",
        "durationMs": int(duration_ms) if duration_ms.is_integer() else duration_ms,
        "title": payload.get("title"),
        **header.to_json(),
        **columns,
        "hand": "".join(hands),
        "removed": removed,
        "handGuessed": guessed,
    }
    if outside:
        body["outside"] = outside
    return body


def from_pmn(body: dict[str, Any]) -> dict[str, Any]:
    """The body of ``notes.pmn`` to the JSON of ``events.json``, rows in the order of the file.

    Raises ``ValueError`` on a file that is not version 2 of the format.
    """
    if not is_pmn(body):
        raise ValueError(f"Not a {FORMAT} file (format is {body.get('format')!r})")
    if int(body.get("version", 0)) != NOTES_VERSION:
        raise ValueError(f"notes.pmn must be version {NOTES_VERSION}, not {body.get('version')!r}")
    if (
        body.get("lowestMidi", LOWEST_MIDI) != LOWEST_MIDI
        or body.get("keys", KEY_COUNT) != KEY_COUNT
    ):
        raise ValueError(f"Only the {KEY_COUNT} keys from MIDI {LOWEST_MIDI} are supported")
    ids = [int(value) for value in body.get("id", [])]
    count = len(ids)
    hands = decode_hands(body.get("hand") or HAND_CHARS[0] * count)
    removed = set(body.get("removed", []))
    guessed = set(body.get("handGuessed", []))
    rows: list[dict[str, Any]] = []
    for note_id, key, on_ms, len_ms, velocity, hand in zip(
        ids, body["key"], body["onMs"], body["lenMs"], body["velocity"], hands.tolist()
    ):
        name = HAND_NAMES[hand]
        rows.append(
            {
                "id": note_id,
                "midiNote": int(key) + LOWEST_MIDI,
                "start": round(float(on_ms) / 1000.0, READ_SECONDS_DECIMALS),
                "end": round((float(on_ms) + float(len_ms)) / 1000.0, READ_SECONDS_DECIMALS),
                "velocity": int(velocity),
                **({"hand": name} if name else {}),
                **({"handGuessed": True} if name and note_id in guessed else {}),
                **({"removed": True} if note_id in removed else {}),
            }
        )
    rows.extend(body.get("outside", []))
    header_keys = PieceHeader.KEYS.values()
    return {
        "schemaVersion": EVENTS_SCHEMA_VERSION,
        "durationSeconds": round(float(body["durationMs"]) / 1000.0, 6),
        "title": body.get("title"),
        **{key: body[key] for key in header_keys if key in body},
        "events": rows,
    }
