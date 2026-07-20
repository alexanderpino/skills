"""Droplet / particle hydraulic erosion (04-erosion-hydraulic.md).

Beyer 2015, after Musgrave, Kolb & Mace 1989. Simulate N independent droplets; each
follows the gradient (with inertia), erodes when it has spare capacity and deposits when
overloaded or climbing. Erosion uses a disc BRUSH (avoids 1-px scratches); deposition is
BILINEAR to the 4 cells under the droplet. Any sediment still carried at the end of a
droplet's life is deposited, so total volume is conserved to floating point.

Deterministic: pass a seed; the RNG is the only source of randomness.
"""
import numpy as np


def _height_and_gradient(m, x, y):
    """Bilinear height and its gradient at (x=col, y=row)."""
    n, w = m.shape
    j = min(max(int(np.floor(x)), 0), w - 2)
    i = min(max(int(np.floor(y)), 0), n - 2)
    fx, fy = x - j, y - i
    h00, h10 = m[i, j], m[i, j + 1]
    h01, h11 = m[i + 1, j], m[i + 1, j + 1]
    gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
    gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
    h = (h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy)
         + h01 * (1 - fx) * fy + h11 * fx * fy)
    return h, gx, gy


def _deposit(m, x, y, amount):
    n, w = m.shape
    j = min(max(int(np.floor(x)), 0), w - 2)
    i = min(max(int(np.floor(y)), 0), n - 2)
    fx, fy = x - j, y - i
    m[i, j] += amount * (1 - fx) * (1 - fy)
    m[i, j + 1] += amount * fx * (1 - fy)
    m[i + 1, j] += amount * (1 - fx) * fy
    m[i + 1, j + 1] += amount * fx * fy


def _erode_brush(m, x, y, amount, radius):
    """Remove `amount` spread over a disc of the given radius, weight-normalised so the
    exact `amount` leaves the grid (in-bounds weights only -> boundary-safe & conserving)."""
    n, w = m.shape
    ci, cj = int(round(y)), int(round(x))
    cells, tot = [], 0.0
    for di in range(-radius, radius + 1):
        for dj in range(-radius, radius + 1):
            ni, nj = ci + di, cj + dj
            if 0 <= ni < n and 0 <= nj < w:
                d = np.hypot(di, dj)
                if d <= radius:
                    wt = max(0.0, 1.0 - d / (radius + 1e-9))
                    cells.append((ni, nj, wt))
                    tot += wt
    if tot > 0.0:
        for ni, nj, wt in cells:
            m[ni, nj] -= amount * wt / tot


def droplet_erode(heightmap, n_droplets=20000, seed=0, *, inertia=0.05,
                  capacity_factor=4.0, min_slope=0.01, erode_speed=0.3,
                  deposit_speed=0.3, evaporate=0.02, gravity=4.0,
                  max_lifetime=30, brush_radius=2):
    """Return the eroded heightfield. Total volume is conserved (leftover sediment is
    deposited at end of life)."""
    m = np.asarray(heightmap, dtype=np.float64).copy()
    n, w = m.shape
    rng = np.random.default_rng(seed)
    for _ in range(int(n_droplets)):
        x = rng.uniform(1.0, w - 2.0)
        y = rng.uniform(1.0, n - 2.0)
        dx = dy = 0.0
        speed, water, sediment = 1.0, 1.0, 0.0
        for _step in range(max_lifetime):
            h, gx, gy = _height_and_gradient(m, x, y)
            dx = dx * inertia - gx * (1 - inertia)
            dy = dy * inertia - gy * (1 - inertia)
            length = np.hypot(dx, dy)
            if length < 1e-8:
                break
            dx, dy = dx / length, dy / length
            nx, ny = x + dx, y + dy
            if not (1.0 <= nx <= w - 2.0 and 1.0 <= ny <= n - 2.0):
                break
            nh, _, _ = _height_and_gradient(m, nx, ny)
            dh = nh - h                                   # <0 downhill
            capacity = max(-dh, min_slope) * speed * water * capacity_factor
            if sediment > capacity or dh > 0:
                amount = min(dh, sediment) if dh > 0 else (sediment - capacity) * deposit_speed
                sediment -= amount
                _deposit(m, x, y, amount)
            else:
                amount = min((capacity - sediment) * erode_speed, -dh)
                _erode_brush(m, x, y, amount, brush_radius)
                sediment += amount
            speed = np.sqrt(max(0.0, speed * speed + (-dh) * gravity))
            water *= (1.0 - evaporate)
            x, y = nx, ny
        if sediment > 0.0:                                # conserve: drop the rest
            _deposit(m, x, y, sediment)
    return m
