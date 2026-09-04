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


# --- coupled hydraulic erosion (pipe_erode) — Mei 2007 full loop -------------------------------
def test_pipe_erode_conserves_bed_mass_in_a_closed_basin():
    """Erosion moves rock into suspension and back; a walled basin (settle on) keeps every grain."""
    n = 48
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = 100.0 + 40.0 * np.exp(-((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / 120.0)
    r = P.pipe_erode(bed, 20.0, rain=3e-4, iters=250, drain_edges=False, settle=True)
    b = r["budget"]
    asserts.assert_finite(r["bed"], "eroded bed")
    assert abs(b["bed1"] - b["bed0"]) <= 1e-6 * b["bed0"]


def test_pipe_erode_stable_on_steep_terrain():
    """The stability guards (depth-floored/capped velocity, rate-limited erosion) keep a steep cone
    from blowing up — relief stays the same order, values finite."""
    b = inputs.cone(n=64, height=400.0, radius=28.0)
    r = P.pipe_erode(b, 30.0, rain=3e-4, iters=300)
    asserts.assert_finite(r["bed"], "eroded bed")
    assert np.ptp(r["bed"]) < 4.0 * np.ptp(b)


def test_pipe_erode_erodes_slopes_and_deposits_in_the_basin():
    """A steep slope draining into a flat basin: net EROSION on the slope, net DEPOSITION in the
    basin (an alluvial fan), and some sediment exported off the open edge."""
    n = 90
    bed = np.tile(np.linspace(600.0, 0.0, n)[:, None], (1, n))
    bed[n // 2:, :] = 0.0
    bed = bed + 3.0 * np.random.default_rng(1).standard_normal((n, n))
    r = P.pipe_erode(bed, 25.0, rain=4e-4, iters=700, drain_edges=True)
    dz = r["bed"] - bed
    asserts.assert_finite(r["bed"], "eroded bed")
    assert (dz < -1.0).any() and (dz > 1.0).any()
    assert dz[5:n // 2 - 6, :].mean() < 0.0
    assert dz[n // 2:, :].mean() > 0.0
    assert r["budget"]["exported"] > 0.0
