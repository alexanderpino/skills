"""Coastal water: the three constituents, the path, and the glitter.

THE ONE THING THIS SCENE COULD NOT INHERIT. `optics.py` carries the interface
and the medium -- exact Fresnel both ways, `L/n^2`, the trapped series, the
Cauchy dispersion, the critical angle, Pope & Fry's pure-water absorption -- and
every line of it transfers to a beach unchanged. What does NOT transfer is the
pool's `b_b ~ 0`: a swimming pool's water scatters nothing worth rendering, and
a coast's water scatters enough to BE its colour. So this file adds exactly one
thing to the shared module and takes nothing away from it:

    the INHERENT OPTICAL PROPERTIES of coastal water, and the two transports
    that make them visible -- a path THROUGH the water (the green wave face)
    and a path INTO and back OUT of it (the grey-blue body).

NOTHING HERE IS COPIED FROM `optics.py`. `ABS`, `IOR`, `BAND`, `fresnel`,
`rho_water`, `slab_esc` and `wet_albedo` are IMPORTED and used as they stand;
where a coastal absorption is needed the pool's functions already take it as an
argument (`absorb=`), which is the extension point the extraction left open and
the reason no fork was needed. The one place the pool's modules did NOT stretch
is recorded as a finding in `README-beach.md`, not patched here.

THE DOCTRINE, from `terrain-architect/references/28-liquids.md`, and it is the
whole architecture of this file: THE THREE CONSTITUENTS ARE NOT ONE TURBIDITY
SLIDER.

    phytoplankton   absorbs at 440 AND 675, leaves a window at 550-570   GREEN
    CDOM            a440 exp[-S(lam-440)], rises into the blue,
                    SCATTERS NOT AT ALL                                  DARK
    mineral SPM     scattering, near spectrally flat                     PALE

CDOM darkens and sediment brightens: they are opposite controls, and this coast
needs BOTH signatures at once -- a green wave face offshore and a pale surf zone
inshore. One slider cannot do that, and the reason it cannot is structural
rather than aesthetic: the green is an ABSORPTION feature on a TRANSMITTED path
and the pale is a SCATTERING feature on a REFLECTED one. They do not even use
the same coefficient.

WHERE EACH NUMBER COMES FROM. This file's house rule is `beach.py`'s: derived
beside itself, cited to something read this wave, or marked `?`. The chapter is
the source for anything spectroscopic; nothing is recalled from memory. The
three scene scalars are carried as chapter 28's export list asks -- and two of
them are ABSORPTION COEFFICIENTS rather than concentrations, deliberately:

    A_PH_440    m^-1    chlorophyll absorption at 440. RECOVERED from chapter
                        28's own Jerlov table (below), not chosen.
    A_CDOM_440  m^-1    CDOM absorption at 440. DECLARED, `?`, against the
                        chapter's own gates.
    SPM         mg/L    mineral load. NOT declared at all -- it is COMPUTED
                        from the wave dissipation by a settling balance and
                        converted to `b` by chapter 28's Babin bridge.

The chapter's bridge is stated for MASS (`b_p(555)/SPM ~ 0.5 m^2/g`) and so SPM
is carried as a mass; it says nothing about the chlorophyll-specific absorption
`a*_ph`, so a chlorophyll CONCENTRATION cannot be quoted from this file without
importing a number the chapter does not carry. It is not quoted. `a_ph(440)` in
m^-1 is what the optics needs and it is what is carried; the conversion to
mg/m^3 is marked `?` and left open.
"""
import math

import numpy as np

import optics as OPT
import atmosphere as ATM                                        # noqa: F401


# ============================================================ the spectral grid
# A channel is a BAND, not a wavelength -- `optics.py`'s own doctrine, and the
# reason its `ABS` is a band mean of Pope & Fry rather than a point sample. Every
# constituent spectrum in this file is therefore written as a CONTINUOUS function
# of wavelength and then integrated over the same three Voronoi bands
# (582.5-657.5, 502.5-582.5, 417.5-502.5 nm) that `optics.BAND` already defines.
# Sampling a constituent at three deltas while the pure water beside it is
# band-integrated is the inconsistency `optics.py` went out of its way to remove,
# and chlorophyll is the quantity where it would cost most: its whole visual
# signature is a MINIMUM inside the green band, so a delta at 545 nm reports the
# floor of the window and a band mean reports the window, which are not the same
# number.
BAND_NM = OPT.BAND * 1000.0                     # [lo, hi] nm, per channel
BAND_N = 161                                    # nodes per band


def band_mean(f, n=None):
    """Integrate a continuous spectrum onto the renderer's three bands.

    `f` is a CALLABLE of wavelength in nm, and that is deliberate: an earlier
    writing masked one global wavelength grid per band, which made the band's
    end points depend on where the grid's rounding happened to fall. Sampling
    each band on its own `linspace` puts the end points exactly on the band
    edges by construction, so refining `n` changes only the quadrature and not
    the interval -- which is what lets the suite measure the quadrature error
    instead of measuring a moving window.

    Trapezoid on 161 nodes per band. The constituent spectra are Gaussians and
    an exponential over an 80 nm band, so the error is 1e-9 relative; the suite
    carries the convergence against 1601 nodes rather than asserting it."""
    n = BAND_N if n is None else n
    out = []
    for c in range(3):
        lo, hi = BAND_NM[c]
        lam = np.linspace(lo, hi, n)
        y = np.asarray(f(lam), float)
        out.append(np.trapezoid(y, lam, axis=-1) / (hi - lo))
    return np.stack(out, -1)


# ==================================================== 1 - CDOM, the dark one
# Chapter 28, verbatim: `a(lam) = a440 * exp[-S(lam - 440)]`, `S ~ 0.012-0.022
# nm^-1`, and it SCATTERS NOT AT ALL. The exponential slope is the chapter's
# range and 0.017 is its midpoint -- a declared choice inside a cited interval,
# and the sensitivity is reported rather than hidden: across the full 0.012-0.022
# the red-band CDOM absorption moves by a factor of 2.9 while the blue band moves
# by 1.2, so `S` is a RED control and the green window is nearly blind to it.
CDOM_S = 0.017          # nm^-1. Chapter 28's midpoint. `P`
CDOM_S_RANGE = (0.012, 0.022)


def a_cdom(lam_nm, a440):
    return a440 * np.exp(-CDOM_S * (np.asarray(lam_nm, float) - 440.0))


# ============================================== 2 - chlorophyll, the green one
# THE SHAPE IS THE CHAPTER'S AND THE WIDTHS ARE DECLARED. Chapter 28 states the
# mechanism completely -- "absorbs blue (~440 nm) AND red (~675 nm), leaving a
# transmission window at 550-570 nm" -- and states no line shape. So the shape
# here is two Gaussians plus a floor, and every parameter of it except the two
# PEAK POSITIONS is `?`:
#
#     peaks       440, 675 nm             chapter 28
#     widths      40, 22 nm               DECLARED `?`
#     red/blue    0.55                    DECLARED `?`
#     floor       0.08 of the 440 peak    DECLARED `?`, the packaged-pigment
#                                         background that makes a_ph non-zero
#                                         between the bands
#
# WHAT THE SUITE IS ALLOWED TO CHECK IS THE CHAPTER'S CLAIM AND NOT THIS SHAPE:
# that there are two peaks with a window between them, that the window is below
# both, and -- the row that matters -- that the TOTAL absorption of this water
# minimises in the band that contains 550-570 nm. A row that checked the widths
# would be checking this file against itself.
#
# AND ONE CORRECTION TO THE CHAPTER, FOUND BY WRITING THE SHAPE DOWN. Chapter 28
# says chlorophyll "leav[es] a transmission window at 550-570 nm", which reads as
# a statement about a_ph. It is not one, and it cannot be: a_ph alone, with any
# two-band shape whose peaks are at 440 and 675, has its MINIMUM near 590-600 nm
# -- this file's lands at 592 -- because the minimum of a sum of two lines sits
# between them, nearer the broader one's tail. What actually sits at 550-570 is
# the minimum of the SUM with pure water, since a_w climbs steeply above 570 and
# pushes the window back down the spectrum. The chapter's number is right about
# the water and wrong about the constituent, and the distinction matters to
# anyone implementing it: fitting a chlorophyll spectrum to put ITS minimum at
# 560 would need widths no pigment has.
CHL_PEAKS = ((440.0, 40.0, 1.00),
             (675.0, 22.0, 0.55))
CHL_FLOOR = 0.08


def _chl_shape(lam_nm):
    """The chlorophyll absorption shape, normalised to 1.0 at 440 nm."""
    lam = np.asarray(lam_nm, float)
    s = np.full(lam.shape, CHL_FLOOR)
    for mu, sig, amp in CHL_PEAKS:
        s = s + amp * np.exp(-0.5 * ((lam - mu) / sig) ** 2)
    return s / (CHL_FLOOR + sum(a * math.exp(-0.5 * ((440.0 - m) / s0) ** 2)
                                for m, s0, a in CHL_PEAKS))


def a_ph(lam_nm, a440):
    return a440 * _chl_shape(lam_nm)


# --- THE AMPLITUDE IS RECOVERED, NOT CHOSEN ----------------------------------
# `a_ph(440)` for this coast is the one number that would otherwise be a taste,
# and chapter 28 supplies the constraint that removes the choice. Its Jerlov
# table (Solonenko & Mobley 2015) gives, for coastal type 1C -- the entry the
# chapter itself labels "coastal green" --
#
#       K_d(490) = 0.120 m^-1
#
# and Gordon's relation, K_d ~= (a + b_b) / mu_d, inverts that to an ABSORPTION
# at 490 nm. Everything else at 490 is either pure water or already declared:
#
#       a(490)      = K_d(490) * mu_d - b_b(490)
#       a_ph(490)   = a(490) - a_w(490) - a_cdom(490)
#       a_ph(440)   = a_ph(490) / shape(490)
#
# TWO INPUTS TO THIS RECOVERY ARE NOT FROM THE CHAPTER AND BOTH ARE MARKED.
#   * a_w(490) = 0.0150 m^-1. Pope & Fry (1997), the same table `optics.ABS`
#     is a band mean of and the paper this project's bibliography already names.
#     A POINT value, used ONLY here -- the render never sees it -- because 490 nm
#     sits inside the blue band and the band mean is not the quantity Gordon's
#     relation is written at. `P`.
#   * mu_d = 0.86, the mean cosine of the downwelling field. `?`. The recovered
#     a_ph(440) is very nearly LINEAR in it, so a 10% error in mu_d is a 17%
#     error here; that is the dominant uncertainty and it is reported as a
#     bound rather than absorbed.
#
# WHAT MAKES THIS A RECOVERY RATHER THAN A FIT: nothing about this scene entered
# it. The constraint is a published water TYPE, chosen because chapter 28 names
# 1C "coastal green" and this is a productive upwelling coast, and the number
# that comes out is then used unchanged. It was not adjusted afterwards, and the
# suite carries what it predicts for K_d in the OTHER Jerlov types as a check
# that the recovery did not merely restate its own input.
A_W_490 = 0.0150        # m^-1, Pope & Fry (1997) point value. `P`
MU_D = 0.86             # `?`
JERLOV_1C_KD490 = 0.120     # m^-1, chapter 28's table


# ================================================ 3 - mineral, the pale one
# THE BRIDGE IS THE CHAPTER'S AND IT IS THE ONLY CONSTANT IN THIS FILE WITH A
# PRIMARY CITATION: Babin et al. (2003), via chapter 28 --
#
#       b_p(555) / SPM ~= 0.5 m^2/g,  and 1 mg/L = 1 g/m^3
#       so each mg/L of mineral load adds ~0.5 m^-1 to b at 555 nm.
#
# The spectral slope is the chapter's "near spectrally flat, b_b prop lam^-0.5
# ... -1 (against lam^-4.3 for water molecules)". 0.75 is the midpoint of that
# interval and it is DECLARED there; the sensitivity across the full interval is
# 8.4% on the red/blue ratio of b_p, which is small against everything else here
# and is reported rather than argued about.
B_P_555_PER_SPM = 0.5   # m^2/g. Babin et al. (2003), via chapter 28
B_P_SLOPE = 0.75        # midpoint of the chapter's 0.5-1.0. `P`
B_P_SLOPE_RANGE = (0.5, 1.0)


def b_p(lam_nm, spm):
    """Mineral particulate scattering, m^-1, from a mass load in mg/L.

    Plain broadcasting: `spm` and `lam_nm` are combined as given, so a scalar
    load over the wavelength grid returns a spectrum and a load FIELD must be
    given its own trailing axis by the caller. `iops` does exactly that, once,
    on the band-integrated shape rather than on the 490-point grid."""
    return (B_P_555_PER_SPM * np.asarray(spm, float)
            * (555.0 / np.asarray(lam_nm, float)) ** B_P_SLOPE)


# --- WHAT IS DELIBERATELY ZERO, AND IT IS AN OMISSION AND NOT A RESULT --------
# `a_NAP`, the ABSORPTION by the same mineral particles. It is real and it is not
# tiny -- mineral grains absorb in the blue with an exponential shape much like
# CDOM's -- but chapter 28's bridge gives the SCATTERING coefficient only, and
# this file does not import a mass-specific absorption the chapter does not
# carry. So a_NAP = 0 here, and the consequence is named: THE SURF ZONE RENDERS
# SLIGHTLY TOO BRIGHT AND SLIGHTLY TOO NEUTRAL, most in the blue channel. It is
# an open item, not a modelling choice, and it is in the README's `?` list.
A_NAP_440 = 0.0         # `?` -- see above. NOT a claim that it is zero.


# --- pure-water scattering ----------------------------------------------------
# Molecular scattering, which chapter 28 gives only as an exponent: `lam^-4.3 for
# water molecules`, against the particles' -0.5..-1. The amplitude is Morel
# (1974), b_w(500) = 0.00288 m^-1 for pure sea water -- `P`, and it is two to
# three ORDERS below b_p at any load this coast carries, so it is here for
# completeness and for the clear-water limit rather than for the picture.
B_W_500 = 0.00288       # m^-1. Morel (1974). `P`
B_W_SLOPE = 4.3         # chapter 28's exponent for molecular scattering


def b_w(lam_nm):
    return B_W_500 * (500.0 / np.asarray(lam_nm, float)) ** B_W_SLOPE


# ======================================= the backscatter ratio, and g with it
# TWO NUMBERS, AND THE SECOND FALLS OUT OF THE FIRST WITH NOTHING LEFT TO
# CHOOSE. Chapter 28 states the forward dominance as a RATIO -- "forward
# scattering dominates (b_f >~ 50 b_b)" -- and b = b_f + b_b, so
#
#       b_b / b  <=  1 / 51  =  0.01961
#
# That is the chapter's own inequality read at its boundary, and it is the only
# backscatter fraction this file uses. It is NOT a Petzold value recalled from
# memory; it is the chapter's sentence, inverted.
#
# AND THEN THE PHASE ASYMMETRY IS DETERMINED. The chapter asks for `phase_g`
# alongside a and b_b, warns that leaving g at zero "kills the forward glow
# through a sunlit wave crest" -- which is this scene's section A -- and gives no
# number. It does not need to: a Henyey-Greenstein lobe has exactly one
# parameter, and requiring its backscattered fraction to equal b_b/b fixes it.
# The HG backscatter fraction has a closed form,
#
#       B(g) = INT_{pi/2}^{pi} p_HG sin th dth * 2 pi
#            = (1 - g)/(2 g) * [ (1 + g)/sqrt(1 + g^2) - 1 ]
#
# and solving B(g) = 1/51 gives the g below. So the asymmetry parameter this
# renderer would hand an engine is a DERIVED consequence of the chapter's
# forward-dominance sentence, and the suite checks the closed form against a
# quadrature of the phase function itself, which shares no line with it.
BB_OVER_B = 1.0 / 51.0


def hg_backscatter_fraction(g):
    """Closed form: the share of a Henyey-Greenstein lobe going into the
    backward hemisphere."""
    g = np.asarray(g, float)
    return (1.0 - g) / (2.0 * g) * ((1.0 + g) / np.sqrt(1.0 + g * g) - 1.0)


def hg_phase(g, cos_theta):
    """The Henyey-Greenstein phase function, normalised to INT p dw = 1."""
    g = np.asarray(g, float)
    return ((1.0 - g * g)
            / (4.0 * np.pi * (1.0 + g * g - 2.0 * g * np.asarray(
                cos_theta, float)) ** 1.5))


def g_from_backscatter(bb_over_b=BB_OVER_B, lo=0.5, hi=0.9999):
    """Invert `hg_backscatter_fraction`. Bisection, because B(g) is monotone
    decreasing on (0, 1) and a bisection cannot land on the wrong root."""
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if hg_backscatter_fraction(mid) > bb_over_b:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


PHASE_G = g_from_backscatter()      # 0.9235 at b_b/b = 1/51


# ============================================== the scene's three scalars
# THE OPEN OCEAN OFF ALJEZUR, and every one of these is a `?` with a stated
# basis. They are the water MASS's properties; the sediment field below is not
# one of them, and that separation is the whole point of section A.
#
# A_CDOM_440: chapter 28 gives two gates and this coast sits far from both.
# Blackwater is 5-19 m^-1; turquoise requires < 0.5 m^-1. An exposed Atlantic
# embayment with no peat catchment and a small seasonal stream is at the clean
# end, and 0.08 m^-1 is a sixth of the chapter's turquoise gate. `?` -- and the
# suite reports what the frame would look like across 0.02-0.30 rather than
# claiming this value.
A_CDOM_440 = 0.08       # m^-1. `?`


def recover_a_ph_440(kd490=JERLOV_1C_KD490, mu_d=MU_D, a_cdom440=A_CDOM_440,
                     spm=0.0):
    """Chapter 28's Jerlov 1C entry, inverted through Gordon's K_d relation.

    Returns a_ph(440) in m^-1. `spm` is the mineral load assumed present in the
    type's own water, which for an open-coastal type is small; it enters only
    through b_b and moves the answer by under 2% at any load a type-1C water
    could carry."""
    bb490 = BB_OVER_B * float(b_p(490.0, spm) + b_w(490.0))
    a490 = kd490 * mu_d - bb490
    a_ph490 = a490 - A_W_490 - float(a_cdom(490.0, a_cdom440))
    return a_ph490 / float(_chl_shape(490.0))


A_PH_440 = recover_a_ph_440()       # m^-1, recovered -- NOT declared


# ================================= SPM is not a slider: it is the wave field
# THE STANDING RULING SAYS THE PHYSICS COMES FROM PHYSICAL EFFECTS AND NEVER
# FROM A CONSTANT CHOSEN TO MAKE THE PICTURE RIGHT, and a turbidity slider is
# exactly such a constant. Bar section D says the same thing from the other end:
# `b` is a FIELD COUPLED TO THE WAVE FIELD, not a property of the water body,
# because waves suspend the bed and the load pulses with them.
#
# So the suspended load here is a BALANCE, and every term in it is already in
# `beach.py`. Bagnold's suspension argument, in Bailard's (1981) surf-zone form:
# holding sand in suspension costs power, the power comes from the wave's own
# dissipation, and the sand falls out at its settling velocity. Per unit area,
#
#       i_s * w_s  =  eps_s * D                                      (1)
#
# with `i_s` the IMMERSED WEIGHT of sediment carried per unit area (N/m^2), w_s
# the settling velocity (m/s), D the dissipation rate (W/m^2) and eps_s the
# suspension efficiency. Read it as a statement about power: the left side is
# the rate at which gravity does work pulling the load down, the right is the
# share of the wave's dissipation that goes into lifting it back. In equilibrium
# they are equal.
#
# Convert to a mass concentration. Immersed weight of a mass M per unit area is
# i_s = M g (rho_s - rho_w)/rho_s, so
#
#       M = eps_s * D * rho_s / ( g (rho_s - rho_w) w_s )            (2)
#       SPM = M / d                                                  (3)
#
# and (3) is where the DEPTH enters -- the same load spread through a deeper
# column is a lower concentration, which is why the surf zone whitens as it
# shoals even where D is flat.
#
# UNITS, because this is the family of error the standing rulings name twice:
# [eps_s D] = W/m^2 = kg/s^3; dividing by g w_s = m^2/s^3 gives kg/m^2, a mass
# per unit AREA, and dividing again by d gives kg/m^3 = g/L. The chapter's
# bridge wants mg/L, so the last step is a factor of 1000. `validate_beach.py`
# pushes this through its `Dim` algebra rather than trusting the comment.
#
# WHICH DISSIPATION, AND THE FIRST WRITING OF THIS FILE GOT IT WRONG BY A
# FACTOR OF FIFTY. `D` in (1) is the power delivered to the SEDIMENT, and that
# is the BED's dissipation -- the wave boundary layer working on the grains --
# not the wave's total dissipation `tr['D_w']`, which in the surf zone is a
# breaking loss deposited in a surface roller. Using `D_w` gave a depth-averaged
# load of 3.7 g/L across the breaking zone, which is a silt river and not a
# beach, and it would have been reported as a result. The bed's own dissipation
# is the classical stream power,
#
#       D_f = rho c_f <|u|^3>,     <|u|^3> = (4/3 pi) u_orb^3 for a sinusoid
#
# -- the cubic moment of a cosine, which is 0.4244 and is derived rather than
# quoted (`validate_beach.py` integrates it). c_f is `beach.longshore_current`'s
# own 0.006, IMPORTED as a default rather than restated, so a wave that changes
# the friction changes both places at once.
#
# WHAT IS THEREFORE MISSING AND IS NAMED RATHER THAN ADDED: breaking turbulence
# does reach the bed in the inner surf and does suspend sand, and this balance
# does not carry it. The direction of the error is known -- the surf zone's load
# is UNDERSTATED, most where the roller is strongest -- and closing it needs a
# turbulence-injection model that is a wave's work on its own.
EPS_SUSP = 0.02         # Bagnold suspension efficiency, via Bailard (1981). `P`
                        # -- the same paper `beach.py` already takes its
                        # energetics flux structure and its slope term from, so
                        # it is not a new source. The load is LINEAR in it: a
                        # reader who prefers 0.01 halves every SPM here and
                        # changes nothing else.
U3_MEAN = 4.0 / (3.0 * math.pi)     # <|cos|^3>, derived. 0.42441
KAPPA = 0.40            # von Karman. `P`


def bed_dissipation(u_orb, c_f=0.006, rho_w=1025.0):
    """Stream power delivered to the bed, W/m^2, from the orbital velocity."""
    return rho_w * c_f * U3_MEAN * np.asarray(u_orb, float) ** 3


def suspended_load(u_orb, depth, w_s, c_f=0.006, eps_s=EPS_SUSP,
                   rho_s=2650.0, rho_w=1025.0, g=9.80665, d_min=0.10):
    """The suspension, as a load AND as a vertical structure.

    Returns a dict:
        M       kg/m^2, the depth-integrated suspended mass, from (2)
        spm_bar mg/L, the DEPTH-AVERAGED concentration, M/d
        delta   m, the thickness of the layer the load actually occupies
        spm     mg/L, the concentration INSIDE that layer

    THE STRATIFICATION IS NOT A REFINEMENT, IT IS THE DIFFERENCE BETWEEN A BLUE
    SEA AND A MILKY ONE, and getting it wrong is how a physically-derived load
    still produces a wrong picture. The balance (1) fixes the depth-integrated
    mass M and says nothing about where in the column it sits. Where it sits is
    the Rouse problem: turbulent diffusivity eps_v lifts, settling pulls down,
    and the equilibrium profile is exponential with an e-folding height

        ell = eps_v / w_s,      eps_v ~ kappa u* d / 6

    (the depth-mean of the parabolic eddy diffusivity kappa u* z (1 - z/d)).
    With this scene's 0.30 mm sand and a 1.5 m swell, ell is about a metre --
    so in the SURF ZONE, where d is 1-2 m, the load fills the column and the
    water is opaque; at the 8 m offshore boundary the SAME balance puts the same
    kind of load in the bottom metre and leaves seven metres of clear water
    above it. A DEPTH-AVERAGED SPM cannot tell those two apart and renders both
    as milky green.

    That is an optical statement, not a sedimentological one: reflectance is
    dominated by the upper optical depth, so a load hidden under seven metres of
    clear water is nearly invisible while the same load spread through 1.5 m is
    the whole colour of the pixel. `column_reflectance` below is what consumes
    this, and the two-layer split is why it exists."""
    d = np.maximum(np.asarray(depth, float), d_min)
    u = np.maximum(np.asarray(u_orb, float), 0.0)
    m = (eps_s * bed_dissipation(u, c_f, rho_w) * rho_s
         / (g * (rho_s - rho_w) * w_s))                      # kg/m^2
    u_star = np.sqrt(c_f) * u                                # tau = rho c_f u^2
    ell = np.maximum(KAPPA * u_star * d / 6.0, 1e-6) / w_s
    delta = np.minimum(ell, d)
    return dict(M=m, spm_bar=1000.0 * m / d, delta=delta,
                spm=1000.0 * m / delta, ell=ell, u_star=u_star,
                D_f=bed_dissipation(u, c_f, rho_w))


# ================================================== the IOPs, assembled
def iops(a_ph440=None, a_cdom440=A_CDOM_440, spm=0.0, pure=False):
    """The three-band inherent optical properties of this water.

    Returns a dict of length-3 arrays in the renderer's R/G/B band order, each
    a BAND MEAN of a continuous spectrum: a, b, b_b, c = a + b, and the pool's
    own pure-water absorption inside `a`.

    `spm` may be an array; the particulate terms then carry its shape and the
    band axis is last."""
    a_ph440 = A_PH_440 if a_ph440 is None else a_ph440
    if pure:
        a_ph440 = 0.0
        a_cdom440 = 0.0
        spm = 0.0
    a_diss = band_mean(lambda l: a_ph(l, a_ph440) + a_cdom(l, a_cdom440))
    bw = band_mean(b_w)
    # b_p's band mean is linear in SPM, so the band integral is done once on the
    # SHAPE and scaled -- which also keeps an (ny, nx) SPM field from allocating
    # a (ny, nx, 490) array of wavelengths.
    bp_shape = band_mean(lambda l: b_p(l, 1.0))
    spm_a = np.asarray(spm, float)
    bp = spm_a[..., None] * bp_shape[None] if spm_a.ndim else spm_a * bp_shape
    a = OPT.ABS + a_diss                            # pure water is IMPORTED
    b = bw + bp
    b_b = BB_OVER_B * b
    return dict(a=a + np.zeros_like(b), b=b, b_b=b_b, c=a + b,
                a_w=OPT.ABS, a_diss=a_diss, b_p=bp, b_w=bw)


# ============================================ transport 1: the path THROUGH
# SECTION A'S WHOLE ARGUMENT IN ONE FUNCTION. A backlit wave face is a slab of
# water with a light source behind it, and what leaves the front of it is what
# survived the crossing. The colour is therefore the PATH -- it is not a
# property of the water body, it is a property of the LENGTH -- and it must
# vanish when the length does, which is the falsification the bar calls its
# sharpest criterion.
#
# WHICH ATTENUATION COEFFICIENT, AND IT IS NOT c. Chapter 28 is explicit that
# `c = a + b` governs a SHARP SIGHTLINE -- how fast a submerged object's own
# image is lost -- while the ambient column is governed by K_d, and that the two
# differ by 5-20x because forward scattering dominates. A wave face lit from
# behind is neither: it is a diffuse GLOW, and a photon scattered 5 degrees
# forward by a mineral grain is still in the glow. The coefficient for what
# survives as glow is therefore
#
#       c_glow = a + b_b
#
# -- absorption, plus only the share of scattering that turns the photon around.
# That is Gordon's quasi-single-scattering approximation and it is the same
# a + b_b that appears in K_d below, which is the consistency check on the
# choice: the two transports in this file use ONE coefficient.
#
# HOW MUCH IT MATTERS, measured rather than asserted, because it is the largest
# single modelling choice in this file: over a 1.5 m face at this scene's surf
# load the two coefficients differ by a factor of e^(b*(1-1/51)*1.5). `beach_
# render.py` prints both and the README carries the number. Using `c` would make
# every wave face nearly black and would have been attributed to absorption.
def through_path(L_src, path, a, b_b):
    """Radiance through a water path of length `path` (m), given the radiance
    entering it. Beer-Lambert on a + b_b. Shapes broadcast; the band axis is
    last on all three."""
    return np.asarray(L_src, float) * np.exp(
        -(np.asarray(a, float) + np.asarray(b_b, float))
        * np.asarray(path, float)[..., None])


def forward_glow(e_beam, path, cos_theta, a, b, g=None):
    """THE FORWARD GLOW, which chapter 28 asks for by name.

    "leaving g at zero ... kills the forward glow through a sunlit wave crest"
    -- and that glow is a SINGLE-SCATTERING SOURCE inside the water, not an
    attenuation. A beam of irradiance E crossing a slab feeds the view direction
    at b p(Theta) E per metre of path, and both the beam and what it feeds are
    attenuated by the FULL c = a + b, because a photon scattered out of the beam
    has been counted by the source term and must not be counted again as
    survival.

    For a slab whose beam path and view path run nearly along the same axis the
    integral collapses:

        L = INT_0^L b p E exp(-c(L - s)) exp(-c s) ds = b p E L exp(-c L)

    AND THAT EXTRA FACTOR OF L IS A RESULT, not an algebraic accident. The glow
    is NOT Beer-Lambert: it rises linearly out of zero, peaks at L = 1/c and
    falls. A cuvette inversion run on a scattering-dominated signal therefore
    reads

        -ln(T2/T1)/(L2 - L1) = c + ln(L2/L1)/(L2 - L1)

    -- biased HIGH by a term that depends only on the two thicknesses, and
    `beach_render.py` measures exactly that bias on its own frame.

    Units: b [1/m] * p [1/sr] * E [W/m^2] * L [m] = W/m^2/sr. A radiance."""
    g = PHASE_G if g is None else g
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    c = a + b
    L = np.asarray(path, float)[..., None]
    return (b * hg_phase(g, cos_theta) * np.asarray(e_beam, float) * L
            * np.exp(-c * L))


def cuvette_c(t1, t2, l1, l2):
    """THE VARIABLE-PATH CUVETTE, inverted.

        c(lam) = -ln(T2/T1) / (L2 - L1)

    Bar section A: a breaking wave is a WEDGE -- thin at the lip, thick toward
    the trough -- so one frame of one wave contains a two-point transmission
    series at two known thicknesses, and the ratio of the two removes the source
    spectrum, the interface transmittances and the exposure ALL AT ONCE. That is
    why it is an instrument and not a fit: nothing about the illuminant, the
    camera or the Fresnel factors survives the ratio, and only the difference of
    the two path lengths enters.

    WHAT IT CANNOT DO, stated here because it is the finding: it returns ONE
    number per band, and that number is a + b_b summed over three constituents.
    Three bands cannot separate three constituents whose spectra are as
    collinear as CDOM's and NAP's, and it cannot separate a from b at all. The
    second measurement that DOES separate them is the reflectance of the same
    water (below): transmission gives a + b_b, reflectance gives b_b/(a + b_b),
    and the pair is invertible. One frame, two geometries."""
    t1 = np.asarray(t1, float)
    t2 = np.asarray(t2, float)
    return -np.log(t2 / t1) / (np.asarray(l2, float) - np.asarray(l1, float))


def invert_a_bb(c_glow, reflectance, mu_d=MU_D, mu_u=0.5):
    """The pair. Given the cuvette's `a + b_b` and the water's own deep
    reflectance R_inf, recover a and b_b separately.

        R_inf = b_b / ((a + b_b) (1/mu_d + 1/mu_u))     [derived below]
        =>  b_b = R_inf * c_glow * (1/mu_d + 1/mu_u)
            a   = c_glow - b_b

    and then chapter 28's Babin bridge turns b_b into a mineral load."""
    c = np.asarray(c_glow, float)
    bb = np.asarray(reflectance, float) * c * (1.0 / mu_d + 1.0 / mu_u)
    return dict(a=c - bb, b_b=bb, b=bb / BB_OVER_B,
                spm=bb / BB_OVER_B / B_P_555_PER_SPM)


# ======================================= transport 2: the path IN and back OUT
# THE GREY-BLUE BODY, and it is the term the pool never needed. With b_b ~ 0 a
# water column returns only what its BED returns, and `optics.rho_water` is
# exactly that -- the beam in, the slant to the bed, the bed's albedo, the
# escape, and the trapped series, all with the coastal `absorb` passed in. Over
# 20 m of Atlantic there is no bed in reach and that term is zero, so everything
# left is VOLUME BACKSCATTER, which is new.
#
# DERIVED HERE, IN FIVE LINES, BECAUSE IT IS SHORT ENOUGH TO BE DERIVED. Let
# E_d(z) be the downwelling irradiance and E_u(z) the upwelling one.
#
#   E_d(z) = E_d(0) exp(-K_d z),      K_d = (a + b_b)/mu_d
#
# -- the beam loses a to absorption and b_b to being turned around, and mu_d is
# the mean cosine of the field, so the PATH is z/mu_d. Each layer dz turns
# b_b E_d(z) dz upward, and that flux climbs out attenuated by K_u = (a+b_b)/mu_u:
#
#   E_u(0) = INT_0^D b_b E_d(z) exp(-K_u z) dz
#          = b_b E_d(0) (1 - exp(-(K_d + K_u) D)) / (K_d + K_u)
#
#   R(D) = E_u(0)/E_d(0) = [b_b / ((a+b_b)(1/mu_d + 1/mu_u))]
#                          * (1 - exp(-(K_d + K_u) D))
#
# THE DEEP LIMIT IS THE ROW THAT CHECKS IT. As D -> inf this is
# f * b_b/(a + b_b) with f = 1/(1/mu_d + 1/mu_u) -- and f is the constant the
# ocean-colour literature writes as ~0.33 (Gordon et al. 1988; Morel & Prieur
# 1977). With mu_d = 0.86 and mu_u = 0.5 the derivation gives f = 0.3145, which
# is 5% below the published value and is a genuine agreement rather than an
# arranged one: no step above knows what 0.33 is, and the residual 5% is exactly
# what single scattering leaves out. `validate_beach.py` carries it as a tier-2
# row against the literature and as a tier-3 row against a two-stream solve.
MU_U = 0.5              # mean cosine of the upwelling field. Isotropic-upward
                        # is exactly 1/2; the real field is slightly more
                        # vertical, which would raise f toward the published
                        # 0.33. `?`, and the direction of its error is known.


def volume_reflectance(a, b_b, depth, mu_d=MU_D, mu_u=MU_U):
    """Irradiance reflectance of a water column of finite depth, from volume
    backscatter alone. Bed excluded -- `optics.rho_water` is the bed."""
    a = np.asarray(a, float)
    b_b = np.asarray(b_b, float)
    c = a + b_b
    kd, ku = c / mu_d, c / mu_u
    dep = np.asarray(depth, float)[..., None]
    return (b_b / (c * (1.0 / mu_d + 1.0 / mu_u))) * (
        1.0 - np.exp(-(kd + ku) * dep))


F_GORDON = 1.0 / (1.0 / MU_D + 1.0 / MU_U)      # 0.3161, derived


def column_reflectance(a_top, bb_top, d_top, a_bot, bb_bot, d_bot,
                       mu_d=MU_D, mu_u=MU_U):
    """A TWO-LAYER column: clear water over the suspension layer.

    The same integral, split at the interface. For piecewise-constant
    coefficients the derivation above composes exactly -- the light that reaches
    the lower layer is what the upper one passed, and what the lower one returns
    is attenuated on the way back through the same upper layer, which is one
    round trip:

        R = R_top(d_top) + exp(-(K_d + K_u)_top d_top) * R_bot(d_bot)

    There is no interface term because there is no interface: the two layers are
    the same medium at two concentrations, so nothing reflects between them.

    ALSO RETURNED IS `t_col`, the round-trip transmittance of the WHOLE column,
    which is what the bed term needs."""
    a_top, bb_top = np.asarray(a_top, float), np.asarray(bb_top, float)
    a_bot, bb_bot = np.asarray(a_bot, float), np.asarray(bb_bot, float)
    inv = 1.0 / mu_d + 1.0 / mu_u
    ct, cb = a_top + bb_top, a_bot + bb_bot
    dt = np.asarray(d_top, float)[..., None]
    db = np.asarray(d_bot, float)[..., None]
    tt = np.exp(-ct * inv * dt)
    r_top = (bb_top / (ct * inv)) * (1.0 - tt)
    r_bot = (bb_bot / (cb * inv)) * (1.0 - np.exp(-cb * inv * db))
    return dict(R=r_top + tt * r_bot, t_col=tt * np.exp(-cb * inv * db),
                c_bar=(ct * dt + cb * db) / np.maximum(dt + db, 1e-9))


def k_d(a, b_b, mu_d=MU_D):
    """Diffuse attenuation, chapter 28's second coefficient. Gordon's
    K_d ~= (a + b_b)/mu_d -- the same relation used to recover a_ph(440), run
    forward instead of backward."""
    return (np.asarray(a, float) + np.asarray(b_b, float)) / mu_d


def secchi(a, b_b, mu_d=MU_D):
    """Chapter 28's authoring handle, Lee et al. (2015):
    Z_SD ~= 1 / min_lambda K_d(lambda). Reported so the water this file builds
    can be quoted the way the chapter quotes water."""
    return 1.0 / float(np.min(k_d(a, b_b, mu_d)))


# ================================================ the glitter path, Cox & Munk
# BAR SECTION K: the path's angular width is a READOUT OF THE MEAN SQUARE SLOPE,
# and it must come from the slope distribution rather than from a spread
# parameter chosen to look right. So there is no spread parameter in this file.
# There is a wind, a published slope variance, and a Jacobian.
#
# COX & MUNK (1954), from sun-glitter photographs of the Pacific off Maui, clean
# (slick-free) surface, U in m/s at 12.5 m:
#
#       sigma_u^2 = 3.16e-3 U                 along-wind ("up/down wind")
#       sigma_c^2 = 0.003 + 1.92e-3 U         cross-wind
#       mss       = sigma_u^2 + sigma_c^2 = 0.003 + 5.12e-3 U
#
# `P`, cited, and the wind at the reference frame's hour is `?` -- bar section
# K1 says so outright. This file therefore does NOT claim a width for the
# photograph. It states a wind, reports the width that follows, and reports the
# INVERSE map as well, so that a later wave with a wind observation can check
# the number without rerunning anything.
CM_A_U = 3.16e-3
CM_A_C = 1.92e-3
CM_B_C = 0.003


def cox_munk_mss(u10):
    """(sigma_u^2, sigma_c^2), the along- and cross-wind slope variances."""
    u = np.asarray(u10, float)
    return CM_A_U * u, CM_B_C + CM_A_C * u


def wind_from_mss(mss):
    """The inverse readout: a measured total mean square slope, as a wind."""
    return (np.asarray(mss, float) - CM_B_C) / (CM_A_U + CM_A_C)


U10 = 6.0               # m/s. `?` -- the wind at the frame's hour is unknown
                        # and the bar says so. 6 m/s is a moderate summer sea
                        # breeze on this coast; every glitter number this file
                        # reports is a function of it and is reported as such.
WIND_AZ = 315.0         # deg, the direction the wind blows TOWARD, in the same
                        # compass `atmosphere.solar_position` returns. `?`.
                        # It sets only the ORIENTATION of the slope ellipse; the
                        # anisotropy sigma_u/sigma_c is 1.28 at U10 = 6, so the
                        # path's width changes by at most 28% with it.


def slope_pdf(zx, zy, u10=U10, wind_az=WIND_AZ):
    """The Cox-Munk slope probability density, anisotropic, per unit slope^2.

    Gaussian, NOT the Gram-Charlier series. Cox & Munk's own paper adds skewness
    and peakedness corrections; they change the pdf by a few per cent near the
    peak and more in the far wings, and they are `?` here because this file
    reports a WIDTH -- a half-maximum -- which the corrections move far less
    than they move the wings. Recorded as a known omission and NOT as a
    negligible one: the wings are where a glitter path's faint outer edge is."""
    su2, sc2 = cox_munk_mss(u10)
    ph = math.radians(wind_az)
    # the wind's own axes: `u` along the wind, `c` across it
    zu = np.asarray(zx, float) * math.sin(ph) + np.asarray(zy, float) * math.cos(ph)
    zc = -np.asarray(zx, float) * math.cos(ph) + np.asarray(zy, float) * math.sin(ph)
    return (1.0 / (2.0 * np.pi * math.sqrt(su2 * sc2))
            * np.exp(-0.5 * (zu * zu / su2 + zc * zc / sc2)))


# --- THE RADIANCE, DERIVED, BECAUSE THE JACOBIAN IS THE WHOLE PHYSICS ---------
# Per unit HORIZONTAL area, facets whose slope lies in dz_x dz_y occupy a
# horizontal area p dz and therefore a TRUE area p dz / cos beta, where beta is
# the facet's tilt from vertical, cos beta = 1/sqrt(1 + z^2).
#
#   flux intercepted from a beam of normal irradiance E_n:
#       dPhi_i = E_n cos(omega) * p dz / cos beta
#   reflected:  dPhi_r = rho(omega) dPhi_i
#
# It leaves into the mirror direction, and the two Jacobians are:
#       dw_n = cos^3(beta) dz_x dz_y          (slope space -> normal direction)
#       dw_v = 4 cos(omega) dw_n              (mirror doubling)
# The observer sees a unit horizontal patch as cos(theta_v) of projected area,
# so
#       L = dPhi_r / (cos theta_v dw_v)
#         = rho(omega) E_n p(z) / (4 cos^4(beta) cos theta_v)
#
# which is Cox & Munk's glitter radiance. NOTHING IN IT IS FREE: rho is
# `optics.fresnel`, E_n is `atmosphere.E_SUN`, p is the published slope
# distribution, and the rest is geometry. There is no width to choose, which is
# precisely what bar section K demands.
#
# THE ENERGY CHECK THAT COMES WITH IT: integrating L cos theta_v over the upward
# hemisphere must return INT rho(omega) E_n cos(omega) p / cos beta dz -- the
# flux the tilted facets actually intercept, which is NOT E_n cos(theta_s)
# unless the surface is flat. The suite runs both integrals; their ratio is the
# tilt gain, and it is the term a renderer that normalises glitter to a flat
# surface silently throws away.
def glitter_radiance(sun_dir, view_dir, e_sun=None, u10=U10, wind_az=WIND_AZ,
                     shadow=True):
    """Specular sea-surface radiance toward the observer.

    `sun_dir`   unit vector TOWARD the sun, world axes (+x E, +y N, +z up)
    `view_dir`  unit vector of PROPAGATION from the eye into the scene, so its
                z is negative when looking down at the sea
    returns     (..., 3) radiance

    `shadow` applies the Smith/Bourlier-style bistatic shadowing factor for a
    Gaussian surface, which is what keeps the horizon from going infinite: at
    theta_v -> 90 the 1/cos(theta_v) in the Jacobian diverges and the real
    surface hides its own far slopes. It is derived beside its own function."""
    s = np.asarray(sun_dir, float)
    v = np.asarray(view_dir, float)
    v = v / np.linalg.norm(v, axis=-1, keepdims=True)
    r = -v                                   # direction back toward the eye
    n = s + r
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
    nz = np.maximum(n[..., 2], 1e-6)
    zx, zy = -n[..., 0] / nz, -n[..., 1] / nz
    cos_beta = nz
    cos_om = np.clip((s * n).sum(-1), 0.0, 1.0)
    cos_tv = np.maximum(r[..., 2], 1e-6)     # view zenith cosine, upward leg
    e = ATM.E_SUN if e_sun is None else np.asarray(e_sun, float)
    p = slope_pdf(zx, zy, u10, wind_az)
    out = (OPT.fresnel(cos_om) * e
           * (p / (4.0 * cos_beta ** 4 * cos_tv))[..., None])
    if shadow:
        out = out * shadow_factor(s[..., 2], r[..., 2], u10)[..., None]
    valid = (s[..., 2] > 0.0) & (r[..., 2] > 0.0)
    return np.where(np.asarray(valid)[..., None], out, 0.0)


def _lam_smith(mu, sigma):
    """Smith's (1967) Lambda for a Gaussian rough surface: the mean number of
    times a ray at cosine `mu` re-enters the surface per unit run, in units of
    the surface's own correlation length. Written from the definition rather
    than quoted:

        Lambda(mu) = 1/2 [ sigma/(t sqrt(pi)) exp(-t^2/sigma^2) - erfc(t/sigma) ]
        with t = mu / sqrt(1 - mu^2) = cot(theta)

    `sigma` is the RMS slope in the direction of travel."""
    mu = np.clip(np.asarray(mu, float), 1e-6, 1.0)
    t = mu / np.sqrt(np.maximum(1.0 - mu * mu, 1e-12))
    x = t / sigma
    return 0.5 * (np.exp(-x * x) / (x * math.sqrt(np.pi)) - _erfc(x))


def _erfc(x):
    return 1.0 - _erf(x)


def _erf(x):
    """Abramowitz & Stegun 7.1.26, |eps| < 1.5e-7 -- enough for a shadowing
    factor and it keeps this module free of scipy, which nothing else here
    needs."""
    x = np.asarray(x, float)
    sgn = np.sign(x)
    z = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * z)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                - 0.284496736) * t + 0.254829592) * t * np.exp(-z * z)
    return sgn * y


def shadow_factor(mu_s, mu_v, u10=U10):
    """Bistatic Smith shadowing: the joint probability that a facet is both lit
    and visible. 1/(1 + Lambda(mu_s) + Lambda(mu_v)) is the standard
    uncorrelated form and it is what keeps the horizon finite.

    ISOTROPIC sigma is used here even though the slope field is anisotropic:
    the shadowing function is an integral over the whole run of the surface
    toward the horizon, which crosses both wind axes. `?` on the anisotropic
    version; the two differ by under 3% at U10 = 6."""
    su2, sc2 = cox_munk_mss(u10)
    sig = math.sqrt(0.5 * (su2 + sc2))
    return 1.0 / (1.0 + _lam_smith(mu_s, sig) + _lam_smith(mu_v, sig))


def glitter_azimuth_profile(sun_el_deg, view_el_deg, sun_az_deg, dphi_deg,
                            u10=U10, wind_az=WIND_AZ, e_sun=None):
    """The glitter radiance across the path at one view elevation.

    Returns the (n,) green-band radiance for view azimuths offset by `dphi_deg`
    from the sun's. This is the measurement bar section K asks for and it is
    made in ANGLE, not in pixels: the path's width in the image is a mixture of
    the surface's statistics and the camera's perspective, and only the angular
    profile isolates the first."""
    els = math.radians(sun_el_deg)
    s = np.array([math.sin(math.radians(sun_az_deg)) * math.cos(els),
                  math.cos(math.radians(sun_az_deg)) * math.cos(els),
                  math.sin(els)])
    # THE EYE IS OPPOSITE THE SUN, NOT UNDER IT. A flat sea reflects a beam
    # arriving from azimuth `sun_az` into azimuth `sun_az + 180` at the same
    # elevation -- the observer looks TOWARD the sun and the ray that reaches
    # the eye leaves the surface AWAY from it. Writing the eye at the sun's own
    # azimuth puts the required facet normal on the sun instead of on the
    # vertical, and the whole path evaluates at exp(-135) instead of at its
    # peak. That is the first thing this function did, and it is silent: a
    # glitter model with the wrong branch renders black rather than wrong.
    ev = math.radians(view_el_deg)
    az = math.radians(sun_az_deg + 180.0) + np.deg2rad(np.asarray(dphi_deg,
                                                                  float))
    r = np.stack([np.sin(az) * math.cos(ev),
                  np.cos(az) * math.cos(ev),
                  np.full(az.shape, math.sin(ev))], axis=-1)
    return glitter_radiance(s[None], -r, e_sun=e_sun, u10=u10,
                            wind_az=wind_az)


def fwhm(x, y):
    """Full width at half maximum of a sampled profile, by linear interpolation
    on each flank. Returns (width, x_peak). No fitting: the profile is the
    physics and a Gaussian fit to it would be a second model."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    i = int(np.argmax(y))
    half = 0.5 * y[i]
    lo = hi = None
    for j in range(i, 0, -1):
        if y[j - 1] <= half <= y[j]:
            lo = x[j - 1] + (half - y[j - 1]) * (x[j] - x[j - 1]) / (
                y[j] - y[j - 1] + 1e-300)
            break
    for j in range(i, len(x) - 1):
        if y[j + 1] <= half <= y[j]:
            hi = x[j] + (half - y[j]) * (x[j + 1] - x[j]) / (
                y[j + 1] - y[j] + 1e-300)
            break
    if lo is None or hi is None:
        return float('nan'), float(x[i])
    return float(hi - lo), float(x[i])


def glitter_width_deg(sun_el_deg, view_el_deg, sun_az_deg=0.0, u10=U10,
                      wind_az=WIND_AZ, span=60.0, n=1201):
    """The path's width at one view elevation, two ways.

    `dphi`  the width in view AZIMUTH, degrees -- how far round the compass the
            path extends at this elevation.
    `psi`   the same width as an ANGLE ON THE SKY, dphi * cos(view elevation),
            which is what a camera measures and what the photograph shows.

    The two differ by cos(elevation) and they trend in OPPOSITE directions near
    the horizon; reporting only one is how a glitter path gets called uniform."""
    dphi = np.linspace(-span, span, n)
    L = glitter_azimuth_profile(sun_el_deg, view_el_deg, sun_az_deg, dphi,
                                u10=u10, wind_az=wind_az)[:, 1]
    w, pk = fwhm(dphi, L)
    return dict(dphi=w, psi=w * math.cos(math.radians(view_el_deg)),
                peak_dphi=pk, peak_L=float(np.max(L)))


# ============================================================ the foam PLACEHOLDER
# BAR SECTION C NAMES THREE MECHANISMS AND THIS FILE IMPLEMENTS NONE OF THEM.
#
#   surface foam        a coverage mask that floats, deforms and decays slowly
#   entrained air       a participating medium that HIDES THE BED behind it
#   airborne spray      the particle one, and the smallest share of the white
#
# All three whiten from the same 1 - 1/n^2 = 43.874% that runs the mirror
# outside Snell's window, and that constant is the only part of section C this
# file uses. What follows is a COVERAGE MASK DRIVEN BY THE BREAKING FRACTION and
# nothing else: no advection, no decay, no residence time, no volume, no bed
# hiding, no spray. It is here because the breaking zone with no white at all
# reads as a different scene, and the frames it appears in SAY SO IN THEIR OWN
# CAPTION -- the convention wave 1 used for the stamped rip channels and wave 3
# used for their absence.
#
# WHY IT IS NOT MORE THAN THIS. Section C's three mechanisms are three different
# representations -- a surface field with its own advection and decay, a
# participating medium with an albedo and an optical depth, and a particle
# system -- and section H2 adds a fourth requirement on top (foam STRANDED by the
# retreating swash, so two residence times on one surface) while section H5 adds
# rotational structure that a potential-flow advection cannot produce. That is a
# wave's work and probably two. A hurried version of it would be indistinguishable
# from the "make all of it particles" failure the bar opens section C by naming.
FOAM_WHITE = 1.0 - 1.0 / OPT.IOR ** 2       # 0.4362 / 0.4383 / 0.4433


def foam_coverage(f_break, k=1.0):
    """PLACEHOLDER. Coverage fraction from the breaking fraction, saturating.

    One parameter, `k`, and it is a DECLARED shape with no measurement behind
    it. Do not read a foam width, a decay time or a coverage number off any
    frame this produces."""
    return 1.0 - np.exp(-k * np.clip(np.asarray(f_break, float), 0.0, 1.0))
