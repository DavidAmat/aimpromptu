"""The SQLite file of ``.database/`` and the one way to open it (implementation 02, plan section 8).

:func:`engine` opens ``.database/aitu.sqlite`` the first time it is asked for, after making the
folder and bringing the tables to the newest Alembic revision. The engine is kept per file, so a
test that points ``AITU_DATABASE_DIR`` at its own folder gets its own database.

SQLite runs in WAL mode (readers do not wait for a writer, and ``make db-backup`` can copy a
running database) with foreign keys on, which SQLite leaves off unless asked.
"""

from __future__ import annotations

import shutil
import sqlite3
import threading
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from aitu_backend.storage import paths

__all__ = [
    "HEAD_REVISION",
    "LAYOUT_VERSION",
    "LayoutVersionMismatch",
    "engine",
    "forget_engines",
    "migrate",
    "session",
]

#: The layout of ``.database/`` that this code reads and writes, written to ``VERSION``.
LAYOUT_VERSION = "1"
#: The newest Alembic revision in ``db/migrations/versions``. A database already at this revision
#: is opened without loading Alembic (each test opens a new one).
HEAD_REVISION = "0001"

#: A database at :data:`HEAD_REVISION`, copied instead of migrated. The tests set it once per run.
template_path: Path | None = None

#: Engines kept open, newest last. A test run opens one per test; the old ones are closed.
MAX_ENGINES = 4

_engines: "OrderedDict[Path, Engine]" = OrderedDict()
_lock = threading.Lock()


class LayoutVersionMismatch(RuntimeError):
    """``.database/VERSION`` names a layout this code does not know."""


def _on_connect(connection: sqlite3.Connection, _record: object) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def _check_layout() -> None:
    """Make the folder, and write or check ``VERSION``."""
    root = paths.database_dir()
    root.mkdir(parents=True, exist_ok=True)
    version = paths.layout_version_path()
    if not version.is_file():
        version.write_text(LAYOUT_VERSION + "\n", encoding="utf-8")
        return
    found = version.read_text(encoding="utf-8").strip()
    if found != LAYOUT_VERSION:
        raise LayoutVersionMismatch(
            f"{version} says layout {found!r}; this code reads layout {LAYOUT_VERSION!r}"
        )


def _revision(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        with sqlite3.connect(path) as connection:
            row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def migrate(path: Path | None = None) -> None:
    """Bring the database at ``path`` (default: the one of ``.database/``) to the newest revision."""
    from alembic import command  # noqa: PLC0415 - slow to import, rarely needed
    from alembic.config import Config  # noqa: PLC0415

    target = path or paths.sqlite_path()
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{target}")
    command.upgrade(config, "head")


def _prepare(path: Path) -> None:
    _check_layout()
    if not path.is_file() and template_path is not None and template_path.is_file():
        shutil.copyfile(template_path, path)
    if _revision(path) != HEAD_REVISION:
        migrate(path)


def engine() -> Engine:
    """The engine of the current ``.database/``, opened and migrated on first use."""
    path = paths.sqlite_path()
    with _lock:
        found = _engines.get(path)
        if found is not None:
            _engines.move_to_end(path)
            return found
        _prepare(path)
        made = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        event.listen(made, "connect", _on_connect)
        _engines[path] = made
        while len(_engines) > MAX_ENGINES:
            _, old = _engines.popitem(last=False)
            old.dispose()
        return made


def forget_engines() -> None:
    """Close every engine (a restore replaced the file under them, or a test ended)."""
    with _lock:
        while _engines:
            _, old = _engines.popitem()
            old.dispose()


@contextmanager
def session() -> Iterator[Session]:
    """One unit of work: committed when the block ends, rolled back when it raises."""
    with Session(engine(), expire_on_commit=False) as opened:
        try:
            yield opened
            opened.commit()
        except BaseException:
            opened.rollback()
            raise
