"""One ingest path for every source: upload, recording, YouTube.

Whatever the origin, an audio arrives the same way — bytes plus a filename plus
a source label — so uploads, browser recordings and yt-dlp downloads all land in
the store with identical structure and identical metadata. Later epics only have
to know about :func:`ingest_file`.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from aitu_backend.audio import formats, store
from aitu_backend.audio.store import StoredAudio
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource


def ingest_file(
    stream: BinaryIO,
    filename: str,
    source: AudioSource | str,
    *,
    alias: str | None = None,
    source_url: str | None = None,
    normalize: bool = True,
) -> StoredAudio:
    """Store an incoming audio and normalize it.

    ``alias`` defaults to the filename without its extension, which is almost
    always what the user meant; it stays editable afterwards.

    If ffmpeg is missing or the conversion fails, the **uuid folder is removed**
    before the error propagates — a half-ingested audio in the library is worse
    than a failed upload.
    """
    extension = formats.detect_extension(filename)
    display_name = (alias or Path(filename).stem).strip() or Path(filename).stem

    entry = store.create(
        alias=display_name,
        source=source,
        extension=extension,
        original_filename=filename,
        source_url=source_url,
    )

    try:
        store.save_original(entry.uuid, stream, extension)
        if normalize:
            return finalize(entry.uuid)
        return store.get(entry.uuid)
    except Exception:
        store.delete(entry.uuid)
        raise


def ingest_path(
    path: Path,
    source: AudioSource | str,
    *,
    alias: str | None = None,
    source_url: str | None = None,
) -> StoredAudio:
    """Ingest a file already on disk — the yt-dlp download path (Story 3.5)."""
    with path.open("rb") as handle:
        return ingest_file(
            handle,
            path.name,
            source,
            alias=alias,
            source_url=source_url,
        )


def finalize(audio_uuid: str) -> StoredAudio:
    """Normalize the stored original and record duration and sample rate."""
    entry = store.get(audio_uuid)
    original = entry.original_path
    if original is None:
        raise FileNotFoundError(f"Audio {audio_uuid} has no original file")

    formats.normalize_to_wav(original, entry.normalized_path)
    sample_rate, samples = formats.read_wav(entry.normalized_path)

    store.update(
        audio_uuid,
        duration_seconds=round(len(samples) / sample_rate, 6),
        sample_rate=sample_rate,
    )
    return store.get(audio_uuid)


def waveform(
    audio_uuid: str,
    points: int = formats.DEFAULT_WAVEFORM_POINTS,
    *,
    refresh: bool = False,
) -> formats.WaveformPeaks:
    """Peaks for the range selector and the piano-roll watermark.

    Cached as ``waveform.json`` next to the audio. The cache is reused only when
    it holds the requested number of points, so asking for a different
    resolution recomputes rather than returning the wrong shape.
    """
    entry = store.get(audio_uuid)
    if not refresh:
        cached = store.read_waveform(audio_uuid)
        if cached is not None and int(cached.get("points", -1)) == points:
            return formats.WaveformPeaks.from_dict(cached)

    if not entry.has_normalized():
        finalize(audio_uuid)
        entry = store.get(audio_uuid)

    peaks = formats.compute_peaks(entry.normalized_path, points)
    store.write_waveform(audio_uuid, peaks.to_dict())
    return peaks


def summary(entry: StoredAudio) -> AudioMetadata:
    """What the library listing shows. Kept as a seam for future trimming."""
    return entry.metadata
