"""Placement & masking — the art-direction layer (10-primitives-ops-filters.md).

Procedural terrain that only generates *everywhere* cannot be art-directed. Two operations make it
directable, and they are the pair every terrain tool converges on:

  PLACE   build a mask from a signed distance field positioned in WORLD coordinates, so a feature
          lands where the layout says (`disc`, `rect`, `capsule`, `polygon`).
  MASK    apply any effect only where a mask is bright (`apply_masked`) — the universal
          "mask input" that lets one graph erode a valley here and leave the plateau alone.

Everything is in **metres via `cellsize`**, never cells (08): a placement authored against a layout
must not move when the build resolution changes. `falloff` is the width of the soft edge in metres —
a hard 0/1 mask produces a visible seam in any blend, so the default is a smooth edge.

The SDF primitives themselves live in `ops_filters` (`sd_circle`, `sd_box`, `sd_segment`,
`sd_convex_polygon`); this module positions them on a grid and turns distance into coverage.
"""
import numpy as np

import ops_filters


def coords(shape, cellsize=1.0, center=(0.0, 0.0), rotation=0.0):
    """Object-space (x, y) grids in METRES for a primitive placed at `center` (metres from the
    grid origin) and turned by `rotation` radians. Rotating the *coordinates* by -rotation is what
    rotates the shape by +rotation."""
    n, m = shape
    y, x = np.mgrid[0:n, 0:m].astype(np.float64)
    x = x * cellsize - center[0]
    y = y * cellsize - center[1]
    if rotation:
        c, s = np.cos(-rotation), np.sin(-rotation)
        x, y = x * c - y * s, x * s + y * c
    return x, y


def coverage(sdf, falloff=0.0, cellsize=1.0):
    """Signed distance (metres, negative inside) -> coverage mask in [0,1].

    `falloff` is the soft-edge width in METRES, centred on the boundary. 0 gives a hard edge, which
    is antialiased to one cell rather than left as a staircase — a truly binary mask shows its
    jaggies through every downstream blend."""
    sdf = np.asarray(sdf, dtype=np.float64)
    w = max(float(falloff), float(cellsize))          # never sharper than one cell
    return ops_filters._smoothstep(w * 0.5, -w * 0.5, sdf)


def disc(shape, cellsize=1.0, center=(0.0, 0.0), radius=1.0, falloff=0.0):
    """Circular placement mask. `center`/`radius`/`falloff` in metres."""
    x, y = coords(shape, cellsize, center)
    return coverage(ops_filters.sd_circle(x, y, radius), falloff, cellsize)


def rect(shape, cellsize=1.0, center=(0.0, 0.0), half_extent=(1.0, 1.0),
         rotation=0.0, falloff=0.0):
    """Rectangular placement mask, `rotation` in radians. All lengths in metres."""
    x, y = coords(shape, cellsize, center, rotation)
    return coverage(ops_filters.sd_box(x, y, half_extent[0], half_extent[1]), falloff, cellsize)


def capsule(shape, cellsize=1.0, a=(0.0, 0.0), b=(1.0, 0.0), radius=1.0, falloff=0.0):
    """A thick line segment from `a` to `b` — the mask for a river corridor, road or ridgeline."""
    x, y = coords(shape, cellsize)
    d = ops_filters.sd_segment(x, y, a[0], a[1], b[0], b[1]) - radius
    return coverage(d, falloff, cellsize)


def polygon(shape, cellsize=1.0, normals=None, offsets=None, falloff=0.0):
    """Convex-polygon mask from half-plane `normals`/`offsets` (see `ops_filters.sd_convex_polygon`)."""
    x, y = coords(shape, cellsize)
    return coverage(ops_filters.sd_convex_polygon(x, y, normals, offsets), falloff, cellsize)


def path_mask(shape, cellsize=1.0, points=None, radius=1.0, falloff=0.0):
    """A polyline corridor: the union of `capsule`s along `points`. This is the "draw a shape and
    use it as a mask" primitive — author a spine, get a mask that follows it."""
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or len(pts) < 2:
        raise ValueError("path_mask needs at least two (x, y) points")
    x, y = coords(shape, cellsize)
    d = None
    for p, q in zip(pts[:-1], pts[1:]):
        seg = ops_filters.sd_segment(x, y, p[0], p[1], q[0], q[1])
        d = seg if d is None else np.minimum(d, seg)
    return coverage(d - radius, falloff, cellsize)


def apply_masked(base, modified, mask):
    """THE masking rule: an effect applies only where the mask is bright.

    `base` is the field before the effect, `modified` the field after it ran everywhere, `mask` the
    coverage in [0,1]. Returns the per-cell interpolation. Applying an effect and *then* masking it
    like this is a post-process — changing the mask does not re-run the effect, which is why it is
    cheap enough to iterate on layout interactively."""
    base = np.asarray(base, dtype=np.float64)
    modified = np.asarray(modified, dtype=np.float64)
    m = np.clip(np.asarray(mask, dtype=np.float64), 0.0, 1.0)
    return base + (modified - base) * m


def stamp(base, patch, mask=None, mode="max"):
    """Composite a placed feature `patch` onto `base`.

    `mode`: `max` (union — the usual way to drop a landform in without trenching what is there),
    `add` (accumulate relief), or `replace` (overwrite inside the mask). `mask` restricts it;
    without one the patch applies everywhere it is defined."""
    base = np.asarray(base, dtype=np.float64)
    patch = np.asarray(patch, dtype=np.float64)
    if mode == "max":
        out = np.maximum(base, patch)
    elif mode == "add":
        out = base + patch
    elif mode == "replace":
        out = patch
    else:
        raise ValueError(f"unknown stamp mode {mode!r}; expected max, add or replace")
    return out if mask is None else apply_masked(base, out, mask)
