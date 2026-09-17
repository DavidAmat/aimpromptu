"""Downscale the example screenshots so they can be looked at, and report their size."""
import pathlib, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
EX = ROOT / ("context/implementations/04-synthesia-to-notes/examples")
OUT = ROOT / "poc-synthesia-frames/out/thumbs"
OUT.mkdir(parents=True, exist_ok=True)

rows = []
for p in sorted(EX.glob("*.png")):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    scale = 1100 / max(w, h)
    if scale < 1:
        im2 = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    else:
        im2 = im
    im2.save(OUT / (p.stem + ".jpg"), quality=82)
    rows.append((p.stem, w, h, round(w / h, 3)))

for name, w, h, ar in rows:
    print(f"{name:26s} {w:5d}x{h:<5d} ar={ar}")
