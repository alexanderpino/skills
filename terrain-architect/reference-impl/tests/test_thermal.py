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
