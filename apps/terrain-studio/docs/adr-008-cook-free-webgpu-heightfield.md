# ADR 008 - Cook-free WebGPU heightfield for Extreme Detail

**Status:** accepted
**Date:** 2026-08-01

## Context

Sprint 9 defines the authoritative metre-space world, `cellSizeM`, bounded evaluation regions,
streaming hierarchy, and Float64-to-camera-relative-Float32 precision contract. It makes a 100 km
world with 0.5 m authored vertex spacing feasible as bounded field work, but it does not choose a
renderer that displays that source resolution near the camera without materializing a dense world
mesh.

Terrain Studio is an interactive authoring tool. Height and auxiliary fields can change while a
document is open, and the authoritative collision/gameplay representation is already a heightfield.
A representation that converts those fields into a second persistent geometry hierarchy would
duplicate authority and turn every edit into a geometry rebuild problem. The renderer therefore
needs a field-native representation whose topology is reusable and whose local derived data can be
invalidated by page.

The current GPU path in `src/core/gpu.js` is WebGL2. `GPU.init()` requires an existing
`WebGL2RenderingContext` and `EXT_color_buffer_float`; `EXT_float_blend` is optional. Render targets
are square `RGBA32F` textures cached by key and resolution with no eviction. There is no WebGPU
probe, streamed runtime height pyramid, geometry clipmap, patch scene, HiZ traversal, or indirect
terrain submission path.

The selected Extreme tier must operate within standard WebGPU rather than native D3D12/Vulkan
assumptions:

- an application can reliably test `navigator.gpu`, adapter acquisition, reported features and
  limits, and success of `requestDevice({requiredFeatures, requiredLimits})`;
- browsers may privacy-tier reported limits rather than expose exact hardware maxima;
- the web platform does not expose a reliable VRAM quantity or portable proof that the returned
  implementation is a physical GPU rather than SwiftShader/software;
- `powerPreference` is a hint, not a device-class guarantee; fallback-adapter reporting is not a
  portable admission gate;
- standard WebGPU provides compute and `drawIndexedIndirect()` for one fixed argument record, but
  does not guarantee mesh shaders, tessellation shaders, work graphs, bindless descriptors, or a
  draw-indirect-count operation.

Capability language must report only what the APIs prove. "No GPU" is false when an adapter is
hidden, rejected, software-backed, privacy-limited, or lacks one required capability. The blocking
wording is **No supported graphics capability**. A headless SwiftShader adapter is valid when the
same required limits and device request pass.

## Decision drivers

- Display authored 0.5 m height samples near the camera without allocating or storing a 100 km
  dense mesh.
- Keep height and registered auxiliary fields as the one persistent terrain representation.
- Apply edits by invalidating bounded field pages and reproducible runtime caches, with no recook.
- Keep geometry memory, vertex count, page residency, feedback, and submission bounded independently
  of world area.
- Prevent cracks structurally across rings, LOD patches, and page misses.
- Permit GPU-selected visibility over one profile-authored fixed clipmap topology using portable WebGPU.
- Keep Standard available on WebGL2 + `EXT_color_buffer_float` over the same field hierarchy.
- Preserve deterministic/headless validation, Float64 authority, Sprint 9 GLOBAL scheduling, and
  authoritative heightfield collision/gameplay.
- Export only height, auxiliary, and domain/region pages through the Sprint 6/Sprint 9 manifests.

## Considered options

### A. Monolithic dense grid

Convert the complete 100 km at 0.5 m source into one grid/mesh and upload or draw it directly. The
source has `200001` vertex posts per axis and about 40.0 billion samples before explicit mesh
connectivity, intermediates, auxiliary maps, or material data. Browser memory, texture dimensions,
typed-array/index limits, and submission cost fail by orders of magnitude. Rejected.

### B. Cooked cluster/Nanite-family virtualized terrain

Convert bounded heightfield regions into clusters/meshlets, build a simplification hierarchy, and
store canonical geometry pages with coarse roots. This is appropriate for static authored meshes,
especially overhangs and sculpted topology, but Terrain Studio's terrain remains an editable
heightfield. The option is rejected because:

- every height edit invalidates geometry extraction, adjacency, simplification, bounds, error, and
  packed-page products, requiring a recook before the edit is honestly visible;
- the cluster hierarchy duplicates the authoritative heightfield as a second persistent terrain
  representation with independent versioning, storage, import/export, and seam failure modes;
- 0.5 m regular-grid connectivity is implicit in the field, while cluster pages spend bytes storing
  geometry and indices that a shared runtime grid reconstructs directly;
- deterministic geometry cooking, DAG validation, canonical page packing, and rebuild cancellation
  add substantial implementation and evidence cost without adding topology the source can express;
- WebGPU lacks several native control-plane features often associated with Nanite-family pipelines,
  so a browser implementation would incur that representation cost without establishing parity.

This decision does not prohibit separately authored cliff/cave meshes under a future hybrid ADR. It
rejects cooked geometry as the representation of the Sprint 9 authoritative heightfield.

### C. Cook-free streamed clipmap/heightfield GPU renderer - selected

Stream a constant-sample-count pyramid of height and auxiliary-map pages. Derive height mips,
min/max/error pyramids, normals, page tables, clipmap textures, patch records, and GPU buffers at
runtime under bounded worker/compute budgets. Render nested camera-centred geometry clipmap rings by
vertex pulling from those pages, with toroidal updates and an explicit transition morph plus
degenerate/stitch contract. Ring/patch topology is profile-authored and fixed; page error affects
residency priority and quality labels only. Edits invalidate affected field pages, apron dependants,
and the registered ancestor chain plus derived runtime caches.

WebGPU compute produces page requests, selects visible patch/ring records, performs frustum and
two-phase HiZ culling at patch granularity, deterministically compacts one instance buffer by fixed
pass/material/index-pattern buckets, and writes one `drawIndexedIndirect` record per
bounded bucket over shared grid topology.
Selected.

### D. Standard WebGL2 streamed heightfield fallback

Consume the same height/auxiliary pyramid and runtime-derived min/max/error/normal data. Instantiate
bounded fixed-topology geometry-clipmap rings on CPU and draw shared grids through the existing
WebGL2 float renderer. This keeps one data representation and provides the compatibility tier when WebGPU does
not pass. Retained as Standard, not selected as Extreme's control plane.

## Decision

### Representation and cache boundary

The persistent render input is the Sprint 9 field hierarchy:

- vertex-posted height pages at authored spacing, including 0.5 m pages;
- registered auxiliary-map pages with declared units, lattice, resolution, and apron;
- profile-authored power-of-two core-cell dimensions, `coreCells+1` vertex samples, and
  `coreCells` shared-edge stride per axis;
- explicit child-to-parent registration under one lattice/posting basis and a named deterministic
  2x downsample filter, with pinned renderable height roots;
- conservative `minHeightM`, `maxHeightM`, and `geometricErrorM` field-page headers persisted under
  the page content hash;
- canonical page identity `(field, level, x, y, surfaceVersion)` under the Sprint 6/Sprint 9
  manifest contract.

No explicit dense terrain mesh, cluster, meshlet, geometry page, or simplification DAG is stored.
Runtime may create height mips, conservative min/max and geometric-error pyramids, display normals,
page tables, toroidal clipmap textures, shared index buffers, fixed patch records, visibility state,
and indirect arguments. These are **derived runtime caches**: bounded, reproducible, disposable,
byte-accounted, and excluded from export.

An edit creates a new monotonic `surfaceVersion`. A bounded local edit invalidates intersecting leaf
cores, every leaf whose declared apron reads them, and the registered ancestor chain plus derived
caches. Domain or GLOBAL edits broadly invalidate their affected hierarchy. Worker/compute
generation and upload carry `surfaceVersion`; late or cancelled results cannot commit. The old
complete front remains renderable, every miss uses the finest resident ancestor, and replacement
promotes atomically only after required roots/pages/aprons/caches exist.
There is no offline or amortized geometry build, geometry cooker, geometry-page packer, recook, or
rebuild DAG.

### Fixed-topology runtime geometry clipmaps

The initial reliable Extreme base is nested square grid rings centred on the camera. Successive
rings are 2x coarser and cover wider annuli. Ring dimensions, levels, shared topology, and maximum
patch count are profile-bounded, giving fixed geometry memory and vertex count independent of world
area. Vertices derive grid coordinates from vertex ID or a tiny shared index topology and pull
height from the page/clipmap table; no world-sized vertex buffer exists.

Camera motion updates clipmap textures toroidally. When the delta is smaller than the logical texture
span on both axes and overlap exists, only newly exposed strips and page-dirty rectangles upload. If
either absolute delta is at least the span, the level is invalidated and its complete logical texture
is refilled as budgeted strips over subsequent frames while the pinned ancestor renders. CPU texture
scrolling/copy and unbudgeted same-frame full refill are forbidden; a necessary budgeted refill is
valid. The finest ring maps resident source samples at texel centres, so authored 0.5 m spacing is
visible near the camera rather than downsampled away.

The outer band of each ring morphs positions and height-derived normals to the next coarser level.
The factor reaches exactly 1.0 at the boundary. Degenerate/stitch index topology removes
T-junctions where densities meet. Main, depth, shadow, and velocity passes consume the same patch
selection and morph values. Missing detail samples the finest resident ancestor; quality may become
coarse but coverage cannot hole or stall.

Ring levels, patch coordinates, transition bands, and index-pattern buckets are selected solely by
the profile-authored geometry-clipmap topology. Conservative page error in metres drives request
priority and the displayed quality label only; it does not walk a quadtree, add/remove patches, or
alter topology. Main, depth, shadow, and velocity use the same selection and morph values.

### Portable WebGPU control plane

The persistent WebGPU patch scene stores fixed-size records for resident runtime patches: stable ID,
ring/level, page indirection, camera-relative origin, extent, min/max/error, displacement inflation,
morph range, index-pattern ID, and material/pass bucket. CPU patches streaming/edit deltas at frame
boundaries; it does not rebuild a world-sized visible list or submit per resident patch.

Runtime follows this bounded sequence:

1. Compute derives and deduplicates page wants from predicted fixed-ring coverage. Conservative page
  error changes request priority and quality labels only.
2. Compute tests the profile-authored patch/ring set against the frustum without changing topology.
3. Two-phase HiZ draws prior-visible patches, builds the pyramid under the active depth convention,
   and retests candidates. Camera cuts and teleports clear visibility history.
4. Deterministic prefix/ordered compaction writes visible records into one bounded instance buffer,
  grouped by fixed `(pass, material, indexPattern)` buckets. Compute writes one five-word
  `drawIndexedIndirect` argument per bounded bucket over shared static indices, with
  `instanceCount=visiblePatchCount` and `firstInstance=0`. The shader addresses
  `compacted[bucketBase + builtin(instance_index)]`; bucket base is fixed draw metadata or a binding
  offset. Overflow counters fail the gate while selecting a coarser complete fallback.
5. Main, depth, shadow, and velocity consumers share the selected records and morph state.

JavaScript encodes exactly one indirect draw per fixed bucket, so command encoding is
`O(profile bucket count)`, never `O(visible patches)`. `indirect-first-instance` is not required.
No mesh shader, tessellation shader, work graph, bindless descriptor model, indirect-count
operation, cluster data, transient
geometry compaction, or native API extension is required.

This is explicitly **not a Nanite-like representation and does not claim Nanite parity**. The
quality target is fidelity to the finest resident source level exposed by the fixed clipmap, with
sourced material/procedural detail below the cell scale.

### Standard WebGL2 fallback

Standard uses the same field pages and derived runtime-cache definitions. CPU selects the bounded
fixed-topology clipmap rings and the existing WebGL2 float renderer draws shared grids. Standard requires a
WebGL2 context plus `EXT_color_buffer_float`; `EXT_float_blend` remains optional unless a separate
feature requires it. Standard never consumes an exported geometry format and remains image-
comparable with the WebGPU selection reference.

### Capability tiers and blocking startup

Each launch performs a fresh probe before any document/resource allocation:

1. **Extreme:** require every `ExtremeCapability/1` step below.
2. **Standard:** otherwise require WebGL2 plus `EXT_color_buffer_float`, matching the current gate.
3. **Unsupported:** if neither passes, block interactive Studio with **Retry**, **Copy diagnostics**,
   and **Help** under the exact message/title **No supported graphics capability**.

`ExtremeCapability/1` is sourced from the WebGPU Specification's guaranteed default limits and uses
no optional feature:

```text
isSecureContext === true
navigator.gpu exists
requestAdapter() returns non-null
requiredFeatures = []
requiredLimits = {
  maxTextureDimension2D:             8192,
  maxBufferSize:                     268435456,
  maxStorageBufferBindingSize:       134217728,
  maxComputeWorkgroupsPerDimension:  65535,
  maxComputeInvocationsPerWorkgroup: 256,
  maxStorageBuffersPerShaderStage:   8
}
requestDevice({ requiredFeatures: [], requiredLimits }) returns non-null
validation smoke passes:
  r32float COPY_DST | TEXTURE_BINDING (unfiltered textureLoad height sampling)
  depth24plus RENDER_ATTACHMENT
  preferred canvas format RENDER_ATTACHMENT
```

Algorithms partition work to those minima; admission is not raised to accommodate an oversized
buffer, dispatch, texture, or binding design. `rgba16float` and `rgba32float` are not profile
requirements. Any later use must validate the exact core-supported usage and cannot silently become
admission. Timestamp queries are optional diagnostics only: their presence is never requested and
their absence never rejects Extreme. Validation/uncaptured errors reject admission; if `device.lost`
resolves for a reason other than intentional destruction, Extreme is revoked and the reason reported.

Retry reruns the complete probe. Copy diagnostics separately reports `insecure-context`,
`api-absent`, `adapter-null`, `limit-below-profile`, `device-reject`, `format-validation`, and
`device-lost`, plus requested versus reported features/limits, without inventing VRAM,
physical-device class, or vendor performance. Help opens support guidance. A persisted tier is a
preference only and cannot override a failed current probe.

Reliable eligibility facts are API presence, adapter presence, reported feature membership,
reported limit values, and device-request success/failure. Reported limits are admission facts, not
physical maxima. Adapter names, power hints, fallback/software flags, and user-agent strings are
diagnostic hints, not gates. The browser cannot reliably identify physical GPU versus SwiftShader or
report VRAM. Runtime uses authored byte budgets and measured residency instead.

### Scaled feedback, eviction, byte plateau, and precision

Page requests enter a bounded GPU feedback buffer copied through an N-deep asynchronous readback
ring. CPU consumes it frames later, deduplicates/prioritizes fixed-ring wants by distance,
prediction, and conservative page error, and
schedules IO/generation/decode/cache-regeneration/upload under byte/time budgets. Nothing waits for
readback.

One authored byte budget covers source height/auxiliary pages, pinned roots, derived runtime caches,
page tables, clipmap textures, persistent patch/visibility records, indirect buffers, upload/readback
rings, in-flight work, and headroom. Priority-aware LRU evicts only unreferenced entries and must be
exercised with feedback volume above pool capacity until measured bytes plateau within the authored
profile. The page-lifecycle contract above owns pinned roots, cancellation, ancestor fallback, and
atomic version promotion.

CPU owns world/page origins and camera in Float64. It subtracts camera from patch origin in Float64
and uploads camera-relative Float32 values. GPU buffers do not use 100 km absolute near-field
positions.

### Material detail and gameplay authority

VT/page-table material data, macro/detail normals, stochastic anti-tiling, and bounded near-field
parallax provide visual frequencies below heightfield cell scale. Optional displacement requires an
authored/procedural source with units, deterministic identity, frequency band, and maximum
displacement included in patch/frustum/HiZ bounds. Dynamic global weather and season state stays
outside cached VT pages.

Visual displacement is evaluated identically in main, depth, shadow, and velocity. Object seating,
picking, water contact, vegetation placement, and decals either sample authoritative height or
explicitly opt into the same versioned visual-displacement contract.

The renderer does not invent source geometry between 0.5 m posts. Collision, navigation, gameplay,
and authoritative queries remain on the heightfield. Cosmetic displacement does not change them
unless a later ADR explicitly promotes and versions it as authoritative height data.

### CPU/worker and GPU division

- **CPU/workers own** field-page IO/generation/decode, deterministic runtime-cache reference,
  Float64 authority, cancellation, residency policy, manifest validation, and Sprint 9 GLOBAL
  science scheduling.
- **WebGPU owns** proven runtime-cache kernels, page-request production, fixed-ring visibility,
  frustum/HiZ, bucketed ordered instance compaction, instanced indirect arguments, and drawing.
- **WebGL2 owns Standard rendering** with CPU-instantiated fixed-topology clipmap rings over the same field pages.

No owner creates exportable geometry artifacts. GLOBAL drainage, climate, and other science do not
become renderer page jobs; their completed Sprint 9 fields are renderer inputs.

### Evidence, budgets, and export

Platform profiles author field/cache pool bytes, patch/bucket capacities, upload/readback limits,
cache-regeneration work, and frame/pass p95/p99 budgets before the implementation gate. Every
non-empty measured result must be `<=` its authored budget; passing thresholds are not discovered
from the implementation under test and no device-class target is guessed.

The deterministic software/control path emits Float32 linear forward depth
`clamp((zView-near)/(far-near),0,1)` and Uint32 patch IDs and must be byte-identical across runs. For
GPU captures over `N>0` covered pixels, `patchIdMismatchCount=0` exactly. A depth pixel is bad only
when its difference exceeds `max(ulp32(gpuDepth),ulp32(referenceDepth))`; the asserted
`badDepthPixelCount/N` bound is frozen by S10.R0 between measured wrong-depth and passing controls,
while the stale-ID mutation must fail the exact ID gate. The analytic precision gate compares camera-relative Float32 against the Float64 RTE
expression and requires maximum component error `<= 0.001 m` on the named 100 km fixture.

Anti-tiling uses the maximum normalized 2D autocorrelation peak at named non-zero base-period lags.
S10.R0 measures `PeriodicTileControl/1` and `DecorrelatedControl/1`, then freezes the required peak
reduction strictly between those controls. Until both parity and anti-tiling bounds are recorded,
Sprint 10 is grounded but not technically refined or Ready.

Required evidence is non-vacuous:

- an artifact scan and invocation spy assert zero geometry files/pages and zero geometry-cooker calls;
- editing one height page changes visible terrain after bounded runtime-cache regeneration while
  unrelated cache hashes remain unchanged;
- finest-ring samples match source posts at texel centres;
- generated constant, analytic sine, and knife-edge ridge controls cover sampling, bounds, LOD, and
  normal behavior;
- full-range motion sweeps assert transition morph, stitch/degenerate continuity, zero crack pixels,
  and exact toroidal strip-update coverage;
- forced page misses draw ancestors without holes; page/request/patch order is deterministic;
- deterministic control buffers are byte-identical; CPU/WebGL2 and WebGPU selection plus
  culling-off/on captures satisfy the frozen patch-ID/one-ULP mismatch formula; HiZ mutations are red;
- cancellation rejects stale completions, real page traffic reaches a measured memory plateau, and
  a 100 km RTE fixture matches the stable near-origin result;
- the built PWA passes desktop/mobile evidence and the full capability matrix.

Export remains height, auxiliary, and domain/region pages plus persisted per-page conservative
min/max/error headers through the versioned Sprint 6/Sprint 9 manifest. Runtime aggregate
min/max/error pyramid/cache representations, height mips, normals, clipmap textures, page tables, patch records,
shared indices, visibility state, and indirect buffers regenerate after import. Cluster meshes,
meshlets, geometry pages, and simplification DAGs are forbidden package products. Import validates
the complete field dependency graph before document creation and rejects missing, mixed, unsafe, or
partial packages atomically.

## Consequences and gates

- The renderer remains native to the editable authoritative heightfield; there is no recook latency,
  persistent geometry duplication, or geometry-artifact version boundary.
- Geometry clipmaps provide predictable fixed memory and one stable runtime topology. Page error
  prioritizes residency and labels quality; it never changes geometry topology.
- Page misses may temporarily show a coarser labelled quality level, but pinned ancestors preserve
  complete coverage and interactivity.
- Extreme introduces a second renderer and GPU-selection evidence cost; Standard remains the
  compatibility and CPU-reference path over identical field data.
- Capability probing can prove API requirements, not physical GPU class or VRAM. Software adapters
  are accepted when requirements pass and constrained by measured budgets.
- Bucketed indirect submission uses exactly one instanced draw per fixed bucket, including a
  zero-instance draw for an empty bucket, with
  `firstInstance=0`; CPU encoding is bounded by bucket count and requires neither indirect count nor
  `indirect-first-instance`.
- Export ownership remains with Sprint 6/Sprint 9 and cannot grow a hidden geometry branch.

Required gates are Sprint 10's allocation-free capability matrix; zero geometry artifacts/cooker
invocations; deterministic height-page ancestry and runtime-cache generation; page-edit visible
update; source-sample parity; constant/sine/ridge controls; fixed ring/vertex counts; exact toroidal
updates/refills; crack/morph/stitch sweeps; ancestor fallback; calibrated CPU/GPU selection and
culling equivalence; HiZ mutations; bounded bucket overflow; cancellation; measured residency
plateau; analytic 100 km precision; calibrated sourced sub-cell detail; built-PWA evidence; and height/aux/domain-only manifest
round-trip.

## Grounding sources

- Installed Terrain Renderer `references/01-heightfield-lod.md`: clipmap rings, fixed geometry
  memory, toroidal updates, transition morph/degenerate stitching, vertex pulling, runtime edits,
  and source-centred height sampling. This ADR selects only the fixed-topology clipmap branch.
- Installed Terrain Renderer `references/06-tiled-streaming.md`: constant-size field-page pyramid,
  complete renderable front, ancestor fallback, cancellation, byte/upload budgets, eviction, and
  separate collision authority.
- Installed Terrain Renderer `references/07-materials-virtual-texturing.md`: page-table feedback,
  fallback mips, page borders/virtual gradients, anti-tiling, sourced visual detail, and bounded
  cache invalidation.
- Installed Terrain Renderer `references/08-gpu-driven-culling.md`: persistent patch scene,
  level-by-level GPU LOD, frustum/two-phase HiZ, ordered compaction, indirect submission, and async
  feedback.
- Installed Terrain Renderer `references/09-planetary-precision.md`: Float64 CPU authority and
  camera-relative Float32 rendering.
- Installed Terrain Renderer `references/11-verification-failures.md`: analytic controls,
  source/parity/crack/morph/culling checks, deterministic request order, temporal replay, memory
  plateau, and asserted p95/p99 evidence.
- Installed Terrain Renderer `references/16-tool-viewports.md`: field-contract WYSIWYG, dirty-region
  upload, asynchronous refinement, shared-grid preview, and built/export parity.
- Current `src/core/gpu.js`: exact WebGL2/`EXT_color_buffer_float` gate, optional float blending,
  current target cache, and absence of WebGPU/device-memory classification.
- WebGPU/MDN API documentation: `requestAdapter()`, adapter limits and required device limits,
  `drawIndexedIndirect()`, privacy-tiered limits, and the non-portability of physical-GPU/software
  and VRAM classification.
