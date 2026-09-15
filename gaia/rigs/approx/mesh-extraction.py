#!/usr/bin/env python3
"""Machine-cost figures for gaia/references/mesh-extraction.md.

WHAT THIS RIG IS: CPython 3.11 + numpy on a shared Linux container. Every number it
prints is a BYTE COUNT of a data structure the document already describes -- the QEM
per-vertex quadric (`ten floats`, garland1997 4.1 step 1 holds one per initial vertex)
and a position-only triangle-mesh export. Byte counts are exact, deterministic and
implementation-independent: a C++ exporter's symmetric 4x4 quadric is the same ten
floats, and nothing here drifts with machine load.

WHAT IT IS NOT: it is NOT a bake TIME. No wall-clock is measured or printed, because a
CPython heap loop would misstate a production exporter by orders of magnitude, and
because absolutes on a shared container move 15-30% with load. It is not a GPU cost and
not a frame cost.

Seed 20260914 (used only for the random-point TIN; every other figure is deterministic).
Run: python3 mesh-extraction.py
"""
import resource
import numpy as np
from scipy.spatial import Delaunay

SEED = 20260914


def mib(b):
    return b / 2**20


def gib(b):
    return b / 2**30


def rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def quadric_state(n, dtype):
    """One symmetric 4x4 quadric per INITIAL vertex = one per source heightfield cell.
    Ten unique entries (upper triangle of a symmetric 4x4)."""
    m = n * n
    before = rss_mib()
    q = np.zeros((m, 10), dtype=dtype)
    q[:] = 1.0                      # touch every page so the pages are really resident
    after = rss_mib()
    out = (q.nbytes, q.nbytes / m, after - before)
    del q
    return out


def grid_mesh_bytes(n):
    """A position-only export of an n x n triangulated grid:
    float32 xyz positions + uint32 triangle indices."""
    m = n * n
    idx = np.arange(m, dtype=np.uint32).reshape(n, n)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, d = idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    tris = np.concatenate([np.stack([a, b, c], 1), np.stack([b, d, c], 1)])
    pos = np.zeros((m, 3), dtype=np.float32)
    hull = 4 * (n - 1)
    return m, len(tris), pos.nbytes, tris.nbytes, hull


def tin_mesh_bytes(m):
    """The same export of a genuine (non-grid) Delaunay TIN over random points."""
    rng = np.random.default_rng(SEED)
    pts = rng.random((m, 2))
    tri = Delaunay(pts)
    hull = len(np.unique(tri.convex_hull))
    pos = np.zeros((m, 3), dtype=np.float32)
    idx = tri.simplices.astype(np.uint32)
    return m, len(tri.simplices), pos.nbytes, idx.nbytes, hull


print("=== 1. QEM bake state: one quadric per initial vertex (= per source cell) ===")
for dt, name in ((np.float64, "float64"), (np.float32, "float32")):
    nb, per, drss = quadric_state(4096, dt)
    print(f"  4096^2 cells, {name}: {nb} B total, {per:.1f} B per cell, "
          f"{gib(nb):.4f} GiB, RSS delta {drss:.0f} MiB")
print("  (ru_maxrss is a PEAK, so only the first and largest allocation shows a delta;")
print("   nbytes and B-per-cell are exact for every row and are the figures quoted.)")
for dt, name in ((np.float64, "float64"), (np.float32, "float32")):
    nb, per, _ = quadric_state(1024, dt)
    print(f"  1024^2 cells, {name}: {per:.1f} B per cell, {mib(nb):.1f} MiB  "
          f"(rate is flat in grid size)")

print("=== 2. Exported mesh bytes per vertex (float32 xyz + uint32 indices) ===")
for n in (129, 449, 1000, 2049):
    m, t, pb, ib, hull = grid_mesh_bytes(n)
    print(f"  grid {n}^2: m={m} verts, t={t} tris, t/m={t/m:.4f}, "
          f"Euler 2m-2-hull={2*m - 2 - hull} -> {'MATCH' if t == 2*m - 2 - hull else 'MISMATCH'}, "
          f"{pb}+{ib} B = {(pb+ib)/m:.3f} B per vertex, {(pb+ib)/1e6:.2f} MB")
for m in (50_000, 200_000, 1_000_000):
    mm, t, pb, ib, hull = tin_mesh_bytes(m)
    print(f"  random-point Delaunay TIN m={mm}: t={t}, t/m={t/mm:.4f}, hull={hull}, "
          f"Euler 2m-2-hull={2*mm - 2 - hull} -> {'MATCH' if t == 2*mm - 2 - hull else 'MISMATCH'}, "
          f"{(pb+ib)/mm:.3f} B per vertex, {(pb+ib)/1e6:.2f} MB")

print("=== 3. The error law in bytes ===")
k = 2 ** (1 / 0.7)
print(f"  RMS ~ m^-0.7  =>  halving RMS needs 2^(1/0.7) = {k:.4f}x the vertices")
per_vert = 36.0
for m0 in (1_000_000,):
    b0, b1 = m0 * per_vert, m0 * k * per_vert
    print(f"  at {per_vert:.0f} B/vertex: m={m0} is {b0/1e6:.1f} MB; "
          f"its half-RMS successor m={m0*k:.0f} is {b1/1e6:.1f} MB "
          f"(ratio {b1/b0:.4f} -- identical to the vertex ratio, the rate being flat)")
print("  attribute add-ons: float32 normal +12.0 B/vertex, float32 UV +8.0 B/vertex")
print("=== NO TIME IS MEASURED HERE. Bake wall-clock is deliberately unpriced. ===")
