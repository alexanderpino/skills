"""Depression handling and flow routing (03-flow-routing.md).

- priority_flood_fill: Barnes, Lehman & Mulla 2014 priority-flood + epsilon.
- d8_receivers / d8_accumulation: O'Callaghan & Mark 1984 single-receiver routing.
- mfd_accumulation: Freeman 1991 multiple-flow-direction (p = 1.1).

Pure-numpy + a heap; loops are explicit for readability, sized for test grids.
D-infinity (Tarboton 1997) is intentionally NOT reimplemented here — use RichDEM /
pysheds for it (see README); the D8/MFD pair already demonstrates the
single-receiver-artefact vs dispersive contrast the chapter is about.
"""
import heapq
import numpy as np

# 8 neighbours as (di, dj, distance-in-cells)
_SQRT2 = np.sqrt(2.0)
_NB = (
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, _SQRT2), (-1, 1, _SQRT2), (1, -1, _SQRT2), (1, 1, _SQRT2),
)


def priority_flood_fill(dem, eps=1e-5):
    """Fill depressions so every interior cell drains to the edge, with an epsilon
    gradient across filled flats (so flow directions are defined). Returns filled DEM
    (>= dem everywhere). Barnes et al. 2014."""
    dem = np.asarray(dem, dtype=np.float64)
    n, m = dem.shape
    filled = dem.copy()
    closed = np.zeros((n, m), dtype=bool)
    heap = []
    for i in range(n):
        for j in range(m):
            if i in (0, n - 1) or j in (0, m - 1):
                closed[i, j] = True
                heapq.heappush(heap, (filled[i, j], i, j))
    while heap:
        h, i, j = heapq.heappop(heap)
        for di, dj, _ in _NB:
            ni, nj = i + di, j + dj
            if 0 <= ni < n and 0 <= nj < m and not closed[ni, nj]:
                closed[ni, nj] = True
                if filled[ni, nj] <= h + eps:
                    filled[ni, nj] = h + eps
                heapq.heappush(heap, (filled[ni, nj], ni, nj))
    return filled


def d8_receivers(dem, cellsize=1.0):
    """Steepest-descent single receiver per cell (with sqrt(2) diagonal correction).
    Returns (rec, slope): rec[i,j] = (ri,rj) or (-1,-1) if the cell is an outlet/sink."""
    dem = np.asarray(dem, dtype=np.float64)
    n, m = dem.shape
    rec = np.full((n, m, 2), -1, dtype=np.int64)
    slope = np.zeros((n, m), dtype=np.float64)
    for i in range(n):
        for j in range(m):
            best, bi, bj = 0.0, -1, -1
            for di, dj, dist in _NB:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < m:
                    s = (dem[i, j] - dem[ni, nj]) / (dist * cellsize)
                    if s > best:
                        best, bi, bj = s, ni, nj
            rec[i, j] = (bi, bj)
            slope[i, j] = best
    return rec, slope


def _process_order(dem):
    """Indices sorted high -> low; a valid topological order on a filled DEM."""
    m = dem.shape[1]
    order = np.argsort(dem.ravel(), kind="stable")[::-1]
    return [(int(idx) // m, int(idx) % m) for idx in order]


def d8_accumulation(dem, cellsize=1.0, cellarea=None):
    """Drainage area by D8. Run on a filled DEM. Total area is conserved: it all
    leaves through outlet cells. area units = cellarea (default cellsize^2)."""
    dem = np.asarray(dem, dtype=np.float64)
    if cellarea is None:
        cellarea = cellsize * cellsize
    n, m = dem.shape
    rec, _ = d8_receivers(dem, cellsize)
    acc = np.full((n, m), float(cellarea), dtype=np.float64)
    for i, j in _process_order(dem):
        ri, rj = rec[i, j]
        if ri >= 0:
            acc[ri, rj] += acc[i, j]
    return acc


def mfd_accumulation(dem, cellsize=1.0, p=1.1, cellarea=None):
    """Drainage area by MFD (Freeman 1991): flow splits to all lower neighbours in
    proportion to slope^p. Dispersive — the right default for hillslope quantities."""
    dem = np.asarray(dem, dtype=np.float64)
    if cellarea is None:
        cellarea = cellsize * cellsize
    n, m = dem.shape
    acc = np.full((n, m), float(cellarea), dtype=np.float64)
    for i, j in _process_order(dem):
        ws, tot = [], 0.0
        for di, dj, dist in _NB:
            ni, nj = i + di, j + dj
            if 0 <= ni < n and 0 <= nj < m and dem[ni, nj] < dem[i, j]:
                w = ((dem[i, j] - dem[ni, nj]) / (dist * cellsize)) ** p
                ws.append((ni, nj, w))
                tot += w
        if tot > 0.0:
            share = acc[i, j] / tot
            for ni, nj, w in ws:
                acc[ni, nj] += w * share
    return acc


def hybrid_accumulation(dem, cellsize=1.0, p=1.1, channel_cells=60.0, cellarea=None):
    """Drainage area with MFD on the hillslope and D8 once flow has channelised.

    WHY THIS IS A ROUTER AND NOT A BLEND OF TWO RASTERS. `03` recommends the hybrid as the fix
    for D8's stripes and MFD's smears, and the tempting implementation is
    `np.where(d8 >= t, d8, mfd)` -- splice two completed accumulations. That is not a drainage
    field. Each raster is the answer to a DIFFERENT routing of all the water, so gluing them
    creates water: measured on one 160x160 DEM the splice carries 1.58x D8's total, more even
    than MFD's 1.11x, and it breaks downstream monotonicity on 17% of links because the MFD
    hillslope's water never actually enters the D8 channel it appears to feed.

    A hybrid has to be ONE pass. Every cell is visited high to low exactly once, and the only
    thing that changes is how its accumulated area leaves: split among all lower neighbours by
    `slope^p` while the cell is still a hillslope, sent whole to the steepest neighbour once its
    own accumulated area reaches `channel_cells`. Water is conserved because it is routed, not
    composited.

    `channel_cells` is the channelisation threshold in CELLS of contributing area. `03` gives the
    rule and not the number -- it is a landscape property, not a constant -- so it is a parameter
    and the caller states what it used.
    """
    dem = np.asarray(dem, dtype=np.float64)
    if cellarea is None:
        cellarea = cellsize * cellsize
    n, m = dem.shape
    acc = np.full((n, m), float(cellarea), dtype=np.float64)
    threshold = float(channel_cells) * float(cellarea)
    for i, j in _process_order(dem):
        ws, tot, best, best_w = [], 0.0, None, -1.0
        for di, dj, dist in _NB:
            ni, nj = i + di, j + dj
            if 0 <= ni < n and 0 <= nj < m and dem[ni, nj] < dem[i, j]:
                w = ((dem[i, j] - dem[ni, nj]) / (dist * cellsize)) ** p
                ws.append((ni, nj, w))
                tot += w
                if w > best_w:
                    best, best_w = (ni, nj), w
        if tot <= 0.0:
            continue
        if acc[i, j] >= threshold:                 # channelised: single receiver
            acc[best[0], best[1]] += acc[i, j]
        else:                                      # hillslope: split by slope^p
            share = acc[i, j] / tot
            for ni, nj, w in ws:
                acc[ni, nj] += w * share
    return acc
