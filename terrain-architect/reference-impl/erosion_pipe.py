"""Virtual-pipe shallow-water flow (04-erosion-hydraulic.md). Mei, Decaudin & Hu 2007.

This module implements the WATER solver — the canonical hard part of the pipe model and
where its documented failure modes live: without the step-3 outflow scaling, a cell can
drain more water than it holds, depth goes negative, the velocity term divides by a
negative and the sim NaNs within ~20 steps. The scaling is included and verified (depth
stays >= 0, field stays finite). The 8-pipe stencil (per-pipe length) is verified to be
more radially symmetric than the 4-pipe stencil on a cone.

`pipe_water` is the WATER solver alone (periodic boundaries, conserves water exactly — the
reference the radial/conservation tests pin down). `pipe_erode` layers the **sediment/erosion
coupling** on top (open, draining boundaries): the flow's velocity sets a transport CAPACITY, the
bed is eroded where the flow is under capacity and material is DEPOSITED where it is over — alluvial
fans, deltas, valley fill — with suspended sediment advected by **Eulerian flux-form** upwind transport
(each cell exports `c·outflow` and imports the neighbours' inflowing sediment through the same pipes,
so transport is mass-conserving by construction — not a semi-Lagrangian backward trace) and mass conserved. That
is the full Mei-2007 landscape-evolution loop and the base the pro tools' hydro-erosion nodes descend
from. For a production pipeline it wants a GPU; the reference here pins down the algorithm.
"""
import numpy as np

_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
_LEN = [1.0, 1.0, 1.0, 1.0] + [np.sqrt(2.0)] * 4
_OPP = [1, 0, 3, 2, 7, 6, 5, 4]           # index of the opposite direction


def _shift(a, di, dj):
    return np.roll(np.roll(a, di, axis=0), dj, axis=1)


def pipe_water(b, d, iters, *, rain=0.0, evap=0.0, dt=0.02, g=9.81, cellsize=1.0,
               pipes=8, flux_const=1.0):
    """Advance water depth `d` over terrain `b` for `iters` steps. Returns new depth.

    Caveat: the flux accel here is `g·dh/(len·cellsize)` while the depth update divides by `area=cellsize²`
    — the pair is physically scaled only at **cellsize=1** (the resolution this reference solver is exercised
    at; the conservation/radial tests use it there). Mass is conserved at any cellsize (the flux exchange is
    a symmetric roll), but the flow *rate* is not physically scaled off the grid — `pipe_erode`/`shallow_water`
    carry the cellsize-correct `g·cellsize` form for that."""
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


# --------------------------------------------------------------------------- #
# coupled hydraulic erosion  (water shapes the terrain — Mei et al. 2007, full loop)
# --------------------------------------------------------------------------- #
def pipe_erode(bed, cellsize, *, rain=3.0e-4, iters=700, dt=None, capacity=0.6, erode=0.6,
               deposit=0.12, evaporate=0.012, min_tilt=0.05, d_min=1.0e-3, v_max=8.0,
               max_erode=1.0, drain_edges=True, sources=None, settle=True, g=9.81):
    """Couple the pipe flow to sediment transport and let the water reshape `bed` (Mei 2007). Each
    step: rain → pipe flux (mass-clamped, open/draining edges) → velocity → capacity
    ``C = capacity·sin(tilt)·|v|`` (only in WET cells) → **erode** where under capacity (rate-limited)
    / **deposit** where over → **mass-conservative sediment transport by the water fluxes** → evaporate.
    Stability guards: velocity uses a depth floor + a speed cap `v_max`; erosion is capped at
    `max_erode` per step. Returns a dict: `bed` (evolved terrain), `water`, `sediment`, `discharge`
    (m³/s), and a `budget` (bed volume before/after, exported). `settle` drops any remaining suspended
    load at the end (a closed run returns every grain — the mass check)."""
    bed = np.asarray(bed, dtype=np.float64).copy()
    n0, n1 = bed.shape
    if dt is None:
        dt = 0.10 * cellsize / np.sqrt(g * max(np.ptp(bed), 1.0))
    area = cellsize * cellsize
    d = np.zeros_like(bed); s = np.zeros_like(bed)                          # water depth, suspended sediment
    fL = np.zeros_like(bed); fR = np.zeros_like(bed)
    fT = np.zeros_like(bed); fB = np.zeros_like(bed)
    pipe = g * cellsize
    ghost0 = float(bed.min()) - 1.0e7
    bed0_vol = float(bed.sum()) * area
    exported = 0.0

    for _ in range(int(iters)):
        d += rain * dt
        if sources:
            for (i, j, q) in sources:
                d[i, j] += q * dt / area
        dpre = d                                                           # depth the fluxes are built from
        H = bed + dpre
        gh = np.full((n0 + 2, n1 + 2), ghost0) if drain_edges else np.pad(H, 1, mode="edge")
        gh[1:-1, 1:-1] = H
        fL = np.maximum(0.0, fL + dt * pipe * (H - gh[1:-1, 0:-2]))
        fR = np.maximum(0.0, fR + dt * pipe * (H - gh[1:-1, 2:]))
        fT = np.maximum(0.0, fT + dt * pipe * (H - gh[0:-2, 1:-1]))
        fB = np.maximum(0.0, fB + dt * pipe * (H - gh[2:, 1:-1]))
        out = fL + fR + fT + fB
        k = np.where(out > 1e-12, np.minimum(1.0, dpre * area / (out * dt + 1e-12)), 1.0)
        fL *= k; fR *= k; fT *= k; fB *= k
        out = fL + fR + fT + fB
        infl = np.pad(fR, 1)[1:-1, 0:-2]; infr = np.pad(fL, 1)[1:-1, 2:]
        intp = np.pad(fB, 1)[0:-2, 1:-1]; inbt = np.pad(fT, 1)[2:, 1:-1]
        inflow = infl + infr + intp + inbt
        d = np.maximum(dpre + dt * (inflow - out) / area, 0.0)

        dmean = np.maximum(0.5 * (dpre + d), 1.0e-3)                        # floor kills the /0 velocity spike
        vx = 0.5 * (infl - fL + fR - infr) / (cellsize * dmean)            # Mei velocity from the fluxes
        vy = 0.5 * (intp - fT + fB - inbt) / (cellsize * dmean)
        speed = np.minimum(np.hypot(vx, vy), v_max)                        # cap runaway boundary velocities
        wet = (dpre > d_min).astype(np.float64)                            # only flowing water erodes

        gy, gx = np.gradient(bed, cellsize)
        slope = np.hypot(gx, gy)
        sin_t = np.maximum(slope / np.sqrt(1.0 + slope * slope), min_tilt)
        cap = capacity * sin_t * speed * wet                              # transport capacity (m of sediment)
        er = np.where(cap > s, np.minimum(erode * (cap - s), max_erode), 0.0)   # pick up (rate-limited)
        dep = np.where(cap <= s, deposit * (s - cap), 0.0)                # drop (≤ s since deposit ≤ 1)
        bed += dep - er
        s += er - dep

        # sediment transport that MIRRORS the water routing (conservative): each cell's suspended load
        # rides its water out through the same pipes at concentration c = s/depth.
        c = s / np.maximum(dpre, 1.0e-3)
        cL = np.pad(c, 1)[1:-1, 0:-2]; cR = np.pad(c, 1)[1:-1, 2:]
        cT = np.pad(c, 1)[0:-2, 1:-1]; cB = np.pad(c, 1)[2:, 1:-1]
        sed_in = cL * infl + cR * infr + cT * intp + cB * inbt
        sed_out = c * out
        s = np.maximum(s + dt * (sed_in - sed_out) / area, 0.0)
        d *= (1.0 - evaporate * dt)

    if settle:
        bed += s                                                          # drop any remaining load
        s = np.zeros_like(s)
    # with settle, a closed basin conserves bed volume exactly; a draining one loses `exported` off the edge
    exported = bed0_vol - float(bed.sum()) * area
    return {"bed": bed, "water": d, "sediment": s, "discharge": fL + fR + fT + fB,
            "budget": {"bed0": bed0_vol, "bed1": float(bed.sum()) * area, "exported": exported}}


def main():
    """Before/after demo: raw uplifted noise -> coupled hydraulic erosion. Shows the carved valleys
    AND the deposition (fans/valley fill) the stream-power core can't make. -> erosion_pipe.png."""
    import noise
    import render
    n, cell = 150, 27.0
    idx = np.arange(n) * cell / (n * cell * 0.4)
    gx, gy = np.meshgrid(idx, idx)
    warp, _, _ = noise.domain_warp(gx, gy, 5, warp=2.0, octaves=6)
    det = noise.fbm(gx * 1.4 + warp, gy * 1.4 + warp, 5, octaves=7)
    det = (det - det.min()) / (np.ptp(det) + 1e-9)
    ramp = np.clip((np.arange(n)[:, None] - n * 0.35) / (n * 0.65), 0.0, 1.0)   # flat basin -> steep front
    base = ramp * 1600.0 + det * (300.0 + 500.0 * ramp)                  # a mountain front above a basin
    r = pipe_erode(base, cell, rain=1.2e-3, iters=1400)
    eroded = r["bed"]
    dz = eroded - base

    before = render.hillshade(base, cell)
    after = render.hillshade(eroded, cell)
    lim = max(np.abs(dz).max(), 1e-6)                                     # deposition RED, erosion BLUE
    t = np.clip(dz / lim, -1, 1)
    dzmap = np.stack([np.clip(128 + 127 * t, 0, 255),
                      np.full_like(dz, 110),
                      np.clip(128 - 127 * t, 0, 255)], axis=-1).astype(np.uint8)
    pad = np.full((n, 5, 3), 20, np.uint8)
    render.write_png("erosion_pipe.png", np.hstack([before, pad, after, pad, dzmap]))
    b = r["budget"]
    print(f"wrote erosion_pipe.png  (before | after | deposition-red/erosion-blue)")
    print(f"  {n}² @ {cell:.0f} m; eroded off the edge {b['exported']:.2e} m³; "
          f"peak discharge {r['discharge'].max():.1f} m³/s; deposited max {dz.max():.0f} m, incised max {-dz.min():.0f} m")


if __name__ == "__main__":
    main()
