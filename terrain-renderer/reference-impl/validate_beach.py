"""External validation of the beach scene -- bathymetry, wave transform, bar.

    python3 validate_beach.py            # exits non-zero on any FAIL
    python3 validate_beach.py -v         # also prints every tolerance's reason
    python3 validate_beach.py --bugs     # re-runs the whole suite once per
                                         # deliberately reintroduced bug and
                                         # prints which rows caught each one
    python3 validate_beach.py --bug NAME # one of them, verbosely

WHY THIS FILE EXISTS, and it is the same argument `validate.py` makes for the
pool: `beach.py` prints a page of diagnostics and almost all of them check the
implementation against itself. This file checks it against things that were not
written here.

THE THREE TIERS are the pool's, and the tier is the strength of the evidence:

  Tier 1  CLOSED FORM.        The answer is known analytically; a disagreement
                              is a bug in one of the two.
  Tier 2  PUBLISHED.          Compared against a citation. A disagreement may be
                              a bug, a different beach, or a different fit.
  Tier 3  INDEPENDENT METHOD. A second estimate computed a different way -- a
                              ray trace against a 1-D march, one solver against
                              another, a refined grid against a coarse one.

THE HARDEST-WON RULE IN THIS PROJECT, restated because this file is new and the
mistake is cheap to repeat: TWO ROUTES TO A NUMBER MUST NOT SHARE A SOURCE. The
pool installed a wrong constant twice because its two "independent methods" had
both been transcribed from the same comment. Every tier-3 row below names where
its second route came from, and where the second route is an equation, that
equation came from a document read this wave -- not from the module it checks.

AND EVERY GUARD IS FIRED AT THE BUG IT WAS WRITTEN FOR. `--bugs` puts eight
defects back, one at a time, and prints the rows that fail for each. A guard
that does not fire on its own bug is a comment with a check() around it.
"""
import math
import sys
import time

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

import beach as BCH                                             # noqa: E402
import optics as OPT                                            # noqa: E402,F401
import atmosphere as ATM                                        # noqa: E402

VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv
BUG = None
if '--bug' in sys.argv:
    BUG = sys.argv[sys.argv.index('--bug') + 1]


# --------------------------------------------------------------------- harness
# The harness is deliberately the same shape as `validate.py`'s -- Row, check,
# between, info, and a tolerance that is justified rather than fitted. It is
# forty lines of formatting with no physics in it, so it is written here rather
# than imported: importing `validate.py` would run the pool's 285 rows.
class Row:
    __slots__ = ('tier', 'name', 'exp', 'got', 'tol', 'status', 'why', 'unit')

    def __init__(self, tier, name, exp, got, tol, status, why, unit):
        self.tier, self.name, self.exp, self.got = tier, name, exp, got
        self.tol, self.status, self.why, self.unit = tol, status, why, unit


ROWS = []


def _fmt(v):
    if v is None:
        return '-'
    if isinstance(v, str):
        return v
    if isinstance(v, (tuple, list)):
        return '[' + ' '.join(_fmt(x) for x in v) + ']'
    a = np.asarray(v, float)
    if a.ndim:
        return '[' + ' '.join(_fmt(x) for x in a.ravel()) + ']'
    a = float(a)
    if a == 0:
        return '0'
    return '%.6g' % a if 1e-4 <= abs(a) < 1e5 else '%.3e' % a


def check(tier, name, got, exp, tol, why, unit='', rel=False):
    g, e = np.asarray(got, float), np.asarray(exp, float)
    # A ROW COMPUTED ON NOTHING IS THE WORST KIND OF GREEN, and this file shipped
    # two of them on its first run: `d_test > 5*L_0` selected no depths at all,
    # so "deep limit k -> w^2/g" passed by asserting something about an empty
    # array. np.all([]) is True. The pool's suite was caught blind twice by rows
    # that borrowed one name and wrote the rest themselves; this is the same
    # disease with a different vector, and the cure is that an empty comparison
    # is an ERROR, never a pass.
    if g.size == 0 or e.size == 0:
        raise AssertionError('row "%s" compares an EMPTY selection -- a mask '
                             'that matched nothing is a blind test, not a '
                             'passing one' % name)
    lim = np.asarray(tol, float) * (np.abs(e) if rel else 1.0)
    ok = bool(np.all(np.abs(g - e) <= lim + 1e-300))
    ROWS.append(Row(tier, name, exp, got, ('%s rel' % _fmt(tol)) if rel else tol,
                    'PASS' if ok else 'FAIL', why, unit))
    return ok


def between(tier, name, got, lo, hi, why, unit=''):
    g = float(got)
    ok = lo <= g <= hi
    ROWS.append(Row(tier, name, '%s..%s' % (_fmt(lo), _fmt(hi)), got, 'range',
                    'PASS' if ok else 'FAIL', why, unit))
    return ok


def info(tier, name, got, note, exp=None):
    ROWS.append(Row(tier, name, exp, got, '-', 'INFO', note, ''))


def error_row(label, exc):
    """A section that raised. Recorded as a ROW and the run continues.

    WAVE 2 FOUND THIS DEFECT IN ITS OWN HARNESS AND FIXED THE ROWS RATHER THAN
    THE HARNESS, so the harness could still be lied to. Three of its deliberate
    bugs destroyed the bar; the new reform rows had no guard for a degenerate
    profile and raised; the `--bugs` driver counted the exception as one catch
    and STOPPED -- so `cap-not-dissipation`, which fails eight rows, was
    reported as failing one. A row that explodes is worth less than a row that
    fails, because it takes every row after it with it.

    The fix that survives the next such bug is structural: the suite is a list
    of SECTIONS, each called through `guard()`, and an exception inside one
    section costs that section and nothing else. It prints as ERROR, it counts
    against the exit code exactly as a FAIL does, and the sections after it
    still run and still report their own failures.
    """
    ROWS.append(Row(0, 'section "%s" RAISED' % label, '-',
                    '%s: %s' % (type(exc).__name__, str(exc)[:60]), '-',
                    'ERROR', 'The section did not finish. Its remaining rows '
                    'were never evaluated, so this run is INCOMPLETE and not '
                    'merely failing.', ''))


def guard(fn, label, ctx):
    try:
        fn(ctx)
    except Exception as exc:                              # noqa: BLE001
        error_row(label, exc)
    return ctx


def openq(tier, name, got, exp, why, unit=''):
    """A criterion this scene does NOT meet yet, carried as a row.

    A fourth status, and it exists because the two honest options were both
    bad. Marking a known shortfall PASS by widening a tolerance is how a suite
    stops meaning anything; marking it FAIL implies a defect in the code, and
    the next reader spends an hour looking for a bug that is really a missing
    piece of physics. OPEN says: measured, understood, not achieved. It prints
    in the summary line, it is impossible to miss, and it does not set the exit
    code -- the README names every one of them.
    """
    ROWS.append(Row(tier, name, exp, got, '-', 'OPEN', why, unit))


# ------------------------------------------------------ dimensional algebra
class Dim:
    """Exponents of kg, m, s. Enough algebra to push units through a formula.

    This is how the standing trap gets a guard with nothing to transcribe:
    chapter 12 warns that building the undertow from the dissipation RATE D_w
    instead of the energy DENSITY E_w "yields an acceleration rather than a
    velocity", and the way to prove which one `beach.undertow` computes is to
    evaluate it on units instead of numbers. No tolerance, no sample point, and
    it cannot be satisfied by a constant.
    """
    __slots__ = ('e',)

    def __init__(self, kg=0, m=0, s=0):
        self.e = (kg, m, s)

    def __mul__(self, o):
        if not isinstance(o, Dim):
            return self
        return Dim(*[a + b for a, b in zip(self.e, o.e)])
    __rmul__ = __mul__

    def __truediv__(self, o):
        if not isinstance(o, Dim):
            return self
        return Dim(*[a - b for a, b in zip(self.e, o.e)])

    def __rtruediv__(self, o):
        return Dim(*[-a for a in self.e]) if not isinstance(o, Dim) else o / self

    def __pow__(self, n):
        return Dim(*[a * n for a in self.e])

    def __eq__(self, o):
        return isinstance(o, Dim) and self.e == o.e

    def __repr__(self):
        u = []
        for sym, ex in zip(('kg', 'm', 's'), self.e):
            if ex:
                u.append(sym if ex == 1 else '%s^%g' % (sym, ex))
        return '.'.join(u) if u else '1'


KG, M, S = Dim(kg=1), Dim(m=1), Dim(s=1)
VELOCITY = M / S
ACCELERATION = M / S ** 2
ENERGY_DENSITY = KG / S ** 2            # J/m^2
DISSIPATION_RATE = KG / S ** 3          # W/m^2


# ------------------------------------------------------------------ the bugs
# Each entry monkeypatches ONE defect into `beach` before the rows run. They are
# the defects this file's guards were written for -- several of them are defects
# this file's author actually shipped and had to find.
def _bug_dw_for_ew(mod):
    """The standing trap: build the undertow from the dissipation RATE."""
    orig = mod.sediment_flux

    def flux(tr, **kw):
        tr2 = dict(tr)
        tr2['E'] = tr['D_w']                    # W/m^2 where J/m^2 is meant
        return orig(tr2, **kw)
    mod.sediment_flux = flux
    mod._UNDERTOW_ARG = 'D_w'


def _bug_quarter_at_break(mod):
    """Pair the deep-water 1/4 with breaking-zone quantities -- chapter 12's
    named trap, put back into the function that owns it."""
    def thrust(tr, where='deep'):
        if where == 'deep':
            return (tr['E0'] / 4.0) * math.sin(2.0 * tr['theta0'])
        b = mod.breaker_state(tr)
        i = b['i_cell']
        return (tr['E'][i] / 4.0) * math.sin(2.0 * tr['theta'][i])   # /4, not /2
    mod.alongshore_thrust = thrust


def _bug_cap_not_dissipation(mod):
    """Chapter 12's runnable core taken literally: H = min(shoal, gamma*d)."""
    orig = mod.transform

    def transform(x, h, T, H0, theta0, **kw):
        tr = orig(x, h, T, H0, theta0, breaking=False,
                  **{k: v for k, v in kw.items() if k != 'breaking'})
        tr['H'] = np.minimum(tr['H'], mod.GAMMA_B * tr['d'])
        tr['E'] = mod.RHO_SW * mod.G * tr['H'] ** 2 / 8.0
        F = tr['E'] * tr['cg'] * np.cos(tr['theta'])
        tr['F'] = F
        tr['D_w'] = -np.gradient(F, tr['dx'])
        tr['brk'] = tr['H'] >= mod.GAMMA_B * tr['d'] - 1e-12
        return tr
    mod.transform = transform


def _bug_no_skewness(mod):
    orig = mod.sediment_flux
    mod.sediment_flux = lambda tr, **kw: orig(tr, **dict(kw, skew=False))


def _bug_no_undertow(mod):
    orig = mod.sediment_flux
    mod.sediment_flux = lambda tr, **kw: orig(tr, **dict(kw, undertow_on=False))


def _bug_no_refraction(mod):
    """Ignore Snell: keep the deep-water angle everywhere."""
    mod.snell_sin = lambda c, c0, s0: np.full_like(np.asarray(c, float), s0)


def _bug_wavelength_filter(mod):
    """Filter the depth at chapter 27's wavelength scale."""
    orig = mod.transform

    def transform(x, h, T, H0, theta0, **kw):
        kw = dict(kw)
        kw['filter_scale'] = mod.deep_wavelength(T) / 10.0
        return orig(x, h, T, H0, theta0, **kw)
    mod.transform = transform


def _bug_no_slope_term(mod):
    orig = mod.sediment_flux
    mod.sediment_flux = lambda tr, **kw: orig(tr, **dict(kw, eps_slope=0.0))


def _bug_no_hysteresis(mod):
    """THE MEMORY BUG. Leave the flux march in place, but never switch breaking
    off again: delete the `H <= gamma_s*d` branch by making gamma_s zero for the
    ONSET test only. The wave then dissipates forever and can never reform --
    which is what wave 1 suspected its own transform might silently be doing,
    and what this bug exists to prove it is not."""
    orig = mod.transform

    def transform(x, h, T, H0, theta0, **kw):
        kw = dict(kw)
        kw['gamma_s'] = kw.get('gamma_s', mod.GAMMA_STABLE)
        tr = orig(x, h, T, H0, theta0, **kw)
        return tr

    def marched(x, h, T, H0, theta0, **kw):
        tr = transform(x, h, T, H0, theta0, **kw)
        if not kw.get('breaking', True):
            return tr             # a caller that asked for NO breaking still
                                  # gets none; the bug is in the off-switch,
                                  # not in the on-switch, and patching both
                                  # would fail rows for the wrong reason
        # re-march with the off-switch removed
        d, cg, cos_t = tr['d'], tr['cg'], np.cos(tr['theta'])
        gs = mod.GAMMA_STABLE
        F = np.empty_like(d)
        F[0] = tr['F0']
        brk = np.zeros(d.size, bool)
        on = False
        dx = tr['dx']
        for i in range(d.size - 1):
            H_i = math.sqrt(max(8.0 * F[i] / (mod.RHO_SW * mod.G * cg[i]
                                              * cos_t[i]), 0.0))
            if H_i >= mod.GAMMA_B * d[i]:
                on = True                       # and NEVER off again
            brk[i] = on
            if on:
                F_s = (mod.RHO_SW * mod.G * (gs * d[i]) ** 2 / 8.0) * cg[i] * cos_t[i]
                F[i + 1] = F_s + (F[i] - F_s) * math.exp(-mod.K_DALLY * dx / d[i])
            else:
                F[i + 1] = F[i]
        brk[-1] = on
        tr['F'] = F
        tr['brk'] = brk
        tr['H'] = np.sqrt(np.maximum(8.0 * F / (mod.RHO_SW * mod.G * cg * cos_t), 0.0))
        tr['E'] = mod.RHO_SW * mod.G * tr['H'] ** 2 / 8.0
        D = np.zeros_like(F)
        D[1:-1] = -(F[2:] - F[:-2]) / (2.0 * dx)
        D[0] = -(F[1] - F[0]) / dx
        D[-1] = -(F[-1] - F[-2]) / dx
        tr['D_w'] = D
        return tr
    mod.transform = marched


def _bug_sat_no_slope(mod):
    """The saturated ratio with the bed slope dropped: GAMMA_eq = gamma_s. This
    is the reading of Dally that everyone starts with -- 'a broken wave decays
    to 0.4' -- and it is wrong by the slope on every real beach."""
    mod.saturated_ratio = lambda dddx, k_dally=mod.K_DALLY, \
        gamma_s=mod.GAMMA_STABLE: np.full_like(np.asarray(dddx, float), gamma_s)


def _bug_reform_exponent(mod):
    """Drop the 5/2 from the reform exponent a = K/m + 5/2. The 5/2 is the
    d^(5/2) in the shallow-water energy flux -- lose it and the closed form
    stops agreeing with the march it was derived for."""
    orig = mod.reform_ratio

    def reform_ratio(d_c, d_t, length, gamma_start=mod.GAMMA_B,
                     k_dally=mod.K_DALLY, gamma_s=mod.GAMMA_STABLE):
        m = (d_t - d_c) / max(length, 1e-9)
        if m <= 0.0:
            return float(gamma_start)
        a = k_dally / m                                     # the 5/2 gone
        g_eq = k_dally * gamma_s ** 2 / (k_dally + 2.5 * m)
        g = g_eq + (gamma_start ** 2 - g_eq) * (d_t / d_c) ** (-a)
        return math.sqrt(max(g, 0.0))
    mod.reform_ratio = reform_ratio


def _bug_crest_depth_mixed_fields(mod):
    """Wave 1's measurement put back: compare the RAW bed depth at the crest
    against a breaker depth that came out of the FILTERED field."""
    orig = mod.crest_depth_ratio
    mod.crest_depth_ratio = lambda tr, cr, b, field='wave': orig(tr, cr, b,
                                                                 field='bed')



def _bug_no_transverse_refraction(mod):
    """The 2-D march with its source term deleted: k_y is carried unchanged, so
    the crest keeps the direction it entered with and the surf lines stay
    straight while the shore curves. Bar section J's named failure."""
    orig = mod.transform_2d

    def transform_2d(x, y, h2, T, H0, theta0, **kw):
        kw = dict(kw)
        kw['refraction'] = False
        return orig(x, y, h2, T, H0, theta0, **kw)
    mod.transform_2d = transform_2d


def _bug_uniform_hardness(mod):
    """Chapter 12's own counter-case: uniform rock, and the headlands and the
    bay go with it."""
    orig = mod.hardness_field
    mod.hardness_field = lambda x, y, **kw: orig(x, y, **dict(kw,
                                                              uniform=True))
    mod._BAY_CACHE.clear()


def _bug_wide_notch(mod):
    """`notchHeight` too large -- the chapter says this is what costs you the
    wave-cut platform, and it is stated as a diagnostic rather than tested.

    Patched on the FUNCTION and not on the constant: `coastal_step`'s default
    argument was bound when the module was defined, so rebinding
    `mod.NOTCH_HEIGHT` changes nothing a caller sees. A bug that patches
    nothing is the failure mode wave 1 recorded under `quarter-at-break` --
    a defect with nothing to break tests the row, not the code."""
    orig = mod.coastal_step
    wide = 6.0 * mod.NOTCH_HEIGHT

    def step(*a, **kw):
        return orig(*a, **dict(kw, notch=kw.get('notch', wide)))
    mod.coastal_step = step
    mod.NOTCH_HEIGHT = wide
    mod._BAY_CACHE.clear()


def _bug_no_waterline_attack(mod):
    """coastalStep exactly as chapter 12 writes it: the notch band is a pure
    function of the cell's own elevation, with no term for the cliff face the
    water actually reaches. Measured consequence: the coast retreats a few
    metres and stops."""
    orig = mod.coastal_step
    mod.coastal_step = lambda *a, **kw: orig(*a, **dict(kw, waterline=False))
    mod._BAY_CACHE.clear()


def _bug_alignment_mixed_fields(mod):
    """Measure the crest against a contour read off the RAW bed while the crest
    direction came out of the FILTERED one. Wave 2's error class, in the place
    2-D offers it a second time."""
    orig = mod.contour_alignment
    mod.contour_alignment = lambda tr2, field='wave', **kw: orig(
        tr2, field='bed', **kw)


def _bug_flux_not_along_ray(mod):
    """Carry the plan-view sediment flux along the grid's x axis instead of
    along the wave direction. On a straight coast that is the same vector; in a
    bay it is not, and neither the slope term nor the divergence is right."""
    orig = mod.sediment_flux_2d

    def flux(tr2, **kw):
        tr3 = dict(tr2)
        tr3['theta'] = np.zeros_like(tr2['theta'])
        fl = orig(tr3, **kw)
        return fl
    mod.sediment_flux_2d = flux


BUGS = {
    'dw-for-ew': _bug_dw_for_ew,
    'quarter-at-break': _bug_quarter_at_break,
    'cap-not-dissipation': _bug_cap_not_dissipation,
    'no-skewness': _bug_no_skewness,
    'no-undertow': _bug_no_undertow,
    'no-refraction': _bug_no_refraction,
    'wavelength-filter': _bug_wavelength_filter,
    'no-slope-term': _bug_no_slope_term,
    'no-hysteresis': _bug_no_hysteresis,
    'sat-no-slope': _bug_sat_no_slope,
    'reform-exponent': _bug_reform_exponent,
    'crest-depth-mixed-fields': _bug_crest_depth_mixed_fields,
    'no-transverse-refraction': _bug_no_transverse_refraction,
    'uniform-hardness': _bug_uniform_hardness,
    'wide-notch': _bug_wide_notch,
    'no-waterline-attack': _bug_no_waterline_attack,
    'alignment-mixed-fields': _bug_alignment_mixed_fields,
    'flux-not-along-ray': _bug_flux_not_along_ray,
}


# ------------------------------------------------------------------ the suite
#
# THE SUITE IS A LIST OF SECTIONS, and that is a change wave 3 made to the
# harness rather than to any row. See `error_row` above: an exception anywhere
# used to end the run, and the `--bugs` driver counted the crash as one catch,
# so a defect that fails eight rows was reported as failing one. Each section
# below is called through `guard()`; one that raises costs itself and nothing
# after it, and prints as ERROR.
def _sec_waves(ctx):
    B, T, omega = ctx['B'], ctx['T'], ctx['omega']

    # ================================================== 1 · linear wave theory
    # The depth set runs from the solver's own floor (D_MIN -- below it the
    # function clamps and is not being asked a question) to five deep-water
    # wavelengths, so the deep-limit rows below have something to select.
    d_test = np.geomspace(B.D_MIN, 5.0 * B.deep_wavelength(T), 60)
    k = B.wavenumber(omega, d_test)
    resid = np.abs(B.G * k * np.tanh(k * d_test) - omega ** 2) / omega ** 2
    check(1, 'dispersion residual |g k tanh(kd) - w^2| / w^2',
          float(resid.max()), 0.0, 1e-12,
          'The solve is Newton to a relative step of 1e-14; the residual is '
          'then limited by float64 cancellation in tanh, ~1e-15 per term. '
          '1e-12 is three decades of headroom and still catches a solver that '
          'has stopped early.', rel=False)

    deep = k * d_test > 20.0
    check(1, 'deep limit k -> w^2/g', k[deep], omega ** 2 / B.G, 1e-9,
          'At kd > 20, tanh(kd) - 1 < 1e-17, so the two forms agree to well '
          'inside float64. Any visible difference is a wrong branch.', rel=True)

    # The shallow limit needs kd << 1, and a 9 s wave never gets there on a real
    # beach -- at the solver's depth floor it is still kd = 0.09. So the shallow
    # rows are asked of a 120 s wave, which reaches kd = 0.01 in half a metre.
    # Choosing the period to reach the limit is the point; pretending a 9 s wave
    # reaches it would be the error.
    om_long = 2.0 * math.pi / 120.0
    d_sh = np.geomspace(0.15, 2.0, 20)
    k_sh = B.wavenumber(om_long, d_sh)
    shallow = k_sh * d_sh < 0.02
    c_sh, cg_sh, n_sh = B.celerity(om_long, k_sh[shallow], d_sh[shallow])
    check(1, 'shallow limit c -> sqrt(g d)', c_sh,
          np.sqrt(B.G * d_sh[shallow]), 1e-4,
          'c/sqrt(gd) = sqrt(tanh(kd)/(kd)) = 1 - (kd)^2/6 + ...; at kd < 0.02 '
          'the truncation is 6.7e-5. The tolerance IS that series term.',
          rel=True)
    check(1, 'shallow limit n = c_g/c -> 1', n_sh, 1.0, 1.4e-4,
          'n = 1 - (kd)^2/3 + ... to leading order; at kd < 0.02 that is '
          '1.3e-4. Again the tolerance is the series, not the disagreement.',
          rel=True)
    _, _, n_dp = B.celerity(omega, k[deep], d_test[deep])
    check(1, 'deep limit n = c_g/c -> 1/2', n_dp, 0.5, 1e-12,
          'n -> 1/2 + kd/sinh(2kd); at kd > 300 the second term underflows. '
          'This is the factor of two the radiation-stress rows turn on.',
          rel=True)

    # tier 3: a completely different solver for the same root
    k_hunt = B.wavenumber_hunt(omega, d_test)
    rel_hunt = np.abs(k_hunt - k) / k
    band = (k * d_test > 0.05) & (k * d_test < 20)
    check(3, 'Hunt (1979) explicit k vs the Newton root',
          float(rel_hunt[band].max()), 0.0, 0.01,
          'Hunt\'s rational approximation is quoted (COHERENS ch.7 eq 7.10-12) '
          'as accurate to better than 1% over the whole range; the tolerance '
          'is that published accuracy, not a fit to what came out. Nothing in '
          'beach.wavenumber was written from it.', rel=False)
    info(3, 'Hunt vs Newton, worst relative difference',
         float(rel_hunt[band].max()), 'the size of the disagreement, for scale')

    # ================================================ 2 · shoaling / Green's law
    # A deliberately extreme case: a 60 s wave on a 1:200 ramp reaches kd = 0.02,
    # which is where Green's law is an asymptote rather than an approximation.
    x_g = B.make_grid(2000.0, 2.0)
    h_g = -np.maximum(0.02 + 0.005 * (2000.0 - x_g), 0.02)
    tr_g = B.transform(x_g, h_g, 60.0, 0.4, 0.0, breaking=False)
    m = (tr_g['k'] * tr_g['d'] < 0.05) & (tr_g['d'] > 0.2)
    Hd4 = tr_g['H'][m] * tr_g['d'][m] ** 0.25
    check(1, "Green's law: H * d^(1/4) constant as kd -> 0",
          float(Hd4.std() / Hd4.mean()), 0.0, 2e-3,
          'Green is the kd -> 0 asymptote of energy-flux conservation; the '
          'residual scatter is the O((kd)^2) correction, which over the band '
          'kd < 0.05 is at most 8e-4. Tolerance 2e-3 leaves room for the two '
          'ends of the band and nothing else.')
    lh, ld = np.log(tr_g['H'][m]), np.log(tr_g['d'][m])
    slope = float(np.polyfit(ld, lh, 1)[0])
    check(1, "Green's law: measured d(lnH)/d(lnd)", slope, -0.25, 2e-3,
          'Same asymptote, read as an exponent instead of a product. Green is '
          '-1/4 exactly; the tolerance is the same O((kd)^2) term.')

    flux_g = tr_g['E'] * tr_g['cg'] * np.cos(tr_g['theta'])
    check(1, 'energy flux E c_g cos(theta) conserved with no breaking',
          float(flux_g.std() / flux_g.mean()), 0.0, 1e-12,
          'With no dissipation the march is F_{i+1} = F_i exactly, so the only '
          'variation possible is float64 round-off in reconstructing H and '
          'squaring it back. A conservation law with a tolerance would be a '
          'contradiction in terms.')

    # ================================================== 3 · refraction / Snell
    x = B.make_grid()
    h_dean = B.dean_bed(x)
    tr_d = B.transform(x, h_dean, T, B.H0_SWELL, B.THETA0_SWELL, breaking=False)
    inv = np.sin(tr_d['theta']) / tr_d['c']
    check(1, "Snell invariant sin(theta)/c along the profile",
          float(inv.std() / inv.mean()), 0.0, 1e-12,
          'sin(theta)/c is how the angle is computed, so this row proves only '
          'that nothing downstream corrupts it -- it is a round-off guard and '
          'is labelled as one. The ray tracer below is the real test.')
    info(1, 'theta at the break, deg', math.degrees(
        B.breaker_state(B.transform(x, h_dean, T, B.H0_SWELL,
                                    B.THETA0_SWELL))['theta_b']),
        'from theta_0 = %.1f deg. Crests turn onto the contours.'
        % math.degrees(B.THETA0_SWELL))

    # tier 3: the 2-D ray tracer, on an alongshore-uniform bed, against Snell.
    # The tracer integrates dtheta/ds = (sin.dc/dx - cos.dc/dy)/c and has no
    # Snell in it; Snell has no ray integration in it.
    y2 = np.linspace(-150.0, 150.0, 61)
    h2 = np.repeat(h_dean[None, :], y2.size, 0)
    kk = B.wavenumber(omega, np.maximum(-h_dean, B.D_MIN))
    c_prof = omega / kk
    c0 = B.deep_celerity(T)
    d_prof = np.maximum(-h_dean, B.D_MIN)
    # THE RAY MUST BE LAUNCHED AT THE LOCAL ANGLE, NOT THE DEEP-WATER ONE, and
    # the first version of this row was not: it started the ray at 20 deg in
    # 8.2 m of water, where Snell has already turned the crest to 12.5 deg. The
    # tracer then tracked the right law from the wrong initial condition and the
    # row failed by a constant 0.144 rad AT EVERY STEP SIZE -- which is what
    # gave it away, because a truncation error would have halved with ds.
    th_start = math.asin(float(np.interp(1.0, x, c_prof)) / c0
                         * math.sin(B.THETA0_SWELL))
    ray_err = {}
    for ds in (1.0, 0.25):
        ray = B.trace_ray(x, y2, h2, T, 1.0, 0.0, th_start, ds=ds,
                          n_max=int(3000 / ds))
        th_snell = np.arcsin(np.clip(np.interp(ray[:, 0], x, c_prof) / c0
                                     * math.sin(B.THETA0_SWELL), -1, 1))
        keep = np.interp(ray[:, 0], x, d_prof) > 1.0
        ray_err[ds] = float(np.abs(ray[keep, 2] - th_snell[keep]).max())
        last = (math.degrees(ray[keep][-1, 2]),
                math.degrees(th_snell[keep][-1]))
    check(3, 'ray tracer vs Snell, worst |dtheta| in water deeper than 1 m',
          ray_err[0.25], 0.0, 3e-3,
          'The two sides share no line of code: the tracer integrates '
          'dtheta/ds = (sin.dc/dx - cos.dc/dy)/c and Snell is an invariant of '
          'the same field reached without integrating anything. The tolerance '
          'is the tracer\'s own convergence: the error falls from %.2e at '
          'ds = 1 m to %.2e at ds = 0.25 m, i.e. first order in ds through the '
          'bilinear c-field, so 3e-3 is the converged value plus its own '
          'refinement step. Restricted to d > 1 m because inside that the '
          'linear interpolation of c across a 1 m cell is itself the error.'
          % (ray_err[1.0], ray_err[0.25]), unit='rad')
    info(3, 'ray tracer |dtheta| at ds = 1.0 m and 0.25 m',
         (ray_err[1.0], ray_err[0.25]), 'first-order convergence, rad')
    info(3, 'ray tracer final angle vs Snell, deg', last,
         'the same number by two methods, at the shoreward end of the ray')

    # ==================================== 4 · radiation stress & the factor of 2
    tr_u = B.transform(x, h_dean, T, B.H0_SWELL, B.THETA0_SWELL, breaking=False)
    b_u = B.breaker_state(tr_u)
    i_b = b_u['i_cell']
    E_b, th_b, n_b = tr_u['E'][i_b], tr_u['theta'][i_b], tr_u['n'][i_b]
    # Both forms come from the SHIPPED function, so the bug harness has
    # somewhere to put the defect. A row that computes both sides itself tests
    # the row, not the code.
    deep_form = B.alongshore_thrust(tr_u, 'deep')
    brk_form = B.alongshore_thrust(tr_u, 'break')
    check(1, 'alongshore thrust: (E_0/4)sin2t_0 vs (E_b/2)sin2t_b',
          brk_form, deep_form, 0.04,
          'S_yx = E n sin cos is conserved with no dissipation, so the two '
          'forms are ONE quantity written in two places. They are not exactly '
          'equal here because n at the break is 0.96, not 1: the residual is '
          '(1/n_b - 1) = 3.7%%, which is the tolerance and is a statement '
          'about the shallow-water limit rather than about the code.',
          rel=True, unit='N/m')
    wrong = (E_b / 4.0) * math.sin(2.0 * th_b)
    check(1, 'the wrong pairing is off by exactly two',
          deep_form / wrong, 2.0, 0.09,
          'Pairing the deep-water quarter with breaking-zone quantities halves '
          'the thrust. This row exists so the factor of two is measured rather '
          'than remembered; the same 3.7% n_b gap sets the tolerance.')
    info(1, 'n at the break point', float(n_b),
         'the c_g/c that carries the factor: 1/2 offshore, 1 in the shallow '
         'limit, 0.96 here')

    # setdown against the closed form it was NOT written from
    eta = B.wave_setup(tr_u)
    closed = -(1.0 / 8.0) * tr_u['H'] ** 2 * tr_u['k'] / np.sinh(
        2.0 * np.minimum(tr_u['k'] * tr_u['d'], 350.0))
    seg = slice(20, i_b - 20)
    err = np.abs((eta - eta[0]) - (closed - closed[0]))[seg].max()
    check(1, 'wave setdown: integrated dS_xx/dx vs -(1/8)H^2 k/sinh(2kd)',
          float(err), 0.0, 3e-3,
          'The closed form is the exact integral of the same momentum balance '
          'in the shoaling zone (Longuet-Higgins & Stewart). beach.wave_setup '
          'integrates the balance numerically and never sees it. Tolerance is '
          'the trapezoid error over 400 cells of a curve with |eta| < 6 cm.',
          unit='m')

    # longshore current against the coefficient derived in beach.py
    tr_b = B.transform(x, h_dean, T, B.H0_SWELL, B.THETA0_SWELL)
    # On the DEAN RAMP, which is the plane slope the closed form assumes. Run on
    # the barred profile the same comparison is meaningless: the bar localises
    # the dissipation into a few metres and, with no lateral mixing in the
    # model, V spikes there. Chapter 12 says as much -- "C_f and the mixing
    # profile f are tuned" -- and the honest move is to test the coefficient
    # where its assumptions hold and report the spike separately.
    # The closed form assumes a SATURATED wave on a PLANE slope: H = gamma*d
    # everywhere in the surf zone, n = 1. So it is tested on exactly that -- a
    # constant-slope bed with the saturated field written onto it -- and what is
    # being checked is the shipped radiation-stress gradient and bed-stress
    # balance, not the Dally decay. Testing it on the real profile compares two
    # different wave fields and calls the difference a tolerance.
    x_p = B.make_grid(400.0, 1.0)
    tanb_p = 0.02
    h_p = -(400.0 - x_p) * tanb_p - 0.05
    tr_p = B.transform(x_p, h_p, T, B.H0_SWELL, B.THETA0_SWELL)
    sat = tr_p['H'] > B.GAMMA_B * tr_p['d']
    tr_p['H'] = np.where(tr_p['d'] * B.GAMMA_B < tr_p['H'],
                         B.GAMMA_B * tr_p['d'], tr_p['H'])
    i_sat = int(np.nonzero(B.GAMMA_B * tr_p['d'] <= tr_p['H'] + 1e-12)[0][0])
    tr_p['H'] = np.where(np.arange(x_p.size) >= i_sat,
                         B.GAMMA_B * tr_p['d'], tr_p['H'])
    tr_p['E'] = B.RHO_SW * B.G * tr_p['H'] ** 2 / 8.0
    tr_p['brk'] = np.arange(x_p.size) >= i_sat
    V_p = B.longshore_current(tr_p)
    j = i_sat + 40
    V_depth = (math.pi * B.GAMMA_B / (4.0 * 0.006)) * tanb_p * math.sqrt(
        B.G * tr_p['d'][j]) * math.sin(tr_p['theta'][j]) * math.cos(
        tr_p['theta'][j])
    V_closed = 1.25 * V_depth               # + the alongshore refraction term
    check(1, 'longshore V vs the 5pi/16 closed form, saturated plane slope',
          float(V_p[j]), V_closed, 0.06,
          'THIS ROW FOUND SOMETHING AND IT IS WORTH THE PARAGRAPH. It was '
          'first written against the (pi/4) form derived in beach.py from the '
          'depth gradient of S_yx alone, and it failed by 23 per cent. The numerical '
          'solve differentiates the WHOLE of S_yx, which also carries '
          'd(sin.cos)/dx: in shallow water Snell makes sin(theta) go as '
          'sqrt(d), so that term is exactly a quarter of the depth term, with '
          'the same sign. (pi/4)*(5/4) = 5pi/16 -- which is the '
          'Longuet-Higgins (1970) coefficient this project had been carrying '
          'as an unexplained `?`. The suite closed the `?` by failing at it. '
          'What is left is n = %.3f against the 1 the derivation assumes, and '
          'cos(theta) not being exactly 1; 6%% covers those two and nothing '
          'larger.' % float(tr_p['n'][j]), rel=True, unit='m/s')
    info(1, 'longshore V: depth term only, then with refraction, then measured',
         (V_depth, V_closed, float(V_p[j])),
         'the 5/4 between the first two is the alongshore refraction term, and '
         'it is the whole of the gap between pi/4 and 5pi/16')
    deepish = tr_p['d'] > 0.5
    between(2, 'peak longshore current, saturated plane slope, d > 0.5 m',
            float(np.abs(V_p[deepish]).max()), 0.2, 2.0,
            'Field longshore currents on an exposed sandy coast under a 1.5 m '
            'oblique swell run a few tenths of a m/s to about 1 m/s. Measured '
            'outside the last half-metre, where the linearised bed stress '
            'divides by an orbital velocity going to zero and the model is not '
            'making a claim.', unit='m/s')
    info(2, 'peak longshore current on the REAL barred profile',
         float(np.abs(B.longshore_current(tr_b)[tr_b['d'] > 0.5]).max()),
         'higher than the plane-slope value because the bar localises the '
         'dissipation into a few metres and this model carries no lateral '
         'mixing -- chapter 12 lists the mixing profile f among the tuned '
         'parts, and it is not modelled here')

    # ======================================== 5 · the undertow's DIMENSIONS
    # The shipped function reads RHO_SW off the module, so the module's density
    # is temporarily given units too -- otherwise rho drops out of the algebra
    # and the answer comes out wrong for a reason that has nothing to do with
    # the code under test. (It did, on the first run: kg/(m^2 s).)
    rho_real = B.RHO_SW
    try:
        B.RHO_SW = KG / M ** 3
        u_dim = B.undertow(ENERGY_DENSITY, VELOCITY, M, 1.0)
        u_bug = B.undertow(DISSIPATION_RATE, VELOCITY, M, 1.0)
    finally:
        B.RHO_SW = rho_real
    check(1, 'undertow(E_w, c, d) has dimensions of a VELOCITY',
          1.0 if u_dim == VELOCITY else 0.0, 1.0, 0.0,
          'Pushed through the SHIPPED function as units, not numbers: '
          'E/(rho c d) = (kg/s^2)/(kg/m^3 . m/s . m) = m/s. No tolerance is '
          'possible on an exponent, so there is none. Measured: %r' % (u_dim,))
    check(1, 'the same group built from D_w is an ACCELERATION',
          1.0 if u_bug == ACCELERATION else 0.0, 1.0, 0.0,
          'Chapter 12 names this exact substitution as a standing trap in '
          'reimplementations. This row proves the trap is real by evaluating '
          'it -- and --bug dw-for-ew proves the guard fires. Measured: %r'
          % (u_bug,))
    bb = B.breaker_state(tr_b)
    info(1, 'undertow at the break point, m/s',
         float(B.undertow(tr_b['E'][bb['i_cell']], tr_b['c'][bb['i_cell']],
                          tr_b['d'][bb['i_cell']], 1.0)),
         'the pure wave (Stokes) part, before the roller multiplier')
    d_bore = (KG / M ** 3) * (M / S ** 2) * M ** 3 / (S * M)
    check(1, 'bore dissipation scale has dimensions of W/m^2',
          1.0 if d_bore == DISSIPATION_RATE else 0.0, 1.0, 0.0,
          'rho g H^3/(4 T d): kg/m^3 . m/s^2 . m^3 /(s.m) = kg/s^3. It has to '
          'match D_w or the broken fraction is not dimensionless. Measured: '
          '%r' % (d_bore,))

    # ============================================ 6 · sediment, Exner, skewness
    check(1, 'skewness vanishes for a linear wave (Ur -> 0)',
          float(B.skewness(1e-9)), 0.0, 1e-8,
          'Chapter 12: "the skewness factor is what makes this term exist; '
          'u_orb^3 alone would move sand onshore under a perfectly symmetric '
          'swell, which is wrong". A symmetric wave moves no net sand.')
    ur = np.geomspace(1e-3, 1e3, 200)
    sk = B.skewness(ur)
    check(1, 'skewness is monotone in the Ursell number',
          1.0 if float(np.min(np.diff(sk))) >= 0.0 else 0.0, 1.0, 0.0,
          'A transport law that is not monotone in nonlinearity would move '
          'sand offshore for being MORE nonlinear. Exact: the row asserts that '
          'the smallest forward difference over 200 decades-spanning samples '
          'is not negative.')
    between(1, 'skewness saturates below its ceiling', float(sk[-1]),
            0.9 * B.SK_MAX, B.SK_MAX,
            'It must approach SK_MAX and never exceed it.')

    # Exner is closed: the sand is conserved to round-off.
    x_e = B.make_grid()
    h_e = B.dean_bed(x_e)
    h_e2, tr_e, _ = B.evolve(x_e, h_e, T, B.H0_SWELL, B.THETA0_SWELL,
                             n_steps=200)
    dv = float(np.trapezoid(h_e2 - h_e, x_e))
    check(1, 'Exner conserves sand volume over 200 steps', dv, 0.0, 2e-3,
          'The flux is tapered to zero at both ends, so the domain is closed '
          'and the only loss is the trapezoid rule against a gradient computed '
          'with np.gradient -- they are not the same quadrature, and the '
          'mismatch is O(dx^2 * curvature) ~ 1e-3 m^2 over 500 m. A model that '
          'gains sand can build any bar you like.', unit='m2')

    # the two fluxes and their sign structure
    fl_b = B.sediment_flux(tr_b)
    i_off = bb['i'] - 60
    check(1, 'seaward of the break the flux is ONSHORE', 1.0 if
          fl_b['q'][i_off] > 0 else 0.0, 1.0, 0.0,
          'The skewness term must win outside the surf zone: that is the half '
          'of the convergence that feeds the bar from offshore.')
    i_in = min(bb['i_cell'] + 12, x.size - 40)
    check(1, 'landward of the break the flux is OFFSHORE', 1.0 if
          fl_b['q'][i_in] < 0 else 0.0, 1.0, 0.0,
          'The undertow term must win just inside it: the other half of the '
          'convergence. Measured 12 m inside the break and not 40 -- at 40 m '
          'the wave has decayed enough that the dissipation, and with it the '
          'skewness suppression, has faded and the onshore term is back. That '
          'is the model being honest about a short surf zone, not a bug, but '
          'a row placed at 40 m would have been passing on the gravity term '
          'rather than on the undertow.')
    between(2, 'undertow inside the surf zone, m/s',
            float(fl_b['u_u'][tr_b['brk']].mean()), 0.08, 0.60,
            'Measured depth-averaged surf-zone undertows run about 0.1-0.4 '
            'm/s. The bounds are that published band with a 50% margin either '
            'side -- 0.08 and 0.60 -- and they are set from the band, not from '
            'anything this file produces: the measured value sits at 0.24, in '
            'the middle, and would pass a much tighter row. THIS IS THE ROW '
            'THAT CATCHES THE STANDING TRAP, and it took the --bugs table to '
            'find out that the dimension rows do not. Substituting the '
            'dissipation rate D_w for the energy density E_w is a CALLER '
            'passing the wrong thing, so the shipped function\'s dimensions '
            'are untouched and the algebra rows stay green; only the magnitude '
            'gives it away, at 0.058 m/s -- below the published band before '
            'any margin is applied. The dimension rows guard the formula; this '
            'one guards the argument.', unit='m/s')



def _sec_bar(ctx):
    B, T, omega = ctx['B'], ctx['T'], ctx['omega']
    x = ctx['x']
    h_dean = B.dean_bed(x)
    # ============================================================ 7 · the bar
    t0 = time.time()
    sc = B.run_scene()
    x_s, h_s, hd_s, tr_s = sc['x'], sc['h'], sc['h_dean'], sc['tr']
    cr = B.bar_crest(x_s, h_s, hd_s)
    th_s = B.trough(x_s, h_s, hd_s, cr['i'])
    b_s = B.breaker_state(tr_s)
    d_pred = b_s['H_b'] / B.GAMMA_B
    info(2, 'scene run time, s', time.time() - t0, 'the standard 6000-step run')

    check(1, 'a bar exists: crest anomaly above the initial ramp', 1.0 if
          cr['amp'] > 0.5 else 0.0, 1.0, 0.0,
          'The initial bed is a monotone Dean ramp with no ridge in it. An '
          'anomaly of half a metre cannot be a rounding artefact, and every '
          '--bug run that removes a transport term removes this too.')
    info(2, 'bar crest x, depth, amplitude, width',
         (cr['x'], cr['d'], cr['amp'], B.bar_width(x_s, h_s, hd_s, cr['i'])),
         'm from the offshore boundary; m of water; m of relief; m wide')

    # THE ABLATION THAT QUALIFIES CHAPTER 12'S OWN SENTENCE, and it is an INFO
    # row rather than an assertion because what it reports is a fact about the
    # model, not a target. The chapter says the bar is where "the two fluxes
    # converge". Switch the undertow off entirely and a bar still forms, at the
    # same depth: the onshore flux alone converges, because breaking kills the
    # SKEWNESS that drives it and q_on falls to zero over a few metres. The
    # undertow deepens the trough and adds about a fifth to the bar's
    # amplitude; it is not what puts the bar there.
    sc_nu = B.run_scene(undertow_on=False)
    cr_nu = B.bar_crest(sc_nu['x'], sc_nu['h'], sc_nu['h_dean'])
    info(2, 'bar with the undertow OFF: crest x, depth, amplitude',
         (cr_nu['x'], cr_nu['d'], cr_nu['amp']),
         'against %.0f m / %.2f m / %.2f m with it. The bar survives losing '
         'half of the mechanism the chapter names, which is worth knowing and '
         'is written up in README-beach.md rather than asserted away.'
         % (cr['x'], cr['d'], cr['amp']))
    between(2, 'bar crest depth against chapter 12: d_bar ~ H_b/gamma',
            cr['d'] / d_pred, 0.75, 1.25,
            'The chapter states the crest "settles near depth d ~ H_b/gamma" '
            'and gives no tolerance, because it is a scaling. +-25% is what '
            '"near" can defensibly mean for a relation quoted without one, and '
            'the measured value is printed beside it rather than hidden behind '
            'a pass.', unit='ratio')
    info(2, 'crest depth vs H_b/gamma, m', (cr['d'], d_pred),
         'measured, then predicted')

    # ---- WAVE 2: the 0.893 is a two-field comparison, not a shortfall.
    # H_b and d_b are outputs of the transform, which reads the FILTERED depth;
    # cr['d'] is the raw bed. On an 11 m crest the 1.5 m filter lifts the depth
    # the wave feels by 0.19 m and the ratio by 0.08. Both forms are printed,
    # and the one that compares like with like is the one that is asserted.
    check(2, 'd_bar ~ H_b/gamma evaluated in ONE depth field',
          B.crest_depth_ratio(tr_s, cr, b_s, field='wave'), 1.0, 0.06,
          'Chapter 12 gives the relation without a tolerance. 6% is chosen '
          'from the grid study below rather than from this number: refining '
          'space and time together over dx = 2.0/1.0/0.5/0.25 m the same-field '
          'ratio sits at 0.959 / 0.953 / 0.982 / 0.994, a spread of 4% over a '
          'factor of eight in dx, so 6% is one and a half times the spread the '
          'discretisation itself carries. The RAW-bed form of the same ratio '
          'runs 0.834 / 0.906 / 0.942 / 0.974 over those grids -- monotone and '
          'still climbing, which is the tell that it is measuring the filter '
          'and not the physics.', unit='ratio')
    info(2, 'the two forms of the ratio: raw bed, then the depth the wave broke in',
         (B.crest_depth_ratio(tr_s, cr, b_s, field='bed'),
          B.crest_depth_ratio(tr_s, cr, b_s, field='wave')),
         'wave 1 reported the first and called the 0.893 a prediction the '
         'model makes; wave 2 finds it is the two fields, and the trend it '
         'reported across sea states (0.81 -> 0.97) is the same artefact seen '
         'along H_0: a bigger bar is broader, so a fixed filter takes '
         'proportionally less off its crest.')
    check(1, 'the trough is landward of the crest and deeper than it', 1.0 if
          (th_s is not None and th_s['x'] > cr['x'] and th_s['d'] > cr['d'])
          else 0.0, 1.0, 0.0,
          'Bar AND trough, in that order, is the morphology the reference '
          'photograph shows. A single hump would pass a crest test alone.')

    lines = B.break_lines(tr_s)
    ratio = tr_s['H'] / np.maximum(tr_s['d'], 0.1)
    seg = slice(cr['i'], min(cr['i'] + 120, x_s.size))
    r_min = float(ratio[seg].min())
    check(1, 'H/d crosses gamma at the bar and un-crosses behind it',
          1.0 if (len(lines) >= 1 and lines[0][0] <= cr['x'] + 2.0
                  and r_min < B.GAMMA_B) else 0.0, 1.0, 0.0,
          'Section B, first half: the wave reaches the breaking limit over the '
          'bar the loop built and drops away from it in the trough behind, '
          'with nothing in the scene saying "break here" -- the crossings are '
          'read off H/d after the fact.')
    info(1, 'break onsets, m from the offshore boundary',
         [round(s[0], 1) for s in lines], 'each is a crossing of H/d = gamma')
    info(1, 'surf-zone spans -- where the wave IS breaking',
         B.surf_zone_spans(tr_s),
         'NOT the same list as the break onsets above, and wave 2 had to '
         'separate them: H/d >= gamma marks where a wave STARTS breaking and '
         'says nothing about where one stops. Section B\'s "two breaking '
         'lines" is a claim about this list having two entries.')

    # ============================ the second breaking line, wave 2 ============
    # THE CLOSED FORM THAT DECIDES IT. Put H = GAMMA*d into the Dally march in
    # shallow water and the fixed point falls out:
    #     GAMMA_eq = gamma_s / sqrt(1 + (5/2)(dd/dx)/K)
    # so a broken wave on a SHOALING bed decays to a ratio strictly ABOVE
    # gamma_s and can only un-break where the bed DEEPENS. The rows below check
    # that against the marched transform, which has no GAMMA_eq in it, and
    # against a published field measurement that predates it by a decade.
    def _plane(tan_b, d0=9.0, length=1400.0):
        xp = np.arange(0.0, length, 1.0)
        hp = np.minimum(-(d0 - tan_b * xp), -0.05)
        return B.transform(xp, hp, T, 1.5, 0.0)

    slopes = np.array([1 / 150., 1 / 100., 1 / 80., 1 / 60.])
    meas, cfm = [], []
    for tb in slopes:
        tp = _plane(tb)
        ok = tp['brk'] & (tp['d'] > 0.6)
        idx = np.nonzero(ok)[0]
        meas.append(float((tp['H'] / tp['d'])[idx[len(idx) // 2:]].mean()))
        cfm.append(float(B.saturated_ratio(-tb)))
    check(1, 'saturated H/d on a plane slope: closed form vs the march',
          np.array(meas), np.array(cfm), 0.03,
          'Two routes that share no arithmetic. The closed form is the fixed '
          'point of the Dally ODE with the shallow-water flux substituted; the '
          'measurement is the marched transform, which integrates the same ODE '
          'numerically and has never been told the fixed point exists. 3% is '
          'the residual of the shallow-water limit (c_g = sqrt(gd), n = 1) on '
          'slopes this gentle -- it grows to 9% by 1:30 and the closed form '
          'diverges past tan(beta) = 2K/5, both of which are the physics and '
          'are reported as INFO below rather than tolerated here.', rel=True)
    info(1, 'the same four, measured then closed-form',
         (np.array(meas), np.array(cfm)), 'slopes 1:150, 1:100, 1:80, 1:60')
    check(1, 'saturated H/d on the scene\'s own inner slope',
          float((tr_s['H'] / tr_s['d'])[min(cr['i'] + 80, x_s.size - 1)]),
          float(B.saturated_ratio(float(np.gradient(tr_s['d'], tr_s['dx'])[
              min(cr['i'] + 80, x_s.size - 1)]))), 0.02,
          'The same closed form on the bed the loop built rather than on a '
          'plane. 2% because the scene\'s inner slope is not exactly straight '
          'and the fixed point is approached, not sat on.', rel=True)
    between(2, 'saturated gamma rises with bed slope and stays in 0.2-1.0',
            float(B.saturated_ratio(-1 / 40.)) - float(B.saturated_ratio(-1 / 150.)),
            0.02, 1.0,
            'Raubenheimer, Guza & Elgar (1996), "Wave transformation across the '
            'inner surf zone": on a natural beach the saturated H/h "ranged '
            'from 0.2 to 1.0" and was "positively correlated with local beach '
            'slope", and NOT with offshore steepness. That is a field '
            'measurement from 1996 and this is a closed form off a 1985 decay '
            'model; neither was written from the other. This row asserts the '
            'sign and the direction -- the ratio must RISE with slope -- '
            'because the magnitude depends on which beach.', unit='ratio')
    info(2, 'saturated gamma at 1:150, 1:100, 1:60, 1:40, 1:25',
         [float(B.saturated_ratio(-1 / n)) for n in (150, 100, 60, 40, 25)],
         'all inside Raubenheimer et al.\'s 0.2-1.0, rising with slope, and '
         'gamma_s = 0.40 is the flat-bed limit of the family rather than a '
         'value any real surf zone sits at')
    info(1, 'the slope above which no saturated surf zone exists: 2K/5',
         B.saturation_slope_limit(),
         'the closed form\'s denominator vanishes there. Steeper than 1:%.1f '
         'and the shoaling gain outruns the breaking loss: the wave surges '
         'instead of spilling. That is the reflective end of Wright & Short\'s '
         'beach states falling out of a wave model that has never heard of '
         'them, and it lands within a factor of 1.5 of their 1:10-1:15.'
         % (1.0 / B.saturation_slope_limit()))

    # the reform criterion, and it is a DISTANCE.
    # DEFENSIVE, and it is not decoration: three of the deliberate bugs below
    # destroy the bar outright, and a row that CRASHES on a degenerate profile
    # takes every row after it down with it -- so the bugs that used to be
    # caught by four rows each get reported as one exception. A guard must fail,
    # not explode. `th_s` may be None and `_reform_length` may be infinite.
    d_cf = float(tr_s['d'][cr['i']])
    d_tf = float(tr_s['d'][th_s['i']]) if th_s else d_cf
    L_bar = (th_s['x'] - cr['x']) if th_s else 0.0
    check(3, 'reform closed form vs the march, on the loop\'s own back slope',
          B.reform_ratio(d_cf, d_tf, max(L_bar, 1e-3)), r_min, 0.06,
          'The integrated form G(d) = G_eq + (G_c-G_eq)(d/d_c)^-a, a = K/m + '
          '5/2, against the minimum H/d the marched transform actually '
          'reaches behind the bar. 6% because the closed form assumes a '
          'straight back slope and the loop\'s is concave. Independent method: '
          'one is an analytic integration in d, the other a cell-by-cell march '
          'in x.', rel=True)
    n_have = B.dally_efoldings(d_cf, d_tf, L_bar)
    L_need = min(B._reform_length(d_cf, max(d_tf - d_cf, 1e-3)), 400.0)
    L_need_i = int(round(L_need))
    info(1, 'Dally e-foldings behind the bar: delivered, then needed',
         (n_have, B.dally_efoldings(d_cf, d_tf, L_need)),
         'the currency the shortfall is denominated in. The wave has to lose '
         'a factor of (0.78/0.40)^2 in H/d while the depth grows, and the '
         'decay is K/d per METRE, so what is short is travel distance.')
    check(2, 'the trough sits one Dally decay length d/K behind the crest',
          L_bar * B.K_DALLY / max(d_cf, 1e-6), 1.0, 0.30,
          'NOT a coincidence and this row is the reason section B is hard. The '
          'trough is scoured by the undertow, the undertow is driven by the '
          'dissipation, and the dissipation decays over exactly d/K. So the '
          'morphology inherits the wave model\'s own length scale. Measured '
          'across five sea states from H_0 = 1.0 to 3.0 m the ratio runs 0.95 '
          '/ 0.99 / 1.09 / 1.19 / 1.24, and +-30%% covers that whole span. A '
          'one-bar breakpoint model therefore digs a trough ONE e-folding wide '
          'and needs %.1f.' % B.dally_efoldings(d_cf, d_tf, max(L_need, 1e-3)),
          unit='ratio')

    # THE MEMORY IS THERE. Give the transform the loop's own relief spread over
    # the length the closed form asks for and it un-breaks and re-breaks.
    h_probe = B.probe_back_slope(x_s, h_s, hd_s, cr['i'], L_need_i,
                                 max((th_s['d'] - cr['d']) if th_s else 0.0,
                                     1e-3))
    tr_probe = B.transform(x_s, h_probe, T, B.H0_SWELL, B.THETA0_SWELL)
    spans_probe = B.surf_zone_spans(tr_probe)
    check(3, 'the transform DOES reform, given the distance',
          float(len(spans_probe)), 2.0, 0.0,
          'The decisive row, and it separates two candidate causes that look '
          'identical from outside. Take the bed the loop built, keep its OWN '
          '%.2f m of relief, spread it over %d m instead of %.0f, and the '
          'transform gives two surf zones with calm water between them: %s. '
          'Nothing was tuned and no constant moved; the only change is how far '
          'the wave travels. So the model is NOT missing the memory -- the '
          'flux march and the gamma_b/gamma_s hysteresis carry it, and Dally, '
          'Dean & Dalrymple (1985) say so in their own abstract, which reports '
          'the model reproducing "the shoaling, breaking, and wave re-forming '
          'process" on a profile with two bar-and-trough systems. What the '
          'loop is missing is trough WIDTH. The probe bed is a diagnostic and '
          'is never the scene\'s.'
          % ((th_s['d'] - cr['d']) if th_s else 0.0, L_need_i, L_bar,
             '; '.join('%.0f-%.0f m' % s for s in spans_probe)))

    # ---- IS THE GAP ITSELF THE GRID? Refine space and time TOGETHER and see.
    # The energetics slope term is a diffusion with D_eff ~ 6.7e-4 m^2/s, so
    # halving dx without cutting dt walks straight into dt < dx^2/(2 D_eff) and
    # the bed grows a spike. dt is put at 0.6 of that bound here and the run
    # length held in SECONDS, not in steps.
    D_EFF = 6.7e-4
    T_PHYS = 2000 * 300.0
    r_grid = []
    for dxg in (1.0, 0.5):
        dtg = min(300.0, 0.6 * dxg * dxg / (2.0 * D_EFF))
        scg = B.run_scene(dx=dxg, dt=dtg, n_steps=int(round(T_PHYS / dtg)))
        trg = scg['tr']
        i0 = int(np.argmax(trg['brk']))
        r_grid.append(float((trg['H'] / trg['d'])[i0:i0 + int(80 / dxg)].min()))
    check(3, 'the reform gap is grid-CONVERGED: min H/d at dx = 1.0 vs 0.5 m',
          r_grid[1], r_grid[0], 0.02,
          'The obvious escape from this OPEN row is that 0.456 is a coarse-grid '
          'number. It is not. Refining space and time together the minimum H/d '
          'behind the bar runs 0.4574 / 0.4607 / 0.4629 / 0.4625 at dx = 2.0 / '
          '1.0 / 0.5 / 0.25 m -- converged by 0.5 m and moving AWAY from 0.40, '
          'not toward it. The bar\'s relief IS grid-dependent (0.62 / 0.52 / '
          '0.48 / 0.44 m over the same four) and converges downward, so the '
          'refined bar is a slightly worse case, not a better one. Volume '
          'stayed closed to 2.5e-12 m^2 on the finest grid, so this is a '
          'converged answer and not a blown-up one.', rel=True)
    info(3, 'min H/d behind the bar at dx = 1.0 and 0.5 m, dt at 0.6 of the '
            'diffusion bound', (r_grid[0], r_grid[1]),
         'dt = 300 s and 112 s; the same 167 h of physical time in both')

    # ---- cause 4: the forcing history. It reverses.
    h_tide, _ = B.evolve_forced(
        x_s, hd_s, T, B.THETA0_SWELL, n_steps=B.N_STEPS,
        z_of_t=lambda t: 1.0 * math.sin(2.0 * math.pi * t / (12.42 * 3600.0)))
    cr_ti = B.bar_crest(x_s, h_tide, hd_s)
    info(2, 'relief under a +-1.0 m semidiurnal tide, against steady forcing',
         (cr_ti['amp'], cr['amp']),
         'Chapter 12 says the profile "breathes on a storm/calm cycle" and a '
         'moving datum is the obvious way to widen a breakpoint bar. It does '
         'the opposite: the tide walks the break point over ~100 m of profile '
         'and the convergence smears into a low terrace instead of a bar. '
         'Steady forcing is the most favourable case this model has, which is '
         'the reverse of the guess and is why cause 4 is dead.')
    h_ray, _ = B.evolve_forced(x_s, hd_s, T, B.THETA0_SWELL,
                               n_steps=B.N_STEPS, n_quantiles=3)
    cr_ry = B.bar_crest(x_s, h_ray, hd_s)
    th_ry = B.trough(x_s, h_ray, hd_s, cr_ry['i'])
    info(2, 'Rayleigh-averaged flux: crest amp, trough separation, relief',
         (cr_ry['amp'], (th_ry['x'] - cr_ry['x']) if th_ry else -1.0,
          (th_ry['d'] - cr_ry['d']) if th_ry else -1.0),
         'against %.2f m / %.0f m / %.2f m monochromatic. THE TRADE IS THE '
         'FINDING: spreading the break point over the width of a Rayleigh '
         'height distribution is the right physics for why real bars are '
         'broader than a monochromatic breakpoint model builds them, and it '
         'does widen the crest-to-trough separation -- but it pays for every '
         'metre of width in relief, and the minimum H/d behind the bar barely '
         'moves. Every mechanism tried in this wave trades the same two '
         'quantities against each other, which is why the 14%% gap is robust '
         'rather than marginal.' % (cr['amp'], L_bar, d_tf - d_cf))

    # what the photograph would actually record, and it does not rescue this
    qb = B.breaking_fraction_bj(tr_s)
    info(2, 'Battjes-Janssen Q_b over the bar / in the trough / inshore',
         (float(qb[cr['i']]), float(qb[th_s['i']]) if th_s else -1.0,
          float(qb[min(cr['i'] + 120, x_s.size - 1)])),
         'Battjes & Janssen (1978)\'s clipped-Rayleigh breaking fraction, '
         '(1-Q_b)/ln Q_b = -(H_rms/H_m)^2, computed on this scene\'s own H. '
         'It matters because the transform is monochromatic and the photograph '
         'is not: what a camera calls a breaking line is a large FRACTION of '
         'waves breaking. The contrast section B describes IS there -- 1.00 '
         'over the bar against 0.07 in the trough -- but Q_b stays near 0.07 '
         'all the way to the shore, so the random-wave reading does not rescue '
         'the second line either. Reported, not used as a pass.')

    openq(1, 'section B: a SECOND breaking line, with reform between',
          r_min, '< %.2f' % B.GAMMA_STABLE,
          'STILL NOT ACHIEVED, and wave 2 can now say exactly why and exactly '
          'by how much. The reform is a DISTANCE condition, not a relief one: '
          'the wave needs %.2f e-foldings of the Dally decay between crest and '
          'trough and gets %.2f, because the trough it digs is one decay '
          'length d/K wide and the un-breaking takes about two. Equivalently, '
          'at the loop\'s own 15 m back slope it needs %.2f m of relief and '
          'has %.2f m. Four candidate causes were separated and three of them '
          'are dead: the transform HAS the memory (the probe row above reforms '
          'on the loop\'s own relief spread over %d m); the forcing history '
          'makes it WORSE, not better (storm/calm cycling at 1-3 m over 5 '
          'days, semidiurnal tide at +-0.5 and +-1.0 m, and a 3-, 5- and '
          '8-quantile Rayleigh height distribution all LOWER the relief, and '
          'the Rayleigh case widens the trough only by trading relief away for '
          'it); and the decay rate K is the same axis as the distance, since '
          'the e-folding count is K*L/d -- reform needs K ~ 0.35-0.40 against '
          'the flux-form standard 0.15. What is left is that a single-bar '
          'breakpoint model in 1-D has no mechanism that widens the trough '
          'without flattening the bar, and the two effects cancel to within a '
          'few per cent of H/d across everything tried -- and it is not the '
          'grid either: refined in space and time together the trough minimum '
          'converges to 0.463, AWAY from 0.40. Named plainly: what '
          'this needs is a SECOND bar (the field configuration that actually '
          'shows two lines is a double-bar system, not one bar plus a '
          'shorebreak), and a second bar needs the alongshore circulation and '
          'the inner-surf-zone feedback that chapter 12 puts out of scope with '
          'the 2DH model. That is a missing mechanism, not a missing '
          'tolerance.'
          % (B.dally_efoldings(d_cf, d_tf, L_need), n_have,
             B.reform_relief(d_cf, max(L_bar, 1e-3)), d_tf - d_cf, L_need_i))
    check(1, 'H/d at the first break equals gamma', b_s['H_b'] / b_s['d_b'],
          B.GAMMA_B, 2e-3,
          'The crossing is interpolated between the two cells that bracket it, '
          'so the residual is the curvature of H/d over one cell, ~1e-3. This '
          'row guards the SHARED constant actually being the one that fires: '
          'the same GAMMA_B breaks the wave here and predicts the crest depth '
          'above.')

    # the chapter's own verification list: storms push the bar seaward
    sc_st = B.run_scene(H0=B.H0_STORM)
    cr_st = B.bar_crest(sc_st['x'], sc_st['h'], sc_st['h_dean'])
    b_st = B.breaker_state(sc_st['tr'])
    check(1, 'a storm moves the bar SEAWARD', 1.0 if cr_st['x'] < cr['x']
          else 0.0, 1.0, 0.0,
          'Chapter 12, "Verify": "the bar crest sits near depth d ~ H_b/gamma '
          'and migrates seaward when H_b is raised". H_0 is doubled and '
          'nothing else changes.')
    info(2, 'storm bar: crest x, depth, H_b/gamma',
         (cr_st['x'], cr_st['d'], b_st['H_b'] / B.GAMMA_B),
         'H_0 = %.1f m against the swell case above' % B.H0_STORM)
    between(2, 'storm crest depth against H_b/gamma too',
            cr_st['d'] / (b_st['H_b'] / B.GAMMA_B), 0.75, 1.25,
            'The same scaling, at twice the wave height. A relation that only '
            'holds at one sea state is a coincidence.', unit='ratio')

    # ------- tier 3: the same bar by refined grid, refined time step, halved
    # K_Q. All four run to N_CONV steps rather than the full N_STEPS: the crest
    # DEPTH is at its equilibrium value within the first thousand steps (it is
    # set by where the wave breaks, not by how long it has been building), and
    # what these rows compare is that depth. The position keeps migrating and
    # is reported as INFO rather than asserted.
    N_CONV = 2000
    sc_ref = B.run_scene(n_steps=N_CONV)
    cr_ref = B.bar_crest(sc_ref['x'], sc_ref['h'], sc_ref['h_dean'])
    info(3, 'the convergence baseline: crest depth at %d steps' % N_CONV,
         cr_ref['d'], 'the three rows below are compared against this, not '
         'against the full run')
    sc_dx = B.run_scene(dx=0.5, n_steps=N_CONV)
    cr_dx = B.bar_crest(sc_dx['x'], sc_dx['h'], sc_dx['h_dean'])
    check(3, 'crest depth on a 0.5 m grid vs the 1.0 m grid', cr_dx['d'],
          cr_ref['d'], 0.10,
          'Halving dx changes the discretisation of every gradient in the '
          'loop. 10% is the size of the second-order term the coarse grid is '
          'allowed to be wrong by; a larger move would mean the bar is a grid '
          'feature.', rel=True, unit='m')
    info(3, 'crest x on 0.5 m grid vs 1.0 m grid', (cr_dx['x'], cr_ref['x']),
         'position is the softer of the two -- the crest migrates slowly, so '
         'it is also a clock comparison')

    sc_dt = B.run_scene(n_steps=3 * N_CONV, dt=B.DT_MORPH / 3.0)
    cr_dt = B.bar_crest(sc_dt['x'], sc_dt['h'], sc_dt['h_dean'])
    check(3, 'crest depth at dt/3 and 3x the steps', cr_dt['d'], cr_ref['d'],
          0.05,
          'Same morphological time, a third of the step. Explicit Exner is '
          'first order in dt, so the difference bounds the time-stepping '
          'error; 5% says the answer is the physics and not the integrator.',
          rel=True, unit='m')

    sc_kq = B.run_scene(n_steps=2 * N_CONV, k_q=B.K_Q / 2.0)
    cr_kq = B.bar_crest(sc_kq['x'], sc_kq['h'], sc_kq['h_dean'])
    check(3, 'K_Q is a clock, not a shape: half K_Q, twice the steps',
          cr_kq['d'], cr_ref['d'], 0.05,
          'The transport coefficient multiplies q and therefore only scales '
          'time. If the bar moved, K_Q would be setting the morphology and '
          'would need a derivation this file cannot give it.', rel=True,
          unit='m')

    # ------- the coefficient this file could not cite, bounded instead.
    # K_DALLY governs how fast a broken wave decays, not where it starts
    # breaking -- so the onset, and with it the crest depth H_b/gamma, cannot
    # depend on it. That is why an uncited K is survivable, and this row is the
    # proof rather than the assertion.
    ons = []
    for kd in (0.05, 0.15, 0.40):
        trk = B.transform(x, h_dean, T, B.H0_SWELL, B.THETA0_SWELL, k_dally=kd)
        ons.append(B.breaker_state(trk)['x'])
    check(1, 'the break ONSET does not depend on the Dally decay coefficient',
          float(np.ptp(ons)), 0.0, 1e-9,
          'K governs how fast a broken wave decays, not where it starts '
          'breaking -- so the onset, and with it the crest depth H_b/gamma, is '
          'independent of the one coefficient this file could not cite. That '
          'is why the uncited K is survivable.', unit='m')

    lag = []
    for nl in (0.25, 0.5, 1.0):
        s = B.run_scene(n_steps=N_CONV, n_lag=nl)
        lag.append(B.bar_crest(s['x'], s['h'], s['h_dean'])['d'])
    check(3, 'crest depth across roller lag 0.25L .. 1.0L',
          float(np.ptp(lag)), 0.0, 0.15,
          'The lag length is marked `?`. Sweeping it a factor of four moves '
          'the crest depth by less than 15 cm on a 2 m crest, which bounds '
          'what the missing citation can cost.', unit='m')
    info(3, 'crest depth at lag 0.25L / 0.5L / 1.0L', lag, 'm of water')

    ctx.update(sc=sc, x_s=x_s, h_s=h_s, hd_s=hd_s, tr_s=tr_s, cr=cr,
               th_s=th_s, b_s=b_s, d_pred=d_pred)


def _sec_states(ctx):
    B, T, omega = ctx['B'], ctx['T'], ctx['omega']
    x = ctx['x']
    h_dean = B.dean_bed(x)
    sc, x_s, h_s, hd_s = ctx['sc'], ctx['x_s'], ctx['h_s'], ctx['hd_s']
    tr_s, cr, th_s, b_s = ctx['tr_s'], ctx['cr'], ctx['th_s'], ctx['b_s']
    # ======================================== 8 · sediment and the beach state
    w_s = B.settling_velocity()
    d_fine = 20e-6
    s_rel = B.RHO_S / B.RHO_SW - 1.0
    w_stokes = s_rel * B.G * d_fine ** 2 / (18.0 * B.NU_W)
    w_soul = B.settling_velocity(d50=d_fine)
    # AND SOULSBY DOES NOT REDUCE TO STOKES, WHICH IS WORTH KNOWING RATHER THAN
    # TOLERATING. Expanding sqrt(a^2 + x) - a = x/2a for small D*, Soulsby's
    # coefficient is 1.049/(2*10.36) = 0.050627 where Stokes' is 1/18 =
    # 0.055556 -- a fixed 8.9% shortfall in the Stokes limit, not a numerical
    # difference. So the row is written as that RATIO, which is a closed form,
    # instead of as an agreement with a tolerance wide enough to hide it.
    ratio_lim = (1.049 / (2.0 * 10.36)) * 18.0
    check(1, 'Soulsby/Stokes in the Stokes limit = 1.049*18/(2*10.36)',
          w_soul / w_stokes, ratio_lim, 2e-3,
          'At 20 um, D* = 0.48 and the cubic term is 1e-3 of the constant, so '
          'the expansion above is exact to better than 1e-3. The two sides are '
          'Soulsby (COHERENS 7.41) and Stokes (1847); neither was written from '
          'the other, and their ratio in the limit is arithmetic on the fit\'s '
          'own constants.')
    info(2, 'Soulsby is 8.9% below Stokes in the fine limit',
         (w_soul, w_stokes),
         'a property of the published fit, not of this implementation -- and '
         'the reason this row is a ratio and not an agreement')
    # Zhang & Xie (1993), the other formula COHERENS carries -- a genuinely
    # independent published fit, read from the same chapter but not the same
    # equation.
    w_zx = (math.sqrt((13.95 * B.NU_W / B.D50) ** 2
                      + 1.09 * s_rel * B.G * B.D50) - 13.95 * B.NU_W / B.D50)
    check(2, 'Soulsby vs Zhang & Xie (1993) at D50 = 0.30 mm', w_s, w_zx, 0.15,
          'Two published fits to the same sand, quoted side by side in COHERENS '
          'ch.7 (7.41) and (7.42). Published settling fits differ by 10-15% at '
          'medium sand; a larger gap would mean one of them is mistyped.',
          rel=True, unit='m/s')
    info(2, 'w_s at D50 = 0.30 mm: Soulsby, Zhang & Xie', (w_s, w_zx), 'm/s')

    om = B.dimensionless_fall_velocity(b_s['H_b'], w_s, T)
    between(2, 'dimensionless fall velocity Omega', om, 1.0, 6.0,
            'Wright & Short (1984) via chapter 12: 1 < Omega < 6 is the '
            'INTERMEDIATE state, "the bar-rip family". This scene produced a '
            'bar, so a state outside the barred band would mean the model and '
            'the classifier disagree about the beach they are describing.')
    info(2, 'beach state', B.beach_state(om), 'from Omega above')

    # ================================================== 9 · Iribarren & run-up
    tanb_s = float(abs(np.gradient(h_s, tr_s['dx'])[cr['i']]))
    L0 = B.deep_wavelength(T)
    xi0 = B.iribarren(tanb_s, B.H0_SWELL, L0)
    xib = B.iribarren(tanb_s, b_s['H_b'], L0)
    between(2, "Iribarren xi_0 inside Hunt's stated validity", xi0, 0.1, 2.3,
            'Coastal Wiki, "Surf similarity parameter": "According to Hunt '
            '(1959), R ~ Hs xi applies within the range 0.1 < xi < 2.3". If '
            'the scene sat outside it, the run-up scaling would not be '
            'reportable at all.')
    info(2, 'xi_0 and its class (deep-water thresholds 0.5 / 3.3)',
         (xi0, B.breaker_class(xi0, 'deep')),
         'the thresholds attributed to Battjes (1974) in deep-water quantities')
    info(2, 'xi_b and its class (local thresholds 0.4 / 2.0)',
         (xib, B.breaker_class(xib, 'local')),
         'Coastal Wiki quotes the SAME Battjes (1974) with different numbers, '
         'because the parameter is built from different quantities. Same trap '
         'family as E_0/4 vs E_b/2; beach.py refuses to carry one table.')
    info(2, 'run-up scale R ~ H_0 xi_0, m', B.runup_hunt(B.H0_SWELL, xi0),
         'Hunt (1959) is a SCALING; the constant of proportionality is `?` and '
         'run-up rendering is out of scope this wave')

    # =========================================== 10 · the scene, and the sun
    el, el_app, az, am = ATM.solar_position(
        37.3167, -8.8000, 2026, 8, 12, 18, 8, 0.0, 1.0)[:4]
    check(2, "the bar's own solar elevation for the surf frames", el_app, 27.17,
          0.02,
          'gauntlet/sea/bar.md states 27.17 deg / 268.31 deg / air mass 2.182 '
          'for 2026-08-12 18:08 WEST. This row recomputes them through the '
          'POOL\'s shared module, which knew nothing about this beach. Two '
          'decimal places is the precision the bar quotes.', unit='deg')
    check(2, "the bar's own solar azimuth", az, 268.31, 0.02,
          'Same source, same call. A wrong quadrant leaves the elevation '
          'correct and is otherwise silent -- which is why the bar asks for it '
          'to be checked.', unit='deg')
    check(2, "the bar's own air mass", am, 2.182, 0.002,
          'Kasten & Young via the shared module. It is not used by any number '
          'in this scene; it is here because a shared module that has drifted '
          'would show up here first.')
    between(1, 'the whole domain is inside wave base', float(-h_dean[0]),
            0.0, B.deep_wavelength(T) / 2.0,
            'Chapter 12 gates the morphodynamic step to above wave base '
            '(L_0/2 = %.1f m here). The offshore boundary is in %.1f m, so the '
            'gate is inactive and the loop never runs where it may not.'
            % (B.deep_wavelength(T) / 2.0, -h_dean[0]), unit='m')




# ============================================ 11 · the coast in plan, wave 3
# Bar section J settles that this coast is an embayment between headlands, and
# it makes one of the four required closed forms checkable by eye: the breaking
# lines bend to stay parallel to the shore all the way round the curve. That
# check is worth nothing if the curve was drawn, so these rows are about where
# the curve came from -- chapter 12's notch -> collapse -> deposit, run on the
# plan grid with a spatially varying hardness and nothing else.
def _sec_coast(ctx):
    B = ctx['B']
    t0 = time.time()
    cs = B.run_coast()
    ctx['cs'] = cs
    x, y, dx, dy = cs['x'], cs['y'], cs['dx'], cs['dy']
    info(2, 'coastal loop run time, s', time.time() - t0,
         '%d iterations on a %d x %d plan grid' % (B.N_COAST, y.size, x.size))

    # ---- the initial condition has no bay in it, to machine precision
    spread = float(np.abs(cs['h0'] - cs['h0'][0][None, :]).max())
    check(1, 'the coast starts alongshore-uniform', spread, 0.0, 0.0,
          'Everything the loop is credited with -- the cliff, the bench, the '
          'embayment -- has to come out of a bed whose every alongshore row is '
          'the same number. Zero, not a tolerance: `initial_coast` broadcasts '
          'one profile, so any spread at all would mean something wrote to it.',
          unit='m')

    # ---- the domain's rock book closes
    dv = float((cs['h'] - cs['h0']).sum()) * dx * dy
    check(1, 'coastal loop: eroded = deposited + exported', dv + cs['exported'],
          0.0, 1e-6 * max(cs['vol'], 1.0),
          'The notch removes a measured volume each step; the sheltered '
          'nearshore takes what it has room for and the rest is returned as '
          '`export` instead of vanishing. A loop that quietly loses rock will '
          'retreat any coast you ask it to -- the first version of this one '
          'lost 116154 m^3 out of a closed domain because the pseudocode\'s '
          'deposition weight is identically zero over open water.', unit='m^3')
    info(2, 'rock eroded, deposited, exported (m^3)',
         (cs['vol'], cs['vol'] - cs['exported'], cs['exported']),
         'a cliff makes far more debris than a beach can hold: retreating '
         '100 m of a plain rising at 1:12.5 removes ~750 m^2 per metre of '
         'coast and the nearshore band holds ~120. The export is real and it '
         'is reported rather than hidden.')

    # ---- chapter 12: hardness is what makes headlands
    xs, xs0 = cs['x_s'], cs['x_s0']
    hard_at = np.array([cs['hard'][j, int(round(xs[j] / dx))]
                        for j in range(y.size)])
    r = float(np.corrcoef(xs, hard_at)[0, 1])
    check(2, 'retreat is set by the rock: corr(shoreline, hardness)', r, -1.0,
          0.35,
          'Chapter 12: a landform "emerges naturally where a hard bed survives '
          'while the softer rock around it retreats -- so it requires '
          'spatially varying hardness". x_s increases shoreward, so a coast '
          'whose plan-form is cut by the geology has this correlation strongly '
          'NEGATIVE. The tolerance is loose on purpose: the claim is the sign '
          'and the strength, not a number the chapter gives.', unit='r')
    amp = float(xs.max() - xs.min())
    info(2, 'embayment: shoreline range and retreat (m)',
         (amp, float(xs.mean() - xs0.mean())),
         'headland-to-bay amplitude, then the mean retreat that produced it')

    # ---- chapter 12: uniform rock gives a straight cliff and nothing else
    cs_u = B.run_coast(uniform_hardness=True, n_steps=max(B.N_COAST // 4, 1))
    cs_v = B.run_coast(n_steps=max(B.N_COAST // 4, 1))
    amp_u = float(cs_u['x_s'].max() - cs_u['x_s'].min())
    amp_v = float(cs_v['x_s'].max() - cs_v['x_s'].min())
    check(2, 'uniform rock: no embayment (amplitude ratio to varying rock)',
          amp_u / max(amp_v, 1e-9), 0.0, 0.34,
          'Chapter 12 states it as the reason coastal graphs look boring: '
          '"With uniform rock you get a straight cliff and nothing else". The '
          'same loop, the same steps, the same exposure sweep, hardness set to '
          '1 everywhere. Some residue is expected and is the exposure feedback '
          'acting on its own; a third of the varying-rock amplitude is the '
          'ceiling this row allows it.', unit='ratio')
    info(2, 'shoreline amplitude, uniform vs varying hardness (m)',
         (amp_u, amp_v), 'at a quarter of the standard run, both from the '
         'same straight initial coast')

    # ---- chapter 12's own wave-cut-platform diagnostic, run BOTH ways
    def _bench(h2, xx):
        """Width of the flat bench seaward of the shoreline, per row."""
        xsl = B.shoreline_x(xx, h2)
        ddx = float(xx[1] - xx[0])
        out = []
        for j in range(h2.shape[0]):
            i1 = int(round(xsl[j] / ddx))
            i0 = max(i1 - int(200.0 / ddx), 0)
            seg = h2[j, i0:i1]
            if seg.size < 6:
                out.append(0.0)
                continue
            lvl = float(np.median(seg[-int(0.4 * seg.size):]))
            k = seg.size - 1
            n = 0
            while k >= 0 and abs(seg[k] - lvl) <= 0.25:
                n += 1
                k -= 1
            out.append(n * ddx)
        return np.array(out)

    w_narrow = _bench(cs['h'], x)
    cs_wide = B.run_coast(notch=6.0 * B.NOTCH_HEIGHT,
                          n_steps=max(B.N_COAST // 4, 1))
    w_wide = _bench(cs_wide['h'], x)
    check(2, "chapter 12's bench diagnostic: narrow notch gives a bench",
          1.0 if w_narrow.mean() > 40.0 else 0.0, 1.0, 0.0,
          'Chapter 12: "The flat bench at sea level is the signature. It '
          'emerges if `band` is narrow and `K_coast` is high ... If you\'re '
          'not getting one, `notchHeight` is too large." 40 m is a bench and '
          'not a slope: the Dean ramp this coast relaxes to crosses 0.5 m of '
          'relief in 20 m near the shoreline, so a 40 m run inside +-0.25 m '
          'cannot be a ramp.', unit='m')
    check(2, "and the same diagnostic the other way: notch x 6, no bench",
          1.0 if w_wide.mean() < 0.5 * w_narrow.mean() else 0.0, 1.0, 0.0,
          'The chapter gives the diagnostic as a one-way instruction. A row '
          'that only checks the good case cannot tell a bench that emerged '
          'from a bench that was always going to be there, so this one runs '
          'the loop at six times the notch height and requires the bench to '
          'go away. `--bug wide-notch` is the same experiment fired at the '
          'first row.', unit='m')
    info(2, 'bench width, mean / min / max (m)',
         (float(w_narrow.mean()), float(w_narrow.min()), float(w_narrow.max())),
         'the pocketing bar section H1 reads off the platform is this spread; '
         'it is an output of the hardness field and vanishes with it')
    info(2, 'bench width at 6x the notch height (m)', float(w_wide.mean()),
         'against %.0f m at the standard notch' % w_narrow.mean())

    # ---- K_COAST * N_STEPS is the clock, not the answer
    cs_h = B.run_coast(n_steps=B.N_COAST // 2, k_coast=2.0 * B.K_COAST)
    d_shore = float(np.abs(cs_h['x_s'] - cs['x_s']).max())
    check(3, 'K_coast and the step count are one clock',
          d_shore, 0.0, 3.0 * cs['dx'],
          'Halve the steps and double the rate and the plan-form must be the '
          'same coast. This is the coastal loop\'s version of the row that '
          'halves K_Q in the morphodynamic loop: a rate that changes the '
          'ANSWER rather than the clock is a fitted constant wearing a rate\'s '
          'name. Three cells is the tolerance because the shoreline is read by '
          'interpolation between them.', unit='m')

    # ---- the coarse fetch sweep against the full grid
    e_full = B.fetch_exposure(x, y, cs['h'], coarse=(1, 1))
    e_used = B.fetch_exposure(x, y, cs['h'])
    m = np.maximum(-cs['h'], 0.0) > 0.5
    check(3, 'the coarsened fetch sweep against the full-grid one',
          float(np.abs(e_full - e_used)[m].max()), 0.0, 0.15,
          'The sweep is run every other cross-shore cell and interpolated, '
          'because exposure is an integral over 900 m of fetch and does not '
          'have structure at the cell. Compared here against the sweep with no '
          'coarsening at all, over the wet cells that drive the notch. The '
          'tolerance is set from the coarsening and not from the answer: the '
          'coarse water mask puts the shoreline within half a coarse cell '
          '(8 m) of where the fine one puts it, and exposure crosses its whole '
          'range over about 60 m there, so a shift of that size is worth ~0.13 '
          'in the one row of cells at the waterline.',
          unit='exposure')


# ================================= 12 · the wave transform in 2-D, wave 3
# Wave 1 verified sin(theta)/c invariant to 2.2e-16 on a straight coast and said
# in the same breath that the test passes by construction. These are the rows
# that do not.
def _sec_transform2d(ctx):
    B = ctx['B']
    T = ctx['T']

    # ---- (a) the degenerate case: it must BE the 1-D transform
    xu = B.make_grid(500.0, 2.0)
    yu = np.arange(-96.0, 96.0 + 16.0, 16.0)
    hu = B.dean_bed(xu)
    h2u = np.repeat(hu[None, :], yu.size, axis=0)
    j = yu.size // 2
    t1 = B.transform(xu, hu, T, B.H0_SWELL, 0.0)
    t2 = B.transform_2d(xu, yu, h2u, T, B.H0_SWELL, 0.0)
    check(1, '2-D march = 1-D transform, normal incidence, uniform bed',
          float(np.abs(t2['H'][j] - t1['H']).max()), 0.0, 1e-12,
          'At theta = 0 the transverse divergence is identically zero and the '
          'Dally sink is integrated over the same length by both, so the two '
          'codes are doing the same arithmetic in different loops and the only '
          'difference allowed is float64 ordering. This is the row that says '
          'the plan-view scene is running the SAME wave model waves 1 and 2 '
          'measured, not a second one that resembles it.', unit='m')
    ky = t2['k'][j] * np.sin(t2['theta'][j])
    check(1, 'Snell falls out of the march: k_y invariant on a uniform bed',
          float(ky.max() - ky.min()), 0.0, 1e-14,
          'The march integrates dk_y/dx = d(k_x)/dy, the irrotationality of '
          'the wavenumber vector. On an alongshore-uniform bed the right-hand '
          'side is zero, so k_y = k sin(theta) = omega sin(theta)/c is '
          'constant -- which IS Snell. Nothing in `transform_2d` computes '
          'sin(theta) from c; the invariant is an OUTPUT here and an identity '
          'in the 1-D code.', unit='1/m')

    # ---- (b) THE REAL TEST: contours oblique to the grid
    # A plane beach rotated by phi in plan. Snell still holds, about the
    # ROTATED normal, and the march has never heard of phi.
    errs = {}
    for phi_deg in (10.0, 20.0, 30.0):
        phi = math.radians(phi_deg)
        dxo, dyo = 2.0, 4.0
        xo = np.arange(0.0, 700.0 + dxo, dxo)
        yo = np.arange(-1200.0, 1200.0 + dyo, dyo)
        X, Y = np.meshgrid(xo, yo)
        u = X * math.cos(phi) + Y * math.sin(phi)
        u_flat = 1200.0 * math.sin(phi) + 10.0
        d_o = np.clip(8.0 - 0.016 * (u - u_flat), 0.06, 8.0)
        tro = B.transform_2d(xo, yo, -d_o, T, 1.0, math.radians(15.0),
                             breaking=False)
        inv = math.sin(tro['theta'][0, 0] - phi) / tro['c'][0, 0]
        th_pred = phi + np.arcsin(np.clip(tro['c'] * inv, -1.0, 1.0))
        ramp = (d_o < 7.9) & (d_o > 0.4)
        # WHERE THIS ROW LOOKS IS PART OF THE ROW, and the first version got it
        # wrong in the direction that flatters. On a rotated bed the ramp
        # crosses each alongshore row over a different span of x, so a window
        # pinned to the GRID CENTRE samples less and less of it as phi grows --
        # at 30 deg the centre row holds no ramp at all, and the 5202 cells the
        # window did contain were the deep end, where the wave has barely
        # turned. The row read 0.030 deg and made the test look EASIER with more
        # rotation, which is backwards. Centred on the row that samples the ramp
        # most fully it reads 0.277.
        #
        # And 60 rows are cut off each alongshore edge, which is a real
        # exclusion and not a convenience: the march's transverse differences go
        # one-sided there and the error reaches 2.71 deg in the outermost rows.
        # That is a boundary artefact of an open boundary; it is reported rather
        # than hidden, and it is why the plan-view domain is a window wider than
        # the coast it is asked about.
        cover = ramp.sum(axis=1)
        j_best = int(np.argmax(cover))          # NOT `j`: that name is the
        win = np.zeros_like(ramp)               # uniform-bed row index above,
        win[max(j_best - 100, 60):              # and clobbering it cost this
            min(j_best + 100, yo.size - 60), :] = True   # section an IndexError
        m = ramp & win
        errs[phi_deg] = math.degrees(float(np.abs(tro['theta'] - th_pred)[m].max()))
    check(1, 'Snell about a ROTATED normal, contours oblique to the grid',
          [errs[10.0], errs[20.0], errs[30.0]], [0.0, 0.0, 0.0], 0.50,
          'The first refraction test in this project that does not pass by '
          'construction. The bed is a plane beach whose contours run at 10, 20 '
          'and 30 degrees to the grid; the exact answer is Snell taken about '
          'the rotated normal, and the march is given the rotation nowhere -- '
          'it integrates the wavenumber\'s irrotationality on the grid axes. '
          '0.5 deg is 1.6x the worst measured error, and the error is the '
          'first-order upwind difference in y rather than the physics: it does '
          'not fall when the ray step is refined and it does fall with dy.',
          unit='deg')
    info(1, 'the same, per rotation (deg)',
         (errs[10.0], errs[20.0], errs[30.0]),
         'against 0.000 deg at zero rotation, where the test is an identity '
         'again -- the straight-coast case wave 1 measured at 2.2e-16')

    # ---- (c) obliquity: the 1-D form decays over dx, the divergence over ds
    gap = []
    for deg in (0.0, 20.0, 40.0):
        th0 = math.radians(deg)
        a = B.transform(xu, hu, T, B.H0_SWELL, th0)
        b = B.transform_2d(xu, yu, h2u, T, B.H0_SWELL, th0)
        gap.append(float(np.abs(b['H'][j] - a['H']).max()))
    check(1, 'the obliquity gap vanishes at normal incidence', gap[0], 0.0,
          1e-12,
          'chapter 12 (and this file\'s 1-D transform after it) marches '
          'F = E c_g cos(theta) with dF/dx = -(K/d)(F - F_s), applying the '
          'Dally rate per unit CROSS-SHORE distance. A divergence applies it '
          'per unit RAY distance, ds = dx/cos(theta). The two are the same '
          'statement only at theta = 0, and this row is that identity; the '
          'INFO below is the size of the disagreement where it is not.',
          unit='m')
    info(1, 'obliquity gap in H at theta_0 = 0 / 20 / 40 deg (m)', gap,
         'small BECAUSE refraction is doing its job -- the wave has turned to '
         '6.6 deg by the time it breaks, and cos of that is 0.994. On a coast '
         'steep enough to break before it turns the same term is worth per '
         'cent, and a 1-D transform written from the chapter would not carry '
         'it. Measured, reported, and NOT patched into the 1-D file, which is '
         'what waves 1 and 2 measured with.')

    # ---- (d) the energy flux is monotone shoreward (chapter 12's own item)
    bay = B.run_bay(dx=4.0, n_steps=300, dt=6000.0)
    ctx['bay'] = bay
    tr = bay['tr']
    F = tr['Phi'] * np.cos(tr['theta'])
    tot = F.sum(axis=0) * bay['dy']
    rise = float(np.diff(tot).max()) / float(tot[0])
    check(1, 'the wave energy flux never increases shoreward', rise, 0.0, 1e-4,
          'Chapter 12 lists this as a verification item and notes that the '
          '`min(shoal, gamma d)` cap violates it while a marched transform '
          'cannot. IT IS A DIFFERENT STATEMENT IN 2-D and the first version of '
          'this row got it wrong: per CELL the flux may legitimately RISE, '
          'because refraction focuses one ray tube at the expense of its '
          'neighbour -- measured at 0.7 per cent of the peak over the bar, '
          'which is the focusing bar section B asks for ("Curved contours '
          'focus"), not an energy leak. What may not rise is the flux summed '
          'across the coast, and it does not: 7e-5 of the offshore value, '
          'which is the open alongshore boundary and float64.', unit='fraction')
    info(1, 'per-cell flux rise, as a fraction of the peak',
         float((np.diff(F, axis=1) * (tr['d_raw'][:, 1:] > 0.4)).max()
               / F.max()),
         'refraction focusing, and the reason the 1-D form of this row cannot '
         'be carried into a plan view unchanged')

    # ---- (e) an independent integrator over the bay's own curved contours
    x, y = bay['x'], bay['y']
    th_start = float(tr['theta'][0, 0])
    d_filt = -tr['d']                          # the field the march READ
    def _ray_gap(bed):
        out = []
        for y0 in np.linspace(-500.0, 500.0, 11):
            r = B.trace_ray(x, y, bed, T, 2.0 * bay['dx'], y0, th_start,
                            ds=2.0, n_max=3000)
            r = r[r[:, 0] < x[-1] - bay['dx']]
            ii = np.clip((r[:, 0] - x[0]) / bay['dx'], 0, x.size - 1.001)
            jj = np.clip((r[:, 1] - y[0]) / bay['dy'], 0, y.size - 1.001)
            i0 = ii.astype(int)
            j0 = jj.astype(int)
            tx, ty = ii - i0, jj - j0
            def _bi(A):
                return (A[j0, i0] * (1 - tx) * (1 - ty)
                        + A[j0, i0 + 1] * tx * (1 - ty)
                        + A[j0 + 1, i0] * (1 - tx) * ty
                        + A[j0 + 1, i0 + 1] * tx * ty)
            m = _bi(tr['d']) > 0.6
            if m.sum() > 10:
                out.append(float(np.abs(r[:, 2] - _bi(tr['theta']))[m].max()))
        return np.array(out)
    g_same = _ray_gap(d_filt)
    g_mixed = _ray_gap(bay['h'])
    check(3, 'RK2 ray tracer against the 2-D march, over the bay',
          float(g_same.max()), 0.0, 0.06,
          'Two integrators with no arithmetic in common: `trace_ray` steps '
          'dtheta/ds = (sin.dc/dx - cos.dc/dy)/c along a path, the march '
          'integrates dk_y/dx = dk_x/dy across a grid, and neither contains '
          'Snell. On the STRAIGHT coast they agree to 1.6e-3 rad; over the '
          'bay\'s curved contours the gap is 0.038 rad and it is the '
          'alongshore grid, not either integrator -- refining ds by four does '
          'not move it. 0.06 rad is 1.6x the measured worst case.', unit='rad')
    info(3, 'ray-vs-march gap: same field, then mixed fields (rad)',
         (float(g_same.max()), float(g_mixed.max())),
         'THE SAME ERROR CLASS AGAIN, and in 2-D it is worth a factor of six. '
         'The march reads the filtered depth; `trace_ray` was handed the raw '
         'bed, and the disagreement went from 0.038 to 0.226 rad -- 13 degrees '
         'of apparent refraction error that is entirely the two fields. The '
         'straight-coast version of this row could not have shown it, because '
         'a filter along x alone leaves a plane bed plane.')

    # ---- (f) the crest turns onto the contour, and by how much
    a_w, m_w = B.contour_alignment(tr, field='wave')
    a_b, m_b = B.contour_alignment(tr, field='bed')
    brk = tr['brk']
    al = float(np.abs(a_w[m_w & brk]).mean())
    tr_no = B.transform_2d(x, y, bay['h'], T, B.H0_SWELL, B.THETA0_SWELL,
                           refraction=False)
    a_n, _ = B.contour_alignment(tr_no, field='wave')
    al_no = float(np.abs(a_n[m_w & brk]).mean())
    check(2, 'refraction halves the crest-to-contour angle at breaking',
          al / al_no, 0.0, 0.75,
          'Bar section J: "The breaking lines bend to stay parallel to the '
          'shore around the whole curve ... A render whose surf lines stay '
          'straight while the shore curves has failed a criterion a layman '
          'could catch." This is that criterion as a number: the angle between '
          'the crest and the local depth contour, with the transverse '
          'refraction term on and off, both angles measured against the SAME '
          'depth field. Not zero and it should not be -- Snell only takes '
          'sin(theta) to zero in the limit.', unit='ratio')
    info(2, 'crest-to-contour angle at breaking: refracting, frozen (deg)',
         (al, al_no), 'and the shore-normal itself swings through %.0f deg '
         'across this bay, so a crest that ignored the contours would carry '
         'the whole of that swing as error'
         % float(np.ptp(np.degrees(np.arctan(np.gradient(bay['x_s'], bay['dy']))))))
    info(2, 'the same angle measured against the RAW bed (deg)',
         float(np.abs(a_b[m_b & brk]).mean()),
         'the mixed-field form of the same statistic. `contour_alignment` '
         'takes `field` with no default for the reason chapter 12 now carries '
         'as a general finding, and `--bug alignment-mixed-fields` puts the '
         'wrong pairing back.')

    # ---- (g) the regression, against the closed form
    reg = B.crest_azimuth_regression(tr, d_lo=1.0, d_hi=2.4)
    cf = float(B.refraction_slope_closed_form(tr, 1.7, 8.0))
    reg_no = B.crest_azimuth_regression(tr_no, d_lo=1.0, d_hi=2.4)
    between(1, 'crest azimuth regressed on contour azimuth: the slope',
            reg['slope'], 0.15, cf,
            'Slope 0 is a crest that ignores the shore; slope 1 is a crest '
            'locked to the contour. The closed form bounds it from above: '
            'differentiating Snell about a contour at azimuth beta gives '
            'd(theta)/d(beta) = 1 - c(d)/c(d_ref) = %.3f here, with d_ref the '
            '8 m shelf where this bathymetry stops being alongshore-uniform. '
            'The measured slope must sit BELOW that, because the bay\'s '
            'contours turn gradually rather than all at the shelf edge, and '
            'above zero, because the crests do turn.' % cf, unit='slope')
    info(1, 'regression slope, R^2, and the closed-form bound',
         (reg['slope'], reg['r2'], cf),
         'and the same regression with the transverse refraction term removed '
         'gives a slope of %.4f -- a crest that stays where it entered'
         % reg_no['slope'])
    check(1, 'with refraction frozen the slope collapses to zero',
          reg_no['slope'], 0.0, 0.02,
          'The control for the row above. `refraction=False` keeps every other '
          'term -- shoaling, the Dally decay, the transverse divergence -- and '
          'freezes the wave direction at the offshore boundary value, which is '
          'exactly the render bar section J says a layman could catch.',
          unit='slope')


# ================================================= 13 · the bar in plan, wave 3
def _sec_bay(ctx):
    B = ctx['B']
    bay = ctx.get('bay') or B.run_bay(dx=4.0, n_steps=300, dt=6000.0)
    x, y, h, hi, tr = (bay['x'], bay['y'], bay['h'], bay['h_init'], bay['tr'])

    # ---- the initial bed has no bar in it anywhere
    worst = 0.0
    for j in range(y.size):
        d0 = -hi[j][hi[j] < -0.3]
        if d0.size > 4:
            worst = max(worst, float(np.diff(d0).max()))
    check(1, 'the plan bed starts monotone in the cross-shore, every row',
          worst, 0.0, 0.02,
          'The 1-D loop was measured against a monotone Dean ramp and the plan '
          'loop must be too: if the composed bed carried a ridge anywhere, a '
          '"bar" in the answer could be the join between the coastal loop and '
          'the equilibrium ramp rather than a landform. It carried one on the '
          'first attempt -- a 1.8 m step where the bench met the ramp, which '
          'the transform duly broke the whole wave field on, 200 m seaward of '
          'any surf.', unit='m per cell')

    # ---- a bar in every row, and chapter 12's crest depth in ONE field
    ba = B.bar_alongshore(x, y, h, hi)
    n_bar = int((ba['amp'] > 0.5).sum())
    check(1, 'a bar grows in every alongshore row', n_bar, y.size, 0.0,
          'Nothing in the plan bed says "bar here" and nothing in the loop '
          'stamps an alongshore rhythm -- wave 1\'s figure did, and this wave '
          'removes it. Half a metre of relief cannot be a rounding artefact.',
          unit='rows')
    ratio = B.bay_crest_ratio(bay, field='wave')
    ratio_mixed = B.bay_crest_ratio(bay, field='bed')
    ok = ~np.isnan(ratio)
    check(2, 'd_bar ~ H_b/gamma in the bay, one field, every row',
          float(np.nanmean(ratio)), 1.0, 0.12,
          'Chapter 12\'s central quantitative prediction, now asked of 89 '
          'independent cross-shore profiles that the coastal loop shaped '
          'differently from one another. Both terms come from the depth the '
          'wave saw. 12 per cent is twice the 6 per cent the 1-D row allows, '
          'because this grid is 4 m where that one is 1 m and the relation '
          'is met to 5 per cent on coarse grids by chapter 12\'s own '
          'measurement.', unit='ratio')
    info(2, 'crest-depth ratio across the bay: mean, sd, min, max',
         (float(np.nanmean(ratio)), float(np.nanstd(ratio)),
          float(np.nanmin(ratio)), float(np.nanmax(ratio))),
         'and the MIXED-field form of the same statistic has a mean of %.3f. '
         'In 1-D that error was worth 0.08 of the ratio; here it is worth '
         '0.37, because the filter is 6 m on this grid and the bar is 25 m '
         'wide. The trap gets WORSE in 2-D, not better.'
         % float(np.nanmean(ratio_mixed)))

    # ---- does the bar vary alongshore? a measurement, not an imposition
    info(2, 'bar crest depth alongshore: mean, sd, min, max (m)',
         (float(np.nanmean(ba['d'])), float(np.nanstd(ba['d'])),
          float(np.nanmin(ba['d'])), float(np.nanmax(ba['d']))),
         'the brief asked whether the nearshore profile varies with the local '
         'exposure and by how much, rather than asking for it to vary. It '
         'does: the crest sits in %.2f m of water at one station and %.2f m '
         'at another, on ONE offshore sea state, because the coastal loop gave '
         'each station a different shoreface.'
         % (float(np.nanmin(ba['d'])), float(np.nanmax(ba['d']))))
    off = ba['x'] - bay['x_s']
    info(2, 'bar offset from the local shoreline: mean, sd (m)',
         (float(np.nanmean(off)), float(np.nanstd(off))),
         'the bar follows the shoreline round the bay rather than sitting at '
         'one cross-shore distance: its spread about a constant offset is '
         '%.0f m against a shoreline that itself swings %.0f m'
         % (float(np.nanstd(off)), float(np.ptp(bay['x_s']))))

    # ---- the surf line follows the shore, and that is the by-eye criterion
    sl = B.surf_line_x(tr)
    good = ~np.isnan(sl)
    rr = float(np.corrcoef(sl[good], bay['x_s'][good])[0, 1])
    check(2, 'the outer surf line follows the shoreline round the bay', rr,
          1.0, 0.25,
          'The plainest form of bar section J\'s criterion: the most seaward '
          'breaking onset in each alongshore row, correlated against the '
          'shoreline position of that row. A surf line that ignored the bay '
          'would be a straight line across a curved shore and this number '
          'would be near zero.', unit='r')
    info(2, 'surf line: range, and its spread about a constant offset (m)',
         (float(np.nanmax(sl) - np.nanmin(sl)),
          float(np.nanstd(sl - bay['x_s']))),
         'against a shoreline range of %.0f m' % float(np.ptp(bay['x_s'])))

    # ---- Exner still conserves sand in two dimensions
    dv = float((h - hi).sum()) * bay['dx'] * bay['dy']
    check(1, 'the 2-D Exner step conserves sand', dv - bay['edge'], 0.0,
          1e-6 * max(abs(dv), 1.0),
          'The 1-D row that guards this found a 1.83 m^2 leak in an earlier '
          'version of the shallow gate. In 2-D there is a second way to leak '
          '-- the alongshore flux at the domain edges. The answer there is NOT a '
          'wall: the domain is a window on a longer coast and sand really does '
          'cross those boundaries. So the row closes the book instead of '
          'pretending it balances -- the boundary term of the scheme actually '
          'used is accumulated step by step inside `evolve_2d` and subtracted, '
          'and what is left is round-off. The raw change is printed beside it.',
          unit='m^3')
    info(1, 'sand: net change, and the flux through the open alongshore edges',
         (dv, bay['edge']),
         'the two agree, which is the statement; the second number is real '
         'transport and not a leak')

    # ---- and the grid, because wave 2 was caught by exactly this
    b4 = B.run_bay(dx=4.0, n_steps=75, dt=6000.0)
    b2 = B.run_bay(dx=2.0, n_steps=300, dt=1500.0)
    r4 = float(np.nanmean(B.bay_crest_ratio(b4, field='wave')))
    r2 = float(np.nanmean(B.bay_crest_ratio(b2, field='wave')))
    check(3, 'the crest-depth ratio at dx = 4 m against dx = 2 m', r2, r4,
          0.10,
          'Both runs held at 125 hours of the same swell, with dt set from the '
          'same diffusion bound dt < dx^2/(2 D_eff) rather than kept fixed -- '
          'the mistake chapter 12 now records as the reason its own refinement '
          'table has a hole. The same-field ratio is the quantity compared, '
          'because the raw-bed form measures the filter and the filter is '
          '1.5 dx.', unit='ratio')
    info(3, 'crest-depth ratio at dx = 4 m, then 2 m', (r4, r2),
         'the 1-D loop reads 0.953-0.994 over dx = 2.0 to 0.25 m')


def run_suite():
    del ROWS[:]
    B = BCH
    ctx = dict(B=B, T=B.T_SWELL, omega=2.0 * math.pi / B.T_SWELL,
               x=B.make_grid())
    for fn, label in ((_sec_waves, 'linear theory, shoaling, refraction, '
                                   'radiation stress, sediment'),
                      (_sec_bar, 'the bar and the second breaking line'),
                      (_sec_states, 'beach state, Iribarren, the sun'),
                      (_sec_coast, 'the coast in plan'),
                      (_sec_transform2d, 'the wave transform in 2-D'),
                      (_sec_bay, 'the bar in plan')):
        guard(fn, label, ctx)
    return ctx.get('sc')


# --------------------------------------------------------------------- output
def report(title=''):
    n_pass = sum(r.status == 'PASS' for r in ROWS)
    n_fail = sum(r.status == 'FAIL' for r in ROWS)
    n_info = sum(r.status == 'INFO' for r in ROWS)
    n_open = sum(r.status == 'OPEN' for r in ROWS)
    n_err = sum(r.status == 'ERROR' for r in ROWS)
    print('=' * 100)
    if title:
        print(title)
    print('%-4s %-58s %14s %14s %8s' % ('tier', 'row', 'expected', 'measured',
                                        'status'))
    print('-' * 100)
    for r in ROWS:
        print('%-4s %-58s %14s %14s %8s'
              % (r.tier, r.name[:58], _fmt(r.exp), _fmt(r.got), r.status))
        if VERBOSE and r.why:
            for ln in _wrap(r.why, 92):
                print('       %s' % ln)
    print('-' * 100)
    print('%d pass / %d FAIL / %d ERROR / %d open / %d info'
          % (n_pass, n_fail, n_err, n_open, n_info))
    for r in ROWS:
        if r.status == 'ERROR':
            print('ERROR: %s -- %s' % (r.name, r.got))
    for r in ROWS:
        if r.status == 'OPEN':
            print('OPEN: %s' % r.name)
            for ln in _wrap(r.why, 92):
                print('      %s' % ln)
    return n_fail + n_err


def _wrap(s, w):
    out, line = [], ''
    for word in s.split():
        if len(line) + len(word) + 1 > w:
            out.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    if line:
        out.append(line)
    return out


def _fail_names():
    return [r.name for r in ROWS
            if r.status in ('FAIL', 'ERROR')]


if __name__ == '__main__':
    t0 = time.time()
    if '--bugs' in sys.argv:
        run_suite()
        base = set(_fail_names())
        print('clean run: %d pass / %d FAIL'
              % (sum(r.status == 'PASS' for r in ROWS), len(base)))
        print()
        print('%-22s %s' % ('bug reintroduced', 'rows that FAIL'))
        print('-' * 100)
        import importlib
        for name, patch in BUGS.items():
            importlib.reload(BCH)
            patch(BCH)
            try:
                run_suite()
                caught = [n for n in _fail_names() if n not in base]
            except Exception as exc:                      # a crash is a catch
                caught = ['(raised %s: %s)' % (type(exc).__name__,
                                               str(exc)[:60])]
            print('%-22s %d  %s' % (name, len(caught),
                                    '; '.join(c[:70] for c in caught[:4])))
        importlib.reload(BCH)
        sys.exit(0)
    if BUG:
        BUGS[BUG](BCH)
    run_suite()
    n_fail = report('BEACH SUITE -- %s' % (('bug: ' + BUG) if BUG else 'clean'))
    print('%.1f s' % (time.time() - t0))
    sys.exit(1 if (n_fail and not BUG) else 0)
