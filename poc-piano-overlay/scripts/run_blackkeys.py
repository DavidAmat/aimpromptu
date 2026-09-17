"""Run the black key finder on every picture and draw what it found."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from PIL import Image, ImageDraw
from common import *
from blackkeys import find_black_keys, BLACK_NAMES

def main():
    rects = load_rects()
    sheets = []
    for slug in slugs():
        g = rectify(grey(load_rgb(slug)), rects[slug])
        r = find_black_keys(g)
        seen = sum(k.seen for k in r.keys); extra = [k for k in r.keys if not k.seen]
        conf = sum(k.confirmed for k in extra)
        first = r.keys[0] if r.keys else None
        print(f"{slug:24s} depth={r.depth:3d} cands={len(r.candidates):2d} keys={len(r.keys):2d} seen={seen:2d} "
              f"extrapolated={len(extra):2d} confirmed={conf:2d} thrown={len(r.thrown_out):2d} "
              f"semitone={r.semitone_px:5.2f} cost={r.cost:6.2f} runner={r.runner_up:6.2f} conf={r.confidence:.2f} "
              f"first={BLACK_NAMES[first.position] if first else "-"}", flush=True)
        im = Image.fromarray(np.clip(g[:150],0,255).astype(np.uint8)).convert("RGB")
        d = ImageDraw.Draw(im)
        d.line((0, r.depth, 1280, r.depth), fill=(0,255,0))
        for c in r.thrown_out:
            d.rectangle((c.u0, 2, c.u1-1, r.depth-2), outline=(255,0,255))
        for k in r.keys:
            col = (0,255,0) if k.seen else ((255,200,0) if k.confirmed else (255,0,0))
            d.rectangle((k.centre-k.width/2, 2, k.centre+k.width/2, r.depth-2), outline=col)
            d.text((k.centre-5, r.depth+2), BLACK_NAMES[k.position], fill=col)
        d.rectangle((0,0,150,12), fill=(0,0,0)); d.text((2,1), f"{slug} conf={r.confidence:.2f}", fill=(255,255,0))
        sheets.append(im)
    for i in range(0, len(sheets), 8):
        grp = sheets[i:i+8]
        sheet = Image.new("RGB", (1280, 150*len(grp)))
        for j, im in enumerate(grp): sheet.paste(im, (0, j*150))
        sheet.save(OUT / f"blackkeys{i//8}.png")

if __name__ == "__main__":
    main()
