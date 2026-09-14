#!/usr/bin/env python3
"""Measure valley spacing against D and K in dh/dt = U - K*A^m*S^n + D*lap(h).

WHY: stream-power.md's only stated reason to keep the diffusion term is "raise D to widen
valley spacing, raise K to tighten it" (:174-175). Nothing in this corpus had measured
spacing -- an earlier check (RI-9) looked at what a large D does to the slope-area fit, which
is a different question. This rig measures the spacing itself.

WHAT THIS IS: an explicit-diffusion / implicit-fluvial landscape evolution model integrated to
near-steady-state on a tilted plate draining to one edge, with valley spacing read off
cross-slope transects as domain width / number of valleys.

WHAT THIS IS NOT: a claim about real landscapes, and not a reproduction of any published
experiment. It tests whether THIS equation, as this document recommends running it, behaves the
way this document says it does.

Usage: python3 stream-power.py [--n 96] [--steps 1200] [--seed 20260914]
"""
import argparse, math, sys
import numpy as np

def receivers_and_area(h, dx):
    """D8 steepest descent; drainage area by accumulation in descending-elevation order."""
    ny, nx = h.shape
    big = np.full((ny + 2, nx + 2), np.inf)
    big[1:-1, 1:-1] = h
    best = np.zeros_like(h, dtype=np.int64) - 1
    bestslope = np.zeros_like(h)
    offs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    for k, (dy, dxo) in enumerate(offs):
        nb = big[1+dy:1+dy+ny, 1+dxo:1+dxo+nx]
        dist = dx * (math.sqrt(2) if dy and dxo else 1.0)
        slope = (h - nb) / dist
        take = slope > bestslope
        bestslope = np.where(take, slope, bestslope)
        best = np.where(take, k, best)
    area = np.full(h.shape, dx * dx)
    order = np.argsort(h, axis=None)[::-1]           # high to low
    ys, xs = np.unravel_index(order, h.shape)
    bflat, aflat = best.ravel(), area.ravel()
    idx = order
    for t in range(idx.size):
        i = idx[t]; k = bflat[i]
        if k < 0: continue                            # pit or edge: terminal
        y, x = ys[t], xs[t]
        dy, dxo = offs[k]
        yy, xx = y + dy, x + dxo
        if 0 <= yy < h.shape[0] and 0 <= xx < h.shape[1]:
            aflat[yy * h.shape[1] + xx] += aflat[i]
    return best, bestslope, area, offs

def valley_spacing(h, dx, outlet_rows=(0,)):
    """Valleys per cross-slope transect, averaged over the interior."""
    ny, nx = h.shape
    counts = []
    for r in range(ny // 4, 3 * ny // 4):             # interior rows only
        row = h[r]
        # a valley = a strict local minimum across the transect
        mins = (row[1:-1] < row[:-2]) & (row[1:-1] < row[2:])
        c = int(mins.sum())
        if c: counts.append(c)
    if not counts: return float('nan'), 0
    mean_c = float(np.mean(counts))
    return (nx * dx) / mean_c, mean_c

def run(D, K, n=96, steps=1200, seed=20260914, m=0.5, nexp=1.0, U=1e-3, dx=100.0, verbose=False):
    rng = np.random.default_rng(seed)
    h = rng.random((n, n)) * 1.0                      # small noise, flat plate
    h[0, :] = 0.0                                     # outlet edge
    dt_diff = 0.2 * dx * dx / max(D, 1e-12)
    dt = min(1000.0, dt_diff)
    for s in range(steps):
        best, slope, area, offs = receivers_and_area(h, dx)
        # implicit-in-h fluvial term (Braun & Willett style, applied pointwise)
        f = K * dt * np.power(area, m) / dx
        # receiver elevation
        ys, xs = np.mgrid[0:n, 0:n]
        dyv = np.zeros_like(h); dxv = np.zeros_like(h)
        for k, (dy, dxo) in enumerate(offs):
            sel = best == k
            dyv[sel] = dy; dxv[sel] = dxo
        ry = np.clip(ys + dyv.astype(int), 0, n - 1)
        rx = np.clip(xs + dxv.astype(int), 0, n - 1)
        hr = h[ry, rx]
        newh = np.where(best >= 0, (h + f * hr) / (1.0 + f), h)
        newh = np.maximum(newh, hr)                   # never below the receiver
        # explicit diffusion
        lap = (np.roll(newh,1,0) + np.roll(newh,-1,0) + np.roll(newh,1,1) + np.roll(newh,-1,1) - 4*newh) / (dx*dx)
        newh = newh + dt * (U + D * lap)
        newh[0, :] = 0.0                              # pinned outlet
        newh[-1, :] = newh[-2, :]                     # no-flux far edge
        h = newh
    lam, vc = valley_spacing(h, dx)
    pits = int(((best < 0)[1:-1,1:-1]).sum())
    return lam, vc, pits, h

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=96)
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=20260914)
    a = ap.parse_args()
    print(f"rig: numpy {np.__version__}, CPython {sys.version.split()[0]}; "
          f"{a.n}x{a.n}, {a.steps} steps, seed {a.seed}, m=0.5 n=1 U=1e-3 dx=100")
    print("   dh/dt = U - K*A^m*S^n + D*lap(h);  spacing = width / mean local minima per transect\n")
    K0 = 3e-5
    print(f"{'sweep':<8}{'D':>10}{'K':>10}{'spacing m':>12}{'valleys':>9}{'pits':>7}")
    Ds, Dlam, Ks, Klam = [], [], [], []
    for D in (0.0, 0.01, 0.03, 0.1, 0.3, 1.0):
        lam, vc, pits, _ = run(D, K0, a.n, a.steps, a.seed)
        Ds.append(D); Dlam.append(lam)
        print(f"{'D':<8}{D:>10.3g}{K0:>10.1e}{lam:>12.1f}{vc:>9.2f}{pits:>7}")
    print()
    D0 = 0.1
    for K in (1e-5, 3e-5, 1e-4, 3e-4, 1e-3):
        lam, vc, pits, _ = run(D0, K, a.n, a.steps, a.seed)
        Ks.append(K); Klam.append(lam)
        print(f"{'K':<8}{D0:>10.3g}{K:>10.1e}{lam:>12.1f}{vc:>9.2f}{pits:>7}")
    print()
    import numpy as _np
    dd = [(d, l) for d, l in zip(Ds, Dlam) if d > 0]
    if len(dd) > 1:
        sl = _np.polyfit(_np.log([d for d, _ in dd]), _np.log([l for _, l in dd]), 1)[0]
        print(f"  spacing ~ D^{sl:+.3f}   over D = {dd[0][0]:g}..{dd[-1][0]:g} at fixed K")
    if len(Ks) > 1:
        sl = _np.polyfit(_np.log(Ks), _np.log(Klam), 1)[0]
        print(f"  spacing ~ K^{sl:+.3f}   over K = {Ks[0]:g}..{Ks[-1]:g} at fixed D")
    print("\n  the page's claim -- raise D to WIDEN spacing, raise K to TIGHTEN it -- is")
    print("  a statement about the SIGN of those two exponents.")
