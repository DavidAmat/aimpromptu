"""`/matrix` — the transcription pipeline and matrix retrieval (Epics 2, 4, 7)."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.matrix.convert import to_dense_envelope, to_sparse_envelope
from aitu_backend.matrix.granularity import upsample_to
from aitu_backend.matrix.hands import combine_hands
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.ops import EditError, fit_to_width, set_cell, transpose
from aitu_backend.matrix.validator import normalize
from aitu_backend.schemas.matrix import (
    Granularity,
    MatrixProcessingStep,
    PianoMatrixEnvelope,
)
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage.matrix_store import save_matrix
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    EngineUnavailable,
    available_engines,
)

router = APIRouter(prefix="/matrix", tags=["matrix"])


class TranscribeRequest(BaseModel):
    """Body of `POST /matrix/transcribe`."""

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    tempo_bpm: float = Field(60.0, alias="tempoBpm", gt=0)
    granularity: Granularity = Granularity.SEMICORCHEA
    #: Restrict to a range of the source audio, in seconds.
    start_seconds: float | None = Field(None, alias="startSeconds", ge=0)
    end_seconds: float | None = Field(None, alias="endSeconds", gt=0)
    engine: str = DEFAULT_ENGINE
    #: Force a re-transcription even when a raw matrix already exists.
    force: bool = False


class RecomputeRequest(BaseModel):
    """Body of `POST /matrix/recompute` — steps 3-5 only, from the raw matrix."""

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    tempo_bpm: float = Field(60.0, alias="tempoBpm", gt=0)
    granularity: Granularity = Granularity.SEMICORCHEA


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


def _audio_or_404(audio_uuid: str) -> None:
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")


@router.get("/engines")
def list_engines() -> dict[str, bool]:
    """Which transcription engines can actually run here.

    `false` means the package is not installed — the UI can grey the option out
    instead of letting the user pick something that will fail.
    """
    return available_engines()


@router.post("/transcribe", response_model=JobHandle, response_model_by_alias=True, status_code=202)
def transcribe(request: TranscribeRequest) -> JobHandle:
    """Start the pipeline in the background and return a job id.

    Transcription takes tens of seconds, so this answers `202` immediately;
    follow `GET /matrix/progress/{jobId}` for the stream.
    """
    _audio_or_404(request.audio_uuid)

    def work(reporter: Any) -> Any:
        return pipeline.run_pipeline(
            request.audio_uuid,
            request.tempo_bpm,
            request.granularity,
            engine=request.engine,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            reuse_raw=not request.force,
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


@router.post("/recompute", response_model=PianoMatrixEnvelope, response_model_by_alias=True)
def recompute(request: RecomputeRequest) -> PianoMatrixEnvelope:
    """Recompute collapsed/clean/two-hands from the stored raw matrix.

    Synchronous on purpose: this is pure numpy and has to feel instant, so an
    async job would add more latency than it saves.
    """
    _audio_or_404(request.audio_uuid)
    try:
        result = pipeline.recompute(request.audio_uuid, request.tempo_bpm, request.granularity)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.clean.to_envelope()


@router.get("/{audio_uuid}", response_model=PianoMatrixEnvelope, response_model_by_alias=True)
def get_matrix(
    audio_uuid: str,
    step: MatrixProcessingStep = MatrixProcessingStep.CLEAN,
    granularity: Granularity = Granularity.SEMICORCHEA,
    tempo_bpm: float = 60.0,
    sparse: bool = True,
) -> PianoMatrixEnvelope:
    """One processing step of a stored matrix.

    Reads from disk when that step and granularity were already computed, and
    recomputes from the raw matrix otherwise — so the caller never has to know
    which artifacts exist.
    """
    _audio_or_404(audio_uuid)
    if not pipeline.has_raw(audio_uuid):
        raise HTTPException(
            status_code=409,
            detail=f"Audio {audio_uuid} has not been transcribed yet. POST /matrix/transcribe first.",
        )

    result = pipeline.recompute(audio_uuid, tempo_bpm, granularity)
    if step is MatrixProcessingStep.TWO_HANDS:
        envelope = PianoMatrixEnvelope(
            tempo_bpm=tempo_bpm,
            time_step_seconds=result.hands.right.time_step_seconds,
            granularity=granularity,
            matrix_processing_step=step,
            sparse=True,
            r_matrix=result.hands.right.to_coo_payload(),
            l_matrix=result.hands.left.to_coo_payload(),
        )
    else:
        envelope = result.step(step).to_envelope()

    return envelope if sparse else to_dense_envelope(envelope)


@router.get("/{audio_uuid}/export")
def export_matrix(
    audio_uuid: str,
    step: MatrixProcessingStep = MatrixProcessingStep.CLEAN,
    granularity: Granularity = Granularity.SEMICORCHEA,
    tempo_bpm: float = 60.0,
    sparse: bool = True,
) -> Response:
    """Download one step as a self-contained JSON file.

    `sparse=true` gives the COO payload, `sparse=false` the full dense grid with
    `columnHeaders` (88 key names, EN + ES) and `rowTimestamps`. Either way the
    envelope carries everything needed to reopen it in another session — which
    is what `POST /matrix/import` consumes.

    A download rather than a plain body: it answers with `Content-Disposition`
    so the browser saves it under a name that says what it is.
    """
    envelope = get_matrix(audio_uuid, step, granularity, tempo_bpm, sparse)
    alias = store.read_metadata(audio_uuid).alias
    filename = f"{slugify_or_uuid(alias, audio_uuid)}_{step.value}_{granularity.value}"
    filename += "_sparse.json" if sparse else "_dense.json"

    return Response(
        content=envelope.model_dump_json(by_alias=True, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class ImportedMatrix(BaseModel):
    """What an import reports back."""

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    granularity: Granularity
    matrix_processing_step: MatrixProcessingStep = Field(..., alias="matrixProcessingStep")
    frame_count: int = Field(..., alias="frameCount")
    #: Cells the validator had to correct on the way in.
    normalized_cells: int = Field(0, alias="normalizedCells")


class MatrixCellEdit(BaseModel):
    """One staged grid operation. Coordinates use the dense UI orientation."""

    frame: int = Field(..., ge=0)
    key: int = Field(..., ge=0, lt=88)
    value: Literal[-1, 0, 1]


class EditMatrixRequest(BaseModel):
    """Preview or save a sequence of validator-backed cell edits."""

    model_config = ConfigDict(populate_by_name=True)

    tempo_bpm: float = Field(60.0, alias="tempoBpm", gt=0)
    granularity: Granularity = Granularity.SEMICORCHEA
    edits: list[MatrixCellEdit]
    persist: bool = False


class EditedMatrix(BaseModel):
    """The normalized preview plus whether it replaced the working source."""

    model_config = ConfigDict(populate_by_name=True)

    envelope: PianoMatrixEnvelope
    persisted: bool
    edit_count: int = Field(..., alias="editCount")


@router.post(
    "/import", response_model=ImportedMatrix, response_model_by_alias=True, status_code=201
)
def import_matrix(envelope: PianoMatrixEnvelope) -> ImportedMatrix:
    """Load a matrix JSON produced by the export endpoint.

    Accepts either form — the envelope's `sparse` flag says which. The matrix is
    **normalized** on the way in (Task 2.1.2): a hand-edited file can easily
    contain a sustain with no onset, and promoting it to an onset is a better
    answer than refusing the whole import.

    The result is stored under a synthetic audio uuid so every Playground tab
    can read it exactly like a transcription — there is no audio behind it, so
    only the imported step is available, not the whole pipeline.
    """
    matrix = _matrix_from_envelope(envelope)
    normalized = normalize(matrix)
    changed = int((normalized.grid != matrix.grid).sum())

    entry = store.create(
        alias=envelope.title or "Imported matrix",
        source=AudioSource.UPLOAD,
        extension="json",
    )
    path = pipeline.derived_path(entry.uuid, envelope.matrix_processing_step, envelope.granularity)
    save_matrix(path, normalized.to_coo_payload())
    # Imports have no raw matrix behind them, so the imported step doubles as
    # the source: recompute would otherwise have nothing to work from.
    save_matrix(pipeline.raw_path(entry.uuid), normalized.to_coo_payload())

    return ImportedMatrix(
        audio_uuid=entry.uuid,
        granularity=envelope.granularity,
        matrix_processing_step=envelope.matrix_processing_step,
        frame_count=normalized.frame_count,
        normalized_cells=changed,
    )


@router.post(
    "/{audio_uuid}/edit",
    response_model=EditedMatrix,
    response_model_by_alias=True,
)
def edit_matrix(audio_uuid: str, request: EditMatrixRequest) -> EditedMatrix:
    """Validate staged edits against the clean working matrix, then optionally save.

    Preview calls are intentionally stateless: the frontend sends its complete
    staged edit list each time. A sustain with no preceding sound therefore
    fails immediately with the same domain message as the matrix primitive.

    Saving expands the edited view back to the canonical raw fusa resolution.
    This is lossy when the user edits a coarser view, which is expected: saving
    says that view is now the musical truth. The first pre-edit raw matrix is
    retained as ``raw_before_edit.npz``.
    """
    _audio_or_404(audio_uuid)
    if not pipeline.has_raw(audio_uuid):
        raise HTTPException(status_code=409, detail="This audio has not been transcribed yet")

    result = pipeline.recompute(audio_uuid, request.tempo_bpm, request.granularity)
    edited = result.clean
    try:
        for change in request.edits:
            edited = set_cell(edited, change.key, change.frame, change.value)
    except EditError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    edited = normalize(edited)
    if request.persist:
        raw = upsample_to(
            edited.with_grid(
                edited.grid,
                processing_step=MatrixProcessingStep.RAW,
            ),
            Granularity.FUSA,
        )
        fitted = fit_to_width(raw, result.raw.frame_count)
        raw = fitted.with_grid(
            fitted.grid,
            processing_step=MatrixProcessingStep.RAW,
        )
        saved = pipeline.persist_edited_raw(
            audio_uuid,
            raw,
            request.tempo_bpm,
            request.granularity,
        )
        edited = saved.clean

    return EditedMatrix(
        envelope=to_dense_envelope(edited.to_envelope()),
        persisted=request.persist,
        edit_count=len(request.edits),
    )


def _matrix_from_envelope(envelope: PianoMatrixEnvelope) -> PianoMatrix:
    """One-hand matrices load directly; two-hands are merged for storage."""
    if envelope.two_hands:
        sparse_envelope = to_sparse_envelope(envelope)
        if sparse_envelope.r_matrix is None or sparse_envelope.l_matrix is None:
            raise HTTPException(status_code=422, detail="A two-hands import needs both hands")
        right = PianoMatrix.from_coo_payload(
            sparse_envelope.r_matrix,
            granularity=envelope.granularity,
            tempo_bpm=envelope.tempo_bpm,
            processing_step=envelope.matrix_processing_step,
        )
        left = PianoMatrix.from_coo_payload(
            sparse_envelope.l_matrix,
            granularity=envelope.granularity,
            tempo_bpm=envelope.tempo_bpm,
            processing_step=envelope.matrix_processing_step,
        )
        return combine_hands(right, left)
    try:
        return PianoMatrix.from_envelope(envelope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def slugify_or_uuid(alias: str, audio_uuid: str) -> str:
    """A filesystem-safe stem for a download, falling back to the uuid."""
    from aitu_backend.schemas.naming import slugify  # noqa: PLC0415

    try:
        return slugify(alias)
    except ValueError:
        return audio_uuid[:8]


@router.post(
    "/{audio_uuid}/transpose", response_model=PianoMatrixEnvelope, response_model_by_alias=True
)
def transpose_matrix(
    audio_uuid: str,
    semitones: int,
    granularity: Granularity = Granularity.SEMICORCHEA,
    tempo_bpm: float = 60.0,
) -> PianoMatrixEnvelope:
    """Shift every row by `semitones`, clamped to the 88-key range."""
    _audio_or_404(audio_uuid)
    if not pipeline.has_raw(audio_uuid):
        raise HTTPException(status_code=409, detail="This audio has not been transcribed yet")
    result = pipeline.recompute(audio_uuid, tempo_bpm, granularity)
    return transpose(result.clean, semitones).matrix.to_envelope()


def _engine_error(exc: EngineUnavailable) -> HTTPException:  # pragma: no cover - helper
    return HTTPException(status_code=503, detail=str(exc))


def _not_found(exc: AudioNotFound) -> HTTPException:  # pragma: no cover - helper
    return HTTPException(status_code=404, detail=str(exc))
