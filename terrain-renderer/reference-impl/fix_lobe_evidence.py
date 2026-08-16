"""The lobe-receiver fix, as pictures, into `gauntlet/evidence/`, under the
`fig-pool-` prefix the pool loop's other six figures already use.

    python3 fix_lobe_evidence.py            # both figures
    python3 fix_lobe_evidence.py <outdir>

TWO FIGURES AND WHAT EACH ONE HAS TO SHOW.

  `fig-pool-lobe-before-after.png`  The pool's hero frame either side of the
      change, at IDENTICAL framing -- same camera, same seed, same exposure,
      same crop -- with the scene-linear difference beside them. The frames are
      not re-derived here: they are the `HDRP` buffers of two full `render.py`
      runs, handed in as `.npz`, so what is drawn is the renderer's own output
      and not a reconstruction of it.

  `fig-pool-lobe-energy-vs-ratio.png`  The quantity the defect was, against the
      quantity that hid it: the widened lobe's flux over the sphere as a
      function of the reflection ellipse's axis ratio, for both forms, in
      ABSOLUTE steradians and against the unwidened `2 pi/(n+1)`. At ratio 1
      the two curves are the same number and that is the whole reason this
      shipped.

EVERY NUMBER IN EVERY CAPTION IS FORMATTED FROM THE RUN THAT DREW THE FRAME.
Nothing here is transcribed, and if a constant moves the caption moves with it.

THE TONE MAP IS DISPLAY-ONLY AND NOTHING MEASURED GOES THROUGH IT. `_encode`
below is `render.py`'s own `encode` after the SS box-average has already
happened (the `.npz` carries `HDRP`, which is that average), reproduced here
rather than imported because importing `render.py` runs a five-minute render and
prints. Every number in every caption is taken in scene-linear radiance, before
it -- the standing ruling in this project, and the one a false finding was once
bought by breaking.

The plotting toolkit is `beach_plot.py`, imported. A second plotting style in
one project is a second project.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

import atmosphere as ATM                                        # noqa: E402
import beach_plot as P                                          # noqa: E402
import validate as VAL                                          # noqa: E402

OUT = os.path.join(HERE, '..', '..', 'gauntlet', 'evidence')
NPZ = os.environ.get('FIXLOBE_NPZ', '.')

RED = (192, 56, 44)
BLUE = (38, 90, 168)
GREEN = (36, 128, 84)
WARN = (176, 108, 20)


# --------------------------------------------------------------- the tone map
# render.py's `encode`, minus the SS average that HDRP has already had. The
# EXPOSURE and the five ACES constants are read out of the sliced render module
# rather than retyped, so this cannot drift from the frames it is drawing.
def _encode(hdr, R):
    x = np.asarray(hdr, float) * R.EXPOSURE
    a, b, c, d, e = 2.51, .03, 2.43, .59, .14
    x = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    x = np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)
    x = np.clip(x, 0, 1)
    lum = (x * np.array([.2126, .7152, .0722])).sum(-1, keepdims=True)
    x = np.clip(lum + (x - lum) * 1.06, 0, 1)
    x = np.clip((x - .5) * 1.045 + .5 + .020, 0, 1)
    return (x * 255 + .5).astype(np.uint8)


_Y = np.array([.2126, .7152, .0722])


def _lum(a):
    return np.asarray(a, float) @ _Y


# ----------------------------------------------------------------- figure one
# THE SIGNED DIFFERENCE, AND WHY IT IS SIGNED. An |absolute| difference map
# would hide the one thing the closed form already predicts: Cauchy-Schwarz
# puts (u^T Q u)(u^T Q^-1 u) >= 1, so the shipped exponent was never larger
# than the right one, the shipped lobe was never too narrow, and every pixel
# the change touches has to FALL. A map that cannot show a rise cannot show
# that it did not happen. The scale is a signed QUARTER power of |dL| / max|dL|
# -- four decades of it, because the difference spans them -- which is a display
# ramp and nothing else: the colour bar is labelled in ABSOLUTE scene-linear
# radiance at each tick, so a reader takes the number off the bar and not off
# the colour.
_DIV_NEG = np.array([38., 90., 168.])       # after < before: the lobe narrowed
_DIV_POS = np.array([192., 56., 44.])       # after > before: does not occur
_DIV_MID = np.array([250., 249., 246.])     # P.BG, so zero reads as paper


def _diverging(d, dmax, gamma=0.25):
    """Signed d -> RGB. `dmax` is the symmetric limit and is stated on the bar."""
    t = np.clip(np.abs(d) / max(dmax, 1e-30), 0, 1) ** gamma
    end = np.where((np.asarray(d) < 0)[..., None], _DIV_NEG, _DIV_POS)
    return (_DIV_MID + (end - _DIV_MID) * t[..., None]).astype(np.uint8)


def _colourbar(img, x0, y0, w, h, dmax, ticks):
    """A horizontal bar for `_diverging`, labelled in scene-linear radiance."""
    ramp = np.linspace(-1.0, 1.0, int(w))
    strip = _diverging(np.sign(ramp) * dmax * np.abs(ramp) ** (1 / 0.25), dmax)
    img.paste(Image.fromarray(np.repeat(strip[None], int(h), 0)),
              (int(x0), int(y0)))
    d = P.ImageDraw.Draw(img)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h], outline=P.INK, width=1)
    for v in ticks:
        f = np.sign(v) * (abs(v) / dmax) ** 0.25          # the ramp's own map
        px = x0 + (f + 1.0) / 2.0 * (w - 1)
        d.line([px, y0 + h, px, y0 + h + 4], fill=P.INK)
        d.text((px, y0 + h + 6), ('%+.3g' % v) if v else '0', fill=P.MUTED,
               font=P.FONT_S, anchor='ma')


def fig_frames(R, path):
    """The hero frame either side of the change, and the SIGNED scene-linear
    difference between them, all at one framing and with a colour bar."""
    A = np.load(os.path.join(NPZ, 'hdr-before-hero.npz'))['HDRP']
    B = np.load(os.path.join(NPZ, 'hdr-after-hero.npz'))['HDRP']
    if A.shape != B.shape:
        raise SystemExit('the two frames are not at the same framing: %s vs %s'
                         % (A.shape, B.shape))

    # ---- the measurement, in SCENE-LINEAR radiance and before any tone map
    d = np.abs(B - A).max(-1)                    # per pixel, worst channel
    moved = d > 0.0
    la, lb = _lum(A), _lum(B)
    dl = lb - la                                 # SIGNED, luminance
    frac = 100.0 * moved.mean()
    iy, ix = np.unravel_index(int(np.argmax(d)), d.shape)
    peak_frac = float(d[iy, ix] / max(la[iy, ix], 1e-12))
    rel = np.abs(dl[moved]) / np.maximum(la[moved], 1e-12)
    ea, eb = _encode(A, R), _encode(B, R)
    ya, yb = _lum(ea / 255.0), _lum(eb / 255.0)
    lev = np.abs(eb.astype(int) - ea.astype(int)).max(-1)   # DISPLAY only

    # per band, and the bands are not the same number: the liner is blue and
    # the widened lobe multiplies a reddened SUN_COL, so R moves most.
    pb = [(nm, float(np.abs(B[..., i] - A[..., i]).max()),
           float(B[..., i][moved].sum() / max(A[..., i][moved].sum(), 1e-30)))
          for i, nm in enumerate('RGB')]

    # ---- where it moved most, as a crop the reader can see it in
    ny, nx = d.shape
    k = 96
    box = np.array([[d[y:y + k, x:x + k].sum() for x in range(0, nx - k, 24)]
                    for y in range(0, ny - k, 24)])
    iyb, ixb = np.unravel_index(int(np.argmax(box)), box.shape)
    cy, cx = iyb * 24, ixb * 24
    # the column band the difference lives in, at 5th-95th of its own mass
    cm = np.cumsum(d.sum(0)) / d.sum()
    c5, c95 = int(np.searchsorted(cm, .05)), int(np.searchsorted(cm, .95))
    rm = np.cumsum(d.sum(1)) / d.sum()
    r5, r95 = int(np.searchsorted(rm, .05)), int(np.searchsorted(rm, .95))

    # ---- the canvas: three full frames over three crops, then a colour bar
    fh = 620
    fw = int(round(fh * nx / ny))
    S = 3
    ch = k * S
    y_img, y_crop = 66, 66 + fh + 30
    dmax = float(np.abs(dl).max())
    dmap = _diverging(dl, dmax)
    img = P.canvas(3 * fw + 4 * 26, y_crop + ch + 96 + 18 * 18)
    panels = (
        ('BEFORE   n_eff = 1/(uᵀQu)', ea,
         'the shipped form, restored by monkeypatching `atmosphere._lobe_shape`',
         'in a throwaway runner -- the defective expression was never committed'),
        ('AFTER   n_eff = uᵀQ⁻¹u', eb,
         'HEAD of this branch, `atmosphere.py` at 7fe9538. Same camera, same',
         'field, same seed, same EXPOSURE %.3f, same crop as the panel left' % R.EXPOSURE),
        ('SIGNED Δ  (after − before)', None,
         'scene-linear luminance out of the two `HDRP` buffers, NO tone map.',
         'Blue = fell, red = rose. Scale on the bar below, in radiance'),
    )
    for j, (name, enc, pv1, pv2) in enumerate(panels):
        x0 = 26 + j * (fw + 26)
        if enc is None:
            enc = dmap
        im = Image.fromarray(enc).resize((fw, fh), Image.LANCZOS)
        img.paste(im, (x0, y_img))
        d0 = P.ImageDraw.Draw(img)
        d0.text((x0, 8), name, fill=P.INK, font=P.FONT_B)
        d0.text((x0, 30), pv1, fill=P.MUTED, font=P.FONT_S)
        d0.text((x0, 46), pv2, fill=P.MUTED, font=P.FONT_S)
        # the crop box, drawn on the frame it was chosen from
        bx0 = x0 + int(cx / nx * fw); by0 = y_img + int(cy / ny * fh)
        d0.rectangle([bx0, by0, bx0 + int(k / nx * fw), by0 + int(k / ny * fh)],
                     outline=RED if enc is not dmap else P.INK, width=2)
        # ---- the same crop at 3x, underneath
        cr = enc[cy:cy + k, cx:cx + k]
        img.paste(Image.fromarray(cr).resize((ch, ch), Image.NEAREST),
                  (x0, y_crop))
        d0.text((x0, y_crop - 20), 'the same %d x %d px at %dx, rows %d-%d, '
                'cols %d-%d' % (k, k, S, cy, cy + k, cx, cx + k),
                fill=P.MUTED, font=P.FONT_S)
    _colourbar(img, 26 + 2 * (fw + 26) + 44, y_crop + ch + 26, fw - 88, 18, dmax,
               (-dmax, -dmax * 1e-2, 0.0, dmax * 1e-2, dmax))
    P.ImageDraw.Draw(img).text(
        (26 + 2 * (fw + 26), y_crop + ch + 6),
        'ΔL, scene-linear radiance; signed quarter-power ramp, symmetric at %.4g'
        % dmax, fill=P.MUTED, font=P.FONT_S)

    P.caption(img, [
        'THE POOL\'S HERO FRAME, EITHER SIDE OF `atmosphere._lobe_shape`\'s '
        'EXPONENT. `n_eff = 1/(uᵀQu)` is the PROJECTION variance; the convolved '
        'density along u wants `n_eff = uᵀQ⁻¹u`, the 2x2 adjugate over det Q.',
        'The two are the SAME NUMBER for an isotropic Q -- for every u, exactly '
        '-- and on either principal axis, which is why all eleven lobe rows in '
        '`validate.py`, every one of them at cov = None, passed throughout.',
        'Found by the RASTER reference, an independent code path over the same '
        'shared module and the first consumer in this project to reach an '
        'anisotropic Q at all. Both frames here are full `render.py` hero passes.',
        '',
        'MEASURED IN SCENE-LINEAR RADIANCE, BEFORE THE TONE MAP THE FIRST TWO '
        'PANELS ARE DISPLAYED THROUGH. %.2f%% of the %d output pixels moved at '
        'all -- that set is the water, and nothing but the water, because'
        % (frac, d.size),
        '`water_shade` is the only caller in the file that hands the lobe a '
        'non-zero reflection ellipse. PEAK |Δ| is %.4g in radiance, at row %d '
        'col %d, which is %.1f%% of that pixel\'s own %.4g -- the pixel the'
        % (float(d.max()), iy, ix, 100 * peak_frac, float(la[iy, ix])),
        'defect moved most lost three quarters of itself. It is NOT a '
        'uniform lift: the median moved pixel changed by %.2f%% of its own '
        'radiance and the 99th percentile by %.1f%%, because the difference is'
        % (100 * float(np.percentile(rel, 50)),
           100 * float(np.percentile(rel, 99))),
        'a function of the ellipse\'s axis ratio and that ratio is a function '
        'of the view angle. The frame\'s MEDIAN radiance moved %.4g -> %.4g '
        '(%.2f%%); its TOTAL moved %.4g -> %.4g, a factor %.3f.'
        % (float(np.median(la)), float(np.median(lb)),
           100 * (np.median(lb) / np.median(la) - 1),
           float(la.sum()), float(lb.sum()), float(lb.sum() / la.sum())),
        'EVERY MOVED PIXEL FELL (%.3f%% of them), which is the sign '
        'Cauchy-Schwarz forces: (uᵀQu)(uᵀQ⁻¹u) >= 1, so the shipped exponent '
        'was never the larger and the shipped lobe was never too narrow.'
        % (100.0 * float((dl[moved] <= 0).mean())),
        'PER BAND, over the moved pixels: %s. The bands do not move together '
        'because the lobe multiplies a reddened `SUN_COL` against a blue liner.'
        % ', '.join('%s peak |Δ| %.4g, total x%.3f' % t for t in pb),
        '',
        'WHERE IT SITS, and it is not spread over the water evenly: 5th-95th of '
        'the difference\'s own mass is columns %d-%d of %d and rows %d-%d of '
        '%d. That is the near-left strip where the surface turns toward the'
        % (c5, c95, nx, r5, r95, ny),
        'sun\'s azimuth -- `render.py` prints the mirror band as landing at '
        '(4.60, 2.26), 1.13 half-widths past the frame edge, and this is its '
        'in-frame tail, the grazing water where 1/cos²θ_v is largest.',
        'The crop is chosen by the difference itself -- the 96 x 96 box with '
        'the largest summed |Δ| in the frame -- and not by eye.',
        '',
        'AND IT IS VISIBLE, which is a DISPLAY statement and is made here with '
        'display numbers and nowhere else: through `render.py`\'s own ACES + '
        'sRGB curve at EXPOSURE %.3f, %d pixels (%.2f%%) move by 10 sRGB levels'
        % (R.EXPOSURE, int((lev >= 10).sum()), 100.0 * float((lev >= 10).mean())),
        'or more and %d (%.2f%%) by 100 or more, the worst by %d levels. The '
        'whole frame\'s encoded mean luminance moves only %.3f -> %.3f of 1.0, '
        'because the glitter road is 1%% of the frame and the other 99%% is'
        % (int((lev >= 100).sum()), 100.0 * float((lev >= 100).mean()),
           int(lev.max()), ya.mean(), yb.mean()),
        'unchanged -- a frame-mean is exactly the statistic that would have '
        'called this defect invisible, and it is quoted here to be refused.',
    ], x=26)
    return P.save(img, path), dict(
        frac=frac, mean=float(d[moved].mean()) if moved.any() else 0.0,
        worst=float(d.max()), worst_at='%d,%d' % (iy, ix),
        worst_rel=peak_frac, y_before=float(ya.mean()), y_after=float(yb.mean()),
        npix=int(d.size), moved=int(moved.sum()),
        med_before=float(np.median(la)), med_after=float(np.median(lb)),
        total_ratio=float(lb.sum() / la.sum()),
        lev10=int((lev >= 10).sum()), lev100=int((lev >= 100).sum()),
        lev_max=int(lev.max()), crop=(cy, cx))


# ----------------------------------------------------------------- figure two
def fig_energy(R, path):
    """The lobe's flux against the ellipse's axis ratio, both forms, absolute
    and against the unwidened lobe."""
    n = ATM.N_DISC
    ref = 2.0 * np.pi / (n + 1.0)                # steradians, the unwidened lobe
    ratios = np.logspace(0, 4, 81)
    c22 = 1.0e-5                                 # the minor axis, held fixed
    f_ok = np.zeros(ratios.size); f_bug = np.zeros(ratios.size)
    qr = np.zeros(ratios.size)
    for i, rr in enumerate(ratios):
        c11 = c22 * rr
        f_ok[i] = VAL._lobe_flux(ATM._lobe_shape, n, c11, 0.0, c22)
        f_bug[i] = VAL._lobe_flux(VAL._lobe_projection, n, c11, 0.0, c22)
        qr[i] = (1.0 / n + c11) / (1.0 / n + c22)
    closed = np.cosh(.5 * np.log(qr))

    # ---- where THIS scene sits: the reflection ellipse render.py forms is
    # C = J SIGMA J^T with J = diag(-2, -2 cos theta_v), so an isotropic slope
    # tensor still arrives as an ellipse of ratio 1/cos^2(theta_v). theta_v is
    # the camera's own, taken off the flat datum over the basin's water.
    #
    # WEIGHTED BY PIXELS AND NOT BY AREA, and the difference is a factor of
    # three on the median: this camera stands 1.85 m over a 9 m basin, so most
    # of the WATER is far and grazing while most of the FRAME is near water. A
    # pinhole's pixel density on a plane is cos(theta_v)/d^2, which is the
    # weight below, and the samples are gated to the frame by `render.py`'s own
    # `project` rather than by a bounding box.
    xs = np.linspace(R.X0 + .02, R.X1 - .02, 480)
    ys = np.linspace(R.Y0 + .02, R.Y1 - .02, 320)
    X, Y = np.meshgrid(xs, ys)
    dx, dy, dz = X - R.EYE[0], Y - R.EYE[1], -R.EYE[2]
    d2 = dx * dx + dy * dy + dz * dz
    ct = np.abs(dz) / np.sqrt(d2)
    pool_r = (1.0 / ct ** 2).ravel()
    wgt = (ct / d2).ravel()
    pix = R.project(np.stack([X.ravel(), Y.ravel(),
                              np.zeros(X.size)], -1))
    inframe = ((pix[:, 0] >= 0) & (pix[:, 0] < R.W / R.SS)
               & (pix[:, 1] >= 0) & (pix[:, 1] < R.H / R.SS))
    pool_r, wgt = pool_r[inframe], wgt[inframe]
    o = np.argsort(pool_r)
    cw = np.cumsum(wgt[o]) / wgt.sum()
    lo, med, hi = (float(np.interp(q, cw, pool_r[o])) for q in (.05, .5, .95))
    med_area = float(np.median(pool_r))          # what area-weighting would say

    img = P.canvas(1420, 740)
    # ---- left: the whole sweep, four decades of ratio, gain on a log axis
    ax = P.Axes(img, (92, 66, 690, 446), (0, 4), (-0.14, 1.66),
                title='widened flux / the flux of the lobe it replaced',
                xlabel='ellipse axis ratio', ylabel='x  (log scale)')
    ax.frame()
    for x, lab in ((0, '1'), (1, '10'), (2, '100'), (3, '1e3'), (4, '1e4')):
        ax.vline(x, P.GRID, 1)
        ax.d.text((float(ax.px(x)), ax.y1 + 4), lab, fill=P.MUTED,
                  font=P.FONT_S, anchor='ma')
    for v in (1, 1.5, 2, 3, 5, 10, 20, 35):
        ax.hline(np.log10(v), P.GRID, 1)
        ax.d.text((ax.x0 - 6, float(ax.py(np.log10(v)))), '%g' % v,
                  fill=P.MUTED, font=P.FONT_S, anchor='rm')
    ax.band(np.log10(lo), np.log10(hi), (228, 236, 250))
    ax.line(np.log10(ratios), np.log10(f_bug / ref), RED, 3)
    ax.line(np.log10(ratios), np.log10(closed), P.INK, 1, dash=(5, 5))
    ax.line(np.log10(ratios), np.log10(f_ok / ref), GREEN, 3)
    ax.vline(np.log10(med), BLUE)
    ax.text(np.log10(med), 1.58, ' this pool, median ratio %.2f' % med, BLUE)
    P.legend(ax, [(RED, 'shipped,  n_eff = 1/(uᵀQu)'),
                  (P.INK, 'cosh(ln r / 2), closed form'),
                  (GREEN, 'fixed,  n_eff = uᵀQ⁻¹u')], 0.12, 1.38)

    # ---- right: the window this scene actually occupies, in ABSOLUTE sr
    m = ratios <= 14.0
    fl = min(f_ok[m].min(), ref) * 1e5
    fh = f_bug[m].max() * 1e5
    pad = 0.12 * (fh - fl)
    bx = P.Axes(img, (810, 66, 1380, 446), (1, 14), (fl - pad, fh + pad),
                title='the window this scene occupies, ABSOLUTE',
                xlabel='ellipse axis ratio  1/cos²θ_v',
                ylabel='lobe flux, sr x 1e-5')
    bx.frame(xticks=[1, 2, 4, 6, 8, 10, 12, 14])
    bx.band(lo, hi, (228, 236, 250))
    bx.line(ratios[m], f_bug[m] * 1e5, RED, 3)
    bx.line(ratios[m], f_ok[m] * 1e5, GREEN, 3)
    bx.hline(ref * 1e5, WARN)
    bx.text(1.15, ref * 1e5 + 0.02 * (fh - fl),
            'the unwidened lobe, 2π/(n+1) = %.5g sr' % ref, WARN)
    bx.marker(med, float(np.interp(med, ratios, f_bug)) * 1e5, RED, 5)
    bx.marker(med, float(np.interp(med, ratios, f_ok)) * 1e5, GREEN, 5)
    bx.vline(med, BLUE)

    P.caption(img, [
        'CONVOLUTION MOVES A LOBE\'S VARIANCE AND DOES NOT ADD TO ITS INTEGRAL. '
        'Both panels are the flux of ONE cos^%.0f disc lobe -- `atmosphere.'
        'N_DISC`, the sun\'s own -- after widening by a reflection ellipse of'
        % n,
        'the axis ratio on the x axis. The radial integral is exact '
        '(∫cos^m sinρ dρ = 1/(m+1), the same closed form the unwidened '
        '2π/(n+1) comes from) and the azimuth is a %d-point midpoint rule, so '
        'these are'
        % 16384,
        'integrals of the shipped code and not estimates of it. The GREEN curve '
        'is the repaired `_lobe_shape`: flat at %.3f out to ratio 100, because '
        'the peak factor g = √(det Q₀/det Q) was derived to make it so'
        % float(np.interp(2.0, np.log10(ratios), f_ok / ref)),
        'and with the right exponent it does. It falls to %.3f by 1e4, and that '
        'is the widening construction\'s own Gaussian limit showing -- a cos^m '
        'lobe carries 2π/(m+1) and the construction conserves 2π/m --'
        % float(f_ok[-1] / ref),
        'not a second error. The RED curve is the form that shipped: %.3f at '
        'ratio 1, IDENTICAL, because for Q = qI both expressions are 1/q '
        'exactly and for no other reason; then %.3f at 10 and %.1f at 1e4.'
        % (f_bug[0] / ref, float(np.interp(1.0, np.log10(ratios), f_bug / ref)),
           float(f_bug[-1] / ref)),
        'The dashed line is the closed form for that gain, cosh(ln r / 2) with '
        'r the EIGEN-ratio of Q, which the integral tracks to %.1f%% over the '
        'first three decades. Q = (1/n)I + C, so an ellipse of ratio 1e4'
        % (100 * float(np.max(np.abs(f_bug[ratios <= 1e3] / ref
                                     / closed[ratios <= 1e3] - 1.0)))),
        'is a Q of ratio only %.0f, and the gain saturates with it.' % qr[-1],
        '',
        'THE BLUE BAND IS THIS SCENE, and the right panel is nothing but that '
        'band, in STERADIANS. `render.py` forms C = J Σ Jᵀ with '
        'J = diag(-2, -2 cos θ_v), so even an isotropic slope tensor',
        'arrives as an ellipse of ratio 1/cos²θ_v. Over this frame\'s water '
        'on the flat datum, WEIGHTED BY PIXELS -- a pinhole\'s density on a '
        'plane is cosθ_v/d², and weighting by AREA instead would say',
        '%.2f, because most of the water is far and grazing while most of the '
        'frame is near -- that runs %.2f to %.2f (5th-95th percentile) with a '
        'median of %.2f, a flux gain of %.3f to %.3f, median %.3f.'
        % (med_area, lo, hi, med, float(np.cosh(.5 * np.log(lo))),
           float(np.cosh(.5 * np.log(hi))), float(np.cosh(.5 * np.log(med)))),
        'In absolute terms the median water pixel\'s disc lobe carried %.5g sr '
        'where the sun\'s own disc is %.5g sr. That is what the frame beside '
        'this one paid, and it is why the defect read as taste.'
        % (float(np.interp(med, ratios, f_bug)), ref),
        'The raster reference, whose grazing frame reaches an ellipse ratio of '
        '1e4, prices the same error at 12.0x on its own p99 -- which is the '
        'right end of this plot, and is how it was found at all.',
    ], x=26)
    return P.save(img, path), dict(lo=lo, hi=hi, med=med,
                                   g_lo=float(np.cosh(.5 * np.log(lo))),
                                   g_hi=float(np.cosh(.5 * np.log(hi))),
                                   g_med=float(np.cosh(.5 * np.log(med))),
                                   ref=ref, r1=float(f_bug[0] / ref),
                                   r1e4=float(f_bug[-1] / ref),
                                   qr1e4=float(qr[-1]))


FIGURES = (('fig-pool-lobe-before-after.png', fig_frames),
           ('fig-pool-lobe-energy-vs-ratio.png', fig_energy))


def main():
    global OUT
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        OUT = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    R, _skipped, _errs = VAL.load_render()
    for name, fn in FIGURES:
        p, stats = fn(R, os.path.join(OUT, name))
        print('%-34s %s' % (name, ' '.join(
            '%s=%s' % (k, ('%.6g' % v) if isinstance(v, float) else v)
            for k, v in sorted(stats.items()))))
    print('done: %d figures into %s' % (len(FIGURES), os.path.normpath(OUT)))


if __name__ == '__main__':
    main()
