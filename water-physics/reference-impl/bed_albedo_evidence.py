"""WAVE 10 -- WHICH SIDE OF THE INTERFACE THE BED'S ALBEDO LIVES ON.

The measurement and the evidence for gap 8 of `README-beach.md`'s wave-9 list:
"the bed under the water is 1.24-1.40x too bright", reported by wave 8 in `L9`
and deliberately not patched.

WHAT THIS FILE DOES AND WHAT IT REFUSES TO DO. It renders bar J's frame TWICE
off the same bay, the same camera, the same instant and the same everything
except ONE ARRAY -- `Water.rho_lut`, the bed's apparent-albedo ladder -- and
measures the difference in SCENE-LINEAR RADIANCE off the buffer. It never opens
a PNG to get a number. The PNGs it writes are the evidence, not the instrument.

THE REGION IS THE HARD PART AND IT IS STATED RATHER THAN CHOSEN. The largest
of the three distortions this project has recorded in its own measurements was
a REGION THAT DID NOT CONTAIN THE PHENOMENON -- ahead of the tone curve, ahead
of the exposure. So the region here is defined by the BED and by nothing else:

    R = { water pixels standing over less than 1 m of water }

-- a depth threshold, computed off the bathymetry, identical under both
hypotheses, drawn on the frame, and swept. It cannot be a threshold on the
bed's own brightness without the fix choosing its own audience, and it cannot
be "all the water" without measuring the open sea.

AND THE FIRST WRITING OF THIS FILE ASKED FOR "pixels where the bed is at least
half of what you are looking at". THAT REGION IS EMPTY, in every frame this
project owns, and finding that out is most of the verdict: the bed's own light
never exceeds 0.8% of a water pixel in bar J and 0.02% in the close surf frame
F. So a control is built beside it -- the same two renders with the suspended
sediment, the entrained air and the foam deck switched off, three fields zeroed
and nothing else touched -- because a near-zero measurement is worthless until
zero has been shown to be reachable, and the control is where the bed IS the
picture.

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


def clear_the_water(w):
    """THE CONTROL, and it is three fields zeroed and nothing else.

    The suspended sediment, the entrained air and the surface foam deck all
    hide the bed, and in this scene they hide it completely. Switching all
    three off leaves the SAME bay, the SAME camera, the SAME sun, the SAME
    instant and the SAME bed -- and a water column that is the clear coastal
    water mass alone. It is not a prettier render; it is the calibration that
    turns "the correction moves nothing" into a number, because it shows what
    the correction is worth where the bed can be seen at all.
    """
    io = w.io_clear
    col = BO.column_reflectance(io['a'], io['b_b'], w.d,
                                io['a'], io['b_b'] * 0.0,
                                np.zeros_like(w.d))
    w.R_col, w.t_col, w.c_bar = col['R'], col['t_col'], col['c_bar']
    w.plume_on = False
    w.foam_on = False
    return w


def main():
    global BR_CAMPOS
    W, H = (240, 320) if '--fast' in sys.argv else (480, 640)
    bay = build_bay()
    w = BR.Water(bay)
    (_, _, _, camJ, infJ, _, _, _, _) = BR.hero_cameras(w, W, H,
                                                        out=lambda *a: None)
    BR_CAMPOS = camJ.pos
    a_dry, a_wet, a_dif = BR.SAND_DRY, BR.SAND_WET, BR.SAND_WET_DIFF
    ARGS = (('shipped', a_wet), ('L9', a_dif), ('fixed', a_dry))

    frames = {}
    for name, arg in ARGS:
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
    dep = np.zeros(mw.shape)
    dep[mw] = exs['water']['dep'][0]
    reg = mw & (dep < 1.0)
    lum = np.array([.2126, .7152, .0722])

    print('\n=================== BAR J, THE HERO FRAME')
    print('water %d px of %d; REGION (depth < 1 m) %d px = %.2f%% of frame'
          % (mw.sum(), mw.size, reg.sum(), 100.0 * reg.sum() / mw.size))
    print('the bed\'s own share of a water pixel: max %.5f, p99 %.5f'
          % (share_s[mw].max(), np.percentile(share_s[mw], 99)))
    print('  -- so the region "bed >= 50%% of the pixel" is EMPTY, and that is '
          'the verdict on what gap 8 was worth in this frame.')
    _report('THE REGION: bar J, water shallower than 1 m', reg, Ls, Lf, L9,
            bed_s, bed_f, bed_9, lum)
    _report('all water pixels (the dilution, for comparison)', mw, Ls, Lf, L9,
            bed_s, bed_f, bed_9, lum)
    print('\ndepth-threshold sweep on the region:')
    for thr in (0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0):
        m = mw & (dep < thr)
        if m.sum() < 50:
            continue
        bs, bf = bed_s[m].mean(0), bed_f[m].mean(0)
        print('  d < %4.2f m  %6d px   bed factor %s   bed share of pixel '
              '%.5f' % (thr, int(m.sum()), np.round(bf / bs, 4),
                        float((bs * lum).sum()
                              / (Ls[m].mean(0) * lum).sum())))

    # ------------------------------------------------ THE CONTROL
    print('\n=================== THE CONTROL: sediment, air and foam OFF')
    clear_the_water(w)
    cframes = {}
    for name, arg in ARGS:
        w.rho_lut = rho_ladder(arg, w)
        L, ex = BR.render(camJ, w, 0.0, 'J')
        cframes[name] = (L, ex)
    cLs, cexs = cframes['shipped']
    cLf, cexf = cframes['fixed']
    cL9, _ = cframes['L9']
    cbed_s, cshare_s, _ = bed_share(cLs, cexs)
    cbed_f, _, _ = bed_share(cLf, cexf)
    cbed_9, _, _ = bed_share(cL9, cframes['L9'][1])
    print('the bed\'s own share of a water pixel, control: max %.4f p99 %.4f'
          % (cshare_s[mw].max(), np.percentile(cshare_s[mw], 99)))
    creg = mw & (dep < 1.0)
    _report('THE CONTROL, same region', creg, cLs, cLf, cL9, cbed_s, cbed_f,
            cbed_9, lum)

    global FACTOR_L9
    FACTOR_L9 = tuple(bed_s[reg].mean(0) / np.maximum(bed_9[reg].mean(0),
                                                      1e-14))
    figures(w, camJ, Ls, Lf, bed_s, bed_f, reg, mw, dep,
            cLs, cLf, cbed_s, cbed_f, cshare_s)
    ladder_figure(w)


def _report(nm, msk, Ls, Lf, L9, bed_s, bed_f, bed_9, lum):
    if msk.sum() == 0:
        print('\n--- %s: EMPTY' % nm)
        return
    fs, ff, f9 = Ls[msk].mean(0), Lf[msk].mean(0), L9[msk].mean(0)
    bs, bf, b9 = bed_s[msk].mean(0), bed_f[msk].mean(0), bed_9[msk].mean(0)
    print('\n--- %s  (%d px)' % (nm, int(msk.sum())))
    print('  pixel radiance   shipped %s' % np.round(fs, 5))
    print('                   fixed   %s' % np.round(ff, 5))
    print('  BED TERM ONLY    shipped %s' % np.round(bs, 6))
    print('                   L9      %s' % np.round(b9, 6))
    print('                   fixed   %s' % np.round(bf, 6))
    print('  bed factor  fixed/shipped %s   lum %.4f'
          % (np.round(bf / np.maximum(bs, 1e-14), 4),
             float((bf * lum).sum() / max((bs * lum).sum(), 1e-14))))
    print('  bed factor  shipped/L9    %s   <- the 1.24-1.40x wave 8 reported'
          % np.round(bs / np.maximum(b9, 1e-14), 4))
    print('  PIXEL factor fixed/shipped %s' % np.round(ff / fs, 5))
    print('  the bed is %.4f%% of the pixel'
          % (100.0 * (bs * lum).sum() / max((fs * lum).sum(), 1e-14)))


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


FACTOR_L9 = (1.0, 1.0, 1.0)


def _wrap(txt, n):
    out, line = [], ''
    for wd in txt.split():
        if len(line) + len(wd) + 1 > n:
            out.append(line)
            line = wd
        else:
            line = (line + ' ' + wd).strip()
    if line:
        out.append(line)
    return out


def figures(w, cam, Ls, Lf, bed_s, bed_f, reg, mw, dep,
            cLs, cLf, cbed_s, cbed_f, cshare):
    lum = np.array([.2126, .7152, .0722])
    dl = ((Lf - Ls) * lum).sum(-1)
    cdl = ((cLf - cLs) * lum).sum(-1)
    vmax = float(np.abs(dl[mw]).max())
    cvmax = float(np.abs(cdl[mw]).max())
    share_max = float(((bed_s[mw] * lum).sum(-1)
                       / (Ls[mw] * lum).sum(-1)).max())

    H, Wpx = Ls.shape[:2]
    pw = 250
    ph = int(H * pw / Wpx)
    img = P.canvas(4 * pw + 200, ph + 700)
    d = ImageDraw.Draw(img)

    def paste(arr, x, y, title, sub):
        im = Image.fromarray(np.asarray(arr, np.uint8)).resize((pw, ph),
                                                               Image.BILINEAR)
        img.paste(im, (x, y))
        d.rectangle([x, y, x + pw, y + ph], outline=P.INK)
        d.text((x, y - 32), title, fill=P.INK, font=P.FONT_B)
        d.text((x, y - 15), sub, fill=P.MUTED, font=P.FONT_S)

    def grey(L, msk):
        """Non-water pixels of a difference panel, so the frame is readable."""
        g = _srgb(L).astype(float).mean(-1)
        g = 235.0 + 0.06 * (g - 128.0)
        return np.stack([g, g, g], -1)

    y0 = 150
    x = [80 + k * (pw + 12) for k in range(4)]
    paste(_outline(_srgb(Ls), reg), x[0], y0, 'BEFORE',
          'rho_bed = wet_albedo(SAND_DRY).  bar J.')
    paste(_outline(_srgb(Lf), reg), x[1], y0, 'AFTER',
          'rho_bed = SAND_DRY.  ONE array differs.')
    dif = np.where(mw[..., None], _diverging(dl, vmax), grey(Ls, mw))
    paste(dif, x[2], y0, 'AFTER - BEFORE, signed',
          'luminance, scene-linear.  grey = not water')
    paste(_outline(_srgb(cLf), reg), x[3], y0, 'THE CONTROL, AFTER',
          'sediment, air and foam switched OFF')

    d.text((80, 26), 'WAVE 10  -  THE SUBMERGED BED, AND WHICH SIDE OF THE '
           'AIR/WATER INTERFACE ITS ALBEDO LIVES ON', fill=P.INK, font=P.FONT_B)
    for i, ln in enumerate([
            'MEASURED in scene-linear radiance off the buffer -- no PNG is '
            'read for any number here.  The first three frames differ by ONE '
            'array, Water.rho_lut, and by nothing else.',
            'REGION (DERIVED from the bathymetry, identical under both '
            'hypotheses, drawn on the frame): water pixels standing over less '
            'than 1 m of water -- %d px, %.2f%% of frame.'
            % (int(reg.sum()), 100.0 * reg.sum() / mw.size),
            'A region defined on the bed\'s own brightness would let the fix '
            'choose its audience.  The region first asked for -- "pixels '
            'where the bed is at least half of what you see" -- is EMPTY '
            'here, and that is half the verdict.']):
        for j, sub in enumerate(_wrap(ln, 168)):
            d.text((80, 48 + 16 * (i + j)), sub, fill=P.MUTED, font=P.FONT_S)

    # ---- the two colour bars, in ABSOLUTE radiance
    bh = 15
    by = y0 + ph + 14
    for bx, vm, lab, sub in ((x[2], vmax, 'DELTA radiance, W m^-2 sr^-1',
                              'the water in this region sits at %.2f'
                              % float((Ls[reg].mean(0) * lum).sum())),
                             (x[3], cvmax, 'CONTROL: DELTA radiance, same '
                              'units', 'the bed reaches %.0f%% of a pixel '
                              'here, against %.2f%% in the hero frame'
                              % (100 * float(cshare[mw].max()),
                                 100 * share_max))):
        img.paste(Image.fromarray(_diverging(
            np.linspace(-vm, vm, pw)[None].repeat(bh, 0), vm)), (bx, by))
        d.rectangle([bx, by, bx + pw, by + bh], outline=P.INK)
        for f, t, an in ((0.0, '%+.4f' % -vm, 'la'), (0.5, '0', 'ma'),
                         (1.0, '%+.4f' % vm, 'ra')):
            d.text((bx + f * pw, by + bh + 3), t, fill=P.MUTED, font=P.FONT_S,
                   anchor=an)
        d.text((bx + pw / 2, by + bh + 20), lab, fill=P.INK, font=P.FONT_S,
               anchor='ma')
        for j, ln in enumerate(_wrap(sub, 44)):
            d.text((bx + pw / 2, by + bh + 36 + 14 * j), ln, fill=P.MUTED,
                   font=P.FONT_S, anchor='ma')

    # ---- the per-band factors, ABSOLUTE, hero and control
    ay = y0 + ph + 150
    bs, bf = bed_s[reg].mean(0), bed_f[reg].mean(0)
    cs_, cf_ = cbed_s[reg].mean(0), cbed_f[reg].mean(0)
    for k, (sb, fb, ttl, sc, un) in enumerate((
            (bs, bf, 'THE BED TERM ALONE  -  hero frame, over the region',
             1e3, '10^-3 W m^-2 sr^-1'),
            (cs_, cf_, 'THE BED TERM ALONE  -  control, same region',
             1.0, 'W m^-2 sr^-1'))):
        x0 = 150 + k * (2 * pw + 130)
        top = float(max(fb.max(), sb.max())) * sc * 1.30
        ax = P.Axes(img, (x0, ay, x0 + 2 * pw - 90, ay + 175), (-0.6, 2.6),
                    (0.0, top), title=ttl, xlabel='', ylabel=un)
        ax.frame(yticks=np.linspace(0, top, 5), yfmt='%.3g')
        for c in range(3):
            ax.d.rectangle([float(ax.px(c - 0.30)), float(ax.py(sb[c] * sc)),
                            float(ax.px(c - 0.02)), float(ax.py(0))],
                           fill=P.MUTED)
            ax.d.rectangle([float(ax.px(c + 0.02)), float(ax.py(fb[c] * sc)),
                            float(ax.px(c + 0.30)), float(ax.py(0))],
                           fill=CH[c])
            ax.text(c, fb[c] * sc, ' x%.3f' % (fb[c] / max(sb[c], 1e-14)),
                    P.INK, anchor='mb')
            ax.text(c, -top * 0.07, CHN[c], P.INK, anchor='mt')
        P.legend(ax, ((P.MUTED, 'BEFORE   wet_albedo(SAND_DRY) as rho_bed'),
                      (CH[1], 'AFTER   SAND_DRY as rho_bed')),
                 -0.5, top * 0.96)

    cap = [
        '[DERIVED]  optics.rho_water crosses the air/water interface twice '
        'INSIDE itself -- (1 - fresnel) going in, slab_esc coming out -- and '
        'rho_bed sits between the crossings.  So rho_bed is a WATER-SIDE '
        'reflectance.  wet_albedo(a) is the AIR-SIDE apparent albedo of the '
        'same substrate and its own argument is the water-side one.',
        '[DERIVED]  The identity that settles it, exact, and a row in both '
        'suites:   wet_albedo(a) - R_EXT  ==  (1 - R_EXT) a slab_esc(0) '
        'trap_gain(a, 0)   -- wet_albedo IS rho_water with the water column '
        'set to zero.  Passing one to the other composes the closed form with '
        'itself: the trapped series twice, the interface four times.',
        '[CITED]  R_EXT = 6.669% diffuse from outside against R_INT = '
        '47.617% from inside, a ratio of 7.14, tied by Walsh\'s relation '
        'n^2 (1 - R_INT) = 1 - R_EXT.  An extra crossing is never a rounding '
        'error.',
        '[MEASURED]  The correction makes the bed BRIGHTER by %s per band.  '
        'README-beach L9 reported 1.236 / 1.285 / 1.398 and read it as "the '
        'bed is too bright": that ratio is reproduced here exactly (%s) and '
        'its REFERENCE is one interface off -- it compares two air-side '
        'quantities to each other.'
        % (' / '.join('%.3f' % v for v in bf / np.maximum(bs, 1e-14)),
           ' / '.join('%.3f' % v for v in FACTOR_L9)),
        '[MEASURED]  And the other half of the verdict: in the hero frame the '
        'bed is at most %.2f%% of any water pixel, so this correction moves '
        'bar J by %.5f W m^-2 sr^-1 against water at %.2f.  The wave-8 gap '
        'list priced it at "the teal rung and the surf, 12.3%% and 2.3%% of '
        'frame J" -- that is the AREA of those rungs, not the bed\'s share of '
        'them.  The teal rung is the SUSPENSION.'
        % (100 * share_max, float(np.abs(dl[reg]).max()),
           float((Ls[reg].mean(0) * lum).sum())),
    ]
    yy = ay + 212
    for para in cap:
        for ln in _wrap(para, 176):
            d.text((80, yy), ln, fill=P.INK, font=P.FONT_S)
            yy += 15
        yy += 4
    P.save(img, '%s/s10-optics-bed.png' % OUT)
    print('wrote %s/s10-optics-bed.png' % OUT)


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
    img = P.canvas(1240, 700)
    d = ImageDraw.Draw(img)
    d.text((60, 24), 'WAVE 10  -  THE THREE CANDIDATE BED ARGUMENTS, THROUGH '
           'ONE CLOSED FORM', fill=P.INK, font=P.FONT_B)
    d.text((60, 46), 'optics.rho_water(rho_bed, sin 21 deg, d, absorb = this '
           'coast\'s a + b_b).  DERIVED -- no render enters this panel.',
           fill=P.MUTED, font=P.FONT_S)
    deps = np.geomspace(0.05, 12.0, 200)
    cs = math.sin(math.radians(BR.SUN_EL))
    ab = w.io_clear['a'] + w.io_clear['b_b']
    cur = {}
    for nm, arg in (('shipped', BR.SAND_WET), ('L9', BR.SAND_WET_DIFF),
                    ('fixed', BR.SAND_DRY)):
        cur[nm] = np.stack([OPT.rho_water(arg, cs, float(dd), absorb=ab)
                            for dd in deps])
    PURPLE = (150, 100, 190)
    ax = P.Axes(img, (110, 100, 570, 470), (0.0, 12.0),
                (0.0, float(cur['fixed'].max()) * 1.10),
                title='apparent albedo of the column, green band',
                xlabel='water depth, m', ylabel='rho_water  (unitless)')
    ax.frame(xticks=[0, 2, 4, 6, 8, 10, 12],
             yticks=np.linspace(0, ax.ylim[1], 6), yfmt='%.2f')
    ax.line(deps, cur['shipped'][:, 1], P.MUTED, 2)
    ax.line(deps, cur['L9'][:, 1], PURPLE, 2, dash=(7, 5))
    ax.line(deps, cur['fixed'][:, 1], CH[1], 3)
    P.legend(ax, ((CH[1], 'DERIVED: rho_bed = a = SAND_DRY'),
                  (P.MUTED, 'shipped: rho_bed = wet_albedo(a)  [waves 4-9]'),
                  (PURPLE, 'L9\'s proposal: rho_bed = wet_albedo(a) - R_EXT')),
             4.3, ax.ylim[1] * 0.96)

    ax2 = P.Axes(img, (700, 100, 1180, 470), (0.0, 12.0), (0.85, 1.50),
                 title='per-band correction factor',
                 xlabel='water depth, m', ylabel='factor (unitless)')
    ax2.frame(xticks=[0, 2, 4, 6, 8, 10, 12],
              yticks=[0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5], yfmt='%.2f')
    ax2.hline(1.0, P.MUTED)
    for c in range(3):
        ax2.line(deps, cur['fixed'][:, c] / cur['shipped'][:, c], CH[c], 3)
        ax2.line(deps, cur['shipped'][:, c] / cur['L9'][:, c], CH[c], 1,
                 dash=(4, 4))
    P.legend(ax2, ((CH[0], 'R'), (CH[1], 'G'), (CH[2], 'B')), 0.35, 1.475)
    ax2.text(2.2, 1.475, 'SOLID: the correction this wave makes -- the bed '
             'gets BRIGHTER', P.INK)
    ax2.text(2.2, 1.448, 'DASHED: the ratio L9 reported, between two air-side '
             'quantities', P.MUTED)
    ax2.text(2.2, 1.421, 'they cross: the solid peaks in GREEN, the dashed in '
             'BLUE -- the separating row', P.MUTED)

    cap = [
        '[DERIVED]  SAND_DRY = (0.45, 0.39, 0.30) `?`;  wet_albedo(SAND_DRY) = '
        '(0.3473, 0.3008, 0.2373);  its diffuse half = (0.2811, 0.2342, '
        '0.1698).  All three are put through the SAME rho_water, so the three '
        'curves differ by their ARGUMENT and by nothing else.',
        '[MEASURED]  L9 measured the ratio between its own proposal and the '
        'shipped value -- 1.236 / 1.285 / 1.398 -- and read it as "the bed is '
        'too BRIGHT".  Both of those arguments have already crossed the '
        'interface, so the ratio between them is real and its REFERENCE is '
        'one interface off.',
        '[DERIVED]  Against the substrate albedo the shipped bed is too DARK '
        'by 1.298 / 1.315 / 1.270 at 3 m.  The two hypotheses are the same '
        'SIZE and opposite in SPECTRAL ORDER, which is what separates them '
        'with no coefficient in the comparison: L9\'s ratio is '
        'wet_albedo/(wet_albedo - R_EXT), largest where R_EXT is the largest '
        'share of a dark band -- BLUE.',
        '[DERIVED]  The real correction is the doubled trapped series '
        '1/(1 - a R_INT) carried through the column, largest where the bed is '
        'brightest AND the water most transparent -- GREEN.',
        '[`?`]  What is NOT derived and is left open: the substrate\'s '
        'reflectance IN WATER is not its reflectance in air.  A quartz grain '
        'in water has an index contrast of 1.55/1.334 rather than 1.55/1.00, '
        'so it scatters less and the pack absorbs more (Angstrom 1925; Lekner '
        '& Dorf 1988).  Using SAND_DRY for both is the SAME identification '
        'wet_albedo(SAND_DRY) already makes, so this is consistency and not a '
        'new approximation -- and the direction of its error is known: the '
        'true submerged bed is slightly DARKER than the green curve.',
    ]
    yy = 512
    for para in cap:
        for ln in _wrap(para, 182):
            d.text((60, yy), ln, fill=P.INK, font=P.FONT_S)
            yy += 15
        yy += 4
    P.save(img, '%s/s10-optics-ladder.png' % OUT)
    print('wrote %s/s10-optics-ladder.png' % OUT)


if __name__ == '__main__':
    main()
