"""Lifecycle of a staged session: start, record, preview, accept, cancel.

One lifecycle, two operations. **Replace** (Epic 11) is given a window at the start and may never
change the piece's length. **Append** and **insert** (Epic 13) are given a moment instead, and the
passage's own length is what the piece grows by — see :mod:`aitu_backend.editing.compose` for why
that is allowed in exactly this one place.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from aitu_backend.audio import formats, store
from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing
from aitu_backend.editing import audio_splice, compose, history, preview as preview_mod
from aitu_backend.editing.splice import (
    count_marks_in_window,
    drop_marks_in_window,
    first_onset_seconds,
    last_release_seconds,
    splice_events,
    window_from_frames,
    window_from_seconds,
)
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, frame_of_seconds
from aitu_backend.progress import BaseProgress
from aitu_backend.schemas.editing import (
    AcceptOut,
    Placement,
    ConfirmationOut,
    DroppedMarks,
    EditSessionOut,
    MovedMarks,
    PreviewOut,
)
from aitu_backend.schemas.rhythm import SpeedChange
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.storage import staging
from aitu_backend.storage.staging import SessionRecord
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent, TranscriptionEngine


class EditError(ValueError):
    """A session operation that cannot proceed, with a message meant to be shown."""


def _window(
    *,
    start_frame: int | None,
    end_frame: int | None,
    start_seconds: float | None,
    end_seconds: float | None,
    frame_ms: float,
):
    if start_frame is not None and end_frame is not None:
        return window_from_frames(start_frame, end_frame, frame_ms)
    if start_seconds is not None and end_seconds is not None:
        return window_from_seconds(start_seconds, end_seconds, frame_ms)
    raise EditError("Mark a stretch as columns or as two timestamps.")


def _factor(slowdown: int | None) -> float:
    if slowdown is None:
        return 1.0
    if slowdown not in (1, 2, 4):
        raise EditError("Speed must be original, 2 times slower, or 4 times slower.")
    return 1.0 / float(slowdown)


def _moment(
    *,
    start_frame: int | None,
    start_seconds: float | None,
    frame_ms: float,
) -> float:
    """The instant a composed passage opens at, snapped to the start of a column.

    Snapped because a passage occupies a whole number of columns and has to begin on one; see the
    note at the top of :mod:`aitu_backend.editing.compose`.
    """
    if start_seconds is None and start_frame is None:
        raise EditError("Say where the passage goes, as a column or as a timestamp.")
    seconds = (
        float(start_seconds)
        if start_seconds is not None
        else start_frame * frame_ms / 1000.0  # type: ignore[operator]
    )
    if seconds < 0:
        raise EditError("A passage cannot open before the piece starts.")
    return compose.frame_at_or_after(seconds, frame_ms) * frame_ms / 1000.0


def _available_take_seconds(record: SessionRecord) -> float | None:
    """How much recording there is after the take's first onset, or ``None`` if not known yet.

    The bound a composed passage is measured against. A transcription engine reports the sustain it
    hears, and a pedalled chord is heard ringing long after the recording stops — a four-second take
    can come back with a note "ending" ten seconds in. With a window that never matters, because the
    window decides the length; while composing the take decides it, so the recording has to be the
    ceiling or one blurred sustain would stretch the passage to several times what was played.
    """
    duration = record.untrimmed_duration_seconds
    if duration is None:
        return None
    start = max(0.0, record.take_start_seconds or 0.0)
    end = duration if record.take_end_seconds is None else min(record.take_end_seconds, duration)
    remaining = (end - start) - (record.first_onset_seconds or 0.0)
    return remaining if remaining > 0 else None


def _passage_length(record: SessionRecord, take: list[NoteEvent]) -> float:
    """How long this take will be once scaled: a whole number of columns, or zero if empty."""
    if not take:
        return 0.0
    prepared = preview_mod.prepared_take(take, record)
    length, _ = compose.passage_bounds(
        prepared, at_seconds=0.0, factor=record.factor, frame_ms=record.frame_ms
    )
    return length


def _refresh_passage(record: SessionRecord, take: list[NoteEvent] | None = None) -> SessionRecord:
    """Re-measure a composed session's window from its take.

    A replace session's window is frozen at the start and this does nothing to it. A composed
    session has no window until there is a take, and the window it then has is the passage — so it
    is re-measured every time the take or the speed changes, and never remembered from before.
    """
    if not record.composing:
        return record
    if take is None:
        take = staging.read_take_events(record.audio_uuid, record.session_uuid)
    available = _available_take_seconds(record)
    if available is not None and (
        record.trim_length_seconds is None or record.trim_length_seconds > available
    ):
        # Never longer than the recording. A shorter trim the reader asked for is left alone.
        record.trim_length_seconds = available
    length = _passage_length(record, take)
    record.start_frame = compose.frame_at_or_after(record.start_seconds, record.frame_ms)
    record.end_seconds = record.start_seconds + length
    record.end_frame = record.start_frame + int(round(length * 1000.0 / record.frame_ms))
    return record


def to_out(record: SessionRecord) -> EditSessionOut:
    return EditSessionOut(
        session_uuid=record.session_uuid,
        audio_uuid=record.audio_uuid,
        placement=record.placement,
        gap_seconds=record.gap_seconds,
        start_frame=record.start_frame,
        end_frame=record.end_frame,
        start_seconds=record.start_seconds,
        end_seconds=record.end_seconds,
        frame_ms=record.frame_ms,
        window_seconds=record.window_seconds,
        slowdown=record.slowdown,
        factor=record.factor,
        splice_audio=record.splice_audio,
        click_interval_ms=record.click_interval_ms,
        has_take=staging.has_take(record.audio_uuid, record.session_uuid),
        has_events=staging.has_events(record.audio_uuid, record.session_uuid),
        first_onset_seconds=record.first_onset_seconds,
        trim_length_seconds=record.trim_length_seconds,
        untrimmed_duration_seconds=record.untrimmed_duration_seconds,
        expected_take_seconds=record.expected_take_seconds,
        take_start_seconds=record.take_start_seconds,
        take_end_seconds=record.take_end_seconds,
    )


def start(
    audio_uuid: str,
    *,
    placement: Placement = "replace",
    start_frame: int | None = None,
    end_frame: int | None = None,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    gap_seconds: float = 1.0,
    frame_ms: float = DEFAULT_FRAME_MS,
    slowdown: int | None = 1,
    splice_audio: bool = True,
    click_interval_ms: float | None = None,
) -> SessionRecord:
    """Open a disposable session. Nothing outside its folder changes until accept."""
    if not store.exists(audio_uuid):
        raise FileNotFoundError(audio_uuid)
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise EditError("This piece has not been transcribed yet.")

    if placement in ("append", "insert"):
        if slowdown is None:
            raise EditError(
                "A passage being composed has no window to fit to. Choose a speed instead."
            )
        if placement == "append":
            at = compose.append_anchor(stored.events, gap_seconds, frame_ms)
        else:
            at = _moment(start_frame=start_frame, start_seconds=start_seconds, frame_ms=frame_ms)
            if at > stored.duration_seconds + 1e-6:
                raise EditError(
                    "That moment is past the end of the piece. Append the passage instead."
                )
        at_frame = compose.frame_at_or_after(at, frame_ms)
        record = SessionRecord(
            session_uuid=staging.new_session_uuid(),
            audio_uuid=audio_uuid,
            placement=placement,
            gap_seconds=(gap_seconds if placement == "append" else None),
            start_frame=at_frame,
            end_frame=at_frame,
            start_seconds=at,
            end_seconds=at,
            frame_ms=frame_ms,
            slowdown=slowdown,
            factor=_factor(slowdown),
            splice_audio=splice_audio,
            click_interval_ms=click_interval_ms,
            # No window to fill, so nothing to trim the take down to: a composed passage is
            # however long it was played (Subtask 13.1.1.4).
            trim_length_seconds=None,
        )
        return staging.create(record)

    if placement != "replace":
        raise EditError(f"Unknown placement {placement!r}.")

    window = _window(
        start_frame=start_frame,
        end_frame=end_frame,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        frame_ms=frame_ms,
    )
    if window.end_seconds > stored.duration_seconds + 1e-6:
        raise EditError("That stretch runs past the end of the piece.")
    record = SessionRecord(
        session_uuid=staging.new_session_uuid(),
        audio_uuid=audio_uuid,
        placement="replace",
        start_frame=window.start_frame,
        end_frame=window.end_frame,
        start_seconds=window.start_seconds,
        end_seconds=window.end_seconds,
        frame_ms=window.frame_ms,
        slowdown=slowdown,
        factor=_factor(slowdown),
        splice_audio=splice_audio,
        click_interval_ms=click_interval_ms,
        trim_length_seconds=(None if slowdown is None else window.window_seconds * float(slowdown)),
    )
    return staging.create(record)


def load(audio_uuid: str, session_uuid: str) -> SessionRecord:
    return staging.read(audio_uuid, session_uuid)


def cancel(audio_uuid: str, session_uuid: str) -> None:
    staging.delete(audio_uuid, session_uuid)


def patch(
    audio_uuid: str,
    session_uuid: str,
    *,
    slowdown: int | None = None,
    fit: bool = False,
    splice_audio: bool | None = None,
    click_interval_ms: float | None = None,
    trim_length_seconds: float | None = None,
    take_start_seconds: float | None = None,
    take_end_seconds: float | None = None,
    gap_seconds: float | None = None,
    at_seconds: float | None = None,
) -> SessionRecord:
    record = staging.read(audio_uuid, session_uuid)
    if fit:
        if record.composing:
            raise EditError(
                "A passage being composed has no window to fit to. Choose a speed instead."
            )
        record.slowdown = None
        record.trim_length_seconds = None
    elif slowdown is not None:
        record.slowdown = slowdown
        record.factor = _factor(slowdown)
        # A composed passage is as long as it was played: there is no window to cut it down to.
        if not record.composing:
            record.trim_length_seconds = record.window_seconds * float(slowdown)
    if splice_audio is not None:
        record.splice_audio = splice_audio
    if click_interval_ms is not None:
        record.click_interval_ms = click_interval_ms
    if gap_seconds is not None or at_seconds is not None:
        if not record.composing:
            raise EditError("A marked stretch is replaced where it is; it cannot be moved.")
        _move_passage(record, gap_seconds=gap_seconds, at_seconds=at_seconds)
    if trim_length_seconds is not None:
        if record.untrimmed_duration_seconds is not None and record.first_onset_seconds is not None:
            remaining = record.untrimmed_duration_seconds - record.first_onset_seconds
            if trim_length_seconds > remaining + 1e-6:
                raise EditError("There is no more of the take to extend into.")
        record.trim_length_seconds = trim_length_seconds
    start = record.take_start_seconds if take_start_seconds is None else take_start_seconds
    end = record.take_end_seconds if take_end_seconds is None else take_end_seconds
    if take_start_seconds is not None or take_end_seconds is not None:
        if start is not None and end is not None and end <= start:
            raise EditError("The end of the take must be after the start.")
        duration = record.untrimmed_duration_seconds
        if duration is not None:
            if start is not None and start > duration + 1e-6:
                raise EditError("That cut starts past the end of the take.")
            if end is not None and end > duration + 1e-6:
                raise EditError("That cut runs past the end of the take.")
        record.take_start_seconds = start
        record.take_end_seconds = end
    take = staging.read_take_events(audio_uuid, session_uuid)
    if take and record.slowdown is None:
        prepared = preview_mod.prepared_take(take, record)
        record.factor = preview_mod.measured_factor(record, prepared)
    _refresh_passage(record, take)
    staging.write(record)
    return record


def _move_passage(
    record: SessionRecord,
    *,
    gap_seconds: float | None,
    at_seconds: float | None,
) -> None:
    """Slide a composed passage without re-recording it.

    Where a passage goes is a decision about the piece and the take is a decision about the
    playing, so changing one must not cost the other: moving the passage re-anchors the window and
    keeps the recording, the trim and the transcription exactly as they are.
    """
    stored = pipeline.load_note_events(record.audio_uuid)
    if stored is None:
        raise EditError("This piece has not been transcribed yet.")
    if record.placement == "append":
        if gap_seconds is None:
            raise EditError("An appended passage is moved by changing the silence before it.")
        record.gap_seconds = max(0.0, float(gap_seconds))
        record.start_seconds = compose.append_anchor(
            stored.events, record.gap_seconds, record.frame_ms
        )
        return
    if at_seconds is None:
        raise EditError("An inserted passage is moved by changing the moment it opens at.")
    moment = _moment(start_frame=None, start_seconds=at_seconds, frame_ms=record.frame_ms)
    if moment > stored.duration_seconds + 1e-6:
        raise EditError("That moment is past the end of the piece. Append the passage instead.")
    record.start_seconds = moment


def store_take(audio_uuid: str, session_uuid: str, source: Path) -> SessionRecord:
    """Normalise the uploaded take into the session. Does not transcribe."""
    record = staging.read(audio_uuid, session_uuid)
    target = staging.untrimmed_path(audio_uuid, session_uuid)
    formats.normalize_to_wav(source, target)
    record.untrimmed_duration_seconds = formats.duration_seconds(target)
    record.first_onset_seconds = None
    record.take_start_seconds = None
    record.take_end_seconds = None
    for stale in (
        staging.selected_path(audio_uuid, session_uuid),
        staging.trimmed_path(audio_uuid, session_uuid),
        staging.scaled_path(audio_uuid, session_uuid),
        staging.take_events_path(audio_uuid, session_uuid),
    ):
        if stale.is_file():
            stale.unlink()
    staging.write(record)
    return record


def transcribe_take(
    audio_uuid: str,
    session_uuid: str,
    *,
    engine: TranscriptionEngine | str | None = None,
    reporter: BaseProgress | None = None,
) -> SessionRecord:
    record = staging.read(audio_uuid, session_uuid)
    wav = staging.untrimmed_path(audio_uuid, session_uuid)
    if not wav.is_file():
        raise EditError("Record a take before transcribing it.")
    duration = record.untrimmed_duration_seconds or formats.duration_seconds(wav)
    start = record.take_start_seconds if record.take_start_seconds is not None else 0.0
    end = record.take_end_seconds if record.take_end_seconds is not None else duration
    start = max(0.0, start)
    end = min(duration, end)
    if end - start < 0.05:
        raise EditError("Select a longer stretch of the take.")
    clip = staging.selected_path(audio_uuid, session_uuid)
    formats.slice_wav(wav, clip, start, end)
    events = pipeline.transcribe_file(
        clip, engine=engine or pipeline.DEFAULT_ENGINE, reporter=reporter
    )
    staging.write_take_events(audio_uuid, session_uuid, events)
    onset = first_onset_seconds(events)
    record.first_onset_seconds = onset
    if record.slowdown is None and events:
        prepared = preview_mod.prepared_take(events, record)
        record.factor = preview_mod.measured_factor(record, prepared)
        last = last_release_seconds(prepared)
        record.trim_length_seconds = last
    # The passage is now measurable, so the session finally has a window.
    _refresh_passage(record, events)
    staging.write(record)
    _write_trimmed_audio(record)
    return record


def _write_trimmed_audio(record: SessionRecord) -> None:
    source = staging.selected_path(record.audio_uuid, record.session_uuid)
    if not source.is_file():
        source = staging.untrimmed_path(record.audio_uuid, record.session_uuid)
    if not source.is_file():
        return
    onset = record.first_onset_seconds or 0.0
    length = record.trim_length_seconds
    source_len = formats.duration_seconds(source)
    if length is None:
        length = max(0.001, source_len - onset)
    end = min(source_len, onset + length)
    if end <= onset:
        return
    try:
        formats.slice_wav(
            source, staging.trimmed_path(record.audio_uuid, record.session_uuid), onset, end
        )
    except ValueError:
        return


def _confirmation(
    record: SessionRecord, original_count: int, arriving_count: int
) -> ConfirmationOut:
    stored = pipeline.load_note_events(record.audio_uuid)
    rhythm = pipeline.load_rhythm(record.audio_uuid)
    duration = stored.duration_seconds if stored is not None else 0.0

    if record.composing:
        # Nothing leaves a composed passage: it is put between what is there, not over it.
        passage = record.window_seconds
        _, moved_marks = compose.shift_marks(
            rhythm,
            at_seconds=record.start_seconds,
            passage_seconds=passage,
            placement=record.placement,
        )
        notes_moved = 0
        if stored is not None and record.placement == "insert":
            # The same column test the splice uses, so the number said here is the number moved.
            at_frame = compose.frame_at_or_after(record.start_seconds, record.frame_ms)
            notes_moved = sum(
                1
                for event in stored.events
                if frame_of_seconds(event.start, record.frame_ms) >= at_frame
            )
        after = (
            max(duration, record.start_seconds + passage)
            if record.placement == "append"
            else duration + passage
        )
        return ConfirmationOut(
            placement=record.placement,
            notes_removed=0,
            notes_arriving=arriving_count,
            dropped_marks=DroppedMarks(),
            moved_marks=moved_marks,
            notes_moved=notes_moved,
            splice_audio=record.splice_audio,
            length_unchanged=False,
            window_seconds=passage,
            duration_seconds=after,
            next_version=history.current_version(record.audio_uuid) + 1,
        )

    dropped = count_marks_in_window(rhythm, record.start_frame, record.end_frame)
    removed = 0
    if stored is not None:
        removed = sum(
            1 for event in stored.events if record.start_seconds <= event.start < record.end_seconds
        )
    return ConfirmationOut(
        placement="replace",
        notes_removed=removed if original_count < 0 else original_count,
        notes_arriving=arriving_count,
        dropped_marks=dropped,
        moved_marks=MovedMarks(),
        notes_moved=0,
        splice_audio=record.splice_audio,
        length_unchanged=True,
        window_seconds=record.window_seconds,
        duration_seconds=duration,
        next_version=history.current_version(record.audio_uuid) + 1,
    )


def confirmation(audio_uuid: str, session_uuid: str) -> ConfirmationOut:
    record = staging.read(audio_uuid, session_uuid)
    take = staging.read_take_events(audio_uuid, session_uuid)
    arriving = 0
    if take:
        factor = record.factor
        if record.slowdown is None:
            factor = preview_mod.measured_factor(record, preview_mod.prepared_take(take, record))
        if record.composing:
            prepared = preview_mod.prepared_take(take, record)
            _, placed = compose.passage_bounds(
                prepared, at_seconds=0.0, factor=factor, frame_ms=record.frame_ms
            )
            arriving = len(placed)
        else:
            arriving = len(preview_mod.scaled_take(take, record, factor))
    return _confirmation(record, -1, arriving)


def preview(
    audio_uuid: str,
    session_uuid: str,
    *,
    anchor_figure: FigureName = FigureName.NEGRA,
    anchor_ms: float | None = None,
    speed_changes: list[SpeedChange] | None = None,
) -> PreviewOut:
    record = staging.read(audio_uuid, session_uuid)
    if not staging.has_events(audio_uuid, session_uuid):
        raise EditError("Transcribe the take before previewing it.")
    take = staging.read_take_events(audio_uuid, session_uuid)
    if not take:
        raise EditError("No notes were found in this take. Trim a different range or record again.")
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise EditError("This piece has not been transcribed yet.")
    rhythm = pipeline.load_rhythm(audio_uuid)
    figure = anchor_figure
    named_ms = anchor_ms
    changes = speed_changes or []
    if rhythm is not None:
        figure = rhythm.anchor_figure if anchor_figure == FigureName.NEGRA else anchor_figure
        if named_ms is None:
            named_ms = rhythm.anchor_ms
        if not changes:
            changes = rhythm.speed_changes
        if anchor_figure == FigureName.NEGRA:
            figure = rhythm.anchor_figure
    if named_ms is None:
        named_ms = 500.0
    passage_ms = preview_mod.ladder_ms_at(record.start_frame, named_ms, changes)
    factor = record.factor
    if record.slowdown is None:
        factor = preview_mod.measured_factor(record, preview_mod.prepared_take(take, record))
        record.factor = factor
        staging.write(record)
    prepared = preview_mod.prepared_take(take, record)
    if record.composing:
        # The passage is drawn alone, at its own length, with none of the piece around it: what
        # the reader is deciding here is only whether this is the passage they meant to play.
        score, length, arriving = preview_mod.composed_passage_score(
            take,
            record,
            factor,
            anchor_figure=figure,
            anchor_ms=passage_ms,
            title=stored.title,
        )
        removed: list[NoteEvent] = []
        record.end_seconds = record.start_seconds + length
        record.end_frame = record.start_frame + int(round(length * 1000.0 / record.frame_ms))
        staging.write(record)
        relative = arriving
    else:
        _, removed, arriving = splice_events(
            stored.events,
            prepared,
            start_seconds=record.start_seconds,
            end_seconds=record.end_seconds,
            factor=factor,
            frame_ms=record.frame_ms,
        )
        score = preview_mod.passage_score(
            stored.events,
            stored.duration_seconds,
            take,
            record,
            factor,
            anchor_figure=figure,
            anchor_ms=passage_ms,
            title=stored.title,
        )
        relative = preview_mod.scaled_take(take, record, factor)
    peaks, _ = preview_mod.take_peaks(relative, record.frame_ms)
    labelled = preview_mod.labelled_against(peaks, figure, passage_ms)
    return PreviewOut(
        session=to_out(record),
        confirmation=_confirmation(record, len(removed), len(arriving)),
        score=score,
        peaks=peaks,
        labelled=labelled,
        take_note_count=len(prepared),
        scaled_note_count=len(arriving),
    )


def _ensure_window_clip(record: SessionRecord) -> Path:
    target = staging.window_path(record.audio_uuid, record.session_uuid)
    if target.is_file():
        return target
    entry = store.get(record.audio_uuid)
    if not entry.has_normalized():
        raise EditError("This audio has not been normalized yet.")
    formats.slice_wav(
        entry.normalized_path,
        target,
        record.start_seconds,
        record.end_seconds,
    )
    return target


def take_peaks(audio_uuid: str, session_uuid: str, points: int = 1000) -> formats.WaveformPeaks:
    """Min/max peaks of the untrimmed take, for the review range selector."""
    wav = staging.untrimmed_path(audio_uuid, session_uuid)
    if not wav.is_file():
        raise EditError("Record a take first.")
    return formats.compute_peaks(wav, points)


def window_audio(audio_uuid: str, session_uuid: str, *, slowed: bool = False) -> Path:
    record = staging.read(audio_uuid, session_uuid)
    if record.composing:
        raise EditError("There is nothing recorded here yet: this passage is new.")
    clip = _ensure_window_clip(record)
    if not slowed:
        return clip
    rate = float(record.slowdown or 1)
    if rate == 1:
        return clip
    slow = staging.window_slow_path(audio_uuid, session_uuid)
    # Play slower: atempo rate < 1. A 2× slowdown is 0.5.
    audio_splice.stretch_by_rate(clip, slow, 1.0 / rate)
    return slow


def take_audio(
    audio_uuid: str, session_uuid: str, *, scaled: bool = False, untrimmed: bool = False
) -> Path:
    record = staging.read(audio_uuid, session_uuid)
    if scaled:
        trimmed = staging.trimmed_path(audio_uuid, session_uuid)
        if not trimmed.is_file():
            _write_trimmed_audio(record)
            trimmed = staging.trimmed_path(audio_uuid, session_uuid)
        if not trimmed.is_file():
            raise EditError("Record a take first.")
        if record.window_seconds <= 0:
            raise EditError("Transcribe the take before hearing it at the speed it will go.")
        target = staging.scaled_path(audio_uuid, session_uuid)
        source_len = formats.duration_seconds(trimmed)
        audio_splice.stretch_to_length(trimmed, target, source_len, record.window_seconds)
        return target
    if not untrimmed:
        selected = staging.selected_path(audio_uuid, session_uuid)
        if selected.is_file():
            return selected
    path = staging.untrimmed_path(audio_uuid, session_uuid)
    if not path.is_file():
        raise EditError("Record a take first.")
    return path


def accept(audio_uuid: str, session_uuid: str) -> AcceptOut:
    record = staging.read(audio_uuid, session_uuid)
    take = staging.read_take_events(audio_uuid, session_uuid)
    if not take:
        raise EditError("Transcribe the take before accepting it.")
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise EditError("This piece has not been transcribed yet.")
    if record.composing:
        return _accept_passage(record, take, stored)

    original_duration = stored.duration_seconds
    factor = record.factor
    prepared = preview_mod.prepared_take(take, record)
    if record.slowdown is None:
        factor = preview_mod.measured_factor(record, prepared)
        record.factor = factor
    result, removed, arriving = splice_events(
        stored.events,
        prepared,
        start_seconds=record.start_seconds,
        end_seconds=record.end_seconds,
        factor=factor,
        frame_ms=record.frame_ms,
    )
    dropped = count_marks_in_window(
        pipeline.load_rhythm(audio_uuid), record.start_frame, record.end_frame
    )
    history.snapshot_current(audio_uuid)
    pipeline.save_note_events(audio_uuid, result, original_duration, stored.title)
    saved_after = pipeline.load_note_events(audio_uuid)
    if saved_after is None or abs(saved_after.duration_seconds - original_duration) > 1e-6:
        raise AssertionError("Range editing must not change the piece's length.")
    rhythm = pipeline.load_rhythm(audio_uuid)
    if rhythm is not None:
        pipeline.save_rhythm(
            audio_uuid, drop_marks_in_window(rhythm, record.start_frame, record.end_frame)
        )

    audio_spliced = False
    audio_mismatch = False
    if record.splice_audio:
        try:
            _splice_audio(record)
            audio_spliced = True
        except (FfmpegMissing, ConversionFailed, ValueError, FileNotFoundError, OSError):
            history.add_mismatch(audio_uuid, record.start_seconds, record.end_seconds)
            audio_mismatch = True
    else:
        history.add_mismatch(audio_uuid, record.start_seconds, record.end_seconds)
        audio_mismatch = True

    version = history.current_version(audio_uuid)
    staging.delete(audio_uuid, session_uuid)
    return AcceptOut(
        version=version,
        placement="replace",
        duration_seconds=original_duration,
        notes_removed=len(removed),
        notes_arriving=len(arriving),
        dropped_marks=dropped,
        moved_marks=MovedMarks(),
        notes_moved=0,
        audio_spliced=audio_spliced,
        audio_mismatch=audio_mismatch,
    )


def _accept_passage(
    record: SessionRecord, take: list[NoteEvent], stored: pipeline.TranscribedEvents
) -> AcceptOut:
    """Put a composed passage into the piece, and move everything after it (Epic 13).

    The one operation in the product that changes a piece's length. Notes and marks move in the
    same write, so there is never a moment where a fingering points at a note that is no longer
    under it, and the caller is told how many of each moved.
    """
    audio_uuid = record.audio_uuid
    prepared = preview_mod.prepared_take(take, record)
    passage_seconds, arriving = compose.passage_bounds(
        prepared,
        at_seconds=record.start_seconds,
        factor=record.factor,
        frame_ms=record.frame_ms,
    )
    if passage_seconds <= 0 or not arriving:
        raise EditError("No notes were found in this take. Trim a different range or record again.")
    result, notes_moved, new_duration = compose.insert_events(
        stored.events,
        arriving,
        at_seconds=record.start_seconds,
        passage_seconds=passage_seconds,
        duration_seconds=stored.duration_seconds,
        placement=record.placement,
        frame_ms=record.frame_ms,
    )

    history.snapshot_current(audio_uuid)
    title = stored.title or store.read_metadata(audio_uuid).alias
    pipeline.save_note_events(audio_uuid, result, new_duration, title)
    saved_after = pipeline.load_note_events(audio_uuid)
    if saved_after is None or abs(saved_after.duration_seconds - new_duration) > 1e-6:
        raise AssertionError("A placed passage must leave the piece the length it was measured at.")

    shifted, moved_marks = compose.shift_marks(
        pipeline.load_rhythm(audio_uuid),
        at_seconds=record.start_seconds,
        passage_seconds=passage_seconds,
        placement=record.placement,
    )
    if shifted is not None and moved_marks.total:
        pipeline.save_rhythm(audio_uuid, shifted)

    audio_spliced = False
    audio_mismatch = False
    if record.splice_audio:
        try:
            _place_audio(record, passage_seconds)
            audio_spliced = True
        except (FfmpegMissing, ConversionFailed, ValueError, FileNotFoundError, OSError):
            history.add_mismatch(
                audio_uuid, record.start_seconds, record.start_seconds + passage_seconds
            )
            audio_mismatch = True
    else:
        history.add_mismatch(
            audio_uuid, record.start_seconds, record.start_seconds + passage_seconds
        )
        audio_mismatch = True

    store.update(audio_uuid, duration_seconds=new_duration)
    version = history.current_version(audio_uuid)
    staging.delete(audio_uuid, record.session_uuid)
    return AcceptOut(
        version=version,
        placement=record.placement,
        duration_seconds=new_duration,
        notes_removed=0,
        notes_arriving=len(arriving),
        dropped_marks=DroppedMarks(),
        moved_marks=moved_marks,
        notes_moved=notes_moved,
        audio_spliced=audio_spliced,
        audio_mismatch=audio_mismatch,
    )


def _place_audio(record: SessionRecord, passage_seconds: float) -> None:
    """Grow the recording by the passage, so what is heard still matches what is drawn.

    The take is stretched to the passage's length first — a take played twice as slowly is written
    back at the speed the sheet says it goes — and then written into the recording at the moment
    the notes went in. A piece with no recording yet gets one here: its first passage is what
    creates it.
    """
    _write_trimmed_audio(record)
    trimmed = staging.trimmed_path(record.audio_uuid, record.session_uuid)
    if not trimmed.is_file():
        raise FileNotFoundError("trimmed take")
    stretched = staging.scaled_path(record.audio_uuid, record.session_uuid)
    source_len = formats.duration_seconds(trimmed)
    audio_splice.stretch_to_length(trimmed, stretched, source_len, passage_seconds)

    entry = store.get(record.audio_uuid)
    tmp = entry.directory / "normalized.grown.wav"
    audio_splice.insert_wav(
        entry.normalized_path,
        stretched,
        tmp,
        record.start_seconds,
        passage_seconds,
        keep_tail=(record.placement == "insert"),
    )
    tmp.replace(entry.normalized_path)
    if entry.waveform_path.is_file():
        entry.waveform_path.unlink()
    # Playback serves the original. A composed piece has no original until now, and a piece being
    # composed has no original worth keeping: the recording is the passages, in order.
    original = entry.original_path
    if original is not None and original.is_file() and original.suffix.lower() != ".wav":
        original.unlink()
    shutil.copy2(entry.normalized_path, entry.directory / "original.wav")
    store.update(record.audio_uuid, format="wav")


def _splice_audio(record: SessionRecord) -> None:
    _write_trimmed_audio(record)
    trimmed = staging.trimmed_path(record.audio_uuid, record.session_uuid)
    if not trimmed.is_file():
        raise FileNotFoundError("trimmed take")
    stretched = staging.scaled_path(record.audio_uuid, record.session_uuid)
    source_len = formats.duration_seconds(trimmed)
    audio_splice.stretch_to_length(trimmed, stretched, source_len, record.window_seconds)
    entry = store.get(record.audio_uuid)
    if not entry.has_normalized():
        raise FileNotFoundError("normalized.wav")
    tmp = entry.directory / "normalized.spliced.wav"
    audio_splice.splice_wav(
        entry.normalized_path,
        stretched,
        tmp,
        record.start_seconds,
        record.end_seconds,
    )
    tmp.replace(entry.normalized_path)
    if entry.waveform_path.is_file():
        entry.waveform_path.unlink()
    original = entry.original_path
    if original is not None and original.is_file():
        # The original is what playback serves. Write the spliced wav over it as wav;
        # ingest already treats wav as a first-class original.
        spliced_original = entry.directory / "original.wav"
        shutil.copy2(entry.normalized_path, spliced_original)
        if original.resolve() != spliced_original.resolve():
            original.unlink()
            store.update(record.audio_uuid, format="wav")
