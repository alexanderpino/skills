"""Water surface for the pool reference render: the wave field and the jet.

Lane A of the gauntlet owns this file. Everything here answers one question --
what is the surface slope at (x, y)? -- and nothing here knows about light.

Bands, in the order they were forced on the model by observation:
  WIND    short, incoherent, uniform, killed in the lee of the shade sail
  REVERB  the diffuse late field of a reverberant basin: random phase, isotropic
  NEAR    early wall reflections from the jet, still coherent
  BOIL    the turbulent surface over the jet itself, riding a forced envelope
  WAKE    the jet's stationary wake, solved by eikonal ray tracing (wake.py)

ONE DEFINITION OF rms SLOPE, AND WHY THE FILE INSISTS ON IT
-----------------------------------------------------------
Everywhere in this file, and in the chapter,

    s = sqrt(<|grad h|^2>) = sqrt(<gx^2> + <gy^2>) = sqrt(total mean-square slope)

There is a second, equally respectable convention -- the PER-AXIS rms,
sqrt(<gx^2 + gy^2>/2), which is what an isotropic field's single-axis Gaussian
width is -- and it is smaller by exactly sqrt(2). Both are "the rms slope". The
file used to carry both at once: WIND and REVERB were normalised and printed as
sqrt(total mss), NEAR and WAKE were normalised and printed per-axis, and the
TOTAAL row added them in quadrature as though they were the same number. That is
not a cosmetic defect. Because the two bands that use the per-axis form are
normalised TO it, a target written as 0.024 put sqrt(2)*0.024 of actual slope on
the water, so the mixed convention was in the water and not only in the printout,
and the whole point of a slope budget -- weighing one band against another --
was being done with two different units on the two sides of the scale.

sqrt(total mss) is the convention picked because it is the one the rest of the
doctrine already speaks: Cox & Munk quote total mean-square slope, the focusing
number F = 0.25*d*s*k is written for it, and the chapter's independently measured
far-field figures (0.016 short, 0.055 long) are in it. It is computed in exactly
one place, `rms_slope`, and every band, every normaliser and every printed row
goes through that function or its analytic twin `_plane_rms`. Writing the
expression out by hand anywhere else is how the second convention got in.

Slope budget, and why it is the whole game
------------------------------------------
Caustic focusing on the bed goes as F = 0.25*d*s*k (d = 1.40 m, s = rms slope,
k = dominant wavenumber). F ~ 0.3-0.6 writes the soft readable cell net; F >> 1
is past focus and writes fine high-variance speckle with no legible cells. So a
band is not judged by its own slope but by its slope AT ITS OWN WAVENUMBER, and
a band carrying too much slope at too short a wavelength washes the bed out
however correct its individual numbers look.

The net is written by REVERB (~20 cm) and NEAR (~20 cm). WIND and BOIL are past
focus by construction and are allowed to be -- they own sparkle and wash, and
their slope share is small. The WAKE is the dangerous one: it starts long
(~35 cm) and SHORTENS as it travels, so it walks itself into the past-focus band.
The only thing that keeps it honest is the film damping in wake.alpha_eff, which
kills it at about 3 m -- and its normalisation, which is measured in its own near
field, not averaged over the basin.
"""
import numpy as np

import wake as _wk

X0, X1, Y0, Y1 = 0.0, 8.0, 0.0, 4.0
rng = np.random.default_rng(20260810)


def rms_slope(gx, gy):
    """THE rms slope of a sampled gradient field. s = sqrt(<gx^2> + <gy^2>).

    Every band, every normalisation target and every printed row in this file
    goes through this function. See the convention block at the top: the reason
    it exists is that the same quantity written out inline twice came out in two
    different units, and no diagnostic could see it because each band's own
    numbers stayed self-consistent."""
    return float(np.sqrt(np.mean(np.asarray(gx) ** 2 + np.asarray(gy) ** 2)))


def _plane_rms(sl):
    """Same quantity for a superposition of plane waves, analytically.

    A component with slope amplitude sl_i contributes sl_i*cos(phase) to the
    gradient ALONG ITS OWN k, so <|grad h|^2> = sum_i sl_i^2 * <cos^2> =
    sum_i sl_i^2 / 2 -- both gradient components together, not each. Hence the
    /2 here is the <cos^2> factor and NOT a per-axis split, which is the exact
    coincidence that made the two conventions hard to tell apart by eye."""
    return np.sqrt(np.sum(np.asarray(sl) ** 2) / 2.0)


# ------------------------------------------------- PER-BAND FOOTPRINT FILTERING
# WHY A BAND HAS TO BE ATTENUATED, AND BY EXACTLY WHAT.
#
# A camera pixel does not sample the surface at a point, it integrates the
# surface over its own footprint. Write that footprint's normalised weighting
# function as w(r). Then what the pixel is entitled to see of a plane-wave
# component of slope amplitude a and wavevector k is
#
#     INT w(r) a cos(k.(x+r) + phi) dr  =  a * W(k) * cos(k.x + phi),
#     W(k) = INT w(r) exp(-i k.r) dr        (the footprint's transfer function)
#
# -- exact, and it assumes nothing about the field, only about the footprint. So
# the per-band factor is the footprint kernel's own Fourier transform evaluated
# at THAT BAND's k. Three consequences worth stating before the arithmetic:
#
# 1. IT MULTIPLIES AMPLITUDE, NOT VARIANCE, and that is a real distinction and
#    not bookkeeping. Averaging is linear on the field, so it acts on the field;
#    the resolved slope VARIANCE then falls as W^2 on its own. Multiplying the
#    returned gradient by sqrt(W) instead -- "attenuate the variance by W" --
#    would put W on the variance and sqrt(W) on the field, and those are two
#    different surfaces. Downstream this matters because what a shader reads out
#    of grad_points is a FIELD: it computes a normal from it, and a normal is a
#    field quantity. The variance is a SECOND number and it has to be handed over
#    separately, which is what `slope_var_points` below is for.
# 2. THIS IS NOT A BLUR OF THE IMAGE. The image is a nonlinear function of the
#    slope (Fresnel, a specular lobe, a refraction into the pool), so blurring
#    the shaded result averages radiances, which destroys the specular statistics
#    the whole model exists to produce. Narrowing the slope distribution first
#    and shading the narrowed distribution is the chapter's "Distance and
#    filtering" doctrine and it gives the correct answer for the same cost.
# 3. WHAT IS REMOVED IS NOT DESTROYED, IT IS MOVED. See `slope_var_points`.
#
# WHICH w(r). Three candidates, and they do not agree:
#     box of width fp    W = sinc(k fp/2)    zeros at fp = lambda, 2 lambda...,
#                        negative lobes to -0.217, envelope falls only as 1/(k fp)
#     tent               W = sinc^2(k fp/2)  positive, still has zeros, 1/k^2
#     Gaussian, s.d. s   W = exp(-k^2 s^2/2) positive, monotone, no zeros
# The box is the literal footprint of a box-filtered pixel and it is the wrong
# choice here, for a reason that is the whole point of the exercise: a factor
# that passes through zero and comes back NEGATIVE means a band fades out,
# returns phase-inverted and fades again as the footprint grows with distance --
# a slow beat against distance, which is a moire generator, which is the exact
# defect being removed. Its 1/(k fp) envelope is also far too slow: at fp = 5x
# the wavelength a box still passes 6% of the amplitude, oscillating.
# The Gaussian is taken instead because (a) it is positive and monotone, so a
# band fades once and stays faded; (b) it is the only kernel that is at once
# separable and isotropic, which is all a SCALAR fp with no orientation is
# entitled to assume -- the true footprint is an oriented parallelogram, and
# pretending to know its axes from one number would be fake precision; (c) it
# composes, footprint (*) reconstruction filter is another Gaussian with the
# variances added, so nothing downstream has to re-derive it. That is the EWA
# argument, and it is why texture filtering has used elliptical Gaussians for
# forty years.
#
# THE SCALE, which is the part that has to be derived rather than assumed. The
# README proposed exp(-(k fp)^2/2), i.e. this family with s = fp: a Gaussian
# whose STANDARD DEVIATION is the whole footprint width, 2.67x wider than the
# footprint it is standing in for. It does not merely remove the capillary band,
# it takes the long bands with it -- at fp = 8 cm it leaves 4% of a 20 cm wave
# that the grid is sampling 2.5 times per wavelength and resolving perfectly
# well. Right family, undrived scale. Two anchors fix it:
#   (a) SECOND MOMENT. A box of width fp has variance fp^2/12, so the matched
#       Gaussian is s = fp/sqrt(12) = 0.2887 fp. This reproduces the averaging
#       the pixel actually does -- and it is NOT an antialiasing filter: at the
#       Nyquist wavenumber pi/fp it still passes 0.663 of the amplitude, 44% of
#       the variance, straight into the fold. Reproducing a footprint and
#       prefiltering for a footprint are different jobs, and only the second one
#       is being asked for here.
#   (b) NYQUIST. The sample spacing is fp, so the shortest representable wave is
#       lambda = 2 fp. Pin the half-amplitude point there:
#           exp(-(pi/fp)^2 s^2 / 2) = 1/2   ->   s = fp sqrt(2 ln 2)/pi
#       = 0.3748 fp -- only 1.30x the second-moment match, the same deliberate
#       mild over-blur that mip-mapping is and that Bruneton et al.'s
#       N_min = 1.0 / N_max = 2.5 smoothstep is.
# (b) is what is used, and it reduces the whole filter to one checkable sentence:
#   A COMPONENT IS HALF GONE WHEN THE FOOTPRINT REACHES HALF ITS WAVELENGTH,
#   and 94% gone (99.6% of its variance) when the footprint reaches its
#   wavelength.
#
# WHAT fp IS, AND THE ONE WAY A CALLER CAN GET IT WRONG. fp is the footprint the
# PIXEL integrates over, in metres. For render.py that is `FOOT * SS` -- the
# output pixel, which render.py already computes under that name -- and NOT
# `FOOT`, which is one subsample of an SSxSS grid. The difference is a factor SS
# and it decides the answer: at 8 m from the eye the two are 8.6 mm and 25.8 mm
# while the wind band is 28 mm, so the band is comfortably resolved by the
# subsample grid and hopelessly aliased by the output grid, and only the second
# reading removes it. The output pixel is also the conservative reading for a
# second, independent reason: shading is a NONLINEAR function of slope, so a
# slope field sitting merely at the subsample Nyquist still produces radiance
# harmonics well above it. Band-limiting the slope to the sampling rate does not
# band-limit what the shader makes of it, so the prefilter belongs at the rate
# the final image is stored at.
FP_SIGMA = np.sqrt(2.0 * np.log(2.0)) / np.pi        # 0.37478 -- derived above


def _fp_var(fp):
    """The Gaussian footprint's variance, (FP_SIGMA*fp)^2. `None` -> unfiltered.

    Everything internal carries this rather than fp itself, because it is what
    the exponent actually needs and because it is the quantity that ADDS when
    filters compose. Scalar or per-point array; per-point is only meaningful for
    the point-sampled path (`grad_points`), since the grid path is separable and
    a per-texel footprint would break the separability the GEMM depends on."""
    if fp is None:
        return None
    return (np.float32(FP_SIGMA) * np.asarray(fp, np.float32)) ** 2


def band_weight(k, fp):
    """Amplitude a component of wavenumber k keeps at footprint fp. W^2 is the
    fraction of its slope VARIANCE that survives; 1 - W^2 is what moves out to
    `slope_var_points`."""
    v = _fp_var(fp)
    k = np.asarray(k, np.float64)
    return np.ones_like(k) if v is None else np.exp(-0.5 * k ** 2 * v)


def half_footprint(k):
    """The footprint at which a component of wavenumber k is half gone.

    Falls out of the calibration above as exactly lambda/2, with no free
    constant left in it: W = 1/2 needs k*s = sqrt(2 ln 2), and s = FP_SIGMA*fp
    was chosen so that happens at k = pi/fp. The footprint at which half the
    band's VARIANCE is gone is smaller by sqrt(2): lambda/(2 sqrt 2) = 0.354 lambda."""
    return np.pi / np.asarray(k, float)


# ---------------------------------------------------------------- the return jet
# A pool return is a SUBMERGED ROUND TURBULENT JET, not a pulsing point. Its
# surface footprint is then geometry, not an authored lobe:
#   half-width      r_half(s) = S * s                  S ~ 0.094   (linear spreading)
#   centreline      U_c(s)    = B * U0 * d / s         B ~ 5.8     (1/s decay)
#   radial profile  U/U_c     = exp(-ln2 (r/r_half)^2)
#   turbulence      u' ~ 0.25 * U_c  on the axis
# The surface is a plane at radial distance h from the axis, so the jet only
# reaches it once it has spread that far -- which is why the disturbed patch is
# elongated along the aim and starts DOWNSTREAM of the fitting rather than at it.
JET_XY = (0.10, 1.15)
JET_H = 0.15                  # fitting depth below the waterline (m)
JET_TILT = np.deg2rad(6.0)    # aimed slightly up, as returns usually are
JET_AZ = np.deg2rad(20.0)
D_NOZZLE, DP_BAR, CD = 0.020, 0.80, 0.92   # 20 mm eyeball, return pressure in bar
U0 = CD * np.sqrt(2 * DP_BAR * 1e5 / 1000.0)   # Bernoulli: 0.8 bar -> 11.6 m/s
SIGMA_W = 0.0728                                # surface tension, N/m
C_MIN = (4 * 9.81 * SIGMA_W / 1000.0) ** 0.25   # 0.231 m/s, at lambda 17.1 mm
S_SPREAD, B_DECAY, TURB_INT = 0.094, 5.8, 0.25
ETA_C = 1.0                   # O(1) constant in eta ~ C u'^2 / g  (see provenance)
NU = 1.004e-6
# Band rms slopes, all as s = sqrt(<|grad h|^2>). Two of these were RESTATED, not
# retuned, when the file was put on one convention: JNEAR and WAKE were normalised
# through the per-axis expression, so the numbers written here were smaller by
# sqrt(2) than the slope they actually put on the water.
#     JNEAR  0.024 per-axis * sqrt(2) = 0.0339 -> 0.034
#     WAKE   0.068 per-axis * sqrt(2) = 0.0962 -> 0.096
# The water is unchanged to within the rounding: these are the same fields, read
# in the unit the rest of the file uses. Nothing was scaled to preserve an old
# printed total, and the printed totals duly moved (see _norm_jets).
#
# ? WIND_RMS and REVERB_RMS are CHOSEN, not derived -- there is no measurement
# behind 0.016 and 0.046 in this file. The chapter's "0.016 short, 0.055 long"
# was read off this implementation, so quoting it back as confirmation would be
# circular. What the chapter does assert independently is a RATIO (near field
# roughly twice the far field), and that is the number to judge these against.
WIND_RMS, JNEAR_RMS, REVERB_RMS = 0.016, 0.034, 0.046
# The wake's rms slope in ITS OWN near field (inside wake.build's norm_r = 0.40 m
# of the forcing peak), not an average over the basin. The other four bands sum to
# 0.075 over that patch, so sqrt(0.075^2 + 0.096^2) = 0.122 local against 0.058 in
# the far field -- the documented pair, both now in sqrt(<|grad h|^2>).
WAKE_RMS = 0.096

_AIM = np.array([np.cos(JET_TILT) * np.cos(JET_AZ),
                 np.cos(JET_TILT) * np.sin(JET_AZ), np.sin(JET_TILT)])
_ORIG = np.array([JET_XY[0], JET_XY[1], -JET_H])


def _disp(k):
    om = np.sqrt(9.81 * k + (0.0728 / 1000.0) * k ** 3)
    return om, (9.81 + 3 * (0.0728 / 1000.0) * k ** 2) / (2 * om), 2 * NU * k ** 2


def _alpha(k):
    """Amplitude decay. Clean surface: 2 nu k^2 (bulk). A pool always carries a
    surface film, which is INEXTENSIBLE to first order: the surface can no longer
    slip, a Stokes layer of thickness sqrt(2 nu / omega) forms under it, and the
    dissipation there dominates. That gives alpha ~ k sqrt(nu omega) -- a wavelength
    dependent factor, not a tuned multiplier."""
    om = _disp(k)[0]
    return 2 * NU * k ** 2, 0.3536 * k * np.sqrt(NU * om)


def jet_envelope(X, Y):
    """rms surface slope forced by the jet's turbulence, from the jet geometry.
    eta ~ C u'^2 / g (stagnation scale of an eddy of velocity u'), and the eddy
    size is the local jet width, so slope ~ eta / r_half.

    This is an ENVELOPE, one scalar, so it carries no per-axis/total ambiguity of
    its own -- but it is used as BOIL's local rms slope (BOIL's plane set is
    normalised to unit rms and then multiplied by this), so it inherits whatever
    convention that normalisation uses. _plane goes through _plane_rms, so the
    envelope is in sqrt(<|grad h|^2>) like everything else. ? the O(1) constant
    ETA_C is genuinely unknown, so the LEVEL here is a scaling argument and only
    the near/far ratio it produces is defensible."""
    px, py = X - np.float32(_ORIG[0]), Y - np.float32(_ORIG[1])
    pz = np.float32(0.0 - _ORIG[2])
    sax = px * np.float32(_AIM[0]) + py * np.float32(_AIM[1]) + pz * np.float32(_AIM[2])
    sax = np.maximum(sax, np.float32(0.05))
    r2 = np.maximum(px * px + py * py + pz * pz - sax * sax, 0.0)
    rh = np.float32(S_SPREAD) * sax
    Uc = np.float32(B_DECAY * U0 * D_NOZZLE) / sax
    up = np.float32(TURB_INT) * Uc * np.exp(-np.float32(np.log(2.0)) * r2 / (rh * rh))
    return (np.float32(ETA_C) * up * up / np.float32(9.81)) / rh


def _report_jet():
    sax = np.linspace(0.05, 7.5, 400)
    xs = (JET_XY[0] + sax * _AIM[0]).astype(np.float32)
    ys = (JET_XY[1] + sax * _AIM[1]).astype(np.float32)
    e = jet_envelope(xs, ys)
    im = int(np.argmax(e))
    print("  jet: nozzle %.0f mm, U0 %.1f m/s (= %.1f m3/h), diepte %.0f cm, %.0f gr omhoog"
          % (D_NOZZLE * 1000, U0, U0 * np.pi / 4 * D_NOZZLE ** 2 * 3600,
             JET_H * 100, np.degrees(JET_TILT)))
    print("  oppervlakteverstoring piekt %.2f m stroomafwaarts, helling %.3f daar"
          % (sax[im], e[im]))
    half = e > 0.5 * e[im]
    print("  halfwaardelengte langs de as: %.2f - %.2f m"
          % (sax[half][0], sax[half][-1]))
    print("  demping, schoon vs inextensibele film (geldt alleen kort:")
    print("    bij lange golven rekt de film mee en gedraagt het oppervlak zich schoon)")
    for lam in (0.05, 0.03, 0.015, 0.008):
        k = 2 * np.pi / lam; ac, af = _alpha(k); cg = _disp(k)[1]
        print("    lambda %5.0f mm   schoon %7.2f m   film %6.2f m   (factor %.1f)"
              % (lam * 1000, cg / ac, cg / af, af / ac))


def _plane(nc, lo, hi, rms, spread_deg, seed):
    r = np.random.default_rng(seed)
    lam = np.exp(r.uniform(np.log(lo), np.log(hi), nc))
    sl = r.uniform(0.5, 1.0, nc); sl *= rms / _plane_rms(sl)
    k = 2 * np.pi / lam
    th = (r.uniform(0, 2 * np.pi, nc) if spread_deg is None
          else r.normal(np.deg2rad(20.0), np.deg2rad(spread_deg), nc))
    om = _disp(k)[0]
    # k2 is carried so the footprint filter can be applied PER COMPONENT rather
    # than per band. A band here spans two and a half octaves (WIND runs 17 to
    # 70 mm), so one nominal k for the whole band would remove its long half
    # together with its short half; per component, a band narrows as the
    # footprint grows instead of switching off, which is what "narrow the
    # distribution" means.
    return dict(kx=k * np.cos(th), ky=k * np.sin(th), amp=sl / k, k2=k * k,
                ph=r.uniform(0, 2 * np.pi, nc) - om * 3.7)


# Every band's short end is floored at LAM_MIN. Below the minimum phase speed
# there is no propagating surface wave at all -- surface tension takes over as the
# restoring force and the branch turns round -- so wind cannot force anything
# finer and viscosity removes what is there. Octaves below LAM_MIN are detail the
# physics forbids, and on a 1.40 m bed they are pure past-focus speckle: at
# lambda = 8 mm even s = 0.01 gives F = 2.7.
LAM_MIN = 2 * np.pi * np.sqrt(SIGMA_W / (1000.0 * 9.81))    # 17.1 mm, at c_min

WIND = _plane(20, LAM_MIN, 0.070, WIND_RMS, 45.0, 11)
REVERB = _plane(44, 0.120, 0.450, REVERB_RMS, None, 12)
# the turbulent surface itself: very short, non-propagating, rides the envelope
BOIL = _plane(10, LAM_MIN, 0.045, 1.0, None, 17)

# The extended-source Huygens sum that used to live here is now inside the eikonal
# solve (wake.trace launches one fan per axial station, weighted by the forcing
# envelope), so the arc centre still lands out in the water rather than on the
# fitting -- it is just no longer a second, uncalibrated copy of the same physics.
_IMG = [(JET_XY[0], JET_XY[1]), (-JET_XY[0], JET_XY[1]), (JET_XY[0], -JET_XY[1]),
        (2 * X1 - JET_XY[0], JET_XY[1]), (JET_XY[0], 2 * Y1 - JET_XY[1])]
_NEAR = [(2 * np.pi / l, w) for l, w in ((0.30, 1.0), (0.21, 0.8), (0.15, 0.6))]
_SC = {'near': 1.0}
_PH = np.random.default_rng(13).uniform(0, 2 * np.pi, 8)


def shelter(x, y):
    """Wind lee under the sail. Band A only."""
    d = np.exp(-(((x - 2.10) / 2.3) ** 2 + ((y - 0.75) / 1.55) ** 2))
    return 0.40 + 0.60 * (1.0 - 0.70 * d)


def _drift(sax):
    """Mean surface drift over the jet: the momentum product, not the wave product."""
    h_ax = np.maximum(JET_H - sax * np.sin(JET_TILT), 0.0)
    rh = S_SPREAD * sax
    return (B_DECAY * U0 * D_NOZZLE / sax) * np.exp(-np.log(2.0) * (h_ax / rh) ** 2)


_WK_S = np.linspace(0.45, 2.4, 6)
_WK_U = _drift(_WK_S)

# ---------------------------------------------------------------------- the wake
# THE TRAP THIS BAND EXISTS TO AVOID. Stationary crests satisfy c(k) = U cos psi,
# so on the gravity branch k = g/(U cos psi)^2 and the WAVEVECTOR fan opens to
# +-arccos(c_min/U) ~ 78 deg. That fan is not the shape of the disturbance.
# Energy travels at c_g*khat + U, and c_g = U cos psi / 2 <= U/2, so the current
# dominates and the ENERGY fan is narrow and aligned with the jet. Summing plane
# waves over the 78 deg wavevector fan -- the obvious implementation -- sprays the
# whole basin with the fan-edge wavelengths (9 cm and shorter, and they carry the
# MOST slope because slope ~ amp*k ~ 1/cos psi), which is exactly the band that
# destroys the bed caustics. So the fan is not sampled directly: the rays are
# integrated, and the pattern lands where the energy actually goes.
_WK_GRID = (800, 400)      # 10 mm texels; nothing under ~8 cm survives the film
_WK_CACHE = {}


def _boxsm(a, r):
    """Separable box mean of half-width r texels, edges clamped. Used only to turn
    the wake's single realisation into a LOCAL mean square -- see _wake_field."""
    out = np.asarray(a, np.float64)
    for ax in (0, 1):
        n = out.shape[ax]
        pad = [(0, 0), (0, 0)]; pad[ax] = (r + 1, r)
        c = np.cumsum(np.pad(out, pad, mode='edge'), axis=ax)
        hi = [slice(None)] * 2; lo = [slice(None)] * 2
        hi[ax] = slice(2 * r + 1, 2 * r + 1 + n); lo[ax] = slice(0, n)
        out = (c[tuple(hi)] - c[tuple(lo)]) / (2 * r + 1)
    return out


def _wake_field():
    """Eikonal solve, cached. Rays advect at c_g*khat + U(x) and refract on the
    drift gradient; amplitude follows wave action along the ray tube and decays by
    wake.alpha_eff. Nothing is masked or tapered: the reach is the damping.

    Cached alongside the field: `k`, the local wavenumber map wake.build returns,
    and `vxx/vyy/vxy`, the local mean-square slope tensor. The other four bands
    are explicit plane-wave sets, so both quantities are exact for them; this one
    is a reconstructed grid and has to measure them. The mean square is a box
    mean over 21 texels = 21 cm, which is about two wavelengths of the band -- a
    window shorter than a wavelength would report the crest pattern itself as
    variance instead of averaging over it."""
    if not _WK_CACHE:
        jet = _wk.Jet(JET_XY[0], JET_XY[1], depth=JET_H,
                      tilt_deg=np.degrees(JET_TILT), az_deg=np.degrees(JET_AZ),
                      d=D_NOZZLE, dp_bar=DP_BAR, cd=CD, S=S_SPREAD, B=B_DECAY)
        gx, gy, kk = _wk.build(jet, X0, X1, Y0, Y1, _WK_GRID[0], _WK_GRID[1],
                               rms_target=WAKE_RMS)
        _WK_CACHE['gx'] = gx.astype(np.float32)
        _WK_CACHE['gy'] = gy.astype(np.float32)
        _WK_CACHE['k'] = kk.astype(np.float32)
        for nm, a in (('vxx', gx * gx), ('vyy', gy * gy), ('vxy', gx * gy)):
            _WK_CACHE[nm] = _boxsm(a, 10).astype(np.float32)
    return _WK_CACHE['gx'], _WK_CACHE['gy']


def _wk_lookup(X, Y, keys):
    """Bilinear lookup of any cached wake map. 10 mm texels; the shortest thing
    that survives the film damping is ~10 cm, so this samples it many times over."""
    _wake_field()
    nx, ny = _WK_GRID
    fu = np.clip((X - np.float32(X0)) / np.float32(X1 - X0) * nx - 0.5, 0, nx - 1.001)
    fvv = np.clip((Y - np.float32(Y0)) / np.float32(Y1 - Y0) * ny - 0.5, 0, ny - 1.001)
    iu = fu.astype(np.int64); iv = fvv.astype(np.int64)
    du = (fu - iu).astype(np.float32); dv = (fvv - iv).astype(np.float32)
    out = []
    for key in keys:
        g = _WK_CACHE[key]
        out.append(((g[iv, iu] * (1 - du) + g[iv, iu + 1] * du) * (1 - dv) +
                    (g[iv + 1, iu] * (1 - du) + g[iv + 1, iu + 1] * du) * dv))
    return out


def _wake(X, Y, fv=None):
    """The traced wake, footprint-filtered at its own LOCAL wavenumber.

    Per texel and not per band: the stationary condition k = g/(U cos psi)^2
    shortens this wave as the drift decays, so the same band runs from ~35 cm at
    the fitting to under 10 cm downstream, and one k for the whole basin would
    over-filter the source while under-filtering the tail."""
    if fv is None:
        gx, gy = _wk_lookup(X, Y, ('gx', 'gy'))
        return gx, gy
    gx, gy, kk = _wk_lookup(X, Y, ('gx', 'gy', 'k'))
    w = np.exp(-0.5 * kk * kk * fv)
    return gx * w, gy * w


def _cyl(X, Y, fv=None):
    """Long waves radiated from the forcing region and its wall images. Long waves
    on a filmed surface are still bulk-damped, so the clean-water alpha applies."""
    gx = np.zeros(X.shape, np.float32); gy = np.zeros(X.shape, np.float32)
    for j, (k, w) in enumerate(_NEAR):
        om, cg, _ = _disp(k); al = _alpha(k)[0]
        fw = 1.0 if fv is None else np.exp(-0.5 * k * k * fv)
        for xi, yi in _IMG:
            dx = X - np.float32(xi); dy = Y - np.float32(yi)
            r = np.sqrt(dx * dx + dy * dy) + np.float32(0.12)
            a = w / np.sqrt(r) * np.exp(-al * r / cg) * fw
            c = (a * k * np.cos(k * r - om * 3.7 + _PH[j])).astype(np.float32)
            gx += c * dx / r; gy += c * dy / r
    return gx * _SC['near'], gy * _SC['near']


def _gemm(F, xs, ys, fv=None):
    """Separable evaluation on a grid. `fv` (the footprint variance) has to be a
    SCALAR here: the whole speed of this path is that x and y factorise, and a
    per-texel footprint would not."""
    amp = F['amp'] if fv is None else F['amp'] * np.exp(-0.5 * F['k2'] * fv)
    A = F['kx'][None, :] * xs[:, None] + F['ph'][None, :]
    cA, sA = np.cos(A), np.sin(A)
    B = F['ky'][None, :] * ys[:, None]
    P = np.concatenate([np.cos(B), np.sin(B)], 1).astype(np.float32)
    o = []
    for kk in (F['kx'], F['ky']):
        Q = np.concatenate([(amp * kk)[None, :] * cA,
                            -(amp * kk)[None, :] * sA], 1).T
        o.append(P @ Q.astype(np.float32))
    return o[0], o[1]


def _pts(F, x, y, fv=None):
    """Point evaluation. `fv` may be a scalar or one value per point -- this is
    the path the camera uses, and every camera ray has its own footprint."""
    gx = np.zeros_like(x); gy = np.zeros_like(x)
    for i in range(len(F['kx'])):
        a = F['amp'][i] if fv is None else F['amp'][i] * np.exp(-0.5 * F['k2'][i] * fv)
        c = a * np.cos(F['kx'][i] * x + F['ky'][i] * y + F['ph'][i])
        gx += F['kx'][i] * c; gy += F['ky'][i] * c
    return gx, gy


DEPTH_FOR_F = 1.40


def _focus(s, k):
    """F = 0.25 d s k. F >> 1 is past focus (speckle, no cells); F ~ 0.3-0.6 is the
    soft readable net; the cell size on the bed runs with the dominant wavelength."""
    return 0.25 * DEPTH_FOR_F * s * k


def _spec_k(gx, gy, dx, dy):
    """Slope-energy-weighted rms wavenumber of a gradient field on a regular grid."""
    ny, nx = gx.shape
    P = np.abs(np.fft.rfft2(gx)) ** 2 + np.abs(np.fft.rfft2(gy)) ** 2
    kx = 2 * np.pi * np.fft.rfftfreq(nx, dx)[None, :]
    ky = 2 * np.pi * np.fft.fftfreq(ny, dy)[:, None]
    k2 = kx * kx + ky * ky
    P[0, 0] = 0.0
    return np.sqrt((P * k2).sum() / max(P.sum(), 1e-30))


def _plane_k(F):
    e = (F['amp'] * np.hypot(F['kx'], F['ky'])) ** 2
    return np.sqrt((e * (F['kx'] ** 2 + F['ky'] ** 2)).sum() / e.sum())


def _norm_jets():
    _report_jet()
    X, Y = np.meshgrid(np.linspace(0.3, X1 - 0.3, 260).astype(np.float32),
                       np.linspace(0.3, Y1 - 0.3, 130).astype(np.float32))
    g = _cyl(X, Y); _SC['near'] = JNEAR_RMS / rms_slope(*g)
    _wake_field()                       # trace the rays once, before anything asks
    # how far does the wake stay visible?
    sax = np.linspace(0.1, 7.8, 300)
    px = (JET_XY[0] + sax * _AIM[0]).astype(np.float32)
    py = (JET_XY[1] + sax * _AIM[1]).astype(np.float32)
    ga = _wake(px, py); amp = np.sqrt(ga[0] ** 2 + ga[1] ** 2)
    amp = np.convolve(amp, np.ones(15) / 15, 'same')
    vis = sax[amp > 0.10 * amp.max()]
    print("  drift langs de as: " + " ".join("%.2f" % u for u in _WK_U) + " m/s")
    print("  Froude U/c_min = %.1f -> stationaire golven binnen +-%.0f graden"
          % (_WK_U.max() / C_MIN, np.degrees(np.arccos(C_MIN / _WK_U.max()))))
    print("  zog zichtbaar tot %.1f m van de bron (bad is %.1f m)" % (vis[-1], X1))

    # ---- the slope budget, band by band, WITH the focusing number ---------------
    # Nothing may be left out of this table. The defect it exists to catch is a
    # band that is individually defensible and collectively fatal: correct slope,
    # correct spectrum, wrong wavenumber for the depth, and no line anywhere that
    # adds it up.
    _pk = 0.91
    jx_, jy_ = JET_XY[0] + _pk * _AIM[0], JET_XY[1] + _pk * _AIM[1]
    xxn, yyn = np.meshgrid(np.linspace(jx_ - .35, jx_ + .35, 128).astype(np.float32),
                           np.linspace(jy_ - .35, jy_ + .35, 128).astype(np.float32))
    xxf, yyf = np.meshgrid(np.linspace(5.0, 7.0, 256).astype(np.float32),
                           np.linspace(1.0, 3.0, 256).astype(np.float32))
    dn = 0.7 / 127.0; df = 2.0 / 255.0
    rows, near_v, far_v = [], 0.0, 0.0

    # EVERY s below comes out of rms_slope (or _plane_rms, its analytic twin).
    # No band writes its own rms expression -- that is what let two conventions
    # coexist here, one of them reaching all the way into the normalisation.
    # Every row is MEASURED on the two patches, none is the nominal constant read
    # back out. That matters for the TOTAAL row: WIND and REVERB are finite sets
    # of discrete components (20 and 44), so on a 2 m patch REVERB samples a few
    # percent above its 0.046 ensemble value, and a table that printed 0.046 while
    # the water carried 0.049 could not add up to the field's actual total.
    shn = shelter(xxn, yyn).astype(np.float32); shf = shelter(xxf, yyf).astype(np.float32)
    wxn, wyn = _gemm(WIND, xxn[0], yyn[:, 0]); wxf, wyf = _gemm(WIND, xxf[0], yyf[:, 0])
    rows.append(("WIND", rms_slope(wxn * shn, wyn * shn),
                 rms_slope(wxf * shf, wyf * shf), _plane_k(WIND)))
    rxn, ryn = _gemm(REVERB, xxn[0], yyn[:, 0])
    rxf, ryf = _gemm(REVERB, xxf[0], yyf[:, 0])
    rows.append(("REVERB", rms_slope(rxn, ryn), rms_slope(rxf, ryf), _plane_k(REVERB)))
    cn = _cyl(xxn, yyn); cf = _cyl(xxf, yyf)
    rows.append(("NEAR", rms_slope(*cn), rms_slope(*cf), _spec_k(cn[0], cn[1], dn, dn)))
    # BOIL rides the forcing envelope, so measure the product rather than
    # inferring it: the plane set carries unit rms, the envelope carries the rest.
    bxn, byn = _gemm(BOIL, xxn[0], yyn[:, 0]); en_ = jet_envelope(xxn, yyn)
    bxf, byf = _gemm(BOIL, xxf[0], yyf[:, 0]); ef_ = jet_envelope(xxf, yyf)
    rows.append(("BOIL", rms_slope(bxn * en_, byn * en_),
                 rms_slope(bxf * ef_, byf * ef_), _plane_k(BOIL)))
    wn = _wake(xxn, yyn); wf = _wake(xxf, yyf)
    rows.append(("WAKE", rms_slope(*wn), rms_slope(*wf),
                 _spec_k(wn[0], wn[1], dn, dn)))

    print("  band      lambda_dom   s(jet)  F(jet)   s(ver)  F(ver)")
    for nm, sn, sf, k in rows:
        near_v += sn ** 2; far_v += sf ** 2
        print("    %-7s %7.1f cm   %6.3f  %6.2f   %6.3f  %6.2f"
              % (nm, 200 * np.pi / k, sn, _focus(sn, k), sf, _focus(sf, k)))
    # The chapter's "long band" is REVERB AND NEAR together -- both are basin-scale
    # coherent water around 20 cm, and they are only separate rows here because
    # they are generated differently. Reading field.py's REVERB row against the
    # chapter's long band is comparing a part with a whole, which is a second way
    # to get a mismatched F that has nothing to do with the rms convention. The
    # lambda column below is the FAR-field value (that is the one the chapter
    # quotes); each F uses its own patch's k.
    ln = (rxn + cn[0], ryn + cn[1]); lf = (rxf + cf[0], ryf + cf[1])
    kln = _spec_k(ln[0], ln[1], dn, dn); klf = _spec_k(lf[0], lf[1], df, df)
    print("    %-7s %7.1f cm   %6.3f  %6.2f   %6.3f  %6.2f    (= REVERB + NEAR)"
          % ("LANG", 200 * np.pi / klf, rms_slope(*ln), _focus(rms_slope(*ln), kln),
             rms_slope(*lf), _focus(rms_slope(*lf), klf)))
    print("    %-7s %7s      %6.3f           %6.3f"
          % ("TOTAAL", "-", np.sqrt(near_v), np.sqrt(far_v)))
    # Restated from the old mixed-convention pair (0.09-0.11 near, 0.053 far), not
    # retuned to it. The far target was sqrt(0.016^2 + 0.046^2 + 0.020^2) with only
    # the last term per-axis; putting NEAR in the same unit (0.020*sqrt(2) = 0.028)
    # gives sqrt(0.016^2 + 0.046^2 + 0.028^2) = 0.056, and the measured patch runs
    # 0.058 because REVERB samples a shade above its nominal 0.046 there. The near
    # band moves from 0.09-0.11 to 0.11-0.14 the same way -- WIND and REVERB were
    # already in this unit, NEAR/BOIL/WAKE were not, so the total gains 1.35x and
    # not the full sqrt(2). The near/far RATIO, which is the part the chapter
    # states independently ("roughly twice"), goes 1.79 -> 2.16 and is BETTER for
    # the fix, because it was the one number the mixed units were distorting.
    print("    doel: 0.11-0.14 bij de straal, 0.058 ver weg"
          " (s = sqrt(<|grad h|^2>) overal)")


def grad_grid(xs, ys, fp=None):
    """Surface gradient on a separable grid.

    `fp` is the pixel footprint in metres and it is OPTIONAL: omitted, this is
    bit-for-bit the unfiltered field it always was, so a caller that has not
    opted in is unaffected. It must be a scalar on this path (see `_gemm`).
    Note that the caustic pass's "footprint" is the SUN's ray spacing, not a
    camera pixel's, so it is a different number from render.py's FOOT and is not
    interchangeable with it."""
    fv = _fp_var(fp)
    wx, wy = _gemm(WIND, xs, ys, fv)
    m = shelter(xs[None, :], ys[:, None]).astype(np.float32)
    rx_, ry_ = _gemm(REVERB, xs, ys, fv)
    bx, by = _gemm(BOIL, xs, ys, fv)
    gx, gy = wx * m + rx_, wy * m + ry_
    X = np.broadcast_to(xs[None, :].astype(np.float32), gx.shape)
    Y = np.broadcast_to(ys[:, None].astype(np.float32), gx.shape)
    env = jet_envelope(X, Y)
    jx, jy = _cyl(X, Y, fv)
    ax_, ay_ = _wake(X, Y, fv)
    return gx + jx + ax_ + bx * env, gy + jy + ay_ + by * env


def grad_points(x, y, fp=None):
    """Surface gradient at arbitrary points -- the camera pass calls this.

    `fp` is the pixel's footprint on the surface, in metres, scalar or one per
    point, and it is OPTIONAL: omitted, this returns exactly the field it always
    returned. Each band is attenuated at its own wavenumber before the bands are
    summed, so the 2.8 cm and 2.4 cm bands leave the resolved field as the
    footprint passes them while the 10-20 cm bands stay. The return shape does
    not change; the variance that leaves is `slope_var_points`, and a consumer
    that filters without reading that number has traded a moire for a plastic
    sheet, which is the other failure in the same chapter section."""
    fv = _fp_var(fp)
    wx, wy = _pts(WIND, x, y, fv); m = shelter(x, y)
    rx_, ry_ = _pts(REVERB, x, y, fv)
    bx, by = _pts(BOIL, x, y, fv)
    xf, yf = x.astype(np.float32), y.astype(np.float32)
    env = jet_envelope(xf, yf)
    jx, jy = _cyl(xf, yf, fv)
    ax_, ay_ = _wake(xf, yf, fv)
    return (wx * m + rx_ + jx + ax_ + bx * env,
            wy * m + ry_ + jy + ay_ + by * env)


def slope_var_points(x, y, fp):
    """The slope variance the footprint filter TOOK OUT at each point.

    Returns the symmetric 2x2 tensor (vxx, vyy, vxy) of removed mean-square
    slope. Its TRACE is the removed total mean-square slope, so
    sqrt(vxx + vyy) is a removed rms slope in the file's one convention,
    s = sqrt(<|grad h|^2>) -- the tensor is a refinement of that convention, not
    a second one, and collapsing it with `vxx + vyy` is always legal.

    WHY THIS EXISTS AT ALL, and why the interface would be wrong without it. The
    filter above narrows the slope distribution with distance, which is
    physically correct -- the far water really does present a narrower
    distribution to a pixel that averages more of it -- but the variance it
    removes has not gone anywhere in the world, only out of the FIELD. Left
    there, the far surface converges to its mean normal, the specular lobe
    collapses toward a Dirac, and energy conservation makes the surviving
    highlight brighter as it narrows: the far water goes from moire to
    shrink-wrapped perspex, which is the failure the chapter opens that section
    with. The variance has to arrive somewhere, and where it belongs is the
    width of the specular lobe. So the honest interface is a pair -- a narrowed
    field and the variance that was narrowed out of it -- and a consumer that
    takes only the first has swapped one artefact for another.

    The tensor rather than one scalar because the removed part is not isotropic:
    WIND is a 45 deg spread about the wind azimuth and the wake is a directional
    pattern, so what is removed is a Cox-Munk-like ellipse, and a lobe widened
    isotropically by its trace would be visibly wrong across the wind.

    Per component, a wave of slope amplitude a contributes a^2/2 to the total
    mean square along its own k, so the part removed is a^2 (1 - W^2)/2 with
    W^2 = exp(-k^2 s^2). The chapter writes this with a saturating form,
    1 - sqrt(1 - a^2 w_r^2), which differs from a^2 w_r^2/2 by 0.25% at the
    steepest slope in this basin (a ~ 0.1) and which would be a SECOND
    definition of variance sitting beside `_plane_rms`. One definition wins.
    """
    fv = _fp_var(fp)
    xf, yf = np.asarray(x, np.float32), np.asarray(y, np.float32)
    vxx = np.zeros_like(xf); vyy = np.zeros_like(xf); vxy = np.zeros_like(xf)
    for F, env in ((WIND, shelter(xf, yf)), (REVERB, 1.0),
                   (BOIL, jet_envelope(xf, yf))):
        e2 = (env * env) if np.ndim(env) else np.float32(env) ** 2
        # component by component rather than an (npoints, ncomponents) array:
        # this is called on whole camera passes, and 44 REVERB components times
        # a few million rays is a gigabyte of temporary for no reason.
        for i in range(len(F['kx'])):
            k2 = F['k2'][i]
            h = 0.5 * (F['amp'][i] ** 2 * k2) * (1.0 - np.exp(-k2 * fv)) * e2
            ux = F['kx'][i] / np.sqrt(k2); uy = F['ky'][i] / np.sqrt(k2)
            vxx = vxx + h * (ux * ux); vyy = vyy + h * (uy * uy)
            vxy = vxy + h * (ux * uy)
    # NEAR: a coherent sum of image sources, so its local amplitude is geometry
    # (1/sqrt(r) and the viscous decay), not a constant per component.
    for j, (k, w) in enumerate(_NEAR):
        om, cg, _ = _disp(k); al = _alpha(k)[0]
        lost = 1.0 - np.exp(-k * k * fv)
        for xi, yi in _IMG:
            dx = xf - np.float32(xi); dy = yf - np.float32(yi)
            r = np.sqrt(dx * dx + dy * dy) + np.float32(0.12)
            a = _SC['near'] * w / np.sqrt(r) * np.exp(-al * r / cg) * k
            h = 0.5 * a * a * lost
            vxx = vxx + h * (dx / r) ** 2
            vyy = vyy + h * (dy / r) ** 2
            vxy = vxy + h * (dx * dy) / (r * r)
    # WAKE: measured off the reconstructed grid rather than derived, because the
    # band arrives as a field and not as a component list. The local mean square
    # already IS a variance, so there is no factor of a half here.
    kk, mxx, myy, mxy = _wk_lookup(xf, yf, ('k', 'vxx', 'vyy', 'vxy'))
    lost = 1.0 - np.exp(-kk * kk * fv)
    return vxx + lost * mxx, vyy + lost * myy, vxy + lost * mxy


def normal_from_grad(gx, gy):
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    return -gx * inv, -gy * inv, inv


def surface_normal_grid(xs, ys, fp=None):
    """Normals on a separable grid -- the caustic pass calls this."""
    return normal_from_grad(*grad_grid(xs, ys, fp))


def surface_normal_points(x, y, fp=None):
    """Normals at arbitrary points -- the camera pass calls this."""
    return normal_from_grad(*grad_points(x, y, fp))
