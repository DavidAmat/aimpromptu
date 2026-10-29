"""The metadata of a song of My Library or of a project of My projects (implementation 04-3, Phase 1,
plan section 4.4).

A metadata row is a **primary key** (the fixed list of the Public Library, ``tag_categories``:
films, tv_shows, video_games, adverts) and a **secondary key** inside it, such as "The Lord of the
Rings". The secondary keys of a user are their own rows (``private_tag_values``): a value added to
the public ``tag_values`` would be shown to every user of the Public Library. A song links to them
through ``private_song_tags``, a project through ``project_tags``; an item can have several rows.

The metadata follows the work between the two pages:

* **Add to my library** gives the private song the public song's tags (:func:`copy_public_tags`);
  the public rows do not change.
* **Edit** gives the copy in My projects the song's metadata (:func:`copy_song_tags`), and **Save to
  library** (a new version or **Replace**) adds the project's metadata to the song's
  (:func:`add_project_tags_to_song`).
* **Duplicate** gives the copy the metadata of the original.

A secondary key that no song and no project uses any more is deleted, so the Filter and the
suggestions only offer values in use.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    TAG_CATEGORIES,
    PrivateSongTag,
    PrivateTagValue,
    ProjectTag,
    SongTag,
    TagCategory,
    TagValue,
)
from aitu_backend.library import rows

__all__ = [
    "MAX_TAGS",
    "Tag",
    "add_project_tags_to_song",
    "categories",
    "copy_project_tags",
    "copy_public_tags",
    "copy_song_tags",
    "public_tags_of",
    "set_project_tags",
    "set_song_tags",
    "suggestions",
    "tags_of_projects",
    "tags_of_songs",
]

VALUE_LIMIT = 200
#: The metadata rows one song or project may have.
MAX_TAGS = 30


@dataclass(frozen=True)
class Tag:
    #: The primary key: ``films``, ``tv_shows``, ``video_games`` or ``adverts``.
    category: str
    #: The secondary key.
    value: str


@dataclass(frozen=True)
class Suggestion:
    category: str
    value: str
    #: The user's own value (else a value of the Public Library).
    mine: bool


def _order(tag: Tag) -> tuple[int, str]:
    index = TAG_CATEGORIES.index(tag.category) if tag.category in TAG_CATEGORIES else 99
    return index, rows.same(tag.value)


def categories() -> list[str]:
    """The primary keys, in the order of the Public Library."""
    return list(TAG_CATEGORIES)


def _category_ids(db: DbSession) -> dict[str, int]:
    return {name: id_ for id_, name in db.execute(select(TagCategory.id, TagCategory.name))}


def _clean(db: DbSession, tags: list[Tag]) -> list[tuple[int, str]]:
    """``(category id, value)`` once each, the values cleaned; an unknown primary key is refused."""
    if len(tags) > MAX_TAGS:
        raise ValueError(f"A song has at most {MAX_TAGS} metadata rows")
    ids = _category_ids(db)
    out: dict[tuple[int, str], tuple[int, str]] = {}
    for tag in tags:
        if tag.category not in ids:
            raise ValueError(f"No primary key {tag.category!r}")
        value = rows.clean(tag.value, "A secondary key", VALUE_LIMIT)
        out.setdefault((ids[tag.category], rows.same(value)), (ids[tag.category], value))
    return list(out.values())


def _value_ids(db: DbSession, owner: int, tags: list[Tag]) -> list[int]:
    """The owner's secondary key rows for ``tags``, made when missing. "the lord of the rings" finds
    "The Lord of the Rings" (compared here: SQLite's ``lower`` folds only ASCII letters)."""
    wanted = _clean(db, tags)
    known = list(db.scalars(select(PrivateTagValue).where(PrivateTagValue.owner_id == owner)))
    out: list[int] = []
    for category_id, value in wanted:
        found = next(
            (
                row
                for row in known
                if row.category_id == category_id and rows.same(row.value) == rows.same(value)
            ),
            None,
        )
        if found is None:
            found = PrivateTagValue(owner_id=owner, category_id=category_id, value=value)
            db.add(found)
            db.flush()
            known.append(found)
        out.append(found.id)
    return out


def _forget_unused(db: DbSession, owner: int) -> None:
    used = select(ProjectTag.tag_value_id).union(select(PrivateSongTag.tag_value_id))
    db.execute(
        delete(PrivateTagValue).where(
            PrivateTagValue.owner_id == owner, PrivateTagValue.id.not_in(used)
        )
    )


def set_project_tags(db: DbSession, owner: int, project_id: str, tags: list[Tag]) -> list[Tag]:
    """The metadata of a project, all of it (an empty list: none). The caller checked the project
    is the owner's, in My projects."""
    ids = _value_ids(db, owner, tags)
    db.execute(delete(ProjectTag).where(ProjectTag.project_id == project_id))
    db.add_all(ProjectTag(project_id=project_id, tag_value_id=one) for one in ids)
    db.flush()
    _forget_unused(db, owner)
    return tags_of_projects(db, [project_id])[project_id]


def set_song_tags(db: DbSession, owner: int, song_id: int, tags: list[Tag]) -> list[Tag]:
    """The metadata of a song of My Library, all of it."""
    rows.song(db, owner, song_id)
    ids = _value_ids(db, owner, tags)
    db.execute(delete(PrivateSongTag).where(PrivateSongTag.song_id == song_id))
    db.add_all(PrivateSongTag(song_id=song_id, tag_value_id=one) for one in ids)
    db.flush()
    _forget_unused(db, owner)
    return tags_of_songs(db, [song_id])[song_id]


def tags_of_projects(db: DbSession, project_ids: list[str]) -> dict[str, list[Tag]]:
    """``project id -> its metadata``, for every id asked."""
    out: dict[str, list[Tag]] = {project_id: [] for project_id in project_ids}
    if project_ids:
        for project_id, category, value in db.execute(
            select(ProjectTag.project_id, TagCategory.name, PrivateTagValue.value)
            .join(PrivateTagValue, PrivateTagValue.id == ProjectTag.tag_value_id)
            .join(TagCategory, TagCategory.id == PrivateTagValue.category_id)
            .where(ProjectTag.project_id.in_(project_ids))
        ):
            out[project_id].append(Tag(category, value))
    return {key: sorted(found, key=_order) for key, found in out.items()}


def tags_of_songs(db: DbSession, song_ids: list[int]) -> dict[int, list[Tag]]:
    """``song id -> its metadata``, for every private song id asked."""
    out: dict[int, list[Tag]] = {song_id: [] for song_id in song_ids}
    if song_ids:
        for song_id, category, value in db.execute(
            select(PrivateSongTag.song_id, TagCategory.name, PrivateTagValue.value)
            .join(PrivateTagValue, PrivateTagValue.id == PrivateSongTag.tag_value_id)
            .join(TagCategory, TagCategory.id == PrivateTagValue.category_id)
            .where(PrivateSongTag.song_id.in_(song_ids))
        ):
            out[song_id].append(Tag(category, value))
    return {key: sorted(found, key=_order) for key, found in out.items()}


def public_tags_of(db: DbSession, public_song_id: int) -> list[Tag]:
    """The tags of a song of the Public Library."""
    found = [
        Tag(category, value)
        for category, value in db.execute(
            select(TagCategory.name, TagValue.value)
            .join(TagValue, TagValue.category_id == TagCategory.id)
            .join(SongTag, SongTag.tag_value_id == TagValue.id)
            .where(SongTag.song_id == public_song_id)
        )
    ]
    return sorted(found, key=_order)


def suggestions(db: DbSession, owner: int) -> list[Suggestion]:
    """What the secondary-key field offers: the owner's values, then the Public Library's values
    the owner does not have yet, by primary key and name."""
    used = select(ProjectTag.tag_value_id).union(select(PrivateSongTag.tag_value_id))
    # Only values in use: a song or a project deleted leaves its values behind until the next change.
    mine = [
        Suggestion(category, value, True)
        for category, value in db.execute(
            select(TagCategory.name, PrivateTagValue.value)
            .join(TagCategory, TagCategory.id == PrivateTagValue.category_id)
            .where(PrivateTagValue.owner_id == owner, PrivateTagValue.id.in_(used))
        )
    ]
    have = {(one.category, rows.same(one.value)) for one in mine}
    public = [
        Suggestion(category, value, False)
        for category, value in db.execute(
            select(TagCategory.name, TagValue.value).join(
                TagCategory, TagCategory.id == TagValue.category_id
            )
        )
        if (category, rows.same(value)) not in have
    ]
    return sorted(
        mine + public, key=lambda one: (_order(Tag(one.category, one.value)), not one.mine)
    )


def _add(
    db: DbSession, owner: int, song_id: int | None, project_id: str | None, tags: list[Tag]
) -> None:
    """``tags`` added to the item's metadata (the rows it has stay)."""
    for value_id in _value_ids(db, owner, tags):
        if song_id is not None:
            if db.get(PrivateSongTag, (song_id, value_id)) is None:
                db.add(PrivateSongTag(song_id=song_id, tag_value_id=value_id))
        elif project_id is not None:
            if db.get(ProjectTag, (project_id, value_id)) is None:
                db.add(ProjectTag(project_id=project_id, tag_value_id=value_id))
    db.flush()


def copy_public_tags(db: DbSession, owner: int, public_song_id: int, song_id: int) -> None:
    """**Add to my library**: the private song gets the public song's tags as its own metadata."""
    _add(db, owner, song_id, None, public_tags_of(db, public_song_id))


def copy_song_tags(db: DbSession, owner: int, song_id: int, project_id: str) -> None:
    """**Edit** (or **Duplicate** of a version): the copy in My projects gets the song's metadata."""
    _add(db, owner, None, project_id, tags_of_songs(db, [song_id])[song_id])


def copy_project_tags(db: DbSession, owner: int, source_id: str, project_id: str) -> None:
    """**Duplicate** of a project of My projects: the copy gets the original's metadata."""
    _add(db, owner, None, project_id, tags_of_projects(db, [source_id])[source_id])


def add_project_tags_to_song(db: DbSession, owner: int, project_id: str, song_id: int) -> None:
    """**Save to library**: the song keeps its metadata and gets the project's; the project's own
    rows go, because the project is now a version of the song (or, after **Replace**, deleted)."""
    _add(db, owner, song_id, None, tags_of_projects(db, [project_id])[project_id])
    db.execute(delete(ProjectTag).where(ProjectTag.project_id == project_id))
    db.flush()
