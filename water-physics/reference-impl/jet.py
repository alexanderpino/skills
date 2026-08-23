"""The free jet in air: one phenomenon along the Weber axis.

WHAT THIS FILE ADDS, AND WHY IT IS ONE FILE AND NOT FOUR. A waterfall, a
fountain, a fire hose and a water pistol are the SAME jet at different Weber
numbers. The waterfall section already derives the endpoint -- Rayleigh-Plateau
breakup, most-unstable mode near 4.51 diameters -- and never states the
parameter that orders them, so the four read as four subjects instead of four
points on a line.

THE COUNTER-INTUITIVE CONSEQUENCE, and it is the reason this axis is worth
drawing: a fire hose's momentum makes its stream LESS coherent, not more.
Faster jets break up sooner, because the aerodynamic forces that tear the
surface grow as U^2 while the surface tension holding it together does not.

REGIMES, after Lin & Reitz (1998), Annu. Rev. Fluid Mech. 30, 85-105 (`P`).
Ohnesorge (1936) drew the original `Oh`-vs-`Re` diagram; the boundaries used
here are Lin & Reitz's Weber-number statement of it, because the German original
was not opened and this project does not cite what it has not read.

  Rayleigh              We_g < 0.4      drops LARGER than the jet, spaced
                                        regularly; a water pistol's thread
  first wind-induced    0.4 < We_g < 13 aerodynamic help, drops ~ jet diameter
  second wind-induced   13 < We_g < 40  short waves strip the surface; drops
                                        much smaller than the jet
  atomization           We_g > 40       breakup begins AT the nozzle; a fog
                                        nozzle lives here on purpose

`We_g` is the AERODYNAMIC Weber number -- built on the AIR's density, because
the tearing is done by the air. Building it on the liquid's density is the
commonest error in reading this diagram and it moves the boundaries by ~830x.
"""
import numpy as np

# Fluid constants at 20 C. `P`, standard values; sigma matches the one
# `wake.py` declares so the two files cannot drift apart.
RHO_W = 998.2          # kg/m^3, liquid water
RHO_A = 1.204          # kg/m^3, air
MU_W = 1.002e-3        # Pa s, liquid water
SIGMA = 0.0728         # N/m, air/water surface tension -- wake.py::SIG
G = 9.80665

# Lin & Reitz's regime boundaries in the aerodynamic Weber number. `P`.
WE_RAYLEIGH = 0.4
WE_FIRST_WIND = 13.0
WE_SECOND_WIND = 40.3

# Rayleigh's most-unstable wavelength on an inviscid column, in DIAMETERS.
# `P`, Rayleigh (1878): the fastest-growing disturbance has lambda = 4.508 d,
# which sets both the drop spacing and, by volume conservation, the drop size.
RAYLEIGH_LAMBDA_OVER_D = 4.508


def weber_liquid(u, d, rho=RHO_W, sigma=SIGMA):
    """`We_l = rho_l U^2 d / sigma` -- inertia against surface tension."""
    return (float(rho) * np.asarray(u, float) ** 2
            * np.asarray(d, float) / float(sigma))


def weber_aero(u, d, rho_a=RHO_A, sigma=SIGMA):
    """`We_g = rho_air U^2 d / sigma` -- the one the regime diagram uses.

    ⚠️ THE DENSITY IS THE AIR'S. The jet is torn by the gas it moves through,
    so the relevant inertia is the gas's. Using the liquid density here is an
    830x error in the wrong direction and puts every jet in the atomization
    regime, which is why "everything atomises" is a common wrong reading.
    """
    return (float(rho_a) * np.asarray(u, float) ** 2
            * np.asarray(d, float) / float(sigma))


def ohnesorge(d, rho=RHO_W, mu=MU_W, sigma=SIGMA):
    """`Oh = mu / sqrt(rho sigma d)` -- viscosity against inertia and tension.

    Velocity does not appear. `Oh` is a property of the FLUID AND THE NOZZLE,
    not of how hard you push, which is exactly why the regime diagram is drawn
    with `Oh` on one axis and a velocity-carrying number on the other.
    """
    return float(mu) / np.sqrt(float(rho) * float(sigma) * np.asarray(d, float))


def reynolds(u, d, rho=RHO_W, mu=MU_W):
    return float(rho) * np.asarray(u, float) * np.asarray(d, float) / float(mu)


def oh_from_we_re(we_l, re):
    """`Oh = sqrt(We_l)/Re`, the identity that ties the three together.

    Checked in the suite rather than asserted, because it is the relation that
    says the diagram's two axes are not independent choices.
    """
    return np.sqrt(np.asarray(we_l, float)) / np.asarray(re, float)


def regime(u, d, rho_a=RHO_A, sigma=SIGMA):
    """Which of the four regimes a jet is in, by aerodynamic Weber number."""
    we = np.asarray(weber_aero(u, d, rho_a, sigma), float)
    out = np.empty(we.shape, dtype=object)
    out[...] = 'atomization'
    out[we < WE_SECOND_WIND] = 'second wind-induced'
    out[we < WE_FIRST_WIND] = 'first wind-induced'
    out[we < WE_RAYLEIGH] = 'Rayleigh'
    return out if out.shape else out.item()


def rayleigh_drop_diameter(d):
    """Drop size from a Rayleigh-regime jet, by volume conservation.

    One wavelength of column becomes one drop:
      `pi/4 d^2 * lambda = pi/6 D^3`  =>  `D = d * (3/2 * lambda/d)^(1/3)`
    With `lambda/d = 4.508` this gives **D = 1.89 d** -- the drops are nearly
    twice the jet's diameter, which is the visible signature of the regime and
    the thing a particle system sized to the nozzle gets wrong.
    """
    d = np.asarray(d, float)
    return d * (1.5 * RAYLEIGH_LAMBDA_OVER_D) ** (1.0 / 3.0)


def breakup_length_rayleigh(u, d, rho=RHO_W, sigma=SIGMA, c=None):
    """Intact length of a Rayleigh-regime jet: `L = C * sqrt(We_l) * d`.

    THE LENGTH GROWS WITH SPEED IN THIS REGIME AND SHRINKS IN THE NEXT, which
    is the whole shape of the curve and the reason a single "coherence" slider
    cannot represent it. In the Rayleigh regime the disturbance needs a fixed
    number of growth times, and a faster jet covers more distance in that time.
    Past the first wind-induced boundary aerodynamic stripping takes over and
    the trend reverses.

    `C` is an experimental constant of order 10; it is exposed rather than
    baked, and the suite checks the SCALING rather than the constant.
    """
    c = 10.0 if c is None else float(c)
    # ⚠️ REFUSED OUTSIDE ITS OWN REGIME. Evaluated on a fire hose this formula
    # returns ~6000 diameters of intact column, which is not merely inaccurate
    # -- it is backwards, because past the first wind-induced boundary the
    # length falls with speed instead of rising. A correlation that keeps
    # returning a number outside its range is how a wrong trend ships, so this
    # one returns NaN there and the caller has to notice.
    we_g = np.asarray(weber_aero(u, d), float)
    out = c * np.sqrt(weber_liquid(u, d, rho, sigma)) * np.asarray(d, float)
    return np.where(we_g < WE_FIRST_WIND, out, np.nan)


def exit_velocity(delta_p, rho=RHO_W, c_d=0.92):
    """`U0 = C_d sqrt(2 dP / rho)` -- Bernoulli through an orifice.

    Shared with the pool's return jet, deliberately: the nozzle does not know
    whether it discharges into air or water. `C_d ~ 0.92` is an eyeball value
    and is marked `?` wherever it is quoted.
    """
    return float(c_d) * np.sqrt(2.0 * np.asarray(delta_p, float) / float(rho))


def ballistic_range(u, theta_rad, h0=0.0, g=G):
    """Where an un-broken jet lands, ignoring drag -- the fountain's arc.

    The DRAG-FREE answer, and it is stated as the upper bound it is: a coherent
    column has a small area-to-mass ratio and tracks this closely, while the
    droplets it becomes do not, so the arc's tip falls short of this and its
    root does not. That divergence IS the visual signature of a fountain and it
    is why a single particle-system trajectory reads as a hose of pellets.
    """
    u = np.asarray(u, float)
    th = np.asarray(theta_rad, float)
    vx, vy = u * np.cos(th), u * np.sin(th)
    t = (vy + np.sqrt(np.maximum(vy * vy + 2.0 * float(g) * float(h0), 0.0))) / float(g)
    return vx * t


def stokes_number(d_drop, u, length_scale, rho=RHO_W, mu_a=1.81e-5):
    """How well a drop follows the air: `St = rho_d d^2 U / (18 mu_a L)`.

    `St >> 1` is ballistic and ignores the air; `St << 1` is carried by it and
    becomes mist. One number decides whether a spray is drawn as particles or
    as a participating medium, which is the same ladder the waterfall cascade
    already uses -- now with the boundary named instead of eyeballed.
    """
    return (float(rho) * np.asarray(d_drop, float) ** 2 * np.asarray(u, float)
            / (18.0 * float(mu_a) * np.asarray(length_scale, float)))
