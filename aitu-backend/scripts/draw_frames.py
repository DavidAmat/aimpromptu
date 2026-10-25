"""Draw the new sheet of parts with the engine without compases (``aitu_backend.sheet.engrave.frames``) and time it.

Implementation 03, Phase 3, tasks 3.5 and 3.6. For each part it writes the sheet with the algorithm (the starting
hands, then ``propose_frames``), draws the whole song once cold (the first song of the process) and ``--repeat``
times warm, then draws segments of ``--segment`` seconds one by one (the systems that hold each segment, with the
line breaks of the whole song: what Phase 5 redraws when the LLM returns a segment). It checks every drawing:
each note of the sheet is drawn once (``data-note``), and it counts the beam groups that a line break cuts. Nothing
is written to the data folder; ``--out`` keeps the F1 text, the SVG and the cursor map of each part.

    python scripts/draw_frames.py 1a16a836-62b9-483b-af46-d89d0ab1b2d8 [--out DIR]
    python scripts/draw_frames.py --layer private [--json result.json]

In the container: ``docker exec aimpromptu-backend-1 python scripts/draw_frames.py ...``. On the host, load
``.env`` first, or the script opens an empty ``.database/``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from aitu_backend.sheet.engrave import frames as engine
from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription.pipeline import starting_hands


def _ms(begin: float) -> float:
    return round((time.perf_counter() - begin) * 1000, 1)


def _cut_groups(lay: engine.Layout) -> int:
    line_of = {}
    for k, (i, j, _) in enumerate(lay.lines):
        for col in lay.columns[i:j]:
            line_of[col.frame] = k
    return sum(1 for m in lay.beams.values() if len({line_of[int(c.time)] for c in m}) > 1)


def draw(part_id: str, out: Path | None, repeat: int, segment_s: float) -> dict[str, Any]:
    project_path = paths.part_dir(part_id).parents[1] / "project.json"
    title = json.loads(project_path.read_text(encoding="utf-8")).get("title", "")
    begin = time.perf_counter()
    notes = starting_hands(part_id)
    sheet = propose_frames(notes).sheet
    algo_ms = _ms(begin)
    text = f1.write(sheet, mode="frames")

    cold = engine.render_frames(text)
    warm = [engine.render_frames(text).timings for _ in range(repeat)]
    drawn = Counter(re.findall(r'data-note="([^"]+)"', cold.svg))
    want = Counter(
        f"{n.frame}:{n.midi}" for n in engine.merge_unisons(f1.read(text)).notes if not n.covered
    )
    lay = engine.plan(f1.read(text))

    step = round(segment_s * 1000 / 40)
    last = max(c["frame"] for c in cold.columns)
    seg_ms, seg_systems = [], []
    for a in range(0, last + 1, step):
        r = engine.render_frames(text, segment=(a, a + step))
        seg_ms.append(r.timings["total_ms"])
        seg_systems.append(len(r.systems))
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{part_id[:8]}.f1").write_text(text, encoding="utf-8")
        (out / f"{part_id[:8]}.svg").write_text(cold.svg, encoding="utf-8")
        cursor = {"columns": cold.columns, "systems": cold.systems}
        (out / f"{part_id[:8]}.cursor.json").write_text(json.dumps(cursor), encoding="utf-8")

    def med(key: str) -> float:
        return round(statistics.median(t[key] for t in warm), 1)

    return {
        "part": part_id,
        "title": title,
        "notes": len(notes),
        "columns": len(cold.columns),
        "lines": cold.lines,
        "missing": sum((want - drawn).values()),
        "extra": sum((drawn - want).values()),
        "beamGroups": len(lay.beams),
        "beamGroupsCut": _cut_groups(lay),
        "algorithmMs": algo_ms,
        "coldMs": cold.timings["total_ms"],
        "warmMs": med("total_ms"),
        "warmParseMs": med("parse_ms"),
        "warmPlanMs": med("plan_ms"),
        "warmDrawMs": med("draw_ms"),
        "warmSvgMs": med("svg_ms"),
        "segments": len(seg_ms),
        "segmentMs": round(statistics.median(seg_ms), 1),
        "segmentMaxMs": round(max(seg_ms), 1),
        "segmentSystems": round(statistics.mean(seg_systems), 2),
        "svgKb": round(len(cold.svg.encode()) / 1024),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("parts", nargs="*", help="part ids")
    parser.add_argument("--layer", help="every part of a layer instead (private: My library)")
    parser.add_argument("--repeat", type=int, default=3, help="warm draws per song")
    parser.add_argument("--segment", type=float, default=10.0, help="segment length in seconds")
    parser.add_argument("--out", type=Path, help="keep the F1 text, SVG and cursor map here")
    parser.add_argument("--json", type=Path, help="write the rows here")
    args = parser.parse_args()

    part_ids = list(args.parts)
    if args.layer:
        part_ids += [p for p in bundle.list_parts(layers=[args.layer]) if p not in part_ids]
    rows = []
    for part_id in part_ids:
        if not paths.part_notes_path(part_id).exists():
            continue
        row = draw(part_id, args.out, args.repeat, args.segment)
        rows.append(row)
        print(
            f"{part_id[:8]}  {row['notes']:5d} notes  {row['lines']:3d} lines  missing {row['missing']} "
            f"extra {row['extra']}  cut {row['beamGroupsCut']}  cold {row['coldMs']:6.1f}  "
            f"warm {row['warmMs']:6.1f}  segment {row['segmentMs']:5.1f} (max {row['segmentMaxMs']:5.1f}) ms  "
            f"{row['title']}",
            flush=True,
        )
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
