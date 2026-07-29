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


def _dir_slices(di, dj, n, m):
    """Aligned (source, neighbour) slice pair for an 8-neighbour offset: element a of `src` is the
    cell at (i, j) and element a of `nbr` is its neighbour at (i+di, j+dj). Cells whose neighbour
    would fall off the grid are simply outside both slices, which is the bounds check."""
    src = (slice(max(0, -di), n - max(0, di)), slice(max(0, -dj), m - max(0, dj)))
    nbr = (slice(max(0, di), n - max(0, -di)), slice(max(0, dj), m - max(0, -dj)))
    return src, nbr


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
    """Return h after `iters` talus-relaxation steps. repose_slope = tan(repose angle).

    The amount a cell sheds is sized from its **steepest** over-repose pair (`factor * maxExcess`),
    then split among all over-repose lower neighbours in proportion to their excess. This is the
    Musgrave 1989 steepest-descent form, and it is what makes the step *unconditionally* stable:
    sizing from the SUM of all steep neighbours (a naive `factor * total`) lets a spike with many
    lower neighbours shed several times its own relief in one step and invert — the field then
    diverges (mass stays conserved, so the explosion hides from a mass test) precisely on the rough,
    over-steepened terrain thermal is meant to relax. Sizing from the single steepest pair caps the
    drop at `maxExcess`, so the cell can never fall below its lowest lower-neighbour. Double-buffered
    (delta from the old field) -> order-independent and deterministic; mass conserved exactly.

    Written in the **gather form**: rather than each cell scattering into its neighbours one at a
    time, every direction's excess is computed as a whole-array shift, so each cell is solved
    independently and the whole step vectorises (and ports directly to a GPU fragment shader — 15).
    `_thermal_erosion_loop` below is the literal transcription of the algorithm and the two are
    asserted equal in `tests/test_thermal.py`; keep them in step if you change either."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    dirs = [(_dir_slices(di, dj, n, m),
             repose_slope * (dist if distance_correct else 1.0) * cellsize)
            for di, dj, dist in _NB]
    excess = np.zeros((len(_NB), n, m))
    for _ in range(int(iters)):
        excess[:] = 0.0
        for k, ((src, nbr), dmax) in enumerate(dirs):        # over-repose drop per direction
            np.maximum((h[src] - h[nbr]) - dmax, 0.0, out=excess[k][src])
        total = excess.sum(axis=0)
        moving = total > 0.0
        moved = np.where(moving, factor * excess.max(axis=0), 0.0)   # steepest pair, NOT the sum
        share = np.divide(moved, total, out=np.zeros_like(moved), where=moving)
        delta = -moved
        for k, ((src, nbr), _) in enumerate(dirs):           # split in proportion to each excess
            delta[nbr] += excess[k][src] * share[src]
        h += delta
    return h


def _thermal_erosion_loop(h, repose_slope, iters, cellsize=1.0, factor=0.25,
                          distance_correct=True):
    """Literal, cell-by-cell transcription of `thermal_erosion` — the readable reference the
    vectorised version is checked against. Too slow for real grids; use `thermal_erosion`."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    for _ in range(int(iters)):
        delta = np.zeros_like(h)
        for i in range(n):
            for j in range(m):
                per, total, max_excess = [], 0.0, 0.0
                for di, dj, dist in _NB:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < m:
                        dmax = repose_slope * (dist if distance_correct else 1.0) * cellsize
                        excess = (h[i, j] - h[ni, nj]) - dmax
                        if excess > 0.0:
                            per.append((ni, nj, excess))
                            total += excess
                            if excess > max_excess:
                                max_excess = excess
                if total > 0.0:
                    moved = factor * max_excess               # steepest pair, NOT the sum -> non-inverting
                    delta[i, j] -= moved
                    for ni, nj, e in per:
                        delta[ni, nj] += moved * (e / total)
        h += delta
    return h
