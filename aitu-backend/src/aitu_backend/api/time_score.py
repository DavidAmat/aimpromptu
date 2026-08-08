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

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.matrix.intervals import intervals_ms
from aitu_backend.matrix.ladder import build_ladder, bpm_of, header_label, label_peaks
from aitu_backend.matrix.passages import one_passage, passages_from_boundaries
from aitu_backend.matrix.peaks import Peak, peaks_of
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.schemas.time_matrix import FigureLadder, FigureName, TimeScorePayload
from aitu_backend.transcription import pipeline
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
    stored = _events_or_error(audio_uuid)
    return impose_granularity_and_split(
        stored.events,
        stored.duration_seconds,
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
