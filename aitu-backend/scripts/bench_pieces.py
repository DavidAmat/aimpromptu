"""Time the piece API of implementation 08, Phase 5, through the running backend.

Works on a temporary copy of each piece (a new uuid in the data folder), deleted at the end, so the
library is never changed. For each piece: the status, the notes as columns (size raw and with gzip),
**Predict hands** (first and second call), saving the prediction, a move, and the hand move of the
piano sheet (`PUT /time/{uuid}/hands`, then the sheet request the page makes after it), once on the
copy as it was (no saved hands: the first move saves them) and once more after.

    python scripts/bench_pieces.py [--api http://127.0.0.1:8765] [--out result.json] UUID [UUID ...]
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import time
import urllib.request
import uuid as uuid_module
from pathlib import Path
from typing import Any

from aitu_backend.storage import paths


def call(api: str, method: str, path: str, body: Any = None) -> tuple[Any, float, int, int]:
    """The JSON answer, the time in ms, the raw size and the size as sent (gzip when the backend
    compresses it)."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        api + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept-Encoding": "gzip"},
    )
    begin = time.perf_counter()
    with urllib.request.urlopen(request) as response:
        sent = response.read()
        elapsed = (time.perf_counter() - begin) * 1000.0
        raw = gzip.decompress(sent) if response.headers.get("Content-Encoding") == "gzip" else sent
    return (json.loads(raw) if raw else None), round(elapsed, 1), len(raw), len(sent)


def copy_piece(source_uuid: str) -> str:
    copy_uuid = str(uuid_module.uuid4())
    source = paths.audio_dir(source_uuid)
    target = paths.audio_dir(copy_uuid)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("history", "*.wav", "*.mp3"))
    metadata = json.loads((target / "metadata.json").read_text())
    metadata["uuid"] = copy_uuid
    metadata["alias"] = f"bench copy of {metadata.get('alias')}"
    (target / "metadata.json").write_text(json.dumps(metadata))
    return copy_uuid


def sheet_move(api: str, piece: str, reading: dict[str, Any], column: int, row: int, hand: str):
    moved, put_ms, _, _ = call(
        api,
        "PUT",
        f"/time/{piece}/hands",
        {"frameMs": reading["frameMs"], "notes": [{"startFrame": column, "row": row, "hand": hand}]},
    )
    _, score_ms, raw, sent = call(api, "POST", f"/time/{piece}/score", reading)
    return {"assigned": moved["assigned"], "putMs": put_ms, "scoreMs": score_ms, "scoreKb": [
        round(raw / 1024), round(sent / 1024)]}


def bench(api: str, source_uuid: str) -> dict[str, Any]:
    piece = copy_piece(source_uuid)
    try:
        rhythm_path = paths.audio_dir(piece) / "matrices" / "rhythm.json"
        saved = json.loads(rhythm_path.read_text()) if rhythm_path.is_file() else {}
        reading = {
            "anchorFigure": saved.get("anchorFigure", "negra"),
            "anchorMs": saved.get("anchorMs", 500.0),
            "frameMs": saved.get("frameMs", 40.0),
        }
        row: dict[str, Any] = {"uuid": source_uuid}

        _, row["statusMs"], _, _ = call(api, "GET", f"/pieces/{piece}/status")
        notes, row["notesMs"], raw, sent = call(api, "GET", f"/pieces/{piece}/notes")
        row["notes"] = len(notes["id"])
        row["notesKb"] = [round(raw / 1024), round(sent / 1024)]

        # The piano sheet as the page opens it (the split of an old piece: the inference runs).
        _, row["sheetFirstMs"], _, _ = call(api, "POST", f"/time/{piece}/score", reading)
        score, _, _, _ = call(api, "POST", f"/time/{piece}/score", reading)
        first = next(note for note in score["notes"] if note["hand"] == "right")
        column, key = first["startFrame"], first["row"]

        row["sheetMoveOldPiece"] = sheet_move(api, piece, reading, column, key, "left")
        row["sheetMoveSaved"] = sheet_move(api, piece, reading, column, key, "right")

        body = {"baseRevision": notes["revision"], "frameMs": reading["frameMs"]}
        predicted, row["predictFirstMs"], _, _ = call(
            api, "POST", f"/pieces/{piece}/hands/predict", {**body, "replace": True}
        )
        _, row["predictAgainMs"], _, _ = call(
            api, "POST", f"/pieces/{piece}/hands/predict", {**body, "replace": True}
        )
        right = [i for i, hand in zip(predicted["id"], predicted["hand"]) if hand == "r"]
        left = [i for i, hand in zip(predicted["id"], predicted["hand"]) if hand == "l"]
        ops = [{"op": "hand", "ids": right, "hand": "r"}, {"op": "hand", "ids": left, "hand": "l"}]
        saved_hands, row["saveHandsMs"], _, _ = call(
            api, "PATCH", f"/pieces/{piece}/notes", {"baseRevision": notes["revision"], "ops": ops}
        )
        note_id, on_ms, len_ms = notes["id"][10], notes["onMs"][10], notes["lenMs"][10]
        move = {"op": "move", "id": note_id, "onMs": on_ms + 10, "lenMs": max(10, len_ms - 10)}
        _, row["moveMs"], _, _ = call(
            api,
            "PATCH",
            f"/pieces/{piece}/notes",
            {"baseRevision": saved_hands["revision"], "ops": [move]},
        )
        _, row["sheetAfterMoveMs"], _, _ = call(api, "POST", f"/time/{piece}/score", reading)
        return row
    finally:
        shutil.rmtree(paths.audio_dir(piece), ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("uuids", nargs="+")
    parser.add_argument("--api", default="http://127.0.0.1:8765")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    rows = [bench(args.api, source) for source in args.uuids]
    print(json.dumps(rows, indent=2))
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
