"""Every filesystem path the backend uses, built in one place.

Tree under ``aitu-backend/data/``::

    data/
      audio/<uuid>/
        metadata.json
        original.<ext>
        video/                      only when the piece came from a video
          source.mp4                the download (V-01); the audio came out of it
          metadata_video.json       size, duration, frames per second, sampleMs
          calibration.json          the piano overlay and everything measured from it
          plate.npy                 the background plate, derived
          frames/f000001.jpg        the sampled frames, derived
          frames.jsonl              onsets and sustains per sampled frame, derived
          detection-report.json     what the last whole-video run did, in numbers
          notes.json                the notes the stitched roll read (V-32), derived
          corrections.json          what a person changed before the piece was written
          detection/                debug pictures, only when asked for
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
      frame-examples/
        <slug>.json                 one example's calibration and annotations
        cache/<slug>.jpg            the working-resolution copy, derived

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


# ------------------------------------------------------- the example frames
#
# The Synthesia example screenshots are part of the plan that asked for them and
# stay where the user put them, under `context/implementations/`. Only what we
# derive from them is data: one calibration and one set of manual annotations per
# example, plus the working-resolution copy the browser is served.


def repo_root() -> Path:
    """The repository root — the folder holding `aitu-backend/` and `context/`."""
    return backend_root().parent


def frame_examples_source_dir() -> Path:
    """The example screenshots, read only, where the plan keeps them."""
    return repo_root() / "context" / "implementations" / "04-synthesia-to-notes" / "examples"


def frame_examples_root() -> Path:
    """`data/frame-examples/` — one record per example screenshot."""
    return data_dir() / "frame-examples"


def frame_example_path(slug: str) -> Path:
    """`data/frame-examples/<slug>.json` — its calibration and its annotations."""
    return frame_examples_root() / f"{slug}.json"


def frame_example_image_path(slug: str) -> Path:
    """`data/frame-examples/cache/<slug>.jpg` — the working-resolution copy.

    Derived and disposable: the screenshots are 3600 px wide and the detector
    works at 1280, so the browser is served the same picture the detector reads
    and a calibration means the same thing on both sides.
    """
    return frame_examples_root() / "cache" / f"{slug}.jpg"


def list_frame_example_slugs() -> list[str]:
    """Every example screenshot on disk, sorted."""
    source = frame_examples_source_dir()
    if not source.is_dir():
        return []
    return sorted(p.stem for p in source.glob("*.png"))


#: Created on app startup by :func:`ensure_data_tree`.
TREE_ROOTS = (
    audio_root,
    playground_root,
    library_tracks_root,
    library_playlists_root,
    frame_examples_root,
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


# --------------------------------------------------------------------- video
#
# A video lives inside the audio folder of the piece it belongs to (V-03). One
# YouTube URL gives one piece: the video, and the audio of that same video beside
# it. There is no second kind of piece and no second library.
#
# The video file is the source and the sampled frames are a cache (V-01), so
# everything under `frames/` can be thrown away and written again at any sampling
# granularity. Only `calibration.json` cannot: it is the user's work.


def video_dir(audio_uuid: str) -> Path:
    """`data/audio/<uuid>/video/` — everything about the picture of this piece."""
    return audio_dir(audio_uuid) / "video"


def video_source_path(audio_uuid: str) -> Path:
    """`video/source.mp4` — the download. The audio was extracted from this file."""
    return video_dir(audio_uuid) / "source.mp4"


def video_metadata_path(audio_uuid: str) -> Path:
    """`video/metadata_video.json` — size, duration, frames per second, `sampleMs`."""
    return video_dir(audio_uuid) / "metadata_video.json"


def video_calibration_path(audio_uuid: str) -> Path:
    """`video/calibration.json` — the piano overlay and everything measured from it.

    Kept beside the video and never merged into `rhythm.json` (V-12): how the
    notes were read off the screen is a different thing from what a reader
    decided about the sheet.
    """
    return video_dir(audio_uuid) / "calibration.json"


def video_plate_path(audio_uuid: str) -> Path:
    """`video/plate.npy` — the background plate (V-29). Derived from the frames.

    Cached because it is the 20th percentile of a hundred frames and every worker
    process that reads a frame needs it. Deleted with the frames it was built
    from.
    """
    return video_dir(audio_uuid) / "plate.npy"


def video_frames_dir(audio_uuid: str) -> Path:
    """`video/frames/` — the sampled frames. Derived, gitignored, disposable."""
    return video_dir(audio_uuid) / "frames"


def video_frame_path(audio_uuid: str, index: int) -> Path:
    """`video/frames/f000001.jpg` — one sampled frame, counted from 1.

    The name is ffmpeg's own `f%06d.jpg`, so the folder sorts in time order and
    nothing has to parse a name to know which frame came first.
    """
    return video_frames_dir(audio_uuid) / f"f{index:06d}.jpg"


def list_video_frames(audio_uuid: str) -> list[Path]:
    """Every sampled frame on disk, in time order."""
    folder = video_frames_dir(audio_uuid)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("f*.jpg"))


def video_frames_jsonl_path(audio_uuid: str) -> Path:
    """`video/frames.jsonl` — one line per sampled frame: its onsets and sustains."""
    return video_dir(audio_uuid) / "frames.jsonl"


def video_detection_report_path(audio_uuid: str) -> Path:
    """`video/detection-report.json` — what the last whole-video run did, in numbers.

    Kept so a change to a threshold can be compared against the run before it
    without reading the video again. A rule ships with its measured score or it
    does not ship (V-20).
    """
    return video_dir(audio_uuid) / "detection-report.json"


def video_notes_path(audio_uuid: str) -> Path:
    """`video/notes.json` — the notes the stitched roll read (V-32).

    Derived: it is stitched again whenever the reading is run again. It is not
    the piece — the piece is `events.json`, written through the writer that
    already exists (V-02). This is what will be written, kept so it can be looked
    at and corrected first (Task 4.3.1).
    """
    return video_dir(audio_uuid) / "notes.json"


def video_corrections_path(audio_uuid: str) -> Path:
    """`video/corrections.json` — the notes a person took off or put on by hand.

    **Not derived.** A reading made by a person cannot be reproduced, so this
    survives a re-stitch exactly as the calibration survives a re-sample (V-12),
    and `clear_frames` does not touch it.
    """
    return video_dir(audio_uuid) / "corrections.json"


def video_detection_dir(audio_uuid: str) -> Path:
    """`video/detection/` — debug pictures, only when asked for. Derived."""
    return video_dir(audio_uuid) / "detection"


def list_video_uuids() -> list[str]:
    """Every piece in the audio store that has a downloaded video, sorted."""
    return [uuid for uuid in list_audio_uuids() if video_source_path(uuid).is_file()]


# -------------------------------------------------------- range-edit staging


def staging_root(audio_uuid: str) -> Path:
    """`data/audio/<uuid>/staging/` — disposable Epic 11 sessions."""
    return audio_dir(audio_uuid) / "staging"


def staging_session_dir(audio_uuid: str, session_uuid: str) -> Path:
    """`data/audio/<uuid>/staging/<session_uuid>/`."""
    return staging_root(audio_uuid) / session_uuid


def history_root(audio_uuid: str) -> Path:
    """`data/audio/<uuid>/history/` — snapshots of events.json before a splice."""
    return audio_dir(audio_uuid) / "history"


def history_version_dir(audio_uuid: str, version: int) -> Path:
    """`data/audio/<uuid>/history/v1/` — one musical state, before it was replaced."""
    return history_root(audio_uuid) / f"v{version}"


def music_version_path(audio_uuid: str) -> Path:
    """`data/audio/<uuid>/matrices/music-version.json` — the current version number."""
    return audio_dir(audio_uuid) / "matrices" / "music-version.json"


def audio_mismatches_path(audio_uuid: str) -> Path:
    """Windows where the recording no longer matches the sheet, after a failed audio splice."""
    return audio_dir(audio_uuid) / "matrices" / "audio-mismatches.json"


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
