"""Settings shared by every test."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from aitu_backend.db import database
from aitu_backend.storage import locate

# Before any test module is imported: code that runs while the tests are collected (a `skipif`, a
# module-level client) must never reach the real `.database/`, which the container mounts.
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
