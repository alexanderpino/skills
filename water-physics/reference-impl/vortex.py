"""Vortices: the standing one that dents the surface, and the shed one that beats.

THE SIXTH AXIS, AND THE ONE THE REGISTER HELD OPEN LONGEST. `12c` recorded
vortex structure as absent AND UNSOURCED -- the other five gaps carried a
verified reference and this one did not, so it was left open rather than given
an invented citation. It is closed here because two primary sources were found,
downloaded and READ, not summarised:

  `P` Andersen, A., Bohr, T., Stenum, B., Juul Rasmussen, J. & Lautrup, B.
      (2006), "The bathtub vortex in a rotating container", J. Fluid Mech.
      **556**, 121-146, doi:10.1017/S0022112006009463. The free-surface half:
      the cyclostrophic balance below is their equation (5.7), the curvature
      their (5.6), and the Ekman and Rossby numbers their table 1. Their
      short-form companion is Phys. Rev. Lett. **91**, 104502 (2003).
  `P` Jiang, H. & Cheng, L. (2017), "Strouhal-Reynolds number relationship for
      flow past a circular cylinder", J. Fluid Mech. **832**, 170-188. The shed
      half: the onset, the instability boundaries, the family of fitted forms,
      and the Re = 1000 anchor are read from their text and their table 3.

⚠️ WHAT IS ATTRIBUTED RATHER THAN READ. Roshko (1954, 1955), Fey et al. (1998),
Norberg (1994), Williamson (1996a) and Williamson & Brown (1998) are named
below because Jiang & Cheng name them. Their own papers were NOT opened here --
Annual Reviews and APS both refused the request -- so they are attributions,
exactly as `jet.py` marks Ohnesorge (1936). Every number in this file was read
in one of the two sources above.

THE TWO KINDS ARE NOT THE SAME PHENOMENON, and the axis is which frame they
live in. A drain vortex STANDS: the water moves through it and the funnel does
not. A shed vortex TRAVELS: it is released at a fixed rate and carried
downstream. The first is a surface SHAPE, the second is a CLOCK. A renderer
needs the shape from one and the frequency from the other, and this skill
supplied neither.
"""
import numpy as np

RHO_W = 998.2          # kg/m^3      -- jet.py::RHO_W
MU_W = 1.002e-3        # Pa s        -- jet.py::MU_W
SIGMA = 0.0728         # N/m         -- jet.py::SIGMA, wake.py::SIG
G = 9.80665
NU_W = MU_W / RHO_W    # m^2/s, kinematic viscosity -- DERIVED, never declared,
#                        so this file cannot drift from the two it shares.

# Jiang & Cheng (2017), read: vortex shedding emerges at Re = 47; the secondary
# wake instability is near Re ~ 180 and the shear-layer instability near
# Re ~ 1300; boundary-layer transition is near Re ~ 2e5. The twin-peaked
# transition from mode A with dislocations to mode B runs Re = 230-260.
RE_SHEDDING_ONSET = 47.0
RE_MODE_A = 180.0
RE_MODE_B = 260.0
RE_SHEAR_LAYER = 1300.0
RE_BL_TRANSITION = 2.0e5

# Williamson & Brown (1998)'s WAKE Strouhal number, as quoted by Jiang & Cheng:
# St* ~ 0.176, varying between 0.164 and 0.186, over Re from 55 to 1.4e5.
# ⚠️ ATTRIBUTION -- see the header. Carried as a band, not a point, because the
# source that was read reports it as one. AND NOTE IT IS `St* = f D'/U_s`,
# built on the WAKE WIDTH and the SEPARATING VELOCITY, not on the cylinder
# diameter and the free stream. It is not interchangeable with `St` below.
ST_WAKE_UNIVERSAL = 0.176
ST_WAKE_RANGE = (0.164, 0.186)

# The ordinary Strouhal number at Re = 1000, read off Jiang & Cheng's table 3,
# where their own DNS is compared against two experiments:
#     their 3D DNS, five meshes         0.2098 - 0.2125
#     Williamson & Brown (1998), exp.   0.212
#     Norberg (1994), exp.              0.210
# This is the anchor the fitted forms below deliberately lack: one Reynolds
# number at which a value was actually read, from three independent estimates
# agreeing to under 1 %.
RE_ANCHOR = 1000.0
ST_AT_RE_ANCHOR = 0.212
ST_AT_RE_ANCHOR_RANGE = (0.2098, 0.2125)


# --- the standing vortex: a surface shape ------------------------------------
def rankine_velocity(r, core_radius, circulation):
    """Azimuthal speed of a Rankine vortex: solid body inside, free outside.

        `v = Gamma r / (2 pi a^2)`   for `r <= a`   (forced core)
        `v = Gamma / (2 pi r)`       for `r >  a`   (free vortex)

    THE CORE IS NOT A DETAIL, IT IS WHAT MAKES THE ANSWER FINITE. A pure free
    vortex has `v -> infinity` at the axis and, through the balance below, a
    surface depression that diverges with it. Every real vortex has a core; a
    renderer that models only the `1/r` tail has a model with no bottom.
    """
    r = np.asarray(r, float)
    a = float(core_radius)
    g = float(circulation)
    return np.where(r <= a, g * r / (2.0 * np.pi * a * a),
                    g / (2.0 * np.pi * np.maximum(r, 1e-12)))


def circulation_from_core_rate(omega, core_radius):
    """`Gamma = 2 pi Omega a^2` -- the circulation of a core spinning at Omega."""
    return 2.0 * np.pi * float(omega) * float(core_radius) ** 2


def surface_slope(v, r, g=G):
    """The cyclostrophic balance, WITHOUT surface tension: `dh/dr = v^2/(g r)`.

    Andersen et al. (2006) equation (5.7) is

        `v^2 / r = g dh/dr - (alpha/rho) dkappa/dr`

    with `kappa` the surface curvature of their (5.6); dropping the curvature
    term leaves this. It is the whole link between the flow and the shape:
    THE SURFACE DENT IS AN INTEGRAL OF THE VELOCITY PROFILE, so a renderer that
    authors the dip and the swirl separately has two things that can disagree,
    and they will -- at which point neither is the physics.
    """
    r = np.asarray(r, float)
    return np.asarray(v, float) ** 2 / (float(g) * np.maximum(r, 1e-12))


def rankine_surface(r, core_radius, circulation, g=G):
    """Free-surface height of a Rankine vortex, relative to the far field.

    Integrating `dh/dr = v^2/(g r)` on each branch:

        `r >  a`:  `h = -Gamma^2 / (8 pi^2 g r^2)`               the 1/r^2 tail
        `r <= a`:  `h = -Gamma^2/(4 pi^2 g a^2) + Omega^2 r^2/(2 g)`

    both measured from the undisturbed level, and continuous at `r = a` by
    construction rather than by fitting.
    """
    r = np.asarray(r, float)
    a = float(core_radius)
    gam = float(circulation)
    k = gam * gam / (8.0 * np.pi ** 2 * float(g))
    # ⚠️ CLAMPED AT 1e-12 AND NOT AT 1e-300. `np.where` evaluates BOTH branches,
    # so the outer expression is computed at r = 0 even though the inner one is
    # selected there -- and 1e-300 squared underflows to exactly zero, which
    # makes the division a warning instead of a large number. The result was
    # right and the arithmetic was not, which is the quiet kind of wrong.
    outer = -k / np.maximum(r, 1e-12) ** 2
    omega = gam / (2.0 * np.pi * a * a)
    inner = -2.0 * k / (a * a) + omega * omega * r * r / (2.0 * float(g))
    return np.where(r <= a, inner, outer)


def rankine_depth(core_radius, circulation, g=G):
    """Total depth of the dip, axis to far field: `dh = Gamma^2/(4 pi^2 g a^2)`.

    Equivalently `Omega^2 a^2 / g`. THE HALVES ARE EQUAL AND THAT IS THE RESULT
    WORTH CARRYING: the free tail outside the core contributes
    `Omega^2 a^2/(2g)` and the solid-body core contributes exactly the same
    again. So a renderer that draws only the visible funnel has half the depth
    -- and, worse, has a surface that is flat where the real one is still
    sloping, because the outer half of the dent lies OUTSIDE anything that
    looks like a hole.
    """
    a = float(core_radius)
    gam = float(circulation)
    return gam * gam / (4.0 * np.pi ** 2 * float(g) * a * a)


def capillary_length(sigma=SIGMA, rho=RHO_W, g=G):
    """`l_c = sqrt(sigma / (rho g))` -- 2.73 mm for water.

    THE THRESHOLD THAT SAYS WHEN THE FORMULA ABOVE STOPS BEING ENOUGH. Andersen
    et al. found surface tension had to be included for a quantitative account
    of their experiment, and this is why: their dip narrows to a needle, and
    once the tip's radius of curvature approaches `l_c` the curvature term in
    (5.7) is no longer a correction. A bathtub vortex is millimetric at the tip
    and therefore lives right on this boundary; a river's eddy is metres across
    and does not.
    """
    return np.sqrt(float(sigma) / (float(rho) * float(g)))


def surface_tension_matters(core_radius, sigma=SIGMA, rho=RHO_W, g=G):
    """Whether the curvature term in (5.7) can be dropped at this scale."""
    return np.asarray(core_radius, float) < 5.0 * capillary_length(sigma, rho, g)


def ekman_number(omega, length, nu=NU_W):
    """`Ek = nu / (2 Omega L^2)` -- Andersen et al. table 1, read.

    Small `Ek` means the bottom boundary layer is thin against the container,
    which is the regime in which the Ekman layer sets the upwelling that feeds
    the vortex. Their experiment ran at `Ek ~ 1e-7`.
    """
    return float(nu) / (2.0 * np.asarray(omega, float)
                        * np.asarray(length, float) ** 2)


def ekman_layer_depth(omega, nu=NU_W):
    """`delta = sqrt(nu / Omega)` -- the thickness the Ekman balance sets.

    Carried because it is what makes a drain vortex a THREE-DIMENSIONAL object
    rather than a dent: Andersen et al. find the fast downflow confined to a
    narrow rotating "drainpipe" with slow UPWARD flow around it, generated by
    the Ekman layer at the bottom. The fluid that feeds the funnel arrives
    along the floor, not from the sides.
    """
    return np.sqrt(float(nu) / np.asarray(omega, float))


# --- the shed vortex: a clock ------------------------------------------------
def reynolds(u, d, nu=NU_W):
    """`Re = U D / nu` -- the number that says whether anything sheds at all."""
    return (np.asarray(u, float) * np.asarray(d, float)) / float(nu)


def sheds(u, d, nu=NU_W):
    """Below `Re = 47` the wake is a steady pair of attached eddies.

    ⚠️ THE STEADY REGIME IS NOT A SLOW VERSION OF THE OSCILLATING ONE. Below
    onset the two recirculating eddies sit behind the obstacle and do not
    detach; there is no frequency, and an animation that scales its shedding
    rate down with velocity draws a slow beat where the truth is no beat.
    """
    return reynolds(u, d, nu) > RE_SHEDDING_ONSET


def shedding_frequency(u, d, st=0.2, nu=NU_W):
    """`f = St U / D` -- how often a vortex leaves the obstacle, in Hz.

    THE NUMBER A RENDERER ACTUALLY WANTS, and the reason this file exists on
    the animation side. The wake behind a boulder is not noise: it has a
    period, that period follows from the flow speed and the boulder, and
    `St ~ 0.2` holds across most of the range a scene will contain -- read at
    `Re = 1000` as 0.210 to 0.212 by three independent estimates.

    ⚠️ REFUSED BELOW ONSET, and this function shipped without the guard until a
    worked example caught it: a 2 mm silt grain in a 2 cm/s current sits at
    `Re = 40`, where nothing sheds, and the bare formula cheerfully returned
    2 Hz. That is the same defect `jet.py::breakup_length_rayleigh` is guarded
    against -- a correlation that keeps returning a plausible number outside
    its range -- and it is worse here, because a frequency is something an
    animation will happily consume. Below `Re = 47` this returns NaN and the
    caller has to decide what a wake with no beat looks like.
    """
    f = float(st) * np.asarray(u, float) / np.asarray(d, float)
    return np.where(reynolds(u, d, nu) > RE_SHEDDING_ONSET, f, np.nan)


def strouhal_fit(re, a, b, exponent=1.0):
    """`St = A + B / Re^p` -- the published FAMILY, with no constants of its own.

    ⚠️ `a` AND `b` ARE REQUIRED, AND THAT IS THE POINT OF THIS FUNCTION. Jiang &
    Cheng list three forms in use --

        `St = A + B/Re`          Roshko (1954), Ponta & Aref (2004)     p = 1
        `St = A + B/Re^(1/2)`    Fey et al. (1998), Williamson & Brown
                                 (1998), Ponta (2006)                   p = 1/2
        `St = 1/(A + B/Re)`      Roushan & Wu (2005)

    -- and state plainly that all of them "were still derived ultimately
    through curve fitting of the actual St-Re relationship". THE PAPER THAT WAS
    READ GIVES THE FORM AND NOT THE COEFFICIENTS. This file shipped defaults of
    0.212/-4.5 and 0.2684/-1.0356 for one round; they were RECALLED rather than
    read, and the suite caught them by asserting a shape they do not have.
    Numbers that cannot be pointed at a source do not get to be defaults, so
    there are none: a caller supplying a fit is doing so knowingly.

    The exponent carries the only physical claim in the family. `p = 1/2` is
    the shear-layer thickness scaling (attributed to Williamson & Brown 1998);
    `p = 1` is not derived from anything.
    """
    return float(a) + float(b) / np.asarray(re, float) ** float(exponent)


def strouhal_plateau(re, a, b, exponent=1.0):
    """`St/A` -- the shape that survives not knowing the fitted constants.

    Whatever `A` and `B` are, a negative `B` makes `St` climb monotonically
    toward `A` without reaching it. That is the only statement about this
    family this skill is entitled to make, and it is what the suite checks.
    """
    return strouhal_fit(re, a, b, exponent) / float(a)


def wake_regime(re):
    """Which wake a Reynolds number produces. Boundaries read, not recalled."""
    re = float(re)
    if re < RE_SHEDDING_ONSET:
        return 'steady -- a fixed pair of eddies, no shedding and no frequency'
    if re < RE_MODE_A:
        return 'laminar shedding -- a clean two-dimensional Karman street'
    if re < RE_MODE_B:
        return 'wake transition -- mode A then mode B, St drops and twin-peaks'
    if re < RE_SHEAR_LAYER:
        return 'three-dimensional shedding -- the street persists, cores do not'
    if re < RE_BL_TRANSITION:
        return 'shear-layer instability -- turbulent wake, periodic street lives'
    return 'boundary-layer transition -- the drag crisis, shedding goes irregular'


def strouhal_is_universal(re):
    """Whether `St* ~ 0.176` is claimed over this `Re`, per Williamson & Brown.

    Returns the claim's own domain rather than an opinion: 55 to 1.4e5, as
    quoted by Jiang & Cheng. Outside it nothing is asserted -- an attribution
    is not a licence to extrapolate.
    """
    re = np.asarray(re, float)
    return (re >= 55.0) & (re <= 1.4e5)
