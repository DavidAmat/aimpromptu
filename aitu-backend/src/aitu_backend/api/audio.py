"""`/audio` — the audio working store (Epic 3, Stories 3.1 and 3.2)."""

from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import formats, ingest, store
from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing, UnsupportedFormat
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource
from aitu_backend.transcription import pipeline

router = APIRouter(prefix="/audio", tags=["audio"])

#: Content types by stored extension, for the streaming response.
_MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "aac": "audio/aac",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "webm": "audio/webm",
    "ogg": "audio/ogg",
}


class AudioRename(BaseModel):
    """Body of `PATCH /audio/{uuid}`."""

    model_config = ConfigDict(populate_by_name=True)

    alias: str | None = None


class AudioTrimRequest(BaseModel):
    """Create a physically trimmed audio child with root-source lineage."""

    model_config = ConfigDict(populate_by_name=True)

    start_seconds: float = Field(..., alias="startSeconds", ge=0)
    end_seconds: float = Field(..., alias="endSeconds", gt=0)
    alias: str | None = None


class WaveformResponse(BaseModel):
    """Min/max peak pairs, one per bucket."""

    model_config = ConfigDict(populate_by_name=True)

    points: int
    min: list[float]
    max: list[float]
    duration_seconds: float = Field(..., alias="durationSeconds")
    sample_rate: int = Field(..., alias="sampleRate")


def _found(audio_uuid: str) -> None:
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")


class AudioEntry(AudioMetadata):
    """One stored audio, plus what the app can currently do with it.

    The two extra fields are computed rather than stored. A screen that lists
    pieces has to say which of them can be drawn, and asking per row would be one
    request per piece; and a stored flag would be one more thing that can go out
    of step with the folder it describes.
    """

    #: True once the engine has run and the recorded notes are on disk. Without
    #: them there is no rhythm to measure and no sheet to write.
    has_notes: bool = Field(False, alias="hasNotes")
    #: Set for a piece the migration could not carry over, in words meant for a
    #: reader. `None` for every piece that is fine. See P4.5.
    needs_rederivation: str | None = Field(None, alias="needsRederivation")


def _entry(metadata: AudioMetadata) -> AudioEntry:
    return AudioEntry(
        **metadata.model_dump(by_alias=True),
        hasNotes=pipeline.has_events(metadata.uuid),
        needsRederivation=pipeline.needs_rederivation(metadata.uuid),
    )


@router.get("/", response_model=list[AudioEntry], response_model_by_alias=True)
def list_audio() -> list[AudioEntry]:
    """Every audio in the store, newest first. Powers "load from library"."""
    return [_entry(entry.metadata) for entry in store.list_all()]


@router.get("/{audio_uuid}", response_model=AudioEntry, response_model_by_alias=True)
def get_audio(audio_uuid: str) -> AudioEntry:
    """Metadata of one stored audio, and whether it can be drawn."""
    try:
        return _entry(store.read_metadata(audio_uuid))
    except AudioNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{audio_uuid}", response_model=AudioMetadata, response_model_by_alias=True)
def rename_audio(audio_uuid: str, body: AudioRename) -> AudioMetadata:
    """Edit the display alias."""
    _found(audio_uuid)
    if body.alias is None:
        return store.read_metadata(audio_uuid)
    try:
        return store.rename(audio_uuid, body.alias)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{audio_uuid}")
def delete_audio(audio_uuid: str) -> dict[str, str]:
    """Remove an audio uuid folder from the store."""
    try:
        store.delete(audio_uuid)
    except AudioNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "uuid": audio_uuid}


@router.post("/upload", response_model=AudioMetadata, response_model_by_alias=True, status_code=201)
def upload_audio(
    file: Annotated[UploadFile, File()],
    alias: Annotated[str | None, Form()] = None,
) -> AudioMetadata:
    """Store an uploaded file and normalize it with ffmpeg.

    The format comes from the **filename suffix**; anything outside
    `.mp3/.aac/.m4a/.wav` is a `422`.
    """
    return _ingest_upload(file, AudioSource.UPLOAD, alias)


@router.post(
    "/recording", response_model=AudioMetadata, response_model_by_alias=True, status_code=201
)
def store_recording(
    file: Annotated[UploadFile, File()],
    alias: Annotated[str | None, Form()] = None,
) -> AudioMetadata:
    """Store a browser MediaRecorder capture (Story 3.3).

    Identical to `/upload` apart from the recorded `source`, so the two share
    one ingest path.
    """
    return _ingest_upload(file, AudioSource.RECORDING, alias)


def _ingest_upload(file: UploadFile, source: AudioSource, alias: str | None) -> AudioMetadata:
    if not file.filename:
        raise HTTPException(status_code=422, detail="The uploaded file has no name")
    try:
        entry = ingest.ingest_file(file.file, file.filename, source, alias=alias)
    except UnsupportedFormat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FfmpegMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConversionFailed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return entry.metadata


@router.post(
    "/{audio_uuid}/trim",
    response_model=AudioMetadata,
    response_model_by_alias=True,
    status_code=201,
)
def trim_audio(audio_uuid: str, body: AudioTrimRequest) -> AudioMetadata:
    """Persist one selected range as a self-contained segment audio."""
    _found(audio_uuid)
    try:
        return ingest.create_segment(
            audio_uuid,
            body.start_seconds,
            body.end_seconds,
            alias=body.alias,
        ).metadata
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, ConversionFailed) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FfmpegMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{audio_uuid}/waveform", response_model=WaveformResponse, response_model_by_alias=True)
def audio_waveform(
    audio_uuid: str,
    points: Annotated[int, Query(ge=1, le=20000)] = formats.DEFAULT_WAVEFORM_POINTS,
    refresh: bool = False,
) -> WaveformResponse:
    """Downsampled min/max peaks, cached next to the audio.

    Computed backend-side so the frontend never decodes audio just to draw it.
    """
    _found(audio_uuid)
    try:
        peaks = ingest.waveform(audio_uuid, points, refresh=refresh)
    except FileNotFoundError as exc:
        # Matrix-JSON imports deliberately have a store entry but no audio
        # bytes. Piano views treat their waveform as optional, so report that
        # absence without turning the expected fallback into a server error.
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FfmpegMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return WaveformResponse.model_validate(peaks.to_dict())


@router.get("/{audio_uuid}/file")
def stream_audio(audio_uuid: str, normalized: bool = False) -> Any:
    """Serve the stored audio for playback.

    Defaults to the **original** file — it is what the user recognizes.
    `?normalized=true` serves the mono WAV the engine actually reads.
    """
    _found(audio_uuid)
    entry = store.get(audio_uuid)

    if normalized:
        if not entry.has_normalized():
            raise HTTPException(status_code=404, detail="This audio has not been normalized yet")
        return FileResponse(entry.normalized_path, media_type="audio/wav")

    original = entry.original_path
    if original is None:
        raise HTTPException(status_code=404, detail="This audio has no stored original file")
    media_type = _MEDIA_TYPES.get(entry.metadata.format, "application/octet-stream")
    return FileResponse(original, media_type=media_type, filename=original.name)


@router.get("/{audio_uuid}/range")
def audio_range(
    audio_uuid: str,
    start_seconds: Annotated[float, Query(alias="startSeconds", ge=0)] = 0.0,
    end_seconds: Annotated[float, Query(alias="endSeconds", gt=0)] = 1.0,
) -> Any:
    """Serve a sub-range of the audio as WAV.

    The range selector plays ranges client-side by seeking within the already
    downloaded file, so this is not on its hot path. It exists for the callers
    that need the *bytes* of a range: Epic 6's "transcribe only this passage"
    and Epic 11's tempo-compressed preview.
    """
    _found(audio_uuid)
    entry = store.get(audio_uuid)
    if not entry.has_normalized():
        raise HTTPException(status_code=409, detail="This audio has not been normalized yet")

    clip = entry.directory / f"range_{start_seconds:.3f}_{end_seconds:.3f}.wav"
    try:
        formats.slice_wav(entry.normalized_path, clip, start_seconds, end_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FileResponse(clip, media_type="audio/wav", filename=clip.name)
