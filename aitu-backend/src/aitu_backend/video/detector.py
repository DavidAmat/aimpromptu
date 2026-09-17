"""One picture and one calibration in, onsets and sustains out.

Task 2.3.1, and the algorithm of section 8 of the plan. It has no idea whether
the picture came from an example screenshot or from a sampled frame of a video.

Every threshold below carries the measurement Phase 1 made for it; the report is
`context/implementations/04-synthesia-to-notes/04-phase-1-implementation.md` and
the evidence is `poc-synthesia-frames/RESULTS.md`. A rule with no measurement
beside it does not ship (V-20).

The order of the steps, once per key:

1. the foreground — how far this pixel is from the background plate;
2. the lane of **this** key, read once, for this key (V-27);
3. fill each row between its outermost foreground pixels, so an outlined
   rectangle counts as filled;
4. rows whose coverage reaches ``tau_coverage`` are inside a rectangle; close
   gaps of at most ``gap_close`` rows and drop runs shorter than ``min_height``;
5. cut the run at every border deep enough to be two rectangles touching (V-26);
6. measure the rectangle's whole width across the lane borders, against its own
   peak, over a local window (``tau_edge``, ``extent_window``);
7. refuse a run that is too narrow or too wide to be a note;
8. refuse a run whose rectangle is centred nearer another key — that key's own
   lane will find it (V-14 as a filter);
9. flag, never delete, a run whose tip sits inside the halo guard band (V-08,
   V-30).

Then the frame window rule (V-18) turns the runs into two lists of MIDI pitches,
and released is the default and is never written down (V-19).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from aitu_backend.schemas.video import Calibration, DetectedRun, Detection, RejectedRun
from aitu_backend.video import geometry
from aitu_backend.video.plate import foreground_strength


@dataclass(frozen=True)
class DetectorSettings:
    """The named thresholds, with the value Phase 1 measured for each.

    Every length is in white key widths (V-22), because the example screenshots
    are 3600 px wide and the videos are 1280: a threshold in pixels is right on
    one of them and wrong on the other. Since V-38 there are two such widths:
    the vertical lengths and the guard band are in the median white key width,
    and the lane margin, the extent window and the width gate are in the local
    one, the width of the key being read.

    They are a frozen dataclass rather than module constants so the score board
    can measure what a change does instead of asserting it.
    """

    #: Of 255. The roll's own contrast is 104 at the worst usable example.
    tau_foreground: float = 24.0
    #: Filled fraction of the lane core for a row to be inside a rectangle.
    tau_coverage: float = 0.55
    #: Rows. Measured: the gap inside one rectangle is 1 to 2 rows and the border
    #: between two stacked rectangles is 3 to 7, so this has to stay under 3 or
    #: two notes become one and the second onset is lost without a sound (V-26).
    gap_close: int = 2
    #: Of a run's plateau, measured beside the valley (V-46). Texture inside one
    #: rectangle reaches 0.13 at the worst and a real border drops 0.75 to 0.80;
    #: swept against two keyboards, 0.25 to 0.30 is the middle of the plateau
    #: once the plateau is the one beside the dip and not the run's brightest
    #: row.
    split_prominence: float = 0.30
    #: White key widths either side of a dip within which its plateau is read.
    #: A real border is 3 to 7 rows and its plateaus are right beside it; the
    #: brightness of a rectangle changes along its length on some renderings,
    #: and against the brightest row of a whole run a step of 8% read as 40%.
    valley_window: float = 0.5
    #: White key widths either side of the key's centre whose columns set the
    #: reference the extent is measured against. The brightest column of the
    #: window is the rim on a rendering that draws one, and at half of it only
    #: the rim passed.
    core_window: float = 0.25
    #: White key widths. The shortest note measured was 95 ms, which is 15 rows.
    min_height: float = 0.24
    #: White key widths. A run whose lowest row sits this close to the upper line
    #: has been cut there, not tipped there (V-16).
    clip_tolerance: float = 0.12
    #: White key widths on both sides of a key (V-13).
    lane_margin: float = 0.25
    #: Of the run's own peak: where the rectangle stops and its glow starts.
    #: 0.35 to 0.65 all work; 0.00 loses a third of the rectangles.
    tau_edge: float = 0.50
    #: White key widths either side of the key that the search for the
    #: rectangle's own edges may reach. Over the whole width the brightest column
    #: is some other key's strike flash, and the search walks off to it.
    extent_window: float = 2.0
    #: White key widths. A black key rectangle measured 0.62.
    min_width: float = 0.35
    #: White key widths. A white key rectangle measured 1.03.
    max_width: float = 1.40
    #: White key widths above the upper line, when the picture cannot measure it.
    guard_band_default: float = 1.75
    #: Only the gradient channel needs it: a gradient is strong on a rectangle's
    #: border and empty in its middle, so the middle fails a test written for a
    #: filled shape. Turning it on for the plate difference lets the glow through
    #: and costs two invented onsets.
    hollow_fallback: bool = False


DEFAULTS = DetectorSettings()


# --------------------------------------------------------------- the lane ---


def _fill_span(sub: np.ndarray) -> np.ndarray:
    """Fill each row between its leftmost and its rightmost foreground pixel.

    Five of the twenty one examples draw the rectangle as an outline, where the
    inside of the shape is the background colour and only the border is drawn, so
    this step is not optional.
    """
    index = np.arange(sub.shape[1])[None, :]
    any_row: np.ndarray = np.asarray(sub.any(axis=1))
    first = np.where(any_row, np.where(sub, index, sub.shape[1]).min(axis=1), 0)
    last = np.where(any_row, np.where(sub, index, -1).max(axis=1), -1)
    return (index >= first[:, None]) & (index <= last[:, None]) & any_row[:, None]


def _close_gaps(flags: np.ndarray, gap: int) -> np.ndarray:
    """Close gaps of at most ``gap`` rows, and no more.

    ``binary_closing`` with a structure of length L closes every gap shorter than
    L, so the structure is ``gap + 1`` long. Getting this wrong is expensive: a
    structure of ``2 * gap + 1`` with gap 3 closes six rows, and the border
    between two rectangles stacked on one key is three to seven — which merged
    all 1351 separators in a sample of sixty sampled frames (V-26).
    """
    if gap <= 0:
        return flags
    return ndimage.binary_closing(flags, structure=np.ones(gap + 1))


def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """Every stretch of True, as half-open (start, end) row pairs."""
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, value in enumerate(flags):
        if value and start is None:
            start = i
        elif not value and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flags)))
    return out


def valleys(
    profile: np.ndarray, min_height: int, window: int | None = None
) -> list[tuple[int, float]]:
    """The interior local minima of one run, with their prominence.

    Prominence is how far the minimum sits below the lower of the two plateaus
    beside it — within ``window`` rows either side, never the whole run — as a
    share of the run's plateau. It is the right measure because
    the plateau of a rectangle is flat to about one percent while a border drops
    tens of percent, and because it does not care how bright the rendering is: on
    one key the plateau is 144 and the borders drop to 36, while on another the
    plateau is 88 and the texture inside a single confirmed quarter note ripples
    down to 72 — a share of the median cannot separate those, and prominence can.

    A flat bottom is one border, not forty, so neighbouring candidates are
    grouped and only the deepest of each group is answered for.
    """
    if len(profile) < 2 * min_height + 1:
        return []
    window = window or 2 * min_height
    plateau = float(np.percentile(profile, 75))
    if plateau <= 1:
        return []
    candidates = [
        i
        for i in range(min_height, len(profile) - min_height)
        if profile[i] <= profile[i - 1] and profile[i] <= profile[i + 1]
    ]
    if not candidates:
        return []

    groups: list[list[int]] = []
    current = [candidates[0]]
    for i in candidates[1:]:
        if i - current[-1] <= min_height:
            current.append(i)
        else:
            groups.append(current)
            current = [i]
    groups.append(current)

    out: list[tuple[int, float]] = []
    for group in groups:
        i = min(group, key=lambda row: profile[row])
        a, b = group[0], group[-1] + 1
        left = float(profile[max(0, a - window) : a].max()) if a > 0 else 0.0
        right = float(profile[b : b + window].max()) if b < len(profile) else 0.0
        if left <= 0 or right <= 0:
            continue
        out.append((i, (min(left, right) - float(profile[i])) / plateau))
    return out


def split_run(
    profile: np.ndarray,
    a: int,
    b: int,
    settings: DetectorSettings,
    min_height: int,
    window: int | None = None,
) -> list[tuple[int, int]]:
    """Cut one run wherever two rectangles touch (V-26).

    Where the border between two rectangles gets dark enough the run has already
    ended and there is nothing to do here. Where it does not — and on the test
    video two of the three borders of one lane did not — the run is one piece and
    the second onset would be lost without a sound. So the run is cut at every
    valley whose prominence reaches ``split_prominence``.
    """
    piece = profile[a:b]
    cuts = [
        i
        for i, prominence in valleys(piece, min_height, window)
        if prominence >= settings.split_prominence
    ]
    if not cuts:
        return [(a, b)]
    out: list[tuple[int, int]] = []
    start = a
    for cut in cuts:
        if a + cut - start >= min_height:
            out.append((start, a + cut))
            start = a + cut + 1
    if b - start >= min_height:
        out.append((start, b))
    return out or [(a, b)]


def _full_extent(
    strength: np.ndarray,
    y0: int,
    y1: int,
    centre: float,
    white_width: float,
    settings: DetectorSettings,
    filled: np.ndarray | None = None,
    filled_x0: int = 0,
) -> tuple[float, float] | None:
    """How wide the rectangle really is, ignoring where the lane borders are.

    A lane only shows the part of the rectangle that falls inside it, and V-14
    attributes by the midpoint of the whole rectangle, so the rectangle has to be
    measured across the lane borders before its midpoint is taken. Attributing by
    the midpoint of what the lane saw puts one rectangle on three keys.

    The rectangle is the bright part and the glow around it is the dim part, so
    the edge is found against the run's own strength rather than a fixed
    threshold. The reference is the median of the columns within ``core_window``
    white keys of the key's own centre (V-46): not the brightest column of the
    window, which on a rendering that draws a light rim around a darker fill is
    the rim — at half of it only the rim passed, the run read a third of a key
    wide and a real note was refused as too narrow. And never the whole width:
    there the brightest column is some other key's strike flash.

    ``None`` means the key's own centre is not part of anything bright in these
    rows, so this run does not belong to this key.
    """
    lo = max(0, int(round(centre - settings.extent_window * white_width)))
    hi = min(strength.shape[1], int(round(centre + settings.extent_window * white_width)) + 1)
    if hi - lo < 3:
        return None
    per_column = np.median(strength[y0 : y1 + 1, lo:hi], axis=0)
    centre_index = int(round(centre)) - lo
    if not (0 <= centre_index < len(per_column)):
        return None
    reach = max(1, int(round(settings.core_window * white_width)))
    core = per_column[max(0, centre_index - reach) : centre_index + reach + 1]
    reference = float(np.median(core))
    if reference <= 0:
        return None
    column = per_column >= max(settings.tau_edge * reference, settings.tau_foreground)
    if not column[centre_index] and filled is not None and settings.hollow_fallback:
        # An outlined rectangle is hollow: the gradient that drew its border is
        # strong and its middle is empty, so the middle fails a test written for
        # a filled shape. The span filled mask knows the shape is there, so it
        # answers for the columns the strength cannot.
        a0 = max(0, lo - filled_x0)
        b0 = min(filled.shape[1], hi - filled_x0)
        if b0 > a0:
            share = filled[y0 : y1 + 1, a0:b0].mean(axis=0) >= 0.5
            pad = np.zeros(len(column), dtype=bool)
            offset = max(0, filled_x0 - lo)
            count = min(len(share), len(pad) - offset)
            pad[offset : offset + count] = share[:count]
            column = column | pad
    if not column[centre_index]:
        return None

    a = centre_index
    while a > 0 and column[a - 1]:
        a -= 1
    b = centre_index
    while b < len(column) - 1 and column[b + 1]:
        b += 1
    return float(lo + a), float(lo + b)


def _rejection(
    key: dict,
    y0: int,
    y1: int,
    extent: tuple[float, float] | None,
    local: float,
    reason: str,
) -> RejectedRun:
    """One shape the lane found and a gate threw out, with the gate that did it."""
    x0, x1 = extent if extent is not None else (key["left"], key["right"])
    return RejectedRun(
        midi=int(key["midi"]),
        y_top=int(y0),
        y_bottom=int(y1),
        x0=float(x0),
        x1=float(x1),
        mid=float((x0 + x1) / 2),
        width_keys=float((x1 - x0 + 1) / local),
        reason=reason,
    )


def runs_for_key(
    strength: np.ndarray,
    mask: np.ndarray,
    cal: Calibration,
    key: dict,
    mids: np.ndarray,
    midis: np.ndarray,
    upper: int,
    roll_top: int,
    guard: float,
    settings: DetectorSettings,
    rejected: list[RejectedRun] | None = None,
) -> list[DetectedRun]:
    """Every rectangle this key's own lane holds, and no other key's (V-27).

    Reading every lane and then sorting the runs by nearest key midpoint keeps
    three answers about one rectangle, and because each lane cuts it into pieces
    differently the three disagree: on one frame key G2 carried a merged run of
    159 rows on top of the four correct ones, and 23 pairs of runs on one key
    overlapped. Two runs on one key can no longer overlap, because they come from
    one profile.

    ``rejected`` collects what was thrown out and why, so a shape whose width or
    whose midpoint does not match a key can be **reported** rather than rounded
    onto one (Task 4.1.2). It is off unless a caller asks for it, because the
    per-frame reading throws out hundreds of thousands of these and has no use
    for any of them.
    """
    # Two white key widths (V-38). The median one is the unit of the vertical
    # lengths — the minimum height and the clip tolerance, which perspective
    # across the keyboard does not change. The local one — this key's own — is
    # the unit of everything about this key: the lane margin, the extent window
    # and the width gate.
    white = cal.white_width
    local = float(key["white"])
    min_height = max(2, int(round(settings.min_height * white)))
    clip_tolerance = int(round(settings.clip_tolerance * white))
    valley_window = max(min_height, int(round(settings.valley_window * white)))

    lane0 = max(0, int(round(key["left"] - settings.lane_margin * local)))
    lane1 = min(mask.shape[1], int(round(key["right"] + settings.lane_margin * local)) + 1)
    core0 = max(0, int(round(key["left"])))
    core1 = min(mask.shape[1], int(round(key["right"])) + 1)
    if lane1 - lane0 < 3 or core1 - core0 < 2:
        return []

    filled_roll = _fill_span(mask[roll_top:, lane0:lane1])
    filled = np.zeros((mask.shape[0], lane1 - lane0), dtype=bool)
    filled[roll_top:] = filled_roll
    core_lo = core0 - lane0
    core_hi = max(core_lo + 1, core1 - lane0)
    coverage = filled_roll[:, core_lo:core_hi].mean(axis=1)
    inside = _close_gaps(coverage >= settings.tau_coverage, settings.gap_close)
    profile = strength[roll_top:, core0:core1].mean(axis=1)

    out: list[DetectedRun] = []
    for a, b in _runs(inside):
        if b - a < min_height:
            continue
        for run_y0, run_y1 in split_run(profile, a, b - 1, settings, min_height, valley_window):
            y0, y1 = run_y0 + roll_top, run_y1 + roll_top
            if y1 - y0 + 1 < min_height:
                continue
            extent = _full_extent(
                strength, y0, y1, key["mid"], local, settings, filled=filled, filled_x0=lane0
            )
            if extent is None:
                if rejected is not None:
                    rejected.append(_rejection(key, y0, y1, None, local, "no bright column"))
                continue
            x0, x1 = extent
            width = (x1 - x0 + 1) / local
            if not (settings.min_width <= width <= settings.max_width):
                if rejected is not None:
                    reason = "too narrow" if width < settings.min_width else "too wide"
                    rejected.append(_rejection(key, y0, y1, extent, local, reason))
                continue
            mid = (x0 + x1) / 2
            if midis[int(np.argmin(np.abs(mids - mid)))] != key["midi"]:
                if rejected is not None:
                    rejected.append(_rejection(key, y0, y1, extent, local, "nearer another key"))
                continue
            clipped = y1 >= upper - 1 - clip_tolerance
            out.append(
                DetectedRun(
                    midi=int(key["midi"]),
                    y_top=int(y0),
                    y_bottom=int(y1),
                    x0=float(x0),
                    x1=float(x1),
                    mid=float(mid),
                    width_keys=float(width),
                    clipped=bool(clipped),
                    tip_trusted=bool(clipped or y1 <= upper - guard),
                    entering=bool(y0 <= roll_top + 2),
                )
            )
    return out


def runs_from_strength(
    strength: np.ndarray,
    cal: Calibration,
    *,
    upper: int,
    roll_top: int,
    guard: float,
    settings: DetectorSettings = DEFAULTS,
    rejected: list[RejectedRun] | None = None,
) -> list[DetectedRun]:
    """Every rectangle a foreground picture holds, key by key (V-27).

    Split out from :func:`find_runs` because Phase 4's stitched roll is a
    foreground picture that no single frame ever showed: it is the fresh strip of
    every sampled frame piled up, so it has no upper line to cut it and no roll
    top to enter at (V-32). Everything after the foreground step is the same work
    on the same thresholds, so it is the same code.
    """
    mask = strength > settings.tau_foreground
    keys = geometry.keys(cal)
    widths = geometry.local_widths(cal)
    mids = np.array([k.mid for k in keys])
    midis = np.array([k.midi for k in keys])

    runs: list[DetectedRun] = []
    for key in keys:
        runs.extend(
            runs_for_key(
                strength,
                mask,
                cal,
                dict(
                    midi=key.midi,
                    left=key.left,
                    right=key.right,
                    mid=key.mid,
                    white=widths[key.midi],
                ),
                mids,
                midis,
                upper,
                roll_top,
                guard,
                settings,
                rejected=rejected,
            )
        )
    return runs


def find_runs(
    image: np.ndarray,
    cal: Calibration,
    plate: np.ndarray | None = None,
    channel: str = "plate",
    settings: DetectorSettings = DEFAULTS,
) -> list[DetectedRun]:
    """Every rectangle one picture holds, before any rule judges what it means.

    The pixel half of :func:`detect`, split out because a video has a second
    question a screenshot does not: whether the thing that looks like a rectangle
    actually fell (V-33). The momentum rule needs the runs of the frames either
    side of this one before the frame window rule turns anything into an onset,
    so the two halves cannot be one call.

    Nothing here knows whether the picture came from a screenshot or from a
    sampled frame.
    """
    upper = int(round(cal.upper_line))
    strength = foreground_strength(image[:upper], plate, channel=channel, settings=settings)
    return runs_from_strength(
        strength,
        cal,
        upper=upper,
        roll_top=int(round(cal.roll_top)),
        guard=geometry.guard_band_px(cal, settings.guard_band_default),
        settings=settings,
    )


# ------------------------------------------------------- the window rule ---


def window_rule(
    runs: list[DetectedRun], upper: int, offset_px: float
) -> tuple[list[int], list[int]]:
    """V-18, word for word, with V-16 applied to the tip.

    y grows downward. The roll was cut at the upper line, so a run whose lowest
    row sits on that cut has been cut there, not tipped there: its real tip is
    already past the upper line, the note is sounding, and its onset is in the
    past. Reading that edge as a tip is the single easiest way to invent an onset.

    Each run is given its own verdict as a side effect, so that a disagreement on
    the score board can be looked at on the picture rather than imagined.
    """
    onsets: set[int] = set()
    sustains: set[int] = set()
    for run in runs:
        y_bottom = upper if run.clipped else run.y_bottom
        if upper - offset_px <= y_bottom < upper:
            run.verdict = "onset"
            onsets.add(run.midi)
        elif y_bottom >= upper and run.y_top < upper - offset_px:
            run.verdict = "sustain"
            sustains.add(run.midi)
        else:
            run.verdict = "released"
    return sorted(onsets), sorted(sustains - onsets)


# ------------------------------------------------------------- the whole ---


def detect(
    image: np.ndarray,
    cal: Calibration,
    offset_px: float,
    plate: np.ndarray | None = None,
    channel: str = "plate",
    settings: DetectorSettings = DEFAULTS,
    slug: str | None = None,
    colour_check: bool = False,
) -> Detection:
    """Read one picture. ``plate`` is the real background plate when there is one.

    A video gives the plate as the per-pixel 20th percentile of about 100 frames
    (V-29). One screenshot cannot, so the stand-in is used and the score it earns
    is a floor rather than a ceiling: the real plate removed 27% of what the
    stand-in reported.

    ``colour_check`` turns on the second opinion of Task 2.3.4. It is off by
    default: it ships only if the score board improves.
    """
    started = time.perf_counter()
    runs = find_runs(image, cal, plate=plate, channel=channel, settings=settings)
    upper = int(round(cal.upper_line))

    refused: list[DetectedRun] = []
    if colour_check:
        from aitu_backend.video import colour

        verdicts = colour.off_palette(image, runs)
        kept = [run for run, bad in zip(runs, verdicts) if not bad]
        refused = [run for run, bad in zip(runs, verdicts) if bad]
        runs = kept

    onsets, sustains = window_rule(runs, upper, offset_px)
    window_rule(refused, upper, offset_px)
    return Detection(
        slug=slug,
        offset_px=offset_px,
        onsets=onsets,
        sustains=sustains,
        runs=runs,
        refused=refused,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )


# --------------------------------------------------- the baseline to beat ---


def detect_single_row(
    image: np.ndarray, cal: Calibration, rows_above: int = 2, settings: DetectorSettings = DEFAULTS
) -> list[int]:
    """One row of pixels just above the upper line — what most projects do.

    A key is on when the colour in its row differs from what that row looks like
    with nothing on it. It cannot say when inside the window the note started and
    it cannot tell an onset from a sustain, so every key it calls on is reported
    as an onset. Kept because it is the baseline every other idea has to beat, and
    it loses: twenty of the twenty one examples light the exact row it reads, so
    on eight of the nine it scored it called all 88 keys on.
    """
    upper = int(round(cal.upper_line))
    row = image[max(0, upper - rows_above)]
    on: list[int] = []
    for key in geometry.keys(cal):
        a = max(0, int(round(key.left)))
        b = min(image.shape[1], int(round(key.right)) + 1)
        if b - a < 2:
            continue
        quiet = np.median(image[:upper, a:b].reshape(-1, 3), axis=0)
        here = np.median(row[a:b], axis=0)
        if float(np.abs(here - quiet).max()) > settings.tau_foreground:
            on.append(key.midi)
    return sorted(on)
