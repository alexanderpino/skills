#!/usr/bin/env python3
"""What the droplet-count rule of gaia/references/resolution-independence.md COSTS.

The page already states the ERROR half of the pair: holding the eroded volume across a
halving of the cell size needs four times the droplets, and the volume "came back within
+/-30% at four times the droplets".  This script measures the other half: what those four
times the droplets cost in wall clock, and whether the cost really moves as 1/dx^5.

Rig: single-threaded CPython droplet loop, brush applied cell by cell in Python so that
wall clock tracks BRUSH-CELL TOUCHES rather than NumPy call overhead.  NumPy is used only
to synthesise the initial surface.  This is NOT a GPU pass, not a compute shader, not a
vectorised production kernel; a shipped implementation is orders of magnitude faster in
absolute terms.  The transferable number here is the RATIO between the two columns, which
is a count of work and survives the rig; the absolute milliseconds are this container's
and drift with load.

Both columns run the SAME physical scene: one 2 km domain, one seeded fBm surface
generated at 256^2 and box-averaged to 128^2, every droplet parameter carried in world
units and converted per the document's own table.

  count     N at 128^2, 4N at 256^2        (1/dx^2)
  lifetime  reach_m/dx                     (1/dx)
  radius    radius_m/dx                    (1/dx), brush cells ~ 1/dx^2
  evaporate e(dx) = 1 - (1-e0)^(dx/L0)
  erode/deposit speed  ~ dx
  minSlope  compared against a per-step drop as minSlope*dx

Usage:  python3 resolution-independence.py [--droplets N] [--repeats R]
"""

import argparse
import math
import statistics
import time

import numpy as np

SEED = 20260914

# Shipped droplet defaults [lague_erosion], authored at the COARSE grid.
INERTIA = 0.05
CAPACITY_FACTOR = 4.0
MIN_SLOPE = 0.01
ERODE_SPEED_0 = 0.3
DEPOSIT_SPEED_0 = 0.3
EVAPORATE_0 = 0.01
GRAVITY = 4.0
RADIUS_CELLS_0 = 3
LIFETIME_0 = 30

DOMAIN_M = 2000.0
RELIEF_M = 120.0
COARSE = 128
FINE = 256


def fbm(n, hurst, seed, relief_m):
    """Seeded spectral fBm, P(k) ~ k^-(2H+2), scaled to relief_m of relief."""
    rng = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[:, None] * n
    ky = np.fft.fftfreq(n)[None, :] * n
    k = np.hypot(kx, ky)
    k[0, 0] = 1.0
    amp = k ** (-(hurst + 1.0))
    amp[0, 0] = 0.0
    phase = rng.uniform(0.0, 2.0 * np.pi, (n, n))
    h = np.real(np.fft.ifft2(amp * np.exp(1j * phase)))
    h -= h.min()
    h /= h.max()
    return h * relief_m


def box_down(h, factor):
    n = h.shape[0] // factor
    return h.reshape(n, factor, n, factor).mean(axis=(1, 3))


def brush(radius_cells):
    """Lague InitializeBrushIndices: weight 1 - sqrt(sqrDst)/radius, normalised."""
    r = int(radius_cells)
    cells = []
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            d2 = x * x + y * y
            if d2 < r * r:
                cells.append((x, y, 1.0 - math.sqrt(d2) / r))
    total = sum(c[2] for c in cells)
    return [(x, y, w / total) for x, y, w in cells]


def droplet_pass(h, n, count, lifetime, bcells, evaporate, erode_speed,
                 deposit_speed, min_drop, seed):
    """One erosion pass. h is a flat Python list, mutated in place."""
    rng = np.random.default_rng(seed)
    starts = rng.uniform(0.0, n - 1.0001, (count, 2))
    steps = erode_steps = touched = 0
    for d in range(count):
        px, py = float(starts[d, 0]), float(starts[d, 1])
        dx = dy = 0.0
        speed, water, sediment = 1.0, 1.0, 0.0
        for _ in range(lifetime):
            nx, ny = int(px), int(py)
            if nx < 0 or ny < 0 or nx >= n - 1 or ny >= n - 1:
                break
            u, v = px - nx, py - ny
            i = ny * n + nx
            h00 = h[i]
            h10 = h[i + 1]
            h01 = h[i + n]
            h11 = h[i + n + 1]
            gx = (h10 - h00) * (1.0 - v) + (h11 - h01) * v
            gy = (h01 - h00) * (1.0 - u) + (h11 - h10) * u
            height = (h00 * (1.0 - u) * (1.0 - v) + h10 * u * (1.0 - v)
                      + h01 * (1.0 - u) * v + h11 * u * v)
            dx = dx * INERTIA - gx * (1.0 - INERTIA)
            dy = dy * INERTIA - gy * (1.0 - INERTIA)
            mag = math.hypot(dx, dy)
            if mag == 0.0:
                break
            dx /= mag
            dy /= mag
            px_new, py_new = px + dx, py + dy
            mx, my = int(px_new), int(py_new)
            if mx < 0 or my < 0 or mx >= n - 1 or my >= n - 1:
                break
            uu, vv = px_new - mx, py_new - my
            j = my * n + mx
            g00 = h[j]
            g10 = h[j + 1]
            g01 = h[j + n]
            g11 = h[j + n + 1]
            new_height = (g00 * (1.0 - uu) * (1.0 - vv) + g10 * uu * (1.0 - vv)
                          + g01 * (1.0 - uu) * vv + g11 * uu * vv)
            dh = new_height - height
            steps += 1
            capacity = max(-dh, min_drop) * speed * water * CAPACITY_FACTOR
            if sediment > capacity or dh > 0.0:
                amount = min(dh, sediment) if dh > 0.0 else (sediment - capacity) * deposit_speed
                sediment -= amount
                h[i] += amount * (1.0 - u) * (1.0 - v)
                h[i + 1] += amount * u * (1.0 - v)
                h[i + n] += amount * (1.0 - u) * v
                h[i + n + 1] += amount * u * v
            else:
                amount = min((capacity - sediment) * erode_speed, -dh)
                sediment += amount
                erode_steps += 1
                for ox, oy, w in bcells:
                    bx = nx + ox
                    by = ny + oy
                    if 0 <= bx < n and 0 <= by < n:
                        h[by * n + bx] -= amount * w
                        touched += 1
            speed = math.sqrt(max(0.0, speed * speed + (-dh) * GRAVITY))
            water *= (1.0 - evaporate)
            px, py = px_new, py_new
    return steps, erode_steps, touched


def config(n, base_count):
    dx = DOMAIN_M / n
    dx0 = DOMAIN_M / COARSE
    ratio = dx0 / dx                      # 1 at 128^2, 2 at 256^2
    radius_cells = int(round(RADIUS_CELLS_0 * ratio))
    return {
        "n": n,
        "dx": dx,
        "count": int(round(base_count * ratio * ratio)),
        "lifetime": int(round(LIFETIME_0 * ratio)),
        "radius_cells": radius_cells,
        "bcells": brush(radius_cells),
        "evaporate": 1.0 - (1.0 - EVAPORATE_0) ** (dx / dx0),
        "erode_speed": ERODE_SPEED_0 * dx / dx0,
        "deposit_speed": DEPOSIT_SPEED_0 * dx / dx0,
        "min_drop": MIN_SLOPE * dx,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--droplets", type=int, default=2000,
                    help="droplet count at 128^2; the 256^2 column gets 4x")
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    fine = fbm(FINE, 0.6, SEED, RELIEF_M)
    coarse = box_down(fine, 2)
    surfaces = {COARSE: coarse, FINE: fine}

    print(f"seed {SEED}   domain {DOMAIN_M:.0f} m   relief {RELIEF_M:.0f} m   "
          f"base droplets {args.droplets}   repeats {args.repeats}")
    print(f"{'grid':>6} {'dx m':>8} {'count':>7} {'life':>5} {'r_cells':>8} "
          f"{'brush':>6} {'steps':>9} {'touches':>11} {'ms':>10} {'eroded m3':>12}")

    results = {}
    for n in (COARSE, FINE):
        c = config(n, args.droplets)
        for rep in range(args.repeats):
            h = [float(x) for x in surfaces[n].ravel()]
            before = sum(h)
            t0 = time.perf_counter()
            steps, erode_steps, touched = droplet_pass(
                h, n, c["count"], c["lifetime"], c["bcells"], c["evaporate"],
                c["erode_speed"], c["deposit_speed"], c["min_drop"], SEED + 1)
            ms = (time.perf_counter() - t0) * 1000.0
            cell_area = c["dx"] * c["dx"]
            eroded = (before - sum(h)) * cell_area
            results.setdefault(n, []).append(ms)
            print(f"{n:>4}^2 {c['dx']:>8.4f} {c['count']:>7} {c['lifetime']:>5} "
                  f"{c['radius_cells']:>8} {len(c['bcells']):>6} {steps:>9} "
                  f"{touched:>11} {ms:>10.1f} {eroded:>12.1f}")
        results[n] = (results[n], steps, touched)

    (ms_c, steps_c, touch_c) = results[COARSE]
    (ms_f, steps_f, touch_f) = results[FINE]
    med_c = statistics.median(ms_c)
    med_f = statistics.median(ms_f)
    print()
    print(f"128^2 {min(ms_c):.1f}-{max(ms_c):.1f} ms over {len(ms_c)} runs, median {med_c:.1f}")
    print(f"256^2 {min(ms_f):.1f}-{max(ms_f):.1f} ms over {len(ms_f)} runs, median {med_f:.1f}")
    print(f"wall-clock ratio   {med_f / med_c:.2f}x   (predicted 1/dx^5 = 32x); "
          f"worst/best case {min(ms_f)/max(ms_c):.2f}x-{max(ms_f)/min(ms_c):.2f}x")
    print(f"fitted exponent    {math.log(med_f / med_c, 2):.2f}   "
          f"(steps alone would give 3, brush-dominated 5)")
    print(f"brush-touch ratio  {touch_f / touch_c:.2f}x")
    print(f"step ratio         {steps_f / steps_c:.2f}x   (predicted 1/dx^3 = 8x)")
    print(f"per-droplet cost   {med_c / (args.droplets):.3f} ms at 128^2, "
          f"{med_f / (args.droplets * 4):.3f} ms at 256^2")


if __name__ == "__main__":
    main()
