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


def werner_dunes(sand, iters, seed=0, p_sand=0.6, p_bare=0.4, hop=1, wind=(0, 1),
                 shadow=True, shadow_tan=0.268, avalanche=True, repose=2):
    """Return the slab-count grid after `iters` sweeps (each sweep = n*m slab moves).
    sand: integer slab counts. wind: (di, dj) downwind direction, periodic domain.

    Full Werner (1995) slab model — all THREE ideas that make real dunes emerge:
      1. **Deposition instability** — a saltating slab deposits with probability `p_sand`
         over sand, `p_bare` over bare ground. `p_sand > p_bare` is self-reinforcing, so
         sand is swept into dunes separated by bare corridors (the core instability).
      2. **Lee shadow zone** (`shadow`) — a cell sheltered behind a taller upwind obstacle,
         below the shadow line of slope `shadow_tan` (~15°), CAPTURES any slab that reaches
         it (deposit p=1) and is NOT eroded. This builds and sharpens the lee **slip face**
         and drives dune **migration** — the feature that turns clusters into shaped dunes.
      3. **Avalanching** (`avalanche`) — after every erode/deposit, a face steeper than the
         angle of repose (`repose` slabs between neighbours) topples downslope until stable,
         so crests can't spike and the lee face sits at repose (the slip face).
    Slabs are conserved exactly (transport, capture and avalanching all only MOVE slabs).
    Set `shadow=False, avalanche=False` for the minimal deposition-only variant.

    Grounded constants (Werner 1995; Momiji et al. 2000): `shadow_tan = tan(15°) = 0.268` is the
    lee flow-separation (recirculation) angle; `repose = 2` slabs is the dry-sand angle of repose,
    tan⁻¹(2/3) = 33.7°, under the standard 1:3 slab aspect ratio (height:width); `hop` is the
    saltation length (Werner used ~5 cells; a longer hop lengthens the dune wavelength).
    """
    sand = np.asarray(sand).astype(np.int64).copy()
    n, m = sand.shape
    rng = np.random.default_rng(seed)
    wi, wj = wind
    reach = 16                                        # upwind cells to test for a shadow caster
    hmax = int(sand.max())                            # refreshed each sweep; bounds the shadow walk

    def shadowed(ci, cj):
        h = sand[ci, cj]
        kmax = min(reach, int((hmax + 2 - h) / shadow_tan) + 1)   # no caster can shadow past here
        for k in range(1, kmax + 1):                  # walk upwind; is any caster's shadow line above us?
            if sand[(ci - wi * k) % n, (cj - wj * k) % m] - k * shadow_tan > h:
                return True
        return False

    def relax(seed_i, seed_j):
        stack = [(seed_i, seed_j)]
        budget = 512                                  # bound the local relaxation
        while stack and budget > 0:
            a, b = stack.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                na, nb = (a + di) % n, (b + dj) % m
                if sand[a, b] - sand[na, nb] > repose:     # a is too high over nb -> topple a->nb
                    sand[a, b] -= 1; sand[na, nb] += 1
                    stack.extend(((a, b), (na, nb))); budget -= 1; break
                if sand[na, nb] - sand[a, b] > repose:     # nb too high over a (e.g. fresh erosion pit)
                    sand[na, nb] -= 1; sand[a, b] += 1
                    stack.extend(((na, nb), (a, b))); budget -= 1; break

    for _sweep in range(int(iters)):
        hmax = int(sand.max())                        # refresh the shadow-walk bound once per sweep
        for _ in range(n * m):
            i = int(rng.integers(n)); j = int(rng.integers(m))
            if sand[i, j] <= 0:
                continue
            if shadow and shadowed(i, j):             # sheltered cells are not eroded
                continue
            sand[i, j] -= 1                           # erode a slab
            if avalanche:
                relax(i, j)
            ci, cj = i, j
            while True:                               # transport downwind until it deposits
                ci = (ci + wi * hop) % n
                cj = (cj + wj * hop) % m
                if shadow and shadowed(ci, cj):       # shadow zone captures the slab (slip-face build)
                    sand[ci, cj] += 1
                    if avalanche:
                        relax(ci, cj)
                    break
                p = p_sand if sand[ci, cj] > 0 else p_bare
                if rng.random() < p:
                    sand[ci, cj] += 1
                    if avalanche:
                        relax(ci, cj)
                    break
    return sand
