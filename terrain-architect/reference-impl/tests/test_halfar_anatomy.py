"""Guard for `halfar_anatomy.py` — the SIA solver against Halfar's exact solution.

`test_benchmarks.py` already asserts the SIA reproduces the Halfar shape. This file guards the
FIGURE and, more importantly, the property that makes the benchmark worth anything:

⚠️ **THE EXACT SOLUTION'S EXPONENTS MUST NOT APPEAR IN THE SOLVER.** `4/3 = (n+1)/n` and
`3/7 = n/(2n+1)` are consequences of the analytic solution; `glacier_sia` carries an `H^(n+2)`
diffusivity and nothing else. The moment either constant leaks into the solver — through a
refactor that "shares" it, a helper imported for convenience, a default tidied into a module
constant — the benchmark stops being independent and becomes a restatement, while still passing
every numeric row. That failure is invisible to any check on the RESULT, so it needs a check on
the SOURCE.
"""
import re
from pathlib import Path

import numpy as np
import pytest

import halfar_anatomy as HA

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


def test_ice_volume_is_conserved_exactly():
    """No mass balance means no ice may appear or vanish. The claim is exactness."""
    err = HA.volume_error(8)
    assert err == 0.0, (
        "volume changed by %.3e relative; with beta=0 this must be identically zero" % err)


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

    Measured: analytic 9.221e9 s against a fitted 9.243e9 s, 0.23% apart, and the fit
    converges toward the closed form as the step count rises (9.326e9 / 9.275e9 / 9.243e9 /
    9.226e9 at 2/4/8/16 steps) — which is what discretisation error is supposed to do.
    Under `H^(n+1)` the fitted t0 is 4.06e13, a factor of **4405** out. That is the
    discriminator this file was missing.
    """
    analytic = HA.t0_analytic()
    fitted = HA.t0_from_thinning(8)
    rel = abs(fitted / analytic - 1.0)
    assert rel < HA.RATE_TOLERANCE, (
        "the dome spreads at the wrong RATE: t0 fitted from the thinning is %.4e s against "
        "the closed-form %.4e s (%.1f%% off, bound %.0f%%). The shape rows cannot see this — "
        "check the diffusivity exponent in glacier_sia."
        % (fitted, analytic, 100 * rel, 100 * HA.RATE_TOLERANCE))


def test_the_recovered_rate_converges_as_the_step_count_rises():
    """A single agreeing number could be a coincidence; a converging sequence could not.

    Halving the timestep must move the fitted t0 toward the closed form, not away. This is
    the difference between "the answer is right" and "the answer is right for a reason".
    """
    errs = [abs(HA.t0_from_thinning(s) / HA.t0_analytic() - 1.0) for s in HA.STEPS]
    assert errs[-1] < errs[0], (
        "the fitted t0 does not converge on the closed form with more steps: %s"
        % ["%.4f" % e for e in errs])


def test_the_closed_form_time_is_not_read_out_of_the_solver():
    """`t0_analytic` must be written from the paper, exactly like the 4/3 and 3/7 above.

    `Gamma` legitimately contains `n + 2`, which is also the solver's diffusivity exponent.
    That coincidence is the opening for the same independence failure this file's first test
    guards: importing the constant "to keep them in sync" would make the rate check a
    restatement of the solver instead of a check on it.
    """
    src = (REF / "halfar_anatomy.py").read_text(encoding="utf-8")
    fn = src[src.index("def t0_analytic"):]
    fn = fn[:fn.index("\ndef ")]
    assert "sims" not in fn, (
        "t0_analytic reads from the solver module; the rate comparison is no longer "
        "independent of the code it checks")


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
