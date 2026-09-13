"""Lifecycle of a staged range-edit session: start, record, preview, accept, cancel."""

from __future__ import annotations

import shutil
from pathlib import Path

from aitu_backend.audio import formats, store
from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing
from aitu_backend.editing import audio_splice, history, preview as preview_mod
from aitu_backend.editing.splice import (
    count_marks_in_window,
    drop_marks_in_window,
    first_onset_seconds,
    last_release_seconds,
    splice_events,
    window_from_frames,
    window_from_seconds,
)
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.progress import BaseProgress
from aitu_backend.schemas.editing import (
    AcceptOut,
    ConfirmationOut,
    EditSessionOut,
    PreviewOut,
)
from aitu_backend.schemas.rhythm import SpeedChange
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.storage import staging
from aitu_backend.storage.staging import SessionRecord
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import TranscriptionEngine


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


def to_out(record: SessionRecord) -> EditSessionOut:
    return EditSessionOut(
        session_uuid=record.session_uuid,
        audio_uuid=record.audio_uuid,
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
    start_frame: int | None = None,
    end_frame: int | None = None,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    frame_ms: float = DEFAULT_FRAME_MS,
    slowdown: int | None = 1,
    splice_audio: bool = True,
    click_interval_ms: float | None = None,
) -> SessionRecord:
    if not store.exists(audio_uuid):
        raise FileNotFoundError(audio_uuid)
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise EditError("This piece has not been transcribed yet.")
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
) -> SessionRecord:
    record = staging.read(audio_uuid, session_uuid)
    if fit:
        record.slowdown = None
        record.trim_length_seconds = None
    elif slowdown is not None:
        record.slowdown = slowdown
        record.factor = _factor(slowdown)
        record.trim_length_seconds = record.window_seconds * float(slowdown)
    if splice_audio is not None:
        record.splice_audio = splice_audio
    if click_interval_ms is not None:
        record.click_interval_ms = click_interval_ms
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
    staging.write(record)
    return record


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
    rhythm = pipeline.load_rhythm(record.audio_uuid)
    dropped = count_marks_in_window(rhythm, record.start_frame, record.end_frame)
    stored = pipeline.load_note_events(record.audio_uuid)
    removed = 0
    if stored is not None:
        removed = sum(
            1 for event in stored.events if record.start_seconds <= event.start < record.end_seconds
        )
    return ConfirmationOut(
        notes_removed=removed if original_count < 0 else original_count,
        notes_arriving=arriving_count,
        dropped_marks=dropped,
        splice_audio=record.splice_audio,
        length_unchanged=True,
        window_seconds=record.window_seconds,
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
        raise EditError(
            "No notes were found in this take. Trim a different range or record again."
        )
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
        duration_seconds=original_duration,
        notes_removed=len(removed),
        notes_arriving=len(arriving),
        dropped_marks=dropped,
        audio_spliced=audio_spliced,
        audio_mismatch=audio_mismatch,
    )


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
