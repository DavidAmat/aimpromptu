"""Task 1.2.2 — run the five candidates on the examples and draw what each saw.

One picture per example, the five detectors stacked, so a disagreement is
something you look at rather than something you imagine.
"""
from __future__ import annotations

import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import common
import detectors

ZOOM = 2
NAMES = ["absolute", "plate", "edges", "colour", "single-row"]
CHOSEN = ["derulo", "shut-up-and-dance", "7years", "feather",
          "not-immediate-strokes", "more-examples-9", "more-examples-10",
          "more-examples-12", "more-examples-3"]


def _font(size: int):
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def busy_range(img, cal) -> tuple[int, int]:
    u, w = int(round(cal.upper_line)), cal.white_width
    band = img[max(0, u - int(3.2 * w)):u]
    act = np.abs(band - np.median(band, axis=1, keepdims=True)).max(axis=2)
    cols = np.where((act > 20).mean(axis=0) > 0.02)[0]
    if not cols.size:
        return 0, img.shape[1]
    return (max(0, int(cols[0] - 1.5 * w)),
            min(img.shape[1], int(cols[-1] + 1.5 * w)))


def strip(img, cal, runs, onsets, sustains, x0, x1, title, d,
          band=(3.2, 0.0)) -> Image.Image:
    u, w = int(round(cal.upper_line)), cal.white_width
    top = max(0, u - int(band[0] * w))
    bottom = max(top + 4, u - int(band[1] * w))
    im = Image.fromarray(img[top:bottom + 2, x0:x1].astype("uint8")).convert("RGB")
    im = im.resize((im.width * ZOOM, im.height * ZOOM), Image.LANCZOS)
    dr = ImageDraw.Draw(im, "RGBA")
    uy = (u - top) * ZOOM
    dy = (u - d - top) * ZOOM
    for r in runs:
        dr.rectangle([(r["x0"] - x0) * ZOOM, (r["y_top"] - top) * ZOOM,
                      (r["x1"] - x0) * ZOOM, (r["y_bottom"] - top) * ZOOM],
                     outline=(255, 255, 0, 230), width=1)
        dr.line([(r["x0"] - x0) * ZOOM, (r["y_bottom"] - top) * ZOOM,
                 (r["x1"] - x0) * ZOOM, (r["y_bottom"] - top) * ZOOM],
                fill=(255, 0, 0, 255), width=2)
    for k in cal.keys():
        if k["midi"] in onsets or k["midi"] in sustains:
            colour = (0, 255, 0, 220) if k["midi"] in onsets else (0, 160, 255, 220)
            dr.rectangle([(k["left"] - x0) * ZOOM, uy - 5,
                          (k["right"] - x0) * ZOOM, uy + 3], fill=colour)
    dr.line([0, uy, im.width, uy], fill=(0, 255, 0, 255), width=1)
    dr.line([0, dy, im.width, dy], fill=(255, 0, 255, 255), width=1)
    dr.rectangle([0, 0, 340, 18], fill=(0, 0, 0, 190))
    dr.text((4, 2), title, fill=(255, 255, 255, 255), font=_font(13))
    return im


def main(only=None, band=(3.2, 0.0), tag=""):
    cals = common.load_calibrations()
    out = common.OUT / "detectors"
    out.mkdir(parents=True, exist_ok=True)
    table = []
    for slug in (only or CHOSEN):
        cal = cals[slug]
        img = common.load(slug)
        d = 2.0 * cal.white_width
        x0, x1 = busy_range(img, cal)
        pieces = []
        for name in NAMES:
            if name == "single-row":
                res = detectors.detect_single_row(img, cal, d)
            else:
                res = detectors.detect(img, cal, d, mask_name=name)
            u = int(round(cal.upper_line))
            band_top = u - int(band[0] * cal.white_width)
            band_bottom = u - int(band[1] * cal.white_width)
            shown = [r for r in res["runs"]
                     if band_top <= r["y_bottom"] <= band_bottom]
            res["runs"] = shown
            row = dict(example=slug, detector=name, runs=len(shown),
                       onsets=list(res["onsets"]), sustains=list(res["sustains"]))
            table.append(row)
            title = (f"{name}: {len(res['runs'])} runs, "
                     f"{len(res['onsets'])} onsets, {len(res['sustains'])} sustains")
            pieces.append(strip(img, cal, res["runs"], set(res["onsets"]),
                                set(res["sustains"]), x0, x1, title, d, band))
        gap = 6
        h = sum(p.height for p in pieces) + gap * (len(pieces) - 1)
        sheet = Image.new("RGB", (pieces[0].width, h), (30, 30, 30))
        y = 0
        for p in pieces:
            sheet.paste(p, (0, y))
            y += p.height + gap
        from label_sheet import stack
        stack(sheet, out / f"{slug}{tag}.jpg", width=1500)
        print(f"{slug:24s} " + "  ".join(
            f"{r['detector']}={r['runs']}" for r in table[-5:]))
    (common.OUT / "detectors" / f"counts{tag}.json").write_text(
        json.dumps(table, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
