"""Every table of ``.database/aitu.sqlite`` (implementation 02, plan section 8.6).

The bundles on disk hold the music: notes, piano sheet, audio timeline. These tables hold who owns
what, where each project is, the music library in its two scopes, and the requests. Phase 3 makes
all of them, so the later phases fill tables instead of adding migrations.

Two additions to the list of section 8.6, both needed by what the section already says:

* ``parts``: the routes keyed by a uuid work on a part (P-6), so a part must find its project.
* ``song_genres``: a song has one or two genres, and that needs a link between the two tables.

The column names are snake_case here and camelCase on the wire. Times are UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator[datetime]):
    """A time stored in UTC and read back in UTC.

    SQLite keeps no zone: a time written as 14:58 UTC came back as a plain 14:58, which a browser
    then read as its own local time (two hours off in Barcelona). Every time column uses this type,
    so a time always leaves the database with its zone.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass


#: The three storage layers (plan section 8.2).
LAYERS = ("vault", "private", "public")
#: The two scopes of the music library (plan section 15.1).
SCOPES = ("private", "public")
ROLES = ("master", "user")
PROJECT_KINDS = ("song", "integratedPlaylist")
STEPS = ("source", "audio", "notes", "hands", "sheet")
REQUEST_KINDS = ("metadata", "userVersion", "fixedVersion")
REQUEST_STATUSES = (
    "open",
    "changesAsked",
    "accepted",
    "partlyAccepted",
    "refused",
    "withdrawn",
)
ITEM_DECISIONS = ("accepted", "refused", "changesAsked")


def _one_of(column: str, values: tuple[str, ...]) -> CheckConstraint:
    listed = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({listed})", name=f"{column}_allowed")


# ----------------------------------------------------------------------- users


class User(Base):
    __tablename__ = "users"
    __table_args__ = (_one_of("role", ROLES),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    #: Argon2, from Phase 4. Empty until a password is set.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class Session(Base):
    """A login (Phase 4). Only the hash of the token is stored."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


# -------------------------------------------------------------------- projects


class Project(Base):
    """Where a project bundle is and who owns it. The content is in the bundle (section 8.3)."""

    __tablename__ = "projects"
    __table_args__ = (
        _one_of("layer", LAYERS),
        _one_of("kind", PROJECT_KINDS),
        Index("ix_projects_owner_layer", "owner_id", "layer"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    layer: Mapped[str] = mapped_column(String(16), default="vault")
    kind: Mapped[str] = mapped_column(String(32), default="song")
    title: Mapped[str] = mapped_column(String(300), default="")
    #: The library project a vault project edits (section 10.6). Not a foreign key: the library
    #: project may be deleted while the copy is still open.
    based_on: Mapped[str | None] = mapped_column(String(36))
    #: The public project a private copy was pulled from (section 15.1).
    public_source_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    #: The lowest step reached by the parts (section 10.5), for the list of projects.
    step: Mapped[str | None] = mapped_column(String(16))


class Part(Base):
    """One ``.pmn`` of a project (section 8.4). Its id is the uuid of today's routes (P-6)."""

    __tablename__ = "parts"
    __table_args__ = (UniqueConstraint("project_id", "position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)


class AudioFile(Base):
    """One file of ``.database/audio/``, stored once and named by its content (P-3)."""

    __tablename__ = "audio_files"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    #: The file extension, which is also its container: ``mp3``, ``wav``, ``flac``.
    format: Mapped[str] = mapped_column(String(16))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AudioRef(Base):
    """A project uses an audio file: in a timeline of its parts, or in their history."""

    __tablename__ = "audio_refs"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    hash: Mapped[str] = mapped_column(ForeignKey("audio_files.hash"), primary_key=True, index=True)


# --------------------------------------------------------------- music library


class Artist(Base):
    __tablename__ = "artists"
    __table_args__ = (_one_of("scope", SCOPES),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))
    #: Empty for a public row.
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    #: A private row pulled from the Public Library keeps the public id (section 15.1).
    public_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id"))
    #: The id of the source the public row was imported from (Phase 12), so a new run of the
    #: import finds the same row.
    external_key: Mapped[str | None] = mapped_column(String(300), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class ArtistName(Base):
    """One name of an artist. "The Jackson 5" and "Jackson Five" are two rows of one artist."""

    __tablename__ = "artist_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class Album(Base):
    __tablename__ = "albums"
    __table_args__ = (_one_of("scope", SCOPES),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    public_id: Mapped[int | None] = mapped_column(ForeignKey("albums.id"))
    external_key: Mapped[str | None] = mapped_column(String(300), index=True)
    title: Mapped[str] = mapped_column(String(300))
    year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (_one_of("scope", SCOPES),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    public_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"))
    external_key: Mapped[str | None] = mapped_column(String(300), index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    #: The decade is computed from the year, not stored (section 8.6).
    year: Mapped[int | None] = mapped_column(Integer)
    #: 0 to 100, worldwide, all time (section 15.6). Other ranges are computed on request.
    popularity: Mapped[float | None] = mapped_column(Float)
    #: The fixed version Default points at: Hard unless the master user changes it.
    default_version: Mapped[str] = mapped_column(String(24), default="hard")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class SongArtist(Base):
    """A song points to an **artist name**, which points to its artist (app context)."""

    __tablename__ = "song_artists"

    song_id: Mapped[int] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    artist_name_id: Mapped[int] = mapped_column(
        ForeignKey("artist_names.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)


class SongAlbum(Base):
    __tablename__ = "song_albums"

    song_id: Mapped[int] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    album_id: Mapped[int] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    track_number: Mapped[int | None] = mapped_column(Integer)


# -------------------------------------------------------------------- versions


class SongVersion(Base):
    """A fixed version of a public song: Hard, Medium, Easy or an accepted custom name."""

    __tablename__ = "song_versions"
    __table_args__ = (UniqueConstraint("song_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(24))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    #: The user whose project this is, shown as the creator of the version (Phase 14).
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class UserVersion(Base):
    """``user_versions/<user>/<version name>/``: one project per song, user and name."""

    __tablename__ = "user_versions"
    __table_args__ = (UniqueConstraint("song_id", "user_id", "version_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    version_name: Mapped[str] = mapped_column(String(24))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class PrivateVersion(Base):
    """A version of a private song: free text, renamable, pointing to a Private Library project."""

    __tablename__ = "private_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    version_name: Mapped[str] = mapped_column(String(200))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


# ------------------------------------------------------- metadata of a public song


class Genre(Base):
    """The fixed list of section 15.3. A song has at most two."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class SongGenre(Base):
    __tablename__ = "song_genres"

    song_id: Mapped[int] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id"), primary_key=True)


class TagCategory(Base):
    """Fixed: films, video_games, tv_shows, adverts."""

    __tablename__ = "tag_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class TagValue(Base):
    """A value inside a category, such as "Shrek" in films. Added by request."""

    __tablename__ = "tag_values"
    __table_args__ = (UniqueConstraint("category_id", "value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("tag_categories.id"))
    value: Mapped[str] = mapped_column(String(200))


class SongTag(Base):
    __tablename__ = "song_tags"

    song_id: Mapped[int] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    tag_value_id: Mapped[int] = mapped_column(
        ForeignKey("tag_values.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Region(Base):
    """Where a song was popular: ``worldwide`` by default; more by request (Q-5)."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class SongRegion(Base):
    __tablename__ = "song_regions"

    song_id: Mapped[int] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), primary_key=True)


class ChartSource(Base):
    """One chart: its size ``N`` and its weight in the popularity (section 15.6)."""

    __tablename__ = "chart_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"))
    size: Mapped[int] = mapped_column(Integer, default=100)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class ChartEntry(Base):
    """A song at a rank of a chart in one week."""

    __tablename__ = "chart_entries"
    __table_args__ = (UniqueConstraint("song_id", "chart_source_id", "week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    chart_source_id: Mapped[int] = mapped_column(ForeignKey("chart_sources.id"))
    week: Mapped[date] = mapped_column(Date, index=True)
    rank: Mapped[int] = mapped_column(Integer)


# ------------------------------------------------------------------- playlists


class Playlist(Base):
    """A songs playlist (section 14.2). An integrated playlist is a project, not a row here."""

    __tablename__ = "playlists"
    __table_args__ = (_one_of("scope", SCOPES),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    scope: Mapped[str] = mapped_column(String(16))
    public_id: Mapped[int | None] = mapped_column(ForeignKey("playlists.id"))
    title: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id", ondelete="SET NULL"))
    #: The version chosen for the song.
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    #: An optional range of the song, in ms of its part.
    from_ms: Mapped[int | None] = mapped_column(Integer)
    to_ms: Mapped[int | None] = mapped_column(Integer)


# ---------------------------------------------------------------------- social


class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class LibraryShare(Base):
    """The owner shares their whole Private Library, read only (section 15.4)."""

    __tablename__ = "library_shares"

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    shared_with_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


# -------------------------------------------------------------------- requests


class Request(Base):
    """A request to publish into the Public Library (section 16)."""

    __tablename__ = "requests"
    __table_args__ = (_one_of("kind", REQUEST_KINDS), _one_of("status", REQUEST_STATUSES))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class RequestItem(Base):
    """One proposed change of a request, with its own decision: what makes partial acceptance."""

    __tablename__ = "request_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    #: ``newArtist``, ``newSong``, ``metadata``, ``project``, ``versionPointer``.
    kind: Mapped[str] = mapped_column(String(32))
    #: The proposed change, as JSON text.
    payload: Mapped[str] = mapped_column(Text, default="{}")
    decision: Mapped[str | None] = mapped_column(String(16))
    comment: Mapped[str | None] = mapped_column(Text)


class RequestComment(Base):
    __tablename__ = "request_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


#: The fixed lists written by the first migration (section 15.3).
GENRES = (
    "pop",
    "rock",
    "hip hop",
    "r&b and soul",
    "electronic and dance",
    "latin",
    "indie",
    "folk and singer-songwriter",
    "country",
    "jazz and blues",
    "classical",
    "soundtrack",
    "metal",
)
TAG_CATEGORIES = ("films", "video_games", "tv_shows", "adverts")
#: ``spain`` and ``catalan`` come with Q-5 (Phase 12).
REGIONS = (("worldwide", "Worldwide"),)
