import numpy as np
import inputs
import asserts
import erosion_pipe as P


def test_depth_stays_nonnegative_and_finite_on_steep_terrain():
    """The step-3 scaling is what prevents negative water and the NaN blow-up. Put a
    slab of water on a steep cone and run many steps: depth must stay >= 0 and finite."""
    b = inputs.cone(n=64, height=40.0, radius=25.0)   # steep
    d = np.full_like(b, 1.0)
    d = P.pipe_water(b, d, iters=300, dt=0.05, pipes=8)
    asserts.assert_finite(d, "water depth")
    asserts.assert_nonneg(d, "water depth")


def test_water_conserved_without_rain_or_evaporation():
    b = inputs.cone(n=64, height=10.0, radius=25.0)
    d0 = np.zeros_like(b)
    d0[28:36, 28:36] = 2.0                            # a central blob
    d = P.pipe_water(b, d0, iters=200, rain=0.0, evap=0.0, dt=0.05)
    asserts.assert_mass_conserved(d0, d, tol=1e-6, msg="pipe water")


def test_8pipe_more_radial_than_4pipe():
    """On flat ground a central water blob should spread radially. The 4-pipe (cardinal)
    stencil forces a diamond; the 8-pipe stencil (with per-pipe length) is more radial."""
    b = inputs.flat(n=81, value=0.0)
    d0 = np.zeros_like(b)
    d0[40, 40] = 200.0                                # a single-cell source
    # measure while the front is still expanding (not the near-uniform steady state)
    d8 = P.pipe_water(b, d0.copy(), iters=45, dt=0.05, pipes=8)
    d4 = P.pipe_water(b, d0.copy(), iters=45, dt=0.05, pipes=4)
    # 4-pipe spreads as an L1 diamond; 8-pipe as a rounder octagon -> more radial
    assert asserts.radial_anisotropy(d8) < asserts.radial_anisotropy(d4)


def test_deterministic():
    b = inputs.cone(n=48, height=10.0)
    d0 = np.ones_like(b) * 0.5
    asserts.assert_deterministic(lambda: P.pipe_water(b, d0, iters=50, dt=0.05))
