"""Write the new sheet of parts with the algorithm (``aitu_backend.sheet.proposal.frames``) and check it.

Implementation 03, Phase 2, task 6: the F1 frames sheet without compases for every part. For each part
it takes the starting hands (the saved hands, and the hand split for the notes without one:
``pipeline.starting_hands``), runs the algorithm (``propose_frames``: the reference figure, figures,
grace notes, beam groups, the armadura of each passage, the spelling, clefs and 8va), writes the F1
frames text, reads it back, and checks it: the rules of the product sheet (``frames.check``) and the
round trip with the matrix (every onset cell of each hand). Nothing is written to the data folder;
``--out`` keeps the F1 text of each part.

    python scripts/write_sheet.py 1a16a836-62b9-483b-af46-d89d0ab1b2d8 [--out DIR]
    python scripts/write_sheet.py --layer private [--json result.json]

In the container: ``docker exec aimpromptu-backend-1 python scripts/write_sheet.py ...``. On the
host, load ``.env`` first, or the script opens an empty ``.database/``.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.pmn import KEYS
from aitu_backend.sheet.sheet.spelling import key_alter, sign
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription.pipeline import starting_hands


def _ms(begin: float) -> float:
    return round((time.perf_counter() - begin) * 1000, 1)


def write(part_id: str, out: Path | None) -> dict[str, Any]:
    sheet_path = paths.part_sheet_path(part_id)
    sheet_json = json.loads(sheet_path.read_text(encoding="utf-8")) if sheet_path.exists() else {}
    project_path = paths.part_dir(part_id).parents[1] / "project.json"
    title = json.loads(project_path.read_text(encoding="utf-8")).get("title", "")

    begin = time.perf_counter()
    notes = starting_hands(part_id)
    hands_ms = _ms(begin)
    begin = time.perf_counter()
    prop = propose_frames(notes)
    propose_ms = _ms(begin)
    begin = time.perf_counter()
    text = f1.write(prop.sheet, mode="frames")
    write_ms = _ms(begin)
    begin = time.perf_counter()
    back = f1.read(text)
    read_ms = _ms(begin)

    problems = frames.check(back)
    got, lost = frames.cells_of(back, notes)
    exact = got == frames.matrix_cells(notes) and lost == 0
    at = frames.key_at(back)
    signs: Counter = Counter()
    for n in back.notes:
        s = sign(n.step, n.alter, at(n.frame))
        if s:
            signs[s] += 1
            white_name = (n.step, n.alter) in (("E", 1), ("B", 1), ("C", -1), ("F", -1))
            if white_name and key_alter(at(n.frame), n.step) != n.alter:
                signs["rule 4"] += 1
    figures = Counter(n.figure for n in back.notes if not n.grace)
    sizes = Counter()
    for staff in (1, 2):
        for b, c in Counter(
            (n.beam, n.frame) for n in back.notes if n.staff == staff and n.beam is not None
        ).items():
            sizes[b[0]] += 1
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{part_id[:8]}.f1").write_text(text, encoding="utf-8")
    saved = sheet_json.get("keySignature")
    return {
        "part": part_id,
        "title": title,
        "notes": len(notes),
        "columns": len({(n.staff, n.frame) for n in back.notes}),
        "quarterMs": round(prop.quarter_ms, 1),
        "key": back.key,
        "savedKey": KEYS.get(saved) if saved else None,
        "keyChanges": len(back.key_changes),
        "signs": dict(signs),
        "figures": {str(k): v for k, v in sorted(figures.items())},
        "beamSizes": dict(sorted(Counter(sizes.values()).items())),
        "info": prop.info,
        "problems": problems[:20],
        "problemCount": len(problems),
        "roundTrip": exact,
        "lost": lost,
        "handsMs": hands_ms,
        "proposeMs": propose_ms,
        "writeMs": write_ms,
        "readMs": read_ms,
        "f1Kb": round(len(text.encode()) / 1024, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("parts", nargs="*", help="part ids")
    parser.add_argument("--layer", help="every part of a layer instead (private: My library)")
    parser.add_argument("--out", type=Path, help="keep the F1 text here")
    parser.add_argument("--json", type=Path, help="write the rows here")
    args = parser.parse_args()

    part_ids = list(args.parts)
    if args.layer:
        part_ids += [p for p in bundle.list_parts(layers=[args.layer]) if p not in part_ids]
    rows = []
    for part_id in part_ids:
        if not paths.part_notes_path(part_id).exists():
            continue
        row = write(part_id, args.out)
        rows.append(row)
        print(
            f"{part_id[:8]}  {row['notes']:5d} notes  key {row['key']:+d} (saved {row['savedKey']})  "
            f"changes {row['keyChanges']}  problems {row['problemCount']}  round trip {row['roundTrip']}  "
            f"hands {row['handsMs']:7.1f}  propose {row['proposeMs']:6.1f}  write {row['writeMs']:5.1f} "
            f"read {row['readMs']:5.1f} (ms)  {row['title']}"
        )
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
