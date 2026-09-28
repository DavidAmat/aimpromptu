"""Task 1.3.5: the whole song, MuScriptor against the stored ByteDance ``events.json``.

Counts, one-to-one matching of onsets (same pitch, within 50 ms), the signed onset
differences of the matched pairs, the note lengths, the notes cut at a chunk border,
and pictures of both piano roll visualizations over the same windows.

    cd aitu-backend
    uv run python ../pocs/poc-muscriptor/scripts/10_compare_bytedance.py \
        [--config large-float32-b1-prelude]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    SUPERESTRELLA,
    full_uuid,
    result_name,
    run_dir,
    CHUNK_SECONDS,
    OUT,
    load_bytedance,
    read_json,
    write_json,
)  # noqa: E402

TOLERANCE = 0.050
WINDOWS = [(0.0, 20.0), (60.0, 75.0), (120.0, 135.0)]


def match(a: list[dict], b: list[dict], tol: float = TOLERANCE) -> list[tuple[int, int]]:
    """Greedy one-to-one matching by onset distance, same pitch only.

    Every candidate pair within ``tol`` is sorted by distance and taken when both
    notes are still free, so a chord of repeated pitches cannot match one note twice.
    """
    by_pitch: dict[int, list[int]] = {}
    for j, n in enumerate(b):
        by_pitch.setdefault(n["pitch"], []).append(j)
    starts_b = np.array([n["start"] for n in b])
    cands = []
    for i, n in enumerate(a):
        for j in by_pitch.get(n["pitch"], []):
            d = abs(starts_b[j] - n["start"])
            if d <= tol:
                cands.append((d, i, j))
    cands.sort()
    used_a, used_b, pairs = set(), set(), []
    for _, i, j in cands:
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            pairs.append((i, j))
    return pairs


def at_border(t: float, eps: float = 0.0051) -> bool:
    k = round(t / CHUNK_SECONDS)
    return k > 0 and abs(t - k * CHUNK_SECONDS) <= eps


def piano_roll(
    ax, notes: list[dict], t0: float, t1: float, color: str, title: str, ylim: tuple[int, int]
) -> None:
    from matplotlib.patches import Rectangle  # noqa: PLC0415

    for n in notes:
        if n["end"] < t0 or n["start"] > t1:
            continue
        ax.add_patch(
            Rectangle(
                (n["start"], n["pitch"] - 0.4),
                n["end"] - n["start"],
                0.8,
                facecolor=color,
                edgecolor="black",
                linewidth=0.3,
            )
        )
    ax.set_xlim(t0, t1)
    ax.set_ylim(*ylim)
    for k in np.arange(np.ceil(t0 / CHUNK_SECONDS), t1 / CHUNK_SECONDS + 1):
        ax.axvline(k * CHUNK_SECONDS, color="grey", linewidth=0.6, linestyle=":")
    ax.set_title(title, fontsize=9)
    ax.set_ylabel("MIDI")


def main() -> None:
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="large-float32-b1-prelude")
    ap.add_argument("--uuid", default=SUPERESTRELLA, help="piece uuid or its first characters")
    args = ap.parse_args()
    uuid = full_uuid(args.uuid)

    folder = run_dir(args.config, uuid)
    mus = read_json(folder / "notes.json")
    byt = load_bytedance(uuid)
    pairs = match(mus, byt)
    diffs_ms = np.array([1000 * (mus[i]["start"] - byt[j]["start"]) for i, j in pairs])
    len_mus = np.array([n["end"] - n["start"] for n in mus]) * 1000
    len_byt = np.array([n["end"] - n["start"] for n in byt]) * 1000
    ratio = np.array(
        [
            (mus[i]["end"] - mus[i]["start"]) / max(1e-6, byt[j]["end"] - byt[j]["start"])
            for i, j in pairs
        ]
    )

    def q(x: np.ndarray) -> dict:
        return {f"p{p}": round(float(np.percentile(x, p)), 1) for p in (5, 25, 50, 75, 95)}

    matched_mus = {i for i, _ in pairs}
    matched_byt = {j for _, j in pairs}
    summary = {
        "config": args.config,
        "uuid": uuid,
        "muscriptor_notes": len(mus),
        "bytedance_notes": len(byt),
        "matched_within_50ms": len(pairs),
        "share_of_muscriptor_matched": round(len(pairs) / len(mus), 3),
        "share_of_bytedance_matched": round(len(pairs) / len(byt), 3),
        "onset_difference_ms_mus_minus_byt": {
            **q(diffs_ms),
            "mean": round(float(diffs_ms.mean()), 1),
        },
        "length_ms_muscriptor": q(len_mus),
        "length_ms_bytedance": q(len_byt),
        "length_ratio_matched_mus_over_byt": {
            f"p{p}": round(float(np.percentile(ratio, p)), 2) for p in (5, 25, 50, 75, 95)
        },
        "muscriptor_only_examples": [mus[i] for i in range(len(mus)) if i not in matched_mus][:30],
        "bytedance_only_examples": [byt[j] for j in range(len(byt)) if j not in matched_byt][:30],
        "muscriptor_ends_on_chunk_border": sum(at_border(n["end"]) for n in mus),
        "muscriptor_starts_on_chunk_border": sum(at_border(n["start"]) for n in mus),
        "muscriptor_shortest_ms": q(np.sort(len_mus)[:50]),
        "muscriptor_notes_under_30ms": int((len_mus < 30).sum()),
        "bytedance_notes_under_30ms": int((len_byt < 30).sum()),
        "muscriptor_time_step_ms": sorted({round((1000 * n["start"]) % 10, 3) for n in mus})[:10],
    }
    write_json(OUT / "compare" / f"{result_name(args.config, uuid)}.json", summary)
    print({k: v for k, v in summary.items() if not k.endswith("examples")})

    fig, axes = plt.subplots(len(WINDOWS), 2, figsize=(18, 4.2 * len(WINDOWS)), squeeze=False)
    for row, (t0, t1) in enumerate(WINDOWS):
        seen = [n["pitch"] for n in byt + mus if t0 <= n["start"] <= t1]
        ylim = (min(seen, default=40) - 2, max(seen, default=90) + 2)
        piano_roll(
            axes[row][0], byt, t0, t1, "#6c8ebf", f"ByteDance (stored) {t0:.0f}-{t1:.0f} s", ylim
        )
        piano_roll(
            axes[row][1],
            mus,
            t0,
            t1,
            "#d79b00",
            f"MuScriptor {args.config} {t0:.0f}-{t1:.0f} s",
            ylim,
        )
    for ax in axes[-1]:
        ax.set_xlabel("seconds (dotted lines: MuScriptor 5 s chunk borders)")
    fig.tight_layout()
    path = OUT / "compare" / f"{result_name(args.config, uuid)}.pianoroll.png"
    fig.savefig(path, dpi=110)
    print("wrote", path)


if __name__ == "__main__":
    main()
