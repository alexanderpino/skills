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

F-tier structural look; `fault_weakness` becomes P-tier once the erosion runs on it.
"""
import numpy as np


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
