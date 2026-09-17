"""Download one video, and the audio of that same video with it (Task 3.1.1).

`POST /video/download`. yt-dlp fetches the picture capped at 720p, because
nothing in the detector needs more — every picture is read at 1280 px wide
(V-35) — and the file stays small. The audio is then **extracted from the file
we just downloaded**, with ffmpeg, and goes into the store through
:func:`aitu_backend.audio.ingest.ingest_path` exactly as a YouTube audio does
today. One URL, one network fetch, one piece that has both (V-03).

Extracting from the video rather than fetching the audio stream a second time
halves the download and removes any question of the two being aligned. If the
audio quality of the video file ever matters, switching back to a separate
`bestaudio` fetch is a one line change in :data:`VIDEO_FORMAT` and the
:func:`_extract_audio` call below.

The user is not asked about any of this. They paste a URL and get a video they
can play; the audio is there because the Piano Sheet tab plays the original audio
later. yt-dlp errors are surfaced word for word, as they are now: rate limits,
private videos and geo blocks all say more in yt-dlp's own wording than in
anything we could paraphrase.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from aitu_backend.audio import formats, ingest
from aitu_backend.audio.youtube import (
    YT_DLP,
    DownloadFailed,
    YtDlpMissing,
    clean_error,
    PROGRESS_LINE,
    validate_url,
    yt_dlp_available,
)
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.video import VideoMetadata
from aitu_backend.storage import paths
from aitu_backend.video import store

#: Capped at 720p: the detector reads every picture at 1280 px wide, so a 1080p
#: download is three times the bytes for pixels that are thrown away before
#: anything looks at them. The fallback chain is yt-dlp's own: the best video and
#: audio under 720p, then the best single file under 720p, then whatever there is
#: — a video that only exists at 1080p is better downloaded than refused.
VIDEO_FORMAT = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"


def download(
    url: str,
    alias: str | None = None,
    *,
    reporter: BaseProgress | None = None,
) -> VideoMetadata:
    """Download one video and the audio of it, and report what arrived.

    The piece is created by the audio ingest, so the uuid comes back from there
    and the video is moved into that piece's own folder (V-03).
    """
    cleaned = validate_url(url)
    if not yt_dlp_available():
        raise YtDlpMissing()
    if not formats.ffmpeg_available():
        raise formats.FfmpegMissing()

    progress = default_reporter(reporter)

    with tempfile.TemporaryDirectory(prefix="aitu-video-") as workspace:
        target = Path(workspace)
        downloaded, title = _fetch(cleaned, target, progress)

        with progress.stage("audio", total=1) as stage:
            audio_file = _extract_audio(downloaded, target / "audio.mp3")
            entry = ingest.ingest_path(
                audio_file,
                AudioSource.YOUTUBE,
                alias=alias or title,
                source_url=cleaned,
            )
            stage.advance(1, message=entry.uuid)

        destination = paths.video_source_path(entry.uuid)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # `shutil.move`, not `Path.replace`: the temp folder is on the system
        # disk and `data/` may be on another volume, and a rename across two
        # devices fails with `Cross-device link`. Measured the hard way, on the
        # first real download.
        shutil.move(str(downloaded), destination)

    probed = probe_file(destination)
    return store.save_metadata(
        VideoMetadata(
            audio_uuid=entry.uuid,
            title=entry.metadata.alias,
            source_url=cleaned,
            width=probed["width"],
            height=probed["height"],
            duration_seconds=probed["duration"],
            fps=probed["fps"],
            size_bytes=destination.stat().st_size,
        )
    )


def _fetch(url: str, target: Path, progress: BaseProgress) -> tuple[Path, str]:
    """Run yt-dlp and answer with the file it wrote and the title of the video.

    The output template is a fixed name rather than ``%(title)s``, because the
    merge step leaves one file behind per stream before it joins them and a glob
    over the folder could pick up the wrong one. The title comes out of
    ``--write-info-json`` instead, which costs nothing: yt-dlp already has it, so
    there is no second call to YouTube for a name.
    """
    command = [
        *YT_DLP,
        "--no-playlist",
        "--no-part",
        "--newline",  # one progress line per update, so we can parse them
        "--write-info-json",
        "-f",
        VIDEO_FORMAT,
        "--merge-output-format",
        "mp4",
        "-o",
        str(target / "source.%(ext)s"),
        url,
    ]

    with progress.stage("download", total=100) as stage:
        seen = 0.0
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        )
        assert process.stdout is not None
        for line in process.stdout:
            match = PROGRESS_LINE.search(line)
            if match:
                percent = float(match.group(1))
                if percent > seen:
                    stage.advance(int(percent - seen), message=f"{percent:.0f}%")
                    seen = percent
        process.wait()
        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else ""
            raise DownloadFailed(clean_error(stderr))

    info_path = target / "source.info.json"
    title = "Untitled"
    if info_path.is_file():
        title = str(json.loads(info_path.read_text()).get("title") or title)
        info_path.unlink()

    # yt-dlp merges into the container it was asked for, but a single-file
    # fallback keeps whatever extension it had, so the file is found rather than
    # assumed.
    written = sorted(path for path in target.glob("source.*") if path.is_file())
    if not written:
        raise DownloadFailed(
            "yt-dlp finished but produced no video file. Merging needs ffmpeg — "
            "check it is on PATH (macOS: `brew install ffmpeg`)."
        )
    return written[0], title


def _extract_audio(source: Path, destination: Path) -> Path:
    """The audio of the video we just downloaded, as mp3.

    `-vn` drops the picture and `-q:a 0` is ffmpeg's best variable bit rate,
    which is what `yt-dlp -x --audio-quality 0` asks for on the audio path.
    """
    command = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "0",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise formats.ConversionFailed(f"ffmpeg could not take the audio out of the video:\n{tail}")
    return destination


def probe_file(path: Path) -> dict:
    """Size, duration and frames per second of a video file, from ffprobe.

    The frame rate is read from ``avg_frame_rate``, which is a fraction like
    ``30000/1001``, because that is the rate the file really holds; ``r_frame_rate``
    is the rate the container claims it can hold.
    """
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-3:])
        raise formats.ConversionFailed(f"ffprobe could not read {path.name}:\n{tail}")
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or [{}]
    stream = streams[0]
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": _fraction(stream.get("avg_frame_rate")),
        "duration": float(payload.get("format", {}).get("duration") or 0.0),
    }


def _fraction(value: object) -> float:
    """ffprobe's ``30000/1001`` as a number; zero when it says ``0/0``."""
    if not isinstance(value, str) or "/" not in value:
        return float(value) if isinstance(value, (int, float)) else 0.0
    numerator, _, denominator = value.partition("/")
    try:
        bottom = float(denominator)
        return float(numerator) / bottom if bottom else 0.0
    except ValueError:
        return 0.0
