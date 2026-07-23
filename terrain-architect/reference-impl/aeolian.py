"""Aeolian abrasion — yardangs (16-arid-desert.md).

`winds.py` gives a wind field and `dunes.py` deposits sand, but nothing yet models wind as an
EROSIVE agent. This is the yardang carve of chapter 16 (Ward & Greeley 1984): streamlined ridges
abraded from a soft, cohesive substrate (playa clay, loess, tuff), aligned with the prevailing wind
— the aeolian twin of a drumlin.

    yardang(h, windDir, softMask):
        align = anisotropic noise with its long axis ‖ windDir      # 01 domain-warp along the wind
        for iterations:
            abr = K_abr · windExposure(p, windDir) · softMask
            h -= abr · saltationWeight(heightAboveFloor(p))          # abrasion is BOTTOM-weighted
        # teardrop ridges: steep blunt nose upwind, tapering lee tail

The detail that sells it (Ward & Greeley): **abrasion is bottom-weighted** — saltating sand only
reaches ~1 m up, so yardangs are undercut at the base and the low ground is cut fastest. Here the
wind-aligned lanes are seeded by anisotropic fBm (long axis ‖ wind); erosion carves those lanes,
weighted toward each cell's height above its local floor, and only within `softMask`. F-tier "look",
invariant-checked: ridges elongate ‖ wind, only soft ground erodes, and the low ground (troughs)
is cut more than the crests (bottom-weighting → streamlined, undercut ridges).
"""
import numpy as np

import noise


def yardang(h, wind, soft_mask, *, iters=10, K_abr=0.6, freq_along=0.018, freq_cross=0.11,
            saltation_h=6.0, floor_reach=3, octaves=4, cellsize=1.0, seed=0):
    """Abrade wind-parallel streamlined ridges (yardangs) into a soft substrate `h`. `wind=(u, v)` in
    (col, row) components sets the ridge long axis. `soft_mask` (scalar or field in [0,1]) confines
    abrasion to erodible rock. Carve-only. Returns a new height field."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    soft = np.broadcast_to(np.asarray(soft_mask, dtype=np.float64), (n, m))
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    u, v = wind
    mag = float(np.hypot(u, v)) + 1e-30
    u, v = u / mag, v / mag
    along = xx * u + yy * v                                     # wind-parallel coordinate
    cross = -xx * v + yy * u                                    # wind-perpendicular coordinate
    # anisotropic seed: low frequency ALONG the wind (long features), higher ACROSS (narrow spacing)
    groove = noise.fbm(along * freq_along, cross * freq_cross, seed, octaves=octaves)
    pot = np.clip(-groove, 0.0, None)                          # carve the low-groove lanes (troughs)
    pot = pot / (pot.max() + 1e-9)
    r = int(floor_reach)
    for _ in range(int(iters)):
        floor = np.minimum.reduce([np.roll(np.roll(h, di, 0), dj, 1)
                                   for di in (-r, 0, r) for dj in (-r, 0, r)])
        salt = np.exp(-np.maximum(h - floor, 0.0) / saltation_h)   # bottom-weighted saltation (~1 m)
        h = h - K_abr * pot * soft * salt
    return h
