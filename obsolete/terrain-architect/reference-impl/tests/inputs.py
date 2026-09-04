"""Canonical synthetic test inputs from 09-verification.md.

Each is a terrain whose correct behaviour is known in advance, chosen because it
breaks a specific class of node. Returns a float64 heightfield in metres.
"""
import numpy as np


def flat(n=64, value=0.0):
    """Flat plane. Catches div-by-zero in slope/TWI, erosion-from-nothing."""
    return np.full((n, n), float(value), dtype=np.float64)


def constant_slope(n=64, gradient=0.1):
    """Plane tilting down toward increasing row index (row 0 highest, row n-1 = 0).

    Catches flow routing that doesn't route and D8 diagonal bias.
    """
    rows = np.arange(n, dtype=np.float64)[:, None]
    return ((n - 1 - rows) * gradient) * np.ones((1, n))


def cone(n=65, height=10.0, radius=None):
    """Radially symmetric cone (odd n centres it). Output of a radially symmetric
    process must stay radially symmetric -> catches the thermal per-neighbour bug
    and the pipe 4-pipe anisotropy (a plus/diamond shape)."""
    c = (n - 1) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    r = np.hypot(xx - c, yy - c)
    if radius is None:
        radius = c
    return np.clip(1.0 - r / radius, 0.0, None) * height


def inverted_cone(n=65, depth=10.0):
    """A single central pit; rim at 0. Depression handling must resolve it."""
    return -cone(n, depth)


def two_basins(n=48):
    """Two pits of different depth sharing a sill, inside a high rim, with one low
    outlet on the top edge. The classic case naive filling gets wrong: flow must
    exit via the spill/outlet, and each basin fills to its own spill level."""
    h = np.full((n, n), 10.0, dtype=np.float64)
    h[8:20, 8:20] = 3.0          # basin A (shallow)
    h[8:20, 28:40] = 1.0         # basin B (deep)
    h[8:20, 20:28] = 6.0         # sill between the two basins
    h[0, 33] = 0.0               # the one outlet, on the top edge near basin B
    return h


def step(n=64, lo=0.0, hi=5.0):
    """A single edge. Edge-preserving filters must keep it; Gaussian must not."""
    h = np.full((n, n), float(lo), dtype=np.float64)
    h[:, n // 2:] = hi
    return h


def plateau(n=64, base=0.0, top=5.0):
    """A flat-topped block. Flat-resolution / epsilon-fill test."""
    h = np.full((n, n), float(base), dtype=np.float64)
    h[16:48, 16:48] = top
    return h


def spike(n=64, base=0.0, value=100.0):
    """One-pixel spike. Median/despike, erosion stability, capacity singularities."""
    h = np.full((n, n), float(base), dtype=np.float64)
    h[n // 2, n // 2] = value
    return h


def sinusoid(n=64, amp=1.0, k=1):
    """A single spatial Fourier mode along x, for the diffusion analytic-decay test
    and the flexure single-mode exactness test."""
    x = np.linspace(0.0, 2.0 * np.pi * k, n, endpoint=False)
    return (amp * np.sin(x))[None, :] * np.ones((n, 1))
