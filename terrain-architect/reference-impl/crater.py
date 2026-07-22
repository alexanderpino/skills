"""Parameterised asteroid impact — crater from impactor size, velocity, density, gravity and
IMPACT ANGLE (11-geological.md, extended for obliquity).

Two tiers, kept honest:

  * SIZE — decisive physics. Collins, Melosh & Marcus 2005 (*Earth Impact Effects Program*,
    Meteoritics & Planetary Science) π-scaling for the transient crater, then the final crater
    and the simple↔complex transition (∝ 1/g). Angle enters through the vertical velocity
    component, `(sinθ)^(1/3)` — a grazing impact digs a smaller crater than a vertical one of
    the same energy. These relations are verified against their published exponents (rung 4).

  * SHAPE under obliquity — PHENOMENOLOGICAL morphology matched to the oblique-impact
    experiments (Gault & Wedekind 1978; Pierazzo & Melosh 2000; Collins et al. 2011): craters
    stay circular above a target-dependent threshold (~5° sand … ~30° rock; ~12° typical) and
    elongate downrange below it; the up-range rim is depressed; ejecta shifts downrange, then
    into a cross-range butterfly with forbidden zones at very low angles. This is a *look*
    matched to observation, NOT a ballistic-ejecta simulation.

Angles are degrees FROM HORIZONTAL (90 = vertical, the most efficient; 45 = most probable).
"""
import numpy as np

# typical densities (kg/m^3): stony 3000, iron ~7900, icy/cometary ~1000; crustal target ~2700.
STONY, IRON, ICY = 3000.0, 7900.0, 1000.0


def transient_crater_diameter(L, v, rho_i=STONY, rho_t=2700.0, g=9.81, angle=45.0):
    """Transient-crater rim diameter (m), Collins/Melosh/Marcus 2005 gravity-regime π-scaling:
        D_tc = 1.161 (ρ_i/ρ_t)^(1/3) L^0.78 v^0.44 g^(-0.22) (sinθ)^(1/3)
    L = impactor diameter (m), v = impact speed (m/s), θ = angle from horizontal."""
    s = max(np.sin(np.radians(angle)), 1e-6)
    return (1.161 * (rho_i / rho_t) ** (1 / 3) * L ** 0.78 * v ** 0.44
            * g ** (-0.22) * s ** (1 / 3))


def transition_diameter(g=9.81):
    """Final-crater diameter of the simple→complex transition (m). ~3.2 km on Earth, scaling
    as 1/g (Melosh 1989; Collins 2005) — so it is *larger* on low-gravity bodies (the Moon)."""
    return 3200.0 * (9.81 / g)


def final_crater(D_tc, g=9.81):
    """(final rim diameter m, is_complex, depth m) from the transient crater (Collins 2005).
    Simple: D = 1.25 D_tc, depth ≈ 0.2 D. Complex: shallower, D = 1.17 D_tc^1.13 / D_c^0.13."""
    Dc = transition_diameter(g)
    D_simple = 1.25 * D_tc
    if D_simple < Dc:
        return D_simple, False, 0.20 * D_simple
    D = 1.17 * D_tc ** 1.13 / Dc ** 0.13
    depth = 0.20 * Dc * (D / Dc) ** 0.3                     # depth/D decreases with size (Pike)
    return D, True, depth


def _ellipticity(angle):
    """Major/minor axis ratio. ~1 (circular) above ~12°, growing toward grazing (Collins 2011)."""
    return 1.0 + 1.2 * np.clip((12.0 - angle) / 12.0, 0.0, 1.0)


def _ejecta_azimuth_weight(psi, angle):
    """Azimuthal modulation of the r^-3 ejecta (ψ measured from DOWNRANGE). Symmetric at high
    angle → downrange-enhanced / up-range-depleted when oblique → cross-range butterfly with
    forbidden zones at very low angle (Gault & Wedekind 1978; Pierazzo & Melosh 2000)."""
    b = np.clip((45.0 - angle) / 45.0, 0.0, 1.0)            # obliquity: 0 vertical, 1 grazing
    downrange = np.clip(1.0 + 0.8 * b * np.cos(psi), 0.0, None)
    if angle >= 15.0:
        return downrange
    butterfly = 0.25 + np.sin(psi) ** 2                     # lobes at ±90°, minima downrange/uprange
    f = np.clip((15.0 - angle) / 15.0, 0.0, 1.0)            # blend in as the impact grazes
    return np.clip((1.0 - f) * downrange + f * butterfly, 0.0, None)


def stamp_impact(terrain, cx, cy, cellsize=1.0, *, L=100.0, v=17000.0, rho_i=STONY,
                 rho_t=2700.0, g=9.81, angle=45.0, azimuth=0.0):
    """Stamp an impact at cell (cx, cy). Returns (terrain, info). `azimuth` is the trajectory
    heading in degrees (0 = travelling toward +x). Morphology: paraboloid bowl (elongated
    downrange when oblique), raised rim (depressed up-range), r^-3 ejecta (azimuthally modulated
    by obliquity), and a central peak for complex craters (offset downrange)."""
    terrain = np.asarray(terrain, dtype=np.float64).copy()
    n, m = terrain.shape
    D_tc = transient_crater_diameter(L, v, rho_i, rho_t, g, angle)
    D, is_complex, depth = final_crater(D_tc, g)
    rim = 0.04 * D
    R = 0.5 * D / cellsize                                  # radius in cells
    ecc = _ellipticity(angle)

    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    dx, dy = (xx - cx), (yy - cy)
    a = np.radians(azimuth)                                 # rotate so downrange = +x'
    xr = dx * np.cos(a) + dy * np.sin(a)                    # downrange coordinate
    yr = -dx * np.sin(a) + dy * np.cos(a)                   # cross-range
    r = np.hypot(xr / ecc, yr) / R                          # elongated radial (downrange axis longer)
    psi = np.arctan2(yr, xr)                                # azimuth from downrange

    prof = np.zeros_like(terrain)
    inside = r < 1.0
    prof += np.where(inside, -depth * (1.0 - r ** 2), 0.0)  # bowl
    rim_mod = 1.0 - 0.25 * np.clip((45.0 - angle) / 45.0, 0.0, 1.0) * (1.0 - np.cos(psi)) / 2.0
    prof += rim * rim_mod * np.exp(-((r - 1.0) / 0.15) ** 2)   # rim, depressed up-range
    ejecta = rim * 0.5 * np.maximum(r, 1.0) ** (-3.0) * _ejecta_azimuth_weight(psi, angle)
    prof += np.where((r >= 1.0) & (r < 3.0), ejecta, 0.0)
    if is_complex:                                          # central peak (centred if vertical,
        off = 0.15 * R * np.clip((45.0 - angle) / 45.0, 0.0, 1.0)   # nudged downrange when oblique)
        pr = np.hypot(xr - off, yr) / (0.18 * R)
        prof += depth * 0.5 * np.exp(-pr ** 2)

    info = {"D_transient": D_tc, "D_final": D, "complex": is_complex, "depth": depth,
            "ellipticity": ecc}
    return terrain + prof, info
