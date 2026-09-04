"""Tests for the terrain-aware wind FLOW FIELD (winds.py / 13).

Two groups. The first covers the terrain adjustment — the field's SPEED and DIRECTION responding
to the terrain (Jackson & Hunt crest speed-up, lee shelter behind the 15-degree separation line,
channelling along a confining valley axis). The second is the mass-consistent projection, which
has a closed form and is checked to machine precision.

F-tier "look" held to invariants; not a boundary-layer CFD oracle, and the module says so."""
import numpy as np
import winds


def _hill(n=160, sigma=12.0, height=40.0):
    """A single Gaussian hill, gentle enough that its lee slope stays BELOW the 15-degree
    separation line — so it tests speed-up without any shelter confounding it."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = n / 2.0
    return height * np.exp(-(((xx - c) ** 2 + (yy - c) ** 2) / (2 * sigma ** 2)))


def _escarpment(n=128, height=20.0, ramp=40.0, lee_slope=3.0):
    """A gentle windward ramp with a steep lee face — steeper than the 15-degree shadow line, so it
    DOES separate and shelter its lee (unlike the Gaussian hill above)."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = n / 2.0
    return np.where(xx < c, height * np.clip((xx - c + ramp) / ramp, 0, 1),
                    np.clip(height - lee_slope * (xx - c), 0.0, None))


def _valley(n=160, axis_deg=40.0, wall=0.35):
    """A straight V-valley whose axis runs at `axis_deg` to the +x regional wind."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = n / 2.0
    a = np.deg2rad(axis_deg)
    across = -(xx - c) * np.sin(a) + (yy - c) * np.cos(a)
    return wall * np.abs(across)


def _bearing(dx, dy):
    return float(np.degrees(np.arctan2(dy, dx)))


# --------------------------------------------------------------------------- #
# 1. Terrain adjustment: the field is terrain-AWARE in speed and in direction.

def test_speedup_peaks_at_the_crest_not_on_the_flank():
    """Jackson & Hunt's perturbation scales with the hill's H/L, so the fastest wind is AT the
    crest. This is the defect the fetch-secant `upwind_slope` exists to avoid: a one-cell along-wind
    gradient is maximal at the windward INFLECTION and exactly zero at the crest, which would put
    the wind maximum halfway up the hill."""
    n, ds, sigma = 160, 10.0, 12.0
    h = _hill(n, sigma)
    c = n // 2
    s = winds.terrain_speedup(h, (1.0, 0.0), cellsize=ds, fetch=30)
    assert s[c, c] > s[c, c - int(sigma)]            # crest beats the windward flank
    assert s[c, c] > 1.05                            # ...and there IS a speed-up
    assert np.isclose(s[c, 20], 1.0)                 # far upwind: undisturbed
    assert np.isclose(s[c, c + 30], 1.0)             # lee: no speed-up (shelter's job, not this)


def test_speedup_is_bounded_and_scales_with_hill_steepness():
    """A steeper hill speeds the wind up more (delta_u/u ~ H/L), and never past `max_speedup`."""
    n, ds = 160, 10.0
    c = n // 2
    kw = dict(cellsize=ds, fetch=30, max_speedup=2.0)
    low = winds.terrain_speedup(_hill(n, 12.0, 20.0), (1.0, 0.0), **kw)
    high = winds.terrain_speedup(_hill(n, 12.0, 60.0), (1.0, 0.0), **kw)
    assert high[c, c] > low[c, c]
    assert high.max() <= 2.0 + 1e-12 and low.min() >= 1.0


def test_lee_shelter_slows_the_lee_of_a_separating_face():
    h = _escarpment()
    c = h.shape[0] // 2
    s = winds.lee_shelter(h, (1.0, 0.0), cellsize=1.0, reach=20, shelter=0.35)
    assert np.isclose(s[c, c - 10], 1.0)             # windward: exposed
    assert np.isclose(s[c, c], 1.0)                  # crest: exposed
    assert s[c, c + 5] < 0.5                         # lee: sheltered


def test_a_slope_gentler_than_the_separation_angle_does_not_shelter():
    """The 15-degree shadow line is physics, not decoration: a lee face gentler than tan(15) = 0.268
    keeps the flow attached, so it must NOT be sheltered. (The Gaussian hill's steepest lee slope is
    ~0.20.) Sheltering every lee slope is the classic way this term goes wrong."""
    h = _hill(n=160, sigma=12.0, height=40.0)
    s = winds.lee_shelter(h, (1.0, 0.0), cellsize=10.0, reach=20)
    assert np.allclose(s, 1.0)


def test_wind_turns_to_follow_a_confining_valley():
    """The headline consequence: a valley-floor wind points ALONG THE VALLEY, not along the regional
    wind — which is why a valley dune field trends with the valley (`05`)."""
    for axis_deg in (30.0, 40.0):
        h = _valley(axis_deg=axis_deg)
        c = h.shape[0] // 2
        dx, dy = winds.valley_channel(h, (1.0, 0.0), relief_radius=8.0)
        assert abs(_bearing(dx[c, c], dy[c, c]) - axis_deg) < 5.0


def test_a_ridge_does_not_channel_and_a_plain_does_not_turn():
    """Only CONCAVE cross-relief steers. Air is deflected around a ridge, not channelled along it,
    and an unconfined plain must leave the regional wind exactly alone."""
    n = 160
    c = n // 2
    ridge = -_valley(n=n, axis_deg=40.0)
    dx, dy = winds.valley_channel(ridge, (1.0, 0.0), relief_radius=8.0)
    assert abs(_bearing(dx[c, c], dy[c, c])) < 1.0
    dx, dy = winds.valley_channel(np.zeros((n, n)), (1.0, 0.0), relief_radius=8.0)
    assert np.allclose(dx, 1.0) and np.allclose(dy, 0.0)


def test_terrain_axis_is_defined_on_the_valley_floor():
    """The structure tensor exists precisely because the contour direction (perpendicular to grad h)
    is DEGENERATE on the thalweg, where grad h vanishes by symmetry — the one place channelling
    matters most. The axis must be recovered there, with high coherence."""
    h = _valley(axis_deg=40.0)
    c = h.shape[0] // 2
    ax, ay, coh = winds.terrain_axis(h, relief_radius=8.0)
    bearing = _bearing(ax[c, c], ay[c, c]) % 180.0
    assert abs(bearing - 40.0) < 5.0
    assert coh[c, c] > 0.8                           # a straight canyon is strongly anisotropic


def test_flat_terrain_returns_the_regional_wind_unchanged():
    """The null case: with no terrain there is nothing to adjust, so the field is the constant the
    user authored — no drift from the speed-up, shelter or channelling terms."""
    u, v = winds.wind_field(np.zeros((64, 64)), (0.6, 0.8), 7.0)
    assert np.allclose(winds.speed(u, v), 7.0)
    assert np.allclose(u, 7.0 * 0.6) and np.allclose(v, 7.0 * 0.8)


def test_wind_field_is_terrain_aware_and_divergence_free():
    """End to end: all four chapter steps. The field must still vary with the terrain after the
    projection (a projection that flattened the adjustment would be useless), and satisfy the
    continuity constraint the projection exists to impose."""
    h = _hill(n=160, sigma=12.0)
    u, v = winds.wind_field(h, (1.0, 0.0), 10.0, cellsize=10.0, fetch=30, reach=20)
    sp = winds.speed(u, v)
    assert sp.max() - sp.min() > 0.2                 # terrain left a mark
    assert np.abs(winds.divergence_spectral(u, v)).max() < 1e-9


def test_sample_bilinear_is_exact_on_grid_points_and_wraps():
    field = np.arange(64, dtype=float).reshape(8, 8)
    yy, xx = np.mgrid[0:8, 0:8].astype(float)
    assert np.allclose(winds.sample_bilinear(field, yy, xx), field)
    assert np.allclose(winds.sample_bilinear(field, yy + 8, xx + 8), field)   # periodic


def _divergent_field(n=64, m=64, cellsize=1.0):
    """A wind field with real divergence (sources/sinks)."""
    y = np.arange(n)[:, None] * cellsize
    x = np.arange(m)[None, :] * cellsize
    u0 = np.sin(2 * np.pi * x / (m * cellsize)) + 0.3 * np.cos(2 * np.pi * y / (n * cellsize))
    v0 = np.sin(2 * np.pi * y / (n * cellsize)) * np.ones((n, m))
    return u0, v0


def test_projection_kills_divergence():
    u0, v0 = _divergent_field()
    d0 = np.abs(winds.divergence_spectral(u0, v0)).max()
    assert d0 > 1e-3                                   # the input really is divergent
    u, v = winds.mass_consistent(u0, v0)
    d1 = np.abs(winds.divergence_spectral(u, v)).max()
    assert d1 < 1e-9                                   # corrected field is divergence-free


def test_correction_is_minimal_and_finite():
    """The projection removes only the curl-free part, so the change is bounded and finite."""
    u0, v0 = _divergent_field()
    u, v = winds.mass_consistent(u0, v0)
    assert np.all(np.isfinite(u)) and np.all(np.isfinite(v))
    # central-difference divergence also drops by orders of magnitude
    before = np.abs(winds.divergence(u0, v0)).max()
    after = np.abs(winds.divergence(u, v)).max()
    assert after < 0.05 * before


def test_already_divergence_free_is_unchanged():
    """A solenoidal field (u = -d psi/dy, v = d psi/dx) should pass through ~unchanged."""
    n = 64
    y = np.arange(n)[:, None]
    x = np.arange(n)[None, :]
    psi = np.sin(2 * np.pi * x / n) * np.sin(2 * np.pi * y / n)
    u0 = -(np.roll(psi, -1, 0) - np.roll(psi, 1, 0)) / 2.0
    v0 = (np.roll(psi, -1, 1) - np.roll(psi, 1, 1)) / 2.0
    u, v = winds.mass_consistent(u0, v0)
    assert np.allclose(u, u0, atol=1e-6) and np.allclose(v, v0, atol=1e-6)
