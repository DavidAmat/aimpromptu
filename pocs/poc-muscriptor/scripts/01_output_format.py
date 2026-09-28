"""Task 1.3.1: what MuScriptor outputs, on the first 20 seconds of Superestrella.

Runs the ``large`` model on the CPU and on the GPU, conditioned on
``acoustic_piano``, and saves every event exactly as the generator yields it,
with the wall-clock second it arrived. The two runs are then compared note by
note, because the GPU path uses float16 autocast and the CPU path does not.

    cd ../muscriptor
    uv run python ../aimpromptu/pocs/poc-muscriptor/scripts/01_output_format.py [--seconds 20]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import OUT, load_model, load_wav, run_stream, write_json, write_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--size", default="large")
    ap.add_argument("--devices", default="cuda,cpu")
    args = ap.parse_args()

    wav = load_wav(seconds=args.seconds)
    summary: dict = {"seconds": args.seconds, "size": args.size, "runs": {}}
    for device in args.devices.split(","):
        model, load_s = load_model(args.size, device=device)
        result = run_stream(model, wav, log_events=True, instruments=["acoustic_piano"])
        tag = f"superestrella-{int(args.seconds)}s-{args.size}-{device}"
        write_jsonl(OUT / "format" / f"{tag}.events.jsonl", result.pop("events"))
        write_json(OUT / "format" / f"{tag}.notes.json", result["notes"])
        summary["runs"][device] = {
            "load_seconds": round(load_s, 2),
            **{k: v for k, v in result.items() if k not in ("notes", "progress")},
            "progress": result["progress"],
        }
        print(device, summary["runs"][device], flush=True)
        del model

    if len(summary["runs"]) == 2:
        import json  # noqa: PLC0415

        a, b = (
            json.loads(
                (
                    OUT
                    / "format"
                    / f"superestrella-{int(args.seconds)}s-{args.size}-{d}.notes.json"
                ).read_text()
            )
            for d in args.devices.split(",")
        )
        ka = {(n["pitch"], round(n["start"], 2)) for n in a}
        kb = {(n["pitch"], round(n["start"], 2)) for n in b}
        summary["same_notes"] = len(ka & kb)
        summary["only_first"] = sorted(ka - kb)
        summary["only_second"] = sorted(kb - ka)
    write_json(OUT / "format" / f"summary-{args.size}.json", summary)


if __name__ == "__main__":
    main()
