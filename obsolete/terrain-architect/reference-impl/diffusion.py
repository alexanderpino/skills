"""Hillslope diffusion / soil creep (04, 05): dh/dt = D * laplacian(h). Culling 1960.

Explicit scheme with periodic boundaries (np.roll). Stable when D*dt/cellsize^2 <= 0.25.
A single Fourier mode decays by an exact factor per step, which the test asserts.
"""
import numpy as np


def hillslope_diffuse(h, D, dt, iters=1, cellsize=1.0):
    """Return h after `iters` explicit diffusion steps. Mass (sum) is conserved
    exactly under the periodic 5-point stencil."""
    h = np.asarray(h, dtype=np.float64).copy()
    c = D * dt / (cellsize * cellsize)
    for _ in range(int(iters)):
        lap = (
            -4.0 * h
            + np.roll(h, 1, 0) + np.roll(h, -1, 0)
            + np.roll(h, 1, 1) + np.roll(h, -1, 1)
        )
        h = h + c * lap
    return h


def stable_dt(D, cellsize=1.0, safety=0.9):
    """Largest stable explicit timestep: dt <= 0.25 * cellsize^2 / D (2-D)."""
    return safety * 0.25 * cellsize * cellsize / D
