"""
Water, and the interface it presents to the air.

The scene-independent half of the optics: everything here is a property of the
MEDIUM and of the boundary, and nothing here knows what shape the water is in.
Extracted from `render.py` unchanged -- every constant, every derivation, every
refuted hypothesis and every `?` travels with the code it explains -- because a
second reference scene is coming (a beach, for waves, shoaling, breaking and
coastal optics) and the default outcome of a second scene is a fork that
drifts. `field.py` and `wake.py` were already out; this is the rest of the
physics, and the test applied to every line was one question: WOULD A BEACH
NEED EXACTLY THIS, UNCHANGED?

So there is no pool in this file. No DEPTH, no basin, no liner, no camera, no
sun. Where a function needs a length of water column it takes that length as an
ARGUMENT -- `slab_esc(dep, ...)` and not `slab_esc(dep=DEPTH, ...)`. That is the
only signature change the extraction made and it is the whole point of it: a
beach's depth is a field, a pool's DEPTH is its deepest point, and a default
argument drawn from one scene is exactly the hidden coupling this split exists
to prevent. `rho_water` likewise takes the sun's cosine rather than reaching out
of the module for the pool file's `cos_i`.

WHAT IS NOT HERE, so that nobody goes looking:
  * the atmosphere, the sun, the sky and the two derived illuminants --
    `atmosphere.py`, which imports THIS file for `fresnel`, `into_water` and
    `r_int_at`. The dependency runs one way and must keep running one way.
  * the wave surface -- `field.py`; the jet's stationary wake -- `wake.py`.
  * anything that is only true of a rectangular liner basin -- `render.py`.
    The list of what deliberately stayed behind, and why, is in the README.

NOTHING IN THIS FILE PRINTS. Every diagnostic that used to sit beside these
constants is still in `render.py`, reading the values back across the import.
That is deliberate twice: a module that prints on import pollutes `validate.py`,
and leaving every `print` exactly where it was is what made this extraction
CHECKABLE -- `render.py`'s stdout is unchanged line for line, and the frames it
writes are bit-for-bit the ones it wrote before.
"""
import numpy as np


IOR = np.array([1.3320, 1.3348, 1.3400])     # 620 / 545 / 460 nm
LAM = np.array([0.620, 0.545, 0.460])        # the wavelengths those three ARE, um
# Pure-water absorption, m^-1. PURE water -- Pope & Fry (1997), Appl. Opt.
# 36(33) 8710-8723, the integrating-cavity measurement that is the modern
# standard and the one this project's own bibliography names.
#
# THESE ARE BAND MEANS, NOT POINT SAMPLES, and that is a decision, not an
# accident. `a(lambda)` at the three nominal wavelengths is (0.2755, 0.0511,
# 0.00979); averaged over the Voronoi bands defined thirty lines below --
# 582.5-657.5, 502.5-582.5, 417.5-502.5 nm, which is what a channel of this
# renderer actually integrates -- the same table gives
#
#     a_band = (0.26170, 0.052988, 0.010224) m^-1
#
# The file's own doctrine two paragraphs down is that *a channel is a BAND, not
# a wavelength*; the bands tile 417.5-657.5 with no gap and no overlap, and every
# other spectral quantity here (n, the caustic eta, the dispersion sweep) is
# already sampled through them. Taking `a` at a delta function while everything
# beside it is taken over a band is the inconsistency, and `a` is the quantity
# where it costs most: it is strongly curved across the red band (0.0896 at
# 580 nm to 0.3400 at 650), so the point value and the band mean differ by 5.0%
# there. The band reading is the one this file's own model asks for. (A band mean
# of `a` is still an approximation -- Beer-Lambert over a band is the log of a
# mean of exponentials, not the mean of the exponents -- but it is first-order
# right where the point sample is not even that.)
#
# WHAT WAS WRONG BEFORE: (0.2750, 0.0546, 0.0145). Red was Pope & Fry at 620 nm
# to 0.2%; green was 6.9% high; and blue was 0.0145, which is Smith & Baker
# (1981) at 450 nm EXACTLY -- 48% above Pope & Fry, the wrong paper at the wrong
# wavelength, in a project whose own provenance file bans Smith & Baker for blue
# by name (that era's blue is contaminated by scattering in natural water).
# Two independent passes reached the same identification. `validate.py` tier 2
# checks this triple against both tables, point-sampled and band-integrated.
ABS = np.array([0.2617, 0.05299, 0.01022])
F0 = ((IOR - 1.0) / (IOR + 1.0)) ** 2

# --- WHAT LEAVES THE WATER, AND THE FACTOR THAT IS NOT FRESNEL ---------------
# Radiance is NOT conserved across a refracting interface. What is conserved
# along a ray is the basic radiance L/n^2, because a pencil's etendue n^2 dA
# dOmega is: Snell compresses the solid angle by exactly the factor n^2 that the
# projected area does not. So an in-water radiance L_w arriving at the surface
# leaves as
#
#       L_air(theta_v) = T(theta_v) * L_w / n^2,     n^2 = 1.774/1.782/1.796
#
# and Fresnel's T alone is only PART of the transport. This is not a fudge and
# it is not small: 1/n^2 is 0.827-0.844 stops, and it applies to the transmitted
# column of every water pixel while the reflected column beside it is air-side
# and already right -- so leaving it out is a RELATIVE error between the two
# halves of one pixel, which is the one thing no exposure can absorb.
#
# TWO CHECKS THAT IT IS THE RIGHT WAY UP. Both are in `validate.py`:
#   * hemispherically, (1/pi) INT T(mu) (1/n^2) cos dw over the air-side
#     hemisphere is (1 - R_EXT)/n^2 = 1 - R_INT -- the diffuse transmittance OUT
#     of water, which the file already computes by reciprocity for the wet-liner
#     term and which the Egan & Hilgeman fit agrees with to 0.09%.
#   * energetically, a pool with a PERFECT WHITE bed and no absorption must have
#     an apparent albedo of exactly 1. Composed through this function it does;
#     composed without the divisor it comes to 1.73, which is not a taste.
# It was shipped without the divisor for several rounds and is item 5 of 12a's
# `What did not reproduce`; what it had been absorbing is written up there.
N2 = IOR ** 2


def out_of_water(L_w):
    """An in-water radiance, as seen from the air side of the surface. Fresnel's
    T is applied by the caller (it depends on the view angle); this is the part
    that does not, and it is the part that was missing. ONE function so that
    there is exactly one place in the file where a radiance crosses out of the
    medium, and so that `validate.py` has something to integrate."""
    return np.asarray(L_w) / N2[None]


def into_water(L_a, n2=None):
    """The SAME law, run the other way: an air-side radiance as seen from inside
    the water. `out_of_water` divides by n^2 because the pencil's solid angle
    opens out on the way up; a pencil coming DOWN is compressed by exactly the
    same factor, so what an in-water eye sees is

          L_water(theta_w) = T(theta_a) * L_air(theta_a) * n^2

    with the caller applying Fresnel's T, as above. `into_water(out_of_water(L))`
    is the identity, and `validate.py` asserts it -- which is the whole content
    of "L/n^2 is what is conserved" (Nicodemus 1963; see
    `references/12-water-rendering.md`), stated as code rather than as a factor.
    This is the FIRST call site in the project that crosses the interface in the
    gaining direction: everything before it was a view into the medium.

    `n2` overrides the band-nominal N2 for a wavelength sampled inside a band, so
    that the gain and the refraction that produced the direction are taken at one
    and the same index."""
    return np.asarray(L_a) * (N2[None] if n2 is None else n2)


# --- WET LINER, DERIVED RATHER THAN DIALLED ----------------------------------
# A film of water on a NON-POROUS substrate darkens it by a mechanism with no
# free parameter: light crosses the air/water interface twice, and between the
# crossings it is trapped by total internal reflection. With R_EXT the diffuse
# external reflectance of that interface -- integrated here from THIS FILE'S
# own per-channel Fresnel over a cosine-weighted hemisphere, so no constant
# enters -- and R_INT = 1 - (1 - R_EXT)/n^2 by reciprocity, a substrate of dry
# albedo `a` reads
#       a_wet = R_EXT + (1 - R_EXT)(1 - R_INT) a / (1 - a R_INT)
# The wet band at the foot of the blue is therefore a measured fraction of the
# dry one, and it is printed rather than chosen.
#
# HOISTED TO HERE from beside the freeboard band, because `1 - R_INT` is the
# DIFFUSE form of `out_of_water` above -- (1 - R_EXT)/n^2, the share of an
# isotropic in-water radiance that gets out at all -- and WBOUNCE, six hundred
# lines below, needs exactly that number. It used to carry a hand-written 0.5
# in its place. Same interface, same transport, two call sites; now one source.
_wmu = ((np.arange(512) + .5) / 512.)[:, None]
_wct = np.sqrt(np.maximum(1. - (1. - _wmu ** 2) / IOR[None] ** 2, 0.))
_wrs = ((_wmu - IOR[None] * _wct) / (_wmu + IOR[None] * _wct)) ** 2
_wrp = ((IOR[None] * _wmu - _wct) / (IOR[None] * _wmu + _wct)) ** 2
R_EXT = (2. * _wmu * .5 * (_wrs + _wrp)).mean(0)
R_INT = 1. - (1. - R_EXT) / IOR ** 2
T_OUT_DIFFUSE = 1. - R_INT       # = (1 - R_EXT)/n^2 = 0.526/0.524/0.519


def wet_albedo(a):
    """AIR-SIDE apparent albedo of [water film + substrate], given the
    substrate's WATER-SIDE reflectance `a`. The two sides are not the same
    number and the whole point of this function is the map between them.

    IN  `a`     what the substrate returns to the water touching it. No air in
                it, no interface in it.
    OUT         what an eye in the AIR sees looking at the wet substrate: `a`
                with the film's own surface reflection added at the front and
                two interface crossings and a trapped series wrapped round it.

    THE RETURN VALUE IS NOT AN ADMISSIBLE ARGUMENT TO THIS FUNCTION, NOR TO
    `rho_water`, and this project has spent six waves learning that one
    sentence. `wet_albedo(wet_albedo(a))` and `rho_water(wet_albedo(a), ...)`
    are both syntactically fine, both monotone, both energy-conserving and both
    wrong: they cross the interface twice more than the physics does. The
    identity that pins which side is which, and it is a suite row in both
    `validate.py` and `validate_beach.py`:

        wet_albedo(a) - R_EXT == (1 - R_EXT) * a * slab_esc(0) * trap_gain(a, 0)

    -- i.e. this function IS `rho_water` with the water column set to zero and
    the sun's directional Fresnel replaced by its hemispherical average. Same
    transport, same interface, two names, one argument convention.

    (The two sides differ by 7.14x diffusely -- R_EXT = 6.669% out of the air
    against R_INT = 47.617% out of the water -- which is why an extra crossing
    is never a rounding error.)"""
    return R_EXT[None] + (1. - R_EXT[None]) * (1. - R_INT[None]) * a / (
        1. - a * R_INT[None])


# --- THE POOL'S OWN ALBEDO, IN CLOSED FORM ------------------------------------
# `wet_albedo` above is the same physics over a film thin enough to have no
# absorption in it. A POOL is that chain with a 1.40 m column in every leg, and
# it is the quantity that settles the water-to-deck comparison without a
# photograph, an exposure or a camera: a deck and a water surface are both
# HORIZONTAL, so the irradiance that lights them is the same number and cancels
# in their ratio, leaving two albedos. Written in FLUX rather than radiance,
# which is what keeps the n^2 inside R_int instead of carried loose:
#
#   rho_w = (1 - R_ext(sun)) * T_slant * rho_bed * T_up * (1 - R_int)
#                            / (1 - rho_bed * T_up * T_dn * R_int)
#
# Every factor has a name: the beam gets in, crosses to the bed at the REFRACTED
# slant, is reflected, crosses back up, and gets out -- with the geometric series
# counting the light the underside sends back down and the bed sends back up.
#
# THE UP LEG IS IN THE NUMERATOR AND IT IS EASY TO DROP. The writing this round
# was handed had `T_slant * rho_bed * (1 - R_int) / (1 - rho_bed * T_round *
# R_int)`: a round trip in the denominator and no one-way transmission in the
# numerator at all. That over-states the answer by 1/T_up -- 13.0% in luminance
# at this depth and 85% in red -- and it is the whole of why the prediction that
# opened the round read 0.61-1.00 where the corrected form reads 0.55-0.88. The
# numerator must carry exactly ONE up leg and the denominator exactly one round
# trip; `validate.py` pins that with a limit no arithmetic slip can reach.
#
# T_up and T_dn are the same number and it is NOT exp(-a d). A Lambertian bed
# radiates over a cosine distribution, so the flux transmittance of the column
# is <exp(-a d / mu)> over the measure 2 mu dmu, which is the third exponential
# integral,   T_diff = 2 E_3(a d),   evaluated below by Gauss-Legendre on mu and
# by nothing else. At this depth it is 0.542 / 0.871 / 0.972 against the vertical
# exp(-a d) of 0.694 / 0.929 / 0.986: the diffuse path is longer than the
# vertical one and the difference is a fifth of the red.
def _e3(x):
    """2 E_3(x) -- the cosine-weighted flux transmittance of a slab of optical
    depth x, by Gauss-Legendre on mu in (0, 1]. The leading 2 is the
    normalisation of the measure 2 mu dmu; dropping it halves every answer, and
    that is exactly what the first writing of this block did."""
    _m, _w = np.polynomial.legendre.leggauss(400)
    _m, _w = .5 * (_m + 1), .5 * _w
    return 2. * np.array([(_w * _m * np.exp(-xx / _m)).sum()
                          for xx in np.atleast_1d(x)])


# ...AND THE TWO INTEGRALS DO NOT FACTORISE, which is the correction this round
# makes to its own first writing. `T_diff * (1 - R_int)` treats the attenuation
# of an up leg and its chance of escaping as independent. They are not: a steep
# ray escapes AND crosses less water, a grazing one is totally reflected AND
# crosses more, so the two are positively correlated and the product of the
# means understates the mean of the product -- by 19.4% in red, 5.1% in green,
# 1.1% in blue. The round trip is correlated the other way and the factorised
# form OVERstates it by 30% in red. So the escape and the trap are written here
# as ONE integral each, over the water-side cosine, with the exact internal
# Fresnel inside them:
#
#   T_esc = INT_0^1 2 mu exp(-a d / mu) (1 - R_int(mu)) dmu
#   G_rt  = INT_0^1 2 mu exp(-2 a d / mu)    R_int(mu)  dmu
#
# and then, because the bed redraws the direction from a cosine law at every
# bounce, the series really is geometric in rho * G_rt and nothing is lost:
#
#   rho_w = (1 - R_ext(sun)) T_slant rho_bed T_esc / (1 - rho_bed G_rt)
#
# `validate.py` holds this against a photon Monte-Carlo that shares no line with
# it and agrees to 0.1%, which is the only way a correlated integral can be
# checked -- a second quadrature would have shared the premise.
_SQM, _SQW = np.polynomial.legendre.leggauss(2000)
_SQM, _SQW = .5 * (_SQM + 1), .5 * _SQW          # water-side cosine on (0, 1]
_SQ_SINA = IOR[None] * np.sqrt(np.maximum(1. - _SQM[:, None] ** 2, 0.))
_SQ_TIR = _SQ_SINA >= 1.0
_SQ_COSA = np.sqrt(np.maximum(1. - _SQ_SINA ** 2, 0.))
_SQ_RS = ((IOR[None] * _SQM[:, None] - _SQ_COSA)
          / (IOR[None] * _SQM[:, None] + _SQ_COSA)) ** 2
_SQ_RP = ((IOR[None] * _SQ_COSA - _SQM[:, None])
          / (IOR[None] * _SQ_COSA + _SQM[:, None])) ** 2
# the internal reflectance of the surface for a ray arriving from BELOW at
# cosine mu: exactly 1 past the critical angle, the Fresnel mean inside it.
R_INT_MU = np.where(_SQ_TIR, 1.0, .5 * (_SQ_RS + _SQ_RP))


def slab_esc(dep, absorb=None):
    """The share of a Lambertian bed's upward flux that escapes on its FIRST
    pass: attenuation and escape integrated together, not multiplied.

    `dep` is the water column's length and it has no default: this module
    does not know what scene it is in, and a beach's depth is a field. The
    pool passes its own DEPTH at every call site."""
    a = ABS if absorb is None else np.asarray(absorb, float)
    return (_SQW[:, None] * 2. * _SQM[:, None]
            * np.exp(-a[None] * dep / _SQM[:, None])
            * (1. - R_INT_MU)).sum(0)


def slab_trap(dep, absorb=None, cone_only=False):
    """The share of that flux that is returned by the surface and arrives back
    at the bed -- one round trip, at the same cosine, since a specular interface
    does not change it. `cone_only` replaces the exact internal Fresnel with a
    perfect mirror past the critical angle and nothing inside it, which is the
    model the shipped bedret pass carries."""
    a = ABS if absorb is None else np.asarray(absorb, float)
    r = np.where(_SQ_TIR, 1.0, 0.0) if cone_only else R_INT_MU
    return (_SQW[:, None] * 2. * _SQM[:, None]
            * np.exp(-2. * a[None] * dep / _SQM[:, None]) * r).sum(0)


def trap_gain(rho, dep, bounces=None, absorb=None, cone_only=False):
    """The light trap under the surface, as a factor on the bed's own light.
    `bounces=None` closes the geometric series; an integer truncates it at that
    many returns, which is what turns the render's own truncation into a number
    rather than an omission -- `bounces=1, cone_only=True` is exactly the model
    the shipped bedret pass carries, before any of its geometry."""
    g = np.asarray(rho) * slab_trap(dep, absorb, cone_only)
    if bounces is None:
        return 1.0 / (1.0 - g)
    return sum(g ** k for k in range(bounces + 1))


def rho_water(rho_bed, cos_sun, dep, bounces=None, absorb=None):
    """Apparent albedo of the water column: the share of the beam falling on the
    surface that comes back out of it, EXCLUDING the surface's own reflection.

    `rho_bed` IS A WATER-SIDE REFLECTANCE. The interface is crossed twice
    inside this function -- `(1 - fresnel(cos_sun))` going in and `slab_esc`
    coming out -- and `rho_bed` sits between the two crossings, so it must be
    what the bed returns TO THE WATER standing on it. A dry-substrate albedo is
    the right kind of thing (that is the identification `wet_albedo` already
    makes); `wet_albedo(a)` is NOT, and neither is `wet_albedo(a) - R_EXT`.
    Both of those have already crossed the interface and carry the trapped
    series, so passing either applies the whole of this file's interface model
    twice. See `wet_albedo`'s docstring for the identity that separates them,
    and `beach_optics.submerged_bed_rho` for the wave-10 write-up.
    Add `fresnel(cos_sun)` to it and a LOSSLESS WHITE-BEDDED pool comes to
    exactly 1 -- energy conservation, with no constant of this file in the
    right-hand side. That limit pins the SHAPE of the series but it cannot see
    a path length, because at zero absorption every path is 1; what pins the
    legs is the Monte-Carlo row beside it, at the file's own absorption."""
    a = ABS if absorb is None else np.asarray(absorb, float)
    st = np.sqrt(np.maximum(1. - np.asarray(cos_sun, float) ** 2, 0.)) / IOR
    tsl = np.exp(-a * dep / np.sqrt(1. - st ** 2))
    return ((1. - fresnel(cos_sun)) * tsl * np.asarray(rho_bed)
            * slab_esc(dep, absorb)
            * trap_gain(rho_bed, dep, bounces, absorb))


def wbounce_of(L_bed, dep, absorb=None):
    """The AIR-SIDE upwelling radiance a pool of in-water bed radiance `L_bed`
    presents to a facet standing over it -- `WBOUNCE`, in one line.

    A Lambertian bed of radiance L radiates pi*L upward. `slab_esc` is the share
    of that flux which crosses `dep` of water AND gets through the surface, with
    the attenuation and the escape inside ONE integral because they are
    correlated (see above). What comes out is pi*L*slab_esc of flux; written
    back as the radiance of an equivalent Lambertian emitter that is
    L * slab_esc, which is the number a diffuse receiver above the water wants.

    `?` The escaped distribution is NOT Lambertian -- the surface passes the
    steep rays preferentially, so the real lobe is narrower than a cosine and a
    facet directly over the water sees slightly more than this while one at a
    grazing angle sees slightly less. `liner_band` and `_stone` both gather over
    a half-space, where that difference integrates out to first order; nothing
    in this file reads the upwelling in a single direction."""
    return np.asarray(L_bed, float) * slab_esc(dep, absorb)



# --- Fresnel, exactly, because this is a reference ---------------------------
# The unpolarised reflectance of a smooth dielectric interface, from the Fresnel
# equations themselves. With sin t = sin i / n (Snell),
#
#     R_s = ((cos i - n cos t)/(cos i + n cos t))^2      # E perpendicular
#     R_p = ((n cos i -   cos t)/(n cos i +   cos t))^2  # E in the plane
#     R   = (R_s + R_p)/2                                # unpolarised sunlight
#
# THIS FILE USED TO SHIP SCHLICK (1994), `F0 + (1-F0)(1-cos i)^5`, everywhere.
# Schlick's whole justification is that it is one multiply-add cheaper than the
# square roots above; its error is quoted as ~1% of R for common dielectrics and
# for water it is nothing of the sort. Measured against the exact equations:
#
#     worst absolute, 0-90 deg   exact 0.5163 against Schlick 0.5751 at 83.8 deg
#     over the frame's own incidence range (38-79 deg, render.py's own
#       measurement of what this camera spans), Schlick / exact - 1 runs
#           -22.8%  at 51.3 deg   (exact 0.0360 against Schlick 0.0278)
#           +14.3%  at 79.0 deg   (exact 0.3152 against Schlick 0.3604)
#       crossing zero at 67.1 deg
#
# AND THAT SIGN FLIP IS THE POINT. It is not a grazing-only overshoot that a
# scale could absorb: inside one frame the fit is a fifth low on the mid water
# and a seventh high on the far water, so the far band read too much like a
# mirror while the mid band read too little, with no single multiplier able to
# fix both. The far water's specular term is the brightest thing in the picture
# and the mid water is most of its area, so the error sits on exactly the pixels
# a reflection model is judged by, in both directions at once. An
# approximation whose only argument is speed does not belong in a file whose only
# argument is being right. The exact form costs one sqrt and one divide per
# channel, measured at +1.1% of a full render (5m23s -> 5m27s at this resolution),
# and that is the entire price of the 14%.
#
# Provenance: Born & Wolf, *Principles of Optics*, §1.5.2 (the Fresnel
# coefficients); Schlick, *Computer Graphics Forum* 13(3) 233-246 (1994) for what
# was replaced. Guarded in `validate.py` by three things that do not go through
# the same expression: R(0) = F0, the Brewster identity R(atan n) = ((n^2-1)/
# (n^2+1))^2 / 2 exactly (a closed-form NUMBER -- Schlick misses it by 22%), and
# R_s >= R >= R_p over the whole range.
def fresnel(cos_i):
    """Exact unpolarised Fresnel reflectance, per channel. Returns (..., 3)."""
    ci = np.clip(np.asarray(cos_i, float), 0.0, 1.0)[..., None]
    ct = np.sqrt(np.maximum(1.0 - (1.0 - ci * ci) / IOR ** 2, 0.0))
    rs = ((ci - IOR * ct) / (ci + IOR * ct)) ** 2
    rp = ((IOR * ci - ct) / (IOR * ci + ct)) ** 2
    return 0.5 * (rs + rp)


# --- a camera channel is a BAND, not a wavelength ----------------------------
# The three IORs above are three delta functions standing in for three broad
# sensor bands, and a 3-point quadrature is only as good as the integrand is
# smooth over the sample spacing. On a caustic FOLD the integrand is smooth over
# the dispersion scale and three samples are plenty -- that is why the fringing
# on the folds reads correctly. On an OPAQUE SILHOUETTE the integrand is a step
# AT the dispersion scale, and three deltas resolve a step as a comb: three
# separately-placed edges, so the pixel between them carries one primary with
# the other two missing. That is not dispersion, it is aliasing of dispersion,
# and it is what put saturated blue and yellow speckle on every step nosing.
# MEASURED before the fix: the red and blue images of the bed are separated by
# 9.8 mm on the floor and 8.7 mm at the step unit, which is 2.1 and 2.4 OUTPUT
# pixels -- and 0.33% of all water rays disagreed about WHICH surface they hit.
#
# n(lambda) is not a new constant: a two-parameter Cauchy fit through the three
# (lambda, n) pairs already in the file reproduces all three to 5e-5, so the
# three IORs were themselves drawn from one dispersion curve and the curve can
# be recovered from them.
_uu2 = 1.0 / LAM ** 2
CAUCHY_B = (((_uu2 - _uu2.mean()) * (IOR - IOR.mean())).sum()
            / ((_uu2 - _uu2.mean()) ** 2).sum())
CAUCHY_A = IOR.mean() - CAUCHY_B * _uu2.mean()


def n_water(lam_um):
    """Refractive index at a wavelength, from the file's own three IORs."""
    return CAUCHY_A + CAUCHY_B / np.asarray(lam_um) ** 2


# The bands are the VORONOI CELLS of the three nominal wavelengths: edges at the
# midpoints 582.5 and 502.5 nm, the outer edges mirrored so each band is centred
# on its nominal. They then tile 417.5-657.5 nm with no gap and no overlap,
# which is the minimum a three-channel sensor must do to reproduce a continuous
# spectrum without holes. No new number enters -- only the three wavelengths
# that were already here. A real Bayer CFA overlaps its neighbours instead of
# tiling them (`?`), which would smear the edge slightly MORE than this, so the
# tiling choice is the conservative one.
_mid = 0.5 * (LAM[:-1] + LAM[1:])
BAND = np.array([[_mid[0], 2 * LAM[0] - _mid[0]],
                 [_mid[1], _mid[0]],
                 [2 * LAM[2] - _mid[1], _mid[1]]])       # [lo, hi] um, per channel


def refract(ix, iy, iz, nx, ny, nz, eta):
    """Snell's law as a direction map, WITH its total-internal-reflection branch.

    `eta` = n_incident / n_transmitted; `n` must oppose the incident ray. Writing
    the transmitted direction as `t = eta*i + f*n`, orthogonality of the tangential
    part to `n` and |t| = 1 give `f = eta*cos i - cos t` with

        k = cos^2 t = 1 - eta^2 (1 - cos^2 i)

    and k < 0 exactly when sin i > 1/eta -- the critical angle asin(1/eta), which
    exists only for eta > 1 (looking OUT of the denser medium). Past it there is
    no transmitted direction at all: every photon reflects, and the Fresnel R that
    goes with this same interface is 1 there, identically.

    THE BUG THIS FIXES. The old line clamped k at 0 and returned
    `eta*i + eta*cos(i)*n` regardless -- a vector of length `eta*sin i > 1` lying
    flat in the interface plane. Not a unit vector, not the TIR reflection, not a
    flag: a direction that does not exist, handed back silently. Nothing
    downstream could tell it from a real one, because nothing downstream measured
    its length. Unreachable from today's call sites (all five pass eta = 1/n < 1,
    air -> water, where k >= 1 - eta^2 >= 0), and squarely on the path of the
    underwater-camera pass the README describes, which is written entirely around
    this branch.

    THE CONTRACT. Past the critical angle this returns the NULL vector (0, 0, 0);
    `is_tir(t)` is the predicate. Zero was chosen over a NaN or a fourth return
    value because it keeps the signature, it propagates to zero radiance rather
    than to a poisoned frame, and it is checkable with one dot product -- which is
    what `validate.py` does. The five call sites below cannot reach the branch, so
    each declares which side of the interface it is on instead: an assert on eta
    where the eta is computed there, a comment where it is a literal 1/IOR. The
    onset of the null return is cross-checked in the suite against the angle at
    which the exact Fresnel R reaches 1, i.e. against different code.
    """
    cosi = -(ix * nx + iy * ny + iz * nz)
    k = 1.0 - eta * eta * (1.0 - cosi * cosi)
    f = eta * cosi - np.sqrt(np.maximum(k, 0.0))
    tx, ty, tz = eta * ix + f * nx, eta * iy + f * ny, eta * iz + f * nz
    # One reduction decides whether the branch was reached at all, so the eta < 1
    # call sites pay a min() over the batch and nothing else.
    if np.min(k) >= 0.0:
        return tx, ty, tz
    ok = k >= 0.0
    return tx * ok, ty * ok, tz * ok


def is_tir(tx, ty, tz):
    """True where `refract` returned its null vector. A transmitted direction is
    a unit vector, so |t|^2 is either 1 or 0 and the 0.5 threshold cannot be
    reached by round-off from either side."""
    return (tx * tx + ty * ty + tz * tz) < 0.5


# --- WHAT IS ACTUALLY OVER A SUBMERGED FACE ----------------------------------
# Every submerged receiver in this file used to be handed `SKY_AMB` over some
# fraction of its hemisphere. On the BED that is exactly right and it is worth
# saying why, because the same sentence says why it is wrong on a WALL. The sky
# a submerged point sees is not a hemisphere: it is the Snell window, the whole
# air-side hemisphere compressed into a cone of half angle asin(1/n) = 48.5 deg
# about the VERTICAL, and gained by n^2 on the way in (`into_water`). For a
# HORIZONTAL receiver those two factors cancel exactly --
#
#     (1/pi) INT_{t<tc} n^2 L_air cos t dw  =  n^2 L_air sin^2(tc)  =  L_air
#
# -- since sin^2(tc) = 1/n^2. So "a full hemisphere of SKY_AMB" and "the window
# at n^2 SKY_AMB" are the same number on the bed, which is why the bed's term
# has always worked and why nothing here moves it.
#
# On a VERTICAL face the cancellation fails, and it fails by the largest factor
# available: a vertical face weights directions by sin t, so it collects almost
# nothing from a cone about the vertical, while the bed weights them by cos t
# and collects all of it. The two closed forms the file already owns give the
# ratio with nothing new introduced:
#
#     E_vert(hemisphere)/E_bed(hemisphere) = tir_vert(0)         = 0.500
#     E_vert(cone t>tc)/E_bed(cone t>tc)   = tir_vert(tc)        = 0.885
#     E_bed(cone t>tc)/E_bed(hemisphere)   = 1 - 1/n^2           = 0.439
#  => the WINDOW's share of a vertical face, against the bed's:
#     (0.5 - tir_vert(tc)*(1 - 1/n^2)) * n^2                     = 0.199
#
# and `WALL_SKY = 0.5` -- correct as a PARTITION of a hemisphere -- is not that
# number. It over-gives the sky to a submerged vertical face by x2.5 before the
# `WAO` occlusion and by x1.96 after it. What belongs in the rest of that upper
# half is the MIRROR: past tc the underside is a perfect reflector, so a wall
# looks at the pool's own upwelling field folded down, and that is the term the
# file has been carrying at one truncated bounce.
#
# THE THREE FUNCTIONS BELOW ARE THE WHOLE OF IT and none of them is new physics:
# `tir_vert` was already here, `r_int_at` is the file's own external `fresnel`
# read through Stokes reversibility exactly as `uw_interface` reads it, and the
# sky profile is `sky()`'s own first two lines. What is new is that they are now
# evaluated per direction inside one integral instead of being replaced by a
# constant.
TC_SNELL = np.arcsin(1.0 / IOR)     # 48.655 / 48.507 / 48.262 deg -- dispersive
# NAMED TC_SNELL and not THETA_C: `THETA_C` in this file is the meniscus's
# CONTACT angle, four hundred lines down, and the two have nothing to do with
# each other. One collision of that kind is a silently wrong picture.
TIR_FRAC = 1.0 - 1.0 / IOR[1] ** 2  # green's cone share; the shooting pass below


def tir_vert(tc):
    """Vertical-face / horizontal-bed irradiance from a uniform radiance filling
    the cone t > tc. Exact; tir_vert(0) == 1/2 identically. MOVED UP from beside
    the riser TIR term, where its derivation still stands -- the window share
    below needs it four hundred lines earlier, and a second copy would be a
    second premise."""
    return ((np.pi / 2 - tc + np.sin(tc) * np.cos(tc))
            / (np.pi * np.cos(tc) ** 2))


TIR_VERT = float(tir_vert(np.arcsin(1.0 / IOR[1])))


def r_int_at(mu):
    """The underside's reflectance at a water-side polar angle of cosine `mu`,
    per channel, reached through the file's ONE Fresnel implementation. Snell
    takes the water-side angle to the air-side one; past the critical angle the
    air-side cosine's square goes negative and the reflectance is exactly 1,
    which is found here by the sign of that square and never by comparing an
    angle with `TC_SNELL`. Same identity, same code path, as `uw_interface`."""
    mu = np.asarray(mu, float)
    s2 = np.clip(1.0 - mu * mu, 0.0, 1.0)
    out = np.ones(mu.shape + (3,))
    for c in range(3):
        ca2 = 1.0 - IOR[c] ** 2 * s2
        m = ca2 > 0.0
        oc = np.ones(mu.shape)
        if m.any():
            oc[m] = fresnel(np.sqrt(ca2[m]))[:, c]
        out[..., c] = oc
    return out
