"""Depression handling and flow routing (03-flow-routing.md).

- priority_flood_fill: Barnes, Lehman & Mulla 2014 priority-flood + epsilon.
- breach_fill: Lindsay 2016 least-cost breaching under the HYBRID policy `03` calls "the right
  default for terrain generation" — breach shallow pits (noise artefacts), fill deep ones (real
  basins, which is where lakes come from).
- d8_receivers / d8_accumulation: O'Callaghan & Mark 1984 single-receiver routing.
- mfd_accumulation: Freeman 1991 multiple-flow-direction (p = 1.1).
- hybrid_accumulation: the hybrid `03` recommends — MFD on the hillslope, D8 once a cell's own
  accumulated area has channelised — decided inside the single pass, not spliced afterwards.

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


def _depressions(dem, spill):
    """(labels, components) for the 8-connected depression regions — cells the fill would raise."""
    n, m = dem.shape
    dep = spill > dem + 1e-12
    lab = np.full((n, m), -1, dtype=np.int64)
    comps = []
    for i in range(n):
        for j in range(m):
            if not dep[i, j] or lab[i, j] >= 0:
                continue
            k = len(comps)
            lab[i, j] = k
            stack, cells = [(i, j)], []
            while stack:
                ci, cj = stack.pop()
                cells.append((ci, cj))
                for di, dj, _ in _NB:
                    ni, nj = ci + di, cj + dj
                    if 0 <= ni < n and 0 <= nj < m and dep[ni, nj] and lab[ni, nj] < 0:
                        lab[ni, nj] = k
                        stack.append((ni, nj))
            comps.append(cells)
    return lab, comps


def _breach_route(dem, pi, pj):
    """The minimax ("least-cost") escape route from a pit: the path out whose HIGHEST cell is as
    low as possible, ending at the first cell strictly below the pit. Returns the path from the
    pit to that outlet, or None when the pit is the lowest reachable ground (nothing to breach to).

    Minimax and not shortest-path on purpose: the bottleneck of that route IS the depression's
    spill point, so the depth this path has to cut is exactly the depth the fill would have added.
    That identity is what lets one `max_depth` threshold mean the same thing to both policies.
    """
    n, m = dem.shape
    pit_z = dem[pi, pj]
    cost = np.full((n, m), np.inf)
    prev = np.full((n, m, 2), -1, dtype=np.int64)
    cost[pi, pj] = pit_z
    heap = [(pit_z, pi, pj)]
    while heap:
        c, i, j = heapq.heappop(heap)
        if c > cost[i, j]:
            continue
        if dem[i, j] < pit_z:                       # an outlet: ground the pit can drain onto
            path = [(i, j)]
            while (i, j) != (pi, pj):
                i, j = int(prev[i, j, 0]), int(prev[i, j, 1])
                path.append((i, j))
            return path[::-1]
        for di, dj, _ in _NB:
            ni, nj = i + di, j + dj
            if not (0 <= ni < n and 0 <= nj < m):
                continue
            nc = max(c, dem[ni, nj])                # cost of a route = its highest cell
            if nc < cost[ni, nj]:
                cost[ni, nj] = nc
                prev[ni, nj] = (i, j)
                heapq.heappush(heap, (nc, ni, nj))
    return None


def breach_fill(dem, max_depth=10.0, *, eps=1e-5):
    """Depression handling under the HYBRID policy of `03`: **breach shallow pits, fill deep ones**.

    `03` calls this "the right default for terrain generation", and the reason is a rendering fact
    rather than a hydrological one: *fill everything and you lose all your lakes* — every basin that
    should hold water is raised to its rim — while *breach everything* carves absurd canyons out of
    legitimate craters and calderas. A depression whose spill sits `max_depth` or less above its
    lowest cell is treated as a noise artefact and CARVED out (Lindsay 2016 least-cost breaching,
    monotonically descending along the minimax escape route); anything deeper is a real basin and is
    left for the priority-flood pass, which raises it to its spill level as a lake. `03` suggests
    `maxDepth = 5-20 m` depending on vertical scale; the default here is the middle of that band.

    Returns a DEM in which every interior cell drains — the same postcondition
    `priority_flood_fill` gives, which is what flow accumulation requires — so this is a drop-in
    alternative to it, not a stage that runs before it.

    The two limits are exact and are what the guard rows pin:
      * `max_depth = 0`   -> nothing is shallow enough to breach; the result is BITWISE
                            `priority_flood_fill(dem, eps)`.
      * `max_depth = inf` -> every depression with an outlet is breached, so the only cells left
                            above the input are the residue the final fill still has to close.

    ⚠️ NO `cellsize`, DELIBERATELY. `max_depth` is a DEPTH in the DEM's own vertical units and
    every other decision here is a comparison of elevations, so no horizontal length enters. A
    `cellsize` was written into this signature for symmetry with its neighbours and was caught by
    the dead-parameter census in `tests/test_render.py` before it shipped — which is what that
    census is for. `eps` is keyword-only so a stale `breach_fill(dem, cellsize)` cannot put a cell
    size into `max_depth`.
    """
    dem = np.asarray(dem, dtype=np.float64)
    out = dem.copy()
    spill = priority_flood_fill(dem, eps=0.0)                  # spill levels, no epsilon tilt
    _, comps = _depressions(dem, spill)
    for cells in comps:
        zs = [dem[c] for c in cells]
        pi, pj = cells[int(np.argmin(zs))]
        pit_z = float(dem[pi, pj])
        if float(spill[pi, pj]) - pit_z > max_depth:      # a real basin -> leave it to become a lake
            continue
        path = _breach_route(out, pi, pj)
        if path is None or len(path) < 2:                 # no lower ground to drain onto: fill it
            continue
        exit_z = float(out[path[-1]])
        steps = len(path) - 1
        for t, (ci, cj) in enumerate(path[1:], start=1):  # carve, never raise, monotone descending
            z = pit_z - (pit_z - exit_z) * t / steps
            if z < out[ci, cj]:
                out[ci, cj] = z
    return priority_flood_fill(out, eps=eps)


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
    than MFD's 1.11x. The exact statement of the same failure is the outlet invariant -- sum the
    accumulation over the cells that have no strictly-lower neighbour and it must equal the
    domain area, because that is where all the routed water ends up. This router returns
    1.000000000000 of it on every DEM tried; the splice returns 1.039.

    ⚠️ A SECOND SYMPTOM WAS CLAIMED HERE AND IT WAS WRONG. This docstring used to add that the
    splice "breaks downstream monotonicity on 17% of links". It does -- and so does the genuine
    hybrid, at 16.7%, and pure MFD at 21.4%, against D8's 0.0%. Measured along single-receiver
    D8 links, that number is ordinary multiple-flow behaviour: a cell that splits its water
    sends only part of it to its steepest neighbour, so the neighbour can hold less. The
    statistic does not distinguish a splice from a router, and the stated cause -- the MFD
    hillslope's water never entering the D8 channel -- is refuted by the fix not moving it.

    A hybrid has to be ONE pass. Every cell is visited high to low exactly once, and the only
    thing that changes is how its accumulated area leaves: split among all lower neighbours by
    `slope^p` while the cell is still a hillslope, sent whole to the steepest neighbour once its
    own accumulated area reaches `channel_cells`. Water is conserved because it is routed, not
    composited.

    `channel_cells` is the channelisation threshold in CELLS of contributing area. `03` gives the
    rule and not the number -- it is a landscape property, not a constant -- so it is a parameter
    and the caller states what it used. Two limits are worth knowing because they are what the
    guard asserts: at `channel_cells <= 1` every cell is channelised from the start and this
    returns `d8_accumulation` exactly; above the cell count of the domain nothing ever
    channelises and it returns `mfd_accumulation` exactly.

    WHERE IT IS WIRED IN, AND WHERE IT IS NOT. `03` recommends the hybrid as "what most good
    terrain tools do", so the node graph can select it: `graph_demo.py`'s `_area_fn` routes
    `method="hybrid"` here and passes `channel_cells` through, which makes the recommendation
    reachable from the shipped graph rather than only from this module. What is still true is
    that nothing takes it by *default* — the demo graph's `area` node ships `method="d8"`, and
    the figure, gallery and archetype paths call `d8_accumulation` or `mfd_accumulation`
    directly. Its other consumers are `flow_anatomy.py` (panel c) and `test_flow_anatomy.py`.
    Stated rather than left quietly true, so a reader knows which paths this router is on.
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
