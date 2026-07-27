"""Appendix C: fit real, human-played durations onto the matrix grid.

A recording never lands on the grid. A "negra" at 60 BPM might last 1.01 s or
0.94 s, and inventing a figure for the remainder produces exactly the cluttered
sheet this project exists to avoid.

The algorithm, in one sentence
------------------------------

**List the durations that can be written legally, and pick the one closest to
what was played.** That is the whole thing.

What can be written legally is the constrained part:

1. a **single figure** — redonda, blanca, negra, corchea, … down to the grid; or
2. **two figures tied, adjacent in the hierarchy** — which is exactly a dotted
   note (negra + corchea, corchea + semicorchea, blanca + negra).

Never more than two, and **never a non-adjacent pair**. Skipping a step —
negra + semicorchea — is precisely the fussy extra ligature the rule exists to
prevent, so it is not a candidate at all.

The worked example
------------------

*1.23 s at 60 BPM, semicorchea grid (0.25 s per column).* The candidates near
that duration are:

============================  =========  ========  ==========================
Candidate                     Columns    Lasts     Distance from 1.23 s
============================  =========  ========  ==========================
corchea                       2          0.50 s    0.73 s
**negra**                     **4**      **1.00 s**  **0.23 s**  ← closest
negra + corchea (dotted)      6          1.50 s    0.27 s
blanca                        8          2.00 s    0.77 s
============================  =========  ========  ==========================

``negra + semicorchea`` (5 columns, 1.25 s) would have been nearer still — but
it ties two figures that are two steps apart, so it is never generated.

Between the two survivors the choice is arithmetic: 1.00 s is 0.23 s away,
1.50 s is 0.27 s away, so the answer is a **plain negra — 4 columns,
``1 -1 -1 -1``**. No remainder is invented, and the sheet stays clean.

The appendix's other number falls out of the same comparison: 1.1 s is 0.10 s
from a negra and 0.40 s from a dotted negra, so it is "counted as a 1 second"
too.

When nothing lands exactly
--------------------------

Legal column counts at semicorchea granularity are ``1, 2, 3, 4, 6, 8, 12, 16,
24``. A duration between two of them takes the nearer, and an exact tie takes
the **shorter** — a note that ends early leaves a gap, while one that ends late
collides with whatever comes next.

Some temporal information is lost this way, and that is accepted: the appendix
says so outright. A readable page is the goal, not a perfect stopwatch.
"""

from __future__ import annotations

from dataclasses import dataclass

from aitu_backend.schemas.matrix import GRANULARITY_HIERARCHY, Granularity

#: Default onset tolerance, as a fraction of one column. 0.5 = nearest boundary.
DEFAULT_ONSET_TOLERANCE = 0.5


@dataclass(frozen=True)
class DurationFit:
    """The chosen approximation of one note duration."""

    #: Total columns the note occupies, onset column included. Always >= 1.
    columns: int
    #: Sustain (``-1``) columns to emit after the onset column.
    sustain_columns: int
    #: One or two figures, coarsest first.
    figures: tuple[Granularity, ...]
    #: What the fit actually lasts, in seconds.
    seconds: float
    #: ``seconds - requested``; positive means the note was lengthened.
    error_seconds: float
    #: True when the request landed exactly on the grid.
    exact: bool

    @property
    def is_ligature(self) -> bool:
        return len(self.figures) > 1

    def describe(self) -> str:
        """Human-readable, e.g. ``"negra + semicorchea (5 columns, +0.020 s)"``."""
        names = " + ".join(figure.value for figure in self.figures)
        return f"{names} ({self.columns} columns, {self.error_seconds:+.3f} s)"


def figure_columns(figure: Granularity | str, granularity: Granularity | str) -> int:
    """How many ``granularity`` columns one ``figure`` spans.

    Raises when the figure is finer than the granularity — it cannot be drawn
    on this grid at all.
    """
    figure_beats = Granularity(figure).beats
    column_beats = Granularity(granularity).beats
    if figure_beats < column_beats:
        raise ValueError(
            f"{Granularity(figure).value} is finer than the {Granularity(granularity).value} grid"
        )
    return int(round(figure_beats / column_beats))


def available_figures(granularity: Granularity | str) -> list[Granularity]:
    """Figures drawable on this grid, coarsest first (down to the grid itself)."""
    granularity = Granularity(granularity)
    limit = GRANULARITY_HIERARCHY.index(granularity)
    return list(GRANULARITY_HIERARCHY[: limit + 1])


def expressible_columns(
    granularity: Granularity | str,
    *,
    max_figures: int = 2,
    allow_non_adjacent: bool = False,
) -> dict[int, tuple[Granularity, ...]]:
    """Every legally writable column count, mapped to its figures.

    Singles, plus **adjacent** hierarchy pairs — which are exactly the dotted
    notes. At semicorchea granularity that gives
    ``1, 2, 3, 4, 6, 8, 12, 16, 24``.

    ``allow_non_adjacent=True`` also generates pairs that skip a step
    (negra + semicorchea = 5). That is the fussy ligature Appendix C forbids;
    the flag exists only so a test can show what the rule excludes.
    """
    figures = available_figures(granularity)
    table: dict[int, tuple[Granularity, ...]] = {}

    for figure in figures:  # coarsest first
        table.setdefault(figure_columns(figure, granularity), (figure,))

    if max_figures >= 2:
        for index, first in enumerate(figures):
            # Adjacency: only the very next figure in the hierarchy.
            partners = (
                figures[index + 1 :] if allow_non_adjacent else figures[index + 1 : index + 2]
            )
            for second in partners:
                total = figure_columns(first, granularity) + figure_columns(second, granularity)
                table.setdefault(total, (first, second))

    return table


def approximate_duration(
    duration_seconds: float,
    granularity: Granularity | str,
    tempo_bpm: float,
    *,
    max_figures: int = 2,
    allow_non_adjacent: bool = False,
) -> DurationFit:
    """Pick the legally writable duration closest to ``duration_seconds``.

    Worked example — 1.23 s at 60 BPM, semicorchea grid::

        negra           4 cols = 1.00 s   0.23 s away   <- chosen
        negra + corchea 6 cols = 1.50 s   0.27 s away

    (``negra + semicorchea`` would be nearer at 1.25 s, but ties two figures
    two steps apart, so it is never a candidate.)
    """
    if duration_seconds <= 0:
        raise ValueError(f"Duration must be positive, got {duration_seconds}")

    granularity = Granularity(granularity)
    column_seconds = granularity.seconds(tempo_bpm)
    table = expressible_columns(
        granularity, max_figures=max_figures, allow_non_adjacent=allow_non_adjacent
    )

    # How many columns the note *really* lasted, unrounded — comparing against
    # this rather than a pre-rounded count is what makes "closest" mean closest
    # to what was played.
    exact_columns = duration_seconds / column_seconds
    columns = _closest_writable(exact_columns, table)

    seconds = columns * column_seconds
    error = seconds - duration_seconds
    return DurationFit(
        columns=columns,
        sustain_columns=columns - 1,
        figures=table[columns],
        seconds=seconds,
        error_seconds=error,
        exact=abs(error) < 1e-9,
    )


def _closest_writable(exact_columns: float, table: dict[int, tuple[Granularity, ...]]) -> int:
    """The writable column count nearest to the real duration.

    An exact tie takes the **shorter** note: ending early leaves a gap, while
    ending late collides with whatever comes next.
    """
    return min(table, key=lambda columns: (abs(columns - exact_columns), columns))


def snap_onset(
    start_seconds: float,
    granularity: Granularity | str,
    tempo_bpm: float,
    *,
    tolerance: float = DEFAULT_ONSET_TOLERANCE,
) -> int:
    """Column an onset belongs to.

    ``tolerance`` is a fraction of one column: with the default ``0.5`` an onset
    goes to the nearest boundary. A smaller value biases toward the earlier
    column, which is the forgiving choice for a player who rushes.

    Note the sensitivity the doc's General Note warns about: this rounding is
    only as good as the BPM the user supplied. A passage played faster than the
    stated tempo will drift, and no tolerance value fixes that.
    """
    if start_seconds < 0:
        raise ValueError("Onset time cannot be negative")
    if not 0 < tolerance <= 1:
        raise ValueError("tolerance must be in (0, 1]")

    column_seconds = Granularity(granularity).seconds(tempo_bpm)
    exact = start_seconds / column_seconds
    floor = int(exact)
    return floor + 1 if (exact - floor) >= tolerance else floor


@dataclass(frozen=True)
class SnappedNote:
    """A transcription event placed on the grid."""

    row: int
    start_column: int
    fit: DurationFit

    @property
    def end_column(self) -> int:
        """Exclusive: the first column the note no longer occupies."""
        return self.start_column + self.fit.columns


def snap_note(
    row: int,
    start_seconds: float,
    duration_seconds: float,
    granularity: Granularity | str,
    tempo_bpm: float,
    *,
    tolerance: float = DEFAULT_ONSET_TOLERANCE,
    max_figures: int = 2,
    allow_non_adjacent: bool = False,
) -> SnappedNote:
    """Snap one transcription event onto the grid."""
    return SnappedNote(
        row=row,
        start_column=snap_onset(start_seconds, granularity, tempo_bpm, tolerance=tolerance),
        fit=approximate_duration(
            duration_seconds,
            granularity,
            tempo_bpm,
            max_figures=max_figures,
            allow_non_adjacent=allow_non_adjacent,
        ),
    )
