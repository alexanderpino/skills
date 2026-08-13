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
    """
    f = broken_fraction(tr)
    if n_lag <= 0:
        return f
    alpha = 1.0 - np.exp(-tr['dx'] * tr['k'] / (2.0 * math.pi * n_lag))
    out = np.empty_like(f)
    out[0] = f[0]
    for i in range(1, f.size):
        out[i] = out[i - 1] + alpha[i] * (f[i] - out[i - 1])
    return out


def sediment_flux(tr, k_q=K_Q, lam_u=LAM_U, k_roller=K_ROLLER,
                  eps_slope=EPS_SLOPE, skew=True, undertow_on=True,
                  n_lag=ROLLER_LAG):
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
    dhdx = np.gradient(tr['h'], tr['dx'])
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


def break_lines(tr, gamma_b=GAMMA_B):
    """The x-intervals where H/d is at or above the breaker index.

    This is the section-B test in one function: on a barred profile it must
    return TWO intervals with a gap between them, and it must do so without
    anything in the scene saying "break here".
    """
    over = tr['H'] >= gamma_b * tr['d']
    out = []
    i = 0
    n = over.size
    while i < n:
        if over[i]:
            j = i
            while j + 1 < n and over[j + 1]:
                j += 1
            out.append((float(tr['x'][i]), float(tr['x'][j])))
            i = j + 1
        else:
            i += 1
    return out


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
    print('   chapter 12 predicts the crest at d ~ H_b/gamma: %.3f vs %.3f m'
          % (cr['d'], b['H_b'] / GAMMA_B))
    print('   ratio d_crest/(H_b/gamma) = %.3f' % (cr['d'] / (b['H_b'] / GAMMA_B)))
    print('   volume change over the whole run %+.2e m2 (Exner is closed)'
          % float(np.trapezoid(h - h_dean, x)))
    print('   break onsets (H crosses gamma*d): %s'
          % ['%.0f m' % s[0] for s in break_lines(tr)])

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
