"""Analysis & masks (06-analysis-masks.md).

The authoring tail of the Legal Order: once height is final, *describe* it (slope, aspect,
curvature, ambient occlusion, wetness, normals) and *select* from those fields to build the
`MaskField`s that drive materials. Every function here is pure, deterministic, and — per the
chapter's ordering rule — meant to run AFTER the last node that modifies height.

Conventions (06): x = column (axis 1), y = row (axis 0); slope is `tan` (rise/run), not
degrees; aspect points DOWNSLOPE. Thresholds carry world units, never [0,1]. Selector edges
are soft (`smoothstep`), and a real material stack is a *partition* (masks sum to <= 1).
"""
import numpy as np


# --------------------------------------------------------------------------- #
# slope, aspect, normals
# --------------------------------------------------------------------------- #
def gradient(h, cellsize=1.0, method="central"):
    """(dz/dx, dz/dy). `central` = central differences (np.gradient, one-sided at edges);
    `horn` = the 3x3 Sobel-weighted form ArcGIS uses — more robust on noisy/quantised fields."""
    h = np.asarray(h, dtype=np.float64)
    if method == "horn":
        p = np.pad(h, 1, mode="edge")
        z1, z2, z3 = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
        z4, z6 = p[1:-1, :-2], p[1:-1, 2:]
        z7, z8, z9 = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
        dzdx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8 * cellsize)
        dzdy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8 * cellsize)   # +y = increasing row (match `central`)
        return dzdx, dzdy
    dzdy, dzdx = np.gradient(h, cellsize)          # np.gradient: d/d(axis0), d/d(axis1)
    return dzdx, dzdy


def slope(h, cellsize=1.0, method="central"):
    """Steepest slope as `tan` (rise/run). Compare against tan(angle) directly; convert to
    degrees for display only. Resolution-dependent (06) — state the resolution with any mask."""
    dzdx, dzdy = gradient(h, cellsize, method)
    return np.hypot(dzdx, dzdy)


def aspect(h, cellsize=1.0):
    """Downslope-facing direction in radians (the way water leaves). Note the negations —
    the raw gradient points uphill; getting this wrong flips every orientation mask 180deg."""
    dzdx, dzdy = gradient(h, cellsize)
    return np.arctan2(-dzdy, -dzdx)


def northness(aspect_field):
    """+1 facing north (row 0), -1 facing south. Row index increases SOUTHWARD (row 0 = north), so
    the north-facing component is `-sin(aspect)`, not `+sin(aspect)` — without the minus a north-facing
    slope reads -1 and snow/shade masks land on the sunny south face. Snow lingers on north faces
    (N. hemisphere); one term, large payoff (06)."""
    return -np.sin(np.asarray(aspect_field, dtype=np.float64))


def normals(h, cellsize=1.0):
    """Unit surface normals as an (H, W, 3) array — normalize((-dzdx, -dzdy, 1)). The z
    component is 1 (not cellsize): the gradients already carry cellsize."""
    dzdx, dzdy = gradient(h, cellsize, method="horn")
    nz = 1.0 / np.sqrt(dzdx * dzdx + dzdy * dzdy + 1.0)
    return np.stack([-dzdx * nz, -dzdy * nz, nz], axis=-1)


# --------------------------------------------------------------------------- #
# curvature (Zevenbergen & Thorne 1987)
# --------------------------------------------------------------------------- #
def curvature(h, cellsize=1.0, kind="profile", eps=1e-12):
    """Zevenbergen-Thorne curvature on the 3x3 window. `kind`:
      profile - along steepest descent (<0 convex ridge/lip, >0 concave valley floor);
      plan    - across it (flow convergence proxy: >0 hollows, <0 spurs);
      mean    - generic convex/concave.
    Signs vary between tools (06) — render once over a ridge to confirm. A 2nd derivative,
    so compute on R32F before export or it prints the quantisation staircase."""
    h = np.asarray(h, dtype=np.float64)
    p = np.pad(h, 1, mode="edge")
    z1, z2, z3 = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    z4, z5, z6 = p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:]
    z7, z8, z9 = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    L = cellsize
    D = ((z4 + z6) / 2 - z5) / L ** 2
    E = ((z2 + z8) / 2 - z5) / L ** 2
    F = (-z1 + z3 + z7 - z9) / (4 * L ** 2)
    G = (-z4 + z6) / (2 * L)
    H = (z2 - z8) / (2 * L)
    q = G * G + H * H
    if kind == "mean":
        return ((1 + G ** 2) * E * 2 - 2 * G * H * F + (1 + H ** 2) * D * 2) \
            / (2 * np.power(1 + G ** 2 + H ** 2, 1.5))
    safe = np.where(q < eps, 1.0, q)
    if kind == "plan":
        c = 2 * (D * H ** 2 + E * G ** 2 - F * G * H) / safe
    else:                                          # profile: +ve in concave valley floors, matching the
        c = 2 * (D * G ** 2 + E * H ** 2 + F * G * H) / safe   # docstring and `derive_substances` (plan/mean
    return np.where(q < eps, 0.0, c)                            # already use concave-positive; profile was the outlier)


def laplacian(h, cellsize=1.0):
    """The cheap convexity: grad^2 h = (Z2+Z4+Z6+Z8 - 4 Z5)/L^2. Not slope-normalised, but
    one op and usually what a 'convexity' node wants for a blend (06)."""
    h = np.asarray(h, dtype=np.float64)
    p = np.pad(h, 1, mode="edge")
    return (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
            - 4 * p[1:-1, 1:-1]) / cellsize ** 2


# --------------------------------------------------------------------------- #
# horizon ambient occlusion
# --------------------------------------------------------------------------- #
def _sample_offset(h, drow, dcol):
    """Bilinear sample of the whole field shifted by a constant (drow, dcol), edge-clamped."""
    n, m = h.shape
    ii, jj = np.mgrid[0:n, 0:m].astype(np.float64)
    r = np.clip(ii + drow, 0, n - 1)
    c = np.clip(jj + dcol, 0, m - 1)
    r0 = np.floor(r).astype(np.int64)
    c0 = np.floor(c).astype(np.int64)
    r1 = np.minimum(r0 + 1, n - 1)
    c1 = np.minimum(c0 + 1, m - 1)
    fr, fc = r - r0, c - c0
    return (h[r0, c0] * (1 - fr) * (1 - fc) + h[r0, c1] * (1 - fr) * fc
            + h[r1, c0] * fr * (1 - fc) + h[r1, c1] * fr * fc)


def horizon_ao(h, cellsize=1.0, n_dirs=8, max_dist=None, step_growth=1.1):
    """Horizon-based ambient occlusion in [0,1] (0 = fully open). For each of `n_dirs`
    azimuths, march outward tracking the max horizon angle; occlusion = 1 - mean(cos^2 theta)
    (the cosine-weighted-visibility integral, 06). `max_dist` defaults to ~5% of the extent —
    the radius that darkens valleys and lights peaks rather than mapping crevices."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    if max_dist is None:
        max_dist = 0.05 * max(n, m) * cellsize
    occl = np.zeros_like(h)
    for i in range(int(n_dirs)):
        phi = 2 * np.pi * i / n_dirs
        dr, dc = np.sin(phi), np.cos(phi)
        max_tan = np.zeros_like(h)
        d = cellsize
        while d < max_dist:
            s = _sample_offset(h, dr * d / cellsize, dc * d / cellsize)
            max_tan = np.maximum(max_tan, (s - h) / d)
            d *= step_growth
        occl += np.cos(np.arctan(max_tan)) ** 2
    return 1.0 - occl / n_dirs


# --------------------------------------------------------------------------- #
# wetness index (Beven & Kirkby 1979)
# --------------------------------------------------------------------------- #
def twi(area, slope_tan, cellsize=1.0):
    """Topographic wetness index ln(A_specific / tan slope) — where water lingers. `area` is
    the drainage area A (m^2, ideally MFD so D8 stripes don't print through). BOTH guards are
    mandatory (06): slope->0 on flats sends ln to +inf; A is floored at one cell."""
    a = np.maximum(np.asarray(area, dtype=np.float64) / cellsize, cellsize)
    s = np.maximum(np.asarray(slope_tan, dtype=np.float64), 0.001)
    return np.log(a / s)


# --------------------------------------------------------------------------- #
# selectors: analysis field -> MaskField in [0,1]
# --------------------------------------------------------------------------- #
def smoothstep(lo, hi, x):
    """Hermite smoothstep, clamped to [0,1]. lo may exceed hi (returns a descending edge)."""
    x = np.asarray(x, dtype=np.float64)
    if hi == lo:
        return (x >= hi).astype(np.float64)
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def band_select(field, lo, hi, w):
    """Select a band [lo, hi] of a field with soft edges of half-width `w`. The workhorse
    selector: `height_select`, `slope_select` (thresholds in `tan`) are this with world-unit
    lo/hi. Thresholds carry world units, never [0,1] (06)."""
    field = np.asarray(field, dtype=np.float64)
    return smoothstep(lo - w, lo + w, field) * (1.0 - smoothstep(hi - w, hi + w, field))


MATERIAL_NAMES = ("water", "snow", "rock", "sand", "grass")   # priority-stack order


def derive_materials(height, slope_tan, area, cellsize, *, snow_line=None,
                     channel_area=None, rng_seed=0):
    """A partitioned material stack from the analysis fields (06, Masks -> materials). Returns
    an ordered list of (name, MaskField) built as a PRIORITY STACK — each mask multiplied by
    (1 - sum of the masks above it) — so the masks partition (sum <= 1) and a splatmap won't
    silently rescale them. Order: water -> snow -> rock -> sand -> grass. Thresholds are world
    units; snow_line / channel_area default to sensible fractions of the field's own range."""
    height = np.asarray(height, dtype=np.float64)
    slope_tan = np.asarray(slope_tan, dtype=np.float64)
    area = np.asarray(area, dtype=np.float64)
    lo, hi = float(height.min()), float(height.max())
    span = max(hi - lo, 1e-6)
    if snow_line is None:
        snow_line = lo + 0.75 * span
    if channel_area is None:
        channel_area = float(np.quantile(area, 0.985))
    # low-amplitude noise breakup so thresholds don't read as perfect contours (06)
    rng = np.random.default_rng(rng_seed)
    jitter = 0.04 * span * rng.standard_normal(height.shape)
    hj = height + jitter
    asp = aspect(height, cellsize)
    north = 0.5 + 0.5 * northness(asp)

    raw = [
        ("water", smoothstep(channel_area * 0.5, channel_area, area)),
        ("snow", smoothstep(snow_line, snow_line + 0.08 * span, hj)
         * (1.0 - smoothstep(np.tan(np.radians(40)), np.tan(np.radians(50)), slope_tan))
         * north),
        ("rock", smoothstep(np.tan(np.radians(33)), np.tan(np.radians(45)), slope_tan)),
        ("sand", (1.0 - smoothstep(np.tan(np.radians(5)), np.tan(np.radians(15)), slope_tan))
         * smoothstep(lo, lo + 0.15 * span, hj)),
    ]
    stack, claimed = [], np.zeros_like(height)
    for name, mask in raw:
        m = np.clip(mask, 0.0, 1.0) * (1.0 - claimed)
        stack.append((name, m))
        claimed = np.clip(claimed + m, 0.0, 1.0)
    stack.append(("grass", 1.0 - claimed))              # remainder
    return stack


def dominant_material(stack):
    """Index map (H, W) of the highest-weight material per cell — a categorical MaterialField.
    Index i is stack[i][0]."""
    weights = np.stack([m for _, m in stack], axis=0)
    return np.argmax(weights, axis=0)


def deposit_fill(h, cellsize=1.0, radius=3):
    """Depth by which a loose granular deposit PILES UP to fill the crevices/hollows of a surface —
    a greyscale morphological **closing** minus the surface, clamped ≥ 0 (`ops_filters.closing`, 10).
    Closing fills every concavity up to the structuring radius, so this is deep in gullies and hollows
    and zero on ridges and open flats — exactly how snow drifts into couloirs, sand banks into
    interdunes, and scree ramps up a cliff foot. Scale it by a substance's supply mask, then add it to
    the surface: the deposit surface is smoother than the bedrock beneath. `radius` is in cells."""
    import ops_filters
    closed = ops_filters.closing(np.asarray(h, dtype=np.float64), r=int(radius))
    return np.maximum(closed - np.asarray(h, dtype=np.float64), 0.0)


SUBSTANCE_NAMES = ("water", "snow", "rock", "scree", "sediment", "vegetation", "ground")


def derive_substances(height, slope_tan, area, cellsize, *, climate, rng_seed=0):
    """Place SUBSTANCES by where their material physically accumulates — NOT an elevation colour ramp.
    Colour then comes from the substance itself (snow is white because snow is white), never from
    height. Returns an ordered PRIORITY stack [(name, mask)] partitioned (Σ ≤ 1), names in
    `SUBSTANCE_NAMES`. The placement rules (06 masks, but read as materials):

      * **rock**   — bedrock is exposed where the slope is too steep for anything to rest (> ~40°).
      * **scree**  — loose talus sits at the angle of repose (~26–36°), below the cliffs.
      * **snow**   — a substance, placed where it is COLD ENOUGH (a lapse-rate temperature ∝ elevation)
                     AND the slope can HOLD it (steep faces shed) AND wind LOADS it: poleward/shaded
                     aspects and concave hollows collect, convex ridges are scoured. So the snowline
                     is not a clean contour — it dips on shaded aspects and fills sheltered hollows.
      * **sediment** — deposited where flow is high, the slope is gentle, and the profile is concave.
      * **vegetation** — soil/plants on gentle ground below the snowline (thinning with altitude),
                     only where the `climate` is not arid.
      * **ground** — the bare remainder (soil / regolith / dust).

    `climate` selects which substances exist and the thresholds:
    ``{has_water, has_snow, snowline (0–1 of local relief), snow_soft, has_veg}``."""
    height = np.asarray(height, dtype=np.float64)
    slope_tan = np.asarray(slope_tan, dtype=np.float64)
    area = np.asarray(area, dtype=np.float64)
    lo, hi = float(height.min()), float(height.max())
    span = max(hi - lo, 1e-6)
    hn = (height - lo) / span
    rng = np.random.default_rng(rng_seed)
    jitter = 0.03 * rng.standard_normal(height.shape)                       # break clean threshold contours
    north = 0.5 + 0.5 * northness(aspect(height, cellsize))                 # 1 = poleward / shaded (colder)
    curv = curvature(height, cellsize, kind="profile")                     # >0 concave hollow, <0 convex ridge
    concave = np.clip(curv / (np.percentile(np.abs(curv), 85) + 1e-9), -1.0, 1.0)

    def tand(d):
        return np.tan(np.radians(d))

    rock = smoothstep(tand(38), tand(50), slope_tan)                       # exposed bedrock on cliffs
    scree = smoothstep(tand(26), tand(34), slope_tan) * (1.0 - smoothstep(tand(40), tand(48), slope_tan))

    if climate.get("has_water", True):
        qa = float(np.quantile(area, 0.985))
        water = smoothstep(0.5 * qa, qa, area)                             # channels
    else:
        water = np.zeros_like(height)

    if climate.get("has_snow", False):
        snowline = climate.get("snowline", 0.7)
        soft = climate.get("snow_soft", 0.12)
        drive = (hn - snowline) + 0.12 * (north - 0.5) + 0.06 * concave + 0.03 * jitter
        hold = 1.0 - smoothstep(tand(46), tand(58), slope_tan)              # steep faces shed snow
        snow = np.clip(smoothstep(0.0, soft, drive), 0.0, 1.0) * hold
    else:
        snow = np.zeros_like(height)

    la = np.log1p(area)
    mx = float(la.max())
    sediment = (smoothstep(0.55 * mx, 0.82 * mx, la)
                * np.clip(0.5 + 0.5 * concave, 0.0, 1.0)
                * (1.0 - smoothstep(tand(8), tand(18), slope_tan)))

    if climate.get("has_veg", False):
        veg = 1.0 - smoothstep(tand(32), tand(44), slope_tan)              # gentle enough to hold soil
        if climate.get("has_snow", False):
            veg = veg * (1.0 - np.clip(smoothstep(0.0, climate.get("snow_soft", 0.12),
                                                  hn - climate.get("snowline", 0.7)), 0.0, 1.0))
        veg = veg * np.clip(0.35 + 0.65 * (1.0 - hn), 0.0, 1.0)            # thins with altitude
    else:
        veg = np.zeros_like(height)

    raw = [("water", water), ("snow", snow), ("rock", rock), ("scree", scree),
           ("sediment", sediment), ("vegetation", veg)]
    stack, claimed = [], np.zeros_like(height)
    for name, m in raw:
        mm = np.clip(m, 0.0, 1.0) * (1.0 - claimed)
        stack.append((name, mm))
        claimed = np.clip(claimed + mm, 0.0, 1.0)
    stack.append(("ground", 1.0 - claimed))                                # bare soil / regolith / dust
    return stack
