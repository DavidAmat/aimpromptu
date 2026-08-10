"""`/matrix` — running the model, and reading back what it heard.

Five routes, and between them they are everything the Upload / Input tab needs:
which models are installed, start one, follow it, ask how it went, and read the
notes it produced.

Nothing here returns a grid. A grid is a view of the recorded notes at a chosen
frame length, so it is built while the request is answered and served from
`/time` instead. See :mod:`aitu_backend.api.time_score`.

The routes that used to live here belonged to the tempo-based model: reading one
processing step of a stored matrix, switching granularity, editing cells,
transposing, importing and exporting an envelope. They were deleted in P4.2 with
the Playground tabs that called them.
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.transcription.artifacts import drop_artifacts
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    EngineUnavailable,
    available_engines,
)

router = APIRouter(prefix="/matrix", tags=["matrix"])


class TranscribeRequest(BaseModel):
    """Body of `POST /matrix/transcribe`.

    There is one number here and it is a length of time. It does not decide what
    any note is called: the figures are chosen afterwards, on the Rhythm step,
    from a ladder the user names (D-01, D-09).
    """

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    #: How long one matrix column lasts, in milliseconds.
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs", gt=0)
    #: Restrict to a range of the source audio, in seconds.
    start_seconds: float | None = Field(None, alias="startSeconds", ge=0)
    end_seconds: float | None = Field(None, alias="endSeconds", gt=0)
    engine: str = DEFAULT_ENGINE
    #: Run the model again even when this audio already has its recorded notes.
    force: bool = False


class JobHandle(BaseModel):
    """What `POST /matrix/transcribe` returns immediately."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str


class JobStatus(BaseModel):
    """Polling fallback for clients that cannot hold an SSE connection."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str
    error: str | None = None
    stage: str | None = None
    fraction: float | None = None


class RawNoteEvent(BaseModel):
    """One note exactly as the engine emitted it: seconds, not columns."""

    model_config = ConfigDict(populate_by_name=True)

    midi_note: int = Field(..., alias="midiNote")
    start: float
    end: float
    velocity: int
    #: True when the pipeline discards this note as too short to have been
    #: played. Flagged rather than omitted: this view exists to be audited, and
    #: a filter you cannot see is a filter you cannot check.
    artifact: bool = False
    #: ``12`` or ``24`` when a note that far above was struck alongside this one,
    #: which is the octave-masking signature. Only set on artifacts.
    octave_below: int | None = Field(None, alias="octaveBelow")
    #: Which hand plays it, as the standard split decides at ``frameMs``.
    #:
    #: A label, not a time. The start and end above stay exactly as the engine
    #: reported them; this only says which of the two hands the same note ended
    #: up in, so a view can colour it. ``None`` means the split could not be run
    #: or did not place this note — a view should draw it rather than hide it.
    hand: Literal["right", "left"] | None = None


class RawEvents(BaseModel):
    """The stored transcription in seconds, served verbatim.

    This is the only endpoint upstream of any grid. Every other route hands back
    something whose times have already been snapped, which makes a quantisation
    artifact indistinguishable from a transcription one. A view that has to tell
    those two apart needs the engine's own milliseconds, so it gets them here.
    """

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    duration_seconds: float = Field(..., alias="durationSeconds")
    title: str | None = None
    #: How many of ``events`` carry ``artifact: true``.
    artifact_count: int = Field(0, alias="artifactCount")
    #: Of those, how many sit exactly an octave or two under a struck note.
    octave_phantom_count: int = Field(0, alias="octavePhantomCount")
    #: The column length the ``hand`` labels were decided at. Reported so a view
    #: can say what it is showing; it does not affect any time in ``events``.
    frame_ms: float = Field(DEFAULT_FRAME_MS, alias="frameMs")
    events: list[RawNoteEvent]


def _audio_or_404(audio_uuid: str) -> None:
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")


def _hand_labels(audio_uuid: str, frame_ms: float) -> dict[tuple[int, int], str]:
    """``(row, column) -> "right" | "left"`` for every onset, or an empty map.

    The split runs on a grid and the events do not, so this is a lookup keyed by
    where each onset landed on that grid rather than a value carried on the note.
    Nothing here is stored: the answer is re-derived per request from the same
    ``events.json`` the sheet is drawn from, which is what stops a colour on this
    page from disagreeing with a stem direction on the other one.

    A failure is swallowed on purpose. This is a decoration on an endpoint whose
    job is to show the transcription verbatim, and a piece that cannot be split
    still has notes worth looking at.
    """
    try:
        hands = pipeline.hands_of(audio_uuid, frame_ms=frame_ms)
    except Exception:  # pragma: no cover - the split is advisory here
        return {}
    if hands is None:
        return {}

    labels: dict[tuple[int, int], str] = {}
    for name, matrix in (("left", hands.left), ("right", hands.right)):
        for column in range(matrix.frame_count):
            for row in matrix.onsets_in_column(column):
                labels[(row, column)] = name
    return labels


@router.get("/engines")
def list_engines() -> dict[str, bool]:
    """Which transcription engines can actually run here.

    `false` means the package is not installed, so the UI can grey the option out
    instead of letting the user pick something that will fail.
    """
    return available_engines()


@router.post("/transcribe", response_model=JobHandle, response_model_by_alias=True, status_code=202)
def transcribe(request: TranscribeRequest) -> JobHandle:
    """Start the model in the background and return a job id.

    Transcription takes tens of seconds, so this answers `202` immediately and
    the caller follows `GET /matrix/progress/{jobId}` for the stream.
    """
    _audio_or_404(request.audio_uuid)

    def work(reporter: Any) -> Any:
        return pipeline.run_pipeline(
            request.audio_uuid,
            frame_ms=request.frame_ms,
            engine=request.engine,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            reuse_events=not request.force,
            reporter=reporter,
        )

    job = jobs.submit(work)
    return JobHandle(job_id=job.id, status=job.status)


@router.get("/progress/{job_id}")
def transcription_progress(job_id: str) -> StreamingResponse:
    """SSE stream of the job's progress, ending with a named `done` event."""
    return StreamingResponse(
        jobs.stream(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}", response_model=JobStatus, response_model_by_alias=True)
def job_status(job_id: str) -> JobStatus:
    """Current state of a job, for clients that prefer polling."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job '{job_id}'")
    latest = job.history[-1] if job.history else None
    return JobStatus(
        job_id=job.id,
        status=job.status,
        error=job.error,
        stage=latest.stage if latest else None,
        fraction=latest.fraction if latest else None,
    )


@router.get(
    "/{audio_uuid}/events",
    response_model=RawEvents,
    response_model_by_alias=True,
)
def get_raw_events(
    audio_uuid: str,
    frame_ms: float = Query(DEFAULT_FRAME_MS, alias="frameMs", gt=0),
) -> RawEvents:
    """Every note the model reported, in seconds, with the discards marked.

    The artifact filter is applied here only as a label. Nothing is removed from
    the response, because the point of this route is to show what the rest of the
    system chose not to use.

    ``frameMs`` decides nothing about the times below. It is the column length the
    hand split is run at, and it is here so that a view colouring left against
    right colours it the same way the sheet does.
    """
    _audio_or_404(audio_uuid)
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Audio {audio_uuid} has no stored note events. "
                "Run a transcription (POST /matrix/transcribe) to produce them."
            ),
        )

    report = drop_artifacts(stored.events)
    discarded = {id(dropped.event): dropped for dropped in report.dropped}
    labels = _hand_labels(audio_uuid, frame_ms)
    seconds_per_column = frame_ms / 1000.0

    events = []
    for event in stored.events:
        dropped = discarded.get(id(event))
        row = event.midi_note - LOWEST_MIDI
        column = int(event.start / seconds_per_column)
        # The onset is looked for in the neighbouring columns too. Rounding a
        # boundary onset the other way than the grid builder did would otherwise
        # lose the label, and an unlabelled note is drawn in the wrong colour
        # rather than merely uncoloured.
        hand = (
            event.hand
            or labels.get((row, column))
            or labels.get((row, column + 1))
            or labels.get((row, column - 1))
        )

        events.append(
            RawNoteEvent(
                midi_note=event.midi_note,
                start=event.start,
                end=event.end,
                velocity=event.velocity,
                artifact=dropped is not None,
                octave_below=dropped.octave_below if dropped else None,
                hand=hand if hand in ("right", "left") else None,
            )
        )

    return RawEvents(
        audio_uuid=audio_uuid,
        duration_seconds=stored.duration_seconds,
        title=stored.title,
        artifact_count=len(report.dropped),
        octave_phantom_count=report.octave_phantoms,
        frame_ms=frame_ms,
        events=events,
    )


def _engine_error(exc: EngineUnavailable) -> HTTPException:  # pragma: no cover - helper
    return HTTPException(status_code=503, detail=str(exc))


def _not_found(exc: AudioNotFound) -> HTTPException:  # pragma: no cover - helper
    return HTTPException(status_code=404, detail=str(exc))
