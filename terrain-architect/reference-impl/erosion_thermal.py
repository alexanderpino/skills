"""Thermal / talus erosion (05-erosion-thermal-aeolian.md). Musgrave et al. 1989.

Relax slopes toward the material repose angle by moving material to lower neighbours.
Double-buffered (delta computed from the old field) so the result is order-independent
and deterministic. Mass is conserved exactly (all flux stays on-grid). The per-neighbour
distance correction (dmax = repose_slope * dist * cellsize) is what keeps a cone radial;
`distance_correct=False` reproduces the classic plus-shaped artefact for comparison.
"""
import numpy as np

_SQRT2 = np.sqrt(2.0)
_NB = (
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, _SQRT2), (-1, 1, _SQRT2), (1, -1, _SQRT2), (1, 1, _SQRT2),
)


def max_slope(h, cellsize=1.0):
    """Largest downhill 8-neighbour slope anywhere (distance-corrected)."""
    n, m = h.shape
    best = 0.0
    for di, dj, dist in _NB:
        sl = slice(max(0, -di), n - max(0, di)), slice(max(0, -dj), m - max(0, dj))
        nb = slice(max(0, di), n - max(0, -di)), slice(max(0, dj), m - max(0, -dj))
        d = (h[sl] - h[nb]) / (dist * cellsize)
        best = max(best, float(d.max()))
    return best


def thermal_erosion(h, repose_slope, iters, cellsize=1.0, factor=0.25,
                    distance_correct=True):
    """Return h after `iters` talus-relaxation steps. repose_slope = tan(repose angle)."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    for _ in range(int(iters)):
        delta = np.zeros_like(h)
        for i in range(n):
            for j in range(m):
                per, total = [], 0.0
                for di, dj, dist in _NB:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < m:
                        dmax = repose_slope * (dist if distance_correct else 1.0) * cellsize
                        excess = (h[i, j] - h[ni, nj]) - dmax
                        if excess > 0.0:
                            per.append((ni, nj, excess))
                            total += excess
                if total > 0.0:
                    moved = factor * total
                    delta[i, j] -= moved
                    for ni, nj, e in per:
                        delta[ni, nj] += moved * (e / total)
        h += delta
    return h
