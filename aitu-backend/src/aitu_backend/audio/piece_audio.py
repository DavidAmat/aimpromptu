"""The audio of the piece: the original with the cuts removed, written as files every player plays.

Implementation 08 (plan section 9.2) first kept the cuts as ranges only: the audio file never
changed, and the notes lived in the time of the piece. Every player still played the untouched
file, so on a cut piece the playhead and the audio drifted apart by the length of the cuts before
it. The user's rule (2026-09-29): **once the cuts are saved, the edited audio is the audio of the
piece.** The untouched original stays on disk, unused, so the Audio tab can still show a cut and
restore it.

So when a piece has cuts, two files are written beside the original, named with the
``audioRevision`` they were made for:

* ``piece-r<N>.flac``: the original file, decoded at its own sample rate and channels, with the kept
  frames joined. FLAC because it is lossless and sample exact: an MP3 would add the encoder's delay
  at the start and move every note by about 25 ms.
* ``piece-r<N>.wav``: ``normalized.wav`` (16 kHz mono) with the kept frames joined, for the views
  that play the engine's audio, and for the waveform of the piece.

Both are joined exactly as the engine's input is (:func:`aitu_backend.audio.frames.join_kept`): at
each join a 5 ms fade out and in inside the kept samples, and a frame ``f`` of the piece is
``f * rate / 100`` samples in, so they line up with the notes to the sample.

The files are made when the cuts are saved (``PUT /audio/{uuid}/cuts``) and, if one is missing,
when it is first asked for. Files of another revision are deleted, and both go away when the cuts
are removed.

**A piece without cuts plays a lossless copy of a compressed original** (:func:`listen_copy`,
implementation 03, after Phase 6). An ``<audio>`` element jumps inside an MP3 by guessing the byte
of a time: a file of variable bitrate has only a table of 100 points (the Xing header), so a jump
lands up to half a second away from the time it reports, and the music no longer matches the notes
and the cursor until the next jump (measured in Chromium on 7 Years: 30 to 576 ms late depending
on the place, the same at every jump to that place; a FLAC copy lands where asked every time). So
a stored file that is not WAV or FLAC is played as ``listen-<its name>.flac``: decoded by the same
ffmpeg that made the engine's audio, at its own rate and channels, made the first time it is played
and kept in the part's cache.
"""

from __future__ import annotations

import json
import subprocess
import threading
from collections.abc import Iterable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from aitu_backend.audio import formats, sources, store
from aitu_backend.audio.frames import FADE_MS, FRAME_MS, FrameTable, frame_count, join_kept
from aitu_backend.audio.store import StoredAudio

__all__ = ["PieceAudio", "ensure", "join_samples", "listen_copy", "write_joined"]

_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _lock(audio_uuid: str) -> threading.Lock:
    with _locks_lock:
        return _locks.setdefault(audio_uuid, threading.Lock())


@contextmanager
def held(part_ids: Iterable[str]) -> Iterator[None]:
    """No joined audio of these parts is being written while this holds: a write in progress
    finishes first, and the next waits. For a move of the folder the files are written in (**Save
    to library**): a request that plays the piece meanwhile would write into the folder as it goes.
    The locks are taken in the order :func:`ensure` takes them (the part's, then its sources')."""
    with ExitStack() as stack:
        for part_id in part_ids:
            stack.enter_context(_lock(part_id))
            stack.enter_context(sources.writing(part_id))
        yield


@dataclass(frozen=True)
class PieceAudio:
    """The two files of a piece with cuts."""

    listen: Path
    normalized: Path
    table: FrameTable

    @property
    def duration_seconds(self) -> float:
        return self.table.piece_frames * FRAME_MS / 1000.0


def _paths(entry: StoredAudio) -> tuple[Path, Path]:
    revision = entry.metadata.audio_revision
    return (
        entry.directory / f"piece-r{revision}.flac",
        entry.directory / f"piece-r{revision}.wav",
    )


def _remove_others(entry: StoredAudio, keep: tuple[Path, ...]) -> None:
    for path in entry.directory.glob("piece-r*.*"):
        if path not in keep:
            path.unlink(missing_ok=True)


def join_samples(samples: np.ndarray, rate: int, table: FrameTable) -> np.ndarray:
    """The kept frames of ``samples`` (``(n,)`` or ``(n, channels)`` at ``rate``) joined end to end,
    with the same fades as :func:`~aitu_backend.audio.frames.join_kept`."""
    signal = np.asarray(samples, dtype=np.float32)
    if table.is_whole:
        return signal
    per_frame = rate * FRAME_MS / 1000.0
    fade = max(1, int(round(rate * FADE_MS / 1000.0)))
    ramp = np.linspace(0.0, 1.0, fade, endpoint=False, dtype=np.float32)
    if signal.ndim == 2:
        ramp = ramp[:, None]
    parts = []
    last = len(table.original_start) - 1
    for row, (start, length) in enumerate(
        zip(table.original_start.tolist(), table.length.tolist())
    ):
        first = int(round(start * per_frame))
        end = int(round((start + length) * per_frame))
        part = signal[first:end].copy()
        size = min(fade, len(part))
        if row > 0 and size:
            part[:size] *= ramp[:size]
        if row < last and size:
            part[-size:] *= ramp[:size][::-1]
        parts.append(part)
    if not parts:
        return signal[:0]
    return np.concatenate(parts)


def _probe(path: Path) -> tuple[int, int]:
    """``(sample rate, channels)`` of the first audio stream."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise formats.ConversionFailed(
            f"ffprobe could not read {path.name}: {result.stderr[-300:]}"
        )
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["sample_rate"]), int(stream["channels"])


def write_joined(original: Path, target: Path, table: FrameTable) -> None:
    """Decode ``original`` at its own rate and channels, join the kept frames, encode as FLAC."""
    rate, channels = _probe(original)
    decoded = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(original)]
        + ["-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(channels), "-ar", str(rate), "-"],
        capture_output=True,
    )
    if decoded.returncode != 0:
        raise formats.ConversionFailed(f"ffmpeg could not decode {original.name}")
    samples = np.frombuffer(decoded.stdout, dtype=np.float32).reshape(-1, channels)
    joined = join_samples(samples, rate, table)
    temporary = target.with_suffix(".tmp.flac")
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


def _write_normalized(normalized: Path, target: Path, table: FrameTable) -> None:
    rate, samples = formats.read_wav(normalized)
    joined = join_kept(samples, table)
    pcm = np.clip(np.round(joined * 32767.0), -32768, 32767).astype(np.int16)
    temporary = target.with_suffix(".tmp.wav")
    wavfile.write(temporary, rate, pcm)
    temporary.replace(target)


def ensure(audio_uuid: str) -> PieceAudio | None:
    """The audio of the piece for its current cuts, made now if it is missing. ``None`` when the
    piece has no cut: then the original is the audio of the piece, and old files are removed."""
    with _lock(audio_uuid):
        entry = store.get(audio_uuid)
        if not entry.metadata.cuts or not entry.has_normalized():
            _remove_others(entry, ())
            return None
        listen, normalized = _paths(entry)
        _remove_others(entry, (listen, normalized))
        _, samples = formats.sample_count(entry.normalized_path)
        table = FrameTable.from_cuts(entry.metadata.cuts, frame_count(samples))
        if not normalized.is_file():
            _write_normalized(entry.normalized_path, normalized, table)
        if not listen.is_file():
            original = store.original_file(entry) if formats.ffmpeg_available() else None
            if original is None:
                # Nothing better to offer than the engine's own audio of the piece.
                listen = normalized
            else:
                write_joined(original, listen, table)
        return PieceAudio(listen, normalized, table)


#: Stored formats an audio element jumps in exactly: PCM (a time is a byte) and FLAC (its frames carry their sample).
SEEK_EXACT = frozenset({"wav", "flac"})


def listen_copy(audio_uuid: str) -> Path | None:
    """The FLAC that plays a piece without cuts whose stored file is compressed (an MP3, an M4A, a recording), made
    now if it is missing; ``None`` when the stored file plays as it is (WAV, FLAC, a part of several files, which plays
    their joined FLAC) or cannot be converted. See the module's last paragraph."""
    with _lock(audio_uuid):
        entry = store.get(audio_uuid)
        original = entry.original_path
        if (
            entry.joined
            or original is None
            or not original.is_file()
            or original.suffix.lstrip(".").lower() in SEEK_EXACT
            or not formats.ffmpeg_available()
        ):
            return None
        target = entry.directory / f"listen-{original.stem}.flac"
        for old in entry.directory.glob("listen-*.flac"):
            if old != target:
                old.unlink(missing_ok=True)
        if target.is_file():
            return target
        entry.directory.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp.flac")
        encoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(original), "-vn"]
            + ["-c:a", "flac", "-sample_fmt", "s16", str(temporary)],
            capture_output=True,
        )
        if encoded.returncode != 0:
            temporary.unlink(missing_ok=True)
            return None
        temporary.replace(target)
        return target
