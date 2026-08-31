"""Halfar ANATOMY — the SIA solver against an EXACT analytic solution.

WHY THIS FIGURE IS DIFFERENT FROM THE OTHER TWO. `hex_anatomy` and `anisotropy_anatomy` draw
geometry; `flow_anatomy` draws a contrast between two routings. This one draws the top rung of
`VALIDATION.md`'s own evidence ladder: agreement with a **published exact solution**, which is the
only kind of check that can tell "the code solves its equation correctly" apart from "the equation
is right".

THE BENCHMARK. Halfar (1983), as standardised by Bueler et al. (2005) 'Test B': an isothermal ice
dome spreading on a flat bed with no mass balance has a self-similar exact profile

    H(r, t) = H_c(t) · [ 1 − (r/R(t))^(4/3) ]^(3/7)                for Glen n = 3

⚠️ **NEITHER EXPONENT APPEARS ANYWHERE IN THE SOLVER.** `4/3 = (n+1)/n` and `3/7 = n/(2n+1)` are
consequences of the analytic solution. `sims_illustrative.glacier_sia` contains an `H^(n+2)`
diffusivity and nothing else; grep it for `3/7` and there is no hit. So recovering the shape — and,
in panel d, the exponent itself by fitting — is an independent check of the diffusivity rather than
a restatement of it. That independence is the whole value, and it is the property most easily lost
by a well-meaning refactor that "simplifies" the benchmark to reuse a constant.

WHAT THE PANELS SHOW. a: the profile at t=0 and after 1600 model years, with the analytic shape at
the evolved radius on top of it. b: the same profiles at four times, each normalised by its OWN
centre height and radius, collapsing onto one curve — self-similarity is the claim, and a collapse
is what it looks like. c: the residual against radius with the 3% acceptance band, showing WHERE
the error lives — the curve stops at the 0.7R fit-window edge, which the axis is ticked to make
plain. d: the exponent recovered by fitting, against the analytic 3/7.

e: THE RATE, and it is the panel that makes the other four mean anything. a–d all measure SHAPE,
and shape here is nearly vacuous on its own: the initial condition IS the Halfar profile, so a
solver that barely moves the ice matches it trivially — `H^(n+1)` in place of `H^(n+2)` leaves
every shape row green and LOWERS the residual. Panel e compares the characteristic time recovered
from the numerical thinning against Halfar's closed form, which no near-no-op can fake. See the
RATE section below for the derivation and the measured numbers.

⚠️ **PANEL e BOUNDS AGREEMENT, NOT CORRECTNESS, AND THE DIFFERENCE MATTERS.** Its 0.23% is a
systematic discretisation bias rather than noise, and CFL error cancels against it — the same
scheme run at CFL 0.30, half again past the factor `glacier_sia` chose, scores *better* than the
shipped solver, and every factor from 0.22 to 0.35 sits inside the band. `RATE_TOLERANCE` carries
the measured sweep; `cfl_distance_from_refined_timestep` is the companion quantity that has no
cancellation to hide in, and the two rows together are the guard. Neither one may be tightened
without reading that comment.

The numpy half carries no Pillow dependency, so `tests/test_halfar_anatomy.py` imports the
measurements from here. Writes `halfar_anatomy.png`. Run: `python halfar_anatomy.py`.
"""
from functools import lru_cache

import numpy as np

import sims_illustrative as sims

N = 121
CELLSIZE = 12000.0                 # 12 km cells, ~1450 km domain
H0, R0 = 3000.0, 500e3             # initial dome: 3 km thick, 500 km radius
A_GLEN = 1e-16 / (365.25 * 24 * 3600)      # 1e-16 Pa^-3 a^-1 in SI
DT = 200.0 * 3.15e7                        # 200 model years per step
STEPS = (2, 4, 8, 16)

# The analytic exponents. Named here ONLY so the figure can label them; the solver
# never sees these values, which is the point of the whole comparison.
P_RADIAL = 4.0 / 3.0               # (n+1)/n
P_SHAPE = 3.0 / 7.0                # n/(2n+1)
SHAPE_TOLERANCE = 0.03             # the acceptance band test_benchmarks.py uses


def radius_field(n=N, cellsize=CELLSIZE):
    c = (n - 1) // 2
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return np.hypot(xx - c, yy - c) * cellsize, c


def halfar(r, centre_height, radius):
    """The exact self-similar profile. Written from the paper, not from the solver."""
    s = np.clip(np.asarray(r, float) / radius, 0.0, 1.0)
    return centre_height * np.maximum(1.0 - s ** P_RADIAL, 0.0) ** P_SHAPE


@lru_cache(maxsize=None)
def evolve(steps, n=N, cellsize=CELLSIZE):
    """Run the shipped SIA solver from the exact profile for `steps` steps.

    `n` and `cellsize` are open because the GRID is the knob that actually moves the rate
    error (see `GRID_REFINEMENT` below); every shipped pair holds the domain SPAN fixed at
    `(n - 1) * cellsize = 1440 km` so only the resolution changes.

    ⚠️ MEMOISED, AND THE ARRAYS IT HANDS BACK ARE READ-ONLY — ENFORCED, NOT BY CONVENTION.
    The figure and its guard between them ask for the same eight-step run a dozen times, and
    the 241-cell refinement run costs ~10 s on its own. `profile` hands back VIEWS into these
    arrays, so a single stray write would silently poison every row downstream of it in the
    same process. The comment here used to say "read-only by convention" and the flags said
    otherwise; now they agree. Anything needing to mutate must `.copy()` first.
    """
    r, c = radius_field(n, cellsize)
    h_init = halfar(r, H0, R0)
    h = sims.glacier_sia(np.zeros((n, n)), h_init, steps=int(steps), A=A_GLEN,
                         dt=DT, cellsize=cellsize, beta=0.0, max_substeps=4000)
    for a in (r, h_init, h):
        a.flags.writeable = False
    return r, c, h_init, h


def profile(h, r, c):
    """A radial slice out from the dome centre, with its own centre height and margin."""
    rad, prof = r[c, c:], h[c, c:]
    margin = rad[prof > 1.0].max()
    return rad, prof, float(h[c, c]), float(margin)


def shape_residual(steps=8):
    """Max |numeric/H_c − analytic| over the interior, the quantity the suite bounds."""
    r, c, _h0, h = evolve(steps)
    rad, prof, hc, rn = profile(h, r, c)
    interior = (rad > 0) & (rad < 0.7 * rn)
    err = np.abs(prof[interior] / hc - halfar(rad[interior], 1.0, rn))
    return float(err.max()), rad[interior], err


def fitted_exponent(steps=8):
    """Recover `3/7` from the numerical profile by regression.

    `log(H/H_c) = p · log(1 − s^(4/3))`, so the slope IS the shape exponent. The fit window
    excludes the innermost cells (where `log(1 − s^(4/3))` → 0 and the regression is ill-conditioned)
    and the outer 30% (where the SIA degenerates at the margin and the exact solution has a
    singular slope).
    """
    r, c, _h0, h = evolve(steps)
    rad, prof, hc, rn = profile(h, r, c)
    m = (rad > 0.05 * rn) & (rad < 0.7 * rn) & (prof > 1.0)
    s = np.clip(rad[m] / rn, 0.0, 1.0)
    x = np.log(1.0 - s ** P_RADIAL)
    y = np.log(prof[m] / hc)
    return float(np.polyfit(x, y, 1)[0])


def volume_error(steps=8):
    """Relative change in total ice. With no mass balance this must be zero."""
    _r, _c, h_init, h = evolve(steps)
    return float(abs(h.sum() - h_init.sum()) / h_init.sum())


# --------------------------------------------------------------------------- #
# The RATE, which is the half of the benchmark the shape cannot see.
#
# ⚠️ WHY THIS EXISTS. Everything above measures SHAPE, and shape alone is a nearly
# vacuous check here: the initial condition IS the Halfar profile, so a solver that
# barely moves the ice scores BETTER on the residual than the correct one. Replacing
# the `H^(n+2)` diffusivity with `H^(n+1)` — a one-character edit — leaves every shape
# row green and lowers the residual from 0.0113 to 0.0049. A guard that a broken solver
# passes more comfortably than a correct one is not a guard.
#
# What the shape cannot see is HOW FAST the dome spreads, and Halfar fixes that too.
# The characteristic time follows from the ice constants alone:
#
#     Gamma = 2 A (rho g)^n / (n + 2)
#     t0    = (1/18)/Gamma * (7/4)^3 * R0^4 / H0^7
#
# and it enters the solution as H_c(t) = H0 (t/t0)^(-1/9), R(t) = R0 (t/t0)^(1/18),
# with the run starting at t = t0. So the SAME t0 can be recovered from the numerical
# thinning, and the two must agree. That comparison is sensitive to the diffusivity by
# construction — `H^(n+1)` puts the fitted t0 at 4.06e13 against an analytic 9.22e9,
# a factor of 4406.
#
# Note `n + 2` appears in Gamma. That is NOT the solver's exponent leaking in: it is the
# published Test B constant (Bueler et al. 2005), written from the paper like the 4/3
# and 3/7 above, and the test below checks it is not read out of sims_illustrative.

N_GLEN = 3
RHO_ICE, G_ACC = 917.0, 9.81


def t0_analytic(A=A_GLEN, rho=RHO_ICE, g=G_ACC, n=N_GLEN, h0=H0, r0=R0):
    """Halfar's characteristic time, from the ice constants and the dome alone.

    No part of the numerical run enters this. It is the closed form.
    """
    gamma = 2.0 * A * (rho * g) ** n / (n + 2.0)
    return (1.0 / 18.0) / gamma * (7.0 / 4.0) ** 3 * r0 ** 4 / h0 ** 7


def t0_from_thinning(steps=8, n=N, cellsize=CELLSIZE):
    """Recover t0 from how much the solver actually thinned the dome.

    `H_c(t0 + dt)/H0 = ((t0 + dt)/t0)^(-1/9)` inverts to `t0 = dt / ((H0/H_c)^9 - 1)`.
    """
    r, c, _h0, h = evolve(steps, n, cellsize)
    _rad, _prof, hc, _rn = profile(h, r, c)
    dt_total = steps * DT
    return float(dt_total / ((H0 / hc) ** 9.0 - 1.0))


# ⚠️ THE MARGIN CANNOT DO THIS JOB, and the reason is worth keeping. `R = R0 (t/t0)^(1/18)`
# inverts just as cleanly, and it looks like a free second opinion. It is not: `profile`
# finds the margin by thresholding on a 12 km grid, so R is quantised to one cell, one cell
# is 2.4% of R0, and the eighteenth power turns that into **53% in t0**. Measured, the margin
# route returns 6.5e9–8.6e9 across the four step counts, non-monotonically — an instrument
# whose noise dwarfs the effect it would police. It was written, measured, and removed.
#
# Nothing is lost by dropping it — but ⚠️ NOT for the reason this comment used to give. It
# argued from volume conservation, and volume conservation is vacuous AS EVIDENCE here:
# `glacier_sia` transports in divergence form, so total ice is conserved to 0.000e+00 under
# the BROKEN solver too — `H^(n+1)` scores exactly the same perfect zero. A quantity that
# cannot tell a right solver from a wrong one is not evidence about either.
#
# The argument that does hold runs the other way round, from the two rows that ARE
# discriminating. Panel b measures the SHAPE: the profiles at four times collapse onto the
# analytic curve, so the numerical field is `H_c · f(r/R)` with Halfar's own `f`. Panel e
# measures the THINNING RATE, which no near-no-op can fake. For a field of that form the
# ice under it is proportional to `R^2 · H_c`, so once the shape is pinned and H_c(t) is
# pinned, R(t) is not free — and THAT is the step conservation is used for: as an identity
# closing an argument whose evidence comes from elsewhere, never as the evidence itself.


def rate_error(steps=8, n=N, cellsize=CELLSIZE):
    """Relative disagreement between the fitted and the closed-form t0."""
    return float(abs(t0_from_thinning(steps, n, cellsize) / t0_analytic() - 1.0))


TIMESTEP_REFINEMENT = (1, 2, 4, 8, 16)


@lru_cache(maxsize=None)
def rate_error_at_refined_timestep(refine, steps=8, n=N, cellsize=CELLSIZE):
    """Rate error with the TIMESTEP cut `refine`-fold at FIXED total model time.

    ⚠️ THE CONTROL FOR A CLAIM THIS FIGURE USED TO MAKE AND WHICH WAS FALSE. Panel e's caption
    read "converging as the timestep falls", pointing at the 2/4/8/16 series. But `DT` is a
    fixed constant and `STEPS` multiplies TOTAL MODEL TIME — the axis says so — so that series
    varies run LENGTH, not step size. Cutting the actual timestep with the total time held
    fixed is what the sentence claimed, and it moves the answer AWAY, monotonically:
    0.002327 / 0.002330 / 0.002338 / 0.002351 / 0.002376 at dt/1…dt/16. The step-count series
    falls because the denominator `(H0/H_c)^9 - 1` grows with elapsed time — dilution, not
    convergence — and past 16 steps it turns round again (0.000459 / 0.000451 / 0.000854 /
    0.000999 at 16/32/64/128). This function exists so the corrected caption is guarded by a
    measurement rather than by a comment.
    """
    total = float(steps) * DT
    sub = int(steps) * int(refine)
    r, c = radius_field(n, cellsize)
    h_init = halfar(r, H0, R0)
    h = sims.glacier_sia(np.zeros((n, n)), h_init, steps=sub, A=A_GLEN,
                         dt=total / sub, cellsize=cellsize, beta=0.0, max_substeps=4000)
    hc = float(h[c, c])
    return float(abs(total / ((H0 / hc) ** 9.0 - 1.0) / t0_analytic() - 1.0))


# ⚠️ DERIVED FROM THE MEASURED ERROR SERIES, NOT CHOSEN TO BE COMFORTABLE — the sibling
# `SHAPE_TOLERANCE` cites `test_benchmarks.py` as its source, and this one needs a source too.
# The correct solver's rate error, measured at 2/4/8/16 steps: 0.01134, 0.00580, 0.00233,
# 0.00046. The row below is evaluated at 8 steps, so the bound is set at ~4x the 0.00233 that
# run scores.
#
# WHY IT IS NOT 0.05. At 5% this benchmark was decorative. Mutations of `glacier_sia` and
# their rate error at 8 steps, all of which a solver benchmark exists to catch:
#     CFL factor 0.2 -> 0.6           0.0333      CFL 0.2 -> 0.45              0.0279
#     substep floor 1e-6*dt -> 0.05*dt 0.0494     diffusivity x 1.04           0.0364
#     face averaging mean -> max      0.0193
# Every one of them passed at 0.05. All five fail at 0.01, and the shape rows — which the
# rate row exists precisely because they are near-vacuous — catch none of them.
#
# ⚠️ AND THE JUSTIFICATION ABOVE USED TO END "enough headroom that a seed or a numpy version
# cannot redden it", WHICH TREATED 0.00233 AS NOISE. It is not noise; it is a systematic
# discretisation bias, and CFL error CANCELS it, so this row is NOT monotone in the very
# defect it is quoted above as policing. The signed error over the CFL factor, everything
# else held at the shipped values (`rate_bias_at_cfl`, 8 steps, 121 cells):
#     0.05 +0.00340   0.10 +0.00304   0.20 +0.00233   0.25 +0.00193   0.28 +0.00102
#     0.30 -0.00016   0.32 -0.00139   0.35 -0.00528   0.38 -0.01023   0.45 -0.02792
#     0.60 -0.03326
# It is monotone DECREASING and crosses zero near 0.297. So CFL 0.30 — half again past the
# 0.2 the solver chose — scores 0.00016, fifteen times BETTER than the shipped solver, and
# every factor from 0.22 to 0.35 passes this bound. Refining toward stability makes the score
# WORSE. The 0.6 mutation in the table above is real but it sits far out on the tail where
# none of this is visible, which is exactly why it was the one that got written down.
#
# THEREFORE: this bound polices AGREEMENT, not correctness, and it cannot police the timestep
# at all inside 0.22–0.35. `tests/test_halfar_anatomy.py` carries the second row that can —
# distance from the refined-timestep answer, `CFL_REFERENCE` below — and the pair of them is
# the guard. Do NOT tighten this number toward the observed 0.00233 to "close the gap": the
# gap is a cancellation, not slack, and tightening would reject the correct solver at a
# refined timestep (0.00340 at CFL 0.05) while still admitting CFL 0.30.
RATE_TOLERANCE = 0.01

CFL_SHIPPED = 0.2                  # the factor `glacier_sia` hard-codes
CFL_REFERENCE = 0.05               # 4x refined: the "exact in time" answer this grid can afford
CFL_SWEEP = (CFL_REFERENCE, CFL_SHIPPED, 0.30, 0.45, 0.6)

# The GRID pairs panel e's companion row refines over: the domain SPAN `(n - 1) * cellsize` is
# held at exactly 1440 km, so the only thing that changes is resolution. ⚠️ This is the knob
# that moves the rate error; refining the TIMESTEP at fixed total time does not (see
# `caption_lines`).
#
# ⚠️ THE LADDER IS SIX POINTS BECAUSE THREE WERE NOT EVIDENCE OF ANYTHING. It was
# (61, 121, 241) — 0.00265 / 0.00233 / 0.00138 — and the row asserted that sequence is
# monotone, which reads as "finer is better". Over a wider set of grids at the same 1440 km
# span that is FALSE, and the counterexamples are worth pinning here so nobody "helpfully"
# adds one and reddens the row:
#     n=31  0.000532  <- the BEST of every grid measured, beating n=321's 0.000975
#     n=41  0.004375  <- the WORST
#     n=73  0.000347     n=91  0.002534     n=97  0.003222     n=145 0.001525
# n=73 and n=145 are the grids where `R0 / cellsize` is exactly 25 and 50 — the dome margin
# lands on a cell boundary — and they dip well below their neighbours. The trend across the
# six below is real and monotone; POINTWISE monotonicity in n is not a property of this
# solver, and `test_a_low_rate_error_is_not_evidence_of_a_good_grid` keeps the row from being
# read as if it were. Runtime is why the ladder stops at 241: n=289 costs ~23 s, n=321 ~34 s.
GRID_REFINEMENT = ((61, 24000.0), (81, 18000.0), (121, 12000.0),
                   (161, 9000.0), (181, 8000.0), (241, 6000.0))

# The coarse grid whose score beats the whole ladder. Named so the guard can measure the
# anomaly instead of quoting it. `(31 - 1) * 48000 = 1440 km`, the same span as the ladder.
GRID_COARSE_ANOMALY = (31, 48000.0)

# Panel e's y-range. Named so `tests/test_halfar_anatomy.py` can assert the acceptance band
# still fits inside the frame that is supposed to display it — the two used to be able to
# drift apart, and did: the panel was drawn on ±3% while the bound was ±5%.
RATE_PANEL_YLIM = (0.97, 1.03)


def sia_at_cfl(h_init, cfl, steps=8, n=N, cellsize=CELLSIZE):
    """`glacier_sia`'s transport loop, transcribed, with the CFL factor made an argument.

    ⚠️ A TRANSCRIPTION, AND THEREFORE A LIABILITY THE GUARD HAS TO CARRY. `glacier_sia`
    hard-codes `0.2 * cellsize^2 / D_max`, so the only way to sweep that factor without editing
    the shipped solver is to copy the loop. The copy is faithful today — at `cfl=0.2` it is
    BITWISE identical to `evolve(steps)[3]`, max difference 0.000e+00 — and
    `test_the_CFL_transcription_still_matches_the_shipped_solver` is what keeps it so. Without
    that row a change to `glacier_sia` would leave this function quietly "proving" bounds about
    a solver that no longer ships.

    Everything outside the CFL factor matches `sims_illustrative.glacier_sia` at `beta=0` and a
    zero bed line for line — including the ice constants, which are written here as the SOLVER's
    literals rather than as `RHO_ICE`/`G_ACC`. Those are the ANALYTIC side's constants; reading
    them here would wire the transcription to the thing it is being compared against.
    """
    n_glen, rho, g = 3, 917.0, 9.81
    c = 2.0 * A_GLEN / (n_glen + 2) * (rho * g) ** n_glen
    h = np.array(h_init, dtype=np.float64, copy=True)
    cs = float(cellsize)
    for _ in range(int(steps)):
        remaining, subs = DT, 0
        while remaining > 1e-6 * DT and subs < 4000:
            sy, sx = np.gradient(h, cs)
            d = c * h ** (n_glen + 2) * np.hypot(sx, sy) ** (n_glen - 1)
            dmax = float(d.max())
            if dmax <= 0.0:
                break
            sub = min(remaining, cfl * cs * cs / dmax)
            fx = 0.5 * (d[:, :-1] + d[:, 1:]) * (h[:, :-1] - h[:, 1:]) / cs
            fy = 0.5 * (d[:-1, :] + d[1:, :]) * (h[:-1, :] - h[1:, :]) / cs
            dh = np.zeros_like(h)
            dh[:, :-1] -= fx
            dh[:, 1:] += fx
            dh[:-1, :] -= fy
            dh[1:, :] += fy
            h = np.maximum(h + sub / cs * dh, 0.0)
            remaining -= sub
            subs += 1
    return h


@lru_cache(maxsize=None)
def rate_bias_at_cfl(cfl, steps=8, n=N, cellsize=CELLSIZE):
    """The SIGNED relative disagreement `t0_fitted / t0_analytic - 1` at CFL factor `cfl`.

    ⚠️ SIGNED ON PURPOSE. `rate_error` takes the absolute value, and that is what hides the
    defect recorded beside `RATE_TOLERANCE`: this quantity is monotone decreasing in `cfl` and
    crosses zero at ~0.297, so |·| turns a monotone bias into a V and hands the best score to a
    solver running half again past its own stability factor. Read the sign before concluding
    anything from the magnitude.
    """
    r, c = radius_field(n, cellsize)
    h = sia_at_cfl(halfar(r, H0, R0), cfl, steps, n, cellsize)
    fitted = float(steps) * DT / ((H0 / float(h[c, c])) ** 9.0 - 1.0)
    return float(fitted / t0_analytic() - 1.0)


def cfl_distance_from_refined_timestep(cfl, steps=8):
    """How far the recovered t0 sits from the SAME scheme run at `CFL_REFERENCE`.

    ⚠️ THIS IS THE QUANTITY THAT BOUNDS CORRECTNESS, WHERE `rate_error` BOUNDS AGREEMENT.
    The rate error at the shipped grid is a sum of a spatial bias (+0.00361 at cfl=0.02,
    extrapolating to ~+0.0038 at cfl→0) and a time-integration bias (negative, growing with
    `cfl`); they cancel near cfl=0.297, which is why the raw error is not monotone in the
    timestep. Subtracting the refined-timestep answer removes the spatial half, leaving the
    time-integration error alone — which IS monotone, and has nothing to cancel against.
    Measured at 8 steps, 121 cells:
        cfl 0.20 -> 0.00107    0.30 -> 0.00355    0.45 -> 0.03132    0.60 -> 0.03666
    `CFL_REFERENCE` is 0.05 rather than 0 because it has to be affordable: it is 4x refined and
    within 0.00022 of the cfl=0.02 answer, so it stands in for the exact-in-time solution to
    about a ninth of the tolerance below.
    """
    return float(abs(rate_bias_at_cfl(cfl, steps) - rate_bias_at_cfl(CFL_REFERENCE, steps)))


# The bound the row above is asserted against. Derived, like `RATE_TOLERANCE`, from the measured
# series and not from comfort: the shipped CFL 0.2 scores 0.00107 and the first factor past the
# stability limit that `RATE_TOLERANCE` cannot see — 0.30 — scores 0.00355. 0.002 sits at 1.9x
# the shipped value and 0.56x the first defect, which is the widest separation the measurements
# allow. Unlike `RATE_TOLERANCE` this quantity has no cancellation to hide in, so the margin
# does not need to be 4x.
CFL_CONSISTENCY_TOLERANCE = 0.002


def measurements():
    """Everything the figure prints, in one call the test can re-run."""
    r, c, h_init, h = evolve(8)
    _rad, _prof, hc, rn = profile(h, r, c)
    err, _radius, _curve = shape_residual(8)
    return {
        'centre_initial': H0, 'centre_final': hc,
        'radius_initial': R0, 'radius_final': rn,
        'shape_error': err,
        'volume_error': volume_error(8),
        'exponent': fitted_exponent(8),
        'exponent_analytic': P_SHAPE,
        't0_analytic': t0_analytic(),
        't0_fitted': t0_from_thinning(8),
        'rate_error': rate_error(8),
        # The grid-refinement series, measured rather than remembered, because the caption
        # quotes it. Coarse/fine are the ends of GRID_REFINEMENT.
        'rate_error_coarse': rate_error(8, *GRID_REFINEMENT[0]),
        'rate_error_fine': rate_error(8, *GRID_REFINEMENT[-1]),
        'rate_error_by_grid': tuple(rate_error(8, n, cs) for n, cs in GRID_REFINEMENT),
        # …and the grid that beats every rung of that ladder while being the coarsest of all,
        # because the caption says so and a caption that says so must measure it.
        'rate_error_coarse_anomaly': rate_error(8, *GRID_COARSE_ANOMALY),
        # The CFL cancellation, live: the shipped 0.2 against 0.30, which is half again past
        # the stability factor and scores an order of magnitude BETTER on this row.
        'rate_bias_shipped_cfl': rate_bias_at_cfl(CFL_SHIPPED),
        'rate_bias_over_cfl': rate_bias_at_cfl(0.30),
        'cfl_distance_shipped': cfl_distance_from_refined_timestep(CFL_SHIPPED),
        'cfl_distance_over': cfl_distance_from_refined_timestep(0.30),
        # …and the timestep series that does NOT converge, so the caption's correction is
        # quoting a live measurement rather than a remembered one.
        'rate_error_dt_coarse': rate_error_at_refined_timestep(TIMESTEP_REFINEMENT[0]),
        'rate_error_dt_fine': rate_error_at_refined_timestep(TIMESTEP_REFINEMENT[-1]),
        'rate_error_by_steps': tuple(rate_error(s) for s in STEPS),
        'years': 8 * DT / 3.15e7,
    }


# --------------------------------------------------------------------------- #
# drawing
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                          # pragma: no cover
    Image = None

PANEL_W, PANEL_H = 300, 330
COLS, ROWS = 5, 1
PAD, TOP = 26, 92

BG = (250, 249, 246)
INK = (28, 30, 36)
MUTED = (120, 122, 128)
GRID = (222, 220, 214)
RED = (176, 60, 36)
BLU = (38, 76, 158)
GRN = (26, 106, 68)
ACCENT = (150, 60, 130)


def _font(sz, bold=False):
    try:
        return ImageFont.truetype(
            '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'
            % ('-Bold' if bold else ''), sz)
    except OSError:                                          # pragma: no cover
        return ImageFont.load_default()


class _Ax(object):
    def __init__(self, d, box, xlim, ylim):
        self.d, self.box = d, box
        self.xlim, self.ylim = xlim, ylim
        d.rectangle(list(box), outline=MUTED)

    def px(self, x):
        lo, hi = self.xlim
        return self.box[0] + (x - lo) / (hi - lo) * (self.box[2] - self.box[0])

    def py(self, y):
        lo, hi = self.ylim
        return self.box[3] - (y - lo) / (hi - lo) * (self.box[3] - self.box[1])

    def line(self, xs, ys, col, width=2):
        pts = [c for x, y in zip(np.atleast_1d(xs), np.atleast_1d(ys))
               for c in (self.px(float(x)), self.py(float(y)))]
        if len(pts) >= 4:
            self.d.line(pts, fill=col, width=width)

    def hline(self, y, col, width=1):
        self.d.line([self.box[0], self.py(y), self.box[2], self.py(y)],
                    fill=col, width=width)


def build():
    if Image is None:                                        # pragma: no cover
        raise SystemExit('halfar_anatomy needs Pillow:  pip install pillow')
    m = measurements()
    W = PAD * 2 + COLS * PANEL_W
    img = Image.new('RGB', (W, canvas_height(m)), BG)
    d = ImageDraw.Draw(img)
    f_t, f_h, f_s, f_b = _font(26, True), _font(15, True), _font(13), _font(13, True)

    d.text((PAD, 22), 'The SIA solver against an exact solution — Halfar (1983)',
           INK, font=f_t)
    d.text((PAD, 54), 'chapter 12 · %d×%d cells at %.0f km · %.0f model years · '
                      'drawn from sims_illustrative.glacier_sia'
           % (N, N, CELLSIZE / 1e3, m['years']), MUTED, font=f_s)

    side = PANEL_W - 40
    r, c, h_init, h = evolve(8)
    rad, prof, hc, rn = profile(h, r, c)

    # --- a: the profiles ----------------------------------------------------
    x0 = PAD
    d.text((x0, TOP - 26), 'a.  the dome, before and after', INK, font=f_h)
    ax = _Ax(d, (x0 + 34, TOP, x0 + side + 34, TOP + side), (0.0, 700.0), (0.0, 3200.0))
    for t in (0, 1000, 2000, 3000):
        ax.hline(t, GRID)
        d.text((x0 + 30, ax.py(t)), '%d' % t, MUTED, font=f_s, anchor='rm')
    ax.line(rad / 1e3, h_init[c, c:], MUTED, 2)
    ax.line(rad / 1e3, prof, BLU, 3)
    ax.line(rad / 1e3, halfar(rad, hc, rn), RED, 2)
    d.text((x0 + 34, TOP + side + 8), 'radius, km        thickness, m', MUTED, font=f_s)
    d.text((x0 + 34, TOP + side + 26), 'grey t=0 · blue numeric · red exact', INK, font=f_b)

    # --- b: the self-similar collapse ---------------------------------------
    x0 = PAD + PANEL_W
    d.text((x0, TOP - 26), 'b.  self-similar collapse', GRN, font=f_h)
    bx = _Ax(d, (x0 + 34, TOP, x0 + side + 34, TOP + side), (0.0, 1.0), (0.0, 1.08))
    for t in (0.0, 0.5, 1.0):
        bx.hline(t, GRID)
        d.text((x0 + 30, bx.py(t)), '%.1f' % t, MUTED, font=f_s, anchor='rm')
    ss = np.linspace(0, 1, 200)
    bx.line(ss, halfar(ss, 1.0, 1.0), RED, 3)
    for st in STEPS:
        rr, cc, _hi, hh = evolve(st)
        ra, pr, hcc, rnn = profile(hh, rr, cc)
        keep = pr > 1.0
        bx.line(ra[keep] / rnn, pr[keep] / hcc, GRN, 1)
    d.text((x0 + 34, TOP + side + 8), 'r/R           H/H_c', MUTED, font=f_s)
    d.text((x0 + 34, TOP + side + 26), 'four times, one curve', GRN, font=f_b)

    # --- c: the residual ----------------------------------------------------
    x0 = PAD + 2 * PANEL_W
    d.text((x0, TOP - 26), 'c.  where the error lives', ACCENT, font=f_h)
    err, err_rad, err_curve = shape_residual(8)
    cx = _Ax(d, (x0 + 40, TOP, x0 + side + 40, TOP + side), (0.0, 0.72),
             (0.0, SHAPE_TOLERANCE * 1.15))
    for t in (0.0, 0.01, 0.02, 0.03):
        cx.hline(t, GRID)
        d.text((x0 + 36, cx.py(t)), '%.0f%%' % (t * 100), MUTED, font=f_s, anchor='rm')
    cx.hline(SHAPE_TOLERANCE, ACCENT, 2)
    d.text((x0 + 44, cx.py(SHAPE_TOLERANCE) + 3), 'suite bound, 3%', ACCENT, font=f_s)
    cx.line(err_rad / rn, err_curve, BLU, 2)
    # ⚠️ The x axis was unticked and the label read 'at the margin'. It is NOT the margin:
    # `shape_residual` masks to r < 0.7R, so the curve stops at the edge of the FIT WINDOW,
    # and the residual beyond it — where the SIA degenerates and the exact profile has an
    # infinite slope — is not drawn at all. An unticked axis let that read as the full radius.
    for t in (0.0, 0.35, 0.7):
        d.line([cx.px(t), TOP + side, cx.px(t), TOP + side + 4], fill=MUTED)
        d.text((cx.px(t), TOP + side + 6), '%.2f' % t, MUTED, font=f_s, anchor='ma')
    d.line([cx.px(0.7), TOP, cx.px(0.7), TOP + side], fill=ACCENT, width=1)
    d.text((x0 + 40, TOP + side + 24), 'r/R     |numeric − exact|', MUTED, font=f_s)
    d.text((x0 + 40, TOP + side + 42),
           'peak %.2f%% at the 0.7R window edge' % (100 * err), BLU, font=f_b)

    # --- d: the exponent, recovered -----------------------------------------
    x0 = PAD + 3 * PANEL_W
    d.text((x0, TOP - 26), 'd.  the exponent comes back', RED, font=f_h)
    dx = _Ax(d, (x0 + 40, TOP, x0 + side + 40, TOP + side), (0.0, 5.0), (0.38, 0.50))
    for t in (0.40, 0.4286, 0.46, 0.50):
        dx.hline(t, GRID if abs(t - P_SHAPE) > 1e-6 else RED,
                 1 if abs(t - P_SHAPE) > 1e-6 else 2)
        d.text((x0 + 36, dx.py(t)), '%.3f' % t, MUTED, font=f_s, anchor='rm')
    d.text((x0 + 44, dx.py(P_SHAPE) - 15), 'analytic 3/7', RED, font=f_b)
    for i, st in enumerate(STEPS):
        p = fitted_exponent(st)
        px_, py_ = dx.px(i + 1.0), dx.py(p)
        d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], fill=BLU)
        d.text((px_, TOP + side + 6), '%d' % st, MUTED, font=f_s, anchor='ma')
    d.text((x0 + 40, TOP + side + 24), 'steps of 200 model years', MUTED, font=f_s)
    d.text((x0 + 40, TOP + side + 42),
           'fitted %.4f vs 3/7 = %.4f' % (m['exponent'], P_SHAPE), RED, font=f_b)

    # --- e: the rate, which the four panels to the left cannot see -----------
    x0 = PAD + 4 * PANEL_W
    # ⚠️ THIS HEADING READ 'the rate, unfakeable'. It is unfakeable by a near-no-op, which is the
    # claim panels a–d cannot make; it is NOT unfakeable in general — a solver run at CFL 0.30
    # scores better on it than the shipped one (see RATE_TOLERANCE). Claim the thing that is true.
    d.text((x0, TOP - 26), 'e.  the rate shape cannot fake', GRN, font=f_h)
    ex = _Ax(d, (x0 + 44, TOP, x0 + side + 44, TOP + side), (0.0, 5.0), RATE_PANEL_YLIM)
    for t in (0.98, 0.99, 1.00, 1.01, 1.02):
        ex.hline(t, GRID if abs(t - 1.0) > 1e-9 else GRN, 1 if abs(t - 1.0) > 1e-9 else 2)
        d.text((x0 + 40, ex.py(t)), '%.2f' % t, MUTED, font=f_s, anchor='rm')
    # ⚠️ THE ACCEPTANCE BAND, DRAWN. Panel c draws its 3% bound and labels it; this panel used
    # to draw nothing, on a frame of ±3% while the bound it was illustrating was ±5% — the band
    # was WIDER than the whole panel, so the one panel with the loosest bound was the only one
    # that could not show it. `RATE_PANEL_YLIM` and `RATE_TOLERANCE` are now checked against
    # each other by tests/test_halfar_anatomy.py so they cannot drift apart again.
    for t in (1.0 - RATE_TOLERANCE, 1.0 + RATE_TOLERANCE):
        ex.hline(t, ACCENT, 2)
    # Labelled at the LOWER band line: the upper one runs through the 2-step marker, which sits
    # just outside the band because 400 model years give the thinning the least signal.
    d.text((x0 + 48, ex.py(1.0 - RATE_TOLERANCE) + 3),
           'suite bound, ±%.0f%% at 8 steps' % (100 * RATE_TOLERANCE), ACCENT, font=f_s)
    d.text((x0 + 48, ex.py(1.0) + 4), 'closed form', GRN, font=f_b)
    t0a = m['t0_analytic']
    for i, st in enumerate(STEPS):
        ratio = t0_from_thinning(st) / t0a
        px_, py_ = ex.px(i + 1.0), ex.py(ratio)
        d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], fill=BLU)
        d.text((px_, TOP + side + 6), '%d' % st, MUTED, font=f_s, anchor='ma')
    # ⚠️ THE X AXIS IS STEP COUNT, WHICH IS TOTAL MODEL TIME — `DT` is fixed, so more steps is a
    # LONGER RUN, not a finer one. The label was missing and the caption read the axis as a
    # timestep refinement; it is not one. 2 steps sits above the band because 400 model years
    # give the thinning almost no signal, not because a coarse step is inaccurate.
    d.text((x0 + 44, TOP + side + 24), 'steps of 200 model years — longer run →',
           MUTED, font=f_s)
    d.text((x0 + 44, TOP + side + 42), 't0 recovered / t0 closed form', MUTED, font=f_s)
    # The broken solver's point is 4406 — four orders of magnitude off the top of this axis.
    # Stating the number is the only honest way to draw it; a clipped marker would imply it
    # sits just above the frame.
    d.text((x0 + 44, TOP + side + 60), 'H^(n+1) lands at 4406 ↑', RED, font=f_b)

    cap = CAP_TOP
    for i, line in enumerate(caption_lines(m)):
        d.text((PAD, cap + i * CAP_LEADING), line, INK if i == 0 else MUTED, font=f_s)
    return img


CAP_TOP = TOP + PANEL_H + 34
CAP_LEADING = 17
CAP_MARGIN = 20


def caption_lines(m):
    """The caption, as a list, so the CANVAS can be sized from it.

    ⚠️ This is a list rather than a literal inside `build` for one reason: the height used to
    be the hand-tuned constant `TOP + PAD + PANEL_H + 196`, and it was 30 px short — it silently
    clipped the last line, the one carrying the volume result. A number that has to be re-tuned
    by hand every time a sentence is added will eventually not be. `build` now measures this
    list instead, and `tests/test_halfar_anatomy.py` asserts the last line lands inside the
    canvas, so the failure mode is a red row rather than a missing sentence.
    """
    return [
        'THIS IS THE ONLY FIGURE IN THIS SKILL THAT CHECKS A SOLVER AGAINST AN EXACT SOLUTION, and it is the top rung of VALIDATION.md\'s own',
        'evidence ladder — the rung that separates "the code solves its equation correctly" from "the equation is right". Halfar (1983), as',
        'standardised by Bueler et al. (2005) Test B: an isothermal dome on a flat bed with no mass balance spreads self-similarly as',
        'H = H_c·[1 − (r/R)^(4/3)]^(3/7) for Glen n = 3. ⚠️ NEITHER EXPONENT APPEARS IN THE SOLVER — 4/3 = (n+1)/n and 3/7 = n/(2n+1) are',
        'consequences of the analytic solution, while glacier_sia carries an H^(n+2) diffusivity and nothing else. Over %.0f model years the'
        % m['years'],
        'centre thins %.0f → %.0f m while the margin advances %.0f → %.0f km, the interior shape holds to %.2f%% against the suite\'s 3%% bound,'
        % (m['centre_initial'], m['centre_final'], m['radius_initial'] / 1e3,
           m['radius_final'] / 1e3, 100 * m['shape_error']),
        'and ice volume is conserved EXACTLY — the relative change is 0.0, not merely small. Panel d fits the shape exponent out of the'
        if m['volume_error'] == 0.0 else
        'and ice volume is conserved to %.1e relative. Panel d fits the shape exponent out of the' % m['volume_error'],
        'numerical profile and gets %.4f against the analytic %.4f.'
        % (m['exponent'], P_SHAPE),
        '',
        '⚠️ SHAPE IS NOT ENOUGH, and saying so is part of the figure. The initial condition IS the Halfar profile, so a solver that barely moves',
        'the ice still matches it — swapping the H^(n+2) diffusivity for H^(n+1) leaves every shape row above green and *lowers* the residual to',
        '0.49%. What a near-no-op cannot fake is the RATE — panel e. Halfar fixes it with no free parameters: t0 = (1/18)/Γ·(7/4)³·R0⁴/H0⁷ with',
        'Γ = 2A(ρg)ⁿ/(n+2), and H_c = H0(t/t0)^(−1/9), so t0 can be read back out of the thinning. Closed form %.3e s against %.3e s'
        % (m['t0_analytic'], m['t0_fitted']),
        'recovered from the run — %.2f%% apart, inside the ±%.0f%% band panel e now draws. Under H^(n+1) that recovery returns 4.06e13 s, ×4406.'
        % (100 * m['rate_error'], 100 * RATE_TOLERANCE),
        '⚠️ PANEL e\'S x AXIS IS RUN LENGTH, NOT STEP SIZE, and this caption used to say the opposite. DT is FIXED at 200 model years, so "more',
        'steps" is a LONGER RUN. The sequence %s at 2/4/8/16 steps is the SIGNAL growing — the denominator (H0/H_c)⁹ − 1'
        % ' / '.join('%.2f%%' % (100 * e) for e in m['rate_error_by_steps']),
        'grows with elapsed time — not discretisation error shrinking; carry it past 16 steps and it turns round again. Cut the REAL timestep at',
        'fixed total time, which is what the old sentence claimed, and the answer moves the WRONG way: %.4f%% → %.4f%% over dt/1…dt/16. The knob'
        % (100 * m['rate_error_dt_coarse'], 100 * m['rate_error_dt_fine']),
        'that does converge is the GRID, so that is the row the suite asserts, over six of them at a fixed 1440 km span: %s%% at'
        % ' / '.join('%.3f' % (100 * e) for e in m['rate_error_by_grid']),
        '%s cells — monotone. ⚠️ BUT NOT MONOTONE IN THE GRID GENERALLY, and the row must not be read as "finer is better": n=31 scores'
        % ' / '.join(str(n) for n, _cs in GRID_REFINEMENT),
        '%.3f%%, better than every rung of that ladder, and n=73 and n=145 — the grids where R0/cellsize is exactly 25 and 50 — dip below their'
        % (100 * m['rate_error_coarse_anomaly']),
        'neighbours too. A low rate error is not by itself evidence of a good discretisation.',
        '',
        '⚠️ AND THE ±%.0f%% BAND IS AGREEMENT, NOT CORRECTNESS. The %.3f%% above is a systematic bias, not noise, and CFL error CANCELS it: run the'
        % (100 * RATE_TOLERANCE, 100 * m['rate_error']),
        'same scheme at CFL 0.30 — half again past the 0.2 glacier_sia chose — and it scores %.3f%%, better than the shipped solver, with everything'
        % (100 * abs(m['rate_bias_over_cfl'])),
        'from 0.22 to 0.35 inside the band. The bias is monotone in CFL and changes SIGN at ~0.297; taking |·| turns that into a V. So the suite',
        'carries a second row that measures distance from the refined-timestep answer instead, where the shipped 0.2 scores %.3f%% and 0.30 scores'
        % (100 * m['cfl_distance_shipped']),
        '%.3f%% — no cancellation, and the timestep is policed where this band cannot police it.'
        % (100 * m['cfl_distance_over']),
        'Drawn from sims_illustrative.py, guarded by tests/test_halfar_anatomy.py.',
    ]


def canvas_height(m):
    """Tall enough for the caption it actually has, measured rather than remembered."""
    return CAP_TOP + len(caption_lines(m)) * CAP_LEADING + CAP_MARGIN


if __name__ == '__main__':
    build().save('halfar_anatomy.png')
    print('wrote halfar_anatomy.png')
