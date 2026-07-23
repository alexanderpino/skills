"""Hydrology — turn a DISCHARGE field (volumetric flow, m³/s) into a water SURFACE for rendering.
Water is a substance at a level, not a colour painted on the bed:

  * **rivers** carry a depth set by their discharge via bankfull hydraulic geometry (depth grows with
    Q — Leopold & Maddock 1953); at landscape resolution the true channel is narrower than a cell, so
    the *discharge* (not a cell-wide sheet) is the physical truth and the channel is drawn from it;
  * **lakes** fill enclosed depressions to their spill level (priority-flood, `flow.py`).

The discharge comes from a real mass-conserving flow — `shallow_water.simulate` (a rainfall source,
water depth as state, pipe flux, m³/s throughput) — or, when you don't want to time-step, from
`discharge_from_area` (Q = rainfall × upstream drainage area, exactly what the sim converges to under
uniform rain). `water_depth = surface − bed`. Rendering the surface (a level in the channel) is what
makes water read as water in 3-D.
"""
import numpy as np

import flow


def discharge_from_area(area, rain=2.0e-6):
    """Steady-state discharge `Q = rain · upstream_area` (m³/s) — the cheap proxy for a full
    shallow-water run. Under uniform runoff this is exactly the flow `shallow_water.simulate`
    converges to. `area` is drainage area (m²); `rain` a runoff rate (m/s)."""
    return np.asarray(area, dtype=np.float64) * rain


def water_surface(bed, cellsize, discharge, *, q_channel=None, depth_coef=1.4, depth_exp=0.4,
                  max_river_depth=9.0, lakes=True, smooth=1.0):
    """Water-surface elevation `w >= bed` from a DISCHARGE field `Q` (m³/s). River depth follows
    bankfull hydraulic geometry `depth = depth_coef·(Q/q_channel)^depth_exp` (capped), in cells above
    the channel discharge threshold; lakes fill enclosed depressions to spill level. `smooth`
    gaussian-relaxes the wet surface so it reads calm."""
    bed = np.asarray(bed, dtype=np.float64)
    Q = np.asarray(discharge, dtype=np.float64)
    w = bed.copy()
    if lakes:
        w = np.maximum(w, flow.priority_flood_fill(bed))                    # basins fill flat to the spill
    if q_channel is None:
        q_channel = float(np.quantile(Q, 0.985))
    is_channel = Q >= q_channel
    depth = depth_coef * np.power(np.maximum(Q, 1e-9) / (q_channel + 1e-9), depth_exp)
    depth = np.clip(depth, 0.0, max_river_depth) * is_channel               # discharge-scaled river depth
    w = np.maximum(w, bed + depth)
    if smooth > 0.0:
        wet = w > bed + 1e-6
        if wet.any():
            import ops_filters
            ws = ops_filters.gaussian(w, smooth)
            w = np.where(wet, np.maximum(ws, bed), w)
    return w


def water_depth(bed, cellsize, discharge, **kw):
    """Depth of standing/flowing water (surface − bed), 0 on dry land."""
    return water_surface(bed, cellsize, discharge, **kw) - np.asarray(bed, dtype=np.float64)


def water_colour(depth, max_depth=7.0, shallow=(96, 148, 168), deep=(28, 62, 104), sky=(206, 221, 236)):
    """Depth-tinted still-water colour: shallow teal → deep blue, lifted slightly toward the sky it
    reflects. Returns float RGB (0-255) per cell. (Opaque; for the translucent stage use
    `water_over_land`.)"""
    d = np.clip(np.asarray(depth, dtype=np.float64) / max_depth, 0.0, 1.0)
    col = np.array(shallow, np.float64) * (1 - d[..., None]) + np.array(deep, np.float64) * d[..., None]
    return col * 0.85 + np.array(sky, np.float64) * 0.15


def water_over_land(land_rgb, depth, *, k=0.45, tint=(24, 66, 104), sky=(200, 218, 238), sheen=0.10):
    """Composite **translucent** water over the already-lit land as a SEPARATE render stage (like snow,
    water is its own pass). Beer–Lambert transmittance ``T = exp(-k·depth)``: shallow water lets the bed
    (rock/soil) show through, deep water hides it under a blue `tint`; a little `sheen` adds the sky the
    calm surface reflects. `land_rgb` is the shaded land colour (float 0-255), `depth` the water depth
    (m). Returns float RGB — dry cells are unchanged."""
    land = np.asarray(land_rgb, dtype=np.float64)
    d = np.clip(np.asarray(depth, dtype=np.float64), 0.0, None)
    T = np.exp(-k * d)[..., None]                                           # fraction of the bed still visible
    water = land * T + np.array(tint, np.float64) * (1.0 - T)              # bed seen through, tinted by depth
    water = water * (1.0 - sheen) + np.array(sky, np.float64) * sheen       # calm surface reflects a little sky
    wet = (d > 1e-4)[..., None]
    return np.where(wet, water, land)
