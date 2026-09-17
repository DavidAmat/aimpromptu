"""Export one example screenshot into the inspection page's format.

A screenshot has no motion, so it has no measured scroll speed, no roll top and
no real background plate — only the single screenshot stand-in. The payload says
so with `mode`, and the page hides what does not apply.
"""
from __future__ import annotations

import json
import sys

from PIL import Image

import common
import detectors

OUT = common.OUT / "ui-example"
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def pack(res) -> dict:
    return dict(
        runs=[dict(midi=int(r["midi"]), x0=round(r["x0"], 1), x1=round(r["x1"], 1),
                   yTop=int(r["y_top"]), yBottom=int(r["y_bottom"]),
                   widthKeys=round(r["width_keys"], 2),
                   heightRows=int(r["y_bottom"] - r["y_top"] + 1),
                   clipped=bool(r["clipped"]), entering=bool(r["entering"]),
                   tipTrusted=bool(r["tip_trusted"]))
              for r in sorted(res["runs"], key=lambda r: (r["midi"], r["y_top"]))],
        onsets=sorted(res["onsets"]), sustains=sorted(res["sustains"]),
    )


def main(slug: str = "more-examples-3"):
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    cal = common.load_calibrations()[slug]
    img = common.load(slug)
    h, w = img.shape[:2]
    Image.fromarray(img.astype("uint8")).save(OUT / f"{slug}.jpg", quality=92)

    d = 2.0 * cal.white_width
    plate = detectors.detect(img, cal, d, mask_name="plate")
    edges = detectors.detect(img, cal, d, mask_name="edges")

    payload = dict(
        mode="screenshot", video=f"{slug}.png",
        source="context/implementations/04-synthesia-to-notes/examples/",
        width=w, height=h, sampleMs=None,
        upperLine=cal.upper_line, rollTop=0.0,
        guardBand=detectors.GUARD_BAND * cal.white_width,
        whiteWidth=round(cal.white_width, 2),
        scrollPxPerSecond=None, offsetLinePx=round(d, 2), bpm=None,
        thresholds=dict(tauForeground=detectors.TAU_FOREGROUND,
                        tauCoverage=detectors.TAU_COVERAGE,
                        gapCloseRows=detectors.GAP_CLOSE,
                        splitProminence=detectors.SPLIT_PROMINENCE,
                        minHeightRows=detectors.MIN_HEIGHT,
                        laneMargin=detectors.LANE_MARGIN,
                        tauEdge=detectors.TAU_EDGE,
                        minWidth=detectors.MIN_WIDTH, maxWidth=detectors.MAX_WIDTH),
        keys=[dict(midi=k["midi"], kind=k["kind"], name=name(k["midi"]),
                   left=round(k["left"], 1), right=round(k["right"], 1),
                   mid=round(k["mid"], 1)) for k in cal.keys()],
        lanes=[dict(midi=l["midi"], x0=round(l["x0"], 1), x1=round(l["x1"], 1))
               for l in cal.lanes(detectors.LANE_MARGIN)],
        frames=[dict(seconds=0.0, index=0, picture=f"{slug}.jpg",
                     after=pack(plate), before=pack(edges))],
        variantLabels=["gradient", "plate stand-in"],
    )
    (OUT / "detection.json").write_text(json.dumps(payload, separators=(",", ":")))
    print(f"{slug}: {w}x{h}, upper line {cal.upper_line:.0f}, "
          f"white key {cal.white_width:.2f} px")
    print(f"  plate stand-in: {len(plate['runs'])} runs, "
          f"{len(plate['onsets'])} onsets, {len(plate['sustains'])} sustains")
    print(f"  gradient:       {len(edges['runs'])} runs, "
          f"{len(edges['onsets'])} onsets, {len(edges['sustains'])} sustains")
    # Where the title text is, so the question can be answered with a number.
    txt = [r for r in plate["runs"] if r["y_bottom"] < cal.upper_line - 1.5 * cal.white_width]
    print(f"  runs above the bottom 1.5 white keys of the roll: {len(txt)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "more-examples-3")
