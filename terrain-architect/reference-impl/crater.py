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
    elongate downrange below it; the excavated bowl volume is redeposited as an ejecta blanket
    that piles DOWNRANGE (mass pushed forward) and starves the up-range side — the forbidden
    zone — splitting into a cross-range butterfly at very low angles. The *placement* of the
    ejecta is a look matched to observation, NOT a ballistic-ejecta simulation, but the amount
    is mass-conserving: what the bowl removes is what the blanket lays back down.

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
    """Azimuthal weight of the ejecta blanket (ψ from DOWNRANGE). Uniform at vertical
    (`(...)^0 = 1`); as the impact tilts, the exponent grows so the blanket concentrates
    **downrange** and the **up-range** side empties (the forbidden zone); at very low angle it
    splits into a cross-range **butterfly** (Gault & Wedekind 1978; Pierazzo & Melosh 2000). A
    small floor keeps a subdued rim all the way around."""
    b = np.clip((90.0 - angle) / 75.0, 0.0, 1.0)           # obliquity: 0 vertical, ~1 grazing
    down = 0.5 + 0.5 * np.cos(psi)                          # 1 downrange, 0 up-range
    w = down ** (5.0 * b)                                   # vertical -> uniform; oblique -> forward
    bf = np.clip((15.0 - angle) / 15.0, 0.0, 1.0)           # butterfly onset
    w = (1.0 - bf) * w + bf * np.sin(psi) ** 2
    return 0.12 + 0.88 * np.clip(w, 0.0, 1.0)


def stamp_impact(terrain, cx, cy, cellsize=1.0, *, L=100.0, v=17000.0, rho_i=STONY,
                 rho_t=2700.0, g=9.81, angle=45.0, azimuth=0.0, deposit_fraction=0.9):
    """Stamp an impact at cell (cx, cy). Returns (terrain, info). `azimuth` = trajectory heading
    in degrees (0 → travelling toward +x = downrange). **Mass-conserving**: the paraboloid bowl
    is excavated, and that volume is redeposited as an ejecta blanket biased **downrange** — so
    an oblique impact punches a hole and piles the debris forward, with a clean up-range forbidden
    zone, rather than just carving an oval. `deposit_fraction` is the share of excavated volume
    that lands as visible ejecta (the rest bulks the floor / escapes)."""
    terrain = np.asarray(terrain, dtype=np.float64).copy()
    n, m = terrain.shape
    D_tc = transient_crater_diameter(L, v, rho_i, rho_t, g, angle)
    D, is_complex, depth = final_crater(D_tc, g)
    R = 0.5 * D / cellsize                                  # radius in cells
    ecc = _ellipticity(angle)
    b = np.clip((90.0 - angle) / 75.0, 0.0, 1.0)

    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    dx, dy = (xx - cx), (yy - cy)
    a = np.radians(azimuth)                                 # rotate so downrange = +x'
    xr = dx * np.cos(a) + dy * np.sin(a)
    yr = -dx * np.sin(a) + dy * np.cos(a)
    r = np.hypot(xr / ecc, yr) / R                          # elongated radial (downrange axis longer)
    psi = np.arctan2(yr, xr)

    bowl = np.where(r < 1.0, -depth * (1.0 - r ** 2), 0.0)  # excavate
    excavated = -bowl.sum() * cellsize ** 2                 # m^3 removed

    # ejecta blanket (mass-conserving): debris piles up just outside the rim and thins
    # outward. DOWNRANGE it is thick and reaches farther; UP-RANGE it is starved (the
    # forbidden zone). Keeping it concentrated near the rim gives it steep flanks, so the
    # debris reads as a lobe shoved forward instead of a faint wash spread thin.
    rim = np.maximum(r - 1.0, 0.0)                          # radii beyond the rim
    span = 0.5 + 1.4 * b * np.clip(np.cos(psi), 0.0, 1.0)   # short up-range, long downrange
    falloff = np.clip(1.0 - rim / (span + 1e-9), 0.0, 1.0) ** 1.4
    dep_raw = np.where(r >= 1.0, falloff * _ejecta_azimuth_weight(psi, angle), 0.0)
    dep_vol = dep_raw.sum() * cellsize ** 2
    deposit = dep_raw * (deposit_fraction * excavated / (dep_vol + 1e-12))   # conserve mass

    prof = bowl + deposit
    if is_complex:                                          # central peak (centred if vertical,
        off = 0.18 * R * b                                 # nudged downrange when oblique)
        pr = np.hypot(xr - off, yr) / (0.18 * R)
        prof += depth * 0.5 * np.exp(-pr ** 2)

    info = {"D_transient": D_tc, "D_final": D, "complex": is_complex, "depth": depth,
            "ellipticity": ecc, "excavated": excavated,
            "deposited": deposit.sum() * cellsize ** 2}
    return terrain + prof, info
