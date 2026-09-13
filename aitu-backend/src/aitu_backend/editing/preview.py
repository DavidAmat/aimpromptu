"""Build a passage-only preview of a scaled take: short sheet plus the take's peak plot."""

from __future__ import annotations

import numpy as np

from aitu_backend.editing.splice import (
    first_onset_seconds,
    last_release_seconds,
    scale_take,
    splice_events,
    trim_take_events,
)
from aitu_backend.matrix.intervals import intervals_ms
from aitu_backend.matrix.ladder import build_ladder, label_peaks
from aitu_backend.matrix.peaks import peaks_of
from aitu_backend.schemas.editing import LabelledPeakOut, PeakOut
from aitu_backend.schemas.rhythm import SpeedChange
from aitu_backend.schemas.time_matrix import FigureName, TimeScorePayload
from aitu_backend.storage.staging import SessionRecord
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import impose_granularity_and_split, to_score_payload


def ladder_ms_at(
    start_frame: int,
    anchor_ms: float,
    speed_changes: list[SpeedChange],
) -> float:
    """The named gap length sounding at this column: the last speed change at or before it."""
    ms = anchor_ms
    for change in sorted(speed_changes, key=lambda item: item.start_frame):
        if change.start_frame <= start_frame:
            ms = change.anchor_ms
    return ms


def prepared_take(events: list[NoteEvent], session: SessionRecord) -> list[NoteEvent]:
    """Events of the take, from first onset, clipped to the trim (or to the last note if Fit)."""
    onset = session.first_onset_seconds
    if onset is None:
        onset = first_onset_seconds(events) or 0.0
    length = session.trim_length_seconds
    if session.slowdown is None:
        length = None
    return trim_take_events(events, first_onset=onset, length_seconds=length)


def take_length_seconds(prepared: list[NoteEvent]) -> float:
    end = last_release_seconds(prepared)
    return float(end) if end is not None else 0.0


def measured_factor(session: SessionRecord, prepared: list[NoteEvent]) -> float:
    if session.slowdown is None:
        length = take_length_seconds(prepared)
        if length <= 0:
            raise ValueError("A take with no sounding notes cannot be fitted to the window")
        return session.window_seconds / length
    return 1.0 / float(session.slowdown)


def scaled_take(events: list[NoteEvent], session: SessionRecord, factor: float) -> list[NoteEvent]:
    prepared = prepared_take(events, session)
    return scale_take(
        prepared,
        factor=factor,
        start_seconds=0.0,
        end_seconds=session.window_seconds,
        frame_ms=session.frame_ms,
    )


def passage_score(
    original: list[NoteEvent],
    duration_seconds: float,
    take: list[NoteEvent],
    session: SessionRecord,
    factor: float,
    *,
    anchor_figure: FigureName,
    anchor_ms: float,
    title: str | None,
) -> TimeScorePayload:
    """Redraw only the marked stretch, with the take's notes already scaled into it."""
    prepared = prepared_take(take, session)
    spliced, _, _ = splice_events(
        original,
        prepared,
        start_seconds=session.start_seconds,
        end_seconds=session.end_seconds,
        factor=factor,
        frame_ms=session.frame_ms,
    )
    windowed = [
        event.model_copy(
            update={
                "start": event.start - session.start_seconds,
                "end": min(event.end, session.end_seconds) - session.start_seconds,
            }
        )
        for event in spliced
        if event.start < session.end_seconds and event.end > session.start_seconds
    ]
    windowed = [event for event in windowed if event.end > event.start]
    hands = impose_granularity_and_split(
        windowed,
        session.window_seconds,
        frame_ms=session.frame_ms,
        title=title,
    )
    ladder = build_ladder(anchor_figure, anchor_ms)
    return to_score_payload(
        hands,
        ladder,
        title=title,
        duration_seconds=session.window_seconds,
        trim_trailing_silence=False,
    )


def take_peaks(
    scaled: list[NoteEvent], frame_ms: float
) -> tuple[list[PeakOut], list[LabelledPeakOut]]:
    """Peak plot of the scaled take. A wrong speed is obvious here: every pile sits one step off."""
    if len(scaled) < 2:
        return [], []
    attacks = np.array(sorted(event.start for event in scaled), dtype=float)
    gaps = intervals_ms(attacks)
    if gaps.size == 0:
        return [], []
    found = peaks_of(gaps, frame_ms=frame_ms, guard=False)
    # Label against a dummy ladder at the first pile so the numbers are readable. The caller
    # relabels with the passage's real ladder.
    return (
        [
            PeakOut(
                centre_ms=peak.centre_ms,
                median_ms=peak.median_ms,
                mean_ms=peak.mean_ms,
                count=peak.mass,
                share=peak.share,
                lo_ms=peak.lo_ms,
                hi_ms=peak.hi_ms,
            )
            for peak in found
        ],
        [],
    )


def labelled_against(
    peaks: list[PeakOut],
    anchor_figure: FigureName,
    anchor_ms: float,
) -> list[LabelledPeakOut]:
    from aitu_backend.matrix.peaks import Peak

    if not peaks:
        return []
    ladder = build_ladder(anchor_figure, anchor_ms)
    native = [
        Peak(
            centre_ms=peak.centre_ms,
            mass=peak.count,
            share=peak.share,
            lo_ms=peak.lo_ms,
            hi_ms=peak.hi_ms,
            mean_ms=peak.mean_ms,
            median_ms=peak.median_ms,
        )
        for peak in peaks
    ]
    return [
        LabelledPeakOut(
            peak=peak,
            figure=label.fit.figure,
            figure_ms=label.fit.figure_ms,
            percent_off=label.fit.percent_off,
            tresillo_of=label.tresillo_of,
            name=label.name,
        )
        for peak, label in zip(peaks, label_peaks(native, ladder), strict=True)
    ]
