"""Run the whole PoC: extract -> analyse -> plot -> tabulate.

    python3 scripts/run_poc.py

Writes every figure and table into ``out/``. Reads only the stored artifacts in
``data/``; touches nothing in the app.
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import analysis as A
import common as C

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

HAND = "R"
CHORD_WINDOW_MS = 20.0          # see common.collapse_attacks
SPLIT_SECONDS = 217.0           # 3:37 on the segment clock, per David
BIN_MS = 20.0
KDE_BANDWIDTH_MS = 12.0
PLOT_MAX_MS = 1200.0
APP_GRANULARITY = "semicorchea"  # what the app currently quantises the score at
SEGMENTS = [("A", "0:00 – 3:37", 0.0, SPLIT_SECONDS),
            ("B", "3:37 – end", SPLIT_SECONDS, np.inf)]

# dataviz reference palette, light mode; two series -> slots 1 and 2.
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2de"
SERIES = {"A": "#2a78d6", "B": "#eb6834"}

OUT = C.OUT
OUT.mkdir(exist_ok=True)
sns.set_theme(style="ticks", rc={
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": INK_2, "ytick.color": INK_2, "grid.color": GRID,
    "axes.grid": True, "grid.linewidth": 0.6, "axes.linewidth": 0.8,
    "font.size": 10, "axes.titlesize": 12, "legend.frameon": False,
})


def tidy(ax, *, xgrid: bool = False) -> None:
    sns.despine(ax=ax)
    ax.set_axisbelow(True)
    ax.grid(axis="x", visible=xgrid)


# --------------------------------------------------------------------------
# 1. Extract
# --------------------------------------------------------------------------

events, duration, title = C.load_events()
right = C.load_matrix("two-hands_semicorchea_right.npz")
left = C.load_matrix("two-hands_semicorchea_left.npz")
tempo_bpm = C.infer_tempo_bpm(C.load_matrix("raw.npz").shape[1], duration)
labels, label_report = C.label_hands(events, right, left, tempo_bpm)

print(f"{title}  ({duration:.2f} s, grids written at {tempo_bpm:.2f} BPM)")
print("  hand labelling:", label_report.describe())

onsets = np.array(sorted(e["start"] for e, l in zip(events, labels) if l == HAND))
attacks = C.collapse_attacks(onsets, CHORD_WINDOW_MS)
print(f"  {len(onsets)} right-hand onsets -> {len(attacks)} attacks "
      f"at a {CHORD_WINDOW_MS:.0f} ms chord window")

# How much does the chord window matter? If the answer is "almost nothing", the
# 20 ms choice is not a knob anyone has to defend.
sensitivity_rows = []
for window in (0, 5, 10, 15, 20, 25, 30, 40, 50):
    grouped = C.collapse_attacks(onsets, window)
    gaps = C.inter_onset_intervals_ms(grouped)
    near_beat = gaps[(gaps > 250) & (gaps < 450)]
    sensitivity_rows.append({
        "chord_window_ms": window, "attacks": len(grouped),
        "intervals": len(gaps),
        "intervals_under_50ms": int((gaps < 50).sum()),
        "dominant_peak_ms": round(float(np.median(near_beat)), 1),
    })
sensitivity = pd.DataFrame(sensitivity_rows)
sensitivity.to_csv(OUT / "table_chord_window_sensitivity.csv", index=False)

# --------------------------------------------------------------------------
# 2. Analyse each segment
# --------------------------------------------------------------------------

per_segment: dict[str, dict] = {}
for key, span, lo, hi in SEGMENTS:
    inside = attacks[(attacks >= lo) & (attacks < hi)]
    # Diffing *within* the segment is what drops the one interval that straddles
    # the boundary -- it belongs to neither tempo.
    intervals = C.inter_onset_intervals_ms(inside)
    grid = np.arange(0.0, PLOT_MAX_MS + 1.0, 1.0)
    density = A.gaussian_kde_grid(intervals, grid, KDE_BANDWIDTH_MS)
    peaks = A.find_peaks(intervals, grid, density)
    unit, unit_grid, unit_score = A.fit_tatum(intervals)
    beat, beat_grid, beat_score = A.fit_beat(peaks)
    dominant = max(peaks, key=lambda p: p.mass)
    swing = A.detect_swing(peaks, beat)

    # Every local maximum of the beat objective, best first: the honest output
    # is a shortlist for the user, not a single number.
    interior = np.arange(1, len(beat_score) - 1)
    local = interior[(beat_score[1:-1] > beat_score[:-2])
                     & (beat_score[1:-1] >= beat_score[2:])]
    candidates = sorted(((float(beat_score[i]), float(beat_grid[i])) for i in local),
                        reverse=True)[:4]

    per_segment[key] = dict(span=span, lo=lo, hi=hi, attacks=inside,
                            intervals=intervals, grid=grid, density=density,
                            peaks=peaks, dominant=dominant, unit=unit,
                            unit_grid=unit_grid, unit_score=unit_score,
                            beat=beat, beat_grid=beat_grid, beat_score=beat_score,
                            swing=swing, candidates=candidates)


def lattice_error(intervals: np.ndarray, beat_ms: float) -> np.ndarray:
    """Relative distance from each interval to the nearest printable figure."""
    errors = []
    for value in intervals:
        ratio = value / beat_ms
        if ratio > 4.5:
            continue
        target, _, _ = A.nearest_ratio(ratio)
        errors.append(abs(ratio / target - 1.0))
    return np.asarray(errors)


def binary_phase(intervals: np.ndarray, step_ms: float) -> np.ndarray:
    """Where each interval sits between two columns of a fixed binary grid.

    0 means "lands exactly on a column"; 0.5 means "exactly between two". This
    is the quantity the app's rounding throws away, and its shape says whether
    the grid is the right grid.
    """
    ratio = intervals / step_ms
    return np.abs(ratio - np.round(ratio)) * 2.0


# --------------------------------------------------------------------------
# 3. Tables
# --------------------------------------------------------------------------

peak_rows = []
for key, data in per_segment.items():
    beat = data["beat"]
    for peak in data["peaks"]:
        ratio = peak.median_ms / beat
        target, figure, error = A.nearest_ratio(ratio)
        peak_rows.append({
            "segment": key,
            "peak_ms": round(peak.centre_ms, 1),
            "median_ms": round(peak.median_ms, 1),
            "count": peak.mass,
            "share_pct": round(peak.share * 100, 1),
            "basin_ms": f"{peak.lo_ms:.0f}-{peak.hi_ms:.0f}",
            "x_dominant": round(peak.median_ms / data["dominant"].median_ms, 3),
            "x_beat": round(ratio, 3),
            "nearest_printable": round(target, 4),
            "figure": figure,
            "error_pct": round(error, 1),
        })
peaks_table = pd.DataFrame(peak_rows)
peaks_table.to_csv(OUT / "table_peaks.csv", index=False)

summary_rows = []
for key, data in per_segment.items():
    intervals, dominant = data["intervals"], data["dominant"]
    errors = lattice_error(intervals, data["beat"])
    app_step = C.seconds_per_column(APP_GRANULARITY, tempo_bpm) * 1000.0
    phase = binary_phase(intervals[intervals < 4.5 * data["beat"]], app_step)
    swing = data["swing"]
    summary_rows.append({
        "segment": key, "span": data["span"],
        "attacks": len(data["attacks"]), "intervals": len(intervals),
        "median_ioi_ms": round(float(np.median(intervals)), 1),
        "dominant_peak_ms": round(dominant.median_ms, 1),
        "dominant_share_pct": round(dominant.share * 100, 1),
        "peaks": len(data["peaks"]),
        "mass_in_peaks_pct": round(
            sum(p.mass for p in data["peaks"]) / max(1, len(intervals)) * 100, 1),
        "fitted_tatum_ms": round(data["unit"], 1),
        "fitted_beat_ms": round(data["beat"], 1),
        "fitted_bpm": round(60000.0 / data["beat"], 1),
        "beat_fit_score": round(float(data["beat_score"].max()), 3),
        "median_lattice_error_pct": round(float(np.median(errors)) * 100, 1),
        "within_10pct_of_a_figure": round(float((errors <= 0.10).mean()) * 100, 1),
        "swing_ratio": None if swing is None else round(swing[2], 2),
        # Share of gaps sitting in the outer half of a column gap, i.e. where
        # rounding to the app's grid is a coin toss.
        "binary_grid_coin_toss_pct": round(float((phase > 0.5).mean()) * 100, 1),
    })
summary_table = pd.DataFrame(summary_rows)
summary_table.to_csv(OUT / "table_summary.csv", index=False)

candidate_rows = []
for key, data in per_segment.items():
    best = data["candidates"][0][0] if data["candidates"] else 1.0
    for rank, (score, beat) in enumerate(data["candidates"], start=1):
        candidate_rows.append({
            "segment": key, "rank": rank,
            "beat_ms": round(beat, 1), "bpm": round(60000.0 / beat, 1),
            "score": round(score, 3),
            "score_vs_best_pct": round(score / best * 100, 1),
            "subdivisions_of_tatum": round(beat / data["unit"], 2),
        })
candidates_table = pd.DataFrame(candidate_rows)
candidates_table.to_csv(OUT / "table_beat_candidates.csv", index=False)

histogram_rows = []
bins = np.arange(0.0, PLOT_MAX_MS + BIN_MS, BIN_MS)
for key, data in per_segment.items():
    counts, _ = np.histogram(data["intervals"], bins=bins)
    for edge, count in zip(bins[:-1], counts):
        histogram_rows.append({"segment": key, "bin_lo_ms": edge,
                               "bin_hi_ms": edge + BIN_MS, "count": int(count)})
pd.DataFrame(histogram_rows).to_csv(OUT / "table_histogram_20ms.csv", index=False)

dump = []
for key, data in per_segment.items():
    for start, gap in zip(data["attacks"][:-1], data["intervals"]):
        dump.append({"segment": key, "attack_seconds": round(float(start), 4),
                     "ioi_ms": round(float(gap), 2)})
pd.DataFrame(dump).to_csv(OUT / "right_hand_intervals.csv", index=False)

# --------------------------------------------------------------------------
# 4. Figures
# --------------------------------------------------------------------------

# Fig 1 -- the histogram David asked for, one panel per segment.
fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.4), sharex=True)
for ax, (key, data) in zip(axes, per_segment.items()):
    colour = SERIES[key]
    ax.hist(data["intervals"], bins=bins, color=colour, alpha=0.5,
            edgecolor=SURFACE, linewidth=1.2)
    ax.plot(data["grid"], data["density"] * len(data["intervals"]) * BIN_MS,
            color=colour, linewidth=2.0)
    top = ax.get_ylim()[1]
    previous = -1e9
    row = 0
    for peak in data["peaks"]:
        ax.axvline(peak.centre_ms, color=INK_2, linewidth=0.8,
                   linestyle=(0, (4, 3)), alpha=0.5)
        # Stagger labels that would collide -- peaks can sit 50 ms apart.
        row = (row + 1) % 2 if peak.centre_ms - previous < 110 else 0
        previous = peak.centre_ms
        ax.annotate(f"{peak.median_ms:.0f} ms\n{peak.mass}  ({peak.share*100:.0f} %)",
                    xy=(peak.centre_ms, top * (0.99 - 0.155 * row)), ha="center",
                    va="top", fontsize=8.5, color=INK_2)
    ax.set_ylim(0, top * 1.34)
    ax.set_title(f"Segment {key} — {data['span']}   ·   {len(data['intervals'])} "
                 f"intervals   ·   dominant peak {data['dominant'].median_ms:.0f} ms",
                 loc="left", color=INK)
    ax.set_ylabel("intervals")
    tidy(ax)
axes[-1].set_xlabel("gap between consecutive right-hand attacks (ms)")
axes[-1].set_xlim(0, PLOT_MAX_MS)
fig.suptitle("Right-hand inter-onset intervals — Mr Blue Sky", x=0.006,
             ha="left", fontsize=14, color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.965))
fig.savefig(OUT / "fig1_histograms.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# Fig 2 -- the same densities on a log2 axis. Rhythm is multiplicative, so the
# ladder that is unevenly spaced in ms is evenly spaced here, and a pure tempo
# change is a rigid shift of the whole comb rather than a change of shape.
fig, ax = plt.subplots(figsize=(11.5, 4.8))
for key, data in per_segment.items():
    values = data["intervals"]
    values = values[values > 0]
    log_grid = np.linspace(np.log2(30.0), np.log2(2000.0), 900)
    log_density = A.gaussian_kde_grid(np.log2(values), log_grid, 0.055)
    ax.plot(log_grid, log_density / log_density.max(), color=SERIES[key],
            linewidth=2.0, label=f"Segment {key} · {data['span']}")
    ax.axvline(np.log2(data["dominant"].median_ms), color=SERIES[key],
               linewidth=1.0, linestyle=(0, (4, 3)), alpha=0.75)
ticks = [50, 70, 100, 140, 200, 280, 400, 560, 800, 1100, 1600]
ax.set_xticks(np.log2(ticks))
ax.set_xticklabels(ticks)
ax.set_xlim(np.log2(40), np.log2(1800))
ax.set_xlabel("gap (ms, log₂ axis)")
ax.set_ylabel("density (own peak = 1)")
ax.set_title("The two distributions on a log axis — dashed lines mark each "
             "segment's dominant peak", loc="left", color=INK)
ax.legend(loc="upper right")
tidy(ax)
fig.tight_layout()
fig.savefig(OUT / "fig2_log_overlay.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# Fig 3 -- peaks divided by each segment's own fitted beat. If the idea holds,
# both segments land on the same printable ratios despite different tempi. The
# lower panel repeats segment B at its runner-up beat, because the two score
# within 0.1 % of each other and the picture is the only way to see the choice.
RATIO_TICKS = [(1 / 8, "⅛"), (1 / 6, "⅙"), (1 / 4, "¼"), (1 / 3, "⅓"),
               (3 / 8, "⅜"), (1 / 2, "½"), (2 / 3, "⅔"), (1, "1"),
               (4 / 3, "1⅓"), (3 / 2, "1½"), (2, "2"), (3, "3")]
ceiling = max(max(p.share for p in d["peaks"]) for d in per_segment.values()) * 122
runner_up = per_segment["B"]["candidates"][1][1]
panels = [
    [("A", per_segment["A"]["beat"]), ("B", per_segment["B"]["beat"])],
    [("A", per_segment["A"]["beat"]), ("B", runner_up)],
]
fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.0), sharex=True)
for ax, panel in zip(axes, panels):
    for ratio, name in RATIO_TICKS:
        ax.axvline(np.log2(ratio), color=GRID, linewidth=1.0, zorder=0)
        ax.annotate(name, xy=(np.log2(ratio), ceiling), ha="center", va="top",
                    fontsize=9, color=INK_2)
    for key, beat in panel:
        data = per_segment[key]
        for peak in data["peaks"]:
            x = np.log2(peak.median_ms / beat)
            ax.vlines(x, 0, peak.share * 100, color=SERIES[key], linewidth=2.4)
            ax.plot(x, peak.share * 100, "o", color=SERIES[key], markersize=8,
                    markeredgecolor=SURFACE, markeredgewidth=1.6)
            ax.annotate(f"{peak.median_ms:.0f}", xy=(x, peak.share * 100),
                        xytext=(0, 8), textcoords="offset points", ha="center",
                        fontsize=8.5, color=INK_2)
        ax.plot([], [], "o-", color=SERIES[key],
                label=f"Segment {key} · beat {beat:.0f} ms ({60000/beat:.0f} BPM)")
    ax.set_xticks([])
    ax.set_xlim(np.log2(0.075), np.log2(3.6))
    ax.set_ylim(0, ceiling)
    ax.set_ylabel("share of intervals (%)")
    ax.legend(loc="upper left")
    tidy(ax)
axes[0].set_title("Peaks ÷ their own beat, each segment at its best-scoring beat",
                  loc="left", color=INK)
axes[1].set_title(f"Same, with segment B at its runner-up beat "
                  f"({runner_up:.0f} ms) — it scores 0.1 % lower and reads binary",
                  loc="left", color=INK)
axes[1].set_xlabel("peak ÷ beat  (log₂ axis; gridlines are the printable figure ratios)")
fig.tight_layout()
fig.savefig(OUT / "fig3_ratio_ladder.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# Fig 4 -- the payoff: the fitted unit in a sliding window, over the whole piece.
centres, units, scores, counts = A.sliding_tatum(
    attacks, window_s=12.0, hop_s=1.0, min_intervals=10, lo_ms=80.0, hi_ms=200.0)
pd.DataFrame({"window_centre_s": centres.round(2), "fitted_unit_ms": units.round(2),
              "fit_score": scores.round(4), "intervals_in_window": counts}).to_csv(
    OUT / "table_sliding_unit.csv", index=False)
CONFIDENT = 0.55
fig, axes = plt.subplots(2, 1, figsize=(11.5, 6.6), sharex=True,
                         gridspec_kw={"height_ratios": [3, 1]})
ax = axes[0]
solid = np.where(scores >= CONFIDENT, units, np.nan)
faint = np.where(scores < CONFIDENT, units, np.nan)
ax.plot(centres, faint, color=INK_2, linewidth=1.4, alpha=0.35,
        label=f"low-confidence window (fit < {CONFIDENT})")
ax.plot(centres, solid, color=SERIES["A"], linewidth=2.0, label="12 s sliding fit")
ax.axvline(SPLIT_SECONDS, color=SERIES["B"], linewidth=1.6, linestyle=(0, (5, 3)),
           label="3:37 — the change David hears")
for key, data in per_segment.items():
    ax.hlines(data["unit"], data["lo"], min(data["hi"], float(attacks[-1])),
              color=INK_2, linewidth=1.4, linestyle=":", alpha=0.85)
    ax.annotate(f"segment {key} fit: {data['unit']:.1f} ms",
                xy=(data["lo"] + 8, data["unit"]), xytext=(0, 8),
                textcoords="offset points", fontsize=9, color=INK_2)
ax.set_ylabel("fitted grid unit (ms)")
ax.set_title("Fitted grid unit in a 12 s sliding window — no BPM, no note names, "
             "just the gaps", loc="left", color=INK)
ax.legend(loc="upper left", ncols=3)
tidy(ax)
axes[1].fill_between(centres, counts, color=INK_2, alpha=0.22, linewidth=0)
axes[1].plot(centres, counts, color=INK_2, linewidth=1.2)
axes[1].axvline(SPLIT_SECONDS, color=SERIES["B"], linewidth=1.6, linestyle=(0, (5, 3)))
axes[1].set_ylabel("intervals\nin window")
axes[1].set_xlabel("time in the segment (s)")
tidy(axes[1])
fig.tight_layout()
fig.savefig(OUT / "fig4_sliding_unit.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# Fig 5 -- the two objectives, so neither chosen number is a black box.
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
for key, data in per_segment.items():
    axes[0].plot(data["unit_grid"], data["unit_score"], color=SERIES[key],
                 linewidth=1.8, label=f"Segment {key}")
    axes[0].plot(data["unit"], np.interp(data["unit"], data["unit_grid"],
                                         data["unit_score"]), "o",
                 color=SERIES[key], markersize=8, markeredgecolor=SURFACE,
                 markeredgewidth=1.6)
    axes[1].plot(60000.0 / data["beat_grid"], data["beat_score"],
                 color=SERIES[key], linewidth=1.8, label=f"Segment {key}")
    for score, beat in data["candidates"]:
        axes[1].plot(60000.0 / beat, score, "o", color=SERIES[key], markersize=7,
                     markeredgecolor=SURFACE, markeredgewidth=1.6)
        axes[1].annotate(f"{60000/beat:.0f}", xy=(60000.0 / beat, score),
                         xytext=(0, 8), textcoords="offset points", ha="center",
                         fontsize=8.5, color=INK_2)
axes[0].set_xlabel("candidate grid unit (ms)")
axes[0].set_ylabel("share of intervals explained")
axes[0].set_title("Tatum objective", loc="left", color=INK)
axes[1].set_xlabel("candidate beat (BPM)")
axes[1].set_ylabel("peak mass on printable ratios")
axes[1].set_title("Beat objective — labelled dots are the shortlist", loc="left",
                  color=INK)
axes[1].set_xlim(50, 240)
axes[0].legend(loc="upper right")
axes[1].legend(loc="lower right")
for ax in axes:
    tidy(ax)
fig.tight_layout()
fig.savefig(OUT / "fig5_objectives.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# Fig 6 -- what the app's current binary grid does to these intervals.
app_step_ms = C.seconds_per_column(APP_GRANULARITY, tempo_bpm) * 1000.0
fig, ax = plt.subplots(figsize=(11.5, 4.4))
for key, data in per_segment.items():
    values = data["intervals"]
    values = values[values < 4.5 * data["beat"]]
    ax.hist(binary_phase(values, app_step_ms), bins=np.arange(0, 1.05, 0.05),
            color=SERIES[key], alpha=0.5, edgecolor=SURFACE, linewidth=1.2,
            density=True, label=f"Segment {key} · {len(values)} intervals")
ax.axvline(1.0, color=INK_2, linewidth=1.2, linestyle=(0, (4, 3)))
ax.annotate("worst case:\nexactly between two columns", xy=(0.995, ax.get_ylim()[1]),
            xytext=(-8, -6), textcoords="offset points", ha="right", va="top",
            fontsize=9, color=INK_2)
ax.set_xlabel(f"distance from the nearest {APP_GRANULARITY} column "
              f"({app_step_ms:.1f} ms at {tempo_bpm:.0f} BPM), 0 = on the column, "
              f"1 = halfway")
ax.set_ylabel("density")
ax.set_title("How far the played gaps sit from the grid the score is written on",
             loc="left", color=INK)
ax.legend(loc="upper left")
tidy(ax)
fig.tight_layout()
fig.savefig(OUT / "fig6_binary_grid_phase.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# --------------------------------------------------------------------------
# 5. Where does the split actually want to be?
# --------------------------------------------------------------------------
# Independent of the sliding window and of David's 3:37: try every boundary in a
# range and keep the one whose two halves are jointly best explained by their own
# grid units. Reported, not used -- the split above stays at 217 s.
split_rows = []
for boundary in np.arange(180.0, 255.0, 1.0):
    before = np.diff(attacks[attacks < boundary]) * 1000.0
    after = np.diff(attacks[attacks >= boundary]) * 1000.0
    if len(before) < 60 or len(after) < 60:
        continue
    _, _, score_before = A.fit_tatum(before, lo_ms=80.0, hi_ms=200.0)
    _, _, score_after = A.fit_tatum(after, lo_ms=80.0, hi_ms=200.0)
    joint = (score_before.max() * len(before) + score_after.max() * len(after)) \
        / (len(before) + len(after))
    split_rows.append({"boundary_s": boundary, "joint_fit": round(float(joint), 5)})
split_table = pd.DataFrame(split_rows)
split_table.to_csv(OUT / "table_split_search.csv", index=False)
best_split = split_table.loc[split_table["joint_fit"].idxmax(), "boundary_s"]

# --------------------------------------------------------------------------
# 6. Machine-readable summary
# --------------------------------------------------------------------------

(OUT / "results.json").write_text(json.dumps({
    "title": title, "durationSeconds": duration, "gridTempoBpm": round(tempo_bpm, 3),
    "hand": HAND, "chordWindowMs": CHORD_WINDOW_MS, "splitSeconds": SPLIT_SECONDS,
    "appGranularity": APP_GRANULARITY, "appStepMs": round(app_step_ms, 2),
    "handLabelling": {"right": label_report.matched_right,
                      "left": label_report.matched_left,
                      "unmatched": label_report.unmatched},
    "onsets": int(len(onsets)), "attacks": int(len(attacks)),
    "bestSplitSeconds": float(best_split),
    "segments": {k: {
        "span": d["span"], "intervals": int(len(d["intervals"])),
        "dominantPeakMs": round(d["dominant"].median_ms, 2),
        "fittedTatumMs": round(d["unit"], 2),
        "fittedBeatMs": round(d["beat"], 2),
        "fittedBpm": round(60000.0 / d["beat"], 2),
        "swingRatio": None if d["swing"] is None else round(d["swing"][2], 3),
        "beatCandidates": [{"beatMs": round(b, 1), "bpm": round(60000.0 / b, 1),
                            "score": round(s, 4)} for s, b in d["candidates"]],
        "peaks": [{"ms": round(p.median_ms, 2), "count": p.mass,
                   "share": round(p.share, 4)} for p in d["peaks"]],
    } for k, d in per_segment.items()},
}, indent=2), encoding="utf-8")

print("\n== summary ==")
print(summary_table.to_string(index=False))
print("\n== peaks ==")
print(peaks_table.to_string(index=False))
print("\n== beat candidates ==")
print(candidates_table.to_string(index=False))
print("\n== chord-window sensitivity ==")
print(sensitivity.to_string(index=False))
print(f"\n== best split boundary in 180-255 s: {best_split:.0f} s "
      f"(David's 3:37 = {SPLIT_SECONDS:.0f} s) ==")
print(split_table.iloc[(split_table["joint_fit"].values.argsort()[::-1])[:6]]
      .to_string(index=False))
for key, data in per_segment.items():
    print(f"\nsegment {key}: swing {data['swing']}")
print(f"\nwrote {len(list(OUT.glob('*')))} files to {OUT}")
