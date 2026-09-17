"""The second check: is this run's colour one of the colours notes are drawn in?

Task 2.3.4, and the optional double validation the prompt suggested. It is a
second reason to believe a run is a note — never a reason to decide which hand
plays it, because hands are never read from the colours of the rectangles (V-17).

It ships only if the score board improves, and the report gives the numbers
either way (V-20). Two things from the casuistry catalogue tell it what it has to
cope with, and both argue for a palette collected from the picture rather than a
fixed one:

* **Four of the twenty one examples are grey**, so there is nothing to cluster and
  the check has to answer "no opinion" rather than refuse everything.
* **One changes the rectangle's colour with its height** in the roll, magenta at
  the top and red at the upper line, so a run cannot be compared against one
  fixed colour even within one picture.

So the palette is the colours of the runs themselves, merged into groups; a run
is refused only when its own colour is far from every group that carries a real
share of the picture's rectangles. A picture whose runs are all one colour
refuses nothing, which is the behaviour the grey examples need.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.schemas.video import DetectedRun

#: How close two run colours have to be to be the same colour, in RGB distance.
MERGE_DISTANCE = 40.0

#: How far a run's colour may sit from the nearest real group before it is
#: refused. Deliberately loose: this check is a second opinion, not the detector.
TAU_COLOUR = 90.0

#: A group carrying less than this share of the runs is not "a colour notes are
#: drawn in"; it is the one odd thing the check is looking for.
MIN_SHARE = 0.10


def run_colour(image: np.ndarray, run: DetectedRun) -> np.ndarray:
    """The median colour inside one run, read away from its own borders.

    The middle half of the box in both directions, so the drawn border and the
    glow around the rectangle do not enter the answer.
    """
    height = run.y_bottom - run.y_top + 1
    width = max(1.0, run.x1 - run.x0)
    y0 = int(run.y_top + height * 0.25)
    y1 = max(y0 + 1, int(run.y_bottom - height * 0.25) + 1)
    x0 = int(run.x0 + width * 0.25)
    x1 = max(x0 + 1, int(run.x1 - width * 0.25) + 1)
    patch = image[y0:y1, x0:x1]
    if patch.size == 0:
        return np.zeros(3, dtype=np.float32)
    return np.median(patch.reshape(-1, 3), axis=0)


def palette(colours: list[np.ndarray]) -> list[tuple[np.ndarray, float]]:
    """The colours the rectangles of this picture are drawn in, with their share.

    Agglomerative and deliberately plain: every colour joins the first group it
    is within ``MERGE_DISTANCE`` of, and the group's centre is the running mean.
    Five clusters of k-means were measured as the slowest candidate of Phase 1
    and this needs far less, because it is only grouping a few dozen colours.
    """
    if not colours:
        return []
    centres: list[np.ndarray] = []
    counts: list[int] = []
    for colour in colours:
        for i, centre in enumerate(centres):
            if float(np.linalg.norm(colour - centre)) <= MERGE_DISTANCE:
                counts[i] += 1
                centres[i] = centre + (colour - centre) / counts[i]
                break
        else:
            centres.append(np.asarray(colour, dtype=np.float64))
            counts.append(1)
    total = float(sum(counts))
    return [(centre, count / total) for centre, count in zip(centres, counts)]


def off_palette(
    image: np.ndarray,
    runs: list[DetectedRun],
    tau: float = TAU_COLOUR,
    min_share: float = MIN_SHARE,
) -> list[bool]:
    """One answer per run: is its colour unlike every colour notes are drawn in?

    True means refused. When the picture has only one real group — every
    rectangle the same colour, which is what the grey examples look like —
    nothing is refused, because a single group cannot say what an outlier is.
    """
    if len(runs) < 4:
        return [False] * len(runs)
    colours = [run_colour(image, run) for run in runs]
    groups = [(centre, share) for centre, share in palette(colours) if share >= min_share]
    if len(groups) < 2:
        return [False] * len(runs)
    return [
        min(float(np.linalg.norm(colour - centre)) for centre, _ in groups) > tau
        for colour in colours
    ]
