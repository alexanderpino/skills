"""The slope statistics DERIVED from the forcing, and Cox & Munk as its limit.

WHY THIS FILE EXISTS. Every mean square slope in this project has, until now,
come from one line:

    mss = 0.003 + 5.12e-3 * U            (Cox & Munk 1954)

That line is cited, so it is honest. It is not DERIVED, and the difference
matters more here than anywhere else in the run, because the standing ruling is
that *the physics comes from physical effects, never from a constant chosen to
make the picture right*. Cox & Munk is a **fitted boundary condition**: a 1954
empirical summary of what wind does to open water with long fetch, obtained by
photographing sun glitter from an aircraft over the Pacific off Maui. Feeding it
to a scene is asserting a measurement taken somewhere else.

The project owner put the objection in the sharpest available form:

    "Water is water. De grootte van het oppervlak zou niets/weinig uit moeten
     maken als de formules juist zijn."

and the owner is right in the way that matters. The optics IS scale-free --
Fresnel, the specular condition and the slope-to-radiance map know nothing about
basin size. What differs between a sea and a swimming pool is exactly ONE input,
the slope statistics, and asserting them from a fit is what makes two scenes
look like two physics.

So this file computes the slope statistics from a wind-wave SPECTRUM instead:

    mss(<k_c) = INT_0^{k_c} k^2 S(k) dk = INT B(k) d ln k                  (W1)

with S(k) the omnidirectional elevation spectrum and B(k) = k^3 S(k) the
dimensionless CURVATURE spectrum. (W1) is worth reading twice: **B(k) is the
slope variance per unit ln k**. Every statement in this file is a statement
about how much slope variance sits in each decade of wavenumber.

WHICH SPECTRUM, AND WHY THIS ONE. Elfouhaily, Chapron, Katsaros & Vandemark
(1997), JGR 102(C7), 15781-15796, "A unified directional spectrum for long and
short wind-driven waves" -- ECKV throughout. It was built for exactly this
purpose: to span gravity and capillary wavenumbers in one continuous expression
with no discontinuity at the join, parameterised by wind AND fetch, and
constructed so that its slope integral reproduces Cox & Munk rather than
assuming it. If it does reproduce Cox & Munk, the fit stops being an input and
becomes a CONSEQUENCE, and the sea and the pool become one calculation with two
values of one argument.

--------------------------------------------------------------------------
PROVENANCE, STATED PLAINLY, BECAUSE RULING 9 SAYS CONSULT THE SOURCE OR DO NOT
INVENT IT.

**The ECKV paper itself is NOT held in this container.** It is paywalled at AGU
and no copy was reachable. What was reachable, read, and cross-checked here in
2026-08 is four independent restatements, and the equations below are the
intersection of them:

  [M]  Curtis Mobley, *Ocean Optics Web Book*, "Wave Variance Spectra:
       Examples", oceanopticsbook.info -- gives every ECKV equation with the
       paper's own equation numbers (ECKV 30, 31, 32, 34, 40, 41, 44).
  [W]  Wang et al. (2025), *Atmos. Meas. Tech.* **18**, 6329-6344,
       doi:10.5194/amt-18-6329-2025 -- open access; restates B_l, alpha_p,
       Omega, L_PM, J_p, gamma, sigma, c_p/c and the cut-off term as its
       Eqs. 3-7 and 11-18.
  [P]  Zhang et al., PMC6111991 (open access) -- restates the fetch law and
       k_p as its Eqs. 19, 22, 23.
  [H]  Hwang & Fois, arXiv:2204.11591 -- the mss/cut-off half: which upper
       wavenumber each INSTRUMENT integrates to.

⚠️ **Two transcription traps were found and both are live.** They are recorded
because a reader of one source alone would have shipped either of them, and
because `--bugs-spectrum` fires both:

  (a) **The square roots vanish in HTML.** [M]'s rendering of ECKV 32 reads
      `exp{-0.3162 Omega_c (k/kp - 1)}` and of the phase speed reads
      `c = (g/k)(1 + (k/km)^2)`. The second is DIMENSIONALLY IMPOSSIBLE -- a
      speed is not a speed squared -- which proves the conversion is dropping
      the radical rather than that the paper omits it. [W] Eq. 18 gives the
      same term as `exp{-(Omega/sqrt 10)[sqrt(k/kp) - 1]}` and [W] Eq. 17 gives
      `c_p/c = sqrt(k/k_p)`. The radical is real; note `1/sqrt(10) = 0.31623`,
      which is where [M]'s 0.3162 comes from. **Both are used below with the
      radical**, and `spec-no-sqrt` reintroduces the flat version.
  (b) **The fetch law's exponent looks like a subtraction.** [P] Eq. 22
      extracts as `Omega_c = 0.84 tanh[(X/X0)^0.4] - 0.75`. Read that way,
      infinite fetch gives `Omega_c = 0.84 - 0.75 = 0.09`, which contradicts
      the value *every* source states for a fully developed sea. Read as an
      EXPONENT, `Omega_c = 0.84 tanh[(X/X0)^0.4]^(-0.75)`, infinite fetch gives
      tanh -> 1 and `Omega_c -> 0.84` exactly, and zero fetch gives
      `Omega_c -> infinity` (an infinitely young sea). **The limit picks the
      reading**, which is why `omega_c_fully_developed` is a guard row and not
      a comment. `spec-fetch-subtract` reintroduces the subtraction.

Everything below is therefore marked **P (attribution)** for the ECKV paper and
**D** for the arithmetic, which is evaluated here. Nothing in this file claims
the 1997 paper was read.
--------------------------------------------------------------------------
"""

import math

import numpy as np

# --------------------------------------------------------------- constants
# `G` is the project's own standard gravity, imported rather than restated so
# that a scene and its spectrum cannot disagree about gravity. ECKV's own
# tabulations use 9.81; the difference is 1.5e-4 relative and is below every
# tolerance in this file, but it is stated rather than hidden.
G = 9.80665             # m/s^2, CGPM 1901. Exact by definition.

K_M = 370.0             # rad/m. ECKV's gravity-capillary scale. `P (attr)`.
                        # NOT an independent constant: see `capillary_wavenumber`
                        # below, which derives 367 rad/m from surface tension
                        # and finds ECKV's 370 inside 1%.
C_M = 0.23              # m/s, the phase speed at K_M -- and it is the MINIMUM
                        # of c(k). `P (attr)`; checked against the closed form
                        # in `min_phase_speed` and in the suite.
CD_10N = 0.00144        # neutral 10 m drag coefficient, ECKV's own value.
                        # `P (attr)`. u* = sqrt(CD_10N) * U10.
X_0 = 2.2e4             # dimensionless fetch scale in the wave-age law.
OMEGA_FD = 0.84         # inverse wave age of a FULLY DEVELOPED sea. `P (attr)`,
                        # and agreed by all four sources.
OMEGA_MAX = 5.0         # the largest inverse wave age ECKV's gamma branch is
                        # DEFINED for ([W] Eq. 14 states 0.84 < Omega < 1 and
                        # 1 < Omega < 5). Beyond it the model is extrapolating
                        # and this file says so rather than returning a number
                        # with a straight face. THIS IS THE POOL'S WHOLE STORY.
KAPPA = 0.4             # von Karman. Used ONLY for the 10 m -> 12.5 m wind
                        # conversion, and derived from CD_10N rather than
                        # introducing a roughness length of its own.

# Cox & Munk's own coefficients, kept here so the comparison is against the
# PUBLISHED fit and not against this project's restatement of it. `P` --
# verified 2026-08 against Wang et al. (2025) Eq. 12, which quotes
# `m_u = 3.16e-3 U`, `m_c = 3.0e-3 + 1.92e-3 U` at the 12.5 m mast height over
# 1-14 m/s, matching the answer key's G3 exactly.
CM_TOTAL_B = 0.003      # the COMBINED fit's intercept
CM_TOTAL_A = 5.12e-3    # the COMBINED fit's slope. NOTE this is the separately
                        # fitted total, NOT the sum of the components (5.08e-3).
                        # Answer key G4: a file that checks one against the
                        # other has misread the source.
CM_SIGMA = 0.004        # the paper's own quoted uncertainty on the clean-sea
                        # mss. It is the tolerance for the return row below,
                        # and it is the PAPER's number rather than one sized
                        # from the disagreement it has to accommodate.


def cox_munk_total(u125):
    """Cox & Munk's clean-sea total mean square slope. `U` at 12.5 m, 1-14 m/s."""
    return CM_TOTAL_B + CM_TOTAL_A * np.asarray(u125, float)


# ------------------------------------------------------- the wind, at a height
def roughness_length():
    """z0 implied by ECKV's OWN drag coefficient, metres.

    Cd = (kappa / ln(z/z0))^2 at z = 10, inverted. Nothing new is declared:
    the drag coefficient the spectrum already uses to get u* is the same one
    that fixes the logarithmic profile, so the height conversion below costs
    no extra constant. 2.643e-4 m."""
    return 10.0 * math.exp(-KAPPA / math.sqrt(CD_10N))


def u125_over_u10():
    """U(12.5 m) / U(10 m) in a neutral log profile. 1.02117.

    ⚠️ THIS IS THE ANSWER KEY'S G2 TRAP AND IT IS LIVE IN THIS PROJECT.
    ECKV is parameterised on U10. Cox & Munk's fit is at a 12.5 m mast. They
    are not the same wind, and `beach_optics.U10 = 6.0` is fed straight to a
    12.5 m fit. The conversion is only 2.1%, which is precisely why it survives
    -- it is far too small to notice in a picture and far too large to ignore
    in a row whose tolerance is 0.004 on a number near 0.034."""
    z0 = roughness_length()
    return math.log(12.5 / z0) / math.log(10.0 / z0)


def friction_velocity(u10):
    """u* = sqrt(Cd10N) U10, m/s. ECKV's own drag law. `P (attr)`."""
    return math.sqrt(CD_10N) * np.asarray(u10, float)


# ------------------------------------------------------------- the sea's age
def omega_c(u10, fetch):
    """Inverse wave age Omega_c = U10/c_p, from wind and FETCH.

    ECKV Eq. 37 as restated by [P] Eq. 22:

        X = g F / U10^2                     (dimensionless fetch)
        Omega_c = 0.84 tanh[(X/X_0)^0.4]^(-0.75),  X_0 = 2.2e4

    THE EXPONENT IS AN EXPONENT AND THE LIMIT PROVES IT -- see the header note
    (b). As F -> infinity, tanh -> 1 and Omega_c -> 0.84, the fully developed
    sea every source agrees on. As F -> 0, Omega_c -> infinity, an infinitely
    young sea. Both limits are guard rows.

    THIS IS THE ONLY PLACE BASIN SIZE ENTERS THE WHOLE DERIVATION, which is
    the owner's point made mechanical: fetch moves the PEAK, and nothing else
    in the model has a length scale in it."""
    u10 = np.asarray(u10, float)
    X = G * np.asarray(fetch, float) / (u10 * u10)
    t = np.tanh((X / X_0) ** 0.4)
    return OMEGA_FD * t ** (-0.75)


def fetch_for_omega(u10, om):
    """The fetch, metres, at which a wind of `u10` reaches inverse wave age
    `om`. The inverse of `omega_c`, closed form, used to locate the edge of
    ECKV's fitted domain for a given scene."""
    t = (OMEGA_FD / float(om)) ** (4.0 / 3.0)
    if not 0.0 < t < 1.0:
        raise ValueError('omega %g is outside the reachable range' % om)
    return (math.atanh(t) ** 2.5) * X_0 * float(u10) ** 2 / G


def peak_wavenumber(u10, fetch):
    """k_p = g Omega_c^2 / U10^2, rad/m. [P] Eq. 19; equivalently k_p =
    (Omega_c/U10)^2 g, since Omega_c = U10/c_p and c_p^2 = g/k_p."""
    om = omega_c(u10, fetch)
    return G * om * om / np.asarray(u10, float) ** 2


# ------------------------------------------------------------- phase speeds
def phase_speed(k):
    """c(k) = sqrt[(g/k)(1 + (k/k_m)^2)], m/s. The gravity-capillary dispersion
    relation written with ECKV's k_m in place of rho/sigma.

    ⚠️ THE RADICAL IS NOT OPTIONAL -- see header note (a). [M]'s HTML renders
    this without it, which would make a speed into a speed squared."""
    k = np.asarray(k, float)
    return np.sqrt((G / k) * (1.0 + (k / K_M) ** 2))


def min_phase_speed():
    """The minimum of c(k), reached at k = k_m. Closed form: differentiating
    c^2 = (g/k)(1 + k^2/k_m^2) gives dc^2/dk = 0 at k = k_m exactly, so
    c_min = c(k_m) = sqrt(2g/k_m). 0.2303 m/s at k_m = 370.

    This is the row that shows ECKV's `c_m = 0.23` is a CONSEQUENCE of its
    `k_m = 370` and not a second free constant."""
    return math.sqrt(2.0 * G / K_M)


def capillary_wavenumber(sigma=0.0728, rho=1000.0):
    """k = sqrt(rho g / sigma), rad/m -- the gravity-capillary wavenumber from
    surface tension, which is the SAME quantity ECKV calls k_m.

    367.0 rad/m for clean water at 20 C against ECKV's 370: agreement to 0.8%,
    from two completely different directions. `beach_optics.capillary_cutoff`
    already computes this with sea-water density; this one uses fresh water
    because ECKV's short-wave data are tank measurements. THAT k_m IS DERIVABLE
    AT ALL is what makes the upper end of the spectrum physics rather than a
    knob."""
    return math.sqrt(rho * G / sigma)


# ------------------------------------------------- the two equilibrium amplitudes
# Exposed as named functions rather than inlined, and the reason is a measured
# one. When these lived inside `curvature`, the suite could not tell
# `alpha_p ~ Omega^0.55` from `alpha_p ~ Omega^0.50`: at a fully developed sea
# Omega_c = 0.84, and ANY exponent of a number that close to 1 is that close to
# 1 (0.9107 against 0.9165, 0.6%). The whole section sat at that one fetch, so
# the exponent was a free parameter nothing could see -- the answer key's fifth
# rule, "no row at a degenerate argument", arriving in a new disguise. Splitting
# them out lets a row evaluate `alpha_p` at a YOUNG sea, where the two exponents
# part by 8%, without having to find an independent measurement of a young sea's
# mss (there is none in this container).
def alpha_p(u10, fetch):
    """The Phillips-Kitaigorodskii equilibrium parameter. ECKV Eq. 34.

    alpha_p = 0.006 Omega_c^0.55. ⚠️ THE 0.55 RESTS ON [M] ALONE -- [W]'s PDF
    extraction loses the superscript and no other source read here states it.
    It is checked in the suite as ARITHMETIC (does the code compute what the
    source says) and not as PHYSICS (is the source right), and the difference
    is stated because at large fetch nothing in this project could tell 0.55
    from 0.50 anyway."""
    return 0.006 * np.asarray(omega_c(u10, fetch), float) ** 0.55


def alpha_m(u10):
    """The short-wave equilibrium parameter. ECKV Eq. 44.

    alpha_m = 0.01 [1 + ln(u*/c_m)]      for u* <= c_m
            = 0.01 [1 + 3 ln(u*/c_m)]    for u* >  c_m

    ⚠️ **NO FETCH APPEARS HERE AND THAT IS THE WHOLE POINT.** This is the
    amplitude of the capillary half of the slope budget and it is a function of
    the friction velocity alone -- no basin, no fetch, no length scale. It is
    the owner's "water is water" in one line of algebra."""
    us = float(friction_velocity(u10))
    if us <= C_M:
        return 0.01 * (1.0 + math.log(us / C_M))
    return 0.01 * (1.0 + 3.0 * math.log(us / C_M))


# -------------------------------------------------------- the curvature spectrum
def curvature(k, u10, fetch, split=False):
    """B(k) = k^3 S(k), the dimensionless curvature spectrum. ECKV Eq. 30.

    B = B_l + B_h, long-wave plus short-wave, and (W1) makes B the slope
    variance per unit ln k, so these two ARE the slope budget.

        B_l = 0.5 alpha_p (c_p/c) F_p                          (ECKV 31)
        B_h = 0.5 alpha_m (c_m/c) F_m                          (ECKV 40)

    with, following [M] and [W] together:

        alpha_p = 0.006 Omega_c^0.55                           (ECKV 34)
        L_PM    = exp[-1.25 (k_p/k)^2]                         (ECKV 2)
        gamma   = 1.7                    for Omega_c <= 1
                = 1.7 + 6 log10(Omega_c) for Omega_c >  1      (ECKV 3)
        sigma   = 0.08 (1 + 4 Omega_c^-3)
        Gamma   = exp[-(sqrt(k/k_p) - 1)^2 / (2 sigma^2)]
        J_p     = gamma^Gamma
        F_p     = L_PM J_p exp[-(Omega_c/sqrt 10)(sqrt(k/k_p) - 1)]  (ECKV 32)
        alpha_m = 0.01 [1 +   ln(u*/c_m)]  for u* <= c_m       (ECKV 44)
                = 0.01 [1 + 3 ln(u*/c_m)]  for u* >  c_m
        F_m     = L_PM J_p exp[-0.25 (k/k_m - 1)^2]            (ECKV 41)

    ⚠️ **F_m carries L_PM J_p and ECKV Eq. 41 as PRINTED does not.** [M] flags
    this explicitly as a typo in the paper and supplies the factors; without
    them B_h has a step at low k. It matters almost nowhere -- both factors
    tend to 1 for k >> k_p, which is the whole range where B_h is not
    negligible -- and it is followed here with the source named.

    ⚠️ **alpha_m HAS A KINK AT u* = c_m AND THIS SCENE SITS 3% BELOW IT.**
    u* = c_m at U10 = 6.061 m/s. The scene's 6 m/s gives u* = 0.2230 against
    c_m = 0.23, so it uses the single-log branch, and a scene at 6.2 m/s would
    use the triple-log branch with three times the slope. A wind sweep that
    steps across 6.06 m/s crosses a derivative discontinuity in the model, not
    in the sea. Recorded in the suite as an explicit row rather than left for
    someone to rediscover as a kink in a plot.
    """
    k = np.asarray(k, float)
    om = float(omega_c(u10, fetch))
    kp = float(peak_wavenumber(u10, fetch))
    cp = math.sqrt(G / kp)
    c = phase_speed(k)

    l_pm = np.exp(-1.25 * (kp / k) ** 2)
    gam = 1.7 if om <= 1.0 else 1.7 + 6.0 * math.log10(om)
    sig = 0.08 * (1.0 + 4.0 * om ** -3)
    gamma_big = np.exp(-((np.sqrt(k / kp) - 1.0) ** 2) / (2.0 * sig * sig))
    j_p = gam ** gamma_big

    a_p = float(alpha_p(u10, fetch))
    f_p = l_pm * j_p * np.exp(-(om / math.sqrt(10.0))
                              * (np.sqrt(k / kp) - 1.0))
    b_l = 0.5 * a_p * (cp / c) * f_p

    a_m = float(alpha_m(u10))
    f_m = l_pm * j_p * np.exp(-0.25 * (k / K_M - 1.0) ** 2)
    b_h = 0.5 * a_m * (C_M / c) * f_m

    return (b_l, b_h) if split else b_l + b_h


def omni_spectrum(k, u10, fetch):
    """S(k) = k^-3 B(k), m^3 -- the omnidirectional elevation spectrum, with
    INT S dk the elevation variance and INT k^2 S dk the slope variance."""
    k = np.asarray(k, float)
    return curvature(k, u10, fetch) / k ** 3


# ------------------------------------------------------------------ the integrals
def _log_nodes(k_lo, k_hi, n):
    return np.linspace(math.log(k_lo), math.log(k_hi), int(n))


def mss(u10, fetch, k_hi, k_lo=1e-4, n=20001, split=False):
    """(W1): the mean square slope carried BELOW `k_hi`.

    mss = INT_{k_lo}^{k_hi} k^2 S(k) dk = INT B(k) d ln k, evaluated on a
    log-uniform grid because B is the natural integrand there and because the
    integral spans seven decades.

    ⚠️ **`k_hi` IS AN INSTRUMENT SETTING, NOT A PROPERTY OF THE WATER**, and
    this is the sharpest form of the owner's question. The integral is
    dominated by its high-wavenumber end, so `mss` is meaningless until the
    cut-off is named. Cox & Munk's own number is already filtered: [H] reports
    their artificial-slick runs suppressed waves shorter than about 0.3 m, an
    upper cut-off near **20 rad/m**, while microwave retrievals at L, Ku and Ka
    band integrate to **11, 95 and 250 rad/m**. Four instruments, four
    different "the" mean square slopes, one sea. `mss_cutoff_family` draws it.
    """
    lk = _log_nodes(k_lo, k_hi, n)
    kk = np.exp(lk)
    b_l, b_h = curvature(kk, u10, fetch, split=True)
    if split:
        return (float(np.trapezoid(b_l, lk)), float(np.trapezoid(b_h, lk)))
    return float(np.trapezoid(b_l + b_h, lk))


def elevation_variance(u10, fetch, k_hi=None, k_lo=1e-4, n=20001):
    """INT S(k) dk, m^2. Dominated by the peak, so it tests B_l where `mss`
    tests B_h -- two integrals of one spectrum with different sensitivities,
    which is what the answer key's seventh way asks for before two agreeing
    instruments may be called agreement."""
    k_hi = 10.0 * K_M if k_hi is None else k_hi
    lk = _log_nodes(k_lo, k_hi, n)
    kk = np.exp(lk)
    return float(np.trapezoid(omni_spectrum(kk, u10, fetch) * kk, lk))


def significant_height(u10, fetch, **kw):
    """H_s = 4 sqrt(m0), metres."""
    return 4.0 * math.sqrt(elevation_variance(u10, fetch, **kw))


def mss_cutoff_family(u10, fetch, cutoffs, k_lo=1e-4, n=20001):
    """`mss` at each of several upper cut-offs -- the family the evidence draws
    instead of a line, because a single curve of mss against wind silently
    asserts one cut-off."""
    return [mss(u10, fetch, float(kc), k_lo=k_lo, n=n) for kc in cutoffs]


def phillips_mss_below(k_c, k_lo, k_hi, mss_total):
    """The SAME quantity under the flat-B model this project shipped before:
    equal slope variance per octave between `k_lo` and `k_hi`, scaled so the
    whole range returns `mss_total`.

    mss(<k) = mss_total * ln(k/k_lo) / ln(k_hi/k_lo)

    It is here so the two constructions can be compared at one footprint by
    one function rather than by two files' conventions -- and comparing them is
    how this wave decides whether the render's smooth glitter path is a
    SPECTRUM defect or a REALISATION defect."""
    r = math.log(max(float(k_c), 1e-30) / k_lo) / math.log(k_hi / k_lo)
    return mss_total * min(max(r, 0.0), 1.0)


def resolvable_wavenumber(footprint_m):
    """The largest wavenumber a square pixel footprint can resolve, rad/m.

    k = pi / L: a box of side L averages a component of wavenumber k to
    sinc(kL/2), whose first zero is at kL/2 = pi. Half a wavelength per
    footprint is the Nyquist statement and it is the same convention
    `beach_optics.SlopeRealisation.slope` filters with."""
    return math.pi / float(footprint_m)


def domain_note(u10, fetch):
    """Whether ECKV is being INTERPOLATED or EXTRAPOLATED at this forcing.

    Returns (omega, ok, message). ECKV's gamma branch is defined on
    0.84 <= Omega_c <= 5 ([W] Eq. 14). A 10 m basin under a 6 m/s wind gives
    Omega_c = 12.3, so the model is being run 2.5x outside the largest inverse
    wave age it was ever fitted at, and the number it returns is an
    extrapolation. THE HONEST ANSWER FOR A SWIMMING POOL IS THAT THIS
    DERIVATION HAS NOTHING TO SAY, and this function is what makes the suite
    say it out loud instead of quoting the extrapolated figure."""
    om = float(omega_c(u10, fetch))
    ok = OMEGA_FD - 1e-9 <= om <= OMEGA_MAX + 1e-9
    if ok:
        msg = 'Omega_c = %.3f, inside ECKV\'s fitted 0.84-5' % om
    else:
        msg = ('Omega_c = %.3f, OUTSIDE ECKV\'s fitted 0.84-5 by %.1fx -- '
               'the spectrum is being extrapolated and its mss is not a '
               'prediction' % (om, om / OMEGA_MAX))
    return om, ok, msg
