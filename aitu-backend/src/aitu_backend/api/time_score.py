"""`/time` — the wall-clock pipeline over HTTP: peaks, ladder preview, and the score payload.

Three routes, and they are the three things the user does:

* `GET /time/{audioUuid}/peaks` — show me where the gaps pile up, for one hand or both.
* `POST /time/{audioUuid}/ladder-preview` — if I call *this* peak a negra, what does everything else
  become?
* `GET /time/{audioUuid}/score` — draw it.

Everything is derived from the stored `events.json` on every request. Nothing here is cached and
nothing is written, so re-running a piece at 20 ms instead of 40 is a different query string rather
than a migration (D-01). That costs a second or two on a five-minute piece and buys a system with no
stale state in it.

The routes live under `/time` while the 1.x `/matrix` routes still serve the running app. P4.2 folds
them together.
"""

from __future__ import annotations

from functools import lru_cache
import copy
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.matrix.intervals import intervals_ms
from aitu_backend.matrix.keys import KEY_COUNT, LOWEST_MIDI
from aitu_backend.matrix.ladder import build_ladder, bpm_of, header_label, label_peaks
from aitu_backend.matrix.passages import one_passage, passages_from_boundaries
from aitu_backend.matrix.peaks import Peak, peaks_of
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN
from aitu_backend.notation.trills import MIN_PAIR_REPEATS, detect_trills
from aitu_backend.schemas.rhythm import HiddenNote, SavedRhythm, Trill
from aitu_backend.notation.decorative import decorative_notes
from aitu_backend.schemas.time_matrix import FigureLadder, FigureName, TimeScorePayload
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import (
    TimeHands,
    attack_times_of_hand,
    impose_granularity_and_split,
    to_score_payload,
    trim_to_music,
)

router = APIRouter(prefix="/time", tags=["time"])

HandChoice = Literal["right", "left", "both"]


class PeakOut(BaseModel):
    """One pile of gaps, as the peak plot draws it."""

    model_config = ConfigDict(populate_by_name=True)

    #: Where the pile is centred, in milliseconds. This is the value the user names.
    centre_ms: float = Field(..., alias="centreMs")
    #: The middle gap of the pile. Steadier than the centre when the tail is long.
    median_ms: float = Field(..., alias="medianMs")
    mean_ms: float = Field(..., alias="meanMs")
    #: How many gaps are in it, and what share of all of them that is.
    count: int
    share: float
    #: The pile's edges, so the plot can shade it.
    lo_ms: float = Field(..., alias="loMs")
    hi_ms: float = Field(..., alias="hiMs")


class PeaksResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    hand: HandChoice
    frame_ms: float = Field(..., alias="frameMs")
    #: The stretch measured, in seconds.
    start_seconds: float = Field(..., alias="startSeconds")
    end_seconds: float = Field(..., alias="endSeconds")
    #: How many attacks and how many gaps between them the peaks were found from.
    attack_count: int = Field(..., alias="attackCount")
    gap_count: int = Field(..., alias="gapCount")
    peaks: list[PeakOut]
    #: Set when the gaps look like they came from a grid rather than from playing. See
    #: :func:`_find_peaks`. Plain language, because it is shown to the reader as written.
    warning: str | None = None


class LadderPreviewRequest(BaseModel):
    """ "Call the peak at `anchorMs` a `anchorFigure`, and tell me what follows.\" """

    model_config = ConfigDict(populate_by_name=True)

    anchor_figure: FigureName = Field(FigureName.NEGRA, alias="anchorFigure")
    anchor_ms: float = Field(..., alias="anchorMs", gt=0)
    hand: HandChoice = "right"
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    start_seconds: float = Field(0.0, alias="startSeconds", ge=0)
    end_seconds: float | None = Field(None, alias="endSeconds", gt=0)


class LabelledPeak(BaseModel):
    """What one detected peak becomes under the proposed ladder."""

    model_config = ConfigDict(populate_by_name=True)

    peak: PeakOut
    figure: FigureName
    #: What the ladder says that figure lasts.
    figure_ms: float = Field(..., alias="figureMs")
    #: How far off the fit is, as a percentage of the figure. Small is good.
    percent_off: float = Field(..., alias="percentOff")
    #: Set when the pile is a third of a figure: three of these fill one of those.
    tresillo_of: FigureName | None = Field(None, alias="tresilloOf")
    #: What to write next to the pile, for example ``corchea de tresillo``.
    name: str


class LadderPreviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ladder: FigureLadder
    #: What a passage header would print, for example `negra = 337 ms · ≈178 BPM`.
    header_label: str = Field(..., alias="headerLabel")
    #: The same ladder expressed as a tempo, for readers who think in BPM.
    bpm: float
    labelled: list[LabelledPeak]


def _events_or_error(audio_uuid: str):
    """The recorded notes, or a 409 whose message can be shown to a reader as it is.

    The detail used to name an endpoint and an HTTP verb. It reaches the screen
    unchanged when a piece cannot be drawn, so it now says what happened and what
    to do about it in the words the app uses everywhere else.
    """
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise HTTPException(
            status_code=409,
            detail=pipeline.needs_rederivation(audio_uuid)
            or (
                "This piece has not been transcribed yet, so there are no recorded "
                "notes to write a sheet from. Open Upload / Input, pick it, and press "
                "Run transcription."
            ),
        )
    return stored


def _hands(audio_uuid: str, frame_ms: float) -> TimeHands:
    _events_or_error(audio_uuid)
    # Keyed on the recording's own mtime as well, so re-transcribing a piece drops the cached split
    # instead of serving the previous one for the rest of the process's life.
    stamp = 0.0
    path = pipeline.events_path(audio_uuid)
    if path.exists():
        stamp = path.stat().st_mtime
    return _split_cached(audio_uuid, frame_ms, stamp)


def forget_split_cache() -> None:
    """Drop every cached split.

    Called by anything that writes to a recording. The cache is keyed on the
    events file's mtime as well, so this is belt and braces — but mtime has
    one-second resolution on some filesystems, and two corrections a second
    apart would otherwise serve the first one twice.

    Public because the writer is not always in this module: taking a note off
    the recording is done from `/matrix` as well, and reaching into a private
    name from there would be worse than saying out loud that this is the hook.
    """
    _split_cached.cache_clear()


@lru_cache(maxsize=8)
def _split_cached(audio_uuid: str, frame_ms: float, _stamp: float) -> TimeHands:
    """The hand split for one (piece, column length).

    Cached because it is the expensive half of drawing a sheet — around a second on a five-minute
    piece — and it does not depend on anything the reader is changing. Naming a different peak,
    moving a passage boundary or correcting the hand of a note all rebuild the *printed notes*,
    which is fifty milliseconds, and would otherwise pay for the split again every time.

    The returned object is shared, so every caller must treat it as read-only and copy before
    changing anything. `_with_page_edits` does.
    """
    stored = _events_or_error(audio_uuid)
    # A piece being composed is empty until its first passage lands, and an empty piece is a
    # `durationSeconds` of zero (Epic 13). It still has to draw: one empty column is enough for a
    # pair of staves, and the column is a property of the view, not of the music.
    duration = max(stored.duration_seconds, frame_ms / 1000.0)
    return impose_granularity_and_split(
        stored.events,
        duration,
        frame_ms=frame_ms,
        title=stored.title,
    )


def _gaps(hands: TimeHands, hand: HandChoice, start_seconds: float, end_seconds: float | None):
    """The gaps of one hand, measured between the raw attack times (D-07).

    ``both`` measures each hand on its own and puts the two sets of gaps together, rather than
    measuring the merged stream. Gaps between a right-hand run and a held left-hand chord are not a
    rhythm, and letting them in buries the peak the user is meant to name.
    """
    limit = float("inf") if end_seconds is None else end_seconds
    chosen = ("right", "left") if hand == "both" else (hand,)
    values, attacks = [], 0
    for one in chosen:
        times = [
            second for second in attack_times_of_hand(hands, one) if start_seconds <= second < limit
        ]
        attacks += len(times)
        values.extend(intervals_ms(times).tolist())
    return values, attacks


def _find_peaks(values: list[float], frame_ms: float) -> tuple[list[Peak], str | None]:
    """The piles in a set of gaps, plus a warning if the gaps look like they came from a grid.

    :func:`peaks_of` refuses gaps that are all exact multiples of the frame length, because that is
    the signature of measuring on snapped columns instead of raw times (D-07) and it is silent when
    it happens. A machine-perfect source — a MIDI file, or a piece written by a script — produces
    the same signature honestly, and refusing to draw its plot at all would be the wrong answer to
    a piece that is simply exact. So the measurement goes ahead and the doubt is passed on to the
    reader instead of thrown away.
    """
    if not values:
        # A piece being composed has no gaps yet, and neither has one whose only notes are a single
        # chord. Neither is a failure; the plot is simply empty until there is playing to measure.
        return [], None
    try:
        return peaks_of(values, frame_ms=frame_ms), None
    except ValueError:
        return peaks_of(values, frame_ms=frame_ms, guard=False), (
            "Every gap in this piece is an exact multiple of the column length. That happens with "
            "a MIDI file or anything else played by a machine, and the plot below is still right. "
            "On a real recording it would mean the timings had been rounded before they were "
            "measured, and the piles would not be trustworthy."
        )


def _peak_out(peak: Peak) -> PeakOut:
    return PeakOut(
        centre_ms=peak.centre_ms,
        median_ms=peak.median_ms,
        mean_ms=peak.mean_ms,
        count=peak.mass,
        share=peak.share,
        lo_ms=peak.lo_ms,
        hi_ms=peak.hi_ms,
    )


@router.get("/{audio_uuid}/peaks", response_model=PeaksResponse, response_model_by_alias=True)
def get_peaks(
    audio_uuid: str,
    hand: HandChoice = "right",
    frame_ms: float = Query(DEFAULT_FRAME_MS, alias="frameMs", gt=0),
    start_seconds: float = Query(0.0, alias="startSeconds", ge=0),
    end_seconds: float | None = Query(None, alias="endSeconds", gt=0),
) -> PeaksResponse:
    """Where the gaps between attacks pile up, for the whole piece or for a stretch of it.

    This is the plot the user clicks on. It is measured on the raw recorded times, never on the
    columns (D-07): snapping first splits every pile in two and the user would be asked to name a
    peak that nobody played.
    """
    hands = _hands(audio_uuid, frame_ms)
    values, attacks = _gaps(hands, hand, start_seconds, end_seconds)
    found, warning = _find_peaks(values, frame_ms)
    return PeaksResponse(
        audio_uuid=audio_uuid,
        hand=hand,
        frame_ms=frame_ms,
        start_seconds=start_seconds,
        end_seconds=hands.duration_seconds if end_seconds is None else end_seconds,
        attack_count=attacks,
        gap_count=len(values),
        peaks=[_peak_out(peak) for peak in found],
        warning=warning,
    )


@router.post(
    "/{audio_uuid}/ladder-preview",
    response_model=LadderPreviewResponse,
    response_model_by_alias=True,
)
def preview_ladder(audio_uuid: str, request: LadderPreviewRequest) -> LadderPreviewResponse:
    """Name one peak and see immediately what every other peak becomes (D-10).

    The app never chooses the ladder. Interval statistics fix it only up to a rational factor: a
    beat and twice that beat explain the same gaps equally well. So this shows the consequence of a
    choice and lets the user judge it before committing.
    """
    hands = _hands(audio_uuid, request.frame_ms)
    values, _ = _gaps(hands, request.hand, request.start_seconds, request.end_seconds)
    found, _ = _find_peaks(values, request.frame_ms)
    ladder = build_ladder(request.anchor_figure, request.anchor_ms)
    return LadderPreviewResponse(
        ladder=ladder,
        header_label=header_label(ladder),
        bpm=bpm_of(ladder),
        labelled=[
            LabelledPeak(
                peak=_peak_out(label.peak),
                figure=label.fit.figure,
                figure_ms=label.fit.figure_ms,
                percent_off=label.fit.percent_off,
                tresillo_of=label.tresillo_of,
                name=label.name,
            )
            for label in label_peaks(found, ladder)
        ],
    )


@router.get("/{audio_uuid}/score", response_model=TimeScorePayload, response_model_by_alias=True)
def get_time_score(
    audio_uuid: str,
    anchor_figure: FigureName = Query(FigureName.NEGRA, alias="anchorFigure"),
    anchor_ms: float = Query(..., alias="anchorMs", gt=0),
    frame_ms: float = Query(DEFAULT_FRAME_MS, alias="frameMs", gt=0),
    boundaries: str = Query(
        "",
        description=(
            "Passage boundaries as frame numbers, comma separated, e.g. `250,900`. Each passage "
            "after the first needs its own anchor in `boundaryMs`."
        ),
    ),
    boundary_ms: str = Query("", alias="boundaryMs"),
) -> TimeScorePayload:
    """Everything the renderer draws: the two hand matrices, the passages, and every printed note.

    The figure of each note is decided here and not in the renderer, so the ladder, the proportional
    comparison and the closed vocabulary all live on one side (contract §6).

    With no boundaries the whole piece is one passage on the ladder given. With boundaries, each
    section takes its own anchor from `boundaryMs`, which must have one more entry than
    `boundaries`.
    """
    # Trim first, so the passages the caller drew and the matrix they cover agree on where the
    # piece ends. A recording that runs on after the last note is not part of the sheet.
    hands = trim_to_music(_hands(audio_uuid, frame_ms))
    ladder = build_ladder(anchor_figure, anchor_ms)
    passages = _passages_from_query(hands, ladder, anchor_figure, boundaries, boundary_ms)
    return to_score_payload(hands, ladder, passages=passages, title=hands.right.title)


class HandAssignment(BaseModel):
    """One note, and the hand a person says played it."""

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int = Field(..., alias="startFrame", ge=0)
    row: int = Field(..., ge=0, lt=88)
    hand: Literal["right", "left"]


class HandAssignmentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    notes: list[HandAssignment] = Field(default_factory=list)


class HandAssignmentResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assigned: int
    #: Notes whose column and row matched nothing that was recorded.
    unmatched: int


@router.put(
    "/{audio_uuid}/hands", response_model=HandAssignmentResult, response_model_by_alias=True
)
def put_hands(audio_uuid: str, body: HandAssignmentRequest = Body(...)) -> HandAssignmentResult:
    """Record which hand plays these notes, on the recording itself.

    The hand split is inferred by an algorithm that cannot see the player's hands, and where it is
    wrong a pianist can see it at a glance. Their answer is not an overlay on the drawing: the
    printed length of a note is the gap to the next onset **in the same hand**, so a note that
    changes hands renames its old neighbour, its new neighbour and itself, and a bracket or a beam
    over it may stop making sense. Everything downstream is derived, so the honest place for the
    correction is upstream of all of it — written onto the note event, so the matrix is *built*
    corrected and every consequence falls out by the ordinary path.

    Addressed by column and row because that is what the reader clicked; resolved here to the
    events that landed there, and stored against the raw times those events were played at. The
    correction therefore survives a change of column length: it still holds at 20 ms.
    """
    stored = _events_or_error(audio_uuid)
    hands = trim_to_music(_hands(audio_uuid, body.frame_ms))

    # Column and row back to the raw second the key went down, from the record of where each key's
    # own attack landed. `trim_to_music` may have dropped leading silence, so the lookup is built
    # from the same trimmed hands the reader was looking at.
    seconds_at: dict[tuple[int, int], float] = {}
    for (column, row), seconds in hands.build.event_seconds.items():
        seconds_at[row, column] = seconds

    wanted: dict[tuple[int, float], str] = {}
    unmatched = 0
    for note in body.notes:
        seconds = seconds_at.get((note.row, note.start_frame))
        if seconds is None:
            unmatched += 1
            continue
        wanted[note.row, round(seconds, 4)] = note.hand

    assigned = 0
    for event in stored.events:
        key = (event.midi_note - LOWEST_MIDI, round(event.start, 4))
        hand = wanted.get(key)
        if hand is None or event.hand == hand:
            continue
        event.hand = hand
        assigned += 1

    if assigned:
        pipeline.save_note_events(audio_uuid, stored.events, stored.duration_seconds, stored.title)
        # The split is cached per (piece, column length) and has just stopped being true.
        forget_split_cache()

    return HandAssignmentResult(assigned=assigned, unmatched=unmatched)


class RemovedByColumn(BaseModel):
    """A note to take off the recording, addressed as the sheet drew it."""

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int = Field(..., alias="startFrame", ge=0)
    row: int = Field(..., ge=0, lt=KEY_COUNT)


class RemovalByColumnRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    notes: list[RemovedByColumn] = Field(default_factory=list)
    #: ``False`` puts them back.
    removed: bool = True


class RemovalByColumnResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    changed: int
    #: Notes whose column and row matched nothing that was recorded.
    unmatched: int


@router.put(
    "/{audio_uuid}/removed",
    response_model=RemovalByColumnResult,
    response_model_by_alias=True,
)
def put_removed_by_column(
    audio_uuid: str, body: RemovalByColumnRequest = Body(...)
) -> RemovalByColumnResult:
    """Take notes off the recording, addressed by the column and row the sheet drew.

    The twin of `PUT /matrix/{id}/events/removed`, which the roll uses. Two routes
    because the two screens genuinely hold different things: the roll is looking at
    raw seconds and can say which event it means, while a reader on the sheet has
    clicked a notehead and knows only where it sits on the grid. Resolving the
    second one needs the split's record of where each attack landed, which lives
    here — the same reason `PUT /{id}/hands` is a separate route from anything
    under `/matrix`.

    What it writes is identical, so a note taken off here is gone from the roll
    too, and from the gaps the rhythm is measured from.
    """
    stored = _events_or_error(audio_uuid)

    if body.removed:
        hands = trim_to_music(_hands(audio_uuid, body.frame_ms))
    else:
        # Putting a note back cannot be resolved against the current matrix,
        # because the note is not in it — that is what being removed means. The
        # lookup is built from a split of the recording with every removal undone,
        # which is the numbering the columns in the request were written down at.
        # It costs one extra split, and it is an undo, so it is paid once and only
        # when somebody asks.
        as_played = [event.model_copy(update={"removed": False}) for event in stored.events]
        hands = trim_to_music(
            impose_granularity_and_split(
                as_played,
                stored.duration_seconds,
                frame_ms=body.frame_ms,
                title=stored.title,
            )
        )

    # Column and row back to the raw second the key went down. `trim_to_music` may
    # have dropped leading silence, so the lookup is built from the same trimmed
    # hands the numbering came from.
    seconds_at: dict[tuple[int, int], float] = {}
    for (column, row), seconds in hands.build.event_seconds.items():
        seconds_at[row, column] = seconds

    wanted: set[tuple[int, float]] = set()
    unmatched = 0
    for note in body.notes:
        seconds = seconds_at.get((note.row, note.start_frame))
        if seconds is None:
            unmatched += 1
            continue
        wanted.add((note.row, round(seconds, 4)))

    changed = 0
    for event in stored.events:
        key = (event.midi_note - LOWEST_MIDI, round(event.start, 4))
        if key not in wanted or event.removed == body.removed:
            continue
        event.removed = body.removed
        changed += 1

    if changed:
        pipeline.save_note_events(audio_uuid, stored.events, stored.duration_seconds, stored.title)
        forget_split_cache()

    return RemovalByColumnResult(changed=changed, unmatched=unmatched)


class AddedNote(BaseModel):
    """A note a reader put in from the keyboard panel, addressed as the sheet draws one."""

    model_config = ConfigDict(populate_by_name=True)

    start_frame: int = Field(..., alias="startFrame", ge=0)
    row: int = Field(..., ge=0, lt=KEY_COUNT)
    hand: Literal["right", "left"]
    #: How many columns it is held for. One column is the shortest a note can be.
    length_frames: int = Field(1, alias="lengthFrames", ge=1)


class AddNotesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    notes: list[AddedNote] = Field(default_factory=list)


class AddNotesResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    added: int
    #: Notes refused because that key is already struck in that column.
    duplicate: int


@router.put("/{audio_uuid}/notes", response_model=AddNotesResult, response_model_by_alias=True)
def put_added_notes(audio_uuid: str, body: AddNotesRequest = Body(...)) -> AddNotesResult:
    """Put a note into the recording, addressed by the column and row the sheet draws.

    The opposite of ``PUT /{id}/removed``, and written to the same place for the same reason. A
    reader looking at a chord on the keyboard panel can see that a note is missing from it, and the
    honest fix is to say the key went down — not to hang an extra notehead off the drawing. The
    printed length of a note is the gap to the next onset **in the same hand**, so a note that
    appears out of nowhere renames its neighbour; only a recording can carry that.

    The hand is pinned on the event, exactly as ``PUT /{id}/hands`` pins a correction, so the split
    puts the note on the staff the reader asked for rather than on the one the register suggests.

    A column and a row are all the reader has, so the times are the column's own: a note added at
    f120 starts at 120 column-lengths into the piece. That is only ever a few milliseconds from
    where a played note would have landed, and the whole page is drawn on that grid anyway.

    Refused where that key is already struck in that column, in either hand. The matrix rejects a
    frame where both hands hold one key, and silently merging the two would lose a note.
    """
    stored = _events_or_error(audio_uuid)
    seconds_per_frame = body.frame_ms / 1000

    # What is already struck, so an addition can step aside rather than collide. Read from the raw
    # events: the columns in the request were numbered on the same grid this rounds to.
    struck = {
        (round(event.start / seconds_per_frame), event.midi_note - LOWEST_MIDI)
        for event in stored.events
        if not event.removed
    }

    added = 0
    duplicate = 0
    for note in body.notes:
        if (note.start_frame, note.row) in struck:
            duplicate += 1
            continue
        start = note.start_frame * seconds_per_frame
        stored.events.append(
            NoteEvent(
                midi_note=note.row + LOWEST_MIDI,
                start=start,
                end=start + note.length_frames * seconds_per_frame,
                velocity=64,
                hand=note.hand,
            )
        )
        struck.add((note.start_frame, note.row))
        added += 1

    if added:
        # Ordered by start time, which is what every reader of `events.json` assumes.
        stored.events.sort(key=lambda event: (event.start, event.midi_note))
        pipeline.save_note_events(audio_uuid, stored.events, stored.duration_seconds, stored.title)
        forget_split_cache()

    return AddNotesResult(added=added, duplicate=duplicate)


class ScoreRequest(BaseModel):
    """A sheet to draw: the ladder, the passage boundaries, and the reader's page edits.

    A POST rather than a GET because the page edits are a list as long as the reader likes — a
    marquee over one line of Mr Blue moves forty-eight notes — and that does not belong in a query
    string. The GET stays for a sheet with no edits, which is what the docs and the tests use.
    """

    model_config = ConfigDict(populate_by_name=True)

    anchor_figure: FigureName = Field(FigureName.NEGRA, alias="anchorFigure")
    anchor_ms: float = Field(..., alias="anchorMs", gt=0)
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    boundaries: list[int] = Field(default_factory=list)
    boundary_ms: list[float] = Field(default_factory=list, alias="boundaryMs")
    hidden_notes: list[HiddenNote] = Field(default_factory=list, alias="hiddenNotes")
    #: Stretches the reader accepted as trills. Each prints as one held note with ``tr``
    #: over it, and the alternations under it are left off the page.
    trills: list[Trill] = Field(default_factory=list)
    #: Leave the ornaments off: a sixteenth or shorter printed right before an eighth or
    #: longer in the same hand is taken off the page, and the note before it runs on.
    drop_decorative: bool = Field(False, alias="dropDecorative")


#: How many more times the figures are named after ornaments are taken off. Taking one off
#: lengthens the note before it, which can only ever make that note *longer*, so the second
#: pass finds ornaments whose leaning note was itself an ornament and the third finds nothing.
DECORATIVE_PASSES = 3


def _with_page_edits(hands: TimeHands, hidden: list[HiddenNote]) -> TimeHands:
    """The two hands as the reader has corrected them, for the purpose of naming figures.

    The recording is not touched — this is a copy, made per request, and nothing is written back.
    What it is for is that **the printed figure of a note is the gap to the next onset in the same
    hand** (D-14). Take a note off the page and whatever preceded it now runs on to a later onset,
    which is exactly the point of hiding one the transcriber invented out of a pedal blur: the note
    before it was never that short. Doing this in the browser alone left it named wrong.

    Correcting a *hand* is not here. That one is written onto the note event and the matrix is built
    with it — see `pin_hands`. A hand is a fact about the playing and survives a change of column
    length; hiding a note is a decision about this page.

    Frames are never renumbered here. The hands arrive already trimmed and the caller draws with
    `trim_trailing_silence=False`, so hiding the last note of a piece cannot shift the column
    numbers that every other annotation is keyed by.
    """
    if not hidden:
        return hands

    edited = copy.deepcopy(hands)
    planes = {"right": edited.right, "left": edited.left}

    def run_of(plane, row: int, column: int) -> list[int]:
        """The onset and the sustain cells it owns, as column indices."""
        cells = [column]
        follower = column + 1
        while follower < plane.frame_count and plane.cell(row, follower) == SUSTAIN:
            cells.append(follower)
            follower += 1
        return cells

    def owning_plane(row: int, column: int):
        for plane in planes.values():
            if plane.cell(row, column) == ONSET:
                return plane
        return None

    for note in hidden:
        plane = owning_plane(note.row, note.start_frame)
        if plane is None:
            continue
        for column in run_of(plane, note.row, note.start_frame):
            plane.grid[note.row, column] = SILENCE

    return edited


def _with_trills(hands: TimeHands, trills: list[Trill]) -> TimeHands:
    """Each accepted trill drawn as one held note, on a copy of the hands.

    Same contract as `_with_page_edits` and for the same reason: the printed figure of a note is
    the gap to the next onset in the same hand (D-14), so taking the alternations off the page has
    to happen before any figure is named. Done in the browser the held note would print as a
    semicorchea with a `tr` over it.

    What the copy gets is the run's notes cleared and one note put back: an onset at the run's
    first column on the trill's own row, sounding to the end of what was cleared. The recording is
    untouched, so playback still sounds every alternation (D-29) and dropping the mark restores
    them exactly.
    """
    if not trills:
        return hands

    edited = copy.deepcopy(hands)
    planes = {"right": edited.right, "left": edited.left}

    for trill in trills:
        plane = planes[trill.hand]
        end_frame = min(trill.end_frame, plane.frame_count)
        if trill.start_frame >= end_frame:
            continue

        # Every note whose onset is inside the run, including the cells its sustain owns. A note
        # that started before the run and is still sounding through it is not part of it and stays.
        last_column = end_frame - 1
        for column in range(trill.start_frame, end_frame):
            for row in list(plane.onsets_in_column(column)):
                follower = column
                while follower < plane.frame_count and (
                    follower == column or plane.cell(row, follower) == SUSTAIN
                ):
                    plane.grid[row, follower] = SILENCE
                    last_column = max(last_column, follower)
                    follower += 1

        plane.grid[trill.row, trill.start_frame] = ONSET
        for column in range(trill.start_frame + 1, min(last_column + 1, plane.frame_count)):
            plane.grid[trill.row, column] = SUSTAIN

    return edited


@router.post("/{audio_uuid}/score", response_model=TimeScorePayload, response_model_by_alias=True)
def post_time_score(audio_uuid: str, body: ScoreRequest = Body(...)) -> TimeScorePayload:
    """The sheet, with the reader's page edits folded in before any figure is named.

    Same answer as the GET for a piece with no edits. See `_with_page_edits` for why the edits have
    to be applied on this side rather than in the browser.
    """
    hands = trim_to_music(_hands(audio_uuid, body.frame_ms))
    ladder = build_ladder(body.anchor_figure, body.anchor_ms)
    passages = _passages_from_query(
        hands,
        ladder,
        body.anchor_figure,
        ",".join(str(frame) for frame in body.boundaries),
        ",".join(str(value) for value in body.boundary_ms),
    )
    hidden = list(body.hidden_notes)
    dropped: list[HiddenNote] = []
    # The ornaments are found on the printed figures, and taking one off renames the note before
    # it, so the figures are named again until nothing short is left before something long.
    for _ in range(DECORATIVE_PASSES + 1):
        edited = _with_trills(_with_page_edits(hands, hidden), body.trills)
        payload = to_score_payload(
            edited,
            ladder,
            passages=passages,
            title=hands.right.title,
            # Already trimmed above. Trimming the *edited* hands could cut further — hiding the
            # last note of a piece would shorten it — and that renumbers every column, which
            # every frame-keyed annotation on the page depends on not happening.
            trim_trailing_silence=False,
        )
        if not body.drop_decorative:
            break
        found = [
            note
            for note in decorative_notes(payload.notes)
            if (note.start_frame, note.row) not in {(h.start_frame, h.row) for h in hidden}
        ]
        if not found:
            break
        hidden.extend(found)
        dropped.extend(found)
    payload.decorative_dropped = len(dropped)
    return payload


def _passages_from_query(
    hands: TimeHands,
    ladder: FigureLadder,
    anchor_figure: FigureName,
    boundaries: str,
    boundary_ms: str,
):
    frames = [int(value) for value in boundaries.split(",") if value.strip()]
    if not frames:
        return one_passage(hands.frame_count, ladder)
    anchors = [float(value) for value in boundary_ms.split(",") if value.strip()]
    if len(anchors) != len(frames) + 1:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{len(frames)} boundary/boundaries make {len(frames) + 1} passages, but "
                f"{len(anchors)} value(s) were given in boundaryMs."
            ),
        )
    try:
        return passages_from_boundaries(
            hands.frame_count,
            frames,
            [build_ladder(anchor_figure, value) for value in anchors],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


# --------------------------------------------------------------------------- trills


class TrillSuggestion(BaseModel):
    """One stretch where two notes alternate, offered to the reader."""

    model_config = ConfigDict(populate_by_name=True)

    hand: Literal["right", "left"]
    start_frame: int = Field(..., alias="startFrame")
    end_frame: int = Field(..., alias="endFrame")
    #: The note that would stay on the page: the lower of the two.
    row: int
    #: The note it alternates with.
    other_row: int = Field(..., alias="otherRow")
    #: What the two notes are called, for example ``Si-3`` and ``Do-4``.
    note_name: str = Field(..., alias="noteName")
    other_note_name: str = Field(..., alias="otherNoteName")
    #: How many notes the run holds, and how many times the pair comes round.
    note_count: int = Field(..., alias="noteCount")
    pair_repeats: int = Field(..., alias="pairRepeats")
    #: The middle gap of the run, in milliseconds.
    median_gap_ms: float = Field(..., alias="medianGapMs")
    start_seconds: float = Field(..., alias="startSeconds")
    end_seconds: float = Field(..., alias="endSeconds")


class TrillsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    frame_ms: float = Field(..., alias="frameMs")
    suggestions: list[TrillSuggestion]


@router.get("/{audio_uuid}/trills", response_model=TrillsResponse, response_model_by_alias=True)
def get_trills(
    audio_uuid: str,
    frame_ms: float = Query(DEFAULT_FRAME_MS, alias="frameMs", gt=0),
    min_pair_repeats: int = Query(MIN_PAIR_REPEATS, alias="minPairRepeats", ge=2, le=20),
) -> TrillsResponse:
    """Where two notes are trading places fast enough to be worth one ``tr``.

    A suggestion and nothing more. Nothing is written here and the sheet does not change until the
    reader accepts one: a missed trill costs a reader nothing, and a wrong one hides notes that were
    really played, so the reader has the last word (D-17).
    """
    hands = trim_to_music(_hands(audio_uuid, frame_ms))
    runs = detect_trills(hands, min_pair_repeats=min_pair_repeats)
    key_names = hands.right.key_names()
    seconds_per_frame = frame_ms / 1000.0
    return TrillsResponse(
        audio_uuid=audio_uuid,
        frame_ms=frame_ms,
        suggestions=[
            TrillSuggestion(
                hand=run.hand,
                start_frame=run.start_frame,
                end_frame=run.end_frame,
                row=run.row,
                other_row=run.other_row,
                note_name=key_names[run.row],
                other_note_name=key_names[run.other_row],
                note_count=run.note_count,
                pair_repeats=run.pair_repeats,
                median_gap_ms=run.median_gap_ms,
                start_seconds=run.start_frame * seconds_per_frame,
                end_seconds=run.end_frame * seconds_per_frame,
            )
            for run in runs
        ],
    )


# --------------------------------------------------------------------------- the saved reading


@router.get("/{audio_uuid}/rhythm", response_model=SavedRhythm, response_model_by_alias=True)
def get_rhythm(audio_uuid: str) -> SavedRhythm:
    """The reading saved for this piece: the named ladder, and what the reader changed by hand.

    Everything else about a score is worked out from the recorded notes on each request. This is the
    part that cannot be: nothing in a recording says which pile of gaps is the beat, or where a
    phrase restarts. Answers `404` when nobody has saved one, which is how the screen knows to start
    from the plot instead.
    """
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    saved = pipeline.load_rhythm(audio_uuid)
    if saved is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No rhythm has been saved for {audio_uuid}. Name a gap on the Rhythm tab and "
                "save it."
            ),
        )
    return saved


@router.put("/{audio_uuid}/rhythm", response_model=SavedRhythm, response_model_by_alias=True)
def put_rhythm(audio_uuid: str, rhythm: SavedRhythm) -> SavedRhythm:
    """Save the reading, replacing any earlier one.

    One per piece, because a rhythm is a decision rather than a version: what a reader wants back is
    the last reading they were happy with. Transcribing the audio again clears it, since the column
    numbers in it would then point at a different set of notes.
    """
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    if pipeline.load_note_events(audio_uuid) is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Audio {audio_uuid} has not been transcribed, so there is nothing for a rhythm to "
                "describe."
            ),
        )
    pipeline.save_rhythm(audio_uuid, rhythm)
    return rhythm


@router.delete("/{audio_uuid}/rhythm", status_code=204)
def delete_rhythm(audio_uuid: str) -> None:
    """Forget the saved reading and start again from the plot."""
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    pipeline.clear_rhythm(audio_uuid)
