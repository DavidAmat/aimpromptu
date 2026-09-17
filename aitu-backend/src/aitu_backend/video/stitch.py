"""The stitched roll: the whole piece rebuilt as one tall picture (V-32).

Task 4.1.1 of `04-synthesia-to-notes`. The scroll speed is constant to three
parts in a thousand over a piece, so the top ``scrollSpeed x sampleMs`` rows of
each sampled frame are exactly the strip of the roll nobody has seen yet. Piling
them up rebuilds the whole piece as one picture whose vertical axis is time, and
a note is then one shape in it with a top row and a bottom row, both of which
convert straight to seconds.

**The picture keeps the sense of a frame.** Time runs *upward*: the bottom row is
the start of the piece and the top row is the end, exactly as in the video, where
a rectangle at the top of the roll is the future and the one about to touch the
piano is the present. That is not a detail of taste. It means the rectangle tip —
the lowest row of a shape — is still the onset and the last rectangle tip — its
highest row — is still the release, so every word of the detector's vocabulary,
and the ``clipped`` and ``entering`` flags of :class:`DetectedRun`, mean here what
they mean on a frame:

* a shape whose lowest row is the bottom edge of the stitched roll is a note that
  was already sounding when the video started — the same fact ``clipped`` records
  about a run the upper line cut (V-16);
* a shape whose highest row is the top edge is a note that is still falling when
  the video ends — the same fact ``entering`` records about a run still coming
  into view at the roll top (V-28).

**Where the strip is taken.** Below the roll top and far above the upper line, so
no halo, no sparkle and no strike light enters it at all (V-23, V-32). The two
edges are the ones motion measured for this video (V-28): the strip starts
``STRIP_MARGIN`` white key widths below ``rollTop`` and is one frame of travel
tall, which leaves the whole of the rest of the roll between it and the guard
band.

**The head.** A strip one travel tall catches every row of the roll exactly once
— except the rows that were already *below* the strip in the very first sampled
frame, which are the first few seconds of the piece. Those are read out of frame
0 in one go, from the strip down to the guard band, and they are the bottom of
the picture. Without them a video that starts playing immediately loses its first
notes without saying so.

**What is piled up** is the foreground strength — how far each pixel is from the
background plate (V-15, V-29) — and not the picture. The plate is what removes a
title, a watermark and the octave guide lines, and it has to be applied per frame,
before the strip is cut, because the plate is in frame coordinates and the strip
is not.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.video import Calibration, VideoMeasurement
from aitu_backend.video import geometry, store
from aitu_backend.video.detector import DEFAULTS, DetectorSettings
from aitu_backend.video.plate import foreground_strength

#: How far below the roll top the strip starts, in median white key widths
#: (V-22). The roll top is measured from motion and is worth a little room; a
#: rectangle coming into view at that exact line is caught a few rows later, and
#: no row of the roll is lost by it because every row scrolls through the strip.
STRIP_MARGIN = 0.5


class NotMeasured(RuntimeError):
    """There is no scroll speed, so the strips cannot be placed."""


@dataclass(frozen=True)
class StitchGeometry:
    """Where the strip sits, how tall the picture is, and what a row means.

    ``row_seconds`` is the whole of V-05 for the stitched roll: a row is a
    distance above the upper line, and a distance is a time.
    """

    #: First row of the frame the strip is cut from, and how tall it is.
    strip_top: int
    strip_height: int
    #: Rows of the finished picture, and how many of them are the head.
    rows: int
    head_rows: int
    #: How far the roll falls between two sampled frames, in picture pixels.
    travel: float
    px_per_second: float
    #: The upper line of the calibration, kept so a row can be turned into a time.
    upper_line: float
    #: Picture row of the frame that the **bottom** row of the stitched roll
    #: holds. Everything below it is inside the halo guard band.
    bottom_row: int

    def seconds(self, row: float) -> float:
        """The time a shape edge at this row of the stitched roll sounds at.

        The bottom row of the picture is the oldest content, so a row counted
        from the bottom is a distance above the upper line at the moment the
        video started, and that distance over the scroll speed is a time (V-05).
        """
        above = (self.rows - 1 - row) + (self.upper_line - self.bottom_row)
        return above / self.px_per_second


def plan(
    calibration: Calibration,
    measurement: VideoMeasurement,
    frame_count: int,
    settings: DetectorSettings = DEFAULTS,
) -> StitchGeometry:
    """Where every strip goes, before a single pixel is read.

    Separated from the reading so the memory the stitch will take can be stated
    before it is taken, and so a test can check the arithmetic without a video.
    """
    travel = measurement.scroll_speed.px_per_frame
    if travel <= 0:
        raise NotMeasured("the scroll speed has not been measured, so a strip has no height")
    if frame_count < 1:
        raise NotMeasured("a stitched roll needs at least one sampled frame")

    strip_top = int(round(calibration.roll_top + STRIP_MARGIN * calibration.white_width))
    strip_height = int(round(travel))
    guard = geometry.guard_band_px(calibration, settings.guard_band_default)
    bottom_row = int(round(calibration.upper_line - guard)) - 1
    if bottom_row < strip_top + strip_height:
        # The trustworthy band is shorter than one strip. Nothing is lost: the
        # head is simply empty and the piece starts where the strip does.
        bottom_row = strip_top + strip_height - 1

    head_rows = bottom_row - (strip_top + strip_height) + 1
    rows = head_rows + strip_height + int(round((frame_count - 1) * travel))
    return StitchGeometry(
        strip_top=strip_top,
        strip_height=strip_height,
        rows=rows,
        head_rows=head_rows,
        travel=travel,
        px_per_second=measurement.scroll_speed.px_per_second,
        upper_line=calibration.upper_line,
        bottom_row=bottom_row,
    )


def rows_of(index: int, geom: StitchGeometry) -> tuple[int, int]:
    """Which rows of the picture frame ``index`` fills, counted from the bottom.

    The bottom is the oldest content and the offsets are what the roll has
    scrolled by. Frame 0 fills the head and its own strip; every later frame
    fills exactly what the roll moved on by, which is
    ``round(i x travel) - round((i-1) x travel)`` rows — sixteen or seventeen on
    a video travelling 16.89 — and never the same row twice. Rounding each
    offset against the exact float travel rather than stepping by a whole number
    of rows is what keeps the picture from drifting: at 17 rows a frame the
    error is 0.11 px a frame, which over 2728 frames is 305 px, or 1.8 seconds.
    """
    offset = int(round(index * geom.travel))
    end = geom.head_rows + geom.strip_height - 1 + offset
    if index == 0:
        return 0, end
    start = geom.head_rows + geom.strip_height + int(round((index - 1) * geom.travel))
    return start, end


def build(
    audio_uuid: str,
    *,
    channel: str = "plate",
    settings: DetectorSettings = DEFAULTS,
    frames: int | None = None,
    reporter: BaseProgress | None = None,
) -> tuple[np.ndarray, StitchGeometry]:
    """Read every sampled frame once and pile its fresh strip into one picture.

    The answer is ``uint8``: the foreground strength is the largest difference
    between a pixel and the plate over the three colour channels, which is
    already a number from 0 to 255, so nothing is lost by storing it that way and
    a four and a half minute video costs 60 MB instead of 240.

    Only the rows that are actually new are read — seventeen of seven hundred and
    twenty for every frame after the first — which is what makes this cheaper
    than the per-frame detector rather than more expensive: about a thirtieth of
    the pixel work of reading the whole roll in every frame (V-32).
    """
    calibration = store.load_calibration(audio_uuid)
    if calibration is None:
        raise NotMeasured(f"Audio {audio_uuid} has no piano overlay yet")
    measurement = store.load_measurement(audio_uuid)
    if measurement is None:
        raise NotMeasured(f"Audio {audio_uuid} has no measured scroll speed yet")
    count = store.frame_count(audio_uuid)
    if frames is not None:
        count = min(count, frames)

    geom = plan(calibration, measurement, count, settings)
    plate = store.load_plate(audio_uuid)
    roll = np.zeros((geom.rows, calibration.image_width), dtype=np.uint8)

    progress = default_reporter(reporter)
    with progress.stage("stitch", total=count) as stage:
        for index in range(count):
            start, end = rows_of(index, geom)
            # Always read from the top of the strip downward: the newest content
            # is the highest, and frame 0 reaches all the way down to the guard
            # band because it is the only frame that has ever shown those rows.
            a, b = geom.strip_top, geom.strip_top + (end - start) + 1
            image = store.load_frame(audio_uuid, index)[a:b]
            strength = foreground_strength(
                image,
                plate[a:b] if plate is not None else None,
                channel=channel,
                settings=settings,
            )
            # Counted from the bottom, so the newest content ends up at the top.
            roll[geom.rows - 1 - end : geom.rows - start] = np.clip(strength, 0, 255).astype(
                np.uint8
            )
            stage.advance(1)
    return roll, geom
