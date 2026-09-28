"""An extent measured against the rectangle's own core rather than the brightest column in the window."""
import numpy as np
from aitu_backend.video import detector
def full_extent_core(strength, y0, y1, centre, white_width, settings, filled=None, filled_x0=0):
    lo = max(0, int(round(centre - settings.extent_window * white_width)))
    hi = min(strength.shape[1], int(round(centre + settings.extent_window * white_width)) + 1)
    if hi - lo < 3:
        return None
    per_column = np.median(strength[y0 : y1 + 1, lo:hi], axis=0)
    c = int(round(centre)) - lo
    if not (0 <= c < len(per_column)):
        return None
    # the reference is the key's own core: the median of the columns within a quarter key of the centre
    core = per_column[max(0, c - int(0.25 * white_width)) : c + int(0.25 * white_width) + 1]
    reference = float(np.median(core))
    if reference <= settings.tau_foreground:
        return None
    column = per_column >= max(settings.tau_edge * reference, settings.tau_foreground)
    if not column[c]:
        return None
    a = c
    while a > 0 and column[a - 1]:
        a -= 1
    b = c
    while b < len(column) - 1 and column[b + 1]:
        b += 1
    return float(lo + a), float(lo + b)
def install():
    detector._full_extent = full_extent_core
