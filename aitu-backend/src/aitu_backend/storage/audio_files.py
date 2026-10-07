"""The audio store: every audio file once, named by the SHA-256 of its content (plan P-3).

``.database/audio/<sha256>.<ext>``. A file here never changes: an edit that makes new audio (a
splice, a passage put in) adds a new file. So a duplicated project, a pasted passage or a pull from
the Public Library points at the same file and copies no audio bytes.

The ``audio_files`` table records each file (format, length, size); ``audio_refs`` records which
project uses which file (:func:`aitu_backend.storage.bundle.sync_audio_refs`). A file is deleted only
when no project uses it (:func:`delete_unused`), and nothing deletes one in the Personal Vault.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, Iterable

from sqlalchemy import select

from aitu_backend.db.database import session
from aitu_backend.db.models import AudioFile, AudioRef
from aitu_backend.storage import paths

__all__ = [
    "add_file",
    "add_stream",
    "delete_unused",
    "file_path",
    "hash_file",
    "info",
    "record_duration",
]

CHUNK_BYTES = 1024 * 1024


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_path(content_hash: str, extension: str) -> Path:
    return paths.audio_file_path(content_hash, extension)


def _register(content_hash: str, extension: str, size: int, duration_ms: int | None) -> None:
    with session() as db:
        row = db.get(AudioFile, content_hash)
        if row is None:
            db.add(
                AudioFile(
                    hash=content_hash, format=extension, size_bytes=size, duration_ms=duration_ms
                )
            )
        elif duration_ms is not None and row.duration_ms is None:
            row.duration_ms = duration_ms


def add_file(source: Path, extension: str, *, duration_ms: int | None = None) -> str:
    """Copy ``source`` into the store and return its hash. A file already there is not copied."""
    extension = extension.lstrip(".").lower()
    content_hash = hash_file(source)
    target = file_path(content_hash, extension)
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp")
        shutil.copyfile(source, temporary)
        temporary.replace(target)
    _register(content_hash, extension, target.stat().st_size, duration_ms)
    return content_hash


def add_stream(stream: BinaryIO | Iterable[bytes], extension: str) -> str:
    """Write incoming bytes into the store, in chunks, and return their hash."""
    extension = extension.lstrip(".").lower()
    root = paths.audio_store_dir()
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with tempfile.NamedTemporaryFile(dir=root, prefix=".upload-", delete=False) as handle:
        temporary = Path(handle.name)
        reader = getattr(stream, "read", None)
        chunks = iter(lambda: reader(CHUNK_BYTES), b"") if reader is not None else stream
        for chunk in chunks:
            digest.update(chunk)
            handle.write(chunk)
    content_hash = digest.hexdigest()
    target = file_path(content_hash, extension)
    if target.is_file():
        temporary.unlink()
    else:
        temporary.replace(target)
    _register(content_hash, extension, target.stat().st_size, None)
    return content_hash


def record_duration(content_hash: str, duration_ms: int) -> None:
    """Record the length of a stored file once it is measured."""
    with session() as db:
        row = db.get(AudioFile, content_hash)
        if row is not None and row.duration_ms is None:
            row.duration_ms = duration_ms


def info(content_hash: str) -> AudioFile | None:
    with session() as db:
        return db.get(AudioFile, content_hash)


def delete_unused(hashes: Iterable[str]) -> list[str]:
    """Delete the files among ``hashes`` that no project uses any more. Returns what was deleted."""
    deleted: list[str] = []
    with session() as db:
        for content_hash in set(hashes):
            used = db.scalar(select(AudioRef.project_id).where(AudioRef.hash == content_hash))
            row = db.get(AudioFile, content_hash)
            if used is not None or row is None:
                continue
            file_path(content_hash, row.format).unlink(missing_ok=True)
            db.delete(row)
            deleted.append(content_hash)
    return deleted
