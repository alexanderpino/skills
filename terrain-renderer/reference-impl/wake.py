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


class Jet:
    def __init__(self, x, y, depth=0.15, tilt_deg=6.0, az_deg=20.0,
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


def trace(jet, n_psi=161, n_step=900, dt=0.02, s_launch=(0.7, 1.0, 1.4, 1.9)):
    """Launch fans of stationary gravity waves from points along the jet axis."""
    P, K, PH, AM = [], [], [], []
    for s0 in s_launch:
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
            att = att + 2 * NU * km ** 2 * dt
            xs.append(x.copy()); ks.append(k.copy()); phs.append(ph.copy()); ats.append(att.copy())
        X = np.stack(xs); Kk = np.stack(ks); Ph = np.stack(phs); At = np.stack(ats)
        # wave action: A^2 |dx/dt| W = const, W from neighbouring rays
        W = np.gradient(X, axis=1); W = np.hypot(W[..., 0], W[..., 1])
        km = np.hypot(Kk[..., 0], Kk[..., 1]) + 1e-9
        cg = 0.5 * np.sqrt(G / km)
        ux, uy = jet.drift(X[..., 0], X[..., 1])
        v = np.hypot(cg * Kk[..., 0] / km + ux, cg * Kk[..., 1] / km + uy)
        flux = np.maximum(v * W, 1e-6)
        REF = 12                       # tube width is ~0 at the launch point
        A = np.sqrt(flux[REF:REF + 1] / flux) * np.exp(-At)
        A[:REF] = 0.0                  # do not deposit inside the source region
        P.append(X); K.append(Kk); PH.append(Ph); AM.append(A)
    return (np.concatenate(P, 1), np.concatenate(K, 1),
            np.concatenate(PH, 1), np.concatenate(AM, 1))


def build(jet, x0, x1, y0, y1, nx, ny, rms_target=0.055, stride=3):
    """Gabor reconstruction: every ray sample deposits a local plane wave over a
    window the size of its own ray tube. No hand-shaped envelope anywhere."""
    X, K, PH, A = trace(jet)
    dxg = (x1 - x0) / nx
    num_x = np.zeros((ny, nx)); num_y = np.zeros((ny, nx)); den = np.zeros((ny, nx))
    W = np.gradient(X, axis=1); W = np.hypot(W[..., 0], W[..., 1])
    for t in range(0, X.shape[0], stride):
        px, py = X[t, :, 0], X[t, :, 1]
        kx, ky, ph, am = K[t, :, 0], K[t, :, 1], PH[t], A[t]
        sig = np.clip(np.maximum(W[t], 2.0 * dxg) * 1.1, 2.0 * dxg, 0.15)
        ok = (px > x0 - .3) & (px < x1 + .3) & (py > y0 - .3) & (py < y1 + .3) & (am > 1e-3)
        for i in np.nonzero(ok)[0]:
            r = max(int(np.ceil(2.2 * sig[i] / dxg)), 1)
            cx = int((px[i] - x0) / dxg); cy = int((py[i] - y0) / ((y1 - y0) / ny))
            xs_ = slice(max(cx - r, 0), min(cx + r + 1, nx))
            ys_ = slice(max(cy - r, 0), min(cy + r + 1, ny))
            if xs_.start >= xs_.stop or ys_.start >= ys_.stop:
                continue
            gx_ = x0 + (np.arange(xs_.start, xs_.stop) + .5) * dxg
            gy_ = y0 + (np.arange(ys_.start, ys_.stop) + .5) * ((y1 - y0) / ny)
            ddx = gx_[None, :] - px[i]; ddy = gy_[:, None] - py[i]
            w = np.exp(-(ddx ** 2 + ddy ** 2) / (2 * sig[i] ** 2))
            loc = ph[i] + kx[i] * ddx + ky[i] * ddy
            c = am[i] * np.cos(loc) * w
            num_x[ys_, xs_] += c * kx[i]; num_y[ys_, xs_] += c * ky[i]
            den[ys_, xs_] += w
    den = np.maximum(den, 1e-9)
    gx, gy = num_x / den, num_y / den
    rms = np.sqrt((gx ** 2 + gy ** 2).mean() / 2)
    sc = rms_target / max(rms, 1e-9)
    return gx * sc, gy * sc
