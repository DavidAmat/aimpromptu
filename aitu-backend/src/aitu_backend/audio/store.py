"""The audio working store: one uuid folder per ingested audio.

```text
data/audio/<uuid>/
  metadata.json      alias, source, format, duration, created_at
  original.<ext>     the file exactly as it arrived
  normalized.wav     mono WAV at the transcription rate (Task 3.2.1)
  waveform.json      cached peaks (Task 3.2.1)
```

**Every filesystem access for audio goes through this module.** Nothing else
opens, writes or deletes a file under ``data/audio/``. That is the whole point:
if this is ever backed by MinIO instead of a local disk, swapping the six
functions below is the entire change. Not building MinIO now.
"""

from __future__ import annotations

import json
import shutil
import uuid as uuid_module
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable

from aitu_backend.schemas.metadata import AudioMetadata, AudioSource
from aitu_backend.storage import paths

#: Copied in chunks so a large upload never lands in memory whole.
COPY_CHUNK_BYTES = 1024 * 1024


class AudioNotFound(KeyError):
    """No uuid folder for the requested audio."""

    def __init__(self, audio_uuid: str) -> None:
        self.audio_uuid = audio_uuid
        super().__init__(f"No audio with uuid '{audio_uuid}'")


@dataclass(frozen=True)
class StoredAudio:
    """An entry in the store: its metadata plus where its files live."""

    metadata: AudioMetadata
    directory: Path

    @property
    def uuid(self) -> str:
        return self.metadata.uuid

    @property
    def original_path(self) -> Path | None:
        return paths.find_audio_original(self.uuid)

    @property
    def normalized_path(self) -> Path:
        return self.directory / "normalized.wav"

    @property
    def waveform_path(self) -> Path:
        return self.directory / "waveform.json"

    def has_normalized(self) -> bool:
        return self.normalized_path.is_file()


# ------------------------------------------------------------------- creating


def new_uuid() -> str:
    return str(uuid_module.uuid4())


def create(
    alias: str,
    source: AudioSource | str,
    extension: str,
    *,
    audio_uuid: str | None = None,
    original_filename: str | None = None,
    source_url: str | None = None,
) -> StoredAudio:
    """Create an empty uuid folder with its metadata. No audio bytes yet."""
    audio_uuid = audio_uuid or new_uuid()
    directory = paths.audio_dir(audio_uuid)
    if directory.exists():
        raise FileExistsError(f"Audio folder already exists: {audio_uuid}")
    directory.mkdir(parents=True)

    metadata = AudioMetadata(
        uuid=audio_uuid,
        alias=alias,
        source=AudioSource(source),
        format=extension.lstrip("."),
        original_filename=original_filename,
        source_url=source_url,
    )
    write_metadata(metadata)
    return StoredAudio(metadata=metadata, directory=directory)


def save_original(audio_uuid: str, stream: BinaryIO | Iterable[bytes], extension: str) -> Path:
    """Write the incoming bytes as ``original.<ext>``, streaming in chunks."""
    target = paths.audio_original_path(audio_uuid, extension)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("wb") as handle:
        reader = getattr(stream, "read", None)
        if reader is not None:
            while True:
                chunk = reader(COPY_CHUNK_BYTES)
                if not chunk:
                    break
                handle.write(chunk)
        else:
            for chunk in stream:
                handle.write(chunk)
    return target


# -------------------------------------------------------------------- reading


def exists(audio_uuid: str) -> bool:
    return paths.audio_metadata_path(audio_uuid).is_file()


def read_metadata(audio_uuid: str) -> AudioMetadata:
    """Load one audio's metadata. Raises :class:`AudioNotFound`."""
    path = paths.audio_metadata_path(audio_uuid)
    if not path.is_file():
        raise AudioNotFound(audio_uuid)
    return AudioMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def get(audio_uuid: str) -> StoredAudio:
    """The full store entry for one uuid."""
    return StoredAudio(
        metadata=read_metadata(audio_uuid),
        directory=paths.audio_dir(audio_uuid),
    )


def list_all() -> list[StoredAudio]:
    """Every entry in the store, newest first.

    Folders without readable metadata are skipped rather than raising: a
    half-written ingest must not break the whole library listing.
    """
    entries: list[StoredAudio] = []
    for audio_uuid in paths.list_audio_uuids():
        try:
            entries.append(get(audio_uuid))
        except (AudioNotFound, ValueError):
            continue
    entries.sort(key=lambda entry: entry.metadata.created_at, reverse=True)
    return entries


# -------------------------------------------------------------------- writing


def write_metadata(metadata: AudioMetadata) -> Path:
    """Persist metadata, creating the folder if needed."""
    path = paths.audio_metadata_path(metadata.uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        metadata.model_dump_json(by_alias=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def update(audio_uuid: str, **changes: object) -> AudioMetadata:
    """Patch metadata fields by name and persist. Returns the new metadata.

    Only known fields are accepted; ``uuid`` cannot be changed, since it is the
    folder name.
    """
    metadata = read_metadata(audio_uuid)
    if "uuid" in changes:
        raise ValueError("An audio's uuid is its folder name and cannot be changed")

    unknown = set(changes) - set(type(metadata).model_fields)
    if unknown:
        raise ValueError(f"Unknown audio metadata field(s): {sorted(unknown)}")

    updated = metadata.model_copy(update={k: v for k, v in changes.items() if v is not None})
    write_metadata(updated)
    return updated


def rename(audio_uuid: str, alias: str) -> AudioMetadata:
    """Change the display alias — the common case, so it gets its own verb."""
    if not alias.strip():
        raise ValueError("Alias cannot be empty")
    return update(audio_uuid, alias=alias.strip())


def delete(audio_uuid: str) -> None:
    """Remove the whole uuid folder. Raises :class:`AudioNotFound` if absent."""
    if not exists(audio_uuid):
        raise AudioNotFound(audio_uuid)
    shutil.rmtree(paths.audio_dir(audio_uuid))


# ------------------------------------------------------------------- waveform


def read_waveform(audio_uuid: str) -> dict | None:
    """Cached peaks, or ``None`` when they have not been computed yet."""
    path = get(audio_uuid).waveform_path
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_waveform(audio_uuid: str, payload: dict) -> Path:
    """Cache computed peaks next to the audio."""
    path = get(audio_uuid).waveform_path
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
