"""Sizes and build times of the payloads the piano sheet and the piano roll ask for.

Implementation 08, Phase 2, task 2.3.3. Runs every transcribed part of ``.database/`` through
the real FastAPI app (``TestClient``, so the time includes validation and JSON encoding, which is
where most of it went) and writes one JSON file with a row per piece.

Run it once on the code before a change and once after, then compare the two files::

    uv run python scripts/bench_payloads.py --out /tmp/before.json
    uv run python scripts/bench_payloads.py --out /tmp/after.json --compare /tmp/before.json

What is measured per piece:

* ``POST /time/{uuid}/score``, the request the piano sheet sends: the first call (the hand split
  is computed) and the median of three more (the split is cached), the bytes sent, and the bytes
  sent when the client accepts gzip.
* ``GET /matrix/{uuid}/events``, the request the old piano roll sends.
* ``events.json`` on disk, and, when the ``pmn`` module exists, the columns form of section 6.4
  of the plan, raw and gzip.
"""

from __future__ import annotations

import argparse
import gzip
import json
import statistics
import time
from pathlib import Path

from fastapi.testclient import TestClient

from aitu_backend.api import time_score
from aitu_backend.main import app
from aitu_backend.pmn import events_file
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription import pipeline

WARM_RUNS = 3


def _anchor(piece: Path) -> tuple[str, float]:
    rhythm = piece / pipeline.SHEET_FILE
    if rhythm.is_file():
        saved = json.loads(rhythm.read_text(encoding="utf-8"))
        return saved.get("anchorFigure", "negra"), float(saved["anchorMs"])
    return "negra", 500.0


def _timed(call):
    start = time.perf_counter()
    response = call()
    return response, (time.perf_counter() - start) * 1000.0


def _columns(uuid: str) -> dict:
    """The columns form of plan section 6.4: bytes, and the time to read the file and build it."""
    try:
        from aitu_backend.pmn import columns, events_file  # noqa: PLC0415 - absent before Phase 2
    except ImportError:
        return {"columnsBytes": None, "columnsGzipBytes": None, "columnsMs": None}
    start = time.perf_counter()
    stored = events_file.read_piece(uuid)
    assert stored is not None
    body = json.dumps(columns.to_columns(stored.notes), separators=(",", ":")).encode()
    elapsed = (time.perf_counter() - start) * 1000.0
    return {
        "columnsBytes": len(body),
        "columnsGzipBytes": len(gzip.compress(body, 5)),
        "columnsMs": round(elapsed, 2),
    }


def _coo_loop(grid) -> tuple[list[int], list[int], list[int]]:
    """How `PianoMatrix.to_coo_payload` built the payload before Phase 2."""
    import numpy as np  # noqa: PLC0415

    cols, rows = np.nonzero(grid.T)
    rows_list, cols_list = rows.astype(int).tolist(), cols.astype(int).tolist()
    onset = [row if grid[row, col] == 1 else -1 for row, col in zip(rows_list, cols_list)]
    return rows_list, cols_list, onset


def _check_loop(rows: list[int], cols: list[int], onset: list[int], width: int) -> None:
    """How `SparseCooMatrix` checked every cell before Phase 2 (it ran twice per request)."""
    for index, (row, col, value) in enumerate(zip(rows, cols, onset)):
        if not 0 <= row < 88 or not 0 <= col < width or (value != row and value != -1):
            raise ValueError(index)


def _coo_times(uuid: str) -> dict:
    """The COO build and the cell check of both hands, the old Python way and the NumPy way."""
    from aitu_backend.schemas.matrix import SparseCooMatrix  # noqa: PLC0415
    from aitu_backend.transcription.time_pipeline import trim_to_music  # noqa: PLC0415

    hands = trim_to_music(time_score._hands(uuid, 40))
    grids = [hands.right.grid, hands.left.grid]
    out = {"cells": int(sum((grid != 0).sum() for grid in grids))}

    start = time.perf_counter()
    built = [_coo_loop(grid) for grid in grids]
    out["cooLoopMs"] = round((time.perf_counter() - start) * 1000.0, 2)
    start = time.perf_counter()
    for (rows, cols, onset), grid in zip(built, grids):
        _check_loop(rows, cols, onset, grid.shape[1])
    out["checkLoopMs"] = round((time.perf_counter() - start) * 1000.0, 2)
    try:
        from aitu_backend.pmn.coo import coo_from_grid  # noqa: PLC0415
    except ImportError:
        return out
    start = time.perf_counter()
    payloads = [coo_from_grid(grid) for grid in grids]
    out["cooNumpyMs"] = round((time.perf_counter() - start) * 1000.0, 2)
    start = time.perf_counter()
    for payload in payloads:
        SparseCooMatrix._check_arrays(payload)
    out["checkNumpyMs"] = round((time.perf_counter() - start) * 1000.0, 2)
    return out


def measure(client: TestClient, piece: Path) -> dict:
    uuid = piece.name
    figure, anchor_ms = _anchor(piece)
    body = {"anchorFigure": figure, "anchorMs": anchor_ms, "frameMs": 40}
    events = events_file.read_payload(piece / pipeline.NOTES_FILE) or {}

    time_score.forget_split_cache()
    first, cold_ms = _timed(lambda: client.post(f"/time/{uuid}/score", json=body))
    first.raise_for_status()
    plain = {"Accept-Encoding": "identity"}
    zip_header = {"Accept-Encoding": "gzip"}
    warm, warm_gzip = [], []
    for _ in range(WARM_RUNS):
        _, elapsed = _timed(lambda: client.post(f"/time/{uuid}/score", json=body, headers=plain))
        warm.append(elapsed)
        _, elapsed = _timed(
            lambda: client.post(f"/time/{uuid}/score", json=body, headers=zip_header)
        )
        warm_gzip.append(elapsed)
    zipped = client.post(f"/time/{uuid}/score", json=body, headers={"Accept-Encoding": "gzip"})
    # httpx decodes the body; the bytes on the wire are the header's length when it is present.
    zipped_bytes = int(zipped.headers.get("content-length", len(zipped.content)))
    gzip_applied = zipped.headers.get("content-encoding") == "gzip"

    raw_events, events_ms = _timed(lambda: client.get(f"/matrix/{uuid}/events"))
    raw_events.raise_for_status()

    return {
        "uuid": uuid,
        "title": events.get("title"),
        "notes": len(events.get("events", [])),
        "durationSeconds": events.get("durationSeconds"),
        "eventsJsonBytes": (piece / pipeline.NOTES_FILE).stat().st_size,
        "scoreBytes": len(first.content),
        # Before Phase 2 nothing was compressed; the level-9 size is what Starlette's default gives.
        "scoreGzipBytes": zipped_bytes if gzip_applied else len(gzip.compress(first.content, 9)),
        "scoreGzipServed": gzip_applied,
        "scoreColdMs": round(cold_ms, 1),
        "scoreWarmMs": round(statistics.median(warm), 1),
        "scoreWarmGzipMs": round(statistics.median(warm_gzip), 1),
        "rawEventsBytes": len(raw_events.content),
        "rawEventsMs": round(events_ms, 1),
        **_columns(uuid),
        **_coo_times(uuid),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare", type=Path, help="An earlier --out file to compare with.")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N pieces.")
    args = parser.parse_args()

    pieces = sorted(
        paths.part_dir(part) for part in bundle.list_parts() if pipeline.has_events(part)
    )
    if args.limit:
        pieces = pieces[: args.limit]

    rows = []
    with TestClient(app) as client:
        for index, piece in enumerate(pieces, 1):
            row = measure(client, piece)
            rows.append(row)
            print(
                f"[{index:2d}/{len(pieces)}] {row['uuid'][:8]} {row['notes']:5d} notes  "
                f"score {row['scoreBytes'] / 1024:7.1f} KB ({row['scoreGzipBytes'] / 1024:6.1f} gz)  "
                f"cold {row['scoreColdMs']:7.1f} ms  warm {row['scoreWarmMs']:7.1f} ms  "
                f"events {row['rawEventsMs']:7.1f} ms"
            )

    args.out.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")

    if args.compare:
        before = {row["uuid"]: row for row in json.loads(args.compare.read_text())}
        keys = ["scoreBytes", "scoreGzipBytes", "scoreColdMs", "scoreWarmMs", "rawEventsMs"]
        print("\nmedian over pieces, before -> after")
        for key in keys:
            old = statistics.median(before[row["uuid"]][key] for row in rows)
            new = statistics.median(row[key] for row in rows)
            print(f"  {key:16s} {old:10.1f} -> {new:10.1f}")


if __name__ == "__main__":
    main()
