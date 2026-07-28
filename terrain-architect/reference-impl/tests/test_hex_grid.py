"""Oracle tests for the hexagonal working grid (chapter `26`).

Chapter 26 quotes measured numbers — the 16.8% wrong-cell rate of naive rounding, the 30.5-deg
naive-normal error, the sqrt(3) anisotropy of two-axis 'separable' blurs, the H/3 corner-mean
plateau, the 1.5x un-renormalised Laplacian. This file is where those numbers are measured, so
the chapter's claims and the reference implementation cannot drift apart silently.
"""
import math

import numpy as np
import pytest

import hex_grid
from hex_grid import (NEIGHBOURS, basis, cell_at, disc, gradient6, hessian6, laplacian6,
                      ring, sample)

CS = 1.7  # deliberately non-unit: catches any formula that silently assumes cellsize == 1


# --------------------------------------------------------------------------- #
# The shear matrix B and the metric it induces

def test_basis_metric_and_area():
    Bp, Bf = basis(CS, "pointy"), basis(CS, "flat")
    G = CS * CS * np.array([[1.0, 0.5], [0.5, 1.0]])
    assert np.allclose(Bp.T @ Bp, G) and np.allclose(Bf.T @ Bf, G)  # same metric, cos60 off-diag
    assert np.allclose(np.linalg.det(Bp), math.sqrt(3) / 2 * CS * CS)  # cell area, positive
    Q = Bf @ np.linalg.inv(Bp)  # orientations differ by a 30-deg rotation, nothing more
    assert np.allclose(Q.T @ Q, np.eye(2)) and np.isclose(math.degrees(math.atan2(Q[1, 0], Q[0, 0])), 30.0)


def test_neighbours_are_equidistant_and_antipodal():
    B = basis(CS)
    d = [np.linalg.norm(B @ np.array(n, dtype=float)) for n in NEIGHBOURS]
    assert np.allclose(d, CS)  # all six at one cellsize — the property D8 never has
    for k in range(3):
        assert NEIGHBOURS[k][0] == -NEIGHBOURS[k + 3][0] and NEIGHBOURS[k][1] == -NEIGHBOURS[k + 3][1]


def test_naive_index_gradient_error_bounds():
    """The 30.5-deg / sqrt(3) numbers behind the B^-T rule: treat an index-space gradient as
    world and the direction is off by up to ~30.5 deg, the magnitude by sqrt(3) end to end."""
    M = np.linalg.inv(basis(CS)).T * CS  # cellsize factored out: pure shape error
    ang, mag = [], []
    for t in np.linspace(0, 2 * math.pi, 4001):
        v = np.array([math.cos(t), math.sin(t)])
        w = M @ v
        ang.append(math.degrees(math.acos(min(1.0, v @ w / np.linalg.norm(w)))))
        mag.append(np.linalg.norm(w))
    assert 30.0 < max(ang) < 31.0  # chapter quotes 30.5 deg
    assert np.isclose(max(mag) / min(mag), math.sqrt(3), atol=1e-3)


# --------------------------------------------------------------------------- #
# Point -> cell: cube rounding against brute force

def test_cube_round_is_exact_and_naive_rounding_is_not():
    B = basis(CS)
    cells = [(q, r) for q in range(-8, 9) for r in range(-8, 9)]
    centres = {c: B @ np.array(c, dtype=float) for c in cells}
    rng = np.random.default_rng(7)
    pts = rng.uniform(-4 * CS, 4 * CS, size=(4000, 2))
    wrong_naive = 0
    for p in pts:
        true = min(cells, key=lambda c: np.linalg.norm(centres[c] - p))
        assert cell_at(p, CS) == true  # cube_round: exact, every point
        u = np.linalg.solve(B, p)
        wrong_naive += (int(round(u[0])), int(round(u[1]))) != true
    # chapter quotes 16.8%: per-axis rounding draws rhombi, cells are hexagons
    assert 0.14 < wrong_naive / len(pts) < 0.20


# --------------------------------------------------------------------------- #
# Point -> value: barycentric on the dual triangle

def test_sample_is_affine_exact_and_continuous():
    a, b, c = 0.37, -1.9, 4.2
    B = basis(CS)
    n = 12
    h = np.empty((n, n))
    for q in range(n):
        for r in range(n):
            x, y = B @ np.array([q, r], dtype=float)
            h[q, r] = a * x + b * y + c
    rng = np.random.default_rng(3)
    for _ in range(500):
        u = rng.uniform(1, n - 2, size=2)
        p = B @ u
        assert np.isclose(sample(h, p, CS), a * p[0] + b * p[1] + c, atol=1e-9)
    # continuity across the anti-diagonal seam (fq + fr == 1), where the two branches meet
    for t in np.linspace(0.05, 0.95, 19):
        p_seam = B @ np.array([3 + t, 4 + (1 - t)])
        lo = sample(h, p_seam - 1e-9 * (B @ np.ones(2)), CS)
        hi = sample(h, p_seam + 1e-9 * (B @ np.ones(2)), CS)
        assert np.isclose(lo, hi, atol=1e-6)


# --------------------------------------------------------------------------- #
# Neighbourhoods: rings and discs, not boxes

def test_ring_and_disc_counts_and_distance():
    def hexdist(a, b):
        ax, az = a
        bx, bz = b
        ay, by = -ax - az, -bx - bz
        return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2

    for k in range(1, 6):
        rk = ring(2, -1, k)
        assert len(rk) == 6 * k and len(set(rk)) == 6 * k
        assert all(hexdist((2, -1), c) == k for c in rk)
        assert len(disc(2, -1, k)) == 1 + 3 * k * (k + 1)


# --------------------------------------------------------------------------- #
# Stencils: the renormalised Laplacian and the world-space gradient

def _world_field(fn, n, cellsize):
    B = basis(cellsize)
    h = np.empty((n, n))
    for q in range(n):
        for r in range(n):
            h[q, r] = fn(*(B @ np.array([q, r], dtype=float)))
    return h


def test_laplacian6_exact_on_quadratic_and_square_constant_is_1p5x():
    n = 24
    h = _world_field(lambda x, y: x * x + y * y, n, CS)  # true Laplacian = 4 everywhere
    lap = laplacian6(h, CS)[8:16, 8:16]  # interior: away from the periodic wrap
    assert np.allclose(lap, 4.0, atol=1e-9)
    # keep the square grid's 1/d^2 constant instead and the answer is exactly 1.5x high
    unrenormalised = lap * (3.0 / 2.0)
    assert np.allclose(unrenormalised, 6.0, atol=1e-9)


def test_hessian6_exact_on_quadratic_and_consistent_with_laplacian():
    """Three antipodal second differences determine the full world-space Hessian in closed
    form — the hex replacement for Zevenbergen-Thorne's 3x3 quadratic fit (`06`)."""
    Hxx, Hxy, Hyy = 0.7, -0.4, 1.3
    n = 24
    h = _world_field(lambda x, y: 0.5 * (Hxx * x * x + Hyy * y * y) + Hxy * x * y
                     + 0.3 * x - 0.8 * y + 2.0, n, CS)
    hxx, hxy, hyy = hessian6(h, CS)
    sl = np.s_[8:16, 8:16]
    assert np.allclose(hxx[sl], Hxx, atol=1e-9)
    assert np.allclose(hxy[sl], Hxy, atol=1e-9)
    assert np.allclose(hyy[sl], Hyy, atol=1e-9)
    # trace(H) must agree with the renormalised 6-neighbour Laplacian — same moments
    assert np.allclose((hxx + hyy)[sl], laplacian6(h, CS)[sl], atol=1e-9)


def test_gradient6_is_affine_exact_in_world_space():
    a, b = 0.37, -1.9
    n = 24
    h = _world_field(lambda x, y: a * x + b * y + 4.2, n, CS)
    gx, gy = gradient6(h, CS)
    assert np.allclose(gx[8:16, 8:16], a, atol=1e-9)
    assert np.allclose(gy[8:16, 8:16], b, atol=1e-9)


# --------------------------------------------------------------------------- #
# The corner-only (4-triangle) tile mesh: the H/3 plateau

def test_corner_mean_kernel_and_impulse_plateau():
    """Corner heights are means of 3 cells, so a corner-only tile renders the field through
    (1/3) h_A + (1/9) sum(ring): affine-blind, but a one-cell spike H flattens to H/3."""
    n = 12
    q = r = n // 2
    h = np.zeros((n, n))
    h[q, r] = 1.0  # impulse of height H = 1
    corner_means = []
    for k in range(6):
        aq, ar = NEIGHBOURS[k]
        bq, br = NEIGHBOURS[(k + 1) % 6]
        corner_means.append((h[q, r] + h[q + aq, r + ar] + h[q + bq, r + br]) / 3.0)
    assert np.allclose(corner_means, 1.0 / 3.0)  # every corner of the spike cell: exactly H/3
    # and the kernel identity on a random field: mean-of-6-corners = h/3 + ring/9
    rng = np.random.default_rng(0)
    g = rng.normal(size=(n, n))
    mean6 = np.mean([(g[q, r] + g[q + NEIGHBOURS[k][0], r + NEIGHBOURS[k][1]]
                      + g[q + NEIGHBOURS[(k + 1) % 6][0], r + NEIGHBOURS[(k + 1) % 6][1]]) / 3.0
                     for k in range(6)])
    ringsum = sum(g[q + dq, r + dr] for dq, dr in NEIGHBOURS)
    assert np.isclose(mean6, g[q, r] / 3.0 + ringsum / 9.0, atol=1e-12)


# --------------------------------------------------------------------------- #
# The 14 corner-only triangulations of a tile: three families, and one min angle

def _triangulations(poly):
    """Every triangulation of a convex polygon given as a tuple of vertex indices."""
    if len(poly) < 3:
        return [[]]
    if len(poly) == 3:
        return [[tuple(poly)]]
    out, a, b = [], poly[0], poly[-1]
    for i in range(1, len(poly) - 1):
        for L in _triangulations(poly[:i + 1]):
            for R in _triangulations(poly[i:]):
                out.append(L + R + [(a, poly[i], b)])
    return out


def test_hexagon_triangulation_taxonomy():
    """`26` claims 14 triangulations splitting 6 fan / 6 zigzag / 2 ear-and-core, and min angle
    exactly 30 degrees for ALL of them against the centre fan's 60. Enumerated, not argued —
    the ear argument only proves 30 is a *bound*; this proves every one attains it, which is
    what makes 'the centre fan beats all fourteen' a statement rather than a hope."""
    import itertools
    from collections import Counter

    n = 6
    pts = [(math.cos(math.radians(30 + 60 * k)), math.sin(math.radians(30 + 60 * k)))
           for k in range(n)]
    boundary = {tuple(sorted((i, (i + 1) % n))) for i in range(n)}

    def diagonals(tri):
        e = {tuple(sorted(p)) for t in tri for p in itertools.combinations(t, 2)}
        return sorted(e - boundary)

    def family(diags):
        deg = Counter(v for d in diags for v in d)
        if max(deg.values()) == 3:
            return "fan"                       # all three diagonals from one corner
        if set(deg.values()) == {2}:
            return "ear-and-core"              # the diagonals form a triangle
        return "zigzag"

    def min_angle(tri, P):
        m = 180.0
        for t in tri:
            for i in range(3):
                v, a, b = P[t[i]], P[t[(i + 1) % 3]], P[t[(i + 2) % 3]]
                u1 = (a[0] - v[0], a[1] - v[1])
                u2 = (b[0] - v[0], b[1] - v[1])
                c = ((u1[0] * u2[0] + u1[1] * u2[1])
                     / (math.hypot(*u1) * math.hypot(*u2)))
                m = min(m, math.degrees(math.acos(max(-1.0, min(1.0, c)))))
        return m

    tris = _triangulations(tuple(range(n)))
    assert len(tris) == 14                                      # Catalan C4
    fams = Counter(family(diagonals(t)) for t in tris)
    assert fams == {"fan": 6, "zigzag": 6, "ear-and-core": 2}, fams
    assert sum(fams.values()) == 14                             # the space is fully accounted for
    for t in tris:
        assert math.isclose(min_angle(t, pts), 30.0, abs_tol=1e-9)

    # the centre fan is NOT one of the 14 — it adds a 7th vertex — and it is equilateral
    centre_fan = [(6, k, (k + 1) % 6) for k in range(6)]
    assert math.isclose(min_angle(centre_fan, pts + [(0.0, 0.0)]), 60.0, abs_tol=1e-9)


# --------------------------------------------------------------------------- #
# Separable filters do not port: two axes print sqrt(3), three axes are isotropic

def _blur_axis(a, d, k):
    out = np.zeros_like(a)
    for i, w in enumerate(k):
        s = i - len(k) // 2
        out += w * np.roll(np.roll(a, s * d[0], axis=0), s * d[1], axis=1)
    return out


def _world_aspect(a, cellsize):
    B = basis(cellsize)
    c = a.shape[0] // 2
    ys, xs = np.nonzero(a > 1e-9)
    w = a[ys, xs]
    P = np.array([B @ np.array([y - c, x - c], dtype=float) for y, x in zip(ys, xs)])
    M = (P * w[:, None]).T @ P / w.sum()
    ev = np.linalg.eigvalsh(M)
    return math.sqrt(ev[1] / ev[0])


def test_two_axis_blur_prints_sqrt3_and_three_axis_is_isotropic():
    n = 81
    imp = np.zeros((n, n))
    imp[n // 2, n // 2] = 1.0
    k = np.array([1.0, 2.0, 1.0])
    k /= k.sum()
    two = _blur_axis(_blur_axis(imp, (1, 0), k), (0, 1), k)
    three = _blur_axis(two, (1, -1), k)
    assert np.isclose(_world_aspect(two, CS), math.sqrt(3), atol=1e-6)  # the square-grid reflex
    assert np.isclose(_world_aspect(three, CS), 1.0, atol=1e-6)  # one pass per axis family
