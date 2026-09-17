import sys, json
sys.path.insert(0, sys.argv[1])
import numpy as np
from collections import Counter
import extent_core; extent_core.install()
import local_valleys
U_PHOTO = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'; U_FIRST = 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'
S = sys.argv[1]; which = sys.argv[2]; window = int(sys.argv[3])
from aitu_backend.video import store, stitch, notes as notes_module
if which == 'photo':
    U = U_PHOTO
    plate = np.load(S + '/plate_static_full.npy'); store.load_plate = lambda uuid: plate
    cal = store.load_calibration(U); cal.roll_top = 0; cal.guard_band = 56; store.load_calibration = lambda uuid: cal
    meas = store.load_measurement(U); meas.scroll_speed.px_per_frame = 20.22; meas.scroll_speed.px_per_second = 202.2; store.load_measurement = lambda uuid: meas
    strikes = json.load(open(S + '/strikes.json'))
else:
    U = U_FIRST; cal = store.load_calibration(U)
    strikes = [tuple(x) for x in json.load(open(S + '/strikes_first.json'))]
duration = store.load_metadata(U).duration_seconds
roll, geom = stitch.build(U)
count = store.frame_count(U)
frame_row = np.full(geom.rows, -1, np.int32)
for i in range(count):
    start, end = stitch.rows_of(i, geom); top = geom.rows - 1 - end; n = end - start + 1
    frame_row[top: top + n] = geom.strip_top + np.arange(n)
sk = {}
for m, t in strikes: sk.setdefault(m, []).append(t)
def report(label, notes):
    by = {}
    for n in notes: by.setdefault(n.midi, []).append(n)
    found = sum(1 for m, t in strikes if any(abs(t - n.start) <= 0.15 for n in by.get(m, [])))
    not_shown = sum(1 for n in notes if not any(abs(n.start - s) <= 0.15 for s in sk.get(n.midi, [])))
    cuts = []; real = 0
    for m, ns in by.items():
        ns.sort(key=lambda n: n.start)
        for p, q in zip(ns, ns[1:]):
            g = p.row_top - q.row_bottom - 1
            if g == 0: cuts.append(int(frame_row[q.row_bottom]))
            elif g <= 8: real += 1
    c = Counter(cuts); edge = c[geom.strip_top] + c[geom.strip_top + geom.strip_height - 1] + c[geom.strip_top + geom.strip_height - 2]
    print(f'{label:28s}: notes {len(notes)}  found {found} of {len(strikes)} ({100*found/len(strikes):.1f}%)  not shown {not_shown} ({100*not_shown/len(notes):.1f}%)  split cuts {len(cuts)} (at the seam rows {edge})  real borders {real}')
notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
report(f'{which} whole-run plateau', notes)
local_valleys.install(window)
notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
report(f'{which} local plateau W={window}', notes)
json.dump({'notes': [n.model_dump(by_alias=True) for n in notes]}, open(S + f'/notes_{which}_local{window}.json', 'w'))
