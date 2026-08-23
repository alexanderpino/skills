"""The reference the filtered wave paths are measured against: the pixel's own
integral, taken by brute force.

WHAT THE REFERENCE IS, stated precisely, because the whole measurement turns on
it. A pixel's value is

    L_pix = INT_pixel w(s) L( surface(s) ) ds

with `w` the pixel's own reconstruction filter -- a BOX over the pixel square,
which is what a converged renderer converges to -- and `L` the shading model.
`L` is NONLINEAR in the slope, which is the entire content of the chapter's
section: filtering the slope and shading once is not the same as shading and
then filtering, and neither is the same as shading the mean slope.

So this file evaluates that integral by stratified sub-sampling of the pixel
square, with the FULL unfiltered `field.py` at every sub-sample. Same shading
model, same `atmosphere.sky`, same Fresnel, same transmitted half -- the ONLY
difference from `waves.wave_pass` is that nothing is filtered and nothing is
approximated. Every disagreement is therefore a filtering error and not a model
error, which is the only way to price a filter.

THE ESTIMATOR HAS AN ERROR AND IT IS QUOTED, NOT ASSUMED. The sun's disc is a
`cos^93493` lobe -- 0.53 degrees wide -- and a footprint that scatters the
reflected ray over several degrees turns the glitter integral into a needle
hunt: at one sample per pixel a Monte-Carlo estimate of the disc term has a
relative standard error above 100%. The estimator therefore reports its own
standard error per bin (`sem`), computed from the sub-sample spread, and the
suite takes its tolerances from that number and never from the disagreement it
is measuring. Where the per-pixel estimate cannot be converged at any affordable
rate, the row is a BIN MEAN and says so.

NOTHING AUTHORED, and no second shading model: `shade_samples` below calls
`waves.surface_shade` -- the same function the pass calls -- with `cov=None`,
because an unfiltered sample has nothing removed and therefore nothing to widen
with. That is the chapter's own insistence that the filtered path "degenerates
bit-for-bit to the unfiltered expression at zero variance", used as machinery
rather than asserted.
"""
import sys as _sys
import os as _os

import numpy as np

_REF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                     '..', 'reference-impl')
if _REF not in _sys.path:
    _sys.path.insert(0, _REF)

import optics as OPT                                            # noqa: E402
import atmosphere as ATM                                        # noqa: E402
import field as FLD                                             # noqa: E402

import scene as SC                                              # noqa: E402
import waves as WV                                              # noqa: E402


def strata(nsub, seed):
    """A jittered NxN grid of offsets in [-0.5, 0.5]^2 -- stratified, so the
    variance falls faster than 1/N on the smooth part of the integrand and no
    faster than 1/N on the needle, which is the honest expectation and is what
    the reported standard error measures."""
    n = int(round(np.sqrt(nsub)))
    r = np.random.default_rng(seed)
    i, j = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
    u = (i.ravel() + r.random(n * n)) / n - 0.5
    v = (j.ravel() + r.random(n * n)) / n - 0.5
    return np.stack([u, v], axis=1)


def sample_positions(gbuf, sel, off):
    """Where one sub-sample of each selected pixel lands on the datum.

    The pixel square is jittered in NDC and the datum hit is recomputed, so the
    sub-samples fill the pixel's TRUE footprint -- an oriented parallelogram
    that is 800x longer than it is wide at the far end of this frame. That
    anisotropy is the reference's for free and the scalar-footprint pass cannot
    have it, which is precisely the regime the README prices."""
    res = gbuf['res']
    rows, cols = np.nonzero(sel)
    ndc_x = 2.0 * (cols + 0.5 + off[0]) / res[0] - 1.0
    ndc_y = 1.0 - 2.0 * (rows + 0.5 + off[1]) / res[1]
    d = SC.ray_dirs(ndc_x, ndc_y, gbuf['az'], gbuf['el'], gbuf['fov'],
                    res[0] / res[1])
    eye = gbuf['eye']
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (SC.H_WATER - eye[2]) / d[:, 2]
    P = eye[None] + t[:, None] * d
    return d, t, P


# --------------------------------------- THE DISC TERM NEEDS A SECOND ESTIMATOR
# AND WHY, stated before the code because it is the sharpest single fact in this
# directory about the section being tested. The sun's disc is
# `cos^93493` -- a lobe 0.53 deg across, solid angle 6.72e-5 sr -- and past 30 m
# the footprint scatters the reflected ray over a distribution several degrees
# wide. The probability that any one sub-sample lands on the disc is then of
# order 1e-6. A brute-force mean over 256 sub-samples of 4400 pixels collects
# about TWO hits, so its answer is a Poisson draw and its sample standard error
# (which is zero on every pixel that drew no hit at all) is a lie. That is not a
# defect of this estimator; it IS the chapter's claim -- "one shading sample per
# pixel hits or misses it essentially at random" -- arriving on the measurement
# side. An estimator that cannot see the far glitter cannot referee a fix for it.
#
# THE SECOND ESTIMATOR, and it is the physically meaningful one. A lobe narrow
# against everything else is a delta of known flux, so the expected reflected
# radiance of the disc through a footprint is
#
#     S  =  L_sun * Omega_lobe * p_R(sun) * R_fresnel,     Omega_lobe = 2pi/(n+1)
#
# with `p_R` the DENSITY, per steradian, of the reflected direction over the
# footprint. `p_R(sun)` is what "the specular response" physically IS, and it is
# estimable at any precision: count the sub-samples whose reflected ray lands
# inside a cone of half-angle eps around the sun and divide by that cone's solid
# angle. At eps = 2 deg the acceptance is 57x the disc's own, so the same
# sub-samples that gave two hits give a hundred.
#
# ITS BIAS IS THE KERNEL WIDTH AND IT IS MEASURED, NOT ASSUMED: `p_R` is
# smoothed over eps, so the estimate is reported at TWO eps and the pair brackets
# the bias. Everything is returned in RADIANCE so it sits beside the brute-force
# column in the same units, which is the absolute row this quantity gets.
EPS_CONE = (np.deg2rad(1.0), np.deg2rad(2.0))

# The disc lobe's own angular integral and peak, both `atmosphere.py`'s and
# neither written by hand: `SKY_LOBE[0] = (1/1.15, N_DISC, L_SUN)` and `sky()`
# multiplies the whole environment by 1.15, so the disc's flux is exactly
# L_SUN * 2 pi/(N_DISC + 1) and the two 1.15s cancel.
OMEGA_LOBE = 2.0 * np.pi / (ATM.N_DISC + 1.0)
DISC_FLUX = ATM.L_SUN * OMEGA_LOBE * ATM.SKY_LOBE[0][0] * 1.15


def cone_solid_angle(eps):
    return 2.0 * np.pi * (1.0 - np.cos(eps))


def reference(gbuf, base, sel, nsub=64, seed=11, chunk=400000, want_mip=False):
    """The pixel integral over `sel`, by `nsub` stratified sub-samples.

    Returns a dict with, for every selected pixel:
      `color`  the full radiance, reflected + transmitted
      `sun`    the sun DISC lobe's reflected contribution alone
      `refl`   the whole reflected half
      `sem`    the standard error of the mean of `color`, per band, from the
               sub-sample spread -- the estimator's own error, which is what
               every tolerance in the suite is allowed to be built from
      `sun_sem` the same for the disc term, which is the one that does not
               converge
      `fresnel` E[R] -- the EXACT mean of `optics.fresnel` over the footprint's
               own slope distribution, which is what Bruneton's roughness fit
               is a fit TO, and the only way to price that fit rather than cite
               it. `ndv` is E[n.v] beside it.
      `s_res`  rms slope of the UNFILTERED field over the sub-samples of each
               pixel, i.e. the slope variance the surface actually has inside
               that footprint. The number the filtered field is measured against.
      `nrm`    (want_mip) the mean UNIT normal over the footprint, before
               renormalisation -- a literal normal-map mip texel, and the length
               of it is Toksvig's discarded signal.
    """
    WV.init_field()               # see `waves.init_field`: not optional
    rows, cols = np.nonzero(sel)
    npx = len(rows)
    off = strata(nsub, seed)
    n = len(off)

    # the transmitted half, at the pixel centre, from the flat-datum pass. It is
    # held fixed across the sub-samples on PURPOSE and identically in the pass,
    # so the comparison is a comparison of the reflected half; see
    # `waves.flat_base` for the bound on what that costs.
    w_all = base['water']
    idx = np.zeros(w_all.shape, np.int64)
    idx[w_all] = np.arange(int(w_all.sum()))
    pick = idx[rows, cols]
    up_flat = base['up_flat'][pick]
    R_flat = base['R_flat'][pick]

    acc = np.zeros((npx, 3))
    acc2 = np.zeros((npx, 3))
    accs = np.zeros((npx, 3))
    accs2 = np.zeros((npx, 3))
    accr = np.zeros((npx, 3))
    accg = np.zeros((npx, 2))
    accg2 = np.zeros(npx)
    accn = np.zeros((npx, 3))
    accF = np.zeros((npx, 3))
    accnv = np.zeros(npx)
    cone = [np.zeros((npx, 3)) for _ in EPS_CONE]
    cone_n = [np.zeros(npx) for _ in EPS_CONE]
    cs_min = np.cos(np.asarray(EPS_CONE))

    for k in range(n):
        d, t, P = sample_positions(gbuf, sel, off[k])
        gx = np.empty(npx)
        gy = np.empty(npx)
        for lo in range(0, npx, chunk):
            hi = min(lo + chunk, npx)
            gx[lo:hi], gy[lo:hi] = FLD.grad_points(P[lo:hi, 0], P[lo:hi, 1],
                                                   None)
        L_refl, L_sun, R, ndv, rdir = WV.surface_shade(d, gx, gy, None)
        L_up = up_flat * ((1.0 - R) / np.maximum(1.0 - R_flat, 1e-9))
        L = L_refl + L_up
        acc += L
        acc2 += L * L
        accs += L_sun
        accs2 += L_sun * L_sun
        accr += L_refl
        accg += np.stack([gx, gy], axis=1)
        accg2 += gx * gx + gy * gy
        accF += R
        accnv += ndv
        cs = rdir @ ATM.SUN_DIR
        for j, cmin in enumerate(cs_min):
            h = cs >= cmin
            cone[j] += np.where(h[:, None], R, 0.0)
            cone_n[j] += h
        if want_mip:
            nx, ny, nz = FLD.normal_from_grad(gx, gy)
            accn += np.stack([nx, ny, nz], axis=1)

    m = acc / n
    var = np.maximum(acc2 / n - m * m, 0.0)
    ms = accs / n
    vars_ = np.maximum(accs2 / n - ms * ms, 0.0)
    out = {'rows': rows, 'cols': cols, 'nsub': n,
           'color': m, 'refl': accr / n, 'sun': ms,
           'sem': np.sqrt(var / n), 'sun_sem': np.sqrt(vars_ / n),
           'gmean': accg / n, 's_res': np.sqrt(accg2 / n),
           'fresnel': accF / n, 'ndv': accnv / n}
    # the cone estimator of the same disc term, in the same radiance units:
    # S = (mean of R over the samples that landed in the cone) * (hits/N/Omega)
    # * disc flux. `hits` is kept beside it because a bin's Poisson error is
    # sqrt(hits) and that is the tolerance every row built on this may use.
    for j, eps in enumerate(EPS_CONE):
        out['sun_cone%d' % j] = (cone[j] / n / cone_solid_angle(eps)
                                 * DISC_FLUX[None])
        out['sun_hits%d' % j] = cone_n[j]
    out['eps_cone'] = np.asarray(EPS_CONE)
    if want_mip:
        out['nrm'] = accn / n
    return out


def bin_stats(vals, sems, sel_bin):
    """Bin mean and the bin mean's OWN standard error, propagated from the
    per-pixel estimator errors. A bin of `m` pixels each with standard error
    `e_i` has a mean whose error is `sqrt(sum e_i^2)/m` -- so the bin figure
    converges even where the per-pixel one does not, which is the only reason
    the disc term is measurable at all."""
    v = np.asarray(vals)[sel_bin]
    e = np.asarray(sems)[sel_bin]
    m = max(len(v), 1)
    return v.mean(0), np.sqrt((e ** 2).sum(0)) / m
