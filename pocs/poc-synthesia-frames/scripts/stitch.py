"""Stack the sampled frames into one long roll and see whether a note is one
shape in it.

If the scroll speed is stable, the top `shift` rows of each sampled frame are
exactly the strip of the roll that has not been seen yet, so piling them up
rebuilds the whole piece as one tall picture in which the vertical axis is time.
A note is then one connected shape with a top row and a bottom row, and both
convert straight to seconds. This is the alternative to following a rectangle
from frame to frame, and it is written down here so Phase 4 can choose with a
picture in front of it.
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image

import common
import scroll_speed


def build(i0: int, i1: int, shift: float, upper: int, bg: np.ndarray,
          top_skip: int = 40) -> np.ndarray:
    paths = scroll_speed.frames()[i0:i1]
    step = int(round(shift))
    strips = []
    for p in paths:
        img = scroll_speed.load_frame(p)
        diff = np.abs(img[:upper] - bg[:upper]).max(axis=2)
        strips.append(diff[top_skip: top_skip + step])
    return np.flipud(np.concatenate(strips[::-1], axis=0))


def main(seconds: float = 12.0):
    import find_keyboard
    paths = scroll_speed.frames()
    bg = np.load(common.DATA / "video" / "plate.npy")
    cal = find_keyboard.find(scroll_speed.load_frame(paths[len(paths) // 2]), "video")
    upper = int(round(cal.upper_line))
    i0 = 700
    i1 = i0 + int(seconds * 10)
    roll = build(i0, i1, 15.84, upper, bg)
    print(f"stitched {i1 - i0} sampled frames into {roll.shape[0]} rows "
          f"({seconds:.0f} s of music)")
    out = common.OUT / "stitch"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.fromarray(np.clip(roll * 2.2, 0, 255).astype("uint8"))
    # Half width, so the whole thing fits on one screen.
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im.save(out / "roll.jpg", quality=88)
    print(out / "roll.jpg", im.size)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 12.0)


def measure(seconds: float = 30.0, i0: int = 700, shift: float = 15.84,
            sample_ms: int = 100):
    """Count the notes in the stitched roll and check their shape."""
    from scipy import ndimage
    import find_keyboard

    paths = scroll_speed.frames()
    bg = np.load(common.DATA / "video" / "plate.npy")
    cal = find_keyboard.find(scroll_speed.load_frame(paths[len(paths) // 2]), "video")
    upper = int(round(cal.upper_line))
    roll = build(i0, i0 + int(seconds * 1000 / sample_ms), shift, upper, bg)

    mask = roll > 24
    labels, n = ndimage.label(mask)
    keys = cal.keys()
    mids = np.array([k["mid"] for k in keys])

    widths, heights, dists = [], [], []
    kept = 0
    px_per_second = shift * 1000 / sample_ms
    for sl in ndimage.find_objects(labels):
        ys, xs = sl
        h, w = ys.stop - ys.start, xs.stop - xs.start
        if h < 4 or w < 6:
            continue
        kept += 1
        widths.append(w / cal.white_width)
        heights.append(h / px_per_second * 1000)
        mid = (xs.start + xs.stop - 1) / 2
        dists.append(float(np.min(np.abs(mids - mid))) / cal.white_width)

    widths = np.asarray(widths)
    heights = np.asarray(heights)
    dists = np.asarray(dists)
    print(f"{seconds:.0f} s of music, {roll.shape[0]} rows, "
          f"{n} shapes, {kept} kept after dropping specks")
    print(f"notes per second: {kept / seconds:.1f}")
    print(f"width  in white key widths: median {np.median(widths):.2f}, "
          f"5th..95th {np.percentile(widths, 5):.2f}..{np.percentile(widths, 95):.2f}")
    print(f"length in ms:               median {np.median(heights):.0f}, "
          f"5th..95th {np.percentile(heights, 5):.0f}..{np.percentile(heights, 95):.0f}")
    print(f"distance from the nearest key midpoint, in white key widths: "
          f"median {np.median(dists):.3f}, 95th {np.percentile(dists, 95):.3f}, "
          f"worst {dists.max():.3f}")
    print(f"shapes whose midpoint is more than a quarter key from any key: "
          f"{int((dists > 0.25).sum())} of {kept}")
