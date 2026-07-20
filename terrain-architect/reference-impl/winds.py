"""Mass-consistent wind adjustment (13-climate-ecosystem.md). Sherman 1978, MATHEW.

Project a terrain-adjusted wind field onto a divergence-free field by solving a Poisson
equation for the scalar potential lambda (the Helmholtz-Hodge projection): remove the
curl-free (divergent) part so streamlines wrap terrain instead of piling into it.

Solved spectrally (periodic BCs) with the SAME wavenumber grid as the isostasy flexure
solve. Using spectral derivatives throughout makes the projection exact: the corrected
field's (spectral) divergence is zero to machine precision.
"""
import numpy as np


def _wavenumbers(shape, cellsize):
    n, m = shape
    ky = 2.0 * np.pi * np.fft.fftfreq(n, d=cellsize)
    kx = 2.0 * np.pi * np.fft.fftfreq(m, d=cellsize)
    KX, KY = np.meshgrid(kx, ky)
    return KX, KY


def divergence(u, v, cellsize=1.0):
    """Central-difference divergence (periodic), for user-facing diagnostics."""
    du = (np.roll(u, -1, 1) - np.roll(u, 1, 1)) / (2.0 * cellsize)
    dv = (np.roll(v, -1, 0) - np.roll(v, 1, 0)) / (2.0 * cellsize)
    return du + dv


def divergence_spectral(u, v, cellsize=1.0):
    KX, KY = _wavenumbers(u.shape, cellsize)
    d_hat = 1j * KX * np.fft.fft2(u) + 1j * KY * np.fft.fft2(v)
    return np.real(np.fft.ifft2(d_hat))


def mass_consistent(u0, v0, cellsize=1.0):
    """Return (u, v): the divergence-free field closest to (u0, v0). Solves
    nabla^2 lambda = div(u0) spectrally, then u = u0 - grad(lambda)."""
    u0 = np.asarray(u0, dtype=np.float64)
    v0 = np.asarray(v0, dtype=np.float64)
    KX, KY = _wavenumbers(u0.shape, cellsize)
    U, V = np.fft.fft2(u0), np.fft.fft2(v0)
    div_hat = 1j * KX * U + 1j * KY * V           # spectral divergence
    k2 = KX ** 2 + KY ** 2
    k2[0, 0] = 1.0                                  # avoid /0; the DC mode is set to 0 next
    lam_hat = -div_hat / k2                         # nabla^2 lambda = div  ->  -k^2 lam_hat = div_hat
    lam_hat[0, 0] = 0.0                             # gauge: zero-mean potential
    U -= 1j * KX * lam_hat                          # u = u0 - d(lambda)/dx
    V -= 1j * KY * lam_hat
    return np.real(np.fft.ifft2(U)), np.real(np.fft.ifft2(V))
