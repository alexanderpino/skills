---
type: Bibliography
title: Papers — architecture
description: "Sources for the architecture axis: graph evaluation, caching and invalidation, layering, and the driver fields a terrain graph carries."
tags: [bibliography, provenance, architecture]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Papers — architecture

The bibliography family for the architecture axis: how a node graph is executed, cached,
invalidated and kept resolution-independent. **The tier table and the two non-negotiable rules
live in `papers-flow.md`** and are not repeated here; read them before citing anything below.

⚠️ **This axis was grounded from scratch, and that is worth stating.** Its in-repo source,
`terrain-architect/references/14-graph-runtime.md`, is 425 lines of architecture prose carrying
**zero citations** — checked, no inline markers anywhere in the file. Distilling it would have
produced confident unsourced assertion, which is the failure mode this skill exists to prevent.
So the mechanisms below are grounded in the **incremental-computation and build-systems**
literature, which has studied exactly this problem for twenty years and which the terrain
literature does not cite. The mapping is not a metaphor: a node graph *is* a build system whose
keys are node outputs, and the design space is already mapped.

One tier decision recurs and is stated once: **a specification, a vendor documentation page or a
conference talk is graded `F`**, however authoritative. Microsoft's DirectX specifications are the
recurring case on this axis. Naming them is right; dressing them as peer review is not.

## Incremental evaluation and caching

- **alacarte** `P` — Mokhov, A., Mitchell, N. & Peyton Jones, S. (2018). *Build Systems à la
  Carte.* Proc. ACM Program. Lang. 2(ICFP), Article 79. — The decomposition this axis is built
  on: a build system is a **scheduler** (§4.1: topological, restarting, suspending) crossed with a
  **rebuilder** (§4.2: dirty bit, verifying traces, constructive traces, deep constructive
  traces). §2.3 defines **early cutoff**; §2.5 Table 1 classifies Make, Excel, Shake and Bazel by
  scheduler, minimality, cutoff and cloud support; §5.4 models Bazel, CloudBuild, Buck and Nix and
  closes by naming a suspending scheduler with constructive traces as the most desirable
  combination then unavailable.
- **adapton** `P` — Hammer, M.A. et al. (2014). *Adapton: Composable, Demand-Driven Incremental
  Computation.* PLDI 2014, Edinburgh. — Demand-driven incremental computation: results are
  recomputed lazily when *observed*, not eagerly when an input changes. §2 is the overview, §4.1
  the trace structure and propagation semantics.
- **acar2002** `P` — Acar, U.A., Blelloch, G.E. & Harper, R. (2002). *Adaptive Functional Programming.*
  POPL '02, Portland OR. — Change propagation as a language feature rather than an application
  concern; §6 proves the propagation sound. The ancestor of the whole self-adjusting-computation
  line that `adapton` continues.

## Tiled evaluation and bounds

- **halide** `P` — Ragan-Kelley, J., Barnes, C., Adams, A., Paris, S., Durand, F. & Amarasinghe,
  S. (2013). *Halide: A Language and Compiler for Optimizing Parallelism, Locality, and
  Recomputation in Image Processing Pipelines.* PLDI 2013, 519–530. doi:10.1145/2491956.2462176. —
  §4.2 Bounds Inference: the region an input must produce is inferred backwards from the region its
  consumers require, by interval analysis, composed recursively up the pipeline. Fig. 5 carries the
  worked tiled halo. §3.1 names the apron ("ghost zones", "overlapped tiling") and states the
  redundancy-versus-locality trade.
  ⚠️ It does **not** support a claim about how a *masked* operator's footprint combines: the paper
  contains no notion of union, mask or select, and computes bounds per callee function. Cite
  `nuke_request` for the union, not this.
- **barnes2017** `P` — Barnes, R. (2017). *Parallel non-divergent flow accumulation for trillion
  cell digital elevation models on desktops or clusters.* Environmental Modelling & Software 92,
  202–212. doi:10.1016/j.envsoft.2017.02.022. — The counterexample to "globally ordered means it
  cannot tile". §3.1 states why an apron cannot work and how a perimeter aggregate fixes it; §3
  gives the three-stage structure and the two-trillion-cell result. §2 restricts to non-divergent
  flow because divergent metrics resist divide-and-conquer — which makes the D8/MFD choice a tiling
  decision as well as a hydrology one.
- **barnes2016** `P` — Barnes, R. (2016). *Parallel Priority-Flood depression filling for trillion
  cell digital elevation models on desktops or clusters.* Computers & Geosciences 96, 56–68.
  doi:10.1016/j.cageo.2016.07.001. — The same tile → perimeter digest → global reduce → offset
  shape applied to depression filling, which is what makes it a pattern rather than one algorithm's
  trick.
- **nuke_request** `F` — Foundry. *Nuke Developer Kit*, `DD::Image::Iop` class reference,
  `request()` / `_request()`; and the NDK Developers Guide, "Basic Image Calls". — No canonical
  paper: a compositing SDK's own documentation. Every region requested of an input is **unioned**,
  and the union is what gets computed and cached; a node reading a neighbourhood widens the box it
  requests; a node with random access must request the input's entire bounding box.

## Tool practice — layering, masking and evaluation

No canonical paper exists for any of this; these are vendors documenting their own products, and
the prose that rests on them must say so. They are cited for **what a shipping tool chose**, which
is evidence about practice, never about correctness.

- **gaea_masks** `F` — QuadSpinner. *Gaea 2 Documentation*, Using Gaea → Terrain Basics → "Masks".
  https://docs.gaea.app/ (the site is JS-rendered; the full corpus is published as plain text at
  https://docs.gaea.app/llms-full.txt, slug `masks`). — States that a mask is a greyscale weight,
  that direct masking and the post-hoc Mask node have **"no difference in results"**, and that the
  Mask node is preferred because masking a node directly "will force a rebuild of the entire node"
  while the post-process "is extremely fast".
- **gaea_accumulator** `F` — QuadSpinner. *Gaea 2 Documentation*, Node Reference → Utilities →
  "Accumulator", and the User Guide page "Accumulators". — A Generator node with no data inputs
  whose output depends on every Snow/Water/Debris/Trees node in the graph, selected by `Type` and
  scoped by `Restrict to Group`. Carries its own failure mode verbatim — "The Accumulator will only
  add nodes that have been built" — and the workaround, which is for the user to draw an edge whose
  only purpose is ordering.
- **gaea_mixer** `F` — QuadSpinner. *Gaea 2 Documentation*, Using Gaea → "Layering Textures". — The
  Mixer node: a layer stack with built-in height and slope masks living inside the DAG.
- **houdini_hdk** `F` — SideFX. *Houdini Development Kit*, Building Custom Operators → "Cooking",
  and Basics → "Cooking" (Houdini 22.0). — The documented answer to an undeclared input set: a node
  that cooks another's data "via some other means" **must** call `OP_Node::addExtraInput()`, and
  must do so on *every* cook because extra inputs are cleared as soon as dirty propagation
  traverses them. Also states the two-phase model: dirt is pushed eagerly, data is pulled lazily.

## GPU execution, 2026

- **hlsl_wg_removal** `F` — Microsoft. *HLSL Specifications*, `proposals/0018-work-graphs.md`
  (status Completed), and `proposals/0046-dxil110.md`. github.com/microsoft/hlsl-specs. — The
  primary artefact for the removal: the header reads "Version: SM 6.8 / Removed: SM 6.10", and the
  body states "Work Graphs was introduced in Shader Model 6.8, and has been removed effective
  Shader Model 6.10. Driver support for Work Graphs is still available and supported on many
  devices." 0046 adds "DXIL 1.10 removes support for 'node' shaders."
- **dxc_wg_removal** `F` — Microsoft. *DirectXShaderCompiler*, PR #8798 "[SM 6.10] Disable Work
  Graphs in SM 6.10", merged 2026-08-31. — The implementation, and the exact lifecycle in a source
  comment: "Work graph node record objects: available SM6.8, deprecated SM6.9, obsoleted SM6.10."
  `lib_6_x` targets are explicitly exempted from the new diagnostic.
- **d3d_worklists** `F` — Microsoft. *DirectX Specs*, `d3d/WorkLists.md`, v0.851, added 2026-08-21.
  — Motivated by `ExecuteIndirect`'s inability to switch PSOs from the GPU timeline, and
  self-described as an `ExecuteIndirect` analog. It does **not** claim to replace work graphs, and
  states "This feature is early in development. While the spec is public, implementations are not
  ready. Hopefully a preview can be available some time in 2027."

## Driver fields — temperature, sun, shadow, wind

- **dozier2022** `P` — Dozier, J. (2022). *Revisiting Topographic Horizons in the Era of Big Data
  and Parallel Computing.* IEEE Geoscience and Remote Sensing Letters 19, art. 8024605.
  doi:10.1109/LGRS.2021.3125278 (open access). — The horizon sweep, its complexity, its real
  lineage, tile-halo requirements and measured timings. §I records that the order-N horizon method
  is **Dozier, Bruno & Downey (1981)**, Computers & Geosciences 7(2), 145–151 — not a 2010 paper.
- **winstral2002** `P` — Winstral, A., Elder, K. & Davis, R.E. (2002). *Spatial Snow Modeling of
  Wind-Redistributed Snow Using Terrain-Based Parameters.* Journal of Hydrometeorology 3(5),
  524–538. — The keystone for this axis: §3 states that "the selection of a maximum
  shelter-producing pixel based on slope is analogous to the determination of solar shading within
  the horizon function used in radiation modeling". Also Eq. (1) defining `Sx`, Eqs. (3)–(5) for the
  flow-separation detector `Sb`, and §4's measured search-distance comparison.
- **minder2010** `P` — Minder, J.R., Mote, P.W. & Lundquist, J.D. (2010). *Surface temperature lapse
  rates over complex terrain: Lessons from the Cascade Mountains.* J. Geophysical Research 115,
  D14122. doi:10.1029/2009JD013493. — Measures what the conventional 6.5 °C/km assumption is worth.
- **reda2004** `P` — Reda, I. & Andreas, A. (2004). *Solar position algorithm for solar radiation
  applications.* Solar Energy 76(5), 577–589. doi:10.1016/j.solener.2003.12.003.
  ⚠️ **What was actually read is the companion NREL technical report** NREL/TP-560-34302 (rev.
  January 2008, 40 pp.), not the Solar Energy article. The locator points into the report.
- **furich2002** `P` — Fu, P. & Rich, P.M. (2002). *A geometric solar radiation model with
  applications in agriculture and forestry.* Computers and Electronics in Agriculture 37(1–3),
  25–35. — The peer-reviewed model behind ArcGIS's Area Solar Radiation tool; the occlusion →
  insolation coupling with its fitted equations.
- **forthofer2014** `P` — Forthofer, J.M., Butler, B.W. & Wagenbrenner, N.S. (2014). *A comparison
  of three approaches for simulating fine-scale surface winds… Part I.* International Journal of
  Wildland Fire 23(7), 969–981. doi:10.1071/WF12089. — The wind-field taxonomy with a measured
  cost/accuracy comparison across the three approaches.
- **stendardo2020** `P` — Stendardo, N., Desthieux, G., Abdennadher, N. & Gallinelli, P. (2020).
  *GPU-Enabled Shadow Casting for Solar Potential Estimation in Large Urban Areas.* Applied Sciences
  10(15), 5361. doi:10.3390/app10155361 (open access). — The GPU brute-force baseline, and §3.2's
  coarse-grid trick for long-baseline occlusion: evaluate distant obstruction on a 100× coarser
  heightfield and take the minimum.

## In-repo sources

These are artefacts in this repository rather than published work. They are `F` — a register or a
chapter is not peer review — but they are checkable, which a recollection is not.

- **ta_graph_runtime** `F` — `terrain-architect/references/14-graph-runtime.md`. — The node and
  parameter model, demand-driven evaluation, the content-addressed cache key, dirty propagation,
  and the accumulator pattern. **Carries no citations of its own**, so it is cited here for what a
  practitioner built and for the two defects Gaia found in it, never as evidence that a mechanism
  is correct.
- **ta_ops_filters** `F` — `terrain-architect/references/10-primitives-ops-filters.md`. —
  §"Placement & masking" for `apply_masked` and the rules that placements are authored in metres
  and that a binary mask must never ship; §"Place before you sample, not after" for the
  coordinate-versus-raster transform measurement. Unlike its sibling chapter this one **does** carry
  citations, and it records two of its own errors in place, which is why it is worth reading.
- **simd_dispatch_drift** `F` — `terrain-architect/registers/figure-regen.tsv`, on the branch
  `origin/claude/terrain-architect-definition-of-done`. — A measured, reproducible case of the
  same code on the same CPU producing materially different terrain under two SIMD dispatch
  regimes. Records the reproduction recipe, the per-ufunc 1-ULP measurement over 10007 doubles,
  and the amplification mechanism. **Not present on `main` or on this branch** — cite it to that
  branch or not at all.
