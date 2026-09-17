"""valleys() with the plateau measured next to the valley rather than over the whole run."""
import numpy as np
from aitu_backend.video import detector
WINDOW_ROWS = 14
def valleys_local(profile, min_height):
    if len(profile) < 2 * min_height + 1:
        return []
    plateau = float(np.percentile(profile, 75))
    if plateau <= 1:
        return []
    candidates = [i for i in range(min_height, len(profile) - min_height) if profile[i] <= profile[i - 1] and profile[i] <= profile[i + 1]]
    if not candidates:
        return []
    groups = []; current = [candidates[0]]
    for i in candidates[1:]:
        if i - current[-1] <= min_height: current.append(i)
        else: groups.append(current); current = [i]
    groups.append(current)
    out = []
    for group in groups:
        i = min(group, key=lambda row: profile[row])
        a, b = group[0], group[-1] + 1
        left = float(profile[max(0, a - WINDOW_ROWS): a].max()) if a > 0 else 0.0
        right = float(profile[b: b + WINDOW_ROWS].max()) if b < len(profile) else 0.0
        if left <= 0 or right <= 0:
            continue
        out.append((i, (min(left, right) - float(profile[i])) / plateau))
    return out
def install(window):
    global WINDOW_ROWS
    WINDOW_ROWS = window
    detector.valleys = valleys_local
