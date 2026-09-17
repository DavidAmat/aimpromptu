"""Is the white key width the same across the picture?

Task 2.1.1 builds the piano overlay from one white key and one black key, which
only works if every white key has the same width. A keyboard photographed at an
angle does not: the keys near the edges are narrower. This measures how far each
example is from uniform, by finding the octave period separately in the left,
the middle and the right third of the keyboard.
"""
from __future__ import annotations

import numpy as np

import common
from find_keyboard import _best_period


def octave_in_window(img, cal, x0: int, x1: int) -> float:
    u, w = cal.upper_line, cal.white_width
    strip = img[int(u + 0.35 * w): int(u + 2.0 * w), x0:x1].mean(axis=2)
    prof = np.median(strip, axis=0)
    prof = prof - np.convolve(prof, np.ones(9) / 9, mode="same")
    lo, hi = int(6.0 * w), int(8.5 * w)
    lag, _ = _best_period(prof, lo, min(hi, len(prof) - 2))
    return lag / 7.0


def main():
    cals = common.load_calibrations()
    print(f"{'example':24s} {'left':>6s} {'mid':>6s} {'right':>6s} {'spread':>7s}")
    rows = []
    for slug in common.slugs():
        cal = cals[slug]
        img = common.load(slug)
        w = img.shape[1]
        thirds = [octave_in_window(img, cal, a, b) for a, b in
                  ((0, w // 3), (w // 3, 2 * w // 3), (2 * w // 3, w))]
        if min(thirds) <= 0:
            print(f"{slug:24s} could not measure")
            continue
        spread = (max(thirds) - min(thirds)) / np.mean(thirds)
        rows.append((slug, thirds, spread))
        print(f"{slug:24s} {thirds[0]:6.2f} {thirds[1]:6.2f} {thirds[2]:6.2f} "
              f"{100 * spread:6.1f}%")
    worst = max(rows, key=lambda r: r[2])
    print(f"\nworst: {worst[0]} at {100 * worst[2]:.1f}%")
    print(f"median spread: {100 * np.median([r[2] for r in rows]):.1f}%")


if __name__ == "__main__":
    main()
