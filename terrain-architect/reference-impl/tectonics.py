"""Faults & plates — structural tectonics (02-macro-tectonics.md).

Two documented-but-unbuilt pieces of chapter 02:

* `fault_scarp` — the `faultIteration` displacement fractal: sum N random fault lines, each
  offsetting the two sides with a feathered scarp, displacement decaying over iterations. It is a
  fractal, not a simulation ("it has no drainage"), useful as a structural detail layer.

* `fault_weakness` — the *geologically-correct* coupling the chapter recommends INSTEAD of raw
  displacement: emit a spatially-varying erodibility `K(x,y)` weakened along the fault traces, then
  feed it to `erosion_streampower.stream_power_evolve` (`04`). Erosion exploiting the fractured, weak
  fault lines produces valleys that follow structure — which is exactly what real faulted terrain
  looks like. This reuses the Phase-1 spatial-K coupling.

* `plate_uplift` — the plate-boundary pseudocode of chapter 02: Voronoi plates with noise-warped
  boundaries, each boundary classified (collision / subduction / island-arc / rift / transform), and
  the boundary uplift diffused inland over the orogen width. Produces the tectonic elevation/uplift
  field that the chapter's ★★★★ thesis then feeds to fluvial erosion. F-tier (a plausible planar
  plate sketch, not plate physics).

F-tier structural look; `fault_weakness` becomes P-tier once the erosion runs on it.
"""
import numpy as np

import noise
import ops_filters


def _fault_lines(shape, n_faults, rng):
    """Yield (point, unit-normal) for N random fault lines across the domain."""
    n, m = shape
    for _ in range(int(n_faults)):
        px, py = rng.uniform(0, m), rng.uniform(0, n)
        ang = rng.uniform(0.0, np.pi)
        nx, ny = -np.sin(ang), np.cos(ang)                 # unit normal to the line
        yield (px, py), (nx, ny)


def fault_scarp(h, *, n_faults=6, displacement=40.0, width=6.0, decay=0.75, cellsize=1.0, seed=0):
    """`faultIteration` (02): offset the two sides of each of N random fault lines, feathered over a
    width `w` (a smooth step, not a hard cliff), with the displacement decaying each iteration so the
    first faults are the big range-bounding ones and later faults add finer blocky structure. A
    fractal detail layer — no drainage. Returns a new height field."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    rng = np.random.default_rng(seed)
    disp = float(displacement)
    for (px, py), (nx, ny) in _fault_lines((n, m), n_faults, rng):
        sd = (nx * (xx - px) + ny * (yy - py)) * cellsize   # signed distance to the fault line
        h = h + 0.5 * disp * np.tanh(sd / max(width * cellsize, 1e-9))   # feathered up/down offset
        disp *= decay
    return h


def fault_weakness(shape, *, n_faults=6, k_rock=1.0, k_fault=6.0, width=4.0, cellsize=1.0, seed=0):
    """Emit an erodibility field `K(x,y)` with the N fault traces set MORE erodible (`k_fault > k_rock`)
    than the surrounding rock (02: the geologically-correct coupling). A fault is a zone of fractured,
    weak rock, so erosion cuts it fastest — feed this to `stream_power_evolve` as its `K` and the
    valleys follow the fault structure. `width` is the Gaussian half-width of the weak band, in cells.
    Returns K (= k_fault on a trace, = k_rock away from all faults)."""
    n, m = shape
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    rng = np.random.default_rng(seed)
    weak = np.zeros((n, m))                                 # 0 away from faults, ->1 on a fault trace
    for (px, py), (nx, ny) in _fault_lines((n, m), n_faults, rng):
        sd = nx * (xx - px) + ny * (yy - py)                # perpendicular distance (cells)
        weak = np.maximum(weak, np.exp(-(sd / max(width, 1e-9)) ** 2))
    return k_rock + (k_fault - k_rock) * weak               # lerp UP toward k_fault (weak) on the traces


def plate_uplift(shape, *, n_plates=12, seed=0, warp_amp=9.0, warp_freq=0.045, relax=2,
                 ocean_frac=0.45, orogen_width=12.0, amplitude=2600.0, collision=1.0,
                 subduction=0.7, arc=0.45, rift=0.6, ocean_base=-4000.0, cont_base=200.0,
                 cellsize=1.0, return_plates=False):
    """Plate-tectonic elevation field (02): Voronoi plates with **noise-warped** boundaries, each
    boundary classified into collision / subduction / island-arc (convergent), rift (divergent) or
    transform (shear), and the boundary uplift **diffused inland** over the orogen width. Returns the
    tectonic elevation field = per-plate base elevation (oceanic ≈ -4000 m, continental ≈ +200 m) plus
    the diffused orogen uplift. `n_plates` ≈ 8-20 for a continent-scale map. F-tier (a plausible planar
    plate sketch, not plate physics); feed the orogen uplift to stream power, or render directly."""
    n, m = shape
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    rng = np.random.default_rng(seed)
    cy = rng.uniform(0, n, n_plates)
    cx = rng.uniform(0, m, n_plates)
    # domain-warp the coordinates so plate boundaries are not straight Voronoi edges (the tell)
    wx = xx + warp_amp * noise.fbm(xx * warp_freq, yy * warp_freq, seed)
    wy = yy + warp_amp * noise.fbm(xx * warp_freq, yy * warp_freq, seed + 7)

    def assign(px, py):
        d = (py[..., None] - cy) ** 2 + (px[..., None] - cx) ** 2      # (n, m, P)
        return d.argmin(-1)

    for _ in range(int(relax)):                                        # Lloyd relaxation -> even plates
        pid0 = assign(xx, yy)
        for p in range(n_plates):
            sel = pid0 == p
            if sel.any():
                cy[p], cx[p] = yy[sel].mean(), xx[sel].mean()
    pid = assign(wx, wy)                                               # warped Voronoi partition

    vel = rng.normal(0.0, 1.0, (n_plates, 2))                          # 2D plate velocities
    is_ocean = rng.random(n_plates) < ocean_frac
    base = np.where(is_ocean, ocean_base, cont_base)

    boundary = np.zeros((n, m))
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nb = np.roll(np.roll(pid, di, 0), dj, 1)
        diff = nb != pid
        a, b = pid, nb
        nx, ny = cx[b] - cx[a], cy[b] - cy[a]
        nl = np.hypot(nx, ny) + 1e-9
        nx, ny = nx / nl, ny / nl                                      # unit normal a -> b
        rvx, rvy = vel[a, 0] - vel[b, 0], vel[a, 1] - vel[b, 1]        # relative velocity
        conv = rvx * nx + rvy * ny                                     # >0 converging
        shear = np.abs(rvx * ny - rvy * nx)
        conv_dom = np.abs(conv) >= shear                              # else transform (~0 uplift)
        oa, ob = is_ocean[a], is_ocean[b]
        val = np.zeros((n, m))
        cong = conv_dom & (conv > 0)
        val = np.where(cong & (~oa) & (~ob), collision * conv, val)   # continent-continent collision
        val = np.where(cong & (oa ^ ob), subduction * conv, val)      # subduction (one oceanic)
        val = np.where(cong & oa & ob, arc * conv, val)               # island arc (both oceanic)
        val = np.where(conv_dom & (conv < 0), rift * conv, val)       # rift (conv<0 -> subsidence)
        boundary += np.where(diff, val, 0.0)
    boundary *= 0.5                                                    # each boundary seen from both sides

    orogen = ops_filters.gaussian(boundary, orogen_width / cellsize)  # diffuse inland (orogen width)
    elevation = base[pid] + amplitude * orogen
    if return_plates:
        return elevation, pid
    return elevation
