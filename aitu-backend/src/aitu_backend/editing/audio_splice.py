"""Pitch-preserving stretch and a splice of that stretch back into the recording.

``ffmpeg atempo`` does the stretch. If the factor is outside one pass, filters are chained.
A failure here must not fail the edit: the sheet still changes, and the window is marked as
audio that no longer matches.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

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


def stretch_by_rate(source: Path, target: Path, rate: float) -> Path:
    """Play ``source`` at ``rate`` times its original speed, pitch preserved."""
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
        "-ac",
        "1",
        "-ar",
        str(formats.TRANSCRIPTION_SAMPLE_RATE),
        "-acodec",
        "pcm_s16le",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise ConversionFailed(f"ffmpeg atempo failed on {source.name}:\n{tail}")
    return target


def splice_wav(
    source: Path,
    replacement: Path,
    target: Path,
    start_seconds: float,
    end_seconds: float,
) -> Path:
    """Overwrite ``[start, end)`` of ``source`` with ``replacement``, written to ``target``."""
    sample_rate, samples = formats.read_wav(source)
    _, patch = formats.read_wav(replacement)
    start = max(0, int(round(start_seconds * sample_rate)))
    end = min(len(samples), int(round(end_seconds * sample_rate)))
    if start >= end:
        raise ValueError("The requested range falls outside the audio")
    window = end - start
    if len(patch) < window:
        patch = np.concatenate([patch, np.zeros(window - len(patch), dtype=patch.dtype)])
    elif len(patch) > window:
        patch = patch[:window]
    spliced = samples.copy()
    spliced[start:end] = patch
    target.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(spliced, -1.0, 1.0)
    wavfile.write(target, sample_rate, (clipped * np.iinfo(np.int16).max).astype(np.int16))
    return target


def _samples_or_silence(path: Path, sample_rate: int) -> tuple[int, np.ndarray]:
    """The audio at ``path``, or nothing at all when a piece has no recording yet.

    A composed piece starts with no audio file: its first passage is what creates one. Returning
    an empty array here is what lets the same insertion code serve both the first passage and the
    fiftieth.
    """
    if not path.is_file():
        return sample_rate, np.zeros(0, dtype=np.float32)
    return formats.read_wav(path)


def insert_wav(
    source: Path,
    insertion: Path,
    target: Path,
    at_seconds: float,
    length_seconds: float,
    *,
    keep_tail: bool,
) -> Path:
    """Open ``source`` at ``at_seconds`` and write ``insertion`` into the gap (Epic 13).

    The twin of :func:`splice_wav`, which overwrites a stretch and keeps the recording the length
    it was. This one makes it longer, which is the whole difference between replacing a passage and
    composing one.

    ``keep_tail`` is the placement: ``False`` appends — whatever was after the moment, which for an
    append is only trailing silence, is left where it is and the passage is written over it;
    ``True`` inserts — everything after the moment is pushed later by ``length_seconds``, so the
    audio moves by exactly what the notes moved by.

    A moment past the end of the recording is padded with silence up to it, which is what an append
    with a gap asks for.
    """
    sample_rate, samples = _samples_or_silence(source, formats.TRANSCRIPTION_SAMPLE_RATE)
    _, patch = _samples_or_silence(insertion, sample_rate)

    width = max(0, int(round(length_seconds * sample_rate)))
    if width == 0:
        raise ValueError("A passage of no length cannot be written into the recording")
    if len(patch) < width:
        patch = np.concatenate([patch, np.zeros(width - len(patch), dtype=np.float32)])
    else:
        patch = patch[:width]

    at = max(0, int(round(at_seconds * sample_rate)))
    if at > len(samples):
        samples = np.concatenate([samples, np.zeros(at - len(samples), dtype=np.float32)])
    head = samples[:at]
    tail = samples[at:] if keep_tail else samples[at + width :]

    grown = np.concatenate([head, patch, tail]) if len(tail) else np.concatenate([head, patch])
    target.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(grown, -1.0, 1.0)
    wavfile.write(target, sample_rate, (clipped * np.iinfo(np.int16).max).astype(np.int16))
    return target
