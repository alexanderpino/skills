"""WAVE 18 -- the foam edge, before and after, from ONE code path.

The pair is rendered from the SAME bay, the SAME camera and the SAME build,
with two flags moved: `foam_realise` selects the realisation over its own
expectation, and `foam_roller` selects `deck_source` over Battjes & Janssen's
exceedance. Both flags are the control-panel branches `shade_water` already
carries, and both default to the shipping value -- so the BEFORE half is the
code waves 6 to 17 ran, executed by this build, and not a remembered checkout.

Nothing is captioned in the pixels: wave 11's three critics each reported that
burned-in commentary defeated the blind. Every figure writes `<name>.caption.md`
beside it.

    python3 foam_evidence.py            # both halves and the figures
    python3 foam_evidence.py --measure  # re-measure from saved buffers only
"""
import math
import os
import sys
import time

import numpy as np
from PIL import Image

import beach as B
import beach_foam as FM
import beach_render as BR
import validate_beach as V

OUT = BR.OUT
CACHE = os.environ.get('FOAM_EV_CACHE', '/tmp/foam_ev')


# ---------------------------------------------------------------- the crop box
# THE CROP IS TAKEN FROM THE FULL-RESOLUTION BUFFER, so 1:1 means one render
# sample per image pixel and the 2x2 downsample cannot smooth an edge into
# existence or out of it. Wave 12's `waterline_crop` set that rule and this
# follows it.
#
# WHERE IT IS is not hand-placed: the box is centred on the column of greatest
# drawn coverage inside the surf band, which is a deterministic rule on the
# frame's own field.
CROP_W, CROP_H = 560, 360


def _crop_box(cov, shape):
    h, w = shape
    c = np.nan_to_num(cov)
    band = c > 0.30
    if not band.any():
        raise AssertionError('no foam band to crop -- the figure would be sand')
    ys, xs = np.where(band)
    cy, cx = int(np.median(ys)), int(np.median(xs))
    y0 = int(np.clip(cy - CROP_H // 2, 0, h - CROP_H))
    x0 = int(np.clip(cx - CROP_W // 2, 0, w - CROP_W))
    return x0, y0, x0 + CROP_W, y0 + CROP_H


def _render(tag, realise, roller):
    t0 = time.time()
    BR._set_runup()
    bay = B.run_bay(embay=True)
    w = BR.Water(bay)
    w.foam_realise = realise
    w.foam_roller = roller
    SS = BR.SS_HERO
    cam = BR.hero_cameras(w, BR.W_HERO * SS, BR.H_HERO * SS,
                          out=lambda *a, **kw: None)[3]
    L, ex = BR.render(cam, w)
    mw = ex['water_mask']
    cov = np.zeros(L.shape[:2])
    cov[mw] = ex['water']['cov'][0] if np.ndim(ex['water']['cov']) == 2 \
        else ex['water']['cov']
    os.makedirs(CACHE, exist_ok=True)
    np.save('%s/L_%s.npy' % (CACHE, tag), L)
    np.save('%s/cov_%s.npy' % (CACHE, tag), cov)
    np.save('%s/mw_%s.npy' % (CACHE, tag), mw)
    st = ex['water'].get('foam_stats')
    print('%-7s rendered %.1f s  cov max %.3f mean %.4f  stats %s'
          % (tag, time.time() - t0, cov.max(), cov[mw].mean(), st))
    sys.stdout.flush()
    return L, cov, mw


def _load(tag):
    return (np.load('%s/L_%s.npy' % (CACHE, tag)),
            np.load('%s/cov_%s.npy' % (CACHE, tag)),
            np.load('%s/mw_%s.npy' % (CACHE, tag)))


def _u8(L):
    return np.clip(_enc(L), 0, 255).astype(np.uint8)


def _enc(L):
    return (np.clip(np.asarray(L, float) / BR.WHITE, 0.0, 1.0)
            ** (1.0 / 2.2)) * 255.0


def _write(path, arr, caption):
    Image.fromarray(arr).save(path)
    with open(path.replace('.png', '.caption.md'), 'w') as f:
        f.write(caption.rstrip() + '\n')
    print('wrote %s' % path)


def main():
    # THE HALVES ARE SEPARATE INVOCATIONS ON PURPOSE. Standing ruling 13: a
    # backgrounded process in this container gets about 22 s of CPU per ten
    # minutes of wall clock, and one hero render is ~610 s of foreground. Two
    # of them in one call does not fit in a foreground window, so each half is
    # rendered and cached by its own call and `--measure` draws the figures
    # from the buffers. A builder that dies loses one render, not the pair.
    if '--half' in sys.argv:
        tag = sys.argv[sys.argv.index('--half') + 1]
        _render(tag, realise=(tag == 'after'), roller=(tag == 'after'))
        return
    Lb, covb, mwb = _load('before')
    La, cova, mwa = _load('after')

    box = _crop_box(cova, La.shape[:2])
    x0, y0, x1, y1 = box
    print('crop box (1:1, full-res buffer): %s' % (box,))

    Yb, Ya = V._foam_luma8(_enc(Lb)), V._foam_luma8(_enc(La))
    tb = V._foam_texture(Yb[y0:y1, x0:x1][:, :500])
    ta = V._foam_texture(Ya[y0:y1, x0:x1][:, :500])
    print('BEFORE  l/W %.3f %%  acf %.2f px  run q90 %.0f  gap med %.0f'
          % (tb['lW'], tb['acf'], tb['run_q90'], tb['gap_med']))
    print('AFTER   l/W %.3f %%  acf %.2f px  run q90 %.0f  gap med %.0f'
          % (ta['lW'], ta['acf'], ta['run_q90'], ta['gap_med']))

    # -------------------------------------------------- the 1:1 crops, no text
    _write('%s/s18-foam-edge-before.png' % OUT, _u8(Lb[y0:y1, x0:x1]),
           CAP_BEFORE % dict(box=box, **tb))
    _write('%s/s18-foam-edge-after.png' % OUT, _u8(La[y0:y1, x0:x1]),
           CAP_AFTER % dict(box=box, **ta))

    # ------------------------------------------------ the coverage field alone
    _write('%s/s18-foam-coverage-before.png' % OUT,
           (np.clip(np.nan_to_num(covb), 0, 1) * 255).astype(np.uint8),
           CAP_COV_BEFORE)
    _write('%s/s18-foam-coverage-after.png' % OUT,
           (np.clip(np.nan_to_num(cova), 0, 1) * 255).astype(np.uint8),
           CAP_COV_AFTER)

    # -------------------------------------------------------- the hero, after
    _write('%s/s18-foam-frame-after.png' % OUT,
           _u8(BR.downsample(La, BR.SS_HERO)), CAP_FRAME)

    with open('%s/s18-foam-edge-before.caption.md' % OUT) as f:
        pass
    print('\nl/W  before %.3f %%   after %.3f %%   photographs 0.3-0.8 %%'
          % (tb['lW'], ta['lW']))


CAP_BEFORE = """# s18-foam-edge-before

**1:1 crop of the foam edge, the field waves 6 to 17 drew.** Full-resolution
render buffer, columns %(box)s of a 1440 x 1920 buffer, one render sample per
image pixel -- the 2 x 2 downsample is not applied, so this edge is not
smoothed into or out of existence by resampling.

**Provenance: measured.** Rendered by `foam_evidence.py` from this build with
`foam_realise = False` and `foam_roller = False`, which are the control-panel
branches `beach_render.shade_water` already carries. It is therefore the same
code path as the AFTER half with two flags moved, not a remembered checkout.
`foam_realise = False` alpha-blends by `coverage(m) = 1 - exp(-m)`, the
EXPECTATION of the Boolean model; `foam_roller = False` lays the deck from
Battjes & Janssen's `Q_b` instead of the roller.

**Display-referred, and it has to be.** Encoded through
`beach_render._save`'s curve -- exposure `WHITE`, gamma 2.2 -- because the
numbers below are compared against 8-bit JPEG photographs and a run-length
statistic above a half-max threshold does not survive a change of tone curve.
Every physical quantity in this project is measured scene-linear; this one is
not, deliberately.

**Measured on this crop, leftmost 500 px:** correlation length
`l/W` = %(lW).2f %% of the box width, acf 1/e = %(acf).2f px, run q90 =
%(run_q90).0f px, gap median = %(gap_med).0f px. The photographs in
`gauntlet/sea/bar/generic/` give 0.3-0.8 %% and 8-52 px.
"""

CAP_AFTER = """# s18-foam-edge-after

**1:1 crop of the foam edge, the realisation drawn.** Same camera, same bay,
same build, same crop box as `s18-foam-edge-before`. One render sample per
image pixel.

**Provenance: measured.** Rendered by `foam_evidence.py` with
`foam_realise = True` and `foam_roller = True`, the shipping values.

**What is different, and every part of it is a computed quantity.** The
coverage is now ONE REALISATION of the Boolean model whose void probability is
`coverage(m)`, drawn by `beach_foam.boolean_indicator`: a homogeneous
dominating Poisson germ field with per-germ marks thinned at the query point,
which reproduces `1 - exp(-m)` EXACTLY at every point. The grain size is the
local depth through `grain_radius` -- `r_g = d/2`, on the depth-limited
macroturbulence argument -- and the crossover to the mean is the pixel
footprint the renderer already computes for the slope band-limit. The deck's
source is `deck_source`, the transform's own dissipation lagged shoreward by
`ROLLER_LAG` local wavelengths. NOTHING HERE IS A NOISE FUNCTION: the germ
positions are the sampler of a stated point process, and the suite row
"realisation mean against 1 - exp(-m)" is what holds them to it.

**Display-referred**, through the same encode as the BEFORE half, for the same
reason.

**Measured on this crop, leftmost 500 px:** `l/W` = %(lW).2f %%, acf 1/e =
%(acf).2f px, run q90 = %(run_q90).0f px, gap median = %(gap_med).0f px,
against the photographs' 0.3-0.8 %% and 8-52 px.
"""

CAP_COV_BEFORE = """# s18-foam-coverage-before

**The coverage field alone, as an image, before.** Not a render -- the drawn
coverage buffer itself, 0 to 1 mapped to 0 to 255, so that the thing being
alpha-blended can be looked at without the sky, the glitter and the bed on top
of it.

**Provenance: measured**, from the same run as `s18-foam-edge-before`.

This is the owner's *strak witte lijnen* in their own right: a set of
perfectly smooth diagonal ribbons with continuous edges and no break-up at any
scale. It is not a rendering artefact and not a filter -- it is what
`1 - exp(-m)` looks like when `m` is a smooth function of position, which is
what an expectation is. The picture is the diagnosis.
"""

CAP_COV_AFTER = """# s18-foam-coverage-after

**The coverage field alone, as an image, after.** Same mapping, same run as
`s18-foam-edge-after`.

**Provenance: measured.**

The ribbons are the same ribbons -- the mean is unchanged at every point by
construction, and the suite states that as a number rather than as an
intention. What has changed is that the field is now a REALISATION of the
model rather than its first moment, so the edges break into grains at the
depth-limited scale and the seaward edge stops being a curve.
"""

CAP_FRAME = """# s18-foam-frame-after

**Hero frame J, after.** The full frame at delivery resolution, 720 x 960,
box-averaged in scene-linear from the 1440 x 1920 buffer.

**Provenance: measured.** `foam_evidence.py`, shipping flags, one code path.

Included so the crops can be located, and so the foam is judged in the frame
it belongs to rather than only at 1:1. The frame carries defects that are not
this lane's -- the clipped highlight on the left is the glitter path and the
sand is the bathymetry lane's -- and no caption inside the pixels says so,
because that is what defeated wave 11's blind.
"""


if __name__ == '__main__':
    main()
