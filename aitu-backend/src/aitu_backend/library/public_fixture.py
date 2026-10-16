"""Place or remove a public version from the command line, for the browser checks of the Public
Library (implementation 02, Phase 13).

Public versions arrive by accepted requests, which Phase 14 builds. Until then, ``check:public``
needs a version to play, like and add to a library: it makes a copy of a project of its own
(``POST /projects/{id}/duplicate``), places a **copy** of that as a version of a public song with
this command, and removes it at the end. Nothing of a library is touched::

    python -m aitu_backend.library.public_fixture place --project <id> --song <public song id>
        --name hard [--user-version] [--creator <username>]
    python -m aitu_backend.library.public_fixture remove --project <public project id>
    python -m aitu_backend.library.public_fixture playlist --title <title> --item <song>[:<project>] ...
    python -m aitu_backend.library.public_fixture remove-playlist --id <public playlist id>
    python -m aitu_backend.library.public_fixture remove-song --id <public song id>
    python -m aitu_backend.library.public_fixture remove-artist --id <public artist id>
    python -m aitu_backend.library.public_fixture remove-user --username <name>

``place`` prints the id of the public project it made. It runs on the host, like ``make db-*``,
with ``AITU_DATABASE_DIR`` set.

``check:requests`` (Phase 14) makes a temporary user, its requests, and the public rows its
accepted requests make; ``remove-song``, ``remove-artist`` and ``remove-user`` delete them again:
a public song with its versions, a public artist with no song left, and a user with every project,
request, row and like of theirs (their public versions first). They refuse a row that is not
public, and ``remove-user`` refuses the master user.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    place = commands.add_parser("place")
    place.add_argument("--project", required=True)
    place.add_argument("--song", type=int, required=True)
    place.add_argument("--name", required=True)
    place.add_argument("--user-version", action="store_true")
    place.add_argument("--creator", default=None)
    remove = commands.add_parser("remove")
    remove.add_argument("--project", required=True)
    playlist = commands.add_parser("playlist")
    playlist.add_argument("--title", required=True)
    playlist.add_argument("--item", action="append", default=[])
    remove_playlist = commands.add_parser("remove-playlist")
    remove_playlist.add_argument("--id", type=int, required=True)
    remove_song = commands.add_parser("remove-song")
    remove_song.add_argument("--id", type=int, required=True)
    remove_artist = commands.add_parser("remove-artist")
    remove_artist.add_argument("--id", type=int, required=True)
    remove_user = commands.add_parser("remove-user")
    remove_user.add_argument("--username", required=True)
    args = parser.parse_args(argv)

    if args.command == "remove-song":
        _remove_song(args.id)
        return 0
    if args.command == "remove-artist":
        _remove_artist(args.id)
        return 0
    if args.command == "remove-user":
        _remove_user(args.username)
        return 0

    from aitu_backend.db import users  # noqa: PLC0415 - after the arguments
    from aitu_backend.db.database import session  # noqa: PLC0415
    from aitu_backend.db.models import Playlist, PlaylistItem  # noqa: PLC0415
    from aitu_backend.library import public  # noqa: PLC0415

    if args.command == "place":
        creator = users.find_by_username(args.creator) if args.creator else None
        creator_id = creator.id if creator is not None else users.ensure_master_user()
        print(
            public.place_version(
                args.project,
                song_id=args.song,
                name=args.name,
                creator_id=creator_id,
                user_version=args.user_version,
            )
        )
    elif args.command == "remove":
        public.remove_version(args.project)
    elif args.command == "playlist":
        with session() as db:
            made = Playlist(scope="public", title=args.title)
            db.add(made)
            db.flush()
            for position, item in enumerate(args.item):
                song, _, project = item.partition(":")
                db.add(
                    PlaylistItem(
                        playlist_id=made.id,
                        position=position,
                        song_id=int(song),
                        project_id=project or None,
                    )
                )
            print(made.id)
    else:
        with session() as db:
            found = db.get(Playlist, args.id)
            if found is not None and found.scope == "public":
                db.delete(found)
    return 0


def _remove_song(song_id: int) -> None:
    from sqlalchemy import select  # noqa: PLC0415

    from aitu_backend.db.database import session  # noqa: PLC0415
    from aitu_backend.db.models import Song, SongVersion, UserVersion  # noqa: PLC0415
    from aitu_backend.library import public  # noqa: PLC0415

    with session() as db:
        song = db.get(Song, song_id)
        if song is None or song.scope != "public":
            raise SystemExit(f"No public song {song_id}")
        projects = set(
            db.scalars(select(SongVersion.project_id).where(SongVersion.song_id == song_id))
        ) | set(db.scalars(select(UserVersion.project_id).where(UserVersion.song_id == song_id)))
    for project_id in projects:
        if project_id:
            public.remove_version(project_id)
    with session() as db:
        found = db.get(Song, song_id)
        if found is not None:
            db.delete(found)


def _remove_artist(artist_id: int) -> None:
    from aitu_backend.db.database import session  # noqa: PLC0415
    from aitu_backend.db.models import Artist  # noqa: PLC0415
    from aitu_backend.library import rows  # noqa: PLC0415

    with session() as db:
        artist = db.get(Artist, artist_id)
        if artist is None or artist.scope != "public":
            raise SystemExit(f"No public artist {artist_id}")
        if rows.song_ids_of_artist(db, artist_id):
            raise SystemExit(f"The public artist {artist_id} still has songs")
        db.delete(artist)


def _remove_user(username: str) -> None:
    from sqlalchemy import delete, select  # noqa: PLC0415

    from aitu_backend.db.database import session  # noqa: PLC0415
    from aitu_backend.db.models import (  # noqa: PLC0415
        Artist,
        Playlist,
        Project,
        Request,
        RequestComment,
        Song,
        SongVersion,
        User,
    )
    from aitu_backend.library import public  # noqa: PLC0415
    from aitu_backend.storage import bundle  # noqa: PLC0415

    with session() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            raise SystemExit(f"No user {username}")
        if user.role == "master":
            raise SystemExit("The master user is never removed")
        user_id = user.id
        projects = list(
            db.execute(select(Project.id, Project.layer).where(Project.owner_id == user_id))
        )
    for project_id, layer in projects:
        if layer == "public":
            public.remove_version(project_id)
        else:
            bundle.delete_project(project_id)
    with session() as db:
        db.execute(delete(RequestComment).where(RequestComment.author_id == user_id))
        db.execute(delete(Request).where(Request.author_id == user_id))
        db.execute(delete(Playlist).where(Playlist.owner_id == user_id))
        db.execute(delete(Song).where(Song.owner_id == user_id))
        db.execute(delete(Artist).where(Artist.owner_id == user_id))
        for fixed in db.scalars(select(SongVersion).where(SongVersion.creator_id == user_id)):
            fixed.creator_id = None
        found = db.get(User, user_id)
        if found is not None:
            db.delete(found)


if __name__ == "__main__":
    sys.exit(main())
