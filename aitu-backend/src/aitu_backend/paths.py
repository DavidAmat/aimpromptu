"""Filesystem paths for runtime data (repo-root `data/`)."""

from pathlib import Path


def repo_root() -> Path:
    """`aitu-backend/` — parent of `src/`."""
    return Path(__file__).resolve().parent.parent.parent


def scores_json_path() -> Path:
    return repo_root() / "data" / "example-scores.json"
