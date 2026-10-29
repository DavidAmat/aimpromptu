"""The folders of My projects and of My Library (implementation 04-3, Phase 1, plan section 4.2).

A user has two independent trees of folders: ``projects`` (the projects of the Personal Vault) and ``library`` (the
songs of the Private Library). A folder is a row with its own id and the id of its parent folder (``None`` at the
top); a project or a song points at the folder id (``folder_projects``, ``folder_songs``), never at a path. Moving a
folder, or making a parent folder on top of some folders, therefore changes the rows of those folders only, and the
items inside them follow.

An item can be in several folders, or in none (it is then listed under the folders, at the top level). Deleting a
folder deletes its child folders (the table's ``ON DELETE CASCADE``) and the links of the items inside them, never
an item.

Every function takes the owner and answers :class:`~aitu_backend.library.rows.NotFound` for a folder, a project or a
song of another user, as the rest of the library does (section 9.3 of implementation 02).
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    FOLDER_AREAS,
    Folder,
    FolderProject,
    FolderSong,
    Project,
)
from aitu_backend.library import rows

__all__ = [
    "NAME_LIMIT",
    "copy_project_folders",
    "create",
    "delete_folder",
    "drop_project_folders",
    "folder",
    "folders_of_projects",
    "folders_of_songs",
    "list_of",
    "make_parent",
    "move",
    "rename",
    "set_project_folders",
    "set_song_folders",
]

NAME_LIMIT = 200


def _area(area: str) -> str:
    if area not in FOLDER_AREAS:
        raise ValueError(f"No folders in {area!r}")
    return area


def folder(db: DbSession, owner: int, folder_id: int, area: str | None = None) -> Folder:
    row = db.get(Folder, folder_id)
    if row is None or row.owner_id != owner or (area is not None and row.area != area):
        raise rows.NotFound(f"No folder with id {folder_id}")
    return row


def list_of(db: DbSession, owner: int, area: str) -> list[Folder]:
    """Every folder of the owner in the area, by name."""
    found = list(
        db.scalars(select(Folder).where(Folder.owner_id == owner, Folder.area == _area(area)))
    )
    found.sort(key=lambda row: (rows.same(row.name), row.id))
    return found


def _check_name(
    db: DbSession,
    owner: int,
    area: str,
    parent_id: int | None,
    name: str,
    *,
    ignore: frozenset[int] | set[int] = frozenset(),
) -> str:
    """``name`` cleaned; refused when another folder with the same parent has it (ignoring case)."""
    name = rows.clean(name, "A folder's name", NAME_LIMIT)
    wanted = rows.same(name)
    for sibling in list_of(db, owner, area):
        if (
            sibling.parent_id == parent_id
            and sibling.id not in ignore
            and rows.same(sibling.name) == wanted
        ):
            raise rows.Conflict(f"This folder already has a folder called “{sibling.name}”")
    return name


def create(db: DbSession, owner: int, area: str, name: str, parent_id: int | None = None) -> Folder:
    """A new folder at the top, or inside ``parent_id``."""
    _area(area)
    if parent_id is not None:
        folder(db, owner, parent_id, area)
    made = Folder(
        owner_id=owner,
        area=area,
        parent_id=parent_id,
        name=_check_name(db, owner, area, parent_id, name),
    )
    db.add(made)
    db.flush()
    return made


def rename(db: DbSession, owner: int, folder_id: int, name: str) -> Folder:
    row = folder(db, owner, folder_id)
    row.name = _check_name(db, owner, row.area, row.parent_id, name, ignore={row.id})
    db.flush()
    return row


def _inside(db: DbSession, owner: int, area: str, folder_id: int) -> set[int]:
    """The folder and every folder inside it, at any depth."""
    children: dict[int | None, list[int]] = {}
    for row in list_of(db, owner, area):
        children.setdefault(row.parent_id, []).append(row.id)
    found, waiting = set(), [folder_id]
    while waiting:
        current = waiting.pop()
        if current in found:
            continue
        found.add(current)
        waiting.extend(children.get(current, []))
    return found


def move(db: DbSession, owner: int, folder_id: int, parent_id: int | None) -> Folder:
    """The folder goes inside ``parent_id`` (``None``: to the top). Refused into itself or into a folder inside it."""
    row = folder(db, owner, folder_id)
    if parent_id is not None:
        folder(db, owner, parent_id, row.area)
        if parent_id in _inside(db, owner, row.area, row.id):
            raise rows.Conflict("A folder cannot go inside itself or inside one of its own folders")
    if parent_id == row.parent_id:
        return row
    _check_name(db, owner, row.area, parent_id, row.name, ignore={row.id})
    row.parent_id = parent_id
    db.flush()
    return row


def make_parent(db: DbSession, owner: int, area: str, name: str, children: list[int]) -> Folder:
    """**New parent folder**: one new folder where ``children`` are, and ``children`` moved into it. The children
    must have the same parent folder."""
    if not children:
        raise ValueError("Choose the folders that go inside the new folder")
    found = [folder(db, owner, child, _area(area)) for child in dict.fromkeys(children)]
    parents = {row.parent_id for row in found}
    if len(parents) != 1:
        raise rows.Conflict("The folders must be in the same folder")
    parent_id = parents.pop()
    made = Folder(
        owner_id=owner,
        area=area,
        parent_id=parent_id,
        name=_check_name(db, owner, area, parent_id, name, ignore={row.id for row in found}),
    )
    db.add(made)
    db.flush()
    for row in found:
        row.parent_id = made.id
    db.flush()
    return made


def delete_folder(db: DbSession, owner: int, folder_id: int) -> None:
    """Delete the folder and the folders inside it; their items stay in **All** and in their other folders."""
    row = folder(db, owner, folder_id)
    ids = _inside(db, owner, row.area, row.id)
    # The table deletes the child folders and the links too; said here as well, so a database opened without
    # foreign keys gives the same answer.
    db.execute(delete(FolderProject).where(FolderProject.folder_id.in_(ids)))
    db.execute(delete(FolderSong).where(FolderSong.folder_id.in_(ids)))
    db.execute(delete(Folder).where(Folder.id.in_(ids)))
    db.flush()


# ----------------------------------------------------------------------- items


def _own_project(db: DbSession, owner: int, project_id: str) -> Project:
    row = db.get(Project, project_id)
    if row is None or row.owner_id != owner or row.layer != "vault":
        raise rows.NotFound(f"No project with id '{project_id}' in your projects")
    return row


def _folder_ids(db: DbSession, owner: int, area: str, folder_ids: list[int]) -> list[int]:
    wanted = list(dict.fromkeys(folder_ids))
    for folder_id in wanted:
        folder(db, owner, folder_id, area)
    return wanted


def set_project_folders(
    db: DbSession, owner: int, project_id: str, folder_ids: list[int]
) -> list[int]:
    """The folders of a project of My projects, all of them (an empty list: in no folder)."""
    _own_project(db, owner, project_id)
    wanted = _folder_ids(db, owner, "projects", folder_ids)
    db.execute(delete(FolderProject).where(FolderProject.project_id == project_id))
    db.add_all(FolderProject(folder_id=folder_id, project_id=project_id) for folder_id in wanted)
    db.flush()
    return wanted


def set_song_folders(db: DbSession, owner: int, song_id: int, folder_ids: list[int]) -> list[int]:
    """The folders of a song of My Library, all of them."""
    rows.song(db, owner, song_id)
    wanted = _folder_ids(db, owner, "library", folder_ids)
    db.execute(delete(FolderSong).where(FolderSong.song_id == song_id))
    db.add_all(FolderSong(folder_id=folder_id, song_id=song_id) for folder_id in wanted)
    db.flush()
    return wanted


def folders_of_projects(db: DbSession, project_ids: list[str]) -> dict[str, list[int]]:
    """``project id -> its folder ids``, for every id asked (an empty list for none)."""
    out: dict[str, list[int]] = {project_id: [] for project_id in project_ids}
    if project_ids:
        for folder_id, project_id in db.execute(
            select(FolderProject.folder_id, FolderProject.project_id)
            .where(FolderProject.project_id.in_(project_ids))
            .order_by(FolderProject.folder_id)
        ):
            out[project_id].append(folder_id)
    return out


def folders_of_songs(db: DbSession, song_ids: list[int]) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {song_id: [] for song_id in song_ids}
    if song_ids:
        for folder_id, song_id in db.execute(
            select(FolderSong.folder_id, FolderSong.song_id)
            .where(FolderSong.song_id.in_(song_ids))
            .order_by(FolderSong.folder_id)
        ):
            out[song_id].append(folder_id)
    return out


def copy_project_folders(db: DbSession, source_id: str, target_id: str) -> None:
    """**Duplicate**: the copy goes into the folders of the original, as a copy in the Finder stays beside it."""
    for folder_id in folders_of_projects(db, [source_id])[source_id]:
        db.add(FolderProject(folder_id=folder_id, project_id=target_id))
    db.flush()


def drop_project_folders(db: DbSession, project_id: str) -> None:
    """A project that leaves My projects (**Save to library**) leaves its folders: the two trees are independent."""
    db.execute(delete(FolderProject).where(FolderProject.project_id == project_id))
