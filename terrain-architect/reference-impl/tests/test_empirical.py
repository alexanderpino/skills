"""Empirical validation (validity rung 5): do the statistics of our generated terrain fall in
the range measured on REAL landscapes? Unlike the oracles, these targets are EMERGENT — we
never set Hack's exponent or the hypsometric integral; they arise from the erosion physics. So
landing in the published real-terrain range is evidence the model produces realistic landscapes,
not just self-consistent ones.

Compared against PUBLISHED statistics (no DEM download): Strahler 1952 hypsometry, Hack 1957.
"""
import functools

import numpy as np
import erosion_streampower as SP
import erosion_thermal as TH
import flow


@functools.lru_cache(maxsize=2)
def _eroded_landscape(n=100, cellsize=1000.0, seed=0):
    """A continental stream-power landscape at steady state (the regime that self-organises
    into realistic drainage)."""
    import noise
    idx = np.arange(n) * cellsize / (n * cellsize * 0.45)
    xx, yy = np.meshgrid(idx, idx)
    f = noise.fbm(xx, yy, seed, octaves=6, base=noise.perlin)
    base = (f - f.min()) / (f.max() - f.min()) * 800.0
    h = SP.stream_power_evolve(base, np.full((n, n), 3e-4), 1e-5, 0.45, 1e3, 80, cellsize)
    return TH.thermal_erosion(h, 0.6, 10, cellsize)


def test_hypsometric_integral_matches_real_basins():
    """Strahler 1952: mature, fluvially-graded basins have a hypsometric integral ~0.4-0.6
    (youthful >0.6, monadnock/old <0.35). Ours is emergent from the erosion."""
    h = _eroded_landscape()
    hi = (h.mean() - h.min()) / (h.max() - h.min())
    assert 0.35 <= hi <= 0.62, f"hypsometric integral {hi:.3f} outside the real mature range"


def test_hacks_law_exponent_matches_real_networks():
    """Hack 1957: mainstream length scales with drainage area as L ~ A^h, h ≈ 0.5-0.6 across
    real basins (classic 0.57; geometric-similarity 0.5). We measure it on our OWN emergent
    drainage network — nothing sets this exponent."""
    h = _eroded_landscape()
    n = h.shape[0]
    hf = flow.priority_flood_fill(h)
    ri, rj, _, dd = SP.receivers(hf, 1000.0)
    A = SP.drainage_area(hf, ri, rj, 1000.0 ** 2)

    # upstream max flow-path length (Hack's L), accumulated high -> low
    Lpath = np.zeros((n, n))
    for idx in np.argsort(hf.ravel())[::-1]:
        i, j = idx // n, idx % n
        r, c = ri[i, j], rj[i, j]
        if r >= 0:
            Lpath[r, c] = max(Lpath[r, c], Lpath[i, j] + dd[i, j])

    interior = np.zeros((n, n), dtype=bool)
    interior[2:-2, 2:-2] = True
    chan = interior & (A > 50 * 1000.0 ** 2) & (Lpath > 0)
    assert chan.sum() > 100
    h_exp = np.polyfit(np.log(A[chan]), np.log(Lpath[chan]), 1)[0]
    assert 0.45 <= h_exp <= 0.62, f"Hack exponent {h_exp:.3f} outside the real range"
