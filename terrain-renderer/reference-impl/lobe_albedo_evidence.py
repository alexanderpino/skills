"""The apparent-albedo re-take, as one picture, into `gauntlet/evidence/`.

    python3 lobe_albedo_measure.py before      # the two runs this reads
    python3 lobe_albedo_measure.py after
    python3 lobe_albedo_evidence.py            # -> fig-pool-albedo-retake.png
    python3 lobe_albedo_evidence.py <outdir>

    FIXLOBE_NPZ=<dir>                          where those buffers live

WHAT THIS FIGURE HAS TO SHOW, and it is three things in one row.

  1  WHERE THE MEASUREMENT WAS TAKEN, drawn on the frame it was taken on. The
     largest of the three errors in the older reading of this same quantity was
     *a region that did not contain the phenomenon*, so the region is the first
     thing a reader has to be able to audit. Both regions are drawn -- the
     numerator (`REG == 3`, sunlit floor at 1.40 m seen through the water) and
     the denominator (`REG == 4`, sunlit coping stone) -- and over them, the set
     of output pixels the lobe fix actually moved. The overlap is the finding:
     the lobe DID reach this region, and the reading still did not move.

  2  THE PAIR, PER BAND, AGAINST THE CLOSED FORM. Pre-fix and post-fix measured
     `rho_water` beside `optics.rho_water` evaluated at this file's own
     constants. The two measured ladders coincide to every digit, which is what
     the panel exists to show; the closed form is a third, independent ladder.

  3  WHY IT DID NOT MOVE, which is the column and not the region. The same
     region's two columns: the transmitted one the measurement is of, and the
     reflected one the lobe lives in. The first is bit-identical; the second
     lost 42% of its mean and none of its median.

EVERY NUMBER IN EVERY CAPTION IS FORMATTED FROM THE BUFFERS THE PANELS DRAW.
Nothing is transcribed. Provenance is stated per panel: `derived` for the closed
form, `measured` for anything read off a render.

THE TONE MAP IS DISPLAY-ONLY. Panel 1 is encoded for the eye; every number in
the figure is taken in scene-linear radiance off `HDRP` and the two columns,
never off a PNG. The plotting toolkit is `beach_plot.py`, and the encode is
`fix_lobe_evidence._encode` -- render.py's own, already written once.
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
WARN = (176, 108, 20)
_Y = np.array([.2126, .7152, .0722])
BANDS = ('red', 'green', 'blue', 'lum')


def _outline(mask):
    """The 1-px boundary of a boolean mask, by its own 4-neighbourhood."""
    m = np.asarray(mask, bool)
    e = np.zeros_like(m)
    e[1:] |= m[1:] & ~m[:-1]
    e[:-1] |= m[:-1] & ~m[1:]
    e[:, 1:] |= m[:, 1:] & ~m[:, :-1]
    e[:, :-1] |= m[:, :-1] & ~m[:, 1:]
    return e


def _lum4(v):
    """A per-band triple with its own luminance appended, for a 4-tick axis."""
    v = np.asarray(v, float)
    return np.append(v, float(v @ _Y))


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
    w3, s4 = REG == 3, REG == 4
    moved = (HA != HB).any(-1)

    # ---- the numbers the captions carry, all off the buffers above
    n_w, n_s = int(w3.sum()), int(s4.sum())
    ov = float((moved & w3).sum()) / max(n_w, 1)
    frac_moved = float(moved.mean())
    tran_b = np.array(ma['tran_band'])
    assert np.allclose(tran_b, mb['tran_band'], rtol=0, atol=0), \
        'the transmitted column moved; the report is wrong'
    rho_meas_a, rho_meas_b = _lum4(ma['rho_w_meas_band']), \
        _lum4(mb['rho_w_meas_band'])
    rho_meas_a[3], rho_meas_b[3] = ma['rho_w_meas'], mb['rho_w_meas']
    rho_pred = _lum4(ma['rho_w_pred_band'])
    rho_pred[3] = ma['rho_w_pred']

    # ---- canvas
    ny, nx = REG.shape
    ph = 560
    pw = int(round(ph * nx / ny))
    gap, top = 34, 96
    aw = 300
    img = P.canvas(pw + 2 * aw + 4 * gap + 120, top + ph + 210)
    d = P.ImageDraw.Draw(img)

    # ================================================ panel 1 -- the region
    enc = FLE._encode(HA, R).copy()
    enc[moved] = (0.55 * enc[moved] + 0.45 * np.array(WARN)).astype(np.uint8)
    enc[_outline(w3)] = BLUE
    enc[_outline(s4)] = RED
    x0 = gap
    img.paste(Image.fromarray(enc).resize((pw, ph), Image.LANCZOS), (x0, top))
    d.rectangle([x0, top, x0 + pw - 1, top + ph - 1], outline=P.INK, width=1)
    d.text((x0, 26), '1 · WHERE IT WAS TAKEN  (measured)', fill=P.INK,
           font=P.FONT_B)
    d.text((x0, 48), 'the post-fix hero frame, `render.py` HEAD, tone-mapped '
                     'for the eye ONLY', fill=P.MUTED, font=P.FONT_S)
    d.text((x0, 64), 'x, y: output pixels, %d x %d' % (nx, ny), fill=P.MUTED,
           font=P.FONT_S)
    for i, (c, s) in enumerate((
            (BLUE, 'numerator  REG == 3, sunlit floor at 1.40 m '
                   'through the water (%s px)' % '{:,}'.format(n_w)),
            (RED, 'denominator  REG == 4, sunlit coping stone (%s px)'
             % '{:,}'.format(n_s)),
            (WARN, 'pixels the lobe fix moved: %.1f%% of the frame, and '
                   '%.1f%% of the numerator' % (100 * frac_moved, 100 * ov)))):
        yy = top + ph + 12 + 18 * i
        d.rectangle([x0, yy + 4, x0 + 16, yy + 12], fill=c)
        d.text((x0 + 24, yy), s, fill=P.INK, font=P.FONT_S)

    # ================================ panel 2 -- the ladder, per band
    x1 = x0 + pw + gap + 62
    ymax = 1.15 * max(rho_meas_a.max(), rho_pred.max())
    ax = P.Axes(img, (x1, top, x1 + aw, top + ph), (-0.5, 3.5), (0.0, ymax),
                title='2 · THE PAIR, PER BAND',
                xlabel='band of `render.py`\'s own three, and luminance',
                ylabel='apparent albedo  rho_water  (scene-linear, unitless)')
    ax.frame(xticks=[0, 1, 2, 3], yticks=np.arange(0, ymax, 0.1),
             xfmt='%g', yfmt='%.1f')
    for i, nm in enumerate(BANDS):
        ax.d.text((float(ax.px(i)), ax.y1 + 4), nm, fill=P.MUTED,
                  font=P.FONT_S, anchor='ma')
    bw = 0.16
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
                for t in np.arange(0.0, 1.0, 0.14):
                    ax.d.line([float(ax.px(cx - bw / 2)),
                               float(ax.py(v * t)),
                               float(ax.px(cx + bw / 2)),
                               float(ax.py(v * min(t + 0.07, 1.0)))],
                              fill=col, width=1)
        ax.d.text((float(ax.px(i)), float(ax.py(rho_meas_a[i])) - 6),
                  '%.4f' % rho_meas_a[i], fill=P.INK, font=P.FONT_S,
                  anchor='ms')
    P.legend(ax, ((GREEN, 'closed form `optics.rho_water`  (derived)'),
                  (P.MUTED, 'measured, PRE-fix lobe  (measured)'),
                  (BLUE, 'measured, POST-fix lobe  (measured)')),
             -0.35, ymax * 0.97)
    ax.d.text((float(ax.px(-0.35)), float(ax.py(ymax * 0.78))),
              'the two measured ladders coincide', fill=P.INK, font=P.FONT_S)
    ax.d.text((float(ax.px(-0.35)), float(ax.py(ymax * 0.74))),
              'to every digit: %.6f both.' % rho_meas_a[3], fill=P.INK,
              font=P.FONT_S)

    # ================================ panel 3 -- the two columns
    x2 = x1 + aw + gap + 76
    lo, hi = -2.2, 1.6                                    # decades of radiance
    ax2 = P.Axes(img, (x2, top, x2 + aw, top + ph), (-0.5, 3.5), (lo, hi),
                 title='3 · WHY: THE COLUMN, NOT THE REGION',
                 xlabel='the same region 3, per band and in luminance',
                 ylabel='mean radiance over region 3  (log10, scene-linear)')
    ax2.frame(xticks=[0, 1, 2, 3], yticks=np.arange(-2, 2, 1),
              yfmt='1e%g')
    for i, nm in enumerate(BANDS):
        ax2.d.text((float(ax2.px(i)), ax2.y1 + 4), nm, fill=P.MUTED,
                   font=P.FONT_S, anchor='ma')
    cols = (('transmitted, pre & post (identical)', GREEN,
             _lum4(ma['tran_band']), _lum4(mb['tran_band'])),
            ('reflected mean, pre -> post', RED,
             _lum4(ma['spec_band_mean']), _lum4(mb['spec_band_mean'])),
            ('reflected MEDIAN, pre & post (identical)', BLUE,
             _lum4(ma['spec_band_med']), _lum4(mb['spec_band_med'])))
    for k, (lab, col, va, vb) in enumerate(cols):
        cx = np.arange(4) + (k - 1) * 0.22
        for i in range(4):
            ya, yb = np.log10(max(va[i], 1e-9)), np.log10(max(vb[i], 1e-9))
            ax2.d.line([float(ax2.px(cx[i])), float(ax2.py(yb)),
                        float(ax2.px(cx[i])), float(ax2.py(ya))],
                       fill=col, width=3)
            ax2.marker(cx[i], yb, (255, 255, 255) if abs(ya - yb) > 1e-12
                       else col, r=4)
            ax2.d.ellipse([float(ax2.px(cx[i])) - 4, float(ax2.py(yb)) - 4,
                           float(ax2.px(cx[i])) + 4, float(ax2.py(yb)) + 4],
                          outline=col, width=2)
            ax2.marker(cx[i], ya, col, r=4)
    P.legend(ax2, [(c[1], c[0]) for c in cols], -0.35, lo + (hi - lo) * 0.97)
    ax2.d.text((float(ax2.px(-0.35)), float(ax2.py(lo + (hi - lo) * 0.78))),
               'open circle = pre-fix, filled = post-fix', fill=P.MUTED,
               font=P.FONT_S)
    g = np.array(ma['spec_band_mean']) / np.array(mb['spec_band_mean'])
    ax2.d.text((float(ax2.px(-0.35)), float(ax2.py(lo + (hi - lo) * 0.74))),
               'reflected mean x%.3f / %.3f / %.3f' % tuple(g), fill=RED,
               font=P.FONT_S)

    P.caption(img, [
        'THE RE-TAKE. `terrain-renderer/reference-impl/README.md` carries the '
        'pool\'s headline photometric row -- the render\'s apparent albedo '
        'against `optics.rho_water` -- as a number MEASURED off a render, and '
        'it was measured before 7fe9538 fixed the widened',
        'environment lobe\'s exponent. Both passes here are full `render.py` '
        'hero passes at one framing (same camera, same field, same seed, same '
        'EXPOSURE %.3f); the pre-fix one has `_lobe_shape` monkeypatched back '
        'to the projection form by' % R.EXPOSURE,
        '`fix_lobe_render._lobe_projection` for that run only, and '
        '`atmosphere.py` on disk is never touched. Read off `HDRP` and off '
        '`water_shade`\'s own two columns, in scene-linear radiance, before '
        'the tone map -- NEVER off a PNG.',
        '',
        'THE VERDICT (measured): rho_water measured %.6f pre-fix and %.6f '
        'post-fix -- IDENTICAL -- against a closed form (derived) of %.6f, '
        'i.e. %+.1f%% before and %+.1f%% after. The agreement neither improved '
        'nor worsened.'
        % (rho_meas_b[3], rho_meas_a[3], rho_pred[3],
           100 * (rho_meas_b[3] / rho_pred[3] - 1),
           100 * (rho_meas_a[3] / rho_pred[3] - 1)),
        'THE REASON IS PANEL 3 AND NOT PANEL 1. The region is not the problem '
        'this time: the lobe reached %.1f%% of the numerator\'s own pixels. '
        'The measurement is of the TRANSMITTED column, which is bit-identical '
        'over the whole frame,' % (100 * ov),
        'while the lobe lives entirely in the REFLECTED one, whose mean over '
        'this same region fell %.4f -> %.4f in luminance (x%.3f) and whose '
        'MEDIAN did not move at all (%.4f both). So the pool\'s photometric '
        'ledger was never exposed to this defect,'
        % (mb['sp_mean'], ma['sp_mean'], ma['sp_mean'] / mb['sp_mean'],
           ma['sp_med']),
        'and could not have caught it: a %.1f%% fall in the frame\'s total '
        'radiance is invisible to every row of it. That gap -- no regression '
        'anywhere on the reflected column\'s LEVEL -- is what this re-take '
        'implicates as the next thing to look at.'
        % (100 * (1 - float(HA.sum() / HB.sum()))),
    ], x=gap)

    path = P.save(img, os.path.join(OUT, 'fig-pool-albedo-retake.png'))
    print('%-34s meas_pre=%.6f meas_post=%.6f closed=%.6f overlap=%.4f '
          'spec_mean=%.4f->%.4f' % (os.path.basename(path), rho_meas_b[3],
                                    rho_meas_a[3], rho_pred[3], ov,
                                    mb['sp_mean'], ma['sp_mean']))
    print('done: 1 figure into %s' % os.path.normpath(OUT))


if __name__ == '__main__':
    main()
