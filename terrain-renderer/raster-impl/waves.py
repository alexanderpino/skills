"""The wave surface on the flat datum, and the two ways to filter it.

`12-water-rendering.md`, *Distance and filtering: why far water turns to
plastic* and *Pick the kernel on purpose, and give the variance a receiver*.
Before this file those two sections had no code behind them anywhere in this
directory: the datum was flat in both the pass and the offline frame, so nothing
here could exhibit a slope distribution, let alone lose one.

WHAT THE CHAPTER CLAIMS, in its own terms
  * As distance grows the number of waves inside a pixel footprint grows without
    bound. Normals computed from the surface converge to the MEAN normal --
    vertical -- and "all the slope variance those waves carried is silently
    discarded". The specular lobe collapses toward a Dirac and the far water
    reads as plastic.
  * "The fix is to move the variance rather than lose it": what leaves the
    resolved field is accumulated into a 2x2 slope-variance tensor that widens
    the BRDF lobe, so the SAME quantity moves between representations.
  * The hand-off has two named subtleties. What was removed is a TENSOR, not a
    scalar. And the map from slope covariance to reflected-lobe covariance is
    NOT the identity: `C = J S J^T` with `J = diag(-2, -2 cos theta_v)` in the
    view-azimuth frame.

WHAT IS IMPORTED AND NEVER COPIED
  * `field.grad_points(x, y, fp)` -- the narrowed slope field. The footprint
    kernel, its Gaussian family and its `sqrt(2 ln 2)/pi` scale are all derived
    inside `field.py` and this file does not restate them; it passes `fp` in
    metres and reads what comes back.
  * `field.slope_var_points(x, y, fp)` -- THE REMOVED-VARIANCE TENSOR, which
    already exists there for exactly this purpose and is not reimplemented here.
  * `atmosphere.sky(..., cov=...)` -- THE RECEIVER. `atmosphere._lobe_shape`
    already convolves each `cos^n` environment lobe with a reflection ellipse
    and writes the result back as a DIRECTIONAL `n_eff`, with the peak falling
    by `sqrt(det Q0 / det Q)` so the integral is conserved. That is the
    chapter's "convolving that into a `cos^n` lobe is closed-form"; it ships,
    and this file feeds it rather than growing a second copy.
  * `optics.fresnel` for the exact interface, `sswater.water_shade` for the
    transmitted half and the whole radiometric composition.

WHAT IS DERIVED HERE, and it is two things, both beside themselves below:
  1. `pixel_footprint` -- the scalar footprint a screen-space pass can actually
     form, from the SCREEN-SPACE DERIVATIVES of the water hit point, at 2x2 quad
     granularity because that is the granularity a GPU has. The anisotropy it
     has to throw away is returned beside it, because that is where the whole
     approximation runs out (see `README`).
  2. `refl_ellipse` -- the chapter's `C = J S J^T`, written out, with a
     Monte-Carlo row on it in `validate_raster.py` rather than a citation.

THE THREE PATHS, and they are the experiment:

  'point'     No filter at all. `fp=None`, one slope sample per pixel, the full
              field. This is the moire end of the same trade -- the chapter's
              "a band is still sampled at a footprint wider than itself".
  'naive'     The filtered field, and NOTHING ELSE. `field.grad_points(x,y,fp)`
              narrows the slope distribution with distance and the variance it
              removes is dropped on the floor. This is the plastic end, and it
              is what "mip the normal map and let the specular lobe read
              whatever it reads" does. NOTE that this is the CHARITABLE naive
              path: `field.py`'s filter attenuates AMPLITUDE per component,
              which is a better prefilter than a normal-map mip chain, and a
              real mip is measured separately (`mip_normals` below) and is
              worse again.
  'variance'  The filtered field PLUS `slope_var_points` folded into the lobe
              through `refl_ellipse` and into the Fresnel through Bruneton's
              roughness factor. The chapter's fix, complete.

MEASURE IN SCENE-LINEAR. Everything here is radiance and nothing goes near a
tone map. NOTHING IS AUTHORED: every wave in this file comes out of `field.py`'s
analytic band sums, and this file contains no texture, no noise and no table of
numbers that is not derived on the line above it.
"""
import sys as _sys
import os as _os
import io as _io
import contextlib as _ctx

import numpy as np

_REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                     '..', 'reference-impl')
if _REF not in _sys.path:
    _sys.path.insert(0, _REF)

import optics as OPT                                            # noqa: E402
import atmosphere as ATM                                        # noqa: E402
import field as FLD                                             # noqa: E402

import scene as SC                                              # noqa: E402
import sswater as WA                                            # noqa: E402
import lut as LUT                                               # noqa: E402


# --------------------------------------------------------------- field set-up
# `field.py` normalises the NEAR band and traces the wake inside `_norm_jets`,
# which `render.py` calls at line 1228 and `validate.py` at line 4137 -- i.e. it
# is part of the module's construction and not an optional report. It is called
# here for the same reason and exactly once. It PRINTS (a Dutch slope-budget
# table), and a module that prints on import is what keeps `render.py` out of
# this directory, so the print is captured rather than inherited.
_INIT = {}


def init_field():
    """Idempotent. Returns the captured slope-budget report so a caller can put
    it in front of a reader instead of losing it.

    CALLING IT IS NOT OPTIONAL AND NOTHING SAYS SO. `field._SC['near']` ships at
    1.0 and `_norm_jets` sets it to 0.001011 -- so a consumer that imports
    `field` and calls `grad_points` without this gets the NEAR band at 989x its
    calibrated amplitude, silently, with the field's own rms slope reading 0.99
    instead of 0.049. There is no guard on it and no exception; the numbers are
    simply wrong, and they are wrong in the band that carries the basin's long
    waves. Every entry point in this directory that samples the field calls this
    first for that reason (see `wave_pass`, `waveref.reference`)."""
    if 'txt' not in _INIT:
        buf = _io.StringIO()
        with _ctx.redirect_stdout(buf):
            FLD._norm_jets()
        _INIT['txt'] = buf.getvalue()
    return _INIT['txt']


def band_rms(F):
    """A plane-wave band's rms slope, through `field.py`'s OWN analytic
    convention function. The file's rule is that nobody writes the rms
    expression out by hand -- that is how two conventions once coexisted there,
    one of them a factor sqrt(2) into the water -- so this goes through
    `_plane_rms` even though it is underscore-named. Slope amplitude of a
    component is `amp * |k|`."""
    return float(FLD._plane_rms(F['amp'] * np.sqrt(F['k2'])))


def stationary_rms():
    """The rms slope of the two bands that are STATIONARY over the whole plane
    -- WIND (times the sail's shelter, which tends to 1.0 far from the sail) and
    REVERB. Independent bands, so they add in quadrature.

    This matters because the frame below puts water out to 2.4 km while
    `field.py`'s basin is 8 x 4 m. NEAR, BOIL and WAKE are all localised: NEAR
    falls as 1/sqrt(r), BOIL rides `jet_envelope`, and the WAKE is a grid whose
    lookup CLAMPS outside the basin -- so the honest question is what those
    three contribute out there, and the answer is measured in the suite against
    this number rather than assumed. (Measured: the wake is 0.0000 everywhere
    outside the basin, because the film damping kills it inside it.)"""
    return float(np.hypot(band_rms(FLD.WIND), band_rms(FLD.REVERB)))


# ------------------------------------------------------- 1. THE FOOTPRINT
# WHAT A SCREEN-SPACE PASS CAN ACTUALLY FORM, and it is not the pixel's true
# footprint. A pixel's footprint on the water is the image of the pixel SQUARE
# under the ray-plane map: a parallelogram, oriented, with two different axis
# lengths. `field.py` takes a SCALAR `fp` because its kernel is the isotropic
# Gaussian, "all a scalar footprint with no orientation is entitled to assume".
# So a scalar has to be chosen out of a 2x2 Jacobian, and there is exactly one
# defensible choice: the two singular values s1 >= s2 of
#
#     J = [ dP/dx_pixel , dP/dy_pixel ]        (2 x 2, in the datum plane)
#
# are the footprint's two axes, their PRODUCT is |det J| = the footprint's area,
# and the isotropic footprint carrying the same area is
#
#     fp = sqrt(|det J|) = sqrt(s1 s2),
#
# the GEOMETRIC MEAN of the two axes. Not the max (which over-blurs the whole
# far field by the anisotropy, which reaches 805 in this frame), not the min
# (which under-filters along the view and puts the moire straight back), and not
# the arithmetic mean (which is not what an area-matched Gaussian is). The ratio
# s1/s2 is returned beside it because the error of this whole scheme is a
# function of it and the README prices that.
#
# THE DERIVATIVES ARE QUAD DERIVATIVES. A GPU has no per-pixel derivative: it
# has `ddx`/`ddy` over the 2x2 shading quad, one value shared by four lanes.
# Reproducing that is not pedantry -- it is why the horizon row of this frame
# has no usable footprint at all (the quad straddles the plane's vanishing line
# and one lane's `t` is negative or infinite), and a pass that computed a
# per-pixel analytic footprint instead would not have that failure and would not
# be a shader. Those quads are FLAGGED, not silently clamped.
def quad_ddxy(P):
    """`ddx`/`ddy` of a per-pixel quantity at 2x2 quad granularity -- the
    forward difference inside each quad, broadcast to all four of its lanes.
    `P` is (H, W, ...) and the result is two arrays of the same shape."""
    H, W = P.shape[:2]
    ix0 = (np.arange(W) // 2) * 2
    ix1 = np.minimum(ix0 + 1, W - 1)
    iy0 = (np.arange(H) // 2) * 2
    iy1 = np.minimum(iy0 + 1, H - 1)
    return P[:, ix1] - P[:, ix0], P[iy1] - P[iy0]


def quad_all(mask):
    """True where ALL FOUR lanes of the 2x2 shading quad are true. A quad
    derivative is only meaningful when every lane of the quad has a value, and
    on the horizon row of a water pass it does not."""
    H, W = mask.shape
    ix0 = (np.arange(W) // 2) * 2
    ix1 = np.minimum(ix0 + 1, W - 1)
    iy0 = (np.arange(H) // 2) * 2
    iy1 = np.minimum(iy0 + 1, H - 1)
    m = mask[:, ix0] & mask[:, ix1]
    return m[iy0] & m[iy1]


def pixel_footprint(gbuf, t, d, water):
    """(fp, aniso, ok, P) for every pixel: the area-matched isotropic footprint
    in metres, the footprint parallelogram's axis ratio, whether the quad's four
    lanes all hit the datum, and the hit point itself.

    `ok=False` is the horizon quad -- one lane of it looks above the datum, so
    `t` is negative there and the quad derivative is not a footprint at all.
    There is no correct scalar in that quad and the pass says so rather than
    inventing one; the count is a suite row and the patch is excluded from every
    number the way `12`'s occluder silhouettes are."""
    eye = gbuf['eye']
    good = np.isfinite(t) & (t > 0)
    tt = np.where(good, t, np.nan)
    P = eye[None, None] + tt[..., None] * d
    dx, dy = quad_ddxy(P[..., :2])
    det = np.abs(dx[..., 0] * dy[..., 1] - dx[..., 1] * dy[..., 0])
    frob = (dx ** 2).sum(-1) + (dy ** 2).sum(-1)
    # singular values of a 2x2: s1^2 + s2^2 = ||J||_F^2 and s1 s2 = |det J|
    disc = np.sqrt(np.maximum(frob ** 2 - 4.0 * det ** 2, 0.0))
    s1 = np.sqrt(np.maximum(0.5 * (frob + disc), 0.0))
    s2 = np.sqrt(np.maximum(0.5 * (frob - disc), 0.0))
    fp = np.sqrt(det)
    ok = quad_all(good) & water & np.isfinite(fp) & (fp > 0)
    aniso = s1 / np.maximum(s2, 1e-12)
    return (np.where(ok, fp, 0.0), np.where(ok, aniso, 1.0), ok,
            np.where(np.isfinite(P), P, 0.0))


def analytic_footprint(t, cos_a, res=SC.RES, fov=SC.FOV):
    """The same quantity in closed form, for the suite to check the derivative
    path against: a pixel subtends `dth = 2 tan(fov/2)/H` at the eye, the
    across-view axis of the footprint is `t*dth` and the along-view axis is
    `t*dth/cos_a` (the plane is raked by the view), so the area is
    `t^2 dth^2 / cos_a` and the area-matched isotropic footprint is

        fp = t * dth / sqrt(cos_a),        aniso = 1 / cos_a.

    Leading order in `dth` -- it ignores the pinhole's own foreshortening across
    the frame -- so it is an ASYMPTOTIC check and the suite states the order."""
    dth = 2.0 * np.tan(0.5 * fov) / res[1]
    c = np.maximum(np.asarray(cos_a, float), 1e-12)
    return np.asarray(t, float) * dth / np.sqrt(c), 1.0 / c


# ------------------------------------- 2. SLOPE COVARIANCE -> LOBE COVARIANCE
# THE CHAPTER'S OWN SENTENCE, AND WHY IT IS NOT THE IDENTITY:
#
#   "An in-plane slope perturbation swings the reflected ray by 2d, an
#    out-of-plane one by 2d cos(theta_v) with theta_v measured from the surface
#    normal -- so C = J S J^T with J = diag(-2, -2 cos theta_v) in the
#    view-azimuth frame."
#
# Derived rather than quoted, because the two factors of two are the content.
# Let the resolved normal be n, the view direction toward the eye be v, and the
# unresolved slope be a zero-mean 2-vector `delta` with covariance SIGMA (that
# IS what `slope_var_points` returns). The normal tilts by -delta to first
# order, and R = 2(n.v)n - v gives dR = 2(dn.v) n + 2(n.v) dn. Put the incidence
# plane in x-z with n = z_hat and v = (sin tv, 0, cos tv):
#   * delta IN the incidence plane: dR = -2 delta_p e_hat. The full factor of
#     two -- the tilt swings the normal and the incidence angle together.
#   * delta ACROSS it: dR = -2 cos(tv) delta_q s_hat. Foreshortened, because an
#     out-of-plane tilt only rolls the ray about the view direction.
# So in the frame (in-plane, across-plane) the map is diag(-2, -2 cos tv) and
# C = J SIGMA' J^T where SIGMA' is SIGMA rotated into that frame.
#
# THE FRAME THE ANSWER IS WANTED IN is the two directions perpendicular to R:
# `s_hat` normal to the incidence plane and `e_hat` completing the triad. The
# offset to the sun is then just its two components there and no angle is ever
# formed -- which is the interface `atmosphere._lobe_shape` already takes.
#
# THE SQRT(2) TRAP LIVES IN THE OTHER RETURN VALUE. `sigma_v^2` for the
# roughness-Fresnel is the chapter's "ONE-DIRECTION variance, not s^2": the
# component of SIGMA along the view azimuth, `p^T SIGMA p`. The trace
# `vxx + vyy` is the TOTAL mean-square slope -- `field.py`'s one convention --
# and it is larger by a factor of two for an isotropic field, i.e. sqrt(2) in
# the rms that Bruneton's fit is written in. Using the trace here is exactly the
# mixed-convention defect `field.py`'s header block exists to prevent, arriving
# from the consumer's side instead of the producer's. It is priced in the suite.
def refl_ellipse(dvec, nx, ny, nz, vxx, vyy, vxy):
    """(u1, u2, c11, c12, c22, sigma_v2, ndv).

    `dvec` (...,3) is the VIEW ray (from the eye toward the water, so `v = -d`),
    `n` the resolved surface normal, and (vxx, vyy, vxy) the removed slope
    covariance from `field.slope_var_points`. The first five are exactly what
    `atmosphere.sky(..., cov=...)` consumes."""
    vx, vy, vz = -dvec[..., 0], -dvec[..., 1], -dvec[..., 2]
    ndv = np.clip(nx * vx + ny * vy + nz * vz, 1e-4, 1.0)
    rx, ry = -vx + 2.0 * ndv * nx, -vy + 2.0 * ndv * ny
    rz = np.abs(-vz + 2.0 * ndv * nz)      # folded, as the sky lookup is
    # s_hat: the incidence plane's normal, re-orthogonalised against the folded R
    s0x = vy * nz - vz * ny
    s0y = vz * nx - vx * nz
    s0z = vx * ny - vy * nx
    dot = s0x * rx + s0y * ry + s0z * rz
    s0x, s0y, s0z = s0x - dot * rx, s0y - dot * ry, s0z - dot * rz
    inv = 1.0 / np.maximum(np.sqrt(s0x ** 2 + s0y ** 2 + s0z ** 2), 1e-9)
    sx, sy, sz = s0x * inv, s0y * inv, s0z * inv
    ex, ey, ez = ry * sz - rz * sy, rz * sx - rx * sz, rx * sy - ry * sx
    # SIGMA rotated into (along the view azimuth p, across it q). q = (py, -px)
    # rather than (-py, px) so that it points along s_hat; the sign of the cross
    # term is the only place that choice shows.
    ph = np.maximum(np.hypot(vx, vy), 1e-9)
    px, py = vx / ph, vy / ph
    a = px * px * vxx + 2.0 * px * py * vxy + py * py * vyy     # in-plane
    b = py * py * vxx - 2.0 * px * py * vxy + px * px * vyy     # across
    cr = px * py * (vxx - vyy) + (py * py - px * px) * vxy
    c11 = 4.0 * a
    c12 = 4.0 * ndv * cr
    c22 = 4.0 * ndv * ndv * b
    u1 = ATM.SUN_DIR[0] * ex + ATM.SUN_DIR[1] * ey + ATM.SUN_DIR[2] * ez
    u2 = ATM.SUN_DIR[0] * sx + ATM.SUN_DIR[1] * sy + ATM.SUN_DIR[2] * sz
    return u1, u2, c11, c12, c22, a, ndv


# Cause two on the chapter's own list, and the half that keeps the far horizon
# off 100% mirror: Fresnel is derived for a SMOOTH interface and microfacet
# masking lowers it on a rough one. Bruneton, Neyret & Holzschuch (2010), quoted
# by `12` for `sigma_v < 0.5`:
#     F = R + (1-R) (1-cos tv)^5 exp(-2.69 s_v) / (1 + 22.7 s_v^1.5)
# `12` then says in the same section that `(1-cos tv)^5` is Schlick and that
# Schlick is wrong for water by -22.8% at 51.3 deg and +14.3% at 79 deg -- so
# the factor is applied to the EXACT interface's grazing rise above F0 instead,
#     F = F0 + (F_exact(cos tv) - F0) * r,
# which the chapter also states and which keeps both limits exact: r -> 1 gives
# `optics.fresnel` untouched, r -> 0 gives F0. Two constants, both Bruneton's,
# neither fitted here. It is fed the UNRESOLVED variance only, so it is the
# identity wherever the footprint resolves the surface.
F0 = OPT.fresnel(np.array([1.0]))[0]


def fresnel_rough(ndv, sigma_v2):
    sv = np.sqrt(np.maximum(sigma_v2, 0.0))
    r = (np.exp(-2.69 * sv) / (1.0 + 22.7 * sv ** 1.5))[..., None]
    return F0[None] + (OPT.fresnel(ndv) - F0[None]) * r


# ------------------------------------------------------------ 3. THE SHADING
# ------------------------------------------- THE RECEIVER, AND ONE CORRECTION
# `atmosphere._lobe_shape` already does the chapter's closed form -- "two
# Gaussians convolve to a Gaussian, covariances add, the integral is conserved
# (so the peak falls by sqrt(det Q0/det Q)), and writing the result back as a
# DIRECTIONAL n_eff keeps the anisotropy". It is the receiver this pass wants
# and it is imported. IT IS ALSO WRONG FOR AN ANISOTROPIC COVARIANCE, and this
# frame's covariance is anisotropic by four orders of magnitude, so the
# correction is written out here and the shipped form is kept beside it so the
# suite can price the difference rather than assert it. NOT PATCHED: `atmosphere.py`
# is a shared module and a fix belongs in a round that can re-run everything
# that reads it.
#
# THE DEFECT, IN ONE LINE. For a summed covariance Q, the value of the
# convolved lobe at angular offset `rho` along the unit direction `u` is
#     exp(-rho^2/2 * u^T Q^-1 u)      -- the density, so the INVERSE form
# and `cos^n(rho) ~ exp(-n rho^2/2)` therefore wants `n_eff = u^T Q^-1 u`.
# `_lobe_shape` returns `n_eff = 1/(u^T Q u)` -- the PROJECTION variance, which
# is the width of the shadow the Gaussian casts on the u axis and not its value
# along it. The two are identical when Q is isotropic (and equal on either
# principal axis), which is why nothing caught it: `render.py`'s pool camera
# sits 33 deg above the horizontal, where the ellipse's axis ratio 1/cos^2 is
# about 3, and the error there is a 1.2-1.7x brightening that reads as taste.
# By Cauchy-Schwarz `1/(u^T Q u) <= u^T Q^-1 u` always, so the shipped lobe is
# never too narrow, always too wide, and since the peak factor `g` was computed
# for the CORRECT Gaussian the widened lobe no longer integrates to the lobe it
# replaced: it CREATES ENERGY, monotonically in the anisotropy. Measured over
# the sphere against the unwidened `2 pi/(n+1)`:
#     axis ratio     1      4      10     1e4
#     shipped     1.01x  1.24x  1.68x  10.4x
#     inverted    1.02x  1.00x  1.00x   1.00x
# (`validate_raster.tier1_lobe_energy`, recomputed there, not transcribed.)
#
#     u^T Q^-1 u = (u1^2 q22 - 2 u1 u2 q12 + u2^2 q11) / (|u|^2 det Q)
#
# -- the same three terms with q11 and q22 swapped and the cross term's sign
# flipped, i.e. the 2x2 adjugate. That is the whole repair.
def widened_lobes(lobes, cov):
    """`atmosphere.sky`'s `lobes` argument, with each `cos^n` already convolved
    with the reflection ellipse `cov = (u1, u2, c11, c12, c22)`.

    Feeding the shipped `sky` a per-pixel amplitude and a per-pixel exponent is
    how the correction is applied WITHOUT a second copy of the environment: the
    horizon/zenith gradient, the lobe amplitudes, the 1.15 and the partition
    into disc and aureole all stay `atmosphere.py`'s."""
    if cov is None:
        return lobes
    u1, u2, c11, c12, c22 = cov
    r2 = u1 * u1 + u2 * u2
    out = []
    for amp, n, L in lobes:
        q11 = 1.0 / n + c11
        q22 = 1.0 / n + c22
        det = np.maximum(q11 * q22 - c12 * c12, 1e-300)
        g = (1.0 / n) / np.sqrt(det)
        num = u1 * u1 * q22 - 2.0 * u1 * u2 * c12 + u2 * u2 * q11
        # on the lobe's own axis every direction gives cos^n = 1, so the
        # fallback is the mean of u^T Q^-1 u over directions, tr(Q^-1)/2.
        ne = np.where(r2 > 1e-16, num / np.maximum(r2, 1e-16) / det,
                      0.5 * (q11 + q22) / det)
        out.append((amp * np.asarray(g)[..., None], ne, L))
    return out


def sky_and_sun(dx, dy, dz, cov=None, receiver='inverted'):
    """(the whole environment, the sun DISC lobe's contribution alone).

    The disc term is the difference of two calls to the shipped `atmosphere.sky`
    -- the full lobe set and `SKY_DIFFUSE_LOBES`, the partition `atmosphere.py`
    already draws for its own illuminants -- so it adds no model of its own. It
    is the quantity the chapter's "the specular response collapses toward a
    Dirac" is a statement about, isolated so that the collapse can be measured
    rather than inferred from a composite.

    `receiver='shipped'` hands the covariance to `atmosphere._lobe_shape`
    instead, which is the defect above, kept so the suite can price it."""
    if cov is None:
        full = ATM.sky(dx, dy, dz, None, lobes=ATM.SKY_LOBE)
        nodisc = ATM.sky(dx, dy, dz, None, lobes=ATM.SKY_DIFFUSE_LOBES)
    elif receiver == 'shipped':
        full = ATM.sky(dx, dy, dz, cov, lobes=ATM.SKY_LOBE)
        nodisc = ATM.sky(dx, dy, dz, cov, lobes=ATM.SKY_DIFFUSE_LOBES)
    else:
        full = ATM.sky(dx, dy, dz, None,
                       lobes=widened_lobes(ATM.SKY_LOBE, cov))
        nodisc = ATM.sky(dx, dy, dz, None,
                         lobes=widened_lobes(ATM.SKY_DIFFUSE_LOBES, cov))
    return full, full - nodisc


def surface_shade(dvec, gx, gy, cov_in=None, receiver='inverted',
                  fresnel='rough'):
    """The reflected half of a water pixel with a wave normal on the flat datum.

    Returns (L_refl, L_sun, R, ndv, refl_dir). `cov_in` is `(vxx, vyy, vxy)` from
    `field.slope_var_points`, or None for the paths that discard it -- and at
    None every expression below degenerates EXACTLY to the mirror the flat pass
    already had, which is the property the chapter insists on ("a filtered path
    that does not reduce exactly to the unfiltered one is a second shading
    model")."""
    nx, ny, nz = FLD.normal_from_grad(gx, gy)
    vx, vy, vz = -dvec[..., 0], -dvec[..., 1], -dvec[..., 2]
    ndv = np.clip(nx * vx + ny * vy + nz * vz, 1e-4, 1.0)
    rx, ry = -vx + 2.0 * ndv * nx, -vy + 2.0 * ndv * ny
    rz = np.abs(-vz + 2.0 * ndv * nz)
    rn = 1.0 / np.maximum(np.sqrt(rx * rx + ry * ry + rz * rz), 1e-12)
    rx, ry, rz = rx * rn, ry * rn, rz * rn
    if cov_in is None:
        cov, R = None, OPT.fresnel(ndv)
    else:
        u1, u2, c11, c12, c22, sv2, _ = refl_ellipse(dvec, nx, ny, nz, *cov_in)
        cov = (u1, u2, c11, c12, c22)
        # THE FIX HAS TWO HALVES AND THEY ARE PRICED SEPARATELY. The lobe
        # widening is a derivation; the roughness-Fresnel is a FIT, and it is
        # the only fitted thing in the whole doctrine. `fresnel='exact'` keeps
        # the widening and drops the fit, which is the only way to say which of
        # the two carries the residual error. See the README: the fit is what
        # carries it, by a factor of ten.
        R = (fresnel_rough(ndv, sv2) if fresnel == 'rough'
             else OPT.fresnel(ndv))
    L, Lsun = sky_and_sun(rx, ry, rz, cov, receiver)
    return L * R, Lsun * R, R, ndv, np.stack([rx, ry, rz], axis=-1)


# ---------------------------------------------------------------- 4. THE PASS
_BASE = {}


def flat_base(gbuf, exitlut=None, ssr_iters=6):
    """The flat-datum pass, run once and shared by every wave path.

    THE TRANSMITTED HALF IS NOT RE-DERIVED. `sswater.water_shade` owns the
    composition -- bed radiance, the trap, the entry leg, `out_of_water` -- and
    the wave field enters it through exactly one factor, the Fresnel split, so
    each path below rescales `L_up` by `(1 - R_wave)/(1 - R_flat)` and changes
    nothing else. Two things are therefore deliberately NOT modelled, on every
    path AND in the reference, so that no path gains from the omission:

      * the refracted DIRECTION is not perturbed by the wave normal, so the bed
        does not wobble. That needs a per-band refracted trace per sub-sample
        and it is `offline.py`'s machinery at 256x the cost. It is bounded
        rather than waved at: the transmitted half is `(1 - R)` weighted, and
        the suite reports what fraction of the frame's radiance it carries at
        each distance -- past 60 m it is under a percent and the section being
        tested is about the far field.
      * the surface is not displaced, only tilted. `12`'s hierarchy is
        "displaced geometry near, normal detail mid, statistical BRDF far", and
        this pass owns the second and third rungs.
    """
    key = (id(gbuf), ssr_iters, None if exitlut is None else exitlut.mode)
    if key in _BASE:
        return _BASE[key]
    if exitlut is None:
        exitlut = LUT.ExitLUT('joint')
    P = WA.water_pass(gbuf, exitlut=exitlut, traversal='ssr',
                      ssr_iters=ssr_iters)
    w = P['water']
    d = P['dirs']
    refl_flat, up_flat = WA.water_shade(d[w], P['dep'][w], P['path3'][w],
                                        exitlut, 'directional')
    R_flat = OPT.fresnel(np.clip(-d[w][..., 2], 0.0, 1.0))
    out = dict(P)
    out['refl_flat'] = refl_flat
    out['up_flat'] = up_flat
    out['R_flat'] = R_flat
    _BASE[key] = out
    return out


def wave_pass(gbuf, path='variance', fp_scale=1.0, base=None, gxy=None,
              want_parts=False, receiver='inverted', fresnel='rough'):
    """The screen-space water pass with waves on the flat datum.

    `path` is 'point' | 'naive' | 'variance' (see the module docstring).
    `fp_scale` multiplies the footprint handed to `field.py` -- 1.0 is the
    kernel `field.py` derives, and the suite runs 0.7736 (the second-moment box
    match, `1/1.2926`) to ask whether the fix is insensitive to the kernel
    choice, which is the whole point of moving the variance rather than losing
    it."""
    init_field()
    if base is None:
        base = flat_base(gbuf)
    w = base['water']
    d = base['dirs']
    fp, aniso, ok, Pw = pixel_footprint(gbuf, base['t'], d, w)
    # the horizon quads have no usable derivative; rather than leave `fp = 0`
    # there (which would hand the FULL unfiltered field to a pixel two
    # kilometres away, i.e. the worst possible answer) they fall back to the
    # closed form above. They are excluded from every measurement regardless --
    # a fallback keeps the picture honest, it does not make the pixel measured.
    bad = w & ~ok
    if bad.any():
        fa, aa = analytic_footprint(base['t'][bad],
                                    np.clip(-d[..., 2][bad], 1e-9, 1.0))
        fp = fp.copy(); aniso = aniso.copy()
        fp[bad], aniso[bad] = fa, aa

    x = Pw[..., 0][w].astype(np.float64)
    y = Pw[..., 1][w].astype(np.float64)
    f = (fp[w] * fp_scale).astype(np.float64)

    if path == 'point':
        gx, gy = FLD.grad_points(x, y, None) if gxy is None else gxy
        cov_in = None
    else:
        gx, gy = FLD.grad_points(x, y, f) if gxy is None else gxy
        cov_in = FLD.slope_var_points(x, y, f) if path == 'variance' else None

    L_refl, L_sun, R, ndv, rdir = surface_shade(d[w], gx, gy, cov_in,
                                                receiver, fresnel)
    L_up = base['up_flat'] * ((1.0 - R) / np.maximum(1.0 - base['R_flat'], 1e-9))

    L = gbuf['color'].copy()
    L[w] = L_refl + L_up
    out = {'color': L, 'water': w, 'fp': fp, 'aniso': aniso, 'fp_ok': ok,
           'path': path, 'P': Pw, 'gx': gx, 'gy': gy, 'R': R, 'ndv': ndv}
    if want_parts:
        out['L_refl'] = L_refl
        out['L_sun'] = L_sun
        out['L_up'] = L_up
        out['cov_in'] = cov_in
    return out


def mip_normals(nsub=8, seed=7):
    """A LITERAL normal-map mip, for the record: the mean of the UNIT normals
    over the footprint, renormalised. That is what a mip chain of a normal map
    holds and it is not what `field.py`'s filter produces -- the filter averages
    the SLOPE FIELD, which is linear in the surface, while a normal mip averages
    a nonlinear function of it and then throws away the shortening of the mean
    vector (which is Toksvig's whole signal). Built out of the reference's own
    sub-samples in `waveref.py`, so it costs nothing extra; this function only
    names the operation."""
    raise NotImplementedError('see waveref.reference_frame(want_mip=True)')
