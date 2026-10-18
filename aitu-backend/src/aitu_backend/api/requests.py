"""``/requests``: requests to the Public Library (implementation 02, Phase 14, plan section 16).

Every user sends their own requests, sees them (**Requests** in the sidebar), sends one again when
changes are asked, and withdraws one until it is reviewed. The master user reads every request and
decides them through ``/admin/requests`` (:mod:`aitu_backend.api.admin`). The rules are in
:mod:`aitu_backend.library.requests`.

A request is read by its author and the master user; anyone else gets **404**, as for a project
(section 9.3). The routes name their request ``request_id`` and never ``project_id``: the router's
rights check reads a ``project_id`` as a project to check.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.auth import context, rights
from aitu_backend.db.database import session
from aitu_backend.db.users import current_user_id
from aitu_backend.library import flow, rows
from aitu_backend.library import requests as library_requests

router = APIRouter(prefix="/requests", tags=["requests"])


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SummaryOut(_Camel):
    id: int
    kind: str
    status: str
    author: str
    title: str
    subject: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    decided_at: datetime | None = Field(None, alias="decidedAt")
    waiting: int
    items: int


class ProjectRefOut(_Camel):
    project_id: str = Field(..., alias="projectId")
    parts: list[str]
    creator: str
    name: str
    kept: bool


class CompareOut(_Camel):
    current: ProjectRefOut | None = None
    proposed: ProjectRefOut | None = None


class ItemOut(_Camel):
    id: int
    kind: str
    decision: str | None = None
    comment: str | None = None
    payload: dict[str, Any]
    compare: CompareOut | None = None


class CommentOut(_Camel):
    id: int
    #: ``comment``, or an event: ``review``, ``sentAgain``, ``withdrawn``.
    kind: str
    author: str
    body: str
    created_at: datetime = Field(..., alias="createdAt")
    item_id: int | None = Field(None, alias="itemId")
    parent_id: int | None = Field(None, alias="parentId")
    #: A comment on a stretch: ``partId``, ``fromMs``, ``toMs``, ``excerpt``, ``excerptPart``,
    #: ``anchorMs``. A review: ``items``, each ``{id, kind, decision, comment}``.
    details: dict[str, Any] = Field(default_factory=dict)


class CommentIn(_Camel):
    body: str = Field(..., max_length=4000)
    #: A reply to this comment.
    parent_id: int | None = Field(None, alias="parentId")
    #: A comment on a stretch of the proposed sheet of this item: its part and its stretch.
    item_id: int | None = Field(None, alias="itemId")
    part_id: str | None = Field(None, alias="partId")
    from_ms: float | None = Field(None, alias="fromMs", ge=0)
    to_ms: float | None = Field(None, alias="toMs", gt=0)


class DetailOut(SummaryOut):
    #: The viewer is its author: they may send it again or withdraw it while it waits.
    mine: bool
    items_out: list[ItemOut] = Field(..., alias="itemList")
    comments: list[CommentOut]
    #: The proposal as it would be sent again.
    proposal: dict[str, Any]


class CreatedOut(_Camel):
    id: int


class CountsOut(_Camel):
    #: The user's requests with changes asked.
    mine: int
    #: The open requests to review (the master user).
    review: int


class ArtistOfSongOut(_Camel):
    private_id: int = Field(..., alias="privateId")
    name: str
    public_id: int | None = Field(None, alias="publicId")
    public_name: str | None = Field(None, alias="publicName")


class PublishInfoOut(_Camel):
    version_id: int = Field(..., alias="versionId")
    version_name: str = Field(..., alias="versionName")
    suggested_name: str = Field(..., alias="suggestedName")
    ready: bool
    song_id: int = Field(..., alias="songId")
    song_title: str = Field(..., alias="songTitle")
    artists: list[ArtistOfSongOut]
    public_song_id: int | None = Field(None, alias="publicSongId")
    public_song_title: str | None = Field(None, alias="publicSongTitle")
    own_versions: list[str] = Field(..., alias="ownVersions")
    waiting_request: int | None = Field(None, alias="waitingRequest")


class PlaylistInfoOut(_Camel):
    title: str
    items: list[dict[str, Any]]
    left: list[str]


@contextmanager
def _answers() -> Iterator[None]:
    try:
        yield
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (rows.Conflict, flow.Refused) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def summary_out(found: library_requests.Summary) -> SummaryOut:
    return SummaryOut(
        id=found.id,
        kind=found.kind,
        status=found.status,
        author=found.author,
        title=found.title,
        subject=found.subject,
        created_at=found.created_at,
        updated_at=found.updated_at,
        decided_at=found.decided_at,
        waiting=found.waiting,
        items=found.items,
    )


def _ref_out(found: library_requests.ProjectRef | None) -> ProjectRefOut | None:
    if found is None:
        return None
    return ProjectRefOut(
        project_id=found.project_id,
        parts=found.parts,
        creator=found.creator,
        name=found.name,
        kept=found.kept,
    )


def detail_out(request_id: int) -> DetailOut:
    """A request for the user of this call: its author or the master user (else 404)."""
    user = context.current()
    row = library_requests.request_row(request_id)
    if user is None or not rights.can_read_request(user, row):
        raise rows.NotFound(f"No request with id {request_id}")
    found = library_requests.detail(request_id)
    base = summary_out(found.summary)
    return DetailOut(
        **base.model_dump(),
        mine=found.author_id == user.id,
        items_out=[
            ItemOut(
                id=one.id,
                kind=one.kind,
                decision=one.decision,
                comment=one.comment,
                payload=one.payload,
                compare=(
                    CompareOut(
                        current=_ref_out(one.compare.current),
                        proposed=_ref_out(one.compare.proposed),
                    )
                    if one.compare is not None
                    else None
                ),
            )
            for one in found.items
        ],
        comments=[
            CommentOut(
                id=one.id,
                kind=one.kind,
                author=one.author,
                body=one.body,
                created_at=one.created_at,
                item_id=one.item_id,
                parent_id=one.parent_id,
                details=one.details,
            )
            for one in found.comments
        ],
        proposal=found.proposal,
    )


@router.get("", response_model=list[SummaryOut], response_model_by_alias=True)
def list_mine() -> list[SummaryOut]:
    """The user's requests, the most recently changed first."""
    return [summary_out(one) for one in library_requests.mine(current_user_id())]


@router.get("/counts", response_model=CountsOut)
def counts() -> CountsOut:
    """The numbers beside **Requests** and **Review** in the sidebar."""
    user = context.current()
    is_master = bool(user and user.is_master)
    mine, review = library_requests.counts(current_user_id(), is_master)
    return CountsOut(mine=mine, review=review)


@router.get("/publish-info", response_model=PublishInfoOut, response_model_by_alias=True)
def publish_info(version: int = Query(...)) -> PublishInfoOut:
    """What the **Publish** dialog of a version of My library starts from."""
    with _answers():
        found = library_requests.publish_info(current_user_id(), version)
    return PublishInfoOut(
        version_id=found.version_id,
        version_name=found.version_name,
        suggested_name=found.suggested_name,
        ready=found.ready,
        song_id=found.song_id,
        song_title=found.song_title,
        artists=[
            ArtistOfSongOut(
                private_id=one.private_id,
                name=one.name,
                public_id=one.public_id,
                public_name=one.public_name,
            )
            for one in found.artists
        ],
        public_song_id=found.public_song_id,
        public_song_title=found.public_song_title,
        own_versions=found.own_versions,
        waiting_request=found.waiting_request,
    )


@router.get("/playlist-info", response_model=PlaylistInfoOut)
def playlist_info(playlist: int = Query(...)) -> PlaylistInfoOut:
    """What a songs playlist of My library would hold in the Public Library, and what is left out."""
    with _answers(), session() as db:
        found = library_requests.playlist_info(db, current_user_id(), playlist)
    return PlaylistInfoOut(title=found.title, items=found.items, left=found.left)


@router.post("", response_model=CreatedOut, status_code=201)
def send(body: library_requests.Proposal) -> CreatedOut:
    """Send a request (its kind in the body). A ``userVersion`` copies the project now."""
    with _answers():
        return CreatedOut(id=library_requests.create(current_user_id(), body))


@router.get("/{request_id}", response_model=DetailOut, response_model_by_alias=True)
def get_request(request_id: int) -> DetailOut:
    with _answers():
        return detail_out(request_id)


@router.put("/{request_id}", response_model=DetailOut, response_model_by_alias=True)
def send_again(request_id: int, body: library_requests.Proposal) -> DetailOut:
    """The author's changes, after the master user asked for some."""
    with _answers():
        library_requests.resend(request_id, current_user_id(), body)
        return detail_out(request_id)


@router.post("/{request_id}/withdraw", response_model=DetailOut, response_model_by_alias=True)
def withdraw(request_id: int) -> DetailOut:
    with _answers():
        library_requests.withdraw(request_id, current_user_id())
        return detail_out(request_id)


@router.post(
    "/{request_id}/comments",
    response_model=DetailOut,
    response_model_by_alias=True,
    status_code=201,
)
def comment(request_id: int, body: CommentIn) -> DetailOut:
    """A comment of the author or the master user: on the request, a reply, or on a stretch of
    the proposed sheet (a project of just that stretch is kept beside it, so the conversation
    draws it as it was)."""
    user = context.current()
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in first.")
    with _answers():
        library_requests.add_comment(
            request_id,
            user.id,
            user.is_master,
            body.body,
            parent_id=body.parent_id,
            item_id=body.item_id,
            part_id=body.part_id,
            from_ms=body.from_ms,
            to_ms=body.to_ms,
        )
        return detail_out(request_id)
