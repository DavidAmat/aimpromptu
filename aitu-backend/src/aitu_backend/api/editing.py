"""`/audio/{uuid}/edits` — staged range editing (Epic 11).

A disposable session holds the take. Accept splices it into exactly the window
it replaces. Cancel deletes the folder and nothing else. The existing Frames
toolbox (key, octave) is not involved: this router only serves the Re-record tab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.editing.session import EditError, accept, cancel, confirmation, load
from aitu_backend.editing.session import patch as patch_session
from aitu_backend.editing.session import (
    preview,
    start,
    store_take,
    take_audio,
    take_peaks,
    to_out,
    transcribe_take,
    window_audio,
)
from aitu_backend.schemas.editing import (
    AcceptOut,
    ConfirmationOut,
    EditSessionOut,
    PatchEditRequest,
    PreviewOut,
    StartEditRequest,
)
from aitu_backend.schemas.rhythm import SpeedChange
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.storage import staging
from aitu_backend.storage.staging import SessionNotFound
from aitu_backend.transcription import jobs

router = APIRouter(prefix="/audio", tags=["edits"])


class JobHandle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str


class PreviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    anchor_figure: FigureName = Field(FigureName.NEGRA, alias="anchorFigure")
    anchor_ms: float | None = Field(None, alias="anchorMs", gt=0)
    speed_changes: list[SpeedChange] = Field(default_factory=list, alias="speedChanges")


class TakeWaveformOut(BaseModel):
    """Min/max peaks of the untrimmed take, matching `/audio/{uuid}/waveform`."""

    model_config = ConfigDict(populate_by_name=True)

    points: int
    min: list[float]
    max: list[float]
    duration_seconds: float = Field(..., alias="durationSeconds")
    sample_rate: int = Field(..., alias="sampleRate")


def _found(audio_uuid: str) -> None:
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SessionNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, EditError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, FfmpegMissing):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ConversionFailed):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, AudioNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    raise exc


@router.post(
    "/{audio_uuid}/edits",
    response_model=EditSessionOut,
    response_model_by_alias=True,
    status_code=201,
)
def start_edit(audio_uuid: str, body: StartEditRequest) -> EditSessionOut:
    """Open a disposable session for the marked window. Nothing is written to the piece."""
    _found(audio_uuid)
    try:
        record = start(
            audio_uuid,
            start_frame=body.start_frame,
            end_frame=body.end_frame,
            start_seconds=body.start_seconds,
            end_seconds=body.end_seconds,
            frame_ms=body.frame_ms,
            slowdown=body.slowdown,
            splice_audio=body.splice_audio,
            click_interval_ms=body.click_interval_ms,
        )
    except (EditError, FileNotFoundError, ValueError) as exc:
        raise _map_error(exc) from exc
    return to_out(record)


@router.get(
    "/{audio_uuid}/edits/{session_uuid}",
    response_model=EditSessionOut,
    response_model_by_alias=True,
)
def get_edit(audio_uuid: str, session_uuid: str) -> EditSessionOut:
    _found(audio_uuid)
    try:
        return to_out(load(audio_uuid, session_uuid))
    except SessionNotFound as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/{audio_uuid}/edits/{session_uuid}",
    response_model=EditSessionOut,
    response_model_by_alias=True,
)
def patch_edit(audio_uuid: str, session_uuid: str, body: PatchEditRequest) -> EditSessionOut:
    """Change speed or extend the trim without recording again."""
    _found(audio_uuid)
    try:
        record = patch_session(
            audio_uuid,
            session_uuid,
            slowdown=body.slowdown,
            fit=body.fit,
            splice_audio=body.splice_audio,
            click_interval_ms=body.click_interval_ms,
            trim_length_seconds=body.trim_length_seconds,
            take_start_seconds=body.take_start_seconds,
            take_end_seconds=body.take_end_seconds,
        )
    except (SessionNotFound, EditError, ValueError) as exc:
        raise _map_error(exc) from exc
    return to_out(record)


@router.delete("/{audio_uuid}/edits/{session_uuid}")
def cancel_edit(audio_uuid: str, session_uuid: str) -> dict[str, str]:
    """Delete the session folder. The piece is untouched."""
    _found(audio_uuid)
    try:
        cancel(audio_uuid, session_uuid)
    except SessionNotFound as exc:
        raise _map_error(exc) from exc
    return {"status": "cancelled", "sessionUuid": session_uuid}


@router.post(
    "/{audio_uuid}/edits/{session_uuid}/take",
    response_model=EditSessionOut,
    response_model_by_alias=True,
)
def upload_take(
    audio_uuid: str,
    session_uuid: str,
    file: Annotated[UploadFile, File()],
) -> EditSessionOut:
    """Store the untrimmed take. Transcription is a separate step."""
    _found(audio_uuid)
    if not file.filename:
        raise HTTPException(status_code=422, detail="The uploaded file has no name")
    try:
        load(audio_uuid, session_uuid)
        suffix = Path(file.filename).suffix or ".webm"
        dest = staging.session_dir(audio_uuid, session_uuid) / f"upload{suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as handle:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        record = store_take(audio_uuid, session_uuid, dest)
    except (SessionNotFound, EditError, FfmpegMissing, ConversionFailed, ValueError) as exc:
        raise _map_error(exc) from exc
    return to_out(record)


@router.post(
    "/{audio_uuid}/edits/{session_uuid}/transcribe",
    response_model=JobHandle,
    response_model_by_alias=True,
    status_code=202,
)
def transcribe_edit(audio_uuid: str, session_uuid: str) -> JobHandle:
    """Transcribe the take as it was played. Never transcribes stretched audio."""
    _found(audio_uuid)
    try:
        load(audio_uuid, session_uuid)
    except SessionNotFound as exc:
        raise _map_error(exc) from exc

    def work(reporter: Any) -> Any:
        return transcribe_take(audio_uuid, session_uuid, reporter=reporter)

    job = jobs.submit(work)
    return JobHandle(job_id=job.id, status=job.status)


@router.post(
    "/{audio_uuid}/edits/{session_uuid}/preview",
    response_model=PreviewOut,
    response_model_by_alias=True,
)
def preview_edit(
    audio_uuid: str,
    session_uuid: str,
    body: PreviewRequest | None = Body(None),
) -> PreviewOut:
    """Scale the already-transcribed take into the window and draw that stretch."""
    _found(audio_uuid)
    request = body or PreviewRequest()
    try:
        return preview(
            audio_uuid,
            session_uuid,
            anchor_figure=request.anchor_figure,
            anchor_ms=request.anchor_ms,
            speed_changes=request.speed_changes,
        )
    except (SessionNotFound, EditError, ValueError) as exc:
        raise _map_error(exc) from exc


@router.get(
    "/{audio_uuid}/edits/{session_uuid}/confirmation",
    response_model=ConfirmationOut,
    response_model_by_alias=True,
)
def confirm_edit(audio_uuid: str, session_uuid: str) -> ConfirmationOut:
    _found(audio_uuid)
    try:
        return confirmation(audio_uuid, session_uuid)
    except SessionNotFound as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{audio_uuid}/edits/{session_uuid}/accept",
    response_model=AcceptOut,
    response_model_by_alias=True,
)
def accept_edit(audio_uuid: str, session_uuid: str) -> AcceptOut:
    """Splice the take into the window and write a new version of the piece."""
    _found(audio_uuid)
    try:
        return accept(audio_uuid, session_uuid)
    except (SessionNotFound, EditError, AssertionError, ValueError) as exc:
        raise _map_error(exc) from exc


@router.get("/{audio_uuid}/edits/{session_uuid}/window")
def get_window_audio(
    audio_uuid: str,
    session_uuid: str,
    slowed: bool = Query(False),
) -> Any:
    """The original window, optionally slowed with pitch preserved."""
    _found(audio_uuid)
    try:
        path = window_audio(audio_uuid, session_uuid, slowed=slowed)
    except (SessionNotFound, EditError, FfmpegMissing, ConversionFailed, ValueError) as exc:
        raise _map_error(exc) from exc
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{audio_uuid}/edits/{session_uuid}/take")
def get_take_audio(
    audio_uuid: str,
    session_uuid: str,
    scaled: bool = Query(False),
    untrimmed: bool = Query(False),
) -> Any:
    """The take as played, or scaled into the window.

    ``untrimmed`` is the full recording, for the review range picker. After a
    range is cut, the default file is that slice.
    """
    _found(audio_uuid)
    try:
        path = take_audio(audio_uuid, session_uuid, scaled=scaled, untrimmed=untrimmed)
    except (SessionNotFound, EditError, FfmpegMissing, ConversionFailed, ValueError) as exc:
        raise _map_error(exc) from exc
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/{audio_uuid}/edits/{session_uuid}/waveform",
    response_model=TakeWaveformOut,
    response_model_by_alias=True,
)
def get_take_waveform(
    audio_uuid: str,
    session_uuid: str,
    points: Annotated[int, Query(ge=1, le=20000)] = 1000,
) -> TakeWaveformOut:
    """Peaks of the recorded take, for the same range picker the Input tab uses."""
    _found(audio_uuid)
    try:
        load(audio_uuid, session_uuid)
        peaks = take_peaks(audio_uuid, session_uuid, points)
    except (SessionNotFound, EditError, ValueError) as exc:
        raise _map_error(exc) from exc
    return TakeWaveformOut.model_validate(peaks.to_dict())
