"""Read the thin dark lines on every picture and draw them on ruled crops for the eye.

Writes `out/lines/<slug>.png` — three octaves of the front of the keys at 2.5x,
with the two reading rows, every line found (cyan), its extension to the top
edge (yellow tick on the top row), and the found black keys (green) — and a
draft of the truth in `data/truth-draft.json`, to be checked by eye and then
copied to `data/truth.json` with the rejected lines removed.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from PIL import Image, ImageDraw
from common import *
from blackkeys import find_black_keys, BLACK_NAMES, candidates
from lines import keyboard_bottom, read_lines, top_edge_lines

def main():
    rects = load_rects()
    draft = {}
    (OUT / "lines").mkdir(parents=True, exist_ok=True)
    for slug in slugs():
        g = rectify(grey(load_rgb(slug)), rects[slug])
        r = find_black_keys(g)
        black_cols = np.zeros(g.shape[1], dtype=bool)
        for k in r.keys:
            a, b = int(k.centre - k.width/2), int(k.centre + k.width/2) + 1
            black_cols[max(0,a):b] = True
        bottom = keyboard_bottom(g, r.depth, black_cols)
        width = float(np.median([k.width for k in r.keys])) if r.keys else 14.0
        lines, v_high, v_low = read_lines(g, r.depth, bottom, width)
        draft[slug] = {
            "depth": r.depth, "bottom": bottom, "v_high": v_high, "v_low": v_low,
            "black_keys": [{"index": k.index, "name": BLACK_NAMES[k.position], "centre": round(k.centre, 2),
                             "width": k.width, "seen": k.seen, "confirmed": k.confirmed} for k in r.keys],
            "lines": [{"u_high": round(l.u_high, 2), "u_low": round(l.u_low, 2), "u_top": round(l.at(0, v_high, v_low), 2),
                        "strength": round(l.strength, 1), "paired": l.paired} for l in lines],
            "top_edge": [round(u, 2) for u in top_edge_lines(g, r.depth, black_cols)],
        }
        print(f"{slug:24s} depth={r.depth:3d} bottom={bottom:3d} rows={v_high},{v_low} lines={len(lines):3d} keys={len(r.keys)}", flush=True)
        # review crop: rows 0..bottom+4, three windows of ~3 octaves: left, middle, right
        strip = np.clip(g[: min(g.shape[0], bottom + 6)], 0, 255).astype(np.uint8)
        im = Image.fromarray(strip).convert("RGB")
        d = ImageDraw.Draw(im)
        d.line((0, v_high, 1280, v_high), fill=(255, 0, 0)); d.line((0, v_low, 1280, v_low), fill=(255, 0, 0))
        d.line((0, r.depth, 1280, r.depth), fill=(0, 160, 0))
        for k in r.keys:
            col = (0, 255, 0) if k.seen else (255, 200, 0)
            d.rectangle((k.centre - k.width/2, 1, k.centre + k.width/2, r.depth - 1), outline=col)
        for l in lines:
            d.line((l.u_high, v_high - 4, l.u_high, v_high + 4), fill=(0, 255, 255))
            d.line((l.u_low, v_low - 4, l.u_low, v_low + 4), fill=(0, 255, 255))
            d.line((l.u_high, v_high, l.u_low, v_low), fill=(0, 200, 255))
            ut = l.at(0, v_high, v_low)
            d.line((ut, 0, ut, 6), fill=(255, 255, 0))
        # rules every 10 px along u on the top row
        for x in range(0, 1280, 10):
            d.line((x, im.height - 3, x, im.height - 1), fill=(255, 0, 255) if x % 50 == 0 else (120, 0, 120))
        zoom = 2.5
        pieces = []
        for x0 in (0, 440, 880):
            crop = im.crop((x0, 0, min(1280, x0 + 400), im.height)).resize((int(400 * zoom), int(im.height * zoom)), Image.Resampling.NEAREST)
            dd = ImageDraw.Draw(crop); dd.rectangle((0, 0, 160, 12), fill=(0, 0, 0)); dd.text((2, 1), f"{slug} u={x0}..{x0+400}", fill=(255, 255, 0))
            pieces.append(crop)
        sheet = Image.new("RGB", (pieces[0].width, sum(p.height for p in pieces)))
        y = 0
        for p in pieces:
            sheet.paste(p, (0, y)); y += p.height
        sheet.save(OUT / "lines" / f"{slug}.png")
    (DATA / "truth-draft.json").write_text(json.dumps(draft, indent=1) + "\n")

if __name__ == "__main__":
    main()
