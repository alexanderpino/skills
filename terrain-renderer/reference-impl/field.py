"""Water surface for the pool reference render: the wave field and the jet.

Lane A of the gauntlet owns this file. Everything here answers one question --
what is the surface slope at (x, y)? -- and nothing here knows about light.

Bands, in the order they were forced on the model by observation:
  WIND    short, incoherent, uniform, killed in the lee of the shade sail
  REVERB  the diffuse late field of a reverberant basin: random phase, isotropic
  NEAR    early wall reflections from the jet, still coherent
  BOIL    the turbulent surface over the jet itself, riding a forced envelope
  WAKE    the jet's stationary wake, solved by eikonal ray tracing (wake.py)

ONE DEFINITION OF rms SLOPE, AND WHY THE FILE INSISTS ON IT
-----------------------------------------------------------
Everywhere in this file, and in the chapter,

    s = sqrt(<|grad h|^2>) = sqrt(<gx^2> + <gy^2>) = sqrt(total mean-square slope)

There is a second, equally respectable convention -- the PER-AXIS rms,
sqrt(<gx^2 + gy^2>/2), which is what an isotropic field's single-axis Gaussian
width is -- and it is smaller by exactly sqrt(2). Both are "the rms slope". The
file used to carry both at once: WIND and REVERB were normalised and printed as
sqrt(total mss), NEAR and WAKE were normalised and printed per-axis, and the
TOTAAL row added them in quadrature as though they were the same number. That is
not a cosmetic defect. Because the two bands that use the per-axis form are
normalised TO it, a target written as 0.024 put sqrt(2)*0.024 of actual slope on
the water, so the mixed convention was in the water and not only in the printout,
and the whole point of a slope budget -- weighing one band against another --
was being done with two different units on the two sides of the scale.

sqrt(total mss) is the convention picked because it is the one the rest of the
doctrine already speaks: Cox & Munk quote total mean-square slope, the focusing
number F = 0.25*d*s*k is written for it, and the chapter's independently measured
far-field figures (0.016 short, 0.055 long) are in it. It is computed in exactly
one place, `rms_slope`, and every band, every normaliser and every printed row
goes through that function or its analytic twin `_plane_rms`. Writing the
expression out by hand anywhere else is how the second convention got in.

Slope budget, and why it is the whole game
------------------------------------------
Caustic focusing on the bed goes as F = 0.25*d*s*k (d = 1.40 m, s = rms slope,
k = dominant wavenumber). F ~ 0.3-0.6 writes the soft readable cell net; F >> 1
is past focus and writes fine high-variance speckle with no legible cells. So a
band is not judged by its own slope but by its slope AT ITS OWN WAVENUMBER, and
a band carrying too much slope at too short a wavelength washes the bed out
however correct its individual numbers look.

The net is written by REVERB (~20 cm) and NEAR (~20 cm). WIND and BOIL are past
focus by construction and are allowed to be -- they own sparkle and wash, and
their slope share is small. The WAKE is the dangerous one: it starts long
(~35 cm) and SHORTENS as it travels, so it walks itself into the past-focus band.
The only thing that keeps it honest is the film damping in wake.alpha_eff, which
kills it at about 3 m -- and its normalisation, which is measured in its own near
field, not averaged over the basin.
"""
import numpy as np

import wake as _wk

X0, X1, Y0, Y1 = 0.0, 8.0, 0.0, 4.0
rng = np.random.default_rng(20260810)


def rms_slope(gx, gy):
    """THE rms slope of a sampled gradient field. s = sqrt(<gx^2> + <gy^2>).

    Every band, every normalisation target and every printed row in this file
    goes through this function. See the convention block at the top: the reason
    it exists is that the same quantity written out inline twice came out in two
    different units, and no diagnostic could see it because each band's own
    numbers stayed self-consistent."""
    return float(np.sqrt(np.mean(np.asarray(gx) ** 2 + np.asarray(gy) ** 2)))


def _plane_rms(sl):
    """Same quantity for a superposition of plane waves, analytically.

    A component with slope amplitude sl_i contributes sl_i*cos(phase) to the
    gradient ALONG ITS OWN k, so <|grad h|^2> = sum_i sl_i^2 * <cos^2> =
    sum_i sl_i^2 / 2 -- both gradient components together, not each. Hence the
    /2 here is the <cos^2> factor and NOT a per-axis split, which is the exact
    coincidence that made the two conventions hard to tell apart by eye."""
    return np.sqrt(np.sum(np.asarray(sl) ** 2) / 2.0)

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
# Band rms slopes, all as s = sqrt(<|grad h|^2>). Two of these were RESTATED, not
# retuned, when the file was put on one convention: JNEAR and WAKE were normalised
# through the per-axis expression, so the numbers written here were smaller by
# sqrt(2) than the slope they actually put on the water.
#     JNEAR  0.024 per-axis * sqrt(2) = 0.0339 -> 0.034
#     WAKE   0.068 per-axis * sqrt(2) = 0.0962 -> 0.096
# The water is unchanged to within the rounding: these are the same fields, read
# in the unit the rest of the file uses. Nothing was scaled to preserve an old
# printed total, and the printed totals duly moved (see _norm_jets).
#
# ? WIND_RMS and REVERB_RMS are CHOSEN, not derived -- there is no measurement
# behind 0.016 and 0.046 in this file. The chapter's "0.016 short, 0.055 long"
# was read off this implementation, so quoting it back as confirmation would be
# circular. What the chapter does assert independently is a RATIO (near field
# roughly twice the far field), and that is the number to judge these against.
WIND_RMS, JNEAR_RMS, REVERB_RMS = 0.016, 0.034, 0.046
# The wake's rms slope in ITS OWN near field (inside wake.build's norm_r = 0.40 m
# of the forcing peak), not an average over the basin. The other four bands sum to
# 0.075 over that patch, so sqrt(0.075^2 + 0.096^2) = 0.122 local against 0.058 in
# the far field -- the documented pair, both now in sqrt(<|grad h|^2>).
WAKE_RMS = 0.096

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
    size is the local jet width, so slope ~ eta / r_half.

    This is an ENVELOPE, one scalar, so it carries no per-axis/total ambiguity of
    its own -- but it is used as BOIL's local rms slope (BOIL's plane set is
    normalised to unit rms and then multiplied by this), so it inherits whatever
    convention that normalisation uses. _plane goes through _plane_rms, so the
    envelope is in sqrt(<|grad h|^2>) like everything else. ? the O(1) constant
    ETA_C is genuinely unknown, so the LEVEL here is a scaling argument and only
    the near/far ratio it produces is defensible."""
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
    sl = r.uniform(0.5, 1.0, nc); sl *= rms / _plane_rms(sl)
    k = 2 * np.pi / lam
    th = (r.uniform(0, 2 * np.pi, nc) if spread_deg is None
          else r.normal(np.deg2rad(20.0), np.deg2rad(spread_deg), nc))
    om = _disp(k)[0]
    return dict(kx=k * np.cos(th), ky=k * np.sin(th), amp=sl / k,
                ph=r.uniform(0, 2 * np.pi, nc) - om * 3.7)


# Every band's short end is floored at LAM_MIN. Below the minimum phase speed
# there is no propagating surface wave at all -- surface tension takes over as the
# restoring force and the branch turns round -- so wind cannot force anything
# finer and viscosity removes what is there. Octaves below LAM_MIN are detail the
# physics forbids, and on a 1.40 m bed they are pure past-focus speckle: at
# lambda = 8 mm even s = 0.01 gives F = 2.7.
LAM_MIN = 2 * np.pi * np.sqrt(SIGMA_W / (1000.0 * 9.81))    # 17.1 mm, at c_min

WIND = _plane(20, LAM_MIN, 0.070, WIND_RMS, 45.0, 11)
REVERB = _plane(44, 0.120, 0.450, REVERB_RMS, None, 12)
# the turbulent surface itself: very short, non-propagating, rides the envelope
BOIL = _plane(10, LAM_MIN, 0.045, 1.0, None, 17)

# The extended-source Huygens sum that used to live here is now inside the eikonal
# solve (wake.trace launches one fan per axial station, weighted by the forcing
# envelope), so the arc centre still lands out in the water rather than on the
# fitting -- it is just no longer a second, uncalibrated copy of the same physics.
_IMG = [(JET_XY[0], JET_XY[1]), (-JET_XY[0], JET_XY[1]), (JET_XY[0], -JET_XY[1]),
        (2 * X1 - JET_XY[0], JET_XY[1]), (JET_XY[0], 2 * Y1 - JET_XY[1])]
_NEAR = [(2 * np.pi / l, w) for l, w in ((0.30, 1.0), (0.21, 0.8), (0.15, 0.6))]
_SC = {'near': 1.0}
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

# ---------------------------------------------------------------------- the wake
# THE TRAP THIS BAND EXISTS TO AVOID. Stationary crests satisfy c(k) = U cos psi,
# so on the gravity branch k = g/(U cos psi)^2 and the WAVEVECTOR fan opens to
# +-arccos(c_min/U) ~ 78 deg. That fan is not the shape of the disturbance.
# Energy travels at c_g*khat + U, and c_g = U cos psi / 2 <= U/2, so the current
# dominates and the ENERGY fan is narrow and aligned with the jet. Summing plane
# waves over the 78 deg wavevector fan -- the obvious implementation -- sprays the
# whole basin with the fan-edge wavelengths (9 cm and shorter, and they carry the
# MOST slope because slope ~ amp*k ~ 1/cos psi), which is exactly the band that
# destroys the bed caustics. So the fan is not sampled directly: the rays are
# integrated, and the pattern lands where the energy actually goes.
_WK_GRID = (800, 400)      # 10 mm texels; nothing under ~8 cm survives the film
_WK_CACHE = {}


def _wake_field():
    """Eikonal solve, cached. Rays advect at c_g*khat + U(x) and refract on the
    drift gradient; amplitude follows wave action along the ray tube and decays by
    wake.alpha_eff. Nothing is masked or tapered: the reach is the damping."""
    if not _WK_CACHE:
        jet = _wk.Jet(JET_XY[0], JET_XY[1], depth=JET_H,
                      tilt_deg=np.degrees(JET_TILT), az_deg=np.degrees(JET_AZ),
                      d=D_NOZZLE, dp_bar=DP_BAR, cd=CD, S=S_SPREAD, B=B_DECAY)
        gx, gy = _wk.build(jet, X0, X1, Y0, Y1, _WK_GRID[0], _WK_GRID[1],
                           rms_target=WAKE_RMS)
        _WK_CACHE['gx'] = gx.astype(np.float32)
        _WK_CACHE['gy'] = gy.astype(np.float32)
    return _WK_CACHE['gx'], _WK_CACHE['gy']


def _wake(X, Y):
    """Bilinear lookup into the traced wake. 5 mm texels; the shortest thing that
    survives the film damping is ~10 cm, so this samples it many times over."""
    gxg, gyg = _wake_field()
    nx, ny = _WK_GRID
    fu = np.clip((X - np.float32(X0)) / np.float32(X1 - X0) * nx - 0.5, 0, nx - 1.001)
    fv = np.clip((Y - np.float32(Y0)) / np.float32(Y1 - Y0) * ny - 0.5, 0, ny - 1.001)
    iu = fu.astype(np.int64); iv = fv.astype(np.int64)
    du = (fu - iu).astype(np.float32); dv = (fv - iv).astype(np.float32)
    out = []
    for g in (gxg, gyg):
        out.append(((g[iv, iu] * (1 - du) + g[iv, iu + 1] * du) * (1 - dv) +
                    (g[iv + 1, iu] * (1 - du) + g[iv + 1, iu + 1] * du) * dv))
    return out[0], out[1]


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


DEPTH_FOR_F = 1.40


def _focus(s, k):
    """F = 0.25 d s k. F >> 1 is past focus (speckle, no cells); F ~ 0.3-0.6 is the
    soft readable net; the cell size on the bed runs with the dominant wavelength."""
    return 0.25 * DEPTH_FOR_F * s * k


def _spec_k(gx, gy, dx, dy):
    """Slope-energy-weighted rms wavenumber of a gradient field on a regular grid."""
    ny, nx = gx.shape
    P = np.abs(np.fft.rfft2(gx)) ** 2 + np.abs(np.fft.rfft2(gy)) ** 2
    kx = 2 * np.pi * np.fft.rfftfreq(nx, dx)[None, :]
    ky = 2 * np.pi * np.fft.fftfreq(ny, dy)[:, None]
    k2 = kx * kx + ky * ky
    P[0, 0] = 0.0
    return np.sqrt((P * k2).sum() / max(P.sum(), 1e-30))


def _plane_k(F):
    e = (F['amp'] * np.hypot(F['kx'], F['ky'])) ** 2
    return np.sqrt((e * (F['kx'] ** 2 + F['ky'] ** 2)).sum() / e.sum())


def _norm_jets():
    _report_jet()
    X, Y = np.meshgrid(np.linspace(0.3, X1 - 0.3, 260).astype(np.float32),
                       np.linspace(0.3, Y1 - 0.3, 130).astype(np.float32))
    g = _cyl(X, Y); _SC['near'] = JNEAR_RMS / rms_slope(*g)
    _wake_field()                       # trace the rays once, before anything asks
    # how far does the wake stay visible?
    sax = np.linspace(0.1, 7.8, 300)
    px = (JET_XY[0] + sax * _AIM[0]).astype(np.float32)
    py = (JET_XY[1] + sax * _AIM[1]).astype(np.float32)
    ga = _wake(px, py); amp = np.sqrt(ga[0] ** 2 + ga[1] ** 2)
    amp = np.convolve(amp, np.ones(15) / 15, 'same')
    vis = sax[amp > 0.10 * amp.max()]
    print("  drift langs de as: " + " ".join("%.2f" % u for u in _WK_U) + " m/s")
    print("  Froude U/c_min = %.1f -> stationaire golven binnen +-%.0f graden"
          % (_WK_U.max() / C_MIN, np.degrees(np.arccos(C_MIN / _WK_U.max()))))
    print("  zog zichtbaar tot %.1f m van de bron (bad is %.1f m)" % (vis[-1], X1))

    # ---- the slope budget, band by band, WITH the focusing number ---------------
    # Nothing may be left out of this table. The defect it exists to catch is a
    # band that is individually defensible and collectively fatal: correct slope,
    # correct spectrum, wrong wavenumber for the depth, and no line anywhere that
    # adds it up.
    _pk = 0.91
    jx_, jy_ = JET_XY[0] + _pk * _AIM[0], JET_XY[1] + _pk * _AIM[1]
    xxn, yyn = np.meshgrid(np.linspace(jx_ - .35, jx_ + .35, 128).astype(np.float32),
                           np.linspace(jy_ - .35, jy_ + .35, 128).astype(np.float32))
    xxf, yyf = np.meshgrid(np.linspace(5.0, 7.0, 256).astype(np.float32),
                           np.linspace(1.0, 3.0, 256).astype(np.float32))
    dn = 0.7 / 127.0; df = 2.0 / 255.0
    rows, near_v, far_v = [], 0.0, 0.0

    # EVERY s below comes out of rms_slope (or _plane_rms, its analytic twin).
    # No band writes its own rms expression -- that is what let two conventions
    # coexist here, one of them reaching all the way into the normalisation.
    # Every row is MEASURED on the two patches, none is the nominal constant read
    # back out. That matters for the TOTAAL row: WIND and REVERB are finite sets
    # of discrete components (20 and 44), so on a 2 m patch REVERB samples a few
    # percent above its 0.046 ensemble value, and a table that printed 0.046 while
    # the water carried 0.049 could not add up to the field's actual total.
    shn = shelter(xxn, yyn).astype(np.float32); shf = shelter(xxf, yyf).astype(np.float32)
    wxn, wyn = _gemm(WIND, xxn[0], yyn[:, 0]); wxf, wyf = _gemm(WIND, xxf[0], yyf[:, 0])
    rows.append(("WIND", rms_slope(wxn * shn, wyn * shn),
                 rms_slope(wxf * shf, wyf * shf), _plane_k(WIND)))
    rxn, ryn = _gemm(REVERB, xxn[0], yyn[:, 0])
    rxf, ryf = _gemm(REVERB, xxf[0], yyf[:, 0])
    rows.append(("REVERB", rms_slope(rxn, ryn), rms_slope(rxf, ryf), _plane_k(REVERB)))
    cn = _cyl(xxn, yyn); cf = _cyl(xxf, yyf)
    rows.append(("NEAR", rms_slope(*cn), rms_slope(*cf), _spec_k(cn[0], cn[1], dn, dn)))
    # BOIL rides the forcing envelope, so measure the product rather than
    # inferring it: the plane set carries unit rms, the envelope carries the rest.
    bxn, byn = _gemm(BOIL, xxn[0], yyn[:, 0]); en_ = jet_envelope(xxn, yyn)
    bxf, byf = _gemm(BOIL, xxf[0], yyf[:, 0]); ef_ = jet_envelope(xxf, yyf)
    rows.append(("BOIL", rms_slope(bxn * en_, byn * en_),
                 rms_slope(bxf * ef_, byf * ef_), _plane_k(BOIL)))
    wn = _wake(xxn, yyn); wf = _wake(xxf, yyf)
    rows.append(("WAKE", rms_slope(*wn), rms_slope(*wf),
                 _spec_k(wn[0], wn[1], dn, dn)))

    print("  band      lambda_dom   s(jet)  F(jet)   s(ver)  F(ver)")
    for nm, sn, sf, k in rows:
        near_v += sn ** 2; far_v += sf ** 2
        print("    %-7s %7.1f cm   %6.3f  %6.2f   %6.3f  %6.2f"
              % (nm, 200 * np.pi / k, sn, _focus(sn, k), sf, _focus(sf, k)))
    # The chapter's "long band" is REVERB AND NEAR together -- both are basin-scale
    # coherent water around 20 cm, and they are only separate rows here because
    # they are generated differently. Reading field.py's REVERB row against the
    # chapter's long band is comparing a part with a whole, which is a second way
    # to get a mismatched F that has nothing to do with the rms convention. The
    # lambda column below is the FAR-field value (that is the one the chapter
    # quotes); each F uses its own patch's k.
    ln = (rxn + cn[0], ryn + cn[1]); lf = (rxf + cf[0], ryf + cf[1])
    kln = _spec_k(ln[0], ln[1], dn, dn); klf = _spec_k(lf[0], lf[1], df, df)
    print("    %-7s %7.1f cm   %6.3f  %6.2f   %6.3f  %6.2f    (= REVERB + NEAR)"
          % ("LANG", 200 * np.pi / klf, rms_slope(*ln), _focus(rms_slope(*ln), kln),
             rms_slope(*lf), _focus(rms_slope(*lf), klf)))
    print("    %-7s %7s      %6.3f           %6.3f"
          % ("TOTAAL", "-", np.sqrt(near_v), np.sqrt(far_v)))
    # Restated from the old mixed-convention pair (0.09-0.11 near, 0.053 far), not
    # retuned to it. The far target was sqrt(0.016^2 + 0.046^2 + 0.020^2) with only
    # the last term per-axis; putting NEAR in the same unit (0.020*sqrt(2) = 0.028)
    # gives sqrt(0.016^2 + 0.046^2 + 0.028^2) = 0.056, and the measured patch runs
    # 0.058 because REVERB samples a shade above its nominal 0.046 there. The near
    # band moves from 0.09-0.11 to 0.11-0.14 the same way -- WIND and REVERB were
    # already in this unit, NEAR/BOIL/WAKE were not, so the total gains 1.35x and
    # not the full sqrt(2). The near/far RATIO, which is the part the chapter
    # states independently ("roughly twice"), goes 1.79 -> 2.16 and is BETTER for
    # the fix, because it was the one number the mixed units were distorting.
    print("    doel: 0.11-0.14 bij de straal, 0.058 ver weg"
          " (s = sqrt(<|grad h|^2>) overal)")


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
