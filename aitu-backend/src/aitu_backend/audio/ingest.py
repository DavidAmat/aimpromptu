"""One ingest path for every source: upload, recording, YouTube.

Whatever the origin, an audio arrives the same way — bytes plus a filename plus
a source label — so uploads, browser recordings and yt-dlp downloads all land in
the store with identical structure and identical metadata. Later epics only have
to know about :func:`ingest_file`.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from aitu_backend.audio import formats, piece_audio, sources, store
from aitu_backend.audio.frames import frame_count
from aitu_backend.audio.store import StoredAudio
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource, TimeRange
from aitu_backend.storage import audio_files


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

    If ffmpeg is missing or the conversion fails, the **project is removed**
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


def append_file(
    audio_uuid: str,
    stream: BinaryIO,
    filename: str,
    source: AudioSource | str = AudioSource.UPLOAD,
) -> AudioMetadata:
    """**Add audio**: store a file, measure it, and append it to the part's audio.

    A file that cannot be read is not kept: when the conversion fails, the stored bytes are deleted
    again unless another project already uses them.
    """
    extension = formats.detect_extension(filename)
    content_hash = audio_files.add_stream(stream, extension)
    try:
        frames = sources.measure(audio_uuid, content_hash, extension)
        audio_files.record_duration(content_hash, frames * 10)
        return store.append(
            audio_uuid,
            content_hash,
            extension,
            frames,
            original_filename=filename,
            kind=AudioSource(source).value,
        )
    except Exception:
        audio_files.delete_unused([content_hash])
        raise


def finalize(audio_uuid: str) -> StoredAudio:
    """Normalize the stored original, and record its duration, sample rate and length in frames."""
    entry = store.get(audio_uuid)
    original = entry.original_path
    if original is None:
        raise FileNotFoundError(f"Audio {audio_uuid} has no original file")

    entry.directory.mkdir(parents=True, exist_ok=True)
    formats.normalize_to_wav(original, entry.normalized_path)
    sample_rate, samples = formats.read_wav(entry.normalized_path)

    store.set_audio_frames(audio_uuid, frame_count(len(samples)))
    store.update(
        audio_uuid,
        duration_seconds=round(len(samples) / sample_rate, 6),
        sample_rate=sample_rate,
    )
    return store.get(audio_uuid)


def create_segment(
    audio_uuid: str,
    start_seconds: float,
    end_seconds: float,
    *,
    alias: str | None = None,
) -> StoredAudio:
    """Create a self-contained WAV child for one range of an audio.

    The child is a new project whose one audio file is a WAV of only the selected
    range, with the same samples as its ``normalized.wav``. Its lineage points to the root audio and uses absolute
    root timestamps, even if a segment is trimmed again.
    """
    source = store.get(audio_uuid)
    if not source.has_normalized():
        source = finalize(audio_uuid)

    duration = source.metadata.duration_seconds
    if duration is None:
        duration = formats.duration_seconds(source.normalized_path)
    if start_seconds < 0 or end_seconds > duration + 0.001:
        raise ValueError(f"The segment must stay inside the {duration:.2f}-second source audio")
    if end_seconds <= start_seconds:
        raise ValueError(
            f"endSeconds must be after startSeconds ({end_seconds} <= {start_seconds})"
        )
    if start_seconds <= 0.001 and end_seconds >= duration - 0.001:
        raise ValueError("Choose a smaller range before creating a segment")
    if source.metadata.cuts:
        # The selector's seconds are those of the piece (the cuts removed), the file's are not.
        raise ValueError(
            "This piece has cuts. Cut it on the Audio tab of the Piece page instead of creating a "
            "segment."
        )

    source_range = source.metadata.source_time_range
    root_uuid = source.metadata.source_audio_uuid or source.uuid
    root_start = (source_range.start_seconds if source_range else 0.0) + start_seconds
    root_end = (source_range.start_seconds if source_range else 0.0) + end_seconds
    root_range = TimeRange(start_seconds=root_start, end_seconds=root_end)
    display_alias = (alias or "").strip() or (
        f"{source.metadata.alias} — segment {root_start:.2f}s–{root_end:.2f}s"
    )
    filename = f"{display_alias}.wav"

    segment = store.create(
        alias=display_alias,
        source=AudioSource.SEGMENT,
        extension="wav",
        original_filename=filename,
        source_audio_uuid=root_uuid,
        source_time_range=root_range,
    )
    try:
        segment.directory.mkdir(parents=True, exist_ok=True)
        formats.slice_wav(
            source.normalized_path,
            segment.normalized_path,
            start_seconds,
            end_seconds,
        )
        # The source is already the canonical mono 16 kHz WAV, so the clip is both the stored
        # file and its normalized copy: no ffmpeg run.
        store.replace_original(segment.uuid, segment.normalized_path, "wav", keep_cuts=False)
        sample_rate, samples = formats.read_wav(segment.normalized_path)
        store.update(
            segment.uuid,
            duration_seconds=round(len(samples) / sample_rate, 6),
            sample_rate=sample_rate,
        )
        return store.get(segment.uuid)
    except Exception:
        store.delete(segment.uuid)
        raise


def waveform(
    audio_uuid: str,
    points: int = formats.DEFAULT_WAVEFORM_POINTS,
    *,
    refresh: bool = False,
) -> formats.WaveformPeaks:
    """Peaks for the range selector and the piano-roll watermark.

    Cached as ``waveform.json`` in the part's cache folder. The cache is reused only when
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

    # The waveform of the piece: with cuts, the edited audio every player plays.
    piece = piece_audio.ensure(audio_uuid)
    peaks = formats.compute_peaks(piece.normalized if piece else entry.normalized_path, points)
    store.write_waveform(audio_uuid, peaks.to_dict())
    return peaks


def summary(entry: StoredAudio) -> AudioMetadata:
    """What the library listing shows. Kept as a seam for future trimming."""
    return entry.metadata
