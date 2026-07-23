"""Stream-power fluvial incision (04-erosion-hydraulic.md).

Braun & Willett 2013 O(N) implicit solver, applied as in Cordonnier et al. 2016:
    dh/dt = U - K * A^m * S^n     (n = 1 here; the standard, unconditionally-stable case)
Nodes are processed receiver-before-donor so the implicit update is a single linear solve
per node. At steady state (U = K A^m S^n) the slope-area relation is S ∝ A^(-m/n) — a
straight line of slope -m/n on a log-log plot, which is the decisive verification (09).

Domain edges are fixed base level. Receivers are computed vectorised; depressions are
filled each step (flow.priority_flood_fill) so interior lakes still route.
"""
import numpy as np

import flow

_DIRS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
         (-1, -1, np.sqrt(2)), (-1, 1, np.sqrt(2)),
         (1, -1, np.sqrt(2)), (1, 1, np.sqrt(2))]


def receivers(h, cellsize=1.0):
    """Vectorised D8 steepest-descent receiver (row, col, dist) per cell; (-1,-1) if none.
    Off-grid neighbours are +inf so edge cells find no lower neighbour -> base outlets."""
    n, m = h.shape
    pad = np.pad(h, 1, constant_values=np.inf)
    ii, jj = np.mgrid[0:n, 0:m]
    best = np.zeros((n, m))
    ri = np.full((n, m), -1, dtype=np.int64)
    rj = np.full((n, m), -1, dtype=np.int64)
    dd = np.ones((n, m))
    for di, dj, dist in _DIRS:
        nb = pad[1 + di:1 + di + n, 1 + dj:1 + dj + m]
        s = (h - nb) / (dist * cellsize)
        take = s > best
        best = np.where(take, s, best)
        ri = np.where(take, ii + di, ri)
        rj = np.where(take, jj + dj, rj)
        dd = np.where(take, dist * cellsize, dd)
    return ri, rj, best, dd


def drainage_area(h, ri, rj, cellarea=1.0):
    n, m = h.shape
    A = np.full((n, m), float(cellarea))
    order = np.argsort(h.ravel(), kind="stable")[::-1]     # high -> low
    for idx in order:
        i, j = int(idx) // m, int(idx) % m
        if ri[i, j] >= 0:
            A[ri[i, j], rj[i, j]] += A[i, j]
    return A


def stream_power_evolve(h, uplift, K, m_exp, dt, iters, cellsize=1.0):
    """Evolve to (near) steady state. Edges held at base level 0.

    `K` (erodibility) and `uplift` may each be a SCALAR or an (n, m) FIELD. A spatially-varying
    K(x,y) is the lithology coupling (11): hard beds (low K) resist and stand proud as caprock /
    cuestas / structural benches, soft beds (high K) cut to structural valleys — differential
    erosion. Build the field from stratigraphy with `landforms.bed_erodibility(strat, table)`.
    A scalar K broadcasts to a uniform field, so the classic single-K behaviour is unchanged.

    `K` may also be a CALLABLE `K(h) -> field`, re-evaluated on the current surface each iteration.
    That is the faithful `K(p, h)` of the chapter (11): beds are fixed in the rock column, so which
    bed is exposed at a cell depends on the current elevation. As incision cuts down it exposes a
    different bed — the mechanism behind caprock mesas, cuestas, and relief inversion (a hard bed
    laid in a valley bottom ends up standing proud). Pass e.g.
    `K=lambda hh: bed_erodibility(strat_coord(hh, x, y, tilt=...), table)`."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    if callable(K):
        K_of = K                                                  # K(p, h): re-evaluated on the surface
    else:
        _Kf = np.broadcast_to(np.asarray(K, dtype=np.float64), (n, m))   # scalar or field -> fixed field
        K_of = lambda _h: _Kf
    edge = np.zeros((n, m), dtype=bool)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    h[edge] = 0.0
    for _ in range(int(iters)):
        h = h + np.where(edge, 0.0, uplift * dt)
        Kf = np.broadcast_to(np.asarray(K_of(h), dtype=np.float64), (n, m))
        hf = flow.priority_flood_fill(h)
        ri, rj, _, dd = receivers(hf, cellsize)
        A = drainage_area(hf, ri, rj, cellsize * cellsize)
        order = np.argsort(hf.ravel(), kind="stable")       # low -> high: receiver first
        for idx in order:
            i, j = int(idx) // m, int(idx) % m
            if edge[i, j] or ri[i, j] < 0:
                continue
            C = Kf[i, j] * A[i, j] ** m_exp * dt / dd[i, j]  # n = 1 implicit coefficient; K may vary by cell
            h[i, j] = (h[i, j] + C * h[ri[i, j], rj[i, j]]) / (1.0 + C)
            if h[i, j] < h[ri[i, j], rj[i, j]]:              # receiver-floor guard (04): never incise
                h[i, j] = h[ri[i, j], rj[i, j]]              # below your receiver — inside a filled pit
        h[edge] = 0.0                                        # h_r (from filled hf) can exceed h_i
    return h
