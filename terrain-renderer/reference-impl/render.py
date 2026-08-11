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
DEPTH = 1.40
X0, X1, Y0, Y1 = 0.0, 8.0, 0.0, 4.0
W, H = 2000, 1340          # rendered at 2x, averaged down: glints are rare events
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
SAIL_TAU = 0.30          # shade fabric transmits ~15-20%, DIFFUSELY:
                         # it lifts the shadow without making caustics

# --- camera -----------------------------------------------------------------
# The reference is a CLOSE-UP over the water: the frame is water, the pool edge
# is a border at the top, and there is no garden in it. Two constraints fix the
# viewpoint and neither is free:
#   * the specular path.  A facet reflects the sun to the camera when its normal
#     bisects L and V.  With the sun at 21 deg and the camera due east of the
#     target, |theta_v - 21| < 12 deg keeps the required slope inside the field's
#     rms (0.053 far, 0.092 over the jet) -- that is the ONLY band in which
#     spec C's isolated glints can exist.  Look down at 60 deg and there is no
#     sparkle anywhere, at any roughness.
#   * the caustic net.  25-40 cells at 15-30 cm needs 4-8 m of water in frame.
# 2.55 m over the east coping, 29 deg down, 22 deg lens: the frame runs from the
# far coping (8.7 m, theta_v 16 deg) to 3.2 m out (theta_v 39 deg), so the glint
# band lands on the jet's rough patch and the far half stays turquoise.
EYE = np.array([8.30, 2.45, 2.55])    # east: the anti-solar side
CAM_AZ = np.deg2rad(183.5)            # very nearly due west: see above
CAM_EL = np.deg2rad(-27.5)
FOV = np.deg2rad(22.0)
TGT = EYE + 7.0 * np.array([np.cos(CAM_AZ) * np.cos(CAM_EL),
                            np.sin(CAM_AZ) * np.cos(CAM_EL), np.sin(CAM_EL)])
SAIL = np.array([[-5.10, -0.90, 2.72], [-2.10, -0.50, 2.55],
                 [-2.40, 1.90, 2.35], [-5.40, 1.50, 2.55]])
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
WET  =  0.155     # how far back from the lip the stone is still splash-damp
# A real pool liner is BLUE, not white plaster. Absolute albedo ~ (0.24, 0.54, 0.70):
# reflective enough to stay bright, saturated enough to carry the colour itself.
LINER_TINT = np.array([0.30, 0.79, 0.92])

rng = np.random.default_rng(20260810)

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


def box_hit(px, py, tx, ty, tz):
    """First hit of a downgoing ray in the pool box. 0=bed 1=x0 2=x1 3=y0 4=y1."""
    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.stack([
            np.where(tz < -1e-9, -DEPTH / tz, BIG),
            np.where(tx < -1e-9, (X0 - px) / tx, BIG),
            np.where(tx > 1e-9, (X1 - px) / tx, BIG),
            np.where(ty < -1e-9, (Y0 - py) / ty, BIG),
            np.where(ty > 1e-9, (Y1 - py) / ty, BIG)])
    s = np.where(np.isfinite(s), s, BIG)
    sid = np.argmin(s, 0).astype(np.int8)
    sm = np.take_along_axis(s, sid[None].astype(np.intp), 0)[0]
    hx, hy, hz = px + tx * sm, py + ty * sm, tz * sm
    u = np.where(sid == 0, hx, np.where(sid <= 2, hy, hx))
    v = np.where(sid == 0, hy, hz)
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
XLIP, YLIP = X0 - SLIP, Y1 + SLIP          # the lip, 20 mm proud of each face
_RUNX = ZLIP * abs(SUN_DIR[0]) / SUN_DIR[2]
_RUNY = ZLIP * abs(SUN_DIR[1]) / SUN_DIR[2]
_LPEN = np.deg2rad(0.53) * (ZLIP / SUN_DIR[2])     # sun disc over a 12 cm run
print("coping lip shades %.0f mm of water off the west wall, %.0f mm off the "
      "north wall (penumbra %.1f mm)" % (_RUNX * 1000, _RUNY * 1000, _LPEN * 1000))


def coping_vis(x, y):
    """Sun visibility at the water surface, cut by the coping lip itself."""
    return (np.clip((x - XLIP - _RUNX) / _LPEN + .5, 0, 1) *
            np.clip((YLIP - _RUNY - y) / _LPEN + .5, 0, 1))


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
sig_m = pen / 4.0 * 1.45          # 1.45x physical: the excess is variance reduction
for c in range(4):
    bed[c] = blur(bed[c], sig_m / ((X1 - X0) / CAU_NX))
    for wi in range(4):
        wall[wi][c] = blur(wall[wi][c], sig_m / ((Y1 - Y0) / WNU))
print("bed caustic: mean %.2f  p99 %.2f  max %.2f" %
      (bed[1].mean(), np.percentile(bed[1], 99), bed[1].max()))


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

    wl = v > -0.155                                        # waterline course
    gm = ((np.abs(((u / .048) % 1.) - .5) > .40) |
          ((np.abs(((v / .048) % 1.) - .5) > .40)))
    lev = np.where(wl, np.where(gm, .90, .62 + .10 * np.sin(u * 131.) * np.sin(v * 97.)),
                   lev)
    alb = np.where(wl[..., None],
                   (LINER_TINT * np.array([.60, .90, 1.03]))[None, None], alb)

    cal = np.exp(-((v + .0070) / .0055) ** 2)              # calcium, at mean level
    dirt = np.exp(-((v + .0235) / .0080) ** 2)             # surface film, just under
    lev = lev * (1 + .60 * cal) * (1 - .40 * dirt)
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


def shade(cau, alb, ao=1.0, glow=None):
    o = np.zeros(cau[0].shape + (3,))
    for c in range(3):
        ac = alb[..., c] if alb.ndim == 3 else alb
        amb = SKY_AMB[c] * ao
        if glow is not None:
            amb = amb + SAIL_TAU * SUN_COL[c] * SUN_DIR[2] * glow
        o[..., c] = ac * (SUN_COL[c] * cos_i * TSUN * cau[c] * np.exp(-ABS[c] * slant)
                           + amb * np.exp(-ABS[c] * DEPTH * 1.55))
    return o


BU, BV = np.meshgrid(np.linspace(X0, X1, CAU_NX), np.linspace(Y0, Y1, CAU_NY))
LIN = liner(BU, BV)
GLOW = sail_glow(BU, BV)
# The walls stand between the bed and half the sky, so the ambient term -- and
# only the ambient term, the caustic already knows about geometry -- falls off
# into the corners. 1 - 0.30 exp(-d/0.30) is a two-wall corner losing 60%.
_dw = np.minimum(np.minimum(BU - X0, X1 - BU), np.minimum(BV - Y0, Y1 - BV))
BED_AO = 1.0 - 0.30 * np.exp(-_dw / 0.30)
bed_img = {'disp': shade(bed[:3], LIN, BED_AO, glow=GLOW),
           'mono': shade([bed[3]] * 3, LIN, BED_AO, glow=GLOW)}
wall_img = {'disp': [], 'mono': []}
for wi in range(4):
    uu = np.linspace(Y0, Y1, WNU) if wi < 2 else np.linspace(X0, X1, WNU)
    UU, VV = np.meshgrid(uu, np.linspace(-DEPTH, 0.0, WNV))
    T = tiles(UU, VV)
    # the coping overhangs the wall by 20 mm, so the last few centimetres of wall
    # sit in its shade: the darkest thing in the pool is the line under the lip.
    WAO = .78 * (1.0 - .58 * np.exp(VV / .028))
    wall_img['disp'].append(shade(wall[wi][:3], T, WAO))
    wall_img['mono'].append(shade([wall[wi][3]] * 3, T, WAO))


def sample(img, u, v, u0, u1, v0, v1):
    nv, nu = img.shape[:2]
    fu = np.clip((u - u0) / (u1 - u0) * nu - .5, 0, nu - 1.001)
    fv = np.clip((v - v0) / (v1 - v0) * nv - .5, 0, nv - 1.001)
    iu, iv = fu.astype(np.int64), fv.astype(np.int64)
    du, dv = (fu - iu)[:, None], (fv - iv)[:, None]
    return ((img[iv, iu] * (1 - du) + img[iv, iu + 1] * du) * (1 - dv) +
            (img[iv + 1, iu] * (1 - du) + img[iv + 1, iu + 1] * du) * dv)


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


def ground(x, y, grass):
    v = np.asarray(sun_vis(x, y), float)[:, None]
    if grass:
        n = vnoise(x * 2.2, y * 2.2) * .6 + vnoise(x * 9., y * 9.) * .4
        alb = np.array([.14, .29, .10])[None] * (.78 + .44 * n)[:, None]
    else:
        n = vnoise(x * 1.6, y * 1.6) * .7 + vnoise(x * 7.5, y * 7.5) * .3
        j = ((np.abs(((x / .62) % 1.) - .5) > .478) |
             (np.abs(((y / .62) % 1.) - .5) > .478)).astype(float)
        alb = (np.array([.63, .51, .41])[None] * (.88 + .14 * n)[:, None]
               * (1 - .14 * j)[:, None])
    lift = SAIL_TAU * (1.0 - v) * sail_glow(x, y)[:, None]
    return alb * (SUN_COL[None] * SUN_DIR[2] * (v + lift) * .30 + SKY_AMB[None] * .88)


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

with np.errstate(divide='ignore', invalid='ignore'):
    sd = (0.055 - EYE[2]) / D[:, 2]
    sw = (0.0 - EYE[2]) / D[:, 2]
pdx, pdy = EYE[0] + D[:, 0] * sd, EYE[1] + D[:, 1] * sd
pwx, pwy = EYE[0] + D[:, 0] * sw, EYE[1] + D[:, 1] * sw
down = (D[:, 2] < 0) & ~hit_sail
inp = down & (pwx > X0) & (pwx < X1) & (pwy > Y0) & (pwy < Y1)
DK = (X0 - 1.7, X1 + 1.7, Y0 - 1.5, Y1 + 2.1)
GR = (X0 - 6., X1 + 6., Y0 - 3., Y1 + 6.)
dk = down & ~inp & (pdx > DK[0]) & (pdx < DK[1]) & (pdy > DK[2]) & (pdy < DK[3])
gr = down & ~inp & ~dk & (pdx > GR[0]) & (pdx < GR[1]) & (pdy > GR[2]) & (pdy < GR[3])
bgm = ~hit_sail & ~inp & ~dk & ~gr

ix, iy = pwx[inp], pwy[inp]
gxx, gyy = grad_points(ix, iy)
nx, ny, nz = normal_from_grad(gxx, gyy)
dd = D[inp]
vx, vy, vz = -dd[:, 0], -dd[:, 1], -dd[:, 2]
ndv = np.clip(nx * vx + ny * vy + nz * vz, 1e-4, 1.)
refl = sky(-vx + 2 * ndv * nx, -vy + 2 * ndv * ny, np.abs(-vz + 2 * ndv * nz))
fres = F0[None] + (1 - F0[None]) * ((1 - ndv) ** 5)[:, None]


def render(mode):
    img = np.zeros((W * H, 3))
    img[hit_sail] = (np.array([.74, .72, .76])[None] *
                     (SKY_AMB[None] * 1.6 + SUN_COL[None] * .22))
    img[bgm] = sky(D[bgm, 0], D[bgm, 1], np.abs(D[bgm, 2])) * .95
    img[dk] = ground(pdx[dk], pdy[dk], False)
    img[gr] = ground(pdx[gr], pdy[gr], True)
    water = np.zeros((inp.sum(), 3))
    bi, wim = bed_img[mode], wall_img[mode]
    for c in range(3):
        eta = 1.0 / (IOR[c] if mode == 'disp' else IOR[1])
        tx, ty, tz = refract(dd[:, 0], dd[:, 1], dd[:, 2], nx, ny, nz, eta)
        sid, u, v, sm = box_hit(ix, iy, tx, ty, tz)
        col = np.zeros(len(u))
        m = sid == 0
        if m.any():
            col[m] = sample(bi[..., c:c + 1], u[m], v[m], X0, X1, Y0, Y1)[:, 0]
        for wi, sv in enumerate((1, 2, 3, 4)):
            m = sid == sv
            if m.any():
                a, b = (Y0, Y1) if sv <= 2 else (X0, X1)
                col[m] = sample(wim[wi][..., c:c + 1], u[m], v[m], a, b, -DEPTH, 0.)[:, 0]
        water[:, c] = col * np.exp(-ABS[c] * sm)
    water += np.array([.002, .011, .019])[None] * (1 - np.exp(-.30 * DEPTH))
    img[inp] = fres * refl + (1 - fres) * water
    return img.reshape(H, W, 3)


def encode(hdr):
    hdr = hdr.reshape(H // 2, 2, W // 2, 2, 3).mean((1, 3))
    x = hdr * EXPOSURE
    a, b, c, d, e = 2.51, .03, 2.43, .59, .14
    x = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    x = np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)
    x = np.clip(x, 0, 1)
    lum = (x * np.array([.2126, .7152, .0722])).sum(-1, keepdims=True)
    x = np.clip(lum + (x - lum) * 1.06, 0, 1)              # saturation, display-side
    #  1.06, not 1.22: with a blue liner the saturation is physical, not graded
    x = np.clip((x - .5) * 1.10 + .5 + .012, 0, 1)          # gentle S, display-side
    return (x * 255 + .5).astype(np.uint8)


hero = encode(render('disp'))
mono = encode(render('mono'))
Image.fromarray(hero).save("pool_final.png")
print("wrote pool.png")

CX, CY, CW, CHh = 430, 330, 300, 200
S = 3


def crop(a, label):
    im = Image.fromarray(a[CY:CY + CHh, CX:CX + CW]).resize((CW * S, CHh * S), Image.LANCZOS)
    return im


A, B = crop(mono, 'mono'), crop(hero, 'disp')
cmp = Image.new('RGB', (A.width * 2 + 18, A.height), (16, 18, 20))
cmp.paste(A, (0, 0)); cmp.paste(B, (A.width + 18, 0))
cmp.save("pool_final_dispersion.png")
Image.fromarray(hero[CY:CY + CHh, CX:CX + CW]).resize(
    (CW * S, CHh * S), Image.LANCZOS).save("pool_final_zoom.png")
print("wrote pool_dispersion.png, pool_zoom.png")
