"""One video on disk: the file, its metadata, its calibration, its frames.

Task 3.1.1 and Task 3.2.1 of `04-synthesia-to-notes`. Everything under
`data/audio/<uuid>/video/` is read and written here and nowhere else, the way
`audio/store.py` owns `data/audio/<uuid>/`.

Two rules from the frozen decisions shape it:

* **The video is the source and the sampled frames are a cache** (V-01). The
  frames, the plate and `frames.jsonl` can all be thrown away and written again;
  the video file and `calibration.json` cannot.
* **The calibration is kept beside the video, never inside `rhythm.json`**
  (V-12). How the notes were read off the screen is a different thing from what
  a reader decided about the sheet.

A sampled frame is addressed by its **index**, counted from zero, and its time is
``index * sampleMs / 1000``. ffmpeg's ``fps`` filter emits its first frame at
t = 0 — measured: a two second clip sampled at 10 frames per second gives exactly
twenty frames — so the index and the time line up with nothing to correct for.
The file on disk keeps ffmpeg's own one-based name so the folder sorts in time
order, and nothing outside this module has to know that.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from aitu_backend.schemas.video import (
    Calibration,
    DetectionReport,
    FrameLine,
    NoteCorrections,
    VideoMeasurement,
    VideoMetadata,
    VideoNotes,
)
from aitu_backend.storage import paths
from aitu_backend.video import images


class VideoNotFound(LookupError):
    """No downloaded video for that piece."""

    def __init__(self, audio_uuid: str) -> None:
        self.audio_uuid = audio_uuid
        super().__init__(f"Audio {audio_uuid} has no downloaded video")


# ------------------------------------------------------------ the file ------


def exists(audio_uuid: str) -> bool:
    """Is there a downloaded video for this piece?"""
    return paths.video_source_path(audio_uuid).is_file()


def require(audio_uuid: str) -> Path:
    """The downloaded video, or :class:`VideoNotFound`."""
    path = paths.video_source_path(audio_uuid)
    if not path.is_file():
        raise VideoNotFound(audio_uuid)
    return path


def uuids() -> list[str]:
    """Every piece that has a downloaded video, sorted."""
    return paths.list_video_uuids()


# -------------------------------------------------------- the metadata ------


def load_metadata(audio_uuid: str) -> VideoMetadata:
    """`video/metadata_video.json`, or an empty record naming the piece."""
    path = paths.video_metadata_path(audio_uuid)
    if not path.exists():
        return VideoMetadata(audio_uuid=audio_uuid)
    return VideoMetadata.model_validate(json.loads(path.read_text()))


def save_metadata(metadata: VideoMetadata) -> VideoMetadata:
    """Write `video/metadata_video.json`."""
    path = paths.video_metadata_path(metadata.audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata.model_dump(by_alias=True), indent=2) + "\n")
    return metadata


def update_metadata(audio_uuid: str, **changes: object) -> VideoMetadata:
    """Change some fields of the metadata and write it back."""
    metadata = load_metadata(audio_uuid)
    for key, value in changes.items():
        setattr(metadata, key, value)
    return save_metadata(metadata)


# ----------------------------------------------------- the calibration ------


def load_calibration(audio_uuid: str) -> Calibration | None:
    """The piano overlay of this video, or `None` if it has not been fitted."""
    path = paths.video_calibration_path(audio_uuid)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return Calibration.model_validate(raw.get("calibration", raw))


def save_calibration(audio_uuid: str, calibration: Calibration) -> Calibration:
    """Write the piano overlay, keeping whatever the motion measured beside it."""
    path = paths.video_calibration_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text()) if path.exists() else {}
    payload = {
        "calibration": calibration.model_dump(by_alias=True),
        "measurement": existing.get("measurement"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return calibration


def load_measurement(audio_uuid: str) -> VideoMeasurement | None:
    """What the motion of the roll said: the scroll speed and the two edges."""
    path = paths.video_calibration_path(audio_uuid)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    measured = raw.get("measurement")
    return VideoMeasurement.model_validate(measured) if measured else None


def save_measurement(audio_uuid: str, measurement: VideoMeasurement) -> VideoMeasurement:
    """Write the measurement beside the calibration it was made against."""
    path = paths.video_calibration_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text()) if path.exists() else {}
    existing["measurement"] = measurement.model_dump(by_alias=True)
    path.write_text(json.dumps(existing, indent=2) + "\n")
    return measurement


# --------------------------------------------------- the sampled frames -----


def frames(audio_uuid: str) -> list[Path]:
    """Every sampled frame on disk, in time order. Index 0 is t = 0."""
    return paths.list_video_frames(audio_uuid)


def frame_count(audio_uuid: str) -> int:
    return len(frames(audio_uuid))


def frame_path(audio_uuid: str, index: int) -> Path:
    """One sampled frame by its index, counted from zero."""
    found = frames(audio_uuid)
    if not 0 <= index < len(found):
        raise IndexError(f"frame {index} is outside the {len(found)} sampled frames")
    return found[index]


def frame_time(index: int, sample_ms: float) -> float:
    """The time of one sampled frame, in seconds from the start of the video."""
    return index * sample_ms / 1000.0


def load_frame(audio_uuid: str, index: int) -> np.ndarray:
    """One sampled frame as float RGB at the working resolution."""
    return images.load_rgb(frame_path(audio_uuid, index))


def clear_frames(audio_uuid: str) -> None:
    """Throw the sampled frames away, with the plate and the detection with them.

    Sampling again at another granularity replaces the folder; the video is still
    there, so nothing is lost (V-01). The plate and `frames.jsonl` are answers
    about frames that no longer exist, so they go too — a stale plate is worse
    than no plate, because it is wrong without saying so.
    """
    shutil.rmtree(paths.video_frames_dir(audio_uuid), ignore_errors=True)
    shutil.rmtree(paths.video_detection_dir(audio_uuid), ignore_errors=True)
    paths.video_plate_path(audio_uuid).unlink(missing_ok=True)
    paths.video_frames_jsonl_path(audio_uuid).unlink(missing_ok=True)
    paths.video_detection_report_path(audio_uuid).unlink(missing_ok=True)
    # `notes.json` is derived too. `corrections.json` is not: a reading made by a
    # person cannot be reproduced, so it survives the frames it was made against.
    paths.video_notes_path(audio_uuid).unlink(missing_ok=True)


def frames_bytes(audio_uuid: str) -> int:
    """How much disk the sampled frames take. The number V-01 rests on."""
    return sum(path.stat().st_size for path in frames(audio_uuid))


# ---------------------------------------------------------- the reading -----


def save_frame_lines(audio_uuid: str, lines: list[FrameLine]) -> Path:
    """Write `frames.jsonl`: one line per sampled frame, in time order."""
    path = paths.video_frames_jsonl_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for line in lines:
            handle.write(json.dumps(line.model_dump(by_alias=True)) + "\n")
    return path


def load_frame_lines(audio_uuid: str) -> list[FrameLine]:
    """Read `frames.jsonl` back. Empty when the detector has not run."""
    path = paths.video_frames_jsonl_path(audio_uuid)
    if not path.exists():
        return []
    return [
        FrameLine.model_validate(json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def save_report(audio_uuid: str, report: DetectionReport) -> DetectionReport:
    """Write what the last whole-video run did, so a change can be compared."""
    path = paths.video_detection_report_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(by_alias=True), indent=2) + "\n")
    return report


def load_report(audio_uuid: str) -> DetectionReport | None:
    """What the last whole-video run did, or `None` if it has not run."""
    path = paths.video_detection_report_path(audio_uuid)
    if not path.exists():
        return None
    return DetectionReport.model_validate(json.loads(path.read_text()))


# ------------------------------------------------------------- the notes ----


def save_notes(audio_uuid: str, notes: VideoNotes) -> Path:
    """Write `video/notes.json` — what the stitched roll read (V-32).

    Derived, like `frames.jsonl`: it is written again whenever the video is read
    again. It is not the piece.
    """
    path = paths.video_notes_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes.model_dump(by_alias=True), indent=2) + "\n")
    return path


def load_notes(audio_uuid: str) -> VideoNotes | None:
    """What the stitched roll read, or `None` when it has not been read."""
    path = paths.video_notes_path(audio_uuid)
    if not path.exists():
        return None
    return VideoNotes.model_validate(json.loads(path.read_text()))


def load_corrections(audio_uuid: str) -> NoteCorrections:
    """The notes a person took off or put on. Empty when nobody has touched it."""
    path = paths.video_corrections_path(audio_uuid)
    if not path.exists():
        return NoteCorrections()
    return NoteCorrections.model_validate(json.loads(path.read_text()))


def save_corrections(audio_uuid: str, corrections: NoteCorrections) -> NoteCorrections:
    """Write what a person changed. It survives a re-stitch (V-12)."""
    path = paths.video_corrections_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(corrections.model_dump(by_alias=True), indent=2) + "\n")
    return corrections


# ------------------------------------------------------------- the plate ----


def save_plate(audio_uuid: str, plate: np.ndarray) -> Path:
    """Cache the background plate, so every worker process reads one file."""
    path = paths.video_plate_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, plate.astype(np.float32))
    return path


def load_plate(audio_uuid: str) -> np.ndarray | None:
    """The cached background plate, or `None` if it has not been built."""
    path = paths.video_plate_path(audio_uuid)
    if not path.exists():
        return None
    return np.load(path)
