"""WAVE 10 -- WHICH SIDE OF THE INTERFACE THE BED'S ALBEDO LIVES ON.

The measurement and the evidence for gap 8 of `README-beach.md`'s wave-9 list:
"the bed under the water is 1.24-1.40x too bright", reported by wave 8 in `L9`
and deliberately not patched.

WHAT THIS FILE DOES AND WHAT IT REFUSES TO DO. It renders bar J's frame TWICE
off the same bay, the same camera, the same instant and the same everything
except ONE ARRAY -- `Water.rho_lut`, the bed's apparent-albedo ladder -- and
measures the difference in SCENE-LINEAR RADIANCE off the buffer. It never opens
a PNG to get a number. The PNGs it writes are the evidence, not the instrument.

THE REGION IS THE HARD PART AND IT IS STATED RATHER THAN CHOSEN. The largest of
the three distortions this project has recorded in its own measurements was a
REGION THAT DID NOT CONTAIN THE PHENOMENON -- ahead of the tone curve, ahead of
the exposure. The bed's light is a minority term over most of bar J's water:
the far sea is 90% airlight, the mid sea is mostly a mirrored sky, and the surf
is a foam deck with a plume under it. Average a bed factor over "the water" and
it comes back diluted by a factor that has nothing to do with the bed.

So the region is defined by the phenomenon and computed per pixel from the
shader's OWN returns, before any figure is drawn:

    R = { water pixels : the bed's own contribution to the pixel's radiance,
          after the plume, the foam deck and the air, is at least half of what
          that pixel carries }

-- "the bed is more than half of what you are looking at". The threshold is
declared and the whole sweep of it is reported beside the number, so the
reader can see the answer is not a property of 0.5. The region is DRAWN on the
frame in the figure, so it is auditable.

Both the region's number and the whole-water-mask number are printed, because
the ratio between them IS the dilution the region exists to remove.
"""
import math
import os
import pickle
import sys
import time

import numpy as np

import beach as B
import beach_optics as BO
import beach_plot as P
import beach_render as BR
import optics as OPT
from PIL import Image, ImageDraw

OUT = BR.OUT
CACHE = os.environ.get('S10_CACHE', '/tmp/s10_bay.pkl')
CH = ((196, 66, 60), (52, 132, 74), (58, 104, 190))
CHN = ('R', 'G', 'B')


# --------------------------------------------------------------- the two beds
def rho_ladder(arg, w):
    """`Water.rho_lut` rebuilt with an arbitrary bed argument. One line of the
    render, isolated, so the two frames differ by exactly this array."""
    return np.stack([
        OPT.rho_water(arg, math.sin(math.radians(BR.SUN_EL)), float(dd),
                      absorb=w.io_clear['a'] + w.io_clear['b_b'])
        for dd in w.dep_lut])


def build_bay():
    if os.path.exists(CACHE):
        with open(CACHE, 'rb') as f:
            return pickle.load(f)
    bay = B.run_bay(embay=True)
    try:
        with open(CACHE, 'wb') as f:
            pickle.dump(bay, f)
    except OSError:
        pass
    return bay


# ------------------------------------------------------------ the measurement
def bed_share(L, ex):
    """The bed's own contribution to each water pixel, and its share of it.

    EXACT, not estimated. `shade_water` returns `R_bed_seen` -- the bed's
    reflectance after the plume's adding series -- so the bed's radiance at the
    surface is the same three factors the shader applies to the whole column,
    with R_tot replaced by R_bed_seen. The foam deck multiplies it by (1 - cov)
    and the air by its own transmittance, which is affine and therefore exact
    on a difference.
    """
    sh, mw = ex['water'], ex['water_mask']
    Rf = OPT.fresnel(sh['cos_v'][0])
    L_bed = (OPT.out_of_water(sh['E_dn_w'] * sh['R_bed_seen'][0] / np.pi)
             * (1.0 - Rf) * (1.0 - sh['cov'][0][..., None]))
    D = ex['trace']['D'][mw]
    r = np.linalg.norm(ex['water_P'] - np.asarray(BR_CAMPOS)[None], axis=-1)
    T = np.exp(-r[..., None] * BR.beta_ext(None)[None])
    Lb = L_bed * T                                   # what reaches the film
    full = np.zeros(L.shape)
    full[mw] = Lb
    share = np.zeros(L.shape[:2])
    lum = np.array([.2126, .7152, .0722])
    share[mw] = ((Lb * lum).sum(-1)
                 / np.maximum((L[mw] * lum).sum(-1), 1e-12))
    return full, share, D


BR_CAMPOS = None


def main():
    global BR_CAMPOS
    W, H = (240, 320) if '--fast' in sys.argv else (480, 640)
    bay = build_bay()
    w = BR.Water(bay)
    (_, _, _, camJ, infJ, _, _, _, _) = BR.hero_cameras(w, W, H,
                                                        out=lambda *a: None)
    BR_CAMPOS = camJ.pos
    a_dry, a_wet, a_dif = BR.SAND_DRY, BR.SAND_WET, BR.SAND_WET_DIFF

    frames = {}
    for name, arg in (('shipped', a_wet), ('L9', a_dif), ('fixed', a_dry)):
        w.rho_lut = rho_ladder(arg, w)
        t1 = time.time()
        L, ex = BR.render(camJ, w, 0.0, 'J')
        frames[name] = (L, ex)
        print('%-8s render %.1f s' % (name, time.time() - t1))

    Ls, exs = frames['shipped']
    Lf, exf = frames['fixed']
    L9, ex9 = frames['L9']
    bed_s, share_s, _ = bed_share(Ls, exs)
    bed_f, share_f, _ = bed_share(Lf, exf)
    bed_9, share_9, _ = bed_share(L9, ex9)

    mw = exs['water_mask']
    # THE REGION. Defined on the SHIPPED frame, so the fix cannot choose its own
    # audience -- a region drawn on the corrected frame would be a region the
    # correction selected.
    reg = mw & (share_s >= 0.5)
    print('\nregion: %d px of %d water px of %d frame px  (%.2f%% of frame)'
          % (reg.sum(), mw.sum(), share_s.size, 100.0 * reg.sum() / share_s.size))

    lum = np.array([.2126, .7152, .0722])
    rows = []
    for nm, msk in (('THE REGION (bed >= 50% of the pixel)', reg),
                    ('all water pixels', mw)):
        if msk.sum() == 0:
            continue
        fs = Ls[msk].mean(0)
        ff = Lf[msk].mean(0)
        f9 = L9[msk].mean(0)
        bs, bf = bed_s[msk].mean(0), bed_f[msk].mean(0)
        rows.append((nm, fs, ff, f9, bs, bf))
        print('\n--- %s  (%d px)' % (nm, int(msk.sum())))
        print('  mean pixel radiance, shipped %s' % np.round(fs, 5))
        print('  mean pixel radiance, fixed   %s' % np.round(ff, 5))
        print('  mean pixel radiance, L9      %s' % np.round(f9, 5))
        print('  BED TERM ONLY, shipped       %s' % np.round(bs, 5))
        print('  BED TERM ONLY, fixed         %s' % np.round(bf, 5))
        print('  bed factor fixed/shipped     %s   lum %.4f'
              % (np.round(bf / np.maximum(bs, 1e-12), 4),
                 float((bf * lum).sum() / (bs * lum).sum())))
        print('  bed factor shipped/L9        %s'
              % np.round(bs / np.maximum(bed_9[msk].mean(0), 1e-12), 4))
        print('  PIXEL factor fixed/shipped   %s'
              % np.round(ff / np.maximum(fs, 1e-12), 4))

    # threshold sweep -- the answer must not be a property of 0.5
    print('\nthreshold sweep on the region definition:')
    for thr in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        m = mw & (share_s >= thr)
        if m.sum() < 50:
            continue
        bs, bf = bed_s[m].mean(0), bed_f[m].mean(0)
        print('  bed>=%.0f%%  %6d px   bed factor %s   pixel factor %s'
              % (100 * thr, int(m.sum()), np.round(bf / bs, 4),
                 np.round(Lf[m].mean(0) / Ls[m].mean(0), 4)))

    figures(w, camJ, infJ, Ls, Lf, L9, bed_s, bed_f, reg, mw, share_s)
    return rows


# ---------------------------------------------------------------- the figures
def _outline(rgb, mask, colour=(255, 232, 60)):
    """Draw the measurement region's boundary onto an 8-bit image."""
    m = mask
    e = np.zeros_like(m)
    e[1:, :] |= m[1:, :] ^ m[:-1, :]
    e[:-1, :] |= m[1:, :] ^ m[:-1, :]
    e[:, 1:] |= m[:, 1:] ^ m[:, :-1]
    e[:, :-1] |= m[:, 1:] ^ m[:, :-1]
    out = rgb.copy()
    out[e] = colour
    return out


def _diverging(v, vmax):
    """Signed difference to RGB: blue negative, white zero, red positive."""
    t = np.clip(v / max(vmax, 1e-12), -1.0, 1.0)
    r = np.where(t > 0, 255, 255 + t * (255 - 58))
    g = np.where(t > 0, 255 - t * (255 - 66), 255 + t * (255 - 104))
    b = np.where(t > 0, 255 - t * (255 - 60), 255)
    return np.stack([r, g, b], -1).astype(np.uint8)


def figures(w, cam, inf, Ls, Lf, L9, bed_s, bed_f, reg, mw, share):
    lum = np.array([.2126, .7152, .0722])
    dif = (Lf - Ls)
    dl = (dif * lum).sum(-1)
    vmax = float(np.percentile(np.abs(dl[mw]), 99.0)) if mw.any() else 1.0

    H, Wpx = Ls.shape[:2]
    sc = 300.0 / Wpx
    ph, pw = int(H * sc), int(Wpx * sc)

    img = P.canvas(3 * pw + 200, ph + 300)
    d = ImageDraw.Draw(img)

    def paste(arr, x, y, title):
        im = Image.fromarray(np.asarray(arr, np.uint8)).resize((pw, ph),
                                                              Image.BILINEAR)
        img.paste(im, (x, y))
        d.rectangle([x, y, x + pw, y + ph], outline=P.INK)
        d.text((x, y - 18), title, fill=P.INK, font=P.FONT_B)

    disp_s = _outline(_srgb(Ls), reg)
    disp_f = _outline(_srgb(Lf), reg)
    paste(disp_s, 40, 60, 'BEFORE  rho_bed = wet_albedo(SAND_DRY)')
    paste(disp_f, 60 + pw, 60, 'AFTER  rho_bed = SAND_DRY')
    paste(_diverging(dl, vmax), 80 + 2 * pw, 60,
          'AFTER - BEFORE, signed, luminance')
    d.text((40, 28), 'WAVE 10 - THE SUBMERGED BED, AND WHICH SIDE OF THE '
           'INTERFACE ITS ALBEDO LIVES ON', fill=P.INK, font=P.FONT_B)
    d.text((40, 46), 'bar J framing, scene-linear radiance off the buffer; '
           'yellow outline = the measurement region (bed >= 50%% of the pixel, '
           '%d px)' % int(reg.sum()), fill=P.MUTED, font=P.FONT_S)

    # --- the colour bar, in ABSOLUTE radiance
    bx0, by0 = 80 + 2 * pw, 60 + ph + 26
    bw, bh = pw, 16
    ramp = _diverging(np.linspace(-vmax, vmax, bw)[None].repeat(bh, 0), vmax)
    img.paste(Image.fromarray(ramp), (bx0, by0))
    d.rectangle([bx0, by0, bx0 + bw, by0 + bh], outline=P.INK)
    for f, lab in ((0.0, '%+.3f' % -vmax), (0.5, '0'), (1.0, '%+.3f' % vmax)):
        d.text((bx0 + f * bw, by0 + bh + 3), lab, fill=P.MUTED, font=P.FONT_S,
               anchor='ma')
    d.text((bx0 + bw / 2, by0 + bh + 20),
           'DELTA radiance, W m^-2 sr^-1 (luminance-weighted), scene-linear',
           fill=P.INK, font=P.FONT_S, anchor='ma')

    # --- the per-band factors, as a bar chart in absolute radiance
    ax = P.Axes(img, (40, 60 + ph + 40, 40 + 2 * pw - 20, 60 + ph + 200),
                (-0.6, 2.6), (0.0, float(max(bed_f[reg].mean(0).max(),
                                             bed_s[reg].mean(0).max())) * 1.25),
                title='THE BED TERM ALONE, over the region  (measured)',
                xlabel='', ylabel='radiance, W m^-2 sr^-1')
    ax.frame(yticks=np.linspace(0, ax.ylim[1], 5))
    bs, bf = bed_s[reg].mean(0), bed_f[reg].mean(0)
    for c in range(3):
        ax.d.rectangle([float(ax.px(c - 0.30)), float(ax.py(bs[c])),
                        float(ax.px(c - 0.02)), float(ax.py(0))],
                       fill=P.MUTED)
        ax.d.rectangle([float(ax.px(c + 0.02)), float(ax.py(bf[c])),
                        float(ax.px(c + 0.30)), float(ax.py(0))], fill=CH[c])
        ax.text(c, bf[c], ' x%.3f' % (bf[c] / max(bs[c], 1e-12)), P.INK,
                anchor='mb')
        ax.text(c, -ax.ylim[1] * 0.06, CHN[c], P.INK, anchor='mt')
    P.legend(ax, ((P.MUTED, 'BEFORE  wet_albedo(SAND_DRY) passed as rho_bed'),
                  (CH[1], 'AFTER  SAND_DRY passed as rho_bed')),
             1.4, ax.ylim[1] * 0.92)

    P.caption(img, [
        'MEASURED, scene-linear, off the radiance buffer -- no PNG is read. '
        'Frames differ by ONE array: Water.rho_lut, the bed`s apparent-albedo '
        'ladder. Everything else is identical.',
        'REGION (derived from the shipped frame, so the fix does not choose '
        'its own audience): water pixels whose BED TERM -- after the plume`s '
        'adding series, the foam deck and the air -- is >= 50%% of the pixel.',
        'DERIVED: optics.rho_water already carries the air/water interface '
        'both ways; its rho_bed argument is a WATER-SIDE reflectance. '
        'wet_albedo(a) is an AIR-SIDE apparent albedo of the same substrate.',
        'The identity that settles it, checked to 5e-5 in validate.py: '
        'wet_albedo(a) - R_EXT == (1-R_EXT) a slab_esc(0) trap_gain(a,0) -- '
        'wet_albedo IS rho_water at zero depth. Passing one to the other '
        'composes the form with itself.',
        'per-band factor on the bed term: %s   (the correction is BRIGHTER, '
        'not darker; L9 reported the sign backwards)'
        % np.round(bf / np.maximum(bs, 1e-12), 4),
    ], x=40, y=60 + ph + 218)
    P.save(img, '%s/s10-optics-bed.png' % OUT)
    print('wrote %s/s10-optics-bed.png' % OUT)

    ladder_figure(w)


def _srgb(L):
    """`beach_render._save`'s own display transform -- ONE exposure key and a
    gamma, the same for both frames, so the pair is comparable to the eye.
    DISPLAY ONLY: every number in this file is taken off `L` before this runs,
    and nothing is ever read back out of an image."""
    x = np.clip(np.asarray(L, float) / max(BR.WHITE, 1e-9), 0.0, 1.0)
    return np.clip((x ** (1.0 / 2.2)) * 255.0 + 0.5, 0, 255).astype(np.uint8)


def ladder_figure(w):
    """The three candidate bed arguments, put through the SAME rho_water on the
    SAME depth ladder, in absolute apparent albedo. Derived, not measured."""
    img = P.canvas(1080, 620)
    d = ImageDraw.Draw(img)
    d.text((40, 24), 'WAVE 10 - THE THREE CANDIDATE BED ARGUMENTS, THROUGH ONE '
           'CLOSED FORM', fill=P.INK, font=P.FONT_B)
    d.text((40, 44), 'optics.rho_water(rho_bed, sin 21 deg, d, absorb = this '
           'coast`s a + b_b). DERIVED -- no render enters this panel.',
           fill=P.MUTED, font=P.FONT_S)
    deps = np.geomspace(0.05, 12.0, 200)
    cs = math.sin(math.radians(BR.SUN_EL))
    ab = w.io_clear['a'] + w.io_clear['b_b']
    curves = {}
    for nm, arg in (('shipped', BR.SAND_WET), ('L9', BR.SAND_WET_DIFF),
                    ('fixed', BR.SAND_DRY)):
        curves[nm] = np.stack([OPT.rho_water(arg, cs, float(dd), absorb=ab)
                               for dd in deps])
    ax = P.Axes(img, (90, 90, 520, 470), (0.0, 12.0),
                (0.0, float(curves['fixed'].max()) * 1.08),
                title='apparent albedo of the column, green band',
                xlabel='water depth, m', ylabel='rho_water  (unitless)')
    ax.frame(xticks=[0, 2, 4, 6, 8, 10, 12],
             yticks=np.linspace(0, ax.ylim[1], 6), yfmt='%.2f')
    ax.line(deps, curves['shipped'][:, 1], P.MUTED, 2)
    ax.line(deps, curves['L9'][:, 1], (150, 100, 190), 2, dash=(7, 5))
    ax.line(deps, curves['fixed'][:, 1], CH[1], 3)
    P.legend(ax, ((P.MUTED, 'shipped: rho_bed = wet_albedo(a)   [waves 4-9]'),
                  ((150, 100, 190), 'L9`s proposal: rho_bed = wet_albedo(a) '
                   '- R_EXT'),
                  (CH[1], 'DERIVED: rho_bed = a = SAND_DRY')),
             4.6, ax.ylim[1] * 0.95)

    ax2 = P.Axes(img, (620, 90, 1040, 470), (0.0, 12.0), (0.85, 1.45),
                 title='per-band correction factor  fixed / shipped',
                 xlabel='water depth, m', ylabel='factor (unitless)')
    ax2.frame(xticks=[0, 2, 4, 6, 8, 10, 12],
              yticks=[0.9, 1.0, 1.1, 1.2, 1.3, 1.4], yfmt='%.2f')
    ax2.hline(1.0, P.MUTED)
    for c in range(3):
        ax2.line(deps, curves['fixed'][:, c] / curves['shipped'][:, c], CH[c], 2)
        ax2.line(deps, curves['shipped'][:, c] / curves['L9'][:, c], CH[c], 1,
                 dash=(4, 4))
    P.legend(ax2, ((CH[0], 'R'), (CH[1], 'G'), (CH[2], 'B')), 0.4, 1.41)
    ax2.text(6.2, 1.40, 'solid: the correction this wave makes (BRIGHTER)',
             P.INK)
    ax2.text(6.2, 1.375, 'dashed: the factor L9 reported (wrong reference)',
             P.MUTED)

    P.caption(img, [
        'DERIVED. SAND_DRY = (0.45, 0.39, 0.30) `?`; wet_albedo(SAND_DRY) = '
        '(%s); its diffuse half = (%s).'
        % (', '.join('%.4f' % v for v in BR.SAND_WET),
           ', '.join('%.4f' % v for v in BR.SAND_WET_DIFF)),
        'L9 measured the ratio between its own proposal and the shipped value '
        '(1.236 / 1.285 / 1.398) and read it as "the bed is too BRIGHT". Both '
        'of those arguments have already crossed the interface;',
        'the ratio between them is real and its REFERENCE is wrong. Against '
        'the substrate albedo the shipped bed is too DARK by 1.30 / 1.32 / '
        '1.27 at 3 m, and the per-band ORDER differs -- which is what '
        'separates the two hypotheses.',
    ], x=40, y=500)
    P.save(img, '%s/s10-optics-ladder.png' % OUT)
    print('wrote %s/s10-optics-ladder.png' % OUT)


if __name__ == '__main__':
    main()
