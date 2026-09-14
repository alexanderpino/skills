#!/usr/bin/env python3
"""What wrapping costs, on ONE rig: CPython + numpy, vectorised, CPU, single process.

Measures three things the document asserts as operation COUNTS and never as costs:

  A. the modular reduction itself -- `i % P` added to a 2-D gradient-lattice noise, against
     the same noise hashing the raw index.  The document calls this "one line".
  B. the 4-D torus embedding against the 2-D gradient-lattice noise it replaces.  The document
     states "16-against-4 is the *gradient*-lattice figure", a CORNER COUNT.  This measures the
     wall cost of the same pair on this rig.
  C. the permutation table the document tells you to lengthen -- "at least the *finest* octave's
     P*lacunarity^(n-1)" -- as bytes, via numpy's own nbytes.

WHAT THIS RIG IS NOT: it is not a GPU frame cost, not a shader cost, and not a per-sample cost
in a scalar inner loop.  numpy evaluates every lattice corner for every sample with no branching
and no cache blocking, so the 4-D/2-D ratio it reports is the ratio of two vectorised array
pipelines, not of two shaders.  A GPU kernel pays register pressure and transcendental
throughput this rig cannot see.  Nothing here may be printed as a frame time.

    python3 seamless-and-periodic.py            # seed 20260910, 512**2 samples, 9 repeats
"""
import time

import numpy as np

SEED = 20260910
N = 512                      # 512**2 = 262144 samples, the document's own sample count
REPEATS = 15


def perm_table(size, rng):
    p = rng.permutation(size).astype(np.int32)
    return np.concatenate([p, p])


def fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _grad2(h, x, y):
    h = h & 7
    u = np.where(h < 4, x, y)
    v = np.where(h < 4, y, x)
    return np.where(h & 1, -u, u) + np.where(h & 2, -2.0 * v, 2.0 * v)


def noise2(x, y, p, mask, period=None):
    """2-D gradient-lattice noise. `period` not None => reduce the lattice index mod it."""
    i0 = np.floor(x).astype(np.int32)
    j0 = np.floor(y).astype(np.int32)
    fx, fy = x - i0, y - j0
    if period is None:
        i0m, j0m = i0 & mask, j0 & mask
        i1m, j1m = (i0 + 1) & mask, (j0 + 1) & mask
    else:
        i0m, j0m = i0 % period, j0 % period
        i1m, j1m = (i0 + 1) % period, (j0 + 1) % period
        i0m, j0m = i0m & mask, j0m & mask
        i1m, j1m = i1m & mask, j1m & mask
    u, v = fade(fx), fade(fy)
    a, b = p[i0m] + j0m, p[i1m] + j0m
    a1, b1 = p[i0m] + j1m, p[i1m] + j1m
    n00 = _grad2(p[a], fx, fy)
    n10 = _grad2(p[b], fx - 1, fy)
    n01 = _grad2(p[a1], fx, fy - 1)
    n11 = _grad2(p[b1], fx - 1, fy - 1)
    x0 = n00 + u * (n10 - n00)
    x1 = n01 + u * (n11 - n01)
    return x0 + v * (x1 - x0)


def _grad4(h, x, y, z, w):
    h = h & 31
    a = np.where(h & 1, -x, x)
    b = np.where(h & 2, -y, y)
    c = np.where(h & 4, -z, z)
    d = np.where(h & 8, -w, w)
    return a + b + c + d


def noise4(x, y, z, w, p, mask):
    """4-D gradient-lattice noise: 16 corners, same hash and same fade as noise2."""
    i0 = np.floor(x).astype(np.int32)
    j0 = np.floor(y).astype(np.int32)
    k0 = np.floor(z).astype(np.int32)
    l0 = np.floor(w).astype(np.int32)
    fx, fy, fz, fw = x - i0, y - j0, z - k0, w - l0
    u, v, s, t = fade(fx), fade(fy), fade(fz), fade(fw)
    i0m, j0m, k0m, l0m = i0 & mask, j0 & mask, k0 & mask, l0 & mask
    i1m, j1m, k1m, l1m = (i0 + 1) & mask, (j0 + 1) & mask, (k0 + 1) & mask, (l0 + 1) & mask
    corners = []
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                for dl in (0, 1):
                    ii = i1m if di else i0m
                    jj = j1m if dj else j0m
                    kk = k1m if dk else k0m
                    ll = l1m if dl else l0m
                    h = p[p[p[p[ii] + jj] + kk] + ll]
                    g = _grad4(h, fx - di, fy - dj, fz - dk, fw - dl)
                    wgt = (u if di else 1.0 - u) * (v if dj else 1.0 - v) \
                        * (s if dk else 1.0 - s) * (t if dl else 1.0 - t)
                    corners.append(g * wgt)
    acc = corners[0]
    for c in corners[1:]:
        acc = acc + c
    return acc


def torus4(x, y, T, p, mask):
    """The document's embedding: two circles in 4-D, r = T/(2*pi) for a unit-rate mapping."""
    a = 2.0 * np.pi * x / T
    b = 2.0 * np.pi * y / T
    r = T / (2.0 * np.pi)
    return noise4(r * np.cos(a), r * np.sin(a), r * np.cos(b), r * np.sin(b), p, mask)


def bench(fn, repeats=REPEATS):
    fn()                                    # warm up: first call pays numpy's allocation
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    ts.sort()
    return ts[len(ts) // 2], ts[0], ts[-1]


def main():
    rng = np.random.default_rng(SEED)
    p = perm_table(256, rng)
    mask = 255
    T = 64

    xs = np.linspace(0.0, T, N, endpoint=False, dtype=np.float64)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    X = np.ascontiguousarray(X.ravel())
    Y = np.ascontiguousarray(Y.ravel())
    nsamp = X.size

    print(f"rig      CPython {__import__('sys').version.split()[0]}, numpy {np.__version__}, "
          f"float64, single process, CPU")
    print(f"seed     {SEED}   samples {N}x{N} = {nsamp}   repeats {REPEATS} (median, min, max ms)")
    print()

    # -- A. what the modular reduction costs -------------------------------------------------
    m_raw = bench(lambda: noise2(X, Y, p, mask, period=None))
    m_mod = bench(lambda: noise2(X, Y, p, mask, period=T))
    print(f"A  noise2, raw index            {m_raw[0]:8.2f} ms   ({m_raw[1]:.2f} .. {m_raw[2]:.2f})")
    print(f"A  noise2, index mod P          {m_mod[0]:8.2f} ms   ({m_mod[1]:.2f} .. {m_mod[2]:.2f})")
    print(f"A  ratio mod/raw                {m_mod[0] / m_raw[0]:8.3f} x")
    print(f"A  per megasample, mod          {m_mod[0] * 1e6 / nsamp:8.2f} ms/Msample")
    print()

    # -- B. what the 4-D torus embedding costs -----------------------------------------------
    m_t4 = bench(lambda: torus4(X, Y, T, p, mask))
    print(f"B  noise2 (4 corners)           {m_mod[0]:8.2f} ms   ({m_mod[1]:.2f} .. {m_mod[2]:.2f})")
    print(f"B  torus4 (16 corners + 4 trig) {m_t4[0]:8.2f} ms   ({m_t4[1]:.2f} .. {m_t4[2]:.2f})")
    print(f"B  ratio torus4/noise2          {m_t4[0] / m_mod[0]:8.3f} x   "
          f"(corner count says 16/4 = 4.000 x)")
    print(f"B  per megasample, torus4       {m_t4[0] * 1e6 / nsamp:8.2f} ms/Msample")
    print()

    # -- B'. is the embedding actually periodic on this rig? ---------------------------------
    rng2 = np.random.default_rng(SEED + 1)
    sx = rng2.uniform(0.0, T, 4096)
    sy = rng2.uniform(0.0, T, 4096)
    e_x = np.max(np.abs(torus4(sx, sy, T, p, mask) - torus4(sx + T, sy, T, p, mask)))
    e_y = np.max(np.abs(torus4(sx, sy, T, p, mask) - torus4(sx, sy + T, T, p, mask)))
    print(f"B' torus4 max wrap error, x     {e_x:.3e}")
    print(f"B' torus4 max wrap error, y     {e_y:.3e}")
    print()

    # -- C. what the long hash table costs, in bytes -----------------------------------------
    print("C  permutation table, measured as numpy nbytes:")
    for label, entries in [("P = 1024, a P-entry table", 1024),
                           ("P = 1024, 6 octaves lac 2 -> finest is 32768", 32768)]:
        big = perm_table(entries, np.random.default_rng(SEED))              # int32, doubled
        lean = np.random.default_rng(SEED).permutation(entries).astype(np.uint16)
        print(f"C    {label:44s} int32 doubled {big.nbytes / 1024:7.1f} KB   "
              f"uint16 plain {lean.nbytes / 1024:7.1f} KB")
    print("C  (an integer mixer with no table pays 0 bytes and is the recommended route)")


if __name__ == "__main__":
    main()
