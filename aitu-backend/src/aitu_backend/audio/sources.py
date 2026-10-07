"""The audio files of a part laid end to end: the axis of the Audio step (implementation 02, plan
section 8.5, **add audio**).

A part of one file needs nothing here: its file is the original, and ``normalized.wav`` is that
file at 16 kHz mono, as since implementation 08. A part of several files (``timeline.sources``)
has no single original, so two derived files stand in for it, both in the part's ``cache/`` folder
and both written again when they are missing:

* ``normalized.wav``: each file's own 16 kHz mono copy (``src-<hash>.wav``), padded with silence to
  a whole number of 10 ms frames and joined. File ``i`` therefore starts exactly at the frame where
  the timeline says it starts, and everything that reads ``normalized.wav`` (the frames of the cuts,
  the waveform, the transcription) works on the axis unchanged.
* ``sources-<key>.flac``: the files decoded at one rate (44.1 kHz, or 48 kHz when a file is above
  it) and the most channels any of them has, each padded or trimmed to its frames, joined, FLAC
  (lossless and sample exact). It is what the Audio step plays and what the joined audio of the
  cuts is cut from. ``<key>`` names the list of files, so adding a file writes a new one.

At each join of two files, 5 ms fade out and in inside the files, as at the join of a cut
(:data:`aitu_backend.audio.frames.FADE_MS`), so the join does not click.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from aitu_backend.audio import formats
from aitu_backend.audio.frames import FADE_MS, FRAME_MS, SAMPLE_RATE, SAMPLES_PER_FRAME, frame_count
from aitu_backend.storage import audio_files, paths
from aitu_backend.storage.bundle import Timeline

__all__ = [
    "LISTEN_PREFIX",
    "clear",
    "ensure_listen",
    "listen_path",
    "measure",
    "source_wav",
    "write_normalized",
]

LISTEN_PREFIX = "sources-"
SOURCE_PREFIX = "src-"

_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def _lock(key: str) -> threading.Lock:
    with _guard:
        return _locks.setdefault(key, threading.Lock())


def _cache(part_id: str) -> Path:
    return paths.part_cache_dir(part_id)


def source_wav(part_id: str, content_hash: str, extension: str) -> Path:
    """The file's own 16 kHz mono copy in the part's cache, written from the stored file when it
    is missing."""
    target = _cache(part_id) / f"{SOURCE_PREFIX}{content_hash}.wav"
    if target.is_file():
        return target
    with _lock(f"{part_id}:{content_hash}"):
        if not target.is_file():
            temporary = target.with_name(f".{target.name}.tmp.wav")
            formats.normalize_to_wav(audio_files.file_path(content_hash, extension), temporary)
            temporary.replace(target)
    return target


def measure(part_id: str, content_hash: str, extension: str) -> int:
    """The length of a stored file in 10 ms frames, from its 16 kHz copy (written now)."""
    _, samples = formats.sample_count(source_wav(part_id, content_hash, extension))
    return frame_count(samples)


def _fade_joins(signal: np.ndarray, starts: list[int], rate: int) -> np.ndarray:
    """5 ms out before and 5 ms in after each sample index of ``starts`` (the joins)."""
    fade = max(1, int(round(rate * FADE_MS / 1000.0)))
    ramp = np.linspace(0.0, 1.0, fade, endpoint=False, dtype=np.float32)
    if signal.ndim == 2:
        ramp = ramp[:, None]
    for at in starts:
        before = signal[max(0, at - fade) : at]
        before *= ramp[: len(before)][::-1]
        after = signal[at : at + fade]
        after *= ramp[: len(after)]
    return signal


def _fit(samples: np.ndarray, length: int) -> np.ndarray:
    """``samples`` padded with silence, or trimmed, to ``length``."""
    if len(samples) >= length:
        return samples[:length]
    pad = [(0, length - len(samples))] + [(0, 0)] * (samples.ndim - 1)
    return np.pad(samples, pad)


def write_normalized(part_id: str, timeline: Timeline, target: Path) -> Path:
    """``normalized.wav`` of a part of several files: each file's 16 kHz copy, padded to its
    frames, joined."""
    pieces: list[np.ndarray] = []
    starts: list[int] = []
    position = 0
    for content_hash, frames in timeline.axis():
        extension = timeline.audio[content_hash].format
        rate, samples = formats.read_wav(source_wav(part_id, content_hash, extension))
        if rate != SAMPLE_RATE:
            raise formats.ConversionFailed(f"src-{content_hash}.wav is {rate} Hz")
        if position:
            starts.append(position)
        length = frames * SAMPLES_PER_FRAME
        pieces.append(_fit(samples, length))
        position += length
    joined = _fade_joins(np.concatenate(pieces).astype(np.float32), starts, SAMPLE_RATE)
    pcm = np.clip(np.round(joined * 32767.0), -32768, 32767).astype(np.int16)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp.wav")
    wavfile.write(temporary, SAMPLE_RATE, pcm)
    temporary.replace(target)
    return target


def _key(timeline: Timeline) -> str:
    body = json.dumps(timeline.axis())
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def listen_path(part_id: str, timeline: Timeline) -> Path:
    return _cache(part_id) / f"{LISTEN_PREFIX}{_key(timeline)}.flac"


def _probe(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0"]
        + ["-show_entries", "stream=sample_rate,channels", "-of", "json", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise formats.ConversionFailed(f"ffprobe could not read {path.name}")
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["sample_rate"]), int(stream["channels"])


def _decode(path: Path, rate: int, channels: int) -> np.ndarray:
    decoded = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path)]
        + ["-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(channels), "-ar", str(rate), "-"],
        capture_output=True,
    )
    if decoded.returncode != 0:
        raise formats.ConversionFailed(f"ffmpeg could not decode {path.name}")
    return np.frombuffer(decoded.stdout, dtype=np.float32).reshape(-1, channels).copy()


def ensure_listen(part_id: str, timeline: Timeline) -> Path:
    """The files of a part of several files joined at one rate, as FLAC, written now if missing.
    Files of another list of sources are deleted."""
    target = listen_path(part_id, timeline)
    with _lock(f"{part_id}:listen"):
        for other in _cache(part_id).glob(f"{LISTEN_PREFIX}*.flac"):
            if other != target:
                other.unlink(missing_ok=True)
        if target.is_file():
            return target
        if not formats.ffmpeg_available():
            raise formats.FfmpegMissing()
        files = [
            (audio_files.file_path(content_hash, timeline.audio[content_hash].format), frames)
            for content_hash, frames in timeline.axis()
        ]
        probes = [_probe(path) for path, _ in files]
        rate = 44_100 if max(found for found, _ in probes) <= 44_100 else 48_000
        channels = max(count for _, count in probes)
        per_frame = rate * FRAME_MS // 1000
        pieces: list[np.ndarray] = []
        starts: list[int] = []
        position = 0
        for path, frames in files:
            if position:
                starts.append(position)
            pieces.append(_fit(_decode(path, rate, channels), frames * per_frame))
            position += frames * per_frame
        joined = _fade_joins(np.concatenate(pieces), starts, rate)
        temporary = target.with_name(f".{target.stem}.tmp.flac")
        encoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y"]
            + ["-f", "f32le", "-ar", str(rate), "-ac", str(channels), "-i", "-"]
            + ["-c:a", "flac", "-sample_fmt", "s16", str(temporary)],
            input=np.ascontiguousarray(joined).tobytes(),
            capture_output=True,
        )
        if encoded.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise formats.ConversionFailed(f"ffmpeg could not write {target.name}")
        temporary.replace(target)
    return target


def clear(part_id: str, *, keep_sources: bool = True) -> None:
    """Delete the joined files of a part (its list of files changed). ``keep_sources`` keeps the
    16 kHz copy of each file, which does not change."""
    cache = _cache(part_id)
    for path in cache.glob(f"{LISTEN_PREFIX}*.flac"):
        path.unlink(missing_ok=True)
    if not keep_sources:
        for path in cache.glob(f"{SOURCE_PREFIX}*.wav"):
            path.unlink(missing_ok=True)
