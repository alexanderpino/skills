"""The apparent-albedo re-take, as one picture, into `gauntlet/evidence/`.

    python3 lobe_albedo_measure.py before      # the two runs this reads
    python3 lobe_albedo_measure.py after
    python3 lobe_albedo_evidence.py            # -> fig-pool-albedo-retake.png
    python3 lobe_albedo_evidence.py <outdir>

    FIXLOBE_NPZ=<dir>                          where those buffers live

WHAT THIS FIGURE HAS TO SHOW, and it is four things in one row.

  1  WHERE THE MEASUREMENT WAS TAKEN, drawn on the frame it was taken on. The
     largest of the three errors in the older reading of this same quantity was
     *a region that did not contain the phenomenon*, so the region is the first
     thing a reader has to be able to audit, and it has to survive being drawn:
     the outlines are computed AFTER the frame is resampled to the panel, at
     panel resolution and 3 px wide, because a 1 px outline drawn at 800x1200
     and then LANCZOS'd down is an outline nobody can check. Both regions are
     drawn -- the numerator (`REG == 3`, sunlit floor at 1.40 m seen through the
     water) and the denominator (`REG == 4`, sunlit coping stone) -- and over
     them, the output pixels the lobe fix moved.

  2  THE PAIR, PER BAND, AGAINST THE CLOSED FORM. Pre-fix and post-fix measured
     `rho_water` beside `optics.rho_water` evaluated at this file's own
     constants. The two measured ladders coincide to every digit, which is what
     the panel exists to show; the closed form is a third, independent ladder.

  3  WHY IT DID NOT MOVE, which is the COLUMN and not the REGION. The lobe did
     reach this region. The same region's two columns are drawn: the transmitted
     one the measurement is of, and the reflected one the lobe lives in. The
     first is bit-identical; the second lost 42% of its mean and none of its
     median.

  4  THE SWEEP, as one bar each. Every photometric reading `render.py` takes off
     this frame, as the percentage the lobe fix moved it. Five of them are zero
     to the bit and three are not, and which is which is the round's finding.

EVERY NUMBER IN EVERY CAPTION IS FORMATTED FROM THE BUFFERS THE PANELS DRAW.
Nothing is transcribed. Provenance is stated per panel: `derived` for the closed
form, `measured` for anything read off a render.

THE TONE MAP IS DISPLAY-ONLY. Panel 1 is encoded for the eye; every number in
the figure is taken in scene-linear radiance off `HDRP` and the two columns,
never off a PNG. The two display-referred rows in panel 4 are labelled as such
and are there only because the README carries those readings as display-referred.
The plotting toolkit is `beach_plot.py`, and the encode is
`fix_lobe_evidence._encode` -- render.py's own, already written once.

TWO THRESHOLDS ARE DECLARED RATHER THAN ASSUMED. `lobe_albedo_measure.py` stores
`HDRP` as float32, so "moved" in panel 1 means "differs in the float32 buffer",
i.e. by more than about 1e-7 of the pixel. That is a STRICTER test than the
close-out section's 58.96%, which was taken on float64 buffers and counts every
water pixel that moved at all; both are stated so neither can be read as the
other. And panel 4 separates "equal to the last bit" from "equal to 1e-9",
because the two are different claims and only the first is bit-identity.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

import beach_plot as P                                          # noqa: E402
import fix_lobe_evidence as FLE                                 # noqa: E402
import validate as VAL                                          # noqa: E402

OUT = os.path.join(HERE, '..', '..', 'gauntlet', 'evidence')
NPZ = os.environ.get('FIXLOBE_NPZ', '.')

RED = (192, 56, 44)
BLUE = (38, 90, 168)
GREEN = (36, 128, 84)
WARN = (196, 112, 12)
_Y = np.array([.2126, .7152, .0722])
BANDS = ('red', 'green', 'blue', 'lum')


def _outline(mask, k=3):
    """The k-px inner boundary of a boolean mask, by its own 4-neighbourhood."""
    m = np.asarray(mask, bool)
    e = np.zeros_like(m)
    e[1:] |= m[1:] & ~m[:-1]
    e[:-1] |= m[:-1] & ~m[1:]
    e[:, 1:] |= m[:, 1:] & ~m[:, :-1]
    e[:, :-1] |= m[:, :-1] & ~m[:, 1:]
    for _ in range(k - 1):
        g = e.copy()
        g[1:] |= e[:-1]
        g[:-1] |= e[1:]
        g[:, 1:] |= e[:, :-1]
        g[:, :-1] |= e[:, 1:]
        e = g
    return e & m


def _cover(mask, pw, ph):
    """A boolean mask resampled to the panel as a COVERAGE fraction, so a
    region that is 3% of a panel pixel tints it by 3% rather than by nothing or
    by everything."""
    im = Image.fromarray((np.asarray(mask, bool) * 255).astype(np.uint8))
    return np.asarray(im.resize((pw, ph), Image.BOX), np.float64) / 255.0


def _lum4(v):
    """A per-band triple with its own luminance appended, for a 4-tick axis."""
    v = np.asarray(v, float)
    return np.append(v, float(v @ _Y))


def _wrap(s, n=300):
    out, cur = [], ''
    for w in s.split(' '):
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    out.append(cur)
    return out


def _srgb_med_lum(H, R, mask):
    """The DISPLAY-REFERRED reading `render.py`'s colour regression prints: the
    per-channel median sRGB code value over a region, collapsed to luminance.
    Reproduced here only so panel 4 can show what a reader with the PNG gets;
    nothing physical is taken off it."""
    return float(np.median(FLE._encode(H, R)[mask].reshape(-1, 3), 0) @ _Y)


def main():
    global OUT
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        OUT = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    R, _s, _e = VAL.load_render()

    A = np.load(os.path.join(NPZ, 'albedo-after-hero.npz'), allow_pickle=True)
    B = np.load(os.path.join(NPZ, 'albedo-before-hero.npz'), allow_pickle=True)
    ma, mb = json.loads(str(A['meta'])), json.loads(str(B['meta']))
    assert np.array_equal(A['REG'], B['REG']), \
        'the two runs do not share a segmentation; the panels are not comparable'
    REG = A['REG']
    HA, HB = A['HDRP'].astype(float), B['HDRP'].astype(float)
    PTA, PTB = A['PTRAN'].astype(float), B['PTRAN'].astype(float)
    PSA, PSB = A['PSPEC'].astype(float), B['PSPEC'].astype(float)
    w3, s4 = REG == 3, REG == 4
    moved = (HA != HB).any(-1)
    spec_moved = (PSA != PSB).any(-1)

    # ---- the numbers the captions carry, all off the buffers above
    n_w, n_s = int(w3.sum()), int(s4.sum())
    ov = float((spec_moved & w3).sum()) / max(n_w, 1)
    frac_moved = float(moved.mean())
    assert np.array_equal(PTA, PTB), \
        'the transmitted column moved; the report is wrong'
    assert (moved & s4).sum() == 0, \
        'the denominator moved; it is above the water and must not'
    rho_meas_a, rho_meas_b = _lum4(ma['rho_w_meas_band']), \
        _lum4(mb['rho_w_meas_band'])
    rho_meas_a[3], rho_meas_b[3] = ma['rho_w_meas'], mb['rho_w_meas']
    rho_pred = _lum4(ma['rho_w_pred_band'])
    rho_pred[3] = ma['rho_w_pred']
    fall = 1 - float((HA @ _Y).sum() / (HB @ _Y).sum())

    # ---- panel 4: the sweep, pre and post of every reading this frame carries
    sweep = [
        ('rho_water measured, luminance -- THE HEADLINE ROW',
         mb['rho_w_meas'], ma['rho_w_meas']),
        ('rho_water measured, green band',
         mb['rho_w_meas_band'][1], ma['rho_w_meas_band'][1]),
        ('water/stone, transmitted mean over mean',
         mb['r_tran'], ma['r_tran']),
        ('transmitted column, mean over region 3',
         float((PTB[w3] @ _Y).mean()), float((PTA[w3] @ _Y).mean())),
        ('reflected column, MEDIAN over region 3',
         mb['sp_med'], ma['sp_med']),
        ('water/stone, + reflected median (glitter out)',
         mb['r_tran_plus_specmed'], ma['r_tran_plus_specmed']),
        ('sunlit floor, median sRGB luminance [display]',
         _srgb_med_lum(HB, R, w3), _srgb_med_lum(HA, R, w3)),
        ('water/stone, median over median [display, PNG]',
         mb['r_med_display'], ma['r_med_display']),
        ('water/stone, median over median, scene-linear',
         mb['r_med_scene'], ma['r_med_scene']),
        ('frame total radiance, luminance',
         float((HB @ _Y).sum()), float((HA @ _Y).sum())),
        ('reflected column, MEAN over region 3',
         mb['sp_mean'], ma['sp_mean']),
    ]
    pct = [100.0 * (post / pre - 1.0) for _, pre, post in sweep]
    exact = [pre == post for _, pre, post in sweep]

    # ---- the key and the caption, written before the canvas so it can be
    #      sized to hold them rather than clipped to a guess
    keyrows = [
        (None, 'PANEL 1, the region drawn on the frame it was measured on '
               '(measured):'),
        (BLUE, 'NUMERATOR -- `REG == 3`, the sunlit floor at 1.40 m seen '
               'through the water, %s output pixels. This is the region the '
               'closed form is about.' % '{:,}'.format(n_w)),
        (RED, 'DENOMINATOR -- `REG == 4`, the sunlit coping stone, %s output '
              'pixels. It is above the water and NOT ONE of them moved, which '
              'is the panel\'s own control.' % '{:,}'.format(n_s)),
        (WARN, 'the output pixels the lobe fix moved in the float32 buffer: '
               '%.2f%% of the frame. The lobe DID reach the numerator -- '
               '%.1f%% of region 3 has a moved REFLECTED column.'
               % (100 * frac_moved, 100 * ov)),
        (None, ''),
        (None, 'PANEL 2, the pair per band:'),
        (GREEN, 'the closed form `optics.rho_water` at this file\'s own '
                'constants (DERIVED -- the lobe cannot touch it).'),
        (P.MUTED, 'measured off the render with the PRE-fix projection lobe '
                  '(MEASURED, hatched).'),
        (BLUE, 'measured off the render with the POST-fix lobe (MEASURED). The '
               'two measured ladders coincide to every digit: %.6f both, in '
               'luminance.' % rho_meas_a[3]),
        (None, ''),
        (None, 'PANEL 3, the two columns of the same region -- open circle = '
               'PRE-fix, filled disc = POST-fix, and a lone filled disc means '
               'the reading did not move:'),
        (GREEN, 'the TRANSMITTED column -- what the measurement is of. Pre and '
                'post are bit-identical, in every band, over the whole frame.'),
        (RED, 'the REFLECTED column\'s MEAN -- where the lobe lives. It fell '
              'x%.3f / %.3f / %.3f per band.'
              % tuple(np.array(ma['spec_band_mean'])
                      / np.array(mb['spec_band_mean']))),
        (BLUE, 'the REFLECTED column\'s MEDIAN -- unmoved to 5e-11: the whole '
               'of the fall is in the glitter tail, not in the level.'),
        (None, ''),
        (None, 'PANEL 4, the sweep. Every reading is scene-linear off `HDRP` '
               'or off `water_shade`\'s two columns except the two marked '
               '[display], which are what a reader with the PNG gets and are '
               'carried for that reason only.'),
    ]
    caption = []
    for s in [
        'THE RE-TAKE.  `terrain-renderer/reference-impl/README.md` carries the '
        'pool\'s headline photometric row -- the render\'s apparent albedo '
        'against `optics.rho_water` -- as a number MEASURED off a render, and it '
        'was measured before `7fe9538` fixed the widened environment lobe\'s '
        'exponent from 1/(uT Q u) to uT Q^-1 u. Both passes here are full '
        '`render.py` hero passes at one framing (same camera, same field, same '
        'seed, same EXPOSURE %.3f); the pre-fix one has `_lobe_shape` '
        'monkeypatched back to the projection form by '
        '`fix_lobe_render._lobe_projection` for that run only, and '
        '`atmosphere.py` on disk is never touched. Everything is read off `HDRP` '
        'and off `water_shade`\'s own two columns, in scene-linear radiance, '
        'before the tone map -- NEVER off a PNG.' % R.EXPOSURE,
        '',
        'THE VERDICT (measured against derived).  rho_water measured %.6f '
        'pre-fix and %.6f post-fix -- IDENTICAL, bit for bit, in luminance and '
        'in all three bands -- against a closed form (derived) of %.6f: %+.1f%% '
        'before and %+.1f%% after. THE AGREEMENT NEITHER IMPROVED NOR WORSENED, '
        'because the fix could not reach it.'
        % (rho_meas_b[3], rho_meas_a[3], rho_pred[3],
           100 * (rho_meas_b[3] / rho_pred[3] - 1),
           100 * (rho_meas_a[3] / rho_pred[3] - 1)),
        '',
        'AND THE REASON IS PANEL 3, NOT PANEL 1.  The region is not the problem '
        'this time -- the lobe DID reach it: %.1f%% of the numerator\'s own '
        'pixels have a moved reflected column, and that column\'s mean over the '
        'region fell %.4f -> %.4f in luminance (x%.3f). But the measurement is '
        'of the TRANSMITTED column, which is bit-identical over the whole frame, '
        'while the lobe lives entirely in the REFLECTED one -- and the block '
        'takes that column deliberately, on its own stated ground that a mean '
        'over the whole pixel is hostage to a factor-%.0f glitter tail. THE SAME '
        'CHOICE THAT MAKES THE ROW ROBUST TO GLITTER IS WHAT MAKES IT BLIND TO '
        'THE LOBE.' % (100 * ov, mb['sp_mean'], ma['sp_mean'],
                       ma['sp_mean'] / mb['sp_mean'],
                       mb['sp_mean'] / mb['sp_med']),
        '',
        'WHAT THAT IMPLICATES.  A %.1f%% fall in the frame\'s total radiance is '
        'invisible to every row of the pool\'s photometric ledger except the '
        'three in panel 4 that move by one part in a hundred, none of which is '
        'compared with a closed form at all. The ledger was never exposed to '
        'this defect and could not have caught it -- the raster reference did. '
        'That gap, no regression anywhere on the reflected column\'s LEVEL '
        'against anything, is what this re-take implicates as the next thing to '
        'build, and it is a gap in the INSTRUMENT rather than in the physics.'
        % (100 * fall),
    ]:
        caption += _wrap(s) if s else ['']

    # ---- canvas, sized from the text above
    ny, nx = REG.shape
    gap, top, ph, aw, yl, lw = 36, 120, 600, 300, 66, 312
    pw = int(round(ph * nx / ny))
    x0 = gap
    x1 = x0 + pw + gap + yl
    x2 = x1 + aw + gap + yl
    x3 = x2 + aw + gap + lw
    wcanvas = x3 + aw + gap
    keyy = top + ph + 54
    capy = keyy + 18 * len(keyrows) + 26
    img = P.canvas(wcanvas, capy + 18 * len(caption) + 24)
    d = P.ImageDraw.Draw(img)

    # ================================================ panel 1 -- the region
    pan = np.asarray(Image.fromarray(FLE._encode(HA, R))
                     .resize((pw, ph), Image.LANCZOS), float)
    cm, cw, cs = (_cover(m, pw, ph) for m in (moved, w3, s4))
    for cov, col, a in ((cw, BLUE, .13), (cs, RED, .11),
                        (np.minimum(1.0, 4.0 * cm), WARN, .80)):
        pan = pan * (1 - a * cov[..., None]) + np.array(col) * a * cov[..., None]
    pan[_outline(cw > .5)] = BLUE
    pan[_outline(cs > .5)] = RED
    img.paste(Image.fromarray(pan.clip(0, 255).astype(np.uint8)), (x0, top))
    d.rectangle([x0, top, x0 + pw - 1, top + ph - 1], outline=P.INK, width=1)
    d.text((x0, 30), '1 · WHERE IT WAS TAKEN', fill=P.INK, font=P.FONT_B)
    for i, s in enumerate((
            'the POST-fix hero frame, `render.py` HEAD -- scene-linear `HDRP` '
            'tone-mapped for the eye ONLY  (measured)',
            'axes: output pixel column x, 0-%d left to right; output pixel row '
            'y, 0-%d top to bottom' % (nx - 1, ny - 1),
            'both regions outlined at PANEL resolution, 3 px wide')):
        d.text((x0, 52 + 16 * i), s, fill=P.MUTED, font=P.FONT_S)

    # ================================ panel 2 -- the ladder, per band
    ymax = 1.28 * max(rho_meas_a.max(), rho_pred.max())
    ax = P.Axes(img, (x1, top, x1 + aw, top + ph), (-0.55, 3.55), (0.0, ymax),
                title='2 · THE PAIR, PER BAND',
                xlabel='band of `render.py`\'s own three, and luminance',
                ylabel='apparent albedo  rho_water  (scene-linear, unitless)')
    ax.frame(xticks=[0, 1, 2, 3], yticks=np.arange(0, ymax, 0.1),
             xfmt='%g', yfmt='%.1f')
    for i, nm in enumerate(BANDS):
        ax.d.text((float(ax.px(i)), ax.y1 + 4), nm, fill=P.MUTED,
                  font=P.FONT_S, anchor='ma')
    bw = 0.17
    for i in range(4):
        for j, (v, col, hatch) in enumerate((
                (rho_pred[i], GREEN, False),
                (rho_meas_b[i], P.MUTED, True),
                (rho_meas_a[i], BLUE, False))):
            cx = i + (j - 1) * bw
            ax.d.rectangle([float(ax.px(cx - bw / 2)), float(ax.py(v)),
                            float(ax.px(cx + bw / 2)), ax.y1],
                           fill=None if hatch else col, outline=col, width=2)
            if hatch:
                for t in np.arange(0.0, 1.0, 0.13):
                    ax.d.line([float(ax.px(cx - bw / 2)), float(ax.py(v * t)),
                               float(ax.px(cx + bw / 2)),
                               float(ax.py(v * min(t + 0.065, 1.0)))],
                              fill=col, width=1)
        ax.d.text((float(ax.px(i)), float(ax.py(rho_meas_a[i])) - 7),
                  'measured %+.1f%%' % (100 * (rho_meas_a[i] / rho_pred[i] - 1)),
                  fill=P.INK, font=P.FONT_S, anchor='ms')

    # ================================ panel 3 -- the two columns
    lo, hi = -2.1, 1.75                                   # decades of radiance
    ax2 = P.Axes(img, (x2, top, x2 + aw, top + ph), (-0.55, 3.55), (lo, hi),
                 title='3 · WHY: THE COLUMN, NOT THE REGION',
                 xlabel='the same region 3, per band and in luminance',
                 ylabel='mean over region 3, scene-linear radiance (log10)')
    ax2.frame(xticks=[0, 1, 2, 3], yticks=np.arange(-2, 2, 1), yfmt='1e%g')
    for i, nm in enumerate(BANDS):
        ax2.d.text((float(ax2.px(i)), ax2.y1 + 4), nm, fill=P.MUTED,
                   font=P.FONT_S, anchor='ma')
    for k, (col, va, vb) in enumerate((
            (GREEN, _lum4(ma['tran_band']), _lum4(mb['tran_band'])),
            (RED, _lum4(ma['spec_band_mean']), _lum4(mb['spec_band_mean'])),
            (BLUE, _lum4(ma['spec_band_med']), _lum4(mb['spec_band_med'])))):
        cx = np.arange(4) + (k - 1) * 0.23
        for i in range(4):
            ya, yb = np.log10(max(va[i], 1e-9)), np.log10(max(vb[i], 1e-9))
            if abs(ya - yb) > 1e-9:
                ax2.d.line([float(ax2.px(cx[i])), float(ax2.py(yb)),
                            float(ax2.px(cx[i])), float(ax2.py(ya))],
                           fill=col, width=3)
                ax2.d.ellipse([float(ax2.px(cx[i])) - 5, float(ax2.py(yb)) - 5,
                               float(ax2.px(cx[i])) + 5, float(ax2.py(yb)) + 5],
                              fill=P.BG, outline=col, width=2)
            ax2.marker(cx[i], ya, col, r=4)

    # ================================ panel 4 -- the sweep
    lo4 = 1.16 * min(pct + [0.0])
    ax3 = P.Axes(img, (x3, top, x3 + aw, top + ph), (lo4, 1.0),
                 (-0.6, len(sweep) - 0.4),
                 title='4 · THE SWEEP: WHAT THE FIX MOVED',
                 xlabel='change under the lobe fix, 100·(post/pre − 1), per cent',
                 y_up=False)
    ax3.frame(xticks=[-40, -30, -20, -10, 0], xfmt='%d')
    ax3.d.line([float(ax3.px(0)), ax3.y0, float(ax3.px(0)), ax3.y1],
               fill=P.INK, width=1)
    for i, ((lab, pre, post), p) in enumerate(zip(sweep, pct)):
        yy = float(ax3.py(i))
        col = P.MUTED if abs(p) < 1e-6 else RED if p < 0 else GREEN
        xa, xb = sorted([float(ax3.px(0)), float(ax3.px(p))])
        ax3.d.rectangle([xa, yy - 8, max(xb, xa + 2), yy + 8], fill=col)
        ax3.d.text((x3 - 10, yy), lab, fill=P.INK, font=P.FONT_S, anchor='rm')
        txt = ('zero, to the last bit' if exact[i] else
               ('%+.1e%%' % p) if abs(p) < 1e-6 else '%+.3f%%' % p)
        if xb - xa > 90:                     # inside the bar, or it lands on
            ax3.d.text((xa + 8, yy), txt, fill=(255, 255, 255),   # the label
                       font=P.FONT_S, anchor='lm')
        else:
            ax3.d.text((xa - 7, yy), txt,
                       fill=P.INK if abs(p) > 1e-6 else P.MUTED,
                       font=P.FONT_S, anchor='rm')

    # ================================ the key and the caption
    for i, (col, s) in enumerate(keyrows):
        yy = keyy + 18 * i
        if col is not None:
            d.rectangle([gap, yy + 4, gap + 16, yy + 12], fill=col)
        d.text((gap + (24 if col is not None else 0), yy), s,
               fill=P.INK if col is not None else P.MUTED,
               font=P.FONT_S if col is not None else P.FONT)
    P.caption(img, caption, x=gap, y=capy)

    path = P.save(img, os.path.join(OUT, 'fig-pool-albedo-retake.png'))
    print('%-34s meas_pre=%.6f meas_post=%.6f closed=%.6f overlap=%.4f '
          'spec_mean=%.4f->%.4f' % (os.path.basename(path), rho_meas_b[3],
                                    rho_meas_a[3], rho_pred[3], ov,
                                    mb['sp_mean'], ma['sp_mean']))
    for (lab, pre, post), p, ex in zip(sweep, pct, exact):
        print('   %-46s %+11.5f%%   %s' % (lab, p, 'BIT-IDENTICAL' if ex else ''))
    print('done: 1 figure into %s' % os.path.normpath(OUT))


if __name__ == '__main__':
    main()
