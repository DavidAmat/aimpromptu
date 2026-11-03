"""The history of the AI runs of a part (implementation 04-5, the user, 2026-10-31).

Every level run writes a log in the part's folder, ``ai-runs/<run id>.json``, after its plan and after each batch, so
that a run that stops (Stop, a reload) still explains itself. The log holds the request (level, hands, patterns,
Strict refs, words, model), the system prompt once, and each conversation with the AI (``levels.Talk``: the prompts,
the replies, the check's refusals, the target of a batch, its explanation, its rules and its declared lines), the
rules of the run, its state and its cost. The page lists the runs, the latest first (:func:`listing`), and opens one
(:func:`load`). Level runs stored before this log have only their entry in the record's ``levels``: the listing shows
them from it.

A run whose backend process stopped (a crash, a restart, a reload after a ``.py`` edit) never wrote its end: its log
stays ``running``. :func:`close_unfinished`, called once when the backend starts (implementation 04-6), marks those
logs ``stopped``, with a note, and marks "not written" the batches whose notes never reached the sheet.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aitu_backend.storage import locate, paths

from . import store

__all__ = ["close_unfinished", "create", "listing", "load", "save", "update"]

log = logging.getLogger(__name__)

#: The note of a run the backend did not finish (implementation 04-6).
STOPPED_NOTE = "The backend stopped during the run."

_lock = threading.Lock()
_ID = re.compile(r"^[0-9a-f]{12}$")


def _dir(part_id: str) -> Path:
    return paths.part_frames_path(part_id).parent / "ai-runs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create(part_id: str, request: dict[str, Any], system: str) -> dict[str, Any]:
    """A new log, ``running``, written at once."""
    run = {
        "id": uuid.uuid4().hex[:12],
        "kind": "level",
        "created": _now(),
        "state": "running",
        "request": request,
        "system": system,
        "plan": None,
        "batches": [],
        "rules": [],
        "usd": 0.0,
        "requests": 0,
    }
    save(part_id, run)
    return run


def save(part_id: str, run: dict[str, Any]) -> None:
    folder = _dir(part_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{run['id']}.json"
    tmp = path.with_suffix(".json.tmp")
    with _lock:
        run["updated"] = _now()
        tmp.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def update(part_id: str, run: dict[str, Any], talk: Any) -> None:
    """Put a conversation (``levels.Talk``) into the log, the plan's (``k`` -1) or a batch's (in place of an earlier
    one of the same batch), and write the log."""
    data = talk.to_json()
    if talk.k < 0:
        run["plan"] = data
    else:
        run["batches"] = [b for b in run["batches"] if b["k"] != talk.k] + [data]
        run["batches"].sort(key=lambda b: b["k"])
    save(part_id, run)


def load(part_id: str, run_id: str) -> dict[str, Any] | None:
    if not _ID.match(run_id):
        return None
    try:
        path = _dir(part_id) / f"{run_id}.json"
    except locate.NotFound:
        return None
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _short(run: dict[str, Any]) -> dict[str, Any]:
    req = run.get("request", {})
    return {
        "id": run["id"],
        "log": True,
        "created": run.get("created"),
        "state": run.get("state"),
        "level": req.get("level"),
        "hand": req.get("hand"),
        "patterns": req.get("patterns", []),
        "strict": req.get("strict", []),
        "words": req.get("words", ""),
        "model": req.get("model"),
        "batches": [
            {"k": b["k"], "start": b["start"], "end": b["end"], "status": b["status"]} for b in run.get("batches", [])
        ],
        "total": len(req.get("windows", [])),
        "usd": run.get("usd", 0.0),
    }


def listing(part_id: str) -> list[dict[str, Any]]:
    """The runs of the part, the latest first: the logs, and the level runs of the record that have none."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        folder = _dir(part_id)
    except locate.NotFound:
        return []
    if folder.is_dir():
        for path in folder.glob("*.json"):
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            out.append(_short(run))
            seen.add(run["id"])
    stored = store.load(part_id)
    for k, entry in enumerate(stored.record.levels if stored is not None else []):
        if entry.get("run") in seen:
            continue
        out.append(
            {
                "id": f"record-{k}",
                "log": False,
                "created": entry.get("written"),
                "state": "done",
                "level": entry.get("level"),
                "hand": entry.get("hand"),
                "patterns": entry.get("patterns", []),
                "strict": entry.get("strict", []),
                "words": entry.get("words", ""),
                "model": None,
                "batches": [
                    {"k": i, "start": b[0], "end": b[1], "status": b[2]} for i, b in enumerate(entry.get("batches", []))
                ],
                "total": len(entry.get("batches", [])),
                "usd": entry.get("usd", 0.0),
                "plan": entry.get("plan", []),
                "declared": entry.get("declared", []),
            }
        )
    out.sort(key=lambda r: r.get("created") or "", reverse=True)
    return out


def _saved_batches(part_id: str, run_id: str) -> set[tuple[int, int]]:
    """The batches of a run whose notes are on the sheet: the record's ``levels`` entries of that run hold them (a
    level run saves its notes and its entry together, at its end or at the wait after batch 1)."""
    stored = store.load(part_id)
    out: set[tuple[int, int]] = set()
    for entry in stored.record.levels if stored is not None else []:
        if entry.get("run") == run_id:
            out.update((int(b[0]), int(b[1])) for b in entry.get("batches", []) if len(b) > 2 and b[2] == "ok")
    return out


def _logs() -> list[Path]:
    roots = (paths.users_dir(), paths.public_dir(), paths.requests_dir())
    return [path for root in roots if root.is_dir() for path in root.glob("**/parts/*/ai-runs/*.json")]


def close_unfinished() -> int:
    """At the start of the backend, when no run can be going: every log still ``running`` becomes ``stopped`` with
    :data:`STOPPED_NOTE`, and each of its batches written (``ok``) or being written (``open``) whose notes are not on
    the sheet becomes ``error`` (the page says "Not written"; **Write this batch again** still works on it). Returns
    how many runs it closed. A log it cannot read or write is left as it is: the start never fails for a log."""
    closed = 0
    for path in _logs():
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(run, dict) or run.get("state") != "running":
                continue
            part_id = path.parent.parent.name
            saved = _saved_batches(part_id, run["id"])
            for batch in run.get("batches", []):
                if batch.get("status") in ("ok", "open") and (batch.get("start"), batch.get("end")) not in saved:
                    batch["status"] = "error"
            run["state"] = "stopped"
            run["note"] = STOPPED_NOTE
            save(part_id, run)
            closed += 1
        except Exception:  # noqa: BLE001 - one bad log must not stop the backend from starting
            log.exception("Could not close the unfinished AI run %s", path)
    if closed:
        log.warning("%d AI run(s) were left running when the backend stopped: marked stopped.", closed)
    return closed
