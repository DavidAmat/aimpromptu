"""`/video` — one YouTube URL becomes a video, sampled frames and a reading.

Phase 3 of `04-synthesia-to-notes`, in the order of the work: download, sample,
calibrate, measure, detect. Every shape on the wire is camelCase, like every
other router.

Two of these are jobs with progress, on the same SSE plumbing transcription uses,
because they are the two that take longer than a request should: sampling a four
minute video and reading every frame of it. The rest answer straight away.

The piece a video belongs to is an ordinary audio uuid (V-03): there is no second
kind of piece and no second library. `POST /video/download` creates it, the audio
of that same video included, and the user is never asked about the audio.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import formats, store as audio_store
from aitu_backend.audio.youtube import DownloadFailed, InvalidYoutubeUrl, YtDlpMissing
from aitu_backend.schemas.video import (
    Calibration,
    Detection,
    DetectionReport,
    FindRequest,
    FrameLine,
    NoteCorrections,
    VideoMetadata,
    VideoNotes,
    VideoSummary,
)
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.video import (
    download,
    finder,
    notes as notes_module,
    piece,
    reading,
    sampling,
    store,
)
from aitu_backend.video.finder import NoKeyboard

router = APIRouter(prefix="/video", tags=["video"])


class VideoDownloadRequest(BaseModel):
    """Body of `POST /video/download`."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    #: Display name for the piece. Defaults to the video title, as the audio
    #: download already does.
    alias: str | None = Field(None, alias="fileName")


class JobHandle(BaseModel):
    """What a job returns immediately; follow `GET /video/progress/{jobId}`."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str


def _video_or_404(audio_uuid: str) -> None:
    if not audio_store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"Audio {audio_uuid} has no downloaded video")


def _summary(audio_uuid: str) -> VideoSummary:
    lines = store.load_frame_lines(audio_uuid)
    read = store.load_notes(audio_uuid)
    return VideoSummary(
        metadata=store.load_metadata(audio_uuid),
        calibration=store.load_calibration(audio_uuid),
        measurement=store.load_measurement(audio_uuid),
        detected=bool(lines),
        detected_frames=len(lines),
        note_count=len(read.notes) if read else 0,
        has_piece=pipeline.has_events(audio_uuid),
    )


# ------------------------------------------------------------- downloading ---


@router.post(
    "/download", response_model=VideoMetadata, response_model_by_alias=True, status_code=201
)
def download_video(request: VideoDownloadRequest) -> VideoMetadata:
    """Download one video, and the audio of that same video with it (V-03).

    Synchronous, like the audio download beside it: a piano video at 720p is a
    few megabytes and takes a few seconds. yt-dlp's own words are surfaced when
    it refuses, because rate limits, private videos and geo blocks say more in
    its wording than in anything we could paraphrase.
    """
    try:
        return download.download(request.url, request.alias)
    except InvalidYoutubeUrl as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (YtDlpMissing, formats.FfmpegMissing) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (DownloadFailed, formats.ConversionFailed) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("", response_model=list[VideoSummary], response_model_by_alias=True)
def list_videos() -> list[VideoSummary]:
    """Every piece that has a downloaded video, so the screens can offer a choice.

    The whole series of per-pair shifts is left out of the rows. V-06 says the
    series is stored and it is — in `calibration.json`, and on
    `GET /video/{audio_uuid}` — but it is one number per pair of sampled frames,
    which is 2727 of them on a four and a half minute video, and a picker that
    shows a title and five chips has no use for any of them.
    """
    out: list[VideoSummary] = []
    for audio_uuid in store.uuids():
        summary = _summary(audio_uuid)
        if summary.measurement is not None:
            summary.measurement.scroll_speed.series = []
        out.append(summary)
    return out


@router.get("/progress/{job_id}")
def video_progress(job_id: str) -> StreamingResponse:
    """SSE stream of a sampling or detection job, ending with a named `done`."""
    return StreamingResponse(
        jobs.stream(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{audio_uuid}", response_model=VideoSummary, response_model_by_alias=True)
def get_video(audio_uuid: str) -> VideoSummary:
    """What we have about one video: what it is, how it was sampled, what was read."""
    _video_or_404(audio_uuid)
    return _summary(audio_uuid)


# ---------------------------------------------------------------- sampling ---


@router.post(
    "/{audio_uuid}/sample", response_model=JobHandle, response_model_by_alias=True, status_code=202
)
def sample_video(
    audio_uuid: str,
    sample_ms: float = Query(sampling.DEFAULT_SAMPLE_MS, alias="sampleMs", gt=0),
) -> JobHandle:
    """Sample the frames at a sampling granularity, as a job with progress.

    `sampleMs` is how often we look at the video. It is never `frameMs`, which is
    the column length the sheet is read at (V-04). Sampling again at another
    granularity replaces the folder; the video is still there, so nothing is lost
    (V-01).
    """
    _video_or_404(audio_uuid)

    def work(reporter: Any) -> Any:
        return sampling.sample(audio_uuid, sample_ms, reporter=reporter)

    job = jobs.submit(work)
    return JobHandle(job_id=job.id, status=job.status)


@router.get("/{audio_uuid}/frames/{index}")
def get_frame(audio_uuid: str, index: int) -> FileResponse:
    """One sampled frame, as an image, at the working resolution.

    The picture the browser draws is the picture the detector reads (V-35), so a
    coordinate the user places in the calibration UI needs no scaling anywhere.
    """
    _video_or_404(audio_uuid)
    try:
        path = store.frame_path(audio_uuid, index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/jpeg")


# ------------------------------------------------------------- calibration ---


@router.get("/{audio_uuid}/calibration", response_model=Calibration, response_model_by_alias=True)
def get_calibration(audio_uuid: str) -> Calibration:
    """The piano overlay of this video."""
    _video_or_404(audio_uuid)
    calibration = store.load_calibration(audio_uuid)
    if calibration is None:
        raise HTTPException(status_code=404, detail=f"Audio {audio_uuid} has no piano overlay yet")
    return calibration


@router.put("/{audio_uuid}/calibration", response_model=VideoSummary, response_model_by_alias=True)
def put_calibration(audio_uuid: str, calibration: Calibration) -> VideoSummary:
    """Save the piano overlay of this video. The piano does not move (V-11)."""
    _video_or_404(audio_uuid)
    store.save_calibration(audio_uuid, calibration)
    return _summary(audio_uuid)


@router.post("/{audio_uuid}/find", response_model=Calibration, response_model_by_alias=True)
def find_overlay(
    audio_uuid: str,
    body: FindRequest,
    index: int = Query(..., ge=0),
) -> Calibration:
    """The one rectangle in, the piano overlay found inside one frame out (V-37).

    The same finder the example screenshots use, on a sampled frame. Nothing is
    saved: the screen shows the answer and the user saves it through
    `PUT /{audio_uuid}/calibration`.
    """
    _video_or_404(audio_uuid)
    try:
        image = store.load_frame(audio_uuid, index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        found = finder.find_overlay(
            image,
            body.piano_rect,
            upper_line=body.upper_line,
            first_white_octave=body.first_white_octave,
        )
    except NoKeyboard as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # The roll top and the guard band belong to the video, not to the frame the
    # overlay was found in, so a re-find never throws away what motion measured.
    saved = store.load_calibration(audio_uuid)
    if saved is not None:
        found.roll_top, found.guard_band = saved.roll_top, saved.guard_band
    return found


# ------------------------------------------------------------ the motion ----


@router.post(
    "/{audio_uuid}/measure", response_model=JobHandle, response_model_by_alias=True, status_code=202
)
def measure_video(
    audio_uuid: str,
    workers: int | None = Query(None, ge=1, le=16),
) -> JobHandle:
    """What the motion of the roll says: the scroll speed and the two edges.

    The scroll speed is measured, never assumed (V-06), and the same pass finds
    where the roll starts and where the strike light begins (V-28) — because the
    roll scrolls and nothing else does. The roll top and the guard band are
    written into the calibration, which is where the detector reads them from.

    A job with progress, because V-06 asks every pair of consecutive sampled
    frames and that means reading every frame. The answer is on
    `GET /video/{audio_uuid}` when it finishes; a video whose speed is not stable
    comes back with `stable: false` and the reason in words, and is not
    transcribed quietly.
    """
    _video_or_404(audio_uuid)
    if store.load_calibration(audio_uuid) is None:
        raise HTTPException(
            status_code=409,
            detail=f"Audio {audio_uuid} has no piano overlay yet, so there is no upper line",
        )
    count = store.frame_count(audio_uuid)
    if count < 2:
        raise HTTPException(
            status_code=409,
            detail=f"Audio {audio_uuid} has {count} sampled frames; a scroll speed needs two",
        )

    def work(reporter: Any) -> Any:
        return reading.measure_video(audio_uuid, workers=workers, reporter=reporter)

    job = jobs.submit(work)
    return JobHandle(job_id=job.id, status=job.status)


# ------------------------------------------------------------ detection -----


@router.post(
    "/{audio_uuid}/detect", response_model=JobHandle, response_model_by_alias=True, status_code=202
)
def detect_video(
    audio_uuid: str,
    channel: str = Query("plate", description="plate, edges or both"),
    workers: int | None = Query(None, ge=1, le=16),
) -> JobHandle:
    """Run the detector over every sampled frame and write `frames.jsonl`.

    A job with progress. The lanes are independent (V-13) and so are the frames,
    so the pixel work is spread over worker processes.
    """
    _video_or_404(audio_uuid)

    def work(reporter: Any) -> Any:
        return reading.read_video(audio_uuid, channel=channel, workers=workers, reporter=reporter)

    job = jobs.submit(work)
    return JobHandle(job_id=job.id, status=job.status)


@router.get("/{audio_uuid}/detection", response_model=list[FrameLine], response_model_by_alias=True)
def get_detection(
    audio_uuid: str,
    start: int = Query(0, ge=0),
    limit: int = Query(2000, ge=1, le=100000),
) -> list[FrameLine]:
    """`frames.jsonl` as it was written: onsets and sustains per sampled frame."""
    _video_or_404(audio_uuid)
    return store.load_frame_lines(audio_uuid)[start : start + limit]


@router.get("/{audio_uuid}/report", response_model=DetectionReport, response_model_by_alias=True)
def get_report(audio_uuid: str) -> DetectionReport:
    """What the last run over the whole video did, in numbers (V-20, V-31)."""
    _video_or_404(audio_uuid)
    report = store.load_report(audio_uuid)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Audio {audio_uuid} has not been read yet")
    return report


@router.post(
    "/{audio_uuid}/frames/{index}/detect", response_model=Detection, response_model_by_alias=True
)
def detect_frame(
    audio_uuid: str,
    index: int,
    channel: str = Query("plate"),
) -> Detection:
    """Read one sampled frame, with its two neighbours, for the screen to draw.

    Every run comes back with the pixels it was found at and with what the
    momentum rule made of it, so a refusal is something you can look at rather
    than something you have to imagine.
    """
    _video_or_404(audio_uuid)
    try:
        return reading.detect_frame(audio_uuid, index, channel=channel)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except reading.NotCalibrated as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# --------------------------------------------------- the piece, from a video --
#
# Phase 4. The stitched roll (V-32) turns the whole video into one tall picture
# whose vertical axis is time, a note is one shape in it, and its bottom and top
# rows convert straight to seconds (V-05). What comes out is `events.json` and
# nothing else (V-02).


class WriteResult(BaseModel):
    """What `POST /video/{uuid}/events` did, in the words the screen shows."""

    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    title: str
    duration_seconds: float = Field(..., alias="durationSeconds")
    notes: int
    removed: int
    added: int
    #: Corrections naming a note the reading no longer holds, reported not hidden.
    unmatched: int
    #: The piece's music version after the write. Reading a video again replaces
    #: the piece, so it advances exactly as any other change to the music does.
    music_version: int = Field(..., alias="musicVersion")


@router.post(
    "/{audio_uuid}/notes", response_model=JobHandle, response_model_by_alias=True, status_code=202
)
def read_notes(
    audio_uuid: str,
    channel: str = Query("plate", description="plate, edges or both"),
) -> JobHandle:
    """Stitch the whole video into one picture and read the notes out of it (V-32).

    A job with progress: it reads every sampled frame once, piles its fresh strip
    into one tall picture whose vertical axis is time, and labels it. This does
    **not** write the piece — what it writes is `video/notes.json`, which is what
    *will* be written, so it can be looked at and corrected first (Task 4.3.1).
    """
    _video_or_404(audio_uuid)

    def work(reporter: Any) -> Any:
        return notes_module.read_notes(audio_uuid, channel=channel, reporter=reporter)

    job = jobs.submit(work)
    return JobHandle(job_id=job.id, status=job.status)


@router.get("/{audio_uuid}/notes", response_model=VideoNotes, response_model_by_alias=True)
def get_notes(audio_uuid: str) -> VideoNotes:
    """What the stitched roll read: every note, and the numbers behind them (V-20)."""
    _video_or_404(audio_uuid)
    read = store.load_notes(audio_uuid)
    if read is None:
        raise HTTPException(
            status_code=404, detail=f"Audio {audio_uuid} has not been read into notes yet"
        )
    return read


@router.get(
    "/{audio_uuid}/corrections", response_model=NoteCorrections, response_model_by_alias=True
)
def get_corrections(audio_uuid: str) -> NoteCorrections:
    """The notes a person took off or put on before the piece was written."""
    _video_or_404(audio_uuid)
    return store.load_corrections(audio_uuid)


@router.put(
    "/{audio_uuid}/corrections", response_model=NoteCorrections, response_model_by_alias=True
)
def put_corrections(audio_uuid: str, corrections: NoteCorrections) -> NoteCorrections:
    """Save what a person decided. It survives a re-stitch, as the calibration does."""
    _video_or_404(audio_uuid)
    return store.save_corrections(audio_uuid, corrections)


@router.post("/{audio_uuid}/events", response_model=WriteResult, response_model_by_alias=True)
def write_events(audio_uuid: str) -> WriteResult:
    """Turn the reading into `events.json`. This is the step that changes the piece.

    So it advances the music version, exactly as any other change to the music
    does, and the piece it writes is an ordinary piece: the hand split, the
    matrix, the peaks, the ladder and the sheet read it without knowing that a
    video is where it came from (V-02).
    """
    _video_or_404(audio_uuid)
    try:
        written = piece.write(audio_uuid)
    except piece.NotRead as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except piece.NotStable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return WriteResult(
        audio_uuid=written.audio_uuid,
        title=written.title,
        duration_seconds=written.duration_seconds,
        notes=written.notes,
        removed=written.removed,
        added=written.added,
        unmatched=written.unmatched,
        music_version=written.music_version,
    )
