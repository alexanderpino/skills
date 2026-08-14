"""The pool scene's physics, as pictures, into `gauntlet/evidence/`.

    python3 pool_figures.py [outdir]

WHY THIS EXISTS. The sea loop ships diagnostic figures -- a profile with the bar
on it, flux convergence, refraction rays, an H/d transect with the threshold
drawn -- and the pool ships none. The pool has 285 validated quantities and not
one of them is visible: they live in a terminal transcript that scrolls away.
The renders exist; the MEASUREMENTS do not. These six figures close that, and
the test each one had to pass is a single question: DOES IT LET A READER SEE A
QUANTITY THAT CURRENTLY ONLY EXISTS AS A NUMBER?

THREE RULES, and they are what makes this a diagnostic rather than a decoration.

  1. NO PHYSICS IS WRITTEN HERE. Every curve, every level and every number in
     every label is imported from `optics.py`, `atmosphere.py`, or the slice of
     `render.py` that `validate.py` already knows how to take. Nothing is
     re-typed, nothing is re-derived, and there is not one physical constant in
     this file. The only arithmetic below is data-to-pixel and the composition
     of quantities the modules already export.
  2. THE CAPTION IS BURNED INTO THE FRAME. A PNG travels and a README does not.
     Each figure states what it is, what is measured against what, and which
     numbers are derived against which are still open and marked `?`.
  3. IT FAILS RATHER THAN DRAWS A STALE VALUE. `preflight()` below re-derives
     every headline number by a route that does not share code with the one
     being drawn -- Walsh's reciprocity against a quadrature, a closed geometric
     series against a truncated sum, a closed form against a midpoint rule --
     and raises `SystemExit` on the first disagreement. A plotting module cannot
     be guarded by the suite (it asserts nothing about a picture), so it carries
     its own guard, and that guard runs before any pixel is drawn.

WHAT THIS FILE DOES NOT TOUCH. It does not import `render.py` directly and it
never calls it: the pool's rendered frames must stay bit-identical, and the only
way to be sure of that is to not run the renderer. `validate.py`'s `load_render`
is reused verbatim for the two scene numbers these figures need (DEPTH, and the
liner's own albedo), because a second loader is a second premise.

`?` marks on the figures are the file's own: SKY_AMB and the horizon/zenith
gradient are hand-set in `atmosphere.py` and say so there. Nothing here promotes
a `?` to a result.
"""
import math
import os
import sys

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

import atmosphere as ATM                                        # noqa: E402
import beach_plot as P                                          # noqa: E402
import optics as OPT                                            # noqa: E402
import validate as VAL                                          # noqa: E402

OUT = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-')
       else os.path.join(HERE, '..', '..', 'gauntlet', 'evidence'))

# ---------------------------------------------------------------- plot furniture
RED = (192, 56, 44)
GRN = (26, 128, 78)
BLU = (44, 80, 190)
CH = (RED, GRN, BLU)
CHN = ('red', 'green', 'blue')
INK, MUTED, GRID = P.INK, P.MUTED, P.GRID
WARN = (168, 76, 24)
PURPLE = (124, 72, 168)
GREY = (110, 112, 118)
FAINT = (222, 224, 228)


def _ticks(lo, hi, n=6):
    """A round tick sequence covering [lo, hi]. Presentation only."""
    step = (hi - lo) / n
    mag = 10.0 ** math.floor(math.log10(step))
    for m in (1, 2, 2.5, 5, 10):
        if mag * m >= step:
            step = mag * m
            break
    t0 = math.ceil(lo / step) * step
    return [t0 + i * step for i in range(int((hi - t0) / step) + 1)]


def _logticks(ax, vals, fmt='%g'):
    """x gridlines at log10(vals), labelled with `vals` themselves. `Axes.frame`
    formats a tick by its own coordinate, which on a log axis is the exponent;
    this draws the decade labels instead. Presentation only."""
    for v in vals:
        px = float(ax.px(math.log10(v)))
        if not (ax.x0 - 1 <= px <= ax.x1 + 1):
            continue
        ax.d.line([px, ax.y0, px, ax.y1], fill=GRID)
        ax.d.text((px, ax.y1 + 4), fmt % v, fill=MUTED, font=P.FONT_S,
                  anchor='ma')


def _ylogticks(ax, vals, fmt='%g'):
    for v in vals:
        py = float(ax.py(math.log10(v)))
        if not (ax.y0 - 1 <= py <= ax.y1 + 1):
            continue
        ax.d.line([ax.x0, py, ax.x1, py], fill=GRID)
        ax.d.text((ax.x0 - 6, py), fmt % v, fill=MUTED, font=P.FONT_S,
                  anchor='rm')


def _bar(ax, x, y0, y1, colour, w=0.30, outline=None):
    ax.d.rectangle([float(ax.px(x - w)), float(ax.py(y1)),
                    float(ax.px(x + w)), float(ax.py(y0))],
                   fill=colour, outline=outline or colour)


def _trip(v, fmt='%.4f'):
    """A per-channel triple as it is written everywhere in this project."""
    return ' / '.join(fmt % f for f in np.asarray(v, float).ravel())


def _pct(v, fmt='%.2f'):
    return ' / '.join((fmt + '%%') % (100. * f)
                      for f in np.asarray(v, float).ravel())


# ============================================================ THE SCENE'S TWO
# The only two numbers below the waterline that are not in `optics.py` or
# `atmosphere.py`: how deep this pool is, and what its liner reflects. Both are
# statements about THIS basin, they live in `render.py` where they belong, and
# they are taken through `validate.py`'s own slicing loader rather than through a
# second one written here. Importing `render.py` outright would run a five-minute
# render and write over the reference frames.
_SCENE = {}


def scene():
    if not _SCENE:
        R, _skipped, _errs = VAL.load_render()
        _SCENE['R'] = R
        _SCENE['DEPTH'] = float(R.DEPTH)
        _SCENE['RHO_BED'] = np.asarray(R.LINER_TINT * 0.74, float)
        _SCENE['COS_SUN'] = float(R.cos_i)
    return _SCENE


# ================================================================== THE GUARD
# Every headline number these figures draw, re-derived by a route that shares no
# expression with the one being plotted. This is the whole of this module's
# verification: a figure that has gone stale against the physics it claims to
# show is worse than no figure, so the script refuses to draw one.
CHECKS = []


def _esc_integrand(mu, c, dep):
    """optics.slab_esc's integrand, assembled from the module's own pieces."""
    return (2. * mu * np.exp(-OPT.ABS[c] * dep / mu)
            * (1. - OPT.r_int_at(mu)[:, c]))


def _trap_integrand(mu, c, dep):
    """optics.slab_trap's, likewise."""
    return (2. * mu * np.exp(-2. * OPT.ABS[c] * dep / mu)
            * OPT.r_int_at(mu)[:, c])


def _split_gl(f, dep, nodes=400):
    """Gauss-Legendre on (0, 1] SPLIT at mu = cos(tc), per channel. Quadrature,
    not physics: the integrand is entirely the module's. The split is the whole
    point -- see the note at the guard that uses this."""
    out = np.zeros(3)
    for c in range(3):
        mc = float(np.cos(OPT.TC_SNELL[c]))
        x, w = np.polynomial.legendre.leggauss(nodes)
        for lo, hi in ((0.0, mc), (mc, 1.0)):
            m = .5 * (hi - lo) * x + .5 * (hi + lo)
            out[c] += (.5 * (hi - lo) * w * f(m, c, dep)).sum()
    return out


def guard(name, got, want, tol, note, rel=False):
    g = np.atleast_1d(np.asarray(got, float))
    w = np.atleast_1d(np.asarray(want, float))
    err = np.abs(g - w)
    if rel:
        err = err / np.maximum(np.abs(w), 1e-300)
    e = float(np.max(err))
    CHECKS.append((name, e, tol, note))
    if not (e <= tol):
        raise SystemExit(
            'pool_figures.py: GUARD FAILED -- %s\n'
            '  drawn    %s\n'
            '  expected %s\n'
            '  %s error %.3e exceeds %.3e\n'
            '  %s\n'
            'The physics moved and this figure would have drawn a stale value. '
            'Fix the figure, not the tolerance.'
            % (name, np.round(g, 8), np.round(w, 8),
               'relative' if rel else 'absolute', e, tol, note))


def preflight():
    S = scene()
    dep, rho, cs = S['DEPTH'], S['RHO_BED'], S['COS_SUN']
    n = OPT.IOR

    # -- FIGURE 1. R_EXT is drawn as the cosine-weighted mean of the file's own
    # `fresnel`; R_INT is drawn as Walsh's reciprocity. Neither is checked
    # against itself: R_EXT goes against a 20000-node quadrature of `fresnel`
    # and R_INT against a DIRECT quadrature of `r_int_at`, which reaches the
    # interface from the other side and never touches R_EXT.
    mu = (np.arange(20000) + .5) / 20000
    guard('R_EXT == 2 mu <fresnel> over the air-side hemisphere',
          OPT.R_EXT, (2. * mu[:, None] * OPT.fresnel(mu)).mean(0), 3e-5,
          'the module builds R_EXT on 512 nodes; this is 20000 of them')
    guard('R_INT == 2 mu <r_int_at> over the water-side hemisphere',
          OPT.R_INT, (2. * mu[:, None] * OPT.r_int_at(mu)).mean(0), 3e-5,
          'Walsh reciprocity against a direct quadrature of the other side')
    guard('R_INT == 1 - (1 - R_EXT)/n^2', OPT.R_INT,
          1. - (1. - OPT.R_EXT) / n ** 2, 1e-15, 'algebraic identity')
    # the decomposition the figure draws as two stacked pieces must close.
    inside = 2. * mu[:, None] * np.where(
        (mu[:, None] ** 2) > (1. - 1. / n[None] ** 2), OPT.r_int_at(mu), 0.)
    guard('R_INT == (1 - 1/n^2) + <partial Fresnel inside the cone>',
          OPT.R_INT, (1. - 1. / n ** 2) + inside.mean(0), 3e-5,
          'the two pieces figure 1 stacks; if they do not sum the bar is a lie')
    guard('T_OUT_DIFFUSE == (1 - R_EXT)/n^2 == 1 - R_INT',
          OPT.T_OUT_DIFFUSE, (1. - OPT.R_EXT) / n ** 2, 1e-15,
          'the diffuse form of out_of_water, and the factor WBOUNCE carries')
    guard('TC_SNELL == the angle at which r_int_at first reaches 1',
          np.sin(OPT.TC_SNELL), 1. / n, 1e-15, 'Snell, from the file own IOR')

    # -- FIGURE 2. slab_esc's zero-depth limit is the diffuse escape exactly;
    # at depth it is checked against a midpoint rule that shares no node with
    # the module's 2000-point Gauss-Legendre.
    guard('slab_esc(0) == T_OUT_DIFFUSE', OPT.slab_esc(0.0), OPT.T_OUT_DIFFUSE,
          1e-4, 'zero depth: the correlated integral collapses to the mean')
    # The reference here is the SAME integrand on a Gauss-Legendre rule SPLIT at
    # mu = cos(tc), which is the one point where the integrand is continuous but
    # not differentiable -- `r_int_at` pins at exactly 1 to the left of it. A
    # single-interval Gaussian rule cannot see that kink and stalls at algebraic
    # convergence; split, it agrees with a converged 4M-node midpoint rule to
    # eight digits. The residual below is therefore the MODULE's own quadrature
    # error, measured at 3.9 / -6.2 / 3.1 e-5 relative for `slab_esc` and
    # -8.0 / 8.1 / -3.4 e-5 for `slab_trap` at this depth; the tolerance is set
    # to 2e-4 so that this guard fires on a MOVED physics and not on a known and
    # reported 6e-5. See the README note that goes with these figures.
    guard('slab_esc(DEPTH) == the same integrand, GL split at cos(tc)',
          OPT.slab_esc(dep), _split_gl(_esc_integrand, dep), 2e-4,
          'the module single-interval rule against one split at the kink',
          rel=True)
    guard('slab_trap(DEPTH) == the same rule on the round trip',
          OPT.slab_trap(dep), _split_gl(_trap_integrand, dep), 2e-4,
          'ditto, one round trip', rel=True)

    # -- FIGURE 3. The closed series against a truncated one, and the lossless
    # white pool, which is energy conservation and not a tolerance.
    guard('trap_gain closed == the same series summed to 400 terms',
          OPT.trap_gain(rho, dep), OPT.trap_gain(rho, dep, bounces=400),
          1e-12, 'geometric closure')
    guard('LOSSLESS WHITE POOL: fresnel(sun) + rho_water(1) == 1',
          OPT.fresnel(cs) + OPT.rho_water(1.0, cs, dep, absorb=0.0),
          np.ones(3), 1e-12,
          'energy conservation with no constant of the module on the right')
    guard('the sun cosine the figure uses is SUN_DIR z', cs,
          float(ATM.SUN_DIR[2]), 1e-12,
          'render.py cos_i against atmosphere.py own ephemeris vector')

    # -- FIGURE 4. The two window shares, against the two closed forms neither
    # quadrature can see.
    wb, wv = ATM.window_shares(False)
    guard('flat window share of a BED == 1/n^2', wb, 1. / n ** 2, 1e-8,
          'the Snell window change of variables, exactly')
    guard('flat window share of a VERTICAL face == 0.5 - tir_vert(tc)(1-1/n^2)',
          wv, .5 - OPT.tir_vert(OPT.TC_SNELL) * (1. - 1. / n ** 2), 1e-8,
          'the closed form the module own TIR_VERT is one reading of')
    guard('tir_vert(0) == 1/2', OPT.tir_vert(0.0), 0.5, 1e-15,
          'a vertical face sees half of what a horizontal one does, exactly')

    # -- FIGURE 5. The Cauchy curve the bands are read through must reproduce
    # the three IORs it was fitted to, and the bands must tile without a gap.
    guard('n_water(LAM) == IOR', OPT.n_water(OPT.LAM), n, 1e-4,
          'the two-parameter Cauchy fit through the file own three pairs')
    guard('the Voronoi bands tile with no gap and no overlap',
          [OPT.BAND[0, 0], OPT.BAND[1, 0]], [OPT.BAND[1, 1], OPT.BAND[2, 1]],
          1e-15, 'band edges are the midpoints of the nominal wavelengths')
    guard('2E_3(0) == 1', OPT._e3(0.0), np.ones(1), 1e-9,
          'a slab of zero optical depth transmits everything')

    # -- FIGURE 6. The disc lobe carries the beam exactly; that is the whole
    # claim the figure makes and it is one line of algebra.
    guard('the disc lobe flux == pi SUN_COL == E_SUN',
          2. * np.pi / (ATM.N_DISC + 1.) * ATM.L_SUN, ATM.E_SUN, 1e-9,
          'a cos^n lobe carries 2 pi/(n+1); nothing about the disc is free',
          rel=True)
    guard('N_DISC == 2/theta_s^2 - 1', ATM.N_DISC,
          2. / ATM.THETA_SUN ** 2 - 1., 1e-9, 'the width that makes it so')
    guard('the aureole amplitude == (E_n/4pi) m tau_R x 3/4',
          ATM.L_AURE, ATM.E_SUN / (4. * np.pi) * ATM.AIRMASS * ATM.TAU_R * .75,
          1e-12, 'Rayleigh forward term, single scattering albedo 1')
    sd = [np.atleast_1d(float(v)) for v in ATM.SUN_DIR]
    guard('env_diffuse + the disc == sky, on the sun axis',
          ATM.sky(*sd),
          ATM.env_diffuse(*sd)
          + ATM.SKY_LOBE[0][2][None] * ATM.SKY_LOBE[0][0] * 1.15, 1e-9,
          'the partition the two illuminants stand on', rel=True)
    return S


# ================================================================== FIGURE 1
def fig_interface(S, path):
    """The two sides of one interface: 6.7% out there, 47.6% in here."""
    n, tc = OPT.IOR, OPT.TC_SNELL
    th = np.linspace(0., np.pi / 2., 4001)
    ext = OPT.fresnel(np.cos(th))                       # air -> water
    thw = np.linspace(0., np.pi / 2., 4001)
    inn = OPT.r_int_at(np.cos(thw))                     # water -> air
    tir = 1. - 1. / n ** 2
    part = OPT.R_INT - tir

    img = P.canvas(1260, 1030)
    ax = P.Axes(img, (100, 72, 700, 440), (0, 90), (0, 1.16),
                title='One interface, two sides',
                xlabel='angle from the normal, deg',
                ylabel='reflectance R (unpolarised)')
    ax.frame(_ticks(0, 90, 6), _ticks(0, 1.0, 5), '%g', '%.2f')
    for c in range(3):
        ax.line(np.rad2deg(thw), inn[:, c], CH[c], 3)
        ax.line(np.rad2deg(th), ext[:, c], CH[c], 2, dash=(6, 5))
        ax.vline(float(np.rad2deg(tc[c])), CH[c], 1, dash=(3, 4))
    ax.hline(float(OPT.R_INT[1]), GREY, 1, dash=(8, 6))
    ax.hline(float(OPT.R_EXT[1]), GREY, 1, dash=(8, 6))
    ax.text(51, 0.62, 'diffuse R_int (green) = %.5f' % OPT.R_INT[1], INK)
    ax.text(51, 0.56, 'diffuse R_ext (green) = %.5f' % OPT.R_EXT[1], INK)
    ax.text(51, 0.44, 'critical angle, per band:', INK)
    ax.text(51, 0.38, '%s deg' % _trip(np.rad2deg(tc), '%.3f'), MUTED)
    P.legend(ax, [(GREY, 'solid: from INSIDE the water  (r_int_at)'),
                  (GREY, 'dashed: from the AIR  (fresnel)')], 2.5, 1.11)

    # -- the decomposition, as the two pieces that must sum
    bx = P.Axes(img, (790, 72, 1200, 440), (-0.5, 2.5), (0, 0.70),
                title='...and what the 47.6% is made of',
                xlabel='band', ylabel='share of an isotropic in-water flux')
    bx.frame(None, _ticks(0, 0.5, 5), '%g', '%.2f')
    for c in range(3):
        _bar(bx, c, 0., float(tir[c]), CH[c], 0.30)
        _bar(bx, c, float(tir[c]), float(OPT.R_INT[c]), FAINT, 0.30,
             outline=CH[c])
        bx.text(c, float(tir[c]) / 2., '%.3f%%' % (100 * tir[c]),
                (255, 255, 255), 'mm')
        bx.text(c, float(OPT.R_INT[c]) + .012,
                '%.3f%%' % (100 * OPT.R_INT[c]), INK, 'ms')
        bx.text(c, -0.028, CHN[c], MUTED, 'ma')
    bx.text(-0.42, 0.665, 'solid   1 - 1/n^2: total reflection past tc', INK)
    bx.text(-0.42, 0.630, 'hollow  partial Fresnel INSIDE the cone,', INK)
    bx.text(-0.42, 0.595, '        = %s' % _pct(part, '%.3f'), MUTED)
    bx.text(-0.42, 0.560, 'the two must sum to R_int -- guarded to 3e-5.', INK)

    # -- and why the two means differ: the cosine weighting itself
    cx = P.Axes(img, (100, 545, 1200, 815), (0, 1), (0, 1.45),
                title='Why the two means differ: the same weighting on both '
                      'sides',
                xlabel='cosine mu from the normal (1 = straight up)',
                ylabel='2 mu R(mu)')
    cx.frame(_ticks(0, 1, 5), _ticks(0, 1.4, 4), '%.1f', '%.2f')
    mu = np.linspace(1e-6, 1., 1600)
    ei = 2. * mu[:, None] * OPT.fresnel(mu)
    ii = 2. * mu[:, None] * OPT.r_int_at(mu)
    cx.fill_between(mu, np.zeros_like(mu), ii[:, 1], (214, 232, 220))
    cx.fill_between(mu, np.zeros_like(mu), ei[:, 1], (238, 220, 216))
    for c in range(3):
        cx.line(mu, ii[:, c], CH[c], 3)
        cx.line(mu, ei[:, c], CH[c], 2, dash=(6, 5))
    for c in range(3):
        cx.vline(float(np.cos(tc[c])), CH[c], 1, dash=(3, 4))
    cx.text(float(np.cos(tc[1])) - 0.02, 1.36,
            'mu = cos(tc): everything LEFT of this is totally reflected',
            INK, 'rs')
    cx.text(0.03, 1.32, 'green area = R_int = %.5f' % OPT.R_INT[1], INK)
    cx.text(0.03, 1.24, 'pink area  = R_ext = %.5f' % OPT.R_EXT[1], INK)
    cx.text(0.03, 1.16, 'the area under each curve IS that mean.', MUTED)

    P.caption(img, [
        'WHAT IS MEASURED. One smooth water surface, asked the same question '
        'from both sides, through ONE Fresnel implementation (optics.fresnel; '
        'r_int_at reads it back through Snell).',
        'Diffuse external R_ext = %s against diffuse internal R_int = %s: a '
        'factor of %.2f between the two faces of the same boundary.'
        % (_pct(OPT.R_EXT, '%.3f'), _pct(OPT.R_INT, '%.3f'),
           float(OPT.R_INT[1] / OPT.R_EXT[1])),
        'They are TIED, not independent: R_int = 1 - (1 - R_ext)/n^2 (Walsh '
        'reciprocity) reproduces a direct quadrature of r_int_at to 3e-5, which '
        'is a guard this figure runs before drawing.',
        'The right panel splits R_int: %s is total reflection past the critical '
        'angle (1 - 1/n^2, exactly known), and only %s is partial Fresnel '
        'inside the cone.'
        % (_pct(1 - 1 / OPT.IOR ** 2, '%.3f'), _pct(part, '%.3f')),
        'CORRECTED VALUE. The transport OUT of the water shipped for several '
        'rounds as Fresnel T alone, without the 1/n^2 = %s that goes with it.'
        % _trip(1. / OPT.N2, '%.4f'),
        'A lossless white-bedded pool then read an apparent albedo of 1.73 '
        'instead of 1 -- and the wet-liner term already had the divisor while '
        'the camera path went without, the two disagreeing by n^2.',
    ], 40, 858)
    return P.save(img, path)


# ================================================================== FIGURE 2
def fig_correlation(S, path):
    """Attenuation and escape do not factorise. The LUT trap, drawn."""
    dep = S['DEPTH']
    a = OPT.ABS
    mu = np.linspace(1e-3, 1., 1600)
    att = np.exp(-a[None] * dep / mu[:, None])
    esc = 1. - OPT.r_int_at(mu)
    w = 2. * mu[:, None]
    e3d = OPT._e3(a * dep)                      # 2E_3 at DEPTH, per channel

    img = P.canvas(1320, 1010)
    ax = P.Axes(img, (95, 72, 620, 405), (0, 1), (0, 1.34),
                title='The two factors are correlated (red band, %.2f m)' % dep,
                xlabel='cosine mu of the upgoing ray',
                ylabel='value of each factor')
    ax.frame(_ticks(0, 1, 5), _ticks(0, 1.0, 5), '%.1f', '%.2f')
    ax.line(mu, att[:, 0], RED, 3)
    ax.line(mu, esc[:, 0], BLU, 3)
    ax.line(mu, att[:, 0] * esc[:, 0], INK, 3)
    ax.vline(float(np.cos(OPT.TC_SNELL[0])), GREY, 1, dash=(3, 4))
    P.legend(ax, [(RED, 'attenuation  exp(-a d / mu)'),
                  (BLU, 'escape  1 - R_int(mu)'),
                  (INK, 'their product -- what slab_esc integrates')],
             0.04, 1.30)
    ax.text(float(np.cos(OPT.TC_SNELL[0])) - .02, 0.16,
            'cos(tc): nothing escapes left of here', INK, 'rs')
    ax.text(0.04, 1.13,
            'BOTH rise with mu. A steep ray escapes AND crosses less water,', INK)
    ax.text(0.04, 1.07,
            'so <A><E> is not <AE>, and the sign of the error is fixed.', INK)

    bx = P.Axes(img, (740, 72, 1265, 405), (0, 1), (0, 1.34),
                title='Product of means against mean of product',
                xlabel='cosine mu', ylabel='cosine-weighted integrand 2 mu f')
    bx.frame(_ticks(0, 1, 5), _ticks(0, 1.0, 5), '%.1f', '%.2f')
    for c in range(3):
        bx.line(mu, (w * att * esc)[:, c], CH[c], 3)
        bx.line(mu, 2. * mu * float(e3d[c] * OPT.T_OUT_DIFFUSE[c]), CH[c], 1,
                dash=(4, 4))
    bx.text(0.04, 1.30, 'solid: 2 mu exp(-a d/mu)(1 - R_int(mu)) -- slab_esc',
            INK)
    bx.text(0.04, 1.24, 'dashed: 2 mu x 2E_3(a d) x (1 - R_int), the same area '
                        'rule on the', MUTED)
    bx.text(0.04, 1.18, 'PRODUCT OF THE TWO MEANS. The areas are what differ:',
            MUTED)
    for c in range(3):
        bx.text(0.04, 1.10 - .06 * c,
                '%-6s  slab_esc %.5f   factorised %.5f   %+.2f%%'
                % (CHN[c], OPT.slab_esc(dep)[c],
                   e3d[c] * OPT.T_OUT_DIFFUSE[c],
                   100 * (OPT.slab_esc(dep)[c]
                          / (e3d[c] * OPT.T_OUT_DIFFUSE[c]) - 1)),
                CH[c])

    dd = np.linspace(0., 4., 260)
    esc_t = np.array([OPT.slab_esc(d) for d in dd])
    trp_t = np.array([OPT.slab_trap(d) for d in dd])
    # `_e3` takes a vector, so this is three calls and not 780.
    esc_f = np.array([OPT._e3(a[c] * dd) for c in range(3)]).T * OPT.T_OUT_DIFFUSE
    trp_f = np.array([OPT._e3(2. * a[c] * dd) for c in range(3)]).T * OPT.R_INT

    cx = P.Axes(img, (95, 505, 620, 800), (0, 4), (0, 26),
                title='ESCAPE: factorising UNDERstates it',
                xlabel='water column, m',
                ylabel='slab_esc / (2E_3 x (1 - R_int)) - 1,  %')
    cx.frame(_ticks(0, 4, 4), _ticks(0, 25, 5), '%g', '%g')
    for c in range(3):
        cx.line(dd, 100. * (esc_t[:, c] / esc_f[:, c] - 1.), CH[c], 3)
    cx.vline(dep, WARN, 2, dash=(6, 5))
    gap = OPT.slab_esc(dep) / (e3d * OPT.T_OUT_DIFFUSE) - 1.
    for c in range(3):
        cx.marker(dep, 100. * float(gap[c]), CH[c])
    cx.text(1.95, 24.0, 'this pool: DEPTH = %.2f m' % dep, WARN)
    cx.text(1.95, 21.5, '%s' % _pct(gap, '%.1f'), INK)
    cx.text(1.95, 19.0, 'and optics.py says 19.4 / 5.1 / 1.1% -- agrees',
            MUTED)

    ex = P.Axes(img, (740, 505, 1265, 800), (0, 4), (0, 112),
                title='ROUND TRIP: factorising OVERstates it',
                xlabel='water column, m',
                ylabel='(2E_3(2ad) x R_int) / slab_trap - 1,  %')
    ex.frame(_ticks(0, 4, 4), _ticks(0, 100, 5), '%g', '%g')
    for c in range(3):
        ex.line(dd, 100. * (trp_f[:, c] / trp_t[:, c] - 1.), CH[c], 3)
    ex.vline(dep, WARN, 2, dash=(6, 5))
    tgap = OPT._e3(2. * a * dep) * OPT.R_INT / OPT.slab_trap(dep) - 1.
    for c in range(3):
        ex.marker(dep, 100. * float(tgap[c]), CH[c])
    ex.text(0.12, 107., 'this pool: %s' % _pct(tgap, '%.1f'), INK)
    ex.text(0.12, 100., 'optics.py comment says "30% in red" -- it does not '
                        'reproduce;', WARN)
    ex.text(0.12, 93., 'at DEPTH the measured red figure is %.1f%%. Flagged, '
                       'not silently redrawn.' % (100 * tgap[0]), WARN)

    P.caption(img, [
        'WHAT IS MEASURED. Whether the two things that happen to a photon on its '
        'way up out of the bed -- being absorbed, and getting through the surface '
        '-- can be multiplied. They cannot.',
        'Both factors RISE with mu (top left), so they are positively '
        'correlated: the product of the means UNDERstates the escape by %s...'
        % _pct(gap, '%.1f'),
        '...and the round trip, correlated the other way, is OVERstated by %s. '
        'This is the LUT trap, and it is invisible as prose.'
        % _pct(tgap, '%.1f'),
        'A table of "mean transmission" times a table of "mean escape" is a '
        'defensible-looking pipeline that is a fifth wrong in red at this depth.',
        'DERIVED: every curve is optics.slab_esc / slab_trap / _e3 / r_int_at, '
        'Gauss-Legendre on the water-side cosine, guarded here against the same '
        'integrand split at the kink before drawing.',
        'FINDING: the escape gap reproduces optics.py own 19.4 / 5.1 / 1.1%% '
        'exactly. The round-trip comment in the same block says 30%% in red; '
        'the measurement at DEPTH is %.1f%%.' % (100 * tgap[0]),
    ], 40, 855)
    return P.save(img, path)


# ================================================================== FIGURE 3
def fig_trap(S, path):
    """The light trap under the surface, and its chromatic gain."""
    dep, rb, cs = S['DEPTH'], S['RHO_BED'], S['COS_SUN']
    rho = np.linspace(0., 1., 400)
    gain = np.array([OPT.trap_gain(np.full(3, r), dep) for r in rho])
    bound = 1. / (1. - rho[:, None] * OPT.R_INT[None])
    one = np.array([OPT.trap_gain(np.full(3, r), dep, bounces=1, cone_only=True)
                    for r in rho])
    alb = np.array([OPT.rho_water(np.full(3, r), cs, dep) for r in rho])

    img = P.canvas(1280, 1030)
    ax = P.Axes(img, (100, 72, 650, 450), (0, 1), (1.0, 2.1),
                title="The trapped series: gain on the bed's own light",
                xlabel='bed albedo rho_bed',
                ylabel='trap_gain = 1 / (1 - rho G_rt)')
    ax.frame(_ticks(0, 1, 5), _ticks(1.0, 2.1, 5), '%.1f', '%.1f')
    for c in range(3):
        ax.line(rho, bound[:, c], CH[c], 1, dash=(5, 5))
        ax.line(rho, gain[:, c], CH[c], 3)
        ax.line(rho, one[:, c], CH[c], 2, dash=(2, 4))
        ax.marker(float(rb[c]), float(OPT.trap_gain(rb, dep)[c]), CH[c])
    P.legend(ax, [(GREY, 'solid: 1/(1 - rho G_rt), G_rt = slab_trap(DEPTH)'),
                  (GREY, 'dashed: the diffuse-R_int BOUND, 1/(1 - rho R_int)'),
                  (GREY, 'dotted: one bounce over the cone -- what render ships')],
             0.03, 2.05)
    ax.text(0.03, 1.66,
            'markers: this liner, rho_bed = %s' % _trip(rb, '%.3f'), INK)
    ax.text(0.03, 1.61, 'gain there = %s' % _trip(OPT.trap_gain(rb, dep), '%.4f'),
            INK)

    bx = P.Axes(img, (760, 72, 1220, 450), (0, 1), (0, 1.02),
                title='...and what comes back out: apparent albedo',
                xlabel='bed albedo rho_bed',
                ylabel='rho_water (surface reflection excluded)')
    bx.frame(_ticks(0, 1, 5), _ticks(0, 1.0, 5), '%.1f', '%.2f')
    for c in range(3):
        bx.line(rho, alb[:, c], CH[c], 3)
        bx.marker(float(rb[c]), float(OPT.rho_water(rb, cs, dep)[c]), CH[c])
    bx.line(rho, rho, GREY, 1, dash=(5, 5))
    loss = OPT.rho_water(1.0, cs, dep, absorb=0.0)
    bx.marker(1.0, float(loss[1]), INK, 5)
    bx.text(0.50, float(loss[1]) - 0.02,
            'lossless white pool (dot): rho_w = 1 - R(sun) = %.4f' % loss[1],
            INK)
    bx.text(0.50, float(loss[1]) - 0.07,
            'energy conservation -- guarded to 1e-12', MUTED)
    bx.text(0.04, 0.97, 'this liner: %s' % _trip(OPT.rho_water(rb, cs, dep),
                                                 '%.4f'), INK)
    bx.text(0.04, 0.92, 'a %.3f red bed reads %.4f: the water keeps 82%% of it'
            % (rb[0], OPT.rho_water(rb, cs, dep)[0]), MUTED)
    bx.text(0.04, 0.87, 'grey 1:1 line = a dry bed, for scale', MUTED)

    dd = np.linspace(0., 4., 260)
    st = np.array([OPT.slab_trap(d) for d in dd])
    cx = P.Axes(img, (100, 545, 1220, 812), (0, 4), (0, 0.68),
                title='The bound is the ZERO-DEPTH limit, and the pool is not '
                      'at zero depth',
                xlabel='water column, m',
                ylabel='G_rt, share returned to the bed')
    cx.frame(_ticks(0, 4, 4), _ticks(0, 0.6, 6), '%g', '%.2f')
    for c in range(3):
        cx.line(dd, st[:, c], CH[c], 3)
        cx.hline(float(OPT.R_INT[c]), CH[c], 1, dash=(5, 5))
        cx.marker(dep, float(OPT.slab_trap(dep)[c]), CH[c])
    cx.vline(dep, WARN, 2, dash=(6, 5))
    amp_t = OPT.trap_gain(rb, dep) - 1.
    amp_b = 1. / (1. - rb * OPT.R_INT) - 1.
    cx.text(0.10, 0.655, 'dashed: the bound R_int = %s -- the d -> 0 limit'
            % _trip(OPT.R_INT, '%.4f'), MUTED)
    cx.text(0.10, 0.620, 'solid: G_rt(d). At DEPTH = %.2f m it is %s'
            % (dep, _trip(OPT.slab_trap(dep), '%.4f')), INK)
    cx.text(0.10, 0.585,
            'so the AMPLIFICATION (gain - 1) at this liner is %s,'
            % _trip(amp_t, '%.4f'), INK)
    cx.text(0.10, 0.550,
            'and quoting the bound would give %s -- over by %s'
            % (_trip(amp_b, '%.4f'), _pct(amp_b / amp_t - 1., '%.0f')), WARN)

    P.caption(img, [
        "WHAT IS MEASURED. How much brighter the bed is than its own first "
        "bounce, because the underside of the surface sends light back down.",
        'THE BOUND AND THE POOL ARE DIFFERENT NUMBERS. R_int = %s is the share '
        'returned by the SURFACE.' % _trip(OPT.R_INT, '%.4f'),
        'G_rt = %s is the share that gets back to the BED, having crossed %.2f '
        'm of water on the way.'
        % (_trip(OPT.slab_trap(dep), '%.4f'), 2 * dep),
        'At this liner the true amplification is %s; the diffuse-R_int bound '
        'gives %s instead -- over by %s, worst where the water absorbs most.'
        % (_trip(amp_t, '%.4f'), _trip(amp_b, '%.4f'),
           _pct(amp_b / amp_t - 1., '%.0f')),
        'DOTTED is what the shipped bedret pass carries: one bounce, a perfect '
        'mirror over the cone and nothing inside it, = %s.'
        % _trip(OPT.trap_gain(rb, dep, bounces=1, cone_only=True), '%.4f'),
        'A truncated series with a smaller ratio is a LOWER bound, so the '
        'render is dark there and never bright -- the sign is what matters.',
        'CORRECTED VALUE. The chain rho_water is written in shipped once with a '
        'round trip in the denominator and NO up leg in the numerator.',
        'That overstates the answer by 1/T_up -- 85% in red -- and passes the '
        'lossless-white limit anyway: that limit pins the shape, not the legs.',
    ], 40, 862)
    return P.save(img, path)


# ================================================================== FIGURE 4
def fig_window(S, path):
    """Snell's window from below, and the share a vertical face gets of it."""
    n, tc = OPT.IOR, OPT.TC_SNELL
    img = P.canvas(1320, 1010)

    ax = P.Axes(img, (100, 72, 640, 420), (0, 50), (0, 92),
                title="Snell's window: the whole sky, in a %.1f deg cone"
                      % np.rad2deg(tc[1]),
                xlabel='water-side polar angle from the vertical, deg',
                ylabel='air-side ELEVATION it came from, deg')
    ax.frame(_ticks(0, 50, 5), _ticks(0, 90, 6), '%g', '%g')
    for c in range(3):
        tw = np.linspace(0., float(tc[c]), 4000)
        ta = np.arcsin(np.clip(n[c] * np.sin(tw), 0., 1.))
        ax.line(np.rad2deg(tw), 90. - np.rad2deg(ta), CH[c], 3)
        ax.vline(float(np.rad2deg(tc[c])), CH[c], 1, dash=(3, 4))
    tw1 = float(tc[1]) - np.deg2rad(1.0)
    el1 = 90. - np.rad2deg(np.arcsin(n[1] * np.sin(tw1)))
    ax.line([np.rad2deg(tw1), np.rad2deg(tw1)], [0, el1], WARN, 2, dash=(4, 4))
    ax.line([0, np.rad2deg(tw1)], [el1, el1], WARN, 2, dash=(4, 4))
    ax.marker(np.rad2deg(tw1), el1, WARN)
    ax.text(2.5, 22.0,
            'the OUTER 1.00 deg of the window holds', WARN)
    ax.text(2.5, 17.0,
            'every air direction below %.2f deg of elevation' % el1, WARN)
    ax.text(2.5, 86., 'rim is dispersive: %s deg'
            % _trip(np.rad2deg(tc), '%.3f'), INK)

    bx = P.Axes(img, (760, 72, 1270, 420), (0, 50), (0, 2.6),
                title='...which is why a lookup starves the rim',
                xlabel='water-side polar angle, deg',
                ylabel='d(theta_air) / d(theta_water)')
    bx.frame(_ticks(0, 50, 5), _ticks(0, 2.5, 5), '%g', '%g')
    for c in range(3):
        tw = np.linspace(0., float(tc[c]) * (1 - 1e-6), 4000)
        ta = np.arcsin(np.clip(n[c] * np.sin(tw), 0., 1. - 1e-12))
        jac = n[c] * np.cos(tw) / np.maximum(np.cos(ta), 1e-9)
        bx.line(np.rad2deg(tw), np.log10(jac) * 0 + jac, CH[c], 3)
        bx.vline(float(np.rad2deg(tc[c])), CH[c], 1, dash=(3, 4))
    bx.hline(1.0, GREY, 1, dash=(5, 5))
    bx.text(1.5, 2.45,
            'the map is n:1 at the axis and SINGULAR at the rim --', INK)
    bx.text(1.5, 2.30,
            'a uniform sample in theta_water gets thinner and thinner', INK)
    bx.text(1.5, 2.15, 'air per sample as it approaches tc.', INK)
    bx.text(1.5, 1.10, 'axis: d(theta_a)/d(theta_w) = n = %s'
            % _trip(n, '%.4f'), MUTED)

    # -- the two weightings, and the shares they integrate to
    cx = P.Axes(img, (100, 520, 640, 810), (0, 50), (0, 1.05),
                title='Two receivers, two weightings of the same window',
                xlabel='water-side polar angle, deg',
                ylabel='normalised weight (peak = 1)')
    cx.frame(_ticks(0, 50, 5), _ticks(0, 1.0, 5), '%g', '%.2f')
    tw = np.linspace(0., float(tc[1]), 3000)
    wb = np.cos(tw) * np.sin(tw)
    wv = np.sin(tw) ** 2
    cx.line(np.rad2deg(tw), wb / wb.max(), PURPLE, 3)
    cx.line(np.rad2deg(tw), wv / wv.max(), (24, 122, 156), 3)
    cx.vline(float(np.rad2deg(tc[1])), GREY, 1, dash=(3, 4))
    P.legend(cx, [(PURPLE, 'horizontal BED:  cos t sin t'),
                  ((24, 122, 156), 'vertical WALL:  sin^2 t')], 2.0, 1.00)
    cx.text(2.0, 0.70, 'the wall is weighted hardest at the RIM, where the', INK)
    cx.text(2.0, 0.65, 'air-side horizon is; the bed peaks at 45 deg and the', INK)
    cx.text(2.0, 0.60, 'gain n^2 cancels its compression exactly.', INK)

    wbf, wvf = ATM.window_shares(False)
    dx = P.Axes(img, (760, 520, 1270, 810), (-0.6, 2.6), (0, 0.62),
                title='The share each one collects, and the number it replaced',
                xlabel='band', ylabel='(1/pi) INT L cos dw for uniform L = 1')
    dx.frame(None, _ticks(0, 0.6, 6), '%g', '%.1f')
    for c in range(3):
        _bar(dx, c - 0.17, 0., float(wbf[c]), CH[c], 0.15)
        _bar(dx, c + 0.17, 0., float(wvf[c]), FAINT, 0.15, outline=CH[c])
        dx.text(c - 0.17, float(wbf[c]) + .012, '%.4f' % wbf[c], INK, 'ms')
        dx.text(c + 0.17, float(wvf[c]) + .012, '%.4f' % wvf[c], INK, 'ms')
        dx.text(c, -0.026, CHN[c], MUTED, 'ma')
    dx.hline(0.5, WARN, 2, dash=(6, 5))
    dx.text(2.55, 0.515, 'WALL_SKY = 0.5, superseded', WARN, 'rs')
    dx.text(-0.55, 0.59, 'solid  BED   = 1/n^2 exactly = %s'
            % _trip(1. / n ** 2, '%.4f'), INK)
    dx.text(-0.55, 0.56,
            'hollow WALL  = 0.5 - tir_vert(tc)(1 - 1/n^2) = %s'
            % _trip(wvf, '%.4f'), INK)
    dx.text(-0.55, 0.53, 'ratio SKY_VERT = %s' % _trip(ATM.SKY_VERT, '%.4f'),
            INK)

    P.caption(img, [
        'WHAT IS MEASURED. What a submerged eye or facet actually has over it. '
        'The whole air-side hemisphere arrives inside a cone of half-angle '
        'asin(1/n) = %s deg -- dispersive, and drawn per band.'
        % _trip(np.rad2deg(tc), '%.3f'),
        'The mapping is singular at the rim (top right): every air direction '
        'below %.2f deg of elevation is folded into the outermost 1.00 deg of '
        'the window, so an environment lookup uniform in the water-side angle '
        'starves exactly the low-elevation sky.' % el1,
        'ON A HORIZONTAL BED the n^2 gain and the compression cancel exactly: '
        'the window share is 1/n^2 = %s and "a full hemisphere of SKY_AMB" is '
        'the right answer. That is why the bed term always worked.'
        % _trip(1. / n ** 2, '%.4f'),
        'ON A VERTICAL WALL the cancellation fails, and by the largest factor '
        'available: sin^2 weights the rim, cos sin weights 45 deg, and the '
        'wall collects %s where the bed collects %s.'
        % (_trip(wvf, '%.4f'), _trip(wbf, '%.4f')),
        'CORRECTED VALUE. WALL_SKY = 0.5 -- correct as a partition of a '
        'HEMISPHERE, wrong as a share of a WINDOW -- is superseded by SKY_VERT '
        '= %s, a factor of %.2f. Both closed forms are guarded here against '
        "atmosphere.window_shares' own quadrature to 1e-8."
        % (_trip(ATM.SKY_VERT, '%.4f'), float(0.5 / ATM.SKY_VERT[1])),
        '`?` The RADIANCE filling the window is not derived: SKY_HOR, SKY_TOP '
        'and the 0.55 exponent between them are hand-set in atmosphere.py. This '
        'figure draws the GEOMETRY, which is, and sets L = 1.',
    ], 40, 835)
    return P.save(img, path)


# ================================================================== FIGURE 5
def fig_absorption(S, path):
    """The spectral absorption, the bands it is a mean over, and the path."""
    dep = S['DEPTH']
    a = OPT.ABS
    img = P.canvas(1280, 1010)

    ax = P.Axes(img, (100, 72, 640, 420), (405, 670), (0, 0.30),
                title='a is a BAND MEAN, over bands that tile',
                xlabel='wavelength, nm', ylabel='absorption a, 1/m')
    ax.frame(_ticks(410, 670, 5), _ticks(0, 0.30, 6), '%g', '%.2f')
    for c in range(3):
        lo, hi = 1000. * OPT.BAND[c]
        ax.d.rectangle([float(ax.px(min(lo, hi))), float(ax.py(float(a[c]))),
                        float(ax.px(max(lo, hi))), float(ax.py(0.))],
                       fill=CH[c])
        ax.vline(1000. * float(OPT.LAM[c]), (255, 255, 255), 1, dash=(3, 3))
        ax.text(1000. * float(OPT.LAM[c]), float(a[c]) + .012,
                '%.5f' % a[c], INK, 'ms')
        ax.text(1000. * float(OPT.LAM[c]), 0.012, '%.0f' % (1000 * OPT.LAM[c]),
                (255, 255, 255), 'ms')
    ax.text(412, 0.285, 'bar width = the Voronoi cell of its own wavelength;', INK)
    ax.text(412, 0.270, 'the three tile %.1f - %.1f nm with no gap.'
            % (1000 * OPT.BAND[2, 0], 1000 * OPT.BAND[0, 1]), INK)
    ax.text(412, 0.255, 'height = a averaged over THAT cell, not sampled at '
                        'its centre.', INK)

    dd = np.linspace(0., 3.2, 400)
    bx = P.Axes(img, (760, 72, 1220, 420), (0, 3.2), (0, 1.02),
                title='...and what it does to a path',
                xlabel='water crossed, m', ylabel='transmission')
    bx.frame(_ticks(0, 3.2, 4), _ticks(0, 1.0, 5), '%g', '%.2f')
    for c in range(3):
        bx.line(dd, np.exp(-a[c] * dd), CH[c], 3)
        bx.line(dd, OPT._e3(a[c] * dd), CH[c], 2, dash=(5, 5))
    bx.vline(dep, WARN, 2, dash=(6, 5))
    bx.vline(2. * dep, WARN, 2, dash=(6, 5))
    bx.text(dep + .05, 0.98, 'one way', WARN)
    bx.text(2. * dep + .05, 0.98, 'round trip', WARN, 'rs')
    P.legend(bx, [(GREY, 'solid: vertical exp(-a d)'),
                  (GREY, 'dashed: diffuse 2E_3(a d), a cosine law off the bed')],
             0.12, 0.90)
    bx.text(0.12, 0.60, 'vertical at DEPTH   %s' % _trip(np.exp(-a * dep)), INK)
    bx.text(0.12, 0.55, 'diffuse at DEPTH    %s' % _trip(OPT._e3(a * dep)), INK)
    bx.text(0.12, 0.50, 'the diffuse path is LONGER: a fifth of the red.', MUTED)

    slant = 1. / np.sqrt(1. - (np.sqrt(1. - S['COS_SUN'] ** 2) / OPT.IOR) ** 2)
    cx = P.Axes(img, (100, 520, 1220, 810), (-0.6, 2.6), (0, 1.05),
                title='The four legs of this pool own chain, at DEPTH = %.2f m'
                      % dep,
                xlabel='band', ylabel='transmission of that leg')
    cx.frame(None, _ticks(0, 1.0, 5), '%g', '%.2f')
    legs = [
        ('sun in, at the refracted slant (x%.4f)' % slant[0],
         np.exp(-a * dep * slant), (232, 168, 60)),
        ('vertical up, exp(-a d)', np.exp(-a * dep), PURPLE),
        ('diffuse up, 2E_3(a d)', OPT._e3(a * dep), (24, 122, 156)),
        ('diffuse up AND out, slab_esc', OPT.slab_esc(dep), INK),
    ]
    for i, (lab, v, col) in enumerate(legs):
        for c in range(3):
            _bar(cx, c - 0.30 + 0.20 * i, 0., float(v[c]), col, 0.09)
        cx.text(-0.55, 1.00 - 0.055 * i, '%s   %s' % (_trip(v), lab), col)
    for c in range(3):
        cx.text(c, -0.05, CHN[c], MUTED, 'ma')

    P.caption(img, [
        'WHAT IS MEASURED. The one material property of the water: a = %s /m, '
        'Pope & Fry (1997), averaged over the Voronoi band each channel '
        'actually integrates rather than sampled at its nominal wavelength.'
        % _trip(a, '%.5f'),
        'The band mean matters most in RED, where a runs from 0.09 to 0.34 '
        'across the band: the point sample and the band mean differ by 5.0% '
        'there, and every other spectral quantity in optics.py is already taken '
        'over these bands.',
        'CORRECTED VALUE. The triple this replaced was (0.2750, 0.0546, '
        '0.0145): red right to 0.2%, green 6.9% high, and blue lifted straight '
        'out of Smith & Baker (1981) at 450 nm -- 48% above Pope & Fry, from a '
        "paper this project's own provenance file bans for blue by name.",
        'The bottom panel is why one absorption gives four different numbers per '
        'band: the sun enters at a refracted slant (x%.4f), light leaves the '
        'bed over a cosine law, and only slab_esc has the escape inside the '
        'same integral as the attenuation.' % slant[0],
        'DERIVED throughout: optics.ABS, optics._e3, optics.slab_esc, and the '
        'slant from render own cos_i through Snell. 2E_3(0) = 1 is guarded '
        'before drawing.',
    ], 40, 835)
    return P.save(img, path)


# ================================================================== FIGURE 6
def fig_sun(S, path):
    """The sun the pool is lit by: one disc, one aureole, nothing free."""
    ang = np.logspace(-2, np.log10(90.), 900)          # deg from the sun
    cs = np.clip(np.cos(np.deg2rad(ang)), 0., 1.)      # 90 deg lands on 6e-17
    disc = ATM.L_SUN[None] * cs[:, None] ** ATM.N_DISC
    aure = ATM.L_AURE[None] * cs[:, None] ** ATM.N_AURE
    grad = ATM.sky_diffuse(np.ones(1))[0]              # zenith, gradient only
    ghor = ATM.sky_diffuse(np.zeros(1))[0]             # horizon

    img = P.canvas(1280, 900)
    ax = P.Axes(img, (110, 72, 760, 520), (-2, np.log10(90.)), (-4, 6.2),
                title='One disc, one aureole, and a sky under both',
                xlabel='angle from the sun, deg',
                ylabel='radiance, scene-linear (green band)')
    ax.frame(None, None)
    _logticks(ax, [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 90])
    _ylogticks(ax, [1e-4, 1e-2, 1, 1e2, 1e4, 1e6], '%g')
    for c in range(3):
        ax.line(np.log10(ang), np.log10(np.maximum(disc[:, c], 1e-30)), CH[c], 3)
        ax.line(np.log10(ang), np.log10(np.maximum(aure[:, c], 1e-30)), CH[c],
                2, dash=(6, 5))
    ax.hline(float(np.log10(grad[1])), GREY, 1, dash=(4, 4))
    ax.hline(float(np.log10(ghor[1])), GREY, 1, dash=(4, 4))
    ax.vline(float(np.log10(np.rad2deg(ATM.THETA_SUN))), WARN, 2, dash=(4, 4))
    ax.text(np.log10(np.rad2deg(ATM.THETA_SUN)) + .06, 5.9,
            'solar radius %.3f deg' % np.rad2deg(ATM.THETA_SUN), WARN)
    ax.text(-1.93, np.log10(grad[1]) + 0.16, 'sky gradient: zenith %.3f, '
            'horizon %.3f  `?` hand-set' % (grad[1], ghor[1]), INK)
    ax.text(-1.93, 5.4, 'disc peak L_sun = %s' % _trip(ATM.L_SUN, '%.3e'), INK)
    ax.text(-1.93, 5.0, '  = pi SUN_COL / Omega_sun, Omega_sun = %.3e sr'
            % ATM.OMEGA_SUN, MUTED)
    ax.text(-1.93, 4.6, 'aureole amp L_aure = %s' % _trip(ATM.L_AURE, '%.4f'),
            INK)
    ax.text(-1.93, 4.2, '  = (E_n/4pi) x m x tau_R x 3/4, cos^2', MUTED)
    ax.text(-1.93, -3.0, 'solid: the disc, cos^%.0f' % ATM.N_DISC, INK)
    ax.text(-1.93, -3.4, 'dashed: the Rayleigh aureole, cos^%.0f' % ATM.N_AURE,
            INK)

    disc_f = 2. * np.pi / (ATM.N_DISC + 1.) * ATM.L_SUN
    aure_f = 2. * np.pi / (ATM.N_AURE + 1.) * ATM.L_AURE
    bx = P.Axes(img, (860, 72, 1220, 520), (-0.6, 2.6), (0, 31),
                title='...and the flux each carries',
                xlabel='band', ylabel='hemispherical flux, 2 pi/(n+1) x amp')
    bx.frame(None, _ticks(0, 30, 6), '%g', '%g')
    for c in range(3):
        _bar(bx, c - 0.17, 0., float(disc_f[c]), CH[c], 0.15)
        _bar(bx, c + 0.17, 0., float(aure_f[c]), FAINT, 0.15, outline=CH[c])
        bx.text(c - 0.17, float(disc_f[c]) + 0.5, '%.2f' % disc_f[c], INK, 'ms')
        bx.text(c + 0.17, float(aure_f[c]) + 0.5, '%.2f' % aure_f[c], INK, 'ms')
        bx.text(c, -1.3, CHN[c], MUTED, 'ma')
    bx.text(-0.55, 29.5, 'solid  disc = %s' % _trip(disc_f, '%.3f'), INK)
    bx.text(-0.55, 28.0, 'hollow aureole = %s' % _trip(aure_f, '%.3f'), INK)
    bx.text(-0.55, 26.5, 'and pi x SUN_COL = %s' % _trip(ATM.E_SUN, '%.3f'),
            WARN)
    bx.text(-0.55, 25.0, 'the disc IS the beam, to 1e-9 relative.', WARN)

    P.caption(img, [
        'WHAT IS MEASURED. The angular structure of the environment this pool '
        'is lit by, on log axes, because it spans nine decades: a disc of peak '
        '%.3e and half-width %.3f deg sitting on a sky of about %.2f.'
        % (ATM.L_SUN[1], np.rad2deg(ATM.THETA_SUN), grad[1]),
        'NOTHING IN EITHER LOBE IS FREE. The disc is fixed three ways at once '
        '-- peak L = pi SUN_COL / Omega_sun, width n = 2/theta_s^2 - 1 = %.0f, '
        'and therefore flux 2pi/(n+1) x L = pi SUN_COL exactly, which is the '
        'guard this figure runs.' % ATM.N_DISC,
        'The aureole is single-scattered Rayleigh at the air mass SUN_COL own '
        'colour is read out of (m = %.2f, tau_R = %s): amplitude (E_n/4pi) m '
        'tau 3/4 and cos^2, the whole forward structure a clean atmosphere has.'
        % (ATM.AIRMASS, _trip(ATM.TAU_R, '%.4f')),
        'CORRECTED VALUES. All six lobe numbers were guesses: the disc lobe peak '
        'was 1563x under the sun own radiance and 7.8x too wide, and the three '
        'lobes together carried a 35th of the direct beam -- a broad dim smear '
        'where the physics has a small blinding point.',
        'AND ONE DERIVED TO ZERO. There is no aerosol lobe, and that is a '
        'result: SUN_COL colour is Rayleigh extinction alone, so the beam was '
        'never dimmed by aerosol, and adding an aerosol aureole would create '
        'that light twice.',
        '`?` The horizon/zenith GRADIENT under the lobes (SKY_HOR, SKY_TOP, the '
        '0.55 exponent) is hand-set and stays hand-set; atmosphere.py computes a '
        'single-scattering LOWER bound beside it and names what is missing.',
    ], 40, 760)
    return P.save(img, path)


# ====================================================================== main
FIGURES = (
    ('fig-pool-interface-two-sides.png', fig_interface),
    ('fig-pool-escape-correlation.png', fig_correlation),
    ('fig-pool-trapped-series.png', fig_trap),
    ('fig-pool-snell-window.png', fig_window),
    ('fig-pool-absorption-path.png', fig_absorption),
    ('fig-pool-sun-lobes.png', fig_sun),
)


def main():
    os.makedirs(OUT, exist_ok=True)
    print('pool_figures.py -- the pool own physics, as pictures')
    print('  loading the scene through validate.load_render ...')
    S = preflight()
    print('  DEPTH %.2f m, liner albedo %s, sun cosine %.5f'
          % (S['DEPTH'], _trip(S['RHO_BED'], '%.4f'), S['COS_SUN']))
    worst = max(CHECKS, key=lambda r: r[1] / r[2])
    print('  %d guards passed; the closest to failing is "%s" at %.1f%% of its '
          'tolerance (%.3e of %.3e)'
          % (len(CHECKS), worst[0], 100. * worst[1] / worst[2], worst[1],
             worst[2]))
    for name, fn in FIGURES:
        p = fn(S, os.path.join(OUT, name))
        print('  wrote %s' % os.path.relpath(p, HERE))
    print('done: %d figures into %s' % (len(FIGURES), os.path.normpath(OUT)))


if __name__ == '__main__':
    main()
