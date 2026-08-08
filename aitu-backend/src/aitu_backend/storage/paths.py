"""Every filesystem path the backend uses, built in one place.

Tree under ``aitu-backend/data/``::

    data/
      audio/<uuid>/
        metadata.json
        original.<ext>
      playground/<artist_slug>/<track_slug>/
        metadata_track.json
        v1_f40/
          metadata.json
          piano_matrix_v1_f40.npz
      library/
        tracks/<artist_slug>/<track_slug>/
          metadata_library_track.json
          piano_matrix_<...>.npz
        playlists/<playlist_slug>/
          metadata_library_playlist.json

No path literal lives outside this module. If storage is ever containerized the
tree maps 1:1 onto a MinIO bucket; not now.
"""

from __future__ import annotations

from pathlib import Path

from aitu_backend.schemas.naming import matrix_filename, version_folder

# --------------------------------------------------------------------- roots


def backend_root() -> Path:
    """`aitu-backend/` — the folder holding `pyproject.toml`, `src/` and `data/`."""
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    """`aitu-backend/data/` — root of all local persistence."""
    return backend_root() / "data"


def audio_root() -> Path:
    """`data/audio/` — one uuid folder per ingested audio."""
    return data_dir() / "audio"


def playground_root() -> Path:
    """`data/playground/` — work in progress, versioned per track."""
    return data_dir() / "playground"


def library_root() -> Path:
    """`data/library/` — the performer-facing library."""
    return data_dir() / "library"


def library_tracks_root() -> Path:
    return library_root() / "tracks"


def library_playlists_root() -> Path:
    return library_root() / "playlists"


#: Created on app startup by :func:`ensure_data_tree`.
TREE_ROOTS = (
    audio_root,
    playground_root,
    library_tracks_root,
    library_playlists_root,
)


def ensure_data_tree() -> None:
    """Create the whole storage tree if missing. Called on app startup."""
    for root in TREE_ROOTS:
        root().mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------- audio


def audio_dir(audio_uuid: str) -> Path:
    """`data/audio/<uuid>/`."""
    return audio_root() / audio_uuid


def audio_metadata_path(audio_uuid: str) -> Path:
    """`data/audio/<uuid>/metadata.json`."""
    return audio_dir(audio_uuid) / "metadata.json"


def audio_original_path(audio_uuid: str, extension: str) -> Path:
    """`data/audio/<uuid>/original.<ext>`; the extension may include the dot."""
    return audio_dir(audio_uuid) / f"original.{extension.lstrip('.')}"


def find_audio_original(audio_uuid: str) -> Path | None:
    """The stored `original.*` file, whatever its extension. `None` if absent."""
    matches = sorted(audio_dir(audio_uuid).glob("original.*"))
    return matches[0] if matches else None


def list_audio_uuids() -> list[str]:
    """Every uuid folder in the audio store, sorted."""
    return _child_names(audio_root())


# ---------------------------------------------------------------- playground


def playground_artist_dir(artist_slug: str) -> Path:
    return playground_root() / artist_slug


def playground_track_dir(artist_slug: str, track_slug: str) -> Path:
    """`data/playground/<artist>/<track>/`."""
    return playground_artist_dir(artist_slug) / track_slug


def playground_track_metadata_path(artist_slug: str, track_slug: str) -> Path:
    """`.../metadata_track.json`."""
    return playground_track_dir(artist_slug, track_slug) / "metadata_track.json"


def playground_version_dir(
    artist_slug: str,
    track_slug: str,
    version: int,
    frame_ms: float,
) -> Path:
    """`data/playground/<artist>/<track>/v2_f40/`."""
    return playground_track_dir(artist_slug, track_slug) / version_folder(version, frame_ms)


def playground_version_metadata_path(
    artist_slug: str,
    track_slug: str,
    version: int,
    frame_ms: float,
) -> Path:
    """`.../v2_f40/metadata.json`."""
    return playground_version_dir(artist_slug, track_slug, version, frame_ms) / "metadata.json"


def playground_matrix_path(
    artist_slug: str,
    track_slug: str,
    version: int,
    frame_ms: float,
    hand: str | None = None,
) -> Path:
    """`.../v2_f40/piano_matrix_v2_f40.npz`, or the per-hand variant."""
    return playground_version_dir(artist_slug, track_slug, version, frame_ms) / matrix_filename(
        version, frame_ms, hand
    )


def list_playground_artists() -> list[str]:
    return _child_names(playground_root())


def list_playground_tracks(artist_slug: str) -> list[str]:
    return _child_names(playground_artist_dir(artist_slug))


def list_playground_versions(artist_slug: str, track_slug: str) -> list[str]:
    """Version folder names present on disk, sorted by name."""
    return _child_names(playground_track_dir(artist_slug, track_slug))


# ------------------------------------------------------------------- library


def library_track_dir(artist_slug: str, track_slug: str) -> Path:
    """`data/library/tracks/<artist>/<track>/`."""
    return library_tracks_root() / artist_slug / track_slug


def library_track_metadata_path(artist_slug: str, track_slug: str) -> Path:
    """`.../metadata_library_track.json`."""
    return library_track_dir(artist_slug, track_slug) / "metadata_library_track.json"


def library_matrix_path(
    artist_slug: str,
    track_slug: str,
    version: int,
    frame_ms: float,
    hand: str | None = None,
) -> Path:
    """A promoted matrix inside the library track folder."""
    return library_track_dir(artist_slug, track_slug) / matrix_filename(version, frame_ms, hand)


def playlist_dir(playlist_slug: str) -> Path:
    """`data/library/playlists/<slug>/`."""
    return library_playlists_root() / playlist_slug


def playlist_metadata_path(playlist_slug: str) -> Path:
    """`.../metadata_library_playlist.json`."""
    return playlist_dir(playlist_slug) / "metadata_library_playlist.json"


def list_library_artists() -> list[str]:
    return _child_names(library_tracks_root())


def list_library_tracks(artist_slug: str) -> list[str]:
    return _child_names(library_tracks_root() / artist_slug)


def list_playlists() -> list[str]:
    return _child_names(library_playlists_root())


# --------------------------------------------------------------------- seeds


def scores_json_path() -> Path:
    """Seed example scores served by `GET /scores`."""
    return data_dir() / "example-scores.json"


# ------------------------------------------------------------------ internal


def _child_names(directory: Path) -> list[str]:
    """Sorted names of the subdirectories of ``directory``; empty if absent."""
    if not directory.is_dir():
        return []
    return sorted(child.name for child in directory.iterdir() if child.is_dir())
