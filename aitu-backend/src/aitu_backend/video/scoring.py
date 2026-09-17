"""The score board: what the detector found, invented and missed.

Task 2.3.3. It runs every example at every annotated offset line position and
reports, per line, onsets found, invented and missed, the same three for
sustains, and the list of keys that disagree. A total sits at the top, and every
change from here on quotes it (V-20).

Two rules about what is counted:

* **Released is the default and is never written down** (V-19), so a key that is
  in neither list is released on both sides and is not a disagreement.
* **A key the picture cannot answer for comes out of the score on both sides**
  rather than being guessed. Phase 1 found one: a rectangle entirely past the
  upper line with the strike light over what is left.
"""

from __future__ import annotations

from aitu_backend.matrix.keys import CHROMATIC_EN
from aitu_backend.schemas.video import (
    Annotation,
    Disagreement,
    ScoreBoard,
    ScoreLine,
)
from aitu_backend.video import detector, examples
from aitu_backend.video.detector import DetectorSettings


def _name(midi: int) -> str:
    return f"{CHROMATIC_EN[midi % 12]}{midi // 12 - 1}"


def _state(midi: int, onsets: set[int], sustains: set[int]) -> str:
    if midi in onsets:
        return "onset"
    if midi in sustains:
        return "sustain"
    return "released"


def score_one(
    slug: str,
    annotation: Annotation,
    detected_onsets: list[int],
    detected_sustains: list[int],
) -> ScoreLine:
    """One hand reading against one detection, both under the same offset line."""
    skip = set(annotation.skip)
    truth_onsets = set(annotation.onsets) - skip
    truth_sustains = set(annotation.sustains) - skip
    found_onsets = set(detected_onsets) - skip
    found_sustains = set(detected_sustains) - skip

    disagreements = [
        Disagreement(
            midi=midi,
            name_en=_name(midi),
            truth=_state(midi, truth_onsets, truth_sustains),  # type: ignore[arg-type]
            detected=_state(midi, found_onsets, found_sustains),  # type: ignore[arg-type]
        )
        for midi in sorted(
            (truth_onsets | truth_sustains | found_onsets | found_sustains)
            - ((truth_onsets & found_onsets) | (truth_sustains & found_sustains))
        )
    ]

    return ScoreLine(
        slug=slug,
        offset_px=annotation.offset_px,
        onsets_found=len(truth_onsets & found_onsets),
        onsets_invented=len(found_onsets - truth_onsets),
        onsets_missed=len(truth_onsets - found_onsets),
        sustains_found=len(truth_sustains & found_sustains),
        sustains_invented=len(found_sustains - truth_sustains),
        sustains_missed=len(truth_sustains - found_sustains),
        disagreements=disagreements,
    )


def _total(lines: list[ScoreLine]) -> ScoreLine:
    return ScoreLine(
        slug="total",
        offset_px=0.0,
        onsets_found=sum(line.onsets_found for line in lines),
        onsets_invented=sum(line.onsets_invented for line in lines),
        onsets_missed=sum(line.onsets_missed for line in lines),
        sustains_found=sum(line.sustains_found for line in lines),
        sustains_invented=sum(line.sustains_invented for line in lines),
        sustains_missed=sum(line.sustains_missed for line in lines),
    )


def board(
    channel: str = "plate",
    settings: DetectorSettings = detector.DEFAULTS,
    only: list[str] | None = None,
    colour_check: bool = False,
) -> ScoreBoard:
    """Run every annotated example at every annotated offset line position.

    An example without a calibration, without an annotation, or with no roll to
    read is named in ``skipped`` with the reason rather than counted as a pass or
    as a failure. An honest failure list is a result; a rounded up number is not.
    """
    lines: list[ScoreLine] = []
    skipped: dict[str, str] = {}

    for slug in only or examples.slugs():
        record = examples.load(slug)
        if record.no_roll:
            skipped[slug] = "marked as having no roll to read"
            continue
        if record.calibration is None:
            skipped[slug] = "no calibration yet"
            continue
        if not record.annotations:
            skipped[slug] = "no annotation yet"
            continue

        image = examples.load_rgb(slug)
        for annotation in record.annotations:
            result = detector.detect(
                image,
                record.calibration,
                annotation.offset_px,
                channel=channel,
                settings=settings,
                slug=slug,
                colour_check=colour_check,
            )
            lines.append(score_one(slug, annotation, result.onsets, result.sustains))

    return ScoreBoard(lines=lines, total=_total(lines), skipped=skipped)
