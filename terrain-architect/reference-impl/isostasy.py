"""Isostasy & flexure (02-macro-tectonics.md).

The FFT flexure solver is verified two ways: an exact single-Fourier-mode check
(the transfer function applied to one resolved mode is exact), the Airy long-
wavelength limit, and a comparison of a line load against the closed-form kernel.
"""
import numpy as np

G = 9.81


def airy_root(h, rho_c=2800.0, rho_m=3300.0):
    """Airy local compensation: root depth r = rho_c*h / (rho_m - rho_c)."""
    return rho_c * np.asarray(h, dtype=np.float64) / (rho_m - rho_c)


def flexural_rigidity(E, Te, nu=0.25):
    """D = E*Te^3 / [12(1 - nu^2)]."""
    return E * Te ** 3 / (12.0 * (1.0 - nu ** 2))


def flexural_parameter(D, drho, g=G):
    """alpha = [4D / (drho*g)]^(1/4) — the flexural response length scale."""
    return (4.0 * D / (drho * g)) ** 0.25


def flexure_fft(load, D, drho, g=G, cellsize=1.0):
    """Thin-elastic-plate deflection w under a 2-D load (Pa), solved in Fourier space:
        D*del4(w) + drho*g*w = q     ->     W(k) = Q(k) / (D*|k|^4 + drho*g)
    Positive w = downward deflection. drho = (rho_mantle - rho_infill)."""
    load = np.asarray(load, dtype=np.float64)
    n, m = load.shape
    ky = 2.0 * np.pi * np.fft.fftfreq(n, d=cellsize)
    kx = 2.0 * np.pi * np.fft.fftfreq(m, d=cellsize)
    KX, KY = np.meshgrid(kx, ky)
    k2 = KX ** 2 + KY ** 2
    Q = np.fft.fft2(load)
    W = Q / (D * k2 ** 2 + drho * g)
    return np.real(np.fft.ifft2(W))


def flexure_line_load_analytic(x, V0, D, drho, g=G):
    """Closed-form deflection under an infinite line load V0 (N/m), Turcotte &
    Schubert / Watts: w(x) = (V0 alpha^3 / 8D) exp(-|x|/alpha)(cos|x|/alpha + sin|x|/alpha)."""
    alpha = flexural_parameter(D, drho, g)
    ax = np.abs(np.asarray(x, dtype=np.float64)) / alpha
    return (V0 * alpha ** 3 / (8.0 * D)) * np.exp(-ax) * (np.cos(ax) + np.sin(ax))


def erosional_rebound(eroded_thickness, rho_c=2800.0, rho_m=3300.0):
    """Local (Airy) isostatic rebound from unloading: (rho_c/rho_m) * eroded thickness.
    Molnar & England 1990 — why peaks rise as valleys incise."""
    return (rho_c / rho_m) * np.asarray(eroded_thickness, dtype=np.float64)
