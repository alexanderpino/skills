# Advanced Terrain Generator Blueprint

The end-to-end assembly for an agent implementing an advanced terrain generator. The other
chapters define individual algorithms; this chapter closes the product loop for **offline /
pre-cooked**, **runtime**, and **hybrid** generation. It is terrain-algorithm complete: target
engine rendering APIs, editor UX and gameplay integration remain project-specific.

Contents: [Delivery modes](#delivery-modes) · [Minimum node library](#minimum-node-library) ·
[Shared substrate](#shared-substrate) · [Offline pipeline](#offline--pre-cooked-pipeline) ·
[Runtime pipeline](#runtime-pipeline) · [Hybrid pipeline](#hybrid-pipeline) ·
[Implementation milestones](#implementation-milestones) ·
[Acceptance gates](#acceptance-gates) · [Agent delivery contract](#agent-delivery-contract)

## Delivery modes

| Mode | Terrain processes available | Execution shape | Use when |
|---|---|---|---|
| **Offline / pre-cooked** | Full corpus, including GLOBAL hydrology, stream power, climate and long-radius analysis | Deterministic full-domain or region bake, cached and exported | Authored worlds, shipped maps, high-quality editor builds |
| **Runtime** | T0–T2 LOCAL/NEIGHBOURHOOD processes; GLOBAL work only as bounded async region jobs | Seeded chunk/clipmap generation under frame and memory budgets | Infinite worlds, user-generated worlds, destructible/regenerating regions |
| **Hybrid** | Baked/coarse GLOBAL process history plus runtime local detail and state | Global fields streamed; deterministic local refinement per chunk | The normal advanced game: believable drainage and cheap runtime variation |

Do not promise a fully runtime T3 world merely because kernels are fast. Drainage area, stream
power and other GLOBAL fields need a domain. Choose one of three honest treatments: bake them,
compute them asynchronously over a declared region, or omit them and accept the visual loss.

## Minimum node library

An advanced generator is not complete until every row has at least one production implementation:

| Family | Minimum nodes | Primary references |
|---|---|---|
| **Fields & sources** | constant, gradient, radial/SDF primitives, imported height/DEM, world-coordinate noise | `01`, `10`, `08` |
| **Fractal synthesis** | FBM, ridged/hybrid multifractal, domain warp, octave controls | `01` |
| **Composition** | add/subtract, lerp, smooth min/max, curve/remap, clamp, switch, morphology, edge-preserving filter | `10` |
| **Macro geology** | uplift field, plate/fault authoring, strata/lithology, volcanic/crater primitives | `02`, `11`, `19` |
| **Hydrology** | epsilon fill or breach, D8 plus MFD/D∞, accumulation in m², lake/sea policy | `03` |
| **Erosion** | one small-scale hydraulic model, Braun–Willett stream power, hillslope/thermal, diffusion | `04`, `05` |
| **Regime processes** | aeolian/dunes, glacial/coastal, arid/periglacial, lava as product scope requires | `05`, `12`, `16`, `17`, `19` |
| **Analysis** | slope, aspect, curvature, drainage/wetness, horizon/SVF AO, distance fields | `06` |
| **Materials & layers** | bedrock/soil/sand/water/snow stack, lithology and physical properties, splat/material masks | `08`, `11`, `13`, `18` |
| **Climate & biomes** | lapse rate, orographic rain, wind, snow line, biome/ecosystem fields | `13` |
| **Scatter** | deterministic Poisson/blue-noise placement, density masks, hierarchical scatter | `07` |
| **Output** | quantisation last, normals/AO, mesh/heightfield, tiling/aprons, LOD/clipmaps, engine encoding | `08` |
| **Runtime substrate** | typed ports, pure nodes, cache keys, dirty propagation, preview, jobs, serialisation | `14`, `15` |

Product scope may omit a regime family; it may not omit the shared contracts that keep remaining
nodes composable.

## Shared substrate

Both offline and runtime modes execute the same logical DAG:

```text
evaluate(nodeId, worldRegion, resolution, quality, rootSeed) -> FieldSet

cacheKey =
  hash(nodeTypeVersion, parametersInWorldUnits, inputContentHashes,
       worldRegion, resolution, quality, rootSeed, numericalBackendVersion)
```

Every node declares:

```text
inputs/outputs + units
LOCAL | NEIGHBOURHOOD(radiusMetres) | GLOBAL
RESOLUTION_INVARIANT | RESOLUTION_BOUND(policy)
CPU | GPU | EITHER
precision + boundary policy + deterministic seed/update policy
oracle set + implementation version
```

Use one field/layer model across editor preview, offline bake and runtime. Separate algorithms for
"editor terrain" and "game terrain" guarantee drift; quality tiers should alter resolution,
iteration count and optional detail, not field meaning.

## Offline / pre-cooked pipeline

Canonical full-quality DAG:

```text
world extent + seed
  -> macro uplift / geology / base shape
  -> scale-free noise and authored constraints
  -> depression policy
  -> global routing + drainage area
  -> stream-power or hydraulic erosion
  -> hillslope / thermal / regime processes
  -> sea, lakes, coast and climate feedbacks
  -> final analysis fields
  -> material/layer masks
  -> deterministic scatter
  -> normals/AO/colour/splat outputs
  -> chunk, LOD, quantise and package
```

Execution rules:

1. Evaluate GLOBAL nodes monolithically or by an algorithm with explicit cross-region
   reconciliation; never pretend independent tiles are equivalent.
2. Cache immutable intermediate fields in R32F or stronger working precision.
3. Make previews a declared resolution policy; final bake reuses the same graph and seed.
4. Export chunks only after all cross-chunk processes finish.
5. Retain graph version, node versions, root seed, world units and verification report beside the
   cooked assets so a world is reproducible.

## Runtime pipeline

Runtime generation begins from the same world coordinate and seed contract but obeys T0–T3
budgets from `15`:

```text
chunk request
  -> resolve global/coarse fields available for region
  -> T0 base/noise/operators on GPU or jobs
  -> bounded T1/T2 local erosion/detail with apron
  -> analysis needed by materials/scatter
  -> mesh/height upload + material maps + instances
  -> publish atomically when all seam contracts pass
```

Required runtime mechanics:

- **Request key:** world seed, graph version, chunk coordinate, LOD and quality.
- **Cancellation:** every staged CPU job or GPU batch can be abandoned when the chunk leaves the
  interest set.
- **Persistent resources:** pools or render-graph transients; no allocator per terrain cell.
- **Aprons:** derive width from declared neighbourhood/transport radius and crop only at publish.
- **Seam ownership:** shared border samples have one deterministic owner or identical evaluation.
- **Determinism:** thread count and completion order cannot alter persistent terrain.
- **Budgeting:** classify nodes T0–T3; checkpoint T2 work and never hide T3 in a frame task.
- **State overlay:** gameplay deformation, construction and save-state deltas sit above regenerated
  procedural truth and are versioned separately.
- **Publish barrier:** collision, render mesh, materials, water and scatter switch together; avoid
  one-frame disagreement between surfaces.

If runtime hydrology is required, declare the hydrological domain: loaded watershed, generation
region, planet face or coarse global graph. Persist boundary inflow/outflow and drainage area so
chunks do not invent isolated rivers.

The extreme of the runtime mode — an infinite, lazily-streamed **voxel** world that generates each
chunk from `(seed, coord)` with **no** global process at all (the Minecraft-style paradigm) — takes
the opposite bargain: it drops drainage and process history entirely and buys plausibility back with
local noise, splines and per-block density. Its full assembly, and the ledger of which core doctrines
it suspends, is `references/24-voxel-streaming-generation.md`. When a brief wants *both* an infinite
voxel world *and* real drainage, that is the **hybrid** pipeline below, not the pure per-chunk mode.

## Hybrid pipeline

The standard advanced architecture separates **process history** from **local expression**:

**Cook or asynchronously build globally:**

- macro elevation/uplift and lithology
- depression policy, flow graph, drainage area and channel skeleton
- stream-power equilibrium or other geological-timescale erosion
- climate/biome fields and stable water bodies
- coarse material, LOD and validation fields

**Generate or refine at runtime:**

- scale-free noise/warp below the baked band limit
- bounded thermal/detail erosion that cannot move global drainage
- local material breakup, decals and wetness/snow state
- deterministic scatter and biome instances
- mesh/normal generation and clipmap/chunk publication

The frequency split is explicit. Runtime detail amplitude must not reverse coarse drainage,
submerge ridges, move coastlines or invalidate baked analysis. Recompute local derivatives after
detail, but preserve global `A`, channel IDs and basin topology unless the product intentionally
supports dynamic geomorphology.

## Implementation milestones

1. **Contracts and tests:** field types, units, seed, boundaries, synthetic inputs, cache/version
   scheme (`08`, `09`, `14`).
2. **Composable scalar core:** arrays/fields, operators, noise, curves, filters and CPU truth.
3. **Hydrological backbone:** depression handling, routing, accumulation, lake/sea policy; prove
   connectivity before erosion.
4. **Terrain processes:** stream power, local hydraulic, thermal/diffusion; prove stability,
   conservation and resolution consistency.
5. **Analysis and appearance:** derivatives, masks, layers, materials, scatter and output maps.
6. **Offline product path:** deterministic full graph, cache, chunk/LOD export and reproducibility
   manifest.
7. **Engine-native runtime:** jobs, GPU passes, resource pools, cancellation, aprons, publication
   and streaming.
8. **Hybrid/global integration:** baked fields consumed by runtime detail without topology drift.
9. **Advanced regimes:** geology, climate, glacier/coast/desert/lava/planetary families selected by
   product needs.

Do not optimise milestone 2 into GPU-only code before milestone 4's scalar oracles pass.

## Acceptance gates

**Algorithm gate**

- Every production node has a provenance tier and pre-grounding status (`00`, `22`).
- Fields, units, boundaries, precision, locality, determinism and resolution policy are explicit.
- The family-specific `09` oracle passes; visual plausibility is not sufficient.

**Offline gate**

- Same graph/seed produces bit-identical or tolerance-declared assets.
- GLOBAL hydrology is connected; monolithic/tiled differences match declared theory.
- Export quantises once, after analysis; LOD and chunk seams pass.
- Cook manifest can reproduce every shipped terrain asset.

**Runtime gate**

- Chunk order, thread count and CPU/GPU path do not change persistent terrain beyond tolerance.
- Worst-case time, memory and transient-resource budgets are measured per tier.
- Cancellation leaks no resources and publishes no partial terrain.
- Cross-chunk height, normal, water, material and drainage contracts pass.
- Save-state overlays survive regeneration and graph-version migration.

**Hybrid gate**

- Runtime detail preserves baked basin/channel/coast topology.
- Coarse-to-fine spectral bands do not overlap visibly or leave a gap.
- Local analysis/materials agree with refined geometry while global fields retain identity.

## Agent delivery contract

When asked to implement a generator, the agent must:

1. Select offline, runtime or hybrid mode from product constraints; do not leave this undecided.
2. Instantiate the minimum node-library rows needed by scope and name deliberate omissions.
3. Produce target-language code and engine integration, not a list of papers or libraries.
4. Use the internal algorithm chapter and `22` grounding decision; do not redirect upstream
   research to the user.
5. Include scalar truth/oracles before or beside optimized CPU/GPU paths.
6. State world units, locality, boundaries, seed, precision, cache/version and runtime budget for
   every implemented node.
7. End with the acceptance evidence appropriate to the delivery mode.
