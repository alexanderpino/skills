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
#     rms (0.053 far, 0.092 over the jet) -- that is the ONLY band in which
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
EYE = np.array([9.40, 1.55, 1.85])    # east: the anti-solar side
CAM_AZ = np.deg2rad(176.6)            # anti-solar to 0.4 deg: see above
CAM_EL = np.deg2rad(-34.0)
FOV = np.deg2rad(46.0)
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
    WAO = .78 * (1.0 - .32 * np.exp(VV / .055))
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
def pool_s(x, y):
    """Outward distance from the pool rectangle in the max norm -- mitred corners,
    and convex, which is what lets the march below take its shortcut."""
    return np.maximum(np.abs(x - .5 * (X0 + X1)) - .5 * (X1 - X0),
                      np.abs(y - .5 * (Y0 + Y1)) - .5 * (Y1 - Y0))


def pool_grad(x, y):
    a = np.abs(x - .5 * (X0 + X1)) - .5 * (X1 - X0)
    b = np.abs(y - .5 * (Y0 + Y1)) - .5 * (Y1 - Y0)
    e = a >= b
    return (np.where(e, np.sign(x - .5 * (X0 + X1)), 0.),
            np.where(e, 0., np.sign(y - .5 * (Y0 + Y1))), e)


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
    alb = np.where(cop[:, None], np.array([.660, .604, .502])[None],
                   np.array([.618, .558, .466])[None])
    alb = alb * (1. + .46 * (t1 - .5))[:, None]
    alb = alb * (1. + np.stack([.20 * (t2 - .5), .03 * (t2 - .5), -.21 * (t2 - .5)], 1))
    alb = alb * (1. + .13 * (n1 - .5) + .11 * w2 * (n2 - .5) + .09 * w3 * (n3 - .5)
                 + .07 * w4 * (n4 - .5) + .05 * w5 * (n5 - .5))[:, None]
    alb = alb * (1. - .42 * jm)[:, None]
    alb = alb * (1. - .22 * jw * vnoise(x * 3.3 + 61., y * 3.3 + 41.))[:, None]
    alb = alb * (1. - .46 * wet)[:, None]

    # --- light
    L = SUN_DIR
    ndl = np.clip(Nx * L[0] + Ny * L[1] + Nz * L[2], 0, 1)
    vis = np.asarray(sun_vis(x, y), float)
    lift = SAIL_TAU * (1. - vis) * sail_glow(x, y)
    skyv = (.55 + .45 * Nz) * (1. - .40 * jm)
    col = alb * (SUN_COL[None] * (ndl * vis + SUN_DIR[2] * lift)[:, None] * .30
                 + SKY_DECK[None] * skyv[:, None])

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
# pool_s is convex, so on the segment it never exceeds its endpoints: both ends
# inside the lip proves the whole 75 mm of ray is over open water. 8 mm of slack
# covers the laid-stone wobble, which is not convex.
is_wat = down & (np.maximum(_sa, _sb) < SLIP - .008)
is_pav = down & (_sa >= SBUL + .008)       # already on the flat at the top plane
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
COP_REFL = np.array([.62, .57, .48]) * (SKY_AMB * .52 + SUN_COL * .034)
refl = refl * (1 - _occ)[:, None] + COP_REFL[None] * _occ[:, None]
LIP_AO = 1. - .34 * np.exp(-(IN_W + SLIP) / .045)
MENIS = np.exp(-np.maximum(IN_W + SLIP, 0.) / .010)
print("reflection of the coping occludes %.1f%% of the visible surface"
      % (100. * (_occ > .5).mean()))

PAV_COL = paving(hx[pav], hy[pav], S_HIT[pav], D[pav], FOOT[pav])


def render(mode):
    img = np.zeros((W * H, 3))
    img[hit_sail] = (np.array([.74, .72, .76])[None] *
                     (SKY_AMB[None] * 1.6 + SUN_COL[None] * .22))
    if bgm.any():
        img[bgm] = sky(D[bgm, 0], D[bgm, 1], np.abs(D[bgm, 2])) * .95
    img[pav] = PAV_COL
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
