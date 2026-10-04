"""The split painted from saved hands against the inference, on every piece of the library.

Implementation 08, Phase 5. For each transcribed piece: run the old split (the inference, then the
reader's pinned hands), read it back as one hand per note id, save those hands on a copy of the
notes, paint the split from them, and compare the two right hand matrices and the two left hand
matrices cell by cell. Also times both paths. Nothing is written to the data folder.

    python scripts/check_saved_hands.py [--frame-ms 40] [--out result.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np

from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline, saved_hands
from aitu_backend.transcription.time_pipeline import impose_granularity_and_split


def check(audio_uuid: str, frame_ms: float) -> dict | None:
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None or not stored.events:
        return None
    duration = max(stored.duration_seconds, frame_ms / 1000.0)
    filters = pipeline.filters_for(stored.header.engine)
    common: dict[str, Any] = {"frame_ms": frame_ms, "title": stored.title, **filters}

    begin = time.perf_counter()
    old = impose_granularity_and_split(stored.events, duration, **common)
    inferred_s = time.perf_counter() - begin

    hands = saved_hands.hands_of_split(old, stored.events)
    events = [
        event.model_copy(
            update={"hand": hands.get(event.id, event.hand) if event.id is not None else event.hand}
        )
        for event in stored.events
    ]
    begin = time.perf_counter()
    new = saved_hands.split_with_saved_hands(events, duration, **common)
    painted_s = time.perf_counter() - begin

    right = int(np.count_nonzero(old.right.grid != new.right.grid))
    left = int(np.count_nonzero(old.left.grid != new.left.grid))
    return {
        "uuid": audio_uuid,
        "engine": stored.header.engine,
        "notes": len(stored.events),
        "pinned": sum(1 for event in stored.events if event.hand),
        "cellsDifferent": right + left,
        "inferredMs": round(inferred_s * 1000, 1),
        "paintedMs": round(painted_s * 1000, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frame-ms", type=float, default=40.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = []
    for folder in sorted(paths.audio_root().iterdir()):
        if (folder / "matrices" / "events.json").is_file():
            row = check(folder.name, args.frame_ms)
            if row is not None:
                rows.append(row)
                print(
                    f"{row['uuid'][:8]}  {row['notes']:5d} notes  {row['pinned']:4d} pinned  "
                    f"diff {row['cellsDifferent']:3d}  "
                    f"inferred {row['inferredMs']:7.1f} ms  painted {row['paintedMs']:6.1f} ms"
                )
    summary = {
        "frameMs": args.frame_ms,
        "pieces": len(rows),
        "identical": sum(1 for row in rows if row["cellsDifferent"] == 0),
        "inferredMsMedian": statistics.median(row["inferredMs"] for row in rows),
        "paintedMsMedian": statistics.median(row["paintedMs"] for row in rows),
        "inferredMsMax": max(row["inferredMs"] for row in rows),
        "paintedMsMax": max(row["paintedMs"] for row in rows),
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "pieces": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
