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

from fastapi import APIRouter, Body, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend import config
from aitu_backend.auth.dependencies import require_job, require_part
from aitu_backend.transcription import jobs, models, pipeline
from aitu_backend.transcription.artifacts import drop_artifacts
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    ENGINES,
    SELECTABLE_ENGINES,
    EngineUnavailable,
    engine_installed,
    selectable_engines,
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
    #: Kept for older clients. Implementation 08 forces MuScriptor: any other engine is refused.
    engine: str = DEFAULT_ENGINE
    #: Run the model again even when this audio already has its recorded notes.
    force: bool = False


class JobHandle(BaseModel):
    """What `POST /matrix/transcribe` returns immediately."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str


class EngineStatus(BaseModel):
    """`GET /matrix/engine`: the one engine the app uses, and whether it can run now."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    installed: bool
    #: ``cuda`` or ``cpu`` (``AITU_DEVICE``).
    device: str
    #: What is loaded in the process, for example ``muscriptor-large (cuda, float16)``.
    loaded: list[str]
    #: Transcriptions waiting for the GPU behind the running one.
    waiting: int
    #: Why the model could not be loaded at startup, in plain words; ``None`` when it could.
    error: str | None = None


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
    #: True when a reader has said this note was never played. It is still
    #: returned — this route reports what the engine heard, and a correction you
    #: cannot see is a correction you cannot undo.
    removed: bool = False
    #: Which hand plays it, as the standard split decides at ``frameMs``.
    #:
    #: A label, not a time. The start and end above stay exactly as the engine
    #: reported them; this only says which of the two hands the same note ended
    #: up in, so a view can colour it. ``None`` means the split could not be run
    #: or did not place this note — a view should draw it rather than hide it.
    hand: Literal["right", "left"] | None = None
    #: The note's stable id in ``events.json``, which ``PATCH /pieces/{uuid}/notes`` names it by.
    id: int | None = None


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
    #: The notes revision and the hands revision, for a page that edits through
    #: ``PATCH /pieces/{uuid}/notes`` (``baseRevision``, ``baseHandsRevision``).
    revision: int = 0
    hands_revision: int = Field(0, alias="handsRevision")


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
    """The engines the page may offer, and whether each can run here.

    Implementation 08 forces MuScriptor, so this lists only ``muscriptor``. With one entry the
    Input page shows no engine choice; `false` means the package is not installed.
    """
    return selectable_engines()


@router.get("/engine", response_model=EngineStatus, response_model_by_alias=True)
def engine_status() -> EngineStatus:
    """The one engine, whether it is installed and loaded, and why it failed to load, if it did.

    With ``AITU_PRELOAD_ENGINE`` the model loads when the server starts; a missing Hugging Face
    token or licence is then reported here before any job fails.
    """
    return EngineStatus(
        name=DEFAULT_ENGINE,
        installed=engine_installed(DEFAULT_ENGINE),
        device=config.device(),
        loaded=models.loaded(),
        waiting=jobs.waiting_on_gpu(),
        error=models.preload_error(),
    )


def _check_engine(name: str) -> None:
    """MuScriptor only (plan section 9.1): the other engines stay in the code, not in the app."""
    if name in SELECTABLE_ENGINES:
        return
    if name not in ENGINES:
        raise HTTPException(status_code=422, detail=f"Unknown transcription engine '{name}'")
    raise HTTPException(
        status_code=422,
        detail=(
            f"The '{name}' engine is kept in the code but cannot be chosen: every transcription "
            f"uses {DEFAULT_ENGINE}."
        ),
    )


@router.post("/transcribe", response_model=JobHandle, response_model_by_alias=True, status_code=202)
def transcribe(request: TranscribeRequest) -> JobHandle:
    """Start the model in the background and return a job id.

    Transcription takes tens of seconds, so this answers `202` immediately and
    the caller follows `GET /matrix/progress/{jobId}` for the stream: the progress
    ticks, the live notes as `event: chunk` frames (plan section 9.3), and a final
    `event: done` frame with the `revision` of the saved notes.

    One transcription runs on the GPU at a time; a second one waits and its stream
    says so. While a transcription of this audio is waiting or running, this returns
    that job instead of starting another.
    """
    _audio_or_404(request.audio_uuid)
    require_part(request.audio_uuid, write=True)
    _check_engine(request.engine)
    ranged = request.start_seconds is not None and request.end_seconds is not None
    needs_model = request.force or ranged or pipeline.current_events(request.audio_uuid) is None

    def work(reporter: Any) -> Any:
        stored: pipeline.TranscribedEvents | None
        if needs_model:
            stored = pipeline.transcribe_audio(
                request.audio_uuid,
                engine=request.engine,
                start_seconds=request.start_seconds,
                end_seconds=request.end_seconds,
                reporter=reporter,
            )
        else:
            stored = pipeline.load_note_events(request.audio_uuid)
        # The split is computed beside the stream, not before `done`, and kept for the sheet.
        pipeline.warm_split(request.audio_uuid, request.frame_ms)
        return stored

    def describe(stored: Any) -> dict[str, Any]:
        header = stored.header if stored is not None else None
        return {
            "audioUuid": request.audio_uuid,
            "revision": header.notes_revision if header else None,
            "lagCorrectionMs": header.lag_correction_ms if header else None,
            "noteCount": len(stored.events) if stored is not None else 0,
        }

    job = jobs.submit(
        work, gpu=needs_model, key=f"transcribe:{request.audio_uuid}", describe=describe
    )
    return JobHandle(job_id=job.id, status=job.status)


@router.get(
    "/{audio_uuid}/job",
    response_model=JobHandle,
    response_model_by_alias=True,
)
def active_job(audio_uuid: str) -> JobHandle:
    """The transcription of this audio that is waiting or running, so a page opened or reloaded
    during it can follow the stream from the start. 404 when there is none."""
    _audio_or_404(audio_uuid)
    job = jobs.active(f"transcribe:{audio_uuid}")
    if job is None:
        raise HTTPException(status_code=404, detail=f"No transcription of {audio_uuid} is running")
    return JobHandle(job_id=job.id, status=job.status)


@router.get("/progress/{job_id}")
def transcription_progress(
    job_id: str,
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """SSE stream of the job, ending with a named `done` event.

    A page that connects late receives every frame already sent first. An
    ``EventSource`` that reconnects sends ``Last-Event-ID`` and resumes after it.
    """
    after = int(last_event_id) if last_event_id and last_event_id.isdigit() else None
    found = jobs.get(job_id)
    if found is not None:
        require_job(found.owner_id, job_id)
    return StreamingResponse(
        jobs.stream(job_id, after=after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}", response_model=JobStatus, response_model_by_alias=True)
def job_status(job_id: str) -> JobStatus:
    """Current state of a job, for clients that prefer polling."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job '{job_id}'")
    require_job(job.owner_id, job_id)
    latest = job.latest
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

    # The artifact filter is labelled only where the split applies it: not on MuScriptor pieces.
    if pipeline.filters_for(stored.header.engine):
        dropped_events: list[Any] = []
        octave_phantoms = 0
    else:
        report = drop_artifacts(stored.events)
        dropped_events, octave_phantoms = report.dropped, report.octave_phantoms
    discarded = {id(dropped.event): dropped for dropped in dropped_events}
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
                removed=event.removed,
                hand=hand if hand in ("right", "left") else None,
                id=event.id,
            )
        )

    return RawEvents(
        audio_uuid=audio_uuid,
        duration_seconds=stored.duration_seconds,
        title=stored.title,
        artifact_count=len(dropped_events),
        octave_phantom_count=octave_phantoms,
        frame_ms=frame_ms,
        events=events,
        revision=stored.header.notes_revision,
        hands_revision=stored.header.hands_revision,
    )


class RemovedNote(BaseModel):
    """One note to take off the recording, or put back, addressed as it was played."""

    model_config = ConfigDict(populate_by_name=True)

    midi_note: int = Field(..., alias="midiNote", ge=0, le=127)
    #: The event's own start in seconds, as ``GET /events`` reported it. Matched to
    #: four decimal places, which is how the file stores it.
    start: float = Field(..., ge=0)


class RemovalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    notes: list[RemovedNote] = Field(default_factory=list)
    #: ``False`` puts the notes back. The same route both ways, because undoing is
    #: the same decision as doing and should not be a different code path.
    removed: bool = True


class RemovalResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    changed: int
    #: Notes whose pitch and start matched nothing that was recorded.
    unmatched: int


@router.put(
    "/{audio_uuid}/events/removed",
    response_model=RemovalResult,
    response_model_by_alias=True,
)
def put_removed_events(audio_uuid: str, body: RemovalRequest = Body(...)) -> RemovalResult:
    """Take notes off the recording, or put them back.

    A transcriber invents notes — out of a pedal blur, out of an octave ringing
    under a struck key — and the automatic filter only catches the ones short
    enough to be obviously wrong. What is left, a player can see at a glance.

    Their answer is written onto the note event, not kept as a filter on one
    screen, for the reason the hand correction is: the printed length of a note is
    the gap to the next onset, so removing one renames its neighbour. Everything
    downstream is derived from these events, so writing it here is what makes the
    roll, the gap plot and the sheet agree without any of them coordinating.

    Addressed by pitch and start second, which is what the roll was drawing, so the
    correction is independent of any column length.
    """
    _audio_or_404(audio_uuid)
    with pipeline.piece_lock(audio_uuid):
        stored = pipeline.load_note_events(audio_uuid)
        if stored is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Audio {audio_uuid} has no stored note events. "
                    "Run a transcription (POST /matrix/transcribe) to produce them."
                ),
            )

        wanted = {(note.midi_note, round(note.start, 4)) for note in body.notes}
        seen: set[tuple[int, float]] = set()
        changed = 0
        for event in stored.events:
            key = (event.midi_note, round(event.start, 4))
            if key not in wanted:
                continue
            seen.add(key)
            if event.removed == body.removed:
                continue
            event.removed = body.removed
            changed += 1

        if changed:
            # A notes edit (plan section 8.2): the notes and hands revisions go up, and the piano
            # sheet becomes stale, because this page is not the sheet.
            pipeline.save_edit(
                audio_uuid,
                stored.events,
                stored.duration_seconds,
                stored.title,
                before=stored.header,
                notes_changed=True,
                hands_changed=False,
            )

    return RemovalResult(changed=changed, unmatched=len(wanted - seen))


def _engine_error(exc: EngineUnavailable) -> HTTPException:  # pragma: no cover - helper
    return HTTPException(status_code=503, detail=str(exc))


def _not_found(exc: AudioNotFound) -> HTTPException:  # pragma: no cover - helper
    return HTTPException(status_code=404, detail=str(exc))
