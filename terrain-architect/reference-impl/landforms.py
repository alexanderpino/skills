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
                      repose_tan=0.62, sides=6, fault=None, warp=0.12, corner_round=1.3):
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
    if corner_round > 0.0:                                                   # blur the SDF a touch so the razor
        d = ops_filters.gaussian(d, corner_round)                          # ~90° joint corners round off —
    #  sharp exposed corners weather fastest, so a perfectly square block reads artificial (a short diffusion
    #  of the footprint SDF is the cheap stand-in for that preferential corner erosion; faces stay straight).
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
# Gaea's Mountain node styles. The organized (non-noisy) look comes from a MODULATED
# VORONOI ridge network — cell EDGES are ridgelines, cell INTERIORS are valleys — broken
# by a domain distortion into natural spurs (QuadSpinner docs: "modulated Voronoi + distortion",
# the eroded look baked into the primitive, NOT a downstream erosion sim). The style then shapes
# that network: sharpness of crests, drainage-cell count, warp, and a talus pass for weathering.
_MOUNTAIN_STYLES = {
    #           cells warp  relief spur crest  erode talus repose terr
    "basic":  dict(cells=4.0, warp=0.30, relief=0.55, spur=0.28, crest=1.15, erode=0.00, talus=0,  repose=0.95, terr=0),
    "eroded": dict(cells=5.0, warp=0.55, relief=0.66, spur=0.40, crest=1.35, erode=0.15, talus=4,  repose=0.72, terr=0),
    "alpine": dict(cells=3.6, warp=0.42, relief=0.74, spur=0.44, crest=1.70, erode=0.12, talus=7,  repose=1.15, terr=0),
    "old":    dict(cells=5.6, warp=0.62, relief=0.44, spur=0.30, crest=1.05, erode=0.20, talus=14, repose=0.42, terr=0),
    "strata": dict(cells=4.4, warp=0.34, relief=0.52, spur=0.30, crest=1.20, erode=0.13, talus=4,  repose=0.72, terr=8),
}


def _talus_relax(h, repose_tan, iters, cellsize, factor=0.5):
    """Fast vectorised thermal/talus relaxation (Musgrave 1989): move above-repose material to
    lower 4-neighbours. **No-flux boundaries** — flux is computed on interior slices, never wrapped
    across the tile edge (an earlier np.roll version wrapped material between opposite margins, which
    is wrong for a bounded massif whose edges are NOT ~0). Mass is conserved exactly on the finite grid
    (every shed amount lands on an in-grid neighbour). The tested `erosion_thermal.thermal_erosion` is
    the reference; this is its vectorised twin for baking weathering into the primitive cheaply."""
    h = np.array(h, dtype=np.float64)
    thr = repose_tan * cellsize
    for _ in range(int(iters)):
        delta = np.zeros_like(h)
        # each cardinal pair, interior-only (a<->b are aligned overlapping slices; no boundary crossing)
        for a, b in (((slice(0, -1), slice(None)), (slice(1, None), slice(None))),   # vertical
                     ((slice(None), slice(0, -1)), (slice(None), slice(1, None)))):   # horizontal
            diff = h[a] - h[b]
            fwd = factor * 0.25 * np.maximum(diff - thr, 0.0)                # a higher than b: a -> b
            bwd = factor * 0.25 * np.maximum(-diff - thr, 0.0)              # b higher than a: b -> a
            delta[a] += bwd - fwd
            delta[b] += fwd - bwd
        h += delta
    return h


def mountain(shape, cellsize, *, seed=0, n_ridges=3, height=1600.0, reach_frac=0.34,
             style="eroded", cells=None, warp=None, relief=None):
    """A MOUNTAIN feature primitive — the "Mountain" generator node an artist places (Gaea's Mountain;
    Génévaux et al. 2015 *Terrain Modelling from Feature Primitives*; Guérin et al. 2016). NOT thresholded
    isotropic noise (which reads as "noise on a lump"): the eroded, drainage-organised look is baked in via
    a **modulated Voronoi ridge network** the way Gaea builds it — Worley cell *edges* form the ridgelines and
    cell *interiors* the valleys, then a **domain distortion** breaks the cell regularity into natural spurs and
    drainages. A wandering ridge-crest **skeleton** (a polyline SDF) sets the overall concave-flank massif
    envelope (`n_ridges` crest lines unioned into a small range); the Voronoi network dissects it into a
    connected system of spurs and incised valleys; a talus pass weathers the faces.

    `style` matches Gaea's presets — **basic** (clean young massif), **eroded** (default; gullied, weathered),
    **alpine** (sharp high-relief aretes), **old** (subdued, rounded, low relief), **strata** (horizontal
    sedimentary banding). The primitive is "ready for further erosion" — place it, combine several
    (`np.maximum` / `ops_filters.smax`), then run a real hydraulic + thermal pass (see `main`). Returns height (m).
    `cells`/`warp`/`relief` override the style's drainage-cell count, distortion, and valley-incision depth.

    Note (composability): the ridge network is scaled by a whole-tile `np.percentile` of the Worley field,
    so this is a **single-shot, whole-tile generator** — it is NOT tile-composable (a different crop
    renormalises differently and the seam would not match), the evaluation-dependent-normalisation caveat
    `10` warns about. That is acceptable here (a Mountain node produces one massif on one tile); for a
    tiling pipeline, drive it from a fixed normalisation constant instead of the percentile."""
    n0, n1 = shape
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    rng = np.random.default_rng(seed)
    st = _MOUNTAIN_STYLES.get(style, _MOUNTAIN_STYLES["eroded"])
    ncell = st["cells"] if cells is None else cells
    warpamt = st["warp"] if warp is None else warp
    relief = st["relief"] if relief is None else relief

    # 1) crest-skeleton envelope: a non-circular massif footprint (crest high, margins low).
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
        env = np.maximum(env, (0.7 + 0.6 * rng.random()) * np.clip(1.0 - d / reach, 0.0, 1.0) ** 1.6)

    # 2) modulated-Voronoi RIDGE NETWORK (the organized, non-noisy dissection Gaea's Mountain is built on).
    u = xx / max(n0, n1) * ncell                                            # ~ncell drainage cells across the tile
    v = yy / max(n0, n1) * ncell
    # Two-scale domain distortion: a COARSE bend curves the ridgelines off Voronoi's straight cell edges,
    # a FINER warp adds spurs. Without it the cells read as geometric polygons rather than mountain flanks.
    wx = (noise.fbm(u * 0.35, v * 0.35, seed + 3, octaves=4)
          + 0.5 * noise.fbm(u * 0.9, v * 0.9, seed + 13, octaves=4))
    wy = (noise.fbm(u * 0.35 + 4.7, v * 0.35 + 2.3, seed + 4, octaves=4)
          + 0.5 * noise.fbm(u * 0.9 + 1.9, v * 0.9 + 6.1, seed + 14, octaves=4))
    u2, v2 = u + warpamt * wx, v + warpamt * wy
    edge = noise.worley(u2, v2, seed + 1, kind="f2f1")                       # ~0 at cell boundaries, large inside
    net = 1.0 - edge / (np.percentile(edge, 98) + 1e-9)                      # -> ~1 on the ridgelines (cell edges)
    edge2 = noise.worley(u2 * 2.0, v2 * 2.0, seed + 8, kind="f2f1")          # finer octave: sub-ridges / spurs
    net2 = 1.0 - edge2 / (np.percentile(edge2, 98) + 1e-9)
    ridges = np.clip((1.0 - st["spur"]) * net + st["spur"] * net2, 0.0, 1.0) ** st["crest"]

    # 3) incise the massif: crest sits at the envelope, valleys drop `relief` below it.
    h = height * env * ((1.0 - relief) + relief * ridges)

    # 4) bake the weathering the style implies. A modest droplet (hydraulic) pass turns the Voronoi
    #    cell skeleton into a DENDRITIC drainage network — the step that reads as "eroded mountain"
    #    rather than "crumpled Voronoi" — exactly what Gaea's Eroded/Old presets fold in (the primitive
    #    is still "ready for" a heavier erosion pass afterwards). Then a talus pass relaxes faces to repose,
    #    and strata banding is quantised onto the eroded surface (so bands sit on real slopes).
    if st["erode"] > 0.0:
        import erosion_droplet
        h = erosion_droplet.droplet_erode(h, n_droplets=int(st["erode"] * n0 * n1),
                                          seed=seed + 11, brush_radius=2)
    if st["talus"]:
        h = _talus_relax(h, st["repose"], st["talus"], cellsize, factor=0.5)
    if st["terr"]:
        peak = h.max()
        if peak > 0.0:
            h = terrace(h / peak, st["terr"], sharpness=2.4, warp_amp=0.03,   # warp a HEIGHT-NORMALISED field
                        warp_wl=max(n0, n1) * cellsize / 6.0, cellsize=cellsize, seed=seed + 5) * peak
    return h


# --------------------------------------------------------------------------- #
# more placeable feature primitives (Gaea's Ridge / Volcano / Canyon nodes)
# --------------------------------------------------------------------------- #
def _polyline_distance(xx, yy, px, py):
    """Distance (cells) from every grid point to a polyline through control points (px, py)."""
    d = np.full(xx.shape, np.inf)
    for a in range(len(px) - 1):
        d = np.minimum(d, ops_filters.sd_segment(xx, yy, px[a], py[a], px[a + 1], py[a + 1]))
    return d


def ridge(shape, cellsize, *, seed=0, height=900.0, angle=None, width_frac=0.16,
          sinuosity=0.5, asymmetry=0.55, detail=0.35, crest_round=0.12, weather_iters=0):
    """A single linear RIDGELINE primitive — Gaea's "Ridge" node; the **hogback / cuesta** an
    exhumed resistant bed makes. Geology: a hogback/cuesta is the erosional expression of a **dipping
    resistant bed** (a homocline) under differential erosion — the gentle **dip slope** IS the exhumed
    top bedding plane (angle ≈ bed dip), the steep **scarp** cuts across the beds; the dip angle sets
    the class (cuesta ≲25°, hogback ≳30–40°). Huggett 2011 *Fundamentals of Geomorphology*; Fairbridge
    1968. The physically-correct route is differential erosion of a tilted `bed_erodibility` field
    (the `04+11` differential-erosion path); THIS is the fast placeable *primitive*, built the way the
    graphics literature builds ridges — a BLENDED shape, not a hard-stamped wedge (Génevaux 2013;
    Guérin 2016), with three fixes so the crest is not a razor mathematical cut:

      1. **domain warp** the across-crest coordinate (Quilez, iquilezles.org/articles/warp) so the
         strike-line meanders organically instead of running dead-straight;
      2. **smooth-min the two flank planes** (`ops_filters.smin`; Quilez, iquilezles.org/articles/smin)
         so the crest is a rounded C∞ transition of width `crest_round·height`, not a C1 crease;
      3. optional **thermal weathering** (`weather_iters`; Musgrave, Kolb & Mace 1989) to shed talus
         and round the over-steep crest.

    The ridged detail is weighted onto the SCARP flank (dissected), leaving the dip slope smooth (the
    exhumed bedding plane). `asymmetry` 0 = symmetric arête; → 1 steepens/shortens the scarp and
    lengthens the gentle dip. Returns height (m)."""
    n0, n1 = shape
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0.0, np.pi) if angle is None else angle
    reach = width_frac * max(n0, n1)
    perpx, perpy = -np.sin(ang), np.cos(ang)                                # across-crest unit vector
    s0 = (xx - 0.5 * n1) * perpx + (yy - 0.5 * n0) * perpy                  # signed across-crest coord (cells)
    fw = 2.4 / max(n0, n1)                                                  # low frequency -> few meanders/tile
    warp = (noise.fbm(xx * fw, yy * fw, seed + 3, octaves=4)               # DOMAIN WARP the crest (Quilez)
            + 0.4 * noise.fbm(xx * fw * 3.0, yy * fw * 3.0, seed + 9, octaves=3))
    s = s0 + sinuosity * reach * warp                                      # warped -> the crest s=0 meanders
    scarp = reach * (1.0 - asymmetry)                                      # short, steep scarp flank
    dip = reach * (1.0 + asymmetry)                                        # long, gentle dip flank
    p_scarp = height * (1.0 - s / scarp)                                   # roof plane descending on the scarp side
    p_dip = height * (1.0 + s / dip)                                       # roof plane descending on the dip side
    z = ops_filters.smin(p_scarp, p_dip, crest_round * height)            # SMOOTH crest (rounded, no razor cut)
    z = ops_filters.smax(z, 0.0, 0.06 * height)                           # rounded toe onto the plain
    z = np.clip(z, 0.0, height)
    fx = xx * cellsize / (max(n0, n1) * cellsize * 0.10)
    fy = yy * cellsize / (max(n0, n1) * cellsize * 0.10)
    rid = noise.ridged_mf(fx, fy, seed + 7, octaves=6)
    rid = (rid - rid.min()) / (np.ptp(rid) + 1e-9)
    scarp_w = _smoothstep(-0.2 * reach, 0.4 * reach, s)                    # dissect the scarp, keep the dip smooth
    dfac = detail * scarp_w
    z = z * ((1.0 - dfac) + dfac * rid)
    if weather_iters > 0:                                                  # talus weathering rounds the crest (05)
        import erosion_thermal
        z = erosion_thermal.thermal_erosion(z, 0.7, int(weather_iters), cellsize)
    return z


def volcano(shape, cx, cy, radius, height, cellsize=1.0, *, seed=0, kind="strato",
            crater_frac=0.14, crater_depth_frac=0.35, barranco=0.10, n_barrancos=16):
    """A VOLCANO edifice primitive — Gaea's "Volcano" node. A radial cone with the CONCAVE-UP profile
    real volcanoes show (upper slopes steepest), a summit CRATER, and radial BARRANCOS (the erosional
    gullies that groove every stratovolcano flank). `kind`: 'strato' = steep concave cone (upper slopes
    ~30–35°, flaring to a gentle base; Karátson et al. 2010 morphometry) with a deep summit crater;
    'shield' = low-angle (~5–8°) broad convex dome with a shallow caldera (Hawaiian type). `radius`,
    `height`, crater sizes in the obvious units. Returns height-above-base (m)."""
    n0, n1 = shape
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    R = radius
    r = np.hypot((xx - cx) * cellsize, (yy - cy) * cellsize)
    rn = np.clip(r / R, 0.0, 1.0)
    if kind == "shield":
        prof = 1.0 - rn ** 1.7                                              # broad convex dome, low slopes
    else:
        prof = (1.0 - rn) ** 2.2                                           # concave-up: STEEPEST at the summit,
        #  exponent > 1 => |dprof/dr| ~ (1-rn)^1.2 is largest at rn->0 (summit) and flares to 0 at the foot,
        #  the stratovolcano's pronounced concave SWEEP (steep upper cone ~30-35deg, long gentle apron;
        #  Karátson 2010). 2.2 gives a summit/foot slope ratio ~3x — a real sweep, not a linear cone.
        #  Exponent < 1 would invert this into a foot-steepened dome (the bug the audit first caught).
    # radial barrancos: gullies grooving the flanks, deepening downslope, vanishing at the summit
    theta = np.arctan2(yy - cy, xx - cx)
    grooves = 0.5 * (1.0 + np.cos(n_barrancos * theta + 2.0 * np.pi * noise.fbm(xx / 9.0, yy / 9.0, seed + 3, octaves=3)))
    prof = prof * (1.0 - barranco * grooves * rn)                          # grooves grow toward the base
    h = height * np.clip(prof, 0.0, 1.0)
    # summit crater / caldera: a rimmed bowl at the centre
    cr = crater_frac * R
    bowl = np.clip(1.0 - r / cr, 0.0, 1.0)
    h = h - crater_depth_frac * height * bowl ** 1.5                        # depression
    h = h + 0.05 * height * np.exp(-((r - cr) / (0.35 * cr)) ** 2)         # raised crater rim
    return np.maximum(h, 0.0)


def canyon(shape, cellsize, *, seed=0, rim=1000.0, depth=750.0, width_frac=0.035,
           sinuosity=0.22, benches=3, n_tributaries=3, roughness=0.05):
    """A CANYON primitive — Gaea's "Canyon" node. A high PLATEAU incised by a MEANDERING trunk gorge
    with HORIZONTAL-STRATA benches and a few tributary side-canyons. Grounded the way real canyons form:
    a fixed base level with the trunk incising down to a flat floor, and resistant beds holding the walls
    back as benches AT CONSTANT ABSOLUTE ELEVATIONS — so the terraces stay flat and stationary while the
    meander cuts down through them (the Grand Canyon's cliff-and-bench profile; Leopold 1964 meanders —
    the trunk's sinuous planform, tributaries joining at acute angles). `depth` below `rim` (m),
    `width_frac` of the tile for the floor half-width. Returns height (m)."""
    n0, n1 = shape
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    rng = np.random.default_rng(seed)
    plateau = rim + roughness * rim * noise.fbm(xx / 12.0, yy / 12.0, seed + 1, octaves=5)
    # trunk centreline runs down the tile (row-parametric) and meanders across it
    k = 10
    ry = np.linspace(0.0, n0 - 1.0, k)
    mx = 0.5 * n1 + sinuosity * n1 * np.sin(np.linspace(0.0, 3.0, k) * np.pi) \
        + np.cumsum(rng.normal(0.0, 0.05, k)) * n1
    d = _polyline_distance(xx, yy, mx, ry)
    for _ in range(int(n_tributaries)):                                     # tributaries join the trunk
        j = rng.integers(2, k - 2)
        ex = rng.uniform(0.12, 0.88) * n1                                   # tributary head on a plateau margin
        ey = rng.uniform(0.12, 0.88) * n0
        tk = 5
        tx = np.linspace(ex, mx[j], tk) + rng.normal(0.0, 0.03 * n1, tk)
        ty = np.linspace(ey, ry[j], tk) + rng.normal(0.0, 0.03 * n0, tk)
        d = np.minimum(d, _polyline_distance(xx, yy, tx, ty))
    floor_w = width_frac * max(n0, n1)                                      # flat floor half-width (cells)
    wall_w = 2.2 * floor_w                                                  # wall run from floor lip to rim (steep)
    # 1) a SMOOTH V-profile gorge (distance-driven): incision 1 on the floor -> 0 at the rim.
    ramp = np.clip((d - floor_w) / wall_w, 0.0, 1.0)
    h_smooth = plateau - depth * np.where(d <= floor_w, 1.0, 1.0 - ramp)
    # 2) benches are HORIZONTAL STRATA, not river contours: quantise ABSOLUTE ELEVATION to global bands, so
    #    the steps stay flat and geographically STATIONARY while the meander cuts down THROUGH them (the true
    #    strath-terrace geometry). A low-frequency warp gives the bed traces natural irregularity, and the
    #    river floor + plateau keep their smooth surfaces — only the incised walls are terraced.
    base = rim - depth
    step = depth / max(int(benches), 1)
    b = (h_smooth - base) / step + 0.18 * noise.fbm(xx / 9.0, yy / 9.0, seed + 7, octaves=3)
    bench = base + step * (np.floor(b) + _smoothstep(0.0, 1.0, (b - np.floor(b)) ** 2.4))
    wall = (d > floor_w) & (h_smooth < rim - 0.02 * depth)                  # incised walls only
    h = np.where(wall, bench, h_smooth)
    h = h + (d <= floor_w) * roughness * depth * noise.fbm(xx / 6.0, yy / 6.0, seed + 4, octaves=3)  # rough floor
    return h


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


def alluvial_fan(h, apex, *, flux=9.0, length=90.0, spread_deg=62.0, downfan=(1.0, 0.0),
                 lobes=6, concavity=1.7, gate_power=1.5, cellsize=1.0, seed=0):
    """Deposit a semiconical **alluvial fan** at a mountain-front `apex` (16; Blair & McPherson 1994).
    Where a confined channel debouches onto the basin floor it unconfines, spreads over an angular
    sector, and drops its load — a fan that **thins downfan** (concave profile: steep near the apex,
    gentle distal). It is built as overlapping **avulsion lobes** (the feeder channel jumps between
    episodes, `seed`-jittered within the spread) rather than a smooth cone — which is what makes a fan
    a fan. Coalesce several along a range front → a **bajada**. `apex=(row, col)`, `downfan=(drow,
    dcol)`. Deposition only (adds to `h`); returns a new height field."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    ai, aj = apex
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    dy, dx = yy - ai, xx - aj
    r = np.hypot(dy, dx) * cellsize
    rn = np.hypot(dy, dx) + 1e-9
    du, dv = downfan
    dm = float(np.hypot(du, dv)) + 1e-30
    du, dv = du / dm, dv / dm
    rng = np.random.default_rng(seed)
    half = np.radians(spread_deg) / 2.0
    prof = np.clip(1.0 - r / length, 0.0, 1.0) ** concavity            # concave thinning profile
    total = np.zeros_like(h)
    for _ in range(int(lobes)):                                        # avulsion: jittered lobes
        j = float(rng.uniform(-1.0, 1.0)) * half * 0.7
        lu = du * np.cos(j) - dv * np.sin(j)
        lv = du * np.sin(j) + dv * np.cos(j)
        ang = np.arccos(np.clip((dy * lu + dx * lv) / rn, -1.0, 1.0))  # angle off the lobe axis
        gate = np.clip(1.0 - ang / half, 0.0, 1.0) ** gate_power
        total += flux * prof * gate
    return h + total


# --------------------------------------------------------------------------- #
# karst — the depression-handling exception
# --------------------------------------------------------------------------- #
def karst_sinkholes(h, soluble_mask, cellsize=1.0, spacing=None, depth=5.0,
                    radius=None, seed=0, size_var=0.0):
    """Carve dolines (sinkholes) at blue-noise points that fall on soluble rock. Returns
    (h, sink_mask). The sink_mask marks pits that must NOT be filled (03): in karst the water
    genuinely goes underground and leaves the surface network — the one case a pit is correct.

    `size_var` gives the dolines a natural SIZE DISTRIBUTION rather than one radius: real doline
    fields are lognormal/power-law in diameter (Williams 1972; Denizman 2003), so each pit's radius
    is scaled by a lognormal factor exp(size_var * N(0,1)) (clamped to [0.4, 2.2]) and its depth
    scaled the same way, preserving the conical depth:diameter aspect. `size_var=0` = uniform (the
    old behaviour)."""
    h = np.asarray(h, dtype=np.float64).copy()
    soluble_mask = np.asarray(soluble_mask, dtype=np.float64)
    n, m = h.shape
    if spacing is None:
        spacing = 8.0 * cellsize
    if radius is None:
        radius = 3.0 * cellsize
    pts = scatter.poisson_disk(m * cellsize, n * cellsize, spacing, seed)
    rng = np.random.default_rng(seed + 12345)              # size draws, independent of the point pattern
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    sink_mask = np.zeros((n, m), dtype=bool)
    for x, y in pts:
        j, i = int(x / cellsize), int(y / cellsize)
        f = float(np.clip(np.exp(size_var * rng.standard_normal()), 0.4, 2.2)) if size_var else 1.0
        if 0 <= i < n and 0 <= j < m and soluble_mask[i, j] > 0.5:
            r = np.hypot((xx - j) * cellsize, (yy - i) * cellsize)
            h -= depth * f * np.clip(1.0 - r / (radius * f), 0.0, 1.0)   # bigger dolines dig deeper (const aspect)
            sink_mask |= r < radius * f
    return h, sink_mask


def main():
    """A gallery of the placeable landform GENERATORS — the Gaea-style "nodes" an artist drops in.
    Top row: the Mountain node's five styles (basic | eroded | alpine | old | strata) — the
    drainage-organised look is baked into the primitive (modulated Voronoi + distortion). Bottom
    row: Mountain(basic) then a REAL hydraulic+thermal pass | Ridge | Volcano | Canyon. -> landforms.png."""
    import erosion_droplet
    import erosion_thermal
    import render
    n, cell = 200, 26.0
    pad = np.full((n, 5, 3), 20, np.uint8)
    tiles = [render.hillshade(mountain((n, n), cell, seed=3, n_ridges=3, height=1900.0, style=s), cell)
             for s in ("basic", "eroded", "alpine", "old", "strata")]
    top = np.hstack([t for pair in zip(tiles, [pad] * len(tiles)) for t in pair][:-1])

    h = mountain((n, n), cell, seed=3, n_ridges=3, height=1900.0, style="basic")
    he = erosion_thermal.thermal_erosion(
        erosion_droplet.droplet_erode(h, n_droplets=55 * n, seed=3, brush_radius=2), 0.7, 14, cell, factor=0.12)
    rg = ridge((n, n), cell, seed=2, height=1400.0, asymmetry=0.6)
    vo = volcano((n, n), n / 2, n / 2, radius=n * 0.42 * cell, height=1900.0, cellsize=cell, seed=1, kind="strato")
    ca = canyon((n, n), cell, seed=3, rim=1200.0, depth=950.0)
    bottom_tiles = [render.hillshade(x, cell) for x in (he, rg, vo, ca)]
    bottom = np.hstack([t for pair in zip(bottom_tiles, [pad] * len(bottom_tiles)) for t in pair][:-1])
    bottom = np.hstack([bottom, np.full((n, top.shape[1] - bottom.shape[1], 3), 20, np.uint8)])
    gap = np.full((5, top.shape[1], 3), 20, np.uint8)
    render.write_png("landforms.png", np.vstack([top, gap, bottom]))
    print(f"wrote landforms.png — landform generators: Mountain styles + Erode/Ridge/Volcano/Canyon, "
          f"eroded relief {np.ptp(he):.0f} m")


if __name__ == "__main__":
    main()
