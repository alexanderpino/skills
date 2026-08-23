"""Water entry: the crown, the cavity, the pinch-off and the Worthington jet.

THE DEFECT THIS FILE IS FOR. A renderer emits one particle burst when something
touches the water. That draws the FIRST of four events and skips the three that
follow, and the ones it skips are the ones that read as water rather than as a
puff:

  1. CROWN      an ejecta sheet rises at the contact ring, thin and translucent
  2. CAVITY     the body drags an air cavity down behind it
  3. PINCH-OFF  hydrostatic pressure closes that cavity at a depth, splitting it
  4. WORTHINGTON JET   the collapse fires a narrow column UPWARD out of the
                surface -- often higher than the crown, and DELAYED from it

The delay is the tell, and it is why a single burst cannot be tuned into
looking right: the two bright events are separated in time by the cavity's
whole life, and no decay curve on one impulse produces a second impulse.

SOURCES. Truscott, T. T., Epps, B. P. & Belden, J. (2014), "Water Entry of
Projectiles", Annu. Rev. Fluid Mech. 46, 355-378 (`P`) -- the review this file
follows for the sequence and its scalings. Worthington, A. M. (1908), "A Study
of Splashes" (`P`) -- the origin, and still the clearest photographic account.

⚠️ WHAT IS DERIVED AND WHAT IS SCALING. The dimensionless groups and the
energy/volume arguments below are derived. The pinch-off constants are
SCALINGS with order-unity coefficients that the literature reports as fitted;
they are exposed as arguments and marked, never baked in as though closed form.
"""
import numpy as np

RHO_W = 998.2
SIGMA = 0.0728
G = 9.80665


def impact_velocity(drop_height, g=G):
    """`U = sqrt(2 g h)` -- the free-fall speed at contact."""
    return np.sqrt(2.0 * float(g) * np.asarray(drop_height, float))


def froude_impact(u, d, g=G):
    """`Fr = U^2 / (g d)` -- inertia against gravity, on the body's scale.

    THE GROUP THAT DECIDES WHETHER THERE IS A CAVITY AT ALL. The cavity is held
    open by the body's momentum and closed by hydrostatic pressure, so `Fr` is
    the ratio of the two. Low `Fr` gives a splash and no cavity; high `Fr` gives
    a deep cavity and a late pinch-off.
    """
    return (np.asarray(u, float) ** 2
            / (float(g) * np.asarray(d, float)))


def weber_impact(u, d, rho=RHO_W, sigma=SIGMA):
    """`We = rho U^2 d / sigma` -- whether the crown survives as a sheet.

    Surface tension is what holds the ejecta sheet together. At low `We` the
    crown is a coherent rim that falls back; at high `We` it disintegrates into
    the ring of secondary droplets a photograph of a milk-drop crown shows.
    """
    return (float(rho) * np.asarray(u, float) ** 2
            * np.asarray(d, float) / float(sigma))


def cavity_pinchoff_time(d, u, g=G, c=None):
    """When the cavity closes, in seconds after contact.

    `t_p = C * sqrt(d / g)` -- and the SHAPE is the finding. The pinch-off time
    scales on the GRAVITATIONAL time of the body's own size and is nearly
    independent of the impact speed: hitting the water harder makes the cavity
    DEEPER, not longer-lived. So a faster impact does not delay the second
    flash; it moves it further down and makes the jet that follows faster.

    `C` is order unity and fitted; it is an argument, and the suite checks the
    scaling in `d` and the insensitivity to `u`, never the constant.
    """
    c = 2.0 if c is None else float(c)
    del u                       # named to document that it does NOT enter
    return c * np.sqrt(np.asarray(d, float) / float(g))


def cavity_pinchoff_depth(d, u, g=G, c=None):
    """How deep the cavity is when it closes.

    `h_p = C * d * sqrt(Fr)`, so depth grows with impact speed while the timing
    does not. Together with the row above this is the whole kinematic skeleton
    a renderer needs: WHEN the second event happens, and WHERE it comes from.
    """
    c = 0.5 if c is None else float(c)
    return (c * np.asarray(d, float)
            * np.sqrt(np.asarray(froude_impact(u, d, g), float)))


def worthington_jet_speed(u, d, g=G, eta=0.15):
    """Upward jet speed out of the collapse, from an energy argument.

    THE JET IS FASTER THAN THE IMPACT AND THAT IS NOT A MISTAKE. The cavity's
    walls converge on a line, so a large area of slowly-moving water is focused
    into a small one -- the same singular focusing a collapsing bubble does.
    Taking a fraction `eta` of the cavity's potential energy and delivering it
    into a column of the pinch-off neck's area gives

        `U_jet ~ sqrt(2 eta g h_p) * (d / d_neck)`

    and with a neck an order of magnitude smaller than the body the result
    exceeds `U`. ⚠️ `eta` and the neck ratio are NOT derived here; this returns
    a scaling with its assumptions exposed, and the suite checks only that the
    jet exceeds the impact speed for a deep cavity -- which is the qualitative
    fact a renderer must not get backwards.
    """
    h_p = cavity_pinchoff_depth(d, u, g)
    d_neck = 0.1 * np.asarray(d, float)
    return (np.sqrt(2.0 * float(eta) * float(g) * h_p)
            * np.asarray(d, float) / d_neck)


def crown_radius(t, u, d, c=None):
    """Radius of the ejecta crown at time `t`, in the inertial phase.

    `r ~ C * sqrt(U d t)` -- the classic square-root spreading of an impact
    ring, before surface tension and gravity take it back. The exponent is the
    part worth having: a crown drawn with a LINEAR expansion looks wrong early
    and wrong late, and no keyframe fixes both ends.
    """
    c = 1.0 if c is None else float(c)
    return c * np.sqrt(np.asarray(u, float) * np.asarray(d, float)
                       * np.asarray(t, float))


def splash_regime(u, d, g=G, rho=RHO_W, sigma=SIGMA):
    """Which events a given impact actually produces.

    Returns the pair `(cavity, crown_breaks)` so a caller can decide which of
    the four events to author. A raindrop on a puddle has a crown and no
    cavity; a boulder has both; a slow log has neither and only a bulge.
    """
    fr = np.asarray(froude_impact(u, d, g), float)
    we = np.asarray(weber_impact(u, d, rho, sigma), float)
    # ⚠️ A FROUDE THRESHOLD ALONE IS NOT THE CRITERION, and this file shipped
    # that error until a suite row caught it. A raindrop has Fr ~ 40 -- high --
    # and leaves no persistent cavity, because at millimetre scale SURFACE
    # TENSION closes the cavity long before hydrostatic pressure would. Both
    # numbers have to clear: momentum against gravity AND momentum against
    # surface tension. The second is what separates a raindrop from a pebble.
    return (fr > 10.0) & (we > 100.0), we > 500.0
