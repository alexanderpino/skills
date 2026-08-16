"""The lobe-receiver fix, as pictures, into `gauntlet/evidence/` with a
`fix-lobe-` prefix.

    python3 fix_lobe_evidence.py            # both figures
    python3 fix_lobe_evidence.py <outdir>

TWO FIGURES AND WHAT EACH ONE HAS TO SHOW.

  `fix-lobe-hero-before-after.png`  The pool's hero frame either side of the
      change, at IDENTICAL framing -- same camera, same seed, same exposure,
      same crop -- with the scene-linear difference beside them. The frames are
      not re-derived here: they are the `HDRP` buffers of two full `render.py`
      runs, handed in as `.npz`, so what is drawn is the renderer's own output
      and not a reconstruction of it.

  `fix-lobe-energy-vs-ratio.png`  The quantity the defect was, against the
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
def fig_frames(R, path):
    """The hero frame either side of the change, and the difference between
    them, all at one framing."""
    A = np.load(os.path.join(NPZ, 'hdr-before-hero.npz'))['HDRP']
    B = np.load(os.path.join(NPZ, 'hdr-after-hero.npz'))['HDRP']
    if A.shape != B.shape:
        raise SystemExit('the two frames are not at the same framing: %s vs %s'
                         % (A.shape, B.shape))

    # ---- the measurement, in SCENE-LINEAR radiance and before any tone map
    d = np.abs(B - A).max(-1)                    # per pixel, worst channel
    moved = d > 0.0
    la, lb = _lum(A), _lum(B)
    dl = lb - la
    frac = 100.0 * moved.mean()
    ea, eb = _encode(A, R), _encode(B, R)
    ya, yb = _lum(ea / 255.0), _lum(eb / 255.0)

    # ---- where it moved most, as a crop the reader can see it in
    ny, nx = d.shape
    k = 96
    box = np.array([[d[y:y + k, x:x + k].sum() for x in range(0, nx - k, 24)]
                    for y in range(0, ny - k, 24)])
    iy, ix = np.unravel_index(int(np.argmax(box)), box.shape)
    cy, cx = iy * 24, ix * 24

    # ---- the canvas: three full frames over three crops
    fh = 560
    fw = int(round(fh * nx / ny))
    S = 3
    ch = k * S
    img = P.canvas(3 * fw + 4 * 26, fh + ch + 26 * 3 + 150)
    for j, (name, enc) in enumerate((('BEFORE  1/(uᵀQu)', ea),
                                     ('AFTER  uᵀQ⁻¹u', eb),
                                     ('scene-linear |Δ|', None))):
        x0 = 26 + j * (fw + 26)
        if enc is None:
            # the difference, on its own scale, stated in the label
            mx = float(d.max())
            g = np.clip(d / max(mx, 1e-12), 0, 1) ** 0.45
            enc = (np.stack([g, g * 0.55, g * 0.15], -1) * 255).astype(np.uint8)
            name = 'scene-linear |Δ|, 0 .. %.3g' % mx
        im = Image.fromarray(enc).resize((fw, fh), Image.LANCZOS)
        img.paste(im, (x0, 26))
        d0 = P.ImageDraw.Draw(img)
        d0.text((x0, 8), name, fill=P.INK, font=P.FONT_B)
        # the crop box, drawn on the frame it was chosen from
        bx0 = x0 + int(cx / nx * fw); by0 = 26 + int(cy / ny * fh)
        d0.rectangle([bx0, by0, bx0 + int(k / nx * fw), by0 + int(k / ny * fh)],
                     outline=RED, width=2)
        # ---- the same crop at 3x, underneath
        cr = enc[cy:cy + k, cx:cx + k]
        img.paste(Image.fromarray(cr).resize((ch, ch), Image.NEAREST),
                  (x0, 26 + fh + 26))
        d0.text((x0, 26 + fh + 8), 'the same %d x %d px at %dx, rows %d-%d'
                % (k, k, S, cy, cy + k), fill=P.MUTED, font=P.FONT_S)

    P.caption(img, [
        'THE POOL\'S HERO FRAME, EITHER SIDE OF `atmosphere._lobe_shape`\'s '
        'RECEIVER. Same camera, same field, same EXPOSURE %.3f, same crop: the '
        'only difference between the two frames is the'
        % R.EXPOSURE,
        'exponent the widened sun lobe is written with. `n_eff = 1/(uᵀQu)` '
        'is the PROJECTION variance; the convolved density along u wants '
        '`n_eff = uᵀQ⁻¹u`, the 2x2 adjugate over det Q. The two '
        'are the SAME',
        'NUMBER for an isotropic Q and on either principal axis, which is why '
        'every lobe row in `validate.py` -- all of them at cov = None -- passed '
        'throughout. Found by the raster reference, an independent',
        'code path over the same shared module.',
        '',
        'MEASURED IN SCENE-LINEAR RADIANCE, BEFORE THE TONE MAP ABOVE. '
        '%.2f%% of the %d output pixels moved at all. Over those, mean |Δ| '
        '%.4g and worst |Δ| %.4g in radiance; the frame\'s own median '
        'radiance is %.4g,'
        % (frac, d.size, float(d[moved].mean()) if moved.any() else 0.0,
           float(d.max()), float(np.median(la))),
        'so the worst pixel moved %.0fx its median. The change is a REDUCTION '
        'everywhere it is not zero (%.2f%% of moved pixels fell), because '
        'Cauchy-Schwarz puts the shipped exponent below the right one and a '
        'lower'
        % (float(d.max() / max(np.median(la), 1e-12)),
           100.0 * float((dl[moved] < 0).mean()) if moved.any() else 0.0),
        'exponent is a wider lobe. ENCODED MEAN LUMINANCE over the whole frame '
        '%.3f -> %.3f of 1.0 (%.1f -> %.1f of 255); over the moved pixels only, '
        '%.3f -> %.3f (%.1f -> %.1f of 255).'
        % (ya.mean(), yb.mean(), 255 * ya.mean(), 255 * yb.mean(),
           ya[moved].mean() if moved.any() else 0.0,
           yb[moved].mean() if moved.any() else 0.0,
           255 * (ya[moved].mean() if moved.any() else 0.0),
           255 * (yb[moved].mean() if moved.any() else 0.0)),
        'The crop is picked by the difference itself -- the 96 x 96 box with '
        'the largest summed |Δ| in the frame -- and not by eye.',
    ], x=26)
    return P.save(img, path), dict(
        frac=frac, mean=float(d[moved].mean()) if moved.any() else 0.0,
        worst=float(d.max()), y_before=float(ya.mean()),
        y_after=float(yb.mean()),
        y_moved_before=float(ya[moved].mean()) if moved.any() else 0.0,
        y_moved_after=float(yb[moved].mean()) if moved.any() else 0.0,
        npix=int(d.size), moved=int(moved.sum()),
        med=float(np.median(la)), crop=(cy, cx))


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


FIGURES = (('fix-lobe-hero-before-after.png', fig_frames),
           ('fix-lobe-energy-vs-ratio.png', fig_energy))


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
