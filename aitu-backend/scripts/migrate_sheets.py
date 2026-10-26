"""Store the marks of the old sheets (``sheet.json``, vexflow-v2) in the new sheet of every part.

Implementation 03, Phase 9. The page already draws a part that has no ``sheet.f1`` with the marks of its old sheet
(``part_sheet.build.with_legacy``); this script stores that result, so the marks no longer depend on ``sheet.json``,
and gives the stored sheets (the AI's, or one the user edited) the marks they lack. For each part with a
``sheet.json``:

* no stored sheet, or a plain algorithm one: the algorithm's sheet with the old marks (titles, lyrics, space between
  lines, figures set by hand, fingers, beam breaks and joins), stored as edited by the user (``Record.edited``), with
  ``reference: user`` when the old sheet renamed the reference figure (a new AI run then keeps it);
* a stored sheet with decisions: the titles, lyrics and space between lines it lacks, and the figures and fingers;
  beam marks only when the AI did not write it (beams are the AI's kind);
* the old clef changes and octave lines are never carried (the user's answer of 2026-10-26: the new clef rules
  everywhere); they are counted, with the other kinds the new sheet has no place for.

The record keeps what was carried (``legacy``), so a second run changes nothing. It writes versions of My library in
place, like a migration: run ``make db-backup`` first, and the dry run (the default) before ``--write``. With
``.env`` loaded:

    python scripts/migrate_sheets.py            # dry run: what each part would get
    python scripts/migrate_sheets.py --write
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy

from aitu_backend.part_sheet import build, legacy, store
from aitu_backend.pmn import events_file
from aitu_backend.sheet.sheet import f1
from aitu_backend.storage import bundle, locate, paths
from aitu_backend.transcription import pipeline


def _plain(counts: Counter) -> str:
    return ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "-"


def migrate(part: str, *, write: bool) -> tuple[str, Counter, Counter]:
    """One part: what happens to it, what is carried, what is dropped."""
    rhythm = pipeline.load_rhythm(part)
    if rhythm is None:
        return "no sheet.json", Counter(), Counter()
    dropped = legacy.dropped(rhythm)
    kept = store.load(part)
    if kept is not None and kept.record.legacy is not None:
        return "migrated already", Counter(), dropped
    if not legacy.has_marks(rhythm):
        return "nothing to carry", Counter(), dropped
    with pipeline.piece_lock(part):
        if pipeline.load_note_events(part) is None:
            return "no notes", Counter(), dropped
        header = events_file.read_header(paths.part_notes_path(part))
        notes = pipeline.starting_hands(part)
        if kept is None or not kept.record.decided:
            record = deepcopy(kept.record) if kept is not None else store.Record()
            algo = build.algorithm(part, notes, quarter_ms=record.quarter_ms, key=record.key)
            base, ai = algo.sheet, False
            record.quarter_ms = algo.quarter_ms
            if kept is None and build.reading_of(part).quarter_ms is not None:
                record.reference = (
                    "user"  # renamed with Transpose figures on the old sheet (rule 5)
                )
            what = "algorithm sheet"
        else:
            record = deepcopy(kept.record)
            base, ai = f1.read(build.current(part).text), record.enhanced
            what = f"{record.source} sheet"
        sheet, carried = build.with_legacy(base, notes, rhythm, ai=ai)
        if ai:
            beams = len(rhythm.beam_breaks) + len(rhythm.beam_joins)
            if beams:
                dropped["beam marks (the AI's)"] += beams
        done = {k: v for k, v in carried.items() if not k.endswith((" lost", " held", " left out"))}
        if not done:
            return f"{what}: nothing carried", carried, dropped
        if write:
            record.edited = True
            record.hands_revision = header.hands_revision
            record.legacy = done
            store.save(part, f1.write(sheet, mode="frames"), record)
            build.forget(part)
        return f"{what}: {'stored' if write else 'would store'}", carried, dropped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true", help="store the sheets (default: dry run)")
    args = parser.parse_args()

    totals: dict[str, Counter] = {"parts": Counter(), "carried": Counter(), "dropped": Counter()}
    for part in bundle.list_parts():
        try:
            where = locate.part(part)
            title = bundle.read_project(where.project_id).title
        except (locate.NotFound, OSError):
            continue
        what, carried, dropped = migrate(part, write=args.write)
        totals["parts"][what.split(":")[-1].strip()] += 1
        totals["carried"].update(carried)
        totals["dropped"].update(dropped)
        if carried or dropped:
            print(f"{part[:8]}  {where.layer:8} {title[:32]:32}  {what}")
            print(f"          carried: {_plain(carried)}")
            print(f"          dropped: {_plain(dropped)}")
    print()
    for name, counts in totals.items():
        print(f"{name}: {_plain(counts)}")
    if not args.write:
        print("(dry run: nothing written)")


if __name__ == "__main__":
    main()
