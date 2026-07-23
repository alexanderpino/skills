"""Physical invariants for the virtual-pipe shallow-water flow (shallow_water.py, Mei et al. 2007).
Water is a real mass-conserving volume, so the checks are the conservation laws: depth stays
non-negative, a closed basin conserves every drop of rain, an open domain balances rain in = out +
stored, and discharge grows downstream as tributaries join."""
import numpy as np

import shallow_water as sw


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
