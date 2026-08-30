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
