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

The derivation is one linear walk. State is tracked **per subresource** (mip × array slice), never per whole resource, so a pass touching mip 0 doesn't over-transition mip 3:

```text
// API-AGNOSTIC PSEUDOCODE — not a backend. Lowers to D3D12 enhanced barriers
// or Vulkan sync2. Omits queue-family ownership (see Async Compute), depth/
// stencil plane splits, and all validation. Illustrates the derivation only.
struct State {
  Access access; Sync stage; Layout layout;
  Pass lastUse; bool lastWasWrite;
  Resource aliasPredecessor;
};
map<(Resource, Subresource), State> cur;              // last-known state per subresource

for pass in scheduledOrder:                            // topo order, queues already assigned
  for use in pass.accesses:                            // each declared read/write edge
    for sub in expand(use.range):                      // per mip / array slice
      State& s = cur[(use.resource, sub)];

      if use.resource.aliasedThisFrame and use.isFirstUse:   // transient-alias activation
        emit AliasingBarrier(s.aliasPredecessor -> use.resource);
        s = { NONE, NONE, UNDEFINED, null, false, null }; // contents are GARBAGE

      if isRead(s.access) and isRead(use.access) and s.layout == use.layout:
        s.access |= use.access; s.stage |= use.stage;        // retain ALL reader stages
        s.lastUse = pass; s.lastWasWrite = false;
        continue                                             // compatible read-combine, NO barrier

      if s.access != use.access or s.layout != use.layout:
        emit Transition(from s, to use,                      // split only when lastUse exists:
                        begin = s.lastUse?.end,              //   after the final prior access
                        end   = pass.begin);                 //   just before this use
      else if use.layout == UAV and s.lastWasWrite:          // same UAV state hides no hazard
        emit UavBarrier(use.resource, sub);                  // RAW / WAW through one UAV

      s.access = use.access; s.stage = use.stage; s.layout = use.layout;
      s.lastUse = pass; s.lastWasWrite = isWrite(use.access);
```

Two hazards the walk must never miss: an **aliased** subresource is `UNDEFINED` at first use (emit the aliasing barrier and treat contents as garbage), and a write→read/write pair that stays in the **same UAV layout** gets no automatic transition, so it needs an explicit `UavBarrier`.

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

Cross-queue dependencies resolve to GPU-side wait/signal on a monotonic timeline per queue — no CPU stall, no over-synchronization beyond the actual graph edges:

```text
// API-AGNOSTIC PSEUDOCODE — not a backend. Lowers to timeline semaphores
// (Vulkan) or ID3D12Fence (D3D12). Values remain globally monotonic while the
// fence/semaphore exists; NEVER reset them while older frames can be in flight.
nextSignal[q] persists across frames for each queue     // graphics / asyncCompute / copy

for pass in scheduledOrder:
  // 1. collect the highest predecessor value per foreign queue. The graph
  // compiler emits per-subresource RAW, WAR, and WAW hazard edges:
  //   read  waits for the last writer;
  //   write waits for the last writer AND all outstanding readers.
  waits = {}                                            // queue -> timeline value
  for edge in incomingResourceHazards(pass):            // edge carries resource+subresource
    producer = edge.predecessor
    if producer.queue != pass.queue:
      waits[producer.queue] = max(waits[producer.queue], producer.signalValue)
      // Vulkan: also emit the queue-family ACQUIRE half of the ownership transfer
      // (producer emitted the RELEASE); the state/layout change rides the barrier.
      emit QueueOwnershipAcquire(edge.resourceRange,
                                 from=producer.queue, to=pass.queue)

  // 2. the consuming queue waits on each producer's value — GPU waits, CPU does not
  for (q, value) in waits:
    submit[pass.queue].waitTimeline(q, value)

  submit[pass.queue].record(pass)

  // 3. signal real cross-queue edges and the final submission used for frame pacing
  if pass.hasCrossQueueConsumer or pass.isLastSubmissionOnQueue:
    pass.signalValue = ++nextSignal[pass.queue]
    submit[pass.queue].signalTimeline(pass.queue, pass.signalValue)

// CPU frame pacing (separate from the GPU-side waits above): reset frame N's
// arena only after EVERY queue that used it reaches frameFinalValue[q].
for q in queuesUsedBy(frameN):
  waitTimeline(q, frameN.finalValue[q])
// Alternative: submit one final fan-in that waits on all queues, then signal one
// retirement fence. Waiting on graphics alone is unsafe if copy/compute outlives it.
```

Wait **only** at real cross-queue hazard edges. Track both the last writer and outstanding readers per subresource: writer-only tracking catches RAW/WAW but misses cross-queue WAR. Signals do not themselves serialize queues, but coalescing them to hazard edges and frame-completion points reduces submission overhead. A resource produced on async and read on graphics needs *both* this timeline wait **and** the state/ownership transition from the barrier walk above; the fence orders execution, the barrier makes the memory visible. An aliased resource shared across queues also takes its aliasing barrier on the consuming queue *after* the wait.

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

Occlusion culling without CPU readback or a frame of latency. Builds on the Hi-Z buffer (HZB): a mip pyramid of the depth buffer where each texel is the **conservative farthest** occluder depth of its 2×2 children — the value that lets you cull only objects provably behind *everything* in that tile (see the reduction operator below).

**Reverse-Z changes the reduction operator.** With reverse-Z (near = 1.0, far = 0.0 — the engine default, see `RENDERING_AND_GRAPHICS.md` §Depth & Reverse-Z), *closest* is the **largest** depth value. So:

- Clear depth to **0.0**, depth test is `GREATER_EQUAL`.
- A conservative occlusion HZB stores the **farthest** occluder in each tile so it only culls objects provably behind *everything* there. In reverse-Z the farthest surface is the **smallest** depth, so **build the HZB with `min` reduction** — the mirror of the classic near=0/far=1 HZB, which uses `max` for the same "farthest occluder" semantics. Getting the operator backwards silently culls visible geometry or culls nothing, so assert it in a unit test.
- Use `D32_FLOAT`. Reverse-Z's precision win only exists for floating-point depth; it does nothing for `D24_UNORM`.

Build (min reduction) and test (compare the object's *nearest* point against the farthest occluder):

```hlsl
// HLSL-LIKE PSEUDOCODE — exact bindings and dispatch bounds are backend-specific.
// BUILD: mip 0 = depth buffer. Each coarser texel = MIN of its 2x2 children.
// Reverse-Z: min == farthest occluder == the conservative value.
float ReduceHZB(Texture2D<float> src, uint2 dst, uint srcMip) {
    uint width, height, levels;
    src.GetDimensions(srcMip, width, height, levels);
    uint2 base = dst * 2;
    float d = 1.0;                                        // identity for min()
    [unroll] for (uint y = 0; y < 2; ++y)
    [unroll] for (uint x = 0; x < 2; ++x) {
        uint2 p = base + uint2(x, y);
        if (p.x < width && p.y < height)                  // preserve odd edge texels
            d = min(d, src.Load(int3(p, srcMip)));        // explicit source mip
    }
    return d;
}

// TEST: an object is occluded iff its NEAREST point (the largest reverse-Z depth
// over its bounds) is still behind the farthest occluder (the min-reduced HZB)
// across its screen footprint.
bool IsOccluded(ScreenRect r, float objNearestDepth /* max reverse-Z of bounds */) {
    uint mip = SelectMipForAtMost2x2Texels(r);
    uint2 lo = RectMinTexel(r, mip);
    uint2 hi = RectMaxTexel(r, mip);                       // hi-lo <= (1,1), clamped to mip
    float occ = min(min(HZB.Load(int3(lo,                  mip)),
                        HZB.Load(int3(uint2(hi.x, lo.y),   mip))),
                    min(HZB.Load(int3(uint2(lo.x, hi.y),   mip)),
                        HZB.Load(int3(hi,                  mip))));
    return objNearestDepth < occ;                         // strictly behind everything -> cull
}
```

> **Unit-test the operator, not just the code.** Place a small quad fully behind a large wall and assert `IsOccluded == true`; move the quad in front and assert `false`. Flipping `min`↔`max` or `<`↔`>` still compiles and only surfaces as popped-away geometry or zero culling — a deterministic assert against a known-occluder scene catches it immediately.

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

Compute Work Graphs arrived in Shader Model 6.8. Mesh Nodes, which connect work graphs to rasterization, require the Shader Model 6.9 preview path and an opt-in Agility SDK. Treat both as optional: driver scheduling and backing-memory requirements still need measurement and explicit limits.

Why it matters for this layer: a work graph is, in effect, a **GPU-resident sub-frame-graph** for highly variable workloads (material classification → per-material shade, adaptive tessellation, particle expansion). It naturally scales with the workload (SKILL.md §"Dynamic GPU Autonomy") instead of being sized for worst case.

Fallback chain (graceful degradation per capability query):
- SM 6.9 preview: Work Graphs + Mesh Nodes
- SM 6.8: compute Work Graphs
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
