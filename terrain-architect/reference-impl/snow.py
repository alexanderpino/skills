"""Snowpack dynamics — a time-evolving snow layer (13-climate-ecosystem.md).

`analysis.derive_substances` places snow as a STATIC elevation+aspect mask. This is the dynamic
model of chapter 13 (`snowStep`, Cordonnier et al. 2018): snow accumulates where it is cold, melts
where it is warm (degree-day), sheds off steep ground, and — the step that matters —
**avalanches**, which is *thermal erosion on the snow layer* (`05`, a lower repose angle). Snow
relaxed on `h + snowDepth` slides off steep faces and piles in gullies and at the base of slopes —
which is where snow actually is. Without step 4 snow is a slope-thresholded mask painted uniformly,
"which reads as fake instantly because it ignores that snow *moves*." Optional wind redistribution
scours windward crests and builds lee cornices (the dune shadow-zone logic, `05`).

Tier: F-tier "look" held to invariants — accumulate-cold / melt-warm, no snow past the shed slope,
the avalanche conserves snow and drives the snow surface below its repose, and snow collects in
hollows. Not a certified snow-water-equivalent oracle.
"""
import numpy as np

import analysis

_SQRT2 = np.sqrt(2.0)
_NB = ((-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
       (-1, -1, _SQRT2), (-1, 1, _SQRT2), (1, -1, _SQRT2), (1, 1, _SQRT2))


def _smoothstep(lo, hi, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - lo) / (hi - lo + 1e-30), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def thermal_on_layer(base, layer, repose_slope, iters=4, cellsize=1.0, factor=0.25):
    """Talus relaxation of a granular LAYER resting on a fixed BASE (13/05). Slopes are measured on
    the SURFACE `base + layer`, but only the layer moves — a cell can shed no more than the layer it
    holds — so the layer avalanches over the terrain, conserving its mass and never going negative.
    This is the chapter's `thermal(field=snowDepth, base=h, talusAngle=snowRepose)`. Same Musgrave
    steepest-pair sizing as `erosion_thermal` (non-inverting); double-buffered and deterministic."""
    base = np.asarray(base, dtype=np.float64)
    layer = np.asarray(layer, dtype=np.float64).copy()
    n, m = layer.shape
    for _ in range(int(iters)):
        s = base + layer
        delta = np.zeros_like(layer)
        for i in range(n):
            for j in range(m):
                if layer[i, j] <= 0.0:
                    continue
                per, total, max_excess = [], 0.0, 0.0
                for di, dj, dist in _NB:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < m:
                        excess = (s[i, j] - s[ni, nj]) - repose_slope * dist * cellsize
                        if excess > 0.0:
                            per.append((ni, nj, excess))
                            total += excess
                            if excess > max_excess:
                                max_excess = excess
                if total > 0.0:
                    moved = min(factor * max_excess, layer[i, j])   # can't move more snow than present
                    delta[i, j] -= moved
                    for ni, nj, e in per:
                        delta[ni, nj] += moved * (e / total)
        layer = layer + delta
    return np.maximum(layer, 0.0)


def wind_redistribute(h, snow, wind, *, cellsize=1.0, rate=0.4, iters=3):
    """Scour snow from windward-exposed cells and deposit it one cell downwind — the dune shadow-zone
    logic (`05`), which strips crests and builds lee cornices. `wind=(u, v)` in (col, row) components.
    Conserves snow (scoured mass is re-deposited, not lost)."""
    u, v = wind
    mag = float(np.hypot(u, v)) + 1e-30
    u, v = u / mag, v / mag
    di, dj = int(round(v)), int(round(u))                   # downwind cell offset (row, col)
    snow = np.asarray(snow, dtype=np.float64).copy()
    h = np.asarray(h, dtype=np.float64)
    for _ in range(int(iters)):
        gy, gx = np.gradient(h + snow, cellsize)
        exposure = np.clip(u * gx + v * gy, 0.0, None)      # surface rising INTO the wind = windward
        scoured = rate * snow * np.tanh(5.0 * exposure)
        snow = snow - scoured + np.roll(np.roll(scoured, di, 0), dj, 1)   # deposit one cell downwind
    return np.maximum(snow, 0.0)


def snow_step(h, snow_depth, T, precip, *, dt=1.0, melt_factor=0.6, snow_repose_deg=37.0,
              shed_lo_deg=50.0, shed_hi_deg=60.0, cellsize=1.0, avalanche_iters=4,
              wind=None, wind_rate=0.4):
    """One `snowStep` (13): accumulate cold -> degree-day melt -> shed steep -> avalanche (thermal on
    the snow layer) -> optional wind redistribution. `T` and `precip` may be scalars or fields (a
    lapse-rate temperature field `T0 - lapse*h` is the usual driver). Returns the new snow depth."""
    snow = np.asarray(snow_depth, dtype=np.float64).copy()
    T = np.asarray(T, dtype=np.float64)
    precip = np.asarray(precip, dtype=np.float64)
    snow = snow + precip * (T < 0.0) * dt                              # 1. accumulate where cold
    snow = snow - np.maximum(0.0, melt_factor * T) * dt               # 2. degree-day melt
    snow = np.maximum(snow, 0.0)
    slope = analysis.slope(h, cellsize)                               # 3. shed steep ground
    snow = snow * (1.0 - _smoothstep(np.tan(np.radians(shed_lo_deg)),
                                     np.tan(np.radians(shed_hi_deg)), slope))
    snow = thermal_on_layer(h, snow, np.tan(np.radians(snow_repose_deg)),               # 4. avalanche
                            iters=avalanche_iters, cellsize=cellsize)
    if wind is not None:                                             # 5. wind redistribution (cornices)
        snow = wind_redistribute(h, snow, wind, cellsize=cellsize, rate=wind_rate)
    return snow
