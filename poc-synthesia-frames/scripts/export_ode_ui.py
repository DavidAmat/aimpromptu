"""Export the three Ode to Vivian frames and the momentum rule, for the page."""
from __future__ import annotations

import json

import numpy as np
from PIL import Image

import common
import ode_momentum as om

OUT = common.OUT / "ui-ode"
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def pack(runs, verd, w: float) -> dict:
    return dict(runs=[dict(midi=int(r["midi"]), x0=round(r["x0"], 1),
                           x1=round(r["x1"], 1), yTop=int(r["y_top"]),
                           yBottom=int(r["y_bottom"]),
                           widthKeys=round(r["width_keys"], 2),
                           heightRows=int(r["y_bottom"] - r["y_top"] + 1),
                           clipped=bool(r["clipped"]), entering=bool(r["entering"]),
                           tipTrusted=bool(r["tip_trusted"]), verdict=v)
                      for r, v in zip(runs, verd)],
                onsets=[], sustains=[])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    r = om.main()
    cal, aligned, w = r["cal"], r["aligned"], r["white"]
    h, wide = aligned["ode1"].shape[:2]

    frames = []
    for i, s in enumerate(om.SLUGS):
        Image.fromarray(aligned[s].astype("uint8")).save(OUT / f"{s}.jpg", quality=92)
        frames.append(dict(
            seconds=float(i), index=i, picture=f"{s}.jpg", label=s,
            after=pack(r["runs"][s], r["verd"][s + "_alone"], w),
            before=pack(r["runs3"][s], r["verd"][s], w),
        ))

    payload = dict(
        mode="ode", video="ode1 / ode2 / ode3", source="Ode to Vivian",
        width=wide, height=h, sampleMs=None,
        upperLine=cal.upper_line, rollTop=0.0, guardBand=1.75 * w,
        whiteWidth=round(w, 2), scrollPxPerSecond=None,
        offsetLinePx=round(r["d"], 2), bpm=None,
        travels=r["travels"]["alone"], tolerance=om.TOL,
        thresholds=dict(matchTolerance=om.TOL, staticTolerance=om.STATIC_TOL,
                        voteFloor=om.VOTE_FLOOR),
        keys=[dict(midi=k["midi"], kind=k["kind"], name=name(k["midi"]),
                   left=round(k["left"], 1), right=round(k["right"], 1),
                   mid=round(k["mid"], 1)) for k in cal.keys()],
        lanes=[dict(midi=l["midi"], x0=round(l["x0"], 1), x1=round(l["x1"], 1))
               for l in cal.lanes(0.25)],
        frames=frames,
    )
    (OUT / "detection.json").write_text(json.dumps(payload, separators=(",", ":")))
    print()
    for f in frames:
        v = [x["verdict"] for x in f["after"]["runs"]]
        print(f"{f['label']}: {len(v)} runs — {v.count('fell')} fell, "
              f"{v.count('static')} static, {v.count('unknown')} unknown")
    print(f"{(OUT / 'detection.json').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
