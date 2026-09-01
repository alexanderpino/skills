"""Guard for `halfar_anatomy.py` — the SIA solver against Halfar's exact solution.

`test_benchmarks.py` already asserts the SIA reproduces the Halfar shape. This file guards the
FIGURE and, more importantly, the property that makes the benchmark worth anything:

⚠️ **THE EXACT SOLUTION'S EXPONENTS MUST NOT APPEAR IN THE SOLVER.** `4/3 = (n+1)/n` and
`3/7 = n/(2n+1)` are consequences of the analytic solution; `glacier_sia` carries an `H^(n+2)`
diffusivity and nothing else. The moment either constant leaks into the solver — through a
refactor that "shares" it, a helper imported for convenience, a default tidied into a module
constant — the benchmark stops being independent and becomes a restatement, while still passing
every numeric row.

The MIRROR of that claim — that the closed-form `t0_analytic` does not read its constants out of
the solver — used to be checked by scanning `halfar_anatomy.py`'s source text, and twice over
that scan was defeatable. It is now checked BEHAVIOURALLY: recompute `t0_analytic` with the
solver module replaced by a stub whose ice constants are wrong, and require the answer not to
move. See the block above `test_the_closed_form_time_does_not_move_when_the_solver_does`.
"""
import importlib.util
import re
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import pytest

import halfar_anatomy as HA
import sims_illustrative as sims

REF = Path(__file__).resolve().parents[1]


def test_the_solver_does_not_contain_the_analytic_exponents():
    """The independence claim, checked where it can actually be lost."""
    src = (REF / "sims_illustrative.py").read_text(encoding="utf-8")
    fn = src[src.index("def glacier_sia"):]
    fn = fn[:fn.index("\ndef ") if "\ndef " in fn else len(fn)]
    leaked = re.findall(r"3\s*/\s*7|3\.0\s*/\s*7|4\s*/\s*3|4\.0\s*/\s*3|0\.4286|1\.3333", fn)
    assert not leaked, (
        "the analytic exponents have leaked into glacier_sia (%s) — the Halfar comparison is no "
        "longer independent of the solver it checks" % leaked)


def test_ice_volume_is_conserved():
    """No mass balance means no ice may appear or vanish.

    ⚠️ THE BOUND IS 1e-12, NOT `== 0.0`, AND THE CHANGE IS DELIBERATE. The measured value IS
    0.0 — `glacier_sia` transports in divergence form, so the sum is conserved to the last bit
    on this input — and the figure's caption still says so, measured, at build time. But exact
    float equality is brittle in BOTH directions across numpy and BLAS versions: it can redden
    on a correct solver whose reduction order changed, and it says nothing extra about a wrong
    one. It says nothing about a wrong one because conservation here is VACUOUS AS EVIDENCE:
    `halfar_anatomy`'s own margin comment records that the `H^(n+1)` solver scores the same
    perfect 0.0. This row is a sanity check on the transport form, not a discriminator, and the
    rows that discriminate are the rate rows below.
    """
    err = HA.volume_error(8)
    assert err < 1e-12, (
        "volume changed by %.3e relative; with beta=0 divergence-form transport must conserve "
        "the sum to round-off" % err)


def test_the_memoised_arrays_cannot_be_written_through():
    """⚠️ `evolve` IS `lru_cache`D AND `profile` HANDS BACK VIEWS INTO WHAT IT RETURNS.

    Every row in this file, and every panel in the figure, reads the same three arrays out of
    one memoised eight-step run. A single write anywhere — a `-=` meant to be local, a
    normalisation done in place — would poison every consumer downstream of it in the same
    process, silently and only sometimes. The docstring said "read-only by convention" and the
    arrays were writeable; now the flag says it too, and this row is what keeps the two
    agreeing.
    """
    r, _c, h_init, h = HA.evolve(8)
    for name, arr in (("radius", r), ("h_init", h_init), ("h", h)):
        assert not arr.flags.writeable, (
            "evolve's %s array is writeable, so one stray in-place edit anywhere in this "
            "process silently rewrites the benchmark for every later row" % name)
    _rad, prof, _hc, _rn = HA.profile(h, r, _c)
    with pytest.raises(ValueError):
        prof[0] = 0.0


def test_the_dome_spreads_the_way_a_self_similar_solution_must():
    """Centre thins while the margin advances — the direction, not just the magnitude."""
    r, c, h_init, h = HA.evolve(8)
    _rad, _prof, hc, rn = HA.profile(h, r, c)
    assert hc < HA.H0, "the centre did not thin: %.1f -> %.1f" % (HA.H0, hc)
    assert rn > HA.R0, "the margin did not advance: %.0f -> %.0f" % (HA.R0, rn)


def test_the_interior_shape_holds_inside_the_suites_bound():
    err, _rad, _curve = HA.shape_residual(8)
    assert err < HA.SHAPE_TOLERANCE, (
        "interior shape error %.4f exceeds the %.2f bound" % (err, HA.SHAPE_TOLERANCE))


def test_the_error_grows_outward():
    """⚠️ WHERE the error lives is a claim panel c makes, so it is a claim to check.

    The SIA degenerates at the margin — the exact profile has an infinite surface slope there —
    so the residual must be largest at the outer edge of the fit window. A residual that peaked in
    the interior would mean something quite different and the panel's caption would be wrong.
    """
    _err, rad, curve = HA.shape_residual(8)
    order = np.argsort(rad)
    inner = curve[order][: len(order) // 3].mean()
    outer = curve[order][-len(order) // 3:].mean()
    assert outer > inner * 2.0, (
        "the residual should grow toward the margin: inner %.5f, outer %.5f" % (inner, outer))


@pytest.mark.parametrize("steps", HA.STEPS)
def test_the_fitted_exponent_recovers_three_sevenths(steps):
    """Fit the shape exponent out of the numerical profile; it must land on 3/7.

    This is the row that makes the whole figure evidence rather than illustration: the number it
    recovers exists nowhere in the code it is testing.
    """
    p = HA.fitted_exponent(steps)
    rel = abs(p - HA.P_SHAPE) / HA.P_SHAPE
    assert rel < 0.06, (
        "at %d steps the fitted exponent is %.4f against the analytic %.4f (%.1f%% off)"
        % (steps, p, HA.P_SHAPE, 100 * rel))


def test_the_spreading_RATE_matches_the_closed_form_not_just_the_shape():
    """⚠️ THE ROW THAT MAKES THE OTHER ROWS MEAN SOMETHING. Read this before touching them.

    Every shape row above is close to vacuous on its own, and the demonstration is short:
    change `H ** (n + 2)` to `H ** (n + 1)` in `glacier_sia` — one character — and all of
    them stay green. Worse, the interior residual *improves*, 0.0113 to 0.0049, and the
    fitted exponent stays inside its 6% band. The reason is structural: the initial condition
    IS the Halfar profile, so a solver that hardly moves the ice trivially still looks like
    Halfar. Shape agreement cannot distinguish "solves the equation" from "does almost
    nothing", and four of the rows in this file are shape rows.

    What a near-no-op cannot fake is the RATE. Halfar fixes it with no free parameters:
    `t0 = (1/18)/Gamma · (7/4)^3 · R0^4 / H0^7` with `Gamma = 2A(rho g)^n/(n+2)`, and
    `H_c(t) = H0 (t/t0)^(-1/9)`, so t0 can be read back out of the numerical thinning and
    the two must be the same number.

    Measured: analytic 9.221e9 s against a fitted 9.243e9 s, 0.23% apart, against a bound of
    1%. Under `H^(n+1)` the fitted t0 is 4.06e13, a factor of **4406** out. That is the
    discriminator this file was missing.

    ⚠️ THE BOUND WAS 0.05 AND THAT WAS 21x THE OBSERVED ERROR, which made this row decorative
    on everything short of the one-character diffusivity edit. `HA.RATE_TOLERANCE` now carries
    the derivation and the five solver mutations that used to walk past it;
    `test_the_rate_row_rejects_a_solver_run_above_its_own_CFL_limit` is the control that
    proves the tightened bound can still fail.
    """
    analytic = HA.t0_analytic()
    fitted = HA.t0_from_thinning(8)
    rel = abs(fitted / analytic - 1.0)
    assert rel < HA.RATE_TOLERANCE, (
        "the dome spreads at the wrong RATE: t0 fitted from the thinning is %.4e s against "
        "the closed-form %.4e s (%.1f%% off, bound %.0f%%). The shape rows cannot see this — "
        "check the diffusivity exponent in glacier_sia."
        % (fitted, analytic, 100 * rel, 100 * HA.RATE_TOLERANCE))


def test_the_CFL_transcription_still_matches_the_shipped_solver():
    """⚠️ THE ROWS BELOW ALL RUN A COPY OF THE SOLVER, AND A COPY ROTS SILENTLY.

    `glacier_sia` hard-codes its CFL factor, so `HA.sia_at_cfl` transcribes the transport loop
    to make that factor an argument. Nothing used to assert the transcription still matched the
    thing it was standing in for: if `glacier_sia` changed, every CFL row would go on "proving"
    bounds about a solver that no longer ships, and every one of them would stay green.

    Measured: at the shipped factor the two are BITWISE identical, max difference 0.000e+00.
    Bitwise is the right standard here — the transcription is the same arithmetic in the same
    order, so anything short of identical means the loops have genuinely diverged.
    """
    r, c = HA.radius_field()
    transcribed = HA.sia_at_cfl(HA.halfar(r, HA.H0, HA.R0), HA.CFL_SHIPPED)
    shipped = HA.evolve(8)[3]
    assert np.array_equal(transcribed, shipped), (
        "HA.sia_at_cfl at the shipped CFL %.2f no longer reproduces glacier_sia: max "
        "difference %.3e m over %d cells. Every CFL row below is now measuring a solver that "
        "does not ship — re-transcribe the loop before trusting any of them."
        % (HA.CFL_SHIPPED, float(np.abs(transcribed - shipped).max()), transcribed.size))


def test_the_rate_row_rejects_a_solver_run_above_its_own_CFL_limit():
    """⚠️ MUTATION CONTROL for `RATE_TOLERANCE`. The row above must be able to fail.

    `glacier_sia` subcycles its explicit diffusion at `0.2 * cellsize^2 / D_max`. Running the
    same scheme at 0.6 — three times the chosen factor — is precisely the defect a solver
    benchmark exists to catch, and at the old 5% bound it passed the entire file. Measured
    rate error at 8 steps: 0.0333 against the correct solver's 0.00233.

    The shape rows cannot see it either: the interior residual under CFL 0.6 is 0.0098,
    *better* than the correct solver's 0.0113, for the same reason every shape row here is
    near-vacuous. This row is the one that says no.

    ⚠️ AND 0.6 IS THE EASY CASE. It sits far out on the tail of the CFL sweep; the three rows
    below are about the part of that sweep where this bound is blind, which is most of it.
    """
    err = abs(HA.rate_bias_at_cfl(0.6))
    assert err > HA.RATE_TOLERANCE, (
        "a solver run at CFL 0.6 — three times the factor glacier_sia chose — now scores "
        "%.5f, inside the %.3f bound. The rate row has gone quiet and is no longer known to "
        "be able to fail." % (err, HA.RATE_TOLERANCE))


# --------------------------------------------------------------------------- #
# ⚠️ THE RATE ROW IS NOT MONOTONE IN THE DEFECT IT IS ADVERTISED AS POLICING.
#
# `RATE_TOLERANCE` was derived as ~4x the 0.00233 the correct solver scores, on the reading
# that 0.00233 was noise. It is not noise. It is a systematic discretisation bias, and the
# CFL error cancels against it — the signed sweep is monotone DECREASING and crosses zero at
# ~0.297, so |·| turns a monotone bias into a V with its floor at CFL 0.30. Consequences,
# all measured (`HA.rate_bias_at_cfl`, 8 steps, 121 cells):
#
#   * CFL 0.30 — half again past the solver's own stability factor — scores 0.00016, FIFTEEN
#     TIMES BETTER than the shipped solver, and passes.
#   * every factor from 0.22 to 0.35 passes; the row cannot police the timestep in that band.
#   * refining the timestep toward stability makes the score WORSE, not better (0.05 scores
#     0.00340 against 0.20's 0.00233).
#
# The naive repair — assert `rate_error(cfl=0.2) < rate_error(cfl=0.3)`, i.e. "the shipped
# factor is the best one" — FAILS TODAY, 0.00233 against 0.00016, because it is false. What is
# true, and is what the two rows below assert, is that the bias is monotone in CFL with a sign
# change, and that the distance from the REFINED-TIMESTEP answer — which has no spatial bias
# left in it to cancel against — is monotone with no sign change and separates 0.2 from 0.30
# cleanly. That second quantity bounds correctness where `RATE_TOLERANCE` bounds agreement.


def test_the_rate_bias_is_monotone_in_CFL_and_changes_sign_inside_the_band():
    """⚠️ A CHARACTERISATION ROW: it pins a DEFECT of the rate row, not a virtue.

    If this fails because the sign change has gone and the shipped CFL now minimises the error,
    that is good news and not a bug — but `RATE_TOLERANCE` was derived on the assumption that
    it is there, so re-derive that bound from the new sweep before deleting this row.
    """
    bias = [HA.rate_bias_at_cfl(cfl) for cfl in HA.CFL_SWEEP]
    assert bias == sorted(bias, reverse=True), (
        "the signed rate bias is no longer monotone in the CFL factor: %s at %s"
        % (["%+.5f" % b for b in bias], list(HA.CFL_SWEEP)))
    assert bias[0] > 0.0 > bias[-1], (
        "the rate bias no longer changes sign across the CFL sweep (%s at %s); the |·| that "
        "`rate_error` takes is what hid this, and RATE_TOLERANCE's derivation assumes it"
        % (["%+.5f" % b for b in bias], list(HA.CFL_SWEEP)))
    shipped, over = abs(HA.rate_bias_at_cfl(HA.CFL_SHIPPED)), abs(HA.rate_bias_at_cfl(0.30))
    assert over < shipped and over < HA.RATE_TOLERANCE, (
        "CFL 0.30 no longer beats the shipped %.2f on the rate row (%.5f against %.5f). That "
        "is an improvement, but RATE_TOLERANCE's 4x margin was justified against the old "
        "behaviour — re-derive it." % (HA.CFL_SHIPPED, over, shipped))


def test_the_timestep_is_policed_where_the_rate_row_cannot_police_it():
    """⚠️ THE ROW THAT BOUNDS CORRECTNESS RATHER THAN AGREEMENT.

    Distance from the same scheme run at `CFL_REFERENCE` (4x refined) removes the spatial bias
    the raw error cancels against, leaving the time-integration error alone. Measured at 8
    steps: 0.2 -> 0.00107, 0.30 -> 0.00355, 0.45 -> 0.03132, 0.6 -> 0.03666 — monotone, no sign
    change, and `CFL_CONSISTENCY_TOLERANCE = 0.002` separates the shipped factor from the first
    one the rate row is blind to.
    """
    dist = [HA.cfl_distance_from_refined_timestep(cfl) for cfl in HA.CFL_SWEEP[1:]]
    assert dist == sorted(dist), (
        "distance from the refined-timestep answer is no longer monotone in the CFL factor: "
        "%s at %s" % (["%.5f" % d for d in dist], list(HA.CFL_SWEEP[1:])))
    shipped = HA.cfl_distance_from_refined_timestep(HA.CFL_SHIPPED)
    assert shipped < HA.CFL_CONSISTENCY_TOLERANCE, (
        "the SHIPPED solver's recovered t0 now sits %.5f from its own refined-timestep answer, "
        "outside the %.4f bound. Either the timestep integration has got worse or the bound "
        "needs re-deriving from a fresh sweep." % (shipped, HA.CFL_CONSISTENCY_TOLERANCE))
    over = HA.cfl_distance_from_refined_timestep(0.30)
    assert over > HA.CFL_CONSISTENCY_TOLERANCE, (
        "⚠️ THE POSITIVE CONTROL FOR THIS ROW HAS GONE QUIET. CFL 0.30 is half again past the "
        "factor glacier_sia chose and passes the rate row outright (%.5f against a %.3f "
        "bound); this row is the only one that rejects it, and it now scores %.5f inside its "
        "own %.4f bound." % (abs(HA.rate_bias_at_cfl(0.30)), HA.RATE_TOLERANCE, over,
                             HA.CFL_CONSISTENCY_TOLERANCE))


def test_the_rate_error_falls_as_the_GRID_is_refined():
    """A single agreeing number could be a coincidence; a converging sequence could not.

    ⚠️ THIS ROW USED TO REFINE THE WRONG THING, and the figure repeated the mistake. It
    walked `HA.STEPS` and called that a falling timestep. `DT` is a fixed constant and
    `STEPS` multiplies TOTAL MODEL TIME — panel d's own axis says "steps of 200 model years"
    — so that sequence varies run LENGTH. It does fall (1.13 / 0.58 / 0.23 / 0.05% at
    2/4/8/16), but because the denominator `(H0/H_c)^9 - 1` grows with elapsed time: signal
    growth, i.e. dilution. It is not even convergent — carry it past 16 and it turns round
    (0.000459 / 0.000451 / 0.000854 / 0.000999 at 16/32/64/128).

    The GRID is the knob that actually moves this error, so the grid is what this asserts.

    ⚠️ AND IT ASSERTS IT OVER SIX GRIDS, NOT THREE, BECAUSE THREE POINTS ARE NOT A TREND. The
    ladder was (61, 121, 241) and monotonicity across three chosen points is nearly free. It is
    six now. ⚠️ What this row does NOT say — and what the row below exists to stop it being read
    as — is "finer is better": pointwise monotonicity in `n` is false for this solver, and
    `HA.GRID_REFINEMENT`'s comment carries the measured counterexamples. Adding a grid to the
    ladder without re-measuring will redden this.
    """
    assert len(HA.GRID_REFINEMENT) >= 5, (
        "the grid ladder is down to %d points; three of them was the defect this row was "
        "widened to fix" % len(HA.GRID_REFINEMENT))
    spans = {(n - 1) * cs for n, cs in HA.GRID_REFINEMENT}
    assert len(spans) == 1, (
        "the grid ladder no longer holds the domain span fixed (%s), so it is refining the "
        "domain as well as the resolution and the sequence means nothing" % sorted(spans))
    errs = [HA.rate_error(8, n, cs) for n, cs in HA.GRID_REFINEMENT]
    assert errs[-1] < errs[0], (
        "refining the grid does not improve the recovered t0: %s at %s"
        % (["%.5f" % e for e in errs], list(HA.GRID_REFINEMENT)))
    assert errs == sorted(errs, reverse=True), (
        "the grid-refinement sequence is not monotone: %s at %s"
        % (["%.5f" % e for e in errs], [n for n, _cs in HA.GRID_REFINEMENT]))


def test_a_low_rate_error_is_not_evidence_of_a_good_grid():
    """⚠️ THE COUNTERWEIGHT TO THE ROW ABOVE, AND ANOTHER CHARACTERISATION ROW.

    A monotone ladder invites the reading "a low rate error means a well-resolved run". It does
    not. At the same 1440 km span, n=31 — the coarsest grid that will hold the dome at all,
    48 km cells — scores 0.000532, better than every rung of the six-point ladder and better
    than n=321's 0.000975. The reason is the same cancellation the CFL rows above pin: the
    total error is a sum of biases that happen to oppose, and a coarse grid can land near the
    crossing by luck.

    Pinning it executably rather than in a comment does two things: it stops somebody
    "helpfully" extending `GRID_REFINEMENT` downward and reddening the monotone row for no
    reason, and it keeps the disclaimer from going stale silently. If this row fails because
    the anomaly is gone, re-measure the whole sweep before relaxing anything.
    """
    coarse = HA.rate_error(8, *HA.GRID_COARSE_ANOMALY)
    ladder = [HA.rate_error(8, n, cs) for n, cs in HA.GRID_REFINEMENT]
    assert coarse < min(ladder), (
        "n=%d no longer beats every rung of the refinement ladder (%.6f against a best of "
        "%.6f). The anomaly this row documents may be gone — good — but the ladder's "
        "monotonicity is then a claim about a different solver; re-measure before editing "
        "GRID_REFINEMENT's comment or this row."
        % (HA.GRID_COARSE_ANOMALY[0], coarse, min(ladder)))


def test_refining_the_TIMESTEP_is_not_what_moves_this_error():
    """The control that keeps the corrected caption honest, rather than merely reworded.

    The old caption said the recovery converged "as the timestep falls". Cut the real
    timestep with total model time held fixed and the error moves the OTHER way, monotonically
    (0.002327 → 0.002376 over dt/1…dt/16). If that ever stops being true the caption's
    correction is itself stale, and this row is what says so.
    """
    errs = [HA.rate_error_at_refined_timestep(k) for k in HA.TIMESTEP_REFINEMENT]
    assert errs[-1] > errs[0], (
        "refining the timestep at fixed total time now DOES reduce the rate error (%s) — the "
        "caption and the grid row above both need rewriting" % ["%.6f" % e for e in errs])


# --------------------------------------------------------------------------- #
# the independence of `t0_analytic`, checked BEHAVIOURALLY
#
# ⚠️ TWO GENERATIONS OF THIS GUARD READ SOURCE TEXT AND BOTH WERE DEFEATABLE. The record
# belongs here because the third attempt would have been another regex.
#
# v1 sliced `def t0_analytic` to the next `\ndef ` and asserted `"sims" not in` that slice.
# But `t0_analytic` takes every physical number it uses from module constants defined ABOVE
# it — A_GLEN, RHO_ICE, G_ACC, N_GLEN, H0, R0 — which the slice never saw.
#
# v2 walked module-level ASSIGNMENTS transitively from those six names and asserted
# `"sims" not in` the collected lines. Both halves of that are defeatable, and SIX one-line
# rewrites were measured walking straight past it — the six parametrised below. `def`,
# `class`, and any indented line are not assignment targets, so the walk simply stops at
# them; and `import sims_illustrative as _phys` puts the substring "sims" only on an import
# line, which is not an assignment and is never collected, so the text test has nothing to
# match on at all.
#
# THE FULL KILL, MEASURED. Change the solver's rho from 917 to 800 — a 13%-wrong ice density
# — and the rate row fires at 0.51229. Add the one-line import-alias evasion so RHO_ICE
# follows the solver, and the SAME solver scores 0.00414: the rate row passes inside its 0.01
# bound and v2's independence guard passes too. A benchmark wired to its own subject shipped
# green.
#
# SO THIS STOPS SCANNING TEXT. `t0_analytic` is recomputed with `sims_illustrative` replaced
# in `sys.modules` by a stub whose ice constants are all wrong, and the answer must not move.
# That is the property itself rather than a proxy for it, so it catches all six shapes and any
# seventh — including ones nobody has thought of, which is the entire point.

_ANCHOR = "N_GLEN = 3\nRHO_ICE, G_ACC = 917.0, 9.81"
_TOP_IMPORT = "import sims_illustrative as sims\n"

# ⚠️ TWO STUBS, NOT ONE, AND THE SECOND ONE IS NOT DECORATION. A single stub compares the
# recomputed t0 against `HA.t0_analytic()` — but if the SOLVER has also been mutated to the
# stub's density, the wired module already returns the wired answer and nothing moves. That
# collision was measured: rho 917->800 in the solver plus the import-alias evasion, against a
# stub that also used 800, and the guard passed. Two stubs that disagree about every constant
# cannot both collide, so the property is stated as "the answer is the same under both, and
# the same as the shipped one" and there is nothing left to coincide with.
STUB_CONSTANTS = (
    {"A": 1.0e-20, "n": 4, "rho": 800.0, "g": 5.0},
    {"A": 3.7e-19, "n": 5, "rho": 137.035999, "g": 1.61803399},
)


def _stub_solver_module(const):
    """A stand-in `sims_illustrative` whose every ice constant is wrong on purpose.

    Two ways to notice a read. `glacier_sia.__kwdefaults__` carries different numbers, so
    anything wired to them changes `t0_analytic`'s answer; and the module-level `__getattr__`
    turns a read of any OTHER solver attribute into a loud failure rather than an
    `AttributeError` somebody might mistake for an unrelated import problem.
    """
    mod = types.ModuleType("sims_illustrative")

    def glacier_sia(bed, H, steps, *, A=const["A"], n=const["n"], rho=const["rho"],
                    g=const["g"], dt=1.0, cellsize=1.0, ela=None, beta=0.0, b_max=1.0,
                    max_substeps=1):
        raise AssertionError(
            "the closed form RAN the solver; t0_analytic must be arithmetic on published "
            "constants, not a call into the code it is checking")

    def __getattr__(name):
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(
            "halfar_anatomy read sims_illustrative.%s while defining the closed form; the "
            "analytic side must not touch the solver module at all" % name)

    mod.glacier_sia = glacier_sia
    mod.__getattr__ = __getattr__
    return mod


def _t0_with_the_solver_stubbed(src, const, extra=(), name="halfar_under_a_stubbed_solver"):
    """Execute `src` as a fresh module with the solver stubbed, and return its `t0_analytic()`.

    A fresh module object rather than `importlib.reload(HA)` so the rest of the session keeps
    its warm `lru_cache`s and its real solver. `extra` is `[(filename, source)]` for evasions
    that route the constants through a second module of their own.

    ⚠️ EVERY ALREADY-IMPORTED MODULE FROM `reference-impl/` IS EVICTED FOR THE DURATION, and
    that is not tidiness. The laundering hop can be a second local module — `_ice_constants`
    importing the solver and re-exporting `rho` — and if that module is already in
    `sys.modules` holding the REAL constants, the fresh copy of `halfar_anatomy` imports the
    cached one and the stub never reaches it. Measured: without this eviction the
    helper-module evasion walked through the behavioural guard exactly as it walked through
    the text scan. `sys.modules` is restored to its exact snapshot afterwards.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for fname, text in extra:
            (tmp / fname).write_text(text, encoding="utf-8")
        path = tmp / (name + ".py")
        path.write_text(src, encoding="utf-8")
        snapshot = dict(sys.modules)
        for modname, module in list(sys.modules.items()):
            f = getattr(module, "__file__", None)
            if f and Path(f).resolve().parent == REF:
                del sys.modules[modname]
        sys.modules["sims_illustrative"] = _stub_solver_module(const)
        sys.path.insert(0, str(tmp))
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return float(mod.t0_analytic())
        finally:
            sys.path.remove(str(tmp))
            for modname in [k for k in sys.modules if k not in snapshot]:
                del sys.modules[modname]
            sys.modules.update(snapshot)


# The six evasion shapes, as (id, prelude inserted after the solver import, replacement for
# `_ANCHOR`, extra modules). Every one of them was measured passing the deleted text scan;
# every one of them changes `t0_analytic`'s answer, which is why the behavioural guard sees
# them. They are not exotic — each is the tidy version of "keep the constants in sync".
_HELPER_MODULE = ("import sims_illustrative\n\n"
                  "RHO = sims_illustrative.glacier_sia.__kwdefaults__['rho']\n")

EVASIONS = (
    ("a-function-call", "",
     "def _rho_from_solver():\n"
     "    return sims.glacier_sia.__kwdefaults__['rho']\n\n\n"
     "N_GLEN = 3\nRHO_ICE, G_ACC = _rho_from_solver(), 9.81", ()),
    ("an-import-alias", "import sims_illustrative as _phys\n",
     "N_GLEN = 3\nRHO_ICE, G_ACC = _phys.glacier_sia.__kwdefaults__['rho'], 9.81", ()),
    ("a-class-attribute", "",
     "class _Phys(object):\n"
     "    rho = sims.glacier_sia.__kwdefaults__['rho']\n\n\n"
     "N_GLEN = 3\nRHO_ICE, G_ACC = _Phys.rho, 9.81", ()),
    ("a-try-except-rebind", "",
     "N_GLEN = 3\nRHO_ICE, G_ACC = 917.0, 9.81\n"
     "try:\n"
     "    RHO_ICE = sims.glacier_sia.__kwdefaults__['rho']\n"
     "except Exception:\n"
     "    pass", ()),
    ("getattr-on-an-alias", "import sims_illustrative as _phys\n",
     "_KW = getattr(_phys, 'glacier_sia').__kwdefaults__\n"
     "N_GLEN = 3\nRHO_ICE, G_ACC = _KW['rho'], _KW['g']", ()),
    ("a-second-helper-module", "import _ice_constants as _ic\n",
     "N_GLEN = 3\nRHO_ICE, G_ACC = _ic.RHO, 9.81",
     (("_ice_constants.py", _HELPER_MODULE),)),
)


def _halfar_source():
    return (REF / "halfar_anatomy.py").read_text(encoding="utf-8")


def test_the_closed_form_time_does_not_move_when_the_solver_does():
    """`t0_analytic` must be written from the paper, exactly like the 4/3 and 3/7 above.

    `Gamma` legitimately contains `n + 2`, which is also the solver's diffusivity exponent.
    That coincidence is the opening for the same independence failure this file's first test
    guards: importing the constant "to keep them in sync" would make the rate check a
    restatement of the solver instead of a check on it.

    Checked by swapping the whole solver module for two different stubs — each with a wrong
    density, a wrong `g`, a wrong Glen exponent and a wrong `A`, disagreeing with each other
    about all four — and requiring the closed form to return the same number under both, and
    the same as the shipped module returns. Nothing about HOW the constants are written
    matters; only whether the answer depends on the code it is being compared against.
    """
    src = _halfar_source()
    stubbed = [_t0_with_the_solver_stubbed(src, const) for const in STUB_CONSTANTS]
    real = HA.t0_analytic()
    for const, got in zip(STUB_CONSTANTS, stubbed):
        assert abs(got / real - 1.0) < 1e-12, (
            "t0_analytic moved from %.6e to %.6e when the solver module was replaced by a "
            "stub with rho=%.4f, g=%.4f, n=%d. The closed form is reading its numbers out of "
            "the code it is supposed to be an independent check on, so the rate comparison is "
            "a restatement." % (real, got, const["rho"], const["g"], const["n"]))


@pytest.mark.parametrize("shape,prelude,replacement,extra", EVASIONS,
                         ids=[e[0] for e in EVASIONS])
def test_the_independence_guard_rejects_constants_read_from_the_solver(
        shape, prelude, replacement, extra):
    """⚠️ POSITIVE CONTROL, PARAMETRISED OVER ALL SIX SHAPES THE TEXT SCAN MISSED.

    A guard never seen to fail is not known to be a guard, and the previous single, un-
    parametrised control is exactly how a guard ends up proof against one shape and blind to
    the rest — the commit that added it claimed "caught in four variants now" while shipping
    one. Each parameter here rebuilds "keep the ice constants in sync with the solver" in a
    different idiom, in an in-memory copy of `halfar_anatomy.py`, and asserts the closed form
    then MOVES when the solver's constants move — which is what the row above forbids.
    """
    src = _halfar_source()
    assert _TOP_IMPORT in src and _ANCHOR in src, (
        "the controls can no longer find the import line or the constants they patch, so they "
        "are not testing anything — re-pin them to however the solver import, RHO_ICE and "
        "G_ACC are now written")
    patched = src.replace(_TOP_IMPORT, _TOP_IMPORT + prelude, 1).replace(
        _ANCHOR, replacement, 1)
    a, b = [_t0_with_the_solver_stubbed(patched, const, extra) for const in STUB_CONSTANTS]
    assert abs(a / b - 1.0) > 1e-6, (
        "the independence guard does not notice the ice constants being read out of the "
        "solver via %s: t0_analytic returned the same %.6e under two stubs that disagree "
        "about every ice constant, so the guard would pass a benchmark wired to its own "
        "subject." % (shape, a))


# --------------------------------------------------------------------------- #
# THE TWO AXES HALFAR TEST B CANNOT REACH
#
# ⚠️ THE PROBLEM THESE TWO ROWS CLOSE. Test B is legitimately defined at `beta = 0` on a FLAT
# bed, so every row above runs `glacier_sia` with the mass-balance branch switched off and the
# bed identically zero. That leaves two whole axes of the solver untouched while this file
# presents itself as the solver's validation, and the survivors are not subtle: 16 of 23
# mutations of `glacier_sia` survive every numeric row here, seven of them BITWISE.
#
# The worst is the bed. `s = bed + H` with `bed` all zeros IS `H`, so deleting the bed
# entirely — which deletes the SIA's defining property, that ice flows down the SURFACE
# gradient rather than the thickness gradient — changes not one bit of any run in this file.
# On a 2% tilted bed the two versions differ by 108682 m of ice summed over the grid.
#
# Both rows below are cheap (a 41-cell grid and a five-cell one), and both are mutation-proved:
# bed deleted from the transport, bed deleted from the mass balance, the mass-balance branch
# deleted, its sign flipped, its `b_max` clip removed, and its `H >= 0` clamp removed are all
# caught. They belong in this file because this is the file that claims to validate the solver.


def test_the_ice_flows_down_the_SURFACE_gradient_not_the_thickness_gradient():
    """⚠️ THE SIA'S DEFINING PROPERTY, AND NOTHING ELSE HERE TESTS IT.

    Halfar Test B puts the dome on a flat bed, where `bed + H` and `H` are the same field, so
    every other row in this file scores identically against a solver that ignores the bed
    outright. Tilt the bed and the two must part company: the same dome on a 2% slope has to
    flow downhill, and a thickness-gradient solver does not know the slope is there.

    Measured with the shipped solver: 108682.2304 m of ice summed over the grid separates the
    tilted run from the flat one, 364.07 m in the worst cell. Under `s = bed + H` -> `s = H`
    the two runs are BITWISE identical and this row is the only thing in the file that fires.
    """
    n, cellsize = 41, 4000.0
    c = (n - 1) // 2
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    rr = np.hypot(xx - c, yy - c) * cellsize
    dome = 800.0 * np.maximum(1.0 - (rr / (0.3 * n * cellsize)) ** 2, 0.0)
    run = dict(steps=3, A=HA.A_GLEN, dt=3.0e10, cellsize=cellsize, beta=0.0,
               max_substeps=4000)
    flat = sims.glacier_sia(np.zeros((n, n)), dome, **run)
    tilted = sims.glacier_sia(0.02 * xx * cellsize, dome, **run)
    spread = float(np.abs(tilted - flat).sum())
    assert spread > 1.0e4, (
        "the same dome on a 2%% tilted bed evolves to within %.4f m (summed) of the flat-bed "
        "run, so the bed is not entering the flow. `glacier_sia` diffuses the ICE SURFACE, "
        "`bed + H`; a solver diffusing H alone passes every other row in this file because "
        "Test B's bed is identically zero." % spread)


def test_the_mass_balance_accumulates_above_the_ELA_melts_below_and_clips_at_b_max():
    """The other axis Test B switches off — and four mutations live in it.

    `A=0.0` kills the diffusivity, so transport contributes nothing and this row sees the mass
    balance alone. Five columns straddle the ELA. Measured with the shipped solver, from a
    uniform 100 m of ice: `[0, 80, 100, 120, 150]`, which pins four separate claims at once —
    ice grows above the ELA, shrinks below it, is left alone at it, is clamped at zero instead
    of going negative, and gains `b_max * dt` rather than `beta * (s - ela) * dt` where the
    latter would be far larger.

    Mutation-proved: branch deleted -> all 100; sign flipped -> [150, 120, 100, 80, 0];
    `b_max` clip removed -> last cell 900; `H >= 0` clamp removed -> first cell -100; bed
    dropped from `s` -> all 0.
    """
    bed = np.array([[0.0, 900.0, 1000.0, 1100.0, 5000.0]] * 3)
    h = np.full_like(bed, 100.0)
    beta, ela, b_max, dt = 0.02, 1100.0, 5.0, 10.0
    out = sims.glacier_sia(bed, h, steps=1, A=0.0, dt=dt, cellsize=1000.0,
                           ela=ela, beta=beta, b_max=b_max, max_substeps=10)
    got = [float(v) for v in out[1]]
    below_far, below, at, above, way_above = got
    assert at == 100.0, (
        "a column exactly at the ELA gained or lost ice (%.4f): the mass balance is not "
        "b = beta * (surface - ela)" % at)
    assert above > 100.0, (
        "ice ABOVE the ELA (surface %.0f, ela %.0f) did not accumulate: %.4f -> %.4f. The "
        "mass-balance branch is missing or its sign is inverted."
        % (bed[0][3] + 100.0, ela, 100.0, above))
    assert below < 100.0, (
        "ice BELOW the ELA did not melt: %.4f -> %.4f" % (100.0, below))
    assert below_far == 0.0, (
        "a column melting past its own thickness went to %.4f rather than being clamped at "
        "zero; `H` must stay >= 0" % below_far)
    unclipped = 100.0 + beta * (bed[0][4] + 100.0 - ela) * dt
    assert way_above == 100.0 + b_max * dt < unclipped, (
        "a column %.0f m above the ELA gained %.4f m rather than the b_max * dt = %.1f it is "
        "capped at (uncapped it would reach %.1f); the b_max clip is gone"
        % (bed[0][4] + 100.0 - ela, way_above - 100.0, b_max * dt, unclipped))


def test_profiles_at_different_times_collapse_onto_one_curve():
    """Self-similarity is the claim panel b draws, so it is measured rather than eyeballed."""
    worst = 0.0
    for steps in HA.STEPS:
        r, c, _h0, h = HA.evolve(steps)
        rad, prof, hc, rn = HA.profile(h, r, c)
        m = (rad > 0) & (rad < 0.7 * rn)
        worst = max(worst, float(np.abs(prof[m] / hc - HA.halfar(rad[m], 1.0, rn)).max()))
    assert worst < HA.SHAPE_TOLERANCE, (
        "the normalised profiles do not collapse: worst deviation %.4f" % worst)


def test_panel_e_can_show_the_bound_it_is_drawn_to_illustrate():
    """⚠️ THE AXIS AND THE BOUND MUST NOT DRIFT APART, AND THEY HAD.

    Panel e was drawn on (0.97, 1.03) while `RATE_TOLERANCE` was 0.05, so the acceptance band
    was WIDER THAN THE WHOLE PANEL and could not be drawn inside it — the one panel with the
    loosest bound was the only one not showing it, while panel c drew and labelled its 3%.
    With the bound at 1% the band fits, `build` draws it, and this row keeps either number
    from moving without the other.
    """
    lo, hi = HA.RATE_PANEL_YLIM
    assert lo <= 1.0 - HA.RATE_TOLERANCE and 1.0 + HA.RATE_TOLERANCE <= hi, (
        "panel e is drawn on %s but its acceptance band is %.3f-%.3f — the band does not fit "
        "inside the frame that is supposed to display it"
        % (HA.RATE_PANEL_YLIM, 1.0 - HA.RATE_TOLERANCE, 1.0 + HA.RATE_TOLERANCE))


def test_figure_builds():
    pytest.importorskip("PIL", reason="the anatomy figures need Pillow")
    img = HA.build()
    assert img.size[0] == HA.PAD * 2 + HA.COLS * HA.PANEL_W
    assert img.size[1] > HA.TOP + HA.PANEL_H


def test_the_whole_caption_fits_on_the_canvas():
    """⚠️ This exact failure has already happened once, silently.

    The canvas height was a hand-tuned constant and the caption grew past it, clipping the
    last line — the one carrying the volume result. Nothing failed; the figure simply said
    less than it claimed to. `canvas_height` is now measured from `caption_lines`, and this
    row is what keeps the two from drifting apart again.
    """
    m = HA.measurements()
    lines = HA.caption_lines(m)
    bottom = HA.CAP_TOP + len(lines) * HA.CAP_LEADING
    assert bottom <= HA.canvas_height(m), (
        "the caption's %d lines end at y=%d on a canvas %d tall — the last %d line(s) are "
        "clipped" % (len(lines), bottom, HA.canvas_height(m),
                     1 + (bottom - HA.canvas_height(m)) // HA.CAP_LEADING))


def test_no_caption_line_runs_off_the_right_edge():
    """The sibling of the row above, for the axis it does not cover.

    `canvas_height` measures the caption's height; nothing measured its WIDTH, and the caption
    grew again to carry the CFL and grid-anomaly results. A line wider than the canvas is
    clipped exactly as silently as one below its bottom edge. Widest line today: 1059 px of
    1526 available.
    """
    pytest.importorskip("PIL", reason="measuring text width needs Pillow")
    font = HA._font(13)
    width = HA.PAD * 2 + HA.COLS * HA.PANEL_W
    for line in HA.caption_lines(HA.measurements()):
        if not line:
            continue
        right = HA.PAD + font.getbbox(line)[2]
        assert right <= width, (
            "a caption line runs to x=%d on a %d px canvas and is clipped: %r"
            % (right, width, line))


def test_the_caption_states_the_rate_result_not_only_the_shape():
    """The figure's strongest claim must be *in* the figure, not only in this file.

    A reader takes the caption as the summary. If the caption reports only the shape
    agreement, the figure oversells itself by exactly the amount the shape rows are vacuous.
    """
    m = HA.measurements()
    text = " ".join(HA.caption_lines(m))
    assert "RATE" in text, "the caption never mentions the rate check"
    assert "t0" in text, "the caption never names the characteristic time it compares"
    assert "%.3e" % m["t0_analytic"] in text, (
        "the caption does not quote the closed-form t0 it claims to compare against")


def test_the_caption_does_not_call_the_step_sweep_a_timestep_refinement():
    """⚠️ THE PUBLISHED FIGURE CARRIED A FALSE CLAIM, AND THIS IS WHAT STOPS IT COMING BACK.

    The caption read "converging as the timestep falls". `DT` is fixed; more steps is more
    model time. Refining the actual timestep moves the error the other way, and the step
    sequence is not convergent past 16 anyway. The phrase is banned rather than merely
    corrected, because it is the natural thing to write again.
    """
    text = " ".join(HA.caption_lines(HA.measurements()))
    for banned in ("as the timestep falls", "as the time step falls",
                   "converging as the timestep", "timestep refinement"):
        assert banned not in text.lower(), (
            "the caption is back to describing the step-count sweep as a timestep "
            "refinement (%r); it is a RUN-LENGTH sweep" % banned)
    assert "RUN LENGTH" in text or "LONGER RUN" in text, (
        "the caption no longer says what panel e's x axis actually varies")
