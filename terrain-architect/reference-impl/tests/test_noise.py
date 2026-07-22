"""Oracles for the noise families (01-noise.md). Gradient noise is 0 on the lattice; fBm of
one octave is the base noise; curl noise is divergence-free; the fractal sums stay finite and
bounded. All deterministic from the seed, all pure functions of world coordinates (seam-free).
"""
import numpy as np
import noise as N


def _grid(n=48, step=0.37, origin=0.0):
    x = origin + np.arange(n) * step
    return np.meshgrid(x, x)


def test_perlin_is_zero_on_the_lattice():
    """Perlin's defining property: value is exactly 0 at every integer lattice point."""
    xi, yi = np.meshgrid(np.arange(12), np.arange(12))
    assert np.allclose(N.perlin(xi, yi, seed=3), 0.0, atol=1e-12)


def test_perlin_range_and_zero_mean():
    """Gradient noise is roughly [-0.7, 0.7] and ~zero-mean — never assume [-1,1] is filled."""
    xx, yy = _grid(96, 0.13)
    p = N.perlin(xx, yy, seed=1)
    assert p.min() > -0.95 and p.max() < 0.95
    assert abs(p.mean()) < 0.05


def test_noise_is_a_pure_world_space_function():
    """Same world coordinates -> same value, independent of the window (the seam-free call).
    A sub-window matches the corresponding slice of a larger evaluation."""
    xx, yy = _grid(40, 0.25)
    full = N.perlin(xx, yy, seed=7)
    sub = N.perlin(xx[5:15, 5:15], yy[5:15, 5:15], seed=7)
    assert np.allclose(sub, full[5:15, 5:15])


def test_value_noise_in_unit_range():
    xx, yy = _grid(64, 0.21)
    v = N.value(xx, yy, seed=2)
    assert v.min() >= 0.0 and v.max() <= 1.0


def test_worley_orderings():
    xx, yy = _grid(64, 0.2)
    f1 = N.worley(xx, yy, seed=1, kind="f1")
    f2f1 = N.worley(xx, yy, seed=1, kind="f2f1")
    assert np.all(f1 >= 0.0)
    assert np.all(f2f1 >= -1e-9)                       # F2 >= F1
    assert np.allclose(N.worley(xx, yy, seed=1, kind="inv_f1"), 1.0 - f1)


def test_fbm_single_octave_is_the_base_noise():
    """The normalisation oracle: one octave of fBm is exactly the base noise."""
    xx, yy = _grid(48, 0.3)
    assert np.allclose(N.fbm(xx, yy, seed=4, octaves=1), N.perlin(xx, yy, seed=4))


def test_fbm_bounded_and_deterministic():
    xx, yy = _grid(64, 0.17)
    a = N.fbm(xx, yy, seed=5, octaves=6)
    b = N.fbm(xx, yy, seed=5, octaves=6)
    assert np.array_equal(a, b)
    assert np.abs(a).max() < 0.8                       # bounded by the perlin range
    assert not np.allclose(a, N.fbm(xx, yy, seed=6, octaves=6))   # seed shuffles, not shifts


def test_ridged_is_nonnegative_and_finite():
    xx, yy = _grid(64, 0.15)
    r = N.ridged_mf(xx, yy, seed=1)
    assert np.all(np.isfinite(r)) and r.min() >= -1e-9


def test_hybrid_is_finite_thanks_to_the_clamp():
    """The min(weight,1) clamp keeps the multifractal product from diverging to spikes."""
    xx, yy = _grid(96, 0.11)
    h = N.hybrid_mf(xx, yy, seed=2)
    assert np.all(np.isfinite(h))
    assert h.max() < 50.0                              # no runaway spikes


def test_domain_warp_actually_warps():
    xx, yy = _grid(64, 0.2)
    h, qx, qy = N.domain_warp(xx, yy, seed=3, warp=4.0, octaves=5)
    plain = N.fbm(xx, yy, seed=3, octaves=5)
    assert np.all(np.isfinite(h)) and np.all(np.isfinite(qx))
    assert not np.allclose(h, plain)                   # the warp displaced the field


def test_curl_is_divergence_free():
    """The decisive curl oracle: div(curl psi) = 0. With central differences at the grid
    spacing, the mixed partials commute, so divergence is machine-zero."""
    n, step = 64, 1.0
    xx, yy = _grid(n, step)
    vx, vy = N.curl(xx, yy, seed=1, eps=step, octaves=5)
    # discrete divergence at the same spacing
    dvx_dx = (vx[:, 2:] - vx[:, :-2]) / (2 * step)
    dvy_dy = (vy[2:, :] - vy[:-2, :]) / (2 * step)
    div = dvx_dx[1:-1, :] + dvy_dy[:, 1:-1]
    assert np.abs(div).max() < 1e-9
