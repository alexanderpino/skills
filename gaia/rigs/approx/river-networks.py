#!/usr/bin/env python3
"""What the authored-carve recommendation COSTS, on this container.

river-networks.md states how good the carve recommendation is (the monotone-fix table:
289 of 899 segments uphill, 32.1%, removed at 107.9 m mean extra excavation, on a path
traced along a valley with +-3 cells of jitter it is 4 of 71, 5.6%). Those geometry
figures are NOT re-measured here -- they belong to w4/carve_monotone.py, registered in
gaia/registers/pseudocode-execution.tsv:195, and that script is not on disk. This script
measures only the MACHINE cost of the same two steps, so the page can carry the pair.

WHAT THE RIG IS: CPython + numpy, single-threaded, on a shared container.
WHAT IT IS NOT: a GPU frame cost, and not a shipping bake time. The carve here is a
plain per-sample numpy stamp, not a production carver. Absolute milliseconds on a
shared container drift with load; the RATIO of the two steps is the load-proof figure
and is what the document prints as its headline. Memory is exact arithmetic, not a
timing, and does not drift at all.

Usage: python3 river-networks.py
"""
import time
import numpy as np

SEED = 20260914
REPS = 5                 # outer repeats, so the spread is visible
N_SAMPLES = 899          # the path length carve_monotone.py reports (289 of 899)
GRID = 512               # the terrain carve_monotone.py ran on
RADIUS = 8.0             # carve support radius in cells
DEPTH = 4.0              # the 4 m channel the document's table asks for


def make_path(rng, n, grid):
    """A sine path drawn across the grain, the shape the table's first row describes."""
    t = np.linspace(0.0, 1.0, n)
    x = 8.0 + t * (grid - 17.0)
    y = grid / 2.0 + (grid / 5.0) * np.sin(2.0 * np.pi * 3.0 * t)
    return x, y


def make_terrain(rng, grid):
    """Ridged-ish fractal dome, float32, 170 m of relief -- shape only, not the original."""
    h = np.zeros((grid, grid), dtype=np.float32)
    for octave in range(6):
        f = 2 ** octave
        small = rng.standard_normal((f + 1, f + 1)).astype(np.float32)
        yi = np.linspace(0, f, grid)
        xi = np.linspace(0, f, grid)
        y0 = np.clip(np.floor(yi).astype(int), 0, f - 1)
        x0 = np.clip(np.floor(xi).astype(int), 0, f - 1)
        ty = (yi - y0)[:, None]
        tx = (xi - x0)[None, :]
        a = small[np.ix_(y0, x0)]
        b = small[np.ix_(y0, x0 + 1)]
        c = small[np.ix_(y0 + 1, x0)]
        d = small[np.ix_(y0 + 1, x0 + 1)]
        h += ((a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty) / (2 ** octave)
    h -= h.min()
    h *= np.float32(170.0 / h.max())
    return h


def monotone_downstream(bed):
    """The fix peytavie2019 5.1 states: propagate heights downwards. One pass, O(n)."""
    return np.minimum.accumulate(bed)


def monotone_downstream_eps(bed, eps):
    """Same pass with the failure table's epsilon slope: accumulate over bed + eps*i.

    bed'[i] = min_{j<=i}(bed[j] + eps*j) - eps*i, so bed'[i] - bed'[i+1] >= eps and
    bed'[i] <= bed[i] (take j = i). Checked numerically in main().
    """
    i = np.arange(bed.size, dtype=bed.dtype)
    return np.minimum.accumulate(bed + eps * i) - eps * i


def carve(h, x, y, bed, radius, depth):
    """h(p) = u_z(p) + delta(d(p)), stamped per sample, min over samples (peytavie2019 5.2)."""
    grid = h.shape[0]
    out = h.copy()
    r = int(np.ceil(radius))
    for i in range(x.size):
        xi, yi = x[i], y[i]
        x0, x1 = max(0, int(xi) - r), min(grid, int(xi) + r + 1)
        y0, y1 = max(0, int(yi) - r), min(grid, int(yi) + r + 1)
        gy, gx = np.mgrid[y0:y1, x0:x1]
        d2 = (gx - xi) ** 2 + (gy - yi) ** 2
        inside = d2 < radius * radius
        # stored 1-D profile delta(d): parabolic, full depth on the centreline
        delta = -depth * (1.0 - d2 / (radius * radius))
        cand = bed[i] + delta
        block = out[y0:y1, x0:x1]
        np.minimum(block, cand.astype(np.float32), out=block, where=inside)
    return out


def main():
    rng = np.random.default_rng(SEED)
    h = make_terrain(rng, GRID)
    x, y = make_path(rng, N_SAMPLES, GRID)
    sampled = h[np.clip(y.astype(int), 0, GRID - 1), np.clip(x.astype(int), 0, GRID - 1)]
    sampled = sampled.astype(np.float64) - DEPTH

    print(f"rig: CPython + numpy {np.__version__}, single thread, shared container")
    print(f"seed {SEED}   grid {GRID}x{GRID}   path {N_SAMPLES} samples   "
          f"radius {RADIUS} cells   depth {DEPTH} m")
    print(f"terrain relief {float(h.max() - h.min()):.1f} m")
    print()

    # correctness first: the pass must actually leave a monotone bed
    bed = monotone_downstream(sampled)
    uphill_before = int(np.sum(np.diff(sampled) > 0))
    uphill_after = int(np.sum(np.diff(bed) > 0))
    print(f"uphill segments before fix {uphill_before} of {N_SAMPLES - 1}, after fix {uphill_after}")
    print("  (this rig's own terrain, NOT a re-measurement of carve_monotone.py's 289 of 899)")

    eps = 1e-3
    bed_eps = monotone_downstream_eps(sampled, eps)
    drops = -np.diff(bed_eps)
    print(f"epsilon variant (bed + eps*i, eps = {eps}): min drop per segment "
          f"{drops.min():.2e} >= eps: {bool(drops.min() >= eps * (1 - 1e-9))}; "
          f"never above input: {bool(np.all(bed_eps <= sampled + 1e-9))}")
    print()

    mono_ms, mono_eps_ms, carve_ms = [], [], []
    for rep in range(REPS):
        t0 = time.perf_counter()
        for _ in range(200):
            monotone_downstream(sampled)
        t1 = time.perf_counter()
        mono_ms.append((t1 - t0) / 200 * 1e3)

        t0 = time.perf_counter()
        for _ in range(200):
            monotone_downstream_eps(sampled, eps)
        t1 = time.perf_counter()
        mono_eps_ms.append((t1 - t0) / 200 * 1e3)

        t0 = time.perf_counter()
        carve(h, x, y, bed, RADIUS, DEPTH)
        t1 = time.perf_counter()
        carve_ms.append((t1 - t0) * 1e3)
        print(f"run {rep + 1}: monotone pass {mono_ms[-1] * 1e3:8.1f} us   "
              f"+eps {mono_eps_ms[-1] * 1e3:8.1f} us   "
              f"carve stamp {carve_ms[-1]:7.2f} ms   ratio 1 : {carve_ms[-1] / mono_ms[-1]:.0f}")

    mono = float(np.median(mono_ms))
    cv = float(np.median(carve_ms))
    print()
    print(f"median monotone +eps  {float(np.median(mono_eps_ms)) * 1e3:.1f} us")
    print(f"median monotone pass  {mono * 1e3:.1f} us   "
          f"(spread {min(mono_ms) * 1e3:.1f}-{max(mono_ms) * 1e3:.1f} us, "
          f"{(max(mono_ms) - min(mono_ms)) / mono * 100:.0f}% of median)")
    print(f"median carve stamp    {cv:.2f} ms   "
          f"(spread {min(carve_ms):.2f}-{max(carve_ms):.2f} ms, "
          f"{(max(carve_ms) - min(carve_ms)) / cv * 100:.0f}% of median)")
    print(f"median ratio          carve is {cv / mono:.0f}x the monotone pass")
    print(f"ratio spread          {min(c / m for c, m in zip(carve_ms, mono_ms)):.0f}x - "
          f"{max(c / m for c, m in zip(carve_ms, mono_ms)):.0f}x")
    print()

    # memory: exact arithmetic, no timing, does not drift
    print("memory (float32 heightfield, exact arithmetic):")
    print(f"  bytes per cell {h.dtype.itemsize}")
    for g in (512, 1024, 2048, 4096):
        print(f"  {g}x{g}: {g * g * 4 / 1e6:8.2f} MB")
    edge_bytes = 4 * 4 + 8 * 2          # discharge,width,type,slope + two node ids
    print(f"  authored graph, (discharge,width,type) + endpoints per edge: ~{edge_bytes} bytes/edge; "
          f"a 10,000-edge network is {10000 * edge_bytes / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
