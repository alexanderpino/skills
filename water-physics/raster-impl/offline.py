"""The offline frame the screen-space pass is validated against.

SAME MODEL, DIFFERENT MACHINERY. That is the only thing that makes the
comparison worth anything, and every difference between this file and
`sswater.py` is deliberate and listed:

  |                     | `offline.py`                  | `sswater.py`            |
  |---------------------|-------------------------------|-------------------------|
  | geometry            | analytic ray-cast, f64        | reversed-Z depth buffer |
  | the refracted ray   | traced, PER BAND (dispersive) | not traced -- the water |
  |                     |                               | column is `t_scene - t` |
  |                     |                               | along the STRAIGHT ray, |
  |                     |                               | which is what `12` step |
  |                     |                               | 4 specifies             |
  | T_esc, G_rt         | `optics.slab_esc/slab_trap`   | a LUT fetch             |
  |                     | evaluated at the pixel's own  |                         |
  |                     | tau, 2000-node Gauss-Legendre |                         |
  | coverage            | per pixel                     | one fullscreen triangle |

WHAT IS SHARED, and shared by IMPORT so it cannot drift: `optics.py`,
`atmosphere.py`, the scene constants in `scene.py`, and the radiometric
composition in `sswater.bed_radiance`. Sharing the composition is on purpose --
if the two files each wrote their own, a disagreement would tell you nothing
about screen space, only that two people had written two shaders.

THE COST IS THE POINT. This file calls `optics.slab_esc` and `optics.slab_trap`
ONCE PER WATER PIXEL, at that pixel's own three optical depths, which is ~100 us
each and ~20 s a frame. That is precisely the cost a LUT exists to remove, and
it is why the chapter's claim is a claim about real-time rendering and cannot be
tested anywhere else.

NOT MODELLED, on both sides equally, so that neither gains: cast shadows (the
post's shadow is absent from the bed in both), and any wave -- the datum is flat
in both. Listed in the README under `Not built`.
"""
import sys as _sys
import os as _os

import numpy as np

_REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                     '..', 'reference-impl')
if _REF not in _sys.path:
    _sys.path.insert(0, _REF)

import optics as OPT                                            # noqa: E402

import scene as SC                                              # noqa: E402
import sswater as WA                                            # noqa: E402


def exact_exit(tau3):
    """`T_esc` and `G_rt` at three per-band optical depths, from `optics.py`,
    with nothing pre-computed and nothing interpolated.

    `slab_esc(1.0, absorb)` reads channel c's own internal Fresnel at
    `absorb[c]`, so three DIFFERENT optical depths -- which is what a dispersive
    trace produces -- cost one call, not three. That is a property of the
    shipped signature and not a trick: `absorb` is per channel by construction.
    """
    tau3 = np.asarray(tau3, float)
    esc = np.empty(tau3.shape)
    rt = np.empty(tau3.shape)
    flat_i = tau3.reshape(-1, 3)
    fe, fr = np.empty_like(flat_i), np.empty_like(flat_i)
    # exact duplicates are grouped, which is exact (float equality) and buys the
    # flat shelf -- a third of this scene's water -- for one call.
    key = np.ascontiguousarray(flat_i).view([('a', 'f8'), ('b', 'f8'),
                                             ('c', 'f8')]).ravel()
    uniq, inv = np.unique(key, return_inverse=True)
    ue = np.empty((len(uniq), 3))
    ur = np.empty((len(uniq), 3))
    for i, k in enumerate(uniq):
        a = np.array([k['a'], k['b'], k['c']])
        ue[i] = OPT.slab_esc(1.0, a)
        ur[i] = OPT.slab_trap(1.0, a)
    fe[:], fr[:] = ue[inv], ur[inv]
    esc.reshape(-1, 3)[:] = fe
    rt.reshape(-1, 3)[:] = fr
    return esc, rt


def offline_frame(gbuf, h_water=SC.H_WATER):
    """The reference frame. Per pixel:

      1. the water-plane hit, from the same ray as the pass but with the scene's
         own analytic geometry deciding occlusion -- no depth buffer;
      2. the view ray REFRACTED into the water, per band, through
         `optics.refract` (the shipped function, TIR branch and all, with
         eta = 1/n so the branch is unreachable from this side and the call
         site says so);
      3. the submerged hit of each band's own ray -- three hits, three column
         lengths, three optical depths;
      4. `T_esc`, `G_rt` at those three depths, exactly;
      5. the same radiometric composition the pass uses, imported from it.
    """
    res = gbuf['res']
    eye = gbuf['eye']
    d = gbuf['dirs']
    dz = d[..., 2]

    with np.errstate(divide='ignore', invalid='ignore'):
        t = (h_water - eye[2]) / dz
    hit = (dz < -WA.EPS_RAYZ) & (t > 0)
    # occlusion decided by the ANALYTIC scene, which is the whole difference
    # from the pass's depth-buffer reject.
    water = hit & ((gbuf['kind'] == 2) | ((gbuf['kind'] == 3) & (gbuf['t'] > t)))
    water &= gbuf['t'] > t

    L = gbuf['color'].copy()
    if not water.any():
        return {'color': L, 'water': water}

    dd = d[water]
    tt = t[water]
    P = eye[None] + tt[:, None] * dd
    n = np.zeros_like(dd)
    n[:, 2] = 1.0
    cos_a = np.clip(-dd[:, 2], 0.0, 1.0)
    R = OPT.fresnel(cos_a)

    npx = len(dd)
    dep3 = np.empty((npx, 3))
    path3 = np.empty((npx, 3))
    alb3 = np.empty((npx, 3))
    for c in range(3):
        eta = 1.0 / OPT.IOR[c]        # air -> water: eta < 1, TIR unreachable
        assert eta < 1.0
        tx, ty, tz = OPT.refract(dd[:, 0], dd[:, 1], dd[:, 2],
                                 n[:, 0], n[:, 1], n[:, 2], eta)
        rd = np.stack([tx, ty, tz], axis=1)
        tb, zb, alb, _ = SC.submerged_hit(P, rd)
        dep3[:, c] = np.clip(h_water - zb, 0.0, None)
        path3[:, c] = np.where(np.isfinite(tb), tb, 0.0)
        alb3[:, c] = alb[:, c]

    tau3 = OPT.ABS[None] * dep3
    esc, rt = exact_exit(tau3)

    # the composition, imported. `bed_radiance` reads `scene.RHO_BED`; where the
    # refracted ray landed on the POST instead, swap the albedo in by ratio --
    # the composition is linear in it except through the trap denominator, so
    # the trap is recomputed rather than scaled.
    L_bed = WA.bed_radiance(dep3, esc, rt)
    post = np.abs(alb3 - SC.RHO_BED[None]).sum(1) > 1e-12
    if post.any():
        num = L_bed[post] * (1.0 - SC.RHO_BED[None] * rt[post]) / SC.RHO_BED[None]
        L_bed[post] = (num * alb3[post]) / (1.0 - alb3[post] * rt[post])

    att = np.exp(-OPT.ABS[None] * path3)
    L_up = OPT.out_of_water((1.0 - R) * L_bed * att)
    refl = dd.copy()
    refl[:, 2] = -refl[:, 2]
    L_refl = R * WA.sky_dirs(refl)

    L[water] = L_refl + L_up
    out = {'color': L, 'water': water}
    for k, v in (('dep3', dep3), ('path3', path3), ('tau3', tau3),
                 ('esc', esc), ('rt', rt)):
        full = np.zeros(res[::-1] + (3,))
        full[water] = v
        out[k] = full
    return out
