"""tiled-streaming.md -- how big is the parent-residency overhead, really?

The page claims: "refinement is atomic per parent, so the cut is whole sibling quads and its
distinct parents number a quarter of it -- at the constant per-tile size of part 1, at most
+25% of drawn bytes."

This is pure combinatorics over quadtrees. No timing, no GPU, no wall clock: the quantity is
  overhead = (number of DISTINCT parents of cut tiles) / (number of cut tiles)
for a complete cut = the leaf set of a quadtree refined atomically (4 children at a time).
Tiles are constant size (part 1), so tile counts ARE byte fractions.

Three independent probes:
  A  exhaustive enumeration of every refinement shape up to N internal nodes -> the true maximum
  B  the closed form for the family that attains the maximum
  C  distance-based camera-centred cuts, i.e. the shape this architecture actually produces,
     swept over threshold and camera position -> what a real streamer sees

Deterministic. No RNG is used anywhere, so there is no seed to report and re-runs are bit-identical.
"""
import itertools
import math

# ---------------------------------------------------------------- A: exhaustive

def shapes(max_internal):
    """Yield every quadtree refinement shape with 1..max_internal internal nodes.

    A shape is a nested tuple: () is a leaf, (c0,c1,c2,c3) is an internal node.
    Refinement is atomic: an internal node always has exactly 4 children.
    """
    cache = {0: [()]}

    def gen(n):
        if n in cache:
            return cache[n]
        out = []
        # this node is internal (costs 1), distribute n-1 internal nodes over 4 children
        for a in range(n):
            for b in range(n - a):
                for c in range(n - a - b):
                    d = n - 1 - a - b - c
                    if d < 0:
                        continue
                    for ca in gen(a):
                        for cb in gen(b):
                            for cc in gen(c):
                                for cd in gen(d):
                                    out.append((ca, cb, cc, cd))
        cache[n] = out
        return out

    for n in range(1, max_internal + 1):
        for s in gen(n):
            yield n, s


def leaves_and_parents(shape):
    """(#leaves, #distinct parents of leaves) for a refinement shape."""
    leaves = 0
    parents = 0
    stack = [shape]
    while stack:
        node = stack.pop()
        if node == ():
            continue
        has_leaf_child = False
        for ch in node:
            if ch == ():
                leaves += 1
                has_leaf_child = True
            else:
                stack.append(ch)
        if has_leaf_child:
            parents += 1
    return leaves, parents


def probe_a(max_internal=7):
    best = (0.0, None, 0, 0)
    worst = (1.0, None, 0, 0)
    mixed_at_quarter = []
    for n, s in shapes(max_internal):
        L, P = leaves_and_parents(s)
        r = P / L
        if r > best[0]:
            best = (r, s, L, P)
        if r < worst[0]:
            worst = (r, s, L, P)
        # the exact condition: ratio is 1/4 iff no internal node MIXES leaf and refined children
        if abs(r - 0.25) < 1e-12 and has_mixed_node(s):
            mixed_at_quarter.append(s)
    return best, worst, mixed_at_quarter


def has_mixed_node(shape):
    """True if some internal node has both a leaf child and a refined child."""
    stack = [shape]
    while stack:
        node = stack.pop()
        if node == ():
            continue
        kinds = {ch == () for ch in node}
        if len(kinds) == 2:
            return True
        stack.extend(ch for ch in node if ch != ())
    return False


def probe_a_mixed(max_internal=7):
    """Every shape that HAS a mixed node: is its ratio always strictly above 1/4?"""
    lo = 1.0
    n_mixed = 0
    for n, s in shapes(max_internal):
        if not has_mixed_node(s):
            continue
        n_mixed += 1
        L, P = leaves_and_parents(s)
        lo = min(lo, P / L)
    return n_mixed, lo


# ---------------------------------------------------------------- B: closed form

def probe_b(depths=(1, 2, 3, 5, 10, 100, 10000)):
    """Caterpillar: refine exactly one child at every level. I internal nodes, L = 3I+1 leaves,
    and EVERY internal node keeps 3 leaf children, so P = I."""
    return [(i, 3 * i + 1, i, i / (3 * i + 1)) for i in depths]


# ---------------------------------------------------------------- C: distance-based cuts

def distance_cut(cx, cy, k, max_depth):
    """Camera-centred cut over the unit square. Refine a node while size/dist > k, to max_depth.

    size/dist is the standard screen-space-error proxy (rho = e*K/d with e proportional to the
    node's sample spacing); k plays the role of tau/(e0*K). Returns (leaves, distinct parents).
    """
    leaves = 0
    parents = 0
    stack = [(0.0, 0.0, 1.0, 0)]           # x, y, size, depth
    while stack:
        x, y, s, d = stack.pop()
        # does this node refine?
        kids = [(x, y, s / 2, d + 1), (x + s / 2, y, s / 2, d + 1),
                (x, y + s / 2, s / 2, d + 1), (x + s / 2, y + s / 2, s / 2, d + 1)]
        has_leaf_child = False
        for kx, ky, ks, kd in kids:
            # distance from camera to the child's centre, floored at half a tile
            dx = max(abs(cx - (kx + ks / 2)) - ks / 2, 0.0)
            dy = max(abs(cy - (ky + ks / 2)) - ks / 2, 0.0)
            dist = max(math.hypot(dx, dy), 1e-9)
            if kd < max_depth and (ks / dist) > k:
                stack.append((kx, ky, ks, kd))
            else:
                leaves += 1
                has_leaf_child = True
        if has_leaf_child:
            parents += 1
    return leaves, parents


def probe_c():
    rows = []
    cams = [(0.5, 0.5), (0.5, 0.0), (0.0, 0.0), (0.37, 0.61), (0.5, 0.25), (0.125, 0.5)]
    for k in (0.9, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1):
        for max_depth in (6, 8, 10):
            for cx, cy in cams:
                L, P = distance_cut(cx, cy, k, max_depth)
                if L >= 16:                      # ignore degenerate near-root cuts
                    rows.append((k, max_depth, cx, cy, L, P, P / L))
    return rows


if __name__ == "__main__":
    print("A  exhaustive over every refinement shape with <= 7 internal nodes")
    best, worst, mixed_at_quarter = probe_a(7)
    r, shape, L, P = best
    print(f"   max distinct-parents/cut = {P}/{L} = {100*r:.2f}%   shape={shape}")
    print(f"   min distinct-parents/cut = {worst[3]}/{worst[2]} = {100*worst[0]:.2f}%")
    print(f"   the page's claim is 25.00%; exceeded: {r > 0.25}")
    n_mixed, lo = probe_a_mixed(7)
    print(f"   shapes with a node MIXING leaf and refined children: {n_mixed}; "
          f"their min ratio = {100*lo:.4f}%")
    print(f"   shapes at exactly 25% that contain a mixed node: {len(mixed_at_quarter)} "
          f"(expect 0 -- 1/4 holds iff no parent mixes)")
    print()
    print("B  caterpillar family (refine one child per level): I internal, L=3I+1 leaves, P=I")
    for i, Lf, Pf, ratio in probe_b():
        print(f"   I={i:<6} L={Lf:<6} P={Pf:<6} overhead={100*ratio:.3f}%")
    print(f"   limit = 1/3 = {100/3:.3f}%")
    print()
    print("C  distance-based camera-centred cuts (the shape this architecture produces)")
    rows = probe_c()
    ratios = sorted(x[6] for x in rows)
    n = len(rows)
    print(f"   {n} cuts, cut sizes {min(x[4] for x in rows)}..{max(x[4] for x in rows)} tiles")
    print(f"   overhead  min={100*ratios[0]:.2f}%  median={100*ratios[n//2]:.2f}%  "
          f"max={100*ratios[-1]:.2f}%")
    over = [x for x in rows if x[6] > 0.25]
    print(f"   cuts above the page's 25% bound: {len(over)}/{n} = {100*len(over)/n:.1f}%")
    worst = max(rows, key=lambda x: x[6])
    print(f"   worst: k={worst[0]} depth={worst[1]} cam=({worst[2]},{worst[3]}) "
          f"L={worst[4]} P={worst[5]} -> {100*worst[6]:.2f}%")
