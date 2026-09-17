"""The same cut-row histogram on the first video, as a control."""
import sys, json
import numpy as np
from collections import Counter
from aitu_backend.video import store, stitch, notes as notes_module
U = 'ddd8bce8-3e3f-4262-9595-46aaf66de54b'
cal = store.load_calibration(U); duration = store.load_metadata(U).duration_seconds
roll, geom = stitch.build(U)
count = store.frame_count(U)
frame_row = np.full(geom.rows, -1, np.int32)
for i in range(count):
    start, end = stitch.rows_of(i, geom); top = geom.rows - 1 - end; n = end - start + 1
    frame_row[top: top + n] = geom.strip_top + np.arange(n)
notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
by = {}
for n in notes: by.setdefault(n.midi, []).append(n)
cut_rows = []; gaps = []
for m, ns in by.items():
    ns.sort(key=lambda n: n.start)
    for p, q in zip(ns, ns[1:]):
        g = p.row_top - q.row_bottom - 1; gaps.append(g)
        if g == 0: cut_rows.append(int(frame_row[q.row_bottom]))
print('first video: strip rows', geom.strip_top, 'to', geom.strip_top + geom.strip_height - 1, '; notes', len(notes), '; split cuts', len(cut_rows), '; real borders 3-8 rows', sum(1 for g in gaps if 3 <= g <= 8))
print('cuts by frame row:', sorted(Counter(cut_rows).items()))
