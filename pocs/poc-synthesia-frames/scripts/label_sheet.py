"""Draw the band between the offset line and the upper line with the lanes and
the MIDI numbers, so the ground truth of Phase 1 can be read off the picture.

This is the small version of the annotation page of Task 2.2.2, and the reader
applies the same rule the detector applies (V-18): a key is an onset when a
rectangle tip is between the offset line and the upper line; a key is a sustain
when the rectangle already crossed the upper line and its last tip is still
above the offset line.

The picture is cut to the part of the width that has anything in it, because a
human reading forty empty lanes is a human making mistakes.
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import common

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ZOOM = 4
D_IN_KEYS = 2.0          # the offset line, in white key widths above the upper line


def _font(size: int):
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def sheet(slug: str, pad_keys: float = 1.5) -> list:
    cal = common.load_calibrations()[slug]
    img = common.load(slug)
    u, w = cal.upper_line, cal.white_width
    d = D_IN_KEYS * w
    top = max(0, int(u - 3.2 * w))
    band = img[top:int(u + 0.5 * w)]

    # Where is there anything at all? Take the columns that stand out from the
    # row background of the band.
    act = np.abs(band - np.median(band, axis=1, keepdims=True)).max(axis=2)
    col = (act > 20).mean(axis=0)
    busy = np.where(col > 0.02)[0]
    if busy.size:
        x0 = max(0, int(busy[0] - pad_keys * w))
        x1 = min(band.shape[1], int(busy[-1] + pad_keys * w))
    else:
        x0, x1 = 0, band.shape[1]

    im = Image.fromarray(band[:, x0:x1].astype("uint8"))
    im = im.resize((im.width * ZOOM, im.height * ZOOM), Image.LANCZOS)
    dr = ImageDraw.Draw(im, "RGBA")
    f = _font(15)
    uy = (u - top) * ZOOM
    dy = (u - d - top) * ZOOM

    for k in cal.keys():
        if not (x0 - w <= k["mid"] <= x1 + w):
            continue
        x = (k["mid"] - x0) * ZOOM
        colour = (255, 90, 90, 170) if k["kind"] == "black" else (120, 220, 255, 110)
        dr.line([x, 0, x, uy], fill=colour, width=1)
        ty = uy + 2 if k["kind"] == "white" else uy - 18
        fill = (255, 255, 0, 255) if k["kind"] == "white" else (255, 140, 140, 255)
        dr.text((x - 10, ty), str(k["midi"]), fill=fill, font=f)

    dr.line([0, uy, im.width, uy], fill=(0, 255, 0, 255), width=2)
    dr.line([0, dy, im.width, dy], fill=(255, 0, 255, 255), width=2)
    dr.text((6, dy + 3), f"offset line d={d:.0f}px", fill=(255, 0, 255, 255), font=f)

    out = common.OUT / "labels"
    out.mkdir(parents=True, exist_ok=True)
    return [stack(im, out / f"{slug}.jpg")]


def stack(im: Image.Image, path, width: int = 1400, gap: int = 10):
    """Cut a very wide picture into strips and pile them up, so one picture
    holds the whole band at a size a reader can actually read."""
    n = max(1, int(np.ceil(im.width / width)))
    step = int(np.ceil(im.width / n))
    out = Image.new("RGB", (min(width, im.width), n * im.height + (n - 1) * gap),
                    (40, 40, 40))
    for i in range(n):
        piece = im.crop((i * step, 0, min(im.width, (i + 1) * step), im.height))
        out.paste(piece, (0, i * (im.height + gap)))
    out.save(path, quality=92)
    return path


if __name__ == "__main__":
    for s in sys.argv[1:]:
        for p in sheet(s):
            print(p)
