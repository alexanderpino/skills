"""Braided / anastomosing rivers — Murray & Paola (1994) cellular braided-stream model (03/04).

A single-thread river (`meander.py`) is ONE channel that migrates; a braided river is MANY
threads that split and rejoin around mid-channel bars. The multi-thread pattern is not authored —
it EMERGES on a gently downstream-sloping, sediment-charged bed (rows = downstream) from three rules:

  1. **Flow splits.** Water in a cell is divided among the three downstream-forward cells,
     weighted by (bed slope + a floor)^(1/2) — so flow follows *every* downhill route, and still
     spreads across bars where the local slope is ~flat (the floor keeps weights > 0).
  2. **Transport capacity is super-linear in discharge and is evaluated PER BRANCH.** Each branch
     `k` can carry `qs_k = K · (Q_k)^m`, m > 1 (Murray & Paola used m ≈ 2.5). This is the braiding
     engine: when a thread SPLITS, its discharge divides, so Σ_k K·(Q_k)^m ≪ K·(Q_total)^m — the
     downstream capacity collapses super-linearly, the incoming sediment can no longer be carried,
     it DEPOSITS at the split → builds a mid-channel BAR → the next flow routes around it → the
     thread has braided. Where flow re-concentrates, capacity rises and the bed is scoured (a
     channel). With m = 1 the split capacities sum back to the single-thread capacity (Σ K·Q_k =
     K·ΣQ_k), so nothing deposits at splits and the reach stays single-thread — the super-linearity
     IS the instability.
  3. **Sediment also moves LATERALLY**, down the cross-stream bed slope — gravitational bank
     relaxation. It is NOT what causes braiding (Murray & Paola: "not crucial to produce braiding"),
     but it lets threads shift and keeps the network dynamic.

The reach is held in the **aggradational regime** real braided rivers occupy: a gentle gradient and
an upstream sediment supply (`feed`) at the top edge, so channels choke and switch rather than incise
into one thread. Sediment is conserved: Σbed_change = fed − exported (to float roundoff).

**Tier — reduced-complexity (illustrative).** This is a cellular / "reduced-complexity" (RC) model:
it reproduces braiding *statistically* — multi-thread topology (braiding index > 1), the super-linear
instability, and a closed mass budget — the properties Murray & Paola set out to capture. It does NOT
reproduce a photoreal woven planform; a row-by-row cellular reach reads as downstream-grained threads,
and crisp braid morphology needs a depth-resolved morphodynamic (CFD) solver (Delft3D / BASEMENT
class), which is out of scope for this pure-NumPy sandbox. Grounding: Murray & Paola 1994 (*A cellular
model of braided rivers*, Nature 371:54–57); 1997 (*Properties of a cellular braided-stream model*,
ESP&L 22). See `references/03-flow-routing.md` and `reference-impl/CANON-COMPARISON.md`.
"""
import numpy as np

_DJ = (-1, 0, 1)                                        # the three downstream-forward columns


def braided_river(bed, steps, *, Q0=40.0, feed=0.3, m_exp=2.5, K=0.02, erode_rate=0.55,
                  lateral=0.04, slope_add=0.001, cellsize=1.0, return_budget=False):
    """Evolve a gently downstream-sloping, sediment-charged `bed` (rows = downstream flow direction)
    into a braided channel network by the Murray–Paola rules. `Q0` = total water inflow spread across
    the top row, `feed` = per-cell sediment supply at the top edge (the aggradational forcing —
    raise it for a more braided, more strongly aggrading reach; 0 lets the reach rework only its own
    bed), `m_exp` = transport exponent (**> 1 braids, = 1 stays single-thread**), `K` = transport
    coefficient, `erode_rate` in [0,1] = fraction of the local capacity surplus scoured from the bed
    per pass, `lateral` in [0,~0.1] = cross-stream gravitational bank relaxation (thread shifting, not
    the braiding cause), `slope_add` = the small routing-weight floor that keeps flow moving over
    flats and past pits (so water + sediment are always fully routed → no sink). Keep `slope_add`
    **small** — a large floor forces the water to spread regardless of the bed, masking the emergent,
    `m`-driven braiding. The reach braids best on a **gentle** mean gradient (~0.0015–0.004 per cell);
    a steep bed funnels to a single thread.
    Returns `(bed, discharge)`, or `(bed, discharge, budget)` if `return_budget`. Sediment is conserved:
    Σbed_change = fed − exported (to float roundoff)."""
    bed = np.asarray(bed, dtype=np.float64).copy()
    bed0_total = float(bed.sum())
    n, m = bed.shape
    cols = np.arange(m)
    Q = np.zeros((n, m))
    fed = exported = 0.0                               # sediment mass budget (grounds the conservation claim)
    for _ in range(int(steps)):
        Q = np.zeros((n, m))
        Q[0, :] = Q0 / m                               # water in across the top row; CONSERVED downstream (no rain)
        load = np.zeros((n, m))                        # sediment in transport, arriving from upstream
        load[0, :] = feed                              # upstream sediment supply (aggradational forcing)
        fed += float(load[0].sum())
        dbed = np.zeros((n, m))
        for i in range(n):
            if i == n - 1:
                exported += float(load[i].sum())       # what reaches the downstream edge leaves the reach
                break
            # routing weights to the three forward cells, (slope + floor)^1/2, zero off-grid
            ws = []
            jcs = []
            for dj in _DJ:
                jj = cols + dj
                valid = (jj >= 0) & (jj < m)
                jc = np.clip(jj, 0, m - 1)
                jcs.append(jc)
                s = np.maximum((bed[i] - bed[i + 1, jc]) / cellsize, 0.0)
                ws.append(np.sqrt(s + slope_add) * valid)   # slope_add floor -> weights stay > 0 (full routing)
            wsum = ws[0] + ws[1] + ws[2] + 1e-12
            Qk = [Q[i] * (w / wsum) for w in ws]            # per-branch discharge
            capk = [K * (q ** m_exp) for q in Qk]           # PER-BRANCH capacity (super-linear -> collapses on split)
            Cout = capk[0] + capk[1] + capk[2]              # total downstream transport capacity out of this cell
            incoming = load[i]
            over = incoming > Cout
            deposit = np.where(over, incoming - Cout, 0.0)            # split chokes capacity -> deposit -> BAR
            erode = np.where(over, 0.0, erode_rate * (Cout - incoming))   # re-concentrated flow scours -> CHANNEL
            dbed[i] += deposit - erode
            sent = incoming + erode - deposit                        # = min(incoming+erode, Cout); conserved
            capsum = Cout + 1e-12
            for k in range(3):                                       # water by weight, sediment by branch capacity
                np.add.at(Q[i + 1], jcs[k], Qk[k])
                np.add.at(load[i + 1], jcs[k], sent * capk[k] / capsum)
        bed += dbed
        if lateral:                                    # gravitational lateral relaxation (thread shifting; conserves)
            fl = lateral * (bed[:, :-1] - bed[:, 1:])   # strict flux form (no-flux edges) -> conserves EXACTLY per row
            bed[:, :-1] -= fl
            bed[:, 1:] += fl
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
