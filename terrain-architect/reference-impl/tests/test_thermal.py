import numpy as np
import inputs
import asserts
import erosion_thermal as T


def test_converges_below_repose():
    """A cone steeper than repose relaxes until no slope exceeds the repose angle."""
    h0 = inputs.cone(n=41, height=10.0, radius=20.0)   # slope ~ 0.5
    repose = 0.3
    h = T.thermal_erosion(h0, repose_slope=repose, iters=400, factor=0.25)
    assert T.max_slope(h) <= repose + 0.02


def test_stable_on_rough_oversteepened_terrain():
    """The input thermal actually faces: rough, over-steepened terrain with many steep neighbours per
    cell (what hydraulic erosion leaves behind). Sizing the move from the SUM of all steep neighbours
    diverges here (a spike sheds several times its relief and inverts); sizing from the steepest pair
    stays bounded. Mass conservation alone would NOT catch the blow-up (the divergence conserves mass),
    so we assert the field does not explode — at the default factor."""
    rng = np.random.default_rng(0)
    h0 = rng.random((40, 40)) * 100.0
    h = T.thermal_erosion(h0, repose_slope=0.6, iters=40)          # default factor=0.25
    assert np.all(np.isfinite(h))
    assert np.ptp(h) <= np.ptp(h0)                                 # relaxes, never amplifies relief
    assert T.max_slope(h) < T.max_slope(h0)                        # slopes actually decrease


def test_mass_conserved():
    h0 = inputs.cone(n=41, height=10.0, radius=20.0)
    h = T.thermal_erosion(h0, repose_slope=0.3, iters=50)
    asserts.assert_mass_conserved(h0, h, tol=1e-9, msg="thermal")


def test_deterministic_and_finite():
    h0 = inputs.cone(n=41, height=10.0)
    run = lambda: T.thermal_erosion(h0, repose_slope=0.3, iters=30)
    asserts.assert_deterministic(run)
    asserts.assert_finite(run())


def test_vectorised_matches_literal_loop():
    """`thermal_erosion` is the gather-form vectorisation; `_thermal_erosion_loop` is the literal
    cell-by-cell transcription. They must stay numerically identical (float reassociation only)."""
    rng = np.random.default_rng(0)
    for kwargs in ({}, {"distance_correct": False}, {"cellsize": 3.0}, {"factor": 0.4}):
        h0 = rng.random((30, 30)) * 50.0
        fast = T.thermal_erosion(h0, 0.3, iters=20, **kwargs)
        slow = T._thermal_erosion_loop(h0, 0.3, iters=20, **kwargs)
        assert np.allclose(fast, slow, atol=1e-12), f"gather form drifted for {kwargs}"


def test_repose_angle_is_resolution_independent():
    """SCALE RULE (08). Two distinct things have to scale, and this pins both:

    1. MAGNITUDE — `repose_slope` is a slope (tan of the repose angle) multiplied by `cellsize`, so
       the same physical hillslope relaxes to the same ANGLE at any sampling. A raw per-cell drop
       would instead encode atan(drop*n), i.e. a steeper angle on every finer grid.
    2. DISTANCE — talus moves at most one cell per iteration, so covering the same *physical*
       distance takes iterations proportional to n. Holding `iters` fixed leaves finer grids
       under-relaxed (measured: 0.51 / 0.55 / 0.60 at n = 32 / 64 / 128 for a fixed 300 iters).
    """
    extent, repose = 1000.0, 0.5                       # 1 km across, tan(repose angle) = 0.5
    angles = []
    for n in (32, 64, 128):
        cellsize = extent / n                          # the SAME cone, sampled three ways:
        h0 = inputs.cone(n=n + 1, height=300.0, radius=n / 2.0)   # radius in cells -> extent/2 metres
        h = T.thermal_erosion(h0, repose_slope=repose, iters=12 * n, cellsize=cellsize)
        angles.append(T.max_slope(h, cellsize=cellsize))
    for a in angles:
        assert a <= repose + 0.05, f"relaxed past repose: {angles}"
    assert max(angles) - min(angles) < 0.05, f"repose angle drifted with resolution: {angles}"


def test_distance_correction_reduces_grid_bias():
    """The per-neighbour distance correction keeps a cone radial; without it you get
    the plus-shaped artefact (higher directional bias). This is the 09 cone test."""
    h0 = inputs.cone(n=41, height=10.0, radius=20.0)
    good = T.thermal_erosion(h0, 0.3, iters=200, distance_correct=True)
    naive = T.thermal_erosion(h0, 0.3, iters=200, distance_correct=False)
    assert asserts.radial_anisotropy(good) < asserts.radial_anisotropy(naive)
