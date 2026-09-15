#!/usr/bin/env python3
"""Rig for gaia/references/gpu-driven-culling.md.

TWO independent things, both pure arithmetic in CPython. NEITHER is a GPU measurement.

PART 1 -- HiZ footprint-mip test, exact software model.
  Ground truth is computed by brute force over every pixel of the query rect, so the
  "error" reported is the difference between the four-corner-tap HiZ test and the
  answer a perfect occlusion query would give on the SAME depth buffer. It is NOT a
  claim about any real renderer's kill rate, and it is not a frame cost.

PART 2 -- HiZ pyramid memory, closed-form.
  The mip-chain sum for one R32_FLOAT depth pyramid. Arithmetic over the mip rule,
  NOT a measured allocation: a driver aligns and pads, so a real allocation is >= this.

Standard Z throughout (near = 0, far = 1) with a max-depth reduce, matching the
document's worked example. Power-of-two dimensions, so the odd-dimension edge case of
bullet 2 is absent and mip CHOICE is the only variable under test.
"""
import random

SEED = 20260910
N_TRIALS = 20000
DIM = 1024          # power of two: isolates mip choice from the NPOT edge-texel bug
SKY = 1.0


def build_scene(rng):
    depth = [[SKY] * DIM for _ in range(DIM)]
    for _ in range(60):                       # occluder slabs: ridges, walls, buildings
        w = rng.randint(16, 320)
        h = rng.randint(16, 320)
        x0 = rng.randint(0, DIM - w)
        y0 = rng.randint(0, DIM - h)
        z = rng.uniform(0.10, 0.70)
        for y in range(y0, y0 + h):
            row = depth[y]
            for x in range(x0, x0 + w):
                if z < row[x]:
                    row[x] = z                # nearest occluder wins, as a depth buffer does
    return depth


def build_pyramid(depth):
    """max-depth reduce == farthest depth in the footprint == standard-Z convention."""
    mips = [depth]
    cur, dim = depth, DIM
    while dim > 1:
        nd = dim // 2
        nxt = [[0.0] * nd for _ in range(nd)]
        for y in range(nd):
            a, b = cur[2 * y], cur[2 * y + 1]
            row = nxt[y]
            for x in range(nd):
                row[x] = max(a[2 * x], a[2 * x + 1], b[2 * x], b[2 * x + 1])
        mips.append(nxt)
        cur, dim = nxt, nd
    return mips


def rule_mip(w, h):
    """The document's rule: larger dimension, log2 rounded up -> one texel spans the rect."""
    m, span = 0, 1
    while span < max(w, h):
        span *= 2
        m += 1
    return m


def sampled_max(mips, m, x0, y0, w, h):
    """Four corner taps at mip m, exactly as a shader would issue them."""
    m = max(0, min(m, len(mips) - 1))
    mip = mips[m]
    n = len(mip)
    x1, y1 = x0 + w - 1, y0 + h - 1
    tx0, tx1 = min(x0 >> m, n - 1), min(x1 >> m, n - 1)
    ty0, ty1 = min(y0 >> m, n - 1), min(y1 >> m, n - 1)
    return max(mip[ty0][tx0], mip[ty0][tx1], mip[ty1][tx0], mip[ty1][tx1])


def true_max(depth, x0, y0, w, h):
    return max(max(depth[y][x0:x0 + w]) for y in range(y0, y0 + h))


def part1():
    rng = random.Random(SEED)
    depth = build_scene(rng)
    mips = build_pyramid(depth)

    # offset -> [false culls, missed culls, trials, drawable trials]
    tally = {-1: [0, 0], 0: [0, 0], 1: [0, 0]}
    drawable = occluded = 0

    for _ in range(N_TRIALS):
        w = rng.randint(4, 256)
        h = rng.randint(4, 256)
        x0 = rng.randint(0, DIM - w)
        y0 = rng.randint(0, DIM - h)
        z_near = rng.uniform(0.05, 0.95)

        t_max = true_max(depth, x0, y0, w, h)
        truth_cull = z_near > t_max            # every pixel has a nearer occluder
        if truth_cull:
            occluded += 1
        else:
            drawable += 1

        base = rule_mip(w, h)
        for off in (-1, 0, 1):
            s_max = sampled_max(mips, base + off, x0, y0, w, h)
            test_cull = z_near > s_max
            if test_cull and not truth_cull:
                tally[off][0] += 1             # VISIBLE GEOMETRY CULLED
            elif truth_cull and not test_cull:
                tally[off][1] += 1             # cull silently lost

    print(f"PART 1  HiZ footprint mip, {N_TRIALS} trials, seed {SEED}, {DIM}x{DIM} "
          f"standard-Z max-depth pyramid")
    print(f"  ground truth: {drawable} trials must draw, {occluded} are genuinely occluded")
    for off, name in ((-1, "one level FINER  (rule - 1)"),
                      (0, "THE RULE ceil(log2)     "),
                      (1, "one level COARSER (rule + 1)")):
        fc, mc = tally[off]
        print(f"  {name}: wrongly culled {fc:5d} of {drawable} drawable "
              f"({100.0 * fc / drawable:6.2f}%)   cull lost {mc:5d} of {occluded} "
              f"({100.0 * mc / occluded:6.2f}%)")


def chain_bytes(w, h, bpp):
    total = 0
    while True:
        total += w * h * bpp
        if w == 1 and h == 1:
            return total
        w, h = max(1, w // 2), max(1, h // 2)


def part2():
    print("PART 2  HiZ pyramid memory, R32_FLOAT, full mip chain (closed form, not measured)")
    for w, h in ((1920, 1080), (2560, 1440), (3840, 2160)):
        base = w * h * 4
        chain = chain_bytes(w, h, 4)
        print(f"  {w}x{h}: base {base / 1e6:7.3f} MB   full chain {chain / 1e6:7.3f} MB "
              f"(x{chain / base:.4f})")


if __name__ == "__main__":
    part1()
    print()
    part2()
