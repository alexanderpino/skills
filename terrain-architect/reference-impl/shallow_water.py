"""Shallow-water flow by the VIRTUAL-PIPE model (Mei, Decaudin & Hu 2007, "Fast Hydraulic Erosion
Simulation and Visualization on GPU"). Water is a real, mass-conserving volume — not a painted level:

  * water **depth** ``d(x,y)`` is a state variable (metres);
  * a **source** adds water — uniform rainfall ``rain`` (m/s) and/or point springs (m³/s);
  * water moves through four **virtual pipes** to its 4-neighbours, the flux driven by the
    water-SURFACE (hydraulic head ``bed+d``) difference, and **clamped so a cell never outputs more
    water than it holds** (mass positivity);
  * water **leaves at the domain boundary** (open edges);
  * **discharge** ``Q = Σ outflow`` is a genuine volumetric flow in **m³/s**, and at steady state under
    uniform rain it accumulates downstream ≈ ``rain × upstream drainage area``.

This is the grounded real-time hydraulics the pro tools use (and the base for pipe-model erosion). It
time-steps; run it to near-steady-state for a river network with real discharge. Invariants in
`tests/test_shallow_water.py`: depth ≥ 0, mass is conserved in a closed basin, discharge grows
downstream.
"""
import numpy as np

G = 9.81


def simulate(bed, cellsize, *, rain=2.0e-6, iters=600, dt=None, sources=None, source_field=None,
             drain_edges=True, damp=0.0):
    """Evolve water over `bed` (m). `rain` is a uniform rainfall source in m/s (2e-6 ≈ 7 mm/h);
    `source_field` is an optional per-cell source rate (m/s) added on top — e.g. **snowmelt**, so water
    runs out from under the snow; `sources` is a list of (row, col, q_m3s) point springs. Returns a dict
    with `depth` (m), `discharge` (m³/s per cell, the throughput), `speed` (m/s), and a `budget`."""
    bed = np.asarray(bed, dtype=np.float64)
    n0, n1 = bed.shape
    if dt is None:                                                          # CFL-safe explicit step
        dt = 0.20 * cellsize / np.sqrt(G * max(np.ptp(bed), 1.0))
    area = cellsize * cellsize
    d = np.zeros_like(bed)
    fL = np.zeros_like(bed); fR = np.zeros_like(bed)
    fT = np.zeros_like(bed); fB = np.zeros_like(bed)
    pipe = G * cellsize                                                     # A·g/l with A=l=cellsize -> g·cellsize
    ghost = float(bed.min()) - 1.0e7                                        # open, very low -> boundary drains
    rain_in = 0.0
    out_vol = 0.0

    src = None if source_field is None else np.asarray(source_field, dtype=np.float64)
    for _ in range(int(iters)):
        d += rain * dt                                                      # rainfall source
        rain_in += rain * dt * n0 * n1 * area
        if src is not None:                                                 # per-cell source (e.g. snowmelt)
            d += src * dt
            rain_in += float(src.sum()) * dt * area
        if sources:
            for (i, j, q) in sources:
                d[i, j] += q * dt / area
                rain_in += q * dt

        H = bed + d
        gh = np.full((n0 + 2, n1 + 2), ghost) if drain_edges else np.pad(H, 1, mode="edge")
        gh[1:-1, 1:-1] = H
        dHL = H - gh[1:-1, 0:-2]                                            # head drop to each neighbour
        dHR = H - gh[1:-1, 2:]
        dHT = H - gh[0:-2, 1:-1]
        dHB = H - gh[2:, 1:-1]

        fL = np.maximum(0.0, fL * (1.0 - damp) + dt * pipe * dHL)           # accelerate flux by head
        fR = np.maximum(0.0, fR * (1.0 - damp) + dt * pipe * dHR)
        fT = np.maximum(0.0, fT * (1.0 - damp) + dt * pipe * dHT)
        fB = np.maximum(0.0, fB * (1.0 - damp) + dt * pipe * dHB)

        out = fL + fR + fT + fB
        stored = d * area / dt                                             # max volumetric outflow this step
        k = np.where(out > 1e-12, np.minimum(1.0, stored / (out + 1e-12)), 1.0)
        fL *= k; fR *= k; fT *= k; fB *= k                                  # can't drain more than is held

        # inflow = each neighbour's flux directed at this cell (ghost pads contribute nothing)
        infl = np.pad(fR, 1)[1:-1, 0:-2]      # left neighbour's rightward flux
        infr = np.pad(fL, 1)[1:-1, 2:]        # right neighbour's leftward flux
        intp = np.pad(fB, 1)[0:-2, 1:-1]      # top neighbour's downward flux
        inbt = np.pad(fT, 1)[2:, 1:-1]        # bottom neighbour's upward flux
        inflow = infl + infr + intp + inbt
        outflow = fL + fR + fT + fB

        d += dt * (inflow - outflow) / area
        d = np.maximum(d, 0.0)                                             # guard rounding
        if drain_edges:
            out_vol += dt * float(outflow.sum() - inflow.sum())            # net leaving the domain

    discharge = (fL + fR + fT + fB)                                        # m³/s throughput per cell
    # speed = discharge / cross-section. Floor the depth (a cell that fully drained this step has d≈0
    # while discharge still carries last step's flux → speed would blow up); this keeps the reported
    # field physical, as pipe_erode already does. Dry cells (no discharge) read 0.
    speed = discharge / (np.maximum(d, 1e-3) * cellsize)
    return {"depth": d, "discharge": discharge, "speed": speed,
            "budget": {"rain_in": rain_in, "out": out_vol, "stored": float(d.sum() * area)}}
