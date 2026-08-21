"""WAVE 18's evidence: the glitter path before and after the realisation.

    python3 glitter_evidence.py [OUTDIR]

TWO FIGURES AND THEY ANSWER DIFFERENT QUESTIONS.

  `s18-glitter-1to1`   the picture. A 1:1 crop of frame K's glitter path with
                       the sub-footprint slope field OFF and ON -- one flag,
                       the same bed, the same camera, the same instant of
                       phase, the same exposure key. No text in the pixels: a
                       critic must be able to look at it without being told
                       what to see.
  `s18-cv-floor`       the physics behind the picture. The coefficient of
                       variation the partition REQUIRES, as a function of the
                       pixel's footprint, with the render's own measured bands
                       on it. This is the figure that says the granularity is
                       a consequence and not a texture: every point on the
                       curve is `_cv_partition` evaluated on `SlopeRealisation`
                       at one footprint, and nothing in it has been fitted to
                       anything.

THE EXPOSURE, STATED BECAUSE THE FIRST FIGURE IS DISPLAY-REFERRED AND MUST
SAY SO. Both panels are divided by ONE key and taken through ONE gamma, and
the key is the maximum of the BEFORE panel's own green channel over the crop.
So the smooth path just reaches white and nothing in the before panel is
clipped by the choice; whatever the after panel does above or below that is
the change. The key is a display decision and it is identical between the two
panels, which is the only property that matters for a pair. Every NUMBER in
the caption is taken from the scene-linear buffer before this division.
"""
import math
import sys
import time

import numpy as np
from PIL import Image

import beach as B
import beach_optics as BO
import beach_render as R
import beach_plot as P

OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') \
    else '../../gauntlet/sea/evidence'
SS = 2                              # the hero raster's own supersampling
GAMMA = 2.2

# THE CROP. Columns and rows of the FULL-RESOLUTION buffer, so "1:1" means one
# render sample per image pixel and no downsample can smooth structure into
# existence or out of it. It is centred on the path and runs from just under
# the horizon into the near field, which is the range over which the footprint
# changes by two orders of magnitude and therefore the range over which the
# partition predicts the granularity to change at all.
CROP_ROWS = (600, 1080)
CROP_COLS = (540, 900)


def _strip_stats(g, mw, r0, r1, jc, half):
    """mean, sd, CV of a core strip. Scene-linear, off the buffer."""
    blk = g[r0:r1, jc - half:jc + half + 1]
    bm = mw[r0:r1, jc - half:jc + half + 1]
    v = blk[bm]
    return float(v.mean()), float(v.std()), float(v.std() / max(v.mean(), 1e-12))


def _runs(g, mw, r0, r1, jc, half):
    blk = g[r0:r1, jc - half:jc + half + 1]
    bm = mw[r0:r1, jc - half:jc + half + 1]
    v = blk[bm]
    thr = np.percentile(v, 10) + 0.5 * (np.percentile(v, 99)
                                        - np.percentile(v, 10))
    runs, gaps = [], []
    for i in range(blk.shape[0]):
        line = blk[i][bm[i]]
        if line.size < 8:
            continue
        up = line > thr
        n = 1
        for t in range(1, up.size):
            if up[t] == up[t - 1]:
                n += 1
            else:
                (runs if up[t - 1] else gaps).append(n)
                n = 1
        (runs if up[-1] else gaps).append(n)
    return (float(np.median(runs)) if runs else float('nan'),
            float(np.median(gaps)) if gaps else float('nan'))


def _cv_partition(ru, rc):
    """The closed form the suite's row 18 derives; repeated here so the figure
    and the guard cannot drift apart is NOT the argument -- they would. It is
    imported from the suite instead."""
    import validate_beach as V
    return V._cv_partition(ru, rc)


def render_pair(w, W=720, H=960):
    cam, inf = R.build_frame(w, 0.0, R.CAM.K_CONTENT, 'K', R.SUN_AZ,
                             W * SS, H * SS,
                             float(0.5 * (w.y[-1] - w.y[0])),
                             R.surf_line_scale(w)[1])
    t0 = time.time()
    w.subgrid_on = False
    L_off, ex_off = R.render(cam, w)
    print('  before: %.0f s' % (time.time() - t0), flush=True)
    t0 = time.time()
    w.subgrid_on = True
    L_on, ex_on = R.render(cam, w)
    print('  after:  %.0f s' % (time.time() - t0), flush=True)
    return cam, L_off, ex_off, L_on, ex_on


def figure_1to1(L_off, L_on, path, gap=14):
    """The crop, before | after, one key, no text."""
    r0, r1 = CROP_ROWS
    c0, c1 = CROP_COLS
    a = L_off[r0:r1, c0:c1]
    b = L_on[r0:r1, c0:c1]
    key = float(a[..., 1].max())
    pa = np.clip(a / key, 0.0, 1.0) ** (1.0 / GAMMA)
    pb = np.clip(b / key, 0.0, 1.0) ** (1.0 / GAMMA)
    h, wd = pa.shape[:2]
    img = np.zeros((h, wd * 2 + gap, 3))
    img[:, :wd] = pa
    img[:, wd + gap:] = pb
    img[:, wd:wd + gap] = np.array(P.BG) / 255.0
    Image.fromarray((img * 255.0 + 0.5).astype(np.uint8)).save(path)
    return key


def figure_cv_floor(w, bands, path, W=1500, H=700):
    """The derived CV against footprint, with the render's own bands on it."""
    img = P.canvas(W, H)
    ax = P.Axes(img, (95, 90, 720, 600), (math.log10(0.02), math.log10(50.0)),
                (0.0, 1.6),
                title='the CV the partition requires, against footprint',
                xlabel='log10 pixel footprint, m',
                ylabel='coefficient of variation of the glitter radiance')
    ax.frame(xticks=[-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5],
             yticks=[0.0, 0.4, 0.8, 1.2, 1.6])
    foots = np.geomspace(0.02, 50.0, 40)
    rng = np.random.default_rng(20260821)
    n = 40000
    x = rng.uniform(-800, 800, n)
    y = rng.uniform(-800, 800, n)
    ea = np.stack([np.ones(n), np.zeros(n)], -1)
    cv, frac = [], []
    for f in foots:
        ff = np.full(n, float(f))
        dd = w.subgrid.slope(x, y, foot_c=ff, foot_a=ff, ea=ea)
        ru = float(dd['su2_res'].mean())
        rc = float(dd['sc2_res'].mean())
        cv.append(_cv_partition(ru / max(w.subgrid.su2 - ru, 1e-30),
                                rc / max(w.subgrid.sc2 - rc, 1e-30)))
        frac.append((ru + rc) / (w.subgrid.su2 + w.subgrid.sc2))
    ax.line(np.log10(foots), cv, (28, 30, 34), 3)
    for bd in bands:
        ax.marker(math.log10(bd['foot']), bd['cv_on'], (196, 84, 48), 5)
        ax.marker(math.log10(bd['foot']), bd['cv_off'], (70, 110, 190), 5)
    ax.text(math.log10(0.03), 1.50, 'derived floor: CV of p_sub(z* - z_res)',
            (28, 30, 34), font=P.FONT)
    ax.text(math.log10(0.03), 1.40, 'measured, realisation ON', (196, 84, 48),
            font=P.FONT)
    ax.text(math.log10(0.03), 1.30, 'measured, waves 4-17', (70, 110, 190),
            font=P.FONT)

    ax2 = P.Axes(img, (840, 90, 1440, 600),
                 (math.log10(0.02), math.log10(50.0)), (0.0, 1.0),
                 title='and the share of the wind sea a pixel can draw',
                 xlabel='log10 pixel footprint, m',
                 ylabel='resolved share of the carried slope variance')
    ax2.frame(xticks=[-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5],
              yticks=[0.0, 0.25, 0.5, 0.75, 1.0])
    ax2.line(np.log10(foots), frac, (28, 30, 34), 3)
    r3 = [float(BO.mss_fraction_below(math.pi / f, w.subgrid.k_lo,
                                      w.subgrid.k_hi)) for f in foots]
    ax2.line(np.log10(foots), r3, (150, 100, 40), 2, dash=(7, 5))
    sw = (w.mss_swell['su2'] + w.mss_swell['sc2']) / (w.subgrid.su2
                                                      + w.subgrid.sc2)
    ax2.hline(sw, (70, 110, 190), 2, (4, 4))
    ax2.text(math.log10(0.03), 0.95, 'sampled, box filter (sinc)',
             (28, 30, 34), font=P.FONT)
    ax2.text(math.log10(0.03), 0.89, '(R3), sharp cut-off at k = pi/L',
             (150, 100, 40), font=P.FONT)
    ax2.text(math.log10(0.03), 0.83, 'what the swell alone carried, waves 4-17',
             (70, 110, 190), font=P.FONT)
    P.caption(img, ['scene-linear; every point is `SlopeRealisation` sampled '
                    'on 40000 world points at that footprint, and no quantity '
                    'in this figure is read back out of any image'])
    img.save(path)
    return foots, cv, frac


def _sidecar(path, text):
    with open(path.replace('.png', '.caption.md'), 'w') as f:
        f.write(text)


def main():
    t0 = time.time()
    R._set_runup()
    bay = B.run_bay(embay=True)
    w = R.Water(bay)
    print('bed %.0f s' % (time.time() - t0), flush=True)
    cam, L_off, ex_off, L_on, ex_on = render_pair(w)
    mw = ex_on['water_mask']
    g_on, g_off = L_on[..., 1], L_off[..., 1]

    # ---- the bands, measured on the scene-linear buffer
    foot_full = np.zeros(L_on.shape[:2])
    foot_full[mw] = ex_on['water']['foot'][0]
    r0, r1 = CROP_ROWS
    bands = []
    edges = np.linspace(r0, r1, 5).astype(int)
    for i in range(4):
        a, b = int(edges[i]), int(edges[i + 1])
        col = np.where(mw[a:b], g_off[a:b], np.nan)
        prof = np.nanmean(col, axis=0)
        jc = int(np.nanargmax(prof))
        bg = np.nanpercentile(prof, 20)
        pk = prof[jc] - bg
        wl, wr = jc, jc
        while wl > 0 and prof[wl - 1] - bg > 0.5 * pk:
            wl -= 1
        while wr < prof.size - 1 and prof[wr + 1] - bg > 0.5 * pk:
            wr += 1
        half = max(int(round(0.15 * (wr - wl))), 2)
        m_on, s_on, cv_on = _strip_stats(g_on, mw, a, b, jc, half)
        m_of, s_of, cv_of = _strip_stats(g_off, mw, a, b, jc, half)
        wide = max(int(round(0.6 * (wr - wl))), 6)
        ru_on, gp_on = _runs(g_on, mw, a, b, jc, wide)
        ru_of, gp_of = _runs(g_off, mw, a, b, jc, wide)
        # THE 90th PERCENTILE, AND IT IS THE GUARD'S OWN CONVENTION. The floor
        # a band must clear is set by its COARSEST pixels -- those are the ones
        # with the least to be granular with -- so `_sec_glitter_field` takes
        # p90 of the strip's footprints and this figure must plot the same
        # thing or the curve and the row are two different claims. Plotting
        # the median instead puts the floor above where the row evaluates it,
        # which is how a figure ends up appearing to contradict a passing
        # guard. It did, on this section's first run.
        ft = float(np.percentile(foot_full[a:b, jc - half:jc + half + 1]
                                 [mw[a:b, jc - half:jc + half + 1]], 90))
        if wr - wl < 20:
            # A BAND WHOSE PATH COULD NOT BE LOCATED IS DROPPED AND SAID SO.
            # In the near field the path runs off the bottom of the crop and
            # the column profile stops having a peak; a 14 px "width" against
            # its neighbours' 105-164 is that, not a narrow path. Measuring a
            # core strip on it would put a point on the figure that means
            # nothing, which is worse than a gap.
            print('   band %d-%d DROPPED: located width %d px is degenerate'
                  % (a, b, wr - wl))
            continue
        bands.append(dict(rows=(a, b), col=jc, width=int(wr - wl), foot=ft,
                          mean_on=m_on, sd_on=s_on, cv_on=cv_on,
                          mean_off=m_of, sd_off=s_of, cv_off=cv_of,
                          run_on=ru_on, gap_on=gp_on,
                          run_off=ru_of, gap_off=gp_of))

    key = figure_1to1(L_off, L_on, '%s/s18-glitter-1to1.png' % OUT)
    figure_cv_floor(w, bands, '%s/s18-cv-floor.png' % OUT)

    # ---- the 8-bit numbers, through the SAME encode, said out loud
    def to8(v):
        return np.floor(np.clip(v / key, 0, 1) ** (1 / GAMMA) * 255 + 0.5)

    print()
    print('THE GLITTER PATH, frame K, %d x %d supersampled %dx, crop rows '
          '%d-%d cols %d-%d' % (720, 960, SS, CROP_ROWS[0], CROP_ROWS[1],
                                CROP_COLS[0], CROP_COLS[1]))
    print('exposure key for the FIGURE ONLY: %.4f (max green of the BEFORE '
          'panel); WHITE = %.4f' % (key, R.WHITE))
    print('%-12s %5s %6s | %9s %9s %7s | %9s %9s %7s | %s'
          % ('rows', 'col', 'width', 'lin mean', 'lin sd', 'CV',
             'lin mean', 'lin sd', 'CV', 'foot m'))
    for bd in bands:
        print('%5d-%-6d %5d %6d | %9.4g %9.4g %7.3f | %9.4g %9.4g %7.3f | %.3f'
              % (bd['rows'][0], bd['rows'][1], bd['col'], bd['width'],
                 bd['mean_off'], bd['sd_off'], bd['cv_off'],
                 bd['mean_on'], bd['sd_on'], bd['cv_on'], bd['foot']))
    print('8-bit through the same encode as the figure (display-referred, '
          'stated as such):')
    for bd in bands:
        a, b = bd['rows']
        h = max(int(round(0.15 * bd['width'])), 2)
        j = bd['col']
        for tag, gg in (('before', g_off), ('after ', g_on)):
            v = to8(gg[a:b, j - h:j + h + 1][mw[a:b, j - h:j + h + 1]])
            print('   %5d-%-6d %s  mean %5.1f  sd %5.1f  p5 %5.1f  '
                  '>=250 %5.1f%%'
                  % (a, b, tag, v.mean(), v.std(), np.percentile(v, 5),
                     100 * (v >= 250).mean()))
    print('runs / gaps, px, on the wide box:')
    for bd in bands:
        print('   %5d-%-6d before %.0f / %.0f    after %.0f / %.0f'
              % (bd['rows'][0], bd['rows'][1], bd['run_off'], bd['gap_off'],
                 bd['run_on'], bd['gap_on']))
    print('swell budget: su2 %.6f sc2 %.6f (%d wet points)'
          % (w.mss_swell['su2'], w.mss_swell['sc2'], w.mss_swell['n']))
    print('%.0f s' % (time.time() - t0))
    return dict(bands=bands, key=key, w=w)


if __name__ == '__main__':
    main()
