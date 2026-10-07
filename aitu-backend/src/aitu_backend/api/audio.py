"""`/audio` — the audio working store (Epic 3, Stories 3.1 and 3.2)."""

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import formats, ingest, piece_audio, store
from aitu_backend.audio.frames import (
    FRAME_MS,
    SAMPLE_RATE,
    FrameTable,
    frame_count,
    frame_peaks,
    normalize_cuts,
)
from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing, UnsupportedFormat
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.video import store as video_store

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


class FramePeaksResponse(BaseModel):
    """`GET /audio/{uuid}/frames/peaks`: the waveform at one pair of values per time frame."""

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    frame_ms: int = Field(FRAME_MS, alias="frameMs")
    #: Frames of the original audio: the same count as `GET /audio/{uuid}/cuts`.
    total_frames: int = Field(..., alias="totalFrames")
    #: The loudest sample of the audio (0 to 1). The values below are scaled so it is 127.
    peak: float
    #: Base64 of one signed byte per frame: the lowest sample of the frame, and the highest.
    min: str
    max: str


class KeptRange(BaseModel):
    """One row of the frame table: a kept range of the original audio, in 10 ms frames."""

    model_config = ConfigDict(populate_by_name=True)

    #: Where the range starts in the piece (the original minus the cuts).
    piece_start: int = Field(..., alias="pieceStart")
    #: Where it starts in the original audio file.
    original_start: int = Field(..., alias="originalStart")
    length: int


class CutsResponse(BaseModel):
    """`GET` and `PUT /audio/{uuid}/cuts`: the selected region (plan section 9.2)."""

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    #: Goes up by one each time the cuts change. Notes made from another revision are stale.
    audio_revision: int = Field(..., alias="audioRevision")
    #: One time frame, in ms: the column of the piano matrix notation at 10 ms.
    frame_ms: int = Field(FRAME_MS, alias="frameMs")
    #: Frames of the original audio, and of the piece once the cuts are removed.
    total_frames: int = Field(..., alias="totalFrames")
    piece_frames: int = Field(..., alias="pieceFrames")
    #: ``[startFrame, endFrame)`` of the original audio, sorted.
    cuts: list[tuple[int, int]]
    #: The table from a frame of the piece to a frame of the original, one row per kept range.
    kept: list[KeptRange]
    #: True when the stored notes were transcribed from other cuts: transcribe again (Q-2).
    notes_stale: bool = Field(False, alias="notesStale")
    #: The files of the audio laid end to end, in order (**add audio**): one for most parts.
    files: list["AxisFile"] = Field(default_factory=list)


class AxisFile(BaseModel):
    """One file of the axis of the Audio step."""

    model_config = ConfigDict(populate_by_name=True)

    #: Its place in the order of the audio, from 0.
    index: int = 0
    #: The name the user gave it (its file name, or the video's title, at first).
    name: str
    #: ``upload``, ``youtube``, ``recording`` ...
    kind: str = "upload"
    original_filename: str | None = Field(None, alias="originalFilename")
    url: str | None = None
    #: Where the file starts on the axis, and its length, in 10 ms frames.
    start_frame: int = Field(..., alias="startFrame")
    frames: int
    #: How many of its frames are cut.
    cut_frames: int = Field(0, alias="cutFrames")


class FilesResponse(BaseModel):
    """`/audio/{uuid}/files`: the files of the part's audio, in order (the Source step)."""

    model_config = ConfigDict(populate_by_name=True)

    audio_revision: int = Field(..., alias="audioRevision")
    files: list[AxisFile]


class FileName(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=200)


class FileOrder(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    #: The current places of the files, in their new order: ``[1, 0, 2]`` swaps the first two.
    order: list[int]
    base_revision: int | None = Field(None, alias="baseRevision", ge=0)


CutsResponse.model_rebuild()


class CutsRequest(BaseModel):
    """Body of `PUT /audio/{uuid}/cuts`."""

    model_config = ConfigDict(populate_by_name=True)

    cuts: list[tuple[int, int]]
    #: The `audioRevision` the page started from. When it is not the stored one any more, the
    #: request is refused with 409 instead of writing over a newer selection.
    base_revision: int | None = Field(None, alias="baseRevision", ge=0)


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
    #: The length of the untouched original. `durationSeconds` is the length of the piece: once cuts
    #: are saved, the edited audio is the audio of the piece (implementation 08, Phase 6).
    original_duration_seconds: float | None = Field(None, alias="originalDurationSeconds")
    #: When the piece last changed: the newest file directly in its folder (the audio, the
    #: metadata, the notes, the piano sheet). The Projects page sorts and shows it.
    updated_at: datetime | None = Field(None, alias="updatedAt")
    #: The part has a video (a video project): its Audio step is the Video step (section 10.2).
    has_video: bool = Field(False, alias="hasVideo")


def _updated_at(audio_uuid: str) -> datetime | None:
    """The newest modification time of the part's files (notes, sheet, timeline) and of
    ``project.json`` (its title and source).

    One `stat` per file, no file read, so the list of every project stays fast. History, staging,
    the cache and the video are not looked at: they are not edits of the project itself.
    """
    try:
        folder = paths.part_dir(audio_uuid)
        files = [child for child in folder.iterdir() if child.is_file()]
        files.append(folder.parent.parent / "project.json")
        times = [child.stat().st_mtime for child in files if child.is_file()]
    except (OSError, KeyError):
        return None
    return datetime.fromtimestamp(max(times), tz=UTC) if times else None


def _entry(metadata: AudioMetadata) -> AudioEntry:
    fields = metadata.model_dump(by_alias=True)
    original = metadata.duration_seconds
    if original is not None and metadata.cuts:
        removed = sum(end - start for start, end in metadata.cuts) * FRAME_MS / 1000.0
        fields["durationSeconds"] = round(max(0.0, original - removed), 6)
    return AudioEntry(
        **fields,
        hasNotes=pipeline.has_events(metadata.uuid),
        needsRederivation=pipeline.needs_rederivation(metadata.uuid),
        originalDurationSeconds=original,
        updatedAt=_updated_at(metadata.uuid),
        hasVideo=video_store.exists(metadata.uuid),
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
    "/{audio_uuid}/add",
    response_model=AudioMetadata,
    response_model_by_alias=True,
    status_code=201,
)
def add_audio(
    audio_uuid: str,
    file: Annotated[UploadFile, File()],
    name: Annotated[str | None, Form()] = None,
) -> AudioMetadata:
    """**Add audio**: another file at the end of the part's audio (plan section 8.5).

    The file is stored once by its content, measured, and appended to the timeline; the cuts keep
    their frames. The audio changed, so ``audioRevision`` goes up and the notes become stale.
    ``name`` is the name the Source step shows; the file's name without its extension by default.
    """
    _found(audio_uuid)
    if not file.filename:
        raise HTTPException(status_code=422, detail="The uploaded file has no name")
    try:
        return ingest.append_file(audio_uuid, file.file, file.filename, name=name)
    except UnsupportedFormat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FfmpegMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConversionFailed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _files(audio_uuid: str) -> FilesResponse:
    return FilesResponse(
        audio_revision=store.read_metadata(audio_uuid).audio_revision,
        files=[AxisFile.model_validate(row) for row in store.files_of(audio_uuid)],
    )


def _file_change(audio_uuid: str, change: Any) -> FilesResponse:
    _found(audio_uuid)
    try:
        change()
    except store.RevisionMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _files(audio_uuid)


@router.get("/{audio_uuid}/files", response_model=FilesResponse, response_model_by_alias=True)
def list_files(audio_uuid: str) -> FilesResponse:
    """The files of the part's audio in order, with their names and how much of each is cut."""
    _found(audio_uuid)
    return _files(audio_uuid)


@router.patch(
    "/{audio_uuid}/files/{index}", response_model=FilesResponse, response_model_by_alias=True
)
def rename_file(audio_uuid: str, index: int, body: FileName) -> FilesResponse:
    """Name one file of the audio. The audio does not change."""
    return _file_change(audio_uuid, lambda: store.rename_file(audio_uuid, index, body.name))


@router.put("/{audio_uuid}/files/order", response_model=FilesResponse, response_model_by_alias=True)
def reorder_files(audio_uuid: str, body: FileOrder) -> FilesResponse:
    """Put the files in a new order. Each keeps its cuts; the notes become stale."""
    return _file_change(
        audio_uuid,
        lambda: store.reorder_files(audio_uuid, body.order, base_revision=body.base_revision),
    )


@router.delete(
    "/{audio_uuid}/files/{index}", response_model=FilesResponse, response_model_by_alias=True
)
def remove_file(
    audio_uuid: str,
    index: int,
    base_revision: Annotated[int | None, Query(alias="baseRevision", ge=0)] = None,
) -> FilesResponse:
    """Take one file out of the audio (not the last one). The notes become stale."""
    return _file_change(
        audio_uuid,
        lambda: store.remove_file(audio_uuid, index, base_revision=base_revision),
    )


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


@router.get(
    "/{audio_uuid}/frames/peaks",
    response_model=FramePeaksResponse,
    response_model_by_alias=True,
)
def audio_frame_peaks(audio_uuid: str) -> FramePeaksResponse:
    """The waveform of the Audio tab: the lowest and the highest sample of each 10 ms time frame.

    One request gives every zoom level down to a single frame, which is the step a cut snaps to
    (implementation 08, plan section 9.4). Read from ``normalized.wav``, like the frames of the
    cuts, so frame ``f`` here is frame ``f`` there.
    """
    _found(audio_uuid)
    entry = store.get(audio_uuid)
    if not entry.has_normalized():
        raise HTTPException(
            status_code=409, detail="This audio has no normalized.wav yet, so it has no frames."
        )
    rate, samples = formats.read_wav(entry.normalized_path)
    if rate != SAMPLE_RATE:
        raise HTTPException(
            status_code=409,
            detail=f"normalized.wav is {rate} Hz, not {SAMPLE_RATE} Hz. Normalize it again.",
        )
    low, high, peak = frame_peaks(samples)
    return FramePeaksResponse(
        audio_uuid=audio_uuid,
        total_frames=len(low),
        peak=round(peak, 6),
        min=base64.b64encode(low.tobytes()).decode("ascii"),
        max=base64.b64encode(high.tobytes()).decode("ascii"),
    )


def _cuts_response(audio_uuid: str) -> CutsResponse:
    entry = store.get(audio_uuid)
    if not entry.has_normalized():
        raise HTTPException(
            status_code=409, detail="This audio has no normalized.wav yet, so it has no frames."
        )
    _, samples = formats.sample_count(entry.normalized_path)
    table = FrameTable.from_cuts(entry.metadata.cuts, frame_count(samples))
    return CutsResponse(
        audio_uuid=audio_uuid,
        audio_revision=entry.metadata.audio_revision,
        total_frames=table.total_frames,
        piece_frames=table.piece_frames,
        cuts=table.cuts(),
        kept=[KeptRange.model_validate(row) for row in table.rows()],
        notes_stale=pipeline.notes_are_stale(audio_uuid),
        files=[AxisFile.model_validate(row) for row in store.files_of(audio_uuid)],
    )


@router.get("/{audio_uuid}/cuts", response_model=CutsResponse, response_model_by_alias=True)
def get_cuts(audio_uuid: str) -> CutsResponse:
    """The parts of the audio the user deleted, and the table that joins the rest.

    The audio file is never changed: a cut is a range of 10 ms time frames of the original, and the
    piece is every frame that is not in a cut (implementation 08, plan section 9.2).
    """
    _found(audio_uuid)
    return _cuts_response(audio_uuid)


@router.put("/{audio_uuid}/cuts", response_model=CutsResponse, response_model_by_alias=True)
def put_cuts(audio_uuid: str, body: CutsRequest) -> CutsResponse:
    """Save the cuts. Nothing is written when they did not change.

    From then on the edited audio is the audio of the piece: this writes it (a few seconds for a
    song), and `GET /audio/{uuid}/file` serves it to every player. The original stays on disk for
    the Audio tab only (``?original=true``).

    The cuts are sorted, clipped to the audio and merged where they overlap or touch. A change
    makes ``audioRevision`` go up by one, which makes any stored notes stale: the next
    transcription request transcribes again instead of reusing them, and the old notes go into
    history (Q-2). This route does not start the transcription; the page's **Transcribe** does.
    """
    _found(audio_uuid)
    entry = store.get(audio_uuid)
    if body.base_revision is not None and body.base_revision != entry.metadata.audio_revision:
        raise HTTPException(
            status_code=409,
            detail=(
                "The selected region was changed somewhere else since this page loaded it "
                f"(revision {entry.metadata.audio_revision}, not {body.base_revision}). "
                "Reload the page to see the current one."
            ),
        )
    current = _cuts_response(audio_uuid)
    cuts = normalize_cuts(body.cuts, current.total_frames)
    if cuts and sum(end - start for start, end in cuts) >= current.total_frames:
        raise HTTPException(status_code=422, detail="The cuts would delete the whole audio.")
    store.set_cuts(audio_uuid, cuts)
    try:
        piece_audio.ensure(audio_uuid)
    except ConversionFailed as exc:
        raise HTTPException(status_code=500, detail=f"The edited audio could not be written: {exc}")
    return _cuts_response(audio_uuid)


@router.get("/{audio_uuid}/file")
def stream_audio(audio_uuid: str, normalized: bool = False, original: bool = False) -> Any:
    """Serve the audio of the piece for playback.

    The file the user gave (upload, recording, download) by default: it is what the user
    recognizes. `?normalized=true` serves the mono 16 kHz WAV the engine reads.

    **A piece with cuts plays its edited audio** (implementation 08, Phase 6): the original with
    the cuts removed, the time the notes are in, from both forms. `?original=true` serves the
    untouched file instead, for the Audio tab, which shows the cuts on the original to restore them.
    The answer is revalidated on each play (`no-cache`), because saving other cuts changes it.
    """
    _found(audio_uuid)
    if not original:
        try:
            piece = piece_audio.ensure(audio_uuid)
        except ConversionFailed as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if piece is not None:
            path = piece.normalized if normalized else piece.listen
            media = "audio/flac" if path.suffix == ".flac" else "audio/wav"
            return FileResponse(path, media_type=media, headers={"Cache-Control": "no-cache"})
    entry = store.get(audio_uuid)

    if normalized:
        if not entry.has_normalized():
            raise HTTPException(status_code=404, detail="This audio has not been normalized yet")
        return FileResponse(
            entry.normalized_path, media_type="audio/wav", headers={"Cache-Control": "no-cache"}
        )

    try:
        original_path = store.original_file(entry)
    except (ConversionFailed, FfmpegMissing) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if original_path is None:
        raise HTTPException(status_code=404, detail="This audio has no stored original file")
    media_type = (
        "audio/flac"
        if entry.joined
        else _MEDIA_TYPES.get(entry.metadata.format, "application/octet-stream")
    )
    # The stored file is named by its content; the download keeps the name the user knows.
    name = Path(entry.metadata.original_filename or entry.metadata.alias).stem or "audio"
    return FileResponse(
        original_path,
        media_type=media_type,
        filename=f"{name}{original_path.suffix}",
        headers={"Cache-Control": "no-cache"},
    )


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
