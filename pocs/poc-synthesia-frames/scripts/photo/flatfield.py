"""Where the split rule cuts, in frame rows; and a per-pixel gain that flattens the strength inside a rectangle."""
import sys, json, time
sys.path.insert(0, sys.argv[1])
import numpy as np
import extent_core; extent_core.install()
from aitu_backend.video import store, stitch, notes as notes_module, geometry
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]
plate = np.load(S + '/plate_static_full.npy')
store.load_plate = lambda uuid: plate
cal = store.load_calibration(U); cal.roll_top = 0; cal.guard_band = 56
store.load_calibration = lambda uuid: cal
meas = store.load_measurement(U); meas.scroll_speed.px_per_frame = 20.22; meas.scroll_speed.px_per_second = 202.2
store.load_measurement = lambda uuid: meas
duration = store.load_metadata(U).duration_seconds
roll, geom = stitch.build(U)
count = store.frame_count(U)
# the frame row every stitched row came from
frame_row = np.full(geom.rows, -1, dtype=np.int32)
for i in range(count):
    start, end = stitch.rows_of(i, geom)
    top = geom.rows - 1 - end
    n = end - start + 1
    frame_row[top: top + n] = geom.strip_top + np.arange(n)
strikes = json.load(open(S + '/strikes.json')); sk = {}
for m, t in strikes: sk.setdefault(m, []).append(t)
def score(notes):
    by = {}
    for n in notes: by.setdefault(n.midi, []).append(n.start)
    found = sum(1 for m, t in strikes if any(abs(t - s) <= 0.15 for s in by.get(m, [])))
    not_shown = sum(1 for n in notes if not any(abs(n.start - s) <= 0.15 for s in sk.get(n.midi, [])))
    cuts = 0; cut_rows = []
    for m, ns in by.items():
        full = sorted([n for n in notes if n.midi == m], key=lambda n: n.start)
        for p, q in zip(full, full[1:]):
            if p.row_top - q.row_bottom - 1 == 0:
                cuts += 1; cut_rows.append((m, int(frame_row[q.row_bottom])))
    return found, not_shown, cuts, cut_rows
notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
found, not_shown, cuts, cut_rows = score(notes)
print(f'plain      : notes {len(notes)}  found {found} of {len(strikes)} ({100*found/len(strikes):.1f}%)  not shown {not_shown} ({100*not_shown/len(notes):.1f}%)  split cuts {cuts}')
from collections import Counter
c = Counter(cut_rows)
print('   cuts by (key, frame row), top 12:', c.most_common(12))
print('   cuts by frame row:', sorted(Counter(r for _, r in cut_rows).items()))
# the gain: per (frame row, x), the 90th percentile of the strength where it is foreground
tau = 24.0
gain = np.zeros((720, 1280), np.float32)
for fr in range(geom.strip_top, geom.strip_top + geom.strip_height):
    rows = np.where(frame_row == fr)[0]
    block = roll[rows].astype(np.float32)
    fg = np.where(block > tau, block, np.nan)
    with np.errstate(all='ignore'):
        gain[fr] = np.nan_to_num(np.nanpercentile(fg, 90, axis=0), nan=0.0)
strip = gain[geom.strip_top: geom.strip_top + geom.strip_height]
ref = float(np.median(strip[strip > 0]))
print(f'gain over the strip: reference {ref:.0f}; per-x spread within the strip (max/min over the 20 rows), p50/p90 over x:', np.percentile((strip.max(axis=0) / np.maximum(strip.min(axis=0), 1))[strip.min(axis=0) > 0], [50, 90]).round(2))
flat = roll.astype(np.float32).copy()
for fr in range(geom.strip_top, geom.strip_top + geom.strip_height):
    rows = np.where(frame_row == fr)[0]
    g = np.where(gain[fr] > tau, gain[fr], ref)
    flat[rows] = roll[rows] * (ref / g)[None, :]
flat = np.clip(flat, 0, 255).astype(np.uint8)
notes2, _ = notes_module.notes_from_roll(flat, cal, geom, duration)
found, not_shown, cuts, cut_rows = score(notes2)
print(f'flattened  : notes {len(notes2)}  found {found} of {len(strikes)} ({100*found/len(strikes):.1f}%)  not shown {not_shown} ({100*not_shown/len(notes2):.1f}%)  split cuts {cuts}')
print('   cuts by frame row:', sorted(Counter(r for _, r in cut_rows).items()))
json.dump({'notes': [n.model_dump(by_alias=True) for n in notes2]}, open(S + '/notes_flat.json', 'w'))
np.save(S + '/gain.npy', gain)
