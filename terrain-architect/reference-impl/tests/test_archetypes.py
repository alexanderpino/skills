"""Invariant checks for the archetype compositions (archetypes.py). Each blueprint in
`references/20-archetypes.md` carries a `09` verification signature ("here is what right looks
like"); this asserts a robust, generous version of each — and, above all, that no composition
blows up (the guard that would have caught the thermal-erosion instability the alpine build hit).
These are integration tests over already-oracle-verified blocks, so they check *signatures*, not
exact numbers. One pass computes all six (the pipelines are the cost)."""
import numpy as np

import analysis
import archetypes as A


def _local_minima(h):
    c = h[1:-1, 1:-1]
    mn = np.ones_like(c, dtype=bool)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                mn &= c < h[1 + di:h.shape[0] - 1 + di, 1 + dj:h.shape[1] - 1 + dj]
    return int(mn.sum())


def _p99_slope_deg(h):
    return np.degrees(np.arctan(np.percentile(analysis.slope(h, A.CELL), 99)))


def test_archetype_signatures():
    built = {name: fn() for name, fn, _ in A.ARCHETYPES}

    # universal: finite, right shape, and NOT blown up (the thermal-instability regression guard)
    for name, h in built.items():
        assert h.shape == (A.TILE, A.TILE), name
        assert np.all(np.isfinite(h)), name
        assert 0.0 < (h.max() - h.min()) < 5e4, f"{name}: relief {(h.max() - h.min()):.3e} — blown up?"

    # alpine — a dissected orogen: substantial relief
    al = built["alpine (orogen)"]
    assert (al.max() - al.min()) > 300.0

    # canyon — a deep trunk cut into a high plateau: high hypsometric integral (mostly high ground)
    cn = built["canyon + strata"]
    assert (cn.mean() - cn.min()) / (cn.max() - cn.min()) > 0.55

    # erg — aeolian: low relief and slopes no steeper than the sand repose regime
    eg = built["erg dune sea"]
    assert (eg.max() - eg.min()) < 130.0 and _p99_slope_deg(eg) < 45.0

    # fjord — the sea (z<0) invades a modest fraction AND reaches the open-ocean edge
    fj = built["fjord coast"]
    below = fj < 0.0
    assert 0.03 < below.mean() < 0.7
    assert below[0].any() or below[-1].any() or below[:, 0].any() or below[:, -1].any()

    # lunar cratered — impact-dominated: a field of pits, not a drained surface
    assert _local_minima(built["lunar cratered"]) > 12

    # tower karst — dissolution: mostly low alluviated plain (low hypsometric integral) with towers
    tk = built["tower karst"]
    assert (tk.mean() - tk.min()) / (tk.max() - tk.min()) < 0.30


def test_archetypes_deterministic():
    """Same seed → same terrain (the caching/regression-baseline contract)."""
    assert np.array_equal(A.cratered(seed=3), A.cratered(seed=3))
    assert not np.array_equal(A.cratered(seed=3), A.cratered(seed=4))
