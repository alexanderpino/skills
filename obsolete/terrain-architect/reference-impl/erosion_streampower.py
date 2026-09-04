"""Stream-power fluvial incision + hillslope diffusion (04-erosion-hydraulic.md).

Braun & Willett 2013 O(N) implicit solver, applied as in Cordonnier et al. 2016:
    dh/dt = U - K * A^m * S^n + D * laplacian(h)
Nodes are processed receiver-before-donor so the implicit update is a single linear solve
per node. At steady state (U = K A^m S^n) the slope-area relation is S ∝ A^(-m/n) — a
straight line of slope -m/n on a log-log plot, which is the decisive verification (09).

The `D` term is the companion Cordonnier et al. (2016) add, and the chapter is emphatic
about it: **stream power alone carves channels and leaves the interfluves as unweathered
plateaux with knife-edge divides.** Diffusion is what rounds a hilltop. It is coupled here
rather than left to the caller because the two rates are not independent — their competition
is what selects a valley spacing (Perron, Kirchner & Dietrich 2008; Perron, Dietrich &
Kirchner 2009), so running them as separate un-coupled passes gives you no handle on the one
landscape property the pair exists to determine. Measured numbers, and what this harness can
and cannot show about it, are in `stream_power_evolve`.

Domain edges are fixed base level. Receivers are computed vectorised; depressions are
filled each step (flow.priority_flood_fill) so interior lakes still route.
"""
import numpy as np

import diffusion
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


def stream_power_evolve(h, uplift, K, m_exp, dt, iters, cellsize=1.0, D=0.0):
    """Evolve to (near) steady state under `dh/dt = U - K A^m S^n + D laplacian(h)`.
    Edges held at base level 0.

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
    `K=lambda hh: bed_erodibility(strat_coord(hh, x, y, tilt=...), table)`.

    `D` (hillslope diffusivity, m^2/yr; ~0.01-0.1 in nature) adds the **coupled** creep term
    `+D laplacian(h)`, run as an explicit pass after the fluvial solve each iteration. `D=0`
    (the default) is the pure-fluvial solver, bit-for-bit as before. `D` may be a scalar or an
    (n, m) field — a soil-mantled slope creeps and a bare rock face does not.

    **The competition is the point, not either rate.** Fluvial incision cuts valleys in;
    diffusion fills them back and rounds the divides between them, and the balance selects a
    valley spacing — the mechanism behind evenly-spaced ridges and valleys (Perron, Kirchner &
    Dietrich 2008 *JGR* 113:F04016, "Controls on the spacing of first-order valleys"; Perron,
    Dietrich & Kirchner 2009 *Nature* 460:502). Measured here on 80x80, K=1, m=0.5, U=1, dt=1,
    200 steps (`tests/test_streampower.py::test_diffusion_sets_valley_spacing_and_smooths_divides`):

        D        valley spacing (cells)   mean |laplacian| (divide roughness)
        0.0            3.32                        1.4135
        0.1            3.38                        0.6797
        0.5            3.81                        0.2588
        1.5            6.33                        0.1078
        4.0            9.76                        0.0512
       10.0       network fully erased             0.0204

    and in the other direction, at fixed D=0.5, raising K from 1 -> 2 -> 4 tightens spacing
    3.81 -> 3.59 -> 3.37. Two cautions, both learned the hard way here:

      * **Measure valley SPACING (mean distance to the nearest channel), not channel COUNT.**
        The count is flat — it read 360/363/316/211/215 over that same sweep, and 198/199/205/
        217/184 on a 60x60 tile — because on a domain this size the network fills the grid
        whatever `D` does. It is a resolution-saturated metric with no signal in it.
      * Turned up far enough, diffusion **erases** the network instead of coarsening it (D=10
        above: zero channel cells). A slope-area fit will then degrade for want of anything to
        fit; check the channel count before blaming the solver.

    This harness cannot test the stronger claim that the *ratio* alone fixes the geometry:
    holding D/K at 0.5 while scaling both (K,D = 1,0.5 -> 2,1 -> 4,2) gave spacing 3.81 ->
    4.58 -> 5.91, because at fixed `iters` the scaled runs sit at different stages of
    evolution rather than at a matched steady state. The monotone trends above are what is
    measured; ratio-invariance is the literature's claim, not ours.

    Stability: the explicit Laplacian needs `D*dt/cellsize^2 <= 0.25`, which the caller's
    fluvial `dt` will usually violate, so the diffusion is **sub-cycled** internally via
    `diffusion.stable_dt`. Nothing to tune; `dt` stays the fluvial timestep."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    Df = np.broadcast_to(np.asarray(D, dtype=np.float64), (n, m))
    D_max = float(Df.max())
    n_sub, dt_sub = 0, 0.0
    if D_max > 0.0:
        # Sub-cycle the explicit Laplacian under `diffusion.stable_dt`, and note that its 0.9 SAFETY
        # FACTOR is load-bearing, not decoration: the 5-point stencil amplifies the checkerboard mode
        # by 1 - 8c (c = D*dt/cellsize^2), so c = 0.25 exactly gives -1 — the mode flips sign forever
        # and never damps. Sizing with a bare `ceil(D*dt/(0.25*cellsize^2))` lands *exactly* on 0.25
        # for every D that divides evenly, so the scheme roughened the terrain instead of smoothing it
        # (mean |laplacian| rose 0.68 -> 2.36 across D = 0.1 -> 10) while staying "stable" by any
        # blow-up test. Going through `stable_dt` keeps c at 0.225.
        n_sub = max(1, int(np.ceil(dt / diffusion.stable_dt(D_max, cellsize))))
        dt_sub = dt / n_sub
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
        if n_sub:
            # Hillslope creep, the Cordonnier companion term. `hillslope_diffuse` rolls (periodic),
            # but every interior cell's 5-point stencil only ever reads cells that are themselves
            # interior or on the edge ring, and the ring is pinned to 0 both before and after — so
            # for the interior this IS the Dirichlet solution. Only the ring itself sees the wrap,
            # and it is overwritten immediately.
            h = diffusion.hillslope_diffuse(h, Df, dt_sub, iters=n_sub, cellsize=cellsize)
            h[edge] = 0.0
    return h


def main():
    """`python erosion_streampower.py` -> erosion_streampower.png: the D sweep, because the
    coupling is the kind of claim that has to be looked at as well as measured."""
    import render

    n, iters = 220, 260
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    panels, pad = [], np.full((n, 5, 3), 20, np.uint8)
    for D in (0.0, 0.5, 2.0, 6.0):
        h = stream_power_evolve(h0, 1.0, 1.0, 0.5, 1.0, iters, D=D)
        if panels:
            panels.append(pad)
        panels.append(render.hillshade(h, 1.0))
        print(f"  D={D:<4} relief {h.max():6.2f}")
    render.write_png("erosion_streampower.png", np.hstack(panels))
    print("wrote erosion_streampower.png  (D = 0 | 0.5 | 2 | 6, left to right)")
    print("  D=0 is the knife-edge interfluve the chapter warns about; D=2 is the classic")
    print("  'SPL channels + diffusion hillslopes' look; D=6 has begun erasing the network.")


if __name__ == "__main__":
    main()
