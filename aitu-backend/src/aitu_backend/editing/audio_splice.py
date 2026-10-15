"""A pitch-preserving stretch of a recording: a take played faster or slower into a song (Record in
Sheet, implementation 02, Phase 9).

``ffmpeg atempo`` does the stretch. If the factor is outside one pass, filters are chained. The
splice of a stretched take into ``normalized.wav`` (Epics 11 and 13) was removed in Phase 9: a take
goes into the part's audio timeline as a file of its own (:mod:`aitu_backend.editing.passages`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aitu_backend.audio import formats
from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing

#: One ``atempo`` pass is documented as 0.5–2.0. Newer ffmpeg allows more; stay in this band.
ATEMPO_MIN = 0.5
ATEMPO_MAX = 2.0


def atempo_chain(rate: float) -> list[str]:
    """Split ``rate`` into ``atempo`` stages, each inside 0.5–2.0.

    ``rate`` is how fast to play the take: 2.0 fits a 6 s take into a 3 s window.
    """
    if rate <= 0:
        raise ValueError(f"atempo rate must be positive, got {rate}")
    stages: list[float] = []
    remaining = float(rate)
    while remaining > ATEMPO_MAX + 1e-9:
        stages.append(ATEMPO_MAX)
        remaining /= ATEMPO_MAX
    while remaining < ATEMPO_MIN - 1e-9:
        stages.append(ATEMPO_MIN)
        remaining /= ATEMPO_MIN
    stages.append(remaining)
    return [f"atempo={stage:.6f}".rstrip("0").rstrip(".") for stage in stages]


def stretch_to_length(
    source: Path, target: Path, source_seconds: float, target_seconds: float
) -> Path:
    """Write ``source`` stretched (or compressed) to ``target_seconds``, pitch preserved."""
    if source_seconds <= 0 or target_seconds <= 0:
        raise ValueError("Both lengths must be positive to stretch audio")
    rate = source_seconds / target_seconds
    return stretch_by_rate(source, target, rate)


def stretch_by_rate(source: Path, target: Path, rate: float, *, keep_format: bool = False) -> Path:
    """Play ``source`` at ``rate`` times its original speed, pitch preserved.

    The engine's 16 kHz mono by default; with ``keep_format`` the source's own rate and channels (a
    take going into a song, which is played as it was recorded)."""
    if abs(rate - 1.0) < 1e-6:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target
    if not formats.ffmpeg_available():
        raise FfmpegMissing()
    filters = ",".join(atempo_chain(rate))
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-filter:a",
        filters,
        *([] if keep_format else ["-ac", "1", "-ar", str(formats.TRANSCRIPTION_SAMPLE_RATE)]),
        "-acodec",
        "pcm_s16le",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise ConversionFailed(f"ffmpeg atempo failed on {source.name}:\n{tail}")
    return target
