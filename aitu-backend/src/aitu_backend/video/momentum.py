"""A rectangle falls. Anything that does not fall is not a note (V-33).

A song title, a watermark, decorative scrollwork and an octave guide line all
look like rectangles to a detector that only ever sees one picture — on one
example 34 of the 49 runs found are lettering. Two pictures settle it without any
appeal to what the thing looks like: a run is believed when a neighbouring
sampled frame holds the same run one frame of travel away, and refused when a
neighbouring frame holds it in exactly the same place.

Three things this module is careful about, each of which was got wrong first:

* **The travel is voted for by the runs, never correlated from the pictures.** A
  title drawn in letters a hundred pixels tall dominates any correlation that
  still contains them, and the correlation then peaks at a shift of nothing,
  because the letters really did not move. The first attempt answered 0 px.
* **A rectangle in the neighbouring frame is the past of at most one rectangle in
  this one** (V-34). Without that, a key struck twice about one frame of travel
  apart aliases: the first stroke's rectangle sits, in the frame before, exactly
  where the second stroke's rectangle sits now, so the second stroke looks
  static and a real note is thrown away.
* **The rule refuses; it does not select.** Only a run proven to have stood still
  is dropped. A run with no neighbour to ask is kept, because the absence of an
  answer is not an answer. Measured: refusing the proven static ones drops 42
  runs of 174 and not one of them is a rectangle, while keeping only the proven
  moving ones drops 128 and 28 of those are rectangles.
"""

from __future__ import annotations

from aitu_backend.schemas.video import DetectedRun

#: Pixels of slack when matching a run to its own self in another frame.
#: Measured: at 3 the vote is stable but a few real notes are missed, at 7 it
#: collapses onto the static content, because that much slack lets a letter match
#: itself at a small shift.
TOLERANCE = 5.0

#: Pixels. This close to where it was, it did not move.
STATIC_TOLERANCE = 2.0

#: The vote never considers a travel smaller than this, because that is where the
#: answer "nothing moved" lives and counting it is the mistake this rule exists
#: to avoid. It is derived, not chosen: a run matches itself at any shift within
#: :data:`TOLERANCE`, so any floor at or below the slack lets the lettering vote
#: for itself and the vote collapses onto the static content. Phase 1 used 15 on
#: three screenshots 51 and 68 px apart; a video sampled at 10 frames per second
#: travels about 17 px, so the floor has to sit well under that as well.
VOTE_FLOOR = int(2 * TOLERANCE) + 1


def _by_key(runs: list[DetectedRun]) -> dict[int, list[tuple[int, DetectedRun]]]:
    index: dict[int, list[tuple[int, DetectedRun]]] = {}
    for i, run in enumerate(runs):
        index.setdefault(run.midi, []).append((i, run))
    return index


def _fits(candidate: DetectedRun, run: DetectedRun, dy: float, tolerance: float) -> float | None:
    """How badly ``candidate`` fits as the same rectangle ``dy`` pixels away.

    **A pinned edge is not evidence, on either side.** A run cut by the upper
    line has not got a tip there, it has been cut there (V-16), so its lowest row
    is the line and not the rectangle — it stays at the same row however fast the
    rectangle falls. A run still coming into view at the roll top (V-28) has the
    same problem at its other end. So the edge that the picture pinned is left
    out of the comparison and the free one decides.

    Getting this wrong was measured on a real video, where the rule wired for the
    first time refused 80 runs in a fourteen second stretch and **every single one
    of them was clipped**: with the bottom edge pinned at the line on both sides,
    a falling rectangle can never be shown to have fallen, and any glow whose top
    happens to sit still is refused as proven static. That is a deletion on
    evidence that is not evidence, which V-30 forbids.

    A run that is pinned at both ends — a rectangle taller than the whole roll —
    has nothing that can move, so nothing fits it and it stays ``unknown``, which
    is V-33's own answer: the absence of an answer is not an answer.
    """
    checks: list[float] = []
    if not (run.entering or candidate.entering):
        checks.append(abs(candidate.y_top - (run.y_top + dy)))
    if not (run.clipped or candidate.clipped):
        checks.append(abs(candidate.y_bottom - (run.y_bottom + dy)))
    if not checks or max(checks) > tolerance:
        return None
    return sum(checks)


def matches_at(runs: list[DetectedRun], other: list[DetectedRun], travel: float) -> int:
    """How many runs sit exactly ``travel`` below a run of the other frame."""
    index = _by_key(other)
    count = 0
    for run in runs:
        for _, candidate in index.get(run.midi, ()):
            if _fits(candidate, run, -travel, TOLERANCE) is not None:
                count += 1
                break
    return count


def vote_for_travel(
    runs: list[DetectedRun], previous: list[DetectedRun], lo: int = VOTE_FLOOR, hi: int = 220
) -> tuple[int, int, int]:
    """Let the rectangles say how far they fell: (travel, agreeing, standing still).

    A shift of nothing is excluded on purpose, but it is counted and returned,
    because how big it is says how much of the picture is not music.

    The slack of :data:`TOLERANCE` makes the winning count a plateau rather than a
    spike — every shift within the slack of the real travel matches the same runs
    — so the answer is the middle of the widest plateau, not its first shift.
    Taking the first would bias every travel low by the whole slack.
    """
    if not runs or not previous:
        return 0, 0, 0
    counts = {shift: matches_at(runs, previous, shift) for shift in range(lo, hi + 1)}
    peak = max(counts.values())
    if peak == 0:
        return 0, 0, matches_at(runs, previous, 0)

    best_plateau: list[int] = []
    current: list[int] = []
    for shift in range(lo, hi + 1):
        if counts[shift] == peak:
            current.append(shift)
        else:
            if len(current) > len(best_plateau):
                best_plateau = current
            current = []
    if len(current) > len(best_plateau):
        best_plateau = current

    best = best_plateau[len(best_plateau) // 2]
    return best, peak, matches_at(runs, previous, 0)


def link(
    runs: list[DetectedRun], other: list[DetectedRun], dy: float
) -> tuple[list[int | None], set[int]]:
    """Match every run to its own self in a neighbouring frame, one to one.

    Pairs are taken best fit first, so the closest reading of each rectangle wins
    and the leftovers cannot steal it. The set returned is which runs of the
    neighbouring frame are spoken for: a claimed rectangle is not evidence that
    anything stood still (V-34).
    """
    index = _by_key(other)
    pairs: list[tuple[float, int, int]] = []
    for i, run in enumerate(runs):
        for j, candidate in index.get(run.midi, ()):
            cost = _fits(candidate, run, dy, TOLERANCE)
            if cost is not None:
                pairs.append((cost, i, j))
    pairs.sort()

    link_of: list[int | None] = [None] * len(runs)
    taken: set[int] = set()
    for _, i, j in pairs:
        if link_of[i] is None and j not in taken:
            link_of[i] = j
            taken.add(j)
    return link_of, taken


def verdicts(
    runs: list[DetectedRun],
    before: list[DetectedRun],
    before_travel: float,
    after: list[DetectedRun],
    after_travel: float,
) -> list[str]:
    """One word per run: ``fell``, ``static``, or ``unknown``.

    Both neighbours are asked, not only the one before. A rectangle at the top of
    the roll has no frame before it that holds it, but the frame after it holds it
    one travel lower, and that answers just as well.
    """
    fell_before, claimed_before = (
        link(runs, before, -before_travel) if before else ([None] * len(runs), set())
    )
    fell_after, claimed_after = (
        link(runs, after, +after_travel) if after else ([None] * len(runs), set())
    )
    index_before, index_after = _by_key(before), _by_key(after)

    out: list[str] = []
    for i, run in enumerate(runs):
        if fell_before[i] is not None or fell_after[i] is not None:
            out.append("fell")
            continue
        still = False
        for index, claimed in ((index_before, claimed_before), (index_after, claimed_after)):
            for j, candidate in index.get(run.midi, ()):
                if j in claimed:
                    continue  # already the past of another rectangle (V-34)
                if _fits(candidate, run, 0.0, STATIC_TOLERANCE) is not None:
                    still = True
                    break
            if still:
                break
        out.append("static" if still else "unknown")
    return out


def apply(
    runs: list[DetectedRun],
    before: list[DetectedRun],
    before_travel: float,
    after: list[DetectedRun],
    after_travel: float,
) -> tuple[list[DetectedRun], list[DetectedRun]]:
    """Stamp every run with its verdict and split off the ones refused.

    Returns (kept, refused). Only a run proven static is refused; a run with no
    neighbour to ask is kept, because the absence of an answer is not an answer.
    """
    stamped = verdicts(runs, before, before_travel, after, after_travel)
    kept: list[DetectedRun] = []
    refused: list[DetectedRun] = []
    for run, verdict in zip(runs, stamped):
        run.momentum = verdict  # type: ignore[assignment]
        (refused if verdict == "static" else kept).append(run)
    return kept, refused
