"""Mass-consistent wind adjustment (13-climate-ecosystem.md). Sherman 1978, MATHEW.

Project a terrain-adjusted wind field onto a divergence-free field by solving a Poisson
equation for the scalar potential lambda (the Helmholtz-Hodge projection): remove the
curl-free (divergent) part so streamlines wrap terrain instead of piling into it.

Solved spectrally (periodic BCs) with the SAME wavenumber grid as the isostasy flexure
solve. Using spectral derivatives throughout makes the projection exact: the corrected
field's (spectral) divergence is zero to machine precision — on ANY grid, because the
odd-order (first-derivative) i*k operator ZEROES the Nyquist mode. On an even-length axis the
Nyquist frequency is its own conjugate, so i*k*(Nyquist) has an imaginary part that np.real
silently drops; leaving it in place would let a real field carry a spurious residual divergence
at the grid scale. Zeroing it (the standard spectral-derivative rule) and using the SAME zeroed
wavenumbers for the Laplacian keeps the projection identity div_new = div - k^2*lambda exact.
"""
import numpy as np


def _wavenumbers(shape, cellsize, zero_nyquist=False):
    """2-D angular wavenumber grids. `zero_nyquist` drops the Nyquist mode on each even-length
    axis — required for the ODD-order i*k derivative (div/grad); leave it False for the EVEN-order
    Laplacian k^2 (where the Nyquist term is real and well-defined)."""
    n, m = shape
    ky = 2.0 * np.pi * np.fft.fftfreq(n, d=cellsize)
    kx = 2.0 * np.pi * np.fft.fftfreq(m, d=cellsize)
    if zero_nyquist:
        if n % 2 == 0:
            ky[n // 2] = 0.0
        if m % 2 == 0:
            kx[m // 2] = 0.0
    KX, KY = np.meshgrid(kx, ky)
    return KX, KY


def divergence(u, v, cellsize=1.0):
    """Central-difference divergence (periodic), for user-facing diagnostics."""
    du = (np.roll(u, -1, 1) - np.roll(u, 1, 1)) / (2.0 * cellsize)
    dv = (np.roll(v, -1, 0) - np.roll(v, 1, 0)) / (2.0 * cellsize)
    return du + dv


def divergence_spectral(u, v, cellsize=1.0):
    KX, KY = _wavenumbers(u.shape, cellsize, zero_nyquist=True)   # i*k derivative -> zero Nyquist
    d_hat = 1j * KX * np.fft.fft2(u) + 1j * KY * np.fft.fft2(v)
    return np.real(np.fft.ifft2(d_hat))


def mass_consistent(u0, v0, cellsize=1.0):
    """Return (u, v): the divergence-free field closest to (u0, v0). Solves
    nabla^2 lambda = div(u0) spectrally, then u = u0 - grad(lambda)."""
    u0 = np.asarray(u0, dtype=np.float64)
    v0 = np.asarray(v0, dtype=np.float64)
    # ONE zeroed-Nyquist i*k operator used for divergence, the Laplacian, AND the gradient update,
    # so the projection cancels exactly (div_new = div_hat + k2*lam_hat = 0) on any grid.
    KX, KY = _wavenumbers(u0.shape, cellsize, zero_nyquist=True)
    U, V = np.fft.fft2(u0), np.fft.fft2(v0)
    div_hat = 1j * KX * U + 1j * KY * V           # spectral divergence
    k2 = KX ** 2 + KY ** 2                          # SAME (zeroed) wavenumbers -> consistent Laplacian
    zero = k2 == 0.0                                # DC and every zeroed-Nyquist mode (div_hat==0 there too)
    k2 = np.where(zero, 1.0, k2)                    # avoid /0; those modes are left unprojected next
    lam_hat = -div_hat / k2                         # nabla^2 lambda = div  ->  -k^2 lam_hat = div_hat
    lam_hat[zero] = 0.0                             # gauge (DC) + unforced Nyquist modes -> no correction
    U -= 1j * KX * lam_hat                          # u = u0 - d(lambda)/dx
    V -= 1j * KY * lam_hat
    return np.real(np.fft.ifft2(U)), np.real(np.fft.ifft2(V))
