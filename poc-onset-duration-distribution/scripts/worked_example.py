"""One passage, four rows: what was played, where the beats are, what the app
wrote, what the sheet says.

The F–E–C at 00:46 of the original video. David's question was: the sheet calls
these corcheas, so why is there no peak at half a negra? The answer is on this
picture -- in a shuffle the two corcheas of a beat are not equal, so "half a
negra" is a value nobody plays.

    python3 scripts/worked_example.py
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as C

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2de"
BLUE, ORANGE = "#2a78d6", "#eb6834"

OFFSET = 5.0                 # the stored audio starts 5 s into the video
BEAT_MS = 337.2
ANCHOR = 42.087              # a confidently on-beat attack, segment clock
LO, HI = 41.30, 42.35

events, duration, _ = C.load_events()
tempo_bpm = C.infer_tempo_bpm(C.load_matrix("raw.npz").shape[1], duration)
right = C.load_matrix("two-hands_semicorchea_right.npz")
left = C.load_matrix("two-hands_semicorchea_left.npz")
labels, _ = C.label_hands(events, right, left, tempo_bpm)
step_s = C.seconds_per_column("semicorchea", tempo_bpm)

PASSAGE = [("F5", 77), ("E5", 76), ("C5", 72)]
played = []
for name, midi in PASSAGE:
    hits = [e["start"] for e, l in zip(events, labels)
            if l == "R" and e["midiNote"] == midi and LO <= e["start"] <= HI]
    played.append((name, min(hits)))
played.sort(key=lambda item: item[1])

written = {}
for name, midi in PASSAGE:
    row = midi - 21
    for column in np.where(right[row] == 1)[0]:
        if LO <= column * step_s <= HI:
            length = 1
            while (column + length < right.shape[1]
                   and right[row, column + length] == -1):
                length += 1
            written[name] = (int(column), int(length))

fig, ax = plt.subplots(figsize=(12, 6.2))
ax.set_facecolor(SURFACE)
fig.patch.set_facecolor(SURFACE)

# --- the beat grid, with each beat's long/short split shaded -----------------
beat = BEAT_MS / 1000.0
first = ANCHOR - np.ceil((ANCHOR - LO) / beat) * beat
edges = np.arange(first, HI + beat, beat)
BAND_LO, BAND_HI = 0.50, 0.575
for start in edges:
    ax.axvline(start, color=INK_2, linewidth=1.6, alpha=0.6, zorder=1)
    long_end = start + beat * 0.627
    ax.axvspan(max(start, LO), min(long_end, HI), ymin=BAND_LO, ymax=BAND_HI,
               color=BLUE, alpha=0.30, zorder=0)
    ax.axvspan(max(long_end, LO), min(start + beat, HI), ymin=BAND_LO, ymax=BAND_HI,
               color=ORANGE, alpha=0.40, zorder=0)
    if LO < start + beat / 2 < HI:
        ax.annotate("211 ms", xy=(start + beat * 0.31, (BAND_LO + BAND_HI) / 2),
                    xycoords=("data", "axes fraction"), ha="center", va="center",
                    fontsize=9, color=INK)
        ax.annotate("125", xy=(start + beat * 0.81, (BAND_LO + BAND_HI) / 2),
                    xycoords=("data", "axes fraction"), ha="center", va="center",
                    fontsize=9, color=INK)
ax.annotate("one beat = 337 ms, split long-then-short by the pianist",
            xy=(LO + 0.006, BAND_HI + 0.02), xycoords=("data", "axes fraction"),
            ha="left", fontsize=10, color=INK_2)

# --- the app's semicorchea columns ------------------------------------------
for column in range(int(LO / step_s), int(HI / step_s) + 2):
    ax.axvline(column * step_s, color=GRID, linewidth=1.0, zorder=0)

# --- row 1: what was played --------------------------------------------------
Y_PLAYED = 0.88
for index, (name, time) in enumerate(played):
    ax.plot([time], [Y_PLAYED], "o", transform=ax.get_xaxis_transform(),
            color=INK, markersize=11, zorder=5)
    ax.annotate(name, xy=(time, Y_PLAYED), xycoords=("data", "axes fraction"),
                xytext=(0, 13), textcoords="offset points", ha="center",
                fontsize=12, color=INK, weight="bold")
    if index:
        previous = played[index - 1][1]
        gap = (time - previous) * 1000
        ax.annotate("", xy=(time, Y_PLAYED - 0.055), xytext=(previous, Y_PLAYED - 0.055),
                    xycoords=("data", "axes fraction"), textcoords=("data", "axes fraction"),
                    arrowprops=dict(arrowstyle="<->", color=INK_2, linewidth=1.3))
        ax.annotate(f"{gap:.0f} ms", xy=((time + previous) / 2, Y_PLAYED - 0.085),
                    xycoords=("data", "axes fraction"), ha="center", fontsize=10.5,
                    color=INK_2)

# --- row 2 / row 3: what the app wrote vs what the sheet says ----------------
def bar(y, column, length, colour, text):
    ax.barh(y, length * step_s, left=column * step_s, height=0.05,
            transform=ax.get_xaxis_transform(), color=colour, alpha=0.85,
            edgecolor=SURFACE, linewidth=2.0, zorder=4)
    ax.annotate(text, xy=(column * step_s + length * step_s / 2, y + 0.037),
                xycoords=("data", "axes fraction"), ha="center", va="bottom",
                fontsize=9.5, color=INK, zorder=6)


Y_APP, Y_SHEET = 0.30, 0.10
FIGURE = {1: "semicorchea", 2: "corchea", 3: "corchea con puntillo", 4: "negra"}
# The sheet row is drawn on the *intended* grid, not on the played times: three
# equal corcheas, the middle one starting on the beat. That is the whole point --
# the page says "equal", the performance says otherwise.
beat_column = round(41.750 / step_s)
for offset, (name, _time) in zip((-2, 0, 2), played):
    column, length = written[name]
    bar(Y_APP, column, length, ORANGE, f"{name}: {FIGURE.get(length, str(length))}")
    bar(Y_SHEET, beat_column + offset, 2, BLUE, f"{name}: corchea")

for y, text in [(Y_PLAYED, "1 · what the pianist played"),
                (Y_APP, "2 · what the app wrote, read back from the stored score"),
                (Y_SHEET, "3 · what the sheet says — three equal corcheas")]:
    ax.annotate(text, xy=(0.004, y + 0.085), xycoords="axes fraction", ha="left",
                fontsize=11, color=INK_2)

ax.set_xlim(LO, HI)
ax.set_ylim(0, 1)
ax.set_yticks([])
ticks = np.arange(41.3, 42.36, 0.1)
ax.set_xticks(ticks)
ax.set_xticklabels([f"{t + OFFSET:.1f}" for t in ticks])
ax.set_xlabel("time in the original video (s)   ·   thick lines = beats, "
              "thin lines = the app's semicorchea columns")
ax.set_title("The F–E–C at 00:46 — three corcheas on the page, three different "
             "lengths in the air", loc="left", color=INK, fontsize=13)
for spine in ("top", "right", "left"):
    ax.spines[spine].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.grid(False)
fig.tight_layout()
fig.savefig(C.OUT / "fig7_worked_example.png", dpi=170, facecolor=SURFACE)
print("played:", [(n, round(t, 3)) for n, t in played])
print("app wrote:", written)
