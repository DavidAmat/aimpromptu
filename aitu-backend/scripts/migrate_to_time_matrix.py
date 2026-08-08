#!/usr/bin/env python
"""Carry the stored artifacts across to the wall-clock model, or say why not.

Task P4.5, and success criterion 5: **every stored artifact either migrates or is
explicitly marked as needing re-derivation. Nothing is silently reinterpreted.**

Read `progress/P4.1-artifact-inventory.md` before running this. It classifies
what is on disk, and this script acts on the same four verdicts.

What migrating actually means here, because it is less than it sounds. The
wall-clock path reads ``events.json`` and works everything else out on each
request, so a piece with its recorded notes intact is *already* on the new model
and needs no conversion. What it needs is for the leftovers of the old model to
stop sitting next to it looking authoritative: ``raw.npz`` and its granularity
sidecar, the collapsed and clean grids, the split hands and the stored hand map.
Those were built at a tempo that is written down nowhere, so reading one as wall
clock would move every note in it without saying so.

So this script does three things:

1. **Copies the whole data tree aside first.** ``data/audio/**`` is not in git,
   so the recorded notes exist in one place only and every step below is
   irreversible without a copy.
2. **Moves the old files out of the way** for each piece that has its recorded
   notes, into ``_replaced-by-time-matrix/`` beside them. Moved rather than
   deleted: this is the one operation nobody can undo, and disk is cheap.
3. **Marks what it cannot carry.** A piece with no ``events.json`` cannot be
   rebuilt at all, and a saved version on a beat grid cannot either. Both are
   flagged with a sentence a reader can act on, which the audio list and the
   Rhythm screen show. Re-transcribing clears the flag.

Run::

    uv run python scripts/migrate_to_time_matrix.py            # dry run, changes nothing
    uv run python scripts/migrate_to_time_matrix.py --apply    # do it
    uv run python scripts/migrate_to_time_matrix.py --apply --data DIR

A dry run is the default on purpose. Read what it says it will do, then run it
again with ``--apply``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

MATRICES_DIR = "matrices"
EVENTS_FILE = "events.json"
NEEDS_REDERIVATION_FILE = "needs-rederivation.json"

#: Where the old files go. Beside the piece rather than in a global folder, so a
#: person looking at one confusing artifact finds its own history next to it.
REPLACED_DIR = "_replaced-by-time-matrix"

#: Everything the old pipeline wrote. `events.json` is deliberately not here.
STALE_PATTERNS = (
    "raw.npz",
    "raw_before_edit.npz",
    "raw-granularity.txt",
    "raw-edited.flag",
    "collapsed_*.npz",
    "clean_*.npz",
    "two-hands_*.npz",
    "hands_*.json",
    "score.json",
)

NO_EVENTS_REASON = (
    "This piece was transcribed before the recorded note times were kept, so "
    "there is nothing to write a sheet from. Open Upload / Input, pick it, and "
    "press Run transcription."
)

BEAT_GRID_REASON = (
    "This version was saved on a grid built from a tempo, and that tempo was not "
    "recorded. Reading it as wall clock would move every note. Transcribe the "
    "source audio again to get a version that can be drawn."
)


@dataclass
class Action:
    """One thing the migration will do, or did."""

    kind: str
    target: str
    detail: str = ""


@dataclass
class Result:
    backup: str | None = None
    actions: list[Action] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, kind: str, target: str, detail: str = "") -> None:
        self.actions.append(Action(kind=kind, target=target, detail=detail))


def _unique(path: Path) -> Path:
    """A destination that does not exist yet, so a second run never overwrites."""
    if not path.exists():
        return path
    stem, suffix, index = path.stem, path.suffix, 2
    while True:
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def back_up(data_dir: Path, apply: bool) -> Path:
    """Copy the whole tree next to itself before anything moves.

    Named from the source folder rather than from the clock, because this script
    must not read the time: a run has to be reproducible, and a timestamp in a
    path is the kind of detail that makes two runs disagree.
    """
    destination = _unique(data_dir.parent / f"{data_dir.name}-before-time-migration")
    if apply:
        shutil.copytree(data_dir, destination)
    return destination


def migrate_working(audio_dir: Path, result: Result, apply: bool) -> None:
    """One ``data/audio/<uuid>/`` folder."""
    matrices = audio_dir / MATRICES_DIR
    name = audio_dir.name[:8]

    if not matrices.is_dir():
        result.add("skip", name, "no matrices folder; nothing was ever built for it")
        return

    has_events = (matrices / EVENTS_FILE).is_file()
    stale = sorted(
        {path for pattern in STALE_PATTERNS for path in matrices.glob(pattern) if path.is_file()}
    )

    if not has_events:
        if not stale:
            result.add("skip", name, "no recorded notes and nothing left over")
            return
        result.add(
            "flag",
            name,
            f"no {EVENTS_FILE}; marked as needing re-transcription, "
            f"{len(stale)} old file(s) left untouched",
        )
        if apply:
            (matrices / NEEDS_REDERIVATION_FILE).write_text(
                json.dumps({"schemaVersion": "1.0", "reason": NO_EVENTS_REASON}, indent=2) + "\n",
                encoding="utf-8",
            )
        return

    # It has its recorded notes, so it already works on the new path.
    if (matrices / NEEDS_REDERIVATION_FILE).is_file():
        result.add("unflag", name, "has recorded notes after all; the flag is removed")
        if apply:
            (matrices / NEEDS_REDERIVATION_FILE).unlink()

    if not stale:
        result.add("ok", name, "already carries only its recorded notes")
        return

    result.add("move", name, f"{len(stale)} old file(s) -> {REPLACED_DIR}/")
    if apply:
        destination = matrices / REPLACED_DIR
        destination.mkdir(parents=True, exist_ok=True)
        for path in stale:
            path.rename(_unique(destination / path.name))


def migrate_versions(root: Path, where: str, audio_root: Path, result: Result, apply: bool) -> None:
    """Saved versions under ``playground/`` or ``library/tracks/``."""
    if not root.is_dir():
        return
    for artist in sorted(p for p in root.iterdir() if p.is_dir()):
        for track in sorted(p for p in artist.iterdir() if p.is_dir()):
            for folder in sorted(p for p in track.iterdir() if p.is_dir()):
                metadata = folder / "metadata.json"
                if not metadata.is_file():
                    continue
                label = f"{where}:{artist.name}/{track.name}/{folder.name}"
                audio_uuid = _audio_uuid_of(metadata)
                rebuildable = bool(
                    audio_uuid and (audio_root / audio_uuid / MATRICES_DIR / EVENTS_FILE).is_file()
                )
                if rebuildable:
                    result.add(
                        "flag",
                        label,
                        "its source audio still has recorded notes, so it can be redrawn "
                        "from there; the saved grid itself is not carried over",
                    )
                else:
                    result.add("flag", label, "no way to rebuild it; marked")
                if apply:
                    (folder / NEEDS_REDERIVATION_FILE).write_text(
                        json.dumps({"schemaVersion": "1.0", "reason": BEAT_GRID_REASON}, indent=2)
                        + "\n",
                        encoding="utf-8",
                    )


def _audio_uuid_of(metadata: Path) -> str | None:
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    audio = payload.get("audio") or {}
    return audio.get("audioUuid") if isinstance(audio, dict) else None


def migrate(data_dir: Path, apply: bool) -> Result:
    result = Result()
    result.backup = str(back_up(data_dir, apply))

    audio_root = data_dir / "audio"
    if audio_root.is_dir():
        for child in sorted(p for p in audio_root.iterdir() if p.is_dir()):
            migrate_working(child, result, apply)

    migrate_versions(data_dir / "playground", "playground", audio_root, result, apply)
    migrate_versions(data_dir / "library" / "tracks", "library", audio_root, result, apply)
    return result


def report(result: Result, apply: bool) -> str:
    verb = "Done" if apply else "Would do"
    lines = [
        f"{'Migration' if apply else 'Dry run'} — nothing here is guesswork; "
        "each line says what it found.",
        "",
        f"Backup: {result.backup}{'' if apply else ' (not written on a dry run)'}",
        "",
    ]
    if not result.actions:
        lines.append("No stored artifacts found. Nothing to do.")
        return "\n".join(lines)

    width = max(len(action.kind) for action in result.actions)
    for action in result.actions:
        lines.append(f"  {action.kind.ljust(width)}  {action.target}  — {action.detail}")

    tally: dict[str, int] = {}
    for action in result.actions:
        tally[action.kind] = tally.get(action.kind, 0) + 1
    lines += [
        "",
        f"{verb}: " + ", ".join(f"{count} {kind}" for kind, count in sorted(tally.items())),
    ]
    if not apply:
        lines += ["", "Nothing was changed. Run again with --apply to do it."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="the data tree to migrate (default: this checkout's data/)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="actually move and write; off by default"
    )
    args = parser.parse_args(argv)

    if not args.data.is_dir():
        print(f"No data tree at {args.data}", file=sys.stderr)
        return 1

    print(report(migrate(args.data, args.apply), args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
