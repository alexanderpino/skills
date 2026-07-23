"""Primitives, operators, filters & warps (10-primitives-ops-filters.md).

The "boring" nodes — no papers, which is exactly why they ship broken. This module is the
toolbox the graph draws on: SDF primitives, crease-free smooth min/max, edge-preserving
filters, and greyscale morphology, each held to the property the chapter says it must have.

Two deliberate choices from the chapter:
  * there is NO `normalize` here — it destroys world-space units and makes the graph
    non-composable (a guaranteed seam). Use `remap(a, known_lo, known_hi)` with constants.
  * `smin`/`smax` carry the `k·h·(1−h)` term (world-space `k`), so combining shapes leaves no
    crease for a curvature mask to trip on.

Filter sigmas/radii are in CELLS here; convert from world metres (`sigma_m / cellSize`) at the
call site, per the chapter's resolution rule.
"""
import numpy as np


def _smoothstep(lo, hi, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------- #
# SDF primitives (Frisken et al. 2000; Quilez catalogue). Operate on coordinates.
# --------------------------------------------------------------------------- #
def sd_circle(px, py, r):
    """Signed distance to a circle: |p| - r. Negative inside, 0 on the rim, positive out."""
    return np.hypot(np.asarray(px, dtype=np.float64), np.asarray(py, dtype=np.float64)) - r


def sd_box(px, py, bx, by):
    """Signed distance to an axis-aligned box of half-extents (bx, by)."""
    dx = np.abs(np.asarray(px, dtype=np.float64)) - bx
    dy = np.abs(np.asarray(py, dtype=np.float64)) - by
    return (np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
            + np.minimum(np.maximum(dx, dy), 0.0))


def sd_convex_polygon(px, py, normals, offsets):
    """Signed distance to a convex polygon given as the intersection of half-planes:
    ``max_k( n_k · p - d_k )`` for outward unit normals ``n_k`` and offsets ``d_k`` (distance from
    the origin along ``n_k``). Negative inside, 0 on an edge, positive outside; exact on the faces
    (the generalisation of `sd_box`, which is this at four axis-aligned normals). This is the
    grounded primitive behind fault/joint-bounded landforms — a butte or mesa is a convex block
    bounded by a couple of near-orthogonal joint sets (place it, then combine with `smax`/`np.maximum`
    and erode). `normals` is a sequence of (nx, ny) unit vectors; `offsets` a matching sequence of
    scalars."""
    px = np.asarray(px, dtype=np.float64)
    py = np.asarray(py, dtype=np.float64)
    d = np.full(np.broadcast(px, py).shape, -np.inf)
    for (nx, ny), dk in zip(normals, offsets):
        d = np.maximum(d, nx * px + ny * py - dk)
    return d


def sd_segment(px, py, ax, ay, bx, by):
    """Distance to the segment a->b — the workhorse: a spline is a polyline, and distance to
    it is the min over segments. Remap the field with a profile to cut a valley/ridge/road."""
    pax, pay = px - ax, py - ay
    bax, bay = bx - ax, by - ay
    h = np.clip((pax * bax + pay * bay) / (bax * bax + bay * bay + 1e-30), 0.0, 1.0)
    return np.hypot(pax - bax * h, pay - bay * h)


def radial_gradient(px, py, radius):
    """1 at the centre falling to 0 at `radius`, with a smoothstep falloff (a linear one has a
    C1 crease ring at the rim under any lighting)."""
    return 1.0 - _smoothstep(0.0, radius, np.hypot(px, py))


def cone(px, py, radius, height=1.0):
    """A cone primitive. Has creases at apex and base — smoothstep it or run thermal after."""
    return height * np.clip(1.0 - np.hypot(px, py) / radius, 0.0, None)


# --------------------------------------------------------------------------- #
# heightfield operators
# --------------------------------------------------------------------------- #
def blend(a, b, t):
    """lerp — the honest masking op. Use `blend(base_level, height, mask)` to flatten, NOT
    `height * mask` (which scales absolute elevation, moving the terrain down, not flattening)."""
    return a + (b - a) * t


def remap(a, lo, hi, out_lo=0.0, out_hi=1.0):
    """Map [lo, hi] -> [out_lo, out_hi] with lo/hi you WROTE DOWN. The composable replacement
    for `normalize`, whose min/max depend on the evaluation and therefore seam."""
    return out_lo + (np.asarray(a, dtype=np.float64) - lo) * (out_hi - out_lo) / (hi - lo)


def smin(a, b, k):
    """Quilez polynomial smooth min. `k` = blend width in the SAME units as a, b (metres).
    The -k·h·(1-h) term is what makes it smooth (and dips it just below the hard min);
    k -> 0 recovers min. smin(a,b,k) <= min(a,b) always."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-np.asarray(a, dtype=np.float64), -np.asarray(b, dtype=np.float64), k)


# --------------------------------------------------------------------------- #
# filters  (radii/sigmas in CELLS)
# --------------------------------------------------------------------------- #
def _conv1d(h, kernel, axis):
    r = len(kernel) // 2
    pad = [(r, r) if a == axis else (0, 0) for a in range(h.ndim)]
    hp = np.pad(h, pad, mode="reflect")
    out = np.zeros_like(h, dtype=np.float64)
    for i, w in enumerate(kernel):
        sl = [slice(None)] * h.ndim
        sl[axis] = slice(i, i + h.shape[axis])
        out += w * hp[tuple(sl)]
    return out


def gaussian(h, sigma):
    """Separable Gaussian blur (two 1D passes). Preserves the mean; blurs everything, INCLUDING
    ridges and cliffs — the chapter's point is that it's the wrong default for terrain. Prefer
    bilateral/guided/median below; this is here as the baseline they beat."""
    h = np.asarray(h, dtype=np.float64)
    r = max(1, int(np.ceil(3 * sigma)))
    x = np.arange(-r, r + 1)
    k = np.exp(-(x * x) / (2 * sigma * sigma))
    k /= k.sum()
    return _conv1d(_conv1d(h, k, 0), k, 1)


def box_filter(h, r):
    """Uniform (mean) filter over a (2r+1) window, separable. The O(1) building block guided
    filtering is made of."""
    h = np.asarray(h, dtype=np.float64)
    k = np.ones(2 * r + 1) / (2 * r + 1)
    return _conv1d(_conv1d(h, k, 0), k, 1)


def _window_stack(h, r):
    n, m = h.shape
    hp = np.pad(h, r, mode="reflect")
    return np.stack([hp[i:i + n, j:j + m]
                     for i in range(2 * r + 1) for j in range(2 * r + 1)], axis=0)


def median(h, r=1):
    """Median of the (2r+1)^2 window. Removes SPIKES (salt-and-pepper) while preserving step
    edges exactly — not a smoother; it removes outliers, not noise."""
    return np.median(_window_stack(np.asarray(h, dtype=np.float64), r), axis=0)


def bilateral(h, sigma_s, sigma_r):
    """Edge-preserving smoothing (Tomasi & Manduchi 1998): weight neighbours by spatial AND
    value distance. `sigma_r` is in METRES of height — set it above the noise and below the
    smallest real cliff, and hillslope noise smooths while cliffs stay razor-sharp."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    r = max(1, int(round(2 * sigma_s)))
    hp = np.pad(h, r, mode="reflect")
    num = np.zeros_like(h)
    den = np.zeros_like(h)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            nb = hp[r + di:r + di + n, r + dj:r + dj + m]
            ws = np.exp(-(di * di + dj * dj) / (2 * sigma_s * sigma_s))
            wr = np.exp(-((nb - h) ** 2) / (2 * sigma_r * sigma_r))
            w = ws * wr
            num += w * nb
            den += w
    return num / den


def guided_filter(p, guide=None, r=2, eps=1e-3):
    """He, Sun & Tang 2010: edge-preserving, O(1) per cell (box filters only), no bilateral
    gradient-reversal. `eps` plays sigma_r^2 — the variance below which a region is 'flat'.
    Pass a separate `guide` to snap one field's edges to another's (e.g. a mask to height)."""
    p = np.asarray(p, dtype=np.float64)
    I = p if guide is None else np.asarray(guide, dtype=np.float64)
    mean_I, mean_p = box_filter(I, r), box_filter(p, r)
    var_I = box_filter(I * I, r) - mean_I * mean_I
    cov_Ip = box_filter(I * p, r) - mean_I * mean_p
    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I
    return box_filter(a, r) * I + box_filter(b, r)


def perona_malik(h, K, iters=20, lam=0.2):
    """Anisotropic diffusion (Perona & Malik 1990): conductivity drops where the gradient is
    high, so it smooths WITHIN regions, not ACROSS edges. `K` is the edge threshold in metres.
    Note: this is the same object as thermal erosion (05) with a different conductivity — if you
    already run thermal you are already running this."""
    h = np.asarray(h, dtype=np.float64).copy()
    for _ in range(int(iters)):
        hp = np.pad(h, 1, mode="edge")
        d = np.zeros_like(h)
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nb = hp[1 + di:1 + di + h.shape[0], 1 + dj:1 + dj + h.shape[1]]
            diff = nb - h
            d += lam * np.exp(-(diff / K) ** 2) * diff
        h += d
    return h


# --------------------------------------------------------------------------- #
# greyscale morphology (Serra 1982), flat square SE of radius r
# --------------------------------------------------------------------------- #
def dilate(h, r=1):
    """max over the SE — grows peaks, fills pits."""
    return _window_stack(np.asarray(h, dtype=np.float64), r).max(axis=0)


def erode(h, r=1):
    """min over the SE — shrinks peaks, deepens pits."""
    return _window_stack(np.asarray(h, dtype=np.float64), r).min(axis=0)


def opening(h, r=1):
    """erode then dilate — removes peaks smaller than the SE. Idempotent."""
    return dilate(erode(h, r), r)


def closing(h, r=1):
    """dilate then erode — fills pits smaller than the SE. A poor man's depression fill, and
    INFERIOR to priority-flood (03): it fills by SE size, not hydrological connectivity, so it
    routes flow wrong while looking fine. Do not substitute it for 03."""
    return erode(dilate(h, r), r)


def tophat(h, r=1):
    """h - opening: isolates small peaks -> a free 'small features' mask (scree, boulders)."""
    return np.asarray(h, dtype=np.float64) - opening(h, r)


def bothat(h, r=1):
    """closing - h: isolates small pits."""
    return closing(h, r) - np.asarray(h, dtype=np.float64)


# --------------------------------------------------------------------------- #
# authored coordinate warps (warp the SAMPLE COORDINATE, upstream of erosion)
# --------------------------------------------------------------------------- #
def twist(px, py, cx, cy, k):
    """Rotate coordinates by an angle that grows with radius (k=0 is identity). Returns warped
    (x, y) to sample with. A twist DOWNSTREAM of erosion is a bug — it breaks the drainage (10)."""
    qx, qy = np.asarray(px, dtype=np.float64) - cx, np.asarray(py, dtype=np.float64) - cy
    a = k * np.hypot(qx, qy)
    ca, sa = np.cos(a), np.sin(a)
    return cx + qx * ca - qy * sa, cy + qx * sa + qy * ca


def bend(px, py, k):
    """Parabolic bend of the sample coordinate (k=0 is identity)."""
    px = np.asarray(px, dtype=np.float64)
    return px, np.asarray(py, dtype=np.float64) + k * px * px
