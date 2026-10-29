"""Find the systems (grand staves) and the barlines of a rendered score page."""
import subprocess, os, sys
from PIL import Image
import numpy as np

DPI = 200
CACHE = os.environ.get("CROP_CACHE", "/tmp/chopin-r200")

def page(pdf, p):
    os.makedirs(CACHE, exist_ok=True)
    stem = os.path.join(CACHE, f"{os.path.basename(pdf)[:-4]}-{p}")
    if not os.path.exists(stem + '.d.png'):
        subprocess.run(['pdftoppm', '-f', str(p), '-l', str(p), '-r', str(DPI), '-gray', '-png', '-singlefile', pdf, stem], check=True)
        deskew(Image.open(stem + '.png').convert('L')).save(stem + '.d.png')
    return Image.open(stem + '.d.png')

def deskew(im):
    small = im.resize((im.width // 2, im.height // 2))
    w = small.width
    best = (0, 0.0)
    for k in range(-30, 31):
        ang = k * 0.05
        r = np.array(small.rotate(ang, fillcolor=255, resample=Image.BILINEAR))[:, int(w * .3):int(w * .7)] < 128
        score = (r.mean(1) ** 2).sum()
        if score > best[0]: best = (score, ang)
    return im.rotate(best[1], fillcolor=255, resample=Image.BICUBIC)

def staves(a, x0=0.35, x1=0.65):
    w = a.shape[1]
    dark = a[:, int(w * x0):int(w * x1)] < 150
    frac = dark.mean(1)
    rows = [y for y in range(len(frac)) if frac[y] > 0.6]
    lines = []
    for y in rows:
        if lines and y - lines[-1][-1] <= 2: lines[-1].append(y)
        else: lines.append([y])
    ys = [sum(l) / len(l) for l in lines]
    out, i = [], 0
    while i + 4 < len(ys):
        g = ys[i:i + 5]; d = np.diff(g)
        if d.max() - d.min() < 0.35 * d.mean() and 8 < d.mean() < 40:
            out.append((g[0], g[4], d.mean())); i += 5
        else: i += 1
    return out

def systems(a):
    st = staves(a)
    if len(st) < 2: return []
    dist = [st[i + 1][0] - st[i][1] for i in range(len(st) - 1)]
    thr = (min(dist) + max(dist)) / 2 if max(dist) - min(dist) > 2 * st[0][2] else max(dist) + 1
    out, i = [], 0
    while i + 1 < len(st):
        if dist[i] < thr:
            s1, s2 = st[i], st[i + 1]
            out.append({'top': s1[0], 'bottom': s2[1], 'gap': s1[2], 'mid': (s1[1] + s2[0]) / 2, 's1': s1[:2], 's2': s2[:2]})
            i += 2
        else: i += 1
    return out

def barlines(a, s):
    dark = a < 150
    def col(r):
        t, b = int(r[0]) + 2, int(r[1]) - 2
        return dark[t:b, :].mean(0)
    c = np.minimum(col(s['s1']), col(s['s2']))
    xs = [x for x in range(a.shape[1]) if c[x] > 0.9]
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= 3: groups[-1].append(x)
        else: groups.append([x])
    return [round((g[0] + g[-1]) / 2) for g in groups]

if __name__ == '__main__':
    pdf, p = sys.argv[1], int(sys.argv[2])
    a = np.array(page(pdf, p))
    for i, s in enumerate(systems(a)):
        print(i, 'top', round(s['top']), 'bot', round(s['bottom']), 'mid', round(s['mid']), barlines(a, s))
