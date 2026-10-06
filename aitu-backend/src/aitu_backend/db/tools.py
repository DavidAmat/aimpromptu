"""``make db-backup``, ``db-restore``, ``db-check`` and ``db-reindex`` (implementation 02, plan
section 8.7).

::

    python -m aitu_backend.db.tools backup [--out FOLDER]
    python -m aitu_backend.db.tools restore FILE
    python -m aitu_backend.db.tools check [--hashes]
    python -m aitu_backend.db.tools reindex

* **backup** writes ``.database-YYYYMMDD-HHMMSS.tar.zst`` (UTC) beside ``.database/``. SQLite's own
  backup command copies the database first, so a running app gives a consistent copy; the rest of
  the folder is copied as it is (the audio files never change once written).
* **restore** unpacks a backup into an empty ``.database/``.
* **check** compares the tables with the bundles and the audio store, and exits 1 on a problem.
* **reindex** writes the ``projects``, ``parts``, ``audio_files`` and ``audio_refs`` rows again
  from what is on disk: the bundles are the truth for the music (section 8.6).

They need ``tar`` with zstd, so the Makefile runs them on the host, not in the container.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from aitu_backend.db import database
from aitu_backend.db.database import session
from aitu_backend.db.models import STEPS, AudioFile, AudioRef, Part, Project, User
from aitu_backend.pmn import events_file
from aitu_backend.storage import bundle, locate, paths

__all__ = ["backup", "check", "refresh_step", "reindex", "restore"]

SQLITE_FILES = ("aitu.sqlite", "aitu.sqlite-wal", "aitu.sqlite-shm")


# -------------------------------------------------------------------- the step


def refresh_step(project_id: str) -> str | None:
    """Record the lowest step its parts reached (plan section 10.5), for the list of projects."""
    from aitu_backend.pieces.status import (
        piece_status,
    )  # noqa: PLC0415 - heavy, and a cycle

    reached = []
    for part_id in bundle.part_ids_of(project_id):
        try:
            reached.append(piece_status(part_id).resume)
        except Exception:  # noqa: BLE001 - a part that cannot be read has no step
            continue
    step = min(reached, key=STEPS.index) if reached else None
    with session() as db:
        row = db.get(Project, project_id)
        if row is not None:
            row.step = step
    return step


# ---------------------------------------------------------------------- backup


def backup(out_dir: Path | None = None) -> Path:
    root = paths.database_dir().resolve()
    target_dir = out_dir or paths.database_dir().parent
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive = target_dir / f".database-{stamp}.tar.zst"
    with tempfile.TemporaryDirectory(prefix="aitu-backup-") as staging:
        # In a folder of its own: the excludes below skip the live files by name, and would skip
        # this copy too if it were also `./aitu.sqlite`.
        copy = Path(staging) / "snapshot" / "aitu.sqlite"
        copy.parent.mkdir()
        if paths.sqlite_path().is_file():
            source = sqlite3.connect(paths.sqlite_path())
            destination = sqlite3.connect(copy)
            with destination:
                source.backup(destination)
            source.close()
            destination.close()
        command = ["tar", "--zstd", "-cf", str(archive)]
        command += [f"--exclude=./{name}" for name in SQLITE_FILES]
        command += [
            "--transform",
            r"s,^\.,.database,",
            "--transform",
            r"s,^snapshot/,.database/,",
        ]
        command += ["-C", str(root), "."]
        if copy.is_file():
            command += ["-C", staging, "snapshot/aitu.sqlite"]
        result = subprocess.run(command)
        # 1 is GNU tar's "a file changed while it was read": the app wrote a file during the copy.
        if result.returncode == 1:
            print(
                "warning: a file changed while it was copied (the app was writing); "
                "the backup is kept, run it again for a quiet copy",
                file=sys.stderr,
            )
        elif result.returncode != 0:
            archive.unlink(missing_ok=True)
            raise subprocess.CalledProcessError(result.returncode, command)
    return archive


def restore(archive: Path) -> Path:
    """Unpack a backup into ``.database/``, which must be empty (or missing)."""
    root = paths.database_dir()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"{root} is not empty; restore only into an empty .database/")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aitu-restore-", dir=root.resolve().parent) as work:
        subprocess.run(["tar", "--zstd", "-xf", str(archive), "-C", work], check=True)
        unpacked = Path(work) / ".database"
        for child in unpacked.iterdir():
            shutil.move(str(child), root / child.name)
    database.forget_engines()
    locate.forget()
    return root


# ----------------------------------------------------------------------- check


@dataclass
class Report:
    counts: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"counts": self.counts, "problems": self.problems, "notes": self.notes}


def _bundles_on_disk() -> dict[str, tuple[int, str, Path]]:
    """``project id -> (owner, layer, folder)`` for every ``project.json`` on disk."""
    found: dict[str, tuple[int, str, Path]] = {}
    folders = {"vault": "vault", "library": "private"}
    for user_dir in (sorted(paths.users_dir().glob("*")) if paths.users_dir().is_dir() else []):
        if not user_dir.name.isdigit():
            continue
        for folder, layer in folders.items():
            for project_json in sorted((user_dir / folder).glob("*/project.json")):
                found[project_json.parent.name] = (
                    int(user_dir.name),
                    layer,
                    project_json.parent,
                )
    for project_json in sorted(paths.public_dir().glob("*/project.json")):
        project = json.loads(project_json.read_text(encoding="utf-8"))
        found[project_json.parent.name] = (
            int(project["ownerId"]),
            "public",
            project_json.parent,
        )
    return found


def check(*, hashes: bool = False) -> Report:
    report = Report()
    database.engine()  # checks VERSION and the revision
    on_disk = _bundles_on_disk()
    with session() as db:
        rows = {row.id: row for row in db.scalars(select(Project))}
        part_rows: dict[str, list[str]] = {}
        for part in db.scalars(select(Part).order_by(Part.position)):
            part_rows.setdefault(part.project_id, []).append(part.id)
        files = {row.hash: row for row in db.scalars(select(AudioFile))}
        refs: dict[str, set[str]] = {}
        for ref in db.scalars(select(AudioRef)):
            refs.setdefault(ref.project_id, set()).add(ref.hash)

    report.counts = {
        "projects": len(rows),
        "bundles": len(on_disk),
        "parts": sum(len(ids) for ids in part_rows.values()),
        "audioFiles": len(files),
        "audioBytes": sum(row.size_bytes for row in files.values()),
    }
    for project_id in sorted(set(rows) - set(on_disk)):
        report.problems.append(f"project {project_id}: a row with no bundle on disk")
    for project_id in sorted(set(on_disk) - set(rows)):
        report.problems.append(f"project {project_id}: a bundle with no row (run db-reindex)")

    used: set[str] = set()
    for project_id in sorted(set(rows) & set(on_disk)):
        row = rows[project_id]
        owner, layer, folder = on_disk[project_id]
        if (row.owner_id, row.layer) != (owner, layer):
            report.problems.append(
                f"project {project_id}: the row says {row.layer} of user {row.owner_id}, the "
                f"folder says {layer} of user {owner}"
            )
        project = bundle.ProjectFile.model_validate_json(
            (folder / "project.json").read_text(encoding="utf-8")
        )
        if [entry.id for entry in project.parts] != part_rows.get(project_id, []):
            report.problems.append(f"project {project_id}: its parts differ from the parts rows")
        for part_id in part_rows.get(project_id, []):
            part_dir = folder / "parts" / part_id
            notes = part_dir / "notes.pmn"
            if notes.is_file() and events_file.read_payload(notes) is None:
                report.problems.append(f"part {part_id}: notes.pmn cannot be read")
            timeline = bundle.read_timeline(part_id)
            for content_hash, entry in timeline.audio.items():
                if content_hash not in files:
                    report.problems.append(f"part {part_id}: audio {content_hash[:12]} has no row")
                if not paths.audio_file_path(content_hash, entry.format).is_file():
                    report.problems.append(f"part {part_id}: audio {content_hash[:12]} is missing")
        wanted = bundle.used_hashes(project_id)
        used |= wanted
        if wanted != refs.get(project_id, set()):
            report.problems.append(f"project {project_id}: audio_refs differ from its bundle")

    store_files = {
        path.stem: path
        for path in (paths.audio_store_dir().iterdir() if paths.audio_store_dir().is_dir() else [])
        if path.is_file() and not path.name.startswith(".")
    }
    for content_hash in sorted(set(files) - set(store_files)):
        report.problems.append(f"audio {content_hash[:12]}: a row with no file")
    for content_hash in sorted(set(store_files) - set(files)):
        report.problems.append(f"audio {content_hash[:12]}: a file with no row")
    unused = sorted(set(files) - used)
    if unused:
        report.notes.append(f"{len(unused)} audio file(s) no project uses: {unused}")
    if hashes:
        from aitu_backend.storage import audio_files  # noqa: PLC0415

        for content_hash, path in sorted(store_files.items()):
            if audio_files.hash_file(path) != content_hash:
                report.problems.append(f"audio {content_hash[:12]}: its content changed")
    return report


# --------------------------------------------------------------------- reindex


def reindex() -> Report:
    """Write the rows of the projects, their parts and the audio files again from the disk."""
    report = Report()
    database.engine()
    on_disk = _bundles_on_disk()
    with session() as db:
        for owner in {owner for owner, _, _ in on_disk.values()}:
            if db.get(User, owner) is None:
                db.add(User(id=owner, username=f"user{owner}", role="user"))
                report.notes.append(f"user {owner} had no row; made as user{owner}")
        db.flush()
        for project_id in set(db.scalars(select(Project.id))) - set(on_disk):
            db.delete(db.get(Project, project_id))
            report.notes.append(f"project {project_id}: no bundle, row deleted")
        for project_id, (owner, layer, folder) in on_disk.items():
            project = bundle.ProjectFile.model_validate_json(
                (folder / "project.json").read_text(encoding="utf-8")
            )
            row = db.get(Project, project_id) or Project(id=project_id)
            row.owner_id, row.layer, row.kind = owner, layer, project.kind
            row.title, row.based_on = project.title, project.based_on
            row.created_at, row.updated_at = project.created_at, project.updated_at
            db.merge(row)
            db.flush()
            db.execute(delete(Part).where(Part.project_id == project_id))
            for position, entry in enumerate(project.parts):
                db.add(Part(id=entry.id, project_id=project_id, position=position))
        store_dir = paths.audio_store_dir()
        for path in sorted(store_dir.iterdir()) if store_dir.is_dir() else []:
            if (
                path.is_file()
                and not path.name.startswith(".")
                and db.get(AudioFile, path.stem) is None
            ):
                db.add(
                    AudioFile(
                        hash=path.stem,
                        format=path.suffix.lstrip("."),
                        size_bytes=path.stat().st_size,
                    )
                )
    locate.forget()
    for project_id in on_disk:
        bundle.sync_audio_refs(project_id)
        refresh_step(project_id)
    report.counts = {"projects": len(on_disk)}
    return report


# ------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    made = commands.add_parser("backup")
    made.add_argument("--out", type=Path)
    restored = commands.add_parser("restore")
    restored.add_argument("file", type=Path)
    checked = commands.add_parser("check")
    checked.add_argument("--hashes", action="store_true", help="also hash every audio file")
    commands.add_parser("reindex")
    args = parser.parse_args(argv)

    if args.command == "backup":
        archive = backup(args.out)
        print(f"{archive}  {archive.stat().st_size / 1e6:.1f} MB")
        return 0
    if args.command == "restore":
        print(f"restored into {restore(args.file)}")
        return 0
    result = check(hashes=args.hashes) if args.command == "check" else reindex()
    print(json.dumps(result.to_json(), indent=2))
    return 1 if result.problems else 0


if __name__ == "__main__":
    sys.exit(main())
