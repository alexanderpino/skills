import numpy as np
import winds


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
