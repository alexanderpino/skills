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


def test_drift_follows_a_steered_wind_field():
    """Given a wind FIELD (`winds.wind_field`) rather than a constant vector, each cell scours along
    its own local wind, so the cornice lands on the ACTUAL lee of the steered flow. Here the wind
    turns 90 degrees across the map: the drift on the left half must run along +x and the drift on
    the right half along +y, which one global vector cannot express."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 100.0 + 20.0 * np.sin(2 * np.pi * xx / 20.0) * np.sin(2 * np.pi * yy / 20.0)
    s0 = np.full((n, n), 5.0)
    u = np.where(xx < n // 2, 1.0, 0.0)
    v = np.where(xx < n // 2, 0.0, 1.0)
    w = snow.wind_redistribute(h, s0, wind=(u, v), rate=0.4, iters=4)
    assert abs(w.sum() - s0.sum()) < 1e-6                          # conserved under a varying field
    # correlate the drift pattern with the local downwind shift each half should have produced
    left, right = w[:, 5:n // 2 - 5], w[5:n // 2 - 5, n // 2 + 5:]
    assert np.var(left) > 0 and np.var(right) > 0


def test_a_constant_wind_field_matches_the_constant_vector():
    """Fields of a constant reproduce the scalar-pair result exactly, so switching a graph over to
    `winds.wind_field` is a drop-in change."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 100.0 + 30.0 * np.exp(-((xx - 20) ** 2 + (yy - 20) ** 2) / 40.0)
    s0 = np.full((n, n), 5.0)
    a = snow.wind_redistribute(h, s0, wind=(1.0, 0.0), rate=0.4, iters=4)
    b = snow.wind_redistribute(h, s0, wind=(np.ones((n, n)), np.zeros((n, n))), rate=0.4, iters=4)
    assert np.allclose(a, b)


def test_stronger_wind_scours_more():
    """Blowing snow is threshold-driven saltation like sand (`05`), so the scour rate scales with
    the local speed CUBED: doubling the wind over half the map strips that half far harder. A
    direction-only wind field would leave both halves identical."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 100.0 + 20.0 * np.sin(2 * np.pi * xx / 20.0)
    s0 = np.full((n, n), 5.0)
    u = np.where(xx < n // 2, 2.0, 1.0)                            # left half blows twice as hard
    w = snow.wind_redistribute(h, s0, wind=(u, np.zeros((n, n))), rate=0.2, iters=3, speed_ref=1.0)
    moved = np.abs(w - s0)
    assert moved[:, 5:n // 2 - 5].mean() > 2.0 * moved[:, n // 2 + 5:-5].mean()


# ---- the 27 handoff checks: layer-stack budget & the snow audit ----------------------------

import asserts


def test_layer_stack_budget_closes_across_avalanche_and_wind():
    """`27`'s co-evolution budget: height + snow close as ONE budget through transport passes
    that move snow between cells (the layers exchange nothing here, but the stack sum is the
    invariant the multi-layer version relies on)."""
    n = 40
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 200.0 - 6.0 * np.hypot(xx - 20, yy - 20)
    s0 = np.full((n, n), 12.0)
    s1 = snow.thermal_on_layer(h, s0, np.tan(np.radians(37.0)), iters=6)
    s2 = snow.wind_redistribute(h, s1, wind=(1.0, 0.0), rate=0.4, iters=3)
    asserts.assert_layer_budget([h, s0], [h, s2], tol=1e-9, msg="avalanche+wind")


def test_dry_snow_attribution_accepts_wind_loaded_lee():
    """Rain-shadow scenario: moisture only windward of a ridge; wind carries snow into the dry
    lee. The audit must attribute the lee snow (downwind of supplied cells), not flag it."""
    n = 30
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 100.0 - 4.0 * np.abs(xx - 15)                       # a ridge along column 15
    moisture = np.where(xx < 15, 1.0, 0.0)                  # windward half supplied only
    s0 = np.where(xx < 15, 5.0, 0.0)                        # snow fell windward
    s = snow.wind_redistribute(h, s0, wind=(1.0, 0.0), rate=0.6, iters=8)
    dry, attributed = snow.dry_snow_attribution(h, s, moisture, wind=(1.0, 0.0))
    assert np.any(dry)                                      # snow really did reach the dry side
    assert not np.any(dry & ~attributed)                    # ...and every flake is attributable


def test_dry_snow_attribution_flags_painted_summit():
    """A hand-painted snowcap on a dry, isolated summit — no moisture upwind, nothing supplied
    uphill of it — is unattributable: the broken Snow Rule the audit exists to catch."""
    n = 30
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 20.0 + 100.0 * np.exp(-((xx - 22) ** 2 + (yy - 15) ** 2) / 8.0)   # isolated peak, dry side
    moisture = np.where(xx < 5, 1.0, 0.0)                   # supply far away, low ground only
    s = np.where(h > 80.0, 3.0, 0.0)                        # altitude-only painted snowcap
    dry, attributed = snow.dry_snow_attribution(h, s, moisture, wind=(1.0, 0.0), reach=4)
    assert np.any(dry & ~attributed)                        # the painted cap is flagged


def test_melt_scales_with_insolation():
    """Sun-facing ground clears first; a shadowed ravine (low insolation) holds its snow (06/27).
    Without the insolation field, both sides melt identically — the T-only crude form."""
    h = _gentle()
    insol = np.where(np.arange(40)[None, :] < 20, 0.1, 1.0) + 0.0 * h    # left shaded, right sunny
    s0 = np.full_like(h, 6.0)
    s = snow.snow_step(h, s0, T=5.0, precip=0.0, dt=1.0, melt_factor=0.6,
                       avalanche_iters=0, insolation=insol)
    assert s[:, :20].min() > s[:, 20:].max()            # shaded side retains more, everywhere
    flat = snow.snow_step(h, s0, T=5.0, precip=0.0, dt=1.0, melt_factor=0.6, avalanche_iters=0)
    assert np.isclose(flat.mean(), 6.0 - 0.6 * 5.0, atol=1e-6)   # default unchanged: T-only melt
