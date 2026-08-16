"""Re-take the pool's *measured* apparent albedo either side of the lobe fix.

    python3 lobe_albedo_measure.py after     -> albedo-after-hero.npz
    python3 lobe_albedo_measure.py before    -> albedo-before-hero.npz
    POOL_WIDE=1 python3 lobe_albedo_measure.py after   -> albedo-after-wide.npz

    FIXLOBE_NPZ=<dir>                        where they are written (default `.`)

WHY THIS EXISTS AND WHY IT IS NOT `fix_lobe_render.py`. That runner slices
`render.py` at the line that forms `HDRP` -- the scene-linear buffer -- which is
everything a *picture* needs and 700 lines short of the block that measures the
pool's apparent albedo against its own closed form. The README's headline
photometric row (`the render, measured  0.2151`) is written by THAT block, at
`render.py`'s "and the same quantity MEASURED off the frame". So this file cuts
lower: at the head of the second measurement, immediately after the four
water/sunlit-stone readings are printed.

THE DEFECT IS NOT REDEFINED HERE. `fix_lobe_render._lobe_projection` is imported
and monkeypatched, character for character the same object that drew
`fig-pool-lobe-before-after.png`, and `atmosphere.py` on disk is never touched.

ONE SOURCE LINE IS INSERTED and it records rather than changes. `water_shade`
carries its two columns out as LUMINANCES only -- `spec_ @ _Y, tran_ @ _Y` -- on
the file's own stated grounds that the full pair is 300 MB. The measured
`rho_water` is a luminance and needs no more than that; a PER-BAND reading of the
same quantity does. So one append is inserted immediately above that projection,
capturing `spec_` and `tran_` as float32, and the capture is then CHECKED against
the luminances `render.py` itself carried out: the primary call is identified by
`spec_ @ _Y` reproducing `WSPEC` to float tolerance, so a mis-picked call cannot
pass silently. Nothing downstream reads the capture.

EVERYTHING MEASURED IS SCENE-LINEAR, off `HDRP`/`WSPEC`/`WTRAN`, never off a PNG.
The one display-referred number reported is labelled as such and is reported only
because the README carries it as a display-referred number.
"""
import json
import os
import sys

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)
OUT = os.environ.get('FIXLOBE_NPZ', '.')

import atmosphere as ATM                                        # noqa: E402
import fix_lobe_render as FLR                                   # noqa: E402

_Y3 = np.array([.2126, .7152, .0722])
CAPTURE = '    _LOBE_CAP.append((spec_.astype(np.float32), '\
          'tran_.astype(np.float32)))'
ANCHOR = "    _Y = np.array([.2126, .7152, .0722])"
CUTMARK = '# --- the second measurement: submerged wall against the dry band'


def _pass():
    """`render.py` down to the end of the apparent-albedo block, plus the two
    per-band columns captured on the way."""
    path = os.path.join(HERE, 'render.py')
    src = open(path).read().split('\n')
    anchors = [i for i, ln in enumerate(src) if ln == ANCHOR]
    assert len(anchors) == 1, 'the water_shade anchor is not unique: %r' % anchors
    src.insert(anchors[0] + 1, CAPTURE)
    cut = next(i for i, ln in enumerate(src) if ln.startswith(CUTMARK))
    ns = {'__name__': 'lobe_albedo_measure', '__file__': path, '_LOBE_CAP': []}
    exec(compile('\n'.join(src[:cut]), path, 'exec'), ns)
    return ns


def _box(ns, v):
    """A per-ray water quantity onto the output grid exactly as `render.py`'s
    own `_plw` does it: scatter into the full W*H frame, then the SS box mean."""
    W, H, SS, inp = ns['W'], ns['H'], ns['SS'], ns['inp']
    a = np.zeros((W * H, v.shape[1]))
    a[np.flatnonzero(inp)] = v
    return a.reshape(H // SS, SS, W // SS, SS, v.shape[1]).mean((1, 3))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'after'
    if mode not in ('before', 'after'):
        raise SystemExit(__doc__)
    if mode == 'before':
        assert ATM._lobe_shape(ATM.N_DISC, None) \
            == FLR._lobe_projection(ATM.N_DISC, None)
        ATM._lobe_shape = FLR._lobe_projection
        print('*** _lobe_shape -> the PROJECTION form, for this run only')

    ns = _pass()
    cap = ns['_LOBE_CAP']
    WSPEC, WTRAN = ns['WSPEC'], ns['WTRAN']
    hit = [k for k in cap
           if k[0].shape[0] == WSPEC.size
           and np.allclose(k[0] @ _Y3, WSPEC, rtol=1e-5, atol=1e-6)
           and np.allclose(k[1] @ _Y3, WTRAN, rtol=1e-5, atol=1e-6)]
    assert len(hit) == 1, 'the primary water_shade call is not identified (%d)' \
        % len(hit)
    spec3, tran3 = (h.astype(np.float64) for h in hit[0])

    PS, PT = _box(ns, spec3), _box(ns, tran3)
    REG, HDRP = ns['REG'], ns['HDRP']
    w3, s4 = REG == 3, REG == 4
    EB, SH = ns['_EBEAM'], ns['_SHAPE']

    tran_b = PT[w3].mean(0)                       # per band, transmitted column
    spec_b_mean = PS[w3].mean(0)
    spec_b_med = np.median(PS[w3], 0)
    hdr_b = HDRP[w3].mean(0)
    stone_b = HDRP[s4].mean(0)
    hy = HDRP @ _Y3

    o = dict(
        mode=mode,
        wide=bool(ns['POOL_WIDE']),
        n_water_px=int(w3.sum()), n_stone_px=int(s4.sum()),
        # --- the README's headline row, in luminance, as render.py writes it
        rho_w_meas=float(ns['_rho_w_meas']),
        rho_w_pred=float(ns['_rho_w_pred']),
        plt_mean=float(ns['_plt_mean']),
        plt_med=float(np.median(ns['_plw'][w3, 1])),
        sp_mean=float(ns['_sp_mean']), sp_med=float(ns['_sp_med']),
        L_stone=float(ns['_L_stone']),
        rho_stone_eff=float(ns['_rho_stone_eff']),
        # --- the same quantity per band, from the captured columns
        rho_w_meas_band=(tran_b / (EB * SH)).tolist(),
        rho_w_pred_band=np.asarray(ns['RHO_WATER']).tolist(),
        tran_band=tran_b.tolist(),
        spec_band_mean=spec_b_mean.tolist(),
        spec_band_med=spec_b_med.tolist(),
        hdr_band_water=hdr_b.tolist(),
        hdr_band_stone=stone_b.tolist(),
        EBEAM=np.asarray(EB).tolist(), SHAPE=np.asarray(SH).tolist(),
        # --- the four readings of the frame the README tabulates
        r_tran=float(ns['_plt_mean'] / ns['_L_stone']),
        r_tran_plus_specmed=float((ns['_plt_mean'] + ns['_sp_med'])
                                  / ns['_L_stone']),
        r_med_scene=float(np.median(hy[w3]) / np.median(hy[s4])),
        r_med_display=float((ns['_srgb_lin'](np.median(ns['hero'][w3]
                                                       .reshape(-1, 3), 0))
                             @ _Y3)
                            / (ns['_srgb_lin'](np.median(ns['hero'][s4]
                                                         .reshape(-1, 3), 0))
                               @ _Y3)),
        r_closed=float(ns['_rho_w_pred'] * (_Y3 * EB * SH).sum()
                       / ns['_L_stone']),
        # --- the bed terms the same block prices, which are render-measured too
        caubar=np.asarray(ns['_CAUBAR']).tolist(),
        EBED_SUN=np.asarray(ns['_EBED_SUN']).tolist(),
        EBED_SKY=np.asarray(ns['_EBED_SKY']).tolist(),
        EBED_RET=np.asarray(ns['_EBED_RET']).tolist(),
    )
    tag = 'wide' if ns['POOL_WIDE'] else 'hero'
    np.savez_compressed(os.path.join(OUT, 'albedo-%s-%s.npz' % (mode, tag)),
                        HDRP=HDRP.astype(np.float32), REG=REG,
                        PSPEC=PS.astype(np.float32), PTRAN=PT.astype(np.float32),
                        meta=json.dumps(o))
    print('\n*** %s / %s' % (mode, tag))
    print(json.dumps(o, indent=1))


if __name__ == '__main__':
    main()
