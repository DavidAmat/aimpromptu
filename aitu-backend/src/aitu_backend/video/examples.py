"""The example set: the screenshots, their calibrations and their annotations.

Task 2.2.1. The screenshots stay where the user put them, under
`context/implementations/04-synthesia-to-notes/examples/`, and are read from
there; only what we derive from them is data. Every example needs its own
calibration because every example is a different piano.
"""

from __future__ import annotations

import json

from aitu_backend.schemas.video import Annotation, Calibration, FrameExample
from aitu_backend.storage import paths
from aitu_backend.video import images
from aitu_backend.video.upgrade import upgrade


class ExampleNotFound(LookupError):
    """No screenshot with that slug."""


def slugs() -> list[str]:
    """Every example screenshot on disk, sorted."""
    return paths.list_frame_example_slugs()


def exists(slug: str) -> bool:
    return (paths.frame_examples_source_dir() / f"{slug}.png").is_file()


def _require(slug: str) -> None:
    if not exists(slug):
        raise ExampleNotFound(f"No example screenshot named '{slug}'")


def image_path(slug: str):
    """The working-resolution copy of one example, written if it is missing."""
    _require(slug)
    source = paths.frame_examples_source_dir() / f"{slug}.png"
    destination = paths.frame_example_image_path(slug)
    images.ensure_work_copy(source, destination)
    return destination


def image_size(slug: str) -> tuple[int, int]:
    """Width and height of the working-resolution copy."""
    _require(slug)
    source = paths.frame_examples_source_dir() / f"{slug}.png"
    return images.ensure_work_copy(source, paths.frame_example_image_path(slug))


def load_rgb(slug: str):
    """One example as float RGB at the working resolution."""
    return images.load_rgb(image_path(slug))


def load(slug: str) -> FrameExample:
    """The record of one example. A record that has never been saved is empty."""
    _require(slug)
    width, height = image_size(slug)
    path = paths.frame_example_path(slug)
    if not path.exists():
        return FrameExample(slug=slug, image_width=width, image_height=height)
    raw = json.loads(path.read_text())
    # A record written by 04 keeps its overlay as a grid. It is spelt out into
    # per-key borders on the way in (V-38) and written back in the new shape the
    # first time it is saved; its hand readings never notice.
    if raw.get("calibration"):
        raw["calibration"] = upgrade(raw["calibration"])
    record = FrameExample.model_validate(raw)
    # The picture is the truth about its own size: a record written before the
    # working resolution changed would otherwise hand the UI a stale frame.
    record.slug = slug
    record.image_width, record.image_height = width, height
    return record


def save(record: FrameExample) -> FrameExample:
    """Write one example's record, sorting its annotations by offset line."""
    _require(record.slug)
    record.annotations.sort(key=lambda a: a.offset_px)
    path = paths.frame_example_path(record.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.model_dump(by_alias=True), indent=2) + "\n")
    return record


def set_calibration(slug: str, calibration: Calibration) -> FrameExample:
    """Replace the piano overlay of one example, keeping its annotations."""
    record = load(slug)
    record.calibration = calibration
    return save(record)


def put_annotation(slug: str, annotation: Annotation) -> FrameExample:
    """Add or replace the reading at one offset line position.

    The entry is the triple (example, offset line position, the keys marked), so
    two readings a pixel apart are two entries — which is the point of the page.
    Saving over the same position replaces it rather than piling up near
    duplicates that nobody can tell apart afterwards.
    """
    record = load(slug)
    kept = [a for a in record.annotations if round(a.offset_px) != round(annotation.offset_px)]
    record.annotations = [*kept, annotation]
    return save(record)


def delete_annotation(slug: str, offset_px: float) -> FrameExample:
    """Remove the reading at one offset line position."""
    record = load(slug)
    record.annotations = [a for a in record.annotations if round(a.offset_px) != round(offset_px)]
    return save(record)
