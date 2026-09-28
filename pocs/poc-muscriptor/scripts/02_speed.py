"""Task 1.3.2: speed and GPU memory of every size, dtype and batch option.

Each configuration transcribes the same excerpt of Superestrella (120 s = 24
chunks by default), after one short warm-up run on the same loaded model, and
records:

* ``audio_per_wall``: seconds of audio per second of processing (the prompt's
  hope is 20);
* ``first_chunk_seconds``: how long the live view waits for its first chunk;
* ``peak_gpu_gb``: ``torch.cuda.max_memory_allocated`` during the run;
* the notes, so that ``13_speed_quality.py`` can say what each faster option
  costs in notes, against the reference (large, float32, batch 1, prelude forcing).

``--compile`` wraps the transformer in ``torch.compile`` and adds that as one
more option.

    cd ../muscriptor
    uv run python ../aimpromptu/pocs/poc-muscriptor/scripts/02_speed.py --sizes large
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import OUT, load_model, load_wav, read_json, run_stream, write_json  # noqa: E402

#: (batch_size, prelude_forcing). Batch 1 with forcing is MuScriptor's default.
BATCHES = [(1, True), (1, False), (4, False), (8, False), (24, False)]


def tag(size: str, dtype: str, batch: int, prelude: bool, compiled: bool) -> str:
    return f"{size}-{dtype}-b{batch}{'-prelude' if prelude else ''}{'-compile' if compiled else ''}"


def main() -> None:
    import torch  # noqa: PLC0415

    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="small,medium,large")
    ap.add_argument("--dtypes", default="float32,float16,bfloat16")
    ap.add_argument("--batches", default=",".join(f"{b}{'p' if p else ''}" for b, p in BATCHES))
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-run configurations already saved")
    args = ap.parse_args()

    batches = [(int(b.rstrip("p")), b.endswith("p")) for b in args.batches.split(",")]
    wav = load_wav(seconds=args.seconds)
    warm = load_wav(seconds=10.0)
    out_dir = OUT / "speed"
    index_path = out_dir / "index.json"
    index = read_json(index_path) if index_path.exists() else {}

    for size in args.sizes.split(","):
        for dtype in args.dtypes.split(","):
            todo = [
                (b, p)
                for b, p in batches
                if args.force or tag(size, dtype, b, p, args.compile) not in index
            ]
            if not todo:
                continue
            model, load_s = load_model(size, device="cuda", dtype=dtype)
            weights_gb = torch.cuda.memory_allocated() / 1e9
            if args.compile:
                t0 = time.perf_counter()
                model._model.transformer = torch.compile(model._model.transformer, dynamic=True)
                print(f"compile wrap {time.perf_counter() - t0:.1f}s", flush=True)
            for batch, prelude in todo:
                name = tag(size, dtype, batch, prelude, args.compile)
                try:
                    t0 = time.perf_counter()
                    run_stream(
                        model,
                        warm,
                        instruments=["acoustic_piano"],
                        batch_size=batch,
                        prelude_forcing=prelude,
                    )
                    warm_s = time.perf_counter() - t0
                    r = run_stream(
                        model,
                        wav,
                        instruments=["acoustic_piano"],
                        batch_size=batch,
                        prelude_forcing=prelude,
                    )
                except Exception as exc:  # a failing option is a result too
                    traceback.print_exc()
                    index[name] = {"error": f"{type(exc).__name__}: {exc}"[:400]}
                    write_json(index_path, index)
                    continue
                first_chunk = next((p["t"] for p in r["progress"] if p["completed"] >= 1), None)
                row = {
                    "size": size,
                    "dtype": dtype,
                    "batch": batch,
                    "prelude": prelude,
                    "compile": args.compile,
                    "load_seconds": round(load_s, 2),
                    "weights_gb": round(weights_gb, 2),
                    "warmup_seconds": round(warm_s, 2),
                    "audio_seconds": r["audio_seconds"],
                    "wall_seconds": r["wall_seconds"],
                    "audio_per_wall": r["audio_per_wall"],
                    "first_chunk_seconds": first_chunk,
                    "first_note_seconds": r["first_note_seconds"],
                    "peak_gpu_gb": r["peak_gpu_gb"],
                    "note_count": r["note_count"],
                }
                print(name, row, flush=True)
                index[name] = row
                write_json(out_dir / "notes" / f"{name}.json", r["notes"])
                write_json(index_path, index)
            del model
            gc.collect()
            torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
