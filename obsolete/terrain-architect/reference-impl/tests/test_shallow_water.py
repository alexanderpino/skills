"""Physical invariants for the virtual-pipe shallow-water flow (shallow_water.py, Mei et al. 2007).
Water is a real mass-conserving volume, so the checks are the conservation laws: depth stays
non-negative, a closed basin conserves every drop of rain, an open domain balances rain in = out +
stored, and discharge grows downstream as tributaries join. Plus the one invariant that is not a
conservation law: the default `dt` is the step this scheme's own stability condition allows, and the
grid does not slosh at it."""
import math

import numpy as np
import pytest

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


def test_default_dt_is_the_schemes_own_cfl_limit():
    """`dt=None` must give 0.20·cellsize/sqrt(G·cellsize) — the scheme's A/l, not the bed.

    Pinned because nothing else can see it: the bound contains neither the water depth nor the bed
    relief, and a wrong step here does not raise. This line once divided by sqrt(G·ptp(bed)), which
    is the same number only by accident; two cell sizes and two very different reliefs separate the
    two forms (relief-derived, the four `dt`s below would be 0.0029 / 0.0857 / 1.9157 / 6.3855)."""
    for cellsize in (1.0, 30.0, 100.0):
        for relief in (0.5, 500.0):
            bed = np.tile(np.linspace(0.0, relief, 32), (32, 1))
            got = sw.simulate(bed, cellsize, rain=1e-6, iters=1)["budget"]["dt"]
            assert got == pytest.approx(_cfl_dt(cellsize), rel=1e-12), (
                "dt at cellsize=%g, relief=%g m: got %.6g, expected %.6g — the step must come from "
                "the scheme's own A/l = cellsize" % (cellsize, relief, got, _cfl_dt(cellsize)))


def test_no_checkerboard_sloshing_at_the_default_dt():
    """A filled basin must stay smooth: the (pi,pi) mode after 300 steps is < 1e-2 of the depth.

    The failure this catches has no NaN in it — the outflow clamp holds positivity above the CFL
    limit, so depth stays finite and non-negative while the grid sloshes at its Nyquist mode. On this
    gentle basin (0.5 m of relief, 30 m cells) the relief-derived step was 2.19× the limit and this
    assertion fails at 1.8e-1; at the CFL step the amplitude is 5.0e-6, and mass balances to 2.8e-15."""
    n, cellsize, steps = 48, 30.0, 300
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = ((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (n * n)          # a smooth bowl, 0.5 m deep
    bed *= 0.5 / np.ptp(bed)
    rain = 1.0 / (_cfl_dt(cellsize) * steps)                          # fill it to ~1 m over the run
    r = sw.simulate(bed, cellsize, rain=rain, iters=steps, drain_edges=False)
    amp = _checkerboard_amplitude(r["depth"])
    assert amp < 1e-2, "checkerboard mode at %.3e of the mean depth — dt is above the CFL limit" % amp
    assert abs(r["budget"]["stored"] - r["budget"]["rain_in"]) <= 1e-9 * r["budget"]["rain_in"]


def test_source_field_adds_water_and_flow():
    """A per-cell source (e.g. snowmelt) delivers extra water and raises discharge over rain alone."""
    bed = np.tile(np.linspace(100.0, 0.0, 24), (24, 1))
    base = sw.simulate(bed, 20.0, rain=1e-6, iters=200)
    melt = np.zeros((24, 24)); melt[:, :6] = 1e-5                     # a meltwater source band up-slope
    withmelt = sw.simulate(bed, 20.0, rain=1e-6, source_field=melt, iters=200)
    assert withmelt["budget"]["rain_in"] > base["budget"]["rain_in"]
    assert withmelt["discharge"].max() > base["discharge"].max()
