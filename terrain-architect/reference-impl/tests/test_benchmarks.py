"""Independent benchmarks (validity rung 3): check EMERGENT output against a result derived
outside our code — an analytic continuum solution or an independent recomputation — not against
an oracle re-derived from the same equation.

This file adds two; several more already live in the per-module tests and are catalogued in
VALIDATION.md (diffusion single-mode decay, flexure kernel, stream-power slope-area exponent,
Voellmy runout L=H/tanα, Pyle tephra thinning, Parsons-Sclater age-depth).
"""
import numpy as np
import diffusion
import noise
import sims_illustrative as sims


def test_diffusion_matches_the_gaussian_greens_function():
    """The heat equation dh/dt = D grad^2 h has the exact free-space Green's function: an
    initial Gaussian of variance s0^2 spreads to variance s0^2 + 2 D t PER DIMENSION. Our
    discrete Culling scheme must reproduce that continuum solution — a benchmark independent of
    the discretisation (the analytic answer comes from the PDE, not our stencil)."""
    n, D, dt, iters, s0 = 128, 0.5, 0.1, 50, 3.0
    T = dt * iters
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    c = n / 2.0
    init = np.exp(-((xx - c) ** 2 + (yy - c) ** 2) / (2 * s0 ** 2))
    out = diffusion.hillslope_diffuse(init, D, dt, iters, cellsize=1.0)

    tot = out.sum()
    xm = (out * xx).sum() / tot
    ym = (out * yy).sum() / tot
    var_x = (out * (xx - xm) ** 2).sum() / tot
    var_y = (out * (yy - ym) ** 2).sum() / tot
    analytic = s0 ** 2 + 2 * D * T
    assert abs(var_x - analytic) < 0.05 * analytic
    assert abs(var_y - analytic) < 0.05 * analytic


def test_worley_f1_equals_independent_nearest_point():
    """Worley F1 must be the distance to the nearest feature point. Recompute it by brute force
    over a WIDER (7x7) neighbourhood; the module's 3x3 search must return the same value — an
    independent check that the 3x3 window is sufficient (no closer point lies outside it)."""
    n = 40
    x = np.arange(n) * 0.3
    xx, yy = np.meshgrid(x, x)
    ours = noise.worley(xx, yy, seed=5, kind="f1")

    cx = np.floor(xx).astype(np.int64)
    cy = np.floor(yy).astype(np.int64)
    brute = np.full(xx.shape, np.inf)
    for dj in range(-3, 4):
        for di in range(-3, 4):
            gx, gy = cx + di, cy + dj
            fx = gx + noise._hash01(gx, gy, 5, salt=1)
            fy = gy + noise._hash01(gx, gy, 5, salt=2)
            brute = np.minimum(brute, np.hypot(xx - fx, yy - fy))
    assert np.allclose(ours, brute)


def test_glacier_sia_matches_halfar_similarity_solution():
    """The SIA solver's decisive benchmark: the **Halfar (1983) similarity solution** for an
    isothermal ice dome spreading on a flat bed with NO mass balance (Bueler et al. 2005 'Test B').
    For Glen n=3 the exact profile is self-similar with shape H(r,t) = H_c(t)·[1 - (r/R(t))^(4/3)]^(3/7)
    — the exponents (n+1)/n = 4/3 and n/(2n+1) = 3/7 come from the analytic solution, NOT our code, so
    reproducing the shape is an independent check of the H^(n+2)·|∇s|^(n-1) diffusivity. Started from the
    Halfar profile the numerical dome must (a) conserve ice exactly, (b) thin at the centre while the
    margin advances (the self-similar spreading direction), and (c) keep the analytic interior shape.
    This closes the SIA benchmark gap VALIDATION.md rung 3 recorded as deferred."""
    n, cell = 121, 12000.0                                          # 12 km cells, ~1450 km domain
    c = (n - 1) // 2
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    r = np.hypot(xx - c, yy - c) * cell
    H0, R0 = 3000.0, 500e3
    shape = lambda rr, Hc, R: Hc * np.maximum(1.0 - np.clip(rr / R, 0, 1) ** (4.0 / 3.0), 0.0) ** (3.0 / 7.0)
    H = shape(r, H0, R0)
    A = 1e-16 / (365.25 * 24 * 3600)                               # 1e-16 Pa^-3 a^-1 -> SI (Pa^-3 s^-1)
    H1 = sims.glacier_sia(np.zeros((n, n)), H, steps=8, A=A, dt=200.0 * 3.15e7,
                          cellsize=cell, beta=0.0, max_substeps=4000)

    assert abs(H1.sum() - H.sum()) < 1e-9 * H.sum()                # (a) ice volume conserved (no mass balance)
    Hc = H1[c, c]
    rad, prof = r[c, c:], H1[c, c:]                                 # radial slice out from the dome centre
    Rnum = rad[prof > 1.0].max()
    assert Hc < H0 and Rnum > R0                                   # (b) centre thins, margin advances
    interior = (rad > 0) & (rad < 0.7 * Rnum)                      # (c) interior matches the Halfar shape
    err = np.abs(prof[interior] / Hc - shape(rad[interior], 1.0, Rnum))
    assert err.max() < 0.03                                        # numerical dome reproduces [1-s^(4/3)]^(3/7)
