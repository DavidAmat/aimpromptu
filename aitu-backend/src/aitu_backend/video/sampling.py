"""Sampling the frames of a video (Task 3.2.1).

ffmpeg writes the sampled frames into `video/frames/` at the sampling
granularity. The video is the source and the frames are a cache (V-01), so
sampling again at another granularity throws the folder away and writes it
again; nothing is lost, because the video is still there.

Two things this step decides, and both are decisions from the frozen list:

* **The sampling granularity is `sampleMs`, never `frameMs`** (V-04). `sampleMs`
  is how often we look at the video; `frameMs` is the column length the sheet is
  read at. They are never derived from each other and no code may use one where
  the other is meant. The default is 100 ms, ten frames per second, which gives a
  rectangle about 33 votes before it reaches the upper line.
* **A frame is written at the working resolution**, 1280 px wide (V-35), so a
  coordinate the user places in the calibration UI is the coordinate the detector
  reads with no scaling anywhere between them. ffmpeg does the resize in the same
  pass, which costs nothing and means no frame on disk is ever at another size.

Measured, on a 3.6 minute video at 1280x720 and 10 frames per second: 2136 frames
taking 118 MB against 9.6 MB for the video, so the frames cost twelve times the
video and 33 MB per minute of music. Sampling took 3.8 s of wall clock. That is
the number behind V-01 — keeping the video and treating the frames as a cache
costs less disk, not more.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from aitu_backend.audio import formats
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.video import VideoMetadata
from aitu_backend.storage import paths
from aitu_backend.video import images, store

#: How often we look at the video, in milliseconds. Ten frames per second: a
#: rectangle is on the screen for over three seconds before it reaches the upper
#: line, so this gives it about thirty independent readings (V-07).
DEFAULT_SAMPLE_MS = 100.0

#: JPEG quality for ffmpeg's `-q:v`, where 2 is best and 31 is worst. 3 is what
#: the spike measured its 118 MB and its thresholds on.
JPEG_QSCALE = 3

#: ffmpeg's progress lines carry `frame= 1234`, which is how many frames it has
#: written so far — the only honest progress this step has.
_FRAME_LINE = re.compile(r"frame=\s*(\d+)")


def sample(
    audio_uuid: str,
    sample_ms: float = DEFAULT_SAMPLE_MS,
    *,
    reporter: BaseProgress | None = None,
) -> VideoMetadata:
    """Write the sampled frames of one video and report what came out.

    Replaces whatever was sampled before, together with the plate and the
    detection built from it: an answer about frames that no longer exist is wrong
    without saying so.
    """
    source = store.require(audio_uuid)
    if not formats.ffmpeg_available():
        raise formats.FfmpegMissing()
    if sample_ms <= 0:
        raise ValueError(f"sampleMs must be positive (got {sample_ms})")

    metadata = store.load_metadata(audio_uuid)
    if metadata.duration_seconds <= 0:
        from aitu_backend.video.download import probe_file

        probed = probe_file(source)
        metadata.width, metadata.height = probed["width"], probed["height"]
        metadata.duration_seconds, metadata.fps = probed["duration"], probed["fps"]
        metadata.size_bytes = source.stat().st_size

    store.clear_frames(audio_uuid)
    folder = paths.video_frames_dir(audio_uuid)
    folder.mkdir(parents=True, exist_ok=True)

    expected = max(1, round(metadata.duration_seconds * 1000.0 / sample_ms))
    progress = default_reporter(reporter)
    with progress.stage("sample", total=expected) as stage:
        seen = 0
        for written in _run_ffmpeg(source, folder, sample_ms):
            if written > seen:
                stage.advance(written - seen, message=f"{written} frames")
                seen = written

    frames = store.frames(audio_uuid)
    if not frames:
        raise formats.ConversionFailed(
            f"ffmpeg wrote no frames out of {source.name}. The file may be audio only."
        )
    width, height = _size_of(frames[0])

    metadata.sample_ms = sample_ms
    metadata.frame_count = len(frames)
    metadata.frame_width, metadata.frame_height = width, height
    metadata.frames_bytes = store.frames_bytes(audio_uuid)
    return store.save_metadata(metadata)


def _run_ffmpeg(source: Path, folder: Path, sample_ms: float):
    """Run ffmpeg and yield how many frames it has written, as it writes them.

    The filter is `fps` then `scale`: pick the frames first and resize only the
    ones that are kept. `-2` on the height keeps the aspect ratio and rounds to an
    even number of rows, which the JPEG encoder needs.
    """
    fps = 1000.0 / sample_ms
    command = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-stats",
        "-y",
        "-i",
        str(source),
        "-vf",
        f"fps={fps:g},scale={images.WORK_WIDTH}:-2",
        "-q:v",
        str(JPEG_QSCALE),
        str(folder / "f%06d.jpg"),
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )
    assert process.stderr is not None
    tail: list[str] = []
    buffer = ""
    # ffmpeg writes both its stats and its errors on stderr, and `-stats` ends
    # each tick with a carriage return rather than a newline — so iterating
    # lines would hand back one enormous line at the end and the progress bar
    # would jump from nothing to done. It is read a character at a time instead
    # and cut on either separator, which is what makes the progress live.
    while True:
        char = process.stderr.read(1)
        if not char:
            break
        if char in "\r\n":
            line, buffer = buffer, ""
        else:
            buffer += char
            continue
        match = _FRAME_LINE.search(line)
        if match:
            yield int(match.group(1))
        elif line.strip():
            tail.append(line.strip())
    if buffer.strip():
        tail.append(buffer.strip())
    process.wait()
    if process.returncode != 0:
        raise formats.ConversionFailed(
            "ffmpeg could not sample the video:\n" + "\n".join(tail[-5:])
        )


def _size_of(path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as handle:
        return handle.width, handle.height
