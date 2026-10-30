"""The whole song simplification by levels (implementation 04-3, Phase 3): the grid, the chords, the measures of the
hand tracker, the prompts, the plan of the song and the check of a level answer, with recorded answers (no AI)."""

from __future__ import annotations

import re

from aitu_backend.sheet.levels import grid as grid_mod
from aitu_backend.sheet.levels.grid import song_grid
from aitu_backend.sheet.levels.hands import measure, melody, track
from aitu_backend.sheet.levels.harmony import chords
from aitu_backend.sheet.llm import levels as L
from aitu_backend.sheet.sheet import f1

HEAD = "F1 frames frameMs=40 quarterMs=600\nkey=0 clefs: R=treble L=bass\n"
Q = 15  # frames per negra at quarterMs=600

# C major for 4 negras, then G major, then A minor, then F major, twice: a melody in negras over chords in negras
PROG = [("C3,E3,G3", "C2"), ("B2,D3,G3", "G2"), ("A2,C3,E3", "A2"), ("A2,C3,F3", "F2")]
MELODY = ["E5", "D5", "C5", "D5", "D5", "B4", "G4", "B4", "C5", "E5", "A4", "C5", "C5", "A4", "F4", "A4"]


def song(left: str = "chords"):
    lines = []
    for k in range(32):
        f = 30 + k * Q
        chord, bass = PROG[(k // 4) % 4]
        mel = MELODY[k % 16]
        lh = f"{bass},{chord}:4" if left == "wide" else f"{chord}:4"
        lines.append(f"f{f} L: {lh}  R: {mel}:4")
    return f1.read(HEAD + "\n".join(lines) + "\n")


def answer(lines: list[str], declared: list[str]) -> str:
    return "```\n" + HEAD + "\n".join(lines + declared) + "\n```"


def easy_lines(s, start: int = 30, end: int = 30 + 32 * Q, *, skip: set[int] = frozenset(), bass_octave: int = 2):
    """The melody in single notes; the bass of each chord on its first negra, then the triad held."""
    out = []
    for k in range(32):
        f = 30 + k * Q
        if not start <= f < end:
            continue
        chord, bass = PROG[(k // 4) % 4]
        bass = bass[:-1] + str(bass_octave)
        r = "" if k in skip else f"  R: {MELODY[k % 16]}:4"
        left = f"L: {bass}:4" if k % 4 == 0 else f"L: {chord}:2" if k % 4 == 1 else ""
        if left or r:
            out.append(f"f{f} {left}{r}".rstrip())
    return out


def checked(reply, s, level="easy", staffs=(1, 2), allowed=("left easy 2", "right easy 2"), start=30, end=30 + 32 * Q):
    g = song_grid(s)
    cs = chords(s, g)
    return L.check_level(
        reply, s, level=level, staffs=staffs, grid=g, cs=cs, allowed=set(allowed), start=start, end=end
    )


DECLARED = ["# pattern L f30-f510: left easy 2", "# pattern R f30-f510: right easy 2"]


# ------------------------------------------------------------------ the grid


def test_the_grid_follows_a_steady_negra_and_divides_it_in_two() -> None:
    g = song_grid(song())
    assert g.division == 2
    negras = g.points(30, 1000, "negra")
    assert negras[:3] == [30, 45, 60]
    corcheas = g.points(30, 61, "corchea")
    assert corcheas == [30, 38, 45, 52, 60] or corcheas == [30, 37, 45, 52, 60]
    assert g.on_grid(45) and g.on_grid(46) and g.on_grid(52, "corchea")
    assert not g.on_grid(41, "corchea")
    assert g.kind_of(30) == "negra"
    assert g.text(30, 61).startswith("f30 (f3")
    assert g.points(495, 530, "negra") == [495, 510, 525]  # the grid goes on after the last onset


def test_a_ternary_song_divides_the_negra_in_three() -> None:
    lines = [f"f{30 + k * 5} R: {'C5' if k % 3 == 0 else 'E5'}:8" for k in range(60)]
    lines += [f"f{30 + k * 15} L: C3:4" for k in range(20)]
    by = {}
    for line in lines:
        f, rest = line.split(" ", 1)
        by.setdefault(int(f[1:]), []).append(rest)
    text = HEAD + "\n".join(f"f{f} " + "  ".join(sorted(v)) for f, v in sorted(by.items())) + "\n"
    g = song_grid(f1.read(text))
    assert g.division == 3
    assert g.on_grid(35, "corchea") and g.on_grid(40, "corchea")


# ------------------------------------------------------------------ the chords


def test_the_chords_are_found_from_the_notes_and_join_into_stretches() -> None:
    s = song("wide")
    cs = chords(s, song_grid(s))
    names = [c.name() for c in cs]
    assert names[:4] == ["C", "G", "Am", "F"]
    assert cs[0].start == 30 and cs[1].start == 30 + 4 * Q
    assert cs[0].bass == 0 and cs[2].bass == 9


# ------------------------------------------------------------------ the measures


def test_a_held_triad_does_not_move_and_octave_jumps_do() -> None:
    still = track([0, 0.5, 1.0, 1.5], [[53, 57, 60]] * 4)
    assert still.moves == []
    jumps = track([0, 0.5, 1.0, 1.5], [[41], [65], [41], [65]])
    assert len(jumps.moves) == 3


def test_the_measures_of_a_hand() -> None:
    s = song("wide")
    g = song_grid(s)
    m = measure(s, 2, 30, 30 + 32 * Q, g)
    assert m.chord_max == 4 and m.span >= 19
    assert m.columns == 32 and abs(m.notes_s - 120 / m.seconds) < 0.01  # A2 is the bass and the root of Am
    assert m.moves_q == m.moves / (m.seconds * 1000 / 600)
    r = measure(s, 1, 30, 30 + 32 * Q, g)
    assert r.chord_max == 1 and r.span == 0
    assert [n.midi for n in melody(s)][:3] == [76, 74, 72]


# ------------------------------------------------------------------ the patterns and the prompts


def test_the_words_name_patterns_with_or_without_a_hand() -> None:
    assert L.refs_in("at the start apply medium 2; at frame 112 use left hard 3", ("left",)) == [
        "left medium 2",
        "left hard 3",
    ]
    assert L.refs_in("easy 1 everywhere") == ["left easy 1", "right easy 1"]


def _pattern(ref: str) -> L.Pattern:
    hand, level, number = ref.split(" ")
    return L.Pattern(ref, hand, level, int(number), f"name {ref}", "a line", HEAD + "f0 L: F2:4  R: A4:4\nf12 L: F3,A3,C4:2\n")


def test_the_system_prompt_has_the_level_and_only_the_patterns_of_the_run() -> None:
    text = L.system_prompt("easy", [_pattern("right easy 2"), _pattern("left easy 2")])
    assert "# The level of this run: easy" in text and "# The level of this run: medium" not in text
    assert text.index("### left easy 2") < text.index("### right easy 2")
    assert "left easy 1" not in text.split("# The patterns of this run")[1]
    assert L.LEVEL_VERSION == "1"


def test_the_examples_of_the_shared_prompt_parse() -> None:
    text = (L.PROMPT_DIR / "shared.md").read_text()
    block = re.search(r"```\n(F1 frames.*?)```", text, re.S).group(1)
    sheet = f1.read(block)
    assert len(sheet.notes) == 7
    d = L.read_declared(block)
    assert ("L", 1042, 1440, "left easy 2") in d.patterns
    assert [k for _, _, k, _, _ in d.dropped] == ["not melody", "artifact"]


# ------------------------------------------------------------------ the plan of the song


def test_a_plan_covers_the_song_with_allowed_patterns() -> None:
    allowed = {"left easy 2", "right easy 2", "left easy 1"}
    good = "```\nS1 f30-f270 L=left easy 2 R=right easy 2 | the verse\nS2 f270-f510 L=left easy 1 R=right easy 2 | the chorus\n```"
    errs, plan = L.read_plan(good, allowed, (1, 2), 30, 510)
    assert errs == [] and [s.left for s in plan] == ["left easy 2", "left easy 1"]
    gap = "S1 f30-f260 L=left easy 2 R=right easy 2\nS2 f270-f510 L=left easy 3 R=right easy 2"
    errs, _ = L.read_plan(gap, allowed, (1, 2), 30, 510)
    assert any("no gap" in e for e in errs) and any("left easy 3 is not a pattern" in e for e in errs)
    one = "S1 f30-f510 L=left easy 2 R=right easy 2"
    errs, _ = L.read_plan(one, allowed, (2,), 30, 510)
    assert any("stays as it is" in e for e in errs)


def test_the_plan_prompt_and_the_summary() -> None:
    s = song("wide")
    g = song_grid(s)
    summary, rows = L.song_summary(s, g, (1, 2))
    assert rows and summary.count("\n") == len(rows) - 1
    assert "chords C G Am F" in summary.splitlines()[0]
    text = L.plan_prompt(sid="t", level="easy", staffs=(2,), summary=summary, start=30, end=510)
    assert "the left hand only" in text and "The right hand stays exactly as it is" in text


# ------------------------------------------------------------------ the check of a batch


def test_a_clean_easy_answer_passes() -> None:
    s = song("wide")
    r = checked(answer(easy_lines(s), DECLARED), s)
    assert r.errors == []
    assert r.melody == 32 and r.measures[2].chord_max == 3
    assert r.new_notes == 0  # every note of this answer is a note of the song at its frame


def test_a_melody_note_left_out_must_be_declared_and_far_or_alone_for_an_artifact() -> None:
    s = song("wide")
    r = checked(answer(easy_lines(s, skip={5}), DECLARED), s)
    assert any("1 notes of the melody line are missing: f105 B4" in e for e in r.errors)
    said = DECLARED + ["# artifact f105 B4: high"]
    r = checked(answer(easy_lines(s, skip={5}), said), s)
    assert any("declared artifacts are part of the melody line" in e for e in r.errors)
    said = DECLARED + ["# not melody f105 B4: a fill"]
    assert checked(answer(easy_lines(s, skip={5}), said), s).errors == []


def test_a_high_chord_alone_is_an_artifact() -> None:
    s = song("wide")
    high = f1.read(f1.write(s, mode="frames").rstrip("\n") + "\nf540 R: D#7,E7:4\n")
    declared = ["# pattern L f30-f600: left easy 2", "# pattern R f30-f600: right easy 2"]
    r = checked(answer(easy_lines(high), declared + ["# artifact f540 D#7,E7: a high chord alone"]), high, end=600)
    assert r.errors == [] and r.melody_dropped == 1
    r = checked(answer(easy_lines(high), declared), high, end=600)
    assert any("missing: f540 E7" in e for e in r.errors)


def test_the_bass_and_the_chords_are_kept() -> None:
    s = song("wide")
    lines = [line.replace("L: G2:4", "L: E2:4") for line in easy_lines(s)]
    r = checked(answer(lines, DECLARED), s)
    assert any("chords begin on another bass" in e and "G" in e for e in r.errors)
    lines = [line.replace("L: C3,E3,G3:2", "L: C#3,F3,G#3:2") for line in easy_lines(s)]
    r = checked(answer(lines, DECLARED), s)
    assert any("outside the chords of the song" in e for e in r.errors)


def test_the_level_limits_per_column_and_hand_motion() -> None:
    s = song("wide")
    wide = [line.replace("L: C3,E3,G3:2", "L: C3,E3,G3,C4:2") for line in easy_lines(s)]
    r = checked(answer(wide, DECLARED), s)
    assert any(e.startswith("L: 2 columns are beyond the level") for e in r.errors)
    assert checked(answer(wide, [d.replace("easy", "hard") for d in DECLARED]), s, level="hard",
                   allowed=("left hard 2", "right hard 2")).errors == []
    chords_r = [line.replace("R: E5:4", "R: C5,E5:4") for line in easy_lines(s)]
    assert any(e.startswith("R: 4 columns are beyond") for e in checked(answer(chords_r, DECLARED), s).errors)
    jumpy = []
    for k in range(32):
        f = 30 + k * Q
        chord, bass = PROG[(k // 4) % 4]
        jumpy.append(f"f{f} L: {bass[:-1]}1:8  R: {MELODY[k % 16]}:4")
        jumpy.append(f"f{f + 7} L: {chord}:8")
    r = checked(answer(jumpy, DECLARED), s)
    assert any("times per negra" in e for e in r.errors)


def test_patterns_must_be_declared_and_allowed_and_new_notes_on_the_grid() -> None:
    s = song("wide")
    r = checked(answer(easy_lines(s), ["# pattern R f30-f510: right easy 2"]), s)
    assert any("declare the pattern of the left hand" in e for e in r.errors)
    r = checked(answer(easy_lines(s), ["# pattern L f30-f510: left easy 9", DECLARED[1]]), s)
    assert any("left easy 9 is not a pattern of this run" in e for e in r.errors)
    off = easy_lines(s) + ["f41 L: E3:16"]
    r = checked(answer(sorted(off, key=lambda t: int(t.split()[0][1:])), DECLARED), s)
    assert any("not on the grid: f41 E3" in e for e in r.errors)
    fast = easy_lines(s) + ["f38 L: E3:32"]
    r = checked(answer(sorted(fast, key=lambda t: int(t.split()[0][1:])), DECLARED), s)
    assert any("shorter than the level allows" in e for e in r.errors)


def test_a_run_of_one_hand_refuses_the_other_hand() -> None:
    s = song("wide")
    r = checked(answer(easy_lines(s), DECLARED), s, staffs=(2,), allowed=("left easy 2",))
    assert any("the right hand is fixed" in e for e in r.errors)


# ------------------------------------------------------------------ a run in memory, with recorded answers


def test_a_level_run_plans_then_writes_each_batch_with_feedback() -> None:
    s = song("wide")
    plan = "```\nS1 f30-f496 L=left easy 2 R=right easy 2 | one section\n```"
    bad = answer(easy_lines(s, 30, 270, skip={1}), ["# pattern L f30-f270: left easy 2", "# pattern R f30-f270: right easy 2"])
    good1 = answer(easy_lines(s, 30, 270), ["# pattern L f30-f270: left easy 2", "# pattern R f30-f270: right easy 2"])
    good2 = answer(easy_lines(s, 270, 510), ["# pattern L f270-f510: left easy 2", "# pattern R f270-f510: right easy 2"])
    replies = [plan, bad, good1, good2]
    seen: list[tuple[str, list[dict]]] = []

    def complete(system: str, messages: list[dict]) -> str:
        seen.append((system, messages))
        return replies[len(seen) - 1]

    run = L.write_level(
        s,
        complete,
        song_grid(s),
        level="easy",
        staffs=(1, 2),
        patterns=[_pattern("left easy 2"), _pattern("right easy 2")],
        windows=[(30, 270), (270, 510)],
    )
    assert run.plan_log.status == "ok" and len(run.plan) == 1
    assert [log.status for log, _ in run.batches] == ["ok", "ok"]
    assert run.batches[0][0].replies == 2
    assert "melody line are missing" in seen[2][1][-1]["content"]
    assert len({system for system, _ in seen}) == 1  # one system prompt for the run: cached
    assert "Decided context" in seen[3][1][0]["content"]
    assert len(run.written.notes) == len(f1.read(_block(good1)).notes) + len(f1.read(_block(good2)).notes)
    drawn = L.drawn(run.written, 600.0, key=0)
    assert {n.staff for n in drawn.notes} == {1, 2} and all(n.figure for n in drawn.notes)


def _block(reply: str) -> str:
    return reply.split("```\n")[1].split("```")[0]


def test_the_grid_tolerance_is_one_frame() -> None:
    assert grid_mod.TOLERANCE == 1


def test_a_level_per_hand_takes_each_hand_part_and_its_limits() -> None:
    level = {"right": "hard", "left": "medium"}
    text = L.system_prompt(level, [_pattern("left medium 2"), _pattern("right hard 1")])
    assert "## The right hand at hard" in text and "## The left hand at medium" in text
    assert "## The left hand at hard" not in text and "## The right hand at medium" not in text
    assert "hard for the right hand, medium for the left hand" in text.replace("levels of this run: ", "")
    assert L.level_name(level) == "hard for the right hand and medium for the left hand"
    s = song("wide")
    lines = [line.replace("R: E5:4", "R: G4,C5,E5:4") for line in easy_lines(s)]  # a three-note chord: hard only
    declared = ["# pattern L f30-f510: left medium 2", "# pattern R f30-f510: right hard 1"]
    allowed = ("left medium 2", "right hard 1")
    assert checked(answer(lines, declared), s, level=level, allowed=allowed).errors == []
    wide = [line.replace("L: C3,E3,G3:2", "L: C3,E3,G3,C4:2") for line in lines]  # four notes: not medium
    r = checked(answer(wide, declared), s, level=level, allowed=allowed)
    assert any(e.startswith("L: 2 columns are beyond the level") for e in r.errors)


def test_where_the_right_hand_has_only_an_artifact_the_left_hand_tops_go_to_the_right_hand() -> None:
    lines = [f"f{30 + k * Q} L: E2,E3,B3,{'E4' if k % 2 == 0 else 'C#4'}:4" for k in range(8)]
    riff = f1.read(HEAD + "\n".join(lines[:3] + ["f75 L: E2,E3,B3,C#4:4  R: D#7,E7:4"] + lines[4:]) + "\n")
    declared = ["# pattern L f30-f150: left medium 2", "# pattern R f30-f150: right hard 1", "# artifact f75 D#7,E7: high"]
    kept_low = [f"f{30 + k * Q} L: E2:4" for k in range(8)]
    r = checked(answer(kept_low, declared), riff, level={"right": "hard", "left": "medium"},
                allowed=("left medium 2", "right hard 1"), start=30, end=150)
    assert any("top notes of the left-hand chords are missing from the right hand" in e for e in r.errors)
    taken = [f"f{30 + k * Q} L: E2:4  R: {'E4' if k % 2 == 0 else 'C#4'}:4" for k in range(8)]
    r = checked(answer(taken, declared), riff, level={"right": "hard", "left": "medium"},
                allowed=("left medium 2", "right hard 1"), start=30, end=150)
    assert not any("top notes" in e for e in r.errors), r.errors


def test_a_simple_left_hand_keeps_its_notes_and_only_a_regular_rhythm() -> None:
    uneven = [30, 34, 37, 45, 49, 53, 60, 64, 75, 79, 83, 90]
    mel = {30: "E5", 45: "D5", 60: "C5", 75: "D5", 90: "E5"}
    lines = [f"f{f} L: C3:16" + (f"  R: {mel[f]}:4" if f in mel else "") for f in uneven]
    s = f1.read(HEAD + "\n".join(lines) + "\n")
    declared = ["# pattern L f30-f105: keep", "# pattern R f30-f105: right easy 2"]
    kept = [f"f{f} L: C3:4  R: {m}:4" for f, m in mel.items()]
    assert checked(answer(kept, declared), s, start=30, end=105).errors == []
    added = [f"f{f} L: {'C2' if f % 30 == 0 else 'E3,G3'}:4  R: {m}:4" for f, m in mel.items()]
    r = checked(answer(added, declared), s, start=30, end=105)
    assert any("simple stretches are made harder" in e and "adds" in e for e in r.errors)
    assert "L simple (keep): f30-f" in L.song_summary(s, song_grid(s), (1, 2))[0]


def test_the_left_hand_follows_its_rhythm_now() -> None:
    s = song("wide")  # the left hand plays on every negra
    more = []
    for k in range(32):
        f = 30 + k * Q
        chord, bass = PROG[(k // 4) % 4]
        more.append(f"f{f} L: {bass}:8  R: {MELODY[k % 16]}:4")
        more.append(f"f{f + 7} L: {chord.split(',')[1]}:8")
    r = checked(answer(more, DECLARED), s)
    assert any("more left-hand onsets than the sheet now" in e for e in r.errors)
    assert any("onsets of the left hand now" in e for e in r.errors)


def test_easy_and_medium_keep_a_steady_rhythm_and_a_melody_note_may_move_to_the_grid() -> None:
    s = song("wide")
    quick = f1.read(f1.write(s, mode="frames").replace("f45 ", "f42 R: G5:32\nf45 ", 1))
    lines = easy_lines(quick)
    with_quick = sorted(lines + ["f42 R: G5:32"], key=lambda t: int(t.split()[0][1:]))
    r = checked(answer(with_quick, DECLARED), quick)
    assert any("pairs of notes closer than a semicorchea" in e for e in r.errors)
    assert any("shorter than the level allows" in e for e in r.errors)
    moved = sorted(lines + ["f38 R: G5:16"], key=lambda t: int(t.split()[0][1:]))  # G5 to the semicorchea at f38
    r = checked(answer(moved, DECLARED), quick)
    assert r.errors == [], r.errors
