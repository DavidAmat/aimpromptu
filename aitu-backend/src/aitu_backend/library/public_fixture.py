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

``place`` prints the id of the public project it made. It runs on the host, like ``make db-*``,
with ``AITU_DATABASE_DIR`` set.
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
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
