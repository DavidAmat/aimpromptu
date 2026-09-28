"""What the strength looks like around a cut at a strip seam."""
import sys, json
sys.path.insert(0, sys.argv[1])
import numpy as np
import extent_core; extent_core.install()
from aitu_backend.video import store, stitch, notes as notes_module, geometry
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]
plate = np.load(S + '/plate_static_full.npy'); store.load_plate = lambda uuid: plate
cal = store.load_calibration(U); cal.roll_top = 0; cal.guard_band = 56; store.load_calibration = lambda uuid: cal
meas = store.load_measurement(U); meas.scroll_speed.px_per_frame = 20.22; meas.scroll_speed.px_per_second = 202.2; store.load_measurement = lambda uuid: meas
duration = store.load_metadata(U).duration_seconds
roll, geom = stitch.build(U)
count = store.frame_count(U)
frame_row = np.full(geom.rows, -1, np.int32); frame_of = np.full(geom.rows, -1, np.int32)
for i in range(count):
    start, end = stitch.rows_of(i, geom); top = geom.rows - 1 - end; n = end - start + 1
    frame_row[top: top + n] = geom.strip_top + np.arange(n); frame_of[top: top + n] = i
notes, _ = notes_module.notes_from_roll(roll, cal, geom, duration)
keys = {k.midi: k for k in geometry.keys(cal)}
by = {}
for n in notes: by.setdefault(n.midi, []).append(n)
sites = []
for m, ns in by.items():
    ns.sort(key=lambda n: n.start)
    for p, q in zip(ns, ns[1:]):
        if p.row_top - q.row_bottom - 1 == 0:
            sites.append((m, q.row_bottom, int(frame_row[q.row_bottom]), int(frame_of[q.row_bottom])))
shown = 0
for m, r, fr, fi in sites:
    if fr not in (15, 34, 35, 25) or shown >= 8: continue
    if fr == 25 and shown < 6: continue
    shown += 1
    k = keys[m]; a, b = int(round(k.left)), int(round(k.right)) + 1
    prof = roll[r - 12: r + 13, a:b].mean(axis=1)
    print(f'key {m} cut at stitched row {r} = frame {fi} row {fr}:')
    print('   frame rows :', frame_row[r - 12: r + 13].tolist())
    print('   strength   :', prof.round(0).astype(int).tolist())
    # the picture itself at the seam: the frame rows of both frames around the seam, mean over the lane core
    if fr in (15, 34, 35):
        fa, fb = (fi, fi + 1) if fr == 15 else (fi - 1, fi)   # older frame and newer frame around this seam
        A = store.load_frame(U, fa); B = store.load_frame(U, fb)
        print('   older frame', fa, 'rows 10..20 mean rgb:', [A[y, a + 3:b - 3].mean(axis=0).round(0).astype(int).tolist() for y in range(10, 21, 2)])
        print('   newer frame', fb, 'rows 30..40 mean rgb:', [B[y, a + 3:b - 3].mean(axis=0).round(0).astype(int).tolist() for y in range(30, 41, 2)])
        print('   plate rows 10..20:', [plate[y, a + 3:b - 3].mean(axis=0).round(0).astype(int).tolist() for y in range(10, 21, 2)], ' plate rows 30..40:', [plate[y, a + 3:b - 3].mean(axis=0).round(0).astype(int).tolist() for y in range(30, 41, 2)])
