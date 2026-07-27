"""YouTube audio downloads via `yt-dlp`.

`yt-dlp` is the maintained fork of youtube-dl and ships as a Python dependency,
but it is used through its **command line** rather than its Python API: the CLI
is the stable, documented surface, and its error messages (rate limits, private
videos, geo blocks) are exactly what we want to show the user verbatim.

It is invoked as ``python -m yt_dlp`` using **this interpreter**, not as a bare
``yt-dlp`` on ``PATH``. The console script only exists on ``PATH`` while the
venv is active, so a backend started any other way would not find it — while
``sys.executable -m yt_dlp`` works from wherever the process was launched.

Downloads land in a temp folder, then go through the normal
:func:`aitu_backend.audio.ingest.ingest_path`, so a YouTube audio ends up
identical to an upload apart from `source` and `sourceUrl`.

Single-user, manual usage. There is no scheduling and no retry: if YouTube
refuses, the error is surfaced and the user tries again.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aitu_backend.audio import ingest
from aitu_backend.audio.store import StoredAudio
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.metadata import AudioSource

#: Accepted URL shapes. Deliberately narrow: this endpoint shells out, so the
#: input is validated before it ever reaches a subprocess.
YOUTUBE_URL = re.compile(
    r"^https?://(?:www\.|m\.|music\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/)|youtu\.be/)"
    r"[\w-]{6,}",
    re.IGNORECASE,
)

#: yt-dlp's progress lines look like `[download]  42.3% of ...`.
_PROGRESS_LINE = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")


class YtDlpMissing(RuntimeError):
    """yt-dlp is not importable by this interpreter."""

    def __init__(self) -> None:
        super().__init__(
            "yt-dlp was not found. It is a backend dependency — run `uv sync` in aitu-backend/."
        )


class InvalidYoutubeUrl(ValueError):
    """The URL is not a YouTube link we recognize."""


class DownloadFailed(RuntimeError):
    """yt-dlp ran and refused. Carries its message for the user to read."""


@dataclass(frozen=True)
class VideoInfo:
    """What we learn about a video before downloading it."""

    title: str
    duration_seconds: float | None
    uploader: str | None


#: The command prefix every call uses. `-m` on this interpreter, not PATH.
YT_DLP = [sys.executable, "-m", "yt_dlp"]


def yt_dlp_available() -> bool:
    """Is the `yt_dlp` module importable by this interpreter?"""
    try:
        return importlib.util.find_spec("yt_dlp") is not None
    except (ImportError, ValueError):
        return False


def validate_url(url: str) -> str:
    """Return the URL if it looks like YouTube; raise otherwise."""
    cleaned = url.strip()
    if not YOUTUBE_URL.match(cleaned):
        raise InvalidYoutubeUrl(
            f"'{url}' is not a YouTube URL. Expected a youtube.com/watch, youtu.be "
            "or youtube.com/shorts link."
        )
    return cleaned


def probe(url: str) -> VideoInfo:
    """Fetch the title and duration without downloading the audio."""
    cleaned = validate_url(url)
    if not yt_dlp_available():
        raise YtDlpMissing()

    result = subprocess.run(
        [*YT_DLP, "--no-playlist", "--dump-single-json", "--skip-download", cleaned],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DownloadFailed(_clean_error(result.stderr))

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - yt-dlp always emits JSON here
        raise DownloadFailed(f"Could not read the video metadata: {exc}") from exc

    duration = payload.get("duration")
    return VideoInfo(
        title=str(payload.get("title") or "Untitled"),
        duration_seconds=float(duration) if duration is not None else None,
        uploader=payload.get("uploader"),
    )


def download(
    url: str,
    alias: str | None = None,
    *,
    reporter: BaseProgress | None = None,
) -> StoredAudio:
    """Download a video's audio as mp3 and ingest it into the audio store.

    ``alias`` defaults to the video title. Progress is reported through the
    standard :class:`~aitu_backend.progress.ProgressReporter`, so the same
    events feed a terminal bar and the SSE stream.
    """
    cleaned = validate_url(url)
    if not yt_dlp_available():
        raise YtDlpMissing()

    progress = default_reporter(reporter)

    with tempfile.TemporaryDirectory(prefix="aitu-yt-") as workspace:
        target = Path(workspace)
        command = [
            *YT_DLP,
            "--no-playlist",
            "--no-part",
            "--newline",  # one progress line per update, so we can parse them
            "-f",
            "bestaudio/best",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",  # best
            "-o",
            str(target / "%(title)s.%(ext)s"),
            cleaned,
        ]

        with progress.stage("download", total=100) as stage:
            seen = 0.0
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
            assert process.stdout is not None
            for line in process.stdout:
                match = _PROGRESS_LINE.search(line)
                if match:
                    percent = float(match.group(1))
                    if percent > seen:
                        stage.advance(int(percent - seen), message=f"{percent:.0f}%")
                        seen = percent
            process.wait()
            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else ""
                raise DownloadFailed(_clean_error(stderr))

        downloaded = sorted(target.glob("*.mp3"))
        if not downloaded:
            raise DownloadFailed(
                "yt-dlp finished but produced no mp3. `-x --audio-format mp3` needs ffmpeg — "
                "check it is on PATH (macOS: `brew install ffmpeg`)."
            )

        return ingest.ingest_path(
            downloaded[0],
            AudioSource.YOUTUBE,
            alias=alias or downloaded[0].stem,
            source_url=cleaned,
        )


def _clean_error(stderr: str) -> str:
    """The last meaningful yt-dlp error line, shown to the user verbatim.

    Rate limits, private videos and geo blocks all surface here, and yt-dlp's
    own wording is more useful than anything we could paraphrase.
    """
    lines = [line.strip() for line in stderr.strip().splitlines() if line.strip()]
    errors = [line for line in lines if line.upper().startswith("ERROR")]
    if errors:
        return errors[-1]
    return lines[-1] if lines else "yt-dlp failed without a message."
