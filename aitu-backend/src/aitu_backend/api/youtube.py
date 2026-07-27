"""`/youtube` — audio downloads via yt-dlp (Epic 3, Story 3.5)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import youtube
from aitu_backend.audio.youtube import (
    DownloadFailed,
    InvalidYoutubeUrl,
    YtDlpMissing,
)
from aitu_backend.schemas.metadata import AudioMetadata

router = APIRouter(prefix="/youtube", tags=["youtube"])


class YoutubeRequest(BaseModel):
    """Body of `POST /youtube/download` and `POST /youtube/probe`."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    #: Display name for the stored audio. Defaults to the video title.
    alias: str | None = Field(None, alias="fileName")


class VideoInfoResponse(BaseModel):
    """What `POST /youtube/probe` reports, so the UI can prefill the name."""

    model_config = ConfigDict(populate_by_name=True)

    title: str
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    uploader: str | None = None


class BatchRequest(BaseModel):
    """Body of `POST /youtube/batch` — several downloads, run in order."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[YoutubeRequest]


class BatchEntry(BaseModel):
    """Outcome of one item in a batch."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    status: str
    detail: str | None = None
    audio: AudioMetadata | None = None


def _handle(exc: Exception) -> HTTPException:
    """Map a yt-dlp failure onto a status code, keeping its own wording."""
    if isinstance(exc, InvalidYoutubeUrl):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, YtDlpMissing):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


@router.post("/probe", response_model=VideoInfoResponse, response_model_by_alias=True)
def probe_video(request: YoutubeRequest) -> VideoInfoResponse:
    """Title and duration without downloading — lets the UI prefill the name."""
    try:
        info = youtube.probe(request.url)
    except (InvalidYoutubeUrl, YtDlpMissing, DownloadFailed) as exc:
        raise _handle(exc) from exc
    return VideoInfoResponse(
        title=info.title,
        duration_seconds=info.duration_seconds,
        uploader=info.uploader,
    )


@router.post(
    "/download", response_model=AudioMetadata, response_model_by_alias=True, status_code=201
)
def download(request: YoutubeRequest) -> AudioMetadata:
    """Download one video's audio as mp3 into the audio store.

    Synchronous: a typical piano video takes a few seconds. Epic 4's job/SSE
    plumbing can wrap this later if long videos become the norm — the
    `ProgressReporter` events are already emitted.
    """
    try:
        entry = youtube.download(request.url, request.alias)
    except (InvalidYoutubeUrl, YtDlpMissing, DownloadFailed) as exc:
        raise _handle(exc) from exc
    return entry.metadata


@router.post("/batch", response_model=list[BatchEntry], response_model_by_alias=True)
def download_batch(request: BatchRequest) -> list[BatchEntry]:
    """Download several videos in order (the nice-to-have queue).

    One failure does not stop the rest: each entry reports its own outcome, so
    a rate-limited item can be retried on its own.
    """
    results: list[BatchEntry] = []
    for item in request.items:
        try:
            entry = youtube.download(item.url, item.alias)
            results.append(BatchEntry(url=item.url, status="done", audio=entry.metadata))
        except (InvalidYoutubeUrl, YtDlpMissing, DownloadFailed) as exc:
            results.append(BatchEntry(url=item.url, status="error", detail=str(exc)))
    return results
