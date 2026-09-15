#!/usr/bin/env python3
"""Measure the machine cost of the per-cell cliff-threshold operator recommended in
gaia/references/coastal-erosion.md, against the uniform-mean-rate operator it replaces.

WHAT THIS IS: a NumPy/CPython measurement on this container's CPU, of (1) the resident
storage of a per-cell resistance field F_R, and (2) the wall time of one vectorised
threshold step over the whole grid.

WHAT THIS IS NOT: a GPU frame cost, a shipped authoring tool's cost, or a measurement of
[shadrick2022]'s own code. It is the arithmetic the operator has to do, timed once, so a
reader can tell whether per-cell resistance is affordable at all -- not a benchmark of any
particular implementation.

Usage: python3 coastal-erosion.py [--n 4096] [--reps 30] [--seed 20260910]
"""
import argparse, platform, sys, time
import numpy as np


def build(n, seed):
    rng = np.random.default_rng(seed)
    # per-cell resistance (lithology), per-cell platform width (distance seaward of the
    # cliff foot), and the elevation the notch cuts. All float32 -- the storage claim.
    F_R = rng.uniform(0.4, 1.6, size=(n, n)).astype(np.float32)
    width = rng.uniform(0.0, 60.0, size=(n, n)).astype(np.float32)
    z = rng.uniform(-2.0, 30.0, size=(n, n)).astype(np.float32)
    return F_R, width, z


def threshold_step(F_R, width, z, H, decay, dz, weather):
    """One step of the coupled rock-coast operator, vectorised.
    assailing force = H*exp(-decay*width); erode only where it exceeds F_R;
    weathering lowers F_R rather than eroding."""
    force = H * np.exp(-decay * width)
    hit = force > F_R
    z -= dz * hit                      # notch cut only where the threshold is crossed
    width += dz * hit                  # the platform widens by what was cut
    F_R -= weather                     # weathering lowers resistance everywhere
    np.maximum(F_R, 0.05, out=F_R)
    return int(hit.sum())


def uniform_step(z, rate):
    """The operator it replaces: every cell retreats by the mean rate. No state."""
    z -= rate


def timeit(fn, reps):
    fn()                                # warm-up, excluded
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    ts.sort()
    return ts[len(ts) // 2], ts[0], ts[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20260910)
    a = ap.parse_args()

    F_R, width, z = build(a.n, a.seed)
    cells = a.n * a.n

    print(f"rig      : NumPy {np.__version__}, CPython {sys.version.split()[0]}, "
          f"{platform.machine()} CPU. NOT a GPU, NOT a frame cost.")
    print(f"grid     : {a.n} x {a.n} = {cells} cells, seed {a.seed}, reps {a.reps}")

    # (1) storage
    print(f"F_R dtype: {F_R.dtype}, itemsize {F_R.dtype.itemsize} bytes per cell")
    print(f"F_R field: {F_R.nbytes} bytes = {F_R.nbytes / 2**20:.1f} MiB at {a.n}^2")
    print(f"           float64 would be {F_R.astype(np.float64).nbytes / 2**20:.1f} MiB; "
          f"uint8 {F_R.astype(np.uint8).nbytes / 2**20:.1f} MiB")
    print(f"uniform-mean-rate operator resident state: 0 bytes per cell "
          f"(one scalar for the whole field)")

    # (2) step cost
    med, lo, hi = timeit(
        lambda: threshold_step(F_R, width, z, 1.0, 0.05, 0.01, 1e-5), a.reps)
    print(f"threshold step: median {med:.1f} ms  (min {lo:.1f}, max {hi:.1f}) over {cells} cells")

    med_u, lo_u, hi_u = timeit(lambda: uniform_step(z, 0.058), a.reps)
    print(f"uniform  step: median {med_u:.1f} ms  (min {lo_u:.1f}, max {hi_u:.1f})")
    print(f"ratio        : {med / med_u:.1f}x")


if __name__ == "__main__":
    main()
