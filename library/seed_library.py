"""Seed the audio library from `library/library.json`, then transcribe it.

Run it from `aitu-backend/`, which is where the backend's dependencies and its
`data/` tree live::

    cd aitu-backend
    nohup uv run python ../library/seed_library.py > /dev/null 2>&1 &

Two phases, in order, one piece at a time:

1. **Download.** Each URL goes through :func:`aitu_backend.audio.youtube.download`,
   the same function `POST /youtube/download` calls, so a seeded piece is
   indistinguishable from one added through the UI and nothing here opens a file
   under ``data/audio/`` itself — `audio/store.py` says why that matters.
2. **Transcribe.** Each stored piece goes through
   :func:`aitu_backend.transcription.pipeline.run_pipeline` with the defaults
   `TranscribeRequest` declares — ``frameMs`` 40.0, engine ``bytedance``,
   ``reuse_events`` on — which writes ``events.json`` and nothing else.

**It writes no `rhythm.json`.** D-09: the app never chooses the ladder, the user
does. Precomputing an anchor would be this script naming the ladder on the
reader's behalf while looking like the reader did, so every seeded piece opens
with its peaks measurable and no figure named. Everything else a sheet is made
of — matrix, hand split, peaks, ladder candidates — is derived per request and
was never stored in the first place, so there is nothing else to precompute.

Downloads are paced with a long randomized gap because YouTube throttles
anything that looks like a bulk scrape, and they are strictly sequential for the
same reason. Transcription is local CPU with nobody to annoy; its short gap is
only there to keep the machine responsive.

Resumable and safe to re-run. A piece already in the store under the same
``sourceUrl`` is not downloaded twice, and ``reuse_events`` skips a piece that
already has its notes — so retrying the failures at the end of a run means
running this file again.
"""

from __future__ import annotations

import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from aitu_backend.audio import store, youtube
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import DEFAULT_ENGINE

HERE = Path(__file__).resolve().parent
LIBRARY_JSON = HERE / "library.json"
STATE_PATH = HERE / "seed-state.json"
LOG_PATH = HERE / "seed.log"

#: Seconds to wait between two downloads. Long, and jittered rather than fixed:
#: a metronomic gap is itself a bot signature.
DOWNLOAD_GAP = (45, 120)

#: Seconds between two transcriptions. Short — this one talks to no server.
TRANSCRIBE_GAP = 10


def log(message: str) -> None:
    """One timestamped line, flushed immediately so `tail -f` keeps up."""
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")
        handle.flush()


def save_state(state: dict) -> None:
    """Persist after every step, so a crash still leaves a readable record."""
    state["updatedAt"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def existing_by_url() -> dict[str, str]:
    """``sourceUrl -> uuid`` for everything already in the store."""
    return {
        entry.metadata.source_url: entry.uuid
        for entry in store.list_all()
        if entry.metadata.source_url
    }


def pace(low: int, high: int, reason: str) -> None:
    """Sleep a jittered interval, saying out loud how long and why."""
    delay = random.uniform(low, high)
    log(f"    pausing {delay:.0f}s ({reason})")
    time.sleep(delay)


# ----------------------------------------------------------------- phase one


def download_all(pieces: list[dict], state: dict) -> None:
    """Download every piece that has a URL and is not already stored."""
    already = existing_by_url()
    wanted = [p for p in pieces if p.get("url") and not p.get("skip")]

    log(f"phase 1 — downloading {len(wanted)} pieces, one at a time")
    for index, piece in enumerate(wanted, start=1):
        url, alias = piece["url"], piece["alias"]
        entry_state = state["downloads"].setdefault(url, {"alias": alias})

        if url in already:
            log(f"  {index:>2}/{len(wanted)}  {alias} — already stored, skipping")
            entry_state.update(status="skipped", uuid=already[url], detail="already in the store")
            save_state(state)
            continue

        log(f"  {index:>2}/{len(wanted)}  {alias}")
        started = time.time()
        try:
            stored = youtube.download(url, alias)
        except Exception as exc:  # one failure must not stop the rest
            log(f"      FAILED — {type(exc).__name__}: {exc}")
            entry_state.update(status="error", detail=f"{type(exc).__name__}: {exc}")
        else:
            seconds = stored.metadata.duration_seconds or 0.0
            log(f"      ok — {stored.uuid[:8]}  {seconds:.0f}s  in {time.time() - started:.0f}s")
            entry_state.update(
                status="done",
                uuid=stored.uuid,
                durationSeconds=round(seconds, 2),
                detail=None,
            )
        save_state(state)

        if index < len(wanted):
            pace(*DOWNLOAD_GAP, reason="YouTube throttles bulk downloads")


# ----------------------------------------------------------------- phase two


def transcribe_all(state: dict) -> None:
    """Run the model over every piece that landed, following each job."""
    uuids = [
        (entry["uuid"], entry["alias"])
        for entry in state["downloads"].values()
        if entry.get("status") in {"done", "skipped"} and entry.get("uuid")
    ]

    log(f"phase 2 — transcribing {len(uuids)} pieces "
        f"(engine {DEFAULT_ENGINE}, frameMs {DEFAULT_FRAME_MS})")

    for index, (uuid, alias) in enumerate(uuids, start=1):
        entry_state = state["transcriptions"].setdefault(uuid, {"alias": alias})

        if pipeline.load_note_events(uuid) is not None:
            log(f"  {index:>2}/{len(uuids)}  {alias} — events.json already present, skipping")
            entry_state.update(status="skipped", detail="already transcribed")
            save_state(state)
            continue

        log(f"  {index:>2}/{len(uuids)}  {alias}")
        started = time.time()
        last_stage = {"name": ""}

        def follow(event: ProgressEvent) -> None:
            """Log every stage change — this job is followed, not fired off."""
            if event.stage != last_stage["name"]:
                last_stage["name"] = event.stage
                log(f"      stage: {event.stage}")

        try:
            pipeline.run_pipeline(
                uuid,
                frame_ms=DEFAULT_FRAME_MS,
                engine=DEFAULT_ENGINE,
                reuse_events=True,
                reporter=CallbackProgress(follow),
            )
        except Exception as exc:
            log(f"      FAILED — {type(exc).__name__}: {exc}")
            entry_state.update(status="error", detail=f"{type(exc).__name__}: {exc}")
        else:
            events = pipeline.load_note_events(uuid)
            count = len(events.events) if events else 0
            log(f"      ok — {count} notes in {time.time() - started:.0f}s")
            entry_state.update(status="done", noteCount=count, detail=None)
        save_state(state)

        if index < len(uuids):
            time.sleep(TRANSCRIBE_GAP)


def main() -> int:
    pieces = json.loads(LIBRARY_JSON.read_text(encoding="utf-8"))["pieces"]

    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.is_file() else {}
    state.setdefault("startedAt", datetime.now(timezone.utc).isoformat())
    state.setdefault("downloads", {})
    state.setdefault("transcriptions", {})
    state["engine"] = DEFAULT_ENGINE
    state["frameMs"] = DEFAULT_FRAME_MS

    log("=" * 70)
    log(f"seeding from {LIBRARY_JSON.name} — {len(pieces)} lines")
    for piece in pieces:
        if piece.get("skip"):
            log(f"  not downloading '{piece['title']}' — {piece['skip']}")

    download_all(pieces, state)
    transcribe_all(state)

    downloads = state["downloads"].values()
    transcriptions = state["transcriptions"].values()
    failed_downloads = [e for e in downloads if e.get("status") == "error"]
    failed_transcriptions = [e for e in transcriptions if e.get("status") == "error"]

    state["finishedAt"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    log("-" * 70)
    log(f"downloaded     {sum(1 for e in downloads if e.get('status') == 'done')}")
    log(f"transcribed    {sum(1 for e in transcriptions if e.get('status') == 'done')}")
    log(f"failed         {len(failed_downloads)} download(s), "
        f"{len(failed_transcriptions)} transcription(s)")
    for entry in failed_downloads + failed_transcriptions:
        log(f"  - {entry['alias']}: {entry['detail']}")
    log("done. re-run this file to retry the failures; everything that landed is skipped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
