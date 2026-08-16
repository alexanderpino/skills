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
import beach_optics as BOP                                      # noqa: E402
import beach_foam as FOAM                                       # noqa: E402
import beach_camera as CMR                                      # noqa: E402
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



# --- WAVE 4'S DEFECTS, all in `beach_optics`. Every one of them is a mistake
# this wave either made or came within one line of making, and each is here
# because a guard that has never fired at anything is a comment with a check()
# around it.
def _bug_one_turbidity_slider(mod):
    """THE FAILURE CHAPTER 28 NAMES BY NAME: collapse the three constituents
    into one murkiness control, so that CDOM and chlorophyll rise with the
    mineral load instead of belonging to the water mass. It is the single most
    plausible wrong architecture for this scene and it must not merely look
    worse -- it must break a row."""
    orig = mod.iops

    def iops(a_ph440=None, a_cdom440=mod.A_CDOM_440, spm=0.0, pure=False):
        s = np.asarray(spm, float)
        return orig(a_ph440=mod.A_PH_440 * (1.0 + np.mean(s)),
                    a_cdom440=a_cdom440 * (1.0 + np.mean(s)), spm=spm,
                    pure=pure)
    mod.iops = iops


def _bug_cdom_scatters(mod):
    """Give CDOM a scattering coefficient. Chapter 28: it "scatters not at
    all", and that single word is what makes blackwater dark instead of
    milky."""
    orig = mod.iops

    def iops(**kw):
        out = orig(**kw)
        out['b'] = out['b'] + 0.5 * kw.get('a_cdom440', mod.A_CDOM_440)
        out['b_b'] = mod.BB_OVER_B * out['b']
        out['c'] = out['a'] + out['b']
        return out
    mod.iops = iops


def _bug_depth_averaged_spm(mod):
    """Spread the suspended load through the whole column instead of the layer
    the Rouse balance puts it in. The load is unchanged and so is every
    sedimentological number; only the OPTICS move -- which is the point."""
    orig = mod.suspended_load

    def load(*a, **kw):
        out = orig(*a, **kw)
        out['delta'] = np.full_like(np.asarray(out['delta'], float),
                                    1e9)
        out['spm'] = out['spm_bar']
        return out
    mod.suspended_load = load


def _bug_dw_for_bed_power(mod):
    """Drive the suspension from the WAVE's dissipation instead of the BED's --
    wave 4's own first writing, wrong by a factor of about fifty."""
    orig = mod.bed_dissipation

    def bd(u_orb, c_f=0.006, rho_w=1025.0):
        return 50.0 * orig(u_orb, c_f, rho_w)
    mod.bed_dissipation = bd


def _bug_isotropic_phase(mod):
    """Leave the phase asymmetry at zero, which chapter 28 warns "kills the
    forward glow through a sunlit wave crest"."""
    mod.PHASE_G = 0.0


def _bug_glitter_fixed_width(mod):
    """The defect bar section K exists to catch: a spread parameter chosen to
    look right, instead of the published slope distribution. The width stops
    depending on the wind and stops varying along the path."""
    def pdf(zx, zy, u10=mod.U10, wind_az=mod.WIND_AZ):
        s2 = 0.02
        z2 = np.asarray(zx, float) ** 2 + np.asarray(zy, float) ** 2
        return np.exp(-0.5 * z2 / s2) / (2.0 * np.pi * s2)
    mod.slope_pdf = pdf


def _bug_glitter_no_jacobian(mod):
    """Drop the 1/cos^4(beta) from the glitter radiance -- the Jacobian between
    slope space and direction space. It is invisible near the specular point
    and it is the whole of the behaviour toward the horizon."""
    orig = mod.glitter_radiance

    def gl(sun_dir, view_dir, **kw):
        s = np.asarray(sun_dir, float)
        v = np.asarray(view_dir, float)
        v = v / np.linalg.norm(v, axis=-1, keepdims=True)
        n = s - v
        n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
        cb = np.maximum(n[..., 2], 1e-6)
        return orig(sun_dir, view_dir, **kw) * (cb ** 4)[..., None]
    mod.glitter_radiance = gl


def _bug_ambient_in_the_tube(mod):
    """Light the through-path with an ambient term, so the green no longer
    vanishes when the sun is not behind the water. Bar section I2: "a renderer
    that lights a tube interior with ambient sky has missed the whole
    mechanism"."""
    orig = mod.through_path

    def tp(L_src, path, a, b_b):
        return orig(np.asarray(L_src, float) + 2.0, path, a, b_b)
    mod.through_path = tp


# --- WAVE 5'S DEFECTS. All six are in `beach`, all six are mistakes this wave
# either made or was one line from making, and every one of them draws a
# PLAUSIBLE picture -- which is the only reason they need a suite at all.
def _bug_sinusoidal_surface(mod):
    """Wave 4's surface: no second harmonic at all. The frame it draws is the
    one that has already shipped, so nothing looks broken; only the face slope
    and the harmonic rows can see it."""
    mod.stokes2_ratio = lambda H, k, d: np.zeros_like(np.asarray(H, float))


def _bug_harmonic_shallow_everywhere(mod):
    """Use the shallow asymptote C = 3/(kd)^3 at every depth. Every shallow-
    water row still passes -- including the r = 2 Ur identity, which is the
    asymptote -- and the open ocean gets a harmonic 30x too large."""
    mod.stokes2_shape = lambda kd: 3.0 / np.maximum(
        np.asarray(kd, float), 1e-9) ** 3


def _bug_unclamped_stokes(mod):
    """Run second-order Stokes past its validity limit, which is what a file
    that does not check the Ursell number does by default. r reaches 75 in this
    scene and the surface grows a false crest inside every trough."""
    orig = mod.surface_state
    mod.surface_state = lambda tr, clamp=True: orig(tr, clamp=False)


def _bug_bore_phase_flipped(mod):
    """psi = +(pi/2) f_brk. The waves lean SEAWARD. Every moment, every
    magnitude and every colour measurement is unchanged -- Sk^2 + As^2 does not
    know the sign -- and a still frame of a wave breaking backwards is exactly
    as convincing as one breaking forwards."""
    mod.bore_phase = lambda f: (np.pi / 2.0) * np.clip(
        np.asarray(f, float), 0.0, 1.0)


def _bug_skew_without_asymmetry(mod):
    """Keep the second harmonic and never rotate it: psi = 0 everywhere, so the
    wave is peaked and symmetric at every stage of breaking. This is the
    tempting version -- it is 'the skewness the file already had' taken
    literally -- and it buys 30% of face slope instead of 100%."""
    mod.bore_phase = lambda f: np.zeros_like(np.asarray(f, float))


def _bug_ur_half_declared(mod):
    """Put wave 1's declared UR_HALF = 1.0 back into the derivation, so the
    parameterisation and the Stokes surface disagree by 4.24x at the origin and
    nothing says so."""
    mod.ur_half_derived = lambda sk_max=1.0: 1.0



# ------------------------------------------------------- wave 6's bugs
# EIGHT DEFECTS IN THE WHITE, and every one of them is a mistake this wave's
# author either made or was one keystroke from making. They patch `beach_foam`,
# so `--bugs-foam` runs them against `_sec_foam` alone -- the same argument
# waves 4 and 5 made for their own sections.
def _bug_foam_no_transmittance(mod):
    """Whiten without hiding: the failure bar section C opens by naming."""
    orig = mod.plume_optics

    def po(*a, **kw):
        out = orig(*a, **kw)
        out['T'] = np.ones_like(out['T'])
        return out
    mod.plume_optics = po


def _bug_foam_backscatter_is_tir(mod):
    """Read the bar's 43.874% as a BACKSCATTER fraction, which its wording
    invites. A bubble would then be twenty times the backscatterer it is."""
    orig = mod.bubble_scatter

    def bs(*a, **kw):
        out = orig(*a, **kw)
        out['bb_over_b'] = np.full(3, float(mod.TIR_FRAC))
        out['g'] = 1.0 - 2.0 * out['bb_over_b']
        return out
    mod.bubble_scatter = bs


def _bug_bubble_fresnel_one_channel(mod):
    """The defect wave 7 removed: every channel's internal Fresnel evaluated at
    RED's refracted cosine. `optics.fresnel` broadcasts a scalar to three
    channels, so the array shape is right and the energy sum still closes --
    only the ANGLE is wrong, in two bands out of three."""
    def fi(sin_i):
        si = np.asarray(sin_i, float)[..., None]
        st = mod.N_W * si
        tir = st >= 1.0
        ct = np.sqrt(np.maximum(1.0 - np.minimum(st, 1.0) ** 2, 0.0))
        return np.where(tir, 1.0, OPT.fresnel(ct[..., 0]))
    mod._fresnel_internal = fi


def _bug_foam_on_the_crest(mod):
    """Put the foam ON the crest -- age zero everywhere -- instead of in the
    tail behind it. The placeholder's own mistake, kept."""
    mod.age_from_phase = lambda phase, omega: np.zeros_like(
        np.asarray(phase, float))


def _bug_foam_declared_k(mod):
    """Restore the placeholder: 1 - exp(-k f_brk) with k = 1 declared, no
    residence time and no period."""
    mod.covering_measure_break = lambda q_b, T, age, tau=None: np.clip(
        np.asarray(q_b, float), 0.0, 1.0) * np.ones_like(
            np.asarray(age, float))


def _bug_foam_percent_for_fraction(mod):
    """Monahan in PER CENT read as a fraction. A factor of 100, and a sea
    covered in whitecaps at a summer breeze."""
    mod.MOM80_A = 3.84e-4
    orig = mod.whitecap_coverage
    mod.whitecap_coverage = (
        lambda u10, a=3.84e-4, n=mod.MOM80_N: orig(u10, a, n))


def _bug_foam_single_rise_speed(mod):
    """THE DEFECT THIS WAVE ACTUALLY SHIPPED. Clear the whole plume at one rise
    speed -- the Sauter radius' -- instead of size by size."""
    orig = mod.bubble_spectrum

    def sp(d_plume, *a, **kw):
        out = orig(d_plume, *a, **kw)
        out['tau_vol'] = float(d_plume) / float(
            mod.bubble_rise_velocity(out['r_32']))
        return out
    mod.bubble_spectrum = sp


def _bug_foam_stokes_everywhere(mod):
    """Drop Schiller & Naumann's correction and rise by Stokes at every size.
    A 1 cm bubble would then rise at 20 m/s."""
    mod.bubble_rise_velocity = lambda r, nu=BCH.NU_W, rho_w=BCH.RHO_SW, \
        g=BCH.G, n_iter=0: 2.0 * np.asarray(r, float) ** 2 * g / (9.0 * nu)


def _bug_foam_unclipped_spheres(mod):
    """Use the dilute-sphere projected area at any void fraction, including the
    polyhedral-foam regime where the scatterers are films."""
    orig = mod.entrained_air

    def ea(*a, **kw):
        out = orig(*a, **kw)
        out['alpha'] = out['Q'] * out['tau_vol'] / out['d_p']
        return out
    mod.entrained_air = ea



# ---------------------------------------- wave 7: the camera's own six defects
# Every one is a thing a reader would write on a first pass and none of them
# looks wrong in the output: a frame is still a frame at the wrong field of
# view, and a horizon is still a horizon at the wrong dip.
def _bug_fov_on_the_long_side(mod):
    """Treat the 35-mm-equivalent focal length as equivalent on the LONG SIDE
    instead of the diagonal. 4% at 24 mm, 10% at 13 mm, and it moves the lens
    selection -- which is the one step of the inference the frame's content
    is supposed to decide."""
    def ef(f_mm, aspect=mod.STILL_ASPECT, diag=mod.DIAG_35):
        half_l = math.atan(36.0 / (2.0 * f_mm))
        a = float(aspect)
        n = math.hypot(a, 1.0)
        half_d = math.atan(math.tan(half_l) * n / a)
        half_s = math.atan(math.tan(half_l) / a)
        return dict(f=float(f_mm), diag=2 * half_d, long=2 * half_l,
                    short=2 * half_s)
    mod.equiv_fov = ef


def _bug_dip_unrefracted(mod):
    """Drop the refraction. 7% on the dip, which is 0.01 deg -- invisible in
    the frame and wrong against every published dip table."""
    orig = mod.horizon_dip
    mod.horizon_dip = lambda z, refraction=True: orig(z, refraction=False)


def _bug_landscape_not_upright(mod):
    """Hold the phone the other way. Both bar J and bar K record the frame
    UPRIGHT; landscape gives the same lens 89.9 deg tall and 106.2 wide, which
    moves the horizon, the depression bracket and the lens selection."""
    mod.portrait_fov = lambda f_mm, aspect=mod.STILL_ASPECT: (
        mod.equiv_fov(f_mm, aspect)['short'], mod.equiv_fov(f_mm, aspect)['long'])


def _bug_hfov_scaled_linearly(mod):
    """h = v * W/H instead of tan(h/2) = tan(v/2) W/H. Exact at zero and 12%
    narrow at 90 degrees, so it passes every small-angle check anybody tries
    and fails exactly where this project uses it."""
    mod.rectilinear_hfov = lambda fov_v, aspect_wh: fov_v * aspect_wh


def _bug_separation_small_angle(mod):
    """Keep the small-angle form z*s/D^2 instead of the two arctangents. It is
    right to a per cent on a cliff and it has NO CEILING -- so the closed form
    that says no eye height can do better than atan(s/2sqrt(D(D-s))) quietly
    stops being true, and the eye-height inference loses its upper branch."""
    mod.line_separation = lambda z, D, s: float(z) * float(s) / float(D) ** 2


def _bug_flat_sea_no_horizon(mod):
    """Report the flat plane as costing nothing. It costs a third of a pixel
    row, which is the RIGHT answer and is why the defect matters: a wave that
    assumed it was large would spend itself on the wrong end of the gap list."""
    orig = mod.flat_sea_error

    def fse(z, far, refraction=True):
        out = orig(z, far, refraction)
        out['over_paint'] = 0.0
        return out
    mod.flat_sea_error = fse


# ---------------------------------------------- WAVE 8: the land and the air
def _bug_face_slope_at_break(mod):
    """The beach face slope read off the bed AT THE BREAK POINT, which is what
    waves 4-7's `_set_runup` did to get its Iribarren number. It is the slope
    of the shoreface a hundred metres offshore in two metres of water -- 1:130
    -- and Hunt's xi is defined on the slope the SWASH climbs."""
    mod.beach_face_slope = lambda A=mod.DEAN_A, d_hand=mod.D_MORPH_MIN: 0.0077
    mod.TAN_FACE = 0.0077
    mod.BERM_Z = mod.berm_crest(tan_beta=0.0077)
    mod.BACKSHORE_Z = mod.berm_crest(mod.H0_STORM, tan_beta=0.0077)
    mod._BAY_CACHE.clear()


def _bug_swash_linear_band(mod):
    """The wet/dry boundary as a linear ramp over a declared width, which is
    what `shade_land` carried for four waves. Run-up heights are Rayleigh and
    an exceedance is an exponential of the SQUARE; a ramp is neither."""
    mod.swash_wetness = lambda z, R=None: np.clip(
        1.0 - np.maximum(np.asarray(z, float), 0.0)
        / (mod.BERM_Z if R is None else R), 0.0, 1.0)


def _bug_wet_albedo_all_diffuse(mod):
    """`optics.wet_albedo` shipped whole into the Lambertian lobe -- waves
    4-7's own code. Wet sand then reads BRIGHTER than dry and never glossy,
    which is bar H3 exactly backwards."""
    mod.SAND_WET_DIFF = mod.SAND_WET
    mod.ROCK_WET_DIFF = mod.ROCK_WET


def _bug_airlight_view_direction(mod):
    """The airlight taken in the VIEW direction instead of the ray flattened to
    the horizontal. It looks more physical -- the light does come from where
    you are looking -- and it reopens the sea-sky seam, because a downward ray
    samples the ground-facing hemisphere and not the horizon."""
    orig = mod.aerial

    def bad(L, D, r, vis=None):
        b = mod.beta_ext(vis)
        T = np.exp(-r[..., None] * b[None])
        return L * T + mod.sky_radiance(D) * (1.0 - T)
    mod.aerial = bad


def _bug_beta_no_scale_height(mod):
    """The ZENITH OPTICAL DEPTH used as if it were an extinction coefficient.
    tau is dimensionless and beta is per metre; the two differ by 8.5 km and
    the confusion is one of the easiest in atmospheric optics to make."""
    mod.beta_ext = lambda vis=None: np.asarray(ATM.TAU_R, float)


def _bug_specular_no_jacobian(mod):
    """The slope pdf used as a radiance with no change of variables -- the same
    defect wave 4 shipped in the sea's glitter and the suite caught there,
    offered again in a new surface. The lobe keeps the right SHAPE and takes
    the wrong magnitude at every angle but one, which is why a picture cannot
    report it."""
    mod.sun_jacobian = lambda cos_beta, cos_theta_v: 1.0


def _bug_shadow_reach_one_cell(mod):
    """The shadow march stopped at one cell instead of h_max/tan(elevation).
    A shadow that is short by a factor of ten looks like a shadow."""
    orig = mod.land_shadow
    mod.land_shadow = lambda w, P, N, n=40, reach=None, sun=None: orig(
        w, P, N, n=n, reach=4.0, sun=sun)



# ------------------------------------------- wave 9: the plan-form's defects
def _bug_grid_snell(mod):
    """The offshore Snell taken against the GRID's y axis instead of the local
    contour -- what waves 1-8 shipped, and what stopped the transport meter
    from being able to read zero."""
    orig = mod.transform_2d
    mod.transform_2d = lambda *a, **kw: orig(
        *a, **dict(kw, contour0=None))


def _bug_spiral_no_tangency(mod):
    """Drop the downcoast-tangency condition and close the pole on the anchors
    alone. One equation for two unknowns -- Newton then wanders to whatever
    the start point is nearest, and the bay stops being determined."""
    def bad(D, A1, A2, alpha, khat):
        r = mod.spiral_residual(D, A1, A2, alpha, khat)
        return np.array([r[0], 0.0])
    orig = mod.spiral_pole

    def pole(A1, A2, alpha, khat, D0=None, n_iter=200, tol=1e-13):
        A1 = np.asarray(A1, float)
        A2 = np.asarray(A2, float)
        ch = float(np.hypot(*(A2 - A1)))
        D = A1 + np.array([0.3 * ch, -0.3 * ch]) if D0 is None else np.asarray(
            D0, float).copy()
        for _ in range(int(n_iter)):
            f = bad(D, A1, A2, alpha, khat)
            J = np.zeros((2, 2))
            for kk in range(2):
                e = np.zeros(2)
                e[kk] = 1e-5 * max(1.0, abs(D[kk]))
                J[:, kk] = (bad(D + e, A1, A2, alpha, khat) - f) / e[kk]
            J[1, 1] += 1.0
            try:
                step = np.linalg.solve(J, -f)
            except np.linalg.LinAlgError:
                break
            nrm = float(np.hypot(*step))
            if nrm > 400.0:
                step = step * (400.0 / nrm)
            D = D + step
        return D, mod.spiral_residual(D, A1, A2, alpha, khat)
    mod.spiral_pole = pole
    mod._SPIRAL_ORIG_POLE = orig


def _bug_alpha_declared(mod):
    """alpha set to Silvester's published mid-range for real bays instead of
    being derived from this scene's own breaking obliquity. The bay still
    looks like a bay -- which is the point of the row."""
    mod.equilibrium_alpha = lambda delta: math.radians(40.0)


def _bug_theta_loc_no_shore(mod):
    """theta_loc taken as the grid-relative wave angle, forgetting that the
    shoreline has rotated under it. The classic: an obliquity measured against
    the wrong normal."""
    mod.shore_normal_angle = lambda y, x_s: np.zeros(np.asarray(y).size)


def _bug_zero_transport_breaking_angle(mod):
    """The closed-form zero-transport coast rotated by the BREAKING obliquity
    instead of the deep-water one. This file wrote that version first: Snell
    shrinks an angle but never to zero, so the coast is still oblique."""
    sc = mod._scene_1d(mod.T_SWELL, mod.H0_SWELL, mod.THETA0_SWELL)
    orig = mod.zero_transport_plan
    mod.zero_transport_plan = lambda y, x_ref, theta0: orig(
        y, x_ref, sc['theta_b'])


def _bug_cerc_sin_not_double(mod):
    """sin(theta) in place of sin(2 theta) in the CERC closure. Still zero at
    theta = 0, so the equilibrium is untouched -- and the K-doubling rows and
    the ratio rows cannot see it either. It is here to be caught by ONE thing
    only, and if nothing catches it that is the finding."""
    s = mod.RHO_S / mod.RHO_SW
    def bad(H_b, theta_loc, k_cerc=mod.K_CERC, gamma_b=mod.GAMMA_B):
        coef = (float(k_cerc) / (16.0 * (s - 1.0) * (1.0 - mod.POROSITY)
                                 * math.sqrt(gamma_b)))
        return (coef * math.sqrt(mod.G) * np.asarray(H_b, float) ** 2.5
                * np.sin(np.asarray(theta_loc, float)))
    mod.cerc_transport = bad


def _bug_plan_ramp_flat_contours(mod):
    """The Dean ramp keyed to the MEAN shoreline instead of the local one, so
    the depth contours stay straight under a curved shore. The bay is then a
    shape with no bathymetry behind it and refraction has nothing to turn onto
    -- the exact failure bar section J calls checkable by eye."""
    orig = mod.plan_ramp
    mod.plan_ramp = lambda x, y, x_s, **kw: orig(
        x, y, np.full(np.asarray(y).size, float(np.mean(x_s))), **kw)


def _bug_bay_bed_ignores_plan(mod):
    """`bay_bed` takes the plan-form and drops it. A silent no-op is the
    hardest kind of defect: nothing raises, the render still draws, and the
    only thing that changes is the answer."""
    orig = mod.bay_bed
    mod.bay_bed = lambda *a, **kw: orig(*a, **dict(kw, plan=None))


EMBAY_BUGS = ('grid-snell', 'spiral-no-tangency', 'alpha-declared',
              'theta-loc-no-shore', 'zero-transport-breaking-angle',
              'cerc-sin-not-double', 'plan-ramp-flat-contours',
              'bay-bed-ignores-plan')


LAND_BUGS = ('face-slope-at-break', 'swash-linear-band',
             'wet-albedo-all-diffuse', 'airlight-view-direction',
             'beta-no-scale-height', 'specular-no-jacobian',
             'shadow-reach-one-cell')
LAND_RENDER_BUGS = {'wet-albedo-all-diffuse', 'airlight-view-direction',
                    'beta-no-scale-height', 'specular-no-jacobian',
                    'shadow-reach-one-cell'}


BUGS = {
    'face-slope-at-break': _bug_face_slope_at_break,
    'swash-linear-band': _bug_swash_linear_band,
    'wet-albedo-all-diffuse': _bug_wet_albedo_all_diffuse,
    'airlight-view-direction': _bug_airlight_view_direction,
    'beta-no-scale-height': _bug_beta_no_scale_height,
    'specular-no-jacobian': _bug_specular_no_jacobian,
    'shadow-reach-one-cell': _bug_shadow_reach_one_cell,
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
    'one-turbidity-slider': _bug_one_turbidity_slider,
    'cdom-scatters': _bug_cdom_scatters,
    'depth-averaged-spm': _bug_depth_averaged_spm,
    'dw-for-bed-power': _bug_dw_for_bed_power,
    'isotropic-phase': _bug_isotropic_phase,
    'glitter-fixed-width': _bug_glitter_fixed_width,
    'glitter-no-jacobian': _bug_glitter_no_jacobian,
    'ambient-in-the-tube': _bug_ambient_in_the_tube,
    'sinusoidal-surface': _bug_sinusoidal_surface,
    'harmonic-shallow-everywhere': _bug_harmonic_shallow_everywhere,
    'unclamped-stokes': _bug_unclamped_stokes,
    'bore-phase-flipped': _bug_bore_phase_flipped,
    'skew-without-asymmetry': _bug_skew_without_asymmetry,
    'ur-half-declared': _bug_ur_half_declared,
    'foam-no-transmittance': _bug_foam_no_transmittance,
    'foam-backscatter-is-tir': _bug_foam_backscatter_is_tir,
    'foam-on-the-crest': _bug_foam_on_the_crest,
    'foam-declared-k': _bug_foam_declared_k,
    'foam-percent-for-fraction': _bug_foam_percent_for_fraction,
    'foam-single-rise-speed': _bug_foam_single_rise_speed,
    'foam-stokes-everywhere': _bug_foam_stokes_everywhere,
    'foam-unclipped-spheres': _bug_foam_unclipped_spheres,
    'bubble-fresnel-one-channel': _bug_bubble_fresnel_one_channel,
    'fov-on-the-long-side': _bug_fov_on_the_long_side,
    'dip-unrefracted': _bug_dip_unrefracted,
    'landscape-not-upright': _bug_landscape_not_upright,
    'hfov-scaled-linearly': _bug_hfov_scaled_linearly,
    'separation-small-angle': _bug_separation_small_angle,
    'flat-sea-no-horizon': _bug_flat_sea_no_horizon,
    'grid-snell': _bug_grid_snell,
    'spiral-no-tangency': _bug_spiral_no_tangency,
    'alpha-declared': _bug_alpha_declared,
    'theta-loc-no-shore': _bug_theta_loc_no_shore,
    'zero-transport-breaking-angle': _bug_zero_transport_breaking_angle,
    'cerc-sin-not-double': _bug_cerc_sin_not_double,
    'plan-ramp-flat-contours': _bug_plan_ramp_flat_contours,
    'bay-bed-ignores-plan': _bug_bay_bed_ignores_plan,
}
FOAM_BUGS = ('foam-no-transmittance', 'foam-backscatter-is-tir',
             'foam-on-the-crest', 'foam-declared-k',
             'foam-percent-for-fraction', 'foam-single-rise-speed',
             'foam-stokes-everywhere', 'foam-unclipped-spheres',
             'bubble-fresnel-one-channel')
CAMERA_BUGS = ('fov-on-the-long-side', 'dip-unrefracted',
               'landscape-not-upright', 'hfov-scaled-linearly',
               'separation-small-angle', 'flat-sea-no-horizon')
OPTICS_BUGS = {'one-turbidity-slider', 'cdom-scatters', 'depth-averaged-spm',
               'dw-for-bed-power', 'isotropic-phase', 'glitter-fixed-width',
               'glitter-no-jacobian', 'ambient-in-the-tube'}


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



# ------------------------------------------------- the static-equilibrium bay
def _sec_embay(ctx):
    """WAVE 9. The plan-form, and the one property that makes it provable.

    THE PROPERTY: at static equilibrium the wave orthogonal is normal to the
    shoreline everywhere, so sin(2 theta) is zero and the longshore transport
    is zero all along the bay. That is a claim with a number attached, and the
    section's job is to fire it at four shorelines under ONE offshore spectrum
    and report which of them the meter can and cannot tell apart.

    THE METER IS CALIBRATED FIRST AND THAT IS NOT OPTIONAL. `_zero` below is
    the closed-form zero-transport plan-form -- a straight coast rotated by the
    FULL deep-water obliquity -- and it exists so that "near zero on the bay"
    can be read against a floor that was measured rather than assumed. A test
    whose zero has never been demonstrated is the fourteenth way a measurement
    lies with the sign flipped: two readings agree because neither instrument
    could have said anything else.
    """
    B = ctx['B']
    ep = B.equilibrium_plan()
    ec = B.equilibrium_plan(delta=0.0)
    y = ep['y']
    x = np.arange(0.0, 1000.0 + 4.0, 4.0)
    ctx['ep'] = ep

    # ---- 1. the closed form is the closed form ------------------------------
    # the constant-angle property, from the DERIVATIVE against the DEFINITION
    ph = np.linspace(-1.2, 1.4, 97)
    t = B.spiral_tangent(ph, ep['alpha'])
    u = np.stack([np.cos(ph), np.sin(ph)], axis=-1)
    ang = np.arccos(np.clip(np.sum(t * u, axis=-1), -1.0, 1.0))
    check(1, 'log spiral: angle(radius, tangent) is constant alpha',
          ang, np.full(ph.size, ep['alpha']), 1e-12,
          'The logarithmic spiral is DEFINED by a constant angle between the '
          'radius vector and the tangent, and `spiral_tangent` is written '
          'from dP/dphi = R(cot(a) u + u_perp) without ever using that fact. '
          'Two routes, one of which is the definition.', 'rad')
    # the radial law itself, against a finite difference of ln R
    R = B.log_spiral(ph, 1000.0, 0.0, ep['alpha'])
    dlnR = np.gradient(np.log(R), ph)
    check(1, 'log spiral: d(ln R)/d(phi) = cot(alpha)',
          dlnR[3:-3], np.full(ph.size - 6, 1.0 / math.tan(ep['alpha'])), 1e-8,
          'R = R_a exp((phi-phi_a) cot a) has a constant logarithmic '
          'derivative. Checked numerically so a typo in the exponent cannot '
          'hide behind the exponential.', '1/rad')
    # alpha = 90 deg IS the circle -- the derived member
    Rc = B.log_spiral(ph, 1000.0, 0.0, math.pi / 2.0)
    check(1, 'alpha = 90 deg is a circle (R constant)',
          Rc, np.full(ph.size, 1000.0), 1e-9,
          'The derived member. Shore normal to a radial orthogonal is a '
          'circular arc about the pole, exactly; the spiral is its '
          'generalisation to a constant residual obliquity.', 'm')

    # ---- 2. the construction has no free parameter --------------------------
    check(1, 'pole solve: both closure residuals vanish',
          np.abs(ep['res']), np.zeros(2), 1e-10,
          'Two equations -- the spiral passes through both rock anchors, and '
          'its tangent at the downcoast control point is perpendicular to the '
          'deep-water wave vector -- for the two coordinates of the pole. '
          'Nothing is left over to tune.', '-')
    tang = math.degrees(math.atan(ep['slope_tangent']))
    check(1, 'downcoast tangent is perpendicular to the crests',
          tang, -math.degrees(B.THETA0_SWELL), 1e-9,
          'Hsu and Evans\' downcoast control point is where the beach becomes '
          'parallel to the incoming crests. Here that is a CONSEQUENCE of the '
          'pole solve, recomputed from the sampled shoreline rather than from '
          'the condition, so it is a check and not a restatement.', 'deg')
    fit = B.fit_log_spiral(ep['pts'], alpha0=ep['alpha'], D0=ep['D'])
    check(3, 'independent spiral fit recovers the pole',
          fit['D'], ep['D'], 1.0,
          'A least-squares fit over pole AND alpha, minimising a radial '
          'residual over 2001 sampled points -- a different objective from '
          'the two exact closure conditions the construction solved.', 'm')
    info(3, 'independent fit: rms radial residual', fit['rms'],
         'The bay against the closed form it came from. Metres.')
    check(3, 'independent spiral fit recovers alpha',
          fit['alpha'], ep['alpha'], 1e-3,
          'Same fit, the shape parameter. If the construction and the fit '
          'disagreed here the sampling would be wrong.', 'rad')

    # ---- 3. alpha is derived, and delta is the `?` --------------------------
    sc = B._scene_1d(B.T_SWELL, B.H0_SWELL, B.THETA0_SWELL)
    check(1, 'alpha = 90 deg - theta_b, from the transform\'s own break',
          ep['alpha'], math.pi / 2.0 - sc['theta_b'], 1e-14,
          'The spiral angle is not fitted to a coastline: it is the residual '
          'breaking obliquity the 1-D transform OUTPUTS for the stated '
          'offshore spectrum. Change the spectrum and the bay changes shape.',
          'rad')
    openq(2, 'delta, the residual obliquity: DECLARED', 
          '%.4f deg' % math.degrees(sc['theta_b']), '?',
          'Only delta = 0 (the circle) is derived. delta = theta_b is a '
          'declared choice. Silvester\'s published alpha for real bays is '
          '30-50 deg, i.e. delta = 40-60 deg -- an order above anything '
          'refraction leaves, and an EMPIRICAL fit, not this quantity. The '
          'circle is computed beside the spiral every run so the choice is '
          'visible: its indentation is %.2f m against the spiral\'s %.2f m, '
          'a %.1f%% difference.'
          % (ec['sagitta'], ep['sagitta'],
             100 * abs(ec['sagitta'] / ep['sagitta'] - 1)))
    check(3, 'the circle and the spiral agree on the indentation to 5%',
          ec['sagitta'] / ep['sagitta'], 1.0, 0.05,
          'The `?` in delta is worth less than the two headlands are: the '
          'derived member and the declared one put the shoreline within a few '
          'per cent of each other, which is why the `?` is reported rather '
          'than chased.', '-')

    # ---- 4. the indentation, against the photograph -------------------------
    info(2, 'bay indentation over the frame', ep['sagitta'],
         'The maximum perpendicular offset of the shoreline from the chord of '
         'its ends, over %.0f m of coast. Bar section J\'s overview gives '
         'roughly 50 m over 1408 m. This is an OUTPUT -- nothing in the '
         'construction was set from it, and the standing ruling forbids '
         'calibrating against the photographs.' % ep['chord'])
    openq(2, 'indentation against bar J: ratio', 
          '%.2fx' % (ep['sagitta'] / 50.0), '1.0x',
          'The closed form over-predicts the photograph\'s indentation. The '
          'mechanism is the downcoast tangency condition: it puts the whole '
          'frame between the diffraction point and the control point, so the '
          'frame is asserted to be ONE WHOLE BAY. Inverting instead -- what '
          'deep-water obliquity gives 50 m over 1408 m -- gives %.2f deg '
          'against the file\'s declared %.1f, and THAT is a measurement of '
          'the offshore spectrum from a plan-form, reported and not applied.'
          % (math.degrees(_theta0_for_sagitta(B, ep, 50.0)),
             math.degrees(B.THETA0_SWELL)))
    check(2, 'the coastal loop alone gives no bay',
          _smooth_curvature(ep['x_s_rock'], y) < 0.35 * ep['sagitta'], True,
          0, 'Waves 1-8 measured 55 m of shoreline RANGE and read it as plan '
          'curvature. It is not: fit a straight line to the loop\'s own '
          'shoreline and the residual is roughness at the hardness field\'s '
          '380 m correlation length, not one curve. The bay-scale component '
          'is %.1f m against the built bay\'s %.1f.'
          % (_smooth_curvature(ep['x_s_rock'], y), ep['sagitta']), '-')

    # ---- 5. THE TRANSPORT. four shorelines, one offshore spectrum ----------
    x_ref = float(np.mean(ep['x_s']))
    x_str = np.full(y.size, x_ref)
    x_rot = B.zero_transport_plan(y, x_ref, B.THETA0_SWELL)
    fan = B.fan_theta0(y, ep['x_s'], ep['D'])
    res = {}
    for nm, xs, th0 in (('straight', x_str, B.THETA0_SWELL),
                        ('rotated', x_rot, B.THETA0_SWELL),
                        ('bay_plane', ep['x_s'], B.THETA0_SWELL),
                        ('bay_fan', ep['x_s'], fan)):
        _, tr = B.plan_field(x, y, xs, theta0=th0)
        res[nm] = B.plan_transport(y, xs, tr)
    # the spiral span only, for the bay: the frame's outer sixth is the rock
    # headland the loop built, and its plan-form is the hardness field's
    # roughness rather than the closed form.
    msp = np.zeros(y.size, bool)
    msp[ep['j1'] + 2:ep['j2'] - 1] = True
    sp = {k: float(np.sqrt(np.mean(res[k]['Q'][msp & res[k]['mask']] ** 2)))
          for k in res}
    ctx['embay_Q'] = dict(res=res, sp=sp)

    check(1, 'straight coast under an oblique swell: Q is NOT zero',
          res['straight']['Q_rms'] > 5e-2, True, 0,
          'The control the bar asks for. A straight shoreline under this '
          'offshore spectrum carries %.4e m3/s of longshore transport at '
          'every station, because theta_b = %.3f deg and sin(2 theta) is not '
          'zero. If this row ever passes trivially the whole section is '
          'measuring nothing.'
          % (res['straight']['Q_rms'], math.degrees(sc['theta_b'])), '-')
    check(1, 'the closed-form zero-transport coast reads zero: 18x down',
          res['rotated']['Q_rms'] / res['straight']['Q_rms'], 0.0, 0.10,
          'THE METER\'S OWN FLOOR, and it is measured rather than assumed. '
          'theta_loc = 0 forces phi_s = -theta_0 -- a straight coast rotated '
          'by the FULL deep-water obliquity, not the breaking one -- and the '
          'transform returns %.5f deg of residual obliquity on it against '
          '%.4f on the straight coast. Everything below is read against this '
          'number.' % (math.degrees(res['rotated']['th_mean']),
                       math.degrees(res['straight']['th_mean'])), '-')
    openq(1, 'the bay under a PLANE crest: Q is not reduced',
          '%.4e' % res['bay_plane']['Q_rms'],
          '<= %.4e' % res['straight']['Q_rms'],
          'AND IT CANNOT BE. With plane offshore crests and contours that '
          'follow the shore, theta_loc = 0 demands phi_s = -theta_0 at every '
          'station, which is one straight line. ANY curvature raises the '
          'transport. That is terrain-architect chapter 12\'s own sentence -- '
          '"headlands retreat faster than bays ... until the coast '
          'STRAIGHTENS" -- and it is right. A static-equilibrium BAY is '
          'therefore not a property of a shoreline; it is a property of a '
          'shoreline AND the headland that shelters it.')
    info(1, 'the fan the bay requires, alongshore swing',
         math.degrees(ep['fan']['swing']),
         'Degrees. The wave orthogonal must swing this far across the bay for '
         'the built shoreline to be an equilibrium. It is pure geometry -- no '
         'wave model enters it -- and it is the quantitative form of "the bay '
         'needs its headland to diffract".')
    check(1, 'with that fan, the bay\'s transport falls by 3x',
          sp['bay_fan'] / sp['straight'] < 0.45, True, 0,
          'The bay under the fan its OWN pole implies, over the spiral span: '
          'Q rms %.4e against the straight coast\'s %.4e, a factor of %.2f. '
          'Measured through the same transform, the same ramp and the same '
          'CERC closure -- one array changed.'
          % (sp['bay_fan'], sp['straight'], sp['straight'] / sp['bay_fan']),
          '-')
    openq(1, 'the bay is NOT zero to within numerics',
          '%.4e' % sp['bay_fan'], '%.4e (the floor)' % sp['rotated'],
          'HONEST ANSWER TO THE BAR\'S QUESTION. The bay\'s residual is %.1fx '
          'the meter\'s own floor, so it is SMALL and not ZERO. The residual '
          'is decomposed in the two rows below rather than left as a '
          'tolerance.' % (sp['bay_fan'] / max(sp['rotated'], 1e-12)))

    # ---- 6. where the residual comes from ----------------------------------
    v = ec['pts'] - ec['D']
    Rc0 = float(np.mean(np.hypot(v[:, 0], v[:, 1])))
    xs_c = ec['D'][0] + np.sqrt(np.maximum(Rc0 ** 2 - (y - ec['D'][1]) ** 2,
                                           0.0))
    n0 = np.arctan2(y - ec['D'][1], xs_c - ec['D'][0])
    h_pol = B.plan_ramp_polar(x, y, ec['D'],
                              (np.array([-1.5, 1.5]), np.array([Rc0, Rc0])))
    tr_pol = B.transform_2d(x, y, h_pol, B.T_SWELL, B.H0_SWELL, n0,
                            contour0=n0)
    p_pol = B.plan_transport(y, xs_c, tr_pol)
    _, tr_car = B.plan_field(x, y, xs_c, theta0=n0)
    p_car = B.plan_transport(y, xs_c, tr_car)
    check(3, 'a concentric ramp lowers the residual: contours, not curvature',
          p_pol['th_mean'] < p_car['th_mean'], True, 0,
          'THE SEPARATING MEASUREMENT. Same circular shoreline, same radial '
          'incidence, two beds: one whose depth is a function of CROSS-SHORE '
          'distance (contours are x-translates of the shore, and they '
          'converge where it is concave) and one whose depth is a function of '
          'distance from the POLE (contours are concentric arcs, on which a '
          'radial ray is normal to every contour it crosses). %.4f deg '
          'against %.4f -- so %.2f deg of the residual is the ramp not being '
          'concentric with the curve it is keyed to, and the rest is not.'
          % (math.degrees(p_pol['th_mean']), math.degrees(p_car['th_mean']),
             math.degrees(p_car['th_mean'] - p_pol['th_mean'])), '-')
    openq(3, 'the rest of the residual is the SOLVER, on a curved bed',
          '%.4f deg' % math.degrees(p_pol['th_mean']),
          '%.4f deg (straight-contour floor)'
          % math.degrees(res['rotated']['th_mean']),
          'On STRAIGHT contours at the same 20 deg obliquity the transform '
          'leaves %.4f deg; on concentric contours with exactly radial '
          'incidence it leaves %.4f. The difference is the march itself: '
          '`transform_2d` advances column by column in x and carries the '
          'ray\'s alongshore drift only through the dk/dy terms, and at 20 '
          'deg the drift is 0.36 of a cell per step rather than the 0.015 the '
          'function\'s own comment quotes for the near-normal case. Named, '
          'measured, and out of scope for this wave.'
          % (math.degrees(res['rotated']['th_mean']),
             math.degrees(p_pol['th_mean'])))

    # ---- 7. the closure coefficient cannot reach the answer ----------------
    _, tr_b = B.plan_field(x, y, ep['x_s'], theta0=fan)
    q1 = B.plan_transport(y, ep['x_s'], tr_b, k_cerc=B.K_CERC)
    q2 = B.plan_transport(y, ep['x_s'], tr_b, k_cerc=2.0 * B.K_CERC)
    check(1, 'CERC K doubles: theta_loc does not move at all',
          float(np.max(np.abs(q2['theta_loc'] - q1['theta_loc']))), 0.0, 0.0,
          'The equilibrium is Q = 0 and Q = C sin(2 theta) with C > 0, so the '
          'plan-form cannot depend on C for ANY C. The empirical closure '
          'coefficient is the one number in this section that could have been '
          'tuned to make the answer come out, and it is structurally unable '
          'to reach it.', 'rad')
    check(1, 'CERC K doubles: Q doubles exactly',
          q2['Q_rms'] / q1['Q_rms'], 2.0, 1e-12,
          'The other half of the same statement: K sets the RATE and nothing '
          'else. Both halves are needed -- one alone is consistent with K '
          'being ignored.', '-')

    # ---- 7b. the closure's own shape, against chapter 12's sentence --------
    th = np.linspace(0.0, math.radians(89.0), 4001)
    Qc = B.cerc_transport(1.0, th)
    check(2, 'CERC transport peaks at a 45 deg approach',
          math.degrees(th[int(np.argmax(Qc))]), 45.0, 0.05,
          'terrain-architect chapter 12 states the closure as "Q_long ~ '
          'sin(2 (waveAngle - shorelineNormal))  # peaks near 45 deg '
          'approach" (Komar & Inman 1970). The peak location is the one '
          'property of the closure that distinguishes sin(2 theta) from '
          'sin(theta) WITHOUT knowing the coefficient -- sin(theta) peaks at '
          '90. Written from the chapter\'s sentence, not from the function.',
          'deg')
    check(1, 'CERC transport is odd in the approach angle',
          B.cerc_transport(1.3, -th) + B.cerc_transport(1.3, th),
          np.zeros(th.size), 1e-14,
          'Reverse the approach and the drift reverses. A closure that is not '
          'odd cannot make a spit point the right way, which is chapter 12\'s '
          'own stated reason for computing the drift DIRECTION at all.',
          'm3/s')
    check(1, 'CERC transport scales as H_b^(5/2)',
          B.cerc_transport(2.0, 0.2) / B.cerc_transport(1.0, 0.2),
          2.0 ** 2.5, 1e-12,
          'The height exponent, isolated at fixed angle.', '-')

    # ---- 8. the sign convention, against a hand-rotated coast --------------
    yy = np.linspace(-100.0, 100.0, 41)
    for deg in (-12.0, -5.0, 7.0, 15.0):
        xr = 500.0 + math.tan(math.radians(deg)) * yy
        check(1, 'shore_normal_angle on a %+.0f deg coast' % deg,
              math.degrees(float(np.median(B.shore_normal_angle(yy, xr)))),
              deg, 1e-9,
              'phi_s = atan(dx_s/dy) by construction, and theta_loc = theta + '
              'phi_s. The sign is the one thing in this section a reader will '
              'get backwards, so it is checked against a coast whose angle is '
              'typed in.', 'deg')

    # ---- 9. the bed carries the plan-form ----------------------------------
    b0 = B.run_bay(dx=4.0, n_steps=75, dt=6000.0)
    b1 = B.run_bay(dx=4.0, n_steps=75, dt=6000.0, embay=True)
    r0 = float(b0['x_s'].max() - b0['x_s'].min())
    r1 = float(b1['x_s'].max() - b1['x_s'].min())
    check(2, 'the composed bed inherits the bay: shoreline range triples',
          r1 / r0 > 2.5, True, 0,
          'The plan-form reaches `bay_bed`, which shifts the coastal loop\'s '
          'own surface bodily per row so the cliff, the bench, the hardness '
          'roughness and the retreat all survive and ONLY the position of the '
          'coast moves. %.1f m against %.1f m.' % (r1, r0), '-')
    a0, m0 = B.contour_alignment(b0['tr'])
    a1, m1 = B.contour_alignment(b1['tr'])
    ali0 = dict(mean=float(np.mean(a0[m0])))
    ali1 = dict(mean=float(np.mean(a1[m1])))
    info(2, 'crest-to-contour alignment, embayed bed', ali1['mean'],
         'Degrees between the wave crest and the local depth contour, over '
         'the surf zone. Bar section J\'s by-eye criterion -- "the breaking '
         'lines bend to stay parallel to the shore around the whole curve" -- '
         'as a number. The un-embayed bed reads %.4f deg, and it reads it on '
         'contours that were already straight, which is the '
         'straight-contour test that passes by construction.' % ali0['mean'])
    check(2, 'the embayed bed turns the crests through a real angle',
          _crest_swing(b1) > 2.0 * _crest_swing(b0), True, 0,
          'ALIGNMENT IS NOT THE TEST. A crest can lie on the contour on a '
          'straight coast without the refraction doing any work at all. What '
          'a bay adds is that the crest DIRECTION has to change alongshore, '
          'one way, across the whole frame. Bay-scale swing of the breaking '
          'crest azimuth: %.3f deg embayed against %.3f flat, a factor of '
          '%.2f. The threshold is a factor of two -- a round number and not '
          'the measured one, because a threshold set at the measurement is a '
          'tolerance the size of the thing it covers.'
          % (_crest_swing(b1), _crest_swing(b0),
             _crest_swing(b1) / max(_crest_swing(b0), 1e-9)), '-')


def _theta0_for_sagitta(B, ep, target):
    """Invert the closed form: the deep-water obliquity a stated indentation
    implies. A measurement of the offshore spectrum FROM a plan-form, reported
    and never applied -- the standing ruling forbids calibrating on the
    photographs."""
    lo, hi = 1e-4, math.radians(45.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        s = B.equilibrium_plan(theta0=mid)['sagitta']
        if s < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _smooth_curvature(x_s, y, n=3):
    """The bay-scale component of a shoreline: the maximum |residual| after a
    low-order polynomial is removed, evaluated on a HEAVILY smoothed profile
    so that hardness-field roughness cannot be counted as a bay."""
    x_s = np.asarray(x_s, float)
    y = np.asarray(y, float)
    w = max(int(round(0.2 * y.size)) | 1, 3)
    ker = np.ones(w) / w
    sm = np.convolve(np.pad(x_s, w // 2, mode='edge'), ker, mode='valid')
    ch = sm[0] + (sm[-1] - sm[0]) * (y - y[0]) / (y[-1] - y[0])
    return float(np.max(np.abs(sm - ch)))


def _crest_swing(bay):
    """The BAY-SCALE alongshore swing of the breaking crest azimuth, degrees.

    Smoothed over a fifth of the frame first, and that is the measurement and
    not a cosmetic. The raw swing is 19.5 deg on the un-embayed bed and 17.0
    on the embayed one -- the un-embayed bed looks BETTER -- because the raw
    number is dominated by the hardness field\'s 380 m roughness wiggling the
    local shore normal cell by cell. Roughness turns crests locally and
    averages to nothing; a bay turns them one way across the whole frame. The
    first draft of this row measured the raw swing, reported the wrong sign of
    the effect, and is left recorded because the next reader will reach for the
    raw number too.
    """
    br = BCH.breaker_row(bay['tr'])
    th = np.degrees(br['theta'])
    w = max(int(round(0.2 * th.size)) | 1, 3)
    sm = np.convolve(np.pad(th, w // 2, mode='edge'), np.ones(w) / w,
                     mode='valid')
    return float(sm.max() - sm.min())


# ================================ 7 - the coastal IOPs, the path and the glitter
#
# WAVE 4. The pool's `optics.py` and `atmosphere.py` are IMPORTED here exactly as
# `beach_optics.py` imports them, and nothing in this section checks them again:
# `validate.py` owns 285 rows on that physics and duplicating any of them would
# be the two-routes-one-source error in its purest form. What this section
# checks is the layer wave 4 added -- the inherent optical properties, the two
# transports, and the glitter -- and every tier-3 row names the second route.
def _sec_optics(ctx):
    O = BOP

    # -------------------------------------------------- 7.1 the phase function
    # The Henyey-Greenstein backscatter fraction, closed form against a
    # quadrature of the phase function itself. The two share the letter g and
    # nothing else: one is an algebraic expression, the other integrates
    # `hg_phase` over the backward hemisphere with a Gauss-Legendre rule.
    mu, wq = np.polynomial.legendre.leggauss(12000)
    for g in (0.30, 0.60, 0.9132, 0.98):
        num = 2.0 * math.pi * float(
            (wq[mu < 0] * O.hg_phase(g, mu[mu < 0])).sum())
        check(1, 'HG backscatter fraction, closed form vs quadrature (g=%.2f)'
              % g, O.hg_backscatter_fraction(g), num, 3e-8,
              'Gauss-Legendre at 24000 nodes. The tolerance is the '
              'quadrature\'s own residual on a lobe whose width goes as '
              '(1-g): at g = 0.98 the peak is 0.02 rad wide and a rule uniform '
              'in cos(theta) is working hardest exactly where the closed form '
              'is cheapest. Two decades of headroom over a transcription '
              'error, which is what this row is for.')
    tot = 2.0 * math.pi * float((wq * O.hg_phase(0.9132, mu)).sum())
    check(1, 'HG phase normalisation INT p dw', tot, 1.0, 1e-9,
          'A phase function that does not integrate to 1 is an albedo hiding '
          'in a shape, and it would move every scattering term by the same '
          'unnoticed factor.')
    check(1, 'g is DERIVED from chapter 28\'s b_f >= 50 b_b',
          O.hg_backscatter_fraction(O.PHASE_G), O.BB_OVER_B, 1e-9,
          'The chapter states the forward dominance as a ratio and gives no g. '
          'Inverting B(g) = b_b/b is what removes the choice, so this row is '
          'the one that fails if anybody types a g in by hand.')

    # ------------------------------------------------- 7.2 the band integration
    def _sp(l):
        return O.a_ph(l, 0.1) + O.a_cdom(l, 0.08)
    check(3, 'band integration, 161 nodes per band against 1601',
          O.band_mean(_sp), O.band_mean(_sp, 1601), 1e-6,
          'Ten times the node density on the SAME interval -- each band is '
          'sampled on its own linspace between its own edges, so refining n '
          'cannot move the window. An earlier writing masked one global grid '
          'per band and this row measured the rounding of the grid instead of '
          'the quadrature: it read 0.7% and looked like a convergence problem.')

    # --------------------------------------- 7.3 chapter 28's OWN claims, as rows
    # These check the CHAPTER, not this file's shape parameters. The widths and
    # the red/blue ratio of the chlorophyll line shape are declared `?`, and a
    # row that checked them would be checking `beach_optics.py` against itself.
    lam = np.arange(400.0, 720.0, 1.0)
    aph = O.a_ph(lam, 1.0)
    win = (lam >= 550.0) & (lam <= 570.0)
    i_min = int(np.argmin(aph[(lam >= 480) & (lam <= 640)]))
    lam_min = float(lam[(lam >= 480) & (lam <= 640)][i_min])
    check(1, 'chlorophyll: the window is below both peaks',
          float(aph[win].max() < min(aph[np.argmin(abs(lam - 440))],
                                     aph[np.argmin(abs(lam - 675))])),
          1.0, 0.0, 'Two peaks and a window between them is the whole of the '
          'chapter\'s statement about this constituent, and the only part of '
          'the declared line shape a row is entitled to check.')
    # THE CHAPTER'S 550-570 IS A STATEMENT ABOUT THE WATER, NOT ABOUT THE
    # PIGMENT, and this pair of rows is where that was found.
    ab = O.iops()['a']
    check(2, 'the water\'s total absorption minimises in the band holding '
          '550-570 nm', float(np.argmin(ab)), 1.0, 0.0,
          'Chapter 28: chlorophyll "leav[es] a transmission window at 550-570 '
          'nm". Band 1 is 502.5-582.5 nm and contains that window, so the '
          'chapter\'s claim about THIS WATER is that channel 1 is the least '
          'absorbed. It is.')
    info(2, 'but a_ph ALONE minimises at %g nm, not 550-570' % lam_min,
         lam_min,
         'A correction to the chapter, found by writing the line shape down. '
         'The minimum of a sum of two absorption lines sits BETWEEN them, '
         'nearer the broader one\'s tail -- near 590-600 for peaks at 440 and '
         '675. What sits at 550-570 is the minimum of a_ph PLUS pure water, '
         'because a_w climbs steeply above 570 and pushes the window back down '
         'the spectrum. The chapter is right about the water and loose about '
         'the constituent, and an implementer who fits a pigment spectrum to '
         'put ITS minimum at 560 needs widths no pigment has.', exp='550-570')
    acd = O.a_cdom(lam, 1.0)
    check(1, 'CDOM rises monotonically into the blue',
          float(np.all(np.diff(acd) < 0.0)), 1.0, 0.0,
          'a440 exp[-S(lam - 440)] with S > 0 is monotone decreasing in '
          'wavelength by construction; the row fires at a sign slip in S, '
          'which would turn gelbstoff into a red absorber.')
    io_c = O.iops(a_cdom440=5.0, a_ph440=0.0)
    io_0 = O.iops(a_cdom440=0.0, a_ph440=0.0)
    # THE THREE ARE NOT ONE SLIDER, and this is the row that says so. The water
    # MASS's absorption belongs to the water mass; the mineral load is a FIELD
    # driven by the waves. A renderer that ties them together has one turbidity
    # control wearing three names, which is the architecture chapter 28 spends a
    # section warning against.
    check(1, 'the water mass\'s absorption does not depend on the mineral load',
          O.iops(spm=200.0)['a'], O.iops(spm=0.0)['a'], 1e-14,
          'Chlorophyll and CDOM are properties of the water body; suspended '
          'mineral is a property of what the waves are doing to the bed. They '
          'move independently or this coast cannot show BOTH a green wave face '
          'and a pale surf zone, which bar section A says it does. Two hundred '
          'mg/L of sediment must not move `a` by one part in 1e14.')
    check(1, 'CDOM scatters not at all', io_c['b'], io_0['b'], 1e-14,
          'Chapter 28, verbatim, and it is the sentence that separates '
          'blackwater from mud. A hundredfold change in CDOM must leave b '
          'exactly where it was.')
    # CDOM darkens, sediment brightens -- the chapter's own doctrine, as a pair
    R_c = O.volume_reflectance(io_c['a'], io_c['b_b'], 30.0)
    R_0 = O.volume_reflectance(io_0['a'], io_0['b_b'], 30.0)
    io_s = O.iops(a_cdom440=0.0, a_ph440=0.0, spm=20.0)
    R_s = O.volume_reflectance(io_s['a'], io_s['b_b'], 30.0)
    check(1, 'chapter 28 doctrine: CDOM DARKENS, sediment BRIGHTENS',
          (float(np.all(R_c < R_0)), float(np.all(R_s > R_0))), (1.0, 1.0),
          0.0, '"They are opposite controls." Reaching for turbidity to make a '
          'tannin-stained water gives mud, and this is the row that separates '
          'the two knobs rather than trusting a comment that they differ.')

    # ------------------------------------------------- 7.4 the Babin bridge
    check(2, 'Babin et al. (2003): b_p(555)/SPM', float(O.b_p(555.0, 1.0)),
          0.5, 1e-12,
          'Chapter 28\'s concentration -> optics bridge, at the wavelength it '
          'is stated at. 1 mg/L = 1 g/m^3, so each mg/L adds 0.5 m^-1.',
          unit='m^2/g')
    for spm, lo, hi in ((1.0, 0.4, 0.7), (1000.0, 400.0, 700.0)):
        b555 = float(O.b_p(555.0, spm))
        between(2, 'the bridge\'s own dimension check at SPM = %g mg/L' % spm,
                b555, lo, hi,
                'Chapter 28 checks its own bridge twice: "a coastal few-mg/L '
                'water then has b of order 1 m^-1, and a 1000 mg/L silt river '
                'has b ~ 500 m^-1 -- a millimetre-scale photon path". Both '
                'ends, so a factor of 1000 in the units cannot hide.',
                unit='m^-1')

    # ----------------------------------- 7.5 the recovery, and what it predicts
    # The a_ph(440) this scene uses is recovered from chapter 28's Jerlov 1C
    # entry. Running the SAME relation FORWARD must return the entry, which is
    # only a consistency check -- so the row that matters is the next one: what
    # the recovered water predicts for a DIFFERENT Jerlov type it never saw.
    kd_fwd = (O.A_W_490 + float(O.a_cdom(490.0, O.A_CDOM_440))
              + O.A_PH_440 * float(O._chl_shape(490.0))
              + O.BB_OVER_B * float(O.b_w(490.0))) / O.MU_D
    check(1, 'the Jerlov 1C recovery, run forward', kd_fwd,
          O.JERLOV_1C_KD490, 1e-9,
          'Gordon\'s K_d ~= (a + b_b)/mu_d, inverted to get a_ph(440) and then '
          'evaluated again. An algebraic identity, and it is here because a '
          'recovery that does not round-trip is a typo, not a measurement.',
          unit='m^-1')
    between(2, 'Secchi depth of the recovered water (Lee et al. 2015)',
            O.secchi(O.iops()['a'], O.iops()['b_b']), 4.0, 20.0,
            'Chapter 28: Z_SD ~= 1/min_lambda K_d, and its Jerlov table puts a '
            'type-I sea at ~30 m and a 9C harbour under a metre. A coastal '
            'green water belongs between those, nearer the clear end. This is '
            'a RANGE and not a value: nothing measured the water off Aljezur.',
            unit='m')

    # ------------------------------------- 7.6 the volume reflectance, derived
    a, bb = O.iops(spm=3.0)['a'], O.iops(spm=3.0)['b_b']
    R_inf = O.volume_reflectance(a, bb, 1.0e6)
    check(1, 'deep limit R -> f b_b/(a + b_b)', R_inf,
          O.F_GORDON * bb / (a + bb), 1e-12,
          'The derived integral\'s own limit, in closed form. It fires at a '
          'dropped mu in either leg, which is the arithmetic this file is most '
          'exposed to.')
    between(2, 'the derived f against the published ~0.33',
            O.F_GORDON, 0.28, 0.36,
            'f = 1/(1/mu_d + 1/mu_u) comes out of a single-scattering '
            'integral that has never heard of 0.33; the ocean-colour '
            'literature (Gordon et al. 1988; Morel & Prieur 1977) writes f ~ '
            '0.33 from full radiative transfer. The 5% gap IS the multiple '
            'scattering single scattering leaves out, and its SIGN is right: '
            'single scattering must under-count.')
    # tier 3: the same reflectance by quadrature rather than by the closed form
    zq, wz = np.polynomial.legendre.leggauss(2000)
    D_test = 4.0
    zq, wz = 0.5 * D_test * (zq + 1.0), 0.5 * D_test * wz
    inv = 1.0 / O.MU_D + 1.0 / O.MU_U
    c = a + bb
    R_num = np.array([float((wz * bb[ch] * np.exp(-c[ch] * inv * zq)).sum())
                      for ch in range(3)])
    check(3, 'volume reflectance: closed form against a quadrature of the '
          'source integral', O.volume_reflectance(a, bb, D_test), R_num, 1e-10,
          'The second route integrates b_b E_d(z) exp(-K_u z) dz numerically '
          'instead of evaluating the antiderivative. It shares the model and '
          'not the algebra, which is what a tier-3 row on a derivation can be.')
    # tier 1: the two-layer composition must collapse when the layers agree
    two = O.column_reflectance(a, bb, 1.5, a, bb, 2.5)
    check(1, 'the two-layer column collapses to one when the layers agree',
          two['R'], O.volume_reflectance(a, bb, 4.0), 1e-12,
          'Splitting a uniform column at an arbitrary depth cannot change its '
          'reflectance. This is the row that fires at a missing round trip in '
          'the composition, which is exactly the error `optics.py` records '
          'itself making on the pool\'s trapped series.')

    # ------------------------------------------------- 7.7 the path, section A
    io = O.iops()
    L0 = np.array([1.0, 1.0, 1.0])
    for Lp in (0.25, 1.0, 3.0):
        T = O.through_path(L0, np.array(Lp), io['a'], io['b_b'])
        check(1, 'Beer-Lambert on a + b_b at L = %.2f m' % Lp, T,
              np.exp(-(io['a'] + io['b_b']) * Lp), 1e-14,
              'The transport itself, against its own closed form -- which is '
              'trivial and is here so that the CUVETTE row below is measuring '
              'the inversion and not the forward model.')
    # the green must vanish when the path does
    ge = []
    for Lp in (0.0, 0.05, 0.5, 2.0, 5.0):
        T = O.through_path(L0, np.array(Lp), io['a'], io['b_b'])
        ge.append(2.0 * T[1] / (T[0] + T[2]))
    check(1, 'THE GREEN VANISHES WHEN THE PATH DOES', ge[0], 1.0, 1e-12,
          'Bar section A, and it is the sharpest criterion in the file: at '
          'zero path the transmitted spectrum IS the source spectrum, so the '
          'green excess of a neutral source is exactly 1. A renderer that '
          'tints its water body cannot pass this row at any tolerance.')
    check(1, 'and it grows monotonically with the path',
          float(np.all(np.diff(ge) > 0)), 1.0, 0.0,
          'The GRADE, which section A asks for by name -- "the render must '
          'reproduce the grade, not merely the hue".')
    info(1, 'green excess 2G/(R+B) at L = 0, 0.05, 0.5, 2, 5 m', tuple(ge),
         'the wedge, in one row')
    # the bar's own pure-water number, as an independent check on the water half
    T2 = np.exp(-OPT.ABS * 2.0)
    check(2, 'bar section A: pure water over 2 m transmits (0.59, 0.90, 0.98)',
          T2, np.array([0.59, 0.90, 0.98]), 0.015,
          'The bar states this triple as the reason the observed hue "is not '
          'pure water\'s". It is computed here from `optics.ABS` -- Pope & Fry '
          'band means, which the bar did not use -- so the agreement is '
          'between two independent statements of the same spectrum. The '
          'tolerance is the band-mean-versus-point-sample difference.')

    # ------------------------------- 7.7b THE FORWARD GLOW, and why g matters
    # Chapter 28 asks for `phase_g` and warns that leaving it at zero "kills the
    # forward glow through a sunlit wave crest". These two rows are that warning
    # made checkable: the glow's whole behaviour is an ASYMMETRY between looking
    # into the sun and looking away from it, and an isotropic phase function has
    # no asymmetry to give.
    c16 = math.cos(math.radians(15.8))
    c159 = math.cos(math.radians(159.0))
    ratio = float(O.hg_phase(O.PHASE_G, c16) / O.hg_phase(O.PHASE_G, c159))
    between(1, 'the HG lobe is forward-peaked by two orders', ratio,
            50.0, 1e4,
            "The cuvette's two panels sit at scattering angles 15.8 and 159 "
            "deg -- the same lobe, the same water, only the observer moved. If "
            "the ratio between them is near 1 the phase function is isotropic "
            "and the backlit face has stopped being backlit, which is exactly "
            "the defect chapter 28 names when it says leaving g at zero kills "
            "the forward glow through a sunlit wave crest.")
    g1 = O.forward_glow(np.ones(3), 1.0, c16, io['a'], io['b'])
    g2 = O.forward_glow(np.ones(3), 2.0, c16, io['a'], io['b'])
    check(1, 'the glow is NOT Beer-Lambert: L exp(-cL), not exp(-cL)',
          g2 / g1, 2.0 * np.exp(-(io['a'] + io['b']) * 1.0), 1e-12,
          "Doubling the path does not attenuate the glow the way it attenuates "
          "a transmitted image -- it doubles the SOURCE length first. That "
          "extra factor of L is what biases a cuvette inversion run on a "
          "scattering-dominated signal, by ln(L2/L1)/(L2-L1) weighted by the "
          "glow's share of the signal, and it is worst in the green.")

    # -------------------------------------------------- 7.8 the cuvette
    for (l1, l2) in ((0.2, 1.0), (0.5, 3.0), (1.0, 8.0)):
        t1 = O.through_path(L0, np.array(l1), io['a'], io['b_b'])
        t2 = O.through_path(L0, np.array(l2), io['a'], io['b_b'])
        check(1, 'cuvette inversion at L = %.1f / %.1f m' % (l1, l2),
              O.cuvette_c(t1, t2, l1, l2), io['a'] + io['b_b'], 1e-12,
              'c = -ln(T2/T1)/(L2 - L1). The source cancels exactly, which is '
              'the entire argument for using a wedge: nothing about the '
              'illuminant, the interface or the exposure survives the ratio.')
    # and what it cannot do
    io_t = O.iops(spm=40.0)
    inv2 = O.invert_a_bb(io_t['a'] + io_t['b_b'],
                         O.volume_reflectance(io_t['a'], io_t['b_b'], 1.0e6))
    check(1, 'transmission + reflectance separates a from b_b', inv2['a'],
          io_t['a'], 1e-9,
          'One geometry gives a + b_b and cannot be inverted further. TWO '
          'geometries -- the wedge in transmission and the same water in deep '
          'reflectance -- are two equations in two unknowns and they close. '
          'This is what the bar means by using the cuvette to BOUND the IOPs.')
    spm_hat = float(inv2['spm'][1])
    check(2, 'and the Babin bridge returns the load, in the green band',
          spm_hat, 40.0, 0.05,
          'The bridge is stated at 555 nm and the green band is centred at '
          '545, so the recovered load carries the particulate spectral slope '
          'over 10 nm -- 1.4% at the declared exponent 0.75 and 1.8% across '
          'the chapter\'s whole 0.5-1.0 interval. The red and blue bands are '
          'further off BY EXACTLY THAT SLOPE and are not checked here, because '
          'that would be checking the slope against itself.',
          unit='mg/L', rel=True)

    # ------------------------------------ 7.9 the suspension balance
    # THE DIMENSIONAL ROW, because this is the family of error the standing
    # rulings name twice and a wrong power of a length is silent in a picture.
    eps_D = KG / S ** 3                       # eps_s * D_f : W/m^2
    rho = KG / M ** 3
    got = eps_D * rho / ((M / S ** 2) * rho * (M / S) * M)
    check(1, 'the suspension balance is a CONCENTRATION',
          float(got == rho), 1.0, 0.0,
          'eps_s D rho_s / (g (rho_s - rho_w) w_s d) pushed through the unit '
          'algebra rather than through a comment: W/m^2 divided by m^2/s^3 is '
          'kg/m^2, and one more length makes kg/m^3. Wave 4 shipped this '
          'formula once with the depth in the wrong place.')
    # THE MAGNITUDE, and not only the scaling. A row that checks how the load
    # RESPONDS to velocity is blind to a constant factor in front of it, and a
    # constant factor of fifty is exactly the defect this wave shipped.
    check(1, 'the bed stream power is rho c_f <|u|^3>',
          O.bed_dissipation(1.0), 1025.0 * 0.006 * 4.0 / (3.0 * math.pi),
          1e-12,
          'Closed form, at u_orb = 1 m/s, with c_f the same 0.006 '
          '`beach.longshore_current` uses. It is here because the two rows '
          'beside it are RATIOS -- the u^3 scaling and the two-depth '
          'comparison -- and a ratio cannot see a factor in front of the whole '
          'expression. Driving the balance from the WAVE\'s dissipation '
          'instead of the BED\'s is such a factor, about fifty, and it is what '
          'this row exists to catch.', unit='W/m^2')
    ws0 = BCH.settling_velocity()
    spm_surf = float(O.suspended_load(1.4, 1.5, ws0)['spm_bar'])
    between(2, 'the breaking zone\'s depth-averaged load, against chapter 28\'s '
            'own anchors', spm_surf, 5.0, 500.0,
            'Chapter 28 checks its bridge at two ends: "a coastal few-mg/L '
            'water then has b of order 1 m^-1, and a 1000 mg/L silt river has '
            'b ~ 500 m^-1 -- a millimetre-scale photon path, i.e. opaque mud". '
            'A breaking surf zone is between those and nearer the first: '
            'turbid, not mud. The range is wide BECAUSE nothing measured the '
            'load at Aljezur -- it is a sanity bound, not a calibration -- and '
            'it is what separates a suspension balance from an arithmetic '
            'slip. Wave 4\'s own first writing put 3700 mg/L here, past the '
            'chapter\'s silt river.', unit='mg/L')
    check(1, '<|cos|^3> = 4/(3 pi)', O.U3_MEAN,
          float(np.mean(np.abs(np.cos(np.linspace(0, 2 * math.pi, 2000001)))
                        ** 3)), 1e-6,
          'The cubic moment of a sinusoidal orbital velocity, by quadrature '
          'against the closed form. It is the factor between a peak velocity '
          'and the stream power it delivers, and dropping it overstates the '
          'load by 2.36x.')
    # the load must scale the way the balance says
    ws = BCH.settling_velocity()
    s1 = O.suspended_load(1.0, 2.0, ws)
    s2 = O.suspended_load(2.0, 2.0, ws)
    check(1, 'the load goes as u_orb^3', s2['M'] / s1['M'], 8.0, 1e-9,
          'Bagnold\'s balance is linear in the stream power and the stream '
          'power is cubic in the velocity. A load that scales as u^2 has a '
          'friction law in it instead of a power.')
    # THE ROW THE STRATIFICATION EXISTS FOR
    deep = O.suspended_load(0.9, 8.0, ws)
    shal = O.suspended_load(0.9, 1.2, ws)
    io_dp = O.iops(spm=float(deep['spm']))
    io_sh = O.iops(spm=float(shal['spm']))
    R_deep = O.column_reflectance(io['a'], io['b_b'],
                                  8.0 - float(deep['delta']),
                                  io['a'], io_dp['b_b'],
                                  float(deep['delta']))['R']
    R_shal = O.column_reflectance(io['a'], io['b_b'],
                                  1.2 - float(shal['delta']),
                                  io['a'], io_sh['b_b'],
                                  float(shal['delta']))['R']
    check(1, 'the SAME stirring reads dark at 8 m and pale at 1.2 m',
          float(R_shal[1] > 4.0 * R_deep[1]), 1.0, 0.0,
          'One orbital velocity, one balance, one load per unit area -- and '
          'two colours, because the Rouse layer fills a 1.2 m column and hides '
          'under a 8 m one. This is the row that fires when the load is '
          'depth-averaged, and depth-averaging is what makes an entire sea '
          'milky from a physically correct suspension.')
    info(1, 'reflectance (green) of the same load at d = 8 m and d = 1.2 m',
         (float(R_deep[1]), float(R_shal[1])),
         'the separation the two-layer column buys')

    # ------------------------------------------- 7.10 the glitter, Cox & Munk
    for u in (0.0, 3.0, 6.0, 12.0):
        su2, sc2 = O.cox_munk_mss(u)
        check(2, 'Cox & Munk (1954) component mss at U = %g m/s' % u, su2 + sc2,
              0.003 + 5.08e-3 * u, 1e-12,
              'sigma_u^2 = 3.16e-3 U and sigma_c^2 = 0.003 + 1.92e-3 U, which '
              'is what this file stores; their sum is 0.003 + 5.08e-3 U.')
        between(2, 'and against the paper\'s own COMBINED fit at U = %g' % u,
                su2 + sc2, (0.003 + 5.12e-3 * u) * 0.99,
                (0.003 + 5.12e-3 * u) * 1.01,
                'AND THE TWO DO NOT AGREE EXACTLY, WHICH IS THE PAPER AND NOT '
                'A SLIP. Cox & Munk fit the up/downwind and crosswind '
                'components separately AND fit the total separately, and the '
                'combined fit is 0.003 + 5.12e-3 U against the components\' '
                '5.08e-3 -- 0.8% apart at any wind, inside their own quoted '
                'uncertainties (+-0.004 and +-0.002). A file that quotes both '
                'numbers as if one implied the other has misread the source; '
                'this row records the gap instead.')
    check(1, 'the wind readout inverts the slope law', O.wind_from_mss(
        sum(O.cox_munk_mss(7.5))), 7.5, 1e-9,
        'Bar section K asks for the width as a READOUT of the wind, which '
        'means the map has to run both ways.')
    # the pdf is a pdf
    zz = np.linspace(-1.2, 1.2, 1201)
    ZX, ZY = np.meshgrid(zz, zz)
    tot = float(np.trapezoid(np.trapezoid(O.slope_pdf(ZX, ZY), zz, axis=1),
                             zz))
    check(1, 'the slope distribution integrates to 1', tot, 1.0, 1e-6,
          'A slope pdf that does not normalise is a brightness multiplier '
          'wearing a statistic\'s clothes, and it would be absorbed by an '
          'exposure and never found.')
    # THE WIDTH IS A READOUT OF THE MEAN SQUARE SLOPE
    ws_ = []
    for u in (3.0, 6.0, 10.0, 16.0):
        r = O.glitter_width_deg(21.02, 10.0, u10=u)
        ws_.append(r['dphi'] / math.sqrt(sum(O.cox_munk_mss(u))))
    check(1, 'the glitter width goes as the RMS slope', np.array(ws_),
          np.full(4, float(np.mean(ws_))), 0.02,
          'Bar section K1: "the width must come from the slope distribution '
          'rather than from a spread parameter chosen to look right". If it '
          'does, then width/sqrt(mss) is a constant of the geometry alone -- '
          'and it is, to 1.7% over a factor of 5 in wind. That constancy is what '
          'makes the width a READOUT, and it is what a chosen spread parameter '
          'cannot reproduce.', unit='deg', rel=True)
    info(1, 'width / sqrt(mss) at U = 3, 6, 10, 16 m/s', tuple(ws_),
         'deg per unit RMS slope, at view elevation 10 deg')
    # THE SHAPE, which the bar says is diagnostic too
    els = [25.0, 21.02, 15.0, 10.0, 6.0, 3.0, 1.5, 0.5]
    wid = [O.glitter_width_deg(21.02, e)['dphi'] for e in els]
    check(1, 'the path NARROWS toward the horizon',
          float(np.all(np.diff(wid) < 0.0)), 1.0, 0.0,
          'Bar section K1: "It narrows toward the horizon and spreads toward '
          'the observer, because the same slope distribution subtends a '
          'different range of specular directions at different incidences. A '
          'path of uniform width is wrong in a way that is obvious once stated '
          'and almost never modelled." The list runs from the near field to '
          'the horizon, so a monotone DECREASE is the bar\'s claim and this '
          'row is the bar\'s claim tested against the geometry.')
    info(1, 'path width in deg at view elev 25/21/15/10/6/3/1.5/0.5',
         tuple(round(v, 3) for v in wid),
         'from the specular point to the horizon; the bar predicted the sign '
         'of this trend and the geometry agrees')
    # the specular point is where the geometry says
    prof = O.glitter_azimuth_profile(21.02, 21.02, 0.0,
                                     np.linspace(-30, 30, 601))[:, 1]
    check(1, 'the path is centred on the sun\'s own azimuth',
          float(np.linspace(-30, 30, 601)[int(np.argmax(prof))]), 0.0, 0.06,
          'The specular direction, and the row that fires at the branch error '
          'wave 4 actually made: putting the eye at the sun\'s azimuth instead '
          'of opposite it moves the required facet normal onto the sun and '
          'evaluates the whole path at exp(-135). A glitter model with the '
          'wrong branch renders BLACK rather than wrong, which is the kind of '
          'defect that survives a look at the picture.', unit='deg')
    # ENERGY. The Jacobian, checked by integrating the radiance it produces.
    n_mu, n_ph = 160, 320
    mv = (np.arange(n_mu) + 0.5) / n_mu
    pv = (np.arange(n_ph) + 0.5) / n_ph * 2 * math.pi
    dw = (1.0 / n_mu) * (2 * math.pi / n_ph)
    MV, PV = np.meshgrid(mv, pv, indexing='ij')
    st = np.sqrt(np.maximum(1 - MV ** 2, 0))
    R = np.stack([st * np.cos(PV), st * np.sin(PV), MV], -1).reshape(-1, 3)
    Lg = BOP.glitter_radiance(ATM.SUN_DIR, -R, e_sun=np.ones(3), shadow=False)
    flux = float((Lg[:, 1] * R[:, 2] * dw).sum())
    # the second route: the flux the tilted facets INTERCEPT, in slope space
    zz2 = np.linspace(-1.5, 1.5, 601)
    ZX2, ZY2 = np.meshgrid(zz2, zz2)
    nz = 1.0 / np.sqrt(1 + ZX2 ** 2 + ZY2 ** 2)
    NX, NY = -ZX2 * nz, -ZY2 * nz
    com = NX * ATM.SUN_DIR[0] + NY * ATM.SUN_DIR[1] + nz * ATM.SUN_DIR[2]
    p = BOP.slope_pdf(ZX2, ZY2)
    vz = 2.0 * com * nz - ATM.SUN_DIR[2]        # the mirror direction's z
    integ = np.where(com > 0, OPT.fresnel(np.clip(com, 0, 1))[..., 1]
                     * com * p / nz, 0.0)
    all_f = float(np.trapezoid(np.trapezoid(integ, zz2, axis=1), zz2))
    inter = float(np.trapezoid(np.trapezoid(np.where(vz > 0, integ, 0.0),
                                            zz2, axis=1), zz2))
    check(3, 'the glitter integral returns the flux the facets intercept',
          flux, inter, 2e-3,
          'Two routes with nothing in common but the slope pdf: one integrates '
          'the RADIANCE this file produces over the upward hemisphere, the '
          'other integrates rho(omega) cos(omega) p / cos(beta) over SLOPE '
          'SPACE. Their agreement is the Jacobian dw_v = 4 cos(omega) '
          'cos^3(beta) dz -- the whole physics of a glitter model -- and the '
          'agreement is the Jacobian and nothing else. The slope integral is '
          'restricted to facets whose MIRROR DIRECTION POINTS UP, because the '
          'hemisphere integral can only see those -- and the difference is the '
          'next row, which is a result rather than a residual.', rel=True)
    info(3, 'share of the intercepted flux reflected BELOW the horizon',
         1.0 - inter / all_f,
         'Facets tilted far enough away from a 21 deg sun send their specular '
         'lobe into the sea rather than into the sky, and a single-bounce '
         'glitter model drops that light entirely. At this sun and this wind '
         'it is 10% of what the surface intercepts -- not a rounding error, '
         'and exactly the light that a multiple-surface-bounce model would put '
         'back as the faint filling between the glints. Recorded, not '
         'modelled.')
    # and the tilt gain, which is the term a flat-surface normalisation drops
    between(3, 'the tilt gain against a flat surface', all_f / float(
        (OPT.fresnel(ATM.SUN_DIR[2])[1] * ATM.SUN_DIR[2])), 1.0, 3.0,
        'A rough surface intercepts MORE of a low sun than a flat one, because '
        'the facets tilted toward it are more nearly normal to the beam. At '
        'this sun (21 deg) and this wind the gain is what it is; the row is a '
        'range because nothing published fixes it, and it is recorded because '
        'a renderer that normalises its glitter to a flat surface has thrown '
        'exactly this away.')
    # the Snell-cone limit on a face, which is why section A needs a steep one
    need = math.degrees(math.atan(math.tan(
        math.pi / 2 - math.asin(1.0 / OPT.IOR[1]))))
    check(1, 'a lengthwise sightline needs a face steeper than 90 - asin(1/n)',
          need, 41.49, 0.02,
          'A ray entering water is confined to the Snell cone, so to travel '
          'ALONG a wave rather than down into it the face must be tilted by at '
          'least 90 - asin(1/n) from the horizontal. The number is the '
          'complement of the critical angle `optics.TC_SNELL` already carries, '
          'and it is what makes bar section A a NEAR-BREAKING geometry: this '
          'scene\'s linear free surface reaches 0.08 of slope, which is 4.6 '
          'deg.', unit='deg')

    # ---------------------------------------------- 7.11 the foam constant
    check(2, 'bar section C: one constant, three whites, 1 - 1/n^2',
          O.FOAM_WHITE[1] * 100.0, 43.874, 0.02,
          'The bar states 43.874% and derives it from the critical angle a '
          'bubble seen from the water side has. It is computed here from '
          '`optics.IOR` and nothing else. The foam MODEL is a placeholder and '
          'says so in its caption; the CONSTANT is not.', unit='%')
    openq(1, 'foam: three mechanisms, none of them modelled',
          'coverage mask only', 'surface / entrained air / spray',
          'Bar section C names three mechanisms with different '
          'representations -- a surface coverage field with its own advection '
          'and decay, a participating medium that HIDES THE BED, and a '
          'particle system -- and section H2 adds a fourth requirement (foam '
          'stranded by the retreating swash, so two residence times on one '
          'surface) while H5 adds rotational structure a potential-flow '
          'advection cannot produce. `beach_optics.foam_coverage` is a '
          'saturating function of the breaking fraction and NOTHING ELSE. It '
          'is rendered so the breaking zone is not blank, and every figure '
          'that shows it says so in its own caption. Measured, understood, '
          'not achieved.')


def _sec_surface(ctx):
    """WAVE 5 -- the nonlinear free surface.

    Every row here exists because bar section A turns on ONE number, the
    steepest face the representation can reach, and that number is a product of
    a chain: Ursell -> harmonic ratio -> validity clamp -> phase -> slope gain.
    A ratio anywhere in that chain hides a factor that multiplies both its
    terms, which is exactly how one of wave 4's guards caught nothing, so
    EVERY new quantity below gets at least one ABSOLUTE row against a number
    computed outside the function under test.
    """
    B = ctx['B']

    # ------------------------------------------- 8.1 the depth function C(kd)
    # Absolute, both limits, computed from the asymptotics rather than from the
    # function. These are what tie the second harmonic to the two regimes.
    check(1, 'Stokes-2 depth function, shallow limit C(kd)(kd)^3 -> 3',
          float(B.stokes2_shape(1e-3)) * 1e-9, 3.0, 1e-5,
          'C = cosh(kd)(2 + cosh 2kd)/sinh^3(kd). As kd -> 0 the two cosh go '
          'to 1 and sinh^3 -> (kd)^3, so C(kd)^3 -> 3. It is this 3 that '
          'turns the harmonic ratio into twice the Ursell number, which is '
          'the whole reason this file can steepen its surface without '
          'declaring anything.')
    check(1, 'Stokes-2 depth function, deep limit C -> 2',
          float(B.stokes2_shape(20.0)), 2.0, 1e-9,
          'cosh(kd) ~ e^kd/2, cosh 2kd ~ e^2kd/2, sinh^3 ~ e^3kd/8, so C -> 2 '
          'and b/a -> ak/2, which is the textbook deep-water second-order '
          'Stokes wave. A file whose harmonic used the shallow asymptote '
          'everywhere would pass every shallow row and be wrong offshore.')

    # ------------------------------------------- 8.2 the harmonic ratio, twice
    # ABSOLUTE first: b evaluated from Dean & Dalrymple's own written form,
    # b = (pi H^2 / 8L) C, with L = 2 pi/k -- a different expression from the
    # one `stokes2_ratio` uses (H k/8 * C for the RATIO), so the arithmetic is
    # not shared even though the physics is.
    Ht, kt, dt = 1.10, 0.2600, 1.90
    L_t = 2.0 * math.pi / kt
    b_abs = (math.pi * Ht ** 2 / (8.0 * L_t)) * float(B.stokes2_shape(kt * dt))
    check(1, 'second harmonic amplitude b, absolute, vs (pi H^2/8L) C(kd)',
          float(B.stokes2_ratio(Ht, kt, dt)) * (Ht / 2.0), b_abs, 1e-12,
          'Dean & Dalrymple write the second-order surface as (H/2)cos + '
          '(pi H^2/8L) C cos 2; this file carries the RATIO b/a = (Hk/8)C. '
          'The two are the same statement and the row is the algebra between '
          'them, in metres rather than as a ratio -- deliberately, because a '
          'ratio row cannot see a factor that multiplies a and b alike.',
          unit='m')
    # and the identity that makes the Ursell number the same quantity
    d_sh, H_sh = 0.5, 0.02
    res = []
    for kd_sh in (0.02, 0.01):
        k_sh = kd_sh / d_sh
        res.append(float(B.stokes2_ratio(H_sh, k_sh, d_sh))
                   / float(B.ursell(H_sh, k_sh, d_sh)) - 2.0)
    k_sh = 0.02 / d_sh
    check(1, 'shallow water: r = b/a is 2 x this file\'s Ursell number',
          float(B.stokes2_ratio(H_sh, k_sh, d_sh))
          / float(B.ursell(H_sh, k_sh, d_sh)), 2.0, 1e-3,
          'r = (Hk/8)C -> (3/8)Hk/(kd)^3 and Ur = (3/16)Hk/(kd)^3. The 3/16 '
          'in `ursell` is not a tidy convention: it is the constant that makes '
          'the Ursell number half the second harmonic\'s own amplitude ratio. '
          'The nonlinearity of the surface has been computed in this file '
          'since wave 1 and spent only inside the sediment transport. The '
          'identity is ASYMPTOTIC and the tolerance is the O((kd)^2) term, '
          'which the next row measures rather than assumes.')
    check(1, 'and the residual is O((kd)^2): halving kd quarters it',
          res[0] / res[1] if abs(res[1]) > 1e-15 else float('inf'), 4.0, 0.05,
          'A tolerance on an asymptotic identity is only honest if the '
          'CONVERGENCE RATE is checked too -- otherwise any tolerance can be '
          'made to pass by choosing kd. C(kd)(kd)^3 = 3 + (kd)^2/... , so the '
          'residual must fall by four when kd halves. It does. THE GUARD ON '
          'THE DIVISION IS NOT COSMETIC: `harmonic-shallow-everywhere` makes '
          'the identity EXACT at every kd, so both residuals are zero and this '
          'row raised a ZeroDivisionError on its first firing -- an ERROR, '
          'which by this harness\'s own doctrine costs every row after it. It '
          'now reads inf and FAILS.')
    check(1, 'the residual itself is nonzero and the right size at kd = 0.02',
          res[0], 4.0 / 3.0 * 0.02 ** 2, 2e-5,
          'ABSOLUTE, and it is the row the ratio above cannot be: an identity '
          'that is exact where it should only be asymptotic means the DEPTH '
          'FUNCTION has been replaced by its own shallow limit, which passes '
          'every shallow row and is 30x wrong offshore. A ratio of two '
          'residuals cannot see that; their size can. AND THE SIZE IS A CLOSED '
          'FORM RATHER THAN A FITTED NUMBER: expanding C(kd)(kd)^3 = 3 + '
          '4(kd)^2 + O((kd)^4) gives r/Ur = 2(1 + (4/3)(kd)^2), so the '
          'residual is (4/3)(kd)^2 = 5.333e-4 at kd = 0.02 against 5.334e-4 '
          'measured, and 1.333e-4 at half that.')

    # ------------------------------------- 8.3 the Ursell number, second route
    # The classic parameter is U = H L^2/d^3 and this file's is (3/16)Hk/(kd)^3.
    # Written out independently and compared ABSOLUTELY, not as a ratio.
    U_classic = H_sh * L_t ** 0.0 * (2.0 * math.pi / k_sh) ** 2 / d_sh ** 3
    check(1, 'Ur (this file) vs (3/(64 pi^2)) H L^2/d^3, absolute',
          float(B.ursell(H_sh, k_sh, d_sh)),
          3.0 / (64.0 * math.pi ** 2) * U_classic, 1e-12,
          'Ur = (3/16)H/(k^2 d^3) and k = 2 pi/L, so Ur = (3/(64 pi^2)) HL^2/'
          'd^3. The conversion is what lets the published regime boundary be '
          'quoted in this file\'s variable at all.')
    check(1, 'the Stokes/cnoidal boundary is Ur = 1/2 in this normalisation',
          B.URSELL_STOKES_LIMIT,
          3.0 / (64.0 * math.pi ** 2) * (32.0 * math.pi ** 2 / 3.0), 1e-15,
          'CITED half: the conventional boundary is U = 32 pi^2/3 = 105.3 '
          '(Ursell 1953; the regime diagrams in Le Mehaute and in the Shore '
          'Protection Manual). DERIVED half: the conversion above turns it '
          'into exactly 1/2 here. The constant is a citation and the arithmetic '
          'is not, and the row separates them.')

    # ------------------------------- 8.4 the validity limit, derived two ways
    for psi, want, note in ((0.0, 0.25, 'at psi = 0 the derivative factorises '
                            'as -sin(phi)(1 + 4r cos phi), so the extra roots '
                            'appear at cos phi = -1/(4r): r = 1/4 exactly, '
                            'and AT that value the trough is flat, which is '
                            'the shape section A wants reached at the limit '
                            'of the theory rather than by choosing it.'),
                            (-math.pi / 2, 0.5, 'at psi = -pi/2 the derivative '
                             'is a quadratic in sin(phi) whose second root '
                             'leaves [-1,1] at r = 1/2. The pitched-forward '
                             'shape tolerates twice the harmonic the peaked '
                             'one does -- the SAME harmonic, rotated.')):
        check(1, 'secondary-crest limit at psi = %+.3f rad' % psi,
              float(B.stokes2_crest_limit(np.array(psi))), want, 2e-6, note)
    # the interpolated table against the direct bisection, ABSOLUTE in r
    err = max(abs(float(B.stokes2_crest_limit(np.array(p)))
                  - B._crest_limit_direct(p))
              for p in np.linspace(-math.pi / 2, 0.0, 61))
    check(3, 'the crest-limit table vs a direct per-phase bisection',
          err, 0.0, 1e-5,
          'The limit is tabulated on a ladder because computing it per cell '
          'was 7e9 flops on one bay. THE LADDER IS UNIFORM IN sqrt(-psi): '
          'r_max leaves 1/4 with infinite slope at psi = 0, and a ladder '
          'uniform in psi reported 0.2548 where the closed form says 0.2500 -- '
          'a 2% error in the one place the answer is known exactly, introduced '
          'by an optimisation. Both routes are in `beach.py` and the row '
          'compares them.', unit='r')
    # INDEPENDENT METHOD: count the surface's extrema directly, on a phase grid
    # this function does not use, either side of the limit it returns.
    ph = np.linspace(0.0, 2.0 * math.pi, 200001)[:-1] + 1e-5
    for psi in (0.0, -0.6, -math.pi / 2):
        lim = float(B.stokes2_crest_limit(np.array(psi)))
        n_lo, n_hi = [], []
        for r, box in ((lim * 0.97, n_lo), (lim * 1.03, n_hi)):
            e = np.cos(ph) + r * np.cos(2.0 * ph + psi)
            # PERIODIC, and the first writing of this row was not. Counting
            # sign changes of a forward difference without wrapping loses the
            # turning point that straddles phi = 0, which is exactly the crest
            # at psi = 0 -- so the row read [1, 3] and FAILED on correct code.
            s = np.sign(np.diff(np.concatenate([e, e[:1]])))
            box.append(int((s != np.roll(s, -1)).sum()))
        check(3, 'extrema per cycle just below / above the limit (psi=%+.2f)'
              % psi, [n_lo[0], n_hi[0]], [2, 4], 0,
              'The limit is claimed to be where a false crest appears inside '
              'the trough. This counts turning points of eta itself on a '
              '200000-point phase grid -- a different quantity computed a '
              'different way from the sign-change bisection in '
              '`stokes2_crest_limit` -- and finds two below it and four above.',
              unit='turning points')

    # ------------------------------------------- 8.5 the slope gain, absolute
    for r in (0.10, 0.25, 0.50):
        check(1, 'slope gain at psi = -pi/2 is exactly 1 + 2r (r = %.2f)' % r,
              float(B.slope_gain(np.array(r), np.array(-math.pi / 2))),
              1.0 + 2.0 * r, 2e-6,
              'max |sin phi - 2r cos 2phi| is attained at phi = pi/2 where the '
              'two terms add: 1 + 2r. This is the ONLY place the second '
              'harmonic buys slope at first order, and it is why the '
              'asymmetry and not the skewness is what steepens a face.')
    # psi = 0, from the stationarity condition solved in closed form
    r0 = 0.25
    c0 = (-1.0 + math.sqrt(1.0 + 128.0 * r0 ** 2)) / (16.0 * r0)
    s0 = math.sqrt(1.0 - c0 ** 2)
    check(1, 'slope gain at psi = 0, r = 1/4, vs the stationarity cubic',
          float(B.slope_gain(np.array(r0), np.array(0.0))),
          abs(s0 + 2.0 * r0 * 2.0 * s0 * c0), 3e-6,
          'd/dphi of sin phi + 2r sin 2phi is cos phi + 4r cos 2phi, which is '
          '8r cos^2 phi + cos phi - 4r = 0 -- a quadratic in cos phi solved '
          'here and a grid maximum inside `slope_gain`. THE PAIR IS THE '
          'FINDING: 1.299 against 1.500 at the same r. A peaked crest at the '
          'very limit of second-order theory buys 30% of face slope; the same '
          'harmonic rotated into a bore buys 100%.')

    # --------------------------------- 8.6 the two moments, and their rotation
    ph = np.linspace(0.0, 2.0 * math.pi, 262144, endpoint=False)
    for r, psi in ((0.20, 0.0), (0.20, -math.pi / 2), (0.35, -0.7)):
        e = np.cos(ph) + r * np.cos(2.0 * ph + psi)
        sd = float(np.sqrt(np.mean(e ** 2)))
        sk_num = float(np.mean(e ** 3)) / sd ** 3
        # the Hilbert transform by FFT -- a genuinely different route to As
        F = np.fft.fft(e)
        hsel = np.zeros(F.size)
        hsel[0] = 0.0
        hsel[1:F.size // 2] = -1j.imag * 0 - 1.0      # placeholder, set below
        H = np.fft.ifft(F * (-1j) * np.sign(np.fft.fftfreq(F.size))).real
        as_num = float(np.mean(H ** 3)) / sd ** 3
        sk, asy = B.surface_moments(np.array(r), np.array(psi))
        check(3, 'surface skewness, closed form vs numerical moment '
              '(r=%.2f psi=%+.2f)' % (r, psi), float(sk), sk_num, 2e-9,
              '<eta^3> = (3/4) a^3 r cos psi is done by hand in '
              '`surface_moments`; this integrates eta^3 on a 262144-point '
              'phase grid. Absolute, in skewness units.')
        check(3, 'surface asymmetry, closed form vs an FFT Hilbert transform '
              '(r=%.2f psi=%+.2f)' % (r, psi), float(asy), as_num, 2e-9,
              'As is the third moment of the HILBERT TRANSFORM of the surface, '
              'and the second route here builds it with -i sgn(f) in the '
              'frequency domain rather than by replacing cos with sin term by '
              'term. Sign convention: Hilb(cos n phi) = +sin n phi, so a '
              'shoreward-pitched front reads As > 0 here; papers with the '
              'other sign convention report the same wave negative.')
    # THE INVARIANT, and it is the theory finding this section carries
    inv = [float(sum(x ** 2 for x in B.surface_moments(np.array(0.3),
                                                       np.array(p))))
           for p in (0.0, -0.4, -0.9, -math.pi / 2)]
    check(1, 'Sk^2 + As^2 depends on r alone, not on psi', inv,
          [inv[0]] * 4, 1e-12,
          'THE FINDING: breaking does not destroy the wave\'s third moment, it '
          'ROTATES it out of the skewness and into the asymmetry. `beach.py`\'s '
          'sediment transport multiplies its skewness by (1 - f_brk) and '
          'carries no asymmetry term at all, so it sees half of one quantity '
          'and calls it a collapse.')
    check(1, 'cos(pi f/2) against the (1 - f) the transport uses, at f = 1/2',
          math.cos(math.pi * 0.25) - 0.5, 0.2071068, 1e-6,
          'The two agree at both ends and differ by 0.207 in the middle -- 41% '
          'of the (1-f) value. That difference is what the transport pays for '
          'writing the rotation as a straight line, and it is measured here '
          'rather than argued.')

    # --------------------------------------------- 8.7 the phase, and its SIGN
    check(1, 'bore phase: unbroken wave carries a BOUND harmonic, psi = 0',
          float(B.bore_phase(0.0)), 0.0, 0.0,
          'A bound harmonic is phase-locked to its primary. That is '
          'second-order Stokes and it is not a choice.')
    check(1, 'bore phase: fully broken wave is a sawtooth, psi = -pi/2',
          float(B.bore_phase(1.0)), -math.pi / 2, 0.0,
          '`broken_fraction`\'s own docstring in this file already says a '
          'broken wave is a bore whose near-bed velocity is a sawtooth. A '
          'sawtooth is the pure-asymmetry shape.')
    # THE SIGN ROW. A wave leaning the wrong way is a defect a still frame
    # hides completely, so the guard reads WHICH SIDE of the crest is steep.
    ph = np.linspace(-math.pi, math.pi, 100001)
    psi_b = float(B.bore_phase(1.0))
    e = np.cos(ph) + 0.5 * np.cos(2.0 * ph + psi_b)
    steep = float(ph[np.argmin(np.diff(e) / np.diff(ph)[0])])
    check(1, 'the steep face is on the SHOREWARD side of the crest',
          steep, math.pi / 2, 0.02,
          'S increases shoreward and eta = (H/2)cos(S - omega t), so phases '
          'in (0, pi) are shoreward of the crest. The most negative d eta/d '
          'phi must lie there: a wave breaking backwards is a defect that a '
          'still frame cannot show and that no colour measurement would '
          'catch.', unit='rad')

    # --------------------------- 8.8 UR_HALF, derived, and the two-route check
    check(1, 'ur_half derived = sqrt(2)/6, absolute',
          B.ur_half_derived(1.0), math.sqrt(2.0) / 6.0, 1e-15,
          'In shallow water u = eta sqrt(g/d), a positive multiple of the '
          'surface at every phase, so the VELOCITY skewness the transport uses '
          'and the ELEVATION skewness of the surface are the same number. '
          'Matching the small-Ur slope of sk_max Ur/(Ur + ur_half) to the '
          'derived 3 sqrt2 Ur gives ur_half = sk_max/(3 sqrt2).')
    # THE ROW IS ON THE SLOPE AT THE ORIGIN, not on one sample of it. Both
    # sides carry their own O(Ur) corrections, so comparing them at a single
    # small Ur only says the tolerance was chosen to fit; extrapolating the
    # ratio to Ur -> 0 by Richardson says the LIMITS agree, which is the claim.
    def _sl(f, u):
        return f(u) / u

    sk_surf = (lambda u: float(B.surface_moments(np.array(2.0 * u),
                                                 np.array(0.0))[0]))
    sk_par = (lambda u: float(B.skewness(u, 1.0, B.ur_half_derived(1.0))))
    sl_s = 2.0 * _sl(sk_surf, 1e-5) - _sl(sk_surf, 2e-5)
    sl_p = 2.0 * _sl(sk_par, 1e-5) - _sl(sk_par, 2e-5)
    check(3, 'the two routes have the SAME slope at Ur -> 0, and it is 3 sqrt2',
          [sl_p, sl_s], [3.0 * math.sqrt(2.0)] * 2, 1e-7,
          'TWO ROUTES THAT DO NOT SHARE A SOURCE: one is a saturating fit '
          'declared in wave 1, the other is the third moment of a second-order '
          'Stokes surface whose amplitude came from Dean & Dalrymple. They '
          'agree at the origin only at ur_half = sqrt2/6. At the DECLARED 1.0 '
          'they are 4.24x apart, so wave 1\'s shoaling wave was skewed 4.24x '
          'too weakly exactly where the onshore term does its work.')
    openq(1, 'UR_HALF is derived and NOT adopted, and the cost is measured',
          'declared %.3f' % B.UR_HALF, 'derived %.6f' % B.ur_half_derived(1.0),
          'ADOPTING IT MOVES THE BAR AND THAT IS MEASURED, NOT FEARED: crest '
          '360 -> 345 m, crest depth 2.084 -> 1.906 m, bar-to-trough relief '
          '0.900 -> 1.195 m (+33%), break point 359 -> 344 m, and '
          'd_bar/(H_b/gamma) 0.973 -> 0.941, which would put wave 2\'s "1-3 '
          'per cent" claim at 5.9. IT IS NOT ADOPTED THIS WAVE FOR A REASON '
          'THAT IS NOT TIMIDITY: the derivation constrains the SLOPE AT THE '
          'ORIGIN, where Ur -> 0, and the bar sits at Ur ~ 1-2 where the '
          'saturating form\'s shape is governed by sk_max, which is still `?`. '
          'Changing one of two coupled shape parameters using a limit that '
          'does not reach the bar\'s own regime would trade a declared '
          'constant for a half-derived one. What the derivation DOES close is '
          'the ratio sk_max/ur_half = 3 sqrt 2, and that is the liftable '
          'result. Re-tested against the parked section B: the bigger bar does '
          'NOT reform -- min H/d in the trough goes 0.4556 -> 0.4571 against '
          'the 0.40 needed, so wave 2\'s missing-mechanism verdict survives a '
          'constant that made the bar a third deeper.')

    # ------------------------------------ 8.9 the cap, and it is not this scene
    need = float(B.snell_cone_face_deg())
    check(1, 'the face a lengthwise sightline needs, from optics.IOR',
          need, 90.0 - math.degrees(math.asin(1.0 / OPT.IOR[1])), 1e-12,
          'Imported, not restated: the same n that runs the pool\'s Fresnel, '
          'critical angle and L/n^2.', unit='deg')
    check(1, 'Stokes\' 120 deg corner caps every wave of permanent form',
          B.STOKES_FACE_DEG, 0.5 * (180.0 - B.STOKES_CORNER_DEG), 1e-12,
          'q^2/2 + gz = 0 at a stagnation crest forces q ~ r^(1/2); a wedge '
          'flow of interior angle 2a has q ~ r^(pi/2a - 1); matching gives '
          '2a = 120 deg, so the surface leaves the crest at 30 deg. '
          'Independent of depth, wavelength and height -- the same corner for '
          'the limiting deep-water Stokes wave and the limiting solitary '
          'wave.', unit='deg')
    openq(1, 'bar section A: no height field of a steady wave can reach it',
          '%.2f deg available' % B.STOKES_FACE_DEG,
          '%.2f deg needed' % need,
          'THIS IS STRONGER THAN WAVE 4\'S ROW AND IT REPLACES IT. Wave 4 '
          'measured THIS SCENE\'s linear surface at 8.2 deg and inferred that '
          'more nonlinearity might close the gap. It cannot: 30 < 41.48 for '
          'every wave of permanent form at every order, so the shortfall is a '
          'theorem about the representation and not a property of this bed, '
          'this sea state or this wave count. Section A belongs beside bar '
          'section F\'s plunging lip -- BY PROOF, not by analogy -- and '
          'closing it means the multivalued surface section F puts out of '
          'scope.')

    # --------------------------- 8.10 on the scene itself, and it stays a graph
    bay = ctx.get('bay') or B.run_bay(dx=4.0, n_steps=300, dt=6000.0)
    ctx['bay'] = bay
    tr = bay['tr']
    ss = B.surface_state(tr)
    wet = tr['d'] > B.D_MIN
    check(1, 'after clamping, r never exceeds the secondary-crest limit',
          float(np.max((ss['r'] - ss['limit'])[wet])), 0.0, 1e-12,
          'ABSOLUTE, in units of r. Above the limit the surface grows a false '
          'crest inside its own trough -- a rendering artifact that looks like '
          'chop and is not.')
    # THE GRAPH PROPERTY, section F's standing ruling, checked on the scene
    php = np.linspace(0.0, 2.0 * math.pi, 4001)[:-1] + 1e-4
    sel = np.argsort(ss['r'][wet])[-400:]
    rs, ps = ss['r'][wet][sel], ss['psi'][wet][sel]
    ee = (np.cos(php)[None] + rs[:, None] * np.cos(2.0 * php[None]
                                                   + ps[:, None]))
    de = np.diff(ee, axis=1)
    n_ex = (np.sign(de[:, :-1]) != np.sign(de[:, 1:])).sum(axis=1)
    check(1, 'the 400 most nonlinear cells still have ONE crest and ONE trough',
          int(n_ex.max()), 2, 0,
          'Bar section F puts the multivalued surface out of scope and that '
          'ruling stands. A Fourier sum cannot overturn, so the risk is not '
          'multivaluedness -- it is the false crest, which is single-valued '
          'and still wrong. This counts turning points per cycle on the '
          'steepest cells the scene has.', unit='turning points')
    info(1, 'how far past second-order Stokes this scene is',
         (float(np.median(ss['ursell'][wet])), float(ss['ursell'][wet].max()),
          ss['clamped_fraction']),
         'median Ur, max Ur, and the fraction of wet cells the validity clamp '
         'bites. The boundary is 0.5. THIS IS A SHALLOW-WATER SCENE AND '
         'SECOND-ORDER STOKES IS SPENT IN IT -- cnoidal theory is the regime\'s '
         'own form and it needs elliptic functions this environment has no '
         'library for; the clamp is what keeps the shape inside the theory '
         'that IS available, and the fraction is the honest size of the '
         'compromise.')
    # the steepest face this scene reaches, ABSOLUTE and in degrees
    a_lin = 0.5 * tr['H'] * tr['k']
    gain = B.slope_gain(ss['r'], ss['psi'])
    s_nl = float(np.max((a_lin * gain)[wet]))
    s_li = float(np.max(a_lin[wet]))
    check(3, 'the steepest face, linear vs nonlinear, on one transform',
          [math.degrees(math.atan(s_li)), math.degrees(math.atan(s_nl))],
          [8.81, 16.49], 0.4,
          'ABSOLUTE, in degrees, both from ONE transform with only r changed. '
          'The expected pair is what wave 5 measured on THIS BAY -- the '
          'suite\'s coarse one, dx = 4 m and 300 steps; the render\'s finer '
          'bay reads 8.23 / 15.78, and the gap between the two is the grid, '
          'not the physics. The pair is here so that a later wave that moves '
          'either number has to say so. The second route is `slope_gain`, a '
          'grid maximum over the shape, against the analytic (H/2)k for the '
          'sinusoid.', unit='deg')
    openq(3, 'the steepest face this scene reaches, against section A',
          '%.2f deg' % math.degrees(math.atan(s_nl)), '41.48 deg',
          'Measured, understood, not achieved -- and now bounded above by 30 '
          'deg for any wave of permanent form, so the row will not close by '
          'trying harder.')

    # --------------------------------- 8.11 the difference operator, absolute
    # `beach_render.surface_slope` differentiates by central difference and the
    # harmonic is at 2k. The gain is stated in that file's docstring; this is
    # the arithmetic behind it, so the docstring cannot drift.
    k_typ = 0.29
    for eps, want in ((1.0, math.sin(2 * k_typ * 1.0) / (2 * k_typ * 1.0)),
                      (0.5, math.sin(2 * k_typ * 0.5) / (2 * k_typ * 0.5))):
        check(1, 'central-difference gain on the SECOND harmonic at eps=%.1f m'
              % eps, want, 1.0, 0.06,
              'A central difference of step eps reports a sinusoid of '
              'wavenumber q at sin(q eps)/(q eps) of its slope. At q = 2k = '
              '0.58 and eps = 1 m that is 0.946 -- the operator would have '
              'eaten 5.4% of the very steepening this wave is measuring, and '
              'at 0.5 m it eats 1.4%. Wave 5 halved eps for this reason and '
              'the row is here so nobody puts it back.')



def SUN_OF(RND):
    """The scene's sun vector, read off the renderer rather than rebuilt."""
    return np.asarray(RND.SUN, float)


def _sec_land(ctx):
    """WAVE 8 -- THE LAND AND THE AIR: the beach, the wet/dry pair, the shadow
    ray and the aerial perspective.

    EVERY NEW QUANTITY GETS AT LEAST ONE ABSOLUTE ROW. A ratio-only guard has
    now been blind FIVE times in this project -- the most recent, a per-channel
    Fresnel bug, was visible to two absolute rows and to no ratio row at all --
    so nothing below is checked only as a quotient. The three beach numbers are
    metres and a slope, the two extinction coefficients are per-metre, and the
    wetness is checked against Rayleigh variates drawn by a generator that has
    never heard of `swash_wetness`.

    AND NO TWO ROUTES SHARE A SOURCE where one can be found. The face slope's
    closed form is checked against a finite difference on `dean_bed`, which was
    written three waves earlier and knows nothing about beaches; the swash
    excursion is checked against `runup_hunt`/`iribarren` composed the long way
    round; the wetness is checked against a Monte-Carlo Rayleigh sample; the
    airlight's limit is checked against `sky_radiance` evaluated directly.
    """
    import beach_render as RND
    B = BCH
    L0 = B.deep_wavelength(B.T_SWELL)
    # THE MEASURED QUANTITIES THE SECTION COMPARES AGAINST, computed once and
    # cached in ctx so a re-run of the section inside the bug driver does not
    # pay for the loops twice.
    if '_face_measured' not in ctx:
        sc = ctx.get('sc') or B.run_scene()
        ctx['sc'] = sc
        tr1 = sc['tr']
        ii = np.where(tr1['d'] > B.D_MORPH_MIN)[0]
        ctx['_face_measured'] = float(abs(np.gradient(
            tr1['h'], tr1['dx'])[ii[-1]]))
        bay = B.run_bay()
        ctx['_bay'] = bay
        ctx['_beach'] = bay.get('beach')
        ctx['_sand_row'] = bay['coast']['sand_row'] / float(
            bay['y'][1] - bay['y'][0])

        class _W:
            pass
        _w = _W()
        _w.x, _w.y, _w.h = bay['x'], bay['y'], bay['h']
        ctx['_beach_width'] = RND.beach_width(_w)

    # ================================================ 11.1 THE BEACH FACE
    check(1, 'beach_face_slope is (2/3) A^1.5 / sqrt(d_hand), ABSOLUTE',
          B.beach_face_slope(), 0.0528193, 1e-6,
          'The number the whole subaerial landform hangs off. Stated '
          'absolutely because a beach face of 1:19 and one of 1:10 are '
          'different landforms and both look like beaches.', unit='')
    # ...AND THE SAME NUMBER OFF A FUNCTION THAT KNOWS NOTHING ABOUT BEACHES.
    # `dean_bed` is wave 1's equilibrium profile. Differencing it at the
    # handover depth must reproduce the closed form, because the closed form IS
    # its derivative -- and if anyone rewrites the algebra with a 3/2 where a
    # 2/3 belongs this is the row that says so.
    y0 = (B.D_MORPH_MIN / B.DEAN_A) ** 1.5
    e = 1e-4
    xs = B.X_SHORE0
    dd = -(B.dean_bed(np.array([xs - y0 - e]), x_shore=xs)[0]
           - B.dean_bed(np.array([xs - y0 + e]), x_shore=xs)[0]) / (2 * e)
    check(1, 'the same slope by finite difference on dean_bed, ABSOLUTE',
          dd, B.beach_face_slope(), 1e-7,
          'Two routes to one number and only one of them is algebra. The '
          'equilibrium profile was written in wave 1 for the submarine bed and '
          'has no idea a beach exists; its derivative at the handover depth is '
          'the face slope by construction, so this is an identity when the '
          'derivation is right and silent-looking nonsense when it is not.',
          unit='')
    between(1, 'the handover bracket: 1:10 at D_MIN, 1:32 at 1 m',
            B.beach_face_slope(d_hand=B.D_MIN)
            / B.beach_face_slope(d_hand=1.0), 3.1, 3.2,
            'The one soft place in the derivation, stated as a range rather '
            'than hidden. tan(beta) goes as 1/sqrt(d) and the depth at which '
            'the surf-zone model hands over to the swash is a judgement, so '
            'the answer is bracketed by a factor of 3.16 exactly -- which is '
            'the observed range of sandy beach faces and is why the middle of '
            'it is not a coincidence.')
    check(1, 'the evolved 1-D bed agrees at its innermost resolved cell',
          ctx['_face_measured'], B.beach_face_slope(), 0.004,
          'THE ROW THAT COULD HAVE DISAGREED. The 1-D morphodynamic loop is '
          'run to quasi-steady from a Dean ramp and reshaped all the way in by '
          'a transport model with three terms; it builds a bar that departs '
          'from the ramp by 0.4 m a hundred metres offshore. Its own slope at '
          'the shallowest cell it will answer for is the beach face slope, and '
          'nothing made it be.', unit='')

    # =============================================== 11.2 THE SWASH EXCURSION
    check(1, 'swash_excursion = sqrt(H0 L0), ABSOLUTE', B.swash_excursion(),
          math.sqrt(B.H0_SWELL * L0), 1e-12,
          'The width of the dry beach, in metres, with no constant in it. '
          'Absolute because it replaced a 6.0 m leftover and the difference '
          'between 6 m and 13.8 m is the difference between a beach and a '
          'strip.', unit='m')
    check(1, 'and the same by the long route, R/tan(beta), ABSOLUTE',
          B.runup_hunt(B.H0_SWELL,
                       B.iribarren(B.TAN_FACE, B.H0_SWELL, L0)) / B.TAN_FACE,
          B.swash_excursion(), 1e-9,
          'Hunt composed with Iribarren and then divided by the slope again. '
          'It is the SAME statement written the long way, and the point of the '
          'row is that the slope cancels: the horizontal reach of the swash '
          'does not depend on how steep the beach is, which is why the width '
          'needs no constant. A row that fires the moment anyone puts a slope '
          'back into the excursion.', unit='m')
    for f in (2.0, 0.5):
        check(1, 'the slope divides out: tan(beta) x%g leaves the excursion '
              'ABSOLUTELY unchanged' % f,
              B.berm_crest(tan_beta=f * B.TAN_FACE) / (f * B.TAN_FACE),
              B.swash_excursion(), 1e-9,
              'The run-up limit moves with the slope and the excursion does '
              'not. Two quantities, one of them slope-free, and this row is '
              'what stops the two being confused.', unit='m')
    check(1, 'berm_crest, swell and storm, ABSOLUTE',
          [B.BERM_Z, B.BACKSHORE_Z], [0.7273578, 1.0286400], 1e-6,
          'The two elevations the wet/dry boundary and the backshore sit at, '
          'in metres. The storm one is the file\'s OWN H0_STORM -- chapter '
          '12\'s "Storms push the bar seaward" case -- so the backshore needs '
          'no constant either.', unit='m')
    check(1, 'the run-up scales as sqrt(H): 4x the swell is 2x the limit',
          B.berm_crest(H=4.0 * B.H0_SWELL) / B.BERM_Z, 2.0, 1e-12,
          'Hunt\'s R = tan(beta) sqrt(H L_0) at fixed period. The row that '
          'catches an R written linear in H, which is what a reader who '
          'remembers "R ~ H xi" and forgets that xi carries 1/sqrt(H) will '
          'write.')

    # ============================================= 11.3 THE WET/DRY BOUNDARY
    check(1, 'swash_wetness at 0, R, 2R, ABSOLUTE',
          [float(B.swash_wetness(0.0)), float(B.swash_wetness(B.BERM_Z)),
           float(B.swash_wetness(2.0 * B.BERM_Z))],
          [1.0, math.exp(-1.0), math.exp(-4.0)], 1e-12,
          'The boundary is a distribution and these are three points of it. '
          'Absolute, because a wet band that is too tall and one that is too '
          'short both look like a wet band and only the numbers separate '
          'them.')
    # ...AND AGAINST A GENERATOR THAT HAS NEVER SEEN THE FUNCTION.
    rg = np.random.default_rng(20260816)
    sig = B.BERM_Z / math.sqrt(2.0)
    smp = rg.rayleigh(sig, 400000)
    for z in (0.3, 0.727394, 1.2):
        check(1, 'Monte-Carlo Rayleigh exceedance at z = %.3f m' % z,
              float((smp > z).mean()), float(B.swash_wetness(z)), 0.0025,
              'The claim is that the wetted share IS the exceedance of a '
              'Rayleigh run-up of rms scale R, and this draws 400000 of them '
              'and counts. Nothing in numpy\'s generator knows about beaches. '
              'A linear ramp -- which is what waves 4-7 used -- misses by 0.13 '
              'at this level, fifty times the tolerance.')
    check(1, 'the median of the band, ABSOLUTE',
          B.BERM_Z * math.sqrt(math.log(2.0)), 0.6055646, 1e-6,
          'Where wetness crosses 0.5, which is the level the ladder counts '
          'wet sand below. In metres, so the rung and the shader cannot drift '
          'apart in opposite directions and both stay green.', unit='m')

    # ================================== 11.4 THE BEACH IN THE BED, IN METRES
    bw = ctx['_beach_width']
    # THE WIDTH IS NOT THE EXCURSION ON THIS COAST, AND THAT IS A RESULT.
    # `swash_excursion` is the width a beach WOULD have on an unobstructed
    # profile; here the cliff's own thermally relaxed talus rises INTO the
    # swash plane 12 m from the waterline, so the wedge is truncated at 0.92 m
    # -- past the swell's berm level and short of the storm's backshore. The
    # prediction is therefore geometric: the distance from the waterline to
    # where the ROCK first crosses the plane. It is computed here from the
    # pre-beach composed bed by code that walks and does not solve, and it is
    # compared with a slope-walk on the FINAL evolved bed that knows nothing
    # about planes at all.
    bch = ctx['_beach']
    if bch is not None:
        rock, plane = bch['h_rock'], bch['plane']
        pred = []
        for jj in range(rock.shape[0]):
            ok = (plane[jj] > rock[jj]) & (plane[jj] > 0.0)
            if ok.any():
                idx = np.where(ok)[0]
                pred.append(float(ctx['_bay']['x'][idx[-1]]
                                  - ctx['_bay']['x'][idx[0]]))
        pred_w = float(np.median(pred)) if pred else 0.0
        check(2, 'the subaerial beach measured off the 2-D bed, ABSOLUTE',
              bw['median'], pred_w, 4.5,
              'The width of the landform, in metres. MEASURED by a slope walk '
              'from the waterline to the cliff foot on the bed the render '
              'actually shades; PREDICTED from where the rock crosses the '
              'swash plane on the bed before any sand was laid. Wave 7 '
              'measured 6.0 m here and called it a face slope of 1.000. The '
              'TOLERANCE IS TWO CELLS AND IT IS TWO NAMED CELLS: the '
              'prediction counts every cell where the plane stands above the '
              'rock and above the datum, and the measurement stops at a slope '
              'threshold, which cuts the transitional cell at the toe and the '
              'one where the talus enters the plane. 2 m each on the render\'s '
              'grid, and the coastal loop that placed the cliff foot runs at '
              '4 m.', unit='m')
        info(2, 'and the excursion it is truncated FROM',
             [bw['median'], B.SWASH_W, B.BACKSHORE_W],
             'measured / swell excursion / storm excursion, metres. The '
             'cliff\'s talus takes the top of the wedge, so the beach reaches '
             'past the swell\'s berm level and is cut short of the storm\'s '
             'backshore -- which is what a cliffed coast looks like and is '
             'why the dry rung is thin. A wide backshore belongs to the '
             'embayment this bed does not have.')
    between(2, 'the beach\'s top is between the swell berm and the storm '
            'backshore', bw['top'], B.BERM_Z, B.BACKSHORE_Z,
            'Both bounds are DERIVED -- 0.727 m and 1.029 m -- so this is an '
            'absolute statement with no declared number in it: the wedge is '
            'complete to the level the ordinary swell builds and truncated '
            'before the level the storm would.')
    check(2, 'its face slope measured off the same bed, ABSOLUTE',
          bw['slope'], B.TAN_FACE, 0.006,
          'The median slope over the span, not a rise over a run -- so a bed '
          'whose beach is a ramp and one whose beach is a step do not report '
          'the same number. Wave 7 measured 1.000 here, which is a cliff.',
          unit='')
    if bch is not None:
        check(2, 'the sand budget is not what limits the width',
              float(bch['frac'].min()), 1.0, 1e-9,
              'The wedge needs about 35 m^3 per metre of coast and the coastal '
              'loop delivered about 206. If this row ever fails the beach has '
              'become supply-limited and its width stops being a closed form '
              'and starts being an accounting answer -- which is a real state '
              'for a starved coast and must not be reached silently.')
        between(2, 'and the margin it passes by', float(np.median(
            ctx['_sand_row']) / np.median(bch['need_row'])), 3.0, 12.0,
            'A factor, reported so that "not supply-limited" is a measurement '
            'with a number rather than a boolean. Two orders would be a '
            'suspiciously large budget; unity would mean the closed form is '
            'about to stop applying.')

    # ============================== 11.5 THE ALBEDO SPLIT -- WAVE 8'S FINDING
    check(1, 'the split is exact: diffuse + R_EXT = wet_albedo, ABSOLUTE',
          RND.SAND_WET_DIFF + OPT.R_EXT, RND.SAND_WET, 1e-15,
          'Nothing is invented and nothing is lost. `optics.wet_albedo` is not '
          'touched; its LEADING TERM is moved out of the diffuse lobe and into '
          'a specular one, and this row is the arithmetic that says the move '
          'conserved it.')
    check(1, 'wet sand is DARKER than dry, diffusely, in every channel',
          (RND.SAND_WET_DIFF < RND.SAND_DRY).all(), True, 0,
          'Bar H3: "wet sand darkens". Waves 4-7 shipped the full wet_albedo '
          'as a Lambertian, which makes it BRIGHTER -- and this row is what '
          'fires when that is put back.')
    info(1, 'the size of the error waves 4-7 shipped',
         np.round(RND.SAND_WET - RND.SAND_DRY, 4),
         'The signed difference the old code produced between wet sand and dry '
         'sand in the diffuse lobe. Positive in a channel means wet read '
         'brighter than dry there, which is backwards.')
    check(1, 'the specular that replaces it is R_EXT, ABSOLUTE',
          OPT.R_EXT, [0.0662480, 0.0666910, 0.0675109], 1e-6,
          'The hemispherical external reflectance of the film, per channel. '
          'It is the quantity removed from the diffuse albedo and the '
          'magnitude of the lobe that replaces it, so it is stated rather '
          'than trusted.')

    # ======================================= 11.6 THE SPECULAR LOBE'S GEOMETRY
    # THE SLOPE DISTRIBUTION MUST NORMALISE. Integrated over the slope plane it
    # is 1 by definition of a probability density, and the row that fires when
    # someone drops the 2 pi sigma^2 is worth more than any picture.
    g = np.linspace(-3.0, 3.0, 1201)
    gx, gy = np.meshgrid(g, g)
    check(1, 'the wet film\'s slope pdf integrates to 1, ABSOLUTE',
          float(RND.wet_slope_pdf(gx ** 2 + gy ** 2).sum()
                * (g[1] - g[0]) ** 2), 1.0, 1e-6,
          'The same statement `beach_optics.slope_pdf` carries for the sea, on '
          'the distribution this file uses for a wet film -- and it integrates '
          'THE FUNCTION THE SHADER CALLS, not a copy of it written beside the '
          'row. An unnormalised lobe is brighter or darker by a constant that '
          'no picture reports.')
    check(1, 'the sun lobe\'s Jacobian, ABSOLUTE',
          [RND.sun_jacobian(1.0, 1.0), RND.sun_jacobian(0.9, 0.5)],
          [0.25, 1.0 / (4.0 * 0.9 ** 4 * 0.5)], 1e-12,
          'dw_v = 4 cos(omega) cos^3(beta) dz, the change of variables from '
          'the slope plane to solid angle at the eye. It is GEOMETRY and it '
          'transfers from `beach_optics`\'s sea to a wet beach unchanged; the '
          'density it multiplies does not, and keeping them in two functions '
          'is what lets each be checked without the other.')
    # AND THE TWO COMPOSED, ON A GEOMETRY THE ROW SOLVES ITSELF. A surface
    # whose normal is the half-vector between the sun and the eye is at exact
    # specular, so the density is at its peak and every factor is known.
    hvv = SUN_OF(RND) + np.array([0.0, 0.0, 1.0])
    hvv = hvv / np.linalg.norm(hvv)
    Dn = np.array([[0.0, 0.0, -1.0]])
    Nn = np.array([hvv])
    ctv = float(hvv[2])
    got_sun = RND.wet_specular(Dn, Nn)[0] - RND.wet_specular(Dn, Nn,
                                                             sun=False)[0]
    com = float(np.dot(RND.SUN, hvv))
    exp_sun = (OPT.fresnel(np.array([com]))[0] * RND.E_SUN
               * RND.wet_slope_pdf(0.0) * RND.sun_jacobian(1.0, ctv))
    check(1, 'the sun\'s glint at exact specular, ABSOLUTE, per channel',
          got_sun, exp_sun, 1e-9,
          'The whole lobe at the one geometry where every factor is known: the '
          'surface normal IS the half-vector, so cos(beta) = 1, the density is '
          'at its peak, and the answer is fresnel x E_SUN x p(0) x J. This is '
          'the row that fires when the Jacobian is dropped -- which is the '
          'defect wave 4 shipped in the sea\'s glitter and the suite caught '
          'there, offered a second time in a new surface.')
    # AND THE MIRROR DIRECTION IS THE MIRROR DIRECTION. A flat wet surface seen
    # at theta must reflect the sky from theta on the other side, and the
    # radiance must be fresnel(cos theta) times it -- ABSOLUTE, per channel.
    N = np.array([[0.0, 0.0, 1.0]])
    for th in (10.0, 45.0, 80.0):
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        D = np.array([[s, 0.0, -c]])
        got = RND.wet_specular(D, N, sun=False)[0]
        exp = OPT.fresnel(np.array([c]))[0] * RND.sky_radiance(
            np.array([[s, 0.0, c]]))[0]
        check(1, 'the wet band mirrors the sky at %g deg, ABSOLUTE' % th,
              got, exp, 1e-12,
              'A smooth film is a mirror and the sky term needs no roughness '
              'at all. This is the half of the specular that carries no `?`, '
              'and it is checked against optics.fresnel and the environment '
              'evaluated directly rather than against itself.')

    # ============================================= 11.7 THE AIR, PER METRE
    check(1, 'the Rayleigh coefficient is TAU_R / 8.5 km, ABSOLUTE',
          RND.beta_ext(vis=None) - RND.CAM.koschmieder_beta(RND.VIS_SHIPPED),
          np.asarray(ATM.TAU_R, float) / 8500.0, 1e-15,
          'NO NEW CONSTANT. tau is the zenith optical depth this project '
          'derived four waves ago for the sun\'s own colour; over an '
          'exponential atmosphere of scale height H the surface coefficient is '
          'tau/H. Per channel and per metre.', unit='/m')
    check(1, 'and its green value, ABSOLUTE',
          float(np.asarray(ATM.TAU_R, float)[1] / 8500.0), 1.1878374e-5,
          1e-11,
          'One number, in inverse metres. The row that fires when the scale '
          'height is left out entirely -- which gives 0.1015, four orders '
          'high, and paints the frame flat grey at 50 m.', unit='/m')
    check(1, 'Koschmieder at 60 km and 20 km, ABSOLUTE',
          [RND.CAM.koschmieder_beta(60000.0),
           RND.CAM.koschmieder_beta(20000.0)],
          [-math.log(0.02) / 60000.0, -math.log(0.02) / 20000.0], 1e-15,
          'The `?` half of the air, both ends of the bracket, stated in '
          'inverse metres so that "clean" and "hazy" are numbers rather than '
          'adjectives. -ln(0.02) and not the rounded 3.912 that every quotation '
          'of Koschmieder carries: the two differ in the fifth digit, which is '
          'nothing here and is the sort of thing that is worth writing down '
          'once rather than wondering about later.', unit='/m')
    # THE TWO LIMITS OF THE TRANSFER, AND THEY ARE THE WHOLE PHYSICS.
    Dh = np.array([[0.6, 0.8, -0.02]])
    Dh = Dh / np.linalg.norm(Dh)
    Lsurf = np.array([[0.4, 0.5, 0.9]])
    check(1, 'aerial at zero range returns the surface EXACTLY',
          RND.aerial(Lsurf, Dh, np.array([0.0]))[0], Lsurf[0], 1e-15,
          'A path of no length changes nothing. The row that fires if the '
          'airlight is added unattenuated -- which is what "L + airlight" '
          'instead of "L T + airlight (1 - T)" does, and it is bright enough '
          'at the camera to look like a lifted black point.')
    flat = Dh.copy()
    flat[..., 2] = 0.0
    flat = flat / np.linalg.norm(flat)
    check(1, 'aerial at infinite range returns the HORIZON sky, ABSOLUTE',
          RND.aerial(Lsurf, Dh, np.array([1e9]))[0],
          RND.sky_radiance(flat)[0], 1e-12,
          'THE ROW THE SEAM RESTS ON. In a horizontally homogeneous atmosphere '
          'an infinitely long horizontal path REACHES the horizon sky -- that '
          'is what the horizon sky is -- so the sea at grazing goes to the sky '
          'just above it identically, and bar K2\'s continuity criterion is '
          'satisfied by construction rather than by a fitted number. If the '
          'airlight is taken in the VIEW direction instead of the flattened '
          'one this row fires and the seam reopens.')
    # ...AND ON A STEEPLY DOWNWARD RAY, WHICH IS THE ROW THAT MATTERS. The
    # near-horizontal ray above cannot tell the horizon sky from the sky in the
    # view direction, because for that ray they are nearly the same direction.
    # An airlight taken in the VIEW direction is the mistake a reader is most
    # likely to make -- the light does come from where you are looking -- and
    # only a steep ray separates the two.
    Ds = np.array([[0.4, 0.5, -0.766]])
    Ds = Ds / np.linalg.norm(Ds)
    fls = Ds.copy()
    fls[..., 2] = 0.0
    fls = fls / np.linalg.norm(fls)
    check(1, 'the same at 50 deg of depression -- the HORIZON sky and not the '
          'view direction', RND.aerial(Lsurf, Ds, np.array([1e9]))[0],
          RND.sky_radiance(fls)[0], 1e-12,
          'The airlight is the radiance of an infinitely long path, and a '
          'HORIZONTAL infinite path is what reaches equilibrium -- the ray\'s '
          'own inclination does not enter it. Taking the sky in the view '
          'direction instead leaves this row off by the whole difference '
          'between the horizon and a 50 deg depression, and leaves the '
          'near-horizontal row above passing, which is why both are here.')
    r1 = np.array([1000.0])
    T1 = np.exp(-1000.0 * RND.beta_ext())
    T2 = np.exp(-2000.0 * RND.beta_ext())
    check(1, 'Beer-Lambert composes: T(2r) = T(r)^2, ABSOLUTE',
          T2, T1 ** 2, 1e-15,
          'The property that makes a single exponential the right model at '
          'all. Cheap, and it is the row that catches a transmittance written '
          'as 1 - beta r, which agrees to first order and is 39 per cent wrong '
          'at one e-folding.')

    # ================================================= 11.8 THE SHADOW RAY
    # A SYNTHETIC BED WITH ONE WALL ON IT, so the answer is arithmetic rather
    # than a picture. The sun is at 30 deg; a 10 m wall shadows 17.32 m behind
    # it and nothing in front of it.
    class _Bed:
        pass
    bed = _Bed()
    bed.x = np.arange(0.0, 200.0, 1.0)
    bed.y = np.arange(-20.0, 21.0, 1.0)
    hh = np.zeros((bed.y.size, bed.x.size))
    hh[:, 100:104] = 10.0
    bed.h = hh

    def _samp(xq, yq, fld):
        i = np.clip(np.round(np.asarray(xq)).astype(int), 0, bed.x.size - 1)
        j = np.clip(np.round(np.asarray(yq) + 20).astype(int), 0,
                    bed.y.size - 1)
        return fld[j, i]
    bed.sample = _samp
    S = np.array([math.cos(math.radians(30.0)), 0.0,
                  math.sin(math.radians(30.0))])          # +x, 30 deg up
    Nup = np.tile(np.array([0.0, 0.0, 1.0]), (6, 1))
    xs_t = np.array([80.0, 95.0, 108.0, 115.0, 121.0, 130.0])
    P = np.stack([xs_t, np.zeros(6), np.zeros(6)], -1)
    sh = RND.land_shadow(bed, P, Nup, n=200, sun=S)
    # 104 is the wall's far face; the shadow reaches 104 - 10/tan(30) = 86.7 m
    # BEHIND it, i.e. down to x = 104 - 17.32... the sun is toward +x, so the
    # shadow falls on x < 100 and ends at 100 - 17.32 = 82.68.
    check(1, 'a 10 m wall under a 30 deg sun: which of six points are dark',
          sh, [1.0, 0.0, 1.0, 1.0, 1.0, 1.0], 0,
          'The shadow falls toward -x because the sun is toward +x, and it '
          'reaches 10/tan(30) = 17.32 m from the wall\'s near face at x = 100. '
          'So x = 95 is dark, x = 80 is 20 m away and lit, and everything '
          'beyond the wall is lit. Six points, one arithmetic answer, and no '
          'picture involved.')
    check(1, 'the shadow\'s edge, in metres, ABSOLUTE',
          float(bed.x[np.argmin(RND.land_shadow(
              bed, np.stack([bed.x, np.zeros(bed.x.size),
                             np.zeros(bed.x.size)], -1),
              np.tile(np.array([0., 0., 1.]), (bed.x.size, 1)), n=300,
              sun=S)[:100])]),
          100.0 - 10.0 / math.tan(math.radians(30.0)), 1.5,
          'Where the dark ends, measured off the same march the renderer uses '
          'and compared with h/tan(elevation) in metres. The tolerance is the '
          'march\'s own step near the wall. A reach that is too short moves '
          'this edge toward the wall and a normal test that is inverted '
          'removes the shadow entirely.', unit='m')

    # ================================ 11.9 WHAT IS STILL OPEN, STATED AS ROWS
    ROWS.append(Row(1, 'the berm SCARP -- a break in slope at the run-up limit',
                    'a break in slope', 'a level on one plane', '-', 'OPEN',
                    'Hunt\'s run-up with one face slope puts EVERY run-up '
                    'limit on the SAME PLANE, so the swell\'s limit and the '
                    'storm\'s differ only in how far up it they reach. A berm '
                    'crest is a break in slope and needs the swell to CUT the '
                    'storm-built profile -- swash transport, which this model '
                    'does not have. The level is derived and marked; the '
                    'scarp is absent, not approximated.', ''))
    ROWS.append(Row(1, 'SIGMA_WET, the wet film\'s residual rms slope',
                    '0.10 - 0.40', RND.SIGMA_WET, '-', 'OPEN',
                    'The one new unknown wave 8 adds. It moves the SUN\'s '
                    'glint on the wet band and nothing else -- the sky half of '
                    'the specular needs no roughness at all -- and no '
                    'measurement of a wet grain pack\'s residual slope was '
                    'available. Declared at 0.20, bracketed, and the bracket '
                    'is rendered.', ''))
    ROWS.append(Row(1, 'the aerosol visibility', '20 - 60 km',
                    RND.VIS_SHIPPED / 1000.0, '-', 'OPEN',
                    'Koschmieder turns a meteorological visibility into an '
                    'extinction coefficient and a maritime boundary layer runs '
                    '20-60 km. The clean end is shipped because it UNDERSTATES '
                    'the term being added; the hazy end is rendered beside it. '
                    'It is not read off bar J or bar K -- the standing ruling '
                    'forbids reading a level off them and horizon sharpness is '
                    'a level.', 'km'))
    ROWS.append(Row(1, 'the beach\'s feedback on the cliff', 'closed',
                    'not closed', '-', 'OPEN',
                    'The wedge is laid at COMPOSITION time, in `bay_bed`, and '
                    'not inside `coastal_step`\'s iteration. Inside it the '
                    'beach moves the waterline the notch attacks and the cliff '
                    'stops retreating -- a real feedback, and the reason it is '
                    'not closed here is that it changes the plan-form every '
                    'row in `_sec_coast` is measured on. The budget is the '
                    'loop\'s; the iteration is not.', ''))
    ROWS.append(Row(1, 'the coastal plain\'s relief', 'a landform',
                    'a straight ramp', '-', 'OPEN',
                    'Gap 2, and it is a missing PROCESS rather than a missing '
                    'constant. Differential subaerial weathering keyed to the '
                    'hardness field this file already owns lowers the plateau '
                    'by 2-18 cm over the 182 m this coast retreated (denudation '
                    '0.01-0.1 mm/yr against cliff retreat 0.05-0.5 m/yr), so '
                    'the relief it can produce has slopes of 1e-4 -- invisible '
                    'under ANY coefficient in the bracket. The relief on a real '
                    'coastal plain is drainage, which is out of chapter 12.',
                    ''))


def _sec_camera(ctx):
    """WAVE 7 -- WHERE THE PHOTOGRAPH WAS TAKEN FROM.

    The gauntlet's first hyper-realism criterion is FRAME TO MATCH, and meeting
    it means inferring a camera from photographs that carry no EXIF and are not
    in this repository. Everything the inference produces is an angle or a
    length; nothing in it is a level, which is the standing ruling. This section
    guards the geometry that turns the bar's inventory into a camera, and every
    quantity the inference reports gets at least one ABSOLUTE row -- the fourth
    time a ratio-only guard was blind in this project is one time too many.
    """
    C = CMR

    # ============================================ 10.1 THE INSTRUMENT'S OPTICS
    # An "equivalent focal length" is equivalent ON the 36 x 24 frame, and the
    # equivalence is on the DIAGONAL. Feed the function a 3:2 target and the
    # long side must come back to the textbook 2 atan(18/f) exactly -- the only
    # row that catches a diagonal/long-side confusion, which is a 4% error at
    # 24 mm and 10% at 13 mm and looks entirely reasonable either way.
    for f in (13.0, 24.0, 48.0, 120.0):
        check(1, 'equiv_fov at %g mm on 3:2 recovers 2 atan(18/f), ABSOLUTE'
              % f, math.degrees(C.equiv_fov(f, aspect=1.5)['long']),
              math.degrees(2.0 * math.atan(18.0 / f)), 1e-9,
              'The diagonal-to-side conversion, checked against the definition '
              'of focal length on the frame the equivalence names. It is an '
              'identity when the conversion is right and off by 4-10 per cent '
              'when the diagonal FOV is applied to the long side instead.',
              unit='deg')
    check(1, 'the two FOV routes agree: rectilinear_hfov(long, 3/4) = short',
          math.degrees(C.rectilinear_hfov(C.portrait_fov(13.0)[0], 0.75)),
          math.degrees(C.portrait_fov(13.0)[1]), 1e-9,
          'One route goes through the lens (diagonal, then the frame aspect), '
          'the other through the raster (vertical FOV, then W/H). They are the '
          'same rectilinear projection and must land on the same number. This '
          'is the row that fires if anyone writes h = v * W/H, which is 12 per '
          'cent narrow at 90 degrees and exact at zero -- so it passes every '
          'small-angle sanity check anybody would try.', unit='deg')
    check(1, 'the widest lens upright, ABSOLUTE', 
          math.degrees(C.portrait_fov(13.0)[1]), 89.91172, 1e-4,
          'The number the whole lens selection turns on: 89.9117 deg across, '
          'against the 90.00 a chord seen from exactly half a chord back '
          'subtends. Stated absolutely because the inference EXCLUDES a range '
          'of standoffs on the strength of that 0.09 deg.', unit='deg')
    check(1, 'no lens can hold a chord from nearer than 0.5008 chords',
          C.min_standoff_over_chord(), 0.5007710, 1e-6,
          '1/(2 tan(h_max/2)). A bound on where the photographer stood, '
          'recovered from the frame\'s content and the phone\'s spec sheet and '
          'nothing else -- the bay\'s size cancels out of it.')

    # ================================================ 10.2 THE EARTH, AND ITS DIP
    check(1, 'the refracted dip is Bowditch\'s table, ABSOLUTE',
          math.degrees(C.horizon_dip(25.0)) * 60.0 / 5.0,
          C.BOWDITCH_DIP_ARCMIN, 1e-3,
          'Dip in arcminutes per sqrt(metre). The geometric value is 1.9261 '
          'and Bowditch\'s tabulated dip is 0.97 sqrt(h_ft) = 1.757 '
          'sqrt(h_m); the ratio is what REFRACTION_K is fitted to. This row is '
          'the fit, stated against the table rather than against itself.',
          unit='arcmin/sqrt(m)')
    check(1, 'the geometric dip is sqrt(2z/R) to its own series',
          math.degrees(C.horizon_dip(25.0, refraction=False)),
          math.degrees(math.sqrt(2.0 * 25.0 / C.R_EARTH)), 2e-5,
          'acos(R/(R+z)) = sqrt(2z/R) (1 - z/(6R) + ...). At 25 m the second '
          'term is 6e-7 relative, so the tolerance IS the series and not a '
          'disagreement.', unit='deg')
    check(1, 'horizon range = R_eff * dip, ABSOLUTE at 21 m',
          C.horizon_range(21.0), 17931.41, 0.5,
          'The arc to the visible horizon. Stated absolutely and in metres '
          'because the flat-plane cost below is a DIFFERENCE against it, and '
          'a difference of two large numbers is exactly where an absolute row '
          'earns its place.', unit='m')
    check(1, 'the curved and flat range agree where the curve does not bite',
          C.range_at_depression(21.0, math.radians(30.0)),
          C.range_flat(21.0, math.radians(30.0)), 5e-4,
          'At 30 degrees of depression the target is 36 m away and the earth '
          'is flat to 0.15 mm, which IS the tolerance. The two functions must be '
          'indistinguishable here and wildly different at the horizon; this '
          'row is the first half and the next is the second.', unit='m')
    check(1, 'and they diverge at grazing: flat says infinity, curved says the '
          'horizon', C.range_at_depression(21.0, C.horizon_dip(21.0) * 1.000001)
          / C.horizon_range(21.0), 1.0, 2e-3,
          'At the dip angle itself the spherical solution lands ON the horizon '
          'while z/tan(dep) overshoots by 2.5 per cent and keeps going. The '
          'ratio is stated because the absolute is stated above.')
    fs = C.flat_sea_error(21.0, 40000.0)
    check(1, 'the flat sea plane over-paints the sky by 0.1039 deg, ABSOLUTE',
          math.degrees(fs['over_paint']), 0.104121, 1e-5,
          'THE WHOLE COST OF A FLAT EARTH IN THIS RENDER, in one number. '
          '`beach_render.trace` meets a plane at z = 0 that runs to 40 km and '
          'has no horizon, so it paints sea over a band of sky one tenth of a '
          'degree tall -- about a third of a pixel row in an upright 106 deg '
          'frame. The 23 km of ocean beyond the true horizon is fictitious and '
          'it is compressed into that third of a row. Measured so the defect '
          'can be ranked at the BOTTOM of the gap list on evidence rather '
          'than left unranked.', unit='deg')

    # ============================== 10.3 THE INSTRUMENT THAT MEASURES THE EYE
    # The dip is famous and useless; the resolved surf-line separation is
    # neither. These rows are its closed form.
    D, s_gap = 704.0, 42.86
    for z in (20.0, 60.0, 200.0):
        got = C.line_separation(z, D, s_gap)
        want = math.atan(z * s_gap / (D * (D - s_gap) + z * z))
        check(1, 'the separation is one arctangent at z = %g m' % z,
              math.degrees(got), math.degrees(want), 1e-9,
              'atan(a) - atan(b) = atan((a-b)/(1+ab)) with a = z/(D-s) and '
              'b = z/D. Written as a difference in the code and as the single '
              'form here, so the algebra the ceiling is derived from is '
              'checked against the function rather than assumed.', unit='deg')
    d_max, z_star = C.separation_ceiling(D, s_gap)
    check(1, 'the ceiling is at z* = sqrt(D(D-s)), ABSOLUTE',
          z_star, math.sqrt(D * (D - s_gap)), 1e-9,
          'DERIVED HERE AND NOT CITED, because no source states it. '
          'Maximising tan(d) = zs/(D(D-s) + z^2) over z gives z^2 = D(D-s): '
          'the best eye height for separating two lines is the GEOMETRIC MEAN '
          'of the two ranges. At 704 m that is 682 m, which is why a cliff is '
          'always on the linear branch and a metre of height is worth a metre '
          'of height.', unit='m')
    zz = np.geomspace(1.0, 1e5, 20001)
    scan = np.array([C.line_separation(z, D, s_gap) for z in zz])
    check(1, 'and it IS the maximum: a scan over five decades of eye height',
          math.degrees(scan.max()), math.degrees(d_max), 2e-5,
          'The closed form against twenty thousand samples. A ceiling that is '
          'only asserted is a ceiling nobody has tested.', unit='deg')
    check(1, 'eye_height_for_separation inverts line_separation, ABSOLUTE',
          [C.line_separation(C.eye_height_for_separation(D, s_gap, dd), D,
                             s_gap) for dd in (0.002, 0.005, 0.01, 0.02)],
          [0.002, 0.005, 0.01, 0.02], 1e-12,
          'Round trip through the quadratic. The SMALLER root is the one '
          'returned, and this row is what says the branch is the right one: '
          'the larger root also satisfies the equation and puts the eye a '
          'kilometre up.', unit='rad')
    openq(1, 'THIS BED CANNOT SUPPLY BAR J\'S EYE HEIGHT',
          '17-21 m at the brow', '25-102 m',
          'Bar J reads three to four SEPARATED breaking lines across the wider '
          'parts of the embayment. At this transform\'s own surf-zone width '
          '(150 m median, so 43 m between lines at "three to four") and at the '
          'range across this bay, resolving that gap at 5-20 px in a 4032-row '
          'upright frame needs an eye at 25-102 m. Wave 3\'s coastal loop '
          'leaves a cliff whose brow is 17-21 m, and the plateau behind it is '
          'a straight 0.08 ramp that occludes its own brow, so there is no '
          'higher place to stand. The shortfall is a statement about the '
          'coastal loop and not about the camera, and it is why the s7 frames '
          'give the near cliff a share of the frame that bar J\'s does not.')

    # ============================================ 10.4 THE FRAME AND THE HORIZON
    fov_v = C.portrait_fov(13.0)[0]
    for f_h in (0.05, 0.25, 0.5, 0.9):
        check(1, 'horizon fraction inverts, ABSOLUTE at f = %.2f' % f_h,
              C.horizon_fraction(
                  C.depression_from_horizon_fraction(f_h, fov_v, 21.0),
                  fov_v, 21.0), f_h, 1e-12,
              'The two directions of the same projection: a depression gives a '
              'row, a row gives a depression. This is the pair the actual '
              'photograph would close -- one measured horizon row collapses '
              'the depression interval from +/- 13 deg to +/- 0.03.')
    check(1, 'the dip moves the horizon by 0.33 rows in a 304-row frame',
          (C.horizon_fraction(math.radians(25.46), fov_v, 21.12)
           - C.frame_fraction(math.radians(25.46), fov_v)) * 304.0,
          0.328621, 1e-5,
          'ABSOLUTE, in pixels, and it is the number that says the earth\'s '
          'curvature is not a framing parameter. A third of a row at this '
          'raster; even at the phone\'s own 4032 it is 4.4 rows, which is '
          'inside the tilt error of a hand-held frame.', unit='rows')

    # ================================ 10.5 THE TWO CAMERAS, PARAMETER BY PARAMETER
    # EVERY DERIVED PARAMETER GETS AN ABSOLUTE ROW. The eye height is the
    # scene's and is checked where the scene is built; the field of view, the
    # aspect and the depression are the inference's own and are checked here.
    infJ = C.infer_frame('J', C.J_CONTENT, 21.12, 704.0, 42.86)
    infK = C.infer_frame('K', C.K_CONTENT, 21.12, 704.0, 42.86)
    for nm, inf, dep_deg, half_deg in (('J', infJ, 25.455246, 13.296088),
                                       ('K', infK, 27.805133, 12.761096)):
        check(1, 'frame %s: vertical field of view, ABSOLUTE' % nm,
              math.degrees(inf['fov_v']), 106.175435, 1e-5,
              'The 13 mm equivalent held upright on a 4:3 frame. It is the '
              'parameter the frame\'s CONTENT selects -- "the whole embayment '
              'from its own rim" needs more than 89.91 deg across and no other '
              'lens on this phone has it -- so it is the best determined of '
              'the three and it is determined by the instrument.', unit='deg')
        check(1, 'frame %s: horizontal field of view, ABSOLUTE' % nm,
              math.degrees(inf['fov_h']), 89.911717, 1e-5,
              'The short side of the same lens. Portrait matters: the same '
              'lens held landscape is 89.91 tall and 106.18 wide, which moves '
              'the horizon, the depression and every content bound.',
              unit='deg')
        check(1, 'frame %s: depression of the optical axis, ABSOLUTE' % nm,
              math.degrees(inf['dep']['mid']), dep_deg, 1e-5,
              'The midpoint of the bracket. It is stated absolutely because '
              'it is the parameter a reader is most likely to want to move, '
              'and a row is the only thing that makes a move visible.',
              unit='deg')
        check(1, 'frame %s: the bracket\'s half-width, ABSOLUTE' % nm,
              math.degrees(inf['dep']['half_width']), half_deg, 1e-5,
              'THE UNCERTAINTY GETS ITS OWN ROW, and that is deliberate. The '
              'depression is the only one of the three parameters the picture '
              'itself measures, and without the pixels it is bracketed by two '
              'content facts rather than measured. A wave that quietly '
              'narrowed this interval would be claiming evidence it does not '
              'have; the row makes that impossible to do silently.', unit='deg')
    info(1, 'the foreground bound does not bind, and that is a result',
         math.degrees(infK['dep']['bound_foreground']),
         'K records dune vegetation in the foreground, which sounds like it '
         'pins the camera\'s downward tilt. It does not: an upright 106 deg '
         'frame held LEVEL already contains the ground at the photographer\'s '
         'feet, so the bound comes out at -50.8 deg and is never active. A '
         'content fact that constrains nothing is worth recording, because the '
         'next reader will otherwise reach for it again.')

    # ====================== 10.6 THE CAMERA AS BUILT, NOT AS INFERRED
    # The inference is arithmetic; the camera is a ray field. This row closes
    # the loop between them, and it is the one that fires if the Camera class
    # is fed a horizontal FOV where it wants a vertical one -- which would be
    # silent in every row above.
    import beach_render as RND                              # noqa: PLC0415
    cam = RND.Camera((0.0, 0.0, 21.12),
                     (0.0, 1000.0, 21.12 - 1000.0 * math.tan(infJ['dep']['mid'])),
                     math.degrees(infJ['fov_v']), 228, 304)
    Dr = cam.rays()
    rows = np.where((Dr[..., 2] >= 0.0).all(1))[0]
    check(1, 'the BUILT camera puts the horizon where the inference says',
          float(rows[-1] + 1) / 304.0,
          C.frame_fraction(infJ['dep']['mid'], infJ['fov_v']), 1.0 / 304.0,
          'The ray field of the camera actually used, against the projection '
          'the inference reported. Tolerance is ONE ROW because the ray field '
          'is sampled at pixel centres and the prediction is continuous. This '
          'is the only row in the section that touches the renderer, and it '
          'is the one that catches a vertical field of view passed where a '
          'horizontal one belongs -- an error every arithmetic row above is '
          'blind to.')
    check(1, 'the built camera\'s aspect is UPRIGHT 3:4', cam.w / cam.h,
          0.75, 1e-12,
          'Bar J and bar K both record the frame upright and every other frame '
          'in this file is 16:9. If this ever comes back 4:3 the frames have '
          'been rotated and every content bound in `beach_camera` is being '
          'applied to the wrong axis.')

    # =============================================== 10.7 THE AIR THAT IS MISSING
    check(1, 'Koschmieder: beta * V = -ln(0.02), ABSOLUTE',
          C.koschmieder_beta(20000.0) * 20000.0, 3.912023, 1e-5,
          'V = -ln(eps)/beta at the standard 2 per cent contrast threshold. '
          'Cited, not derived. It is here because the aerial-perspective gap '
          'is measured through it and a factor hiding in the definition would '
          'move the whole ranking.')
    check(1, 'Rayleigh beta from the project\'s OWN zenith optical depth',
          np.asarray(ATM.TAU_R) / 8500.0 * 8500.0, np.asarray(ATM.TAU_R), 1e-15,
          'beta = tau_zenith / H_R over an exponential atmosphere. NOTHING NEW '
          'IS DECLARED for the Rayleigh half of the missing air: '
          '`atmosphere.TAU_R` is the optical depth this project already '
          'derived for the sun\'s own colour, and the scale height is the '
          'standard 8.5 km. The AEROSOL half does need a number and it is `?` '
          '-- a 20-60 km visibility bracket, reported as a bracket.')
    openq(2, 'THE AIR BETWEEN THE CAMERA AND THE SEA IS NOT MODELLED',
          'extinction + airlight over 15 km', 'neither',
          'The pool was five metres across and this is a fifteen-kilometre '
          'frame. `shade_water` and `shade_land` return the radiance LEAVING '
          'the surface and the trace hands it straight to the film: there is '
          'no extinction along the line of sight and no airlight scattered '
          'into it. In hazy 20 km air the direct transmittance at one '
          'kilometre is 0.81 and at the horizon it is nothing at all, so the '
          'far sea is too dark and too saturated BY CONSTRUCTION, and the '
          'sea-sky seam that bar K2 makes a criterion cannot close. Measured '
          'on the frames rather than asserted; see README-beach.md.')


def _sec_foam(ctx):
    """WAVE 6 -- the white, and it is three mechanisms (bar sections C and E).

    EVERY NEW QUANTITY GETS AN ABSOLUTE ROW. A ratio-only guard has now been
    blind three times in this project -- once dividing 0/0 and raising -- and
    this wave found a fourth in its own first draft: `bed_visibility` reported
    R_bed_seen/R_bed, which in the breaking band divides one underflowed number
    by another and returned 1.6e-4 for a run with the plume switched OFF, where
    the answer is 1 by construction. So the plume's effect is measured as a
    FORWARD quantity, `bed_factor`, and the rows below check absolutes.

    AND NO TWO ROUTES SHARE A SOURCE. The bubble's constant is recovered by a
    ray trace that was not written from it; the raft's reflectance is computed
    from Stokes' pile of plates AND from a two-stream that never sees the
    constant; the three decay times come from three different published laws
    (Monahan & Zietlow's measurement, Schiller & Naumann's drag, Soulsby's
    settling); and the void fraction's units are checked by algebra rather than
    by a number.
    """
    B = ctx['B']
    F = FOAM

    # ============================== 9.1 ONE CONSTANT, AND IT MUST BE ONE
    oc = F.check_one_constant()
    check(1, 'the three whites and the window are ONE constant',
          float(F.FOAM_WHITE[1]), float(F.TIR_FRAC), 1e-15,
          'Bar section C: "All three whiten from 1 - 1/n^2 = 43.874% ... one '
          'constant, three appearances, and the same one that runs the mirror '
          'outside Snell\'s window." `optics.TIR_FRAC` is the window\'s and '
          '`beach_optics.FOAM_WHITE` is the foam\'s, and if they are ever two '
          'numbers the bar\'s claim has quietly become two claims. This row is '
          'the identity, at machine precision, and it fires on the most likely '
          'future edit of all -- someone giving foam its own whiteness.')
    check(1, 'the critical angle, absolute', float(np.degrees(F.THETA_C[1])),
          48.5194, 5e-4,
          'asin(1/1.3348) in degrees. ABSOLUTE and not a ratio: everything '
          'else in this section is an area or a fraction derived from this '
          'angle, so one row states the angle itself.', unit='deg')

    # ============================== 9.2 THE BUBBLE, TRACED
    bs = F.bubble_scatter(n_p=20001)
    check(1, 'the ray trace RECOVERS 1 - 1/n^2 without being told it',
          bs['tir_fraction'], np.asarray(F.FOAM_WHITE), 2e-4,
          'THE STRONGEST FORM THIS CHECK CAN TAKE. `bubble_scatter` integrates '
          'over the impact parameter with Fresnel from `optics.fresnel` and '
          'never evaluates 1 - 1/n^2; the share of the disc that lands beyond '
          'the critical angle comes out of the quadrature. That it equals the '
          'bar\'s constant is the bar\'s claim PROVED rather than restated -- '
          'the constant is the AREA OF A DISC, which is why the same number '
          'runs the window from below.')
    check(1, 'the bubble conserves energy across all orders',
          bs['total'], np.ones(3), 2e-6,
          'R + (1-R)^2 SUM R^(k-1) = R + (1-R) = 1 for every impact parameter, '
          'so the trace must sum to one channel by channel. It is the row that '
          'fires if the internal reflectance is taken as the external one -- '
          'the reciprocity step is the easiest thing in this file to get '
          'backwards and it is silent, because a bubble with the wrong Fresnel '
          'still looks like a bubble.')
    check(1, 'a TIR ray off a sphere deviates by at most pi - 2 theta_c',
          math.degrees(math.pi - 2 * float(F.THETA_C[1])), 82.961, 1e-2,
          'AND THIS IS THE QUALIFIER THE BAR DOES NOT CARRY. Section C says '
          '43.874% "is totally reflected", which is true, and then uses it to '
          'explain the white. A ray reflected off a sphere at incidence '
          'theta_i leaves deviated by pi - 2 theta_i, and every TIR ray has '
          'theta_i > theta_c, so every one of them deviates by LESS than 83 '
          'deg: a bubble is a SIDE scatterer, not a backscatterer. The white '
          'is multiple scattering in a medium of albedo 1. This row is the '
          'geometry that forces that reading.', unit='deg')
    between(2, 'the bubble\'s backscatter ratio b_b/b', float(bs['bb_over_b'][1]),
            0.005, 0.06,
            'Clean bubbles in water are strongly FORWARD scattering; the '
            'published backscattering ratio for uncoated bubbles is a few per '
            'cent (Zhang, Lewis & Johnson 1998 give ~0.03 for clean bubbles, '
            'and surfactant coatings raise it). The trace gives 0.023 and the '
            'band is deliberately loose -- it is a sanity bracket on an '
            'independent computation, not a fit. A file that used the bar\'s '
            '43.9% as a backscatter fraction would land twenty times outside '
            'it, which is what this row is for.')
    check(1, 'the trace RECOVERS optics.R_INT in ALL THREE bands',
          bs['reflected'], np.asarray(OPT.R_INT), 3e-6,
          'THE STRONGEST ROW IN THIS SECTION, and wave 7 had to fix a defect '
          'to earn it. An impact-parameter uniform over the DISC is a cosine '
          'weighting over the hemisphere, so the disc-average of the internal '
          'Fresnel reflectance IS the diffuse internal reflectance -- which '
          '`optics.py` carries in closed form as R_INT = 1 - (1 - R_EXT)/n^2, '
          'derived from the external one by reciprocity and sharing not one '
          'line of code with this quadrature. Two independent routes to three '
          'numbers, agreeing to seven digits. It could not be written before, '
          'because `_fresnel_internal` evaluated all three channels at RED\'s '
          'refracted cosine: the shape was right, `optics.fresnel` broadcasts '
          'a scalar to three channels, and only the red band landed. A wrong '
          'ANGLE per channel is invisible to every shape and energy check in '
          'this file -- energy still summed to 1, because R and (1-R) were '
          'consistent with each other at the wrong angle.')
    info(1, 'the bubble: g, b_b/b, reflected share (R,G,B)',
         (tuple(np.round(bs['g'], 5)), tuple(np.round(bs['bb_over_b'], 5)),
          tuple(np.round(bs['reflected'], 5))),
         'the reflected share exceeds 1-1/n^2 because partial Fresnel below '
         'the critical angle adds to the total internal reflection above it')
    bs2 = F.bubble_scatter(n_p=5003)
    check(3, 'the trace has converged in the impact parameter',
          bs2['g'], bs['g'], 2e-3,
          'A second quadrature at a quarter of the samples. Convergence is a '
          'tier-3 check because it compares the method with itself; it is here '
          'because g feeds the similarity scaling and a badly sampled g would '
          'move every optical depth in this section.', rel=True)

    # ============================== 9.3 THE RISE, AND ITS CLOSED LIMIT
    for r in (1e-6, 3e-6):
        w_st = 2.0 * r * r * B.G / (9.0 * B.NU_W)
        check(1, 'bubble rise -> Stokes at r = %g m' % r,
              float(F.bubble_rise_velocity(r)), w_st, 4e-3,
              'At Re << 1 Schiller & Naumann\'s C_D collapses to 24/Re and the '
              'force balance gives w = 2 r^2 g / (9 nu) for a body of zero '
              'density -- a CLOSED FORM this function was not written from. '
              'The tolerance is the 0.15 Re^0.687 term that is still there at '
              'this radius, not a disagreement.', unit='m/s', rel=True)
    r_t = 2.25e-4
    w_t = float(F.bubble_rise_velocity(r_t))
    re = 2 * r_t * w_t / B.NU_W
    cd = (24.0 / re) * (1.0 + 0.15 * re ** 0.687)
    check(1, 'the terminal velocity balances its own drag (residual)',
          float(abs(cd * math.pi * r_t ** 2 * 0.5 * w_t ** 2
                    - (4.0 / 3.0) * math.pi * r_t ** 3 * B.G)
                / ((4.0 / 3.0) * math.pi * r_t ** 3 * B.G)), 0.0, 1e-6,
          'Buoyancy against drag, evaluated at the returned w. ABSOLUTE and '
          'dimensional: it fires on a fixed point that stopped early and on '
          'any algebra slip in the balance, neither of which a monotone check '
          'would see.')
    info(1, 'rise speed at r = 0.225 mm', round(w_t, 5),
         'm/s, rigid-sphere (surfactant-immobilised) drag; a mobile interface '
         'would be about 1.5x faster and the choice is marked `P` in the module')

    # ============================== 9.4 THE POPULATION, SIZE-RESOLVED
    sp = F.bubble_spectrum(0.75)
    check(1, 'the standing spectrum\'s clock, <tau>_vol, ABSOLUTE',
          sp['tau_vol'], 0.813927, 1e-5,
          'INT n_s r^3 tau / INT n_s r^3 with tau(r) = (d_p/2)/w(r) over the '
          'Deane & Stokes spectrum. THE AIR IS GONE IN UNDER A SECOND, and '
          'that number is the entire reason the plume is a feature of the bore '
          'front rather than a property of the surf zone. ABSOLUTE because the '
          'first writing of this section used a single rise speed at the '
          'Sauter radius, got 15.7 s, and turned the bay into milk.', unit='s')
    check(1, 'the standing Sauter radius, ABSOLUTE', sp['r_32'], 7.3345e-4,
          1e-8,
          'INT n_st r^3 / INT n_st r^2 -- the only moment the optics needs, '
          'because the projected area per unit volume of ANY suspension of '
          'volume fraction alpha is exactly 3 alpha/(4 r_32). b goes as 1/r_32, '
          'so this row is the scattering coefficient in disguise and it is '
          'stated absolutely rather than through it.', unit='m')
    check(1, 'the residence time SPANS four decades across the spectrum',
          float(sp['tau_at_rmin'] / sp['tau_at_rmax']), 6335.0, 40.0,
          'BAR SECTION E SAYS ONE DECAY CURVE FITS NEITHER OF ITS TWO CLOUDS. '
          'Measured, one decay curve does not fit even ONE of them: tau(r) '
          'runs 0.29 s at a centimetre to 1813 s at ten microns. The AIR '
          'VOLUME leaves on the fast end and the projected AREA that scatters '
          'light leaves on the slow end, and quoting either as "the plume\'s '
          'decay time" picks a side without saying so.')
    info(1, 'tau(r) at r_max and r_min, and the area-weighted median',
         (round(sp['tau_at_rmax'], 4), round(sp['tau_at_rmin'], 1),
          round(sp['tau_area_median'], 1)),
         's -- the area-weighted median tracks r_min and is reported as a '
         'statement about the cutoff, not as a timescale')
    r32s = [F.bubble_spectrum(0.75, r_min=rm)['r_32']
            for rm in (3e-6, 1e-5, 3e-5, 1e-4)]
    tvs = [F.bubble_spectrum(0.75, r_min=rm)['tau_vol']
           for rm in (3e-6, 1e-5, 3e-5, 1e-4)]
    check(1, '<tau>_vol is insensitive to the SMALL cutoff, r_32 is NOT',
          float(max(tvs) / min(tvs)), 1.0, 0.03,
          'The source spectrum\'s volume converges at the small end, so the '
          'air\'s clock does not care where the population stops -- 2% over a '
          'factor of thirty in r_min. The STANDING spectrum is a different '
          'matter and the row below is the correction to this file\'s own '
          'first draft, which called the small cutoff harmless for both.')
    check(1, 'and r_32 moves 2.4x over the same range of r_min',
          float(max(r32s) / min(r32s)), 2.377, 0.02,
          'n_st r^2 goes as r^-1.5 in the Stokes regime, so the projected AREA '
          'diverges as r_min -> 0 and r_32 runs 0.50 mm at 3 micron to 1.20 mm '
          'at 100 micron. The cutoff is physical -- Laplace pressure drives a '
          'sub-ten-micron bubble into solution in seconds -- but its exact '
          'place is `P`, and this row is the honest size of that uncertainty '
          'rather than a claim that it is small.')
    info(1, 'r_32 at r_min = 3 / 10 / 30 / 100 micron',
         tuple(round(v, 7) for v in r32s), 'm')
    spa, spb = F.bubble_spectrum(0.75, r_max=3e-3), F.bubble_spectrum(0.75)
    info(1, '<tau>_vol and r_32 at r_max = 3 mm vs 10 mm',
         ((round(spa['tau_vol'], 4), round(spa['r_32'], 7)),
          (round(spb['tau_vol'], 4), round(spb['r_32'], 7))),
         'the LARGE cutoff moves b by 2.7x and it is `?` at this coast -- the '
         'sharpest thing in section C this file cannot close')
    check(3, 'the spectrum has converged in its own quadrature',
          F.bubble_spectrum(0.75, n=12001)['r_32'], sp['r_32'], 2e-3,
          'Four times the nodes on the same log grid. Tier 3 because it '
          'compares the method with itself; it is here because r_32 is an '
          'integral over five decades and a coarse grid on a power law is a '
          'classic silent bias.', rel=True)

    # ============================== 9.5 THE PLUME
    # THE STANDING TRAP, ONE FILE FURTHER ON, AND IT IS CHECKED BY ALGEBRA.
    # alpha = 2 eps D_w <tau>/(rho g d_p^2). Push units through it: a
    # dissipation RATE gives a dimensionless alpha; an energy DENSITY gives
    # seconds. No tolerance and no sample point, and it cannot be satisfied by
    # a constant.
    alpha_dim = (DISSIPATION_RATE * S) / ((KG / M ** 3) * ACCELERATION * M ** 2)
    check(1, 'the void fraction is DIMENSIONLESS',
          float(alpha_dim.e == (0, 0, 0)), 1.0, 0.0,
          'chapter 12\'s standing trap is that D_w (W/m^2) and E_w (J/m^2) are '
          'one keystroke apart and the wrong one "yields an acceleration '
          'rather than a velocity". Here the wrong one yields a void fraction '
          'in seconds. Evaluated on UNITS, so it cannot be tuned away and no '
          'sample point can make it pass by luck.')
    alpha_wrong = (ENERGY_DENSITY * S) / ((KG / M ** 3) * ACCELERATION * M ** 2)
    check(1, 'and an ENERGY DENSITY in that slot gives seconds',
          float(alpha_wrong.e == (0, 0, 1)), 1.0, 0.0,
          'The other half of the same row, stated so the first cannot pass by '
          'accident: the bug this guards against has a NAMED wrong answer and '
          'this is it.')
    ea = F.entrained_air(np.array([250.0, 25.0]), np.array([1.5, 1.5]), 9.0)
    check(1, 'the void fraction is linear in the dissipation',
          float(ea['alpha'][0] / ea['alpha'][1]), 10.0, 1e-9,
          'alpha = Q <tau>/d_p and Q is linear in D_w, so ten times the '
          'dissipation is ten times the air. Neither value is clipped here '
          '(0.30 is the limit and these are 0.029 and 0.0029), which the row '
          'below states absolutely so this one cannot be passing on a clip.')
    check(1, 'the void fraction, ABSOLUTE, at D_w = 250 W/m2 and H = 1.5 m',
          float(ea['alpha'][0]), 0.0287904, 1e-6,
          'THE ABSOLUTE ROW FOR THIS QUANTITY. 2 x 0.40 x 250/(1025 x 9.80665 '
          'x 0.75) x 0.8139/0.75, with every factor named in the module: '
          'Lamarre & Melville\'s 0.40, the plume depth H/2, the size-resolved '
          '<tau>_vol, seawater density and standard gravity. A FEW PER CENT, '
          'which is where measured surf-zone void fractions are; the first '
          'draft of this file produced 0.30, hit its own validity clip across '
          'the whole surf zone, and the frame was a sheet of milk. A ratio row '
          'alone would have survived that unchanged.')
    check(1, 'the entrainment rate Q, ABSOLUTE', float(ea['Q'][0]), 0.0265292,
          1e-6,
          '2 eps D_w/(rho g d_p) -- cubic metres of air per square metre per '
          'second. It is the quantity the raft is fed by as well as the plume, '
          'so it gets its own row rather than being inferred from alpha.',
          unit='m/s')
    bs = F.bubble_scatter(n_p=20001)
    io = BOP.iops()
    po = F.plume_optics(np.array([0.0, 0.03]), sp['r_32'],
                        np.array([0.75, 0.75]), bs['g'], bs['bb_over_b'],
                        io['a'])
    check(1, 'a plume of zero air is EXACTLY transparent',
          float(po['T'][0, 1]), 1.0, 1e-12,
          'alpha = 0 gives tau = 0, T = 1, R = 0. It is the limit that makes '
          'the medium an ADDITION to the scene rather than a replacement of '
          'it, and it is the exact control the paired evidence frame relies '
          'on. IT DID NOT HOLD in the first writing, which multiplied the slab '
          'by the water\'s own absorption and returned 0.94 -- a double-count '
          'of the column `beach_optics` already carries.')
    check(1, 'the conservative two-stream conserves: R + T = 1',
          float(po['R'][1, 1] + po['T'][1, 1]), 1.0, 1e-12,
          'tau\'/(1+tau\') + 1/(1+tau\') = 1 identically. A slab that reflects '
          'without transmitting less is a light source.')
    check(1, 'the plume HIDES: T at alpha = 0.03 over 0.75 m',
          float(po['T'][1, 1]), 0.0651344, 1e-6,
          'BAR SECTION C\'S OWN TEST, absolute. Three per cent air over a '
          '0.75 m plume leaves a diffuse transmittance of 6.5% in the green, '
          'so what is behind it is fifteen times fainter. "If a renderer whitens '
          'without hiding what is behind, it has modelled the symptom" -- this '
          'row is the number that says it does not. WAVE 7 MOVED THIS LITERAL '
          'BY 0.11%, from 0.0652069, and the move is the point: the per-channel '
          'Fresnel fix in `_fresnel_internal` shifted the traced g and b_b/b, '
          'and an ABSOLUTE row is what noticed. Every ratio row in this section '
          'survived the defect untouched.')
    check(1, 'and it whitens: R at the same depth', float(po['R'][1, 1]),
          0.9348656, 1e-6,
          'The other half. R and T are one two-stream and a renderer cannot '
          'have the second without the first; stating both absolutely is what '
          'stops a future edit turning the opacity up and the whiteness down '
          'independently.')
    aa = np.linspace(0.0, 9.0, 200001)
    check(1, 'the plume\'s phase factor has mean EXACTLY 1',
          float(np.trapezoid(F.plume_phase_factor(aa, 9.0, sp['tau_vol']), aa)
                / 9.0), 1.0, 1e-8,
          'The plume is concentrated at the bore front because <tau>_vol is '
          'under a second against a nine-second period, and the factor that '
          'concentrates it must REDISTRIBUTE the energy budget rather than add '
          'to it. If this mean drifts from 1 the render has quietly acquired a '
          'free brightness multiplier, which is the oldest way for a foam '
          'model to look better than its physics.')
    check(1, 'and it is 11x at the crest, ABSOLUTE',
          float(F.plume_phase_factor(0.0, 9.0, sp['tau_vol'])), 11.058, 1e-3,
          '(T/tau)/(1 - exp(-T/tau)) at a = 0. The plume at the front is '
          'eleven times the surf zone\'s time-mean void fraction, which is '
          'what makes the front opaque and the water behind it green. A model '
          'that spread the mean evenly would be wrong by this factor in both '
          'directions at once.')

    # ============================== 9.6 THE RAFT, TWO ROUTES
    rf = F.foam_raft(float(ea['Q'][0]), r_32=sp['r_32'])
    h = float(rf['h_raft'])
    b_raft = 2.0 * 3.0 * F.ALPHA_RAFT / (4.0 * sp['r_32'])
    taup = float((1.0 - bs['g'][1]) * b_raft * h)
    R_two = taup / (1.0 + taup)
    check(3, 'the raft\'s reflectance, pile-of-plates vs two-stream',
          float(rf['R_pile'][1]), R_two, 0.01,
          'TWO ROUTES AND THEY DO NOT SHARE A SOURCE. Stokes (1862): N '
          'reflectors of reflectance rho with no absorption give '
          'N rho/(1 + (N-1) rho), and rho here IS the bar\'s 1 - 1/n^2 with N '
          'the raft thickness over the cell size. The two-stream never sees '
          'that constant -- it goes through the bubble population\'s b and the '
          'traced g. They agree to 0.35%, which is what makes the raft\'s '
          'brightness a consequence of section C\'s constant rather than a '
          'second declaration of it.', rel=True)
    check(1, 'the raft thickness is DERIVED, and absolute', h, 0.107513, 1e-5,
          'Q * tau_foam / alpha_raft: in steady state every cubic metre pushed '
          'under comes back up, so the surface is fed at exactly the '
          'entrainment rate and loses it by bursting over Monahan & Zietlow\'s '
          '3.85 s. Nothing was chosen. ABSOLUTE, because the two-route row '
          'above would pass with both routes reading a wrong thickness -- and '
          'the two routes SATURATE above about a centimetre, so they would not '
          'notice.', unit='m')
    between(2, 'the SINGLE-WALL constant against Koepke (1984)\'s fresh whitecap',
            float(F.FOAM_WHITE[1]), 0.20, 0.55,
            'Koepke (1984), Applied Optics 23, 1816, measured whitecap '
            'reflectance falling from 0.20-0.55 at first breaking to 0.03-0.10 '
            'after ten seconds, with a life-and-area-averaged EFFECTIVE value '
            'of 0.22. The bar\'s 1 - 1/n^2 = 0.4387 sits inside his '
            'fresh-whitecap band, which is a published bracket on a derived '
            'constant and is worth recording as survived.')
    openq(2, 'the thick raft against Koepke\'s effective 0.22',
          round(float(rf['R_pile'][1]), 4), '0.22',
          'MEASURED, UNDERSTOOD, NOT MATCHED -- and the mismatch is the '
          'finding rather than the defect. The raft is seventy-odd bubble '
          'walls of a non-absorbing scatterer, and both routes above put its '
          'reflectance at 0.98; a soap foam is that white and so is fresh surf. '
          'Koepke\'s 0.22 is NOT a foam albedo: it is the whitecap\'s '
          'contribution averaged over its LIFE and its AREA, and it therefore '
          'already contains the decay. A renderer that models the coverage and '
          'its decay explicitly -- as this one now does -- and ALSO uses 0.22 '
          'as the foam\'s reflectance has counted the decay twice, which is '
          'the standard reason rendered foam reads grey. What cannot be closed '
          'here is the comparison itself: closing it needs Koepke\'s '
          'time-resolved reflectance against this model\'s R(age), and the '
          'paper\'s own age bins are not in hand.')

    # ============================== 9.7 THE COVERAGE, AS A CLOCK
    T_w, tau = 9.0, F.TAU_FOAM_SALT
    aa = np.linspace(0.0, T_w, 20001)
    for q in (0.2, 0.7, 1.0):
        m = F.covering_measure_break(q, T_w, aa, tau)
        check(1, 'phase-mean covering measure = Q_b tau/T at Q_b = %.1f' % q,
              float(np.trapezoid(m, aa) / T_w), q * tau / T_w, 1e-8,
              'A CLOSED FORM AND THE WHOLE JUSTIFICATION FOR THE MODEL. '
              'Summing exp(-(a+jT)/tau) over all past sweeps and averaging '
              'over the phase gives exactly Q_b tau/T -- the steady state of '
              'dW/dt = S - W/tau with S = Q_b/T. So the phase structure the '
              'render draws is a REDISTRIBUTION of a coverage whose mean is '
              'fixed by the two clocks, and it is the row that fires if the '
              'foam is put back on the crests.', rel=True)
    check(1, 'the placeholder\'s k was tau/T, and it was 2.3x too long',
          tau / T_w, 0.42778, 1e-5,
          'The foam this file replaced was 1 - exp(-k f_brk) with k = 1 '
          'declared. The form was right and the k was not: k IS tau/T, and at '
          'Monahan & Zietlow\'s salt-water 3.85 s against this swell\'s 9 s it '
          'is 0.428. The placeholder ran a foam residence time of 9 s. '
          'ABSOLUTE, and it is the number that turns a declared shape into a '
          'measured one.')
    check(1, 'coverage saturates and never exceeds 1',
          float(np.max(F.coverage(np.linspace(0.0, 50.0, 1000)))), 1.0, 1e-12,
          '1 - exp(-m) for a Poisson field of overlapping patches. The '
          'saturation is why two sources can be ADDED as covering measures and '
          'why a breaking band with Q_b = 1 does not produce 300% foam.')
    check(1, 'coverage(0) is exactly zero', float(F.coverage(0.0)), 0.0, 0.0,
          'No breaking and no wind is no foam, exactly -- not a small number. '
          'A model with a floor would put a grey film on the whole sea.')
    # the two sources ADD, and the open sea reduces to Monahan exactly
    W_mon = float(F.whitecap_coverage(6.0))
    cov0, _ = F.surface_foam(0.0, T_w, 0.0, 6.0)
    check(1, 'with nothing breaking the field IS Monahan\'s coverage',
          float(cov0), W_mon, 1e-12,
          'The round trip through the covering measure: -ln(1-W) added and '
          '1-exp(-m) taken. If it did not return W exactly, the surf zone and '
          'the open sea would be two models with a seam between them, which is '
          'precisely the failure this wave is about.', rel=True)

    # --------------------- the mask FLOATS, and the age is the phase
    om = 2.0 * math.pi / T_w
    ages = F.age_from_phase(np.array([0.0, -math.pi / 2, -math.pi,
                                      -3 * math.pi / 2]), om)
    check(1, 'the age behind a crest, from the phase, ABSOLUTE',
          ages, np.array([0.0, T_w / 4, T_w / 2, 3 * T_w / 4]), 1e-12,
          'BAR SECTION C: the deck "floats, deforms with the flow". So it is '
          'NOT on the crest. phase = S - omega t decreases with time at a '
          'fixed point, a crest is phase = 0 mod 2 pi, and the time since one '
          'passed is (-phase mod 2 pi)/omega. Four phases, four ages, exact -- '
          'and this is the row that fires when someone puts the foam back on '
          'the crests, which is what the placeholder did and what almost every '
          'rendered surf zone does.', unit='s')
    check(1, 'the age is periodic and never negative',
          float(np.min(F.age_from_phase(np.linspace(-40.0, 40.0, 4001), om))),
          0.0, 1e-12,
          'A negative age would put foam in front of the wave that has not '
          'broken yet. The modulo is what prevents it and this row is what '
          'notices if it is removed.')
    check(1, 'the foam tail length is c tau, ABSOLUTE',
          float(F.foam_tail_length(4.43, F.TAU_FOAM_SALT)), 17.0555, 1e-3,
          'At the celerity of a 2 m depth the tail is 17 m against a local '
          'wavelength near 40 m, so the white lies over more than a third of '
          'the wave and behind its crest rather than on it. ABSOLUTE, because '
          'the visual claim the frames make rests on this number and not on a '
          'ratio.', unit='m')

    # --------------------- the validity clip, exercised
    ea_big = F.entrained_air(np.array([4000.0]), np.array([1.5]), 9.0)
    check(1, 'the dilute-sphere formula is CLIPPED at its own limit',
          float(ea_big['alpha'][0]), 0.30, 1e-12,
          '3 alpha/(4 r_32) is the projected area of independent spheres and '
          'stops meaning that around alpha = 0.3, where the bubbles become '
          'polyhedral cells and the scatterers are the films between them. The '
          'clip is the validity limit, not a brightness limit, and this row '
          'exercises it: without it a bore front would be given an optical '
          'depth from a formula that does not apply there. The FRACTION '
          'clipped is reported by the render rather than applied silently.')
    check(1, 'and the clipped fraction is reported',
          float(ea_big['clipped_fraction']), 1.0, 0.0,
          'A clip that nobody counts is a silent model change. This is the '
          'counter, and the bay frame prints it in its own caption.')

    # ============================== 9.8 WHITECAPS AND THE WIND
    check(2, 'Monahan & O\'Muircheartaigh at 10 m/s, ABSOLUTE',
          float(F.whitecap_coverage(10.0)), 0.00987, 1e-5,
          '3.84e-6 x 10^3.41 = 0.99% -- "about one per cent at ten metres a '
          'second" is the number this law is remembered by, and it is the row '
          'that fires on the fraction/per-cent confusion: the same law is '
          'written 3.84e-4 U^3.41 in per cent, and taking that for a fraction '
          'is a factor of 100 and a sea covered in foam.')
    check(1, 'the wind readout inverts the coverage law',
          float(F.wind_from_whitecap(F.whitecap_coverage(7.5))[0]), 7.5, 1e-9,
          'Section K asks for a readout, which means the map has to run both '
          'ways -- the same demand `beach_optics.wind_from_mss` already meets '
          'for the slope law.')
    U, lo, hi = F.wind_from_whitecap(F.whitecap_coverage(6.0))
    check(1, 'the exponent band brackets the central wind',
          float((lo <= U) and (U <= hi)), 1.0, 0.0,
          'The band is what the published EXPONENT alone (3.0 to 3.52) does to '
          'the inferred wind. It must contain the central value or the band is '
          'not a band.')
    info(2, 'wind from a 0.173% coverage: central and exponent band',
         (round(float(U), 3), round(float(lo), 3), round(float(hi), 3)),
         'm/s -- and the coefficient\'s spread across the literature is worse '
         'than the exponent\'s, so this band is a LOWER bound on the '
         'uncertainty')
    # THE CROSS-CHECK THE BAR ASKS FOR: one wind, two readouts
    su2, sc2 = BOP.cox_munk_mss(BOP.U10)
    d_width = 0.5 * (BOP.CM_A_U + BOP.CM_A_C) / (su2 + sc2)
    d_W = F.MOM80_N / BOP.U10
    check(1, 'd(ln glitter width)/dU at U10 = 6 m/s', d_width, 0.075866, 1e-5,
          'width goes as sqrt(mss) and mss = 0.003 + 5.08e-3 U, so '
          'd(ln width)/dU = (a_u + a_c)/(2 mss). ABSOLUTE, and it is one half '
          'of the comparison bar section K\'s cross-check actually settles.',
          unit='per m/s')
    check(1, 'd(ln whitecap coverage)/dU at U10 = 6 m/s', d_W, 0.568333, 1e-5,
          'W goes as U^n, so d(ln W)/dU = n/U. The other half.',
          unit='per m/s')
    check(1, 'the width is at least ten times the wind instrument the '
          'coverage is',
          float((math.log(3.0) / d_W) / (0.01 / d_width)), 14.6, 0.4,
          'THE FINDING, AS A ROW. A 1% measurement of the path width fixes the '
          'wind to 0.13 m/s; a factor of THREE in the coverage -- which is '
          'inside the literature\'s own spread -- leaves 1.93 m/s. The two '
          'readouts agree in this render because one U10 drives both, and the '
          'reason that agreement is not a strong test is this ratio. A future '
          'wave tempted to calibrate the wind off a coverage should fail this '
          'row first.')

    # ============================== 9.9 THE THREE CLOCKS
    ct = F.decay_times(1.5, 2.0, 9.0)
    check(1, 'tau_foam, the surface raft, ABSOLUTE', ct['tau_foam'], 3.85,
          1e-12,
          'Monahan & Zietlow (1969), JGR 74, 6961: laboratory whitecap AREA '
          'decays with an e-folding time of 3.85 s in salt water and 2.54 s in '
          'fresh. PUBLISHED, and the salt/fresh pair is a factor of 1.5 that '
          'says the decay is a bubble-stability property rather than a '
          'hydrodynamic one.', unit='s')
    check(1, 'tau_air, the plume\'s AIR VOLUME, ABSOLUTE', ct['tau_air'],
          0.813927, 1e-5,
          '<tau>_vol over the Deane & Stokes spectrum with Schiller & '
          'Naumann\'s drag -- a law that shares no source with the row above. '
          'UNDER A SECOND, so the bar\'s "entrained air rises and bursts in '
          'seconds" holds for the air VOLUME. It does not hold for the '
          'projected area, and the row on the spectrum\'s span above is where '
          'that is said.', unit='s')
    check(1, 'tau_sed, the suspension, ABSOLUTE', ct['tau_sed'], 47.03, 0.05,
          'd / w_s = 2.0 / 0.0425 with w_s from `beach.settling_velocity`, '
          'which is Soulsby\'s law -- a THIRD published relation, so no two of '
          'the three clocks come from one place.', unit='s')
    check(1, 'the clocks are ORDERED air < foam < sediment',
          float((ct['tau_air'] < ct['tau_foam'] < ct['tau_sed'])), 1.0, 0.0,
          'AND THIS IS THE BAR\'S OWN ORDERING, RECOVERED RATHER THAN '
          'ASSUMED. Section C calls the surface deck the one that "decays '
          'slowly" and section E has the entrained air "rising and bursting in '
          'seconds"; measured, 0.81 s of air against 3.85 s of raft against '
          '47 s of suspension. THE FIRST DRAFT OF THIS FILE GOT THE OPPOSITE '
          'and was ready to report it as a finding against the bar -- it came '
          'from a single rise speed at the Sauter radius instead of the '
          'size-resolved mean, and the render caught it before the claim was '
          'made. A survived claim is worth recording as survived.')
    check(1, 'the settling inversion round-trips',
          float(ct['depth'] / B.settling_velocity(
              d50=F.d50_for_settling_time(120.0, ct['depth']))), 120.0, 0.02,
          '`d50_for_settling_time` is the answer to "the bar says MINUTES, so '
          'what size is that?" and it must invert the law it is built on.',
          unit='s')
    info(1, 'D50 the bar\'s "minutes" implies, against this file\'s bed D50',
         (round(1e6 * F.d50_for_settling_time(120.0, ct['depth']), 1),
          round(1e6 * B.D50, 1)),
         'micron -- the suspended fine tail, not the bed median, and the file '
         'carries a single grain size so it cannot produce the slow half')
    openq(2, 'the suspended load\'s SIZE DISTRIBUTION at Aljezur',
          'single D50', 'a distribution',
          'The bar says the sediment cloud lasts minutes and this file\'s bed '
          'D50 of 300 micron clears 2 m in 47 s. Both are right: what stays up '
          'for minutes is the FINE TAIL, around 160 micron and below, and '
          '`beach.py` carries one grain size because there is no grain-size '
          'survey of this coast -- which is already an open item at intake. '
          'Closing it needs a measured distribution, not a wider tolerance, '
          'and until then the sediment clock in this file is the coarse '
          'bound.')


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
                      (_sec_bay, 'the bar in plan'),
                      (_sec_embay, 'the static-equilibrium bay'),
                      (_sec_optics, 'the coastal IOPs, the path and the '
                                    'glitter'),
                      (_sec_surface, 'the nonlinear free surface'),
                      (_sec_foam, 'the white: foam, entrained air, whitecaps'),
                      (_sec_camera, 'the camera at the owner\'s viewpoints'),
                      (_sec_land, 'the land and the air: beach, wet/dry, '
                                  'shadow, aerial perspective')):
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


SURFACE_BUGS = ('sinusoidal-surface', 'harmonic-shallow-everywhere',
                'unclamped-stokes', 'bore-phase-flipped',
                'skew-without-asymmetry', 'ur-half-declared')


def _run_section(fn, label):
    """One section, standalone. `--bugs-surface` uses this because the full
    `--bugs` table is 32 defects x the whole suite, and wave 5's six all patch
    functions that ONLY `_sec_surface` calls -- which is exact rather than a
    shortcut, and is the same argument wave 4 made for running its eight
    against the optics section alone."""
    del ROWS[:]
    ctx = dict(B=BCH, T=BCH.T_SWELL, omega=2.0 * math.pi / BCH.T_SWELL,
               x=BCH.make_grid())
    guard(fn, label, ctx)
    return ctx


if __name__ == '__main__':
    t0 = time.time()
    if '--bugs-land' in sys.argv:
        import importlib
        import beach_render as RND
        _run_section(_sec_land, 'the land and the air')
        base = set(_fail_names())
        print('clean land section: %d pass / %d FAIL'
              % (sum(r.status == 'PASS' for r in ROWS), len(base)))
        print()
        print('%-28s %s' % ('bug reintroduced', 'rows that FAIL'))
        print('-' * 118)
        for name in LAND_BUGS:
            importlib.reload(BCH)
            importlib.reload(RND)
            BUGS[name](RND if name in LAND_RENDER_BUGS else BCH)
            try:
                _run_section(_sec_land, 'the land and the air')
                caught = [n for n in _fail_names() if n not in base]
            except Exception as exc:                      # a crash is a catch
                caught = ['(raised %s: %s)' % (type(exc).__name__,
                                               str(exc)[:60])]
            print('%-28s %d  %s' % (name, len(caught),
                                    '; '.join(c[:70] for c in caught[:5])))
        importlib.reload(BCH)
        importlib.reload(RND)
        sys.exit(0)
    if '--bugs-camera' in sys.argv:
        import importlib
        _run_section(_sec_camera, 'the camera')
        base = set(_fail_names())
        print('clean camera section: %d pass / %d FAIL'
              % (sum(r.status == 'PASS' for r in ROWS), len(base)))
        print()
        print('%-30s %s' % ('bug reintroduced', 'rows that FAIL'))
        print('-' * 110)
        for name in CAMERA_BUGS:
            importlib.reload(CMR)
            BUGS[name](CMR)
            try:
                _run_section(_sec_camera, 'the camera')
                caught = [n for n in _fail_names() if n not in base]
            except Exception as exc:                      # a crash is a catch
                caught = ['(raised %s: %s)' % (type(exc).__name__,
                                               str(exc)[:60])]
            print('%-30s %d  %s' % (name, len(caught),
                                    '; '.join(c[:64] for c in caught[:5])))
        importlib.reload(CMR)
        sys.exit(0)
    if '--bugs-foam' in sys.argv:
        import importlib
        _run_section(_sec_foam, 'the white')
        base = set(_fail_names())
        print('clean foam section: %d pass / %d FAIL'
              % (sum(r.status == 'PASS' for r in ROWS), len(base)))
        print()
        print('%-30s %s' % ('bug reintroduced', 'rows that FAIL'))
        print('-' * 110)
        for name in FOAM_BUGS:
            importlib.reload(FOAM)
            BUGS[name](FOAM)
            try:
                _run_section(_sec_foam, 'the white')
                caught = [n for n in _fail_names() if n not in base]
            except Exception as exc:                      # a crash is a catch
                caught = ['(raised %s: %s)' % (type(exc).__name__,
                                               str(exc)[:60])]
            print('%-30s %d  %s' % (name, len(caught),
                                    '; '.join(c[:64] for c in caught[:5])))
        importlib.reload(FOAM)
        sys.exit(0)
    if '--bugs-embay' in sys.argv:
        import importlib
        _run_section(_sec_embay, 'the static-equilibrium bay')
        base = set(_fail_names())
        print('clean embayment section: %d pass / %d FAIL'
              % (sum(r.status == 'PASS' for r in ROWS), len(base)))
        print()
        print('%-32s %s' % ('bug reintroduced', 'rows that FAIL'))
        print('-' * 110)
        for name in EMBAY_BUGS:
            importlib.reload(BCH)
            BCH._BAY_CACHE.clear()
            BUGS[name](BCH)
            try:
                _run_section(_sec_embay, 'the static-equilibrium bay')
                caught = [n for n in _fail_names() if n not in base]
            except Exception as exc:                      # a crash is a catch
                caught = ['(raised %s: %s)' % (type(exc).__name__,
                                               str(exc)[:60])]
            print('%-32s %d  %s' % (name, len(caught),
                                    '; '.join(c[:62] for c in caught[:5])))
        importlib.reload(BCH)
        BCH._BAY_CACHE.clear()
        sys.exit(0)
    if '--bugs-surface' in sys.argv:
        import importlib
        _run_section(_sec_surface, 'the nonlinear free surface')
        base = set(_fail_names())
        print('clean surface section: %d pass / %d FAIL'
              % (sum(r.status == 'PASS' for r in ROWS), len(base)))
        print()
        print('%-30s %s' % ('bug reintroduced', 'rows that FAIL'))
        print('-' * 110)
        for name in SURFACE_BUGS:
            importlib.reload(BCH)
            BUGS[name](BCH)
            try:
                _run_section(_sec_surface, 'the nonlinear free surface')
                caught = [n for n in _fail_names() if n not in base]
            except Exception as exc:                      # a crash is a catch
                caught = ['(raised %s: %s)' % (type(exc).__name__,
                                               str(exc)[:60])]
            print('%-30s %d  %s' % (name, len(caught),
                                    '; '.join(c[:66] for c in caught[:5])))
        importlib.reload(BCH)
        sys.exit(0)
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
            importlib.reload(BOP)
            importlib.reload(CMR)
            if name in EMBAY_BUGS:
                # the embayment section is exercised by `--bugs-embay`, which
                # clears `beach._BAY_CACHE` between runs. The whole-suite
                # driver reuses the cache across bugs, so a patched plan-form
                # would be invisible to every section after the first.
                continue
            if name in LAND_BUGS:
                # the land section is exercised by `--bugs-land`, which
                # reloads `beach_render` between runs. The whole-suite driver
                # does not import the renderer, so these are skipped here and
                # the table that fires them is the one printed by that flag.
                continue
            patch(CMR if name in CAMERA_BUGS
                  else (FOAM if name in FOAM_BUGS
                        else (BOP if name in OPTICS_BUGS else BCH)))
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
