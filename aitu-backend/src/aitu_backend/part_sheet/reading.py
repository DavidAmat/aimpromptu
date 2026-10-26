"""The reading edits of the new sheet: what the note toolbox and the range toolbox change (implementation 03, Phase 7).

Each function changes a frames sheet in place (the sheet the page shows now, ``build.current``) and returns the
label of the step ("Write 3 chords as corcheas"), or raises :class:`Refused` with the reason, said for the page. It
does not settle the sheet: :mod:`.edits` lays the result on the notes again (``build.reapply``), so the rules run
(figures, grace notes, beam groups cut by the figures, spelling) and keep the user's decisions:

* **notes** are named as their noteheads name them, ``"<frame>:<midi>"`` (``data-note``). A figure, a beam, the
  grace note switch and an ornament belong to a chord: picking one note of a chord in a hand names the whole chord
  of that hand. A finger belongs to one note;
* **a stretch** is the columns ``[start, end)`` (frames, end excluded), on one staff or both.

The marks only the user writes (a finger ``fg3``, a figure set by hand ``fix``, the grace note switch ``asgrace`` /
``nograce``) are kept through a new AI run; the others (beams, clefs, 8va, armaduras, ornaments) are the AI's kinds
too, and a new AI run writes them again (the user's answer of Phase 7, plan section 3.7).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Callable

from aitu_backend.sheet.llm.frames import one_figure
from aitu_backend.sheet.proposal.frames import (
    _SIGNS,
    BASS_LIMIT,
    KEYS,
    _ledger,
    clefs_and_ottavas,
)
from aitu_backend.sheet.sheet.data import (
    LYRIC_FONTS,
    LYRIC_MAX,
    LYRIC_MIN,
    TITLE_FIELDS,
    Lyric,
    Note,
    Sheet,
)
from aitu_backend.sheet.sheet.figures import FIGURES, NAMES
from aitu_backend.sheet.sheet.frames import MAX_BEAM
from aitu_backend.sheet.sheet.spelling import spell

__all__ = [
    "ACTIONS",
    "OWN_CLEF",
    "Refused",
    "clef_rule",
    "fewest_signs",
    "join_beam",
    "key_name",
    "plan",
    "break_beam",
    "set_clef",
    "set_figure",
    "set_fingers",
    "set_grace",
    "set_key",
    "set_ornament",
    "set_ottava",
    "unwrap_ornament",
    "far_notes",
    "moved_key",
    "rename_figures",
    "transpose_sheet",
    "set_line_space",
    "set_lyrics",
    "set_piece_key",
    "set_titles",
]

#: The clef each hand reads when nothing changes it.
OWN_CLEF = {1: "G2", 2: "F4"}
CLEFS = {"treble": "G2", "bass": "F4"}
#: The ornaments written over the first onset of a run, the other onsets of the run inside them (``orn``).
SPANS = ("trill", "mordent", "turn")
#: The ornaments of one chord.
MARKS = ("arpeggio", "fermata")
OTTAVA_NAMES = {1: "8va", 2: "15ma", -1: "8vb", -2: "15mb"}
#: The space between lines the sheet toolbox offers, in staff spaces (the engine's own is 5).
LINE_SPACE = (2.0, 16.0)


class Refused(ValueError):
    """The edit cannot be made; the message says why, for the page."""


# ------------------------------------------------------------------ the notes and chords picked


def _ref(ref: str) -> tuple[int, int] | None:
    try:
        frame, midi = ref.split(":")
        return int(frame), int(midi)
    except ValueError:
        return None


def _drawn(sheet: Sheet) -> list[Note]:
    return [n for n in sheet.notes if n.staff in (1, 2) and not n.covered and n.frame is not None]


def picked_notes(sheet: Sheet, refs: list[str]) -> list[Note]:
    places = {p for p in map(_ref, refs) if p is not None}
    found = [n for n in _drawn(sheet) if (n.frame, n.midi) in places]
    if not found:
        raise Refused("None of these notes is on the sheet any more.")
    return found


def chords_of(sheet: Sheet, refs: list[str]) -> dict[tuple[int, int], list[Note]]:
    """The chords the picked notes belong to: ``(staff, frame) -> every drawn note of that hand at that column``."""
    picked = {(n.staff, n.frame) for n in picked_notes(sheet, refs)}
    out: dict[tuple[int, int], list[Note]] = defaultdict(list)
    for n in _drawn(sheet):
        if (n.staff, n.frame) in picked:
            out[(n.staff, n.frame)].append(n)
    return dict(sorted(out.items(), key=lambda kv: (kv[0][1], kv[0][0])))


def _columns(sheet: Sheet, staff: int) -> list[tuple[int, list[Note]]]:
    """The main (not grace) drawn columns of one hand, in order."""
    cols: dict[int, list[Note]] = defaultdict(list)
    for n in _drawn(sheet):
        if n.staff == staff and not n.grace:
            cols[n.frame].append(n)
    return sorted(cols.items())


def _count(k: int, one: str, many: str | None = None) -> str:
    return one if k == 1 else f"{k} {many or one + 's'}"


def _one_hand(chords: dict[tuple[int, int], list[Note]], what: str) -> int:
    staffs = {st for st, _ in chords}
    if len(staffs) != 1:
        raise Refused(f"Pick the notes of one hand: {what} belongs to one hand.")
    return staffs.pop()


def _run(sheet: Sheet, staff: int, frames: list[int], what: str) -> list[tuple[int, list[Note]]]:
    """The columns ``frames`` of a hand when they follow one another (no column of that hand between them)."""
    cols = _columns(sheet, staff)
    at = {f: i for i, (f, _) in enumerate(cols)}
    idx = sorted(at[f] for f in frames if f in at)
    if not idx or idx != list(range(idx[0], idx[-1] + 1)):
        raise Refused(f"Pick notes that follow one another in one hand: {what}.")
    return [cols[i] for i in idx]


# ------------------------------------------------------------------ figures, fingers, grace notes


def set_figure(sheet: Sheet, refs: list[str], figure: int | None) -> str:
    """The figure of the picked chords, set by hand (``fix``): the rule keeps it, and it is never a grace note.
    ``None`` gives them back the rule's figure."""
    chords = chords_of(sheet, refs)
    if figure is not None and figure not in FIGURES:
        raise Refused(f"No figure {figure}.")
    for ns in chords.values():
        for n in ns:
            if figure is None:
                n.fixed = False
            else:
                n.figure, n.fixed, n.grace_rule = figure, True, None
    k = len(chords)
    if figure is None:
        return f"Give {_count(k, 'a chord', 'chords')} back {'its' if k == 1 else 'their'} figure"
    return f"Write {_count(k, 'a chord', 'chords')} as {_count(k, f'a {NAMES[figure]}', NAMES[figure] + 's')}"


def set_fingers(sheet: Sheet, refs: list[str], fingers: list[int]) -> str:
    """Fingers: one number on every picked note, or on a single chord one number per note from the lowest note up:
    the smallest numbers first in the right hand (the thumb under the lowest note), the largest first in the left
    hand (the little finger on it). ``[]`` takes them off."""
    notes = picked_notes(sheet, refs)
    if any(f not in range(1, 6) for f in fingers):
        raise Refused("A finger is a number from 1 to 5.")
    one_chord = len({(n.staff, n.frame) for n in notes}) == 1 and len(notes) > 1
    if not fingers:
        for n in notes:
            n.finger = None
        return "Remove the fingers"
    if one_chord and len(fingers) > 1:
        ordered = sorted(set(fingers), reverse=notes[0].staff == 2)
        for n, f in zip(sorted(notes, key=lambda n: n.midi), ordered + [None] * len(notes)):
            n.finger = f
        return f"Fingers {' '.join(map(str, ordered))} on a chord"
    for n in notes:
        n.finger = fingers[-1]
    return f"Finger {fingers[-1]} on {_count(len(notes), 'a note', 'notes')}"


def set_grace(sheet: Sheet, refs: list[str], rule: str | None) -> str:
    """The grace note switch of the picked chords: ``on`` written as grace notes of the next note of their hand,
    ``off`` as normal notes, ``None`` back to the grace rule. A figure set by hand gives way to ``on``.
    """
    if rule not in ("on", "off", None):
        raise Refused(f"No grace switch {rule!r}.")
    chords = chords_of(sheet, refs)
    for ns in chords.values():
        for n in ns:
            n.grace_rule = rule
            if rule == "on":
                n.fixed = False
    k = len(chords)
    if rule is None:
        return f"Grace {'note' if k == 1 else 'notes'} back to the rule"
    return (
        f"Write {_count(k, 'a chord', 'chords')} as {'grace' if rule == 'on' else 'normal'} notes"
    )


# ------------------------------------------------------------------ beams


def _beam_check(cols: list[tuple[int, list[Note]]]) -> None:
    if len(cols) < 2:
        raise Refused("A beam joins two notes or more.")
    if len(cols) > MAX_BEAM:
        raise Refused(f"A beam group has at most {MAX_BEAM} notes (a chord counts as one).")
    figs = [ns[0].figure or 0 for _, ns in cols]
    if any(f < 8 for f in figs):
        raise Refused(
            "A negra or a longer figure has no beam: every note must be a corchea or shorter."
        )
    if one_figure(list(range(len(cols))), figs) != [list(range(len(cols)))]:
        raise Refused(
            "A beam group holds one figure; one note of a figure next to it may open or close the group."
        )


def _new_beam(sheet: Sheet) -> int:
    return max((n.beam for n in sheet.notes if n.beam is not None), default=0) + 1


def join_beam(sheet: Sheet, refs: list[str]) -> str:
    """Beam the picked chords as one group; when they are already exactly one group, take the beam away."""
    chords = chords_of(sheet, refs)
    staff = _one_hand(chords, "a beam")
    if any(n.grace for ns in chords.values() for n in ns):
        raise Refused("A grace note has no beam with the notes of the music.")
    cols = _run(sheet, staff, [f for _, f in chords], "a beam joins notes that follow one another")
    beams = {n.beam for _, ns in cols for n in ns}
    group = beams.pop() if len(beams) == 1 else None
    if group is not None and len(cols) == len({n.frame for n in sheet.notes if n.beam == group}):
        for _, ns in cols:
            for n in ns:
                n.beam = None
        return "Remove the beam"
    _beam_check(cols)
    new = _new_beam(sheet)
    for _, ns in cols:
        for n in ns:
            n.beam = new
    return f"Beam {_count(len(cols), 'a note', 'notes')} as one group"


def break_beam(sheet: Sheet, refs: list[str]) -> str:
    """Start a new beam group at the first picked chord, or, when it already starts one (or has none) after a
    beamed note, join it to the group before."""
    chords = chords_of(sheet, refs)
    staff = _one_hand(chords, "a beam")
    cols = _columns(sheet, staff)
    at = {f: i for i, (f, _) in enumerate(cols)}
    first = min(f for _, f in chords if f in at) if any(f in at for _, f in chords) else None
    if first is None:
        raise Refused("A grace note has no beam with the notes of the music.")
    i = at[first]
    beam = cols[i][1][0].beam
    if beam is not None and i > 0 and cols[i - 1][1][0].beam == beam:
        new = _new_beam(sheet)
        for _, ns in cols[i:]:
            if ns[0].beam != beam:
                break
            for n in ns:
                n.beam = new
        return "Start a new beam here"
    before = cols[i - 1][1][0].beam if i > 0 else None
    if before is None:
        raise Refused("There is no beam before this note to join.")
    run = [c for c in cols if c[1][0].beam == before]
    run += [c for c in cols[i:] if beam is not None and c[1][0].beam == beam] or [cols[i]]
    _beam_check(run)
    for _, ns in run:
        for n in ns:
            n.beam = before
    return "Join the beam again"


# ------------------------------------------------------------------ ornaments


def set_ornament(sheet: Sheet, refs: list[str], kind: str) -> str:
    """An ornament. ``trill``, ``mordent``, ``turn``: written over the first picked onset of one hand, the other
    picked onsets (which follow it) played inside it (``orn``: kept in the notes, not drawn); pressed again on the
    same onsets, the ornament goes away. ``arpeggio``, ``fermata``: on every picked chord, or off when all of them
    carry it."""
    chords = chords_of(sheet, refs)
    if kind in MARKS:
        on = not all(kind in n.ornaments for ns in chords.values() for n in ns)
        for ns in chords.values():
            for n in ns:
                rest = tuple(o for o in n.ornaments if o != kind)
                n.ornaments = tuple(sorted(rest + ((kind,) if on else ())))
        name = "a rolled chord" if kind == "arpeggio" else "a fermata"
        return f"{'Add' if on else 'Remove'} {name}"
    if kind not in SPANS:
        raise Refused(f"No ornament {kind!r}.")
    staff = _one_hand(chords, "an ornament")
    cols = _run(
        sheet, staff, [f for _, f in chords], "an ornament is played on onsets one after another"
    )
    head, inside = cols[0][1], [n for _, ns in cols[1:] for n in ns]
    if kind in head[0].ornaments:
        unwrap_ornament(sheet, refs)
        return f"Print the {kind} as notes"
    unwrap_ornament(sheet, refs)
    for n in head:
        # One held note with the ornament over it: out of its beam group, which the hidden onsets would break.
        n.ornaments = tuple(sorted({*(o for o in n.ornaments if o not in SPANS), kind}))
        n.beam = None
    for n in inside:
        n.covered, n.beam, n.grace_rule = True, None, None
        n.ornaments = tuple(o for o in n.ornaments if o not in SPANS)
    what = {"trill": "a trill", "mordent": "a mordent", "turn": "a turn"}[kind]
    return f"Write {_count(len(cols), 'a note', 'notes')} as {what}"


def unwrap_ornament(sheet: Sheet, refs: list[str]) -> int:
    """Take the trills, mordents and turns off the picked chords; the onsets played inside them are drawn again.
    Returns how many chords had one."""
    done = 0
    for (staff, frame), ns in chords_of(sheet, refs).items():
        if not any(o in SPANS for n in ns for o in n.ornaments):
            continue
        done += 1
        for n in ns:
            n.ornaments = tuple(o for o in n.ornaments if o not in SPANS)
        later = sorted(
            (
                n
                for n in sheet.notes
                if n.staff == staff and n.frame is not None and n.frame > frame
            ),
            key=lambda n: n.frame,
        )
        stop = next((n.frame for n in later if not n.covered), None)
        for n in later:
            if stop is not None and n.frame >= stop:
                break
            n.covered = False
    return done


# ------------------------------------------------------------------ a stretch: armadura, clefs, 8va


def _frames(sheet: Sheet) -> list[int]:
    return sorted({n.frame for n in sheet.notes if n.frame is not None})


def _stretch(sheet: Sheet, start: int, end: int) -> tuple[int, bool]:
    """The first frame of the sheet, and whether notes come after the stretch."""
    frames = _frames(sheet)
    if start >= end or not any(start <= f < end for f in frames):
        raise Refused("The stretch holds no notes.")
    return frames[0], any(f >= end for f in frames)


def _key_at(sheet: Sheet, frame: int) -> int:
    key = sheet.key or 0
    for f, k in sorted(sheet.key_changes):
        if f <= frame:
            key = k
    return key


def _clef_at(sheet: Sheet, staff: int, frame: int) -> str:
    clef = sheet.clefs.get(staff, OWN_CLEF[staff])
    for f, st, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if st == staff and f <= frame:
            clef = c
    return clef


def key_name(fifths: int) -> str:
    """``3`` -> "3 sostenidos", ``-1`` -> "1 bemol", ``0`` -> "no signs" (the user's names of the signs)."""
    if fifths == 0:
        return "no signs"
    k = abs(fifths)
    return f"{k} {'sostenido' if fifths > 0 else 'bemol'}{'' if k == 1 else ('s' if fifths > 0 else 'es')}"


def set_key(sheet: Sheet, start: int, end: int, key: int | None) -> str:
    """The armadura of the stretch (fifths; ``None``: the armadura of the piece); the one in force after it comes
    back at its end. A stretch from the first note changes the armadura the sheet starts with."""
    if key is not None and key not in range(-7, 8):
        raise Refused("An armadura has at most seven signs.")
    first, after = _stretch(sheet, start, end)
    piece = sheet.key or 0
    key = piece if key is None else key
    at_end = _key_at(sheet, end)
    changes = [(f, k) for f, k in sheet.key_changes if not start <= f < end]
    if start <= first:
        sheet.key = key
    else:
        changes.append((start, key))
    if after and not any(f == end for f, _ in changes):
        changes.append((end, at_end))
    sheet.key_changes = sorted(changes)
    if key == piece:
        return "The armadura of the piece for a stretch"
    return f"Armadura of {key_name(key)} for a stretch"


def fewest_signs(sheet: Sheet, start: int, end: int) -> dict[str, int]:
    """The armadura in force at the start of the stretch, the one that prints the fewest signs over it (the rule of
    the algorithm, ``choose_keys``, for one passage; a tie keeps the one in force), and their signs.
    """
    pcs = [n.midi % 12 for n in _drawn(sheet) if start <= n.frame < end]
    now = _key_at(sheet, start)
    signs = {int(k): int(sum(_SIGNS[i][pc] for pc in pcs)) for i, k in enumerate(KEYS)}
    best = min(signs, key=lambda k: (signs[k], k != now, abs(k), k < 0))
    return {"key": now, "signs": signs[now], "fewest": best, "fewestSigns": signs[best]}


def set_clef(sheet: Sheet, start: int, end: int, staff: int, clef: str | None) -> str:
    """The clef of one hand over the stretch (``treble``, ``bass``; ``None``: the hand's own clef); the clef in force
    after it comes back at its end. A bass clef takes no 8va: the notes under one in the stretch lose it.
    """
    if staff not in (1, 2):
        raise Refused("A clef belongs to one hand.")
    code = OWN_CLEF[staff] if clef is None else CLEFS.get(clef)
    if code is None:
        raise Refused(f"No clef {clef!r}.")
    first, after = _stretch(sheet, start, end)
    at_end = _clef_at(sheet, staff, end)
    changes = [c for c in sheet.clef_changes if not (c[1] == staff and start <= c[0] < end)]
    if start <= first:
        sheet.clefs[staff] = code
    else:
        changes.append((start, staff, code))
    if after and not any(f == end and st == staff for f, st, _ in changes):
        changes.append((end, staff, at_end))
    sheet.clef_changes = sorted(changes, key=lambda c: (c[0], c[1]))
    if code == "F4":
        for n in sheet.notes:
            if n.staff == staff and n.frame is not None and start <= n.frame < end and n.ottava > 0:
                n.ottava = 0
    hand = "right" if staff == 1 else "left"
    return f"{'Treble' if code == 'G2' else 'Bass'} clef for a stretch of the {hand} hand"


def clef_rule(sheet: Sheet, start: int, end: int, staffs: list[int]) -> str:
    """The clefs and 8va of the clef rules (version 4: ``proposal.frames.clefs_and_ottavas``) over the stretch, for
    the hands in ``staffs``; the stored ones stay everywhere else."""
    first, after = _stretch(sheet, start, end)
    rule = replace(
        sheet,
        notes=[replace(n) for n in sheet.notes],
        clefs=dict(sheet.clefs),
        clef_changes=list(sheet.clef_changes),
    )
    clefs_and_ottavas(rule)
    by_place = {(n.staff, n.frame, n.midi, n.grace is not None): n.ottava for n in rule.notes}
    for staff in staffs:
        at_end = _clef_at(sheet, staff, end)
        start_clef = _clef_at(rule, staff, start)
        changes = [c for c in sheet.clef_changes if not (c[1] == staff and start <= c[0] < end)]
        changes += [c for c in rule.clef_changes if c[1] == staff and start < c[0] < end]
        if start <= first:
            sheet.clefs[staff] = start_clef
        else:
            changes.append((start, staff, start_clef))
        if after and not any(f == end and st == staff for f, st, _ in changes):
            changes.append((end, staff, at_end))
        sheet.clef_changes = sorted(changes, key=lambda c: (c[0], c[1]))
        for n in sheet.notes:
            if n.staff == staff and n.frame is not None and start <= n.frame < end:
                n.ottava = by_place.get((staff, n.frame, n.midi, n.grace is not None), 0)
    return "Clefs and 8va by the rule for a stretch"


def set_ottava(sheet: Sheet, start: int, end: int, staff: int, ottava: int) -> str:
    """An octave line over one hand's notes in the stretch (``1`` 8va, ``2`` 15ma, ``-1`` 8vb, ``-2`` 15mb; ``0``
    none). The notes are written that far from where they sound. A bass clef takes no 8va or 15ma.
    """
    if staff not in (1, 2):
        raise Refused("An octave line belongs to one hand.")
    if ottava not in (0, *OTTAVA_NAMES):
        raise Refused(f"No octave line {ottava}.")
    _stretch(sheet, start, end)
    notes = [
        n
        for n in sheet.notes
        if n.staff == staff and n.frame is not None and start <= n.frame < end
    ]
    if not notes:
        raise Refused(
            f"The {'right' if staff == 1 else 'left'} hand plays nothing in this stretch."
        )
    if ottava > 0 and any(_clef_at(sheet, staff, n.frame) == "F4" for n in notes):
        raise Refused("A bass clef takes no 8va: write this stretch in the treble clef first.")
    for n in notes:
        n.ottava = ottava
    hand = "right" if staff == 1 else "left"
    if ottava == 0:
        return f"Remove the octave line of a stretch of the {hand} hand"
    return f"{OTTAVA_NAMES[ottava]} over a stretch of the {hand} hand"


# ------------------------------------------------------------------ the whole sheet (Phase 8: the sheet toolbox)


def set_titles(sheet: Sheet, titles: dict[str, object]) -> str:
    """The title lines printed above the sheet (``title``, ``subtitle``, ``artist``); an empty one is left out (the
    title is then the project's name)."""
    unknown = set(titles) - set(TITLE_FIELDS)
    if unknown:
        raise Refused(f"No title line {sorted(unknown)[0]!r}.")
    for name, value in titles.items():
        text = " ".join(str(value or "").split())[:200]
        if text:
            sheet.titles[name] = text
        else:
            sheet.titles.pop(name, None)
    names = [name for name in TITLE_FIELDS if name in titles]
    return "Title" if names == ["title"] else "Title lines"


def set_piece_key(sheet: Sheet, key: int) -> str:
    """The armadura of the piece (the one the sheet starts with); the armaduras of passages stay. Spelling only:
    no note moves."""
    if key not in range(-7, 8):
        raise Refused("An armadura has at most seven signs.")
    sheet.key = key
    return f"Armadura of the piece: {key_name(key)}"


def set_line_space(sheet: Sheet, space: float | None) -> str:
    """The space between lines, in staff spaces (``None``: the engine's own)."""
    if space is not None and not LINE_SPACE[0] <= space <= LINE_SPACE[1]:
        raise Refused(
            f"The space between lines is {LINE_SPACE[0]:g} to {LINE_SPACE[1]:g} staff spaces."
        )
    sheet.line_space = None if space is None else round(float(space), 2)
    return "Space between lines"


#: How far a lyrics block may be put from its column and from the top staff line, in staff spaces.
LYRIC_REACH = 40.0


def set_lyrics(sheet: Sheet, pieces: list[dict], label: str | None) -> str:
    """The lyrics pieces of the sheet, all of them (the page works out the list: a piece placed, moved, made
    longer, split, merged, its words, its size, its lift; since Phase 8A++ a block put anywhere, its width, font,
    bold and italic). Two pieces never share a frame."""
    lyrics = []
    for piece in pieces:
        try:
            dy = piece.get("dy")
            width = piece.get("width")
            one = Lyric(
                start=int(piece["start"]),
                end=int(piece["end"]),
                text=str(piece.get("text") or "").strip("\n")[:500],
                size=None if piece.get("size") is None else float(piece["size"]),
                lift=float(piece.get("lift") or 0.0),
                at=None if dy is None or piece.get("at") is None else int(piece["at"]),
                dx=0.0 if dy is None else float(piece.get("dx") or 0.0),
                dy=None if dy is None else float(dy),
                width=None if width is None else float(width),
                font=str(piece.get("font") or "lora"),
                bold=bool(piece.get("bold", False)),
                italic=bool(piece.get("italic", True)),
            )
        except (KeyError, TypeError, ValueError):
            raise Refused("A lyrics piece needs its first and last frames and its words.") from None
        if one.start < 0 or one.end <= one.start:
            raise Refused("A lyrics piece ends after it starts.")
        if not one.text.strip():
            raise Refused("A lyrics piece has words.")
        if one.size is not None:
            one.size = round(min(LYRIC_MAX, max(LYRIC_MIN, one.size)), 2)
        one.lift = round(min(20.0, max(-4.0, one.lift)), 2)
        if one.font not in LYRIC_FONTS:
            raise Refused(f"No lyrics font {one.font!r}.")
        if one.dy is not None:
            one.dx = round(min(LYRIC_REACH, max(-LYRIC_REACH, one.dx)), 2)
            one.dy = round(min(LYRIC_REACH, max(-LYRIC_REACH, one.dy)), 2)
            if one.at is not None and one.at < 0:
                one.at = None
        if one.width is not None:
            one.width = round(min(200.0, max(2.0, one.width)), 2)
        lyrics.append(one)
    lyrics.sort(key=lambda one: one.start)
    for a, b in zip(lyrics, lyrics[1:]):
        if b.start < a.end:
            raise Refused("Another lyrics piece is already over those frames.")
    sheet.lyrics = lyrics
    return (label or "Lyrics")[:80]


def rename_figures(sheet: Sheet, steps: int) -> str:
    """Transpose figures: every figure ``steps`` figures shorter (negative: longer), the user's override of the
    reference figure (rule 5; D-18). No note moves: the spacing keeps the figure it was measured with
    (``Sheet.space_ms``). A figure set by hand moves with the others; one that has no figure to become goes back to
    the rule."""
    if not steps:
        raise Refused("Choose two different figures.")
    quarter = sheet.quarter_ms
    if quarter is None:
        raise Refused("This sheet has no reference figure yet.")
    if sheet.space_ms is None:
        sheet.space_ms = quarter
    sheet.quarter_ms = quarter * 2.0**steps
    if abs(sheet.quarter_ms - sheet.space_ms) < 0.05:
        sheet.space_ms = None
    for n in sheet.notes:
        if n.fixed and n.figure is not None:
            moved = int(n.figure * 2.0**steps) if steps > 0 else n.figure // 2 ** (-steps)
            if moved in FIGURES and n.figure * 2.0**steps == moved:
                n.figure = moved
            else:
                n.fixed = False
    k = abs(steps)
    return (
        f"Every figure {k} {'step' if k == 1 else 'steps'} {'shorter' if steps > 0 else 'longer'}"
    )


def moved_key(key: int, semitones: int) -> int:
    """An armadura moved by ``semitones``: of the two names of one key, the one with fewer signs (Db mayor up two
    semitones is Eb mayor, 3 bemoles; six signs either way keep the side they had)."""
    k = (key + 7 * semitones + 6) % 12 - 6
    if k == -6 and key > 0:
        k = 6
    return k


def transpose_sheet(sheet: Sheet, semitones: int) -> None:
    """Every note of a stored sheet ``semitones`` higher, and its armaduras with them (Transpose notes, Phase 8):
    the decisions stay on their notes. The spelling is the rule's (``build.reapply`` writes it again); the clefs are
    fitted afterwards where a note reads too far from its staff (:func:`far_notes`)."""
    sheet.key = moved_key(sheet.key or 0, semitones)
    sheet.key_changes = [(f, moved_key(k, semitones)) for f, k in sheet.key_changes]
    for n in sheet.notes:
        at = sheet.key
        for f, k in sorted(sheet.key_changes):
            if n.frame is not None and f <= n.frame:
                at = k
        n.step, n.alter, n.octave = spell(n.midi + semitones, at)


def far_notes(sheet: Sheet) -> set[tuple[int, int, int]]:
    """The notes four ledger lines or more from their staff, in the clef and 8va they are written in: where the
    clef rules should decide again (``build.fit_clefs``)."""
    out = set()
    for n in _drawn(sheet):
        below, above = _ledger(n, _clef_at(sheet, n.staff, n.frame), n.ottava)
        if max(below, above) >= BASS_LIMIT:
            out.add((n.frame, n.midi, n.staff))
    return out


# ------------------------------------------------------------------ one request of the page


STAFFS = {"right": [1], "left": [2], "both": [1, 2]}
ACTIONS = (
    "figure",
    "finger",
    "beam-join",
    "beam-break",
    "grace",
    "ornament",
    "key",
    "clef",
    "clef-rule",
    "ottava",
    "titles",
    "piece-key",
    "line-space",
    "lyrics",
    "figures",
)


def plan(
    action: str,
    *,
    notes: list[str] | None = None,
    start: int | None = None,
    end: int | None = None,
    staff: str = "both",
    value: object = None,
) -> tuple[Callable[[Sheet], str], Callable[[Sheet], str | None] | None]:
    """The change of one request of the toolboxes, and what the settled sheet must hold afterwards (``None``: the
    rules cannot undo it). Raises :class:`Refused` for a request that names nothing to change."""
    refs = list(notes or [])
    # The whole sheet (Phase 8): no notes, no stretch.
    if action == "titles":
        if not isinstance(value, dict):
            raise Refused("Say which title lines to write.")
        return (lambda s: set_titles(s, value)), None
    if action == "piece-key":
        return (lambda s: set_piece_key(s, int(value or 0))), None
    if action == "line-space":
        return (lambda s: set_line_space(s, None if value is None else float(value))), None
    if action == "lyrics":
        if not isinstance(value, dict) or not isinstance(value.get("pieces"), list):
            raise Refused("Send the lyrics pieces.")
        return (lambda s: set_lyrics(s, value["pieces"], value.get("label"))), None
    if action == "figures":
        return (lambda s: rename_figures(s, int(value or 0))), None
    staffs = STAFFS.get(staff)
    if staffs is None:
        raise Refused(f"No staff {staff!r}.")
    if action in ("figure", "finger", "beam-join", "beam-break", "grace", "ornament") and not refs:
        raise Refused("Pick a note first.")
    if action in ("key", "clef", "clef-rule", "ottava") and (start is None or end is None):
        raise Refused("Mark a stretch first.")

    def one_staff() -> int:
        if len(staffs) != 1:
            raise Refused("Choose the right or the left hand's staff.")
        return staffs[0]

    if action == "figure":
        return (lambda s: set_figure(s, refs, None if value is None else int(value))), None
    if action == "finger":
        fingers = (
            [int(f) for f in (value or [])]
            if isinstance(value, list)
            else [int(value)] if value else []
        )
        return (lambda s: set_fingers(s, refs, fingers)), None
    if action == "beam-join":

        def one_group(settled: Sheet) -> str | None:
            beams = {n.beam for ns in chords_of(settled, refs).values() for n in ns}
            if len(beams) == 1:
                return None
            return "The rules of the sheet cut this group: a beam group holds one figure."

        return (lambda s: join_beam(s, refs)), one_group
    if action == "beam-break":
        return (lambda s: break_beam(s, refs)), None
    if action == "grace":
        rule = None if value is None else str(value)

        def graced(settled: Sheet) -> str | None:
            if rule is None:
                return None
            wanted = rule == "on"
            if all(
                (n.grace is not None) == wanted
                for ns in chords_of(settled, refs).values()
                for n in ns
            ):
                return None
            if wanted:
                return (
                    "A grace note leans on the next note of its hand: this one has none after it."
                )
            return "These notes could not be written as normal notes."

        return (lambda s: set_grace(s, refs, rule)), graced
    if action == "ornament":
        return (lambda s: set_ornament(s, refs, str(value))), None
    assert start is not None and end is not None
    if action == "key":
        return (lambda s: set_key(s, start, end, None if value is None else int(value))), None
    if action == "clef":
        return (
            lambda s: set_clef(s, start, end, one_staff(), None if value is None else str(value))
        ), None
    if action == "clef-rule":
        return (lambda s: clef_rule(s, start, end, staffs)), None
    if action == "ottava":
        return (lambda s: set_ottava(s, start, end, one_staff(), int(value or 0))), None
    raise Refused(f"No edit {action!r}.")
