"""`.database/`: the layout, the tables, the master user, and finding a part (implementation 02,
Phase 3, plan sections 8.1, 8.2, 8.6 and 9.1)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import func, select

from aitu_backend.db import database
from aitu_backend.db.database import session
from aitu_backend.db.models import (
    GENRES,
    TAG_CATEGORIES,
    Genre,
    Region,
    TagCategory,
    User,
)
from aitu_backend.db.users import ensure_master_user
from aitu_backend.storage import bundle, locate, paths


def test_the_folder_and_its_version_are_made_on_first_use(
    _temporary_database: Path,
) -> None:
    database.engine()
    assert paths.sqlite_path().is_file()
    assert paths.layout_version_path().read_text().strip() == database.LAYOUT_VERSION


def test_a_layout_this_code_does_not_know_is_refused(_temporary_database: Path) -> None:
    paths.layout_version_path().parent.mkdir(parents=True, exist_ok=True)
    paths.layout_version_path().write_text("99\n")
    with pytest.raises(database.LayoutVersionMismatch):
        database.engine()


def test_every_table_of_section_8_6_exists(_temporary_database: Path) -> None:
    database.engine()
    with sqlite3.connect(paths.sqlite_path()) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == database.HEAD_REVISION
    expected = {
        "users", "sessions", "projects", "parts", "audio_files", "audio_refs", "artists",
        "artist_names", "albums", "songs", "song_artists", "song_albums", "song_versions",
        "user_versions", "private_versions", "genres", "song_genres", "tag_categories",
        "tag_values", "song_tags", "regions", "song_regions", "chart_sources", "chart_entries",
        "playlists", "playlist_items", "likes", "library_shares", "requests", "request_items",
        "request_comments",
    }  # fmt: skip
    assert expected <= tables


def test_the_fixed_lists_are_written_by_the_first_migration(
    _temporary_database: Path,
) -> None:
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Genre)) == len(GENRES)
        assert set(db.scalars(select(TagCategory.name))) == set(TAG_CATEGORIES)
        assert list(db.scalars(select(Region.code))) == ["worldwide"]


def test_foreign_keys_and_wal_are_on(_temporary_database: Path) -> None:
    with database.engine().connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"


def test_the_migration_runs_on_an_empty_file_too(tmp_path: Path) -> None:
    target = tmp_path / "fresh.sqlite"
    database.migrate(target)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT count(*) FROM genres").fetchone()[0] == len(GENRES)


def test_the_master_user_is_made_once(
    _temporary_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AITU_MASTER_USERNAME", "david")
    first = ensure_master_user()
    assert ensure_master_user() == first
    with session() as db:
        users = list(db.scalars(select(User)))
    assert [(user.username, user.role, user.password_hash) for user in users] == [
        ("david", "master", None)
    ]


def test_a_part_finds_its_project_and_an_unknown_one_is_not_found(
    _temporary_database: Path,
) -> None:
    owner = ensure_master_user()
    project = bundle.create_project(owner_id=owner, title="One")
    where = locate.part(project.id)
    assert (where.project_id, where.owner_id, where.layer) == (
        project.id,
        owner,
        "vault",
    )
    assert paths.part_dir(project.id) == (
        paths.database_dir() / "users" / str(owner) / "vault" / project.id / "parts" / project.id
    )
    with pytest.raises(locate.NotFound):
        locate.part("missing")
    with pytest.raises(KeyError):
        paths.part_dir("missing")


def test_each_layer_has_its_folder(_temporary_database: Path) -> None:
    assert paths.layer_dir(3, "vault") == paths.users_dir() / "3" / "vault"
    assert paths.layer_dir(3, "private") == paths.users_dir() / "3" / "library"
    assert paths.layer_dir(3, "public") == paths.public_dir()
