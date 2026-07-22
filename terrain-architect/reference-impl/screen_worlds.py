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
import erosion_thermal
import landforms
import noise
import render

TILE, CELL = A.TILE, A.CELL


# --- worlds that ARE an archetype already (re-dressed) --------------------------------------
def arrakis(seed=7, n=TILE, cell=CELL):
    """Dune (Wadi Rum + Liwa erg) — the erg (entry 9): open sand where nothing stands."""
    return A.erg(seed, n, cell)


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
        br, bh = rng.uniform(0.04, 0.15) * n, rng.uniform(150.0, 350.0)
        ang = np.arctan2(yy - by, xx - bx)
        wob = 1.0 + 0.22 * noise.fbm(np.cos(ang) * 4 + 10.0 * i, np.sin(ang) * 4 + 10.0, seed + i, octaves=3)
        cap = np.clip((br * wob - np.hypot(xx - bx, yy - by)) / 2.5, 0.0, 1.0)   # irregular FLAT top
        h = np.maximum(h, 25.0 + cap * bh)
    return h + A._g(0.08, seed + 1, n, cell) * 5.0                            # micro-relief; no talus (keep cliffs)


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
    for _ in range(4):                                                        # nunataks: sharp rock peaks
        px, py = rng.integers(int(0.2 * n), int(0.8 * n), 2)
        pk = np.clip(1.0 - np.hypot(xx - px, yy - py) / (rng.uniform(0.045, 0.075) * n), 0.0, 1.0)
        ice = ice + pk ** 1.5 * rng.uniform(320.0, 480.0)
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
    rows = np.arange(n)[:, None] / n
    return seabed + 120.0 * np.exp(-((rows - 0.4) / 0.05) ** 2)               # the tidal wave crest emerges


SCREEN = [
    ("Arrakis (Wadi Rum)", arrakis, "dunes"),
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
        cell_in = analysis.smoothstep(0.0, 0.10, noise.worley(xx, yy, 6, kind="f2f1"))   # 0 on crack lines
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
