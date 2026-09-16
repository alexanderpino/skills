#!/usr/bin/env python3
"""Rebuild cost of the post-process mask form, on the field this document already uses.

Two halves, both for gaia/references/layering-filters-and-masks.md:

  GATE   reproduce the figure the document already prints at :118-120 (20 steps of a linear
         3x3 blur cropped at W=R differ from the full-domain reference by 2.60% of relief,
         reaching 18 cells inside the mask; exactly 0.000000000 at W = N*R). If this does not
         reproduce, the field construction below is not the document's and nothing else here
         may be quoted.

  COST   what a mask tweak costs in each of the two arrangements the `## Use this` block
         compares: (1) mask as a downstream node -- re-run the post-blend only; (2) mask as a
         port on the operator -- re-run N transport iterations, then blend. Plus the resident
         cost of the cached operator output that arrangement (1) requires.

RIG, and what it is NOT.  CPython 3.11 + NumPy on one core of an Intel Xeon @ 2.10GHz, float32
heightfields, single-threaded, wall clock via time.perf_counter over repeated runs (best-of
reported alongside the median).  It is NOT a GPU frame cost, NOT a shipping tool's erosion
kernel (a real thermal/hydraulic solver is far more work per iteration than the 8-neighbour
step below), and NOT a measurement of Gaea or Houdini.  The transferable quantity is the
RATIO between the two arrangements at a fixed field size; the absolute milliseconds belong to
this container and this operator only.

Usage:  python3 layering-filters-and-masks.py
Seed:   numpy default_rng(4), as the document's own harness rows record.
"""
import time

import numpy as np

RELIEF = 17.47          # the document's field is rescaled to this relief
SEED = 4
N_SMOOTH = 30           # box passes used to build the field


def build_field(n=128, dtype=np.float64):
    """default_rng(4) uniform noise, 30 edge-padded 3x3 box passes, rescaled to relief 17.47."""
    rng = np.random.default_rng(SEED)
    h = rng.random((n, n))
    for _ in range(N_SMOOTH):
        h = box3(h)
    h = h - h.min()
    h = h * (RELIEF / h.max())
    return h.astype(dtype)


def box3(a):
    p = np.pad(a, 1, mode="edge")
    out = np.zeros_like(a)
    for dy in range(3):
        for dx in range(3):
            out = out + p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
    return out / 9.0


def left_half_mask(n, dtype=np.float64):
    m = np.zeros((n, n), dtype=dtype)
    m[:, : n // 2] = 1.0
    return m


# ---------------------------------------------------------------- GATE (reproduction)

def gate(verbose=True):
    n = 128
    h0 = build_field(n)
    m = left_half_mask(n)
    N, R = 20, 1

    ref = h0.copy()
    for _ in range(N):
        ref = box3(ref)
    r_ref = h0 + (ref - h0) * m

    rows = []
    for W in (R, 5, 18, 19, N * R):
        win = np.zeros((n, n), dtype=bool)
        win[:, : n // 2 + W] = True
        cur = h0.copy()
        for _ in range(N):
            t = box3(cur)
            cur = np.where(win, t, h0)
        r_c = h0 + (cur - h0) * m
        d = np.abs(r_ref - r_c)
        depth = 0
        cols = np.where(d.max(axis=0) > 1e-12)[0]
        if cols.size:
            depth = n // 2 - cols.min()
        rows.append((W, d.max(), 100.0 * d.max() / RELIEF, depth))

    if verbose:
        print("GATE  20 steps of a linear 3x3 blur, window dilated by W, exterior frozen")
        print("      reference = full domain then post-blend; binary left-half mask, R = 1")
        print(f"{'W':>4} {'max error':>14} {'% of relief':>12} {'cells inside mask':>18}")
        for W, e, pct, depth in rows:
            print(f"{W:>4} {e:>14.9f} {pct:>11.4f}% {depth:>18}")
    w1 = rows[0]
    ok = (abs(w1[1] - 0.454813) < 5e-6) and (abs(w1[2] - 2.6034) < 5e-4) and w1[3] == 18
    ok = ok and rows[-1][1] == 0.0
    if verbose:
        print(f"      GATE {'PASS' if ok else 'FAIL'}: document's 2.60% / 18 cells / exact-zero "
              f"at W = N*R reproduced\n")
    return ok


# ---------------------------------------------------------------- COST

def transport_step(h, rate=0.15, thresh=0.5):
    """Thermal-style: move rate*dh to any 8-neighbour more than thresh below. Edges clamped."""
    p = np.pad(h, 1, mode="edge")
    delta = np.zeros_like(h)
    gain = np.zeros((h.shape[0] + 2, h.shape[1] + 2), dtype=h.dtype)
    for dy in range(3):
        for dx in range(3):
            if dy == 1 and dx == 1:
                continue
            nb = p[dy:dy + h.shape[0], dx:dx + h.shape[1]]
            dh = h - nb
            move = np.where(dh > thresh, rate * dh, 0.0)
            delta -= move
            gain[dy:dy + h.shape[0], dx:dx + h.shape[1]] += move
    return h + delta + gain[1:-1, 1:-1]


def blend(h, fh, m):
    return h + (fh - h) * m


def timeit(fn, repeats=9):
    ts = []
    fn()                      # warm the allocator / caches
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    ts.sort()
    return ts[len(ts) // 2], ts[0]


def cost(sizes=(128, 1024), N=20):
    print("COST  a mask tweak, in each of the two arrangements `## Use this` compares")
    print("      float32, single core, median of 9 (best in brackets), milliseconds")
    print(f"{'field':>8} {'blend only':>22} {'N=%d transport + blend' % N:>26} {'ratio':>9}")
    out = {}
    for n in sizes:
        h = build_field(n, dtype=np.float32)
        m = left_half_mask(n, dtype=np.float32)
        fh = h.copy()
        for _ in range(N):
            fh = transport_step(fh).astype(np.float32)

        t_blend, b_blend = timeit(lambda: blend(h, fh, m))

        def full():
            cur = h
            for _ in range(N):
                cur = transport_step(cur)
            return blend(h, cur, m)

        t_full, b_full = timeit(full, repeats=5)
        t_iter, _ = timeit(lambda: transport_step(h), repeats=9)
        print(f"{n}^2".rjust(8)
              + f"{t_blend:>16.3f} [{b_blend:.3f}]".rjust(22)
              + f"{t_full:>18.1f} [{b_full:.1f}]".rjust(26)
              + f"{t_full / t_blend:>8.0f}x"
              + f"   ({t_iter:.2f} ms/iter)")
        out[n] = (t_blend, t_full, t_full / t_blend)
    print()
    return out


def resident():
    print("RESIDENT  the price of the reuse: arrangement (1) must KEEP the operator's output")
    print("          arithmetic on a stated dtype (float32 itemsize), not a benchmark")
    for n in (1024, 2048, 4096):
        a = np.zeros((n, n), dtype=np.float32)
        print(f"  {n}^2  itemsize {a.itemsize} bytes per cell   one cached field "
              f"{a.nbytes / 1e6:.0f} MB ({a.nbytes / 2**20:.0f} MiB)")
        del a
    print()


if __name__ == "__main__":
    ok = gate()
    cost()
    resident()
    print("GATE PASS" if ok else "GATE FAIL -- do not quote the cost figures above")
