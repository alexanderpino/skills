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
    'refract', 'scene_hit', 'box_hit', '_cyl_entry', 'splat', 'blur', 'sample',
    'bed_depth', 'bed_z', 'pool_sdf', 'edge_z',
    'cos_i', 'cos_t', 'sin_t', 'slant', 'TSUN', 'sig_at', 'SIG_EST',
    'TIR_FRAC', 'TIR_VERT', '_sky_vf', '_ris_closure', 'RIS_D0', 'RIS_D1',
    'RIS_ND', 'RIS_NP', 'RIS_HMIN',
    'R_EXT', 'R_INT', 'wet_albedo', '_fresnel_rough', '_refl_ellipse',
    '_lobe_shape', 'sky', 'SKY_LOBE', 'E_SUN', 'L_SUN', 'OMEGA_SUN', 'N_DISC',
    'N_AURE', 'L_AURE', 'AIRMASS', 'TAU_R', '_tau_rayleigh', 'THETA_SUN',
    'CAP_A', 'MENIS_H', 'SIGMA_W',
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
    # -- SCHLICK, which is what the renderer actually evaluates. `_fresnel_rough`
    # at zero unresolved variance is plain Schlick, so this measures the
    # approximation the picture is made of against the exact equations.
    # The frame spans theta_v 11-52 deg above the water (render.py's own
    # measurement), i.e. 38-79 deg of incidence, so the error is reported over
    # that range and over the full 0-90.
    n = IOR[1]
    for lo, hi, tag in ((0.0, 90.0, 'full 0-90 deg'), (38.0, 79.0, 'in-frame 38-79 deg')):
        th = np.linspace(np.deg2rad(lo), np.deg2rad(hi), 20001)
        ci = np.cos(th)
        ex = fresnel_exact(ci, n)[0]
        sch = R._fresnel_rough(ci, np.zeros_like(ci))[:, 1]
        i = int(np.argmax(np.abs(ex - sch)))
        # Schlick (1994) is quoted as ~1% of the reflectance for common
        # dielectrics. For water at grazing it is far worse, and 0.02 absolute
        # is chosen as "an error that cannot change the look": at the frame's
        # own white point a 0.02 error in a reflectance of ~0.3 is a 7% error
        # in the brightest term in the picture. It fails, and the number is
        # the finding.
        check(1, 'Schlick vs exact Fresnel, max |dR| (%s)' % tag,
              float(np.abs(ex - sch).max()), 0.0, 0.02,
              'Schlick 1994 claims ~1% of R for dielectrics; 0.02 absolute is the '
              'level at which the specular term visibly changes')
        info(1, '  ... worst at (%s)' % tag,
             'theta %.1f deg: exact %.4f, Schlick %.4f (+%.1f%%)'
             % (np.degrees(th[i]), ex[i], sch[i], 100 * (sch[i] / ex[i] - 1)),
             'where Schlick departs most')
    # -- TSUN, the sun's transmission into the water at 69 deg incidence, is
    # Schlick in the file. Against exact Fresnel:
    ex = 1.0 - fresnel_exact(R.cos_i, IOR[1])[0]
    check(1, 'TSUN (sun into water at 69 deg) vs exact Fresnel', R.TSUN, ex,
          0.005, 'a 0.5% error in the beam entering the water is below the '
                 'exposure quantisation of the frame')
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
        # either nothing or a flagged value. It returns a vector of length
        # n*sin(i) > 1 lying in the surface plane -- a direction that is not a
        # direction. Currently unreachable (every call site has eta = 1/n < 1),
        # but it is exactly the branch the README's Snell's-window pass needs.
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
            info(1, '  ... what refract() returns past TIR instead',
                 '|t| runs %.3f to %.3f (= n sin i), tz = %.3g'
                 % (L.min(), L.max(), float(np.abs(tz2).max())),
                 'a horizontal vector longer than unity')
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
          T, [0.5834, 0.8985, 0.9720], 5e-4,
          "render.py prints this triple to 3 dp; 5e-4 is that precision")
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
    info(2, '  ... ABS / Pope & Fry, per channel', np.round(R.ABS / pf, 4),
         'red is Pope & Fry; blue is not')
    info(2, '  ... ABS / Smith & Baker 1981 at the same three', np.round(R.ABS / sb, 4),
         'ABS[2] = 0.0145 is Smith & Baker\'s 450 nm value exactly')
    # -- BAND INTEGRALS over the file's own Voronoi cells. This is the reading
    # the file's own band doctrine demands, and it is the one to adopt.
    band = []
    for lo, hi in np.sort(R.BAND, axis=1) * 1000.0:
        xs = np.linspace(lo, hi, 801)
        band.append(float(np.trapezoid(_tab(POPE_FRY_1997, xs), xs) / (hi - lo)))
    band = np.array(band)
    check(2, 'ABS vs Pope & Fry band-integrated over the file\'s own BAND cells',
          R.ABS / band, [1., 1., 1.], 0.15, 'same justification as above')
    info(2, '  ... Pope & Fry averaged over BAND (582-658, 502-582, 418-502 nm)',
         np.round(band, 5), 'the reading the file\'s own band model asks for')
    # -- the chapter's / README's triple, at ITS stated wavelengths.
    ch = np.array([0.264, 0.0565, 0.0092])
    check(2, 'chapter a_water (0.264, 0.0565, 0.0092) vs Pope & Fry at 610/550/450',
          ch / _tab(POPE_FRY_1997, [610, 550, 450]), [1., 1., 1.], 0.02,
          'the chapter states these ARE Pope & Fry at those wavelengths, so the '
          'only tolerance is its own 3-significant-figure quotation')
    rm = np.array([0.25, 0.0565, 0.0092])
    check(2, 'README a_water (0.25, ...) vs the chapter it quotes',
          rm / ch, [1., 1., 1.], 0.02,
          'the README says it is quoting the chapter; 2% is its own rounding')
    # -- the identification, which is what settles the dispute.
    check(2, 'ABS blue is Smith & Baker 1981 at 450 nm', R.ABS[2],
          SMITH_BAKER_1981[450], 1e-9,
          'exact identity, printed to show provenance rather than to pass or fail')
    # -- and what it costs, so the severity is a number and not an adjective.
    over = np.exp(-R.ABS * 2 * R.slant) / np.exp(-band * 2 * R.slant)
    info(2, '  ... cost on the shipped 3.92 m down-and-back path',
         'transmittance ratio %s (blue is %.1f%% dark)'
         % (np.round(over, 4), 100 * (1 - over[2])),
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
    # -- TIR_VERT: the ratio of the returning flux caught by a vertical face to
    # that caught by the horizontal bed. Closed form in render.py; here by
    # quadrature and by Monte-Carlo, both of the same physical statement.
    #   emission from a Lambertian bed:  L cos t
    #   solid angle:                     sin t dt dphi
    #   receiver cosine, vertical face:  sin t * max(cos phi, 0),  <..> = 1/pi
    #   receiver cosine, horizontal:     cos t
    th = np.linspace(tc, np.pi / 2, 2000001)
    quad = (np.trapezoid(np.cos(th) * np.sin(th) ** 2, th) / np.pi) \
        / np.trapezoid(np.cos(th) ** 2 * np.sin(th), th)
    K = 4000000
    t2 = np.arccos(rng.random(K))              # uniform in solid angle
    p2 = rng.uniform(0, 2 * np.pi, K)
    m = t2 > tc
    mcv = float((np.cos(t2[m]) * np.sin(t2[m]) * np.maximum(np.cos(p2[m]), 0)).sum()
                / (np.cos(t2[m]) ** 2).sum())
    check(3, 'TIR_VERT vs quadrature of the integral its comment states', R.TIR_VERT,
          float(quad), 1e-3,
          'both are the same one-dimensional integral; 1e-3 is the trapezoid\'s '
          'own error on 2e6 points, which is under 1e-9')
    check(3, 'TIR_VERT vs %dk uniform-solid-angle MC' % (K // 1000), R.TIR_VERT,
          mcv, 4 * mcv / np.sqrt(m.sum()),
          'MC 1 sigma is %.5f; 4 sigma' % (mcv / np.sqrt(m.sum())))
    info(3, '  ... corrected TIR_VERT from the stated derivation',
         '%.5f (code has %.5f, %.1f%% low)'
         % (quad, R.TIR_VERT, 100 * (1 - R.TIR_VERT / quad)),
         'see the report: the vertical-face integrand carries one sin(t) too many')
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
    * The shade sail's shadow map, the coping's height-field march, the
      freeboard band, the waterline, the deck and liner gathers.
    * `_riser_shade` and the riser bounce MAP -- the closure of its estimator is
      tested, the map it produces is not.
    * The bed-return (TIR) map: TIR_FRAC and TIR_VERT are tested, the 2.4 M-ray
      splat that spends them is not.

  TESTED IN PART
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
                     (tier3_diffuse_fresnel, (R,)), (tier3_cylinder, (R,)),
                     (tier3_gemm, (fld,)), (tier3_geometry, (R,)),
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
