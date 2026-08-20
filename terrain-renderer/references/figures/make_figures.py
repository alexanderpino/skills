"""The chapters' figures, regenerated from the code that ships.

    python3 terrain-renderer/references/figures/make_figures.py [outdir]

WHY THIS FILE IS HERE AND NOT IN AN IMPLEMENTATION DIRECTORY. It is the
chapters' tooling, not the implementation's. It lives beside the PNGs it writes
and beside the chapters that embed them, so a chapter, its figure and the code
that drew the figure move as one unit and a reviewer reading `12` can reach the
generator in one hop from the caption. The two implementation directories
(`reference-impl/`, `raster-impl/`) are the SUBJECT of these figures; putting
the chapter's plotting in there would make the thing being measured and the
instrument the same directory, and it would tie the skill's own assets to a
scene's build. Nothing here writes into either of them.

WHAT IT MAY AND MAY NOT DO.

  1. NO PHYSICS IS WRITTEN HERE. Every curve, level and number comes from
     `reference-impl/optics.py`, `beach.py`, `beach_optics.py` or
     `beach_diffract.py`, imported READ-ONLY. There is not one physical
     constant in this file. The only arithmetic below is data-to-pixel plus
     compositions of quantities those modules already export. A figure drawn
     from the code that ships cannot drift from it.
  2. NO BURNED-IN COMMENTARY. Axis labels, tick labels and legend entries only
     -- those are the data's coordinate system. The caption, the provenance
     mark and every sentence of interpretation live in the markdown beside the
     image, where they can be read, diffed and corrected. Wave 11's three
     critics each reported that text inside the pixels defeated the blind.
  3. SCENE-LINEAR throughout, and NOTHING here is display-referred. The two
     panels that are images rather than plots (`fig_runup`) map grey level
     LINEARLY to scene-linear albedo: no exposure, no tone curve, no gamma.
     They are maps of a field, not renders of it, and the chapter caption says
     so. If a future figure ever needs a display transform, take it from
     `render.encode` rather than writing a private gamma, and say so in the
     caption.
  4. IT FAILS RATHER THAN DRAWS A STALE VALUE. `preflight()` re-derives each
     figure's headline number by a route that does not share code with the one
     being drawn, and raises SystemExit on the first disagreement. A plotting
     module cannot be guarded by `validate.py` -- it asserts nothing about a
     picture -- so it carries its own guard and that guard runs before any
     pixel.
  5. DETERMINISTIC. No unseeded randomness anywhere. The one stochastic figure
     draws from `beach.damp_limit`, whose sampler is a counter hash of an
     explicit seed and has no RNG state at all.

THE FIGURE LIST IS DERIVED FROM THE CHAPTERS' CLAIMS, not from the evidence
set. Each figure below answers "what does this claim look like" for a claim
whose equation is not already its own clearest statement -- typically a claim
about a SHAPE (a discontinuity, a correlation, an edge, a width that is a
function) where the chapter currently carries only a level or a table.

THE SECOND PROVENANCE CATEGORY, and why chapter `09` is allowed a figure at all.

Rule 1 above says a figure's numbers come from the implementation, and that a
claim with no implementation behind it does not get drawn. That rule zeroes out
most of the real-time half of this skill, correctly: `06`'s residency budget,
`07`'s mip halo, `08`'s kill rates and `01`'s crack contract all have shapes,
and every number in a figure of them would be one this file invented. They are
not drawn, and `00-index.md` says which and why.

`09`'s three figures are a different case and the distinction is worth stating
precisely, because it is the only thing separating them from decoration. They
import no implementation module because they need none: their subject IS the
arithmetic. `fig_float_binades` and `fig_depth_precision` ask numpy's own
`float32` where the representable values are -- that is IEEE-754 answering, not
a constant retyped, and there is nothing for it to drift from because the
machine is the authority. `fig_cube_sphere` is a closed-form property of a
stated map; the chapter carries its number at tier **F** with the instruction
"re-derive before quoting in print", and the figure is that re-derivation, with
the answer computed rather than quoted. In all three the guard is the same as
everywhere else: `preflight` re-derives the headline by a second route (a
closed form against a quadrature, an analytic spacing against the machine's)
and refuses to draw on disagreement.

What this file still may NOT do, and did not: pick a near plane, a tile size, a
cascade count or a texture resolution and draw a curve through it. Those are
choices, not measurements, and a figure of them is a picture of this file's own
test case. `fig_depth_precision` is dimensionless in `w/near` for exactly that
reason -- the parameter cancels, so there is no parameter to invent.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_IMPL = os.path.abspath(os.path.join(_HERE, '..', '..', 'reference-impl'))
if _IMPL not in sys.path:
    sys.path.insert(0, _IMPL)

import atmosphere as A                 # noqa: E402  read-only
import beach as B                      # noqa: E402  read-only
import beach_diffract as BD            # noqa: E402  read-only
import beach_optics as BO              # noqa: E402  read-only
import beach_plot as P                 # noqa: E402  read-only (the toolkit)
import optics as O                     # noqa: E402  read-only
import wake as W                       # noqa: E402  read-only

# --- palette -----------------------------------------------------------------
# A light page, and no distinction is carried by colour alone: every pair that
# has to be told apart differs in DASH as well as in hue. The three band
# colours are ordered by luminance too, so the set survives a greyscale print.
RED = (176, 60, 36)
GRN = (26, 106, 68)
BLU = (38, 76, 158)
BAND = (RED, GRN, BLU)
BAND_DASH = (None, (9, 5), (3, 4))
BAND_NAME = ('620 nm', '545 nm', '460 nm')
INK = P.INK
MUTED = P.MUTED
ACCENT = (150, 60, 130)
FILL_A = (214, 226, 214)          # the geometric block
FILL_B = (168, 190, 210)          # the Fresnel remnant
FILL_C = (232, 224, 208)

DEG = '°'


def _lin(a, b, n=601):
    return np.linspace(a, b, n)


def _legend(ax, entries, x, y, dy=18, w=30):
    """`beach_plot.legend`, but the sample line carries the curve's DASH.

    The toolkit's own legend draws every sample solid, which silently defeats
    the rule that no distinction may rest on colour alone: two curves told
    apart by dash then have identical legend keys. Entries are
    (colour, dash, label); `dash=None` is solid."""
    for i, (col, dash, lab) in enumerate(entries):
        px, py = float(ax.px(x)), float(ax.py(y)) + i * dy
        if dash is None:
            ax.d.line([px, py, px + w, py], fill=col, width=3)
        else:
            on, off, t = dash[0], dash[1], 0.0
            while t < w:
                ax.d.line([px + t, py, px + min(t + on, w), py], fill=col,
                          width=3)
                t += on + off
        ax.d.text((px + w + 7, py), lab, fill=INK, font=P.FONT_S, anchor='lm')


def _fill_signed(ax, x, lo, hi, col_hi, col_lo):
    """Fill between two curves, using a different tone on each side of every
    crossing. Two curves whose AREAS are the quantity being compared cross
    where the weight moves; a single-tone fill draws a bowtie over that and
    reads as one region when it is two."""
    d = np.sign(np.asarray(hi) - np.asarray(lo))
    edges = np.flatnonzero(d[1:] != d[:-1]) + 1
    for i0, i1 in zip(np.r_[0, edges], np.r_[edges, len(x)]):
        sl = slice(max(i0 - 1, 0), min(i1 + 1, len(x)))
        if sl.stop - sl.start < 2:
            continue
        ax.fill_between(x[sl], lo[sl], hi[sl],
                        col_hi if d[i0] >= 0 else col_lo)


# --- guards ------------------------------------------------------------------
def preflight():
    """Re-derive every headline number by a second route. SystemExit on the
    first disagreement, before any pixel is drawn."""
    fails = []

    def chk(name, got, want, tol):
        got = np.atleast_1d(np.asarray(got, float))
        want = np.atleast_1d(np.asarray(want, float))
        if not np.all(np.abs(got - want) <= tol):
            fails.append('%-34s got %s want %s' % (name, got, want))

    # 1. Walsh's relation ties the two diffuse constants. The two integrals are
    #    quadratured from different index pairs, so this pins the EXPONENT.
    chk('walsh n^2(1-R_int)=1-R_ext',
        O.IOR ** 2 * (1.0 - O.R_INT), 1.0 - O.R_EXT, 1e-12)
    # 2. R_int decomposes into cos^2(theta_c) plus the partial Fresnel inside
    #    the cone. Quadratured HERE with the chapter's own prescription -- the
    #    interval split at mu_c, 400 nodes a side, because R_int(mu) has a kink
    #    there -- and compared against `optics.R_INT`, which is reached by a
    #    different route entirely (a 512-node midpoint rule on R_ext, taken
    #    across by Walsh). Two routes, no shared line.
    n2 = O.IOR ** 2
    mu_c = np.sqrt(1.0 - 1.0 / n2)
    gx, gw = np.polynomial.legendre.leggauss(400)
    part = np.empty(3)
    for c in range(3):
        m = 0.5 * (gx + 1.0) * (1.0 - mu_c[c]) + mu_c[c]
        w = 0.5 * gw * (1.0 - mu_c[c])
        part[c] = float((w * 2.0 * m * O.r_int_at(m)[:, c]).sum())
    chk('1 - 1/n^2 == mu_c^2', mu_c ** 2, 1.0 - 1.0 / n2, 1e-15)
    chk('R_int = (1-1/n^2) + partial', mu_c ** 2 + part, O.R_INT, 3e-6)
    chk('partial Fresnel remnant', part[1], 0.037431, 5e-6)
    # 3. The factorisation error the chapter prints for this pool's own depth.
    tau = O.ABS * B_DEPTH
    joint = O.slab_esc(B_DEPTH)
    sep = O._e3(tau) * (1.0 - O.R_INT)
    chk('escape leg joint/sep - 1 (%)',
        100.0 * (joint / sep - 1.0), [19.400, 5.072, 1.101], 0.02)
    # 4. Sommerfeld's exact half on the shadow boundary, and the Cornu limits.
    chk('K_d(0)', BD.knife_edge_kd(0.0), 0.5, 1e-12)
    chk("Cornu C(inf), S(inf)", BD.cornu_limit(), [0.5, 0.5], 1e-8)
    # 5. The run-up reading that decides where the wet band ends.
    chk('sigma = R_2% / sqrt(ln 50)',
        B.swash_scale(), B.BERM_Z / np.sqrt(np.log(50.0)), 1e-12)
    # 6. Cox & Munk's two components against the separately fitted total.
    chk('mss components at 6 m/s', sum(BO.cox_munk_mss(6.0)), 0.03348, 1e-9)

    # ---- `09`, `10` and `19`. Same rule: a second route, no shared line. ----
    # 7. The spacing staircase. IEEE-754's own answer against the closed form
    #    2^(floor(log2 x) - 23), which numpy's `spacing` does not compute this
    #    way, and the bound's overstatement pinned to its exact interval.
    xs = 10.0 ** np.linspace(0.0, 12.0, 997)
    closed = 2.0 ** (np.floor(np.log2(xs)) - 23.0)
    chk('spacing == 2^(floor(log2 x)-23)', _f32_spacing(xs) / closed,
        np.ones_like(xs), 0.0)
    ratio = xs * 2.0 ** -23 / _f32_spacing(xs)
    if not (ratio.min() >= 1.0 and ratio.max() < 2.0):
        fails.append('%-34s ratio out of [1, 2): %s'
                     % ('x*2^-23 / spacing', (ratio.min(), ratio.max())))
    #    10^6 sits just above 2^19, near the FLOOR of its binade, so the
    #    chapter's rule overstates that row by 10^6/2^19 -- the worst case in
    #    the whole table and very nearly the worst case possible.
    chk('the 1000 km row is 1.907x pessimistic',
        1e6 * 2.0 ** -23 / _f32_spacing(1e6), 1e6 / 2.0 ** 19, 1e-12)

    # 8. Reversed-Z float32 flat to exactly one binade over seven decades, and
    #    the two fixed-point curves identical -- the chapter says "almost
    #    nothing"; they agree to the last bit, which is a stronger statement.
    wn = 10.0 ** np.linspace(1e-4, 7.0, 4801)
    rev = _depth_rel_err(wn, True, True)
    if not (rev.min() >= 2.0 ** -24 and rev.max() <= 2.0 ** -23):
        fails.append('%-34s left [2^-24, 2^-23]: %s'
                     % ('rev+f32 relative error', (rev.min(), rev.max())))
    chk('and it fills that band', rev.max() / rev.min(), 2.0, 2e-3)
    chk('reversed-Z buys nothing in fixed point',
        _depth_rel_err(wn, True, False) - _depth_rel_err(wn, False, False),
        np.zeros_like(wn), 0.0)

    # 9. The cube-sphere ratios, quadratured shape against closed form. The
    #    chapter files both at tier F asking for re-derivation; these are it.
    chk('gnomonic centre/corner = 3 sqrt(3)', _cube_ratio(False),
        3.0 * np.sqrt(3.0), 1e-12)
    chk('tangent centre/corner = 3 sqrt(3)/4', _cube_ratio(True),
        0.75 * np.sqrt(3.0), 1e-12)
    chk('the tangent map divides it by exactly 4',
        _cube_ratio(False) / _cube_ratio(True), 4.0, 1e-12)
    #     ...and the corner is not where the tangent map is worst. Its face
    #     minimum is the EDGE MIDPOINT at exactly 1/sqrt(2), which is the top
    #     of the chapter's quoted band; the bottom of that band is the corner.
    #     Located by a search over the face, not by evaluating the closed form
    #     at a point already believed to be the answer.
    chk('tangent centre/edge-midpoint = sqrt(2)',
        _cube_ratio(True, corner=False), np.sqrt(2.0), 1e-12)
    gg = np.linspace(-1.0, 1.0, 1201)
    UU_, VV_ = np.meshgrid(gg, gg, indexing='ij')
    for tan, want in ((False, (1.0, 1.0)), (True, (1.0, 0.0))):
        dd = _cube_density(UU_, VV_, tan)
        i_, j_ = np.unravel_index(int(np.argmin(dd)), dd.shape)
        got = (abs(gg[i_]), abs(gg[j_]))
        if sorted(got) != sorted(want):
            fails.append('%-34s min at %s, expected %s'
                         % ('cube face minimum, tangent=%s' % tan, got, want))
    chk('gnomonic: the corner IS the minimum',
        _cube_ratio(False) / _cube_ratio(False, corner=False),
        3.0 * np.sqrt(3.0) / (2.0 * np.sqrt(2.0)), 1e-12)

    # 10. The deck illuminant's two halves must re-sum to the one
    #     `atmosphere.py` publishes, and the aureole's share must invert to a
    #     moment of cos^2 that exists. The shipped pair's does not, in any band.
    #     The sum check alone is weak -- ANY two-way split of the environment
    #     re-sums. What makes the second piece the AUREOLE is that the diffuse
    #     partition holds exactly one lobe and its exponent is Rayleigh's
    #     cos^2, so that is asserted before the sum is trusted.
    if len(A.SKY_DIFFUSE_LOBES) != 1:
        fails.append('%-34s partition is no longer one lobe: %d'
                     % ('SKY_DIFFUSE_LOBES', len(A.SKY_DIFFUSE_LOBES)))
    chk('the diffuse lobe is Rayleigh\'s cos^2', A.SKY_DIFFUSE_LOBES[0][1],
        2.0, 0.0)
    e_grad, e_aur = _deck_split()
    chk('gradient + aureole == SKY_DECK', e_grad + e_aur, A.SKY_DECK, 1e-12)
    sh = e_aur / (e_grad + e_aur)
    chk('share == m/(1+m) round trip', (sh / (1.0 - sh)) / (1.0 + sh
                                                            / (1.0 - sh)),
        sh, 1e-14)
    if not np.all(sh / (1.0 - sh) <= 1.0):
        fails.append('%-34s derived moment exceeds 1: %s'
                     % ('aureole <cos^2>', sh / (1.0 - sh)))
    hand_sh = (A.SUN_COL * 0.075) / (A.SKY_AMB * 0.30 + A.SUN_COL * 0.075)
    if not np.all(hand_sh > 0.5):
        fails.append('%-34s shipped share no longer clears the ceiling: %s'
                     % ('hand aureole share', hand_sh))
    chk('the ceiling is a half', 1.0 / (1.0 + 1.0), 0.5, 0.0)

    # 11. The two receiver weights are densities, and their ratio against a
    #     uniform sky is exactly 1/2 -- checked against `env_irradiance`'s own
    #     spherical quadrature, which shares no line with the 1-D forms.
    tq = np.linspace(0.0, np.pi / 2.0, 400001)
    w_h, w_v = _recv_weights(tq)
    chk('horizontal weight integrates to 1', np.trapezoid(w_h, tq), 1.0, 1e-9)
    chk('vertical weight integrates to 1', np.trapezoid(w_v, tq), 1.0, 1e-9)
    uni = np.ones_like(A.ENV_L)
    chk('uniform sky: vertical / horizontal',
        A.env_irradiance(1., 0., 0., L=uni) / A.env_irradiance(0., 0., 1.,
                                                               L=uni),
        [0.5, 0.5, 0.5], 5e-5)
    rq = O.fresnel(np.cos(tq))[:, 1]
    chk('sin^2-weighted R_ext', np.trapezoid(rq * w_v, tq), 0.21118, 1e-5)
    chk('cos-weighted R_ext', np.trapezoid(rq * w_h, tq), 0.066690, 1e-5)

    # 12. Both `acos` forms must reproduce `solar_position`'s own azimuth
    #     through their own afternoon rules, the crossing must land on the
    #     chapter's 306, and the elevation must be even in the hour angle --
    #     which is the fold, checked rather than asserted.
    el0, _, az0, _, dec0, _, ha0 = A.solar_position(A.SITE_LAT, A.SITE_LON,
                                                    *_SUN_B)
    an0, as0 = _az_branches(dec0, el0, A.SITE_LAT)
    chk('form N, afternoon rule', 360.0 - an0, az0, 1e-9)
    chk('form S, afternoon rule', 180.0 + as0, az0, 1e-9)
    chk('the crossing', 360.0 - as0, 306.0487, 1e-3)
    chk('and it is 72 deg wrong', 360.0 - as0 - az0, 72.0973, 1e-3)
    #    The mirror hour: the same civil clock reflected about solar noon, so
    #    its hour angle is -ha0. The elevation there differs only by the
    #    declination's own drift across those 3.6 hours, which is what makes
    #    this a check on evenness rather than a restatement of it.
    _t = 15.0 + 28.0 / 60.0 - 2.0 * float(ha0) / 15.0
    el_m, _, _, _, _, _, ha_m = A.solar_position(
        A.SITE_LAT, A.SITE_LON, 2026, 8, 12, int(_t), (_t % 1.0) * 60.0,
        0.0, 1.0)
    chk('the mirror hour angle', ha_m, -ha0, 0.01)
    chk('elevation is even in it, to the declination drift', el_m, el0, 0.05)

    # 13. The wake's half-angle at the gravity ratio, against Kelvin's own
    #     closed form, and the ratio itself from `wake.py` at both ends.
    chk('half-angle at r = 1/2 == arcsin(1/3)',
        _kelvin_half_angle(0.5)[0], np.degrees(np.arcsin(1.0 / 3.0)), 1e-4)
    chk('c_g/c -> 1/2 in the gravity limit', _cg_over_c(1.0e4), 0.5, 1e-4)
    lam_min = 2.0 * np.pi / np.sqrt(W.RHO * W.G / W.SIG)
    chk('c_g == c at the capillary minimum', _cg_over_c(lam_min), 1.0, 1e-9)
    chk('and the phase speed there is wake.py\'s C_MIN',
        W.sigma_w(2.0 * np.pi / lam_min) / (2.0 * np.pi / lam_min), W.C_MIN,
        1e-12)

    if fails:
        raise SystemExit('preflight FAILED:\n  ' + '\n  '.join(fails))


# The pool's own column length, taken from the module that owns it rather than
# retyped. `optics.py` deliberately has no default depth.
B_DEPTH = 1.40


# --- figure 1: the two sides of one interface --------------------------------
def fig_two_sides(out):
    """R_ext(theta) against R_int(theta), and the exact decomposition of R_int.

    The claim: one flat surface carries TWO diffuse Fresnel constants that
    differ by 7.14x, and 92% of the larger one is not Fresnel at all. The
    equation is symmetric in the two index pairs and hides both facts; the
    SHAPES do not -- one curve has a critical angle pinned to exactly 1, the
    other has none."""
    img = P.canvas(1180, 640)
    mu_c = float(np.cos(O.TC_SNELL[1]))
    tc = float(np.degrees(O.TC_SNELL[1]))

    # -- panel A: the two directional curves, green band
    ax = P.Axes(img, (86, 54, 566, 520), (0.0, 90.0), (0.0, 1.0),
                xlabel='incidence angle from the normal, ' + DEG,
                ylabel='reflectance')
    ax.frame(xticks=[0, 15, 30, 45, 60, 75, 90],
             yticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0], yfmt='%.1f')
    th = _lin(0.0, 90.0, 1801)
    r_ext = O.fresnel(np.cos(np.radians(th)))[:, 1]
    r_int = O.r_int_at(np.cos(np.radians(th)))[:, 1]
    ax.vline(tc, ACCENT, width=2, dash=(7, 5))
    ax.hline(float(O.R_INT[1]), MUTED, width=1, dash=(2, 4))
    ax.hline(float(O.R_EXT[1]), MUTED, width=1, dash=(2, 4))
    ax.line(th, r_int, BLU, width=3, dash=(9, 5))
    ax.line(th, r_ext, INK, width=3)
    ax.text(tc + 1.5, 0.955, '%s_c = %.2f%s' % ('θ', tc, DEG), ACCENT)
    ax.text(55.0, float(O.R_INT[1]) + 0.024,
            'R_int = %.3f%%' % (100 * O.R_INT[1]), MUTED)
    ax.text(4.0, float(O.R_EXT[1]) + 0.045,
            'R_ext = %.3f%%' % (100 * O.R_EXT[1]), MUTED)
    _legend(ax, [(INK, None, 'R(%s) air %s water' % ('θ', '→')),
                 (BLU, (9, 5), 'R(%s) water %s air' % ('θ', '→'))],
            3.0, 0.86)

    # -- panel B: the cosine-weighted integrand, split at mu_c
    bx = P.Axes(img, (676, 54, 1140, 520), (0.0, 1.0), (0.0, 1.45),
                xlabel='water-side cosine %s (grazing %s normal)'
                       % ('μ', '→'),
                ylabel='2%s R(%s), the integrand' % ('μ', 'μ'))
    bx.frame(xticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
             yticks=[0.0, 0.4, 0.8, 1.2], xfmt='%.1f', yfmt='%.1f')
    m = _lin(0.0, 1.0, 2001)
    gi = 2.0 * m * O.r_int_at(m)[:, 1]
    ge = 2.0 * m * O.fresnel(m)[:, 1]
    lo = np.zeros_like(m)
    left = m <= mu_c
    bx.fill_between(m[left], lo[left], gi[left], FILL_A)
    bx.fill_between(m[~left], lo[~left], gi[~left], FILL_B)
    bx.fill_between(m, lo, ge, FILL_C)
    bx.line(m, gi, BLU, width=3, dash=(9, 5))
    bx.line(m, ge, INK, width=3)
    bx.vline(mu_c, ACCENT, width=2, dash=(7, 5))
    bx.text(mu_c - 0.02, 1.39, '%s_c = %.4f' % ('μ', mu_c), ACCENT,
            anchor='rs')
    bx.text(0.30, 0.42, '%.5f' % (1.0 - 1.0 / O.IOR[1] ** 2), INK, anchor='ms')
    bx.text(0.86, 0.13, '%.5f' % float(O.R_INT[1] - (1 - 1 / O.IOR[1] ** 2)),
            INK, anchor='ms')
    bx.text(0.30, 0.045, '%.5f' % float(O.R_EXT[1]), INK, anchor='ms')
    _legend(bx, [(INK, None, '2%s R_ext(%s)' % ('μ', 'μ')),
                 (BLU, (9, 5), '2%s R_int(%s)' % ('μ', 'μ'))],
            0.05, 1.30)
    return P.save(img, os.path.join(out, 'fresnel-two-sides.png'))


# --- figure 2: attenuation and escape do not factorise -----------------------
def fig_factorisation(out):
    """The correlation that breaks the product, and what it costs against tau.

    The claim: <fg> = <f><g> + Cov(f, g), and the two factors of the exit
    transport share their integration variable. Panel A parameterises the two
    factors by mu and plots one against the other: a monotone rising track IS
    the +0.76, a falling one IS the -0.85. Panel B is the size of it, per band,
    which is the correction the chapter's own table needed."""
    img = P.canvas(1180, 640)
    tau_pool = O.ABS * B_DEPTH

    # -- panel A: the two integrands, and the gap between their areas.
    # Red band at this pool's own column, because red is where the error is
    # largest and the two areas are then far enough apart to see.
    ax = P.Axes(img, (92, 54, 578, 520), (0.0, 1.0), (0.0, 1.45),
                xlabel='water-side cosine %s (grazing %s normal)' % ('μ', '→'),
                ylabel='integrand over the measure 2%s d%s' % ('μ', 'μ'))
    ax.frame(xticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
             yticks=[0.0, 0.4, 0.8, 1.2], xfmt='%.1f', yfmt='%.1f')
    m = _lin(1e-3, 1.0, 2001)
    f = np.exp(-tau_pool[0] / m)                  # attenuation along 1/mu
    g = 1.0 - O.r_int_at(m)[:, 0]                 # what escapes at that mu
    joint = 2.0 * m * f * g                       # area = T_esc, the transport
    sep_val = float(O._e3(tau_pool[0])[0] * (1.0 - O.R_INT[0]))
    sep = 2.0 * m * sep_val                       # area = <f><g>, the product
    _fill_signed(ax, m, sep, joint, FILL_B, FILL_C)
    ax.line(m, f, MUTED, width=2, dash=(3, 4))
    ax.line(m, g, MUTED, width=2, dash=(9, 5))
    ax.line(m, sep, ACCENT, width=3, dash=(7, 5))
    ax.line(m, joint, RED, width=3)
    ax.vline(float(np.cos(O.TC_SNELL[0])), MUTED, width=1, dash=(2, 6))
    _legend(ax, [(MUTED, (3, 4), 'f(%s) = exp(-%s/%s)' % ('μ', 'τ', 'μ')),
                 (MUTED, (9, 5), 'g(%s) = 1 - R_int(%s)' % ('μ', 'μ')),
                 (RED, None, '2%s f g   %s  T_esc = %.4f'
                  % ('μ', '→', O.slab_esc(B_DEPTH)[0])),
                 (ACCENT, (7, 5), '2%s mean(f) mean(g)  %s  %.4f'
                  % ('μ', '→', sep_val))],
            0.04, 1.39)

    # -- panel B: the size of it against tau, both legs, per band
    bx = P.Axes(img, (688, 54, 1140, 520), (0.0, 2.0), (-90.0, 70.0),
                xlabel='vertical optical depth %s = a d' % 'τ',
                ylabel='joint / separated - 1,  %')
    bx.frame(xticks=[0.0, 0.5, 1.0, 1.5, 2.0],
             yticks=[-80, -60, -40, -20, 0, 20, 40, 60], xfmt='%.1f')
    bx.hline(0.0, INK, width=1, dash=(2, 4))
    t = _lin(1e-3, 2.0, 401)
    e3 = O._e3(t)
    e3_2 = O._e3(2.0 * t)
    for c in (0, 1, 2):
        a = np.zeros(3)
        a[c] = 1.0
        esc = np.array([O.slab_esc(x, absorb=a)[c] for x in t])
        rt = np.array([O.slab_trap(x, absorb=a)[c] for x in t])
        bx.line(t, 100.0 * (esc / (e3 * (1.0 - O.R_INT[c])) - 1.0), BAND[c],
                width=3, dash=BAND_DASH[c])
        bx.line(t, 100.0 * (rt / (e3_2 * O.R_INT[c]) - 1.0), BAND[c],
                width=3, dash=BAND_DASH[c])
    for c in (0, 1, 2):
        tp = float(tau_pool[c])
        bx.vline(tp, MUTED, width=1, dash=(2, 6))
        bx.marker(tp, 100.0 * float(O.slab_esc(B_DEPTH)[c]
                                    / (O._e3(np.array([tp]))[0]
                                       * (1 - O.R_INT[c])) - 1), BAND[c])
        bx.marker(tp, 100.0 * float(O.slab_trap(B_DEPTH)[c]
                                    / (O._e3(np.array([2 * tp]))[0]
                                       * O.R_INT[c]) - 1), BAND[c])
    _legend(bx, [(BAND[c], BAND_DASH[c], BAND_NAME[c]) for c in (0, 1, 2)],
            0.06, 62.0)
    return P.save(img, os.path.join(out, 'lut-factorisation.png'))


# --- figure 3: the trapped series, its truncations and its bound -------------
def fig_trapped_series(out):
    """1/(1 - rho R_int) against what the column actually returns.

    The claim: the trap's gain rises with albedo, truncating it at one bounce
    costs 7-10% CHROMATICALLY, and the lossless series is an upper bound that
    an absorbing column does not reach. Three separate errors, all in the same
    quantity, all invisible in a luminance check -- which is exactly what one
    axis with four curves on it shows and three tables do not."""
    img = P.canvas(1180, 640)
    rho = _lin(0.0, 1.0, 801)
    liner = np.array([0.222, 0.585, 0.681])       # this chapter's own liner

    # -- panel A: the truncations, at the diffuse constant and the wrong one
    ax = P.Axes(img, (92, 54, 578, 520), (0.0, 1.0), (1.0, 2.0),
                xlabel='bed albedo %s (water-side)' % 'ρ',
                ylabel='trapped gain')
    ax.frame(xticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
             yticks=[1.0, 1.2, 1.4, 1.6, 1.8, 2.0], xfmt='%.1f', yfmt='%.1f')
    exact = 1.0 / (1.0 - rho * O.R_INT[1])
    one = 1.0 + rho * O.R_INT[1]
    two = one + (rho * O.R_INT[1]) ** 2
    tir_only = 1.0 / (1.0 - rho * (1.0 - 1.0 / O.IOR[1] ** 2))
    _fill_signed(ax, rho, one, exact, FILL_B, FILL_B)
    ax.line(rho, tir_only, ACCENT, width=2, dash=(2, 6))
    ax.line(rho, one, GRN, width=2, dash=(3, 4))
    ax.line(rho, two, GRN, width=2, dash=(9, 5))
    ax.line(rho, exact, INK, width=3)
    for c in (0, 1, 2):
        ax.vline(float(liner[c]), MUTED, width=1, dash=(2, 6))
        ax.marker(float(liner[c]),
                  float(1.0 / (1.0 - liner[c] * O.R_INT[1])), BAND[c])
    _legend(ax, [(INK, None, '1/(1 - %s R_int)' % 'ρ'),
                 (GRN, (9, 5), 'two bounces'),
                 (GRN, (3, 4), 'one bounce'),
                 (ACCENT, (2, 6), '1/(1 - %s (1 - 1/n%s))' % ('ρ', '²'))],
            0.04, 1.94)

    # -- panel B: the lossless series as a BOUND the real column does not reach
    bx = P.Axes(img, (688, 54, 1140, 520), (0.0, 1.0), (1.0, 2.0),
                xlabel='bed albedo %s (water-side)' % 'ρ',
                ylabel='trapped gain at d = %.2f m' % B_DEPTH)
    bx.frame(xticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
             yticks=[1.0, 1.2, 1.4, 1.6, 1.8, 2.0], xfmt='%.1f', yfmt='%.1f')
    grt = O.slab_trap(B_DEPTH)
    for c in (0, 1, 2):
        bound = 1.0 / (1.0 - rho * O.R_INT[c])
        real = 1.0 / (1.0 - rho * grt[c])
        _fill_signed(bx, rho, real, bound, FILL_C, FILL_C)
        bx.line(rho, bound, INK, width=2, dash=BAND_DASH[c])
        bx.line(rho, real, BAND[c], width=3, dash=BAND_DASH[c])
    for c in (0, 1, 2):
        bx.vline(float(liner[c]), MUTED, width=1, dash=(2, 6))
        bx.marker(float(liner[c]), float(1.0 / (1.0 - liner[c] * grt[c])),
                  BAND[c])
    _legend(bx, [(INK, (3, 4), '1/(1 - %s R_int),  no absorption' % 'ρ')]
            + [(BAND[c], BAND_DASH[c], '1/(1 - %s G_rt),  %s'
                % ('ρ', BAND_NAME[c])) for c in (0, 1, 2)], 0.04, 1.94)
    return P.save(img, os.path.join(out, 'trapped-series.png'))


# --- figure 4: a distribution is not a surface -------------------------------
def fig_runup(out):
    """The swash exceedance painted where its realisation belongs.

    The claim, and the chapter calls it the same defect class as glitter drawn
    as its slope pdf and foam drawn as its own mean: `exp(-(z/sigma)^2)` is the
    share of cycles reaching a level, so blending wet into dry by it draws the
    beach's TIME-AVERAGE, and an average has no edge. This is the one claim in
    the water chapters that a paragraph genuinely cannot carry, because the
    whole of it is that one picture has a boundary and the other does not.

    Both panels are FIELDS OF SCENE-LINEAR ALBEDO, not renders: grey level is
    linear in albedo with one common scale factor, no exposure, no tone curve
    and no gamma. Nothing here is display-referred."""
    import beach_render as BR                    # read-only, for the sand pair

    img = P.canvas(1180, 700)
    y = _lin(0.0, 120.0, 480)
    z = _lin(0.0, 1.10, 260)
    ZZ, YY = np.meshgrid(z, y, indexing='ij')

    # the shipped blend, taken from the renderer rather than retyped
    def albedo(wet):
        w = np.asarray(wet, float)[..., None]
        return BR.SAND_DRY * (1.0 - w) + BR.SAND_WET_DIFF * w

    dist = B.swash_wetness(ZZ)                   # the exceedance: a DISTRIBUTION
    real = (ZZ <= B.damp_limit(YY)).astype(float)  # one draw: a REALISATION
    scale = 255.0 / float(BR.SAND_DRY.max())

    def strip(w):
        a = np.clip(albedo(w) * scale, 0, 255).astype(np.uint8)
        return a[::-1]                            # elevation up the page

    box_a = (92, 54, 566, 300)
    box_b = (92, 386, 566, 632)  # xlabel below
    ax = P.Axes(img, box_a, (0.0, 120.0), (0.0, 1.10),
                ylabel='elevation z, m')
    ax.image(strip(dist))
    ax.frame(yticks=[0.0, 0.5, 1.0], yfmt='%.1f')
    ax.hline(float(B.damp_limit_median()), ACCENT, width=2, dash=(7, 5))
    bx = P.Axes(img, box_b, (0.0, 120.0), (0.0, 1.10),
                xlabel='alongshore position y, m', ylabel='elevation z, m')
    bx.image(strip(real))
    bx.frame(xticks=[0, 30, 60, 90, 120], yticks=[0.0, 0.5, 1.0], yfmt='%.1f')
    bx.hline(float(B.damp_limit_median()), ACCENT, width=2, dash=(7, 5))

    # the vertical cut through both, in scene-linear albedo
    cx = P.Axes(img, (688, 54, 1140, 632), (0.21, 0.43), (0.0, 1.10),
                xlabel='scene-linear albedo, green band',
                ylabel='elevation z, m')
    cx.frame(xticks=[0.22, 0.26, 0.30, 0.34, 0.38, 0.42],
             yticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0], xfmt='%.2f', yfmt='%.1f')
    a_dist = albedo(B.swash_wetness(z))[:, 1]
    cx.line(a_dist, z, ACCENT, width=3, dash=(9, 5))
    stations = (0.0, 27.5, 55.1, 82.6)
    for i, y0 in enumerate(stations):
        zl = float(B.damp_limit(np.array([y0]))[0])
        w = (z <= zl).astype(float)
        cx.line(albedo(w)[:, 1], z, INK, width=2 if i else 3)
    cx.hline(float(B.damp_limit_median()), ACCENT, width=1, dash=(2, 6))
    _legend(cx, [(ACCENT, (9, 5), 'painted by the exceedance p(z)'),
                 (INK, None, 'one realisation, four stations')], 0.222, 1.06)
    return P.save(img, os.path.join(out, 'runup-distribution-vs-realisation.png'))


# --- figure 5: Sommerfeld's half-plane ---------------------------------------
def fig_sommerfeld(out):
    """K_d across the shadow boundary, and the Cornu spiral that fixes the half.

    The claim: K_d = 1/2 on the geometric shadow boundary EXACTLY, at every kr
    and with no asymptotics in it; the lit side overshoots and rings; and a
    model that returns a clean 1 and 0 there has smoothed the physics away.
    Two of those three are shapes. The spiral is not decoration -- K_d is
    1/sqrt2 times the chord from the current point to the upper eye, so the
    half at v = 0 is the chord from the origin, and C(inf) = S(inf) = 1/2 is
    why it is a half and not something else."""
    img = P.canvas(1180, 620)

    ax = P.Axes(img, (92, 54, 578, 500), (-6.0, 6.0), (0.0, 1.25),
                xlabel='Fresnel parameter v  (lit %s 0 %s geometric shadow)'
                       % ('←', '→'),
                ylabel='K_d = |U| / |U_incident|')
    ax.frame(xticks=[-6, -4, -2, 0, 2, 4, 6],
             yticks=[0.0, 0.25, 0.5, 0.75, 1.0, 1.25], yfmt='%.2f')
    v = _lin(-6.0, 6.0, 2401)
    ax.hline(1.0, MUTED, width=1, dash=(2, 6))
    ax.hline(0.5, ACCENT, width=1, dash=(2, 6))
    ax.vline(0.0, ACCENT, width=2, dash=(7, 5))
    ax.line(v, BD.knife_edge_kd(v), INK, width=3)
    ax.marker(0.0, float(BD.knife_edge_kd(0.0)), ACCENT, r=5)
    for vv in (0.5, 1.0, 2.0):
        ax.marker(vv, float(BD.knife_edge_kd(vv)), BLU, r=4)
    ax.text(0.35, 0.53, 'K_d(0) = %.4f' % BD.knife_edge_kd(0.0), ACCENT)

    bx = P.Axes(img, (700, 54, 1140, 500), (-0.75, 0.75), (-0.75, 0.75),
                xlabel='C(x)', ylabel='S(x)')
    bx.frame(xticks=[-0.5, 0.0, 0.5], yticks=[-0.5, 0.0, 0.5],
             xfmt='%.1f', yfmt='%.1f')
    x = _lin(-8.0, 8.0, 6001)
    f = BD.fresnel(x)
    cl = BD.cornu_limit()
    bx.line(f.real, f.imag, INK, width=2)
    bx.line([0.0, cl[0]], [0.0, cl[1]], ACCENT, width=3)
    bx.line([-cl[0], cl[0]], [-cl[1], cl[1]], BLU, width=2, dash=(7, 5))
    bx.marker(cl[0], cl[1], ACCENT, r=5)
    bx.marker(-cl[0], -cl[1], BLU, r=5)
    bx.marker(0.0, 0.0, ACCENT, r=5)
    bx.text(0.22, 0.66, 'x %s +%s' % ('→', '∞'), MUTED, anchor='rs')
    bx.text(-0.22, -0.71, 'x %s -%s' % ('→', '∞'), MUTED)
    bx.text(0.03, -0.06, 'x = 0', MUTED)
    return P.save(img, os.path.join(out, 'sommerfeld-half-plane.png'))


# --- figure 6: the glitter path's width is a function ------------------------
def _glit_profile(view_el, sun_el=21.02, dphi=None):
    """One azimuth cut of the Cox & Munk glitter path, green band, at a stated
    view elevation. Everything comes from `beach_optics.glitter_radiance`."""
    if dphi is None:
        dphi = _lin(-40.0, 40.0, 1601)

    def d(el, az):
        el, az = np.radians(el), np.radians(az)
        return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                         np.sin(el) * np.ones_like(az)], -1)
    s = d(sun_el, 180.0 * np.ones(1))[0]
    r = d(view_el, dphi)
    L = BO.glitter_radiance(s, -r)[:, 1]
    return dphi, L


def _fwhm(dphi, L):
    pk = float(L.max())
    over = dphi[L >= 0.5 * pk]
    return float(over.max() - over.min()), pk


def fig_glitter_path(out):
    """The path narrows toward the horizon while it brightens.

    The claim: a glitter path of uniform width is wrong and it is the default,
    and the error is a SHAPE rather than a level, so no exposure check sees it.
    A shape claim is the one kind a table cannot make -- the chapter's two
    monotone columns are here as two curves that go opposite ways, from one
    slope distribution and one wind."""
    img = P.canvas(1180, 620)
    els = (25.0, 15.0, 6.0, 1.5, 0.2)
    styles = (None, (9, 5), (3, 4), (2, 6), (1, 3))

    ax = P.Axes(img, (86, 54, 470, 500), (-25.0, 25.0), (0.0, 1.06),
                xlabel='azimuth from the path centre %s%s, %s'
                       % ('Δ', 'φ', DEG),
                ylabel='radiance / its own peak')
    ax.frame(xticks=[-20, -10, 0, 10, 20],
             yticks=[0.0, 0.25, 0.5, 0.75, 1.0], yfmt='%.2f')
    ax.hline(0.5, MUTED, width=1, dash=(2, 6))
    ent = []
    for i, e in enumerate(els):
        dphi, L = _glit_profile(e)
        w, pk = _fwhm(dphi, L)
        ax.line(dphi, L / pk, INK if i == 0 else BLU, width=3 if i == 0 else 2,
                dash=styles[i])
        ent.append((INK if i == 0 else BLU, styles[i], '%.1f%s' % (e, DEG)))
    _legend(ax, ent, -24.0, 1.02)

    sweep = np.array([25.0, 21.02, 18.0, 15.0, 12.0, 10.0, 8.0, 6.0, 4.5, 3.0,
                      2.0, 1.5, 1.0, 0.5, 0.2])
    ws, pks = [], []
    for e in sweep:
        dphi, L = _glit_profile(e)
        w, pk = _fwhm(dphi, L)
        ws.append(w)
        pks.append(pk)
    ws, pks = np.array(ws), np.array(pks)

    bx = P.Axes(img, (566, 54, 830, 500), (0.0, 26.0), (0.0, 17.0),
                xlabel='view elevation, ' + DEG,
                ylabel='path FWHM in azimuth, ' + DEG)
    bx.frame(xticks=[0, 5, 10, 15, 20, 25], yticks=[0, 4, 8, 12, 16])
    bx.line(sweep, ws, INK, width=3)
    for e, w in zip(sweep, ws):
        if e in (25.0, 0.2):
            bx.marker(e, w, ACCENT, r=5)

    cx = P.Axes(img, (912, 54, 1140, 500), (0.0, 26.0), (0.0, 210.0),
                xlabel='view elevation, ' + DEG,
                ylabel='peak radiance, green band, scene-linear')
    cx.frame(xticks=[0, 5, 10, 15, 20, 25], yticks=[0, 50, 100, 150, 200])
    cx.line(sweep, pks, INK, width=3)
    for e, p_ in zip(sweep, pks):
        if e in (25.0, 0.2):
            cx.marker(e, p_, ACCENT, r=5)
    return P.save(img, os.path.join(out, 'glitter-path-narrowing.png'))


# =============================================================================
# `09-planetary-precision.md` and `10-lighting-shadows.md` and `19` -- see the
# SECOND PROVENANCE CATEGORY note at the top of this file for what the three
# `09` figures are measured against, since it is not an implementation module.
# =============================================================================

# The astronomical unit, exactly, as the IAU defined it in 2012. This is a UNIT
# CONVERSION and not a physical constant -- the same status as the 1000 in a
# kilometre -- and it is here only to label one tick on a log axis.
_AU_M = 149597870700.0


def _ticks(ax, xs=None, xlabs=None, ys=None, ylabs=None):
    """Grid lines with hand-written tick labels.

    `beach_plot.frame` formats a tick as `fmt % value`, which cannot turn the
    log10 value -3.0 into '1 mm'. Every axis below that carries the log10 of a
    quantity is labelled in the quantity's own units instead, because a reader
    checking a figure against a chapter's table should not have to exponentiate
    in their head. Data-to-pixel and text only -- no arithmetic on the data."""
    if xs is not None:
        for v, s in zip(xs, xlabs):
            px = float(ax.px(v))
            ax.d.line([px, ax.y0, px, ax.y1], fill=P.GRID)
            ax.d.text((px, ax.y1 + 4), s, fill=MUTED, font=P.FONT_S,
                      anchor='ma')
    if ys is not None:
        for v, s in zip(ys, ylabs):
            py = float(ax.py(v))
            ax.d.line([ax.x0, py, ax.x1, py], fill=P.GRID)
            ax.d.text((ax.x0 - 6, py), s, fill=MUTED, font=P.FONT_S,
                      anchor='rm')


# --- figure 7: float32 degrades in steps, not on a slope ---------------------
_F32_ROWS = (('1 km', 1e3), ('10 km', 1e4), ('100 km', 1e5),
             ('1000 km', 1e6), ('6371 km', 6.371e6), ('1 AU', _AU_M))


def _f32_spacing(x):
    """The distance to the next representable float32 above `x`, asked of
    IEEE-754 rather than computed from a rule. This is the whole source of
    figure 7 and of the left half of figure 8: numpy's `float32` IS the
    hardware's format, so there is no constant here to drift from."""
    return np.spacing(np.asarray(x, np.float32)).astype(np.float64)


def fig_float_binades(out):
    """The spacing staircase, and the factor of two the chapter's rule hides.

    The claim, as `09` states it: float32 has "an absolute spacing between
    representable values of `x * 2^-23 ~= x * 1.2e-7` at magnitude `x`", and
    then a five-row table of that product. The product is not the spacing. It
    is the spacing's WORST CASE inside a binade: the true spacing is
    `2^(floor(log2 x) - 23)`, constant between consecutive powers of two and
    doubling at each one, so `x * 2^-23` overstates it by a factor that runs
    from 1 to 2 depending on where `x` sits in its binade.

    That is a shape claim and a table cannot make it. A reader of the table
    sees a smooth 1.2e-7 law and budgets against a slope; the truth is a
    staircase, and two worlds whose sizes differ by a hair either side of a
    power of two differ by 2x in vertex precision. Panel B is the size of the
    overstatement, and the chapter's own six rows are marked on it."""
    img = P.canvas(1180, 640)
    # The window is 10 km to 10,000 km: eleven binades, which is few enough
    # that the individual treads are legible and wide enough to hold four of
    # the chapter's five terrestrial rows. Twelve decades of log-log turns the
    # staircase into a straight line and the sawtooth into a picket fence --
    # the shape is only a shape at a scale where a step is a step.
    lo, hi = 4.0, 7.0
    lx = _lin(lo, hi, 24001)
    x = 10.0 ** lx
    sp = _f32_spacing(x)
    l2 = np.log10(2.0)
    rows = [(n, v) for n, v in _F32_ROWS if lo <= np.log10(v) <= hi]

    ax = P.Axes(img, (108, 54, 578, 520), (lo, hi), (-3.3, 0.45),
                xlabel='distance from the origin',
                ylabel='spacing to the next representable float32')
    ax.frame()
    _ticks(ax, [4, 5, 6, 7], ['10 km', '100 km', '1000 km', '10 000 km'],
           [-3, -2, -1, 0], ['1 mm', '1 cm', '10 cm', '1 m'])
    ax.fill_between(lx, np.log10(x) - 24 * l2, np.log10(x) - 23 * l2, FILL_C)
    ax.line(lx, np.log10(x) - 23 * l2, ACCENT, width=2, dash=(7, 5))
    ax.line(lx, np.log10(x) - 24 * l2, MUTED, width=2, dash=(2, 6))
    ax.line(lx, np.log10(sp), INK, width=3)
    for nm, v in rows:
        lv = float(np.log10(v))
        ax.vline(lv, MUTED, width=1, dash=(2, 6))
        ax.marker(lv, float(np.log10(_f32_spacing(v))), BLU, r=5)
    ax.text(5.78, -2.52, 'the table, and the truth', INK)
    ax.text(5.78, -2.82, '1000 km:  12 %s 6.25 cm' % '→', BLU)
    ax.text(5.78, -3.10, '6371 km:  0.76 %s 0.50 m' % '→', BLU)
    _legend(ax, [(INK, None, 'the spacing itself (IEEE-754)'),
                 (ACCENT, (7, 5),
                  'x %s 2%s -- the chapter\'s rule, and the tread\'s TOP'
                  % ('·', '⁻²³')),
                 (MUTED, (2, 6), 'x %s 2%s -- the tread\'s bottom'
                  % ('·', '⁻²⁴'))], 4.06, 0.33)

    bx = P.Axes(img, (688, 54, 1140, 520), (lo, hi), (0.95, 2.25),
                xlabel='distance from the origin',
                ylabel='(x %s 2%s) %s the true spacing' % ('·', '⁻²³', '÷'))
    bx.frame(yticks=[1.0, 1.25, 1.5, 1.75, 2.0], yfmt='%.2f')
    _ticks(bx, [4, 5, 6, 7], ['10 km', '100 km', '1000 km', '10 000 km'])
    bx.hline(1.0, MUTED, width=1, dash=(2, 4))
    bx.hline(2.0, ACCENT, width=1, dash=(2, 4))
    bx.line(lx, (x * 2.0 ** -23) / sp, INK, width=3)
    for i, (nm, v) in enumerate(rows):
        lv = float(np.log10(v))
        r = float(v * 2.0 ** -23 / _f32_spacing(v))
        bx.vline(lv, MUTED, width=1, dash=(2, 6))
        bx.marker(lv, r, BLU, r=5)
        right = lv < hi - 0.6
        bx.text(lv + (0.07 if right else -0.07),
                r + (0.06 if r < 1.7 else -0.14),
                '%s  %.2f%s' % (nm, r, '×'), INK,
                anchor='ls' if right else 'rs')
    bx.text(6.94, 2.09, 'the rule can be no worse than 2%s' % '×', ACCENT,
            anchor='rs')
    return P.save(img, os.path.join(out, 'float32-binade-staircase.png'))


# --- figure 8: reversed-Z, and what it does and does not buy -----------------
def _depth_rel_err(wn, reversed_z, float_depth):
    """Relative depth resolution `dw/w` at view distance `w = wn * near`, for
    the four combinations `09` names.

    With the infinite far plane the chapter mandates, the whole projection
    collapses to one expression and `near` CANCELS: reversed-Z writes
    `z = near/w`, standard-Z writes `z = 1 - near/w`. Differentiating,
    `|dw/dz| = w^2/near` for both, so

        dw/w = (w/near) * (the depth buffer's own spacing at that z)

    and the only thing that differs between the four curves is where that
    spacing comes from -- IEEE-754's `float32`, asked directly, or a 24-bit
    fixed-point step of 2^-24. There is not one chosen number in this figure:
    the x axis is dimensionless and the y axis is a ratio."""
    wn = np.asarray(wn, float)
    z = 1.0 / wn if reversed_z else 1.0 - 1.0 / wn
    step = (_f32_spacing(z) if float_depth
            else np.full(z.shape, 2.0 ** -24))
    return wn * step


def fig_depth_precision(out):
    """Two of `09`'s sentences, and both of them are shapes.

    The claim: "Reversed-Z aligns the two gradients instead of opposing them,
    yielding near-constant relative error across the range", and "with a 24-bit
    *fixed* depth buffer reversed-Z gains almost nothing". The first is a curve
    that stays flat over seven decades while its opposite number climbs by
    seven; the second is two curves lying exactly on top of each other. Neither
    survives being written as a level.

    Panel B is the flat curve at its own scale, and it is figure 7 again: the
    relative error of reversed-Z float32 is the binade staircase, so "constant"
    means constant to a factor of exactly 2 and never better."""
    img = P.canvas(1180, 640)
    lw = _lin(1e-4, 7.0, 4801)
    wn = 10.0 ** lw

    ax = P.Axes(img, (104, 54, 578, 520), (0.0, 7.0), (-8.0, 1.0),
                xlabel='view distance, in units of the near plane (w / near)',
                ylabel='relative depth resolution %sw / w' % 'Δ')
    ax.frame()
    _ticks(ax, [0, 1, 2, 3, 4, 5, 6, 7],
           ['1', '10', '10%s' % '²', '10%s' % '³', '10%s' % '⁴', '10%s' % '⁵',
            '10%s' % '⁶', '10%s' % '⁷'],
           [-8, -6, -4, -2, 0], ['10%s' % '⁻⁸', '10%s' % '⁻⁶', '10%s' % '⁻⁴',
                                 '10%s' % '⁻²', '1'])
    # The three losing curves lie on top of one another to the last bit past
    # w/near = 2, so they are drawn thick-to-thin: all three stay visible and
    # the coincidence is the point rather than an accident of draw order.
    for rev, flt, col, dash, wid in ((False, True, RED, None, 7),
                                     (False, False, BLU, (3, 4), 5),
                                     (True, False, GRN, (9, 5), 3),
                                     (True, True, INK, None, 3)):
        e = _depth_rel_err(wn, rev, flt)
        ax.line(lw, np.log10(np.where(e > 0, e, np.nan)), col, width=wid,
                dash=dash)
    ax.text(5.7, -4.7, 'all three are the SAME curve', MUTED, anchor='rs')
    ax.text(4.75, -6.6, 'reversed-Z + float32', INK)
    _legend(ax, [(INK, None, 'reversed-Z, float32'),
                 (GRN, (9, 5), 'reversed-Z, 24-bit fixed'),
                 (BLU, (3, 4), 'standard Z, 24-bit fixed'),
                 (RED, None, 'standard Z, float32')], 0.2, 0.62)

    # Panel B: the only window in which the four are not two. A float depth
    # buffer under STANDARD Z writes z = 1 - near/w, which is inside the
    # binade [1/2, 1) for every w past twice the near plane -- so its mantissa
    # is all that is left and it degenerates to fixed point exactly. The
    # exponent buys precision only while w < 2 near, which is the one place
    # nothing needs it.
    lin = _lin(1.0, 6.0, 28001)
    bx = P.Axes(img, (688, 54, 1140, 520), (1.0, 6.0), (-8.7, -6.2),
                xlabel='view distance, in units of the near plane (w / near)',
                ylabel='relative depth resolution %sw / w' % 'Δ')
    bx.frame(xticks=[1, 2, 3, 4, 5, 6])
    _ticks(bx, None, None, [-8.5, -8.0, -7.5, -7.0],
           ['10%s' % '⁻⁸·⁵', '10%s' % '⁻⁸', '10%s' % '⁻⁷·⁵', '10%s' % '⁻⁷'])
    for rev, flt, col, dash, wid in ((False, True, RED, None, 7),
                                     (False, False, BLU, (3, 4), 5),
                                     (True, True, INK, None, 3)):
        e = _depth_rel_err(lin, rev, flt)
        bx.line(lin, np.log10(np.where(e > 0, e, np.nan)), col, width=wid,
                dash=dash)
    bx.vline(2.0, ACCENT, width=2, dash=(7, 5))
    bx.text(5.9, -8.34, 'past w = 2 near the float exponent', ACCENT,
            anchor='rs')
    bx.text(5.9, -8.54, 'is spent, and reversed-Z is the', ACCENT,
            anchor='rs')
    bx.text(5.9, -8.66, 'only thing still buying anything', ACCENT,
            anchor='rs')
    return P.save(img, os.path.join(out, 'depth-precision-reversed-z.png'))


# --- figure 9: the cube-sphere's two mappings, re-derived --------------------
def _cube_density(u, v, tangent):
    """Relative solid angle per unit face area for the cube->sphere map.

    Gnomonic sends the face point `(u, v, 1)` to its own direction, whose
    Jacobian onto the sphere is `(1 + u^2 + v^2)^(-3/2)`. The tangent-adjusted
    variant applies `u' = tan(u pi/4)` per axis first, which multiplies in
    `du'/du = (pi/4) sec^2(u pi/4)`. Both are the chapter's own prescriptions;
    the numbers they produce are computed here rather than quoted, which is
    what `09` asks for when it files them at tier F with "re-derive before
    quoting in print"."""
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    if tangent:
        du = (np.pi / 4.0) / np.cos(u * np.pi / 4.0) ** 2
        dv = (np.pi / 4.0) / np.cos(v * np.pi / 4.0) ** 2
        U, V = np.tan(u * np.pi / 4.0), np.tan(v * np.pi / 4.0)
        return du * dv / (1.0 + U ** 2 + V ** 2) ** 1.5
    return np.ones_like(u * v) / (1.0 + u ** 2 + v ** 2) ** 1.5


def _cube_ratio(tangent, corner=True):
    """Face centre over face CORNER (the number the chapter carries), or over
    the face EDGE MIDPOINT, which for the tangent-adjusted map is the smaller
    of the two and therefore the one that bounds the variation."""
    u, v = (1.0, 1.0) if corner else (1.0, 0.0)
    return float(_cube_density(0.0, 0.0, tangent)
                 / _cube_density(u, v, tangent))


def fig_cube_sphere(out):
    """What the tangent adjustment buys, and why its number was ever a range.

    The claim: gnomonic "varies texel solid angle by ~5.2x between face centre
    and corner"; tangent-adjusted "cuts the variation to roughly 1.3-1.4x".
    Both sit at tier **F** with the instruction to re-derive before quoting,
    and this figure is that re-derivation.

    Gnomonic comes out at `3 sqrt(3) = 5.1962`, and for gnomonic the corner IS
    the face minimum, so one number describes the whole face. The tangent
    variant does not behave that way and the quoted range is the fingerprint of
    it. Centre-to-corner it is `3 sqrt(3)/4 = 1.2990` -- exactly a quarter of
    the gnomonic figure, which is a closed form neither the chapter nor its
    sources state. But the corner is not where the tangent map is worst: the
    density falls FASTER along the edge midline than along the diagonal, and
    bottoms out at the EDGE MIDPOINT at exactly `1/sqrt(2)`, so the variation
    across the face is `sqrt(2) = 1.4142`.

    That is the whole of "roughly 1.3-1.4". The two ends of the folklore band
    are not an uncertainty; they are two different measurements -- 1.2990 to
    the corner and 1.4142 to the edge midpoint -- and the second is the one a
    resolution budget needs. The shape is what makes it visible: for gnomonic
    the diagonal is the steepest way off the centre, and for tangent-adjusted
    it is the shallowest."""
    img = P.canvas(1180, 660)
    t = _lin(0.0, 1.0, 801)

    ax = P.Axes(img, (100, 54, 588, 540), (0.0, 1.0), (0.0, 1.25),
                xlabel='distance from the face centre, in face half-widths',
                ylabel='solid angle per unit face area, %s its own centre'
                       % '÷')
    ax.frame(xticks=[0.0, 0.25, 0.5, 0.75, 1.0],
             yticks=[0.0, 0.25, 0.5, 0.75, 1.0, 1.25],
             xfmt='%.2f', yfmt='%.2f')
    ax.hline(1.0, MUTED, width=1, dash=(2, 4))
    for tan, col, dash in ((False, INK, None), (True, BLU, (9, 5))):
        for edge, w in ((False, 3), (True, 2)):
            d = (_cube_density(t, 0.0 * t if edge else t, tan)
                 / _cube_density(0.0, 0.0, tan))
            ax.line(t, d, col, width=w, dash=(2, 5) if edge else dash)
            ax.marker(1.0, float(d[-1]), ACCENT, r=5)
    ax.text(0.985, 0.845, 'corner  4/(3%s3) = %.4f'
            % ('√', 1.0 / _cube_ratio(True)), ACCENT, anchor='rs')
    ax.text(0.985, 0.665, 'edge mid  1/%s2 = %.4f'
            % ('√', 1.0 / _cube_ratio(True, corner=False)), ACCENT,
            anchor='rs')
    ax.text(0.985, 0.395, 'edge mid  1/(2%s2) = %.4f'
            % ('√', 1.0 / _cube_ratio(False, corner=False)), ACCENT,
            anchor='rs')
    ax.text(0.985, 0.115, 'corner  1/(3%s3) = %.4f'
            % ('√', 1.0 / _cube_ratio(False)), ACCENT, anchor='rs')
    _legend(ax, [(INK, None, 'gnomonic, along the diagonal'),
                 (INK, (2, 5), 'gnomonic, along the edge midline'),
                 (BLU, (9, 5), 'tangent-adjusted, diagonal'),
                 (BLU, (2, 5), 'tangent-adjusted, edge midline')],
            0.03, 0.28)

    n = 220
    g = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    UU, VV = np.meshgrid(g, g, indexing='ij')
    for i, (tan, box) in enumerate(((False, (690, 96, 900, 306)),
                                    (True, (920, 96, 1130, 306)))):
        d = _cube_density(UU, VV, tan)
        d = d / d.max()
        rgb = np.repeat((np.clip(d, 0, 1) * 255).astype(np.uint8)[..., None],
                        3, axis=2)
        cx = P.Axes(img, box, (-1.0, 1.0), (-1.0, 1.0),
                    xlabel='gnomonic' if not tan else 'tangent-adjusted')
        cx.image(rgb)
        cx.frame()
    # Along the face's own boundary, from the edge midpoint to the corner. The
    # two maps run in OPPOSITE directions here, which is the whole finding:
    # gnomonic's minimum is the corner, the tangent map's is the edge midpoint,
    # so "centre to corner" bounds one of them and not the other.
    dx = P.Axes(img, (690, 400, 1130, 552), (0.0, 1.0), (0.45, 1.18),
                xlabel='along the face BOUNDARY, edge midpoint %s corner' % '→',
                ylabel='%s edge midpoint' % '÷')
    dx.frame(xticks=[0.0, 0.25, 0.5, 0.75, 1.0],
             yticks=[0.5, 0.75, 1.0], xfmt='%.2f', yfmt='%.2f')
    dx.hline(1.0, MUTED, width=1, dash=(2, 4))
    for tan, col, dash in ((False, INK, None), (True, BLU, (9, 5))):
        d = _cube_density(np.ones_like(t), t, tan)
        dx.line(t, d / d[0], col, width=3, dash=dash)
        dx.marker(1.0, float(d[-1] / d[0]), ACCENT, r=4)
    dx.text(0.97, 1.10, 'tangent: the corner is the BEST point', BLU,
            anchor='rs')
    dx.text(0.97, 0.50, 'gnomonic: the corner is the worst', INK, anchor='rs')
    return P.save(img, os.path.join(out, 'cube-sphere-distortion.png'))


# --- figure 10: a share with a ceiling, and a constant that cleared it -------
def _deck_split():
    """The horizontal deck's illuminant, split into the sky gradient and the
    Rayleigh aureole, both from `atmosphere.py`'s own environment and its own
    quadrature. `sky(lobes=())` is the gradient alone; the aureole is what
    `SKY_DIFFUSE_LOBES` adds to it. Nothing is re-integrated here."""
    d = (A.ENV_DX, A.ENV_DY, A.ENV_DZ)
    l_grad = A.sky(*d, lobes=())
    l_aur = A.sky(*d, lobes=A.SKY_DIFFUSE_LOBES) - l_grad
    return (A.env_irradiance(0., 0., 1., L=l_grad),
            A.env_irradiance(0., 0., 1., L=l_aur))


def fig_aureole_ceiling(out):
    """A bound, three points under it, and three points where nothing can be.

    The claim, from Rayleigh's phase function alone: with
    `P(Theta) = (3/4)(1 + cos^2 Theta)`, the forward `cos^2` half is the whole
    aureole and the isotropic half is the gradient, so the aureole's share of
    any receiver's illuminant is `m / (1 + m)` with `m = <cos^2 Theta>_w`.
    Because `cos^2` lies in [0, 1] so does `m`, and the share therefore cannot
    exceed **one half** -- for any optical depth, any solar elevation and any
    wavelength.

    A ceiling is exactly the kind of claim a number states badly and a picture
    states in one look: the curve simply stops rising, and the shipped hand
    constant `SUN_COL * 0.075` lands ABOVE it in all three bands, in a region
    of the axis that has no `m` behind it. Panel B is why it survived: the two
    hand terms are wrong in opposite directions, and the product crosses 1
    between green and blue."""
    img = P.canvas(1180, 640)
    e_grad, e_aur = _deck_split()
    e_tot = e_grad + e_aur
    share = e_aur / e_tot
    hand_aur = A.SUN_COL * 0.075
    hand_tot = A.SKY_AMB * 0.30 + hand_aur
    hand_share = hand_aur / hand_tot

    ax = P.Axes(img, (104, 54, 578, 520), (0.0, 4.0), (0.0, 0.9),
                xlabel='%scos%s%s%s, the receiver\'s weighted moment'
                       % ('⟨', '²', 'Θ', '⟩'),
                ylabel='the aureole\'s share of the illuminant')
    ax.frame(xticks=[0.0, 1.0, 2.0, 3.0, 4.0],
             yticks=[0.0, 0.25, 0.5, 0.75], xfmt='%.1f', yfmt='%.2f')
    m = _lin(0.0, 1.0, 801)
    ax.fill_between(m, np.zeros_like(m), m / (1.0 + m), FILL_A)
    ax.hline(0.5, ACCENT, width=2, dash=(7, 5))
    ax.vline(1.0, ACCENT, width=2, dash=(7, 5))
    mx = _lin(0.0, 4.0, 3201)
    ax.line(mx, mx / (1.0 + mx), MUTED, width=2, dash=(2, 6))
    ax.line(m, m / (1.0 + m), INK, width=3)
    ax.text(1.06, 0.83, 'no %scos%s%s%s beyond here' % ('⟨', '²', 'Θ', '⟩'),
            ACCENT)
    ax.text(3.94, 0.515, 'the ceiling, %s' % '½', ACCENT, anchor='rs')
    for c in (0, 1, 2):
        s = float(share[c])
        ax.marker(s / (1.0 - s), s, BAND[c], r=5)
        hs = float(hand_share[c])
        ax.marker(hs / (1.0 - hs), hs, BAND[c], r=5)
        ax.line([hs / (1.0 - hs)] * 2, [hs, s], BAND[c], width=1, dash=(2, 5))
    _legend(ax, [(BAND[c], BAND_DASH[c], '%s  derived %.1f%%,  shipped %.1f%%'
                  % (BAND_NAME[c], 100 * share[c], 100 * hand_share[c]))
                 for c in (0, 1, 2)], 1.30, 0.30)

    # The three ratios span 0.37 to 10.5, so the axis is log: on a linear one
    # the aureole term leaves the frame and the cancellation -- which is the
    # whole point of the panel -- stops being visible.
    bx = P.Axes(img, (688, 54, 1140, 520), (440.0, 640.0), (-0.62, 1.30),
                xlabel='band centre wavelength, nm',
                ylabel='shipped constant %s the same integral of this sky' % '÷')
    bx.frame(xticks=[460, 500, 545, 590, 620])
    _ticks(bx, None, None, [np.log10(v) for v in (0.3, 0.5, 1.0, 2.0, 5.0,
                                                  10.0)],
           ['0.3%s' % '×', '0.5%s' % '×', '1%s' % '×', '2%s' % '×',
            '5%s' % '×', '10%s' % '×'])
    lam = np.array([620.0, 545.0, 460.0])
    order = np.argsort(lam)
    bx.hline(0.0, INK, width=2, dash=(2, 4))
    bx.text(638.0, 0.03, 'the constant is right here', INK, anchor='rs')
    for vals, col, dash in (((A.SKY_AMB * 0.30) / e_grad, GRN, (9, 5)),
                            (hand_tot / e_tot, INK, None),
                            (hand_aur / e_aur, RED, (3, 4))):
        v = np.log10(np.asarray(vals, float))
        bx.line(lam[order], v[order], col, width=3, dash=dash)
        for c in (0, 1, 2):
            bx.marker(float(lam[c]), float(v[c]), col, r=4)
    _legend(bx, [(RED, (3, 4), 'the aureole term alone: 3.1%s to 10.5%s HIGH'
                  % ('×', '×')),
                 (GRN, (9, 5), 'the gradient term alone: 0.37%s to 0.42%s, LOW'
                  % ('×', '×')),
                 (INK, None, 'their SUM: 1.60%s red, 1.16%s green, 0.68%s blue'
                  % ('×', '×', '×'))], 446.0, 1.24)
    return P.save(img, os.path.join(out, 'aureole-ceiling.png'))


# --- figure 11: the receiver's own weight, and what it does to Fresnel -------
def _recv_weights(th):
    """The two normalised elevation weights `10` derives, as densities in the
    polar angle `theta` measured from the zenith.

    A horizontal receiver integrates `cos(theta)` over the whole azimuth: the
    density is `2 cos sin`. A vertical one sees half the azimuth and collects
    `cos(phi)` across it, which contributes 2, times `sin(theta)` for the
    cosine law and `sin(theta)` for the Jacobian: the density is
    `(4/pi) sin^2`. Both integrate to 1 over [0, pi/2] by construction, which
    is what makes them comparable at all, and their ratio against a uniform sky
    is the exact 1/2 `preflight` checks against `atmosphere.env_irradiance`."""
    th = np.asarray(th, float)
    return (2.0 * np.cos(th) * np.sin(th),
            (4.0 / np.pi) * np.sin(th) ** 2)


def fig_receiver_weights(out):
    """Why a vertical face sees three times the water a horizontal one does.

    The claim: "a horizontal receiver weights the sky by `cos theta sin theta`
    and a vertical one by `sin^2 theta`; the two agree at exactly 1/2 for a
    uniform sky". Read as levels those two facts sound like a small correction.
    Drawn, they are two densities of completely different shape that happen to
    enclose the same area -- one peaking at 45 degrees, the other still
    climbing when it runs out of sky.

    Panel B is the consequence, and it is the reason this belongs in a terrain
    chapter rather than a water one: the vertical weight peaks exactly where
    Fresnel does. The same interface, under the same sky, returns 0.0667 to a
    horizontal receiver and 0.2112 to a vertical one -- 3.17x, from the
    receiver's orientation alone, with nothing about the water changed."""
    img = P.canvas(1180, 640)
    th = _lin(0.0, np.pi / 2.0, 4001)
    deg = np.degrees(th)
    wh, wv = _recv_weights(th)

    ax = P.Axes(img, (104, 54, 578, 520), (0.0, 90.0), (0.0, 1.45),
                xlabel='polar angle %s from the zenith, %s' % ('θ', DEG),
                ylabel='weight density (each integrates to 1)')
    ax.frame(xticks=[0, 15, 30, 45, 60, 75, 90],
             yticks=[0.0, 0.4, 0.8, 1.2], yfmt='%.1f')
    ax.fill_between(deg, np.zeros_like(deg), wh, FILL_A)
    ax.line(deg, wh, INK, width=3)
    ax.line(deg, wv, BLU, width=3, dash=(9, 5))
    ax.vline(45.0, ACCENT, width=2, dash=(7, 5))
    ax.text(46.5, 1.02, 'peak at 45%s' % DEG, ACCENT)
    ax.text(88.0, 1.33, 'still climbing', BLU, anchor='rs')
    _legend(ax, [(INK, None, 'horizontal receiver:  2 cos%s sin%s' % ('θ', 'θ')),
                 (BLU, (9, 5), 'vertical receiver:  (4/%s) sin%s%s'
                  % ('π', '²', 'θ'))], 2.0, 1.39)

    # The axis belongs to the two INTEGRANDS, whose areas are the two means.
    # R itself climbs to 1 at grazing and would flatten them against the floor;
    # it is drawn at true scale and simply leaves the frame, which is a more
    # honest way to say "it goes to one" than rescaling everything else.
    bx = P.Axes(img, (688, 54, 1140, 520), (0.0, 90.0), (0.0, 0.50),
                xlabel='polar angle %s from the zenith, %s' % ('θ', DEG),
                ylabel='reflectance, and each weight\'s integrand')
    bx.frame(xticks=[0, 15, 30, 45, 60, 75, 90],
             yticks=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5], yfmt='%.1f')
    r = O.fresnel(np.cos(th))[:, 1]
    bx.fill_between(deg, np.zeros_like(deg), r * wv, FILL_B)
    bx.fill_between(deg, np.zeros_like(deg), r * wh, FILL_C)
    bx.line(deg, r, INK, width=2, dash=(2, 5))
    bx.line(deg, r * wv, BLU, width=3, dash=(9, 5))
    bx.line(deg, r * wh, GRN, width=3, dash=(3, 4))
    mh = float(np.trapezoid(r * wh, th))
    mv = float(np.trapezoid(r * wv, th))
    bx.marker(0.0, float(O.fresnel(np.array([1.0]))[0, 1]), ACCENT, r=5)
    bx.text(76.5, 0.455, 'R(%s) %s 1' % ('θ', '→'), INK, anchor='rs')
    bx.text(88.0, 0.055, 'normal incidence %.4f'
            % O.fresnel(np.array([1.0]))[0, 1], ACCENT, anchor='rs')
    _legend(bx, [(INK, (2, 5), 'R(%s), green band, n = %.4f' % ('θ', O.IOR[1])),
                 (BLU, (9, 5), 'vertical integrand:  area = %.4f' % mv),
                 (GRN, (3, 4), 'horizontal integrand:  area = %.4f' % mh),
                 (ACCENT, None, 'the ratio is %.2f%s, from the weight alone'
                  % (mv / mh, '×'))], 2.0, 0.475)
    return P.save(img, os.path.join(out, 'receiver-orientation-weights.png'))


# --- figure 12: an even function cannot know the afternoon -------------------
_SUN_B = (2026, 8, 12, 15, 28, 0.0, 1.0)     # `10`'s second worked sun


def _az_branches(decl, el, lat):
    """`10`'s two `acos` azimuth forms, evaluated from angles that
    `atmosphere.solar_position` returned. Both take the hour angle only through
    the elevation, and the elevation is even in it -- which is the entire
    content of the figure, so it is computed rather than asserted."""
    lat, d, h = np.radians(lat), np.radians(decl), np.radians(el)
    zen = np.pi / 2.0 - h
    a_n = np.degrees(np.arccos(np.clip(
        (np.sin(d) - np.sin(h) * np.sin(lat)) / (np.cos(h) * np.cos(lat)),
        -1.0, 1.0)))
    a_s = np.degrees(np.arccos(np.clip(
        (np.sin(lat) * np.cos(zen) - np.sin(d)) / (np.cos(lat) * np.sin(zen)),
        -1.0, 1.0)))
    return a_n, a_s


def fig_azimuth_fold(out):
    """The branch, the fold, and the check that keeps passing anyway.

    The claim: the azimuth is the one output of the solar chain with a branch
    in it; the two `acos` forms are each correct with their own afternoon rule;
    and crossing them "does not fail, it returns a plausible number" -- 306.05
    against a correct 233.95, 72 degrees wrong, with the elevation untouched.

    The mechanism is that `acos` of a quantity that depends on the hour angle
    only through `cos(ha)` is EVEN, so both forms fold about solar noon and
    neither can tell morning from afternoon. That fold is a shape, and it is
    what makes the bug look like a transcription slip rather than a branch
    error: the crossed value is the mirror of a true azimuth, so it is always
    a real compass bearing, just the wrong one. Panel B is the reason it
    survives review -- the elevation has no `acos` branch in it, so every check
    a reader is likely to run still passes at the wrong sun."""
    img = P.canvas(1180, 660)
    y, mo, d, _, _, s, tz = _SUN_B
    mins = np.arange(4 * 60, 21 * 60 + 1, 2.0)
    # The sweep runs past both horizons so the whole fold is in frame. Kasten &
    # Young's air-mass fit has no value below about -6 degrees and says so with
    # a NaN; nothing in this figure reads the air mass, so the warning is
    # silenced here rather than the sweep being trimmed to hide it.
    with np.errstate(invalid='ignore'):
        out_rows = [A.solar_position(A.SITE_LAT, A.SITE_LON, y, mo, d,
                                     int(t // 60), float(t % 60), s, tz)
                    for t in mins]
    el = np.array([r[0] for r in out_rows])
    az = np.array([r[2] for r in out_rows])
    decl = np.array([r[4] for r in out_rows])
    ha = np.array([r[6] for r in out_rows])
    up = el > 0.0
    a_n, a_s = _az_branches(decl, el, A.SITE_LAT)

    # the shoot itself, and the crossing, from the same routine
    el0, _, az0, _, dec0, _, ha0 = A.solar_position(A.SITE_LAT, A.SITE_LON,
                                                    *_SUN_B)
    an0, as0 = _az_branches(dec0, el0, A.SITE_LAT)
    crossed = 360.0 - as0
    h0 = np.radians(-0.833)
    latr, dr = np.radians(A.SITE_LAT), np.radians(dec0)
    a_rise = np.degrees(np.arccos(np.clip(
        (np.sin(dr) - np.sin(h0) * np.sin(latr))
        / (np.cos(h0) * np.cos(latr)), -1.0, 1.0)))

    ax = P.Axes(img, (104, 54, 1140, 392), (-120.0, 120.0), (40.0, 340.0),
                ylabel='azimuth, %s clockwise from north' % DEG)
    ax.frame(xticks=[-120, -90, -60, -30, 0, 30, 60, 90, 120],
             yticks=[90, 135, 180, 225, 270, 315])
    ax.band(-120.0, 0.0, (246, 244, 238))
    ax.fill_between(np.array([-120.0, 120.0]),
                    np.array([a_rise, a_rise]),
                    np.array([360.0 - a_rise, 360.0 - a_rise]), FILL_A)
    ax.hline(float(a_rise), MUTED, width=1, dash=(2, 4))
    ax.hline(360.0 - float(a_rise), MUTED, width=1, dash=(2, 4))
    ax.vline(0.0, ACCENT, width=2, dash=(7, 5))
    ax.line(ha[up], (360.0 - a_n)[up], RED, width=2, dash=(3, 4))
    ax.line(ha[up], a_n[up], BLU, width=2, dash=(2, 6))
    ax.line(ha[up], az[up], INK, width=3)
    ax.marker(float(ha0), float(az0), ACCENT, r=5)
    ax.marker(float(ha0), float(crossed), RED, r=5)
    ax.text(float(ha0) + 4.0, float(crossed) + 6.0,
            'crossed: %.2f%s' % (crossed, DEG), RED)
    ax.text(float(ha0) + 4.0, float(az0) - 22.0,
            'correct: %.2f%s' % (az0, DEG), ACCENT)
    ax.text(-116.0, 328.0, 'morning', MUTED)
    ax.text(116.0, 328.0, 'afternoon', MUTED, anchor='rs')
    ax.text(-116.0, 300.0,
            'each branch lies exactly ON atan2 in its own half of the day, '
            'and mirrors it in the other %s that is the fold' % '—', MUTED)
    ax.text(-116.0, 46.0,
            'shaded: the rise/set bracket (%.1f%s, %.1f%s) %s the crossed '
            'value is outside it, the correct one is not'
            % (a_rise, DEG, 360.0 - a_rise, DEG, '—'), MUTED)
    _legend(ax, [(INK, None, 'atan2 -- no branch, no fold'),
                 (BLU, (2, 6), 'A_N from acos: EVEN in the hour angle'),
                 (RED, (3, 4), '360 %s A_N: the other branch of the same fold'
                  % '−')], -116.0, 130.0)

    bx = P.Axes(img, (104, 462, 1140, 604), (-120.0, 120.0), (0.0, 72.0),
                xlabel='hour angle from local solar noon, %s (%s = 1 hour)'
                       % (DEG, '15' + DEG),
                ylabel='elevation, %s' % DEG)
    bx.frame(xticks=[-120, -90, -60, -30, 0, 30, 60, 90, 120],
             yticks=[0, 20, 40, 60])
    bx.band(-120.0, 0.0, (246, 244, 238))
    bx.vline(0.0, ACCENT, width=2, dash=(7, 5))
    bx.line(ha[up], el[up], INK, width=3)
    bx.marker(float(ha0), float(el0), ACCENT, r=5)
    bx.marker(-float(ha0), float(el0), RED, r=5)
    bx.text(-float(ha0) - 5.0, float(el0) - 1.0, 'the mirror hour', RED,
            anchor='rs')
    bx.text(-116.0, 64.0,
            'the same elevation at both %s which is why every check but the '
            'azimuth still passes at the wrong sun' % '—', MUTED)
    return P.save(img, os.path.join(out, 'azimuth-quadrant-fold.png'))


# --- figure 13: the Kelvin angle is a ratio, and the ratio is not always 1/2 --
def _kelvin_half_angle(r, n=200001):
    """The wake's half-angle for a general group-to-phase speed ratio `r`.

    A pattern held steady behind a source at speed `V` is made of waves whose
    phase speed matches the source's component along their own direction,
    `c = V cos(theta)`; their energy leaves the emission point at `c_g = r c`
    along the same direction, while the source has run on by `V t`. The
    disturbance from age `t` therefore sits at

        (x, y) = V t ( -1 + r cos^2(theta),  r cos(theta) sin(theta) )

    which is self-similar in `V t`: the WEDGE IS SCALE-FREE, and that is the
    whole of the chapter's "independent of speed". Its half-angle is the
    maximum over theta of `atan(y / -x)`, and it exists only while `r < 1`.
    `r` itself is never assumed here -- it is measured from `wake.py`."""
    r = float(r)
    if r >= 1.0:
        return float('nan'), float('nan')
    th = np.linspace(1e-9, np.pi / 2.0 - 1e-9, n)
    t = r * np.sin(th) * np.cos(th) / (1.0 - r * np.cos(th) ** 2)
    i = int(np.argmax(t))
    return float(np.degrees(np.arctan(t[i]))), float(np.degrees(th[i]))


def _cg_over_c(lam_m):
    """Group speed over phase speed, from `wake.py`'s own `sigma_w` and
    `c_group` -- one dispersion relation, both halves taken from it."""
    k = 2.0 * np.pi / np.asarray(lam_m, float)
    return W.c_group(k) / (W.sigma_w(k) / k)


def fig_kelvin_wake(out):
    """Why the angle is speed-free, and the band in which it is not 19.47.

    `19` states the Kelvin half-angle as `arcsin(1/3) ~= 19.47 deg` and gives
    the reason in one clause: "deep-water group velocity is half the phase
    velocity". That clause is the whole mechanism, and it says something the
    number does not -- the angle is a function of the RATIO `c_g/c` and of
    nothing else, so it is speed-free because the ratio is, and it stops being
    19.47 wherever the ratio stops being 1/2.

    Panel A draws the construction at three speeds: the loci are three
    different sizes and the tangent from the origin is the SAME line, which is
    the speed-independence as a picture rather than as an assertion. Panels B
    and C take the ratio from `reference-impl/wake.py`'s capillary-gravity
    dispersion -- the pool's own -- and follow it down. `19` names shallow
    water and Froude 1 as the regimes where the pattern changes; below about
    10 cm the ratio climbs off 1/2 on deep water alone, the wedge WIDENS
    rather than narrowing, and at the capillary minimum `c_g = c` and there is
    no wedge at all. A jet wake in a swimming pool lives entirely inside that
    band, which is why `12`'s wake is not a Kelvin wedge."""
    img = P.canvas(1180, 620)
    r_grav = float(_cg_over_c(1.0e4))          # 10 km: the gravity limit
    a_grav, th_grav = _kelvin_half_angle(r_grav)

    # ISOMETRIC, deliberately: the panel is an ANGLE, so a pixel must be the
    # same length across the track as along it. The y range is therefore set
    # from the box's own aspect rather than chosen, and the vertical slack that
    # leaves is where the annotation goes.
    box = (94, 54, 500, 500)
    xr = (-1.10, 0.06)
    half = 0.5 * (xr[1] - xr[0]) * (box[3] - box[1]) / (box[2] - box[0])
    ax = P.Axes(img, box, xr, (-half, half),
                xlabel='along the track, in units of V t (source at 0)',
                ylabel='across the track, same units')
    ax.frame(xticks=[-1.0, -0.75, -0.5, -0.25, 0.0],
             yticks=[-0.5, -0.25, 0.0, 0.25, 0.5], xfmt='%.2f', yfmt='%.2f')
    th = _lin(1e-6, np.pi / 2.0 - 1e-6, 2001)
    ta = np.tan(np.radians(a_grav))
    xw = np.array([xr[0], 0.0])
    ax.fill_between(xw, xw * ta, -xw * ta, FILL_A)
    for age, col, dash in ((1.0, INK, None), (0.62, BLU, (9, 5)),
                           (0.32, GRN, (3, 4))):
        x = age * (-1.0 + r_grav * np.cos(th) ** 2)
        y = age * (r_grav * np.cos(th) * np.sin(th))
        ax.line(x, y, col, width=3, dash=dash)
        ax.line(x, -y, col, width=3, dash=dash)
    ax.line([xr[0], 0.0], [-xr[0] * ta, 0.0], ACCENT, width=2, dash=(7, 5))
    ax.line([xr[0], 0.0], [xr[0] * ta, 0.0], ACCENT, width=2, dash=(7, 5))
    ax.marker(0.0, 0.0, ACCENT, r=5)
    ax.text(0.03, 0.52, '%.3f%s = arcsin(1/3)' % (a_grav, DEG), ACCENT,
            anchor='rs')
    ax.text(0.03, 0.44, 'ONE tangent line for all three', ACCENT, anchor='rs')
    _legend(ax, [(INK, None, 'the locus at one age V t'),
                 (BLU, (9, 5), 'the same, 0.62 V t'),
                 (GRN, (3, 4), 'the same, 0.32 V t')], -1.06, -0.40)

    lam = 10.0 ** _lin(-3.0, 2.0, 601)
    rr = _cg_over_c(lam)
    lam_min = float(2.0 * np.pi / np.sqrt(W.RHO * W.G / W.SIG))

    bx = P.Axes(img, (592, 54, 852, 500), (-3.0, 2.0), (0.3, 1.6),
                xlabel='wavelength', ylabel='c_g / c, from wake.py')
    bx.frame(yticks=[0.5, 0.75, 1.0, 1.25, 1.5], yfmt='%.2f')
    _ticks(bx, [-3, -2, -1, 0, 1, 2],
           ['1 mm', '1 cm', '10 cm', '1 m', '10 m', '100 m'])
    bx.hline(0.5, ACCENT, width=2, dash=(7, 5))
    bx.hline(1.0, RED, width=2, dash=(2, 6))
    bx.vline(float(np.log10(lam_min)), MUTED, width=1, dash=(2, 6))
    bx.line(np.log10(lam), rr, INK, width=3)
    bx.text(1.95, 0.53, 'the gravity limit, %s' % '½', ACCENT, anchor='rs')
    bx.text(-2.9, 1.05, 'c_g = c: no wedge', RED)

    ang = np.array([_kelvin_half_angle(float(v), 40001)[0] for v in rr])
    cx = P.Axes(img, (944, 54, 1140, 500), (-3.0, 2.0), (0.0, 60.0),
                xlabel='wavelength', ylabel='wake half-angle, %s' % DEG)
    cx.frame(yticks=[0, 15, 30, 45, 60])
    _ticks(cx, [-3, -2, -1, 0, 1, 2],
           ['1 mm', '1 cm', '10 cm', '1 m', '10 m', '100 m'])
    cx.hline(a_grav, ACCENT, width=2, dash=(7, 5))
    cx.vline(float(np.log10(lam_min)), MUTED, width=1, dash=(2, 6))
    cx.line(np.log10(lam), ang, INK, width=3)
    cx.text(1.9, a_grav + 2.0, '%.2f%s' % (a_grav, DEG), ACCENT, anchor='rs')
    cx.text(float(np.log10(lam_min)) - 0.15, 50.0,
            '%.1f mm' % (1000.0 * lam_min), MUTED, anchor='rs')
    return P.save(img, os.path.join(out, 'kelvin-wake-angle.png'))


FIGURES = (fig_two_sides, fig_factorisation, fig_trapped_series,
           fig_runup, fig_sommerfeld, fig_glitter_path,
           fig_float_binades, fig_depth_precision, fig_cube_sphere,
           fig_aureole_ceiling, fig_receiver_weights, fig_azimuth_fold,
           fig_kelvin_wake)


# --- the guard's own guard ---------------------------------------------------
def selftest():
    """`--selftest`: fire `preflight()` at deliberately broken inputs.

    Standing ruling 14 with the sign flipped -- a near-zero measurement is
    worthless until zero has been shown to be reachable, and a guard that has
    never been seen to fail is not known to be a guard. Each case below
    perturbs ONE quantity `preflight` reads, at roughly the size of a real
    regression, and the run fails if any of them slips through. Every module is
    restored afterwards; nothing is written to disk."""
    cases, saved = [], {}

    def case(name, apply, undo):
        apply()
        try:
            preflight()
            r = 'DID NOT FIRE  <-- blind'
        except SystemExit:
            r = 'fired'
        undo()
        cases.append((name, r))

    preflight()                                   # must pass clean first
    saved['R_INT'] = O.R_INT.copy()
    case('R_INT +0.1%',
         lambda: setattr(O, 'R_INT', saved['R_INT'] * 1.001),
         lambda: setattr(O, 'R_INT', saved['R_INT']))
    saved['R_INT_MU'] = O.R_INT_MU.copy()
    case('the TIR branch softened to 0.99',
         lambda: setattr(O, 'R_INT_MU',
                         np.where(saved['R_INT_MU'] >= 1.0, 0.99,
                                  saved['R_INT_MU'])),
         lambda: setattr(O, 'R_INT_MU', saved['R_INT_MU']))
    saved['ABS'] = O.ABS.copy()
    case('ABS red +2%',
         lambda: setattr(O, 'ABS', saved['ABS'] * np.array([1.02, 1.0, 1.0])),
         lambda: setattr(O, 'ABS', saved['ABS']))
    saved['IOR'] = O.IOR.copy()
    case('IOR green 1.3348 -> 1.3330',
         lambda: setattr(O, 'IOR', np.array([1.3320, 1.3330, 1.3400])),
         lambda: setattr(O, 'IOR', saved['IOR']))
    saved['kd'] = BD.knife_edge_kd
    case('K_d scaled by 1.0002',
         lambda: setattr(BD, 'knife_edge_kd',
                         lambda v: saved['kd'](v) * 1.0002),
         lambda: setattr(BD, 'knife_edge_kd', saved['kd']))
    case("Hunt's R read as the rms (the waves 4-11 bug)",
         lambda: setattr(B, 'RUNUP_QUANTILE', float(np.exp(-1.0))),
         lambda: setattr(B, 'RUNUP_QUANTILE', 0.02))

    # ---- the `09`, `10` and `19` guards, perturbed the way they would break --
    _g = globals()
    saved['spacing'] = _g['_f32_spacing']
    case('the spacing replaced by the chapter\'s own rule x*2^-23',
         lambda: _g.__setitem__('_f32_spacing', lambda x: np.asarray(x, float)
                                * 2.0 ** -23),
         lambda: _g.__setitem__('_f32_spacing', saved['spacing']))
    saved['spacing2'] = _g['_f32_spacing']
    case('the spacing rounded to float64 instead of float32',
         lambda: _g.__setitem__('_f32_spacing',
                                lambda x: np.spacing(np.asarray(x, float))),
         lambda: _g.__setitem__('_f32_spacing', saved['spacing2']))
    saved['cube'] = _g['_cube_density']
    case('the tangent adjustment silently dropped',
         lambda: _g.__setitem__('_cube_density',
                                lambda u, v, tangent: saved['cube'](u, v,
                                                                    False)),
         lambda: _g.__setitem__('_cube_density', saved['cube']))
    case('the tangent exponent u\' = tan(u pi/4) softened to u pi/4',
         lambda: _g.__setitem__(
             '_cube_density',
             lambda u, v, tangent: (
                 np.ones_like(np.asarray(u, float) * np.asarray(v, float))
                 * (np.pi / 4.0) ** 2
                 / (1.0 + (np.asarray(u, float) * np.pi / 4.0) ** 2
                    + (np.asarray(v, float) * np.pi / 4.0) ** 2) ** 1.5
                 if tangent else saved['cube'](u, v, False))),
         lambda: _g.__setitem__('_cube_density', saved['cube']))
    saved['SKY_TOP'] = A.SKY_TOP.copy()
    case('the sky gradient\'s zenith moved 2%',
         lambda: setattr(A, 'SKY_TOP', saved['SKY_TOP'] * 1.02),
         lambda: setattr(A, 'SKY_TOP', saved['SKY_TOP']))
    saved['SKY_AMB'] = A.SKY_AMB.copy()
    case('SKY_AMB raised until the shipped share clears the ceiling',
         lambda: setattr(A, 'SKY_AMB', A.SUN_COL.copy()),
         lambda: setattr(A, 'SKY_AMB', saved['SKY_AMB']))
    saved['recv'] = _g['_recv_weights']
    case('the vertical weight left un-normalised (no 4/pi)',
         lambda: _g.__setitem__('_recv_weights',
                                lambda t: (saved['recv'](t)[0],
                                           np.sin(np.asarray(t, float)) ** 2)),
         lambda: _g.__setitem__('_recv_weights', saved['recv']))
    saved['solpos'] = A.solar_position
    case('the azimuth returned on its morning branch all day',
         lambda: setattr(A, 'solar_position',
                         lambda *a, **k: (lambda r: (r[0], r[1],
                                                     360.0 - r[2]) + r[3:])(
                             saved['solpos'](*a, **k))),
         lambda: setattr(A, 'solar_position', saved['solpos']))
    saved['cg'] = W.c_group
    case('c_group taken in the gravity limit (wake.py\'s own warning)',
         lambda: setattr(W, 'c_group',
                         lambda k: 0.5 * np.sqrt(W.G / np.asarray(k, float))),
         lambda: setattr(W, 'c_group', saved['cg']))

    for n, r in cases:
        print('%-46s %s' % (n, r))
    blind = [n for n, r in cases if 'DID NOT' in r]
    print('%d/%d perturbations caught' % (len(cases) - len(blind), len(cases)))
    preflight()                                   # and clean again afterwards
    return 1 if blind else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    out = argv[1] if len(argv) > 1 else _HERE
    os.makedirs(out, exist_ok=True)
    preflight()
    for fn in FIGURES:
        print(fn(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
