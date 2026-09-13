"""The splice itself: membership by onset, scale the take, drop marks inside the window.

A re-recorded passage is written back into exactly the window it replaces. The piece's length
and column count do not change, so every mark after the window keeps its address. See
``context/implementations/plan/wall-clock-rewrite.md`` §3.
"""

from __future__ import annotations

from aitu_backend.matrix.time_grid import frame_of_seconds, frame_start_seconds
from aitu_backend.schemas.editing import DroppedMarks, EditWindow
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.transcription.engine import NoteEvent


def min_duration_seconds(frame_ms: float) -> float:
    """Notes shorter than one frame after scaling are dropped (D-05)."""
    return float(frame_ms) / 1000.0


def window_from_frames(start_frame: int, end_frame: int, frame_ms: float) -> EditWindow:
    """Seconds are computed once from the columns the reader clicked, then frozen."""
    if end_frame <= start_frame:
        raise ValueError(f"endFrame must be after startFrame ({end_frame} <= {start_frame})")
    return EditWindow(
        start_frame=start_frame,
        end_frame=end_frame,
        start_seconds=frame_start_seconds(start_frame, frame_ms),
        end_seconds=frame_start_seconds(end_frame, frame_ms),
        frame_ms=frame_ms,
    )


def window_from_seconds(start_seconds: float, end_seconds: float, frame_ms: float) -> EditWindow:
    """A range typed as timestamps. Columns are derived and frozen with the seconds."""
    if end_seconds <= start_seconds:
        raise ValueError(
            f"endSeconds must be after startSeconds ({end_seconds} <= {start_seconds})"
        )
    start_frame = frame_of_seconds(start_seconds, frame_ms)
    end_frame = frame_of_seconds(end_seconds, frame_ms)
    if end_frame <= start_frame:
        end_frame = start_frame + 1
    return EditWindow(
        start_frame=start_frame,
        end_frame=end_frame,
        start_seconds=float(start_seconds),
        end_seconds=float(end_seconds),
        frame_ms=frame_ms,
    )


def onset_in_window(event: NoteEvent, start_seconds: float, end_seconds: float) -> bool:
    """Membership is decided by onset time only. A note that started earlier is left alone."""
    return start_seconds <= event.start < end_seconds


def events_in_window(
    events: list[NoteEvent], start_seconds: float, end_seconds: float
) -> list[NoteEvent]:
    return [event for event in events if onset_in_window(event, start_seconds, end_seconds)]


def factor_for_slowdown(slowdown: int | None, take_seconds: float, window_seconds: float) -> float:
    """How take times map into the window.

    Original / 2× / 4× slower use the chosen ratio. Fit to the window measures it from the take.
    """
    if slowdown is None:
        if take_seconds <= 0:
            raise ValueError("A take with no sounding notes cannot be fitted to the window")
        return window_seconds / take_seconds
    if slowdown not in (1, 2, 4):
        raise ValueError(f"slowdown must be 1, 2 or 4, got {slowdown}")
    return 1.0 / float(slowdown)


def scale_take(
    events: list[NoteEvent],
    *,
    factor: float,
    start_seconds: float,
    end_seconds: float,
    frame_ms: float,
) -> list[NoteEvent]:
    """Offset and compress the take into the window; cut anything that still sounds at the end."""
    if factor <= 0:
        raise ValueError(f"factor must be a positive number, got {factor}")
    shortest = min_duration_seconds(frame_ms)
    scaled: list[NoteEvent] = []
    for event in events:
        new_start = start_seconds + event.start * factor
        new_end = start_seconds + event.end * factor
        if new_start >= end_seconds:
            continue
        if new_end > end_seconds:
            new_end = end_seconds
        if new_end - new_start < shortest:
            continue
        scaled.append(event.model_copy(update={"start": new_start, "end": new_end}))
    scaled.sort(key=lambda item: (item.start, item.midi_note))
    return scaled


def splice_events(
    original: list[NoteEvent],
    take: list[NoteEvent],
    *,
    start_seconds: float,
    end_seconds: float,
    factor: float,
    frame_ms: float,
) -> tuple[list[NoteEvent], list[NoteEvent], list[NoteEvent]]:
    """Replace every event whose onset falls in the window with the scaled take.

    Returns ``(result, removed, arriving)``. ``durationSeconds`` is not this function's job:
    the caller asserts it against the piece after writing.
    """
    removed = events_in_window(original, start_seconds, end_seconds)
    kept = [event for event in original if not onset_in_window(event, start_seconds, end_seconds)]
    arriving = scale_take(
        take,
        factor=factor,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        frame_ms=frame_ms,
    )
    result = sorted(kept + arriving, key=lambda item: (item.start, item.midi_note))
    return result, removed, arriving


def _in_frames(frame: int, start_frame: int, end_frame: int) -> bool:
    return start_frame <= frame < end_frame


def count_marks_in_window(
    rhythm: SavedRhythm | None, start_frame: int, end_frame: int
) -> DroppedMarks:
    """How many stored editorial marks would be dropped, per kind."""
    if rhythm is None:
        return DroppedMarks()
    return DroppedMarks(
        figure_overrides=sum(
            1 for item in rhythm.overrides if _in_frames(item.start_frame, start_frame, end_frame)
        ),
        beam_breaks=sum(
            1 for item in rhythm.beam_breaks if _in_frames(item.start_frame, start_frame, end_frame)
        ),
        hidden_notes=sum(
            1
            for item in rhythm.hidden_notes
            if _in_frames(item.start_frame, start_frame, end_frame)
        ),
        fingerings=sum(
            1 for item in rhythm.fingers if _in_frames(item.start_frame, start_frame, end_frame)
        ),
    )


def drop_marks_in_window(rhythm: SavedRhythm, start_frame: int, end_frame: int) -> SavedRhythm:
    """Remove marks anchored inside the window. Key, speed changes and marks outside stay.

    A passage boundary that falls inside the window is kept: its frame is still a real moment.
    """
    return rhythm.model_copy(
        update={
            "overrides": [
                item
                for item in rhythm.overrides
                if not _in_frames(item.start_frame, start_frame, end_frame)
            ],
            "beam_breaks": [
                item
                for item in rhythm.beam_breaks
                if not _in_frames(item.start_frame, start_frame, end_frame)
            ],
            "hidden_notes": [
                item
                for item in rhythm.hidden_notes
                if not _in_frames(item.start_frame, start_frame, end_frame)
            ],
            "fingers": [
                item
                for item in rhythm.fingers
                if not _in_frames(item.start_frame, start_frame, end_frame)
            ],
        }
    )


def trim_take_events(
    events: list[NoteEvent],
    *,
    first_onset: float,
    length_seconds: float | None,
) -> list[NoteEvent]:
    """Shift so the first onset is 0, and optionally clip to ``length_seconds`` after that.

    With Fit to the window, ``length_seconds`` is ``None`` and the take runs to its last note.
    """
    if not events:
        return []
    shifted: list[NoteEvent] = []
    limit = None if length_seconds is None else first_onset + length_seconds
    for event in events:
        if event.start < first_onset:
            continue
        if limit is not None and event.start >= limit:
            continue
        new_start = event.start - first_onset
        new_end = event.end - first_onset
        if limit is not None:
            new_end = min(new_end, length_seconds or new_end)
        if new_end <= new_start:
            continue
        shifted.append(event.model_copy(update={"start": new_start, "end": new_end}))
    shifted.sort(key=lambda item: (item.start, item.midi_note))
    return shifted


def first_onset_seconds(events: list[NoteEvent]) -> float | None:
    if not events:
        return None
    return min(event.start for event in events)


def last_release_seconds(events: list[NoteEvent]) -> float | None:
    if not events:
        return None
    return max(event.end for event in events)
