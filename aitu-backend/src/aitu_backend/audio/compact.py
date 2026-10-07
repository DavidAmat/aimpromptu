"""The audio of a part written again with only the ranges in use (implementation 02, plan section
8.5, Q-3).

In the Personal Vault a cut is a range: the stored files never change, so every cut can be
restored. When a project is saved to the Private Library, the user wants the disk back: each file
the timeline uses only in part is written again with only its kept ranges, the timeline points at
the new file from its start to its end, and the old file is deleted once no project uses it.

**Nothing the user hears or reads moves.** The notes are in the time of the joined audio (the kept
ranges end to end), and the new files are exactly those ranges end to end:

* the new file is the old one decoded at its own rate and channels, the kept frames joined with the
  5 ms fade of a cut at each join, FLAC (lossless and sample exact), as ``piece-r<N>.flac`` has
  always been made (:func:`aitu_backend.audio.piece_audio.write_joined`);
* its 16 kHz copy is the old 16 kHz copy with the same frames joined (:func:`join_kept`), so the
  engine's audio of the part is the one the notes were made from, to the sample;
* its length in frames is the number of kept frames, given to the timeline as it is, so the files
  after it start where they started on the joined axis.

The timeline keeps its ``audioRevision``: the audio of the part did not change, so the notes stay
current. A part of several files is written file by file, and keeps its files, their order and
their names; a file cut away completely leaves the list. A file used whole is not touched.

:func:`prepare` writes the new files and changes nothing of the part, so a failure (ffmpeg) leaves
the project as it was. :func:`apply` then points the part at them.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from aitu_backend.audio import formats, piece_audio, sources
from aitu_backend.audio.frames import SAMPLES_PER_FRAME, FrameTable, join_kept
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import AudioEntry, Segment, SourceFile, Timeline

__all__ = ["Plan", "apply", "discard", "prepare"]

#: The extension of a file written again.
FORMAT = "flac"


@dataclass
class Plan:
    """What :func:`apply` does to one part: its new timeline, the new names of its files, and the
    16 kHz copies to put in its cache."""

    part_id: str
    timeline: Timeline
    files: list[SourceFile]
    #: ``normalized.wav`` of a part of one file, or ``src-<hash>.wav`` of each new file.
    cache: dict[str, Path] = field(default_factory=dict)
    #: The files the part used before and does not use now.
    replaced: list[str] = field(default_factory=list)
    #: The files :func:`prepare` added to the store.
    added: list[str] = field(default_factory=list)
    scratch: Path | None = None


def _write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = np.clip(np.round(samples * 32767.0), -32768, 32767).astype(np.int16)
    wavfile.write(path, 16_000, pcm)


def _kept_of(group: list[Segment], frames: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for segment in group:
        end = frames if segment.to_ms is None else segment.to_ms // bundle.FRAME_MS
        out.append((segment.from_ms // bundle.FRAME_MS, end))
    return out


def _cuts_inside(kept: list[tuple[int, int]], frames: int) -> list[tuple[int, int]]:
    cuts: list[tuple[int, int]] = []
    cursor = 0
    for start, end in sorted(kept):
        if start > cursor:
            cuts.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < frames:
        cuts.append((cursor, frames))
    return cuts


def _sixteen_k(part_id: str, timeline: Timeline, content_hash: str, frames: int) -> np.ndarray:
    """The 16 kHz copy of one file of the part, ``frames`` frames long."""
    if len(timeline.source_list()) == 1:
        normalized = paths.normalized_path(part_id)
        if not normalized.is_file():
            formats.normalize_to_wav(
                audio_files.file_path(content_hash, timeline.audio[content_hash].format),
                normalized,
            )
        _, samples = formats.read_wav(normalized)
    else:
        extension = timeline.audio[content_hash].format
        _, samples = formats.read_wav(sources.source_wav(part_id, content_hash, extension))
    length = frames * SAMPLES_PER_FRAME
    signal = np.asarray(samples, dtype=np.float32)
    if len(signal) >= length:
        return signal[:length]
    return np.pad(signal, (0, length - len(signal)))


def prepare(part_id: str, project: bundle.ProjectFile) -> Plan | None:
    """Write the new files of a part that has cuts. ``None`` when every file is used whole."""
    timeline = bundle.read_timeline(part_id)
    hashes = timeline.source_list()
    if not hashes or not bundle.cuts_of(timeline):
        return None
    axis = timeline.axis()
    groups: list[list[Segment]] = [[] for _ in hashes]
    for segment in timeline.segments:
        groups[segment.source if segment.source is not None else 0].append(segment)
    names = bundle.source_files(project, part_id, timeline)

    scratch = Path(tempfile.mkdtemp(prefix="aitu-compact-"))
    plan = Plan(part_id=part_id, timeline=timeline, files=[], scratch=scratch)
    order: list[str] = []
    audio: dict[str, AudioEntry] = {}
    lengths: list[int] = []
    try:
        for index, (content_hash, frames) in enumerate(axis):
            kept = _kept_of(groups[index], frames)
            if not kept:
                continue  # cut away completely: the file leaves the part
            name = names[index].model_copy()
            if kept == [(0, frames)]:
                order.append(content_hash)
                audio[content_hash] = timeline.audio[content_hash]
                lengths.append(frames)
                plan.files.append(name)
                continue
            table = FrameTable.from_cuts(_cuts_inside(kept, frames), frames)
            extension = timeline.audio[content_hash].format
            listen = scratch / f"{index}.{FORMAT}"
            piece_audio.write_joined(audio_files.file_path(content_hash, extension), listen, table)
            sixteen = scratch / f"{index}-16k.wav"
            _write_wav(
                sixteen, join_kept(_sixteen_k(part_id, timeline, content_hash, frames), table)
            )
            new_frames = table.piece_frames
            new_hash = audio_files.add_file(
                listen, FORMAT, duration_ms=new_frames * bundle.FRAME_MS
            )
            plan.added.append(new_hash)
            order.append(new_hash)
            audio[new_hash] = AudioEntry(format=FORMAT, frames=new_frames)
            lengths.append(new_frames)
            plan.cache[new_hash] = sixteen
            name.audio = new_hash
            name.format = FORMAT
            name.duration_seconds = new_frames * bundle.FRAME_MS / 1000.0
            plan.files.append(name)
    except Exception:
        discard(plan)
        raise
    if not order:
        discard(plan)
        raise ValueError("Every frame of this audio is cut: restore a part of it first")

    several = len(order) > 1
    plan.timeline = timeline.model_copy(
        update={
            "audio": audio,
            "sources": order if several else None,
            "segments": [
                Segment(
                    audio=content_hash,
                    from_ms=0,
                    to_ms=frames * bundle.FRAME_MS,
                    source=index if several else None,
                )
                for index, (content_hash, frames) in enumerate(zip(order, lengths))
            ],
        }
    )
    plan.replaced = [content_hash for content_hash in hashes if content_hash not in order]
    return plan


def discard(plan: Plan) -> None:
    """Undo :func:`prepare`: its scratch folder, and the new files no project uses."""
    if plan.scratch is not None:
        shutil.rmtree(plan.scratch, ignore_errors=True)
    audio_files.delete_unused(plan.added)


def apply(plan: Plan) -> None:
    """Point the part at its new files: the timeline, the names in ``project.json``, and the cache.

    The caller holds the project's lock, and syncs ``audio_refs`` and deletes the replaced files
    once the project is where it stays.
    """
    part_id = plan.part_id
    cache = paths.part_cache_dir(part_id)
    cache.mkdir(parents=True, exist_ok=True)
    for stale in [*cache.glob("piece-r*.*"), cache / "waveform.json", cache / "normalized.wav"]:
        stale.unlink(missing_ok=True)
    sources.clear(part_id, keep_sources=False)
    order = plan.timeline.source_list()
    for content_hash, sixteen in plan.cache.items():
        if len(order) == 1:
            shutil.copyfile(sixteen, paths.normalized_path(part_id))
        else:
            shutil.copyfile(sixteen, cache / f"{sources.SOURCE_PREFIX}{content_hash}.wav")
    bundle.write_timeline(part_id, plan.timeline)
    if len(order) > 1:
        sources.write_normalized(part_id, plan.timeline, paths.normalized_path(part_id))
    elif not paths.normalized_path(part_id).is_file():
        formats.normalize_to_wav(
            audio_files.file_path(order[0], plan.timeline.audio[order[0]].format),
            paths.normalized_path(part_id),
        )

    project = bundle.read_project(locate.part(part_id).project_id)
    source = project.part(part_id).source
    if len(order) > 1:
        source.files = plan.files
    else:
        # A part of one file is described by its source fields (bundle.source_files).
        first = plan.files[0]
        source.files = []
        source.kind = first.kind
        source.format = first.format
        source.original_filename = first.original_filename
        source.duration_seconds = first.duration_seconds
        source.url = first.url
    bundle.write_project(project)
    if plan.scratch is not None:
        shutil.rmtree(plan.scratch, ignore_errors=True)
