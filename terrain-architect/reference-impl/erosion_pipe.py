"""Virtual-pipe shallow-water flow (04-erosion-hydraulic.md). Mei, Decaudin & Hu 2007.

This module implements the WATER solver — the canonical hard part of the pipe model and
where its documented failure modes live: without the step-3 outflow scaling, a cell can
drain more water than it holds, depth goes negative, the velocity term divides by a
negative and the sim NaNs within ~20 steps. The scaling is included and verified (depth
stays >= 0, field stays finite). The 8-pipe stencil (per-pipe length) is verified to be
more radially symmetric than the 4-pipe stencil on a cone.

The sediment/erosion coupling (transport capacity + semi-Lagrangian advection) layers on
top of this solver; for a production erosion pipeline use a GPU implementation (the model
was designed for it) — the reference here pins down the water routing that everything else
depends on. Boundaries are periodic (np.roll), which conserves total water exactly.
"""
import numpy as np

_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
_LEN = [1.0, 1.0, 1.0, 1.0] + [np.sqrt(2.0)] * 4
_OPP = [1, 0, 3, 2, 7, 6, 5, 4]           # index of the opposite direction


def _shift(a, di, dj):
    return np.roll(np.roll(a, di, axis=0), dj, axis=1)


def pipe_water(b, d, iters, *, rain=0.0, evap=0.0, dt=0.02, g=9.81, cellsize=1.0,
               pipes=8, flux_const=1.0):
    """Advance water depth `d` over terrain `b` for `iters` steps. Returns new depth."""
    b = np.asarray(b, dtype=np.float64)
    d = np.asarray(d, dtype=np.float64).copy()
    ndir = 8 if pipes == 8 else 4
    f = [np.zeros_like(d) for _ in range(ndir)]
    area = cellsize * cellsize
    for _ in range(int(iters)):
        if rain:
            d = d + rain * dt
        head = b + d
        for k in range(ndir):
            di, dj = _DIRS[k]
            dh = head - _shift(head, -di, -dj)
            f[k] = np.maximum(0.0, f[k] + dt * flux_const * g * dh / (_LEN[k] * cellsize))
        out = sum(f)
        # step 3 — CRITICAL: never drain more water than the cell holds
        scale = np.where(out > 0.0, np.minimum(1.0, d * area / (out * dt + 1e-30)), 1.0)
        for k in range(ndir):
            f[k] = f[k] * scale
        inflow = np.zeros_like(d)
        for k in range(ndir):
            di, dj = _DIRS[k]
            inflow += _shift(f[_OPP[k]], -di, -dj)
        d = d + dt * (inflow - sum(f)) / area
        if evap:
            d = d * (1.0 - evap * dt)
        d = np.maximum(d, 0.0)                 # clamp fp dust; scaling makes this a no-op
    return d
