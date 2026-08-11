"""
Stationary wake of a submerged jet, solved properly: EIKONAL RAY TRACING through
the jet's own surface-drift field.

Steady current U(x): the Doppler-shifted dispersion is  H(x,k) = sigma(k) + k.U(x).
A pattern held steady in the lab frame has zero absolute frequency, so H = 0, and
the rays follow Hamilton's equations

    dx/dt =  dH/dk = c_g * khat + U(x)
    dk/dt = -dH/dx = -(grad U)^T k

Phase accumulates as dphi = k.dx, and amplitude follows from wave-action
conservation along the ray tube, A^2 * |dx/dt| * W = const, with W the tube width
taken from neighbouring rays. Viscous decay exp(-int alpha dt), alpha = 2 nu k^2.

Nothing here is masked, tapered or shaped by hand: the wedge edge appears where
neighbouring rays converge, and the crests curve because the current refracts them.
"""
import numpy as np

G, SIG, RHO, NU = 9.81, 0.0728, 1000.0, 1.004e-6
C_MIN = (4 * G * SIG / RHO) ** 0.25          # 0.231 m/s
LAM_FILM = 0.075        # where the film stops being inextensible (see alpha_eff)
C_SRC = 0.186           # forcing coherence scale / jet half-width (footprint_sigma)


def alpha_eff(k):
    """Amplitude decay rate along the ray.

    Clean surface: Lamb's bulk value 2*nu*k^2. A pool always carries a film
    (sunscreen, body oils), and where the film cannot stretch it is INEXTENSIBLE:
    the surface can no longer slip, a Stokes layer of thickness sqrt(2 nu/omega)
    forms under it, and alpha ~ 0.35*k*sqrt(nu*omega) -- a factor 3-9 stronger
    over the 8-50 mm band. The film limit holds only at the short end; past about
    10 cm the film simply stretches and the surface behaves clean. So the two
    limits are blended on wavelength, which is a statement about the film, not a
    tuned multiplier.

    This is the term that decides how far the jet's wake reaches. The wake
    SHORTENS as it travels (k = g/(U cos psi)^2 with U decaying), so it walks
    itself into the film-damped band and dies -- the observed "a return's
    signature is gone by mid-pool". Integrating it with the bulk value instead
    lets 5-10 cm waves ring across the whole basin, which loads the entire pool
    with short-wave slope and dissolves the bed caustic net.
    """
    om = np.sqrt(G * k + (SIG / RHO) * k ** 3)
    a_bulk = 2 * NU * k ** 2
    a_film = 0.3536 * k * np.sqrt(NU * om)
    w = 1.0 / (1.0 + (2 * np.pi / (k * LAM_FILM)) ** 2)     # ->1 short, ->0 long
    return a_bulk + w * (a_film - a_bulk)


class Jet:
    # The defaults are the scene's return fitting, so that a caller who omits
    # them gets the pool this module was written for and not a stale one:
    # az_deg went 20 -> 180 with the fitting's move to the east end wall
    # (field.py's JET_AZ, photo-spec section C), and then 180 -> 188.5 when the
    # wave-6 arbitration turned the fitting to get the wake off the camera
    # azimuth. field.py passes every one of these explicitly; the defaults are
    # documentation, and a default that disagrees with the scene is a trap for
    # the next caller.
    #
    # NOTE that this azimuth is measured in PLAN: `ax` below is a unit vector in
    # the (x, y) plane, so `s` is the plan-projected axial coordinate and not the
    # slant distance along the tilted axis. field.py's `_AIM` is the 3-D axis, so
    # its forcing peak reads 0.92 m along that axis but 0.912 m downstream in
    # plan -- and it is the plan number the fitting's position was solved
    # against. `s_pk` in `build` is written to two decimals, so nothing here
    # turns on the 8 mm; it is recorded because a reader comparing the two files
    # will otherwise find the same symbol meaning two things.
    def __init__(self, x, y, depth=0.15, tilt_deg=6.0, az_deg=188.5,
                 d=0.020, dp_bar=0.80, cd=0.92, S=0.094, B=5.8):
        self.p = np.array([x, y]); self.h = depth; self.S, self.B, self.d = S, B, d
        self.U0 = cd * np.sqrt(2 * dp_bar * 1e5 / RHO)
        self.tilt = np.deg2rad(tilt_deg)
        self.ax = np.array([np.cos(np.deg2rad(az_deg)), np.sin(np.deg2rad(az_deg))])

    def drift(self, x, y):
        """Mean surface drift: the jet's momentum product. Axial coordinate s and
        perpendicular offset in the surface plane; the axis rises with the tilt."""
        dx, dy = x - self.p[0], y - self.p[1]
        s = np.maximum(dx * self.ax[0] + dy * self.ax[1], 1e-3)
        perp = dx * (-self.ax[1]) + dy * self.ax[0]
        h_ax = np.maximum(self.h - s * np.sin(self.tilt), 0.0)
        rh = self.S * s
        r2 = perp * perp + h_ax * h_ax                      # 3-D offset from the axis
        Uc = self.B * self.U0 * self.d / s
        mag = Uc * np.exp(-np.log(2.0) * r2 / (rh * rh))
        return mag * self.ax[0], mag * self.ax[1]

    def grad(self, x, y, e=0.01):
        ux1, uy1 = self.drift(x + e, y); ux0, uy0 = self.drift(x - e, y)
        ux3, uy3 = self.drift(x, y + e); ux2, uy2 = self.drift(x, y - e)
        return ((ux1 - ux0) / (2 * e), (uy1 - uy0) / (2 * e),
                (ux3 - ux2) / (2 * e), (uy3 - uy2) / (2 * e))   # dUx/dx dUy/dx dUx/dy dUy/dy

    def forcing(self, s):
        """rms surface slope the jet's turbulence forces at axial station s.
        eta ~ u'^2/g over an eddy of size r_half, so slope ~ eta/r_half. This is
        the Huygens weight of a secondary source at s: the surface can only be
        driven where the jet has spread far enough to reach it."""
        s = np.maximum(np.asarray(s, float), 0.05)
        h_ax = np.maximum(self.h - s * np.sin(self.tilt), 0.0)
        rh = self.S * s
        up = 0.25 * (self.B * self.U0 * self.d / s) * np.exp(-np.log(2.0) * (h_ax / rh) ** 2)
        return (up * up / G) / rh

    def footprint_sigma(self, s):
        """Coherence scale of the jet's forcing at the free surface.

        This term fixes the LAUNCH SPECTRUM, and leaving it out is the second half
        of the wavevector-fan trap. The stationary condition k = g/(U cos psi)^2
        says WHICH wavelengths can stand still in the drift; it says nothing about
        which ones get excited. A forcing patch of rms size sigma radiates the
        Fourier transform of itself, amplitude ~ exp(-k^2 sigma^2/2), so it cannot
        make waves short compared to its own coherence scale. Launch the fan flat
        instead and the fan-edge components arrive at full amplitude -- and they
        carry the most slope of all, since slope ~ A*k ~ 1/cos^2 psi -- so a 4 cm
        band lands on the water with more slope than the whole rest of the pool.

        Since slope goes as A*k ~ k*exp(-k^2 sigma^2/2), the launched slope peaks
        at k = 1/sigma, and sigma is therefore the one number here that a
        photograph pins down rather than the geometry. It is calibrated, not
        invented: the observed crest spacing in the jet's visible bands is 5-15 cm
        and the chapter's independent statement is that the return launches
        short-gravity waves of 6-14 cm, so sigma sits at C_SRC * r_half with
        C_SRC set to land the peak at ~10 cm. Everything else about the wake --
        where it goes, how it curves, how far it reaches -- then follows from the
        ray solve with nothing else to turn.

        The scale RUNS with the jet: sigma ~ r_half(s), so stations near the
        fitting radiate shorter waves than stations further out, which is why the
        crest spacing tightens toward the origin of the pattern.
        """
        s = max(float(s), 0.05)
        return C_SRC * self.S * s


def trace(jet, n_psi=161, n_step=900, dt=0.02, s_launch=(0.7, 1.0, 1.4, 1.9)):
    """Launch fans of stationary gravity waves from points along the jet axis.
    Each fan is weighted by the local forcing envelope -- a Huygens sum over an
    EXTENDED source, which is why the crest pattern is centred out in the water
    rather than on the fitting."""
    P, K, PH, AM = [], [], [], []
    w_src = jet.forcing(np.asarray(s_launch, float))
    w_src = w_src / max(w_src.sum(), 1e-12)
    for i_src, s0 in enumerate(s_launch):
        p0 = jet.p + s0 * jet.ax
        Ux, Uy = jet.drift(*p0); U = np.hypot(Ux, Uy)
        if U <= C_MIN * 1.02:
            continue
        psi_max = np.arccos(C_MIN / U)
        psi = np.linspace(-psi_max * 0.985, psi_max * 0.985, n_psi)
        uh = np.array([Ux, Uy]) / U
        kmag = G / (U * np.cos(psi)) ** 2                    # gravity branch, stationary
        khat = np.stack([-uh[0] * np.cos(psi) + uh[1] * np.sin(psi),
                         -uh[1] * np.cos(psi) - uh[0] * np.sin(psi)], 1)
        x = np.repeat(p0[None, :], n_psi, 0)
        k = khat * kmag[:, None]
        # radiation efficiency of a source of finite size -- see footprint_sigma
        a0 = np.exp(-0.5 * (kmag * jet.footprint_sigma(s0)) ** 2)
        ph = np.zeros(n_psi); att = np.zeros(n_psi)
        xs, ks, phs, ats = [x.copy()], [k.copy()], [ph.copy()], [att.copy()]
        for _ in range(n_step):
            for _sub in (0, 1):                              # RK2
                km = np.hypot(k[:, 0], k[:, 1]) + 1e-9
                cg = 0.5 * np.sqrt(G / km)
                ux, uy = jet.drift(x[:, 0], x[:, 1])
                vx = cg * k[:, 0] / km + ux
                vy = cg * k[:, 1] / km + uy
                dxx, dyx, dxy, dyy = jet.grad(x[:, 0], x[:, 1])
                dkx = -(dxx * k[:, 0] + dyx * k[:, 1])
                dky = -(dxy * k[:, 0] + dyy * k[:, 1])
                if _sub == 0:
                    xh = x + 0.5 * dt * np.stack([vx, vy], 1)
                    kh = k + 0.5 * dt * np.stack([dkx, dky], 1)
                    x_, k_ = x, k; x, k = xh, kh
                else:
                    x = x_ + dt * np.stack([vx, vy], 1)
                    k = k_ + dt * np.stack([dkx, dky], 1)
            dx = x - xs[-1]
            ph = ph + ks[-1][:, 0] * dx[:, 0] + ks[-1][:, 1] * dx[:, 1]
            km = np.hypot(k[:, 0], k[:, 1])
            att = att + alpha_eff(km) * dt
            xs.append(x.copy()); ks.append(k.copy()); phs.append(ph.copy()); ats.append(att.copy())
        X = np.stack(xs); Kk = np.stack(ks); Ph = np.stack(phs); At = np.stack(ats)
        # wave action: A^2 |dx/dt| W = const, W from neighbouring rays
        W = np.gradient(X, axis=1); W = np.hypot(W[..., 0], W[..., 1])
        km = np.hypot(Kk[..., 0], Kk[..., 1]) + 1e-9
        cg = 0.5 * np.sqrt(G / km)
        ux, uy = jet.drift(X[..., 0], X[..., 1])
        v = np.hypot(cg * Kk[..., 0] / km + ux, cg * Kk[..., 1] / km + uy)
        flux = np.maximum(v * W, 1e-6)
        # WHERE THE STEADY WAKE STOPS EXISTING, and it is not a taper.
        # v is the speed at which the pattern carries wave energy. The drift
        # decays as 1/s, the stationary condition k = g/(U cos psi)^2 shortens the
        # wave to compensate, and v falls with it. When v reaches c_min the
        # pattern can no longer outrun the slowest wave the surface supports at
        # all: it stops transporting energy away from where it was made, and the
        # film damping -- strongest in exactly the band the wake has shortened
        # into by then -- consumes it in place. This is the same c_min bound that
        # already fixes the +-78 deg wavevector fan and the Froude number, applied
        # to the ray instead of to the launch, and it is what keeps the linear
        # wave-action solution from running away: without it A stays flat while k
        # rises fivefold, so the wake gets four times STEEPER downstream and
        # floods mid-pool with 5 cm slope. The factor is cumulative -- energy lost
        # is not recovered if the ray speeds up again.
        esc = np.minimum.accumulate(np.clip((v - C_MIN) / C_MIN, 0.0, 1.0), axis=0)
        REF = 12                       # tube width is ~0 at the launch point
        A = (w_src[i_src] * a0[None, :] * esc
             * np.sqrt(flux[REF:REF + 1] / flux) * np.exp(-At))
        A[:REF] = 0.0                  # do not deposit inside the source region
        P.append(X); K.append(Kk); PH.append(Ph); AM.append(A)
    return (np.concatenate(P, 1), np.concatenate(K, 1),
            np.concatenate(PH, 1), np.concatenate(AM, 1))


def rms_slope(gx, gy):
    """s = sqrt(<gx^2> + <gy^2>) = sqrt(total mean-square slope).

    The same one definition field.py uses, restated here so this module has no
    second opinion about what "rms slope" means. `build`'s rms_target is in these
    units. It used to be normalised through sqrt(<gx^2 + gy^2>/2) -- the per-axis
    rms, smaller by sqrt(2) -- while field.py's WIND and REVERB were normalised
    through this one, so a wake target of 0.068 and a reverb target of 0.046 were
    not comparable numbers even though they sat two lines apart."""
    return float(np.sqrt(np.mean(np.asarray(gx) ** 2 + np.asarray(gy) ** 2)))


def build(jet, x0, x1, y0, y1, nx, ny, rms_target=0.078, sig_max=0.25, norm_r=0.40):
    """Gabor reconstruction: every ray sample deposits a local plane wave over a
    window the size of its own ray tube. No hand-shaped envelope anywhere.

    Returns `(gx, gy, kmap)`. `kmap` is the LOCAL wavenumber of the reconstructed
    field, |k| averaged over the same Gabor windows that deposited the field, and
    it exists so that field.py can footprint-filter this band the way it filters
    the analytic ones. The other four bands are explicit sums of plane waves and
    know their own k per component; this one arrives as a grid and would
    otherwise have to be filtered at a single nominal k for the whole basin --
    which would be wrong in exactly the place it matters, since the stationary
    condition k = g/(U cos psi)^2 SHORTENS the wake as the drift decays, so its
    wavelength runs from ~35 cm near the fitting to under 10 cm downstream. One
    number for the band would over-filter the source and under-filter the tail.

    THE WINDOW MUST BE WIDER THAN THE WAVE IT CARRIES. A Gabor atom narrower than
    its own wavelength is not a local plane wave at all -- it is a wavelet whose
    own spectrum is centred near 1/sigma, and thousands of them at incoherent
    phases reconstruct a field whose slope energy sits at the WINDOW scale rather
    than the WAVE scale. Deposited through 11 mm windows, a wake whose rays carry
    27 cm reconstructed as 5 cm: a fourfold error in the dominant wavelength,
    invisible in every ray-level diagnostic, and worth a factor of five in F on
    the bed. So the floor on sigma is the WKB validity condition, ~half a
    wavelength, and it is that -- not the grid -- that sets the window.

    `rms_target` is the wake's rms slope in its OWN near field -- inside `norm_r`
    of the forcing centroid -- not an average over the basin. Normalising over the
    whole basin instead is what silently turns a local disturbance into a
    pool-wide one: the further the wake wrongly reaches, the harder that
    normalisation pushes short-wave slope onto water that should be glassy.

    It is measured with `rms_slope`, i.e. sqrt(<gx^2> + <gy^2>). The default of
    0.078 is only a placeholder for a caller that omits it -- field.py always
    passes WAKE_RMS -- and it is the old 0.055 restated in this unit
    (0.055*sqrt(2) = 0.0778), not a new choice. `?` neither figure is measured.
    """
    X, K, PH, A = trace(jet)
    dxg = (x1 - x0) / nx; dyg = (y1 - y0) / ny
    num_x = np.zeros((ny, nx)); num_y = np.zeros((ny, nx)); den = np.zeros((ny, nx))
    num_k = np.zeros((ny, nx))
    W = np.gradient(X, axis=1); W = np.hypot(W[..., 0], W[..., 1])
    km = np.hypot(K[..., 0], K[..., 1]) + 1e-12
    lam = 2 * np.pi / km
    SIG = np.clip(np.maximum.reduce([W, 0.45 * lam,
                                     np.full_like(W, 2.0 * dxg)]), 2.0 * dxg, sig_max)
    OK = ((X[..., 0] > x0 - .4) & (X[..., 0] < x1 + .4) &
          (X[..., 1] > y0 - .4) & (X[..., 1] < y1 + .4) & (A > 1e-3))
    nt, nr = X.shape[0], X.shape[1]
    for i in range(nr):
        lx = ly = 1e9                       # last deposit for this ray
        for t in range(nt):
            if not OK[t, i]:
                continue
            s = SIG[t, i]
            px, py = X[t, i, 0], X[t, i, 1]
            # deposits closer together than half a window are redundant: the
            # windows already overlap, and the sum is normalised by `den`
            if (px - lx) ** 2 + (py - ly) ** 2 < (0.45 * s) ** 2:
                continue
            lx, ly = px, py
            r = max(int(np.ceil(2.2 * s / dxg)), 1)
            ry = max(int(np.ceil(2.2 * s / dyg)), 1)
            cx = int((px - x0) / dxg); cy = int((py - y0) / dyg)
            xs_ = slice(max(cx - r, 0), min(cx + r + 1, nx))
            ys_ = slice(max(cy - ry, 0), min(cy + ry + 1, ny))
            if xs_.start >= xs_.stop or ys_.start >= ys_.stop:
                continue
            gx_ = x0 + (np.arange(xs_.start, xs_.stop) + .5) * dxg
            gy_ = y0 + (np.arange(ys_.start, ys_.stop) + .5) * dyg
            ddx = gx_[None, :] - px; ddy = gy_[:, None] - py
            w = np.exp(-(ddx ** 2 + ddy ** 2) / (2 * s * s))
            c = A[t, i] * np.cos(PH[t, i] + K[t, i, 0] * ddx + K[t, i, 1] * ddy) * w
            num_x[ys_, xs_] += c * K[t, i, 0]; num_y[ys_, xs_] += c * K[t, i, 1]
            den[ys_, xs_] += w
            num_k[ys_, xs_] += w * km[t, i]
    # num/den is a Nadaraya-Watson estimate; where a single window barely reaches,
    # den is tiny and the division amplifies it into a hard-edged block. Regularise
    # with a floor of order one window's own weight, which fades thin coverage out
    # instead of magnifying it.
    gx, gy = num_x / (den + 0.35), num_y / (den + 0.35)
    # kmap is a plain weighted mean, NOT regularised with the 0.35 floor: that
    # floor is there to fade thin coverage out of the FIELD, and applying it to a
    # wavenumber would pull k toward zero exactly where coverage is thin, i.e. it
    # would report "very long waves" about water the wake barely reaches and so
    # would protect that water from a filter it does not need protecting from.
    # Where nothing was deposited the field is zero and k is irrelevant; fill
    # those texels with the field's own mean k so the map has no holes.
    kmap = num_k / np.maximum(den, 1e-9)
    seen = den > 1e-6
    kmap[~seen] = float(kmap[seen].mean()) if seen.any() else 1.0
    gxc = x0 + (np.arange(nx) + .5) * dxg
    gyc = y0 + (np.arange(ny) + .5) * ((y1 - y0) / ny)
    s_pk = 0.91                                   # forcing peak, from the jet geometry
    cx, cy = jet.p + s_pk * jet.ax
    near = ((gxc[None, :] - cx) ** 2 + (gyc[:, None] - cy) ** 2) < norm_r ** 2
    rms = rms_slope(gx[near], gy[near])
    sc = rms_target / max(rms, 1e-9)
    return gx * sc, gy * sc, kmap
