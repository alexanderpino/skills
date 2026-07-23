"""Hydrology — a WATER SURFACE over the terrain. Water is a substance that sits at a LEVEL in the
channel the terrain carved, not a colour painted on the bed:

  * **lakes** fill enclosed depressions to their spill level (priority-flood, `flow.py`) — a flat pool;
  * **rivers** carry a discharge-scaled depth in their channels (bankfull hydraulic geometry — depth
    grows with discharge, Leopold & Maddock 1953), so the water surface is a coherent ribbon slightly
    above the bed, descending downstream.

`water_depth = surface - bed`. Rendering the *surface* (flat, depth-tinted) instead of the bed is what
makes water read as water in a 3-D view. A graph node, not a tweak: it takes the eroded height + the
drainage area the flow nodes already produce.
"""
import numpy as np

import flow


def water_surface(bed, area, cellsize, *, channel_area=None, depth_coef=1.1, depth_exp=0.4,
                  max_river_depth=7.0, lakes=True, smooth=1.0):
    """Water-surface elevation `w >= bed`. `area` is drainage area (m², from `flow` accumulation).
    Lakes fill to spill level; river depth = `depth_coef · (A/channel_area)^depth_exp` (capped),
    only in cells above the channel threshold. `smooth` gaussian-relaxes the surface so it reads calm."""
    bed = np.asarray(bed, dtype=np.float64)
    area = np.asarray(area, dtype=np.float64)
    w = bed.copy()
    if lakes:
        w = np.maximum(w, flow.priority_flood_fill(bed))                    # basins fill flat to the spill
    if channel_area is None:
        channel_area = float(np.quantile(area, 0.985))
    is_channel = area >= channel_area
    depth = depth_coef * np.power(np.maximum(area, 1e-9) / (channel_area + 1e-9), depth_exp)
    depth = np.clip(depth, 0.0, max_river_depth) * is_channel               # discharge-scaled river depth
    w = np.maximum(w, bed + depth)
    if smooth > 0.0:                                                        # calm the surface (still water)
        wet = w > bed + 1e-6
        if wet.any():
            import ops_filters
            ws = ops_filters.gaussian(w, smooth)
            w = np.where(wet, np.maximum(ws, bed), w)                       # keep the surface above the bed
    return w


def water_depth(bed, area, cellsize, **kw):
    """Depth of standing/flowing water (surface - bed), 0 on dry land."""
    return water_surface(bed, area, cellsize, **kw) - np.asarray(bed, dtype=np.float64)


# shallow -> deep water colour (calm water also picks up a little sky); pass depth in metres
def water_colour(depth, max_depth=7.0, shallow=(96, 148, 168), deep=(28, 62, 104), sky=(206, 221, 236)):
    """Depth-tinted still-water colour: shallow teal → deep blue, lifted slightly toward the sky it
    reflects. Returns float RGB (0-255) per cell (0 where dry)."""
    d = np.clip(np.asarray(depth, dtype=np.float64) / max_depth, 0.0, 1.0)
    col = np.array(shallow, np.float64) * (1 - d[..., None]) + np.array(deep, np.float64) * d[..., None]
    return col * 0.85 + np.array(sky, np.float64) * 0.15
