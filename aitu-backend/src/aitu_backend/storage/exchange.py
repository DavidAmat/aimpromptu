"""The ``.aitu`` file: a project exported, and imported again (implementation 02, plan section 8.3).

An export is the project bundle plus the audio files it uses, in one zip::

    <title>.aitu
      export.json                  {"format": "aimpromptu-project", "version": 1, ...}
      project.json                 as in the bundle
      parts/<partId>/notes.pmn     the piano matrix notation of the part
      parts/<partId>/sheet.json    the metadata of its piano sheet (when saved)
      parts/<partId>/timeline.json its audio timeline
      audio/<sha256>.<ext>         every file a timeline names, as stored

Nothing derived (``cache/``), nothing temporary (staging, the video) and no history: what is
exported is what the project *is*. The notes, the sheet and the timeline are copied byte for byte,
so an import reads exactly as it was saved (P-5).

An import makes a **new project in the importer's Personal Vault**, with new ids and the same
title; ``origin`` says which project it came from. The audio files keep their names, which are the
hash of their content: each one is hashed again on the way in, and a file whose content does not
match its name refuses the import. The zip is read member by member by the names this module
expects; no name in the zip ever becomes a path on the disk, so a hostile zip cannot write outside
the project.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from pydantic import ValidationError

from aitu_backend.audio import formats
from aitu_backend.pmn import notes_file
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import ProjectFile, Timeline

__all__ = [
    "EXPORT_FORMAT",
    "EXPORT_VERSION",
    "ImportRefused",
    "export_name",
    "export_project",
    "import_project",
]

EXPORT_FORMAT = "aimpromptu-project"
EXPORT_VERSION = 1
EXTENSION = ".aitu"
#: The part files an export carries, in the order they are written.
PART_FILES = ("notes.pmn", "sheet.json", "timeline.json")
#: Above this, an import is refused before anything is unpacked (a long song is about 10 MB).
MAX_TOTAL_BYTES = 2 * 1024**3
MAX_MEMBERS = 10_000
MAX_JSON_BYTES = 64 * 1024**2
_AUDIO_NAME = re.compile(r"^audio/([0-9a-f]{64})\.([a-z0-9]{2,5})$")
_AUDIO_EXTENSIONS = {suffix.lstrip(".") for suffix in formats.SUPPORTED_SUFFIXES}


class ImportRefused(ValueError):
    """The file is not a project this app can import, in words the page shows as they are."""


def export_name(title: str) -> str:
    """``<title>.aitu``, with the characters a file name cannot hold replaced."""
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return f"{cleaned[:120] or 'Untitled project'}{EXTENSION}"


def export_project(project_id: str, target: Path) -> Path:
    """Write the ``.aitu`` zip of a project to ``target``."""
    project = bundle.read_project(project_id)
    hashes: dict[str, str] = {}
    for entry in project.parts:
        timeline = bundle.read_timeline(entry.id)
        for content_hash, audio in timeline.audio.items():
            hashes[content_hash] = audio.format
    manifest = {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "projectId": project.id,
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export.json", json.dumps(manifest, indent=2) + "\n")
        archive.write(paths.project_json_path(project.id), "project.json")
        for entry in project.parts:
            folder = paths.part_dir(entry.id)
            for name in PART_FILES:
                if (folder / name).is_file():
                    archive.write(folder / name, f"parts/{entry.id}/{name}")
        for content_hash, extension in sorted(hashes.items()):
            # Already compressed (mp3, m4a) or large (wav): stored as they are.
            archive.write(
                audio_files.file_path(content_hash, extension),
                f"audio/{content_hash}.{extension}",
                compress_type=zipfile.ZIP_STORED,
            )
    return target


def _read_json(archive: zipfile.ZipFile, name: str) -> object:
    info = archive.getinfo(name)
    if info.file_size > MAX_JSON_BYTES:
        raise ImportRefused(f"{name} is too large")
    try:
        return json.loads(archive.read(name).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ImportRefused(f"{name} is not readable JSON") from exc


def _check_archive(archive: zipfile.ZipFile) -> set[str]:
    members = archive.infolist()
    if len(members) > MAX_MEMBERS:
        raise ImportRefused("This file holds too many entries to be a project")
    if sum(member.file_size for member in members) > MAX_TOTAL_BYTES:
        raise ImportRefused("This file is too large to import")
    names = {member.filename for member in members}
    if "export.json" not in names or "project.json" not in names:
        raise ImportRefused("This is not a project exported by this app")
    manifest = _read_json(archive, "export.json")
    if not isinstance(manifest, dict) or manifest.get("format") != EXPORT_FORMAT:
        raise ImportRefused("This is not a project exported by this app")
    if int(manifest.get("version") or 0) > EXPORT_VERSION:
        raise ImportRefused("This project was exported by a newer version of the app")
    return names


def _validated_part(
    archive: zipfile.ZipFile, names: set[str], part_id: str
) -> tuple[dict[str, bytes], Timeline]:
    """The bytes of one part's files, each checked to read as what it says it is."""
    files: dict[str, bytes] = {}
    for name in PART_FILES:
        member = f"parts/{part_id}/{name}"
        if member in names:
            if archive.getinfo(member).file_size > MAX_JSON_BYTES:
                raise ImportRefused(f"{member} is too large")
            files[name] = archive.read(member)
    try:
        timeline = Timeline.model_validate_json(files.get("timeline.json", b"{}"))
        if "notes.pmn" in files:
            notes = json.loads(files["notes.pmn"].decode("utf-8"))
            if not (isinstance(notes, dict) and notes_file.is_pmn(notes)):
                raise ImportRefused(f"The notes of part {part_id} are not a .pmn file")
            notes_file.from_pmn(notes)
        if "sheet.json" in files:
            SavedRhythm.model_validate_json(files["sheet.json"])
        bundle.cuts_of(timeline)
    except ImportRefused:
        raise
    except (ValidationError, ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
        raise ImportRefused(f"Part {part_id} cannot be read: {exc}") from exc
    return files, timeline


def _store_audio(archive: zipfile.ZipFile, names: set[str], wanted: dict[str, str]) -> list[str]:
    """Copy each audio file the timelines name into the store, checking its content against its
    name. Returns the hashes stored."""
    available: dict[str, str] = {}
    for name in names:
        match = _AUDIO_NAME.match(name)
        if match and match.group(2) in _AUDIO_EXTENSIONS:
            available[match.group(1)] = match.group(2)
    stored: list[str] = []
    for content_hash, extension in wanted.items():
        if available.get(content_hash) != extension:
            raise ImportRefused(f"The audio file {content_hash[:12]}… is missing from this file")
        with archive.open(f"audio/{content_hash}.{extension}") as stream:
            found = audio_files.add_stream(stream, extension)
        stored.append(found)
        if found != content_hash:
            audio_files.delete_unused([found])
            raise ImportRefused(f"The audio file {content_hash[:12]}… is damaged")
    return stored


def import_project(source: IO[bytes] | Path, *, owner_id: int) -> ProjectFile:
    """A new project in ``owner_id``'s Personal Vault from a ``.aitu`` file. Raises
    :class:`ImportRefused` when the file is not one, with nothing left behind."""
    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ImportRefused("This is not a project exported by this app") from exc
    with archive:
        names = _check_archive(archive)
        try:
            original = ProjectFile.model_validate(_read_json(archive, "project.json"))
        except ValidationError as exc:
            raise ImportRefused(f"project.json cannot be read: {exc}") from exc
        if not original.parts:
            raise ImportRefused("This project has no part")
        parts = {entry.id: _validated_part(archive, names, entry.id) for entry in original.parts}
        wanted: dict[str, str] = {}
        for _, timeline in parts.values():
            for content_hash, audio in timeline.audio.items():
                wanted[content_hash] = audio.format
        stored = _store_audio(archive, names, wanted)

        copy: ProjectFile | None = None
        try:
            copy, mapping = bundle.new_bundle_from(
                original,
                owner_id=owner_id,
                origin={"importedFrom": original.id},
            )
            for old_id, new_id in mapping.items():
                folder = paths.part_dir(new_id)
                for name, body in parts[old_id][0].items():
                    (folder / name).write_bytes(body)
            bundle.write_project(copy, touch=False)
            bundle.sync_audio_refs(copy.id)
        except Exception:
            if copy is not None:
                try:
                    bundle.delete_project(copy.id)
                except locate.NotFound:
                    pass
            audio_files.delete_unused(stored)
            raise
    return copy


def import_upload(stream: IO[bytes], *, owner_id: int) -> ProjectFile:
    """:func:`import_project` from an upload, spooled to a temporary file first (a zip needs to
    seek)."""
    with tempfile.TemporaryFile() as spooled:
        shutil.copyfileobj(stream, spooled, length=1024 * 1024)
        spooled.seek(0)
        return import_project(spooled, owner_id=owner_id)
