"""SCOUT MEASUREMENT 2 -- does this project's own domain contain ANY place
where the wave would plunge rather than spill?

Cheap: reads the pickled bay only. No Water, no render.
"""
import math
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'terrain-renderer', 'reference-impl'))
import beach as B                       # noqa: E402

SCR = os.environ.get('SCOUT_CACHE', '/tmp/') + os.sep
if os.path.exists(SCR + 'bay.pkl'):
    bay = pickle.load(open(SCR + 'bay.pkl', 'rb'))
else:
    bay = B.run_bay()
    pickle.dump(bay, open(SCR + 'bay.pkl', 'wb'))
x, y, h, tr = bay['x'], bay['y'], bay['h'], bay['tr']
dx = float(x[1] - x[0])

print('=' * 72)
print('THE BREAKER CLASS OVER THE WHOLE DOMAIN, AND THE DERIVED SLOPE LIMITS')
print('=' * 72)
print('saturation_slope_limit 2K/5 = %.4f  (above it no surf zone saturates --'
      ' the reflective end)' % B.saturation_slope_limit())
print('Battjes deep thresholds  spilling < 0.5 < plunging < 3.3 < surging')
print('Battjes local thresholds spilling < 0.4 < plunging < 2.0 < surging')

# the seaward-facing bed slope everywhere, in the cross-shore direction
# THE SIGN MATTERS AND IT BIT THIS SCRIPT ONCE. x increases SHOREWARD and h
# increases with it, so -grad(h) is NEGATIVE on a shoaling bed; taking argmax
# of the signed array finds the trough's landward wall instead of the bar's
# seaward flank. The magnitude is what the Iribarren number wants.
m = np.abs(-np.gradient(h, dx, axis=1))
d = tr['d']
wet = d > B.D_MIN
print('\nCROSS-SHORE BED SLOPE over the wet bay (|m|):')
q = np.abs(m[wet])
for p in (50, 90, 99, 99.9):
    print('   p%-5s %.4f  (1:%.1f)' % (p, np.percentile(q, p),
                                       1.0 / max(np.percentile(q, p), 1e-9)))
print('   max    %.4f  (1:%.1f)' % (q.max(), 1.0 / max(q.max(), 1e-9)))
print('   share of wet bay steeper than 2K/5 = %.4f : %.4f'
      % (B.saturation_slope_limit(), np.mean(q > B.saturation_slope_limit())))

# xi_b cell by cell: the LOCAL surf-similarity number everywhere breaking
k = tr['k']
H = tr['H']
L = 2.0 * math.pi / np.maximum(k, 1e-9)
xi = np.abs(m) / np.sqrt(np.maximum(H / L, 1e-12))
brk = tr['brk'].astype(bool) if 'brk' in tr else (H / np.maximum(d, B.D_MIN)
                                                 >= B.GAMMA_B)
sel = wet & brk
print('\nLOCAL xi over every BREAKING cell (%d cells):' % sel.sum())
for p in (50, 90, 99, 99.9):
    print('   p%-5s %.4f' % (p, np.percentile(xi[sel], p)))
print('   max    %.4f' % xi[sel].max())
print('   share plunging (xi >= 0.4, local convention)  %.5f'
      % np.mean(xi[sel] >= 0.4))
print('   share surging  (xi >= 2.0, local convention)  %.5f'
      % np.mean(xi[sel] >= 2.0))

# and on the SUBAERIAL/rock side: what is the steepest submerged slope the
# coastal loop produced anywhere, at any depth a wave could break in?
band = wet & (d > 0.5) & (d < 5.0)
print('\nIN THE 0.5-5 m BAND (%d cells): steepest |m| %.4f, share > 2K/5 %.5f'
      % (band.sum(), np.abs(m[band]).max(),
         np.mean(np.abs(m[band]) > B.saturation_slope_limit())))
jj, ii = np.where(band & (np.abs(m) > B.saturation_slope_limit()))
if jj.size:
    print('   steep cells at x %.1f..%.1f m, depth %.2f..%.2f m'
          % (x[ii].min(), x[ii].max(), d[jj, ii].min(), d[jj, ii].max()))
    print('   their xi: median %.4f  max %.4f'
          % (np.median(xi[jj, ii]), xi[jj, ii].max()))

# what deep-water steepness WOULD be needed to plunge on this bed
print('\nWHAT WOULD HAVE TO CHANGE, in the scene declaration:')
tanb = float(np.median(np.abs(m[band])))
for T in (9.0, 12.0, 15.0, 18.0):
    L0 = B.deep_wavelength(T)
    # xi_0 = tanb / sqrt(H0/L0) >= 0.5  ->  H0 <= tanb^2 L0 / 0.25
    H0 = tanb ** 2 * L0 / 0.25
    print('   T = %4.1f s : on tan_beta = %.4f, xi_0 >= 0.5 needs H0 <= %.2f m'
          % (T, tanb, H0))
print('   (the scene declares H0 = %.2f m at T = %.1f s)'
      % (B.H0_SWELL, B.T_SWELL))


# ===========================================================================
# THE SLOPE WINDOW IS THE INSTRUMENT -- the ladder behind the price document's
# section 1.1, and the correction it records. A slope differenced over 20 m on
# a bed whose bar flank is 16 m wide reports the Dean ramp the bar sits on and
# not the face the wave meets, and the two give opposite breaker classes.
# ===========================================================================
import beach_foam as FM                                       # noqa: E402

print('\n' + '=' * 72)
print('THE SLOPE WINDOW IS THE INSTRUMENT -- xi_b at the breakpoint')
print('=' * 72)
for half in (10, 5, 2, 1):
    vals, mm = [], []
    for j in range(y.size):
        bp = B.breakpoints(B.row_slice(tr, j))
        if not bp:
            continue
        i = bp[0]['i']
        lo, hi = max(i - half, 0), min(i + half, x.size - 1)
        mloc = abs(h[j, hi] - h[j, lo]) / ((hi - lo) * dx)
        Lb = 2.0 * math.pi / tr['k'][j, i]
        vals.append(B.iribarren(mloc, bp[0]['H'], Lb))
        mm.append(mloc)
    vals, mm = np.array(vals), np.array(mm)
    print('  window +-%2d cells (%3.0f m): |m| med %.4f (1:%.1f)  xi_b med %.3f'
          '  range %.3f..%.3f  rows plunging %d/%d'
          % (half, 2 * half * dx, np.median(mm), 1.0 / np.median(mm),
             np.median(vals), vals.min(), vals.max(),
             int((vals >= 0.4).sum()), vals.size))

print('\nAT THE STEEPEST CELL OF THE BAR FLANK, per row -- the face the wave'
      ' meets:')
vals, xs, ms, ds = [], [], [], []
for j in range(y.size):
    bp = B.breakpoints(B.row_slice(tr, j))
    if not bp:
        continue
    i = bp[0]['i']
    lo, hi = max(i - 15, 0), min(i + 15, x.size - 1)
    ii = lo + int(np.argmax(m[j, lo:hi]))
    if d[j, ii] < B.D_MORPH_MIN:
        continue
    Lb = 2.0 * math.pi / tr['k'][j, ii]
    vals.append(B.iribarren(m[j, ii], H[j, ii], Lb))
    xs.append(x[ii])
    ms.append(m[j, ii])
    ds.append(d[j, ii])
vals = np.array(vals)
print('  rows %d  x %.0f..%.0f m  d %.2f..%.2f m'
      % (vals.size, min(xs), max(xs), min(ds), max(ds)))
print('  |m| median %.4f (1:%.1f)  max %.4f (1:%.1f)'
      % (np.median(ms), 1.0 / np.median(ms), max(ms), 1.0 / max(ms)))
print('  xi median %.3f  range %.3f..%.3f'
      % (np.median(vals), vals.min(), vals.max()))
print('  rows PLUNGING (local xi>=0.4) %d/%d ; deep convention (>=0.5) %d/%d'
      % (int((vals >= 0.4).sum()), vals.size,
         int((vals >= 0.5).sum()), vals.size))

print('\nTHE CROSS-SHORE PROFILE AT THE MIDDLE ROW, across the bar flank:')
qb = FM.breaking_fraction_2d(d, H)
j = y.size // 2
print('     x       h       d      H     H/d     |m|     1:x      xi     q_b')
for i in range(int(470 / dx), int(500 / dx)):
    if d[j, i] <= B.D_MIN:
        continue
    print('%6.0f %7.3f %7.3f %6.3f %6.3f %7.4f %7.1f %7.3f %7.3f'
          % (x[i], h[j, i], d[j, i], H[j, i], H[j, i] / max(d[j, i], 1e-3),
             m[j, i], 1.0 / max(m[j, i], 1e-9), xi[j, i], qb[j, i]))
