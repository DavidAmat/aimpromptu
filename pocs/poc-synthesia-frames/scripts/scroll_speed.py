"""Task 1.2.3 — is the scroll speed constant, and can it be measured from a pair
of sampled frames?

V-05 turns a distance into a time and V-06 says the speed is measured, never
assumed. Both stand or fall here. The measurement: for every pair of consecutive
sampled frames, the vertical shift that best aligns the roll band of one with
the next, found by cross correlating the row profile of the two bands and then
fitting a parabola to the peak for the part of a pixel.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from PIL import Image

import common

VIDEO = common.DATA / "video"


def frames() -> list[pathlib.Path]:
    return sorted((VIDEO / "frames").glob("f*.jpg"))


def load_frame(p: pathlib.Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)


def plate(paths: list[pathlib.Path], n: int = 50) -> np.ndarray:
    """V-15: the per-pixel median of frames spread over the whole video."""
    pick = np.linspace(0, len(paths) - 1, n).round().astype(int)
    stack = np.stack([load_frame(paths[i]) for i in pick])
    return np.median(stack, axis=0)


def profile(img: np.ndarray, plate_img: np.ndarray, upper: int,
            top_frac: float = 0.15) -> np.ndarray:
    """One number per row of the roll band: how much of that row is not
    background. A falling rectangle moves this profile down with it."""
    band = img[int(upper * top_frac):upper]
    base = plate_img[int(upper * top_frac):upper]
    return np.abs(band - base).max(axis=2).mean(axis=1)


def shift(a: np.ndarray, b: np.ndarray, max_lag: int) -> tuple[float, float]:
    """How far b has moved down relative to a, and how sharp the answer is."""
    a = a - a.mean()
    b = b - b.mean()
    n = 1 << int(np.ceil(np.log2(len(a) * 2)))
    corr = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    corr = np.concatenate([corr[-max_lag:], corr[: max_lag + 1]])
    lags = np.arange(-max_lag, max_lag + 1)
    k = int(np.argmax(corr))
    if 0 < k < len(corr) - 1:
        y0, y1, y2 = corr[k - 1], corr[k], corr[k + 1]
        denom = y0 - 2 * y1 + y2
        sub = 0.5 * (y0 - y2) / denom if denom != 0 else 0.0
    else:
        sub = 0.0
    peak = float(corr[k])
    second = float(np.max(np.delete(corr, slice(max(0, k - 3), k + 4))))
    sharp = peak / second if second > 0 else float("inf")
    return float(lags[k] + sub), sharp


def main(upper: float | None = None, sample_ms: int = 100):
    paths = frames()
    if not paths:
        raise SystemExit("no sampled frames; run the ffmpeg step first")
    print(f"{len(paths)} sampled frames at {sample_ms} ms")

    mid = load_frame(paths[len(paths) // 2])
    if upper is None:
        import find_keyboard
        cal = find_keyboard.find(mid, "video")
        upper = cal.upper_line
        print(f"upper line found at {upper:.0f}, white key width "
              f"{cal.white_width:.2f}, {cal.white_count} white keys")
    upper = int(round(upper))

    print("building the background plate from 50 frames spread over the video")
    bg = plate(paths)
    np.save(VIDEO / "plate.npy", bg)
    Image.fromarray(bg.astype("uint8")).save(VIDEO / "plate.jpg", quality=90)

    prev = profile(load_frame(paths[0]), bg, upper)
    speeds, sharps = [], []
    for p in paths[1:]:
        cur = profile(load_frame(p), bg, upper)
        s, sharp = shift(prev, cur, max_lag=upper // 3)
        speeds.append(s)
        sharps.append(sharp)
        prev = cur
    speeds = np.asarray(speeds)
    sharps = np.asarray(sharps)

    # Frames with nothing falling cannot answer; they are reported, not averaged.
    usable = sharps > 1.15
    good = speeds[usable]
    med = float(np.median(good))
    q1, q3 = np.percentile(good, [25, 75])
    per_second = med * 1000 / sample_ms

    print(f"\nusable frame pairs: {usable.sum()} of {len(speeds)}")
    print(f"shift per sampled frame: median {med:.2f} px, "
          f"quartiles {q1:.2f}..{q3:.2f}, spread {q3 - q1:.2f} px")
    print(f"scroll speed: {per_second:.1f} px/s")
    print(f"5th..95th percentile: {np.percentile(good, 5):.2f}"
          f"..{np.percentile(good, 95):.2f} px per sampled frame")

    # What the spread costs in milliseconds of onset error: a rectangle tip one
    # roll height above the upper line, timed with the median speed instead of
    # the true one.
    for dist_name, dist in (("one sampled frame", med), ("half the roll", upper / 2),
                            ("the whole roll", upper)):
        err_q = abs(dist / med - dist / q3) * sample_ms
        err_9 = abs(dist / med - dist / np.percentile(good, 95)) * sample_ms
        print(f"a tip {dist:6.1f} px up, timed with the median speed: "
              f"{err_q * 1:6.1f} ms off at the upper quartile, "
              f"{err_9:6.1f} ms at the 95th percentile   ({dist_name})")

    (VIDEO / "scroll_speed.json").write_text(json.dumps(dict(
        sample_ms=sample_ms, upper_line=upper, n_pairs=len(speeds),
        usable=int(usable.sum()), median_px_per_frame=med,
        q1=float(q1), q3=float(q3), px_per_second=per_second,
        p5=float(np.percentile(good, 5)), p95=float(np.percentile(good, 95)),
        speeds=[round(float(x), 3) for x in speeds],
    ), indent=2) + "\n")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else None)
