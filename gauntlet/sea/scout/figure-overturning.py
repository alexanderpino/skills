"""The evidence figure for `gauntlet/sea/overturning-price.md`.

Draws only what `measure-overturning.py` and `measure-breaker-class.py`
measured. `beach_plot` is the project's own toolkit (there is no matplotlib in
this container). No commentary is burned into the pixels -- wave 11's ruling --
the caption is the sidecar `s20-overturning.caption.md`.
"""
import math
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'terrain-renderer', 'reference-impl'))
import beach as B                                            # noqa: E402
import beach_plot as P                                       # noqa: E402

SCR = os.environ.get('SCOUT_CACHE', '/tmp/') + os.sep
OUT = os.path.join(ROOT, 'gauntlet', 'sea', 'evidence', 's20-overturning.png')

z = np.load(SCR + 'overturn.npz')
bay = pickle.load(open(SCR + 'bay.pkl', 'rb'))
x, y, h, tr = bay['x'], bay['y'], bay['h'], bay['tr']
dx = float(x[1] - x[0])
m = np.abs(-np.gradient(h, dx, axis=1))
d, H, k = tr['d'], tr['H'], tr['k']
L = 2.0 * math.pi / np.maximum(k, 1e-9)
xi = m / np.sqrt(np.maximum(H / L, 1e-12))
j = y.size // 2

BED = (70, 74, 82)
XI = (192, 57, 43)
BRK = (27, 122, 68)
SHIP = (31, 78, 156)
CARR = (127, 140, 141)
CEIL = (142, 68, 173)
CLAMP = (233, 126, 58)
WATER = (150, 190, 215)

img = P.canvas(1700, 600)

# ------------------------------------------------------------------ panel 1
sel = (x >= 440) & (x <= 620)
a1 = P.Axes(img, (80, 60, 470, 260), (440, 620), (-5.0, 1.0),
            title='1  the bar flank the wave breaks on',
            ylabel='bed elevation (m)')
a1.frame(xticks=[440, 480, 520, 560, 600], yticks=[-4, -3, -2, -1, 0])
a1.fill_between(x[sel], np.full(sel.sum(), -5.0), h[j, sel], (222, 219, 212))
a1.line(x[sel], h[j, sel], BED, 2)
a1.hline(0.0, (110, 150, 190), 1, (4, 4))

hd = H[j] / np.maximum(d[j], B.D_MIN)
cr = [i for i in range(1, x.size)
      if hd[i - 1] < B.GAMMA_B <= hd[i] and 440 < x[i] < 620
      and d[j, i] >= B.D_MORPH_MIN]
for i in cr:
    a1.vline(x[i], BRK, 2, (7, 5))

a2 = P.Axes(img, (80, 340, 470, 520), (440, 620), (0.0, 1.3),
            title='2  the local surf-similarity number across it',
            xlabel='cross-shore x (m)', ylabel='local xi')
a2.frame(xticks=[440, 480, 520, 560, 600], yticks=[0.0, 0.4, 0.8, 1.2])
a2.band(440, 620, (250, 249, 246))
a2.frame(xticks=[440, 480, 520, 560, 600], yticks=[0.0, 0.4, 0.8, 1.2])
a2.line(x[sel], np.minimum(xi[j, sel], 1.29), XI, 2)
a2.hline(0.4, XI, 1, (6, 5))
for i in cr:
    a2.vline(x[i], BRK, 2, (7, 5))
P.legend(a2, [(XI, 'local xi'), (XI, 'spilling / plunging at xi = 0.4'),
              (BRK, 'H/d crosses gamma_b = 0.78')], 447, 1.22)

# ------------------------------------------------------------------ panel 3
a3 = P.Axes(img, (580, 60, 1030, 520), (0.0, 50.0), (-6.0, 0.0),
            title='3  face-angle exceedance, per-point max over one period',
            xlabel='face angle (deg)',
            ylabel='log10 fraction of wet samples steeper')
a3.frame(xticks=[0, 10, 20, 30, 40, 50],
         yticks=[-6, -5, -4, -3, -2, -1, 0])
wetg = z['dg'] > B.D_MIN
for arr, col in ((z['s_off'], CARR), (z['s_on'], SHIP)):
    v = np.sort(np.degrees(np.arctan(arr[wetg])))[::-1]
    ex = np.log10((np.arange(v.size) + 1.0) / v.size)
    a3.line(v, ex, col, 2)
for deg, col, dash in ((16.41, CARR, (3, 4)), (30.0, XI, (8, 5)),
                       (41.48, CEIL, (8, 5)), (41.48, (0, 0, 0), None)):
    if dash is not None:
        a3.vline(deg, col, 2, dash)
P.legend(a3, [(CARR, 'carrier only (waves 5-18)'),
              (SHIP, 'shipped (wave 19 bundle)'),
              (CARR, 'carrier closed-form ceiling 16.41 deg'),
              (XI, "Stokes' corner, 30 deg"),
              (CEIL, 'one-face Snell cone, 41.48 deg')], 20.0, -0.35)

# ------------------------------------------------------------------ panel 4
a4 = P.Axes(img, (1130, 60, 1640, 520), (150.0, float(x[-1])),
            (float(y[0]), float(y[-1])),
            title='4  where the second-order validity clamp bites',
            xlabel='cross-shore x (m)', ylabel='alongshore y (m)')
clam = z['clam'].astype(bool)
wet = d > B.D_MIN
i0 = int(np.searchsorted(x, 150.0))
rgb = np.zeros((y.size, x.size - i0, 3), np.uint8)
rgb[:] = np.array(P.BG, np.uint8)
w2, c2 = wet[:, i0:], clam[:, i0:]
rgb[w2] = np.array(WATER, np.uint8)
rgb[w2 & c2] = np.array(CLAMP, np.uint8)
a4.image(rgb[::-1])
a4.frame(xticks=[200, 400, 600, 800, 1000],
         yticks=[-600, -300, 0, 300, 600])
xb = z['xb']
a4.line(xb, y[:xb.size], BRK, 2)
P.legend(a4, [(CLAMP, 'r asked for exceeds the single-crest limit'),
              (WATER, 'wet, and within the limit'),
              (BRK, 'the seaward breakpoint')], 170.0, -430.0)

P.save(img, OUT)
print('wrote', OUT)
