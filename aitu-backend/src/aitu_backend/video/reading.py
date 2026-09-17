"""Reading a whole video: the plate, then every sampled frame (Task 3.5.1).

The background plate once (V-29), then the detector of Story 2.3 over every
sampled frame, then the momentum rule, then the frame window rule, and out comes
`frames.jsonl` — one line per sampled frame, the simplified notation the prompt
asks for. Phase 4 turns that into the piece; nothing here knows what
`events.json` is (V-02).

Three things this module is the first to do, and each of them is a decision from
the frozen list arriving in the app for the first time:

* **The momentum rule runs here** (V-33, V-34). A screenshot has no neighbouring
  frame to ask, so Phase 2 could only port and unit test the rule. A video has
  two neighbours for every frame, so the rule finally refuses what it was written
  to refuse: a song title, a watermark, an octave guide line and decorative
  scrollwork all look like rectangles to a detector that sees one picture, and
  none of them falls.
* **The offset line is not a free parameter** (V-25). It is the measured scroll
  speed times the sampling granularity, and nothing else. Setting it wider
  reports the same onset in five consecutive frames, which took the onset rate
  from 8.6 to 29.9 per second on a real piece.
* **Frame to frame agreement is the score** (V-31). A rectangle falls by exactly
  the scroll speed between one sampled frame and the next, so a run at rows y0 to
  y1 must reappear at y0+s to y1+s with the same height. That needs no labelling,
  it runs over a whole video, and it is what says whether a threshold change
  helped. Runs that are supposed to change shape are left out: one being cut by
  the upper line, and one still coming into view at the roll top.

**The lanes are independent** (V-13), and so are the frames, so the pixel work is
spread over worker processes. The plate is written to disk once and each worker
reads that one file rather than being handed eleven megabytes down a pipe.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np

from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.video import (
    Calibration,
    DetectedRun,
    DetectionReport,
    FrameLine,
    VideoMeasurement,
)
from aitu_backend.video import (
    detector,
    momentum,
    motion,
    plate as plate_module,
    store,
)
from aitu_backend.video.detector import DetectorSettings

#: How many frames one worker process reads before answering. Big enough that the
#: cost of sending the answer back is small beside the reading, small enough that
#: the progress bar moves.
CHUNK = 12


class NotSampled(RuntimeError):
    """There are no sampled frames to read."""


class NotCalibrated(RuntimeError):
    """There is no piano overlay, so there is nowhere to look."""


@dataclass(frozen=True)
class _Job:
    """What one worker process needs. Everything in it is picklable."""

    audio_uuid: str
    calibration: dict
    channel: str
    settings: DetectorSettings


def _plate_chunk(
    audio_uuid: str, upper: int | None, picks: list[int]
) -> list[plate_module.PlateSample]:
    """One worker's share of the plate: each picked frame with its neighbours."""
    count = store.frame_count(audio_uuid)
    out: list[plate_module.PlateSample] = []
    for index in picks:
        lo = max(0, index - plate_module.PLATE_NEIGHBOURS)
        hi = min(count - 1, index + plate_module.PLATE_NEIGHBOURS)
        window = [store.load_frame(audio_uuid, i) for i in range(lo, hi + 1)]
        out.append(plate_module.sample(window, upper, centre=index - lo))
    return out


def build_plate(
    audio_uuid: str,
    *,
    frames: int = plate_module.PLATE_FRAMES,
    workers: int | None = None,
    reporter: BaseProgress | None = None,
) -> np.ndarray:
    """The median of what stands still, over frames spread over the video (V-44).

    Spread over the whole video on purpose: a hundred and fifty frames taken from
    one passage are pictures of the same notes, and what has to disappear is what
    is in every frame of the *piece*. Each pick is read with its two neighbours
    either side, which is what says whether a pixel stood still, so the pass
    reads five frames a pick and is spread over worker processes like the rest.
    """
    paths = store.frames(audio_uuid)
    if not paths:
        raise NotSampled(f"Audio {audio_uuid} has no sampled frames")
    calibration = store.load_calibration(audio_uuid)
    upper = int(round(calibration.upper_line)) if calibration else None
    picks = sorted(
        {int(x) for x in np.linspace(0, len(paths) - 1, min(frames, len(paths))).round()}
    )
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    chunks = [picks[a : a + 12] for a in range(0, len(picks), 12)]

    progress = default_reporter(reporter)
    samples: list[plate_module.PlateSample] = []
    with progress.stage("plate", total=len(picks)) as stage:
        if workers == 1:
            for chunk in chunks:
                samples.extend(_plate_chunk(audio_uuid, upper, chunk))
                stage.advance(len(chunk))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                answers = pool.map(
                    _plate_chunk, [audio_uuid] * len(chunks), [upper] * len(chunks), chunks
                )
                for chunk, answer in zip(chunks, answers):
                    samples.extend(answer)
                    stage.advance(len(chunk))
    built = plate_module.build_plate(samples)
    store.save_plate(audio_uuid, built)
    return built


def _read_chunk(job: _Job, indices: list[int]) -> list[list[dict]]:
    """One worker's share: the runs of each of these frames.

    Runs, not verdicts. The momentum rule needs the frames either side of this
    one and the window rule needs the momentum rule, so both are applied in the
    parent where every frame's runs are in one place. What crosses the process
    boundary is therefore the pixel work and nothing else, which is the whole of
    the cost.
    """
    calibration = Calibration.model_validate(job.calibration)
    plate = store.load_plate(job.audio_uuid)
    out: list[list[dict]] = []
    for index in indices:
        image = store.load_frame(job.audio_uuid, index)
        runs = detector.find_runs(
            image, calibration, plate=plate, channel=job.channel, settings=job.settings
        )
        out.append([run.model_dump() for run in runs])
    return out


def measure_video(
    audio_uuid: str,
    *,
    workers: int | None = None,
    reporter: BaseProgress | None = None,
) -> VideoMeasurement:
    """What the motion of the roll says: the scroll speed and the two edges.

    The scroll speed is the rectangles' own answer (V-06, V-45): every sampled
    frame is read for its runs — the same pixel work the reading does, spread over
    the same worker processes — and every run is followed into the next frame.
    The bounds of the roll are then read off the plate difference (V-28).
    """
    calibration = store.load_calibration(audio_uuid)
    if calibration is None:
        raise NotCalibrated(f"Audio {audio_uuid} has no piano overlay yet")
    count = store.frame_count(audio_uuid)
    if count < 2:
        raise NotSampled(f"Audio {audio_uuid} has {count} sampled frames; a speed needs two")

    progress = default_reporter(reporter)
    plate = store.load_plate(audio_uuid)
    if plate is None:
        plate = build_plate(audio_uuid, workers=workers, reporter=progress)

    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    per_frame = _runs_of_every_frame(audio_uuid, calibration, workers, progress, stage="follow")
    metadata = store.load_metadata(audio_uuid)
    measurement = motion.measure(
        lambda index: store.load_frame(audio_uuid, index),
        per_frame,
        calibration.upper_line,
        metadata.sample_ms or 100.0,
        plate=plate,
    )
    store.save_measurement(audio_uuid, measurement)
    if measurement.scroll_speed.px_per_frame > 0:
        calibration.roll_top = measurement.roll_top
        calibration.guard_band = measurement.guard_band
        store.save_calibration(audio_uuid, calibration)
    return measurement


def _runs_of_every_frame(
    audio_uuid: str,
    calibration: Calibration,
    workers: int,
    progress: BaseProgress,
    *,
    stage: str,
    channel: str = "plate",
    settings: DetectorSettings = detector.DEFAULTS,
) -> list[list[DetectedRun]]:
    """The runs of every sampled frame, read across worker processes."""
    count = store.frame_count(audio_uuid)
    job = _Job(
        audio_uuid=audio_uuid,
        calibration=calibration.model_dump(by_alias=True),
        channel=channel,
        settings=settings,
    )
    chunks = [list(range(a, min(a + CHUNK, count))) for a in range(0, count, CHUNK)]
    per_frame: list[list[DetectedRun]] = []
    with progress.stage(stage, total=count) as step:
        if workers == 1:
            for chunk in chunks:
                for raw in _read_chunk(job, chunk):
                    per_frame.append([DetectedRun.model_validate(one) for one in raw])
                step.advance(len(chunk))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for chunk, answer in zip(
                    chunks, pool.map(_read_chunk, [job] * len(chunks), chunks)
                ):
                    for raw in answer:
                        per_frame.append([DetectedRun.model_validate(one) for one in raw])
                    step.advance(len(chunk))
    return per_frame


def agreement(per_frame: list[list[DetectedRun]], travel: float) -> float:
    """Frame to frame agreement (V-31): the score when there is no ground truth.

    A run at rows y0 to y1 must reappear one travel lower in the next sampled
    frame with the same height. A run that does not is a run the detector cut two
    ways on two pictures of the same rectangle. Runs that are supposed to change
    shape are left out of the count.
    """
    asked = 0
    agreed = 0
    for before, after in zip(per_frame, per_frame[1:]):
        candidates = [run for run in before if not run.clipped and not run.entering]
        if not candidates:
            continue
        links, _ = momentum.link(candidates, after, +travel)
        asked += len(candidates)
        agreed += sum(1 for link in links if link is not None)
    return agreed / asked if asked else 0.0


def read_video(
    audio_uuid: str,
    *,
    offset_px: float | None = None,
    travel: float | None = None,
    channel: str = "plate",
    settings: DetectorSettings = detector.DEFAULTS,
    workers: int | None = None,
    reporter: BaseProgress | None = None,
) -> DetectionReport:
    """Read every sampled frame and write `frames.jsonl`.

    ``offset_px`` and ``travel`` both default to the measured scroll speed, which
    is what V-25 says they are: the window of one sampled frame is exactly how far
    the roll falls in one sampled frame, and so is the travel the momentum rule
    asks about.
    """
    calibration = store.load_calibration(audio_uuid)
    if calibration is None:
        raise NotCalibrated(f"Audio {audio_uuid} has no piano overlay yet")
    count = store.frame_count(audio_uuid)
    if count == 0:
        raise NotSampled(f"Audio {audio_uuid} has no sampled frames")

    metadata = store.load_metadata(audio_uuid)
    measurement = store.load_measurement(audio_uuid)
    if travel is None or offset_px is None:
        if measurement is None or measurement.scroll_speed.px_per_frame <= 0:
            raise NotCalibrated(
                f"Audio {audio_uuid} has no measured scroll speed. On a video the offset line "
                "is the measured speed times the sampling granularity and nothing else (V-25)."
            )
        travel = travel if travel is not None else measurement.scroll_speed.px_per_frame
        offset_px = offset_px if offset_px is not None else measurement.scroll_speed.px_per_frame

    progress = default_reporter(reporter)
    started = time.perf_counter()

    if store.load_plate(audio_uuid) is None:
        build_plate(audio_uuid, workers=workers, reporter=progress)

    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    per_frame = _runs_of_every_frame(
        audio_uuid,
        calibration,
        workers,
        progress,
        stage="detect",
        channel=channel,
        settings=settings,
    )

    lines: list[FrameLine] = []
    found = refused_count = onset_count = sustain_count = 0
    with progress.stage("window", total=count) as stage:
        empty: list[DetectedRun] = []
        for index, runs in enumerate(per_frame):
            before = per_frame[index - 1] if index > 0 else empty
            after = per_frame[index + 1] if index + 1 < count else empty
            kept, refused = momentum.apply(runs, before, travel, after, travel)
            onsets, sustains = detector.window_rule(
                kept, int(round(calibration.upper_line)), offset_px
            )
            found += len(kept)
            refused_count += len(refused)
            onset_count += len(onsets)
            sustain_count += len(sustains)
            lines.append(
                FrameLine(
                    t=round(store.frame_time(index, metadata.sample_ms), 3),
                    onsets=onsets,
                    sustains=sustains,
                )
            )
            stage.advance(1)

    store.save_frame_lines(audio_uuid, lines)
    seconds = store.frame_time(count, metadata.sample_ms)
    return store.save_report(
        audio_uuid,
        DetectionReport(
            frame_count=count,
            runs_found=found,
            runs_refused=refused_count,
            onsets=onset_count,
            sustains=sustain_count,
            onsets_per_second=onset_count / seconds if seconds else 0.0,
            agreement=agreement(per_frame, travel),
            elapsed_seconds=time.perf_counter() - started,
            workers=workers,
        ),
    )


def detect_frame(
    audio_uuid: str,
    index: int,
    *,
    offset_px: float | None = None,
    travel: float | None = None,
    channel: str = "plate",
    settings: DetectorSettings = detector.DEFAULTS,
):
    """Read one sampled frame, with its two neighbours, for the screen to draw.

    The detection tab steps through the frames with the rectangles drawn on top,
    and a disagreement has to be something you can look at rather than something
    you have to imagine. It asks both neighbours because the momentum rule does
    (V-33): a rectangle at the top of the roll has no frame before it that holds
    it, and the frame after it answers just as well.
    """
    from aitu_backend.schemas.video import Detection

    calibration = store.load_calibration(audio_uuid)
    if calibration is None:
        raise NotCalibrated(f"Audio {audio_uuid} has no piano overlay yet")
    count = store.frame_count(audio_uuid)
    if not 0 <= index < count:
        raise IndexError(f"frame {index} is outside the {count} sampled frames")

    measurement = store.load_measurement(audio_uuid)
    measured = measurement.scroll_speed.px_per_frame if measurement else 0.0
    travel = travel if travel is not None else measured
    offset_px = offset_px if offset_px is not None else measured
    if offset_px <= 0:
        # Before the speed is measured the window is unknown, so the screen is
        # shown the rectangles and no verdict rather than a guessed one.
        offset_px = 0.0

    started = time.perf_counter()
    plate = store.load_plate(audio_uuid)
    here = detector.find_runs(
        store.load_frame(audio_uuid, index),
        calibration,
        plate=plate,
        channel=channel,
        settings=settings,
    )
    neighbours = []
    for other in (index - 1, index + 1):
        if 0 <= other < count and travel > 0:
            neighbours.append(
                detector.find_runs(
                    store.load_frame(audio_uuid, other),
                    calibration,
                    plate=plate,
                    channel=channel,
                    settings=settings,
                )
            )
        else:
            neighbours.append([])

    kept, refused = momentum.apply(here, neighbours[0], travel, neighbours[1], travel)
    onsets, sustains = detector.window_rule(kept, int(round(calibration.upper_line)), offset_px)
    detector.window_rule(refused, int(round(calibration.upper_line)), offset_px)
    return Detection(
        slug=f"{audio_uuid}:{index}",
        offset_px=offset_px,
        onsets=onsets,
        sustains=sustains,
        runs=kept,
        refused=refused,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )
