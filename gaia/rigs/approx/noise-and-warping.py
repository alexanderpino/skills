"""What the recommended noise stack COSTS, on one rig, measured.

Rig: CPython 3.11 + numpy, one container core, vectorised over a 512x512 grid.
THIS IS NOT A GPU FRAME COST and must never be printed as one. A shader evaluates
the same stack per pixel with a different memory hierarchy; nothing here predicts it.
What DOES transfer is the RATIO warp1/fbm and warp2/fbm, because it is the same code
paying the same memory traffic three or five times.

Configs, matching gaia/references/noise-and-warping.md:
  fbm    : 8-octave improved-Perlin fBm, quintic fade, 8-vector 2D gradient set,
           lacunarity 2.03, gain 0.5, per-octave offsets (O_0 = 0)   -> 1 fBm call
  warp1  : fbm(p + K*vec2(fbm(p+O1), fbm(p+O2)))                     -> 3 fBm calls
  warp2  : q = vec2(fbm(p+O1), fbm(p+O2))
           r = vec2(fbm(p+K1*q+O3), fbm(p+K1*q+O4)); fbm(p+K2*r)     -> 5 fBm calls

Usage:  python3 noise-and-warping.py [--reps N] [--seed S]
"""
import argparse
import statistics
import time

import numpy as np

# 8-vector 2D gradient set: 4 axes + 4 diagonals, as the document describes.
GRAD2 = np.array([(1, 0), (-1, 0), (0, 1), (0, -1),
                  (1, 1), (-1, 1), (1, -1), (-1, -1)], dtype=np.float64)


def make_perm(seed):
    rng = np.random.default_rng(seed)
    p = rng.permutation(256).astype(np.int32)
    return np.concatenate([p, p])


def fade(t):                       # quintic 6t^5 - 15t^4 + 10t^3 [perlin2002]
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin2(x, y, perm):
    xi = np.floor(x).astype(np.int32) & 255
    yi = np.floor(y).astype(np.int32) & 255
    xf = x - np.floor(x)
    yf = y - np.floor(y)
    u, v = fade(xf), fade(yf)
    aa = perm[perm[xi] + yi] & 7
    ab = perm[perm[xi] + yi + 1] & 7
    ba = perm[perm[xi + 1] + yi] & 7
    bb = perm[perm[xi + 1] + yi + 1] & 7
    g = GRAD2
    n00 = g[aa, 0] * xf + g[aa, 1] * yf
    n01 = g[ab, 0] * xf + g[ab, 1] * (yf - 1.0)
    n10 = g[ba, 0] * (xf - 1.0) + g[ba, 1] * yf
    n11 = g[bb, 0] * (xf - 1.0) + g[bb, 1] * (yf - 1.0)
    x0 = n00 + u * (n10 - n00)
    x1 = n01 + u * (n11 - n01)
    return x0 + v * (x1 - x0)


def fbm(x, y, perm, offs, octaves=8, lac=2.03, gain=0.5):
    total = np.zeros_like(x)
    amp, freq, norm = 1.0, 1.0, 0.0
    for i in range(octaves):
        ox, oy = offs[i]
        total += amp * perlin2(x * freq + ox, y * freq + oy, perm)
        norm += amp
        freq *= lac
        amp *= gain
    return total / norm


def warp1(x, y, perm, offs, K):
    qx = fbm(x + 5.2, y + 1.3, perm, offs)
    qy = fbm(x + 9.7, y + 4.1, perm, offs)
    return fbm(x + K * qx, y + K * qy, perm, offs)


def warp2(x, y, perm, offs, K1, K2):
    qx = fbm(x + 5.2, y + 1.3, perm, offs)
    qy = fbm(x + 9.7, y + 4.1, perm, offs)
    rx = fbm(x + K1 * qx + 1.7, y + K1 * qy + 9.2, perm, offs)
    ry = fbm(x + K1 * qx + 8.3, y + K1 * qy + 2.8, perm, offs)
    return fbm(x + K2 * rx, y + K2 * ry, perm, offs)


def octave_drop(x, y, perm, offs, full_octaves=8):
    """What does dropping the finest octave COST in accuracy?

    A real LOD keeps the COARSE field's normalisation across bands -- renormalising per
    band makes the terrain change height at the band boundary, which is the pop LOD is
    trying to avoid. So the truncated stack is divided by the FULL stack's norm, and the
    difference is exactly the dropped octaves' own contribution.
    """
    gain = 0.5
    norm_full = sum(gain ** i for i in range(full_octaves))
    full = fbm(x, y, perm, offs, octaves=full_octaves)
    pp = float(full.max() - full.min())
    print(f"\noctave-drop error, {full_octaves}-octave stack, same normalisation across bands "
          f"(peak-to-peak of the full field = {pp:.4f}):")
    for k in range(full_octaves - 1, full_octaves - 4, -1):
        cut = fbm(x, y, perm, offs, octaves=k) * (sum(gain ** i for i in range(k)) / norm_full)
        d = cut - full
        mx = float(np.abs(d).max()) / pp * 100.0
        rms = float(np.sqrt((d ** 2).mean())) / pp * 100.0
        print(f"  drop to {k} octaves ({full_octaves - k} dropped): "
              f"max {mx:6.3f}% of range   rms {rms:6.3f}%   "
              f"(bound: sum of dropped amplitudes / norm = "
              f"{100 * sum(gain ** i for i in range(k, full_octaves)) / norm_full:6.3f}%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=7)
    ap.add_argument("--seed", type=int, default=20260914)
    ap.add_argument("--n", type=int, default=512)
    args = ap.parse_args()

    perm = make_perm(args.seed)
    rng = np.random.default_rng(args.seed + 1)
    offs = [(0.0, 0.0)] + [tuple(rng.uniform(0, 256, 2)) for _ in range(15)]

    # 512x512 samples over a 64-cell base lattice, the document's warp rig.
    n = args.n
    lin = np.linspace(0.0, 64.0, n, endpoint=False)
    x, y = np.meshgrid(lin, lin)
    K = 4.0                                   # [quilez_warp] K = 4.0, both listings

    cases = {
        "fbm            (1 fBm call )": lambda: fbm(x, y, perm, offs),
        "warp1          (3 fBm calls)": lambda: warp1(x, y, perm, offs, K),
        "warp2          (5 fBm calls)": lambda: warp2(x, y, perm, offs, K, K),
    }

    print(f"rig: CPython {'.'.join(map(str, __import__('sys').version_info[:3]))}, "
          f"numpy {np.__version__}, one container core, {n}x{n} grid, "
          f"8 octaves, lacunarity 2.03, gain 0.5, seed {args.seed}, reps {args.reps}")
    print("NOT a GPU frame cost. The transferable figure is the ratio.\n")

    results = {}
    for name, fn in cases.items():
        fn()                                   # warm up: first touch pays page faults
        ts = []
        for _ in range(args.reps):
            t0 = time.perf_counter()
            out = fn()
            ts.append((time.perf_counter() - t0) * 1e3)
        results[name] = ts
        med, lo, hi = statistics.median(ts), min(ts), max(ts)
        print(f"{name}  median {med:8.1f} ms   min {lo:8.1f}  max {hi:8.1f}  "
              f"spread {100 * (hi - lo) / med:4.1f}%   "
              f"range of field [{out.min():+.3f}, {out.max():+.3f}]")

    base = statistics.median(results["fbm            (1 fBm call )"])
    print()
    for name, ts in results.items():
        print(f"{name}  ratio to plain fBm  {statistics.median(ts) / base:5.2f}x")
    print(f"\nper-sample, plain 8-octave fBm: {base * 1e6 / (n * n):.0f} ns/sample "
          f"(numpy-vectorised, not a shader)")
    octave_drop(x, y, perm, offs)


if __name__ == "__main__":
    main()
