"""SECTION A'S REAL CRITERION, MEASURED ON THE SHIPPED SURFACE.

`through_face` reports the fraction of view rays that leave the far side of a
crest, and it has read **0.0000** for six waves. A zero with no distribution
behind it cannot tell "close" from "nowhere near", and the price document's
top recommendation turns on which of the two it is.

WHAT IS MEASURED, and it is a property of the SURFACE alone. Chapter 12's
two-cone derivation says a sightline through a wave crosses the surface twice,
and that for ANY single-valued surface the inclinations at the two crossings
must satisfy

    alpha_1 + alpha_2  >=  2 (90 - theta_c)  =  82.96 deg

on this chapter's green IOR. The ray between the crossings is STRAIGHT, so the
pair (p1, p2) is admissible only if the segment joining them lies inside the
water -- i.e. below the free surface everywhere between. So:

    over every admissible pair on the drawn surface, what is max(a1 + a2)?

THE ADMISSIBILITY TEST IS O(n) PER START POINT, not O(n^2). With
g(j) = (z_j - z_i)/(s_j - s_i), the chord i->j lies below the curve for every
intermediate k exactly when g(j) <= g(k) for all i < k < j -- so a single
sweep with a running minimum of g decides every j.

NOTHING IS DECLARED HERE. The transects run along the cross-shore direction
because that is the direction the crests are being crossed; the alongshore
positions are the bed's own rows; the instants are one period of the scene's
own T_SWELL. The only free number is the sampling step, and it is swept.
"""
import math
import os
import pickle
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'terrain-renderer', 'reference-impl'))
import beach as B                       # noqa: E402
import beach_render as RND              # noqa: E402

SCR = os.environ.get('SCOUT_CACHE', '/tmp/') + os.sep
t0 = time.time()
if os.path.exists(SCR + 'bay.pkl'):
    bay = pickle.load(open(SCR + 'bay.pkl', 'rb'))
else:
    bay = B.run_bay()
    pickle.dump(bay, open(SCR + 'bay.pkl', 'wb'))
w = RND.Water(bay)
print('bay + Water  %.1f s' % (time.time() - t0))

NEED = 2.0 * B.snell_cone_face_deg()
print('the two-cone floor, alpha_1 + alpha_2 >= %.2f deg' % NEED)
print("Stokes' corner allows a steady wave at most 2 x 30 = 60 deg\n")


def sums(ds, span, n_y, n_t, x_lo=430.0, x_hi=640.0, spectral=True):
    """max(a1 + a2) over admissible pairs, and the distribution behind it."""
    w.spectral_on = spectral
    s = np.arange(x_lo, x_hi, ds)
    n = s.size
    nw = int(round(span / ds))
    ys = np.linspace(w.y[0] + 20.0, w.y[-1] - 20.0, n_y)
    best = []
    gmax = 0.0
    n_pair = 0
    for q in range(n_t):
        t = q * B.T_SWELL / n_t
        Z = np.empty((n_y, n))
        for a, yy in enumerate(ys):
            Z[a] = RND.free_surface(w, s, np.full(n, yy), t)
        # inclination at every sample, central difference at the sample step
        A = np.degrees(np.arctan(np.abs(np.gradient(Z, ds, axis=1))))
        for a in range(n_y):
            z = Z[a]
            ang = A[a]
            for i in range(0, n - 2):
                jmax = min(i + nw, n - 1)
                if jmax - i < 2:
                    continue
                k = np.arange(i + 1, jmax + 1)
                g = (z[k] - z[i]) / (s[k] - s[i])
                ok = g <= np.minimum.accumulate(
                    np.concatenate(([np.inf], g[:-1])))
                if not ok.any():
                    continue
                v = ang[i] + ang[k[ok]]
                n_pair += int(ok.sum())
                m = float(v.max())
                best.append(m)
                gmax = max(gmax, m)
    return np.array(best), gmax, n_pair


for ds, span in ((0.25, 30.0), (0.10, 30.0)):
    b, gmax, npair = sums(ds, span, 12, 6)
    print('step %.2f m, span %.0f m, %d start points, %d admissible pairs'
          % (ds, span, b.size, npair))
    print('   MAX (alpha_1 + alpha_2) anywhere        %7.2f deg' % gmax)
    print('   per-start-point best, distribution:')
    for p in (50, 90, 99, 99.9):
        print('      p%-6s                            %7.2f deg'
              % (p, np.percentile(b, p)))
    print('   share of start points whose best beats 60.00 deg '
          '(a steady wave\'s best) %.3e' % np.mean(b > 60.0))
    print('   share whose best beats the %.2f deg floor            %.3e'
          % (NEED, np.mean(b > NEED)))
    print('   THE DEFICIT AT THE BEST PAIR IN THE SCENE: %.2f deg'
          % (NEED - gmax))

b0, g0, n0 = sums(0.25, 30.0, 12, 6, spectral=False)
w.spectral_on = True
print('\nCARRIER ONLY (waves 5-18), step 0.25 m:')
print('   max (alpha_1 + alpha_2)      %7.2f deg   deficit %.2f deg'
      % (g0, NEED - g0))
print('\ntotal %.1f s' % (time.time() - t0))
