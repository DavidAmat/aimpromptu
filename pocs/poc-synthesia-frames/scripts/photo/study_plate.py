"""One pass over every sampled frame: how the 20th percentile plate fails, and a
plate built from what stays still longer than a rectangle can."""
import sys, time, json
import numpy as np
from aitu_backend.video import store, geometry, plate as plate_module
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]
cal = store.load_calibration(U)
upper = int(round(cal.upper_line))
count = store.frame_count(U)
old = np.load(f'data/audio/{U}/video/plate.npy')[:upper]

# streaming state for the long-static plate
TOL = 12.0            # per-channel change for a pixel to count as unchanged
L = 26                # frames: roll height 515 / travel 20.2 = 25.5 -> a rectangle cannot stay longer
prev = None
run = np.zeros((upper, 1280), dtype=np.int32)
ssum = np.zeros((upper, 1280, 3), dtype=np.float64)
scount = np.zeros((upper, 1280), dtype=np.int32)
# also a plain per-pixel mode over 8-level bins, over all frames, for comparison
hist = np.zeros((upper, 1280, 3, 32), dtype=np.uint16)
# occupancy of each lane core by the old plate
keys = geometry.keys(cal)
cores = [(max(0, int(round(k.left))), min(1280, int(round(k.right)) + 1)) for k in keys]
occ_old = np.zeros(len(keys))
t0 = time.time()
picks = set(np.linspace(0, count - 1, 100).round().astype(int).tolist())
spread = []
for i in range(count):
    f = store.load_frame(U, i)[:upper]
    if i in picks:
        spread.append(f.astype(np.uint8))
    q = (f // 8).astype(np.intp)
    for c in range(3):
        np.add.at(hist[:, :, c, :], (np.arange(upper)[:, None], np.arange(1280)[None, :], q[:, :, c]), 1)
    if prev is not None:
        still = np.abs(f - prev).max(axis=2) < TOL
        run = np.where(still, run + 1, 0)
        long = run >= L
        ssum[long] += f[long]
        scount[long] += 1
    prev = f
    d = np.abs(f - old).max(axis=2) > 24
    for j, (a, b) in enumerate(cores):
        if b - a >= 2:
            occ_old[j] += d[:, a:b].mean()
    if i % 200 == 0:
        print(i, round(time.time() - t0, 1), 's', flush=True)
occ_old /= count
static = np.where(scount[..., None] > 0, ssum / np.maximum(scount, 1)[..., None], np.nan)
print('pixels with no long-static value:', np.isnan(static[..., 0]).mean())
# fill the holes from the mode plate
mode = (np.argmax(hist, axis=3) * 8 + 4).astype(np.float32)
filled = np.where(np.isnan(static), mode, static).astype(np.float32)
np.save(S + '/plate_static.npy', filled)
np.save(S + '/plate_mode.npy', mode)
np.save(S + '/plate_scount.npy', scount)
stack = np.stack(spread)
np.save(S + '/plate_p05.npy', np.percentile(stack, 5, axis=0).astype(np.float32))
np.save(S + '/plate_p20.npy', np.percentile(stack, 20, axis=0).astype(np.float32))
np.save(S + '/plate_median.npy', np.median(stack, axis=0).astype(np.float32))
json.dump({'occ_old': occ_old.tolist(), 'midis': [k.midi for k in keys]}, open(S + '/occupancy.json', 'w'))
print('done', round(time.time() - t0, 1), 's')
