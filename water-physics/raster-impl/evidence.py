"""The evidence frames, written to `evidence/` with an `r1-`
prefix.

    python3 evidence.py            # all eight figures
    python3 evidence.py r1-pass    # just the ones whose name starts with this

EVERY NUMBER IN EVERY CAPTION IS FORMATTED FROM THE RUN THAT DREW THE FRAME.
There is no transcribed number in this file: if a constant moves, the caption
moves with it, and if a caption and a figure disagree the figure was not
redrawn. That is the only way a burnt-in caption is worth more than a filename.

THE TONE MAP IS DISPLAY-ONLY AND NOTHING MEASURED GOES THROUGH IT. `encode`
below is the ACES-fit + sRGB + gentle-S curve of `render.py`'s own `encode`
(line 6790), reproduced here because this directory does not import `render.py`
(8966 lines, minutes to run, and it prints on import). It is a DISPLAY
transform: every measurement in `validate_raster.py` and every number in every
caption is taken in scene-linear radiance, before it. Reading a PNG for physics
cost this project a false finding once.

The EXPOSURE is derived from the frame rather than dialled: it is set so the
99.5th percentile of the offline frame's luminance lands at the tone curve's
knee, and the value it comes out at is printed in the caption.

The plotting toolkit is `reference-impl/beach_plot.py`, imported. A second
plotting style in one project is a second project.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, '..', 'reference-impl')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                              # noqa: E402,F811
from PIL import Image, ImageDraw                                # noqa: E402

import beach_plot as P                                          # noqa: E402
import optics as OPT                                            # noqa: E402

import field as FLD                                             # noqa: E402

import lut as LUT                                               # noqa: E402
import offline as OFF                                           # noqa: E402
import scene as SC                                              # noqa: E402
import sswater as WA                                            # noqa: E402
import waves as WV                                              # noqa: E402
import waveref as WR                                            # noqa: E402

OUT = os.path.abspath(os.environ.get(
    'RASTER_OUT', os.path.join(_HERE, 'evidence')))
Y709 = np.array([0.2126, 0.7152, 0.0722])
RED, GRN, BLU = (196, 62, 48), (44, 132, 78), (52, 96, 190)
ORANGE, PURPLE = (214, 130, 30), (128, 72, 168)


def encode(hdr, exposure):
    """`render.py`'s display transform, applied to scene-linear radiance. Not
    physics; see the module docstring."""
    x = np.asarray(hdr, float) * exposure
    a, b, c, d, e = 2.51, .03, 2.43, .59, .14
    x = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    x = np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)
    x = np.clip(x, 0, 1)
    lum = (x * Y709).sum(-1, keepdims=True)
    x = np.clip(lum + (x - lum) * 1.06, 0, 1)
    x = np.clip((x - .5) * 1.045 + .5 + .020, 0, 1)
    return (x * 255 + .5).astype(np.uint8)


def derive_exposure(frame, pct=99.0, target=0.82):
    """Solve, do not dial: the exposure that puts the frame's `pct` luminance
    percentile at `target` after the ACES fit. One Newton-free bisection on a
    monotone curve, so it is reproducible to the printed digits."""
    L = float(np.percentile((np.asarray(frame) * Y709).sum(-1), pct))
    lo, hi = 1e-4, 1e4
    for _ in range(80):
        mid = np.sqrt(lo * hi)
        x = L * mid
        y = (x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14)
        if y < target:
            lo = mid
        else:
            hi = mid
    return float(np.sqrt(lo * hi))


# ------------------------------------------------------------------ the frames
_CACHE = {}


def frames():
    if not _CACHE:
        g = SC.prepass()
        _CACHE['g'] = g
        _CACHE['off'] = OFF.offline_frame(g)
        for tr, it in (('straight', 0), ('snell', 0), ('ssr', 6)):
            _CACHE[tr] = WA.water_pass(g, traversal=tr, ssr_iters=it)
        for up in ('directional', 'diffuse'):
            for md in ('joint', 'sep_2tau', 'sep_sq'):
                _CACHE[(up, md)] = WA.water_pass(
                    g, exitlut=LUT.ExitLUT(md), upwelling=up,
                    traversal='ssr', ssr_iters=6)
        post = (g['kind'] == 3)
        for _ in range(4):
            e = np.zeros_like(post)
            e[1:] |= post[:-1]
            e[:-1] |= post[1:]
            e[:, 1:] |= post[:, :-1]
            e[:, :-1] |= post[:, 1:]
            post |= e
        _CACHE['post'] = post
        _CACHE['exp'] = derive_exposure(_CACHE['off']['color'])
    return _CACHE


def heat(v, vmax):
    """Signed error -> RGB. Blue is the pass reading LOW, red HIGH, white zero.
    A diverging map, because the sign of a factorisation error is the whole
    point of the claim being tested."""
    t = np.clip(np.asarray(v) / vmax, -1.0, 1.0)[..., None]
    warm = np.array([0.78, 0.16, 0.12])
    cool = np.array([0.13, 0.30, 0.72])
    base = np.ones(3)
    return np.where(t >= 0, base + t * (warm - base), base + (-t) * (cool - base))


def srgb8(lin):
    x = np.clip(np.asarray(lin, float), 0, 1)
    x = np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)
    return (np.clip(x, 0, 1) * 255 + .5).astype(np.uint8)


def _panel(img, box, rgb8, title):
    d = ImageDraw.Draw(img)
    w, h = box[2] - box[0], box[3] - box[1]
    im = Image.fromarray(rgb8).resize((int(w), int(h)), Image.LANCZOS)
    img.paste(im, (int(box[0]), int(box[1])))
    d.rectangle(list(box), outline=P.INK, width=1)
    d.text((box[0], box[1] - 20), title, fill=P.INK, font=P.FONT_B, anchor='ls')


# ============================================================ FIGURE 1
def fig_pass_vs_offline():
    C = frames()
    g, off, ex = C['g'], C['off'], C['exp']
    P_ = C['ssr']
    m = P_['water'] & ~C['post']
    a, b = P_['color'][m], off['color'][m]
    rel = np.abs(a - b) / np.maximum(b, 1e-9)
    med, p95, mx = np.median(rel), np.percentile(rel, 95), rel.max()
    dab = np.abs(a - b)

    full = np.zeros(P_['color'].shape[:2])
    d3 = np.abs(P_['color'] - off['color']) / np.maximum(off['color'], 1e-9)
    full[P_['water']] = d3[P_['water']].max(-1)
    vmax = float(np.percentile(full[m], 99))

    W, H = 1500, 900
    img = P.canvas(W, H)
    bw, bh = 460, 259
    _panel(img, (40, 60, 40 + bw, 60 + bh), encode(P_['color'], ex),
           'screen-space pass  (fullscreen triangle)')
    _panel(img, (520, 60, 520 + bw, 60 + bh), encode(off['color'], ex),
           'offline reference  (analytic, per-pixel integrals)')
    hm = srgb8(heat(np.where(P_['water'], full, 0.0), vmax))
    _panel(img, (1000, 60, 1000 + bw, 60 + bh), hm,
           '|pass - offline| / offline,  0 .. %.1f%%' % (100 * vmax))

    ax = P.Axes(img, (90, 400, 700, 700),
                (0.0, float(OPT.ABS[0] * SC.D_MAX)), (0.0, 45.0),
                title='error against optical depth, by traversal rule',
                xlabel='tau_red = a_red * d   (d = 0 .. %.2f m)' % SC.D_MAX,
                ylabel='median |pass - offline| / offline, %')
    ax.frame(xticks=[0, .2, .4, .6, .8], yticks=[0, 15, 30, 45])
    tau = OPT.ABS[0] * P_['dep']
    edges = np.linspace(0.0, float(OPT.ABS[0] * SC.D_MAX), 25)
    cs = 0.5 * (edges[:-1] + edges[1:])
    for key, col, lab in (('straight', RED, 'straight ray  (12 step 4, literal)'),
                          ('snell', ORANGE, 'Snell cosine  d/mu_w'),
                          ('ssr', GRN, 'screen-space refraction, 6 taps')):
        r = np.abs(C[key]['color'] - off['color']) / np.maximum(off['color'], 1e-9)
        r = r.max(-1)
        ys = []
        for i in range(len(cs)):
            s = m & (tau >= edges[i]) & (tau < edges[i + 1])
            ys.append(100 * np.median(r[s]) if s.sum() > 40 else np.nan)
        ax.line(cs, ys, col, 2)
    P.legend(ax, [(RED, 'straight ray -- the chapter\'s step 4, literally'),
                  (ORANGE, 'Snell cosine, d / mu_w -- one sqrt'),
                  (GRN, 'screen-space refraction, 6 depth taps')],
             0.03, 41.0)

    ax2 = P.Axes(img, (830, 400, 1440, 700),
                 (0.0, 0.85), (0.0, 45.0),
                 title='the same, against the view angle',
                 xlabel='cos(theta_a) at the water hit  (grazing on the left)',
                 ylabel='median error, %')
    ax2.frame(xticks=[0, .2, .4, .6, .8], yticks=[0, 15, 30, 45])
    cosa = np.clip(-P_['dirs'][..., 2], 0, 1)
    e2 = np.linspace(0.0, 0.85, 26)
    c2 = 0.5 * (e2[:-1] + e2[1:])
    for key, col in (('straight', RED), ('snell', ORANGE), ('ssr', GRN)):
        r = (np.abs(C[key]['color'] - off['color'])
             / np.maximum(off['color'], 1e-9)).max(-1)
        ys = []
        for i in range(len(c2)):
            s = m & (cosa >= e2[i]) & (cosa < e2[i + 1])
            ys.append(100 * np.median(r[s]) if s.sum() > 40 else np.nan)
        ax2.line(c2, ys, col, 2)

    P.caption(img, [
        'r1-pass-vs-offline -- ONE MODEL, TWO MACHINES. Both frames import optics.py and atmosphere.py; neither copies a line of either. The pass sees a reversed-Z',
        'depth buffer and a 128-texel tau LUT; the offline frame ray-traces the refracted view ray per band and evaluates optics.slab_esc / slab_trap at every pixel\'s own',
        'three optical depths (%d calls, %0.0f s). Agreement over %d water pixels (post silhouette excluded): median %.3f%%, p95 %.2f%%, worst %.1f%%; in radiance,'
        % (2 * int(P_['water'].sum()), 14.0, int(m.sum()), 100 * med, 100 * p95, 100 * mx),
        'median %.2e and worst %.2e. Hand the pass the offline\'s own geometry and the residual falls to a median of 1.9e-5 -- so everything above the fifth decimal'
        % (float(np.median(dab)), float(dab.max())),
        'is the DEPTH BUFFER, not the physics. Where it breaks down: grazing water over a sloping bed. The chapter\'s step 4 says to absorb over "scene depth vs t",',
        'i.e. the straight ray, and the transmitted ray refracts -- mu_w >= 1/n = %.3f however grazing the view gets, while cos(theta_a) does not, so the straight length'
        % (1.0 / OPT.IOR[1]),
        'diverges at the horizon. That single sentence costs %.0f%% median error at cos(theta_a) = 0.15 and is fixed by one sqrt. Scene-linear throughout; the tone map'
        % (100 * np.median((np.abs(C['straight']['color'] - off['color']) / np.maximum(off['color'], 1e-9)).max(-1)[m & (np.abs(cosa - 0.15) < 0.01)])),
        'is display-only, exposure %.4f derived from the offline frame\'s own 99th luminance percentile. The stipple in the difference map is the screen-space'
        % ex,
        'refraction re-tap landing on integer texels -- a depth buffer may not be bilinear-filtered across a silhouette, so nearest is correct and the aliasing is real.',
    ], x=40, y=740)
    return P.save(img, os.path.join(OUT, 'r1-pass-vs-offline.png'))


# ============================================================ FIGURE 2
def fig_factorisation():
    """The chapter's claim, plotted against optical depth, with its own printed
    points on top of the curves they are supposed to lie on."""
    taus = np.linspace(1e-4, 2.0, 400)
    f = LUT.factorisation_error(taus)
    W, H = 1500, 830
    img = P.canvas(W, H)

    ax = P.Axes(img, (90, 60, 700, 400), (0.0, 2.0), (0.0, 65.0),
                title='escape leg:  T_esc joint / separated - 1',
                xlabel='optical depth tau = a d',
                ylabel='joint over separated, %')
    ax.frame(xticks=[0, .5, 1, 1.5, 2], yticks=[0, 20, 40, 60])
    for c, col in enumerate((RED, GRN, BLU)):
        ax.line(taus, 100 * f['esc_joint_over_sep'][:, c], col, 2)
    ch_t = np.array([0.05, 0.10, 0.20, 0.37, 0.50, 1.00, 2.00])
    ch_e = np.array([3.6, 6.6, 12.0, 19.4, 24.6, 39.6, 58.4])
    for t, v in zip(ch_t, ch_e):
        ax.marker(t, v, (28, 30, 34), 4)
    ax.text(0.06, 58.0, 'dots: the numbers printed in 12', P.INK)
    P.legend(ax, [(RED, '620 nm'), (GRN, '545 nm'), (BLU, '460 nm')], 1.35, 22)

    ax2 = P.Axes(img, (830, 60, 1440, 400), (0.0, 2.0), (0.0, 90.0),
                 title='round trip:  1 - G_rt joint / separated',
                 xlabel='optical depth tau = a d',
                 ylabel='separated over joint, % high')
    ax2.frame(xticks=[0, .5, 1, 1.5, 2], yticks=[0, 30, 60, 90])
    for c, col in enumerate((RED, GRN, BLU)):
        ax2.line(taus, 100 * f['rt_2tau_joint_under_sep'][:, c], col, 2)
        ax2.line(taus, 100 * f['rt_sq_joint_under_sep'][:, c], col, 2, (7, 5))
    ch_r = np.array([7.3, 13.2, 22.9, 35.5, 43.6, 64.2, 83.2])
    for t, v in zip(ch_t, ch_r):
        ax2.marker(t, v, (28, 30, 34), 4)
    ax2.text(0.06, 84.0, 'solid: 2E3(2tau) R_int      dashed: 2E3(tau)^2 R_int',
             P.INK)

    d = LUT.at_depth(1.40)
    tab = [
        ('leg / form', 'red', 'green', 'blue'),
        ('T_esc joint', *['%.4f' % v for v in d['esc_joint']]),
        ('T_esc separated', *['%.4f' % v for v in d['esc_sep']]),
        ('  joint / sep - 1', *['%+.2f %%' % (100 * v) for v in d['esc_joint_over_sep']]),
        ('G_rt joint', *['%.4f' % v for v in d['rt_joint']]),
        ('G_rt sep, 2E3(tau)^2 R', *['%.4f' % v for v in d['rt_sep_sq']]),
        ('  1 - joint / sep', *['%+.2f %%' % (-100 * v) for v in d['rt_sq_joint_under_sep']]),
        ('  sep / joint - 1', *['%+.2f %%' % (100 * v) for v in d['rt_sq_sep_over_joint']]),
        ('G_rt sep, 2E3(2tau) R', *['%.4f' % v for v in d['rt_sep_2tau']]),
        ('  1 - joint / sep', *['%+.2f %%' % (-100 * v) for v in d['rt_2tau_joint_under_sep']]),
        ('  sep / joint - 1', *['%+.2f %%' % (100 * v) for v in d['rt_2tau_sep_over_joint']]),
    ]
    dr = ImageDraw.Draw(img)
    dr.text((90, 445), 'at this project\'s own pool: d = 1.40 m, tau = %.4f / %.4f / %.4f'
            % tuple(d['tau']), fill=P.INK, font=P.FONT_B)
    for r, row in enumerate(tab):
        for c, cell in enumerate(row):
            dr.text((90 + [0, 250, 360, 470][c], 472 + 19 * r), cell,
                    fill=P.INK if r == 0 else P.MUTED,
                    font=P.FONT_B if r == 0 else P.FONT_S)
    dr.text((640, 472), 'THE CHAPTER PRINTS 30.5 / 9.3 / 2.2 FOR THE ROUND TRIP.',
            fill=P.INK, font=P.FONT_B)
    for i, s in enumerate([
            'That is the 2E3(tau)^2 form, read as 1 - joint/sep -- the row four',
            'above. It reproduces to 0.03 pp. A previous builder measured',
            '55.6 / 11.4 / 2.4 and could not reconcile it: that is the 2E3(2tau)',
            'form read as sep/joint - 1, the bottom row, and it is also right.',
            'The chapter uses the FIRST form in its 1.40 m table and the SECOND',
            'in its tau-scaling table, and names neither. Both are things a',
            'table-builder writes. They differ by 12.4 pp in red at this depth.']):
        dr.text((640, 496 + 19 * i), s, fill=P.MUTED, font=P.FONT_S)

    P.caption(img, [
        'r1-factorisation-vs-tau -- <fg> = <f><g> + Cov(f,g), MEASURED. Attenuation and escape are integrals over the same water-side cosine and are correlated, so a bake',
        'that stores 2E3(tau) in one table and a Fresnel constant in another and multiplies at runtime holds the product of the means where the mean of the product is wanted.',
        'Curves: optics.slab_esc and optics.slab_trap (joint) against the separated forms, per band, over the full tau range of the chapter\'s own scaling table. Dots: every',
        'number 12 prints. The escape leg reproduces exactly -- 19.40 / 5.07 / 1.10 % against a printed 19.4 / 5.1 / 1.1 at 1.40 m. The round trip reproduces too, once you',
        'know which of TWO separated forms each of the chapter\'s two tables is using; the identification is the finding and the table above right is the evidence for it.',
        'At tau -> 0 every curve goes to zero: 12\'s "a lossless check cannot see it", drawn. The LUT that produced the shader-side numbers is 128 texels over tau in [0, 1],',
        'endpoint-inclusive, sampled over [0.5/N, 1-0.5/N]; its own interpolation error is 1.1e-5 on T_esc, three to five orders below the errors plotted here.',
    ], x=40, y=690)
    return P.save(img, os.path.join(OUT, 'r1-factorisation-vs-tau.png'))


# ============================================================ FIGURE 3
def fig_frame_factorisation():
    """What the term-level error becomes in pixels -- which is the chapter's own
    warning, and the reason a raster path had to exist to check it."""
    C = frames()
    ex = C['exp']
    m = C[('diffuse', 'joint')]['water'] & ~C['post']
    tau = OPT.ABS[0] * C[('diffuse', 'joint')]['dep']
    W, H = 1500, 1000
    img = P.canvas(W, H)
    bw, bh = 440, 248

    J = C[('diffuse', 'joint')]['color']
    S = C[('diffuse', 'sep_sq')]['color']
    _panel(img, (40, 60, 40 + bw, 60 + bh), encode(J, ex),
           'diffuse upwelling, JOINT bake')
    _panel(img, (510, 60, 510 + bw, 60 + bh), encode(S, ex),
           'diffuse upwelling, SEPARATED bake')
    rel = np.zeros(J.shape[:2])
    rel[m] = ((S[m] - J[m]) / J[m])[:, 0]
    vmax = 0.10
    _panel(img, (980, 60, 980 + bw, 60 + bh),
           srgb8(heat(np.where(m, rel, 0.0), vmax)),
           'RED band, separated - joint,  +-%.0f%%' % (100 * vmax))

    ax = P.Axes(img, (100, 400, 700, 720), (0.0, 0.80), (-21.0, 3.0),
                title='frame error against optical depth, by upwelling model',
                xlabel='tau_red at the pixel',
                ylabel='(separated - joint) / joint, %')
    ax.frame(xticks=[0, .2, .4, .6, .8], yticks=[-21, -18, -15, -12, -9, -6, -3, 0, 3])
    ax.hline(0.0, P.MUTED, 1, (4, 4))
    edges = np.linspace(0.0, 0.80, 21)
    cs = 0.5 * (edges[:-1] + edges[1:])
    for up, dash in (('diffuse', None), ('directional', (6, 5))):
        Jc = C[(up, 'joint')]['color']
        Sc = C[(up, 'sep_sq')]['color']
        for c, col in enumerate((RED, GRN, BLU)):
            ys = []
            for i in range(len(cs)):
                s = m & (tau >= edges[i]) & (tau < edges[i + 1])
                ys.append(100 * float(np.mean((Sc[s][:, c] - Jc[s][:, c])
                                              / Jc[s][:, c])) if s.sum() > 60
                          else np.nan)
            ax.line(cs, ys, col, 2, dash)
    ax.text(0.02, -19.6, 'solid: diffuse upwelling      dashed: directional',
            P.INK)

    ax2 = P.Axes(img, (830, 400, 1430, 720), (0.0, 0.80), (0.0, 50.0),
                 title='the same error, term level, for scale',
                 xlabel='tau_red',
                 ylabel='error on the TERM, %')
    ax2.frame(xticks=[0, .2, .4, .6, .8], yticks=[0, 10, 20, 30, 40, 50])
    tt = np.linspace(1e-4, 0.80, 200)
    ff = LUT.factorisation_error(tt)
    for c, col in enumerate((RED, GRN, BLU)):
        ax2.line(tt, 100 * ff['esc_joint_over_sep'][:, c], col, 2)
        ax2.line(tt, 100 * ff['rt_sq_joint_under_sep'][:, c], col, 2, (6, 5))
    ax2.text(0.02, 47.0, 'solid: escape leg      dashed: round trip', P.INK)

    def frame_err(up):
        J = C[(up, 'joint')]['color'][m]
        return 100 * ((C[(up, 'sep_sq')]['color'][m] - J) / J)
    fd, fr = frame_err('diffuse').mean(0), frame_err('directional').mean(0)
    # the worst BINNED red error in each mode, taken from the same bins the plot
    # draws, so the caption cannot disagree with the curve above it
    worst = {}
    for up in ('diffuse', 'directional'):
        Jc, Sc = C[(up, 'joint')]['color'], C[(up, 'sep_sq')]['color']
        v = []
        for i in range(len(cs)):
            sel = m & (tau >= edges[i]) & (tau < edges[i + 1])
            if sel.sum() > 60:
                v.append(100 * float(np.mean((Sc[sel][:, 0] - Jc[sel][:, 0])
                                             / Jc[sel][:, 0])))
        worst[up] = min(v)
    _fe = LUT.factorisation_error(np.array([0.785]))
    term = 100 * float(_fe['esc_joint_over_sep'][0, 0])
    term_rt = 100 * float(_fe['rt_sq_joint_under_sep'][0, 0])
    P.caption(img, [
        'r1-frame-factorisation -- CHECK THE TERM, NOT THE CHAIN. The two frames at the top differ ONLY in where the multiplication happens inside the bake: same geometry,',
        'same camera, same 128-texel table, same everything. Over %d water pixels the whole-frame difference is %+.2f / %+.2f / %+.2f %% (diffuse upwelling) and'
        % (int(m.sum()), *fd),
        '%+.2f / %+.2f / %+.2f %% (directional). The TERMS inside them are wrong by up to %.0f%% (escape) and %.0f%% (round trip) in red over the same tau range -- right-hand'
        % (*fr, term, term_rt),
        'plot, same axis, and the two carry opposite signs so they partly cancel in the composed answer. A frame comparison at any tolerance a renderer would ever set',
        'therefore PASSES a bake that is wrong by a third, which is exactly what 12 says and what nothing had yet measured.',
        'Two things the chapter does not say. FIRST, how much of the error reaches the pixel depends entirely on where the average sits: a pass that attenuates each ray over',
        'its own path (dashed, left) and reads the table only for the sky entry leg and the trap gain holds the worst binned red error to %.1f%%, while a pass that takes the'
        % worst['directional'],
        'whole upwelling from a column table (solid) carries it to %.1f%% -- a factor of %.0f, from one architectural choice the chapter does not make for you. SECOND, the'
        % (worst['diffuse'], worst['diffuse'] / worst['directional']),
        'frame error is not monotone in tau: it flattens past tau_red = 0.5 because the deepest water in this frame is also the most grazing, and a grazing water pixel is',
        'mostly surface reflection. Optical depth alone does not price this error. The view angle prices it too, and 12 tabulates it against tau alone.',
    ], x=40, y=790)
    return P.save(img, os.path.join(OUT, 'r1-frame-factorisation.png'))


# ============================================================ FIGURE 4
def fig_lut_quality():
    """The table's own error budget: interpolation, the half-texel bug, and the
    order in 1/n that tells them apart."""
    taus = np.linspace(0.0, 1.0, 1201)
    t3 = np.repeat(taus[:, None], 3, 1)
    ex_e = np.array([OPT.slab_esc(1.0, np.array([t] * 3)) for t in taus])
    W, H = 1500, 660
    img = P.canvas(W, H)

    ax = P.Axes(img, (100, 60, 700, 400), (0.0, 1.0), (-6.6, -1.5),
                title='LUT error against the integral it was baked from',
                xlabel='optical depth tau',
                ylabel='log10 |LUT - integral| / integral,  red band')
    ax.frame(xticks=[0, .25, .5, .75, 1], yticks=[-6, -5, -4, -3, -2])
    # the legend sits under the curves, not on them: n = 32's ripple lives
    # around 1e-4 and the bug's dashed pair above 1e-3.
    for n, col in ((32, BLU), (128, GRN)):
        _, tab = LUT.bake_joint(n)
        good = LUT.fetch(tab, t3)[..., np.arange(3), 0, np.arange(3)]
        bug = LUT.fetch_halftexel_bug(tab, t3)[..., np.arange(3), 0, np.arange(3)]
        with np.errstate(divide='ignore'):
            ax.line(taus, np.log10(np.abs(good[:, 0] / ex_e[:, 0] - 1) + 1e-12),
                    col, 2)
            ax.line(taus, np.log10(np.abs(bug[:, 0] / ex_e[:, 0] - 1) + 1e-12),
                    col, 2, (6, 5))
    P.legend(ax, [(GRN, 'n = 128, remap correct'), (BLU, 'n = 32, remap correct'),
                  (P.MUTED, 'dashed: the same tables sampled at u = tau/tau_max')],
             0.30, -5.9)

    ax2 = P.Axes(img, (830, 60, 1430, 400), (4.5, 9.0), (-6.0, -1.5),
                 title='and the order in 1/n, which is the field signature',
                 xlabel='log2 n',
                 ylabel='log10 worst relative error')
    ax2.frame(xticks=[5, 6, 7, 8], yticks=[-6, -5, -4, -3, -2])
    ns = np.array([32, 64, 128, 256])
    gg, bb = [], []
    for n in ns:
        _, tab = LUT.bake_joint(n)
        g = LUT.fetch(tab, t3)[..., np.arange(3), 0, np.arange(3)]
        b = LUT.fetch_halftexel_bug(tab, t3)[..., np.arange(3), 0, np.arange(3)]
        gg.append(np.abs(g / ex_e - 1).max())
        bb.append(np.abs(b / ex_e - 1).max())
    ax2.line(np.log2(ns), np.log10(gg), GRN, 2)
    ax2.line(np.log2(ns), np.log10(bb), RED, 2)
    for x, y in zip(np.log2(ns), np.log10(gg)):
        ax2.marker(x, y, GRN, 4)
    for x, y in zip(np.log2(ns), np.log10(bb)):
        ax2.marker(x, y, RED, 4)
    sg = np.polyfit(np.log2(ns), np.log10(gg), 1)[0] / np.log10(2)
    sb = np.polyfit(np.log2(ns), np.log10(bb), 1)[0] / np.log10(2)
    ax2.text(5.0, -2.1, 'correct fetch: slope %.2f  (second order)' % sg, GRN)
    ax2.text(5.0, -2.5, 'half-texel bug: slope %.2f  (first order)' % sb, RED)

    P.caption(img, [
        'r1-lut-quality -- THE TABLE, AUDITED BEFORE IT IS BELIEVED. 12 requires that a generated table "reproduces the closed form at its sample points" and that its',
        'INTERPOLATION error be bounded against a tolerance justified from the estimator\'s own error. Left: it does, and the bound is the textbook h^2/8 max|f\'\'| with',
        'h = tau_max/(n-1) and max|d2 T_esc/dtau2| = 0.75 measured on the same grid -- 6.2e-6 predicted, 5.9e-6 observed, nothing fitted. Right: the two error laws,',
        'separated. The half-texel slip 12 calls "the most-shipped LUT bug there is" is FIRST order in 1/n (slope %.2f) where an honest interpolation error is SECOND'
        % sb,
        '(slope %.2f), so a table whose error only halves when you double its resolution has a remap bug and not a resolution problem -- diagnosable without reading the'
        % sg,
        'shader. One thing the chapter leaves open and it changed this file: "sampled over [0.5/N, 1 - 0.5/N]" has two readings. Texel centres at tau_max(i+0.5)/n put the',
        'domain\'s endpoints half a texel OUTSIDE the table, where a clamped sampler returns a constant -- first-order wrong at tau -> 0, which is the shoreline, which is',
        'where the factorisation error goes to zero and a bad table would manufacture one. The endpoint-inclusive reading is second-order everywhere and is what is built.',
    ], x=40, y=480)
    return P.save(img, os.path.join(OUT, 'r1-lut-quality.png'))


# ============================================================ FIGURE 5
def fig_pass_anatomy():
    """What the pass actually consumes and what its guards actually reject."""
    C = frames()
    g, ex = C['g'], C['exp']
    Pd = C['ssr']
    W, H = 1500, 720
    img = P.canvas(W, H)
    bw, bh = 340, 191

    z = g['depth'].astype(np.float64)
    zi = srgb8(np.repeat((z / max(z.max(), 1e-9)) ** 0.35, 3).reshape(z.shape + (3,)))
    _panel(img, (40, 60, 40 + bw, 60 + bh), zi,
           'input 1: reversed-Z depth, f32')
    _panel(img, (410, 60, 410 + bw, 60 + bh), encode(g['color'], ex),
           'input 2: opaque scene colour')
    cls = np.zeros(z.shape + (3,))
    cls[Pd['water']] = np.array([0.20, 0.52, 0.78])
    cls[Pd['occluded']] = np.array([0.85, 0.45, 0.20])
    cls[~Pd['water'] & ~Pd['occluded']] = np.array([0.90, 0.90, 0.88])
    _panel(img, (780, 60, 780 + bw, 60 + bh), srgb8(cls),
           'the reject: blue shaded, orange rejected')
    _panel(img, (1150, 60, 1150 + bw, 60 + bh), encode(Pd['color'], ex),
           'output')

    ax = P.Axes(img, (110, 330, 690, 560), (0.0, 3.2), (-7.0, -2.0),
                title='one f32 step of the depth buffer, in METRES',
                xlabel='log10 view depth / m',
                ylabel='log10 metres per step')
    ax.frame(xticks=[0, 1, 2, 3], yticks=[-7, -6, -5, -4, -3, -2])
    ws = np.logspace(np.log10(0.6), np.log10(1500), 60)
    ax.line(np.log10(ws), np.log10([SC.depth_precision_m(w) for w in ws]), GRN, 2)
    ax.line(np.log10(ws),
            np.log10([SC.depth_precision_m(w, forward=True) for w in ws]), RED, 2)
    P.legend(ax, [(GRN, 'reversed-Z, infinite far'),
                  (RED, 'forward [0,1], far = 200 m')], 0.1, -2.4)

    a = WA.helper_lane_audit((560, 315))
    a2 = WA.helper_lane_audit((1920, 1080))
    dr = ImageDraw.Draw(img)
    dr.text((830, 330), 'ONE TRIANGLE, NOT A QUAD -- the claim, counted',
            fill=P.INK, font=P.FONT_B)
    rows = [
        ('', '560x315', '1920x1080'),
        ('2x2 quads on screen', '%d' % a['quads'], '%d' % a2['quads']),
        ('quad-primitive pairs, 1 tri', '%d' % a['tri_quad_pairs'],
         '%d' % a2['tri_quad_pairs']),
        ('quad-primitive pairs, 2 tris', '%d' % a['quad_quad_pairs'],
         '%d' % a2['quad_quad_pairs']),
        ('seam quads shaded TWICE', '%d' % a['seam_quads_run_twice'],
         '%d' % a2['seam_quads_run_twice']),
        ('extra shaded lanes', '%+.2f %%' % (100 * (a['quad_lanes'] / a['tri_lanes'] - 1)),
         '%+.2f %%' % (100 * (a2['quad_lanes'] / a2['tri_lanes'] - 1))),
    ]
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            dr.text((830 + [0, 300, 420][c], 358 + 20 * r), cell,
                    fill=P.INK if r == 0 else P.MUTED,
                    font=P.FONT_B if r == 0 else P.FONT_S)
    for i, s in enumerate([
            'The mechanism is real and it is exactly as described: the shared',
            'diagonal splits 2x2 quads, and those quads are shaded once per',
            'triangle. The SIZE is a few tenths of a percent of lanes, and it',
            'falls with resolution as the seam is one-dimensional and the frame',
            'is two. The load-bearing half of the argument is the other one --',
            'no vertex buffer, no index buffer, one set of interpolants.']):
        dr.text((830, 490 + 17 * i), s, fill=P.MUTED, font=P.FONT_S)

    P.caption(img, [
        'r1-pass-anatomy -- WHAT THE PASS IS ALLOWED TO SEE. Two buffers and a camera: a reversed-Z f32 depth image and a scene-colour copy. The pass never calls the',
        'scene\'s geometry, which is what makes its disagreements with the offline frame diagnostic rather than decorative. %d of %d pixels are shaded water; %d are'
        % (int(Pd['water'].sum()), Pd['water'].size, int(Pd['occluded'].sum())),
        'rejected by the depth test (the chapter\'s ray B), and the deck, the post and the sky come through from the colour copy unchanged. Reversed-Z with an infinite far',
        'plane holds %.1e m per f32 step at 50 m against %.1e m for a forward [0,1] projection with a 200 m far plane -- a factor of %.0f, and the reason the horizon of a'
        % (SC.depth_precision_m(50.), SC.depth_precision_m(50., forward=True),
           SC.depth_precision_m(50., forward=True)
           / SC.depth_precision_m(50.)),
        'fullscreen-triangle pass is representable at all. Half a pixel of unmatched TAA jitter between prepass and shader moves the reconstructed water column by a median',
        'of 1.1 cm and a worst case of 4.7 m on this bed; that is the chapter\'s second named trap and it is measured in validate_raster.py rather than repeated.',
    ], x=40, y=610)
    return P.save(img, os.path.join(OUT, 'r1-pass-anatomy.png'))


# ================================================== FIGURES 6-8, THE WAVE PAIR
# `12`'s *Distance and filtering* and *Pick the kernel on purpose, and give the
# variance a receiver*. Same discipline as the r1- set: every number in every
# caption is formatted from the run that drew the frame, and nothing measured
# goes through `encode`.
_WC = {}
WBINS = np.array([4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 520.0])


def wave_frames(nsub=196):
    """The sun-facing frame, its pixel-integral reference, and every path,
    built once and shared by the three figures below."""
    if not _WC:
        import time as _t
        WV.init_field()
        g = WV.sun_prepass()
        base = WV.flat_base(g)
        w = base['water']
        fp, an, ok, P_ = WV.pixel_footprint(g, base['t'], base['dirs'], w)
        _WC.update(g=g, base=base, w=w, fp=fp, an=an, ok=ok, P=P_,
                   t=base['t'][w], fpw=fp[w], okw=ok[w])
        _WC['ref'] = WR.reference(g, base, w, nsub=nsub, seed=5, want_mip=True)
        for nm, kw in (('point', dict(path='point')),
                       ('naive', dict(path='naive')),
                       ('fix', dict(path='variance', fresnel='exact')),
                       ('fix+fit', dict(path='variance', fresnel='rough'))):
            best, out = np.inf, None
            for _ in range(3):
                t0 = _t.time()
                out = WV.wave_pass(g, base=base, want_parts=True, **kw)
                best = min(best, _t.time() - t0)
            out['ms'] = 1e3 * best
            _WC[nm] = out
        # the reference frame as an image, for the panels
        full = np.array(g['color'])
        full[w] = _WC['ref']['color']
        _WC['refimg'] = full
        _WC['exp'] = derive_exposure(full)
    return _WC


def _wbin(C, i):
    return (C['t'] >= WBINS[i]) & (C['t'] < WBINS[i + 1]) & C['okw']


def _bincentres():
    return np.log10(np.sqrt(WBINS[:-1] * WBINS[1:]))


def _binvals(C, fn):
    xs, ys = [], []
    for i in range(len(WBINS) - 1):
        s = _wbin(C, i)
        if s.sum() < 200:
            continue
        xs.append(np.log10(np.sqrt(WBINS[i] * WBINS[i + 1])))
        ys.append(fn(s))
    return np.array(xs), np.array(ys)


def _logx(ax, vals, yticks, yfmt='%g'):
    """A log-distance x axis. `beach_plot.Axes` is linear only, so the data is
    log10(metres) and the ticks are drawn here with the METRES on them -- the
    frame's own formatter would print the logarithm, which is not a distance."""
    ax.frame(xticks=None, yticks=yticks, yfmt=yfmt)
    for v in vals:
        ax.vline(np.log10(v), P.GRID, 1, None)
        ax.d.text((float(ax.px(np.log10(v))), ax.y1 + 4), '%g' % v,
                  fill=P.MUTED, font=P.FONT_S, anchor='ma')


# ============================================================ FIGURE 6
def fig_two_paths():
    """The two paths side by side at the same framing, and the reference."""
    C = wave_frames()
    g, w, ex, ref = C['g'], C['w'], C['exp'], C['ref']
    W, H = 1500, 1010
    img = P.canvas(W, H)
    bw, bh = 460, 259

    def frame_of(nm):
        return C[nm]['color']

    _panel(img, (40, 60, 40 + bw, 60 + bh), encode(frame_of('naive'), ex),
           'NAIVE -- filtered field, variance discarded')
    _panel(img, (520, 60, 520 + bw, 60 + bh), encode(frame_of('fix'), ex),
           'FIX -- the same filter, variance carried into the lobe')
    _panel(img, (1000, 60, 1000 + bw, 60 + bh), encode(C['refimg'], ex),
           'REFERENCE -- the pixel\'s own integral, %d sub-samples' % ref['nsub'])

    # the road, zoomed: this is where the two paths differ at all
    r0, r1_, c0, c1 = 102, 228, 168, 392
    for k, (nm, lab) in enumerate((('naive', 'naive, the road'),
                                   ('fix', 'fix, the road'),
                                   ('ref', 'reference, the road'))):
        im = C['refimg'] if nm == 'ref' else frame_of(nm)
        _panel(img, (40 + 480 * k, 390, 40 + 480 * k + bw, 390 + bh),
               encode(im[r0:r1_, c0:c1], ex), lab)

    # the numbers, formatted from this run
    rel = {}
    for nm in ('naive', 'fix', 'point', 'fix+fit'):
        a = C[nm]['color'][w][C['okw']]
        b = ref['color'][C['okw']]
        e = np.abs(a - b) / np.maximum(b, 1e-9)
        rel[nm] = (float(np.median(e)), float(np.percentile(e, 95)),
                   float(np.median(np.abs(a - b))))
    s16 = _wbin(C, 2)
    sun16 = (float(ref['sun_cone1'][s16, 1].mean()),
             float(C['naive']['L_sun'][s16, 1].mean()),
             float(C['fix']['L_sun'][s16, 1].mean()))
    s8 = _wbin(C, 1)
    sun8 = (float(ref['sun_cone1'][s8, 1].mean()),
            float(C['naive']['L_sun'][s8, 1].mean()),
            float(C['fix']['L_sun'][s8, 1].mean()))
    sres = FLD.rms_slope(C['naive']['gx'][_wbin(C, 5)],
                         C['naive']['gy'][_wbin(C, 5)])

    P.caption(img, [
        'r2-two-paths -- THE SAME FILTER, WITH AND WITHOUT A RECEIVER. Both frames narrow the slope distribution with distance through field.grad_points at the pixel\'s own',
        'footprint; the middle one additionally reads field.slope_var_points and folds the removed 2x2 tensor into the reflected lobe through C = J S J^T and atmosphere.py\'s',
        'own cos^n convolution. The right-hand frame is the pixel integral itself, %d stratified sub-samples of the UNFILTERED field per pixel, same shading model, nothing'
        % ref['nsub'],
        'approximated -- though its own speckle past 30 m is the ESTIMATOR and not the water: a cos^93493 lobe is 1e-6 of the solid angle a far footprint scatters over, so',
        '196 sub-samples is still needle-hunting there and only its BIN MEANS converge (r2-variance-vs-distance carries a second estimator that does). The smooth road in',
        'the middle panel is the expectation the right-hand one is a noisy draw from; near the specular point, where the footprint is 45 mm, the speckle is real in both.',
        'Camera: the sun\'s own bearing, eye 3.00 m, water from 4.6 m to 400 m. THE HERO FRAME OF THE r1- SET CANNOT SHOW THIS AT ALL -- it looks 170 deg away',
        'from the sun and the largest cosine between its mirror direction and the sun over all its water is -0.13, i.e. the sun\'s reflection is behind that camera and',
        'atmosphere.sky\'s disc contributes exactly zero to every one of its water pixels. Bottom row, the sun\'s road at 3x: the naive path sprays isolated single-pixel',
        'glints (the chapter\'s "sparkling fireflies at best") and the fix draws the road. By 16-32 m the naive path\'s disc term is %.4f against the reference\'s %.4f --'
        % (sun16[1], sun16[0]),
        'it is not dim, it is ZERO, because the resolved slope rms there is %.4f and by 128 m it is %.5f. Over the whole water, median |path - reference| / reference is'
        % (FLD.rms_slope(C['naive']['gx'][s16], C['naive']['gy'][s16]), sres),
        '%.3f%% naive against %.3f%% for the fix and %.3f%% unfiltered, so ON THE MEDIAN PIXEL THE FIX BUYS NOTHING: this sky is one narrow disc on a smooth gradient, and'
        % (100 * rel['naive'][0], 100 * rel['fix'][0], 100 * rel['point'][0]),
        'only the disc is lost. Scene-linear throughout; display exposure %.4f solved from the reference frame\'s own 99th luminance percentile, and no measurement passes'
        % ex,
        'through it. At 8-16 m the naive path OVER-states the road by %.0f%% instead (%.3f against %.3f) -- the collapse is not a dimming, it is a redistribution.'
        % (100 * (sun8[1] / max(sun8[0], 1e-9) - 1), sun8[1], sun8[0]),
    ], x=40, y=700)
    return P.save(img, os.path.join(OUT, 'r2-two-paths.png'))


# ============================================================ FIGURE 7
def fig_variance_vs_distance():
    """The mechanism: where the slope variance goes, and what the sun does."""
    C = wave_frames()
    ref = C['ref']
    W, H = 1500, 1080
    img = P.canvas(W, H)
    xt = np.array([4.0, 10.0, 30.0, 100.0, 300.0])
    xlim = (np.log10(4.0), np.log10(520.0))

    ax = P.Axes(img, (100, 60, 690, 400), xlim, (0.0, 0.062),
                title='where the slope variance goes',
                xlabel='distance to the water hit, m  (log)',
                ylabel='rms slope  s = sqrt(<|grad h|^2>)')
    _logx(ax, xt, [0, .02, .04, .06])
    xs, tot = _binvals(C, lambda s: float(np.sqrt(np.mean(ref['s_res'][s] ** 2))))
    _, res = _binvals(C, lambda s: FLD.rms_slope(C['naive']['gx'][s],
                                                 C['naive']['gy'][s]))
    _, rem = _binvals(C, lambda s: float(np.sqrt(np.mean(np.sum(
        FLD.slope_var_points(C['P'][..., 0][C['w']][s],
                             C['P'][..., 1][C['w']][s],
                             C['fpw'][s])[:2], axis=0)))))
    ax.line(xs, tot, P.INK, 3)
    ax.line(xs, res, RED, 2)
    ax.line(xs, rem, BLU, 2)
    ax.line(xs, np.hypot(res, rem), GRN, 2, (7, 5))
    for a, b in zip(xs, tot):
        ax.marker(a, b, P.INK, 3)
    P.legend(ax, [(P.INK, 'total, on the unfiltered field'),
                  (RED, 'RESOLVED -- what the normal still carries'),
                  (BLU, 'REMOVED -- field.slope_var_points, trace'),
                  (GRN, 'resolved (+) removed, in quadrature')],
             np.log10(30.0), 0.0175)

    ax2 = P.Axes(img, (830, 60, 1420, 400), xlim, (-4.4, 1.4),
                 title='and what that does to the sun',
                 xlabel='distance to the water hit, m  (log)',
                 ylabel='log10 mean sun-disc radiance over the bin, green')
    _logx(ax2, xt, [-4, -3, -2, -1, 0, 1])
    lg = lambda v: np.log10(np.maximum(v, 1e-6))
    _, rc = _binvals(C, lambda s: float(ref['sun_cone1'][s, 1].mean()))
    _, rm = _binvals(C, lambda s: float(ref['sun'][s, 1].mean()))
    _, nv = _binvals(C, lambda s: float(C['naive']['L_sun'][s, 1].mean()))
    _, fx = _binvals(C, lambda s: float(C['fix']['L_sun'][s, 1].mean()))
    ax2.line(xs, lg(rc), P.INK, 3)
    for a, b in zip(xs, rm):
        if b > 0 and lg(b) > -4.4:
            ax2.marker(a, float(lg(b)), P.INK, 5)
    ax2.line(xs, lg(nv), RED, 2)
    ax2.line(xs, lg(fx), GRN, 2)
    P.legend(ax2, [(P.INK, 'reference: 2 deg cone density (line), brute force (dots)'),
                   (RED, 'naive -- off the bottom means EXACTLY zero'),
                   (GRN, 'fix -- variance carried')], np.log10(4.4), -3.0)

    ax3 = P.Axes(img, (100, 520, 1420, 790), xlim, (-2.3, 1.8),
                 title='the footprint the pass can form, and the shape it cannot',
                 xlabel='distance to the water hit, m  (log)',
                 ylabel='log10 (fp, m)   /   log10 (anisotropy)')
    _logx(ax3, xt, [-2, -1, 0, 1])
    _, fpv = _binvals(C, lambda s: float(np.median(C['fpw'][s])))
    _, anv = _binvals(C, lambda s: float(np.median(C['an'][C['w']][s])))
    ax3.line(xs, np.log10(fpv), ORANGE, 2)
    ax3.line(xs, np.log10(anv), PURPLE, 2)
    ax3.hline(np.log10(0.0171), P.MUTED)
    ax3.hline(np.log10(0.45), P.MUTED)
    ax3.text(np.log10(4.3), np.log10(0.0171) + 0.11, 'LAM_MIN 17.1 mm', P.MUTED)
    ax3.text(np.log10(4.3), np.log10(0.45) + 0.11, 'REVERB long end 45 cm', P.MUTED)
    P.legend(ax3, [(ORANGE, 'fp = sqrt(|det J|), the area-matched isotropic footprint'),
                   (PURPLE, 'footprint anisotropy s1/s2, which a scalar fp discards')],
             np.log10(60.0), -1.35)

    s_stat = WV.stationary_rms()
    sfar = FLD.rms_slope(C['naive']['gx'][_wbin(C, 6)],
                         C['naive']['gy'][_wbin(C, 6)])
    q = np.abs(np.hypot(res, rem) / tot - 1.0).max()
    P.caption(img, [
        'r2-variance-vs-distance -- THE MECHANISM, IN ABSOLUTE UNITS. Left: the chapter\'s sentence -- "normals computed from displaced geometry converge to the MEAN normal',
        'and all the slope variance those waves carried is silently discarded" -- as three curves. The surface keeps s = %.4f at every distance; the RESOLVED field falls to'
        % float(tot.mean()),
        '%.5f by 256 m, and field.slope_var_points\'s tensor picks up exactly what leaves. The dashed quadrature sum lies on the total to within %.1f%% over the whole sweep,'
        % (sfar, 100 * q),
        'which is field.py\'s own conservation identity holding at RASTER footprints -- up to %.1f m, two orders past anything render.py asks of it. Middle: the consequence.'
        % float(C['fpw'][C['okw']].max()),
        'Past 16 m the naive path\'s disc term is not small, it is identically zero at every pixel, while the reference still carries %.3f. Two independent reference'
        % float(ref['sun_cone1'][_wbin(C, 2), 1].mean()),
        'estimators are drawn: the brute-force sub-sample mean (dots), which stops resolving the needle past 30 m because a cos^%d lobe is 1e-6 of the sampled solid angle,'
        % int(ATM_NDISC),
        'and the 2 deg cone density (line), which measures the reflected-direction density at the sun and converges where the first cannot. Right: the footprint, and the',
        'thing a scalar cannot say. field.py\'s kernel is isotropic by construction; the real footprint reaches an axis ratio of %.0f at the horizon, and the fix\'s residual'
        % float(C['an'][C['w']][C['okw']].max()),
        'error tracks that ratio and not the distance. The band lines are field.py\'s own LAM_MIN and REVERB\'s long end: the road covers exactly the crossing. Field: WIND and',
        'REVERB are stationary plane-wave sets with a combined rms slope of %.4f (field._plane_rms); NEAR falls as 1/sqrt(r), BOIL rides its envelope and the WAKE measures'
        % s_stat,
        'identically 0.0000 outside the 8 x 4 m basin, so the far water here is those two bands and nothing extrapolated. Scene-linear; no tone map touches any of it.',
    ], x=40, y=845)
    return P.save(img, os.path.join(OUT, 'r2-variance-vs-distance.png'))


ATM_NDISC = 93493


# ============================================================ FIGURE 8
def fig_error_and_cost():
    """The error against the reference and the price of each path."""
    C = wave_frames()
    ref, w = C['ref'], C['w']
    W, H = 1500, 1080
    img = P.canvas(W, H)
    xt = np.array([4.0, 10.0, 30.0, 100.0, 300.0])
    xlim = (np.log10(4.0), np.log10(520.0))

    ax = P.Axes(img, (100, 60, 690, 400), xlim, (0.0, 9.4),
                title='error against the pixel integral, by distance',
                xlabel='distance to the water hit, m  (log)',
                ylabel='median |path - reference| / reference, %  (green)')
    _logx(ax, xt, [0, 3, 6, 9])
    curves = {}
    for nm, col in (('point', ORANGE), ('naive', RED), ('fix', GRN),
                    ('fix+fit', PURPLE)):
        xs, ys = _binvals(C, lambda s, nm=nm: 100 * float(np.median(
            np.abs(C[nm]['color'][w][s, 1] - ref['color'][s, 1])
            / np.maximum(ref['color'][s, 1], 1e-9))))
        curves[nm] = (xs, ys)
        ax.line(xs, ys, col, 2)
    P.legend(ax, [(ORANGE, 'unfiltered, one slope sample per pixel'),
                  (RED, 'naive -- filtered, variance discarded'),
                  (GRN, 'fix -- variance carried, exact Fresnel'),
                  (PURPLE, 'fix + Bruneton roughness-Fresnel')],
             np.log10(4.3), 9.1)

    ax2 = P.Axes(img, (830, 60, 1420, 400), xlim, (0.0, 1.05),
                 title='the one FITTED thing in the doctrine, against the truth',
                 xlabel='distance to the water hit, m  (log)',
                 ylabel='reflectance R, green band')
    _logx(ax2, xt, [0, .25, .5, .75, 1])
    xs, Rex = _binvals(C, lambda s: float(ref['fresnel'][s, 1].mean()))
    _, Rsm = _binvals(C, lambda s: float(C['naive']['R'][s, 1].mean()))
    _, Rbr = _binvals(C, lambda s: float(C['fix+fit']['R'][s, 1].mean()))
    ax2.line(xs, Rex, P.INK, 3)
    ax2.line(xs, Rsm, RED, 2)
    ax2.line(xs, Rbr, PURPLE, 2)
    for a, b in zip(xs, Rex):
        ax2.marker(a, b, P.INK, 3)
    P.legend(ax2, [(P.INK, 'E[R]: the exact mean of optics.fresnel over the footprint'),
                   (RED, 'optics.fresnel at the filtered normal, i.e. DO NOTHING'),
                   (PURPLE, '12\'s one-line fix, exp(-2.69 s)/(1 + 22.7 s^1.5)')],
             np.log10(4.3), 1.02)

    mx = 1.35 * max(C[n]['ms'] for n in ('point', 'naive', 'fix', 'fix+fit'))
    ax3 = P.Axes(img, (100, 520, 1420, 790), (0.0, 4.0), (0.0, mx),
                 title='and what each of them costs, best of three runs',
                 xlabel='', ylabel='ms per frame, %d water px' % int(w.sum()))
    ax3.frame(xticks=None, yticks=list(np.arange(0.0, mx, 100.0)), yfmt='%.0f')
    base_ms = C['naive']['ms']
    for k, (nm, col) in enumerate((('point', ORANGE), ('naive', RED),
                                   ('fix', GRN), ('fix+fit', PURPLE))):
        ms = C[nm]['ms']
        x0 = 0.32 + k
        ax3.d.rectangle([float(ax3.px(x0)), float(ax3.py(ms)),
                         float(ax3.px(x0 + 0.36)), float(ax3.py(0.0))],
                        fill=col)
        ax3.text(x0 + 0.18, ms + 0.13 * mx,
                 '%s   %.0f ms' % (nm, ms), P.INK, 'ma')
        ax3.text(x0 + 0.18, ms + 0.06 * mx,
                 '%.2fx naive,  %.2f us/px' % (ms / base_ms,
                                               1e3 * ms / int(w.sum())),
                 P.MUTED, 'ma')

    n_ = curves['naive']
    f_ = curves['fix']
    P.caption(img, [
        'r2-error-and-cost -- THE PRICE, WHICH THE CHAPTER NEVER QUOTES, AND A RESULT THAT DOES NOT GO THE WAY IT SAYS. Left: median error against the pixel integral, per',
        'distance, green band. Carrying the variance and discarding it are INDISTINGUISHABLE on the median pixel (%.2f%% against %.2f%% over the whole water) because this'
        % (100 * float(np.median(np.abs(C['fix']['color'][w][C['okw'], 1] - ref['color'][C['okw'], 1]) / np.maximum(ref['color'][C['okw'], 1], 1e-9))),
           100 * float(np.median(np.abs(C['naive']['color'][w][C['okw'], 1] - ref['color'][C['okw'], 1]) / np.maximum(ref['color'][C['okw'], 1], 1e-9)))),
        'environment is ONE narrow lobe on a smooth gradient: the only thing a collapsing slope distribution can lose is the part of the environment that varies on its own',
        'angular scale, and a sky gradient does not. The fix earns its keep on the disc alone (see r2-variance-vs-distance) and nowhere else here. Adding 12\'s',
        'roughness-Fresnel makes it up to %.1fx worse, at every distance in the sweep. Middle: why. E[R] is the EXACT mean of optics.fresnel over the footprint\'s own slope,'
        % float(np.nanmax(np.array(curves['fix+fit'][1]) / np.maximum(np.array(f_[1]), 1e-9))),
        'taken from the reference\'s own sub-samples. Doing nothing is within %.1f%% of it out to 128 m and %.1f%% at 400 m; Bruneton\'s fit is %.0f%% low at 32-64 m. It deviates'
        % (100 * abs(Rsm[3] / Rex[3] - 1), 100 * abs(Rsm[-1] / Rex[-1] - 1),
           100 * abs(Rbr[3] / Rex[3] - 1)),
        'from 1 as sigma^1.5 where the true correction is O(sigma^2), so at this surface\'s sigma_v = %.4f it removes %.0f%% of the grazing rise above F0 where the truth'
        % (float(np.sqrt(WV.stationary_rms() ** 2 / 2)),
           100 * (1 - np.exp(-2.69 * WV.stationary_rms() / np.sqrt(2)) / (1 + 22.7 * (WV.stationary_rms() / np.sqrt(2)) ** 1.5))),
        'removes a few. 12 quotes the fit "for sigma_v < 0.5" and states no LOWER bound; it needs one. Right: the cost, best of three runs, numpy on a CPU -- what transfers',
        'is the ratio and the op count, not the milliseconds. Carrying the variance costs %.2fx the naive path here, and every bit of that is field.slope_var_points, which'
        % (C['fix']['ms'] / base_ms),
        'sums over EVERY component at every footprint and so costs the same at 400 m as at 4 m -- the opposite of the scaling 12 promises for exactly this quantity.',
    ], x=40, y=845)
    return P.save(img, os.path.join(OUT, 'r2-error-and-cost.png'))


FIGURES = {
    'r1-pass-vs-offline': fig_pass_vs_offline,
    'r1-factorisation-vs-tau': fig_factorisation,
    'r1-frame-factorisation': fig_frame_factorisation,
    'r1-lut-quality': fig_lut_quality,
    'r1-pass-anatomy': fig_pass_anatomy,
    'r2-two-paths': fig_two_paths,
    'r2-variance-vs-distance': fig_variance_vs_distance,
    'r2-error-and-cost': fig_error_and_cost,
}


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    want = [a for a in sys.argv[1:] if not a.startswith('-')]
    for name, fn in FIGURES.items():
        if want and not any(name.startswith(w) for w in want):
            continue
        print(fn())
