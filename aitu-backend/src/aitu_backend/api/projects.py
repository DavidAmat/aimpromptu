"""``/projects``: the projects of the Personal Vault (implementation 02, plan section 8.8).

Phase 3 makes one route, **duplicate**, because the scripts that measure and check the app work on
a temporary copy of a project and can no longer copy a folder by hand: a project is a bundle plus
its rows in the database. Phase 5 adds the list, create, rename, delete, export and import.

A project made by this app has the id of its first part, so the uuid of a piece is also the id of
its project.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.db.users import current_user_id
from aitu_backend.storage import bundle, locate

router = APIRouter(prefix="/projects", tags=["projects"])


class DuplicateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    #: The title of the copy; the original's when absent.
    title: str | None = Field(None, max_length=300)


class ProjectOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    #: The ids of the parts, in order. The first one is the uuid the other routes take.
    parts: list[str]


@router.post(
    "/{project_id}/duplicate",
    status_code=201,
    response_model=ProjectOut,
    response_model_by_alias=True,
)
def duplicate(project_id: str, body: DuplicateIn | None = None) -> ProjectOut:
    """A copy of the project in the current user's Personal Vault, with new ids. The audio files
    are shared, not copied (P-3); staging, history and the video are not copied."""
    try:
        copy = bundle.duplicate_project(
            project_id,
            owner_id=current_user_id(),
            title=body.title if body else None,
        )
    except locate.NotFound as exc:
        raise HTTPException(status_code=404, detail=f"No project with id '{project_id}'") from exc
    return ProjectOut(id=copy.id, title=copy.title, parts=[part.id for part in copy.parts])
