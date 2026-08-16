"""The scene the screen-space pass is drawn over, and the buffers it consumes.

WHAT IS THE CHAPTER'S AND WHAT IS MINE, stated first because the whole point of
this directory is that the chapter's real-time half has never been run:

  THE CHAPTER'S (`12-water-rendering.md`, *Screen-space water: the
  fullscreen-triangle pass*), reproduced here as specified:
    * a flat water datum at `h_water`, one plane per body;
    * a depth buffer of the OPAQUE scene as the pass's only geometric input,
      with the reject rule "if the scene hit is nearer than t, output nothing";
    * the reconstruction using "the frame's actual depth convention
      (reversed-Z, jitter)";
    * the guards on `|rayDir.z| < eps`, `t < 0`, and the below-datum sign flip.

  MINE (choices, and none of them is authored content -- every surface below is
  a plane or a box, and `render.py`'s rule holds: no texture, no Voronoi, no
  noise):
    * the particular body: a shoaling shelf, so that OPTICAL DEPTH SWEEPS ACROSS
      THE FRAME. That is the one property the measurement needs and the chapter
      does not specify a scene at all. Depth runs 0 -> 3.00 m, i.e. tau_red
      0 -> 0.785, which is the span of the chapter's own scaling table.
    * the deck, the post, the camera, the resolution.
    * z is UP and the datum is z = 0, which is `render.py`'s convention, not the
      chapter's `camPos.y`. Same equation, one axis renamed; the rename is here
      so that every constant imported from `reference-impl` keeps its meaning.

WHY A SHELF AND NOT THE POOL. `render.py`'s basin is 1.40 m at its deepest and
one depth cannot show an error that is a function of depth. The chapter's
factorisation error goes from 3.6% at tau = 0.05 to 39.6% at tau = 1.00, and the
only way to put that on a frame is to put the tau range on the frame.

NOTHING IN THIS FILE PRINTS, for the reason given at the head of `optics.py`.
"""
import sys as _sys
import os as _os

import numpy as np

_REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                     '..', 'reference-impl')
if _REF not in _sys.path:
    _sys.path.insert(0, _REF)

import optics as OPT                                            # noqa: E402
import atmosphere as ATM                                        # noqa: E402


# ------------------------------------------------------------------- the body
H_WATER = 0.0        # the datum. One number, because the chapter's pass is a
                     # single-datum pass: "per-body planes" is the multi-body
                     # branch and it is not built here (see README, `Not built`).
D_MAX = 3.00         # m. Chosen so that tau_red = ABS[0]*D_MAX = 0.785 lands at
                     # the top of the LUT domain and inside the chapter's own
                     # scaling table; 3 m is also a plausible shelf edge.
SLOPE = 0.18         # bed gradient; reaches D_MAX at x = D_MAX/SLOPE = 16.67 m.
DECK_Z = 0.22        # freeboard, m. `render.py`'s liner freeboard is 0.10 m of
                     # blue wall plus the coping course; 0.22 is that order and
                     # its only job here is to make the near band of the frame an
                     # opaque reject (the chapter's ray B).
DECK_X = 0.0         # the waterline. Land is x < 0, water is x >= 0.

RHO_BED = np.array([0.24, 0.54, 0.70])
# ^ QUOTED, not derived here: `render.py` line 388, "A real pool liner is BLUE,
#   not white plaster. Absolute albedo ~ (0.24, 0.54, 0.70)". Taken as a
#   CONSTANT over the bed rather than through `render.py`'s `liner(u, v)`,
#   which carries a mottle this scene has no need of and which would be the only
#   authored field in the directory. A constant bed is also what isolates the
#   measurement: every variation in the water's colour across the frame is then
#   optical depth and nothing else.
RHO_DECK = np.array([0.676, 0.536, 0.414])     # `render.py`'s PAV_ALB
RHO_POST = np.array([0.38, 0.33, 0.29])
# ^ MINE. A weathered timber pile; its only job is to be an above-water occluder
#   with a colour that is not the deck's, so a reject is visible as a reject.

POST = np.array([[5.60, 0.90, -D_MAX], [5.92, 1.22, 1.10]])   # aabb, m
# ^ a 0.32 m square pile standing 1.10 m proud of the datum at (5.76, 1.06).
#   Placed so its silhouette falls on water in the hero frame and its shadow
#   does not touch the waterline, where the shallow-tau measurement lives.


def bed_z(x):
    """The bed, as a field. z_bed <= 0 everywhere in the water; a plane for
    x < 0 does not exist (that is the deck) and callers must not ask."""
    return -np.minimum(D_MAX, np.maximum(SLOPE * x, 0.0))


def water_depth(x):
    """Column thickness under the datum. Zero at the waterline by construction,
    which is what makes the frame carry the tau -> 0 limit the chapter says a
    lossless check cannot see."""
    return H_WATER - bed_z(x)


# ------------------------------------------------------------------ the camera
# A STANDING EYE, deliberately. `12`'s own converse -- "a Lambertian bed under a
# flat surface emits a near-Lambertian field into the air" -- is a NADIR
# statement, and the chapter says so in the same breath: over `render.py`'s own
# frame the water spans 44-73 deg from vertical and the shape factor alone varies
# by 17.6%. A drone camera would hide that; this one does not, and the pass-vs-
# offline comparison in `validate_raster.py` is where it shows up.
EYE = np.array([-2.60, 0.00, 1.62])
CAM_AZ = np.deg2rad(4.0)        # look nearly down +x, 4 deg off so the post is
                                # not dead centre and the sun's road is oblique
CAM_EL = np.deg2rad(-9.0)       # horizon in the upper third at this FOV
FOV = np.deg2rad(50.0)
NEAR = 0.05                     # m. Reversed-Z with an INFINITE far plane, so
                                # `near` is the only depth parameter there is.
RES = (560, 315)                # w, h. 16:9. See README, `Why 560x315`.


def basis(az=CAM_AZ, el=CAM_EL):
    """Camera basis, right-handed, z up. Returns (fwd, right, up)."""
    f = np.array([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el)])
    r = np.cross(f, np.array([0., 0., 1.]))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return f, r, u


def ray_dirs(ndc_x, ndc_y, az=CAM_AZ, el=CAM_EL, fov=FOV, aspect=None):
    """Step 1 of the chapter's pixel shader: "build `rayDir` from the camera
    basis and pixel NDC". NDC in [-1, 1]; +y is UP the screen.

    Origin is the camera and everything is camera-relative, which is the
    chapter's own instruction and `09`'s. Returns (..., 3), normalised."""
    if aspect is None:
        aspect = RES[0] / RES[1]
    f, r, u = basis(az, el)
    th = np.tan(0.5 * fov)
    d = (f[None] + (ndc_x * th * aspect)[..., None] * r[None]
         + (ndc_y * th)[..., None] * u[None])
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def pixel_ndc(res=RES, jitter=None):
    """Pixel CENTRES in NDC. `jitter` is a (dx, dy) offset in pixels, because
    the chapter's step 3 says the reconstruction "must use the frame's actual
    depth convention (reversed-Z, jitter)" -- a TAA jitter that the depth
    prepass applies and the water pass does not is one of the three traps the
    section names, and `validate_raster.py` measures it rather than repeating
    it."""
    w, h = res
    jx, jy = (0.0, 0.0) if jitter is None else jitter
    px = (np.arange(w) + 0.5 + jx) / w
    py = (np.arange(h) + 0.5 + jy) / h
    X, Y = np.meshgrid(2.0 * px - 1.0, 1.0 - 2.0 * py)
    return X, Y


# ------------------------------------------------- reversed-Z, infinite far
# THE CONVENTION, WRITTEN OUT, because the chapter names "reversed-Z
# reconstruction mismatch" as one of the pass's three traps and a trap you cannot
# reproduce is a trap you cannot test.
#
#   view depth      w = dot(P - eye, fwd)                 [m, positive forward]
#   reversed-Z      z = near / w                          [1 at the near plane,
#                                                          -> 0 at infinity]
#   reconstruction  w = near / z                          [exactly invertible]
#
# The infinite far plane is not a simplification: it is the standard reversed-Z
# projection precisely because `far` drops out of `near/w`, and it is what makes
# the horizon of a fullscreen-triangle water pass representable at all. The
# float32 storage is the point of the whole scheme -- floats are dense near 0,
# which is where the FAR distances land, so relative precision is roughly
# constant in w. `depth_precision_m` below turns that into metres so the suite
# can put an absolute number on it.
def project_depth(w, near=NEAR):
    """View depth -> reversed-Z buffer value, stored float32 as a GPU would."""
    return np.float32(near / np.maximum(np.asarray(w, float), near))


def unproject_depth(z, near=NEAR):
    """Buffer value -> view depth. The inverse, exactly."""
    z = np.asarray(z, np.float32).astype(np.float64)
    out = np.full(z.shape, np.inf)
    m = z > 0.0
    out[m] = near / z[m]
    return out


def project_depth_forward(w, near=NEAR, far=200.0):
    """The OTHER convention, kept only so the suite can measure what reversed-Z
    buys: standard D3D-style [0,1] forward depth, z = far(w-near)/(w(far-near)).
    Nothing in the pass uses it."""
    w = np.maximum(np.asarray(w, float), near)
    return np.float32(far * (w - near) / (w * (far - near)))


def unproject_depth_forward(z, near=NEAR, far=200.0):
    z = np.asarray(z, np.float32).astype(np.float64)
    den = far - z * (far - near)
    out = np.full(z.shape, np.inf)
    m = den > 0.0
    out[m] = far * near / den[m]
    return out


def depth_precision_m(w, near=NEAR, forward=False):
    """The metre size of one float32 step of the depth buffer at view depth w --
    an ABSOLUTE row, not a ratio. This is the quantity the chapter's trap is
    about: a water pass that reconstructs a position from a depth buffer inherits
    this as a position error, and on a shoaling bed a position error is a DEPTH
    error and therefore an optical-depth error."""
    w = np.asarray(w, float)
    if forward:
        z = project_depth_forward(w, near)
        z2 = np.nextafter(z, np.float32(1.0))
        return np.abs(unproject_depth_forward(z2, near) - w)
    z = project_depth(w, near)
    z2 = np.nextafter(z, np.float32(0.0))     # toward the far plane
    return np.abs(unproject_depth(z2, near) - w)


# ------------------------------------------------------- the opaque scene
def _aabb_hit(o, d, lo, hi):
    """Slab test. Returns t of the nearest entry, inf where missed."""
    t0 = np.full(d.shape[:-1], -np.inf)
    t1 = np.full(d.shape[:-1], np.inf)
    for k in range(3):
        dk = d[..., k]
        safe = np.where(np.abs(dk) < 1e-12, 1e-12, dk)
        a = (lo[k] - o[k]) / safe
        b = (hi[k] - o[k]) / safe
        t0 = np.maximum(t0, np.minimum(a, b))
        t1 = np.minimum(t1, np.maximum(a, b))
    ok = (t1 >= np.maximum(t0, 0.0))
    return np.where(ok & (t0 > 0.0), t0, np.inf)


def opaque_hit(dirs, eye=EYE):
    """Ray-cast the OPAQUE scene: deck, bed, post. This is the prepass, and the
    water pass never sees it -- the water pass sees only the buffers it writes.

    Returns (t, kind, normal) with kind 0 = miss (sky), 1 = deck, 2 = bed,
    3 = post. The bed is a piecewise plane and is solved in closed form on each
    piece rather than marched, which is the same discipline `render.py` applies
    to its own basin."""
    o = np.asarray(eye, float)
    dz, dx = dirs[..., 2], dirs[..., 0]
    inf = np.inf
    t = np.full(dirs.shape[:-1], inf)
    kind = np.zeros(dirs.shape[:-1], np.int8)
    nrm = np.zeros(dirs.shape)

    # -- deck: the plane z = DECK_Z restricted to x < DECK_X
    with np.errstate(divide='ignore', invalid='ignore'):
        td = (DECK_Z - o[2]) / dz
    hit = (dz < 0) & (td > 0) & ((o[0] + td * dx) < DECK_X)
    take = hit & (td < t)
    t = np.where(take, td, t)
    kind = np.where(take, 1, kind)

    # -- bed, piece 1: the ramp z = -SLOPE*x, valid 0 <= x <= D_MAX/SLOPE.
    #    o.z + t dz = -SLOPE (o.x + t dx)  =>  t (dz + SLOPE dx) = -SLOPE o.x - o.z
    den = dz + SLOPE * dx
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (-SLOPE * o[0] - o[2]) / den
    px = o[0] + t1 * dx
    h1 = (t1 > 0) & (px >= DECK_X) & (px <= D_MAX / SLOPE) & np.isfinite(t1)
    n1 = np.array([SLOPE, 0.0, 1.0]) / np.hypot(SLOPE, 1.0)

    # -- bed, piece 2: the flat shelf z = -D_MAX, valid x > D_MAX/SLOPE
    with np.errstate(divide='ignore', invalid='ignore'):
        t2 = (-D_MAX - o[2]) / dz
    px = o[0] + t2 * dx
    h2 = (t2 > 0) & (px > D_MAX / SLOPE) & np.isfinite(t2)

    for hh, tt, nn in ((h1, t1, n1), (h2, t2, np.array([0., 0., 1.]))):
        take = hh & (tt < t)
        t = np.where(take, tt, t)
        kind = np.where(take, 2, kind)
        nrm[take] = nn

    # -- post
    tp = _aabb_hit(o, dirs, POST[0], POST[1])
    take = np.isfinite(tp) & (tp < t)
    t = np.where(take, tp, t)
    kind = np.where(take, 3, kind)
    if take.any():
        p = o[None] + tp[take][:, None] * dirs[take]
        c = 0.5 * (POST[0] + POST[1])
        e = 0.5 * (POST[1] - POST[0])
        rel = (p - c[None]) / e[None]
        ax = np.argmax(np.abs(rel), axis=-1)
        n = np.zeros_like(p)
        n[np.arange(len(p)), ax] = np.sign(rel[np.arange(len(p)), ax])
        nrm[take] = n

    nrm[kind == 1] = np.array([0., 0., 1.])
    return t, kind, nrm


def project_to_pixel(P, res=RES, az=CAM_AZ, el=CAM_EL, fov=FOV, eye=EYE,
                     aspect=None):
    """World point -> (col, row) pixel coordinate and view depth. The inverse of
    `ray_dirs`, and the only thing a screen-space pass needs in order to re-sample
    a buffer somewhere other than at its own pixel -- which is what `12`'s
    "refraction from the scene-color copy" is. Points behind the camera come back
    with `ok=False` rather than wrapping round, which is the bug that version of
    this loop always has."""
    if aspect is None:
        aspect = res[0] / res[1]
    f, r, u = basis(az, el)
    v = np.asarray(P, float) - np.asarray(eye, float)[None]
    wf = v @ f
    ok = wf > 1e-6
    th = np.tan(0.5 * fov)
    with np.errstate(divide='ignore', invalid='ignore'):
        nx = (v @ r) / np.where(ok, wf, 1.0) / (th * aspect)
        ny = (v @ u) / np.where(ok, wf, 1.0) / th
    col = (nx + 1.0) * 0.5 * res[0] - 0.5
    row = (1.0 - ny) * 0.5 * res[1] - 0.5
    ok &= (col >= -0.5) & (col <= res[0] - 0.5)
    ok &= (row >= -0.5) & (row <= res[1] - 0.5)
    return col, row, wf, ok


def submerged_hit(org, dirs):
    """The FIRST submerged surface a ray starting at the water plane meets: bed
    or post. `org` (...,3) on or below the datum, `dirs` (...,3) pointing down.

    Only `offline.py` uses this, and that is the point of it living here rather
    than in the pass: a screen-space pass has no scene, so a screen-space pass
    may not call it. Returns (t, z_hit, albedo, is_post)."""
    o, d = np.asarray(org, float), np.asarray(dirs, float)
    dz, dx = d[..., 2], d[..., 0]
    inf = np.inf
    t = np.full(d.shape[:-1], inf)
    ispost = np.zeros(d.shape[:-1], bool)

    den = dz + SLOPE * dx
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (-SLOPE * o[..., 0] - o[..., 2]) / den
    px = o[..., 0] + t1 * dx
    h1 = (t1 > 0) & (px >= DECK_X) & (px <= D_MAX / SLOPE) & np.isfinite(t1)
    with np.errstate(divide='ignore', invalid='ignore'):
        t2 = (-D_MAX - o[..., 2]) / dz
    px = o[..., 0] + t2 * dx
    h2 = (t2 > 0) & (px > D_MAX / SLOPE) & np.isfinite(t2)
    for hh, tt in ((h1, t1), (h2, t2)):
        take = hh & (tt < t)
        t = np.where(take, tt, t)

    # the post, as a slab test with a per-ray origin
    t0 = np.full(d.shape[:-1], -inf)
    t1b = np.full(d.shape[:-1], inf)
    for k in range(3):
        dk = np.where(np.abs(d[..., k]) < 1e-12, 1e-12, d[..., k])
        a = (POST[0][k] - o[..., k]) / dk
        b = (POST[1][k] - o[..., k]) / dk
        t0 = np.maximum(t0, np.minimum(a, b))
        t1b = np.minimum(t1b, np.maximum(a, b))
    tp = np.where((t1b >= np.maximum(t0, 0.0)) & (t0 > 1e-9), t0, inf)
    take = tp < t
    t = np.where(take, tp, t)
    ispost |= take

    z = o[..., 2] + t * dz
    alb = np.where(ispost[..., None], RHO_POST[None], RHO_BED[None])
    return t, z, alb, ispost


def opaque_shade(pos, kind, nrm):
    """Scene-linear radiance of the opaque surfaces, as the prepass writes it:
    Lambertian, sun beam plus the sky irradiance integrated against the normal.
    NO TONE MAP -- every buffer in this directory is scene-linear and every
    measurement is taken here, before `encode`. Reading a PNG for physics cost
    this project a false finding once and it will not be repeated.

    The submerged bed is shaded WITHOUT the water in the way, which is what an
    engine's opaque pass does and is exactly the contract the water pass then
    completes: the pass owns the column, the prepass owns the surface."""
    sh = pos.shape[:-1]
    # `atmosphere.env_irradiance` takes ONE normal (it contracts the whole
    # environment against it), and this scene has six distinct normals in it --
    # so the gather runs once per DISTINCT normal and is exact, rather than
    # once per pixel and slow, or once per frame and wrong.
    flat = nrm.reshape(-1, 3)
    uniq, inv = np.unique(np.round(flat, 12), axis=0, return_inverse=True)
    tab = np.array([ATM.env_irradiance(*n) if np.dot(n, n) > 0.5 else np.zeros(3)
                    for n in uniq])
    E_sky = tab[inv].reshape(sh + (3,))
    ndl = np.clip(nrm @ ATM.SUN_DIR, 0.0, None)[..., None]
    alb = np.zeros(sh + (3,))
    alb[kind == 1] = RHO_DECK
    alb[kind == 2] = RHO_BED
    alb[kind == 3] = RHO_POST
    # `env_irradiance` already returns E/pi, and `SUN_COL` is already E_n/pi --
    # `atmosphere.py` says so where SKY_DECK is defined ("An illuminant for a
    # diffuse receiver is one number: E(N)/pi"). So the Lambertian exitance is
    # albedo times the SUM of the two illuminants and there is no second pi.
    L = alb * (ATM.SUN_COL[None] * ndl + E_sky)
    return L


def prepass(res=RES, jitter=None, az=CAM_AZ, el=CAM_EL, fov=FOV, eye=EYE):
    """The opaque G-buffer the water pass consumes: a reversed-Z depth buffer and
    a scene-colour copy. THESE TWO ARRAYS AND THE CAMERA ARE ALL THE PASS GETS --
    it never calls `opaque_hit`, which is the whole discipline of a screen-space
    pass and the reason its errors are the errors of a screen-space pass."""
    X, Y = pixel_ndc(res, jitter)
    dirs = ray_dirs(X, Y, az, el, fov, res[0] / res[1])
    t, kind, nrm = opaque_hit(dirs, eye)
    f, _, _ = basis(az, el)
    w = t * (dirs @ f)                        # view depth, not ray distance
    depth = np.where(np.isfinite(t), project_depth(w), np.float32(0.0))
    pos = np.asarray(eye)[None, None] + np.where(np.isfinite(t), t, 0.0)[..., None] * dirs
    col = opaque_shade(pos, kind, nrm)
    sky = ATM.sky(dirs[..., 0].ravel(), dirs[..., 1].ravel(),
                  dirs[..., 2].ravel()).reshape(res[1], res[0], 3)
    col = np.where((kind == 0)[..., None], sky, col)
    return {'depth': depth.astype(np.float32), 'color': col, 'dirs': dirs,
            'kind': kind, 'pos': pos, 't': t, 'nrm': nrm,
            'res': res, 'eye': np.asarray(eye, float), 'az': az, 'el': el,
            'fov': fov, 'jitter': jitter}
