"""Seed the example set: the piano overlay found on every screenshot, and the
hand read ground truth Phase 1 of 04 left.

Since implementation 05 the overlay of an example is found, not placed (V-37):
one rectangle over the piano area — here the full width of the picture from the
upper line Phase 1 of 04 measured down to the bottom, at an angle of zero — and
every key inside it found by `video/finder.py`. All 24 screenshots get one,
including the three `ode` pictures 04 never seeded. The octave of the leftmost
key is what 04 measured where it did; the finder's default elsewhere.

The annotations are the two readings Phase 1 of 04 read by hand off a label
sheet, applying V-18 word for word, and the three Phase 2 of 04 added.

    cd aitu-backend
    uv run python scripts/seed_frame_examples.py

It never overwrites work: an example that already has a calibration keeps it, and
an annotation already saved at that offset line position is left alone. Pass
`--force` to replace them.
"""

from __future__ import annotations

import argparse
import json
import sys

from aitu_backend.schemas.video import Annotation, PianoRect
from aitu_backend.storage import paths
from aitu_backend.video import examples, finder, geometry, images
from aitu_backend.video.finder import NoKeyboard

#: Where Phase 1 of 04 left its measurements.
SPIKE = paths.repo_root() / "poc-synthesia-frames" / "data"

#: The example with no roll at all: a crop of a keyboard. Left out of the score
#: board rather than counted as a failure.
NO_ROLL = {"superestrella"}

#: The upper line of the three pictures 04 never measured, found by Phase 1 of 05
#: from the rows whose horizontal autocorrelation is strong, at 1280 px wide.
UPPER_LINES = {"ode1": 423.0, "ode2": 426.0, "ode3": 424.0}


def seed_calibrations(force: bool) -> tuple[int, int]:
    path = SPIKE / "calibrations.json"
    spike = json.loads(path.read_text()) if path.exists() else {}

    written = kept = 0
    for slug in examples.slugs():
        record = examples.load(slug)
        if record.calibration is not None and not force:
            kept += 1
            continue
        width, height = examples.image_size(slug)
        raw = spike.get(slug)
        upper = float(raw["upper_line"]) if raw else UPPER_LINES.get(slug)
        if upper is None:
            print(f"  {slug}: no upper line known — skipped")
            continue
        rect = PianoRect(
            x=0.0, y=upper, width=float(width), height=max(1.0, height - upper), angle=0.0
        )
        try:
            found = finder.find_overlay(
                examples.load_rgb(slug),
                rect,
                upper_line=upper,
                first_white_octave=int(raw["first_white_octave"]) if raw else None,
            )
        except NoKeyboard as exc:
            print(f"  {slug}: the finder refused — {exc}")
            continue
        # The spike's octave is kept only where the spike's pitch class agrees
        # with the finder's: on three pictures the spike named the wrong key,
        # and its octave went with it.
        if raw and int(raw["first_white_pc"]) != found.first_white_pitch_class:
            found.first_white_octave = geometry.default_octave_for(len(found.white_borders) - 1)
        found.note = f"seeded: {found.note}"
        record.calibration = found
        record.no_roll = record.no_roll or slug in NO_ROLL
        examples.save(record)
        written += 1
    return written, kept


def seed_annotations(force: bool) -> tuple[int, int]:
    path = SPIKE / "ground_truth.json"
    if not path.exists():
        print(f"no spike ground truth at {path} — nothing to seed")
        return 0, 0

    raw = json.loads(path.read_text())
    d_in_white_keys = float(raw["d_in_white_keys"])
    written = kept = 0
    for slug, entry in sorted(raw["examples"].items()):
        if not examples.exists(slug):
            continue
        record = examples.load(slug)
        if record.calibration is None:
            print(f"  {slug}: no calibration, so its offset line has no length — skipped")
            continue
        # The spike stored the offset line in white key widths, because that is
        # the only scale a screenshot has (V-22). The annotation stores it in
        # pixels of this picture, which is the same distance.
        offset_px = d_in_white_keys * record.calibration.white_width
        # within a pixel: the found overlay's median white key width is not the
        # spike's to the decimal, and a reading a tenth of a pixel over is the
        # same reading
        already = [a for a in record.annotations if abs(a.offset_px - offset_px) < 1.0]
        if already and not force:
            kept += 1
            continue
        for old in already:
            examples.delete_annotation(slug, old.offset_px)
        examples.put_annotation(
            slug,
            Annotation(
                offset_px=offset_px,
                onsets=entry.get("onsets", []),
                sustains=entry.get("sustains", []),
                skip=entry.get("skip", []),
                note=f"read by hand in Phase 1. {entry.get('note', '')}".strip(),
            ),
        )
        written += 1
    return written, kept


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace what is already saved")
    args = parser.parse_args()

    paths.frame_examples_root().mkdir(parents=True, exist_ok=True)
    print(f"examples: {len(examples.slugs())} screenshots at {images.WORK_WIDTH} px wide")

    written, kept = seed_calibrations(args.force)
    print(f"calibrations: {written} written, {kept} already there and left alone")
    written, kept = seed_annotations(args.force)
    print(f"annotations:  {written} written, {kept} already there and left alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
