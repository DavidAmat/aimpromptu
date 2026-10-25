"""Store the Sonnet sheets that an earlier run already paid for as the new sheet of their parts.

Implementation 03, Phase 5. The user's answer to the Phase 5 question (2026-10-25): the songs Sonnet has already
written show Sonnet's sheet; the others keep their data and get a button to run Sonnet. Phase 4 ran the 10 viewer
songs (versions of My library) and kept each final sheet in ``<database>/lab/sheet-llm/<run>/<part8>.f1``, with
its windows and cost in ``summary.json``. For each part of the run:

1. the sheet must still fit the notes: every onset cell of the matrix once (``frames.cells_of``), or the part is
   left as it is;
2. its hands go into ``notes.pmn`` (the saved hands before it go to the part's history) and the sheet into
   ``sheet.f1``, as the Sonnet job does at its end (``part_sheet.job.commit``).

It writes versions of My library in place, like a migration: run ``make db-backup`` first (with ``.env`` loaded).

    python scripts/import_llm_sheets.py --run viewer-final --dry-run
    python scripts/import_llm_sheets.py --run viewer-final
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone

from aitu_backend.part_sheet import job, store
from aitu_backend.pmn import events_file
from aitu_backend.sheet.llm.frames import PROMPT_VERSION
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet_llm import MODEL
from aitu_backend.storage import bundle, paths
from aitu_backend.transcription import pipeline


def unhanded(cells: Counter) -> Counter:
    out: Counter = Counter()
    for (_, midi, cell), k in cells.items():
        out[(midi, cell)] += k
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--run", default="viewer-final", help="the folder of the run in <database>/lab/sheet-llm/"
    )
    parser.add_argument("--dry-run", action="store_true", help="check every part, write nothing")
    args = parser.parse_args()

    folder = paths.lab_dir() / "sheet-llm" / args.run
    rows = json.loads((folder / "summary.json").read_text())
    written = datetime.fromtimestamp((folder / "summary.json").stat().st_mtime, timezone.utc)
    known = set(bundle.list_parts())
    for row in rows:
        part = row["part"]
        name = part[:8]
        if part not in known:
            print(f"{name}  no such part: skipped")
            continue
        text = (folder / f"{name}.f1").read_text()
        sheet = f1.read(text)
        notes = pipeline.starting_hands(part)
        got, lost = frames.cells_of(sheet, notes)
        if lost or unhanded(got) != unhanded(frames.matrix_cells(notes)):
            print(f"{name}  the notes changed since the run ({lost} notes without a cell): skipped")
            continue
        windows = [
            [w["start"], w["end"], "llm" if w["status"] == "ok" else "algorithm"]
            for w in row["windowsLog"]
        ]
        states = [state for _, _, state in windows]
        record = store.Record(
            source=(
                "llm"
                if all(s == "llm" for s in states)
                else "mixed" if "llm" in states else "algorithm"
            ),
            windows=windows,
            quarter_ms=row["quarterMs"],
            reference=row["reference"].get("source"),
            model=MODEL,
            prompt=PROMPT_VERSION,
            usd=float(row["usd"]),
            requests=int(row["requests"]),
            written=written.isoformat(timespec="seconds"),
        )
        before = events_file.read_header(paths.part_notes_path(part))
        print(
            f"{name}  {len(sheet.notes)} notes, {len(windows)} windows ({record.source}), quarter "
            f"{record.quarter_ms:g} ms, ${record.usd:.2f}, sheet.f1 {'there' if store.load(part) else 'new'}",
            end="",
        )
        if args.dry_run:
            print("  (dry run)")
            continue
        job.commit(part, sheet, text, record, before.notes_revision)
        after = events_file.read_header(paths.part_notes_path(part))
        print(f"  handsRevision {before.hands_revision} -> {after.hands_revision}")


if __name__ == "__main__":
    main()
