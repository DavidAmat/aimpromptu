"""From other projects, and the parts of a project (implementation 02, plan sections 8.4, 10.4 and
14.1, Phase 10).

**From other projects** makes one project of passages of other projects. Each passage is a part the
user may read and a stretch of it (or the whole of it); from the second on, each says how it joins
the one before: **sequential** (it follows in the same part, one piano matrix) or **subheader** (it
starts a new part, with a title above it). Every passage is put in by the paste of Phase 8
(:func:`aitu_backend.editing.paste.paste`) at the end of its part, so it brings its notes, its marks
(with the key, the clefs and the speed it had) and ranges of the stored audio files: a copy, never a
reference, and no audio byte copied (plan P-3). The project is a ``song`` or an
``integratedPlaylist``; the two differ only in how they are offered later (Play mode).

**The parts of a project** can then be renamed (the subheader), put in another order, joined (a part
put at the end of the one before it, again by a paste) and split (the stretch from a frame to the
end pasted into a new part after it, then cut out of the first, :func:`paste.cut`). The id of the
project is always one of its parts, because the routes of the steps take it: a join keeps that part.

A part's length changes only through :mod:`aitu_backend.editing.paste` (the rule of
``editing-and-compose.md`` section 5).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Literal

from aitu_backend.editing import paste
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.storage import bundle, locate, paths
from aitu_backend.transcription import pipeline

__all__ = [
    "Chosen",
    "Join",
    "PartFacts",
    "PartsError",
    "assemble",
    "facts",
    "join",
    "rename",
    "split",
]

Join = Literal["sequential", "subheader"]
Kind = Literal["song", "integratedPlaylist"]
#: The longest subheader, as the title of a project.
SUBHEADER_LIMIT = 300


class PartsError(ValueError):
    """A change of parts that cannot be done, in words the page shows."""


@dataclass(frozen=True)
class Chosen:
    """One passage chosen on the page of From other projects."""

    part: str
    #: The stretch, in ms of the part; ``None`` for the whole of it.
    from_ms: float | None = None
    to_ms: float | None = None
    #: How it joins the passage before it (ignored for the first).
    join: Join = "sequential"
    #: The title of the new part a ``subheader`` join starts; the source's title when empty.
    subheader: str | None = None


@dataclass(frozen=True)
class PartFacts:
    id: str
    subheader: str | None
    duration_ms: float


def _title_of(part_id: str) -> str:
    project = bundle.read_project(locate.part(part_id).project_id)
    entry = project.part(part_id)
    if len(project.parts) > 1 and entry.subheader:
        return entry.subheader
    return project.title or "Untitled project"


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = " ".join(text.split())[:SUBHEADER_LIMIT]
    return cleaned or None


def _stretch(chosen: Chosen) -> tuple[float, float]:
    if chosen.from_ms is not None and chosen.to_ms is not None:
        if chosen.to_ms <= chosen.from_ms:
            raise PartsError("A passage needs a stretch longer than nothing.")
        return chosen.from_ms, chosen.to_ms
    length = paste.whole_ms(chosen.part)
    if length <= 0:
        raise PartsError(f"“{_title_of(chosen.part)}” has nothing in it yet.")
    return 0.0, length


def _end_ms(part_id: str) -> float:
    """Where the next passage of a part goes: after its last column."""
    return paste.whole_ms(part_id)


def _forget_history(project_id: str) -> None:
    """A project just made starts with no earlier states, as a duplicate does: the snapshots its
    pastes kept are of an empty part."""
    shutil.rmtree(paths.history_dir() / project_id, ignore_errors=True)
    bundle.sync_audio_refs(project_id)


def _put_in(part_id: str, chosen: Chosen) -> None:
    from_ms, to_ms = _stretch(chosen)
    passage = paste.read_passage(chosen.part, from_ms, to_ms)
    paste.paste(part_id, passage, at_ms=_end_ms(part_id))


def assemble(
    *,
    owner_id: int,
    title: str,
    kind: Kind,
    passages: list[Chosen],
) -> bundle.ProjectFile:
    """A new project of the Personal Vault made of ``passages`` (section 10.4): one part per run
    of sequential passages, a new part at each ``subheader`` join. The caller checks the user may
    read every source. Nothing is left behind when a passage cannot be put in."""
    if not passages:
        raise PartsError("Add a passage first.")
    groups: list[list[Chosen]] = []
    for index, chosen in enumerate(passages):
        if index == 0 or chosen.join == "subheader":
            groups.append([chosen])
        else:
            groups[-1].append(chosen)
    project = bundle.create_project(
        owner_id=owner_id,
        title=title.strip(),
        kind=kind,
        source=bundle.PartSource(kind="composed", format="wav"),
        frame_ms=DEFAULT_FRAME_MS,
    )
    try:
        part_ids = [project.parts[0].id]
        for _ in groups[1:]:
            part_ids.append(bundle.add_part(project.id))
        several = len(groups) > 1
        with bundle.project_lock(project.id):
            written = bundle.read_project(project.id)
            for entry, group in zip(written.parts, groups):
                first = group[0]
                entry.subheader = (
                    (_clean(first.subheader) or _title_of(first.part)) if several else None
                )
            written.origin = {
                "composedFrom": [
                    {
                        "part": one.part,
                        "fromMs": one.from_ms,
                        "toMs": one.to_ms,
                        "join": "subheader" if index and one.join == "subheader" else "sequential",
                    }
                    for index, one in enumerate(passages)
                ]
            }
            bundle.write_project(written)
        for part_id, group in zip(part_ids, groups):
            pipeline.save_note_events(part_id, [], 0.0, project.title)
            for chosen in group:
                _put_in(part_id, chosen)
        _forget_history(project.id)
    except Exception:
        bundle.delete_project(project.id)
        raise
    return bundle.read_project(project.id)


def facts(project_id: str) -> list[PartFacts]:
    """The parts of a project in order, each with its subheader and its length."""
    project = bundle.read_project(project_id)
    return [
        PartFacts(
            id=entry.id, subheader=entry.subheader, duration_ms=paste.part_length_ms(entry.id)
        )
        for entry in project.parts
    ]


def rename(project_id: str, part_id: str, subheader: str | None) -> None:
    with bundle.project_lock(project_id):
        project = bundle.read_project(project_id)
        project.part(part_id).subheader = _clean(subheader)
        bundle.write_project(project)


def join(project_id: str, part_id: str) -> str:
    """The part joined to the one before it, sequentially: one part, the music of the first then
    of the second. Returns the id of the part that holds both (the project's id when it is one of
    the two). The other part is removed."""
    project = bundle.read_project(project_id)
    ids = [entry.id for entry in project.parts]
    if part_id not in ids:
        raise locate.NotFound("part", part_id)
    index = ids.index(part_id)
    if index == 0:
        raise PartsError("The first part has no part before it to join.")
    upper, lower = ids[index - 1], ids[index]
    for one in (upper, lower):
        if pipeline.load_note_events(one) is None and bundle.read_timeline(one).source_list():
            raise PartsError("Transcribe both parts first: their notes are not there yet.")
    if lower == project_id:
        # The part that carries the project's id stays: the one before goes in at its start.
        keep, gone = lower, upper
        length = paste.whole_ms(upper)
        if length > 0:
            paste.paste(keep, paste.read_passage(upper, 0.0, length), at_ms=0.0)
        subheader = project.part(upper).subheader
    else:
        keep, gone = upper, lower
        length = paste.whole_ms(lower)
        if length > 0:
            paste.paste(keep, paste.read_passage(lower, 0.0, length), at_ms=_end_ms(keep))
        subheader = project.part(upper).subheader
    bundle.remove_part(project_id, gone)
    rename(project_id, keep, subheader)
    return keep


def split(
    project_id: str,
    part_id: str,
    at_ms: float,
    *,
    subheader: str | None = None,
    sheet: SavedRhythm | None = None,
) -> str:
    """The part split at ``at_ms``: what follows becomes a new part right after it, with
    ``subheader`` as its title. ``sheet`` is the part's sheet as the page holds it (saved by the
    split). Returns the id of the new part."""
    project = bundle.read_project(project_id)
    ids = [entry.id for entry in project.parts]
    if part_id not in ids:
        raise locate.NotFound("part", part_id)
    if pipeline.load_note_events(part_id) is None:
        raise PartsError("Transcribe this part first: its notes are not there yet.")
    length = paste.whole_ms(part_id)
    frame_ms = paste.sheet_frame_ms_of(part_id)
    at = round(at_ms / frame_ms) * frame_ms
    if at <= 0 or at >= length - frame_ms / 2:
        raise PartsError("Place the cursor inside the part to split it there.")
    new_part = bundle.add_part(
        project_id, position=ids.index(part_id) + 1, subheader=_clean(subheader)
    )
    try:
        pipeline.save_note_events(new_part, [], 0.0, project.title)
        paste.paste(new_part, paste.read_passage(part_id, at, length, sheet=sheet), at_ms=0.0)
        paste.cut(part_id, at, length, sheet=sheet)
    except Exception:
        bundle.remove_part(project_id, new_part)
        raise
    return new_part
