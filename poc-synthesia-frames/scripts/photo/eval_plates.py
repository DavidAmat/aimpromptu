"""Every candidate plate: what frame 65 looks like against it, the lane occupancy, the roll bounds."""
import sys, json
import numpy as np
from PIL import Image
from aitu_backend.video import store, geometry, motion
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]
cal = store.load_calibration(U)
upper = int(round(cal.upper_line))
keys = geometry.keys(cal)
cores = [(max(0, int(round(k.left))), min(1280, int(round(k.right)) + 1)) for k in keys]
plates = {
    'p20 (shipped)': np.load(f'data/audio/{U}/video/plate.npy')[:upper],
    'p05': np.load(S + '/plate_p05.npy'),
    'median': np.load(S + '/plate_median.npy'),
    'mode': np.load(S + '/plate_mode.npy'),
    'static': np.load(S + '/plate_static.npy'),
}
picks = np.linspace(100, 1850, 40).round().astype(int)
frames = [store.load_frame(U, int(i))[:upper] for i in picks]
f65 = store.load_frame(U, 65)[:upper]
for name, p in plates.items():
    Image.fromarray(np.clip(p, 0, 255).astype(np.uint8)).save(S + f'/plate_{name.split()[0]}.png')
    d65 = np.abs(f65 - p).max(axis=2)
    Image.fromarray(np.clip(d65, 0, 255).astype(np.uint8)).save(S + f'/diff65_{name.split()[0]}.png')
    occ = np.zeros(len(keys)); fg = 0.0
    for f in frames:
        d = np.abs(f - p).max(axis=2) > 24
        fg += d.mean()
        for j, (a, b) in enumerate(cores):
            occ[j] += d[:, a:b].mean()
    occ /= len(frames); fg /= len(frames)
    worst = sorted([(round(float(o), 2), keys[j].midi) for j, o in enumerate(occ)], reverse=True)[:5]
    load = lambda i, p=p: np.repeat(np.abs(store.load_frame(U, i)[:upper] - p).max(axis=2)[..., None], 3, axis=2)
    top, bottom, score = motion.roll_bounds(load, list(range(940, 955)), cal.upper_line, 20.16)
    print(f'{name:14s} foreground share {fg:.3f}  worst lanes {worst}  roll bounds top {top} bottom {bottom} (guard {upper-bottom})  score by band {[round(float(score[a:a+100].mean()),3) for a in range(0,upper,100)]}')
