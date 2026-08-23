"""The three buffers `fix_lobe_evidence.py` draws from, and the only place in
this tree where the lobe defect exists at all.

    python3 fix_lobe_render.py after     -> hdr-after-hero.npz
    python3 fix_lobe_render.py before    -> hdr-before-hero.npz
    python3 fix_lobe_render.py qratio    -> q-ratio-hero.npz

    FIXLOBE_NPZ=<dir>                    where they are written (default `.`)

Each mode is ONE FULL `render.py` HERO PASS -- same camera, same field, same
seed, same EXPOSURE -- so the difference between `before` and `after` is the
exponent and nothing else. `render.py` is not imported: it has no `__main__`
guard and importing it runs every camera the file carries. Its source is read,
sliced at the line that forms `HDRP` (the scene-linear buffer, at output
resolution, immediately before the tone map) and executed to there. Nothing
below the tone map runs and no PNG is written.

`before` REINTRODUCES THE DEFECT AND DOES NOT COMMIT IT. `atmosphere.py` is left
exactly as it is on disk; what changes is one name in the atmosphere module's own
globals, before `render.py` is executed. `sky()` resolves `_lobe_shape` by name
at call time, so it picks the projection form up, and every other constant in
that file -- SUN_COL, the lobe amplitudes, the ENV lattice -- is the shipped one.
The replacement is character-identical to `validate._lobe_projection`, which is
the suite's own copy of the defect, and the `cov = None` branch is asserted equal
to the shipped one before the run starts: the unfiltered path has to stay
bit-for-bit the same or the two frames differ in more than the thing being
measured.

`qratio` answers "how far outside the degeneracy did this frame actually get".
The widened lobe's flux gain is `cosh(ln r / 2)` with `r` the eigen-ratio of
`Q = (1/n)I + C` -- of Q, and NOT of the reflection ellipse C, whose own axis
ratio is an upper bound because the isotropic `(1/n)I` pulls the eigen-ratio down.
It cannot be inferred from the camera: it depends on the slope tensor the
footprint filter removes, which is anisotropic in its own right. So it is
recorded rather than estimated -- `_lobe_shape` is wrapped, every call the hero
pass makes is caught, and only the DISC's call is kept so each surface sample is
counted once rather than once per lobe. What is written out is a 1001-point
quantile grid, not the samples: the figure needs the distribution and the raw
array is 26 MB.
"""
import os
import sys

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)
OUT = os.environ.get('FIXLOBE_NPZ', '.')

import atmosphere as ATM                                        # noqa: E402


def _lobe_projection(n, cov):
    """`atmosphere._lobe_shape` EXACTLY AS IT SHIPPED before 7fe9538: the
    projection variance `1/(u^T Q u)` where the convolved density along u wants
    `u^T Q^-1 u`. Character-identical to `validate._lobe_projection`."""
    if cov is None:
        return 1.0, n
    u1, u2, c11, c12, c22 = cov
    q11, q22 = 1.0 / n + c11, 1.0 / n + c22
    det = np.maximum(q11 * q22 - c12 * c12, 1e-30)
    g = (1.0 / n) / np.sqrt(det)
    r2 = u1 * u1 + u2 * u2
    w = np.where(r2 > 1e-16,
                 (u1 * u1 * q11 + 2.0 * u1 * u2 * c12 + u2 * u2 * q22)
                 / np.maximum(r2, 1e-16),
                 0.5 * (q11 + q22))
    return g, 1.0 / np.maximum(w, 1e-12)


def _hero_pass():
    """Run `render.py` down to `HDRP` and hand it back."""
    src = open(os.path.join(HERE, 'render.py')).read().split('\n')
    cut = next(i for i, ln in enumerate(src) if ln.startswith('HDRP = '))
    path = os.path.join(HERE, 'render.py')
    ns = {'__name__': 'fix_lobe_render', '__file__': path}
    exec(compile('\n'.join(src[:cut + 1]), path, 'exec'), ns)
    return ns['HDRP']


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'after'
    if mode not in ('before', 'after', 'qratio'):
        raise SystemExit(__doc__)
    os.makedirs(OUT, exist_ok=True)

    if mode == 'before':
        assert ATM._lobe_shape(ATM.N_DISC, None) \
            == _lobe_projection(ATM.N_DISC, None), \
            'the cov = None branches differ; the two frames would not be ' \
            'comparable'
        ATM._lobe_shape = _lobe_projection
        print('*** _lobe_shape -> the PROJECTION form, for this run only')

    acc = []
    if mode == 'qratio':
        _real = ATM._lobe_shape

        def _spy(n, cov):
            if cov is not None and abs(n - ATM.N_DISC) < 1e-9:
                u1, u2, c11, c12, c22 = cov
                q11, q22 = 1.0 / n + c11, 1.0 / n + c22
                tr = q11 + q22
                dt = np.maximum(q11 * q22 - c12 * c12, 1e-300)
                disc = np.sqrt(np.maximum(tr * tr - 4.0 * dt, 0.0))
                l1, l2 = .5 * (tr + disc), .5 * (tr - disc)
                acc.append(np.asarray(l1 / np.maximum(l2, 1e-300),
                                      np.float32).ravel())
            return _real(n, cov)

        ATM._lobe_shape = _spy

    H = _hero_pass()

    if mode == 'qratio':
        r = np.concatenate(acc)
        q = np.linspace(0.0, 100.0, 1001)
        p = np.percentile(r, q)
        np.savez_compressed(os.path.join(OUT, 'q-ratio-hero.npz'),
                            q=q, p=p, n=np.array([r.size]))
        g = np.cosh(.5 * np.log(np.maximum(p, 1.0)))
        print('\n*** Q eigen-ratio over %d surface samples of the hero pass'
              % r.size)
        for i, lab in ((50, 'p5 '), (500, 'p50'), (950, 'p95'), (990, 'p99'),
                       (1000, 'max')):
            print('    %s  r = %8.4f   gain = cosh(ln r/2) = %.4f'
                  % (lab, p[i], g[i]))
    else:
        np.savez_compressed(os.path.join(OUT, 'hdr-%s-hero.npz' % mode), HDRP=H)
        print('\n*** %s: HDRP %s  min %.6g  max %.6g  mean %.6g'
              % (mode, H.shape, H.min(), H.max(), H.mean()))


if __name__ == '__main__':
    main()
