#!/usr/bin/env python3
"""Measure the max-mip traversal in gaia/references/heightfield-raymarching.md.

Two questions, one rig:

  ERROR  How far is the hit this kernel returns from the true first crossing of the
         SAME reconstructed surface, as a function of the refinement iteration count
         the block prescribes ("binary or secant refine, 5-8 iterations")?  And does
         the pyramid ever hide a hit (a miss the reference finds) or invent one?

  COST   What does the max-reduce pyramid add to the field it is built over?  This is
         exact arithmetic over the arrays actually built here, not a timing.

WHAT THIS RIG IS
  CPython + numpy, fp64 ray parameter, fp32 height storage, 512x512 base field at
  s0 = 1 m, surface reconstructed BILINEARLY from samples at texel centres, pyramid
  built exactly as the document prescribes (dilate the base samples 3x3, then
  max-reduce that).  Reference intersection is analytic: inside one bilinear cell the
  ray-surface difference is a QUADRATIC in t, solved in closed form, so the reference
  carries no step size and no tolerance of its own.

WHAT THIS RIG IS NOT
  Not a GPU measurement of any kind.  It prices no frame, no wave, no divergence, no
  bandwidth.  It is fp64 in t, so it does NOT reproduce the fp32 ULP behaviour the
  document argues about at :88-:96 -- the relative advance is exercised, its fp32
  failure mode is not.  The field is smooth and synthetic; a real terrain with cliffs
  has longer level-0 spans and therefore a larger refinement residual at the same
  iteration count.

Run:  python3 heightfield-raymarching.py
Seed: 20260910 (fixed below)
"""
import math
import random

import numpy as np

SEED = 20260910
S0 = 1.0          # metres per level-0 texel
N = 512           # base grid is N x N
A, KX = 40.0, 2.0 * math.pi / 128.0
B, KZ = 15.0, 2.0 * math.pi / 91.0
BISECTIONS = (5, 6, 8)   # the range the document's block prescribes
SCAN = 8                 # linear-search samples used only when the endpoints do not bracket
STEP_CAP = 10 ** 9
RELATIVE_ADVANCE = 1.0 + 2.0 ** -22   # the constant printed in the document


def analytic(x, z):
    return A * math.sin(KX * x) + B * math.sin(KZ * z)


# ---------------------------------------------------------------- field + pyramid
def build():
    i = (np.arange(N) + 0.5) * S0
    hx = A * np.sin(KX * i)
    hz = B * np.sin(KZ * i)
    H = (hx[None, :] + hz[:, None]).astype(np.float32)   # H[j, i], i -> x, j -> z

    # level 0 of the pyramid: the base samples DILATED 3x3, per the document.  A texel's
    # half-open square is reconstructed from samples i-1..i+1, so the 3x3 max bounds it.
    d = H.copy()
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            d = np.maximum(d, np.roll(np.roll(H, dj, axis=0), di, axis=1))
    pyr = [d]
    while pyr[-1].shape[0] > 1:
        p = pyr[-1]
        pyr.append(np.maximum.reduce([p[0::2, 0::2], p[0::2, 1::2],
                                      p[1::2, 0::2], p[1::2, 1::2]]))
    return H, pyr


def surface(H, x, z):
    """Bilinear reconstruction from samples at texel centres."""
    u, v = x / S0 - 0.5, z / S0 - 0.5
    i, j = int(math.floor(u)), int(math.floor(v))
    p, q = u - i, v - j
    i = min(max(i, 0), N - 2)
    j = min(max(j, 0), N - 2)
    h00, h10 = float(H[j, i]), float(H[j, i + 1])
    h01, h11 = float(H[j + 1, i]), float(H[j + 1, i + 1])
    return (h00 * (1 - p) * (1 - q) + h10 * p * (1 - q)
            + h01 * (1 - p) * q + h11 * p * q)


# ---------------------------------------------------------------- exact reference
def cell_quadratic(H, o, d, i, j):
    """f(t) = rayHeight(t) - surface(t) inside bilinear cell (i, j): a quadratic."""
    h00, h10 = float(H[j, i]), float(H[j, i + 1])
    h01, h11 = float(H[j + 1, i]), float(H[j + 1, i + 1])
    c0 = h00
    c1 = h10 - h00
    c2 = h01 - h00
    c3 = h00 - h10 - h01 + h11
    x0 = (i + 0.5) * S0
    z0 = (j + 0.5) * S0
    p0, pd = (o[0] - x0) / S0, d[0] / S0
    q0, qd = (o[2] - z0) / S0, d[2] / S0
    a2 = -(c3 * pd * qd)
    a1 = d[1] - (c1 * pd + c2 * qd + c3 * (p0 * qd + q0 * pd))
    a0 = o[1] - (c0 + c1 * p0 + c2 * q0 + c3 * p0 * q0)
    return a2, a1, a0


def roots_in(a2, a1, a0, lo, hi):
    out = []
    if abs(a2) < 1e-18:
        if abs(a1) > 1e-18:
            out.append(-a0 / a1)
    else:
        disc = a1 * a1 - 4 * a2 * a0
        if disc >= 0.0:
            s = math.sqrt(disc)
            out += [(-a1 + s) / (2 * a2), (-a1 - s) / (2 * a2)]
    return sorted(t for t in out if lo - 1e-12 <= t <= hi + 1e-12)


def reference_hit(H, o, d, t_enter, t_exit):
    """First crossing of the bilinear surface, found cell by cell in closed form."""
    t = t_enter
    guard = 0
    while t < t_exit and guard < 4 * N:
        guard += 1
        x, z = o[0] + d[0] * t, o[2] + d[2] * t
        i = int(math.floor(x / S0 - 0.5))
        j = int(math.floor(z / S0 - 0.5))
        if not (0 <= i < N - 1 and 0 <= j < N - 1):
            return None
        tx = math.inf if d[0] == 0 else (((i + (1.5 if d[0] > 0 else 0.5)) * S0) - o[0]) / d[0]
        tz = math.inf if d[2] == 0 else (((j + (1.5 if d[2] > 0 else 0.5)) * S0) - o[2]) / d[2]
        t_cell = min(tx, tz, t_exit)
        a2, a1, a0 = cell_quadratic(H, o, d, i, j)
        r = roots_in(a2, a1, a0, t, t_cell)
        if r:
            return r[0]
        t = t_cell * RELATIVE_ADVANCE if t_cell > 0 else t_cell + 1e-9
    return None


# ---------------------------------------------------------------- the kernel
def refine(H, o, d, t0, t1, iters):
    """Bisection on [t0, t1], with a short linear scan when the ends do not bracket."""
    f = lambda t: (o[1] + d[1] * t) - surface(H, o[0] + d[0] * t, o[2] + d[2] * t)
    lo, hi = t0, t1
    flo, fhi = f(lo), f(hi)
    if flo <= 0.0:
        return lo
    if not (flo > 0.0 > fhi):
        found = False
        prev_t, prev_f = lo, flo
        for s in range(1, SCAN + 1):
            tt = lo + (hi - lo) * s / SCAN
            ft = f(tt)
            if prev_f > 0.0 > ft:
                lo, hi, flo, fhi = prev_t, tt, prev_f, ft
                found = True
                break
            prev_t, prev_f = tt, ft
        if not found:
            return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if fm > 0.0:
            lo, flo = mid, fm
        else:
            hi, fhi = mid, fm
    return 0.5 * (lo + hi)


def march(H, pyr, o, d, t_enter, t_exit, iters):
    coarsest = len(pyr) - 1
    level = coarsest
    t = max(0.0, t_enter)
    steps = 0
    while t < t_exit:
        s = S0 * (1 << level)
        x, z = o[0] + d[0] * t, o[2] + d[2] * t
        i, j = int(math.floor(x / s)), int(math.floor(z / s))
        n = pyr[level].shape[0]
        if not (0 <= i < n and 0 <= j < n):
            return None, steps, 0.0
        node_max = float(pyr[level][j, i])
        tx = math.inf if d[0] == 0 else (((i + (1 if d[0] > 0 else 0)) * s) - o[0]) / d[0]
        tz = math.inf if d[2] == 0 else (((j + (1 if d[2] > 0 else 0)) * s) - o[2]) / d[2]
        t_exit_node = min(tx, tz, t_exit)
        if min(o[1] + d[1] * t, o[1] + d[1] * t_exit_node) < node_max:
            if level == 0:
                hit = refine(H, o, d, t, t_exit_node, iters)
                if hit is not None:
                    return hit, steps, t_exit_node - t
                t = max(t, t_exit_node) * RELATIVE_ADVANCE
                level = min(level + 1, coarsest)
                steps += 1
                continue
            if d[1] < 0.0:
                t_cross = (node_max - o[1]) / d[1]
                t = max(t, t_cross)
            level -= 1
        else:
            t = max(t, t_exit_node) * RELATIVE_ADVANCE
            level = min(level + 1, coarsest)
        steps += 1
        if steps > STEP_CAP:
            return None, steps, 0.0
    return None, steps, 0.0


# ---------------------------------------------------------------- ray set
def rays(H):
    rng = random.Random(SEED)
    lo, hi = 2.0 * S0, (N - 2) * S0
    out = []

    def clip(o, d):
        """t range over the interior box, and the [mapMin, mapMax] height slab."""
        t0, t1 = 0.0, 1e9
        for ax, a, b in ((0, lo, hi), (2, lo, hi), (1, -(A + B) - 1.0, (A + B) + 1.0)):
            if abs(d[ax]) < 1e-15:
                if not (a <= o[ax] <= b):
                    return None
                continue
            ta, tb = (a - o[ax]) / d[ax], (b - o[ax]) / d[ax]
            if ta > tb:
                ta, tb = tb, ta
            t0, t1 = max(t0, ta), min(t1, tb)
        return (max(0.0, t0), t1) if t1 > max(0.0, t0) else None

    def push(o, d, kind):
        L = math.sqrt(sum(c * c for c in d))
        d = [c / L for c in d]
        c = clip(o, d)
        if c:
            out.append((o, d, c[0], c[1], kind))

    # primary rays: camera above the field, looking forward and down
    for _ in range(250):
        o = [rng.uniform(20, N - 20), rng.uniform(70, 140), rng.uniform(20, N - 20)]
        yaw = rng.uniform(0, 2 * math.pi)
        pitch = math.radians(rng.uniform(-40, -3))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "primary")
    # ascending shadow / line-of-sight rays: start on the surface, climb toward the sun
    for _ in range(200):
        x, z = rng.uniform(20, N - 20), rng.uniform(20, N - 20)
        o = [x, surface(H, x, z) + 0.05, z]
        yaw = rng.uniform(0, 2 * math.pi)
        pitch = math.radians(rng.uniform(4, 30))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "ascending")
    # grazing rays: the worst case the document names.  Started just ABOVE the
    # reconstructed surface: an origin inside the terrain is outside this kernel's contract.
    for _ in range(100):
        x, z = rng.uniform(20, N - 20), rng.uniform(20, N - 20)
        o = [x, surface(H, x, z) + 0.5, z]
        yaw = rng.uniform(0, 2 * math.pi)
        pitch = math.radians(rng.uniform(-0.8, 0.8))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "grazing")
    # straight-down picking rays
    for _ in range(50):
        o = [rng.uniform(20, N - 20), 120.0, rng.uniform(20, N - 20)]
        push(o, [0.0, -1.0, 0.0], "picking")
    return out


def main():
    H, pyr = build()

    # ---- COST: exact arithmetic over the arrays actually built.  Level 0 of the max
    # pyramid is the 3x3-DILATED base, a second full-resolution array; the heights
    # themselves are not conservative and cannot serve as it.
    base_cells = H.size
    pyr_cells = sum(int(p.size) for p in pyr)
    upper = pyr_cells - int(pyr[0].size)
    for name, bpt in (("R16", 2), ("R32F", 4)):
        print(f"COST {name}: field {bpt:.2f} bytes/cell | pyramid {pyr_cells * bpt / base_cells:.4f} "
              f"bytes/cell (level 0 {int(pyr[0].size) * bpt / base_cells:.2f} + levels 1.. "
              f"{upper * bpt / base_cells:.4f}) | field+pyramid "
              f"{(base_cells + pyr_cells) * bpt / base_cells:.4f} bytes/cell")
    print(f"COST ratios: pyramid/field={pyr_cells / base_cells:.6f}  "
          f"(field+pyramid)/field={(base_cells + pyr_cells) / base_cells:.6f}  "
          f"levels={len(pyr)} base_cells={base_cells} pyramid_cells={pyr_cells}")

    rs = rays(H)
    # An origin inside the terrain is outside this kernel's contract: refine() reports the
    # origin itself and the reference reports the surface EXIT.  Drop them, and say how many.
    def above(o, d, t0):
        return (o[1] + d[1] * t0) - surface(H, o[0] + d[0] * t0, o[2] + d[2] * t0) > 0.0
    kept = [r for r in rs if above(r[0], r[1], r[2])]
    print(f"rays: {len(rs)} generated, {len(rs) - len(kept)} dropped (origin below the "
          f"reconstructed surface), {len(kept)} used; " + ", ".join(
              f"{k}={sum(1 for r in kept if r[4] == k)}" for k in
              ("primary", "ascending", "grazing", "picking")))
    rs = kept

    ref = [reference_hit(H, o, d, t0, t1) for (o, d, t0, t1, _) in rs]
    print(f"reference: {sum(1 for r in ref if r is not None)} hits, "
          f"{sum(1 for r in ref if r is None)} misses")

    # The reference is analytic; cross-check a sample of it against a dense brute march.
    def brute(o, d, t0, t1, step=5e-4):
        f = lambda t: (o[1] + d[1] * t) - surface(H, o[0] + d[0] * t, o[2] + d[2] * t)
        t, prev = t0, f(t0)
        while t < t1:
            t2 = min(t + step, t1)
            cur = f(t2)
            if prev > 0.0 >= cur:
                lo, hi = t, t2
                for _ in range(60):
                    m = 0.5 * (lo + hi)
                    if f(m) > 0.0:
                        lo = m
                    else:
                        hi = m
                return 0.5 * (lo + hi)
            t, prev = t2, cur
        return None
    worst_ref = 0.0
    checked = 0
    for (o, d, t0, t1, _), rt in list(zip(rs, ref))[::17]:
        if rt is None:
            continue
        b = brute(o, d, t0, min(t1, rt + 2.0))
        if b is not None:
            worst_ref = max(worst_ref, abs(b - rt))
            checked += 1
    print(f"reference cross-check: {checked} rays against a 0.5 mm brute march + 60 bisections, "
          f"max disagreement {worst_ref * 1e6:.3f} um")

    for iters in BISECTIONS:
        by = {}
        missed = spurious = 0
        for (o, d, t0, t1, kind), rt in zip(rs, ref):
            ht, steps, span = march(H, pyr, o, d, t0, t1, iters)
            if rt is None and ht is None:
                continue
            if rt is not None and ht is None:
                missed += 1
            elif rt is None and ht is not None:
                spurious += 1
            else:
                cls = "column-locked" if kind == "picking" else "general"
                by.setdefault(cls, []).append((abs(ht - rt), span, steps))
        for cls in ("general", "column-locked"):
            v = by.get(cls, [])
            if not v:
                continue
            errs = sorted(e for e, _, _ in v)
            n = len(errs)
            spans = [sp for _, sp, _ in v]
            bound = max(sp / 2 ** iters for sp in spans)
            print(f"ERROR k={iters} {cls:13s}: n={n} missed={missed} spurious={spurious} "
                  f"max={errs[-1] * 1000:8.2f} mm  p99={errs[int(0.99 * (n - 1))] * 1000:8.2f} mm  "
                  f"mean={sum(errs) / n * 1000:7.2f} mm | level-0 span max={max(spans):8.2f} m "
                  f"median={sorted(spans)[n // 2]:.3f} m | span/2^k bound={bound * 1000:.2f} mm "
                  f"| max_steps={max(st for _, _, st in v)}")


if __name__ == "__main__":
    main()
