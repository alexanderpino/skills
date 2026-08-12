"""External validation of the pool reference implementation.

    python3 validate.py            # runs everything, exits non-zero on any FAIL
    python3 validate.py -v         # also prints every tolerance's justification

WHY THIS FILE EXISTS. `render.py` prints ~90 diagnostics per run and almost all of
them check the implementation against itself: a derived constant against the
expression it was derived from, a measured field against the target it was
normalised to. That is internal consistency, and a reference that has only ever
been checked against its own opinion is a second opinion. This file checks it
against things that were not written here.

THREE TIERS, and the tier is the strength of the evidence, not the difficulty:

  Tier 1  CLOSED FORM.  The right answer is known analytically, so a
          disagreement is unambiguous and is a bug in one of the two.
  Tier 2  PUBLISHED MEASUREMENT.  Compared against a citation. A disagreement
          may be a bug, a different sample point, or a different water.
  Tier 3  INDEPENDENT METHOD.  A second estimate computed a different way --
          Monte-Carlo against an analytic form, a brute-force march against a
          quadratic solve. A disagreement localises to one of the two methods.

HOW TO READ A FAILURE. Every row prints expected, measured, tolerance. The
tolerance is chosen from the *estimator's* own error (binning, Monte-Carlo
variance, float32 precision) or from the published uncertainty -- never from the
measured disagreement. So a FAIL means the number is outside the range the
measurement itself can explain, and the next question is always "which of the two
sides is wrong", not "can the tolerance move". Rows marked INFO carry no
assertion: they are measurements printed because they are worth knowing, and they
never affect the exit code.

WHAT THIS FILE MAY NOT DO. It imports `field`, `wake` and (by slicing, see
`load_render`) `render`. It never edits them. A test that finds a bug is left
failing on purpose.
"""
import ast
import contextlib
import io
import sys
import time
import types
import warnings

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv


# --------------------------------------------------------------------- harness
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
    a = np.asarray(v, float)
    if a.ndim:
        return '[' + ' '.join(_fmt(x) for x in a.ravel()) + ']'
    a = float(a)
    if a == 0:
        return '0'
    m = abs(a)
    if 1e-4 <= m < 1e5:
        return '%.6g' % a
    return '%.3e' % a


def check(tier, name, got, exp, tol, why, unit='', rel=False):
    """Assert |got - exp| <= tol (or <= tol*|exp| if rel). `why` justifies tol."""
    g = np.asarray(got, float)
    e = np.asarray(exp, float)
    lim = np.asarray(tol, float) * (np.abs(e) if rel else 1.0)
    ok = bool(np.all(np.abs(g - e) <= lim + 1e-300))
    ROWS.append(Row(tier, name, exp, got, ('%s rel' % _fmt(tol)) if rel else tol,
                    'PASS' if ok else 'FAIL', why, unit))
    return ok


def between(tier, name, got, lo, hi, why, unit=''):
    """Assert lo <= got <= hi. Used where the literature gives a range."""
    g = float(got)
    ok = lo <= g <= hi
    ROWS.append(Row(tier, name, '%s..%s' % (_fmt(lo), _fmt(hi)), got,
                    'range', 'PASS' if ok else 'FAIL', why, unit))
    return ok


def info(tier, name, got, note, exp=None):
    """A measurement with no assertion attached. Never fails the run."""
    ROWS.append(Row(tier, name, exp, got, '-', 'INFO', note, ''))


# ------------------------------------------------------------ loading render.py
# render.py has no `if __name__ == '__main__'` guard: importing it runs the whole
# 4m45s render, writes three PNGs and allocates several GB. That is not something
# a test suite can do on every run, and reducing its resolution constants would
# test a renderer nobody ships.
#
# So the module is loaded by SLICING: its source is parsed, and only the top-level
# nodes that DEFINE things are executed -- imports, function and class
# definitions, and cheap assignments. Every top-level `for`, `while`, `if` and
# bare expression (i.e. every `print` and every pass loop) is skipped, as is a
# named list of assignments that allocate the big buffers. Nodes that then fail
# with NameError because their input was skipped are recorded and skipped in turn.
#
# THE GUARD AGAINST THIS SILENTLY LOSING SOMETHING is `REQUIRED`: every name this
# file tests is listed there, and the loader raises if any is missing. A skipped
# node that mattered shows up as a missing name, not as a quietly absent test.
_SKIP_ASSIGN = {
    # the big buffers and everything derived inside a pass loop
    'bed', 'wall', 'BU', 'BV', 'BDEP', 'DLEV', 'LIN', 'GLOW', 'BED_AO',
    'SHADOW', '_cov', '_den', 'RIS_MAP', 'D', 'PX', 'PY', 'HDR', '_hdr',
    '_E', '_A', '_W', 'BEDRET', 'BED_DRY', 'bedret', '_WSH', 'SX', 'SY',
    '_VN', 'EDGE_PX', 'EDGE_DISP', 'DECK', 'DECK0', 'BANDG', 'BANDG0',
    'SUBK', '_LATIN',
    # 21 s of Monte-Carlo on the antialiasing estimator; not tested here
    '_CQ3', '_CQA',
    # 3 s to build the waterline; not tested here
    'WLINE', 'ETA_RMS', 'WETTOP',
}
_HEAVY_TEXT = ('np.zeros((', 'np.meshgrid', 'rng.random((', 'np.linspace(X0 - 3')

REQUIRED = [
    'IOR', 'LAM', 'ABS', 'F0', 'n_water', 'BAND', 'CAUCHY_A', 'CAUCHY_B',
    'SUN_DIR', 'SUN_COL', 'DEPTH', 'X0', 'X1', 'Y0', 'Y1', 'CYL',
    'refract', 'is_tir', 'fresnel', 'tir_vert',
    'scene_hit', 'box_hit', '_cyl_entry', 'splat', 'blur', 'sample',
    'bed_depth', 'bed_z', 'pool_sdf', 'edge_z',
    'cos_i', 'cos_t', 'sin_t', 'slant', 'TSUN', 'sig_at', 'SIG_EST',
    'TIR_FRAC', 'TIR_VERT', '_sky_vf', '_ris_closure', 'RIS_D0', 'RIS_D1',
    'RIS_ND', 'RIS_NP', 'RIS_HMIN', '_DD', '_PH', '_lnR',
    # the gather, now shared by the risers and the pool walls, and the partition
    # of the wall's hemisphere that keeps the sky from being counted twice
    'bounce_gather', 'bed_wall_src', 'wall_shade', 'WALL_SKY', 'WB_NU', 'WB_NZ',
    'WALL_BAND_Z', 'WALL_FRONT',
    'R_EXT', 'R_INT', 'wet_albedo', '_fresnel_rough', '_refl_ellipse',
    '_lobe_shape', 'sky', 'SKY_LOBE', 'E_SUN', 'L_SUN', 'OMEGA_SUN', 'N_DISC',
    '_e3', 'T_DIFF_UP', 'trap_gain', 'rho_water', 'slab_esc', 'slab_trap',
    'R_INT_MU',
    'N_AURE', 'L_AURE', 'AIRMASS', 'TAU_R', '_tau_rayleigh', 'THETA_SUN',
    'CAP_A', 'MENIS_H', 'SIGMA_W',
    # the fillet: the tables, the two helpers the columns are built on, the
    # shipped integrator, and the constant that records the refuted term
    'menis_tables', 'MENIS_N', 'MENIS_WD', 'MENIS_D', 'MENIS_Z', 'MENIS_SIN',
    'MENIS_COS', 'MENIS_REACH', 'MENIS_LIFT', 'PHI_W', 'THETA_C', '_mph',
    '_menis_weights', '_menis_under', '_env_menis', 'meniscus',
    'MENIS_TIR_REACH', 'EDGE_REFL', 'surf_stats', 'pool_grad',
    'EYE', 'PIXANG', 'SS', 'SLIP', 'sail_vis',
    # the six defects closed in the round that follows: the interface
    # transport, the wall planes, the map's top, the fold guard and the
    # stone's own sun term
    'N2', 'out_of_water', 'T_OUT_DIFFUSE', 'WTOP',
    'XW0', 'XW1', 'YW0', 'YW1', 'pool_sdf_grad',
    'MENIS_FOLD_TOL', '_menis_fold_guard',
    'stone_vis', 'sun_vis', 'coping_vis', 'SBUL', 'COPW', 'ZD', 'ZLIP',
    # the camera under the water: the interface crossed in the gaining
    # direction, the tracer that is allowed to look up, and the frame the
    # window's rim is measured off
    'into_water', 'submerged_radiance', 'scene_hit_under', '_cyl_entry_any',
    'uw_interface', 'uw_shade', 'uw_render', 'uw_dirs', 'uw_pixel_dirs',
    'uw_project', 'UW_EYE', 'UW_TC', 'UW_TSUN', 'UW_SPREAD', 'UW_FOV',
    'UW_TF', 'UW_PIXANG', 'INSCAT', 'INSCAT_K', 'W', 'H', 'SS',
    'normal_from_grad',
]


def load_render():
    src = open(HERE + '/render.py').read()
    tree = ast.parse(src)
    mod = types.ModuleType('render_sliced')
    g = mod.__dict__
    g['__name__'] = 'render_sliced'
    g['__file__'] = HERE + '/render.py'
    skipped, errors = 0, []
    sink = io.StringIO()
    for node in tree.body:
        if isinstance(node, (ast.For, ast.While, ast.If, ast.Try, ast.With)):
            skipped += 1
            continue
        if isinstance(node, ast.Expr):
            if not (isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                skipped += 1
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            tgts = [node.target] if not isinstance(node, ast.Assign) else node.targets
            names = {n.id for t in tgts for n in ast.walk(t)
                     if isinstance(n, ast.Name)}
            seg = ast.get_source_segment(src, node) or ''
            if names & _SKIP_ASSIGN or any(h in seg for h in _HEAVY_TEXT):
                skipped += 1
                continue
        try:
            with contextlib.redirect_stdout(sink), np.errstate(all='ignore'), \
                    warnings.catch_warnings():
                warnings.simplefilter('ignore')
                exec(compile(ast.Module(body=[node], type_ignores=[]),
                             g['__file__'], 'exec'), g)
        except Exception as exc:                       # noqa: BLE001 -- by design
            errors.append((node.lineno, '%s: %s' % (type(exc).__name__, exc)))
    missing = [n for n in REQUIRED if n not in g]
    if missing:
        raise SystemExit(
            'validate.py: the render.py slice did not produce %s.\n'
            'render.py has been restructured; fix load_render or REQUIRED.\n'
            'First few load errors: %s' % (missing, errors[:8]))
    return mod, skipped, errors


# ---------------------------------------------------------------- shared exact
def fresnel_exact(cos_i, n):
    """Unpolarised reflectance at a smooth dielectric, air -> medium n.

    Returns (R_unpolarised, R_s, R_p). Past the critical angle for n < 1 the
    caller must not use this; here n > 1 always, so cos_t is real."""
    ci = np.asarray(cos_i, float)
    st = np.sqrt(np.maximum(1.0 - ci ** 2, 0.0)) / n
    ct = np.sqrt(np.maximum(1.0 - st ** 2, 0.0))
    rs = ((ci - n * ct) / (ci + n * ct)) ** 2
    rp = ((n * ci - ct) / (n * ci + ct)) ** 2
    return 0.5 * (rs + rp), rs, rp


# ============================================================ TIER 1: FRESNEL
def tier1_fresnel(R):
    IOR, F0 = R.IOR, R.F0
    # -- the normal-incidence identity. Pure algebra: R(0) = ((n-1)/(n+1))^2 is
    # the exact Fresnel limit, so the only tolerance is float round-off.
    check(1, 'F0 == ((n-1)/(n+1))^2', F0, ((IOR - 1) / (IOR + 1)) ** 2, 1e-15,
          'algebraic identity; tolerance is one double ulp')
    for c, nm in enumerate('RGB'):
        n = IOR[c]
        th = np.linspace(0.0, np.pi / 2, 20001)
        ci = np.cos(th)
        ex, rs, rp = fresnel_exact(ci, n)
        # -- R(0) against the file's own F0.  Same reason: exact limit.
        check(1, 'exact Fresnel R(0) == F0  [%s]' % nm, ex[0], F0[c], 1e-14,
              'exact limit of the same formula; double round-off only')
        # -- grazing.  R -> 1 as theta -> 90 for any n.  Evaluated at 89.99 deg
        # because 90 exactly is the removable singularity; 1 - R there is
        # O(theta') and 0.0011 is what the closed form gives, so 2e-3 is the
        # sampled distance from the limit, not slack.
        check(1, 'exact Fresnel R(89.99 deg) -> 1  [%s]' % nm, ex[-1], 1.0,
              2e-3, 'R = 1 - O(90-theta); at 89.99 deg the exact value is 0.9989')
        # -- Brewster.  R_p vanishes identically at atan(n) -- the sharpest
        # closed-form test there is on the p branch, and the one thing an
        # unpolarised-only implementation cannot fake.
        cb = np.cos(np.arctan(n))
        check(1, 'R_p == 0 at Brewster atan(n)  [%s]' % nm,
              fresnel_exact(cb, n)[2], 0.0, 1e-20,
              'exact zero of the p amplitude; tolerance is float underflow')
        # -- s and p bracket the unpolarised mean everywhere. Exact ordering for
        # a real dielectric, so this is a boolean with no tolerance at all.
        check(1, 'R_s >= R_unpol >= R_p over 0-90 deg  [%s]' % nm,
              float(min(np.min(rs - ex), np.min(ex - rp)) >= -1e-15), 1.0, 0.0,
              'exact ordering for a real dielectric; boolean, no tolerance')
    # -- WHAT THE RENDERER ACTUALLY EVALUATES. `_fresnel_rough` at zero
    # unresolved variance is the file's smooth-interface Fresnel, so this
    # compares the curve the picture is made of against the exact equations,
    # written out separately at the top of this file. It used to ship Schlick
    # (1994) and it used to FAIL both rows: 0.0587 absolute at 83.8 deg (exact
    # 0.5163 against 0.5751) and 0.0452 over the frame's own incidence range,
    # i.e. +14.3% on the brightest term in the picture. The renderer now calls
    # the exact equations, so what is left is two implementations of one closed
    # form and the tolerance is TIGHTENED to double round-off, not relaxed.
    # The frame spans theta_v 11-52 deg above the water (render.py's own
    # measurement), i.e. 38-79 deg of incidence, so the comparison is made over
    # that range and over the full 0-90.
    n = IOR[1]
    for lo, hi, tag in ((0.0, 90.0, 'full 0-90 deg'), (38.0, 79.0, 'in-frame 38-79 deg')):
        th = np.linspace(np.deg2rad(lo), np.deg2rad(hi), 20001)
        ci = np.cos(th)
        ex = fresnel_exact(ci, n)[0]
        sch = R._fresnel_rough(ci, np.zeros_like(ci))[:, 1]
        i = int(np.argmax(np.abs(ex - sch)))
        check(1, 'render Fresnel vs exact Fresnel, max |dR| (%s)' % tag,
              float(np.abs(ex - sch).max()), 0.0, 1e-14,
              'two evaluations of one closed form; the only tolerance is double '
              'round-off. Schlick, which this replaced, read 0.0587 here')
        info(1, '  ... worst at (%s)' % tag,
             'theta %.1f deg: exact %.6f, render %.6f (%+.4f%%)'
             % (np.degrees(th[i]), ex[i], sch[i], 100 * (sch[i] / ex[i] - 1)),
             'where the two evaluations differ most')
    # -- AND THE GUARD THAT DOES NOT GO THROUGH THE SAME EXPRESSION. At Brewster
    # the p amplitude vanishes identically, so the unpolarised reflectance is
    # exactly half the s branch, and the s branch there collapses to a closed-form
    # NUMBER with no Fresnel evaluation in it at all:
    #     cos i = 1/sqrt(1+n^2), cos t = n/sqrt(1+n^2)
    #     r_s = (cos i - n cos t)/(cos i + n cos t) = (1 - n^2)/(1 + n^2)
    #     R(theta_B) = ((n^2 - 1)/(n^2 + 1))^2 / 2
    # This is the sharpest test of a reflectance model there is: it is a single
    # number, it needs no quadrature and no table, and an approximation cannot
    # hit it by construction -- Schlick gave 0.0306 against 0.0395 here, 22% low,
    # while passing every grazing-behaviour eyeball test. It is checked against
    # render.py's OWN `fresnel`, which is the thing the frame is drawn with.
    for c, nm in enumerate('RGB'):
        nn = IOR[c]
        cb = np.cos(np.arctan(nn))
        check(1, 'render fresnel at Brewster == ((n^2-1)/(n^2+1))^2/2  [%s]' % nm,
              float(R.fresnel(cb)[c]), 0.5 * ((nn ** 2 - 1) / (nn ** 2 + 1)) ** 2,
              1e-15, 'closed-form value of the unpolarised reflectance at the '
                     'zero of R_p; no integral, no table, one double ulp')
    check(1, 'render fresnel(1) == F0 (normal incidence)', R.fresnel(1.0), F0,
          1e-15, 'algebraic identity; the two are computed by different code')
    # -- TSUN, the sun's transmission into the water at 69 deg incidence.
    ex = 1.0 - fresnel_exact(R.cos_i, IOR[1])[0]
    check(1, 'TSUN (sun into water at 69 deg) vs exact Fresnel', R.TSUN, ex,
          1e-14, 'the file now evaluates the exact equations here too; double '
                 'round-off. Schlick read 0.8729 against 0.8774')
    # -- the diffuse Fresnel reflectance the wet-liner model integrates. The
    # file uses a 512-point midpoint rule in mu; a 200k-point rule is the same
    # integral converged.
    N = 200000
    mu = ((np.arange(N) + .5) / N)[:, None]
    ct = np.sqrt(np.maximum(1. - (1. - mu ** 2) / IOR[None] ** 2, 0.))
    rs = ((mu - IOR[None] * ct) / (mu + IOR[None] * ct)) ** 2
    rp = ((IOR[None] * mu - ct) / (IOR[None] * mu + ct)) ** 2
    check(1, 'R_EXT 512-pt rule vs converged quadrature',
          R.R_EXT, (2. * mu * .5 * (rs + rp)).mean(0), 2e-5,
          'midpoint rule on a smooth integrand converges as N^-2; 2e-5 is well '
          'above the 512-vs-200000 difference and below any physical effect')
    # -- reciprocity: R_int = 1 - (1 - R_ext)/n^2 is a two-line consequence of
    # the n^2 law for radiance. Independent check in tier 3 against Walsh.
    check(1, 'R_INT == 1 - (1 - R_EXT)/n^2', R.R_INT,
          1. - (1. - R.R_EXT) / IOR ** 2, 1e-15, 'algebraic identity')
    # -- the wet-albedo series is a geometric sum; check its two fixed points.
    check(1, 'wet_albedo(1) == 1 (no light lost on a perfect reflector)',
          R.wet_albedo(np.ones((1, 3)))[0], np.ones(3), 1e-12,
          'a = 1 must give a_wet = 1 identically; anything else leaks energy')
    check(1, 'wet_albedo(0) == R_EXT (bare interface over a black substrate)',
          R.wet_albedo(np.zeros((1, 3)))[0], R.R_EXT, 1e-15, 'algebraic limit')


# ====================================================== TIER 1: SNELL AND TIR
def tier1_snell(R):
    IOR = R.IOR
    th = np.linspace(0.0, np.deg2rad(89.9), 4001)
    for c, nm in enumerate('RGB'):
        n = IOR[c]
        # air -> water, the only direction the renderer currently uses
        ix = np.sin(th)
        iz = -np.cos(th)
        iy = np.zeros_like(ix)
        nx = np.zeros_like(ix)
        ny = np.zeros_like(ix)
        nz = np.ones_like(ix)
        tx, ty, tz = R.refract(ix, iy, iz, nx, ny, nz, 1.0 / n)
        # -- the refracted ray must be a unit vector. `refract` normalises by
        # construction only when it does not hit the k < 0 branch.
        check(1, 'refract() returns a unit vector, air->water  [%s]' % nm,
              float(np.abs(np.sqrt(tx ** 2 + ty ** 2 + tz ** 2) - 1).max()), 0.0,
              1e-12, 'algebraic identity; double round-off over 4001 angles')
        # -- Snell's law itself, measured off the returned direction.
        st = np.sqrt(tx ** 2 + ty ** 2)
        check(1, "Snell: sin(i) == n sin(t), air->water  [%s]" % nm,
              float(np.abs(np.sin(th) - n * st).max()), 0.0, 1e-12,
              'algebraic identity; double round-off')
        # -- round trip. Refracting the transmitted ray again with eta = n and
        # the same normal must recover the incident direction exactly. Same code
        # path the README's underwater camera will use, run in its safe regime.
        bx, by, bz = R.refract(tx, ty, tz, nx, ny, nz, n)
        check(1, 'refraction round trip air->water->air  [%s]' % nm,
              float(max(np.abs(bx - ix).max(), np.abs(bz - iz).max())), 0.0,
              1e-9, 'two square roots and a subtraction; the round trip is '
                    'ill-conditioned near grazing and 1e-9 is what that costs')
        # -- the critical angle. asin(1/n) is exact; the README quotes
        # 48.655 / 48.519 / 48.268 deg from these same three IORs.
        tc = np.degrees(np.arcsin(1.0 / n))
        check(1, 'critical angle asin(1/n)  [%s]' % nm, tc,
              [48.6551, 48.5190, 48.2683][c], 1e-3,
              'closed form against the README\'s own three figures, quoted to '
              '3 dp; 1e-3 deg is that quotation precision', 'deg')
        # -- AND THE TEST THAT MATTERS: nothing may transmit past it. Water->air
        # beyond asin(1/n) is total internal reflection, so refract() must return
        # either nothing or a flagged value. It used to return a vector of length
        # n*sin(i) > 1 lying in the surface plane -- a direction that is not a
        # direction, handed back silently. Unreachable from today's call sites
        # (all five pass eta = 1/n < 1), and exactly the branch the README's
        # underwater pass is written around.
        if c == 1:
            # an UPWARD ray inside the water meeting the surface from below: the
            # interface normal handed to refract() must oppose the ray, so -z.
            thi = np.linspace(np.arcsin(1.0 / n) + 1e-3, np.deg2rad(89.9), 500)
            ix2, iz2 = np.sin(thi), np.cos(thi)
            z = np.zeros_like(ix2)
            tx2, ty2, tz2 = R.refract(ix2, z, iz2, z, z, -np.ones_like(z), n)
            L = np.sqrt(tx2 ** 2 + ty2 ** 2 + tz2 ** 2)
            check(1, 'no transmission past the critical angle, water->air',
                  float(np.abs(L).max()), 0.0, 1e-9,
                  'past TIR the transmitted direction must be null or flagged; a '
                  'returned vector of any length is a direction that does not exist')
            check(1, 'is_tir() flags exactly those rays', float(R.is_tir(
                tx2, ty2, tz2).mean()), 1.0, 0.0,
                  'boolean over all 500 past-critical rays; no tolerance')
            # -- and BELOW the critical angle it must still transmit a real unit
            # vector, or "no transmission past TIR" could be passed by a function
            # that transmits nothing at all.
            thb = np.linspace(1e-3, np.arcsin(1.0 / n) - 1e-3, 500)
            ix3, iz3 = np.sin(thb), np.cos(thb)
            z3 = np.zeros_like(ix3)
            tx3, ty3, tz3 = R.refract(ix3, z3, iz3, z3, z3, -np.ones_like(z3), n)
            check(1, 'refract() still transmits a unit vector below TIR, water->air',
                  float(np.abs(np.sqrt(tx3 ** 2 + ty3 ** 2 + tz3 ** 2) - 1).max()),
                  0.0, 1e-12, 'algebraic identity over 500 sub-critical angles; '
                              'the other half of the branch, so the null return '
                              'cannot be passed by refusing to refract anything')
            # -- THE PREMISE-INDEPENDENT ONE. Where refract() stops returning a
            # direction and where the Fresnel reflectance reaches 1 are the SAME
            # angle, and they are computed by two functions that share no line of
            # code: one solves for cos t and tests its sign, the other forms the
            # s and p amplitude ratios. Bisect on refract()'s own output for the
            # onset -- no formula for it enters here -- and compare against the
            # first angle at which the exact water->air R is 1 to machine zero.
            lo_, hi_ = 0.0, np.pi / 2
            for _ in range(200):
                mid = 0.5 * (lo_ + hi_)
                t_ = R.refract(np.sin(mid), 0.0, np.cos(mid), 0.0, 0.0, -1.0, n)
                lo_, hi_ = (mid, hi_) if not R.is_tir(*t_) else (lo_, mid)
            fr_ = np.linspace(0.0, np.pi / 2, 4000001)
            # water -> air: the same equations with the index ratio inverted.
            rr_ = fresnel_exact(np.cos(fr_), 1.0 / n)[0]
            onset_f = float(fr_[int(np.argmax(rr_ >= 1.0 - 1e-15))])
            check(1, 'refract() TIR onset == the angle exact Fresnel R reaches 1',
                  np.degrees(0.5 * (lo_ + hi_)), np.degrees(onset_f), 1e-4,
                  'two functions with no shared line: a bisection on refract()\'s '
                  'own null return against a scan of the exact reflectance. '
                  '1e-4 deg is the 4M-point scan\'s own grid spacing', 'deg')
    # -- the penumbra compression factor. Differentiating Snell gives
    # dtheta_t/dtheta_i = cos(i)/(n cos(t)); render.py uses exactly that to
    # shrink the 0.53 deg sun disc on entry. Checked against a numerical
    # derivative of arcsin(sin(i)/n).
    ti = np.arcsin(R.cos_i)          # the file's own incidence, 69 deg from normal
    ti = np.arccos(R.cos_i)
    h = 1e-6
    num = (np.arcsin(np.sin(ti + h) / R.IOR[1])
           - np.arcsin(np.sin(ti - h) / R.IOR[1])) / (2 * h)
    check(1, 'penumbra compression dtheta_t/dtheta_i == cos i /(n cos t)',
          R.cos_i / (R.IOR[1] * R.cos_t), num, 1e-8,
          'central difference at h = 1e-6 has O(h^2) = 1e-12 truncation and '
          '~1e-10 of cancellation; 1e-8 covers both')
    # -- and the resulting figure the chapter quotes.
    pen = np.deg2rad(0.53) * (R.cos_i / (R.IOR[1] * R.cos_t)) * R.slant
    check(1, 'sun-disc penumbra on the 1.40 m bed', 1000 * pen, 6.8, 0.05,
          'the chapter and README both quote 6.8 mm to 1 dp; 0.05 mm is that '
          'quotation precision', 'mm')
    # -- the slant path is a geometric statement about the traced ray, so it is
    # checked against scene_hit rather than against its own formula.
    tx = np.array([R.sin_t * -R.SUN_DIR[0] / np.hypot(*R.SUN_DIR[:2])])
    ty = np.array([R.sin_t * -R.SUN_DIR[1] / np.hypot(*R.SUN_DIR[:2])])
    tz = np.array([-R.cos_t])
    _, _, _, sm, _ = R.scene_hit(np.array([1.0]), np.array([1.5]), tx, ty, tz)
    check(1, 'refracted slant to the bed, traced vs DEPTH/cos(t)',
          float(sm[0]), R.slant, 1e-9,
          'the traced distance and the closed form are the same geometry; any '
          'difference is a bug in scene_hit or in the slant', 'm')


# ================================================== TIER 1: BEER-LAMBERT
def tier1_beer(R):
    ABS = R.ABS
    # -- the law itself, over the renderer's own light-leg slant. render.py
    # applies exp(-ABS*sm) with sm from scene_hit, so this is the composed
    # quantity and not a restatement of the expression.
    T = np.exp(-ABS * R.slant)
    check(1, 'transmittance over the 1.96 m refracted slant',
          T, [0.5990, 0.9014, 0.9802], 5e-4,
          "render.py prints this triple to 3 dp; 5e-4 is that precision. It "
          "moved from (0.583, 0.899, 0.972) when ABS became the Pope & Fry band "
          "mean rather than a red point sample with a Smith & Baker blue")
    # -- multiplicativity. The renderer attenuates the light leg into the bed
    # map and the camera leg in water_shade, so the two-leg product must equal
    # the single-path law or the depth cue is wrong by a factor.
    L1, L2 = 1.96, 2.35
    check(1, 'Beer-Lambert composes: T(L1)T(L2) == T(L1+L2)',
          np.exp(-ABS * L1) * np.exp(-ABS * L2), np.exp(-ABS * (L1 + L2)),
          1e-15, 'exponential identity; double round-off only')
    # -- the slant path is longer than the depth by 1/cos(t), which is the whole
    # reason a low sun darkens a pool more than a high one.
    check(1, 'slant / depth == 1/cos(theta_t)', R.slant / R.DEPTH,
          1.0 / R.cos_t, 1e-14, 'algebraic identity')
    # -- the round trip the chapter quotes for a 1.5 m floor.
    check(1, 'chapter figure: exp(-a*3.0) at 610/550/450 nm',
          np.exp(-np.array([0.2644, 0.0565, 0.0092]) * 3.0),
          [0.45, 0.84, 0.97], 6e-3,
          'the chapter quotes these to 2 dp; 6e-3 is that rounding')
    # -- and the same law applied along a camera leg through the step region,
    # traced rather than assumed: the transmittance must fall monotonically with
    # the traced distance for every channel.
    x = np.full(64, 1.0)
    y = np.linspace(0.6, 3.4, 64)
    d = np.stack([np.full(64, 0.25), np.zeros(64), np.full(64, -1.0)], 1)
    d /= np.linalg.norm(d, axis=1)[:, None]
    _, _, _, sm, _ = R.scene_hit(x, y, d[:, 0], d[:, 1], d[:, 2])
    Tt = np.exp(-ABS[0] * sm)
    check(1, 'traced-path transmittance is monotone in path length',
          float(np.max(np.diff(Tt[np.argsort(sm)]))), 0.0, 1e-15,
          'exp(-aL) is strictly decreasing in L; any positive step is a sort or '
          'a path-length bug')


# ================================= TIER 1: A SINGLE SINUSOID'S CAUSTIC
# THE MOST VALUABLE TEST IN THE SUITE, because the caustic pass is the least
# checkable thing in the renderer: it has no closed form for the real field, so
# every diagnostic render.py prints about it is a statistic of its own output.
#
# For h = a sin(kx) under a vertical sun over a flat bed at depth d, the whole
# pass is a 1-D map with an exact Jacobian. A surface point x has slope
# h' = a k cos(kx), so the surface tilts by theta_n = atan(h'); the ray refracts
# to theta_t = asin(sin theta_n / n) from the normal, i.e. theta_n - theta_t from
# the vertical, and lands at
#       X(x) = x + d tan(theta_n - theta_t)
# with irradiance E(X) = sum over branches of 1/|dX/dx| and
#       dX/dx = 1 + d sec^2(theta_n - theta_t) (dtheta_n/dx)(1 - cos t_n/(n cos t_t))
# Folds are the zeros of that. Small-angle, dX/dx = 1 - d(1 - 1/n) a k^2 sin(kx),
# so a fold exists iff d(1 - 1/n) a k^2 >= 1 -- and since a k is the slope
# AMPLITUDE while field.py's s is the rms, which for one sinusoid is a k/sqrt(2),
# the file's F = 0.25 d s k reaches fold onset at F = 1/sqrt(2) = 0.7071 exactly.
# The 0.25 in that expression IS 1 - 1/n = 0.25076 for the green channel.
#
# The pass is exercised through render.py's own functions in the same order the
# module-level loop uses them: normal_from_grad -> refract -> scene_hit -> a
# density estimate on the receiver.
def _caustic_run(R, fld, a, k, nray=2_000_000, nbin=3000, x0=0.30, nper=4):
    lam = 2 * np.pi / k
    x1 = x0 + nper * lam
    x = x0 + (np.arange(nray) + 0.5) / nray * (x1 - x0)
    y = np.full(nray, 1.5)                      # clear of the step unit and bench
    gx = a * k * np.cos(k * (x - x0))
    nx, ny, nz = fld.normal_from_grad(gx, np.zeros_like(gx))
    tx, ty, tz = R.refract(np.float64(0.), np.float64(0.), np.float64(-1.),
                           nx, ny, nz, 1.0 / R.IOR[1])
    sid, u, v, sm, _ = R.scene_hit(x, y, tx, ty, tz)
    lo, hi = x0 - 0.3, x1 + 0.3
    h, edges = np.histogram(u, bins=nbin, range=(lo, hi))
    cell = (x1 - x0) / nray
    return (0.5 * (edges[1:] + edges[:-1]), h * cell / ((hi - lo) / nbin),
            x0, x1, int((sid != 0).sum()))


def _caustic_analytic(R, xs, a, k, x0):
    n, d = R.IOR[1], R.DEPTH
    hp = a * k * np.cos(k * (xs - x0))
    hpp = -a * k * k * np.sin(k * (xs - x0))
    thn = np.arctan(hp)
    tht = np.arcsin(np.sin(thn) / n)
    X = xs + d * np.tan(thn - tht)
    dthn = hpp / (1 + hp ** 2)
    dtht = dthn * np.cos(thn) / (n * np.cos(tht))
    J = 1 + d / np.cos(thn - tht) ** 2 * (dthn - dtht)
    return X, J


def tier1_caustic(R, fld):
    d, n = R.DEPTH, R.IOR[1]
    lam = 0.20
    k = 2 * np.pi / lam
    # -- the 0.25 in F = 0.25 d s k is 1 - 1/n, not a round number.
    check(1, "focusing constant 0.25 == 1 - 1/n (green)", 0.25, 1.0 - 1.0 / n,
          0.003, 'the chapter derives F = d(1-1/n)sk and writes 0.25 for the '
                 '0.25076 that 1.3348 gives; 0.003 is that stated rounding')
    check(1, 'field._focus(s,k) == 0.25 * 1.40 * s * k', fld._focus(0.05, k),
          0.25 * 1.40 * 0.05 * k, 1e-14, 'algebraic identity')
    # -- FOLD ONSET. The exact condition is min|dX/dx| = 0; sweep F and find
    # where the analytic Jacobian first touches zero, then confirm the traced
    # pass agrees about whether a fold is there.
    xs = np.linspace(0, lam, 200001)

    def minJ(F):
        s = F / (0.25 * d * k)
        return float(_caustic_analytic(R, xs, s * np.sqrt(2) / k, k, 0.0)[1].min())

    lo, hi = 0.50, 0.95                      # minJ(lo) > 0 > minJ(hi)
    for _ in range(60):                      # bisection on the sign of min J
        mid = 0.5 * (lo + hi)
        if minJ(mid) > 0:
            lo = mid
        else:
            hi = mid
    onset = 0.5 * (lo + hi)
    # The small-angle fold condition is d(1 - 1/n) a k^2 = 1. Written in the
    # file's F = 0.25 d s k with s = a k / sqrt(2) (the rms of one sinusoid),
    # that is F_onset = 0.25 / ((1 - 1/n) sqrt(2)) = 0.70473 -- and it would be
    # exactly 1/sqrt(2) = 0.70711 if the 0.25 in F really were 1 - 1/n. The
    # 0.34% between those two IS the chapter's rounding, so this row resolves it.
    check(1, 'fold onset for one sinusoid, in the file\'s F convention',
          onset, 0.25 / ((1.0 - 1.0 / n) * np.sqrt(2)), 5e-4,
          'the fold sits where the sinusoid crosses zero slope, so the '
          'small-angle expansion is exact AT the fold and the residual is second '
          'order in ak; 5e-4 is an order under the 0.34% this row separates')
    info(1, '  ... fold onset if 0.25 were exactly 1 - 1/n',
         '%.5f measured, %.5f for 1-1/n = %.5f, %.5f for a literal 0.25'
         % (onset, 0.25 / ((1 - 1 / n) * np.sqrt(2)), 1 - 1 / n, 1 / np.sqrt(2)),
         'the chapter writes F ~= 0.25 d s k and means d(1-1/n)sk')
    # -- SUB-CRITICAL: below onset there is one branch and E(X) = 1/|J| exactly.
    F = 0.35
    s = F / (0.25 * d * k)
    a = s * np.sqrt(2) / k
    c, E, x0, x1, off = _caustic_run(R, fld, a, k)
    xs = np.linspace(x0, x1, 400001)
    X, J = _caustic_analytic(R, xs, a, k, x0)
    m = (c > x0 + 0.15) & (c < x1 - 0.15)
    Ea = 1.0 / np.abs(np.interp(c, X, J))
    rel = float(np.abs(E[m] - Ea[m]).max() / Ea[m].mean())
    # A per-channel IOR swap (1.3320 vs 1.3400) moves 1 - 1/n by 0.45% and so
    # moves J by ~0.6% here; the measured binning noise of this estimator is
    # 0.06%. 0.5% is set to catch the first and sit ten times above the second.
    check(1, 'caustic irradiance vs analytic 1/|J| at F = 0.35 (no fold)',
          rel, 0.0, 0.005,
          'tight enough to catch a per-channel IOR swap (0.6% in J), 8x the '
          'measured 0.06% histogram noise', 'rel')
    check(1, 'caustic pass conserves flux at F = 0.35 (mean E == 1)',
          float(E[m].mean()), 1.0, 2e-3,
          'the receiver is flat and unbounded here, so the mean is exactly 1; '
          '2e-3 is the histogram edge effect over the masked window')
    check(1, 'no ray leaves the flat floor in the test strip', off, 0, 0,
          'the strip x 0.30-1.10, y 1.5 contains no wall, tread or riser')
    # -- PAST FOCUS: fold positions. Two folds per period, at the zeros of J.
    F = 1.5
    s = F / (0.25 * d * k)
    a = s * np.sqrt(2) / k
    c, E, x0, x1, _ = _caustic_run(R, fld, a, k)
    xs = np.linspace(x0, x1, 800001)
    X, J = _caustic_analytic(R, xs, a, k, x0)
    zc = np.flatnonzero(np.diff(np.sign(J)) != 0)
    Xf = np.sort(X[zc])
    m = (c > x0 + 0.15) & (c < x1 - 0.15)
    cm, Em = c[m], E[m]
    pk = cm[1:-1][(Em[1:-1] > Em[:-2]) & (Em[1:-1] > Em[2:]) & (Em[1:-1] > 3.0)]
    Xf = Xf[(Xf > x0 + 0.15) & (Xf < x1 - 0.15)]
    check(1, 'fold count at F = 1.5 (2 per period, 4 periods traced)',
          len(pk), len(Xf), 0, 'a fold is a zero of J; the two counts are the '
                              'same quantity computed two ways')
    if len(pk) == len(Xf):
        err = float(np.abs(np.sort(pk) - Xf).max())
        binw = float(c[1] - c[0])
        check(1, 'fold POSITION at F = 1.5, traced vs analytic', err, 0.0,
              2 * binw,
              'the density estimate quantises to %.2f mm bins, so the peak can '
              'only be located to +-1 bin; 2 bins is the tolerance' % (1000 * binw),
              'm')
    check(1, 'caustic pass conserves flux at F = 1.5 (mean E == 1)',
          float(Em.mean()), 1.0, 2e-3,
          'flux conservation is exact regardless of folding; same edge effect')
    info(1, 'peak irradiance at the F = 1.5 folds',
         '%.1f x ambient in a %.2f mm bin; the analytic value AT a fold is '
         'infinite (1/|J| -> inf), so the peak is set by the bin, not by physics'
         % (Em.max(), 1000 * (c[1] - c[0])),
         'a fold is a caustic singularity; only its POSITION is testable')
    # -- what the pass does NOT model, stated as a number rather than left out:
    # the rays start at z = 0, not at z = h(x). At F = 1.5 the surface is
    # +-6.1 mm, so every path length is off by up to 0.4%.
    info(1, 'entry-height approximation in the pass',
         'rays launched from z = 0, surface is +-%.1f mm -> path error <= %.2f%%'
         % (1000 * a, 100 * a / d), 'flat-interface approximation, not tested')


# ============================================== TIER 1: A FLAT SURFACE
def tier1_flat(R, fld):
    # Zero slope must give a mirror: one offset, no distortion, no structure.
    nray = 400000
    x = np.random.default_rng(3).uniform(0.3, 2.0, nray)
    y = np.random.default_rng(4).uniform(0.6, 3.4, nray)
    gx = np.zeros(nray)
    nx, ny, nz = fld.normal_from_grad(gx, gx)
    check(1, 'flat surface: normal_from_grad(0,0) == +z', [nx[0], ny[0], nz[0]],
          [0., 0., 1.], 1e-15, 'algebraic identity')
    tx, ty, tz = R.refract(-R.SUN_DIR[0], -R.SUN_DIR[1], -R.SUN_DIR[2],
                           nx, ny, nz, 1.0 / R.IOR[1])
    sid, u, v, sm, _ = R.scene_hit(x, y, tx, ty, tz)
    ok = sid == 0
    du, dv = u[ok] - x[ok], v[ok] - y[ok]
    off = np.hypot(du, dv)
    # -- the bed image is a pure translation: every ray moves by the same vector.
    check(1, 'flat surface: bed image is undistorted (one offset for all rays)',
          float(off.std()), 0.0, 1e-9,
          'a rigid translation has zero spread; 1e-9 m is float noise on a 1.37 m '
          'offset', 'm')
    check(1, 'flat surface: caustic offset == DEPTH * tan(theta_t)',
          float(off.mean()), R.DEPTH * np.tan(np.arccos(R.cos_t)), 1e-9,
          'closed form for a plane interface; float round-off', 'm')
    check(1, 'flat surface: caustic offset == 1.37 m (README figure)',
          float(off.mean()), 1.37, 0.005,
          'the README quotes 1.37 m to 2 dp; 5 mm is that precision', 'm')
    check(1, 'flat surface: offset lies along the sun azimuth',
          float(np.abs(du.mean() * -R.SUN_DIR[1] - dv.mean() * -R.SUN_DIR[0])
                / max(off.mean(), 1e-12)), 0.0, 1e-9,
          'the refracted ray stays in the plane of incidence; cross product is '
          'identically zero')
    # -- the caustic map is uniform. Splat the rays into the real map's texel
    # size and compare the variation with the Poisson noise of the estimator,
    # which is the only variation a mirror may have.
    NX, NY = 200, 100
    acc = np.zeros((NY, NX))
    R.splat(acc, u[ok], v[ok], np.ones(int(ok.sum())), R.X0, R.X1, R.Y0, R.Y1)
    # the window is the interior of where the rays actually landed, inset by two
    # texels so that no partly-covered edge texel enters the statistic
    iu = np.clip(((u[ok] - R.X0) / (R.X1 - R.X0) * NX).astype(int), 0, NX - 1)
    iv = np.clip(((v[ok] - R.Y0) / (R.Y1 - R.Y0) * NY).astype(int), 0, NY - 1)
    sub = acc[iv.min() + 2:iv.max() - 1, iu.min() + 2:iu.max() - 1]
    poisson = 1.0 / np.sqrt(max(sub.mean(), 1e-9))
    check(1, 'flat surface: caustic map is uniform to within shot noise',
          float(sub.std() / sub.mean()), 0.0, 2.0 * poisson,
          'the only structure a mirror may show is the estimator\'s own Poisson '
          'noise, 1/sqrt(N per texel) = %.3f; 2x that is the tolerance' % poisson,
          'rel')
    # -- the slope ledger. Zero field, zero rms, in both of the file's routes to
    # the number, and no variance removed at any footprint.
    check(1, 'flat surface: rms_slope(0,0) == 0', fld.rms_slope(gx, gx), 0.0, 0.0,
          'exact')
    check(1, 'flat surface: _plane_rms([0,...]) == 0', fld._plane_rms(np.zeros(8)),
          0.0, 0.0, 'exact')
    check(1, 'unfiltered band_weight == 1 at every k',
          float(np.abs(fld.band_weight(np.logspace(0, 3, 50), None) - 1).max()),
          0.0, 0.0, 'fp = None must be the identity, bit for bit')
    # -- and the footprint filter's own one-sentence claim: a component is half
    # gone when the footprint reaches half its wavelength.
    kk = 2 * np.pi / np.array([0.02, 0.05, 0.20, 0.50])
    check(1, 'band_weight == 1/2 at fp = lambda/2 (the derived calibration)',
          [float(fld.band_weight(kx, np.pi / kx)) for kx in kk],
          [0.5] * 4, 1e-7,
          'the calibration is defined by this identity, so the only tolerance is '
          'arithmetic: _fp_var casts the footprint to float32, which is 1e-8 here')
    check(1, 'half_footprint(k) == lambda/2',
          fld.half_footprint(kk), np.pi / kk, 1e-15, 'algebraic identity')


# ================================================== TIER 1: ENERGY
def tier1_energy(R):
    # -- the disc lobe. n = 2/theta^2 - 1 is chosen so that a cos^n lobe's
    # hemisphere integral 2pi/(n+1) equals the sun's own solid angle, which is
    # what makes peak, width and flux land on the sun together.
    check(1, 'cos^N_DISC solid angle == Omega_sun', 2 * np.pi / (R.N_DISC + 1),
          R.OMEGA_SUN, 1e-18, 'the identity N = 2/theta^2 - 1 is defined by this')
    check(1, 'Omega_sun == pi theta_s^2', R.OMEGA_SUN,
          np.pi * R.THETA_SUN ** 2, 1e-20, 'algebraic identity')
    check(1, 'L_sun * Omega_sun == E_sun (normal irradiance)',
          R.L_SUN * R.OMEGA_SUN, R.E_SUN, 1e-12,
          'the definition of radiance for a small source; float round-off')
    check(1, 'E_sun == pi * SUN_COL', R.E_SUN, np.pi * R.SUN_COL, 1e-15,
          'shade() uses SUN_COL as E/pi; this is that convention, restated')
    # -- the flux the sky() function actually delivers, including the 1/1.15 the
    # lobes carry and the 1.15 sky() multiplies back. If that bookkeeping were
    # wrong the reflected sun would be off by 15% and nothing else would notice.
    disc = R.SKY_LOBE[0]
    flux_disc = disc[0] * disc[2] * 1.15 * 2 * np.pi / (disc[1] + 1)
    check(1, 'disc lobe flux, as shipped, == the direct beam', flux_disc,
          R.E_SUN, 1e-9,
          'exact by construction; 1e-9 catches a lost or doubled 1.15 and '
          'nothing else', rel=True)
    # -- the peak, measured by calling sky() along the sun direction rather than
    # by recomputing the amplitude.
    got = R.sky(np.array([R.SUN_DIR[0]]), np.array([R.SUN_DIR[1]]),
                np.array([R.SUN_DIR[2]]))[0]
    hor = R.SKY_HOR * (1 - np.clip(R.SUN_DIR[2], 0, 1) ** .55) \
        + R.SKY_TOP * np.clip(R.SUN_DIR[2], 0, 1) ** .55
    peak = got - hor * 1.15 - R.L_AURE * 1.15 * disc[0] / disc[0]
    check(1, 'sky() peak radiance on axis == L_sun (+ aureole)',
          float((got[1] - hor[1] * 1.15) / R.L_SUN[1]),
          1.0 + float(R.L_AURE[1] / R.L_SUN[1]), 1e-6,
          'evaluated through sky() itself, so it also checks _lobe_shape\'s '
          'cov = None path is the identity', rel=True)
    # -- the aureole's flux is not free either: for a Rayleigh atmosphere it is
    # E m tau / 8, so the total is (1 + m tau / 8) of the beam.
    tot = sum(amp * c * 1.15 * 2 * np.pi / (nn + 1) for amp, nn, c in R.SKY_LOBE)
    check(1, 'total lobe flux / direct beam == 1 + m tau_R / 8',
          tot / R.E_SUN, 1.0 + R.AIRMASS * R.TAU_R / 8.0, 1e-12,
          'closed form for a cos^2 Rayleigh lobe of amplitude E m tau (3/4)/(4pi); '
          'float round-off')
    check(1, 'total lobe flux / direct beam (green) == 1.035', float(tot[1] / R.E_SUN[1]),
          1.035, 5e-4, 'render.py prints 1.035 to 3 dp')
    # -- the sun colour read back as Rayleigh extinction. This is the file's own
    # claim; the test is that _tau_rayleigh is the standard form, checked against
    # the 0.008569 lam^-4 law it says it is.
    lam = np.array([0.620, 0.545, 0.460])
    check(1, 'Rayleigh tau is the Hansen & Travis 1974 form', R._tau_rayleigh(lam),
          0.008569 * lam ** -4 * (1 + 0.0113 * lam ** -2 + 0.00013 * lam ** -4),
          1e-15, 'algebraic identity with the published coefficients')
    tr = np.exp(-R.AIRMASS * R.TAU_R)
    check(1, 'exp(-m tau)/red reproduces SUN_COL\'s colour', tr / tr[0],
          R.SUN_COL / R.SUN_COL[0], 1e-3,
          'render.py claims one part in 1e4 on two channels; 1e-3 is ten times '
          'looser and still fails if the air mass moves by 0.02')
    # -- the riser gather's closure. (1/pi) INT L cos dw over the downgoing
    # quarter-sphere is exactly 1/2 for a uniform L, and _ris_closure is the
    # truncated form of the same integral.
    check(1, 'riser gather closure over the full range == 0.500',
          float(R._ris_closure(0.12, 1e-9, 1e9)), 0.5, 1e-6,
          'closed form; the range is truncated at 1e-9 and 1e9 so the residual '
          'is the arctan\'s own limit, ~1e-9')
    tr = float(np.mean(R._ris_closure(np.linspace(R.RIS_HMIN, 0.24, 64),
                                      R.RIS_D0, R.RIS_D1)))
    check(1, 'riser gather closure over the SHIPPED range 6 mm - 120 m',
          tr, 0.498, 2e-3,
          'render.py prints 0.498; 2e-3 is the spread over the riser heights '
          'this averages')


# ========================================== TIER 2: PUBLISHED MEASUREMENT
# Pure-water absorption, a_w, in m^-1. Both tables are transcribed from the
# Oregon Medical Laser Center compendium (omlc.org/spectra/water/abs/), which
# reproduces the authors' published values; the source files there are in cm^-1
# and are multiplied by 100 here.
#
#   Pope & Fry (1997), Appl. Opt. 36(33) 8710-8723 -- integrating-cavity
#   measurement of PURE water, 380-700 nm. This is the modern standard and it is
#   the reference the chapter's own bibliography names.
#
#   Smith & Baker (1981), Appl. Opt. 20(2) 177-184 -- the "clearest natural
#   waters". Retained here because it is the OTHER candidate for the constant in
#   dispute, and because identifying which table a number came from is the whole
#   of the resolution.
POPE_FRY_1997 = {
    400: 0.00663, 405: 0.00530, 410: 0.00473, 415: 0.00444, 420: 0.00454,
    425: 0.00478, 430: 0.00495, 435: 0.00530, 440: 0.00635, 445: 0.00751,
    450: 0.00922, 455: 0.00962, 460: 0.00979, 465: 0.01011, 470: 0.01060,
    475: 0.01140, 480: 0.01270, 485: 0.01360, 490: 0.01500, 495: 0.01730,
    500: 0.02040, 505: 0.02560, 510: 0.03250, 515: 0.03960, 520: 0.04090,
    525: 0.04170, 530: 0.04340, 535: 0.04520, 540: 0.04740, 545: 0.05110,
    550: 0.05650, 555: 0.05960, 560: 0.06190, 565: 0.06420, 570: 0.06950,
    575: 0.07720, 580: 0.08960, 585: 0.11000, 590: 0.13510, 595: 0.16720,
    600: 0.22240, 605: 0.25770, 610: 0.26440, 615: 0.26780, 620: 0.27550,
    625: 0.28340, 630: 0.29160, 635: 0.30120, 640: 0.31080, 645: 0.32500,
    650: 0.34000, 655: 0.37100, 660: 0.41000, 665: 0.42900, 670: 0.43900,
    675: 0.44800, 680: 0.46500, 685: 0.48600, 690: 0.51600, 695: 0.55900,
    700: 0.62400,
}
SMITH_BAKER_1981 = {
    400: 0.0171, 410: 0.0162, 420: 0.0153, 430: 0.0144, 440: 0.0145,
    450: 0.0145, 460: 0.0156, 470: 0.0156, 480: 0.0176, 490: 0.0196,
    500: 0.0257, 510: 0.0357, 520: 0.0477, 530: 0.0507, 540: 0.0558,
    550: 0.0638, 560: 0.0708, 570: 0.0799, 580: 0.1080, 590: 0.1570,
    600: 0.2440, 610: 0.2890, 620: 0.3090, 630: 0.3190, 640: 0.3290,
    650: 0.3490, 660: 0.4000, 670: 0.4300, 680: 0.4500, 690: 0.5000,
    700: 0.6500,
}


def _tab(t, w):
    ks = np.array(sorted(t))
    return np.interp(np.asarray(w, float), ks, np.array([t[k] for k in ks]))


def tier2_absorption(R):
    nm = 1000.0 * R.LAM                                  # 620 / 545 / 460
    pf = _tab(POPE_FRY_1997, nm)
    sb = _tab(SMITH_BAKER_1981, nm)
    # -- POINT VALUES at the file's own three nominal wavelengths.
    # Tolerance: 15%. Justification, and it is not the disagreement -- it is the
    # sum of the two things that legitimately move this number.
    #   (a) delta vs band. The file's own doctrine is that a channel is a BAND,
    #       not a wavelength, and a is not linear over a band: the band mean and
    #       the point value differ by 5% (red), 4% (green), 4% (blue). Both are
    #       defensible readings of the same measurement.
    #   (b) the published spread. Pope & Fry and the other modern integrating-
    #       cavity work agree to a few percent in the green and red.
    # 15% covers both with room to spare, and is still four times smaller than
    # the blue disagreement it reports.
    check(2, 'ABS vs Pope & Fry 1997 at 620/545/460 nm', R.ABS / pf,
          [1., 1., 1.], 0.15,
          'covers the delta-vs-band ambiguity (<=5%) and the published spread; '
          'chosen before the measurement, not after')
    info(2, '  ... Pope & Fry point values at 620/545/460 nm', np.round(pf, 5),
         'the file states these three wavelengths itself')
    info(2, '  ... ABS / Pope & Fry point values, per channel',
         np.round(R.ABS / pf, 4),
         'ABS is the BAND MEAN of this same table, so the residual here is the '
         'curvature of a(lambda) across each band and nothing else')
    info(2, '  ... ABS / Smith & Baker 1981 at the same three', np.round(R.ABS / sb, 4),
         'the file used to ship 0.0145 in blue, Smith & Baker\'s 450 nm value '
         'exactly; it no longer does')
    # -- BAND INTEGRALS over the file's own Voronoi cells. This is the reading
    # the file's own band doctrine demands, and it is the one render.py now
    # ships: `a` averaged over 582.5-657.5 / 502.5-582.5 / 417.5-502.5 nm, the
    # same cells every other spectral quantity in the renderer is sampled
    # through. The tolerance stays 15% -- it was chosen before the measurement
    # and has not been touched -- but the residual it now covers is a transcribed
    # constant against a trapezoid of the published table, ~2e-4 relative.
    band = []
    for lo, hi in np.sort(R.BAND, axis=1) * 1000.0:
        xs = np.linspace(lo, hi, 801)
        band.append(float(np.trapezoid(_tab(POPE_FRY_1997, xs), xs) / (hi - lo)))
    band = np.array(band)
    check(2, 'ABS vs Pope & Fry band-integrated over the file\'s own BAND cells',
          R.ABS / band, [1., 1., 1.], 0.15, 'same justification as above')
    info(2, '  ... Pope & Fry averaged over BAND (582-658, 502-582, 418-502 nm)',
         np.round(band, 5), 'the reading the file\'s own band model asks for, '
                            'and the one it now ships')
    info(2, '  ... ABS - band mean, per channel, relative',
         np.round(R.ABS / band - 1.0, 6),
         'this is transcription error only; the two are the same integral')
    # -- the chapter's triple, at ITS stated wavelengths. NOT an alternative
    # water: the same Pope & Fry table point-sampled at 610/550/450 instead of
    # averaged over the renderer's bands. Both are checked against the table, so
    # neither can drift without a row moving.
    ch = np.array([0.2644, 0.0565, 0.00922])
    check(2, 'chapter a_water (0.2644, 0.0565, 0.00922) vs Pope & Fry at 610/550/450',
          ch / _tab(POPE_FRY_1997, [610, 550, 450]), [1., 1., 1.], 0.02,
          'the chapter states these ARE Pope & Fry at those wavelengths, so the '
          'only tolerance is its own 3-significant-figure quotation')
    rm = np.array([0.2644, 0.0565, 0.00922])
    check(2, 'README a_water vs the chapter it quotes',
          rm / ch, [1., 1., 1.], 0.02,
          'the README says it is quoting the chapter; 2% is its own rounding')
    # -- THE IDENTIFICATION THAT SETTLED THE DISPUTE, now asserted the other way
    # round. The file used to ship ABS[2] = 0.0145, which is Smith & Baker (1981)
    # at 450 nm to the digit -- the wrong paper at the wrong wavelength, 48%
    # above Pope & Fry, in a project whose provenance file bans Smith & Baker for
    # blue by name (that era's blue carries scattering from natural water). This
    # row exists so that value cannot come back unnoticed.
    _dsb = float(np.min(np.abs(R.ABS[2] / np.array(
        [SMITH_BAKER_1981[w] for w in (440, 450, 460)]) - 1.0)))
    check(2, 'ABS blue is Pope & Fry, not Smith & Baker 1981',
          float(_dsb > 0.10 and abs(R.ABS[2] / band[2] - 1.0) < 0.05), 1.0, 0.0,
          'boolean, no tolerance: blue must sit within 5% of the Pope & Fry band '
          'mean AND more than 10%% from every Smith & Baker value in 440-460 nm')
    info(2, '  ... ABS blue against the two candidate tables',
         'Pope & Fry band mean %+.2f%%, nearest Smith & Baker 440-460 %+.1f%%'
         % (100 * (R.ABS[2] / band[2] - 1), 100 * _dsb),
         'the identification that settled the dispute, kept as a regression')
    # -- and what the correction was worth, so the severity is a number.
    old = np.array([0.2750, 0.0546, 0.0145])
    over = np.exp(-old * 2 * R.slant) / np.exp(-R.ABS * 2 * R.slant)
    info(2, '  ... what the old triple cost on the 3.92 m down-and-back path',
         'transmittance ratio %s (blue was %.1f%% dark, red %.1f%%)'
         % (np.round(over, 4), 100 * (1 - over[2]), 100 * (1 - over[0])),
         'small here; the README\'s underwater 8 m view multiplies it by 4')


def tier2_coxmunk(R, fld):
    # Cox & Munk (1954), JOSA 44(11) 838-850, and the relation as the chapter
    # carries it:
    #     sigma_c^2 = 0.003 + 1.92e-3 W      (crosswind, per-axis)
    #     sigma_u^2 = 0.000 + 3.16e-3 W      (upwind, per-axis)
    #     s^2       = 0.003 + 5.12e-3 W      (total mean-square slope)
    # with W the wind at 12.5 m, valid 1-14 m/s, and sigma_u^2/sigma_c^2
    # averaging 1.34 over the range 1.0-1.8.
    xs = np.linspace(0.4, 7.6, 600)
    ys = np.linspace(0.4, 3.6, 300)
    gx, gy = fld.grad_grid(xs, ys)
    mss = float(np.mean(gx ** 2 + gy ** 2))
    # -- the LEVEL. Cox & Munk is a sea, and a 1.4 m pool is calmer than the
    # calmest sea they photographed, so the honest test is a bracket, not an
    # equality: the basin must sit between the W -> 0 intercept (a dead-flat
    # sea still has mss 0.003 from swell) and the bottom of their validity, 1 m/s.
    between(2, 'basin total mss inside Cox & Munk [W=0, W=1 m/s]', mss,
            0.003, 0.003 + 5.12e-3 * 1.0,
            'C&M is fitted for 1-14 m/s; below that only the bracket is '
            'defensible, and it is the only external check on this level there is')
    info(2, '  ... implied Cox & Munk wind speed',
         '%.2f m/s (below their 1 m/s validity floor)' % ((mss - 0.003) / 5.12e-3),
         'a pool is calmer than any sea they measured')
    info(2, '  ... basin total rms slope s = sqrt(mss)', round(float(np.sqrt(mss)), 4),
         'against the file\'s own far-field 0.058 and near-field 0.122')
    # -- the SHAPE. C&M's Gram-Charlier fit is a Gaussian with small peakedness
    # corrections, c40 = 0.40 +- 0.23 upwind and c04 = 0.23 +- 0.41 crosswind,
    # i.e. excess kurtosis under about 1. Measured on the FAR patch, which is
    # the only part of this basin that is a homogeneous wave field at all -- the
    # jet region is a localised high-variance patch and is leptokurtic by
    # construction, which is physics and not a defect.
    fx = np.linspace(2.0, 4.0, 256)
    fy = np.linspace(1.0, 3.0, 256)
    fgx, fgy = fld.grad_grid(fx, fy)
    for a, tag in ((fgx.ravel(), 'x'), (fgy.ravel(), 'y')):
        ek = float(np.mean((a - a.mean()) ** 4) / np.mean((a - a.mean()) ** 2) ** 2 - 3)
        between(2, 'far-patch slope excess kurtosis, %s axis, vs Cox & Munk' % tag,
                ek, -0.5, 1.5,
                'C&M peakedness c40 = 0.40 +- 0.23; +-3 sigma is [-0.29, 1.09] '
                'and this widens it to [-0.5, 1.5]')
    # -- ANISOTROPY. Reported, not asserted: this basin's directionality is set
    # by a jet and by wall reflections, not by wind, so C&M's wind-sea envelope
    # is the wrong yardstick for the total. It is the right one for the WIND
    # band alone, which is stated below as a number.
    C = np.cov(np.stack([fgx.ravel(), fgy.ravel()]))
    w = np.linalg.eigvalsh(C)
    info(2, 'far-patch slope anisotropy (major/minor eigenvalue)',
         round(float(w[1] / w[0]), 3),
         'C&M report sigma_u^2/sigma_c^2 = 1.34, range 1.0-1.8, for a wind sea')
    Wb = fld.WIND
    cw = np.zeros((2, 2))
    for i in range(len(Wb['kx'])):
        kk = np.hypot(Wb['kx'][i], Wb['ky'][i])
        a = Wb['amp'][i] * kk
        u = np.array([Wb['kx'][i], Wb['ky'][i]]) / kk
        cw += 0.5 * a * a * np.outer(u, u)
    ww = np.linalg.eigvalsh(cw)
    # The band is drawn from a Gaussian of spread 45 deg about one azimuth, and
    # for that the ENSEMBLE ratio is (1+e^-2s^2)/(1-e^-2s^2) with s in radians --
    # a closed form, so the drawn realisation can be checked against the design.
    sg = np.deg2rad(45.0)
    ens = (1 + np.exp(-2 * sg ** 2)) / (1 - np.exp(-2 * sg ** 2))
    info(2, 'WIND band anisotropy: drawn 20 components / design / Cox & Munk',
         '%.3f drawn, %.3f for a 45 deg spread, 1.0-1.8 measured at sea'
         % (ww[1] / ww[0], ens),
         'the DESIGN value already sits outside the Cox & Munk envelope')
    check(2, 'WIND band total mss == WIND_RMS^2', float(cw.trace()),
          float(fld.WIND_RMS) ** 2, 1e-12,
          'the band is normalised to this by _plane_rms; an identity, and the '
          'guard that the tensor and the scalar use one convention')


def tier2_jet(fld, wkm):
    # A submerged round turbulent jet in the self-similar region:
    #     r_1/2(s) = S s        S = 0.094
    #     U_c(s)   = B U0 d / s B = 5.8
    # Pope, "Turbulent Flows" (CUP 2000), Sec. 5.4.2 and Table 5.1; the
    # experimental spread across the literature is roughly S = 0.086-0.096 and
    # B = 5.7-6.1 (Wygnanski & Fiedler 1969, Hussein, Capp & George 1994).
    J = wkm.Jet(fld.JET_XY[0], fld.JET_XY[1], depth=fld.JET_H,
                tilt_deg=np.degrees(fld.JET_TILT), az_deg=np.degrees(fld.JET_AZ),
                d=fld.D_NOZZLE, dp_bar=fld.DP_BAR, cd=fld.CD,
                S=fld.S_SPREAD, B=fld.B_DECAY)
    # measured beyond s = h/sin(tilt), where the tilted axis has reached the
    # surface, so that the surface profile is the axis profile
    s0 = 2.0
    p = J.p + s0 * J.ax
    perp = np.array([-J.ax[1], J.ax[0]])
    r = np.linspace(0, 0.4, 40001)
    U = np.hypot(*J.drift(p[0] + r * perp[0], p[1] + r * perp[1]))
    rh = float(r[np.argmin(np.abs(U - 0.5 * U[0]))])
    check(2, 'jet half-width measured off drift(): r_1/2 / s == S', rh / s0,
          0.094, 1e-3,
          'the constant is the literature value; 1e-3 is the resolution of the '
          '10 um radial sweep used to find the half-velocity point')
    between(2, 'jet spreading rate S vs the turbulence literature', rh / s0,
            0.086, 0.096,
            'the experimental range across Wygnanski & Fiedler and Hussein et al.')
    B = float(U[0] * s0 / (J.U0 * J.d))
    check(2, 'jet centreline decay measured off drift(): U_c s/(U0 d) == B', B,
          5.8, 1e-3, 'closed form of the same expression; float noise only')
    between(2, 'jet decay constant B vs the turbulence literature', B, 5.7, 6.1,
            'the experimental range in the same sources')
    # -- the radial profile's shape: U/U_c = exp(-ln2 (r/r_half)^2) must give
    # exactly 1/2 at r_half, which is the definition and therefore a real check
    # that the code's exponent is ln 2 and not 1 or 1/2.
    check(2, 'jet radial profile == 1/2 at r_1/2', float(np.interp(rh, r, U) / U[0]),
          0.5, 1e-4, 'the definition of the half-width; 1e-4 is the sweep '
                     'resolution again')
    # -- MOMENTUM, the one exact invariant of a round jet, as an independent
    # constraint on the (S, B) pair. For the Gaussian profile,
    #   M/rho = INT U^2 2 pi r dr = pi Uc^2 r_1/2^2 / (2 ln 2) = pi B^2 U0^2 d^2 S^2/(2 ln2)
    # which is s-independent (so the pair is self-consistent) and equals
    # 2 B^2 S^2 / ln 2 times the nozzle's own pi U0^2 d^2/4.
    M = 2 * fld.B_DECAY ** 2 * fld.S_SPREAD ** 2 / np.log(2.0)
    between(2, 'jet momentum flux / nozzle momentum flux (Gaussian profile)',
            M, 0.75, 1.05,
            'momentum is conserved exactly; a Gaussian fit to a real jet '
            'recovers 85-95% of it because the profile has non-Gaussian tails '
            'and the turbulent normal stresses are omitted. Outside [0.75, 1.05] '
            'the pair would not describe a jet at all')
    info(2, '  ... measured momentum ratio', round(float(M), 4),
         'the 14% deficit is the known Gaussian-profile / normal-stress gap')
    # -- turbulence intensity on the axis, u'/U_c.
    between(2, "jet axial turbulence intensity u'/U_c", float(fld.TURB_INT),
            0.20, 0.30,
            'measured 0.25-0.28 on the centreline of a self-similar round jet '
            '(Wygnanski & Fiedler 1969); the file uses 0.25')


def tier2_dispersion(fld, wkm):
    g, sig, rho = 9.81, fld.SIGMA_W, 1000.0
    # -- surface tension of clean water at 20 C is 72.8 mN/m (CRC Handbook).
    check(2, 'surface tension 0.0728 N/m (clean water, 20 C)', sig, 0.0728,
          1e-12, 'the published value at 20 C to 3 significant figures')
    # -- the capillary-gravity dispersion relation, against the closed form.
    k = np.logspace(0, 4, 4001)
    om, cg, al = fld._disp(k)
    check(2, 'field._disp omega == sqrt(gk + sigma k^3/rho)',
          float(np.abs(om / np.sqrt(g * k + sig / rho * k ** 3) - 1).max()), 0.0,
          1e-12, 'algebraic identity; note _disp hard-codes 0.0728 and 9.81 '
                 'rather than reading SIGMA_W', rel=False)
    # -- the group velocity must be domega/dk, checked numerically.
    h = k * 1e-6
    num = (fld._disp(k + h)[0] - fld._disp(k - h)[0]) / (2 * h)
    check(2, 'field._disp group velocity == domega/dk',
          float(np.abs(cg / num - 1).max()), 0.0, 1e-8,
          'central difference with a relative step of 1e-6; O(h^2) truncation is '
          '1e-12 and cancellation is ~1e-9')
    # -- THE MINIMUM PHASE SPEED. c(k) = sqrt(g/k + sigma k/rho) has a minimum
    # at k = sqrt(rho g/sigma), where c = (4 g sigma/rho)^(1/4). The published
    # figures for clean water at 20 C are 23.1 cm/s at 1.71 cm.
    kk = np.logspace(1, 4, 2000001)
    c = np.sqrt(g / kk + sig * kk / rho)
    i = int(np.argmin(c))
    check(2, 'minimum phase speed c_min = (4 g sigma/rho)^(1/4)', float(c[i]),
          fld.C_MIN, 1e-6,
          'the numeric minimum over a 2e6-point log sweep is within 1e-9 of the '
          'closed form; 1e-6 is the sweep resolution', 'm/s')
    check(2, 'c_min == 0.231 m/s (published, clean water 20 C)', fld.C_MIN,
          0.231, 5e-4, 'the textbook value is quoted to 3 dp', 'm/s')
    check(2, 'wavelength at c_min == 2 pi sqrt(sigma/rho g)',
          2 * np.pi / kk[i], fld.LAM_MIN, 1e-6,
          'closed form vs the same sweep', 'm')
    check(2, 'lambda at c_min == 17.1 mm (published)', 1000 * fld.LAM_MIN, 17.1,
          0.05, 'the textbook value is quoted to 1 dp', 'mm')
    check(2, 'wake.py C_MIN == field.py C_MIN', wkm.C_MIN, fld.C_MIN, 1e-15,
          'two modules, one constant; a divergence here is a silent fork')
    # -- the capillary length and the meniscus climb it sets.
    check(2, 'capillary length sqrt(sigma/rho g) == 2.72 mm',
          1000 * np.sqrt(sig / (rho * g)), 2.72, 0.005,
          'closed form; the README quotes 2.72 mm to 2 dp', 'mm')
    # -- the stationary-wave fan. cos(psi_max) = c_min/U is exact for a steady
    # pattern in a current U, and it is what fixes the +-78 deg wavevector fan.
    U = 4.6 * fld.C_MIN
    check(2, 'stationary wavevector fan arccos(c_min/U) at Froude 4.6',
          np.degrees(np.arccos(fld.C_MIN / U)), 77.44, 0.02,
          'closed form; render.py prints 78 deg to the nearest degree, so this '
          'is checked against the unrounded value', 'deg')


# ============================================ TIER 3: INDEPENDENT METHOD
def tier3_refl_ellipse(R, fld):
    # The reflected-slope ellipse C = J SIGMA J^T with J = diag(-2, -2 cos tv)
    # is a FIRST-ORDER result. Monte-Carlo the exact reflection instead: draw
    # slopes from SIGMA, build the exact normal, reflect exactly, and measure the
    # covariance of the reflected directions in the same frame.
    rng = np.random.default_rng(20260811)
    tv = np.deg2rad(33.35)                    # the camera's own depression
    dvec = np.array([[np.sin(tv), 0.0, -np.cos(tv)]])
    sxx, syy, sxy = 0.0025, 0.0009, 0.0006    # rms 0.05 -- the basin's own scale
    z1 = np.zeros(1)
    o1 = np.ones(1)
    ndv = np.array([np.cos(tv)])
    # R = -v + 2(n.v)n with v = -dvec and n = +z
    rx = np.array([np.sin(tv)])
    rz = np.array([np.cos(tv)])
    u1, u2, c11, c12, c22, a = R._refl_ellipse(
        dvec, z1, z1, o1, ndv, rx, z1, rz,
        np.array([sxx]), np.array([syy]), np.array([sxy]))
    N = 400000
    dd = rng.multivariate_normal([0, 0], [[sxx, sxy], [sxy, syy]], N)
    mx, my, mz = fld.normal_from_grad(dd[:, 0], dd[:, 1])
    vx, vy, vz = -dvec[0, 0], -dvec[0, 1], -dvec[0, 2]
    nd = mx * vx + my * vy + mz * vz
    Rx, Ry, Rz = -vx + 2 * nd * mx, -vy + 2 * nd * my, -vz + 2 * nd * mz
    Rh = np.array([rx[0], 0.0, rz[0]])
    sh = np.cross([vx, vy, vz], [0, 0, 1.0])
    sh /= np.linalg.norm(sh)
    eh = np.cross(Rh, sh)
    p1 = Rx * eh[0] + Ry * eh[1] + Rz * eh[2]
    p2 = Rx * sh[0] + Ry * sh[1] + Rz * sh[2]
    C = np.cov(np.stack([p1, p2]))
    # The linearisation drops O(slope^2), so at rms 0.05 the expected error is a
    # few times 0.05^2 = 2.5e-3 relative -- percent-level. 6% is set from that
    # and from the Monte-Carlo's own 1/sqrt(2N) = 0.11% on a variance.
    check(3, 'reflected-slope ellipse C11 vs 400k Monte-Carlo', C[0, 0] / c11[0],
          1.0, 0.06,
          'the analytic form is first order in slope; at rms 0.05 the dropped '
          'term is percent-level, and the MC has 0.1% of its own')
    check(3, 'reflected-slope ellipse C22 vs 400k Monte-Carlo', C[1, 1] / c22[0],
          1.0, 0.06, 'same')
    check(3, 'reflected-slope ellipse C12 vs 400k Monte-Carlo', C[0, 1] / c12[0],
          1.0, 0.06, 'same; the cross term also fixes the sign convention')
    info(3, '  ... measured ratios (MC / analytic)',
         np.round([C[0, 0] / c11[0], C[0, 1] / c12[0], C[1, 1] / c22[0]], 4),
         'all three below 1: the linearisation slightly over-widens the lobe')
    # -- the anisotropy the derivation exists to produce: 1/cos(tv).
    check(3, 'ellipse stretch along the view azimuth == 1/cos(theta_v)',
          np.sqrt(c11[0] / c22[0]) / np.sqrt(sxx / syy), 1.0 / np.cos(tv), 1e-12,
          'algebraic consequence of J = diag(-2, -2 cos tv); float round-off')


# ================================== TIER 1: THE INTERFACE, AS A TRANSPORT
# THE ROW THAT WOULD HAVE CAUGHT THE MISSING 1/n^2, and the reason it sits apart
# from the Fresnel block: Fresnel is only HALF of what happens to a radiance at
# a refracting interface. The other half is that radiance is not conserved at
# all -- L/n^2 is, because a pencil's etendue n^2 dA dOmega is -- and render.py
# shipped for several rounds with T applied and the 1/n^2 absent. Every Fresnel
# row in this file passed throughout, because none of them ever asked what
# happens to a RADIANCE; they asked what happens to a ratio, and a ratio is
# where this factor cancels.
#
# What closes it is an audit with nothing to transcribe. Put a PERFECT WHITE
# Lambertian bed under a flat surface with no absorption, light it with a
# uniform sky, and compose it the way render.py composes -- down through the
# interface, off the bed, back up through `out_of_water`. The pool's apparent
# albedo must then be EXACTLY 1, because a lossless system cannot do anything
# else. With the divisor it is 1; without it, 1.73, and no tolerance argument
# reaches that. Both crossings use THIS file's own `fresnel_exact`, so the only
# thing borrowed from render.py is the quantity under test.
def tier_interface(R):
    n = R.IOR
    NQ = 20000
    mu = (np.arange(NQ) + .5) / NQ                # cosine in air / in water

    # -- the two diffuse Fresnel integrals, both computed here.
    r_ext = np.array([np.mean(2. * mu * fresnel_exact(mu, nc)[0]) for nc in n])

    def _rint(nc):
        """Water -> air, cosine-weighted, INCLUDING the whole TIR cone. Past the
        critical angle the reflectance is exactly 1 and that cone is 1 - 1/n^2
        of the hemisphere, which is most of the answer."""
        sa = np.sqrt(np.maximum(1. - mu ** 2, 0.)) * nc      # sine in air
        ca = np.sqrt(np.maximum(1. - sa ** 2, 0.))
        r = np.where(sa >= 1., 1., fresnel_exact(ca, nc)[0])
        return float(np.mean(2. * mu * r))
    r_int = np.array([_rint(nc) for nc in n])
    Tbar = np.array([np.mean(2. * mu * (1. - fresnel_exact(mu, nc)[0]))
                     for nc in n])

    # WALSH'S RELATION, which pins the EXPONENT and not merely the presence of a
    # factor: n^2 (1 - R_int) = 1 - R_ext is an exact consequence of Fresnel
    # reciprocity and holds for the square and for no other power.
    check(1, 'Walsh: n^2 (1 - R_int) == 1 - R_ext  [two quadratures, both here]',
          n ** 2 * (1. - r_int), 1. - r_ext, 3e-4,
          'exact identity; 3e-4 is the 20000-node midpoint rule against the '
          'square-root corner the TIR cone puts in the integrand')
    info(1, '  ... the same product at n^1 and n^3, for scale',
         'n^1 %s | n^3 %s | 1 - R_ext = %s'
         % (np.round(n * (1 - r_int), 4), np.round(n ** 3 * (1 - r_int), 4),
            np.round(1 - r_ext, 4)),
         'the identity picks out the square and nothing else, so a wrong power '
         'is as visible here as a missing factor')
    check(3, 'R_EXT / R_INT as shipped, vs this file\'s own quadratures',
          np.concatenate([R.R_EXT, R.R_INT]), np.concatenate([r_ext, r_int]),
          5e-4,
          'render.py integrates R_EXT on 512 nodes and gets R_INT by '
          'reciprocity; this integrates both directly on 20000 and gets R_INT '
          'the long way, through the TIR cone. 5e-4 is the coarse rule\'s error')

    # -- THE HEMISPHERICAL FORM OF THE FACTOR UNDER TEST.
    check(1, 'INT T(mu) out_of_water(1) 2 mu dmu == 1 - R_int',
          Tbar * R.out_of_water(np.ones((1, 3)))[0], 1. - r_int, 3e-4,
          'the exit transport, hemispherically averaged, evaluated THROUGH the '
          'shipped function. Without the 1/n^2 it reads 0.93 against 0.52 -- a '
          'clean factor n^2; with a 1/n instead it reads 0.70')
    check(1, 'T_OUT_DIFFUSE, the factor WBOUNCE now carries, == 1 - R_int',
          R.T_OUT_DIFFUSE, 1. - r_int, 5e-4,
          'the same transport in its diffuse form. The bare 0.5 it replaced '
          'misses this by 4.5%, which is why it is derived now')

    # -- THE CLOSED ENERGY AUDIT.
    def apparent_albedo(rho, divisor=True):
        E_w = (1. - r_ext) / (1. - rho * r_int)       # in-water bed irradiance
        L_w = rho * E_w / np.pi                       # in-water bed radiance
        L_a = R.out_of_water(L_w[None])[0]            # <- THE THING UNDER TEST
        if not divisor:
            L_a = L_a * R.IOR ** 2
        return r_ext + Tbar * np.pi * L_a

    check(1, 'a LOSSLESS pool (white bed, no absorption) has albedo exactly 1',
          apparent_albedo(1.0), np.ones(3), 5e-4,
          'energy conservation and nothing else -- the right-hand side is the '
          'number 1, and no constant of render.py enters it. 5e-4 is the two '
          'quadratures; composed without the 1/n^2 the row reads 1.73, a pool '
          'returning 73% more light than fell on it')
    info(1, '  ... the same audit with the divisor taken back out',
         np.round(apparent_albedo(1.0, divisor=False), 3),
         'what the file shipped for several rounds, in the energy books')
    # -- and off unity, against the file's own wet-liner formula: the same
    # physical quantity reached by unrelated code (a geometric series over
    # trapped bounces), itself already guarded against Egan & Hilgeman.
    for rho in (0.222, 0.585, 0.681, 0.95):
        check(3, 'apparent albedo of the pool == wet_albedo(%.3f)' % rho,
              apparent_albedo(rho), R.wet_albedo(np.array([[rho] * 3]))[0],
              1e-3,
              'this side integrates the transport ray by ray; wet_albedo sums '
              'the trapped series in closed form. They share no line of code. '
              '1e-3 relative is the two quadratures\' own spread', rel=True)

    # === WHY THAT AUDIT WAS BLIND, AND THE ROWS THAT ARE NOT ==================
    # The block above calls itself "a closed energy audit of the whole pool" and
    # it is nothing of the kind. Read what it borrows from render.py: ONE name,
    # `out_of_water`, sandwiched between an `E_w` and an `L_w` this file writes
    # itself. Everything the round that follows went looking for is on the other
    # side of that sandwich --
    #
    #   * whether render.py applies the trapped series TO THE BED at all. The
    #     audit closes the series in its own `1/(1 - rho r_int)` and never asks
    #     the renderer for it. The shipped bedret pass truncates at ONE bounce
    #     over the TIR cone alone and drops the 58% of that cone that meets a
    #     wall; the audit is arithmetically incapable of noticing.
    #   * absorption. `apparent_albedo` has no `a` and no depth: every path
    #     length in it is exactly 1. So the up leg -- the term the round's own
    #     closed form was found to be missing -- cannot appear in it either way.
    #   * geometry. There is no basin: no walls to take the beam, no sail.
    #
    # It is a good unit test of one divisor wearing the title of an audit. The
    # rows below go through the shipped chain instead: `rho_water` IS what
    # render.py's diagnostics quote, and the right-hand side is still the number
    # 1. The other half of the fix is in render.py, which now prints the three
    # scene terms the closed form has no room for, each signed and measured.
    check(1, '2 E_3(0) == 1 exactly (a transparent slab transmits all of it)',
          R._e3(0.0), np.ones(1), 1e-14,
          'the cosine measure 2 mu dmu integrates to 1; this is the row that '
          'catches a dropped leading 2, which halves every path in the chain')
    # -- 2 E_3 by a route with nothing in common with a Gauss-Legendre rule on
    #    mu: the exponential-integral recurrence E_{n+1} = (e^-x - x E_n)/n run
    #    down to E_1, and E_1 by its own convergent series. Two quadratures
    #    would have shared a premise; a recurrence and a series do not.
    EULER = 0.5772156649015329
    def _E1(x):
        s, t = -EULER - np.log(x), 1.0
        for k in range(1, 80):
            t = t * (-x) / k
            s = s - t / k
        return s
    xs = R.ABS * R.DEPTH
    rec = np.array([np.exp(-x) * (1. - x) + x * x * _E1(x) for x in xs])
    check(3, 'T_DIFF_UP == e^-x (1-x) + x^2 E_1(x)  [quadrature vs recurrence]',
          R.T_DIFF_UP, rec, 1e-10,
          'E_3 by the recurrence from E_1, with E_1 by its own series -- no '
          'quadrature node in common with render.py\'s 400-point Gauss-Legendre '
          'rule. 1e-10 is float64 accumulation over 80 series terms')
    between(1, 'the diffuse path is LONGER than the vertical: 2E_3(ad) < e^-ad',
            float(np.max(R.T_DIFF_UP - np.exp(-xs))), -1.0, -1e-4,
            'an inequality, not a fit: a cosine-distributed pencil crosses the '
          'slab at 1/mu >= 1, so its mean transmittance cannot reach the '
            'vertical one. It is 0.542 against 0.694 in red, and a chain that '
            'used exp(-a d) here would be 28% high on that channel')

    # -- THE AUDIT, RE-COMPOSED THROUGH THE SHIPPED CHAIN.
    _cs = float(R.cos_i)
    check(1, 'LOSSLESS WHITE POOL through rho_water: R(sun) + rho_w == 1',
          R.fresnel(_cs) + R.rho_water(1.0, absorb=0.0), np.ones(3), 1e-12,
          'energy conservation, and the right-hand side is the number 1. Unlike '
          'the audit above this goes through render.py\'s own transport: drop '
          'the up leg from its numerator and the row reads 1/T_up too high; put '
          'a one-way transmittance where the round trip belongs and it misses '
          'too. 1e-12 is float64 -- at zero absorption there is no quadrature '
          'left in it')
    for rho in (0.222, 0.585, 0.681, 0.95):
        # the same limit off unity, against a formula written HERE from this
        # file's own quadratured r_int -- `wet_albedo`'s algebra with R_ext
        # swapped for the directional R(sun), which is the only difference
        # between a thin film under a diffuse sky and a pool under a beam.
        rs = np.array([float(fresnel_exact(np.array([_cs]), nc)[0][0])
                       for nc in n])
        exp_ = rs + (1. - rs) * (1. - r_int) * rho / (1. - rho * r_int)
        check(3, 'lossless pool albedo == wet_albedo\'s algebra at R(sun), '
                 'rho=%.3f' % rho,
              R.fresnel(_cs) + R.rho_water(rho, absorb=0.0), exp_, 1e-3,
              'render.py composes a beam, a bed, an up leg and a series; this '
              'side is the closed geometric sum written out with r_int taken '
              'from this file\'s own 20000-node quadrature through the TIR '
              'cone. 1e-3 relative is that quadrature\'s spread', rel=True)

    # -- AND THE TRUNCATION, PRICED. This is the row that would have caught the
    #    shipped bedret pass, and it is INFO because the deficit is real, named
    #    in the README and not closed this round: closing it needs a wall -> bed
    #    return leg, which needs an up-going intersector `scene_hit` is not.
    # -- THE WHOLE CHAIN AT THE FILE'S OWN ABSORPTION, AGAINST A PHOTON WALK.
    # The lossless limit above pins the SHAPE of the series and is blind to
    # every path length in it, because at a = 0 every path is 1. Two of the
    # three errors this round found -- a numerator missing its up leg, and a
    # one-way transmittance where a round trip belongs -- pass that limit
    # untouched, and they were caught here instead. A second quadrature would
    # have shared the premise; this is an analog random walk: a photon enters
    # at the refracted angle, crosses to the bed, is redrawn from a cosine law,
    # attenuates over its OWN 1/mu, meets the exact internal Fresnel and either
    # escapes or comes back. Nothing in it is an average of anything.
    rng = np.random.default_rng(20260812)
    NMC = 400_000
    ci_s = float(R.cos_i)
    st = np.sqrt(1. - ci_s ** 2) / n
    tsl = np.exp(-R.ABS * R.DEPTH / np.sqrt(1. - st ** 2))
    rsun = np.array([float(fresnel_exact(np.array([ci_s]), nc)[0][0]) for nc in n])
    rb = np.array([0.222, 0.585, 0.681])

    def _rint_mu(mu, nc):
        sa = nc * np.sqrt(np.maximum(1. - mu ** 2, 0.))
        ca = np.sqrt(np.maximum(1. - sa ** 2, 0.))
        rs = ((nc * mu - ca) / (nc * mu + ca)) ** 2
        rp = ((nc * ca - mu) / (nc * ca + mu)) ** 2
        return np.where(sa >= 1., 1., .5 * (rs + rp))

    mc = np.zeros(3)
    for c in range(3):
        wt = np.full(NMC, (1. - rsun[c]) * tsl[c] * rb[c])
        esc = 0.0
        for _ in range(80):
            mu = np.sqrt(rng.random(NMC))            # cosine law off the bed
            wt = wt * np.exp(-R.ABS[c] * R.DEPTH / mu)
            rr = _rint_mu(mu, n[c])
            esc += float((wt * (1. - rr)).sum())
            wt = wt * rr * np.exp(-R.ABS[c] * R.DEPTH / mu) * rb[c]
            if wt.sum() < 1e-12 * NMC:
                break
        mc[c] = esc / NMC
    check(3, 'rho_water at the file\'s own ABS vs a %dk-photon walk' % (NMC // 1000),
          R.rho_water(rb), mc, 4e-3,
          'the walk\'s own standard error on 400k photons is under 1e-3 '
          'relative; 4e-3 covers it and the direction-sampling bias with room '
          'to spare. Factorising T_esc fails this row by 5-19%%, and dropping '
          'the up leg by 85%% in red -- neither of which the lossless limit '
          'above can see', rel=True)
    info(3, '  ... the two wrong writings of the same chain, on this row',
         'factorised %s | no up leg %s | walk %s'
         % (np.round(R._e3(R.ABS * R.DEPTH) * (1. - r_int) * (1. - rsun) * tsl
                     * rb / (1. - rb * R._e3(R.ABS * R.DEPTH) ** 2 * r_int), 5),
            np.round((1. - r_int) * (1. - rsun) * tsl * rb
                     / (1. - rb * R._e3(R.ABS * R.DEPTH) ** 2 * r_int), 5),
            np.round(mc, 5)),
         'both pass the lossless limit and both fail the walk; that is why the '
         'walk is here')

    full = R.trap_gain(rb)
    one_cone = R.trap_gain(rb, bounces=1, cone_only=True)
    info(1, 'the trapped series, closed vs the shipped pass\'s own model',
         'closed %s | one bounce over the TIR cone %s | ratio %s'
         % (np.round(full, 4), np.round(one_cone, 4),
            np.round(one_cone / full, 4)),
         'render.py returns the bed\'s light once, over 1 - 1/n^2 of the '
         'directions instead of R_int, and only for the share that reaches the '
         'surface without meeting a wall. The first two are arithmetic and are '
         'priced here; the third is geometry and is priced in the render\'s own '
         'print. This is what the audit above cannot see, because it never asks '
         'render.py for the series at all')
    between(1, 'the truncated trap is a LOWER bound on the closed one',
            float(np.max(one_cone - full)), -1.0, 0.0,
            'a truncated geometric series with a smaller ratio cannot exceed the '
          'closed one with the larger. It is the sign that matters: a render '
            'short of its own trap is dark, never bright, so this deficit can '
            'never be mistaken for the opposite defect the 1/n^2 round closed')


# ============================ TIER 1 / 3: WHERE THE SUBMERGED WALLS STAND
# `scene_hit` used to put the four walls on the PLAN RECTANGLE, s = 0, while
# every other piece of the edge -- the vertical face the freeboard band stands
# on, the line `gh` cliffs at, the line the meniscus climbs -- stands 20 mm
# inside it at s = SLIP. Nothing caught it because nothing ever asked the two
# constructions the same question. These rows ask it two ways.
def tier_wall_plane(R):
    rng = np.random.default_rng(20260812)
    N = 6000
    px = rng.uniform(R.X0 + .3, R.X1 - .3, N)
    py = rng.uniform(R.Y0 + .3, R.Y1 - .3, N)
    th = rng.uniform(0., 2 * np.pi, N)
    el = rng.uniform(.04, 1.35, N)
    tx, ty = np.cos(th) * np.cos(el), np.sin(th) * np.cos(el)
    tz = -np.sin(el)
    sid, u, v, sm, cyl = R.scene_hit(px, py, tx, ty, tz)
    hx, hy = px + tx * sm, py + ty * sm
    w = (sid >= 1) & (sid <= 4)
    # (1) THE PLANE ITSELF, read back through pool_sdf -- which `scene_hit` does
    # not call and has never called. Two constructions of the same surface.
    check(1, 'every wall hit lands on pool_sdf == SLIP  [%d of %d rays]'
          % (int(w.sum()), N),
          float(np.max(np.abs(R.pool_sdf(hx[w], hy[w]) - R.SLIP))), 0.0, 1e-12,
          'the four planes and the plan boundary are the same surface, so the '
          'residual is float round-off on a subtraction of order 8 m. On the '
          'planes this shipped with (s = 0) this row reads 0.020 exactly',
          unit='m')
    # (2) and nothing is reached THROUGH the boundary: every hit is the FIRST.
    eps = np.linspace(0., 1., 65)[1:-1]
    ins = np.max([np.max(R.pool_sdf(px + tx * sm * e, py + ty * sm * e))
                  for e in eps])
    between(1, 'the whole traced segment stays inside the water boundary',
            float(ins), -8.0, R.SLIP,
            'a first-hit solver that overshot a wall would put part of the '
            'segment OUTSIDE s = SLIP, so the assertion is one-sided: the '
            'worst interior sample of 6000 segments must still be at or '
            'within the boundary. On the planes this shipped with it reaches '
            's = 0', unit='m')
    # (3) THE INDEPENDENT METHOD: march the same rays through the height field
    # instead of solving five planes. `bed_z` is the bed as a height field and
    # `pool_sdf` is the boundary; neither is used by scene_hit's arithmetic.
    K = 400
    tt = np.linspace(0., 12., 12001)[None, :]
    j = rng.choice(N, K, replace=False)
    mx = px[j][:, None] + tx[j][:, None] * tt
    my = py[j][:, None] + ty[j][:, None] * tt
    mz = tz[j][:, None] * tt
    solid = (mz <= R.bed_z(mx, my)) | (R.pool_sdf(mx, my) >= R.SLIP)
    first = np.argmax(solid, 1).astype(float) * (12. / 12000.)
    ok = solid.any(1)
    d = np.abs(first[ok] - sm[j][ok])
    check(3, 'a 1 mm march of the height field finds the same first hit',
          float(np.percentile(d, 99)), 0.0, 1.1e-3,
          'the march quantises the answer to its own 1 mm step, so the whole '
          'tolerance is that step; the 99th percentile rather than the max '
          'because a ray landing exactly on an edge splits between two steps',
          unit='m')
    info(3, '  ... median march-vs-solve disagreement',
         '%.2e m over %d rays' % (float(np.median(d)), int(ok.sum())),
         'half a step is what a quantised march should give')


# ================== TIER 3: DOES THE WALL MAP COVER THE FILLET'S COLUMN?
# The fillet's transmitted rays start as high as MENIS_H above the still line
# and a refracted camera ray descends everywhere (t_z < 0 identically -- the
# same algebra that refutes the underside term, tested in section 8 below), so
# MENIS_H is a STRICT upper bound on where one of them can land. The map used to
# stop at z = 0 and `sample` clamped the top 3.9 mm of the column onto its first
# texel. It now runs to WTOP; this marches the whole fan and says both that the
# bound is respected and that it is not vacuous.
def tier_map_extent(R):
    check(1, 'WTOP, the wall map\'s top, == MENIS_H, the climb', R.WTOP,
          float(R.MENIS_H), 0.0,
          'the map is extended to the analytic bound, not to a round number')
    m4 = ((np.array([1., 0.]), lambda a: (np.full_like(a, R.X0 - R.SLIP), a)),
          (np.array([-1., 0.]), lambda a: (np.full_like(a, R.X1 + R.SLIP), a)),
          (np.array([0., 1.]), lambda a: (a, np.full_like(a, R.Y0 - R.SLIP))),
          (np.array([0., -1.]), lambda a: (a, np.full_like(a, R.Y1 + R.SLIP))))
    eyes = [R.EYE, np.array([-1.40, 2.00, 1.60]), np.array([4.00, -1.30, 2.40]),
            np.array([4.00, 2.00, 0.28]), np.array([9.40, 5.20, 3.10])]
    hi, lo, nwall, rise = -1e9, 1e9, 0, -1e9
    for tcd in (0.0, 40.0, 80.0):
        t = R.menis_tables(np.deg2rad(tcd), R.CAP_A, R.MENIS_N)
        _mph, WD, MD, MZ, MS, MC, _re = t
        for mvec, pos in m4:
            a = np.linspace(0.25, 3.75, 40)
            for eye in eyes:
                bx, by = pos(a)
                nd_x = (bx[:, None] + mvec[0] * MD[None]).ravel()
                nd_y = (by[:, None] + mvec[1] * MD[None]).ravel()
                pz = np.broadcast_to(MZ[None], (a.size, MD.size)).ravel()
                P = np.stack([nd_x, nd_y, pz], 1) - eye[None]
                P /= np.linalg.norm(P, axis=1, keepdims=True)
                nx = np.broadcast_to(mvec[0] * MS[None], (a.size, MD.size)).ravel()
                ny = np.broadcast_to(mvec[1] * MS[None], (a.size, MD.size)).ravel()
                nz = np.broadcast_to(MC[None], (a.size, MD.size)).ravel()
                ndv = -(P[:, 0] * nx + P[:, 1] * ny + P[:, 2] * nz)
                tx, ty, tz = R.refract(P[:, 0], P[:, 1], P[:, 2], nx, ny, nz,
                                       1.0 / R.IOR[1])
                sid, uu, vv, sm, _ = R.scene_hit(nd_x, nd_y, tx, ty, tz, pz)
                sel = (sid >= 1) & (sid <= 4) & (ndv > 0.)
                if not sel.any():
                    continue
                nwall += int(sel.sum())
                hi = max(hi, float(vv[sel].max()))
                lo = min(lo, float(vv[sel].min()))
                rise = max(rise, float((vv[sel] - pz[sel]).max()))
    between(1, 'no fillet ray ever RISES: max(z_hit - z_launch) <= 0', rise,
            -1.0, 0.0,
            'f = eta cos_i - cos_t < 0 for eta < 1, and n_z = cos(phi) >= 0 on '
            'a meniscus against a vertical wall, so t_z < 0 identically and '
            'the bound MENIS_H is strict. One-sided, over %d traced wall hits '
            'across 4 walls, 5 eye positions and 3 contact angles' % nwall,
            unit='m')
    check(3, 'the highest wall hit is INSIDE the map  [%d hits, 4 walls, 5 eye '
          'positions, theta_c 0-80 deg]' % nwall, hi, R.WTOP - 5e-4, 5e-4,
          'the bound is MENIS_H = %.2f mm and the map now runs to it. The row '
          'is two-sided on purpose: a map that stopped short would fail high, '
          'and a bound nothing reaches would fail low, which is how a vacuous '
          'row is caught' % (1000 * R.MENIS_H), unit='m')
    info(3, '  ... the fillet\'s transmitted column, in z',
         'lands between %.2f mm and %+.2f mm of the still line; the map runs '
         '-1400.00 to %+.2f mm' % (1000 * lo, 1000 * hi, 1000 * R.WTOP),
         'the top 3.9 mm of it used to be read off the map\'s first texel')


# ===================== TIER 1: THE NEAR-WALL FOLD, WHICH IS NOW ENFORCED
# `_menis_weights` prices the fold at |Vm| * h and says this frame never reaches
# it. That was a comment. It is now a guard, and these rows hold both halves of
# it: that it does not fire where the reference frame lives, and that it does
# fire where the bound applies.
def tier_fold(R):
    check(1, 'the fold guard passes a FAR wall (Vm > 0)',
          R._menis_fold_guard(np.array([0.31, 0.88]), True), 0.0, 0.0,
          'max(-Vm, 0) is identically zero there, so the reported area is '
          'exactly zero and no tolerance is involved', unit='m')
    raised = 0
    try:
        R._menis_fold_guard(np.array([0.31, -0.42]), True)
    except AssertionError:
        raised = 1
    check(1, 'the fold guard RAISES on a NEAR wall (Vm < 0)', raised, 1, 0,
          'a bound that nothing enforces is a comment; this is the row that '
          'makes it a guard')
    check(1, 'the area it reports is |Vm| * h',
          R._menis_fold_guard(np.array([-0.42]), False),
          0.42 * float(R.MENIS_H), 1e-15,
          'the bound as stated in `_menis_weights`, evaluated', unit='m')
    check(1, 'the tolerance is under one node of climb',
          float(R.MENIS_FOLD_TOL < R.MENIS_H / R.MENIS_N / 100.), 1.0, 0.0,
          'MENIS_H/MENIS_N is 60 um, the smallest fold a single quadrature '
          'node could carry; the tolerance is a thousandth of that, so it is '
          '"no ray at all" rather than a budget')
    # -- end to end, through `meniscus` itself, on the two walls that differ.
    stash = (R._env_menis, R._menis_under, R.EDGE_REFL, R.L_SUN, R.sail_vis)
    R._env_menis = lambda rx, ry, rz: np.ones((np.asarray(rx).size, 3))
    R._menis_under = lambda sid, u, v, sm, cyl, tz, mode: np.ones((sid.size, 3))
    R.EDGE_REFL = np.ones(3)
    R.L_SUN = np.zeros(3)
    R.sail_vis = lambda x, y: np.ones(np.asarray(x).shape)
    try:
        def run(P):
            nd, span = 401, 0.040
            gx, gy, _ = R.pool_grad(P[0], P[1])
            dd = np.linspace(0., span, nd)
            px, py = P[0] - gx * dd, P[1] - gy * dd
            dv = np.stack([px, py, np.zeros(nd)], 1) - R.EYE[None]
            tt = np.linalg.norm(dv, axis=1)
            dv /= tt[:, None]
            fpp = tt * R.PIXANG / np.maximum(np.abs(dv[:, 2]), .10) * R.SS
            st = R.surf_stats(px, py, fpp)
            return R.meniscus(px, py, R.SLIP - dd, dv, fpp, *st)
        run(np.array([3.40, R.Y1 + R.SLIP, 0.]))
        okn = 1
    except AssertionError:
        okn = 0
    try:
        run(np.array([R.X1 + R.SLIP, 2.60, 0.]))
        oke = 0
    except AssertionError:
        oke = 1
    finally:
        (R._env_menis, R._menis_under, R.EDGE_REFL, R.L_SUN,
         R.sail_vis) = stash
    check(1, 'meniscus() runs on the NORTH waterline (the frame\'s own)', okn,
          1, 0, 'Vm = +0.94 there; the reference frame must render')
    check(1, 'meniscus() REFUSES the EAST waterline (a near wall)', oke, 1, 0,
          'Vm = -0.61 there. The east waterline is behind the near coping\'s '
          'arris in this frame and no camera ray selects it, which is exactly '
          'the condition the comment rested on and the guard now enforces')


# ===================== TIER 1 / 3: DOES THE SUN REACH THE COPING?
# `sun_vis` = sail_vis * coping_vis, and `coping_vis` is a WATER-SURFACE term:
# the run from a point inside the pool to the lip. Applied to a point ON the
# stone its numerator goes negative on every side whose outward normal has a
# positive component toward the sun, so it returned a flat 0 and the north and
# west copings lost their direct sun entirely. The march below is the answer the
# geometry gives; `stone_vis` now has to match it.
def tier_stone_sun(R):
    def gz(x, y):
        """The pool-edge height field, minus the laid-stone wobble -- a +-4 mm
        dither the slice cannot build (its noise table is one of the skipped
        allocations) and one that cannot change a 21 deg ray's answer over the
        metres this marches."""
        s = R.pool_sdf(x, y)
        return np.where(s < R.SLIP, 0.0, R.edge_z(s))

    ss = np.linspace(R.SBUL + .002, R.COPW - .002, 12)      # coping TOP only
    aa = np.linspace(.35, 3.65, 14)
    PX, PY, SIDE = [], [], []
    for k, (nm, mk) in enumerate((('west ', lambda s, a: (R.X0 - s, a)),
                                  ('east ', lambda s, a: (R.X1 + s, a)),
                                  ('south', lambda s, a: (a * 2., R.Y0 - s)),
                                  ('north', lambda s, a: (a * 2., R.Y1 + s)))):
        S, A = np.meshgrid(ss, aa)
        x, y = mk(S.ravel(), A.ravel())
        PX.append(np.asarray(x, float)); PY.append(np.asarray(y, float))
        SIDE.append(np.full(x.size, k))
    PXa, PYa, SIDEa = np.concatenate(PX), np.concatenate(PY), np.concatenate(SIDE)
    z0 = gz(PXa, PYa)
    # -- the march. Step toward the sun and ask whether the height field ever
    # rises above the ray. Nothing else in the scene is above the water.
    tt = np.linspace(0., 14., 7001)[None, :]
    occ = np.zeros(PXa.size, bool)
    for c0 in range(0, PXa.size, 128):
        sl = slice(c0, c0 + 128)
        rx = PXa[sl][:, None] + R.SUN_DIR[0] * tt
        ry = PYa[sl][:, None] + R.SUN_DIR[1] * tt
        rz = z0[sl][:, None] + R.SUN_DIR[2] * tt
        occ[sl] = ((rz + 2e-4) < gz(rx, ry)).any(1)
    check(1, 'the sun reaches EVERY coping-top point (2 mm march of the height '
          'field, %d points on 4 sides)' % PXa.size, int(occ.sum()), 0, 0,
          'the coping is the highest thing in the scene bar the sail, and the '
          'far coping\'s own shadow reaches ZD/tan(21 deg) = 0.40 m, which '
          'lands on water. So the geometric answer is "lit", everywhere, and '
          'it is not a tolerance')
    stash = R.sail_vis
    R.sail_vis = lambda x, y: np.ones(np.asarray(x).shape)
    try:
        sv = np.asarray(R.stone_vis(PXa, PYa), float)
        uv = np.asarray(R.sun_vis(PXa, PYa), float)
    finally:
        R.sail_vis = stash
    check(1, 'stone_vis agrees with the march on every coping-top point',
          float(np.abs(sv - (~occ).astype(float)).max()), 0.0, 0.0,
          'sail_vis is stubbed to 1 for this row (the slice does not build the '
          'shade-sail map), so what is left IS the coping question. With the '
          '`sun_vis` this used to call, the row reads 1.0 on 50% of the points')
    info(1, '  ... what sun_vis gives on the same points, per side',
         '  '.join('%s %.2f' % (nm, uv[SIDEa == k].mean())
                   for k, nm in enumerate(('west', 'east', 'south', 'north'))),
         'coping_vis is 0 wherever the outward normal has a positive component '
         'toward the sun -- west and north here -- which is why it may not be '
         'asked about stone at all')
    # -- and the one place the coping DOES shade itself, recorded rather than
    # claimed away: the bottom of the bullnose on the sun-facing sides.
    sb = np.linspace(R.SLIP + .001, R.SBUL - .001, 24)
    bx = R.X0 - sb
    by = np.full_like(sb, 2.0)
    bz = gz(bx, by)
    rx = bx[:, None] + R.SUN_DIR[0] * tt
    ry = by[:, None] + R.SUN_DIR[1] * tt
    rz = bz[:, None] + R.SUN_DIR[2] * tt
    bocc = ((rz + 2e-4) < gz(rx, ry)).any(1)
    nl = -R.SUN_DIR[0]       # the west bullnose faces +x; the sun is at -x
    info(1, '  ... the west bullnose shades its own foot',
         '%.0f%% of the roll-over, up to s = %+.1f mm; N.L there is %+.3f'
         % (100 * bocc.mean(), 1000 * sb[bocc].max() if bocc.any() else 0., nl),
         'real, unmodelled and worth nothing: those facets face the pool, so '
         'the sun is behind them and their own N.L is negative. Recorded so '
         'that a camera on the other side of the pool does not inherit it '
         'silently')


def tier3_diffuse_fresnel(R):
    # R_INT is derived here by reciprocity from a quadrature of the file's own
    # Fresnel. There is an entirely separate, empirical expression for the same
    # quantity -- the internal diffuse reflectance of a smooth dielectric --
    # fitted by Egan & Hilgeman (1979) and in wide use in tissue optics as
    #     r_i = -1.440/n^2 + 0.710/n + 0.668 + 0.0636 n
    # It shares no arithmetic with the file's route to the number.
    walsh = -1.440 / R.IOR ** 2 + 0.710 / R.IOR + 0.668 + 0.0636 * R.IOR
    check(3, 'R_INT vs the Egan & Hilgeman 1979 empirical fit', R.R_INT, walsh,
          0.01,
          'the fit is quoted to 3-4 significant figures over n = 1.0-2.0; 1% is '
          'its own stated accuracy, and the two share no arithmetic at all',
          rel=True)
    info(3, '  ... R_INT, quadrature vs empirical fit',
         '%s against %s' % (np.round(R.R_INT, 5), np.round(walsh, 5)),
         'two unrelated routes to the same interface')


def tier3_cylinder(R):
    # The step risers are solved as four quadratics in `_cyl_entry`. March the
    # same union instead: step along the ray and take the first sample inside.
    rng = np.random.default_rng(11)
    M = 1500
    px = rng.uniform(4.3, 7.7, M)
    py = rng.uniform(2.1, 4.0, M)
    d = rng.normal(size=(M, 3))
    d[:, 2] = -np.abs(d[:, 2]) * 2.0
    d /= np.linalg.norm(d, axis=1)[:, None]
    bt, bf, bi = R._cyl_entry(px, py, d[:, 0], d[:, 1], d[:, 2], 0.0)
    step = 2e-4
    tmax = 3.0
    tg = np.arange(step, tmax, step)
    hit = np.full(M, np.inf)
    tang = np.zeros(M)                 # perpendicular miss distance at closest approach
    for i in range(M):
        x = px[i] + d[i, 0] * tg
        y = py[i] + d[i, 1] * tg
        z = d[i, 2] * tg
        inside = np.zeros(tg.shape, bool)
        near = np.inf
        for cx, cy, rr, zt in R.CYL:
            r2 = (x - cx) ** 2 + (y - cy) ** 2
            inside |= (r2 < rr * rr) & (z <= zt)
            near = min(near, float(np.abs(np.sqrt(r2) - rr).min()))
        tang[i] = near
        if inside.any():
            hit[i] = tg[np.argmax(inside)]
    ana = bt < tmax
    num = np.isfinite(hit)
    # -- WHERE BOTH FIND AN ENTRY, the two distances must agree to the march's
    # own resolution.
    keep = ana & num & (np.abs(hit - bt) < 0.05)
    check(3, 'analytic cylinder entry vs 0.2 mm brute-force march',
          float(np.abs(hit[keep] - bt[keep]).max()), 0.0, 1.5 * step,
          'the march quantises to %.1f mm and reports the first sample INSIDE, '
          'so 1.5 steps is the resolution of the comparison, not slack'
          % (1000 * step), 'm')
    # -- WHERE THEY DISAGREE ABOUT WHETHER there is an entry at all, every case
    # must be a near-tangent ray, which is a limit of the marcher and not of the
    # solve. This is the assertion with no tolerance in it: a disagreement that
    # is NOT tangential would be a real classification bug.
    dis = ana != num
    worst = float(tang[dis].max()) if dis.any() else 0.0
    check(3, 'every hit/miss disagreement is a near-tangent ray', worst, 0.0,
          3.0 * step,
          'a ray whose closest approach to a cylinder wall is under a few march '
          'steps can be classified either way by the marcher; one further out '
          'cannot, and would be a bug in the quadratic', 'm')
    info(3, '  ... rays compared / tangential disagreements',
         '%d entries compared, %d of %d disagree, all within %.2f mm of tangency'
         % (int(keep.sum()), int(dis.sum()), M, 1000 * worst),
         'the rest miss the step unit entirely')


def tier3_gemm(fld):
    # Four of the five bands are explicit plane-wave sums, evaluated two
    # different ways: a separable GEMM on the grid (the caustic pass) and a
    # direct per-component sum at points (the camera). If those disagree, the
    # light and the eye are looking at two different surfaces.
    xs = np.linspace(0.7, 3.3, 64)
    ys = np.linspace(0.6, 3.1, 48)
    X, Y = np.meshgrid(xs, ys)
    xp = X.ravel().astype(np.float64)
    yp = Y.ravel().astype(np.float64)
    for fp, tag in ((None, 'unfiltered'), (0.02, 'fp = 20 mm')):
        G = fld.grad_grid(xs, ys, fp)
        P = fld.grad_points(xp, yp, fp)
        e = float(max(np.abs(G[0].ravel() - P[0]).max(),
                      np.abs(G[1].ravel() - P[1]).max()))
        # The GEMM path accumulates in float32 over 64-74 components; the point
        # path accumulates in float64 from float32 inputs. 1e-6 is the float32
        # epsilon times the number of terms, i.e. the accumulated round-off, and
        # is 20x smaller than the third decimal any diagnostic reads.
        check(3, 'grad_grid (separable GEMM) vs grad_points (direct sum), %s' % tag,
              e, 0.0, 1e-6,
              'float32 accumulation over ~70 components: eps*sqrt(N)*|g| ~ 3e-7; '
              '1e-6 is that, and 1e-4 of the smallest slope any row prints')
    # -- the Gabor reconstruction the wake arrives through, tested on a field
    # whose answer is known: deposit atoms of ONE plane wave along a line, with
    # the module's own window rule, and check the Nadaraya-Watson quotient
    # returns that plane wave. This is the "window must be wider than the wave"
    # claim in wake.build's docstring, as a closed form.
    lam = 0.27
    kw = 2 * np.pi / lam
    sg = 0.45 * lam                      # wake.build's floor: sigma >= 0.45 lambda
    cx = np.arange(-1.0, 1.0001, 0.35 * sg)
    gxs = np.linspace(-0.30, 0.30, 241)
    num = np.zeros_like(gxs)
    den = np.zeros_like(gxs)
    for p in cx:
        dxg = gxs - p
        w = np.exp(-dxg ** 2 / (2 * sg * sg))
        num += np.cos(kw * p + kw * dxg) * w
        den += w
    err = float(np.abs(num / den - np.cos(kw * gxs)).max())
    check(3, 'Gabor sum reconstructs a plane wave (sigma = 0.45 lambda)', err,
          0.0, 0.02,
          'atoms 0.35 sigma apart on a 1-D lattice; the residual is the '
          'lattice\'s own aliasing, exp(-2 pi^2 sigma^2/dx^2), under 1e-3. '
          '0.02 is 20x that and still catches a wrong window')
    # -- and the reason wake.build floors the window at half a wavelength, as a
    # spectrum rather than as an assertion: a Gabor ATOM of width sigma has its
    # slope energy at the atom's own k only while sigma exceeds the wavelength.
    # Below that the atom is a wavelet and its slope-weighted centroid runs away
    # to 1/sigma, which is the "reconstructed as 5 cm" failure in the docstring.
    xs = np.linspace(-2.0, 2.0, 1 << 15)
    dxs = xs[1] - xs[0]
    kk = 2 * np.pi * np.fft.rfftfreq(xs.size, dxs)
    cen = []
    for fw in (0.45, 0.04):
        atom = np.cos(kw * xs) * np.exp(-xs ** 2 / (2 * (fw * lam) ** 2))
        P = np.abs(np.fft.rfft(atom)) ** 2 * kk ** 2      # slope energy
        cen.append(float((P * kk).sum() / max(P.sum(), 1e-30)))
    check(3, 'Gabor atom at the shipped floor carries its own k, not the window\'s',
          cen[0] / kw, 1.0, 0.15,
          'a Gaussian-windowed cosine has spectral width 1/sigma about k, so the '
          'slope-weighted centroid sits within 1/(k sigma) = 35% of k at this '
          'floor and the shift is one-sided; 15% is the measured half of that')
    info(3, '  ... atom centroid at sigma = 0.45 and 0.04 lambda',
         '%.2f k and %.2f k (the second is the docstring\'s failure mode)'
         % (cen[0] / kw, cen[1] / kw),
         'below the WKB floor the window, not the wave, sets the wavelength')


def tier3_geometry(R):
    rng = np.random.default_rng(5150)
    # -- the exact rectangle view factor against Monte-Carlo. This is the number
    # that prices the missing wall term, so it is worth more than one opinion.
    for x, y, h in ((2.7, 1.3, 1.40), (0.4, 3.6, 1.40), (4.0, 2.0, 0.205)):
        K = 400000
        u = rng.random(K)
        ph = rng.uniform(0, 2 * np.pi, K)
        sn, cs = np.sqrt(u), np.sqrt(1 - u)
        sx = x + h / cs * sn * np.cos(ph)
        sy = y + h / cs * sn * np.sin(ph)
        mc = float(((sx > R.X0) & (sx < R.X1) & (sy > R.Y0) & (sy < R.Y1)).mean())
        se = np.sqrt(mc * (1 - mc) / K)
        check(3, '_sky_vf closed form vs %dk cosine-weighted MC at (%.1f,%.1f,%.2f)'
              % (K // 1000, x, y, h), float(R._sky_vf(x, y, h)), mc, 4 * se,
              'cosine-weighted sampling gives a binomial estimate with 1 sigma = '
              '%.5f; 4 sigma is the tolerance' % se)
    # -- the TIR fraction. 1 - 1/n^2 is the exact share of a cosine-weighted
    # hemisphere beyond the critical angle.
    K = 2000000
    u = rng.random(K)
    th = np.arcsin(np.sqrt(u))                 # cosine-weighted polar angle
    tc = np.arcsin(1.0 / R.IOR[1])
    frac = float((th > tc).mean())
    check(3, 'TIR_FRAC vs %dk cosine-weighted MC' % (K // 1000), R.TIR_FRAC, frac,
          4 * np.sqrt(frac * (1 - frac) / K),
          'binomial 1 sigma = %.5f; 4 sigma' % np.sqrt(frac * (1 - frac) / K))
    check(1, 'TIR_FRAC == 1 - 1/n^2 exactly', R.TIR_FRAC,
          1 - 1 / R.IOR[1] ** 2, 1e-15, 'algebraic identity')
    info(3, '  ... TIR_FRAC vs the file\'s own diffuse R_INT',
         '%.4f (TIR only) against %.4f (TIR + sub-critical Fresnel)'
         % (R.TIR_FRAC, R.R_INT[1]),
         'the same interface, priced twice, 8.5%% apart; the bed return uses the '
         'smaller one')
    # -- TIR_VERT: the irradiance a vertical face collects from the returning
    # field, over what the horizontal bed collects from it. Closed form in
    # render.py; here by quadrature and by Monte-Carlo.
    #
    # THESE TWO ROWS USED TO BE WRONG TOGETHER, and how they got that way is the
    # reason the file is written the way it is. Both were transcribed from the
    # SENTENCE beside the constant in render.py -- "the returning flux has
    # angular density cos(t) sin(t) dt" -- rather than from the interface. That
    # density is the EMITTED-FLUX distribution, right for a flux fraction (it is
    # how TIR_FRAC is derived) and wrong for a receiver's irradiance, because it
    # already contains the horizontal receiver's own cosine. So a quadrature and
    # a 4M-sample Monte-Carlo, nominally independent, agreed with each other on
    # 0.635 -- and neither was measuring the physics. Two methods that read the
    # same premise are one method.
    #
    # WHAT THE PHYSICS SAYS. Under a mirror the arriving field is a UNIFORM
    # radiance L over the cone t > tc (a Lambertian bed's radiance is
    # angle-independent, radiance is conserved along a ray, a perfect mirror
    # preserves it). Each receiver's irradiance is then INT L (w.n)+ dw over that
    # cone and nothing else:
    #   horizontal:  (w.n) = cos t
    #   vertical:    (w.n) = sin t * max(cos phi, 0)
    # Both integrals are now written from THAT, in two ways that share nothing:
    # a 1-D quadrature of the closed forms, and a Monte-Carlo that never forms an
    # integrand at all -- it draws directions uniform in solid angle, throws away
    # those inside the cone, and averages the two receiver cosines directly.
    th = np.linspace(tc, np.pi / 2, 2000001)
    quad = (2.0 * np.trapezoid(np.sin(th) ** 2, th)) \
        / (2.0 * np.pi * np.trapezoid(np.cos(th) * np.sin(th), th))
    K = 4000000
    ct2 = rng.random(K)                        # cos t uniform => uniform in dw
    st2 = np.sqrt(1.0 - ct2 ** 2)
    p2 = rng.uniform(0, 2 * np.pi, K)
    m = np.arccos(ct2) > tc
    # E = INT L (w.n)+ dw estimated as 2 pi <(w.n)+ . 1[t>tc]>; the 2 pi and the
    # sample count cancel in the ratio, so this is a ratio of two plain means.
    mcv = float((st2[m] * np.maximum(np.cos(p2[m]), 0)).sum() / ct2[m].sum())
    check(3, 'TIR_VERT vs quadrature of the arriving RADIANCE', R.TIR_VERT,
          float(quad), 1e-6,
          'both are the same pair of one-dimensional integrals; the trapezoid\'s '
          'own error on 2e6 points is under 1e-11')
    _se = float(np.std(np.where(m, st2 * np.maximum(np.cos(p2), 0), 0.0))
                / np.sqrt(K) / (ct2[m].sum() / K))
    check(3, 'TIR_VERT vs %dk uniform-solid-angle MC of the same field'
          % (K // 1000), R.TIR_VERT, mcv, 4 * _se,
          'MC 1 sigma on the numerator is %.5f; 4 sigma' % _se)
    # -- THE GUARD THAT CANNOT SHARE THE PREMISE, and the one that would have
    # caught the original defect on its own. As tc -> 0 the cone opens to the
    # whole hemisphere, where a vertical face must collect EXACTLY half of what a
    # horizontal one does. It is a limit, not a value: no quadrature, no MC, no
    # sentence to transcribe. The shipped 0.563 form sends tc -> 0 to
    # (1/(4 pi))/(1/3) = 0.2387 and the 0.635 form to 0.3183; only the radiance
    # form lands on 1/2.
    check(1, 'tir_vert(theta_c -> 0) == 1/2 exactly (the full hemisphere)',
          float(R.tir_vert(0.0)), 0.5, 1e-15,
          'algebraic limit of the closed form; one double ulp')
    # -- and the same 1/2 arrived at from the other end of the file: the riser
    # gather's estimator closes on 1/2 over its full range, by a completely
    # different integral (a distance-importance-sampled view factor) over the
    # same hemisphere. Two independent pieces of code, one number.
    check(1, 'tir_vert(0) == the riser gather\'s full-range closure (both 1/2)',
          float(R.tir_vert(0.0)), float(R._ris_closure(0.12, 1e-9, 1e9)), 1e-6,
          'the same half-hemisphere identity reached by two unrelated '
          'estimators; 1e-6 is the closure\'s own truncation at 1e-9/1e9 m')
    # -- AND THE SAME 1/2 A THIRD TIME, where it is a PARTITION and not a
    # closure. `WALL_SKY` is what the wall's sky ambient is multiplied by now
    # that the gather supplies the downgoing half of the same hemisphere. If the
    # two do not sum to one hemisphere the wall is either lit twice over the
    # half they overlap on or not at all over the half they miss, and the whole
    # of the bed-onto-wall round is that arithmetic. So: the share the sky keeps
    # and the share the gather closes on must add to exactly 1, with the second
    # taken from the gather's own analytic closure and not from the constant.
    check(1, 'WALL_SKY + the gather\'s full-range closure == 1 (one hemisphere, '
             'counted once)',
          float(R.WALL_SKY) + float(R._ris_closure(0.35, 1e-9, 1e9)), 1.0, 1e-6,
          'a partition of the wall\'s hemisphere: whatever the bed supplies has '
          'to come OUT of the sky term, and both halves are 1/2 exactly. 1e-6 '
          'is the closure\'s own truncation at 1e-9/1e9 m')
    check(1, 'WALL_SKY == tir_vert(0), the same half from the interface side',
          float(R.WALL_SKY), float(R.tir_vert(0.0)), 1e-15,
          'a vertical face collects half of what a horizontal one does under a '
          'uniform hemisphere; algebraic limit, one double ulp')
    info(3, '  ... TIR_VERT, three readings of one sentence',
         'shipped-before 0.56271, the comment\'s own words 0.63476, physics '
         '%.5f (code now %.5f)' % (quad, R.TIR_VERT),
         'the suite asserted the middle one until this round')
    # -- the riser gather's estimator. _ris_closure is the analytic value of the
    # truncated view factor; the estimator that is actually run is a lattice of
    # (d, phi) samples with a closed-form weight. Sample that estimator directly.
    h = 0.12
    K = 400000
    lnR = np.log(R.RIS_D1 / R.RIS_D0)
    dd = R.RIS_D0 * np.exp(lnR * rng.random(K))
    phi = np.pi * rng.random(K) - np.pi / 2
    w = lnR * np.cos(phi) * dd ** 3 * h / (h * h + dd * dd) ** 2
    est = float(w.mean())
    ref = float(R._ris_closure(h, R.RIS_D0, R.RIS_D1))
    check(3, 'riser gather estimator (MC of the shipped weight) vs _ris_closure',
          est, ref, 4 * float(w.std()) / np.sqrt(K),
          'the estimator\'s own standard error over %dk samples is %.5f; 4 sigma'
          % (K // 1000, float(w.std()) / np.sqrt(K)))
    # -- THE SHIPPED LATTICE, at the heights the WALLS added. The row above
    # samples the weight at random; the picture is made with 960 FIXED
    # directions (40 log-spaced distance strata x 24 azimuth strata, jittered
    # once at import), so its error is not a standard error -- it is a
    # deterministic quadrature bias that is a function of the face's height over
    # its own foot. On a riser that height is 20-240 mm; on a wall it runs to
    # 1.40 m, an order of magnitude the lattice had never been asked for. This
    # measures that bias against the closed form, and the next row's tolerance
    # is taken FROM it rather than from the disagreement it is testing.
    hs = np.array([0.03, 0.06, 0.12, 0.25, 0.50, 1.00, 1.40])
    r2 = hs[:, None] ** 2 + R._DD[None] ** 2
    lat = (R._lnR * np.cos(R._PH)[None] * R._DD[None] ** 3
           * hs[:, None] / (r2 * r2)).mean(1)
    exa = R._ris_closure(hs, R.RIS_D0, R.RIS_D1)
    LAT_ERR = float(np.max(np.abs(lat / exa - 1.0)))
    check(3, 'the SHIPPED %d-direction lattice vs _ris_closure, 30 mm - 1.40 m'
          % (R.RIS_ND * R.RIS_NP), lat, exa, 0.05, rel=True,
          why='a 20x12 stratified lattice jittered once integrates a kernel '
              'whose width is h; over 30 mm - 1.40 m the worst stratum error is '
              '%.1f%% and 5%% is the bound this asserts it stays inside'
              % (100 * LAT_ERR))
    info(3, '  ... worst lattice bias over those heights', '%.2f%%'
         % (100 * LAT_ERR),
         'systematic, not noise: every texel shares the same lattice, so the '
         'bias is a function of the height and not of the texel')
    # -- THE BED <-> WALL TRANSFER, BY RECIPROCITY. This is the conservation
    # identity behind the round that lit the pool walls, and the two sides of it
    # are computed by code that shares nothing but the pool's dimensions.
    #
    # WHAT IS BEING ASSERTED. For any two surfaces exchanging diffuse light the
    # view-factor kernel cos(t1) cos(t2)/(pi r^2) is symmetric, so
    #     A_bed * F(bed -> wall)  ==  A_wall * F(wall -> bed).
    # render.py already had the LEFT side in closed form: `_sky_vf` is the exact
    # cosine-weighted view factor from a bed point to the water rectangle
    # overhead (Hottel's differential-element-to-parallel-rectangle formula) and
    # everything left over is wall -- that is the 35% the file has printed every
    # run since wave 5 as the size of the term it did not have. The RIGHT side
    # did not exist until the gather was pointed at the walls; it is
    # `bounce_gather`, a distance-importance-sampled lattice quadrature over the
    # wall's own hemisphere, run here with a UNIT RADIANCE on the bed and an
    # empty box, so what comes back is pure geometry.
    #
    # Neither side can be right by construction. One is an arctangent formula
    # evaluated over the floor; the other is 960 traced rays per texel with a
    # closed-form Jacobian weight, evaluated over the walls. They meet only
    # through the reciprocity theorem.
    #
    # AND THE EMPTY BOX IS THE POINT, not a convenience: reciprocity between
    # `_sky_vf` and the gather is EXACT only where the two agree on what a wall
    # is, and in the real basin they do not -- the step unit is a riser to the
    # gather and part of the bed point's non-sky hemisphere to the rectangle
    # formula. render.py prints the real-scene version of this same pair, with
    # that gap named; the row here is the version with nothing left over.
    X0_, X1_, Y0_, Y1_, DP = R.X0, R.X1, R.Y0, R.Y1, R.DEPTH
    BIGV = 1e9

    def box_hit(px, py, tx, ty, tz, pz):
        """First hit of a downgoing ray in an EMPTY box: flat bed at -DEPTH over
        the plan rectangle, four vertical walls, open top. Written here, from the
        box, so that it shares no line with render.py's `scene_hit`."""
        px, py = np.broadcast_arrays(np.asarray(px, float), np.asarray(py, float))
        pz = np.broadcast_to(np.asarray(pz, float), px.shape)
        with np.errstate(divide='ignore', invalid='ignore'):
            s = np.stack([np.where(tz < -1e-12, (-DP - pz) / tz, BIGV),
                          np.where(tx < -1e-12, (X0_ - px) / tx, BIGV),
                          np.where(tx > 1e-12, (X1_ - px) / tx, BIGV),
                          np.where(ty < -1e-12, (Y0_ - py) / ty, BIGV),
                          np.where(ty > 1e-12, (Y1_ - py) / ty, BIGV)])
        s = np.where(np.isfinite(s) & (s > 1e-12), s, BIGV)
        sid = np.argmin(s, 0).astype(np.int8)
        sm = np.take_along_axis(s, sid[None].astype(np.intp), 0)[0]
        hx, hy, hz = px + tx * sm, py + ty * sm, pz + tz * sm
        u = np.where(sid == 0, hx, np.where(sid <= 2, hy, hx))
        return sid, u, np.where(sid == 0, hy, hz), sm, np.full(px.shape, -1, np.int8)

    def unit_on_bed(sd, u, v, sm):
        """A radiance of 1 on the bed, 0 everywhere else, and NO absorption --
        so the gather returns the view factor and not a light level."""
        return np.repeat((sd == 0)[:, None].astype(float), 3, 1)

    NU, NZ = 96, 32
    A_wall, wall_side, closure = 0.0, 0.0, []
    for nx, ny, ax, along in ((1, 0, X0_, 0), (-1, 0, X1_, 0),
                              (0, 1, Y0_, 1), (0, -1, Y1_, 1)):
        e = np.linspace(X0_, X1_, NU + 1) if along else np.linspace(Y0_, Y1_, NU + 1)
        uu = .5 * (e[:-1] + e[1:])
        ez = np.linspace(-DP, 0.0, NZ + 1)
        zz = .5 * (ez[:-1] + ez[1:])
        U, Z = np.meshgrid(uu, zz)
        px = U.ravel() if along else np.full(U.size, float(ax))
        py = np.full(U.size, float(ax)) if along else U.ravel()
        hh = Z.ravel() + DP                       # exact: the foot IS the bed
        _, vf = R.bounce_gather(px, py, Z.ravel(), nx, ny, hh,
                                src=unit_on_bed, hit=box_hit)
        L = (X1_ - X0_) if along else (Y1_ - Y0_)
        A_wall += L * DP
        wall_side += L * DP * float(vf[:, 0].mean())
        closure.append(float(vf[:, :2].sum(1).mean()))
    n = 600
    ex_ = np.linspace(X0_, X1_, n + 1)
    ey_ = np.linspace(Y0_, Y1_, n + 1)
    XX, YY = np.meshgrid(.5 * (ex_[:-1] + ex_[1:]), .5 * (ey_[:-1] + ey_[1:]))
    A_bed = (X1_ - X0_) * (Y1_ - Y0_)
    bed_side = A_bed * float((1.0 - R._sky_vf(XX, YY, DP)).mean())
    check(3, 'bed <-> wall reciprocity: A_wall F(wall->bed) == A_bed F(bed->wall)',
          wall_side, bed_side, 1.5 * LAT_ERR, rel=True,
          why='the shipped lattice\'s own closure error at these heights is '
              '%.1f%% (row above), which is a floor on any transfer it '
              'computes; the extra half is the 12 azimuth strata resolving the '
              'bed/far-wall horizon, which the closure test does not exercise. '
              'Nothing here is fitted to the disagreement: 1.5x%.1f%% = %.1f%%'
              % (100 * LAT_ERR, 100 * LAT_ERR, 150 * LAT_ERR),
          unit='m2')
    info(3, '  ... the two sides, and the wall\'s own hemisphere split',
         'A_bed F = %.3f m2 over %.1f m2 of bed, A_wall F = %.3f m2 over %.1f '
         'm2 of wall; F(wall->bed) = %.3f of the %.3f the gather closes on'
         % (bed_side, A_bed, wall_side, A_wall, wall_side / A_wall,
            float(np.mean(closure))),
         'the rest of the wall\'s downgoing half is the other three walls')


_ODE_CACHE = {}


def _menis_ode(R, theta_c, a, nstep=200000):
    """The meniscus profile by MARCHING YOUNG-LAPLACE, not by integrating it.

    render.py ships the closed-form first integral, z = 2a sin(phi/2), and the
    closed-form dd/dphi that goes with it. Here the two-dimensional
    Young-Laplace balance is solved as an initial-value problem in arc length,
    RK4, from the wall outward:

        dphi/ds = -z/a^2        (curvature = hydrostatic head / surface tension)
        dz/ds   = -sin(phi)
        dd/ds   = +cos(phi)     (d measured poolward from the wall)

    starting at phi = phi_w, z = h, d = 0. Nothing in this loop knows that the
    answer is 2a sin(phi/2), or what dd/dphi is; it knows the DIFFERENTIAL
    statement the closed form was derived from. Scalar arithmetic on purpose --
    numpy on three-element states spends all its time in dispatch.

    Returns (phi, d, z) along the march, phi descending."""
    key = (round(theta_c, 12), round(a, 15), nstep)
    if key in _ODE_CACHE:
        return _ODE_CACHE[key]
    from math import sin, cos
    phw = np.pi / 2 - theta_c
    h = a * np.sqrt(2.0 * (1.0 - np.sin(theta_c)))
    ds = 12.0 * a / nstep                 # the whole fillet is a few a of arc
    ia2 = 1.0 / (a * a)
    ph, z, d = float(phw), float(h), 0.0
    P = [ph]
    D = [d]
    Z = [z]
    for _ in range(nstep):
        k1p, k1z, k1d = -z * ia2, -sin(ph), cos(ph)
        p2, z2 = ph + .5 * ds * k1p, z + .5 * ds * k1z
        k2p, k2z, k2d = -z2 * ia2, -sin(p2), cos(p2)
        p3, z3 = ph + .5 * ds * k2p, z + .5 * ds * k2z
        k3p, k3z, k3d = -z3 * ia2, -sin(p3), cos(p3)
        p4, z4 = ph + ds * k3p, z + ds * k3z
        k4p, k4z, k4d = -z4 * ia2, -sin(p4), cos(p4)
        ph += (ds / 6.0) * (k1p + 2 * k2p + 2 * k3p + k4p)
        z += (ds / 6.0) * (k1z + 2 * k2z + 2 * k3z + k4z)
        d += (ds / 6.0) * (k1d + 2 * k2d + 2 * k3d + k4d)
        if ph <= 0.0:
            break
        P.append(ph)
        D.append(d)
        Z.append(z)
    out = (np.array(P), np.array(D), np.array(Z))
    _ODE_CACHE[key] = out
    return out


def tier_meniscus(R):
    """The fillet. Every row here is a statement the implementation does not
    make about itself.

    The shipped code writes the profile as a closed form, sweeps it with a
    64-node midpoint rule, weights each node by a Fresnel and an environment,
    subtracts the flat surface it replaces and deposits the difference through a
    folded Gaussian. Re-deriving any of that and comparing would be one method
    twice. So what is checked instead is:

      * a FORCE BALANCE on the tabulated columns (Newton, not Young-Laplace),
      * the profile against an RK4 march of the DIFFERENTIAL statement,
      * a PROJECTED-AREA identity that depends only on the fillet's endpoints
        and is therefore blind to everything the quadrature does in between,
      * the same excess measured by a brute-force parallel-ray march,
      * the shipped `meniscus`'s own DEPOSIT integrated back to that excess,
        which closes the Fresnel split, the kernel and the fold at once,
      * two LIMITS that are forced and that the code cannot satisfy by
        construction: a -> 0 and theta_c -> 90 deg,
      * the reachability algebra against literal reflection,
      * and the refutation of the internal-reflection term.
    """
    a, rho_g = R.CAP_A, 1000.0 * 9.81

    # ---------------------------------------------------------------- 1. force
    # THE WEIGHT THE SURFACE HOLDS UP. Per unit length of waterline the fillet
    # raises a cross-section of liquid whose weight must equal the vertical
    # component of the surface tension pulling on the wall:
    #       rho g INT z dx = sigma cos(theta_c) = sigma sin(phi_w).
    # This is a statement about FORCES. It never appears in the derivation of
    # the profile, it constrains z and dx JOINTLY, and it is evaluated on the
    # very two columns the flux integral sweeps -- so a table that is
    # self-consistently wrong in either column fails it. The residual is the
    # midpoint rule's own error and nothing else.
    for tcd in (0.0, 30.0, 60.0, 89.0):
        tc = np.deg2rad(tcd)
        _, wd, _, z, _, _, _ = R.menis_tables(tc, a, R.MENIS_N)
        lift = float((z * wd).sum() * rho_g)
        ref = float(R.SIGMA_W * np.sin(np.pi / 2 - tc))
        # midpoint rule on an integrand that goes as a/phi at the outer end;
        # measured against the same construction at 4096 nodes below.
        _, wd4, _, z4, _, _, _ = R.menis_tables(tc, a, 4096)
        qerr = abs(float((z4 * wd4).sum() * rho_g) - lift)
        check(1, 'fillet force balance rho g INT z dx == sigma cos(theta_c)  '
              '[theta_c = %2.0f deg]' % tcd, lift, ref, max(3 * qerr, 1e-9),
              'the midpoint rule\'s own error: the same construction at 4096 '
              'nodes moves the sum by %.2e N/m, and 3x that is the tolerance'
              % qerr, unit='N/m')
    check(1, 'the shipped table\'s MENIS_LIFT is that same balance',
          R.MENIS_LIFT, float(R.SIGMA_W * np.sin(R.PHI_W)), 1e-5,
          'the module-level constant against the module-level contact angle')

    # ------------------------------------------------------------- 2. the shape
    # The force balance pins the AREA under the profile; it says nothing about
    # its shape, because it depends only on an integral. The shape is checked by
    # solving the differential statement the closed form came from.
    for tcd in (0.0, 60.0):
        tc = np.deg2rad(tcd)
        ph, wd, dd, zz, _, _, reach = R.menis_tables(tc, a, R.MENIS_N)
        oph, odd, ozz = _menis_ode(R, tc, a)
        # the march runs from the wall (phi_w) outward, so phi descends
        zm = np.interp(ph, oph[::-1], ozz[::-1])
        dm = np.interp(ph, oph[::-1], odd[::-1])
        ez = float(np.max(np.abs(zz - zm)))
        # d is the CUMULATIVE midpoint sum, so it carries the rule's error; the
        # tolerance is that error, measured by refining the same construction.
        _, _, dd4, _, _, _, _ = R.menis_tables(tc, a, 4096)
        ph4 = (np.arange(4096) + .5) / 4096 * (np.pi / 2 - tc)
        qd = float(np.max(np.abs(dd - np.interp(ph, ph4, dd4))))
        ed = float(np.max(np.abs(dd - dm)))
        check(3, 'profile z(phi) vs RK4 march of Young-Laplace  '
              '[theta_c = %2.0f deg]' % tcd, ez, 0.0, 2e-8,
              'RK4 at 4e5 steps over 6a of arc; the march\'s own truncation is '
              'far below this and 2e-8 m = 20 nm is the interpolation floor',
              unit='m')
        check(3, 'profile d(phi) vs RK4 march of Young-Laplace  '
              '[theta_c = %2.0f deg]' % tcd, ed, 0.0, max(3 * qd, 2e-8),
              'the tabulated d is a 64-node midpoint cumulative sum; refining '
              'the same sum to 4096 nodes moves it by %.2e m, and 3x that is '
              'the tolerance' % qd, unit='m')

    # ------------------------------------------- 3. the projected-area identity
    # THE ONE ROW THAT IS BLIND TO THE QUADRATURE. For any monotone profile,
    #       INT ds (n.V) = Vm * z(end) + Vz * (d(start) - d(end))
    # because ds sin(phi) = dz and ds cos(phi) = -dd exactly, so the integral
    # telescopes to its endpoints. Subtract the flat strip of the same width,
    # Vz * (d(start) - d(end)), and everything cancels but
    #       SUM (w_fil - w_flt) = Vm * z(phi*)
    # with phi* the steepest tilt the eye can see. It depends on the CLIMB and
    # the view direction and on nothing else: not on the node count, not on
    # dd/dphi, not on where the nodes sit. A quadrature that is wrong anywhere
    # in the middle still has to land here, and one that is wrong at either end
    # cannot. Checked on both signs of Vm -- the far walls, where the whole
    # fillet faces the eye, and the near wall, where its own crest hides
    # everything steeper than atan(Vz/|Vm|).
    for tcd in (0.0, 30.0, 89.0):
        tc = np.deg2rad(tcd)
        ph, wd, dd, zz, sn, cs, reach = R.menis_tables(tc, a, R.MENIS_N)
        old = (R._mph, R.MENIS_WD, R.MENIS_D, R.MENIS_Z, R.MENIS_SIN,
               R.MENIS_COS, R.MENIS_REACH, R.PHI_W)
        (R._mph, R.MENIS_WD, R.MENIS_D, R.MENIS_Z, R.MENIS_SIN,
         R.MENIS_COS, R.MENIS_REACH, R.PHI_W) = (ph, wd, dd, zz, sn, cs,
                                                 reach, np.pi / 2 - tc)
        try:
            for Vm0, Vz0, tag in ((0.51, 0.46, 'far wall, whole fillet in view'),
                                  (0.216, 0.197, 'far wall, 11 deg grazing'),
                                  (-0.60, 0.79, 'near wall, crest occludes'),
                                  (-0.10, 0.99, 'near wall, steep')):
                n = np.hypot(Vm0, Vz0)
                Vm, Vz = Vm0 / n, Vz0 / n
                ndv, wf, wl, wo, isil = R._menis_weights(
                    np.array([Vm]), np.array([Vz]))
                got = float((wf + wo - wl).sum())
                vis = np.flatnonzero(ndv[0] > 0)
                # z at the visible arc's steep end, taken at the CELL EDGE
                phe = (ph[vis[-1]] + .5 * (ph[1] - ph[0])) if vis.size else 0.0
                zst = 2 * a * np.sin(min(phe, np.pi / 2 - tc) / 2)
                exp = Vm * zst
                check(1, 'fillet excess projected area == Vm*z(phi*)  '
                      '[theta_c %2.0f, %s]' % (tcd, tag), got, exp,
                      3e-5, 'a telescoping identity, exact for the continuum; '
                      'the residual is the midpoint rule on the visible arc, '
                      'measured at 6e-6 relative on 64 nodes', unit='m',
                      rel=True)
        finally:
            (R._mph, R.MENIS_WD, R.MENIS_D, R.MENIS_Z, R.MENIS_SIN,
             R.MENIS_COS, R.MENIS_REACH, R.PHI_W) = old

    # ------------------------------------------------ 4. the brute-force march
    # The identity above is blind to the SHAPE -- it telescopes to the endpoints
    # -- and the RK4 row does not know about the eye. This one is neither. A
    # parallel fan of rays is cast at the RK4-marched polyline and each ray is
    # MARCHED until it passes below the surface; the tilt of the facet it lands
    # on is recorded, and the rays are histogrammed into the shipped
    # quadrature's own cells. What that measures is the projected area PER CELL
    # -- rays per cell times the fan spacing -- which is what the deposit's
    # placement depends on and what neither of the rows above can see. No
    # quadrature, no closed form, no telescoping: the geometric definition of a
    # projection, counted.
    tc = 0.0
    oph, odd, ozz = _menis_ode(R, tc, a, nstep=200000)
    ph, wd, dd, zz, sn, cs, reach = R.menis_tables(tc, a, R.MENIS_N)
    keep = odd <= reach
    pd, pz = odd[keep], ozz[keep]
    for Vm0, Vz0 in ((0.51, 0.46), (0.216, 0.197)):
        vn = np.hypot(Vm0, Vz0)
        um, uz = Vm0 / vn, Vz0 / vn              # in-plane unit view, toward eye
        # fan axis: perpendicular to the view, in the (poolward, up) plane
        ex_, ez_ = -uz, um
        M, S = 4000, 1200
        qq = np.linspace(-uz * reach - 2e-3, um * (2 * a) + 2e-3, M)
        dq = float(qq[1] - qq[0])
        ex_, ez_ = -uz, um                        # the fan's own axis

        def solid(tt):
            """Is the marched point inside the liquid or the wall? The fillet
            below its own surface, and everything at d < 0, which is the wall."""
            rd = qq * ex_ + 0.05 * um - um * tt
            rz = qq * ez_ + 0.05 * uz - uz * tt
            zs = np.where(rd > reach, 0.0,
                          np.interp(np.clip(rd, 0.0, reach), pd, pz))
            return (rd < 0.0) | (rz <= zs), rd, rz

        # stage 1: a coarse march to BRACKET the first entry. The crest is
        # 30 um of d and a uniform step fine enough to resolve it over 100 mm
        # of march would be 4e7 samples, so the grid brackets and a bisection
        # finishes -- still a march, with a root-find on its own predicate.
        tg = np.linspace(0.0, 0.10, S)
        inside = np.zeros((M, S), bool)
        for i in range(S):
            inside[:, i] = solid(tg[i])[0]
        hit = inside.any(1)
        first = np.argmax(inside, 1)
        lo = tg[np.maximum(first - 1, 0)]
        hi = tg[first]
        for _ in range(50):                       # stage 2: bisect the bracket
            mid = .5 * (lo + hi)
            sm_, _, _ = solid(mid)
            lo = np.where(sm_, lo, mid)
            hi = np.where(sm_, mid, hi)
        _, hd, hz = solid(hi)
        # a ray that passes over the crest lands on the WALL above the fillet,
        # not on the fillet; the fillet's own top is at z = h
        onfil = hit & (hd >= -1e-9) & (hd <= reach) & (hz <= pz[0] + 1e-9)
        meas = float(onfil.sum()) * dq * vn
        ndv, wf, wl, wo, isil = R._menis_weights(np.array([um * vn]),
                                                 np.array([uz * vn]))
        # the quadrature truncates the fillet's log-divergent outer tail at
        # d = reach, where the true surface still stands z(reach) above the
        # far field; the march sees that stump and the sum does not, so it is
        # subtracted rather than absorbed into a tolerance
        want = float(wf.sum()) - um * vn * float(pz[-1])
        check(3, 'fillet projected area, quadrature vs a %d-ray march of the '
              'RK4 profile  [Vm = %.3f]' % (M, um * vn), meas, want,
              4 * dq * vn,
              'the fan resolves a projection to one spacing, %.2f um, and each '
              'of the two ends can lose or gain a ray; 4 spacings is the '
              'tolerance' % (1e6 * dq), unit='m')
        info(3, '  ... rays landing on the fillet  [Vm = %.3f]' % (um * vn),
             '%d of %d cast, over a fan %.1f mm wide'
             % (int(onfil.sum()), M, 1000 * (qq[-1] - qq[0])),
             'the rest pass over the crest onto the wall, or outside the reach '
             'onto flat water')

    # ---------------------------------------- 5. the deposit, integrated back
    # THE CLOSURE ACROSS ALL THREE TERMS. Hand `meniscus` a scene of unit
    # radiance -- sky, coping undercut and everything under the water all 1, sun
    # off -- and the two columns become F*w_fil + (1-F)*w_fil = w_fil and
    # F0*w_flt + (1-F0)*w_flt = w_flt, whatever F is. What the shipped function
    # then deposits, integrated across the waterline and multiplied back by the
    # |v_z| it divided out, must be the excess projected area of row 3.
    #
    # This is one assertion over four things the code does separately: the node
    # weights, the Fresnel split (which must be a partition of unity across the
    # reflected and transmitted columns, not two independent weightings), the
    # folded Gaussian's normalisation, and the fold at d = 0 that reflects flux
    # back out of the wall. None of them is computed anywhere as a total, so
    # there is no line of render.py this row can be reading back.
    # a unit scene: sky, coping undercut and everything under the water all 1,
    # and the sun's disc switched off so that what is left is exactly the two
    # environment-weighted columns. `sail_vis` is stubbed with it because the
    # slice does not build the shade-sail map and the disc term is the only
    # caller; with L_SUN zero it multiplies nothing.
    stash = (R._env_menis, R._menis_under, R.EDGE_REFL, R.L_SUN, R.sail_vis)
    R._env_menis = lambda rx, ry, rz: np.ones((np.asarray(rx).size, 3))
    R._menis_under = lambda sid, u, v, sm, cyl, tz, mode: np.ones((sid.size, 3))
    R.EDGE_REFL = np.ones(3)
    R.L_SUN = np.zeros(3)
    R.sail_vis = lambda x, y: np.ones(np.asarray(x).shape)
    try:
        for P, tag in ((np.array([1.40, R.Y1 + R.SLIP, 0.]), 'north wall, 8.4 m'),
                       (np.array([5.40, R.Y1 + R.SLIP, 0.]), 'north wall, 4.8 m')):
            nd, span = 6001, 0.080
            gx, gy, _ = R.pool_grad(P[0], P[1])
            ddv = np.linspace(0., span, nd)
            px, py = P[0] - gx * ddv, P[1] - gy * ddv
            dv = np.stack([px, py, np.zeros(nd)], 1) - R.EYE[None]
            tt = np.linalg.norm(dv, axis=1)
            dv /= tt[:, None]
            fpp = tt * R.PIXANG / np.maximum(np.abs(dv[:, 2]), .10) * R.SS
            st = R.surf_stats(px, py, fpp)
            Lc = R.meniscus(px, py, R.SLIP - ddv, dv, fpp, *st)
            vz = np.maximum(-dv[:, 2], .05)
            got = float(np.trapezoid(Lc[:, 1] * vz, ddv))
            # what it must come to: the folded kernel puts each node's excess at
            # that node's own d and integrates to 1 over d >= 0, so the total is
            # the sum of the per-node excesses evaluated at the view direction
            # each node actually sits under -- not at the fan's mean, which is a
            # different direction 40 mm out
            Vm = -(dv[:, 0] * -gx + dv[:, 1] * -gy)
            jn = np.searchsorted(ddv, R.MENIS_D)
            ndv, wf, wl, wo, isil = R._menis_weights(Vm[jn], -dv[jn, 2])
            exp = float(np.diagonal(wf + wo - wl).sum())
            check(3, 'the deposit integrates back to the excess area  [%s]' % tag,
                  got, exp, 1e-3,
                  'the kernel is normalised over d >= 0, so the identity is '
                  'exact; what is left is that K is up to 3 mm wide and the '
                  'view direction turns 0.02 deg across that, worth 4e-4 in '
                  'Vm, plus the trapezoid on a %d-point fan at 13 um' % nd,
                  unit='m', rel=True)

        # -------------------------------------------------------- 6. the limits
        # Both are forced and neither can be satisfied by construction. As the
        # capillary length goes to zero the fillet has no size; as the contact
        # angle goes to 90 degrees it has no climb. In both the whole term must
        # collapse to zero and leave EXACTLY the flat surface -- and because the
        # excess is Vm*z(phi*) and z(phi*) = 2a sin(phi*/2), it must collapse
        # LINEARLY in each. A missing subtraction is what this catches: without
        # it the integrand is INT dx (F L cos_i/cos phi), whose dx ~ a dphi/phi
        # diverges logarithmically at the flat end, so it does not go to zero as
        # phi_w -> 0 at all -- it goes to a constant times log N.
        P = np.array([2.40, R.Y1 + R.SLIP, 0.])
        nd, span = 4001, 0.080
        gx, gy, _ = R.pool_grad(P[0], P[1])
        ddv = np.linspace(0., span, nd)
        px, py = P[0] - gx * ddv, P[1] - gy * ddv
        dv = np.stack([px, py, np.zeros(nd)], 1) - R.EYE[None]
        tt = np.linalg.norm(dv, axis=1)
        dv /= tt[:, None]
        fpp = tt * R.PIXANG / np.maximum(np.abs(dv[:, 2]), .10) * R.SS
        st = R.surf_stats(px, py, fpp)
        vz = np.maximum(-dv[:, 2], .05)

        def dep(theta_c, aa):
            old = (R._mph, R.MENIS_WD, R.MENIS_D, R.MENIS_Z, R.MENIS_SIN,
                   R.MENIS_COS, R.MENIS_REACH, R.PHI_W, R.CAP_A)
            t = R.menis_tables(theta_c, aa, R.MENIS_N)
            (R._mph, R.MENIS_WD, R.MENIS_D, R.MENIS_Z, R.MENIS_SIN,
             R.MENIS_COS, R.MENIS_REACH) = t
            R.PHI_W, R.CAP_A = np.pi / 2 - theta_c, aa
            try:
                Lc = R.meniscus(px, py, R.SLIP - ddv, dv, fpp, *st)
                return float(np.trapezoid(Lc[:, 1] * vz, ddv))
            finally:
                (R._mph, R.MENIS_WD, R.MENIS_D, R.MENIS_Z, R.MENIS_SIN,
                 R.MENIS_COS, R.MENIS_REACH, R.PHI_W, R.CAP_A) = old

        base = dep(0.0, a)
        for f in (1e-1, 1e-2, 1e-3):
            check(1, 'limit a -> 0: the deposit is linear in the capillary '
                  'length  [a/%g]' % (1 / f), dep(0.0, a * f), base * f,
                  2e-3, 'the excess is Vm*2a sin(phi*/2) and phi* does not '
                  'depend on a, so the deposit is exactly proportional to a; '
                  '2e-3 relative is the fan quadrature', unit='m', rel=True)
        # theta_c -> 90 deg: z(phi*) = 2a sin((90-theta_c)/2) -> a*(90-theta_c)
        for tcd in (60.0, 80.0, 89.0, 89.9):
            tc = np.deg2rad(tcd)
            got = dep(tc, a)
            exp = base * np.sin((np.pi / 2 - tc) / 2) / np.sin(np.pi / 4)
            check(1, 'limit theta_c -> 90 deg: the deposit collapses with the '
                  'CLIMB  [theta_c = %4.1f deg]' % tcd, got, exp, 0.03,
                  'the excess is Vm*z(phi_w) = Vm*2a sin(phi_w/2), so the ratio '
                  'to theta_c = 0 is sin(phi_w/2)/sin(45 deg) exactly; 3% '
                  'covers the environment\'s own variation over the collapsing '
                  'sweep, which is not part of the identity', unit='m', rel=True)
        info(1, '  ... and at theta_c = 90 deg exactly', '%.3e m'
             % dep(np.pi / 2 - 1e-9, a),
             'the fillet is gone and the term is the flat surface minus itself')
    finally:
        (R._env_menis, R._menis_under, R.EDGE_REFL, R.L_SUN,
         R.sail_vis) = stash

    # ------------------------------------------------- 7. the reachability algebra
    # render.py claims R(phi).L = sin A sin B + cos A cos B cos(2(phi - phi*))
    # EXACTLY, with A = asin(-v.t), B = asin(L.t), phi* = (theta_v + theta_l)/2,
    # and reads two consequences off it: the closest the mirror direction comes
    # to the sun is beta = A - B, and that closest approach is zero exactly
    # where (L + v).t = 0. Here the reflection is done literally -- build n(phi),
    # reflect v about it, dot with L -- over random configurations.
    rng = np.random.default_rng(20260812)
    K = 4000
    m3 = np.array([1., 0., 0.])
    t3 = np.array([0., 1., 0.])
    z3 = np.array([0., 0., 1.])
    ph = np.linspace(0, np.pi / 2, K)
    n3 = np.sin(ph)[:, None] * m3 + np.cos(ph)[:, None] * z3
    err = errb = errs = 0.0
    for _ in range(60):
        V = rng.normal(size=3)                    # toward the eye: V_z > 0
        V /= np.linalg.norm(V)
        V[2] = abs(V[2])
        V /= np.linalg.norm(V)
        L = rng.normal(size=3)                    # toward the sun: L_z > 0
        L /= np.linalg.norm(L)
        L[2] = abs(L[2])
        L /= np.linalg.norm(L)
        ndv = n3 @ V
        Rv = 2 * ndv[:, None] * n3 - V[None]      # the mirror direction
        dot = Rv @ L
        A = np.arcsin(np.clip(-(V @ t3), -1, 1))
        B = np.arcsin(np.clip(L @ t3, -1, 1))
        thv = np.arctan2(V @ m3, V @ z3)
        thl = np.arctan2(L @ m3, L @ z3)
        phs = .5 * (thv + thl)
        pred = np.sin(A) * np.sin(B) + np.cos(A) * np.cos(B) * np.cos(2 * (ph - phs))
        err = max(err, float(np.max(np.abs(dot - pred))))
        # the closest approach over the WHOLE family of tilts, not the clipped
        # sweep: max over phi of cos(2(phi - phi*)) is 1, so the maximum is
        # cos(A - B) identically
        phf = np.linspace(phs - np.pi, phs + np.pi, 8193)
        nf = np.sin(phf)[:, None] * m3 + np.cos(phf)[:, None] * z3
        Rf = 2 * (nf @ V)[:, None] * nf - V[None]
        errb = max(errb, abs(float(np.max(Rf @ L)) - np.cos(A - B)))
        # and it reaches 1 -- the mirror direction hits the sun exactly -- iff
        # (L + V).t = 0. Constructed, not scanned: rotate L about the vertical
        # until its t-component matches -V.t, which is the half-vector residual
        # written the other way round.
        lt = -(V @ t3)
        lm = L @ m3
        lz = L @ z3
        sc = np.sqrt(max(1.0 - lt * lt, 0.0)) / max(np.hypot(lm, lz), 1e-12)
        L2 = lt * t3 + sc * (lm * m3 + lz * z3)
        errs = max(errs, abs(float(np.max(Rf @ L2)) - 1.0))
    check(1, 'R(phi).L closed form vs literal reflection, max |err| over 60 '
          'random (V, L)', err, 0.0, 1e-14,
          'both sides are exact algebra in double precision on a 4000-node '
          'sweep; 1e-14 is round-off')
    check(1, 'closest approach of the mirror direction to the sun == cos(A - B)',
          errb, 0.0, 3e-7,
          'the 8193-node scan can miss the peak by half a spacing, dphi/2 = '
          '3.8e-4 rad, and a quadratic maximum then reads low by (2*dphi/2)^2/2 '
          '= 3e-7; the tolerance is that grid error, not a fit')
    check(1, 'the sun is EXACTLY reachable iff (L + V).t = 0, over 60 '
          'constructed configurations', errs, 0.0, 3e-7,
          'same scan, same grid error. L is rebuilt with L.t = -V.t and nothing '
          'else changed, so the residual is zero by construction and the mirror '
          'direction must pass through the sun for some tilt')

    # ----------------------------------------- 8. the internal-reflection term
    # THE HYPOTHESIS THAT DID NOT SURVIVE, kept as a row so that it cannot be
    # rebuilt by accident. Past 48.5 deg the fillet's underside is a perfect
    # mirror, and the fillet sweeps every tilt, so the critical-angle condition
    # is met inside it by construction. What is not met is arrival: writing the
    # transmitted direction as t = eta i + f n, f = eta cos_i - cos_t is
    # NEGATIVE for every incidence whenever eta < 1, and a camera above the
    # water always has eta = 1/n < 1. With n_z = cos(phi) >= 0 on any meniscus
    # against a vertical wall, t_z = eta i_z + f cos(phi) < 0 identically: the
    # refracted camera ray descends, always, and cannot reach a surface above
    # it. Two rows -- the algebraic sign, and a scan of the shipped `refract`
    # over every wall, every point along it and every tilt.
    ci = np.linspace(0.0, 1.0, 200001)
    eta = 1.0 / R.IOR[1]
    f = eta * ci - np.sqrt(1.0 - eta ** 2 * (1.0 - ci ** 2))
    check(1, 'refracting INTO water: f = eta cos_i - cos_t < 0 at every '
          'incidence', float(f.max()), eta - 1.0, 1e-12,
          'f is monotone in cos_i and its supremum is at normal incidence, '
          'where f = eta - 1; anything >= 0 would be a ray bending away from '
          'the normal into a denser medium')
    worst = -1e30
    nup = 0
    ntot = 0
    for m3, t3 in ((np.array([-1., 0., 0.]), np.array([0., 1., 0.])),
                   (np.array([0., -1., 0.]), np.array([1., 0., 0.])),
                   (np.array([1., 0., 0.]), np.array([0., -1., 0.])),
                   (np.array([0., 1., 0.]), np.array([-1., 0., 0.]))):
        ax = 0 if m3[0] else 1
        u = np.linspace(0.02, (R.Y1 - R.Y0 if ax == 0 else R.X1 - R.X0) - .02, 300)
        c = (R.X1 + R.SLIP) if (ax == 0 and m3[0] < 0) else \
            (R.X0 - R.SLIP) if ax == 0 else \
            (R.Y1 + R.SLIP) if m3[1] < 0 else (R.Y0 - R.SLIP)
        P = np.stack([np.full(u.size, c), u, np.zeros(u.size)], 1) if ax == 0 \
            else np.stack([u, np.full(u.size, c), np.zeros(u.size)], 1)
        V = P - R.EYE[None]
        V /= np.linalg.norm(V, axis=1)[:, None]
        ph = np.linspace(0.0, np.pi / 2, 301)
        nx = (np.sin(ph)[None, :] * m3[0])
        ny = (np.sin(ph)[None, :] * m3[1])
        nz = np.broadcast_to(np.cos(ph)[None, :], (u.size, ph.size))
        ix = np.broadcast_to(V[:, 0:1], nz.shape)
        iy = np.broadcast_to(V[:, 1:2], nz.shape)
        iz = np.broadcast_to(V[:, 2:3], nz.shape)
        nxb = np.broadcast_to(nx, nz.shape)
        nyb = np.broadcast_to(ny, nz.shape)
        tx, ty, tz = R.refract(ix.ravel(), iy.ravel(), iz.ravel(),
                               nxb.ravel(), nyb.ravel(), nz.ravel(), eta)
        front = -(ix.ravel() * nxb.ravel() + iy.ravel() * nyb.ravel()
                  + iz.ravel() * nz.ravel()) > 1e-9
        ntot += int(front.sum())
        nup += int((front & (tz > 0)).sum())
        worst = max(worst, float(np.max(np.where(front, tz, -1e30))))
    check(1, 'no refracted camera ray travels upward: t_z over %d front-facing '
          '(wall, position, tilt) samples' % ntot, worst, -1.0, 1.0,
          'the assertion is the SIGN; the tolerance admits any negative t_z and '
          'nothing else, so a single upward ray fails the row')
    check(1, 'fillet-underside TIR: rays reaching it out of %d' % ntot,
          float(nup), 0.0, 0.0, 'exact count, not a fraction')
    check(1, 'MENIS_TIR_REACH (solid angle of the fillet\'s underside from any '
          'camera above the water)', R.MENIS_TIR_REACH, 0.0, 0.0,
          'zero by the sign of f, for every eye, every wall and every contact '
          'angle -- not a small angle this frame happens to miss', unit='sr')


def tier3_wake(fld, wkm):
    # THE EIKONAL SOLVE, checked against its own conserved quantity. A pattern
    # held stationary in the lab frame has H(x,k) = sigma(k) + k.U(x) = 0, and
    # H is conserved along the rays of its own Hamiltonian system. So |H|
    # relative to sigma measures the RK2 integrator's drift, independently of
    # anything the reconstruction does with the result.
    J = wkm.Jet(fld.JET_XY[0], fld.JET_XY[1], depth=fld.JET_H,
                tilt_deg=np.degrees(fld.JET_TILT), az_deg=np.degrees(fld.JET_AZ),
                d=fld.D_NOZZLE, dp_bar=fld.DP_BAR, cd=fld.CD,
                S=fld.S_SPREAD, B=fld.B_DECAY)
    def H_of(dt, n_step):
        X, K, PH, A = wkm.trace(J, n_psi=31, n_step=n_step, dt=dt)
        km = np.hypot(K[..., 0], K[..., 1])
        om = np.sqrt(wkm.G * km + (wkm.SIG / wkm.RHO) * km ** 3)
        ux, uy = J.drift(X[..., 0], X[..., 1])
        return (om + K[..., 0] * ux + K[..., 1] * uy) / om, km, X, K

    Hn, km, X, K = H_of(0.02, 300)
    # -- THE LAUNCH, against the exact stationary condition. A wave standing
    # still in a current c = U cos(psi) satisfies sigma(k) = k c, i.e.
    #     (sigma_t/rho) k^2 - c^2 k + g = 0,
    # whose gravity root is k = rho(c^2 - sqrt(c^4 - c_min^4))/(2 sigma_t) and
    # whose deep-water limit is the k = g/c^2 the file launches. The two agree
    # where the wake actually lives (10-35 cm) and part company at the fan edge,
    # where c -> c_min and the exact root is k = sqrt(rho g/sigma_t), i.e.
    # lambda_min = 17.1 mm exactly.
    U = np.hypot(*J.drift(X[0, :, 0], X[0, :, 1]))
    cs = np.abs(K[0, :, 0] * (-J.ax[0]) + K[0, :, 1] * (-J.ax[1])) / km[0]
    c = U * cs
    kex = wkm.RHO * (c ** 2 - np.sqrt(np.maximum(c ** 4 - wkm.C_MIN ** 4, 0))) \
        / (2 * wkm.SIG)
    check(3, 'wake launch satisfies sigma(k) == k U cos(psi) exactly',
          float(np.abs(Hn[0]).max()), 0.0, 0.01,
          'the wake band carries 10-35 cm, where the deep-water gravity limit of '
          'the stationary condition is good to 1%; a launch outside that is '
          'launching a wave that does not stand still', 'rel')
    info(3, '  ... launched k / exact capillary-gravity root',
         'psi = 0: %.4f;  fan edge: %.4f (lambda %.1f mm launched vs %.1f exact)'
         % (float((km[0] / kex)[np.argmax(cs)]),
            float((km[0] / kex)[np.argmin(cs)]),
            1000 * 2 * np.pi / float(km[0][np.argmin(cs)]),
            1000 * 2 * np.pi / float(kex[np.argmin(cs)])),
         'the deep-water limit is exact on the axis and 28% out at the fan edge')
    # -- THE INTEGRATOR, by convergence rather than by a threshold. If dx/dt and
    # dk/dt are the flow of the same H the rays are evaluated against, then H is
    # conserved and the drift away from its launch value falls as dt^2. Halving
    # dt must therefore cut the drift by about four. This assertion has no
    # tolerance in it at all: either the equations are the Hamiltonian's or they
    # are not, and no step size fixes the second case.
    d1 = float(np.abs(Hn - Hn[0][None, :]).max())
    Hn2, _, _, _ = H_of(0.01, 600)
    d2 = float(np.abs(Hn2 - Hn2[0][None, :]).max())
    check(3, 'eikonal drift |H - H0|/sigma falls when dt is halved', d2 / d1,
          0.0, 0.6,
          'a consistent RK2 flow gives 0.25; 0.6 admits a first-order term and '
          'still fails a drift that does not fall at all', 'ratio')
    info(3, '  ... drift at dt = 0.02 and dt = 0.01',
         'max %.4f -> %.4f (ratio %.2f)' % (d1, d2, d2 / d1),
         'a systematic error, not a step-size one')
    info(3, '  ... Jet.grad finite difference vs the jet half-width',
         'e = 10 mm against r_1/2 = %.0f mm at s = 0.5 m'
         % (1000 * J.S * 0.5),
         'a fixed 1 cm central difference on a 47 mm structure')
    # -- the wake band's reconstruction reaches field.py through a grid and a
    # bilinear read; grid and point paths must agree there too.
    xs = np.linspace(6.2, 7.8, 48)
    ys = np.linspace(1.6, 2.8, 32)
    X2, Y2 = np.meshgrid(xs, ys)
    a = fld._wake(X2.astype(np.float32), Y2.astype(np.float32))
    b = fld._wake(X2.ravel().astype(np.float32), Y2.ravel().astype(np.float32))
    check(3, 'wake grid and point lookups are the same field',
          float(max(np.abs(a[0].ravel() - b[0]).max(),
                    np.abs(a[1].ravel() - b[1]).max())), 0.0, 1e-6,
          'the same bilinear read reshaped; float32 round-off only')


# ------------------------------------------------------------------- reporting
UNVALIDATED = """
WHAT IS STILL UNVALIDATED, so that this file is also a map of the gaps.

  NOT TESTED AT ALL -- no external reference exists or none was found
    * The five-band decomposition itself. WIND_RMS, REVERB_RMS and JNEAR_RMS are
      chosen, the chapter's own far-field figures were read off this code, and
      Cox & Munk can only bracket the total (it does, above). Nothing here pins
      an individual band's level.
    * ETA_C, C_SRC, SIG_EST, RIS_HMIN, the contact angle, the wake carrier
      ratio, the bead width -- the file's own `?` markers. Each is a place the
      reference cannot answer; none has moved.
    * The materials: LINER_TINT, the stone, the paving, the tile grout, the
      sail's transmittance. These are chosen to match a photograph and there is
      no measurement behind any of them.
    * The tone map, the exposure and L_WHITE. There is no external referent for
      a look.
    * The Gabor reconstruction of the WAKE band as shipped. The tests above
      validate the OPERATOR -- that a lattice of atoms reproduces a plane wave,
      and that an atom at the shipped window floor carries its own wavenumber --
      not the deposit lattice the traced rays actually make, whose amplitudes,
      phases and window widths all vary along the ray. A direct atom-by-atom sum
      at scattered points would do it and costs a full re-trace.
    * The wake's amplitude: wave action A^2 |dx/dt| W = const is asserted along
      the ray tube and never checked, and the `esc` cutoff at c_min is a choice
      of form. Only the ray GEOMETRY is tested here.

  TESTED ONLY AGAINST ITSELF, and would need a second implementation
    * The whole camera pass: projection, subsample grid, adaptive edge refine,
      the spectral Latin square. Nothing here renders a pixel.
    * The underwater camera's RADIANCE, as against its geometry. The window's
      half angle is measured off the frame's own ray DIRECTIONS, the interface
      against closed forms, and the tracer against a march -- but no row here
      reads a wall map, so nothing external says the mirrored twin shows the
      right wall at the right place. What checks that is render.py's own
      waterline measurement, which walks a column across the north wall's
      waterline and reports the image, the wall and the step between them; it
      is a consistency argument, not an external one.
    * Two `?` in that pass, both named in render.py and neither testable here:
      the world above the water is `sky()` alone, so the outermost ~0.2 deg of
      the window shows sky where a photograph shows the coping and the deck;
      and the unresolved slope variance is not fed to a refracted lobe, though
      the footprint that generates it is measured every run.
    * The shade sail's shadow map, the freeboard band, the waterline, the deck
      and liner gathers. (The coping's height-field march is no longer in this
      list: `stone_vis` is now checked against a 2 mm shadow march of the same
      field, on 672 points over all four sides. What is still untested is the
      SAIL half of it, which is stubbed to 1 for that row.)
    * `_riser_shade` and the riser bounce MAP -- the closure of its estimator is
      tested, the map it produces is not. Nor is the term that was found to be
      striping the step unit: `_riser_shade` reads the BED's caustic map as a
      stand-in for a caustic on a vertical face, and nothing here says the point
      it now reads -- the refracted beam's continuation to the face's own foot --
      is the right one. What says it is render.py's own arc-scale print, which
      measures each of the four terms' structure along AND up the face and would
      show a height-independent term as a z/arc of zero.
    * The WALL bounce map, and here the gap has a shape worth naming. What is
      tested is the estimator's GEOMETRY: the shipped 960-direction lattice
      against `_ris_closure` over the wall's own height range, and the bed <->
      wall transfer against the exact rectangle view factor by reciprocity, both
      with a unit radiance and an empty box substituted for the scene. What is
      NOT tested is that render.py APPLIES that transfer to the walls -- no row
      here reads a wall map, because building one costs a caustic pass. A wall
      left dark would still pass every row in this file; what would catch it is
      render.py's own `wall bounce:` print, which measures the term's size every
      run, and the ordering verdict in the colour regression.
    * The bed-return (TIR) map: TIR_FRAC and TIR_VERT are tested, the 2.4 M-ray
      splat that spends them is not. Its TRUNCATION is now priced -- one bounce
      over the TIR cone against the closed series, in a row above -- but that row
      compares two closed forms; no row here reads the splat's own output, and
      the 58% of the cone it drops on the walls is measured only by render.py's
      own print. This is the largest single gap in the file's transport and it is
      the one the README's water/stone section ends on.

  TESTED IN PART
    * The meniscus. Its GEOMETRY is now well covered -- a force balance on the
      tabulated columns, an RK4 march of the Young-Laplace IVP, a
      projected-area identity, a brute-force ray march, a unit-radiance closure
      that integrates the shipped deposit back to that identity, and the two
      limits a -> 0 and theta_c -> 90 deg. What is NOT covered is the RADIANCE
      the two columns read: `_env_menis` and the traced bed / wall / riser maps
      are both stubbed out to unit for the closure row, so nothing here says the
      line is the right COLOUR or the right BRIGHTNESS -- only that it carries
      the flux the geometry allows and splits it correctly between reflection
      and transmission -- a property that survives the 1/n^2 only because the
      divisor lives inside `_menis_under`, so both columns are air-side in the
      caller's units. The near-wall fold (Vm < 0) is still a bounded
      approximation rather than a model; what changed is that the bound is now
      ENFORCED -- `meniscus` raises on any picture path that reaches it, and two
      rows here fire it both ways.
    * Fresnel: the exact equations, the Brewster zero and the diffuse integrals
      are covered. The roughness correction's two constants (2.69 and 22.7,
      Bruneton et al. 2010) are used as published and are not checked against
      the paper's own data.
    * The caustic pass: exact for one sinusoid under a vertical sun over a flat
      bed. Not tested for an oblique sun (the obliquity factor the chapter
      mentions), for a sloped or stepped receiver, or for two crossed sinusoids,
      where the Jacobian is a 2x2 determinant and folds become cusps.
    * The sky: flux and peak are closed form. The elevation gradient
      SKY_HOR -> SKY_TOP is a choice with no referent, and the circumsolar ratio
      the file prints against the measured ~0.05 for a clear sky is not lifted
      here because the file already records it as a known shortfall.
    * The eikonal solve: stationarity at launch and conservation along the ray
      are tested. The film damping `alpha_eff`, its LAM_FILM blend and the
      inextensible-film coefficient 0.3536 are used as stated and are checked
      against nothing.
    * The jet: S, B and the profile are literature. The turbulent SLOPE the boil
      forces is eta ~ ETA_C u'^2/g with ETA_C = 1, and that is a scaling
      argument, not a measurement.
"""


# ======================== TIER 1 / 3: THE CAMERA UNDER THE WATER
# The pass that flips the assert. Every row here is about something that could
# not be reached from any call site before it existed: `eta > 1`, `refract()`'s
# null return, and the interface crossed in the GAINING direction.
#
# THE TRAP THIS FILE HAS ALREADY BEEN CAUGHT IN ONCE is two "independent
# methods" transcribed from one comment (TIR_VERT, and both rows were wrong
# together). So each pair below is named with what it does NOT share:
#   * the window's half angle is measured off the FRAME's own ray directions
#     through render.py's `is_tir`, and compared with asin(1/n) -- a formula
#     that appears nowhere in the pass;
#   * the onset of the mirror regime is bisected on `refract()`'s null return
#     and compared with a scan of the exact reflectance reaching 1 -- one solves
#     for cos t and tests its sign, the other forms amplitude ratios;
#   * the n^2 gain is composed through render.py's `into_water` and
#     `uw_interface` on the water side, and closed against a hemispherical
#     integral of THIS file's own `fresnel_exact` on the air side. The two share
#     the three indices and nothing else.
def tier_underwater(R):
    n = R.IOR

    # ---- the sibling tracer did not become a second opinion ------------------
    # `scene_hit_under` handles rays of either sign; on the downgoing half it
    # must reproduce `scene_hit` EXACTLY, or the mirrored twin and the hero's
    # own bed would be two different pools.
    rng = np.random.default_rng(20260812)
    N = 120000
    d = rng.normal(size=(N, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    d[:, 2] = -np.abs(d[:, 2])
    px = rng.uniform(R.XW0 + 1e-3, R.XW1 - 1e-3, N)
    py = rng.uniform(R.YW0 + 1e-3, R.YW1 - 1e-3, N)
    for lbl, pz in (('from the surface', 0.0),
                    ('from mid-depth', rng.uniform(-1.3, -0.05, N))):
        a = R.scene_hit(px, py, d[:, 0], d[:, 1], d[:, 2], pz)
        b = R.scene_hit_under(px, py, pz, d[:, 0], d[:, 1], d[:, 2])
        same = all(np.array_equal(np.asarray(a[k]), np.asarray(b[k]))
                   for k in range(5))
        check(1, 'scene_hit_under == scene_hit, downgoing %s' % lbl,
              float(same), 1.0, 0.0,
              'the sibling must reproduce the five-plane solve bit for bit on '
              'the half it shares -- id, u, v, distance and cylinder, over '
              '120000 random rays. No tolerance: equality or a bug')

    # ---- and its UPGOING half against a brute-force march --------------------
    # The half no existing code covers, so it gets the treatment `scene_hit`
    # itself gets: a 0.5 mm march of the water body's own definition (inside the
    # walls, under the surface, over `bed_z`) against the analytic solve.
    M = 20000
    dm = rng.normal(size=(M, 3))
    dm /= np.linalg.norm(dm, axis=1, keepdims=True)
    qx = rng.uniform(R.XW0 + .02, R.XW1 - .02, M)
    qy = rng.uniform(R.YW0 + .02, R.YW1 - .02, M)
    qz = rng.uniform(-1.35, -0.02, M)
    ok = qz > R.bed_z(qx, qy) + .02
    qx, qy, qz, dm = qx[ok], qy[ok], qz[ok], dm[ok]
    sid, _u, _v, sm, _c = R.scene_hit_under(qx, qy, qz, dm[:, 0], dm[:, 1], dm[:, 2])
    step = 5e-4
    tm = np.full(qx.size, np.inf)
    alive = np.ones(qx.size, bool)
    for i in range(1, int(9.0 / step)):
        t = i * step
        x, y, z = qx + dm[:, 0] * t, qy + dm[:, 1] * t, qz + dm[:, 2] * t
        out = alive & ~((x > R.XW0) & (x < R.XW1) & (y > R.YW0) & (y < R.YW1)
                        & (z < 0.0) & (z > R.bed_z(x, y)))
        tm[out] = t
        alive &= ~out
        if not alive.any():
            break
    err = np.abs(tm - sm)
    check(3, 'scene_hit_under vs a 0.5 mm march of the water body',
          float(np.percentile(err, 99.9)), 0.5 * step, 0.5 * step,
          'a forward march overshoots by half a step on average and one step at '
          'worst, so the p99.9 is compared against half a step with half a step '
          'of slack. The p100 is not used: a ray tangent to a riser at exactly '
          'the cap height is a measure-zero disagreement between two exact '
          'solids, and 1 ray in 36000 finds one', 'm')
    info(3, '  ... the same march, median and worst',
         'median %.4f mm | max %.1f mm | %d rays, %.0f%% of them upgoing'
         % (1000 * np.median(err), 1000 * err.max(), qx.size,
            100 * (dm[:, 2] > 0).mean()),
         'the median is the march\'s own half-step; the max is the tangency')
    info(1, '  ... what an upgoing ray can now hit',
         'surface %.1f%% | riser %.1f%% | bed %.1f%% | walls %.1f%%'
         % (100 * (sid == 6).mean(), 100 * (sid == 5).mean(),
            100 * (sid == 0).mean(), 100 * ((sid >= 1) & (sid <= 4)).mean()),
         'id 6 is the new one -- the still surface seen from below, which is '
         'where a ray leaves the tracer and meets the interface')

    # ---- THE WINDOW'S HALF ANGLE, OFF THE FRAME'S OWN GEOMETRY --------------
    # No formula enters this. Take the camera's own ray directions, flat water,
    # and ask render.py's `uw_interface` -- i.e. `refract` and `is_tir` -- which
    # of them found a mirror. The rim is then bracketed between the steepest ray
    # that still transmitted and the shallowest that did not, and asin(1/n) has
    # to lie inside that bracket. The bracket's width is the frame's own angular
    # sampling and nothing else, which is what makes this a measurement of the
    # renderer rather than of the tolerance.
    W_, H_, SS_ = R.W, R.H, R.SS
    jj = np.arange(0, W_ * H_, 7)                  # a coprime stride: all rows
    dv = R.uw_pixel_dirs(jj)
    pol = np.degrees(np.arccos(np.clip(dv[:, 2], -1, 1)))
    keep = (dv[:, 2] > 0) & (np.abs(pol - np.degrees(np.arcsin(1 / n[1]))) < 3.0)
    dv, pol = dv[keep], pol[keep]
    z0 = np.zeros(dv.shape[0])
    nz0 = R.normal_from_grad(z0, z0)
    pixang = np.degrees(R.UW_PIXANG)
    mids = []
    for c, nm in enumerate('RGB'):
        tir = R.uw_interface(dv, nz0[0], nz0[1], nz0[2],
                             np.full(dv.shape[0], n[c]), c)[3]
        lo, hi = pol[~tir].max(), pol[tir].min()
        mids.append(.5 * (lo + hi))
        tc = np.degrees(np.arcsin(1.0 / n[c]))
        check(1, 'Snell window off the frame == asin(1/n)  [%s]' % nm,
              .5 * (lo + hi), tc, max(.5 * (hi - lo), 1e-9),
              'the rim bracketed by the frame\'s own rays -- the steepest that '
              'transmitted (%.5f deg) and the shallowest that did not (%.5f) -- '
              'against the closed form. The tolerance IS the bracket, i.e. the '
              'frame\'s angular sampling; it is not a free parameter and it '
              'shrinks if the frame is rendered finer' % (lo, hi), 'deg')
    check(1, 'the rim\'s dispersive spread, red - blue, off the frame',
          mids[0] - mids[2],
          np.degrees(np.arcsin(1 / n[0]) - np.arcsin(1 / n[2])), 2 * pixang,
          'the difference of two bracket midpoints, each good to half the '
          'frame\'s pixel angle (%.5f deg)' % pixang, 'deg')
    info(1, '  ... the three rims and the README\'s figures',
         '%s deg against 48.6551 / 48.5190 / 48.2683'
         % np.round(np.degrees(np.arcsin(1 / n)), 4),
         'the same three constants that put the fringing on the bed caustics, '
         'used on a hard edge instead of a soft one')

    # ---- THE MIRROR REGIME IS TOTAL ----------------------------------------
    tirall = R.uw_interface(dv, nz0[0], nz0[1], nz0[2],
                            np.full(dv.shape[0], n[1]), 1)
    check(1, 'past the rim the reflectance is exactly 1, with no partial regime',
          float(tirall[4][tirall[3]].min()), 1.0, 0.0,
          'section G: "there is no partial regime out there". Every ray '
          '`is_tir` flags must carry R = 1 identically; no tolerance')
    info(1, '  ... and how close it gets from the transmitting side',
         'max R below the rim %.6f, at %.4f deg'
         % (tirall[4][~tirall[3]].max(),
            pol[~tirall[3]][np.argmax(tirall[4][~tirall[3]])]),
         'the rim is continuous in radiance, not a step: R rises to 1 like '
         'sqrt(theta_c - theta), so the transmitted column fades rather than '
         'being cut. What is discontinuous there is the DERIVATIVE')

    # ---- THE ONSET, FROM TWO FUNCTIONS THAT SHARE NO LINE -------------------
    # The green band already carries this row in tier1_snell; here it is run for
    # all three, through the shading path's own entry point rather than through
    # `refract` directly, so the pass cannot lose the branch by wrapping it.
    fr = np.linspace(0.0, np.pi / 2, 4000001)
    for c, nm in enumerate('RGB'):
        lo_, hi_ = 0.0, np.pi / 2
        for _ in range(200):
            mid = .5 * (lo_ + hi_)
            dd = np.array([[np.sin(mid), 0.0, np.cos(mid)]])
            t_ = R.uw_interface(dd, np.zeros(1), np.zeros(1), np.ones(1),
                                np.full(1, n[c]), c)
            lo_, hi_ = (mid, hi_) if not t_[3][0] else (lo_, mid)
        rr_ = fresnel_exact(np.cos(fr), 1.0 / n[c])[0]
        onset = float(fr[int(np.argmax(rr_ >= 1.0 - 1e-15))])
        check(1, 'uw_interface TIR onset == where exact Fresnel reaches 1  [%s]'
              % nm, np.degrees(.5 * (lo_ + hi_)), np.degrees(onset), 1e-4,
              'a bisection on the pass\'s own null return against a 4M-point '
              'scan of the exact water->air reflectance. Different code, and '
              'neither of them contains asin(1/n). 1e-4 deg is the scan\'s grid',
              'deg')

    # ---- REVERSIBILITY, WHICH IS WHY THERE IS ONLY ONE FRESNEL IN THE FILE --
    # `uw_interface` gets the INTERNAL reflectance out of the file's EXTERNAL
    # `fresnel` by evaluating it at the conjugate air-side angle. If that
    # identity failed, the whole window would carry the wrong weight.
    th = np.linspace(1e-4, np.arcsin(1 / n[1]) - 1e-5, 20001)
    dvr = np.stack([np.sin(th), np.zeros_like(th), np.cos(th)], 1)
    zz = np.zeros(th.size)
    Rw = R.uw_interface(dvr, zz, zz, np.ones(th.size),
                        np.full(th.size, n[1]), 1)[4]
    ci = np.cos(th)
    sa = n[1] * np.sin(th)
    ca = np.sqrt(np.maximum(1 - sa ** 2, 0.))
    rs = ((n[1] * ci - ca) / (n[1] * ci + ca)) ** 2
    rp = ((n[1] * ca - ci) / (n[1] * ca + ci)) ** 2
    check(1, 'R_water->air(theta_w) == R_air->water(theta_a)  [reversibility]',
          float(np.abs(Rw - .5 * (rs + rp)).max()), 0.0, 1e-12,
          'Stokes reversibility, exactly. The left side is the shipped path -- '
          'render.py\'s external `fresnel` read at the conjugate angle; the '
          'right is the water->air equations formed here from the two indices. '
          '1e-12 is double round-off over 20001 angles')

    # ---- THE n^2 RADIANCE GAIN ---------------------------------------------
    # First the identity that says the two directions are one law.
    L = np.array([[0.3, 0.7, 1.1], [2.0, 0.01, 5.0]])
    check(1, 'into_water(out_of_water(L)) == L',
          float(np.abs(R.into_water(R.out_of_water(L)) - L).max()), 0.0, 1e-15,
          'the gaining and losing directions of L/n^2 are one factor and its '
          'reciprocal; one double ulp')
    check(1, 'into_water(1) == n^2', R.into_water(np.ones((1, 3)))[0], n ** 2,
          1e-15, 'the factor itself, read out of the shipped function rather '
                 'than out of a comment')

    # ...and then the closed form it has to satisfy on a flat surface. A uniform
    # sky of radiance 1 shines on flat water. Count the transmitted flux TWICE:
    #   AIR SIDE, this file's own quadrature over the whole hemisphere,
    #       E = pi INT 2 mu (1 - R_ext(mu)) dmu
    #   WATER SIDE, through render.py's `uw_interface` and `into_water`, over
    #       the WINDOW only -- everything outside it is mirror --
    #       E = pi INT_{cos tc}^{1} 2 mu_w (1 - R_int) n^2 dmu_w
    # They are equal only for the square. The window's compression of solid
    # angle and the n^2 gain in radiance are the same statement, so this row
    # fails if the exponent is 1 or 3 as loudly as if the factor were absent --
    # and it is the FIRST row in this file that tests the gaining direction.
    NQ = 40000
    mu = (np.arange(NQ) + .5) / NQ
    for c, nm in enumerate('RGB'):
        air = float(np.mean(2. * mu * (1. - fresnel_exact(mu, n[c])[0])))
        muc = np.cos(np.arcsin(1.0 / n[c]))
        mw = muc + (1. - muc) * (np.arange(NQ) + .5) / NQ
        sw = np.sqrt(np.maximum(1. - mw ** 2, 0.))
        dvw = np.stack([sw, np.zeros_like(sw), mw], 1)
        zw = np.zeros(NQ)
        tw = R.uw_interface(dvw, zw, zw, np.ones(NQ), np.full(NQ, n[c]), c)
        gain = R.into_water(np.ones((NQ, 1)) * (1. - tw[4])[:, None],
                            n[c] ** 2)[:, 0]
        # the mean is over (mu_c, 1], so the integral is that mean times the
        # interval, and the interval is 1 - mu_c.
        wat = float(np.mean(2. * mw * gain) * (1. - muc))
        check(1, 'sky flux into the water: n^2 over the window == T over the '
                 'hemisphere  [%s]' % nm, wat, air, 1e-3, rel=True,
              why='the same transmitted irradiance counted on both sides of a '
                  'flat interface -- the water side through the shipped '
                  '`uw_interface` and `into_water` over the window alone, the '
                  'air side through this file\'s `fresnel_exact` over the whole '
                  'hemisphere. At n^1 the water side reads %.3f of the air '
                  'side and at n^3 %.3f, so the exponent is what is under test. '
                  '1e-3 relative is the two 40000-node rules'
                  % (1. / n[c], n[c]))
    info(1, '  ... the gain at the window\'s centre',
         '(1 - F0) n^2 = %s' % np.round((1 - R.F0) * n ** 2, 4),
         'the sky straight overhead is brighter under water than over it, by '
         '0.80 of a stop, and that is not a look: it is the solid angle the '
         'window compresses it into')

    # ---- THE EYE, AND WHAT THE COMPOSITION CLAIMS --------------------------
    dwall = min(R.UW_EYE[0] - R.XW0, R.XW1 - R.UW_EYE[0],
                R.UW_EYE[1] - R.YW0, R.YW1 - R.UW_EYE[1])
    rim_r = -R.UW_EYE[2] * np.tan(np.arcsin(1 / n[1]))
    check(1, 'the underwater eye is inside the water body',
          float((R.UW_EYE[2] < 0) and (R.UW_EYE[2] > R.bed_z(
              np.array([R.UW_EYE[0]]), np.array([R.UW_EYE[1]]))[0]) and
              (R.pool_sdf(np.array([R.UW_EYE[0]]),
                          np.array([R.UW_EYE[1]]))[0] < 0)), 1.0, 0.0,
          'a camera inside the liner renders a frame that reads as a shading '
          'bug; no tolerance')
    between(1, 'the window is unclipped: d tan(tc) / (nearest wall) < 1',
            rim_r / dwall, 0.0, 1.0,
            'the rim lands on the surface at d tan(theta_c) = %.3f m and the '
            'nearest wall is %.3f m away, so the whole rim is on open water. '
            'This is a one-sided condition and it is the only thing the eye\'s '
            'depth is chosen against; the margin it leaves, %.0f%%, is what the '
            'camera comment claims' % (rim_r, dwall, 100 * (1 - rim_r / dwall)))
    info(1, '  ... the sun in the window',
         'refracted to %.2f deg from vertical, %.2f deg inside the green rim'
         % (np.degrees(np.arcsin(np.sqrt(1 - R.SUN_DIR[2] ** 2) / n[1])),
            np.degrees(np.arcsin(1 / n[1])
                       - np.arcsin(np.sqrt(1 - R.SUN_DIR[2] ** 2) / n[1]))),
         'section G predicts 44.4 deg and 4.1 deg from a 21.0 deg sun; both '
         'follow from SUN_DIR and IOR with nothing else in them')


def main():
    t0 = time.time()
    print('validate.py -- external checks on the pool reference implementation')
    print('loading render.py by slicing (see load_render) ...', flush=True)
    R, skipped, errors = load_render()
    # A NameError is the expected cascade: a node whose input was deliberately
    # skipped. Anything else is worth seeing, because it means a node the slice
    # DID try to run is broken.
    odd = [e for e in errors if not e[1].startswith('NameError')]
    print('  %d top-level nodes skipped by rule, %d skipped by cascade '
          '(%d of those not NameError)' % (skipped, len(errors), len(odd)))
    for ln, msg in odd[:5]:
        print('    render.py:%d  %s' % (ln, msg))
    import field as fld
    import wake as wkm
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        fld._norm_jets()          # render.py calls this before anything samples
    print('  field bands normalised (%.1f s so far)' % (time.time() - t0), flush=True)

    for fn, args in ((tier1_fresnel, (R,)), (tier1_snell, (R,)),
                     (tier1_beer, (R,)), (tier1_caustic, (R, fld)),
                     (tier1_flat, (R, fld)), (tier1_energy, (R,)),
                     (tier2_absorption, (R,)), (tier2_coxmunk, (R, fld)),
                     (tier2_jet, (fld, wkm)), (tier2_dispersion, (fld, wkm)),
                     (tier3_refl_ellipse, (R, fld)),
                     (tier_interface, (R,)), (tier_wall_plane, (R,)),
                     (tier_map_extent, (R,)), (tier_fold, (R,)),
                     (tier_stone_sun, (R,)),
                     (tier3_diffuse_fresnel, (R,)), (tier3_cylinder, (R,)),
                     (tier3_gemm, (fld,)), (tier3_geometry, (R,)),
                     (tier_meniscus, (R,)),
                     (tier_underwater, (R,)),
                     (tier3_wake, (fld, wkm))):
        try:
            fn(*args)
        except Exception as exc:                       # noqa: BLE001
            ROWS.append(Row(0, '%s RAISED' % fn.__name__, '-',
                            '%s: %s' % (type(exc).__name__, exc), '-', 'FAIL',
                            'a test that cannot run is a failing test', ''))

    wid = max(len(r.name) for r in ROWS) + 2
    vw = 26
    print()
    for tier in (1, 2, 3, 0):
        rs = [r for r in ROWS if r.tier == tier]
        if not rs:
            continue
        title = {1: 'TIER 1  CLOSED FORM', 2: 'TIER 2  PUBLISHED MEASUREMENT',
                 3: 'TIER 3  INDEPENDENT METHOD', 0: 'HARNESS'}[tier]
        print('=' * (wid + 2 * vw + 22))
        print(title)
        print('=' * (wid + 2 * vw + 22))
        print('%-*s %-*s %-*s %-10s %s'
              % (wid, 'test', vw, 'expected', vw, 'measured', 'tol', 'result'))
        print('-' * (wid + 2 * vw + 22))
        for r in rs:
            if r.status == 'INFO':
                # INFO rows carry prose, so they get the whole line rather than
                # a 26-character column that would cut it off.
                print('%-*s INFO  %s' % (wid, r.name, _fmt(r.got)))
                continue
            print('%-*s %-*s %-*s %-10s %s'
                  % (wid, r.name, vw, _fmt(r.exp)[:vw], vw, _fmt(r.got)[:vw],
                     _fmt(r.tol)[:10], r.status))
            if VERBOSE:
                print('%-*s   why: %s' % (wid, '', r.why))
        print()

    npass = sum(r.status == 'PASS' for r in ROWS)
    nfail = sum(r.status == 'FAIL' for r in ROWS)
    ninfo = sum(r.status == 'INFO' for r in ROWS)
    if nfail:
        print('=' * 78)
        print('FAILURES -- each with the tolerance\'s justification')
        print('=' * 78)
        for r in ROWS:
            if r.status == 'FAIL':
                print('  %s' % r.name)
                print('      expected %s   measured %s   tolerance %s'
                      % (_fmt(r.exp), _fmt(r.got), _fmt(r.tol)))
                print('      tolerance is: %s' % r.why)
        print()
    print(UNVALIDATED)
    print('=' * 78)
    print('%d pass, %d FAIL, %d info -- %.1f s' % (npass, nfail, ninfo,
                                                   time.time() - t0))
    print('=' * 78)
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main())
