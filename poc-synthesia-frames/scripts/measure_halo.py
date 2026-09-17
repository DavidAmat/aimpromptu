"""How far above the upper line does the light reach?

V-08 says nothing is trusted inside the halo guard band and that its height is a
calibration value. The plan's first guess was 12 rows. This measures it: for
every row above the upper line, how much of the width is much brighter than the
quiet part of the roll. The halo is the band where that fraction stays high
across the whole width, because the glow line lights the whole upper line, and a
falling rectangle lights one lane.
"""
from __future__ import annotations

import numpy as np

import common


def measure(img: np.ndarray, cal) -> dict:
    u, w = int(round(cal.upper_line)), cal.white_width
    band = img[max(0, u - int(6 * w)):u].mean(axis=2)
    if band.shape[0] < 10:
        return {}
    quiet = float(np.percentile(band[: band.shape[0] // 3], 50))
    lit = band > quiet + 40
    # Washed out, not merely lit: a rectangle is drawn in a colour, the halo is
    # drawn in light, and only light saturates. This is the band where a tip
    # cannot be read from the pixels at all.
    blown = band > 235
    frac = lit.mean(axis=1)            # per row, share of the width that is lit
    # Walk up from the upper line while more than half the width is lit.
    h = 0
    for i in range(1, len(frac)):
        if frac[-i] < 0.5:
            break
        h = i
    # The glow line lights the whole width. A struck key also blooms around
    # itself, and that local bloom is what hides a rectangle tip, so it is
    # measured separately: per column, how far up it stays lit.
    # Per column, the run of lit pixels that touches the upper line, with gaps
    # of two rows closed. It has to touch the line: a sparkle or a title high in
    # the roll is bright too, and it is not the halo. This is the band where a
    # rectangle tip cannot be separated from the light the strike emits.
    reach = []
    for x in range(lit.shape[1]):
        col = lit[:, x]
        i, misses = 0, 0
        while i < len(col):
            if col[-1 - i]:
                misses = 0
            else:
                misses += 1
                if misses > 2:
                    break
            i += 1
        run = i - misses
        if run > 0:
            reach.append(run)
    busy = np.asarray(reach)
    p90 = float(np.percentile(busy, 90)) if busy.size else 0.0
    return dict(halo_rows=h, halo_keys=h / w,
                bloom_rows=p90, bloom_keys=p90 / w,
                lit_at_line=float(frac[-1]), quiet=quiet,
                band_rows=band.shape[0])


def main():
    cals = common.load_calibrations()
    print(f"{'example':24s} {'line rows':>9s} {'keys':>5s} {'bloom rows':>10s} "
          f"{'keys':>5s} {'lit at line':>11s}")
    rows = []
    for slug in common.slugs():
        m = measure(common.load(slug), cals[slug])
        if not m:
            print(f"{slug:24s} band too short")
            continue
        rows.append(m)
        print(f"{slug:24s} {m['halo_rows']:9d} {m['halo_keys']:5.2f} "
              f"{m['bloom_rows']:10.0f} {m['bloom_keys']:5.2f} "
              f"{m['lit_at_line']:11.2f}")
    hk = [r["halo_keys"] for r in rows]
    bk = [r["bloom_keys"] for r in rows]
    ww = float(np.median([c.white_width for c in cals.values()]))
    print(f"\nglow line, in white key widths: median {np.median(hk):.2f} "
          f"max {max(hk):.2f}")
    print(f"local bloom, in white key widths: median {np.median(bk):.2f} "
          f"max {max(bk):.2f}")
    print(f"the plan guessed a 12 row guard band = {12 / ww:.2f} white keys "
          f"at this resolution ({ww:.1f} px per white key)")


if __name__ == "__main__":
    main()
