"""SCOUT MEASUREMENT -- how close the shipped surface gets to overturning.

Read-only against terrain-renderer/reference-impl. Nothing here is imported by
the render or the suite; it is a measuring instrument for the price document.
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
import optics as OPT                    # noqa: E402

# `run_bay()` costs 117.8 s and every number below needs it, so it is cached to
# a pickle OUTSIDE the repository. Set SCOUT_CACHE to choose where.
SCR = os.environ.get('SCOUT_CACHE', '/tmp/') + os.sep
t0 = time.time()
if os.path.exists(SCR + 'bay.pkl'):
    bay = pickle.load(open(SCR + 'bay.pkl', 'rb'))
else:
    bay = B.run_bay()
    pickle.dump(bay, open(SCR + 'bay.pkl', 'wb'))
print('bay loaded  %.1f s' % (time.time() - t0))
t1 = time.time()
w = RND.Water(bay)
print('Water built %.1f s   spectral_on=%s bundle=%s'
      % (time.time() - t1, RND.SPECTRAL_ON, w.bundle is not None))

tr = bay['tr']
x, y, d = w.x, w.y, w.d
dx = float(x[1] - x[0])
dy = float(y[1] - y[0])
wet = d > B.D_MIN
print('\ngrid  x %d cells dx=%.2f m   y %d cells dy=%.2f m   wet cells %d'
      % (x.size, dx, y.size, dy, wet.sum()))

# =====================================================================  A
print('\n' + '=' * 72)
print('A -- THE SCENE, AND WHICH BREAKER CLASS IT IS')
print('=' * 72)
print('T_SWELL %.2f s   H0_SWELL %.2f m   theta0 %.1f deg   GAMMA_B %.3f'
      % (B.T_SWELL, B.H0_SWELL, math.degrees(B.THETA0_SWELL), B.GAMMA_B))
L0 = B.deep_wavelength(B.T_SWELL)
tan_face = B.beach_face_slope()
print('deep wavelength L0 %.2f m   beach-face slope tan_beta %.5f (1:%.1f)'
      % (L0, tan_face, 1.0 / tan_face))
# the local slope at the break point, per row, from the bed itself
rows = range(0, y.size, max(1, y.size // 9))
xi0 = B.iribarren(tan_face, B.H0_SWELL, L0)
print('xi_0 (deep quantities, Dean face slope) %.4f -> %s'
      % (xi0, B.breaker_class(xi0, 'deep')))
bp_rows = []
for j in range(y.size):
    trj = B.row_slice(tr, j)
    bp = B.breakpoints(trj)
    bp_rows.append(bp)
nbp = np.array([len(b) for b in bp_rows])
print('breaker-index crossings per alongshore row: min %d  median %d  max %d'
      % (nbp.min(), int(np.median(nbp)), nbp.max()))
xb = np.array([b[0]['x'] for b in bp_rows if b])
db = np.array([b[0]['d'] for b in bp_rows if b])
Hb = np.array([b[0]['H'] for b in bp_rows if b])
print('seaward breakpoint: x %.1f..%.1f m   d %.3f..%.3f m   H_b %.3f..%.3f m'
      % (xb.min(), xb.max(), db.min(), db.max(), Hb.min(), Hb.max()))
# local bed slope at the break point, per row, and xi_b in LOCAL quantities
mloc, xib = [], []
for j in range(y.size):
    if not bp_rows[j]:
        continue
    i = bp_rows[j][0]['i']
    m = -(w.h[j, min(i + 5, x.size - 1)] - w.h[j, max(i - 5, 0)]) / (10.0 * dx)
    m = abs(float(m))
    mloc.append(m)
    Lb = 2.0 * math.pi / float(tr['k'][j, i])
    xib.append(B.iribarren(m, bp_rows[j][0]['H'], Lb))
mloc = np.array(mloc)
xib = np.array(xib)
print('local bed slope at breaking  median %.5f (1:%.0f)   xi_b median %.4f'
      ' -> %s' % (np.median(mloc), 1.0 / np.median(mloc), np.median(xib),
                  B.breaker_class(float(np.median(xib)), 'local')))
print('xi_b range %.4f .. %.4f' % (xib.min(), xib.max()))
cls = [B.breaker_class(float(v), 'local') for v in xib]
for nm in ('spilling', 'plunging', 'surging/collapsing'):
    print('   rows classed %-20s %d / %d' % (nm, cls.count(nm), len(cls)))

# the two-partition climate, evaluated on THIS bed (no re-run of the morphology)
jmid = y.size // 2
cb = B.climate_breakpoints(x, w.h[jmid], climate=B.CLIMATE_SCENE)
print('\noffshore climate partitions (weight, H0, T):')
for p in B.CLIMATE_SCENE:
    print('   %.3f  H0 %.3f m  T %.2f s' % tuple(p))
print('climate_breakpoints on the SHIPPED bed, mid row: n=%d  per_partition=%s'
      % (cb['n'], cb['per_partition']))
print('   lines at x = %s m ; depths %s m'
      % (', '.join('%.1f' % v for v in cb['x']),
         ', '.join('%.3f' % v for v in cb['d'])))

# =====================================================================  B
print('\n' + '=' * 72)
print('B -- THE NONLINEAR SURFACE STATE (wave 5) AND ITS OWN VALIDITY')
print('=' * 72)
Ur = w.Ur[wet]
r_raw, r_lim, r_use = w.r2_raw[wet], w.r2_lim[wet], w.r2[wet]
print('Ursell  median %.3f  p99 %.3f  max %.3f   (Stokes/cnoidal boundary %.3f)'
      % (np.median(Ur), np.percentile(Ur, 99), Ur.max(), B.URSELL_STOKES_LIMIT))
print('fraction of wet bay past the boundary %.4f' %
      np.mean(Ur > B.URSELL_STOKES_LIMIT))
print('r asked for by Stokes-2  median %.3f  max %.3f' %
      (np.median(r_raw), r_raw.max()))
print('secondary-crest limit    %.4f .. %.4f' % (r_lim.min(), r_lim.max()))
print('FRACTION OF WET BAY WHERE THE VALIDITY CLAMP BITES  %.4f'
      % w.r2_clamped)
clam = (w.r2_raw > w.r2_lim) & wet
print('clamped cells %d of %d wet' % (clam.sum(), wet.sum()))
if clam.any():
    xi_c = np.where(clam)[1]
    print('   clamped cells span x %.1f .. %.1f m   depth %.3f .. %.3f m'
          % (x[xi_c].min(), x[xi_c].max(), d[clam].min(), d[clam].max()))
    print('   median clamped x %.1f m against seaward breakpoint median %.1f m'
          % (np.median(x[xi_c]), np.median(xb)))
    print('   r_raw/r_lim over the clamped set: median %.2f  max %.2f'
          % (np.median((w.r2_raw / w.r2_lim)[clam]),
             (w.r2_raw / w.r2_lim)[clam].max()))
Sk, As = B.surface_moments(w.r2, w.psi2)
print('surface_moments over the wet bay:  Sk %.4f..%.4f   As %.4f..%.4f'
      % (Sk[wet].min(), Sk[wet].max(), As[wet].min(), As[wet].max()))
print('   |As| median %.4f  p99 %.4f   (nothing outside beach.py and the '
      'suite reads it)' % (np.median(np.abs(As[wet])),
                           np.percentile(np.abs(As[wet]), 99)))

# =====================================================================  C
print('\n' + '=' * 72)
print('C -- THE CEILING OF THE REPRESENTATION, IN CLOSED FORM')
print('=' * 72)
ak = 0.5 * w.H * w.k
gain_used = B.slope_gain(w.r2, w.psi2)
gain_ceil = B.slope_gain(w.r2_lim, w.psi2)
need1 = B.snell_cone_face_deg()
print('a*k (linear max face slope) over the wet bay  max %.4f = %.2f deg'
      % (ak[wet].max(), math.degrees(math.atan(ak[wet].max()))))
print('slope_gain at the SHIPPED (r, psi)            max %.4f' %
      gain_used[wet].max())
print('slope_gain at the CLAMP LIMIT (r_lim, psi)    max %.4f' %
      gain_ceil[wet].max())
cl_used = (ak * gain_used)[wet].max()
cl_ceil = (ak * gain_ceil)[wet].max()
print('closed-form ceiling, shipped r   %.4f = %.2f deg' %
      (cl_used, math.degrees(math.atan(cl_used))))
print('closed-form ceiling, r at limit  %.4f = %.2f deg' %
      (cl_ceil, math.degrees(math.atan(cl_ceil))))
print('Stokes 120 deg corner            %.4f = %.2f deg' %
      (math.tan(math.radians(B.STOKES_FACE_DEG)), B.STOKES_FACE_DEG))
print('one-face Snell cone  90-asin(1/n) %.4f = %.2f deg' %
      (math.tan(math.radians(need1)), need1))
print('two-cone SUM criterion alpha1+alpha2 >= %.2f deg (chapter 12)'
      % (2.0 * need1))

# =====================================================================  D
print('\n' + '=' * 72)
print('D -- THE FACE ANGLE OF THE SHIPPED SURFACE, MEASURED')
print('=' * 72)
NX, NY = 900, 100
gx, gy = np.meshgrid(np.linspace(x[0] + 5, x[-1] - 5, NX),
                     np.linspace(y[0] + 20, y[-1] - 20, NY))
dg = w.sample(gx, gy, d)
qg = w.sample(gx, gy, w.q_b)
wetg = dg > B.D_MIN
surfg = qg > 0.01


def census(eps, spec, nt, tag):
    w.spectral_on = spec
    smax = np.zeros_like(gx)
    allv = []
    for q in range(nt):
        t = q * B.T_SWELL / nt
        zx, zy = RND.surface_slope(w, gx, gy, t, eps=eps)
        s = np.hypot(zx, zy)
        smax = np.maximum(smax, s)
        allv.append(s[wetg])
    a = np.concatenate(allv)
    deg = lambda v: math.degrees(math.atan(v))
    print('\n[%s] eps=%.3f m  spectral=%s  %d instants over one period'
          % (tag, eps, spec, nt))
    print('   max face angle       %.4f = %6.2f deg' % (a.max(), deg(a.max())))
    for p in (50, 99, 99.9, 99.99):
        v = np.percentile(a, p)
        print('   p%-6s            %.4f = %6.2f deg' % (p, v, deg(v)))
    for lim, nm in ((30.0, 'Stokes 30 deg'), (need1, '41.48 deg one-face')):
        tl = math.tan(math.radians(lim))
        print('   share of wet samples over %-18s %.3e' % (nm, np.mean(a > tl)))
    # surf zone only, using the per-sample max over the period
    ss = smax[surfg]
    print('   SURF ZONE (q_b>0.01), per-point max over the period:')
    print('      max %6.2f deg   p99.9 %6.2f deg   median %6.2f deg'
          % (deg(ss.max()), deg(np.percentile(ss, 99.9)),
             deg(np.median(ss))))
    return smax, a


NT = 8
s_on, a_on = census(0.5, True, NT, 'shipped')
s_off, a_off = census(0.5, False, NT, 'carrier only')
s_e2, _ = census(0.125, True, 4, 'eps/4')
w.spectral_on = True

deg = lambda v: math.degrees(math.atan(v))
print('\nBAND LIMIT OF THE SHIPPED DIFFERENCE OPERATOR:')
print('   max angle at eps=0.5 m  %.2f deg ; at eps=0.125 m %.2f deg ; x%.3f'
      % (deg(s_on.max()), deg(s_e2.max()), s_e2.max() / s_on.max()))

jm, im = np.unravel_index(np.argmax(s_on), s_on.shape)
xm, ym = gx[jm, im], gy[jm, im]
print('\nWHERE THE STEEPEST FACE IS:')
print('   x %.1f m   y %.1f m   depth %.3f m   q_b %.4f   angle %.2f deg'
      % (xm, ym, dg[jm, im], qg[jm, im], deg(s_on.max())))
print('   seaward breakpoint on that row is near x %.1f m' % np.median(xb))

# --- and a fine zoom around it, so the coarse grid's sampling is not the answer
zx_, zy_ = np.meshgrid(np.linspace(xm - 40, xm + 40, 400),
                       np.linspace(ym - 40, ym + 40, 120))
zmax = np.zeros_like(zx_)
for q in range(24):
    t = q * B.T_SWELL / 24
    a_, b_ = RND.surface_slope(w, zx_, zy_, t, eps=0.5)
    zmax = np.maximum(zmax, np.hypot(a_, b_))
print('   FINE ZOOM 80x80 m at 0.2 m, 24 instants: max %.2f deg (coarse %.2f)'
      % (deg(zmax.max()), deg(s_on.max())))

# =====================================================================  E
print('\n' + '=' * 72)
print('E -- THE KINEMATIC OVERTURNING CRITERION, u_crest / c')
print('=' * 72)
print('In shallow water a long wave carries u = eta*sqrt(g/d) and c = sqrt(gd)')
print('(beach.ur_half_derived states the first; beach.celerity the second),')
print('so u/c = eta/d exactly, and the solitary-wave form is eta/(d+eta).')
print('Overturning is u_crest >= c. Both forms are reported.')
NT2 = 24
w.spectral_on = True
eta_max = np.full(gx.shape, -1e9)
for q in range(NT2):
    t = q * B.T_SWELL / NT2
    e = RND.free_surface(w, gx, gy, t)
    eta_max = np.maximum(eta_max, e)
m = surfg & wetg
uc1 = eta_max / np.maximum(dg, B.D_MIN)
uc2 = eta_max / np.maximum(dg + eta_max, B.D_MIN)
print('\nover the SURF ZONE (%d samples):' % m.sum())
print('   eta_crest / d          median %.4f  p99.9 %.4f  max %.4f'
      % (np.median(uc1[m]), np.percentile(uc1[m], 99.9), uc1[m].max()))
print('   eta_crest / (d+eta)    median %.4f  p99.9 %.4f  max %.4f'
      % (np.median(uc2[m]), np.percentile(uc2[m], 99.9), uc2[m].max()))
print('   share with u/c >= 1 (solitary form) %.3e' % np.mean(uc2[m] >= 1.0))
Hd = (w.H / np.maximum(w.d, B.D_MIN))[wet]
print('\nH/d over the wet bay   median %.4f  p99 %.4f  max %.4f  '
      '(gamma_b %.3f)' % (np.median(Hd), np.percentile(Hd, 99), Hd.max(),
                          B.GAMMA_B))
print('   share of wet bay with H/d >= gamma_b  %.4f' %
      np.mean(Hd >= B.GAMMA_B))
print('   McCowan limit H/d=0.78 gives u/c = 0.78/1.78 = %.4f' %
      (0.78 / 1.78))

np.savez(SCR + 'overturn.npz', gx=gx, gy=gy, dg=dg, qg=qg,
         s_on=s_on, s_off=s_off, eta_max=eta_max, uc1=uc1, uc2=uc2,
         xb=xb, clam=clam.astype(np.uint8), x=x, y=y, d=d, h=w.h)
print('\ntotal %.1f s' % (time.time() - t0))
