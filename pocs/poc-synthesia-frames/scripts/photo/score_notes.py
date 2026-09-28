"""Score a notes list against the strikes the keyboard shows (Phase 4's tool, rebuilt for this rendering)."""
import sys, json
import numpy as np
from aitu_backend.video import store, geometry
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]
LIT = 60.0
sat = np.load(S + '/sat.npy')
cal = store.load_calibration(U)
keys = geometry.keys(cal)
midis = [k.midi for k in keys]
lit = sat > LIT
# a strike: unlit -> lit. time of the frame it is first lit in.
strikes = []
for j, m in enumerate(midis):
    col = lit[:, j]
    on = np.where(col[1:] & ~col[:-1])[0] + 1
    for i in on:
        strikes.append((m, i * 0.1))
always = [m for j, m in enumerate(midis) if lit[:, j].mean() > 0.95]
print('keys lit in every frame (a defect of the tool):', always)
print('strikes', len(strikes), 'over', sat.shape[0] / 10, 's =', round(len(strikes) / (sat.shape[0] / 10), 2), 'a second')
print('lit fraction per key, top 10:', sorted([(round(float(lit[:, j].mean()), 3), m) for j, m in enumerate(midis)], reverse=True)[:10])

def score(notes, tol=0.15, lo=None, hi=None):
    """found: strikes with a note onset on that key within tol. not shown: notes with no strike within tol."""
    st = [(m, t) for m, t in strikes if (lo is None or t >= lo) and (hi is None or t < hi)]
    ns = [(n['midi'], n['start']) for n in notes if (lo is None or n['start'] >= lo) and (hi is None or n['start'] < hi)]
    by_key = {}
    for m, t in ns:
        by_key.setdefault(m, []).append(t)
    found = sum(1 for m, t in st if any(abs(t - s) <= tol for s in by_key.get(m, [])))
    sk = {}
    for m, t in st:
        sk.setdefault(m, []).append(t)
    not_shown = sum(1 for m, t in ns if not any(abs(t - s) <= tol for s in sk.get(m, [])))
    return len(st), found, len(ns), not_shown

if len(sys.argv) > 2:
    data = json.load(open(sys.argv[2]))
    notes = data['notes'] if isinstance(data, dict) else data
    for lo, hi in [(None, None), (5, 65), (65, 125), (125, 185)]:
        n_st, found, n_notes, not_shown = score(notes, lo=lo, hi=hi)
        print(f'window {lo}-{hi}: strikes {n_st}  found {found} ({100*found/max(1,n_st):.0f}%)  notes {n_notes}  not shown {not_shown} ({100*not_shown/max(1,n_notes):.0f}%)')
json.dump(strikes, open(S + '/strikes.json', 'w'))
