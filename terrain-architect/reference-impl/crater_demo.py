"""Impact matrix — asteroid impacts across SIZE (rows) and ANGLE (columns), rendered as a
hillshaded contact sheet (`crater_matrix.png`). Trajectory travels left→right, so downrange is
to the RIGHT of each tile. Each tile is normalised to the crater's own major axis, so the panels
compare SHAPE, not absolute size. Run: `python crater_demo.py`.

Why hillshade, and why noisy: the verified physics core (`crater.py`) is a set of smooth analytic
primitives — a paraboloid bowl, a Gaussian peak, a cosine-weighted ejecta falloff. Rendered raw
on a flat plane they look like "bevel & emboss", not geology. `stamp_impact_natural` below is the
PRESENTATION layer: it keeps the physical dimensions from `crater.py` (diameter, depth, the
simple↔complex split, the elongation and downrange-ejecta laws) but composites them with the
skill's own fractal noise (`noise.py`, chapter 01). The design principle (the crux of the crater
critiques): keep the CAVITY a smooth near-circular bowl — a hypervelocity impact is a point-source
explosion, so the hole is circular at all but grazing angles — and put the chaos in the displaced
MASS. So it adds a distinct raised RIM RING (the overturned flap, Pike 1977), an irregular rim/
ejecta outline, terraced walls and a defined central MASSIF on complex craters, and a hummocky
ejecta apron that slopes off the rim and piles heavier + reaches farther DOWNRANGE. Below ~12° the
cavity elongates into an irregular furrow that is DEEPER UP-RANGE (first contact / peak energy;
Schultz) and shallower downrange, with rim mass shoved to the sides. Shown as ELEVATION via
hillshade, so the mass reads as excavated/heaped earth, not a tint.

The analytic core stays oracle-clean; this layer is a look, deliberately NOT mass-conserving
(the rim, apron and rough peak add material), and is not part of the verified ledger.
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
                         angle=45.0, azimuth=0.0, seed=0, rough=1.0):
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

    # The CAVITY stays a smooth (near-circular) bowl — `rc` is clean, so no radial spokes. All the
    # irregularity lives in the RIM + EJECTA outline via a separate perturbed radius `re`. That is
    # also the right physics: a hypervelocity impact digs a circular hole; the chaos is in the mass.
    rc = np.hypot(xr / ecc, yr) / R                        # clean cavity radius (smooth bowl)
    lump = 0.11 + 0.30 * graze                             # break the outline harder toward grazing
    pert = (lump * rough * _ang_noise(psi, seed + 1, k=5, octaves=4)
            + 0.06 * rough * _ang_noise(psi, seed + 11, k=12, octaves=3))
    re = rc - pert                                         # irregular rim / ejecta outline
    inside = rc < 1.0
    azw = crater._ejecta_azimuth_weight(psi, angle)        # ~0.12 (up-range) … 1 (downrange)

    # --- parabolic bowl with terraced walls (complex) — uses the CLEAN rc ---------------
    bowl = np.where(inside, -depth * (1.0 - rc ** 2), 0.0)
    excavated = -bowl.sum() * cellsize ** 2
    nter = 6 if is_complex else 2                          # complex craters terrace; simple barely
    tamp = (0.55 if is_complex else 0.18) * depth * rough
    rj = rc * nter + 0.6 * _ang_noise(psi, seed + 8, k=6, octaves=3)
    bowl = np.where(inside, bowl + tamp * (np.round(rj) / nter - rc) * np.clip(rc, 0, 1) ** 2, bowl)

    # --- grazing asymmetry: DEEPER UP-RANGE — the deepest point and steepest wall sit on the
    # up-range side (first contact / peak energy transfer; Schultz, arXiv 2308.01876), and the
    # floor shallows DOWN-RANGE where material is plowed out. Rim mass is shoved to the SIDES
    # (maximum structural uplift is transverse to the track). ----------------------------------
    if graze > 0:
        along = np.clip(xr / (R * ecc), -1.0, 1.0)         # -1 up-range … +1 downrange
        bowl -= np.where(inside, graze * depth * 0.45 * (0.5 - 0.5 * along), 0.0)   # deepen up-range
        flank = np.exp(-((np.abs(yr) / R - 1.0) / 0.30) ** 2) * np.clip(1.0 - np.abs(xr) / (R * ecc), 0, 1)
        bowl += graze * 0.35 * depth * flank               # transverse (cross-range) rim levees

    prof = bowl.copy()

    # --- RAISED RIM RING: the overturned flap, a ridge above the plain at the cavity edge.
    # Every fresh crater has one (Pike 1977: rim height ~15-20% of depth). Lumpy, and piled
    # higher DOWNRANGE, so the structural mass is asymmetric even though the hole is circular.
    rim_h = (0.32 if not is_complex else 0.24) * depth
    ring = rim_h * np.exp(-((re - 1.0) / 0.10) ** 2)
    ring *= 0.6 + 0.8 * (0.5 + 0.5 * _ang_noise(psi, seed + 9, k=9, octaves=4))    # lumpy crest
    # azimuthal rim mass: uniform when vertical; toward grazing the UP-RANGE rim is starved into a
    # depressed 'forbidden' arc while the downrange rim builds up (Schultz 1996; Gault & Wedekind).
    rim_floor = 0.7 - 0.45 * d
    ring *= rim_floor + (1.0 - rim_floor) * azw
    prof = prof + ring

    # --- DEFINED central peak (complex): an upheaved rough massif rising from the floor ---
    if is_complex:
        off = 0.12 * R * d
        pr = np.hypot(xr + off, yr) / (0.30 * R)
        cone = np.clip(1.0 - pr, 0.0, 1.0) ** 0.8          # a defined mountain, not a broad dome
        rk = (0.6 + 0.5 * noise.ridged_mf(xx * fp * 1.3, yy * fp * 1.3, seed + 6, octaves=4)
              + 0.3 * noise.fbm(xx * fp * 2.6, yy * fp * 2.6, seed + 2))
        prof = prof + depth * 0.80 * cone * np.clip(rk, 0.0, None)                 # below the rim crest

    # --- ejecta apron: slopes DOWN from the rim outward (rim stays the crest), hummocky, and
    # reaches far DOWNRANGE — the asymmetry reads as EXTENT + thickness, not a buried rim.
    rim = np.maximum(re - 1.0, 0.0)
    reach = 0.6 + 2.4 * d * np.clip(np.cos(psi), 0.0, 1.0) + 0.4 * azw             # far downrange
    apron = np.clip(1.0 - rim / (reach + 1e-9), 0.0, 1.0) ** 1.6                   # 1 at rim → 0 out
    hum = (0.55 + 0.45 * noise.fbm(xx * fp * 1.5 + 3.0, yy * fp * 1.5, seed + 4)
           + 0.25 * noise.fbm(xx * fp * 3.4, yy * fp * 3.4, seed + 14))            # multi-scale bumps
    jag = 0.6 + 0.7 * np.clip(noise.ridged_mf(xx * fp * 1.1, yy * fp * 1.1, seed + 15, octaves=4), 0, 1.3)
    rays = 0.85 + 0.15 * _ang_noise(psi, seed + 3, k=13, octaves=3)                # faint long rays
    ejecta = apron * azw * np.clip(hum, 0.0, None) * rays * jag                    # jagged downrange ridges
    prof = prof + 0.24 * depth * np.where(re >= 1.0, ejecta, 0.0)                  # lower than the rim

    # --- micro-relief everywhere (nothing dead flat) ----------------------------------
    prof = prof + 0.03 * depth * rough * noise.fbm(xx * fp, yy * fp, seed + 5)

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
