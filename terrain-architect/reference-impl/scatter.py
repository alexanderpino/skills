"""Object distribution / scatter (07-scatter.md). Placement, not plant geometry.

Where each instance goes and what it is — never the trunk/leaf/boulder mesh. Bridson
Poisson-disk sampling (the O(N) grid method, with the details that are usually wrong: cell
size r/sqrt(2), a 5x5 neighbour check, an area-uniform annulus), variable density by
rejection, Ulichney (1993) void-and-cluster blue-noise tiles (the chapter's recommendation for
ground cover and its "Preferred" answer to tiling), a tileable jittered grid for dense ground
cover, and the rule-based layer that gates instances on the terrain (slope, height, water) —
variation from the environment, not from random().
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


# --------------------------------------------------------------------------- #
# ULICHNEY (1993) VOID-AND-CLUSTER TILES — 07:139, :149, :175, :189, :300, :311
#
# `07` names these in six places and calls them "Preferred" for tiling (:175) and the
# "Recommendation for terrain" for ground cover (:149). Five are recommendations; :189 is the
# hex-grid crossref saying the sampler itself is untouched by the lattice, which is true of this
# one — `ulichney_scatter` returns world coordinates and never sees a grid type.
#
# What the chapter specifies is a
# PROPERTY, not an algorithm: "Precompute a tileable blue-noise mask; threshold it against the
# density map. O(1) per cell, trivially tileable, no seams, no state." (:139) and "no problem
# exists; the mask is tileable by construction" (:175). The algorithm below is Ulichney's
# original void-and-cluster method, which is what earns that property.
#
# WHY EVERY FILTER HERE WRAPS. Tileability is not a post-hoc repair here — it is the direct
# consequence of doing all of the neighbourhood arithmetic on a torus. A pixel one column from
# the right edge sees the left edge as its neighbour while the array is being built, so when the
# finished mask is tiled edge-to-edge the seam is an interior column that was already accounted
# for. Filter without wrapping and the border pixels look like voids (nothing on the far side
# contributes to their density), the algorithm packs the borders, and tiling produces exactly the
# doubled-density seam that :156 says a per-tile Poisson run produces.
#
# The wrap is a MINIMUM-IMAGE Gaussian evaluated per moved pixel (`_kernel_at`), not an FFT
# convolution. Both compute the same circular convolution; the shifted-kernel form was chosen for
# two reasons. It lets the filtered field be updated INCREMENTALLY — one pixel changes, so add or
# subtract one shifted kernel — which is O(n^2) per step instead of an O(n^2 log n) transform per
# step, and makes the whole generation sub-second at the tile sizes anyone ships. And it puts the
# wraparound in two readable lines that a mutation can reach, rather than inside a library call
# or inside a precomputed kernel image (a precomputed image indexed modularly is circular
# whatever the image holds, so that arrangement leaves the tileability guard unfalsifiable).
#
# The toroidal filter also collapses Ulichney's phases II and III into one loop. Phase III is
# stated in terms of the tightest cluster of the MINORITY, which past the half-way point is the
# zeros; but for a circular convolution with kernel sum S, filter(1 - P) == S - filter(P)
# exactly, so "the zero of maximal zero-density" and "the zero of minimal one-density" are the
# same pixel. One loop, and the identity is checked by test_scatter.py rather than assumed.
# --------------------------------------------------------------------------- #

def _kernel_at(n, sigma, idx):
    """The Gaussian of `sigma` centred on flat index `idx` over the n x n grid, ON A TORUS.

    The two MINIMUM-IMAGE lines are the wraparound, and they are the only place it lives: an
    offset larger than half a tile is replaced by the shorter way round the edge, so a pixel in
    the first column and one in the last are neighbours. Delete them and this is the same
    Gaussian on a bounded rectangle — still symmetric, still terminating, no longer circular, and
    the mask it builds is no longer tileable. That is the mutation
    `registers/mutation-proofs.wave6-ulichney.tsv` fires the seam guard with.

    Evaluated directly rather than looked up in a precomputed kernel image, deliberately: a
    precomputed image indexed modularly is circular no matter what the image holds, so the
    property this whole atom rests on would have had no reachable failure mode at all.
    """
    d = np.arange(n)
    dy = d - int(idx) // n
    dx = d - int(idx) % n
    dy = dy - n * np.round(dy / n)                   # minimum image: the wrap
    dx = dx - n * np.round(dx / n)                   # minimum image: the wrap
    return np.exp(-(dy[:, None] ** 2 + dx[None, :] ** 2) / (2.0 * float(sigma) ** 2))


def _tightest_cluster(filtered, ones):
    """The minority pixel of MAXIMUM filtered density — Ulichney's tightest cluster."""
    return int(np.where(ones, filtered, -np.inf).argmax())


def _largest_void(filtered, ones):
    """The non-minority pixel of MINIMUM filtered density — Ulichney's largest void."""
    return int(np.where(ones, np.inf, filtered).argmin())


def _initial_pattern(n, sigma, seed, count):
    """Ulichney's initial binary pattern: `count` random pixels, relaxed to blue noise.

    Move the pixel of the tightest cluster into the largest void, repeatedly. The standard
    termination is that the move would undo itself: if the largest void after the removal IS the
    pixel just vacated, putting it back returns the pattern to a state already seen, so the
    relaxation has converged and the loop stops.
    """
    rng = np.random.default_rng(seed)
    ones = np.zeros(n * n, dtype=bool)
    ones[rng.choice(n * n, size=int(count), replace=False)] = True
    filtered = np.zeros((n, n), dtype=np.float64)
    for idx in np.flatnonzero(ones):
        filtered += _kernel_at(n, sigma, idx)
    while True:
        c = _tightest_cluster(filtered.ravel(), ones)
        ones[c] = False
        filtered -= _kernel_at(n, sigma, c)
        v = _largest_void(filtered.ravel(), ones)
        if v == c:                                   # the move undoes itself -> converged
            ones[c] = True
            filtered += _kernel_at(n, sigma, c)
            return ones, filtered
        ones[v] = True
        filtered += _kernel_at(n, sigma, v)


def void_and_cluster_rank(n=32, sigma=1.5, seed=0, initial_fraction=0.1):
    """Ulichney 1993 void-and-cluster dither array: an (n, n) int64 PERMUTATION of 0..n*n-1.

    `07:139` / `07:175`. Rank r is the order in which pixel r would be turned on as the density
    rises, so thresholding `rank < d * n * n` yields a blue-noise point set of density d, for
    every d at once, and the result is tileable because all of the arithmetic below is toroidal.

    Three phases, all sharing one incrementally-maintained wrapped Gaussian density:
      * initial pattern  - `initial_fraction` of the pixels, relaxed (`_initial_pattern`);
      * phase I          - remove from the tightest cluster, ranking DOWN to 0;
      * phase II/III     - insert into the largest void, ranking UP to n*n-1 (one loop; see the
                           block comment above for why the toroidal filter merges II and III).

    `sigma = 1.5` and an initial minority of about a tenth of the pixels are Ulichney's values.
    Neither is load-bearing for the blue-noise property — the mask stays blue over a wide range,
    which is why both are the DECOYS in the mutation register, not mutations.
    """
    n = int(n)
    if n < 4:
        raise ValueError("n must be at least 4 for a usable dither array")
    count = int(max(1, min(n * n - 1, round(float(initial_fraction) * n * n))))
    ones0, filt0 = _initial_pattern(n, sigma, seed, count)
    rank = np.full(n * n, -1, dtype=np.int64)

    ones = ones0.copy()
    filtered = filt0.copy()
    for r in range(count - 1, -1, -1):               # PHASE I
        c = _tightest_cluster(filtered.ravel(), ones)
        ones[c] = False
        filtered -= _kernel_at(n, sigma, c)
        rank[c] = r

    ones = ones0.copy()
    filtered = filt0.copy()
    for r in range(count, n * n):                    # PHASE II / III
        v = _largest_void(filtered.ravel(), ones)
        ones[v] = True
        filtered += _kernel_at(n, sigma, v)
        rank[v] = r
    return rank.reshape(n, n)


def void_and_cluster_mask(n=32, sigma=1.5, seed=0, initial_fraction=0.1):
    """The Ulichney threshold matrix: `void_and_cluster_rank(...) / n**2`, in [0, 1).

    This is the object `07:139` calls "a tileable blue-noise mask": compare it against a density
    in [0, 1] and keep the cells that come out below. O(1) per cell, no state, no seams.
    """
    n = int(n)
    return void_and_cluster_rank(n, sigma, seed, initial_fraction).astype(np.float64) / (n * n)


def ulichney_scatter(width, height, cellsize, density, mask=None, seed=0,
                     tile=32, sigma=1.5):
    """Ground-cover scatter by thresholding an Ulichney tile against a density map (07:149).

    The chapter's recommendation for grass, rocks, debris and pebble beaches (`07:300`, `07:311`)
    — high count, per-cell, tileable. Cell (i, j) keeps a point iff `mask[i % tile, j % tile] <
    density`; the modulo is the whole tiling story, so a sub-region of the domain is bit-identical
    to the same cells of the whole (`07:175`, "no problem exists").

    `density` is a scalar in [0, 1] or a 2-D map, which is resampled to the cell grid by nearest
    neighbour. It is NOT a per-point callable: `07:139`'s claim is O(1) per cell at grass counts,
    and a Python callable per cell is not that. Returns (N, 2) cell centres in metres, (x, y).
    """
    gw = max(1, int(width // cellsize))
    gh = max(1, int(height // cellsize))
    if mask is None:
        mask = void_and_cluster_mask(tile, sigma=sigma, seed=seed)
    mask = np.asarray(mask, dtype=np.float64)
    tn = mask.shape[0]
    ii, jj = np.meshgrid(np.arange(gh), np.arange(gw), indexing="ij")
    thresh = mask[ii % tn, jj % tn]

    d = np.asarray(density, dtype=np.float64)
    if d.ndim == 0:
        dfield = np.full((gh, gw), float(d))
    else:
        si = np.minimum((ii * d.shape[0]) // gh, d.shape[0] - 1)
        sj = np.minimum((jj * d.shape[1]) // gw, d.shape[1] - 1)
        dfield = d[si, sj]

    keep = thresh < dfield
    y = (ii[keep] + 0.5) * cellsize
    x = (jj[keep] + 0.5) * cellsize
    return np.stack([x, y], axis=1)
