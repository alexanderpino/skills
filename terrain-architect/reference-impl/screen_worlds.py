"""Screen worlds — fictional planets as recombined Earth archetypes (references/20-archetypes.md,
"Screen worlds"). The skill's thesis: a film's planet is never new physics — it is an Earth
archetype in costume, and the *filming location names the archetype*. So each tile here is one of
the `archetypes.py` compositions, re-dressed (render / sea level / material), labelled with the
world, its real filming location, and the archetype it decomposes to. Renders `screen_worlds.png`.

Nothing here invents a process: Arrakis IS the erg, Monument Valley IS the mesa end-member, Crait
IS the evaporite playa. The fiction is set dressing over one substrate and one hydrology. Run:
`python screen_worlds.py`.
"""
import numpy as np

import analysis
import archetypes as A
import erosion_droplet
import erosion_thermal
import landforms
import noise
import render

TILE, CELL = A.TILE, A.CELL


# --- worlds that ARE an archetype already (re-dressed) --------------------------------------
def arrakis(seed=7, n=TILE, cell=CELL):
    """Dune (Wadi Rum) — extreme CONTRAST, not uniform bumpiness: flat wind-swept sand plains
    interrupted by sudden sheer sandstone JEBELS (the sietch country + the open erg)."""
    xx, yy = A._xy(n, cell)
    sand = A._g(0.28, seed, n, cell) * 20.0 + 8.0                            # near-flat sand sea
    rng = np.random.default_rng(seed)
    for i in range(4):                                                       # sheer sandstone jebels
        bx, by = rng.integers(int(0.2 * n), int(0.8 * n), 2)
        br, bh = rng.uniform(0.10, 0.20) * n, rng.uniform(320.0, 520.0)
        ang = np.arctan2(yy - by, xx - bx)
        ecc = rng.uniform(0.6, 1.6)                                          # elongated, irregular jebels
        wob = 1.0 + 0.20 * noise.fbm(np.cos(ang) * 6 + 5.0 * i, np.sin(ang) * 6 + 5.0, seed + i, octaves=4)
        cap = np.clip((br * wob - np.hypot((xx - bx) / ecc, yy - by)) / 1.5, 0.0, 1.0)   # SHEER wall
        sand = np.maximum(sand, 8.0 + cap * bh)
    return erosion_droplet.droplet_erode(sand, n_droplets=5 * n, seed=seed, brush_radius=1)   # flute the walls


def beggars_canyon(seed=3, n=TILE, cell=CELL):
    """Tatooine's Beggar's Canyon (Maguer Gorge) — an entrenched layered gorge (entry 7/13); a
    canyon carved by *vanished* water reads as a relict, exactly like a Martian valley."""
    return A.canyon(seed, n, cell)


# --- worlds needing one re-dressing edit ---------------------------------------------------
def monument_valley(seed=1, n=TILE, cell=CELL):
    """Monument Valley (US-163) — entry 7's END-MEMBER: the plateau all but consumed, leaving a
    mesa→butte→spire remnant series of flat-capped towers standing on an open plain."""
    xx, yy = A._xy(n, cell)
    h = 25.0 + A._g(0.5, seed, n, cell) * 15.0
    rng = np.random.default_rng(seed)
    for i in range(7):                                                        # a mesa→butte→spire series
        bx, by = rng.integers(int(0.15 * n), int(0.85 * n), 2)
        br, bh = rng.uniform(0.04, 0.14) * n, rng.uniform(150.0, 350.0)
        ang = np.arctan2(yy - by, xx - bx)
        ecc = rng.uniform(0.65, 1.5)                                          # asymmetry via ELONGATION, not lobes
        wob = 1.0 + 0.18 * noise.fbm(np.cos(ang) * 7 + 10.0 * i, np.sin(ang) * 7 + 10.0, seed + i, octaves=4)
        rr = np.hypot((xx - bx) / ecc, yy - by) / (br * wob)                  # finely rough edge, not gear teeth
        top = np.where(rr < 1.0, bh, 0.0)                                     # flat top, vertical cliff
        skirt = np.clip((1.9 - rr) / 0.9, 0.0, 1.0) ** 2 * (bh * 0.4)         # TALUS debris apron at the base
        h = np.maximum(h, 25.0 + np.maximum(top, skirt))
    h = h + A._g(0.08, seed + 1, n, cell) * 5.0
    return erosion_droplet.droplet_erode(h, n_droplets=6 * n, seed=seed, brush_radius=1)   # flute the cliffs


def pandora(seed=2, n=TILE, cell=CELL):
    """Pandora's Hallelujah Mountains (modelled on Zhangjiajie) — entry 24's joint-gated pillar
    forest, taller and denser; the fiction is one impossible edit (float them), the terrain is Earth."""
    massive = np.clip(1.0 - A._g(0.10, seed, n, cell) / 0.45, 0.0, 1.0) ** 2.5
    h = 520.0 - (1.0 - massive) * 480.0
    return erosion_thermal.thermal_erosion(h, 1.6, 6, cell, factor=0.12)


def skull_island(seed=4, n=TILE, cell=CELL):
    """Kong: Skull Island (Ha Long Bay) — entry 14's tower karst DROWNED: the plain sits below sea
    level so the sea floods between the towers into a fanged island coast. Rendered with sea at z=0."""
    massive = np.clip(1.0 - A._g(0.11, seed, n, cell) / 0.5, 0.0, 1.0) ** 2
    return 200.0 - (1.0 - massive) * 260.0                                    # towers >0, plain <0 (drowned)


# --- worlds whose conceit is the material / the water, not the height ----------------------
def hoth(seed=5, n=TILE, cell=CELL):
    """Hoth (Finse / Hardangerjøkulen glacier, Norway) — entry 18's glacial machinery with the SEA
    OFF and the ICE CAP ON: a glaciated massif with nunataks (bare rock piercing the ice)."""
    ice = A._g(0.45, seed, n, cell) * 320.0 + 200.0                          # gentle rolling ice sheet
    xx, yy = A._xy(n, cell)
    rng = np.random.default_rng(seed)
    for _ in range(5):                                                        # nunataks: JAGGED rock, not circles
        px, py = int(rng.integers(int(0.2 * n), int(0.8 * n))), int(rng.integers(int(0.2 * n), int(0.8 * n)))
        pr, ecc = rng.uniform(0.05, 0.09) * n, rng.uniform(0.5, 1.6)
        ang = np.arctan2(yy - py, xx - px)
        wob = 1.0 + 0.5 * noise.fbm(np.cos(ang) * 6 + 3.0, np.sin(ang) * 6 + 3.0, seed + px, octaves=4)  # irregular
        rr = np.hypot((xx - px) / ecc, yy - py) / (pr * wob)
        ice = ice + np.clip(1.0 - rr, 0.0, 1.0) ** 1.3 * rng.uniform(320.0, 480.0)
    return ice


def crait(seed=6, n=TILE, cell=CELL):
    """Crait (Salar de Uyuni) — entry 22's evaporite playa: a dead-flat white salt crust over red
    substrate. The conceit is the MATERIAL STACK (`08`), not the relief. Rendered white-over-red."""
    return 10.0 + A._g(0.4, seed, n, cell) * 4.0                              # near-dead-flat


def miller(seed=8, n=TILE, cell=CELL):
    """Interstellar's Miller's world (Icelandic sandur) — a braided outwash plain (the flattest
    surface erosion builds) under ankle-deep water: flood it and it is a SHORELESS ocean, plus one
    mountainous tidal wave. Rendered with sea at z=0."""
    seabed = -5.0 + A._g(0.12, seed, n, cell) * 3.0                           # flat, shallow, braided
    t = np.arange(n) / n
    fw = noise.fbm(t * 3.0, np.full(n, 9.0), seed + 2, octaves=4)
    fw = (fw - fw.mean()) / (np.max(np.abs(fw)) + 1e-9)
    front = 0.42 + 0.09 * fw                                                  # the wave FRONT wanders (not a line)
    amp = 80.0 + 60.0 * (0.5 + 0.5 * noise.fbm(t * 2.0, np.full(n, 2.0), seed + 3, octaves=3))   # varying height
    rows = np.arange(n)[:, None] / n
    return seabed + amp[None, :] * np.exp(-((rows - front[None, :]) / 0.05) ** 2)


SCREEN = [
    ("Arrakis (Wadi Rum)", arrakis, "hillshade"),
    ("Monument Valley", monument_valley, "hillshade"),
    ("Pandora (Zhangjiajie)", pandora, "hillshade"),
    ("Hoth (Norway ice)", hoth, "snow"),
    ("Skull Is. (Ha Long)", skull_island, "sea"),
    ("Beggar's Canyon", beggars_canyon, "hillshade"),
    ("Crait (Salar Uyuni)", crait, "salt"),
    ("Miller's world (sandur)", miller, "sea"),
]


def _render(h, mode, cell=CELL):
    if mode == "snow":                                                        # ice-white, bare rock where steep
        hs = render.hillshade(h, cell)[..., :1].astype(np.float64) / 255.0    # (H,W,1) grey factor
        rock = analysis.smoothstep(np.tan(np.radians(48)), np.tan(np.radians(66)), analysis.slope(h, cell))
        base = np.array([224, 234, 246]) * (1 - rock[..., None]) + np.array([92, 86, 80]) * rock[..., None]
        return np.clip(base * (0.66 + 0.34 * hs), 0, 255).astype(np.uint8)    # keep ice bright in shadow
    if mode == "salt":                                                        # white crust, red polygonal cracks
        idx = np.arange(h.shape[0]) * cell / (h.shape[0] * cell * 0.12)
        xx, yy = np.meshgrid(idx, idx)
        wx = noise.fbm(xx * 0.7, yy * 0.7, 11, octaves=4)                     # DOMAIN WARP the Voronoi so the
        wy = noise.fbm(xx * 0.7 + 3.0, yy * 0.7 + 3.0, 12, octaves=4)         # crack lines are jagged, not straight
        cracks = noise.worley(xx + 1.3 * wx, yy + 1.3 * wy, 6, kind="f2f1")
        cell_in = analysis.smoothstep(0.0, 0.10, cracks)                      # 0 on crack lines
        hs = render.hillshade(h, cell)[..., :1].astype(np.float64) / 255.0
        col = (np.array([238, 236, 230]) * cell_in[..., None]
               + np.array([150, 70, 55]) * (1 - cell_in[..., None]))
        return np.clip(col * (0.78 + 0.22 * hs), 0, 255).astype(np.uint8)
    return A._render(h, mode, cell)                                           # dunes / sea / hillshade


def main():
    tiles = [(label, _render(fn(), mode)) for label, fn, mode in SCREEN]
    render.write_png("screen_worlds.png", A.labeled_montage(tiles, cols=4))
    print(f"wrote screen_worlds.png ({len(tiles)} screen worlds)")
    for label, fn, _ in SCREEN:
        h = fn()
        print(f"  {label:24s} relief={h.max() - h.min():7.0f} m")


if __name__ == "__main__":
    main()
