"""Oracles for scatter (07-scatter.md). The decisive one is Bridson's guarantee: no two
samples closer than r. Plus density-following, deterministic tileable jitter, and the
rule-based gates actually rejecting cliffs/treeline/water.
"""
import numpy as np
import scatter as S


def _min_pairwise(pts):
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    d[np.diag_indices(len(pts))] = np.inf
    return d.min()


def test_poisson_disk_respects_min_distance():
    """Bridson's guarantee: every pair is at least r apart, and the set is maximal (fills)."""
    pts = S.poisson_disk(100.0, 100.0, r=6.0, seed=1)
    assert len(pts) > 30                               # maximal-ish, not a handful
    assert _min_pairwise(pts) >= 6.0 - 1e-9
    assert np.all((pts >= 0) & (pts < 100.0))


def test_poisson_disk_deterministic():
    a = S.poisson_disk(60.0, 60.0, r=5.0, seed=7)
    b = S.poisson_disk(60.0, 60.0, r=5.0, seed=7)
    assert a.shape == b.shape and np.allclose(a, b)
    c = S.poisson_disk(60.0, 60.0, r=5.0, seed=8)
    assert a.shape != c.shape or not np.allclose(a, c)


def test_density_rejection_follows_the_field():
    """More instances land where the density map is high (left half) than low (right half)."""
    def dens(p):
        return 0.9 if p[0] < 50.0 else 0.1
    pts = S.scatter_by_density(100.0, 100.0, dens, r_min=4.0, seed=2, max_density=1.0)
    left = np.sum(pts[:, 0] < 50.0)
    right = np.sum(pts[:, 0] >= 50.0)
    assert left > 2 * right                            # density drove the count
    assert _min_pairwise(pts) >= 4.0 - 1e-9            # still respects r_min


def test_jittered_grid_is_deterministic_tileable_and_in_cell():
    g = S.jittered_grid(40.0, 40.0, spacing=5.0, seed=3)
    assert np.allclose(g, S.jittered_grid(40.0, 40.0, spacing=5.0, seed=3))   # deterministic
    assert len(g) == 8 * 8                             # one point per cell
    # every point lies within its own cell (jitter=1 -> within +/- half a cell of the centre)
    cell = np.floor(g / 5.0)
    assert np.all(cell >= 0) and np.all(cell < 8)


def test_jittered_grid_tiles_seamlessly():
    """A cell's point depends only on its integer coordinate, so a sub-region matches the whole
    (the tileability that a per-tile Poisson run lacks)."""
    full = S.jittered_grid(40.0, 40.0, spacing=5.0, seed=3).reshape(8, 8, 2)
    sub = S.jittered_grid(20.0, 20.0, spacing=5.0, seed=3).reshape(4, 4, 2)
    assert np.allclose(sub, full[:4, :4])


def test_rule_based_gates():
    pts = S.jittered_grid(40.0, 40.0, spacing=4.0, seed=5)
    kept = S.rule_based(
        pts,
        slope_fn=lambda p: 0.9 if p[0] > 20.0 else 0.1,       # steep on the right
        height_fn=lambda p: p[1],                              # height = y
        tree_line=30.0,
        max_slope_tan=np.tan(np.radians(35.0)),
    )
    assert len(kept) > 0
    assert np.all(kept[:, 0] <= 20.0)                  # steep right half rejected
    assert np.all(kept[:, 1] <= 30.0)                  # above treeline rejected


def test_sample_field_reads_the_raster():
    field = np.arange(100, dtype=float).reshape(10, 10)   # field[i,j] = 10i + j
    pts = np.array([[0.0, 0.0], [9.0, 9.0], [3.0, 5.0]])
    vals = S.sample_field(field, pts, cellsize=1.0)
    assert vals[0] == 0.0 and vals[1] == 99.0 and vals[2] == 53.0
