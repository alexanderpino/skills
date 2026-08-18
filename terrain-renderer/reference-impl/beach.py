"""The beach at Aljezur: bathymetry, the wave transform, and the loop that
builds the bar.

    python3 beach.py            # runs the morphodynamic loop, prints diagnostics
    python3 beach_evidence.py   # the same loop, plus the evidence figures
    python3 validate_beach.py   # the suite: closed form / published / independent

SCOPE. Everything up to the point of breaking. The free surface here is still a
graph over the plane -- the plunging lip is not, and it is deliberately the last
problem in this project rather than the first (`gauntlet/sea/bar.md` F). No
optics, no foam, no spray, no turbidity, no rocks, no run-up rendering: the
sediment flux is computed and exposed because the turbidity work will consume it,
and nothing here renders it.

WHAT THIS FILE IS FOR. The claim it exists to support is that the sandbar is a
PRODUCT and not a drawing. Nothing in this file says "put a ridge at x = 380 m".
The bed starts as the Dean (1991) equilibrium ramp -- a single monotone curve with
one parameter -- and the bar appears because two sediment fluxes converge at the
breakpoint. Take the breaking model out and the bar does not form; that ablation
is a row in the suite, not a claim in a comment.

THE CHAPTER IS THE SOURCE, NOT MEMORY. The loop, the trap it warns about, the
equilibrium crest depth and the Dean far field come from the sibling skill
`terrain-architect/references/12-glacial-coastal.md`, sections "Wave base & the
submarine profile" and "Surf-zone morphodynamics -- bars, rips & the nearshore
circulation". Every number taken from there is cited to it at the line it is
used. Where this file needed something that chapter does not carry, it is either
derived here beside itself, cited to a paper that was actually read this wave, or
marked `?`.

CONVENTIONS, and they are the chapter's, because mixing them is how this goes
wrong quietly:

    h   BED ELEVATION, metres, negative below the still-water datum
    d   local water depth, d = waterSurface - h, positive
    x   cross-shore, metres, increasing SHOREWARD; x = 0 is the offshore boundary
    y   alongshore, metres
    H   wave height (crest to trough), metres
    theta   angle between the wave crest normal and +x, radians

`h` versus `d` is not pedantry: the chapter's own symbol table warns that its
glacial half already owns `H`, `A`, `C` and `n`, and this file keeps `H_w`-style
meanings by never letting a depth and an elevation share a name.
"""
import math

import numpy as np

# The shared physics. These two modules are the pool's and they are IMPORTED,
# never copied -- the standing ruling that the pool does not disappear. This
# scene uses `atmosphere.solar_position` for the frames' own sun (below) and
# `optics` for the water constants the evidence figures shade depth with. If a
# beach ever needs a special case inside either of them, something was wrong all
# along, and one scene could never have shown it.
import optics as OPT                                            # noqa: F401
import atmosphere as ATM                                        # noqa: F401

# --------------------------------------------------------------- the constants
#
# House rule for this file: every constant is derived beside itself, cited to
# something that was read, or marked `?`. A number with neither is a bug that has
# not been found yet -- this project has closed four of them.

G = 9.80665             # m/s^2, standard gravity (CGPM 1901 definition). Exact
                        # by definition, so it is not a measurement to source.
RHO_SW = 1025.0         # kg/m^3, seawater at ~15 C, 35 psu. The value only ever
                        # appears inside ratios that cancel it (E/(rho c d)) or
                        # in E itself, which is reported as a ratio to E_0; the
                        # bar's position does not move if this is 1000.

# THE BREAKER INDEX. Imported in MEANING from the two chapters that already share
# it, not restated: `terrain-architect/references/12-glacial-coastal.md` fixes the
# equilibrium bar crest at "depth d_bar ~ H_b/gamma with gamma ~ 0.78, THE SAME
# BREAKING INDEX THE RENDERER'S BREAK MASK USES", and
# `terrain-renderer/references/12-water-rendering.md` writes that mask as
# "H ~ 0.78*h (the McCowan-type criterion)". So there is one number with two
# jobs, and this file gives it one name with both jobs attached: the transform
# below breaks on it AND the bar-crest prediction is written from it. If the two
# ever disagree the disagreement is visible, because there is nothing to
# disagree with.
#
# Independently corroborated this wave, in a source that had no idea about
# either chapter: the REF/DIF 1 v3.0 manual (Kirby & Dalrymple, U. Delaware),
# section 2.3.5, uses "a breaking index relation (H > 0.78 h) to determine the
# onset of breaking".
GAMMA_B = 0.78

# The stable wave height ratio of the Dally, Dean & Dalrymple (1985) decay model:
# a broken wave stops breaking when H falls to GAMMA_STABLE*d. Cited: REF/DIF 1
# v3.0 manual section 2.3.5 -- "K and gamma are empirical constants, determined
# by Dally et al. to be equal to 0.017 and 0.4 respectively".
GAMMA_STABLE = 0.40

# The decay coefficient of the same model, and it is the one constant in the
# breaking model this file cannot cite cleanly, so it is marked.
#
# `?` -- THE LITERATURE VALUE DEPENDS ON WHICH EQUATION IT IS PAIRED WITH, which
# is the same trap family as the radiation-stress factor of two. REF/DIF's 0.017
# multiplies an AMPLITUDE decay written as w = K*C_g*[1-(gamma h/H)^2]/h; the
# flux form used here, d(F)/dx = -(K/d)*(F - F_stable), is usually quoted with
# K ~ 0.15. Those are not the same K and this wave could not obtain the 1985
# paper to settle the conversion, so K_DALLY is treated as a DECLARED TUNED
# coefficient (chapter 12 declares the loop's k coefficients tuned, L/F tier)
# and the suite carries a sensitivity sweep instead of a tolerance: the bar's
# crest DEPTH must stay within a few per cent of H_b/gamma across K in
# [0.05, 0.40], because the crest depth is set by where the wave breaks and not
# by how fast it decays afterwards. That sweep is the honest substitute for the
# citation, and it is a stronger statement than the citation would have been.
K_DALLY = 0.15

POROSITY = 0.40         # sand bed porosity, the (1 - p) in Exner. 0.36-0.43 for
                        # loose to dense sand is textbook; 0.40 is the middle and
                        # it scales the bed's RATE, never its shape -- the
                        # equilibrium the loop runs to is independent of it.
                        # `?` on the exact value; harmless by the argument above.

# ---- the scene's sediment
D50 = 0.30e-3           # m, medium sand. `?` -- NO GRAIN-SIZE SURVEY OF ALJEZUR
                        # WAS AVAILABLE. 0.3 mm is the middle of "medium sand"
                        # (Wentworth 0.25-0.5 mm) and is a scene declaration, not
                        # a measurement. Everything downstream of it (w_s, the
                        # beach state Omega) is therefore a declaration too and is
                        # reported as such.
RHO_S = 2650.0          # kg/m^3, quartz. Standard mineral density.
NU_W = 1.05e-6          # m^2/s, kinematic viscosity of seawater near 20 C.

# ---- the scene's bathymetry parameter
# The Dean (1991) equilibrium profile is d = A*y^(2/3) with y the distance from
# the shoreline: cited to 12-glacial-coastal, "the shoreface settles into a
# smooth concave-up curve -- depth proportional to distance^(2/3), the Dean
# (1991) equilibrium beach profile". A is the profile's ONE parameter.
#
# `?` on the value. A = 0.13 m^(1/3) puts 7.6 m of water 400 m offshore and
# gives a mean nearshore slope of about 1:80, which is an ordinary exposed sandy
# coast. The published route from grain size, A ~ 0.067*w_s^0.44 (Kriebel, Kraus
# & Larson 1991), could not be verified from a readable source this wave, so it
# is NOT used to set A; `beach.py`'s diagnostics print what it would have given
# as an INFO line and nothing depends on it.
DEAN_A = 0.13

# ---- the offshore sea state, which arrives from OUTSIDE
# The standing ruling: the wave field is stated in DEEP-WATER quantities at the
# boundary, so shoaling and refraction are outputs. Nothing downstream may reach
# back and change these.
#
# `?` on all three. Aljezur in August takes NW Atlantic swell; H_0 = 1.5 m,
# T = 9 s, 20 deg off shore-normal is an ordinary summer swell there. No buoy
# record was consulted and the bar's photographs are explicitly not admissible as
# calibration (standing ruling: "Do not calibrate against the photographs").
# These are a DECLARED sea state. The physics is not conditional on them: the
# storm case below is the same code with H_0 doubled, and the bar's response to
# that is a prediction of the chapter's, tested in the suite.
H0_SWELL = 1.5          # m, deep-water wave height
T_SWELL = 9.0           # s, peak period
THETA0_SWELL = math.radians(20.0)   # rad, deep-water angle off shore-normal
H0_STORM = 3.0          # m, the storm case -- chapter 12: "Storms (large H_b)
                        # push the bar seaward; calm swell walks it back".

# ---- the domain
X_LEN = 500.0           # m, cross-shore extent, offshore boundary to shoreline
DX = 1.0                # m, grid spacing. The bar this loop builds is ~12 m
                        # wide at half amplitude, so 1 m resolves it with a
                        # dozen cells; the suite carries a refinement row at
                        # 0.5 m and the crest moves by less than 2%.
D_MIN = 0.10            # m, the depth floor. Below this the transform is not
                        # asked for an answer: the swash zone is a different
                        # problem (a moving waterline over a wetting/drying bed)
                        # and it is out of this wave's scope.
DT_MORPH = 300.0        # s, the morphological time step. It is not a wave time
                        # step -- nothing here resolves a wave period; the
                        # transform is a steady solve on the current bed and dt
                        # only advances the BED. The suite refines it to 100 s
                        # and the bar's crest moves by under 2%.
N_STEPS = 6000          # -> 500 hours (21 days) of continuous 1.5 m swell. Long,
                        # and honestly so: it is how long THIS transport
                        # coefficient takes to reach the quasi-steady crest
                        # depth. K_Q sets the clock and cancels out of the
                        # answer -- the suite checks that by halving K_Q and
                        # doubling the steps.
D_MORPH_MIN = 0.35      # m, the Exner step is gated to water deeper than this.
                        # Same reason: the bed inside the swash is shaped by
                        # swash, which is not modelled here, so the loop is not
                        # allowed to invent an answer for it.


# ------------------------------------------------------------ linear wave theory
def wavenumber(omega, d, iters=40, tol=1e-14):
    """Solve omega^2 = g*k*tanh(k*d) for k. Newton, from a shallow-water start.

    The dispersion relation is linear (Airy) theory, cited to
    `terrain-renderer/references/12-water-rendering.md`: "omega^2 = g*k*tanh(k*h)
    relates frequency omega, wavenumber k = 2*pi/L, and local depth h". The
    solver is this file's; it is checked in the suite against Hunt's (1979)
    explicit approximation, which is a different method entirely.
    """
    d = np.maximum(np.asarray(d, float), D_MIN)
    k = omega / np.sqrt(G * d)              # shallow-water seed, always an
    k = np.maximum(k, omega ** 2 / G)       # over-estimate of the true k in
                                            # deep water, where k -> omega^2/g
    for _ in range(iters):
        t = np.tanh(k * d)
        f = G * k * t - omega ** 2
        # d/dk [g k tanh(kd)] = g tanh(kd) + g k d sech^2(kd)
        fp = G * t + G * k * d * (1.0 - t * t)
        step = f / fp
        k = k - step
        if np.max(np.abs(step)) < tol * np.max(k):
            break
    return k


def wavenumber_hunt(omega, d):
    """Hunt's (1979) explicit approximation to the same root. INDEPENDENT.

    Quoted from COHERENS chapter 7, equations (7.10)-(7.12):
        k = omega * sqrt(f(a) / (g*d)),  a = omega^2 * d / g,
        f(a) = a + (1 + 0.652a + 0.4664a^2 + 0.0864a^4 + 0.0675a^5)^-1
    Nothing in this file's Newton solve was written from this, and nothing here
    was written from that -- which is the whole point of having it. Two routes to
    a number must not share a source; this project installed a wrong constant
    twice because they did.
    """
    d = np.maximum(np.asarray(d, float), D_MIN)
    a = omega ** 2 * d / G
    f = a + 1.0 / (1.0 + 0.652 * a + 0.4664 * a ** 2
                   + 0.0864 * a ** 4 + 0.0675 * a ** 5)
    return omega * np.sqrt(f / (G * d))


def celerity(omega, k, d):
    """Phase speed c, group speed c_g, and the ratio n = c_g/c.

    n = 0.5*(1 + 2kd/sinh 2kd) is linear theory. It is worth having the two
    limits in front of the eye, because THE FACTOR-OF-TWO TRAP LIVES HERE:
    n -> 1/2 in deep water (kd >> 1) and n -> 1 in shallow water (kd << 1). Every
    "coefficient" in the radiation-stress algebra that looks like a constant is
    really this n evaluated at one end or the other.
    """
    kd = np.minimum(k * np.maximum(d, D_MIN), 350.0)   # sinh overflows past ~710
    c = omega / k
    n = 0.5 * (1.0 + 2.0 * kd / np.sinh(2.0 * kd))
    return c, n * c, n


def deep_celerity(T):
    """c_0 = g*T/(2*pi). The deep-water limit of c = omega/k with k = omega^2/g."""
    return G * T / (2.0 * math.pi)


def deep_wavelength(T):
    """L_0 = g*T^2/(2*pi). Used by the Iribarren number and by the wave-base gate."""
    return G * T * T / (2.0 * math.pi)


def snell_sin(c, c0, sin_theta0):
    """Snell for water waves: sin(theta)/c is invariant along straight contours.

    This is the SAME statement as optics' Snell with c in place of 1/n, and the
    reason the crests turn onto the depth contours: c falls shoreward, so
    sin(theta) falls with it. Cited to 12-water-rendering ("crests rotate toward
    alignment with depth contours"); the invariant itself is the closed form the
    suite tests the 2-D ray tracer against.
    """
    return np.clip(c / c0 * sin_theta0, -1.0, 1.0)


# ------------------------------------------------------------------- the bed
def dean_bed(x, x_shore=None, A=DEAN_A):
    """The Dean (1991) equilibrium ramp as a BED ELEVATION on this file's grid.

    d = A*y^(2/3) with y the distance seaward of the shoreline, so
    h = -A*(x_shore - x)^(2/3) with x increasing shoreward.

    Cited to 12-glacial-coastal: it is the FAR-FIELD relaxation and explicitly
    "not the whole profile" -- the surf-zone band gets the morphodynamic step and
    "its far field relaxes back onto this Dean ramp".
    """
    x = np.asarray(x, float)
    if x_shore is None:
        x_shore = float(x[-1])
    y = np.maximum(x_shore - x, 0.0)
    return -A * y ** (2.0 / 3.0)


def make_grid(x_len=X_LEN, dx=DX):
    """x increasing shoreward, x = 0 offshore, x = x_len at the still waterline."""
    n = int(round(x_len / dx)) + 1
    return np.linspace(0.0, x_len, n)


def smooth_depth(d, dx, scale):
    """A wavelength-scale filtered copy of the depth, for the transform only.

    Cited to `terrain-architect/references/27-engine-data-handoff.md`, which asks
    the handoff to carry "waterDepth (and a wavelength-scale filtered copy -- raw
    bathymetry noise dithers the break line)". The same argument applies to a
    morphodynamic loop, where the bed the transform reads is the bed the loop is
    writing: without it, one-cell bed noise moves the break point and the loop
    amplifies its own numerical grain into a comb of little bars.

    THE CHAPTER'S SCALE IS WRONG FOR THIS USE, AND IT COST THIS FILE A ROUND.
    Taken literally, "wavelength-scale" here is L/10 to L, i.e. 13-130 m, and
    the bar the loop builds is 11 m wide at half amplitude. Filtering at 13 m did not merely blur
    the bar: it HID the bar from the wave that was supposed to break on it, so
    the feedback that limits the bar's growth never fired and the crest grew
    through the depth the chapter predicts for it and kept going. The filter is
    therefore set at the GRID-NOISE scale (1.5 cells) and not the wavelength
    scale, and this file records the disagreement rather than quietly deviating:
    27's advice is right for a renderer's break MASK, where the aim is a clean
    foam line, and wrong for a morphodynamic loop, where the depth field is a
    state variable and filtering it feeds back into the bed.
    """
    sig = max(scale / dx, 1e-6)
    rad = int(math.ceil(3.0 * sig))
    if rad < 1:
        return np.asarray(d, float).copy()
    t = np.arange(-rad, rad + 1, dtype=float)
    w = np.exp(-0.5 * (t / sig) ** 2)
    w /= w.sum()
    pad = np.concatenate([np.full(rad, d[0]), d, np.full(rad, d[-1])])
    return np.convolve(pad, w, mode='valid')


# ------------------------------------------------------- the wave transform
def transform(x, h, T, H0, theta0, eta=None, breaking=True,
              gamma_b=GAMMA_B, gamma_s=GAMMA_STABLE, k_dally=K_DALLY,
              filter_scale=None):
    """Shoal, refract and break a stated offshore sea state across a bed.

    IN:  x (m, shoreward+), h (bed elevation, m), T (s), H0 (deep-water m),
         theta0 (deep-water rad off shore-normal), eta (wave setup, m, optional)
    OUT: a dict of fields on x.

    THE SHAPE OF THE CALCULATION, and why it is not chapter 12's pseudocode.

    12-glacial-coastal's runnable core writes the transform as

        H_w = min(shoal(H_0, d), gamma*d)          # shoaling + breaker cap

    and that CANNOT PRODUCE THE FEATURE THE SAME SECTION IS ABOUT. `shoal()` is
    the unbroken flux-conserving height, which keeps growing shoreward; over a
    bar-trough profile min(shoal, gamma*d) therefore stays pinned to gamma*d
    everywhere landward of the first break, because shoal() has no memory of the
    energy the break took out. The wave never un-breaks, the trough never
    reforms, and the two breaking lines with calm water between them -- the exact
    signature the bar exists to reproduce -- cannot appear. The cap is a mask,
    not a transform.

    What produces reform is a DISSIPATION model with memory: march the energy
    flux and let breaking subtract from it. This file uses Dally, Dean &
    Dalrymple (1985), the standard model for exactly this, in its energy-flux
    form:

        d/dx (E c_g cos(theta)) = -(K/d) * (E c_g cos(theta) - E_s c_g cos(theta))
        E_s = rho g (gamma_s d)^2 / 8                      # the stable flux

    with breaking switched ON when H >= gamma_b*d and OFF again when H falls to
    gamma_s*d. That hysteresis IS the reform mechanism, and gamma_b is the same
    shared index the bar crest is predicted from. Cited: REF/DIF 1 v3.0 manual
    section 2.3.5 for the model, its onset criterion and gamma_s = 0.4; K is
    marked and swept (see K_DALLY).

    The march is exact for locally constant d and E_s:
        F_{i+1} = F_s + (F_i - F_s) * exp(-K*dx/d)
    which is unconditionally stable and does not need a sub-stepped Euler.
    """
    x = np.asarray(x, float)
    h = np.asarray(h, float)
    dx = float(x[1] - x[0])
    omega = 2.0 * math.pi / T
    n_pts = x.size

    surf = np.zeros(n_pts) if eta is None else np.asarray(eta, float)
    d_raw = np.maximum(surf - h, D_MIN)
    if filter_scale is None:
        filter_scale = 1.5 * dx
    d = np.maximum(smooth_depth(d_raw, dx, filter_scale), D_MIN)

    k = wavenumber(omega, d)
    c, cg, n = celerity(omega, k, d)

    c0 = deep_celerity(T)
    sin_t = snell_sin(c, c0, math.sin(theta0))
    theta = np.arcsin(sin_t)
    cos_t = np.cos(theta)

    # The offshore boundary condition. E_0 c_g0 cos(theta_0) is the deep-water
    # energy flux per unit length of COAST; c_g0 = c_0/2 because n = 1/2 out
    # there. Conserving it to the boundary is what makes H at x = 0 an output.
    E0 = RHO_SW * G * H0 ** 2 / 8.0
    cg0 = c0 / 2.0
    F0 = E0 * cg0 * math.cos(theta0)

    F = np.empty(n_pts)
    brk = np.zeros(n_pts, bool)
    F[0] = F0
    breaking_now = False
    for i in range(n_pts - 1):
        H_i = math.sqrt(max(8.0 * F[i] / (RHO_SW * G * cg[i] * cos_t[i]), 0.0))
        if breaking:
            if H_i >= gamma_b * d[i]:
                breaking_now = True
            elif H_i <= gamma_s * d[i]:
                breaking_now = False
        brk[i] = breaking_now
        if breaking_now:
            F_s = (RHO_SW * G * (gamma_s * d[i]) ** 2 / 8.0) * cg[i] * cos_t[i]
            F[i + 1] = F_s + (F[i] - F_s) * math.exp(-k_dally * dx / d[i])
        else:
            F[i + 1] = F[i]
    brk[-1] = breaking_now

    H = np.sqrt(np.maximum(8.0 * F / (RHO_SW * G * cg * cos_t), 0.0))
    E = RHO_SW * G * H ** 2 / 8.0

    # Dissipation rate. D_w = -d(F)/dx, W/m^2, POSITIVE where energy is lost.
    # It is a RATE and it is not a velocity and it is not an energy density; the
    # undertow below is built from E and not from this, which is the standing
    # trap chapter 12 names.
    D_w = np.zeros(n_pts)
    D_w[1:-1] = -(F[2:] - F[:-2]) / (2.0 * dx)
    D_w[0] = -(F[1] - F[0]) / dx
    D_w[-1] = -(F[-1] - F[-2]) / dx

    return dict(x=x, h=h, d=d, d_raw=d_raw, k=k, c=c, cg=cg, n=n,
                theta=theta, H=H, E=E, F=F, D_w=D_w, brk=brk,
                T=T, omega=omega, H0=H0, theta0=theta0, c0=c0, cg0=cg0,
                E0=E0, F0=F0, dx=dx)


def breaker_state(tr, gamma_b=GAMMA_B):
    """Where the wave first breaks, and how big it is there. H_b and d_b are
    OUTPUTS of the transform -- chapter 12 says so explicitly, and the bar's
    predicted crest depth is written from them, never the other way round."""
    H, d = tr['H'], tr['d']
    over = np.nonzero(H >= gamma_b * d)[0]
    if over.size == 0:
        return None
    i = int(over[0])
    # INTERPOLATE THE CROSSING. Taking the first cell that is over the index
    # reports H/d at that cell, which on a 1 m grid across a bar's flank
    # overshoots gamma by ~3% -- a discretisation artefact that looks exactly
    # like a wrong constant. The crossing itself is where H/d = gamma, so it is
    # found where it is, between two cells.
    f = 0.0
    if i > 0:
        r0 = H[i - 1] / max(d[i - 1], D_MIN)
        r1 = H[i] / max(d[i], D_MIN)
        if r1 != r0:
            f = float(np.clip((gamma_b - r0) / (r1 - r0), 0.0, 1.0))

    def _at(a):
        return float(a[i - 1] + f * (a[i] - a[i - 1])) if i > 0 else float(a[i])

    return dict(i=i, x=_at(tr['x']), H_b=_at(H), d_b=_at(d),
                theta_b=_at(tr['theta']), c_b=_at(tr['c']), n_b=_at(tr['n']),
                i_cell=i, frac=f)


# ------------------------------------------- radiation stress: setup & longshore
def radiation_stress(tr):
    """S_xx and S_yx from linear theory (Longuet-Higgins & Stewart 1962, 1964).

        S_xx = E * (n*(1 + cos^2 theta) - 1/2)
        S_yx = E * n * sin(theta) * cos(theta)

    THE FACTOR OF TWO LIVES IN THE n. S_yx carries n = c_g/c, which is 1/2 in
    deep water and 1 at breaking, so the SAME conserved alongshore momentum flux
    reads

        (E_0/4) * sin(2*theta_0)     in deep-water quantities
        (E_b/2) * sin(2*theta_b)     in breaking-zone quantities

    Pairing the quarter with breaking-zone values is wrong by exactly two, and
    the suite proves the two forms equal on this file's own fields rather than
    asserting it in a comment.
    """
    E, n, th = tr['E'], tr['n'], tr['theta']
    Sxx = E * (n * (1.0 + np.cos(th) ** 2) - 0.5)
    Syx = E * n * np.sin(th) * np.cos(th)
    return Sxx, Syx


def alongshore_thrust(tr, where='deep'):
    """The alongshore radiation-stress flux S_yx, written at one end or the
    other of the transform.

        where='deep'  ->  (E_0/4) * sin(2*theta_0)      # c_g/c = 1/2 out there
        where='break' ->  (E_b/2) * sin(2*theta_b)      # c_g/c -> 1 at breaking

    THIS FUNCTION EXISTS SO THE FACTOR OF TWO HAS SOMEWHERE TO LIVE. The two
    expressions are the SAME conserved quantity, and with no dissipation between
    them they must agree; the coefficients differ only because each has absorbed
    the local n = c_g/c. Chapter 12 states the trap in one sentence -- "pairing
    the 1/4 with breaking-zone values is wrong by exactly two, and it is the easy
    mistake here" -- and putting both forms in one function, checked against each
    other, is how that sentence becomes a test instead of a warning.
    """
    if where == 'deep':
        return (tr['E0'] / 4.0) * math.sin(2.0 * tr['theta0'])
    b = breaker_state(tr)
    if b is None:
        return None
    i = b['i_cell']
    return (tr['E'][i] / 2.0) * math.sin(2.0 * tr['theta'][i])


def wave_setup(tr):
    """Integrate the cross-shore momentum balance for the mean surface eta.

        d(eta)/dx = -(1/(rho g d)) * d(S_xx)/dx

    Setdown seaward of the break, setup inside it. The closed form for the
    shoaling zone -- eta = -(1/8) H^2 k / sinh(2 k d) -- is NOT used here; it is
    what the suite checks this integration against, and the two are independent
    because this routine never sees it.
    """
    Sxx, _ = radiation_stress(tr)
    d, x = tr['d'], tr['x']
    dx = tr['dx']
    dS = np.gradient(Sxx, dx)
    slope = -dS / (RHO_SW * G * np.maximum(d, D_MIN))
    eta = np.concatenate([[0.0], np.cumsum(0.5 * (slope[1:] + slope[:-1]) * dx)])
    return eta - eta[0]


def longshore_current(tr, c_f=0.006):
    """The longshore current from the alongshore radiation-stress gradient.

    Momentum balance, per unit bed area:  -d(S_yx)/dx = tau_b
    with the linearised bed stress tau_b = rho * c_f * (2/pi) * u_orb * V
    (the 2/pi is the cycle mean of |cos| for a sinusoidal orbital velocity much
    larger than V -- it is an average, not a fit).

    Chapter 12 gives the shape, not the coefficient:
        V ~ (gamma/C_f) * tan(beta) * sqrt(g d_b) * sin(theta_b) * cos(theta_b)
    and insists tan(beta) is structural. Deriving the coefficient on a
    saturated plane slope, with H = gamma*d and n = 1:

        S_yx      = (rho g gamma^2 d^2 / 8) sin cos
        u_orb     = (gamma/2) sqrt(g d)
        dS_yx/dx  = (rho g gamma^2/8) [ 2 d (dd/dx) sin cos
                                        + d^2 d(sin cos)/dx ]
                                      └ depth term    └ REFRACTION term

    The depth term alone gives V = (pi/4)(gamma/C_f) tan(beta) sqrt(gd) sin cos.

    THE REFRACTION TERM IS NOT NEGLIGIBLE AND THIS FILE DROPPED IT FIRST TIME.
    In shallow water Snell gives sin(theta) proportional to c, i.e. to sqrt(d),
    so d(ln(sin cos))/dx = (1/2) d(ln d)/dx and the second term is exactly a
    QUARTER of the first, with the same sign. The coefficient is therefore

        (pi/4) * (5/4) = 5*pi/16 = 0.9817

    which is the Longuet-Higgins (1970) value this file previously carried as an
    unexplained `?` -- "the textbook number is 25% larger and the difference is
    presumably in the bed-stress linearisation". It is not: the 25% IS the
    alongshore refraction, and the `?` is now closed by a derivation instead of
    a citation. The suite found it, by failing: the numerical solve (which
    differentiates the whole of S_yx and therefore has the term) sat 23% above
    the hand-written closed form, and 1.25 is not a tolerance one can widen.

    C_f = 0.006 is a declared tuned friction coefficient (chapter 12: "C_f and
    the mixing profile f are tuned"), and lateral mixing is not modelled -- so
    over a bar, where the dissipation is localised into a few metres, this V
    spikes. That is a known limit and the suite reports it separately rather
    than smoothing it away.
    """
    _, Syx = radiation_stress(tr)
    dx = tr['dx']
    thrust = -np.gradient(Syx, dx)                  # N/m^2, alongshore
    u_orb = orbital_velocity(tr)
    denom = RHO_SW * c_f * (2.0 / math.pi) * np.maximum(u_orb, 1e-6)
    V = thrust / denom
    V[~tr['brk']] *= 0.0                            # confined to the surf zone:
    return V                                        # outside it the gradient is
                                                    # the shoaling one, which is
                                                    # balanced by setdown, not by
                                                    # the bed.


# ------------------------------------------------ the currents that move sand
def orbital_velocity(tr):
    """Near-bed orbital velocity amplitude, linear theory:

        u_orb = pi*H / (T * sinh(k*d))

    which is the standard Airy result a*omega/sinh(kd) with a = H/2. It is the
    STIRRING term in the energetics flux below: sand does not move because the
    current is strong, it moves because the waves lift it and the current then
    has something to carry.
    """
    kd = np.minimum(tr['k'] * np.maximum(tr['d'], D_MIN), 350.0)
    return math.pi * tr['H'] / (tr['T'] * np.sinh(kd))


def undertow(E_w, c, d, k_u=1.0):
    """The seaward return flow below trough level.

        u_u = k_u * E_w / (rho * c * d)

    DERIVED, not asserted: a progressive wave carries a mass flux per unit width
    of M = E/c (the Stokes transport; it is the momentum density of the wave).
    Continuity returns that below trough level over the depth d, so the mean
    return speed is M/(rho d) = E/(rho c d). k_u = 1 is that pure wave part;
    breaking adds the surface roller on top of it and the caller passes k_u > 1
    for the broken band.

    DIMENSIONS, because chapter 12 names this exact trap: E_w is an energy
    DENSITY, kg/s^2 (J/m^2). E/(rho c d) = (kg s^-2)/(kg m^-3 * m s^-1 * m)
    = m/s. Building it from the dissipation RATE D_w (kg/s^3, W/m^2) instead
    gives m/s^2, an acceleration. This function is written in pure arithmetic so
    the suite can push a dimension algebra through it and get m/s out -- and get
    m/s^2 out when the bug is put back.
    """
    return k_u * E_w / (RHO_SW * c * d)


def ursell(H, k, d):
    """Ursell number, the standard measure of how nonlinear a wave has become.

        Ur = (3/16) * H * k / (k*d)^3

    = (3/8)*a*k/(kd)^3 with a = H/2. Zero in deep water (kd large), large in
    shallow water. It is what the skewness below is a function of, and it is why
    the skewness vanishes offshore without anything switching it off.
    """
    kd = np.maximum(k * np.maximum(d, D_MIN), 1e-9)
    return (3.0 / 16.0) * H * k / kd ** 3


SK_MAX = 1.0        # the saturating skewness. `?` -- a declared shape parameter.
UR_HALF = 1.0       # Ursell number at half saturation. `?` -- likewise.


def skewness(Ur, sk_max=SK_MAX, ur_half=UR_HALF):
    """Wave-orbital velocity skewness as a function of the Ursell number.

        Sk = sk_max * Ur / (Ur + ur_half)

    `?` ON THE PARAMETERISATION, and it is stated rather than hidden. What is
    NOT free is the shape, and the shape is what the bar depends on:

      * Sk -> 0 as Ur -> 0. A linear, symmetric wave has NO skewness, and
        chapter 12 makes this the whole reason the onshore term exists: "the
        skewness factor is what makes this term exist; u_orb^3 alone would move
        sand onshore under a perfectly symmetric swell, which is wrong".
      * Sk saturates rather than growing without bound, because a real wave's
        crest-trough asymmetry is limited by breaking.

    A published parameterisation exists (Ruessink et al. 2012 give B(Ur) and a
    phase psi); it could not be verified from a source this wave, so it is not
    claimed. The suite tests the two limits above, which is what the bar uses,
    and the sensitivity of the bar crest to sk_max and ur_half is swept.
    """
    Ur = np.maximum(np.asarray(Ur, float), 0.0)
    return sk_max * Ur / (Ur + ur_half)


# ============================================================================
# THE NONLINEAR FREE SURFACE -- wave 5
# ============================================================================
# WHAT THIS SECTION IS FOR, and it is one sentence: the skewness above is spent
# ONLY inside the sediment transport, and the same quantity is what makes the
# crest sharp and the trough flat. Waves 1-4 drew the surface as
#
#       eta = (H/2) cos(S)
#
# -- a sinusoid, symmetric about the still level, whose steepest face is
# (H/2)k = 8.4 deg on this scene. Everything below turns the file's OWN Ursell
# number into the shape of that surface, with NO new magnitude constant.
#
# ONE NONLINEARITY, TWO MOMENTS. Second-order Stokes adds a bound second
# harmonic to the primary:
#
#       eta = a cos(phi) + a r cos(2 phi + psi),      a = H/2
#
# and the two free moments of that shape are not independent of it:
#
#       skewness   Sk = <eta^3>/sigma^3 = (3/4) r cos(psi) / ((1+r^2)/2)^(3/2)
#       asymmetry  As = <Hilb(eta)^3>/sigma^3 = -(3/4) r sin(psi) / (...)
#
# so Sk^2 + As^2 is a function of r alone and psi merely ROTATES between them.
# That is the finding this section carries into the README: the file's own
# `broken_fraction` collapse of the skewness at breaking, written as a factor
# (1 - f_brk), IS this rotation seen from one side -- what leaves the skewness
# arrives in the asymmetry, and a bore is the same wave with psi = -pi/2.


def stokes2_shape(kd):
    """The depth function of the bound second harmonic,

        C(kd) = cosh(kd) (2 + cosh 2kd) / sinh^3(kd)

    from second-order Stokes theory (Dean & Dalrymple, *Water Wave Mechanics
    for Engineers and Scientists*, the second-order surface profile). Its two
    limits are checked in the suite because they are what tie it to quantities
    this file already has:

        kd -> 0   C -> 3/(kd)^3        (shallow; see `stokes2_ratio`)
        kd -> inf C -> 2               (deep; b/a -> ak/2, the textbook form)
    """
    kd = np.maximum(np.asarray(kd, float), 1e-9)
    return np.cosh(kd) * (2.0 + np.cosh(2.0 * kd)) / np.sinh(kd) ** 3


def stokes2_ratio(H, k, d):
    """r = b/a, the second harmonic's amplitude as a fraction of the first.

        b = (H^2 k / 16) C(kd)   ->   r = b/a = (H k / 8) C(kd)

    NOTHING IS DECLARED HERE. r is a function of the three fields the transform
    already marches, and its shallow-water limit is the punchline:

        C -> 3/(kd)^3   =>   r -> (3/8) H k /(kd)^3 = 2 * Ur

    with `ursell` EXACTLY as this file already defines it, Ur = (3/16)Hk/(kd)^3.
    The 3/16 in that definition is not a convention picked for tidiness -- it is
    the constant that makes the Ursell number one half of the second harmonic's
    own amplitude ratio. The nonlinearity of the surface was already in this
    file four waves ago, computed and thrown away.
    """
    kd = np.maximum(np.asarray(k, float) * np.maximum(d, D_MIN), 1e-9)
    return np.asarray(H, float) * np.asarray(k, float) / 8.0 * stokes2_shape(kd)


# --- the two validity limits, and neither is a tolerance ---------------------
# Stokes' expansion is a series in the steepness and it does not hold in the
# surf zone. Running past that silently is the failure mode this section is
# written against, so BOTH limits below are computed and both are reported.

URSELL_STOKES_LIMIT = 0.5
# THE REGIME BOUNDARY, IN THIS FILE'S OWN NORMALISATION, DERIVED. The standard
# Ursell parameter is U = H L^2 / d^3 and the conventional Stokes/cnoidal
# boundary is U ~ 32 pi^2 / 3 = 105.3 (Ursell 1953; the regime diagram in
# Le Mehaute and in the Shore Protection Manual). This file's Ur uses k rather
# than L:
#
#   Ur = (3/16) H k /(kd)^3 = (3/16) H /(k^2 d^3) = (3/16) H L^2/(4 pi^2 d^3)
#      = (3/(64 pi^2)) U
#
# so U = 32 pi^2/3  <=>  Ur = (3/(64 pi^2))(32 pi^2/3) = 1/2, EXACTLY. The
# boundary is a round number in this file's variable and that is not luck: the
# same 3/16 that makes Ur half the harmonic ratio makes the regime boundary a
# half. The 32 pi^2/3 is the cited half; the conversion is the derived half.


def stokes2_crest_limit(psi, n=4096):
    """The largest r for which eta is still ONE crest and ONE trough per cycle.

    DERIVED HERE, and it is the limit that does not need a citation. With

        eta = a[cos(phi) + r cos(2 phi + psi)]
        d(eta)/d(phi) = -a[sin(phi) + 2 r sin(2 phi + psi)]

    the surface has extra stationary points -- a false crest standing in the
    trough -- as soon as that derivative gains more than two zeros per cycle.
    Two closed forms bracket the answer and the suite checks both against this
    function:

      psi = 0      d(eta)/d(phi) = -sin(phi)(1 + 4 r cos(phi)), so the extra
                   roots appear at cos(phi) = -1/(4r), i.e. at r = 1/4. At
                   exactly 1/4 the trough is FLAT -- which is the shape bar
                   section A is after, reached at the limit of the theory
                   rather than by choosing it.

      psi = -pi/2  the derivative is -[sin(phi) + 2r(1 - 2 sin^2 phi)], a
                   quadratic in sin(phi); its second root leaves [-1, 1] at
                   r = 1/2, twice as generous.

    So the pitched-forward (asymmetric) shape tolerates twice the harmonic the
    peaked (skewed) one does -- the SAME second harmonic, rotated. In between
    there is no closed form and this counts sign changes on a fine grid.

    THE ANSWER IS A FUNCTION OF ONE VARIABLE, so it is bisected once on a
    ladder of 257 phases and interpolated after that. Written cell-by-cell the
    first time, it was 7e9 flops on a 89 x 501 bay and dominated the whole
    render; the ladder is 1/170th of that and its interpolation error against
    the direct bisection is a row in the suite.
    """
    psi = np.asarray(psi, float)
    tab_u, tab_r = _crest_limit_table(n)
    u = np.sqrt(np.clip(-psi, 0.0, np.pi / 2))
    out = np.interp(u, tab_u, tab_r)
    return out if psi.shape else float(out)


_CREST_TAB = {}


def _crest_limit_table(n=4096, m=513):
    """The bisection itself, on a ladder spanning the only phases `bore_phase`
    can produce -- [-pi/2, 0].

    THE LADDER IS UNIFORM IN sqrt(-psi) AND NOT IN psi, and that is not a
    refinement, it is required. r_max(psi) has a SQUARE-ROOT CUSP at psi = 0:
    it leaves 1/4 with infinite slope, 0.2524 at psi = -0.001 and 0.2610 at
    -0.01. A ladder uniform in psi interpolates across that cusp and reports
    0.2548 where the closed form says 0.2500 -- a 2% error in the one place
    the answer is known exactly. In sqrt(-psi) the curve is smooth and the
    suite's row against `_crest_limit_direct` holds to 1e-4.
    """
    if (n, m) in _CREST_TAB:
        return _CREST_TAB[(n, m)]
    phi = (np.arange(n) + 0.5) / n * 2.0 * np.pi          # off the zeros of sin
    u = np.linspace(0.0, math.sqrt(np.pi / 2), m)
    ps = (-u ** 2).reshape(-1, 1)
    lo = np.full(m, 1e-4)
    hi = np.full(m, 2.0)
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        f = -(np.sin(phi)[None] + 2.0 * mid[:, None]
              * np.sin(2.0 * phi[None] + ps))
        s = np.sign(f)
        n_ch = (s != np.roll(s, -1, axis=1)).sum(axis=1)
        ok = n_ch <= 2
        lo = np.where(ok, mid, lo)
        hi = np.where(ok, hi, mid)
    out = (u, lo)
    _CREST_TAB[(n, m)] = out
    return out


def _crest_limit_direct(psi, n=4096):
    """One phase, bisected without the table. The suite's second route."""
    phi = (np.arange(n) + 0.5) / n * 2.0 * np.pi
    lo, hi = 1e-4, 2.0
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        f = -(np.sin(phi) + 2.0 * mid * np.sin(2.0 * phi + psi))
        s = np.sign(f)
        if int((s != np.roll(s, -1)).sum()) <= 2:
            lo = mid
        else:
            hi = mid
    return lo


def bore_phase(f_brk):
    """The second harmonic's phase, psi, from the breaking fraction the
    transform already computes.

        psi = -(pi/2) * f_brk

    DECLARED SHAPE, DERIVED ENDPOINTS, and it is the one interpolation in this
    section. What is derived is both ends:

      f_brk = 0   an unbroken shoaling wave carries a BOUND harmonic, and a
                  bound harmonic is phase-locked to its primary: psi = 0. That
                  is second-order Stokes and nothing else.
      f_brk = 1   a fully broken wave is a BORE, and `broken_fraction`'s own
                  docstring already says so in this file: "the shape energy has
                  gone into a pitched-forward front, the near-bed velocity is a
                  sawtooth". A sawtooth is the pure-asymmetry shape, psi=-pi/2.

    The sign is not free either. With eta = a cos(S - omega t) and S increasing
    SHOREWARD, psi = -pi/2 puts the steep face on the shoreward side (the wave's
    front) and psi = +pi/2 puts it on the seaward side. The suite has a row that
    fails if the sign is flipped, because a wave leaning the wrong way is a
    defect a still frame hides.

    Ruessink et al. (2012) publish a psi(Ur) for exactly this and it goes the
    same way; it could not be verified from a source in this loop, so it is not
    claimed and this linear form is used and swept instead.
    """
    return -(np.pi / 2.0) * np.clip(np.asarray(f_brk, float), 0.0, 1.0)


def nonlinear_eta(a, r, psi, phase):
    """eta = a [cos(phase) + r cos(2*phase + psi)]. The whole surface."""
    return a * (np.cos(phase) + r * np.cos(2.0 * phase + psi))


def surface_moments(r, psi):
    """The EXACT skewness and asymmetry of that shape, in closed form.

        <eta^2>   = a^2 (1 + r^2)/2
        <eta^3>   = (3/4) a^3 r cos(psi)
        <Hilb^3>  = -(3/4) a^3 r sin(psi)      with Hilb(cos n phi) = sin n phi

        Sk = (3/4) r cos(psi) / ((1+r^2)/2)^(3/2)
        As = -(3/4) r sin(psi) / ((1+r^2)/2)^(3/2)

    THE CONSEQUENCE IS THE POINT: Sk^2 + As^2 depends on r ALONE. Breaking does
    not destroy the wave's third moment, it ROTATES it out of the skewness and
    into the asymmetry. This file's sediment transport multiplies its skewness
    by (1 - f_brk) and has no asymmetry term at all; cos(pi f_brk/2) and
    (1 - f_brk) agree at both ends and differ by 41% at f_brk = 1/2, and that
    difference is measured rather than argued.

    THE SIGN CONVENTION IS STATED because the literature's is not uniform: with
    Hilb(cos) = +sin, a shoreward-pitched front (psi = -pi/2) gives As > 0 here.
    Papers that define the Hilbert transform with the opposite sign report the
    same wave with As < 0. Nothing downstream reads the sign of As except the
    suite row that checks which face is steep, and that row measures the SLOPE,
    which has no convention in it.
    """
    r = np.asarray(r, float)
    psi = np.asarray(psi, float)
    s3 = ((1.0 + r ** 2) / 2.0) ** 1.5
    return (0.75 * r * np.cos(psi) / s3, -0.75 * r * np.sin(psi) / s3)


def slope_gain(r, psi, n=4096):
    """max |d eta/d phi| / a, the factor by which the second harmonic steepens
    the STEEPEST FACE. 1.0 for a sinusoid, by construction.

    This is the quantity bar section A lives or dies on, so it is measured on
    the shape rather than estimated: the maximum face slope of the surface is
    a k * slope_gain(r, psi), with a k the linear wave's own maximum slope.

    The two limits worth knowing, both reproduced by the suite:
      psi = 0,     r = 1/4  ->  1.299   (peaked crest, barely steeper flanks)
      psi = -pi/2, r = 1/2  ->  2.000   exactly: max|sin phi - 2r cos 2 phi|
                                        at phi = pi/2 is 1 + 2r.

    A PEAKED CREST IS NOT A STEEP FACE, and the pair above is the cleanest way
    to say it. Pure skewness at ITS OWN validity limit buys 30% of slope; the
    same harmonic rotated into pure asymmetry buys 100%. Section A needs 500%.
    """
    r = np.asarray(r, float)
    psi = np.asarray(psi, float)
    phi = (np.arange(n) + 0.5) / n * 2.0 * np.pi
    sh = np.broadcast(r, psi).shape
    rr = np.broadcast_to(r, sh).reshape(-1)
    pp = np.broadcast_to(psi, sh).reshape(-1)
    g = np.empty(rr.size)
    step = max(1, 2 ** 22 // n)         # chunked: a whole bay at once is 1.5 GB
    for i in range(0, rr.size, step):
        f = np.abs(np.sin(phi)[None] + 2.0 * rr[i:i + step, None]
                   * np.sin(2.0 * phi[None] + pp[i:i + step, None]))
        g[i:i + step] = f.max(axis=1)
    return g.reshape(sh) if sh else float(g[0])


# --- what NO height field can do, and it is a theorem rather than a scene ----
STOKES_CORNER_DEG = 120.0
STOKES_FACE_DEG = 30.0
# STOKES' CORNER, 1880, and it caps every wave of permanent form.
#
# At the crest of the LIMITING wave the fluid is at rest in the frame moving
# with the wave, so the crest is a stagnation point. Bernoulli on the free
# surface, measured from the crest downward, is q^2/2 + g z = 0, so
# q ~ (2 g |z|)^(1/2) ~ r^(1/2) near the corner. A potential flow in a wedge of
# interior angle 2 alpha has q ~ r^(pi/(2 alpha) - 1); matching the exponents,
#
#       pi/(2 alpha) - 1 = 1/2   =>   2 alpha = 2 pi/3 = 120 deg
#
# and the free surface therefore leaves the crest at 30 deg to the horizontal.
# The result is independent of depth, of wavelength and of the wave's height:
# it is the same 120 deg for the limiting deep-water Stokes wave and for the
# limiting solitary wave. Longuet-Higgins & Fox (1977) find the maximum surface
# inclination of the ALMOST-highest wave slightly above this, near 30.4 deg --
# cited, not reproduced here, and it does not change the conclusion.
#
# THE CONCLUSION IT DOES NOT CHANGE: bar section A needs a face steeper than
# 90 - asin(1/n) = 41.48 deg for a sightline to run lengthwise inside the water.
# 30 deg < 41.48 deg. No wave of permanent form -- no Stokes wave at any order,
# no cnoidal wave, no solitary wave, and so no single-valued height field of
# one -- can reach it. Section A is not "not yet steep enough". It is out of
# reach of the representation, for the same structural reason as section F's
# plunging lip, and the two belong together as a matter of proof.


def snell_cone_face_deg(n_w=None):
    """The face angle a lengthwise in-water sightline needs: 90 - asin(1/n).

    Imported rather than restated: n is `optics.IOR`'s green entry, the same
    refractive index the pool's Fresnel, critical angle and L/n^2 all use.
    """
    if n_w is None:
        import optics as _OPT
        n_w = float(_OPT.IOR[1])
    return 90.0 - math.degrees(math.asin(1.0 / n_w))


def ur_half_derived(sk_max=SK_MAX):
    """THE VALUE OF `UR_HALF`, WHICH HAS BEEN `?` SINCE WAVE 1, DERIVED.

    In shallow water the horizontal orbital velocity of a long wave is
    u = eta sqrt(g/d) -- a POSITIVE MULTIPLE of the surface, the same at every
    phase -- so the velocity skewness and the ELEVATION skewness are the same
    number. That makes the parameterisation checkable against the surface:

        Sk_surface -> (3/4) r * 2^(3/2) = (3 sqrt2 / 2) r     (small r)
        r          -> 2 Ur                                    (shallow water)
        =>  Sk     -> 3 sqrt2 Ur = 4.2426 Ur

    while `skewness(Ur) = sk_max Ur/(Ur + ur_half)` has initial slope
    sk_max/ur_half. Matching them,

        ur_half = sk_max / (3 sqrt 2) = sqrt2/6 = 0.235702      (sk_max = 1)

    against the 1.0 declared in wave 1. The declared value is 4.24x too large,
    which makes the shoaling wave's skewness 4.24x too WEAK where the Ursell
    number is small -- offshore of the bar, which is precisely where the
    onshore term is supposed to be doing its work.

    WHAT IS STILL `?` IS `sk_max`, and it is untouched by this: the saturating
    value is a statement about the wave near breaking, where the expansion this
    derivation uses has already failed. What is closed is the SLOPE AT THE
    ORIGIN, which is the half of the parameterisation the bar depends on.
    """
    return sk_max / (3.0 * math.sqrt(2.0))


def surface_state(tr, clamp=True):
    """The nonlinear surface's two fields over a transform, in one place.

    Returns r (clamped to the validity limit if asked), psi, the unclamped r,
    and the fraction of wet cells the clamp bit on -- because that fraction is
    the honest report of how far past second-order Stokes this scene is.

    THE MIXED-FIELD TRAP IS THE REASON THIS IS ONE FUNCTION. r, psi and the
    phase all have to come from ONE transform: r off `tr['H'], tr['k'],
    tr['d']`, psi off `broken_fraction(tr)` which reads `tr['D_w']`, and the
    phase off `tr['S']`. Wave 3 measured that trap at 0.37 of a ratio in 2-D.
    A surface whose harmonic amplitude came from a filtered depth and whose
    phase came from the raw one would be steep in the wrong places and nothing
    in a still frame would say so.
    """
    r_raw = stokes2_ratio(tr['H'], tr['k'], tr['d'])
    psi = bore_phase(broken_fraction(tr))
    lim = stokes2_crest_limit(psi)
    wet = np.asarray(tr['d']) > D_MIN
    frac = float(np.mean(r_raw[wet] > lim[wet])) if wet.any() else 0.0
    r = np.minimum(r_raw, lim) if clamp else r_raw
    return dict(r=r, psi=psi, r_raw=r_raw, limit=lim, clamped_fraction=frac,
                ursell=ursell(tr['H'], tr['k'], tr['d']))


# ------------------------------------------------------ sediment flux and Exner
K_Q = 2.0e-5        # s^2/m, the energetics transport coefficient. DECLARED
                    # TUNED (chapter 12: "the k coefficients, rip speeds, and
                    # spacings are tuned looks"). It sets HOW FAST the bed
                    # responds and cancels out of the equilibrium the loop runs
                    # to -- the suite carries that as an ablation, not a claim.
LAM_U = 1.0         # the weight of the offshore (undertow) term against the
                    # onshore (skewness) one. 1.0 = "neither term is privileged";
                    # both are the same energetics moment <|u|^2 u> with a
                    # different u in it. DECLARED.
K_ROLLER = 0.5      # the roller's multiplier on the undertow inside the broken
                    # band: k_u = 1 + K_ROLLER*f_roll, so the return flow is at
                    # most 1.5x the pure wave value. `?` on the number -- a real
                    # roller model carries an area A_r and its own energy
                    # balance, which is out of scope this wave.
                    #
                    # IT IS BOUNDED FROM ABOVE BY A MEASUREMENT, WHICH IS WHY IT
                    # IS 0.5 AND NOT 1.5. The pure wave part of the undertow at
                    # this scene's break point is E/(rho c d) = 0.38 m/s, and
                    # measured surf-zone undertows are 0.1-0.4 m/s. A multiplier
                    # of 2.5 would have put this scene's undertow at 0.94 m/s,
                    # which is not a beach. The first version of this file did
                    # exactly that, and the bar it produced ran offshore without
                    # ever settling.
EPS_SLOPE = 1.0 / math.tan(math.radians(32.0))     # = 1.600
                    # The downslope gravity term's weight. DERIVED, not chosen:
                    # Bailard's (1981) energetics bedload carries a slope term
                    # whose ratio to the skewness term is tan(beta)/tan(phi),
                    # with phi the sediment's angle of repose -- so the
                    # coefficient IS 1/tan(phi), and 32 deg is the middle of the
                    # 30-34 deg quoted for loose sand. It sets the slope at
                    # which gravity balances the skewness drive: Sk/eps, about
                    # 0.16 at this scene's peak skewness, which is the steepest
                    # a flank can get.
                    #
                    # The first version of this file carried 0.15 with no
                    # derivation, ten times too small, and the bar grew without
                    # limit into a two-cell spike that the transform's own depth
                    # filter then hid from the waves -- the feedback that is
                    # supposed to stop it never fired. An underived constant did
                    # not merely make the picture wrong; it silently disabled a
                    # feedback loop.


def bore_dissipation_scale(tr):
    """The dissipation rate of a FULLY saturated bore, W/m^2:

        D_sat = rho * g * H^3 / (4 * T * d)

    the hydraulic-jump analogy: a broken wave is a bore, a bore of height H in
    depth d dissipates rho*g*H^3/(4*d) per unit length of front, and one front
    passes per period. It is the natural scale to measure D_w against, and it is
    what turns a rate into a dimensionless "how broken is this wave" -- which is
    what the sediment terms want.

    Dimensions: kg/m^3 * m/s^2 * m^3 / (s*m) = kg/s^3 = W/m^2. Same units as
    D_w, which is the point.
    """
    return (RHO_SW * G * tr['H'] ** 3
            / (4.0 * tr['T'] * np.maximum(tr['d'], D_MIN)))


def broken_fraction(tr):
    """How far through breaking the wave is, 0 to 1:

        f = clip( D_w / D_sat, 0, 1 )

    THE FIRST VERSION OF THIS FILE BUILT IT FROM H/d INSTEAD, AND IT WAS WRONG
    IN A WAY WORTH RECORDING. With f keyed to H/d, the sediment saw a broken
    wave wherever H/d was near gamma -- including where the transform said the
    wave was NOT breaking, because H/d had stopped just short. The bed then
    self-organised into a flat terrace at exactly the marginal depth: a wide
    plateau on which the wave was permanently about-to-break and nothing moved.
    Keying f to the DISSIPATION the transform actually computed removes the
    disagreement by construction -- there is only one statement about whether
    this wave is breaking, and both halves read it.

    f carries the two things breaking does to the sediment transport, and
    chapter 12 states both of them as the mechanism that makes the bar:

      * THE SKEWNESS COLLAPSES. An unbroken shoaling wave has a sharp shoreward
        crest stroke and a long weak seaward one (velocity skewness). A broken
        wave is a BORE: the shape energy has gone into a pitched-forward front,
        the near-bed velocity is a sawtooth, and the third moment that drove
        sand shoreward goes with it. So the onshore term dies where the wave
        breaks -- not because it is masked, but because the wave that carried it
        stopped existing.
      * THE ROLLER ARRIVES. The surface roller rides the front and its mass flux
        adds to the shoreward transport above trough level, so continuity has
        more to return below it. The undertow strengthens.

    Those are the two halves of chapter 12's sentence: "Seaward of the
    breakpoint, wave-orbital skewness nudges sand shoreward; landward of it, the
    undertow drags stirred sand seaward. The two fluxes converge at the break
    point". This function is where the sign flip physically happens, and it is
    keyed to a computed field rather than to a position.
    """
    return np.clip(tr['D_w'] / np.maximum(bore_dissipation_scale(tr), 1e-12),
                   0.0, 1.0)


ROLLER_LAG = 0.5    # in LOCAL WAVELENGTHS. The roller does not appear at the
                    # break point and vanish at the end of it: it rides the
                    # front, so its momentum is delivered over the distance the
                    # wave travels while the roller lives. One wavelength is the
                    # distance a crest covers in one period, so a lag measured
                    # in wavelengths needs no new unit. `?` on the 0.5 itself:
                    # the suite sweeps it over [0.25, 1.0] and the bar's crest
                    # DEPTH moves by ~2%, which is the honest substitute for
                    # pinning it.


def roller_fraction(tr, n_lag=ROLLER_LAG):
    """`broken_fraction` delayed SHOREWARD by `n_lag` local wavelengths.

    A first-order causal lag, marched in the direction the wave travels:

        alpha_i = 1 - exp(-dx * k_i / (2*pi*n_lag))       # = dx/(n_lag*L_i)
        f_i     = f_{i-1} + alpha_i * (f_raw_i - f_{i-1})

    CAUSAL AND NOT SYMMETRIC, and that is physics rather than a numerical
    preference: a symmetric filter would put roller momentum SEAWARD of the
    break point, where there is no roller yet, and that would build the bar in
    water the wave has not broken in.

    THE MARCH RUNS ALONG THE LAST AXIS, which is the cross-shore one in both the
    1-D and the 2-D fields. Wave 3 needed this function on a plan-view transform
    and the honest move was to make the shipped function shape-agnostic rather
    than to copy it: a 2-D scene that runs a *copy* of the sediment physics is
    two implementations to keep in step, and the pool loop's standing ruling
    ("shared physics is imported, never copied") applies inside a file as much
    as between two. For a 1-D input this is the identical arithmetic it always
    was, and every wave-1 and wave-2 row still guards it.
    """
    f = broken_fraction(tr)
    if n_lag <= 0:
        return f
    alpha = 1.0 - np.exp(-tr['dx'] * tr['k'] / (2.0 * math.pi * n_lag))
    out = np.empty_like(f)
    out[..., 0] = f[..., 0]
    for i in range(1, f.shape[-1]):
        out[..., i] = out[..., i - 1] + alpha[..., i] * (f[..., i]
                                                        - out[..., i - 1])
    return out


def sediment_flux(tr, k_q=K_Q, lam_u=LAM_U, k_roller=K_ROLLER,
                  eps_slope=EPS_SLOPE, skew=True, undertow_on=True,
                  n_lag=ROLLER_LAG, dhds=None):
    """The cross-shore sediment flux, energetics form (Bailard 1981 structure).

        q = k_q * u_orb^2 * ( Sk*u_orb  -  lam_u*u_u )  -  k_q*eps*u_orb^3*dh/dx

    positive SHOREWARD. The three terms, and each is a different mechanism:

      onshore   Sk*u_orb^3   wave-orbital skewness. A shoaling wave has a short
                             sharp shoreward crest stroke and a long weak seaward
                             one; the transport goes as the third moment, so the
                             asymmetry moves net sand SHOREWARD. Dies offshore
                             because Sk -> 0 there, not because it is masked.
      offshore  u_u*u_orb^2  the undertow carrying what the waves stirred.
                             Strongest where breaking is strongest -- i.e. just
                             landward of the break point.
      slope     -eps*dh/dx   gravity, downslope. Bailard's slope term.

    THE BAR IS THE CONVERGENCE OF THE FIRST TWO. Seaward of the break the first
    dominates and q > 0; landward of it the second dominates and q < 0; at the
    break point q crosses zero with dq/dx < 0, and Exner turns that convergence
    into a ridge. Nothing here knows where the break point is -- `tr['brk']`
    comes out of the transform, which came out of the bed.

    EXCEPT THAT ONE OF THE TWO TURNS OUT TO BE OPTIONAL, AND THE SUITE FOUND IT.
    Chapter 12 states the bar as the meeting of the two fluxes. Run this
    function with `undertow_on=False` -- no offshore term at all -- and a bar
    still forms, at the same depth (2.07 m against 2.08 m) with about a fifth
    less relief. The onshore flux converges against ZERO: breaking destroys the
    skewness that drives it, so q_on collapses over a few metres at the break
    point whether or not anything is carrying sand the other way. The undertow
    deepens the trough and sharpens the crest; it is not what puts the bar
    where it is. Recorded here because the sentence above is the one a reader
    will otherwise take on trust.
    """
    u_orb = orbital_velocity(tr)
    f_brk = broken_fraction(tr)                 # the wave's own shape: instant
    f_roll = roller_fraction(tr, n_lag)         # the roller's: lagged shoreward
    k_u = 1.0 + k_roller * f_roll
    u_u = undertow(tr['E'], tr['c'], np.maximum(tr['d'], D_MIN), k_u)
    Sk = (skewness(ursell(tr['H'], tr['k'], tr['d'])) * (1.0 - f_brk)
          if skew else np.zeros_like(u_orb))
    if not undertow_on:
        u_u = np.zeros_like(u_u)
    q_on = k_q * Sk * u_orb ** 3
    q_off = k_q * lam_u * u_orb ** 2 * u_u
    # The bed slope along the direction the flux is carried. In 1-D that is
    # d(h)/dx; in the 2-D plan field the caller passes `dhds`, the directional
    # derivative along the wave direction, because gravity pulls sand down the
    # slope the transport is crossing and not down the grid's x axis.
    dhdx = np.gradient(tr['h'], tr['dx'], axis=-1) if dhds is None else dhds
    q_slope = -k_q * eps_slope * u_orb ** 3 * dhdx
    return dict(q=q_on - q_off + q_slope, q_on=q_on, q_off=q_off,
                q_slope=q_slope, u_orb=u_orb, u_u=u_u, Sk=Sk, f_brk=f_brk,
                f_roll=f_roll)


def exner_step(h, q, dx, dt, d, poros=POROSITY, d_min=D_MORPH_MIN):
    """dh/dt = -(1/(1-p)) * dq/dx, the classical Exner equation.

    Attributed to Exner himself, on chapter 12's explicit instruction: "attribute
    the plain dh/dt = -div q/(1-poros) form to Exner himself, *not* to Paola &
    Voller 2005, whose contribution is the generalisation".

    The flux is zeroed at both ends and in water shallower than d_min, so the
    domain is CLOSED: no sand enters or leaves, and the suite checks total volume
    to round-off. A morphodynamic loop that quietly gains sand can build any bar
    you like.
    """
    q = np.asarray(q, float).copy()
    # The shallow gate is a TAPER and not a cliff. A hard q -> 0 at a depth
    # contour puts a step in the flux, and Exner reads a step as an infinite
    # convergence: the first version of this file grew a 14 m spike of sand at
    # the gate's edge in a day and a half of model time. The taper spreads the
    # same (physically correct) shoreward delivery over the band instead of
    # stacking it on one cell.
    taper = np.clip((d - d_min) / 0.5, 0.0, 1.0)
    q *= taper
    q[0] = 0.0
    q[-1] = 0.0
    dqdx = np.gradient(q, dx)
    return h + (-dt / (1.0 - poros) * dqdx)
    # NOTE THE ABSENCE OF A SECOND GATE. An earlier version also zeroed `dh`
    # inside the shallow band, on the reasoning that the swash zone is not
    # modelled here and the loop should not invent an answer for it. That is
    # true and it also LEAKED SAND: the bed change the taper had already
    # accounted for was thrown away, and the domain gained 1.83 m^2 of sand
    # over a 500-hour run -- a source with no physics behind it. Conservation
    # wins: the taper is the only gate, the flux it carries is deposited where
    # it lands, and the suite's volume row is exact rather than tolerant.


def evolve(x, h0, T, H0, theta0, n_steps=N_STEPS, dt=DT_MORPH, with_setup=False,
           relax_dean=0.0, dean_ref=None, **flux_kw):
    """The loop, exactly as chapter 12 draws it:

        waves (shoal, refract, break) -> radiation stress -> currents
          -> sediment flux -> Exner -> the bed changes -> the waves feel it

    `relax_dean` is the far-field relaxation the chapter asks for ("its far
    field relaxes back onto this Dean ramp"), as a rate per step toward
    `dean_ref` OUTSIDE the surf zone only. It defaults to ZERO here, and the
    reason is a test: with the relaxation off, nothing in this loop knows the
    Dean profile at all, so a bar that appears anyway cannot have come from it.
    The evidence run turns it on at a weak rate to show it changes the bar by
    less than a per cent.
    """
    h = np.asarray(h0, float).copy()
    dx = float(x[1] - x[0])
    hist = []
    eta = None
    for step in range(n_steps):
        tr = transform(x, h, T, H0, theta0, eta=eta)
        if with_setup:
            eta = wave_setup(tr)
        fl = sediment_flux(tr, **flux_kw)
        h = exner_step(h, fl['q'], dx, dt, tr['d'])
        if relax_dean > 0.0 and dean_ref is not None:
            outside = ~tr['brk']
            h[outside] += relax_dean * (dean_ref[outside] - h[outside])
        if step % max(1, n_steps // 8) == 0 or step == n_steps - 1:
            hist.append((step, h.copy()))
    tr = transform(x, h, T, H0, theta0, eta=eta)
    return h, tr, hist


def rayleigh_quantiles(h_rms, n):
    """`n` equal-probability heights of a Rayleigh distribution with this H_rms.

        P(H) = 1 - exp(-(H/H_rms)^2)   ->   H_i = H_rms*sqrt(-ln(1 - p_i))

    Rayleigh is the standard deep-water height distribution for a narrow-band
    sea (Longuet-Higgins 1952) and is what Battjes & Janssen clip to get their
    breaking fraction. Equal-probability sampling is used rather than a grid in
    H so the mean of H^2 comes out at H_rms^2 without a weight vector: for
    n = 5 it lands at 2.098 against 2.250, a 7% energy deficit from the missing
    tail, which is reported rather than corrected because correcting it by a
    scale factor would put energy back at the wrong heights.
    """
    p = (np.arange(n) + 0.5) / n
    return h_rms * np.sqrt(-np.log(1.0 - p))


def evolve_forced(x, h0, T, theta0, n_steps=N_STEPS, dt=DT_MORPH,
                  h0_of_t=None, z_of_t=None, n_quantiles=1, H0=H0_SWELL,
                  **flux_kw):
    """The same loop with the forcing allowed to VARY, which is what chapter 12
    means by "the profile breathes on a storm/calm cycle".

    Three knobs, and each one exists to test a candidate cause of section B's
    missing reform rather than to make a prettier bar:

      h0_of_t(t)    the offshore height as a function of model time -- the
                    storm/calm cycle.
      z_of_t(t)     the still-water level -- the tide, as a moving datum. It
                    enters as `eta`, so the depth field, the break point, the
                    Exner shallow gate and the transform all move together.
      n_quantiles   how many Rayleigh heights the sediment flux is averaged
                    over at each step. 1 is the monochromatic loop. Greater
                    than 1 spreads the break point over the width of the height
                    distribution, which is the physical reason real bars are
                    broader than a monochromatic breakpoint model builds them.

    WHAT THIS MEASURED, recorded here because it reverses the obvious guess:
    every one of the three LOWERS the bar's relief. Steady monochromatic
    forcing is the most favourable case this model has. The Rayleigh average
    does widen the crest-to-trough separation -- 15 m to 25 m at n = 3 -- but
    pays for it in relief, 0.90 m down to 0.53 m, and the minimum H/d behind
    the bar barely moves (0.4296 to 0.4172 against the 0.40 needed). See
    README-beach.md, "the second breaking line".
    """
    h = np.asarray(h0, float).copy()
    dx = float(x[1] - x[0])
    for step in range(n_steps):
        t = step * dt
        Hn = H0 if h0_of_t is None else float(h0_of_t(t))
        eta = None if z_of_t is None else np.full_like(h, float(z_of_t(t)))
        heights = (rayleigh_quantiles(Hn, n_quantiles) if n_quantiles > 1
                   else np.array([Hn]))
        q = np.zeros_like(h)
        for Hi in heights:
            tr_i = transform(x, h, T, Hi, theta0, eta=eta)
            q += sediment_flux(tr_i, **flux_kw)['q']
        q /= heights.size
        tr = transform(x, h, T, Hn, theta0, eta=eta)
        h = exner_step(h, q, dx, dt, tr['d'])
    return h, transform(x, h, T, H0, theta0)


# ------------------------------------------------------------- reading the bar
def bar_crest(x, h, h_ref, x_min=None, x_max=None):
    """Find the bar as the largest POSITIVE anomaly of the bed above its
    reference (the initial Dean ramp), and report the water depth over it.

    Deliberately written as "the biggest bump relative to the monotone profile
    it started as", with no window narrower than the domain, so it cannot be
    accused of having been pointed at the answer.
    """
    x = np.asarray(x, float)
    anom = np.asarray(h, float) - np.asarray(h_ref, float)
    m = np.ones_like(anom, bool)
    if x_min is not None:
        m &= x >= x_min
    if x_max is not None:
        m &= x <= x_max
    if not np.any(m):
        return None
    idx = np.arange(x.size)[m]
    i = int(idx[np.argmax(anom[m])])
    return dict(i=i, x=float(x[i]), h=float(h[i]), d=float(-h[i]),
                amp=float(anom[i]))


def trough(x, h, h_ref, i_crest):
    """The trough: the first local MINIMUM of the bed landward of the crest.

    Deliberately not "the largest negative anomaly landward of the crest",
    which was the first version and which answered with the swash zone: on a
    profile whose whole inner surf zone has eroded, the deepest anomaly is at
    the waterline and has nothing to do with a bar-trough. The trough is a
    topographic feature, so it is found topographically.
    """
    h = np.asarray(h, float)
    j = i_crest
    while j + 1 < h.size and h[j + 1] <= h[j]:
        j += 1
    if j >= h.size - 2 or j == i_crest:
        return None
    return dict(i=j, x=float(x[j]), h=float(h[j]), d=float(-h[j]),
                amp=float(h[j] - np.asarray(h_ref, float)[j]))


def _spans(mask, x):
    out, i, n = [], 0, mask.size
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((float(x[i]), float(x[j])))
            i = j + 1
        else:
            i += 1
    return out


def break_lines(tr, gamma_b=GAMMA_B):
    """The x-intervals where H/d is at or above the breaker index.

    THIS IS THE ONSET TEST AND IT IS NOT THE SURF ZONE, and wave 2 had to
    separate the two before section B could be argued about at all. H/d >= gamma
    marks where a wave STARTS breaking. It says nothing about where one stops:
    a wave that has broken sits well below gamma while it is still a bore, so
    this function returns a single narrow interval at each break POINT and empty
    space over the whole white-water band behind it. Reading its output as "the
    breaking lines" makes a saturated surf zone look like no surf zone at all.

    `surf_zone_spans` below is the band the photograph shows.
    """
    return _spans(tr['H'] >= gamma_b * tr['d'], tr['x'])


def surf_zone_spans(tr):
    """The x-intervals where the wave IS breaking -- the white water.

    This reads `tr['brk']`, which is the transform's own hysteretic state: on at
    H >= gamma_b*d, off again at H <= gamma_s*d. Section B's criterion --
    "two breaking lines with calmer water between them" -- is a statement about
    THIS list having two entries, not about `break_lines` having two.
    """
    return _spans(np.asarray(tr['brk'], bool), tr['x'])


# ---------------------------------------------- the saturated surf zone, closed
# The Dally, Dean & Dalrymple march has a closed-form fixed point on a plane
# slope, and it is what decides whether a wave can ever un-break. Derived here
# rather than cited, because no source read this wave states it.
#
# Write the flux in shallow water, where c_g -> sqrt(g d) and cos(theta) -> 1,
# and put H = GAMMA*d for an as-yet-unknown ratio GAMMA(x):
#
#     F = (rho g H^2 / 8) * sqrt(g d) = (rho g^(3/2) / 8) * GAMMA^2 * d^(5/2)
#
# Substitute into the model, dF/dx = -(K/d) * (F - F_s), with the stable flux
# F_s the same expression at GAMMA = gamma_s, and divide out the common factor
# (rho g^(3/2)/8) d^(3/2):
#
#     2 GAMMA GAMMA' d  +  (5/2) m GAMMA^2  =  -K (GAMMA^2 - gamma_s^2)
#
# with m = dd/dx, NEGATIVE where the bed shoals shoreward. GAMMA' = 0 gives
#
#     GAMMA_eq = gamma_s / sqrt(1 + (5/2) m / K)
#
# and three things follow that are not in chapter 12 and were not obvious:
#
#   * A BROKEN WAVE ON A SHOALING BED DOES NOT DECAY TO gamma_s. It decays to a
#     ratio strictly ABOVE it, because the bed keeps taking depth away as fast
#     as the breaking takes height. On this scene's inner slope that ratio is
#     0.477 and the wave sits on it from the bar to the shore. Reading
#     gamma_s = 0.40 as "the H/d a surf zone relaxes to" is wrong by the slope.
#   * IT IS SLOPE-DEPENDENT, RISING WITH tan(beta) -- which is exactly what
#     Raubenheimer, Guza & Elgar (1996) measured on a natural beach and report
#     as a range of 0.2 to 1.0 correlated with the local bed slope. That paper
#     is a field measurement and this is a closed form off a 1985 decay model;
#     they were not written from each other, and they agree in sign, in range
#     and in the claim that gamma is not a constant.
#   * THERE IS A SLOPE ABOVE WHICH NO SATURATED SURF ZONE EXISTS. The
#     denominator vanishes at m = -2K/5, i.e. tan(beta) = 2K/5 = 0.060 here,
#     one in 16.7. Steeper than that and the shoaling gain outruns the breaking
#     loss, GAMMA grows without bound, and the wave surges up the face instead
#     of spilling down it. That is the reflective end of Wright & Short's beach
#     states arriving out of a wave model that has never heard of them.
def saturated_ratio(dddx, k_dally=K_DALLY, gamma_s=GAMMA_STABLE):
    """GAMMA_eq = gamma_s / sqrt(1 + (5/2)*(dd/dx)/K). See the block above.

    `dddx` is dd/dx with x SHOREWARD, so it is negative on a shoaling bed and
    positive down the back of a bar. Returns inf where no fixed point exists.
    """
    v = 1.0 + 2.5 * np.asarray(dddx, float) / k_dally
    return np.where(v > 0.0, gamma_s / np.sqrt(np.maximum(v, 1e-12)), np.inf)


def saturation_slope_limit(k_dally=K_DALLY):
    """tan(beta) above which the Dally model has no saturated state: 2K/5."""
    return 2.0 * k_dally / 5.0


def reform_ratio(d_c, d_t, length, gamma_start=GAMMA_B, k_dally=K_DALLY,
                 gamma_s=GAMMA_STABLE):
    """H/d at the trough, from H/d = gamma_start at the crest, in closed form.

    Same ODE as above, now integrated rather than fixed. With m = dd/dx constant
    and positive (the bed DEEPENS shoreward, down the back of the bar), write
    G = GAMMA^2 and change the independent variable from x to d = d_c + m*(x-x_c):

        dG/dd + (a/d) G = b/d,    a = K/m + 5/2,    b = K gamma_s^2 / m

    which is linear and integrates exactly:

        G(d) = G_eq + (G_c - G_eq) * (d/d_c)^(-a),   G_eq = K gamma_s^2/(K+5m/2)

    THE EXPONENT IS THE WHOLE ANSWER TO SECTION B. `a` carries K/m, so the decay
    is paid for in TRAVEL DISTANCE and not in depth gained: doubling the relief
    over the same 15 m helps far less than keeping the relief and doubling the
    distance. That is why the reform is a trough-WIDTH condition dressed up as a
    relief condition, and it is what `--bug reform-exponent` exists to prove.
    """
    m = (d_t - d_c) / max(length, 1e-9)
    if m <= 0.0:
        return float(gamma_start)
    a = k_dally / m + 2.5
    g_eq = k_dally * gamma_s ** 2 / (k_dally + 2.5 * m)
    g = g_eq + (gamma_start ** 2 - g_eq) * (d_t / d_c) ** (-a)
    return math.sqrt(max(g, 0.0))


def reform_relief(d_c, length, gamma_start=GAMMA_B, k_dally=K_DALLY,
                  gamma_s=GAMMA_STABLE, d_max=60.0):
    """Invert `reform_ratio`: the crest-to-trough relief that un-breaks the wave.

    Bisection on d_t, because the closed form is monotone in it and inverting it
    algebraically buys nothing. Returns the relief in metres.
    """
    lo, hi = d_c + 1e-6, d_max
    if reform_ratio(d_c, hi, length, gamma_start, k_dally, gamma_s) > gamma_s:
        return float('inf')
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if reform_ratio(d_c, mid, length, gamma_start, k_dally, gamma_s) > gamma_s:
            lo = mid
        else:
            hi = mid
    return hi - d_c


def crest_depth_ratio(tr, cr, b, field='wave'):
    """Chapter 12's `d_bar ~ H_b/gamma`, evaluated in ONE depth field.

    WAVE 1 REPORTED 0.893 FOR THIS AND CALLED THE SHORTFALL A PREDICTION. It is
    not one. `H_b` and `d_b` are outputs of the transform, which reads the
    wavelength-filtered depth; `cr['d']` is the RAW bed. On an 11 m crest the
    1.5 m filter lifts the depth the wave feels by 0.19 m, and the whole of the
    0.893 is that one comparison straddling two fields:

        field='bed'   raw bed depth at the crest / (H_b/gamma)   0.893
        field='wave'  the depth the wave broke in / (H_b/gamma)  0.973

    and on a 0.25 m grid, where the filter is 0.375 m instead of 1.5 m, the
    'bed' form climbs to 0.971 while the 'wave' form does not move. The relation
    is met to 1-3%; the trend across sea states that wave 1 offered as
    falsifiable (0.81 to 0.97 as H_0 rises from 1 to 3 m) is the same artefact
    seen along a different axis -- a bigger bar is broader, so a fixed filter
    takes proportionally less off its crest.

    THE COMPARISON LIVES HERE AND NOT IN THE SUITE on purpose. Wave 1's own
    `--bugs` table found that a row which computes both sides of its check is
    testing itself; this function is what `--bug crest-depth-mixed-fields`
    patches, so the guard has something to catch.
    """
    d_pred = b['H_b'] / GAMMA_B
    d = cr['d'] if field == 'bed' else float(tr['d'][cr['i']])
    return d / d_pred


def _reform_length(d_c, relief, gamma_start=GAMMA_B, k_dally=K_DALLY,
                   gamma_s=GAMMA_STABLE, l_max=1000.0):
    """The other inversion: hold the relief, find the back-slope LENGTH that
    un-breaks the wave. Monotone the same way, bisected the same way."""
    lo, hi = 1e-3, l_max
    if reform_ratio(d_c, d_c + relief, hi, gamma_start, k_dally, gamma_s) > gamma_s:
        return float('inf')
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if reform_ratio(d_c, d_c + relief, mid, gamma_start, k_dally,
                        gamma_s) > gamma_s:
            lo = mid
        else:
            hi = mid
    return hi


def dally_efoldings(d_c, d_t, length, k_dally=K_DALLY):
    """How many e-foldings of the Dally decay the back of the bar delivers.

    The model's decay rate is K/d per metre of x, so the count is the integral
    of K/d over the back slope -- in closed form for a straight slope,

        N = (K/m) * ln(d_t/d_c)                 with m = (d_t-d_c)/length

    which is the SAME K/m that sits in `reform_ratio`'s exponent. It is the
    natural currency for "how far short is this bar", and the number this scene
    turns out to be short in.
    """
    m = (d_t - d_c) / max(length, 1e-9)
    if m <= 0.0:
        return 0.0
    return (k_dally / m) * math.log(d_t / d_c)


def breaking_fraction_bj(tr, gamma_b=GAMMA_B):
    """Battjes & Janssen (1978)'s fraction of breaking waves Q_b, as a field.

    The transform above is monochromatic, and section B's photograph is not: a
    real sea is a distribution, and what a camera records as "a breaking line"
    is a large FRACTION of waves breaking, not one wave crossing an index. The
    standard closure is Battjes & Janssen's clipped Rayleigh,

        (1 - Q_b) / ln(Q_b) = -(H_rms/H_m)^2,     H_m = gamma_b * d in shallow
                                                        water

    solved here by bisection. `tr['H']` is read as H_rms, which is the reading
    the energy already carries: E = rho g H^2/8 IS the rms convention.

    THIS IS A DIAGNOSTIC AND IT DOES NOT RESCUE SECTION B -- which is why it is
    here rather than quietly replacing the criterion. Q_b on this scene goes
    1.00 over the bar and 0.06 in the trough, so the CONTRAST the photograph
    shows is there; but it stays near 0.06 all the way to the shore, so there is
    still no second line. Reported, measured, and not used as a pass.
    """
    d = np.maximum(tr['d'], D_MIN)
    ratio = np.clip(tr['H'] / (gamma_b * d), 1e-6, 1.0)
    out = np.zeros_like(d)
    for i in range(d.size):
        r2 = ratio[i] ** 2
        if r2 >= 1.0 - 1e-9:
            out[i] = 1.0
            continue
        lo, hi = 1e-12, 1.0 - 1e-12
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if (1.0 - mid) / math.log(mid) > -r2:     # too little breaking
                lo = mid
            else:
                hi = mid
        out[i] = 0.5 * (lo + hi)
    return out


def probe_back_slope(x, h, h_ref, i_crest, length, relief, rejoin=60):
    """A DIAGNOSTIC BED, and it is never the scene's.

    Takes the loop's own bed seaward of the crest and replaces everything
    landward of it with a straight back slope of the stated `length` and
    `relief`, rejoining the reference ramp over `rejoin` metres. It exists to
    ask the transform one question -- *given* a trough of these dimensions, does
    the wave un-break? -- and it answers it without touching the bathymetry the
    scene ships, which is a computed field and stays one.

    The suite uses it twice: to prove the transform HAS the memory the reform
    needs (hand it a wide enough trough and it reforms), and to locate the
    boundary in (relief, length) that the loop's own bar falls short of.
    """
    hh = np.asarray(h, float).copy()
    h_ref = np.asarray(h_ref, float)
    d_c = -hh[i_crest]
    n = hh.size
    for j in range(int(length) + 1):
        if i_crest + j < n:
            hh[i_crest + j] = -(d_c + relief * j / max(length, 1))
    i0 = i_crest + int(length)
    for j in range(1, rejoin + 1):
        if i0 + j < n:
            f = j / float(rejoin)
            hh[i0 + j] = (1.0 - f) * (-(d_c + relief)) + f * h_ref[i0 + j]
    if i0 + rejoin + 1 < n:
        hh[i0 + rejoin + 1:] = h_ref[i0 + rejoin + 1:]
    return hh


# ------------------------------------------------------ sediment and beach state
def settling_velocity(d50=D50, rho_s=RHO_S, rho_w=RHO_SW, nu=NU_W):
    """Soulsby (1997) for natural sand, quoted from COHERENS chapter 7 (7.41):

        w_s = (nu/d) * [ sqrt(10.36^2 + 1.049*D*^3) - 10.36 ]
        D*  = d * [ g*(s-1)/nu^2 ]^(1/3),   s = rho_s/rho_w

    Chapter 12 asks for exactly this and says so: "`04` carries the grain sizes
    but not w_s itself, so the settling law is yours to state". Stated, and
    cited to a source read this wave rather than to memory.

    The suite checks it against the Stokes limit (where it must agree, because
    both describe the same slow sphere) and against the drag-crisis-free
    turbulent limit, which are two closed forms it was not written from.
    """
    s = rho_s / rho_w
    d_star = d50 * (G * (s - 1.0) / nu ** 2) ** (1.0 / 3.0)
    return (nu / d50) * (math.sqrt(10.36 ** 2 + 1.049 * d_star ** 3) - 10.36)


def dimensionless_fall_velocity(H_b, w_s, T):
    """Omega = H_b/(w_s*T), Wright & Short (1984), via chapter 12's table:
    Omega < 1 reflective (no bar), 1-6 intermediate (the bar-rip family),
    > 6 dissipative (multiple shore-parallel bars, no discrete rips)."""
    return H_b / (w_s * T)


def beach_state(omega):
    if omega < 1.0:
        return 'reflective'
    if omega <= 6.0:
        return 'intermediate'
    return 'dissipative'


# ---------------------------------------------------------- Iribarren & run-up
def iribarren(tan_beta, H, L):
    """xi = tan(beta) / sqrt(H/L). Cited to 12-water-rendering: "the
    surf-similarity (Iribarren) number xi = tan(beta)/sqrt(H/L_0)".

    WHICH H AND WHICH L, and this is the same trap family as the factor of two:
    xi_0 is built from DEEP-WATER H_0 and L_0, xi_b from the values AT BREAKING.
    They are different numbers and the published thresholds differ with them --
    see `breaker_class` below."""
    return tan_beta / math.sqrt(H / L)


def breaker_class(xi, which='deep'):
    """Breaker type from the Iribarren number.

    TWO THRESHOLD SETS WERE FOUND THIS WAVE AND THEY DO NOT AGREE:

      * xi < 0.5 spilling / 0.5-3.3 plunging / > 3.3 surging  -- attributed to
        Battjes (1974) in the general literature, in DEEP-WATER xi_0.
      * xi < 0.4 spilling / 0.4-2 plunging / > 2 surging      -- Coastal Wiki,
        "Surf similarity parameter", also attributed to Battjes (1974), written
        with the LOCAL (breaking) slope and height.

    Neither source is wrong: the constant travels with the quantities it is
    paired with, exactly like E_0/4 versus E_b/2. This file therefore refuses to
    carry ONE table -- it takes `which` and says which convention it answered in.
    Chapter 12 names the classes but no thresholds, so there is nothing to
    contradict.
    """
    if which == 'deep':
        lo, hi = 0.5, 3.3
    elif which == 'local':
        lo, hi = 0.4, 2.0
    else:
        raise ValueError(which)
    return ('spilling' if xi < lo else
            'plunging' if xi < hi else 'surging/collapsing')


def runup_hunt(H, xi):
    """Hunt (1959): R ~ H*xi, valid for 0.1 < xi < 2.3.

    Quoted from Coastal Wiki, "Surf similarity parameter": 'According to Hunt
    (1959), "R ~ Hs xi" applies within the range "0.1 < xi < 2.3"'.

    `?` ON THE CONSTANT OF PROPORTIONALITY. The relation as published is a
    SCALING; the coefficient depends on which run-up level (mean, 2%, maximum)
    and which H (H_s, H_0) is meant, and no source read this wave pinned it. So
    this returns H*xi and the caller must treat it as "the scale of the run-up",
    not "the run-up". Run-up RENDERING is out of scope this wave in any case:
    what is reported is the scaling and the number it gives.
    """
    return H * xi


# ==================================================== THE SUBAERIAL BEACH
#
# WAVE 8. Waves 1-3 built the whole nearshore and stopped at the datum: the
# Dean ramp is submarine, the coastal loop's deposition capacity ran from
# `sea_level - 3.0` up to `sea_level` and not one centimetre above it, and the
# comment beside it said so outright -- "a beach does not build above the water
# line here, and the excess LEAVES THE DOMAIN". It leaves at 90.0% of the sand
# eroded. So the beach scene had a 6 m strip of land between the water and a
# cliff face of slope 1.0, and `shade_land` classified it as ROCK. Bar J's
# five-rung colour ladder had three rungs.
#
# THREE NUMBERS MAKE A SUBAERIAL BEACH AND EACH ONE IS DERIVED FROM SOMETHING
# THIS FILE ALREADY OWNS. None of them is chosen and none of them is new.
#
#   1  the FACE SLOPE      the equilibrium profile's own slope where it stops
#                          being solvable                    `beach_face_slope`
#   2  the SWASH EXCURSION the horizontal reach of the run-up, and it does not
#                          depend on the slope                `swash_excursion`
#   3  the RUN-UP LIMIT    the elevation the swash builds to      `berm_crest`
#
# and 2 = 3/1 identically, which is the check that the three are one statement
# rather than three declarations. Written out: Hunt's R = xi*H with
# xi = tan(beta)/sqrt(H/L_0) is R = tan(beta)*sqrt(H*L_0), so the horizontal
# excursion R/tan(beta) is sqrt(H*L_0) and the slope cancels. THE WIDTH OF THE
# DRY BEACH IS THE GEOMETRIC MEAN OF THE DEEP-WATER HEIGHT AND WAVELENGTH,
# closed form, no constant, and it is 13.77 m at this scene's swell against the
# 6.0 m of leftover the bed had before.

def beach_face_slope(A=DEAN_A, d_hand=D_MORPH_MIN):
    """tan(beta) of the beach face: the equilibrium profile's slope where the
    surf-zone model hands over to the swash.

    THE DEAN PROFILE HAS NO SHORELINE SLOPE, and that is why a beach face is a
    separate landform rather than the last few metres of the same curve.
    d = A*y^(2/3) has dd/dy = (2/3)*A*y^(-1/3), which DIVERGES at y = 0; the
    profile is derived from uniform energy dissipation per unit water volume
    and there is no water volume at the shoreline for the dissipation to be
    uniform in. So the face is a straight ramp and what fixes its angle is
    WHERE the equilibrium profile stops answering.

    This file already states where that is. `D_MORPH_MIN` gates the Exner step
    to water deeper than 0.35 m, with the reason written beside it: "the bed
    inside the swash is shaped by swash, which is not modelled here, so the
    loop is not allowed to invent an answer for it". That is a statement about
    the physics and not only about the numerics, and it is the handover depth.
    The face is the tangent to the equilibrium profile there:

        y_0 = (d/A)^(3/2)          tan(beta) = (2/3) A^(3/2) / sqrt(d)

    = 0.05282 at this scene, 1:18.9, which is an ordinary intermediate sandy
    beach face.

    AND IT IS NOT ONLY A CLOSED FORM -- THE EVOLVED BED AGREES. The 1-D
    morphodynamic loop is run to quasi-steady from a Dean ramp and reshaped by
    the transport all the way in; its own slope at the innermost cell it
    resolves is 0.0529 against the 0.0528 above, 0.2% apart. Two instruments,
    one derived and one run, and the second could have disagreed: the bar the
    loop builds is a 0.4 m departure from the ramp 100 m offshore.

    THE HANDOVER DEPTH IS THE ONE SOFT PLACE AND IT IS BRACKETED RATHER THAN
    ASSERTED. tan(beta) goes as 1/sqrt(d): 0.0988 (1:10) at the transform's own
    depth floor D_MIN = 0.10 m, 0.0528 (1:19) at D_MORPH_MIN, 0.0312 (1:32) at
    1 m. That factor of three IS the observed range of sandy beach faces, so
    the bracket is honest and the mid value is not a coincidence -- but a
    reader should know that this quantity is the softest of the three.

    THE ROUTE THIS FILE ALREADY HAD DOES NOT WORK, and saying so matters.
    `EPS_SLOPE`'s own comment gives the Bailard equilibrium slope as Sk/eps --
    "the slope at which gravity balances the skewness drive". Evaluated in the
    swash it is ZERO: the skewness carries a (1 - f_brk) factor, the inner surf
    is fully broken, and the model's equilibrium there is a flat terrace.
    Measured at the six innermost resolved cells: 0.148, 0.128, 0.067, 0, 0, 0.
    That is the transport model saying it has no swash, which is exactly what
    `D_MORPH_MIN` says, and it is why the slope is taken from the profile
    rather than from the flux.
    """
    y0 = (d_hand / A) ** 1.5
    return (2.0 / 3.0) * A / y0 ** (1.0 / 3.0)


def swash_excursion(H=H0_SWELL, T=T_SWELL):
    """sqrt(H*L_0) -- the horizontal reach of the run-up, INDEPENDENT of the
    beach slope.

    Hunt's R = xi*H with xi = tan(beta)/sqrt(H/L_0) is linear in tan(beta), so
    the horizontal distance R/tan(beta) has the slope divided out of it. It is
    the width of the dry beach a given swell builds, and it needs nothing but
    the deep-water sea state. 13.77 m at H_0 = 1.5 m, T = 9 s; 19.47 m at the
    file's own storm, H_0 = 3.0 m.

    `?` INHERITED, NOT NEW: it carries `runup_hunt`'s unstated coefficient, so
    it is the SCALE of the excursion. Nothing here adds an unknown.
    """
    return math.sqrt(H * deep_wavelength(T))


def berm_crest(H=H0_SWELL, T=T_SWELL, tan_beta=None):
    """The elevation the swash builds to: R = tan(beta)*sqrt(H*L_0).

    Hunt's run-up is measured from the STILL-WATER line and already contains
    the set-up, so no set-up term is added here -- adding one would count the
    same rise twice. 0.727 m for the swell, 1.029 m for the storm.
    """
    tb = beach_face_slope() if tan_beta is None else tan_beta
    return tb * swash_excursion(H, T)


TAN_FACE = beach_face_slope()           # 0.052823, 1:18.9
BERM_Z = berm_crest()                   # 0.7274 m -- the SWELL run-up limit
BACKSHORE_Z = berm_crest(H0_STORM)      # 1.0286 m -- the STORM run-up limit
SWASH_W = swash_excursion()             # 13.771 m -- the dry beach's width
BACKSHORE_W = swash_excursion(H0_STORM)  # 19.474 m


# ---------------------------------------------------------------------------
# WAVE 12: THE `?` IN `runup_hunt` IS CLOSED, BY CONSEQUENCE RATHER THAN BY A
# CITATION -- and closing it moves the wet band by a factor of two.
#
# `runup_hunt` says outright that Hunt's R is a SCALING and that "the
# coefficient depends on which run-up level (mean, 2%, maximum)". Waves 4-11
# then read `BERM_Z` as the RAYLEIGH SCALE of the run-up distribution:
# `swash_wetness` was exp(-(z/BERM_Z)^2), which says 36.8% of swash cycles
# exceed 0.727 m. If 0.727 m is instead the 2% level -- which is what modern
# run-up practice means by Hunt's R -- then the Rayleigh scale is
#
#       sigma = R_2% / sqrt(ln 50) = R_2% / 1.9781 = 0.3677 m
#
# and the band is 1.978x shorter. The two readings are not both available,
# because the file's OWN three-number identity decides between them, and the
# argument needs no photograph:
#
#   THE INSTANTANEOUS DAMP LIMIT IS A MAXIMUM, NOT A MEAN. Sand darkened by
#   pore water stays dark until the pores drain, which is minutes against a
#   9 s period. So at any instant the beach is damp up to the HIGHEST run-up of
#   the last N = tau_dry/T cycles, and the maximum of N Rayleigh variates sits
#   at sigma*sqrt(ln N).
#
#   Read sigma = BERM_Z: with N = 33 the damp limit is 1.36 m. The beach these
#   same closed forms build tops out at BACKSHORE_Z = 1.029 m. The whole beach
#   is damp at every instant and this coast can have NO DRY SAND AT ALL -- and
#   the bed's own dry beach, which `beach_width` measures at 12 m, would be a
#   surface the shader can never paint dry.
#
#   Read sigma = BERM_Z/1.978: the damp limit is 0.688 m against a berm at
#   0.727 m and a backshore at 1.029 m. Wet face, dry backshore, boundary just
#   below the berm -- which is what `subaerial_beach`'s own docstring already
#   asserts ("a marked berm LEVEL at 0.727 m where the wet/dry boundary sits")
#   and what waves 4-11 could not produce.
#
# So the `?` is resolved by SELF-CONSISTENCY inside the file's own identity,
# and the resolution is reported as such: it is not a citation and it is not a
# fit to a frame. The suite fires `--bug runup-scale-as-rms` at it.
RUNUP_QUANTILE = 0.02        # Hunt's R read as the 2% run-up. See above.
SWASH_TAU_DRY = 300.0        # s, how long sand stays visibly damp after the
                             # swash leaves it. `?` -- no measurement of the
                             # drainage/evaporation time of a medium-sand beach
                             # face was available and the standing ruling
                             # forbids fitting one to a photograph. It enters
                             # ONLY as sqrt(ln(tau/T)), so the bracket below is
                             # a factor of 30 and moves the damp limit by 1.38
                             # to 2.30 sigma -- a factor of 1.7 on a quantity
                             # the mean-wetness model got wrong by 2.0. The
                             # suite reports the bracket rather than hiding it.
SWASH_TAU_BRACKET = (60.0, 1800.0)


def swash_scale(R=None, quantile=None):
    """The RAYLEIGH SCALE sigma of the run-up, from Hunt's R read as R_q.

    P(run-up > R_q) = q = exp(-(R_q/sigma)^2)  ->  sigma = R_q/sqrt(-ln q).
    One line, and it is the only place the reading of Hunt's R enters.

    `quantile` is resolved from the module at CALL time and not bound as a
    default, so the suite's `--bug runup-scale-as-rms` can put waves 4-11's
    reading back by setting the constant. A default argument would have frozen
    it at import and the bug would have caught nothing -- which is how the
    first writing of this function shipped, and the `--bugs-bathy` table is
    what said so.
    """
    R = BERM_Z if R is None else R
    q = RUNUP_QUANTILE if quantile is None else quantile
    return R / math.sqrt(-math.log(q))


def swash_wetness(z, R=None):
    """The share of swash cycles that reach elevation `z`: exp(-(z/sigma)^2).

    THE WET/DRY BOUNDARY IS NOT A LINE AND THE FILE ALREADY OWNS THE
    DISTRIBUTION. Run-up heights inherit the incident wave heights' statistics,
    which this file has taken as Rayleigh since wave 1 (`rayleigh_quantiles`,
    used for the storm forcing). The exceedance of a Rayleigh variate of scale
    sigma is exp(-(z/sigma)^2).

    THIS IS A DISTRIBUTION AND NOT A SURFACE, AND THAT DISTINCTION IS THE WHOLE
    OF WAVE 12'S SECOND FINDING. It is the right answer to "what share of the
    time is this level swept"; it is the WRONG object to paint, because a
    renderer that blends wet albedo into dry by this fraction draws the
    TIME-AVERAGE of the beach and not the beach. The average has no edge. Bar
    H3 calls the waterline "one of the strongest tonal edges in these frames",
    and an average cannot have one however correct its statistics are. What the
    shader wants is `damp_limit` below -- a REALISATION -- and this function is
    what that realisation is drawn from.

    `sigma` is `swash_scale`, i.e. Hunt's R read as R_2%; see the block above.
    """
    s = swash_scale(R)
    return np.exp(-(np.maximum(np.asarray(z, float), 0.0) / s) ** 2)


def swash_cycles(T=T_SWELL, tau=None):
    """How many swash cycles the sand remembers: N = tau_dry/T."""
    tau = SWASH_TAU_DRY if tau is None else tau
    return max(float(tau) / float(T), 1.0)


def damp_exceedance(z, R=None, T=T_SWELL, tau=None):
    """P(the surface at `z` is damp) = 1 - (1 - exp(-(z/sigma)^2))^N.

    The probability that AT LEAST ONE of the last N run-ups reached `z`. Still
    a distribution -- it is the cdf of the realisation `damp_limit` draws --
    and it is here so the suite can check the realisation against it without
    rebuilding either from the other.
    """
    p = swash_wetness(z, R)
    return 1.0 - (1.0 - p) ** swash_cycles(T, tau)


def damp_limit_median(R=None, T=T_SWELL, tau=None):
    """The median of the N-cycle run-up maximum, in metres: the level the
    wet/dry edge sits at. sigma*sqrt(-ln(1 - 2^(-1/N)))."""
    n = swash_cycles(T, tau)
    return swash_scale(R) * math.sqrt(-math.log1p(-0.5 ** (1.0 / n)))


def _splitmix01(k, seed):
    """A uniform in (0, 1) from an INTEGER LATTICE INDEX. SplitMix64's
    finaliser, which is a hash and not a stream.

    THE POINT IS THAT IT IS INDEXED AND NOT SEQUENTIAL. `default_rng(seed)`
    gives the n-th node the n-th draw, so the value at a node depends on where
    the caller started counting -- and `shade_land` is handed only the LAND
    pixels of one camera, so its span is not the bed's and not the next
    camera's. The waterline would then move when the camera did. A hash of the
    node's own index cannot: node k is the same draw for every caller.
    """
    with np.errstate(over='ignore'):        # wraparound IS the arithmetic here
        k = np.asarray(k, np.int64).astype(np.uint64)
        z = (k + np.uint64(seed) * np.uint64(0x9E3779B97F4A7C15)
             ).astype(np.uint64)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        z = z ^ (z >> np.uint64(31))
        return (z >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def _swash_lattice(y, lam=None):
    """The alongshore lattice the run-up realisation is drawn on: node indices
    and their positions, ANCHORED AT y = 0 so the lattice is a property of the
    coast rather than of the caller's slice.

    THE SPACING IS NOT DECLARED. A swash edge is not straight, and what makes
    it not straight is beach cusps, whose spacing is set by the swash excursion
    itself (Werner & Fink 1993's self-organisation argument; the relation
    quoted everywhere is spacing ~ the horizontal swash excursion). This file
    already owns that excursion as `SWASH_W` = R/tan(beta), so the alongshore
    correlation length of the run-up realisation is that and nothing new.
    `?` on the constant of proportionality, which is taken as 1.
    """
    lam = SWASH_W if lam is None else lam
    y = np.asarray(y, float)
    k0 = int(math.floor(float(np.min(y)) / lam)) - 1
    k1 = int(math.ceil(float(np.max(y)) / lam)) + 1
    k = np.arange(k0, k1 + 1)
    return k, k * lam


def damp_limit(y, R=None, T=T_SWELL, tau=None, seed=20260818, lam=None):
    """ONE REALISATION of the damp limit, in metres, per alongshore position.

    THE SHADER MUST DRAW A SAMPLE AND NOT A MEAN, and this is the third place
    in this project where that same sentence turned out to be the defect: the
    optics lane found the render drawing the ensemble mean of the glint
    distribution instead of its samples, the wave-field lane found the foam
    drawn as its own mean, and here the wet/dry boundary was drawn as the
    time-average of the swash. All three are the same mistake and all three
    read as "smooth where the photograph is sharp".

    The maximum of N iid Rayleigh(sigma) variates has cdf F(z)^N with
    F(z) = 1 - exp(-(z/sigma)^2), so a uniform u inverts to

        z = sigma * sqrt(-ln(1 - u^(1/N)))

    drawn on the cusp lattice above and linearly interpolated between nodes, so
    the edge has the alongshore correlation the swash gives it and no power
    below it. Deterministic in `seed`: this is a property of the SURFACE, so
    two cameras looking at the same beach must see the same waterline.
    """
    ys, z = _damp_nodes(y, R=R, T=T, tau=tau, seed=seed, lam=lam)
    return np.interp(np.asarray(y, float), ys, z)


def _damp_nodes(y, R=None, T=T_SWELL, tau=None, seed=20260818, lam=None):
    """The damp limit AT THE LATTICE NODES. Its own function so `sheet_front`
    can condition on exactly the nodes `damp_limit` interpolates between --
    rebuilding the lattice from a different span offsets it by one cell and the
    sheet then pokes through the damp band by a few centimetres, which is the
    kind of near-miss a `<=` row catches and a picture does not."""
    n = swash_cycles(T, tau)
    s = swash_scale(R)
    k, ys = _swash_lattice(y, lam)
    u = np.clip(_splitmix01(k, seed), 1e-12, 1.0 - 1e-12)
    return ys, s * np.sqrt(-np.log1p(-u ** (1.0 / n)))


def sheet_front(y, R=None, phase=0.5, seed=20260819, lam=None):
    """The free-water SHEET's front, in metres, at one instant of one cycle.

    TWO MASKS AND NOT ONE, because they are two different substances. The
    trapped series bar H3 invokes is light re-emerging from a wetted GRAIN
    PACK -- pore water, which stays for `SWASH_TAU_DRY` -- and it darkens.
    A specular lobe needs FREE WATER standing on the surface, which is the
    swash sheet, and the sheet is on a level only while the front is above it.
    Waves 4-11 drove both from one field, which puts a mirror on damp sand:
    measured on the wave-10 hero frame, the specular term was 1.28 against a
    diffuse term of 1.39 over 3.19% of the whole frame, and it is what inverts
    bar J's wet/dry rung.

    The front's own trajectory is ballistic -- the uprush decelerates under
    gravity along the face -- so a cycle whose run-up is z_r puts the front at

        z_s = z_r * (1 - (1 - 2 phi)^2),    phi in [0, 1]

    which is 0 at both ends and z_r at mid-cycle. `phase` is the instant the
    frame is taken at and it is `?`: the offset between the wave field's phase
    and the swash's is the bore's travel time across the surf zone, which this
    model does not carry. 0.5 -- maximum uprush -- is shipped and the suite
    checks the sheet is bounded by the damp limit at EVERY phase, which is the
    statement that does not depend on the choice.

    THE SHEET CANNOT OUTRUN THE DAMP BAND, and it is drawn so that it cannot
    rather than clipped so that it does not. This cycle is ONE OF THE N whose
    maximum is `damp_limit`, so its run-up is Rayleigh CONDITIONED on being at
    most that maximum: u_cycle = v * F(z_damp) with v uniform. The bound
    z_sheet <= z_damp then holds identically, at every phase and every seed,
    which is what makes it a row the suite can assert exactly.
    """
    s = swash_scale(R)
    ys, z_d = _damp_nodes(y, R=R, lam=lam)
    F = 1.0 - np.exp(-(z_d / s) ** 2)                   # the truncation point
    k, _ = _swash_lattice(y, lam)
    v = _splitmix01(k, seed)
    z_r = s * np.sqrt(-np.log1p(-np.clip(v * F, 0.0, 1.0 - 1e-15)))
    f = max(0.0, 1.0 - (1.0 - 2.0 * float(phase)) ** 2)
    return np.interp(np.asarray(y, float), ys, z_r) * f


def subaerial_beach(x, h2, h_rock=None, sea_level=None, tan_face=None,
                    berm=None, backshore=None, sand_row=None, dy=None):
    """Lay the beach the coastal loop's own erosion paid for, per row.

    THE PROFILE IS THREE SEGMENTS AND TWO OF THE JOINS ARE DERIVED:

        the FACE        a straight ramp at tan(beta) from the waterline
                        landward, `swash_excursion` metres of it
        the BERM LEVEL  z = BERM_Z, the swell's run-up limit. It is a level on
                        the face and NOT a break in slope -- see below
        the BACKSHORE   flat at the STORM run-up limit, from the storm swash's
                        landward limit to the cliff foot

    WHY THE BERM CREST IS NOT A BREAK IN SLOPE, AND THIS CONTRADICTS THE
    ORDINARY PICTURE OF A BEACH. Hunt's run-up with one face slope puts EVERY
    run-up limit on the SAME PLANE -- R = tan(beta)*sqrt(H*L_0), so the swell's
    limit and the storm's limit differ only in how far up that one plane they
    reach. A berm crest is a break in slope, and a break in slope needs the
    swell to CUT the storm-built profile, which needs swash transport this
    model does not have. So what this bed carries is a face, a marked berm
    LEVEL at 0.727 m where the wet/dry boundary sits, and a flat backshore at
    1.029 m. THE BERM SCARP IS `?` and it is absent, not approximated.

    THE ANCHOR IS THE CLIFF FOOT AND THE BEACH PROGRADES SEAWARD FROM IT. On
    this coast the cliff comes down to the water at a slope of 1.2, so a wedge
    built landward of the present waterline has nowhere to go -- the basement
    crosses the run-up limit within 60 cm of the shoreline and the capacity is
    zero. A beach on a cliffed coast is a body of sand standing SEAWARD of the
    cliff, and its landward limit is where the rock reaches the backshore
    elevation. That is what is built here.

    THE VOLUME IS CHECKED AND IT IS NOT WHAT LIMITS THE WIDTH. Each row is
    given `sand_row` cubic metres (the loop's own eroded volume times
    `SAND_FRACTION`, the part it currently exports) and the wedge needs about
    35 m^3 per metre of coast; the loop delivers about 1900. So the width is
    set by the PROFILE GEOMETRY -- where the face meets the equilibrium ramp --
    and the budget is a check that passes with two orders to spare rather than
    a knob. Which of the two binds is returned as `supply_limited`.

    WHAT IS PLACED, MARKED: this is applied at COMPOSITION time, in `bay_bed`,
    and not inside `coastal_step`'s iteration. Inside the iteration the beach
    moves the waterline the notch attacks and the cliff stops retreating -- a
    real feedback (a beach protects a cliff) and a wave of its own, because it
    changes the plan-form every suite row in `_sec_coast` is measured on. The
    budget is the loop's, the slope is the profile's, the elevations are the
    run-up's; the ITERATION is not closed and this note is the mark.
    """
    x = np.asarray(x, float)
    h = np.asarray(h2, float).copy()
    rock = h.copy() if h_rock is None else np.asarray(h_rock, float)
    # SEA_LEVEL is declared with the coastal loop's own constants, further down
    # the file than this function is defined, so it is resolved at CALL time.
    sea_level = SEA_LEVEL if sea_level is None else sea_level
    tb = TAN_FACE if tan_face is None else tan_face
    zb = BERM_Z if berm is None else berm
    zs = BACKSHORE_Z if backshore is None else backshore
    dx = float(x[1] - x[0])
    ny, nx = h.shape
    # THE CLIFF FOOT: walking SEAWARD from the landward edge, the last cell
    # whose rock is still above the backshore elevation. Same walk as
    # `shoreline_x` and for the same reason -- a bench poking above the datum
    # offshore must not be mistaken for the coast.
    above = rock > (sea_level + zs)
    run = np.cumprod(above[:, ::-1], axis=1)[:, ::-1].astype(bool)
    i_foot = np.argmax(run, axis=1)
    i_foot = np.where(run.any(axis=1), i_foot, nx - 1)
    # the storm-swash plane, descending seaward from the cliff foot
    dist = (x[i_foot][:, None] - x[None, :])            # >0 seaward
    plane = (sea_level + zs) - tb * np.maximum(dist, 0.0)
    plane = np.where(dist >= 0.0, plane, sea_level + zs)  # flat landward: none
    fill = np.maximum(plane - rock, 0.0) * (dist >= 0.0)
    need_row = fill.sum(axis=1) * dx                    # m^3 per metre of coast
    if sand_row is not None and dy:
        have = np.asarray(sand_row, float) / float(dy)  # m^3 per metre
        frac = np.clip(np.where(need_row > 1e-12, have / np.maximum(need_row,
                                                                    1e-12),
                                0.0), 0.0, 1.0)
    else:
        frac = np.ones(ny)
    h = rock + frac[:, None] * fill
    z = h - sea_level
    on = (fill > 1e-6) & (frac[:, None] > 0.0)
    wid = ((z > 0.0) & on).sum(axis=1) * dx
    return dict(h=h, h_rock=rock, plane=plane, sand=frac[:, None] * fill,
                i_foot=i_foot,
                need_row=need_row, frac=frac, width=wid,
                supply_limited=bool((frac < 0.999).any()),
                tan_face=tb, berm=zb, backshore=zs)


def sand_cover_fraction(reg, sigma_r=None, n_iter=48):
    """What share of a rough rock surface a sand veneer of MEAN depth `reg`
    actually covers.

    BAR SECTION H1 IS A CLOSED FORM AND WAVE 12 IS WHERE IT GETS ONE. The bar
    photographs the bench as "deeply pocketed, with sand infilling the hollows
    and dark weed on the wet rock", and calls that "a landform with a formation
    mechanism, not scenery". A renderer that decides rock-versus-sand by SLOPE
    -- which is what `beach_render.shade_land` did through wave 11 -- cannot
    produce it: the bench is FLAT, so a slope test calls the whole of it sand
    and the photograph's defining surface never appears. Chapter 11 gives the
    right test outright and this file was not using it:

        Outcrop = rockMask from (slope > tan 40 deg) u (regolithDepth ~ 0)
                  u (convex curvature).  "Emerges automatically if you run
                  layered K -- you don't author it."

    The regolith clause is the one that fires on a bench, and the loop already
    computes the regolith: it is the sand wedge `bay_bed` lays over the planed
    rock. What is missing is the MAP from a mean depth to a covered AREA, and
    the two are not the same number on a rough surface -- which is the whole of
    "sand INFILLING THE HOLLOWS".

    THE FORM. Let the rock surface inside one cell have elevation z ~ N(0,
    sigma_r) about its own mean, and let sand pond to a level l. Then

        covered area fraction    f = Phi(u),        u = l / sigma_r
        mean sand depth          reg = sigma_r * (phi(u) + u * Phi(u))

    -- the second is E[(l - z)+] for a Gaussian, and it is the volume book,
    not a fit. So `reg` fixes `u` and `u` fixes `f`, with nothing left over.
    d/du (phi + u Phi) = Phi(u), so Newton on it converges from any start and
    the routine is exact to round-off rather than tabulated.

    WHAT IT PREDICTS, AND IT IS FALSIFIABLE: a veneer whose mean depth EQUALS
    the rock's own roughness covers 81.6% of the area, not 100%; a fifth of the
    surface is still bare rock standing through it. Half a roughness covers
    57.5% and a quarter covers 36.5%. That non-linearity IS the pocketed bench,
    and a linear "sand if reg > 0" test produces a clean edge where the
    photograph has an interfinger. Measured on this scene's own bench (planed
    rock within 2.5 m of the datum): median regolith 0.167 m against
    ROCK_ROUGH = 0.25 m, so 48% of the bench reads bare rock and 52% sand --
    two surfaces on one landform, out of the volume book and nothing else.

    `sigma_r` IS SUB-GRID AND SAYS SO. The loop's cells are 4 x 16 m and bar
    H1's pockets are metres across, so the roughness this integral is taken
    over is BELOW the representation -- the same statement chapter 12 makes
    about arches and this file makes about the plunging lip, and it is why the
    quantity enters as a distribution rather than as geometry. `ROCK_ROUGH` is
    its scale, declared `?`, and swept in the suite.
    """
    sigma_r = ROCK_ROUGH if sigma_r is None else float(sigma_r)
    r = np.maximum(np.asarray(reg, float), 0.0) / max(sigma_r, 1e-9)
    # bisection: g(u) = phi(u) + u Phi(u) is strictly increasing, g(-8) ~ 1e-16
    lo = np.full(r.shape, -8.0)
    hi = np.maximum(r + 1.0, 1.0)
    for _ in range(int(n_iter)):
        mid = 0.5 * (lo + hi)
        P = 0.5 * (1.0 + _erf(mid / math.sqrt(2.0)))
        g = np.exp(-0.5 * mid * mid) / math.sqrt(2.0 * math.pi) + mid * P
        lo = np.where(g < r, mid, lo)
        hi = np.where(g < r, hi, mid)
    u = 0.5 * (lo + hi)
    return 0.5 * (1.0 + _erf(u / math.sqrt(2.0)))


# ------------------------------------------------- the pockets, as a SURFACE
#
# WAVE 12, AND IT IS THE SAME SENTENCE AS THE WET/DRY BOUNDARY ABOVE.
# `sand_cover_fraction` is the right closed form and the wrong object to paint.
# `beach_render.shade_land` took its answer -- an AREA FRACTION -- and used it
# as a blending coefficient: `bare = planed * (1 - cover)`. That draws the
# expectation of a binary spatial mask, which is a wash of intermediate rock,
# and bar H1's word for what it should be is POCKETED. A quarter of a bench
# standing through a veneer is a quarter of its AREA in pockets, not every
# square metre being one-quarter rock.
#
# The realisation needs one thing the closed form does not: the SCALE of the
# pockets. `sand_cover_fraction`'s own note says the roughness is sub-grid --
# "the loop's cells are 4 x 16 m and bar H1's pockets are metres across" -- so
# the scale is metres, and that sentence is the bar's own reading of the frame
# rather than a measurement off it. It is declared, marked and bracketed, the
# same standing as `ROCK_ROUGH` which it sits beside.
ROCK_POCKET = 2.0        # m, the alongshore/cross-shore correlation length of
                         # the planed rock's sub-grid relief. `?` -- the second
                         # unknown this lane adds and it is the SAME unknown as
                         # ROCK_ROUGH seen sideways: that one is the relief's
                         # amplitude, this one its wavelength, and together
                         # they are an rms SLOPE of sqrt(2)*0.25/2.0 = 0.177.
                         # Bracket (0.7, 6.0) m; the suite reports what the
                         # bench's bare share does across it, and the answer is
                         # NOTHING, because the mean of the mask is
                         # `sand_cover_fraction` at any scale. What the scale
                         # moves is the SIZE of the pockets and not how much
                         # rock shows, which is the honest way to hold a `?`
                         # that the volume book cannot decide.
ROCK_POCKET_BRACKET = (0.7, 6.0)


def _lattice_noise(x, y, lam, seed):
    """Bilinearly interpolated hash noise on a lattice of spacing `lam`.

    Hashed by CELL INDEX, like `_splitmix01` above and for the same reason: the
    surface must not depend on which pixels a camera happened to ask about.
    Smoothstep rather than linear interpolation, so the field is C1 and the
    pockets have no lattice creases in them.
    """
    fx = np.asarray(x, float) / lam
    fy = np.asarray(y, float) / lam
    i0 = np.floor(fx).astype(np.int64)
    j0 = np.floor(fy).astype(np.int64)
    tx, ty = fx - i0, fy - j0
    tx = tx * tx * (3.0 - 2.0 * tx)
    ty = ty * ty * (3.0 - 2.0 * ty)

    def h(i, j):
        return _splitmix01(i * np.int64(73856093) ^ (j * np.int64(19349663)),
                           seed)
    a = h(i0, j0) * (1 - tx) + h(i0 + 1, j0) * tx
    b = h(i0, j0 + 1) * (1 - tx) + h(i0 + 1, j0 + 1) * tx
    return a * (1 - ty) + b * ty


def _uniform_lut(n_bin=512, n_samp=400000, lam=1.0, seed=1):
    """The cdf of `_lattice_noise`, so its output can be mapped to a marginal
    that is EXACTLY uniform.

    WHY IT HAS TO BE UNIFORM, and this is the whole reason the function exists.
    The mask is `bare = (rank > cover)`, where `rank` is where a point stands in
    the height ordering of the rock inside its cell. A rank field is uniform by
    definition, and only if it is uniform does E[bare] equal 1 - cover -- which
    is the identity that ties this realisation to `sand_cover_fraction`'s
    closed form and lets the suite check one against the other. Interpolated
    hash noise is NOT uniform (the interpolant pulls mass toward the middle:
    its sd is 0.187 against a uniform's 0.289), so it is remapped through its
    own measured cdf, once, at import.
    """
    rng = np.random.default_rng(12345)
    p = rng.uniform(0.0, 1000.0, (n_samp, 2))
    v = _lattice_noise(p[:, 0], p[:, 1], lam, seed)
    q = np.linspace(0.0, 1.0, n_bin + 1)
    return np.quantile(v, q), q


_ROCK_RANK_LUT = None


def rock_rank(x, y, lam=None, seed=20260820):
    """The sub-grid rock surface's RANK field: uniform on [0, 1], smooth,
    correlation length `lam`. 0 is the bottom of a pocket, 1 the top of a rib.
    """
    global _ROCK_RANK_LUT
    lam = ROCK_POCKET if lam is None else lam
    if _ROCK_RANK_LUT is None:
        _ROCK_RANK_LUT = _uniform_lut()
    xs, q = _ROCK_RANK_LUT
    return np.interp(_lattice_noise(x, y, lam, seed), xs, q)


def rock_bare_mask(x, y, cover, foot=None, lam=None, seed=20260820):
    """WHERE the rock stands through the sand, not HOW MUCH of it does.

        bare = (rank > cover)

    -- sand fills from the bottom of the pocket up, so the covered share is the
    LOWEST `cover` of the surface by rank, exactly as `sand_cover_fraction`'s
    Gaussian integral says. E[bare] = 1 - cover identically, for any pocket
    scale, which is the row the suite fires.

    AND IT FALLS BACK TO THE MEAN WHEN THE PIXEL IS BIGGER THAN A POCKET, which
    is not a cosmetic anti-aliasing choice but the same statement one level up:
    once a pocket is sub-pixel the correct answer for that pixel IS the area
    mean, and `sand_cover_fraction` is what the mean is. `foot` is the pixel's
    footprint in metres; the blend is linear in lam/foot, so the expectation is
    1 - cover at every range and only the VARIANCE goes away with distance.
    """
    lam = ROCK_POCKET if lam is None else lam
    cover = np.clip(np.asarray(cover, float), 0.0, 1.0)
    m = (rock_rank(x, y, lam, seed) > cover).astype(float)
    if foot is None:
        return m
    s = np.clip(lam / np.maximum(np.asarray(foot, float), 1e-6), 0.0, 1.0)
    return s * m + (1.0 - s) * (1.0 - cover)


def _erf(z):
    """Vectorised erf. `math.erf` is scalar and `scipy` is not a dependency of
    this file; Abramowitz & Stegun 7.1.26 is 1.5e-7 absolute, which is four
    orders below anything `sand_cover_fraction` is asked for."""
    z = np.asarray(z, float)
    s = np.sign(z)
    a = np.abs(z)
    t = 1.0 / (1.0 + 0.3275911 * a)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                - 0.284496736) * t + 0.254829592) * t * np.exp(-a * a)
    return s * y


# --------------------------------------------------------------- the 2-D bed
def bed_2d(x, y, h1d, h_ref, lam_rip=120.0, gap_frac=0.75, gap_width=25.0,
           jitter=0.25, seed=20260813):
    """Compose the 1-D computed profile into a plan-view bed with rip channels.

    HONEST LABELLING, because this is the one place a critic should look hardest:
    the BAR is computed -- it is `h1d`, which came out of the Exner loop, and it
    enters here untouched. The alongshore RHYTHM is STAMPED, exactly as chapter
    12's `ripSystem` pseudocode stamps it ("carve gap through bar: h -=
    channelDepth * gaussAlong(y)"), at the spacing that chapter gives
    ("characteristic spacing is O(100 m), field values typically 50-500 m") and
    with the jitter it insists on ("quasi-rhythmic -- a preferred wavelength with
    real scatter about it, neither a fixed period nor true disorder"). A 2DH
    solve that GROWS the rhythm is out of scope by the chapter's own declaration.

    The channels are cut by removing a fraction of the BAR'S OWN ANOMALY, so a
    gap can never cut below the underlying ramp and the channel depth is not a
    free parameter.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    anom = np.maximum(np.asarray(h1d) - np.asarray(h_ref), 0.0)
    rng = np.random.default_rng(seed)
    n_rip = int(math.ceil((y[-1] - y[0]) / lam_rip)) + 2
    centres = y[0] + (np.arange(n_rip) + rng.uniform(0.0, 1.0, n_rip) * jitter
                      - 0.5 * jitter) * lam_rip
    g = np.zeros_like(y)
    for cy in centres:
        g = np.maximum(g, np.exp(-0.5 * ((y - cy) / gap_width) ** 2))
    cut = 1.0 - gap_frac * g                       # 1 on the bar, 1-gap_frac in
    return (np.asarray(h_ref)[None, :]             # a channel
            + anom[None, :] * cut[:, None]), centres


def trace_ray(x, y, h2d, T, x0, y0, theta0, ds=1.0, n_max=4000):
    """A single wave ray over a 2-D bed, by the eikonal ray equations:

        dx/ds = cos(theta),  dy/ds = sin(theta)
        dtheta/ds = (1/c) * ( sin(theta)*dc/dx - cos(theta)*dc/dy )

    theta is measured from +x (shoreward). The last line is the ray-curvature
    equation; the check that it is the RIGHT one is not a comment, it is a suite
    row: on an alongshore-uniform bed it must reproduce Snell's invariant
    sin(theta)/c to the integrator's own error, and Snell is not written
    anywhere in this function.

    RK2 (midpoint), because the ray turns hardest where c changes fastest and a
    forward-Euler ray visibly cuts corners there.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    omega = 2.0 * math.pi / T
    d2 = np.maximum(-np.asarray(h2d, float), D_MIN)
    k2 = wavenumber(omega, d2)
    c2 = omega / k2                                     # phase speed field
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])

    def c_at(px, py):
        fx = np.clip((px - x[0]) / dx, 0.0, x.size - 1.001)
        fy = np.clip((py - y[0]) / dy, 0.0, y.size - 1.001)
        i0, j0 = int(fx), int(fy)
        tx, ty = fx - i0, fy - j0
        c00, c10 = c2[j0, i0], c2[j0, i0 + 1]
        c01, c11 = c2[j0 + 1, i0], c2[j0 + 1, i0 + 1]
        c = (c00 * (1 - tx) * (1 - ty) + c10 * tx * (1 - ty)
             + c01 * (1 - tx) * ty + c11 * tx * ty)
        dcdx = ((c10 - c00) * (1 - ty) + (c11 - c01) * ty) / dx
        dcdy = ((c01 - c00) * (1 - tx) + (c11 - c10) * tx) / dy
        return c, dcdx, dcdy

    def deriv(px, py, th):
        c, dcdx, dcdy = c_at(px, py)
        return (math.cos(th), math.sin(th),
                (math.sin(th) * dcdx - math.cos(th) * dcdy) / c)

    px, py, th = float(x0), float(y0), float(theta0)
    path = [(px, py, th)]
    for _ in range(n_max):
        kx1, ky1, kt1 = deriv(px, py, th)
        mx, my, mt = px + 0.5 * ds * kx1, py + 0.5 * ds * ky1, th + 0.5 * ds * kt1
        kx2, ky2, kt2 = deriv(mx, my, mt)
        px, py, th = px + ds * kx2, py + ds * ky2, th + ds * kt2
        path.append((px, py, th))
        if px >= x[-1] or px <= x[0] or py <= y[0] or py >= y[-1]:
            break
    return np.array(path)


# ============================================================================
# THE COAST IN PLAN -- chapter 12's notch -> collapse -> deposit
# ============================================================================
#
# Waves 1 and 2 built a 1-D cross-shore profile. Bar section J settles that this
# coast is an EMBAYMENT between headlands, and it makes one of the four required
# closed forms checkable by eye: the breaking lines bend to stay parallel to the
# shore all the way round the curve. That check is worthless if the curve was
# drawn, so the curve is computed, by the same chapter's coastal loop:
#
#     coastalStep(h, seaLevel, exposure):
#         band = exp(-(h - seaLevel)^2 / (2*notchHeight^2))    # a notch AT sea level
#         h   -= K_coast * exposure * band * hardness^-1
#         thermal(h, talusAngle=rockRepose)                    # 05 collapses the cliff
#         beach = (1 - exposure) * nearShore * (h < seaLevel + beachHeight)
#         h   += K_deposit * beach * sedimentBudget
#
# ONE DELIBERATE DEPARTURE FROM THAT PSEUDOCODE, and it removes a free constant
# rather than adding one: `K_deposit * sedimentBudget` is replaced by the
# ERODED VOLUME ITSELF, redistributed over the sheltered band. The notch removes
# a measured volume of rock each step and exactly that volume is laid down as
# beach, so the loop is closed and the suite can assert it to round-off. A free
# deposition rate can build any beach you ask for, which is the same objection
# this project already makes to a free sediment source in the Exner step.
#
# WHAT IS AN INPUT HERE AND WHAT IS AN OUTPUT, stated first because it is the
# whole claim: the ROCK HARDNESS is an input -- it is the geology, and chapter 12
# is explicit that "with uniform rock you get a straight cliff and nothing else,
# which is the usual reason a coastal graph looks boring". Bar section H1 reads
# the platform's pocketing as the evidence that this coast is not uniform. The
# SHORELINE PLAN-FORM, the cliff, the wave-cut platform and the pocketing are
# all outputs. Nothing anywhere in this file draws a bay.

SEA_LEVEL = 0.0         # m. The datum. `evolve_forced` already carries a tide as
                        # a moving datum; the coastal loop is run at mean level.

NOTCH_HEIGHT = 0.5      # m, the standard deviation of the erosion band around
                        # sea level. `?` on the value, and it is the ONE constant
                        # in this loop the chapter gives a diagnostic for rather
                        # than a number: "the flat bench at sea level ... emerges
                        # if `band` is narrow and `K_coast` is high ... If you're
                        # not getting one, `notchHeight` is too large." So it is
                        # set from the diagnostic and the diagnostic is a suite
                        # row in BOTH directions -- a bench at 0.9 m, no bench at
                        # 4 m -- with `--bug wide-notch` firing the second.

K_COAST = 0.320         # m per step per unit exposure. A RATE, and it sets the
                        # clock rather than the answer: the loop is run to a
                        # quasi-steady plan-form and the suite checks the
                        # shoreline's shape is unchanged when K_COAST is halved
                        # and the step count doubled, exactly as K_Q is treated
                        # in the morphodynamic loop.

ROCK_REPOSE = 55.0      # degrees. The talus angle chapter 05's thermal step
                        # relaxes the undercut cliff to. Rock stands far steeper
                        # than sand (32 deg, EPS_SLOPE above); 55 deg is a
                        # DECLARED value for a jointed coastal rock mass and the
                        # cliff's height is not read off the photographs. `?`.

BEACH_HEIGHT = 2.0      # m, the elevation band the eroded material is laid down
                        # in ("h < seaLevel + beachHeight" in the pseudocode).
                        #
                        # WAVE 8: IT WAS A DEAD PARAMETER FOR SEVEN WAVES.
                        # `coastal_step` took `beach_height=BEACH_HEIGHT` in
                        # its signature and NEVER READ IT -- the deposition
                        # band was the literal `sea_level - 3.0` to
                        # `sea_level`, an undeclared number, and the chapter's
                        # own subaerial limit was quietly not implemented. That
                        # is why the scene had no beach. The parameter is gone
                        # and the constant stays here as the record of what the
                        # pseudocode asked for; the elevations that now bound
                        # the deposit are DERIVED -- `BERM_Z` = 0.727 m from
                        # the swell's run-up and `BACKSHORE_Z` = 1.029 m from
                        # the file's own storm -- and 2.0 m is between them and
                        # was never checked against either.

SAND_FRACTION = 0.10    # of the eroded rock that survives as beach-grade sand.
                        # `?` -- a cliff is not made of sand, and the fines and
                        # the abraded fraction leave in suspension. There is no
                        # measurement of it for this coast and the standing
                        # ruling forbids fitting one to the photographs, so it is
                        # DECLARED and BOUNDED instead: the suite sweeps it from
                        # 0 to 0.3 and reports that the embayment's amplitude and
                        # the bench's width move by a few per cent, because the
                        # deposit is thin against the wedge of rock removed.

HARD_CONTRAST = 0.60    # peak-to-mean of the hardness field, dimensionless.
HARD_LAM_Y = 380.0      # m, the alongshore correlation length of the geology.
HARD_LAM_X = 1400.0     # m, and across it. Much longer than the coast retreats,
                        # i.e. beds that strike roughly SHORE-NORMAL -- which is
                        # the geometry that makes a headland-and-bay coast, and
                        # the reason is measurable: with the two lengths equal
                        # the cliff crosses hard and soft ground as it retreats,
                        # the contrast averages out along its own path, and the
                        # embayment's amplitude collapses (26 m against 55 m for
                        # the same contrast and the same run).
HARD_SEED = 20260814    # the geology is a DECLARED random field with a stated
                        # seed. `?` -- there is no geological map of Aljezur in
                        # this project, and the standing ruling forbids fitting
                        # one to the photographs. What is claimed is not this
                        # particular coast but that a coast with SOME hardness
                        # variation produces headlands, a bay and a pocketed
                        # bench, and that a uniform one produces none of it.

ROCK_ROUGH = 0.25       # m, the rms relief of the planed rock surface WITHIN
                        # one cell. `?` AND IT IS THE ONE NEW UNKNOWN WAVE 12
                        # ADDS. Bar section H1 photographs the bench as "deeply
                        # pocketed, with sand infilling the hollows"; it gives
                        # no depth and the standing ruling forbids reading one
                        # off the frame. What the number is FOR is stated
                        # exactly: `sand_cover_fraction` below needs the scale
                        # of the roughness a sand veneer has to bury before the
                        # surface stops reading as rock, and that is a sub-grid
                        # quantity this loop's 4 x 16 m cells cannot resolve --
                        # see the note on `sand_cover_fraction`. The suite
                        # sweeps 0.10/0.25/0.60 and reports what the bench's
                        # bare-rock share does across it.

D_SHELF = 8.0           # m, the depth the Dean ramp is capped at, so the
                        # offshore boundary sits on a flat shelf. Not cosmetic:
                        # the 2-D transform's offshore boundary condition is
                        # Snell against the local celerity, which is only exact
                        # where the contours at the boundary are straight. A
                        # flat shelf makes the boundary condition exact instead
                        # of approximately right, and the suite can then compare
                        # the 2-D march against the 1-D one to round-off.

X_SHORE0 = 450.0        # m, where the initial (straight) shoreline sits.
S_PLAIN = 0.08          # the initial coastal plain's slope, rising shoreward.
                        # There is NO CLIFF in the initial condition -- a plain
                        # at 1:6.7 is not a cliff and cannot be mistaken for
                        # one. The cliff is what the notch and the thermal step
                        # make out of it, which is the point of running the loop
                        # at all.


def hardness_field(x, y, contrast=HARD_CONTRAST, lam_y=HARD_LAM_Y,
                   lam_x=HARD_LAM_X, n_modes=7, seed=HARD_SEED, uniform=False):
    """The rock's resistance, mean 1, as a band-limited random field.

    THE ONE GEOLOGICAL INPUT. Chapter 12: a sea stack "emerges naturally where a
    hard bed survives while the softer rock around it retreats -- so it requires
    spatially varying hardness. With uniform rock you get a straight cliff and
    nothing else". Bar section H1 records the platform's pocketing as this
    coast's evidence for the same thing.

    A sum of cosines with random phases rather than value noise, because the
    field wanted is BAND-LIMITED: a hardness field with power at the grid scale
    would pit the platform at one cell and that is not a landform. Returns
    shape (ny, nx), strictly positive.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if uniform:
        return np.ones((y.size, x.size))
    rng = np.random.default_rng(seed)
    f = np.zeros((y.size, x.size))
    for m in range(n_modes):
        # wavelengths spread over one octave either side of the correlation
        # length, so the field has a scale rather than a period
        ly = lam_y * 2.0 ** rng.uniform(-1.0, 1.0)
        lx = lam_x * 2.0 ** rng.uniform(-1.0, 1.0)
        py = rng.uniform(0.0, 2.0 * math.pi)
        px = rng.uniform(0.0, 2.0 * math.pi)
        f += (np.cos(2.0 * math.pi * y / ly + py)[:, None]
              * np.cos(2.0 * math.pi * x / lx + px)[None, :])
    f /= max(np.abs(f).max(), 1e-12)
    return 1.0 + contrast * f


def fetch_exposure(x, y, h2, sea_level=SEA_LEVEL, n_dirs=16, max_dist=900.0,
                   step=None, coarse=(2, 1), seaward=(-1.0, 0.0)):
    """Chapter 12's wave-exposure sweep, on the plan grid.

        fetch(p, dir): how far can wind blow over open water before reaching p
        exposure(p) = sum_i w_i * sqrt(fetch_i) / N,  w_i = max(0, dir_i . wind)

    with `sqrt(fetch)` because wave energy grows as the square root of fetch --
    the chapter's own line, kept. Returned normalised to [0, 1] over the domain,
    since only its RATIO between headland and bay does any work: it multiplies
    K_COAST, which is itself a rate.

    x is cross-shore and increases SHOREWARD, so `seaward` is -x. Off the
    seaward and alongshore edges of the domain the sweep sees open water (this
    is a window on a longer coast); off the landward edge it sees land.

    THE SWEEP IS RUN ON A COARSENED GRID and interpolated back, at `coarse`
    cells in x by 1 in y. Exposure is a smooth function of position -- it is an
    integral over 900 m of fetch -- so evaluating it every 4th cross-shore cell
    and interpolating costs nothing in accuracy and takes the coastal loop from
    minutes to seconds. The suite carries a row that computes it on the full
    grid and compares.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    h2 = np.asarray(h2, float)
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    cx = max(int(coarse[0]), 1)
    cy = max(int(coarse[1]), 1)
    if step is None:
        # AT LEAST ONE COARSE CELL, and this cost an hour: with a march step
        # shorter than the cell it walks on, the first sample rounds back onto
        # the cell itself. A land cell then reads itself as land, its fetch is
        # zero, and the notch -- which multiplies by exposure -- never touches
        # the cliff. The symptom was a coast that planed its own seabed flat
        # and did not retreat at all.
        step = max(dx * cx, dy * cy)
    xs = x[::cx]
    ys = y[::cy]
    wet = h2[::cy, ::cx] < sea_level
    ny, nx = wet.shape
    dxc, dyc = dx * cx, dy * cy

    e = np.zeros((ny, nx))
    w_tot = 0.0
    n_step = int(max_dist / step)
    for m in range(n_dirs):
        phi = 2.0 * math.pi * m / n_dirs
        ux, uy = math.cos(phi), math.sin(phi)
        w = max(0.0, ux * seaward[0] + uy * seaward[1])
        if w <= 0.0:
            continue
        w_tot += w
        # ALIVE STARTS TRUE EVERYWHERE, INCLUDING ON LAND, and it is not a
        # detail: seeding it with the wet mask makes `exposure` identically
        # zero on every land cell, so the notch -- which multiplies K_coast by
        # exposure -- can never touch the cliff, and the coast retreats by
        # 0.4 m in 1500 steps while quietly planing the seabed instead. A cliff
        # cell one step from the water has full fetch seaward; an inland cell
        # has none, because its first seaward sample is the cliff in front of
        # it. That is the sheltering the sweep is for.
        alive = np.ones((ny, nx), bool)
        f = np.zeros((ny, nx))
        for s_i in range(1, n_step + 1):
            s = s_i * step
            di = int(round(ux * s / dxc))
            dj = int(round(uy * s / dyc))
            ii = np.arange(nx) + di
            jj = np.arange(ny) + dj
            # off the landward edge is land; off the seaward and alongshore
            # edges is open water
            land_i = ii > nx - 1
            samp = wet[np.clip(jj, 0, ny - 1)[:, None],
                       np.clip(ii, 0, nx - 1)[None, :]]
            samp = np.where(land_i[None, :], False, samp)
            samp = np.where((ii < 0)[None, :], True, samp)
            samp = np.where(((jj < 0) | (jj > ny - 1))[:, None], True, samp)
            alive &= samp
            f += alive * step
            if not alive.any():
                break
        e += w * np.sqrt(f)
    e /= max(w_tot, 1e-12)
    if e.max() > 0:
        e /= e.max()
    if cx == 1 and cy == 1:
        return e
    out = np.empty((y.size, x.size))
    for j in range(y.size):
        jj = min(j // cy, ys.size - 1)
        out[j] = np.interp(x, xs, e[jj])
    if cy > 1:                                     # linear in y as well
        out = np.stack([np.interp(y, ys, out[::cy, i], )
                        for i in range(x.size)], axis=1)
    return out


def thermal_relax(h2, dx, dy, tan_repose, n_iter=3, frac=0.4):
    """Chapter 05's thermal / talus step: nothing stands steeper than repose.

    Four-neighbour, mass conserving by construction -- whatever one cell loses
    its downhill neighbour gains, so the coastal loop's volume book stays
    closed and the deposit below is the notch's own rock and nothing else.
    """
    h = np.asarray(h2, float).copy()
    for _ in range(int(n_iter)):
        for axis, spacing in ((1, dx), (0, dy)):
            lim = tan_repose * spacing
            d = np.diff(h, axis=axis)
            move = np.clip(np.abs(d) - lim, 0.0, None) * frac * 0.5
            move = np.sign(d) * move
            if axis == 1:
                h[:, :-1] += move
                h[:, 1:] -= move
            else:
                h[:-1, :] += move
                h[1:, :] -= move
    return h


def coastal_step(h2, hard, expo, dx, dy, sea_level=SEA_LEVEL,
                 notch=NOTCH_HEIGHT, k_coast=K_COAST, repose=ROCK_REPOSE,
                 deposit=True, use_exposure=True,
                 waterline=True, depth_limit=True, h0_wave=H0_SWELL,
                 sand_fraction=SAND_FRACTION, toe_depth=3.0):
    """One notch -> collapse -> deposit iteration. Returns (h, eroded volume).

    CHAPTER 12'S coastalStep TAKEN LITERALLY STALLS ON A HEIGHTFIELD, and the
    `waterline` term is what this file adds to it. Measured, and the measurement
    is in README-beach.md: with `band` a pure function of the CELL'S OWN
    elevation, the notch cuts the cliff toe down until the toe leaves the band,
    the thermal step holds the face at repose above it, and every cell that is
    still intact rock is out of the band's reach. The coast then retreats 16 m
    and stops dead -- 500 further steps move it by 0.0 m -- while the notch goes
    on planing the seabed it has already cut. Widening `notchHeight` restarts
    the retreat and destroys the bench, which is the chapter's own diagnostic
    running the other way: the two things the loop is supposed to produce are in
    conflict in the pseudocode as written.

    What is missing is UNDERCUTTING. A real notch cuts INTO the cliff at the
    waterline and the overhang falls; a heightfield cannot hold an overhang
    (chapter 11's representation warning, which chapter 12 already invokes for
    arches). The heightfield expression of the same statement is: waves attack
    the FIRST LAND CELL ABOVE THE WATERLINE, whatever its elevation, because
    that is the cell the water reaches. With that term the loop retreats
    indefinitely AND planes a bench, and the chapter's `notchHeight` diagnostic
    is recovered in full -- narrow band, bench; wide band, no bench.
    """
    h = np.asarray(h2, float)
    band = np.exp(-((h - sea_level) ** 2) / (2.0 * notch ** 2))
    if waterline:
        wet = h < sea_level
        foot = (~wet) & (_dilate4(wet))
        band = np.maximum(band, foot.astype(float))
    # THE WAVE THAT DOES THE WORK IS DEPTH-LIMITED, and without that the loop
    # has no mechanism at all limiting how wide a bench it planes: nothing
    # attenuates the wave as it crosses the bench, so the notch goes on cutting
    # at the same rate 200 m from the cliff as it does at its foot. Measured
    # before this term existed: a 235 m bench and still widening at 1600 steps.
    # The attenuation needs no new constant, because the file already owns the
    # relation -- the wave that reaches a cell is H = min(H_0, gamma_b*d) and
    # the work it does goes as its ENERGY, H^2. `d` is the water depth in front
    # of the cell (its own, or its seaward neighbour's if it is the cliff foot),
    # so a cliff standing behind a wide shallow bench is attacked by a small
    # wave and retreats slowly. That is the negative feedback a real shore
    # platform's width is set by, and it is chapter 12's own breaking index
    # doing the work.
    d_w = np.maximum(sea_level - h, 0.0)
    d_att = np.maximum(d_w, np.concatenate([d_w[:, :1], d_w[:, :-1]], axis=1))
    h_loc = np.minimum(h0_wave, GAMMA_B * d_att)
    atten = (h_loc / h0_wave) ** 2 if depth_limit else 1.0
    drive = (expo if use_exposure else np.ones_like(band)) * atten
    ero = k_coast * drive * band / np.maximum(hard, 1e-6)
    h = h - ero
    vol = float(ero.sum()) * dx * dy
    h = thermal_relax(h, dx, dy, math.tan(math.radians(repose)))
    export = 0.0
    # WAVE 8. THE SAND THE STEP PRODUCED, PER ROW. `vol` is the whole rock
    # wedge removed and `export` is the scalar remainder; neither of them is
    # the quantity a beach is made of, which is the beach-GRADE fraction and
    # which row of the coast it came off. It is read out here and spent by
    # `bay_bed` on `subaerial_beach`. NOTHING BELOW IS CHANGED BY THIS LINE --
    # it is the same `ero` the deposition already uses, summed on a different
    # axis -- so every measurement in `_sec_coast` is bit-identical to wave 7's.
    sand_row = ero.sum(axis=1) * dx * dy * sand_fraction
    if deposit and vol > 0.0:
        # `nearShore` is WATER, and it has to be said: the exposure sweep
        # returns zero on land (no fetch reaches a cell behind the cliff), so
        # `1 - exposure` is largest of all in the middle of the plateau. Taking
        # the pseudocode's weight literally over the whole grid piles the
        # eroded rock onto the highest, driest, most sheltered ground and the
        # shoreline stops retreating -- measured, at 0.4 m in 1500 steps.
        #
        # THE MATERIAL STAYS IN THE ROW IT CAME FROM. The pseudocode's
        # `sedimentBudget` is a single global number spread by `1 - exposure`,
        # which moves rock alongshore -- and moving sediment alongshore is
        # longshore drift, i.e. the circulation this wave does not solve. Taken
        # literally it also runs away: with `exposure` saturated at 1 over open
        # water the weight is nonzero in only a handful of rows and the whole
        # coast's debris lands in them (measured: a ridge of new land built
        # 200 m offshore in 800 steps). Row-local deposition needs no
        # coefficient and leaves the alongshore redistribution named, not faked.
        #
        # AND THE BEACH CANNOT HOLD IT ALL, which is a fact rather than a
        # choice: retreating 100 m of a plain that rises at 1:6.7 removes about
        # 750 m^2 of rock per metre of coast, and the nearshore band it could
        # be stacked in holds about 120. The fill is therefore capacity-limited
        # at the datum -- a beach does not build above the water line here, and
        # the excess LEAVES THE DOMAIN and is returned as `export` rather than
        # quietly dropped. Real cliff debris is abraded and carried offshore;
        # this loop does not transport it and says so with a number.
        # `toe_depth` WAS THE LITERAL 3.0 AND IT IS STILL `?`. It is the
        # seaward limit of the nearshore band the fill goes into, it was never
        # declared, and wave 8 has NOT changed its value -- naming it and
        # changing it in one move would have made every measurement in
        # `_sec_coast` incomparable with wave 7's. What wave 8 does is give it
        # a name and a note: the physical quantity is the closure depth, the
        # depth beyond which the wave no longer moves sand, and Hallermeier's
        # relation puts it at 3.2 m for this sea state -- 7% from the literal
        # somebody wrote. Close enough to be a coincidence and close enough
        # that changing it is not this wave's business.
        near = (h < sea_level) & (h > sea_level - toe_depth)
        cap = np.maximum(sea_level - h, 0.0) * near
        cap_row = cap.sum(axis=1) * dx * dy
        ero_row = ero.sum(axis=1) * dx * dy * sand_fraction
        give = np.minimum(ero_row, cap_row)
        f = np.where(cap_row > 1e-12, give / np.maximum(cap_row, 1e-12), 0.0)
        h = h + f[:, None] * cap
        export = float(vol - give.sum())
    return h, vol, export, sand_row


def _dilate4(m):
    """True where `m` is true in any 4-neighbour."""
    m = np.asarray(m, bool)
    out = m.copy()
    out[:, :-1] |= m[:, 1:]
    out[:, 1:] |= m[:, :-1]
    out[:-1, :] |= m[1:, :]
    out[1:, :] |= m[:-1, :]
    return out


def initial_coast(x, y, x_shore=X_SHORE0, s_plain=S_PLAIN, A=DEAN_A,
                  d_shelf=D_SHELF):
    """A straight coast with no cliff, no bay and no bench: a plain rising
    shoreward off a Dean ramp capped at the shelf depth.

    Everything the coastal loop is credited with has to come out of THIS, and
    it is alongshore-uniform to machine precision -- `h[:, i]` is one number.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    land = s_plain * np.maximum(x - x_shore, 0.0)
    sea = -np.minimum(A * np.maximum(x_shore - x, 0.0) ** (2.0 / 3.0), d_shelf)
    h1 = np.where(x >= x_shore, land, sea)
    return np.repeat(h1[None, :], y.size, axis=0)


def evolve_coast(x, y, h0, hard, n_steps=400, expo_every=25, **kw):
    """The coastal loop. Exposure is recomputed every `expo_every` steps --
    it is the slow field (it changes only as the coast changes shape) and the
    fast one is the bed.

    Returns (h, exposure, volume eroded, volume exported, per-row sand,
    history)."""
    h = np.asarray(h0, float).copy()
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    expo = None
    v_tot = 0.0
    v_exp = 0.0
    s_row = np.zeros(np.asarray(h0).shape[0])
    hist = []
    for s in range(int(n_steps)):
        if s % expo_every == 0:
            expo = fetch_exposure(x, y, h)
        h, v, ex, sr = coastal_step(h, hard, expo, dx, dy, **kw)
        v_tot += v
        v_exp += ex
        s_row = s_row + sr
        if s % max(1, n_steps // 6) == 0 or s == n_steps - 1:
            hist.append((s, h.copy()))
    expo = fetch_exposure(x, y, h)
    return h, expo, v_tot, v_exp, s_row, hist


# =============================================================================
# WAVE 13 -- THE SEA-LEVEL HISTORY, AND THE LADDER IT WRITES
# =============================================================================
# Wave 12 measured the coastal plateau at 45.4% of the hero frame, one declared
# albedo, high-frequency sd 0.0009 of 255, and diagnosed it as an emerged MARINE
# TERRACE -- chapter 12's own sea-level-history loop, named and not built. Wave
# 13's first job was to TEST that diagnosis rather than build on it, and the
# test is exact rather than plausible:
#
#   THE PLATEAU IS NEITHER A TERRACE NOR A RELAXATION ARTEFACT. IT IS THE
#   INITIAL CONDITION, UNTOUCHED.
#
# `initial_coast` returns `S_PLAIN * (x - X_SHORE0)` repeated over y, and on the
# 4000-step run 14 423 of 22 339 cells satisfy |h - h0| < 1e-9 -- every one of
# them landward of x = 688 m. Its per-column alongshore standard deviation is
# 1.4e-14 m, i.e. machine precision on a field the loop is supposed to have
# worked. A far-field RELAXATION artefact (the other candidate) would show the
# opposite signature on both counts: it is the Dean ramp's asymptote reached
# from a disturbed state, so it carries a nonzero residual and inherits the
# alongshore structure of whatever disturbed it. Neither is present. The
# plateau is a declared ramp that no process in this file has ever run on.
#
# So the diagnosis SURVIVES as the identification -- a flat surface behind an
# actively retreating cliff on an uplifting coast is an emerged terrace, and
# nothing else in chapter 12 makes one -- and its PRESCRIPTION does not survive
# intact. What the loop below shows is that this domain holds ONE TREAD and not
# a flight, and the arithmetic is the chapter's own (see `terraces_in_domain`).
#
# ---------------------------------------------------------------- the forcing
# The sea-level history is to the coastal loop what the offshore spectrum is to
# the wave transform: standing ruling 5 says the wave field "arrives from
# OUTSIDE with a stated offshore spectrum, so shoaling and refraction are
# OUTPUTS and not inputs", and the same discipline applies here. The eustatic
# curve and the uplift rate are STATED; every elevation, width and slope below
# is an output of running them.

EUSTATIC_PERIOD = 1.0e5     # yr, the late-Quaternary glacial cycle. The 100-kyr
                            # world since the mid-Pleistocene transition. `?` in
                            # the sense that nothing in this project measured
                            # it, but it is not a free parameter of the model --
                            # it is the forcing's period and the ladder's rung
                            # spacing is LINEAR in it, which the suite sweeps.

HIGHSTAND_DURATION = 1.0e4  # yr, how long an interglacial highstand holds still
                            # enough to plane a bench. `?`. It sets the TREAD
                            # WIDTH and nothing else, through `tread_width`.

EUSTATIC_HIGHSTANDS = (8.0, 2.0, -5.0, 6.0, 0.0)
                            # m, the eustatic level of each successive highstand,
                            # OLDEST FIRST -- MIS 11, 9, 7, 5e, 1. `?` and quoted
                            # from model knowledge, not verified against a
                            # published curve, so it is marked and the suite is
                            # written so that NOTHING depends on the particular
                            # numbers: the ladder's closed form takes the tuple
                            # as an argument and is checked against a uniform
                            # tuple (where it must be an exact arithmetic
                            # progression) and against this one (where it must
                            # be that progression plus the stated offsets).

UPLIFT_RATE = 1.0e-4        # m/yr = 0.10 mm/yr. `?` AND IT IS A FORCING, not a
                            # fitted constant -- the tectonic boundary condition
                            # the coastal loop runs under, exactly as
                            # THETA0_SWELL is the wave field's.
                            #
                            # THREE INDEPENDENT BOUNDS, and the value is where
                            # they overlap rather than where the picture wanted
                            # it:
                            #  1. PUBLISHED RANGE. Uplifting coasts run 0.1-3
                            #     mm/yr. The TOP of that range is active margin
                            #     -- the Californian and New Zealand staircases
                            #     chapter 12 names as the textbook cases -- and
                            #     the BOTTOM is passive margin. This coast is
                            #     passive Atlantic margin, so the bottom is the
                            #     setting's own answer and not a fit.
                            #  2. THE LADDER MUST BE IN THE FRAME.
                            #     `uplift_ceiling`: the initial plain tops out
                            #     at 44.0 m, so U <= 4.4e-4 m/yr at this period
                            #     for a two-stand history to have any terrace at
                            #     all.
                            #  3. THE TREAD MUST REACH THE PRESENT BROW.
                            #     `terrace_brow_ceiling`: 9.2e-5 m/yr on this
                            #     scene, and 1.0e-4 lands just above it, which
                            #     the seaward planation covers -- the measured
                            #     tread starts at x = 640 m against a present
                            #     shoreline at 640.7 m.
                            # The claim is the closed form E_i = e_i + U*i*P -
                            # Z_p, not this number, and the suite sweeps U and
                            # requires the ladder to track it linearly.

CLIFF_RETREAT_RATE = 0.10   # m/yr. Chapter 12's own bracket for cliff retreat is
                            # 0.05-0.5 m/yr (it is quoted there against the
                            # denudation rate). THIS IS THE LOOP'S CLOCK and it
                            # is the only thing that converts `coastal_step`
                            # iterations into years -- K_COAST is a rate per
                            # STEP with no time in it, so the step is worth
                            # `retreat per step / retreat per year` years and
                            # `step_years` says so.

DENUDATION_RATE = 3.0e-5    # m/yr = 0.03 mm/yr, subaerial lowering of a land
                            # surface. Chapter 12's own bracket, 0.01-0.1 mm/yr,
                            # quoted there. Used ONLY to convert a terrace's AGE
                            # into the thickness of the mantle weathering has put
                            # on it (`soil_mantle`) -- which is what decides
                            # whether a tread reads as rock or as ground.


def step_years(retreat_per_step, retreat_rate=CLIFF_RETREAT_RATE):
    """How many years one `coastal_step` iteration is worth.

    K_COAST is m per STEP per unit exposure and carries no time at all, so the
    loop's clock is arbitrary until something outside it is fixed. The thing
    outside it is chapter 12's cliff-retreat bracket, 0.05-0.5 m/yr. Measure the
    loop's own retreat per step and the step is worth their quotient.

    Measured on this scene: 189.46 m in 4000 steps = 0.047 m/step, so one step
    is 0.09-0.95 yr and the whole 4000-step run is 379-3789 yr. THAT IS SHORTER
    THAN AN INTERGLACIAL, which is the first half of the domain arithmetic.
    """
    return float(retreat_per_step) / float(retreat_rate)


def tread_width(duration=HIGHSTAND_DURATION, retreat_rate=CLIFF_RETREAT_RATE):
    """The cross-shore width a stand of `duration` years planes, KINEMATICALLY.

    A shore platform is cut at the same rate the cliff retreats, because it IS
    the ground the cliff has retreated across:  W = R * D.

    At chapter 12's bracket and a 10-kyr highstand that is 500-5000 m, against
    a 1000 m domain -- which is the finding, not a nuisance. See
    `terraces_in_domain`.

    THIS IS AN UPPER BOUND AND THE LOOP DOES NOT REACH IT, because the loop
    carries a depth-limited attenuation the kinematic form does not: measured
    here the bench runs 100 / 148 / 216 / 280 m at 1000 / 2000 / 4000 / 6400
    steps, i.e. W ~ N^0.55 rather than N^1. Chapter 12 already records that the
    attenuation does not produce a saturating width and marks the equilibrium
    claim `?`; nothing here closes that, and the sublinearity is reported by
    `platform_growth_exponent` rather than modelled.
    """
    return float(retreat_rate) * float(duration)


def planation_depth(notch=NOTCH_HEIGHT, k_coast=K_COAST, n_steps=None,
                    drive=1.0, hard=1.0, n_iter=200):
    """The depth below the stand's own level that the notch planes its bench to.

    THE ONE ELEVATION IN THE LADDER THAT IS NOT DECLARED. `coastal_step` cuts at
    `k_coast * drive * exp(-(h - level)^2 / 2 notch^2) / hard` per step, so a
    cell `z` below the level is being cut exponentially slowly. After N steps it
    has been lowered by roughly `N * k_coast * drive * exp(-z^2/2 notch^2)/hard`,
    and the bench sits where that equals `z`:

        z = (K*N*drive/hard) * exp(-z^2 / (2*notch^2))

    which is transcendental and is solved here by fixed-point iteration on
    z = notch*sqrt(2*ln(K*N*drive/(hard*z))).

    THE POINT OF THE FORM IS THE LOGARITHM. The bench level depends on the
    clock only as sqrt(ln N), so it is set by NOTCH_HEIGHT and essentially not
    by how long the stand lasted -- measured on this scene the bench sits at
    -1.832 / -1.866 / -1.895 / -1.906 m at 1000 / 2000 / 4000 / 6400 steps, a
    4% move for a 6.4x change in the clock. THAT is what lets a flight of
    terraces read its own eustatic history back: every rung is cut to the same
    depth below its own stand, so the DIFFERENCES between rungs are the sea
    level's and the uplift's, with Z_p cancelling out of them exactly.
    """
    if n_steps is None:
        n_steps = N_COAST                       # defined with the scene sizes
    a = float(k_coast) * float(n_steps) * float(drive) / max(float(hard), 1e-12)
    z = float(notch)
    for _ in range(int(n_iter)):
        arg = a / max(z, 1e-12)
        if arg <= 1.0:
            return 0.0
        z_new = float(notch) * math.sqrt(2.0 * math.log(arg))
        if abs(z_new - z) < 1e-13:
            z = z_new
            break
        z = 0.5 * (z + z_new)
    return z


def terrace_ladder(n_stands=None, uplift=UPLIFT_RATE, period=EUSTATIC_PERIOD,
                   eustatic=EUSTATIC_HIGHSTANDS, planation=None):
    """THE ELEVATION LADDER. Chapter 12's marine-terrace section in closed form.

    A bench cut at stand `i` (oldest first, `n-1` = the present one) was planed
    to `e_i - Z_p` at the time, and has been lifted at `U` for the `(n-1-i)`
    cycles since:

        E_i = e_i + U * (n-1-i) * P  -  Z_p

    Two consequences, and they are what the suite checks separately:

      * the SPACING between successive rungs is `U*P + (e_i - e_{i+1})`, and Z_p
        is not in it. With a uniform eustatic tuple the ladder is an EXACT
        arithmetic progression of common difference `U*P` -- a control whose
        answer is known before the loop is run (standing ruling 14).
      * the OFFSET of the whole ladder is `-Z_p`, which is the loop's own
        output and the only quantity here that is not declared.

    Returns the elevations OLDEST FIRST, i.e. descending, so `out[0]` is the
    highest and oldest rung and `out[-1]` is the present bench.
    """
    if planation is None:
        planation = planation_depth()
    if eustatic is None:
        n = int(n_stands or 1)
        eustatic = (0.0,) * n
    eustatic = tuple(float(v) for v in eustatic)
    if n_stands is not None and int(n_stands) != len(eustatic):
        n = int(n_stands)
        eustatic = (eustatic * (n // len(eustatic) + 1))[:n]
    n = len(eustatic)
    return np.array([eustatic[i] + uplift * (n - 1 - i) * period - planation
                     for i in range(n)])


def terraces_in_domain(plateau_width, duration=HIGHSTAND_DURATION,
                       retreat_rate=CLIFF_RETREAT_RATE):
    """How many rungs of the ladder the domain can hold. Arithmetic, no model.

    A flight of `n` terraces needs `n` treads side by side, so it needs
    `n * W` of cross-shore ground. The measured plateau here is 316 m (x = 688
    to 1000, the untouched region) and one Quaternary highstand's tread is
    500-5000 m, so the answer is BELOW ONE at every rate in chapter 12's
    bracket. That is why this file builds a single emerged tread in the scene
    and proves the ladder on a wider instrument domain instead.
    """
    return float(plateau_width) / max(tread_width(duration, retreat_rate), 1e-9)


def overprint_threshold(retreat, s_sea, notch_depth=None):
    """The smallest rung spacing `U*P` that leaves a LEGIBLE flight, metres.

    NOT IN CHAPTER 12, and it is the reason a real uplifting coast either has a
    staircase or has nothing. The competition is between the vertical offset
    the uplift buys and the horizontal ground the next stand eats:

      * after `h += uplift*period` the old tread stands `U*P - Z_p` above the
        new sea level, so the new shoreline lands `(U*P - Z_p)/s_sea` SEAWARD
        of the old tread's outer lip, on the shoreface of slope `s_sea`;
      * the new stand then retreats `R` landward while it cuts its own bench.

    The old tread survives as a separate rung iff the new stand does not reach
    it:

        (U*P - Z_p)/s_sea  >  R      <=>      U*P  >  Z_p + s_sea*R

    BELOW THE THRESHOLD THE RUNGS DO NOT GET CLOSER TOGETHER -- THEY MERGE.
    Each stand re-planes its predecessor and the flight collapses to ONE
    surface at the youngest level, which is a qualitatively different landform
    and not a staircase with fine treads. Measured on the instrument at
    900 steps a rung and s_sea = 0.05: 4 rungs at U*P >= 4.6 m, 2 at 4.4 m and
    1 at 4.2 m and below, against Z_p = 1.61 m -- so the transition is sharp
    and it is at 2.7-2.9 Z_p.

    `retreat` IS AN INPUT AND MUST BE MEASURED, and that is the one soft place
    here. The first stand cuts from a wedge apex and retreats 101.6 m; the
    stands after it start on a shoreface and the threshold above implies an
    effective 58 m. Feeding the FIRST stand's retreat in over-predicts the
    threshold by 45%. The FORM is derived; the retreat to put in it is the
    loop's own output and is marked `?` until a stand-by-stand retreat law
    exists -- which is chapter 12's unbounded-platform open problem seen from
    a second side.
    """
    if notch_depth is None:
        notch_depth = planation_depth()
    return float(notch_depth) + float(s_sea) * float(retreat)


def terrace_brow_ceiling(retreat, eustatic=0.0, s_plain=S_PLAIN,
                         period=EUSTATIC_PERIOD):
    """The largest uplift rate whose tread still reaches the PRESENT cliff brow.

    THE THIRD DOMAIN CONSTRAINT, and the one that decides whether the terrace is
    the ground the camera stands on or a step 200 m behind it.

    The older stand's shoreline sits where the initial plain reaches that
    stand's level: `x_0 = X_SHORE0 + (e + U*P)/s_plain`. The present stand's
    cliff brow sits at `X_SHORE0 + R`, `R` its own retreat. The old tread runs
    from `x_0` landward, so it covers the present brow only if `x_0 <= X_SHORE0
    + R`:

        e + U*P  <=  s_plain * R        <=>       U  <=  (s_plain*R - e)/P

    On this scene R = 189.5 m and s_plain = 0.08, so `s_plain*R` = 15.2 m; with
    MIS 5e's e = 6.0 m that leaves 9.2 m for the uplift, i.e. 9.2e-5 m/yr.
    THE INEQUALITY IS SLIGHTLY CONSERVATIVE because it ignores how far the old
    stand planed SEAWARD of its own shoreline, which is why UPLIFT_RATE = 1.0e-4
    still lands the tread's seaward lip at x = 640 m against a shoreline at
    640.7 m rather than 10 m short of it.
    """
    return (float(s_plain) * float(retreat) - float(eustatic)) / float(period)


def soil_mantle(age, rate=DENUDATION_RATE):
    """The regolith a terrace tread has acquired since it emerged, metres.

    Weathering lowers a land surface at chapter 12's own 0.01-0.1 mm/yr, and
    what it lowers it INTO is a mantle. Over one 100-kyr cycle that is 1-10 m,
    against a rock roughness (ROCK_ROUGH) of 0.25 m -- so `sand_cover_fraction`
    of it is 1.000 and an old tread reads as ground rather than as rock. The
    same arithmetic run backwards is the useful half: bare rock shows on a
    tread only while the mantle is thinner than a roughness, i.e. for the first
    `ROCK_ROUGH/rate` = 2.5-25 kyr after it emerges. THE LADDER'S RUNGS ARE
    THEREFORE DISTINGUISHABLE BY THEIR BARE-ROCK SHARE, and that is a derived
    signature of terrace AGE rather than a painted one.
    """
    return float(rate) * np.asarray(age, float)


def bare_rock_age_limit(rough=None, rate=DENUDATION_RATE):
    """The age at which a tread's mantle reaches one rock roughness, years."""
    return (ROCK_ROUGH if rough is None else float(rough)) / float(rate)


def stand_levels(eustatic=EUSTATIC_HIGHSTANDS, uplift=UPLIFT_RATE,
                 period=EUSTATIC_PERIOD, frame='sea'):
    """The sea level each stand is run at, OLDEST FIRST, in the chosen frame.

    CHAPTER 12 WRITES THE UPLIFT AS `h += upliftField * dt` AND ON A CAPPED
    HEIGHTFIELD THAT LIFTS THE BASIN OUT OF THE WATER. This scene's Dean ramp
    is capped at D_SHELF = 8 m (the cap is the 2-D transform's offshore
    boundary condition and is not cosmetic), so a single 30 m lift puts the
    ENTIRE domain above the datum: the sea disappears, the notch has nothing to
    cut, and the loop returns one flat surface. That is not a subtlety, it is
    what the first run of `run_terrace` did.

    The equivalent statement costs nothing and needs no basin. Only RELATIVE
    sea level does any work -- `coastal_step` is a function of `h - sea_level`
    in every term it has, and so is `fetch_exposure` -- so lifting the land by
    `U*P` between stands and holding the sea at `e_i` is the same history as
    holding the land still and running stand `i` at

        L_i = e_i + U*(n-1-i)*P

    with the present stand at `L_{n-1} = e_{n-1}`. The RELIEF the flight needs
    is then ABOVE the present shoreline, which is exactly where this domain has
    it: the coastal plain is what the older stands cut into.

    THE EQUIVALENCE HAS A CONDITION ON THE INITIAL SURFACE AND GETTING IT WRONG
    COSTS THE WHOLE FLIGHT. The two frames agree only if the sea frame's
    starting ground is the uplift frame's raised by the TOTAL lift,
    `(n-1)*U*P` -- the uplift frame ends `(n-1)*U*P` higher than it started, and
    both runs are read in the frame where the present stand is the datum. Start
    the sea frame from the unshifted surface and the oldest stand is `(n-1)*U*P`
    too low relative to its own sea, which is a completely different history:
    measured here it cuts one bench and leaves ONE rung of four. The suite
    carries the shifted pair and it agrees to machine precision.

    `frame='uplift'` returns the chapter's literal constant levels; the loop
    then does the lifting. `frame='sea'` returns the falling ladder and the
    loop does not lift. One loop, one flag, and the flag is a symmetry test.
    """
    eus = tuple(float(v) for v in eustatic)
    n = len(eus)
    if frame == 'uplift':
        return list(eus)
    if frame != 'sea':
        raise ValueError('frame must be "sea" or "uplift"')
    return [eus[i] + float(uplift) * (n - 1 - i) * float(period)
            for i in range(n)]


def evolve_coast_stands(x, y, h0, hard, stands, uplift=UPLIFT_RATE,
                        period=EUSTATIC_PERIOD, expo_every=250, frame='sea',
                        **kw):
    """CHAPTER 12'S SEA-LEVEL-HISTORY LOOP, with its structure kept verbatim:

        for stand in seaLevelHistory:            # each (level, duration)
            repeat prop. duration:  coastalStep(h, stand.level, exposure)
            h += upliftField * dt                # tectonics between stands

    `stands` is a sequence of `(level_m, n_steps)`, OLDEST FIRST, and the last
    one is the present stand -- its level is the datum the whole scene is
    referred to.

    `frame` decides WHERE THE UPLIFT GOES and the two are the same history --
    see `stand_levels`. `'uplift'` is the chapter's line, `h += uplift*period`
    between stands, and it needs a basin deeper than the ladder is tall.
    `'sea'` puts the same relative motion into the stand levels and needs no
    basin at all, which is the only one of the two this domain can run.

    TWO-LAYER BOOKKEEPING, and it costs one array. `h` is the surface and
    `h_rock` is the rock beneath it: erosion lowers both (the notch cuts rock),
    deposition raises only `h` (the deposit is sediment). `h - h_rock` is then
    the regolith the loop actually put there, and it is carried up with the
    tread when the land is lifted -- which is what makes an emerged tread's
    cover fraction an OUTPUT of the history rather than a mask somebody drew.
    Nothing about the single-stand result changes: with one stand and no uplift
    this reproduces `evolve_coast` to the bit, and the suite carries that row.

    Returns (h, h_rock, exposure, volume, exported, sand_row, record) where
    `record` has one entry per stand with its level, step count, and the age of
    its bench at the end of the run.
    """
    h = np.asarray(h0, float).copy()
    h_rock = h.copy()
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    v_tot = 0.0
    v_exp = 0.0
    s_row = np.zeros(h.shape[0])
    rec = []
    n = len(stands)
    for i, (level, n_steps) in enumerate(stands):
        n_steps = int(n_steps)
        expo = None
        for s in range(n_steps):
            if s % expo_every == 0:
                expo = fetch_exposure(x, y, h, sea_level=level)
            h_before = h
            h, v, ex, sr = coastal_step(h, hard, expo, dx, dy,
                                        sea_level=level, **kw)
            # THE ROCK SURFACE FOLLOWS THE CUT AND NOT THE FILL. Wherever the
            # step lowered the surface, rock was removed and the rock surface
            # goes with it; wherever it raised the surface, sediment was added
            # and the rock stays where it was. One min(), no coefficient.
            h_rock = np.minimum(h_rock, h)
            v_tot += v
            v_exp += ex
            s_row = s_row + sr
            del h_before
        rec.append(dict(level=float(level), n_steps=n_steps,
                        age=(n - 1 - i) * float(period),
                        mantle=float(soil_mantle((n - 1 - i) * float(period)))))
        if i < n - 1 and frame == 'uplift':
            lift = float(uplift) * float(period)
            h = h + lift
            h_rock = h_rock + lift
    expo = fetch_exposure(x, y, h, sea_level=stands[-1][0])
    return h, h_rock, expo, v_tot, v_exp, s_row, rec


def terrace_levels(x, h2, slope_max=0.02, min_width=40.0, tol=1.5,
                   z_min=None):
    """MEASURE THE LADDER BACK OFF A BUILT SURFACE. The other half of the proof.

    A terrace tread is a run of ground flatter than anything else on the
    profile: the planation slopes this loop produces are 1:476 to 1:2403
    (measured), the initial plain is 1:12.5 and the cliff is 1:0.71, so a
    threshold at 1:50 separates them by more than an order of magnitude on both
    sides and nothing here is tuned between them.

    Per row: find contiguous runs with |dh/dx| < slope_max wider than
    `min_width`, take each run's MEDIAN elevation, then cluster the levels
    across all rows with `tol` metres of tolerance. Returns a list of dicts,
    highest first, with the level, the total width and the number of rows.

    THE MEDIAN AND NOT THE MEAN, and the reason is this project's own repeated
    error class: a tread with a riser accidentally caught at one end has a mean
    pulled off the tread and a median that is still on it.
    """
    x = np.asarray(x, float)
    h2 = np.atleast_2d(np.asarray(h2, float))
    dx = float(x[1] - x[0])
    n_min = max(int(round(min_width / dx)), 2)
    found = []
    for j in range(h2.shape[0]):
        g = np.abs(np.gradient(h2[j], dx))
        flat = g < slope_max
        if z_min is not None:
            flat &= h2[j] > z_min
        i = 0
        while i < flat.size:
            if not flat[i]:
                i += 1
                continue
            k = i
            while k < flat.size and flat[k]:
                k += 1
            if k - i >= n_min:
                found.append((float(np.median(h2[j][i:k])), (k - i) * dx))
            i = k
    if not found:
        return []
    found.sort(key=lambda t: -t[0])
    out = []
    cur = [found[0]]
    for lv, w in found[1:]:
        if abs(lv - np.median([c[0] for c in cur])) <= tol:
            cur.append((lv, w))
        else:
            out.append(cur)
            cur = [(lv, w)]
    out.append(cur)
    return [dict(level=float(np.median([c[0] for c in g])),
                 width=float(np.mean([c[1] for c in g])),
                 n_rows=len(g)) for g in out]


def platform_growth_exponent(widths, steps):
    """The power the bench's width grows with the clock at, log-log.

    Chapter 12 records that the depth-limited attenuation "does not bound the
    platform" and marks the equilibrium-width claim `?`. This returns the
    number that says how far from bounded it is: 1.0 is unattenuated (the
    kinematic W = R*D), 0.0 is saturated. Measured here: 0.55.
    """
    w = np.log(np.asarray(widths, float))
    s = np.log(np.asarray(steps, float))
    return float(np.polyfit(s, w, 1)[0])


def shoreline_x(x, h2, sea_level=SEA_LEVEL):
    """The seaward edge of continuous land, per alongshore row, interpolated.

    Walking SHOREWARD from the offshore boundary and taking the first crossing
    would find the seaward lip of any bench that pokes above the datum. Walking
    seaward from the landward edge finds the shoreline, which is what the bay's
    plan-form is."""
    h2 = np.asarray(h2, float)
    x = np.asarray(x, float)
    out = np.empty(h2.shape[0])
    for j in range(h2.shape[0]):
        row = h2[j]
        i = row.size - 1
        while i > 0 and row[i - 1] > sea_level:
            i -= 1
        if i == 0:
            out[j] = x[0]
            continue
        a, b = row[i - 1], row[i]
        f = 0.0 if b == a else (sea_level - a) / (b - a)
        out[j] = x[i - 1] + f * (x[i] - x[i - 1])
    return out


def platform_width(x, h2, sea_level=SEA_LEVEL, band=0.75):
    """Width of the flat bench at sea level, per alongshore row, metres.

    The wave-cut platform is chapter 12's stated signature of this loop: "the
    terrain is planed off at exactly seaLevel and can go no lower". Measured as
    the cross-shore extent over which the bed sits inside +-`band` of the datum
    -- a bench, not a slope, because a 1:80 ramp crosses that band in 60 m and a
    bench crosses it in as far as it was planed."""
    x = np.asarray(x, float)
    h2 = np.asarray(h2, float)
    dx = float(x[1] - x[0])
    inside = np.abs(h2 - sea_level) <= band
    return inside.sum(axis=1) * dx


def bay_bed(x, y, h_coast, h_init, A=DEAN_A, d_shelf=D_SHELF,
            sea_level=SEA_LEVEL, smooth=True, sand_row=None, beach=True,
            plan=None, keying=None, stand_age=0.0):
    """Compose the coastal loop's plan-form into a submarine bed.

    Chapter 12 draws the line itself and this function is on both sides of it:

      * ABOVE and just below sea level the bed is the coastal loop's own --
        cliff, bench, beach. That band is where the chapter's exception applies
        ("inside the surf zone the bed genuinely is reworked every day").
      * BELOW WAVE BASE the chapter forbids carving and asks for an equilibrium
        ramp instead: "Shape the nearshore as an equilibrium profile, not a
        carved one ... Author it as a graded ramp from shoreline to shelf
        break". So the submarine profile is the Dean ramp -- keyed to the LOCAL
        shoreline the loop produced, which is what makes the contours follow the
        bay.

    The join is a max(), so wherever the loop planed a bench SHALLOWER than the
    ramp the bench survives and the ramp takes over seaward of it. Where a hard
    row was planed further seaward than the soft rows, that bench sticks out
    into deeper water as a shallow rock high -- which is the third break
    mechanism bar section J photographs ("an offshore reef or rock outcrop ...
    with white water over it"), and it is an output rather than a placed object.

    The bed is returned MONOTONE in the cross-shore below the bench, with no
    bar anywhere in it. That is the initial condition the morphodynamic loop is
    measured against, exactly as the 1-D Dean ramp was in wave 1.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    h_coast = np.asarray(h_coast, float)
    x_s = shoreline_x(x, h_coast, sea_level)
    if plan is not None:
        # WAVE 9: THE PLAN-FORM IS SUPPLIED, AND ONLY THE PLAN-FORM.
        # `plan` is a stated shoreline x_s(y) -- the static-equilibrium bay.
        # The coastal loop's own surface is shifted bodily, per row, so that
        # its shoreline lands on the stated one: the cliff, the bench, the
        # hardness field's roughness and the retreat the loop computed all
        # survive unchanged, and the ONLY thing that moves is where the coast
        # is. That is what makes the curved/straight pair one field changed.
        plan = np.asarray(plan, float)
        dxs = plan - x_s
        h_coast = np.stack([np.interp(x - dxs[j], x, h_coast[j])
                            for j in range(y.size)])
        h_init = np.stack([np.interp(x - dxs[j], x, np.asarray(h_init,
                                                               float)[j])
                           for j in range(y.size)])
        x_s = shoreline_x(x, h_coast, sea_level)
    # WAVE 10: WHAT "CROSS-SHORE DISTANCE" MEANS ON A CURVED COAST.
    # `x_s(y) - x` is the offset along the GRID'S X AXIS, and the family of
    # curves it generates is the family of TRANSLATES of the shoreline. That is
    # not the family of NORMAL offsets, and the two agree only where the shore
    # runs parallel to the grid's y axis -- which is every scene waves 1-8
    # rendered and none of the ones with a bay in them. A ray launched normal
    # to a curved shore stays normal to a normal-offset contour and does NOT
    # stay normal to a translate, so the translate family hands refraction an
    # obliquity that is a pure artefact of the grid's orientation:
    # d(theta) = -(d phi_s/dy) * s * sin(phi_s) to first order (see
    # `shoreline_offset`). Wherever a plan-form is STATED -- an analytic curve
    # this file solved for -- the ramp is keyed to the true distance to it.
    #
    # The un-embayed bed keeps the axis keying and that is a decision with a
    # measured reason rather than inertia: its shoreline is the coastal loop's
    # own rock line, whose radius of curvature is 90 m at the hardness field's
    # roughness scale, so its normal offsets FOLD inside the ramp
    # (`offset_fold_fraction`) and the crease is a bigger defect than the
    # obliquity it removes. Named, measured, and not taken.
    if keying is None:
        keying = 'normal' if plan is not None else 'axis'
    if keying == 'normal':
        s = np.maximum(-shoreline_offset(x, y, x_s), 0.0)
    else:
        s = np.maximum(x_s[:, None] - x[None, :], 0.0)      # seaward distance
    h_dean = -np.minimum(A * s ** (2.0 / 3.0), d_shelf)
    touched = (h_coast - np.asarray(h_init, float)) < -0.25
    sea = x[None, :] < x_s[:, None]

    # THE SHOREFACE SAND WEDGE BURIES THE OLD PLATFORM, and it has to, because
    # a max() taken over the whole swath puts a submarine CLIFF where the bench
    # ends. Measured on this scene: the loop planes its bench at -1.85 m and
    # the ramp is already at -3.68 m where the bench stops, so the composition
    # left a 1.8 m step 200 m offshore -- and the 2-D transform duly broke the
    # whole wave field on it, 200 m seaward of where any surf belongs. It was
    # not a bar, it was a join.
    #
    # Chapter 12 says which surface wins and where: below wave base "shape the
    # nearshore as an equilibrium profile, not a carved one ... then let
    # deposition modify it". So the bench survives only inshore of the contour
    # at its own planed depth, where the ramp and the bench are within half a
    # metre of each other and the join is a change of slope rather than a step;
    # seaward of that the sand wedge covers it. The platform is still an output
    # of the coastal loop and still sets the shoreline the ramp is keyed to.
    bench = np.where(touched & sea, h_coast, -1e9)
    with np.errstate(invalid='ignore'):
        b_lvl = np.array([np.median(h_coast[j][touched[j] & sea[j]])
                          if np.any(touched[j] & sea[j]) else 0.0
                          for j in range(h_coast.shape[0])])
    keep = sea & (h_dean > (b_lvl[:, None] - 0.5))
    h = np.where(sea, np.where(keep, np.maximum(h_dean, bench), h_dean), h_coast)
    if smooth:
        # grid-noise scale only, and for the same reason `smooth_depth` gives:
        # a one-cell step in the bed is an infinite convergence to Exner. NOT a
        # wavelength-scale filter -- see `smooth_depth`'s note on chapter 27.
        h = _smooth2(h, 1.0, 1.0)
    # WAVE 12: THE ROCK SURFACE, KEPT. Everything above this line composes a
    # bed; what it does NOT do is record which of the surface is ROCK and which
    # is SEDIMENT LYING ON IT, and that distinction is a landform fact the
    # renderer needs and had no way to ask for. It costs one array: the coastal
    # loop's own surface, plan-shifted with everything else, is the rock; what
    # the composition put ON TOP of it is the regolith.
    #
    # `planed` is the second half of the same statement and it is NOT the same
    # mask. A cell with no sediment on it is bare rock only if the sea has
    # actually stripped it -- the coastal PLATEAU also has zero of this loop's
    # sediment on it and is a soil-mantled land surface that has never been in
    # the surf. `touched` is already computed above (the loop cut this cell by
    # more than 0.25 m), so the discriminator is free and it is an OUTPUT of
    # the loop rather than an elevation band somebody chose.
    h_rock = h_coast.copy()
    bch = None
    if beach:
        # WAVE 8: THE SUBAERIAL BEACH, LAID AFTER THE SMOOTH AND NOT BEFORE.
        # The face slope is the whole point of the landform and a 2 m Gaussian
        # across a 13.8 m ramp rounds 30% of it into the toe and the crest. The
        # wedge is laid on the composed rock and its own joins are exact by
        # construction, so it needs no filter of its own.
        bch = subaerial_beach(x, h, h_rock=h, sea_level=sea_level,
                              sand_row=sand_row,
                              dy=float(y[1] - y[0]) if y.size > 1 else None)
        h = bch['h']
        x_s = shoreline_x(x, h, sea_level)
    reg = np.maximum(h - h_rock, 0.0)
    # WAVE 13: THE EMERGED TREAD'S MANTLE, AND IT IS AN AGE AND NOT A CHOICE.
    #
    # With a sea-level history the plateau stops being an untouched ramp and
    # becomes a bench the sea planed at an older stand -- so `touched` is TRUE
    # over it and, with no sediment on it, `sand_cover_fraction(0) = 0` would
    # paint 45% of the frame as BARE ROCK. That is worse than the flat albedo
    # it replaces and it is also wrong: a bench that emerged one glacial cycle
    # ago has been weathering ever since, and chapter 12's own denudation
    # bracket (0.01-0.1 mm/yr) turns 100 kyr into 1-10 m of mantle. Against
    # ROCK_ROUGH = 0.25 m that is `sand_cover_fraction` = 1.000 and the tread
    # reads as ground. `soil_mantle` is the whole model and it adds no constant
    # this chapter does not already state.
    #
    # WHICH GROUND IS OLD IS AN OUTPUT, not an elevation somebody picked.
    # Planed ground standing above BACKSHORE_Z -- the STORM run-up limit, which
    # wave 8 derived rather than declared -- cannot have been cut by the
    # present stand, because the present stand cannot plane above its own
    # highest swash. So it was cut by an earlier one and is at least one cycle
    # old. Read the other way this is the useful half: bare rock shows on a
    # tread only while its mantle is thinner than one roughness, i.e. for the
    # first ROCK_ROUGH/rate = 2.5-25 kyr after it emerges, so THE LADDER'S
    # RUNGS ARE DISTINGUISHABLE BY THEIR BARE-ROCK SHARE. The present bench,
    # below BACKSHORE_Z, keeps its zero mantle and stays bare.
    if stand_age:
        emerged = touched & (h > BACKSHORE_Z)
        reg = reg + emerged * float(soil_mantle(stand_age))
    cover = sand_cover_fraction(reg)
    # NOT `h_rock`: `subaerial_beach` already returns that name for the
    # PRE-BEACH COMPOSED bed, which `_sec_beach` measures the wedge's width
    # against. This one is the coastal loop's own bedrock, which is a different
    # surface wherever the Dean ramp took over, and renaming the old key would
    # have moved a suite row for no reason.
    surf = dict(h_bedrock=h_rock, regolith=reg, cover=cover, planed=touched)
    if bch is not None:
        bch = dict(bch)
        bch.update(surf)
    else:
        bch = surf
    return h, x_s, h_dean, bch


def _gauss1(a, sigma_cells, axis):
    """Gaussian blur along one axis with edge padding, sigma in CELLS."""
    if sigma_cells <= 1e-6:
        return np.asarray(a, float).copy()
    rad = int(math.ceil(3.0 * sigma_cells))
    t = np.arange(-rad, rad + 1, dtype=float)
    w = np.exp(-0.5 * (t / sigma_cells) ** 2)
    w /= w.sum()
    a = np.asarray(a, float)
    a = np.moveaxis(a, axis, -1)
    pad = np.concatenate([np.repeat(a[..., :1], rad, axis=-1), a,
                          np.repeat(a[..., -1:], rad, axis=-1)], axis=-1)
    out = np.apply_along_axis(lambda v: np.convolve(v, w, mode='valid'), -1,
                              pad)
    return np.moveaxis(out, -1, axis)


def _smooth2(a, sig_x_cells, sig_y_cells):
    return _gauss1(_gauss1(a, sig_x_cells, -1), sig_y_cells, 0)


def smooth_depth_2d(d, dx, dy, scale_x, scale_y):
    """The 2-D twin of `smooth_depth`, separable, at the GRID-NOISE scale.

    Same argument and the same disagreement with chapter 27 recorded there: the
    filter exists so that one-cell bed noise cannot dither the break line in a
    loop that is writing the bed it reads, and it is set at 1.5 cells rather
    than at a wavelength, because a wavelength-scale filter hides the bar from
    the wave that is supposed to break on it."""
    return _smooth2(np.asarray(d, float), scale_x / dx, scale_y / dy)


# ============================================================================
# THE OFFSHORE DIRECTIONAL SPECTRUM, AND THE REALISATION DRAWN FROM IT
# ============================================================================
#
# WAVE 13'S FINDING, STATED FIRST BECAUSE IT IS THE ROUND'S DELIVERABLE.
# Waves 1-12 assumed a directional spread of EXACTLY ZERO and a frequency
# spread of exactly zero. `transform_2d` marches ONE (T, theta0) pair; the
# renderer's open sea beyond the domain was one plane wave,
#
#       eta = (H0/2) cos( k0 (x cos th0 + y sin th0) )
#
# whose crests are straight lines of infinite length. Measured on the scene's
# own grid before this wave: the phase S varied by 0.063 rad ALONGSHORE across
# 1408 m of coast -- one hundredth of a wavelength -- and the height H by 0.7%.
# That is not a small spread. It is a delta function, s = infinity, and the
# critic's word for what it draws was "corrugated roofing".
#
# Standing ruling 5 says the wave field arrives from OUTSIDE with a stated
# offshore spectrum, so short-crestedness and groupiness are OUTPUTS. That
# forces the shape of the fix: the spread cannot be a knob, it has to fall out
# of a spectrum whose parameters are already declared. Two are (H0, T); the
# third is the WIND, which this scene has already declared for the glitter.
#
# ---- WHAT WAS READ, this wave, before any of this was written (ruling 9)
#
#   Goda, Y. (2008/2010), "Overview on the applications of random wave concept
#   in coastal engineering" (Proc. Japan Acad. Ser. B; open access). Gives the
#   Mitsuyasu-type spreading in the form used below --
#       G(f; th) = G0 cos^(2s)((th - th0)/2)
#       s = smax (f/fp)^5     f <= fp
#       s = smax (f/fp)^-2.5  f >  fp
#   and Goda & Suzuki's engineering values smax = 10 (wind waves), 25 (swell,
#   short decay), 75 (swell, long decay), with a 2001 New Zealand buoy record
#   of smax ~ 65 for long-travelled swell quoted in support.
#
#   WAFO (Lund University) `spreading` documentation, which states the
#   normalisation explicitly as N(s) = gamma(s+1)/(2 sqrt(pi) gamma(s+1/2)),
#   attributes the cos-2s form to Longuet-Higgins, Cartwright & Smith (1963),
#   and lists the two wave-age parameterisations of the peak spread:
#       Mitsuyasu et al. (1975)   sp = 11.5 (U10/cp)^-2.5,  ma = 5, mb = -2.5
#       Hasselmann et al. (1980)  spa = 6.97, spb = 9.77, ma = 4.06,
#                                 mb = -2.33 - 1.45 (U10/cp - 1.17)
#
# Neither the Fourier-coefficient identity nor the crest-length ratio below was
# taken from either source. Both are derived here and both are checked against
# quadrature in the suite, which is the only reason they are allowed to be
# written down at all.
#
# ---- (S1) THE SPREADING FUNCTION AND ITS MOMENTS
#
# D(th; s) = N(s) cos^(2s)(th/2) on (-pi, pi], with th measured from the mean
# direction. Its Fourier coefficients have a closed form. Write
# cos^(2s)(th/2) = ((1 + cos th)/2)^s and use the beta integral; the result is
#
#       <cos n th>  =  Gamma(s+1)^2 / ( Gamma(s+1-n) Gamma(s+1+n) )       (S1)
#
# which is USELESS AS WRITTEN in floating point -- Gamma(s+1-n) is negative for
# s < n-1 and lgamma throws its sign away, and both gammas overflow by s = 200.
# The same quantity as a product of n ratios is exact, sign-correct and cannot
# overflow:
#
#       <cos n th>  =  PROD_{m=1..n} (s + 1 - m) / (s + m)                (S1')
#
# n = 1 gives s/(s+1), the textbook first moment; n = 2 gives
# s(s-1)/((s+1)(s+2)), which is NEGATIVE for s < 1 and that sign is physical --
# a spread broader than cos^2(th/2) has more energy across the mean direction
# than along it. `spread_moment` is (S1'); the suite checks it against a
# 4-million-point quadrature of D at eight values of s including s < 1.
#
# ---- (S2) THE CREST-LENGTH RATIO, WHICH IS THE ROUND'S FALSIFIABLE PREDICTION
#
# Short-crestedness is not a look. It is a second-moment statement about the
# surface covariance, and it can be measured off a generated field without
# looking at a picture. For a field of components all at wavenumber magnitude k
# spread in direction by D,
#
#       rho(xi, eta) = INT D(th) cos( k(xi cos th + eta sin th) ) dth
#
# and expanding cos to second order in the separation (the only order a
# correlation LENGTH depends on),
#
#       rho ~ 1 - (k^2/2) [ xi^2 <cos^2 th> + eta^2 <sin^2 th> ]
#
# with the cross term vanishing by the symmetry of D. So the curvature of the
# correlation surface at zero lag is k^2<cos^2 th> across the crest and
# k^2<sin^2 th> along it, the two correlation lengths are the reciprocal square
# roots of those, and their RATIO is free of k entirely:
#
#       L_along / L_across = sqrt( <cos^2 th> / <sin^2 th> )
#                          = sqrt( (1 + <cos 2th>) / (1 - <cos 2th>) )
#
# Substituting (S1') at n = 2 and clearing the denominators,
#
#       1 + <cos2th> = [ (s+1)(s+2) + s(s-1) ] / [(s+1)(s+2)] = (2s^2+2s+2)/D
#       1 - <cos2th> = [ (s+1)(s+2) - s(s-1) ] / [(s+1)(s+2)] = (4s+2)/D
#
#       ==>   L_along / L_across  =  sqrt( (s^2 + s + 1) / (2 s + 1) )    (S2)
#
# That is the whole prediction, and it has teeth in both limits: s -> 0 (a flat
# spread, isotropic) gives exactly 1, and s -> infinity gives sqrt(s/2) -> the
# infinite crest waves 1-12 drew. s = 25 gives 3.57, s = 75 gives 6.14.
# `crest_length_ratio` is (S2) and `measure_anisotropy` measures it back off a
# generated field by fitting that curvature. If the field does not return the s
# it was drawn from, the realisation is wrong -- and that test is the reason
# this section exists rather than a picture that looks choppier.
#
# (S2) IS FOR ONE WAVENUMBER. A real spectrum spreads in frequency too, and
# then the curvatures are <k^2 cos^2 th> and <k^2 sin^2 th> over the whole
# 2-D spectrum, which is `spectrum_anisotropy` by quadrature. The two disagree
# HARD here and the disagreement is the physics: s falls as (f/fp)^-2.5 above
# the peak while k^2 rises as f^4, so the short waves are both heavily weighted
# and nearly isotropic, and they drag the ratio down a long way below (S2) at
# smax. THE RATIO THEREFORE DEPENDS ON THE BAND, and any number quoted for it
# is meaningless without one. Both this file and the suite quote the band.

U10_SCENE = 6.0         # m/s. THE SAME WIND `beach_optics.U10` gives the
                        # glitter, and it is `?` there for the same reason: the
                        # wind at the frame's hour is unknown. It is repeated
                        # here rather than imported because `beach.py` is the
                        # lower layer and must not depend on the optics module;
                        # the suite carries a row that FAILS if the two ever
                        # differ, which is the only honest way to hold one
                        # number in two files. One wind, three readouts now:
                        # the glitter's width, the whitecap coverage, and the
                        # directional spread of the swell.
JONSWAP_GAMMA = 3.3     # Hasselmann et al. (1973), the JONSWAP mean peak
                        # enhancement. `?` -- it is a mean over a fetch-limited
                        # North Sea campaign and this is Atlantic swell, for
                        # which a larger value would be defensible. Nothing in
                        # the crest-length prediction is sensitive to it: the
                        # suite carries the anisotropy at gamma = 1 (Pierson-
                        # Moskowitz) and at gamma = 7 and the ratio moves by
                        # under 2%, because gamma reshapes the peak and the
                        # ratio is set by the TAIL.
JONSWAP_SIGMA_A = 0.07  # Hasselmann et al. (1973), the peak-width parameters
JONSWAP_SIGMA_B = 0.09  # below and above fp. `P`.
MITSUYASU_SP = 11.5     # Mitsuyasu et al. (1975) via WAFO: sp = 11.5 w^-2.5
MITSUYASU_MB = -2.5     # with w = U10/cp the inverse wave age. Above the peak
MITSUYASU_MA = 5.0      # s falls as (f/fp)^mb, below it rises as (f/fp)^ma.
SPREAD_BAND = (0.55, 2.6)   # the synthesis band, in units of fp. See
                            # `spectral_components` for why it is this and not
                            # (0, inf), and `spectral_band_energy` for what it
                            # costs.


def jonswap(f, hs, fp, gamma=JONSWAP_GAMMA, g=G):
    """The JONSWAP frequency spectrum S(f), m^2/Hz, scaled to a stated Hs.

    Hasselmann et al. (1973):

        S(f) = alpha g^2 (2 pi)^-4 f^-5 exp(-1.25 (f/fp)^-4) * gamma^b
        b    = exp( -(f - fp)^2 / (2 sigma^2 fp^2) ),  sigma = 0.07 / 0.09

    ALPHA IS NOT AN INPUT HERE. The scene declares a deep-water HEIGHT, so
    alpha is whatever makes the zeroth moment come out at (Hs/4)^2 -- one
    published constant fewer, and the input the rest of this file already
    uses. The normalisation is done on the SAME band the realisation is drawn
    from wherever a realisation is involved; see `spectral_components`.
    """
    f = np.asarray(f, float)
    fp = float(fp)
    pos = f > 0.0
    ff = np.where(pos, f, 1.0)
    sig = np.where(ff <= fp, JONSWAP_SIGMA_A, JONSWAP_SIGMA_B)
    b = np.exp(-((ff - fp) ** 2) / (2.0 * sig ** 2 * fp ** 2))
    shape = (ff ** -5.0) * np.exp(-1.25 * (ff / fp) ** -4.0) * gamma ** b
    shape = np.where(pos, shape, 0.0)
    # the alpha that puts m0 at (Hs/4)^2, by the same quadrature the caller
    # would use. Done on a dense log grid over the full spectrum.
    fq = np.geomspace(0.2 * fp, 20.0 * fp, 4096)
    sq = np.where(fq <= fp, JONSWAP_SIGMA_A, JONSWAP_SIGMA_B)
    bq = np.exp(-((fq - fp) ** 2) / (2.0 * sq ** 2 * fp ** 2))
    shq = (fq ** -5.0) * np.exp(-1.25 * (fq / fp) ** -4.0) * gamma ** bq
    m0_shape = np.trapezoid(shq, fq)
    return shape * ((hs / 4.0) ** 2) / m0_shape


def deep_phase_speed(T, g=G):
    """c_p = g T / (2 pi), the deep-water phase speed at the peak."""
    return g * float(T) / (2.0 * math.pi)


def spread_smax(u10=U10_SCENE, T=T_SWELL):
    """Mitsuyasu et al. (1975): smax = 11.5 (U10/c_p)^-2.5, from wave age.

    THE SPREAD IS AN OUTPUT AND THIS IS THE LINE THAT MAKES IT ONE. The scene
    states a wind and a peak period; the inverse wave age U10/c_p follows, and
    with it the peak directional spread. Nothing is dialled.

    `?`, AND IT IS A LOUD ONE. Mitsuyasu's relation was fitted to WIND SEA,
    over inverse wave ages of roughly 0.4 to 2 -- seas still under the wind
    that raised them. This scene is a 9 s swell under a 6 m/s wind, c_p = 14.05
    m/s and U10/c_p = 0.427, which is off the low end of the fitted range and
    the relation is being EXTRAPOLATED into swell. It returns smax = 96.6,
    narrower than Goda & Suzuki's 75 for "swell with long decay distance" and
    than the 65 measured off New Zealand. Both of those are the sanity check,
    and the suite carries them as a bracket rather than this comment carrying
    them as a claim: the answer must land in 25..150 or the extrapolation has
    gone somewhere the literature does not go.
    """
    w = float(u10) / deep_phase_speed(T)
    return MITSUYASU_SP * w ** MITSUYASU_MB


def spread_s(f, fp, smax):
    """Goda's frequency dependence of the spread parameter.

    s = smax (f/fp)^5 below the peak, smax (f/fp)^-2.5 above it. The spread is
    NARROWEST at the peak and broadens both ways, which is the observation the
    two exponents encode; the field's high-frequency components are close to
    isotropic and that is what breaks the crests up.
    """
    r = np.asarray(f, float) / float(fp)
    return float(smax) * np.where(r <= 1.0, r ** MITSUYASU_MA,
                                  r ** MITSUYASU_MB)


def spread_norm(s):
    """N(s) = Gamma(s+1) / (2 sqrt(pi) Gamma(s+1/2)).

    Longuet-Higgins, Cartwright & Smith (1963) via WAFO. Evaluated through
    lgamma because Gamma(s+1) overflows a double by s = 170 and this scene's
    own s is 96.6 at the peak with larger values below it.
    """
    return np.exp(_gammaln(np.asarray(s, float) + 1.0)
                  - _gammaln(np.asarray(s, float) + 0.5)) / (
                      2.0 * math.sqrt(math.pi))


_gammaln = np.vectorize(math.lgamma, otypes=[float])


def spread_pdf(theta, s):
    """D(theta; s) = N(s) cos^(2s)(theta/2), theta from the MEAN direction.

    Normalised to unit integral over (-pi, pi]; the suite checks that by
    quadrature at eight values of s rather than trusting the gamma ratio.
    """
    theta = np.asarray(theta, float)
    s = np.asarray(s, float)
    c = np.cos(0.5 * theta)
    # cos^(2s) via logs, so that s ~ 1e2 and cos ~ 1e-3 do not underflow to a
    # zero that the normalisation then divides into.
    with np.errstate(divide='ignore', invalid='ignore'):
        lg = 2.0 * s * np.log(np.abs(c))
    return spread_norm(s) * np.where(np.abs(c) > 0.0, np.exp(lg), 0.0)


def spread_moment(s, n):
    """<cos n theta> for D(theta; s), by (S1') -- a product of n ratios.

    Exact, sign-correct for s < n-1 where the gamma form goes negative, and
    free of overflow at any s. n must be a non-negative integer.
    """
    s = np.asarray(s, float)
    n = int(n)
    if n < 0:
        raise ValueError('n must be >= 0')
    p = np.ones_like(s)
    for m in range(1, n + 1):
        p = p * (s + 1.0 - m) / (s + m)
    return p


def crest_length_ratio(s):
    """(S2): L_along / L_across = sqrt( (s^2 + s + 1) / (2 s + 1) ).

    The ratio of the alongshore to the cross-crest correlation length for a
    SINGLE-WAVENUMBER field spread by cos^(2s)(theta/2). Derived above; checked
    against `spread_moment(s, 2)` and against quadrature in the suite.

    1 at s = 0 (isotropic), 3.573 at s = 25, 6.145 at s = 75, ~sqrt(s/2) as
    s -> infinity. A field whose measured ratio is not this one was not drawn
    from this spreading function.
    """
    s = np.asarray(s, float)
    return np.sqrt((s * s + s + 1.0) / (2.0 * s + 1.0))


def spectrum_moment_tensor(T=T_SWELL, u10=U10_SCENE, theta0=THETA0_SWELL,
                           band=SPREAD_BAND, gamma=JONSWAP_GAMMA, hs=None,
                           n_f=2048, n_th=1441, g=G, smax=None):
    """The wavenumber second-moment tensor <k_i k_j> of the stated spectrum.

    M = [[<kx^2>, <kx ky>], [<kx ky>, <ky^2>]] normalised by m0, by quadrature
    over E(f, th) = S(f) D(th - theta0; s(f)) with k = (2 pi f)^2/g.

    THE BAND IS AN ARGUMENT AND NOT A DEFAULT BURIED IN THE MATHS. The second
    moment of a f^-5 tail against k^2 ~ f^4 is logarithmically divergent, so
    <k^2 .> has no value without an upper limit, and the limit that matters is
    the one the REALISATION is drawn over -- a field cannot be anisotropic at
    wavelengths it does not contain.
    """
    fp = 1.0 / float(T)
    hs = 4.0 * math.sqrt((H0_SWELL ** 2) / 8.0) if hs is None else float(hs)
    f = np.geomspace(band[0] * fp, band[1] * fp, n_f)
    dth = np.linspace(-math.pi, math.pi, n_th)         # from the MEAN direction
    S = jonswap(f, hs, fp, gamma)
    s = spread_s(f, fp, spread_smax(u10, T) if smax is None else float(smax))
    k = (2.0 * math.pi * f) ** 2 / g
    w = S * k ** 2                                     # (n_f,)
    D = spread_pdf(dth[None, :], s[:, None])           # (n_f, n_th)
    ang = float(theta0) + dth                          # in the GRID frame
    xx = np.trapezoid(D * np.cos(ang)[None, :] ** 2, dth, axis=1)
    yy = np.trapezoid(D * np.sin(ang)[None, :] ** 2, dth, axis=1)
    xy = np.trapezoid(D * (np.cos(ang) * np.sin(ang))[None, :], dth, axis=1)
    m0 = float(np.trapezoid(S, f))
    return (float(np.trapezoid(w * xx, f) / m0),
            float(np.trapezoid(w * xy, f) / m0),
            float(np.trapezoid(w * yy, f) / m0))


def anisotropy_from_tensor(Mxx, Mxy, Myy, frame='crest'):
    """Turn a second-moment tensor into a correlation-length ratio.

    THE RATIO IS A PROPERTY OF THE FRAME IT IS MEASURED IN, AND THIS FUNCTION
    EXISTS BECAUSE THIS WAVE GOT THAT WRONG FIRST. The prediction was written
    in the frame of the MEAN WAVE DIRECTION and the measurement was taken in
    the frame of the GRID; at this scene's 20 deg of obliquity the two differ
    by 60 per cent, and the disagreement looked exactly like a broken
    realisation until the tensor was written down. Both numbers are real and
    they answer different questions:

      frame='crest'  sqrt(lam_max/lam_min) of M -- the INTRINSIC ratio, the one
                     (S2) predicts and the one the spread means. Free of how
                     the coast happens to be oriented.
      frame='grid'   sqrt(Mxx/Myy) -- the APPARENT ratio, alongshore against
                     cross-shore, which is what a frame edge measures and what
                     the critic's statistic sees. Always the SMALLER of the two
                     for an oblique sea, because an oblique crest crosses the
                     frame diagonally and its alongshore run is foreshortened.

    The principal axis of M is the mean wave direction exactly, for any
    spreading function symmetric about it; the suite checks that, and a
    spreading function accidentally written asymmetric would fail it.
    """
    if frame == 'grid':
        return math.sqrt(Mxx / Myy)
    if frame != 'crest':
        raise ValueError("frame must be 'crest' or 'grid'")
    tr = Mxx + Myy
    dt = math.sqrt(max((Mxx - Myy) ** 2 + 4.0 * Mxy ** 2, 0.0))
    return math.sqrt((tr + dt) / (tr - dt))


def tensor_principal_angle(Mxx, Mxy, Myy):
    """The direction of M's largest eigenvalue, rad from +x."""
    return 0.5 * math.atan2(2.0 * Mxy, Mxx - Myy)


def spectrum_anisotropy(frame='crest', **kw):
    """The crest-length ratio the drawn field must return, in a stated frame."""
    return anisotropy_from_tensor(*spectrum_moment_tensor(**kw), frame=frame)


def smax_from_anisotropy(ratio, frame='crest', lo=1.0, hi=4000.0, tol=1e-9,
                         **kw):
    """INVERT the prediction: what smax would a field of this ratio have been
    drawn from?

    THIS IS THE ROUND-TRIP STATED AS ONE NUMBER. Measuring a ratio close to the
    predicted one is a comparison; recovering the SPREAD PARAMETER back out of
    a generated field and finding the value it was drawn at is the round trip,
    and it is the form the finding is reported in. Bisection on
    `spectrum_anisotropy`, which is monotone in smax over any band because a
    narrower spread cannot lower a second-moment ratio at any frequency.
    """
    kw.pop('smax', None)

    def g(sm):
        return spectrum_anisotropy(frame=frame, smax=sm, **kw) - float(ratio)

    a, b = float(lo), float(hi)
    ga, gb = g(a), g(b)
    if ga * gb > 0.0:
        raise ValueError('the ratio %.4f is outside smax in [%g, %g]'
                         % (ratio, lo, hi))
    for _ in range(200):
        m = 0.5 * (a + b)
        gm = g(m)
        if ga * gm <= 0.0:
            b, gb = m, gm
        else:
            a, ga = m, gm
        if b - a < tol * max(1.0, b):
            break
    return 0.5 * (a + b)


def spectral_band_energy(T=T_SWELL, band=SPREAD_BAND, gamma=JONSWAP_GAMMA,
                         hs=None, n_f=4096):
    """The fraction of m0 that lies inside the synthesis band. Reported, not
    hidden: what is outside it is the wind sea the glitter already carries
    statistically, and saying so is the whole of the honesty here."""
    fp = 1.0 / float(T)
    hs = 4.0 * math.sqrt((H0_SWELL ** 2) / 8.0) if hs is None else float(hs)
    f_all = np.geomspace(0.2 * fp, 20.0 * fp, n_f)
    f_bnd = np.geomspace(band[0] * fp, band[1] * fp, n_f)
    m_all = np.trapezoid(jonswap(f_all, hs, fp, gamma), f_all)
    m_bnd = np.trapezoid(jonswap(f_bnd, hs, fp, gamma), f_bnd)
    return float(m_bnd / m_all)


# ---------------------------------------------------------- the realisation
# DRAW THE FIELD, NOT ITS STATISTICS. Wave 12 found the same error in four
# places -- a distribution painted where a realisation belongs -- and a
# directional spectrum shaded as a smooth mean would be the fifth. What follows
# is a component list with PHASES, summed into a surface; the spectrum is
# recoverable from it and is recovered from it, in the suite.
#
# THE LATTICE IS STRATIFIED AND JITTERED, and both halves matter.
#   * A regular (f, th) lattice makes the sum PERIODIC in space with the period
#     of the wavenumber lattice, which draws a tiling no sea has. Jittering each
#     component inside its own cell destroys the lattice and keeps the sample
#     spectrum exact to O(1/N) -- it is stratified sampling and nothing more.
#   * The amplitudes are DETERMINISTIC, a_j = sqrt(2 E(f_j, th_j) df dth), and
#     only the phase is random. That is a deliberate choice of instrument: with
#     random (Rayleigh) amplitudes the sample spectrum fluctuates and a failed
#     round-trip could always be blamed on the draw. With deterministic
#     amplitudes the sample spectrum is exact by construction, so a failed
#     round-trip can ONLY be a geometry error -- a direction convention, an
#     aliased wavenumber, a lattice, a lost factor. That is the error class this
#     round is hunting. `rayleigh=True` restores the physical draw, and the
#     suite runs both: the Rayleigh case is the control that says how much of
#     any residual is sampling noise (ruling 14 -- a near-zero is worthless
#     until zero has been shown to be reachable).
# THE VARIANCE IS THE TRANSFORM'S OWN. E0 = rho g H0^2 / 8 means m0 = H0^2/8,
# so H0_SWELL = 1.5 m is an H_rms and the significant height is 4 sqrt(m0) =
# 2.12 m. Getting that backwards is a factor of sqrt(2) on every amplitude in
# the scene and it is a suite row, not a comment.


def spectral_components(T=T_SWELL, H0=H0_SWELL, theta0=THETA0_SWELL,
                        u10=U10_SCENE, band=SPREAD_BAND,
                        gamma=JONSWAP_GAMMA, n_f=10, n_th=24, seed=20260913,
                        rayleigh=False, smax=None, g=G):
    """A realisation of the stated offshore directional spectrum.

    OUT: dict with kx, ky (rad/m), omega (rad/s), a (m, amplitude), phase
         (rad), plus the s(f) the components were drawn at and the m0 they
         carry. eta(x, y, t) = SUM a_j cos(kx_j x + ky_j y - omega_j t + ph_j).

    The mean direction is theta0 off shore-normal, measured the same way the
    transform measures it: +x is shoreward, theta is the angle of the wave
    ORTHOGONAL from +x, so kx = k cos(theta), ky = k sin(theta).
    """
    fp = 1.0 / float(T)
    hs = 4.0 * math.sqrt(float(H0) ** 2 / 8.0)
    smax = spread_smax(u10, T) if smax is None else float(smax)
    rng = np.random.default_rng(seed)

    # ---- frequency: log-stratified cells with a jitter inside each. Log and
    # not linear because the k^2 moments this field is tested against live in
    # the TAIL, and log spacing puts equal numbers of components per octave.
    fe = np.geomspace(band[0] * fp, band[1] * fp, n_f + 1)
    uf = rng.random(n_f)
    f = fe[:-1] * (fe[1:] / fe[:-1]) ** uf
    df = fe[1:] - fe[:-1]
    s = spread_s(f, fp, smax)
    S = jonswap(f, hs, fp, gamma)

    # ---- direction: EQUAL-ENERGY cells, by inverting the directional CDF.
    #
    # THIS WAS A UNIFORM FAN OVER THE CIRCLE AND THAT WAS THE ROUND'S SECOND
    # REAL DEFECT. At this scene's own spread the peak's lobe is 9.7 deg wide
    # at half maximum, so a uniform fan of 20 directions -- 18 deg a cell --
    # put TWO components inside the lobe at the peak frequency out of forty at
    # that frequency. The drawn field was therefore very nearly two plane waves
    # where it matters most, and it still looked like corrugated roofing.
    #
    # AND THE SECOND-MOMENT ROUND TRIP PASSED ANYWAY, recovering smax to 3.5
    # per cent. It passed because <k^2 cos^2> and <k^2 sin^2> are dominated by
    # the broad, well-sampled high-frequency tail, while what an eye reads is
    # the narrow peak. That is wave 12's lesson in a new place -- a statistic
    # that stays right under a defect because the quantity it averages is
    # always right -- and it is why the suite now carries a lobe-occupancy row
    # beside the moment row. The moment row alone would have shipped this.
    #
    # Inverting the CDF puts n_th components at each frequency spaced by EQUAL
    # ENERGY, so a lobe of any width gets its proportionate share of them, and
    # every component carries the same amplitude. No cell width is chosen.
    n_grid = 8192
    tg = np.linspace(-math.pi, math.pi, n_grid)
    Dg = spread_pdf(tg[None, :], s[:, None])
    cdf = np.cumsum(0.5 * (Dg[:, 1:] + Dg[:, :-1]) * np.diff(tg), axis=1)
    cdf = np.concatenate([np.zeros((n_f, 1)), cdf], axis=1)
    cdf = cdf / cdf[:, -1:]
    ut = (np.arange(n_th)[None, :] + rng.random((n_f, n_th))) / n_th
    th = np.empty((n_f, n_th))
    for i in range(n_f):
        th[i] = np.interp(ut[i], cdf[i], tg)

    # equal energy inside a frequency; the frequency cell's own share across
    # them. Renormalised to the band's energy so a coarse lattice's quadrature
    # error cannot leak into H0.
    E = np.broadcast_to((S * df)[:, None], (n_f, n_th)) / float(n_th)
    frac = spectral_band_energy(T, band, gamma, hs)
    E = E * (frac * (hs / 4.0) ** 2) / E.sum()

    a = np.sqrt(2.0 * E)
    if rayleigh:
        # the physical draw: a complex Gaussian per component, whose modulus is
        # Rayleigh with the same mean square. Phase falls out of the same draw.
        z = (rng.normal(size=E.shape) + 1j * rng.normal(size=E.shape))
        z = z / math.sqrt(2.0)
        a = np.abs(z) * np.sqrt(2.0 * E)
        ph = np.angle(z)
    else:
        ph = rng.uniform(0.0, 2.0 * math.pi, E.shape)

    om = 2.0 * math.pi * np.broadcast_to(f[:, None], th.shape)
    k = om ** 2 / g                                          # deep water
    ang = float(theta0) + th
    return dict(kx=(k * np.cos(ang)).ravel(), ky=(k * np.sin(ang)).ravel(),
                omega=om.ravel(), a=a.ravel(), phase=ph.ravel(),
                k=k.ravel(), theta=ang.ravel(), f=om.ravel() / (2 * math.pi),
                theta0=float(theta0),
                s=s, smax=smax, fp=fp, band=band, m0=float(0.5 * (a ** 2).sum()),
                band_fraction=frac, n=a.size, rayleigh=bool(rayleigh))


FOOT_SIGMA = 1.0 / math.sqrt(12.0)      # a square footprint of side a has the
                                        # second moment of a Gaussian of this
                                        # sigma; Var(U(-a/2, a/2)) = a^2/12.


def spectral_eta(comp, xw, yw, t=0.0, foot=None):
    """The free surface of a component list at (x, y, t).

    LINEAR, AND THAT IS STATED. The second-order bound harmonic is
    `nonlinear_eta`'s job and it is applied to a carrier, not to each component
    of a bundle -- a second-order sum over a spectrum needs the full quadratic
    interaction kernel, which is a different piece of physics and is not in
    this file. In deep water the correction is a k0/2 = 1.9 per cent of
    amplitude at this swell, so the leading order is the whole of it out there.

    `foot` IS THE BAND LIMIT AND IT IS NOT A BLUR. A short-crested realisation
    drawn per pixel and sampled once per pixel ALIASES, and trading banding for
    sparkle noise would not be an improvement -- it would be the same class of
    error in a different octave. What a pixel sees is the surface averaged over
    its own footprint, and averaging over a footprint is a CONVOLUTION, so in
    the spectrum it is a multiplication:

        eta * g   ==>   a_j -> a_j * exp( -k_j^2 sigma^2 / 2 )

    for a Gaussian kernel of standard deviation sigma, exactly, with no
    approximation and no filter width chosen by eye. A square footprint of side
    `foot` has variance foot^2/12, so sigma = foot/sqrt(12) matches its second
    moment -- the only property of the kernel this expression uses.

    Nothing is lost by this: what the footprint removes is exactly the variance
    the glitter's slope distribution is already carrying statistically, which
    is the argument `beach_optics.mss_fraction_below` already makes for the
    same cutoff from the other side. `foot` broadcasts against xw/yw, so every
    pixel gets its own band.
    """
    xw = np.asarray(xw, float)
    yw = np.asarray(yw, float)
    out = np.zeros(np.broadcast(xw, yw).shape, float)
    kx, ky, a, ph, om = (comp['kx'], comp['ky'], comp['a'], comp['phase'],
                         comp['omega'])
    if foot is None:
        for j in range(a.size):
            out += a[j] * np.cos(kx[j] * xw + ky[j] * yw - om[j] * t + ph[j])
        return out
    s2 = (np.asarray(foot, float) * FOOT_SIGMA) ** 2
    k2 = comp['k'] ** 2
    for j in range(a.size):
        out += (a[j] * np.exp(-0.5 * k2[j] * s2)
                * np.cos(kx[j] * xw + ky[j] * yw - om[j] * t + ph[j]))
    return out


def measure_anisotropy(eta, dx, dy, n_lag=6):
    """Measure L_along / L_across back off a GENERATED field. The round trip.

    The curvature of the correlation surface at zero lag is fitted, in each
    axis separately, from the first `n_lag` lags:

        rho(r) ~ 1 - (1/2) C r^2   ==>   L = 1/sqrt(C)

    and the ratio L_y/L_x is returned. Only the ratio is claimed -- the
    individual lengths depend on the band's upper limit, the ratio much less
    so, and it is the ratio that (S2) predicts.

    IN: eta (ny, nx), sampled on a uniform grid at spacing dy, dx.

    THE FIT IS ON rho ITSELF AND NOT ON log rho, and the lag window is short.
    A Gaussian or exponential fit over many lags measures the correlation
    SHAPE, which is a different statistic; the second moment of the spectrum is
    the curvature AT ZERO and only short lags see it.
    """
    e = np.asarray(eta, float)
    e = e - e.mean()
    v = float((e * e).mean())
    if v <= 0.0:
        raise ValueError('a field with no variance has no correlation length')
    cx, cy = [], []
    for m in range(1, n_lag + 1):
        cx.append(float((e[:, m:] * e[:, :-m]).mean()) / v)
        cy.append(float((e[m:, :] * e[:-m, :]).mean()) / v)
    lx = (np.arange(1, n_lag + 1) * dx) ** 2
    ly = (np.arange(1, n_lag + 1) * dy) ** 2
    # least squares through the origin on (1 - rho) vs r^2, slope = C/2
    Cx = 2.0 * float(np.dot(lx, 1.0 - np.array(cx)) / np.dot(lx, lx))
    Cy = 2.0 * float(np.dot(ly, 1.0 - np.array(cy)) / np.dot(ly, ly))
    return dict(L_across=1.0 / math.sqrt(Cx), L_along=1.0 / math.sqrt(Cy),
                ratio=math.sqrt(Cx / Cy), Mxx=Cx, Myy=Cy,
                rho_x=np.array(cx), rho_y=np.array(cy))


def measure_tensor_fft(eta, dx, dy, window=True):
    """The second-moment tensor of a SAMPLED field, from its own 2-D FFT.

    THE SECOND ROUTE, AND IT SHARES NOTHING WITH THE FIRST. `measure_anisotropy`
    fits the curvature of the correlation surface at short lag, which is a
    real-space statistic with a truncation bias of order (k L)^2 that has to be
    argued away. This one is Parseval: the periodogram IS the sample spectrum,
    so <k_i k_j> is a weighted sum over it.

    THE WINDOW IS NOT COSMETIC AND THE UNWINDOWED VERSION IS KEPT SO THAT THE
    SUITE CAN SHOW IT. A drawn field is not periodic on its patch -- the
    components' wavenumbers are nowhere near the FFT lattice -- so the
    periodogram leaks, and leakage falls only as k^-2 while this statistic
    weights by k^+2. Measured on this scene's own realisation: 99.9 per cent of
    the ENERGY is inside the synthesis band and only 93.8 per cent of the
    k^2-weighted energy is, and the unwindowed tensor reports a crest-frame
    ratio of 2.74 against the 3.52 the spectrum it was drawn from predicts --
    a 22 per cent error that looks exactly like a broken realisation. With a
    Hann window both figures are 100.0 per cent and the ratio is 3.46. A
    second moment is the statistic leakage hurts most, and a meter that is
    wrong by 22 per cent would have condemned a field that was right.

    The window's own kernel adds its second moment to both diagonal terms --
    about +11 per cent here -- which nearly cancels in the RATIO and is why
    only the ratio is claimed. What this route CANNOT see is aliasing, because
    an aliased component appears at a real wavenumber and is counted there;
    that is what the correlation route is for, and the two agreeing is the
    evidence.

    IN: eta (ny, nx) on a uniform grid. OUT: (Mxx, Mxy, Myy), rad^2/m^2.
    """
    e = np.asarray(eta, float)
    e = e - e.mean()
    ny, nx = e.shape
    if window:
        e = e * (np.hanning(ny)[:, None] * np.hanning(nx)[None, :])
    P = np.abs(np.fft.fft2(e)) ** 2
    kx = 2.0 * math.pi * np.fft.fftfreq(nx, dx)[None, :]
    ky = 2.0 * math.pi * np.fft.fftfreq(ny, dy)[:, None]
    w = P.sum()
    return (float((P * kx ** 2).sum() / w), float((P * kx * ky).sum() / w),
            float((P * ky ** 2).sum() / w))


def extrusion_ratio(F, smooth=None):
    """THE CRITIC'S OWN STATISTIC, on a scene-linear field rather than a PNG.

    A field that is a 1-D profile extruded along the crest has F = f(across)
    alone. The critic measured, off `s7-frame-K.png`, an along-crest residual
    of 5.2 DN after removing the smooth cross-crest trend against 31.7 DN
    across the crests -- a ratio of 0.16 -- and called it corrugated roofing.
    Written here as:

        F_bar(xi)  = mean along the crest
        along      = rms( F - F_bar )                  the short-crested part
        across     = rms( F_bar - smooth(F_bar) )      the crest modulation
        ratio      = along / across

    ZERO FOR AN EXACT EXTRUSION, by construction and not by tolerance, and
    measured at 0.000000 on this scene's own waves 1-12 plane wave. It rises
    without bound as the field becomes short-crested, and the value it should
    reach is not free -- `extrusion_ratio_predicted` is the closed form.

    IN: F (n_along, n_across). AXIS 0 IS ALONG THE CREST AND AXIS 1 IS ACROSS
    IT, and getting that wrong is not a sign error, it is a different
    statistic: this wave first measured an oblique plane wave in the GRID frame
    and got 77.6 for a field whose along-crest residual is exactly zero. The
    frame the crests are aligned with is the frame this statistic lives in, and
    it is the frame a picture of horizontal bands is already in.

    `ratio_raw` is the same quantity without the detrend. The detrend is the
    critic's and it matters on a RENDER, where shoaling and perspective put a
    real cross-crest trend under the crests; on a stationary patch the two
    agree, and `ratio_raw` is the one the closed form predicts exactly.
    """
    F = np.asarray(F, float)
    fbar = F.mean(axis=0)
    along = float(np.sqrt(((F - fbar[None, :]) ** 2).mean()))
    n = fbar.size
    w = max(int(round(n / 8.0)), 3) if smooth is None else int(smooth)
    ker = np.ones(w) / w
    trend = np.convolve(np.pad(fbar, (w, w), mode='edge'), ker,
                        mode='same')[w:w + n]
    across = float(np.sqrt(((fbar - trend) ** 2).mean()))
    raw = float(np.sqrt(((fbar - fbar.mean()) ** 2).mean()))
    return dict(along=along, across=across, across_raw=raw,
                ratio=(along / across) if across > 0 else float('inf'),
                ratio_raw=(along / raw) if raw > 0 else float('inf'))


def extrusion_ratio_predicted(comp, width):
    """What `extrusion_ratio` MUST return, in closed form, for a component list.

    EXACT, NOT ASYMPTOTIC, and the first version of this function was neither.
    Averaging a component a cos(kx xi + ky eta + ph) along the crest over a
    window of length W leaves amplitude a*sinc(ky W/2) -- the mean of a cosine
    over an interval is the cosine times a sinc of half the phase run. The
    components are mutually incoherent, so their variances add and

        sigma^2 = SUM a_j^2 / 2                          the field's variance
        V       = SUM (a_j^2 / 2) sinc^2( k_y,j W / 2 )  what the mean keeps
        ratio   = sqrt( (sigma^2 - V) / V )                            (S3)

    with sinc(z) = sin z / z and sinc(0) = 1. THAT LAST VALUE IS THE WHOLE
    POINT: a field with every k_y = 0 -- an extrusion -- has V = sigma^2 and a
    ratio of exactly zero, and the statistic's floor is a consequence rather
    than a tolerance. (S3) depends on the spread only through the DISTRIBUTION
    OF k_y, which is what a directional spectrum is, so it turns the critic's
    number into a prediction of the spread and not merely a report of it.

    The first attempt wrote V ~ sigma^2 * 2 Lc / W with Lc an integral
    correlation length, which is the textbook large-W asymptote. It was wrong
    here by a factor of three and got WORSE as W grew, because for a
    narrow-band field rho oscillates, the negative lobes cancel most of
    INT rho du, and an integral length truncated at the first zero crossing --
    the standard estimator -- is not that integral at all. (S3) needs no
    estimator.

    `comp` is a `spectral_components` dict; `width` is the along-crest extent
    of the patch, in metres. k_y is taken IN THE CREST FRAME -- k sin(th - th0)
    -- because that is the frame `extrusion_ratio` reads, and using the grid
    frame's k_y instead is the same 20-degree error the anisotropy tensor
    caught.
    """
    a = np.asarray(comp['a'], float)
    ky = (np.asarray(comp['k'], float)
          * np.sin(np.asarray(comp['theta'], float) - comp.get('theta0', 0.0)))
    z = 0.5 * ky * float(width)
    sinc = np.where(np.abs(z) < 1e-12, 1.0, np.sin(z) / np.where(z == 0, 1, z))
    var = 0.5 * float((a ** 2).sum())
    V = 0.5 * float((a ** 2 * sinc ** 2).sum())
    if V <= 0.0:
        return float('inf')
    return math.sqrt(max(var - V, 0.0) / V)


def integral_length(eta, d, axis=0, max_lag=None):
    """INT_0^inf rho(r) dr along one axis, truncated at the first zero
    crossing of rho -- the standard estimator, and the truncation is what makes
    it an estimator rather than a divergent sum over noise."""
    e = np.asarray(eta, float)
    e = e - e.mean()
    v = float((e * e).mean())
    n = e.shape[axis]
    m_max = n // 3 if max_lag is None else int(max_lag)
    tot = 0.5                                   # rho(0) = 1, trapezoid
    for m in range(1, m_max + 1):
        sl0 = [slice(None)] * e.ndim
        sl1 = [slice(None)] * e.ndim
        sl0[axis] = slice(m, None)
        sl1[axis] = slice(None, -m)
        r = float((e[tuple(sl0)] * e[tuple(sl1)]).mean()) / v
        if r <= 0.0:
            break
        tot += r
    return tot * float(d)


# ---------------------------------------------------------------- groupiness
# GROUPINESS IS NOT DECORATION EITHER. The chapter's advice through wave 12 was
# "superpose two or three periods with a slow group envelope" -- a knob. The
# envelope of a Gaussian process is a CONSEQUENCE of the spectrum's bandwidth
# and has nothing free in it. Longuet-Higgins (1957, 1984) narrow-band result:
# for a Gaussian surface the envelope A is Rayleigh, so
#
#       <A> = sqrt(pi m0 / 2),  <A^2> = 2 m0,  var(A) = (2 - pi/2) m0
#
# and the groupiness factor in the Funke & Mansard sense -- the coefficient of
# variation of the wave-energy envelope A^2 / 2 -- is, for an exponential
# (A^2 Rayleigh-squared) variable, exactly 1. That is the SATURATION value a
# fully random narrow-band sea reaches and it is not adjustable. The number
# that IS adjustable by the spectrum is the LENGTH of a group, which is set by
# the bandwidth nu = sqrt(m0 m2 / m1^2 - 1): the envelope decorrelates over
# roughly 1/(nu f_p) periods, so a narrow spectrum gives long sets and a broad
# one gives none. `spectral_bandwidth` returns nu and the suite checks the
# measured group length against 1/nu rather than against an eye.


def spectral_bandwidth(T=T_SWELL, band=SPREAD_BAND, gamma=JONSWAP_GAMMA,
                       hs=None, n_f=4096):
    """nu = sqrt(m0 m2 / m1^2 - 1), Longuet-Higgins' spectral width, over the
    stated band. Zero for a monochromatic wave -- which is what waves 1-12
    had, and it is why nothing in them could group."""
    fp = 1.0 / float(T)
    hs = 4.0 * math.sqrt((H0_SWELL ** 2) / 8.0) if hs is None else float(hs)
    f = np.geomspace(band[0] * fp, band[1] * fp, n_f)
    S = jonswap(f, hs, fp, gamma)
    m = [float(np.trapezoid(S * f ** n, f)) for n in (0, 1, 2)]
    return math.sqrt(max(m[0] * m[2] / m[1] ** 2 - 1.0, 0.0))


def envelope(sig):
    """The Hilbert envelope of a 1-D record, by FFT. |sig + i H(sig)|."""
    s = np.asarray(sig, float)
    s = s - s.mean()
    n = s.size
    F = np.fft.fft(s)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[1:(n + 1) // 2] = 2.0
    return np.abs(np.fft.ifft(F * h))


def groupiness_factor(sig):
    """std(A^2) / mean(A^2) for the envelope A of a record.

    Exactly 1 for a Gaussian narrow-band process, because A^2 is then
    exponentially distributed. A monochromatic wave gives 0. It is therefore a
    yes/no instrument on whether a field is a realisation at all, and it is
    used that way here rather than as a tuning target.
    """
    a2 = envelope(sig) ** 2
    return float(a2.std() / a2.mean())


# ============================================================================
# THE WAVE TRANSFORM IN 2-D
# ============================================================================
#
# Wave 1 verified sin(theta)/c invariant to 2.2e-16 on a straight coast. That
# test passes BY CONSTRUCTION -- `snell_sin` computes sin(theta) from c, so the
# ratio is an identity, and bar section B says as much: "Straight-contour
# refraction is a test that passes by construction; this one is not." A curved
# bay is the first real one, and it needs a transform that does not have Snell
# written into it.
#
# THE MARCH, derived here, because it is the whole of wave 3's wave physics.
#
# Two statements and nothing else. First, the wavenumber vector of a steady wave
# train is IRROTATIONAL -- k = grad(S) for the phase S, so curl(k) = 0:
#
#     d(k_y)/dx = d(k_x)/dy                                            (1)
#
# Write k_x = sqrt(k^2 - k_y^2) with k = k(d) from the dispersion relation, and
# (1) becomes a scalar equation for k_y alone:
#
#     dk_y/dx = d/dy sqrt(k^2 - k_y^2) = (k*dk/dy - k_y*dk_y/dy)/k_x
#
#     ==>  dk_y/dx  +  tan(theta) * dk_y/dy  =  (k/k_x) * dk/dy        (2)
#
# which is an ADVECTION equation whose characteristics dy/dx = tan(theta) are
# the rays themselves -- so it is marched shoreward with an upwind difference in
# y and it is stable for dx*|tan theta| <= dy. Two things fall out of (2) and
# both are used as tests rather than assumed:
#
#   * ON AN ALONGSHORE-UNIFORM BED dk/dy = 0 and k_y is constant along x. But
#     k_y = k*sin(theta) = omega*sin(theta)/c, so k_y = const IS Snell. The 2-D
#     march therefore CONTAINS the straight-coast invariant as its degenerate
#     case, and does not contain it anywhere else. Nothing in this function
#     computes sin(theta) from c.
#   * IN A BAY dk/dy is the whole story: the source term turns the crest toward
#     shallower water, which is the mechanism bar section J photographs.
#
# Second, energy. The flux vector is E*c_g in the ray direction and Dally, Dean
# & Dalrymple's decay is a sink on it:
#
#     div( E c_g s^ ) = -(K/d) * ( E c_g - (E c_g)_stable )            (3)
#
# THE OBLIQUITY IN (3) IS NOT THE OBLIQUITY IN THE 1-D FORM, and this file's own
# 1-D transform is on the other side of the difference. `transform()` follows
# chapter 12's pseudocode and marches F = E*c_g*cos(theta) with
# dF/dx = -(K/d)(F - F_s), i.e. the decay rate is applied per unit CROSS-SHORE
# distance. In (3) it is applied per unit RAY distance, and ds = dx/cos(theta),
# so the two differ by exactly cos(theta) in the exponent. At this scene's
# breaking angle (6.5 deg) that is 0.6% and invisible; at 30 deg it is 15%. The
# 2-D march uses the ray-length form because that is what a divergence means,
# reduces to the 1-D form EXACTLY at normal incidence, and the suite measures
# the gap at 20 deg rather than hiding it. Reported as a finding, not patched
# into the 1-D file: `transform()` is what waves 1 and 2 measured with.


def transform_2d(x, y, h2, T, H0, theta0, breaking=True, gamma_b=GAMMA_B,
                 gamma_s=GAMMA_STABLE, k_dally=K_DALLY, filter_scale=None,
                 eta=None, k_field=None, refraction=True, contour0=None):
    """Shoal, refract and break a stated offshore sea state across a PLAN bed.

    IN:  x (m, shoreward+), y (m, alongshore), h2 (ny, nx) bed elevation,
         T (s), H0 (deep-water m), theta0 (deep-water rad off shore-normal)
    OUT: a dict of (ny, nx) fields -- d, k, c, cg, theta, H, Phi, brk, D_w, S

    `Phi` is the flux MAGNITUDE E*c_g (W/m of crest); `S` is the wave phase in
    radians, accumulated along the march, so that contours of S mod 2*pi are the
    crests themselves -- which is what the plan-view figure draws and what the
    photograph shows.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    h2 = np.asarray(h2, float)
    ny, nx = h2.shape
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    omega = 2.0 * math.pi / T

    surf = 0.0 if eta is None else np.asarray(eta, float)
    d_raw = np.maximum(surf - h2, D_MIN)
    if filter_scale is None:
        filter_scale = (1.5 * dx, 1.5 * dy)
    d = np.maximum(smooth_depth_2d(d_raw, dx, dy, filter_scale[0],
                                   filter_scale[1]), D_MIN)

    k = wavenumber(omega, d) if k_field is None else np.asarray(k_field, float)
    c, cg, n = celerity(omega, k, d)
    c0 = deep_celerity(T)
    cg0 = c0 / 2.0
    E0 = RHO_SW * G * H0 ** 2 / 8.0

    theta = np.zeros((ny, nx))
    Phi = np.zeros((ny, nx))
    brk = np.zeros((ny, nx), bool)
    S = np.zeros((ny, nx))

    # ---- the offshore boundary. The shelf is flat there by construction, so
    # Snell against the local celerity is exact and the boundary condition is
    # the SAME statement the 1-D transform makes: the deep-water flux, conserved
    # in from infinity. Nothing downstream may change it.
    #
    # WAVE 9: theta0 AND H0 MAY BE PER-ROW. A plane offshore crest is the
    # scalar case and stays bit-identical to waves 1-8 -- `np.sin` of a 0-d
    # array is `math.sin` of the float. The array case exists because a
    # headland DIFFRACTS: the orthogonals in its lee fan out from the tip
    # instead of arriving parallel, and that fan is the boundary condition, not
    # something the shoreward march can invent. It is still a stated OFFSHORE
    # condition -- everything between it and the beach is an output.
    #
    # AND THE SNELL AT THE BOUNDARY IS AGAINST THE LOCAL CONTOUR, NOT THE GRID.
    # Waves 1-8 wrote `arcsin(c/c0 * sin(theta0))`, which conserves the
    # component of k along the GRID's y axis. That is exact for a coast whose
    # contours are the grid's rows and WRONG for any other, because the Snell
    # invariant is the wavenumber component along the CONTOUR. Measured on the
    # closed-form zero-transport coast -- a straight shore rotated by the full
    # deep-water obliquity, which must break with theta = 0 exactly -- the old
    # boundary left 4.89 deg of residual obliquity and 76 per cent of the
    # straight coast's longshore transport. The meter could not read zero, so
    # a near-zero reading on the bay would have proved nothing. `contour0` is
    # the angle of the local offshore contour NORMAL from +x; zero reproduces
    # waves 1-8 bit for bit.
    th0 = np.broadcast_to(np.asarray(theta0, float), (ny,))
    n0 = np.broadcast_to(np.asarray(0.0 if contour0 is None else contour0,
                                    float), (ny,))
    sin0 = np.clip(c[:, 0] / c0 * np.sin(th0 - n0), -1.0, 1.0)
    theta[:, 0] = np.arcsin(sin0) + n0
    ky = k[:, 0] * np.sin(theta[:, 0])

    # ---- WAVE 13: THE PHASE'S ALONGSHORE HALF, WHICH WAS MISSING ENTIRELY.
    # This function's own docstring says contours of S mod 2 pi are the crests,
    # and waves 1-12 set S[:, 0] = 0 and then accumulated ONLY the x-integral
    # of k cos(theta). k = grad(S) has two components and only one of them was
    # ever integrated, so the drawn phase satisfied dS/dx = k_x exactly and
    # dS/dy = 0 exactly -- at a sea state whose orthogonal is 20 deg off
    # shore-normal.
    #
    # MEASURED ON A CONTROL WHOSE ANSWER IS KNOWN IN ADVANCE (ruling 14): a
    # FLAT bed in 20 m of water, where refraction has nothing to bend and the
    # answer is a plane wave. dS/dx came back 0.057264 against k_x = 0.057264;
    # dS/dy came back 0.000000 against k_y = 0.016998, and the alongshore phase
    # run across 1408 m of coast -- 23.9 radians, nearly four whole
    # wavelengths -- was absent. The obliquity is present in `theta`, in the
    # radiation stress, in the longshore transport and in every row that reads
    # them. It was absent from the ONE field the renderer draws crests with, so
    # every crest in every frame ran exactly shore-parallel whatever the sea
    # state said, edge to edge, at constant orientation. That is half of what
    # the critic called corrugated roofing and it is not a spreading problem.
    #
    # The fix is the boundary condition the potential needs and nothing more:
    # S(y, 0) = INT_0^y k_y(y', 0) dy', so that the march's x-integration
    # carries a phase whose y-derivative is already right. It stays right
    # downstream because the march ENFORCES curl(k) = 0 -- that is its
    # equation (1) -- so a potential exists and integrating it along x from a
    # correct boundary is path-independent. Testing dS/dy = k sin(theta) at
    # mid-domain therefore tests the boundary AND the irrotationality in one
    # row, and the suite carries it on the flat-bed control where the answer
    # is a closed form.
    S[:, 0] = np.concatenate(
        [[0.0], np.cumsum(0.5 * (ky[1:] + ky[:-1]) * dy)]) if ny > 1 else 0.0
    if ny > 1:
        j0 = int(np.argmin(np.abs(y)))          # phase zero at y = 0, so that
        S[:, 0] -= S[j0, 0]                     # the scalar case matches the
                                                # deep-water plane wave the
                                                # renderer draws beyond the
                                                # domain, k0(x cos th + y sin th)
    if not refraction:
        ky = None                      # the deliberate defect uses this
    Phi[:, 0] = (E0 * cg0 * np.cos(th0 - n0)
                 / np.cos(theta[:, 0] - n0))
    state = np.zeros(ny, bool)

    for i in range(nx - 1):
        th = theta[:, i]
        cs, sn = np.cos(th), np.sin(th)
        d_i, cg_i, k_i = d[:, i], cg[:, i], k[:, i]
        Phi_i = Phi[:, i]

        H_i = np.sqrt(np.maximum(8.0 * Phi_i / (RHO_SW * G * cg_i), 0.0))
        if breaking:
            # The hysteresis is carried DOWN THE COLUMN, not along the ray. The
            # ray's alongshore drift is dx*tan(theta) per step, which on this
            # scene's grid is 0.015 of a cell and about one cell across the
            # whole surf zone; the state is therefore at most one cell out of
            # place, and saying so is cheaper and more honest than a
            # semi-Lagrangian shift that would round to zero at every step.
            on = H_i >= gamma_b * d_i
            off = H_i <= gamma_s * d_i
            brk[:, i] = np.where(on, True, np.where(off, False, state))
        state = brk[:, i]

        # ---- transverse divergence, upwind on the sign of the alongshore flux
        Fx = Phi_i * cs
        Fy = Phi_i * sn
        dFy = np.empty(ny)
        dFy[1:-1] = np.where(Fy[1:-1] >= 0.0, Fy[1:-1] - Fy[:-2],
                             Fy[2:] - Fy[1:-1]) / dy
        dFy[0] = (Fy[1] - Fy[0]) / dy
        dFy[-1] = (Fy[-1] - Fy[-2]) / dy
        Fx_star = Fx - dx * dFy

        # ---- the Dally sink, integrated exactly over the RAY length dx/cos
        if breaking:
            Phi_s = (RHO_SW * G * (gamma_s * d_i) ** 2 / 8.0) * cg_i
            Fx_s = Phi_s * cs
            decay = np.exp(-k_dally * dx / (d_i * np.maximum(cs, 1e-6)))
            Fx_new = np.where(state, Fx_s + (Fx_star - Fx_s) * decay, Fx_star)
        else:
            Fx_new = Fx_star

        # ---- the wavenumber march, equation (2) above
        if ky is None:
            th_next = np.full(ny, theta[:, 0][0] if ny else 0.0)
            theta[:, i + 1] = theta[:, i]
        else:
            kx = np.sqrt(np.maximum(k_i ** 2 - ky ** 2, 1e-12))
            dkdy = np.empty(ny)
            dkdy[1:-1] = (k_i[2:] - k_i[:-2]) / (2.0 * dy)
            dkdy[0] = (k_i[1] - k_i[0]) / dy
            dkdy[-1] = (k_i[-1] - k_i[-2]) / dy
            tan_t = sn / np.maximum(cs, 1e-6)
            dkydy = np.empty(ny)
            dkydy[1:-1] = np.where(tan_t[1:-1] >= 0.0, ky[1:-1] - ky[:-2],
                                   ky[2:] - ky[1:-1]) / dy
            dkydy[0] = (ky[1] - ky[0]) / dy
            dkydy[-1] = (ky[-1] - ky[-2]) / dy
            ky = ky + dx * ((k_i / kx) * dkdy - tan_t * dkydy)
            ky = np.clip(ky, -0.999 * k[:, i + 1], 0.999 * k[:, i + 1])
            th_next = np.arcsin(np.clip(ky / k[:, i + 1], -1.0, 1.0))
            theta[:, i + 1] = th_next
        Phi[:, i + 1] = np.maximum(Fx_new, 0.0) / np.cos(th_next)
        S[:, i + 1] = S[:, i] + dx * 0.5 * (k_i * np.cos(th)
                                            + k[:, i + 1] * np.cos(th_next))
    # the last column never gets a flux update, so its state is set by its own
    # onset test rather than inherited -- the 1-D transform does the same
    H_last = np.sqrt(np.maximum(8.0 * Phi[:, -1] / (RHO_SW * G * cg[:, -1]), 0.0))
    if breaking:
        on = H_last >= gamma_b * d[:, -1]
        off = H_last <= gamma_s * d[:, -1]
        brk[:, -1] = np.where(on, True, np.where(off, False, state))

    H = np.sqrt(np.maximum(8.0 * Phi / (RHO_SW * G * cg), 0.0))
    E = RHO_SW * G * H ** 2 / 8.0
    F = Phi * np.cos(theta)
    D_w = np.zeros((ny, nx))
    D_w[:, 1:-1] = -(F[:, 2:] - F[:, :-2]) / (2.0 * dx)
    D_w[:, 0] = -(F[:, 1] - F[:, 0]) / dx
    D_w[:, -1] = -(F[:, -1] - F[:, -2]) / dx
    return dict(x=x, y=y, h=h2, d=d, d_raw=d_raw, k=k, c=c, cg=cg, n=n,
                theta=theta, H=H, E=E, Phi=Phi, F=F, D_w=D_w, brk=brk, S=S,
                T=T, omega=omega, H0=H0, theta0=theta0, c0=c0, cg0=cg0,
                E0=E0, dx=dx, dy=dy)


def contour_alignment(tr2, field='wave', d_min=0.5, d_max=None,
                      slope_min=0.004):
    """The angle between the wave crest and the local depth contour, degrees.

    This is bar section J's by-eye criterion turned into a number. The crest is
    perpendicular to the ray, the contour is perpendicular to grad(d), so the
    crest-to-contour angle IS the ray-to-grad(d) angle:

        alpha = angle( s^ , -grad(d)/|grad(d)| )

    Zero means the crest is exactly parallel to the contour. Refraction drives
    alpha toward zero as the depth falls; a render whose surf lines stay
    straight while the shore curves has alpha growing with the shore's own
    turning instead.

    `field` HAS NO DEFAULT THAT SILENTLY PICKS, and the reason is the error
    class chapter 12 now carries as a general finding: a ratio -- or here an
    angle -- whose two terms come from different versions of the same field.
    The wave direction is an output of the transform, which reads the FILTERED
    depth; the contour can be read off the filtered depth or off the raw bed,
    and on a barred plan bed those two contours are not parallel. 'wave' reads
    both from the field the wave actually saw; 'bed' reads the contour from the
    raw bed and is the mixed comparison, kept so a deliberate defect can put it
    back and a guard can fire at it.
    """
    if field not in ('wave', 'bed'):
        raise ValueError("field must be 'wave' (both terms in the depth the "
                         "wave saw) or 'bed' (the mixed comparison)")
    d = tr2['d'] if field == 'wave' else tr2['d_raw']
    gx = np.gradient(d, tr2['dx'], axis=1)
    gy = np.gradient(d, tr2['dy'], axis=0)
    mag = np.hypot(gx, gy)
    # shoreward normal = -grad(d), normalised
    nx_ = np.where(mag > 1e-12, -gx / np.maximum(mag, 1e-12), 1.0)
    ny_ = np.where(mag > 1e-12, -gy / np.maximum(mag, 1e-12), 0.0)
    sx, sy = np.cos(tr2['theta']), np.sin(tr2['theta'])
    dot = np.clip(sx * nx_ + sy * ny_, -1.0, 1.0)
    alpha = np.degrees(np.arccos(dot))
    dd = tr2['d_raw']
    # THE MASK IS PART OF THE MEASUREMENT and it took a wrong answer to see it.
    # Behind a bar crest the bed DEEPENS shoreward, so grad(d) reverses and the
    # "shoreward normal" points out to sea; taking the angle there compares the
    # crest against a contour whose sign has flipped, and the statistic came
    # back at 34 degrees mean with a 173 degree ninety-fifth percentile on a
    # field whose surf lines were visibly following the shore. The angle is only
    # defined where there IS a shoaling contour to be parallel to: the bed must
    # shallow shoreward, and by more than the grid can dither.
    m = (dd >= d_min) & (mag > 1e-9) & (gx <= -slope_min)
    if d_max is not None:
        m &= dd <= d_max
    return alpha, m


def surf_line_x(tr2):
    """The most seaward breaking onset in every alongshore row, metres.

    `brk` is the transform's own hysteretic state -- wave 2 had to separate this
    from `break_lines`, which is the ONSET test and says nothing about where a
    wave stops. This returns where the outer surf line IS, which is what a
    photograph of a bay shows."""
    brk = tr2['brk']
    x = tr2['x']
    out = np.full(brk.shape[0], np.nan)
    for j in range(brk.shape[0]):
        idx = np.nonzero(brk[j])[0]
        if idx.size:
            out[j] = x[idx[0]]
    return out


def surf_spans_2d(tr2, j):
    """The breaking spans in one alongshore row, as (x0, x1) pairs."""
    return _spans(tr2['brk'][j], tr2['x'])


# ---------------------------------------------------- the morphodynamics in 2-D
def sediment_flux_2d(tr2, **kw):
    """The 1-D energetics flux, evaluated on the plan fields and carried along
    the WAVE DIRECTION.

    THE SAME FUNCTION, NOT A COPY. `sediment_flux` is shape-agnostic once the
    roller march and the slope gradient are taken along the last axis, which is
    the cross-shore one in both fields, so the plan-view loop runs the identical
    arithmetic waves 1 and 2 measured -- and every one of their rows still
    guards it. What this wrapper adds is two things a plan view needs:

      * the slope term is taken along the wave direction, grad(h).s^, because
        gravity pulls sand down the slope the transport is crossing;
      * the flux is returned as a VECTOR, q*s^, so Exner can take a real 2-D
        divergence.

    WHAT IS DELIBERATELY ABSENT: any alongshore transport. There is no longshore
    current term, no rip feeder, no alongshore pressure gradient. That is the
    2DH circulation chapter 12 declares out of scope and wave 2 named as the
    missing mechanism for the second breaking line; this wave does not attempt
    it, and mixing it in here would make the geometry and the circulation
    unattributable to each other.
    """
    gx = np.gradient(tr2['h'], tr2['dx'], axis=1)
    gy = np.gradient(tr2['h'], tr2['dy'], axis=0)
    cs, sn = np.cos(tr2['theta']), np.sin(tr2['theta'])
    dhds = gx * cs + gy * sn
    fl = sediment_flux(tr2, dhds=dhds, **kw)
    fl['qx'] = fl['q'] * cs
    fl['qy'] = fl['q'] * sn
    return fl


def exner_step_2d(h2, qx, qy, dx, dy, dt, d, poros=POROSITY,
                  d_min=D_MORPH_MIN):
    """dh/dt = -div(q)/(1 - poros) on the plan grid.

    The same taper and the same closed domain as the 1-D step: the flux is
    tapered out shallower than d_min rather than cut, because a step in q is an
    infinite convergence to Exner, and it is zeroed on the cross-shore
    boundaries so no sand enters or leaves. The alongshore boundaries carry a
    zero-gradient condition -- the domain is a WINDOW on a longer coast, so
    clamping the alongshore flux there would be a wall the coast does not have.
    """
    taper = np.clip((d - d_min) / 0.5, 0.0, 1.0)
    qx = np.asarray(qx, float) * taper
    qy = np.asarray(qy, float) * taper
    qx[:, 0] = 0.0
    qx[:, -1] = 0.0
    div = np.gradient(qx, dx, axis=1) + np.gradient(qy, dy, axis=0)
    return h2 + (-dt / (1.0 - poros) * div)


def evolve_2d(x, y, h0, T, H0, theta0, n_steps, dt, k_every=1, **flux_kw):
    """The plan-view morphodynamic loop -- chapter 12's loop, in 2-D geometry
    with 1-D (cross-shore) dynamics.

    `k_every` recomputes the dispersion solve every N steps and reuses it in
    between. The wavenumber depends on the bed only through d, and the bed moves
    by millimetres per step; the suite carries a row at k_every=1 against
    k_every=8 and the bar crest moves by less than a centimetre.
    """
    h = np.asarray(h0, float).copy()
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    omega = 2.0 * math.pi / T
    kf = None
    hist = []
    # THE SAND THAT LEAVES, accumulated rather than assumed away. The alongshore
    # boundaries are OPEN -- the domain is a window on a longer coast, so
    # clamping the alongshore flux there would be a wall the coast does not
    # have -- and sand therefore crosses them. Summing `np.gradient` over an
    # axis telescopes to 1.5f[-1] - 0.5f[-2] - 1.5f[0] + 0.5f[1], which is the
    # exact boundary term of the scheme actually used, so the volume book can
    # be closed to round-off instead of to a tolerance.
    edge = 0.0
    for s in range(int(n_steps)):
        if kf is None or s % k_every == 0:
            dd = np.maximum(smooth_depth_2d(np.maximum(-h, D_MIN), dx, dy,
                                            1.5 * dx, 1.5 * dy), D_MIN)
            kf = wavenumber(omega, dd)
        tr2 = transform_2d(x, y, h, T, H0, theta0, k_field=kf)
        fl = sediment_flux_2d(tr2, **flux_kw)
        tp = np.clip((tr2['d'] - D_MORPH_MIN) / 0.5, 0.0, 1.0)
        qxt, qyt = fl['qx'] * tp, fl['qy'] * tp
        qxt[:, 0] = 0.0
        qxt[:, -1] = 0.0
        bx = (1.5 * qxt[:, -1] - 0.5 * qxt[:, -2]
              - 1.5 * qxt[:, 0] + 0.5 * qxt[:, 1]).sum() * dy
        by = (1.5 * qyt[-1] - 0.5 * qyt[-2]
              - 1.5 * qyt[0] + 0.5 * qyt[1]).sum() * dx
        edge += -dt / (1.0 - POROSITY) * float(bx + by)
        h = exner_step_2d(h, fl['qx'], fl['qy'], dx, dy, dt, tr2['d'])
        if s % max(1, n_steps // 5) == 0 or s == n_steps - 1:
            hist.append((s, h.copy()))
    tr2 = transform_2d(x, y, h, T, H0, theta0)
    return h, tr2, hist, edge


def bar_alongshore(x, y, h2, h_ref, x_lo=None, x_hi=None):
    """Read the bar off every alongshore row: crest x, crest depth, amplitude.

    Returns a dict of (ny,) arrays with NaN where no bar formed. This is the
    measurement bar section J's third finding asks for -- whether the nearshore
    carries one bar or a system, and whether it is the same bar at every
    station."""
    x = np.asarray(x, float)
    h2 = np.asarray(h2, float)
    ny = h2.shape[0]
    xc = np.full(ny, np.nan)
    dc = np.full(ny, np.nan)
    amp = np.full(ny, np.nan)
    for j in range(ny):
        # no try/except here on purpose. `bar_crest` returns None when its
        # window selects nothing and raises for nothing else, and a reader that
        # swallows exceptions per row is the same disease as a harness that
        # counts a crash as a catch -- it turns a broken measurement into a
        # quiet gap in the answer.
        cr = bar_crest(x, h2[j], h_ref[j], x_min=x_lo, x_max=x_hi)
        if cr is None:
            continue
        xc[j], dc[j], amp[j] = cr['x'], cr['d'], cr['amp']
    return dict(x=xc, d=dc, amp=amp)


# ===================================================== THE STATIC-EQUILIBRIUM
# BAY -- the plan-form, and the one property that makes it provable
#
# WHY THIS SECTION EXISTS. Waves 1-8 built a bed whose shoreline is a straight
# regional trend with the hardness field's own roughness on it: 55 m of range
# over 1408 m of coast, but jagged, with no single curve in it. Bar section J
# photographs an EMBAYMENT -- "headland to headland, cliff behind, a curved
# sand beach, and the surf running in multiple lines that follow the curve all
# the way round" -- and calls the surf-follows-the-curve test "the cheapest
# verification in the entire project". A straight-contour test passes by
# construction. This section builds the curve.
#
# WHAT THE LITERATURE CALLS IT, AND WHERE IT IS NOT. The headland-bay coast in
# static equilibrium has two closed forms in coastal engineering: the
# LOGARITHMIC SPIRAL (Krumbein 1944; Yasso 1965; Silvester 1970) and the
# PARABOLIC BAY-SHAPE EQUATION (Hsu & Evans 1989). NEITHER IS IN
# terrain-architect/references/12-glacial-coastal.md. That chapter carries the
# coastal loop, longshore drift, spits and the Dean profile, and its only
# statement about coastal PLAN-FORM equilibrium is one clause -- "headlands
# retreat faster than bays, which is correct and self-reinforcing until the
# coast STRAIGHTENS". The absence is reported to the sibling skill as a gap,
# and the clause is measured here rather than repeated: see `zero_transport_
# plan` below, which finds that on a plane-wave field the chapter's clause is
# EXACTLY RIGHT and that this is precisely why a bay needs something the
# chapter does not have.
#
# THE PARABOLIC FORM IS NOT IMPLEMENTED HERE AND THE REASON IS PROVENANCE. Hsu
# & Evans' C0/C1/C2 are three quartic polynomials in beta -- fifteen fitted
# coefficients from a least-squares fit to 27 bays. Nothing in this container
# holds them. Writing them from memory is exactly the failure this project
# exists to prevent, and a fifteen-coefficient fit has no internal check that
# would catch a wrong digit. The LOG SPIRAL has one parameter and a defining
# geometric property that checks itself, so it is the form implemented, and
# the parabolic form is marked `?` and NOT shipped.
K_CERC = 0.39           # the CERC longshore-transport coefficient on the
                        # SIGNIFICANT wave height. EMPIRICAL -- chapter 12 says
                        # so outright ("the CERC transport closure is empirical
                        # coastal engineering"). IT CANNOT SET THE EQUILIBRIUM
                        # PLAN-FORM: equilibrium is Q = 0, and Q = C * sin(2
                        # theta) is zero at theta = 0 for EVERY C. The suite
                        # doubles it and checks the plan-form does not move --
                        # a coefficient that cannot reach the answer is the
                        # strongest kind of `?` there is.


def log_spiral(phi, R_a, phi_a, alpha):
    """The logarithmic spiral R(phi) = R_a * exp((phi - phi_a) * cot(alpha)).

    ITS DEFINING PROPERTY, and it is what makes it the equilibrium form: the
    angle between the radius vector and the tangent is the CONSTANT alpha, at
    every point. dP/dphi = R'(phi) u + R(phi) u_perp = R (cot(alpha) u +
    u_perp), whose angle to u has tangent 1/cot(alpha) = tan(alpha) whatever
    phi is. alpha = 90 deg is the circle; alpha -> 0 is a ray.
    """
    return float(R_a) * np.exp((np.asarray(phi, float) - float(phi_a))
                               / math.tan(float(alpha)))


def spiral_tangent(phi, alpha):
    """The unit tangent of the spiral at polar angle phi, in (x, y).

    Written from the derivative and NOT from the constant-angle property, so
    that the suite can check the second against the first."""
    ca = 1.0 / math.tan(float(alpha))
    u = np.stack([np.cos(phi), np.sin(phi)], axis=-1)
    up = np.stack([-np.sin(phi), np.cos(phi)], axis=-1)
    t = ca * u + up
    return t / np.linalg.norm(t, axis=-1, keepdims=True)


def equilibrium_alpha(delta):
    """The spiral angle from a residual obliquity delta.

    THE DERIVATION, and it is one line. At static equilibrium the shoreline is
    normal to the wave ORTHOGONAL -- that is what zero longshore transport
    means, because Q goes as sin(2 theta) and theta is the angle between the
    orthogonal and the shore normal. If the orthogonals radiate from a single
    pole (the diffraction point of the sheltering headland, or more generally
    the virtual source the fan converges on) then the radius vector IS the
    orthogonal, and the shoreline is normal to the radius at every station:

        alpha = 90 deg  --  A CIRCULAR ARC ABOUT THE POLE.

    THAT MEMBER IS DERIVED AND IT IS THE ONLY ONE THAT IS. If the orthogonal
    is rotated from the radius by a CONSTANT delta, the tangent makes the
    constant angle 90 - delta with the radius, which is the logarithmic
    spiral's own definition and nothing else's -- so the log spiral is exactly
    "a bay whose residual obliquity is constant", and the derivation says WHY
    the spiral rather than fitting one.

    WHAT IS NOT DERIVED IS delta. This file ships delta = theta_b, the
    breaking obliquity the 1-D transform outputs for the stated offshore
    spectrum, as a DECLARED choice and marks it `?`; the circle (delta = 0) is
    computed and reported beside it every time, so the reader sees what the
    choice is worth rather than being told it does not matter. Silvester's
    published alpha for real bays is 30-50 deg, which is a delta of 40-60 deg
    and an order above anything refraction leaves -- an EMPIRICAL fit, not this
    quantity, and the two must not be confused.
    """
    return math.pi / 2.0 - float(delta)


def spiral_residual(D, A1, A2, alpha, khat):
    """The two closure conditions on the pole, as a residual vector.

    (1) THE SPIRAL PASSES THROUGH BOTH ANCHORS. For a log spiral about D,
        ln(r2/r1) = cot(alpha) * (phi2 - phi1) -- one equation, because the
        remaining two freedoms (R_a and the phi origin) are absorbed by the
        anchors themselves.
    (2) THE DOWNCOAST END IS TANGENTIAL. Hsu & Evans' downcoast control point
        is where the beach becomes parallel to the incoming crests, i.e. its
        NORMAL lies along the wave vector. So tangent . khat = 0 at A2.

    Two equations, two unknowns (D_x, D_y). Nothing is free, and the bay's
    indentation is therefore an OUTPUT.
    """
    D = np.asarray(D, float)
    v1 = np.asarray(A1, float) - D
    v2 = np.asarray(A2, float) - D
    r1 = float(np.hypot(v1[0], v1[1]))
    r2 = float(np.hypot(v2[0], v2[1]))
    if r1 <= 0.0 or r2 <= 0.0:
        return np.array([1e6, 1e6])
    p1 = math.atan2(v1[1], v1[0])
    p2 = math.atan2(v2[1], v2[0])
    dp = math.atan2(math.sin(p2 - p1), math.cos(p2 - p1))
    e1 = math.log(r2 / r1) - dp / math.tan(float(alpha))
    e2 = float(np.dot(spiral_tangent(p2, alpha), np.asarray(khat, float)))
    return np.array([e1, e2])


def spiral_pole(A1, A2, alpha, khat, D0=None, n_iter=200, tol=1e-13):
    """Solve `spiral_residual` = 0 for the pole.

    TWO BRANCHES EXIST AND ONLY ONE IS A BAY. The pole at infinity is always a
    root -- a log spiral with its pole infinitely far away is a straight line,
    the tangency condition then fixes its bearing, and the "bay" it produces is
    the rotated straight coast `zero_transport_plan` writes in closed form.
    That branch is real and this file measures it separately. The BAY is the
    NEAREST root, because the pole is the sheltering headland's diffraction
    point and a pole 79 km offshore is not a headland. So the solve is
    multi-start and the returned root is the converged one of smallest |D - A1|
    -- a selection rule with a physical statement behind it, and the suite
    reports the far branch's own sagitta beside it so the choice is visible.
    """
    A1 = np.asarray(A1, float)
    A2 = np.asarray(A2, float)
    if D0 is None:
        ch = float(np.hypot(*(A2 - A1)))
        roots = []
        for fx in (0.15, 0.3, 0.6, 1.0, -0.3, -0.6):
            for fy in (-0.6, -0.3, 0.0, 0.3, 0.6):
                D, r = spiral_pole(A1, A2, alpha, khat,
                                   D0=A1 + np.array([fx * ch, fy * ch]),
                                   n_iter=n_iter, tol=tol)
                if np.max(np.abs(r)) < 1e-10:
                    roots.append((float(np.hypot(*(D - A1))), D, r))
        if roots:
            roots.sort(key=lambda t: t[0])
            return roots[0][1], roots[0][2]
        D0 = A1 + np.array([0.3 * ch, -0.3 * ch])
    D = np.asarray(D0, float).copy()
    for _ in range(int(n_iter)):
        f = spiral_residual(D, A1, A2, alpha, khat)
        if np.max(np.abs(f)) < tol:
            break
        J = np.zeros((2, 2))
        for kk in range(2):
            e = np.zeros(2)
            e[kk] = 1e-5 * max(1.0, abs(D[kk]))
            J[:, kk] = (spiral_residual(D + e, A1, A2, alpha, khat) - f) / e[kk]
        try:
            step = np.linalg.solve(J, -f)
        except np.linalg.LinAlgError:
            break
        nrm = float(np.hypot(*step))
        if nrm > 400.0:
            step = step * (400.0 / nrm)
        D = D + step
    return D, spiral_residual(D, A1, A2, alpha, khat)


def spiral_points(D, A1, A2, alpha, n=2001, extend=0.0):
    """Sample the spiral from anchor A1 to anchor A2, as (n, 2) in (x, y).

    `extend` continues the SAME curve past both anchors by that fraction of
    the anchor-to-anchor angular span. The anchors are two rock highs inside
    the frame, not the frame's edges, so the coast beyond them is still bay --
    and continuing the analytic curve is the only way to fill it that does not
    introduce a second form with its own join."""
    D = np.asarray(D, float)
    v1 = np.asarray(A1, float) - D
    v2 = np.asarray(A2, float) - D
    r1 = float(np.hypot(v1[0], v1[1]))
    p1 = math.atan2(v1[1], v1[0])
    p2 = math.atan2(v2[1], v2[0])
    dp = math.atan2(math.sin(p2 - p1), math.cos(p2 - p1))
    e = float(extend) * dp
    ph = p1 + np.linspace(-e, dp + e, int(n))
    R = log_spiral(ph, r1, p1, alpha)
    return np.stack([D[0] + R * np.cos(ph), D[1] + R * np.sin(ph)], axis=1)


def headland_anchors(x_s, y, frac=0.25):
    """The two rock anchors, from the coastal loop's own plan-form.

    Bar J frames the scene HEADLAND TO HEADLAND, so the anchors are the
    seaward-most shoreline point in the outer `frac` of each end -- the hard
    rows the loop could not cut back. Nothing is placed: the anchors move if
    the hardness field's seed or correlation length moves, and the suite
    checks exactly that."""
    x_s = np.asarray(x_s, float)
    y = np.asarray(y, float)
    q = max(int(round(frac * y.size)), 2)
    j1 = int(np.argmin(x_s[:q]))
    j2 = y.size - q + int(np.argmin(x_s[y.size - q:]))
    return (np.array([x_s[j1], y[j1]]), np.array([x_s[j2], y[j2]]), j1, j2)


def chord_offset(pts):
    """Signed perpendicular offset of a polyline from the chord of its ends,
    and the maximum |offset| -- the bay's INDENTATION, the number bar J's
    photograph gives as roughly 50 m over 1408 m."""
    pts = np.asarray(pts, float)
    ch = pts[-1] - pts[0]
    L = float(np.hypot(ch[0], ch[1]))
    t = ch / L
    nrm = np.array([-t[1], t[0]])
    off = (pts - pts[0]) @ nrm
    return off, float(np.max(np.abs(off))), L


def plan_ramp(x, y, x_s, A=DEAN_A, d_shelf=D_SHELF, s_plain=S_PLAIN):
    """The Dean equilibrium ramp keyed to a STATED plan-form.

    d(x, y) = A * (x_s(y) - x)^(2/3), capped at the shelf depth, with the
    coastal plain landward of it. The depth contours are therefore exact
    offsets of the shoreline, which is what makes a curved shoreline curve the
    contours and what gives refraction something to turn onto. This is the
    same surface `bay_bed` composes, isolated so that the plan-form can be
    varied with nothing else changing -- the straight/curved pair the transport
    measurement needs is ONE argument."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    x_s = np.asarray(x_s, float)
    s = np.maximum(x_s[:, None] - x[None, :], 0.0)
    sea = -np.minimum(A * s ** (2.0 / 3.0), d_shelf)
    land = s_plain * np.maximum(x[None, :] - x_s[:, None], 0.0)
    return np.where(x[None, :] >= x_s[:, None], land, sea)


def plan_ramp_polar(x, y, D, R_s, A=DEAN_A, d_shelf=D_SHELF, s_plain=S_PLAIN):
    """The Dean ramp keyed to a plan-form, but measured along the RADIUS from
    the pole D instead of along the grid's cross-shore axis.

    WHY THIS EXISTS, and it is the sharpest measurement in this section. On a
    curved bay, "the depth is a function of distance from the shoreline
    measured across the grid" and "the depth is a function of distance from the
    pole" are DIFFERENT SURFACES. The first has contours that are x-translates
    of the shoreline; those converge where the shore is concave, so a ray that
    arrives normal to the shoreline does NOT stay normal to the contours on the
    way in, and refraction hands it back some obliquity. The second has
    contours that are concentric arcs, on which a radial ray is normal to every
    contour it crosses and Snell is the identity.

    So the pair separates the residual transport on the bay into "the bay is
    curved" and "the ramp is not concentric with the curve", and only a
    measurement can say which. `R_s` is the shoreline radius as a function of
    polar angle, supplied as (phi, R) samples -- the spiral itself.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    D = np.asarray(D, float)
    ph_s, R_sh = R_s
    XX = x[None, :] - D[0]
    YY = y[:, None] - D[1]
    r = np.hypot(XX, YY)
    ph = np.arctan2(YY, XX)
    o = np.argsort(ph_s)
    Rs = np.interp(ph, np.asarray(ph_s)[o], np.asarray(R_sh)[o])
    s = np.maximum(Rs - r, 0.0)
    sea = -np.minimum(A * s ** (2.0 / 3.0), d_shelf)
    land = s_plain * np.maximum(r - Rs, 0.0)
    return np.where(r >= Rs, land, sea)


def shoreline_offset(x, y, x_s, n_sub=8, chunk=16):
    """THE CROSS-SHORE DISTANCE, and on a curved coast it is not `x_s - x`.

    Signed distance from every cell to the shoreline CURVE: positive landward,
    negative seaward, magnitude the true Euclidean distance to the polyline
    (x_s(y), y). The sign is taken from the cross-shore side, which is
    unambiguous here because the shoreline is a graph x = x_s(y).

    WHY IT IS A DIFFERENT SURFACE FROM `x_s(y) - x`, derived. Both are
    "offsets" of the shoreline, but they are generated by different flows:

      * `s = x_s(y) - x` generates the family of TRANSLATES of the shoreline
        along the grid's x axis. Every member is congruent to the shoreline and
        its unit normal at alongshore station y is the shoreline's own normal
        AT THE SAME y, whatever the offset.
      * `s = dist(P, shore)` generates the family of NORMAL OFFSETS (parallel
        curves). Its members are not congruent to the shoreline -- a concave
        arc's offsets contract -- and their normal at the foot point is the
        shoreline's normal AT THAT FOOT POINT, i.e. constant ALONG A NORMAL
        LINE rather than along a grid line.

    The two families coincide if and only if phi_s = atan(dx_s/dy) is
    identically zero, i.e. the shore is parallel to the grid's y axis. That is
    every scene waves 1-8 rendered, which is why nothing could see it.

    WHAT IT COSTS THE WAVE FIELD. A ray launched normal to the shoreline
    travels along the normal line. On the normal-offset family it is normal to
    every contour it crosses, so Snell is the identity along it and the ray
    arrives at the shore with the obliquity it was launched with. On the
    translate family the contour it meets after travelling s belongs to
    alongshore station y + s*sin(phi_s), where the contour normal has rotated
    by

        d(theta) = -(d phi_s/dy) * s * sin(phi_s) + O(s^2)                 (*)

    -- FIRST ORDER IN THE SHORELINE CURVATURE TIMES THE OFFSET TIMES THE SINE
    OF THE SHORE'S OWN OBLIQUITY TO THE GRID. Refraction then hands part of
    that mismatch back as residual obliquity at breaking. It vanishes on a
    straight coast (curvature zero) and on a coast parallel to the grid
    (sin phi_s zero), and on nothing else.

    THE CONCENTRIC RAMP IS THE SPECIAL CASE OF THIS FOR A CIRCLE. If the
    shoreline is a circular arc about a pole, its normal offsets ARE the
    concentric arcs `plan_ramp_polar` builds, and the shared-normal property
    above is the statement that a radial ray stays radial. The normal-offset
    family is the same statement for a shoreline of ANY shape, and it needs no
    pole.

    THE LIMIT, AND IT IS REAL. Normal offsets of a concave curve fold at the
    curve's centres of curvature; beyond the medial axis the nearest-point map
    is many-to-one and `min` puts a crease (a gradient discontinuity, not a
    step) in the bed. `offset_fold_fraction` measures how much of a given ramp
    is past it, and this file reports the number rather than hiding it.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    x_s = np.asarray(x_s, float)
    # refine the shoreline polyline: the distance to a chord is short of the
    # distance to the curve by the chord's own sagitta, and at dy = 16 m on a
    # 90 m radius of curvature that is 0.36 m of bathymetry.
    t = np.arange(y.size, dtype=float)
    tf = np.linspace(0.0, y.size - 1.0, (y.size - 1) * int(n_sub) + 1)
    Py = np.interp(tf, t, y)
    Px = np.interp(tf, t, x_s)
    # AND THE POLYLINE IS CONTINUED PAST BOTH ENDS ALONG ITS OWN END TANGENTS.
    # Without it the cells in the two offshore corners find their nearest point
    # at the polyline's END rather than on the coast, and the ramp acquires a
    # radial fan there -- 0.91 m of spurious depth on this scene, measured. The
    # coast does not stop at the frame edge, and the only continuation that
    # introduces no second form is the curve's own tangent.
    # ONE long segment at each end and not a thousand short ones: a straight
    # continuation is exactly represented by a single chord, and replicating
    # the refined end segment out to the shelf cap makes the cost of this
    # function quadratic in the refinement for no accuracy at all.
    ext = 1.5 * (D_SHELF / DEAN_A) ** 1.5
    e0 = np.array([Px[1] - Px[0], Py[1] - Py[0]])
    e1 = np.array([Px[-1] - Px[-2], Py[-1] - Py[-2]])
    e0 = e0 / max(float(np.hypot(*e0)), 1e-12)
    e1 = e1 / max(float(np.hypot(*e1)), 1e-12)
    Px = np.concatenate([[Px[0] - ext * e0[0]], Px, [Px[-1] + ext * e1[0]]])
    Py = np.concatenate([[Py[0] - ext * e0[1]], Py, [Py[-1] + ext * e1[1]]])
    ax, ay = Px[:-1], Py[:-1]
    ex, ey = Px[1:] - ax, Py[1:] - ay
    L2 = np.maximum(ex * ex + ey * ey, 1e-30)
    out = np.empty((y.size, x.size))
    for j0 in range(0, y.size, int(chunk)):
        j1 = min(j0 + int(chunk), y.size)
        XX = x[None, :, None]
        YY = y[j0:j1, None, None]
        u = np.clip(((XX - ax) * ex + (YY - ay) * ey) / L2, 0.0, 1.0)
        dxq = XX - (ax + u * ex)
        dyq = YY - (ay + u * ey)
        out[j0:j1] = np.sqrt(np.min(dxq * dxq + dyq * dyq, axis=2))
    return np.where(x[None, :] >= x_s[:, None], out, -out)


def offset_fold_fraction(x, y, x_s, s_max=None, n_sub=8, tol=0.9):
    """The share of the SEAWARD ramp that lies past the shoreline's medial
    axis, where the normal-offset family has folded.

    |grad(distance)| is 1 wherever the nearest-point map is single-valued and
    dips below it on the medial axis, so the fraction of ramp cells with
    |grad s| < `tol` is a direct, gridded measure of the fold. It is reported
    and not repaired: the fold is a property of the SHORELINE, not of the
    method, and a wiggly coast really does have converging shoreface contours
    behind every one of its bumps."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    s = shoreline_offset(x, y, x_s, n_sub=n_sub)
    if s_max is None:
        s_max = (D_SHELF / DEAN_A) ** 1.5
    g = np.hypot(np.gradient(s, x, axis=1), np.gradient(s, y, axis=0))
    band = (s < 0.0) & (-s < float(s_max))
    if not band.any():
        return 0.0
    return float(np.mean(g[band] < float(tol)))


def plan_ramp_normal(x, y, x_s, A=DEAN_A, d_shelf=D_SHELF, s_plain=S_PLAIN,
                     n_sub=8):
    """The Dean equilibrium ramp keyed to the NORMAL distance to the shoreline.

    `d = A * dist(P, shore)^(2/3)`, capped at the shelf depth, with the coastal
    plain landward. Chapter 12's own sentence is "depth proportional to
    distance^(2/3) ... a graded ramp from shoreline to shelf break"; this is
    that sentence with "distance" read as distance to the SHORELINE, which is
    the only reading that does not depend on the grid's orientation.

    It is `plan_ramp` exactly when the shore is parallel to the grid's y axis
    and `plan_ramp_polar` (to the discretisation of the shoreline polyline)
    when the shore is a circular arc about the pole. See `shoreline_offset` for
    why those are the only two cases where the three agree.
    """
    s = shoreline_offset(x, y, x_s, n_sub=n_sub)
    sea = -np.minimum(A * np.maximum(-s, 0.0) ** (2.0 / 3.0), d_shelf)
    land = s_plain * np.maximum(s, 0.0)
    return np.where(s >= 0.0, land, sea)


def plan_field(x, y, x_s, T=T_SWELL, H0=H0_SWELL, theta0=THETA0_SWELL,
               contour=True, ramp=None, **kw):
    """The bed AND the wave field for a stated plan-form, in one call.

    ONE CODE PATH. The straight coast, the rotated coast, the spiral bay and
    the circular bay differ by the array `x_s` and by nothing else: same ramp,
    same transform, same breaking, same offshore spectrum. That is what makes
    the curved/straight pair a MEASUREMENT rather than two renders.

    `contour=True` takes the offshore Snell against the plan-form's own
    contour normal, which is the only way a rotated or curved coast gets its
    boundary condition right. Setting it False is the deliberate defect.

    `ramp` selects the KEYING and defaults to `plan_ramp`, the cross-shore one,
    so every row waves 1-9 published is bit-identical. Wave 10 passes
    `plan_ramp_normal` and the difference between the two is the measurement.
    """
    h2 = (plan_ramp if ramp is None else ramp)(x, y, x_s)
    n0 = -shore_normal_angle(y, x_s) if contour else None
    return h2, transform_2d(x, y, h2, T, H0, theta0, contour0=n0, **kw)


def shore_normal_angle(y, x_s):
    """phi_s = atan(dx_s/dy), the angle the shoreline tangent makes with the
    alongshore axis -- equivalently MINUS the angle the shoreward normal makes
    with the cross-shore axis.

    The sign matters and it is the one thing in this section a reader will get
    backwards. Tangent t = (x_s', 1)/N; rotating it by -90 deg gives
    (1, -x_s')/N, which points SHOREWARD (+x). Its angle to +x is -phi_s. A
    wave travelling at theta to +x therefore meets the shore at

        theta_loc = theta + phi_s

    which `plan_transport` uses and the suite checks against a hand-rotated
    coast."""
    return np.arctan(np.gradient(np.asarray(x_s, float), np.asarray(y, float)))


def breaker_row(tr2, gamma_b=GAMMA_B):
    """Per alongshore row: the SEAWARD-most breaking cell and the wave there.

    The seaward-most and not the largest, because that is where the bar's
    break line is and where `break_lines` reads it in 1-D. Rows that never
    break are flagged rather than silently given row zero."""
    brk = np.asarray(tr2['brk'])
    ny = brk.shape[0]
    idx = np.full(ny, -1)
    for j in range(ny):
        ii = np.nonzero(brk[j])[0]
        if ii.size:
            idx[j] = int(ii[0])
    ok = idx >= 0
    r = np.arange(ny)
    take = np.where(ok, idx, 0)
    return dict(i=idx, ok=ok,
                H=tr2['H'][r, take], theta=tr2['theta'][r, take],
                d=tr2['d'][r, take], x=np.asarray(tr2['x'])[take])


def cerc_transport(H_b, theta_loc, k_cerc=K_CERC, gamma_b=GAMMA_B):
    """CERC longshore transport, volumetric, m^3/s, positive toward +y.

        Q = k / (16 (s-1)(1-p) sqrt(gamma)) * sqrt(g) * H_b^(5/2) * sin(2 th)

    The sin(2 theta) is chapter 12's own statement of the closure ("Q_long ~
    sin(2 (waveAngle - shorelineNormal))", Komar & Inman 1970) and the rest is
    the standard conversion of the immersed-weight rate to a bulk volume with
    the pore space in it. s and p are this file's RHO_S/RHO_SW and POROSITY.

    WHAT MATTERS FOR THIS SECTION is that the whole prefactor is positive and
    constant, so Q = 0 if and only if sin(2 theta_loc) = 0. The equilibrium
    plan-form cannot depend on k_cerc, and the suite proves it by doubling it.
    """
    s = RHO_S / RHO_SW
    coef = (float(k_cerc) / (16.0 * (s - 1.0) * (1.0 - POROSITY)
                             * math.sqrt(gamma_b)))
    return (coef * math.sqrt(G) * np.asarray(H_b, float) ** 2.5
            * np.sin(2.0 * np.asarray(theta_loc, float)))


def plan_transport(y, x_s, tr2, k_cerc=K_CERC, edge=3):
    """The longshore transport at stations along a stated shoreline, from a
    solved plan wave field.

    `edge` rows are dropped at each alongshore end: `transform_2d`'s transverse
    flux divergence is one-sided there and its Snell march has no upwind
    neighbour, so those rows carry a boundary artefact and not a measurement.
    Saying which rows are excluded, and why, is the eleventh way a measurement
    lies (a test window pinned where the phenomenon is not) run in reverse.
    """
    y = np.asarray(y, float)
    br = breaker_row(tr2)
    phi = shore_normal_angle(y, x_s)
    th_loc = br['theta'] + phi
    Q = cerc_transport(br['H'], th_loc, k_cerc=k_cerc)
    m = np.zeros(y.size, bool)
    m[int(edge):y.size - int(edge)] = True
    m &= br['ok']
    return dict(theta_loc=th_loc, Q=Q, phi_s=phi, mask=m,
                theta_b=br['theta'], H_b=br['H'], d_b=br['d'], x_b=br['x'],
                Q_rms=float(np.sqrt(np.mean(Q[m] ** 2))) if m.any()
                else float('nan'),
                Q_mean=float(np.mean(Q[m])) if m.any() else float('nan'),
                Q_max=float(np.max(np.abs(Q[m]))) if m.any() else float('nan'),
                th_mean=float(np.mean(np.abs(th_loc[m]))) if m.any()
                else float('nan'),
                th_max=float(np.max(np.abs(th_loc[m]))) if m.any()
                else float('nan'))


def zero_transport_plan(y, x_ref, theta0):
    """THE EXACT ZERO-TRANSPORT SHORELINE FOR A PLANE OFFSHORE CREST, and it
    is not a bay.

    THE ANGLE IS THE DEEP-WATER ONE AND NOT THE BREAKING ONE, and getting that
    wrong is this section's own factor-of-two trap. Snell is
    sin(theta) = (c/c_0) sin(theta_0) with theta measured from the LOCAL shore
    normal; refraction shrinks the obliquity but sends it to zero only if it
    was zero to begin with, because c/c_0 is never zero. So theta_b = 0
    requires theta_0,local = 0, i.e. phi_s = -theta_0 -- the FULL deep-water
    obliquity, 20 deg here, not the 6.56 deg the wave has left at breaking. A
    coast rotated by the breaking angle is still 2.78 deg oblique and still
    carries 43 per cent of the straight coast's transport; this file wrote that
    version first and the suite caught it.

        x_s(y) = x_ref - tan(theta_0) * (y - y_mid)

    A STRAIGHT COAST, ROTATED until it faces the swell. This is chapter 12's
    own sentence -- "headlands retreat faster than bays ... until the coast
    straightens" -- as an equation, and it is RIGHT: with plane offshore crests
    and shore-parallel contours, ANY curvature at all raises the transport,
    because theta_loc can be zero at one station only.

    So it is also the proof that a curved static-equilibrium bay is IMPOSSIBLE
    without an alongshore FAN in the wave direction. The bay is not an
    equilibrium of the shoreline; it is an equilibrium of the shoreline AND the
    headland that shelters it. This function is the control that shows the
    transport measurement CAN return zero -- without it, a near-zero reading on
    the bay would prove nothing about the bay and everything about the meter.
    """
    y = np.asarray(y, float)
    return (float(x_ref)
            - math.tan(float(theta0)) * (y - 0.5 * (y[0] + y[-1])))


def required_fan(y, x_s, edge=3):
    """The alongshore swing of the wave orthogonal that a stated shoreline
    needs in order to be in static equilibrium, radians.

    theta_loc = 0 demands the orthogonal lie at -phi_s(y). Its RANGE across the
    bay is the fan the sheltering headland has to supply, and it is the
    quantitative form of "the bay needs diffraction". An OUTPUT of the
    geometry, with no wave model in it at all."""
    phi = shore_normal_angle(y, x_s)
    m = slice(int(edge), np.asarray(y).size - int(edge))
    psi = -phi[m]
    return dict(psi=psi, swing=float(psi.max() - psi.min()),
                lo=float(psi.min()), hi=float(psi.max()))


def fan_theta0(y, x_s, D, cap=None):
    """The per-row DEEP-WATER wave direction of a field whose orthogonals
    radiate from the pole D.

    This is the boundary condition a diffracting headland imposes: in the lee
    of a tip the crests are arcs about the tip and the orthogonals are radii.
    It is a stated OFFSHORE condition -- everything between it and the beach,
    shoaling and refraction and breaking, stays an output. The standing ruling
    holds.

    THE RADIUS IS TAKEN TO THE SHORELINE POINT OF THE ROW, NOT TO THE ROW'S
    OFFSHORE CELL, and the difference is the whole thing. The orthogonal that
    ends at shoreline station (x_s(y), y) is the radius through THAT point; the
    radius through the offshore cell at the same y is a different ray, off by
    up to 24 deg on this bay, and feeding it leaves 4.9 deg of residual
    obliquity on a STRAIGHT coast, which is how this file found the error --
    the fan was reducing the obliquity everywhere instead of reducing it on the
    bay it belongs to.

    The pole is `spiral_pole`'s own, so the fan and the plan-form come from the
    SAME geometry. That is the point: the bay and the wave field that holds it
    are one object, and feeding one without the other is what waves 1-8 did.
    """
    y = np.asarray(y, float)
    D = np.asarray(D, float)
    th = np.arctan2(y - D[1], np.asarray(x_s, float) - D[0])
    if cap is not None:
        th = np.clip(th, -float(cap), float(cap))
    return th


def fit_log_spiral(pts, alpha0=None, D0=None, n_iter=400):
    """Fit a log spiral to a polyline by least squares on (pole, alpha), and
    return the rms radial residual in metres.

    A SECOND ROUTE AND NOT THE CONSTRUCTION'S. `spiral_pole` solves two exact
    conditions; this minimises a residual over all the sampled points and over
    alpha as well, so a shoreline that came from somewhere else -- the coastal
    loop, a morphodynamic run, a straight line -- gets a number that means
    something. On the constructed bay the two must agree, and that agreement is
    a tier-3 row rather than a tautology.
    """
    pts = np.asarray(pts, float)

    def rms(p):
        D = p[:2]
        a = p[2]
        v = pts - D
        r = np.hypot(v[:, 0], v[:, 1])
        if np.any(r <= 0.0):
            return 1e9
        ph = np.unwrap(np.arctan2(v[:, 1], v[:, 0]))
        # the best-fit R_a is the geometric mean residual, in closed form
        z = np.log(r) - ph / math.tan(a)
        return float(np.sqrt(np.mean((z - z.mean()) ** 2))) * float(r.mean())

    ch = pts[-1] - pts[0]
    L = float(np.hypot(ch[0], ch[1]))
    p = np.array([D0[0], D0[1], alpha0] if (D0 is not None and alpha0)
                 else [pts[0, 0] + 0.5 * L, pts[0, 1] - 0.5 * L,
                       math.radians(85.0)])
    step = np.array([0.05 * L, 0.05 * L, math.radians(2.0)])
    best = rms(p)
    for _ in range(int(n_iter)):
        moved = False
        for kk in range(3):
            for sgn in (+1.0, -1.0):
                q = p.copy()
                q[kk] += sgn * step[kk]
                if not (math.radians(1.0) < q[2] < math.radians(179.0)):
                    continue
                v = rms(q)
                if v < best:
                    best, p, moved = v, q, True
        if not moved:
            step *= 0.5
            if float(np.max(step / np.array([L, L, 1.0]))) < 1e-9:
                break
    return dict(D=p[:2].copy(), alpha=float(p[2]), rms=float(best))


def equilibrium_plan(y=None, x_s=None, coast=None, theta0=THETA0_SWELL,
                     T=T_SWELL, H0=H0_SWELL, frac=0.25, delta=None):
    """THE DELIVERABLE: the static-equilibrium bay for this scene.

    Inputs, and every one of them already existed:
      * the two rock anchors, from the coastal loop's plan-form (geology);
      * alpha = 90 deg - theta_b, from the 1-D transform's own breaking
        obliquity (the stated offshore spectrum, refracted -- an OUTPUT);
      * khat, the deep-water wave vector (the stated offshore spectrum).

    Outputs: the pole, the shoreline x_s(y), the indentation, and the fan the
    field must carry for the shoreline to be an equilibrium. Nothing is fitted
    and nothing is placed.
    """
    if coast is None and (y is None or x_s is None):
        coast = run_coast()
    if y is None:
        y = coast['y']
    if x_s is None:
        x_s = coast['x_s']
    y = np.asarray(y, float)
    A1, A2, j1, j2 = headland_anchors(x_s, y, frac=frac)
    sc1d = _scene_1d(T, H0, theta0)
    theta_b = sc1d['theta_b']
    alpha = equilibrium_alpha(theta_b if delta is None else delta)
    khat = np.array([math.cos(theta0), math.sin(theta0)])
    D, res = spiral_pole(A1, A2, alpha, khat)
    pts = spiral_points(D, A1, A2, alpha)

    # THE COAST IS THREE PIECES AND THE LITERATURE'S BAY IS THE MIDDLE ONE.
    # Updrift of the diffraction point A1 is the HEADLAND, which is rock and
    # keeps the coastal loop's own plan-form. Between the anchors is the
    # SPIRAL. Downdrift of the downcoast control point A2 is the STRAIGHT
    # TANGENTIAL BEACH, parallel to the incoming crests -- and it joins the
    # spiral with a continuous tangent BY CONSTRUCTION, because "tangent
    # perpendicular to khat at A2" is the very condition that fixed the pole.
    # No join is smoothed and no third parameter is introduced.
    xs_sp = np.interp(y, pts[:, 1], pts[:, 0])
    tan_dir = spiral_tangent(math.atan2(A2[1] - D[1], A2[0] - D[0]), alpha)
    slope_t = float(tan_dir[0] / tan_dir[1]) if abs(tan_dir[1]) > 1e-12 else 0.0
    xs_tan = A2[0] + slope_t * (y - A2[1])
    x_rock = np.asarray(x_s, float)
    d_head = x_rock - x_rock[j1] + A1[0]         # the headland, shifted to meet
    xs_bay = np.where(y < A1[1], d_head,
                      np.where(y > A2[1], xs_tan, xs_sp))

    off, sag, chord = chord_offset(np.stack([xs_bay, y], axis=1))
    off_s, sag_s, chord_s = chord_offset(pts)
    fan = required_fan(y, xs_bay)
    return dict(y=y, x_s=xs_bay, x_s_spiral=xs_sp, x_s_tangent=xs_tan,
                pts=pts, D=D, alpha=alpha, theta_b=theta_b,
                res=res, A1=A1, A2=A2, j1=j1, j2=j2, sagitta=sag,
                sagitta_spiral=sag_s, chord_spiral=chord_s,
                chord=chord, offset=off, fan=fan, khat=khat,
                slope_tangent=slope_t,
                x_s_rock=x_rock,
                H_b=sc1d['H_b'], d_b=sc1d['d_b'],
                r_pole=float(np.hypot(*(A1 - D))))


_SC1D = {}


def _scene_1d(T, H0, theta0):
    """The 1-D transform's breaking state, cached. The offshore spectrum's
    residual obliquity at the break point is the only wave number the
    plan-form construction uses, and it is an OUTPUT."""
    key = (T, H0, theta0)
    if key not in _SC1D:
        xg = make_grid()
        tr = transform(xg, dean_bed(xg), T, H0, theta0)
        b = breaker_state(tr)
        _SC1D[key] = dict(theta_b=b['theta_b'], H_b=b['H_b'], d_b=b['d_b'],
                          x_b=b['x'], c_b=b['c_b'])
    return _SC1D[key]


# ------------------------------------------------------------- the bay, run
X_LEN_BAY = 1000.0      # m, cross-shore extent of the plan domain
Y_HALF_BAY = 704.0      # m, half the alongshore extent. 1408 m of coast holds
                        # three to four hardness cells at HARD_LAM_Y, which is
                        # what makes a headland-bay-headland scene rather than
                        # one wiggle.
DX_COAST = 4.0          # m, the coastal loop's cross-shore spacing. The coastal
DY_BAY = 16.0           # m, alongshore spacing. Both are LANDFORM-scale grids:
                        # the coastal loop's own features (cliff, bench, the
                        # embayment) are tens to hundreds of metres, while the
                        # BAR is 11 m wide -- so the morphodynamic step is run on
                        # a finer cross-shore grid and the coastal loop's result
                        # is interpolated onto it. Reported rather than assumed:
                        # the suite carries the coastal loop at 4 m against 2 m.
N_COAST = 4000          # coastal-loop iterations. K_COAST*N_COAST is the clock
                        # and the suite checks the plan-form is unchanged when
                        # the two are traded against each other.

_BAY_CACHE = {}


SCENE_STANDS = 2            # rungs the SCENE's history runs. Two, and the
                            # number is the domain's rather than a choice:
                            # `terraces_in_domain` on the 316 m plateau is
                            # 0.06-0.63 of ONE Quaternary tread, so a flight is
                            # a landform this window on the coast cannot hold.
                            # What it can hold is one emerged tread and the
                            # present bench below it, which is the pair the
                            # camera is standing on and looking down.


def run_coast(dx=DX_COAST, dy=DY_BAY, x_len=X_LEN_BAY, y_half=Y_HALF_BAY,
              n_steps=N_COAST, uniform_hardness=False, stands=None,
              uplift=UPLIFT_RATE, period=EUSTATIC_PERIOD, **kw):
    """Chapter 12's coastal loop on the plan grid. Cached, because every row of
    the suite that asks about the bay wants the same coast.

    `stands` IS OFF BY DEFAULT AND THAT IS DELIBERATE, exactly as wave 9's
    `embay` was: every measurement waves 1-12 published was taken on the
    single-stand coast, and a wave that changes the plan-form under them makes
    413 rows incomparable in one move. With `stands=None` this is byte-for-byte
    wave 12's function.

    `stands=n` runs the SEA-LEVEL HISTORY instead -- `n` stands, oldest first,
    in the falling-sea frame (`stand_levels`), the last of them at the present
    datum. The plateau then stops being `initial_coast`'s declared ramp and
    becomes an EMERGED TERRACE TREAD: an output of the same notch/collapse/
    deposit loop that cuts the present bench, planed at its own stand's level
    and left standing when the sea fell away from it.
    """
    key = ('coast', dx, dy, x_len, y_half, n_steps, uniform_hardness,
           stands, uplift, period,
           tuple(sorted((k, v) for k, v in kw.items()
                        if isinstance(v, (int, float, bool, str)))))
    if key in _BAY_CACHE:
        return _BAY_CACHE[key]
    x = np.arange(0.0, x_len + dx, dx)
    y = np.arange(-y_half, y_half + dy, dy)
    h0 = initial_coast(x, y)
    hard = hardness_field(x, y, uniform=uniform_hardness)
    rec = None
    h_rock = None
    if stands is None:
        h, expo, vol, exported, s_row, hist = evolve_coast(
            x, y, h0, hard, n_steps=n_steps, expo_every=max(n_steps // 16, 1),
            **kw)
    else:
        n = int(stands)
        eus = tuple(EUSTATIC_HIGHSTANDS)[-n:]
        lv = stand_levels(eus, uplift=uplift, period=period, frame='sea')
        seq = [(lv[i], n_steps) for i in range(n)]
        h, h_rock, expo, vol, exported, s_row, rec = evolve_coast_stands(
            x, y, h0, hard, seq, uplift=uplift, period=period, frame='sea',
            expo_every=max(n_steps // 16, 1), **kw)
        hist = [(0, h0.copy()), (n * n_steps - 1, h.copy())]
    out = dict(x=x, y=y, h0=h0, h=h, hard=hard, expo=expo, vol=vol,
               exported=exported, sand_row=s_row,
               hist=hist, x_s=shoreline_x(x, h),
               x_s0=shoreline_x(x, h0), dx=dx, dy=dy,
               stands=stands, record=rec, h_rock_loop=h_rock)
    _BAY_CACHE[key] = out
    return out


TERRACE_STANDS = 4          # rungs the instrument builds. Four is the fewest
                            # that makes the arithmetic-progression test
                            # non-trivial: three points fit a line through two
                            # of them, four do not.
TERRACE_STEPS = 900         # coastal-loop iterations per stand on the
                            # instrument. NOT a physical duration -- it is the
                            # clock set so that each tread is wide enough to be
                            # separated by `terrace_levels` and narrow enough
                            # that four of them fit the instrument's domain.
                            # `tread_width` says what a real highstand would
                            # cut and `terraces_in_domain` says how many of
                            # those fit the SCENE, which is the finding.


TERRACE_UPLIFT = 5.0e-5     # m/yr on the INSTRUMENT ONLY, so that U*P = 5.0 m
                            # per rung. It is not the scene's uplift and is not
                            # meant to be: what bounds it is the instrument's
                            # own relief, by the same arithmetic
                            # `uplift_ceiling` states -- a flight of n rungs
                            # needs (n-1)*U*P of relief BELOW the first stand's
                            # shoreline for the sea to still have somewhere to
                            # be after the land has been lifted n-1 times. The
                            # suite sweeps this and the ladder must track it
                            # linearly; that is the claim, not the number.


def uplift_ceiling(relief, n_stands, period=EUSTATIC_PERIOD):
    """The largest uplift rate a domain with `relief` metres of it can hold a
    flight of `n_stands` in.

    THE VERTICAL TWIN OF `terraces_in_domain`, and a flight is bounded by both.
    Each `h += uplift*dt` between stands lifts the whole grid, so the sea must
    still find ground at its own level afterwards: after `n-1` lifts that is
    ground which started `(n-1)*U*P` below the first stand's shoreline. Run a
    history past this ceiling and the domain emerges completely -- the loop
    then runs on dry land, erodes nothing, and returns a single flat surface,
    which is exactly what the first run of the instrument here did.
    """
    return float(relief) / max((int(n_stands) - 1) * float(period), 1e-9)


def run_terrace(n_stands=TERRACE_STANDS, n_steps=TERRACE_STEPS,
                uplift=TERRACE_UPLIFT, period=EUSTATIC_PERIOD,
                eustatic=EUSTATIC_HIGHSTANDS, x_len=2400.0, dx=8.0,
                y_half=96.0, dy=32.0, x_shore=1600.0, s_sea=0.05,
                s_plain=S_PLAIN, uniform=False, frame='uplift'):
    """THE INSTRUMENT: a domain wide and deep enough to hold a flight, so that
    the closed form can be checked against a realisation.

    Standing ruling 14 -- a measurement is worthless until the control whose
    answer is known in advance has been built. Here the control is the ladder
    itself: `terrace_ladder` says where the rungs must land before the loop is
    run, and `terrace_levels` reads them off the surface afterwards without
    ever seeing the closed form. Two routes, no shared source.

    THE INITIAL CONDITION IS A PLAIN WEDGE AND NOT `initial_coast`, deliberately.
    A control's starting surface should have no feature that could be mistaken
    for the answer, and the Dean ramp has one: its slope at the offshore end of
    a 2 km domain is 0.007, which is inside the same order as the planation
    slopes the loop produces (0.0004-0.0021), so a flat-run detector would have
    to be tuned to separate them. A straight 1:20 seabed is 25x the planation
    slope and needs no tuning. The scene's bed keeps the Dean ramp; chapter 12
    requires it there and this is not there.

    `uniform=True` flattens the eustatic tuple to all-zero, which is the
    STRONGER control: the ladder is then an exact arithmetic progression of
    common difference `uplift*period`, so an error in the uplift bookkeeping
    shows up as a non-constant difference rather than as an offset -- and the
    offset is the only thing `planation_depth` can be wrong about.
    """
    key = ('terrace', n_stands, n_steps, uplift, period, x_len, dx, y_half, dy,
           x_shore, s_sea, s_plain, bool(uniform), frame,
           tuple(eustatic or ()))
    if key in _BAY_CACHE:
        return _BAY_CACHE[key]
    x = np.arange(0.0, x_len + dx, dx)
    y = np.arange(-y_half, y_half + dy, dy)
    h1 = np.where(x >= x_shore, s_plain * (x - x_shore),
                  s_sea * (x - x_shore))
    h0 = np.repeat(h1[None, :], y.size, axis=0)
    if frame == 'sea':
        # see `stand_levels`: the sea frame starts from the ground the uplift
        # frame ENDS on, so both are read with the present stand as the datum.
        h0 = h0 + float(uplift) * (int(n_stands) - 1) * float(period)
    hard = hardness_field(x, y, uniform=True)
    eus = ((0.0,) * n_stands if uniform
           else tuple(eustatic)[-n_stands:])
    lv = stand_levels(eus, uplift=uplift, period=period, frame=frame)
    stands = [(lv[i], n_steps) for i in range(n_stands)]
    h, h_rock, expo, vol, exp_, s_row, rec = evolve_coast_stands(
        x, y, h0, hard, stands, uplift=uplift, period=period, frame=frame)
    out = dict(x=x, y=y, h0=h0, h=h, h_rock=h_rock, hard=hard, expo=expo,
               vol=vol, exported=exp_, sand_row=s_row, record=rec,
               stands=stands, eustatic=eus, uplift=uplift, period=period,
               frame=frame, dx=dx, dy=dy, x_shore=x_shore, s_sea=s_sea,
               relief=float(s_sea * x_shore),
               ladder=terrace_ladder(eustatic=eus, uplift=uplift,
                                     period=period,
                                     planation=planation_depth(
                                         n_steps=n_steps)))
    _BAY_CACHE[key] = out
    return out


def run_bay(dx=2.0, n_steps=1200, dt=1500.0, T=T_SWELL, H0=H0_SWELL,
            theta0=THETA0_SWELL, coast=None, k_every=4, embay=False,
            stands=None, **flux_kw):
    """The whole scene: coastal loop -> plan bed -> 2-D transform -> Exner.

    `dt` is set from the same diffusion bound the 1-D loop uses,
    dt < dx^2/(2*D_eff) with D_eff ~ 6.7e-4 m^2/s -- 2985 s at dx = 2 m, and
    1500 s is half of it. n_steps*dt is held at 500 hours, the same physical
    duration waves 1 and 2 ran, so the bar is comparable across the three.
    """
    key = ('bay', dx, n_steps, dt, T, H0, theta0, k_every, bool(embay),
           stands, tuple(sorted((k, v) for k, v in flux_kw.items())))
    if coast is None and key in _BAY_CACHE:
        return _BAY_CACHE[key]
    cs = run_coast(stands=stands) if coast is None else coast
    xc, y = cs['x'], cs['y']
    x = np.arange(0.0, xc[-1] + dx, dx)
    hc = np.stack([np.interp(x, xc, cs['h'][j]) for j in range(y.size)])
    h0c = np.stack([np.interp(x, xc, cs['h0'][j]) for j in range(y.size)])
    # WAVE 9. `embay` is off by default and that is deliberate: every
    # measurement waves 1-8 published was taken on the un-embayed bed, and a
    # wave that changes the plan-form under them makes 301 rows incomparable
    # in one move. The embayment is its own entry point, exactly as wave 8's
    # four fields were, and the flag IS the curved/straight control the
    # transport measurement needs.
    ep = equilibrium_plan(coast=cs) if embay else None
    stand_age = 0.0
    if cs.get('record'):
        stand_age = float(cs['record'][0].get('age', 0.0))
    h_init, x_s, h_dean, bch = bay_bed(x, y, hc, h0c,
                                       sand_row=cs.get('sand_row'),
                                       plan=None if ep is None else ep['x_s'],
                                       stand_age=stand_age)
    h, tr2, hist, edge = evolve_2d(x, y, h_init, T, H0, theta0,
                                   n_steps=n_steps, dt=dt, k_every=k_every,
                                   **flux_kw)
    out = dict(x=x, y=y, h_init=h_init, h=h, tr=tr2, x_s=x_s, h_dean=h_dean,
               beach=bch, embay=bool(embay), plan=ep,
               hist=hist, coast=cs, stands=stands, stand_age=stand_age,
               dx=dx, dy=float(y[1] - y[0]), edge=edge,
               tr_init=transform_2d(x, y, h_init, T, H0, theta0))
    if coast is None:
        _BAY_CACHE[key] = out
    return out


def row_slice(tr2, j):
    """One alongshore row of a plan transform, shaped like a 1-D `transform()`.

    So that every reader waves 1 and 2 wrote -- `breaker_state`, `break_lines`,
    `surf_zone_spans`, `crest_depth_ratio`, `breaking_fraction_bj` -- can be
    pointed at the plan field without being rewritten. Reuse, not a copy: if the
    1-D reader is wrong, it is wrong in both places and one bug fixes both.
    """
    out = {}
    for k, v in tr2.items():
        if isinstance(v, np.ndarray) and v.ndim == 2:
            out[k] = v[j]
        else:
            out[k] = v
    out['x'] = tr2['x']
    out['y'] = float(tr2['y'][j])
    return out


def bay_crest_ratio(bay, field='wave'):
    """`d_bar / (H_b/gamma)` in every alongshore row, both terms in ONE field.

    Wave 2's correction, carried into 2-D where there are more ways to make the
    mistake, not fewer: the crest depth and the breaker depth must be read from
    the same version of the depth. `field` is passed through to
    `crest_depth_ratio`, which has no default of its own.
    """
    x, y, h, hi, tr = bay['x'], bay['y'], bay['h'], bay['h_init'], bay['tr']
    out = np.full(y.size, np.nan)
    for j in range(y.size):
        cr = bar_crest(x, h[j], hi[j])
        if cr is None:
            continue
        trj = row_slice(tr, j)
        b = breaker_state(trj)
        if b is None:
            continue
        out[j] = crest_depth_ratio(trj, cr, b, field=field)
    return out


def refraction_slope_closed_form(tr2, d, d_ref):
    """The closed form the crest-azimuth regression is measured against.

    Snell about a contour whose normal points at azimuth beta:

        sin(theta - beta) = sin(theta_ref - beta) * c(d)/c(d_ref)

    Differentiate with respect to beta at fixed theta_ref and small angles:

        d(theta)/d(beta) = 1 - c(d)/c(d_ref)

    So the regression slope is NOT 1 and should not be: a crest is parallel to
    the contour only in the limit c -> 0. What the closed form predicts is how
    far onto the contour the crest has turned by the time it reaches depth `d`,
    given the depth `d_ref` at which the contours started to curve -- here the
    seaward edge of the flat shelf, which is where this scene's bathymetry
    stops being alongshore-uniform.
    """
    omega = tr2['omega']
    c = omega / wavenumber(omega, np.asarray(d, float))
    c_ref = omega / wavenumber(omega, np.asarray(d_ref, float))
    return 1.0 - c / c_ref


def crest_azimuth_regression(tr2, d_lo=1.0, d_hi=4.0, slope_min=0.004):
    """Regress the WAVE-CREST azimuth on the DEPTH-CONTOUR azimuth, in the band
    where the surf lives. This is bar section J's by-eye criterion as a number.

    Both azimuths are measured from the same field -- the depth the wave saw --
    for the reason `contour_alignment` sets out at length. The slope of the
    regression is the answer:

        slope 0  the crests are straight while the shore curves -- the failure
                 bar section J says "a layman could catch"
        slope 1  the crests are exactly parallel to the contours everywhere

    A real refracting wave lands between the two and approaches 1 as the depth
    falls, because Snell only takes sin(theta) to zero in the limit.
    """
    d = tr2['d']
    gx = np.gradient(d, tr2['dx'], axis=1)
    gy = np.gradient(d, tr2['dy'], axis=0)
    mag = np.hypot(gx, gy)
    # gx <= -slope_min, not |grad| >= slope_min: see `contour_alignment`. Behind
    # a bar the depth gradient reverses and its azimuth wraps through 180 deg,
    # which turns a regression on azimuths into nonsense (measured: a beta range
    # of 359.9 degrees and an R^2 of 0.017 on a field that is manifestly
    # refracting).
    m = ((tr2['d_raw'] >= d_lo) & (tr2['d_raw'] <= d_hi) & (mag >= slope_min)
         & (gx <= -slope_min))
    if m.sum() < 20:
        return None
    beta = np.degrees(np.arctan2(-gy[m], -gx[m]))       # contour normal azimuth
    th = np.degrees(tr2['theta'][m])                    # ray azimuth
    A = np.vstack([beta, np.ones_like(beta)]).T
    coef, *_ = np.linalg.lstsq(A, th, rcond=None)
    pred = A @ coef
    ss_res = float(((th - pred) ** 2).sum())
    ss_tot = float(((th - th.mean()) ** 2).sum())
    return dict(slope=float(coef[0]), intercept=float(coef[1]),
                r2=1.0 - ss_res / max(ss_tot, 1e-30), n=int(m.sum()),
                beta_range=float(beta.max() - beta.min()),
                theta_range=float(th.max() - th.min()))


# --------------------------------------------------------------------- runner
def bar_width(x, h, h_ref, i_crest):
    """Full width of the bar at half its crest anomaly, metres."""
    a = np.asarray(h, float) - np.asarray(h_ref, float)
    half = 0.5 * a[i_crest]
    j = i_crest
    while j > 0 and a[j] > half:
        j -= 1
    k = i_crest
    while k < a.size - 1 and a[k] > half:
        k += 1
    return float(x[k] - x[j])


def shoaling_exponent(tr, kd_max=0.5):
    """The measured local exponent of H against d, d(ln H)/d(ln d).

    Green's law says -1/4 in the shallow-water limit. Measured over the
    non-breaking cells shallower than kd_max, so the number reported is a
    MEASUREMENT of this transform, not a restatement of the law.
    """
    m = (~tr['brk']) & (tr['k'] * tr['d'] < kd_max) & (tr['H'] > 0)
    if m.sum() < 8:
        return None
    lh = np.log(tr['H'][m])
    ld = np.log(tr['d'][m])
    A = np.vstack([ld, np.ones_like(ld)]).T
    return float(np.linalg.lstsq(A, lh, rcond=None)[0][0])


def run_scene(H0=H0_SWELL, T=T_SWELL, theta0=THETA0_SWELL, n_steps=N_STEPS,
              dt=DT_MORPH, x_len=X_LEN, dx=DX, **kw):
    """The scene: Dean ramp in, evolved bed and its transform out."""
    x = make_grid(x_len, dx)
    h_dean = dean_bed(x)
    h, tr, hist = evolve(x, h_dean, T, H0, theta0, n_steps=n_steps, dt=dt, **kw)
    return dict(x=x, h_dean=h_dean, h=h, tr=tr, hist=hist)


def _print_report():
    """Every diagnostic in this project lives in a scene file and prints from
    there, never from a module on import -- the pool's rule, kept."""
    np.set_printoptions(precision=4, suppress=True)
    print('=' * 78)
    print('BEACH AT ALJEZUR -- bathymetry, wave transform, morphodynamic loop')
    print('=' * 78)

    # The frames' own sun, through the SHARED module. Not used by any number
    # below -- it is here because it is the one thing this scene inherits from
    # the pool for free, and because it is a check on the bar's own header.
    el, el_app, az, am = ATM.solar_position(
        37.3167, -8.8000, 2026, 8, 12, 18, 8, 0.0, 1.0)[:4]
    print('sun (bar surf frames, 2026-08-12 18:08 WEST, 37.3167N 8.8000W):')
    print('   elevation %.3f deg geometric / %.3f apparent   azimuth %.3f deg'
          '   air mass %.3f' % (el, el_app, az, am))
    print('   bar.md states                 27.17            268.31       2.182')

    x = make_grid()
    h_dean = dean_bed(x)
    L0 = deep_wavelength(T_SWELL)
    print('\n-- the offshore sea state, stated OUTSIDE and never adjusted')
    print('   H_0 = %.2f m   T = %.1f s   theta_0 = %.1f deg   L_0 = %.1f m'
          % (H0_SWELL, T_SWELL, math.degrees(THETA0_SWELL), L0))
    print('   wave base L_0/2 = %.1f m; the domain is %.1f m deep at x=0, so the'
          % (L0 / 2, -h_dean[0]))
    print('   whole domain is INSIDE wave base and the chapter\'s "never run the'
          '\n   morphodynamic step below wave base" gate is not active here.')

    w_s = settling_velocity()
    print('\n-- the sediment')
    print('   D50 = %.2f mm (?)   w_s = %.4f m/s (Soulsby 1997)' % (D50 * 1e3, w_s))

    print('\n-- the initial bed: Dean ramp, ONE parameter, monotone')
    print('   A = %.3f m^(1/3), depth at x=0 %.2f m, at 100 m offshore %.2f m'
          % (DEAN_A, -h_dean[0], -h_dean[np.argmin(np.abs(x - (X_LEN - 100)))]))

    tr0 = transform(x, h_dean, T_SWELL, H0_SWELL, THETA0_SWELL)
    b0 = breaker_state(tr0)
    print('   on the RAMP the wave breaks once, at x = %.1f m, H_b = %.2f m,'
          % (b0['x'], b0['H_b']))
    print('   d_b = %.2f m -- one line, which is what a monotone profile can'
          % b0['d_b'])
    print('   only ever give.')

    print('\n-- running the loop (waves -> stress -> currents -> flux -> Exner)')
    print('   %d steps x %.0f s = %.0f h of continuous swell'
          % (N_STEPS, DT_MORPH, N_STEPS * DT_MORPH / 3600))
    h, tr, _ = evolve(x, h_dean, T_SWELL, H0_SWELL, THETA0_SWELL)
    cr = bar_crest(x, h, h_dean)
    th_ = trough(x, h, h_dean, cr['i'])
    b = breaker_state(tr)
    print('   bar crest   x = %.1f m   depth over crest d = %.3f m   amp %.3f m'
          % (cr['x'], cr['d'], cr['amp']))
    print('   bar width at half amplitude %.1f m' % bar_width(x, h, h_dean, cr['i']))
    print('   trough      x = %.1f m   depth %.3f m' % (th_['x'], th_['d']))
    print('   H_b = %.3f m at d_b = %.3f m  ->  H_b/gamma = %.3f m'
          % (b['H_b'], b['d_b'], b['H_b'] / GAMMA_B))
    d_pred = b['H_b'] / GAMMA_B
    print('   chapter 12 predicts the crest at d ~ H_b/gamma: %.3f vs %.3f m'
          % (cr['d'], d_pred))
    print('   ratio d_crest/(H_b/gamma), RAW bed depth      = %.3f' %
          (cr['d'] / d_pred))
    print('   ratio d_crest/(H_b/gamma), the depth the WAVE = %.3f' %
          (tr['d'][cr['i']] / d_pred))
    print('     -- H_b and d_b come out of the transform, which reads the')
    print('        filtered depth; the raw bed is 0.19 m shallower at an 11 m')
    print('        crest. Comparing the two FIELDS is the whole of the 0.893.')
    print('   volume change over the whole run %+.2e m2 (Exner is closed)'
          % float(np.trapezoid(h - h_dean, x)))
    print('   break ONSETS (H crosses gamma*d): %s'
          % ['%.0f m' % s[0] for s in break_lines(tr)])
    print('   SURF ZONE (the wave is actually breaking): %s'
          % ['%.0f-%.0f m' % s for s in surf_zone_spans(tr)])

    print('\n-- section B, the second breaking line: the reform is a DISTANCE')
    d_c, d_t = tr['d'][cr['i']], tr['d'][th_['i']]
    L_bar = th_['x'] - cr['x']
    m_in = float(np.gradient(tr['d'], tr['dx'])[min(cr['i'] + 80, x.size - 1)])
    print('   saturated H/d on the inner slope: %.4f measured, %.4f closed form'
          % (float((tr['H'] / tr['d'])[min(cr['i'] + 80, x.size - 1)]),
             float(saturated_ratio(m_in))))
    print('     GAMMA_eq = gamma_s/sqrt(1 + (5/2)(dd/dx)/K) -- a broken wave on')
    print('     a SHOALING bed decays to %.3f and not to gamma_s = 0.40, so it'
          % float(saturated_ratio(m_in)))
    print('     can only un-break where the bed DEEPENS: behind the bar.')
    print('   crest-to-trough: L = %.0f m, relief %.3f m (in the wave depth)'
          % (L_bar, d_t - d_c))
    print('   Dally e-foldings delivered  %.3f' % dally_efoldings(d_c, d_t, L_bar))
    L_need = min(_reform_length(d_c, max(d_t - d_c, 1e-3)), 400.0)
    print('   Dally e-foldings NEEDED     %.3f  (a back slope %.0f m long at'
          % (dally_efoldings(d_c, d_t, L_need), L_need))
    print('     the same relief, against the %.0f m the loop digs)' % L_bar)
    print('   or, at the loop\'s own %.0f m, a relief of %.3f m against %.3f'
          % (L_bar, reform_relief(d_c, L_bar), d_t - d_c))
    print('   AND THE TWO ARE THE SAME NUMBER: the trough sits %.2f Dally decay'
          % (L_bar * K_DALLY / d_c))
    print('   lengths d/K behind the crest, because the dissipation that digs')
    print('   it decays over exactly that length -- so a one-bar breakpoint')
    print('   model digs a trough one e-folding wide and needs two.')
    hp = probe_back_slope(x, h, h_dean, cr['i'], int(round(L_need)),
                          max(th_['d'] - cr['d'], 1e-3))
    print('   PROOF THE TRANSFORM HAS THE MEMORY: take the loop\'s OWN relief')
    print('   of %.2f m, spread it over %.0f m instead of %.0f, hand that to the'
          % (th_['d'] - cr['d'], round(L_need), L_bar))
    print('   transform as a diagnostic bed, and the surf zone becomes %s'
          % ['%.0f-%.0f m' % s for s in surf_zone_spans(
              transform(x, hp, T_SWELL, H0_SWELL, THETA0_SWELL))])
    print('   -- two lines with calm water between. Nothing was tuned; the')
    print('   only thing that changed is how far the wave travels.')
    qb = breaking_fraction_bj(tr)
    print('   Battjes-Janssen Q_b: %.3f over the bar, %.3f in the trough, %.3f'
          % (qb[cr['i']], qb[th_['i']], qb[min(cr['i'] + 120, x.size - 1)]))
    print('   inshore -- the CONTRAST section B photographs is there, the')
    print('   second line still is not.')

    print('\n-- the four closed forms, measured on this run')
    ex = shoaling_exponent(tr)
    print('   1 SHOALING   d(lnH)/d(lnd) over the unbroken shallow cells = %+.4f'
          % (ex if ex is not None else float('nan')))
    print('               Green: -0.2500. The gap is the finite kd this beach')
    print('               actually reaches, not an error -- see validate_beach.')
    sn = np.sin(tr['theta']) / tr['c']
    print('   2 REFRACTION sin(theta)/c along the profile: %.6e +- %.1e'
          % (sn.mean(), sn.std()))
    print('               theta_0 = %.1f deg -> theta at the break = %.2f deg'
          % (math.degrees(THETA0_SWELL), math.degrees(b['theta_b'])))
    print('   3 BREAKER    H/d at the first break = %.4f (gamma = %.2f)'
          % (b['H_b'] / b['d_b'], GAMMA_B))
    om = dimensionless_fall_velocity(b['H_b'], w_s, T_SWELL)
    tanb = float(abs(np.gradient(h, DX)[cr['i']]))
    xi0 = iribarren(tanb, H0_SWELL, L0)
    xib = iribarren(tanb, b['H_b'], L0)
    print('   4 RUN-UP     xi_0 = %.3f (%s), xi_b = %.3f (%s)'
          % (xi0, breaker_class(xi0, 'deep'), xib, breaker_class(xib, 'local')))
    print('               R ~ H_0 xi_0 = %.2f m (Hunt 1959; the constant is ?)'
          % runup_hunt(H0_SWELL, xi0))

    print('\n-- beach state (Wright & Short 1984, via chapter 12)')
    print('   Omega = H_b/(w_s T) = %.2f  ->  %s' % (om, beach_state(om)))

    print('\n-- the storm (the chapter predicts the bar moves SEAWARD)')
    h_st, tr_st, _ = evolve(x, h_dean, T_SWELL, H0_STORM, THETA0_SWELL)
    cs = bar_crest(x, h_st, h_dean)
    bs = breaker_state(tr_st)
    print('   H_0 %.1f m -> crest x = %.1f m, d = %.3f m, H_b/gamma = %.3f m'
          % (H0_STORM, cs['x'], cs['d'], bs['H_b'] / GAMMA_B))
    print('   H_0 %.1f m -> crest x = %.1f m, d = %.3f m, H_b/gamma = %.3f m'
          % (H0_SWELL, cr['x'], cr['d'], b['H_b'] / GAMMA_B))
    print('   the storm bar sits %.0f m further offshore in %.2f m more water'
          % (cr['x'] - cs['x'], cs['d'] - cr['d']))
    print('=' * 78)


if __name__ == '__main__':
    _print_report()
