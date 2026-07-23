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


def test_distance_correction_reduces_grid_bias():
    """The per-neighbour distance correction keeps a cone radial; without it you get
    the plus-shaped artefact (higher directional bias). This is the 09 cone test."""
    h0 = inputs.cone(n=41, height=10.0, radius=20.0)
    good = T.thermal_erosion(h0, 0.3, iters=200, distance_correct=True)
    naive = T.thermal_erosion(h0, 0.3, iters=200, distance_correct=False)
    assert asserts.radial_anisotropy(good) < asserts.radial_anisotropy(naive)
