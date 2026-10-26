"""``sheet.f1``: the new piano sheet of a part, as it was last written (implementation 03, Phase 5).

The file is the F1 frames text of the sheet (``aitu_backend.sheet``, plan section 3.1), with one comment line on top
that says how it was written::

    # aitu-sheet {"source": "llm", "handsRevision": 4, "windows": [[177, 512, "llm"], ...], ...}
    F1 frames frameMs=40 quarterMs=480
    key=2b clefs: R=treble L=bass
    ...

The F1 reader skips ``#`` lines, so the file is also a plain F1 text. The hands are written in ``notes.pmn`` too (the
numeric truth, plan section 3.7): the file is only the reading of the notes, rule 1 of the time model.

The record (:class:`Record`):

* ``source``: ``llm`` (every window by Sonnet), ``mixed`` (some windows kept the algorithm), ``algorithm`` (none);
* ``handsRevision``: the ``handsRevision`` of ``notes.pmn`` the sheet was written for. Another value means the
  notes or the hands changed since: the sheet is then laid again on the current notes (:mod:`.build`);
* ``windows``: the segments of the piece-by-piece view, ``[first frame, end frame, "llm" | "algorithm"]``;
* ``quarterMs`` and ``reference`` (who chose the reference figure), ``model``, ``prompt``, ``usd``, ``requests``,
  ``written`` (UTC), and ``note`` when the requests stopped (no credits, no network);
* ``runs``: how many AI runs wrote this sheet. A sheet whose ``source`` is ``llm`` or ``mixed`` was **enhanced with
  AI**, and stays marked so through every later change of the notes or the hands (the user's rule of 2026-10-25:
  running it again is at the user's own risk of the same result). Only a new transcription (new notes) forgets it.
* ``edited``: the user changed the reading (Phase 7: a figure, a finger, a beam, a clef, ...). An ``algorithm``
  sheet is then kept and laid again on new notes, as the AI's is, instead of being computed again.
* ``stretches``: the stretches the AI wrote again with the user's words (Phase 7), ``[first frame, end frame,
  words, usd, written]``, oldest first. Their cost is in ``usd`` and ``requests`` too.
* ``key``: the armadura the algorithm writes this sheet with (fifths), when something other than the notes chose it:
  the song's, on the sheets of a passage of it (Record in Sheet, Phase 8B, with ``reference: song``).
* ``legacy``: what the migration of Phase 9 (``scripts/migrate_sheets.py``) carried from the old ``sheet.json``, by
  kind (``{"lyrics": 2, "figures": 6}``); a sheet that has it is not migrated again.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aitu_backend.storage import bundle, locate, paths

__all__ = [
    "MARK",
    "Record",
    "Stored",
    "ask_sonnet",
    "asked",
    "clear",
    "enhanced",
    "load",
    "save",
    "taken",
]

#: The first word of the comment line that holds the record.
MARK = "# aitu-sheet "


@dataclass
class Record:
    source: str = "algorithm"
    hands_revision: int | None = None
    windows: list[list[Any]] = field(default_factory=list)
    quarter_ms: float | None = None
    reference: str | None = None
    model: str | None = None
    prompt: str | None = None
    usd: float = 0.0
    requests: int = 0
    written: str | None = None
    note: str | None = None
    runs: int = 0
    edited: bool = False
    stretches: list[list[Any]] = field(default_factory=list)
    key: int | None = None
    legacy: dict[str, int] | None = None

    @property
    def enhanced(self) -> bool:
        """The AI wrote this sheet, or part of it."""
        return self.source in ("llm", "mixed")

    @property
    def decided(self) -> bool:
        """The stored reading holds decisions (the AI's or the user's): laid again on new notes, never computed
        again. A plain ``algorithm`` sheet (an AI run that wrote no window) is only the rule's result.
        """
        return self.enhanced or self.edited

    def to_json(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "handsRevision": self.hands_revision,
            "windows": self.windows,
            "quarterMs": self.quarter_ms,
            "reference": self.reference,
            "model": self.model,
            "prompt": self.prompt,
            "usd": round(self.usd, 4),
            "requests": self.requests,
            "written": self.written,
            "note": self.note,
            "runs": self.runs,
            "edited": self.edited,
            "stretches": self.stretches,
            **({"key": self.key} if self.key is not None else {}),
            **({"legacy": self.legacy} if self.legacy is not None else {}),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Record":
        return cls(
            source=str(payload.get("source") or "algorithm"),
            hands_revision=payload.get("handsRevision"),
            windows=list(payload.get("windows") or []),
            quarter_ms=payload.get("quarterMs"),
            reference=payload.get("reference"),
            model=payload.get("model"),
            prompt=payload.get("prompt"),
            usd=float(payload.get("usd") or 0.0),
            requests=int(payload.get("requests") or 0),
            written=payload.get("written"),
            note=payload.get("note"),
            # A record written before the count existed: one run if the AI wrote it.
            runs=int(
                payload.get("runs") or (1 if payload.get("source") in ("llm", "mixed") else 0)
            ),
            edited=bool(payload.get("edited")),
            stretches=list(payload.get("stretches") or []),
            key=payload.get("key"),
            legacy=payload.get("legacy"),
        )


@dataclass
class Stored:
    text: str  # the F1 frames text, without the record line
    record: Record
    stamp: int  # the file's modification time (ns): the cache key of what is drawn from it


def load(part_id: str) -> Stored | None:
    """The stored sheet of a part, or ``None`` (never written, or unreadable: the algorithm draws it then)."""
    try:
        path = paths.part_frames_path(part_id)
    except locate.NotFound:
        return None
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        stamp = path.stat().st_mtime_ns
    except OSError:
        return None
    record = Record()
    lines = raw.splitlines(keepends=True)
    if lines and lines[0].startswith(MARK):
        try:
            record = Record.from_json(json.loads(lines[0][len(MARK) :]))
        except (ValueError, TypeError):
            pass
        lines = lines[1:]
    return Stored(text="".join(lines), record=record, stamp=stamp)


def enhanced(part_id: str) -> bool:
    """Whether the AI wrote the stored sheet of a part (or part of it), from the record line alone: the list of
    projects asks it for every part."""
    try:
        path = paths.part_frames_path(part_id)
    except locate.NotFound:
        return False
    try:
        with path.open(encoding="utf-8") as handle:
            first = handle.readline()
    except OSError:
        return False
    if not first.startswith(MARK):
        return False
    try:
        return Record.from_json(json.loads(first[len(MARK) :])).enhanced
    except (ValueError, TypeError):
        return False


def save(part_id: str, text: str, record: Record) -> None:
    path = paths.part_frames_path(part_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = MARK + json.dumps(record.to_json(), separators=(",", ":")) + "\n" + text
    tmp = path.with_suffix(".f1.tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)
    bundle.step_changed(part_id)


def ask_sonnet(part_id: str) -> None:
    """A whole new set of notes (a transcription, a video read): the Sheet step starts Sonnet by itself. Parts that
    existed before Phase 5 never carry the mark, so they keep their sheet until the user asks (the user's answer).
    """
    path = paths.part_frames_pending_path(part_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"asked": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n"
    )


def asked(part_id: str) -> bool:
    try:
        return paths.part_frames_pending_path(part_id).is_file()
    except locate.NotFound:
        return False


def taken(part_id: str) -> None:
    """Sonnet started on the part: the mark is used."""
    try:
        paths.part_frames_pending_path(part_id).unlink(missing_ok=True)
    except locate.NotFound:
        pass


def clear(part_id: str) -> None:
    """Forget the sheet (a new transcription: its columns would point at other notes)."""
    try:
        path = paths.part_frames_path(part_id)
    except locate.NotFound:
        return
    if path.is_file():
        path.unlink()
        bundle.step_changed(part_id)
    # The steps of undo and redo name notes and lines that are gone (``edits``).
    paths.part_frames_edits_path(part_id).unlink(missing_ok=True)
