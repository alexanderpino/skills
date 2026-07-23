"""Archetype compositions (references/20-archetypes.md) — the PROVINCE altitude: one recognisable
PLACE per tile, assembled from the verified Legal-Order blocks, NOT new algorithms. `graph_demo.py`
runs the generic baseline; each function here is a *diff* that switches the dominant agent, exactly
as `20-archetypes.md` frames the blueprints. Every archetype carries its `09` verification signature
(printed by `main`, asserted in `tests/test_archetypes.py`). Renders a montage → `archetypes.png`.

Coverage: the renderable archetypes across Groups A–L (see `ARCHETYPES.md` for the full ledger of
which of the 29 blueprints render and which are prose-only). Adapt, don't paste (the prime directive
of `20`): illustrative KINDS of place at one small extent, not scale models of the named exemplars.
Functions take (seed, n, cell) so the montage renders at 96² while the tests run fast at low res.
Run: `python archetypes.py`.
"""
import numpy as np

import analysis
import dunes
import erosion_droplet
import erosion_thermal
import flow
import landforms
import noise
import ops_filters
import render
import sims_illustrative as sims

TILE, CELL, SEED = 96, 20.0, 0             # montage: 96² @ 20 m/cell -> 1.92 km (droplet-legal)


def _g(frac, seed, n, cell, kind="perlin", octaves=6):
    """Normalised [0,1] noise whose feature wavelength is `frac` of the tile — resolution-independent."""
    idx = np.arange(n) * cell / (n * cell * frac)
    xx, yy = np.meshgrid(idx, idx)
    if kind == "ridged":
        f = noise.ridged_mf(xx, yy, seed, octaves=octaves)
    elif kind == "worley":
        f = noise.worley(xx, yy, seed, kind="f1")
    else:
        f = noise.fbm(xx, yy, seed, octaves=octaves, base=noise.perlin)
    return (f - f.min()) / max(f.max() - f.min(), 1e-9)


def _xy(n, cell):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return xx, yy


def _wander(n, seed, amp, base=0.5):
    """A NON-periodic wandering centre-line (one column per row) from 1-D fbm — meanders irregular
    in amplitude and spacing, never a sine. Returns an (n, 1) column of centre positions in cells.
    ('Kill the sine wave': real river/fault paths struggle through rock, they don't repeat.)"""
    t = np.arange(n) / n
    w = noise.fbm(t * 3.5, np.full(n, 5.0 + 0.7 * seed), seed, octaves=5)
    w = w - w.mean()
    return (base * n + amp * n * w / (np.max(np.abs(w)) + 1e-9))[:, None]


# ================= Group A · Orogens ========================================================
def alpine(seed=SEED, n=TILE, cell=CELL):
    """Young collisional range: fbm+ridged uplift → droplet fluvial → talus to repose. 09: dissected
    ridges & dendritic valleys, slopes packing toward repose."""
    base = 0.55 * _g(0.20, seed, n, cell, octaves=7) + 0.45 * _g(0.20, seed + 1, n, cell, "ridged")
    base = (base - base.min()) / max(base.max() - base.min(), 1e-9) * 1200.0
    fl = erosion_droplet.droplet_erode(base, n_droplets=11 * n, seed=seed, brush_radius=2)
    return erosion_thermal.thermal_erosion(fl, 0.8, 22, cell, factor=0.15)   # small factor: razor-ridge stability


def appalachian(seed=SEED, n=TILE, cell=CELL):
    """Old, decayed orogen: low uplift, HEAVILY eroded, subdued relief with inherited dendritic
    drainage. 09: low relief, gentle slopes, high drainage density — a MATURE hypsometric curve."""
    base = _g(0.30, seed, n, cell, octaves=6) * 650.0
    fl = erosion_droplet.droplet_erode(base, n_droplets=24 * n, seed=seed, brush_radius=2)
    return erosion_thermal.thermal_erosion(fl, 0.5, 30, cell, factor=0.2)


# ================= Group C · Canyons & tablelands ==========================================
def canyon(seed=SEED, n=TILE, cell=CELL):
    """High plateau with one deeply-incised meandering trunk + tributaries, then STRATA (terrace)
    on the walls. 09: relief concentrated at the trunk; the elevation histogram is stepped."""
    plateau = 260.0 + _g(0.35, seed, n, cell) * 70.0
    cols = np.arange(n)[None, :]
    center = _wander(n, seed, amp=0.17)                                      # irregular meander, not a sine
    trunk = np.clip(1.0 - np.abs(cols - center) / (0.13 * n), 0.0, 1.0) ** 1.4
    h = plateau - trunk * 240.0
    h = erosion_droplet.droplet_erode(h, n_droplets=9 * n, seed=seed, brush_radius=2)
    lo, hi = float(h.min()), float(h.max())
    nb = (h - lo) / max(hi - lo, 1e-9)
    return landforms.terrace(nb, 9, sharpness=6.0, warp_amp=0.04, cellsize=cell) * (hi - lo) + lo


def _butte(shape, bx, by, br, bh, cell, seed=0, ecc=1.0, talus=0.42, repose_tan=0.62,
           sides=6, fault=None, warp=0.12):
    """Local alias for the `landforms.fault_block_butte` primitive (11) — a fault/joint-controlled
    caprock butte (flat top → cliff → talus break on a blocky polygonal footprint). Kept so the
    archetype compositions read locally; the grounded implementation, the SDF-primitive composition
    and the citations live in `landforms.py`."""
    return landforms.fault_block_butte(shape, bx, by, br, bh, cell, seed=seed, ecc=ecc, talus=talus,
                                       repose_tan=repose_tan, sides=sides, fault=fault, warp=warp)


def mesa(seed=SEED, n=TILE, cell=CELL):
    """Tepui / table-mountain: a few LARGE blocky tablelands — flat structural tops under a resistant
    caprock, near-vertical cliffs, a SHARP break to a talus apron, horizontal strata. NOT serpentine
    ridges (thresholding noise makes worms; place solid buttes instead). 09: flat tops, sharp rims,
    caprock→talus break, banded cliffs."""
    base = 30.0 + _g(0.5, seed, n, cell) * 16.0
    h = base.copy()
    rng = np.random.default_rng(seed)
    fault = rng.uniform(0.0, np.pi)                                          # one regional joint strike -> aligned faces
    for i in range(3):                                                       # a few big tablelands
        bx, by = rng.integers(int(0.28 * n), int(0.72 * n), 2)
        br, bh = rng.uniform(0.13, 0.20) * n, rng.uniform(250.0, 350.0)
        h = np.maximum(h, base + _butte((n, n), bx, by, br, bh, cell, seed + i,
                                        ecc=rng.uniform(0.75, 1.35), fault=fault))
    lo, hi = float(h.min()), float(h.max())
    nb = (h - lo) / max(hi - lo, 1e-9)
    return landforms.terrace(nb, 7, sharpness=7.0, warp_amp=0.02, cellsize=cell) * (hi - lo) + lo   # strata


# ================= Group D · Deserts ======================================================
def erg(seed=SEED, n=TILE, cell=CELL):
    """Aeolian dominant: transverse dunes with the signature the Werner slabs (dunes.py) smooth away —
    an ASYMMETRIC profile: a gentle windward (stoss) back rising to the crest, then a steep lee SLIP
    FACE at the sand repose angle, with flat interdune corridors between. Crests run across-wind and
    wander (non-periodic), never a sine. 09: a dominant transverse wavelength, low relief, slip faces
    at ~repose (< 45°)."""
    xx, yy = _xy(n, cell)
    xm, ym = xx * cell, yy * cell                                            # metres; wind blows in +x
    lam = 130.0                                                             # dune wavelength (m)
    march = 0.9 * noise.fbm(xm / 320.0, ym / 900.0, seed, octaves=4)         # break periodicity down-wind
    sinu = 0.35 * noise.fbm(ym / 220.0, np.full_like(ym, 3.0), seed + 5, octaves=4)  # crest sinuosity
    frac = (xm / lam + march + sinu) % 1.0
    s = 0.72                                                                # windward share; lee is the slip face
    prof = np.where(frac < s, frac / s, (1.0 - frac) / (1.0 - s))            # gentle stoss, steep lee
    amp = 8.0 + 13.0 * _g(0.3, seed + 2, n, cell)                            # dune height varies; low -> interdune flat
    return ops_filters.gaussian(amp * prof, 0.5) + _g(0.08, seed + 3, n, cell) * 2.0


def basin_range(seed=SEED, n=TILE, cell=CELL):
    """Basin-and-Range: parallel fault-block ranges separated by flat sediment-filled basins, one a
    dead-flat playa. 09: alternating high ridges / flat floors — a bimodal, banded profile."""
    cols, rows = np.arange(n)[None, :] / n, np.arange(n)[:, None] / n
    # tectonic extension TILTS fault blocks: a gentle alluvial back-slope up to a crest, then a STEEP
    # fault scarp (asymmetric sawtooth, all scarps facing the same way) — not a smooth sine.
    warp = 0.28 * _g(0.3, seed, n, cell) + 0.14 * _g(0.11, seed + 4, n, cell)   # 2-scale noise, no sine
    phase = (2.6 * cols + warp) % 1.0
    block = np.where(phase < 0.78, phase / 0.78, (1.0 - phase) / 0.22)      # ramp up, drop off a scarp
    throw = 300.0 + 260.0 * _g(0.28, seed + 1, n, cell)                     # fault throw varies along strike
    h = block * throw + _g(0.10, seed + 2, n, cell) * 45.0
    floor = np.percentile(h, 32)
    h = np.where(h < floor, floor - 4.0 + _g(0.12, seed + 3, n, cell) * 5.0, h)   # flat alluvial basins / playa
    return erosion_thermal.thermal_erosion(h, 1.0, 5, cell, factor=0.15)    # weather the fault scarps


def badlands(seed=SEED, n=TILE, cell=CELL):
    """Soft flat-lying strata, densely dissected into rills and hoodoos. 09: very high drainage
    density, stepped strata, knife-edge divides."""
    rows = np.arange(n)[:, None] / n
    base = 240.0 * (1.0 - rows) + _g(0.12, seed, n, cell) * 45.0              # gently dipping beds
    nb = (base - base.min()) / max(base.max() - base.min(), 1e-9)
    strata = landforms.terrace(nb, 16, sharpness=8.0, warp_amp=0.02, cellsize=cell) * 260.0
    return erosion_droplet.droplet_erode(strata, n_droplets=16 * n, seed=seed, brush_radius=1)


# ================= Group E · Karst ========================================================
def tower_karst(seed=SEED, n=TILE, cell=CELL):
    """Dissolution: lower the surface in proportion to fracture density, so massive rock survives as
    towers. Fenglin towers spring ABRUPTLY from a flat alluviated plain at ~90° with a basal
    dissolution notch — not tapering cones. 09: BIMODAL elevation (towers vs plain), near-vertical
    flanks, abrupt base."""
    fracture = _g(0.11, seed, n, cell)
    core = analysis.smoothstep(0.66, 0.78, 1.0 - fracture)                   # sparse towers, sharp vertical walls
    h = 20.0 + core * 270.0
    notch = analysis.smoothstep(0.08, 0.24, core) * (1.0 - analysis.smoothstep(0.24, 0.42, core))
    h = h - notch * 12.0                                                     # basal dissolution notch (undercut foot)
    return erosion_thermal.thermal_erosion(h, 0.9, 3, cell, factor=0.12)     # minimal -> keep the flanks steep


# ================= Group F · Volcanic =====================================================
def volcano(seed=SEED, n=TILE, cell=CELL):
    """Stratovolcano: a steep radial cone with a summit crater, gullied by radial drainage. 09:
    near-radial symmetry, radial valleys, a single central high."""
    xx, yy = _xy(n, cell)
    cone = ops_filters.cone(xx - n / 2, yy - n / 2, 0.44 * n, 950.0) + _g(0.06, seed, n, cell) * 25.0
    h = erosion_droplet.droplet_erode(cone, n_droplets=7 * n, seed=seed, brush_radius=1)   # radial gullies
    r = np.hypot(xx - n / 2, yy - n / 2)
    return h - 220.0 * np.clip(1.0 - r / (0.07 * n), 0.0, 1.0)                # summit crater


def caldera(seed=SEED, n=TILE, cell=CELL):
    """Caldera lake: a broad edifice whose summit collapsed to a flat-floored caldera holding a
    lake. 09: a raised rim RING around a flat interior floor filled with water."""
    xx, yy = _xy(n, cell)
    dx, dy = xx - n / 2, yy - n / 2
    r, ang = np.hypot(dx, dy), np.arctan2(dy, dx)
    # a COLLAPSE structure, not a boolean cut: fracture the flanks, jag the rim, rough the floor,
    # and leave a resurgent central dome (a lake island, like Crater Lake's Wizard Island).
    cone = (ops_filters.cone(dx, dy, 0.46 * n, 700.0)
            + (_g(0.09, seed, n, cell) - 0.5) * 110.0 + (_g(0.04, seed + 1, n, cell) - 0.5) * 45.0)
    rim_r = (0.23 + 0.06 * noise.fbm(np.cos(ang) * 5 + 7.0, np.sin(ang) * 5 + 7.0, seed + 2, octaves=4)) * n
    floor = 300.0 + (_g(0.12, seed + 3, n, cell) - 0.5) * 30.0
    dome = 150.0 * np.clip(1.0 - r / (0.09 * n), 0.0, 1.0) ** 1.3
    h = np.where(r < rim_r, np.minimum(cone, floor) + dome, cone)
    return erosion_thermal.thermal_erosion(h, 1.3, 4, cell, factor=0.12)     # slump the fresh scarps


# ================= Group G · Glacial coasts ================================================
def fjord(seed=SEED, n=TILE, cell=CELL):
    """Glacial U-troughs carved into a coastal massif, then flooded to sea level (z=0). 09: the sea
    invades long, narrow, U-floored inlets reaching the open-ocean edge, not a smooth shoreline."""
    massif = _g(0.5, seed, n, cell, "ridged") * 900.0 + 120.0
    rows, cols = np.arange(n)[:, None], np.arange(n)[None, :]
    troughs = np.zeros((n, n))
    for k, frac in enumerate((0.22, 0.5, 0.78)):
        cc = _wander(n, seed + 10 + k, amp=0.05, base=frac)                  # troughs wander, not sines
        troughs = np.maximum(troughs, np.clip(1.0 - ((cols - cc) / (0.08 * n)) ** 2, 0.0, 1.0))
    h = massif - troughs * np.clip(1.0 - rows / n, 0.15, 1.0) * 720.0
    return h - (1.0 - rows / n) * 260.0                                      # regional tilt into the sea


# ================= Group H · Coastal & marine =============================================
def sea_cliffs(seed=SEED, n=TILE, cell=CELL):
    """Wave-attacked upland: a retreating cliff line with a shore platform and residual stacks
    (coastal-retreat sim). 09: a steep cliff at the waterline fronting a near-flat wave-cut bench."""
    rows = np.arange(n)[:, None] / n
    h = _g(0.35, seed, n, cell) * 210.0 + (rows - 0.35) * 300.0              # upland inland, sea at the near edge
    return sims.coastal_retreat(h, 0.0, 8, k_coast=2.0, notch=10.0, cellsize=cell)


# ================= Group K · Anthropogenic ================================================
def ag_terraces(seed=SEED, n=TILE, cell=CELL):
    """Contour agriculture: a hillslope cut into many level rice-paddy / dry-stone benches (fine
    terracing following the contours). 09: a strongly STEPPED elevation histogram, benches ⟂ slope."""
    hill = _g(0.4, seed, n, cell) * 170.0 + 40.0
    nb = (hill - hill.min()) / max(hill.max() - hill.min(), 1e-9)
    return landforms.terrace(nb, 22, sharpness=9.0, warp_amp=0.015, cellsize=cell) * 180.0


# ================= Group L · Off-Earth ====================================================
def cratered(seed=SEED, n=TILE, cell=CELL):
    """Lunar highlands — the regime switch (no liquid water): fluvial backbone OFF, IMPACTS dominate
    (power-law crater sizes). 09: a saturated field of overlapping pits; NO connected drainage."""
    h = _g(0.4, seed, n, cell) * 240.0
    rng = np.random.default_rng(seed)
    for D in np.clip(45.0 * (1.0 - rng.random(n // 2)) ** (-0.8), 30.0, n * cell * 0.32):
        h = landforms.impact_crater(h, int(rng.integers(0, n)), int(rng.integers(0, n)),
                                    float(D), cell, complex_D=1e9)
    return h


def maria(seed=SEED, n=TILE, cell=CELL):
    """Lunar maria — basaltic plains flooding an old basin: very smooth, low, a wrinkle ridge, sparse
    younger craters. 09: very low relief and a MATURE-flat surface with a sinuous ridge."""
    xx, yy = _xy(n, cell)
    h = _g(0.5, seed, n, cell) * 32.0
    h = landforms.anticline(h, xx * cell, yy * cell, 22.0,
                            (0.5 * n * cell, 0.5 * n * cell), (0.7, 0.7), 0.06 * n * cell)   # wrinkle ridge
    rng = np.random.default_rng(seed + 5)
    for _ in range(max(3, n // 20)):
        h = landforms.impact_crater(h, int(rng.integers(0, n)), int(rng.integers(0, n)),
                                    float(rng.uniform(40, 110)), cell, complex_D=1e9)
    return h


def mars(seed=SEED, n=TILE, cell=CELL):
    """Mars — the blended relict world: subdued cratered highlands overprinted by a relict outflow
    channel and aeolian ripples. 09: craters AND a dry sinuous valley AND dune texture together."""
    h = _g(0.4, seed, n, cell) * 170.0
    rng = np.random.default_rng(seed + 2)
    for _ in range(max(6, n // 8)):
        D = float(np.clip(50.0 * (1.0 - rng.random()) ** (-0.7), 40.0, n * cell * 0.26))
        h = landforms.impact_crater(h, int(rng.integers(0, n)), int(rng.integers(0, n)),
                                    D, cell, complex_D=1e9)
    cols = np.arange(n)[None, :]
    cc = _wander(n, seed + 7, amp=0.16, base=0.4)                            # relict outflow channel (wanders)
    h = h - np.clip(1.0 - np.abs(cols - cc) / (0.05 * n), 0.0, 1.0) * 55.0
    ripple = 9.0 * np.sin(2 * np.pi * cols / 5.0) * (_g(0.07, seed + 9, n, cell) > 0.55)
    return h + ripple                                                        # aeolian ripples in patches


ARCHETYPES = [
    ("alpine orogen", "A", alpine, "hillshade"),
    ("appalachian (old)", "A", appalachian, "hillshade"),
    ("canyon + strata", "C", canyon, "hillshade"),
    ("mesa / tepui", "C", mesa, "hillshade"),
    ("erg dune sea", "D", erg, "dunes"),
    ("basin & range", "D", basin_range, "hillshade"),
    ("badlands", "D", badlands, "hillshade"),
    ("tower karst", "E", tower_karst, "hillshade"),
    ("stratovolcano", "F", volcano, "hillshade"),
    ("caldera lake", "F", caldera, "lake"),
    ("fjord coast", "G", fjord, "sea"),
    ("sea cliffs & stacks", "H", sea_cliffs, "sea"),
    ("ag terraces", "K", ag_terraces, "hillshade"),
    ("lunar cratered", "L", cratered, "hillshade"),
    ("lunar maria", "L", maria, "hillshade"),
    ("mars relict", "L", mars, "hillshade"),
]


# --------------------------------------------------------------------------- #
# Colour by SUBSTANCE, not by elevation. Each world is a BIOME: which substances exist (climate) and
# what colour each one IS (snow is white because snow is white). `analysis.derive_substances` places
# them by physics — snow where it's cold + the slope holds it + wind loads it; rock where too steep to
# hold anything; scree at repose; sediment where flow deposits; vegetation on gentle ground below the
# snowline — and the splatmap blend (render.material_rgb) paints each substance its own colour.
# --------------------------------------------------------------------------- #
BIOME = {
    "temperate": {"climate": {"has_water": True, "has_snow": True, "snowline": 0.70, "snow_soft": 0.12, "has_veg": True},
                  "water": (58, 104, 150), "snow": (240, 242, 247), "rock": (112, 108, 102), "scree": (146, 138, 126),
                  "sediment": (150, 142, 116), "vegetation": (84, 114, 64), "ground": (120, 110, 88)},
    "verdant":   {"climate": {"has_water": True, "has_snow": False, "has_veg": True},
                  "water": (60, 110, 140), "snow": (240, 242, 247), "rock": (120, 120, 104), "scree": (150, 148, 120),
                  "sediment": (150, 150, 118), "vegetation": (70, 112, 58), "ground": (116, 128, 90)},
    "arid":      {"climate": {"has_water": True, "has_snow": False, "has_veg": False},
                  "water": (110, 120, 118), "snow": (230, 224, 208), "rock": (150, 96, 66), "scree": (176, 124, 86),
                  "sediment": (208, 184, 136), "vegetation": (120, 130, 80), "ground": (184, 142, 102)},
    "sand":      {"climate": {"has_water": False, "has_snow": False, "has_veg": False},
                  "water": (150, 140, 110), "snow": (230, 224, 208), "rock": (160, 120, 84), "scree": (202, 178, 134),
                  "sediment": (216, 194, 152), "vegetation": (150, 150, 110), "ground": (208, 186, 142)},
    "volcanic":  {"climate": {"has_water": True, "has_snow": True, "snowline": 0.82, "snow_soft": 0.10, "has_veg": True},
                  "water": (52, 100, 140), "snow": (236, 238, 242), "rock": (84, 78, 76), "scree": (112, 104, 100),
                  "sediment": (126, 114, 102), "vegetation": (78, 104, 62), "ground": (98, 92, 86)},
    "mars":      {"climate": {"has_water": False, "has_snow": False, "has_veg": False},
                  "water": (70, 45, 40), "snow": (214, 196, 178), "rock": (120, 64, 46), "scree": (150, 92, 64),
                  "sediment": (198, 132, 88), "vegetation": (150, 110, 80), "ground": (162, 104, 70)},
    "lunar":     {"climate": {"has_water": False, "has_snow": False, "has_veg": False},
                  "water": (72, 72, 76), "snow": (210, 210, 214), "rock": (146, 146, 152), "scree": (120, 120, 126),
                  "sediment": (104, 104, 110), "vegetation": (120, 120, 120), "ground": (122, 122, 128)},
}
FAMILY = {                                        # archetype/world name -> biome
    "alpine orogen": "temperate", "appalachian (old)": "temperate", "tower karst": "verdant",
    "ag terraces": "temperate", "fjord coast": "temperate", "sea cliffs & stacks": "temperate",
    "canyon + strata": "arid", "mesa / tepui": "arid", "basin & range": "arid", "badlands": "arid",
    "erg dune sea": "sand", "stratovolcano": "volcanic", "caldera lake": "volcanic",
    "lunar cratered": "lunar", "lunar maria": "lunar", "mars relict": "mars",
}


def substance_color(h, family, cell=CELL, climate=None):
    """Colour a tile by the SUBSTANCES on it, WITH DEPTH: loose materials pile up and fill the
    crevices (analysis.deposit_fill), building a surface smoother than the bedrock, and snow covers
    the gullies it drifts into. `climate` overrides the biome's default (e.g. a lower snowline).
    Returns (float RGB 0-255, drainage area, piled surface)."""
    bio = BIOME[family]
    clim = climate if climate is not None else bio["climate"]
    slope = analysis.slope(h, cell)
    area = flow.d8_accumulation(flow.priority_flood_fill(h), cell)
    stack = analysis.derive_substances(h, slope, area, cell, climate=clim, rng_seed=0)
    md = {n: m.copy() for n, m in stack}
    fill = analysis.deposit_fill(h, cell, radius=3)                          # depth that fills crevices/hollows
    surf = h.astype(np.float64).copy()

    # loose ground settles into the lows first (desert sand/dust drifts into hollows; sediment fills)
    low = md["sediment"].copy()
    if not clim.get("has_veg", False):                                       # arid: the bare ground IS sand
        low = np.clip(low + md["ground"], 0.0, 1.0)
    surf = surf + low * fill

    if clim.get("has_snow", False):                                          # snow PILES: deep in couloirs/hollows
        snow_depth = md["snow"] * fill
        surf = surf + snow_depth
        span = np.ptp(h) + 1e-9
        deep = analysis.smoothstep(0.015 * span, 0.06 * span, snow_depth)    # where snow filled in, it now covers
        md["snow"] = np.clip(np.maximum(md["snow"], deep), 0.0, 1.0)

    # composite in priority order (splatmap): ground base, then deposits, veg, rock, snow, water on top
    col = render.splat_blend(
        np.zeros(h.shape + (3,), dtype=np.float64) + np.array(bio["ground"], dtype=np.float64),
        [(md["sediment"], bio["sediment"]), (md["scree"], bio["scree"]),
         (md["vegetation"], bio["vegetation"]), (md["rock"], bio["rock"]),
         (md["snow"], bio["snow"]), (md["water"], bio["water"])])
    return col, area, surf


def _rich(h, family, cell=CELL, sea_level=None, azimuth=315.0, altitude=42.0):
    """Colour one tile by substance-with-depth (BIOME), then light the PILED surface with
    render.photoreal (sun+sky, AO, rivers, aerial). Rivers only on wet worlds."""
    col, area, surf = substance_color(h, family, cell)
    ao = analysis.horizon_ao(surf, cell)                                     # AO on the deposit surface
    rivers = None
    if family in ("temperate", "verdant", "volcanic"):                       # wet worlds carry channels
        la = np.log1p(area)
        mx = float(la.max())
        rivers = np.clip((la - 0.87 * mx) / (0.13 * mx + 1e-9), 0.0, 1.0)
    return render.photoreal(col, surf, cell, ao=ao, rivers=rivers, ao_strength=0.38,
                            aerial_strength=0.34, aerial_band=0.20,
                            azimuth=azimuth, altitude=altitude, sea_level=sea_level)


def _flood(img, h, water_mask, blue=(46, 96, 156)):
    """Composite still water (a lake or the sea) over a rendered tile where `water_mask` is True."""
    w = np.asarray(water_mask, dtype=np.float64)[..., None]
    return np.clip(np.asarray(img, np.float64) * (1.0 - 0.78 * w)
                   + np.array(blue, np.float64) * 0.78 * w, 0, 255).astype(np.uint8)


def render_tile(h, name, mode, cell=CELL):
    """Dispatch one archetype to the photoreal composite, honouring its water mode."""
    family = FAMILY.get(name, "temperate")
    if mode == "sea":                                                        # ocean floods z<0, reaches edge
        img = _rich(h, family, cell, sea_level=0.0)
        return _flood(img, h, h < 0.0)
    if mode == "lake":                                                       # only ENCLOSED basins hold water
        img = _rich(h, family, cell)
        return _flood(img, h, (flow.priority_flood_fill(h) - h) > 1.0)
    if mode == "dunes":                                                      # aeolian: low raking sun
        return _rich(h, family, cell, azimuth=270.0, altitude=28.0)
    return _rich(h, family, cell)


def _render(h, mode, cell=CELL):
    """Legacy grey/hypsometric render (kept for screen_worlds' snow/salt fallbacks and quick checks)."""
    if mode == "sea":
        return render.hypsometric(h, cell, sea_level=0.0)
    if mode == "lake":
        water = (flow.priority_flood_fill(h) - h) > 1.0
        hs = render.hillshade(h, cell).astype(np.float64)
        blue = np.array([45, 95, 155], dtype=np.float64)
        w = water[..., None]
        return np.clip(hs * (1.0 - 0.7 * w) + blue * 0.7 * w, 0, 255).astype(np.uint8)
    if mode == "dunes":
        return render.hillshade(h, cell, azimuth=270, altitude=30)
    return render.hillshade(h, cell, azimuth=315, altitude=40)


def _signature(name, group, h, cell=CELL):
    slope = analysis.slope(h, cell)
    p99 = np.degrees(np.arctan(np.percentile(slope, 99)))
    hi = (h.mean() - h.min()) / max(h.max() - h.min(), 1e-9)
    pit = float((flow.priority_flood_fill(h) - h).sum()) * cell * cell
    return (f"  [{group}] {name:20s} relief={h.max() - h.min():7.0f} m  99th-slope={p99:4.1f}°  "
            f"HI={hi:.2f}  pit-storage={pit:.2e} m³")


def montage(tiles, cols=4, pad=4, bg=20):
    n = tiles[0][1].shape[0]
    rows = (len(tiles) + cols - 1) // cols
    out = np.full((rows * (n + pad) + pad, cols * (n + pad) + pad, 3), bg, dtype=np.uint8)
    for k, (_, tile) in enumerate(tiles):
        r, c = divmod(k, cols)
        out[pad + r * (n + pad):pad + r * (n + pad) + n, pad + c * (n + pad):pad + c * (n + pad) + n] = tile
    return out


def labeled_montage(tiles, cols=4, pad=4, title_h=14, bg=(16, 16, 18)):
    """Montage with a caption under each tile (the fix for 'I can't tell which is which'). Needs
    Pillow; falls back to the unlabelled numpy montage if it is missing."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:                                                      # pragma: no cover
        return montage(tiles, cols=cols)
    n = tiles[0][1].shape[0]
    rows = (len(tiles) + cols - 1) // cols
    cw, ch = n + pad, n + pad + title_h
    img = Image.new("RGB", (cols * cw + pad, rows * ch + pad), bg)
    dr = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=10)
    for k, (label, tile) in enumerate(tiles):
        r, c = divmod(k, cols)
        x0, y0 = pad + c * cw, pad + r * ch
        img.paste(Image.fromarray(np.ascontiguousarray(tile)), (x0, y0))
        dr.text((x0 + n / 2, y0 + n + 1), label, font=font, fill=(235, 235, 235), anchor="ma")
    return np.asarray(img)


def main():
    tiles, sigs = [], []
    for name, group, fn, mode in ARCHETYPES:
        h = fn()
        tiles.append((f"{group}. {name}", render_tile(h, name, mode)))
        sigs.append(_signature(name, group, h))
    render.write_png("archetypes.png", labeled_montage(tiles, cols=4))
    print(f"wrote archetypes.png ({len(tiles)} archetypes, {TILE}px tiles, ~{TILE * CELL / 1000:.1f} km each)")
    print("\n09 verification signatures (the tells to check by eye against the montage):")
    for s in sigs:
        print(s)


if __name__ == "__main__":
    main()
