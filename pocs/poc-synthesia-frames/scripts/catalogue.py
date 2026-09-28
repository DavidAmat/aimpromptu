"""The measurable half of the casuistry catalogue.

The style of a rectangle is read by eye and lives in the phase report. What a
program can measure is measured here, so the report's table has numbers in the
columns that can have them.
"""
from __future__ import annotations

import numpy as np

import common
import measure_halo


def row(slug: str) -> dict:
    cal = common.load_calibrations()[slug]
    img = common.load(slug)
    u, w = int(round(cal.upper_line)), cal.white_width
    keys = cal.keys()
    roll = img[:u]
    grey = roll.mean(axis=2)
    halo = measure_halo.measure(img, cal)

    # Contrast: how far the brightest tenth of the roll sits above the quietest
    # half of it. A shallow rectangle is one where this is small.
    quiet = float(np.percentile(grey, 50))
    bright = float(np.percentile(grey, 99))
    # Colour: how far the roll's colours stray from grey.
    chroma = float(np.percentile(roll.max(axis=2) - roll.min(axis=2), 99))
    return dict(
        slug=slug, keys=len(keys), first=keys[0]["midi"], last=keys[-1]["midi"],
        white_width=round(w, 1), roll_rows=u,
        roll_keys=round(u / w, 1),
        contrast=round(bright - quiet),
        chroma=round(chroma),
        glow_line_keys=round(halo["halo_keys"], 2),
        guard_keys=round(halo["bloom_keys"], 2),
        lit_at_line=round(halo["lit_at_line"], 2),
    )


def main():
    rows = [row(s) for s in common.slugs()]
    head = ("example", "keys", "first", "last", "wkey", "roll", "roll/key",
            "contr", "chroma", "glow", "guard", "lit")
    print(f"{head[0]:24s} {head[1]:>4s} {head[2]:>5s} {head[3]:>4s} "
          f"{head[4]:>5s} {head[5]:>5s} {head[6]:>7s} {head[7]:>5s} "
          f"{head[8]:>6s} {head[9]:>5s} {head[10]:>5s} {head[11]:>4s}")
    for r in rows:
        print(f"{r['slug']:24s} {r['keys']:4d} {r['first']:5d} {r['last']:4d} "
              f"{r['white_width']:5.1f} {r['roll_rows']:5d} {r['roll_keys']:7.1f} "
              f"{r['contrast']:5d} {r['chroma']:6d} {r['glow_line_keys']:5.2f} "
              f"{r['guard_keys']:5.2f} {r['lit_at_line']:4.2f}")
    print()
    print(f"roll height, in white key widths: median "
          f"{np.median([r['roll_keys'] for r in rows]):.1f}, "
          f"min {min(r['roll_keys'] for r in rows):.1f}, "
          f"max {max(r['roll_keys'] for r in rows):.1f}")
    print(f"contrast: median {np.median([r['contrast'] for r in rows]):.0f}, "
          f"min {min(r['contrast'] for r in rows)}")
    print(f"chroma: median {np.median([r['chroma'] for r in rows]):.0f}, "
          f"below 40 (all but grey): "
          f"{[r['slug'] for r in rows if r['chroma'] < 40]}")


if __name__ == "__main__":
    main()
