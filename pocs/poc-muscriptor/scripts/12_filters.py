"""Task 1.3.6: do ``artifacts.py`` and ``leakage.py`` help or harm MuScriptor notes?

Both filters were tuned for ByteDance. This runs them, unchanged, on the MuScriptor
notes of the whole song, and prints every note they would drop or merge, so each
one can be checked against the audio.

The leakage filter's fourth condition compares velocities ("the phantom is
quieter"). MuScriptor has no velocity: its velocity token has only two values,
onset and offset. Every note therefore gets the default 64 and the condition can
never pass. The script also runs the filter with that condition switched off
(``min_velocity_drop=0``) to show what the other three conditions would do alone.

    cd aitu-backend
    uv run python ../pocs/poc-muscriptor/scripts/12_filters.py [--config large-float32-b1-prelude]
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    SUPERESTRELLA,
    full_uuid,
    result_name,
    run_dir,
    OUT,
    load_bytedance,
    read_json,
    write_json,
)  # noqa: E402

from aitu_backend.transcription.artifacts import drop_artifacts  # noqa: E402
from aitu_backend.transcription.engine import NoteEvent  # noqa: E402
from aitu_backend.transcription.leakage import DEFAULT_LEAKAGE, merge_leaked_onsets  # noqa: E402


def to_events(notes: list[dict]) -> list[NoteEvent]:
    return [
        NoteEvent(
            midi_note=n["pitch"], start=n["start"], end=n["end"], velocity=n.get("velocity", 64)
        )
        for n in notes
        if n["end"] > n["start"]
    ]


def run(notes: list[dict]) -> dict:
    events = to_events(notes)
    art = drop_artifacts(events)
    merged, leak = merge_leaked_onsets(art.kept)
    no_velocity = dataclasses.replace(DEFAULT_LEAKAGE, min_velocity_drop=0)
    _, leak_nv = merge_leaked_onsets(art.kept, no_velocity)
    return {
        "notes": len(events),
        "artifacts_dropped": len(art.dropped),
        "artifacts_octave_phantoms": art.octave_phantoms,
        "artifacts_kept_isolated_short": art.kept_isolated,
        "artifact_examples": [d.describe() for d in art.dropped[:60]],
        "leakage_merged": len(leak.merges),
        "leakage_merged_without_velocity_condition": len(leak_nv.merges),
        "leakage_examples_without_velocity_condition": [m.describe() for m in leak_nv.merges[:60]],
        "notes_after": len(merged),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="large-float32-b1-prelude")
    ap.add_argument("--uuid", default=SUPERESTRELLA, help="piece uuid or its first characters")
    args = ap.parse_args()
    uuid = full_uuid(args.uuid)

    mus = read_json(run_dir(args.config, uuid) / "notes.json")
    summary = {
        "config": args.config,
        "uuid": uuid,
        "muscriptor": run(mus),
        "bytedance": run(load_bytedance(uuid)),
    }
    write_json(OUT / "filters" / f"{result_name(args.config, uuid)}.json", summary)
    for engine in ("muscriptor", "bytedance"):
        print(engine, {k: v for k, v in summary[engine].items() if not k.endswith("examples")})


if __name__ == "__main__":
    main()
