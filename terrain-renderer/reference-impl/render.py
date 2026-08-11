"""
Swimming pool, 1.40 m deep -- physically-motivated render.

Chain (terrain-renderer/references/12-water-rendering.md):
  fetch-limited capillary-gravity wave field (no swell, no current)
   -> per-channel refraction of the sun; n_R != n_G != n_B  (dispersion)
   -> forward ray splat onto bed + 4 walls; folds emerge from ray density alone
   -> sun-disc penumbra blur, 0.53 deg compressed on entry by cos(ti)/(n cos(tt))
   -> sun visibility sampled AT THE SURFACE ENTRY POINT (shade sail), with penumbra
   -> Beer-Lambert over the light path, then again over the camera path
   -> liner albedo * transmittance   (b_b ~ 0: pool colour is the bottom, not scattering)
   -> Fresnel with F0 from per-channel IOR (0.0197, not the 0.04 dielectric default)

Nothing in the caustic pattern is authored: no texture, no Voronoi, no noise.
The chromatic fringing on the bed is emergent -- three IORs, three fold sets.
"""
import numpy as np
from PIL import Image

# --------------------------------------------------------------------------- config
DEPTH = 1.40   # the DEEPEST point only. Depth is a field -- bed_depth(x, y) --
               # and every optical path length is taken from it. What is left of
               # this constant is the floor of the containing box, the extent of
               # the wall maps, and the deepest-case numbers in the diagnostics.
X0, X1, Y0, Y1 = 0.0, 8.0, 0.0, 4.0
W, H = 2400, 3600          # rendered at SSx, averaged down: glints are rare
SS = 3                     # events, and the waterline is a high-contrast edge
                           # portrait: the frame runs from the coping at the
                           # photographer's feet to the far coping, all water
RAY_NX, RAY_NY = 8192, 4096          # 33.5 M forward rays per channel
CAU_NX, CAU_NY = 2666, 1333          # 3 mm bed texels
WNU, WNV = 1800, 340                 # wall caustic maps
SHADOW_N = (2200, 1100)

IOR = np.array([1.3320, 1.3348, 1.3400])     # 620 / 545 / 460 nm
ABS = np.array([0.2750, 0.0546, 0.0145])     # pure-water absorption, m^-1
F0 = ((IOR - 1.0) / (IOR + 1.0)) ** 2

# NOAA solar position, Aljezur 37.319N 8.803W, 2026-08-10 18:41 WEST:
#   elevation 21.02 deg, azimuth 273.75 deg (due west), air mass 2.77
SUN_DIR = np.array([-0.93141, 0.06104, 0.35878])   # +x east, +y north, +z up
SUN_DIR /= np.linalg.norm(SUN_DIR)
SUN_COL = np.array([1.000, 0.892, 0.674]) * 8.6   # golden: AM 2.77, not a noon sun
SKY_TOP = np.array([0.26, 0.46, 0.98])
SKY_HOR = np.array([0.86, 0.90, 0.98])
SKY_AMB = np.array([0.26, 0.42, 0.66]) * 2.15   # clear sky is still a big blue source
# ...but SKY_AMB is the sky the WATER sees: through the Snell window it is
# zenith-weighted, and the zenith is the blue part. A horizontal stone surface
# sees a cosine-weighted hemisphere instead, and at a 21 degree sun most of that
# hemisphere's energy is in the aureole and the horizon band around the sun,
# reddened by the same air mass 2.77 that makes SUN_COL golden. Feeding the
# water's blue ambient to the stone is what made the deck come out neutral grey
# in the previous frame: a warm albedo times a blue illuminant is grey.
SKY_DECK = SKY_AMB * 0.30 + SUN_COL * 0.075
SAIL_TAU = 0.30          # shade fabric transmits ~15-20%, DIFFUSELY:
                         # it lifts the shadow without making caustics

# --- camera -----------------------------------------------------------------
# The reference is a CLOSE-UP over the water: the frame is water, the pool edge
# is a border at the top, and there is no garden in it. Two constraints fix the
# viewpoint and neither is free:
#   * the specular path.  A facet reflects the sun to the camera when its normal
#     bisects L and V.  With the sun at 21 deg and the camera due east of the
#     target, |theta_v - 21| < 12 deg keeps the required slope inside the field's
#     rms (0.058 far, 0.123 over the jet) -- that is the ONLY band in which
#     spec C's isolated glints can exist.  Look down at 60 deg and there is no
#     sparkle anywhere, at any roughness.
#   * the caustic net.  25-40 cells at 15-30 cm needs 4-8 m of water in frame.
#   * the waterline has to be legible somewhere.  At the FAR coping it is four
#     pixels of stone; the only place a pool edge can be read is the one under
#     the photographer, so the bottom of the frame is put on it at 1.2 m.
# Phone at chest height on the east deck, a metre back from the edge, 34 deg
# down, portrait: bottom edge on the near coping (theta_v 57 deg), top edge on
# the far coping (9.5 m, theta_v 11 deg), 7.4 m of water in between, and the
# mirror direction for a 21 deg sun crossing it a fifth of the way down.
#
# The lateral position moved 0.40 m north this round, to the pool's own centre
# line. It is the only camera number that changed, and it is what puts the step
# unit -- now set into the north wall at mid-length rather than 8 m away in the
# far corner -- inside the 15.8 deg half-width of the frame. The sail moved with
# it, by the same 0.70 m, so that its shadow EDGE stays in frame: the shadow gate
# is a claim under test and it has to be visible to be judged.
EYE = np.array([9.40, 1.95, 1.85])    # east: the anti-solar side
CAM_AZ = np.deg2rad(176.6)            # anti-solar to 0.4 deg: see above
CAM_EL = np.deg2rad(-33.35)
FOV = np.deg2rad(46.0)
TGT = EYE + 7.0 * np.array([np.cos(CAM_AZ) * np.cos(CAM_EL),
                            np.sin(CAM_AZ) * np.cos(CAM_EL), np.sin(CAM_EL)])
SAIL = np.array([[-5.10, -0.20, 2.72], [-2.10, 0.20, 2.55],
                 [-2.40, 2.60, 2.35], [-5.40, 2.20, 2.55]])
EXPOSURE = 0.275      # the camera exposes for a 21-degree sun

# --- the pool edge, in section ----------------------------------------------
# Not a boolean rectangle.  A poured wall, a coping course bedded on it that
# OVERHANGS the wall face, and a bullnose rolled over that overhang.  Every
# number here is a dimension off a real coping stone, and each one does visible
# work: the overhang makes the undercut the water sits in, the bullnose makes
# the roll that catches or loses the sun depending on which side of the pool it
# is, and the 75 mm freeboard makes the reflection of the coping in the water.
ZD   =  0.075     # coping top, 75 mm above the still waterline (the freeboard)
ZG   = -0.030     # lawn, if it ever gets in frame -- it does not
BULR =  0.032     # bullnose radius
SLIP = -0.020     # the coping overhangs the wall face by 20 mm, into the pool
SBUL = SLIP + BULR
ZCEN = ZD - BULR  # centre of the bullnose arc, in (s, z)
ZLIP = ZCEN       # the lip: lowest point of the bullnose, 43 mm over the water
COPW =  0.34      # width of the coping course
WET  =  0.210     # how far back from the lip the stone is still splash-damp
# A real pool liner is BLUE, not white plaster. Absolute albedo ~ (0.24, 0.54, 0.70):
# reflective enough to stay bright, saturated enough to carry the colour itself.
LINER_TINT = np.array([0.30, 0.79, 0.92])

rng = np.random.default_rng(20260810)

# --------------------------------------------------------------------------- the plan
# ONE function owns the shape of the water in plan, and one owns the shape of
# the bed. Everything downstream -- the coping trace, the lip occluder, the wall
# shading, the meniscus, the caustic pass, the Beer-Lambert path -- consumes
# them rather than re-deriving the rectangle. Swapping a kidney-shaped boundary
# or a sloping shelf in is then a change to these two functions and nothing else.
#
# pool_sdf is the MITRED (max-norm) distance for the box instance, not the true
# Euclidean one: a coping course is laid with a mitre joint at the corner, so the
# max norm is the right metric for where the stones are, and the bullnose sweeps
# round the mitre exactly as a laid one does. The mitred form is still convex,
# which is what the camera-side edge march exploits below -- see POOL_CONVEX.
POOL_CONVEX = True          # true for the box; a kidney with a concave lobe is not


def pool_sdf(x, y):
    """Signed outward distance from the water's plan boundary; <0 inside."""
    return np.maximum(np.abs(x - .5 * (X0 + X1)) - .5 * (X1 - X0),
                      np.abs(y - .5 * (Y0 + Y1)) - .5 * (Y1 - Y0))


def pool_sdf_grad(x, y):
    """Outward unit gradient of pool_sdf, plus a flag saying which axis carries
    it (the coping course runs ALONG the boundary, so the caller needs to know)."""
    a = np.abs(x - .5 * (X0 + X1)) - .5 * (X1 - X0)
    b = np.abs(y - .5 * (Y0 + Y1)) - .5 * (Y1 - Y0)
    e = a >= b
    return (np.where(e, np.sign(x - .5 * (X0 + X1)), 0.),
            np.where(e, 0., np.sign(y - .5 * (Y0 + Y1))), e)


# --- the bed, as a field ------------------------------------------------------
# A RADIUS ENTRY STEP -- the "wedding cake" unit every vinyl-liner pool has --
# set into the north wall at mid-length, plus a bench lobe further west. Both are
# part of the LINER SHELL: same vinyl, same colour, continuous over the form.
# They are not a stone insert, and they are not decoration: they are the only
# straight-ish edges in the basin, and a circular nosing is the specific shape
# that a decorative wobble cannot fake. A wobbling straight line is a line with
# noise on it; a circular arc seen through a wavy interface stays a coherent arc
# whose local tangent swings, and only a real refracted view ray does that.
#
# Dimensions are a standard unit: tread 300 mm, riser 240/255 mm, three treads,
# 3.0 m along the wall and 1.5 m out into the water. The last drop to the floor
# is 700 mm -- that is what a three-tread unit in a 1.40 m basin actually does;
# you sit on it.
#
# WHERE IT SITS. Two constraints, and the previous placement satisfied only one.
#  * THE SUN, which is not a composition choice.  The refracted sun travels EAST
#    under water at 44.4 deg from vertical, so a tread that steps down toward the
#    east lies in its own nosing's shadow: 235 mm of a 300 mm tread. A flight
#    whose descent sweeps through east is 80% self-shadowed and shows no caustic
#    at all. Both of the west-wall corners descend eastward over half their
#    sweep. A unit centred on a side wall sweeps its descent through the whole
#    half-circle, so the self-shadow runs from 235 mm at the east end to 16 mm at
#    the south point -- a gradient that falls out of the geometry, and every
#    tread that faces the camera keeps a lit outer strip.
#  * THE FRAME, which the last placement lost.  At 7.5-9 m the flight is seen at
#    theta_v 11-14 deg: the treads foreshorten to 24% of their width, the whole
#    unit is 130 px of a 1200 px frame, the 12.9 mm nosing wobble projects to
#    0.6 px, and Fresnel on the surface above it is 0.25-0.36, which puts a
#    near-neutral sky reflection over everything the unit was built to show.
#    A 90 deg CORNER unit cannot be brought closer: from a viewpoint near its own
#    corner a 2.2 m quarter-arc subtends 40-60 deg of azimuth and leaves the
#    31.6 deg frame. A half-circle centred on the wall does not have that
#    problem -- its bulge points at the camera and its ends recede -- so at
#    x = 6.0 the outer nosing comes to 3.4 m, theta_v 28 deg, Fresnel 0.05, and
#    the arcs sweep 90 deg of frame instead of 15.
# The unit sits east of the mirror band (theta_v 21 deg, at 4.8 m) rather than
# under it, so the sun glitter road crosses OPEN water beyond the steps.
STEP_C = np.array([6.00, Y1])                     # the arcs are centred ON the wall
STEP_R = np.array([0.90, 1.20, 1.50])             # nosing radii, 300 mm treads
STEP_Z = np.array([-0.205, -0.445, -0.700])       # tread levels below still water
BENCH_C = np.array([3.00, 4.35])                  # the bench lobe: a disc cut by
BENCH_R = 0.85                                    # the north wall, so its leading
BENCH_Z = -0.445                                  # edge is an arc, at tread-2 level
NOSE_R = 0.025          # ? nosings are eased, not arrised -- 25 mm reads as the
                        # ? shading round-over only; it is under a pixel of silhouette


def bed_z(x, y):
    """Height of the bed under (x, y). The floor, the corner step, the bench."""
    r = np.sqrt((x - STEP_C[0]) ** 2 + (y - STEP_C[1]) ** 2)
    z = np.where(r <= STEP_R[0], STEP_Z[0],
                 np.where(r <= STEP_R[1], STEP_Z[1],
                          np.where(r <= STEP_R[2], STEP_Z[2], -DEPTH)))
    rb = np.sqrt((x - BENCH_C[0]) ** 2 + (y - BENCH_C[1]) ** 2)
    return np.where(rb <= BENCH_R, np.maximum(z, BENCH_Z), z)


def bed_depth(x, y):
    """Water depth over the bed at (x, y). DEPTH is now only the deepest point."""
    return -bed_z(x, y)


# The bed as a union of vertical cylinders {r <= R, z <= ztop}, which is exactly
# the staircase above: the union's upper surface is the deepest ztop whose disc
# contains the point. Analytic, so the caustic pass pays four quadratics and no
# march. (cx, cy, R, ztop)
CYL = [(STEP_C[0], STEP_C[1], STEP_R[0], STEP_Z[0]),
       (STEP_C[0], STEP_C[1], STEP_R[1], STEP_Z[1]),
       (STEP_C[0], STEP_C[1], STEP_R[2], STEP_Z[2]),
       (BENCH_C[0], BENCH_C[1], BENCH_R, BENCH_Z)]
# Bounding box of everything that is not the flat floor, in PLAN, so a ray whose
# whole horizontal run misses it can skip the cylinder tests entirely.
STEP_BB = (min(STEP_C[0] - STEP_R[2], BENCH_C[0] - BENCH_R),
           max(STEP_C[0] + STEP_R[2], BENCH_C[0] + BENCH_R),
           min(STEP_C[1] - STEP_R[2], BENCH_C[1] - BENCH_R),
           max(STEP_C[1] + STEP_R[2], BENCH_C[1] + BENCH_R))

# --------------------------------------------------------------------------- wave field
# Four bands. The structure is the room-acoustics one: EARLY reflections explicit
# and coherent, LATE reverberation statistical -- because after several bounces a
# basin field is diffuse, and a random-phase spectrum IS its correct description.
#   A  wind          short, incoherent, uniform, killed in the lee
#   B1 jet near      direct + first-order wall images: coherent arcs near the inlet
#   B2 reverb tail   the diffuse late field: random phase, near-ISOTROPIC directions
#                    (a reverberant basin has no preferred direction; a wind sea does)
#   C  jet boil      short waves at the outlet, e-folding ~2 m -> the local rough patch
NU = 1.004e-6

from field import (X0, X1, Y0, Y1, JET_XY, grad_grid, grad_points,
                   normal_from_grad, jet_envelope, shelter, _norm_jets)

def refract(ix, iy, iz, nx, ny, nz, eta):
    cosi = -(ix * nx + iy * ny + iz * nz)
    k = np.maximum(1.0 - eta * eta * (1.0 - cosi * cosi), 0.0)
    f = eta * cosi - np.sqrt(k)
    return eta * ix + f * nx, eta * iy + f * ny, eta * iz + f * nz


BIG = np.float32(1e9)


def _cyl_entry(px, py, tx, ty, tz, pz=0.0):
    """Entry point of a downgoing ray into the UNION of the bed cylinders.
    Returns (t, is_riser, which). The union's first entry is the minimum of the
    per-solid entries, so no CSG walk is needed -- only four quadratics.
    `pz` is the ray's starting height; 0 (the still surface) for every caustic
    and camera ray, negative for the inter-reflection gather, which starts on a
    riser. It used to be hard-coded to 0 in the two places z enters."""
    n = px.shape
    bt = np.full(n, BIG); bf = np.zeros(n, bool); bi = np.full(n, -1, np.int8)
    a = tx * tx + ty * ty
    vert = a <= 1e-14
    inva = 1.0 / np.where(vert, 1.0, a)
    down = tz < -1e-9                             # z(t) <= ztop  <=>  t >= ztop/tz
    tzd = np.minimum(tz, -1e-9)
    for i, (cx, cy, R, ztop) in enumerate(CYL):
        ox, oy = px - cx, py - cy
        b = 2.0 * (ox * tx + oy * ty)
        c = ox * ox + oy * oy - R * R
        disc = b * b - 4.0 * a * c
        hit = (disc > 0.0) & ~vert
        sq = np.sqrt(np.where(hit, disc, 0.0))
        t1 = np.where(hit, (-b - sq) * 0.5 * inva, BIG)
        t2 = np.where(hit, (-b + sq) * 0.5 * inva, -BIG)
        t1 = np.where(vert, np.where(c < 0.0, -BIG, BIG), t1)
        t2 = np.where(vert, np.where(c < 0.0, BIG, -BIG), t2)
        tc = np.where(down, (ztop - pz) / tzd, BIG)
        tin = np.maximum(t1, tc)
        ok = (tin < t2) & (tin > 1e-6) & (tin < bt)
        bt = np.where(ok, tin, bt)
        bf = np.where(ok, t1 > tc, bf)            # entered through the round face
        bi = np.where(ok, i, bi)
    return bt, bf, bi


def scene_hit(px, py, tx, ty, tz, pz=0.0):
    """First hit of a downgoing ray in the pool, starting at height `pz`
    (0 = the still surface, which is where every caustic and camera ray starts).
    Surface ids:
         0 = a horizontal bed face -- floor, tread or bench top; (u,v) = (x,y)
         1..4 = the walls x0, x1, y0, y1;                        (u,v) = (along,z)
         5 = a cylindrical riser of the step unit;               (u,v) = (x,y)
    `cyl` says which cylinder a riser hit belongs to, so the caller can get the
    outward normal without a second intersection."""
    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.stack([
            np.where(tz < -1e-9, (-DEPTH - pz) / tz, BIG),
            np.where(tx < -1e-9, (X0 - px) / tx, BIG),
            np.where(tx > 1e-9, (X1 - px) / tx, BIG),
            np.where(ty < -1e-9, (Y0 - py) / ty, BIG),
            np.where(ty > 1e-9, (Y1 - py) / ty, BIG)])
    s = np.where(np.isfinite(s), s, BIG)
    sid = np.argmin(s, 0).astype(np.int8)
    sm = np.take_along_axis(s, sid[None].astype(np.intp), 0)[0]
    cyl = np.full(px.shape, -1, np.int8)

    # Prune: a ray can only meet the step unit if its horizontal run crosses the
    # unit's plan bounding box. Everything else keeps the flat-floor fast path.
    L = np.minimum(sm, (DEPTH + pz) / np.maximum(-tz, 1e-9))
    ax, bx2 = px, px + tx * L
    ay, by2 = py, py + ty * L
    near = ((np.minimum(ax, bx2) <= STEP_BB[1]) & (np.maximum(ax, bx2) >= STEP_BB[0]) &
            (np.minimum(ay, by2) <= STEP_BB[3]) & (np.maximum(ay, by2) >= STEP_BB[2]))
    idx = np.flatnonzero(near)
    if idx.size:
        pzi = pz if np.ndim(pz) == 0 else pz[idx]
        ct, cf, ci = _cyl_entry(px[idx], py[idx], tx[idx], ty[idx], tz[idx], pzi)
        take = ct < sm[idx]
        j = idx[take]
        sm[j] = ct[take]
        sid[j] = np.where(cf[take], 5, 0).astype(np.int8)
        cyl[j] = ci[take]

    hx, hy, hz = px + tx * sm, py + ty * sm, pz + tz * sm
    u = np.where((sid == 0) | (sid == 5), hx, np.where(sid <= 2, hy, hx))
    v = np.where((sid == 0) | (sid == 5), hy, hz)
    return sid, u, v, sm, cyl


def box_hit(px, py, tx, ty, tz):
    """Backwards-compatible view of scene_hit for callers that do not care which
    cylinder was hit."""
    sid, u, v, sm, _ = scene_hit(px, py, tx, ty, tz)
    return sid, u, v, sm


def splat(acc, u, v, w, u0, u1, v0, v1):
    nv, nu = acc.shape
    fu = (u - u0) / (u1 - u0) * nu - 0.5
    fv = (v - v0) / (v1 - v0) * nv - 0.5
    iu, iv = np.floor(fu).astype(np.int64), np.floor(fv).astype(np.int64)
    du, dv = fu - iu, fv - iv
    flat = acc.ravel()
    for ou, wu in ((0, 1 - du), (1, du)):
        for ov, wv in ((0, 1 - dv), (1, dv)):
            cu, cv = iu + ou, iv + ov
            ok = (cu >= 0) & (cu < nu) & (cv >= 0) & (cv < nv)
            if ok.any():
                flat += np.bincount(cv[ok] * nu + cu[ok],
                                    weights=(w * wu * wv)[ok], minlength=nu * nv)


def sample(img, u, v, u0, u1, v0, v1):
    nv, nu = img.shape[:2]
    fu = np.clip((u - u0) / (u1 - u0) * nu - .5, 0, nu - 1.001)
    fv = np.clip((v - v0) / (v1 - v0) * nv - .5, 0, nv - 1.001)
    iu, iv = fu.astype(np.int64), fv.astype(np.int64)
    du, dv = (fu - iu)[:, None], (fv - iv)[:, None]
    return ((img[iv, iu] * (1 - du) + img[iv, iu + 1] * du) * (1 - dv) +
            (img[iv + 1, iu] * (1 - du) + img[iv + 1, iu + 1] * du) * dv)


def blur(img, sig):
    if sig < 0.35:
        return img
    r = int(np.ceil(3 * sig))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2); k /= k.sum()
    o = img
    for ax in (0, 1):
        pad = [(0, 0), (0, 0)]; pad[ax] = (r, r)
        p = np.pad(o, pad, mode='edge')
        o = np.apply_along_axis(lambda m: np.convolve(m, k, 'valid'), ax, p)
    return o


# --------------------------------------------------------------------------- shade sail
# The sail is here as an OCCLUDER and nothing else -- the shadow gate is the
# claim under test (no caustics inside it, water still luminous), and its EDGE
# is what lands in frame.  A tensioned sail is not a flat quad, so its shadow
# edge is not a straight line: the fabric hangs in a catenary between the four
# anchors and each edge is cut in a concave scallop so it can be tensioned at
# all.  Both change the shadow's outline, so both are in the projection.  The
# sail is not otherwise drawn: it sits above the top of the frame.
SAIL_SAG = 0.24        # mid-panel droop below the bilinear surface, m
SAIL_SCAL = 0.085      # edge scallop, as a fraction of the span


def sail_surface(u, v):
    """Point on the fabric. Bilinear between the four anchors, less a catenary
    droop that vanishes at every edge (the edges are the tensioned ones)."""
    w = ((1 - u) * (1 - v))[..., None], (u * (1 - v))[..., None], \
        (u * v)[..., None], ((1 - u) * v)[..., None]
    p = w[0] * SAIL[0] + w[1] * SAIL[1] + w[2] * SAIL[2] + w[3] * SAIL[3]
    cu, cv = np.clip(u, 0, 1), np.clip(v, 0, 1)
    return p - np.stack([np.zeros_like(u), np.zeros_like(u),
                         SAIL_SAG * np.sin(np.pi * cu) * np.sin(np.pi * cv)], -1)


def sail_inside(u, v):
    c, s = SAIL_SCAL, np.sin
    return ((v > c * s(np.pi * u)) & (v < 1 - c * s(np.pi * u)) &
            (u > c * s(np.pi * v)) & (u < 1 - c * s(np.pi * v)))


# Project the fabric to z = 0 along the sun and accumulate coverage. Sampling
# (u, v) and normalising by the sample density is exact for any warped surface,
# which a polygon projection is not once the panel sags.
SX = np.linspace(X0 - 3, X1 + 3, SHADOW_N[0])
SY = np.linspace(Y0 - 3, Y1 + 3, SHADOW_N[1])
_cov = np.zeros((SHADOW_N[1], SHADOW_N[0]))
_den = np.zeros((SHADOW_N[1], SHADOW_N[0]))
_NUV = 2400
_uu = np.linspace(-0.18, 1.18, _NUV)
for _j0 in range(0, _NUV, 200):
    _U, _V = np.meshgrid(_uu, _uu[_j0:_j0 + 200])
    _P = sail_surface(_U.ravel(), _V.ravel())
    _g = _P[:, :2] - SUN_DIR[None, :2] * (_P[:, 2:3] / SUN_DIR[2])
    _m = sail_inside(_U.ravel(), _V.ravel()).astype(np.float64)
    splat(_cov, _g[:, 0], _g[:, 1], _m, SX[0], SX[-1], SY[0], SY[-1])
    splat(_den, _g[:, 0], _g[:, 1], np.ones_like(_m), SX[0], SX[-1], SY[0], SY[-1])
SHADOW = 1.0 - _cov / np.maximum(_den, 1e-9)
del _cov, _den

# soft shadow: penumbra = 0.53 deg over the sail's slant height above the water
_pen = np.deg2rad(0.53) * (SAIL[:, 2].mean() / SUN_DIR[2])
SHADOW = np.clip(blur(SHADOW, (_pen / 4.0) / ((SX[-1] - SX[0]) / SHADOW_N[0])), 0, 1)
print("sail penumbra at the water: %.0f mm" % (_pen * 1000))
print("sail shadow covers %.1f m2 of the basin" %
      ((1 - SHADOW).sum() * ((SX[-1] - SX[0]) / SHADOW_N[0]) *
       ((SY[-1] - SY[0]) / SHADOW_N[1])))


# The coping overhangs the wall, so along the WEST wall the sun never reaches the
# surface at all: it has to climb ZLIP = 43 mm to clear the lip and it only gains
# 0.385 m per metre run, so a band of water against that wall is in shadow. The
# refracted ray from the first LIT surface then travels 1.37 m east, so what you
# see on the bed is not a dark strip against the wall but a dark strip out in the
# basin. The same test on the NORTH wall gives 7 mm: the sun is 3.75 deg north of
# due west, so it is climbing almost parallel to that wall.
#
# Written against pool_sdf, not against X0/Y1: walk from the water point toward
# the sun's azimuth until the SDF reaches the lip value SLIP. The SDF changes at
# rate (shat . grad s) along that walk, so the run to the lip is
# (SLIP - s)/(shat . grad s) -- which is why the same 43 mm of freeboard costs
# 112 mm on the wall the sun faces and 7 mm on the wall it runs along. A curved
# boundary needs no new code here; only grad s changes.
_SHAT = SUN_DIR[:2] / np.linalg.norm(SUN_DIR[:2])   # horizontal, toward the sun
_LRUN = ZLIP * np.linalg.norm(SUN_DIR[:2]) / SUN_DIR[2]   # run needed to clear it
_LPEN = np.deg2rad(0.53) * (ZLIP / SUN_DIR[2])      # sun disc over that run


def _lip_run(x, y):
    """Horizontal run from (x,y) to the lip, along the sun's azimuth."""
    gx, gy, _ = pool_sdf_grad(x, y)
    adv = gx * _SHAT[0] + gy * _SHAT[1]             # d(sdf)/d(run) toward the sun
    return np.where(adv > 1e-6, (SLIP - pool_sdf(x, y)) / np.maximum(adv, 1e-6), BIG)


# The shaded band on a wall is the run projected back onto that wall's normal.
print("coping lip shades %.0f mm of water off the west wall, %.0f mm off the "
      "north wall (penumbra %.1f mm)"
      % (_LRUN * abs(_SHAT[0]) * 1000, _LRUN * abs(_SHAT[1]) * 1000, _LPEN * 1000))


def coping_vis(x, y):
    """Sun visibility at the water surface, cut by the coping lip itself. Lit
    where the run to the lip exceeds the run needed to clear its 43 mm."""
    return np.clip((_lip_run(x, y) - _LRUN) / _LPEN + .5, 0, 1)


def sun_vis(x, y):
    fu = np.clip((x - SX[0]) / (SX[-1] - SX[0]) * SHADOW_N[0] - .5, 0, SHADOW_N[0] - 1.001)
    fv = np.clip((y - SY[0]) / (SY[-1] - SY[0]) * SHADOW_N[1] - .5, 0, SHADOW_N[1] - 1.001)
    iu, iv = fu.astype(np.int64), fv.astype(np.int64)
    du, dv = fu - iu, fv - iv
    s = ((SHADOW[iv, iu] * (1 - du) + SHADOW[iv, iu + 1] * du) * (1 - dv) +
         (SHADOW[iv + 1, iu] * (1 - du) + SHADOW[iv + 1, iu + 1] * du) * dv)
    return s * coping_vis(x, y)


# --------------------------------------------------------------------------- caustic pass
_norm_jets()
print("caustic pass: %.1f M rays x 4 sets" % (RAY_NX * RAY_NY / 1e6))
bed = [np.zeros((CAU_NY, CAU_NX)) for _ in range(4)]        # 0,1,2 = RGB ; 3 = mono
wall = [[np.zeros((WNV, WNU)) for _ in range(4)] for _ in range(4)]
IOR_SET = [IOR[0], IOR[1], IOR[2], IOR[1]]

rx = (np.arange(RAY_NX) + 0.5) / RAY_NX * (X1 - X0) + X0
ry = (np.arange(RAY_NY) + 0.5) / RAY_NY * (Y1 - Y0) + Y0
cell = ((X1 - X0) / RAY_NX) * ((Y1 - Y0) / RAY_NY)
CH = 256
for j0 in range(0, RAY_NY, CH):
    yy = ry[j0:j0 + CH]
    gx, gy = grad_grid(rx, yy)
    XX = np.broadcast_to(rx[None, :], gx.shape).ravel().astype(np.float32)
    YY = np.broadcast_to(yy[:, None], gx.shape).ravel().astype(np.float32)
    nx, ny, nz = normal_from_grad(gx.ravel(), gy.ravel())
    wgt = (sun_vis(XX, YY) * cell).astype(np.float64)
    live = wgt > 1e-4 * cell
    XXl, YYl = XX[live], YY[live]
    nxl, nyl, nzl, wl = nx[live], ny[live], nz[live], wgt[live]
    for c in range(4):
        tx, ty, tz = refract(np.float32(-SUN_DIR[0]), np.float32(-SUN_DIR[1]),
                             np.float32(-SUN_DIR[2]), nxl, nyl, nzl,
                             np.float32(1.0 / IOR_SET[c]))
        sid, u, v, _ = box_hit(XXl, YYl, tx, ty, tz)
        # sid 0 is EVERY horizontal receiver -- floor, tread, bench top -- and
        # (u, v) is (x, y) for all of them, so one map carries the whole bed.
        # The depth each texel focuses over is bed_depth(x, y), and the rays got
        # there by being traced to it: nothing here assumes 1.40 m.
        # sid 5 is a riser. Those rays are DROPPED, which is exactly the step
        # unit's cast shadow on the floor east of it -- the light stopped there.
        m = sid == 0
        if m.any():
            splat(bed[c], u[m], v[m], wl[m], X0, X1, Y0, Y1)
        for wi, sv in enumerate((1, 2, 3, 4)):
            m = sid == sv
            if m.any():
                a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
                splat(wall[wi][c], u[m], v[m], wl[m], a, b, -DEPTH, 0.0)
    if (j0 // CH) % 4 == 0:
        print("  rows %d/%d" % (j0, RAY_NY), flush=True)

bt = ((X1 - X0) / CAU_NX) * ((Y1 - Y0) / CAU_NY)
wt = [((Y1 - Y0) / WNU) * (DEPTH / WNV)] * 2 + [((X1 - X0) / WNU) * (DEPTH / WNV)] * 2
for c in range(4):
    bed[c] /= bt
    for wi in range(4):
        wall[wi][c] /= wt[wi]

cos_i = SUN_DIR[2]
sin_t = np.sqrt(1 - cos_i ** 2) / IOR[1]
cos_t = np.sqrt(1 - sin_t ** 2)
slant = DEPTH / cos_t
TSUN = 1.0 - (F0[1] + (1 - F0[1]) * (1 - cos_i) ** 5)   # 13% reflects at 69 deg incidence
print('sun elev %.1f deg -> refracted %.1f deg, offset %.2f m, slant %.2f m, T %.3f'
      % (np.degrees(np.arcsin(cos_i)), np.degrees(np.arccos(cos_t)),
         DEPTH * np.tan(np.arccos(cos_t)), slant, TSUN))
pen = np.deg2rad(0.53) * (cos_i / (IOR[1] * cos_t)) * slant
print("sun-disc penumbra on the bed at %.2f m: %.1f mm" % (DEPTH, pen * 1000))


# The caustic map is a DENSITY ESTIMATE, so its kernel has to satisfy two things
# at once: the physical sun-disc penumbra, and the bandwidth below which the
# estimator's own shot noise beats the signal. At 33.6 M rays over 32 m2 a 3 mm
# texel holds ~9 rays, so a bare texel is 33% noise. The two add in quadrature.
# This replaces a flat "1.45x physical" multiplier that used to hide the second
# term inside the first -- and hiding it there is exactly what breaks when the
# receiver is 205 mm down instead of 1.40 m, because the physical part collapses
# by 7x and the estimator's does not. SIG_EST is set to leave the 1.40 m bed
# kernel unchanged, so this is a re-derivation and not a re-tune.
SIG_EST = 0.0018        # ? density-estimator bandwidth, m: ~0.6 of a bed texel


def sig_at(d):
    """Kernel sigma for the caustic map at receiver depth d."""
    pen = np.deg2rad(0.53) * (cos_i / (IOR[1] * cos_t)) * (d / cos_t)
    return np.sqrt((pen / 4.0) ** 2 + SIG_EST ** 2)


# The penumbra is proportional to the depth it fell through, so a single blur is
# a depth bug: it would smear a 0.205 m tread with a 1.40 m disc and flatten the
# very thing the step flight exists to show. bed_depth is piecewise constant, so
# blurring per level and selecting is exact rather than approximate.
BU, BV = np.meshgrid(np.linspace(X0, X1, CAU_NX), np.linspace(Y0, Y1, CAU_NY))
BDEP = bed_depth(BU, BV)
DLEV = np.unique(np.round(BDEP, 6))
_dx = (X1 - X0) / CAU_NX
print("bed depths present: " + ", ".join(
    "%.3f m (%.0f%% of area, penumbra %.1f mm, kernel %.1f mm)"
    % (d, 100. * (BDEP == d).mean(),
       np.deg2rad(0.53) * (cos_i / (IOR[1] * cos_t)) * (d / cos_t) * 1000,
       sig_at(d) * 1000) for d in DLEV))
for c in range(4):
    raw = bed[c]
    out = blur(raw, sig_at(DEPTH) / _dx)
    if out is raw:
        out = raw.copy()
    for d in DLEV:
        if abs(d - DEPTH) < 1e-9:
            continue
        m = BDEP == d
        rr = np.flatnonzero(m.any(1)); cc = np.flatnonzero(m.any(0))
        pad = int(np.ceil(3 * sig_at(DEPTH) / _dx)) + 2
        r0, r1 = max(rr[0] - pad, 0), min(rr[-1] + pad + 1, CAU_NY)
        c0, c1 = max(cc[0] - pad, 0), min(cc[-1] + pad + 1, CAU_NX)
        sub = blur(raw[r0:r1, c0:c1], sig_at(d) / _dx)
        out[r0:r1, c0:c1] = np.where(m[r0:r1, c0:c1], sub, out[r0:r1, c0:c1])
    bed[c] = out
    # ? A wall texel at height z was lit through |z| of water, so its penumbra
    # ? runs from 0 at the waterline to the full 6.8 mm at the foot. The wall
    # ? maps are blurred at the mid-wall value instead of per row: the walls are
    # ? at most a few pixels tall in this frame and the shading below already
    # ? takes their Beer-Lambert path from |z| rather than from DEPTH.
    for wi in range(4):
        wall[wi][c] = blur(wall[wi][c], sig_at(0.5 * DEPTH) / ((Y1 - Y0) / WNU))
print("bed caustic: mean %.2f  p99 %.2f  max %.2f" %
      (bed[1].mean(), np.percentile(bed[1], 99), bed[1].max()))


# --- is the net actually depth-graded?  Measure it, do not assert it. ---------
# Cell SIZE, which is what the bar asks for, is twice the lag of the first zero
# crossing of the radially averaged autocorrelation: one bright line to the next
# dark centre and back. (Falling to 1/e instead measures the WIDTH of a bright
# line, which is a different and much smaller number -- worth saying, because
# reading the wrong one off an autocorrelogram is an easy way to declare a pass.)
def cell_size(x0, x1, y0, y1, arr=None):
    a = bed[3] if arr is None else arr
    i0, i1 = int(x0 / (X1 - X0) * CAU_NX), int(x1 / (X1 - X0) * CAU_NX)
    j0, j1 = int(y0 / (Y1 - Y0) * CAU_NY), int(y1 / (Y1 - Y0) * CAU_NY)
    p = a[j0:j1, i0:i1]
    if p.size < 4096 or p.std() < 1e-9:
        return float('nan')
    p = p - p.mean()
    F = np.fft.rfft2(p)
    ac = np.fft.irfft2(F * np.conj(F), s=p.shape)
    ac = ac / ac[0, 0]
    # Each axis is read out to ITS OWN reach and only the axes that actually
    # cross zero within it are averaged. A tread is an annulus 300 mm wide and
    # metres long, so a single lag limit taken from the short axis reports the
    # limit -- 114 mm, suspiciously close to twice a third of the patch -- and
    # calls it a cell size. Returning nan when nothing crosses is the honest
    # answer for a patch too small to hold a cell.
    est = [2.0 * np.flatnonzero(c < 0.0)[0] * _dx
           for c in (ac[:min(ac.shape[0] // 3, 200), 0],
                     ac[0, :min(ac.shape[1] // 3, 200)])
           if np.any(c < 0.0)]
    return float(np.mean(est)) if est else float('nan')

# Upwelling radiance of the lit water: liner albedo, lit through the whole light
# path and looked at through a whole depth of water. The pool is a large, bright,
# strongly coloured UPWARD source and the stone at its edge is lit by it. Without
# this term the coping's bullnose -- which faces the water and therefore faces
# away from a western sun -- comes out black, and a 3 cm black line compressed
# into two pixels at the far coping is speckle, not a shadow line. With it, it is
# the dim teal line a real pool edge has, and the coping picks up a cast from the
# water for the first half metre, which real ones visibly do.
WBOUNCE = 0.5 * LINER_TINT * 0.74 * (
    SUN_COL * cos_i * TSUN * np.exp(-ABS * (slant + DEPTH)) + SKY_AMB * 0.8)
print("water upwelling onto the coping: %s  (sky on stone: %s)"
      % (np.round(WBOUNCE, 3), np.round(SKY_DECK, 3)))


# --------------------------------------------------------------------------- materials
def liner(u, v):
    n = (0.5 + 0.5 * np.sin(u * 3.1 + .7) * np.sin(v * 4.3 - .4)
         + 0.30 * np.sin(u * 10.0 - 1.2) * np.sin(v * 8.5 + 2.1))
    a = 0.74 + 0.030 * (n - 0.6)
    a -= 0.34 * np.exp(-(((u - 4.0) / .15) ** 2 + ((v - 2.0) / .15) ** 2))
    return np.clip(a, .05, .95)[..., None] * LINER_TINT[None, None]


def tiles(u, v):
    """The wall, and specifically the last 155 mm of it. v is depth, 0 at the
    still waterline. A pool wall is not uniform down to the surface: it carries a
    waterline course in small mosaic, and it carries the two marks the surface
    itself leaves -- a chalky calcium bloom exactly at the mean level where
    evaporation keeps depositing the hardness, and a thin dirt line a couple of
    centimetres under it where the surface film collects and is never skimmed.
    Those two lines are the reason a real pool edge does not read as a cut."""
    lev = 0.82 + .04 * np.sin(u * 17.) * np.sin(v * 21.)
    g = ((np.abs(((u / .25) % 1.) - .5) > .456) | (np.abs(((v / .25) % 1.) - .5) > .456))
    lev = np.where(g, .70, lev)
    alb = np.broadcast_to(LINER_TINT[None, None], lev.shape + (3,)).copy()

    # The waterline course is 48 mm mosaic, but at 9 m and 11 degrees one tile is
    # a pixel and a half, so it is carried as a smooth modulation rather than a
    # hard grid: a two-level grid at that footprint is not detail, it is noise,
    # and the wall image is prefiltered on a fixed grid with no footprint to
    # filter against. Everything that survives the distance is smooth in u.
    wl = v > -0.155                                        # waterline course
    gm = .5 - .5 * np.cos(2 * np.pi * u / .048) * np.cos(2 * np.pi * v / .048)
    lev = np.where(wl, .66 + .13 * gm + .04 * np.sin(u * 131.) * np.sin(v * 97.), lev)
    alb = np.where(wl[..., None],
                   (LINER_TINT * np.array([.62, .91, 1.03]))[None, None], alb)

    cal = np.exp(-((v + .0095) / .0115) ** 2)              # calcium, at mean level
    dirt = np.exp(-((v + .0330) / .0165) ** 2)             # surface film, just under
    lev = lev * (1 + .34 * cal) * (1 - .22 * dirt)
    w = (.78 * cal)[..., None]
    alb = alb * (1 - w) + np.array([.95, .91, .84])[None, None] * w
    return np.clip(lev, .04, 1.7)[..., None] * alb


def sail_glow(u, v):
    """Diffuse transmission through the fabric. What matters at a point below is
    the SOLID ANGLE the panel subtends, not whether the point is under its
    footprint -- a swimmer two metres to the side still sees most of it. Proxy:
    1/(1+(d/R)^2) about the panel centroid, R from panel size + hang height."""
    c = SAIL[:, :2].mean(0)
    R = 0.5 * np.hypot(*(SAIL[:, :2].max(0) - SAIL[:, :2].min(0))) + SAIL[:, 2].mean()
    d2 = (u - c[0]) ** 2 + (v - c[1]) ** 2
    return 1.0 / (1.0 + d2 / (R * R))


def shade(cau, alb, ao=1.0, glow=None, dep=DEPTH, extra=None):
    """Receiver radiance. `dep` is the water OVER this texel, and it is a field,
    not a constant: the light path to it is dep/cos_t and the camera-side path is
    added later from the traced distance. This is where a tonal staircase over
    the steps comes from -- exp(-a*dep) with a(red) = 0.275 is a third of a stop
    per 250 mm riser in red alone, which is what makes a tread read shallower."""
    o = np.zeros(cau[0].shape + (3,))
    sl = dep / cos_t
    for c in range(3):
        ac = alb[..., c] if alb.ndim == 3 else alb
        amb = SKY_AMB[c] * ao
        if glow is not None:
            amb = amb + SAIL_TAU * SUN_COL[c] * SUN_DIR[2] * glow
        e = (SUN_COL[c] * cos_i * TSUN * cau[c] * np.exp(-ABS[c] * sl)
             + amb * np.exp(-ABS[c] * dep * 1.55))
        if extra is not None:
            e = e + extra[..., c]
        o[..., c] = ac * e
    return o


LIN = liner(BU, BV)
GLOW = sail_glow(BU, BV)


def bed_ao(x, y, z=None):
    """Sky visibility at a bed point, cosine-weighted. Two occluders:
      * the pool walls -- 1 - 0.30 exp(-d/0.30) is a two-wall corner losing 60%.
      * every step riser standing PROUD of this point. For a straight wall of
        height h at distance a the cosine-weighted occluded fraction is exactly
        (1 - a/sqrt(a^2+h^2))/2, so the dark line that hugs the underside of each
        nosing is a closed form, not a painted gradient. The arcs are convex
        outward, so this slightly over-occludes; that is the conservative way
        round for a contact shadow."""
    ao = 1.0 - 0.30 * np.exp(pool_sdf(x, y) / 0.30)
    zz = bed_z(x, y) if z is None else z
    for (cx, cy, R, ztop) in CYL:
        a = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - R
        h = ztop - zz
        ok = (a >= 0) & (h > 0)
        a = np.maximum(a, 1e-4)
        ao = ao * np.where(ok, 1.0 - .5 * (1.0 - a / np.hypot(a, np.maximum(h, 0.))), 1.0)
    return ao


BED_AO = bed_ao(BU, BV)

# --- one bounce back off the UNDERSIDE of the surface -------------------------
# The bed is a bright Lambertian reflector and the interface above it is a
# mirror over most of its output: everything leaving beyond the critical angle
# 48.6 deg is totally internally reflected straight back down. For a cosine
# distribution the share beyond that angle is exactly 1 - 1/n^2 = 0.438 -- no
# fitting, no constant. This is the term whose absence makes a shaded bed a flat
# dark hole: the bar says the water under the sail stays clearly luminous at
# about half the lit value, and flat sky ambient through the Snell window cannot
# do that. The step unit's own cast shadow needs it for the same reason.
# It is NOT a local fill. A ray leaving 1.40 m of water at the critical angle
# lands 3.2 m away and steeper ones land further, so the return is smeared over
# metres -- which is why it is estimated on a coarse grid and why it reads as a
# lift rather than as a glow. Only ONE bounce is taken; the further ones and the
# share that lands on the walls and comes back are not modelled.
TIR_FRAC = 1.0 - 1.0 / IOR[1] ** 2
_S2C = 1.0 / IOR[1] ** 2
NRET, RNX, RNY = 2_400_000, 200, 100
_rr = np.random.default_rng(4242)
_bx = _rr.uniform(X0, X1, NRET); _by = _rr.uniform(Y0, Y1, NRET)
_bz = bed_z(_bx, _by)
_u = _S2C + (1.0 - _S2C) * _rr.random(NRET)      # sin^2(theta), cosine-weighted
_sn, _cs = np.sqrt(_u), np.sqrt(1.0 - _u)
_ph = _rr.uniform(0, 2 * np.pi, NRET)
_up = -_bz / _cs                                  # slant from bed to surface
_sx = _bx + _up * _sn * np.cos(_ph)
_sy = _by + _up * _sn * np.sin(_ph)
_ok = pool_sdf(_sx, _sy) < SLIP                   # else it met a wall on the way up
_E = np.stack([sample(shade(bed[:3], np.ones_like(BDEP), BED_AO, glow=GLOW,
                            dep=BDEP)[..., c:c + 1], _bx, _by, X0, X1, Y0, Y1)[:, 0]
               for c in range(3)], 1)             # bed irradiance at the source
_A = sample(LIN, _bx, _by, X0, X1, Y0, Y1)        # times its albedo -> flux up
_W = _A * _E * (TIR_FRAC * (X1 - X0) * (Y1 - Y0) / NRET)
_sid, _u2, _v2, _sm, _ = scene_hit(_sx[_ok], _sy[_ok],
                                   (_sn * np.cos(_ph))[_ok], (_sn * np.sin(_ph))[_ok],
                                   -_cs[_ok])
_path = (_up[_ok] + _sm)
_bch, _wch = [], [[] for _ in range(4)]
for c in range(3):
    w = _W[_ok, c] * np.exp(-ABS[c] * _path)
    acc = np.zeros((RNY, RNX))
    m = _sid == 0
    splat(acc, _u2[m], _v2[m], w[m], X0, X1, Y0, Y1)
    acc /= ((X1 - X0) / RNX) * ((Y1 - Y0) / RNY)
    # ? 1.6 coarse texels (64 mm) of smoothing on the estimate. The returned
    # ? field is genuinely smooth over metres, so this removes Monte-Carlo
    # ? variance and not signal -- but the bandwidth itself is not derived.
    _bch.append(blur(acc, 1.6))
    for wi, sv in enumerate((1, 2, 3, 4)):
        m = _sid == sv
        a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
        wa = np.zeros((WNV // 4, WNU // 4))
        splat(wa, _u2[m], _v2[m], w[m], a, b, -DEPTH, 0.0)
        wa /= ((b - a) / (WNU // 4)) * (DEPTH / (WNV // 4))
        _wch[wi].append(blur(wa, 1.6))
bedret = np.stack(_bch, -1)
wallret = [np.stack(_wch[wi], -1) for wi in range(4)]
print("TIR return: %.1f%% of the bed's own output comes back down; it adds %s "
      "to the bed against %s of sky ambient"
      % (100 * TIR_FRAC, np.round(bedret.reshape(-1, 3).mean(0), 3),
         np.round(SKY_AMB * np.exp(-ABS * DEPTH * 1.55), 3)))
BEDRET = np.stack([sample(bedret[..., c:c + 1], BU.ravel(), BV.ravel(),
                          X0, X1, Y0, Y1)[:, 0].reshape(BU.shape)
                   for c in range(3)], -1)

bed_img = {'disp': shade(bed[:3], LIN, BED_AO, glow=GLOW, dep=BDEP, extra=BEDRET),
           'mono': shade([bed[3]] * 3, LIN, BED_AO, glow=GLOW, dep=BDEP, extra=BEDRET)}
wall_img = {'disp': [], 'mono': []}
for wi in range(4):
    uu = np.linspace(Y0, Y1, WNU) if wi < 2 else np.linspace(X0, X1, WNU)
    UU, VV = np.meshgrid(uu, np.linspace(-DEPTH, 0.0, WNV))
    T = tiles(UU, VV)
    WR = np.stack([sample(wallret[wi][..., c:c + 1], UU.ravel(), VV.ravel(),
                          uu[0], uu[-1], -DEPTH, 0.)[:, 0].reshape(UU.shape)
                   for c in range(3)], -1)
    # the coping overhangs the wall by 20 mm, so the last few centimetres of wall
    # sit in its shade: the darkest thing in the pool is the line under the lip.
    WAO = .78 * (1.0 - .32 * np.exp(VV / .055))
    wall_img['disp'].append(shade(wall[wi][:3], T, WAO, dep=-VV, extra=WR))
    wall_img['mono'].append(shade([wall[wi][3]] * 3, T, WAO, dep=-VV, extra=WR))

# --- ONE BOUNCE OFF THE BED, ONTO THE RISERS ---------------------------------
# The step region rendered NEUTRAL GREY: median sRGB (119, 128, 141) at
# saturation 0.16, against 0.42 for open water in the SAME image row and 0.69
# for the floor nearer the camera. Same row is the same grazing angle and the
# same Fresnel, so the surface reflection was not the cause; the receiver was.
# The bar says the saturation comes from the liner and that the water column can
# only subtract, so a near-neutral region is a statement that light reached the
# camera without going through water or off the liner. What was happening is
# arithmetic: the riser's own radiance was so low that the (horizon-coloured,
# nearly neutral) sky reflection won by default at 36% Fresnel.
#
# WHY THE RISER HAS ALMOST NOTHING. The refracted sun runs east at 44.4 deg from
# vertical, so a face is lit only if it faces west of the underwater terminator;
# an anti-solar camera looks at east-facing surfaces by construction. The two
# sets barely intersect, and the print further down MEASURES the overlap rather
# than asserting it away: about 6% of the riser arc is both lit and visible, and
# nowhere on it does min(N.L, N.V) exceed 0.10 -- the sun 84 deg off the normal
# on a face the camera sees 84 deg off the normal. So direct sun on a visible
# riser is not identically zero, it is a grazing tenth of one term on a sliver
# a few pixels wide. The appearance of the step region is indirect light, and
# the model had exactly one indirect term: SKY_AMB * ao, a flat blue DC through
# the Snell window.
#
# THE MISSING TERM is one bounce off the sunlit tread and floor a few
# centimetres in front of the riser. It is the bigger of the two and it is the
# one that carries colour and structure: the liner is a diffuse reflector of
# albedo (0.24, 0.54, 0.70) carrying the caustic net, so what arrives from below
# is bright cyan and spatially varying, and a real riser visibly shows the net
# moving on it.
#
# IT IS A GATHER, NOT A FORM FACTOR, for two reasons. The pattern is the point --
# a form factor would deliver the right energy with no net on it. And the bed a
# riser sees is a staircase, not a plane: the tread in front is 43% in the
# riser's own shadow, the floor beyond it is in full sun 0.7 m lower, and the
# outer nosing hides part of that floor. No closed form spans those.
#
# THE ESTIMATOR is cosine-weighted about the outward normal and restricted to
# the downgoing half of the hemisphere, which is exactly the half a vertical
# face can see the bed through; the upgoing half is the sky term already there,
# so the two partition the hemisphere and nothing is counted twice. With
# psi drawn uniformly on (0, pi) the pdf is 2 cos(t)/pi over that half, so
# E = (pi/2) <L_real> = 0.5 <L>, L being the same albedo*irradiance product that
# shade() returns. The closed form for a uniformly bright bed is then exactly
# 0.5, and that is printed below as a regression test on the quadrature.
RIS_NT, RIS_NZ = 512, 24        # arc samples per cylinder (18 mm), height samples
RIS_NU, RIS_NP = 8, 8           # stratified cosine x azimuth gather directions
_rr2 = np.random.default_rng(90210)
_U1 = ((np.arange(RIS_NU)[:, None] + _rr2.random((RIS_NU, RIS_NP))) / RIS_NU).ravel()
_PSI = (np.pi * (np.arange(RIS_NP)[None, :] + _rr2.random((RIS_NU, RIS_NP)))
        / RIS_NP).ravel()
_DN = np.sqrt(1.0 - _U1)                    # along the outward normal
_DT = np.sqrt(_U1) * np.cos(_PSI)           # along the tangent
_DB = np.sqrt(_U1) * np.sin(_PSI)           # straight down; > 0 by construction

RIS_MAP, RIS_FOOT, _mbs = [], [], []
_rstat = np.zeros(3)                        # [bed+wall hits, riser hits, samples]
for _i, (_cx, _cy, _R, _zt) in enumerate(CYL):
    _th = (np.arange(RIS_NT) + .5) / RIS_NT * 2 * np.pi
    _ct, _st = np.cos(_th), np.sin(_th)
    # the riser's FOOT is whatever the bed does just outside this cylinder --
    # the next tread down, or the floor. Read, not tabulated, so the map needs
    # no edit when a level moves.
    _zf = np.minimum(bed_z(_cx + (_R + 2e-3) * _ct, _cy + (_R + 2e-3) * _st),
                     _zt - 1e-3)
    RIS_FOOT.append(_zf)
    _tt = (np.arange(RIS_NZ) + .5) / RIS_NZ
    _Z = (_zf[None, :] + _tt[:, None] * (_zt - _zf)[None, :])
    _PX = np.broadcast_to(_cx + _R * _ct, _Z.shape).ravel()
    _PY = np.broadcast_to(_cy + _R * _st, _Z.shape).ravel()
    _NX = np.broadcast_to(_ct, _Z.shape).ravel().copy()
    _NY = np.broadcast_to(_st, _Z.shape).ravel().copy()
    _PZ = _Z.ravel()
    # Only the arc INSIDE the basin is traced. The other half of a wall-set unit
    # is behind the wall, where a ray leaves the box immediately and every
    # distance is negative: garbage, and it would poison the map's neighbours
    # through the bilinear read at the wall.
    _ix = np.flatnonzero(pool_sdf(_PX, _PY) < 0.0)
    _PX, _PY, _PZ2 = _PX[_ix], _PY[_ix], _PZ[_ix]
    _NX, _NY = _NX[_ix], _NY[_ix]
    _acc = np.zeros((_PZ.size, 3))
    for _dn, _dt, _db in zip(_DN, _DT, _DB):
        _tx, _ty = _NX * _dn - _NY * _dt, _NY * _dn + _NX * _dt
        _tz = np.full(_PZ2.size, -_db)
        _sd, _u, _v, _sm, _ = scene_hit(_PX + _NX * 1e-4, _PY + _NY * 1e-4,
                                        _tx, _ty, _tz, _PZ2)
        _col = np.zeros((_PZ2.size, 3))
        _m = _sd == 0
        if _m.any():
            _col[_m] = sample(bed_img['mono'], _u[_m], _v[_m], X0, X1, Y0, Y1)
        for _wi, _sv in enumerate((1, 2, 3, 4)):
            _m = _sd == _sv
            if _m.any():
                _a, _b = (Y0, Y1) if _sv <= 2 else (X0, X1)
                _col[_m] = sample(wall_img['mono'][_wi], _u[_m], _v[_m],
                                  _a, _b, -DEPTH, 0.)
        # ? a gather ray that lands on ANOTHER riser contributes nothing. Those
        # ? faces are the dark side of the same terminator, so the error is one
        # ? bounce of a dim source; the share is printed and it is under 2%.
        _acc[_ix] += _col * np.exp(-ABS[None] * _sm[:, None])
        _rstat += [(_sd != 5).sum(), (_sd == 5).sum(), _sd.size]
    _acc *= 0.5 / (RIS_NU * RIS_NP)
    _mbs.append(_acc[_ix].mean(0))
    RIS_MAP.append(_acc.reshape(RIS_NZ, RIS_NT, 3))
print("riser bounce: %d faces x %d directions; view-factor closure %.3f of the "
      "0.500 a vertical face has by geometry (%.1f%% of rays land on another "
      "riser and are dropped)"
      % (4 * RIS_NT * RIS_NZ, RIS_NU * RIS_NP,
         0.5 * _rstat[0] / max(_rstat[2], 1), 100 * _rstat[1] / max(_rstat[2], 1)))
print("  it adds %s of irradiance against %s of sky ambient on the same face "
      "-- and unlike the sky term it carries the caustic net"
      % (np.round(np.mean(_mbs, 0), 3), np.round(SKY_AMB * 0.5, 3)))

# The TIR return arrives at SHALLOW angles -- everything the bed emits beyond the
# critical angle 48.6 deg comes back down between 48.6 and 90 deg from vertical --
# so a vertical face intercepts it BETTER than the horizontal bed the bedret map
# is normalised for. For a Lambertian bed the returning flux has angular density
# cos(t) sin(t) dt over [tc, 90], so
#   E_horiz ~ int cos^2(t) sin(t) dt      = cos^3(tc)/3            = 0.0969
#   E_vert  ~ int sin^2(t) cos(t) sin(t) dt / pi = (1-sin^4(tc))/(4 pi) = 0.0545
# (the 1/pi is <max(cos azimuth, 0)> over a full turn), giving 0.563. Derived,
# not fitted -- but it does assume the arriving distribution is still the emitted
# one after the metre-scale smear, which is only true because every bed point
# emits the same distribution.
_SC2 = 1.0 / IOR[1] ** 2
TIR_VERT = ((1.0 - _SC2 ** 2) / (4 * np.pi)) / ((1.0 - _SC2) ** 1.5 / 3.0)
print("  TIR return on a vertical face: %.3f of its value on the bed" % TIR_VERT)


def riser_bounce(x, y, z, ci):
    """Bilinear read of the bounce map. Theta wraps; height is normalised to the
    riser's own foot, so a 240 mm riser and the 700 mm drop to the floor carry
    the same map without either being resampled."""
    out = np.zeros((x.size, 3))
    for i, (cx, cy, R, ztop) in enumerate(CYL):
        m = ci == i
        if not m.any():
            continue
        fa = (np.arctan2(y[m] - cy, x[m] - cx) % (2 * np.pi)) / (2 * np.pi) * RIS_NT - .5
        ja = np.floor(fa).astype(np.int64)
        fj = (fa - ja)[:, None]
        j0, j1 = ja % RIS_NT, (ja + 1) % RIS_NT
        zf = RIS_FOOT[i][j0] * (1 - fj[:, 0]) + RIS_FOOT[i][j1] * fj[:, 0]
        fb = np.clip((z[m] - zf) / np.maximum(ztop - zf, 1e-6), 0, 1) * RIS_NZ - .5
        kb = np.clip(fb, 0, RIS_NZ - 1.001).astype(np.int64)
        fk = np.clip(fb - kb, 0, 1)[:, None]
        A = RIS_MAP[i]
        out[m] = ((A[kb, j0] * (1 - fj) + A[kb, j1] * fj) * (1 - fk) +
                  (A[kb + 1, j0] * (1 - fj) + A[kb + 1, j1] * fj) * fk)
    return out

# --- the depth ladder, measured ----------------------------------------------
# F = 0.25 d s k with s and k taken from the field itself over the water that
# actually lights each receiver, so the number moves with the depth and nothing
# else. Cell size is the autocorrelation reading, in the same units the bar uses.
from field import grad_grid as _gg
import field as _fld


def _sk(x0, x1, y0, y1):
    xs = np.linspace(x0, x1, 192).astype(np.float32)
    ys = np.linspace(y0, y1, 192).astype(np.float32)
    gx, gy = _gg(xs, ys)
    # ONE slope convention, and it is field.py's: s = sqrt(<|grad h|^2>), the
    # total mean-square slope. This line used to divide by 2 -- the per-axis rms,
    # smaller by sqrt(2) -- while the F(net) column beside it was fed
    # field.REVERB_RMS, which is total. Two units in one printed table, which is
    # exactly the defect the surface lane had just removed from field.py. Calling
    # rms_slope rather than writing the expression out again is the fix that
    # sticks: there is now no second place where the convention can drift.
    s = _fld.rms_slope(gx, gy)
    dx, dy = (x1 - x0) / 191., (y1 - y0) / 191.
    P = np.abs(np.fft.rfft2(gx)) ** 2 + np.abs(np.fft.rfft2(gy)) ** 2
    kx = 2 * np.pi * np.fft.rfftfreq(192, dx)[None, :]
    ky = 2 * np.pi * np.fft.fftfreq(192, dy)[:, None]
    P[0, 0] = 0.0
    return s, np.sqrt((P * (kx * kx + ky * ky)).sum() / P.sum())


_PATCH = [("top tread   ", STEP_Z[0], 5.45, 6.55, 3.45, 3.95),
          ("2nd tread   ", STEP_Z[1], 5.70, 6.30, 2.88, 3.05),
          ("bench       ", BENCH_Z, 2.65, 3.35, 3.65, 3.98),
          ("3rd tread   ", STEP_Z[2], 5.70, 6.30, 2.55, 2.75),
          ("floor       ", -DEPTH, 4.80, 6.50, 0.90, 2.30)]
# F is a PER-BAND number -- that is the whole point of field.py's slope budget --
# so the net-writing band is what decides whether a receiver has a legible net.
# REVERB at 19.7 cm writes it; the all-band column is the same formula fed the
# slope-energy-weighted k, which the capillary floor drags down to ~8 cm and
# which therefore says "past focus" about water that plainly is not. Both are
# printed because reporting only the second is exactly the mistake the slope
# budget exists to catch. Corrected to the total-mss convention the F(all) column
# now crosses 1.0 on the floor -- so the all-band reading says "past focus" about
# the one receiver whose net is plainly legible in the frame. That does not
# weaken the argument above, it is the argument: a slope-energy-weighted k that
# the 2.8 cm capillary band drags to ~9.6 cm is the wrong k to put in F.
_KNET = _fld._plane_k(_fld.REVERB)
print("  receiver      depth  F(net,%.0fcm)  s_all  k_all  F(all)  cell (autocorr)"
      % (200 * np.pi / _KNET))
for nm, zz, x0, x1, y0, y1 in _PATCH:
    d = -zz
    # The water that lights this patch sits one refracted offset to the WEST.
    # The window over it is a fixed 1.2 m square rather than the patch's own
    # footprint: a tread patch is 170 mm across the annulus, and a window
    # narrower than a couple of wavelengths cannot see the 20 cm band at all --
    # it measures the capillary floor and reports it as k, which is how the
    # 2nd tread came out at k = 166 (3.8 cm) with the same water beside it at 66.
    off = d * np.tan(np.arccos(cos_t))
    xa = min(max(.5 * (x0 + x1) - off, X0 + .65), X1 - .65)
    ya = min(max(.5 * (y0 + y1), Y0 + .65), Y1 - .65)
    s, k = _sk(xa - .6, xa + .6, ya - .6, ya + .6)
    print("  %s %5.3f m     %5.2f      %.3f %6.1f  %5.2f    %4.0f mm"
          % (nm, d, 0.25 * d * _fld.REVERB_RMS * _KNET, s, k,
             0.25 * d * s * k, 1000 * cell_size(x0, x1, y0, y1)))


def sky(dx, dy, dz):
    t = np.clip(dz, 0, 1)[:, None] ** .55
    col = SKY_HOR[None] * (1 - t) + SKY_TOP[None] * t
    cs = np.clip(dx * SUN_DIR[0] + dy * SUN_DIR[1] + dz * SUN_DIR[2], 0, 1)
    return (col + SUN_COL[None] * 26. * (cs ** 12000)[:, None]
            + np.array([1., .90, .72])[None] * 2.6 * (cs ** 260)[:, None]
            + np.array([1., .92, .80])[None] * 1.15 * (cs ** 14)[:, None]) * 1.15


_VN = rng.random((256, 256))


def vnoise(x, y):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    g = lambda a, b: _VN[(yi + b) & 255, (xi + a) & 255]
    return ((g(0, 0) * (1 - fx) + g(1, 0) * fx) * (1 - fy) +
            (g(0, 1) * (1 - fx) + g(1, 1) * fx) * fy)


def vnoise_d(x, y):
    """Same field, with its analytic gradient -- the paving needs slopes, not
    values: at a 21 degree sun the relief is carried by N.L, not by albedo."""
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    dux, duy = 6 * fx * (1 - fx), 6 * fy * (1 - fy)
    g = lambda a, b: _VN[(yi + b) & 255, (xi + a) & 255]
    a00, a10, a01, a11 = g(0, 0), g(1, 0), g(0, 1), g(1, 1)
    k1, k2 = a10 - a00, a01 - a00
    k3 = a00 - a10 - a01 + a11
    return (a00 + k1 * ux + k2 * uy + k3 * ux * uy,
            (k1 + k3 * uy) * dux, (k2 + k3 * ux) * duy)


# --------------------------------------------------------------------------- the pool edge
# The single thing this file used to get wrong. The water was a rectangle test
# against a deck plane 55 mm up, so the two met along an aliased boolean line and
# the pool read as a decal. It is replaced here by the actual section of a pool
# edge, traced as a height field: wall, coping bedded on it and OVERHANGING its
# face, bullnose rolled over the overhang, water 75 mm below the coping top.
pool_s = pool_sdf              # the shape enters through ONE function; see the top
pool_grad = pool_sdf_grad


def edge_z(s):
    d = np.clip(SBUL - s, 0., BULR)
    return np.where(s >= SBUL, ZD, ZCEN + np.sqrt(np.maximum(BULR * BULR - d * d, 0.)))


def _hash(a, b, k=0.):
    v = np.sin(a * 127.1 + b * 311.7 + k * 74.7) * 43758.5453
    return v - np.floor(v)


def _run(x, y):
    """Position along the coping course, and which of the four sides it is on."""
    gx, gy, e = pool_grad(x, y)
    return np.where(e, y, x), np.where(e, np.where(gx > 0, 0., 1.),
                                       np.where(gy > 0, 2., 3.)), gx, gy, e


def lip_wobble(x, y):
    """Coping stones are LAID, not extruded. Each sits a couple of millimetres
    proud or shy of its neighbour and its arris is worn unevenly, so the line
    where water meets stone is never straight. Amplitude 4 mm, which is a third
    of a pixel at the far coping and four pixels at the near one -- and at the
    near one a mathematically straight, stair-stepped waterline was the loudest
    synthetic tell left in the frame. Physical, and it dithers the edge."""
    a, sd, _, _, _ = _run(x, y)
    k = np.floor((a + .19 * sd) / .55)
    return (.0040 * (_hash(k, sd, 5.7) - .5) * 2.
            + .0026 * (vnoise(a * 11., sd * 7.3 + .5) - .5) * 2.)


def pool_se(x, y):
    return pool_s(x, y) + lip_wobble(x, y)


def gh(x, y):
    s = pool_se(x, y)
    return np.where(s < SLIP, 0.0, edge_z(s))


# --------------------------------------------------------- caustic light OUT of the pool
# The other half of the WBOUNCE term. The bed is a bright diffuse reflector
# carrying the sun's net; that radiance hits the UNDERSIDE of the same wavy
# surface, and the surface lenses it on the way out exactly as on the way in. So
# what leaves the pool is not a uniform teal glow -- it is a focused, moving
# pattern, spatially coherent with the caustics on the bed because it is the same
# wave field and the same bed map, read along the reverse path.
#
# The path is traced, not invented: from a point on the stone, aim back at the
# water, refract INTO it with the real field.py normal at that point, trace to
# the bed with the same scene_hit, read the same bed_img. Fresnel on that entry
# is by reciprocity the transmittance the light actually had leaving, and it is
# what kills the near-grazing contributions from far out in the basin.
#
# WHAT CAN SEE THE WATER AT ALL. A horizontal stone face 75 mm ABOVE the water
# plane cannot: every direction toward the water is below its horizon, N.w < 0.
# Only faces that tip toward the pool see it -- the bullnose, the poolward flank
# of every joint groove, and the poolward half of the stone's own micro-relief.
# So the receiver normal used here is the POOLWARD HORIZONTAL one, and what the
# flat top of the coping gets is only the sub-pixel-facet share of that (the
# 0.10 below, which stays a `?`). The falloff is no longer a guessed exponential.
DECK_S = np.array([SLIP, 0.02, 0.06, 0.14, 0.30, 0.55, 0.95])
DECK_DA = 0.005                      # 5 mm along the run; the pattern's own
DECK_NA = [int(round((Y1 - Y0) / DECK_DA))] * 2 + \
          [int(round((X1 - X0) / DECK_DA))] * 2      # finest scale is ~70 mm
_DG = [(1., 0., 0., 1., X1, None), (-1., 0., 0., 1., X0, None),
       (0., 1., 1., 0., None, Y1), (0., -1., 1., 0., None, Y0)]
_NRHO, _NPHI = 12, 7
_RHO = np.exp(np.linspace(np.log(0.010), np.log(6.0), _NRHO))
_PHI = np.linspace(-np.deg2rad(75.), np.deg2rad(75.), _NPHI)


def _deck_gather(flat):
    """Irradiance on a poolward-facing stone facet from the water surface.
    Polar quadrature over the water: for a facet at height qz above the still
    plane and a surface point at horizontal distance rho and bearing phi off the
    inward normal, R^2 = rho^2 + qz^2, the incoming direction carries
    (N.w) = rho cos(phi)/R and dOmega = (qz/R) dA/R^2, so the weight is
    rho cos(phi) qz / R^4 -- a 1/s falloff before Fresnel, and steeper after it,
    which is the 'near-grazing exit from a source of finite extent' the pattern
    is supposed to have."""
    out = []
    for sd in range(4):
        gx, gy, lx, ly, fx, fy = _DG[sd]
        a = (np.arange(DECK_NA[sd]) + .5) * DECK_DA + (Y0 if sd < 2 else X0)
        acc = np.zeros((len(DECK_S), DECK_NA[sd], 3))
        for si, s in enumerate(DECK_S):
            qz = float(edge_z(np.array([s]))[0])
            bx = (fx + gx * s) if fx is not None else a
            by = (fy + gy * s) if fy is not None else a
            bx = np.broadcast_to(np.atleast_1d(bx), a.shape).astype(np.float64)
            by = np.broadcast_to(np.atleast_1d(by), a.shape).astype(np.float64)
            for ph in _PHI:
                cp, sp = np.cos(ph), np.sin(ph)
                r0 = max((s - SLIP) / cp, 1e-3)
                rho = _RHO[_RHO > r0]
                if not rho.size:
                    rho = np.array([r0 * 1.05])
                dln = np.log(_RHO[-1] / _RHO[0]) / (_NRHO - 1)
                dphi = (_PHI[-1] - _PHI[0]) / (_NPHI - 1)
                for rr in rho:
                    px = bx - gx * rr * cp + lx * rr * sp
                    py = by - gy * rr * cp + ly * rr * sp
                    ok = pool_sdf(px, py) < SLIP
                    if not ok.any():
                        continue
                    R = np.hypot(rr, qz)
                    # direction from the facet DOWN to the water point
                    wx, wy, wz = (px - bx) / R, (py - by) / R, -qz / R
                    if flat:
                        nx_, ny_, nz_ = np.zeros_like(px), np.zeros_like(px), np.ones_like(px)
                    else:
                        nx_, ny_, nz_ = normal_from_grad(*grad_points(px, py))
                    cosi = -(wx * nx_ + wy * ny_ + wz * nz_)
                    tx, ty, tz = refract(wx, wy, wz, nx_, ny_, nz_, 1.0 / IOR[1])
                    sid, u, v, sm, _ = scene_hit(px, py, tx, ty, tz)
                    col = np.zeros((len(px), 3))
                    m = sid == 0
                    if m.any():
                        col[m] = sample(bed_img['mono'], u[m], v[m], X0, X1, Y0, Y1)
                    for wi, sv in enumerate((1, 2, 3, 4)):
                        m = sid == sv
                        if m.any():
                            aa, bb = (Y0, Y1) if sv <= 2 else (X0, X1)
                            col[m] = sample(wall_img['mono'][wi], u[m], v[m],
                                            aa, bb, -DEPTH, 0.)
                    col = col * np.exp(-ABS[None] * sm[:, None])
                    T = 1.0 - (F0[None] + (1 - F0[None]) *
                               (1 - np.clip(cosi, 0, 1))[:, None] ** 5)
                    w = rr * cp * qz / R ** 4 * (rr * rr * dln * dphi)
                    acc[si] += np.where(ok[:, None], col * T * w, 0.0)
        out.append(acc)
    return out


print("water-out pass: %d facets x %d water samples"
      % (sum(DECK_NA) * len(DECK_S), _NRHO * _NPHI), flush=True)
DECK = _deck_gather(False)
DECK0 = _deck_gather(True)
_fall = np.array([DECK0[2][si].mean() for si in range(len(DECK_S))])
_fall /= _fall[0]
print("  water-out falloff off the lip: " +
      "  ".join("%.0fmm:%.2f" % (1000 * s, f) for s, f in zip(DECK_S, _fall)))
_pat = np.array([np.std(DECK[2][si, :, 1] / np.maximum(DECK0[2][si, :, 1], 1e-12))
                 for si in range(len(DECK_S))])
print("  pattern contrast (rms/mean of the lensed / flat ratio): " +
      "  ".join("%.2f" % p for p in _pat))


def deck_water(along, side, s):
    """Bilinear lookup of the water-out map: pattern ratio, and derived falloff."""
    out = np.ones((len(along), 3)); fal = np.ones(len(along))
    fs = np.interp(np.clip(s, DECK_S[0], DECK_S[-1]), DECK_S,
                   np.arange(len(DECK_S)))
    i0 = np.clip(fs.astype(np.int64), 0, len(DECK_S) - 2); ft = (fs - i0)[:, None]
    for sd in range(4):
        m = side == sd
        if not m.any():
            continue
        fa = np.clip((along[m] - (Y0 if sd < 2 else X0)) / DECK_DA - .5,
                     0, DECK_NA[sd] - 1.001)
        ja = fa.astype(np.int64); fj = (fa - ja)[:, None]
        A, B = DECK[sd], DECK0[sd]
        j0, k0 = i0[m], ja
        def g(arr):
            lo = arr[j0, k0] * (1 - fj) + arr[j0, k0 + 1] * fj
            hi = arr[j0 + 1, k0] * (1 - fj) + arr[j0 + 1, k0 + 1] * fj
            return lo * (1 - ft[m]) + hi * ft[m]
        num, den = g(A), g(B)
        # ? clipped at 4x: far out on the deck the flat reference is nearly zero
        # ? and the ratio is quadrature noise, not lensing. It is multiplied by a
        # ? falloff of order 0.01 there, so the clip changes nothing visible.
        out[m] = np.clip(num / np.maximum(den, 1e-12), 0., 4.)
        fal[m] = den[:, 1] / max(DECK0[sd][0, :, 1].mean(), 1e-12)
    return out, fal


def _groove(c, per, hw, dep):
    """A joint every `per` metres. A 5 mm groove under a 21 degree sun is not a
    drawn line: it is one face that catches the sun and one that cannot."""
    f = (c / per) % 1.0
    d = np.minimum(f, 1 - f) * per
    return (-dep * np.clip(1 - d / hw, 0, 1),
            np.where(d < hw, dep / hw * np.where(f < .5, 1., -1.), 0.),
            np.clip(1 - d / hw, 0, 1), np.clip(1 - d / .050, 0, 1))


def _notch(c, c0, hw, dep):
    d = np.abs(c - c0)
    return (-dep * np.clip(1 - d / hw, 0, 1),
            np.where(d < hw, dep / hw * np.sign(c - c0), 0.),
            np.clip(1 - d / hw, 0, 1), np.clip(1 - d / .050, 0, 1))


def paving(x, y, s, vdir, fp):
    """Coping course and terrace. In this frame it is a border, so it gets what a
    border needs and nothing else: stone that changes stone to stone, joints with
    a groove rather than a line, and the splash-damp band every coping carries
    within a hand's width of the water -- darker, and glossy where the stone is
    matt. No garden, no props."""
    along, side, gx, gy, ex = _run(x, y)
    cop = s < COPW

    # --- joints: coping runs across the course, the terrace is a 0.92 x 0.61 field
    ja, dja, ga, wa = _groove(along + .19 * side, .55, .009, .0050)
    jn, djn, gn, wn = _notch(s, COPW, .009, .0050)
    row = np.floor(y / .61)
    jx, djx, gxj, wxj = _groove(x + .46 * (row % 2.), .92, .008, .0045)
    jy, djy, gyj, wyj = _groove(y, .61, .008, .0045)
    dzx = np.where(cop, np.where(ex, 0., dja) + djn * gx, djx)
    dzy = np.where(cop, np.where(ex, dja, 0.) + djn * gy, djy)
    jm = np.where(cop, np.maximum(ga, gn), np.maximum(gxj, gyj))
    jw = np.where(cop, np.maximum(wa, wn), np.maximum(wxj, wyj))

    # --- micro relief, faded out once an octave is finer than the pixel footprint
    n1, d1x, d1y = vnoise_d(x * 1.9, y * 1.9)
    n2, d2x, d2y = vnoise_d(x * 8.5 + 11., y * 8.5 + 3.)
    n3, d3x, d3y = vnoise_d(x * 33. + 5., y * 33. + 7.)
    n4, d4x, d4y = vnoise_d(x * 128. + 19., y * 128. + 23.)
    n5, d5x, d5y = vnoise_d(x * 430. + 2., y * 430. + 8.)
    w2 = 1. / (1. + (2.6 * fp * 8.5) ** 2)
    w3 = 1. / (1. + (2.6 * fp * 33.) ** 2)
    w4 = 1. / (1. + (2.6 * fp * 128.) ** 2)
    w5 = 1. / (1. + (2.6 * fp * 430.) ** 2)
    dzx = (dzx + .0055 * w2 * d2x * 8.5 + .0016 * w3 * d3x * 33.
           + .00040 * w4 * d4x * 128. + .00009 * w5 * d5x * 430.)
    dzy = (dzy + .0055 * w2 * d2y * 8.5 + .0016 * w3 * d3y * 33.
           + .00040 * w4 * d4y * 128. + .00009 * w5 * d5y * 430.)

    # --- the bullnose, as a normal in (s, z)
    d = np.clip(SBUL - s, 0., BULR)
    nz0 = np.sqrt(np.maximum(BULR * BULR - d * d, 0.)) / BULR
    ns0 = np.where(s < SBUL, -d / BULR, 0.)
    Nx, Ny, Nz = ns0 * gx - dzx * nz0, ns0 * gy - dzy * nz0, nz0
    inv = 1. / np.sqrt(Nx * Nx + Ny * Ny + Nz * Nz)
    Nx, Ny, Nz = Nx * inv, Ny * inv, Nz * inv

    # --- splash. The stone within ~15 cm of the lip is never dry at 18:41.
    wr = WET * (.55 + .90 * vnoise(x * 2.6 + 31., y * 2.6 + 17.))
    wet = np.clip(1. - (s - SLIP) / np.maximum(wr, .02), 0, 1) ** 1.4
    spot = (np.clip((vnoise(x * 5.5 + 3., y * 5.5 + 9.) - .60) / .18, 0, 1) *
            np.clip(1. - (s - SLIP) / .60, 0, 1))
    wet = wet * (.62 + .76 * vnoise(x * 9.5 + 51., y * 9.5 + 13.))   # splash is patchy
    wet = np.where(cop, np.maximum(wet, .60 * spot), .35 * spot)
    wet = np.minimum(wet * 1.35, 1.)

    # --- albedo
    ks = np.where(cop, np.floor((along + .19 * side) / .55), np.floor((x + .46 * (row % 2.)) / .92))
    kt = np.where(cop, side, row)
    t1, t2 = _hash(ks, kt, 3.1), _hash(ks, kt, 11.7)
    alb = np.where(cop[:, None], np.array([.700, .600, .452])[None],
                   np.array([.662, .562, .428])[None])
    alb = alb * (1. + .46 * (t1 - .5))[:, None]
    alb = alb * (1. + np.stack([.20 * (t2 - .5), .03 * (t2 - .5), -.21 * (t2 - .5)], 1))
    alb = alb * (1. + .13 * (n1 - .5) + .11 * w2 * (n2 - .5) + .09 * w3 * (n3 - .5)
                 + .07 * w4 * (n4 - .5) + .05 * w5 * (n5 - .5))[:, None]
    alb = alb * (1. - .42 * jm)[:, None]
    alb = alb * (1. - .22 * jw * vnoise(x * 3.3 + 61., y * 3.3 + 41.))[:, None]
    alb = alb * (1. - .54 * wet)[:, None]

    # --- light
    L = SUN_DIR
    ndl = np.clip(Nx * L[0] + Ny * L[1] + Nz * L[2], 0, 1)
    vis = np.asarray(sun_vis(x, y), float)
    lift = SAIL_TAU * (1. - vis) * sail_glow(x, y)
    skyv = (.55 + .45 * Nz) * (1. - .40 * jm)
    pf = np.clip(-(Nx * gx + Ny * gy), 0, 1)          # how much it faces the pool
    # The water's own light on the stone, in two parts that used to be one:
    #   level  -- WBOUNCE, the DC. Without it the bullnose renders black.
    #   shape  -- deck_water, the LENSED pattern and the derived falloff. The
    #             pattern is the ratio of the traced water-out gather to the same
    #             gather over a FLAT surface, so its mean is one by construction
    #             and it modulates the DC instead of adding energy to it.
    # 0.10 is still a `?`: it is the share of a nominally horizontal stone facet
    # that sub-pixel relief tips far enough poolward to see the water at all.
    pat, fal = deck_water(along, side.astype(np.int64), s)
    wv = (.95 * pf + .10 * Nz) * fal * (1. - .40 * jm)
    col = alb * (SUN_COL[None] * (ndl * vis + SUN_DIR[2] * lift)[:, None] * .30
                 + SKY_DECK[None] * skyv[:, None]
                 + WBOUNCE[None] * pat * wv[:, None])

    Vx, Vy, Vz = -vdir[:, 0], -vdir[:, 1], -vdir[:, 2]
    Hx, Hy, Hz = L[0] + Vx, L[1] + Vy, L[2] + Vz
    hn = 1. / np.sqrt(Hx * Hx + Hy * Hy + Hz * Hz)
    Hx, Hy, Hz = Hx * hn, Hy * hn, Hz * hn
    ndh = np.clip(Nx * Hx + Ny * Hy + Nz * Hz, 0, 1)
    vdh = np.clip(Vx * Hx + Vy * Hy + Vz * Hz, 0, 1)
    ndv = np.clip(Nx * Vx + Ny * Vy + Nz * Vz, 1e-3, 1)
    m = 12. + 300. * wet
    Fs = .045 + .955 * (1. - vdh) ** 5
    col = col + (SUN_COL[None] * (Fs * (m + 8.) / (8. * np.pi) * ndh ** m
                                  * ndl * vis * .30)[:, None])
    Fv = .045 + .955 * (1. - ndv) ** 5
    return col + SKY_AMB[None] * (Fv * (.09 + .55 * wet))[:, None]


# --------------------------------------------------------------------------- camera
fwd = TGT - EYE; fwd /= np.linalg.norm(fwd)
rgt = np.cross(fwd, [0, 0, 1.]); rgt /= np.linalg.norm(rgt)
upv = np.cross(rgt, fwd)
PX, PY = np.meshgrid((np.arange(W) + .5) / W * 2 - 1, 1 - (np.arange(H) + .5) / H * 2)
tf = np.tan(FOV / 2)
D = (fwd[None, None] + rgt[None, None] * (PX * tf * W / H)[..., None]
     + upv[None, None] * (PY * tf)[..., None])
D /= np.linalg.norm(D, axis=2, keepdims=True)
D = D.reshape(-1, 3)


def project(P):
    """World point -> pixel in the ENCODED image (after the SS box filter), so
    the crops below are aimed at geometry rather than at remembered numbers."""
    d = np.atleast_2d(np.asarray(P, float)) - EYE[None]
    f = np.maximum(d @ fwd, 1e-6)
    return np.stack([(((d @ rgt) / f / (tf * W / H) + 1) * .5 * W - .5) / SS,
                     ((1 - (d @ upv) / f / tf) * .5 * H - .5) / SS], -1)


def tri(o, d, a, b, c):
    e1, e2 = b - a, c - a
    p = np.cross(d, e2); det = p @ e1
    inv = 1. / np.where(np.abs(det) < 1e-12, 1e-12, det)
    t = o - a; u = (t @ p.T) * inv
    q = np.cross(t, e1); v = (d @ q) * inv; s = (e2 @ q) * inv
    return (u >= 0) & (v >= 0) & (u + v <= 1) & (s > 1e-4)


hit_sail = np.zeros(W * H, bool)
for t3 in ((0, 1, 2), (0, 2, 3)):
    hit_sail |= tri(EYE, D, SAIL[t3[0]], SAIL[t3[1]], SAIL[t3[2]])

# --- trace the pool edge as a height field ---------------------------------
# gh() is flat almost everywhere, so almost every ray is settled by an endpoint
# test and only the band of pixels that actually straddles the coping is marched.
Ex, Ey, Ez = EYE
with np.errstate(divide='ignore', invalid='ignore'):
    t_top = (ZD - Ez) / D[:, 2]           # plane of the coping top
    t_wat = (0.0 - Ez) / D[:, 2]          # the still waterline
down = (D[:, 2] < -1e-9) & ~hit_sail
t_top = np.where(down, t_top, BIG)
t_wat = np.where(down, t_wat, BIG)
_ax, _ay = Ex + D[:, 0] * t_top, Ey + D[:, 1] * t_top
_bx, _by = Ex + D[:, 0] * t_wat, Ey + D[:, 1] * t_wat
_sa, _sb = pool_s(_ax, _ay), pool_s(_bx, _by)
# THE SHORTCUT NEEDS CONVEXITY, and says so. pool_sdf is convex for the box, so
# on the 75 mm segment between the coping-top plane and the waterline it never
# exceeds its endpoints: both ends inside the lip proves the whole ray is over
# open water, and no march is needed. A freeform boundary with a concave lobe --
# a kidney's waist, a step unit cut out of the water -- breaks that, and the
# endpoints would silently certify a ray that clips stone in between. So the
# shortcut is GATED on POOL_CONVEX rather than assumed; with it off every
# downgoing ray is marched, which costs about 30x on this band of pixels.
# 8 mm of slack covers the laid-stone wobble, which is not convex either.
if POOL_CONVEX:
    is_wat = down & (np.maximum(_sa, _sb) < SLIP - .008)
    is_pav = down & (_sa >= SBUL + .008)   # already on the flat at the top plane
else:
    is_wat = down & (np.maximum(_sa, _sb) < SLIP - .30)
    is_pav = down & (np.minimum(_sa, _sb) >= SBUL + .30)
_mar = np.flatnonzero(down & ~is_wat & ~is_pav)
t_hit = np.where(is_wat, t_wat, np.where(is_pav, t_top, BIG))
print("edge march: %d of %d rays (%.2f%%) straddle the coping"
      % (_mar.size, down.sum(), 100. * _mar.size / max(down.sum(), 1)))
if _mar.size:
    _t0, _t1 = t_top[_mar], t_wat[_mar]
    _dx, _dy, _dz = D[_mar, 0], D[_mar, 1], D[_mar, 2]
    _lo, _hi, _prev = _t0.copy(), _t1.copy(), _t0.copy()
    _got = np.zeros(_mar.size, bool)
    for _k in range(1, 25):
        _t = _t0 + (_t1 - _t0) * (_k / 24.)
        _f = (Ez + _dz * _t) - gh(Ex + _dx * _t, Ey + _dy * _t)
        _n = (~_got) & (_f <= 0)
        _lo = np.where(_n, _prev, _lo); _hi = np.where(_n, _t, _hi)
        _got |= _n; _prev = _t
    _lo = np.where(_got, _lo, _t1); _hi = np.where(_got, _hi, _t1)
    for _ in range(16):
        _m = .5 * (_lo + _hi)
        _f = (Ez + _dz * _m) - gh(Ex + _dx * _m, Ey + _dy * _m)
        _lo = np.where(_f > 0, _m, _lo); _hi = np.where(_f > 0, _hi, _m)
    t_hit[_mar] = _hi

hx, hy = Ex + D[:, 0] * t_hit, Ey + D[:, 1] * t_hit
S_HIT = pool_se(hx, hy)
inp = down & (S_HIT < SLIP + 1e-7)
pav = down & ~inp
bgm = ~hit_sail & ~inp & ~pav             # nothing: the frame is water and stone

PIXANG = 2. * np.tan(FOV / 2.) / H
FOOT = t_hit * PIXANG / np.maximum(np.abs(D[:, 2]), .10)

ix, iy = hx[inp], hy[inp]
gxx, gyy = grad_points(ix, iy)
nx, ny, nz = normal_from_grad(gxx, gyy)
dd = D[inp]
vx, vy, vz = -dd[:, 0], -dd[:, 1], -dd[:, 2]
ndv = np.clip(nx * vx + ny * vy + nz * vz, 1e-4, 1.)
rfx, rfy = -vx + 2 * ndv * nx, -vy + 2 * ndv * ny
rfz = np.abs(-vz + 2 * ndv * nz)
refl = sky(rfx, rfy, rfz)
fres = F0[None] + (1 - F0[None]) * ((1 - ndv) ** 5)[:, None]

# --- what the water does within a hand's width of the wall -------------------
# Three separate things, all of them missing before, and together they are the
# whole reason a pool edge does not read as a cut in a coloured rectangle.
#  1  the reflection.  The coping stands 75 mm over the water and overhangs the
#     wall by 20 mm, so a reflected ray heading at the wall from close in hits
#     the underside of the stone instead of the sky.  That is the dark band that
#     hugs every real pool edge, and it wobbles because the ripples aim the ray.
#  2  the ambient.  Under the overhang the water sees a fraction of the sky.
#  3  the meniscus.  Water wets the wall and climbs it; the curved sliver is
#     brighter than the flat surface next to it.
IN_W = -S_HIT[inp]                          # distance in from the wall face
_egx, _egy, _ = pool_grad(ix, iy)
_toward = rfx * _egx + rfy * _egy           # + = the reflected ray heads at the wall
_over = rfz * np.maximum(IN_W + SLIP, 0.) / np.maximum(_toward, 1e-6)
_occ = np.where(_toward > 0, np.clip(1. - _over / ZD, 0, 1), 0.) ** .8
COP_REFL = np.array([.62, .57, .48]) * (SKY_DECK * .40 + WBOUNCE * .85)
refl = refl * (1 - _occ)[:, None] + COP_REFL[None] * _occ[:, None]
LIP_AO = 1. - .34 * np.exp(-(IN_W + SLIP) / .045)
MENIS = np.exp(-np.maximum(IN_W + SLIP, 0.) / .010)
print("reflection of the coping occludes %.1f%% of the visible surface"
      % (100. * (_occ > .5).mean()))

PAV_COL = paving(hx[pav], hy[pav], S_HIT[pav], D[pav], FOOT[pav])


# The refracted sun UNDER the surface, as one direction: this is what decides
# which faces of the step unit can be lit at all. It travels east and 2.6 deg
# south of east, so a riser is lit only if its outward normal has a westward
# component -- and an anti-solar camera can only see normals with an EASTWARD
# one. The two sets nearly exclude each other, and the test below measures the
# overlap over the whole riser arc of every cylinder instead of asserting it
# over five sample normals: what survives is a narrow band of faces that are
# grazed by both at once. Refraction at the surface does not change a ray's
# azimuth, only its elevation, so for a vertical face this test is exact.
_th = -SUN_DIR[:2] / np.linalg.norm(SUN_DIR[:2])
TSUN_DIR = np.array([_th[0] * sin_t, _th[1] * sin_t, -cos_t])
_a = np.linspace(0, 2 * np.pi, 1441)[:-1]
_ca, _sa = np.cos(_a), np.sin(_a)
_nlit = _nvis = _nboth = _ntot = 0.
_best = -9.
for (_cx, _cy, _R, _zt) in CYL:
    _px, _py = _cx + _R * _ca, _cy + _R * _sa
    _ok = ((pool_sdf(_px, _py) < 0) &
           (bed_z(_cx + (_R + 2e-3) * _ca, _cy + (_R + 2e-3) * _sa) < _zt - 1e-3))
    _nl = -(_ca * TSUN_DIR[0] + _sa * TSUN_DIR[1])
    _dx, _dy = EYE[0] - _px, EYE[1] - _py
    _nv = (_ca * _dx + _sa * _dy) / np.hypot(_dx, _dy)
    _nlit += (_ok & (_nl > 0)).sum(); _nvis += (_ok & (_nv > 0)).sum()
    _nboth += (_ok & (_nl > 0) & (_nv > 0)).sum(); _ntot += _ok.sum()
    _best = max(_best, np.where(_ok, np.minimum(_nl, _nv), -9.).max())
print("refracted sun under water: (%.3f, %.3f, %.3f)" % tuple(TSUN_DIR))
print("  riser arc in the basin: %.0f%% lit, %.0f%% faces the camera, %.1f%% both;"
      " the best any face manages is min(N.L, N.V) = %+.3f -- so the light on"
      " every riser this frame can see is entirely indirect"
      % (100 * _nlit / _ntot, 100 * _nvis / _ntot, 100 * _nboth / _ntot, _best))


def _riser_shade(hxr, hyr, hzr, ci, c, mode):
    """A cylindrical riser of the step unit. No caustic map is rasterised for
    these faces: the caustic pass drops the rays that reach them (that IS the
    cast shadow), and the mean refracted sun grazes them 2.6 deg on the dark
    side wherever the camera can see them. Four terms, in the order they matter:
      * the BOUNCE off the sunlit bed in front, gathered above -- the largest,
        the one that carries the caustic net, and the one whose absence rendered
        this whole region neutral grey;
      * the TIR return, arriving shallow and so favouring a vertical face;
      * sky through the Snell window, over the upgoing half hemisphere only;
      * direct sun, which is nonzero only on the crescent that turns west and is
        never visible from an anti-solar camera. It is kept because it is real,
        not because it is seen."""
    cx = np.array([c_[0] for c_ in CYL])[ci]
    cy = np.array([c_[1] for c_ in CYL])[ci]
    RR = np.array([c_[2] for c_ in CYL])[ci]
    zt = np.array([c_[3] for c_ in CYL])[ci]
    ox, oy = (hxr - cx) / RR, (hyr - cy) / RR
    # eased nosing: the top NOSE_R of the riser rolls over to meet the tread.
    # ? shading-only round-over -- 25 mm is under one pixel of silhouette here.
    th = np.clip((hzr - (zt - NOSE_R)) / NOSE_R, 0, 1) * (np.pi / 4)
    Nx, Ny, Nz = ox * np.cos(th), oy * np.cos(th), np.sin(th)
    d = -hzr
    lev = np.clip(0.74 + 0.030 * (0.5 + 0.5 * np.sin(hxr * 3.1 + .7)
                                  * np.sin(hyr * 4.3 - .4) - 0.6), .05, .95)
    ndl = np.clip(Nx * -TSUN_DIR[0] + Ny * -TSUN_DIR[1] + Nz * -TSUN_DIR[2], 0, 1)
    # ? the caustic that lands on a riser is read off the bed map 30 mm radially
    # ? outside it -- the map is indexed by bed position and a vertical face has
    # ? none. Only the bench crescent is lit at all, so this is a 6-pixel term.
    cau = sample((bed[c] if mode == 'disp' else bed[3])[..., None],
                 hxr + ox * .030, hyr + oy * .030, X0, X1, Y0, Y1)[:, 0]
    aow = bed_ao(hxr, hyr, hzr)
    ao = aow * .5 * (1. + Nz)          # a vertical face sees half the sky
    bnc = riser_bounce(hxr, hyr, hzr, ci)[:, c]
    tir = sample(bedret[..., c:c + 1], hxr, hyr, X0, X1, Y0, Y1)[:, 0] * \
        aow * (TIR_VERT + (1. - TIR_VERT) * Nz)
    return LINER_TINT[c] * lev * (
        SUN_COL[c] * cos_i * TSUN * cau * (ndl / cos_t) * np.exp(-ABS[c] * d / cos_t)
        + SKY_AMB[c] * ao * np.exp(-ABS[c] * d * 1.55)
        + tir + bnc)


def render(mode):
    img = np.zeros((W * H, 3))
    img[hit_sail] = (np.array([.74, .72, .76])[None] *
                     (SKY_AMB[None] * 1.6 + SUN_COL[None] * .22))
    if bgm.any():
        img[bgm] = sky(D[bgm, 0], D[bgm, 1], np.abs(D[bgm, 2])) * .95
    img[pav] = PAV_COL
    water = np.zeros((inp.sum(), 3))
    bi, wim = bed_img[mode], wall_img[mode]
    geo, smG = {}, None
    for c in range(3):
        eta = 1.0 / (IOR[c] if mode == 'disp' else IOR[1])
        if eta not in geo:                    # mono: one trace serves all three
            tx, ty, tz = refract(dd[:, 0], dd[:, 1], dd[:, 2], nx, ny, nz, eta)
            geo[eta] = scene_hit(ix, iy, tx, ty, tz) + (tz,)
        sid, u, v, sm, cyl, tz = geo[eta]
        col = np.zeros(len(u))
        m = sid == 0
        if m.any():
            col[m] = sample(bi[..., c:c + 1], u[m], v[m], X0, X1, Y0, Y1)[:, 0]
        for wi, sv in enumerate((1, 2, 3, 4)):
            m = sid == sv
            if m.any():
                a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
                col[m] = sample(wim[wi][..., c:c + 1], u[m], v[m], a, b, -DEPTH, 0.)[:, 0]
        m = sid == 5
        if m.any():
            col[m] = _riser_shade(u[m], v[m], tz[m] * sm[m], cyl[m], c, mode)
        water[:, c] = col * np.exp(-ABS[c] * sm)
        if c == 1:
            smG = sm
            global WSID, WU, WV
            WSID, WU, WV = sid, u, v      # green trace: what each water pixel sees
    # the residual in-scatter of a treated pool: tiny, but it is a PATH integral,
    # so it grows with the water actually crossed and is one more depth cue.
    water += np.array([.002, .011, .019])[None] * (1 - np.exp(-.30 * smG))[:, None]
    water *= LIP_AO[:, None]
    img[inp] = (fres * refl + (1 - fres) * water
                + (SKY_AMB[None] * .17 + SUN_COL[None] * .006) * MENIS[:, None])
    return img.reshape(H, W, 3)


def encode(hdr):
    hdr = hdr.reshape(H // SS, SS, W // SS, SS, 3).mean((1, 3))
    x = hdr * EXPOSURE
    a, b, c, d, e = 2.51, .03, 2.43, .59, .14
    x = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    x = np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)
    x = np.clip(x, 0, 1)
    lum = (x * np.array([.2126, .7152, .0722])).sum(-1, keepdims=True)
    x = np.clip(lum + (x - lum) * 1.06, 0, 1)              # saturation, display-side
    #  1.06, not 1.22: with a blue liner the saturation is physical, not graded
    #  and the S below is 1.045, not 1.10: spec B's most-missed property is that
    #  the caustic cell INTERIORS stay turquoise instead of dropping to navy, and
    #  a display-side contrast boost is exactly what pushes them there.
    x = np.clip((x - .5) * 1.045 + .5 + .020, 0, 1)         # gentle S, display-side
    return (x * 255 + .5).astype(np.uint8)


hero = encode(render('disp'))


# --- THE COLOUR REGRESSION ---------------------------------------------------
# The defect this round existed to fix does not show up in any of the numbers
# above: every term in _riser_shade was defensible on its own and the region
# still came out neutral. So it is measured here, in the units the bar's section
# A is written in -- the sRGB (max - min)/max of a region's MEDIAN colour.
#
# Two rules make the reading mean something. Regions are compared WITHIN THE SAME
# IMAGE ROWS, because grazing angle and Fresnel are functions of the row, and
# holding them fixed is what makes the difference attributable to the receiver.
# And a downsampled pixel counts only if all SS^2 of its subsamples belong to one
# region, so nothing on a silhouette edge is mixed into either side.
def _regions():
    lb = np.zeros(W * H, np.int8)
    iw = np.flatnonzero(inp)
    flr = (WSID == 0) & (bed_z(WU, WV) <= -DEPTH + 1e-6)
    lb[iw[WSID == 5]] = 1                                   # riser face
    lb[iw[(WSID == 0) & ~flr]] = 2                          # tread / bench top
    lb[iw[flr]] = 3                                         # floor, 1.40 m down
    lb[np.flatnonzero(pav)] = 4                             # stone
    lb = lb.reshape(H // SS, SS, W // SS, SS).transpose(0, 2, 1, 3)
    lb = lb.reshape(H // SS, W // SS, SS * SS)
    return np.where((lb == lb[..., :1]).all(-1), lb[..., 0], -1)


def _sat(m):
    return (m.max() - m.min()) / max(m.max(), 1e-9)


def colour_table(img, reg):
    print("colour regression (sRGB medians; saturation = (max-min)/max)")
    for nm, k in (("riser face  ", 1), ("tread top   ", 2),
                  ("floor 1.40 m", 3), ("coping stone", 4)):
        sel = reg == k
        if sel.sum() < 100:
            print("  %s   -- %d px, not measured" % (nm, sel.sum()))
            continue
        med = np.median(img[sel].reshape(-1, 3), 0)
        print("  %s  (%3.0f,%3.0f,%3.0f)  sat %.2f   %6d px"
              % (nm, med[0], med[1], med[2], _sat(med), sel.sum()))
    # PAIRED, ROW BY ROW. Grazing angle and Fresnel are functions of the image
    # row, so the only way to say "the receiver is the difference" is to hold
    # the row fixed: take each region's median within a row, then the median of
    # those over the rows where both regions have enough pixels to have one.
    ok = ((reg == 1).sum(1) >= 20) & ((reg == 3).sum(1) >= 20)
    rows = np.flatnonzero(ok)
    if rows.size:
        pr = np.array([[np.median(img[r][reg[r] == k], 0) for k in (1, 3)]
                       for r in rows])
        a, b = np.median(pr[:, 0], 0), np.median(pr[:, 1], 0)
        print("  paired over the %d rows that hold both (%d-%d):" %
              (rows.size, rows[0], rows[-1]))
        print("     riser (%3.0f,%3.0f,%3.0f) sat %.2f   vs   open water "
              "(%3.0f,%3.0f,%3.0f) sat %.2f"
              % (a[0], a[1], a[2], _sat(a), b[0], b[1], b[2], _sat(b)))


REG = _regions()
colour_table(hero, REG)

mono = encode(render('mono'))
Image.fromarray(hero).save("pool_final.png")
print("wrote pool.png")

# A patch of sunlit floor between the camera and the step unit -- aimed by
# projecting the point, not by a remembered pixel index.
CW, CHh = 280, 190
_c = project([4.90, 1.60, -DEPTH])[0]
CX = int(np.clip(_c[0] - CW / 2, 0, W // SS - CW))
CY = int(np.clip(_c[1] - CHh / 2, 0, H // SS - CHh))
S = 3


def crop(a, label):
    im = Image.fromarray(a[CY:CY + CHh, CX:CX + CW]).resize((CW * S, CHh * S), Image.LANCZOS)
    return im


A, B = crop(mono, 'mono'), crop(hero, 'disp')
cmp = Image.new('RGB', (A.width * 2 + 18, A.height), (16, 18, 20))
cmp.paste(A, (0, 0)); cmp.paste(B, (A.width + 18, 0))
cmp.save("pool_final_dispersion.png")
# The zoom is aimed at the radius step, because that is where the claims under
# test are legible: three arc nosings displaced and undulating with the same
# slope field that writes the caustics, a tonal staircase from the shorter
# Beer-Lambert path over each tread, a shaded riser under each nosing carrying
# the bounce off the tread in front of it, and the unit's own cast shadow out on
# the floor. The rectangle is the projected bounding box of the three nosings
# plus the strip of floor outside them, so it follows the unit if it moves.
_zp = []
for (_cx, _cy, _R, _zt) in CYL[:3]:
    _a2 = np.linspace(np.pi, 2 * np.pi, 400)      # the half circle in the water
    _zp.append(np.stack([_cx + _R * np.cos(_a2), _cy + _R * np.sin(_a2),
                         np.full(400, _zt)], -1))
    _zp.append(np.stack([_cx + (_R + .35) * np.cos(_a2),
                         _cy + (_R + .35) * np.sin(_a2), np.full(400, -DEPTH)], -1))
_zpix = project(np.concatenate(_zp))
_zpix = _zpix[(_zpix[:, 0] > 0) & (_zpix[:, 0] < W // SS) &
              (_zpix[:, 1] > 0) & (_zpix[:, 1] < H // SS)]
ZX = int(np.clip(_zpix[:, 0].min() - 12, 0, W // SS - 40))
ZY = int(np.clip(_zpix[:, 1].min() - 12, 0, H // SS - 40))
ZW = int(np.clip(_zpix[:, 0].max() + 12, 0, W // SS) - ZX)
ZH = int(np.clip(_zpix[:, 1].max() + 12, 0, H // SS) - ZY)
print("zoom on the step unit: %dx%d px at (%d, %d)" % (ZW, ZH, ZX, ZY))
Image.fromarray(hero[ZY:ZY + ZH, ZX:ZX + ZW]).resize(
    (ZW * S, ZH * S), Image.LANCZOS).save("pool_final_zoom.png")
print("wrote pool_dispersion.png, pool_zoom.png")
