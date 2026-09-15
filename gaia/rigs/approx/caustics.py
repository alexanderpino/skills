#!/usr/bin/env python3
"""Two numbers for gaia/references/caustics.md, both re-runnable.

RIG (what this IS):
  A 1-D, single-wavelength, geometric-optics caustic on CPU. One sinusoidal water surface,
  a zenith sun, a flat bed at depth d, Snell refraction at n = 1.335, one refraction per
  photon, no scattering, no absorption, no Fresnel weighting. Photons are emitted on a
  UNIFORM grid in surface x -- one per light-space texel, exactly as the caustic-map
  technique does -- and splatted nearest-bin into a periodic bed texture. The reference is
  the SAME estimator at 2^22 photons; the sweep measures how far a practical photon count
  sits from its own converged answer.

  What it is NOT: not a GPU frame cost, not a render, not a validation of the caustic map
  against a path-traced ground truth. It prices ONE error term -- the estimator's
  discretisation -- and the storage a 2-D map of a given size occupies. Nothing else.

  Deterministic: a uniform grid, no RNG, so no seed. Same output on every run.
"""
import numpy as np

N_WATER = 1.335
LAMBDA  = 0.5    # surface wavelength, m -- a wind ripple
AMP     = 0.02   # amplitude, m -> steepness A/lambda = 0.04 (H/L = 0.08)
DEPTH   = 3.0    # bed depth below mean surface, m -- well past the 1.3 m focal depth
BINS    = 512    # bed texels per surface wavelength
REF_N   = 1 << 22


def bed_gain(n_photons: int, bins: int = BINS, half_width: int = 0) -> np.ndarray:
    """Splat n_photons over one surface wavelength; return the bed gain, mean 1."""
    x = (np.arange(n_photons) + 0.5) * (LAMBDA / n_photons)
    h = AMP * np.sin(2 * np.pi * x / LAMBDA)
    s = AMP * (2 * np.pi / LAMBDA) * np.cos(2 * np.pi * x / LAMBDA)   # dh/dx

    inv = 1.0 / np.sqrt(1.0 + s * s)
    Nx, Nz = -s * inv, inv          # unit up-normal
    Ix, Iz = 0.0, -1.0              # zenith sun, travelling down
    eta = 1.0 / N_WATER
    c1 = -(Ix * Nx + Iz * Nz)       # cos(theta_i) > 0
    k = 1.0 - eta * eta * (1.0 - c1 * c1)
    assert (k > 0).all(), "no TIR entering the denser medium"
    f = eta * c1 - np.sqrt(k)
    Tx, Tz = eta * Ix + f * Nx, eta * Iz + f * Nz
    assert (Tz < 0).all()

    t = (h + DEPTH) / (-Tz)
    xb = np.mod(x + t * Tx, LAMBDA)

    pos = xb / LAMBDA * bins                       # continuous bed-texel coordinate
    if half_width == 0:                            # nearest-bin: a bare additive splat
        idx = np.minimum(pos.astype(np.int64), bins - 1)
        g = np.bincount(idx, minlength=bins).astype(np.float64)
    else:                                          # normalised tent kernel, half_width texels
        base = np.floor(pos).astype(np.int64)
        g = np.zeros(bins)
        offs = np.arange(-half_width, half_width + 1)
        w = np.maximum(0.0, 1.0 - np.abs((base[:, None] + offs + 0.5) - pos[:, None]) / half_width)
        w /= w.sum(axis=1, keepdims=True)          # every photon deposits exactly its energy
        np.add.at(g, np.mod(base[:, None] + offs, bins).ravel(), w.ravel())
    return g * (bins / n_photons)   # mean 1 by construction


def main() -> None:
    ref = bed_gain(REF_N)
    fold = ref.max()
    print(f"# rig: lambda={LAMBDA} m  A={AMP} m  depth={DEPTH} m  n={N_WATER}  "
          f"bed bins={BINS}  reference={REF_N} photons")
    print(f"# converged gain: mean {ref.mean():.6f}  min {ref.min():.3f}  "
          f"peak {fold:.2f}  (folds present: peak/mean = {fold:.1f})")
    print()
    print("photons/wavelength  photons/bed texel  RMS error (gain units, mean=1)  peak error")
    for n in (512, 1024, 2048, 4096, 8192, 16384, 32768):
        g = bed_gain(n)
        d = g - ref
        print(f"{n:>18}  {n / BINS:>17.1f}  {np.sqrt((d * d).mean()):>29.3f}  "
              f"{np.abs(d).max():>10.2f}")
    print()

    print("tent kernel at 1 emitted photon per bed texel: does a kernel buy convergence?")
    print(f"half-width [texels]   RMS error   peak gain (converged peak = {fold:.1f})")
    for hw in (0, 1, 2, 4, 8):
        g = bed_gain(512, half_width=hw)
        d = g - ref
        print(f"{hw:>19}   {np.sqrt((d * d).mean()):>9.3f}   {g.max():>29.2f}")
    print()

    # Storage: arithmetic, not a benchmark. Bytes for the two resident light-space targets.
    print("resident light-space storage (arithmetic: resolution x format, not a measurement)")
    for res in (512, 1024, 2048):
        caustic = res * res * 2      # R16F scalar gain
        depth = res * res * 4        # R32F light-space depth map of the terrain (step 3)
        print(f"  {res}^2: caustic R16F {caustic / 2**20:.1f} MiB + depth R32F "
              f"{depth / 2**20:.1f} MiB = {(caustic + depth) / 2**20:.1f} MiB")
    print("  emission image, IF materialised rather than emitted from the wave field:")
    for res in (1024, 2048, 4096, 8192):
        print(f"    {res}^2 RG16F normals: {res * res * 4 / 2**20:.1f} MiB")




# ---------------------------------------------------------------------------
# 2-D: the same estimator on a crossed ripple, because the 1-D photons-per-texel
# ratio does not transfer to a 2-D emission grid on its own.
# ---------------------------------------------------------------------------

def bed_gain_2d(n: int, bins: int = 256, chunk: int = 256,
                jitter: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    """n x n photons on a lambda x lambda cell of h = A(sin kx + sin ky); bins x bins bed."""
    k = 2 * np.pi / LAMBDA
    eta = 1.0 / N_WATER
    step = LAMBDA / n
    g = np.zeros(bins * bins)
    xs = (np.arange(n) + 0.5) * step
    xj, yj = xs + jitter[0] * step, xs + jitter[1] * step
    for a in range(0, n, chunk):
        yb = yj[a:a + chunk]
        X, Y = np.meshgrid(xj, yb, indexing="xy")
        h = AMP * (np.sin(k * X) + np.sin(k * Y))
        hx = AMP * k * np.cos(k * X)
        hy = AMP * k * np.cos(k * Y)
        inv = 1.0 / np.sqrt(1.0 + hx * hx + hy * hy)
        Nx, Ny, Nz = -hx * inv, -hy * inv, inv
        c1 = Nz                                  # -(I.N) with I = (0,0,-1)
        f = eta * c1 - np.sqrt(1.0 - eta * eta * (1.0 - c1 * c1))
        Tx, Ty, Tz = eta * 0 + f * Nx, eta * 0 + f * Ny, -eta + f * Nz
        t = (h + DEPTH) / (-Tz)
        ix = np.mod((X + t * Tx) / LAMBDA * bins, bins).astype(np.int64)
        iy = np.mod((Y + t * Ty) / LAMBDA * bins, bins).astype(np.int64)
        g += np.bincount((iy * bins + ix).ravel(), minlength=bins * bins)
    return g * (bins * bins / float(n) / float(n))


def main_2d() -> None:
    REF = 8192
    ref = bed_gain_2d(REF)
    print("2-D crossed ripple h = A(sin kx + sin ky), same lambda/A/depth/n; "
          f"bed {256}x{256} texels per cell, reference {REF}x{REF} photons")
    print(f"# converged gain: mean {ref.mean():.6f}  min {ref.min():.3f}  peak {ref.max():.2f}")
    print("photons/axis  photons/bed texel  RMS error (gain units, mean=1)  peak error")
    for n in (256, 512, 1024, 2048, 4096):
        gg = bed_gain_2d(n)
        d = gg - ref
        print(f"{n:>12}  {(n / 256.0) ** 2:>17.0f}  {np.sqrt((d * d).mean()):>29.3f}  "
              f"{np.abs(d).max():>10.2f}")
    print()
    print("temporal accumulation of 4 frames at 256 photons/axis -- jittered vs not")
    same = np.mean([bed_gain_2d(256) for _ in range(4)], axis=0)
    jit = np.mean([bed_gain_2d(256, jitter=(dx, dy))
                   for dx in (-0.25, 0.25) for dy in (-0.25, 0.25)], axis=0)
    for name, g in (("4x the SAME grid", same), ("4x quarter-texel jitter", jit)):
        d = g - ref
        print(f"  {name:<24} RMS error {np.sqrt((d * d).mean()):.3f}")
    print("  (the jittered set is exactly the 512-photons/axis grid, so it reproduces that row)")


def _all():
    main()
    main_2d()


if __name__ == "__main__":
    _all()
