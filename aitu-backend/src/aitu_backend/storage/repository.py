"""The playground repository: versioned piano matrices per track.

```text
data/playground/<artist_slug>/<track_slug>/
  metadata_track.json          names, slugs, dates, the version history
  v1_gsc/
    metadata.json              everything needed to re-render this state
    piano_matrix_v1_gsc.npz
  v1_gn/                       same version, collapsed differently
  v2_gn/
```

Two ideas shape it:

**A version is a musical state, a granularity is a view of it.** ``v1_gsc`` and ``v1_gn`` are the
same take collapsed two ways, so the version number does not advance when you only change
granularity. ``v2`` means you changed the music.

**Edits never touch the base matrix.** Saving an edited matrix records ``parentMatrix``; "back to
the original" means loading the parent, not undoing. The lineage is data, not history you can lose.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.schemas.metadata import (
    AudioReference,
    ParentMatrix,
    TrackMetadata,
    VersionHistoryEntry,
    VersionMetadata,
)
from aitu_backend.schemas.naming import (
    matrix_filename,
    next_version,
    parse_version_folder,
    slugify,
    version_folder,
)
from aitu_backend.storage import paths
from aitu_backend.storage.matrix_store import load_matrix, save_matrix


class TrackNotFound(KeyError):
    """No such track in the playground."""

    def __init__(self, artist_slug: str, track_slug: str) -> None:
        super().__init__(f"No playground track '{artist_slug}/{track_slug}'")


class VersionNotFound(KeyError):
    """The track exists but not that version folder."""

    def __init__(self, artist_slug: str, track_slug: str, folder: str) -> None:
        super().__init__(f"'{artist_slug}/{track_slug}' has no version '{folder}'")


@dataclass(frozen=True)
class LoadedVersion:
    """A saved version, read back."""

    matrix: PianoMatrix
    metadata: VersionMetadata
    artist_slug: str
    track_slug: str

    @property
    def folder(self) -> str:
        return self.metadata.folder


# --------------------------------------------------------------------- tracks


def track_exists(artist_slug: str, track_slug: str) -> bool:
    return paths.playground_track_metadata_path(artist_slug, track_slug).is_file()


def read_track(artist_slug: str, track_slug: str) -> TrackMetadata:
    path = paths.playground_track_metadata_path(artist_slug, track_slug)
    if not path.is_file():
        raise TrackNotFound(artist_slug, track_slug)
    return TrackMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def write_track(metadata: TrackMetadata) -> None:
    path = paths.playground_track_metadata_path(metadata.artist_slug, metadata.track_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        metadata.model_dump_json(by_alias=True, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_track(artist_name: str, track_name: str) -> TrackMetadata:
    """Find or create a track folder from human names."""
    artist_slug, track_slug = slugify(artist_name), slugify(track_name)
    if track_exists(artist_slug, track_slug):
        return read_track(artist_slug, track_slug)

    metadata = TrackMetadata(
        artist_name=artist_name.strip(),
        track_name=track_name.strip(),
        artist_slug=artist_slug,
        track_slug=track_slug,
    )
    write_track(metadata)
    return metadata


def list_tracks() -> list[TrackMetadata]:
    """Every playground track. Unreadable folders are skipped, not fatal."""
    tracks: list[TrackMetadata] = []
    for artist_slug in paths.list_playground_artists():
        for track_slug in paths.list_playground_tracks(artist_slug):
            try:
                tracks.append(read_track(artist_slug, track_slug))
            except (TrackNotFound, ValueError):
                continue
    tracks.sort(key=lambda track: (track.artist_name.lower(), track.track_name.lower()))
    return tracks


def find_tracks(query: str) -> list[TrackMetadata]:
    """Search by **real** artist/track name, not slug — what the user typed."""
    needle = query.strip().lower()
    if not needle:
        return list_tracks()
    return [
        track
        for track in list_tracks()
        if needle in track.artist_name.lower() or needle in track.track_name.lower()
    ]


def rename_track(
    artist_slug: str,
    track_slug: str,
    *,
    artist_name: str | None = None,
    track_name: str | None = None,
) -> TrackMetadata:
    """Change the display names. **Slugs and folders never move.**

    Renaming a folder would break every `parentMatrix` pointer and every library
    promotion that references it; the slug is an identity, the name is a label.
    """
    metadata = read_track(artist_slug, track_slug)
    updated = metadata.model_copy(
        update={
            "artist_name": (artist_name or metadata.artist_name).strip(),
            "track_name": (track_name or metadata.track_name).strip(),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    write_track(updated)
    return updated


# ------------------------------------------------------------------- versions


def list_versions(artist_slug: str, track_slug: str) -> list[VersionHistoryEntry]:
    """The recorded history, oldest first. The file is the source of truth."""
    return list(read_track(artist_slug, track_slug).versions)


def version_exists(artist_slug: str, track_slug: str, folder: str) -> bool:
    return (
        paths.playground_track_dir(artist_slug, track_slug) / folder / "metadata.json"
    ).is_file()


def save_version(
    artist_name: str,
    track_name: str,
    matrix: PianoMatrix,
    *,
    comment: str | None = None,
    overwrite: bool = False,
    version: int | None = None,
    parent: ParentMatrix | None = None,
    audio: AudioReference | None = None,
    key_signature: str | None = None,
) -> LoadedVersion:
    """Write a matrix as a ``vN_gX`` version folder.

    ``version`` pins the number explicitly — that is how the same musical state
    is saved at a second granularity (``v1_gsc`` then ``v1_gn``) without
    advancing to ``v2``. Left ``None``, the next unused number is chosen.

    ``overwrite`` rewrites an existing folder in place, replacing its history
    entry rather than appending a second one.
    """
    track = ensure_track(artist_name, track_name)
    number = version if version is not None else next_version(track.version_folders())
    folder = version_folder(number, matrix.granularity)

    existing = version_exists(track.artist_slug, track.track_slug, folder)
    if existing and not overwrite:
        raise FileExistsError(
            f"'{track.artist_slug}/{track.track_slug}' already has {folder}. "
            "Pass overwrite=True to replace it, or leave version unset for a new one."
        )

    metadata = VersionMetadata(
        version=number,
        tempo_bpm=matrix.tempo_bpm,
        granularity=matrix.granularity,
        matrix_processing_step=matrix.processing_step,
        time_step_seconds=matrix.time_step_seconds,
        parent_matrix=parent,
        audio=audio,
        key_signature=key_signature or matrix.key_signature,
        comment=comment,
    )

    directory = paths.playground_version_dir(
        track.artist_slug, track.track_slug, number, matrix.granularity
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "metadata.json").write_text(
        metadata.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8"
    )
    save_matrix(directory / matrix_filename(number, matrix.granularity), matrix.to_coo_payload())

    _record_history(track, metadata, folder, parent, replace=existing)

    return LoadedVersion(
        matrix=matrix,
        metadata=metadata,
        artist_slug=track.artist_slug,
        track_slug=track.track_slug,
    )


def save_two_hands(
    artist_name: str,
    track_name: str,
    right: PianoMatrix,
    left: PianoMatrix,
    **kwargs: object,
) -> LoadedVersion:
    """Save a two-hands state: one folder, one metadata, two ``.npz`` files."""
    if right.shape != left.shape:
        raise ValueError("Both hands must have the same shape to be saved together")

    saved = save_version(artist_name, track_name, right, **kwargs)  # type: ignore[arg-type]
    directory = paths.playground_version_dir(
        saved.artist_slug, saved.track_slug, saved.metadata.version, right.granularity
    )
    save_matrix(
        directory / matrix_filename(saved.metadata.version, right.granularity, "right"),
        right.to_coo_payload(),
    )
    save_matrix(
        directory / matrix_filename(saved.metadata.version, left.granularity, "left"),
        left.to_coo_payload(),
    )
    return saved


def load_version(artist_slug: str, track_slug: str, folder: str) -> LoadedVersion:
    """Read one saved version back into a :class:`PianoMatrix`."""
    if not track_exists(artist_slug, track_slug):
        raise TrackNotFound(artist_slug, track_slug)

    directory = paths.playground_track_dir(artist_slug, track_slug) / folder
    metadata_path = directory / "metadata.json"
    if not metadata_path.is_file():
        raise VersionNotFound(artist_slug, track_slug, folder)

    metadata = VersionMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    number, granularity = parse_version_folder(folder)
    payload = load_matrix(directory / matrix_filename(number, granularity))

    matrix = PianoMatrix.from_coo_payload(
        payload,
        granularity=metadata.granularity,
        tempo_bpm=metadata.tempo_bpm,
        processing_step=metadata.matrix_processing_step,
        key_signature=metadata.key_signature,
    )
    return LoadedVersion(
        matrix=matrix,
        metadata=metadata,
        artist_slug=artist_slug,
        track_slug=track_slug,
    )


def load_latest(artist_slug: str, track_slug: str) -> LoadedVersion:
    """The most recently saved version of a track."""
    latest = read_track(artist_slug, track_slug).latest()
    if latest is None:
        raise VersionNotFound(artist_slug, track_slug, "<none saved yet>")
    return load_version(artist_slug, track_slug, latest.folder)


def load_parent(version: LoadedVersion) -> LoadedVersion:
    """Load the matrix this one was derived from — "back to the original".

    Not an undo: the parent is a real saved state, and the edited version stays
    exactly where it is.
    """
    parent = version.metadata.parent_matrix
    if parent is None or parent.version_folder is None:
        raise VersionNotFound(version.artist_slug, version.track_slug, "<no parent recorded>")
    return load_version(version.artist_slug, version.track_slug, parent.version_folder)


def parent_pointer(version: LoadedVersion) -> ParentMatrix:
    """Build the ``parentMatrix`` to record when saving an edit of ``version``."""
    number, granularity = version.metadata.version, version.metadata.granularity
    return ParentMatrix(
        version_folder=version.folder,
        matrix_processing_step=version.metadata.matrix_processing_step,
        path=f"../{version.folder}/{matrix_filename(number, granularity)}",
    )


def delete_version(artist_slug: str, track_slug: str, folder: str) -> None:
    """Remove a version folder and drop it from the history."""
    import shutil

    directory = paths.playground_track_dir(artist_slug, track_slug) / folder
    if not directory.is_dir():
        raise VersionNotFound(artist_slug, track_slug, folder)
    shutil.rmtree(directory)

    track = read_track(artist_slug, track_slug)
    write_track(
        track.model_copy(
            update={
                "versions": [entry for entry in track.versions if entry.folder != folder],
                "updated_at": datetime.now(timezone.utc),
            }
        )
    )


# ------------------------------------------------------------------ internals


def _record_history(
    track: TrackMetadata,
    metadata: VersionMetadata,
    folder: str,
    parent: ParentMatrix | None,
    *,
    replace: bool,
) -> None:
    entry = VersionHistoryEntry(
        folder=folder,
        comment=metadata.comment,
        parent_version=parent.version_folder if parent else None,
        granularity=metadata.granularity,
        matrix_processing_step=metadata.matrix_processing_step,
    )
    versions = [item for item in track.versions if not (replace and item.folder == folder)]
    versions.append(entry)
    write_track(
        track.model_copy(update={"versions": versions, "updated_at": datetime.now(timezone.utc)})
    )


def step_of(matrix: PianoMatrix) -> MatrixProcessingStep:
    """Small helper so callers do not reach into the model for this."""
    return matrix.processing_step


def granularity_of(matrix: PianoMatrix) -> Granularity:
    return matrix.granularity
