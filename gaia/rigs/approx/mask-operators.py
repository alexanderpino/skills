#!/usr/bin/env python3
"""Price the distance-transform recommendations in gaia/references/mask-operators.md.

The document already states how GOOD each operator is (hajdu2012's 0.0572 / 0.0198 chamfer
constants, reproduced on the page; the exact transform's 0.000e+00 against brute force). It
never states what any of them COSTS. This measures the cost.

What is measured
  1. correctness gate -- the exact separable transform (Felzenszwalb & Huttenlocher Alg. 1)
     against brute force, and the 3-4 chamfer against the analytic Euclidean distance, so the
     memory figures below are attached to the operators the document actually recommends.
  2. bytes per cell -- peak RSS of a child process, least-squares slope over five grid sizes.
     The slope cancels the interpreter/numpy baseline, so it is the per-cell working set of the
     transform itself. Deterministic: it is array shapes, not wall clock.
  3. float32 exactness -- whether a 4-byte field could hold the squared distances a 4096^2 grid
     produces. If it cannot, the 8 bytes/cell is forced by the algorithm, not a dtype whim.
  4. wall clock -- reported as a RATIO (chamfer : exact) as well as absolutes, because absolutes
     on a shared container drift with load and ratios do not.

Rig: CPython + numpy on a 4-core Intel Xeon @ 2.80GHz container. This is NOT a GPU frame cost
and NOT a C implementation's throughput; the bytes/cell and the exactness result are properties
of the algorithm and carry over, the milliseconds are this interpreter's and do not.

Usage:  python3 mask-operators.py            # full report
        python3 mask-operators.py --rss OP N # child: run OP on an NxN grid, print peak RSS KB
"""
import sys
import resource
import subprocess
import time

import numpy as np

INF = 1e12


# ---------------------------------------------------------------- exact separable transform

def _edt_1d(f, d, v, z):
    """Felzenszwalb & Huttenlocher Algorithm 1: lower envelope of parabolas rooted at (q, f(q))."""
    n = f.shape[0]
    k = 0
    v[0] = 0
    z[0] = -INF
    z[1] = INF
    for q in range(1, n):
        while True:
            r = v[k]
            s = ((f[q] + q * q) - (f[r] + r * r)) / (2.0 * q - 2.0 * r)
            if s <= z[k]:
                k -= 1
                if k < 0:
                    k = 0
                    break
            else:
                break
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = INF
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        r = v[k]
        d[q] = (q - r) * (q - r) + f[r]


def edt2_sq(mask):
    """Squared exact Euclidean distance to the nearest True cell. One full-field array, in place."""
    m, n = mask.shape
    f = np.where(mask, 0.0, INF)            # the ONE full-field array, float64
    long = max(m, n)
    d = np.empty(long, dtype=np.float64)    # O(max(m,n)) scratch, not per-cell
    v = np.empty(long, dtype=np.int64)
    z = np.empty(long + 1, dtype=np.float64)
    for x in range(n):                      # pass down every column
        col = f[:, x].copy()
        _edt_1d(col, d[:m], v[:m], z[:m + 1])
        f[:, x] = d[:m]
    for y in range(m):                      # pass across every row of the result
        row = f[y, :].copy()
        _edt_1d(row, d[:n], v[:n], z[:n + 1])
        f[y, :] = d[:n]
    return f


# ---------------------------------------------------------------- chamfer 3-4 two-sweep

def _row_running_min(row, a, idx):
    """d[x] = min_{k<=x} (row[k] + a*(x-k)) -- the (0,-1) chain, done as an accumulate."""
    np.minimum.accumulate(row - a * idx, out=row)
    row += a * idx


def chamfer(mask, a, b, scale):
    """3-4 / 5-7-11 chamfer: forward raster sweep then backward.

    Deliberately like-for-like with edt2_sq: ONE full-field float64 array, swept in place, so the
    two bytes/cell figures can be compared. The 5-7-11 mask's 5x5 neighbours are applied by
    iterating the 3x3-plus-knight sweep to a fixed point.
    """
    m, n = mask.shape
    BIG = 1e12
    d = np.where(mask, 0.0, BIG)                  # the ONE full-field array, float64
    idx = np.arange(n, dtype=np.float64)
    knight = (scale == 5)
    c = 11.0
    for _ in range(6 if knight else 1):
        prev = None if not knight else d.copy()
        for y in range(m):                        # forward: (-1,-1) (-1,0) (-1,1) (0,-1)
            row = d[y]
            if y:
                up = d[y - 1]
                np.minimum(row, up + a, out=row)
                np.minimum(row[1:], up[:-1] + b, out=row[1:])
                np.minimum(row[:-1], up[1:] + b, out=row[:-1])
            if knight and y >= 2:
                u2 = d[y - 2]
                np.minimum(row[1:], u2[:-1] + c, out=row[1:])
                np.minimum(row[:-1], u2[1:] + c, out=row[:-1])
            if knight and y >= 1:
                u1 = d[y - 1]
                np.minimum(row[2:], u1[:-2] + c, out=row[2:])
                np.minimum(row[:-2], u1[2:] + c, out=row[:-2])
            _row_running_min(row, a, idx)
        for y in range(m - 1, -1, -1):            # backward: the mirrored neighbours
            row = d[y]
            if y < m - 1:
                dn = d[y + 1]
                np.minimum(row, dn + a, out=row)
                np.minimum(row[1:], dn[:-1] + b, out=row[1:])
                np.minimum(row[:-1], dn[1:] + b, out=row[:-1])
            if knight and y < m - 2:
                d2 = d[y + 2]
                np.minimum(row[1:], d2[:-1] + c, out=row[1:])
                np.minimum(row[:-1], d2[1:] + c, out=row[:-1])
            if knight and y < m - 1:
                d1 = d[y + 1]
                np.minimum(row[2:], d1[:-2] + c, out=row[2:])
                np.minimum(row[:-2], d1[2:] + c, out=row[:-2])
            rev = row[::-1].copy()
            _row_running_min(rev, a, idx)
            row[:] = rev[::-1]
        if knight and prev is not None and np.array_equal(prev, d):
            break
    d /= scale                                    # in place: no second field
    return d


def scratch_bytes(n):
    """The exact transform's per-line envelope stack, the array the chamfer does not need."""
    return (np.empty(n, np.float64).nbytes + np.empty(n, np.int64).nbytes
            + np.empty(n + 1, np.float64).nbytes)


# ---------------------------------------------------------------- gates

def gate_exact(rng):
    """Alg. 1 against brute-force minimisation over all seed pixels."""
    out = []
    for m, n, nseed in ((64, 64, 40), (129, 129, 1)):
        mask = np.zeros((m, n), dtype=bool)
        if nseed == 1:
            mask[m // 2, n // 2] = True
        else:
            ys = rng.integers(0, m, nseed)
            xs = rng.integers(0, n, nseed)
            mask[ys, xs] = True
        got = np.sqrt(edt2_sq(mask))
        sy, sx = np.nonzero(mask)
        yy, xx = np.mgrid[0:m, 0:n]
        brute = np.sqrt(np.min((yy[..., None] - sy) ** 2 + (xx[..., None] - sx) ** 2, axis=-1))
        out.append((f"{m}x{n}, {nseed} seed(s)", float(np.max(np.abs(got - brute)))))
    return out


def gate_chamfer():
    """Max relative error of the 3-4 and 5-7-11 masks, single centre seed, cells beyond r = 20.

    hajdu2012 prints 0.0572 and 0.0198. Reproducing them says the implementation whose memory is
    measured below is the operator the document names.
    """
    m = 201
    mask = np.zeros((m, m), dtype=bool)
    mask[m // 2, m // 2] = True
    yy, xx = np.mgrid[0:m, 0:m]
    true = np.sqrt((yy - m // 2) ** 2 + (xx - m // 2) ** 2)
    far = true > 20
    out = []
    for name, (a, b, sc) in (("3-4", (3, 4, 3)), ("5-7-11", (5, 7, 5))):
        approx = chamfer(mask, a, b, sc)
        rel = (approx - true)[far] / true[far]
        out.append((name, float(np.max(np.abs(rel))), float(np.max(rel)), float(np.min(rel))))
    return out


def gate_float32():
    """Can a 4-byte field hold the squared distances a 4096^2 grid produces exactly?"""
    n = 4096
    worst = 2 * (n - 1) ** 2                      # corner-to-corner squared distance
    bad = [v for v in range(worst - 40, worst + 1)
           if int(np.float32(v)) != v]
    return worst, len(bad), 40 + 1


# ---------------------------------------------------------------- cost: bytes per cell

OPS = {"exact": lambda mk: edt2_sq(mk), "chamfer": lambda mk: chamfer(mk, 3.0, 4.0, 3.0),
       "none": lambda mk: mk}


def _child(op, n):
    mask = np.zeros((n, n), dtype=bool)
    mask[n // 2, n // 2] = True
    mask[n // 4, 3 * n // 4] = True
    res = OPS[op](mask)
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"{kb} {float(res[0, 0]):.6f}")


def bytes_per_cell(op, sizes):
    xs, ys = [], []
    for n in sizes:
        p = subprocess.run([sys.executable, __file__, "--rss", op, str(n)],
                           capture_output=True, text=True, check=True)
        kb = int(p.stdout.split()[0])
        xs.append(n * n)
        ys.append(kb * 1024.0)
    x = np.array(xs, dtype=np.float64)
    y = np.array(ys, dtype=np.float64)
    A = np.vstack([x, np.ones_like(x)]).T
    slope, base = np.linalg.lstsq(A, y, rcond=None)[0]
    resid = y - (slope * x + base)
    return slope, base, list(zip(sizes, ys)), float(np.max(np.abs(resid)) / y.max())


# ---------------------------------------------------------------- cost: wall clock

def timings(n, reps=3):
    mask = np.zeros((n, n), dtype=bool)
    mask[n // 2, n // 2] = True
    out = {}
    for op, fn in OPS.items():
        best = min(_time_once(fn, mask) for _ in range(reps))
        out[op] = best * 1e3
    return out


def _time_once(fn, mask):
    t = time.perf_counter()
    fn(mask)
    return time.perf_counter() - t


# ---------------------------------------------------------------- report

def main():
    rng = np.random.default_rng(20260914)
    print("rig: CPython", sys.version.split()[0], "/ numpy", np.__version__,
          "/ 4-core Intel Xeon @ 2.80GHz container. NOT a GPU cost, NOT a C throughput.")
    print("seed: 20260914")
    print()

    print("GATE 1 -- exact separable transform vs brute force (max abs difference, cells)")
    for label, err in gate_exact(rng):
        print(f"  {label:24s} {err:.3e}")
    print()

    print("GATE 2 -- chamfer max relative error, 201^2, single centre seed, cells beyond r=20")
    print("          (hajdu2012 prints 0.0572 for 3-4 and 0.0198 for 5-7-11)")
    for name, mx, pos, neg in gate_chamfer():
        print(f"  {name:8s} max|rel| {mx:.4f}   most positive {pos:+.4f}   most negative {neg:+.4f}")
    print()

    worst, nbad, ntested = gate_float32()
    print("GATE 3 -- float32 exactness of the squared-distance field on a 4096^2 grid")
    print(f"  largest squared distance the grid holds: {worst} ({worst / 2**20:.1f} Mi)")
    print(f"  of the {ntested} integers at or just below it, {nbad} are NOT exactly "
          f"representable in float32")
    print(f"  -> the field must be 8 bytes/cell (float64) or 4-byte INTEGER; a 4-byte FLOAT "
          f"field is not exact at this size")
    print()

    sizes = (1536, 2048, 2560, 3072)
    print(f"COST 1 -- peak-RSS slope over grid sizes {sizes} = working set per cell")
    slopes = {}
    for op in ("exact", "chamfer"):
        slope, base, pts, relresid = bytes_per_cell(op, sizes)
        slopes[op] = slope
        print(f"  {op:8s} {slope:6.2f} bytes/cell   (baseline {base / 2**20:6.1f} MiB, "
              f"max residual {relresid * 100:.2f}% of peak)")
        for n, yb in pts:
            print(f"           {n:5d}^2  peak RSS {yb / 2**20:8.1f} MiB")
        print(f"           -> at 4096^2: {slope * 4096 * 4096 / 2**20:.0f} MiB; "
              f"at 16384^2: {slope * 16384 * 16384 / 2**30:.2f} GiB")
    d = slopes["exact"] - slopes["chamfer"]
    print(f"  difference exact - chamfer: {d:+.2f} bytes/cell "
          f"({d * 4096 * 4096 / 2**20:+.1f} MiB at 4096^2)")
    print("  the array the chamfer does NOT need is the per-line envelope stack, which is")
    print("  O(max(m,n)), not O(N):")
    for n in (1024, 4096, 16384):
        print(f"           {n:5d}^2  stack {scratch_bytes(n) / 1024:7.1f} KiB   "
              f"field {8 * n * n / 2**20:8.1f} MiB   "
              f"stack/field {100 * scratch_bytes(n) / (8 * n * n):.4f}%")
    print()

    print("COST 2 -- wall clock. NOT COMPARABLE BETWEEN THE TWO and NOT PUT ON THE PAGE: the")
    print("  exact transform here is a per-line CPython loop and the chamfer is vectorised numpy,")
    print("  so the ratio below measures the interpreter, not the algorithms. Recorded only so a")
    print("  later reader knows it was looked at and rejected as a figure to publish.")
    for n in (512,):
        t = timings(n)
        print(f"  {n}^2  exact {t['exact']:9.1f} ms   chamfer {t['chamfer']:8.1f} ms   "
              f"interpreter ratio {t['exact'] / t['chamfer']:.0f}x")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rss":
        _child(sys.argv[2], int(sys.argv[3]))
    else:
        main()
