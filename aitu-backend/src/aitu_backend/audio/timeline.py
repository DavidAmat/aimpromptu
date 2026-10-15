"""Changing the audio timeline of a part in the middle: a passage put in, a stretch taken out
(implementation 02, plan sections 8.5 and 12, Phase 8).

The timeline is the files of the Audio step laid end to end (the **axis**), each one a whole stored
file or a range of one, and the cuts are ranges of that axis. The time of the notes is the time of
the kept frames joined (the **piece**). Everything here works on those two lists, entries and cuts,
and writes the segments again from them (:func:`aitu_backend.storage.bundle.segments_for_axis`), so
the Audio step, the joined audio and the cuts of implementation 08 keep working on the result:

* :func:`passage_pieces` says which ranges of which stored files a stretch of the piece plays: what
  a copied passage brings with it. No audio byte is read or copied (plan P-3).
* :func:`insert` puts entries into the axis at a moment of the piece. An entry the moment falls
  inside is split in two (the same file twice, a range each), and every cut after it moves later.
* :func:`remove` cuts a stretch of the piece out: the frames it covers become cuts, so the Audio
  step can still restore them in the Personal Vault.

Times are 10 ms frames: of a file for an entry's range, of the axis for a cut, of the piece for a
moment. A frame of the piano sheet (``frameMs``, 40 ms by default) is a whole number of them.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from aitu_backend.audio.frames import SAMPLE_RATE, SAMPLES_PER_FRAME
from aitu_backend.storage import audio_files, bundle
from aitu_backend.storage.bundle import AudioEntry, Timeline

__all__ = [
    "Piece",
    "axis_at",
    "insert",
    "insert_with_origins",
    "kept_frames",
    "passage_pieces",
    "remove",
    "silence",
]


@dataclass(frozen=True)
class Piece:
    """A range of one stored file: ``[start, end)`` in 10 ms frames of the file."""

    audio: str
    format: str
    #: The length of the whole file, in frames (the timeline lists it with the file).
    file_frames: int
    start: int
    end: int

    @property
    def frames(self) -> int:
        return self.end - self.start


def _kept(timeline: Timeline) -> list[tuple[int, int, int]]:
    """``(axisStart, axisEnd, pieceStart)`` of each kept range, in order."""
    if not timeline.source_list():
        return []
    total = sum(last - first for _, first, last in timeline.items())
    out: list[tuple[int, int, int]] = []
    position = piece = 0
    for cut_start, cut_end in bundle.cuts_of(timeline):
        if cut_start > position:
            out.append((position, cut_start, piece))
            piece += cut_start - position
        position = max(position, cut_end)
    if position < total:
        out.append((position, total, piece))
    return out


def kept_frames(timeline: Timeline) -> int:
    """How long the audio of the piece is, in frames: the kept frames of the axis."""
    return sum(end - start for start, end, _ in _kept(timeline))


def axis_at(timeline: Timeline, piece_frame: int) -> int:
    """The frame of the axis where ``piece_frame`` of the piece is.

    A moment at the end of a kept range is put at that end, before the cut that follows, so a
    passage put in there comes before the frames cut away. A moment past the end of the audio is
    the end of the last kept range.
    """
    kept = _kept(timeline)
    if not kept:
        return 0
    for axis_start, axis_end, piece_start in kept:
        if piece_frame <= piece_start + (axis_end - axis_start):
            return axis_start + max(0, piece_frame - piece_start)
    return kept[-1][1]


def passage_pieces(timeline: Timeline, from_frame: int, to_frame: int) -> list[Piece]:
    """The ranges of stored files that frames ``[from_frame, to_frame)`` of the piece play, in
    order. A stretch past the end of the audio gives nothing for that part (:func:`silence` fills
    it)."""
    if to_frame <= from_frame or not timeline.source_list():
        return []
    items = timeline.items()
    offsets = [0]
    for _, first, last in items[:-1]:
        offsets.append(offsets[-1] + last - first)
    out: list[Piece] = []
    for axis_start, axis_end, piece_start in _kept(timeline):
        piece_end = piece_start + axis_end - axis_start
        first, last = max(from_frame, piece_start), min(to_frame, piece_end)
        if first >= last:
            continue
        # The same range on the axis, then split where one entry ends and the next begins.
        lo, hi = axis_start + first - piece_start, axis_start + last - piece_start
        for index, (content_hash, start, end) in enumerate(items):
            entry_lo, entry_hi = offsets[index], offsets[index] + end - start
            a, b = max(lo, entry_lo), min(hi, entry_hi)
            if a >= b:
                continue
            audio = timeline.audio[content_hash]
            piece = Piece(
                audio=content_hash,
                format=audio.format,
                file_frames=audio.frames if audio.frames is not None else end,
                start=start + a - entry_lo,
                end=start + b - entry_lo,
            )
            previous = out[-1] if out else None
            if previous and previous.audio == piece.audio and previous.end == piece.start:
                out[-1] = Piece(
                    previous.audio, previous.format, previous.file_frames, previous.start, piece.end
                )
            else:
                out.append(piece)
    return out


def silence(frames: int) -> Piece:
    """A stored file of ``frames`` frames of silence (16 kHz mono WAV), for a passage that plays
    longer than its audio, or a moment past the end of the audio. The same length gives the same
    file, stored once."""
    if frames <= 0:
        raise ValueError("Silence needs a length")
    with tempfile.TemporaryDirectory(prefix="aitu-silence-") as folder:
        path = Path(folder) / "silence.wav"
        wavfile.write(path, SAMPLE_RATE, np.zeros(frames * SAMPLES_PER_FRAME, dtype=np.int16))
        content_hash = audio_files.add_file(path, "wav", duration_ms=frames * bundle.FRAME_MS)
    return Piece(audio=content_hash, format="wav", file_frames=frames, start=0, end=frames)


def _entries(timeline: Timeline) -> list[tuple[str, int, int]]:
    return timeline.items() if timeline.source_list() else []


def _rebuilt(
    timeline: Timeline,
    entries: list[tuple[str, int, int]],
    cuts: list[tuple[int, int]],
    audio: dict[str, AudioEntry],
) -> Timeline:
    """The timeline of ``entries`` and ``cuts``, one revision on."""
    used = {content_hash for content_hash, _, _ in entries}
    whole = [
        first == 0 and last == audio[content_hash].frames for content_hash, first, last in entries
    ]
    several = len(entries) > 1 or not all(whole)
    ranges: list[list[int] | None] = [
        None if is_whole else [first, last] for (_, first, last), is_whole in zip(entries, whole)
    ]
    merged: list[tuple[int, int]] = []
    for start, end in sorted(cuts):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    if not entries:
        segments = []
    elif several:
        segments = bundle.segments_for_axis(entries, merged)
    else:
        segments = bundle.segments_for_cuts(entries[0][0], merged, audio[entries[0][0]].frames)
    return timeline.model_copy(
        update={
            "audio": {key: value for key, value in audio.items() if key in used},
            "sources": [content_hash for content_hash, _, _ in entries] if several else None,
            "ranges": ranges if several and any(span is not None for span in ranges) else None,
            "segments": segments,
            "audio_revision": timeline.audio_revision + 1,
        }
    )


def insert(timeline: Timeline, piece_frame: int, pieces: list[Piece]) -> Timeline:
    """``pieces`` put into the audio at ``piece_frame`` of the piece; everything after plays
    later by their length. A moment past the end of the audio is reached with silence first."""
    have = kept_frames(timeline)
    if piece_frame > have and pieces:
        pieces = [silence(piece_frame - have), *pieces]
        piece_frame = have
    return insert_with_origins(timeline, piece_frame, pieces)[0]


def insert_with_origins(
    timeline: Timeline, piece_frame: int, pieces: list[Piece]
) -> tuple[Timeline, list[tuple[str, int]]]:
    """:func:`insert`, and where each entry of the new axis comes from: ``("old", i)`` for entry
    ``i`` of the old axis (or a part of it), ``("new", k)`` for ``pieces[k]``. The moment must be
    inside the audio (or at its end)."""
    entries = _entries(timeline)
    if not pieces:
        return timeline, [("old", index) for index in range(len(entries))]
    audio = dict(timeline.audio)
    cuts = bundle.cuts_of(timeline) if entries else []
    at = axis_at(timeline, min(piece_frame, kept_frames(timeline)))
    adding = [(piece.audio, piece.start, piece.end) for piece in pieces]
    added = [("new", index) for index in range(len(pieces))]
    for piece in pieces:
        audio.setdefault(piece.audio, AudioEntry(format=piece.format, frames=piece.file_frames))
    length = sum(piece.frames for piece in pieces)

    out: list[tuple[str, int, int]] = []
    origins: list[tuple[str, int]] = []
    position = 0
    placed = False
    for index, (content_hash, first, last) in enumerate(entries):
        size = last - first
        if not placed and position <= at < position + size:
            if at > position:
                out.append((content_hash, first, first + at - position))
                origins.append(("old", index))
            out.extend(adding)
            origins.extend(added)
            out.append((content_hash, first + at - position, last))
            origins.append(("old", index))
            placed = True
        else:
            out.append((content_hash, first, last))
            origins.append(("old", index))
        position += size
    if not placed:
        out.extend(adding)
        origins.extend(added)

    moved: list[tuple[int, int]] = []
    for start, end in cuts:
        if start >= at:
            moved.append((start + length, end + length))
        elif end > at:
            moved.extend([(start, at), (at + length, end + length)])
        else:
            moved.append((start, end))
    return _rebuilt(timeline, out, moved, audio), origins


def remove(timeline: Timeline, from_frame: int, to_frame: int) -> Timeline:
    """Frames ``[from_frame, to_frame)`` of the piece cut out of its audio: they become cuts of
    the axis, which the Audio step can restore. A stretch past the end of the audio cuts nothing
    there."""
    entries = _entries(timeline)
    if not entries or to_frame <= from_frame:
        return timeline
    cuts = list(bundle.cuts_of(timeline))
    for axis_start, axis_end, piece_start in _kept(timeline):
        piece_end = piece_start + axis_end - axis_start
        first, last = max(from_frame, piece_start), min(to_frame, piece_end)
        if first < last:
            cuts.append((axis_start + first - piece_start, axis_start + last - piece_start))
    return _rebuilt(timeline, entries, cuts, dict(timeline.audio))
