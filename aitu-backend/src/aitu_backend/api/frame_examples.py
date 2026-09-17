"""`/frame-examples` — the Synthesia example screenshots and their score board.

Phase 2 of `04-synthesia-to-notes`. The example set is how a detection rule earns
its place: a rule ships with its measured score over these pictures, or it does
not ship (V-20).

The pictures are served at the working resolution, which is the width the
detector reads, so a coordinate the user places in the calibration UI means the
same thing on both sides.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from aitu_backend.schemas.video import (
    Annotation,
    Calibration,
    Detection,
    ExampleSummary,
    FindRequest,
    FrameExample,
    Geometry,
    ScoreBoard,
)
from aitu_backend.video import detector, examples, finder, geometry, scoring
from aitu_backend.video.examples import ExampleNotFound
from aitu_backend.video.finder import NoKeyboard

router = APIRouter(prefix="/frame-examples", tags=["frame-examples"])


def _found(slug: str) -> None:
    if not examples.exists(slug):
        raise HTTPException(status_code=404, detail=f"No example screenshot named '{slug}'")


@router.get("", response_model=list[ExampleSummary], response_model_by_alias=True)
def list_examples() -> list[ExampleSummary]:
    """Every example screenshot, with how far its annotation has got."""
    out: list[ExampleSummary] = []
    for slug in examples.slugs():
        record = examples.load(slug)
        out.append(
            ExampleSummary(
                slug=slug,
                has_calibration=record.calibration is not None,
                annotation_count=len(record.annotations),
                no_roll=record.no_roll,
            )
        )
    return out


@router.get("/score", response_model=ScoreBoard, response_model_by_alias=True)
def score_board(
    channel: str = Query("plate", description="plate, edges or both"),
    colour_check: bool = Query(False, alias="colourCheck"),
) -> ScoreBoard:
    """Run every annotated example at every annotated offset line and report.

    This is the number every change from here on quotes. `channel` and
    `colourCheck` exist so a change can be measured rather than asserted.
    """
    return scoring.board(channel=channel, settings=detector.DEFAULTS, colour_check=colour_check)


@router.get("/{slug}", response_model=FrameExample, response_model_by_alias=True)
def get_example(slug: str) -> FrameExample:
    """One example: its size, its calibration and every annotation on it."""
    _found(slug)
    return examples.load(slug)


@router.get("/{slug}/image")
def get_example_image(slug: str) -> FileResponse:
    """The working-resolution copy of one example — what the detector reads."""
    try:
        path = examples.image_path(slug)
    except ExampleNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/jpeg")


@router.put("/{slug}/calibration", response_model=FrameExample, response_model_by_alias=True)
def put_calibration(slug: str, calibration: Calibration) -> FrameExample:
    """Save the piano overlay of one example, keeping its annotations."""
    _found(slug)
    return examples.set_calibration(slug, calibration)


@router.post("/{slug}/find", response_model=Calibration, response_model_by_alias=True)
def find_overlay(slug: str, body: FindRequest) -> Calibration:
    """The one rectangle in, the piano overlay found inside it out (V-37).

    Nothing is saved: the screen shows the answer and the user saves it through
    `PUT /{slug}/calibration`. A rectangle with no keyboard in it is a 422 with
    the finder's own words, so the screen can say why.
    """
    _found(slug)
    image = examples.load_rgb(slug)
    try:
        return finder.find_overlay(
            image,
            body.piano_rect,
            upper_line=body.upper_line,
            first_white_octave=body.first_white_octave,
        )
    except NoKeyboard as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{slug}/geometry", response_model=Geometry, response_model_by_alias=True)
def build_geometry(slug: str, calibration: Calibration) -> Geometry:
    """Every key and lane a calibration implies, as the backend computes them.

    The frontend has the same geometry and draws from its own, because a round
    trip per drag is not a UI. This endpoint is what proves the two agree.
    """
    _found(slug)
    return geometry.geometry(calibration)


@router.put("/{slug}/annotation", response_model=FrameExample, response_model_by_alias=True)
def put_annotation(slug: str, annotation: Annotation) -> FrameExample:
    """Save one hand reading, at one offset line position."""
    _found(slug)
    return examples.put_annotation(slug, annotation)


@router.delete("/{slug}/annotation", response_model=FrameExample, response_model_by_alias=True)
def delete_annotation(slug: str, offset_px: float = Query(..., alias="offsetPx")) -> FrameExample:
    """Remove the reading at one offset line position."""
    _found(slug)
    return examples.delete_annotation(slug, offset_px)


@router.patch("/{slug}", response_model=FrameExample, response_model_by_alias=True)
def patch_example(slug: str, no_roll: bool = Query(..., alias="noRoll")) -> FrameExample:
    """Mark an example as having no roll to read, or take the mark off again.

    `superestrella` is a crop of a keyboard with no roll at all. It is left out of
    the score board rather than counted as a failure.
    """
    _found(slug)
    record = examples.load(slug)
    record.no_roll = no_roll
    return examples.save(record)


@router.post("/{slug}/detect", response_model=Detection, response_model_by_alias=True)
def detect_example(
    slug: str,
    offset_px: float = Query(..., alias="offsetPx", gt=0),
    channel: str = Query("plate"),
    colour_check: bool = Query(False, alias="colourCheck"),
) -> Detection:
    """Run the detector on one example with its own saved calibration.

    Every run comes back with the pixels it was found at, so the UI can draw it on
    the picture: a disagreement with the hand reading has to be something you can
    look at, not something you have to imagine (Task 2.3.2).
    """
    _found(slug)
    record = examples.load(slug)
    if record.calibration is None:
        raise HTTPException(status_code=409, detail=f"'{slug}' has no calibration yet")
    image = examples.load_rgb(slug)
    return detector.detect(
        image,
        record.calibration,
        offset_px,
        channel=channel,
        slug=slug,
        colour_check=colour_check,
    )
