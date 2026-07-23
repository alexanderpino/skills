"""Oracle-backed geological landforms (11-geological.md).

The pieces of `11` that have a decisive check: impact craters (Pike 1977 / Melosh 1989
morphology and the gravity pi-scaling), stratigraphy as a material coordinate + terracing,
folding as a warp of that coordinate, and karst sinkholes — the one place a pit is correct
and must NOT be filled (03). Deformations that only make sense as an eroded material stack
(salt diapirs, tower karst, relief inversion) stay in the reference as pseudocode; they have
no standalone deterministic oracle and are out of scope here.
"""
import numpy as np

import noise
import ops_filters
import scatter


def _smoothstep(lo, hi, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------- #
# impact craters (Pike 1977; Melosh 1989)
# --------------------------------------------------------------------------- #
def crater_diameter(energy, g, k=1.0, mu=0.55):
    """Gravity-regime pi-scaling (Melosh 1989): final diameter grows with impact energy and
    SHRINKS with gravity — the same energy digs a BIGGER crater at lower g. Exponents are the
    pi-group form (energy ~1/(2+mu), gravity ~ -mu/(2+mu)); the load-bearing fact is the sign
    of the gravity dependence (the off-Earth doctrine in SKILL.md)."""
    return k * energy ** (1.0 / (2.0 + mu)) * g ** (-mu / (2.0 + mu))


def impact_crater(h, cx, cy, D, cellsize=1.0, complex_D=3000.0):
    """Stamp a crater of diameter `D` (metres) centred at cell (cx, cy). Morphology per Pike:
    a paraboloid bowl to depth ~D/5, a raised rim ~0.04*D, an ejecta blanket thinning as r^-3,
    and — for D >= complex_D (the simple->complex transition, ~1/g) — a central rebound peak and
    a shallower floor. A crater without rim/ejecta/peak is a golf divot, not an impact (11)."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    R = D / 2.0
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    r = np.hypot((xx - cx) * cellsize, (yy - cy) * cellsize)

    complex_ = D >= complex_D
    depth = 0.2 * D * ((complex_D / D) ** 0.3 if complex_ else 1.0)   # shallower when complex
    rim = 0.04 * D

    inside = r < R
    prof = np.where(inside, -depth * (1.0 - (r / R) ** 2), 0.0)       # paraboloid bowl
    prof += rim * np.exp(-((r - R) / (0.15 * R)) ** 2)               # raised rim ring
    ejecta = rim * 0.5 * (np.maximum(r, R) / R) ** (-3.0)            # ejecta ~ r^-3
    prof += np.where((r >= R) & (r < 3.0 * R), ejecta, 0.0)
    if complex_:
        prof += np.where(inside, depth * 0.5 * np.exp(-(r / (0.18 * R)) ** 2), 0.0)  # central peak
    return h + prof


# --------------------------------------------------------------------------- #
# stratigraphy, terracing, folding
# --------------------------------------------------------------------------- #
def strat_coord(h, x, y, *, tilt=(0.0, 0.0), fold_amp=0.0, fold_dir=(1.0, 0.0),
                fold_freq=0.0, warp_amp=0.0, warp_wl=1.0, seed=0):
    """Stratigraphic coordinate: depth within the bed sequence (11). Horizontal beds -> strat =
    elevation; regional dip adds a linear term; folds add a sinusoid; fBm adds the irregularity
    real beds have. Erosion of `K(strat)` produces the landform, not a height op."""
    s = np.asarray(h, dtype=np.float64) + tilt[0] * x + tilt[1] * y
    if fold_amp:
        s = s + fold_amp * np.sin((fold_dir[0] * x + fold_dir[1] * y) * fold_freq)
    if warp_amp:
        s = s + warp_amp * noise.fbm(np.asarray(x) / warp_wl, np.asarray(y) / warp_wl, seed)
    return s


def bed_erodibility(strat, bed_table):
    """Map a stratigraphic coordinate to a bed property via an ordered `bed_table`
    [(thickness, value), ...], repeating with the sequence. Bed thicknesses must be non-uniform
    — even beds are the tell-tale of a fake (11). Feed the result to stream power / thermal."""
    strat = np.asarray(strat, dtype=np.float64)
    total = sum(t for t, _ in bed_table)
    sm = np.mod(strat, total)
    out = np.zeros_like(strat)
    acc = 0.0
    for t, v in bed_table:
        out = np.where((sm >= acc) & (sm < acc + t), v, out)
        acc += t
    return out


def terrace(h, levels, sharpness=2.0, warp_amp=0.0, warp_wl=1.0, cellsize=1.0, seed=0):
    """The terracing height op: quantise to `levels` bands, sharpness>1 giving flat treads and
    sharp risers. `warp_amp` warps BEFORE quantising so steps wander instead of following
    perfect contours (11). Belongs upstream of flow routing — quantising after erosion destroys
    the drainage."""
    h = np.asarray(h, dtype=np.float64)
    if warp_amp:
        n, m = h.shape
        yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
        h = h + warp_amp * noise.fbm(xx * cellsize / warp_wl, yy * cellsize / warp_wl, seed)
    q = h * levels
    f = _smoothstep(0.0, 1.0, (q - np.floor(q)) ** sharpness)
    return (np.floor(q) + f) / levels


# --------------------------------------------------------------------------- #
# fault/joint-controlled buttes & mesas (a placeable landform primitive)
# --------------------------------------------------------------------------- #
def fault_block_butte(shape, bx, by, br, bh, cellsize, seed=0, ecc=1.0, talus=0.42,
                      repose_tan=0.62, sides=6, fault=None, warp=0.12):
    """A caprock butte/mesa/jebel as height-above-plain (m): flat structural TOP, a near-vertical
    CLIFF, then a SHARP break of slope to a TALUS apron at the angle of repose. Cliff-foot-to-scree
    is the break-of-slope that reads as rock rather than a smoothed noise blob.

    The footprint is **fault/joint-controlled**, not radial: flat-lying sandstone fails along two
    near-orthogonal systematic joint sets, so real buttes are blocky polygons with straight faces and
    ~90° corners — never circles (NPS Arches/Canyonlands *The Needles*; Li et al. 2021; Narr & Suppe
    1991). The outline is a convex polygon = intersection of half-planes (`ops_filters.sd_convex_polygon`,
    10) at two orthogonal joint azimuths, with **cross joints spaced ~1.7× wider** (so blocks elongate
    along strike), small jitter to keep the corners square, and a low-amplitude **domain warp** so the
    joint traces read jagged, not ruler-straight. Pass `fault` (radians) to share one regional joint
    strike across several buttes so their faces align. Place, then combine with `np.maximum`/`smax` and
    run thermal erosion for the talus — the same "primitive → combine → erode" a Houdini/Gaea graph uses.
    `bx,by,br` in cells; `bh` in metres; `ecc` gives per-butte aspect variety; `talus` = height fraction
    in the scree apron."""
    n0, n1 = shape
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    rng = np.random.default_rng(seed)
    R = br * cellsize                                                        # nominal footprint radius (m)
    dx = (xx - bx) * cellsize
    dy = (yy - by) * cellsize / ecc                                          # per-butte aspect variety
    wx = noise.fbm(xx / 7.0, yy / 7.0, seed, octaves=4)                      # jagged fault traces (warp << spacing)
    wy = noise.fbm(xx / 7.0 + 5.0, yy / 7.0 + 5.0, seed + 1, octaves=4)
    dx = dx + warp * R * wx
    dy = dy + warp * R * wy
    base_ang = rng.uniform(0.0, np.pi) if fault is None else fault           # regional joint strike
    normals, offsets = [], []                                               # a CLOSED block: the four faces step
    for k in range(sides):                                                   # by 90° (two orthogonal joint sets),
        a = base_ang + (np.pi / 2.0) * k + rng.uniform(-0.18, 0.18)          # small jitter keeps ~90° corners
        spacing = 1.7 if (k % 2) else 1.0                                    # cross joints ~1.8x wider -> elongated
        normals.append((np.cos(a), np.sin(a)))
        offsets.append(R * spacing * rng.uniform(0.74, 1.12))              # irregular, off-centre edge offsets
    d = ops_filters.sd_convex_polygon(dx, dy, normals, offsets)             # grounded SDF primitive (10)
    th = talus * bh                                                         # scree-apron height (m)
    tr = th / repose_tan                                                    # apron run length at repose (m)
    cw = 1.4 * cellsize                                                     # cliff width (m) -> near vertical
    prof = np.where(d <= 0.0, bh,                                           # inside the fault block: flat top
                    np.where(d <= cw, bh - (bh - th) * d / cw,              # near-vertical cliff
                             np.where(d <= cw + tr, th * (1.0 - (d - cw) / tr), 0.0)))  # repose talus
    prof = np.maximum(prof, 0.0)
    tal = (d > cw) & (d <= cw + tr)                                         # roughen the scree (not a smooth cone)
    prof = prof + tal * noise.fbm(xx / 5.0, yy / 5.0, seed + 2, octaves=3) * 0.03 * bh
    lip = np.clip(1.0 - np.abs(d) / (0.8 * cellsize), 0.0, 1.0) * 0.05 * bh  # resistant caprock rim
    return np.maximum(prof + lip * (d <= cw), 0.0)                           # height-above-plain (>= 0)


# --------------------------------------------------------------------------- #
# mountain generator (a placeable feature primitive — Gaea's "Mountain" node)
# --------------------------------------------------------------------------- #
def mountain(shape, cellsize, *, seed=0, n_ridges=3, height=1600.0, reach_frac=0.32,
             detail=0.55, octaves=7, profile=1.6):
    """A MOUNTAIN feature primitive (Génévaux et al. 2015, *Terrain Modelling from Feature Primitives*;
    Guérin et al. 2016) — a landform GENERATOR, the "Mountain" node an artist places, distinct from
    thresholded noise: a wandering ridge-crest **skeleton** (a polyline) sets a concave-flank envelope,
    which ridged-multifractal **detail** then dissects into spurs and valleys. `n_ridges` crest lines are
    unioned into a small range. Place it, combine several (`np.maximum` / `ops_filters.smax`), then erode
    — the construction-tree workflow. Returns height (m)."""
    n0, n1 = shape
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    rng = np.random.default_rng(seed)
    reach = reach_frac * max(n0, n1)                                         # flank half-width (cells)
    env = np.zeros(shape)
    for _ in range(int(n_ridges)):
        ang = rng.uniform(0.0, np.pi)                                        # crest orientation
        k = 6
        t = np.linspace(-1.0, 1.0, k)
        cx = 0.5 * n1 + 0.4 * n1 * np.cos(ang) * t                          # crest control points across the tile
        cy = 0.5 * n0 + 0.4 * n0 * np.sin(ang) * t
        perp = np.array([-np.sin(ang), np.cos(ang)])
        wob = np.cumsum(rng.normal(0.0, 0.05, k)); wob -= wob.mean()        # the crest wanders (non-straight)
        cx += perp[0] * wob * n1; cy += perp[1] * wob * n0
        d = np.full(shape, np.inf)
        for a in range(k - 1):
            d = np.minimum(d, ops_filters.sd_segment(xx, yy, cx[a], cy[a], cx[a + 1], cy[a + 1]))
        env = np.maximum(env, (0.7 + 0.6 * rng.random()) * np.clip(1.0 - d / reach, 0.0, 1.0) ** profile)
    fx = xx * cellsize / (max(n0, n1) * cellsize * 0.14)                     # ridged detail lattice
    fy = yy * cellsize / (max(n0, n1) * cellsize * 0.14)
    rid = noise.ridged_mf(fx, fy, seed + 7, octaves=octaves)
    rid = (rid - rid.min()) / (np.ptp(rid) + 1e-9)
    return env * height * ((1.0 - detail) + detail * rid)                    # envelope dissected by ridges


def fold(h, x, y, amp, direction=(1.0, 0.0), freq=0.0, phase=0.0):
    """A sinusoidal fold train added to the (stratigraphic) coordinate. Fold beds, THEN erode,
    and erosion through an anticline crest exposes older beds in a bullseye — free, unauthorable."""
    return np.asarray(h, dtype=np.float64) + amp * np.sin(
        (direction[0] * np.asarray(x) + direction[1] * np.asarray(y)) * freq + phase)


def anticline(h, x, y, amp, axis_point, axis_normal, sigma):
    """A single anticline (up-fold) as a Gaussian ridge across the fold axis."""
    d = (np.asarray(x) - axis_point[0]) * axis_normal[0] \
        + (np.asarray(y) - axis_point[1]) * axis_normal[1]
    return np.asarray(h, dtype=np.float64) + amp * np.exp(-d * d / (2.0 * sigma * sigma))


# --------------------------------------------------------------------------- #
# karst — the depression-handling exception
# --------------------------------------------------------------------------- #
def karst_sinkholes(h, soluble_mask, cellsize=1.0, spacing=None, depth=5.0,
                    radius=None, seed=0):
    """Carve dolines (sinkholes) at blue-noise points that fall on soluble rock. Returns
    (h, sink_mask). The sink_mask marks pits that must NOT be filled (03): in karst the water
    genuinely goes underground and leaves the surface network — the one case a pit is correct."""
    h = np.asarray(h, dtype=np.float64).copy()
    soluble_mask = np.asarray(soluble_mask, dtype=np.float64)
    n, m = h.shape
    if spacing is None:
        spacing = 8.0 * cellsize
    if radius is None:
        radius = 3.0 * cellsize
    pts = scatter.poisson_disk(m * cellsize, n * cellsize, spacing, seed)
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    sink_mask = np.zeros((n, m), dtype=bool)
    for x, y in pts:
        j, i = int(x / cellsize), int(y / cellsize)
        if 0 <= i < n and 0 <= j < m and soluble_mask[i, j] > 0.5:
            r = np.hypot((xx - j) * cellsize, (yy - i) * cellsize)
            h -= depth * np.clip(1.0 - r / radius, 0.0, 1.0)
            sink_mask |= r < radius
    return h, sink_mask


def main():
    """Demo the `mountain` feature primitive (the "Mountain" generator node): place it, then erode —
    raw primitive | after droplet + thermal erosion. -> landforms.png."""
    import erosion_droplet
    import erosion_thermal
    import render
    n, cell = 200, 26.0
    h = mountain((n, n), cell, seed=3, n_ridges=3, height=1900.0)
    he = erosion_droplet.droplet_erode(h, n_droplets=55 * n, seed=3, brush_radius=2)
    he = erosion_thermal.thermal_erosion(he, 0.7, 14, cell, factor=0.12)
    pad = np.full((n, 5, 3), 20, np.uint8)
    render.write_png("landforms.png", np.hstack([render.hillshade(h, cell), pad, render.hillshade(he, cell)]))
    print(f"wrote landforms.png — mountain feature primitive (raw | eroded), relief {np.ptp(he):.0f} m")


if __name__ == "__main__":
    main()
