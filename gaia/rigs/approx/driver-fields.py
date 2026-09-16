"""What an azimuth count costs and what it buys -- for gaia/references/driver-fields.md.

QUESTION. The document recommends one order-N horizon sweep, baked at N azimuths,
serving every sun position and the wind field. Two things a reader must be able to
price: what the baked field COSTS to keep, and how WRONG it is at a sun azimuth
that was not one of the N.

RIG. Pure numpy on CPython. A periodic synthetic heightfield (FFT-filtered noise,
k^-beta, fixed seed), scaled to a fixed rms slope. Horizon angle toward an azimuth
is found by stepping a rasterised ray out to a fixed search distance with periodic
wrap, so there are no border effects. Reference = 576 azimuths (0.625 deg), chosen
because 576 is divisible by 8/16/32/64, so every coarse set is an exact subset of
the reference and no interpolation contaminates the reference itself.
The default sampler takes whole cells (nearest offset), which is what a profile
sweep over a raster actually does; a bilinear cross-check re-runs one field to show
the answer is not an artefact of that choice.

WHAT THIS IS NOT. Not a bake-time benchmark, not a GPU number, not a measurement of
anyone's real terrain, and not a claim about urban skylines (where the horizon is a
step function of azimuth and every number here would be worse). The storage figures
at the end are exact arithmetic on a stated float width, not a benchmark.

Run: python3 driver-fields.py     (about 50 s, deterministic, numpy only)
"""
import math
import numpy as np

SEED = 20260910
GRID = 256          # cells per side
CELL = 25.0         # metres per cell
DMAX = 64           # search distance in cells -> 1.6 km
REF_DIRS = 576      # reference azimuth set; divisible by 8, 16, 32, 64
COUNTS = (8, 16, 32, 64)
RMS_SLOPE = 0.25    # terrain scaled to this rms |grad z| (about 14 degrees)
SUN_ELEVS = (10.0, 20.0)


def terrain(n, beta, rng):
    """Periodic fractal surface: white noise shaped by k^-beta, unit variance."""
    f = np.fft.fft2(rng.normal(size=(n, n)))
    ky = np.fft.fftfreq(n)[:, None]
    kx = np.fft.fftfreq(n)[None, :]
    k = np.hypot(kx, ky)
    k[0, 0] = 1.0
    f *= k ** (-beta)
    f[0, 0] = 0.0
    z = np.real(np.fft.ifft2(f))
    return z / z.std()


def scale_to_slope(z, cell, target):
    gy, gx = np.gradient(z, cell)
    return z * (target / float(np.sqrt((gx ** 2 + gy ** 2).mean())))


def _roll(z, ox, oy):
    return np.roll(np.roll(z, -oy, axis=0), -ox, axis=1)


def horizon_nearest(z, az, dmax, cell):
    """Horizon elevation angle (rad) toward `az`, whole-cell ray steps."""
    dx, dy = math.cos(az), math.sin(az)
    best = np.zeros_like(z)
    for s in range(1, dmax + 1):
        ox, oy = int(round(s * dx)), int(round(s * dy))
        if ox == 0 and oy == 0:
            continue
        np.maximum(best, (_roll(z, ox, oy) - z) / (math.hypot(ox, oy) * cell), out=best)
    return np.arctan(best)


def horizon_bilinear(z, az, dmax, cell):
    """Same, sampling the surface bilinearly at the exact ray position."""
    dx, dy = math.cos(az), math.sin(az)
    best = np.zeros_like(z)
    for s in range(1, dmax + 1):
        ox, oy = s * dx, s * dy
        x0, y0 = math.floor(ox), math.floor(oy)
        tx, ty = ox - x0, oy - y0
        sample = ((1 - tx) * (1 - ty) * _roll(z, x0, y0)
                  + tx * (1 - ty) * _roll(z, x0 + 1, y0)
                  + (1 - tx) * ty * _roll(z, x0, y0 + 1)
                  + tx * ty * _roll(z, x0 + 1, y0 + 1))
        np.maximum(best, (sample - z) / (s * cell), out=best)
    return np.arctan(best)


def reference(z, sampler):
    ref = np.empty((REF_DIRS, GRID, GRID), dtype=np.float32)
    for i in range(REF_DIRS):
        ref[i] = sampler(z, 2 * math.pi * i / REF_DIRS, DMAX, CELL)
    return ref


def report(name, z, ref):
    svf_ref_field = (np.cos(ref) ** 2).mean(axis=0)
    svf_ref = float(svf_ref_field.mean())
    adj = np.abs(ref[1:] - ref[:-1])
    print(f"--- {name}: relief {z.max() - z.min():.0f} m, "
          f"rms slope {RMS_SLOPE} ({math.degrees(math.atan(RMS_SLOPE)):.0f} deg), "
          f"mean SVF {svf_ref:.4f}")
    print(f"    rig floor, adjacent reference azimuths ({360 / REF_DIRS:.3f} deg apart): "
          f"|dtheta| mean {math.degrees(adj.mean()):.3f} deg, "
          f"max {math.degrees(adj.max()):.2f} deg")
    for n in COUNTS:
        assert REF_DIRS % n == 0
        step = REF_DIRS // n
        baked = ref[::step]
        assert baked.shape[0] == n
        svf_err = np.abs((np.cos(baked) ** 2).mean(axis=0) - svf_ref_field)
        tot = np.zeros(3)          # sum, count, max  (streamed, not stored)
        flips = {e: 0 for e in SUN_ELEVS}
        p99acc = []
        ntest = 0
        for i in range(REF_DIRS):
            if i % step == 0:
                continue
            lo = i // step
            hi = (lo + 1) % n
            t = (i % step) / step
            est = (1 - t) * baked[lo] + t * baked[hi]
            err = np.abs(est - ref[i])
            tot[0] += err.sum()
            tot[1] += err.size
            tot[2] = max(tot[2], err.max())
            p99acc.append(err.ravel()[::17])       # thinned, for the percentile
            for e in SUN_ELEVS:
                r = math.radians(e)
                flips[e] += int(np.count_nonzero((ref[i] < r) != (est < r)))
            ntest += err.size
        p99 = math.degrees(np.percentile(np.concatenate(p99acc), 99))
        flip_txt = ", ".join(f"{100 * flips[e] / ntest:.2f}% at {e:.0f} deg sun"
                             for e in SUN_ELEVS)
        print(f"  N={n:3d}  {4 * n:4d} bytes/cell   "
              f"SVF mean|err| {svf_err.mean():.5f} = {100 * svf_err.mean() / svf_ref:.2f}%, "
              f"max {svf_err.max():.5f} = {100 * svf_err.max() / svf_ref:.2f}%")
        print(f"           horizon angle at an unbaked azimuth: mean err "
              f"{math.degrees(tot[0] / tot[1]):.2f} deg, p99 {p99:.2f} deg, "
              f"max {math.degrees(tot[2]):.2f} deg;  shadow bit wrong on {flip_txt}")
    print()


def main():
    print(f"seed {SEED}  grid {GRID}^2  cell {CELL} m  dmax {DMAX} cells "
          f"= {DMAX * CELL / 1000:.1f} km  reference {REF_DIRS} azimuths  "
          f"linear interpolation between baked azimuths")
    print()
    rng = np.random.default_rng(SEED)
    smooth = scale_to_slope(terrain(GRID, 2.0, rng), CELL, RMS_SLOPE)
    rough = scale_to_slope(terrain(GRID, 1.5, rng), CELL, RMS_SLOPE)

    report("isotropic fBm, beta=2.0, whole-cell ray steps", smooth,
           reference(smooth, horizon_nearest))
    report("rougher fBm, beta=1.5, whole-cell ray steps", rough,
           reference(rough, horizon_nearest))
    report("isotropic fBm, beta=2.0, BILINEAR cross-check", smooth,
           reference(smooth, horizon_bilinear))

    print("storage, exact arithmetic on a stated width, not a benchmark:")
    for n in COUNTS:
        arr = np.zeros((n, 512, 512), dtype=np.float32)
        print(f"  N={n:3d}: float32 per azimuth = {arr.nbytes / (512 * 512):.0f} "
              f"bytes per cell -> {n * 4 * 4096 * 4096 / 1e9:.2f} GB for a 4096^2 tile")
    print(f"  reduced to one sky-view scalar: 4 bytes per cell -> "
          f"{4 * 4096 * 4096 / 1e6:.0f} MB for a 4096^2 tile")


if __name__ == "__main__":
    main()
