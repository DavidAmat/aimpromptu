"""Find two notes trading places quickly, and offer to print them as one ``tr``.

A trill is written as one held note with ``tr`` over it. Written literally it is a storm of
noteheads that says nothing a reader can use: twenty beamed semicorcheas where the music means
"hold this note and shake it".

The rule here is deliberately the smallest one that works. **Two notes a whole tone or less apart,
taking turns, with the pair repeated at least three times** — Si-Do-Si-Do-Si-Do — **at an even,
quick speed.** Nothing about harmony, nothing about where the run sits in the bar.

Two things this is not:

* **It is not a rewrite.** Detection returns suggestions. The reader accepts one and it becomes a
  mark in ``rhythm.json``; until then the notes print as they were played. A missed trill costs
  nothing and a wrong one hides real notes, so the asymmetry decides who has the last word (D-17).
* **It is not measured on the grid.** The gaps come from the raw attack times, the same times
  Phase 2 measures (D-07). A trill can easily run faster than one column, and a detector reading
  column numbers would see a flat line of identical gaps and call anything a trill.

The notes themselves are never touched. ``events.json`` still holds every alternation, playback
still sounds all of them (D-29), and removing the mark prints them again exactly as they were.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from aitu_backend.notation.figures import onset_columns
from aitu_backend.schemas.time_matrix import PrintedHand

MS_PER_SECOND = 1000.0

#: How many times the pair has to come round. Three means six notes: Si-Do-Si-Do-Si-Do.
MIN_PAIR_REPEATS = 3

#: How far apart the two notes may be, in semitones. A whole tone; a trill is a second, and a
#: third apart is a tremolo, which is written differently and is not offered here.
MAX_SEMITONES = 2

#: Longest gap that still reads as a trill rather than as two notes being played. 300 ms is a
#: little over three alternations a second, which is slow for a trill and safely fast for a melody.
MAX_GAP_MS = 300.0

#: How uneven the alternation may be, as a share of the run's first gap. A trill played by a hand
#: is not a metronome, but it is not a phrase either: 0.6 lets a gap wander from 40% to 160% of the
#: first one and stops a run of unrelated notes from being swept in because two of them happened to
#: alternate.
EVENNESS = 0.6


@dataclass(frozen=True)
class TrillRun:
    """One stretch where two notes alternate, as the detector found it."""

    hand: PrintedHand
    #: The column the run starts in. The ``tr`` is printed here.
    start_frame: int
    #: One past the column of the run's **last onset**. The held note is drawn across the whole
    #: stretch, so the mark's own end also depends on how long that last note sounds.
    end_frame: int
    #: The lower of the two notes: the one that stays on the page. ``tr`` means "alternate with the
    #: note above", so the lower one is the note actually written.
    row: int
    #: The upper of the two. Kept so the panel can say which two notes it found.
    other_row: int
    #: How many onsets the run holds. Six or more, by construction.
    note_count: int
    #: The middle gap of the run, in milliseconds. What the panel shows as its speed.
    median_gap_ms: float

    @property
    def pair_repeats(self) -> int:
        """How many times the pair came round. Six notes are three repeats."""
        return self.note_count // 2


def detect_trills(
    hands,
    *,
    min_pair_repeats: int = MIN_PAIR_REPEATS,
    max_semitones: int = MAX_SEMITONES,
    max_gap_ms: float = MAX_GAP_MS,
    evenness: float = EVENNESS,
) -> list[TrillRun]:
    """Every alternating run in either hand, longest-first within each hand.

    ``hands`` is a :class:`~aitu_backend.transcription.time_pipeline.TimeHands`. Imported lazily by
    duck typing rather than by name, because ``time_pipeline`` already imports this module's
    neighbour and a straight import would close the circle.
    """
    from aitu_backend.transcription.time_pipeline import attack_seconds_of_hand

    found: list[TrillRun] = []
    hand: PrintedHand
    for hand in ("right", "left"):
        matrix = hands.right if hand == "right" else hands.left
        seconds_at = attack_seconds_of_hand(hands, hand)
        attacks = _single_note_attacks(matrix, seconds_at, hands.frame_ms)
        found.extend(
            _runs_in(
                attacks,
                hand,
                min_pair_repeats=min_pair_repeats,
                max_semitones=max_semitones,
                max_gap_ms=max_gap_ms,
                evenness=evenness,
            )
        )
    return found


@dataclass(frozen=True)
class _Attack:
    column: int
    seconds: float
    #: ``None`` for a chord. A chord cannot be half of a trill, and it ends any run it lands in.
    row: int | None


def _single_note_attacks(matrix, seconds_at: dict[int, float], frame_ms: float) -> list[_Attack]:
    """Every attack in one hand, in order, with the raw time it was played at.

    Chords stay in the list with ``row = None`` instead of being dropped. They have to: a chord in
    the middle of an alternation is the end of that alternation, and a detector that could not see
    it would join the runs on either side of it.
    """
    attacks: list[_Attack] = []
    for column in onset_columns(matrix):
        rows = list(matrix.onsets_in_column(column))
        attacks.append(
            _Attack(
                column=column,
                seconds=seconds_at.get(column, (column + 0.5) * frame_ms / MS_PER_SECOND),
                row=rows[0] if len(rows) == 1 else None,
            )
        )
    return attacks


def _runs_in(
    attacks: list[_Attack],
    hand: PrintedHand,
    *,
    min_pair_repeats: int,
    max_semitones: int,
    max_gap_ms: float,
    evenness: float,
) -> list[TrillRun]:
    """Walk the hand once, taking the longest run that starts at each position.

    Runs never overlap: after one is taken the walk resumes at its last note, so a long trill
    cannot be reported as several shorter ones sharing notes.
    """
    minimum_notes = min_pair_repeats * 2
    runs: list[TrillRun] = []
    index = 0
    while index + minimum_notes <= len(attacks):
        end, gaps, pair = _extend(
            attacks,
            index,
            max_semitones=max_semitones,
            max_gap_ms=max_gap_ms,
            evenness=evenness,
        )
        note_count = end - index + 1
        if pair is not None and note_count >= minimum_notes:
            low, high = pair
            runs.append(
                TrillRun(
                    hand=hand,
                    start_frame=attacks[index].column,
                    end_frame=attacks[end].column + 1,
                    row=low,
                    other_row=high,
                    note_count=note_count,
                    median_gap_ms=median(gaps),
                )
            )
            # Resume at the run's last note. It may legitimately begin the next one.
            index = end
        else:
            index += 1
    return runs


def _extend(
    attacks: list[_Attack],
    start: int,
    *,
    max_semitones: int,
    max_gap_ms: float,
    evenness: float,
) -> tuple[int, list[float], tuple[int, int] | None]:
    """How far the alternation beginning at ``start`` runs, its gaps, and the two notes in it.

    Returns ``(start, [], None)`` when the two notes at ``start`` cannot begin one at all. The
    pair comes back rather than being read off the attacks again, so a caller never has to
    re-establish that both of them really were single notes.
    """
    first, second = attacks[start], attacks[start + 1] if start + 1 < len(attacks) else None
    if second is None or first.row is None or second.row is None:
        return start, [], None
    if not 1 <= abs(first.row - second.row) <= max_semitones:
        return start, [], None

    first_gap = (second.seconds - first.seconds) * MS_PER_SECOND
    if not 0 < first_gap <= max_gap_ms:
        return start, [], None

    lo, hi = first_gap * (1 - evenness), first_gap * (1 + evenness)
    gaps = [first_gap]
    end = start + 1
    while end + 1 < len(attacks):
        candidate = attacks[end + 1]
        # The alternation is strict: every note repeats the one two back and differs from the one
        # before it. Two notes in a row, or a third note joining in, ends the run.
        if candidate.row is None or candidate.row != attacks[end - 1].row:
            break
        gap = (candidate.seconds - attacks[end].seconds) * MS_PER_SECOND
        if not lo <= gap <= hi or gap > max_gap_ms:
            break
        gaps.append(gap)
        end += 1
    low, high = sorted((first.row, second.row))
    return end, gaps, (low, high)
