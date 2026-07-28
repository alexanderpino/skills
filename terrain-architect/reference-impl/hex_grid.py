"""Hexagonal working grid (chapter `26`): the sheared-array core.

A hex heightfield is a square 2D array under a shear: ``h[q, r]`` holds one height per cell
centre and ``basis()`` is the single 2x2 matrix that carries index space to world space.
Everything metric routes through that matrix; everything that branches on neighbour structure,
distance or rounding uses the hex-native forms below rather than ported square-grid idioms
(`26`, *What does not port*).

Conventions: axial coordinates ``(q, r)`` map to array indices directly (a rhombic domain);
``NEIGHBOURS`` is the fixed 6-entry direction table, consecutive entries 60 deg apart.
Stencil functions treat the array as periodic (``np.roll``) — callers own the apron/boundary
policy exactly as for the square-grid modules.
"""
import math

import numpy as np

# The 6 axial neighbour offsets, in counter-clockwise world order (pointy-top).
# Antipodal pairs are (k, k+3); consecutive entries are 60 deg apart.
NEIGHBOURS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def basis(cellsize, orientation="pointy"):
    """Index->world shear matrix B: world = B @ (q, r).

    ``cellsize`` is the centre-to-centre spacing (the only length in the lattice). The two
    orientations differ by a 30 deg rotation and share the metric tensor G = B.T @ B, whose
    off-diagonal cos60 = 1/2 is the term square-grid code assumes is zero. det B =
    (sqrt(3)/2) * cellsize**2 is the cell area (positive: winding survives the shear).
    """
    if orientation == "pointy":
        return cellsize * np.array([[1.0, 0.5], [0.0, math.sqrt(3) / 2]])
    if orientation == "flat":
        return cellsize * np.array([[math.sqrt(3) / 2, 0.0], [0.5, 1.0]])
    raise ValueError(f"orientation must be 'pointy' or 'flat', got {orientation!r}")


def cell_at(p, cellsize, orientation="pointy"):
    """Point -> containing cell, by cube rounding (never floor, never per-axis round).

    Cell boundaries are hexagons; rounding fractional axial coordinates independently
    partitions the plane into rhombi instead and picks the wrong cell for ~17% of points.
    Round all three cube coordinates and re-derive the one that moved furthest, so the
    x + y + z = 0 constraint survives.
    """
    u = np.linalg.solve(basis(cellsize, orientation), np.asarray(p, dtype=float))
    x, z = u[0], u[1]
    y = -x - z
    rx, ry, rz = round(x), round(y), round(z)
    dx, dy, dz = abs(rx - x), abs(ry - y), abs(rz - z)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


def sample(h, p, cellsize, orientation="pointy"):
    """Point -> height, barycentric over the containing dual triangle (there is no bilinear).

    The triangle is located by the pinned anti-diagonal split of the index quad (`26`,
    *Storage*), so what is sampled is exactly what the dual mesh renders: weights are
    non-negative, sum to 1, and reproduce an affine field exactly.
    """
    h = np.asarray(h)
    u = np.linalg.solve(basis(cellsize, orientation), np.asarray(p, dtype=float))
    qi, ri = math.floor(u[0]), math.floor(u[1])
    fq, fr = u[0] - qi, u[1] - ri
    if fq + fr <= 1.0:  # lower dual triangle
        return ((1 - fq - fr) * h[qi, ri] + fq * h[qi + 1, ri] + fr * h[qi, ri + 1])
    return ((1 - fr) * h[qi + 1, ri] + (1 - fq) * h[qi, ri + 1]
            + (fq + fr - 1) * h[qi + 1, ri + 1])


def ring(q, r, k):
    """The 6k cells at exact hex distance k: walk k steps out, then k along each of the six
    sides. A box loop has no hex analogue — neighbourhoods are rings and discs."""
    if k == 0:
        return [(q, r)]
    out = []
    cq, cr = q + NEIGHBOURS[0][0] * k, r + NEIGHBOURS[0][1] * k
    for side in range(6):
        dq, dr = NEIGHBOURS[(side + 2) % 6]
        for _ in range(k):
            out.append((cq, cr))
            cq, cr = cq + dq, cr + dr
    return out


def disc(q, r, k):
    """All 1 + 3k(k+1) cells within hex distance k (rings 0..k)."""
    out = [(q, r)]
    for i in range(1, k + 1):
        out.extend(ring(q, r, i))
    return out


def laplacian6(h, cellsize):
    """Renormalised 6-neighbour Laplacian: (2 / (3 d^2)) * sum(h_k - 6 h).

    The constant is 2/(3 d^2), NOT the square grid's 1/d^2 — keep the square constant and
    diffusivity is silently 1.5x high (`26`; the lattice moment is sum(e e^T) = 3I, not 2I).
    Periodic boundaries; exact on quadratics.
    """
    h = np.asarray(h, dtype=float)
    acc = -6.0 * h
    for dq, dr in NEIGHBOURS:
        acc += np.roll(np.roll(h, -dq, axis=0), -dr, axis=1)
    return acc * (2.0 / (3.0 * cellsize * cellsize))


def gradient6(h, cellsize, orientation="pointy"):
    """World-space gradient from the one-ring stencil: g = sum(h_k * e_k) / (3 d).

    e_k are the WORLD unit vectors to the six neighbours — the shear is inside the stencil,
    so no B^-T correction is left for the caller to forget (`26`, the 30.5-deg normal bug).
    Second-order accurate with an isotropic leading error; exact on affine fields.
    Returns (gx, gy) arrays; the surface normal is normalize(-gx, -gy, 1).
    """
    h = np.asarray(h, dtype=float)
    B = basis(cellsize, orientation)
    gx = np.zeros_like(h)
    gy = np.zeros_like(h)
    for dq, dr in NEIGHBOURS:
        e = B @ np.array([dq, dr], dtype=float)
        e /= np.linalg.norm(e)
        hk = np.roll(np.roll(h, -dq, axis=0), -dr, axis=1)
        gx += hk * e[0]
        gy += hk * e[1]
    scale = 1.0 / (3.0 * cellsize)
    return gx * scale, gy * scale
