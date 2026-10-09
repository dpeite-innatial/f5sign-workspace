"""Trace the red part of the Factor5 logo (cover of the identity manual, 300ppi) to SVG.

Marching squares on a continuous "redness" field (r - g), iso 0.5, then
Ramer-Douglas-Peucker simplification. Output: one path per closed contour,
fill-rule evenodd so counters come out as holes.
"""
import json
import sys

import numpy as np
from PIL import Image, ImageFilter

SRC = sys.argv[1]
OUT = sys.argv[2]
MAX_ROW = int(sys.argv[3]) if len(sys.argv) > 3 else None  # cut the rule line below the logo
EPS = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8

im = Image.open(SRC).convert('RGB').filter(ImageFilter.GaussianBlur(0.8))
a = np.asarray(im).astype(float)
f = np.clip((a[..., 0] - a[..., 1]) / 136.0, 0, 1)
if MAX_ROW:
    f[MAX_ROW:, :] = 0
f = np.pad(f, 1)  # closed contours at the borders
H, W = f.shape
ISO = 0.5

b = (f > ISO).astype(np.uint8)
case = b[:-1, :-1] * 1 + b[:-1, 1:] * 2 + b[1:, 1:] * 4 + b[1:, :-1] * 8


def pt(edge):
    kind, i, j = edge
    if kind == 'h':  # between (i,j) and (i,j+1)
        va, vb = f[i, j], f[i, j + 1]
        t = (ISO - va) / (vb - va)
        return (j + t, i)
    va, vb = f[i, j], f[i + 1, j]  # between (i,j) and (i+1,j)
    t = (ISO - va) / (vb - va)
    return (j, i + t)


# edges of cell (i,j): top=h(i,j), right=v(i,j+1), bottom=h(i+1,j), left=v(i,j)
SEG = {
    1: [('t', 'l')], 2: [('t', 'r')], 3: [('l', 'r')], 4: [('r', 'b')],
    6: [('t', 'b')], 7: [('l', 'b')], 8: [('l', 'b')], 9: [('t', 'b')],
    11: [('r', 'b')], 12: [('l', 'r')], 13: [('t', 'r')], 14: [('t', 'l')],
}
adj = {}


def link(e1, e2):
    adj.setdefault(e1, []).append(e2)
    adj.setdefault(e2, []).append(e1)


ii, jj = np.nonzero((case > 0) & (case < 15))
for i, j in zip(ii.tolist(), jj.tolist()):
    c = int(case[i, j])
    E = {'t': ('h', i, j), 'r': ('v', i, j + 1), 'b': ('h', i + 1, j), 'l': ('v', i, j)}
    if c in (5, 10):
        centre = (f[i, j] + f[i, j + 1] + f[i + 1, j] + f[i + 1, j + 1]) / 4 > ISO
        if c == 5:
            pairs = [('t', 'r'), ('l', 'b')] if centre else [('t', 'l'), ('r', 'b')]
        else:
            pairs = [('t', 'l'), ('r', 'b')] if centre else [('t', 'r'), ('l', 'b')]
    else:
        pairs = SEG[c]
    for p, q in pairs:
        link(E[p], E[q])

seen = set()
loops = []
for start in adj:
    if start in seen:
        continue
    loop = [start]
    seen.add(start)
    prev, cur = None, start
    while True:
        nxt = [e for e in adj[cur] if e != prev and e not in seen]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        seen.add(cur)
        loop.append(cur)
    if len(loop) > 12:
        loops.append([pt(e) for e in loop])


def rdp(points, eps):
    pts = np.asarray(points)
    if len(pts) < 3:
        return pts
    start, end = pts[0], pts[-1]
    d = end - start
    n = np.hypot(*d)
    if n == 0:
        dist = np.hypot(*(pts - start).T)
    else:
        dist = np.abs(d[0] * (pts[:, 1] - start[1]) - d[1] * (pts[:, 0] - start[0])) / n
    k = int(np.argmax(dist))
    if dist[k] > eps:
        left = rdp(pts[: k + 1], eps)
        right = rdp(pts[k:], eps)
        return np.vstack([left[:-1], right])
    return np.vstack([start, end])


def simplify_closed(loop, eps):
    pts = np.asarray(loop)
    # split the loop at its two farthest points so RDP has stable anchors
    k = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    a_ = rdp(np.vstack([pts[: k + 1]]), eps)
    b_ = rdp(np.vstack([pts[k:], pts[:1]]), eps)
    return np.vstack([a_[:-1], b_[:-1]])


shapes = []
for loop in loops:
    s = simplify_closed(loop, EPS) - 1  # undo the padding
    shapes.append(s.round(2).tolist())

xs = [p[0] for s in shapes for p in s]
ys = [p[1] for s in shapes for p in s]
x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
json.dump({'bbox': [x0, y0, x1, y1], 'shapes': shapes}, open(OUT, 'w'))
print(len(shapes), 'contours,', sum(len(s) for s in shapes), 'points, bbox', [round(v, 1) for v in (x0, y0, x1, y1)])
