"""Tasks 1.3.3 and 1.3.5: the whole of Superestrella with ``large`` on the GPU.

Saves, for each configuration asked for:

* ``notes.json``: every note, as ``{pitch, start, end, instrument}`` in seconds;
* ``progress.json``: the wall-clock second at which each chunk finished, which is
  what the live view will see;
* ``beats.json``: MuScriptor's own beat grid (beat_this) and the ``onset_delay`` it
  measures from these notes. The app will not store any of it (rule 3); it is only
  one of the two ways ``11_lag.py`` estimates the lag.

The analysis (counts, agreement with ByteDance, pictures, the lag, the filters) is
in the ``1*`` scripts, which run in the backend venv.

    cd ../muscriptor
    uv run python ../aimpromptu/pocs/poc-muscriptor/scripts/04_full_song.py \
        --config large-float32-b1-prelude
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    SAMPLE_RATE,
    SUPERESTRELLA,
    full_uuid,
    load_model,
    load_wav,
    run_dir,
    run_stream,
    write_json,
)


def parse(config: str) -> tuple[str, str, int, bool, bool]:
    """``large-float32-b1-prelude-free`` -> ("large", "float32", 1, True, False).

    The last value says whether the run is conditioned on ``acoustic_piano``; a
    ``free`` suffix lets the model name any instrument (task 1.3.4).
    """
    parts = config.split("-")
    return (
        parts[0],
        parts[1],
        int(parts[2].lstrip("b")),
        "prelude" in parts[3:],
        "free" not in parts[3:],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", action="append", default=None)
    ap.add_argument("--no-beats", action="store_true")
    ap.add_argument(
        "--uuid", action="append", default=None, help="piece uuid or its first characters"
    )
    args = ap.parse_args()
    configs = args.config or ["large-float32-b1-prelude"]

    uuids = [full_uuid(u) for u in (args.uuid or [SUPERESTRELLA])]
    loaded: dict[tuple[str, str], object] = {}
    for uuid, config in [(u, c) for u in uuids for c in configs]:
        wav = load_wav(uuid)
        size, dtype, batch, prelude, piano = parse(config)
        if (size, dtype) not in loaded:
            loaded.clear()
            loaded[(size, dtype)] = load_model(size, device="cuda", dtype=dtype)[0]
        model = loaded[(size, dtype)]
        r = run_stream(
            model,
            wav,
            instruments=["acoustic_piano"] if piano else None,
            batch_size=batch,
            prelude_forcing=prelude,
        )
        folder = run_dir(config, uuid)
        write_json(folder / "notes.json", r["notes"])
        write_json(folder / "progress.json", r["progress"])
        summary = {k: v for k, v in r.items() if k not in ("notes", "progress", "events")}
        if not args.no_beats:
            t0 = time.perf_counter()
            grid = model.detect_beat_grid_for((wav, SAMPLE_RATE))
            beat_s = time.perf_counter() - t0
            if grid is not None:
                measured = grid.with_onset_delay([n["start"] for n in r["notes"]])
                write_json(
                    folder / "beats.json",
                    {
                        "bpm": grid.bpm,
                        "beats_per_bar": grid.beats_per_bar,
                        "first_downbeat": grid.first_downbeat,
                        "onset_delay": measured.onset_delay,
                        "beat_subdivision": measured.beat_subdivision,
                        "beat_detection_seconds": round(beat_s, 2),
                        "beats": [round(float(b), 4) for b in grid.beats],
                    },
                )
                summary["onset_delay_ms"] = round(1000 * (measured.onset_delay or 0.0), 1)
        write_json(folder / "summary.json", summary)
        print(uuid[:8], config, summary, flush=True)


if __name__ == "__main__":
    main()
