"""The live stream of a real transcription, through the HTTP routes (implementation 08, Phase 4).

    make up
    cd aitu-backend && uv run python scripts/bench_stream.py            # Superestrella
    uv run python scripts/bench_stream.py --uuid 1a16a836 --cut-at 60

It never touches the piece it measures. It uploads a **copy** of the piece's original audio as a new
temporary piece, measures on the copy, and deletes the copy at the end (``--keep`` keeps it).

1. **The whole piece.** ``POST /matrix/transcribe``, then ``GET /matrix/progress/{job}`` read frame
   by frame: when the first rectangle arrives, how many ``chunk`` messages, the longest pause
   between two of them, the total time, and what the ``done`` frame says (revision, lag
   correction). Then the first ``GET /time/{uuid}/score``, which the job's split warm-up should
   make fast. For Superestrella the notes are compared with the Phase 1 native run.
2. **The same piece with a 5 s cut** from ``--cut-at`` seconds (plan section 13, "the joined audio
   makes a false note at a cut"): the notes that start within 100 ms after the join, against the
   notes the whole piece has at the same place of the original audio.

The answer is printed and written as JSON to ``--out``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

from aitu_backend.audio import store
from aitu_backend.storage import bundle, paths

SUPERESTRELLA = "a585f9eb-36a1-49a0-9f0c-2626f3d292da"
PHASE_1_NOTES = (
    paths.repo_root()
    / "pocs"
    / "poc-muscriptor"
    / "out"
    / "full"
    / "large-float16-b1-prelude"
    / "notes.json"
)
DEFAULT_OUT = (
    paths.repo_root()
    / "context"
    / "implementations"
    / "08-new-algorithm-notes-detection-muscriptor"
    / "measurements"
    / "phase-4-stream.json"
)


def _piece(prefix: str) -> Path:
    """The cache folder of the one part whose id starts with ``prefix``: it holds
    ``normalized.wav``, and its name is the part's id (implementation 02, Phase 3)."""
    matches = [part for part in bundle.list_parts() if part.startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f"{len(matches)} pieces start with {prefix!r}")
    return paths.part_cache_dir(matches[0])


def _frames(response: httpx.Response):
    """``(seconds since the request, event name, payload)`` of each SSE frame."""
    started = time.perf_counter()
    event, data = None, ""
    for line in response.iter_lines():
        if line.startswith("event: "):
            event = line[len("event: ") :]
        elif line.startswith("data: "):
            data = line[len("data: ") :]
        elif line == "" and data:
            yield time.perf_counter() - started, event, json.loads(data)
            event, data = None, ""


def transcribe(client: httpx.Client, uuid: str) -> dict[str, Any]:
    started = time.perf_counter()
    job = client.post("/matrix/transcribe", json={"audioUuid": uuid, "force": True}).json()
    chunks: list[float] = []
    first_note = None
    stages: dict[str, float] = {}
    done: dict[str, Any] = {}
    with client.stream("GET", f"/matrix/progress/{job['jobId']}", timeout=None) as response:
        for seconds, event, payload in _frames(response):
            if event == "chunk":
                chunks.append(seconds)
                if first_note is None and (payload["closed"]["id"] or payload["open"]["id"]):
                    first_note = seconds
            elif event == "done":
                done = payload
                break
            elif event is None:
                stages.setdefault(payload["stage"], seconds)
    total = time.perf_counter() - started
    gaps = [b - a for a, b in zip(chunks, chunks[1:])]
    return {
        "jobId": job["jobId"],
        "firstNoteS": round(first_note or 0.0, 2),
        "chunkMessages": len(chunks),
        "medianGapS": round(statistics.median(gaps), 3) if gaps else None,
        "longestGapS": round(max(gaps), 3) if gaps else None,
        "totalS": round(total, 2),
        "stageStartsS": {name: round(value, 2) for name, value in stages.items()},
        "done": done,
    }


def notes_of(client: httpx.Client, uuid: str) -> list[dict[str, Any]]:
    return client.get(f"/matrix/{uuid}/events").json()["events"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--api", default="http://127.0.0.1:8765")
    parser.add_argument("--uuid", default=SUPERESTRELLA, help="a piece uuid or its first letters")
    parser.add_argument("--cut-at", type=float, default=60.0, help="where the 5 s cut starts, s")
    parser.add_argument("--keep", action="store_true", help="keep the temporary copy")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    source = _piece(args.uuid)
    original = store.get(source.name).original_path
    assert original is not None, "the piece has no stored audio file"
    client = httpx.Client(base_url=args.api, timeout=120)
    engine = client.get("/matrix/engine").json()
    with original.open("rb") as handle:
        copy = client.post(
            "/audio/upload",
            files={"file": (original.name, handle)},
            data={"alias": f"Phase 4 measurement copy of {source.name[:8]}"},
        ).json()
    uuid = copy["uuid"]
    print(f"copy {uuid} of {source.name}  engine {engine}")
    result: dict[str, Any] = {"piece": source.name, "copy": uuid, "engineBefore": engine}
    try:
        whole = transcribe(client, uuid)
        # The job warms the split at 40 ms (the default frame length) after `done`; 20 ms is not
        # warmed. A page that asks at once waits for the warm-up that is still running (Phase 4
        # report); here the page asks 2 s later, as a reader who looks at the notes first would.
        time.sleep(2.0)
        for frame_ms in (40, 20):
            started = time.perf_counter()
            sheet = client.get(f"/time/{uuid}/score?anchorMs=500&frameMs={frame_ms}")
            sheet.raise_for_status()
            whole[f"firstSheetRequestS{frame_ms}ms"] = round(time.perf_counter() - started, 3)
        notes = notes_of(client, uuid)
        whole["notes"] = len(notes)
        result["whole"] = whole
        print("whole:", json.dumps(whole))

        if source.name == SUPERESTRELLA and PHASE_1_NOTES.is_file():
            lag_ms = float(whole["done"].get("lagCorrectionMs") or 0.0)
            ours = {(n["midiNote"], round(n["start"] * 1000 + lag_ms)) for n in notes}
            theirs = {
                (int(n["pitch"]), round(float(n["start"]) * 1000))
                for n in json.loads(PHASE_1_NOTES.read_text())
            }
            result["againstPhase1Native"] = {
                "ours": len(ours),
                "phase1": len(theirs),
                "sameKeyAndOnset": len(ours & theirs),
            }
            print("against Phase 1:", result["againstPhase1Native"])

        # 5 s cut: frames [cut, cut + 500). The join is at `cut` in the piece.
        cut = int(round(args.cut_at * 100))
        client.put(f"/audio/{uuid}/cuts", json={"cuts": [[cut, cut + 500]]}).raise_for_status()
        cut_run = transcribe(client, uuid)
        cut_notes = notes_of(client, uuid)
        join_s = cut / 100

        def near(values: list[dict[str, Any]], at: float) -> list[list[float]]:
            return [
                [n["midiNote"], round(n["start"], 3)]
                for n in values
                if at - 0.3 <= n["start"] < at + 0.3
            ]

        def keyed(values: list[dict[str, Any]], shift: float = 0.0) -> set[tuple[int, int]]:
            return {(n["midiNote"], round((n["start"] + shift) * 1000)) for n in values}

        # In the piece with the cut, the audio after the join is 5 s earlier than in the whole one.
        before = [n for n in notes if n["start"] < join_s - 0.5]
        before_cut = [n for n in cut_notes if n["start"] < join_s - 0.5]
        after = [n for n in notes if n["start"] >= join_s + 5 + 5.5]
        after_cut = [n for n in cut_notes if n["start"] >= join_s + 5.5]
        cut_run["notes"] = len(cut_notes)
        cut_run["join"] = {
            "atS": join_s,
            "cutNotesWithin300ms": near(cut_notes, join_s),
            "wholeNotesWithin300msOfTheCutStart": near(notes, join_s),
            "wholeNotesWithin300msOfTheCutEnd": near(notes, join_s + 5),
        }
        cut_run["sameKeyAndOnset"] = {
            "beforeTheJoin": [len(keyed(before) & keyed(before_cut)), len(before), len(before_cut)],
            # From 5.5 s after the join, once the first chunk after the join is over.
            "afterTheJoin": [
                len(keyed(after, -5.0) & keyed(after_cut)),
                len(after),
                len(after_cut),
            ],
        }
        result["withCut"] = cut_run
        print("with a cut:", json.dumps(cut_run))
    finally:
        if not args.keep:
            client.delete(f"/audio/{uuid}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"written {args.out}")


if __name__ == "__main__":
    main()
