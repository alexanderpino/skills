import numpy as np
import isostasy as I


def test_airy_root():
    # (rho_m - rho_c) = 500 -> root = 2800/500 * h
    assert abs(I.airy_root(1.0) - 2800.0 / 500.0) < 1e-12


def test_erosional_rebound_ratio():
    assert abs(I.erosional_rebound(100.0) - (2800.0 / 3300.0) * 100.0) < 1e-9


def test_flexure_single_mode_exact():
    """A pure resolved Fourier-mode load -> the transfer function applies exactly.
    This is the decisive exactness test for the FFT solver."""
    n, cs = 128, 1.0
    D, drho = 1e22, 600.0
    mode = 3
    kx = 2.0 * np.pi * mode / (n * cs)
    x = np.arange(n) * cs
    load = np.cos(kx * x)[None, :] * np.ones((n, 1))     # Pa, varies along x
    w = I.flexure_fft(load, D, drho, cellsize=cs)
    expected = (np.cos(kx * x) / (D * kx ** 4 + drho * I.G))[None, :] * np.ones((n, 1))
    assert np.allclose(w, expected, rtol=1e-8, atol=1e-14)


def test_flexure_airy_limit():
    """A uniform load compensates uniformly: w = q/(drho*g) (the k=0 mode)."""
    load = np.full((64, 64), 5e6)
    D, drho = 1e22, 600.0
    w = I.flexure_fft(load, D, drho)
    assert np.allclose(w, 5e6 / (drho * I.G), rtol=1e-9)


def test_flexure_matches_analytic_line_load():
    """A 1-cell-wide line load in the 2-D FFT solver reproduces the closed-form
    kernel away from the immediate load cell (where the discrete delta differs)."""
    n, cs = 1024, 1.0
    # choose D so the flexural length alpha ~ 30 cells (<< domain -> negligible FFT wrap)
    drho = 600.0
    D = 1.2e9
    q0 = 1e6                                    # Pa in the load column
    V0 = q0 * cs                                # N/m line-load intensity
    load = np.zeros((8, n))
    load[:, n // 2] = q0
    w = I.flexure_fft(load, D, drho, cellsize=cs)[0]
    x = (np.arange(n) - n // 2) * cs
    analytic = I.flexure_line_load_analytic(x, V0, D, drho)
    alpha = I.flexural_parameter(D, drho)
    assert 20.0 < alpha < 45.0                  # sanity: alpha well inside the domain
    mask = (np.abs(x) > 3 * cs) & (np.abs(x) < 5 * alpha)   # skip the delta core & FFT wrap
    rel = np.max(np.abs(w[mask] - analytic[mask])) / np.max(np.abs(analytic[mask]))
    assert rel < 0.02, f"line-load flexure deviates from analytic kernel: {rel:.3f}"
