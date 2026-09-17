"""Why roll_bounds answered nothing: the per-row score on raw grey vs on the plate difference."""
import numpy as np
from aitu_backend.video import store, motion
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
cal = store.load_calibration(U)
upper = int(round(cal.upper_line))
old = np.load(f'data/audio/{U}/video/plate.npy')
step = 20
idx = list(range(940, 955))
def score_of(load):
    top, bottom, s = motion.roll_bounds(load, idx, cal.upper_line, 20.16)
    return top, bottom, s
raw = lambda i: store.load_frame(U, i)
print('raw grey   :', score_of(raw)[:2])
diff = lambda i: np.repeat(np.abs(store.load_frame(U, i) - old).max(axis=2)[..., None], 3, axis=2)
t, b, s = score_of(diff)
print('old plate diff:', t, b, 'score p10/50/90', np.percentile(s, [10, 50, 90]).round(3))
t, b, s2 = score_of(raw)
print('raw score p10/50/90', np.percentile(s2, [10, 50, 90]).round(3))
print('raw score by 50-row band:', [round(float(s2[a:a+50].mean()), 3) for a in range(0, upper, 50)])
print('diff score by 50-row band:', [round(float(s[a:a+50].mean()), 3) for a in range(0, upper, 50)])
