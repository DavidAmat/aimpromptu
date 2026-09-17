"""Score a detector against the hand read ground truth.

V-20: a rule ships with its measured score or it does not ship. This is where
the number comes from. Keys listed in `skip` are left out on both sides.
"""
from __future__ import annotations

import json
import sys

import common
import detectors

GT = json.loads((common.DATA / "ground_truth.json").read_text())


def score_one(slug: str, mask_name: str) -> dict:
    truth = GT["examples"][slug]
    cal = common.load_calibrations()[slug]
    img = common.load(slug)
    d = GT["d_in_white_keys"] * cal.white_width
    if mask_name == "single-row":
        res = detectors.detect_single_row(img, cal, d)
    else:
        res = detectors.detect(img, cal, d, mask_name=mask_name)
    skip = set(truth["skip"])
    got_on = set(res["onsets"]) - skip
    got_sus = set(res["sustains"]) - skip
    want_on = set(truth["onsets"]) - skip
    want_sus = set(truth["sustains"]) - skip
    return dict(
        example=slug, detector=mask_name,
        on_found=len(want_on & got_on), on_invented=len(got_on - want_on),
        on_missed=len(want_on - got_on),
        sus_found=len(want_sus & got_sus), sus_invented=len(got_sus - want_sus),
        sus_missed=len(want_sus - got_sus),
        invented_keys=sorted(got_on - want_on), missed_keys=sorted(want_on - got_on),
        sus_invented_keys=sorted(got_sus - want_sus),
    )


def board(names=("absolute", "plate", "edges", "colour", "single-row")) -> None:
    print(f"{'detector':12s} {'example':20s} "
          f"{'on ok':>6s} {'on inv':>7s} {'on miss':>8s} "
          f"{'sus ok':>7s} {'sus inv':>8s} {'sus miss':>9s}")
    totals = {}
    for name in names:
        t = [0, 0, 0, 0, 0, 0]
        for slug in GT["examples"]:
            r = score_one(slug, name)
            print(f"{name:12s} {slug:20s} "
                  f"{r['on_found']:6d} {r['on_invented']:7d} {r['on_missed']:8d} "
                  f"{r['sus_found']:7d} {r['sus_invented']:8d} {r['sus_missed']:9d}"
                  + (f"   invented {r['invented_keys']}" if r['invented_keys'] else "")
                  + (f"   missed {r['missed_keys']}" if r['missed_keys'] else ""))
            for i, k in enumerate(("on_found", "on_invented", "on_missed",
                                   "sus_found", "sus_invented", "sus_missed")):
                t[i] += r[k]
        totals[name] = t
        print(f"{name:12s} {'TOTAL':20s} " + " ".join(
            f"{v:6d} " for v in t))
        print()
    return totals


if __name__ == "__main__":
    board(sys.argv[1:] or None)
