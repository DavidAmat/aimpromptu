"""Audio format detection, ffmpeg normalization and waveform peaks.

``ffmpeg`` is a documented local prerequisite (see
``context/04-local-development.md``); it is invoked as a subprocess rather than
through a binding, so there is one less wheel to build and the exact command is
visible in logs.

Everything downstream — transcription, waveform drawing, range playback — reads
``normalized.wav``, never the original. Normalizing once on ingest means the
rest of the system never has to care that the user uploaded an m4a.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile

#: Suffixes we accept. Anything else is a 422 at the API edge.
#:
#: ``.webm`` and ``.ogg`` are here for **browser recordings**: Chrome's
#: ``MediaRecorder`` can only produce webm/opus, and the standard answer across
#: recording apps is to accept it and convert server-side rather than fight it
#: in the browser. We already normalize every upload through ffmpeg, which
#: decodes opus natively, so the rest of the system never sees the difference.
SUPPORTED_SUFFIXES = (".mp3", ".aac", ".m4a", ".wav", ".webm", ".ogg")

#: Mono at this rate is what `piano_transcription_inference` expects (Epic 4).
TRANSCRIPTION_SAMPLE_RATE = 16000

#: Default number of buckets the waveform endpoint returns.
DEFAULT_WAVEFORM_POINTS = 1000


class UnsupportedFormat(ValueError):
    """The uploaded suffix is not one we handle."""


class FfmpegMissing(RuntimeError):
    """ffmpeg is not on PATH."""

    def __init__(self) -> None:
        super().__init__(
            "ffmpeg was not found on PATH. It is a local prerequisite — install it "
            "(macOS: `brew install ffmpeg`) and restart the backend."
        )


class ConversionFailed(RuntimeError):
    """ffmpeg ran but returned a non-zero exit code."""


def detect_extension(filename: str) -> str:
    """Extension (no dot, lowercase) of a supported file. Raises otherwise."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(SUPPORTED_SUFFIXES)
        raise UnsupportedFormat(
            f"'{filename}' has an unsupported extension. Supported: {supported}"
        )
    return suffix.lstrip(".")


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def normalize_to_wav(
    source: Path,
    target: Path,
    *,
    sample_rate: int = TRANSCRIPTION_SAMPLE_RATE,
) -> Path:
    """Convert any supported audio to mono 16-bit WAV at ``sample_rate``.

    One conversion on ingest; every later step reads the result.
    """
    if not source.is_file():
        raise FileNotFoundError(f"No audio at {source}")
    if not ffmpeg_available():
        raise FfmpegMissing()

    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-nostdin",
        "-y",  # overwrite: re-ingest should be idempotent
        "-i",
        str(source),
        "-ac",
        "1",  # mono
        "-ar",
        str(sample_rate),
        "-acodec",
        "pcm_s16le",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise ConversionFailed(f"ffmpeg failed converting {source.name}:\n{tail}")
    return target


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    """Load a WAV as ``(sample_rate, float32 samples in [-1, 1])``, mono."""
    sample_rate, samples = wavfile.read(path)
    if samples.ndim > 1:  # Defensive: normalization already forces mono.
        samples = samples.mean(axis=1)
    if np.issubdtype(samples.dtype, np.integer):
        samples = samples.astype(np.float32) / np.iinfo(samples.dtype).max
    else:
        samples = samples.astype(np.float32)
    return int(sample_rate), samples


def duration_seconds(path: Path) -> float:
    """Length of a WAV in seconds."""
    sample_rate, samples = read_wav(path)
    return float(len(samples) / sample_rate)


@dataclass(frozen=True)
class WaveformPeaks:
    """Min/max pairs per bucket — everything a waveform drawing needs.

    Computed backend-side on purpose: the frontend never decodes audio to draw.
    """

    points: int
    min: list[float]
    max: list[float]
    duration_seconds: float
    sample_rate: int

    def to_dict(self) -> dict:
        return {
            "points": self.points,
            "min": self.min,
            "max": self.max,
            "durationSeconds": round(self.duration_seconds, 6),
            "sampleRate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "WaveformPeaks":
        return cls(
            points=int(payload["points"]),
            min=list(payload["min"]),
            max=list(payload["max"]),
            duration_seconds=float(payload["durationSeconds"]),
            sample_rate=int(payload["sampleRate"]),
        )


def compute_peaks(path: Path, points: int = DEFAULT_WAVEFORM_POINTS) -> WaveformPeaks:
    """Downsample a WAV to ``points`` min/max pairs.

    Vectorized: the samples are padded to a multiple of ``points`` and reshaped,
    so the whole thing is two reductions rather than a Python loop over buckets.
    """
    if points < 1:
        raise ValueError("points must be at least 1")

    sample_rate, samples = read_wav(path)
    total = len(samples)
    if total == 0:
        zeros = [0.0] * points
        return WaveformPeaks(points, zeros, zeros, 0.0, sample_rate)

    buckets = min(points, total)
    per_bucket = int(np.ceil(total / buckets))
    padded_length = per_bucket * buckets
    if padded_length > total:
        samples = np.concatenate([samples, np.zeros(padded_length - total, dtype=samples.dtype)])

    reshaped = samples.reshape(buckets, per_bucket)
    minima = np.round(reshaped.min(axis=1), 5).astype(float).tolist()
    maxima = np.round(reshaped.max(axis=1), 5).astype(float).tolist()

    return WaveformPeaks(
        points=buckets,
        min=minima,
        max=maxima,
        duration_seconds=float(total / sample_rate),
        sample_rate=sample_rate,
    )


def slice_wav(source: Path, target: Path, start_seconds: float, end_seconds: float) -> Path:
    """Write the ``[start, end)`` range of a WAV to ``target``.

    Used by range playback and by Epic 6's "transcribe only this range".
    """
    if end_seconds <= start_seconds:
        raise ValueError(
            f"endSeconds must be after startSeconds ({end_seconds} <= {start_seconds})"
        )
    sample_rate, samples = read_wav(source)
    start = max(0, int(start_seconds * sample_rate))
    end = min(len(samples), int(end_seconds * sample_rate))
    if start >= end:
        raise ValueError("The requested range falls outside the audio")

    target.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples[start:end], -1.0, 1.0)
    wavfile.write(target, sample_rate, (clipped * np.iinfo(np.int16).max).astype(np.int16))
    return target
