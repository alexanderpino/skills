"""Water surface for the pool reference render: the wave field and the jet.

Lane A of the gauntlet owns this file. Everything here answers one question --
what is the surface slope at (x, y)? -- and nothing here knows about light.

Bands, in the order they were forced on the model by observation:
  WIND    short, incoherent, uniform, killed in the lee of the shade sail
  REVERB  the diffuse late field of a reverberant basin: random phase, isotropic
  NEAR    early wall reflections from the jet, still coherent
  BOIL    the turbulent surface over the jet itself, riding a forced envelope
  WAKE    the jet's stationary wake, solved by eikonal ray tracing (wake.py)
"""
import numpy as np

X0, X1, Y0, Y1 = 0.0, 8.0, 0.0, 4.0
rng = np.random.default_rng(20260810)

# ---------------------------------------------------------------- the return jet
# A pool return is a SUBMERGED ROUND TURBULENT JET, not a pulsing point. Its
# surface footprint is then geometry, not an authored lobe:
#   half-width      r_half(s) = S * s                  S ~ 0.094   (linear spreading)
#   centreline      U_c(s)    = B * U0 * d / s         B ~ 5.8     (1/s decay)
#   radial profile  U/U_c     = exp(-ln2 (r/r_half)^2)
#   turbulence      u' ~ 0.25 * U_c  on the axis
# The surface is a plane at radial distance h from the axis, so the jet only
# reaches it once it has spread that far -- which is why the disturbed patch is
# elongated along the aim and starts DOWNSTREAM of the fitting rather than at it.
JET_XY = (0.10, 1.15)
JET_H = 0.15                  # fitting depth below the waterline (m)
JET_TILT = np.deg2rad(6.0)    # aimed slightly up, as returns usually are
JET_AZ = np.deg2rad(20.0)
D_NOZZLE, DP_BAR, CD = 0.020, 0.80, 0.92   # 20 mm eyeball, return pressure in bar
U0 = CD * np.sqrt(2 * DP_BAR * 1e5 / 1000.0)   # Bernoulli: 0.8 bar -> 11.6 m/s
SIGMA_W = 0.0728                                # surface tension, N/m
C_MIN = (4 * 9.81 * SIGMA_W / 1000.0) ** 0.25   # 0.231 m/s, at lambda 17.1 mm
S_SPREAD, B_DECAY, TURB_INT = 0.094, 5.8, 0.25
ETA_C = 1.0                   # O(1) constant in eta ~ C u'^2 / g  (see provenance)
NU = 1.004e-6
WIND_RMS, JNEAR_RMS, REVERB_RMS = 0.016, 0.024, 0.046

_AIM = np.array([np.cos(JET_TILT) * np.cos(JET_AZ),
                 np.cos(JET_TILT) * np.sin(JET_AZ), np.sin(JET_TILT)])
_ORIG = np.array([JET_XY[0], JET_XY[1], -JET_H])


def _disp(k):
    om = np.sqrt(9.81 * k + (0.0728 / 1000.0) * k ** 3)
    return om, (9.81 + 3 * (0.0728 / 1000.0) * k ** 2) / (2 * om), 2 * NU * k ** 2


def _alpha(k):
    """Amplitude decay. Clean surface: 2 nu k^2 (bulk). A pool always carries a
    surface film, which is INEXTENSIBLE to first order: the surface can no longer
    slip, a Stokes layer of thickness sqrt(2 nu / omega) forms under it, and the
    dissipation there dominates. That gives alpha ~ k sqrt(nu omega) -- a wavelength
    dependent factor, not a tuned multiplier."""
    om = _disp(k)[0]
    return 2 * NU * k ** 2, 0.3536 * k * np.sqrt(NU * om)


def jet_envelope(X, Y):
    """rms surface slope forced by the jet's turbulence, from the jet geometry.
    eta ~ C u'^2 / g (stagnation scale of an eddy of velocity u'), and the eddy
    size is the local jet width, so slope ~ eta / r_half."""
    px, py = X - np.float32(_ORIG[0]), Y - np.float32(_ORIG[1])
    pz = np.float32(0.0 - _ORIG[2])
    sax = px * np.float32(_AIM[0]) + py * np.float32(_AIM[1]) + pz * np.float32(_AIM[2])
    sax = np.maximum(sax, np.float32(0.05))
    r2 = np.maximum(px * px + py * py + pz * pz - sax * sax, 0.0)
    rh = np.float32(S_SPREAD) * sax
    Uc = np.float32(B_DECAY * U0 * D_NOZZLE) / sax
    up = np.float32(TURB_INT) * Uc * np.exp(-np.float32(np.log(2.0)) * r2 / (rh * rh))
    return (np.float32(ETA_C) * up * up / np.float32(9.81)) / rh


def _report_jet():
    sax = np.linspace(0.05, 7.5, 400)
    xs = (JET_XY[0] + sax * _AIM[0]).astype(np.float32)
    ys = (JET_XY[1] + sax * _AIM[1]).astype(np.float32)
    e = jet_envelope(xs, ys)
    im = int(np.argmax(e))
    print("  jet: nozzle %.0f mm, U0 %.1f m/s (= %.1f m3/h), diepte %.0f cm, %.0f gr omhoog"
          % (D_NOZZLE * 1000, U0, U0 * np.pi / 4 * D_NOZZLE ** 2 * 3600,
             JET_H * 100, np.degrees(JET_TILT)))
    print("  oppervlakteverstoring piekt %.2f m stroomafwaarts, helling %.3f daar"
          % (sax[im], e[im]))
    half = e > 0.5 * e[im]
    print("  halfwaardelengte langs de as: %.2f - %.2f m"
          % (sax[half][0], sax[half][-1]))
    print("  demping, schoon vs inextensibele film (geldt alleen kort:")
    print("    bij lange golven rekt de film mee en gedraagt het oppervlak zich schoon)")
    for lam in (0.05, 0.03, 0.015, 0.008):
        k = 2 * np.pi / lam; ac, af = _alpha(k); cg = _disp(k)[1]
        print("    lambda %5.0f mm   schoon %7.2f m   film %6.2f m   (factor %.1f)"
              % (lam * 1000, cg / ac, cg / af, af / ac))


def _plane(nc, lo, hi, rms, spread_deg, seed):
    r = np.random.default_rng(seed)
    lam = np.exp(r.uniform(np.log(lo), np.log(hi), nc))
    sl = r.uniform(0.5, 1.0, nc); sl *= rms / np.sqrt(np.sum(sl ** 2) / 2.0)
    k = 2 * np.pi / lam
    th = (r.uniform(0, 2 * np.pi, nc) if spread_deg is None
          else r.normal(np.deg2rad(20.0), np.deg2rad(spread_deg), nc))
    om = _disp(k)[0]
    return dict(kx=k * np.cos(th), ky=k * np.sin(th), amp=sl / k,
                ph=r.uniform(0, 2 * np.pi, nc) - om * 3.7)


WIND = _plane(20, 0.015, 0.060, WIND_RMS, 45.0, 11)
REVERB = _plane(44, 0.120, 0.450, REVERB_RMS, None, 12)
# the turbulent surface itself: very short, non-propagating, rides the envelope
BOIL = _plane(10, 0.008, 0.025, 1.0, None, 17)

# Secondary sources along the jet axis at the free surface, weighted by the
# forcing envelope: a Huygens construction of an EXTENDED source. The waves that
# leave it are the visible arcs, and they are centred on the footprint, not on
# the fitting -- which is why the crest pattern's origin sits away from the wall.
_NS = 8
_S_AX = np.linspace(0.35, 2.6, _NS)
_SRC = np.stack([JET_XY[0] + _S_AX * _AIM[0], JET_XY[1] + _S_AX * _AIM[1]], 1)
_ARC = [(2 * np.pi / l, w) for l, w in ((0.130, 1.0), (0.095, 0.9), (0.065, 0.6))]
_APH = np.random.default_rng(23).uniform(0, 2 * np.pi, len(_ARC))
ARC_RMS = 0.055

_IMG = [(JET_XY[0], JET_XY[1]), (-JET_XY[0], JET_XY[1]), (JET_XY[0], -JET_XY[1]),
        (2 * X1 - JET_XY[0], JET_XY[1]), (JET_XY[0], 2 * Y1 - JET_XY[1])]
_NEAR = [(2 * np.pi / l, w) for l, w in ((0.30, 1.0), (0.21, 0.8), (0.15, 0.6))]
_SC = {'near': 1.0, 'arc': 1.0}
_PH = np.random.default_rng(13).uniform(0, 2 * np.pi, 8)


def shelter(x, y):
    """Wind lee under the sail. Band A only."""
    d = np.exp(-(((x - 2.10) / 2.3) ** 2 + ((y - 0.75) / 1.55) ** 2))
    return 0.40 + 0.60 * (1.0 - 0.70 * d)


def _drift(sax):
    """Mean surface drift over the jet: the momentum product, not the wave product."""
    h_ax = np.maximum(JET_H - sax * np.sin(JET_TILT), 0.0)
    rh = S_SPREAD * sax
    return (B_DECAY * U0 * D_NOZZLE / sax) * np.exp(-np.log(2.0) * (h_ax / rh) ** 2)


_WK_S = np.linspace(0.45, 2.4, 6)
_WK_U = _drift(_WK_S)
_WK_W = np.array([float(jet_envelope(np.float32(JET_XY[0] + a * _AIM[0]),
                                     np.float32(JET_XY[1] + a * _AIM[1])))
                  for a in _WK_S])
_WK_W = _WK_W / max(_WK_W.sum(), 1e-9)
_WPH = np.random.default_rng(29).uniform(0, 2 * np.pi, (len(_WK_S), 21))
ARC_RMS = 0.055


def _wake(X, Y):
    """Waves forced into a MOVING medium. Stationary crests satisfy the Doppler
    condition c(k) = U cos(psi), so on the gravity branch k = g/(U cos psi)^2 --
    a wedge of wavelengths, not a circle. With U/c_min = 3.8 here nothing can go
    upstream at all, which is precisely why a jet's pattern cannot be round."""
    dxh, dyh = np.float32(_AIM[0]), np.float32(_AIM[1])
    n = np.hypot(dxh, dyh); dxh, dyh = dxh / n, dyh / n
    gx = np.zeros(X.shape, np.float32); gy = np.zeros(X.shape, np.float32)
    for i, (sa, Us, ws) in enumerate(zip(_WK_S, _WK_U, _WK_W)):
        if Us <= C_MIN * 1.05:
            continue
        psi_max = np.arccos(C_MIN / Us) * 0.94
        psis = np.linspace(-psi_max, psi_max, 21)
        sx = np.float32(JET_XY[0] + sa * _AIM[0]); sy = np.float32(JET_XY[1] + sa * _AIM[1])
        dx = X - sx; dy = Y - sy
        along = dx * dxh + dy * dyh
        r = np.sqrt(dx * dx + dy * dy) + np.float32(0.10)
        down = (along > 0).astype(np.float32)
        for j, psi in enumerate(psis):
            c = Us * np.cos(psi)
            k = 9.81 / (c * c)                       # gravity branch, stationary
            om, cg, _ = _disp(k); al = _alpha(k)[0]  # 20-50 cm: bulk damping
            kx = k * (dxh * np.cos(psi) - dyh * np.sin(psi))
            ky = k * (dxh * np.sin(psi) + dyh * np.cos(psi))
            amp = (ws * np.cos(psi) / np.sqrt(r) * np.exp(-al * r / cg)).astype(np.float32)
            ph = (kx * dx + ky * dy + np.float32(_WPH[i, j])).astype(np.float32)
            c_ = (amp * np.cos(ph) * down).astype(np.float32)
            gx += c_ * np.float32(kx); gy += c_ * np.float32(ky)
    return gx * _SC['arc'], gy * _SC['arc']


def _cyl(X, Y):
    """Long waves radiated from the forcing region and its wall images. Long waves
    on a filmed surface are still bulk-damped, so the clean-water alpha applies."""
    gx = np.zeros(X.shape, np.float32); gy = np.zeros(X.shape, np.float32)
    for j, (k, w) in enumerate(_NEAR):
        om, cg, _ = _disp(k); al = _alpha(k)[0]
        for xi, yi in _IMG:
            dx = X - np.float32(xi); dy = Y - np.float32(yi)
            r = np.sqrt(dx * dx + dy * dy) + np.float32(0.12)
            a = w / np.sqrt(r) * np.exp(-al * r / cg)
            c = (a * k * np.cos(k * r - om * 3.7 + _PH[j])).astype(np.float32)
            gx += c * dx / r; gy += c * dy / r
    return gx * _SC['near'], gy * _SC['near']


def _gemm(F, xs, ys):
    A = F['kx'][None, :] * xs[:, None] + F['ph'][None, :]
    cA, sA = np.cos(A), np.sin(A)
    B = F['ky'][None, :] * ys[:, None]
    P = np.concatenate([np.cos(B), np.sin(B)], 1).astype(np.float32)
    o = []
    for kk in (F['kx'], F['ky']):
        Q = np.concatenate([(F['amp'] * kk)[None, :] * cA,
                            -(F['amp'] * kk)[None, :] * sA], 1).T
        o.append(P @ Q.astype(np.float32))
    return o[0], o[1]


def _pts(F, x, y):
    gx = np.zeros_like(x); gy = np.zeros_like(x)
    for i in range(len(F['kx'])):
        c = F['amp'][i] * np.cos(F['kx'][i] * x + F['ky'][i] * y + F['ph'][i])
        gx += F['kx'][i] * c; gy += F['ky'][i] * c
    return gx, gy


def _norm_jets():
    _report_jet()
    X, Y = np.meshgrid(np.linspace(0.3, X1 - 0.3, 260).astype(np.float32),
                       np.linspace(0.3, Y1 - 0.3, 130).astype(np.float32))
    g = _cyl(X, Y); _SC['near'] = JNEAR_RMS / np.sqrt((g[0] ** 2 + g[1] ** 2).mean() / 2)
    g = _wake(X, Y); _SC['arc'] = ARC_RMS / np.sqrt((g[0] ** 2 + g[1] ** 2).mean() / 2)
    # how far do the arcs stay visible?
    sax = np.linspace(0.1, 7.8, 300)
    px = (JET_XY[0] + sax * _AIM[0]).astype(np.float32)
    py = (JET_XY[1] + sax * _AIM[1]).astype(np.float32)
    ga = _wake(px, py); amp = np.sqrt(ga[0] ** 2 + ga[1] ** 2)
    amp = np.convolve(amp, np.ones(15) / 15, 'same')
    vis = sax[amp > 0.10 * amp.max()]
    print("  drift langs de as: " + " ".join("%.2f" % u for u in _WK_U) + " m/s")
    print("  Froude U/c_min = %.1f -> stationaire golven binnen +-%.0f graden"
          % (_WK_U.max() / C_MIN, np.degrees(np.arccos(C_MIN / _WK_U.max()))))
    print("  zog zichtbaar tot %.1f m van de wand (bad is %.1f m)" % (vis[-1], X1))
    _pk = 0.91
    for lab, (cx, cy) in (("piek van de straal", (JET_XY[0] + _pk * _AIM[0],
                                                  JET_XY[1] + _pk * _AIM[1])),
                          ("ver weg (>4 m)", (6.0, 2.0))):
        xx, yy = np.meshgrid(np.linspace(cx - .2, cx + .2, 90).astype(np.float32),
                             np.linspace(cy - .2, cy + .2, 90).astype(np.float32))
        g = _cyl(xx, yy); tot = (g[0] ** 2 + g[1] ** 2).mean() / 2
        tot += (jet_envelope(xx, yy) ** 2).mean()
        tot += REVERB_RMS ** 2 + (WIND_RMS * shelter(xx, yy).mean()) ** 2
        print("  rms-helling %-19s %.3f" % (lab, np.sqrt(tot)))


def grad_grid(xs, ys):
    wx, wy = _gemm(WIND, xs, ys)
    m = shelter(xs[None, :], ys[:, None]).astype(np.float32)
    rx_, ry_ = _gemm(REVERB, xs, ys)
    bx, by = _gemm(BOIL, xs, ys)
    gx, gy = wx * m + rx_, wy * m + ry_
    X = np.broadcast_to(xs[None, :].astype(np.float32), gx.shape)
    Y = np.broadcast_to(ys[:, None].astype(np.float32), gx.shape)
    env = jet_envelope(X, Y)
    jx, jy = _cyl(X, Y)
    ax_, ay_ = _wake(X, Y)
    return gx + jx + ax_ + bx * env, gy + jy + ay_ + by * env


def grad_points(x, y):
    wx, wy = _pts(WIND, x, y); m = shelter(x, y)
    rx_, ry_ = _pts(REVERB, x, y)
    bx, by = _pts(BOIL, x, y)
    xf, yf = x.astype(np.float32), y.astype(np.float32)
    env = jet_envelope(xf, yf)
    jx, jy = _cyl(xf, yf)
    ax_, ay_ = _wake(xf, yf)
    return (wx * m + rx_ + jx + ax_ + bx * env,
            wy * m + ry_ + jy + ay_ + by * env)




def normal_from_grad(gx, gy):
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    return -gx * inv, -gy * inv, inv


def surface_normal_grid(xs, ys):
    """Normals on a separable grid -- the caustic pass calls this."""
    return normal_from_grad(*grad_grid(xs, ys))


def surface_normal_points(x, y):
    """Normals at arbitrary points -- the camera pass calls this."""
    return normal_from_grad(*grad_points(x, y))
