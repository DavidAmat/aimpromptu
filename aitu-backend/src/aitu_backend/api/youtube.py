"""`/youtube` — audio downloads via yt-dlp (Epic 3, Story 3.5).

`POST /youtube/jobs` (implementation 08, Phase 6) runs the same download as a background job, so
the request answers at once and the page follows the progress stream of every job,
`GET /matrix/progress/{jobId}`. Its final `done` frame carries the `audioUuid` of the stored audio.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import youtube
from aitu_backend.auth.dependencies import require_part
from aitu_backend.audio.youtube import (
    DownloadFailed,
    InvalidYoutubeUrl,
    YtDlpMissing,
)
from aitu_backend.progress import BaseProgress
from aitu_backend.schemas.metadata import AudioMetadata
from aitu_backend.transcription import jobs

router = APIRouter(prefix="/youtube", tags=["youtube"])


class YoutubeRequest(BaseModel):
    """Body of `POST /youtube/download` and `POST /youtube/probe`."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    #: Display name for the stored audio. Defaults to the video title.
    alias: str | None = Field(None, alias="fileName")
    #: A part to add the audio to (**add audio** from the Source step), instead of a new project.
    append_to: str | None = Field(None, alias="appendTo")


class VideoInfoResponse(BaseModel):
    """What `POST /youtube/probe` reports, so the UI can prefill the name."""

    model_config = ConfigDict(populate_by_name=True)

    title: str
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    uploader: str | None = None


class DownloadJob(BaseModel):
    """What `POST /youtube/jobs` answers: the job to follow."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str


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


@router.post("/jobs", response_model=DownloadJob, response_model_by_alias=True, status_code=202)
def start_download(request: YoutubeRequest) -> DownloadJob:
    """Start the download in the background and answer at once (the Source tab).

    The URL is checked here, so a wrong link is refused with 422 before any job exists. The page
    follows `GET /matrix/progress/{jobId}`: a `download` stage in percent, then a `store` stage
    while the audio is converted, then `event: done` with `audioUuid`, `alias` and
    `durationSeconds`, or with `status: "error"` and yt-dlp's own words. A second request for the
    same URL while the first is running returns the first job.
    """
    try:
        cleaned = youtube.validate_url(request.url)
    except InvalidYoutubeUrl as exc:
        raise _handle(exc) from exc
    if not youtube.yt_dlp_available():
        raise _handle(YtDlpMissing())
    if request.append_to is not None:
        # The part is named in the body, so its rights are checked here (plan section 9.3).
        require_part(request.append_to, write=True)

    def work(reporter: BaseProgress) -> Any:
        return youtube.download(
            cleaned, request.alias, reporter=reporter, append_to=request.append_to
        )

    def describe(entry: Any) -> dict[str, Any]:
        metadata = entry.metadata
        return {
            "audioUuid": metadata.uuid,
            "alias": metadata.alias,
            "durationSeconds": metadata.duration_seconds,
        }

    key = f"youtube:{cleaned}" + (f":{request.append_to}" if request.append_to else "")
    job = jobs.submit(work, key=key, describe=describe)
    return DownloadJob(job_id=job.id, status=job.status)


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
