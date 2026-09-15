"""What the recommended crater stamp costs, and a re-derivation of the errors already on the page.

Prices exactly the recommendation in gaia/references/impact-craters.md's `## Use this`:
one authored radial profile per crater, dimensions from Pike's two-branch morphometry with
the floor (keep whichever branch returns the smaller value), laid down in age order, oldest
first, into a float32 heightfield.

Per crater, one radial profile covering cavity, crest and blanket:
  D_r  rim-crest diameter (km), R = D_r/2 in metres
  depth below rim crest  = min(0.196*D^1.010, 1.044*D^0.301)  km   [pike1977, floored]
  rim height above plain = min(0.036*D^1.014, 0.236*D^0.399)  km   [pike1977, floored]
  rim-flank width        = min(0.257*D^1.011, 0.467*D^0.836)  km   [pike1977, floored]
  ejecta at the rim  T   = 0.14 * R**0.77  m                       [austin2024]
  blanket            t(r)= T * (r/R)**-2.8, r >= R, out to 4R      [austin2024]
  cavity (r <= R) REPLACES the surface; rim bulge and blanket ADD to it.
Each crater is rasterised into its own bounding box (+-4R, clipped), never the whole grid.

Rig: CPython + NumPy on one shared x86-64 container core. It is a CPU authoring-pass floor.
It is NOT a frame cost and NOT a GPU number. Absolute milliseconds on a shared container drift
with load; the ratios (law vs raster) do not, which is why the page quotes the ratio.

Run:  python3 impact-craters.py          (deterministic; seed 20260914)
"""
from __future__ import annotations

import statistics
import sys
import time

import numpy as np

SEED = 20260914
N_CRATERS = 1000
GRID = 2048
DOMAIN_M = 40_000.0          # 40 km across 2048 cells -> 19.53 m cells
CELL = DOMAIN_M / GRID
D_MIN_KM, D_MAX_KM = 0.05, 8.0
ETA = 3.0                    # cumulative production slope, small end [minton2019]
REPEATS = 5


# ---------------------------------------------------------------- morphometry (floored)
def floored_profile(d_km: float) -> tuple[float, float, float]:
    """Depth below rim crest, rim height, rim-flank width -- km, each floored at its own fit."""
    depth = min(0.196 * d_km ** 1.010, 1.044 * d_km ** 0.301)
    rim_h = min(0.036 * d_km ** 1.014, 0.236 * d_km ** 0.399)
    rim_w = min(0.257 * d_km ** 1.011, 0.467 * d_km ** 0.836)
    return depth, rim_h, rim_w


def constant_profile(d_km: float) -> tuple[float, float, float]:
    """The shortcut the page offers for the simple branch: D/5, 0.18*depth, 0.26*D."""
    depth = d_km / 5.0
    return depth, 0.18 * depth, 0.26 * d_km


# ---------------------------------------------------------------- the error half, re-derived
def error_figures() -> dict[str, float]:
    """The two figures already printed on the page, recomputed from the coefficients."""
    d = np.linspace(0.1, 15.0, 200_001)
    ratio = 0.196 * d ** 1.010 / d                      # depth / diameter, simple branch
    rim_over_depth = (0.036 * d ** 1.014) / (0.196 * d ** 1.010)
    exps = np.array([1.010, 1.014, 1.011])
    return {
        "exponent_max_dev_pct": float(np.max(np.abs(exps - 1.0)) * 100.0),
        "dD_lo": float(ratio.min()), "dD_hi": float(ratio.max()),
        "dD_spread_pct": float((ratio.max() / ratio.min() - 1.0) * 100.0),
        "rim_lo": float(rim_over_depth.min()), "rim_hi": float(rim_over_depth.max()),
        "intercept_ratio": 0.036 / 0.196,
    }


# ---------------------------------------------------------------- the field
def sample_field(rng: np.random.Generator, n: int, d_min: float) -> tuple[np.ndarray, ...]:
    """Inverse-transform sample of a truncated cumulative power law N(>D) ~ D^-eta."""
    u = rng.random(n)
    a, b = d_min ** -ETA, D_MAX_KM ** -ETA
    d = (a + u * (b - a)) ** (-1.0 / ETA)
    x = rng.random(n) * DOMAIN_M
    y = rng.random(n) * DOMAIN_M
    age = rng.random(n)
    order = np.argsort(-age)                             # oldest first
    return d[order], x[order], y[order]


def stamp_field(d_km: np.ndarray, xs: np.ndarray, ys: np.ndarray,
                grid: np.ndarray) -> None:
    """Age-ordered stamping. Cavity replaces; rim bulge and ejecta blanket add."""
    n = grid.shape[0]
    for d, cx, cy in zip(d_km, xs, ys):
        depth_km, rim_km, rimw_km = floored_profile(float(d))
        r_m = 500.0 * float(d)                           # crater radius, metres
        d_plain = (depth_km - rim_km) * 1000.0           # cavity depth below the pre-impact plain
        rim_m, rimw_m = rim_km * 1000.0, rimw_km * 1000.0
        t_rim = 0.14 * r_m ** 0.77                       # ejecta thickness at the rim
        reach = 4.0 * r_m                                # continuous blanket, 3-4 radii
        i0 = max(0, int((cy - reach) / CELL)); i1 = min(n, int((cy + reach) / CELL) + 1)
        j0 = max(0, int((cx - reach) / CELL)); j1 = min(n, int((cx + reach) / CELL) + 1)
        if i1 <= i0 or j1 <= j0:
            continue
        yy = (np.arange(i0, i1) + 0.5) * CELL - cy
        xx = (np.arange(j0, j1) + 0.5) * CELL - cx
        rr = np.hypot(yy[:, None], xx[None, :])
        sub = grid[i0:i1, j0:j1]
        inside = rr <= r_m
        q = np.clip(rr / r_m, 1e-6, None)
        cavity = rim_m * q ** 4 - d_plain * (1.0 - np.minimum(q, 1.0) ** 2)
        sub[inside] = cavity[inside]                     # the cavity REPLACES
        out = ~inside & (rr <= reach)
        uplift = (rim_m - t_rim) * np.exp(-(((rr - r_m) / max(rimw_m, CELL)) ** 2))
        blanket = t_rim * q ** -2.8
        sub[out] += (np.maximum(uplift, 0.0) + blanket)[out]   # the deposit ADDS


def time_stamp() -> tuple[float, float, np.ndarray]:
    rng = np.random.default_rng(SEED)
    d, x, y = sample_field(rng, N_CRATERS, D_MIN_KM)
    grid = np.zeros((GRID, GRID), dtype=np.float32)
    t0 = time.perf_counter()
    stamp_field(d, x, y, grid)
    return (time.perf_counter() - t0) * 1000.0, float(grid.nbytes), grid


def time_one(d_km: float, reps: int = 40) -> float:
    """Milliseconds to stamp ONE crater of this diameter into a resident grid."""
    grid = np.zeros((GRID, GRID), dtype=np.float32)
    d = np.array([d_km]); x = np.array([DOMAIN_M / 2]); y = np.array([DOMAIN_M / 2])
    stamp_field(d, x, y, grid)                       # warm
    t0 = time.perf_counter()
    for _ in range(reps):
        stamp_field(d, x, y, grid)
    return (time.perf_counter() - t0) * 1000.0 / reps


def time_law(fn, d_km: np.ndarray, reps: int = 200) -> float:
    """Microseconds per crater for the closed-form dimensions alone."""
    vals = [float(v) for v in d_km]
    t0 = time.perf_counter()
    for _ in range(reps):
        for v in vals:
            fn(v)
    return (time.perf_counter() - t0) * 1e6 / (reps * len(vals))


def main() -> int:
    print(f"python {sys.version.split()[0]}  numpy {np.__version__}  seed {SEED}")
    print(f"grid {GRID}x{GRID} float32, domain {DOMAIN_M/1000:.0f} km, cell {CELL:.2f} m, "
          f"{N_CRATERS} craters, D in [{D_MIN_KM}, {D_MAX_KM}] km, eta={ETA}")

    e = error_figures()
    print("\n-- error half, re-derived from the coefficients on the page --")
    print(f"simple-branch exponents 1.010/1.014/1.011: max deviation from 1.0 = "
          f"{e['exponent_max_dev_pct']:.2f}%")
    print(f"depth/diameter over D in [0.1,15] km: {e['dD_lo']:.4f} .. {e['dD_hi']:.4f}  "
          f"spread {e['dD_spread_pct']:.1f}%")
    print(f"rim/depth over the same range: {e['rim_lo']:.4f} .. {e['rim_hi']:.4f}  "
          f"vs intercept ratio {e['intercept_ratio']:.4f}")

    rng = np.random.default_rng(SEED)
    d, _, _ = sample_field(rng, N_CRATERS, D_MIN_KM)
    law_us = [time_law(floored_profile, d[:50]) for _ in range(REPEATS)]
    shortcut_us = [time_law(constant_profile, d[:50]) for _ in range(REPEATS)]

    stamps = []
    for _ in range(REPEATS + 2):                  # first two are warm-up: first touch of a
        ms, nbytes, grid = time_stamp()           # fresh 16 MiB array costs page faults
        stamps.append(ms)
    warm, stamps = stamps[:2], stamps[2:]
    touched = float(np.count_nonzero(grid)) / grid.size

    med_stamp = statistics.median(stamps)
    med_law = statistics.median(law_us)
    med_short = statistics.median(shortcut_us)
    print("\n-- cost half, measured here --")
    print(f"stamp, {N_CRATERS} craters: median {med_stamp:.1f} ms   runs "
          f"{' '.join(f'{s:.1f}' for s in stamps)}   (discarded warm-up "
          f"{' '.join(f'{w:.1f}' for w in warm)} ms, first touch of the array)")
    print(f"stamp, per crater: {med_stamp / N_CRATERS * 1000:.1f} us")
    print(f"sanity: {100 * touched:.1f}% of cells written, relief "
          f"{grid.min():.1f} .. {grid.max():.1f} m")
    print(f"floored two-branch dimensions, per crater: median {med_law:.3f} us   runs "
          f"{' '.join(f'{v:.3f}' for v in law_us)}")
    print(f"constant-ratio shortcut,        per crater: median {med_short:.3f} us   runs "
          f"{' '.join(f'{v:.3f}' for v in shortcut_us)}")
    for dd in (0.05, 0.1, 0.5, 2.0, 8.0):
        one = time_one(dd)
        print(f"one crater, D = {dd:>4} km: {one * 1000:8.1f} us   "
              f"(dimensions are {100 * (med_law * 1e-3) / one:.2f}% of it)")
    print(f"law / raster share: {100.0 * (med_law * 1e-3) / (med_stamp / N_CRATERS):.4f}% "
          f"of the per-crater stamp")
    print(f"law - shortcut, per crater: {med_law - med_short:.3f} us  -> "
          f"{100.0 * ((med_law - med_short) * 1e-3) / (med_stamp / N_CRATERS):.4f}% "
          f"of the per-crater stamp saved by approximating")
    rec = (d.nbytes + d.nbytes + d.nbytes + d.nbytes) / len(d)   # D, x, y, age: 4 x float64
    print(f"crater list: {rec:.0f} bytes per crater (D, x, y, age as float64), "
          f"{rec * N_CRATERS / 1000:.0f} KB for {N_CRATERS} craters -- no per-cell state")
    print(f"heightfield: {nbytes / GRID**2:.0f} bytes per cell, {nbytes / 2**20:.1f} MiB at "
          f"{GRID}^2 ({nbytes / 1e6:.1f} MB), {4 * 4096**2 / 2**20:.1f} MiB at 4096^2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
