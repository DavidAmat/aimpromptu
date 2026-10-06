"""Where a project or a part lives: its owner and its layer, from the ``projects`` and ``parts``
tables (implementation 02, plan section 8.8).

Every route keyed by a uuid works on a part (P-6), and every path of a part is under the folder of
its project, which depends on the owner and the layer. One lookup answers both, and its answer is
kept in memory: the paths of a part are asked for many times per request. A write that moves or
deletes a project (:mod:`aitu_backend.storage.bundle`) calls :func:`forget`. A part that is not
found is never kept, so a project made by another process (the migration) is found at once.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

__all__ = ["Location", "NotFound", "forget", "part", "project"]


class NotFound(KeyError):
    """No project or part with this id in the database."""

    def __init__(self, kind: str, item_id: str) -> None:
        self.kind = kind
        self.item_id = item_id
        super().__init__(f"No {kind} with id '{item_id}'")


@dataclass(frozen=True)
class Location:
    """A project's place on disk: ``users/<owner>/<layer folder>/<project>/`` or ``public/<id>/``."""

    project_id: str
    owner_id: int
    layer: str


_lock = threading.Lock()
#: ``(database folder, id) -> Location``, for projects and parts alike.
_parts: dict[tuple[Path, str], Location] = {}
_projects: dict[tuple[Path, str], Location] = {}


def _root() -> Path:
    from aitu_backend.storage import paths  # noqa: PLC0415 - paths imports this module

    return paths.database_dir()


def part(part_id: str) -> Location:
    """The project of a part. Raises :class:`NotFound`."""
    key = (_root(), part_id)
    with _lock:
        found = _parts.get(key)
    if found is not None:
        return found
    from aitu_backend.db.database import session  # noqa: PLC0415 - avoids a cycle
    from aitu_backend.db.models import Part, Project  # noqa: PLC0415

    with session() as db:
        row = db.execute(
            select(Project.id, Project.owner_id, Project.layer)
            .join(Part, Part.project_id == Project.id)
            .where(Part.id == part_id)
        ).first()
    if row is None:
        raise NotFound("part", part_id)
    location = Location(project_id=row[0], owner_id=row[1], layer=row[2])
    with _lock:
        _parts[key] = location
    return location


def project(project_id: str) -> Location:
    """The place of a project. Raises :class:`NotFound`."""
    key = (_root(), project_id)
    with _lock:
        found = _projects.get(key)
    if found is not None:
        return found
    from aitu_backend.db.database import session  # noqa: PLC0415
    from aitu_backend.db.models import Project  # noqa: PLC0415

    with session() as db:
        row = db.execute(
            select(Project.owner_id, Project.layer).where(Project.id == project_id)
        ).first()
    if row is None:
        raise NotFound("project", project_id)
    location = Location(project_id=project_id, owner_id=row[0], layer=row[1])
    with _lock:
        _projects[key] = location
    return location


def forget(project_id: str | None = None) -> None:
    """Drop what is kept about one project and its parts, or about everything."""
    with _lock:
        if project_id is None:
            _parts.clear()
            _projects.clear()
            return
        for store in (_parts, _projects):
            for key in [key for key, value in store.items() if value.project_id == project_id]:
                del store[key]
