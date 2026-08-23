"""
The atmosphere, the sun in it, and the two illuminants that come out of it.

The other scene-independent half (see `optics.py`, which this file imports and
which must never import this one). A beach has the same sky: the same Rayleigh
optical depth, the same solar disc and aureole, the same cosine integral of the
same environment against a normal. So the sky lives here, and with it the
ephemeris that says where the sun was when the reference photograph was taken.

THE ONE BLOCK A SECOND SCENE REPLACES is at the top: the site, the date, the
clock time, and the five hand-set radiometric constants that go with that
particular afternoon -- SUN_DIR, SUN_COL, SKY_TOP, SKY_HOR, SKY_AMB.
EVERYTHING BELOW THEM IS DERIVED FROM THEM and needs no editing at all: change
the hour and the elevation, the azimuth, the air mass, the Rayleigh reddening,
the disc, the aureole and both illuminants follow. They are the SHOOT's
parameters, not the pool's -- which is why they are here and not in `render.py`
-- and a beach photographed on the same afternoon shares them outright.

`?` WHAT IS STILL NOT DERIVED is stated where it lives, and there are two: the
horizon/zenith GRADIENT (SKY_HOR, SKY_TOP and the 0.55 exponent between them),
which is a hand-set profile with a computed lower bound beside it, and SKY_AMB,
whose derived counterpart `SKY_SUB_DERIVED` is computed here and deliberately
not applied.

NOTHING IN THIS FILE PRINTS, for the reasons given at the head of `optics.py`.
"""
import numpy as np

from optics import IOR, fresnel, into_water, r_int_at


# ------------------------------------------------------- WHERE THE SUN ACTUALLY IS
# The three numbers the whole of this file stands on -- the sun's elevation, its
# azimuth and the air mass -- used to enter as a COMMENT above a hand-written
# unit vector:
#
#     # NOAA solar position, Aljezur 37.319N 8.803W, 2026-08-10 18:41 WEST:
#     #   elevation 21.02 deg, azimuth 273.75 deg (due west), air mass 2.77
#
# A comment cannot be re-run at another place, on another date, at another hour,
# and the second scene's reference photographs are timed exactly as this one's
# are. So the ephemeris is code now, and the hand-written vector is checked
# against it rather than trusted.
#
# It is the low-order NOAA/Meeus solution -- Meeus, *Astronomical Algorithms*
# (2nd ed.) ch. 25 and 28, in the reduction NOAA's own solar calculator uses:
# geometric mean longitude and mean anomaly, the equation of centre, the
# apparent longitude with the nutation term in it, the true obliquity, and the
# equation of time from the standard y = tan^2(eps/2) series. Quoted accuracy is
# of order 0.01 deg over this century, which is a fiftieth of the sun's own
# 0.53 deg disc -- and the disc is the angular scale every specular quantity in
# this project is measured against, so that is the right bar.
#
# TWO THINGS HERE ARE SILENT WHEN THEY ARE WRONG, which is the whole reason to
# write it out rather than transcribe a number:
#
#   * THE AZIMUTH QUADRANT. The textbook form solves for cos(Az) and takes an
#     `acos`, which returns [0, pi] and CANNOT distinguish morning from
#     afternoon; the branch is decided by the sign of the HOUR ANGLE and by
#     nothing in the expression. Get it wrong and this scene's 273.75 deg -- an
#     afternoon sun a little north of due west -- comes back as 86.25 deg, a
#     sunrise, while the ELEVATION stays exactly right. Every cosine, every
#     Beer-Lambert path length and every Fresnel term in the file still reads
#     correctly; only the shadows and the specular road point the wrong way, in
#     a scene whose camera was placed on the anti-solar side. That is precisely
#     the class of defect this project has already been bitten by twice (the two
#     azimuth conventions in `render.py`; the camera aimed at the sun for six
#     waves). Written below with `atan2`, which carries the quadrant in the
#     numerator's sign and has no branch left to get wrong.
#   * GEOMETRIC AGAINST APPARENT ELEVATION. Bennett's refraction at 21 deg is
#     +2.57 arcmin. Small -- but it is the difference between a geometric
#     20.978 deg and an apparent 21.020 deg, and the number this file shipped
#     with, 21.02, is the APPARENT one. Air mass is a function of the apparent
#     altitude, so taking the geometric one there would move AIRMASS, and
#     AIRMASS is the constant SUN_COL's colour is read back out of (see the
#     Rayleigh block below). A 0.04 deg slip that propagates into a colour is
#     exactly the kind this file exists to not make.
def _julian_day(y, mo, d, h, mi, s):
    """Julian Day for a UTC civil date, Meeus ch. 7 (Gregorian calendar only --
    this project's dates are all 21st century, and a Julian-calendar branch that
    can never be reached is a branch that can never be tested)."""
    if mo <= 2:
        y, mo = y - 1, mo + 12
    a = y // 100
    b = 2 - a + a // 4
    return (int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + d + b
            - 1524.5 + (h + mi / 60. + s / 3600.) / 24.)


def solar_position(lat_deg, lon_deg, y, mo, d, h, mi, s=0.0, tz=0.0):
    """Where the sun is, from a place and a clock.

    `lat_deg` north-positive, `lon_deg` EAST-positive (so Aljezur is -8.803),
    `tz` the civil offset from UTC in hours (WEST = +1). Returns

        (el_geom, el_app, az, airmass, decl, eot_min, hour_angle_deg)

    with every angle in DEGREES, `el_app` the refracted altitude a camera
    actually sees, and `az` the COMPASS azimuth -- degrees clockwise from north,
    which is the convention the bar's 273.75 is written in and NOT the maths
    convention `render.py` computes its own bearings in. That file states the
    conversion (`math = 90 - compass`) at the point where it first uses a
    bearing, and it states it there because six waves passed with a camera
    pointed at the sun because nobody had.

    Refraction is Bennett (1982) as given in Meeus ch. 16, and air mass is
    Kasten & Young (1989), which is a fit to a real atmosphere rather than the
    plane-parallel 1/sin(h) -- at 21 deg the two differ by 0.7%, and it is the
    Kasten-Young value that reproduces this scene's 2.77."""
    jd = _julian_day(y, mo, d, h - tz, mi, s)
    t = (jd - 2451545.0) / 36525.0                       # Julian centuries, J2000
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.   # mean longitude
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)             # mean anomaly
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)        # eccentricity
    mr = np.deg2rad(m)
    c = (np.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + np.sin(2 * mr) * (0.019993 - 0.000101 * t)
         + np.sin(3 * mr) * 0.000289)                    # equation of centre
    omega = 125.04 - 1934.136 * t                        # lunar node, for nutation
    app_long = l0 + c - 0.00569 - 0.00478 * np.sin(np.deg2rad(omega))
    eps0 = 23. + (26. + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813)))
                  / 60.) / 60.
    eps = eps0 + 0.00256 * np.cos(np.deg2rad(omega))     # true obliquity
    decl = np.rad2deg(np.arcsin(np.sin(np.deg2rad(eps))
                                * np.sin(np.deg2rad(app_long))))
    # the equation of time, in minutes, from the same eps and the same anomaly
    yy = np.tan(np.deg2rad(eps / 2.)) ** 2
    l0r = np.deg2rad(l0)
    eot = 4. * np.rad2deg(yy * np.sin(2 * l0r) - 2 * e * np.sin(mr)
                          + 4 * e * yy * np.sin(mr) * np.cos(2 * l0r)
                          - 0.5 * yy * yy * np.sin(4 * l0r)
                          - 1.25 * e * e * np.sin(2 * mr))
    # true solar time -> hour angle, NEGATIVE before local solar noon and
    # positive after it. That sign is the whole of the azimuth's quadrant.
    tst = ((h - tz) * 60. + mi + s / 60. + eot + 4. * lon_deg) % 1440.
    ha = tst / 4. - 180.
    phi, dec, hr = np.deg2rad(lat_deg), np.deg2rad(decl), np.deg2rad(ha)
    el = np.rad2deg(np.arcsin(np.sin(phi) * np.sin(dec)
                              + np.cos(phi) * np.cos(dec) * np.cos(hr)))
    # atan2, not acos: the numerator is sin(H), so the branch comes for free.
    # The +180 puts it on the compass -- the raw atan2 is measured from SOUTH.
    az = (180. + np.rad2deg(np.arctan2(
        np.sin(hr),
        np.cos(hr) * np.sin(phi) - np.tan(dec) * np.cos(phi)))) % 360.
    el_app = el + (1. / np.tan(np.deg2rad(el + 7.31 / (el + 4.4)))) / 60.
    am = 1. / (np.sin(np.deg2rad(el_app))
               + 0.50572 * (el_app + 6.07995) ** -1.6364)
    return el, el_app, az, am, decl, eot, ha


# The reference photograph's own place and clock, and the first of the two
# blocks a second scene replaces. `tz` is +1: Portugal keeps WEST (UTC+1) in
# August.
SITE_NAME = 'Aljezur'
SITE_LAT, SITE_LON = 37.319, -8.803
SHOOT = (2026, 8, 10, 18, 41, 0.0, 1.0)     # y, m, d, h, min, s, tz hours
(SUN_EL_GEOM, SUN_EL, SUN_AZ, SUN_AM,
 SUN_DECL, SUN_EOT, SUN_HA) = solar_position(SITE_LAT, SITE_LON, *SHOOT)
# The direction TO the sun, in this file's world axes, straight out of the two
# angles above -- and it agrees with the vector that was written by hand to
# 0.006 deg, a fortieth of the sun's own radius. It is computed here so that
# the shipped constant can be MEASURED against it (`render.py` prints the gap)
# without moving a single pixel of the reference frames; see SUN_DIR below.
SUN_DIR_DERIVED = np.array(
    [np.sin(np.deg2rad(SUN_AZ)) * np.cos(np.deg2rad(SUN_EL)),
     np.cos(np.deg2rad(SUN_AZ)) * np.cos(np.deg2rad(SUN_EL)),
     np.sin(np.deg2rad(SUN_EL))])

# THE SHOOT'S OWN RADIOMETRY, and the second half of the block a beach
# replaces. The derivation above reproduces all three of the numbers this
# comment used to assert -- elevation 21.02 deg (apparent), azimuth 273.75 deg
# and air mass 2.77 -- so they are checks now rather than inputs.
#
# SUN_DIR IS LEFT EXACTLY AS IT SHIPPED and that is a decision, not an
# oversight. `SUN_DIR_DERIVED` is 0.006 deg away from it; adopting it would move
# every caustic, every glint and every shadow in the reference frames by a
# hair, and this wave's entire contract is that no rendered pixel moves. The gap
# is a fortieth of the solar radius and two orders below anything the frame can
# resolve, so it is REPORTED (by `render.py`, from these two constants) and not
# absorbed -- the same treatment SKY_AMB gets against `SKY_SUB_DERIVED` below.
# A round that is allowed to move pixels should adopt the derived vector, and
# then the hand-written triple leaves the file for good.
SUN_DIR = np.array([-0.93141, 0.06104, 0.35878])   # +x east, +y north, +z up
SUN_DIR /= np.linalg.norm(SUN_DIR)
SUN_COL = np.array([1.000, 0.892, 0.674]) * 8.6   # golden: AM 2.77, not a noon sun
SKY_TOP = np.array([0.26, 0.46, 0.98])
SKY_HOR = np.array([0.86, 0.90, 0.98])
SKY_AMB = np.array([0.26, 0.42, 0.66]) * 2.15   # clear sky is still a big blue source
# ...but SKY_AMB is the sky the WATER sees, and it is the LAST hand-set
# illuminant in this file. `SKY_DECK` used to sit on the next line as
# `SKY_AMB * 0.30 + SUN_COL * 0.075`; it is now DERIVED, from the same
# environment `sky()` builds, further down this file -- see "THE ILLUMINANTS
# ABOVE THE WATER". SKY_AMB itself is measured against that derivation there
# and the disagreement is reported rather than absorbed.


# --------------------------------------------------------------------------- sky
# The sun and its aureole live in the environment as three cos^n lobes. They are
# named here rather than written inline because they are the ONLY angular
# structure in this sky narrower than the reflection ellipse the footprint
# filter creates below -- the sky gradient itself turns over 90 degrees and a
# few degrees of blur does nothing to it, which is what makes convolving the
# lobes alone the whole of the job and not an approximation of convenience.
# A cos^n lobe is exp(-n th^2 / 2) near its peak, so its per-axis angular
# variance is 1/n, and its flux over the hemisphere is 2 pi / (n + 1).
#
# ALL SIX NUMBERS BELOW WERE GUESSES AND ARE NOW DERIVED. The audit that used to
# sit under this block priced the guess: the disc lobe's peak was 1563x under the
# sun's own radiance and 7.8x too wide, and the three lobes together carried a
# 35th of the direct beam. That is the whole of bar section C's complaint -- a
# broad dim smear where the physics has a small blinding point -- so this round
# replaces the amplitudes and the widths with the atmosphere.
#
# --- THE ATMOSPHERE, READ BACK OUT OF A CONSTANT THIS FILE ALREADY HAD --------
# SUN_COL's COLOUR is not a choice. exp(-m tau_Rayleigh) at the bar's own air
# mass 2.77, evaluated at this file's own three band centres and normalised to
# red, is (1.0000, 0.8921, 0.6740); SUN_COL's triple is (1.000, 0.892, 0.674).
# One part in 10^4 on two channels. So the beam that lights this scene has been
# through a RAYLEIGH atmosphere at the stated air mass and nothing else, which
# fixes three things at once: the air mass is not free, the reddening is not a
# grade, and the aerosol optical depth SUN_COL was written with is ZERO. Every
# lobe below is built on that atmosphere, and the one place a number is added to
# it rather than read out of it is marked.
def _tau_rayleigh(lam_um):
    """Whole-atmosphere Rayleigh optical depth at sea level: the standard
    0.008569 lam^-4 form with its two dispersion corrections (Hansen & Travis
    1974). Not fitted here -- it is what makes the check above a check."""
    return 0.008569 * lam_um ** -4 * (1. + 0.0113 * lam_um ** -2
                                      + 0.00013 * lam_um ** -4)


# AIRMASS is no longer asserted either: `SUN_AM` above is Kasten-Young at the
# apparent elevation this file's own ephemeris returns, and it comes to 2.7702.
# The 2.77 below is that number, rounded where it was first written down, and it
# is kept at four digits' worth of precision rather than replaced for the same
# reason SUN_DIR is -- exp(-m tau) is what SUN_COL's colour is read out of, and
# a change in the fifth digit of m is a change in the frames. `render.py` prints
# both.
AIRMASS = 2.77                                     # the bar's, for elevation 21
TAU_R = _tau_rayleigh(np.array([620., 545., 460.]) / 1000.)


# --- LOBE 1, THE DISC: nothing free at all -----------------------------------
# `shade` uses SUN_COL as E_n/pi, so E_n = pi*SUN_COL is the normal irradiance
# and the disc's radiance is E_n / Omega_sun with Omega_sun the disc's own solid
# angle. A cos^n lobe carries 2 pi / (n + 1); setting that equal to Omega_sun
# gives n = 2/theta_s^2 - 1 and then a peak of L_sun makes the lobe's FLUX equal
# the direct beam exactly. Peak, width and flux all land on the sun at once --
# there is no amplitude left to choose, which is the point.
THETA_SUN = np.deg2rad(0.53) / 2.0                 # solar angular radius
OMEGA_SUN = np.pi * THETA_SUN ** 2                 # 6.72e-5 sr
E_SUN = np.pi * SUN_COL                            # normal irradiance, 24.1 green
L_SUN = E_SUN / OMEGA_SUN                          # 3.59e5 green
N_DISC = 2.0 / THETA_SUN ** 2 - 1.0                # 93493

# --- LOBE 2, THE AUREOLE THIS ATMOSPHERE ACTUALLY HAS ------------------------
# The aureole is single-scattered sunlight and its radiance follows from the
# same plane-parallel integral the beam does. Scattering at optical depth tau'
# feeds the view direction at F_0 exp(-tau'/mu_0) omega P(Theta) / (4 pi) and the
# result is attenuated out again; in the sun's OWN direction mu = mu_0, the
# integral collapses to F_0 m tau exp(-m tau) P / (4 pi), and F_0 exp(-m tau) is
# the beam that arrives, which is E_n. So
#     L(Theta) = (E_n / 4 pi) P(Theta) m tau_sca
# with no free scale: the aureole is the beam times a phase function times the
# slant scattering optical depth, and the atmosphere above has already fixed
# tau_sca -- it is tau_Rayleigh, whose single-scattering albedo is exactly 1.
#
# Rayleigh's phase function is 3/4 (1 + cos^2 Theta), which splits into an
# ISOTROPIC 3/4 -- a uniform sky, which is what SKY_HOR/SKY_TOP and their
# elevation gradient already carry -- plus 3/4 cos^2 Theta, which is the whole
# of the forward structure a Rayleigh atmosphere has. cos^2 IS a cos^n lobe,
# with n = 2, so the aureole needs no fitting at all:
#     amp = (E_n / 4 pi) m tau_R * 3/4,   n = 2.
# It is broad and it is faint -- 0.4 against a sky of about 1.0 -- and that is
# the point: a clean atmosphere has no compact aureole, because a compact
# aureole is a DIFFRACTION peak and diffraction needs particles.
N_AURE = 2.0
L_AURE = (E_SUN / (4. * np.pi)) * AIRMASS * TAU_R * 0.75

# --- LOBE 3, THE AEROSOL AUREOLE: DERIVED TO ZERO, AND MEASURED THERE --------
# What is NOT here, and why, because its absence is a result rather than an
# omission. A real coastal afternoon carries tau_a ~ 0.1 of aerosol, and an
# aerosol aureole is a genuine feature: for particles large against the
# wavelength the extinction efficiency tends to 2 and exactly HALF of it is
# diffraction -- the Airy pattern of the particle's own shadow -- which is a
# forward peak a few degrees wide, the aureole a photographer sees. The other
# half is refraction and reflection, broad, Henyey-Greenstein at the asymmetry
# quoted for tropospheric aerosol. Two mechanisms, two widths, one optical
# depth: the previous cos^260 and cos^14 were sitting almost exactly on those
# two widths, which is why only their amplitudes were wrong.
#
# THE REASON IT IS ZERO IS ENERGY, NOT TASTE. SUN_COL's colour is Rayleigh
# extinction alone, so the beam that lights this frame was never dimmed by
# aerosol. Adding aerosol scattering to the environment without removing it from
# the beam creates the light twice, and it creates it exactly where a reflection
# is most sensitive to it. Dimming the beam instead means changing SUN_COL,
# which relights every diffuse surface in the frame and is a round of its own.
# So the environment is built from the atmosphere the beam actually came
# through, and the aerosol pair waits for the round that can afford both halves.
#
# WHAT IT WOULD COST, measured rather than guessed: this file was rendered with
# that pair in, at tau_a(550) = 0.10, Angstrom 1.0, single-scattering albedo
# 0.95, half of the coarse mode's scattering in a 2.0 um diffraction peak. It
# put a peak radiance of 72 into a 3.4 deg lobe and 15 into a 13.5 deg one, and
# on the picture it moved the mirror band's REFLECTED median from 0.16 to 4.04
# -- past this file's own white point of 11.2 once the disc's glints are added
# on top -- and took the far water's mean luminance to 245 of 255 with 98% of it
# over 200. A frame shot along the sun's azimuth cannot hold both a hazy sky and
# a legible bed, which is a statement about the reference photograph's weather
# as much as about this renderer.

# sky() multiplies the WHOLE environment by 1.15, and the background wants it --
# it is what makes what sky() returns agree with SKY_AMB. The amplitudes below
# are absolute RADIANCES and must not be scaled a second time, so each carries
# 1/1.15 and the product is the derived peak exactly.
_UNSCALE = 1.0 / 1.15
SKY_LOBE = ((_UNSCALE, N_DISC, L_SUN),             # the disc
            (_UNSCALE, N_AURE, L_AURE))            # the Rayleigh aureole


# --- THE DIRECTIONAL EXPONENT, AND THE ONE PLACE THIS FILE CREATED LIGHT ------
# `n_eff` used to be `1 / (u^T Q u)`. That is the PROJECTION variance -- the
# width of the shadow the summed Gaussian casts on the u axis -- and what the
# lobe is asked for is the Gaussian's VALUE along u, which is the other one.
# Written out, because the whole repair is three terms and a sign:
#
#   * a cos^n lobe is exp(-n rho^2 / 2) near its peak, so as a function of the
#     2-D tangent offset u it is a Gaussian of covariance Q_0 = (1/n) I;
#   * convolved with the reflection ellipse C it is a Gaussian of covariance
#     Q = Q_0 + C, whose DENSITY at u is exp(-1/2 u^T Q^-1 u) -- the inverse,
#     because that is what a Gaussian's exponent is written with;
#   * writing that back as cos^(n_eff)(|u|) = exp(-n_eff |u|^2 / 2) therefore
#     forces n_eff |u|^2 = u^T Q^-1 u, i.e.
#
#         n_eff = u_hat^T Q^-1 u_hat
#               = (u1^2 q22 - 2 u1 u2 q12 + u2^2 q11) / (|u|^2 det Q)
#
#     the 2x2 adjugate over the determinant: the SAME three terms the file
#     already had, with q11 and q22 swapped and the cross term's sign flipped.
#
# WHY THE ISOTROPIC CASE HID IT, and this sentence is the whole lesson: for
# Q = q I the inverse is (1/q) I, so u^T Q^-1 u = 1/q and u^T Q u = q, and the
# two expressions are not merely close -- they are the same number, for every
# u, exactly. They agree on either principal axis as well. Every row this file
# ever had on the lobes was taken at cov = None (Q_0 = (1/n) I, isotropic by
# construction) or on axis, so the suite was pinned to the one place in the
# expression's domain where the wrong form cannot be told from the right one.
# A degenerate case is not a weak test of the general one; it is no test of it.
#
# WHAT IT COST, in closed form rather than by inspection. In the small-angle
# limit the widened lobe's flux is g INT dphi / n_eff(phi), and with Q's
# eigenvalues l1, l2:
#     correct   INT dphi / (u^T Q^-1 u) = 2 pi sqrt(l1 l2) = 2 pi sqrt(det Q),
#               so the flux is g 2 pi sqrt(det Q) = 2 pi / n -- CONSERVED, which
#               is exactly the property `g` was derived to give it;
#     shipped   INT dphi (u^T Q u) = pi (l1 + l2) = pi tr Q,
#               so the flux is (l1 + l2) / (2 sqrt(l1 l2)) times that.
# The gain is therefore cosh(ln(r)/2) with r = l1/l2 the ellipse's eigen-ratio,
# and nothing else: 1 at r = 1 (the degeneracy above, and it is why `g` still
# normalised the lobe there), 1.06 at r = 2, 1.37 at r = 5.3, 34.8 at r = 4832.
# By Cauchy-Schwarz (u^T Q u)(u^T Q^-1 u) >= 1, so the shipped exponent was
# never larger than the right one: the lobe was never too narrow, always too
# wide, and since `g` was computed for the CORRECT Gaussian it no longer
# normalised what it multiplied. The lobe CREATED energy, monotonically in the
# anisotropy, and this file's only anisotropic caller -- `render.py`'s open
# water, where the reflection ellipse is stretched by 1/cos(theta_v) along the
# view azimuth -- runs r = 1.75 to 12.2 over its own frame, weighted by pixels,
# and paid 1.04x to 1.89x for it with a median of 1.17x.
#
# FOUND BY THE RASTER REFERENCE (`raster-impl/waves.py`, `widened_lobes`),
# which is an independent code path over the same shared module and is the
# first thing in this project to reach an anisotropic Q at all. Its own frame
# prices the same defect at 12.0x on its p99. `validate.py` now carries the
# energy row on an ANISOTROPIC lobe, which is the row that would have caught
# it, and an absolute one beside it.
def _lobe_shape(n, cov):
    """One cos^n lobe of the environment, convolved with the reflection ellipse
    that the UNRESOLVED slope variance puts on the mirror direction.

    Two Gaussians convolve to a Gaussian whose covariance is the sum and whose
    INTEGRAL is unchanged, so the peak falls by sqrt(det Q_0 / det Q). Writing
    the widened lobe back as cos^(n_eff) rather than as exp(-n_eff th^2 / 2)
    costs nothing and buys the one property that matters here: at cov = None it
    is EXACTLY the expression this file had before, so the unfiltered path is
    bit-for-bit the old one and the sky behind the pool never moves.

    n_eff is directional -- u_hat^T Q^-1 u_hat, the summed Gaussian's own
    exponent along the direction of the offset to the sun -- which is how the
    anisotropy survives. WIND is a 45 deg spread about the wind azimuth and the
    wake is directional, so what the filter removes is a Cox-Munk ellipse and a
    lobe widened by its trace would be visibly wrong across the wind. On the
    axis (offset zero) every direction gives cos^n = 1 and only the peak factor
    is doing anything, so the fallback there is the DIRECTIONAL MEAN of the same
    quantity, tr(Q^-1)/2 -- which is the trace of the inverse and not the
    inverse of the trace, for the reason given in the block above."""
    if cov is None:
        return 1.0, n
    u1, u2, c11, c12, c22 = cov
    q11 = 1.0 / n + c11
    q22 = 1.0 / n + c22
    det = np.maximum(q11 * q22 - c12 * c12, 1e-30)
    g = (1.0 / n) / np.sqrt(det)
    r2 = u1 * u1 + u2 * u2
    ne = np.where(r2 > 1e-16,
                  (u1 * u1 * q22 - 2.0 * u1 * u2 * c12 + u2 * u2 * q11)
                  / np.maximum(r2, 1e-16) / det,
                  0.5 * (q11 + q22) / det)
    # both clamps are unreachable for the covariance a slope tensor can produce
    # -- C is PSD, so Q = (1/n) I + C has det >= (c11 + c22)/n + 1/n^2 > 0 and
    # an adjugate form that is non-negative -- and they are kept as the sign
    # that says so. A row in `validate.py` fires at a caller that breaks it.
    return g, np.maximum(ne, 1e-12)


SKY_DIFFUSE_LOBES = SKY_LOBE[1:]    # everything but the disc -- see below


def sky(dx, dy, dz, cov=None, lobes=None):
    t = np.clip(dz, 0, 1)[:, None] ** .55
    col = SKY_HOR[None] * (1 - t) + SKY_TOP[None] * t
    cs = np.clip(dx * SUN_DIR[0] + dy * SUN_DIR[1] + dz * SUN_DIR[2], 0, 1)
    for amp, n, c in (SKY_LOBE if lobes is None else lobes):
        g, ne = _lobe_shape(n, cov)
        if cov is None:
            col = col + c[None] * amp * (cs ** ne)[:, None]
        else:
            col = col + c[None] * amp * (g * cs ** ne)[:, None]
    return col * 1.15


# ================== THE ILLUMINANTS ABOVE THE WATER, FROM ONE ATMOSPHERE ======
# `SKY_DECK = SKY_AMB * 0.30 + SUN_COL * 0.075` was the longest-standing
# underived constant in this file -- 1.74 stops written by hand, filed as open
# in the README for the whole project, and applied to two receivers that are at
# RIGHT ANGLES to each other: the horizontal coping and paving, and the
# VERTICAL, poolward-facing freeboard band. It is closed here, and so is the
# second illuminant, and neither is a fit.
#
# THE POINT IS THAT THERE IS NOTHING LEFT TO CHOOSE. An illuminant for a
# diffuse receiver is one number:
#
#     E(N)/pi = (1/pi) INT_hemisphere L(w) (w.N)_+ dw
#
# and this file already OWNS L(w): `sky()` is a complete environment -- a
# horizon/zenith gradient and two cos^n lobes whose amplitudes were derived,
# the previous round, from the same Rayleigh atmosphere that reddens SUN_COL
# (AIRMASS = 2.77, TAU_R from the file's own `_tau_rayleigh`). So both
# illuminants are the same integral of the same environment against two
# different normals, and the only judgement in them is which lobes belong.
#
# WHICH LOBES BELONG: everything except the disc. `SKY_LOBE[0]` is the sun's
# own disc, and the audit above proves it carries the beam EXACTLY -- its flux
# is pi*SUN_COL to a part in a thousand. Every diffuse receiver in this file
# already gets that beam as an explicit `SUN_COL * (N.L) * vis` term, so
# integrating the disc into an illuminant as well would light the frame with
# two suns. The aureole is not the beam: it is light Rayleigh-scattered OUT of
# the beam, it arrives from directions the beam does not, and it is skylight.
# `SKY_DIFFUSE_LOBES` is that partition and `sky()` takes it as an argument, so
# a later round that moves a lobe moves both illuminants with it.
def env_diffuse(dx, dy, dz):
    """The environment MINUS the sun's disc, in absolute radiance: the sky
    gradient and the Rayleigh aureole. Same code path as `sky()` -- a row in
    `validate.py` asserts `env_diffuse + disc == sky` over 4096 directions, so
    the two cannot drift."""
    return sky(dx, dy, dz, lobes=SKY_DIFFUSE_LOBES)


# The quadrature. Uniform in cos(theta) and in phi, which is the measure the
# integrand is written against -- no cosine has to be reintroduced by hand and
# the solid angle is one constant. 256 x 512 costs 3 MB and converges the deck
# to 6 significant figures; `validate.py` runs it again at 1024 x 2048 and
# compares, and also against a closed form the quadrature cannot see.
ENV_NMU, ENV_NPH = 256, 512
_emu = (np.arange(ENV_NMU) + .5) / ENV_NMU              # cos from the zenith
_eph = (np.arange(ENV_NPH) + .5) / ENV_NPH * (2. * np.pi)
_est = np.sqrt(np.maximum(1. - _emu ** 2, 0.))
ENV_DX = np.repeat(_est, ENV_NPH) * np.tile(np.cos(_eph), ENV_NMU)
ENV_DY = np.repeat(_est, ENV_NPH) * np.tile(np.sin(_eph), ENV_NMU)
ENV_DZ = np.repeat(_emu, ENV_NPH)
ENV_DW = (1. / ENV_NMU) * (2. * np.pi / ENV_NPH)        # d(mu) d(phi), sr
ENV_L = env_diffuse(ENV_DX, ENV_DY, ENV_DZ)


def env_irradiance(nx, ny, nz, weight=None, nmu=None, nph=None, L=None):
    """E(N)/pi over the SKY hemisphere, per channel -- an illuminant in exactly
    the units every diffuse term in this file is written in, so that a facet of
    albedo `a` and unobstructed sky comes out at `a * env_irradiance(N)`.

    `weight` multiplies the integrand per direction and is how an occluder or an
    interface goes inside the integral rather than beside it. `nmu`/`nph`
    rebuild the lattice at another resolution, which is how the suite measures
    this quadrature's own error instead of assuming it. `L` replaces the
    environment -- a UNIFORM L must give exactly L on a horizontal face and
    exactly L/2 on a vertical one, which is the row that fires at a dropped
    1/pi or a wrong solid angle."""
    if nmu is None and nph is None:
        dx, dy, dz, dw = ENV_DX, ENV_DY, ENV_DZ, ENV_DW
        L = ENV_L if L is None else np.broadcast_to(np.asarray(L, float),
                                                    ENV_L.shape)
    else:
        nmu, nph = nmu or ENV_NMU, nph or ENV_NPH
        m = (np.arange(nmu) + .5) / nmu
        p = (np.arange(nph) + .5) / nph * (2. * np.pi)
        s = np.sqrt(np.maximum(1. - m ** 2, 0.))
        dx = np.repeat(s, nph) * np.tile(np.cos(p), nmu)
        dy = np.repeat(s, nph) * np.tile(np.sin(p), nmu)
        dz = np.repeat(m, nph)
        dw = (1. / nmu) * (2. * np.pi / nph)
        L = (env_diffuse(dx, dy, dz) if L is None
             else np.broadcast_to(np.asarray(L, float), (dx.size, 3)))
    w = np.clip(dx * nx + dy * ny + dz * nz, 0., None) * dw
    if weight is not None:
        w = w * np.asarray(weight, float)
    return (L * w[:, None]).sum(0) / np.pi


# --- ILLUMINANT ONE: the horizontal deck ------------------------------------
SKY_DECK = env_irradiance(0., 0., 1.)


# `?` WHAT IS STILL NOT DERIVED, stated exactly. The two LOBES come from the
# file's Rayleigh atmosphere; the GRADIENT (SKY_HOR, SKY_TOP and the 0.55
# exponent between them) does not -- it is a hand-set profile and it always
# was. What the atmosphere CAN say about it is a lower bound, and the bound is
# computed rather than asserted: single-scattered Rayleigh radiance for a
# ground observer at view cosine mu_v with the sun at mu_s is
#     L = (F0 P(Theta)/4pi) mu_s (e^{-tau/mu_v} - e^{-tau/mu_s}) / (mu_v - mu_s)
# with F0 = E_SUN e^{+tau m} the top-of-atmosphere beam this file's own SUN_COL
# implies. That form is a LOWER bound on a real sky by construction: it has no
# multiple scattering and no ground return, and at tau_R(blue) = 0.20 those are
# not small. What is missing from the gradient is therefore named -- the
# second and higher orders of the sky's own radiative transfer, and the
# albedo of the ground under it -- rather than left as "a choice".
def _ss_rayleigh(mu_v, cos_theta):
    """Single-scattered Rayleigh sky radiance, per channel."""
    mu_s = float(SUN_DIR[2])
    f0 = E_SUN * np.exp(TAU_R * AIRMASS)
    p = 0.75 * (1. + np.asarray(cos_theta, float) ** 2)
    mv = np.maximum(np.asarray(mu_v, float), 1e-4)
    d = mv - mu_s
    d = np.where(np.abs(d) < 1e-5, 1e-5, d)
    return (f0[None] * (p / (4. * np.pi))[:, None]
            * mu_s * (np.exp(-TAU_R[None] / mv[:, None])
                      - np.exp(-TAU_R[None] / mu_s)) / d[:, None])


# --- AND THE THIRD ILLUMINANT, MEASURED AND NOT MOVED ------------------------
# SKY_AMB is the level of the sky every SUBMERGED receiver gets. The same
# integral prices it, because the Snell window is a change of variables and
# nothing else: n^2 cos(t_w) sin(t_w) dt_w = cos(t_a) sin(t_a) dt_a maps the
# window integral of the n^2-gained sky exactly onto the air-side hemisphere, so
# a bed point's sky irradiance is the DECK's, less what the surface reflects
# away. That number is computed here and compared with SKY_AMB, and it is NOT
# applied: this round's control is that nothing below the waterline moves, and
# moving SKY_AMB moves the wall and the band together, which would make the one
# ratio this work exists to report unattributable.
_RBAR = (ENV_L * fresnel(ENV_DZ)
         * (np.clip(ENV_DZ, 0., None) * ENV_DW)[:, None]).sum(0) / np.pi / SKY_DECK
SKY_SUB_DERIVED = SKY_DECK * (1. - _RBAR)


# ================= THE INTERFACE UNDER THIS SKY, AND NOT UNDER A CONSTANT =====
# The last two things in this file are the ones that need BOTH halves of the
# physics: the sky's own horizon/zenith profile, and the Snell window that a
# submerged face sees it through. They live here rather than in `optics.py`
# because the dependency has to run one way -- optics knows nothing about a sky
# -- and they are as scene-independent as everything above: a beach's sandbar
# is a submerged horizontal face and its rock is a submerged vertical one, and
# these are the two shares they get.
def sky_diffuse(mu_air):
    """`sky()`'s diffuse term and nothing else, as a function of the air-side
    direction's cosine from the vertical. The three SUN LOBES are deliberately
    left out: for a submerged receiver the sun arrives as the refracted beam and
    is already counted as `SUN_COL * cos_i * TSUN * cau`, so putting the disc in
    here would be that beam a second time. What it does keep is the horizon /
    zenith gradient, which is the part that matters: the OUTER window -- the
    directions a vertical face weights most -- looks at the air-side horizon,
    and SKY_HOR is brighter than SKY_TOP in red and green and equal in blue."""
    t = np.clip(np.asarray(mu_air, float), 0, 1)[..., None] ** .55
    return (SKY_HOR[None] * (1 - t) + SKY_TOP[None] * t) * 1.15


def window_shares(profile=True, ior=None):
    """(W_bed, W_vert), per channel: the (1/pi) INT L cos dw that a HORIZONTAL
    and a VERTICAL submerged face collect from the Snell window, with L the
    transmitted, n^2-gained sky. `profile=False` sets L to 1 and must reproduce
    the two closed forms 1/n^2 and 0.5 - tir_vert(tc)*(1 - 1/n^2) -- which is
    the row `validate.py` fires at this quadrature, since neither closed form
    can be written from the integrand."""
    ior = IOR if ior is None else np.asarray(ior, float)
    Wb, Wv = np.zeros(3), np.zeros(3)
    for c in range(3):
        tc = np.arcsin(1.0 / ior[c])
        t = (np.arange(40000) + .5) / 40000 * tc
        st, ct = np.sin(t), np.cos(t)
        if profile:
            ca = np.sqrt(np.maximum(1. - (ior[c] * st) ** 2, 0.))
            L = (1. - r_int_at(ct)[:, c]) * into_water(sky_diffuse(ca))[:, c]
        else:
            L = np.ones_like(t)
        Wb[c] = 2. * np.sum(L * ct * st) * (tc / 40000)
        Wv[c] = (2. / np.pi) * np.sum(L * st * st) * (tc / 40000)
    return Wb, Wv


WIN_BED, WIN_VERT = window_shares(True)
SKY_VERT = WIN_VERT / WIN_BED       # a vertical submerged face's sky, as a
                                    # multiple of the BED's -- the number that
                                    # replaces WALL_SKY under the water
