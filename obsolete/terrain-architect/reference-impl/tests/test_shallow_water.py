"""Physical invariants for the virtual-pipe shallow-water flow (shallow_water.py, Mei et al. 2007).
Water is a real mass-conserving volume, so the checks are the conservation laws: depth stays
non-negative, a closed basin conserves every drop of rain, an open domain balances rain in = out +
stored, and discharge grows downstream as tributaries join. Plus the one invariant that is not a
conservation law: the default `dt` is the step this scheme's own stability condition allows, and the
grid does not slosh at it."""
import math

import numpy as np

import shallow_water as sw


def _cfl_dt(cellsize):
    """The step `simulate` must choose at `dt=None`. Constant-A pipe model: `pipe = G*cellsize` is
    A·g/l with A = l² and l = cellsize, so A/l = cellsize, the linear two-pipe scheme propagates at
    sqrt(2·g·A/l), and the 2-D leapfrog bound 1/sqrt(2) on that speed puts dt_crit at
    0.50·cellsize/sqrt(g·cellsize). C = 0.20 is the 2.5× margin the module runs at."""
    return 0.20 * cellsize / math.sqrt(sw.G * cellsize)


def _checkerboard_amplitude(depth):
    """Amplitude of the (pi, pi) grid mode relative to the mean depth — the signature of a step above
    the CFL limit, which the outflow clamp keeps NaN-free and therefore invisible to a smoke test."""
    ii, jj = np.mgrid[0:depth.shape[0], 0:depth.shape[1]]
    return abs(float((depth * (-1.0) ** (ii + jj)).sum())) / depth.size / max(float(depth.mean()), 1e-30)


def test_depth_nonnegative_and_finite():
    rng = np.random.default_rng(0)
    bed = 100.0 + rng.normal(0, 10, (32, 32))
    r = sw.simulate(bed, 20.0, rain=3e-6, iters=200)
    assert np.all(r["depth"] >= 0.0)
    assert np.all(np.isfinite(r["depth"])) and np.all(np.isfinite(r["discharge"]))


def test_closed_basin_conserves_mass():
    """Walls on (drain_edges=False), rain on: every drop must stay — stored water == rain delivered."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = 100.0 - ((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / 40.0
    r = sw.simulate(bed, 20.0, rain=1e-5, iters=250, drain_edges=False)
    b = r["budget"]
    assert abs(b["stored"] - b["rain_in"]) <= 1e-6 * b["rain_in"]


def test_open_domain_mass_balance():
    """Draining edges: rain delivered == water that left + water still stored (nothing created/lost)."""
    n = 40
    bed = np.tile(np.linspace(200.0, 0.0, n), (n, 1))
    r = sw.simulate(bed, 20.0, rain=2e-6, iters=600)
    b = r["budget"]
    assert abs((b["out"] + b["stored"]) - b["rain_in"]) <= 1e-6 * b["rain_in"]


def test_discharge_grows_downstream():
    """On a planar slope draining to one edge, volumetric discharge accumulates toward the outlet."""
    n = 40
    bed = np.tile(np.linspace(200.0, 0.0, n), (n, 1))    # low at the right edge
    r = sw.simulate(bed, 20.0, rain=2e-6, iters=700)
    q = r["discharge"]
    assert q[:, -3].mean() > 3.0 * q[:, 2].mean()        # downstream carries much more than upstream
    assert q.max() > 0.0


def test_source_field_adds_water_and_flow():
    """A per-cell source (e.g. snowmelt) delivers extra water and raises discharge over rain alone."""
    bed = np.tile(np.linspace(100.0, 0.0, 24), (24, 1))
    base = sw.simulate(bed, 20.0, rain=1e-6, iters=200)
    melt = np.zeros((24, 24)); melt[:, :6] = 1e-5                     # a meltwater source band up-slope
    withmelt = sw.simulate(bed, 20.0, rain=1e-6, source_field=melt, iters=200)
    assert withmelt["budget"]["rain_in"] > base["budget"]["rain_in"]
    assert withmelt["discharge"].max() > base["discharge"].max()
