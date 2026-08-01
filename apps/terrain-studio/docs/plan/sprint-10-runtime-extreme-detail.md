# Sprint 10 - Cook-free runtime heightfield / Extreme Detail `[K]+[E]`

**Planning status:** grounded; technical refinement and Ready are BLOCKED by the measured S10.R0
calibration below. **Implementation status:** NOT STARTED.

**Goal.** Add an opt-in Extreme rendering tier that displays the authored 0.5 m source spacing near
the camera from streamed height and auxiliary-map pages, without storing or cooking explicit dense
terrain meshes. Fixed-topology runtime geometry clipmaps provide the reliable base. WebGPU adds
GPU-selected patch/ring visibility, HiZ culling, page requests, and bounded bucketed indirect
submission. Standard remains the WebGL2 renderer over the same height pyramid.

**Depends on:** S10.1 capability probing is independent. The height-page pyramid starts after the
Sprint 9 domain and bounded-evaluation contracts in `MC-S21`/`MC-S22`. Runtime clipmaps require
renderable height ancestors and runtime-derived cache generation. WebGPU selection requires a
passing capability probe plus the height-page/clipmap contracts. Export integration waits for the
Sprint 6 and Sprint 9 manifest owners in `MC-S23`.

**Architecture gate:** [ADR 008](../adr-008-cook-free-webgpu-heightfield.md) is accepted and
normative. It selects a cook-free streamed heightfield with fixed-topology runtime geometry clipmaps
for Extreme, keeps WebGL2 CPU-selected clipmap rings as Standard, and rejects both a monolithic dense grid
and cooked cluster/Nanite-family terrain.

**Scope boundary.** The source is Sprint 9's authoritative vertex-posted heightfield. At
`cellSizeM = 0.5`, adjacent authored vertex posts are 0.5 m apart. Height, auxiliary maps, and their
multiresolution field pages are stored or generated; explicit dense mesh, cluster, meshlet, and
simplification-DAG artifacts are not. Height mips, min/max/error pyramids, normals, page tables, and
GPU buffers created from streamed fields are **derived runtime caches**, not a cook. An edit dirties
only affected source pages, dependent auxiliary pages, and derived runtime caches. It never starts a
geometry recook or rebuild DAG.

Sub-cell visual detail comes from sourced material/procedural data through VT, normal/parallax, or
bounded optional displacement. It does not change collision, navigation, or gameplay unless a later
authority decision explicitly promotes it. The authoritative heightfield remains the collision and
gameplay surface.

---

## Measured starting point

- `src/core/gpu.js::GPU.init()` currently accepts only an existing `WebGL2RenderingContext` with
  `EXT_color_buffer_float`; `EXT_float_blend` is optional. It does not probe WebGPU, adapter limits,
  device creation, VRAM, or physical-versus-software implementation.
- Current render targets are square `RGBA32F` textures cached by key and resolution with no
  eviction. The current app has no streamed height-page pyramid, runtime geometry clipmap, patch
  scene, HiZ cut, or indirect terrain submission path.
- WebGPU reliably exposes whether `navigator.gpu` exists, whether `requestAdapter()` returns an
  adapter, reported features/limits, and whether `requestDevice({requiredFeatures, requiredLimits})`
  succeeds. Reported limits may be privacy-tiered rather than physical maxima. The web platform does
  not expose a reliable VRAM quantity or a portable physical-GPU-versus-SwiftShader verdict.
- Standard WebGPU exposes compute and `drawIndexedIndirect()` with one five-word argument record. It
  does not guarantee mesh shaders, tessellation shaders, work graphs, bindless descriptors, or a
  draw-indirect-count operation.

These are constraints on the design, not implementation claims. Headless SwiftShader is a valid
test/runtime adapter when the same required capabilities pass.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---:|---|
| S10.1 | Capability tiers + blocking startup modal | `[E]` | 5 | current probe only; Retry, Copy diagnostics, Help |
| S10.2 | Versioned streamed height pages + runtime derived caches | `[K]` | 8 | page ancestry; root pinning; atomic promotion/cancellation; caches |
| S10.3 | Cook-free fixed-topology geometry clipmaps | `[K]` | 13 | nested rings, vertex pulling, toroidal refill, morph + stitch contract |
| S10.4 | WebGPU patch culling/HiZ/compacted instancing | `[K]` | 13 | GPU requests/selection, fixed topology, one indirect draw per fixed bucket |
| S10.5 | Scaled async feedback, eviction, byte plateau, RTE precision | `[E]` | 8 | feedback scale, eviction, byte budget, Float64 authority |
| S10.6 | Sub-cell visual detail | `[K]` | 5 | VT, normal/parallax, bounded optional displacement |
| S10.7 | Evidence/export integration | `[E]` | 8 | controls, built PWA, capability matrix, field-page manifests |
| | **Sprint 10 total** | | **60** | `5+8+13+13+8+5+8` |

---

## Technical refinement

### Capability and startup contract

The startup probe runs on every launch before clean/default/template document creation and before
graph, field, worker, WebGL/WebGPU terrain resource, or emitter staging allocation. A persisted tier
is only a preference among currently passing tiers; it never overrides the current probe.

`ExtremeCapability/1` is the exact reliable admission profile. It is sourced from the WebGPU
Specification's guaranteed default limits, not from a guessed device class:

```text
secureContext: true
api: navigator.gpu exists
adapter: await navigator.gpu.requestAdapter() returns non-null
requiredFeatures: []
requiredLimits:
  maxTextureDimension2D:             8192
  maxBufferSize:                     268435456
  maxStorageBufferBindingSize:       134217728
  maxComputeWorkgroupsPerDimension:  65535
  maxComputeInvocationsPerWorkgroup: 256
  maxStorageBuffersPerShaderStage:   8
device: requestDevice({ requiredFeatures: [], requiredLimits }) returns non-null
formats/usages validated under a WebGPU validation error scope:
  r32float:       COPY_DST | TEXTURE_BINDING (unfiltered textureLoad height sampling)
  depth24plus:    RENDER_ATTACHMENT
  canvas format:  navigator.gpu.getPreferredCanvasFormat() with RENDER_ATTACHMENT
```

The selected algorithms must partition buffers, dispatches, textures, and storage bindings to fit
those minima. They may not raise admission limits later to recover an oversized design.
`rgba16float` and `rgba32float` are not required by this profile; a later use must prove its exact
core format usages under validation and may not silently become an admission dependency. Timestamp
queries are optional diagnostics when exposed, are never requested by admission, and never select a
tier. A validation error or uncaptured error during the smoke resources/pipelines rejects admission.
If `device.lost` resolves during startup or later for any reason other than intentional destruction,
Extreme eligibility is revoked and the distinct loss reason is reported.

| Tier | Required current probe | Result |
|---|---|---|
| **Extreme** | secure context plus every `ExtremeCapability/1` step and format usage above | WebGPU runtime-heightfield path eligible |
| **Standard** | WebGL2 context plus `EXT_color_buffer_float` | existing float renderer with CPU-selected clipmap rings eligible |
| **Unsupported** | neither tier passes | block interactive Studio |

The unsupported modal says **No supported graphics capability**. It never says "no GPU." Actions are
**Retry** (rerun the complete current probe), **Copy diagnostics** (copy non-secret browser/API,
feature, limit, and failure-stage facts), and **Help** (open support guidance). The modal remains
blocking until a current probe passes. Diagnostics distinguish `insecure-context`, `api-absent`,
`adapter-null`, `limit-below-profile`, `device-reject`, `format-validation`, `device-lost`, missing
WebGL2, and missing `EXT_color_buffer_float`; none is collapsed into another stage.

Adapter/vendor strings, `powerPreference`, fallback-adapter hints, and reported limits cannot prove a
physical GPU, exclude SwiftShader/software, identify a device class, or reveal VRAM. Capability facts
decide eligibility; measured profile behavior decides budgets. Headless SwiftShader remains a valid
endpoint when the required limits and device request pass.

### Streamed height-page pyramid and derived runtime caches

The persistent representation is the Sprint 9 field hierarchy, not geometry. Each profile fixes
`coreCellsX` and `coreCellsY` as positive powers of two. A page has `coreCells+1` vertex samples per
axis; adjacent pages advance by the shared-edge stride `coreCells`, so their terminal/start posts
are one canonical bit-identical sample. Page identity is
`(field, level, x, y, surfaceVersion)`. Registered consumers declare apron support in samples; the
stored/evaluated rectangle is the core expanded by the maximum transitive declared apron, while
identity and promotion remain core-based.

Every child registers explicitly with one parent under the same posting and lattice basis. The
parent origin is aligned to the 2x child-cell grid, and its posts are generated by the profile's
named deterministic 2x downsample filter over the complete registered child footprint, including
canonical shared edges. Missing or mixed-version children cannot promote a parent. Each completed
field page persists conservative `minHeightM`, `maxHeightM`, and `geometricErrorM` headers as
field-page metadata covered by its content hash. The error pyramid may prioritize residency and
label current quality; it never changes clipmap topology or selects extra geometry.

Minimum renderability belongs here: each surface version pins a complete root, every miss resolves
to the finest resident ancestor, and the old complete renderable front remains active until the new
version's required roots/pages/aprons/derived caches promote atomically. The finest available height
pages retain authored 0.5 m vertex spacing.

Runtime derives only what drawing and selection need:

- height mips using the declared sample/edge convention;
- min/max bounds and conservative geometric-error values in metres;
- display normals and other height-derived shading maps from page plus apron;
- residency/page tables, toroidal clipmap textures, patch records, and GPU buffers.

These products are **derived runtime caches**. They are reproducible from field pages, disposable,
byte-accounted, and never exported as source artifacts. CPU/workers are the deterministic reference
path; WebGPU compute may regenerate a cache when equivalent output is asserted. Same source pages and
cache profile produce the same ordered page metadata independent of request completion order.

An edit creates a new monotonic `surfaceVersion`. A bounded local edit invalidates intersecting leaf
cores, every leaf whose apron reads those cores, and the complete registered ancestor chain plus
their derived caches. Domain or GLOBAL-field edits invalidate the affected field hierarchy broadly;
they are never mislabelled local. Every generation/decode/cache/upload job carries
`surfaceVersion`, supports cancellation, and cannot commit after supersession. The old complete
front remains renderable until one atomic version promotion. No mesh extraction, simplification,
geometry page packing, or rebuild DAG exists.

### Cook-free fixed-topology runtime geometry clipmaps

The initial reliable Extreme geometry is a finite set of nested, camera-centered grid rings. Every
ring uses a shared immutable index topology or vertex-ID-derived grid; the vertex shader pulls height
from resident field pages through the clipmap/page table. There is no per-world vertex buffer and no
explicit dense terrain mesh stored on disk, in a package, or in memory.

- Each successive ring samples a 2x coarser height level and covers a wider annulus. Ring dimensions,
  levels, shared indices, and maximum patch count are profile-bounded, so geometry memory and vertex
  count do not grow with world area.
- Camera movement updates height/aux clipmap textures toroidally. When movement delta on both axes is
  smaller than the logical texture span and overlap exists, only newly exposed strips and dirtied
  rectangles upload. If either absolute delta is at least that span, the level is invalidated and
  its complete logical texture is refilled as budgeted strips over subsequent frames while the
  pinned ancestor renders. CPU texture scrolling/copy, unbudgeted same-frame full refill, and
  treating a necessary budgeted refill as an error are all forbidden.
- The innermost ring maps finest resident samples one-for-one at texel centres, making authored
  0.5 m source spacing visible near the camera when those pages are resident.
- The outer band of each ring morphs height and height-derived normals toward the next coarser level.
  Morph reaches exactly 1.0 at the handoff. Degenerate/stitch index topology removes T-junctions;
  morph and stitch results are shared by main, depth, shadow, and velocity passes.
- A coarse resident ancestor supplies every sample on a page miss. Refinement can sharpen after
  arrival, but missing data cannot open a hole or stall the frame.

Ring levels, patch coordinates, transition bands, and index-pattern buckets are selected solely by
the profile-authored geometry-clipmap topology. Runtime error metadata does not add/remove patches,
walk a quadtree, or alter LOD topology. Main, depth, shadow, and velocity use the same fixed
selection and morph data.

### WebGPU GPU-driven patch selection and draw contract

Extreme keeps persistent fixed-size records for resident clipmap patches: stable patch/page ID,
ring/level, Float64-derived camera-relative origin, extent, height-page indirection, min/max/error,
conservative displacement bounds, morph range, index-pattern ID, and material/pass bucket. CPU
uploads residency and edit deltas at frame boundaries; it does not construct a world-sized visible
list or submit one draw per resident patch.

The portable WebGPU path is:

1. Compute generates/deduplicates bounded page requests from predicted fixed-ring coverage. Error
  metadata affects request priority and quality labels only. Missing detail selects a resident
  ancestor immediately.
2. Compute evaluates the profile-authored patch/ring set for frustum visibility without changing
  topology.
3. Two-phase HiZ works at patch granularity: prior-visible patches establish depth, the active depth
   convention builds a conservative pyramid, and candidates are retested. Camera cuts/teleports clear
   visibility history.
4. A deterministic prefix/ordered compaction writes visible patch records into one bounded instance
  buffer, grouped by the fixed `(pass, material, indexPattern)` buckets. Compute writes one
  five-word `drawIndexedIndirect` record per bounded bucket with shared static index
  topology, `instanceCount = visiblePatchCount`, and `firstInstance = 0`. The shader resolves
  `compacted[bucketBase + builtin(instance_index)]`; `bucketBase` is fixed draw metadata/binding
  offset. JavaScript encodes exactly one indirect draw per fixed bucket, so CPU command encoding is
  `O(profile bucket count)`, never `O(visible patches)`. `indirect-first-instance` is not required.
5. Main, depth, shadow, and velocity consumers share one frame's patch selection and morph result.

Overflow increments asserted counters and falls back to coarser records rather than writing past a
buffer or dropping terrain. The path requires no mesh shader, tessellation shader, work graph,
bindless descriptor model, indirect-count operation, cluster data, or geometry compaction. It is not
a Nanite-like representation and does not claim Nanite parity. The quality target is fidelity to the
finest resident source level exposed by the fixed clipmap plus sourced material detail.

Standard WebGL2 consumes the same streamed height pyramid and derived min/max/error/normal caches.
CPU instantiates the same bounded fixed-topology clipmap rings and the existing float renderer draws shared grids. It
does not consume a different geometry format or require WebGPU-derived state.

### Scaled async feedback, eviction, byte plateau, and precision

- GPU page requests use a bounded feedback buffer copied through an N-deep asynchronous readback
  ring. CPU consumes requests frames later; rendering never waits on mapping/readback.
- CPU/workers deduplicate and prioritize fixed-ring requests using distance, prediction, and
  conservative page error, then perform IO/generation/decode under explicit per-frame byte/work
  budgets. S10.2 owns generation identity, cancellation, ancestor fallback, and atomic promotion.
- A fixed byte budget covers source height/aux pages, pinned ancestors, derived runtime caches, page
  tables, clipmap textures, persistent patch records, indirect buffers, upload/readback rings,
  hysteresis headroom, and in-flight data. Accounting uses measured non-zero bytes.
- Priority-aware LRU evicts only unreferenced entries and must demonstrate eviction under feedback
  volume that exceeds pool capacity. The byte total reaches a plateau within the authored profile;
  S10.2's pinned root and complete-front invariants remain prerequisites.
- World/page origins and camera are Float64 on CPU. CPU subtracts camera from page/patch origin in
  Float64 and uploads camera-relative Float32 values; shaders never receive 100 km absolute
  near-field positions.

### Sub-cell visual-detail contract

VT/page-table material data supplies stable macro composition and authored uniqueness. Macro/detail
normals, stochastic anti-tiling, and bounded near-field parallax provide visual frequencies below the
heightfield cell scale. Optional displacement is allowed only from an authored/procedural source with
units, seed/content identity, frequency band, and declared maximum displacement included in patch,
frustum, and HiZ bounds.

Any visual displacement is evaluated identically in main, depth, shadow, and velocity passes.
Object seating, picking, water contact, vegetation placement, and decals either sample the
authoritative heightfield or explicitly opt into the same versioned visual-displacement contract;
no consumer may silently assume displaced pixels changed authoritative terrain.

The renderer does not infer unsourced geometry between 0.5 m posts. Dynamic global weather/season
state remains outside cached VT pages. Collision, navigation, ray queries, and gameplay consume the
authoritative heightfield. Sub-cell visual displacement is cosmetic until a later decision explicitly
promotes and versions it as authoritative height data.

### CPU, worker, and GPU ownership

| Owner | Responsibilities |
|---|---|
| CPU / workers | field-page IO/generation/decode, deterministic runtime-cache oracle, Float64 authority, cancellation, residency policy, manifest validation, GLOBAL science scheduling |
| WebGPU | runtime cache generation where proven, fixed-ring page requests and visibility, frustum/HiZ, bucketed ordered compaction, instanced indirect arguments, rendering |
| WebGL2 Standard | same height pyramid with CPU-instantiated fixed-topology clipmap rings and existing float renderer |

No owner creates exportable geometry artifacts. GLOBAL drainage/climate/science scheduling remains
under the Sprint 9 evaluator contract and is not converted into per-page renderer work.

### Evidence and export integration

Profile frame/pass, memory, request, page, upload, readback, and cache-regeneration budgets are
authored inputs. Gates assert each non-empty measured value is `<=` its authored budget; they do not
discover a passing threshold from the implementation under test. There is no hard-coded
device-class frame target.

Image parity uses two contracts. The deterministic software/control path emits Float32 linear
forward depth `d = clamp((zView-near)/(far-near),0,1)` and Uint32 patch IDs and must be byte-identical
across repeated runs. For a GPU capture over `N>0` covered pixels:

```text
patchIdMismatchCount = count(patchIdGpu(p) != patchIdRef(p)) = 0
badDepth(p) = abs(depthGpu(p)-depthRef(p))
              > max(ulp32(depthGpu(p)), ulp32(depthRef(p)))
gpuDepthMismatchFraction = count(badDepth(p)) / N
```

The profile gate is `gpuDepthMismatchFraction <= gpuParityMaxMismatchFraction`; S10.R0 must freeze that
bound between measured pass/fail controls before S10 is technically refined. The precision oracle
is analytic: compare `Float32((pageOrigin64-camera64)+localVertex)` against the Float64 reference
`(pageOrigin64+localVertex)-camera64`; maximum component error must be `<= 0.001 m` for the named
100 km fixture.

Anti-tiling uses normalized 2D autocorrelation over the named base-tile-period lag set. Let
`P(I)=max(abs(C_I(lag)))` over non-zero named periodic lags and
`reduction=1-P(candidate)/P(PeriodicTileControl/1)`. S10.R0 generates and measures
`PeriodicTileControl/1` and `DecorrelatedControl/1`, then freezes
`antiTilingMinReduction` strictly between their measured reductions. S10.6 must meet that bound and
the periodic mutation must fail it. No such measurements exist yet, so Sprint 10 is grounded but
not technically refined or Ready.

Evidence includes:

- ring/LOD/page/residency/HiZ/morph/toroidal-update/overflow views with fixed legends;
- generated constant, analytic sine, and knife-edge ridge controls;
- source-sample-to-render parity at finest-ring texel centres;
- desktop and mobile screenshots from the built PWA;
- fixed-dt flythrough and cold-teleport sequences covering ring recentering, page misses, cracks,
  morph, cancellation, fallback, feedback latency, and 100 km RTE precision;
- measured resident/cache/transient/upload/readback bytes and frame/pass p50, p95, and p99;
- CPU/WebGL2 versus WebGPU patch-selection image parity, plus culling-off/on image equivalence;
- deterministic page/request/patch ordering under varied completion order;
- an instrumented assertion that no runtime or export path invokes a geometry cooker.

Export remains the Sprint 6/Sprint 9 field contract: versioned height, auxiliary, and domain/region
pages plus their manifest identity and persisted per-page conservative min/max/error headers. Runtime
aggregate min/max/error pyramid/cache representations, height mips, normals, clipmap
textures, patch records, index buffers, and indirect buffers are regenerated after import and are
never package artifacts. Cluster meshes, meshlets, geometry pages, and simplification DAGs are
forbidden export products. Import validates all field roots/dependencies/hashes before document
creation and rejects partial or mixed packages atomically.

### Owning surfaces and cut order

1. **R0:** capture current WebGL capability behavior, no-WebGPU/no-WebGL controls, allocation spies,
   and an asserted scan showing the new path has no geometry artifact inventory or cooker call.
2. **S10.1:** land the launch-time tier probe and blocking modal without selecting Extreme by default.
3. **S10.2:** land versioned streamed height/aux pages, ancestry, pinned roots, cancellation,
   ancestor fallback, atomic promotion, and bounded derived-cache rebuilds.
4. **S10.3:** add shared-grid clipmap rings, vertex pulling, toroidal updates, and morph/stitch rules.
5. **S10.4:** add WebGPU requests, fixed-topology patch visibility, HiZ, bucketed ordered instance
  compaction, and one indirect draw per fixed bucket.
6. **S10.5:** scale asynchronous feedback, exercise eviction, prove the byte plateau, and gate RTE
  precision.
7. **S10.6:** add VT material pages and sourced bounded near-field detail.
8. **S10.7:** add debug/control evidence, platform profiles, built-PWA gates, no-cooker assertion,
   and field-manifest integration.

---

## Story acceptance gates

### S10.1 - Capability tiers and blocking startup modal - 5 pts

**User story:** As an author, I either enter a currently supported Studio tier or receive actionable
diagnostics before the application allocates or replaces terrain state.

**Acceptance gate:** browser fixtures cover every `ExtremeCapability/1` limit/format at its exact
boundary plus insecure context, absent API, null adapter, device rejection, format validation,
device loss, Standard fallback, WebGL2 without the float extension, and neither tier. Timestamp-query
presence/absence changes diagnostics only. Allocation spies remain zero while blocked. Retry performs a fresh
probe; a persisted Extreme preference cannot bypass failure. Copy diagnostics contains the stage and
reported capability facts but no fabricated VRAM/physical-GPU verdict. Headless SwiftShader passes
when requirements pass. The exact modal phrase is **No supported graphics capability**.

### S10.2 - Versioned streamed height pages and runtime derived caches - 8 pts

**User story:** As an author, I can stream and edit 0.5 m height/auxiliary pages while the renderer
regenerates only bounded disposable caches and never creates stored geometry.

**Acceptance gate:** constant/sine/ridge and non-square fixtures build deterministic height-page
ancestry with power-of-two core cells, `coreCells+1` posts, `coreCells` shared-edge stride, explicit
parent registration/downsample, persisted conservative min/max/error headers, declared aprons, and
pinned renderable roots. Runtime generation produces asserted non-empty height mips, normals,
page-table, and upload bytes within profile limits. A bounded edit creates a `surfaceVersion`,
invalidates intersecting leaves, apron dependants, and ancestors while leaving unrelated hashes
unchanged; GLOBAL/domain edits take the broad path. Cancellation rejects a stale late completion and
the old complete front remains until atomic promotion; forced misses resolve to an ancestor. CPU and
optional WebGPU cache products match their declared numeric/byte oracle. A recursive artifact scan
finds zero geometry outputs. Empty inventories, missing roots/aprons/parents, partial promotion,
whole-world allocation, wrongly global local-edit invalidation, and geometry emission are red.

### S10.3 - Cook-free fixed-topology geometry clipmaps - 13 pts

**User story:** As an author, I see source-resolution terrain near the camera through a fixed-memory
runtime grid that remains watertight while moving and changing LOD.

**Acceptance gate:** constant/sine/ridge controls render from shared grid topology with no world
vertex buffer. Finest-ring vertex heights match source page samples at texel centres, including the
0.5 m fixture. Ring and vertex counts remain constant while a scripted camera crosses more than one
ring width. With overlap, captured uploads cover exactly newly exposed toroidal strips plus dirty
rectangles. A delta at least the logical span invalidates and refills the logical texture in
budgeted strips over multiple frames while the S10.2 ancestor renders. CPU scrolling/copy and
unbudgeted same-frame full refill are red. Full-distance sweeps assert zero
background crack pixels, morph reaches exactly 1.0 at handoffs, degenerates/stitches remove
T-junctions, and every render pass uses the same selection/morph. Missing-parent fallback, unmorphed
normals, shifted texel registration, variable world-sized geometry, and explicit dense-mesh storage
are red.

### S10.4 - WebGPU patch culling, HiZ, and compacted instancing - 13 pts

**User story:** As an author, Extreme selects and draws a bounded complete set of runtime heightfield
patches on the GPU without per-patch CPU submission or unsupported WebGPU assumptions.

**Acceptance gate:** the built PWA produces non-empty GPU page requests, fixed-topology patch/ring
visibility, frustum/two-phase-HiZ results, deterministic bucketed instance compaction, and exactly
one `drawIndexedIndirect` per bounded `(pass,material,indexPattern)` bucket, including zero-visible
buckets. Every argument
has `instanceCount=visible patches` and `firstInstance=0`; shader `instance_index` plus bucket base
addresses the one compacted instance buffer. Encoded draw count is bounded by fixed bucket count,
not patch count, and no `indirect-first-instance` feature is requested. WebGPU and CPU reference
selection satisfy the byte/ULP parity contract; culling-off/on captures satisfy the same formula.
Teleport clears history. Open-plain controls remain complete when occlusion kill rate is low.
Reversed-HiZ-op, unordered compaction, stale recycled patch ID, per-pass selection, CPU-per-patch
draw, per-patch indirect slots, non-zero firstInstance, buffer overflow, and hole-on-capacity
mutations are red. Missing mesh shaders, tessellation
shaders, work graphs, bindless, indirect count, and cluster data cannot disable the path because none
is required.

### S10.5 - Scaled async feedback, eviction, byte plateau, and RTE precision - 8 pts

**User story:** As an author, camera motion and teleports refine a complete world without stalls,
holes, stale uploads, unbounded memory, or 100 km coordinate jitter.

**Acceptance gate:** an N-deep async feedback ring reports non-empty demand at a scale that exceeds
pool capacity without synchronous mapping. Repeated flythrough and cold teleport force actual
eviction and a measured total-byte plateau `<=` the authored profile, including cache/in-flight
bytes; S10.2's pinned root and complete-front invariants remain green. The analytic RTE difference is
`<= 0.001 m` per component on the named 100 km fixture and the image remains stable under sub-cell
camera motion. Synchronous readback, no eviction under excess demand, omitted bytes, an unbounded
pool, and Float32 absolute-position mutations are red.

### S10.6 - Sub-cell visual detail - 5 pts

**User story:** As an author, Extreme displays sourced near-field detail below the cell scale without
pretending it changes authoritative terrain or invalidating culling bounds.

**Acceptance gate:** VT fallback ancestors avoid checkerboards; page-border/aniso and residency views
show no seams; macro/detail normals and stochastic anti-tiling meet the S10.R0 autocorrelation bound;
bounded parallax/optional displacement changes only the declared near visual band, stays inside
conservative patch/HiZ bounds, and is identical in main/depth/shadow/velocity. Seating, picking,
water, vegetation, and decals prove either authoritative-height sampling or the shared visual
contract. Removing the detail source removes the sub-cell effect.
Collision and gameplay samples remain bit-identical. Unbounded displacement, dynamic weather baked
into VT, post-indirection gradients, unsourced detail, and implicit collision promotion are red.

### S10.7 - Evidence and export integration - 8 pts

**User story:** As a maintainer and engine integrator, I can inspect, regress, export, and re-import
the runtime-heightfield contract without hidden geometry products or vacuous evidence.

**Acceptance gate:** built-PWA desktop/mobile captures, capability matrix, constant/sine/ridge
controls, source-sample parity, fixed-dt flythrough, teleport, page-miss/crack/morph/HiZ/residency/
toroidal-update views, CPU/GPU image parity, culling parity, cancellation, memory plateau, 100 km
precision, and frame/memory p95/p99 reports all assert non-empty measurements. A static and runtime
call-path scan plus an invocation spy proves no geometry cooker is invoked. After S6/S9 manifests
exist, height/aux/domain pages round-trip; missing root/dependency, mixed hash/version, unsafe path,
and partial cancellation packages are red. Any cluster mesh, meshlet, geometry page, simplification
DAG, or derived runtime cache in the package is red.

---

## S10.R0 readiness calibration story (required, 0 pts)

S10.R0 is a readiness-only calibration story, not an eighth product story, and does not change the
60-point total. It
must generate the deterministic software depth/patch-ID control, GPU wrong-depth and stale-ID
mutations, `PeriodicTileControl/1`, and `DecorrelatedControl/1`; record non-empty measurements; and
freeze `gpuParityMaxMismatchFraction` plus `antiTilingMinReduction` exactly as defined above. Until
those values and red/green endpoints are recorded, Sprint 10 is grounded but not technically
refined or Ready. Implementers may not choose either bound after seeing the fixed implementation.

## Verification matrix and Ready condition

| Contract risk | Passing endpoint | Mutation that must be red |
|---|---|---|
| stale/fictional capability | fresh WebGPU or WebGL2+float probe | persisted tier bypasses failed probe |
| startup side effects | zero document/resource allocations while blocked | eager graph/texture allocation |
| hidden geometry cook | zero geometry artifacts and zero cooker invocations | emit mesh/page or call cooker |
| edit propagation | affected page visible after bounded cache regeneration | stale cache or global rebuild |
| source fidelity | finest-ring samples equal source posts | shifted/filter-selected samples |
| ring continuity | zero crack pixels; morph exactly 1 at handoff | missing stitch or partial morph |
| toroidal motion | overlap uses strips; non-overlap uses budgeted multi-frame refill | CPU scroll or unbudgeted full refill |
| streaming completeness | resident ancestor on every miss | partial-child replacement or hole |
| deterministic control plane | stable page/request/patch order | completion-order-dependent compaction |
| GPU selection correctness | byte-stable control plus calibrated one-ULP GPU mismatch bound | wrong HiZ reduce or stale patch ID |
| memory/cancellation | S10.2 rejects stale work; S10.5 excess traffic evicts and plateaus | stale upload or unbounded pool |
| precision | analytic RTE error `<= 0.001 m` at 100 km | absolute Float32 near-field positions |
| sourced visual detail | calibrated autocorrelation reduction; source removal removes effect | periodic/unsourced detail or pass mismatch |
| package boundary | S6/S9 height/aux/domain pages only | geometry or runtime-cache artifact exported |

Sprint 10 planning is **grounded but not technically refined or Ready** until S10.R0 records and
freezes both calibration bounds. Implementation is **NOT STARTED**.
S10.1 may enter R0 independently after allocation-spy controls are observed red. S10.2-S10.3 wait
for Sprint 9 domain/evaluation ownership. S10.4-S10.5 wait for capability and runtime-heightfield
base gates. S10.7 export integration remains blocked until the Sprint 6/Sprint 9 manifest branches
exist.

## Exit gate

- All seven story gates have measured red and green endpoints; no report-only or zero-inventory gate.
- Programme capability language says "No supported graphics capability," never "no GPU."
- Standard works with WebGL2 plus `EXT_color_buffer_float`; Extreme requires every exact
  `ExtremeCapability/1` secure-context/API/adapter/limit/device/format step; preference never bypasses it.
- Authored 0.5 m height remains field data. No explicit dense mesh, cluster, meshlet, geometry page,
  simplification DAG, offline geometry build, or amortized geometry build exists.
- Runtime clipmaps have fixed topology/memory/vertex count, overlap strip updates, budgeted
  non-overlap refill, source-sample parity, exact transition morph, structural stitching, and
  S10.2-owned ancestor fallback.
- Extreme requires no mesh shaders, tessellation shaders, work graphs, bindless descriptors, or
  indirect-count operation and makes no Nanite-like representation/parity claim.
- Versioned cancellation/atomic promotion, scaled async feedback, complete-front byte-bounded
  eviction/plateau, and analytic RTE precision pass
  flythrough and teleport gates in the built PWA.
- Sub-cell detail has a source, calibrated anti-repetition gate, conservative bound, and pass parity;
  collision/gameplay remains authoritative heightfield data and dependent consumers declare which
  surface contract they use.
- Export contains only S6/S9-owned height, auxiliary, and domain/region pages plus their persisted
  field-page headers. Derived runtime cache representations regenerate after import and never cross
  the package boundary.

## Grounding sources

- Installed Terrain Renderer `references/01-heightfield-lod.md`: geometry clipmap nested rings,
  fixed memory/vertex count, vertex pulling, toroidal updates, transition morph, degenerate
  stitching, runtime edits, and source-centred height sampling. Sprint 10 deliberately selects only
  the fixed-topology geometry-clipmap branch.
- Installed Terrain Renderer `references/06-tiled-streaming.md`: constant-size field-page pyramid,
  complete renderable front, ancestor fallback, async budgets, cancellation, priority-aware
  eviction, and separate collision authority.
- Installed Terrain Renderer `references/07-materials-virtual-texturing.md`: page tables, async
  feedback, resident fallback mips, page borders/virtual gradients, anti-tiling, sourced material
  detail, and bounded invalidation.
- Installed Terrain Renderer `references/08-gpu-driven-culling.md`: persistent patch scene,
  level-by-level GPU selection, frustum/two-phase HiZ, deterministic compaction, indirect submission,
  and asynchronous request feedback.
- Installed Terrain Renderer `references/09-planetary-precision.md`: Float64 CPU authority and
  camera-relative Float32 rendering.
- Installed Terrain Renderer `references/11-verification-failures.md`: constant/sine/ridge controls,
  crack/morph/culling equivalence, temporal replays, deterministic request order, memory plateaus,
  non-empty counters, and p95/p99 budget discipline.
- Installed Terrain Renderer `references/16-tool-viewports.md`: honest asynchronous preview,
  field-contract WYSIWYG, dirty-region uploads, shared-grid clipmap preview, and built/export
  parity.
- Current `src/core/gpu.js`: WebGL2 + `EXT_color_buffer_float` gate, optional `EXT_float_blend`,
  square `RGBA32F` target cache, and no WebGPU/VRAM/software-adapter probe.
- WebGPU/MDN API documentation: adapter features/limits and required device limits,
  `drawIndexedIndirect()` fixed argument records, privacy-tiered reported limits, and the
  non-portability of physical-GPU/software and VRAM classification.
