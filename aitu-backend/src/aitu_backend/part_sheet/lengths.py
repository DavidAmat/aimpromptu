"""``sheet.f1`` through a change of a part's length (implementation 03, Phase 8B): the new sheet's version of
:mod:`aitu_backend.editing.marks`.

A paste, a promotion of Record in Sheet, a split, a join, a passage of From other projects and a comment's excerpt
change the length of a part, and all of them go through :mod:`aitu_backend.editing.paste`. Before this module none
of them touched ``sheet.f1``: the stored sheet was laid again on the moved notes by column and key
(``build.reapply``), so every decision after the change was lost, and its clef and armadura changes stayed at the old
frames. These are the old sheet's four moves on a frames sheet (frames of 40 ms), each on a copy:

* :func:`shift`: everything at or after a frame moves later (a passage put in). A beam group across that frame is
  cut there, and a lyrics piece across it ends there (its words are not printed twice);
* :func:`cut_out`: a stretch is taken out and everything after it moves earlier; the armadura and the clefs in force
  after it are kept from where it was, so the music after it reads as before;
* :func:`extract`: the notes, changes and lyrics of a stretch, counted from its first frame, as a sheet of their own
  that starts with the armadura and the clefs in force there;
* :func:`put_in`: such a passage put into a sheet at a frame, with its own armadura and clefs from there and the
  sheet's own again after it.

The segments and stretches of the record (``store.Record.windows``, ``stretches``) move with
:func:`shift_spans`, :func:`cut_spans` and :func:`clip_spans`.

:func:`read` and :func:`store_after` are what the paste calls: the sheet of a copied stretch as its part draws it,
and the target's sheet after the change, stored for the new notes when it holds decisions (the AI's or the user's:
``store.Record.decided``, on either side). A sheet of the algorithm on both sides is not stored: it is computed again
from the notes, as before.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from aitu_backend.pmn import events_file
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet, collapse_clefs
from aitu_backend.storage import locate, paths
from aitu_backend.transcription import pipeline

from . import build, store

__all__ = [
    "Copied",
    "clef_at",
    "clip_spans",
    "cut_out",
    "cut_spans",
    "extract",
    "key_at",
    "put_in",
    "read",
    "scaled",
    "shift",
    "shift_spans",
    "keep_figure",
    "song_reading",
    "store_after",
    "target",
]

#: The clef each staff reads when nothing says otherwise.
OWN_CLEF = {1: "G2", 2: "F4"}


def _copy(sheet: Sheet, notes: list[Note]) -> Sheet:
    return replace(
        sheet,
        notes=notes,
        clefs=dict(sheet.clefs),
        clef_changes=list(sheet.clef_changes),
        key_changes=list(sheet.key_changes),
        titles=dict(sheet.titles),
        lyrics=[replace(one) for one in sheet.lyrics],
    )


def key_at(sheet: Sheet, frame: int) -> int:
    key = sheet.key or 0
    for f, k in sorted(sheet.key_changes):
        if f <= frame:
            key = k
    return key


def clef_at(sheet: Sheet, staff: int, frame: int) -> str:
    clef = sheet.clefs.get(staff, OWN_CLEF[staff])
    for f, st, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if st == staff and f <= frame:
            clef = c
    return clef


def _split_beams(notes: list[Note], edge: int) -> None:
    """A beam group with notes on both sides of ``edge`` becomes two: the notes from ``edge`` on take a new number."""
    sides: dict[int, set[bool]] = {}
    for n in notes:
        if n.beam is not None:
            sides.setdefault(n.beam, set()).add(n.frame >= edge)
    torn = [b for b, s in sides.items() if len(s) == 2]
    top = max(sides, default=0)
    for k, b in enumerate(torn, start=1):
        for n in notes:
            if n.beam == b and n.frame >= edge:
                n.beam = top + k


def _no_lone_beams(notes: list[Note]) -> None:
    """A beam group of one note (the rest of it cut away) is no group."""
    count: dict[int, set[int]] = {}
    for n in notes:
        if n.beam is not None and not n.grace:
            count.setdefault(n.beam, set()).add(n.frame)
    for n in notes:
        if n.beam is not None and len(count.get(n.beam, ())) < 2:
            n.beam = None


def _uncover(notes: list[Note], edge: int) -> None:
    """Onsets played inside an ornament whose note is now on the other side of ``edge`` (or gone) are drawn again:
    in each hand, the covered notes from ``edge`` up to the first note there that is not covered."""
    for staff in (1, 2):
        after = sorted(
            (n for n in notes if n.staff == staff and n.frame >= edge), key=lambda n: n.frame
        )
        for n in after:
            if not n.covered:
                break
            n.covered = False


def _tidy(sheet: Sheet) -> Sheet:
    """One armadura and one clef per staff at a frame, and no change to what is already in force."""
    sheet.clef_changes = collapse_clefs(
        sheet.clef_changes, {st: sheet.clefs.get(st, OWN_CLEF[st]) for st in (1, 2)}
    )
    keys: dict[int, int] = {}
    for f, k in sheet.key_changes:
        keys[f] = k
    out, now = [], sheet.key or 0
    for f in sorted(keys):
        if keys[f] != now:
            out.append((f, keys[f]))
            now = keys[f]
    sheet.key_changes = out
    sheet.notes.sort(key=lambda n: (n.frame, n.staff, 0 if n.grace else 1, n.gslot, n.midi))
    return sheet


def _first_frame(sheet: Sheet) -> int | None:
    return min((n.frame for n in sheet.notes if n.frame is not None), default=None)


def shift(sheet: Sheet, at: int, by: int) -> Sheet:
    """Everything at or after frame ``at`` moves ``by`` frames later."""
    if by <= 0:
        return _copy(sheet, [replace(n) for n in sheet.notes])
    notes = [replace(n, frame=n.frame + by) if n.frame >= at else replace(n) for n in sheet.notes]
    _split_beams(notes, at + by)
    _uncover(notes, at + by)
    _no_lone_beams(notes)
    out = _copy(sheet, notes)
    out.key_changes = [(f + by if f >= at else f, k) for f, k in sheet.key_changes]
    out.clef_changes = [(f + by if f >= at else f, st, c) for f, st, c in sheet.clef_changes]
    lyrics = []
    for one in out.lyrics:
        if one.start >= at:
            one = replace(one, start=one.start + by, end=one.end + by)
        elif one.end > at:
            one = replace(one, end=at)
        if one.at is not None and one.at >= at:
            one = replace(one, at=one.at + by)
        lyrics.append(one)
    out.lyrics = lyrics
    return _tidy(out)


def cut_out(sheet: Sheet, start: int, stop: int, *, tail: bool = False) -> Sheet:
    """Frames ``[start, stop)`` taken out: their notes, changes and lyrics go, a lyrics piece that reaches into them
    is shortened, and everything after them moves ``stop - start`` frames earlier. Unless the stretch runs to the
    end (``tail``), the armadura and the clefs in force at ``stop`` are in force from ``start``."""
    length = stop - start
    if length <= 0:
        return _copy(sheet, [replace(n) for n in sheet.notes])
    key_after = key_at(sheet, stop)
    clefs_after = {st: clef_at(sheet, st, stop) for st in (1, 2)}
    notes = [
        replace(n, frame=n.frame - length) if n.frame >= stop else replace(n)
        for n in sheet.notes
        if not start <= n.frame < stop
    ]
    _split_beams(notes, start)
    _uncover(notes, start)
    _no_lone_beams(notes)
    out = _copy(sheet, notes)
    out.key_changes = [
        (f - length if f >= stop else f, k) for f, k in sheet.key_changes if not start <= f < stop
    ]
    out.clef_changes = [
        (f - length if f >= stop else f, st, c)
        for f, st, c in sheet.clef_changes
        if not start <= f < stop
    ]
    if not tail:
        first = _first_frame(out)
        header = first is None or start <= first
        if key_at(out, start) != key_after:
            if header:
                out.key_changes = [(f, k) for f, k in out.key_changes if f > start]
                out.key = key_after
            else:
                out.key_changes.append((start, key_after))
        for st, clef in clefs_after.items():
            if clef_at(out, st, start) != clef:
                if header:
                    out.clef_changes = [
                        c for c in out.clef_changes if not (c[1] == st and c[0] <= start)
                    ]
                    out.clefs[st] = clef
                else:
                    out.clef_changes.append((start, st, clef))
    lyrics = []
    for one in out.lyrics:
        a = one.start if one.start < start else (start if one.start < stop else one.start - length)
        b = one.end if one.end <= start else (start if one.end <= stop else one.end - length)
        if b <= a:
            continue
        place = one.at
        if place is not None:
            place = place if place < start else (start if place < stop else place - length)
        lyrics.append(replace(one, start=a, end=b, at=place))
    out.lyrics = lyrics
    return _tidy(out)


def extract(sheet: Sheet, start: int, stop: int) -> Sheet:
    """The stretch ``[start, stop)`` of a sheet, counted from ``start``: its notes, its changes, its lyrics (a piece
    that reaches out of it is clipped to it), the armadura and the clefs in force at ``start`` as its own, and the
    sheet's reference figures. No title lines."""
    notes = [replace(n, frame=n.frame - start) for n in sheet.notes if start <= n.frame < stop]
    _uncover(notes, 0)
    _no_lone_beams(notes)
    lyrics = []
    for one in sheet.lyrics:
        a, b = max(one.start, start), min(one.end, stop)
        if b <= a:
            continue
        place = None if one.at is None else min(max(one.at, start), stop - 1) - start
        lyrics.append(replace(one, start=a - start, end=b - start, at=place))
    out = Sheet(
        notes=notes,
        clefs={st: clef_at(sheet, st, start) for st in (1, 2)},
        clef_changes=[(f - start, st, c) for f, st, c in sheet.clef_changes if start < f < stop],
        key=key_at(sheet, start),
        key_changes=[(f - start, k) for f, k in sheet.key_changes if start < f < stop],
        quarter_ms=sheet.quarter_ms,
        lyrics=lyrics,
        space_ms=sheet.space_ms,
        line_space=sheet.line_space,
    )
    return _tidy(out)


def put_in(
    target: Sheet | None, passage: Sheet, at: int, length: int, *, music_after: bool
) -> Sheet:
    """``passage`` (from :func:`extract`) put into ``target`` at frame ``at``: the target's notes, changes and lyrics
    from ``at`` move ``length`` frames later first. The passage reads with its own armadura and clefs from ``at``;
    after it (``music_after``), the target's are in force again. A target with no music (``None``, or no notes)
    takes the passage's armadura, clefs and reference figures, and keeps its own title lines and lyrics.
    """
    empty = target is None or not target.notes
    if target is None:
        target = Sheet(notes=[])
    wanted_key = key_at(target, at)
    wanted_clefs = {st: clef_at(target, st, at) for st in (1, 2)}
    out = shift(target, at, length)
    top = max((n.beam for n in out.notes if n.beam is not None), default=0)
    renumber: dict[int, int] = {}
    for n in passage.notes:
        if n.beam is not None and n.beam not in renumber:
            renumber[n.beam] = top + len(renumber) + 1
    out.notes.extend(
        replace(n, frame=n.frame + at, beam=None if n.beam is None else renumber[n.beam])
        for n in passage.notes
    )
    out.key_changes.extend((f + at, k) for f, k in passage.key_changes)
    out.clef_changes.extend((f + at, st, c) for f, st, c in passage.clef_changes)
    out.lyrics.extend(
        replace(
            one,
            start=one.start + at,
            end=one.end + at,
            at=None if one.at is None else one.at + at,
        )
        for one in passage.lyrics
    )
    before = [n.frame for n in out.notes if n.frame < at]
    if empty:
        out.key, out.clefs = passage.key, dict(passage.clefs)
        out.quarter_ms, out.space_ms = passage.quarter_ms, passage.space_ms
        out.line_space = out.line_space if out.line_space is not None else passage.line_space
    elif not before:
        # The passage opens the sheet: its armadura and clefs are the sheet's first ones.
        out.key, out.clefs = passage.key, dict(passage.clefs)
    else:
        if key_at(out, at - 1) != passage.key:
            out.key_changes.append((at, passage.key))
        for st, clef in passage.clefs.items():
            if clef_at(out, st, at - 1) != clef:
                out.clef_changes.append((at, st, clef))
    end = at + length
    if music_after and not empty:
        if key_at(out, end - 1) != wanted_key and not any(f == end for f, _ in out.key_changes):
            out.key_changes.append((end, wanted_key))
        for st, clef in wanted_clefs.items():
            if clef_at(out, st, end - 1) != clef and not any(
                c[0] == end and c[1] == st for c in out.clef_changes
            ):
                out.clef_changes.append((end, st, clef))
    return _tidy(out)


# ------------------------------------------------------------------ the spans of the record


def shift_spans(spans: list[list[Any]], at: int, by: int, *, split: bool = True) -> list[list[Any]]:
    """``[first, end, ...]`` spans with everything at or after ``at`` moved ``by`` later. A span across ``at`` is
    cut in two around the passage (``split``, the AI's segments), or grows over it (the stretches it wrote again: a
    stretch is one request, counted once)."""
    out = []
    for span in spans:
        a, b, rest = int(span[0]), int(span[1]), list(span[2:])
        if a >= at:
            out.append([a + by, b + by, *rest])
        elif b > at and split:
            out.extend([[a, at, *rest], [at + by, b + by, *rest]])
        elif b > at:
            out.append([a, b + by, *rest])
        else:
            out.append([a, b, *rest])
    return out


def cut_spans(spans: list[list[Any]], start: int, stop: int) -> list[list[Any]]:
    """``[first, end, ...]`` spans with ``[start, stop)`` taken out: shortened, moved earlier, or gone."""
    length = stop - start
    out = []
    for span in spans:
        a, b, rest = int(span[0]), int(span[1]), list(span[2:])
        a2 = a if a < start else (start if a < stop else a - length)
        b2 = b if b <= start else (start if b <= stop else b - length)
        if b2 > a2:
            out.append([a2, b2, *rest])
    return out


def clip_spans(spans: list[list[Any]], start: int, stop: int, at: int) -> list[list[Any]]:
    """The parts of ``spans`` inside ``[start, stop)``, moved so that ``start`` is at ``at``."""
    out = []
    for span in spans:
        a, b = max(int(span[0]), start), min(int(span[1]), stop)
        if b > a:
            out.append([a - start + at, b - start + at, *span[2:]])
    return out


# ------------------------------------------------------------------ the stored sheet


def frame_of(ms: float) -> int:
    """The frame of the new sheet at ``ms`` (its frames are 40 ms, whatever ``frameMs`` the old sheet reads at)."""
    return int(round(ms / FRAME_MS))


def _drawn(part_id: str) -> build.Drawn | None:
    """The sheet of a part as the page draws it, or ``None`` when the part has no notes yet."""
    try:
        if not paths.part_notes_path(part_id).is_file():
            return None
        return build.current(part_id)
    except (FileNotFoundError, locate.NotFound):
        return None


@dataclass
class Copied:
    """The new sheet of a copied stretch (:func:`read`), counted from its first frame."""

    sheet: Sheet
    #: The record of the part it was copied from when that sheet holds decisions (``None``: the algorithm's).
    record: store.Record | None
    #: The hand the source's sheet draws for each of its notes, by note id: the hands of the notes it carries.
    hands: dict[int, str]
    #: The AI's segments and stretches of the record inside the stretch, counted from its first frame.
    windows: list[list[Any]]
    stretches: list[list[Any]]

    @property
    def decided(self) -> bool:
        return self.record is not None and self.record.decided


def read(part_id: str, from_ms: float, to_ms: float) -> Copied | None:
    """The new sheet of ``[from_ms, to_ms)`` of a part, as its page draws it now; ``None`` without notes."""
    drawn = _drawn(part_id)
    if drawn is None:
        return None
    sheet = f1.read(drawn.text)
    stored = pipeline.load_note_events(part_id)
    notes = events_file.notes_from_events(stored.events) if stored else None
    hands = build.hands_of_sheet(sheet, notes) if notes is not None else {}
    start, stop = frame_of(from_ms), frame_of(to_ms)
    record = drawn.record if drawn.record is not None and drawn.record.decided else None
    return Copied(
        extract(sheet, start, stop),
        record,
        hands,
        clip_spans(record.windows, start, stop, 0) if record else [],
        clip_spans(record.stretches, start, stop, 0) if record else [],
    )


def scaled(copied: Copied, speed: float, limit_ms: float | None = None) -> Copied:
    """A copied stretch played ``speed`` times as fast (a take promoted at its speed, Record in Sheet): every frame,
    and the reference figures, divided by ``speed``; with ``limit_ms``, what starts after it is left out (the window
    a take is fitted into)."""
    limit = None if limit_ms is None else frame_of(limit_ms)

    def at(frame: int) -> int:
        return int(round(frame / speed))

    def inside(frame: int) -> bool:
        return limit is None or at(frame) < limit

    sheet = copied.sheet
    notes = [replace(n, frame=at(n.frame)) for n in sheet.notes if inside(n.frame)]
    _no_lone_beams(notes)
    out = _copy(sheet, notes)
    out.key_changes = [(at(f), k) for f, k in sheet.key_changes if inside(f)]
    out.clef_changes = [(at(f), st, c) for f, st, c in sheet.clef_changes if inside(f)]
    out.lyrics = [
        replace(
            one,
            start=at(one.start),
            end=max(at(one.start) + 1, at(one.end) if limit is None else min(at(one.end), limit)),
            at=None if one.at is None else at(one.at),
        )
        for one in sheet.lyrics
        if inside(one.start)
    ]
    out.quarter_ms = None if sheet.quarter_ms is None else sheet.quarter_ms / speed
    out.space_ms = None if sheet.space_ms is None else sheet.space_ms / speed

    def spans(rows: list[list[Any]]) -> list[list[Any]]:
        moved = [[at(int(a)), at(int(b)), *rest] for a, b, *rest in rows]
        return [row for row in clip_spans(moved, 0, limit, 0)] if limit is not None else moved

    return replace(
        copied,
        sheet=_tidy(out),
        windows=spans(copied.windows),
        stretches=spans(copied.stretches),
    )


def target(part_id: str) -> tuple[Sheet | None, store.Stored | None]:
    """The sheet of a part a change of length is about to change: what its page draws now (``None`` when it has
    no notes), and what is stored."""
    drawn = _drawn(part_id)
    kept = store.load(part_id)
    if drawn is None or not drawn.text:
        return (f1.read(kept.text) if kept is not None else None), kept
    sheet = f1.read(drawn.text)
    return (sheet if sheet.notes else None), kept


def store_after(
    part_id: str,
    before: Sheet | None,
    kept: store.Stored | None,
    *,
    revision: int,
    cut: tuple[int, int] | None = None,
    tail: bool = False,
    copied: Copied | None = None,
    at: int = 0,
    length: int = 0,
    music_after: bool = False,
) -> bool:
    """The sheet of a part after a change of its length, stored for the notes' ``revision`` (written already): the
    stretch ``cut`` taken out (``tail``: it ran to the end), then the ``copied`` passage put in at frame ``at``,
    ``length`` frames long. Stored when the target's sheet or the passage's holds decisions, or when the target had no
    music; returns whether it was. The result is laid on the notes (``build.reapply``), so the rules run on the new
    neighbours."""
    decided = kept is not None and kept.record.decided
    empty = before is None or not before.notes
    # A part with no music that gets a passage (a blank sheet, a new part of a project) stores its first sheet, even
    # the algorithm's: its Sheet step is then written, as the old sheet saved its first one.
    if not decided and not (copied is not None and (copied.decided or empty)):
        return False
    if kept is not None and kept.record.decided:
        record = store.Record.from_json(kept.record.to_json())
    else:
        record = store.Record(
            source="algorithm",
            quarter_ms=(
                before.quarter_ms
                if before is not None and before.notes
                else (copied.sheet.quarter_ms if copied is not None else None)
            ),
        )
    sheet = before
    if cut is not None and sheet is not None:
        sheet = cut_out(sheet, cut[0], cut[1], tail=tail)
        record.windows = cut_spans(record.windows, *cut)
        record.stretches = cut_spans(record.stretches, *cut)
    if copied is not None:
        sheet = put_in(sheet, copied.sheet, at, length, music_after=music_after)
        record.windows = shift_spans(record.windows, at, length)
        record.stretches = shift_spans(record.stretches, at, length, split=False)
        source = copied.record
        if source is not None:
            record.windows = sorted(
                record.windows + [[a + at, b + at, *rest] for a, b, *rest in copied.windows],
                key=lambda span: span[0],
            )
            record.stretches = sorted(
                record.stretches + [[a + at, b + at, *rest] for a, b, *rest in copied.stretches],
                key=lambda span: span[0],
            )
            if empty and not decided:
                record.source = source.source
                record.quarter_ms, record.reference = copied.sheet.quarter_ms, source.reference
                record.model, record.prompt = source.model, source.prompt
            elif source.enhanced and record.source == "algorithm":
                # The AI wrote part of it: **Enhanced with AI**.
                record.source = "mixed"
            record.runs = max(record.runs, source.runs)
            record.edited = record.edited or source.edited
    if sheet is None:
        return False
    settled = build.reapply(sheet, pipeline.starting_hands(part_id))
    record.hands_revision = revision
    store.save(part_id, f1.write(settled, mode="frames"), record)
    build.forget(part_id)
    return True


def song_reading(part_id: str, at_ms: float) -> tuple[float | None, int | None]:
    """The reference figure of a part's sheet as its page draws it (one negra, in ms) and the armadura in force at
    ``at_ms``; ``(None, None)`` without notes."""
    drawn = _drawn(part_id)
    sheet = f1.read(drawn.text) if drawn is not None and drawn.text else None
    if sheet is None or not sheet.notes:
        return None, None
    return drawn.quarter_ms, key_at(sheet, frame_of(at_ms))


def keep_figure(part_id: str, quarter_ms: float | None, key: int | None = None) -> None:
    """The sheets of a passage (Record in Sheet) read with the song's reference figure (at the take's speed) and its
    armadura where the passage starts: an algorithm record that names them (``reference: song``, ``key``), so the
    algorithm, and an AI run, write with them. A sheet with decisions keeps its own."""
    if quarter_ms is None or quarter_ms <= 0 or not paths.part_notes_path(part_id).is_file():
        return
    kept = store.load(part_id)
    if kept is not None and kept.record.decided:
        return
    header = events_file.read_header(paths.part_notes_path(part_id))
    sheet = build.algorithm(part_id, quarter_ms=quarter_ms, key=key).sheet
    record = store.Record(
        source="algorithm",
        hands_revision=header.hands_revision,
        quarter_ms=quarter_ms,
        reference="song",
        key=key,
    )
    store.save(part_id, f1.write(sheet, mode="frames"), record)
    build.forget(part_id)
