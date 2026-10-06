"""Settings shared by every test."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from aitu_backend.auth import dependencies, throttle
from aitu_backend.auth.context import CurrentUser
from aitu_backend.db import database
from aitu_backend.db.users import ensure_master_user
from aitu_backend.storage import locate

# Before any test module is imported: code that runs while the tests are collected (a `skipif`, a
# module-level client) must never reach the real `.database/`, which the container mounts.
# The real one stays known, for the few tests that read the library (never write it).
os.environ.setdefault(
    "AITU_REAL_DATABASE_DIR",
    os.environ.get("AITU_DATABASE_DIR") or str(Path(__file__).resolve().parents[2] / ".database"),
)
os.environ["AITU_DATABASE_DIR"] = tempfile.mkdtemp(prefix="aitu-collect-database-")


@pytest.fixture(autouse=True)
def _no_data_dir_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ``AITU_DATA_DIR`` out of the tests.

    Some tests move the old data folder by patching ``paths.backend_root`` to a temporary folder. A
    data folder set in the environment would win over that patch. A test of the variable itself
    sets it again with ``monkeypatch.setenv``.
    """
    monkeypatch.delenv("AITU_DATA_DIR", raising=False)
    monkeypatch.delenv("AITU_MASTER_USERNAME", raising=False)
    monkeypatch.delenv("AITU_MASTER_PASSWORD", raising=False)


@pytest.fixture(scope="session")
def _database_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One database at the newest revision, made once per run and copied into every test."""
    path = tmp_path_factory.mktemp("database-template") / "aitu.sqlite"
    database.migrate(path)
    return path


@pytest.fixture(autouse=True)
def _temporary_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    _database_template: Path,
) -> Iterator[Path]:
    """A temporary ``.database/`` per test (implementation 02, plan section 22), so no test reads or
    writes the real one and no two tests share a project."""
    folder = tmp_path_factory.mktemp("database")
    monkeypatch.setenv("AITU_DATABASE_DIR", str(folder))
    monkeypatch.setattr(database, "template_path", _database_template)
    locate.forget()
    yield folder
    locate.forget()
    database.forget_engines()


def _as_master() -> CurrentUser:
    return CurrentUser(ensure_master_user(), "master", "master")


@pytest.fixture(autouse=True)
def _signed_in(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every request of a test acts as the master user, with no cookie, unless the test is marked
    ``real_login``: then it signs in through ``/auth`` like the browser (implementation 02,
    Phase 4)."""
    throttle.clear()
    if request.node.get_closest_marker("real_login") is None:
        monkeypatch.setattr(dependencies, "test_user", _as_master)
