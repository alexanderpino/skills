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

EYE = np.array([13.00, 2.40, 6.60])   # east: the anti-solar side
TGT = np.array([3.60, 2.05, -0.30])
FOV = np.deg2rad(44.0)
SAIL = np.array([[-5.10, -0.90, 2.72], [-2.10, -0.50, 2.55],
                 [-2.40, 1.90, 2.35], [-5.40, 1.50, 2.55]])
EXPOSURE = 0.275      # the camera exposes for a 21-degree sun
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
def _cw(p):
    return sum((p[(i + 1) % len(p)][0] - p[i][0]) *
               (p[(i + 1) % len(p)][1] + p[i][1]) for i in range(len(p))) > 0


SAIL_SHADOW_POLY = SAIL[:, :2] - SUN_DIR[:2][None] * (SAIL[:, 2:3] / SUN_DIR[2])
_SCW = _cw(SAIL_SHADOW_POLY)


def sun_vis_hard(x, y):
    inside = np.ones(np.shape(x), bool)
    p = SAIL_SHADOW_POLY
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        cr = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        inside &= (cr <= 0) if _SCW else (cr >= 0)
    return (~inside).astype(np.float32)


# soft shadow: penumbra = 0.53 deg over the sail's slant height above the water
_pen = np.deg2rad(0.53) * (SAIL[:, 2].mean() / SUN_DIR[2])
SX = np.linspace(X0 - 3, X1 + 3, SHADOW_N[0])
SY = np.linspace(Y0 - 3, Y1 + 3, SHADOW_N[1])
_sxg, _syg = np.meshgrid(SX, SY)
SHADOW = blur(sun_vis_hard(_sxg, _syg).astype(np.float64),
              (_pen / 4.0) / ((SX[-1] - SX[0]) / SHADOW_N[0]))
print("sail penumbra at the water: %.0f mm" % (_pen * 1000))


def sun_vis(x, y):
    fu = np.clip((x - SX[0]) / (SX[-1] - SX[0]) * SHADOW_N[0] - .5, 0, SHADOW_N[0] - 1.001)
    fv = np.clip((y - SY[0]) / (SY[-1] - SY[0]) * SHADOW_N[1] - .5, 0, SHADOW_N[1] - 1.001)
    iu, iv = fu.astype(np.int64), fv.astype(np.int64)
    du, dv = fu - iu, fv - iv
    return ((SHADOW[iv, iu] * (1 - du) + SHADOW[iv, iu + 1] * du) * (1 - dv) +
            (SHADOW[iv + 1, iu] * (1 - du) + SHADOW[iv + 1, iu + 1] * du) * dv)


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
    g = ((np.abs(((u / .20) % 1.) - .5) > .445) | (np.abs(((v / .20) % 1.) - .5) > .445))
    base = (0.82 + .04 * np.sin(u * 17.) * np.sin(v * 21.)) * (1 - g) + .70 * g
    return base[..., None] * LINER_TINT[None, None]


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
bed_img = {'disp': shade(bed[:3], LIN, glow=GLOW),
           'mono': shade([bed[3]] * 3, LIN, glow=GLOW)}
wall_img = {'disp': [], 'mono': []}
for wi in range(4):
    uu = np.linspace(Y0, Y1, WNU) if wi < 2 else np.linspace(X0, X1, WNU)
    UU, VV = np.meshgrid(uu, np.linspace(-DEPTH, 0.0, WNV))
    T = tiles(UU, VV)
    wall_img['disp'].append(shade(wall[wi][:3], T, .78))
    wall_img['mono'].append(shade([wall[wi][3]] * 3, T, .78))


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
