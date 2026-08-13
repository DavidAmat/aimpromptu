"""Performer playlists: an ordered list of named promotions.

```text
data/library/playlists/<slug>/
  metadata_library_playlist.json
```

A playlist is names, not folders. Each entry pins a promotion by the name a
performer would pick, so re-promoting under the same name keeps the playlist
pointing at the live arrangement. The slug is identity; renaming never moves
the folder.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone

from aitu_backend.schemas.metadata import PlaylistItem, PlaylistMetadata
from aitu_backend.schemas.naming import slugify
from aitu_backend.storage import paths, promotion
from aitu_backend.storage.promotion import LibraryTrackNotFound, PromotionNotFound


class PlaylistNotFound(KeyError):
    """No such playlist."""

    def __init__(self, slug: str) -> None:
        super().__init__(f"No playlist '{slug}'")


def list_playlists() -> list[PlaylistMetadata]:
    """Every playlist, oldest name first."""
    found: list[PlaylistMetadata] = []
    for slug in paths.list_playlists():
        try:
            found.append(read_playlist(slug))
        except (PlaylistNotFound, ValueError):
            continue
    found.sort(key=lambda item: item.name.lower())
    return found


def read_playlist(slug: str) -> PlaylistMetadata:
    path = paths.playlist_metadata_path(slug)
    if not path.is_file():
        raise PlaylistNotFound(slug)
    return PlaylistMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def write_playlist(metadata: PlaylistMetadata) -> None:
    path = paths.playlist_metadata_path(metadata.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        metadata.model_dump_json(by_alias=True, indent=2) + "\n",
        encoding="utf-8",
    )


def create_playlist(
    name: str,
    *,
    description: str | None = None,
    items: list[PlaylistItem] | None = None,
) -> PlaylistMetadata:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("A playlist needs a name.")
    try:
        slug = _unique_slug(slugify(cleaned))
    except ValueError as exc:
        raise ValueError("A playlist needs a name with letters or numbers.") from exc
    validate_items(items or [])
    metadata = PlaylistMetadata(
        name=cleaned,
        slug=slug,
        description=(description or "").strip() or None,
        items=list(items or []),
    )
    write_playlist(metadata)
    return metadata


def update_playlist(
    slug: str,
    *,
    name: str | None = None,
    description: str | None = None,
    items: list[PlaylistItem] | None = None,
) -> PlaylistMetadata:
    current = read_playlist(slug)
    if items is not None:
        validate_items(items)
    updated = current.model_copy(
        update={
            "name": name.strip() if name is not None else current.name,
            "description": (
                description.strip() or None if description is not None else current.description
            ),
            "items": list(items) if items is not None else current.items,
            "updated_at": _now(),
        }
    )
    if not updated.name.strip():
        raise ValueError("A playlist needs a name.")
    write_playlist(updated)
    return updated


def delete_playlist(slug: str) -> None:
    path = paths.playlist_metadata_path(slug)
    if not path.is_file():
        raise PlaylistNotFound(slug)
    shutil.rmtree(path.parent)


def validate_items(items: list[PlaylistItem]) -> None:
    """Every entry must name a promotion that is actually in the library."""
    for item in items:
        try:
            track = promotion.read_library_track(item.artist_slug, item.track_slug)
        except LibraryTrackNotFound as exc:
            raise LibraryTrackNotFound(item.artist_slug, item.track_slug) from exc
        if track.find_promotion(item.promotion_name) is None:
            raise PromotionNotFound(item.promotion_name)


def _unique_slug(base: str) -> str:
    slug = base
    n = 2
    while paths.playlist_metadata_path(slug).is_file():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _now() -> datetime:
    return datetime.now(timezone.utc)
