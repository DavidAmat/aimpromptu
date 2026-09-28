"""Task 1.3.3: is there a constant lag in MuScriptor's onset times, and how large?

Three independent estimates, so that no single method decides ``lagCorrectionMs``:

1. **MuScriptor's own** ``onset_delay``: the mean phase of the onsets against the
   beat_this beat grid (saved by ``04_full_song.py``). It needs a steady tempo.
2. **Against the audio**: a spectral-flux onset envelope of ``normalized.wav``
   (10 ms hop). For each candidate lag the onsets are moved back by it and the
   envelope is read at the moved onsets; the lag with the highest mean is where
   the onsets sit best on the energy rises. The envelope itself has a small bias
   (its peak lands a little after the physical onset), so the same measurement is
   made for ByteDance and the **difference** between the two engines is the number
   that matters. ByteDance's regressed onsets are the anchor because the app has
   used them for months and their timing has been checked by ear.
3. **Directly**: the median signed onset difference of the matched pairs from
   ``10_compare_bytedance.py``.

    cd aitu-backend
    uv run python ../pocs/poc-muscriptor/scripts/11_lag.py [--config large-float32-b1-prelude]
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
    OUT,
    SAMPLE_RATE,
    load_bytedance,
    read_json,
    wav_path,
    write_json,
)  # noqa: E402

#: 2 ms. MuScriptor onsets sit on a 10 ms grid, so a 10 ms envelope can only answer in
#: multiples of 10 ms (the mean of a piecewise-linear curve peaks on a knot).
HOP = 32
LAGS_MS = np.arange(-80, 81, 1)


def envelope(uuid: str) -> np.ndarray:
    import librosa  # noqa: PLC0415

    y, _ = librosa.load(str(wav_path(uuid)), sr=SAMPLE_RATE, mono=True)
    env = librosa.onset.onset_strength(
        y=y, sr=SAMPLE_RATE, hop_length=HOP, n_fft=512, center=True, lag=5
    )
    return env / (env.std() + 1e-9)


def lag_curve(env: np.ndarray, onsets: np.ndarray) -> np.ndarray:
    frames = np.arange(len(env)) * HOP / SAMPLE_RATE
    return np.array([np.interp(onsets - lag / 1000.0, frames, env).mean() for lag in LAGS_MS])


def detected_differences(env: np.ndarray, onsets: np.ndarray) -> np.ndarray:
    import librosa  # noqa: PLC0415

    peaks = librosa.onset.onset_detect(
        onset_envelope=env, sr=SAMPLE_RATE, hop_length=HOP, units="time", backtrack=False
    )
    idx = np.clip(np.searchsorted(peaks, onsets), 1, len(peaks) - 1)
    nearest = np.where(
        np.abs(peaks[idx - 1] - onsets) < np.abs(peaks[idx] - onsets), peaks[idx - 1], peaks[idx]
    )
    d = (onsets - nearest) * 1000
    return d[np.abs(d) <= 50]


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
    mus = np.unique(np.round([n["start"] for n in read_json(folder / "notes.json")], 3))
    byt = np.unique(np.round([n["start"] for n in load_bytedance(uuid)], 3))
    env = envelope(uuid)

    curves = {"muscriptor": lag_curve(env, mus), "bytedance": lag_curve(env, byt)}
    best = {k: int(LAGS_MS[int(np.argmax(v))]) for k, v in curves.items()}
    detected = {
        "muscriptor": detected_differences(env, mus),
        "bytedance": detected_differences(env, byt),
    }

    beats = read_json(folder / "beats.json") if (folder / "beats.json").exists() else {}
    compare = OUT / "compare" / f"{result_name(args.config, uuid)}.json"
    matched = read_json(compare)["onset_difference_ms_mus_minus_byt"] if compare.exists() else {}

    summary = {
        "config": args.config,
        "uuid": uuid,
        "1_muscriptor_onset_delay_ms": (
            None if beats.get("onset_delay") is None else round(1000 * beats["onset_delay"], 1)
        ),
        "1_beat_subdivision": beats.get("beat_subdivision"),
        "1_bpm": beats.get("bpm"),
        "2_envelope_best_lag_ms": best,
        "2_muscriptor_minus_bytedance_ms": best["muscriptor"] - best["bytedance"],
        "2_detected_onset_median_ms": {
            k: round(float(np.median(v)), 1) for k, v in detected.items()
        },
        "2_detected_onset_pairs": {k: int(len(v)) for k, v in detected.items()},
        "3_matched_pairs_median_ms_mus_minus_byt": matched.get("p50"),
    }
    write_json(OUT / "lag" / f"{result_name(args.config, uuid)}.json", summary)
    print(summary)

    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    for k, v in curves.items():
        ax[0].plot(LAGS_MS, v, label=f"{k} (peak {best[k]} ms)")
    ax[0].set_xlabel("lag removed from the onsets (ms)")
    ax[0].set_ylabel("mean onset envelope at the onsets")
    ax[0].legend()
    bins = np.arange(-50, 51, 5)
    for k, v in detected.items():
        ax[1].hist(v, bins=bins, alpha=0.5, label=f"{k} median {np.median(v):.1f} ms")
    ax[1].set_xlabel("onset minus nearest detected audio onset (ms)")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(OUT / "lag" / f"{result_name(args.config, uuid)}.png", dpi=110)


if __name__ == "__main__":
    main()
