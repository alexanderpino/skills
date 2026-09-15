"""Measure the tectonic-uplift.md spectral flexure block: idempotency residual + machine cost.

The block is transcribed LITERALLY from gaia/references/tectonic-uplift.md (the fence under
"Flexural is the one to implement"). Rig is a CPython 3.11 + numpy pocketfft microbenchmark on
this container's CPU. It is NOT a GPU frame cost, NOT a shipped-engine figure, and NOT a
measurement of the erosion run this block sits inside.

    python3 tectonic-uplift.py
"""
import time
import numpy as np

SEED = 20260910  # unused by the load (analytic Gaussian) but pinned for reproducibility
np.random.seed(SEED)

RHO_C, RHO_M, RHO_INFILL = 2800.0, 3300.0, 0.0
E, NU, G = 70e9, 0.25, 9.81


def D_of(Te):
    return E * Te ** 3 / (12 * (1 - NU ** 2))


def alpha_of(Te):
    return (4 * D_of(Te) / ((RHO_M - RHO_INFILL) * G)) ** 0.25


def radial_k(n, dx, dtype=np.float64):
    kx = 2 * np.pi * np.fft.fftfreq(n, d=dx).astype(dtype)
    ky = 2 * np.pi * np.fft.fftfreq(n, d=dx).astype(dtype)
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    return np.sqrt(KX ** 2 + KY ** 2)


def bump(n, dx, amp=3000.0, sigma=60e3, dtype=np.float64):
    c = (n // 2) * dx
    x = (np.arange(n) * dx - c).astype(dtype)
    X, Y = np.meshgrid(x, x, indexing="ij")
    return (amp * np.exp(-(X ** 2 + Y ** 2) / (2 * sigma ** 2))).astype(dtype)


def flexure_step(h, w_prev, k, Te, dtype=np.float64):
    """The document's block, verbatim, as one periodic update."""
    t_load = h + w_prev                                    # UN-deflected rock column
    q = RHO_C * G * t_load
    Q = np.fft.fft2(q)
    W = Q / (D_of(Te) * k ** 4 + (RHO_M - RHO_INFILL) * G)
    w_new = np.real(np.fft.ifft2(W)).astype(dtype)
    return (h - (w_new - w_prev)).astype(dtype), w_new


def run(n, dx, Te, calls, dtype=np.float64):
    k = radial_k(n, dx, dtype)
    h0 = bump(n, dx, dtype=dtype)
    h, w = h0.copy(), np.zeros_like(h0)
    peaks = []
    for _ in range(calls):
        h, w = flexure_step(h, w, k, Te, dtype)
        peaks.append(float(h.max()))
    return h0, h, w, peaks


def naive(n, dx, Te, calls):
    """The form the document says converges to zero: load from the already-deflected surface."""
    k = radial_k(n, dx)
    h = bump(n, dx)
    peaks = []
    for _ in range(calls):
        Q = np.fft.fft2(RHO_C * G * h)
        W = Q / (D_of(Te) * k ** 4 + (RHO_M - RHO_INFILL) * G)
        h = h - np.real(np.fft.ifft2(W))
        peaks.append(float(h.max()))
    return peaks


print("== rig ==")
import sys, platform
print(f"python {sys.version.split()[0]}  numpy {np.__version__}  {platform.machine()}")

print("\n== validation: alpha table against the document's printed row ==")
for Te_km in (5, 10, 20, 40, 80):
    print(f"  Te={Te_km:3d} km  alpha={alpha_of(Te_km * 1e3) / 1e3:7.1f} km")

T0 = RHO_C / (RHO_M - RHO_INFILL)
print(f"\n== validation: k=0 limit ==\n  T(0)={T0:.4f}  surface fraction {1 - T0:.4f}"
      f"  x 6.6h = {(1 - T0) * 6.6:.4f} h")

print("\n== ERROR: idempotency, ten calls against one ==")
for n, dx_km in ((512, 2.0), (512, 1.0)):
    _, h1, _, _ = run(n, dx_km * 1e3, 20e3, 1)
    _, h10, _, peaks = run(n, dx_km * 1e3, 20e3, 10)
    resid = float(np.abs(h10 - h1).max())
    print(f"  {n}^2 x {dx_km} km fp64: single-shot peak {h1.max():8.2f} m, "
          f"peak after 10 {peaks[-1]:8.2f} m, max |h10-h1| = {resid:.3e} m")

_, h1f, _, _ = run(512, 2e3, 20e3, 1, np.float32)
_, h10f, _, pf = run(512, 2e3, 20e3, 10, np.float32)
print(f"  512^2 x 2.0 km fp32: single-shot peak {h1f.max():8.2f} m, "
      f"peak after 10 {pf[-1]:8.2f} m, max |h10-h1| = {float(np.abs(h10f - h1f).max()):.3e} m")

print("\n== the naive form, same rig (document says 1163 -> ... -> 76 m) ==")
print("  peaks:", [f"{p:.1f}" for p in naive(512, 1e3, 20e3, 10)])

print("\n== COST: one flexure update (two FFTs) ==")
for n in (256, 512, 1024):
    k = radial_k(n, 2e3)
    h = bump(n, 2e3)
    w = np.zeros_like(h)
    flexure_step(h, w, k, 20e3)                      # warm the plan cache
    ts = []
    for _ in range(11):
        t = time.perf_counter()
        flexure_step(h, w, k, 20e3)
        ts.append((time.perf_counter() - t) * 1e3)
    ts.sort()
    print(f"  {n}^2 fp64: median {ts[len(ts) // 2]:7.2f} ms  (min {ts[0]:.2f}, max {ts[-1]:.2f}, 11 runs)")

w512 = np.zeros((512, 512), dtype=np.float64)
print(f"\n== COST: the w_prev state ==\n  fp64 w_prev: {w512.nbytes // w512.size} bytes per cell"
      f"  ({w512.nbytes / 2**20:.1f} MB at 512^2, {8 * 4096 * 4096 / 2**20:.0f} MB at 4096^2)")
