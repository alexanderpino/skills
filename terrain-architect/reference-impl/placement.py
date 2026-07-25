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


def place_coords(xx, yy, shape, cellsize=1.0, center=None, rotation=0.0, scale=1.0):
    """Move/turn/resize a GENERATOR by transforming the coordinates it samples, before it runs.

    This is the placement that costs nothing. A procedural generator is a function of position, so
    evaluating it at shifted coordinates moves the feature EXACTLY — the same function, sampled
    somewhere else. Transforming the generator's raster afterwards instead resamples it, and
    bilinear resampling is a low-pass filter: measured on fBm, one non-integer raster move loses
    ~17% of the fine detail and four chained moves lose ~34%, while this loses none.

    Use a raster transform (`ops_filters.resample`, a Transform node) only for fields you cannot
    re-evaluate — an imported DEM, or the output of an erosion sim.

    `xx`, `yy` are the generator's own cell-coordinate grids and the return value replaces them.
    `center` is in METRES (08) and defaults to the tile centre, which is where these generators put
    their feature natively; `rotation` is radians, `scale` > 1 magnifies.
    """
    n0, n1 = shape
    c0x, c0y = 0.5 * n1, 0.5 * n0                     # the generator's native centre, in cells
    cx = c0x if center is None else center[0] / cellsize
    cy = c0y if center is None else center[1] / cellsize
    dx = (np.asarray(xx, dtype=np.float64) - cx) / float(scale)
    dy = (np.asarray(yy, dtype=np.float64) - cy) / float(scale)
    if rotation:
        c, s = np.cos(-rotation), np.sin(-rotation)
        dx, dy = dx * c - dy * s, dx * s + dy * c
    return dx + c0x, dy + c0y


# --------------------------------------------------------------------------- #
# affine placement as a matrix
# --------------------------------------------------------------------------- #
def affine(center=(0.0, 0.0), rotation=0.0, scale=(1.0, 1.0), shear=0.0, pivot=(0.0, 0.0)):
    """The FORWARD 3x3 homogeneous transform that places a feature: feature space -> world space.

    Composed as T(center) . R(rotation) . Sh(shear) . S(scale) . T(-pivot) — scale and rotate about
    `pivot` (a generator's native centre), then move to `center`. `scale` may be a scalar or
    (sx, sy) for non-uniform; `shear` slews x by y.

    Sampling uses the INVERSE of this (`sample_coords`): you iterate over destination pixels and
    need the source coordinate feeding each one. Getting that backwards moves the feature the wrong
    way — the classic sign error in every texture transform. `place_coords` above is this same
    inverse, hand-decomposed for the common translate/rotate/uniform-scale case."""
    sx, sy = (scale, scale) if np.isscalar(scale) else (scale[0], scale[1])
    ct, st = np.cos(rotation), np.sin(rotation)
    T_c = np.array([[1.0, 0.0, center[0]], [0.0, 1.0, center[1]], [0.0, 0.0, 1.0]])
    R = np.array([[ct, -st, 0.0], [st, ct, 0.0], [0.0, 0.0, 1.0]])
    Sh = np.array([[1.0, shear, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    S = np.array([[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]])
    T_p = np.array([[1.0, 0.0, -pivot[0]], [0.0, 1.0, -pivot[1]], [0.0, 0.0, 1.0]])
    return T_c @ R @ Sh @ S @ T_p


def compose(*matrices):
    """Combine placements into ONE transform, applied left to right. For a generator, composing and
    sampling once is equivalent to sampling repeatedly; for a RASTER it is strictly better, because
    every extra resample is another low-pass filter (see `place_coords`)."""
    out = np.eye(3)
    for m in matrices:
        out = np.asarray(m, dtype=np.float64) @ out
    return out


def transform_coords(xx, yy, matrix):
    """Apply a 3x3 homogeneous `matrix` to coordinate grids. Returns (x', y')."""
    m = np.asarray(matrix, dtype=np.float64)
    x = np.asarray(xx, dtype=np.float64)
    y = np.asarray(yy, dtype=np.float64)
    return (m[0, 0] * x + m[0, 1] * y + m[0, 2],
            m[1, 0] * x + m[1, 1] * y + m[1, 2])


def sample_coords(xx, yy, matrix):
    """Destination coords -> SOURCE coords for a feature placed by `matrix`: `transform_coords`
    with the inverse. The feature moves by `matrix`, so the sampler moves by its opposite."""
    return transform_coords(xx, yy, np.linalg.inv(np.asarray(matrix, dtype=np.float64)))
