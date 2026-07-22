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
    rows, cols = np.arange(n)[:, None], np.arange(n)[None, :]
    center = n / 2 + 0.19 * n * np.sin(2 * np.pi * rows / (0.9 * n))
    trunk = np.clip(1.0 - np.abs(cols - center) / (0.14 * n), 0.0, 1.0) ** 1.4
    h = plateau - trunk * 240.0
    h = erosion_droplet.droplet_erode(h, n_droplets=9 * n, seed=seed, brush_radius=2)
    lo, hi = float(h.min()), float(h.max())
    nb = (h - lo) / max(hi - lo, 1e-9)
    return landforms.terrace(nb, 9, sharpness=6.0, warp_amp=0.04, cellsize=cell) * (hi - lo) + lo


def mesa(seed=SEED, n=TILE, cell=CELL):
    """Tepui / table-mountain: a resistant caprock holds a FLAT top with near-vertical cliffs over a
    talus-skirted base. 09: bimodal elevation (plateau top vs base), a flat summit, steep rim."""
    field = _g(0.45, seed, n, cell, octaves=5)
    top = analysis.smoothstep(0.52, 0.60, field)                 # sharp plateau caps
    h = 40.0 + top * 340.0 + _g(0.10, seed + 2, n, cell) * 12.0
    return erosion_thermal.thermal_erosion(h, 1.2, 6, cell, factor=0.15)   # skirt the cliff with talus


# ================= Group D · Deserts ======================================================
def erg(seed=SEED, n=TILE, cell=CELL):
    """Aeolian dominant: a sand sheet self-organises into transverse dunes (Werner CA). 09: a
    dominant transverse wavelength, low relief, slopes no steeper than the sand repose regime."""
    sand = np.round(6.0 + 6.0 * _g(0.25, seed, n, cell)).astype(np.int64)
    slabs = dunes.werner_dunes(sand, iters=350, seed=seed, wind=(0, 1))
    return ops_filters.gaussian(slabs.astype(np.float64), 1.0) * 2.5          # smooth to the dune envelope


def basin_range(seed=SEED, n=TILE, cell=CELL):
    """Basin-and-Range: parallel fault-block ranges separated by flat sediment-filled basins, one a
    dead-flat playa. 09: alternating high ridges / flat floors — a bimodal, banded profile."""
    cols, rows = np.arange(n)[None, :] / n, np.arange(n)[:, None] / n
    crest = 0.5 + 0.5 * np.cos(2 * np.pi * 2.2 * cols + 0.7 * np.sin(2 * np.pi * rows))   # wavy N–S ranges
    h = crest ** 2 * (450.0 + 150.0 * _g(0.3, seed, n, cell)) + _g(0.15, seed + 1, n, cell) * 50.0
    floor = np.percentile(h, 40)
    return np.where(h < floor, floor - 5.0 + _g(0.10, seed + 2, n, cell) * 4.0, h)   # flat basins / playa


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
    towers over an alluviated plain. 09: BIMODAL elevation (towers vs plain), steep tower flanks."""
    fracture = _g(0.12, seed, n, cell)
    massive = np.clip(1.0 - fracture / 0.5, 0.0, 1.0) ** 2
    h = 300.0 - (1.0 - massive) * 280.0
    return erosion_thermal.thermal_erosion(h, 1.4, 8, cell, factor=0.15)


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
    cone = ops_filters.cone(xx - n / 2, yy - n / 2, 0.46 * n, 720.0) + _g(0.07, seed, n, cell) * 15.0
    r = np.hypot(xx - n / 2, yy - n / 2)
    return np.where(r < 0.22 * n, np.minimum(cone, 300.0), cone)             # collapse summit to a flat floor


# ================= Group G · Glacial coasts ================================================
def fjord(seed=SEED, n=TILE, cell=CELL):
    """Glacial U-troughs carved into a coastal massif, then flooded to sea level (z=0). 09: the sea
    invades long, narrow, U-floored inlets reaching the open-ocean edge, not a smooth shoreline."""
    massif = _g(0.5, seed, n, cell, "ridged") * 900.0 + 120.0
    rows, cols = np.arange(n)[:, None], np.arange(n)[None, :]
    troughs = np.zeros((n, n))
    for k, frac in enumerate((0.22, 0.5, 0.78)):
        cc = frac * n + 0.08 * n * np.sin(2 * np.pi * rows / (0.6 * n) + k)
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
    rows, cols = np.arange(n)[:, None], np.arange(n)[None, :]
    cc = 0.32 * n + 0.15 * n * np.sin(2 * np.pi * rows / (0.8 * n))          # relict outflow channel
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


def _render(h, mode, cell=CELL):
    if mode == "sea":
        return render.hypsometric(h, cell, sea_level=0.0)
    if mode == "lake":
        # flood only ENCLOSED basins (the caldera) — priority-flood leaves the draining exterior dry
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


def main():
    tiles, sigs = [], []
    for name, group, fn, mode in ARCHETYPES:
        h = fn()
        tiles.append((name, _render(h, mode)))
        sigs.append(_signature(name, group, h))
    render.write_png("archetypes.png", montage(tiles))
    print(f"wrote archetypes.png ({len(tiles)} archetypes, {TILE}px tiles, ~{TILE * CELL / 1000:.1f} km each)")
    print("\n09 verification signatures (the tells to check by eye against the montage):")
    for s in sigs:
        print(s)


if __name__ == "__main__":
    main()
