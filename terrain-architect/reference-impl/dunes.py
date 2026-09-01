"""Aeolian dunes — Werner 1995 slab cellular automaton (05-erosion-thermal-aeolian.md).

Sand moves as discrete slabs: erode a slab from a random occupied cell, transport it
downwind, and deposit with probability p_sand where sand already lies, p_bare on bare
ground. The whole model is that one asymmetry: p_sand > p_bare makes deposition
self-reinforcing, and dunes grow out of a flat sheet. p_sand == p_bare -> no instability,
no dunes. Slabs are conserved exactly.

All three of the chapter's (05) "three ideas that make it work" ARE implemented and on by
default: the deposition-probability instability (p_sand > p_bare), the 15-degree lee **shadow-zone**
capture that sharpens slip faces and drives migration (`shadow=True`), and per-move **avalanching**
(repose relaxation) that keeps the crest from growing into a spike (`avalanche=True`). Set
`shadow=False, avalanche=False` for the minimal deposition-only variant, which is what the
instability test exercises in isolation. The model is invariant-checked, not benchmark-accurate:
slabs are conserved exactly, and the emergent forms are read as ridge signal, not measured against
a wind-tunnel dune. (This header claimed the opposite — "two of the three are not implemented" —
long after `shadow` and `avalanche` had shipped; see `tests/test_dunes.py`, which exercises both.)
"""
import numpy as np


def werner_dunes(sand, iters, seed=0, p_sand=0.6, p_bare=0.4, hop=5, wind=(0, 1),
                 shadow=True, shadow_tan=0.268, avalanche=True, repose=2, wind_field=None):
    """Return the slab-count grid after `iters` sweeps (each sweep = n*m slab moves).
    sand: integer slab counts. wind: (di, dj) downwind direction, periodic domain.

    `wind_field=(u, v)` (the standard (col, row) components from `winds.wind_field`) overrides
    `wind` with a per-cell direction: each slab is transported along the LOCAL wind and each
    shadow test walks the LOCAL upwind, so the path BENDS through the terrain-steered flow. This
    is what makes a valley-floor dune field trend along the valley rather than along the regional
    wind, and what banks sand against an obstacle as an anchored dune (`05`). Directions are
    rounded to the 8 grid neighbours (a unit vector always has a component >= 1/sqrt(2), so the
    step is never degenerate).

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
    tan⁻¹(2/3) = 33.7°, under the standard 1:3 slab aspect ratio (height:width).

    ⚠️ `hop` — THE SALTATION LENGTH, IN CELLS. A slab is carried a FIXED number of cells downwind
    per transport step, and that length sets the emergent dune WAVELENGTH (a longer hop, a longer
    wavelength — measured, not asserted: see `tests/test_dunes.py`
    `test_hop_sets_the_dune_wavelength`). **The value is 5**, which is Werner's, and all four places
    that state it now agree:

      * Werner (1995), as restated by Kok, Parteli, Michaels & Karam 2012 (Rep. Prog. Phys. 75,
        106901, §3.2.2): a slab "moves downwind to a new lattice site l (typically equal to 5)
        sites away (Werner 1995)".
      * `05`'s Werner pseudocode block:  `L = saltationHop   # ~5 cells, fixed`   (05:412)
      * `05`'s runnable-reference note, thirteen lines above that block: "≈5 cells"  (05:399)
      * this signature: `hop=5`

    This constant was previously stated FOUR different ways — 05:412 `~5`, 05:399 `≈3`, this
    docstring `~5`, the signature `1` — i.e. the chapter contradicted itself before the module was
    consulted. The chapter-vs-code half was registered as `werner-saltation-hop` in
    `tests/test_pseudocode_drift.py`'s KNOWN_DIVERGENCES. That row is now RETIRED, and the constant
    is guarded from both sides instead: the 05:412 block and this default are a normal pinned pair
    in that file's BLOCK_CONSTANTS, and `tests/test_dunes.py::test_chapter_note_quotes_the_shipped_hop`
    pins 05:399's PROSE (which no fenced-block register can see) against this
    signature. A fifth value cannot appear quietly.

    Why 5 and not the 3 this repo's dune panel happens to pass: 5 is the published constant, and
    `hop` is a physical claim about transport length, not a taste setting. `hop=3` was never
    unanimous here either — `capability_grid.py:317` passes 3, `tests/test_dunes.py` passes 3 and 1,
    and `gallery.py:166` names nothing and so ran on the old default of 1.

    Passing a SHORTER hop is legitimate and is a statement about the run, not a correction: on a
    tile narrower than ~64 cells along the wind a 5-cell hop leaves barely a dune or two in the
    domain, so a small demo tile may want `hop=1..3`. What is physically set is the mean transport
    path `hop / p_bare` (Nield & Baas 2008; the CA's stand-in for wind strength), so halving `hop`
    and halving `p_bare` are the same move.
    """
    sand = np.asarray(sand).astype(np.int64).copy()
    n, m = sand.shape
    rng = np.random.default_rng(seed)
    if wind_field is None:
        wi_f = np.full((n, m), int(wind[0]), dtype=np.int64)
        wj_f = np.full((n, m), int(wind[1]), dtype=np.int64)
    else:                                             # (u, v) = (col, row) -> per-cell (di, dj)
        u, v = wind_field
        u = np.broadcast_to(np.asarray(u, dtype=np.float64), (n, m))
        v = np.broadcast_to(np.asarray(v, dtype=np.float64), (n, m))
        mag = np.hypot(u, v) + 1e-30
        wi_f = np.rint(v / mag).astype(np.int64)      # row step
        wj_f = np.rint(u / mag).astype(np.int64)      # col step
    reach = 16                                        # upwind cells to test for a shadow caster
    hmax = int(sand.max())                            # refreshed each sweep; bounds the shadow walk

    def shadowed(ci, cj):
        h = sand[ci, cj]
        wi, wj = int(wi_f[ci, cj]), int(wj_f[ci, cj])
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
                ci, cj = ((ci + int(wi_f[ci, cj]) * hop) % n,     # step along the LOCAL wind
                          (cj + int(wj_f[ci, cj]) * hop) % m)
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
