# syntax=docker/dockerfile:1
#
# aitu-backend, development image (implementation 08, Phase 3; plan section 10.3).
#
# The image holds the system tools and the Python environment, nothing else. `compose.yaml` mounts
# the repository at the same place (/work/aimpromptu), so the code, the tests and the data are the
# host's own files, uvicorn reloads on every edit, and a note written in the container is a note on
# the host. A production image, with the code copied in, comes later (Q-5).
#
# PyTorch comes from PyPI exactly as `uv.lock` pins it. Its Linux wheel carries its own CUDA
# libraries (the nvidia-* packages), so the base does not need to be a CUDA image: the NVIDIA
# Container Toolkit adds the driver at run time, and that is all torch needs.
#
# Build from the repository root with `make build` (or `docker compose build backend`).

FROM ghcr.io/astral-sh/uv:0.11.3 AS uv
FROM denoland/deno:bin-2.9.7 AS deno

FROM python:3.12-slim-bookworm

# ffmpeg: the audio normaliser and yt-dlp's mp3 extraction. deno: the JavaScript runtime yt-dlp
# needs to read YouTube's player. curl: the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=deno /deno /usr/local/bin/deno

# The host user's id, so files written into the mounted repository belong to the host user and not
# to root. `make build` passes the real ids.
ARG UID=1000
ARG GID=1000
RUN groupadd --gid "${GID}" app \
    && useradd --uid "${UID}" --gid "${GID}" --create-home --home-dir /home/app app \
    && install -d -o app -g app /opt/venv /work/aimpromptu/aitu-backend

# The environment lives outside the mounted folder, so the host's own `.venv` (built for the host)
# is never used in here and the other way round.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_FROZEN=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /work/aimpromptu/aitu-backend

# Every engine and the dev tools (pytest, black, flake8, mypy). Only the two files that decide the
# environment are needed here, so a code change never rebuilds this layer.
RUN --mount=type=cache,target=/home/app/.cache/uv,uid=${UID},gid=${GID} \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-install-project \
        --extra transcription --extra transkun --extra muscriptor --group dev

# The package itself comes from the mounted `src/` (pytest's `pythonpath` does the same for tests).
ENV PYTHONPATH=/work/aimpromptu/aitu-backend/src \
    AITU_HOST=0.0.0.0 \
    AITU_PORT=8765

EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
    CMD curl -fsS "http://127.0.0.1:${AITU_PORT}/health" || exit 1

CMD ["sh", "-c", "exec python -m uvicorn aitu_backend.main:app --host \"$AITU_HOST\" --port \"$AITU_PORT\" --reload --reload-dir src"]
