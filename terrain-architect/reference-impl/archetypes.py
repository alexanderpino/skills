"""Archetype compositions (references/20-archetypes.md) — the PROVINCE altitude: one recognisable
PLACE assembled from the verified Legal-Order blocks, NOT a new algorithm. `graph_demo.py` runs the
generic baseline; each function here is a *diff* from it that switches the dominant agent, exactly
as `20-archetypes.md` frames the blueprints. Every archetype carries its `09` verification signature
(printed by `main`, asserted in `tests/test_archetypes.py`). Renders a montage → `archetypes.png`.

Adapt, don't paste (the prime directive of `20`): these are illustrative KINDS of place at one small
extent, not scale models of the named exemplars. The extent (~2 km, droplet-legal per the SKILL.md
backbone table) keeps every fluvial archetype's backbone legal. Run: `python archetypes.py`.
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

TILE, CELL, SEED = 96, 20.0, 0             # 96^2 @ 20 m/cell -> 1.92 km (droplet backbone legal)
EXTENT = TILE * CELL


def _grid(wavelength, seed, kind="perlin", octaves=6):
    """Normalised [0,1] noise at feature `wavelength` (metres) — the 01 initial condition."""
    idx = np.arange(TILE) * CELL / wavelength
    xx, yy = np.meshgrid(idx, idx)
    if kind == "ridged":
        f = noise.ridged_mf(xx, yy, seed, octaves=octaves)
    elif kind == "worley":
        f = noise.worley(xx, yy, seed, kind="f1")
    else:
        f = noise.fbm(xx, yy, seed, octaves=octaves, base=noise.perlin)
    return (f - f.min()) / max(f.max() - f.min(), 1e-9)


# --- Group A · Orogen — alpine-type (young collisional; fluvial + talus) --------------------
def alpine(seed=SEED):
    """Diff: crystalline **ridged** uplift → mature fluvial dissection → talus to repose. (The real
    Alps' glacial overprint is a separate agent this fluvial-only cut omits.) 09: slopes pack against
    the repose cap; drainage is dendritic and reaches base level."""
    fb = _grid(EXTENT * 0.20, seed, octaves=7)                             # dendritic body
    rg = _grid(EXTENT * 0.20, seed + 1, kind="ridged", octaves=6)          # sharp crests / aretes
    base = 0.55 * fb + 0.45 * rg
    base = (base - base.min()) / max(base.max() - base.min(), 1e-9) * 1200.0
    fluvial = erosion_droplet.droplet_erode(base, n_droplets=11000, seed=seed, brush_radius=2)
    # `factor` below the 0.25 default: the explicit talus step's checkerboard mode goes unstable when
    # many cells exceed repose (the gallery's gentle terrain hides it; ridged uplift tripped it).
    return erosion_thermal.thermal_erosion(fluvial, repose_slope=0.8, iters=22, cellsize=CELL, factor=0.15)


# --- Group A · Canyon — flat-lying strata deeply incised (Grand-Canyon-type) ---------------
def canyon(seed=SEED):
    """Switch: a high plateau with a single deeply-incised meandering trunk + droplet tributaries,
    then **strata** (terrace) exposed on the walls. 09: relief concentrated at the trunk; the
    elevation histogram is stepped (benches), not smooth."""
    plateau = 260.0 + _grid(EXTENT * 0.35, seed) * 70.0
    rows = np.arange(TILE)[:, None]
    cols = np.arange(TILE)[None, :]
    center = TILE / 2 + 18.0 * np.sin(2 * np.pi * rows / 90.0)          # meandering trunk
    trunk = np.clip(1.0 - np.abs(cols - center) / 14.0, 0.0, 1.0) ** 1.4
    h = plateau - trunk * 240.0
    h = erosion_droplet.droplet_erode(h, n_droplets=9000, seed=seed, brush_radius=2)   # side canyons
    lo, hi = float(h.min()), float(h.max())
    nb = (h - lo) / max(hi - lo, 1e-9)
    return landforms.terrace(nb, 9, sharpness=6.0, warp_amp=0.04, cellsize=CELL) * (hi - lo) + lo


# --- Desert erg — aeolian dominant (Namib-type) --------------------------------------------
def erg(seed=SEED):
    """Switch the dominant agent to **aeolian**: a sand sheet self-organises into transverse dunes
    (Werner CA). 09: a dominant transverse wavelength (FFT), low overall relief, crests perpendicular
    to the wind."""
    sand = np.round(6.0 + 6.0 * _grid(EXTENT * 0.25, seed)).astype(np.int64)
    slabs = dunes.werner_dunes(sand, iters=350, seed=seed, wind=(0, 1))     # downwind = +j
    # the CA output is per-cell slab counts (noisy); a light smooth reveals the DUNE envelope
    return ops_filters.gaussian(slabs.astype(np.float64), 1.0) * 2.5         # slab -> metres


# --- Fjord coast — glacial troughs drowned by the sea --------------------------------------
def fjord(seed=SEED):
    """Two agents: glacial **U-troughs** carved into a coastal massif, then flooded to sea level
    (z = 0). 09: the sea invades long, narrow, U-floored inlets (deep, steep-walled) reaching the
    open-ocean edge, not a smooth shoreline."""
    massif = _grid(EXTENT * 0.5, seed, kind="ridged") * 900.0 + 120.0
    rows = np.arange(TILE)[:, None]
    cols = np.arange(TILE)[None, :]
    troughs = np.zeros((TILE, TILE))
    for k, frac in enumerate((0.22, 0.5, 0.78)):
        cc = frac * TILE + 8.0 * np.sin(2 * np.pi * rows / 60.0 + k)
        troughs = np.maximum(troughs, np.clip(1.0 - ((cols - cc) / (0.08 * TILE)) ** 2, 0.0, 1.0))
    coastward = np.clip(1.0 - rows / TILE, 0.15, 1.0)                        # deeper toward the coast
    h = massif - troughs * coastward * 720.0
    return h - (1.0 - rows / TILE) * 260.0                                   # regional tilt into the sea


# --- Off-Earth · lunar cratered highlands — fluvial OFF, cratering dominant ----------------
def cratered(seed=SEED):
    """The regime switch (no liquid water): the fluvial backbone is **off** and **impacts** dominate.
    Stamp a power-law size distribution of craters onto rolling highlands. 09: high crater density
    with overlap (toward saturation) and NO connected drainage — the surface is a field of pits."""
    h = _grid(EXTENT * 0.4, seed) * 240.0
    rng = np.random.default_rng(seed)
    sizes = np.clip(45.0 * (1.0 - rng.random(46)) ** (-0.8), 30.0, EXTENT * 0.32)   # small common
    for D in sizes:
        cx, cy = int(rng.integers(0, TILE)), int(rng.integers(0, TILE))
        h = landforms.impact_crater(h, cx, cy, float(D), CELL, complex_D=1e9)
    return h


# --- Karst tower — dissolution leaves residual towers (Guilin-type) ------------------------
def tower_karst(seed=SEED):
    """Switch the agent to **dissolution**: lower the surface in proportion to fracture density, so
    massive (low-fracture) rock survives as towers over an alluviated plain. 09: a BIMODAL elevation
    histogram (towers vs plain) with steep tower flanks."""
    fracture = _grid(EXTENT * 0.12, seed)                                   # high = fractured
    massive = np.clip(1.0 - fracture / 0.5, 0.0, 1.0) ** 2                  # 1 where very massive
    h = 300.0 - (1.0 - massive) * 280.0                                     # dissolve where fractured
    return erosion_thermal.thermal_erosion(h, repose_slope=1.4, iters=8, cellsize=CELL)  # steep flanks


ARCHETYPES = [
    ("alpine (orogen)", alpine, "hillshade"),
    ("canyon + strata", canyon, "hillshade"),
    ("erg dune sea", erg, "dunes"),
    ("fjord coast", fjord, "sea"),
    ("lunar cratered", cratered, "hillshade"),
    ("tower karst", tower_karst, "hillshade"),
]


def _render(h, mode):
    if mode == "sea":
        return render.hypsometric(h, CELL, sea_level=0.0)
    if mode == "dunes":
        return render.hillshade(h, CELL, azimuth=270, altitude=30)          # sun across the wind
    return render.hillshade(h, CELL, azimuth=315, altitude=40)


def _signature(name, h):
    """The 09 tells from 20-archetypes.md, one line each — the by-eye montage's numeric partner."""
    slope = analysis.slope(h, CELL)
    p99 = np.degrees(np.arctan(np.percentile(slope, 99)))
    hi = (h.mean() - h.min()) / max(h.max() - h.min(), 1e-9)                 # hypsometric integral
    filled = flow.priority_flood_fill(h)
    pit_vol = float((filled - h).sum()) * CELL * CELL                        # depression storage
    return (f"  {name:18s} relief={h.max() - h.min():7.0f} m  99th-slope={p99:4.1f}°  "
            f"HI={hi:.2f}  pit-storage={pit_vol:.2e} m³")


def montage(tiles, cols=3, pad=4, bg=20):
    n = len(tiles)
    rows = (n + cols - 1) // cols
    out = np.full((rows * (TILE + pad) + pad, cols * (TILE + pad) + pad, 3), bg, dtype=np.uint8)
    for k, (_, tile) in enumerate(tiles):
        r, c = divmod(k, cols)
        out[pad + r * (TILE + pad):pad + r * (TILE + pad) + TILE,
            pad + c * (TILE + pad):pad + c * (TILE + pad) + TILE] = tile
    return out


def main():
    tiles, sigs = [], []
    for name, fn, mode in ARCHETYPES:
        h = fn()
        tiles.append((name, _render(h, mode)))
        sigs.append(_signature(name, h))
    render.write_png("archetypes.png", montage(tiles))
    print(f"wrote archetypes.png ({len(tiles)} archetypes, {TILE}px tiles, ~{EXTENT/1000:.1f} km each)")
    print("\n09 verification signatures (the tells to check by eye against the montage):")
    for s in sigs:
        print(s)


if __name__ == "__main__":
    main()
