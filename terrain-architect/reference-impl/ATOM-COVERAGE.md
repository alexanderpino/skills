# Atomic-base coverage & scope

**What this is.** The reference implementation is a **curated core** of the atomic bases — the
irreducible nodes everything else composes from (analytic noise, SDF/gradient primitives, combiners,
and the iterative erosion/flow solvers). It is deliberately **not exhaustive**: it covers the
must-have set that reproduces the large majority of real terrain work, not every node Gaea / World
Machine / Houdini ship. The named *landform* generators (Mountain, Volcano, Canyon, …) are macros
over these atoms and live in `landforms.py`; this file is only about the atoms.

**Two artifacts, one guarantee.** The skill has two representations of each atom: the neutral
**pseudocode** in `references/` (the algorithm + its grounding) and the executable **reference impl**
here. They are meant to correspond. `tests/test_atom_coverage.py` is the anti-drift harness that keeps
them honest: every atom listed as *implemented* below must exist as a callable in its module, the
reference module's public surface must not contain an atom missing from this list, and every
*deferred* atom must be genuinely absent from the code (documented, not silently half-built). The same
harness also guards the **landform generators** (macros over the atoms — `mountain`, `ridge`, `volcano`,
`canyon`, `fault_block_butte`): each must stay named in its chapter (`11`) pseudocode. What the harness
does **not** prove is that the pseudocode is numerically correct, nor that its CONSTANTS match the code
(e.g. a profile exponent) — pseudocode↔code *constant* drift is caught by the review/faithfulness passes,
and numerical correctness by the per-atom oracle tests (`test_noise.py`, `test_ops_filters.py`, the solver tests).

## Implemented atomic bases

**Noise (`noise.py`, chapter `01`):** `perlin`, `value`, `simplex`, `worley` (f1 / f2f1 / inv_f1),
`fbm`, `ridged_mf`, `hybrid_mf`, `gabor` (anisotropic/directional), `domain_warp`, `curl`.

**SDF / gradient / combiner primitives (`ops_filters.py`, chapter `10`):** `sd_circle`, `sd_box`,
`sd_convex_polygon`, `sd_segment`, `radial_gradient`, `cone`, `smin`, `smax`, `blend`, `remap`.
(The module also carries the filter/morphology toolbox — `gaussian`, `bilateral`, `guided_filter`,
`perona_malik`, `dilate`/`erode`/`opening`/`closing`, `twist`, `bend` — treated as filters, not atoms.)

**Solver atoms (iterative, stateful — cannot be composed from static fields):** flow routing
(`flow.priority_flood_fill`, `d8_receivers`, `d8_accumulation`, `mfd_accumulation`), stream-power
incision (`erosion_streampower.stream_power_evolve`), droplet erosion (`erosion_droplet.droplet_erode`),
thermal/talus (`erosion_thermal.thermal_erosion`), hillslope diffusion (`diffusion.hillslope_diffuse`),
virtual-pipe flow + coupled erosion (`erosion_pipe.pipe_water`, `pipe_erode`), shallow-water
(`shallow_water.simulate`).

## Documented but NOT implemented (deferred)

These are discussed in the chapter pseudocode / grounding but are **not** in the reference impl — the
reference is narrower than the chapters here, by design:

- **OpenSimplex2** — the CC0 lattice is a *port target* (`references/22-open-source-grounding.md`), not
  reimplemented; `simplex` covers the same need for the reference.
- **Wavelet noise** (Cook & DeRose) — band-limited, alias-free; discussed in `01`, not built.
- **Generic sparse-convolution noise** — `gabor` is the one sparse-convolution instance we implement;
  the general form is not.

Other tool nodes (Cellular3D, Cracks, CutNoise, LineNoise/DotNoise, …) are catalogued as deferred in
`GROUNDING.md`'s node table; they are landform/pattern nodes, not the generative atoms this file scopes.
