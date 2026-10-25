"""The new sheet of aimpromptu: the F1 frames view with hands, plain figures and tags (implementation 03, Phase 2).

The product sheet has no compases, no tempo, no puntillos, no tuplets and no silencios (plan section 3.1). It is
the F1 frames view (``f1.write(sheet, mode="frames")``): one line per drawn column, both hands on the line, every
note with its hand and its plain figure, and the tags of beam groups, grace notes, ornaments, clef changes, 8va
and armadura changes.

**Drawn column.** Notes struck together are one chord even when they fall one column apart: the notes are grouped
on their raw onsets, 40 ms from the first onset of a group, without chaining, across both hands (D-04, the rule of
:mod:`aitu_backend.transcription.grouping`), and a group is drawn at the column of its first onset. A note is
therefore drawn at its own onset cell or one column before it. The stored truth stays ``notes.pmn`` (rule 1: a
column never moves); :func:`cells_of` maps the notes of a sheet back to their onset cells, which is the round trip
with the matrix.

:func:`check` lists what breaks the rules of the product sheet; the LLM step (Phase 4) uses it as its checker.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from aitu_backend.matrix.keys import LOWEST_MIDI
from aitu_backend.pmn.dense import columns_of
from aitu_backend.pmn.notes import HAND_LEFT, HAND_RIGHT, Notes
from aitu_backend.sheet.sheet.data import FRAME_MS, Note, Sheet
from aitu_backend.sheet.sheet.figures import FIGURES
from aitu_backend.sheet.sheet.spelling import key_alter, sign, spell

__all__ = [
    "GROUP_MS",
    "MAX_BEAM",
    "cells_of",
    "check",
    "drawn_columns",
    "from_notes",
    "key_at",
    "matrix_cells",
    "printed_signs",
]

GROUP_MS = 40.0  # D-04
MAX_BEAM = 8  # plan section 3.11: a beam group never has more than 8 notes (elements)
STAFF_OF = {HAND_RIGHT: 1, HAND_LEFT: 2}


def drawn_columns(on_ms: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The group of each onset (D-04: 40 ms from the group's first onset, no chaining) and the start (ms) of its
    group. Ties are read in the given order."""
    order = np.argsort(on_ms, kind="stable")
    group = np.empty(len(on_ms), dtype=np.int64)
    start = np.empty(len(on_ms), dtype=float)
    g, first = -1, -np.inf
    for i in order:
        if on_ms[i] - first > GROUP_MS:
            g, first = g + 1, float(on_ms[i])
        group[i], start[i] = g, first
    return group, start


def from_notes(notes: Notes, *, key: int = 0) -> Sheet:
    """The notes as a frames sheet: one note per onset cell of each hand (two notes of one key, hand and cell are
    one, the longer kept, as the matrix does), drawn at the column of its group, with its measured onset (the
    group's) and length (to its own release), spelled in ``key``. A note without a hand takes one by middle C (the
    caller gives every note a hand first: the saved hands and the hand split). No figure yet."""
    live = notes.live()
    hand = live.hand.astype(np.int64).copy()
    none = hand == 0
    hand[none] = np.where(live.key[none] + LOWEST_MIDI >= 60, HAND_RIGHT, HAND_LEFT)
    cell, _ = columns_of(live, FRAME_MS)
    group, start = drawn_columns(live.on_ms)
    keep: dict[tuple[int, int, int], int] = {}
    for i in range(len(live)):
        k = (int(hand[i]), int(live.key[i]), int(cell[i]))
        if k not in keep or live.len_ms[i] > live.len_ms[keep[k]]:
            keep[k] = i
    out = []
    for i in sorted(keep.values()):
        midi = int(live.key[i]) + LOWEST_MIDI
        step, alter, octave = spell(midi, key)
        end = float(live.on_ms[i] + live.len_ms[i])
        out.append(
            Note(
                time=None,
                staff=STAFF_OF[int(hand[i])],
                step=step,
                alter=alter,
                octave=octave,
                frame=int(np.floor(round(start[i] / FRAME_MS, 9) + 0.5)),
                on_ms=float(start[i]),
                len_ms=max(end - float(start[i]), 1.0),
            )
        )
    return Sheet(notes=out, clefs={1: "G2", 2: "F4"}, key=key).sort()


def matrix_cells(notes: Notes, hands: np.ndarray | None = None) -> Counter:
    """The onset cells (staff, midi, column) of the live notes, one per hand, key and column: what the matrix of each
    hand holds. ``hands`` replaces the notes' own hands (same order as ``notes.live()``)."""
    live = notes.live()
    hand = live.hand if hands is None else np.asarray(hands)
    cell, _ = columns_of(live, FRAME_MS)
    return Counter(
        {
            (STAFF_OF.get(int(h), 0), int(k) + LOWEST_MIDI, int(c)): 1
            for h, k, c in zip(hand, live.key, cell)
        }
    )


def cells_of(sheet: Sheet, notes: Notes) -> tuple[Counter, int]:
    """The onset cell of each note of a frames sheet: the cell of its key in ``notes`` at its drawn column or the next
    one (a note is drawn at most one column before its cell), the earliest free one, each cell used once. Returns the
    cells (staff of the sheet, midi, column) and how many notes found no cell."""
    live = notes.live()
    cell, _ = columns_of(live, FRAME_MS)
    free: dict[int, list[int]] = defaultdict(list)
    for k, c in zip(live.key, cell):
        free[int(k) + LOWEST_MIDI].append(int(c))
    for v in free.values():
        v.sort()
    got: Counter = Counter()
    lost = 0
    for n in sorted(sheet.notes, key=lambda n: (n.frame, n.midi)):
        cands = free.get(n.midi, [])
        pick = next((c for c in cands if n.frame <= c <= n.frame + 1), None)
        if pick is None:
            lost += 1
            continue
        cands.remove(pick)
        got[(n.staff, n.midi, pick)] += 1
    return got, lost


def key_at(sheet: Sheet):
    """The armadura in force at a column of a frames sheet."""
    changes = sorted(sheet.key_changes)

    def at(frame: int) -> int:
        k = sheet.key or 0
        for f, kk in changes:
            if f <= frame:
                k = kk
        return k

    return at


def printed_signs(sheet: Sheet) -> dict[int, str]:
    """The sign printed before each note, ``id(note) -> "#" | "b" | "n"`` (notes with no sign are left out).

    Rule 1 (plan section 3.4, :func:`spelling.sign`): every note outside the armadura, every time. Rule 7 (the user,
    2026-10-23, a courtesy sign): when a note of the armadura got a becuadro, the first time the same note (the same
    name and octave, in the same hand) comes back to its armadura name, it prints its sostenido or bemol again, if it
    is in the same beam group as the becuadro or is the next note of the hand. The sign is redundant on purpose: it
    says that the becuadro no longer applies."""
    at = key_at(sheet)
    out: dict[int, str] = {}
    for staff in (1, 2):
        cols: dict[int, list[Note]] = defaultdict(list)
        for n in sheet.notes:
            if n.staff == staff and not n.covered:
                cols[n.frame].append(n)
        becuadro: dict[tuple[str, int], tuple[int | None, int]] = (
            {}
        )  # (step, octave) -> (beam, column index)
        for ci, (f, ns) in enumerate(sorted(cols.items())):
            key = at(f)
            for n in ns:
                s = sign(n.step, n.alter, key)
                if s:
                    out[id(n)] = s
            for n in ns:
                if out.get(id(n)) == "n":
                    continue
                seen = becuadro.pop((n.step, n.octave), None)  # only the first return counts
                back = n.alter != 0 and n.alter == key_alter(key, n.step)
                if (
                    seen
                    and back
                    and ((seen[0] is not None and seen[0] == n.beam) or ci == seen[1] + 1)
                ):
                    out[id(n)] = "#" if n.alter > 0 else "b"
            for n in ns:
                if out.get(id(n)) == "n":
                    becuadro[(n.step, n.octave)] = (n.beam, ci)
    return out


def check(sheet: Sheet) -> list[str]:
    """What breaks the rules of the product sheet (empty: a valid sheet). Each problem names its column."""
    problems: list[str] = []
    if sheet.bars:
        problems.append("the new sheet has no compases (bars)")
    key = key_at(sheet)
    by_hand: dict[int, list[Note]] = defaultdict(list)
    for n in sheet.notes:
        where = f"f{n.frame}"
        if n.time is not None or n.frame is None:
            problems.append(f"{where}: a note without a column")
            continue
        if n.staff not in (1, 2):
            problems.append(f"{where}: {n.step}{n.octave} has no hand")
            continue
        if n.figure not in FIGURES:
            problems.append(f"{where}: {n.step}{n.octave} has no plain figure ({n.figure})")
        if n.dots:
            problems.append(f"{where}: puntillo on {n.step}{n.octave}")
        if n.tuplet:
            problems.append(f"{where}: tuplet on {n.step}{n.octave}")
        if (n.step, n.alter, n.octave) != spell(n.midi, key(n.frame)):
            step, alter, octave = spell(n.midi, key(n.frame))
            problems.append(
                f"{where}: {n.step}{n.alter:+d}{n.octave} is written {step}{alter:+d}{octave} "
                f"in the armadura {key(n.frame)}"
            )
        # The clef rules (version 4): never 8va (or 15ma) in the bass clef; an 8vb under very low notes is allowed
        # (implementation 03, Phase 7: the user's octave lines of a stretch).
        if n.ottava > 0 and _clef_at(sheet, n.staff, n.frame) == "F4":
            problems.append(f"{where}: 8va in the bass clef")
        by_hand[n.staff].append(n)
    for staff, ns in by_hand.items():
        problems += _check_hand(staff, ns)
    return problems


def _clef_at(sheet: Sheet, staff: int, frame: int) -> str:
    clef = sheet.clefs.get(staff, "G2" if staff == 1 else "F4")
    for f, st, c in sorted(sheet.clef_changes, key=lambda c: c[0]):
        if st == staff and f <= frame:
            clef = c
    return clef


def _check_hand(staff: int, notes: list[Note]) -> list[str]:
    """Beam groups, grace notes and ornament onsets of one hand."""
    problems = []
    cols: dict[int, list[Note]] = defaultdict(list)
    for n in notes:
        cols[n.frame].append(n)
    frames = sorted(cols)
    hand = "R" if staff == 1 else "L"
    for f in frames:
        figs = {n.figure for n in cols[f] if not n.grace and not n.covered}
        if len(figs) > 1:
            problems.append(f"f{f} {hand}: one chord, several figures {sorted(figs)}")
    # beams: consecutive columns of this hand, no column of the hand inside left out
    members: dict[int, list[int]] = defaultdict(list)
    for i, f in enumerate(frames):
        for b in {n.beam for n in cols[f] if n.beam is not None}:
            members[b].append(i)
    for b, idx in members.items():
        if len(idx) < 2:
            problems.append(f"f{frames[idx[0]]} {hand}: beam group of one note")
        if len(idx) > MAX_BEAM:
            problems.append(
                f"f{frames[idx[0]]} {hand}: beam group of {len(idx)} notes (at most {MAX_BEAM})"
            )
        inside = range(idx[0], idx[-1] + 1)
        gaps = [i for i in inside if i not in idx and any(not n.grace for n in cols[frames[i]])]
        if gaps:
            problems.append(f"f{frames[idx[0]]} {hand}: beam group broken by f{frames[gaps[0]]}")
        for i in idx:
            for n in cols[frames[i]]:
                if n.beam == b and (n.figure or 0) < 8:
                    problems.append(f"f{frames[i]} {hand}: a {n.figure} in a beam group")
                if n.beam == b and n.grace:
                    problems.append(f"f{frames[i]} {hand}: a grace note in a beam group")
    # graces need a main note after them; ornament onsets need an ornament before them
    for i, f in enumerate(frames):
        if all(n.grace for n in cols[f]):
            nxt = next((g for g in frames[i + 1 :] if not all(n.grace for n in cols[g])), None)
            if nxt is None:
                problems.append(f"f{f} {hand}: a grace note with no note after it")
        if any(n.covered for n in cols[f]):
            before = [g for g in frames[:i] if not all(n.covered for n in cols[g])]
            if not before or not any(n.ornaments for n in cols[before[-1]]):
                problems.append(f"f{f} {hand}: 'orn' with no ornament before it")
    return problems
