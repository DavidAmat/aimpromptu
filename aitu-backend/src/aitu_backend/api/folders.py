"""``/folders``: the folders of My projects and of My Library (implementation 04-3, Phase 1, plan
section 4.2).

``area`` is ``projects`` (My projects) or ``library`` (My Library): two independent trees. Every
route works on the user's own folders only and answers 404 for another user's, as the library routes
do. The rows of ``GET /projects`` and ``GET /library/songs`` carry the folder ids of each item; the
page draws the tree from them and from ``GET /folders``. The logic is in
:mod:`aitu_backend.library.folders`.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.db.database import session
from aitu_backend.db.models import Folder
from aitu_backend.db.users import current_user_id
from aitu_backend.library import folders, rows

router = APIRouter(prefix="/folders", tags=["folders"])

Area = Literal["projects", "library"]


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class FolderRow(_Camel):
    id: int
    #: ``None`` at the top of the tree.
    parent_id: int | None = Field(None, alias="parentId")
    name: str
    created_at: datetime = Field(..., alias="createdAt")


class FolderIn(_Camel):
    area: Area
    name: str = Field(..., max_length=folders.NAME_LIMIT)
    #: Inside this folder; at the top when absent.
    parent_id: int | None = Field(None, alias="parentId")


class RenameIn(_Camel):
    name: str = Field(..., max_length=folders.NAME_LIMIT)


class MoveIn(_Camel):
    #: The new parent folder; ``None`` moves the folder to the top.
    parent_id: int | None = Field(None, alias="parentId")


class ParentIn(_Camel):
    """**New parent folder**: a folder made where ``children`` are, with ``children`` moved into it."""

    area: Area
    name: str = Field(..., max_length=folders.NAME_LIMIT)
    children: list[int] = Field(..., min_length=1, max_length=500)


class MembershipIn(_Camel):
    #: Every folder of the item; an empty list takes it out of every folder.
    folders: list[int] = Field(default_factory=list, max_length=500)


class MembershipOut(_Camel):
    folders: list[int]


@contextmanager
def _answers() -> Iterator[None]:
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except rows.Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _row(found: Folder) -> FolderRow:
    return FolderRow(
        id=found.id, parent_id=found.parent_id, name=found.name, created_at=found.created_at
    )


@router.get("", response_model=list[FolderRow], response_model_by_alias=True)
def list_folders(area: Area) -> list[FolderRow]:
    """Every folder of the user in the area, by name; the page nests them by ``parentId``."""
    with session() as db:
        return [_row(one) for one in folders.list_of(db, current_user_id(), area)]


@router.post("", response_model=FolderRow, response_model_by_alias=True, status_code=201)
def create_folder(body: FolderIn) -> FolderRow:
    """**New folder**, at the top or inside a folder. ``409`` when its parent already has a folder
    of that name."""
    with _answers(), session() as db:
        return _row(folders.create(db, current_user_id(), body.area, body.name, body.parent_id))


@router.post("/parent", response_model=FolderRow, response_model_by_alias=True, status_code=201)
def new_parent_folder(body: ParentIn) -> FolderRow:
    """**New parent folder** on top of folders that have the same parent. The items of those
    folders do not change: they point at the folders' ids, which stay."""
    with _answers(), session() as db:
        return _row(folders.make_parent(db, current_user_id(), body.area, body.name, body.children))


@router.patch("/{folder_id}", response_model=FolderRow, response_model_by_alias=True)
def rename_folder(folder_id: int, body: RenameIn) -> FolderRow:
    with _answers(), session() as db:
        return _row(folders.rename(db, current_user_id(), folder_id, body.name))


@router.post("/{folder_id}/move", response_model=FolderRow, response_model_by_alias=True)
def move_folder(folder_id: int, body: MoveIn) -> FolderRow:
    """**Move to…**: the folder goes inside another one, or to the top. ``409`` into itself or into
    one of its own folders."""
    with _answers(), session() as db:
        return _row(folders.move(db, current_user_id(), folder_id, body.parent_id))


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: int) -> None:
    """Delete the folder and the folders inside it. No project and no song is deleted: they stay in
    **All** and in their other folders."""
    with _answers(), session() as db:
        folders.delete_folder(db, current_user_id(), folder_id)


@router.put("/projects/{project_id}", response_model=MembershipOut, response_model_by_alias=True)
def set_project_folders(project_id: str, body: MembershipIn) -> MembershipOut:
    """The folders of a project of My projects, all of them (the "Folders…" dialog, a drag)."""
    with _answers(), session() as db:
        return MembershipOut(
            folders=folders.set_project_folders(db, current_user_id(), project_id, body.folders)
        )


@router.put("/songs/{song_id}", response_model=MembershipOut, response_model_by_alias=True)
def set_song_folders(song_id: int, body: MembershipIn) -> MembershipOut:
    """The folders of a song of My Library, all of them."""
    with _answers(), session() as db:
        return MembershipOut(
            folders=folders.set_song_folders(db, current_user_id(), song_id, body.folders)
        )
