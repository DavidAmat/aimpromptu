"""Spelling of the new sheet: one name per key and armadura, and the signs it prints (implementation 03, Phase 2).

Without compases there is no "an accidental lasts until the end of the compás". The user's rules (plan section 3.4)
make the name of a note a pure function of its key (the pitch) and the armadura in force:

1. every note outside the armadura carries its sign each time it appears (no memory of earlier notes);
2. a becuadro only cancels a note of the armadura;
3. no double sharps or double flats;
4. a white key is written natural, except when its natural name is in the armadura and would need a becuadro:
   then the other name of the same key with one sign, when it has one (Mi mayor: the key Fa is Mi#, the key Do is
   Si#; Fa mayor: the key Si is Dob). The keys with no other name of one sign (Sol, Re, La in Mi mayor) keep the
   becuadro;
5. a black key outside the armadura takes a sostenido in an armadura with sostenidos, a bemol in one with bemoles.

Rule 5 gives no answer in Do mayor (no armadura). Phase 2 took the research rulebook (classical scores, spell.3 to
spell.7): C# (#1), Eb (b3), F# (#4), G# (the leading tone of La menor), Bb (b7).

``check_rules`` proves on all 15 armaduras and 12 keys that the rules give one name, never a double sign, and a
becuadro only on a note of the armadura.
"""

from __future__ import annotations

from aitu_backend.sheet.sheet.pitch import STEPS

__all__ = [
    "C_MAJOR_BLACK",
    "key_alter",
    "sign",
    "signs_of",
    "spell",
    "spell_pc",
    "check_rules",
]

SHARP_ORDER = "FCGDAEB"
STEP_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
WHITE = {pc: step for step, pc in STEP_PC.items()}
#: Do mayor, black keys: pitch class -> (step, alter)
C_MAJOR_BLACK = {1: ("C", 1), 3: ("E", -1), 6: ("F", 1), 8: ("G", 1), 10: ("B", -1)}


def key_alter(key: int, step: str) -> int:
    """The alteration the armadura ``key`` (fifths: sostenidos > 0, bemoles < 0) gives to a step."""
    if key > 0:
        return int(step in SHARP_ORDER[:key])
    if key < 0:
        return -int(step in SHARP_ORDER[::-1][:-key])
    return 0


def _diatonic(key: int) -> dict[int, tuple[str, int]]:
    out = {}
    for step in STEPS:
        alter = key_alter(key, step)
        out[(STEP_PC[step] + alter) % 12] = (step, alter)
    return out


_DIATONIC = {k: _diatonic(k) for k in range(-7, 8)}


def spell_pc(pc: int, key: int) -> tuple[str, int]:
    """(step, alter) of a pitch class in an armadura, by rules 1 to 5."""
    if pc in _DIATONIC[key]:
        return _DIATONIC[key][pc]
    if pc in WHITE:  # its natural name is in the armadura (rule 4)
        if key > 0 and pc in (0, 5):  # Si# (key Do), Mi# (key Fa)
            return {0: ("B", 1), 5: ("E", 1)}[pc]
        if key < 0 and pc in (11, 4):  # Dob (key Si), Fab (key Mi)
            return {11: ("C", -1), 4: ("F", -1)}[pc]
        return WHITE[pc], 0  # no other name of one sign: becuadro (rule 2)
    if key > 0:  # rule 5
        return WHITE[pc - 1], 1
    if key < 0:
        return WHITE[(pc + 1) % 12], -1
    return C_MAJOR_BLACK[pc]


def spell(midi: int, key: int) -> tuple[str, int, int]:
    """(step, alter, octave) of a key (MIDI) in an armadura."""
    step, alter = spell_pc(midi % 12, key)
    return step, alter, (midi - STEP_PC[step] - alter) // 12 - 1


def sign(step: str, alter: int, key: int) -> str | None:
    """The sign printed before a note (rule 1: every time): ``"#"``, ``"b"``, ``"n"`` (becuadro) or ``None``."""
    if alter == key_alter(key, step):
        return None
    return {1: "#", -1: "b", 0: "n"}.get(alter, "?")


def signs_of(pcs: list[int], key: int) -> int:
    """How many signs the notes of these pitch classes print in an armadura."""
    return sum(sign(*spell_pc(pc, key), key) is not None for pc in pcs)


def check_rules() -> list[str]:
    """Problems of the rules over every armadura and key (empty: one name each, no double sign, a becuadro only
    on a note of the armadura, the same sound)."""
    problems = []
    for key in range(-7, 8):
        for pc in range(12):
            step, alter = spell_pc(pc, key)
            if (STEP_PC[step] + alter) % 12 != pc:
                problems.append(f"key {key} pc {pc}: {step}{alter} is another key")
            if abs(alter) > 1:
                problems.append(f"key {key} pc {pc}: double sign")
            s = sign(step, alter, key)
            if s == "n" and key_alter(key, step) == 0:
                problems.append(f"key {key} pc {pc}: becuadro on a note outside the armadura")
            if s in ("#", "b") and key != 0 and (s == "#") != (key > 0) and alter != 0:
                problems.append(f"key {key} pc {pc}: {s} against the armadura's family")
    return problems
