"""Every number the chapter's five-axes section quotes, re-derived from the code.

    python3 validate_chapter.py         # exits non-zero if the prose has drifted
    python3 validate_chapter.py -v      # print every row, not just the failures
    python3 validate_chapter.py --bugs  # prove the rows can fail

WHY THIS FILE EXISTS. `make_figures.py` enforces one invariant already -- A
FIGURE CANNOT DRIFT FROM THE CODE THAT SHIPS -- by importing the implementation
instead of restating it. The PROSE had no such guard. A chapter that quotes
`sel = 55.01` and an `ice.py` that later moves to a different temperature will
disagree silently and forever, and the disagreement is invisible in a diff
because neither side looks wrong on its own.

So the numbers below are transcribed from the chapter EXACTLY as printed, to
the digits printed, and compared against a fresh evaluation. This file is
therefore the one place in this skill where a "tolerance" is not a physical
claim: it is the rounding of the printed text, and each row's tolerance is
half a unit in the last quoted digit. Widening one hides a drift rather than a
measurement error -- which is the specific thing it exists to prevent.

⚠️ WHAT THIS DOES NOT CHECK. That the physics is right; `validate_phases.py`
does that, against closed forms and published values. This file only checks
that the chapter says what the code computes. Both are needed and neither
substitutes for the other: prose can faithfully quote a wrong number, and
correct code can be described by stale prose.
"""
import sys

import numpy as np

import ice as ICE                                               # noqa: E402
import impact as IMP                                            # noqa: E402
import jet as JET                                               # noqa: E402
import openchannel as OC                                        # noqa: E402
import thinfilm as TF                                           # noqa: E402
import vortex as VTX                                            # noqa: E402

CHAPTER = '../references/12-water-physics.md'
SECTION = 'Six axes the rest of this chapter is a point on'

ROWS = []
BUGS = {}


def quoted(label, printed, value):
    """One quoted number, with its tolerance taken FROM ITS OWN LAST DIGIT.

    `printed` is the string as it appears in the chapter. The tolerance is half
    a unit in its last significant place, which is the largest disagreement
    that rounding alone can explain -- so anything this catches is a real
    divergence between the text and the code, not a display artefact.
    """
    s = printed.strip().replace(' ', '')
    if 'e' in s or 'E' in s:
        mant, _, ex = s.lower().partition('e')
        dec = len(mant.partition('.')[2])
        half = 0.5 * 10.0 ** (-dec) * 10.0 ** float(ex)
    elif '.' in s:
        half = 0.5 * 10.0 ** (-len(s.partition('.')[2]))
    else:
        # An integer as printed: trailing zeros are not significant, so the
        # last NON-zero digit sets the place. "560 000" is quoted to 3 figures
        # and must not be held to a unit.
        t = s.rstrip('0')
        half = 0.5 * 10.0 ** (len(s) - len(t)) if t else 0.5 * 10.0 ** len(s)
    got = float(value)
    exp = float(s)
    ok = abs(got - exp) <= half * (1.0 + 1e-9)
    ROWS.append((label, printed, got, half, ok))
    return ok


# --- the phase axis: ice -----------------------------------------------------
def _ice():
    cw = ICE.compare_with_water()
    quoted('ice F0 at n = 1.3110', '0.01811', ICE.fresnel_normal(1.3110))
    quoted('water F0 at n = 1.334', '0.02048', ICE.fresnel_normal(1.334))
    quoted('ice critical angle, deg', '49.71',
           np.degrees(ICE.critical_angle(1.3110)))
    quoted('water critical angle, deg', '48.56',
           np.degrees(ICE.critical_angle(1.334)))
    for i, p in enumerate(('0.14194', '0.05230', '0.00258')):
        quoted('a_ice channel %d, 1/m' % i, p, ICE.ABS_ICE[i])
    for i, p in enumerate(('1.84', '1.01', '3.96')):
        quoted('water:ice ratio channel %d' % i, p,
               cw['ratio_water_over_ice'][i])
    quoted('red:blue selectivity, ice', '55.01', cw['sel_ice'])
    quoted('red:blue selectivity, water', '25.61', cw['sel_water'])
    quoted('selectivity ratio ice/water', '2.148',
           cw['sel_ice'] / cw['sel_water'])
    # The bubble-density table, at the chapter's own 0.5 mm bubbles.
    for name, nd, s_p, r_p in (
            ('lake ice', 2e6, '3.14', ('0.741', '0.833', '0.960')),
            ('glacier', 5e8, '785', ('0.981', '0.989', '0.997')),
            ('firn', 2e10, '3.14e4', ('0.997', '0.998', '1.000'))):
        S = ICE.bubble_scattering(0.5e-3, nd)
        quoted('S, %s, 1/m' % name, s_p, S)
        R = ICE.km_reflectance_infinite(ICE.ABS_ICE, S)
        for i, p in enumerate(r_p):
            quoted('R_inf %s channel %d' % (name, i), p, R[i])
    pa = ICE.path_amplification(ICE.ABS_ICE, ICE.bubble_scattering(0.5e-3, 5e8))
    quoted('path amplification, glacier red', '104', pa[0])
    quoted('path amplification, glacier blue', '779', pa[2])


# --- the Weber axis: free jets ----------------------------------------------
def _jet():
    for name, u, d, p in (('slow trickle', 0.6, 4.0e-3, '0.024'),
                          ('water pistol', 8.0, 1.5e-3, '1.59'),
                          ('fog nozzle', 35.0, 1.0e-3, '20.3'),
                          ('garden hose', 12.0, 12e-3, '28.6'),
                          ('fountain jet', 9.0, 25e-3, '33.5'),
                          ('fire hose', 30.0, 29e-3, '432')):
        quoted('We_g, %s' % name, p, JET.weber_aero(u, d))
    quoted('Rayleigh drop D/d', '1.891', JET.rayleigh_drop_diameter(1.0))
    quoted('trickle intact length, L/d', '44.4',
           JET.breakup_length_rayleigh(0.6, 4e-3) / 4e-3)
    quoted('rho_water / rho_air', '829', JET.RHO_W / JET.RHO_A)
    quoted('Stokes number, 1 mm drop', '92', JET.stokes_number(1e-3, 30, 1.0))
    quoted('Stokes number, 50 um drop', '0.23',
           JET.stokes_number(50e-6, 30, 1.0))


# --- the impulse axis: water entry ------------------------------------------
def _impact():
    for name, d, u, fr, we, tp, hp in (
            ('falling raindrop', 2.5e-3, 7.0, '1999', '1680', '31.9', '0.056'),
            ('pebble', 20e-3, 5.0, '127', '6856', '90.3', '0.113'),
            ('rock', 0.12, 8.0, '54.4', '105300', '221', '0.442'),
            ('body', 0.35, 6.0, '10.5', '172800', '378', '0.567')):
        quoted('Fr, %s' % name, fr, IMP.froude_impact(u, d))
        quoted('We, %s' % name, we, IMP.weber_impact(u, d))
        quoted('pinch-off time, %s, ms' % name, tp,
               1e3 * IMP.cavity_pinchoff_time(d, u))
        quoted('pinch-off depth, %s, m' % name, hp,
               IMP.cavity_pinchoff_depth(d, u))
    quoted('Fr of the 2.5 mm drip at 1 m/s', '41',
           IMP.froude_impact(1.0, 2.5e-3))
    quoted('crown radius at 10 ms, m', '0.098', IMP.crown_radius(0.010, 8, 0.12))
    quoted('crown radius at 40 ms, m', '0.196', IMP.crown_radius(0.040, 8, 0.12))


# --- travelling or standing: the hydraulic jump ------------------------------
def _jump():
    h1 = 0.30
    table = ((1.4, '2.40', '0.463', '1.54', '0.0077', '0.98', '55'),
             (2.0, '3.43', '0.712', '2.37', '0.082', '2.47', '823'),
             (3.5, '6.00', '1.342', '4.47', '0.703', '6.25', '12400'),
             (6.0, '10.29', '2.400', '8.00', '3.216', '12.60', '97200'),
             (10.0, '17.15', '4.095', '13.65', '11.124', '22.77', '560000'))
    for fr1, u_p, h2_p, rat_p, de_p, l_p, pw_p in table:
        u = fr1 * np.sqrt(9.80665 * h1)
        h2 = OC.conjugate_depth(h1, fr1)
        tag = 'jump Fr=%.1f' % fr1
        quoted('%s upstream speed, m/s' % tag, u_p, u)
        quoted('%s conjugate depth, m' % tag, h2_p, h2)
        quoted('%s depth ratio' % tag, rat_p, h2 / h1)
        quoted('%s head loss, m' % tag, de_p, OC.energy_loss(h1, h2))
        quoted('%s roller length, m' % tag, l_p, OC.roller_length(h1, h2))
        quoted('%s power, W/m' % tag, pw_p, OC.aeration_rate(h1, h2, u * h1))


# --- interference: thin films ------------------------------------------------
def _film():
    for d_nm, f_p, e_p in ((100, '0.30', '0.0073'), (200, '0.61', '0.0221'),
                           (400, '1.22', '0.0572'), (800, '2.44', '0.2568')):
        err, fringes = TF.rgb_aliasing_error(d_nm * 1e-9, 0.8)
        quoted('fringes across the band, %d nm film' % d_nm, f_p, fringes)
        quoted('3-sample RGB error, %d nm film' % d_nm, e_p, err)
    ct = TF.snell_cos(1.0, TF.N_OIL, 0.8)
    quoted('fringe spacing at 550 nm, 800 nm film', '141',
           TF.fringe_spacing_nm(TF.N_OIL, 800e-9, ct, 550e-9) * 1e9)
    lam = np.linspace(380e-9, 730e-9, 3000)
    for cos_i, lam_p, r_p in ((1.0, '470', '0.056'), (0.34, '603', '0.199')):
        r = TF.airy_reflectance(lam, 400e-9, cos_i)
        quoted('peak wavelength at cos=%.2f, nm' % cos_i, lam_p,
               lam[r.argmax()] * 1e9)
        quoted('peak reflectance at cos=%.2f' % cos_i, r_p, r.max())


# --- the frame axis: vortices ------------------------------------------------
def _vortex():
    a, om = 0.02, 20.0
    gam = VTX.circulation_from_core_rate(om, a)
    quoted('circulation of the worked core, m2/s', '0.0503', gam)
    quoted('peak swirl of the worked core, m/s', '0.40',
           VTX.rankine_velocity(a, a, gam))
    quoted('total dip depth, mm', '16.3', 1e3 * VTX.rankine_depth(a, gam))
    quoted('half the dip, mm', '8.2', 0.5e3 * VTX.rankine_depth(a, gam))
    quoted('depth ratio for a 1000x smaller core', '1000000',
           VTX.rankine_depth(a / 1000.0, gam) / VTX.rankine_depth(a, gam))
    quoted('capillary length, mm', '2.73', 1e3 * VTX.capillary_length())
    omega_12rpm = 2.0 * np.pi * 12.0 / 60.0
    quoted('Ekman layer depth at 12 rpm, mm', '0.89',
           1e3 * VTX.ekman_layer_depth(omega_12rpm))
    quoted('Ekman number at L = 0.2 m, 12 rpm', '1.0e-5',
           VTX.ekman_number(omega_12rpm, 0.2))
    for name, u, d, re_p, f_p in (
            ('silt grain', 0.02, 0.002, '40', None),
            ('reed', 0.4, 0.008, '3190', '10'),
            ('boulder', 1.5, 0.30, '4.5e5', '1.0'),
            ('bridge pier', 2.0, 1.2, '2.4e6', '0.33')):
        quoted('Re, %s' % name, re_p, VTX.reynolds(u, d))
        if f_p is not None:
            quoted('shedding frequency, %s, Hz' % name, f_p,
                   VTX.shedding_frequency(u, d))
    quoted('shedding onset Reynolds number', '47', VTX.RE_SHEDDING_ONSET)
    quoted('mode-A boundary', '180', VTX.RE_MODE_A)
    quoted('shear-layer boundary', '1300', VTX.RE_SHEAR_LAYER)
    quoted('St read at Re = 1000', '0.212', VTX.ST_AT_RE_ANCHOR)
    quoted('universal wake St', '0.176', VTX.ST_WAKE_UNIVERSAL)


SECTIONS = ((_ice, 'the phase axis: ice'),
            (_jet, 'the Weber axis: free jets'),
            (_impact, 'the impulse axis: water entry'),
            (_jump, 'travelling or standing: the hydraulic jump'),
            (_film, 'interference: thin films'),
            (_vortex, 'the frame axis: vortices'))


# --- the harness's own guard -------------------------------------------------
# ⚠️ SIX DELIBERATE DRIFTS, one per section plus one on the tolerance rule
# itself. A file whose whole job is to notice a disagreement is worthless until
# it has been SEEN to notice one, and the sixth case is the one that matters
# most: it perturbs a value by less than the last quoted digit, and the run is
# only correct if that case does NOT fire.
def _bugs():
    saved = {}

    def run(name, apply, undo, expect=True):
        apply()
        del ROWS[:]
        for fn, _ in SECTIONS:
            fn()
        fired = [r for r in ROWS if not r[4]]
        undo()
        good = bool(fired) == expect
        if expect:
            verdict = 'caught' if fired else 'MISSED'
        else:
            verdict = 'fired' if fired else 'quiet'
        print('  %-36s %-7s %s' % (
            name, verdict,
            'ok' if good else '<-- the harness is blind here'))
        return good

    allgood = True
    saved['sel'] = ICE.ABS_ICE.copy()
    allgood &= run('ice absorption +2% in red',
                   lambda: ICE.ABS_ICE.__setitem__(0, saved['sel'][0] * 1.02),
                   lambda: ICE.ABS_ICE.__setitem__(0, saved['sel'][0]))
    saved['rho_a'] = JET.RHO_A
    allgood &= run('air density read as 1.225',
                   lambda: setattr(JET, 'RHO_A', 1.225),
                   lambda: setattr(JET, 'RHO_A', saved['rho_a']))
    # ⚠️ NOT `setattr(IMP, 'G', 9.81)`, AND THE REASON IS WORTH KEEPING.
    # `impact.py` writes `def cavity_pinchoff_time(d, u, g=G, ...)`, so `G` is
    # captured as a DEFAULT ARGUMENT at definition time. Reassigning the module
    # attribute afterwards changes nothing that any caller sees, and the naive
    # perturbation sails straight through -- which this harness printed as
    # "MISSED" on its first run. A perturbation that cannot reach the code
    # under test proves the rows are guarded when they are not, so the case
    # patches the function instead. The same applies to `jet.py`, `ice.py` and
    # `openchannel.py`: every `X=CONST` default in this package is immune to
    # module-level reassignment, and anything testing them must go through the
    # function or the argument.
    saved['tp'] = IMP.cavity_pinchoff_time
    allgood &= run('pinch-off constant C 2.0 -> 2.05',
                   lambda: setattr(IMP, 'cavity_pinchoff_time',
                                   lambda d, u, g=IMP.G, c=2.05:
                                   saved['tp'](d, u, g, c)),
                   lambda: setattr(IMP, 'cavity_pinchoff_time', saved['tp']))
    saved['roller'] = OC.roller_length
    allgood &= run('roller constant 6 -> 5.5',
                   lambda: setattr(OC, 'roller_length',
                                   lambda a, b, c=5.5: saved['roller'](a, b, c)),
                   lambda: setattr(OC, 'roller_length', saved['roller']))
    saved['core'] = VTX.rankine_depth
    allgood &= run('vortex depth off by 1 %',
                   lambda: setattr(VTX, 'rankine_depth',
                                   lambda a_, g_, g=VTX.G:
                                   saved['core'](a_, g_, g) * 1.01),
                   lambda: setattr(VTX, 'rankine_depth', saved['core']))
    saved['n_oil'] = TF.N_OIL
    allgood &= run('film index 1.47 -> 1.48',
                   lambda: setattr(TF, 'N_OIL', 1.48),
                   lambda: setattr(TF, 'N_OIL', saved['n_oil']))
    # The control: a perturbation SMALLER than the last quoted digit must NOT
    # fire, or every row here is really a tolerance of "whatever I typed".
    saved['tp2'] = IMP.cavity_pinchoff_time
    allgood &= run('C nudged by 1e-9 (must NOT fire)',
                   lambda: setattr(IMP, 'cavity_pinchoff_time',
                                   lambda d, u, g=IMP.G, c=2.0 + 1e-9:
                                   saved['tp2'](d, u, g, c)),
                   lambda: setattr(IMP, 'cavity_pinchoff_time', saved['tp2']),
                   expect=False)
    return 0 if allgood else 1


def main(argv):
    if '--bugs' in argv:
        print('proving the chapter check can fail:')
        return _bugs()
    verbose = '-v' in argv
    print('%-46s %-12s %-14s' % ('chapter says', 'printed', 'code gives'))
    print('-' * 92)
    bad = 0
    for fn, title in SECTIONS:
        start = len(ROWS)
        fn()
        rows = ROWS[start:]
        n_bad = sum(0 if r[4] else 1 for r in rows)
        bad += n_bad
        if verbose or n_bad:
            print('-- %s' % title)
            for label, printed, got, half, ok in rows:
                if ok and not verbose:
                    continue
                print('%-46s %-12s %-14.6g %s' % (
                    label[:46], printed, got,
                    'ok' if ok else 'DRIFTED (tolerance %.3g)' % half))
    print('-' * 92)
    print('%d numbers quoted in "%s"' % (len(ROWS), SECTION))
    print('%d match the code, %d DRIFTED' % (len(ROWS) - bad, bad))
    if bad:
        print('\nThe chapter and the implementation disagree. Fix the PROSE if '
              'the code moved\ndeliberately; fix the CODE if it did not. Do not '
              'widen a tolerance here -- they\nare the printed digits, not a '
              'measurement error.')
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
