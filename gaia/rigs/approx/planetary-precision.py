#!/usr/bin/env python3
"""Measures the two halves of the `approximation` pair for gaia/references/planetary-precision.md.

ERROR half: the position error the document's prescription actually carries, against the
alternative it tells you to abandon.
  truth      = worldPos_f64 - cameraPos_f64                      (exact enough: f64 ULP at
                                                                  6.371e6 m is 9.3e-10 m)
  prescribed = float32(worldPos_f64 - cameraPos_f64)             ONE truncation, after the subtract
  absolute   = float32(worldPos_f64) - float32(cameraPos_f64)    truncate first, subtract in f32

COST half: wall time of the prescribed per-frame operation over N positions, on THIS machine,
in numpy. This is a CPython/numpy vectorised measurement of a CPU-side array transform. It is
NOT a GPU frame cost and NOT an engine's per-draw transform loop.

Run: python3 planetary-precision.py
"""
import platform
import time

import numpy as np

SEED = 20260910
N = 1_000_000
R = 6_371_000.0   # m, the radius the document's last ULP-table row uses
PATCH = 2_000.0   # m, half-extent of the near-field terrain patch around the camera

print(f"rig: {platform.python_version()} / numpy {np.__version__} / "
      f"{platform.machine()} / {platform.system()}")
try:
    with open("/proc/cpuinfo") as fh:
        for line in fh:
            if line.startswith("model name"):
                print("cpu:", line.split(":", 1)[1].strip())
                break
except OSError:
    pass
print(f"seed={SEED} N={N} R={R:.0f} m patch=+/-{PATCH:.0f} m")

# --- channel (a) check: the ULP table already printed in the document -----------------
print("\nULP table (exact float32 spacing, for cross-check against the document's table):")
for d in (1e3, 1e4, 1e5, 1e6, R):
    print(f"  {d:>10.0f} m  ulp = {float(np.spacing(np.float32(d))):.9g} m")

# --- error half -----------------------------------------------------------------------
rng = np.random.default_rng(SEED)
# camera on the surface, in a generic direction (no axis-aligned luck)
u = rng.normal(size=3)
cam = (u / np.linalg.norm(u)) * R
# vertices in a near-field patch around the camera
world = cam + rng.uniform(-PATCH, PATCH, size=(N, 3))

truth = world - cam                                        # f64
prescribed = (world - cam).astype(np.float32)              # subtract in f64, truncate once
absolute = world.astype(np.float32) - np.float32(cam)      # truncate first, subtract in f32

def report(name, got):
    err = np.linalg.norm(got.astype(np.float64) - truth, axis=1)
    print(f"  {name:<28} max {err.max():.6g} m   rms {np.sqrt((err**2).mean()):.6g} m")

print("\nposition error over the patch (Euclidean, metres):")
report("camera-relative (prescribed)", prescribed)
report("absolute float32", absolute)
print(f"  camera-relative max error in mm: "
      f"{np.linalg.norm(prescribed.astype(np.float64)-truth,axis=1).max()*1e3:.4g}")

# Why the absolute max is 0.398 m and not sqrt(3)*0.5: it is PER-AXIS spacing that bites, and
# only the largest component of this camera sits in the 0.5 m band. And part of the error is a
# rigid offset (the camera's own truncation), shared by every vertex, which does not wobble.
e = absolute.astype(np.float64) - truth
print("\n  qualifications on the absolute-float32 figure:")
print(f"    camera position (km):        {cam/1e3}")
print(f"    per-axis float32 ULP (m):    {[float(np.spacing(np.float32(abs(c)))) for c in cam]}")
print(f"    per-axis max |error| (m):    {np.abs(e).max(axis=0)}")
rigid = e.mean(axis=0)
print(f"    rigid offset, cam truncation (m): {rigid}  |{np.linalg.norm(rigid):.4g}| ")
print(f"    max error with rigid offset removed (differential/wobble, m): "
      f"{np.linalg.norm(e - rigid, axis=1).max():.6g}")

# --- cost half ------------------------------------------------------------------------
REPS = 9

def bench(arr, reps=REPS):
    best = float("inf")
    for _ in range(reps):
        t0 = time.perf_counter()
        _out = (arr - cam).astype(np.float32)
        t1 = time.perf_counter()
        best = min(best, t1 - t0)
    return best

print("\ncost, prescribed per-frame op (pos_f64 - cam_f64).astype(float32), "
      f"best of {REPS}:")
for n in (4_096, 16_384, N):
    arr = world[:n]
    t = bench(arr, 200 if n <= 16_384 else REPS)
    print(f"  {n:>9} positions:  {t*1e3:8.4f} ms   ({t*1e9/n:6.2f} ns each)")
print(f"  store: f64 authoritative {N*24/1e6:.0f} MB vs float32 {N*12/1e6:.0f} MB for {N} positions")
print("\nNOT a GPU cost. NOT an engine transform loop. numpy on one cloud CPU core, "
      "one contiguous array, allocation included.")
