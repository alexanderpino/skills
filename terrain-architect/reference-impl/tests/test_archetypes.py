"""Invariant checks for the archetype compositions (archetypes.py). Each blueprint in
`references/20-archetypes.md` carries a `09` verification signature; this asserts a robust,
generous version of a representative spread — and, above all, that NO composition blows up (the
guard that caught the thermal-erosion instability the alpine build hit). Integration tests over
already-oracle-verified blocks: they check *signatures*, not exact numbers. Run at low resolution
(the archetype functions are resolution-parametric) so the whole set is fast; the montage uses 96².
"""
import numpy as np

import analysis
import archetypes as A
import flow

N = 56


def _local_minima(h):
    c = h[1:-1, 1:-1]
    mn = np.ones_like(c, dtype=bool)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                mn &= c < h[1 + di:h.shape[0] - 1 + di, 1 + dj:h.shape[1] - 1 + dj]
    return int(mn.sum())


def _hi(h):
    return (h.mean() - h.min()) / max(h.max() - h.min(), 1e-9)


def test_archetypes_all_finite_and_not_blown_up():
    """Every archetype in every group: finite, right shape, bounded relief — the regression guard."""
    for name, group, fn, _ in A.ARCHETYPES:
        h = fn(n=N, cell=A.CELL)
        assert h.shape == (N, N), name
        assert np.all(np.isfinite(h)), name
        assert 0.0 < (h.max() - h.min()) < 5e4, f"{name}: relief {(h.max() - h.min()):.2e} — blown up?"


def test_archetype_signatures():
    b = {name: fn(n=N, cell=A.CELL) for name, _, fn, _ in A.ARCHETYPES}

    # orogen maturity: the old (appalachian) range is gentler than the young (alpine) one
    p99 = lambda h: np.degrees(np.arctan(np.percentile(analysis.slope(h, A.CELL), 99)))
    assert p99(b["appalachian (old)"]) < p99(b["alpine orogen"])

    # canyon / mesa: high ground with a deep cut / a flat cap -> high hypsometric integral
    assert _hi(b["canyon + strata"]) > 0.5

    # erg: aeolian -> low relief, slopes no steeper than the sand regime
    assert (b["erg dune sea"].max() - b["erg dune sea"].min()) < 130.0
    assert p99(b["erg dune sea"]) < 45.0

    # basin & range: mostly low basin floor (low HI) punctuated by ranges
    assert _hi(b["basin & range"]) < 0.45

    # tower karst: dissolution plain with residual towers -> low HI (mostly low ground)
    assert _hi(b["tower karst"]) < 0.35

    # stratovolcano: a single dominant central high -> the max sits near the centre
    vo = b["stratovolcano"]
    pk = np.unravel_index(int(np.argmax(vo)), vo.shape)
    assert abs(pk[0] - N / 2) < N * 0.25 and abs(pk[1] - N / 2) < N * 0.25

    # caldera: an ENCLOSED summit basin holds a lake (priority-flood finds real depth)
    ca = b["caldera lake"]
    assert float((flow.priority_flood_fill(ca) - ca).max()) > 20.0

    # fjord & sea cliffs: the sea (z<0) invades and reaches an edge
    for key in ("fjord coast", "sea cliffs & stacks"):
        below = b[key] < 0.0
        assert below.any() and (below[0].any() or below[-1].any() or below[:, 0].any() or below[:, -1].any()), key

    # lunar cratered: impact-dominated -> a field of pits
    assert _local_minima(b["lunar cratered"]) > 6

    # lunar maria: basaltic flood -> very low relief
    assert (b["lunar maria"].max() - b["lunar maria"].min()) < 120.0


def test_archetypes_deterministic():
    assert np.array_equal(A.cratered(seed=3, n=40), A.cratered(seed=3, n=40))
    assert not np.array_equal(A.cratered(seed=3, n=40), A.cratered(seed=4, n=40))


def test_render_tile_photoreal_composite():
    """Every archetype renders to a valid RGB tile via the shared photoreal path (render.photoreal):
    right shape/dtype, in-range, and not a flat single colour (colour + light actually happened)."""
    for name, group, fn, mode in A.ARCHETYPES:
        h = fn(n=N, cell=A.CELL)
        img = A.render_tile(h, name, mode, cell=A.CELL)
        assert img.shape == (N, N, 3) and img.dtype == np.uint8, name
        assert img.min() >= 0 and img.max() <= 255, name
        assert int(img.reshape(-1, 3).std(axis=0).sum()) > 3, f"{name}: render is a flat colour"


def test_photoreal_two_light_floor_and_ao():
    """render.sun_sky_shade never crushes to black (sky floor) and stays <=1; AO only darkens."""
    import render
    h = A.alpine(n=N, cell=A.CELL)
    shade = render.sun_sky_shade(h, A.CELL, sky=0.3)
    assert shade.min() >= 0.3 - 1e-9 and shade.max() <= 1.0 + 1e-9
    flat = np.zeros((N, N, 3)) + 200.0
    occ = np.ones((N, N))                                  # fully occluded -> strictly darker
    lit = render.photoreal(flat, h, A.CELL, ao=occ, ao_strength=0.4, aerial_strength=0.0)
    assert lit.max() <= 200
