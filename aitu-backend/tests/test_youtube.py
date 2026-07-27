"""YouTube downloads: URL validation, error surfacing and the endpoints.

Nothing here touches the network. `yt-dlp` is stubbed at the subprocess boundary,
so the tests pin *our* behaviour — validation, progress parsing, error wording,
ingest wiring — not YouTube's.
"""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import youtube
from aitu_backend.audio.youtube import (
    DownloadFailed,
    InvalidYoutubeUrl,
    YtDlpMissing,
    validate_url,
)
from aitu_backend.main import create_app
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.storage import paths


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


# ------------------------------------------------------------ URL validation


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "http://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abcdefghijk",
        "  https://youtu.be/dQw4w9WgXcQ  ",
    ],
)
def test_youtube_urls_are_accepted(url: str) -> None:
    assert validate_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/12345",
        "youtube.com/watch?v=x",  # no scheme
        "https://www.youtube.com/",
        "not a url",
        "",
        "file:///etc/passwd",
        "https://youtu.be/",
    ],
)
def test_non_youtube_urls_are_rejected(url: str) -> None:
    """This endpoint shells out, so the input is validated before it gets there."""
    with pytest.raises(InvalidYoutubeUrl):
        validate_url(url)


# ------------------------------------------------------------ error wording


def test_the_users_sees_yt_dlps_own_error_line() -> None:
    stderr = (
        "WARNING: unable to fetch something\n"
        "ERROR: [youtube] abc: Sign in to confirm you're not a bot\n"
    )
    assert "Sign in to confirm" in youtube._clean_error(stderr)


def test_the_last_error_wins_when_several_are_reported() -> None:
    stderr = "ERROR: first problem\nERROR: the real problem\n"
    assert youtube._clean_error(stderr) == "ERROR: the real problem"


def test_a_silent_failure_still_produces_a_message() -> None:
    assert "without a message" in youtube._clean_error("   \n  ")


def test_a_missing_yt_dlp_names_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: False)
    with pytest.raises(YtDlpMissing, match="uv sync"):
        youtube.download("https://youtu.be/dQw4w9WgXcQ")


# ------------------------------------------------------------------- probing


def test_probe_reads_the_title_and_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)
    monkeypatch.setattr(
        youtube.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"title": "Levels piano cover", "duration": 187.4, "uploader": "Someone"}',
            stderr="",
        ),
    )

    info = youtube.probe("https://youtu.be/dQw4w9WgXcQ")
    assert info.title == "Levels piano cover"
    assert info.duration_seconds == pytest.approx(187.4)
    assert info.uploader == "Someone"


def test_probe_surfaces_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)
    monkeypatch.setattr(
        youtube.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="ERROR: Private video"
        ),
    )
    with pytest.raises(DownloadFailed, match="Private video"):
        youtube.probe("https://youtu.be/dQw4w9WgXcQ")


# ----------------------------------------------------------------- downloads


class FakeProcess:
    """Stands in for the yt-dlp subprocess, emitting canned progress lines."""

    def __init__(self, lines: list[str], returncode: int = 0, stderr: str = "") -> None:
        self.stdout = iter(lines)
        self.stderr = SimpleNamespace(read=lambda: stderr)
        self.returncode = returncode

    def wait(self) -> int:
        return self.returncode


def test_download_parses_progress_and_ingests(
    temp_store: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mp3 yt-dlp leaves behind goes through the normal ingest path."""
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)

    lines = [
        "[download]   0.0% of 3.00MiB\n",
        "[download]  50.0% of 3.00MiB\n",
        "[download] 100.0% of 3.00MiB\n",
    ]

    def fake_popen(command, **kwargs):
        # yt-dlp's -o template is the second-to-last argument.
        workspace = Path(command[command.index("-o") + 1]).parent
        (workspace / "Levels piano cover.mp3").write_bytes(b"fake mp3")
        return FakeProcess(lines)

    monkeypatch.setattr(youtube.subprocess, "Popen", fake_popen)
    # The bytes are not a real mp3, so stop before ffmpeg would choke on them.
    seen: dict[str, object] = {}

    def fake_ingest(path, source, **kwargs):
        seen.update({"path": path, "source": source, **kwargs})
        return None

    monkeypatch.setattr(youtube.ingest, "ingest_path", fake_ingest)

    events: list[ProgressEvent] = []
    youtube.download("https://youtu.be/dQw4w9WgXcQ", reporter=CallbackProgress(events.append))

    assert Path(str(seen["path"])).name == "Levels piano cover.mp3"
    assert seen["source"] == "youtube"
    assert seen["alias"] == "Levels piano cover"
    assert seen["source_url"] == "https://youtu.be/dQw4w9WgXcQ"

    percentages = [event.current for event in events if event.stage == "download"]
    assert 50 in percentages and 100 in percentages


def test_an_explicit_alias_wins_over_the_video_title(
    temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)

    def fake_popen(command, **kwargs):
        workspace = Path(command[command.index("-o") + 1]).parent
        (workspace / "Some video title.mp3").write_bytes(b"fake")
        return FakeProcess([])

    monkeypatch.setattr(youtube.subprocess, "Popen", fake_popen)
    seen: dict[str, object] = {}

    def fake_ingest(path, source, **kwargs):
        seen.update(kwargs)
        return None

    monkeypatch.setattr(youtube.ingest, "ingest_path", fake_ingest)

    youtube.download("https://youtu.be/dQw4w9WgXcQ", "Levels - Avicii")
    assert seen["alias"] == "Levels - Avicii"


def test_a_download_that_produces_nothing_blames_ffmpeg(
    temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)
    monkeypatch.setattr(youtube.subprocess, "Popen", lambda *a, **k: FakeProcess([]))

    with pytest.raises(DownloadFailed, match="ffmpeg"):
        youtube.download("https://youtu.be/dQw4w9WgXcQ")


def test_a_failed_download_surfaces_the_error(
    temp_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)
    monkeypatch.setattr(
        youtube.subprocess,
        "Popen",
        lambda *a, **k: FakeProcess([], returncode=1, stderr="ERROR: Video unavailable"),
    )
    with pytest.raises(DownloadFailed, match="Video unavailable"):
        youtube.download("https://youtu.be/dQw4w9WgXcQ")


# ----------------------------------------------------------------- endpoints


def test_an_invalid_url_is_a_422(client: TestClient) -> None:
    response = client.post("/youtube/download", json={"url": "https://vimeo.com/1"})
    assert response.status_code == 422
    assert "not a YouTube URL" in response.json()["detail"]


def test_a_missing_yt_dlp_is_a_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: False)
    response = client.post("/youtube/download", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert response.status_code == 503


def test_a_youtube_refusal_is_a_502(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Their problem, not ours — hence a gateway error, with their wording."""
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: True)
    monkeypatch.setattr(
        youtube.subprocess,
        "Popen",
        lambda *a, **k: FakeProcess([], returncode=1, stderr="ERROR: Sign in to confirm"),
    )
    response = client.post("/youtube/download", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert response.status_code == 502
    assert "Sign in to confirm" in response.json()["detail"]


def test_the_request_accepts_the_documented_field_name(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The task file calls the alias `fileName`; both spellings work."""
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: False)
    response = client.post(
        "/youtube/download",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "fileName": "Levels"},
    )
    assert response.status_code == 503  # got past validation to the yt-dlp check


def test_batch_reports_each_item_separately(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One failure must not abandon the rest of the queue."""
    monkeypatch.setattr(youtube, "yt_dlp_available", lambda: False)
    response = client.post(
        "/youtube/batch",
        json={
            "items": [
                {"url": "https://youtu.be/aaaaaaaaaaa"},
                {"url": "https://vimeo.com/nope"},
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert [entry["status"] for entry in body] == ["error", "error"]
    assert "uv sync" in body[0]["detail"]
    assert "not a YouTube URL" in body[1]["detail"]


def test_yt_dlp_runs_through_this_interpreter() -> None:
    """`python -m yt_dlp`, not a bare `yt-dlp` on PATH.

    The console script only exists on PATH while the venv is active; the module
    invocation works wherever the backend was launched from.
    """
    if not youtube.yt_dlp_available():
        pytest.skip("yt-dlp absent in this environment")

    assert youtube.YT_DLP[0] == sys.executable
    assert youtube.YT_DLP[1:] == ["-m", "yt_dlp"]

    result = subprocess.run([*youtube.YT_DLP, "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip()  # a version string, e.g. 2026.07.04
