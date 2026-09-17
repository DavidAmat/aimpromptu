"""split_prominence swept under the local plateau, on one video, against its keyboard."""
import sys, json
sys.path.insert(0, sys.argv[1])
import numpy as np
from collections import Counter
import extent_core; extent_core.install()
import local_valleys; local_valleys.install(14)
from aitu_backend.video import store, stitch, notes as notes_module
from aitu_backend.video.detector import DetectorSettings
S = sys.argv[1]; which = sys.argv[2]
if which == 'photo':
    U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
    plate = np.load(S + '/plate_static_full.npy'); store.load_plate = lambda uuid: plate
    cal = store.load_calibration(U); cal.roll_top = 0; cal.guard_band = 56; store.load_calibration = lambda uuid: cal
    meas = store.load_measurement(U); meas.scroll_speed.px_per_frame = 20.22; meas.scroll_speed.px_per_second = 202.2; store.load_measurement = lambda uuid: meas
    strikes = json.load(open(S + '/strikes.json'))
else:
    U = 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'; cal = store.load_calibration(U)
    strikes = [tuple(x) for x in json.load(open(S + '/strikes_first.json'))]
duration = store.load_metadata(U).duration_seconds
roll, geom = stitch.build(U)
sk = {}
for m, t in strikes: sk.setdefault(m, []).append(t)
for prom in [0.15, 0.2, 0.25, 0.3, 0.4]:
    settings = DetectorSettings(split_prominence=prom)
    notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration, settings=settings)
    by = {}
    for n in notes: by.setdefault(n.midi, []).append(n)
    found = sum(1 for m, t in strikes if any(abs(t - n.start) <= 0.15 for n in by.get(m, [])))
    not_shown = sum(1 for n in notes if not any(abs(n.start - s) <= 0.15 for s in sk.get(n.midi, [])))
    cuts = sum(1 for m, ns in by.items() for p, q in zip(sorted(ns, key=lambda n: n.start), sorted(ns, key=lambda n: n.start)[1:]) if p.row_top - q.row_bottom - 1 == 0)
    long = sum(1 for n in notes if n.end - n.start > 2.0)
    print(f'{which} local W=14 prominence {prom:.2f}: notes {len(notes)}  found {found} of {len(strikes)} ({100*found/len(strikes):.1f}%)  not shown {not_shown} ({100*not_shown/len(notes):.1f}%)  split cuts {cuts}  notes over 2 s {long}  median length {np.median([(n.end-n.start)*1000 for n in notes]):.0f} ms')
    if which == 'photo' and prom == 0.25:
        json.dump({'notes': [n.model_dump(by_alias=True) for n in notes]}, open(S + '/notes_photo_final.json', 'w'))
