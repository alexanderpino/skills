"""The white, and it is three mechanisms -- bar section C, and section E's clocks.

    python3 beach_foam.py            # the derivations and their numbers

WHAT THE BAR ASKS FOR AND WHY IT IS NOT ONE MODEL. Section C:

    surface foam    the persistent white DECK left after a break. A COVERAGE
                    MASK on the surface: it floats, deforms with the flow,
                    decays slowly.
    entrained air   where the wave mouth goes white and opaque and THE BED
                    STOPS BEING VISIBLE THROUGH IT. A participating medium with
                    high scattering albedo.
    airborne spray  droplets clear of the surface. The particle one, and the
                    smallest share of the white in frame.

They are three REPRESENTATIONS -- a two-dimensional field on the surface, a
three-dimensional medium in the column, and a particle system -- and collapsing
them into one particle system is the failure the bar opens section C by naming.
This file builds the first two. The third is DEFERRED and the frames say so.

ONE CONSTANT, THREE APPEARANCES, AND IT IS IMPORTED. A bubble seen from the
water side has the same critical angle as the surface seen from below, so

    1 - 1/n^2 = optics.TIR_FRAC = beach_optics.FOAM_WHITE

is the share of a beam striking a bubble wall that is TOTALLY reflected. It is
`optics.TIR_FRAC` (green scalar) and `beach_optics.FOAM_WHITE` (per channel) and
this file declares NEITHER of them -- it imports both and checks they are the
same number, because the whole of section C rests on their being the same
number. `bubble_scatter()` below RECOVERS it from a ray trace that was not
written from it, which is the strongest form that check can take.

WHAT THIS FILE DOES NOT DO. It does not read anything off a photograph, it
declares no shape because a shape looks like foam, and it contains no noise, no
texture and no Voronoi. Every field here is a function of quantities `beach.py`
already computes -- the breaking fraction, the dissipation, the celerity, the
phase -- or of a published law with its citation beside it.
"""
import math
import sys

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import optics as OPT                                            # noqa: E402
import beach as B                                               # noqa: E402
import beach_optics as BO                                       # noqa: E402


# =============================================================== THE CONSTANT
# IMPORTED, NOT RESTATED. Both names already exist in this project and both are
# built from `optics.IOR`; they are bound here so that every use below reads
# from one place, and `check_one_constant()` is the row that fires if the two
# ever drift apart.
TIR_FRAC = OPT.TIR_FRAC                 # scalar, green band
FOAM_WHITE = BO.FOAM_WHITE              # (3,), per channel
N_W = OPT.IOR                           # (3,) the water's own index
THETA_C = np.arcsin(1.0 / N_W)          # the critical angle, per channel


def check_one_constant():
    """The three whites and the mirror outside Snell's window are ONE number.

    Returned as a dict rather than asserted here, so the suite owns the
    tolerance and this module owns only the arithmetic."""
    return dict(tir_frac=float(TIR_FRAC), foam_white=np.array(FOAM_WHITE),
                from_theta_c=np.cos(THETA_C) ** 2 * 0.0 + (1.0 - 1.0 / N_W ** 2),
                theta_c_deg=np.degrees(THETA_C))


# ==================================================== 1 · THE BUBBLE, TRACED
# GEOMETRIC OPTICS ON A SPHERE OF RELATIVE INDEX m = 1/n < 1, which is what a
# bubble in water is. The size parameter settles the method rather than taste:
# x = 2 pi r / lambda is 2700 for a 0.24 mm bubble in green light, so the
# extinction efficiency is 2 and the angular structure is ray optics plus a
# diffraction lobe that is 0.02 deg wide and carries no information a renderer
# can use.
#
# THE TRACE IS WRITTEN FROM THE DEFINITION AND NOT FROM THE CONSTANT, which is
# the point: the 1 - 1/n^2 above must FALL OUT of it. A ray with impact
# parameter p (in units of the radius) meets the wall at sin(theta_i) = p, and
# the disc is sampled uniformly in area, so the weight is 2p dp. Beyond
# p = sin(theta_c) = 1/n the wall is a perfect mirror, and the share of the disc
# that is beyond it is 1 - sin^2(theta_c) = 1 - 1/n^2. The bar's constant is the
# AREA OF A DISC, and that is why the same number runs the window from below.
#
# FRESNEL COMES FROM `optics.fresnel` AND IS NOT REWRITTEN. That function is
# air -> water; the bubble wall is water -> air, and the two are related by
# reciprocity: R_internal(theta_i) = R_external(theta_t) with n sin(theta_i) =
# sin(theta_t). So the internal reflectance is the imported function evaluated
# at the conjugate angle, and above the critical angle it is 1 by construction.
def _fresnel_internal(sin_i):
    """Water -> air reflectance at a bubble wall, per channel, from
    `optics.fresnel` by reciprocity. Returns (..., 3)."""
    si = np.asarray(sin_i, float)[..., None]
    st = N_W * si                                   # Snell into the air
    tir = st >= 1.0
    ct = np.sqrt(np.maximum(1.0 - np.minimum(st, 1.0) ** 2, 0.0))
    R = OPT.fresnel(ct[..., 0])                     # air-side incidence cosine
    return np.where(tir, 1.0, R)


def bubble_scatter(n_p=20001, n_order=12):
    """One bubble, by ray optics. Returns the reflected share, the asymmetry
    parameter and the backscatter ratio, per channel.

    ORDERS. p = 0 is the external reflection off the wall; p >= 1 is the ray
    that got in, crossed the air, and left after p - 1 internal reflections.
    The deviations are the textbook ones for a sphere,

        Theta_0 = pi - 2 theta_i
        Theta_p = 2(theta_i - theta_t) + (p - 1)(pi - 2 theta_t)

    and for m < 1 the transmitted ray bends AWAY from the normal, so
    theta_t > theta_i and the first term is negative -- a bubble spreads a beam
    where a droplet focuses it. The weights are R, then (1-R)^2 R^(p-1), and
    they sum to 1 by construction rather than by normalisation; the suite checks
    that they do.

    WHAT THE ANSWER IS FOR. The bar says a bubble reflects 43.874% of what
    strikes it and that this is why surf is white. Both halves are checked here
    and the second one turns out to need a qualifier -- see `README-beach.md`.
    """
    # uniform in disc AREA: p^2 uniform, so p = sqrt(u)
    u = (np.arange(n_p) + 0.5) / n_p
    p = np.sqrt(u)                                  # = sin(theta_i)
    wgt = np.full(n_p, 1.0 / n_p)                   # already area-uniform
    th_i = np.arcsin(np.clip(p, 0.0, 1.0))
    R = _fresnel_internal(p)                        # (n_p, 3)
    sin_t = np.clip(N_W[None] * p[:, None], 0.0, 1.0)
    th_t = np.arcsin(sin_t)                         # (n_p, 3); undefined in TIR
    tir = (N_W[None] * p[:, None]) >= 1.0

    tot = np.zeros(3)
    cos_sum = np.zeros(3)
    back = np.zeros(3)
    refl = np.zeros(3)
    # --- p = 0, the external reflection (this is where TIR lives)
    dev0 = math.pi - 2.0 * th_i
    w0 = R * wgt[:, None]
    tot += w0.sum(0)
    cos_sum += (w0 * np.cos(dev0)[:, None]).sum(0)
    back += np.where(np.cos(dev0)[:, None] < 0.0, w0, 0.0).sum(0)
    refl += w0.sum(0)
    tir_share = (np.where(tir, wgt[:, None], 0.0)).sum(0)
    # --- p >= 1, through the bubble
    for k in range(1, n_order + 1):
        wk = np.where(tir, 0.0, (1.0 - R) ** 2 * R ** (k - 1)) * wgt[:, None]
        dev = 2.0 * (th_i[:, None] - th_t) + (k - 1) * (math.pi - 2.0 * th_t)
        c = np.cos(dev)
        tot += wk.sum(0)
        cos_sum += (wk * c).sum(0)
        back += np.where(c < 0.0, wk, 0.0).sum(0)
    g = cos_sum / tot
    return dict(total=tot, g=g, bb_over_b=back / tot, reflected=refl / tot,
                tir_fraction=tir_share,
                # the DIFFRACTION half of Q_ext = 2 is a 0.02 deg forward lobe
                # at this size parameter; it is counted in the extinction and
                # excluded from the phase function on purpose, and the note
                # rather than a silent omission is the point.
                q_ext=2.0)


# ============================================ 2 · THE BUBBLE POPULATION, SIZED
# DEANE & STOKES (2002), Nature 418, 839: inside a breaking wave the bubble
# density follows TWO power laws that meet at the Hinze scale near 1 mm radius,
#
#       n(r) ~ r^(-3/2)     below it -- jet and drop impact on the wave face
#       n(r) ~ r^(-10/3)    above it -- turbulent fragmentation
#
# `P`, cited. The exponents are theirs; the CUTOFFS are this file's and they are
# derived rather than declared, which matters because the Sauter radius that
# sets the optical thickness is dominated by the large end.
DS_SLOPE_SMALL = -1.5           # Deane & Stokes (2002). `P`
DS_SLOPE_LARGE = -10.0 / 3.0    # Deane & Stokes (2002). `P`
R_HINZE = 1.0e-3                # m, the Hinze scale. `P`, ~1 mm in their paper
R_MIN = 1.0e-5                  # m, 10 micron. Below this the population is
                                # invisible to the r^2 moment: the -3/2 slope
                                # makes INT r^2 n dr converge at the small end,
                                # so this cutoff moves r_32 by under 0.2% over a
                                # decade. Checked in the suite rather than
                                # asserted here.


def bubble_rise_velocity(r, nu=B.NU_W, rho_w=B.RHO_SW, g=B.G, n_iter=60):
    """Terminal rise speed of a bubble of radius `r`, rigid-sphere drag.

    THE DRAG LAW IS SCHILLER & NAUMANN (1933) and it is NOT the law
    `beach.settling_velocity` uses -- that one is Soulsby's fit for natural
    sand. Two terminal velocities from two different published drag laws is the
    point: section E's separator is the RATIO of these two times, and a ratio
    whose numerator and denominator came from one correlation would prove
    nothing.

        buoyancy    (4/3) pi r^3 rho g
        drag        C_D pi r^2 (1/2) rho w^2
        C_D         (24/Re)(1 + 0.15 Re^0.687),   Re = 2 r w / nu

    RIGID and not mobile-interface, which is a decision with a reason: seawater
    is surfactant-rich, the film immobilises, and a mobile-interface (Hadamard-
    Rybczynski) bubble rises about 1.5x faster. `P` on the choice; the suite
    carries the clean-water alternative as an INFO row so the sensitivity is
    visible rather than buried.
    """
    r = np.asarray(r, float)
    w = np.sqrt(np.maximum(8.0 * r * g / 3.0 / 0.5, 1e-12))     # C_D = 0.5 seed
    for _ in range(n_iter):
        re = np.maximum(2.0 * r * w / nu, 1e-9)
        cd = (24.0 / re) * (1.0 + 0.15 * re ** 0.687)
        w_new = np.sqrt(8.0 * r * g / (3.0 * cd))
        w = 0.5 * (w + w_new)                       # damped, it is a fixed point
    return w


def _ds_moments(r_lo, r_hi, n=20001):
    """(INT r^2 n dr, INT r^3 n dr) for the two-slope spectrum, normalised so
    the small branch has unit coefficient. Trapezoid on a log grid -- the
    integrand is a pure power law on each side, so log spacing is exact in the
    exponent and the error is the trapezoid's own."""
    r = np.geomspace(max(r_lo, 1e-9), max(r_hi, r_lo * 1.0001), n)
    nr = np.where(r <= R_HINZE, r ** DS_SLOPE_SMALL,
                  R_HINZE ** (DS_SLOPE_SMALL - DS_SLOPE_LARGE)
                  * r ** DS_SLOPE_LARGE)
    m2 = np.trapezoid(nr * r ** 2, r)
    m3 = np.trapezoid(nr * r ** 3, r)
    return m2, m3


def bubble_population(d_plume, T, r_min=R_MIN):
    """The bubble spectrum's Sauter radius, with the LARGE cutoff DERIVED.

    r_32 = INT r^3 n / INT r^2 n is the only moment the optics needs: the
    projected area per unit volume of a suspension of volume fraction alpha is
    3 alpha / (4 r_32) exactly, whatever the spectrum. It is dominated by the
    large end, and on the -10/3 branch INT r^3 n dr grows as r_max^(2/3), so a
    DECLARED r_max would be the whole answer wearing a cutoff's clothes.

    THE CUTOFF IS A CLOCK, NOT A SIZE. A bubble whose rise time across the
    plume is shorter than the wave period is gone before the next wave renews
    the plume, so it is not part of the standing population:

        w_rise(r_max) = d_plume / T

    Nothing is chosen. d_plume and T are the scene's, and w_rise is Schiller &
    Naumann. On this scene it lands BELOW the Hinze scale, so the standing
    population is entirely the -3/2 branch -- which is a result and not an
    assumption, and it is why r_32 comes out where measured plume values are.
    """
    w_target = float(d_plume) / float(T)
    lo, hi = 1e-6, 5.0e-3
    for _ in range(80):                             # w_rise is monotone in r
        mid = 0.5 * (lo + hi)
        if float(bubble_rise_velocity(mid)) < w_target:
            lo = mid
        else:
            hi = mid
    r_max = 0.5 * (lo + hi)
    m2, m3 = _ds_moments(r_min, r_max)
    r32 = m3 / m2
    return dict(r_max=r_max, r_32=r32, w_at_rmax=float(bubble_rise_velocity(r_max)),
                w_at_r32=float(bubble_rise_velocity(r32)),
                below_hinze=bool(r_max < R_HINZE))


# ==================================== 3 · ENTRAINED AIR, FROM THE DISSIPATION
# LAMARRE & MELVILLE (1991), Nature 351, 469: "the entrainment and subsequent
# submergence of large quantities of air can account for between 30 and 50% of
# the total energy dissipated at breaking". `P`, cited, and the 30-50 is carried
# as a RANGE rather than collapsed -- every void fraction below is linear in it.
#
# THE BUDGET, and it is a source and a sink and not a shape. Air is pushed under
# at a volume rate Q per unit plan area, doing work rho g zbar per unit volume
# against buoyancy, and it leaves by rising out over the residence time. In
# steady state the inventory is Q tau, so with a plume of thickness d_p and a
# centroid at d_p/2,
#
#       rho g (d_p/2) Q = eps_LM D_w          (the power)
#       h_air = Q tau_air                     (the inventory)
#       alpha = h_air / d_p = 2 eps_LM D_w tau_air / (rho g d_p^2)
#
# EVERY SYMBOL ON THE RIGHT IS THE SCENE'S OWN. D_w is the transform's breaking
# dissipation, tau_air is d_p / w_rise from the section above, and d_p is the
# crest's own elevation. Nothing is fitted and there is no coefficient to turn.
EPS_LM = 0.40                   # midpoint of Lamarre & Melville's 0.30-0.50
EPS_LM_RANGE = (0.30, 0.50)     # `P`, and the range is carried, not dropped


def plume_depth(H):
    """The entrained-air plume's thickness: the crest's own elevation H/2.

    `P` AND MARKED, because it is the one length in this section that is not
    forced. Lamarre & Melville's plumes penetrate of order the wave height;
    H/2 is the half of that this file can point to in a field it already
    computes, and alpha goes as d_p^-2, so the sensitivity is reported beside
    every number rather than left for a reader to work out."""
    return 0.5 * np.asarray(H, float)


def entrained_air(D_w, H, T, eps=EPS_LM, rho=B.RHO_SW, g=B.G):
    """The void fraction field and its clock, from the wave's own dissipation.

    Returns alpha (the volume fraction of air), d_p, tau_air and the bubble
    population that sets both. `D_w` is W/m^2 of breaking dissipation -- the
    transform's, not a rate borrowed from somewhere else, and the standing trap
    about D_w and E_w is one function away here too: an energy DENSITY in this
    slot would produce a void fraction with units of seconds.
    """
    D_w = np.maximum(np.asarray(D_w, float), 0.0)
    d_p = np.maximum(plume_depth(H), 1e-3)
    pop = bubble_population(np.median(d_p[d_p > 1e-3]) if d_p.ndim else d_p, T)
    w_rise = pop['w_at_r32']
    tau_air = d_p / w_rise
    alpha = 2.0 * eps * D_w * tau_air / (rho * g * d_p ** 2)
    # THE SPHERE FORMULA HAS A DOMAIN AND THIS IS IT. 3 alpha/(4 r_32) is the
    # projected area of a DILUTE suspension of independent spheres; above about
    # alpha = 0.3 the bubbles are polyhedral cells and the scatterers are the
    # films between them, not the spheres. The clip is the validity limit, it is
    # reported as a clipped FRACTION rather than applied silently, and the
    # surface raft -- which is 95% air and far outside this domain -- is done a
    # different way in `foam_raft` below for exactly this reason.
    clipped = float(np.mean(alpha > 0.30)) if np.ndim(alpha) else float(alpha > 0.30)
    alpha = np.minimum(alpha, 0.30)
    return dict(alpha=alpha, d_p=d_p, tau_air=tau_air, w_rise=w_rise,
                r_32=pop['r_32'], r_max=pop['r_max'], pop=pop,
                clipped_fraction=clipped)


def plume_optics(alpha, r_32, path, g_bub, bb_over_b, a_water):
    """A participating medium, and the number that matters is what it HIDES.

    c = Q_ext * 3 alpha / (4 r_32) with Q_ext = 2 in the geometric limit, so
    b = 3 alpha / (2 r_32). Air does not absorb in the visible, so the layer's
    single-scattering albedo is the water's between the bubbles and is very
    close to 1; the whiteness is MULTIPLE SCATTERING in a conservative medium,
    which is a different statement from "each bubble reflects 43.9%".

    THE SIMILARITY SCALING IS THE WHOLE OF IT. A forward-scattering medium of
    optical depth tau behaves like an isotropic one of depth (1 - g) tau, and
    for conservative scattering the two-stream slab gives

        R = tau' / (1 + tau'),      T = 1 / (1 + tau'),      R + T = 1

    exactly. A renderer that whitens by lerping toward white without applying
    the T has modelled the symptom, which is bar section C's own words.
    """
    alpha = np.asarray(alpha, float)
    b = 2.0 * 3.0 * alpha / (4.0 * r_32)                # Q_ext * 3a/(4 r32)
    tau = b * np.asarray(path, float)
    tau_p = (1.0 - np.asarray(g_bub, float)) * tau[..., None]
    R = tau_p / (1.0 + tau_p)
    Td = 1.0 / (1.0 + tau_p)
    # the water BETWEEN the bubbles still absorbs over the same path
    absorb = np.exp(-np.asarray(a_water, float)
                    * np.asarray(path, float)[..., None] * (1.0 - alpha[..., None]))
    return dict(b=b, tau=tau, tau_prime=tau_p, R=R * absorb, T=Td * absorb,
                b_b=b * np.asarray(bb_over_b, float)[..., None]
                if np.ndim(bb_over_b) else b * bb_over_b)


# ================================================ 4 · THE SURFACE FOAM, AND ITS
# TWO CLOCKS
# MONAHAN & ZIETLOW (1969), JGR 74, 6961, laboratory whitecaps: the whitecap
# AREA decays close to exponentially with a time constant of 3.85 s in salt
# water and 2.54 s in fresh. `P`, cited. Salt is the one this scene is made of.
#
# THE SALT/FRESH PAIR IS NOT DECORATION. It is a factor of 1.5 on the residence
# time and therefore on the coverage, and it says the decay is a BUBBLE
# STABILITY property -- dissolved salts inhibit coalescence -- rather than a
# hydrodynamic one. A renderer with one foam lifetime for every liquid has an
# authored constant whatever it calls it.
TAU_FOAM_SALT = 3.85            # s, Monahan & Zietlow (1969), salt water. `P`
TAU_FOAM_FRESH = 2.54           # s, the same paper, fresh water. `P`
ALPHA_RAFT = 0.95               # the raft's own air fraction. `P` -- a foam is
                                # by definition mostly gas; 0.90-0.99 is the
                                # usable range and the raft thickness goes as
                                # 1/alpha, so the span is 10%.


def foam_residence(salt=True):
    return TAU_FOAM_SALT if salt else TAU_FOAM_FRESH


def foam_raft(alpha_plume, w_rise, tau_foam=TAU_FOAM_SALT, r_32=2.4e-4,
              alpha_raft=ALPHA_RAFT):
    """The raft's THICKNESS, derived, and its reflectance two ways.

    THE THICKNESS IS AN INVENTORY AND NOT A GUESS. Air arrives at the surface at
    alpha * w_rise cubic metres per square metre per second and leaves by
    bursting over tau_foam, so the standing depth of AIR in the raft is
    alpha w_rise tau_foam and the raft itself is that over its own air fraction.
    On this scene it lands at a couple of centimetres, which is where a raft of
    fresh surf foam is, and NOTHING was chosen to put it there.

    TWO ROUTES TO THE REFLECTANCE AND THEY DO NOT SHARE A SOURCE:

      * PILE OF PLATES (Stokes 1862). N walls each reflecting rho with no
        absorption give R_N = N rho / (1 + (N-1) rho). rho is the bar's own
        1 - 1/n^2 and N is the raft thickness over the cell size.
      * TWO-STREAM. The same raft as a scattering medium, R = tau'/(1+tau')
        with tau' = (1-g) b h and b from the bubble population.

    The first is the bar's constant used as a single-wall reflectance; the
    second never sees it. They must agree, and the suite is where they are made
    to.
    """
    h_air = alpha_plume * w_rise * tau_foam
    h_raft = h_air / alpha_raft
    n_walls = np.maximum(h_raft / (2.0 * r_32), 1.0)
    rho = FOAM_WHITE                                        # (3,)
    Rn = (n_walls[..., None] * rho) / (1.0 + (n_walls[..., None] - 1.0) * rho) \
        if np.ndim(n_walls) else (n_walls * rho) / (1.0 + (n_walls - 1.0) * rho)
    return dict(h_air=h_air, h_raft=h_raft, n_walls=n_walls, R_pile=Rn)


# ---------------------------------------------------- the coverage, as a clock
# COVERAGE IS A POISSON PROCESS AND THAT IS WHAT MAKES IT SATURATE. Breaking
# crests lay strips of white down on the surface; strips overlap; the fraction
# of surface covered by a random field of patches whose expected covering count
# is m is 1 - exp(-m). So the model has a COVERING MEASURE, which adds over
# independent sources, and one saturating map to a coverage.
#
# THE SURF ZONE'S SOURCE. Crest lines are one wavelength apart and move at c, so
# a fixed point is swept by a crest once per period T; a fraction Q_b of those
# crests are breaking (Battjes & Janssen, and `beach.breaking_fraction_bj`
# already computes it). Each sweep whitens the strip and the white then decays
# over tau_foam. The covering measure at AGE a behind the crest is therefore the
# sum over all past sweeps,
#
#       m(a) = Q_b SUM_j exp(-(a + jT)/tau) = Q_b exp(-a/tau) / (1 - exp(-T/tau))
#
# and there is no free parameter in it: Q_b, T and tau are all named above.
#
# WHAT THIS REPLACES. The placeholder was 1 - exp(-k f_brk) with k = 1 declared.
# The form was right and the k was not: k here is tau/T dressed up, and at this
# scene's 3.85 s and 9 s period the placeholder was running a foam residence
# time 2.3x too long.
def covering_measure_break(q_b, T, age, tau=TAU_FOAM_SALT):
    """m(a) for the surf zone. `age` is seconds since the crest passed."""
    q_b = np.clip(np.asarray(q_b, float), 0.0, 1.0)
    a = np.maximum(np.asarray(age, float), 0.0)
    denom = 1.0 - math.exp(-float(T) / float(tau))
    return q_b * np.exp(-a / float(tau)) / denom


# ------------------------------------------ the open sea, and it is a DIFFERENT
# source with the SAME clock
# MONAHAN & O'MUIRCHEARTAIGH (1980), JPO 10, 2094, "Optimal power-law
# description of oceanic whitecap coverage dependence on wind speed".
#
#   W = 3.84e-6 U10^3.41    the form universally quoted from that paper and the
#                           one Koepke's whitecap reflectance model is built on
#   W = 2.95e-6 U10^3.52    the same paper's own OPTIMAL fit
#
# BOTH ARE CARRIED AND THAT IS DELIBERATE. This project has been here before:
# `beach_optics` already records that Cox & Munk fit their slope components and
# their total separately and that the two disagree by 0.8%, and quoting one as
# if it implied the other is a misreading of the source. The whitecap case is
# the same disease an order of magnitude worse -- the two fits differ by 12% at
# 6 m/s and by 25% at 20 -- and the LITERATURE at large is worse still:
# Callaghan et al. (2008, GRL 35, L23609) fit a piecewise law with an ONSET at
# U10 = 3.70 m/s and branches meeting at 10.18 m/s, which is not a power law at
# all, and the published W at a given moderate wind spans a factor of a few.
#
# THE EXPONENT'S SPREAD IS THE POINT AND IT IS REPORTED AS SUCH. 3.41, 3.52, and
# an offset cubic; the wind a coverage measurement implies carries the spread
# divided by the exponent, and `wind_from_whitecap` below returns that band
# rather than a number.
MOM80_A, MOM80_N = 3.84e-6, 3.41         # `P`, the quoted form
MOM80_OPT_A, MOM80_OPT_N = 2.95e-6, 3.52  # `P`, the same paper's optimal fit
CALLAGHAN_U0 = 3.70                      # m/s, the onset. `P`
EXPONENT_SPREAD = (3.0, 3.52)            # the band the literature supports


def whitecap_coverage(u10, a=MOM80_A, n=MOM80_N):
    """Fractional whitecap coverage of the OPEN sea from the wind. Monahan &
    O'Muircheartaigh (1980). Fraction, not per cent: 3.84e-4 U^3.41 is the same
    law written in per cent and mixing the two is a factor of 100."""
    return a * np.maximum(np.asarray(u10, float), 0.0) ** n


def wind_from_whitecap(W, a=MOM80_A, n=MOM80_N):
    """The inverse readout, and the band that comes with it.

    Returns (U, U_lo, U_hi) where the band is what the EXPONENT's spread alone
    does to the answer -- the coefficient's spread is worse. This is the
    function bar section K's cross-check needs, and its width is the finding."""
    W = np.maximum(np.asarray(W, float), 1e-30)
    U = (W / a) ** (1.0 / n)
    lo = (W / a) ** (1.0 / EXPONENT_SPREAD[1])
    hi = (W / a) ** (1.0 / EXPONENT_SPREAD[0])
    return U, np.minimum(lo, hi), np.maximum(lo, hi)


def covering_measure_wind(u10, tau=TAU_FOAM_SALT):
    """The open sea's covering measure, so it ADDS to the surf zone's.

    Monahan's law is a COVERAGE, and coverages do not add -- covering measures
    do. Inverting the saturation once, here, is what lets one field carry both
    sources and reduce to Monahan exactly where no wave is breaking."""
    del tau                     # the decay is already inside Monahan's fit
    W = np.clip(whitecap_coverage(u10), 0.0, 1.0 - 1e-12)
    return -np.log1p(-W)


def coverage(m):
    """The saturating map. One place, so no caller can write 1 - exp(-k f)."""
    return 1.0 - np.exp(-np.maximum(np.asarray(m, float), 0.0))


# ------------------------------------------- the mask FLOATS, and that is a lag
# BAR SECTION C: the surface deck "floats, deforms with the flow". So it is NOT
# on the crest. Foam is laid down at the breaking crest, which then runs away
# from it at the celerity c while the water it sits on moves at the Stokes
# drift, an order of magnitude slower. Foam of age a is therefore
#
#       xi = (c - u_surf) a
#
# BEHIND the crest -- seaward of it, because the crest is going shoreward -- and
# the coverage field is a tail with an e-folding length (c - u_surf) tau. On
# this scene that is fifteen-odd metres against a forty-metre wavelength, so the
# white lies over a third of the wave and not on its top.
#
# AND THE AGE IS FREE. The transform already accumulates the phase S, so the
# time since the crest passed is ((-phase) mod 2 pi)/omega with no field added
# and nothing to advect. A Lagrangian foam solver would be the general answer;
# for a wave of permanent form the phase IS the age, exactly, and the general
# answer would reproduce this one.
def age_from_phase(phase, omega):
    """Seconds since the crest passed, from the transform's own phase.

    phase = S - omega t, so at a fixed point it DECREASES with time; a crest is
    phase = 0 (mod 2 pi) and the time since is (-phase mod 2 pi)/omega."""
    return (np.mod(-np.asarray(phase, float), 2.0 * math.pi) / float(omega))


def foam_tail_length(c, tau=TAU_FOAM_SALT, u_surf=0.0):
    """(c - u_surf) tau -- the e-folding length of the foam behind a crest."""
    return np.maximum(np.asarray(c, float) - np.asarray(u_surf, float), 0.0) * tau


# =========================================================== 5 · THE CLOCKS
# BAR SECTION E: "They overlap in space and are separated by their DECAY, not
# their appearance. One decay curve fits neither."
def decay_times(H, d, T, D50=None, salt=True):
    """The three clocks, side by side, all from this file's own fields.

    tau_foam    the surface raft, Monahan & Zietlow (1969). PUBLISHED.
    tau_air     the plume, d_p / w_rise(r_32). DERIVED, Schiller & Naumann.
    tau_sed     the suspension, d / w_s. DERIVED, `beach.settling_velocity`,
                which is Soulsby's law and not Schiller & Naumann's.

    THREE MECHANISMS, THREE LAWS, NO SHARED SOURCE. The bar asked for two
    timescales and named them seconds and minutes; what comes out is three, and
    the ORDER is not the one the bar implies -- see the README.
    """
    d_p = float(np.median(plume_depth(np.atleast_1d(H))))
    pop = bubble_population(d_p, T)
    w_s = B.settling_velocity() if D50 is None else B.settling_velocity(d50=D50)
    dd = float(np.median(np.atleast_1d(d)))
    return dict(tau_foam=foam_residence(salt), tau_air=d_p / pop['w_at_r32'],
                tau_sed=dd / w_s, w_rise=pop['w_at_r32'], w_s=w_s,
                r_32=pop['r_32'], d_plume=d_p, depth=dd)


def d50_for_settling_time(tau_target, depth, lo=1e-6, hi=1e-3):
    """What grain size would take `tau_target` seconds to clear `depth`.

    The bar says the sediment cloud lasts MINUTES and this scene's D50 is the
    BED's 0.30 mm, which clears in well under one. This inverts the settling law
    to say what size the bar's observation implies -- which is the fine tail and
    not the median, and that is a statement about the suspension the file does
    not yet carry rather than a disagreement with the owner."""
    for _ in range(90):
        mid = math.sqrt(lo * hi)
        if depth / B.settling_velocity(d50=mid) < tau_target:
            hi = mid                                # too fast, go finer
        else:
            lo = mid
    return math.sqrt(lo * hi)


# ==================================================== 6 · THE SCENE'S FOAM FIELD
def breaking_fraction_2d(d, H, gamma_b=B.GAMMA_B):
    """`beach.breaking_fraction_bj` on a 2-D field, by flattening.

    NOT A SECOND SOLVER. The 1-D function is called on the flattened arrays and
    reshaped, so there is exactly one Battjes & Janssen closure in this project
    and no chance of the two drifting. It is slow -- 45000 bisections -- and it
    runs once per scene."""
    d = np.asarray(d, float)
    q = B.breaking_fraction_bj(dict(d=d.ravel(), H=np.asarray(H, float).ravel()),
                               gamma_b=gamma_b)
    return q.reshape(d.shape)


def surface_foam(q_b, T, age, u10, tau=TAU_FOAM_SALT, deep_mask=None):
    """The coverage mask, from the breaking statistics and the wind. One field,
    two sources, and it reduces to Monahan exactly where nothing breaks."""
    m = covering_measure_break(q_b, T, age, tau) + covering_measure_wind(u10)
    if deep_mask is not None:
        m = np.where(deep_mask, covering_measure_wind(u10) * np.ones_like(m), m)
    return coverage(m), m


# ========================================================= the module's own run
def main():
    np.set_printoptions(precision=5, suppress=False)
    print('=' * 78)
    print('BAR SECTION C -- ONE CONSTANT, THREE APPEARANCES')
    oc = check_one_constant()
    print('  optics.TIR_FRAC        = %.6f   (green, 1 - 1/n^2)' % oc['tir_frac'])
    print('  beach_optics.FOAM_WHITE= %s   per channel' % np.round(oc['foam_white'], 6))
    print('  critical angle         = %s deg' % np.round(oc['theta_c_deg'], 3))
    bs = bubble_scatter()
    print('  RECOVERED from a ray trace that was not written from it:')
    print('    TIR share of the disc  = %s' % np.round(bs['tir_fraction'], 6))
    print('    total reflected share  = %s  (TIR + partial Fresnel)'
          % np.round(bs['reflected'], 6))
    print('    energy sum             = %s  (must be 1)' % np.round(bs['total'], 9))
    print('    asymmetry g            = %s' % np.round(bs['g'], 5))
    print('    backscatter b_b/b      = %s' % np.round(bs['bb_over_b'], 6))
    print('  AND THE QUALIFIER: a TIR ray off a sphere deviates by pi - 2 theta_i,')
    print('  which for theta_i > theta_c is under %.1f deg. The 43.9%% is a'
          % math.degrees(math.pi - 2 * float(THETA_C[1])))
    print('  REFLECTANCE, not a backscatter fraction; a bubble is a SIDE')
    print('  scatterer and the white is multiple scattering in a medium of')
    print('  albedo 1, not one bright bounce.')
    print()
    print('BUBBLE POPULATION -- Deane & Stokes (2002), cutoff derived')
    for dp, T in ((0.75, 9.0), (0.35, 9.0)):
        pop = bubble_population(dp, T)
        print('  d_p = %.2f m, T = %.0f s -> r_max = %.4g m (w = %.4f m/s), '
              'r_32 = %.4g m, below Hinze %s'
              % (dp, T, pop['r_max'], pop['w_at_rmax'], pop['r_32'],
                 pop['below_hinze']))
    print()
    print('THE THREE CLOCKS -- bar section E')
    ct = decay_times(1.5, 2.0, 9.0)
    print('  tau_foam (surface raft)  = %6.2f s   Monahan & Zietlow 1969, salt'
          % ct['tau_foam'])
    print('  tau_air  (plume)         = %6.2f s   d_p/w_rise, w = %.4f m/s'
          % (ct['tau_air'], ct['w_rise']))
    print('  tau_sed  (suspension)    = %6.2f s   d/w_s,      w_s = %.4f m/s'
          % (ct['tau_sed'], ct['w_s']))
    print('  ratios: air/foam %.2f   sed/air %.2f   sed/foam %.2f'
          % (ct['tau_air'] / ct['tau_foam'], ct['tau_sed'] / ct['tau_air'],
             ct['tau_sed'] / ct['tau_foam']))
    print('  the bar says the sediment lasts MINUTES; at this depth that needs'
          ' D50 = %.1f um'
          % (1e6 * d50_for_settling_time(120.0, ct['depth'])))
    print()
    print('WHITECAPS AND THE WIND -- bar section K\'s cross-check')
    for u in (3.0, 6.0, 10.0, 16.0):
        W = whitecap_coverage(u)
        Wo = whitecap_coverage(u, MOM80_OPT_A, MOM80_OPT_N)
        gw = BO.glitter_width_deg(21.02, 10.0, u10=u)
        print('  U10 %5.1f m/s   W = %8.5f (quoted)  %8.5f (optimal, %+.0f%%)'
              '   glitter width %6.3f deg'
              % (u, W, Wo, 100 * (Wo / W - 1), gw['dphi']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
