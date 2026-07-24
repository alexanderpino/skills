"""Braided / anastomosing rivers — Murray & Paola (1994) cellular braided-stream model (03/04).

A single-thread river (`meander.py`) is ONE channel that migrates; a braided river is MANY
threads that split and rejoin around mid-channel bars. The multi-thread pattern is not authored —
it EMERGES from three rules on a bed that slopes downstream (rows = downstream):

  1. **Flow splits.** Water in a cell is divided among the three downstream-forward cells,
     weighted by (bed slope)^(1/2) — so flow follows *every* downhill route, not just the steepest.
  2. **Transport is super-linear in discharge.** Capacity `qs = K · Q^m`, m > 1 (Murray & Paola
     used m ≈ 2.5). A cell carries what its discharge allows: under capacity it ERODES (picks up
     sediment, bed drops); over capacity it DEPOSITS (bed rises). Super-linearity makes a few deep
     threads far more effective than many shallow ones — the concentrating half of the instability.
  3. **Sediment also moves LATERALLY**, down the cross-stream bed slope — which fills the low
     threads' neighbours into BARS. Bars split the flow again → the braid.

Deposition/erosion is the divergence of the sediment flux, and sediment is conserved (bed change +
what leaves the downstream edge = 0). Grounding: Murray & Paola 1994 (*A cellular model of braided
rivers*, Nature 371:54–57); 1997 (*JGR* 102). Illustrative F-tier: reproduces the multi-thread
PATTERN, the braiding instability, and the mass budget — not a calibrated transport rate.
"""
import numpy as np

_DJ = (-1, 0, 1)                                        # the three downstream-forward columns


def braided_river(bed, steps, *, Q0=1.0, rain=0.02, m_exp=2.5, K=0.03, erode_rate=0.5,
                  lateral=0.20, sed_feed=0.9, slope_add=0.003, cellsize=1.0, return_budget=False):
    """Evolve a downstream-sloping `bed` (rows = downstream flow direction) into a braided channel
    network by the Murray–Paola rules. `Q0` = inflow across the top row, `rain` = per-cell input,
    `m_exp` = transport exponent (>1 braids), `K` = transport coefficient, `erode_rate` in [0,1] =
    fraction of the capacity deficit picked up per pass, `lateral` in [0,~0.25] = cross-stream
    sediment diffusion (bar building), `sed_feed` in [0,1] = sediment supplied at the upstream edge
    as a fraction of the local capacity (Murray–Paola upstream supply; ~1 holds the reach at GRADE
    so it braids rather than incising, <1 lets it incise), `slope_add` keeps flow moving over flats.
    Returns `(bed, discharge)`. Sediment is conserved: Σbed_change = fed − exported."""
    bed = np.asarray(bed, dtype=np.float64).copy()
    bed0_total = float(bed.sum())
    n, m = bed.shape
    Q = np.zeros((n, m))
    cols = np.arange(m)
    fed = exported = 0.0                                # sediment mass budget (grounds the conservation claim)
    for _ in range(int(steps)):
        Q[:] = rain
        Q[0, :] += Q0 / m
        load = np.zeros((n, m))                        # sediment in transport, arriving from upstream
        load[0] = sed_feed * (K * Q[0] ** m_exp)       # upstream sediment supply (grade control)
        fed += float(load[0].sum())
        dbed = np.zeros((n, m))
        for i in range(n):
            cap = K * Q[i] ** m_exp                     # transport capacity (super-linear in discharge)
            qs_in = load[i]
            over = qs_in > cap
            deposit = np.where(over, qs_in - cap, 0.0)            # excess drops out -> bar/aggradation
            erode = np.where(over, 0.0, erode_rate * (cap - qs_in))   # deficit picks bed up -> incision
            dbed[i] += deposit - erode
            carried = qs_in + erode - deposit                    # = min(qs_in+erode, cap); conserved
            if i == n - 1:
                exported += float(carried.sum())                 # carried leaves the downstream edge
                break
            # routing weights to the three forward cells, (slope)^1/2, zero off-grid
            ws = []
            for dj in _DJ:
                jj = cols + dj
                valid = (jj >= 0) & (jj < m)
                jc = np.clip(jj, 0, m - 1)
                s = np.maximum((bed[i] - bed[i + 1, jc]) / cellsize, 0.0)
                ws.append(np.sqrt(s + slope_add) * valid)   # slope_add is a FLOOR under the sqrt:
                #   weights stay > 0 even at a local pit (flow then spreads to all forward cells),
                #   so wsum > 0 and water + sediment are ALWAYS fully routed (no sink -> conserves)
            wsum = ws[0] + ws[1] + ws[2] + 1e-12
            for k, dj in enumerate(_DJ):                         # distribute water AND sediment forward
                jc = np.clip(cols + dj, 0, m - 1)
                frac = ws[k] / wsum
                np.add.at(Q[i + 1], jc, Q[i] * frac)
                np.add.at(load[i + 1], jc, carried * frac)
        bed += dbed
        if lateral:                                    # lateral sediment transport -> builds bars between threads
            fl = lateral * (bed[:, :-1] - bed[:, 1:])   # flux across each internal cross-stream face
            bed[:, :-1] -= fl                           # strict flux form (no-flux edges) -> conserves EXACTLY
            bed[:, 1:] += fl                            #   within each row, so Σbed_change = fed − exported
    if return_budget:
        budget = {"fed": fed, "exported": exported, "bed_change": float(bed.sum()) - bed0_total}
        return bed, Q, budget
    return bed, Q


def braiding_index(Q, threshold_frac=0.25):
    """Mean number of active channel THREADS per cross-section — the standard braiding metric. A
    single-thread (meandering/straight) river ~1; a braided one > 1. Count, per downstream row, the
    runs of cells whose discharge exceeds `threshold_frac` × the row's max, then average over rows
    that carry flow."""
    Q = np.asarray(Q, dtype=np.float64)
    counts = []
    for row in Q:
        peak = row.max()
        if peak <= 0:
            continue
        wet = row > threshold_frac * peak
        runs = int(np.sum((wet[1:] & ~wet[:-1])) + (1 if wet[0] else 0))   # rising edges = thread count
        counts.append(runs)
    return float(np.mean(counts)) if counts else 0.0
