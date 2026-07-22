"""Object distribution / scatter (07-scatter.md). Placement, not plant geometry.

Where each instance goes and what it is — never the trunk/leaf/boulder mesh. Bridson
Poisson-disk sampling (the O(N) grid method, with the details that are usually wrong: cell
size r/sqrt(2), a 5x5 neighbour check, an area-uniform annulus), variable density by
rejection, a tileable jittered grid for dense ground cover, and the rule-based layer that
gates instances on the terrain (slope, height, water) — variation from the environment, not
from random().
"""
import numpy as np


def _hash01(ix, iy, seed, salt=0):
    """Deterministic value in [0,1) per integer cell — for tileable jitter (the wrap is intended)."""
    mask = np.uint64(0xFFFFFFFFFFFFFFFF)
    s = np.uint64((int(seed) * 0x9E3779B97F4A7C15 + int(salt) * 0x632BE59BD9B4E019) & int(mask))
    ix_u = np.asarray(ix).astype(np.int64).astype(np.uint64)
    iy_u = np.asarray(iy).astype(np.int64).astype(np.uint64)
    with np.errstate(over="ignore"):
        h = (ix_u * np.uint64(0x9E3779B97F4A7C15)
             ^ iy_u * np.uint64(0xC2B2AE3D27D4EB4F) ^ s) & mask
        h ^= h >> np.uint64(33)
        h *= np.uint64(0xFF51AFD7ED558CCD)
        h ^= h >> np.uint64(33)
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def poisson_disk(width, height, r, seed=0, k=30):
    """Bridson 2007 Poisson-disk sampling of [0,width) x [0,height). Returns an (N,2) array of
    (x, y). Guarantees every pair is at least `r` apart (the blue-noise property) while staying
    maximal. cellSize = r/sqrt(2) (<=1 sample/cell); a 5x5 neighbour search (a conflict can be 2
    cells away); an AREA-uniform annulus draw (the naive r*(1+rand) biases toward clumping)."""
    rng = np.random.default_rng(seed)
    cell = r / np.sqrt(2.0)
    gw = int(np.ceil(width / cell))
    gh = int(np.ceil(height / cell))
    grid = np.full((gh, gw), -1, dtype=np.int64)
    samples = []
    active = []

    def gc(p):
        return min(int(p[1] / cell), gh - 1), min(int(p[0] / cell), gw - 1)

    def far_enough(p):
        ci, cj = gc(p)
        for i in range(max(0, ci - 2), min(gh, ci + 3)):
            for j in range(max(0, cj - 2), min(gw, cj + 3)):
                s = grid[i, j]
                if s >= 0 and np.hypot(*(samples[s] - p)) < r:
                    return False
        return True

    p0 = np.array([rng.uniform(0, width), rng.uniform(0, height)])
    samples.append(p0)
    active.append(0)
    grid[gc(p0)] = 0
    while active:
        idx = active[int(rng.integers(len(active)))]
        found = False
        for _ in range(int(k)):
            rad = r * np.sqrt(1.0 + 3.0 * rng.random())     # area-uniform over [r, 2r]
            ang = 2.0 * np.pi * rng.random()
            p = samples[idx] + rad * np.array([np.cos(ang), np.sin(ang)])
            if not (0.0 <= p[0] < width and 0.0 <= p[1] < height):
                continue
            if far_enough(p):
                samples.append(p)
                active.append(len(samples) - 1)
                grid[gc(p)] = len(samples) - 1
                found = True
                break
        if not found:
            active.remove(idx)
    return np.array(samples)


def scatter_by_density(width, height, density_fn, r_min, seed=0, max_density=1.0):
    """Variable-density scatter by rejection (07, approach A): sample at the minimum spacing,
    then keep p with probability density_fn(p)/max_density. Keeps Bridson unmodified; loses the
    blue-noise property in the sparse regions (fine for trees, not for low-density grass)."""
    pts = poisson_disk(width, height, r_min, seed)
    rng = np.random.default_rng(int(seed) + 1)
    keep = [p for p in pts if rng.random() < density_fn(p) / max_density]
    return np.array(keep) if keep else np.empty((0, 2))


def jittered_grid(width, height, spacing, seed=0, jitter=1.0):
    """Stratified/jittered grid (07, tiling option 2): one point per cell, offset by a
    per-cell hash. Deterministic and seamlessly tileable by construction — not true blue noise,
    but for dense ground cover nobody can tell. Returns (N,2) of (x, y)."""
    gw = max(1, int(width // spacing))
    gh = max(1, int(height // spacing))
    jj, ii = np.meshgrid(np.arange(gw), np.arange(gh))
    hx = _hash01(jj, ii, seed, 1)
    hy = _hash01(jj, ii, seed, 2)
    x = (jj + 0.5 + jitter * (hx - 0.5)) * spacing
    y = (ii + 0.5 + jitter * (hy - 0.5)) * spacing
    return np.stack([x.ravel(), y.ravel()], axis=1)


def rule_based(points, *, height_fn=None, slope_fn=None, river_fn=None,
               max_slope_tan=np.tan(np.radians(35.0)), tree_line=np.inf):
    """The layer above the sampler (07): the positions come from the sampler, the rules decide
    what survives. Hard gates — no instance on a cliff, above the treeline, or in the water."""
    keep = []
    for p in points:
        if slope_fn is not None and slope_fn(p) > max_slope_tan:
            continue
        if height_fn is not None and height_fn(p) > tree_line:
            continue
        if river_fn is not None and river_fn(p) > 0.5:
            continue
        keep.append(p)
    return np.array(keep) if keep else np.empty((0, 2))


def sample_field(field, points, cellsize=1.0):
    """Nearest-cell lookup of a raster `field` (H,W) at world-metre `points` (x, y). The bridge
    from the analysis rasters (06) to the scatter gates above."""
    field = np.asarray(field)
    n, m = field.shape
    out = np.empty(len(points))
    for idx, (x, y) in enumerate(points):
        j = min(max(int(round(x / cellsize)), 0), m - 1)
        i = min(max(int(round(y / cellsize)), 0), n - 1)
        out[idx] = field[i, j]
    return out
