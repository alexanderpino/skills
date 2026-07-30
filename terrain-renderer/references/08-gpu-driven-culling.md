# GPU-driven culling & submission

This chapter owns how terrain gets *drawn*: the persistent GPU scene, the compute culling ladder
(frustum → cluster → two-phase HiZ occlusion), indirect submission, GPU-side LOD selection, and
the terrain-specific culling wins (horizon, shadow cascades, terrain-as-occluder). What is being
culled comes from `01`/`02`/`04`/`05`; what feeds the buffers is streaming `06`; planetary horizon
math is `09`; shadow-caster doctrine is `10`; the debug views that prove any of this works are `11`.

Contents: [Doctrine](#doctrine-cpu-sets-policy-the-gpu-decides) ·
[Culling ladder](#the-culling-ladder) · [Two-phase occlusion & HiZ](#two-phase-occlusion--hiz) ·
[Submission](#submission-indirect-everything) · [GPU LOD selection](#gpu-lod-selection--feedback) ·
[Terrain-specific wins](#terrain-specific-culling-wins) ·
[Visibility buffer path](#visibility-buffer--deferred-material-path) ·
[2026 frontier](#the-2026-frontier) · [Pitfalls](#pitfalls) · [Sources](#sources--provenance)

## Doctrine: CPU sets policy, the GPU decides

The division of labor, fixed since Haar & Aaltonen's 2015 formulation and unchanged since:

- **CPU owns policy.** Camera, budgets (`tau`, triangle/draw ceilings), streaming decisions (`06`),
  what exists in the world. It uploads *deltas* to a persistent GPU scene, not per-frame lists.
- **GPU owns per-frame truth.** Which chunks/clusters are visible, at what LOD, in which passes —
  decided in compute, written into indirect argument buffers, consumed by the GPU without the CPU
  ever seeing the answer. Per-object CPU cost is zero; the CPU issues a handful of dispatches and
  one `ExecuteIndirect`/`vkCmdDrawIndexedIndirectCount` per pass, regardless of world size.

The **persistent GPU scene** is the load-bearing structure: structured buffers holding every
resident chunk/tile/cluster — bounds (AABB + max displacement), LOD tree links, material/page IDs,
mesh offsets into shared vertex/heightmap pools. Streaming (`06`) patches this scene incrementally;
culling reads it every frame. If you are rebuilding any array proportional to world size on the CPU
per frame, you have not built this architecture — you have built a CPU renderer with GPU-flavored
syntax.

Terrain is the *ideal customer* for this design, better than general scenes: thousands-to-millions
of near-identical units (chunks, clusters, voxel bricks) with homogeneous shading, no skinning, no
per-object gameplay logic, bounds known analytically from the heightfield, and a spatial hierarchy
(quadtree/clipmap rings) that already exists for LOD. General GPU-driven pipelines pay complexity
for heterogeneity; terrain gets the wins almost for free. If the engine adopts GPU-driven rendering
anywhere, terrain should be first.

**Pitfall:** partial adoption that keeps a CPU visibility pass "for safety" and then uploads its
results — you pay both costs and gain a frame of latency. Commit: the CPU may keep a *coarse* cut
(dead tiles, streaming residency) because it owns that data anyway, but per-frame visibility and
LOD live on the GPU or the architecture is fiction.

## The culling ladder

Cull coarse-to-fine; each stage runs in compute and compacts survivors for the next. Skipping a
stage is legitimate; reordering them is not — fine stages assume coarse rejection already happened.

| Stage | Granularity | Mechanism | Typical kill rate |
|---|---|---|---|
| Frustum | chunk/tile | 6 plane-vs-AABB tests in compute | large (view-dependent) |
| Cone / backface | cluster (`02`) | normal-cone vs view vector | ~30-50% of back-facing clusters |
| Occlusion (two-phase HiZ) | chunk then cluster | depth pyramid test | the big one in hilly terrain |
| Triangle (optional) | triangle | compute pre-pass: backface, zero-area, small-tri | only when tris are tiny and raster-bound |

**Frustum culling in compute.** One thread per chunk, test the AABB against six planes (positive-
vertex test). The terrain-specific trap is **conservative bounds**: the tested bound must contain
the geometry *as rasterized*, not the base grid. Inflate by maximum displacement (heightmap
min/max per chunk — the generator's per-chunk stats, terrain-architect `08`), by skirt depth,
by geomorph excursion (a morphing vertex sweeps between two LODs' heights — bound the union), and
by any WPO-style material displacement (`07`). Under-inflated bounds fail *at the screen edge*: a
chunk whose displaced peak enters the frustum while its base AABB does not gets culled, and
geometry visibly pops in at the border as the camera pans. This bug hides in flat test terrain and
ships; test on max-relief terrain with skirts (`11`).

**Cluster cone/backface culling** (`02` owns cluster construction; the test lives here): each
cluster stores a normal cone (axis + apex angle, plus apex point for the view-dependent form).
Reject when the entire cone faces away from the camera. Cheap, effective on rolling terrain,
nearly useless on flat plains (all normals up — the cone test never fires for a ground camera);
budget accordingly rather than assuming general-scene kill rates. Wihlidal's compute triangle
culling (GDC 2016) extends the idea per-triangle — worth it only when average triangle size is
small enough that fixed-function backface rejection is the bottleneck; measure before adopting.

## Two-phase occlusion & HiZ

The occlusion problem is circular: you need a depth buffer to cull, but you need to cull to render
the depth buffer. Single-phase answers are all wrong in a characteristic way — last frame's depth
reprojected to this frame's camera misses disocclusions, so objects that *became* visible this
frame pop in one frame late (the classic reprojection artifact). **Two-phase occlusion culling**
(Haar & Aaltonen 2015; the same structure drives Nanite, Karis 2021) closes the loop within one
frame:

```
Phase 1: draw everything that was visible LAST frame (per-chunk/cluster visibility bit)
         → build HiZ pyramid from the resulting depth
Phase 2: test ALL candidates (survivors of frustum/cone stages) against HiZ
         → draw only those that were NOT drawn in phase 1 but pass now (newly visible)
         → write this frame's visibility bits for next frame's phase 1
```

Phase 1 is almost always a superset of true visibility under camera coherence, so the phase-1
depth is a nearly complete occluder set; phase 2 catches disocclusions *this frame*. No
reprojection, no one-frame-late popping, no artist-placed occluder proxies. Costs: two culling
dispatch rounds, two submission rounds per pass, and a persistent visibility-bit buffer keyed by
stable chunk/cluster IDs (streaming must not recycle an ID mid-frame — `06`).

Laid out as the frame-N timeline, with the HiZ dependencies:

```
frame N -------------------------------------------------------------------------->
+------------------+   +------------+   +-----------------+   +------------------+
| PHASE 1          |   | build HiZ  |   | PHASE 2         |   | draw the newly   |
| draw everything  |-->| pyramid    |-->| test ALL        |-->| visible (pass,   |
| visible LAST     |   | from that  |   | candidates      |   | not yet drawn);  |
| frame (vis bits) |   | depth      |   | against the HiZ |   | write vis bits   |
+------------------+   +------------+   +-----------------+   +------------------+
         |                ^      |              ^                       |
         +----- depth ----+      +----- HiZ ----+                       +--> phase 1,
      (the prev-visible set is a                                              frame N+1
       near-complete occluder set)
```

**HiZ build correctness** — this is where the bugs live:

- **Reduction convention.** With standard depth (near=0, far=1), an occluder test needs the
  *farthest* depth in the footprint → **max**-reduce; with reversed-Z (`09` mandates it), →
  **min**-reduce. Getting this backwards produces *false occlusion*: geometry near silhouettes
  vanishes for a frame under camera motion — a sparkle-of-absence at depth edges that is easy to
  misread as a crack (`11` catalogues both).
- **NPOT and odd dimensions.** A naive 2×2 reduction of an odd-sized mip drops the last row/
  column — those texels' depths never propagate up, and the pyramid claims occlusion where the
  dropped texels held sky. Handle odd dims by having edge texels gather the extra row/column
  (3×2 / 2×3 / 3×3 footprints), or pad to POT with far-plane values (near-plane under reversed-Z
  conventions — pad with the *non-occluding* extreme for your convention).
- **Sample footprint.** To test a bound: project its corners, clamp to screen, pick the mip where
  the screen rect spans ≤ 2×2 texels, take the conservative extreme of the 4 fetches, compare
  against the bound's nearest depth. Picking the mip one level too fine (rect spans 3+ texels and
  you only fetch 4) silently under-samples and produces false visibility — benign-looking but it
  erodes the entire win. Compute the mip from the rect's *larger* dimension, ceil the log2.

**First frame and teleports.** Phase 1 has no history after load, camera cut, or teleport. Options,
in order of preference: treat all as visible for one frame and eat the spike (simple, correct,
budget for it); seed visibility from a cheap proxy pass (terrain max-mip occluder below); or warm
the history with a pre-cut render. Never carry stale visibility bits across a teleport — one frame
of a wrong world, and with feedback-driven streaming (`06`) the wrong *pages* get requested too.

## Submission: indirect everything

Survivors become draws without CPU involvement:

- **MultiDrawIndirect + count buffer.** Culling compute appends surviving draws' args
  (`IndexCountPerInstance`, offsets, chunk ID in a root-constant slot or via `StartInstance`) to
  an args buffer and bumps an atomic counter; submit with
  `ExecuteIndirect` / `vkCmdDrawIndexedIndirectCount` using the GPU-side count. Without count-
  buffer support you must draw the worst case with zeroed args — functional, but wasteful on
  front-end throughput; prefer the count path everywhere it exists (D).
- **Compaction.** Append via atomics is simplest and fine at terrain scales (thousands of chunks);
  prefix-sum compaction produces *ordered* survivor lists (preserves front-to-back or material
  order, no atomic contention) and is worth it once counts hit hundreds of thousands (clusters) or
  when draw order matters for early-Z. Atomic append order is nondeterministic — if you need
  deterministic capture comparisons (`11`), sort or prefix-sum.
- **Vertex pulling** (`01`): a draw is (shared patch IB) × (chunk ID). No per-chunk vertex
  buffers means the args buffer is tiny and uniform — every draw differs only in its constants.
  This uniformity is what makes terrain MDI degenerate into "one draw, N instances" in the limit;
  use instancing when every chunk truly shares topology, MDI when edge-permutation IBs (`01`)
  vary the index count. The same generate→cull→compact→indirect spine, specialized to millions
  of vegetation/scatter instances, is `15`.
- **Bindless.** Per-tile heightmaps, splat/VT indirection (`07`), material tables: descriptor
  indexing from the chunk record. Without bindless you are back to CPU-side descriptor binding
  per draw, which reintroduces the per-object cost the architecture exists to kill. NonUniform
  resource index semantics apply — mark divergent indexing or suffer undefined behavior on some
  hardware (D).
- **Mesh shader path.** Amplification/task shader does cluster culling in-pipeline, mesh shader
  fetches and emits meshlets (`02`) — collapses the compute-cull → args-buffer → draw round trip
  into one pipeline, and triangle-level culling comes nearly free. Prefer it on hardware tiers
  that have it; keep the ExecuteIndirect path as the fallback and hide the difference behind the
  same GPU scene so the two paths can be diffed (`11`).
- **Pass batching.** Opaque chunks, skirts, water surface, and decal-receiving terrain are
  *different pipeline states* → separate survivor lists. Run culling once, write per-pass bits
  (main, each shadow cascade, water reflection), then compact per (pass, PSO) bucket. Do not
  re-cull per pass from scratch; do not merge water into the opaque list because "it's all
  terrain" — blend state and depth usage differ and the batch breaks anyway.

## GPU LOD selection & feedback

LOD selection is the same `rho > tau` controller as `01`, executed in compute against the GPU
scene:

- **Level-by-level quadtree dispatch.** Dispatch N: nodes at level N test their error; refiners
  append children to the next dispatch's work list, coarseners append themselves to the draw
  list. Simple, debuggable, one indirect dispatch per level (~8-12 for planet-scale trees). The
  per-level barrier costs a few dispatch tails; at terrain scales this is rarely the bottleneck —
  prefer it as the default.
- **Persistent threads / work-stealing traversal.** One dispatch, workgroups pop/push a shared
  queue. Faster in deep-tree pathologies, but it fights the hardware scheduler, is easy to
  deadlock, and is miserable to debug. In 2026, treat as legacy: Work Graphs (below) is the
  sanctioned form of this idea where available.
- **CBT** (`01`) is the fully-GPU-resident endpoint: the LOD *structure itself* lives in a GPU
  bitfield, split/merge is the per-frame compute pass, and the draw list falls out of leaf
  enumeration. There is no separate "selection" step to feed submission — subsumes this section
  for single-domain terrain, and frustum/HiZ tests move *into* the split criterion.
- **Hysteresis.** Split at `rho > tau`, merge at `rho < tau * h` with `h ≈ 0.7-0.85`, never both
  thresholds equal — a camera hovering at the boundary otherwise flickers a chunk between LODs
  every frame, which thrashes geomorph state, visibility bits, and (worst) streaming requests.
  Same rule for occlusion-driven streaming decisions.
- **Feedback to the CPU** — selection discovers wants (finer tiles, VT pages `07`): write requests
  to a GPU buffer (append + dedupe by tile ID, or a bitfield the CPU scans), copy to a readback
  ring, consume on the CPU **N frames later** (N = ring depth, 2-3). The discipline is absolute:
  readback is asynchronous, latency is a design constant (streaming already tolerates seconds,
  `06`), and *nothing* ever waits on it. One synchronous map of an in-flight buffer flushes the
  pipeline and costs more than the entire culling system saves. Budget the requests buffer and
  drop-with-counter on overflow (`11` asserts the counter).

## Terrain-specific culling wins

Three cuts general pipelines don't have, all cheap, all large:

- **Horizon culling** (`09` owns the math). On a planet, everything beyond the geometric horizon
  of the camera's altitude is invisible regardless of frustum — a single per-chunk dot-product
  test against the horizon plane/cone kills entire continents before HiZ even runs. Hook it
  between frustum and occlusion stages; it is the only stage whose kill rate *grows* with world
  size.
- **Per-cascade shadow culling** (`10` owns bias/fitting doctrine). Each cascade is its own
  frustum → its own culling pass over the same GPU scene with per-pass visibility bits. Casters
  must be tested against the *light* frustum extruded along the light direction — a caster
  outside the camera view still casts into it (see Pitfalls). Terrain-specific win: per-chunk
  height bounds give exact caster AABBs, so cascade culling is tight without artist bounds; and
  chunks whose max height sits below the receiver horizon of a cascade cannot cast into it —
  cull them (conservatively: test against the cascade's receiver depth range).
- **Terrain as the occluder for everything.** The heightfield itself is the best long-range
  occluder in the scene. Build a conservative **max-mip pyramid** of the heightmap (max-reduce;
  coarse mips = "nothing in this footprint exceeds h"); test *any* object — props, buildings,
  crowds, other terrain chunks — by comparing its bound's min height against the conservative
  terrain height along the camera ray footprint, or more simply by rasterizing a coarse
  heightfield proxy into the phase-1 depth before building HiZ so the standard two-phase test
  inherits it. Behind-the-ridge culling of whole cities for the cost of a small proxy draw is a
  standard open-world win (F/T — widely described in AAA talks, no single canonical citation).
  The proxy must be *conservative* (never higher than true terrain — use min-reduce for the
  proxy surface you rasterize) or it culls visible objects along ridgelines.

## Visibility buffer / deferred material path

Burns & Hunt (JCGT 2013): rasterize only `(instance/cluster ID, triangle ID)` per pixel (+ depth);
reconstruct barycentrics and attributes in a later compute pass and shade there. For terrain,
worth it when: triangles are near-pixel-sized (quad overshading makes forward raster pay 4× the
pixel work at triangle edges — at 1 px/tri nearly every pixel is an edge); materials are heavy
layered splats/VT stacks (`07`) where shading once per *visible* pixel beats overdraw; or `02`'s
software rasterizer is in play (which must output a visibility buffer anyway — a software raster
cannot run a pixel shader, so the two decisions are one decision, Karis 2021).

Mechanics for terrain: chunk ID + triangle ID is enough to reconstruct everything (grid position
from triangle ID, height from the heightmap, UVs analytically) — terrain needs *no* vertex
attributes in memory at all on this path. Shade in compute, bucketed per material set: classify
pixels by material/tile ID, build per-bucket pixel lists (prefix sum), dispatch one shading
kernel per bucket to keep waves coherent. When triangles are large and the material is one splat
blend, classic deferred or forward wins — the visibility buffer's reconstruction cost (manual
attribute fetch + analytic derivatives for mip selection, the fiddliest part) is pure overhead
there. Decide on measured triangle size, not fashion.

## The 2026 frontier

Marked honestly — these change the shape of the pipeline but are not yet default-everywhere:

- **D3D12 Work Graphs** (D — shipped in Agility SDK 2024, hardware/driver support still uneven;
  production adoption `?`). GPU-spawned work without round-tripping through indirect dispatch:
  a quadtree traversal node enqueues child-node work; a culling node enqueues submission records;
  streaming analysis enqueues feedback compaction. This is the sanctioned replacement for
  persistent-threads traversal and for dispatch-per-level chains. Mesh nodes (graphics leaf
  nodes) remain the least-mature corner (`?`). Design the GPU scene so traversal can be ported to
  work graphs later; do not block shipping on them.
- **Vulkan device-generated commands** (D — `VK_EXT_device_generated_commands`, 2024): GPU-written
  command sequences including pipeline/shader switches, closing most of the gap to
  ExecuteIndirect-with-state-changes. Same posture: use where present, keep the MDI fallback.
- **ReBAR / GPU upload heaps** (D/F): CPU-visible VRAM at full size makes the persistent scene
  trivially patchable — streaming writes chunk records directly instead of staging + copy.
  Discipline still required: write-combined memory hates reads and scattered writes; patch in
  contiguous bursts, never read back through the BAR, and keep the staging path for non-ReBAR
  hardware.

## Pitfalls

- **Readback stalls.** Any `Map` of a buffer the GPU wrote this frame serializes CPU and GPU. All
  feedback (streaming requests, statistics, `11` counters) goes through an N-deep ring consumed
  frames later. Grep for synchronous maps in code review; one is enough to halve frame rate.
- **Indirect-arg corruption is silent.** A garbage index count draws garbage or nothing, with no
  validation error and no CPU-side trace. Instrument permanently: atomic counters per culling
  stage (in → out), a debug mode that copies args to a readback ring, and breadcrumb writes
  (stage ID + chunk ID into a ring buffer) so a device removal or a wrong draw can be walked
  backwards. Budget these into the shipping build behind a flag — the bug will occur on the
  hardware you don't have.
- **HiZ convention bugs** present as false occlusion at silhouettes and depth edges — one-frame
  disappearances under motion. Check the reduce op against the depth convention (reversed-Z →
  min), the NPOT edge handling, and the footprint mip selection, in that order (`11` has the
  capture recipe).
- **Culling shadow casters against the camera's HiZ.** Wrong: a caster occluded from the camera
  (or outside its frustum entirely) still casts a shadow the camera sees. Each cascade culls
  against its own frustum and, if occlusion-culling casters at all, against a *light-view* depth
  pyramid — or accept camera-frustum-extruded conservative bounds and skip caster occlusion
  (`10`).
- **Non-conservative bounds under displacement.** Geomorph (`01`), skirts, WPO/material
  displacement (`07`), voxel remesh-in-flight (`05`) all move geometry outside static AABBs.
  Every bound in the GPU scene carries an inflation term with a named owner; `11`'s screen-edge
  pan test catches violations.
- **Two-phase history desync.** Visibility bits keyed by array slot instead of stable ID break
  when streaming compacts the scene — a recycled slot inherits a dead chunk's visibility and
  phase 1 draws the wrong thing (or skips a visible one) for a frame. Key history by persistent
  chunk ID; clear on recycle (`06`).
- **Hysteresis missing** anywhere a threshold drives a binary state (LOD, occlusion-driven
  streaming, cascade membership) → per-frame flicker and request storms at the boundary.
- **Assuming general-scene kill rates.** Flat terrain defeats cone culling; open plains defeat
  occlusion culling. Profile the peak-vista frame (`11`), not the canyon frame.

## Sources & provenance

| Claim | Tier |
|---|---|
| GPU-driven pipelines: persistent GPU scene, CPU-policy/GPU-visibility split, compute culling + MDI — Haar & Aaltonen, "GPU-Driven Rendering Pipelines", SIGGRAPH 2015 Advances in Real-Time Rendering course (Assassin's Creed Unity) | **T** |
| Two-phase occlusion culling (draw prev-visible → HiZ → test all → draw newly-visible) — same talk; adopted and restated for Nanite | **T** |
| Nanite cluster culling, two-pass occlusion, software raster → visibility buffer coupling — B. Karis, "Nanite: A Deep Dive", SIGGRAPH 2021 Advances course | **T** |
| Visibility buffer: ID+depth raster, deferred attribute fetch and shading — Burns & Hunt, "The Visibility Buffer: A Cache-Friendly Approach to Deferred Shading", JCGT 2013 | **P** |
| Compute cluster/triangle culling (backface cones, small-primitive culling) — G. Wihlidal, "Optimizing the Graphics Pipeline with Compute", GDC 2016 (Frostbite) | **T** |
| ExecuteIndirect / vkCmdDrawIndexedIndirectCount semantics, count buffers | **D** |
| Bindless / descriptor indexing, NonUniformResourceIndex divergence rules | **D** |
| Mesh/task (amplification) shader pipeline as in-pipeline cluster culling | **D** |
| D3D12 Work Graphs — GPU-enqueued work; mesh nodes immature | **D**; production readiness **?** |
| VK_EXT_device_generated_commands | **D** |
| ReBAR / GPU upload heaps; write-combined memory discipline | **D/F** |
| Quadtree LOD: level-by-level indirect dispatch vs persistent threads trade-off | **F** |
| LOD/occlusion hysteresis band (h ≈ 0.7-0.85) | **F** (band values are judgment) |
| Async N-frame readback ring discipline for GPU→CPU feedback | **F** |
| Horizon culling as a per-chunk plane/cone test (math in `09`) | **F** |
| Per-cascade caster culling with height-bound-tightened AABBs; never against camera HiZ | **F** (practice; consistent with shadow doctrine in `10`) |
| Heightfield max-mip pyramid / coarse terrain proxy as long-range occluder for all scene content | **F/T** (widely described in open-world AAA talks; no single canonical citation) |
| Material-bucketed compute shading via pixel classification + prefix sum | **F** (standard visibility-buffer practice) |
| Quad-overshading cost at ~1 px triangles motivating visibility-buffer/deferred-material paths | **P/F** (raster behavior is documented; crossover threshold is judgment) |
| Cone culling ineffective on flat terrain; occlusion culling weak on plains | **F** (geometric argument) |
