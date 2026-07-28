"""Tests for aeolian transport and abrasion — what the wind does to terrain (aeolian.py / 05, 16).

Two groups:

- **Transport** (Bagnold 1941): the threshold and the cubic flux law are ARITHMETIC, so they get
  exact oracles; the Exner coupling is then held to the invariant that makes a terrain-aware wind
  field worth having at all — a windward face is stripped and its lee fills, and that response
  vanishes identically under a spatially uniform wind.
- **Abrasion / yardangs** (Ward & Greeley 1984): F-tier "look" held to invariants — the abraded
  ridges elongate PARALLEL to the wind (streamlined, the yardang/drumlin signature), abrasion only
  removes material and only within the soft mask, and — the Ward & Greeley detail — the low ground
  is cut fastest (bottom-weighted saltation → undercut, streamlined ridges), not the crests. Not a
  certified erosion-rate oracle.
"""
import numpy as np

import aeolian
import noise
import winds


# --------------------------------------------------------------------------- #
# Transport: speed -> shear velocity -> threshold-gated cubic flux -> bed change.

def _bump(n=160, sigma=12.0, height=40.0):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return height * np.exp(-(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (2 * sigma ** 2)))


def test_threshold_matches_bagnolds_published_value():
    """u*_t ~ 0.2 m/s for 250 um quartz sand in Earth air — the number the chapter quotes."""
    assert 0.19 < aeolian.threshold_shear() < 0.25


def test_flux_is_cubic_in_shear_velocity():
    """Bagnold's u*^3: doubling the wind moves EIGHT times the sand. This is why a linear
    wind-strength slider feels wrong, and why averaging a wind field destroys the result."""
    assert np.isclose(aeolian.saltation_flux(1.0), 8.0 * aeolian.saltation_flux(0.5))


def test_transport_is_threshold_gated():
    """Below the threshold friction velocity NOTHING moves — the flux is exactly zero, not merely
    small. A field uniformly just below threshold transports no sand at all."""
    u_t = aeolian.threshold_shear()
    assert aeolian.saltation_flux(0.99 * u_t) == 0.0
    assert aeolian.saltation_flux(1.01 * u_t) > 0.0


def test_gravity_and_air_density_rescale_the_threshold():
    """Kok et al. 2012 (`SKILL.md`, off-Earth): the same sand needs a different wind on Mars — thin
    air (low rho_a) RAISES the threshold, low gravity LOWERS it. Constants tuned for Earth are wrong
    elsewhere, and the formula must actually carry that."""
    earth = aeolian.threshold_shear()
    assert aeolian.threshold_shear(rho_a=0.020) > earth        # Mars air: much harder to start
    assert aeolian.threshold_shear(g=3.71) < earth             # Mars gravity: easier to lift


def test_uniform_wind_moves_no_sand_anywhere():
    """The honest statement of why the wind FIELD is not optional: under a spatially constant wind
    the flux is constant, its divergence is zero, and the bed never changes — no matter how hard it
    blows or how long you run it."""
    bed = np.zeros((64, 64))
    assert np.allclose(aeolian.exner_step(bed, (12.0, 0.0), dt=1e5, cellsize=10.0), bed, atol=1e-12)


def test_windward_face_is_stripped_and_the_lee_fills():
    """The coupling that makes a terrain-aware field pay off: the flow accelerates up the windward
    slope so the flux DIVERGES and the face deflates; it decelerates past the crest so the flux
    CONVERGES and sand is deposited in the lee."""
    n, ds = 160, 10.0
    c = n // 2
    h = _bump(n)
    u, v = winds.wind_field(h, (1.0, 0.0), 10.0, cellsize=ds, fetch=30, reach=20)
    bed, _sand = aeolian.exner_step(h, (u, v), sand=np.full((n, n), 5.0), dt=2e5, cellsize=ds)
    dh = bed - h
    assert dh[c, c - 12] < 0.0                      # windward flank: deflated
    assert dh[c, c + 16] > 0.0                      # lee: deposited


def test_exner_conserves_sand():
    """Transport MOVES sand; it does not create or destroy it. On the periodic domain the bed
    change must sum to zero — the aeolian mass budget (`SKILL.md`)."""
    n, ds = 96, 10.0
    h = _bump(n, sigma=10.0, height=30.0)
    u, v = winds.wind_field(h, (1.0, 0.2), 10.0, cellsize=ds, fetch=24, reach=16)
    dh = aeolian.exner_step(h, (u, v), dt=1e5, cellsize=ds) - h
    assert abs(dh.sum()) < 1e-9 * max(1.0, np.abs(dh).sum())


def test_deflation_cannot_excavate_below_the_available_sand():
    """Wind strips the sand layer, not the bedrock under it (that is abrasion, far slower). With no
    sand present, no cell can be deflated at all."""
    n, ds = 96, 10.0
    h = _bump(n, sigma=10.0, height=30.0)
    u, v = winds.wind_field(h, (1.0, 0.0), 25.0, cellsize=ds, fetch=24, reach=16)
    bed, sand = aeolian.exner_step(h, (u, v), sand=np.zeros((n, n)), dt=1e7, cellsize=ds)
    assert np.all(sand >= -1e-12)                   # never negative
    assert np.all(bed >= h - 1e-12)                 # nothing was cut out of the bedrock


def test_saturation_length_shifts_deposition_downwind():
    """Sauermann et al. 2001: the saltation cloud takes a length L_sat to reach capacity, so the flux
    lags the wind and the deposition maximum sits DOWNWIND of where it would otherwise be — the
    aeolian twin of the orographic fallout lag (`13`), and the reason dunes have a minimum size."""
    n, ds = 160, 10.0
    h = _bump(n)
    u, v = winds.wind_field(h, (1.0, 0.0), 10.0, cellsize=ds, fetch=30, reach=20)
    row = n // 2
    prompt = aeolian.exner_step(h, (u, v), dt=2e5, cellsize=ds, sat_length=0.0) - h
    lagged = aeolian.exner_step(h, (u, v), dt=2e5, cellsize=ds, sat_length=120.0) - h
    assert int(np.argmax(lagged[row])) > int(np.argmax(prompt[row]))


def test_availability_gate_stops_transport():
    """Vegetation cover, a crust or moisture (`13`) hold the sand down: gating availability to zero
    must stop the bed changing — the same switch that decides a stable nebkha field vs mobile
    barchans."""
    n, ds = 96, 10.0
    h = _bump(n, sigma=10.0, height=30.0)
    u, v = winds.wind_field(h, (1.0, 0.0), 10.0, cellsize=ds, fetch=24, reach=16)
    assert np.allclose(aeolian.exner_step(h, (u, v), dt=1e5, cellsize=ds, availability=0.0), h)


# --------------------------------------------------------------------------- #
# Abrasion / yardangs.


def _playa(n=120, relief=12.0, wind=(1.0, 0.25), seed=3):
    """A soft substrate with a faint wind-aligned grain, ready to be abraded into yardangs."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    u, v = wind; mag = np.hypot(u, v); u, v = u / mag, v / mag
    along, cross = xx * u + yy * v, -xx * v + yy * u
    h = relief * noise.fbm(along * 0.018, cross * 0.11, seed, octaves=4)
    return h - h.min()


def _acf(z, di, dj):
    a = z - z.mean()
    return float((a * np.roll(np.roll(a, di, 0), dj, 1)).mean() / (a * a).mean())


def test_ridges_elongate_parallel_to_the_wind():
    """Streamlined yardang ridges: the surface stays correlated far ALONG the wind but decorrelates
    quickly ACROSS it (the drumlin-like signature). Isotropic erosion would give equal correlation."""
    h = aeolian.yardang(_playa(), wind=(1.0, 0.25), soft_mask=1.0, iters=10, seed=3)
    assert _acf(h, 1, 5) > 3.0 * _acf(h, 5, -1)       # along-wind autocorr >> cross-wind


def test_abrasion_is_carve_only():
    playa = _playa()
    h = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=10, seed=3)
    assert np.all(h <= playa + 1e-9)                  # wind removes, never builds


def test_only_soft_ground_is_abraded():
    """A hard mask (soft=0) leaves the rock untouched — wind abrasion needs a cohesive-but-soft
    substrate (playa clay, loess, tuff)."""
    playa = _playa()
    soft = np.ones_like(playa); soft[:, playa.shape[1] // 2:] = 0.0
    h = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=soft, iters=10, seed=3)
    assert np.allclose(h[:, playa.shape[1] // 2 + 3:], playa[:, playa.shape[1] // 2 + 3:])


def test_low_ground_is_cut_fastest():
    """Bottom-weighted saltation (Ward & Greeley: sand only saltates ~1 m up): the troughs / low
    ground are abraded far more than the ridge crests — which is what undercuts and streamlines the
    ridges rather than lowering everything uniformly."""
    playa = _playa()
    h = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=10, saltation_h=3.0, seed=3)
    ero = playa - h
    med = np.median(playa)
    assert ero[playa < med].mean() > 2.0 * ero[playa > med].mean()


def test_yardang_is_deterministic():
    playa = _playa()
    a = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=6, seed=1)
    b = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=6, seed=1)
    assert np.array_equal(a, b)


def test_abrasion_rate_follows_the_local_wind_speed():
    """Given a wind FIELD rather than a constant vector, the carve responds to local SPEED (cubed —
    the Bagnold scaling): the half of the map under the strong wind is abraded markedly more than
    the sheltered half. Under a constant vector both halves erode identically, which is exactly the
    behaviour a terrain-aware field is meant to replace."""
    playa = _playa()
    n = playa.shape[0]
    u = np.full((n, n), 1.0)
    u[:, n // 2:] = 0.4                              # sheltered downwind half
    v = np.zeros((n, n))
    h = aeolian.yardang(playa, wind=(u, v), soft_mask=1.0, iters=10, seed=3)
    ero = playa - h
    assert ero[:, :n // 2].mean() > 3.0 * ero[:, n // 2:].mean()


def test_a_constant_field_reproduces_the_constant_vector():
    """Passing (u, v) as full fields of a constant must give bit-identical output to passing the
    scalar pair — so swapping a regional constant for `winds.wind_field` is a drop-in change."""
    playa = _playa()
    n = playa.shape[0]
    scalar = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=6, seed=1)
    fields = aeolian.yardang(playa, wind=(np.full((n, n), 1.0), np.full((n, n), 0.25)),
                             soft_mask=1.0, iters=6, seed=1)
    assert np.array_equal(scalar, fields)
