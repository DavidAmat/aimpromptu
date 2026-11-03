"""Copy this style, implementation 06, Phase 1: the matcher of the passages like the reference
(``sheet.style.match``). Code only, no AI.

The songs are written as F1 text: sections of 16 negras (a negra of 600 ms, 15 frames), a melody in corcheas and
negras in the right hand over a chord every two negras in the left hand.
"""

from __future__ import annotations

import time

import numpy as np

from aitu_backend.pmn.notes import HAND_RIGHT, Notes
from aitu_backend.sheet.levels.grid import song_grid
from aitu_backend.sheet.levels.harmony import chords
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.style import match

HEAD = "F1 frames frameMs=40 quarterMs=600\nkey=0 clefs: R=treble L=bass\n"
Q = 15  # frames per negra
SECTION = 16  # negras
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# The melody of a section: (place in corcheas, midi); 32 corcheas
VERSE = [
    (0, 76), (1, 74), (2, 72), (4, 74), (6, 76), (7, 76), (8, 76), (10, 74), (11, 74), (12, 74),
    (14, 76), (15, 79), (16, 79), (18, 77), (19, 76), (20, 74), (22, 72), (24, 71), (25, 72),
    (26, 74), (28, 72), (30, 72),
]  # fmt: skip
VERSE_CHORDS = [(48, 52, 55), (43, 50, 55), (45, 48, 52), (41, 45, 48)] * 2  # C G Am F, two negras each
BRIDGE = [
    (0, 69), (2, 69), (3, 71), (4, 72), (8, 81), (9, 79), (10, 77), (11, 76), (12, 74), (16, 65),
    (17, 67), (18, 69), (20, 71), (24, 83), (26, 81), (27, 79), (28, 78), (30, 79),
]  # fmt: skip
BRIDGE_CHORDS = [(50, 53, 57), (52, 55, 59), (41, 45, 48), (43, 47, 50)] * 2  # Dm Em F G


def name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def section(melody, harmony, start: int, *, shift: int = 0, negra: float = Q) -> dict[int, list[str]]:
    """The F1 tokens of a section from frame ``start``, ``shift`` semitones higher, ``negra`` frames per negra."""
    out: dict[int, list[str]] = {}
    for place, midi in melody:
        out.setdefault(start + round(place * negra / 2), []).append(f"R: {name(midi + shift)}:8")
    for i, chord in enumerate(harmony):
        notes = ",".join(name(m + shift) for m in chord)
        out.setdefault(start + round(2 * i * negra), []).append(f"L: {notes}:2")
    return out


def song(*parts) -> tuple:
    """A song of sections, one after the other; each part ``(melody, harmony, options)``. Returns the sheet and the
    first frame of each section."""
    tokens: dict[int, list[str]] = {}
    starts = []
    f = 30
    for melody, harmony, opts in parts:
        starts.append(f)
        for frame, items in section(melody, harmony, f, **opts).items():
            tokens.setdefault(frame, []).extend(items)
        f += round(SECTION * opts.get("negra", Q))
    text = HEAD + "".join(f"f{k} " + "  ".join(v) + "\n" for k, v in sorted(tokens.items()))
    return f1.read(text), starts


def changed(melody, at: int, midi: int):
    return [(p, midi if i == at else m) for i, (p, m) in enumerate(melody)]


def end_of(start: int, negra: float = Q) -> int:
    return start + round(SECTION * negra)


V, B = (VERSE, VERSE_CHORDS, {}), (BRIDGE, BRIDGE_CHORDS, {})


def test_an_exact_repeat_is_found_and_the_reference_is_not() -> None:
    s, at = song(V, B, V, B)
    found = match.similar(s, None, at[0], end_of(at[0]), (1,))
    assert [m.start for m in found] == [at[2]]
    m = found[0]
    assert m.score > 0.95 and m.shift == 0
    assert m.end <= end_of(at[2]) and m.end > end_of(at[2]) - Q
    # the column map pairs every column of the reference with the same place of the repeat
    assert len(m.columns) == len(VERSE)
    assert all(st == 1 and b - a == at[2] - at[0] for st, a, b in m.columns)


def test_a_repeat_with_a_note_changed_is_found_with_a_lower_score() -> None:
    s, at = song(V, B, V, B, (changed(VERSE, 10, 79), VERSE_CHORDS, {}))
    found = {m.start: m for m in match.similar(s, None, at[0], end_of(at[0]), (1,))}
    assert at[2] in found and at[4] in found
    assert found[at[4]].score < found[at[2]].score
    assert found[at[4]].score >= match.THRESHOLD


def test_a_repeat_a_tone_higher_is_found_with_its_shift() -> None:
    s, at = song(V, B, (VERSE, VERSE_CHORDS, {"shift": 2}), B)
    found = match.similar(s, None, at[0], end_of(at[0]), (1, 2))
    assert [(m.start, m.shift) for m in found] == [(at[2], 2)]
    assert found[0].parts["classes"] > 0.95 and found[0].parts["harmony"] > 0.95
    # without the shifts searched, the same place scores much less
    flat = match.ranked(s, None, at[0], end_of(at[0]), (1, 2), shifts=(0,), floor=0.0)
    there = [m for m in flat if m.overlaps(at[2], end_of(at[2]))]
    assert there and there[0].score < found[0].score - 0.2


def test_another_passage_is_not_found() -> None:
    s, at = song(V, B, V, B)
    found = match.similar(s, None, at[1], end_of(at[1]), (1,))
    assert [m.start for m in found] == [at[3]]  # the other bridge, never a verse
    below = match.ranked(s, None, at[1], end_of(at[1]), (1,), floor=0.0)
    verses = [m for m in below if m.overlaps(at[0], end_of(at[0])) or m.overlaps(at[2], end_of(at[2]))]
    assert verses and all(m.score < match.THRESHOLD for m in verses)


def test_a_cover_a_little_faster_is_found() -> None:
    fast = Q * 0.9
    s, at = song(V, B, V, B, (VERSE, VERSE_CHORDS, {"negra": fast}), B)
    found = {m.start: m for m in match.similar(s, None, at[0], end_of(at[0]), (1,))}
    assert at[4] in found and found[at[4]].score >= match.THRESHOLD
    m = found[at[4]]
    assert end_of(at[4], fast) - Q <= m.end <= end_of(at[4], fast)


def test_both_hands_and_one_hand() -> None:
    # the same melody over other chords: like the reference in the right hand, not in both hands
    s, at = song(V, B, (VERSE, BRIDGE_CHORDS, {}), B)
    right = match.ranked(s, None, at[0], end_of(at[0]), (1,), floor=0.0, limit=3)
    both = match.ranked(s, None, at[0], end_of(at[0]), (1, 2), floor=0.0, limit=3)
    r = next(m for m in right if m.start == at[2])
    b = next(m for m in both if m.start == at[2])
    assert b.score < r.score
    assert {st for st, _, _ in b.columns} == {1, 2}


def test_the_notes_taken_off_the_reference_count_as_played() -> None:
    # the user made the first chord of the reference two notes: its top note is marked removed in notes.pmn
    s, at = song(V, B, V, B)
    ref = [n for n in s.notes if n.staff == 2 and n.frame == at[0]]
    top = max(ref, key=lambda n: n.midi)
    s.notes.remove(top)
    taken = Notes.build([top.midi - 21], [at[0] * 40.0 + 15], [500.0], hand=[2], removed=[True])
    def repeat(notes):
        return next(m for m in match.similar(s, notes, at[0], end_of(at[0]), (2,)) if m.start == at[2])

    live, played = repeat(None), repeat(taken)
    assert played.score > live.score
    # a removed note of the other hand changes nothing of the left hand
    other = Notes.build([top.midi - 21 + 24], [at[0] * 40.0], [500.0], hand=[HAND_RIGHT], removed=[True])
    assert repeat(other).score == live.score


def test_the_places_do_not_overlap_and_stop_at_the_limit() -> None:
    s, at = song(V, B, V, B, V, B, V)
    found = match.similar(s, None, at[0], end_of(at[0]), (1,), limit=2)
    assert len(found) == 2
    every = match.ranked(s, None, at[0], end_of(at[0]), (1,), floor=0.0)
    spans = sorted((m.start, m.end) for m in every)
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:]))
    assert not any(m.overlaps(at[0], end_of(at[0])) for m in every)


def test_a_song_of_four_minutes_is_searched_in_well_under_a_second() -> None:
    parts = [V, B] * 13  # 26 sections of 9.6 s: about 4 minutes
    s, at = song(*parts)
    assert at[-1] * 40 / 1000 > 230
    g = song_grid(s)
    cs = chords(s, g)
    for staffs in ((1,), (2,), (1, 2)):
        t = time.perf_counter()
        found = match.similar(s, None, at[2], end_of(at[2]), staffs, grid=g, harmony=cs)
        seconds = time.perf_counter() - t
        assert seconds < 0.5, seconds
        assert len(found) == match.STYLE_MAX
    # a long reference (four sections, about 38 s)
    t = time.perf_counter()
    match.similar(s, None, at[2], end_of(at[5]), (1, 2), grid=g, harmony=cs)
    assert time.perf_counter() - t < 0.5


def test_no_column_in_the_reference_finds_nothing() -> None:
    s, at = song(V, B)
    assert match.similar(s, None, 10_000, 10_100, (1,)) == []
    assert np.isclose(sum(match.WEIGHTS.values()), 1.0)
