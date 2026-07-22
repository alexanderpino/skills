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
