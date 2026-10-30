"""The metadata of a song of My Library or of a project of My projects (implementation 04-3, Phase 1,
plan section 4.4).

A metadata row is a **primary key** (the fixed list of the Public Library, ``tag_categories``:
films, tv_shows, video_games, adverts) and a **secondary key** inside it, such as "The Lord of the
Rings". The secondary keys of a user are their own rows (``private_tag_values``): a value added to
the public ``tag_values`` would be shown to every user of the Public Library. A song links to them
through ``private_song_tags``, a project through ``project_tags``; an item can have several rows.

The metadata belongs to the **song**, never to one version of it (the user, 2026-10-29): every
version of a song shows the same rows, and a change made from any of them changes them all. A
project of My projects with no song is its own song. An **edit copy** (a project of My projects
that edits a version, ``projects.based_on``) has no rows of its own: it reads and changes its
song's (:func:`edited_songs`).

The metadata follows the work between the two pages:

* **Add to my library** gives the private song the public song's tags (:func:`copy_public_tags`);
  the public rows do not change.
* **Save to library** adds the project's metadata to the song's (:func:`add_project_tags_to_song`);
  an edit copy saved into another song gives that song its own song's metadata
  (:func:`add_song_tags_to_song`).
* **Duplicate** gives the copy the metadata of the original as its own; the duplicate of an edit
  copy edits the same version, so it shares the song's.
* A deleted version leaves its edit copy an ordinary project, which keeps the song's metadata as
  its own (:func:`copy_song_tags`).
* A **level copy** (implementation 04-3, Phase 4: a level of the whole sheet written into a new
  project, ``projects.level_of``) has no rows of its own either: it shares the metadata of the
  project it was written from (:func:`homes`), that is its song's, or that project's own rows
  when it has no song. A deleted original leaves its level copies with its metadata as their own
  (:func:`release_levels`).

A secondary key that no song and no project uses any more is deleted, so the Filter and the
suggestions only offer values in use.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session as DbSession

from aitu_backend.db.models import (
    TAG_CATEGORIES,
    PrivateVersion,
    Project,
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
    "add_song_tags_to_song",
    "categories",
    "copy_project_tags",
    "copy_public_tags",
    "copy_song_tags",
    "edited_songs",
    "homes",
    "release_levels",
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


def homes(db: DbSession, project_ids: list[str]) -> dict[str, str]:
    """``project id -> the project whose metadata it shares``: a level copy's original
    (``level_of``), else itself."""
    if not project_ids:
        return {}
    found = dict(
        db.execute(
            select(Project.id, Project.level_of).where(
                Project.id.in_(project_ids), Project.level_of.is_not(None)
            )
        ).all()
    )
    return {project_id: found.get(project_id) or project_id for project_id in project_ids}


def edited_songs(db: DbSession, project_ids: list[str]) -> dict[str, int]:
    """``project id -> its song``, for the edit copies among the ids (the song of the version it
    edits; a copy whose version was deleted is an ordinary project) and the level copies whose
    original has a song (an edit copy, or a version of My Library)."""
    if not project_ids:
        return {}
    home = homes(db, project_ids)
    targets = sorted(set(home.values()))
    songs = {
        project_id: int(song_id)
        for project_id, song_id in db.execute(
            select(Project.id, PrivateVersion.song_id)
            .join(PrivateVersion, PrivateVersion.project_id == Project.based_on)
            .where(Project.id.in_(targets), Project.layer == "vault")
        )
    }
    originals = sorted({h for p, h in home.items() if h != p})
    if originals:
        songs.update(
            (project_id, int(song_id))
            for project_id, song_id in db.execute(
                select(PrivateVersion.project_id, PrivateVersion.song_id).where(
                    PrivateVersion.project_id.in_(originals)
                )
            )
        )
    return {project_id: songs[h] for project_id, h in home.items() if h in songs}


def release_levels(db: DbSession, owner: int, original_id: str) -> list[str]:
    """The original of level copies is deleted: each copy keeps the metadata it shared as its own,
    and stops pointing at it (as an edit copy whose version is deleted). Returns the copies (the
    caller writes their ``project.json``)."""
    copies = list(db.scalars(select(Project.id).where(Project.level_of == original_id)))
    if not copies:
        return []
    shared = tags_of_projects(db, [copies[0]])[copies[0]]
    db.execute(update(Project).where(Project.id.in_(copies)).values(level_of=None))
    db.flush()
    for copy_id in copies:
        _add(db, owner, None, copy_id, shared)
    return copies


def set_project_tags(db: DbSession, owner: int, project_id: str, tags: list[Tag]) -> list[Tag]:
    """The metadata of a project, all of it (an empty list: none); an edit copy's goes to its song.
    The caller checked the project is the owner's, in My projects."""
    song_id = edited_songs(db, [project_id]).get(project_id)
    if song_id is not None:
        return set_song_tags(db, owner, song_id, tags)
    # A level copy of a project with no song changes that project's rows.
    home = homes(db, [project_id])[project_id]
    ids = _value_ids(db, owner, tags)
    db.execute(delete(ProjectTag).where(ProjectTag.project_id == home))
    db.add_all(ProjectTag(project_id=home, tag_value_id=one) for one in ids)
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
    """``project id -> its metadata``, for every id asked: an edit copy's is its song's, a level
    copy's its original's."""
    home = homes(db, project_ids)
    own = _own_tags_of_projects(db, sorted(set(home.values())))
    out = {project_id: own[home[project_id]] for project_id in project_ids}
    edited = edited_songs(db, project_ids)
    songs = tags_of_songs(db, sorted(set(edited.values())))
    for project_id, song_id in edited.items():
        out[project_id] = songs[song_id]
    return out


def _own_tags_of_projects(db: DbSession, project_ids: list[str]) -> dict[str, list[Tag]]:
    """The rows of ``project_tags`` themselves (an edit copy has none since revision 0009)."""
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
    """**Duplicate** of a version, or an edit copy whose version is deleted: the project in My
    projects gets the song's metadata as its own."""
    _add(db, owner, None, project_id, tags_of_songs(db, [song_id])[song_id])


def copy_project_tags(db: DbSession, owner: int, source_id: str, project_id: str) -> None:
    """**Duplicate** of a project of My projects: the copy gets the original's metadata as its own.
    The duplicate of an edit copy edits the same version, so it has its song's and nothing more;
    the duplicate of a level copy shares its original's."""
    if project_id in edited_songs(db, [project_id]) or homes(db, [project_id])[project_id] != project_id:
        return
    _add(db, owner, None, project_id, tags_of_projects(db, [source_id])[source_id])


def add_song_tags_to_song(db: DbSession, owner: int, source_id: int, song_id: int) -> None:
    """**Save to library** of an edit copy into another song: that song gets the edited song's
    metadata too."""
    if source_id != song_id:
        _add(db, owner, song_id, None, tags_of_songs(db, [source_id])[source_id])


def add_project_tags_to_song(db: DbSession, owner: int, project_id: str, song_id: int) -> None:
    """**Save to library**: the song keeps its metadata and gets the project's own rows, which go,
    because the project is now a version of the song (or, after **Replace**, deleted)."""
    _add(db, owner, song_id, None, _own_tags_of_projects(db, [project_id])[project_id])
    db.execute(delete(ProjectTag).where(ProjectTag.project_id == project_id))
    db.flush()
