"""Task 1.3.4: does conditioning on ``acoustic_piano`` lose any piano note?

Transcribes the same excerpt twice with the ``large`` model: once with
``instruments=["acoustic_piano"]`` (what the app will always do, Q-3) and once
with no conditioning, where the model may name any instrument. Then asks two
questions:

1. Which instruments does the free run name, and how many notes each?
2. Is every note of the free run, whatever instrument it was given, also in the
   conditioned run (same pitch, onset within 50 ms)? A note missing there is a
   note the conditioning removed.

    cd ../muscriptor
    uv run python ../aimpromptu/pocs/poc-muscriptor/scripts/03_conditioning.py [--seconds 60]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import OUT, load_model, load_wav, run_stream, write_json  # noqa: E402

TOLERANCE = 0.050


def matched(a: list[dict], b: list[dict]) -> tuple[list[dict], list[dict]]:
    """Notes of ``a`` that have (and do not have) a same-pitch onset in ``b`` within tolerance."""
    by_pitch: dict[int, list[float]] = {}
    for n in b:
        by_pitch.setdefault(n["pitch"], []).append(n["start"])
    hit, miss = [], []
    for n in a:
        near = any(abs(s - n["start"]) <= TOLERANCE for s in by_pitch.get(n["pitch"], []))
        (hit if near else miss).append(n)
    return hit, miss


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--size", default="large")
    args = ap.parse_args()

    wav = load_wav(seconds=args.seconds)
    model, _ = load_model(args.size, device="cuda")
    piano = run_stream(model, wav, instruments=["acoustic_piano"])
    free = run_stream(model, wav)

    _, lost = matched(free["notes"], piano["notes"])
    _, added = matched(piano["notes"], free["notes"])
    summary = {
        "seconds": args.seconds,
        "size": args.size,
        "conditioned_notes": piano["note_count"],
        "conditioned_instruments": dict(Counter(n["instrument"] for n in piano["notes"])),
        "free_notes": free["note_count"],
        "free_instruments": dict(Counter(n["instrument"] for n in free["notes"])),
        "free_notes_missing_when_conditioned": len(lost),
        "missing_by_instrument": dict(Counter(n["instrument"] for n in lost)),
        "missing_examples": lost[:40],
        "conditioned_notes_missing_when_free": len(added),
        "added_examples": added[:40],
        "wall_seconds": {"conditioned": piano["wall_seconds"], "free": free["wall_seconds"]},
    }
    write_json(OUT / "conditioning" / "summary.json", summary)
    write_json(OUT / "conditioning" / "piano.notes.json", piano["notes"])
    write_json(OUT / "conditioning" / "free.notes.json", free["notes"])
    print({k: v for k, v in summary.items() if not k.endswith("examples")})


if __name__ == "__main__":
    main()
