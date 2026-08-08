"""Printed figures: how long a note is drawn as, and which glyph name that is.

A figure is a **label** now. It says nothing about where the note sits, because the column is the
same width whichever figure is printed. Getting one wrong costs a wrong glyph and nothing else,
which is what makes per-note override (D-17) and re-pointing a whole passage (D-18) ordinary
features rather than repairs.

Two rules decide the label, and both are frozen:

* **The printed length is the gap from this onset to the next onset in the same hand** (D-14), not
  the note's release. A chord counts as one event. The accepted cost is that a held note is cut
  short when the same hand plays anything else; the alternative fills the page with ties, rests and
  inner voices, which is the ugliness this refactor removes.
* **The figure is the nearest one by proportion** (D-11), never by milliseconds, and the vocabulary
  is closed (D-12). The comparison itself lives in :mod:`aitu_backend.matrix.ladder` and is imported
  here rather than written twice.

The gap is measured between the **raw onset times** the attacks were recorded at, not between column
indices. At 40 ms columns a 211 ms gap would otherwise arrive as 200 and a 125 ms one as 120, which
is close enough to change a figure.

The redonda cap (D-06, D-15) is applied here and not when the matrix is built, because a redonda has
no length until the user has named a peak.
"""

from __future__ import annotations

from dataclasses import dataclass

from aitu_backend.matrix.ladder import FigureFit, nearest_figure
from aitu_backend.notation.tuplets import Tresillo, find_tresillos
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, MS_PER_SECOND, frame_span_of_ms
from aitu_backend.schemas.matrix import ONSET
from aitu_backend.schemas.time_matrix import (
    FIGURE_NEGRAS,
    FigureLadder,
    FigureName,
    PrintedHand,
    PrintedNote,
)

__all__ = [
    "FIGURE_NEGRAS",
    "FigureFit",
    "FigureName",
    "onset_columns",
    "printed_notes_of_hand",
    "select_figure",
]


@dataclass(frozen=True)
class _Attack:
    """One column of one hand: when it really happened, and which keys it struck."""

    column: int
    seconds: float
    rows: tuple[int, ...]
    group_id: int


def select_figure(gap_ms: float, ladder: FigureLadder) -> FigureFit:
    """The figure a printed length is drawn as (D-11, D-12).

    This is :func:`aitu_backend.matrix.ladder.nearest_figure` under the name Phase 3 uses. It is
    imported rather than reimplemented on purpose: two versions of the proportional comparison that
    disagree would put a different figure on the page from the one the peak preview promised.
    """
    return nearest_figure(gap_ms, ladder)


def onset_columns(matrix: PianoMatrix) -> list[int]:
    """Every column of this hand that has at least one struck note, in order."""
    struck = (matrix.grid == ONSET).any(axis=0)
    return [int(column) for column in struck.nonzero()[0]]


def printed_notes_of_hand(
    matrix: PianoMatrix,
    hand: PrintedHand,
    ladder_at: FigureLadder | list[tuple[int, int, FigureLadder]],
    *,
    attack_seconds: dict[int, float],
    group_id: dict[int, int] | None = None,
    frame_ms: float = DEFAULT_FRAME_MS,
    tail_seconds: float | None = None,
    tuplet_start_id: int = 0,
) -> list[PrintedNote]:
    """Every glyph this hand contributes, with its figure already chosen.

    ``ladder_at`` is either one ladder for the whole piece, or the passage list as
    ``(startFrame, endFrame, ladder)`` triples. A note takes the ladder of the passage its onset
    falls in, which is what keeps a ladder change local (D-21).

    ``attack_seconds`` maps a column to the raw time the attack really happened at, so the gap
    between two notes is the gap that was played rather than a whole number of frames.

    The **last** note of the hand has no next onset. Its printed length runs to ``tail_seconds`` when
    one is given, otherwise to the end of its own measured sustain, and it is capped like any other.
    """
    attacks = _attacks_of(matrix, attack_seconds, group_id, frame_ms)
    if not attacks:
        return []

    gaps = [
        _gap_ms(attacks, index, matrix, frame_ms, tail_seconds) for index in range(len(attacks))
    ]
    # A tresillo is decided before any figure is chosen, because the whole point of it is that the
    # nearest figure is the wrong answer: three notes dividing a beat land a third of the way apart,
    # and a ladder of halves has no name for that. See `notation/tuplets.py`.
    in_tresillo = _tresillos_by_index(attacks, gaps, ladder_at, tuplet_start_id)

    notes: list[PrintedNote] = []
    for index, attack in enumerate(attacks):
        ladder = _ladder_for(attack.column, ladder_at)
        gap_ms = min(gaps[index], ladder.ms_by_figure[FigureName.REDONDA])
        tresillo = in_tresillo.get(index)
        if tresillo is None:
            fit = select_figure(gap_ms, ladder)
            figure, fit_error = fit.figure, fit.fit_error
        else:
            # Printed as the ordinary figure one step below the one being divided. The 3 and the
            # bracket are what say it is a tresillo, so the glyph itself stays conventional.
            figure = tresillo.group.figure
            fit_error = 0.0
        printed_frames = min(
            frame_span_of_ms(gap_ms, frame_ms),
            max(1, matrix.frame_count - attack.column),
        )
        for row in attack.rows:
            notes.append(
                PrintedNote(
                    hand=hand,
                    row=row,
                    start_frame=attack.column,
                    printed_frames=printed_frames,
                    printed_ms_exact=gap_ms,
                    figure=figure,
                    fit_error=fit_error,
                    tuplet=None if tresillo is None else 3,
                    tuplet_id=None if tresillo is None else tresillo.tuplet_id,
                    group_id=attack.group_id,
                )
            )
    return notes


def _attacks_of(
    matrix: PianoMatrix,
    attack_seconds: dict[int, float],
    group_id: dict[int, int] | None,
    frame_ms: float,
) -> list[_Attack]:
    """This hand's attacks, each with the raw time it happened at.

    A column with no recorded time falls back to the middle of the column. That happens for a matrix
    that was hand-edited or loaded from disk rather than built in this run, and half a frame is the
    least wrong guess available.
    """
    attacks: list[_Attack] = []
    for column in onset_columns(matrix):
        seconds = attack_seconds.get(column)
        if seconds is None:
            seconds = (column + 0.5) * frame_ms / MS_PER_SECOND
        attacks.append(
            _Attack(
                column=column,
                seconds=seconds,
                rows=tuple(matrix.onsets_in_column(column)),
                group_id=(group_id or {}).get(column, column),
            )
        )
    return attacks


def _gap_ms(
    attacks: list[_Attack],
    index: int,
    matrix: PianoMatrix,
    frame_ms: float,
    tail_seconds: float | None,
) -> float:
    """This onset to the next onset in the same hand, in milliseconds (D-14)."""
    if index + 1 < len(attacks):
        return (attacks[index + 1].seconds - attacks[index].seconds) * MS_PER_SECOND
    if tail_seconds is not None:
        return max(frame_ms, (tail_seconds - attacks[index].seconds) * MS_PER_SECOND)
    return max(frame_ms, _sustain_end_ms(matrix, attacks[index], frame_ms))


def _sustain_end_ms(matrix: PianoMatrix, attack: _Attack, frame_ms: float) -> float:
    """How long the last note keeps sounding, from the grid, in milliseconds."""
    end = attack.column + 1
    for row in attack.rows:
        column = attack.column + 1
        while column < matrix.frame_count and matrix.cell(row, column) != 0:
            column += 1
        end = max(end, column)
    return (end - attack.column) * frame_ms


def _ladder_for(
    column: int,
    ladder_at: FigureLadder | list[tuple[int, int, FigureLadder]],
) -> FigureLadder:
    if isinstance(ladder_at, FigureLadder):
        return ladder_at
    for start, end, ladder in ladder_at:
        if start <= column < end:
            return ladder
    raise ValueError(
        f"Column {column} falls in no passage. Passages must tile the piece with no gap; "
        "see contract.md §4."
    )


@dataclass(frozen=True)
class _InTresillo:
    group: Tresillo
    tuplet_id: int


def _tresillos_by_index(
    attacks: list[_Attack],
    gaps: list[float],
    ladder_at: FigureLadder | list[tuple[int, int, FigureLadder]],
    start_id: int,
) -> dict[int, _InTresillo]:
    """Which attacks belong to a tresillo, keyed by their place in the hand's list.

    Found per passage rather than over the whole hand, because "a third of a negra" means a
    different number of milliseconds in each one, and a group must not be judged against a ladder
    that does not apply where it sits.

    Only the last passage is open-ended: its final gap runs out to the end of the hand rather than to
    another onset, so it is not evidence about the group that ends there. Every other passage's last
    gap is a real gap to the first note of the next one.
    """
    inside: dict[int, _InTresillo] = {}
    next_id = start_id
    spans = _passage_spans(attacks, ladder_at)
    for span, (start, end) in enumerate(spans):
        ladder = _ladder_for(attacks[start].column, ladder_at)
        window = gaps[start:end]
        for group in find_tresillos(window, ladder, open_ended=span == len(spans) - 1):
            for offset in group.indexes:
                inside[start + offset] = _InTresillo(group=group, tuplet_id=next_id)
            next_id += 1
    return inside


def _passage_spans(
    attacks: list[_Attack],
    ladder_at: FigureLadder | list[tuple[int, int, FigureLadder]],
) -> list[tuple[int, int]]:
    """The stretches of the attack list that share one ladder, as half-open index ranges."""
    if isinstance(ladder_at, FigureLadder) or len(ladder_at) <= 1:
        return [(0, len(attacks))]
    spans: list[tuple[int, int]] = []
    start = 0
    for index in range(1, len(attacks)):
        if _ladder_for(attacks[index].column, ladder_at) is not _ladder_for(
            attacks[start].column, ladder_at
        ):
            spans.append((start, index))
            start = index
    spans.append((start, len(attacks)))
    return spans
