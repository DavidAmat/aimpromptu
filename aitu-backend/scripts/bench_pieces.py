"""Time the piece API of implementation 08, Phase 5, through the running backend.

Works on a temporary copy of each piece (`POST /projects/{id}/duplicate`), deleted at the end, so the
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
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


#: The session cookie, after :func:`sign_in` (implementation 02, Phase 4: every route needs one).
COOKIE: dict[str, str] = {}


def sign_in(api: str) -> None:
    """Sign in as the master user, with the password of `.env` (or `AITU_CHECK_PASSWORD`)."""
    env: dict[str, str] = {}
    dotenv = Path(__file__).resolve().parents[2] / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    username = os.environ.get("AITU_CHECK_USERNAME") or env.get("AITU_MASTER_USERNAME") or "master"
    password = os.environ.get("AITU_CHECK_PASSWORD") or env.get("AITU_MASTER_PASSWORD") or ""
    request = urllib.request.Request(
        api + "/auth/login",
        data=json.dumps({"username": username, "password": password}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        cookie = response.headers.get("Set-Cookie", "").split(";")[0]
    COOKIE["Cookie"] = cookie


def call(api: str, method: str, path: str, body: Any = None) -> tuple[Any, float, int, int]:
    """The JSON answer, the time in ms, the raw size and the size as sent (gzip when the backend
    compresses it)."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        api + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept-Encoding": "gzip", **COOKIE},
    )
    begin = time.perf_counter()
    with urllib.request.urlopen(request) as response:
        sent = response.read()
        elapsed = (time.perf_counter() - begin) * 1000.0
        raw = gzip.decompress(sent) if response.headers.get("Content-Encoding") == "gzip" else sent
    return (json.loads(raw) if raw else None), round(elapsed, 1), len(raw), len(sent)


def copy_piece(api: str, source_uuid: str) -> str:
    """A temporary copy of the project (implementation 02: `POST /projects/{id}/duplicate`)."""
    copy, _, _, _ = call(api, "POST", f"/projects/{source_uuid}/duplicate", {"title": "bench copy"})
    return copy["parts"][0]


def sheet_move(api: str, piece: str, reading: dict[str, Any], column: int, row: int, hand: str):
    moved, put_ms, _, _ = call(
        api,
        "PUT",
        f"/time/{piece}/hands",
        {
            "frameMs": reading["frameMs"],
            "notes": [{"startFrame": column, "row": row, "hand": hand}],
        },
    )
    _, score_ms, raw, sent = call(api, "POST", f"/time/{piece}/score", reading)
    return {
        "assigned": moved["assigned"],
        "putMs": put_ms,
        "scoreMs": score_ms,
        "scoreKb": [round(raw / 1024), round(sent / 1024)],
    }


def bench(api: str, source_uuid: str) -> dict[str, Any]:
    piece = copy_piece(api, source_uuid)
    try:
        try:
            saved, _, _, _ = call(api, "GET", f"/time/{piece}/rhythm")
        except urllib.error.HTTPError:
            saved = {}
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
        call(api, "DELETE", f"/audio/{piece}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("uuids", nargs="+")
    parser.add_argument("--api", default="http://127.0.0.1:8765")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    sign_in(args.api)
    rows = [bench(args.api, source) for source in args.uuids]
    print(json.dumps(rows, indent=2))
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
