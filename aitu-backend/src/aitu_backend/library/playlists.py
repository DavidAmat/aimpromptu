"""Songs playlists of the Private Library (implementation 02, plan section 14.2, Phase 10).

A songs playlist is a row of ``playlists`` with its items in order (``playlist_items``). Each item
is a song of the owner's library, the version chosen for it (a project), and optionally a stretch of
it (``from_ms``, ``to_ms``, in ms of its first part). Nothing in a songs playlist is a copy: the item
points at the version, and nothing of the version can be changed from the playlist. An integrated
playlist is a project instead (:mod:`aitu_backend.editing.parts`).

A version that is deleted leaves its items on the song's first version (``project_id`` set to
``NULL`` by the table, read here as "the first"); a song that is deleted takes its items with it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import Playlist, PlaylistItem, PrivateVersion
from aitu_backend.library import rows

__all__ = [
    "ItemFacts",
    "NewItem",
    "PlaylistFacts",
    "add_items",
    "change_item",
    "create",
    "delete_playlist",
    "describe",
    "list_of",
    "playlist",
    "remove_item",
    "reorder",
    "rename",
]

TITLE_LIMIT = 300


@dataclass(frozen=True)
class NewItem:
    song_id: int
    #: The version chosen; the song's first when ``None``.
    project_id: str | None = None
    from_ms: int | None = None
    to_ms: int | None = None


@dataclass
class ItemFacts:
    id: int
    song_id: int
    song_title: str
    artists: list[str]
    #: The version on show: the chosen one, or the song's first.
    project_id: str | None
    version_name: str | None
    #: Every version of the song: ``(project_id, name)``.
    versions: list[tuple[str, str]]
    from_ms: int | None
    to_ms: int | None


@dataclass
class PlaylistFacts:
    id: int
    title: str
    updated_at: datetime
    items: list[ItemFacts] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def playlist(db: DbSession, owner: int, playlist_id: int) -> Playlist:
    row = db.get(Playlist, playlist_id)
    if row is None or row.scope != "private" or row.owner_id != owner:
        raise rows.NotFound(f"No playlist with id {playlist_id}")
    return row


def _items(db: DbSession, playlist_id: int) -> list[PlaylistItem]:
    return list(
        db.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position, PlaylistItem.id)
        )
    )


def _renumber(db: DbSession, items: list[PlaylistItem]) -> None:
    for position, item in enumerate(items):
        item.position = position


def _check_item(db: DbSession, owner: int, item: NewItem) -> None:
    rows.song(db, owner, item.song_id)
    if item.project_id is not None:
        found = rows.version_of_project(db, item.project_id)
        if found is None or found.song_id != item.song_id:
            raise rows.NotFound("That version is not a version of this song")
    if (item.from_ms is None) != (item.to_ms is None):
        raise ValueError("A stretch needs its start and its end")
    if item.from_ms is not None and item.to_ms is not None and item.to_ms <= item.from_ms:
        raise ValueError("A stretch must end after it starts")


def create(db: DbSession, owner: int, title: str, items: list[NewItem]) -> Playlist:
    row = Playlist(
        owner_id=owner,
        scope="private",
        title=rows.clean(title, "A playlist's title", TITLE_LIMIT),
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(row)
    db.flush()
    add_items(db, owner, row.id, items)
    return row


def add_items(db: DbSession, owner: int, playlist_id: int, items: list[NewItem]) -> None:
    row = playlist(db, owner, playlist_id)
    start = len(_items(db, playlist_id))
    for offset, item in enumerate(items):
        _check_item(db, owner, item)
        db.add(
            PlaylistItem(
                playlist_id=playlist_id,
                position=start + offset,
                song_id=item.song_id,
                project_id=item.project_id,
                from_ms=item.from_ms,
                to_ms=item.to_ms,
            )
        )
    row.updated_at = _now()
    db.flush()


def rename(db: DbSession, owner: int, playlist_id: int, title: str) -> None:
    row = playlist(db, owner, playlist_id)
    row.title = rows.clean(title, "A playlist's title", TITLE_LIMIT)
    row.updated_at = _now()


def reorder(db: DbSession, owner: int, playlist_id: int, order: list[int]) -> None:
    row = playlist(db, owner, playlist_id)
    items = {item.id: item for item in _items(db, playlist_id)}
    if sorted(order) != sorted(items):
        raise ValueError("Name every song of the playlist once")
    _renumber(db, [items[item_id] for item_id in order])
    row.updated_at = _now()


def _item(db: DbSession, playlist_id: int, item_id: int) -> PlaylistItem:
    item = db.get(PlaylistItem, item_id)
    if item is None or item.playlist_id != playlist_id:
        raise rows.NotFound(f"No song {item_id} in this playlist")
    return item


_KEEP = object()


def change_item(
    db: DbSession,
    owner: int,
    playlist_id: int,
    item_id: int,
    *,
    project_id: str | None | object = _KEEP,
    stretch: tuple[int, int] | None | object = _KEEP,
) -> None:
    """Another version for the song, or another stretch of it (``None``: the whole song)."""
    row = playlist(db, owner, playlist_id)
    item = _item(db, playlist_id, item_id)
    if item.song_id is None:
        raise rows.NotFound("This song is not in your library any more")
    wanted = NewItem(
        song_id=item.song_id,
        project_id=item.project_id if project_id is _KEEP else project_id,  # type: ignore[arg-type]
        from_ms=item.from_ms,
        to_ms=item.to_ms,
    )
    if stretch is not _KEEP:
        span = stretch if isinstance(stretch, tuple) else None
        wanted = NewItem(
            song_id=wanted.song_id,
            project_id=wanted.project_id,
            from_ms=None if span is None else span[0],
            to_ms=None if span is None else span[1],
        )
    _check_item(db, owner, wanted)
    item.project_id = wanted.project_id
    item.from_ms, item.to_ms = wanted.from_ms, wanted.to_ms
    row.updated_at = _now()


def remove_item(db: DbSession, owner: int, playlist_id: int, item_id: int) -> None:
    row = playlist(db, owner, playlist_id)
    db.delete(_item(db, playlist_id, item_id))
    db.flush()
    _renumber(db, _items(db, playlist_id))
    row.updated_at = _now()


def delete_playlist(db: DbSession, owner: int, playlist_id: int) -> None:
    playlist(db, owner, playlist_id)
    db.execute(delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id))
    db.execute(delete(Playlist).where(Playlist.id == playlist_id))


def list_of(db: DbSession, owner: int) -> list[tuple[Playlist, int]]:
    """The owner's playlists, each with how many songs it has, the newest change first."""
    found = list(
        db.scalars(select(Playlist).where(Playlist.scope == "private", Playlist.owner_id == owner))
    )
    out = []
    for row in found:
        out.append((row, sum(1 for item in _items(db, row.id) if item.song_id is not None)))
    out.sort(key=lambda pair: pair[0].updated_at, reverse=True)
    return out


def describe(db: DbSession, owner: int, playlist_id: int) -> PlaylistFacts:
    row = playlist(db, owner, playlist_id)
    items = _items(db, playlist_id)
    # A song deleted from the library leaves nothing to play: its items go.
    gone = [item for item in items if item.song_id is None]
    for item in gone:
        db.delete(item)
    if gone:
        db.flush()
        items = [item for item in items if item.song_id is not None]
        _renumber(db, items)
    song_ids = sorted({item.song_id for item in items if item.song_id is not None})
    credits = rows.credits_of(db, song_ids)
    versions = rows.versions_of(db, song_ids)
    titles = {song_id: rows.song(db, owner, song_id).title for song_id in song_ids}
    out = PlaylistFacts(id=row.id, title=row.title, updated_at=row.updated_at)
    for item in items:
        assert item.song_id is not None
        choices: list[PrivateVersion] = versions[item.song_id]
        chosen = next((one for one in choices if one.project_id == item.project_id), None)
        if chosen is None and choices:
            chosen = choices[0]
        out.items.append(
            ItemFacts(
                id=item.id,
                song_id=item.song_id,
                song_title=titles[item.song_id],
                artists=[credit.name for credit in credits[item.song_id]],
                project_id=chosen.project_id if chosen else None,
                version_name=chosen.version_name if chosen else None,
                versions=[(one.project_id, one.version_name) for one in choices],
                from_ms=item.from_ms,
                to_ms=item.to_ms,
            )
        )
    return out
