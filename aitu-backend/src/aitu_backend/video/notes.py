"""From the stitched roll to the notes of the piece (Story 4.1).

Task 4.1.1 and Task 4.1.2. The stitched roll of :mod:`aitu_backend.video.stitch`
is the whole video as one tall picture whose vertical axis is time; this module
reads the notes out of it and turns their rows into seconds.

**A note is one run in one key's lane, not one connected shape.** V-32 says a
note is one connected shape in the stitched roll, and that is the picture it
describes; what ships is the same idea read with the detector's own machinery —
the span fill, the coverage, the gap close, the split at a prominent border and
the width gate — because those are the rules Phase 1 measured and every one of
them still applies to this picture. Two things connected components cannot do and
these can: they cut two notes of the same key that touch, which V-26 says is 1351
borders in sixty frames of a real video, and they keep two keys struck together
apart when their rectangles touch sideways. The plain labelling is still run
beside it and its count is reported, because a rule ships with its measured score
or it does not ship (V-20).

**The rows are the same rows.** The stitched roll is built at the picture's own
scale, vertically and horizontally, so every threshold Phase 1 measured in white
key widths means here exactly what it means on a frame. Nothing is rescaled and
nothing is retuned.

**What the detector's words mean here** is set out in :mod:`.stitch`: the picture
keeps the sense of a frame, so a shape's lowest row is its onset and its highest
row is its release, ``clipped`` is a note that was already sounding when the video
started and ``entering`` is one still falling when it ended.

The floor on note length (D-05) is **not** applied here. It belongs to the step
that builds the matrix, which already applies it. This step writes what it saw.
"""

from __future__ import annotations

import time

import numpy as np
from scipy import ndimage

from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.video import (
    Calibration,
    NoteReport,
    RejectedRun,
    VideoNote,
    VideoNotes,
)
from aitu_backend.video import detector, geometry, stitch, store
from aitu_backend.video.detector import DEFAULTS, DetectorSettings
from aitu_backend.video.stitch import StitchGeometry

#: How many rejected shapes are kept for the screen to draw. A picture forty
#: thousand rows tall rejects thousands of specks, and a list of them is a
#: scroll bar, not an answer; the counts per gate are in the report and they are
#: what says whether a gate is doing something surprising.
MAX_REJECTED = 400


def connected_shapes(roll: np.ndarray, settings: DetectorSettings = DEFAULTS) -> int:
    """How many shapes plain connected components finds in the same picture.

    The letter of V-32, kept as the comparison the shipping route has to beat
    (V-20). Specks are dropped the way the spike dropped them, so the two counts
    are about the same thing.
    """
    labels, _ = ndimage.label(roll > settings.tau_foreground)
    kept = 0
    for slices in ndimage.find_objects(labels):
        rows, columns = slices
        if rows.stop - rows.start >= 4 and columns.stop - columns.start >= 6:
            kept += 1
    return kept


def busy_keys(
    roll: np.ndarray, calibration: Calibration, settings: DetectorSettings = DEFAULTS
) -> list[int]:
    """The keys whose lane core is foreground more than ``BUSY_LANE`` of the time.

    The plate is the median of what stands still (V-44) and a key held for most
    of the piece would put its own rectangle into it, so a lane that reads as
    foreground this often is named in the report rather than trusted.
    """
    from aitu_backend.video.plate import BUSY_LANE

    out: list[int] = []
    for key in geometry.keys(calibration):
        a, b = max(0, int(round(key.left))), min(roll.shape[1], int(round(key.right)) + 1)
        if b - a < 2:
            continue
        if float((roll[:, a:b] > settings.tau_foreground).mean()) > BUSY_LANE:
            out.append(key.midi)
    return out


def notes_from_roll(
    roll: np.ndarray,
    calibration: Calibration,
    geom: StitchGeometry,
    duration_seconds: float,
    *,
    settings: DetectorSettings = DEFAULTS,
    rejected: list[RejectedRun] | None = None,
) -> tuple[list[VideoNote], int]:
    """Every note the stitched roll holds, in time order, and how many fell off the end.

    The stitched roll has no upper line to cut a shape and no roll top for one to
    enter at, so the two edges given to the detector are the two edges of the
    picture itself. A shape touching the bottom edge was already sounding when the
    video started and a shape touching the top edge is still falling when it
    ended — which is what ``clipped`` and ``entering`` already mean (V-16, V-28).
    """
    runs = detector.runs_from_strength(
        roll,
        calibration,
        upper=roll.shape[0],
        roll_top=0,
        guard=0.0,
        settings=settings,
        rejected=rejected,
    )
    mids = {key.midi: key.mid for key in geometry.keys(calibration)}
    white = calibration.white_width

    out: list[VideoNote] = []
    past_the_end = 0
    for run in runs:
        start = geom.seconds(run.y_bottom)
        end = geom.seconds(run.y_top)
        if start >= duration_seconds > 0:
            # The top of the roll holds music that never reached the piano before
            # the video stopped. It was drawn, but it was never played.
            past_the_end += 1
            continue
        out.append(
            VideoNote(
                midi=run.midi,
                start=round(start, 4),
                end=round(max(end, start + 1e-4), 4),
                row_top=run.y_top,
                row_bottom=run.y_bottom,
                width_keys=round(run.width_keys, 3),
                key_distance=round(abs(run.mid - mids[run.midi]) / white, 4) if white else 0.0,
                starts_before=run.clipped,
                ends_after=run.entering,
            )
        )
    out.sort(key=lambda note: (note.start, note.midi))
    return out, past_the_end


def read_notes(
    audio_uuid: str,
    *,
    channel: str = "plate",
    settings: DetectorSettings = DEFAULTS,
    frames: int | None = None,
    compare_connected: bool = True,
    reporter: BaseProgress | None = None,
) -> VideoNotes:
    """Stitch the whole video and read the notes out of it, then store both.

    One pass over the sampled frames and one labelling pass, which is what V-32
    replaces the frame to frame tracker with. What comes back is not the piece:
    it is what will be written into the piece, so it can be looked at and
    corrected first (Task 4.3.1).
    """
    started = time.perf_counter()
    progress = default_reporter(reporter)

    calibration = store.load_calibration(audio_uuid)
    if calibration is None:
        raise stitch.NotMeasured(f"Audio {audio_uuid} has no piano overlay yet")
    metadata = store.load_metadata(audio_uuid)
    duration = metadata.duration_seconds

    roll, geom = stitch.build(
        audio_uuid, channel=channel, settings=settings, frames=frames, reporter=progress
    )

    rejected: list[RejectedRun] = []
    with progress.stage("notes", total=1) as stage:
        found, past_the_end = notes_from_roll(
            roll, calibration, geom, duration, settings=settings, rejected=rejected
        )
        stage.advance(1)

    shapes = 0
    if compare_connected:
        with progress.stage("shapes", total=1) as stage:
            shapes = connected_shapes(roll, settings)
            stage.advance(1)

    lengths = np.array([(note.end - note.start) * 1000.0 for note in found]) if found else None
    widths = np.array([note.width_keys for note in found]) if found else None
    span = max(duration, 1e-6)
    counts: dict[str, int] = {}
    for one in rejected:
        counts[one.reason] = counts.get(one.reason, 0) + 1

    answer = VideoNotes(
        audio_uuid=audio_uuid,
        notes=found,
        duration_seconds=duration,
        rejected=rejected[:MAX_REJECTED],
        report=NoteReport(
            rows=geom.rows,
            width=roll.shape[1],
            megabytes=round(roll.nbytes / 1e6, 1),
            strip_top=geom.strip_top,
            strip_height=geom.strip_height,
            head_rows=geom.head_rows,
            frame_count=frames if frames is not None else metadata.frame_count,
            notes=len(found),
            rejected=counts,
            notes_starting_before=sum(1 for note in found if note.starts_before),
            notes_ending_after=sum(1 for note in found if note.ends_after),
            notes_past_the_end=past_the_end,
            median_width_keys=round(float(np.median(widths)), 3) if widths is not None else 0.0,
            median_length_ms=round(float(np.median(lengths)), 1) if lengths is not None else 0.0,
            worst_key_distance=round(max((n.key_distance for n in found), default=0.0), 4),
            notes_per_second=round(len(found) / span, 3),
            connected_shapes=shapes,
            busy_keys=busy_keys(roll, calibration, settings),
            elapsed_seconds=round(time.perf_counter() - started, 3),
        ),
    )
    store.save_notes(audio_uuid, answer)
    return answer
