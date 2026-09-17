"""A zoomed crop of the calibration overlay, to check the key borders by eye."""
import sys
from PIL import Image
import numpy as np
import common, overlay

slug, x0, x1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
cal = common.load_calibrations()[slug]
img = common.load(slug)
tmp = common.OUT / "zoom"
tmp.mkdir(parents=True, exist_ok=True)
p = tmp / f"{slug}_full.jpg"
overlay.draw(img, cal, p)
im = Image.open(p)
y0 = int(cal.upper_line - cal.white_width * 1.5)
y1 = int(cal.upper_line + cal.white_width * 3.4)
crop = im.crop((int(x0), max(0, y0), int(x1), min(im.height, y1)))
crop = crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST)
crop.save(tmp / f"{slug}_zoom.jpg", quality=90)
print(tmp / f"{slug}_zoom.jpg", crop.size)
