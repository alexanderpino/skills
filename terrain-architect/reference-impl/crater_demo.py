"""Impact matrix — asteroid impacts across SIZE (rows) and ANGLE (columns), rendered as a
hillshaded contact sheet (`crater_matrix.png`). Trajectory travels left→right, so downrange is
to the RIGHT of each tile. Each tile is normalised to the crater's own major axis, so the panels
compare SHAPE, not absolute size. Run: `python crater_demo.py`.

Why hillshade, and why noisy: the verified physics core (`crater.py`) is a set of smooth analytic
primitives — a paraboloid bowl, a Gaussian peak, a cosine-weighted ejecta falloff. Rendered raw
on a flat plane they look like "bevel & emboss", not geology. `stamp_impact_natural` below is the
PRESENTATION layer: it keeps the physical dimensions from `crater.py` (diameter, depth, the
simple↔complex split, the elongation and downrange-ejecta laws) but composites them with the
skill's own fractal noise (`noise.py`, chapter 01) so nothing is a perfect circle or dead flat —
irregular rims, slumped/terraced walls, a lumpy central massif, streaky ejecta rays, and, at
grazing angles, a plowed FURROW that deepens downrange with lateral levees and mass piled forward.
It is then shown as ELEVATION via hillshade, so the ejecta reads as excavated earth, not a tint.

The analytic core stays oracle-clean; this layer is a look, deliberately NOT mass-conserving
(the levees, rampart and rough peak add material), and is not part of the verified ledger.
"""
import numpy as np

import crater
import noise
import render

TILE = 240
V = 20000.0                                                # 20 km/s, a typical impact speed
SIZES = [("60 m impactor", 60.0), ("1 km impactor", 1000.0), ("10 km impactor", 10000.0)]
# columns walk the observed oblique-impact sequence (Gault & Wedekind 1978):
#   90° vertical → circular   ·   45° most-probable → mild downrange ejecta bias
#   20° → strong downrange lobe + up-range forbidden wedge (still ~circular; ellipse onset ~12°)
#   3°  → grazing: elongated FURROW, deepens downrange, mass shoved aside and forward
ANGLES = [90.0, 45.0, 20.0, 3.0]                           # from horizontal


def _ang_noise(psi, seed, k=4.0, octaves=4):
    """Seamless fractal noise around the azimuth ψ — sample fbm on a circle so there is no seam
    at ±π. Used for irregular rims, terrace jitter and radial ejecta rays."""
    return noise.fbm(np.cos(psi) * k + 12.0, np.sin(psi) * k + 12.0, seed=seed, octaves=octaves)


def stamp_impact_natural(terrain, cx, cy, cellsize=1.0, *, L=100.0, v=20000.0, g=9.81,
                         angle=45.0, azimuth=0.0, seed=0, deposit_fraction=0.9, rough=1.0):
    """Composite a *natural-looking* impact: the physical skeleton from `crater.py` dressed with
    fractal detail (01). `azimuth` = trajectory heading (0 → downrange = +x). Presentation only —
    for the verified, mass-conserving physics use `crater.stamp_impact`."""
    terrain = np.asarray(terrain, dtype=np.float64).copy()
    n, m = terrain.shape
    D_tc = crater.transient_crater_diameter(L, v, g=g, angle=angle)
    D, is_complex, depth = crater.final_crater(D_tc, g)
    R = 0.5 * D / cellsize
    ecc = crater._ellipticity(angle)
    d = np.clip((90.0 - angle) / 85.0, 0.0, 1.0)           # obliquity: 0 vertical → ~1 grazing
    graze = np.clip((12.0 - angle) / 12.0, 0.0, 1.0)       # plow regime below ~12°
    fp = 1.0 / max(0.10 * R, 1.0)                          # micro-relief frequency (~0.1 R)

    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    dx, dy = xx - cx, yy - cy
    a = np.radians(azimuth)
    xr = dx * np.cos(a) + dy * np.sin(a)                   # +x' downrange
    yr = -dx * np.sin(a) + dy * np.cos(a)
    psi = np.arctan2(yr, xr)
    rim_mod = 1.0 + 0.12 * rough * _ang_noise(psi, seed + 1, k=5, octaves=4)   # irregular rim
    r = np.hypot(xr / ecc, yr) / (R * rim_mod)
    inside = r < 1.0

    # --- bowl with slumped / terraced walls (jittered, not perfect rings) --------------
    bowl = np.where(inside, -depth * (1.0 - r ** 2), 0.0)
    excavated = -np.where(inside, -depth * (1.0 - r ** 2), 0.0).sum() * cellsize ** 2
    nter = 6 if is_complex else 2                          # complex craters terrace; simple barely
    tamp = (0.55 if is_complex else 0.20) * depth * rough
    rj = r * nter + 0.6 * _ang_noise(psi, seed + 8, k=6, octaves=3)
    bowl = np.where(inside, bowl + tamp * (np.round(rj) / nter - r) * np.clip(r, 0, 1) ** 2, bowl)

    # --- plow (grazing): deepen downrange, levees aside, rampart forward ---------------
    if graze > 0:
        along = np.clip(xr / (R * ecc), -1.0, 1.0)         # -1 up-range … +1 downrange
        bowl -= np.where(inside, graze * depth * 0.50 * (0.5 + 0.5 * along), 0.0)   # deepen forward
        flank = np.exp(-((np.abs(yr) / R - 1.0) / 0.30) ** 2) * np.clip(1.0 - np.abs(xr) / (R * ecc), 0, 1)
        bowl += graze * 0.40 * depth * flank               # lateral levees (mass shoved aside)
        term = np.exp(-((xr / (R * ecc) - 1.05) / 0.40) ** 2) * np.exp(-(yr / (R * 1.2)) ** 2)
        bowl += graze * 0.55 * depth * term                # terminal rampart (mass piled forward)

    prof = bowl.copy()

    # --- rough central peak (complex), nudged up-range: a lumpy massif, not a cone ------
    if is_complex:
        off = 0.12 * R * d
        pr = np.hypot(xr + off, yr) / (0.30 * R)
        massif = noise.fbm(xx * fp * 2.2, yy * fp * 2.2, seed + 2)
        ridg = noise.ridged_mf(xx * fp * 1.3, yy * fp * 1.3, seed + 6, octaves=4)
        peak = depth * 0.55 * np.clip(0.55 + 0.9 * massif + 0.5 * ridg, 0.0, None) * np.exp(-pr ** 2)
        prof = prof + np.where(r < 1.2, peak, 0.0)

    # --- ejecta blanket: raised, streaky rays, downrange-biased ------------------------
    rim = np.maximum(r - 1.0, 0.0)
    bf = np.clip((5.0 - angle) / 5.0, 0.0, 1.0)
    span = 0.5 + 0.9 * d * ((1.0 - bf) * np.clip(np.cos(psi), 0, 1) + bf * np.sin(psi) ** 2)
    fall = np.clip(1.0 - rim / (span + 1e-9), 0.0, 1.0) ** 1.3
    azw = crater._ejecta_azimuth_weight(psi, angle)
    rays = 0.5 + 0.5 * _ang_noise(psi, seed + 3, k=14, octaves=3)
    clump = 0.5 + 0.5 * noise.fbm(xx * fp * 1.7, yy * fp * 1.7, seed + 4)
    dep_raw = np.where(r >= 1.0, fall * azw * (0.35 + rough * rays) * (0.5 + clump), 0.0)
    dep_vol = dep_raw.sum() * cellsize ** 2
    prof = prof + dep_raw * (deposit_fraction * excavated / (dep_vol + 1e-12))

    # --- micro-relief everywhere (nothing dead flat) ----------------------------------
    prof = prof + 0.035 * depth * rough * noise.fbm(xx * fp, yy * fp, seed + 5)

    info = {"D_final": D, "complex": is_complex, "depth": depth, "ellipticity": ecc}
    return terrain + prof, info


def panel(L, angle):
    D = crater.final_crater(crater.transient_crater_diameter(L, V, angle=angle))[0]
    ecc = crater._ellipticity(angle)
    cs = D * ecc / (TILE * 0.42)              # frame by the MAJOR axis so ejecta always has room
    h, info = stamp_impact_natural(np.zeros((TILE, TILE)), TILE // 2, TILE // 2, cs,
                                   L=L, v=V, angle=angle, azimuth=0.0, seed=7)   # +x = downrange
    # normalise relief by depth (tiles already normalise size) so SHAPE reads the same whether the
    # crater is a steep 1 km bowl or a shallow 130 km basin — a contact-sheet convention, not physics
    return render.hillshade(h / info["depth"], cellsize=1.0, azimuth=315, altitude=35,
                            z_factor=7.0), info


def main():
    rows, pad = [], 3
    for label, L in SIZES:
        for angle in ANGLES:
            tile, info = panel(L, angle)
            rows.append(tile)
            print(f"  {label:16s} @ {angle:4.0f}°  D_final={info['D_final'] / 1000:6.2f} km  "
                  f"{'complex' if info['complex'] else 'simple '}  ecc={info['ellipticity']:.2f}")
    cols = len(ANGLES)
    nr = len(rows) // cols
    out = np.full((nr * (TILE + pad) + pad, cols * (TILE + pad) + pad, 3), 30, dtype=np.uint8)
    for k, t in enumerate(rows):
        r, c = divmod(k, cols)
        out[pad + r * (TILE + pad):pad + r * (TILE + pad) + TILE,
            pad + c * (TILE + pad):pad + c * (TILE + pad) + TILE] = t
    render.write_png("crater_matrix.png", out)
    print(f"\nwrote crater_matrix.png  rows=sizes {[s for s, _ in SIZES]}  cols=angles {ANGLES}°"
          f"  (downrange → right; hillshaded elevation)")


if __name__ == "__main__":
    main()
