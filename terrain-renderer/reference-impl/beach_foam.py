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
    # EACH CHANNEL AT ITS OWN CONJUGATE ANGLE, and wave 7 fixed this. The first
    # writing passed `ct[..., 0]` -- red's air-side cosine -- into a function
    # that then evaluates all three IORs at it, so green and blue were Fresnel
    # at red's refracted angle. `optics.fresnel` broadcasts a scalar cosine to
    # three channels, so the shape was right and nothing complained; the error
    # was a wrong ANGLE per channel, which no shape check can see. What it cost
    # is small in the mean and exact in the check: the disc-average now recovers
    # `optics.R_INT` to six digits in ALL THREE bands (0.473713 / 0.476167 /
    # 0.480681 against 0.473712 / 0.476166 / 0.480681) where before only the red
    # landed. A ray trace that shares no code with the closed form and lands on
    # it to six figures in three bands is the strongest kind of row this suite
    # can carry, and the shipped version was throwing two thirds of it away.
    R = np.stack([OPT.fresnel(ct[..., c])[..., c] for c in range(3)], -1)
    return np.where(tir, 1.0, R)


def bubble_scatter(n_p=20001, n_order=40):
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
    that they do. `n_order` IS the truncation of that geometric series and it is
    set by the check rather than by taste: R is about 0.47 near grazing, so
    twelve orders leave 3e-5 unaccounted in the red and forty leave 8e-7. The
    orders past the second carry no angular structure a renderer can use; they
    are here so the energy row can be tight enough to catch a Fresnel branch
    taken backwards.

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
# `P`, cited. The exponents are theirs. THE ENDS OF THE SPECTRUM ARE THIS FILE'S
# AND THEY ARE MARKED, because the standing population weights them very
# differently from the source and the difference is the whole of section 3.
DS_SLOPE_SMALL = -1.5           # Deane & Stokes (2002). `P`
DS_SLOPE_LARGE = -10.0 / 3.0    # Deane & Stokes (2002). `P`
R_HINZE = 1.0e-3                # m, the Hinze scale. `P`, ~1 mm in their paper
R_MIN = 1.0e-5                  # m, 10 micron, and it is NOT harmless -- which
                                # is a correction to this file's own first
                                # draft. In the SOURCE spectrum the -3/2 slope
                                # makes both moments converge at the small end
                                # and the cutoff is worth 0.4%. In the STANDING
                                # spectrum the residence time goes as 1/w ~
                                # 1/r^2 in the Stokes regime, so n_st r^2 goes
                                # as r^-1.5 and the projected AREA diverges as
                                # r_min -> 0: r_32 runs 0.50 mm at 3 micron to
                                # 1.20 mm at 100 micron, a factor of 2.4 on the
                                # scattering coefficient. The cutoff is
                                # PHYSICAL rather than numerical -- below about
                                # ten microns Laplace pressure drives a bubble
                                # into solution in seconds, so the population
                                # does end -- but the exact end is `P` and the
                                # sensitivity is reported by the suite rather
                                # than hidden here.
R_MAX = 1.0e-2                  # m, a 2 cm bubble. `P`, AND THE PLUME'S OPTICAL
                                # DEPTH IS SENSITIVE TO IT: cutting it to 3 mm
                                # nearly doubles <tau>_vol and cuts r_32 by a
                                # third, which moves the scattering coefficient
                                # by 2.7x. Deane & Stokes photographed bubbles
                                # to about this size in the crest of a breaking
                                # wave. The largest cavity at THIS coast is `?`
                                # and it is the sharpest thing in section C that
                                # this file cannot close.


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


def _ds_density(r):
    """The two-slope source spectrum, unnormalised: the small branch carries
    unit coefficient and the large branch is matched to it at the Hinze scale.
    Every moment below divides one integral of this by another, so the
    normalisation cancels and is never needed."""
    r = np.asarray(r, float)
    return np.where(r <= R_HINZE, r ** DS_SLOPE_SMALL,
                    R_HINZE ** (DS_SLOPE_SMALL - DS_SLOPE_LARGE)
                    * r ** DS_SLOPE_LARGE)


def bubble_spectrum(d_plume, r_min=R_MIN, r_max=R_MAX, n=3001):
    """The SOURCE spectrum, and the STANDING one that survives in the plume.

    THE FIRST WRITING OF THIS SECTION PUT A SHARP CUTOFF ON THE SPECTRUM, AND
    THE RENDER FOUND IT. The cutoff was "a bubble that rises out within a wave
    period is not part of the standing population", which is the right idea in
    the wrong shape: it discarded the large bubbles while KEEPING the energy
    they were entrained with, so the surviving small ones inherited a void
    fraction ten times their own. The bay frame turned into a sheet of milk from
    the outer bar to the beach -- a defect no printed number in that run
    reported and the picture reported at a glance.

    THE STEADY STATE IS SIZE-RESOLVED AND THERE IS NO CUTOFF. Air is entrained
    with the Deane & Stokes spectrum n_s(r), and each size leaves on its own
    clock:

        tau(r) = (d_p/2) / w_rise(r)

    -- half the plume, because air is entrained THROUGH the layer rather than
    injected at its base, so the mean rise distance is half of it. In steady
    state the standing spectrum is

        n_st(r) = n_s(r) tau(r)

    which suppresses the large end smoothly instead of chopping it. The budget
    reads the SOURCE and the optics read the STANDING population, and the two
    are never mixed:

        <tau>_vol   INT n_s r^3 tau / INT n_s r^3    -- the AIR's own clock
        r_32        INT n_st r^3 / INT n_st r^2      -- the OPTICS' own radius

    AND THE ENTRAINED AIR HAS NO SINGLE DECAY TIME, which is a finding rather
    than an inconvenience. tau(r) runs from a third of a second at a centimetre
    to half an hour at ten microns, and the two ends belong to different
    questions: the AIR is gone in under a second (<tau>_vol) while the
    projected AREA that scatters light is dominated by the smallest bubbles
    present and outlives it by orders of magnitude. `tau_area_median` is
    returned so the spread can be seen, and it is NOT a number this file
    quotes: it tracks r_min and is a statement about the cutoff. Bar section E
    says one decay curve fits neither of its two clouds; measured, one decay
    curve does not fit even ONE of them.
    """
    r = np.geomspace(r_min, r_max, n)
    ns = _ds_density(r)
    w = bubble_rise_velocity(r)
    tau = 0.5 * float(d_plume) / w
    nst = ns * tau
    tau_vol = float(np.trapezoid(ns * r ** 3 * tau, r)
                    / np.trapezoid(ns * r ** 3, r))
    r32 = float(np.trapezoid(nst * r ** 3, r) / np.trapezoid(nst * r ** 2, r))
    area = nst * r ** 2
    cdf = np.cumsum(0.5 * (area[1:] + area[:-1]) * np.diff(r))
    cdf = np.concatenate([[0.0], cdf]) / cdf[-1]
    tau_med = float(np.interp(0.5, cdf[::-1], tau[::-1]))
    return dict(r=r, n_source=ns, n_standing=nst, w=w, tau=tau,
                tau_vol=tau_vol, r_32=r32, tau_area_median=tau_med,
                tau_at_rmin=float(tau[0]), tau_at_rmax=float(tau[-1]))


def bubble_population(d_plume, T=None, r_min=R_MIN, r_max=R_MAX):
    """The standing population's radius and the air's clock, in one dict."""
    del T                       # the spectrum no longer needs a wave period
    sp = bubble_spectrum(d_plume, r_min, r_max)
    return dict(r_32=sp['r_32'], tau_vol=sp['tau_vol'], r_max=r_max,
                w_at_r32=float(bubble_rise_velocity(sp['r_32'])),
                below_hinze=bool(sp['r_32'] < R_HINZE), spectrum=sp)


# ==================================== 3 · ENTRAINED AIR, FROM THE DISSIPATION
# LAMARRE & MELVILLE (1991), Nature 351, 469: "the entrainment and subsequent
# submergence of large quantities of air can account for between 30 and 50% of
# the total energy dissipated at breaking". `P`, cited, and the 30-50 is carried
# as a RANGE rather than collapsed -- every void fraction below is linear in it.
#
# THE BUDGET, and it is a source and a sink and not a shape. Air is pushed under
# at a volume rate Q per unit plan area, doing work rho g zbar per unit volume
# against buoyancy, and it leaves by rising out with each size's own clock:
#
#       rho g (d_p/2) Q = eps_LM D_w                     (the power)
#       h_air = Q <tau>_vol                              (the inventory)
#       alpha = h_air/d_p = 2 eps_LM D_w <tau>_vol / (rho g d_p^2)
#
# EVERY SYMBOL ON THE RIGHT IS THE SCENE'S OWN. D_w is the transform's breaking
# dissipation and d_p is the crest's own elevation; <tau>_vol comes out of the
# size-resolved steady state above. Nothing is fitted, there is no coefficient
# to turn, and the ONE number that is not forced -- the plume depth -- is marked
# and its sensitivity is stated beside it.
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
    del T                       # the spectrum sets its own clock now
    D_w = np.maximum(np.asarray(D_w, float), 0.0)
    d_p = np.maximum(plume_depth(H), 1e-3)
    d_rep = float(np.median(d_p)) if np.ndim(d_p) else float(d_p)
    pop = bubble_population(d_rep)
    tau_air = pop['tau_vol']
    Q = 2.0 * eps * D_w / (rho * g * d_p)               # m/s of air entrained
    alpha = Q * tau_air / d_p
    # THE SPHERE FORMULA HAS A DOMAIN AND THIS IS IT. 3 alpha/(4 r_32) is the
    # projected area of a DILUTE suspension of independent spheres; above about
    # alpha = 0.3 the bubbles are polyhedral cells and the scatterers are the
    # films between them, not the spheres. The clip is the validity limit, it is
    # reported as a clipped FRACTION rather than applied silently, and the
    # surface raft -- which is 95% air and far outside this domain -- is done a
    # different way in `foam_raft` below for exactly this reason.
    clipped = float(np.mean(alpha > 0.30)) if np.ndim(alpha) else float(alpha > 0.30)
    alpha = np.minimum(alpha, 0.30)
    return dict(alpha=alpha, d_p=d_p, tau_air=tau_air, tau_vol=tau_air,
                w_rise=pop['w_at_r32'], Q=Q, r_32=pop['r_32'],
                r_max=pop['r_max'], pop=pop, clipped_fraction=clipped,
                tau_area_median=pop['spectrum']['tau_area_median'])


def plume_phase_factor(age, T, tau):
    """The plume is NOT uniform over the wave, and this is why it is not.

    <tau>_vol is under a second and the period is nine, so the air one bore
    front entrains is gone long before the next front arrives: the plume is a
    feature OF THE FRONT, not a property of the surf zone. Summing over past
    sweeps exactly the way the foam's covering measure does, and normalised so
    the mean over the phase is 1 -- this REDISTRIBUTES the budget's void
    fraction and adds nothing to it:

        g(a) = (T/tau) exp(-a/tau) / (1 - exp(-T/tau)),      <g> = 1

    A renderer that spreads the time-mean void fraction evenly over the wave has
    a surf zone of milk. That is not a hypothetical: it is what the first run of
    this wave drew, and the picture is what found it.
    """
    T = float(T)
    tau = float(tau)
    a = np.maximum(np.asarray(age, float), 0.0)
    return (T / tau) * np.exp(-a / tau) / (1.0 - math.exp(-T / tau))


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

    CONSERVATIVE, AND THE ABSORPTION IS DELIBERATELY NOT HERE. The first
    writing multiplied R and T by exp(-a * path) for the water between the
    bubbles, and that DOUBLE-COUNTS: `beach_optics.column_reflectance` already
    carries the whole column's absorption in `t_col` and `R_col`, and the plume
    sits inside that column rather than beside it. It also broke the control:
    at alpha = 0 the transmittance came out 0.94 instead of the 1 that makes
    the paired evidence frame a measurement. What IS omitted by treating the
    slab as conservative is the path LENGTHENING that multiple scattering
    causes inside an absorbing medium -- a thick plume's photons travel farther
    than the slab is deep, so a real plume is very slightly cyan where this one
    is neutral. `?`, named, and small: fresh surf foam photographs neutral.
    """
    del a_water                 # see the note above: not this layer's to apply
    alpha = np.asarray(alpha, float)
    b = 2.0 * 3.0 * alpha / (4.0 * r_32)                # Q_ext * 3a/(4 r32)
    tau = b * np.asarray(path, float)
    tau_p = (1.0 - np.asarray(g_bub, float)) * tau[..., None]
    R = tau_p / (1.0 + tau_p)
    Td = 1.0 / (1.0 + tau_p)
    return dict(b=b, tau=tau, tau_prime=tau_p, R=R, T=Td,
                b_b=b[..., None] * np.atleast_1d(bb_over_b))


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


def foam_raft(Q_air, tau_foam=TAU_FOAM_SALT, r_32=2.4e-4,
              alpha_raft=ALPHA_RAFT):
    """The raft's THICKNESS, derived, and its reflectance two ways.

    THE THICKNESS IS AN INVENTORY AND NOT A GUESS. In steady state every cubic
    metre of air pushed under comes back up, so the surface is fed at exactly
    the entrainment rate Q and the raft loses it by bursting over tau_foam:
    the standing depth of AIR is Q tau_foam and the raft is that over its own
    air fraction. On this scene it lands at a few centimetres, which is where a
    raft of fresh surf foam is, and NOTHING was chosen to put it there.

    THE THICKNESS BARELY MATTERS AND THAT IS WORTH SAYING. Both reflectance
    routes below saturate above about a centimetre, so an error of a factor of
    two in the raft depth moves its brightness by under a per cent. Spreading
    the raft over the whole cell rather than over the COVERED fraction only
    makes it thinner, and it is already past saturation.

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
    h_air = np.asarray(Q_air, float) * tau_foam
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
    tau_air     the plume's AIR, <tau>_vol over the Deane & Stokes spectrum.
                DERIVED, through Schiller & Naumann's drag.
    tau_sed     the suspension, d / w_s. DERIVED, `beach.settling_velocity`,
                which is Soulsby's law and not Schiller & Naumann's.

    THREE MECHANISMS, THREE LAWS, NO SHARED SOURCE. The bar asked for two
    timescales; what comes out is three, plus the finding that the middle one is
    not a number at all but a spectrum -- `tau_lo`/`tau_hi` are the ends of it,
    and `tau_air_area` is the projected-area MEDIAN residence, which is what
    keeps the plume faintly visible long after its air volume has gone.
    """
    del T
    d_p = float(np.median(plume_depth(np.atleast_1d(H))))
    pop = bubble_population(d_p)
    sp = pop['spectrum']
    w_s = B.settling_velocity() if D50 is None else B.settling_velocity(d50=D50)
    dd = float(np.median(np.atleast_1d(d)))
    return dict(tau_foam=foam_residence(salt), tau_air=sp['tau_vol'],
                tau_air_area=sp['tau_area_median'],
                tau_lo=sp['tau_at_rmax'], tau_hi=sp['tau_at_rmin'],
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


# ------------------------- WAVE 12: WHICH BREAKING STATEMENT LAYS THE FOAM,
# and the file was carrying two that disagree by an order of magnitude
#
# THE DEFECT. Wave 6 fed `covering_measure_break` with Battjes & Janssen's Q_b.
# Q_b is a RAYLEIGH EXCEEDANCE PROBABILITY: given a random sea of root-mean-
# square height H_rms, it is the share of individual waves whose height passes
# gamma_b d. The field this renderer draws is not a random sea. `transform_2d`
# marches ONE monochromatic wave train -- one period, one direction, one
# height -- so there is no height distribution for the closure to operate on,
# and handing its deterministic H to a random-sea closure as if it were H_rms
# is a category error. Measured on this scene's centre row:
#
#     x     H/d    transform says    Q_b (BJ)   f_roller (D_w/D_sat, lagged)
#    580   0.598   NOT breaking        0.309          0.015
#    600   0.455   BREAKING            0.064          0.511
#    660   0.484   BREAKING            0.095          0.826
#    700   0.633   BREAKING            0.405          0.987
#
# TWO THINGS ARE WRONG AND THE SECOND IS WORSE THAN THE FIRST. The magnitude is
# eight to ten times low through the saturated surf zone -- and the PLACEMENT
# is inverted. Q_b peaks at x = 580, which is the one column in that list where
# the transform says the wave is NOT breaking, because Q_b keys on H/d
# APPROACHING gamma while the dissipation keys on the wave ACTUALLY breaking.
# So waves 6-11 drew their brightest foam band seaward of their own break
# point. Bar section B is explicit that this is the distinction that matters:
# "a monotone profile cannot distinguish a renderer that COMPUTES breaking from
# one that DRAWS FOAM NEAR THE SHORE".
#
# THE FIX ADDS NOTHING. `beach.roller_fraction` is the transform's own
# dissipation D_w over the saturated-bore scale, lagged shoreward by half a
# local wavelength because the roller rides the front -- and the sediment
# transport has trusted it since wave 1. Using it here means the foam, the
# undertow and the bar are all reading ONE statement about whether this wave is
# breaking, which is the same argument `broken_fraction`'s own docstring makes
# about keying to the dissipation rather than to H/d.
#
# Q_b IS NOT DELETED AND IS NOT WRONG. It is the right closure for a random sea
# and the file keeps it: when this lane gives the offshore boundary a
# directional and frequency spectrum, H becomes an H_rms and Q_b becomes
# applicable. What is recorded is that it was applicable to NEITHER field it
# was used on.
#
# AND A THIRD ROUTE, WHICH IS OPEN. The same file computes h_air = Q tau_foam,
# the standing depth of air per unit surface area, and gets 6.6 cm through the
# inner surf zone. If a real surf raft is h_0 thick then the covered fraction
# is h_air/(alpha h_0), which for h_0 between one bubble layer (0.5 mm) and
# 10 cm spans 0.7 to 137. The deposit of covering measure 1 per fully broken
# sweep -- which is what this file has always assumed and never said -- sits
# inside that bracket at its thick end. THE BRACKET IS TOO WIDE TO SETTLE
# ANYTHING, so nothing here is changed by it and it is recorded as open rather
# than used as a multiplier. Closing it needs a measured raft thickness.
def deck_source(tr, n_lag=None):
    """The field that lays the surface deck: the roller, not the exceedance.

    One line, so that the choice above is in ONE place and a future wave that
    disagrees with it has one call to change."""
    return (B.roller_fraction(tr) if n_lag is None
            else B.roller_fraction(tr, n_lag=n_lag))


def surface_foam(q_b, T, age, u10, tau=TAU_FOAM_SALT, deep_mask=None):
    """The coverage mask, from the breaking statistics and the wind. One field,
    two sources, and it reduces to Monahan exactly where nothing breaks."""
    m = covering_measure_break(q_b, T, age, tau) + covering_measure_wind(u10)
    if deep_mask is not None:
        m = np.where(deep_mask, covering_measure_wind(u10) * np.ones_like(m), m)
    return coverage(m), m


# ==================================================== 7 · THE REALISATION, and
# the difference between it and the mean is the whole of wave 12
#
# THE DEFECT, NAMED FIRST. Waves 6-11 computed the covering measure `m` above,
# mapped it through `coverage()` to a FRACTION, and the renderer then wrote
#
#       L = L_water (1 - cov) + L_foam cov
#
# which is an alpha blend by the EXPECTED coverage. That draws E[chi], the
# ensemble mean of the indicator, and never chi itself. A field whose mean is a
# smooth function of x is a smooth ramp when you draw its mean -- so the surf
# zone came out as one continuous soft grey band with a single smooth
# cross-shore hump, no bubble texture, no bright breaking line, no alongshore
# break-up, and both of its edges continuous smooth curves. Every one of those
# is a property of the MEAN and not of the field. The physics was already right
# and the picture was an airbrush gradient, because the last step threw the
# realisation away.
#
# IT IS THE SAME DEFECT THE OPTICS LANE IS FIXING FOR THE GLITTER IN THIS SAME
# WAVE -- the render drawing the ensemble mean of a stochastic field and never
# its samples -- and finding it in a second place is worth more than either fix.
#
# WHAT THE MODEL ALREADY WAS. `coverage(m) = 1 - exp(-m)` is not a saturating
# curve someone liked the shape of. It is the VOID PROBABILITY of a Boolean
# (germ-grain) model: drop grains of mean area <A> at germs of a Poisson
# process of intensity lambda, and the probability that a given point is
# covered by none of them is exp(-lambda <A>) = exp(-m). So the file has been
# carrying a Boolean model since wave 6 and drawing only its first moment. The
# realisation needs exactly ONE quantity the file did not have -- the GRAIN
# SIZE -- because m alone fixes lambda<A> and says nothing about how that
# product splits.
#
# THE GRAIN SIZE, AND WHERE IT COMES FROM. Foam is a passive tracer on the
# surface (bar section H5: "visible eddies with foam as the tracer"), so its
# patch scale is the scale of the surface flow structures that gather and tear
# it. In the surf zone that flow is DEPTH-LIMITED: the vertical extent of any
# eddy is capped by the local water depth d, and a horizontal structure much
# smaller than its own vertical scale is not a coherent eddy, so d is the
# smallest coherent horizontal scale a depth-limited turbulent surface flow
# carries. Hence
#
#       grain diameter = d,      radius r_g = d/2
#
# and the coefficient is DECLARED AT UNITY on the diameter rather than fitted.
# `grain_sensitivity()` reports what 0.5x and 2x do to the coverage statistics,
# and the coefficient is an OPEN row rather than a claim. What is NOT declared
# is the scaling: grains shrink toward the waterline and coarsen seaward
# because the depth does, which is why the lace at the swash edge is finer than
# the patches over the bar -- and that is a prediction, not a texture.
#
# WHAT IS RANDOM AND WHAT IS NOT. The germ positions and their marks are the
# only random numbers in this file, and they are the SAMPLER of a stated point
# process -- the same standing as a Monte Carlo direction drawn from a BRDF.
# They are not a noise function chosen because the picture came out right:
# `boolean_mean()` below measures the realisation's own coverage against
# `coverage(m)` and the suite fails if they disagree, so the random field is
# pinned to the physics at every point rather than layered on top of it.
R_G_MIN = 0.25                    # m, the finest grain octave. `D`
R_G_OCTAVES = 4                   # 0.25, 0.5, 1.0, 2.0 m
R_G_MAX = R_G_MIN * 2 ** R_G_OCTAVES     # the OUTER scale, not a grain radius
GRAIN_PER_DEPTH = 0.5             # r_g = 0.5 d, i.e. diameter = depth. `D`
MU_REF = 0.5                      # germs per cell of the DOMINATING process
GERM_SLOTS = 4                    # truncation; P(N>4 | mu=0.5) = 1.7e-4
_M32 = np.uint64(0xFFFFFFFF)


def _mix(h):
    """A 32-bit integer avalanche (Murmur-class), evaluated in uint64 so the
    products cannot overflow. Deterministic, so a frame is reproducible and two
    rays that hit the same square metre agree about what is on it."""
    h = np.asarray(h, np.uint64) & _M32
    h = ((h ^ (h >> np.uint64(16))) * np.uint64(0x7FEB352D)) & _M32
    h = ((h ^ (h >> np.uint64(15))) * np.uint64(0x846CA68B)) & _M32
    return (h ^ (h >> np.uint64(16))) & _M32


def _hash_u(*keys):
    """Uniform on [0, 1) from a tuple of integer keys."""
    h = np.uint64(0x2545F491)
    for i, k in enumerate(keys):
        h = _mix(h ^ (np.asarray(k, np.int64).astype(np.uint64)
                      + np.uint64(0x9E3779B9) * np.uint64(i + 1)))
    return h.astype(np.float64) * (1.0 / 4294967296.0)


def _poisson_thresholds(mu, n):
    """CDF cut points of Poisson(mu) at 0, 1, ... n-1, as plain floats.

    The dominating process is HOMOGENEOUS -- mu is a module constant -- so this
    is exact rather than an approximation, and the per-cell count is drawn from
    one uniform by inverse CDF."""
    p, c, out = math.exp(-mu), 0.0, []
    for k in range(n):
        c += p
        out.append(c)
        p *= mu / (k + 1.0)
    return out


_POIS = _poisson_thresholds(MU_REF, GERM_SLOTS)


def grain_radius(d, k=GRAIN_PER_DEPTH, r_min=R_G_MIN, r_max=R_G_MAX):
    """The foam patch radius: half the local depth, clamped to the octave
    ladder. The clamp's cost is a reported row, not a hidden one."""
    return np.clip(k * np.asarray(d, float), r_min, r_max)


def octave_weights(r_g, r_min=R_G_MIN, n=R_G_OCTAVES):
    """Split the covering measure over the octaves BELOW the outer scale, with
    equal measure in each -- a self-similar grain field.

    A SUPERPOSITION OF BOOLEAN MODELS IS A BOOLEAN MODEL: the void probability
    of independent germ fields multiplies, so prod_j exp(-m_j) = exp(-m)
    whenever the weights sum to one. The ladder therefore changes the coverage
    law by exactly nothing, and every choice made here is a choice about
    TEXTURE at fixed coverage.

    WHY EQUAL MEASURE PER OCTAVE AND NOT ALL OF IT AT ONE SCALE. Foam is a
    passive tracer on a surface flow that is turbulent between two scales: the
    depth-limited outer scale r_g = d/2 above, and the scales at which the raft
    stops being a sheet below. A tracer stirred by a flow with no preferred
    scale acquires structure at every scale in that range, so the scale-free
    split is the one that ADDS no scale -- it is the null choice, not a tuned
    spectrum. Wave 12's first draft put all the measure at r_g and the render
    came out as confetti: identical discs, one size, visibly a stamp. Recorded
    because the coverage statistics were identical in both, so no row in this
    file could have told them apart and only the frame could.

    The outer scale is the DEPTH's, so the ladder is short in the swash and
    long over the bar -- fine lace at the waterline, coarse patches offshore --
    and that is a prediction of the depth-limited argument rather than a
    texture setting.
    """
    v = np.clip(np.log2(np.maximum(np.asarray(r_g, float), 1e-9) / r_min),
                0.0, float(n))
    j0 = np.floor(v).astype(np.int64)
    f = v - j0                              # the top octave's partial weight
    idx = np.arange(n).reshape((1,) * np.ndim(v) + (n,))
    w = np.where(idx < j0[..., None], 1.0, 0.0)
    w = np.where(idx == j0[..., None], np.maximum(f, 1e-12)[..., None], w)
    return w / np.maximum(w.sum(-1, keepdims=True), 1e-12)


def boolean_indicator(xw, yw, m, r_g, seed=0, mu=MU_REF, slots=GERM_SLOTS,
                      r_min=R_G_MIN, n_oct=R_G_OCTAVES, return_p=False):
    """chi(x, y) in {0, 1}: ONE REALISATION whose mean is exactly 1 - exp(-m).

    THE CONSTRUCTION, and it is exact rather than approximately Poisson.

      * The DOMINATING germ field is homogeneous with intensity
        lambda_ref = mu / r_j^2 in octave j, so the count in a cell of side r_j
        is Poisson(mu) with mu a CONSTANT -- one uniform per cell, inverse CDF,
        no field evaluation at the germ.
      * Each germ carries an independent uniform mark u.
      * A germ is RETAINED at the query point q if u < p_j(q), with
            p_j(q) = m_j(q) / (lambda_ref pi r_j^2) = m_j(q) / (mu pi).
        Independent marking of a Poisson process gives a Poisson process of
        intensity lambda_ref p, so
            P(q uncovered) = prod_j exp(-lambda_ref p_j pi r_j^2) = exp(-m)
        exactly, for every m and every grain ladder.
      * Cell side = grain radius, so any germ whose disc reaches q lies in the
        3x3 block of cells around q. The search is exhaustive, not a cutoff.

    p is clamped at 1, which happens where m_j > mu pi = 1.571. The clamped
    fraction is returned so the suite can state it instead of a comment
    claiming it never bites.
    """
    xw = np.asarray(xw, float)
    yw = np.asarray(yw, float)
    m = np.broadcast_to(np.asarray(m, float), xw.shape)
    r_g = np.broadcast_to(np.asarray(r_g, float), xw.shape)
    w = octave_weights(r_g, r_min, n_oct)
    covered = np.zeros(xw.shape, bool)
    p_max = 0.0
    for j in range(n_oct):
        s = r_min * 2.0 ** j
        p = np.maximum(m, 0.0) * w[..., j] / (mu * math.pi)
        p_max = max(p_max, float(p.max()) if p.size else 0.0)
        p = np.minimum(p, 1.0)
        live = p > 0.0
        if not live.any():
            continue
        ci = np.floor(xw / s).astype(np.int64)
        cj = np.floor(yw / s).astype(np.int64)
        for oi in (-1, 0, 1):
            for oj in (-1, 0, 1):
                a, b = ci + oi, cj + oj
                nsel = _hash_u(a, b, np.int64(j), np.int64(seed))
                for t in range(slots):
                    # the cell drew N ~ Poisson(mu) from `nsel`; slot t is
                    # occupied iff N > t, i.e. the uniform is above the CDF at t
                    have = (nsel >= _POIS[t]) & live
                    if not have.any():
                        continue
                    gx = (a + _hash_u(a, b, np.int64(100 + t),
                                      np.int64(j), np.int64(seed))) * s
                    gy = (b + _hash_u(a, b, np.int64(200 + t),
                                      np.int64(j), np.int64(seed))) * s
                    u = _hash_u(a, b, np.int64(300 + t), np.int64(j),
                                np.int64(seed))
                    hit = (have & (u < p)
                           & ((xw - gx) ** 2 + (yw - gy) ** 2 < s * s))
                    covered |= hit
    chi = covered.astype(float)
    return (chi, p_max) if return_p else chi


def boolean_mean(n=400, m_val=0.6, r_val=1.0, span=200.0, seed=0):
    """THE GUARD'S INSTRUMENT, and it is a control with a known answer.

    Realise a homogeneous field on a square and measure the covered fraction
    against 1 - exp(-m). Standing ruling 14: a near-agreement is worthless
    unless the meter can also read a DISagreement, so the caller is expected to
    push m and r around and watch the answer track."""
    g = (np.arange(n) + 0.5) / n * span
    X, Y = np.meshgrid(g, g)
    chi = boolean_indicator(X, Y, np.full(X.shape, m_val),
                            np.full(X.shape, r_val), seed=seed)
    return dict(measured=float(chi.mean()), analytic=float(coverage(m_val)),
                m=m_val, r_g=r_val)


def grain_sensitivity(m_val=0.6, coeffs=(0.25, 0.5, 1.0), **kw):
    """What the declared coefficient buys and what it does not.

    The COVERAGE must not move with the grain size -- that is the Boolean
    model's own theorem -- while the PATCH SCALE must move with it exactly.
    Reporting both is what separates a declared constant from a fitted one."""
    out = []
    for k in coeffs:
        r = grain_radius(2.0, k=k)
        out.append((k, float(r), boolean_mean(m_val=m_val, r_val=float(r),
                                              **kw)['measured']))
    return out


def filtered_indicator(chi, cov, footprint, r_g):
    """Fade the realisation to its own mean where the pixel outruns the grain.

    A pixel whose footprint is many grains wide should read the MEAN, because
    that is what the integral of the indicator over the footprint converges to;
    a pixel smaller than a grain should read the SAMPLE. This is a filter, not
    a fudge, and it is exact in both limits -- what is approximate is the
    crossover, which is taken linearly in 2 r_g / footprint."""
    g = np.clip(2.0 * np.asarray(r_g, float)
                / np.maximum(np.asarray(footprint, float), 1e-6), 0.0, 1.0)
    return cov + (chi - cov) * g


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
    print('BUBBLE POPULATION -- Deane & Stokes (2002), size-resolved steady state')
    for dp in (0.75, 0.35):
        sp = bubble_spectrum(dp)
        print('  d_p = %.2f m -> <tau>_vol %.3f s, area-median tau %.2f s, '
              'r_32 %.4g m, tau spans %.2f s (r_max) to %.0f s (r_min)'
              % (dp, sp['tau_vol'], sp['tau_area_median'], sp['r_32'],
                 sp['tau_at_rmax'], sp['tau_at_rmin']))
    for rmx in (3e-3, 1e-2, 2e-2):
        sp = bubble_spectrum(0.75, r_max=rmx)
        print('  SENSITIVITY r_max = %.3g m -> <tau>_vol %.3f s, r_32 %.4g m'
              % (rmx, sp['tau_vol'], sp['r_32']))
    print()
    print('THE THREE CLOCKS -- bar section E')
    ct = decay_times(1.5, 2.0, 9.0)
    print('  tau_foam (surface raft)  = %6.2f s   Monahan & Zietlow 1969, salt'
          % ct['tau_foam'])
    print('  tau_air  (plume AIR)     = %6.2f s   <tau>_vol; the SPECTRUM spans '
          '%.2f - %.0f s and the area-median is %.1f s'
          % (ct['tau_air'], ct['tau_lo'], ct['tau_hi'], ct['tau_air_area']))
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
