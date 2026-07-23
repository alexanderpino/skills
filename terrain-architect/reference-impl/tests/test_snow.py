"""Invariant tests for the dynamic snowpack (snow.py / 13, Cordonnier 2018).

F-tier "look" held to invariants: accumulate where cold / melt where warm; snow is stripped from
steep ground; the avalanche (thermal on the snow layer) conserves snow, drives the snow surface
below its repose, and fills hollows — the thing a static slope-mask can't do. Not a snow-water
oracle."""
import numpy as np

import snow
import analysis


def _gentle(n=40):
    """Low-relief bumpy ground (everywhere below the shed slope) so accumulation/melt isn't masked
    by shedding."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return 100.0 + 3.0 * np.sin(xx / 6.0) + 3.0 * np.cos(yy / 5.0)


def test_accumulates_where_cold_melts_where_warm():
    h = _gentle()
    T = np.where(np.arange(40)[None, :] < 20, -5.0, 5.0) + 0.0 * h    # left cold, right warm
    s = snow.snow_step(h, np.zeros_like(h), T, precip=2.0, dt=1.0, avalanche_iters=0)
    assert np.all(s[T < 0] > 0.0)          # cold ground accumulated
    assert np.all(s[T > 0] == 0.0)         # warm ground has none


def test_degree_day_melt_removes_existing_snow():
    h = _gentle()
    s0 = np.full_like(h, 10.0)
    warm = snow.snow_step(h, s0, T=8.0, precip=0.0, dt=1.0, melt_factor=0.6, avalanche_iters=0)
    assert warm.max() < 10.0                                        # warm -> lost snow
    assert np.isclose(warm.mean(), 10.0 - 0.6 * 8.0, atol=1e-6)     # exactly meltFactor*T*dt


def test_snow_sheds_off_steep_ground():
    """Snow does not stick to slopes past the shed threshold (50-60 deg)."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 400.0 - 8.0 * xx                                            # a uniform ~83 deg wall
    s = snow.snow_step(h, np.full((n, n), 5.0), T=-10.0, precip=0.0, dt=1.0, avalanche_iters=0)
    assert s.max() < 0.2                                            # essentially all shed


def test_avalanche_conserves_snow_and_lowers_the_surface_slope():
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 200.0 - 6.0 * np.hypot(xx - 20, yy - 20)
    snow0 = np.full((n, n), 20.0)
    av = snow.thermal_on_layer(h, snow0, np.tan(np.radians(37.0)), iters=6)
    assert abs(av.sum() - snow0.sum()) < 1e-6                       # snow conserved exactly
    ms = lambda z: np.hypot(*np.gradient(z)[::-1]).max()
    assert ms(h + av) < ms(h + snow0)                              # snow surface relaxed


def test_avalanche_fills_hollows():
    """Snow slides off steep ground and piles in gullies/hollows — the dynamic behaviour a static
    mask misses. A pit ends up deeper in snow than an open slope cell."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 200.0 - 6.0 * np.hypot(xx - 20, yy - 20)
    h[18:22, 18:22] -= 40.0                                         # a pit near the summit
    av = snow.thermal_on_layer(h, np.full((n, n), 15.0), np.tan(np.radians(37.0)), iters=8)
    assert av[19, 19] > 1.6 * av[6, 6]                             # pit collects far more than the open slope


def test_wind_redistribution_conserves_and_builds_lee_deposits():
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 100.0 + 30.0 * np.exp(-((xx - 20) ** 2 + (yy - 20) ** 2) / 40.0)   # a hill (windward/lee sides)
    s0 = np.full((n, n), 5.0)
    w = snow.wind_redistribute(h, s0, wind=(1.0, 0.0), rate=0.4, iters=4)
    assert abs(w.sum() - s0.sum()) < 1e-6                          # snow conserved
    windward = w[:, 12:19].mean()                                  # up-wind flank (x rising into wind)
    lee = w[:, 21:28].mean()                                       # down-wind flank
    assert lee > windward                                          # scoured windward, deposited lee (cornice)
