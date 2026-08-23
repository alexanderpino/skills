"""External checks on ice, the free jet, water entry, open channel and films.

    python3 validate_phases.py        # exits non-zero on any FAIL
    python3 validate_phases.py -v     # also prints every tolerance's reason
    python3 validate_phases.py --bugs # prove the rows can fail

WHAT THESE FIVE HAVE IN COMMON. Each is a kind of water the rest of this skill
did not reach, and each was found by asking what AXIS was missing rather than
what subject was. Ice is the phase axis; the free jet is the Weber axis; water
entry is the impulse axis; the hydraulic jump is travelling-versus-standing;
the film is interference rather than absorption.

TIERS as elsewhere in this skill: 1 closed form, 2 published, 3 independent
method. Every tolerance is justified from the estimator's own error, and `-v`
prints the justification so a widened tolerance is visible in a diff.
"""
import math
import sys

import numpy as np

import ice as ICE                                               # noqa: E402
import impact as IMP                                            # noqa: E402
import jet as JET                                               # noqa: E402
import openchannel as OC                                        # noqa: E402
import optics as OPT                                            # noqa: E402
import thinfilm as TF                                           # noqa: E402


class Row(object):
    __slots__ = ('tier', 'name', 'exp', 'got', 'status', 'why', 'unit')

    def __init__(self, tier, name, exp, got, status, why, unit):
        self.tier, self.name, self.exp, self.got = tier, name, exp, got
        self.status, self.why, self.unit = status, why, unit


ROWS = []
BUGS = {}


def _fmt(v):
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, float):
        return '%.6g' % v
    if isinstance(v, (list, tuple, np.ndarray)):
        a = np.asarray(v).reshape(-1)
        if a.dtype.kind in 'US':          # labels, not quantities
            return '[' + ' '.join(str(x)[:6] for x in a[:2]) + (
                ' ...' if a.size > 2 else '') + ']'
        return '[' + ' '.join('%.4g' % x for x in a[:3]) + (
            ' ...' if a.size > 3 else '') + ']'
    return str(v)


def check(tier, name, got, exp, tol, why, unit='', rel=False):
    g, e = np.asarray(got, float), np.asarray(exp, float)
    if g.size == 0 or e.size == 0:
        raise AssertionError('row "%s" compares an EMPTY selection' % name)
    lim = np.asarray(tol, float) * (np.abs(e) if rel else 1.0)
    ok = bool(np.all(np.abs(g - e) <= lim + 1e-300))
    ROWS.append(Row(tier, name, exp, got, 'PASS' if ok else 'FAIL', why, unit))
    return ok


def between(tier, name, got, lo, hi, why, unit=''):
    g = float(got)
    ROWS.append(Row(tier, name, '%s..%s' % (_fmt(lo), _fmt(hi)), got,
                    'PASS' if lo <= g <= hi else 'FAIL', why, unit))
    return lo <= g <= hi


def check_eq(tier, name, got, exp, why, unit=''):
    """Exact comparison for non-numeric answers -- classes, names, regimes.

    `check` coerces to float, which is right for every quantity and wrong for
    a label. Separating them stops a string row from crashing the section it
    is in and taking every other row with it, which is what it did once.
    """
    ok = list(got) == list(exp)
    ROWS.append(Row(tier, name, exp, got, 'PASS' if ok else 'FAIL', why, unit))
    return ok


def info(tier, name, got, note):
    ROWS.append(Row(tier, name, None, got, 'INFO', note, ''))


# ==========================================================================
#  A · ICE
# ==========================================================================
def _sec_ice():
    a = ICE.absorption_from_k(ICE.K_ICE, ICE.LAM_NM * 1e-9)
    check(1, 'a = 4 pi k / lambda reproduces the published absorption',
          a, ICE.ABS_ICE, 1e-15,
          'DERIVED. The standard relation between the imaginary index and the '
          'Beer-Lambert coefficient, evaluated on Warren & Brandt (2008)\'s '
          'own tabulated k at this project\'s three band points. Tolerance is '
          'machine epsilon because both sides are the same float64 '
          'expression -- the row exists to pin the CONSTANTS, not the algebra.',
          '1/m')

    aw = np.asarray(OPT.ABS, float)
    check(2, 'ice and water absorb green identically, to 1.5 %',
          a[1] / aw[1], 1.0, 0.015,
          'PUBLISHED, AND IT IS THE ROW THAT KILLS "ICE IS TINTED WATER". At '
          '550 nm the two coefficients agree to 1.3 %% (%.5f against %.5f). '
          'They are NOT a scaled copy of each other: at the same wavelength '
          'triple ice absorbs half the red and a quarter of the blue. A '
          'material that matches in one channel and differs by 4x in another '
          'has a different SHAPE, and no tint reproduces a shape.'
          % (a[1], aw[1]), '-')

    check(1, 'ice is 2.15x more spectrally selective than water',
          ICE.selectivity(a) / ICE.selectivity(aw), 2.148, 0.01,
          'DERIVED from the same two triples. Red:blue absorption ratio is '
          '%.1f for ice against %.1f for water. This is the quantitative '
          'answer to "why is glacier ice blue": not because it is colder '
          'water, but because its absorption spectrum is more than twice as '
          'steep across the visible.'
          % (ICE.selectivity(a), ICE.selectivity(aw)), '-')

    # Kubelka-Munk: the semi-infinite reflectance depends only on K/S.
    K = a
    for scale in (0.5, 2.0, 10.0):
        r1 = ICE.km_reflectance_infinite(K, 30.0)
        r2 = ICE.km_reflectance_infinite(K * scale, 30.0 * scale)
        check(1, 'KM reflectance depends on K and S only through their ratio '
                 '(x%g)' % scale, r2, r1, 1e-12,
              'DERIVED, AND IT IS THE STRUCTURAL DIFFERENCE FROM CLEAR WATER. '
              'A semi-infinite scattering slab has a colour that does not '
              'depend on how deep it is -- exactly the opposite of clear '
              'water, whose colour is nothing but depth. That is why a '
              'crevasse reads the same blue from its lip as from ten metres '
              'down, and why "make it deeper" is not the control.', '-')

    # Round-trip the inverse, which is how a photograph is read.
    R = ICE.km_reflectance_infinite(K, 30.0)
    check(1, 'the KM inverse round-trips',
          ICE.km_ratio_from_reflectance(R), K / 30.0, 1e-12,
          'DERIVED. `K/S = (1-R)^2/(2R)` must return what produced R. The '
          'inverse is the direction a reference photograph is read in, so a '
          'forward-only implementation is untested in the direction it is '
          'used.', '-')

    # Bubble density orders the appearance, monotonically and in the right way.
    S = [ICE.bubble_scattering(1e-4, n) for n in (2e6, 5e8, 2e10)]
    Rs = [ICE.km_reflectance_infinite(K, s) for s in S]
    check(1, 'more bubbles means brighter and less saturated, in every channel',
          [bool(np.all(np.diff([r[c] for r in Rs]) > 0)) for c in range(3)],
          [True] * 3, 0,
          'DERIVED. Scattering competes with absorption, so raising S raises '
          'R monotonically. The blue rises least because it started highest, '
          'which is why firn is white and clear lake ice is blue: the same '
          'material at two bubble densities, not two materials.', 'bool')
    info(1, 'reflectance triple at three bubble densities',
         [np.round(r, 3).tolist() for r in Rs],
         'Lake ice (sparse), glacier ice, firn. Reported rather than bounded: '
         'the densities are illustrative and the SHAPE is the claim.')

    check(1, 'ice\'s interface is nearly water\'s, and the interior is not',
          ICE.fresnel_normal(ICE.IOR_ICE[1]) / ICE.fresnel_normal(OPT.IOR[1]),
          0.881, 0.01,
          'DERIVED, AND IT IS THE POINT OF COMPUTING IT. Normal-incidence '
          'reflectance differs by 12 %% -- a small, real shift -- while the '
          'interior differs by a factor of four in blue and by a change of '
          'mechanism. Anyone tuning ice by moving the specular is adjusting '
          'the 12 %% and leaving the rest.', '-')


# ==========================================================================
#  B · THE FREE JET
# ==========================================================================
def _sec_jet():
    d, u = 12e-3, 12.0
    check(1, 'Oh = sqrt(We_l)/Re holds identically',
          JET.oh_from_we_re(JET.weber_liquid(u, d), JET.reynolds(u, d)),
          JET.ohnesorge(d), 1e-12,
          'DERIVED. The identity that says the regime diagram\'s two axes are '
          'not independent choices: given any two of We, Re and Oh the third '
          'is fixed. A file that computes them separately can disagree with '
          'itself, and this row is what stops that.', '-')

    check(2, 'a Rayleigh-regime jet makes drops 1.89x its own diameter',
          JET.rayleigh_drop_diameter(1.0), 1.891, 0.002,
          'PUBLISHED + DERIVED. Rayleigh (1878) gives the most-unstable '
          'wavelength as 4.508 diameters; volume conservation turns one '
          'wavelength of column into one drop, D = d (3/2 * 4.508)^(1/3) = '
          '1.891 d. The drops are nearly TWICE the nozzle, which is the '
          'visible signature of the regime and exactly what a particle system '
          'sized to the nozzle gets wrong.', '-')

    # The four named cases land in four different regimes.
    cases = (('water pistol', 8.0, 1.5e-3, 'first wind-induced'),
             ('garden hose', 12.0, 12e-3, 'second wind-induced'),
             ('fire hose', 30.0, 29e-3, 'atomization'),
             ('slow trickle', 0.6, 4e-3, 'Rayleigh'))
    got = [JET.regime(u_, d_) for _, u_, d_, _e in cases]
    check(2, 'the four everyday jets land in four different regimes',
          [g == e for (_, _, _, e), g in zip(cases, got)], [True] * 4, 0,
          'PUBLISHED BOUNDARIES, applied to cases nobody tuned them for. Lin '
          '& Reitz\'s We_g thresholds 0.4 / 13 / 40.3 sort a trickle, a water '
          'pistol, a garden hose and a fire hose into the four regimes '
          'without adjustment -- which is the evidence that the axis is real '
          'rather than a relabelling. Got: %s.' % ', '.join(got), 'regime')

    # The aerodynamic Weber number is the AIR's, and the difference is huge.
    check(1, 'building We on the liquid density is an 829x error',
          JET.weber_liquid(u, d) / JET.weber_aero(u, d),
          JET.RHO_W / JET.RHO_A, 1e-9,
          'DERIVED. The ratio is exactly rho_w/rho_a = %.0f. Using the liquid '
          'density in the regime diagram puts every jet past the atomization '
          'boundary, which is why "everything atomises" is a common wrong '
          'reading of it.' % (JET.RHO_W / JET.RHO_A), '-', True)

    # Breakup length refuses outside its own regime.
    fin = np.isfinite(JET.breakup_length_rayleigh(8.0, 1.5e-3))
    nan = not np.isfinite(JET.breakup_length_rayleigh(30.0, 29e-3))
    check(1, 'the breakup-length correlation refuses outside its regime',
          [bool(fin), bool(nan)], [True, True], 0,
          'RULING: A CORRELATION THAT KEEPS RETURNING A NUMBER OUTSIDE ITS '
          'RANGE IS HOW A WRONG TREND SHIPS. Evaluated on a fire hose this '
          'formula gives ~6000 diameters of intact column -- not merely '
          'inaccurate but BACKWARDS, since past the first wind-induced '
          'boundary the length falls with speed instead of rising. It returns '
          'NaN there and the caller has to notice.', 'bool')

    # In-regime, the length grows as sqrt(We) -- the trend, not the constant.
    us = np.array([2.0, 4.0, 8.0])
    L = np.array([float(JET.breakup_length_rayleigh(x, 1.5e-3)) for x in us])
    check(1, 'in the Rayleigh regime the intact length grows linearly with U',
          L[1:] / L[:-1], us[1:] / us[:-1], 1e-9,
          'DERIVED. L ~ sqrt(We_l) d and We_l ~ U^2, so L ~ U exactly. The '
          'SCALING is checked and the experimental constant is not, because '
          'the constant is fitted and the trend is the claim.', '-', True)


# ==========================================================================
#  C · WATER ENTRY
# ==========================================================================
def _sec_impact():
    d = 0.12
    check(1, 'pinch-off timing is set by the body size, not the impact speed',
          [float(IMP.cavity_pinchoff_time(d, 5.0)),
           float(IMP.cavity_pinchoff_time(d, 50.0))],
          [float(IMP.cavity_pinchoff_time(d, 5.0))] * 2, 1e-15,
          'DERIVED FROM THE SCALING. t_p ~ sqrt(d/g) carries no velocity, so '
          'hitting the water ten times harder does not delay the second '
          'flash. It moves it DEEPER instead -- which is the next row. A '
          'renderer that ties the Worthington timing to impact energy has the '
          'dependency on the wrong variable.', 's')

    check(1, 'pinch-off depth grows as sqrt(Fr), so it does carry the speed',
          IMP.cavity_pinchoff_depth(d, 20.0) / IMP.cavity_pinchoff_depth(d, 5.0),
          4.0, 1e-9,
          'DERIVED. h_p ~ d sqrt(Fr) and Fr ~ U^2, so h_p ~ U exactly: a 4x '
          'impact speed is a 4x pinch-off depth. Stated as the measured ratio '
          'so the exponent is pinned rather than described.', '-', True)

    # The jet exceeds the impact speed for a deep cavity -- the qualitative
    # fact a renderer must not get backwards.
    check(1, 'the Worthington jet leaves faster than the body arrived',
          float(IMP.worthington_jet_speed(20.0, 1.2)) > 20.0, True, 0,
          'THE ONE QUALITATIVE CLAIM THIS SECTION MAKES, and it is checked '
          'rather than asserted because it is counter-intuitive: the cavity '
          'walls converge on a line, focusing a large area of slow water into '
          'a small one, exactly as a collapsing bubble does. The magnitude '
          'depends on an efficiency and a neck ratio that are NOT derived '
          'here and are exposed as arguments; only the inequality is claimed.',
          'bool')

    check(1, 'the crown spreads as sqrt(t), not linearly',
          IMP.crown_radius(np.array([1.0, 4.0]), 5.0, 0.1)[1]
          / IMP.crown_radius(np.array([1.0, 4.0]), 5.0, 0.1)[0],
          2.0, 1e-12,
          'DERIVED. r ~ sqrt(U d t), so quadrupling the time doubles the '
          'radius. A crown keyframed with a linear expansion is wrong early '
          'and wrong late, and no easing curve fixes both ends.', '-')

    cav_small, _ = IMP.splash_regime(1.0, 2.5e-3)
    cav_big, _ = IMP.splash_regime(20.0, 1.2)
    check(1, 'a slow small impact makes no cavity and a fast large one does',
          [bool(cav_small), bool(cav_big)], [False, True], 0,
          'DERIVED. Fr = U^2/(g d) is the body\'s momentum against the '
          'hydrostatic pressure that closes the cavity behind it. The two '
          'regimes need DIFFERENT event sequences -- crown only, against all '
          'four -- and drawing the four-event sequence for a raindrop is as '
          'wrong as drawing one burst for a boulder.', 'bool')


# ==========================================================================
#  D · THE HYDRAULIC JUMP
# ==========================================================================
def _sec_jump():
    check(1, 'Belanger returns the upstream depth at Fr = 1',
          OC.conjugate_depth(0.2, 1.0), 0.2, 1e-15,
          'DERIVED. At Fr = 1 the flow is critical and there is nothing to '
          'jump: (1/2)(-1 + sqrt(9)) = 1. A closure that does not return the '
          'identity here has a sign or a factor wrong and will produce a jump '
          'in still water.', 'm')

    check(1, 'Belanger is the momentum root, checked against the quadratic',
          OC.conjugate_depth(0.2, 3.0),
          0.2 * 0.5 * (-1.0 + math.sqrt(1.0 + 8.0 * 9.0)), 1e-15,
          'DERIVED, TWO WAYS. The conjugate depth is the positive root of the '
          'momentum balance; evaluating the closed form and the root of the '
          'quadratic must agree. Energy is NOT conserved across a jump -- '
          'that is what a jump IS -- so a model closed on energy returns the '
          'upstream depth and no jump at all.', 'm')

    h1, fr1 = 0.2, 6.0
    h2 = OC.conjugate_depth(h1, fr1)
    q = fr1 * math.sqrt(OC.G * h1) * h1
    e1, e2 = OC.specific_energy(h1, q), OC.specific_energy(h2, q)
    check(1, 'the energy loss formula matches the specific-energy difference',
          OC.energy_loss(h1, h2), e1 - e2, 1e-9,
          'DERIVED, TWO WAYS THAT SHARE NO LINE. dE = (h2-h1)^3/(4 h1 h2) is '
          'an algebraic identity; E1 - E2 evaluates depth plus velocity head '
          'on each side. Agreement is what says the momentum closure and the '
          'energy bookkeeping describe the same jump.', 'm', True)

    check(1, 'the loss grows as the cube of the depth rise',
          OC.energy_loss(1.0, 3.0) / OC.energy_loss(1.0, 2.0),
          (2.0 ** 3 / (4.0 * 3.0)) / (1.0 ** 3 / (4.0 * 2.0)), 1e-12,
          'DERIVED. A cube, which is why strong jumps are violent out of all '
          'proportion to their size and why the aeration budget cannot be '
          'linear in the step. This term is what feeds the foam sections as a '
          'RATE rather than as a mask.', '-')

    check_eq(2, 'the five jump classes land at their published Froude bands',
          [OC.jump_class(f).split(' --')[0]
           for f in (0.8, 1.4, 2.0, 3.5, 6.0, 11.0)],
          ['no jump (subcritical)', 'undular', 'weak', 'oscillating',
           'steady', 'strong'],
          'PUBLISHED CLASSIFICATION. Carried because the classes are a LOOK '
          'and not a taxonomy: undular has standing waves and almost no air, '
          'steady is the classic rapid, strong is violent spray. A renderer '
          'drawing the same white water for all five is drawing one of them.',
          'class')

    check(1, 'the aeration budget is a power, and it vanishes with the jump',
          [float(OC.aeration_rate(0.2, OC.conjugate_depth(0.2, 1.0), 0.3)),
           float(OC.aeration_rate(0.2, OC.conjugate_depth(0.2, 6.0), 0.3)) > 0],
          [0.0, True], 1e-12,
          'DERIVED. P = rho g q dE, so at Fr = 1 there is no jump, no loss '
          'and no entrained air -- the same calm-sea control the whitecap '
          'sections use, applied to rapids. White water that survives when '
          'the flow goes subcritical is painted, not computed.', 'W/m')


# ==========================================================================
#  E · THE THIN FILM
# ==========================================================================
def _sec_film():
    # A vanishing film must return the bare interface.
    r_thin = TF.airy_reflectance(550e-9, 1e-12, 1.0)
    rs, rp = TF.fresnel_rs_rp(TF.N_AIR, TF.N_WATER, 1.0)
    check(1, 'a film of zero thickness returns the bare Fresnel reflectance',
          float(r_thin), 0.5 * (rs ** 2 + rp ** 2), 2e-6,
          'DERIVED. With d -> 0 the phase delay vanishes, the Airy sum '
          'collapses and the two interfaces behave as one. Tolerance 2e-6 is '
          'the residual phase at 1 pm of film, which is the estimator\'s own '
          'error rather than a chosen slack.', '-')

    # Interference is periodic in 1/lambda -- adjacent maxima are a fringe apart.
    d_film, ci = 800e-9, 0.9
    ct = TF.snell_cos(TF.N_AIR, TF.N_OIL, ci)
    lam = np.linspace(380e-9, 730e-9, 20001)
    R = TF.airy_reflectance(lam, d_film, ci)
    pk = lam[1:-1][(R[1:-1] > R[:-2]) & (R[1:-1] > R[2:])]
    if pk.size >= 2:
        meas = float(np.mean(np.diff(pk)))
        pred = float(TF.fringe_spacing_nm(TF.N_OIL, d_film, ct,
                                          float(pk.mean())))
        check(1, 'measured fringe spacing matches lambda^2/(2 n d cos)',
              meas, pred, 0.06,
              'DERIVED, TWO WAYS. The closed form is a first-order expansion '
              'of the phase condition; the measurement counts maxima of the '
              'full Airy sum. 6 %% relative is the expansion\'s own error '
              'across a 350 nm band, not a slack -- the spacing itself varies '
              'across the band because it goes as lambda^2.', 'm', True)
    else:
        info(1, 'fringe spacing', 'too few maxima in band', 'Film too thin.')

    # The aliasing threshold -- the number the chapter needs.
    e_thin, f_thin = TF.rgb_aliasing_error(200e-9, 0.8)
    e_thick, f_thick = TF.rgb_aliasing_error(800e-9, 0.8)
    check(1, 'RGB error grows more than tenfold from one fringe to two',
          e_thick / e_thin > 10.0, True, 0,
          'MEASURED, AND STATED AS A RATIO RATHER THAN A THRESHOLD -- because '
          'a threshold here would have been a number chosen to make the row '
          'pass. At 200 nm of film there is %.1f fringe across the visible '
          'and three-sample RGB is %.1f %% from the band-integrated truth; at '
          '800 nm there are %.1f fringes and the error is %.0f %%, a factor '
          'of %.0f. This is '
          '"a channel is a band, not a wavelength" at its sharpest, and it is '
          'why the production model pre-integrates the spectral response '
          'instead of sampling it.'
          % (f_thin, 100 * e_thin, f_thick, 100 * e_thick,
             e_thick / e_thin), 'bool')

    # The hue must swing with angle -- the signature a tint cannot fake.
    lam_s = np.linspace(400e-9, 700e-9, 301)
    r_norm = TF.airy_reflectance(lam_s, 500e-9, 0.99)
    r_graze = TF.airy_reflectance(lam_s, 500e-9, 0.25)
    peak_n = float(lam_s[int(np.argmax(r_norm))])
    peak_g = float(lam_s[int(np.argmax(r_graze))])
    check(1, 'the reflectance peak moves with viewing angle',
          abs(peak_n - peak_g) > 20e-9, True, 0,
          'DERIVED. The optical path carries cos(theta_t), so tilting the '
          'view shortens it and slides the fringes. Peak at %.0f nm near '
          'normal against %.0f nm at grazing -- a %.0f nm swing. THIS is the '
          'signature of a film, and no tint, gradient or fresnel curve '
          'reproduces it, because none of them is a function of wavelength '
          'AND angle together.'
          % (peak_n * 1e9, peak_g * 1e9, abs(peak_n - peak_g) * 1e9), 'bool')


# ==========================================================================
#  the deliberate defects
# ==========================================================================
def _bug_ice_tinted_water(mod):
    """Ice given water's absorption spectrum, scaled -- the category error."""
    mod.ABS_ICE = np.asarray(OPT.ABS, float) * 0.55


def _bug_jet_liquid_weber(mod):
    """The regime diagram read on the liquid Weber number."""
    mod.weber_aero = mod.weber_liquid


def _bug_jet_no_regime_guard(mod):
    """The breakup correlation answering everywhere."""
    def bad(u, d, rho=mod.RHO_W, sigma=mod.SIGMA, c=None):
        c = 10.0 if c is None else float(c)
        return c * np.sqrt(mod.weber_liquid(u, d, rho, sigma)) * np.asarray(d, float)
    mod.breakup_length_rayleigh = bad


def _bug_impact_time_carries_speed(mod):
    """Pinch-off timing tied to impact energy."""
    orig = mod.cavity_pinchoff_time

    def bad(d, u, g=mod.G, c=None):
        return orig(d, u, g, c) * (1.0 + 0.05 * np.asarray(u, float))
    mod.cavity_pinchoff_time = bad


def _bug_jump_energy_closure(mod):
    """The jump closed on energy instead of momentum -- no jump at all."""
    def bad(h1, fr1):
        return np.asarray(h1, float) * np.ones_like(np.asarray(fr1, float))
    mod.conjugate_depth = bad


def _bug_film_drops_sign(mod):
    """Fresnel amplitudes taken as magnitudes -- the pi phase discarded."""
    orig = mod.fresnel_rs_rp

    def bad(n_i, n_t, cos_i):
        rs, rp = orig(n_i, n_t, cos_i)
        return np.abs(rs), np.abs(rp)
    mod.fresnel_rs_rp = bad


BUGS.update({
    'ice-tinted-water': (_bug_ice_tinted_water, 'ice'),
    'jet-liquid-weber': (_bug_jet_liquid_weber, 'jet'),
    'jet-no-regime-guard': (_bug_jet_no_regime_guard, 'jet'),
    'impact-time-carries-speed': (_bug_impact_time_carries_speed, 'impact'),
    'jump-energy-closure': (_bug_jump_energy_closure, 'openchannel'),
    'film-drops-sign': (_bug_film_drops_sign, 'thinfilm'),
})

SECTIONS = ((_sec_ice, 'ice: a different spectrum and a different mechanism'),
            (_sec_jet, 'the free jet along the Weber axis'),
            (_sec_impact, 'water entry: cavity, pinch-off, Worthington jet'),
            (_sec_jump, 'the hydraulic jump'),
            (_sec_film, 'thin-film interference'))


def run_suite():
    del ROWS[:]
    for fn, label in SECTIONS:
        try:
            fn()
        except Exception as exc:                                # noqa: BLE001
            ROWS.append(Row(0, 'section "%s" raised' % label, '-',
                            '%s: %s' % (type(exc).__name__, exc), 'ERROR',
                            'A section that crashes takes its rows with it.',
                            ''))


def _wrap(s, w):
    out, cur = [], ''
    for word in str(s).split():
        if len(cur) + len(word) + 1 > w:
            out.append(cur)
            cur = word
        else:
            cur = (cur + ' ' + word).strip()
    if cur:
        out.append(cur)
    return out


def report(verbose=False):
    npass = sum(r.status == 'PASS' for r in ROWS)
    nfail = sum(r.status == 'FAIL' for r in ROWS)
    ninfo = sum(r.status == 'INFO' for r in ROWS)
    nerr = sum(r.status == 'ERROR' for r in ROWS)
    print('=' * 100)
    print('%-4s %-56s %15s %15s %7s' % ('tier', 'row', 'expected', 'measured',
                                        'status'))
    print('-' * 100)
    for r in ROWS:
        print('%-4s %-56s %15s %15s %7s'
              % (r.tier, r.name[:56],
                 _fmt(r.exp) if r.exp is not None else '-', _fmt(r.got),
                 r.status))
        if verbose or r.status in ('FAIL', 'ERROR'):
            for line in _wrap(r.why, 92):
                print('     ' + line)
    print('=' * 100)
    print('%d pass, %d FAIL, %d info, %d ERROR' % (npass, nfail, ninfo, nerr))
    print('=' * 100)
    return nfail + nerr


def run_bugs():
    import importlib
    mods = {'ice': ICE, 'jet': JET, 'impact': IMP, 'openchannel': OC,
            'thinfilm': TF}
    print('%-28s %-8s %s' % ('defect', 'caught', 'rows that fired'))
    print('-' * 100)
    missed = []
    for name, (apply_fn, modname) in sorted(BUGS.items()):
        for m in mods.values():
            importlib.reload(m)
        apply_fn(mods[modname])
        run_suite()
        fired = [r.name for r in ROWS if r.status in ('FAIL', 'ERROR')]
        print('%-28s %-8s %s' % (name, 'yes' if fired else 'NO',
                                 '; '.join(f[:40] for f in fired[:2])
                                 or '** nothing fired **'))
        if not fired:
            missed.append(name)
    for m in mods.values():
        importlib.reload(m)
    print('-' * 100)
    print('%d of %d defects caught' % (len(BUGS) - len(missed), len(BUGS)))
    return len(missed)


if __name__ == '__main__':
    if '--bugs' in sys.argv:
        raise SystemExit(run_bugs())
    run_suite()
    raise SystemExit(report('-v' in sys.argv))
