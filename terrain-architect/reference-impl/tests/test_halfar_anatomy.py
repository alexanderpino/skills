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


def _sia_at_cfl(h_init, cfl, steps=8):
    """`glacier_sia`'s transport loop, transcribed, with the CFL factor made an argument.

    A local copy rather than a monkeypatch because the point is to run a solver that is wrong
    in one specific, plausible way — the explicit diffusion pushed past the stability factor
    the shipped code chose — without touching the shipped code. Everything else here matches
    `sims_illustrative.glacier_sia` line for line at `beta=0`.
    """
    n_glen, rho, g = 3, 917.0, 9.81
    c = 2.0 * HA.A_GLEN / (n_glen + 2) * (rho * g) ** n_glen
    h = np.array(h_init, dtype=np.float64, copy=True)
    cs = HA.CELLSIZE
    for _ in range(int(steps)):
        remaining, subs = HA.DT, 0
        while remaining > 1e-6 * HA.DT and subs < 4000:
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


def test_the_rate_row_rejects_a_solver_run_above_its_own_CFL_limit():
    """⚠️ MUTATION CONTROL for `RATE_TOLERANCE`. The row above must be able to fail.

    `glacier_sia` subcycles its explicit diffusion at `0.2 * cellsize^2 / D_max`. Running the
    same scheme at 0.6 — three times the chosen factor — is precisely the defect a solver
    benchmark exists to catch, and at the old 5% bound it passed the entire file. Measured
    rate error at 8 steps: 0.0333 against the correct solver's 0.00233.

    The shape rows cannot see it either: the interior residual under CFL 0.6 is 0.0098,
    *better* than the correct solver's 0.0113, for the same reason every shape row here is
    near-vacuous. This row is the one that says no.
    """
    r, c = HA.radius_field()
    h = _sia_at_cfl(HA.halfar(r, HA.H0, HA.R0), 0.6)
    fitted = 8 * HA.DT / ((HA.H0 / float(h[c, c])) ** 9.0 - 1.0)
    err = abs(fitted / HA.t0_analytic() - 1.0)
    assert err > HA.RATE_TOLERANCE, (
        "a solver run at CFL 0.6 — three times the factor glacier_sia chose — now scores "
        "%.5f, inside the %.3f bound. The rate row has gone quiet and is no longer known to "
        "be able to fail." % (err, HA.RATE_TOLERANCE))


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
    """
    errs = [HA.rate_error(8, n, cs) for n, cs in HA.GRID_REFINEMENT]
    assert errs[-1] < errs[0], (
        "refining the grid does not improve the recovered t0: %s at %s"
        % (["%.5f" % e for e in errs], list(HA.GRID_REFINEMENT)))
    assert errs == sorted(errs, reverse=True), (
        "the grid-refinement sequence is not monotone: %s" % ["%.5f" % e for e in errs])


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
# the independence of `t0_analytic`, scanned where it can actually be lost
#
# ⚠️ THE PREVIOUS VERSION OF THIS GUARD WAS THEATRE, AND THE RECORD BELONGS HERE. It sliced
# `def t0_analytic` to the next `\ndef ` and asserted `"sims" not in` that slice. But
# `t0_analytic` takes every physical number it uses from module constants defined ABOVE it —
# A_GLEN, RHO_ICE, G_ACC, N_GLEN, H0, R0 — which the slice never saw. Rewriting those six to
# read `sims.glacier_sia.__kwdefaults__` left all sixteen rows green; changing the solver's
# rho from 917 to 800 on top of that (a mutation that normally reddens the rate row at ratio
# 1.512) ALSO left sixteen green, because the "analytic" side had been wired to follow it.
# The guard existed to stop exactly that and could not fire.
#
# The scan now covers the constants as well as the function, and `test_..._rejects_constants_
# read_from_the_solver` below is the positive control that proves it can fail.

T0_DEPENDENCIES = ("A_GLEN", "RHO_ICE", "G_ACC", "N_GLEN", "H0", "R0")


_ASSIGN = re.compile(r"^([A-Za-z0-9_,\s]+?)=(?!=)")


def _module_assignments(src):
    """`name -> [the module-level lines that assign it]`, tuple targets included."""
    out = {}
    for ln in src.splitlines():
        if not ln or ln[0].isspace() or ln.lstrip().startswith("#"):
            continue                                   # indented, blank or comment
        m = _ASSIGN.match(ln)
        if not m:
            continue
        targets = [t.strip() for t in m.group(1).split(",")]
        if not targets or not all(t.isidentifier() for t in targets):
            continue                                   # `def f(a=1):`, calls, etc.
        for t in targets:
            out.setdefault(t, []).append(ln)
    return out


def _t0_independence_scan(src):
    """The source `t0_analytic`'s answer actually depends on: the function AND its constants.

    ⚠️ TRANSITIVELY, and the positive control below is why. A first version scanned only the
    lines assigning the six named constants, and the control — which routes them through an
    intermediate `_KW = sims.glacier_sia.__kwdefaults__` — walked straight past it. One hop of
    indirection is the obvious shape of the refactor this guard exists to catch, so the scan
    follows every module-level name a dependency's right-hand side mentions, to closure.

    Returns the concatenated text. Raises if a dependency has no module-level assignment at
    all, so renaming a constant fails loudly instead of quietly emptying the guard.
    """
    assigns = _module_assignments(src)
    for name in T0_DEPENDENCIES:
        assert name in assigns, (
            "the independence scan cannot find where %s is defined, so it is no longer "
            "scanning it — a renamed constant must not silently shrink this guard" % name)
    pending, seen, picked = list(T0_DEPENDENCIES), set(), []
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        for ln in assigns[name]:
            picked.append(ln)
            for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ln.split("=", 1)[1]):
                if ident in assigns and ident not in seen:
                    pending.append(ident)
    fn = src[src.index("def t0_analytic"):]
    picked.append(fn[:fn.index("\ndef ") if "\ndef " in fn else len(fn)])
    return "\n".join(dict.fromkeys(picked))


def test_the_closed_form_time_is_not_read_out_of_the_solver():
    """`t0_analytic` must be written from the paper, exactly like the 4/3 and 3/7 above.

    `Gamma` legitimately contains `n + 2`, which is also the solver's diffusivity exponent.
    That coincidence is the opening for the same independence failure this file's first test
    guards: importing the constant "to keep them in sync" would make the rate check a
    restatement of the solver instead of a check on it.

    The scan covers the six constants the closed form reads as well as the body that reads
    them, because the body alone is not where this can be lost.
    """
    src = (REF / "halfar_anatomy.py").read_text(encoding="utf-8")
    scanned = _t0_independence_scan(src)
    assert "sims" not in scanned, (
        "t0_analytic, or a constant it reads, comes from the solver module; the rate "
        "comparison is no longer independent of the code it checks:\n%s"
        % "\n".join(ln for ln in scanned.splitlines() if "sims" in ln))


def test_the_independence_guard_rejects_constants_read_from_the_solver():
    """⚠️ POSITIVE CONTROL. A guard never seen to fail is not known to be a guard.

    This rebuilds the exact refactor the row above exists to stop — the ice constants
    "kept in sync" by reading `sims.glacier_sia.__kwdefaults__` — in an in-memory copy of
    the source, and asserts the scan rejects it. The old body-only scan passed this.
    """
    src = (REF / "halfar_anatomy.py").read_text(encoding="utf-8")
    patched = src.replace(
        "N_GLEN = 3\nRHO_ICE, G_ACC = 917.0, 9.81",
        "_KW = sims.glacier_sia.__kwdefaults__\n"
        "N_GLEN = _KW['n']\nRHO_ICE, G_ACC = _KW['rho'], _KW['g']")
    assert patched != src, (
        "the control can no longer find the constants it patches, so it is not testing "
        "anything — re-pin it to however RHO_ICE and G_ACC are now written")
    scanned = _t0_independence_scan(patched)
    assert "sims" in scanned, (
        "the independence scan does not see constants rewritten to read out of the solver; "
        "it is scanning the wrong text and would pass a benchmark wired to its own subject")


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
