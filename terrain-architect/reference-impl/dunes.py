"""Aeolian dunes — Werner 1995 slab cellular automaton (05-erosion-thermal-aeolian.md).

Sand moves as discrete slabs: erode a slab from a random occupied cell, transport it
downwind, and deposit with probability p_sand where sand already lies, p_bare on bare
ground. The whole model is that one asymmetry: p_sand > p_bare makes deposition
self-reinforcing, and dunes grow out of a flat sheet. p_sand == p_bare -> no instability,
no dunes. Slabs are conserved exactly.

This is a MINIMAL Werner variant. Two of the chapter's (05) "three ideas that make it work" are
**not** implemented and would be needed for a faithful full model: (1) the 15-degree lee **shadow-zone**
capture that sharpens slip faces and drives migration, and (2) per-move **avalanching** (repose
relaxation) that keeps the crest from growing into a spike. The deposition-probability instability
alone (p_sand > p_bare) is the verifiable core — Werner's central result and the skill's two dune
failure modes — so this is honestly-scoped as illustrative, not a faithful implementation of the full
`05` pseudocode. Slabs are conserved exactly either way.
"""
import numpy as np


def werner_dunes(sand, iters, seed=0, p_sand=0.6, p_bare=0.4, hop=1, wind=(0, 1)):
    """Return the slab-count grid after `iters` sweeps (each sweep = n*m slab moves).
    sand: integer slab counts. wind: (di, dj) downwind direction, periodic domain."""
    sand = np.asarray(sand).astype(np.int64).copy()
    n, m = sand.shape
    rng = np.random.default_rng(seed)
    wi, wj = wind
    for _ in range(int(iters) * n * m):
        i = int(rng.integers(n))
        j = int(rng.integers(m))
        if sand[i, j] <= 0:
            continue
        sand[i, j] -= 1                       # erode a slab
        ci, cj = i, j
        while True:                           # transport downwind until it deposits
            ci = (ci + wi * hop) % n
            cj = (cj + wj * hop) % m
            p = p_sand if sand[ci, cj] > 0 else p_bare
            if rng.random() < p:
                sand[ci, cj] += 1
                break
    return sand
