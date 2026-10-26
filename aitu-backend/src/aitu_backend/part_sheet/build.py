"""The new sheet of a part at any moment, and its drawing (implementation 03, Phase 5).

Three cases, in order (:func:`current`):

1. **Stored and current**: ``sheet.f1`` was written for the ``handsRevision`` that ``notes.pmn`` has now. It is drawn
   as it is.
2. **Stored, but the notes or the hands changed since** (a notes edit, a hand moved in the vexflow-v2 editor, a
   Sonnet run that ended after an edit): the stored decisions are laid again on the current notes
   (:func:`reapply`). The hand of a note is always the one of ``notes.pmn`` (plan section 3.7); a note that kept its
   hand and its column keeps its beam group, ornaments, 8va and the user's marks (Phase 7); the clefs and the
   armaduras stay. The rules (figures, grace notes, beam groups cut by the figures, spelling) run again. This holds
   for a sheet the AI wrote and for one the user edited (``Record.decided``); a plain stored algorithm sheet is
   computed again.
3. **Never written**: the algorithm (``propose_frames``) on the starting hands (the saved hands, the hand split for
   the rest). A part that has a ``sheet.json`` from vexflow-v2 keeps two of its decisions (the user's answer of
   Phase 5, "keep all the data"): the armadura (``keySignature``, ``keyChanges``) and, when the user renamed it with
   Transpose figures, the reference figure (``anchorMs`` and ``anchorFigure``; the negra of the highest pile of gaps
   was vexflow-v2's default, and the pulse estimate replaces it). The other marks are mapped in Phase 9.

The answers are cached by the modification times of the three files, so a page that draws the sheet again at
another width does not run the algorithm again.
"""

from __future__ import annotations

import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn import events_file
from aitu_backend.pmn.notes import Notes
from aitu_backend.schemas.time_matrix import FIGURE_NEGRAS, FigureName
from aitu_backend.sheet.engrave.frames import Options, render_frames
from aitu_backend.sheet.llm.frames import Part, assemble, windows_of
from aitu_backend.sheet.proposal.frames import (
    FramesProposal,
    _columns,
    clefs_and_ottavas,
    propose_frames,
)
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.common import spn
from aitu_backend.sheet.sheet.data import CLEF_NAMES, FRAME_MS, Sheet, carry_extras
from aitu_backend.sheet.sheet.frames import STAFF_OF, drawn_columns
from aitu_backend.sheet.sheet.pmn import KEYS
from aitu_backend.storage import locate, paths
from aitu_backend.transcription import pipeline

from . import store

__all__ = [
    "Drawn",
    "Reading",
    "algorithm",
    "current",
    "draw",
    "drawn_notes",
    "fit_clefs",
    "hands_of_sheet",
    "reading_of",
    "reading_summary",
    "reapply",
    "sheet_settings",
    "user_marks",
    "windows",
    "with_marks",
]

#: The staff width the page asks for, in staff spaces: its own width over the size it draws at.
MIN_WIDTH, MAX_WIDTH = 60.0, 320.0


@dataclass(frozen=True)
class Reading:
    """What a vexflow-v2 ``sheet.json`` decided that the new sheet keeps."""

    key: int | None = None
    key_changes: list[tuple[int, int]] | None = None
    quarter_ms: float | None = None


@dataclass
class Drawn:
    """The sheet of a part as the page draws it."""

    text: str
    #: ``llm``, ``mixed`` or ``algorithm`` (who decided the hands and the reading).
    source: str
    #: The segments of the piece-by-piece view, ``(first frame, end frame, "llm" | "algorithm")``; empty for a sheet
    #: Sonnet never wrote.
    windows: list[tuple[int, int, str]] = field(default_factory=list)
    #: Stored for older notes or hands, and laid again on the current ones.
    stale: bool = False
    quarter_ms: float | None = None
    record: store.Record | None = None


def reading_of(part_id: str) -> Reading:
    rhythm = pipeline.load_rhythm(part_id)
    if rhythm is None:
        return Reading()
    key = KEYS.get(rhythm.key_signature or "C")
    changes = [
        (int(round(change.from_column * rhythm.frame_ms / FRAME_MS)), KEYS[change.key_signature])
        for change in rhythm.key_changes
        if change.key_signature in KEYS
    ]
    # The pile of gaps named a negra was vexflow-v2's default (D-09), not a choice: the pulse estimate decides then.
    # Another name (Transpose figures) is the user's override, and it stays (rule 5).
    negras = FIGURE_NEGRAS.get(rhythm.anchor_figure)
    named = rhythm.anchor_figure != FigureName.NEGRA or rhythm.figures_from is not None
    quarter = rhythm.anchor_ms / negras if negras and named else None
    return Reading(key=key, key_changes=changes or None, quarter_ms=quarter)


def algorithm(
    part_id: str,
    notes: Notes | None = None,
    *,
    quarter_ms: float | None = None,
    key: int | None = None,
) -> FramesProposal:
    """The algorithm's sheet of a part, with the decisions an old ``sheet.json`` keeps; ``key`` (fifths) is an
    armadura chosen elsewhere (the song's, on a passage of it: Record in Sheet)."""
    notes = pipeline.starting_hands(part_id) if notes is None else notes
    reading = reading_of(part_id)
    return propose_frames(
        notes,
        key=key if key is not None else reading.key,
        key_changes=None if key is not None else reading.key_changes,
        quarter_ms=quarter_ms if quarter_ms is not None else reading.quarter_ms,
    )


def windows(sheet: Sheet) -> list[tuple[int, int]]:
    """The segments of a sheet (the LLM's windows): known before any request."""
    return windows_of(sheet) if sheet.notes else []


def _clef_track(sheet: Sheet, staff: int, frames: list[int]) -> list[str]:
    """The clef of ``staff`` in force at each of ``frames`` (sorted)."""
    changes = sorted((f, c) for f, st, c in sheet.clef_changes if st == staff)
    clef, k, out = sheet.clefs.get(staff, "G2" if staff == 1 else "F4"), 0, []
    for frame in frames:
        while k < len(changes) and changes[k][0] <= frame:
            clef, k = changes[k][1], k + 1
        out.append(clef)
    return out


def fit_clefs(sheet: Sheet, changed: set[tuple[int, int, int]]) -> int:
    """Clefs and 8va where notes changed hand (Phase 6). ``changed`` holds the notes, ``(frame, midi, staff)``, that
    are on another staff than in the stored sheet (or new to it). Around each one, the clefs and 8va of the
    algorithm's rule (``clefs_and_ottavas``, the clef rules version 4: the bass clef, then the treble clef, then the
    treble clef with 8va for the left hand, never 8va in the bass clef, no note four ledger lines or more above the
    bass staff) replace the stored ones, on the stretch of that staff where the two differ; everywhere else the
    stored clefs and 8va stay (the AI's, or the user's). A high note moved to the left hand gets a treble clef for
    its stretch rather than five ledger lines. Returns the number of stretches changed.
    """
    if not changed:
        return 0
    # The rule changes only the clefs and the 8va: a copy of the notes is enough (a third of a deep copy's time).
    rule = replace(
        sheet,
        notes=[replace(n) for n in sheet.notes],
        clefs=dict(sheet.clefs),
        clef_changes=list(sheet.clef_changes),
    )
    clefs_and_ottavas(rule)
    done = 0
    for staff in (1, 2):
        cols = [(f, ns) for f, ns in _columns(sheet, staff)]
        if not cols or not any(k[2] == staff for k in changed):
            continue
        frames = [f for f, _ in cols]
        ruled_notes = dict(_columns(rule, staff))
        stored = list(
            zip(_clef_track(sheet, staff, frames), (max(n.ottava for n in ns) for _, ns in cols))
        )
        ruled = list(
            zip(
                _clef_track(rule, staff, frames),
                (max(n.ottava for n in ruled_notes[f]) for f in frames),
            )
        )
        regions: list[tuple[int, int]] = []
        for i, (f, ns) in enumerate(cols):
            if stored[i] == ruled[i] or not any((f, n.midi, staff) in changed for n in ns):
                continue
            if regions and regions[-1][1] >= i:
                continue
            a = i
            while a > 0 and stored[a - 1] != ruled[a - 1]:
                a -= 1
            b = i
            while b + 1 < len(cols) and stored[b + 1] != ruled[b + 1]:
                b += 1
            regions.append((a, b))
        for a, b in regions:
            first = frames[a]
            end = frames[b + 1] if b + 1 < len(frames) else None
            for k in range(a, b + 1):
                by_midi = {(n.midi, n.grace): n.ottava for n in ruled_notes[frames[k]]}
                for n in cols[k][1]:
                    n.ottava = by_midi.get((n.midi, n.grace), ruled[k][1])
            inside = [
                c
                for c in sheet.clef_changes
                if c[1] == staff and c[0] >= first and (end is None or c[0] < end)
            ]
            for c in inside:
                sheet.clef_changes.remove(c)
            before = stored[a - 1][0] if a > 0 else None
            if a == 0:
                sheet.clefs[staff] = ruled[a][0]
            elif ruled[a][0] != before:
                sheet.clef_changes.append((first, staff, ruled[a][0]))
            for c in rule.clef_changes:
                if c[1] == staff and first < c[0] and (end is None or c[0] < end):
                    sheet.clef_changes.append(c)
            if end is not None and ruled[b][0] != stored[b + 1][0]:
                if not any(c[1] == staff and c[0] == end for c in sheet.clef_changes):
                    sheet.clef_changes.append((end, staff, stored[b + 1][0]))
            done += 1
        # Ornament onsets take the 8va of the note before them, as the rule does.
        last = 0
        for n in sorted((n for n in sheet.notes if n.staff == staff), key=lambda n: n.frame):
            if n.covered:
                n.ottava = last
            else:
                last = n.ottava
    sheet.clef_changes.sort(key=lambda c: (c[0], c[1]))
    return done


def reapply(stored: Sheet, notes: Notes) -> Sheet:
    """The decisions of a stored sheet laid on the current notes and their hands (the case 2 of the module). A note
    on another staff than in the stored sheet, or new to it, gets the clefs and 8va of the rule around it
    (:func:`fit_clefs`)."""
    algo = propose_frames(
        notes,
        key=stored.key or 0,
        key_changes=list(stored.key_changes),
        quarter_ms=stored.quarter_ms,
    )
    same = {(n.frame, n.midi, n.staff): n for n in stored.notes}
    near = {(n.frame, n.midi): n for n in stored.notes}
    here = {(n.frame, n.midi, n.staff) for n in algo.sheet.notes}
    decided = {}
    changed: set[tuple[int, int, int]] = set()
    for i, n in enumerate(algo.sheet.notes):
        kept = same.get((n.frame, n.midi, n.staff))
        if kept is None:
            # A note whose drawn column moved by a frame or two: the first note of its chord, played a little
            # before it, was taken off (Phase 7), so the chord's column is now this note's own onset.
            for d in (-1, -2, 1, 2):
                place = (n.frame + d, n.midi, n.staff)
                if place in same and place not in here:
                    kept = same[place]
                    break
        if kept is not None:
            decided[i] = kept
        else:
            changed.add((n.frame, n.midi, n.staff))
            # Another hand now, or a note the stored sheet did not have: no beam group of its own.
            decided[i] = replace(near.get((n.frame, n.midi), n), staff=n.staff, beam=None)
    frames = [n.frame for n in algo.sheet.notes]
    part = Part(
        start=min(frames, default=0),
        end=max(frames, default=0) + 1,
        source="llm",
        notes=decided,
        clefs=dict(stored.clefs),
        key=stored.key or 0,
        clef_changes=list(stored.clef_changes),
        key_changes=list(stored.key_changes),
    )
    sheet, _ = assemble(algo, [part], join=False)
    fit_clefs(sheet, changed)
    # What the user wrote about the whole sheet (Phase 8: titles, lyrics, the spacing's figure, the line space).
    return carry_extras(stored, sheet)


def user_marks(sheet: Sheet) -> dict[tuple[int, int], Any]:
    """The notes of a sheet that carry a mark only the user writes (Phase 7: a finger, a figure set by hand, the
    grace note switch), by ``(frame, midi)``. A new AI run keeps them (the user's answer of Phase 7).
    """
    return {(n.frame, n.midi): n for n in sheet.notes if n.finger or n.fixed or n.grace_rule}


def with_marks(parts: list[Part], marks: dict[tuple[int, int], Any]) -> list[Part]:
    """The decisions of ``parts`` with the user's marks put back on their notes: ``assemble`` keeps them."""
    if not marks:
        return parts
    out = []
    for p in parts:
        notes = {}
        for i, d in p.notes.items():
            m = marks.get((d.frame, d.midi))
            notes[i] = (
                d
                if m is None
                else replace(
                    d,
                    finger=m.finger,
                    fixed=m.fixed,
                    figure=m.figure if m.fixed else d.figure,
                    grace_rule=m.grace_rule,
                )
            )
        out.append(replace(p, notes=notes))
    return out


def hands_of_sheet(sheet: Sheet, notes: Notes) -> dict[int, str]:
    """The hand of each live note in a frames sheet, by note id: its staff at its drawn column. Two notes of one key
    and column are one note of the sheet; a note the sheet does not hold is left out (it keeps its hand).
    """
    live = notes.live()
    if len(live) == 0:
        return {}
    _, start = drawn_columns(live.on_ms)
    column = np.floor(np.round(start / FRAME_MS, 9) + 0.5).astype(np.int64)
    at: dict[tuple[int, int], set[int]] = defaultdict(set)
    for n in sheet.notes:
        if n.staff in (1, 2):
            at[(n.frame, n.midi)].add(n.staff)
    out: dict[int, str] = {}
    for i in range(len(live)):
        staffs = at.get((int(column[i]), int(live.key[i]) + LOWEST_MIDI))
        if not staffs:
            continue
        now = STAFF_OF.get(int(live.hand[i]))
        staff = now if now in staffs else min(staffs)
        out[int(live.id[i])] = "right" if staff == 1 else "left"
    return out


# ------------------------------------------------------------------ the sheet now

_cache: OrderedDict[str, tuple[tuple[int, int, int], Drawn]] = OrderedDict()
_cache_lock = threading.Lock()
CACHE_SIZE = 24


def _mtime(path_of: Any, part_id: str) -> int:
    try:
        path = path_of(part_id)
        return path.stat().st_mtime_ns if path.is_file() else 0
    except (locate.NotFound, OSError):
        return 0


def _stamp(part_id: str) -> tuple[int, int, int]:
    return (
        _mtime(paths.part_notes_path, part_id),
        _mtime(paths.part_sheet_path, part_id),
        _mtime(paths.part_frames_path, part_id),
    )


def current(part_id: str) -> Drawn:
    """The sheet of a part as it is stored now (no running job). Raises ``FileNotFoundError`` without notes."""
    stamp = _stamp(part_id)
    with _cache_lock:
        hit = _cache.get(part_id)
        if hit is not None and hit[0] == stamp:
            _cache.move_to_end(part_id)
            return hit[1]
    drawn = _compute(part_id)
    with _cache_lock:
        _cache[part_id] = (stamp, drawn)
        _cache.move_to_end(part_id)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return drawn


def _compute(part_id: str) -> Drawn:
    header = events_file.read_header(paths.part_notes_path(part_id))
    stored = store.load(part_id)
    if stored is not None:
        record = stored.record
        segments = [(int(a), int(b), str(s)) for a, b, s in record.windows]
        if record.hands_revision is not None and record.hands_revision == header.hands_revision:
            sheet = f1.read(stored.text)
            return Drawn(
                stored.text,
                record.source,
                segments,
                False,
                sheet.quarter_ms or record.quarter_ms,
                record,
            )
        if record.decided:
            sheet = reapply(f1.read(stored.text), pipeline.starting_hands(part_id))
            return Drawn(
                f1.write(sheet, mode="frames"),
                record.source,
                segments,
                True,
                sheet.quarter_ms,
                record,
            )
        algo = algorithm(part_id, quarter_ms=record.quarter_ms, key=record.key)
        return Drawn(
            f1.write(algo.sheet, mode="frames"), "algorithm", [], True, algo.quarter_ms, record
        )
    algo = algorithm(part_id)
    return Drawn(f1.write(algo.sheet, mode="frames"), "algorithm", [], False, algo.quarter_ms, None)


def forget(part_id: str) -> None:
    with _cache_lock:
        _cache.pop(part_id, None)


def drawn_notes(sheet: Sheet) -> list[dict[str, Any]]:
    """Each drawn note as its notehead names it (``ref`` = ``"<frame>:<midi>"``, the ``data-note`` of the SVG), with
    its hand and the name the sheet prints (the sounding pitch, spelled: ``C#5``), for the note toolbox (Phase 6);
    and what the toolbox of Phase 7 shows pressed: the figure (``4`` a negra), the beam group (a number unique in
    the sheet, or ``null``), a grace note, the user's marks (a figure set by hand, the grace note switch, the
    finger), the ornaments and the 8va (``1`` 8va, ``2`` 15ma, ``-1`` 8vb, ``-2`` 15mb).
    """
    return [
        {
            "ref": f"{n.frame}:{n.midi}",
            "hand": "right" if n.staff == 1 else "left",
            "pitch": spn(n.step, n.alter, n.octave),
            "figure": n.figure,
            "beam": n.beam,
            "grace": n.grace is not None,
            "fixed": n.fixed,
            "graceRule": n.grace_rule,
            "finger": n.finger,
            "ornaments": list(n.ornaments),
            "ottava": n.ottava,
        }
        for n in sheet.notes
        if n.frame is not None and not n.covered and n.staff in (1, 2)
    ]


HAND_NAMES = {1: "right", 2: "left"}


def reading_summary(sheet: Sheet) -> dict[str, Any]:
    """The armaduras and clefs of a sheet, for the range toolbox (Phase 7): the armadura of the piece (fifths:
    ``3`` is three sostenidos, ``-2`` two bemoles) and where it changes, the clef each hand starts with and where it
    changes (``treble`` or ``bass``)."""
    return {
        "key": sheet.key or 0,
        "keyChanges": [[f, k] for f, k in sorted(sheet.key_changes)],
        "clefs": {
            HAND_NAMES[st]: CLEF_NAMES.get(c, c)
            for st, c in sheet.clefs.items()
            if st in HAND_NAMES
        },
        "clefChanges": [
            [f, HAND_NAMES[st], CLEF_NAMES.get(c, c)]
            for f, st, c in sorted(sheet.clef_changes, key=lambda c: (c[0], c[1]))
            if st in HAND_NAMES
        ],
    }


def draw(text: str, width: float) -> dict[str, Any]:
    """The drawing of a frames text for a page ``width`` staff spaces wide (the staff width; the SVG adds its
    margins): the SVG with ``data-note`` ids, the columns (system, frame, x, ms), the system boxes and the drawn
    notes (:func:`drawn_notes`).
    """
    width = min(MAX_WIDTH, max(MIN_WIDTH, float(width)))
    sheet = f1.read(text)
    notes = drawn_notes(sheet)
    rendered = render_frames(sheet, Options(width=width))
    return {
        "svg": rendered.svg,
        "columns": rendered.columns,
        "systems": rendered.systems,
        "width": rendered.width,
        "height": rendered.height,
        "notes": notes,
        "reading": reading_summary(sheet),
        **sheet_settings(sheet),
        "timings": {k: round(v, 1) for k, v in rendered.timings.items()},
    }


def sheet_settings(sheet: Sheet) -> dict[str, Any]:
    """What the user wrote about the whole sheet (Phase 8), for the sheet toolbox: the title lines, the lyrics pieces
    in the order of the drawing's ``data-lyric`` (by start), the reference figure and the one of the spacing, the
    space between lines (``None``: the engine's own)."""
    return {
        "titles": dict(sheet.titles),
        "lyrics": [
            {
                "start": one.start,
                "end": one.end,
                "text": one.text,
                "size": one.size,
                "lift": one.lift,
                "at": one.at,
                "dx": one.dx,
                "dy": one.dy,
                "width": one.width,
                "font": one.font,
                "bold": one.bold,
                "italic": one.italic,
            }
            for one in sorted(sheet.lyrics, key=lambda one: (one.start, one.end))
        ],
        "quarterMs": sheet.quarter_ms,
        "spaceMs": sheet.space_ms,
        "lineSpace": sheet.line_space,
    }
