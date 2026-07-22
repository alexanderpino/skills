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
