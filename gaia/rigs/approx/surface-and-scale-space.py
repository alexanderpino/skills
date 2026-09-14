#!/usr/bin/env python3
"""Cross-check the two figures surface-and-scale-space.md pairs in its Tier line.

RIG: CPython + numpy on the session container's CPU, float64, single-threaded scipy-free
separable convolution. This is an AUTHORING-TIME numpy microbenchmark. It is NOT a GPU frame
cost, NOT a shipped-runtime cost, and NOT a C/SIMD implementation -- a tuned build would be
faster and a GPU number would mean something else entirely. Quoted only as build work.

Measures:
  1. wall time of a decimated 512^2 L=5 two-band split, and of the a-trous form  -> the page's
     96 ms / 142 ms (register pseudocode-execution.tsv:205 records 0.096 s / 0.142 s).
  2. working set of the two-band split in bytes per cell.
  3. the mean-correction volume floor on a 257^2 fractal field, 1000 m relief, a=0.4, reflect,
     L=4  -> the page's -0.0050% of sum(h).
Seeded; no randomness outside the seed.
"""
import time
import numpy as np

SEED = 20260910
A = 0.4
W = np.array([0.25 - A / 2, 0.25, A, 0.25, 0.25 - A / 2])


def conv2_sep(g, w, dil=1):
    k = np.zeros((len(w) - 1) * dil + 1)
    k[::dil] = w
    r = len(k) // 2
    o = np.pad(g, ((r, r), (0, 0)), mode="reflect")
    o = np.apply_along_axis(lambda m: np.convolve(m, k, "valid"), 0, o)
    o = np.pad(o, ((0, 0), (r, r)), mode="reflect")
    return np.apply_along_axis(lambda m: np.convolve(m, k, "valid"), 1, o)


def reduce_(g):
    return conv2_sep(g, W)[::2, ::2]


def expand(g, shape):
    up = np.zeros(shape)
    up[::2, ::2] = g[: (shape[0] + 1) // 2, : (shape[1] + 1) // 2]
    return 4.0 * conv2_sep(up, W)


def low_band(h, L):
    shapes, g = [h.shape], h
    for _ in range(L):
        g = reduce_(g)
        shapes.append(g.shape)
    for k in range(L):
        g = expand(g, shapes[L - k - 1])
    return g


def low_band_atrous(h, L):
    g = h
    for l in range(L):
        g = conv2_sep(g, W, dil=2 ** l)
    return g


def fractal(n, relief, seed):
    rng = np.random.default_rng(seed)
    f = np.zeros((n, n))
    amp = 1.0
    for oct_ in range(7):
        m = 2 ** (oct_ + 1) + 1
        c = rng.random((m, m))
        yi = np.linspace(0, m - 1, n)
        g = c[np.clip(np.round(yi).astype(int), 0, m - 1)][:, np.clip(np.round(yi).astype(int), 0, m - 1)]
        f += amp * g
        amp *= 0.5
    f -= f.min()
    return f * (relief / f.max())


def timeit(fn, h, L, reps=3):
    fn(h, L)  # warm
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        lo = fn(h, L)
        hi = h - lo
        ts.append(time.perf_counter() - t0)
    return min(ts), lo, hi


h512 = fractal(512, 1000.0, SEED)
t_dec, lo5, hi5 = timeit(low_band, h512, 5)
t_atr, _, _ = timeit(low_band_atrous, h512, 5)
print(f"1. decimated  512^2 L=5 two-band split : {t_dec * 1e3:8.1f} ms   (page/register: 96 ms)")
print(f"   a-trous    512^2 L=5 two-band split : {t_atr * 1e3:8.1f} ms   (page/register: 142 ms)")
print(f"   ratio a-trous/decimated             : {t_atr / t_dec:8.2f}x   (page: about 1.5x)")

cells = h512.size
resident = lo5.nbytes + hi5.nbytes
print(f"2. two-band working set                 : {resident / cells:8.1f} bytes/cell "
      f"({lo5.dtype}, {lo5.nbytes // cells} bytes x 2 fields)")

h = fractal(257, 1000.0, SEED)
S = h.sum()
ops = {
    "roughen":  lambda r: r + 60 * np.abs(np.random.default_rng(SEED).random(r.shape) - 0.5),
    "distress": lambda r: r - 40 * np.maximum(-r, 0),
    "craggy":   lambda r: np.maximum(r, 0) * 1.6 + np.minimum(r, 0),
    "linear":   lambda r: 1.5 * r,
}
lo = low_band(h, 4)
hi = h - lo
print(f"3. residual mean (split floor), 257^2 L=4: {hi.mean():.4e} m on 1000 m relief "
      f"= {hi.mean() / 1000 * 1e6:.0f} ppm")
for name, f in ops.items():
    r = f(hi)
    r = r - r.mean()
    print(f"   {name:9s} + r -= r.mean(): dVol/Vol   = {(lo + r).sum() / S - 1:+.6%}   "
          f"(page: -0.0050%)")
print(f"   low band unchanged by the operator    : max|lo - lowband| = "
      f"{np.abs(lo - low_band(h, 4)).max():.3e} m")
