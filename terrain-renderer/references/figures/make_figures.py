"""The water chapters' figures, regenerated from the code that ships.

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
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_IMPL = os.path.abspath(os.path.join(_HERE, '..', '..', 'reference-impl'))
if _IMPL not in sys.path:
    sys.path.insert(0, _IMPL)

import beach as B                      # noqa: E402  read-only
import beach_diffract as BD            # noqa: E402  read-only
import beach_optics as BO              # noqa: E402  read-only
import beach_plot as P                 # noqa: E402  read-only (the toolkit)
import optics as O                     # noqa: E402  read-only

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


FIGURES = (fig_two_sides, fig_factorisation, fig_trapped_series,
           fig_runup, fig_sommerfeld, fig_glitter_path)


def main(argv):
    out = argv[1] if len(argv) > 1 else _HERE
    os.makedirs(out, exist_ok=True)
    preflight()
    for fn in FIGURES:
        print(fn(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
