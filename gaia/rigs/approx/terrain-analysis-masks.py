#!/usr/bin/env python3
"""Measurements for gaia/references/terrain-analysis-masks.md.

Two halves of the `approximation` pair for the quartic-fit curvature block:

  (1) ERROR  -- the Zevenbergen & Thorne 3x3 stencil printed in the document,
      against closed-form curvature on a Gaussian hill z = exp(-(x^2+y^2)/2),
      for which profile = f''(r), plan = f'(r)/r and plan/sqrt(p) = -1/r.
  (2) COST   -- wall time and materialised working set for that same block over
      a 4096^2 R32F tile, in NumPy on this container. This is a CPython/NumPy
      authoring-time number on one process. It is NOT a GPU frame cost and must
      never be printed as one.

Run: python3 terrain-analysis-masks.py
"""
import platform
import time

import numpy as np

np.seterr(invalid='ignore', divide='ignore')  # p -> 0 on the summit; masked out below

SEED = 20260910  # timing field only; the accuracy half is deterministic, no RNG


def curvature(z, L):
    """The document's block, verbatim, on the interior of z (rows north->south)."""
    Z1, Z2, Z3 = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    Z4, Z5, Z6 = z[1:-1, :-2], z[1:-1, 1:-1], z[1:-1, 2:]
    Z7, Z8, Z9 = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    D = ((Z4 + Z6) / 2 - Z5) / L**2
    E = ((Z2 + Z8) / 2 - Z5) / L**2
    F = (Z3 + Z7 - Z1 - Z9) / (4 * L**2)
    G = (Z6 - Z4) / (2 * L)
    H = (Z2 - Z8) / (2 * L)
    p = G * G + H * H
    profile = 2 * (D * G * G + F * G * H + E * H * H) / p
    plan = 2 * (D * H * H - F * G * H + E * G * G) / p
    return profile, plan, p, (D, E, F, G, H)


# ---------------------------------------------------------------- (1) ERROR
# Grid rows run north->south, so row index increasing means y DECREASING:
# that is the document's own +y-NORTH convention for H = (Z2 - Z8)/(2L).
def ring_error(L, rlo=0.5, rhi=3.0, half=4.0):
    n = int(round(half / L))
    ax = L * np.arange(-n, n + 1)
    X, Ynorth = np.meshgrid(ax, ax[::-1])          # row 0 is the north edge
    Z = np.exp(-(X**2 + Ynorth**2) / 2.0)
    prof, plan, p, _ = curvature(Z, L)
    x, y = X[1:-1, 1:-1], Ynorth[1:-1, 1:-1]
    r = np.hypot(x, y)
    m = (r >= rlo) & (r <= rhi)
    g = np.exp(-r**2 / 2.0)
    prof_ex = (r**2 - 1.0) * g                     # f''(r)
    plan_ex = -g                                   # f'(r)/r
    kc_ex = -1.0 / r                               # plan / sqrt(p) = contour curvature
    kc = plan / np.sqrt(p)
    # profile passes through zero at r = 1, so a relative error there is singular:
    # normalise the profile residual by the analytic peak |f''| on the same ring.
    scale = np.abs(prof_ex[m]).max()
    kc_err = np.abs(kc[m] - kc_ex[m]) / np.abs(kc_ex[m])
    j = int(np.argmax(kc_err))
    return {
        "L": L,
        "cells": int(m.sum()),
        "profile_norm": float(np.abs(prof[m] - prof_ex[m]).max() / scale),
        "plan_rel": float((np.abs(plan[m] - plan_ex[m]) / np.abs(plan_ex[m])).max()),
        "kc_rel": float(kc_err.max()),
        "kc_worst_r": float(r[m][j]),
    }


def point_digits(L, r0=1.3, half=4.0):
    """The document's own single-point test: plan/sqrt(p) against -1/r at r = 1.3,
    with (r0, 0) forced onto a grid node for every L."""
    n = int(round(half / L))
    off = L * np.arange(-n, n + 1)
    X, Ynorth = np.meshgrid(r0 + off, (0.0 + off)[::-1])
    Z = np.exp(-(X**2 + Ynorth**2) / 2.0)
    _, plan, p, _ = curvature(Z, L)
    kc = (plan / np.sqrt(p))[n - 1, n - 1]         # interior index of the node (r0, 0)
    rel = abs(kc - (-1.0 / r0)) / (1.0 / r0)
    return {"L": L, "kc": float(kc), "rel": float(rel),
            "sig_digits": float(-np.log10(rel))}


# ---------------------------------------------------------------- (2) COST
def cost(nside=4096, reps=5):
    rng = np.random.default_rng(SEED)
    z = rng.standard_normal((nside, nside), dtype=np.float32)
    z = np.cumsum(np.cumsum(z, 0), 1).astype(np.float32)   # smooth-ish, values irrelevant
    L = np.float32(1.0)
    curvature(z, L)                                        # warm the allocator
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        prof, plan, p, coef = curvature(z, L)
        ts.append((time.perf_counter() - t0) * 1e3)
        held = sum(a.nbytes for a in (prof, plan, p) + coef)   # the 8 named intermediates
        del prof, plan, p, coef
    cells = (nside - 2) ** 2
    # Materialised working set, MEASURED as the sum of nbytes of the eight named
    # intermediates (D E F G H p profile plan) still live at the end of the block,
    # plus the R32F input. Floor, not peak: the expressions allocate further
    # unnamed temporaries that are freed before this is read.
    per_cell = (held + z.nbytes) / cells
    return {"nside": nside, "ms_best": min(ts), "ms_med": float(np.median(ts)),
            "ms_all": [round(t, 1) for t in ts], "cells": cells,
            "bytes_per_cell": per_cell,
            "input_MB": z.nbytes / 1e6,
            "materialised_MB": (held + z.nbytes) / 1e6}


if __name__ == "__main__":
    print("rig:", platform.python_version(), "numpy", np.__version__,
          "|", platform.platform())
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    print("cpu:", line.split(":", 1)[1].strip())
                    break
    except OSError:
        pass
    print("seed:", SEED)
    print()
    print("-- ERROR: ring 0.5 <= r <= 3.0 on z = exp(-(x^2+y^2)/2)")
    prev = None
    for L in (0.4, 0.2, 0.1, 0.05, 0.025):
        d = ring_error(L)
        ratio = "" if prev is None else f"  (ratio {prev / d['kc_rel']:.3f})"
        print(f"  L={L:<6} cells={d['cells']:<7} "
              f"profile_max_abs/peak={d['profile_norm']:.6f}  "
              f"plan_max_rel={d['plan_rel']:.6f}  "
              f"plan/sqrt(p) vs -1/r max_rel={d['kc_rel']:.6f} "
              f"@ r={d['kc_worst_r']:.3f}{ratio}")
        prev = d["kc_rel"]
    print()
    print("-- ERROR: the document's own point test, plan/sqrt(p) vs -1/r at r = 1.3")
    for L in (0.4, 0.2, 0.1, 0.05, 0.025):
        d = point_digits(L)
        print(f"  L={L:<6} plan/sqrt(p)={d['kc']:+.8f}  rel={d['rel']:.3e}  "
              f"sig_digits={d['sig_digits']:.1f}")
    print()
    print("-- COST: the same block over a 4096^2 R32F tile, NumPy, one process")
    c = cost()
    print(f"  best {c['ms_best']:.1f} ms, median {c['ms_med']:.1f} ms, runs {c['ms_all']}")
    print(f"  input {c['input_MB']:.1f} MB; the 8 named intermediates + input = "
          f"{c['bytes_per_cell']:.1f} bytes per cell = {c['materialised_MB']:.0f} MB")
