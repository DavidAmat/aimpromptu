"""gzip on the JSON answers only (implementation 08, Phase 2, task 2.3.2).

The piano sheet answer is about 12 times smaller compressed. The audio files and the progress
stream must reach the browser untouched: the player asks for byte ranges when it seeks, and a
compressed SSE stream would hold its messages back until a compressor block fills.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.testclient import TestClient

from aitu_backend.compression import COMPRESS_LEVEL, MINIMUM_SIZE, JsonGZipMiddleware

BIG = {"rows": list(range(5000))}


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.add_middleware(JsonGZipMiddleware)
    audio = tmp_path / "piece.wav"
    audio.write_bytes(b"RIFF" + bytes(range(256)) * 64)

    @app.get("/big")
    def big() -> JSONResponse:
        return JSONResponse(BIG)

    @app.get("/small")
    def small() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/audio")
    def audio_file() -> Response:
        from fastapi.responses import FileResponse

        return FileResponse(audio, media_type="audio/wav")

    @app.get("/stream")
    def stream() -> StreamingResponse:
        frames = (f"data: {json.dumps({'n': n, 'pad': 'x' * 400})}\n\n" for n in range(10))
        return StreamingResponse(frames, media_type="text/event-stream")

    return TestClient(app)


def test_a_large_json_answer_is_compressed(client: TestClient) -> None:
    response = client.get("/big", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert int(response.headers["content-length"]) < len(json.dumps(BIG)) / 2
    assert response.json() == BIG


def test_a_client_that_does_not_ask_for_gzip_gets_plain_json(
    client: TestClient,
) -> None:
    response = client.get("/big", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in response.headers
    assert response.json() == BIG


def test_a_small_answer_is_not_compressed(client: TestClient) -> None:
    response = client.get("/small", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in response.headers
    assert len(response.content) < MINIMUM_SIZE


def test_audio_is_sent_as_it_is_and_still_answers_a_byte_range(
    client: TestClient,
) -> None:
    whole = client.get("/audio", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in whole.headers
    part = client.get("/audio", headers={"Accept-Encoding": "gzip", "Range": "bytes=4-19"})
    assert part.status_code == 206
    assert "content-encoding" not in part.headers
    assert part.content == whole.content[4:20]


def test_the_progress_stream_is_not_compressed(client: TestClient) -> None:
    response = client.get("/stream", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in response.headers
    assert response.text.count("data:") == 10


def test_the_level_is_the_measured_one() -> None:
    # Level 9 took 35 ms on the largest piece for 8% fewer bytes than level 5 (5 ms).
    assert COMPRESS_LEVEL == 5
