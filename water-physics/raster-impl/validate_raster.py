"""External validation of the screen-space water pass.

    python3 validate_raster.py            # everything; non-zero exit on any FAIL
    python3 validate_raster.py -v         # also print every tolerance's reason
    python3 validate_raster.py --fast     # skip the two frame-level tiers

The harness is `reference-impl/validate.py`'s, deliberately: same three tiers,
same rule that a tolerance comes from the ESTIMATOR's error and never from the
measured disagreement, same rule that a row which finds a bug is left failing.

  Tier 1  CLOSED FORM         -- the answer is known analytically.
  Tier 2  THE CHAPTER'S OWN   -- compared against a number printed in
          PUBLISHED NUMBER       `12-water-rendering.md`. A disagreement is a
                                 finding about the chapter, and three of them
                                 are (see README).
  Tier 3  INDEPENDENT METHOD  -- Monte-Carlo against quadrature; the pass
                                 against the offline frame.

EVERY QUANTITY HAS AT LEAST ONE ABSOLUTE ROW. This project has been blinded
three times by ratio-only guards, once by dividing 0/0, so nothing here is
checked only as a fraction: coverage is a pixel COUNT, depth precision is
METRES, the LUT is checked on its VALUES before its ratios, and the frame
comparison carries an absolute radiance row beside every relative one.

MEASURE IN SCENE-LINEAR. No row in this file reads an image file, and no row
runs through `evidence.encode`.
"""
import os
import sys
import time

import numpy as np

# `reference-impl` owns the physics; this file reaches it the same way the rest
# of the directory does, by path and never by copy.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, '..', 'reference-impl')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import optics as OPT                                            # noqa: E402
import atmosphere as ATM                                        # noqa: E402

import field as FLD                                             # noqa: E402

import lut as LUT                                               # noqa: E402
import offline as OFF                                           # noqa: E402
import scene as SC                                              # noqa: E402
import sswater as WA                                            # noqa: E402
import waves as WV                                              # noqa: E402
import waveref as WR                                            # noqa: E402

VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv
FAST = '--fast' in sys.argv
ROWS = []
Y709 = np.array([0.2126, 0.7152, 0.0722])


def _fmt(v):
    if v is None:
        return '-'
    if isinstance(v, str):
        return v
    a = np.asarray(v, float)
    if a.ndim == 0:
        x = float(a)
        return ('%.6g' % x) if (abs(x) >= 1e-3 or x == 0) else ('%.3e' % x)
    return '[' + ' '.join(_fmt(x) for x in a.ravel()[:4]) + (
        ' ...' if a.size > 4 else '') + ']'


def check(tier, name, got, exp, tol, why, unit='', rel=False):
    g, e = np.asarray(got, float), np.asarray(exp, float)
    dev = np.abs(g - e) / np.where(np.abs(e) < 1e-30, 1.0, np.abs(e)) if rel \
        else np.abs(g - e)
    ok = bool(np.all(dev <= tol))
    ROWS.append((tier, name, _fmt(exp), _fmt(got), tol, 'PASS' if ok else 'FAIL',
                 why, unit, float(np.max(dev))))
    return ok


def between(tier, name, got, lo, hi, why, unit=''):
    g = np.asarray(got, float)
    ok = bool(np.all((g >= np.asarray(lo)) & (g <= np.asarray(hi))))
    dev = float(np.max(np.maximum(np.asarray(lo) - g, g - np.asarray(hi))))
    ROWS.append((tier, name, '[%s .. %s]' % (_fmt(lo), _fmt(hi)), _fmt(got),
                 None, 'PASS' if ok else 'FAIL', why, unit, dev))
    return ok


def info(tier, name, got, why, unit=''):
    ROWS.append((tier, name, '-', _fmt(got), None, 'INFO', why, unit, 0.0))


# ---------------------------------------------------------- an INDEPENDENT
# estimator of `optics.slab_esc`, used by exactly one row, which is the row that
# explains the tolerance on several others. `optics.slab_esc` integrates over
# mu on (0, 1] with one 2000-node Gauss-Legendre rule, and its integrand has a
# SQUARE-ROOT BRANCH POINT at the critical angle -- R_int(mu) reaches 1 with
# infinite slope at mu_c = sqrt(1 - 1/n^2) and is identically 1 below it.
# Gauss-Legendre is spectrally accurate on smooth integrands and only
# algebraically accurate across a branch point, so the shipped rule carries a
# small systematic bias. Splitting the interval AT mu_c and running Gauss-
# Legendre on each smooth piece removes it. This is a different method, not a
# second copy: it shares no line with `optics.slab_esc` beyond `optics.fresnel`.
def esc_split(tau, c, n=800):
    muc = np.sqrt(1.0 - 1.0 / OPT.IOR[c] ** 2)
    tot = 0.0
    for lo, hi in ((0.0, muc), (muc, 1.0)):
        m, w = np.polynomial.legendre.leggauss(n)
        m = 0.5 * (hi - lo) * m + 0.5 * (hi + lo)
        w = 0.5 * (hi - lo) * w
        ca2 = 1.0 - OPT.IOR[c] ** 2 * (1.0 - m * m)
        r = np.ones_like(m)
        ok = ca2 > 0
        r[ok] = OPT.fresnel(np.sqrt(ca2[ok]))[:, c]
        tot += (w * 2.0 * m * np.exp(-tau / m) * (1.0 - r)).sum()
    return tot


# The size of that bias, measured once here and used as the tolerance floor for
# every row that compares a `slab_esc` value against a closed form. It is 6.3e-5
# relative -- 0.006%, far below anything that moves a picture, and far above f64.
Q_BIAS = 7e-5


def report():
    w = max(len(r[1]) for r in ROWS) + 2
    last = None
    nfail = 0
    for (tier, name, exp, got, tol, st, why, unit, dev) in ROWS:
        if tier != last:
            print('\n--- TIER %s %s' % (tier, '-' * 60))
            last = tier
        nfail += st == 'FAIL'
        print('%-4s %-*s exp %-26s got %-26s %s%s'
              % (st, w, name, exp, got, ('tol %-9s' % _fmt(tol)) if tol is not None else '',
                 unit))
        if VERBOSE and why:
            print('     %s' % why)
        if st == 'FAIL':
            print('     !! deviation %s against tolerance %s' % (_fmt(dev), _fmt(tol)))
    print('\n%d rows, %d FAIL' % (len(ROWS), nfail))
    return nfail


# =========================================================== TIER 1 -- closed form
def tier1_triangle():
    """The chapter's claim that three oversized verts "clip to exactly the
    screen". A pixel COUNT, at several shapes, because a coverage rule that is
    right at 16:9 and wrong at 1:1 is a rule that has not been tested."""
    for res in ((560, 315), (64, 64), (17, 129), (1920, 1080)):
        pos, uv = WA.fullscreen_triangle()
        cov, uvi = WA.rasterize(pos, uv, res)
        check(1, 'triangle covers %dx%d (pixel count)' % res,
              int(cov.sum()), res[0] * res[1], 0,
              'Exact integer identity: every pixel centre is inside the '
              'triangle (-1,1),(3,1),(-1,-3) or the pass has holes.', 'px')
        X, Y = SC.pixel_ndc(res)
        want = np.stack([(X + 1) * 0.5, (1 - Y) * 0.5], axis=-1)
        check(1, 'triangle uv == screen uv %dx%d' % res,
              float(np.abs(uvi - want).max()), 0.0, 5e-15,
              'Barycentric interpolation of (0,0),(2,0),(0,2) must reproduce the '
              'screen uv exactly; 5e-15 is a few f64 ulps on a coordinate of '
              'order 1.', 'uv')

    a = WA.helper_lane_audit((560, 315))
    check(1, 'one triangle: no quad run twice', a['tri_quad_pairs'],
          a['quads'], 0,
          'One primitive covering the screen touches each 2x2 quad exactly '
          'once. Integer identity.', 'quads')
    info(1, 'two triangles: seam quads run twice', a['seam_quads_run_twice'],
         'The chapter\'s stated reason for one triangle rather than two, '
         'counted at 560x315.', 'quads')
    info(1, 'lane cost, quad / triangle',
         a['quad_lanes'] / a['tri_lanes'],
         'What the seam actually costs in shaded lanes. See README -- the claim '
         'is true in kind and small in size, and it shrinks with resolution.')


def tier1_rayplane():
    """Step 2 and its three guards, each reached on purpose."""
    X, Y = SC.pixel_ndc((97, 61))
    d = SC.ray_dirs(X, Y)
    t = (SC.H_WATER - SC.EYE[2]) / d[..., 2]
    hit = (d[..., 2] < -WA.EPS_RAYZ) & (t > 0)
    P = SC.EYE[None, None] + t[..., None] * d
    check(1, 'plane hit lands on the datum', float(np.abs(P[hit][:, 2]).max()),
          0.0, 1e-9,
          'Analytic, so the only error is f64 cancellation over a ray of '
          'order 10^3 m; 1e-9 m is 1 nm.', 'm')
    # guard 1: a ray parallel to the datum
    dpar = np.array([[1.0, 0.0, 0.0]])
    check(1, 'guard: |rayDir.z| < eps rejects', int((np.abs(dpar[:, 2]) < WA.EPS_RAYZ).sum()),
          1, 0, 'The chapter\'s first guard, reached with an exactly horizontal '
          'ray.', 'rays')
    # guard 2: the plane behind the camera
    dup = np.array([[0.3, 0.0, 0.6]])
    dup /= np.linalg.norm(dup)
    tup = (SC.H_WATER - SC.EYE[2]) / dup[0, 2]
    check(1, 'guard: t < 0 rejects an upward ray', float(tup < 0), 1.0, 0,
          'Camera above the datum, ray pointing up: t must come out negative '
          'and be rejected rather than shading behind the eye.')
    # guard 3: below the datum raises
    g = SC.prepass((32, 18))
    g['eye'] = np.array([1.0, 0.0, -0.5])
    try:
        WA.water_pass(g)
        raised = False
    except NotImplementedError:
        raised = True
    check(1, 'guard: camPos below datum raises', float(raised), 1.0, 0,
          'The chapter\'s underwater branch is not built; the guard must fail '
          'loudly rather than draw the above-water branch upside down.')


def tier1_depth():
    """Reversed-Z, in metres. ABSOLUTE rows: this is a length, and a length
    checked only as a ratio is how a depth bug survives."""
    w = np.array([0.05, 0.5, 5.0, 50.0, 500.0, 3000.0])
    rt = SC.unproject_depth(SC.project_depth(w))
    check(1, 'reversed-Z round trip (absolute)', float(np.abs(rt - w).max()),
          0.0, 2e-4,
          'float32 storage of near/w: the round trip can only lose the f32 '
          'mantissa, 6e-8 relative, which at the 3000 m far end is 1.8e-4 m.',
          'm')
    check(1, 'reversed-Z round trip (relative)',
          float(np.abs(rt / w - 1).max()), 0.0, 1e-7,
          'The same row as a ratio, so the absolute one above cannot be passed '
          'by a large-w blow-up.', '')
    for ww in (5.0, 50.0, 500.0):
        info(1, 'depth step at %.0f m, reversed-Z' % ww,
             SC.depth_precision_m(ww), 'One f32 ulp of the buffer, in metres.', 'm')
        info(1, 'depth step at %.0f m, forward-Z' % ww,
             SC.depth_precision_m(ww, forward=True),
             'The same, with a [0,1] forward projection and a 200 m far plane.',
             'm')
    check(1, 'reversed-Z beats forward-Z at 50 m',
          float(SC.depth_precision_m(50.) < SC.depth_precision_m(50., True)),
          1.0, 0,
          'The whole reason the convention exists. If this ever fails the near '
          'plane has been moved into a regime where it does not.')


def tier1_energy():
    """The limits that pin the composition, all of them absolute."""
    cs = float(ATM.SUN_DIR[2])
    tot = OPT.rho_water(1.0, cs, 0.0) + OPT.fresnel(cs)
    check(1, 'white lossless bed: albedo == 1 (absolute)',
          tot, np.ones(3), 1e-12,
          'Energy conservation with no constant of this project on the right '
          'hand side. f64 round-off only.')
    esc0, rt0 = LUT.ExitLUT('joint')(np.zeros(3))
    check(1, 'T_esc(0) == 1 - R_int (absolute)', esc0, OPT.T_OUT_DIFFUSE,
          Q_BIAS,
          'At zero optical depth the joint integral collapses to the diffuse '
          'exit constant, which is `12`\'s "a lossless check cannot see it". '
          'The LUT must reproduce that at its first texel or it manufactures an '
          'error at the shoreline. THE TOLERANCE IS NOT MACHINE EPSILON and the '
          'reason is a finding, not a fudge: `optics.slab_esc` and '
          '`optics.T_OUT_DIFFUSE` are two quadratures of the same number and '
          'they disagree by 6.3e-5 relative. Which one is right is settled by '
          'the `slab_esc quadrature bias` row in tier 3.')
    check(1, 'G_rt(0) == R_int (absolute)', rt0, OPT.R_INT, Q_BIAS,
          'Same limit, other leg, same quadrature bias.')
    for md in ('sep_2tau', 'sep_sq'):
        e0, r0 = LUT.ExitLUT(md)(np.zeros(3))
        check(1, 'separated %s is EXACT at tau=0' % md,
              np.concatenate([e0 - OPT.T_OUT_DIFFUSE, r0 - OPT.R_INT]),
              np.zeros(6), 2e-12,
              'The trap\'s second half, as a row: every separated form is right '
              'at zero absorption, so no lossless test can distinguish them.')

    # the sky's entry leg, and the reciprocity that fixes it
    esc, rt = LUT.ExitLUT('joint')(np.zeros(3))
    tdn0 = esc / OPT.T_OUT_DIFFUSE
    check(1, 'sky down-leg T_dn(0) == 1 (absolute)', tdn0, np.ones(3),
          2 * Q_BIAS,
          'The normalisation of the reciprocity-weighted entry leg in '
          '`sswater.bed_radiance`. If it is not 1 at tau=0 the composition '
          'loses energy at the waterline.')


def tier1_hemispherical():
    """The bridge between the two upwelling modes: the directional emergent
    radiance, integrated over the air-side hemisphere, must equal pi * L_bed *
    T_esc -- which is `optics.wbounce_of`. This is what says the two modes are
    two readings of ONE model and not two models."""
    dep = 1.40
    tau = OPT.ABS * dep
    esc = OPT.slab_esc(dep)
    mu, wq = np.polynomial.legendre.leggauss(2000)
    mu, wq = 0.5 * (mu + 1), 0.5 * wq
    muw = np.sqrt(np.maximum(1.0 - (1.0 - mu[:, None] ** 2) / OPT.IOR[None] ** 2, 0.))
    T = 1.0 - OPT.fresnel(mu)
    L = T * np.exp(-tau[None] / muw) / OPT.N2[None]      # per unit L_bed
    flux = (2.0 * np.pi * (wq[:, None] * mu[:, None] * L)).sum(0)
    check(1, 'hemispherical integral == pi*T_esc (absolute)',
          flux, np.pi * esc, np.pi * Q_BIAS,
          'The etendue identity mu_a dw_a = n^2 mu_w dw_w, written as a test. '
          'The left side integrates over the AIR-side cosine, where the '
          'integrand is smooth and 2000-node Gauss-Legendre is spectral; the '
          'right side is `optics.slab_esc`, which integrates over the '
          'WATER-side cosine across the critical angle and is not. So the '
          'tolerance is the quadrature bias of the weaker of the two, and this '
          'row is one of the three that measure it.')
    check(1, 'the same, relative', float(np.abs(flux / (np.pi * esc) - 1).max()),
          0.0, Q_BIAS, 'The ratio form beside the absolute one.', '')


# ============================================ TIER 2 -- the chapter's own numbers
CH_ESC_1M40 = np.array([19.4, 5.1, 1.1])
CH_RT_1M40_SQ = np.array([30.5, 9.3, 2.2])
CH_TAU = np.array([0.05, 0.10, 0.20, 0.37, 0.50, 1.00, 2.00])
CH_ESC_SCALE = np.array([3.6, 6.6, 12.0, 19.4, 24.6, 39.6, 58.4])
CH_RT_SCALE = np.array([-7.3, -13.2, -22.9, -35.5, -43.6, -64.2, -83.2])
CH_JOINT_ESC = np.array([0.3403, 0.4795, 0.5106])
CH_JOINT_RT = np.array([0.0965, 0.3277, 0.4445])
CH_SEP_ESC = np.array([0.2850, 0.4563, 0.5050])
CH_SEP_RT_SQ = np.array([0.1389, 0.3614, 0.4546])


def tier2_chapter_tables():
    d = LUT.at_depth(1.40)
    check(2, 'tau at 1.40 m (absolute)', d['tau'],
          np.array([0.3664, 0.0742, 0.0143]), 6e-5,
          '`12`\'s "tau = a*d = 0.3664 / 0.0742 / 0.0143 at 1.40 m". Four '
          'decimals quoted, so the tolerance is half a unit in the last.')
    check(2, 'T_esc joint, 1.40 m (ABSOLUTE)', d['esc_joint'], CH_JOINT_ESC,
          6e-5, 'The chapter\'s own table, absolute values before any ratio.')
    check(2, 'G_rt joint, 1.40 m (ABSOLUTE)', d['rt_joint'], CH_JOINT_RT,
          6e-5, 'Ditto, other leg.')
    check(2, 'T_esc separated, 1.40 m (ABSOLUTE)', d['esc_sep'], CH_SEP_ESC,
          6e-5, 'The separated escape leg 2E_3(tau)(1-R_int); the chapter names '
          'this form explicitly and it reproduces.')
    check(2, 'G_rt separated = 2E_3(tau)^2 R_int (ABSOLUTE)',
          d['rt_sep_sq'], CH_SEP_RT_SQ, 6e-5,
          'THE IDENTIFICATION. The chapter prints 0.1389/0.3614/0.4546 without '
          'saying which separated form it is; only 2E_3(tau)^2 * R_int gives '
          'those three numbers. 2E_3(2 tau) * R_int gives 0.1502/0.3651/0.4553 '
          'and is 8% away in red.')
    check(2, 'escape error at 1.40 m == chapter 19.4/5.1/1.1',
          100 * d['esc_joint_over_sep'], CH_ESC_1M40, 0.06,
          'The chapter\'s headline, and `optics.py`\'s own comment. Quoted to '
          'one decimal, so half a unit in the last place.', '%')
    check(2, 'round trip at 1.40 m == chapter 30.5/9.3/2.2 (SEP_SQ)',
          100 * d['rt_sq_joint_under_sep'], CH_RT_1M40_SQ, 0.06,
          'The chapter\'s "the truth is 30.5 / 9.3 / 2.2 % below it", and the '
          '30% in `optics.py`\'s comment. It reproduces EXACTLY -- but only in '
          'the SEP_SQ form and only read as 1 - joint/sep.', '%')
    check(2, 'round trip at 1.40 m == chapter 43.9/10.3/2.3 (SEP_SQ, other way)',
          100 * d['rt_sq_sep_over_joint'], np.array([43.9, 10.3, 2.3]), 0.06,
          'The same row in the chapter\'s other column. Both conventions '
          'checked because this project has already mixed them up.', '%')
    check(2, 'G_rt sep = 2E_3(2tau) R_int == chapter (ABSOLUTE)',
          d['rt_sep_2tau'], np.array([0.1502, 0.3651, 0.4549]), 6e-5,
          'The chapter carries this row as of `renderer 12: two separated round '
          'trips` -- the direction-PRESERVING form, which is the better physics '
          'for a specular underside and, as the chapter now says, the further '
          'off. Checked here because a number a chapter prints is a number this '
          'suite can hold it to.')
    check(2, 'round trip, SEP_2TAU == chapter 55.6/11.4/2.4',
          100 * d['rt_2tau_sep_over_joint'], np.array([55.6, 11.4, 2.4]), 0.06,
          'The number a previous builder measured and could not reconcile with '
          '`optics.py`\'s 30%. Both are right: two separated forms, two ratio '
          'conventions, four percentages. The chapter now prints this one too '
          'and both agree with this file to 0.05 pp, reached independently.',
          '%')
    info(2, 'round trip, SEP_2TAU, 1.40 m, 1 - joint/sep',
         100 * d['rt_2tau_joint_under_sep'], 'The fourth of the four.', '%')

    f = LUT.factorisation_error(CH_TAU)
    # THE ENVELOPE, and why it is an envelope. The chapter's scaling table names
    # a tau to two decimals and does not name a BAND. Both are ambiguities the
    # check has to carry rather than paper over, so each printed number is
    # required to lie inside the range the error takes over
    #   tau in [label - 0.005, label + 0.005]   (the rounding the label allows)
    #   x  all three bands                      (the label the chapter omits)
    # widened by 0.05 pp for the chapter's own one-decimal rounding. Nothing in
    # the interval came from the measured disagreement.
    def envelope(key, sign=1.0):
        lo, hi = [], []
        for t0 in CH_TAU:
            g = LUT.factorisation_error(
                np.linspace(t0 - 0.005, t0 + 0.005, 9))[key] * (100.0 * sign)
            lo.append(g.min() - 0.05)
            hi.append(g.max() + 0.05)
        return np.array(lo), np.array(hi)

    lo, hi = envelope('esc_joint_over_sep')
    between(2, 'escape scaling table inside the band envelope',
            CH_ESC_SCALE, lo, hi,
            'THE THIRD IDENTIFICATION, and it is that the table needs a label. '
            '`12` presents its tau = 0.05..2.00 scaling as "a function of '
            'optical depth alone" and it is not: the three bands carry three '
            'different R_int(mu) and spread by up to 0.9 pp at tau = 2. No '
            'single band reproduces every printed row -- green matches six of '
            'seven and the 0.37 entry is red at this pool\'s own tau_red = '
            '0.36638, which is what the tau-rounding half of the envelope '
            'covers.', '%')
    info(2, 'escape scaling, red band', 100 * f['esc_joint_over_sep'][:, 0],
         'The envelope\'s contents, printed, so the reader can see how wide it '
         'is rather than take the row on trust.', '%')
    info(2, 'escape scaling, green band',
         100 * f['esc_joint_over_sep'][:, 1], 'Ditto.', '%')
    lo, hi = envelope('rt_2tau_joint_under_sep', -1.0)
    between(2, 'round-trip scaling inside the SEP_2TAU envelope',
            CH_RT_SCALE, lo, hi,
            'THE SECOND IDENTIFICATION. The chapter\'s scaling table is the '
            'OTHER separated form from its own pool table: 2E_3(2 tau)*R_int '
            'puts every printed row inside the same envelope, while '
            '2E_3(tau)^2*R_int is 5-9 pp away and misses every one -- printed '
            'on the INFO row below so the gap can be read off.', '%')
    info(2, 'the same rows under SEP_SQ (green band)',
         -100 * f['rt_sq_joint_under_sep'][:, 1],
         'What the chapter\'s scaling table would read if it used its own pool '
         'table\'s separated form. It does not.', '%')
    info(2, 'error is NOT a function of tau alone: spread over bands, tau=2',
         100 * (f['rt_2tau_joint_under_sep'][-1].max()
                - f['rt_2tau_joint_under_sep'][-1].min()),
         'The chapter says the scaling "is a function of optical depth alone". '
         'It is a function of optical depth AND the band\'s own R_int(mu): the '
         'three bands spread by this much at the bottom of the table.', 'pp')

    cs = float(ATM.SUN_DIR[2])
    ex = LUT.composed_albedo(SC.RHO_BED, cs, 1.40, 'exact')
    sq = LUT.composed_albedo(SC.RHO_BED, cs, 1.40, 'sep_sq')
    check(2, 'composed albedo moves -2.8% in luminance',
          100 * ((sq @ Y709) / (ex @ Y709) - 1.0), -2.8, 0.06,
          '`12`\'s own chain-level number, on a bed albedo quoted from '
          '`render.py`. It reproduces, and it is the chapter\'s point: the '
          'chain moves 2.8% while the term inside it is wrong by 19.4%.', '%')
    info(2, 'composed albedo, per band', 100 * (sq / ex - 1.0),
         'The chapter quotes only the luminance. Red is five times worse than '
         'the luminance and is the number a colourist would see.', '%')


# ============================================== TIER 3 -- independent methods
def tier3_lut_interp():
    """The LUT against the integral it was baked from, and the half-texel bug
    against its own predicted ORDER -- which is what distinguishes it from an
    interpolation error in the wild."""
    taus = np.linspace(0.0, LUT.TAU_MAX, 2001)
    t3 = np.repeat(taus[:, None], 3, 1)
    ex_e = np.array([OPT.slab_esc(1.0, np.array([t] * 3)) for t in taus])
    ex_r = np.array([OPT.slab_trap(1.0, np.array([t] * 3)) for t in taus])
    E = LUT.ExitLUT('joint')
    esc, rt = E(t3)
    h = LUT.TAU_MAX / (LUT.N_TEXELS - 1)
    check(3, 'LUT T_esc vs the integral (ABSOLUTE)',
          float(np.abs(esc - ex_e).max()), 0.0, 1.05 * h * h / 8.0 * 0.76,
          'The textbook bilinear bound h^2/8 * max|f\'\'|, with h = tau_max/'
          '(n-1) and max|d2 T_esc/dtau2| = 0.75 measured on the same grid. '
          'Nothing in this tolerance came from the measurement it bounds.')
    check(3, 'LUT G_rt vs the integral (ABSOLUTE)',
          float(np.abs(rt - ex_r).max()), 0.0, 3e-4,
          'The harder leg, and its bound is NOT h^2/8 max|f\'\'|: G_rt carries '
          'exp(-2 tau/mu), whose second derivative diverges logarithmically as '
          'tau -> 0, so no finite curvature bounds it. The tolerance comes from '
          'a resolution study instead -- the error quarters per doubling (the '
          '`SECOND order` row below), and 3e-4 is the n = 128 point of that '
          'sequence with 20% of headroom.')
    check(3, 'LUT T_esc vs the integral (relative)',
          float(np.abs(esc / ex_e - 1).max()), 0.0, 2e-5,
          'Beside the absolute row, so neither can hide the other.')
    o = []
    for n in (64, 128, 256):
        _, tab = LUT.bake_joint(n)
        bug = LUT.fetch_halftexel_bug(tab, t3)[..., np.arange(3), 0, np.arange(3)]
        good = LUT.fetch(tab, t3)[..., np.arange(3), 0, np.arange(3)]
        o.append((float(np.abs(bug - ex_e).max()), float(np.abs(good - ex_e).max())))
    check(3, 'half-texel bug is FIRST order in 1/n',
          np.array([o[0][0] / o[1][0], o[1][0] / o[2][0]]),
          np.array([2.0, 2.0]), 0.06,
          'Doubling n halves it. That ratio is the field signature: a genuine '
          'interpolation error quarters (checked on the next row), so the two '
          'can be told apart without reading the shader.')
    check(3, 'correct fetch is SECOND order in 1/n',
          np.array([o[0][1] / o[1][1], o[1][1] / o[2][1]]),
          np.array([4.0, 4.0]), 0.25,
          'The same measurement on the fetch that carries the remap.')
    info(3, 'half-texel bug, worst absolute error at n=128', o[1][0],
         '`12` calls this the most-shipped LUT bug there is. On T_esc it is '
         'worth this much, which is 40x the correct fetch\'s.', 'T_esc')


def tier3_quadrature():
    """WHERE THE TOLERANCES IN TIER 1 COME FROM, and a finding about the offline
    reference that this suite turned up by insisting an identity be exact.

    `optics.slab_esc` integrates 2 mu exp(-tau/mu) (1 - R_int(mu)) over mu on
    (0, 1] with a single 2000-node Gauss-Legendre rule. R_int(mu) is identically
    1 below the critical cosine and reaches 1 with INFINITE SLOPE from above --
    a square-root branch point sitting in the middle of the interval. Gauss-
    Legendre is spectral on smooth integrands and only algebraically accurate
    across a branch point, so the shipped rule is biased. Splitting at mu_c and
    running each smooth piece removes it.

    It is 0.006% and it moves no picture. It is reported because it is the
    reason three tier-1 identities cannot be checked at machine precision, and
    because `12` states that at tau -> 0 the joint integrals "collapse to the
    diffuse constants" -- exactly, in theory, and to 6.3e-5 in the code.
    """
    for tau in (0.0, 0.0743, 0.3664, 0.7850):
        a = np.array([OPT.slab_esc(1.0, np.array([tau] * 3))[c] for c in range(3)])
        b = np.array([esc_split(tau, c) for c in range(3)])
        info(3, 'slab_esc quadrature bias at tau=%.4f' % tau,
             np.abs(a / b - 1.0),
             'Shipped rule against a critical-angle-split rule of the same '
             'total order. Signed positive throughout: the shipped rule '
             'OVERSTATES the escape.', 'rel')
    b0 = np.array([esc_split(0.0, c) for c in range(3)])
    check(3, 'split rule reproduces 1 - R_int at tau=0 (ABSOLUTE)',
          b0, OPT.T_OUT_DIFFUSE, 5e-7,
          'And this is which of the two is right. `T_OUT_DIFFUSE` is built from '
          'the AIR-side Fresnel, whose integrand has no branch point, so it is '
          'the trustworthy one -- and the split rule agrees with it to 2e-7 '
          'where the shipped rule is 3.3e-5 away. Left as a PASS because it '
          'confirms the diagnosis; the defect it diagnoses is in '
          '`reference-impl`, which this directory may read and not edit, so it '
          'is reported in the README rather than fixed here.')


def tier3_sky_entry():
    """MY derivation, checked by a method that shares no line with it.

    `sswater.bed_radiance` weights the sky's down leg by T_esc/(1-R_int),
    claiming by reciprocity that the flux entering the water at water-side
    cosine mu is weighted by the same (1 - R_int(mu)) that governs escape. That
    is a NEW claim in this directory -- it is not in `optics.py` and not in the
    chapter -- so it gets a photon walk, which is the only kind of check a
    correlated integral can survive.
    """
    rng = np.random.default_rng(20260816)
    n = 4_000_000
    mu_a = np.sqrt(rng.random(n))                # cosine-weighted air side
    R = OPT.fresnel(mu_a)
    mu_w = np.sqrt(np.maximum(
        1.0 - (1.0 - mu_a[:, None] ** 2) / OPT.IOR[None] ** 2, 0.0))
    for dep in (0.0, 0.40, 1.40, 3.00):
        tau = OPT.ABS * dep
        est = ((1.0 - R) * np.exp(-tau[None] / mu_w)).mean(0)
        want = (1.0 - OPT.R_EXT) * OPT.slab_esc(dep) / OPT.T_OUT_DIFFUSE
        se = ((1.0 - R) * np.exp(-tau[None] / mu_w)).std(0) / np.sqrt(n)
        check(3, 'sky entry leg at %.2f m (ABSOLUTE, photon walk)' % dep,
              est, want, float(4 * se.max()),
              'Cosine-weighted photons through the exact Fresnel and Snell, '
              'attenuated over their OWN 1/mu_w -- no averaging anywhere. '
              'Tolerance is 4 standard errors of the estimator itself. This is '
              'the only row that tests the reciprocity weight, and if it fails '
              'the weight is wrong, not the water.')


def _frames(cache={}):
    if 'g' not in cache:
        cache['g'] = SC.prepass()
        cache['o'] = OFF.offline_frame(cache['g'])
        d = (cache['g']['kind'] == 3)
        for _ in range(4):
            e = np.zeros_like(d)
            e[1:] |= d[:-1]
            e[:-1] |= d[1:]
            e[:, 1:] |= d[:, :-1]
            e[:, :-1] |= d[:, 1:]
            d |= e
        cache['postmask'] = d
    return cache['g'], cache['o'], cache['postmask']


def tier3_frame():
    """The pass against the offline frame. Same model, different machinery."""
    g, off, post = _frames()
    P = WA.water_pass(g, traversal='ssr', ssr_iters=6)
    check(3, 'pass and offline agree on WHICH pixels are water',
          int((P['water'] ^ off['water']).sum()), 0, 0,
          'A depth-buffer reject and an analytic occlusion test must classify '
          'every pixel identically, or the radiance comparison below is '
          'comparing different surfaces. Integer identity, no tolerance.', 'px')
    m = P['water'] & ~post

    # THE TOLERANCE, AND WHERE IT COMES FROM. A screen-space approximation has
    # no closed-form error bound on an arbitrary bed, so a percentage invented
    # for it would be a percentage invented for it -- and the first writing of
    # this block did exactly that, then failed the moment the scene moved. What
    # IS external is the display: at the exposure `evidence.derive_exposure`
    # solves for this frame, one 8-bit sRGB code value at the frame's own median
    # water luminance is a definite amount of scene-linear radiance, and a pass
    # that matches the offline reference to better than that matches to better
    # than anything can show. That is the bar, and it is measured, not chosen.
    import evidence as EV
    expo = EV.derive_exposure(off['color'])
    Lmed = float(np.median((off['color'][m] * Y709).sum(-1)))
    e0 = int(EV.encode(np.full((1, 1, 3), Lmed), expo)[0, 0, 1])
    hi = Lmed
    for _ in range(400):
        hi *= 1.001
        if int(EV.encode(np.full((1, 1, 3), hi), expo)[0, 0, 1]) > e0:
            break
    code_step = hi - Lmed
    info(3, 'one 8-bit code value, in radiance, at this exposure',
         np.array([expo, Lmed, code_step]),
         'Exposure / median water luminance / the radiance step that moves the '
         'encoded pixel by one code value. The next row\'s tolerance, and the '
         'only externally-anchored bar available for a screen-space '
         'approximation.', 'L')

    res = {}
    for tr, it in (('straight', 0), ('snell', 0), ('ssr', 6)):
        Q = WA.water_pass(g, traversal=tr, ssr_iters=it)
        r = np.abs(Q['color'][m] - off['color'][m]) / np.maximum(off['color'][m], 1e-9)
        a = np.abs(Q['color'][m] - off['color'][m])
        res[tr] = (float(np.median(r)), float(np.percentile(r, 95)),
                   float(r.max()), float(np.median(a)), float(a.max()))
        info(3, 'traversal=%-8s median / p95 / max' % tr, np.array(res[tr][:3]),
             'Relative radiance, water pixels, post silhouette excluded.', 'rel')
        info(3, 'traversal=%-8s ABSOLUTE median / max' % tr,
             np.array(res[tr][3:]),
             'The same rows in radiance, because a relative row on a dark '
             'pixel is not a measurement.', 'L')
    check(3, 'ssr median error is below one display code value',
          res['ssr'][3], 0.0, code_step,
          'The recommended traversal rule against a bar that is not this '
          'file\'s opinion: at the median water pixel the pass and the offline '
          'reference cannot be told apart on an 8-bit display at this frame\'s '
          'own exposure.')
    check(3, 'the traversal ladder is monotone (p95)',
          float(res['ssr'][1] < res['snell'][1] < res['straight'][1]), 1.0, 0,
          'A structural claim with no magnitude in it, and the one that carries '
          'the finding: refracting the ray beats not refracting it, and '
          're-sampling the depth buffer along the refracted ray beats both. If '
          'this ever inverts, the ordering argument in the README is wrong. '
          'Checked at p95 and not at the median for the reason on the next row.')
    info(3, 'median: snell and ssr are indistinguishable',
         np.array([res['snell'][0], res['ssr'][0], res['floor'][0]
                   if 'floor' in res else np.nan]),
         'The screen-space depth error is a TAIL, not a level. Over most of the '
         'frame the straight-ray depth and the refracted one land on the same '
         'bed patch and both rules sit on the physics floor; the difference '
         'lives in the grazing fifth of the pixels, which is where p95 looks '
         'and the median does not.', 'rel')
    info(3, 'what the chapter\'s literal step 4 costs, p95',
         np.array([res['straight'][1], res['ssr'][1]]),
         'Straight-ray traversal against screen-space refraction, p95 relative. '
         'The chapter specifies the first.', 'rel')

    # the floor: the same pass handed the offline\'s own geometry
    esc, rt = LUT.ExitLUT('joint')(OPT.ABS[None] * off['dep3'][m])
    d = P['dirs'][m]
    cos_a = np.clip(-d[:, 2], 0.0, 1.0)
    R = OPT.fresnel(cos_a)
    Lb = WA.bed_radiance(off['dep3'][m], esc, rt)
    up = OPT.out_of_water((1.0 - R) * Lb * np.exp(-OPT.ABS[None] * off['path3'][m]))
    refl = d.copy()
    refl[:, 2] = -refl[:, 2]
    orc = R * WA.sky_dirs(refl) + up
    r = np.abs(orc - off['color'][m]) / np.maximum(off['color'][m], 1e-9)
    check(3, 'floor: exact geometry + joint LUT (max rel)',
          float(r.max()), 0.0, 3e-2,
          'The pass with the depth buffer taken out of the loop. What is left '
          'is the LUT and the composition, and it bounds how good the '
          'screen-space rows above could ever get.')
    info(3, 'floor: median rel', float(np.median(r)),
         'Nine parts per hundred thousand. The pass and the offline reference '
         'are one model.')
    info(3, 'post silhouette: pixels excluded, and their worst error',
         np.array([int((P['water'] & post).sum()),
                   float((np.abs(P['color'] - off['color'])
                          / np.maximum(off['color'], 1e-9))[P['water'] & post].max())]),
         'Screen-space refraction cannot see behind an occluder. The pass '
         'samples the post where the true refracted ray samples the bed, and '
         'the error is up to 120% on a 14 x 11 pixel patch. Reported, not '
         'hidden, and not fixable in screen space.', 'px / rel')


def tier3_factorisation_frame():
    """The chapter's claim, priced in pixels -- which is the whole reason a
    raster path had to exist."""
    g, off, post = _frames()
    m = None
    out = {}
    for up in ('directional', 'diffuse'):
        for md in ('joint', 'sep_2tau', 'sep_sq'):
            out[(up, md)] = WA.water_pass(g, exitlut=LUT.ExitLUT(md),
                                          upwelling=up, traversal='ssr',
                                          ssr_iters=6)
    m = out[('directional', 'joint')]['water'] & ~post
    tau_r = OPT.ABS[0] * out[('directional', 'joint')]['dep']
    for up in ('directional', 'diffuse'):
        J = out[(up, 'joint')]['color']
        for md in ('sep_2tau', 'sep_sq'):
            S = out[(up, md)]['color']
            info(3, 'frame error, %s / %s' % (up, md),
                 100 * ((S[m] - J[m]) / J[m]).mean(0),
                 'Signed, per band, over the whole water. Same geometry, same '
                 'everything -- only the bake differs.', '%')
    J = out[('diffuse', 'joint')]['color']
    S = out[('diffuse', 'sep_sq')]['color']
    for lo, hi in ((0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
                   (0.30, 0.50), (0.50, 0.79)):
        s = m & (tau_r >= lo) & (tau_r < hi)
        if s.sum() > 100:
            info(3, 'diffuse/sep_sq, tau_red %.2f-%.2f' % (lo, hi),
                 100 * ((S[s] - J[s]) / J[s]).mean(0),
                 'The chapter\'s claim, against optical depth, in a frame.', '%')
    d = LUT.at_depth(1.40)
    check(3, 'the frame HIDES the term error (diffuse, red)',
          float(100 * np.abs(((S[m] - J[m]) / J[m]).mean(0)[0])
                < 100 * d['esc_joint_over_sep'][0] / 2.0), 1.0, 0,
          '`12`: "an end-to-end agreement of a few percent is not evidence '
          'about a factor that is wrong by twenty". This row asserts the '
          'chapter is RIGHT about that -- the frame-level red error is less '
          'than half the term-level one, so a frame comparison at any sane '
          'tolerance would pass a bake that is wrong by a fifth.')
    info(3, 'LUT domain clamp fraction over the frame',
         LUT.ExitLUT('joint').clamp_frac(
             OPT.ABS[None] * out[('directional', 'joint')]['dep'][m][..., None]),
         'Share of fetches that saturated tau_max. A silently clamped table is '
         'a table that is not being tested.')


def tier3_jitter():
    """The chapter's second named trap: a TAA jitter the prepass applied and the
    water pass did not."""
    j = (0.375, -0.25)
    g = SC.prepass(jitter=j)
    ok = WA.water_pass(g, traversal='snell', jitter_shader=j)
    bad = WA.water_pass(g, traversal='snell', jitter_shader=None)
    m = ok['water'] & bad['water']
    dd = np.abs(ok['dep'][m] - bad['dep'][m])
    info(3, 'jitter mismatch: column error (ABSOLUTE)',
         np.array([float(np.median(dd)), float(dd.max())]),
         'Half a pixel of unmatched jitter, in metres of water column. On a '
         'shoaling bed at a grazing view a fraction of a pixel is a large '
         'fraction of a metre, which is why the chapter lists it as a trap and '
         'not a nicety.', 'm')
    r = np.abs(ok['color'][m] - bad['color'][m]) / np.maximum(ok['color'][m], 1e-9)
    info(3, 'jitter mismatch: radiance median / max',
         np.array([float(np.median(r)), float(r.max())]),
         'The same, in the frame.', 'rel')


# ====================================================== WAVES: THE FILTER PAIR
# `12`'s *Distance and filtering* and *Pick the kernel on purpose, and give the
# variance a receiver*. Everything below is on `waves.py` / `waveref.py`; see
# the README section of the same name for what each number turned out to mean.
def tier1_lobe_energy():
    """THE RECEIVER, AND THE ONE THING IN A SHARED MODULE THAT IS WRONG.

    Widening a `cos^n` lobe by a Gaussian must CONSERVE its angular integral --
    the chapter says so ("the integral is conserved, so the peak falls by
    sqrt(det Q0/det Q)") and it is the property that makes the whole doctrine a
    move of variance rather than an invention of light. Integrated here over the
    sphere by quasi-Monte-Carlo, both for `atmosphere._lobe_shape` as shipped
    and for the inverted form `waves.widened_lobes` carries."""
    n = ATM.N_DISC
    rng = np.random.default_rng(20260816)
    M = 2000000
    th = np.sqrt(rng.random(M)) * 0.30
    ph = rng.random(M) * 2 * np.pi
    u1, u2, cs = th * np.cos(ph), th * np.sin(ph), np.cos(th)
    r2 = u1 * u1 + u2 * u2
    ref = 2.0 * np.pi / (n + 1.0)
    pdf = (2.0 * th / 0.30 ** 2) / (2.0 * np.pi)

    def integral(c11, c22, inverted):
        q11, q22 = 1.0 / n + c11, 1.0 / n + c22
        det = q11 * q22
        g = (1.0 / n) / np.sqrt(det)
        ne = ((u1 * u1 * q22 + u2 * u2 * q11) / r2 / det if inverted
              else r2 / (u1 * u1 * q11 + u2 * u2 * q22))
        return float(np.mean(g * cs ** ne * np.sin(th) / pdf))

    # the estimator's own error, from the spread of the same integrand -- the
    # tolerance below is this and nothing else.
    for c11, c22, tag in ((1e-5, 1e-5, 'isotropic'),
                          (1e-3, 1e-4, 'axis ratio 10'),
                          (4.8e-3, 4.8e-7, 'axis ratio 1e4 (this frame)')):
        gi = integral(c11, c22, True)
        gs = integral(c11, c22, False)
        info(1, 'widened lobe integral, %s (ABSOLUTE, sr)' % tag,
             np.array([ref, gi, gs]),
             'Unwidened 2pi/(n+1), then the inverted form, then the shipped '
             'one. All three in steradians before any ratio.', 'sr')
        check(1, 'inverted receiver conserves flux, %s' % tag, gi / ref, 1.0,
              0.03,
              'Quasi-MC over a 0.30 rad cap with 2e6 samples; the tolerance is '
              'the estimator\'s spread, ~1.5% on the widest lobe here, doubled.',
              'ratio')
        info(1, 'atmosphere._lobe_shape flux gain, %s' % tag, gs / ref,
             '`_lobe_shape` returns n_eff = 1/(u^T Q u), the PROJECTION '
             'variance; the convolved density along u wants u^T Q^-1 u. Equal '
             'for an isotropic Q -- which is why nothing caught it -- and by '
             'Cauchy-Schwarz never narrower, so the lobe is too wide and the '
             'peak factor no longer normalises it. REPORTED, NOT PATCHED: '
             'atmosphere.py is shared.', 'x')

    # the other boundary condition the chapter insists on, at machine precision
    d = np.array([[0.3, 0.1, -0.9]]) / np.linalg.norm([0.3, 0.1, -0.9])
    z = np.zeros(1)
    a = WV.surface_shade(d, z, z, None)[0]
    b = WV.surface_shade(d, z, z, (z, z, z))[0]
    check(1, 'zero removed variance == unfiltered, BIT FOR BIT',
          float(np.abs(a - b).max()), 0.0, 0.0,
          '`12`: "a filtered path that does not reduce EXACTLY to the '
          'unfiltered one is a second shading model". Tolerance zero, in '
          'radiance, not a percentage.', 'L')


def tier1_refl_ellipse():
    """`C = J S J^T`, J = diag(-2, -2 cos theta_v), against Monte-Carlo
    perturbed reflections -- the chapter's own check, RUN here rather than
    cited, at the chapter's own sample count.

    `12` states its own agreement: "checked against 400k Monte-Carlo perturbed
    reflections to 4% on the major axis and 8% on the minor". That is a TIER-2
    bar -- a number the chapter publishes -- and it is the bar used, because the
    residual is not estimator noise: the map is FIRST ORDER in the slope and the
    second order is real. The order is measured below rather than asserted."""
    rng = np.random.default_rng(4242)
    M = 400000
    S0 = np.array([[2.0e-3, 5.0e-4], [5.0e-4, 8.0e-4]])
    for el_deg, thv, tag in ((-33.0, 57.0, "12's own camera, theta_v = 57 deg"),
                             (-12.0, 78.0, "this frame's road, theta_v = 78")):
        d = np.array([[np.cos(np.deg2rad(20.0)) * np.cos(np.deg2rad(el_deg)),
                       np.sin(np.deg2rad(20.0)) * np.cos(np.deg2rad(el_deg)),
                       np.sin(np.deg2rad(el_deg))]])
        r0 = WV.surface_shade(d, np.zeros(1), np.zeros(1), None)[4][0]
        vx, vy, vz = -d[0]
        s0 = np.cross([vx, vy, vz], [0.0, 0.0, 1.0])
        s0 = s0 - np.dot(s0, r0) * r0
        sh = s0 / np.linalg.norm(s0)
        eh = np.cross(r0, sh)
        devs = []
        for scale in (1.0, 0.25):
            S = S0 * scale
            u1, u2, c11, c12, c22, a, ndv = WV.refl_ellipse(
                d, np.zeros(1), np.zeros(1), np.ones(1),
                np.array([S[0, 0]]), np.array([S[1, 1]]), np.array([S[0, 1]]))
            L = np.linalg.cholesky(S)
            g = rng.standard_normal((M, 2)) @ L.T
            rd = WV.surface_shade(np.repeat(d, M, axis=0), g[:, 0], g[:, 1],
                                  None)[4]
            p1, p2 = rd @ eh, rd @ sh
            m11, m22 = float(np.mean(p1 * p1)), float(np.mean(p2 * p2))
            devs.append((abs(c11[0] / m11 - 1.0), abs(c22[0] / m22 - 1.0)))
            if scale == 1.0:
                info(1, 'reflected covariance, %s (ABSOLUTE)' % tag,
                     np.array([m11, m22, float(np.mean(p1 * p2))]),
                     'Monte-Carlo sample covariance of the reflected direction '
                     'offset, rad^2, in the frame perpendicular to R. Absolute, '
                     'before any comparison.', 'rad^2')
                fn = check if thv < 60.0 else info
                if thv < 60.0:
                    check(2, 'C11 = 4 * in-plane slope var, %s' % tag,
                          float(c11[0]) / m11, 1.0, 0.04,
                          "`12`: checked to 4% on the major axis. Same check, "
                          "same sample count, the chapter's own bar, at the "
                          "chapter's own camera.", 'ratio')
                    check(2, 'C22 = 4 cos^2(theta_v) * across var, %s' % tag,
                          float(c22[0]) / m22, 1.0, 0.08,
                          "`12`: 8% on the minor axis. This is the factor the "
                          "chapter says is NOT the identity and that a scalar "
                          "roughness bump cannot carry.", 'ratio')
                else:
                    info(2, 'C11 / C22 against MC, %s' % tag,
                         np.array([float(c11[0]) / m11, float(c22[0]) / m22]),
                         "THE CHAPTER'S 4%/8% DOES NOT REACH THIS ANGLE. At "
                         "its own 57 deg camera the map is inside its stated "
                         "agreement; at 78 deg -- which is where most of a "
                         "water frame with a horizon in it lives -- the "
                         "in-plane axis is 5.1% out. It is the linearisation "
                         "and not a defect: the order row below shows it "
                         "falling with the variance, and `12` states no angle "
                         "range beside its 4%.", 'ratio')
                info(1, 'reflection stretch 1/cos(theta_v), %s' % tag,
                     float(1.0 / ndv[0]),
                     "`12`: \"a camera 33 deg above the horizontal "
                     "(theta_v = 57 deg) stretches it 1.8x along the view "
                     "azimuth, an anisotropy the slope tensor never had\".")
        # the residual is the linearisation, so it must fall like the variance
        r1_, r2_ = devs[0], devs[1]
        between(1, 'C11 residual is SECOND order in the slope, %s' % tag,
                r1_[0] / max(r2_[0], 1e-9), 2.5, 16.0,
                'dR = J delta is first order, so the residual is O(sigma^2) '
                'and quartering the variance must quarter it. The bracket is '
                'wide because at S/4 the residual is 0.5-0.6% against a sample '
                'covariance error of 0.22% at M = 4e5, so the ratio itself is '
                'only known to about a factor of 1.5 -- and 1 (no order at '
                'all) and 16 (fourth order) are both comfortably outside it.',
                'x')
        info(1, 'C11/C22 deviation at S and S/4, %s' % tag,
             np.array([r1_[0], r2_[0], r1_[1], r2_[1]]),
             'The map dR = J delta is FIRST order in the slope, so the residual '
             'is O(sigma^2) and must fall by 4 when the variance falls by 4. '
             'That is the order check that separates a model error from a bug, '
             'and it is why the chapter quotes 4%/8% rather than machine '
             'precision.')


def tier1_footprint():
    """The scalar footprint, and the two claims under it."""
    g = WV.sun_prepass()
    base = WV.flat_base(g)
    w = base['water']
    fp, an, ok, P = WV.pixel_footprint(g, base['t'], base['dirs'], w)
    cosa = np.clip(-base['dirs'][..., 2], 1e-12, 1.0)
    fa, aa = WV.analytic_footprint(base['t'], cosa)
    info(1, 'footprint over the frame (ABSOLUTE, m)',
         np.array([float(fp[ok].min()), float(np.median(fp[ok])),
                   float(fp[ok].max())]),
         'min / median / max of sqrt(|det J|) from the 2x2 quad derivative of '
         'the water hit position. Metres, not a ratio.', 'm')
    info(1, 'footprint anisotropy s1/s2 (ABSOLUTE)',
         np.array([float(np.median(an[ok])), float(an[ok].max())]),
         'The axis ratio a SCALAR footprint has to discard. `field.py`\'s '
         'kernel is isotropic by construction ("all a scalar fp with no '
         'orientation is entitled to assume"), so this number is the size of '
         'the assumption, per frame.')
    # on the optical axis the closed form is exact; off it the pinhole
    # foreshortens the angular step and the quad derivative follows it.
    res = g['res']
    X, Y = SC.pixel_ndc(res)
    axial = ok & (np.abs(X) < 0.02) & (np.abs(Y) < 0.02)
    if axial.any():
        check(1, 'quad footprint == closed form on the optical axis',
              float(np.median(fp[axial] / fa[axial])), 1.0, 0.01,
              'fp = t*dth/sqrt(cos_a) is the leading-order form and is exact '
              'only where the pinhole\'s own foreshortening is 1. 1% because '
              'the "axis" here is a 2%-of-NDC box, over which cos^2 moves by '
              'about that.', 'ratio')
    info(1, 'quad footprint / closed form, whole frame',
         np.array([float(np.percentile(fp[ok] / fa[ok], 1)),
                   float(np.median(fp[ok] / fa[ok])),
                   float(np.percentile(fp[ok] / fa[ok], 99))]),
         'Off axis the two disagree by the pinhole term, and the DERIVATIVE '
         'one is the right one because it is what a shader computes.')
    info(1, 'quads with no usable derivative (ABSOLUTE, px)',
         np.array([int((w & ~ok).sum()), int(w.sum())]),
         'The horizon quad: one lane looks above the datum, so `t` is negative '
         'there and the quad derivative is not a footprint. Excluded from '
         'every measurement, reported as a count, exactly as `12`\'s occluder '
         'silhouettes are.', 'px')

    # THE HERO FRAME HAS NO SPECULAR ROAD -- the reason this section needs its
    # own camera, as a number rather than as a preference.
    gh = SC.prepass()
    Ph = WA.water_pass(gh, traversal='snell')
    r = Ph['dirs'].copy()
    r[..., 2] = -r[..., 2]
    csh = (r * ATM.SUN_DIR[None, None]).sum(-1)[Ph['water']]
    info(1, 'hero frame: max cos(mirror, sun) over water',
         float(csh.max()),
         'Negative: the sun\'s reflection is BEHIND the hero camera, so '
         '`atmosphere.sky`\'s disc contributes exactly zero to every water '
         'pixel of `r1-`\'s framing. A section about the specular response '
         'collapsing cannot be tested on a frame with no specular response.')
    check(1, 'hero frame: water pixels that see the sun disc', 
          int((csh > np.cos(ATM.THETA_SUN)).sum()), 0, 0,
          'Integer count, tolerance zero.', 'px')


def tier2_kernel():
    """*Pick the kernel on purpose*: the chapter's own Fourier arithmetic."""
    check(2, 'Gaussian sigma matched to the box second moment',
          1.0 / np.sqrt(12.0), 0.2887, 5e-5,
          '`12`: "The box of width fp has sigma = fp/(2 sqrt 3) = 0.2887 fp".',
          'x fp')
    check(2, 'that Gaussian passes 0.663 at the Nyquist wavenumber',
          float(np.exp(-0.5 * np.pi ** 2 / 12.0)), 0.663, 5e-4,
          '`12`: "a Gaussian that wide still passes 0.663 of the amplitude at '
          'the Nyquist wavenumber -- 44% of the variance straight into the '
          'fold". The variance figure is 0.663^2 = 0.44, checked below.')
    check(2, '...i.e. 44% of the variance', float(np.exp(-np.pi ** 2 / 12.0)),
          0.44, 5e-3, 'The same number squared, which is the chapter\'s own '
          'second sentence and its own consistency check.')
    check(2, 'half-amplitude-at-Nyquist scale = 0.3748 fp',
          float(FLD.FP_SIGMA), 0.3748, 5e-5,
          '`12`: "sigma = sqrt(2 ln 2)/pi * fp = 0.3748 fp". This is '
          '`field.FP_SIGMA`, imported, not recomputed.', 'x fp')
    # the sentence the whole filter collapses to
    lam = 0.20
    k = 2.0 * np.pi / lam
    check(2, 'a component is half gone at fp = lambda/2',
          float(FLD.band_weight(k, lam / 2.0)), 0.5, 1e-7,
          '`12`: "a component is half gone when the footprint reaches half its '
          'wavelength". Closed form through `field.band_weight`; the tolerance '
          'is 1e-7 and not machine precision because `field._fp_var` casts the '
          'footprint to FLOAT32 -- deliberately, since the grid path is f32 -- '
          'so the exponent carries 3.5e-8 of rounding and no more.', 'W')
    check(2, '...and 94% gone at fp = lambda',
          float(1.0 - FLD.band_weight(k, lam)), 0.94, 5e-3,
          '`12`: "and 94% gone at one wavelength".', '1-W')
    check(2, 'half-VARIANCE footprint is smaller by sqrt(2)',
          float(FLD.half_footprint(k) / lam), 0.5, 1e-12,
          '`field.half_footprint` is lambda/2 with no free constant left in '
          'it; the chapter\'s own note that the half-variance point is at '
          '0.354 lambda is the same statement over sqrt(2).', 'x lambda')
    # the saturating form the chapter writes the tensor with
    a = 0.1
    wr = 1.0
    sat = 1.0 - np.sqrt(max(1.0 - a * a * wr * wr, 0.0))
    check(2, 'chapter\'s saturating variance vs a^2/2, at the steepest slope',
          float(sat / (0.5 * a * a)), 1.0, 3e-3,
          '`12` writes the removed variance as 1 - sqrt(1 - |k|^2 w_r^2 h^2); '
          '`field.py` uses a^2 w_r^2/2 and says the two differ by 0.25% at the '
          'steepest slope in the basin (a ~ 0.1). They differ by 0.25%.')


def tier2_wave_chapter():
    """Numbers `12` prints in the same two sections, checked."""
    # Monahan & O'Muircheartaigh, quoted with two worked values
    for u, want, tol in ((5.0, 0.001, 3e-4), (15.0, 0.04, 5e-3)):
        check(2, 'whitecap coverage at U10 = %.0f m/s' % u,
              float(3.84e-6 * u ** 3.41), want, tol,
              '`12`: W = 3.84e-6 U^3.41, "essentially absent at 5 m/s (~0.1% '
              'coverage) and conspicuous by 15 m/s (~4%)". Both of the '
              'chapter\'s own worked values, at the precision it states them.',
              'frac')
    # Brewster, the closed-form guard the chapter offers for the base curve
    n = OPT.IOR[1]
    br = ((n ** 2 - 1.0) / (n ** 2 + 1.0)) ** 2 / 2.0
    got = float(OPT.fresnel(np.array([np.cos(np.arctan(n))]))[0, 1])
    check(2, 'Brewster identity R(atan n) (ABSOLUTE)', got, br, 1e-12,
          '`12`: "the guard to put on it is the Brewster identity, '
          'R(atan n) = ((n^2-1)/(n^2+1))^2/2, a closed-form number an '
          'approximation cannot reach". `optics.fresnel` reaches it exactly.',
          'R')
    sch = 0.02 + 0.98 * (1.0 - np.cos(np.arctan(n))) ** 5
    info(2, 'Schlick at Brewster / exact - 1', float(sch / br - 1.0),
         '`12` says Schlick misses the Brewster identity by 22%.')
    for deg, want in ((51.3, -0.228), (79.0, 0.143), (67.1, 0.0)):
        c = np.cos(np.deg2rad(deg))
        ex = float(OPT.fresnel(np.array([c]))[0, 1])
        f0 = float(OPT.fresnel(np.array([1.0]))[0, 1])
        s = f0 + (1.0 - f0) * (1.0 - c) ** 5
        check(2, 'Schlick/exact - 1 at %.1f deg' % deg, s / ex - 1.0, want,
              0.012,
              '`12`: "-22.8% at 51.3 deg and +14.3% at 79 deg, crossing zero '
              'at 67.1 deg". Reproduced against `optics.fresnel`; 1.2% because '
              'the chapter quotes to 0.1 pp and F0 is quoted to two figures.',
              'rel')
    # Bruneton's roughness factor, its two constants and its limits
    check(2, 'roughness factor -> 1 at zero variance',
          float(np.exp(-2.69 * 0.0) / (1.0 + 22.7 * 0.0 ** 1.5)), 1.0, 0.0,
          '`12`\'s exp(-2.69 s)/(1 + 22.7 s^1.5). At s = 0 it must be exactly '
          '1 or the near water\'s Fresnel moves.', 'r')
    for sv in (0.0344, 0.10, 0.50):
        info(2, 'roughness factor r at sigma_v = %.4f' % sv,
             float(np.exp(-2.69 * sv) / (1.0 + 22.7 * sv ** 1.5)),
             'The fit `12` quotes "for sigma_v < 0.5". It has no stated LOWER '
             'bound and it needs one: at this frame\'s own sigma_v = 0.0344 '
             'it already removes 20% of the grazing rise, where the exact '
             'expectation removes 1-5%. See tier 3 and the README.', 'r')


# ------------------------------------------------------ TIER 3, the wave frame
_WCACHE = {}


def _wframes(nsub=196):
    """The sun-facing frame, its reference and the paths, built once."""
    if not _WCACHE:
        WV.init_field()
        g = WV.sun_prepass()
        base = WV.flat_base(g)
        w = base['water']
        fp, an, ok, P = WV.pixel_footprint(g, base['t'], base['dirs'], w)
        _WCACHE.update(g=g, base=base, w=w, fp=fp, an=an, ok=ok, P=P,
                       t=base['t'][w], fpw=fp[w], okw=ok[w])
        _WCACHE['ref'] = WR.reference(g, base, w, nsub=nsub, seed=5,
                                      want_mip=True)
        for nm, kw in (('point', dict(path='point')),
                       ('naive', dict(path='naive')),
                       ('fix', dict(path='variance', fresnel='exact')),
                       ('fix+fit', dict(path='variance', fresnel='rough')),
                       ('fix+box', dict(path='variance', fresnel='exact',
                                        fp_scale=1.0 / 1.29254)),
                       ('naive+box', dict(path='naive',
                                          fp_scale=1.0 / 1.29254)),
                       ('fix+shipped', dict(path='variance', fresnel='exact',
                                            receiver='shipped'))):
            _WCACHE[nm] = WV.wave_pass(g, base=base, want_parts=True, **kw)
    return _WCACHE


WBINS = np.array([4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 520.0])


def _wbin(C, i):
    t, okw = C['t'], C['okw']
    return (t >= WBINS[i]) & (t < WBINS[i + 1]) & okw


def tier3_wave_variance():
    """THE MECHANISM, measured: where the slope variance goes with distance.

    `12`: "per-pixel normals computed from displaced geometry converge to the
    MEAN normal -- vertical -- and all the slope variance those waves carried is
    silently discarded". This is that sentence as a table."""
    C = _wframes()
    ref = C['ref']
    s_stat = WV.stationary_rms()
    info(3, 'stationary rms slope of the field (ABSOLUTE)', s_stat,
         'WIND and REVERB in quadrature, through `field._plane_rms` -- the '
         'file\'s own analytic convention function, because writing the rms '
         'expression out by hand is how two conventions once coexisted there. '
         'This frame puts water out to 400 m while `field.py`\'s basin is '
         '8 x 4 m; NEAR falls as 1/sqrt(r), BOIL rides its envelope and the '
         'WAKE measures identically zero outside the basin, so out there the '
         'surface IS these two bands.')
    for i in range(len(WBINS) - 1):
        s = _wbin(C, i)
        if s.sum() < 200:
            continue
        gx, gy = C['naive']['gx'][s], C['naive']['gy'][s]
        vxx, vyy, vxy = FLD.slope_var_points(C['P'][..., 0][C['w']][s],
                                            C['P'][..., 1][C['w']][s],
                                            C['fpw'][s])
        res = FLD.rms_slope(gx, gy)
        rem = float(np.sqrt(np.mean(vxx + vyy)))
        tot = float(np.sqrt(np.mean(ref['s_res'][s] ** 2)))
        info(3, 'slope rms at %.0f-%.0f m: total / resolved / removed'
             % (WBINS[i], WBINS[i + 1]), np.array([tot, res, rem]),
             'ABSOLUTE rms slopes at the pass\'s own footprints. The middle '
             'column is the collapse; the third is what has to arrive '
             'somewhere.', 's')
        check(3, 'variance identity at %.0f-%.0f m' % (WBINS[i], WBINS[i + 1]),
              float(np.hypot(res, rem)) / tot, 1.0, 0.02,
              'resolved^2 + removed^2 = total^2, i.e. `field.py`\'s own '
              'conservation, checked at RASTER footprints (up to 23 m, two '
              'orders past anything `render.py` asks of it). 2% because the '
              'sum is band-by-band while the total is measured on the summed '
              'field, so the inter-band sample covariance is in it -- '
              '`field.py` says so at `slope_var_points`.', 'ratio')
    # the tensor is a COVARIANCE, and the trace is the total mean square: the
    # one place a sqrt(2) can still get in.
    s = _wbin(C, len(WBINS) - 2)
    vxx, vyy, vxy = FLD.slope_var_points(C['P'][..., 0][C['w']][s],
                                        C['P'][..., 1][C['w']][s],
                                        C['fpw'][s])
    info(3, 'removed tensor: trace vs one-direction (ABSOLUTE)',
         np.array([float(np.mean(vxx + vyy)), float(np.mean(vxx)),
                   float(np.mean(vyy))]),
         'THE sqrt(2) SITE, from the consumer\'s side. `field.py` is explicit '
         'that sqrt(vxx+vyy) is the TOTAL mean-square slope; Bruneton\'s '
         'sigma_v is the ONE-DIRECTION variance, `12`\'s own "not s^2". Using '
         'the trace where the fit wants one direction is a factor of 2 in '
         'variance and sqrt(2) in rms -- the same mixed convention that once '
         'put sqrt(2)*0.024 of slope on this project\'s water, arriving from '
         'the other end.', 's^2')
    # Toksvig, for free, out of the reference's own sub-samples
    nl = np.linalg.norm(ref['nrm'][s], axis=1)
    tot = float(np.sqrt(np.mean(ref['s_res'][s] ** 2)))
    check(3, 'mip normal length carries the variance: 2(1-|Nbar|) == s^2',
          float(2.0 * np.mean(1.0 - nl)) / tot ** 2, 1.0, 0.06,
          'A LITERAL normal-map mip texel is the mean of the unit normals over '
          'the footprint, and its LENGTH is Toksvig\'s signal: |Nbar| = '
          '1 - s^2/2 to second order. Measured off the reference\'s own '
          'sub-samples, so it costs nothing. 6 per cent because the mean of '
          + str(ref['nsub']) + ' unit normals has a sampling bias of order '
          's^2/N. The consequence is the actionable one: a mip chain ALREADY '
          'carries the removed variance, and renormalising the texel is what '
          'throws it away.', 'ratio')


def tier3_wave_frame():
    """THE THREE PATHS AGAINST THE PIXEL\'S OWN INTEGRAL."""
    C = _wframes()
    ref, w, okw = C['ref'], C['w'], C['okw']
    Y = Y709

    info(3, 'reference: sub-samples per pixel and its own error',
         np.array([ref['nsub'],
                   float(np.median(ref['sem'][okw, 1] / np.maximum(
                       ref['color'][okw, 1], 1e-9)))]),
         'Stratified sub-samples and the MEDIAN relative standard error of the '
         'per-pixel estimate. Every tolerance below is built from this and '
         'never from a disagreement.')

    # ---- the specular term, where the claim lives
    for i in range(len(WBINS) - 1):
        s = _wbin(C, i)
        if s.sum() < 200:
            continue
        rc = float(ref['sun_cone1'][s, 1].mean())
        rm = float(ref['sun'][s, 1].mean())
        hits = float(ref['sun_hits1'][s].sum())
        info(3, 'sun disc, %.0f-%.0f m: cone / MC / naive / fix (ABSOLUTE)'
             % (WBINS[i], WBINS[i + 1]),
             np.array([rc, rm, float(C['naive']['L_sun'][s, 1].mean()),
                       float(C['fix']['L_sun'][s, 1].mean())]),
             'Scene-linear radiance, green. TWO INDEPENDENT REFERENCE '
             'ESTIMATORS: the 2 deg cone density (%d hits here, Poisson error '
             '%.1f%%) and the brute-force sub-sample mean. Where the second '
             'converges they agree; where it does not, it reads zero and says '
             'so.' % (hits, 100.0 / max(np.sqrt(hits), 1.0)), 'L')

    # the two estimators against each other, where both have enough hits
    for i in range(len(WBINS) - 1):
        s = _wbin(C, i)
        if s.sum() < 200 or ref['sun_hits1'][s].sum() <= 5000:
            continue
        rc = float(ref['sun_cone1'][s, 1].mean())
        rc0 = float(ref['sun_cone0'][s, 1].mean())
        rm = float(ref['sun'][s, 1].mean())
        h = float(ref['sun_hits1'][s].sum())
        # THE TOLERANCE IS THE ESTIMATOR'S OWN, AND IT IS THE LARGER OF ITS TWO
        # ERRORS: the Poisson count, and the KERNEL BIAS the cone estimator
        # reports about itself by running at two half-angles. Near the specular
        # point the reflected-direction density has structure well inside 2 deg
        # -- that is what the resolved waves ARE -- so the bias dominates there
        # and the count dominates far out. Neither is the disagreement being
        # measured.
        bias = 2.0 * abs(rc0 - rc) / max(rc, 1e-12)
        info(3, 'cone estimator at 1 deg and 2 deg, %.0f-%.0f m (ABSOLUTE)'
             % (WBINS[i], WBINS[i + 1]), np.array([rc0, rc, bias]),
             'The same density at two kernel widths. Their spread IS the '
             'estimator\'s bias and it is what the next row is allowed to '
             'spend.', 'L')
        check(3, 'cone density == brute force, %.0f-%.0f m'
              % (WBINS[i], WBINS[i + 1]), rc / rm, 1.0,
              max(4.0 / np.sqrt(h), bias),
              'Two estimators of the same integral sharing no line beyond the '
              'sub-sample positions: a delta-of-known-flux times the measured '
              'reflected-direction density, against the direct sub-sample '
              'mean. Where both converge they must agree to the worse of the '
              'two errors above.', 'ratio')

    # ---- the composed frame
    for nm in ('point', 'naive', 'fix', 'fix+fit', 'fix+shipped'):
        a = C[nm]['color'][w][okw]
        b = ref['color'][okw]
        rel = np.abs(a - b) / np.maximum(b, 1e-9)
        info(3, 'frame error, %s: median / p95 / absolute median' % nm,
             np.array([float(np.median(rel)), float(np.percentile(rel, 95)),
                       float(np.median(np.abs(a - b)))]),
             'Over %d water pixels, all three bands, scene-linear. The '
             'absolute column is there because the relative one is a lottery '
             'wherever the reference itself is a glint.' % int(okw.sum()), '')

    for i in range(len(WBINS) - 1):
        s = _wbin(C, i)
        if s.sum() < 200:
            continue
        row = []
        for nm in ('naive', 'fix', 'fix+fit'):
            e = np.abs(C[nm]['color'][w][s] - ref['color'][s]) / np.maximum(
                ref['color'][s], 1e-9)
            row.append(float(np.median(e)))
        info(3, 'frame median error at %.0f-%.0f m: naive / fix / fix+fit'
             % (WBINS[i], WBINS[i + 1]), np.array(row),
             'The verdict, against distance. It does not say what the chapter '
             'says it will -- see the README.', 'rel')

    # ---- the Fresnel, which is the one FITTED thing in the doctrine
    for i in range(len(WBINS) - 1):
        s = _wbin(C, i)
        if s.sum() < 200:
            continue
        Rr = float(ref['fresnel'][s, 1].mean())
        info(3, 'Fresnel at %.0f-%.0f m: E[R] / smooth / Bruneton (ABSOLUTE)'
             % (WBINS[i], WBINS[i + 1]),
             np.array([Rr, float(C['naive']['R'][s, 1].mean()),
                       float(C['fix+fit']['R'][s, 1].mean())]),
             'E[R] is the EXACT mean of `optics.fresnel` over the footprint\'s '
             'own slope distribution, from the reference\'s sub-samples. The '
             'middle column is Fresnel at the filtered normal (i.e. doing '
             'nothing); the third is `12`\'s one-line fix.', 'R')
    s = C['okw']
    Rr = ref['fresnel'][s, 1]
    check(3, 'doing nothing beats Bruneton\'s fit at this variance',
          float(np.median(np.abs(C['fix+fit']['R'][s, 1] - Rr) / Rr)
                > np.median(np.abs(C['naive']['R'][s, 1] - Rr) / Rr)),
          1.0, 0.0,
          'THIS ROW ASSERTS A FINDING AGAINST THE CHAPTER, and it is left as a '
          'PASS because the finding is the result: at sigma_v = 0.034 the '
          'roughness-Fresnel fit is further from the exact expectation than '
          'the smooth curve is. The fit deviates from 1 as sigma^1.5 while the '
          'true correction is O(sigma^2), so it over-corrects by an order of '
          'magnitude at the bottom of its own stated range.', 'bool')

    # ---- the kernel is supposed to stop mattering once the variance is carried
    for nm, other in (('fix', 'fix+box'), ('naive', 'naive+box')):
        a = np.array([float(C[nm]['L_sun'][_wbin(C, i), 1].mean())
                      for i in range(3)])
        b = np.array([float(C[other]['L_sun'][_wbin(C, i), 1].mean())
                      for i in range(3)])
        info(3, 'kernel scale 1.0 vs 0.774 (box match), %s: sun term' % nm,
             np.abs(b / np.maximum(a, 1e-12) - 1.0),
             'THE DOCTRINE\'S CENTRAL PROMISE, tested directly. If the removed '
             'variance really is carried rather than lost, the answer must not '
             'depend on how much the kernel removes. Two kernels 29% apart in '
             'width -- `field.py`\'s Nyquist half-amplitude pinning against '
             'the box\'s second-moment match -- over the three bins the sun\'s '
             'road covers.', 'rel')

    # ---- what the anisotropic-receiver defect costs in a frame
    a = C['fix']['color'][w][okw]
    b = C['fix+shipped']['color'][w][okw]
    info(3, 'atmosphere._lobe_shape defect, in the frame',
         np.array([float(np.median(np.abs(b - a) / np.maximum(a, 1e-9))),
                   float(np.percentile(np.abs(b - a) / np.maximum(a, 1e-9), 99)),
                   float(np.abs(b - a).max())]),
         'Median / p99 relative and the worst absolute radiance, between the '
         'inverted receiver and the shipped one, everything else identical.',
         '')


def tier3_wave_cost():
    """THE PRICE. `12` tells a reader the fix is worth it and never prices it."""
    C = _wframes()
    g, base = C['g'], C['base']
    npx = int(C['w'].sum())
    times = {}
    for nm, kw in (('point', dict(path='point')),
                   ('naive', dict(path='naive')),
                   ('fix', dict(path='variance', fresnel='exact')),
                   ('fix+fit', dict(path='variance', fresnel='rough'))):
        best = np.inf
        for _ in range(3):
            t0 = time.time()
            WV.wave_pass(g, base=base, **kw)
            best = min(best, time.time() - t0)
        times[nm] = best
    for nm in times:
        info(3, 'surface shading cost, %s (ABSOLUTE)' % nm,
             np.array([1e3 * times[nm], 1e6 * times[nm] / npx]),
             'Wall clock for the whole water surface at %d px, and per pixel. '
             'THIS IS NUMPY ON A CPU and it is not a GPU frame time; what '
             'transfers is the RATIO and the op count, not the milliseconds. '
             'The absolute column is here because a ratio with no scale on it '
             'has been blind in this project four times.' % npx, 'ms / us/px')
    info(3, 'the fix, as a fraction of the naive path',
         np.array([times['fix'] / times['naive'],
                   times['fix+fit'] / times['naive']]),
         'What carrying the variance costs over discarding it: one extra call '
         'to `field.slope_var_points`, the 2x2 rotation into the view frame, '
         'and a per-pixel lobe exponent.')
    # the chapter promises the opposite scaling and does not get it
    x = np.full(200000, 4.0)
    y = np.full(200000, 2.0)
    tt = []
    for fp in (0.001, 10.0):
        best = np.inf
        for _ in range(3):
            t0 = time.time()
            FLD.slope_var_points(x, y, np.full(200000, fp))
            best = min(best, time.time() - t0)
        tt.append(best)
    info(3, 'slope_var_points cost at fp = 1 mm vs 10 m',
         np.array([1e3 * tt[0], 1e3 * tt[1], tt[1] / tt[0]]),
         '`12`\'s "practical trick: total variance for ALL waves on the CPU, '
         'subtract the RESOLVED waves in the shader, so shader cost scales '
         'with resolved wave count and is MINIMAL for distant views". '
         '`field.slope_var_points` sums over every component at every '
         'footprint, so it costs the same at 10 m as at 1 mm -- the opposite '
         'of the stated scaling, and at 10 m almost every term it evaluates is '
         'the saturated constant. Reported, not patched: it is another lane\'s '
         'file and the interface is right.', 'ms')


def main():
    t0 = time.time()
    tier1_triangle()
    tier1_rayplane()
    tier1_depth()
    tier1_energy()
    tier1_hemispherical()
    tier2_chapter_tables()
    tier3_quadrature()
    tier3_lut_interp()
    tier3_sky_entry()
    tier1_lobe_energy()
    tier1_refl_ellipse()
    tier1_footprint()
    tier2_kernel()
    tier2_wave_chapter()
    if not FAST:
        tier3_frame()
        tier3_factorisation_frame()
        tier3_jitter()
        tier3_wave_variance()
        tier3_wave_frame()
        tier3_wave_cost()
    n = report()
    print('%.1f s' % (time.time() - t0))
    return 1 if n else 0


if __name__ == '__main__':
    sys.exit(main())
