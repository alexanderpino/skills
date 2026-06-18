# Frame Graph, Render Graph & GPU-Driven Rendering

Reference document for the per-frame pass-scheduling layer that sits *under* the shading techniques in `RENDERING_AND_GRAPHICS.md`. Audience: senior rendering/engine engineers. This file owns *where and when* the GPU does work; `RENDERING_AND_GRAPHICS.md` owns *what* each pass computes, and the `physically-based-rendering` skill owns the BSDF math inside a pass.

## Table of Contents

- Why a Frame Graph
- Architecture: Setup → Compile → Execute
- Resource Lifetime & Transient Aliasing
- Automatic Barrier & State Tracking
- Async Compute Scheduling
- GPU-Driven Rendering & ExecuteIndirect
- Two-Phase Occlusion Culling & the HZB (reverse-Z)
- D3D12 Work Graphs / Mesh Nodes
- Multi-Queue, Multi-Frame & Pacing
- Validation & Debugging

---

## Why a Frame Graph

A frame graph (a.k.a. render graph) is a **declarative DAG of passes and the resources they read/write**, built fresh every frame, then compiled and executed. It is Pillar 3 of the engine for a reason: it is the single mechanism that makes barriers, memory aliasing, async compute, and pass culling *automatic* instead of hand-maintained. Frostbite's "FrameGraph" (Yuriy O'Donnell, GDC 2017) is the canonical reference; UE5's RDG, Unity SRP's RenderGraph, and Snowdrop all ship equivalents.

What it buys you:

- **Automatic barriers.** Resource state transitions (`RENDER_TARGET` → `PIXEL_SHADER_RESOURCE`, etc.) are derived from declared read/write edges. No hand-placed `ResourceBarrier`.
- **Transient memory aliasing.** Resources whose lifetimes don't overlap share the same physical memory. A 1080p HDR target reused 6× per frame costs one allocation, not six.
- **Dead-pass culling.** A pass whose outputs are never consumed is dropped automatically. This is what makes the "2D game pays zero cost for froxel GI" promise (SKILL.md §Scalability) actually hold.
- **Reordering & async.** The scheduler can move independent compute onto an async queue to overlap with raster.
- **Single source of truth for debugging.** The graph is data — dump it to GraphViz, validate it, diff it across frames.

**Do not** build a frame graph as a thin wrapper over command lists that still requires manual barriers. If barriers aren't derived from the graph, you don't have a frame graph — you have a naming convention.

---

## Architecture: Setup → Compile → Execute

Three strict phases per frame. No GPU work happens before Execute.

```cpp
// 1. SETUP — pure declaration, no allocation, no GPU calls.
//    Each pass declares the resources it reads and writes.
struct GBufferPass {
    FGResource albedo, normal, depth;  // handles, not memory
};
auto& gbuf = graph.AddPass("GBuffer",
    [&](FGBuilder& b) {                          // setup lambda
        gbuf.depth  = b.CreateTexture(depthDesc);
        gbuf.albedo = b.CreateTexture(rt8Desc);
        b.Write(gbuf.albedo); b.Write(gbuf.depth);
    },
    [=](FGContext& ctx) {                         // execute lambda (deferred)
        ctx.cmd.SetRenderTargets(...);            // real GPU calls here
        DrawVisibleGeometry(ctx);
    });

// 2. COMPILE — graph is complete. Now:
//    - topological sort, cull dead passes
//    - compute resource lifetimes (first/last use)
//    - assign aliased physical memory
//    - insert barriers from read/write edges
//    - assign passes to queues (graphics / async compute / copy)
graph.Compile();

// 3. EXECUTE — walk passes in scheduled order, run execute lambdas,
//    record command lists (parallel across passes), submit per queue.
graph.Execute(frameAllocator);
```

The setup/execute split is the whole trick: setup builds knowledge of the *entire frame* before any resource is allocated, so the compiler has global information. Capture by value into the execute lambda (resource *handles*, not pointers) — the lambda runs later, possibly on a worker thread.

**Allocate the graph itself in the frame arena** (see `JOB_SYSTEM_AND_FIBERS.md` and the linear-allocator template). The entire graph — passes, edges, lambdas — is rebuilt every frame and freed in one bump-reset. Zero heap churn.

---

## Resource Lifetime & Transient Aliasing

Each transient resource has a lifetime `[firstUse, lastUse]` in topological pass order. Two resources may share physical memory iff their lifetimes are disjoint **and** their memory requirements are compatible (size, alignment, and on D3D12 the heap tier / resource-type flags).

```
Pass:     0    1    2    3    4    5    6
A (HDR)   [=========]                        ← free after pass 2
B (bloom)           [=========]              ← can alias A's memory? overlaps at 2 → no
C (SSAO)                      [====]         ← disjoint from A → aliases A
```

Algorithm: greedy interval assignment (sort by firstUse, bin-pack into physical "buckets"), or a register-allocation-style approach. Frostbite reports ~50% VRAM savings on transients. **An aliased resource is uninitialized** at the start of its lifetime — never assume cleared contents, and insert an aliasing barrier (`D3D12_RESOURCE_BARRIER_TYPE_ALIASING` / a VkMemoryBarrier with the right access masks) at the handoff.

Persistent resources (history buffers for TAA, the HZB across the two phases, streamed textures) are **not** transient — mark them external/imported so the aliaser leaves them alone.

---

## Automatic Barrier & State Tracking

The compiler walks the scheduled pass list per resource and emits a transition whenever the required state changes between consecutive uses.

- **Split barriers.** Begin the transition as early as the last use ends, end it just before the next use — gives the GPU maximum overlap to drain caches. D3D12 `BEGIN_ONLY`/`END_ONLY`; Vulkan via separate `vkCmdPipelineBarrier2` with event-style scoping.
- **Read-combine.** Multiple consecutive read states fold into one combined read state (e.g. `PIXEL_SHADER_RESOURCE | NON_PIXEL_SHADER_RESOURCE`) so you don't ping-pong.
- **Cross-queue transitions** require ownership transfer (Vulkan queue-family transfer; D3D12 handled via fences + state on the common state promotion rules). The graph knows the producing and consuming queues, so it inserts the fence wait.
- **UAV barriers** between two compute passes that RAW-depend through the same resource — derived from write→read edges on UAV-state resources.

Enhanced barriers (D3D12 `EnhancedBarriers` / Vulkan `synchronization2`) are the 2026 baseline: finer stage/access masks, fewer false dependencies. Don't emit legacy resource barriers if the platform supports enhanced.

---

## Async Compute Scheduling

The frame graph assigns each pass a queue. Independent compute that is **not** on the critical path overlaps with raster on a separate hardware queue, reclaiming GPU idle (shadow raster is ROP/geometry-bound and leaves ALU idle; SSAO/particle sim/light culling are ALU-bound and leave ROPs idle — overlap them).

Classic overlaps:
- Shadow map raster (graphics) ‖ GTAO + light culling + particle sim (async compute)
- Post-process compute of frame N ‖ depth prepass of frame N+1 (with care)

Rules:
- Async only helps when the two workloads stress **different** units. Two ALU-bound passes on two queues just contend.
- Synchronize with fences at the graph edges; over-synchronizing serializes and you lose the win.
- Measure with PIX/Nsight queue timelines — async that doesn't actually overlap (because of a hidden dependency or a full barrier) is a common silent regression.
- Budget per queue; a runaway async pass can starve the graphics queue of bandwidth.

---

## GPU-Driven Rendering & ExecuteIndirect

The CPU stops issuing per-object draws. It uploads the scene (instance transforms, mesh/material IDs, bounds) once; the GPU culls and emits its own draw arguments.

```
[CPU] upload instance buffer (persistent, delta-updated)
        │
[GPU] cull compute  ── frustum + HZB occlusion → visible instance list
        │             (append to a structured buffer, atomic counter)
[GPU] build indirect args  ── one DrawIndexedIndirect arg per visible draw/batch
        │
[GPU] ExecuteIndirect / DrawIndexedIndirect(count from GPU buffer)
```

- **One ExecuteIndirect, thousands of draws.** The draw count itself lives in a GPU buffer (`ExecuteIndirect` with a count buffer); the CPU never knows how many survived culling.
- **Bindless is mandatory** (SM 6.6 `ResourceDescriptorHeap`) — per-draw material/texture binds would defeat the whole point. See `assets/bindless_shader_template.hlsl`.
- **Batch by pipeline state**, not by object. Draws sharing a PSO merge into one indirect batch; the per-instance data (transform, material index) is fetched in the shader from the instance ID.
- This is the path that scales to the "15+ billion instances" open-world target (SKILL.md §Scalability). For small scenes it costs a few compute dispatches — cheap, and it culls itself to ~0 when empty.

---

## Two-Phase Occlusion Culling & the HZB (reverse-Z)

Occlusion culling without CPU readback or a frame of latency. Builds on the Hi-Z buffer (HZB): a mip pyramid of the depth buffer where each texel is the **conservative nearest** depth of its 2×2 children.

**Reverse-Z changes the reduction operator.** With reverse-Z (near = 1.0, far = 0.0 — the engine default, see `RENDERING_AND_GRAPHICS.md` §Depth & Reverse-Z), *closest* is the **largest** depth value. So:

- Clear depth to **0.0**, depth test is `GREATER_EQUAL`.
- The HZB stores, per texel, the value that is **conservative for "could anything be in front."** For a reverse-Z occlusion test you compare the object's *nearest* (largest) depth against the HZB; build the HZB with `max` reduction so a tile's stored depth is the closest occluder. (Mirror image of the classic near=0 `min`-reduction HZB — getting the operator backwards silently culls visible geometry or culls nothing, so assert it in a unit test.)
- Use `D32_FLOAT`. Reverse-Z's precision win only exists for floating-point depth; it does nothing for `D24_UNORM`.

The two phases (also referenced in `RENDERING_AND_GRAPHICS.md` §Virtual Geometry):

```
Phase 1: draw the set that was VISIBLE LAST FRAME (good occluder guess).
         Build HZB from the resulting depth.
Phase 2: test EVERYTHING ELSE against the new HZB.
         Newly-disoccluded objects (camera moved, occluder gone) draw now.
         Update HZB again for next frame's Phase 1 seed.
```

This eliminates the popping you'd get from a one-frame-stale occlusion result without ever stalling on a CPU readback. Meshlet/Nanite-style pipelines run the same two-phase test at *cluster* granularity.

---

## D3D12 Work Graphs / Mesh Nodes

The 2026 fast path (SM 6.9). The GPU spawns its own work without round-tripping to the CPU or even to a fixed dispatch dimension: a node produces records that schedule downstream nodes, and the driver manages the transient memory and occupancy. Mesh Nodes connect a work graph directly into the mesh-shader rasterizer.

Why it matters for this layer: a work graph is, in effect, a **GPU-resident sub-frame-graph** for highly variable workloads (material classification → per-material shade, adaptive tessellation, particle expansion). It naturally scales with the workload (SKILL.md §"Dynamic GPU Autonomy") instead of being sized for worst case.

Fallback chain (graceful degradation per capability query):
- SM 6.9: Work Graphs + Mesh Nodes
- SM 6.5: Mesh Shaders + ExecuteIndirect
- SM 6.0: classic VS/PS with GPU-culled indirect draws (~2× slower, still GPU-driven)

Keep all of this behind the HAL capability query — never hardwire the work-graph path (see SKILL.md Forbidden Patterns: no platform `#if` outside the HAL).

---

## Multi-Queue, Multi-Frame & Pacing

- **Frames in flight.** 2–3 typically. Per-frame transient resources and upload buffers are ring-buffered; the frame allocator is reset only after the GPU signals that frame's fence. Never reset memory the GPU is still reading.
- **CPU/GPU pipelining.** Build frame N+1's graph on the CPU while the GPU executes frame N. The frame graph's setup phase is pure CPU and parallelizes across the job system.
- **Latency vs throughput.** More frames in flight = higher throughput, worse input latency. Expose it; for competitive/VR, cap at 1–2 and consider a low-latency mode (NVIDIA Reflex-style: delay CPU sim start to finish just-in-time).
- **Present pacing.** Decouple sim/render rate from present; pace to the display (VRR-aware). A frame graph executed at a jittery cadence still looks bad.

---

## Validation & Debugging

- **Dump the graph.** Emit GraphViz/JSON of passes, edges, queue assignment, and aliasing buckets. Diff across frames to catch a pass that silently dropped or stopped aliasing.
- **Barrier validation layer.** In debug, run the D3D12 debug layer / Vulkan validation with synchronization validation on. A frame graph with a missing edge produces a real race — sync-validation catches it deterministically; a visual glitch does not.
- **Resource lifetime asserts.** Assert that no pass reads a transient before its first write, and that aliased resources get an aliasing barrier.
- **Deterministic mode** (SKILL.md §Job System): serialize all passes onto one queue in topological order. If the bug reproduces serialized, it's logic; if it vanishes, it's a sync/race — look at the missing edge.
- **Per-pass GPU timestamps** (`ZoneScopedGPU`/PIX markers) keyed by pass name; the graph already has the names. Regression-gate the per-pass ms.

---

## See Also

- `RENDERING_AND_GRAPHICS.md` — what each pass computes (deferred/PBR/GI/shadows/post), depth & reverse-Z, virtual geometry
- `JOB_SYSTEM_AND_FIBERS.md` — the worker pool that records command lists in parallel and the frame arena the graph is built in
- `PERFORMANCE_AND_PROFILING.md` — frame budget, async-compute measurement, GPU occupancy
- `CROSS_PLATFORM_AND_CONSOLE.md` — per-API barrier/queue/indirect specifics (DX12/Vulkan/Metal/NVN2)
- `physically-based-rendering` skill — the BSDF math evaluated inside the shading passes
