#!/usr/bin/env python3
"""What a floe mask costs to build and to hold resident.

Partner measurement for gaia/references/sea-ice.md, whose stated ERROR half is the
published exponent target `m = -1.79 +- 0.08` (denton2022, already on the page and in
registers/pseudocode-execution.tsv row 202). This rig prices the COST half only. It
does NOT re-measure the exponent -- the negative result about Poisson-Voronoi is
already recorded and is not touched here.

RIG: CPython + numpy on a shared 4-core container. This is an AUTHORING-TIME bake
cost measured on a CPU. It is NOT a GPU frame cost and must never be printed as one.
Absolute milliseconds on a shared container drift with load; the RATIO between the two
routes does not, so the ratio is the figure to carry.

Two routes over the same 1024^2 periodic grid:
  A  the recipe sea-ice.md REJECTS: scatter N Poisson seeds, jump-flood, call the
     cells floes.
  B  the recipe sea-ice.md RECOMMENDS: inverse-transform sample N floe diameters from
     a truncated power law between explicit p_min and p_max, place them as discs
     largest-first, then jump-flood ONLY to close the gaps into the space-filling
     lead network.

Usage:  python3 sea-ice.py [--size 1024] [--repeats 5] [--seed 20260914]
"""
import argparse, time, sys
import numpy as np

# ---------------------------------------------------------------- jump flooding

def jfa(label, sy, sx, size):
    """Periodic jump flood. label int32 (-1 = unassigned), sy/sx int16 seed coords.

    Propagates the nearest SEED POSITION, not the distance -- the mechanism
    mask-operators.md describes. Returns the filled label array.
    """
    H = W = size
    yy = np.arange(H, dtype=np.int32)[:, None]
    xx = np.arange(W, dtype=np.int32)[None, :]

    def d2(py, px):
        dy = np.abs(yy - py.astype(np.int32)); np.minimum(dy, H - dy, out=dy)
        dx = np.abs(xx - px.astype(np.int32)); np.minimum(dx, W - dx, out=dx)
        return dy * dy + dx * dx

    best = np.where(label >= 0, d2(sy, sx), np.int32(1 << 30)).astype(np.int32)
    step = size // 2
    while step >= 1:
        for dy in (-step, 0, step):
            for dx in (-step, 0, step):
                if dy == 0 and dx == 0:
                    continue
                cl = np.roll(label, (dy, dx), axis=(0, 1))
                cy = np.roll(sy, (dy, dx), axis=(0, 1))
                cx = np.roll(sx, (dy, dx), axis=(0, 1))
                cand = d2(cy, cx)
                take = (cl >= 0) & (cand < best)
                if take.any():
                    label = np.where(take, cl, label)
                    sy = np.where(take, cy, sy)
                    sx = np.where(take, cx, sx)
                    best = np.where(take, cand, best)
        step //= 2
    return label

# ---------------------------------------------------------------- the two routes

def route_a(size, n, rng):
    """Scatter N Poisson seeds, jump-flood, call the cells floes."""
    label = np.full((size, size), -1, dtype=np.int32)
    sy = np.zeros((size, size), dtype=np.int16)
    sx = np.zeros((size, size), dtype=np.int16)
    py = rng.integers(0, size, n); px = rng.integers(0, size, n)
    label[py, px] = np.arange(n, dtype=np.int32)
    sy[py, px] = py.astype(np.int16); sx[py, px] = px.astype(np.int16)
    return jfa(label, sy, sx, size)


def sample_sizes(n, m, p_min, p_max, rng):
    """Inverse transform from a truncated power law n(a) ~ a^m on [p_min, p_max].

    Areas, in cells. m is the noncumulative AREA slope, denton2022's convention.
    """
    e = m + 1.0
    u = rng.random(n)
    return (p_min**e + u * (p_max**e - p_min**e)) ** (1.0 / e)


def route_b(size, n, rng, m=-1.79, p_min=4.0, p_max=None):
    """Sample sizes from the distribution, place them, partition only for edges."""
    if p_max is None:
        p_max = 0.02 * size * size
    areas = sample_sizes(n, m, p_min, p_max, rng)
    radii = np.sqrt(areas / np.pi)
    order = np.argsort(-radii)                      # largest first
    label = np.full((size, size), -1, dtype=np.int32)
    sy = np.zeros((size, size), dtype=np.int16)
    sx = np.zeros((size, size), dtype=np.int16)
    cy = rng.integers(0, size, n); cx = rng.integers(0, size, n)
    yy = np.arange(size, dtype=np.int32)[:, None]
    xx = np.arange(size, dtype=np.int32)[None, :]
    for k in order:
        r = int(max(1, round(radii[k])))
        ys = (np.arange(cy[k] - r, cy[k] + r + 1) % size).astype(np.int32)
        xs = (np.arange(cx[k] - r, cx[k] + r + 1) % size).astype(np.int32)
        dy = np.minimum(np.abs(ys - cy[k]), size - np.abs(ys - cy[k]))[:, None]
        dx = np.minimum(np.abs(xs - cx[k]), size - np.abs(xs - cx[k]))[None, :]
        disc = (dy * dy + dx * dx) <= r * r
        sub = label[np.ix_(ys, xs)]
        free = disc & (sub < 0)
        sub[free] = k
        label[np.ix_(ys, xs)] = sub
        a = sy[np.ix_(ys, xs)]; b = sx[np.ix_(ys, xs)]
        a[free] = (np.broadcast_to(ys[:, None], free.shape)[free]).astype(np.int16)
        b[free] = (np.broadcast_to(xs[None, :], free.shape)[free]).astype(np.int16)
        sy[np.ix_(ys, xs)] = a; sx[np.ix_(ys, xs)] = b
    del yy, xx
    return jfa(label, sy, sx, size)

# ---------------------------------------------------------------- memory

def resident_bytes_per_cell(size, n_floes):
    """The artefact that survives the bake: one floe id per cell."""
    dt = np.uint16 if n_floes < 2**16 else np.uint32
    a = np.zeros((size, size), dtype=dt)
    return a.nbytes / (size * size), np.dtype(dt).name


def working_bytes_per_cell(size):
    """Peak jump-flood working set: label + two seed coords + best-distance."""
    tot = (np.zeros((size, size), np.int32).nbytes
           + 2 * np.zeros((size, size), np.int16).nbytes
           + np.zeros((size, size), np.int32).nbytes)
    return tot / (size * size)

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260914)
    ap.add_argument("--n", type=int, default=1000)
    a = ap.parse_args()
    S, N, R = a.size, a.n, a.repeats

    print(f"rig      CPython {sys.version.split()[0]}, numpy {np.__version__}, "
          f"shared 4-core x86_64 container")
    print(f"grid     {S}^2 periodic = {S*S} cells;  N = {N} floes;  seed = {a.seed}")
    print(f"WHAT THIS IS NOT: a GPU frame cost. This is a CPU authoring-time bake.\n")

    ta, tb = [], []
    for i in range(R):
        rng = np.random.default_rng(a.seed + i)
        t0 = time.perf_counter(); la = route_a(S, N, rng); t1 = time.perf_counter()
        rng = np.random.default_rng(a.seed + i)
        t2 = time.perf_counter(); lb = route_b(S, N, rng); t3 = time.perf_counter()
        ta.append((t1 - t0) * 1e3); tb.append((t3 - t2) * 1e3)
        print(f"  run {i}: A(partition-only) {ta[-1]:8.1f} ms   "
              f"B(sample+place+partition) {tb[-1]:8.1f} ms   "
              f"cells A {len(np.unique(la))}  B {len(np.unique(lb))}")

    ta = np.array(ta); tb = np.array(tb)
    med_a, med_b = float(np.median(ta)), float(np.median(tb))
    spread = lambda v: 100.0 * (v.max() - v.min()) / np.median(v)
    print(f"\nA  median {med_a:.0f} ms   min {ta.min():.0f}   max {ta.max():.0f}   "
          f"spread {spread(ta):.0f}% of median")
    print(f"B  median {med_b:.0f} ms   min {tb.min():.0f}   max {tb.max():.0f}   "
          f"spread {spread(tb):.0f}% of median")
    print(f"RATIO B/A  median {med_b/med_a:.2f}x   "
          f"per-run {' '.join(f'{x:.2f}' for x in (tb/ta))}")

    # the sampling step alone
    rng = np.random.default_rng(a.seed)
    st = []
    for _ in range(9):
        t0 = time.perf_counter(); sample_sizes(N, -1.79, 4.0, 0.02*S*S, rng)
        st.append((time.perf_counter() - t0) * 1e6)
    print(f"\nsampling step alone (inverse transform, N = {N}): "
          f"median {np.median(st):.0f} us  -- {np.median(st)/1e3/med_b*100:.4f}% of route B (1 part in {med_b*1e3/np.median(st):.0f})")

    bpc, dt = resident_bytes_per_cell(S, N)
    wbpc = working_bytes_per_cell(S)
    print(f"\nresident floe-id mask   {bpc:.0f} bytes per cell ({dt}, N = {N} < 65536)")
    for k in (1024, 2048, 4096, 8192):
        print(f"    {k}^2  ->  {bpc*k*k/2**20:8.1f} MiB resident, "
              f"{wbpc*k*k/2**20:8.1f} MiB jump-flood working set")
    print(f"jump-flood working set  {wbpc:.0f} bytes per cell "
          f"(int32 label + 2 x int16 seed coords + int32 best-distance)")

    # the drift step, for contrast: one complex multiply per frame, not a per-cell pass
    t0 = time.perf_counter()
    for _ in range(100000):
        _ = 0.02 * complex(0.9063, -0.4226) * complex(7.0, 3.0) + complex(0.1, 0.0)
    dtf = (time.perf_counter() - t0) / 100000 * 1e6
    print(f"\nfree-drift step (U = a*exp(-i*th)*U_wind + U_current), per frame: "
          f"{dtf:.3f} us -- ONE complex multiply for the whole mask, not a per-cell pass")

if __name__ == "__main__":
    main()
