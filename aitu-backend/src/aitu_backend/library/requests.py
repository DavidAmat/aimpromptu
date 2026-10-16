"""Requests to the Public Library, and their review (implementation 02, Phase 14, plan section 16).

The app context: "in order to publish something into the public library, we need to open a
request, so the master user needs to review it", like a pull request. A request has a **kind** and
is made of **items**, one per proposed change, each with its own decision: that is what lets the
master user accept part of it (the new song and its artist, but not the piano sheet).

=================  ==========================================================  ===================
Kind               What it proposes                                            Items
=================  ==========================================================  ===================
``userVersion``    A version of My library as the author's user version of a   ``newArtist``*,
                   public song (new, or replacing the author's own of that     ``newSong``?,
                   name); the song and its artists may be proposed with it     ``project``
``metadata``       A change of a public song (title, year, artists, genres,    ``newArtist``*, and
                   regions, tags) or artist (its name, more names), or a new   ``metadata`` or
                   song or artist                                              ``newSong``
``fixedVersion``   The author's accepted user version as Hard, Medium, Easy    ``versionPointer``
                   or a new name of that song
``playlist``       A songs playlist of My library made public (the user,       ``playlist``
                   2026-10-16): its songs that have a public version
=================  ==========================================================  ===================

**Sending** checks everything a review would need, and **copies the project** of a ``userVersion``
into the layer ``request`` (``.database/requests/<id>/``; no audio bytes, P-3), so later edits in
the author's library do not change what is reviewed. No private id ever reaches a public row: a
new artist or song is proposed by its name, and its public id is made on acceptance (app context).
Items point at each other by a ``ref`` (a new song names its new artists by theirs).

**The review** (:func:`decide`) gives every waiting item a decision: accepted, refused, or changes
asked with a comment. The master user may change a name on accepting ("will either accept it or
change it", app context). What is accepted is written **at once, in one transaction**: the public
rows with new ids, the project copied to ``public/`` and its version pointer, the author as the
version's creator, and the links of the author's own song and artists to the public ones. An item
cannot be accepted when an item it needs is not (a song whose new artist is refused).

The request is then: ``changesAsked`` while an item asks for changes (the author changes the
proposal and sends it again, :func:`resend`: the items not accepted are replaced, the accepted
ones stay), else ``accepted``, ``refused`` or ``partlyAccepted``. The author may **withdraw** it
until it is reviewed.

The copies a request sent are kept with it, as the record of what was reviewed.
"""

from __future__ import annotations

import json
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.database import session
from aitu_backend.db.models import (
    Artist,
    ArtistName,
    Genre,
    Playlist,
    PlaylistItem,
    PrivateVersion,
    Project,
    Region,
    Request,
    RequestComment,
    RequestItem,
    Song,
    SongArtist,
    SongGenre,
    SongRegion,
    SongTag,
    SongVersion,
    TagCategory,
    TagValue,
    User,
    UserVersion,
)
from aitu_backend.library import catalogue, flow, public, rows
from aitu_backend.storage import bundle, locate

__all__ = [
    "Compare",
    "Detail",
    "ItemDecision",
    "ItemView",
    "Proposal",
    "Summary",
    "counts",
    "create",
    "decide",
    "detail",
    "for_review",
    "mine",
    "playlist_info",
    "publish_info",
    "resend",
    "simple_name",
    "withdraw",
]

#: The order accepted items are written in: what an item needs is written before it.
KIND_ORDER = ("newArtist", "newSong", "metadata", "project", "versionPointer", "playlist")
#: A request the author can still change or withdraw.
WAITING = ("open", "changesAsked")
#: At most two genres a song (section 15.3).
MAX_GENRES = 2


# ------------------------------------------------------------------ proposals


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ArtistRef(_Camel):
    """An artist of a proposed song: a public artist by its id, or a new one by its name."""

    public_id: int | None = Field(None, alias="publicId")
    new_name: str | None = Field(None, alias="newName", max_length=300)
    #: The author's own artist it stands for: linked to the public one once accepted.
    private_id: int | None = Field(None, alias="privateId")


class TagRef(_Camel):
    category: str = Field(..., max_length=64)
    value: str = Field(..., max_length=200)


class SongFields(_Camel):
    """A new song, or the proposed state of a public song (section 15.3)."""

    title: str = Field(..., max_length=300)
    year: int | None = Field(None, ge=1000, le=2100)
    artists: list[ArtistRef] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    #: Region codes; ``worldwide`` when none is given.
    regions: list[str] = Field(default_factory=list)
    tags: list[TagRef] = Field(default_factory=list)


class SongChoice(_Camel):
    """The public song a version is of: one that exists, or a new one."""

    public_id: int | None = Field(None, alias="publicId")
    new: SongFields | None = None
    #: The author's own song it stands for: linked to the public one once accepted.
    private_id: int | None = Field(None, alias="privateId")


class ArtistChange(_Camel):
    """A change of a public artist (``publicId``: a new default name, more names), or a new
    artist (no ``publicId``: its ``name``)."""

    public_id: int | None = Field(None, alias="publicId")
    name: str | None = Field(None, max_length=300)
    add_names: list[str] = Field(default_factory=list, alias="addNames")


class Proposal(_Camel):
    """What the author asks for, by kind. The same body sends a request and sends it again."""

    kind: Literal["userVersion", "metadata", "fixedVersion", "playlist"]
    #: A few words for the master user.
    note: str | None = Field(None, max_length=2000)
    # userVersion: a version of My library (``version``), as ``versionName`` of ``song``.
    version: int | None = None
    version_name: str | None = Field(None, alias="versionName", max_length=60)
    song: SongChoice | None = None
    # metadata: ``song.publicId`` with ``changes``; ``song.new`` (a new song); or ``artist``.
    changes: SongFields | None = None
    artist: ArtistChange | None = None
    # fixedVersion: the author's user version (its public project) as ``name``.
    user_version: str | None = Field(None, alias="userVersion")
    name: str | None = Field(None, max_length=60)
    # playlist: a songs playlist of My library, published as ``title``.
    playlist: int | None = None
    title: str | None = Field(None, max_length=300)


class ItemDecision(_Camel):
    id: int
    decision: Literal["accepted", "refused", "changesAsked"]
    comment: str | None = Field(None, max_length=2000)
    #: The master user's own change on accepting: ``name`` (a new artist; the fixed version),
    #: ``title`` and ``year`` (a new song; ``title``: a playlist), ``versionName`` (a version).
    changes: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------- helpers


def _now() -> datetime:
    return datetime.now(timezone.utc)


def simple_name(text: str) -> str:
    """The simple form of a version name (section 15.2): "Easy (left hand)" is
    ``easy-left-hand``. Empty when nothing of it is a letter or a digit."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    out: list[str] = []
    for char in folded:
        if char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")[:24].strip("-")


def _ref() -> str:
    return "r" + uuid.uuid4().hex[:10]


def _loads(item: RequestItem) -> dict[str, Any]:
    loaded = json.loads(item.payload or "{}")
    return loaded if isinstance(loaded, dict) else {}


def _items(db: DbSession, request_id: int) -> list[RequestItem]:
    return list(
        db.scalars(
            select(RequestItem)
            .where(RequestItem.request_id == request_id)
            .order_by(RequestItem.position, RequestItem.id)
        )
    )


def _request(db: DbSession, request_id: int) -> Request:
    found = db.get(Request, request_id)
    if found is None:
        raise rows.NotFound(f"No request with id {request_id}")
    return found


def _username(db: DbSession, user_id: int | None) -> str:
    if user_id is None:
        return ""
    return db.scalar(select(User.username).where(User.id == user_id)) or ""


def _default_name(db: DbSession, artist_id: int) -> ArtistName:
    names = rows.names_of(db, artist_id)
    if not names:
        raise rows.NotFound(f"The artist {artist_id} has no name")
    return next((one for one in names if one.is_default), names[0])


def _public_artist_named(db: DbSession, name: str) -> int | None:
    """A public artist with this name, ignoring case (ASCII) and spaces."""
    wanted = rows.same(name)
    for artist_id, found in db.execute(
        select(ArtistName.artist_id, ArtistName.name)
        .join(Artist, Artist.id == ArtistName.artist_id)
        .where(Artist.scope == "public", func.lower(ArtistName.name) == name.strip().lower())
    ):
        if rows.same(found) == wanted:
            return int(artist_id)
    return None


def _song_of_public_project(db: DbSession, project_id: str) -> int | None:
    found = db.scalar(select(SongVersion.song_id).where(SongVersion.project_id == project_id))
    if found is not None:
        return int(found)
    found = db.scalar(select(UserVersion.song_id).where(UserVersion.project_id == project_id))
    return int(found) if found is not None else None


# --------------------------------------------------------------- song fields


def _fixed_lists(db: DbSession) -> tuple[set[str], set[str], set[str]]:
    genres = set(db.scalars(select(Genre.name)))
    regions = set(db.scalars(select(Region.code)))
    categories = set(db.scalars(select(TagCategory.name)))
    return genres, regions, categories


@dataclass
class _Plan:
    """The items a proposal makes, before anything is written."""

    items: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    #: ``(the private project to copy, its title)`` for a ``userVersion``.
    snapshot: tuple[str, str] | None = None


def _artist_refs(db: DbSession, artists: list[ArtistRef], plan: _Plan) -> list[dict[str, Any]]:
    """Each artist as ``{"publicId"}``, or ``{"ref"}`` of a ``newArtist`` item made here."""
    out: list[dict[str, Any]] = []
    made: dict[str, str] = {}
    for one in artists:
        extra = {"privateId": one.private_id} if one.private_id is not None else {}
        if one.public_id is not None:
            public.public_artist(db, one.public_id)
            if any(ref.get("publicId") == one.public_id for ref in out):
                continue
            out.append({"publicId": one.public_id, **extra})
            continue
        name = rows.clean(one.new_name, "An artist's name")
        key = rows.same(name)
        if key not in made:
            if _public_artist_named(db, name) is not None:
                raise rows.Conflict(
                    f"The Public Library already has the artist “{name}”: choose it instead"
                )
            made[key] = _ref()
            plan.items.append(("newArtist", {"ref": made[key], "name": name}))
        out.append({"ref": made[key], **extra})
    return out


def _song_payload(db: DbSession, fields: SongFields, plan: _Plan) -> dict[str, Any]:
    """The fields of a song, checked against the fixed lists of section 15.3."""
    title = rows.clean(fields.title, "A song's title")
    if not fields.artists:
        raise ValueError("A song needs at least one artist")
    genres, regions, categories = _fixed_lists(db)
    chosen_genres = list(dict.fromkeys(fields.genres))
    if len(chosen_genres) > MAX_GENRES:
        raise ValueError("A song has at most two genres")
    for one in chosen_genres:
        if one not in genres:
            raise ValueError(f"No genre “{one}”")
    chosen_regions = list(dict.fromkeys(fields.regions)) or ["worldwide"]
    for one in chosen_regions:
        if one not in regions:
            raise ValueError(f"No region “{one}”")
    tags: list[list[str]] = []
    for tag in fields.tags:
        if tag.category not in categories:
            raise ValueError(f"No tag category “{tag.category}”")
        pair = [tag.category, rows.clean(tag.value, "A tag", 200)]
        if pair not in tags:
            tags.append(pair)
    return {
        "title": title,
        "year": fields.year,
        "artists": _artist_refs(db, fields.artists, plan),
        "genres": chosen_genres,
        "regions": chosen_regions,
        "tags": tags,
    }


def _song_state(db: DbSession, song_id: int) -> dict[str, Any]:
    """A public song's fields as they are, in the form of :func:`_song_payload`."""
    song = public.public_song(db, song_id)
    credits = rows.credits_of(db, [song_id])[song_id]
    genres = list(
        db.scalars(
            select(Genre.name)
            .join(SongGenre, SongGenre.genre_id == Genre.id)
            .where(SongGenre.song_id == song_id)
            .order_by(Genre.name)
        )
    )
    regions = list(
        db.scalars(
            select(Region.code)
            .join(SongRegion, SongRegion.region_id == Region.id)
            .where(SongRegion.song_id == song_id)
            .order_by(Region.code)
        )
    )
    tags = [
        [category, value]
        for category, value in db.execute(
            select(TagCategory.name, TagValue.value)
            .join(TagValue, TagValue.category_id == TagCategory.id)
            .join(SongTag, SongTag.tag_value_id == TagValue.id)
            .where(SongTag.song_id == song_id)
            .order_by(TagCategory.name, TagValue.value)
        )
    ]
    return {
        "title": song.title,
        "year": song.year,
        "artists": [{"publicId": one.artist_id, "nameId": one.name_id} for one in credits],
        "genres": genres,
        "regions": regions,
        "tags": tags,
    }


def _same_state(before: dict[str, Any], after: dict[str, Any]) -> bool:
    def artists(state: dict[str, Any]) -> list[Any]:
        return [one.get("publicId") or one.get("ref") for one in state["artists"]]

    return (
        before["title"] == after["title"]
        and before["year"] == after["year"]
        and artists(before) == artists(after)
        and sorted(before["genres"]) == sorted(after["genres"])
        and sorted(before["regions"]) == sorted(after["regions"])
        and sorted(map(tuple, before["tags"])) == sorted(map(tuple, after["tags"]))
    )


# --------------------------------------------------------------------- plans


def _waiting_twin(
    db: DbSession,
    author: int,
    kind: str,
    same: Callable[[dict[str, Any]], bool],
    skip: int | None,
) -> int | None:
    """Another waiting request of the author with an item not accepted yet that asks for the same
    thing (``same`` of its payload)."""
    for request in db.scalars(
        select(Request).where(
            Request.author_id == author, Request.kind == kind, Request.status.in_(WAITING)
        )
    ):
        if request.id == skip:
            continue
        for item in _items(db, request.id):
            if item.decision != "accepted" and same(_loads(item)):
                return request.id
    return None


def _plan_user_version(db: DbSession, author: int, proposal: Proposal, skip: int | None) -> _Plan:
    if proposal.version is None or proposal.song is None:
        raise ValueError("A version and its public song are needed")
    version = rows.version(db, author, proposal.version)
    if not flow.sheet_ready(bundle.read_project(version.project_id)):
        raise flow.Refused("Save the piano sheet of this version first")
    name = public.check_public_name(proposal.version_name or simple_name(version.version_name))
    plan = _Plan()
    choice = proposal.song
    if choice.public_id is not None:
        song = public.public_song(db, choice.public_id)
        song_ref: dict[str, Any] = {"publicId": song.id}
        title = song.title
    elif choice.new is not None:
        payload = _song_payload(db, choice.new, plan)
        _refuse_known_song(db, payload)
        ref = _ref()
        plan.items.append(("newSong", {"ref": ref, **payload}))
        song_ref, title = {"ref": ref}, payload["title"]
    else:
        raise ValueError("Choose the public song, or propose it")
    if choice.private_id is not None:
        song_ref["privateId"] = choice.private_id
    if "publicId" in song_ref:
        twin = _waiting_twin(
            db,
            author,
            "userVersion",
            lambda payload: payload.get("versionName") == name
            and payload.get("song", {}).get("publicId") == song_ref["publicId"],
            skip,
        )
        if twin is not None:
            raise rows.Conflict(f"Your request {twin} already asks for this version")
    plan.items.append(
        (
            "project",
            {
                "song": song_ref,
                "versionName": name,
                "sourceProjectId": version.project_id,
                "sourceVersionId": version.id,
            },
        )
    )
    plan.snapshot = (version.project_id, title)
    return plan


def _refuse_known_song(db: DbSession, payload: dict[str, Any]) -> None:
    """A new song is refused when the Public Library has one of that title by its first artist."""
    first = payload["artists"][0] if payload["artists"] else {}
    if "publicId" not in first:
        return
    for song_id in db.scalars(
        select(Song.id).where(
            Song.scope == "public", func.lower(Song.title) == payload["title"].lower()
        )
    ):
        if any(
            one.artist_id == first["publicId"] for one in rows.credits_of(db, [song_id])[song_id]
        ):
            raise rows.Conflict(
                f"The Public Library already has “{payload['title']}” by this artist: choose it"
            )


def _plan_metadata(db: DbSession, proposal: Proposal) -> _Plan:
    plan = _Plan()
    if proposal.song is not None and proposal.song.public_id is not None:
        if proposal.changes is None:
            raise ValueError("Say what changes")
        before = _song_state(db, proposal.song.public_id)
        after = _song_payload(db, proposal.changes, plan)
        # An artist the song keeps keeps the name it is credited with ("Jackson Five").
        credited = {one["publicId"]: one["nameId"] for one in before["artists"]}
        for one in after["artists"]:
            if one.get("publicId") in credited:
                one["nameId"] = credited[one["publicId"]]
        if _same_state(before, after):
            raise ValueError("Nothing is changed")
        plan.items.append(
            (
                "metadata",
                {
                    "target": "song",
                    "songId": proposal.song.public_id,
                    "before": before,
                    "after": after,
                },
            )
        )
        return plan
    if proposal.song is not None and proposal.song.new is not None:
        payload = _song_payload(db, proposal.song.new, plan)
        _refuse_known_song(db, payload)
        plan.items.append(("newSong", {"ref": _ref(), **payload}))
        return plan
    change = proposal.artist
    if change is None:
        raise ValueError("Choose a song or an artist")
    if change.public_id is None:
        name = rows.clean(change.name, "An artist's name")
        if _public_artist_named(db, name) is not None:
            raise rows.Conflict(f"The Public Library already has the artist “{name}”")
        plan.items.append(("newArtist", {"ref": _ref(), "name": name}))
        return plan
    public.public_artist(db, change.public_id)
    names = rows.names_of(db, change.public_id)
    default = _default_name(db, change.public_id).name
    rename = rows.clean(change.name, "An artist's name") if change.name else None
    if rename is not None and rename == default:
        rename = None
    own = {rows.same(one.name) for one in names}
    added: list[str] = []
    for one in change.add_names:
        name = rows.clean(one, "An artist's name")
        if rows.same(name) in own or rows.same(name) in {rows.same(a) for a in added}:
            continue
        other = _public_artist_named(db, name)
        if other is not None and other != change.public_id:
            raise rows.Conflict(f"“{name}” is a name of another artist")
        added.append(name)
    if rename is None and not added:
        raise ValueError("Nothing is changed")
    plan.items.append(
        (
            "metadata",
            {
                "target": "artist",
                "artistId": change.public_id,
                "before": {"name": default, "names": [one.name for one in names]},
                "name": rename,
                "addNames": added,
            },
        )
    )
    return plan


def _plan_fixed_version(db: DbSession, author: int, proposal: Proposal, skip: int | None) -> _Plan:
    if not proposal.user_version or not proposal.name:
        raise ValueError("Choose your version and the name it asks for")
    found = db.scalar(select(UserVersion).where(UserVersion.project_id == proposal.user_version))
    if found is None or found.user_id != author:
        raise rows.NotFound("That is not a version of yours in the Public Library")
    name = public.check_public_name(proposal.name)
    current = db.scalar(
        select(SongVersion.project_id).where(
            SongVersion.song_id == found.song_id, SongVersion.name == name
        )
    )
    if current == found.project_id:
        raise rows.Conflict(f"It is already the {name} version")
    twin = _waiting_twin(
        db,
        author,
        "fixedVersion",
        lambda payload: payload.get("projectId") == found.project_id
        and payload.get("name") == name,
        skip,
    )
    if twin is not None:
        raise rows.Conflict(f"Your request {twin} already asks for this")
    return _Plan(
        items=[
            (
                "versionPointer",
                {
                    "songId": found.song_id,
                    "projectId": found.project_id,
                    "name": name,
                    "userVersionName": found.version_name,
                },
            )
        ]
    )


@dataclass
class PlaylistInfo:
    title: str
    #: ``songId, projectId, fromMs, toMs, title, versionName``: what the public playlist holds.
    items: list[dict[str, Any]]
    #: The titles of the songs left out: not in the Public Library with a public version.
    left: list[str]


def public_counterpart(db: DbSession, author: int, project_id: str) -> tuple[int, str] | None:
    """``(public song, public project)`` a project of the author's library stands for: the public
    version it was pulled from, or the user version the author published from it."""
    row = db.get(Project, project_id)
    if row is None:
        return None
    if row.public_source_id:
        song_id = _song_of_public_project(db, row.public_source_id)
        if song_id is not None:
            return song_id, row.public_source_id
    for item in db.scalars(
        select(RequestItem)
        .join(Request, Request.id == RequestItem.request_id)
        .where(
            Request.author_id == author,
            RequestItem.kind == "project",
            RequestItem.decision == "accepted",
        )
        .order_by(RequestItem.id.desc())
    ):
        payload = _loads(item)
        made = payload.get("made") or {}
        if payload.get("sourceProjectId") == project_id and made.get("projectId"):
            song_id = _song_of_public_project(db, made["projectId"])
            if song_id is not None:
                return song_id, made["projectId"]
    return None


def playlist_info(db: DbSession, author: int, playlist_id: int) -> PlaylistInfo:
    """What a songs playlist of My library would be in the Public Library."""
    found = db.get(Playlist, playlist_id)
    if found is None or found.scope != "private" or found.owner_id != author:
        raise rows.NotFound(f"No playlist with id {playlist_id}")
    items: list[dict[str, Any]] = []
    left: list[str] = []
    for one in db.scalars(
        select(PlaylistItem)
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.position)
    ):
        song = db.get(Song, one.song_id) if one.song_id is not None else None
        title = song.title if song is not None else ""
        counterpart = public_counterpart(db, author, one.project_id) if one.project_id else None
        if counterpart is None:
            left.append(title)
            continue
        song_id, project_id = counterpart
        items.append(
            {
                "songId": song_id,
                "projectId": project_id,
                "fromMs": one.from_ms,
                "toMs": one.to_ms,
                "title": public.public_song(db, song_id).title,
                "versionName": public.version_name_of(db, project_id),
            }
        )
    return PlaylistInfo(title=found.title, items=items, left=left)


def _plan_playlist(db: DbSession, author: int, proposal: Proposal) -> _Plan:
    if proposal.playlist is None:
        raise ValueError("Choose a playlist")
    info = playlist_info(db, author, proposal.playlist)
    if not info.items:
        raise flow.Refused("No song of this playlist has a version in the Public Library yet")
    title = rows.clean(proposal.title or info.title, "A playlist's title")
    return _Plan(
        items=[
            (
                "playlist",
                {
                    "title": title,
                    "sourcePlaylistId": proposal.playlist,
                    "items": info.items,
                    "left": info.left,
                },
            )
        ]
    )


def _plan(db: DbSession, author: int, proposal: Proposal, skip: int | None = None) -> _Plan:
    if proposal.kind == "userVersion":
        return _plan_user_version(db, author, proposal, skip)
    if proposal.kind == "metadata":
        return _plan_metadata(db, proposal)
    if proposal.kind == "fixedVersion":
        return _plan_fixed_version(db, author, proposal, skip)
    return _plan_playlist(db, author, proposal)


def _snapshot(plan: _Plan, author: int) -> str | None:
    """The copy of the project a ``userVersion`` sends, in the layer ``request``."""
    if plan.snapshot is None:
        return None
    source, title = plan.snapshot
    copy = bundle.duplicate_project(source, owner_id=author, layer="request", title=title)
    for kind, payload in plan.items:
        if kind == "project":
            payload["projectId"] = copy.id
    return copy.id


def _add_items(db: DbSession, request_id: int, plan: _Plan, start: int) -> None:
    for position, (kind, payload) in enumerate(plan.items, start=start):
        db.add(
            RequestItem(
                request_id=request_id, position=position, kind=kind, payload=json.dumps(payload)
            )
        )


def _note(db: DbSession, request_id: int, author: int, text: str | None) -> None:
    body = " ".join((text or "").split())
    if body:
        db.add(
            RequestComment(request_id=request_id, author_id=author, body=body, created_at=_now())
        )


# ---------------------------------------------------------------------- send


def create(author: int, proposal: Proposal) -> int:
    """Send a request. Answers its id."""
    with session() as db:
        plan = _plan(db, author, proposal)
    snapshot = _snapshot(plan, author)
    try:
        with session() as db:
            moment = _now()
            made = Request(
                kind=proposal.kind,
                author_id=author,
                status="open",
                created_at=moment,
                updated_at=moment,
            )
            db.add(made)
            db.flush()
            _add_items(db, made.id, plan, 0)
            _note(db, made.id, author, proposal.note)
            return made.id
    except BaseException:
        if snapshot is not None:
            bundle.delete_project(snapshot)
        raise


def resend(request_id: int, author: int, proposal: Proposal) -> None:
    """The author's changes, sent again: every item not accepted is replaced by the new proposal's
    (the accepted ones stay, and the new proposal names their public rows)."""
    with session() as db:
        request = _request(db, request_id)
        if request.author_id != author:
            raise rows.NotFound(f"No request with id {request_id}")
        if request.status != "changesAsked":
            raise rows.Conflict("Only a request with changes asked can be sent again")
        if proposal.kind != request.kind:
            raise ValueError("A request keeps its kind")
        plan = _plan(db, author, proposal, skip=request_id)
    snapshot = _snapshot(plan, author)
    dropped: list[str] = []
    try:
        with session() as db:
            request = _request(db, request_id)
            items = _items(db, request_id)
            for item in items:
                if item.decision == "accepted":
                    continue
                payload = _loads(item)
                if item.kind == "project" and payload.get("projectId"):
                    dropped.append(payload["projectId"])
                db.delete(item)
            db.flush()
            start = max((item.position for item in items), default=-1) + 1
            _add_items(db, request_id, plan, start)
            request.status = "open"
            request.updated_at = _now()
            _note(db, request_id, author, proposal.note)
    except BaseException:
        if snapshot is not None:
            bundle.delete_project(snapshot)
        raise
    for project_id in dropped:
        _drop_snapshot(project_id)


def _drop_snapshot(project_id: str) -> None:
    try:
        if locate.project(project_id).layer == "request":
            bundle.delete_project(project_id)
    except locate.NotFound:
        pass


def withdraw(request_id: int, author: int) -> None:
    """The author takes back a request that is not reviewed yet; what was accepted stays."""
    with session() as db:
        request = _request(db, request_id)
        if request.author_id != author:
            raise rows.NotFound(f"No request with id {request_id}")
        if request.status not in WAITING:
            raise rows.Conflict("This request is already reviewed")
        request.status = "withdrawn"
        request.updated_at = request.decided_at = _now()


# -------------------------------------------------------------------- review


def _needs(kind: str, payload: dict[str, Any]) -> list[str]:
    """The refs of the items an item cannot be accepted without."""
    if kind == "newSong":
        return [one["ref"] for one in payload.get("artists", []) if "ref" in one]
    if kind == "metadata" and payload.get("target") == "song":
        return [one["ref"] for one in payload["after"].get("artists", []) if "ref" in one]
    if kind == "project":
        song = payload.get("song", {})
        return [song["ref"]] if "ref" in song else []
    return []


def _edit(kind: str, payload: dict[str, Any], changes: dict[str, Any]) -> None:
    """The master user's change of a name, on accepting."""
    allowed = {
        "newArtist": {"name"},
        "newSong": {"title", "year"},
        "project": {"versionName"},
        "versionPointer": {"name"},
        "playlist": {"title"},
    }.get(kind, set())
    for key, value in changes.items():
        if key not in allowed:
            raise ValueError(f"“{key}” cannot be changed on this item")
        if key == "name" and kind == "newArtist":
            payload["name"] = rows.clean(value, "An artist's name")
        elif key == "title":
            payload["title"] = rows.clean(value, "A title")
        elif key == "year":
            if value is not None and not (isinstance(value, int) and 1000 <= value <= 2100):
                raise ValueError("A year is a number such as 1977")
            payload["year"] = value
        elif key in ("versionName", "name"):
            payload[key] = public.check_public_name(str(value))


def _status(decisions: list[str | None]) -> str:
    if any(one is None for one in decisions):
        return "open"
    if any(one == "changesAsked" for one in decisions):
        return "changesAsked"
    if all(one == "accepted" for one in decisions):
        return "accepted"
    if all(one == "refused" for one in decisions):
        return "refused"
    return "partlyAccepted"


def decide(
    request_id: int,
    master_id: int,
    decisions: list[ItemDecision],
    comment: str | None = None,
) -> str:
    """The master user's review of an open request: a decision for every item waiting. What is
    accepted is published in one transaction. Answers the request's status."""
    with session() as db:
        request = _request(db, request_id)
        if request.status != "open":
            raise rows.Conflict("This request is not waiting for a review")
        items = _items(db, request_id)
        waiting = {item.id: item for item in items if item.decision is None}
        given = {one.id: one for one in decisions}
        if set(given) != set(waiting):
            raise ValueError("Give a decision to every item waiting, and only to those")
        payloads = {item.id: _loads(item) for item in items}
        for one in decisions:
            if one.decision == "accepted" and one.changes:
                _edit(waiting[one.id].kind, payloads[one.id], one.changes)
        accepted = {item.id for item in items if item.decision == "accepted"} | {
            one.id for one in decisions if one.decision == "accepted"
        }
        by_ref = {payloads[item.id]["ref"]: item for item in items if "ref" in payloads[item.id]}
        for item in items:
            if item.id not in accepted:
                continue
            for ref in _needs(item.kind, payloads[item.id]):
                needed = by_ref.get(ref)
                if needed is None or needed.id not in accepted:
                    raise rows.Conflict(_needs_message(item.kind, needed))
        author = request.author_id
        to_copy: list[tuple[int, str, str]] = []
        for one in decisions:
            item = waiting[one.id]
            if one.decision == "accepted" and item.kind == "project":
                payload = payloads[item.id]
                to_copy.append((item.id, payload["projectId"], _song_title(db, payload, payloads)))
        for one in decisions:
            item = waiting[one.id]
            if one.decision == "accepted" and item.kind == "versionPointer":
                _check_user_version(db, payloads[item.id], author)

    copies: dict[int, str] = {}
    try:
        for item_id, snapshot, title in to_copy:
            copies[item_id] = public.copy_to_public(snapshot, creator_id=author, title=title)
        with session() as db:
            replaced, status = _apply(db, request_id, given, payloads, copies, master_id, comment)
    except BaseException:
        for copy in copies.values():
            bundle.delete_project(copy)
        raise
    for project_id in replaced:
        public.delete_if_unused(project_id)
    catalogue.forget()
    return status


def _needs_message(kind: str, needed: RequestItem | None) -> str:
    if needed is not None and needed.kind == "newArtist":
        return "Accept its new artist first, or ask for a change"
    if needed is not None and needed.kind == "newSong":
        return "Accept the new song first, or ask for a change"
    return f"This {kind} needs an item that is not accepted"


def _song_title(db: DbSession, payload: dict[str, Any], payloads: dict[int, Any]) -> str:
    song = payload.get("song", {})
    if "publicId" in song:
        return public.public_song(db, song["publicId"]).title
    for other in payloads.values():
        if other.get("ref") == song.get("ref"):
            return str(other.get("title", ""))
    return ""


def _check_user_version(db: DbSession, payload: dict[str, Any], author: int) -> None:
    found = db.scalar(select(UserVersion).where(UserVersion.project_id == payload["projectId"]))
    if found is None or found.user_id != author:
        raise rows.Conflict("That user version is no longer in the Public Library")


@dataclass
class _Context:
    author: int
    #: ``ref -> what its accepted item made``.
    made: dict[str, dict[str, Any]]
    copies: dict[int, str]
    replaced: list[str] = field(default_factory=list)


def _apply(
    db: DbSession,
    request_id: int,
    given: dict[int, ItemDecision],
    payloads: dict[int, dict[str, Any]],
    copies: dict[int, str],
    master_id: int,
    comment: str | None,
) -> tuple[list[str], str]:
    request = _request(db, request_id)
    items = _items(db, request_id)
    context = _Context(
        author=request.author_id,
        made={
            payloads[item.id]["ref"]: payloads[item.id].get("made", {})
            for item in items
            if item.decision == "accepted" and "ref" in payloads[item.id]
        },
        copies=copies,
    )
    order = sorted(
        (item for item in items if item.id in given),
        key=lambda item: (KIND_ORDER.index(item.kind), item.position),
    )
    for item in order:
        decision = given[item.id]
        item.decision = decision.decision
        item.comment = " ".join((decision.comment or "").split()) or None
        payload = payloads[item.id]
        if decision.decision == "accepted":
            payload["made"] = _accept(db, item, payload, context)
            if "ref" in payload:
                context.made[payload["ref"]] = payload["made"]
        item.payload = json.dumps(payload)
    db.flush()
    status = _status([item.decision for item in items])
    request.status = status
    request.updated_at = _now()
    if status not in WAITING:
        request.decided_at = request.updated_at
    _note(db, request_id, master_id, comment)
    return context.replaced, status


def _name_id(db: DbSession, ref: dict[str, Any], context: _Context) -> int:
    """The artist name a song's credit points at: the one it had, or the artist's default."""
    if ref.get("nameId"):
        return int(ref["nameId"])
    artist_id = ref.get("publicId") or context.made[ref["ref"]]["artistId"]
    return _default_name(db, int(artist_id)).id


def _link_private_artists(db: DbSession, refs: list[dict[str, Any]], context: _Context) -> None:
    """The author's own artists named in the proposal now stand for the public ones."""
    for ref in refs:
        private_id = ref.get("privateId")
        if private_id is None:
            continue
        artist_id = ref.get("publicId") or context.made.get(ref.get("ref", ""), {}).get("artistId")
        own = db.get(Artist, private_id)
        if (
            artist_id is not None
            and own is not None
            and own.scope == "private"
            and own.owner_id == context.author
            and own.public_id is None
        ):
            own.public_id = int(artist_id)


def _write_song_fields(
    db: DbSession, song: Song, fields: dict[str, Any], context: _Context
) -> None:
    song.title = fields["title"]
    song.year = fields["year"]
    db.execute(delete(SongArtist).where(SongArtist.song_id == song.id))
    seen: set[int] = set()
    for position, ref in enumerate(fields["artists"]):
        name_id = _name_id(db, ref, context)
        if name_id not in seen:
            seen.add(name_id)
            db.add(SongArtist(song_id=song.id, artist_name_id=name_id, position=position))
    genres = dict(db.execute(select(Genre.name, Genre.id)).all())
    db.execute(delete(SongGenre).where(SongGenre.song_id == song.id))
    for name in fields["genres"]:
        db.add(SongGenre(song_id=song.id, genre_id=genres[name]))
    regions = dict(db.execute(select(Region.code, Region.id)).all())
    db.execute(delete(SongRegion).where(SongRegion.song_id == song.id))
    for code in fields["regions"]:
        db.add(SongRegion(song_id=song.id, region_id=regions[code]))
    categories = dict(db.execute(select(TagCategory.name, TagCategory.id)).all())
    db.execute(delete(SongTag).where(SongTag.song_id == song.id))
    for category, value in fields["tags"]:
        tag = db.scalar(
            select(TagValue).where(
                TagValue.category_id == categories[category], TagValue.value == value
            )
        )
        if tag is None:
            tag = TagValue(category_id=categories[category], value=value)
            db.add(tag)
            db.flush()
        db.add(SongTag(song_id=song.id, tag_value_id=tag.id))
    _link_private_artists(db, fields["artists"], context)
    db.flush()


def _accept(
    db: DbSession, item: RequestItem, payload: dict[str, Any], context: _Context
) -> dict[str, Any]:
    """Write what one accepted item proposes. Answers what it made."""
    if item.kind == "newArtist":
        artist = Artist(scope="public")
        db.add(artist)
        db.flush()
        db.add(ArtistName(artist_id=artist.id, name=payload["name"], is_default=True))
        db.flush()
        return {"artistId": artist.id}
    if item.kind == "newSong":
        song = Song(scope="public", title=payload["title"], popularity=0.0)
        db.add(song)
        db.flush()
        _write_song_fields(db, song, payload, context)
        return {"songId": song.id}
    if item.kind == "metadata" and payload["target"] == "song":
        song = public.public_song(db, payload["songId"])
        _write_song_fields(db, song, payload["after"], context)
        return {}
    if item.kind == "metadata":
        artist_id = payload["artistId"]
        public.public_artist(db, artist_id)
        if payload.get("name"):
            _default_name(db, artist_id).name = payload["name"]
        for name in payload.get("addNames", []):
            db.add(ArtistName(artist_id=artist_id, name=name, is_default=False))
        db.flush()
        return {}
    if item.kind == "project":
        song_ref = payload["song"]
        song_id = int(song_ref.get("publicId") or context.made[song_ref["ref"]]["songId"])
        project_id = context.copies[item.id]
        replaced = public.point_version(
            db,
            song_id=song_id,
            name=payload["versionName"],
            project_id=project_id,
            creator_id=context.author,
            user_version=True,
        )
        if replaced is not None:
            context.replaced.append(replaced)
        _link_private_song(db, payload, song_id, context)
        return {"projectId": project_id, "songId": song_id}
    if item.kind == "versionPointer":
        _check_user_version(db, payload, context.author)
        replaced = public.point_version(
            db,
            song_id=payload["songId"],
            name=payload["name"],
            project_id=payload["projectId"],
            creator_id=context.author,
            user_version=False,
        )
        if replaced is not None:
            context.replaced.append(replaced)
        return {}
    if item.kind == "playlist":
        moment = _now()
        playlist = Playlist(
            scope="public",
            owner_id=context.author,
            title=payload["title"],
            created_at=moment,
            updated_at=moment,
        )
        db.add(playlist)
        db.flush()
        position = 0
        for one in payload["items"]:
            if _song_of_public_project(db, one["projectId"]) is None:
                continue
            db.add(
                PlaylistItem(
                    playlist_id=playlist.id,
                    position=position,
                    song_id=one["songId"],
                    project_id=one["projectId"],
                    from_ms=one.get("fromMs"),
                    to_ms=one.get("toMs"),
                )
            )
            position += 1
        db.flush()
        return {"playlistId": playlist.id}
    raise ValueError(f"No item of kind {item.kind}")


def _link_private_song(
    db: DbSession, payload: dict[str, Any], song_id: int, context: _Context
) -> None:
    """The author's song the version came from now stands for the public song."""
    version = db.get(PrivateVersion, payload.get("sourceVersionId"))
    own = db.get(Song, version.song_id) if version is not None else None
    if own is None and payload["song"].get("privateId") is not None:
        own = db.get(Song, payload["song"]["privateId"])
    if (
        own is not None
        and own.scope == "private"
        and own.owner_id == context.author
        and own.public_id is None
    ):
        own.public_id = song_id


# --------------------------------------------------------------------- reads


@dataclass
class Summary:
    id: int
    kind: str
    status: str
    author: str
    #: The song, artist or playlist it is about.
    title: str
    #: A few words on what it asks: the version name, "new song", "changes"...
    subject: str
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None
    #: Items waiting for a decision, and in all.
    waiting: int
    items: int


@dataclass
class ProjectRef:
    project_id: str
    parts: list[str]
    #: Who made it ("anna"), and what it is ("easy").
    creator: str
    name: str
    #: The project is still kept (a request's copy, or a public version).
    kept: bool = True


@dataclass
class Compare:
    """The two sides of a project item: what the Public Library has now, and the proposal."""

    current: ProjectRef | None
    proposed: ProjectRef | None


@dataclass
class ItemView:
    id: int
    kind: str
    decision: str | None
    comment: str | None
    #: The payload with names: artists and songs as ``{"name"/"title", "publicId" or "ref",
    #: "isNew"}``; ``made`` once accepted.
    payload: dict[str, Any]
    compare: Compare | None = None


@dataclass
class Comment:
    author: str
    body: str
    created_at: datetime


@dataclass
class Detail:
    summary: Summary
    author_id: int
    items: list[ItemView]
    comments: list[Comment]
    #: The proposal as the author would send it again (for **Change and send again**).
    proposal: dict[str, Any]


def _names_of_refs(
    db: DbSession, refs: list[dict[str, Any]], by_ref: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    out = []
    for ref in refs:
        if "publicId" in ref:
            name = (
                db.scalar(select(ArtistName.name).where(ArtistName.id == ref["nameId"]))
                if ref.get("nameId")
                else None
            ) or _default_name(db, ref["publicId"]).name
            out.append({**ref, "name": name, "isNew": False})
        else:
            other = by_ref.get(ref.get("ref", ""), {})
            out.append({**ref, "name": other.get("name", ""), "isNew": True})
    return out


def _region_names(db: DbSession, codes: list[str]) -> list[str]:
    names = dict(db.execute(select(Region.code, Region.name)).all())
    return [names.get(code, code) for code in codes]


def _describe(
    db: DbSession, request: Request, items: list[RequestItem]
) -> tuple[str, str, dict[str, dict[str, Any]]]:
    payloads = [(item, _loads(item)) for item in items]
    by_ref = {payload["ref"]: payload for _, payload in payloads if "ref" in payload}
    title, subject = "", ""
    for item, payload in payloads:
        if item.kind == "project":
            song = payload.get("song", {})
            if "publicId" in song:
                found = db.get(Song, song["publicId"])
                title = found.title if found is not None else ""
            else:
                title = by_ref.get(song.get("ref", ""), {}).get("title", "")
            subject = payload.get("versionName", "")
        elif item.kind == "versionPointer":
            found = db.get(Song, payload["songId"])
            title = found.title if found is not None else ""
            subject = f"{payload.get('userVersionName', '')} as {payload['name']}"
        elif item.kind == "playlist":
            title, subject = payload["title"], f"{len(payload.get('items', []))} songs"
        elif item.kind == "metadata" and payload["target"] == "song":
            found = db.get(Song, payload["songId"])
            title, subject = (found.title if found is not None else ""), "changes"
        elif item.kind == "metadata":
            title, subject = payload["before"]["name"], "changes"
    if not title:
        for kind, label in (("newSong", "new song"), ("newArtist", "new artist")):
            first = next((p for item, p in payloads if item.kind == kind), None)
            if first is not None:
                title = first.get("title") or first.get("name", "")
                subject = label
                break
    return title, subject, by_ref


def _summary(db: DbSession, request: Request) -> Summary:
    items = _items(db, request.id)
    title, subject, _ = _describe(db, request, items)
    return Summary(
        id=request.id,
        kind=request.kind,
        status=request.status,
        author=_username(db, request.author_id),
        title=title,
        subject=subject,
        created_at=request.created_at,
        updated_at=request.updated_at,
        decided_at=request.decided_at,
        waiting=sum(1 for item in items if item.decision is None),
        items=len(items),
    )


def mine(author: int) -> list[Summary]:
    """The author's requests, the most recently changed first."""
    with session() as db:
        found = db.scalars(
            select(Request)
            .where(Request.author_id == author)
            .order_by(Request.updated_at.desc(), Request.id.desc())
        )
        return [_summary(db, one) for one in found]


def for_review(everything: bool = False) -> list[Summary]:
    """The open requests, oldest first (plan section 16.3); or every request, newest first."""
    with session() as db:
        query = select(Request)
        if everything:
            query = query.order_by(Request.updated_at.desc(), Request.id.desc())
        else:
            query = query.where(Request.status == "open").order_by(Request.created_at, Request.id)
        return [_summary(db, one) for one in db.scalars(query)]


def counts(user_id: int, is_master: bool) -> tuple[int, int]:
    """``(the user's requests with changes asked, the open requests to review)``."""
    with session() as db:
        mine_count = db.scalar(
            select(func.count()).where(
                Request.author_id == user_id, Request.status == "changesAsked"
            )
        )
        review = db.scalar(select(func.count()).where(Request.status == "open")) if is_master else 0
        return int(mine_count or 0), int(review or 0)


def _project_ref(
    db: DbSession, project_id: str | None, creator: str, name: str
) -> ProjectRef | None:
    if not project_id:
        return None
    try:
        locate.project(project_id)
        parts = bundle.part_ids_of(project_id)
    except locate.NotFound:
        return ProjectRef(project_id=project_id, parts=[], creator=creator, name=name, kept=False)
    return ProjectRef(project_id=project_id, parts=parts, creator=creator, name=name)


def _compare(
    db: DbSession, item: RequestItem, payload: dict[str, Any], author: int, author_name: str
) -> Compare | None:
    if item.kind == "project":
        song = payload.get("song", {})
        made = payload.get("made") or {}
        song_id = song.get("publicId") or made.get("songId")
        current = None
        if song_id is not None and not made:
            existing = db.scalar(
                select(UserVersion.project_id).where(
                    UserVersion.song_id == song_id,
                    UserVersion.user_id == author,
                    UserVersion.version_name == payload["versionName"],
                )
            )
            current = _project_ref(db, existing, author_name, payload["versionName"])
        proposed = _project_ref(db, payload.get("projectId"), author_name, payload["versionName"])
        return Compare(current=current, proposed=proposed)
    if item.kind == "versionPointer":
        current_row = db.scalar(
            select(SongVersion).where(
                SongVersion.song_id == payload["songId"], SongVersion.name == payload["name"]
            )
        )
        current = None
        if current_row is not None and current_row.project_id != payload["projectId"]:
            current = _project_ref(
                db,
                current_row.project_id,
                _username(db, current_row.creator_id),
                payload["name"],
            )
        proposed = _project_ref(
            db, payload["projectId"], author_name, payload.get("userVersionName", "")
        )
        return Compare(current=current, proposed=proposed)
    return None


def _view(
    db: DbSession, item: RequestItem, by_ref: dict[str, dict[str, Any]], author: int, name: str
) -> ItemView:
    payload = _loads(item)
    shown = dict(payload)
    if item.kind == "newSong":
        shown["artists"] = _names_of_refs(db, payload.get("artists", []), by_ref)
        shown["regionNames"] = _region_names(db, payload.get("regions", []))
    elif item.kind == "metadata" and payload["target"] == "song":
        shown["before"] = {
            **payload["before"],
            "artists": _names_of_refs(db, payload["before"]["artists"], by_ref),
            "regionNames": _region_names(db, payload["before"]["regions"]),
        }
        shown["after"] = {
            **payload["after"],
            "artists": _names_of_refs(db, payload["after"]["artists"], by_ref),
            "regionNames": _region_names(db, payload["after"]["regions"]),
        }
    elif item.kind == "project":
        song = payload.get("song", {})
        if "publicId" in song:
            found = db.get(Song, song["publicId"])
            shown["song"] = {**song, "title": found.title if found else "", "isNew": False}
        else:
            other = by_ref.get(song.get("ref", ""), {})
            shown["song"] = {**song, "title": other.get("title", ""), "isNew": True}
    elif item.kind == "versionPointer":
        found = db.get(Song, payload["songId"])
        shown["songTitle"] = found.title if found is not None else ""
    return ItemView(
        id=item.id,
        kind=item.kind,
        decision=item.decision,
        comment=item.comment,
        payload=shown,
        compare=_compare(db, item, payload, author, name),
    )


def _proposal_of(request: Request, items: list[RequestItem]) -> dict[str, Any]:
    """The proposal as the author would send it again: the items not accepted, with the accepted
    ones by the public rows they made."""
    payloads = [(item, _loads(item)) for item in items]
    by_ref = {p["ref"]: (item, p) for item, p in payloads if "ref" in p}

    def artist_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for ref in refs:
            extra = {"privateId": ref["privateId"]} if "privateId" in ref else {}
            if "publicId" in ref:
                out.append({"publicId": ref["publicId"], **extra})
                continue
            item, other = by_ref.get(ref.get("ref", ""), (None, {}))
            made = other.get("made") or {}
            if item is not None and item.decision == "accepted" and made.get("artistId"):
                out.append({"publicId": made["artistId"], **extra})
            else:
                out.append({"newName": other.get("name", ""), **extra})
        return out

    def song_fields(fields: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": fields.get("title", ""),
            "year": fields.get("year"),
            "artists": artist_refs(fields.get("artists", [])),
            "genres": fields.get("genres", []),
            "regions": fields.get("regions", []),
            "tags": [{"category": c, "value": v} for c, v in fields.get("tags", [])],
        }

    proposal: dict[str, Any] = {"kind": request.kind}
    for item, payload in payloads:
        if item.kind == "project":
            song = payload["song"]
            extra = {"privateId": song["privateId"]} if "privateId" in song else {}
            if "publicId" in song:
                choice: dict[str, Any] = {"publicId": song["publicId"], **extra}
            else:
                song_item, fields = by_ref.get(song.get("ref", ""), (None, {}))
                made = fields.get("made") or {}
                if song_item is not None and song_item.decision == "accepted":
                    choice = {"publicId": made.get("songId"), **extra}
                else:
                    choice = {"new": song_fields(fields), **extra}
            proposal.update(
                version=payload.get("sourceVersionId"),
                versionName=payload.get("versionName"),
                song=choice,
            )
        elif item.kind == "metadata" and payload["target"] == "song":
            proposal.update(
                song={"publicId": payload["songId"]}, changes=song_fields(payload["after"])
            )
        elif item.kind == "metadata":
            proposal.update(
                artist={
                    "publicId": payload["artistId"],
                    "name": payload.get("name"),
                    "addNames": payload.get("addNames", []),
                }
            )
        elif item.kind == "versionPointer":
            proposal.update(userVersion=payload["projectId"], name=payload["name"])
        elif item.kind == "playlist":
            proposal.update(playlist=payload.get("sourcePlaylistId"), title=payload["title"])
    if request.kind == "metadata" and "song" not in proposal and "artist" not in proposal:
        new_song = next((p for item, p in payloads if item.kind == "newSong"), None)
        if new_song is not None:
            proposal["song"] = {"new": song_fields(new_song)}
        else:
            new_artist = next((p for item, p in payloads if item.kind == "newArtist"), {})
            proposal["artist"] = {"name": new_artist.get("name", "")}
    return proposal


def detail(request_id: int) -> Detail:
    """A request with its items, comments, the two sides of each project, and its proposal."""
    with session() as db:
        request = _request(db, request_id)
        items = _items(db, request_id)
        _, _, by_ref = _describe(db, request, items)
        name = _username(db, request.author_id)
        return Detail(
            summary=_summary(db, request),
            author_id=request.author_id,
            items=[_view(db, item, by_ref, request.author_id, name) for item in items],
            comments=[
                Comment(
                    author=_username(db, one.author_id), body=one.body, created_at=one.created_at
                )
                for one in db.scalars(
                    select(RequestComment)
                    .where(RequestComment.request_id == request_id)
                    .order_by(RequestComment.created_at, RequestComment.id)
                )
            ],
            proposal=_proposal_of(request, items),
        )


def request_row(request_id: int) -> Request:
    """The request's row, for the rights check of the routes."""
    with session() as db:
        found = _request(db, request_id)
        db.expunge(found)
        return found


# ------------------------------------------------------------- publish dialog


@dataclass
class ArtistOfSong:
    private_id: int
    name: str
    #: The public artist the user's own one stands for, and its name.
    public_id: int | None
    public_name: str | None


@dataclass
class PublishInfo:
    version_id: int
    version_name: str
    #: The simple form of the version name (section 15.2).
    suggested_name: str
    ready: bool
    song_id: int
    song_title: str
    artists: list[ArtistOfSong]
    #: The public song the user's own song stands for, if any.
    public_song_id: int | None
    public_song_title: str | None
    #: The names of the user's own versions of that public song (a request of one replaces it).
    own_versions: list[str]
    #: A request of the user still waiting for this version.
    waiting_request: int | None


def publish_info(author: int, version_id: int) -> PublishInfo:
    """What the **Publish** dialog starts from, for a version of My library."""
    with session() as db:
        version = rows.version(db, author, version_id)
        song = rows.song(db, author, version.song_id)
        credits = rows.credits_of(db, [song.id])[song.id]
        artists = []
        for credit in credits:
            own = db.get(Artist, credit.artist_id)
            public_id = own.public_id if own is not None else None
            artists.append(
                ArtistOfSong(
                    private_id=credit.artist_id,
                    name=credit.name,
                    public_id=public_id,
                    public_name=_default_name(db, public_id).name if public_id else None,
                )
            )
        public_title = None
        own_versions: list[str] = []
        if song.public_id is not None:
            found = db.get(Song, song.public_id)
            public_title = found.title if found is not None else None
            own_versions = list(
                db.scalars(
                    select(UserVersion.version_name).where(
                        UserVersion.song_id == song.public_id, UserVersion.user_id == author
                    )
                )
            )
        waiting = None
        for request in db.scalars(
            select(Request).where(
                Request.author_id == author,
                Request.kind == "userVersion",
                Request.status.in_(WAITING),
            )
        ):
            if any(
                _loads(item).get("sourceVersionId") == version_id
                for item in _items(db, request.id)
                if item.kind == "project"
            ):
                waiting = request.id
        return PublishInfo(
            version_id=version.id,
            version_name=version.version_name,
            suggested_name=simple_name(version.version_name),
            ready=flow.sheet_ready(bundle.read_project(version.project_id)),
            song_id=song.id,
            song_title=song.title,
            artists=artists,
            public_song_id=song.public_id,
            public_song_title=public_title,
            own_versions=own_versions,
            waiting_request=waiting,
        )
