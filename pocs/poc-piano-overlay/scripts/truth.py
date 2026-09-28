"""The truth: white key borders read in the front of the keys and checked.

Task 1.1.1. The draft comes from `run_lines.py`: every thin dark line the reader
found on two rows in the front of the keys. This script keeps a line as a truth
border when it passes three checks a person applies by eye, draws every picture
with the kept lines in cyan and the rejected ones in magenta for the eye to
confirm, and writes `data/truth.json`:

1. the line was found on both rows, so it has a direction;
2. its lean agrees with its neighbours' — perspective changes the lean
   smoothly across the keyboard, a hand does not;
3. it is not a duplicate: two lines closer than 0.55 white key widths are one
   border or a hand's edge, and the stronger one is kept.

Task 1.1.2 (the families) and Task 1.1.4 (the perspective) are tables computed
from the same truth, printed at the end.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from PIL import Image, ImageDraw

from common import DATA, OUT, load_rects, load_rgb, grey, rectify, slugs


def eye_rejections(slug: str) -> list[float]:
    path = DATA / "eye-rejections.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [float(u) for u in raw.get(slug, [])]


def keep_lines(entry: dict, slug: str | None = None) -> tuple[list[dict], list[dict]]:
    lines = sorted(entry["lines"], key=lambda l: l["u_high"])
    by_eye = eye_rejections(slug) if slug else []
    v_high, v_low = entry["v_high"], entry["v_low"]
    black = [k for k in entry["black_keys"] if k["seen"]]
    # the local white key width: from the black key spacing, 12 semitones = 7 white keys
    centres = np.array([k["centre"] for k in black])
    widths = np.array([k["width"] for k in black])
    black_w = float(np.median(widths))

    def local_white(u: float) -> float:
        # the white key width near u: the octave period near u over 7, from the
        # nearest black keys of the same name
        near = [k for k in black if abs(k["centre"] - u) < 260]
        by_name: dict[str, list[float]] = {}
        for k in near:
            by_name.setdefault(k["name"], []).append(k["centre"])
        periods = []
        for cs in by_name.values():
            cs = sorted(cs)
            periods += [b - a for a, b in zip(cs, cs[1:]) if 120 < b - a < 260]
        return float(np.median(periods)) / 7 if periods else black_w / 0.58

    kept: list[dict] = []
    rejected: list[dict] = []
    # 1. both rows
    for l in lines:
        l["lean"] = (l["u_low"] - l["u_high"]) / max(1, v_low - v_high) * 30  # px per 30 rows
        l["found_both"] = bool(l["paired"])
    # 2. lean agrees with the neighbours (median lean within 120 px)
    for l in lines:
        near = [m["lean"] for m in lines if m is not l and abs(m["u_high"] - l["u_high"]) < 120 and m["found_both"]]
        l["lean_ok"] = bool(near) and abs(l["lean"] - float(np.median(near))) < 2.5
    # 3. no duplicates
    lines_sorted = sorted(lines, key=lambda l: l["u_high"])
    for l in lines_sorted:
        w = local_white(l["u_high"])
        l["white"] = w
        l["eye"] = any(abs(l["u_top"] - u) < 3.0 or abs(l["u_high"] - u) < 3.0 for u in by_eye)
        ok = l["found_both"] and l["lean_ok"] and not l["eye"]
        if ok and kept and l["u_high"] - kept[-1]["u_high"] < 0.55 * w:
            if l["strength"] > kept[-1]["strength"]:
                rejected.append(kept.pop())
            else:
                ok = False
        (kept if ok else rejected).append(l)
    return kept, rejected


def main() -> None:
    draft = json.loads((DATA / "truth-draft.json").read_text())
    rects = load_rects()
    truth: dict[str, dict] = {}
    (OUT / "truth").mkdir(parents=True, exist_ok=True)
    print("picture                  kept rejected top  W(left) W(mid) W(right)  lean(l) lean(m) lean(r)  taper")
    families: dict[str, dict[str, list[float]]] = {}
    for slug in slugs():
        entry = draft[slug]
        kept, rejected = keep_lines(entry, slug)
        v_high, v_low = entry["v_high"], entry["v_low"]
        us = np.array([l["u_top"] for l in kept])
        # perspective: white key width per third, from consecutive kept borders
        def third(lo: float, hi: float) -> tuple[float, float, float]:
            sel = [l for l in kept if lo <= l["u_top"] < hi]
            ds = [b["u_top"] - a["u_top"] for a, b in zip(sel, sel[1:])]
            ds = [d for d in ds if 0.6 * np.median(ds) < d < 1.4 * np.median(ds)] if ds else []
            w = float(np.median(ds)) if ds else float("nan")
            lean = float(np.median([l["lean"] for l in sel])) if sel else float("nan")
            # taper: how much wider a key is at the front row than at the high row
            fronts = [b["u_low"] - a["u_low"] for a, b in zip(sel, sel[1:])]
            highs = [b["u_high"] - a["u_high"] for a, b in zip(sel, sel[1:])]
            taper = float(np.median(np.array(fronts) / np.array(highs))) if fronts else float("nan")
            return w, lean, taper
        wl, ll, tl = third(0, 427)
        wm, lm, tm = third(427, 854)
        wr, lr, tr = third(854, 1281)
        print(f"{slug:24s} {len(kept):4d} {len(rejected):8d} {len(entry['top_edge']):3d}  {wl:6.2f} {wm:6.2f} {wr:6.2f}   {ll:6.2f} {lm:6.2f} {lr:6.2f}  {np.nanmedian([tl,tm,tr]):5.3f}")
        # families: each seen black key against the nearest kept border at the top edge
        offsets: dict[str, list[float]] = {}
        for k in entry["black_keys"]:
            if not k["seen"] or len(us) == 0:
                continue
            j = int(np.argmin(np.abs(us - k["centre"])))
            w = kept[j]["white"]
            if abs(us[j] - k["centre"]) > 0.5 * w:
                continue
            offsets.setdefault(k["name"], []).append((k["centre"] - us[j]) / w)
        families[slug] = offsets
        truth[slug] = {
            "rect": rects[slug].__dict__,
            "depth": entry["depth"], "bottom": entry["bottom"], "v_high": v_high, "v_low": v_low,
            "borders": [{"u_top": round(l["u_top"], 2), "u_high": round(l["u_high"], 2), "u_low": round(l["u_low"], 2),
                         "white": round(l["white"], 2)} for l in kept],
            "rejected": [{"u_high": round(l["u_high"], 2), "why": "eye" if l.get("eye") else ("one row" if not l["found_both"] else ("lean" if not l["lean_ok"] else "duplicate"))} for l in rejected],
            "top_edge": entry["top_edge"],
            "black_keys": entry["black_keys"],
        }
        # review sheet
        g = rectify(grey(load_rgb(slug)), rects[slug])
        strip = np.clip(g[: min(g.shape[0], entry["bottom"] + 6)], 0, 255).astype(np.uint8)
        im = Image.fromarray(strip).convert("RGB")
        d = ImageDraw.Draw(im)
        d.line((0, v_high, 1280, v_high), fill=(255, 0, 0)); d.line((0, v_low, 1280, v_low), fill=(255, 0, 0))
        for l in rejected:
            d.line((l["u_high"], v_high - 6, l["u_high"], v_high + 6), fill=(255, 0, 255))
        for l in kept:
            d.line((l["u_high"], v_high, l["u_low"], v_low), fill=(0, 255, 255))
            d.line((l["u_top"], 0, l["u_top"], entry["depth"]), fill=(255, 255, 0))
        for u in entry["top_edge"]:
            d.line((u, 0, u, 10), fill=(255, 255, 255))
        for k in entry["black_keys"]:
            col = (0, 255, 0) if k["seen"] else (255, 160, 0)
            d.rectangle((k["centre"] - k["width"] / 2, 1, k["centre"] + k["width"] / 2, entry["depth"] - 1), outline=col)
        zoom = 2.5
        pieces = []
        for x0 in (0, 440, 880):
            crop = im.crop((x0, 0, min(1280, x0 + 400), im.height)).resize((int(400 * zoom), int(im.height * zoom)), Image.Resampling.NEAREST)
            dd = ImageDraw.Draw(crop); dd.rectangle((0, 0, 170, 12), fill=(0, 0, 0)); dd.text((2, 1), f"{slug} u={x0}..{x0+400}", fill=(255, 255, 0))
            pieces.append(crop)
        sheet = Image.new("RGB", (pieces[0].width, sum(p.height for p in pieces)))
        y = 0
        for p in pieces:
            sheet.paste(p, (0, y)); y += p.height
        sheet.save(OUT / "truth" / f"{slug}.png")
    (DATA / "truth.json").write_text(json.dumps(truth, indent=1) + "\n")

    print("\nfamilies: offset of each black key from the nearest white key border at the top edge, in local white key widths")
    print("picture                    C#      D#      F#      G#      A#    (n)")
    rows = {}
    for slug, offsets in families.items():
        meds = [float(np.median(offsets[n])) if offsets.get(n) else float("nan") for n in ["C#", "D#", "F#", "G#", "A#"]]
        n = sum(len(v) for v in offsets.values())
        rows[slug] = meds
        print(f"{slug:24s} " + " ".join(f"{m:7.3f}" for m in meds) + f"   ({n})")
    (DATA / "families.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
