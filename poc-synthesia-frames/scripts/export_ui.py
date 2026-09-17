"""Export what the detector sees on a few frames of the test video, for the UI.

One JSON with the piano overlay, the vertical lanes and the runs, plus the
frames themselves as pictures. The runs are exported twice: once against the
background plate as V-15 first described it, the median of 50 frames, and once
against the plate this phase measured, the 20th percentile of 100. The first is
what put false rectangles across a held note; the page can show the difference.
"""
from __future__ import annotations

import json
import shutil

import numpy as np

import common
import detectors
import testvid

SECONDS = [11.5, 15.0, 35.0, 63.0, 78.0]
OUT = common.OUT / "ui"
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def pack(res: dict, cal) -> dict:
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.jpg"):
        old.unlink()
    cal = testvid.calibration()
    good = testvid.plate(n=100, percentile=20.0)
    paths = testvid.frames()
    pick = np.linspace(0, len(paths) - 1, 50).round().astype(int)
    naive = np.median(np.stack([testvid.load(int(i)) for i in pick]), axis=0)

    speed = json.loads((common.DATA / "video" / "scroll_test.json").read_text())
    d = speed["median_px_per_frame"]

    frames = []
    for sec in SECONDS:
        i = testvid.at_second(sec)
        picture = f"f{i:06d}.jpg"
        shutil.copy(paths[i], OUT / picture)
        img = testvid.load(i)
        frames.append(dict(
            seconds=sec, index=i, picture=picture,
            after=pack(detectors.detect(img, cal, d, plate_img=good), cal),
            before=pack(detectors.detect(img, cal, d, plate_img=naive), cal),
        ))

    keys = [dict(midi=k["midi"], kind=k["kind"], name=name(k["midi"]),
                 left=round(k["left"], 1), right=round(k["right"], 1),
                 mid=round(k["mid"], 1)) for k in cal.keys()]
    lanes = [dict(midi=l["midi"], x0=round(l["x0"], 1), x1=round(l["x1"], 1))
             for l in cal.lanes(detectors.LANE_MARGIN)]

    payload = dict(
        video="test.mp4", source="https://www.youtube.com/watch?v=pgLt4WmPMYQ",
        width=1280, height=720, sampleMs=testvid.SAMPLE_MS,
        upperLine=cal.upper_line, rollTop=cal.roll_top, guardBand=cal.guard_band,
        whiteWidth=round(cal.white_width, 2),
        scrollPxPerSecond=round(speed["px_per_second"], 1),
        offsetLinePx=round(d, 2), bpm=128,
        thresholds=dict(tauForeground=detectors.TAU_FOREGROUND,
                        tauCoverage=detectors.TAU_COVERAGE,
                        gapCloseRows=detectors.GAP_CLOSE,
                        splitProminence=detectors.SPLIT_PROMINENCE,
                        minHeightRows=detectors.MIN_HEIGHT,
                        laneMargin=detectors.LANE_MARGIN,
                        tauEdge=detectors.TAU_EDGE,
                        minWidth=detectors.MIN_WIDTH, maxWidth=detectors.MAX_WIDTH),
        keys=keys, lanes=lanes, frames=frames,
    )
    (OUT / "detection.json").write_text(json.dumps(payload, separators=(",", ":")))
    for f in frames:
        a, b = f["after"], f["before"]
        print(f"t={f['seconds']:5.1f}s  frame {f['index']:4d}  "
              f"runs {len(a['runs']):3d} (median-of-50 plate: {len(b['runs']):3d})  "
              f"onsets {len(a['onsets']):2d}  sustains {len(a['sustains']):2d}")
    print(f"\n{(OUT / 'detection.json').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
