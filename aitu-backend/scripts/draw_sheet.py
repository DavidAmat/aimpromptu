"""Draw parts with the new sheet core (``aitu_backend.sheet``): the algorithm, then the bars engine.

Implementation 03, Phase 1, task 3: the proof that the chain of the research runs inside the
backend. For each part it reads ``notes.pmn`` (the saved hands) and the key of ``sheet.json``, runs
the algorithm (``proposal.propose``, beat tracking on, the notes' own hands), writes the F1 bars
text with frame anchors, and draws it (``engrave.cursor.render_song``) once cold and ``--repeat``
times warm. Nothing is written to the data folder; ``--out`` keeps the F1, the SVG and the cursor
map of each part.

    python scripts/draw_sheet.py 1a16a836-62b9-483b-af46-d89d0ab1b2d8 [--out DIR]
    python scripts/draw_sheet.py --layer private [--json result.json]

In the container: ``docker exec aimpromptu-backend-1 python scripts/draw_sheet.py ...``. On the
host, load ``.env`` first, or the script opens an empty ``.database/``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from aitu_backend.sheet.engrave.cursor import render_song
from aitu_backend.sheet.proposal.pipeline import propose
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.pmn import key_of_sheet_json, notes_from_pmn
from aitu_backend.storage import bundle, paths


def _ms(begin: float) -> float:
    return round((time.perf_counter() - begin) * 1000, 1)


def draw(part_id: str, repeat: int, out: Path | None) -> dict[str, Any]:
    begin = time.perf_counter()
    body = json.loads(paths.part_notes_path(part_id).read_text(encoding="utf-8"))
    sheet_path = paths.part_sheet_path(part_id)
    sheet_json = json.loads(sheet_path.read_text(encoding="utf-8")) if sheet_path.exists() else {}
    project_path = paths.part_dir(part_id).parents[1] / "project.json"
    title = json.loads(project_path.read_text(encoding="utf-8")).get("title", "")
    notes = notes_from_pmn(body)
    key = key_of_sheet_json(sheet_json)
    read_ms = _ms(begin)

    begin = time.perf_counter()
    prop = propose(notes, key=key, track=True)
    propose_ms = _ms(begin)

    begin = time.perf_counter()
    text = f1.write(prop.sheet, mode="bars", anchors=True)
    write_ms = _ms(begin)

    cold = render_song(text)
    warm = [render_song(text).timings["total_ms"] for _ in range(repeat)]
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{part_id[:8]}.f1").write_text(text, encoding="utf-8")
        (out / f"{part_id[:8]}.svg").write_text(cold.svg, encoding="utf-8")
        cursor = {"bars": cold.bars, "width": cold.width, "height": cold.height}
        cursor |= {"systems": cold.systems, "columns": cold.columns}
        (out / f"{part_id[:8]}.cursor.json").write_text(json.dumps(cursor), encoding="utf-8")
    return {
        "part": part_id,
        "title": title,
        "notes": len(notes.key),
        "unhanded": int((notes.hand == 0).sum()),
        "bars": cold.bars,
        "quarterMs": round(prop.quarter_ms, 1),
        "meter": prop.meter,
        "readMs": read_ms,
        "proposeMs": propose_ms,
        "writeMs": write_ms,
        "renderColdMs": cold.timings["total_ms"],
        "renderWarmMs": round(statistics.median(warm), 1) if warm else None,
        "svgKb": round(len(cold.svg) / 1024, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("parts", nargs="*", help="part ids")
    parser.add_argument("--layer", help="every part of a layer instead (private: My library)")
    parser.add_argument("--repeat", type=int, default=3, help="warm draws per part")
    parser.add_argument("--out", type=Path, help="keep the F1, SVG and cursor map here")
    parser.add_argument("--json", type=Path, help="write the rows here")
    args = parser.parse_args()

    part_ids = list(args.parts)
    if args.layer:
        part_ids += [p for p in bundle.list_parts(layers=[args.layer]) if p not in part_ids]
    rows = []
    for part_id in part_ids:
        if not paths.part_notes_path(part_id).exists():
            continue
        row = draw(part_id, args.repeat, args.out)
        rows.append(row)
        print(
            f"{part_id[:8]}  {row['notes']:5d} notes  {row['bars']:4d} bars  "
            f"read {row['readMs']:6.1f}  propose {row['proposeMs']:7.1f}  write {row['writeMs']:5.1f}  "
            f"render {row['renderColdMs']:6.1f} cold {row['renderWarmMs']:6.1f} warm (ms)  "
            f"{row['title']}"
        )
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
