"""Find the piano overlay in an example screenshot, without the user.

The app will not do this in v1 — V-09 says the user calibrates. This exists for
two reasons: the research spike needs a calibration for every example before it
can compare detectors, and the answer to "could the app suggest the overlay
later" is worth measuring now.

How it works, in one line each:

1. the keyboard is the only part of the picture that repeats with the octave,
   so every row is scored by the strength of its horizontal autocorrelation
   peak, and the band of high scoring rows is the keyboard;
2. the octave period divided by seven is the white key width;
3. the phase and the pitch class of the leftmost white key come from matching
   the pattern of two and three black keys against a strip just below the top
   of the keyboard.
"""
from __future__ import annotations

import numpy as np

from common import BLACK_IN_OCTAVE, Calibration, WHITE_PITCH_CLASSES


def _row_profiles(img: np.ndarray) -> np.ndarray:
    """Grey, high passed along x, one row per picture row."""
    grey = img.mean(axis=2)
    k = max(3, int(grey.shape[1] / 12) | 1)
    kernel = np.ones(k) / k
    smooth = np.apply_along_axis(lambda r: np.convolve(r, kernel, mode="same"), 1, grey)
    return grey - smooth


def _best_period(profile: np.ndarray, lo: int, hi: int) -> tuple[int, float]:
    """The lag in [lo, hi] with the strongest normalised autocorrelation."""
    x = profile - profile.mean()
    denom = float(np.dot(x, x))
    if denom <= 1e-6:
        return 0, 0.0
    n = 1 << int(np.ceil(np.log2(len(x) * 2)))
    f = np.fft.rfft(x, n)
    ac = np.fft.irfft(f * np.conj(f), n)[: len(x)] / denom
    lags = np.arange(lo, min(hi, len(ac) - 1))
    if len(lags) == 0:
        return 0, 0.0
    best = int(lags[np.argmax(ac[lags])])
    return best, float(ac[best])


def find(img: np.ndarray, slug: str) -> Calibration:
    h, w = img.shape[:2]
    prof = _row_profiles(img)
    lo, hi = max(8, int(0.05 * w)), int(0.50 * w)

    periods = np.zeros(h, dtype=int)
    scores = np.zeros(h)
    for y in range(h):
        periods[y], scores[y] = _best_period(prof[y], lo, hi)

    # The keyboard is the longest run of rows whose score is high. A row of the
    # roll can score high by accident; a run of eighty of them cannot.
    good = scores > max(0.30, 0.6 * np.percentile(scores, 99))
    runs, start = [], None
    for y in range(h):
        if good[y] and start is None:
            start = y
        elif not good[y] and start is not None:
            runs.append((start, y))
            start = None
    if start is not None:
        runs.append((start, h))
    if not runs:
        raise RuntimeError(f"{slug}: no keyboard band found")
    y0, y1 = max(runs, key=lambda r: r[1] - r[0])

    octave = float(np.median(periods[y0:y1]))
    white_width = octave / 7.0
    white_count = int(round((w - 0) / white_width))

    # Refine the top edge: walk up from inside the band while the row still
    # looks like the keyboard, then take the first row that does not.
    upper = y0

    # Phase and pitch class, from the black key pattern.
    band0 = int(upper + 0.35 * white_width)
    band1 = int(upper + 2.0 * white_width)
    band1 = min(band1, h - 1)
    if band1 <= band0 + 1:
        band1 = min(h - 1, band0 + 3)
    strip = np.median(img[band0:band1].mean(axis=2), axis=0)

    # One hypothesis per pitch class of the leftmost white key. Sliding the
    # whole overlay right by one white key and naming the next pitch class
    # describes the same keyboard, so hypotheses are grouped by where they put
    # the first C and only the best of each group is kept. Without that the
    # runner up is the winner wearing a different label, and the margin below
    # would mean nothing.
    octave_width = 7 * white_width
    groups: dict[int, tuple[float, float, int]] = {}
    for pc_index, pc in enumerate(WHITE_PITCH_CLASSES):
        best_shift = max(
            (
                (_pattern_score(strip, shift, white_width, pc_index), shift)
                for shift in np.arange(0.0, white_width, white_width / 80)
            ),
            key=lambda t: t[0],
        )
        sc, shift = best_shift
        c_pos = (shift + white_width * ((7 - pc_index) % 7)) % octave_width
        key = int(round(c_pos / white_width)) % 7
        if key not in groups or sc > groups[key][0]:
            groups[key] = (sc, shift, pc)
    ranked = sorted(groups.values(), reverse=True)
    score, left, pc = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else float("-inf")
    # The leftmost white key is often cut by the edge of the picture. Keep it
    # when at least half of it shows, so the lane still holds a whole rectangle.
    if left >= 0.5 * white_width:
        left -= white_width
        pc = WHITE_PITCH_CLASSES[(WHITE_PITCH_CLASSES.index(pc) - 1) % 7]
    white_count = int(np.floor((w - left) / white_width))

    return Calibration(
        slug=slug,
        upper_line=float(upper),
        left_border=float(left),
        white_width=float(white_width),
        white_count=int(white_count),
        first_white_pc=int(pc),
        first_white_octave=_guess_octave(white_count, pc),
        note=f"auto pattern={score:.1f} runnerUp={runner_up:.1f} "
             f"acf={float(np.median(scores[y0:y1])):.2f}",
    )


def _pattern_score(strip: np.ndarray, left: float, w: float, pc_index: int) -> float:
    """Bright where a white key top shows, dark where a black key sits."""
    n = int((len(strip) - left) / w)
    if n < 8:
        return -1e9
    bright, dark = [], []
    for i in range(n - 1):
        pc_a = WHITE_PITCH_CLASSES[(pc_index + i) % 7]
        pc_b = WHITE_PITCH_CLASSES[(pc_index + i + 1) % 7]
        x = left + w * (i + 1)
        if not (0 <= x < len(strip)):
            continue
        sample = strip[max(0, int(x - w * 0.18)): int(x + w * 0.18) + 1]
        if sample.size == 0:
            continue
        gap = (pc_b - pc_a) % 12
        # The 75th percentile, not the mean: two white keys are separated by a
        # thin dark line, and the mean over the window lets that line pretend
        # the boundary is a black key.
        (dark if gap == 2 else bright).append(float(np.percentile(sample, 75)))
    if not bright or not dark:
        return -1e9
    return float(np.mean(bright) - np.mean(dark))


def _guess_octave(white_count: int, pc: int) -> int:
    """The octave of the leftmost white key.

    A keyboard that shows about 52 white keys is the 88 key one, which starts at
    A0, so A and B are octave 0 and everything else is octave 1. A shorter one is
    centred on middle C, which is the best guess there is without the user. In
    the app this is a dropdown (V-10); here it only has to be sane.
    """
    if white_count >= 48:
        return 0 if pc in (9, 11) else 1
    wi = WHITE_PITCH_CLASSES.index(pc)
    best, best_d = 4, 1e9
    for octave in range(0, 7):
        mid_index = wi + white_count // 2
        midi = 12 * (octave + mid_index // 7 + 1) + WHITE_PITCH_CLASSES[mid_index % 7]
        if abs(midi - 60) < best_d:
            best, best_d = octave, abs(midi - 60)
    return best
