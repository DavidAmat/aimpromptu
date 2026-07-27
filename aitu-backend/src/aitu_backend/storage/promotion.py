"""Promoting a playground version into the performer-facing library.

```text
data/library/tracks/<artist_slug>/<track_slug>/
  metadata_library_track.json    tags, every promotion, the rollback pointer
  piano_matrix_v3_gsc.npz        a copy, not a reference
```

Three rules, all of them about not losing work:

**Promotions are named, never numbered.** A performer picks *"Levels (Chill) - Avicii"*, not
``v3_gn``. The name defaults to ``"<Track> - <Artist>"`` and is editable in the dialog.

**Promotion copies.** The library gets its own ``.npz`` and an embedded snapshot of the version's
``metadata.json``, so deleting the playground folder later cannot break a piece you play from.

**Nothing is ever deleted.** Re-promoting deactivates the previous entry; rollback reactivates it.
The history is append-only, and ``rollback`` only moves a pointer.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone

from aitu_backend.schemas.metadata import LibraryTrackMetadata, Promotion, VersionMetadata
from aitu_backend.schemas.naming import matrix_filename, parse_version_folder
from aitu_backend.storage import paths, repository


class LibraryTrackNotFound(KeyError):
    """No such track in the library."""

    def __init__(self, artist_slug: str, track_slug: str) -> None:
        super().__init__(f"No library track '{artist_slug}/{track_slug}'")


class PromotionNotFound(KeyError):
    """No promotion by that name."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No promotion named '{name}'")


class NothingToRollBackTo(RuntimeError):
    """Fewer than two promotions, so there is no previous state."""


@dataclass(frozen=True)
class PromotionResult:
    """What a promotion produced."""

    track: LibraryTrackMetadata
    promotion: Promotion

    @property
    def name(self) -> str:
        return self.promotion.promotion_name


def default_promotion_name(track_name: str, artist_name: str) -> str:
    """``"Levels - Avicii"`` — the suggestion the dialog pre-fills."""
    return f"{track_name.strip()} - {artist_name.strip()}"


# --------------------------------------------------------------------- tracks


def library_track_exists(artist_slug: str, track_slug: str) -> bool:
    return paths.library_track_metadata_path(artist_slug, track_slug).is_file()


def read_library_track(artist_slug: str, track_slug: str) -> LibraryTrackMetadata:
    path = paths.library_track_metadata_path(artist_slug, track_slug)
    if not path.is_file():
        raise LibraryTrackNotFound(artist_slug, track_slug)
    return LibraryTrackMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def write_library_track(metadata: LibraryTrackMetadata) -> None:
    path = paths.library_track_metadata_path(metadata.artist_slug, metadata.track_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        metadata.model_dump_json(by_alias=True, indent=2) + "\n",
        encoding="utf-8",
    )


def list_library_tracks(
    *, tag: str | None = None, search: str | None = None
) -> list[LibraryTrackMetadata]:
    """Library tracks, optionally filtered by tag and free-text name search."""
    tracks: list[LibraryTrackMetadata] = []
    for artist_slug in paths.list_library_artists():
        for track_slug in paths.list_library_tracks(artist_slug):
            try:
                tracks.append(read_library_track(artist_slug, track_slug))
            except (LibraryTrackNotFound, ValueError):
                continue

    if tag:
        needle = tag.strip().lower()
        tracks = [track for track in tracks if needle in {item.lower() for item in track.tags}]
    if search:
        needle = search.strip().lower()
        tracks = [
            track
            for track in tracks
            if needle in track.artist_name.lower() or needle in track.track_name.lower()
        ]

    tracks.sort(key=lambda track: (track.artist_name.lower(), track.track_name.lower()))
    return tracks


def set_tags(artist_slug: str, track_slug: str, tags: list[str]) -> LibraryTrackMetadata:
    """Replace a library track's tags."""
    track = read_library_track(artist_slug, track_slug)
    cleaned = sorted({tag.strip() for tag in tags if tag.strip()})
    updated = track.model_copy(update={"tags": cleaned, "updated_at": _now()})
    write_library_track(updated)
    return updated


# ------------------------------------------------------------------ promoting


def promote(
    artist_slug: str,
    track_slug: str,
    version_folder: str,
    *,
    promotion_name: str | None = None,
    as_additional: bool = False,
) -> PromotionResult:
    """Copy a playground version into the library.

    ``as_additional=False`` (the default, and the dialog's unchecked state)
    **replaces** the current promotion: the previous entry is deactivated but
    kept, so rollback can bring it straight back. ``as_additional=True`` keeps
    both live side by side — the same piece in two arrangements.
    """
    source = repository.load_version(artist_slug, track_slug, version_folder)
    playground = repository.read_track(artist_slug, track_slug)

    name = (promotion_name or "").strip() or default_promotion_name(
        playground.track_name, playground.artist_name
    )

    number, granularity = parse_version_folder(version_folder)
    filename = matrix_filename(number, granularity)
    destination = paths.library_track_dir(artist_slug, track_slug)
    destination.mkdir(parents=True, exist_ok=True)

    # Copy, never link: the library must survive the playground being cleaned out.
    shutil.copy2(
        paths.playground_version_dir(artist_slug, track_slug, number, granularity) / filename,
        destination / filename,
    )
    _copy_hand_matrices(artist_slug, track_slug, number, granularity, destination)

    track = _ensure_library_track(
        playground.artist_name, playground.track_name, artist_slug, track_slug
    )
    previous = track.active_promotions()

    promotion = Promotion(
        promotion_name=name,
        source_version_folder=version_folder,
        matrix_filename=filename,
        version_metadata=source.metadata,
    )

    promotions = list(track.promotions)
    if not as_additional:
        # Replace: deactivate what was live, but keep it so rollback can return.
        promotions = [
            entry.model_copy(update={"active": False}) if entry.active else entry
            for entry in promotions
        ]
    else:
        # Additional: only a same-named entry is superseded, so promoting the
        # same arrangement twice does not leave two live copies of it.
        promotions = [
            entry.model_copy(update={"active": False}) if entry.promotion_name == name else entry
            for entry in promotions
        ]
    promotions.append(promotion)

    # `find_promotion` searches newest-first, so appending is enough for a
    # re-promotion under an existing name to win.
    rollback_target = track.rollback_to
    if previous and not as_additional:
        rollback_target = previous[-1].promotion_name

    updated = track.model_copy(
        update={
            "promotions": promotions,
            "rollback_to": rollback_target,
            "updated_at": _now(),
        }
    )
    write_library_track(updated)
    return PromotionResult(track=updated, promotion=promotion)


def rollback(artist_slug: str, track_slug: str) -> PromotionResult:
    """Restore the previously promoted version.

    Moves the "current" pointer only: the rolled-back promotion is deactivated,
    not deleted, so rolling forward again is another promotion away.
    """
    track = read_library_track(artist_slug, track_slug)
    target_name = track.rollback_to
    if not target_name:
        raise NothingToRollBackTo(
            f"'{artist_slug}/{track_slug}' has no previous promotion to roll back to."
        )

    target = track.find_promotion(target_name)
    if target is None:
        raise PromotionNotFound(target_name)

    current = track.active_promotions()
    promotions = [
        entry.model_copy(update={"active": entry.promotion_name == target_name})
        for entry in track.promotions
    ]
    updated = track.model_copy(
        update={
            "promotions": promotions,
            "rollback_to": current[-1].promotion_name if current else None,
            "updated_at": _now(),
        }
    )
    write_library_track(updated)
    return PromotionResult(track=updated, promotion=target.model_copy(update={"active": True}))


def load_promoted(artist_slug: str, track_slug: str, promotion_name: str) -> VersionMetadata:
    """The embedded metadata of one promotion — self-contained by design."""
    track = read_library_track(artist_slug, track_slug)
    promotion = track.find_promotion(promotion_name)
    if promotion is None:
        raise PromotionNotFound(promotion_name)
    if promotion.version_metadata is None:
        raise PromotionNotFound(f"{promotion_name} (no embedded metadata)")
    return promotion.version_metadata


def promoted_matrix_path(artist_slug: str, track_slug: str, promotion_name: str):
    """Where a promotion's ``.npz`` lives inside the library."""
    track = read_library_track(artist_slug, track_slug)
    promotion = track.find_promotion(promotion_name)
    if promotion is None:
        raise PromotionNotFound(promotion_name)
    return paths.library_track_dir(artist_slug, track_slug) / promotion.matrix_filename


# ------------------------------------------------------------------ internals


def _ensure_library_track(
    artist_name: str, track_name: str, artist_slug: str, track_slug: str
) -> LibraryTrackMetadata:
    if library_track_exists(artist_slug, track_slug):
        return read_library_track(artist_slug, track_slug)
    metadata = LibraryTrackMetadata(
        artist_name=artist_name,
        track_name=track_name,
        artist_slug=artist_slug,
        track_slug=track_slug,
    )
    write_library_track(metadata)
    return metadata


def _copy_hand_matrices(
    artist_slug: str, track_slug: str, number: int, granularity, destination
) -> None:
    """Two-hands artifacts travel with their version when they exist."""
    source_dir = paths.playground_version_dir(artist_slug, track_slug, number, granularity)
    for hand in ("right", "left"):
        name = matrix_filename(number, granularity, hand)
        candidate = source_dir / name
        if candidate.is_file():
            shutil.copy2(candidate, destination / name)


def _now() -> datetime:
    return datetime.now(timezone.utc)
