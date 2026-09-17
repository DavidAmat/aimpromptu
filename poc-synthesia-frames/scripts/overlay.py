"""Draw a calibration on a picture so a human can see whether it is right."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from common import Calibration


def draw(img: np.ndarray, cal: Calibration, path, lanes=False, runs=None,
         crop_to_roll: bool = False) -> None:
    im = Image.fromarray(img.astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    u = cal.upper_line
    keys = cal.keys()

    if lanes:
        for i, lane in enumerate(cal.lanes()):
            shade = (0, 255, 255, 26) if i % 2 == 0 else (255, 0, 255, 26)
            d.rectangle([lane["x0"], 0, lane["x1"], u], fill=shade)

    for k in keys:
        colour = (255, 80, 80, 255) if k["kind"] == "black" else (80, 200, 255, 255)
        top = u + (cal.white_width * 3.1 if k["kind"] == "black" else cal.white_width * 4.8)
        d.rectangle([k["left"], u, k["right"], min(top, im.height - 1)],
                    outline=colour, width=1)
        d.line([k["mid"], u, k["mid"], u + cal.white_width * 0.6],
               fill=(255, 255, 0, 180), width=1)

    d.line([0, u, im.width, u], fill=(0, 255, 0, 255), width=2)

    if runs:
        for r in runs:
            d.rectangle([r["x0"], r["y_top"], r["x1"], r["y_bottom"]],
                        outline=(255, 255, 0, 255), width=1)
            d.line([r["x0"], r["y_bottom"], r["x1"], r["y_bottom"]],
                   fill=(255, 0, 0, 255), width=2)

    if crop_to_roll:
        im = im.crop((0, 0, im.width, min(im.height, int(u + cal.white_width * 5.2))))
    im.save(path, quality=88)
