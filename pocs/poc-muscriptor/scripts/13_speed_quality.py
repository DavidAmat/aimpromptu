"""Task 1.3.2, second half: what each faster option costs in notes.

Reads ``out/speed/index.json`` (from ``02_speed.py``) and compares the notes of
every configuration with the reference, ``large-float32-b1-prelude`` (MuScriptor's
own default on CUDA). Agreement is an F1 score, the harmonic mean of the share of
the reference notes found and the share of the configuration's notes that are in
the reference (same pitch, onset within 50 ms). It says how close an option stays
to the reference, not how correct it is: there is no ground truth for this song.

It also counts the notes that end exactly on a 5 s chunk border. Without prelude
forcing a sustained note may be cut there, so that count is the direct price of
batching.

    cd aitu-backend
    uv run python ../pocs/poc-muscriptor/scripts/13_speed_quality.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import OUT, read_json, write_json  # noqa: E402

compare = __import__("10_compare_bytedance")

REFERENCE = "large-float32-b1-prelude"


def main() -> None:
    index = read_json(OUT / "speed" / "index.json")
    ref = read_json(OUT / "speed" / "notes" / f"{REFERENCE}.json")
    rows = []
    for name, row in index.items():
        if "error" in row:
            rows.append({"config": name, "error": row["error"]})
            continue
        notes = read_json(OUT / "speed" / "notes" / f"{name}.json")
        pairs = compare.match(notes, ref)
        recall = len(pairs) / max(1, len(ref))
        precision = len(pairs) / max(1, len(notes))
        f1 = 2 * precision * recall / max(1e-9, precision + recall)
        rows.append(
            {
                "config": name,
                "audio_per_wall": row["audio_per_wall"],
                "first_chunk_seconds": row["first_chunk_seconds"],
                "peak_gpu_gb": row["peak_gpu_gb"],
                "weights_gb": row["weights_gb"],
                "load_seconds": row["load_seconds"],
                "notes": len(notes),
                "f1_vs_reference": round(f1, 3),
                "ends_on_chunk_border": sum(compare.at_border(n["end"]) for n in notes),
            }
        )
    rows.sort(key=lambda r: -r.get("audio_per_wall", 0))
    write_json(OUT / "speed" / "quality.json", rows)
    head = f"{'config':38} {'x real':>7} {'1st chunk':>9} {'GB peak':>7} {'notes':>6} {'F1':>6} {'border':>6}"
    print(head)
    for r in rows:
        if "error" in r:
            print(f"{r['config']:38} ERROR {r['error'][:80]}")
            continue
        print(
            f"{r['config']:38} {r['audio_per_wall']:7.1f} {r['first_chunk_seconds'] or 0:9.2f} "
            f"{r['peak_gpu_gb']:7.2f} {r['notes']:6d} {r['f1_vs_reference']:6.3f} "
            f"{r['ends_on_chunk_border']:6d}"
        )


if __name__ == "__main__":
    main()
