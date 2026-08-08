#!/usr/bin/env python
"""Every stored artifact, and whether the time-based migration can rebuild it.

Task P4.1 of the time-based concept refactor. Phase 4 deletes the granularity
from the storage layer, and once it is gone an artifact that cannot be rebuilt
from its raw events is unrecoverable. So this runs first, and it runs again
before P4.5 flips anything.

**It only reads.** Nothing here writes, moves or deletes a file.

Three families live under ``data/``, and they fail differently:

``data/audio/<uuid>/matrices/``
    The working artifact — what the Playground is holding. ``events.json`` is
    the transcription in seconds and every other file in the folder is a
    function of it, so the whole folder rebuilds at 40 ms from that one file.
    Unless the grid was hand-edited: ``raw-edited.flag`` means the cells say
    something the events do not, and rebuilding would throw that away in
    silence.

``data/playground/<artist>/<track>/v<N>_g<code>/``
    A saved version. Its ``.npz`` is a matrix on a **beat** grid at a stored
    BPM, which has no meaning under D-01, so it can only be rebuilt by going
    back to the audio it came from — and only if ``metadata.json`` records one
    and that audio still has its events. Its ``metadata.json`` also carries
    hand-written content (comment, key signature, annotations) that no
    re-derivation invents.

``data/library/tracks/<artist>/<track>/``
    Promoted copies of a saved version. Same story, one level on.

Run::

    uv run python scripts/inventory_artifacts.py            # markdown to stdout
    uv run python scripts/inventory_artifacts.py --json     # machine readable
    uv run python scripts/inventory_artifacts.py --data DIR # another tree
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# File names are spelled out here rather than imported from
# ``transcription.pipeline`` and ``schemas.naming`` on purpose: P4.2 and P4.4
# rewrite both of those modules, and this script has to keep reading the tree
# they wrote *before* the rewrite. A copy of six strings is cheaper than an
# inventory that stops working on the day it matters most.
MATRICES_DIR = "matrices"
EVENTS_FILE = "events.json"
RAW_FILE = "raw.npz"
RAW_GRANULARITY_FILE = "raw-granularity.txt"
RAW_EDITED_FLAG = "raw-edited.flag"
EDIT_PARENT_FILE = "raw_before_edit.npz"
NOTATION_FILE = "notation.json"
GRID_FILE = "grid-notation.json"
SCORE_FILE = "score.json"

VERSION_FOLDER_PATTERN = re.compile(r"^v(?P<version>\d+)_(?P<granularity>g[a-z]+)$")


# --------------------------------------------------------------- verdicts


#: What the migration can do with one artifact.
REDERIVABLE = "rederivable"
"""Raw events present and untouched: rebuild at 40 ms, byte for byte."""

HAND_EDITED = "hand-edited"
"""The grid diverges from the events. Flag ``needsRederivation``; never rebuild."""

NO_RAW_EVENTS = "no-raw-events"
"""Nothing to rebuild from. Re-transcribing gives different notes, not these."""

DERIVED_ONLY = "derived-only"
"""A saved matrix on a beat grid, rebuildable only through its source audio."""


@dataclass
class WorkingArtifact:
    """One ``data/audio/<uuid>/`` folder."""

    uuid: str
    alias: str | None
    duration_seconds: float | None
    verdict: str
    has_events: bool
    event_count: int | None
    has_raw: bool
    raw_granularity: str | None
    hand_edited: bool
    has_edit_parent: bool
    has_audio_original: bool
    derived_granularities: list[str] = field(default_factory=list)
    hand_maps: list[str] = field(default_factory=list)
    hand_written: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class SavedVersion:
    """One ``v<N>_g<code>/`` folder, in the playground or promoted."""

    where: str
    artist_slug: str
    track_slug: str
    folder: str
    verdict: str
    tempo_bpm: float | None
    granularity: str | None
    audio_uuid: str | None
    audio_has_events: bool
    parent_version: str | None
    matrices: list[str] = field(default_factory=list)
    hand_written: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Inventory:
    data_dir: str
    working: list[WorkingArtifact] = field(default_factory=list)
    versions: list[SavedVersion] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for item in (*self.working, *self.versions):
            tally[item.verdict] = tally.get(item.verdict, 0) + 1
        return tally


# ----------------------------------------------------------------- reading


def _read_json(path: Path) -> Any | None:
    """Parse a JSON file, or ``None`` when it is missing or malformed.

    Malformed is deliberately not fatal: an inventory that stops at the first
    bad file tells you least about the tree you were worried about.
    """
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _has_content(path: Path, keys: tuple[str, ...]) -> bool:
    """Does this sidecar hold anything a person put there?"""
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return False
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict) and any(value.values()):
            return True
        if isinstance(value, list) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return False


def inspect_working(audio_dir: Path) -> WorkingArtifact:
    """Classify one ``data/audio/<uuid>/`` folder."""
    matrices = audio_dir / MATRICES_DIR
    metadata = _read_json(audio_dir / "metadata.json") or {}
    events = _read_json(matrices / EVENTS_FILE)

    hand_edited = (matrices / RAW_EDITED_FLAG).is_file()
    has_events = isinstance(events, dict) and "events" in events
    has_raw = (matrices / RAW_FILE).is_file()

    if hand_edited:
        verdict = HAND_EDITED
    elif has_events:
        verdict = REDERIVABLE
    else:
        verdict = NO_RAW_EVENTS

    granularity_file = matrices / RAW_GRANULARITY_FILE
    raw_granularity = (
        granularity_file.read_text(encoding="utf-8").strip() if granularity_file.is_file() else None
    )

    derived = sorted(
        {path.stem.split("_", 1)[1] for path in matrices.glob("clean_*.npz") if "_" in path.stem}
    )
    hand_maps = sorted(path.name for path in matrices.glob("hands_*.json"))

    hand_written: list[str] = []
    if _has_content(matrices / NOTATION_FILE, ("settings", "annotations")):
        hand_written.append(NOTATION_FILE)
    if (matrices / GRID_FILE).is_file():
        hand_written.append(GRID_FILE)

    notes: list[str] = []
    if hand_edited:
        notes.append(
            "raw-edited.flag present: the grid was changed by hand and no longer "
            "matches events.json. Rebuilding would discard the edit."
        )
        if (matrices / EDIT_PARENT_FILE).is_file():
            notes.append(
                "raw_before_edit.npz holds the pre-edit grid, so the edit is "
                "recoverable as a diff even if the current grid is replaced."
            )
    if not has_events and has_raw:
        notes.append(
            "raw.npz with no events.json: transcribed before events were kept, "
            "or the file was lost. The grid is all there is."
        )
    if raw_granularity is None and has_raw:
        notes.append(
            "No raw-granularity.txt: the grid predates the sidecar and reads as "
            "fusa (LEGACY_RAW_GRANULARITY)."
        )

    original = sorted(audio_dir.glob("original.*"))

    return WorkingArtifact(
        uuid=audio_dir.name,
        alias=metadata.get("alias"),
        duration_seconds=metadata.get("durationSeconds"),
        verdict=verdict,
        has_events=has_events,
        event_count=len(events["events"]) if has_events else None,
        has_raw=has_raw,
        raw_granularity=raw_granularity,
        hand_edited=hand_edited,
        has_edit_parent=(matrices / EDIT_PARENT_FILE).is_file(),
        has_audio_original=bool(original),
        derived_granularities=derived,
        hand_maps=hand_maps,
        hand_written=hand_written,
        notes=notes,
    )


def inspect_version(
    where: str,
    artist_slug: str,
    track_slug: str,
    directory: Path,
    audio_root: Path,
) -> SavedVersion:
    """Classify one ``v<N>_g<code>/`` folder."""
    metadata = _read_json(directory / "metadata.json") or {}
    audio = metadata.get("audio") or {}
    audio_uuid = audio.get("audioUuid") if isinstance(audio, dict) else None

    audio_has_events = bool(
        audio_uuid and (audio_root / audio_uuid / MATRICES_DIR / EVENTS_FILE).is_file()
    )

    hand_written: list[str] = []
    annotations = metadata.get("annotations")
    if isinstance(annotations, dict) and any(annotations.values()):
        hand_written.append("metadata.json:annotations")
    if metadata.get("comment"):
        hand_written.append("metadata.json:comment")
    if metadata.get("keySignature"):
        hand_written.append("metadata.json:keySignature")
    if metadata.get("handAssignments"):
        hand_written.append("metadata.json:handAssignments")
    if _has_content(directory / NOTATION_FILE, ("settings", "annotations")):
        hand_written.append(NOTATION_FILE)
    if (directory / GRID_FILE).is_file():
        hand_written.append(GRID_FILE)

    notes: list[str] = []
    if audio_uuid and not audio_has_events:
        notes.append(
            f"references audio {audio_uuid}, which has no events.json — "
            "the saved grid cannot be rebuilt on a wall clock."
        )
    if not audio_uuid:
        notes.append(
            "no audio reference: nothing links this matrix back to a recording, "
            "so there is no wall clock to place it on."
        )
    parent = metadata.get("parentMatrix") or {}
    if parent:
        notes.append("derived from " + str(parent.get("versionFolder")) + " by a hand edit.")
    if (directory / SCORE_FILE).is_file():
        notes.append("score.json is a pre-generated 1.x score document; it is a cache.")

    return SavedVersion(
        where=where,
        artist_slug=artist_slug,
        track_slug=track_slug,
        folder=directory.name,
        verdict=REDERIVABLE if audio_has_events else DERIVED_ONLY,
        tempo_bpm=metadata.get("tempoBpm"),
        granularity=metadata.get("granularity"),
        audio_uuid=audio_uuid,
        audio_has_events=audio_has_events,
        parent_version=parent.get("versionFolder") if parent else None,
        matrices=sorted(path.name for path in directory.glob("*.npz")),
        hand_written=hand_written,
        notes=notes,
    )


def take_inventory(data_dir: Path) -> Inventory:
    """Walk the whole tree once."""
    inventory = Inventory(data_dir=str(data_dir))
    audio_root = data_dir / "audio"

    for child in (
        sorted(p for p in audio_root.iterdir() if p.is_dir()) if audio_root.is_dir() else []
    ):
        inventory.working.append(inspect_working(child))

    for root, where in (
        (data_dir / "playground", "playground"),
        (data_dir / "library" / "tracks", "library"),
    ):
        if not root.is_dir():
            continue
        for artist in sorted(p for p in root.iterdir() if p.is_dir()):
            for track in sorted(p for p in artist.iterdir() if p.is_dir()):
                folders = [
                    p
                    for p in sorted(track.iterdir())
                    if p.is_dir() and VERSION_FOLDER_PATTERN.match(p.name)
                ]
                for folder in folders:
                    inventory.versions.append(
                        inspect_version(where, artist.name, track.name, folder, audio_root)
                    )
                if where == "library":
                    # Promoted matrices live in the track folder itself, not in a
                    # version subfolder, so a bare .npz there is still an artifact.
                    loose = sorted(p.name for p in track.glob("*.npz"))
                    if loose:
                        inventory.versions.append(
                            SavedVersion(
                                where=where,
                                artist_slug=artist.name,
                                track_slug=track.name,
                                folder="(promoted, no version folder)",
                                verdict=DERIVED_ONLY,
                                tempo_bpm=None,
                                granularity=None,
                                audio_uuid=None,
                                audio_has_events=False,
                                parent_version=None,
                                matrices=loose,
                                notes=["promoted copy; its source version carries the metadata."],
                            )
                        )

    return inventory


# ---------------------------------------------------------------- reporting


def _yes(value: bool) -> str:
    return "yes" if value else "—"


def to_markdown(inventory: Inventory) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"Data tree: `{inventory.data_dir}`")
    add("")
    counts = inventory.counts
    if counts:
        add("| verdict | artifacts |")
        add("|---|---|")
        for verdict in (REDERIVABLE, HAND_EDITED, NO_RAW_EVENTS, DERIVED_ONLY):
            if verdict in counts:
                add(f"| `{verdict}` | {counts[verdict]} |")
    else:
        add("No artifacts found.")
    add("")

    add("## Working artifacts — `data/audio/<uuid>/`")
    add("")
    if not inventory.working:
        add("None.")
    else:
        add("| uuid | alias | verdict | events | notes on disk | audio | hand-written |")
        add("|---|---|---|---|---|---|---|")
        for item in inventory.working:
            events = f"{item.event_count}" if item.has_events else "—"
            derived = ", ".join(item.derived_granularities) or "—"
            add(
                f"| `{item.uuid[:8]}…` | {item.alias or '—'} | `{item.verdict}` | {events} "
                f"| {derived} | {_yes(item.has_audio_original)} "
                f"| {', '.join(item.hand_written) or '—'} |"
            )
        add("")
        for item in inventory.working:
            if item.notes:
                add(f"**`{item.uuid}`**")
                add("")
                for note in item.notes:
                    add(f"- {note}")
                add("")
    add("")

    add("## Saved versions — `data/playground/` and `data/library/tracks/`")
    add("")
    if not inventory.versions:
        add("None.")
    else:
        add(
            "| where | track | folder | verdict | bpm | granularity | source audio | hand-written |"
        )
        add("|---|---|---|---|---|---|---|---|")
        for item in inventory.versions:
            add(
                f"| {item.where} | {item.artist_slug}/{item.track_slug} | `{item.folder}` "
                f"| `{item.verdict}` | {item.tempo_bpm or '—'} | {item.granularity or '—'} "
                f"| {(item.audio_uuid or '—')} | {', '.join(item.hand_written) or '—'} |"
            )
        add("")
        for item in inventory.versions:
            if item.notes:
                add(f"**{item.artist_slug}/{item.track_slug}/{item.folder}**")
                add("")
                for note in item.notes:
                    add(f"- {note}")
                add("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="the data tree to inventory (default: this checkout's data/)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = parser.parse_args(argv)

    if not args.data.is_dir():
        print(f"No data tree at {args.data}", file=sys.stderr)
        return 1

    inventory = take_inventory(args.data)
    if args.json:
        print(json.dumps(asdict(inventory), indent=2))
    else:
        print(to_markdown(inventory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
