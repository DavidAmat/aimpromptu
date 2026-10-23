"""Small pieces shared by the text formats: key signatures, figures, tuplet groups, beam numbering."""

from __future__ import annotations

from fractions import Fraction

from aitu_backend.sheet.sheet.data import Note

__all__ = [
    "ORN_NAMES",
    "ORN_CODES",
    "figure_quarters",
    "key_text",
    "parse_key",
    "renumber_beams",
    "rebuild_tuplet_groups",
    "spn",
    "parse_spn",
]

ORN_NAMES = {
    "arpeggio": "arp",
    "trill": "tr",
    "tremolo": "trem",
    "fermata": "ferm",
    "mordent": "mord",
    "turn": "turn",
}
ORN_CODES = {v: k for k, v in ORN_NAMES.items()}
_ACC = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}
_ACC_CODES = {v: k for k, v in _ACC.items()}


def key_text(fifths: int) -> str:
    """3 -> "3#", -2 -> "2b", 0 -> "0"."""
    return "0" if fifths == 0 else f"{abs(fifths)}{'#' if fifths > 0 else 'b'}"


def parse_key(text: str) -> int:
    if text == "0":
        return 0
    n, sign = int(text[:-1]), text[-1]
    return n if sign == "#" else -n


def spn(step: str, alter: int, octave: int) -> str:
    """Scientific pitch name with the spelled accidental: ("C", 1, 4) -> "C#4", ("B", -1, 2) -> "Bb2"."""
    return f"{step}{_ACC[alter]}{octave}"


def parse_spn(text: str) -> tuple[str, int, int]:
    step = text[0]
    rest = text[1:]
    i = 0
    while i < len(rest) and rest[i] in "#b":
        i += 1
    acc, octave = rest[:i], rest[i:]
    if step not in "CDEFGAB" or acc not in _ACC_CODES or not octave.lstrip("-").isdigit():
        raise ValueError(f"not a pitch: {text!r}")
    return step, _ACC_CODES[acc], int(octave)


def figure_quarters(figure: int | None, dots: int) -> Fraction:
    """Written length of a figure in quarters (dots applied, tuplets not)."""
    if figure is None:
        return Fraction(0)
    base = Fraction(8) if figure == 0 else Fraction(16) if figure == -1 else Fraction(4, figure)
    return base * (2 - Fraction(1, 2**dots))


def renumber_beams(notes: list[Note]) -> dict[int, int]:
    """Beam numbers 1, 2, 3 ... in the order of the first note of each beam (``notes`` in text order)."""
    out: dict[int, int] = {}
    for n in notes:
        if n.beam is not None and n.beam not in out:
            out[n.beam] = len(out) + 1
    return out


def rebuild_tuplet_groups(notes: list[Note], *, whole_beam: bool = True) -> None:
    """Fill ``Note.tgroup`` from the tuplet ratios and the beams (the formats do not write groups).

    Tuplet notes are read per hand and per beam (unbeamed ones per hand), in time order; a chord is
    one element. A group closes at the first element where the written length so far is the ratio's
    numerator times a figure at least as long as the shortest note (3 eighths, 2 eighths of a duplet,
    11 sixteenths), or before a hole in time or a change of ratio. With ``whole_beam``, a group that is
    complete in the middle of its beam stays open when the whole beam is also complete (one group of
    6 triplet sixteenths instead of 3 + 3)."""
    seqs: dict[tuple, list[Note]] = {}
    for n in notes:
        n.tgroup = None
        if n.tuplet and not n.grace:
            seqs.setdefault((n.staff, n.beam), []).append(n)
    counter = 0
    for seq in seqs.values():
        when = (lambda n: n.time) if seq[0].time is not None else (lambda n: n.frame)
        seq.sort(key=lambda n: (when(n), n.midi))
        elements: list[list[Note]] = []
        for n in seq:
            if elements and when(elements[-1][0]) == when(n) and elements[-1][0].tuplet == n.tuplet:
                elements[-1].append(n)
            else:
                elements.append([n])
        i = 0
        while i < len(elements):
            end = _group_end(elements, i, whole_beam)
            counter += 1
            for el in elements[i : end + 1]:
                for n in el:
                    n.tgroup = counter
            i = end + 1


def _group_end(elements: list[list[Note]], i: int, whole_beam: bool) -> int:
    ratio = Fraction(elements[i][0].tuplet)
    written = Fraction(0)
    shortest = None
    first_complete = None
    j = i
    while j < len(elements):
        el = elements[j][0]
        if Fraction(el.tuplet) != ratio or (j > i and _hole(elements[j - 1][0], el, ratio)):
            break
        length = figure_quarters(el.figure, el.dots)
        written += length
        shortest = length if shortest is None else min(shortest, length)
        unit = written / ratio.numerator
        if _power_of_two(unit) and unit >= shortest:
            if first_complete is None:
                first_complete = j
            if not whole_beam or el.beam is None:
                return j
        j += 1
    if first_complete is None:
        return j - 1
    if whole_beam:
        # the last complete point inside the run decides: the whole run if it ends complete
        last = first_complete
        written = Fraction(0)
        shortest = None
        for k in range(i, j):
            el = elements[k][0]
            length = figure_quarters(el.figure, el.dots)
            written += length
            shortest = length if shortest is None else min(shortest, length)
            unit = written / ratio.numerator
            if _power_of_two(unit) and unit >= shortest:
                last = k
        return last if last == j - 1 else first_complete
    return first_complete


def _hole(a: Note, b: Note, ratio: Fraction) -> bool:
    """True when ``b`` starts after the end of ``a`` (a rest or another voice in between)."""
    if a.time is None or b.time is None:
        return False
    return a.time + figure_quarters(a.figure, a.dots) / ratio < b.time


def _power_of_two(x: Fraction) -> bool:
    if x <= 0:
        return False
    n, d = x.numerator, x.denominator
    return (n & (n - 1) == 0) and (d & (d - 1) == 0)
