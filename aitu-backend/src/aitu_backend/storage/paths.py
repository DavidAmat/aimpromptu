"""Every filesystem path the backend uses, built in one place (implementation 02, plan section 8).

Everything the app knows is in ``.database/``, at the root of the repository unless
``AITU_DATABASE_DIR`` says otherwise::

    .database/
      aitu.sqlite                    every record (db/models.py), WAL mode
      VERSION                        the layout version, checked when the database opens
      audio/<sha256>.<ext>           every audio file, once, named by its content (P-3)
      users/<userId>/
        vault/<projectId>/           layer 1: the Personal Vault
        library/<projectId>/         layer 2: the Private Library
      public/<projectId>/            layer 3: the Public Library
      tmp/<userId>/<partId>/video/   temporary files: a video, its frames, its reading
      lab/frame-examples/            the video reader's example data (Lab)
      history/<projectId>/           earlier states: parts/<partId>/vN/ before a splice or a
                                     transcription replaced them
      jobs/                          reserved

A project bundle (section 8.3), the same in every layer::

    <projectId>/
      project.json                   the project's own metadata, and its parts in order
      parts/<partId>/
        notes.pmn                    the piano matrix notation of the part (P-5)
        sheet.json                   the metadata of the part's piano sheet
        timeline.json                the audio timeline of the part (section 8.5)
        music-version.json, audio-mismatches.json, needs-rederivation.json   when they apply
      staging/<sessionId>/           disposable edit sessions
      cache/<partId>/                derived, safe to delete: normalized.wav (the engine's 16 kHz
                                     mono audio), waveform.json, piece-r<N>.flac/.wav (the joined
                                     audio of a part with cuts), scratch clips

The functions of a part take the part's id, the uuid of today's routes (P-6). The folder of its
project comes from :mod:`aitu_backend.storage.locate`.

``aitu-backend/data/`` is the store before Phase 3. Only the migration
(``scripts/migrate/to_database.py``) reads it, through :func:`data_dir`.

No path literal lives outside this module.
"""

from __future__ import annotations

from pathlib import Path

from aitu_backend import config
from aitu_backend.storage import locate

# --------------------------------------------------------------------- roots


def backend_root() -> Path:
    """`aitu-backend/` — the folder holding `pyproject.toml` and `src/`."""
    return Path(__file__).resolve().parents[3]


def repo_root() -> Path:
    """The repository root — the folder holding `aitu-backend/` and `context/`."""
    return backend_root().parent


def data_dir() -> Path:
    """`aitu-backend/data/`, the store before Phase 3, unless `AITU_DATA_DIR` says otherwise.

    Read by the migration only. The app writes nothing here.
    """
    return config.data_dir_override() or backend_root() / "data"


def database_dir() -> Path:
    """`.database/`: every record and every file of the app (plan section 8.1)."""
    return config.database_dir_override() or repo_root() / ".database"


def sqlite_path() -> Path:
    return database_dir() / "aitu.sqlite"


def layout_version_path() -> Path:
    return database_dir() / "VERSION"


def audio_store_dir() -> Path:
    """`.database/audio/` — every audio file, once."""
    return database_dir() / "audio"


def audio_file_path(content_hash: str, extension: str) -> Path:
    """`.database/audio/<sha256>.<ext>`."""
    return audio_store_dir() / f"{content_hash}.{extension.lstrip('.')}"


def users_dir() -> Path:
    return database_dir() / "users"


def public_dir() -> Path:
    """`.database/public/` — layer 3."""
    return database_dir() / "public"


def tmp_dir() -> Path:
    return database_dir() / "tmp"


def lab_dir() -> Path:
    return database_dir() / "lab"


def history_dir() -> Path:
    return database_dir() / "history"


def jobs_dir() -> Path:
    return database_dir() / "jobs"


#: The folder of each layer under `users/<userId>/`.
LAYER_FOLDERS = {"vault": "vault", "private": "library"}


def layer_dir(owner_id: int, layer: str) -> Path:
    """Where the projects of one owner and one layer are."""
    if layer == "public":
        return public_dir()
    return users_dir() / str(owner_id) / LAYER_FOLDERS[layer]


#: Created when the app starts, by :func:`ensure_database_tree`.
TREE_ROOTS = (audio_store_dir, users_dir, public_dir, tmp_dir, history_dir, jobs_dir)


def ensure_database_tree() -> None:
    """Create the top folders of `.database/` if missing. Called on app startup."""
    for root in TREE_ROOTS:
        root().mkdir(parents=True, exist_ok=True)
    frame_examples_root().mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ projects


def project_dir_at(project_id: str, owner_id: int, layer: str) -> Path:
    """The folder a project has, or will have, in a layer."""
    return layer_dir(owner_id, layer) / project_id


def project_dir(project_id: str) -> Path:
    """The folder of a project, wherever it is. Raises :class:`locate.NotFound`."""
    where = locate.project(project_id)
    return project_dir_at(project_id, where.owner_id, where.layer)


def project_json_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def _part_project_dir(part_id: str) -> Path:
    where = locate.part(part_id)
    return project_dir_at(where.project_id, where.owner_id, where.layer)


def part_dir(part_id: str) -> Path:
    """`<project>/parts/<partId>/`. Raises :class:`locate.NotFound`."""
    return _part_project_dir(part_id) / "parts" / part_id


def part_notes_path(part_id: str) -> Path:
    """`notes.pmn` — the piano matrix notation of the part, the only stored music (rule 1)."""
    return part_dir(part_id) / "notes.pmn"


def part_sheet_path(part_id: str) -> Path:
    """`sheet.json` — the reader's decisions on the piano sheet (was `rhythm.json`)."""
    return part_dir(part_id) / "sheet.json"


def part_timeline_path(part_id: str) -> Path:
    """`timeline.json` — the audio segments the part plays one after the other."""
    return part_dir(part_id) / "timeline.json"


def needs_rederivation_path(part_id: str) -> Path:
    return part_dir(part_id) / "needs-rederivation.json"


def music_version_path(part_id: str) -> Path:
    """`music-version.json` — the number of the next history snapshot of the part."""
    return part_dir(part_id) / "music-version.json"


def audio_mismatches_path(part_id: str) -> Path:
    """Windows where the recording no longer matches the sheet, after a failed audio splice."""
    return part_dir(part_id) / "audio-mismatches.json"


def part_cache_dir(part_id: str) -> Path:
    """`<project>/cache/<partId>/` — derived files of the part, safe to delete."""
    return _part_project_dir(part_id) / "cache" / part_id


def normalized_path(part_id: str) -> Path:
    """`normalized.wav`: the audio of the part's file at 16 kHz mono, the engine's input."""
    return part_cache_dir(part_id) / "normalized.wav"


def waveform_path(part_id: str) -> Path:
    return part_cache_dir(part_id) / "waveform.json"


# -------------------------------------------------------- range-edit staging


def staging_root(part_id: str) -> Path:
    """`<project>/staging/` — disposable edit sessions of every part of the project."""
    return _part_project_dir(part_id) / "staging"


def staging_session_dir(part_id: str, session_uuid: str) -> Path:
    """`<project>/staging/<sessionId>/`."""
    return staging_root(part_id) / session_uuid


# ------------------------------------------------------------------- history


def part_history_dir(part_id: str) -> Path:
    """`.database/history/<projectId>/parts/<partId>/`."""
    where = locate.part(part_id)
    return history_dir() / where.project_id / "parts" / part_id


def history_version_dir(part_id: str, version: int) -> Path:
    """`.../parts/<partId>/v1/` — one musical state, before it was replaced."""
    return part_history_dir(part_id) / f"v{version}"


# --------------------------------------------------------------------- video
#
# A video belongs to the part whose audio came out of it (V-03), and it is a temporary file of its
# owner (plan section 8.5): `tmp/<userId>/<partId>/video/`. The video file is the source and the
# sampled frames are a cache (V-01), so everything under `frames/` can be thrown away and written
# again. Only `calibration.json` and `corrections.json` cannot: they are the user's work.


def video_dir(part_id: str) -> Path:
    """`tmp/<userId>/<partId>/video/` — everything about the picture of this part."""
    where = locate.part(part_id)
    return tmp_dir() / str(where.owner_id) / part_id / "video"


def video_source_path(part_id: str) -> Path:
    """`video/source.mp4` — the download. The audio was extracted from this file."""
    return video_dir(part_id) / "source.mp4"


def video_metadata_path(part_id: str) -> Path:
    """`video/metadata_video.json` — size, duration, frames per second, `sampleMs`."""
    return video_dir(part_id) / "metadata_video.json"


def video_calibration_path(part_id: str) -> Path:
    """`video/calibration.json` — the piano overlay and everything measured from it.

    Kept beside the video and never merged into `sheet.json` (V-12): how the notes were read off
    the screen is a different thing from what a reader decided about the sheet.
    """
    return video_dir(part_id) / "calibration.json"


def video_plate_path(part_id: str) -> Path:
    """`video/plate.npy` — the background plate (V-29). Derived from the frames."""
    return video_dir(part_id) / "plate.npy"


def video_frames_dir(part_id: str) -> Path:
    """`video/frames/` — the sampled frames. Derived and disposable."""
    return video_dir(part_id) / "frames"


def video_frame_path(part_id: str, index: int) -> Path:
    """`video/frames/f000001.jpg` — one sampled frame, counted from 1 (ffmpeg's `f%06d.jpg`)."""
    return video_frames_dir(part_id) / f"f{index:06d}.jpg"


def list_video_frames(part_id: str) -> list[Path]:
    """Every sampled frame on disk, in time order."""
    folder = video_frames_dir(part_id)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("f*.jpg"))


def video_frames_jsonl_path(part_id: str) -> Path:
    """`video/frames.jsonl` — one line per sampled frame: its onsets and sustains."""
    return video_dir(part_id) / "frames.jsonl"


def video_detection_report_path(part_id: str) -> Path:
    """`video/detection-report.json` — what the last whole-video run did, in numbers (V-20)."""
    return video_dir(part_id) / "detection-report.json"


def video_notes_path(part_id: str) -> Path:
    """`video/notes.json` — the notes the stitched roll read (V-32). Derived: it is stitched again
    whenever the reading is run again. The part's notes are `notes.pmn` (V-02)."""
    return video_dir(part_id) / "notes.json"


def video_corrections_path(part_id: str) -> Path:
    """`video/corrections.json` — the notes a person took off or put on by hand. **Not derived**:
    it survives a re-stitch exactly as the calibration survives a re-sample (V-12)."""
    return video_dir(part_id) / "corrections.json"


def video_detection_dir(part_id: str) -> Path:
    """`video/detection/` — debug pictures, only when asked for. Derived."""
    return video_dir(part_id) / "detection"


def list_video_part_ids() -> list[str]:
    """Every part that has a downloaded video, sorted: `tmp/<userId>/<partId>/video/source.mp4`."""
    root = tmp_dir()
    if not root.is_dir():
        return []
    return sorted({path.parents[1].name for path in root.glob("*/*/video/source.mp4")})


# ------------------------------------------------------- the example frames
#
# The Synthesia example screenshots stay where the user put them, under `context/implementations/`.
# Only what we derive from them is data, in Lab: one calibration and one set of manual annotations
# per example, plus the working-resolution copy the browser is served.


def frame_examples_source_dir() -> Path:
    """The example screenshots, read only, where the plan keeps them."""
    return (
        repo_root()
        / "context"
        / "implementations"
        / "01-mvp"
        / "04-synthesia-to-notes"
        / "examples"
    )


def frame_examples_seed_dir() -> Path:
    """`aitu-backend/data/frame-examples/` — the committed records the Lab copy started from."""
    return data_dir() / "frame-examples"


def frame_examples_root() -> Path:
    """`.database/lab/frame-examples/` — one record per example screenshot."""
    return lab_dir() / "frame-examples"


def frame_example_path(slug: str) -> Path:
    """`lab/frame-examples/<slug>.json` — its calibration and its annotations."""
    return frame_examples_root() / f"{slug}.json"


def frame_example_image_path(slug: str) -> Path:
    """`lab/frame-examples/cache/<slug>.jpg` — the working-resolution copy, derived.

    The screenshots are 3600 px wide and the detector works at 1280, so the browser is served the
    same picture the detector reads and a calibration means the same thing on both sides.
    """
    return frame_examples_root() / "cache" / f"{slug}.jpg"


def list_frame_example_slugs() -> list[str]:
    """Every example screenshot on disk, sorted."""
    source = frame_examples_source_dir()
    if not source.is_dir():
        return []
    return sorted(p.stem for p in source.glob("*.png"))
