# K-SYSTEMS · Round 2 findings (Systems Critic, blind)

Scope: concurrency, memory, scheduling, IO, low-level architecture. `check.py` passes with 0 errors and 0 warnings. None of the findings below can be seen by the gate.

### K-SYSTEMS-1 · blocker · obsolete-assumption
- Target: CORE.FRAME.pipelining, CORE.FRAME.phases, frame-orchestration, RND.GPU.recording, gpu-platform-architect, CORE.JOBS.thread-model, legacy L03/L01
- Finding: `CORE.FRAME.pipelining` is labelled E and reads "Frame pipelining with a dedicated game thread and a dedicated render thread". That is legacy pattern L03 (game-thread/render-thread dichotomy) stated as an owned capability. It contradicts §6 of 00-design-principles ("No fixed game, render or RHI threads") and `RND.GPU.recording` ("no dedicated render thread unless ... by ADR"). `CORE.FRAME.phases` ("Tick phases, sync points & phase barriers") also names phase barriers as the default mechanism, while C-FLOW says "global barriers need an ADR". Authority over which threads exist is also split three ways:
  - `CORE.JOBS.thread-model` (job-system) owns the thread inventory.
  - gpu-platform-architect's non-responsibility says "thread existence → frame-orchestration".
  - L03's justification owner is gpu-platform-architect.
  The frame-orchestration agent would build exactly the architecture the brief forbids, and would be citing its own owned capability as the reason.
- Evidence: Naughty Dog's "Parallelizing the Naughty Dog Engine Using Fibers" (Gyrling, GDC 2015) and Destiny's job-based renderer (Tatarchuk/Genova, GDC 2015) pipeline frames without fixed game or render threads. Unity DOTS and Frostbite's FrameGraph treat render work as tasks. A fixed two-thread split caps overlap at two cores, the limit brief item "single-threaded / early Unreal" warns about.
- Proposed change:
  - Rename `CORE.FRAME.pipelining` to "Frame pipelining across simulation, render-prep and GPU as overlapping task-graph frames (pipelining depth in C-FRAME); no fixed game/render thread".
  - Rename `CORE.FRAME.phases` to "Named global sync points (minimal set, each justified by ADR); ordering otherwise derived from C-FRAME access declarations".
  - Make `CORE.JOBS.thread-model` the single authority on which threads exist. Change the gpu-platform-architect non-responsibility to "Thread inventory → job-system-task-graph; frames in flight → frame-orchestration".
  - Make frame-orchestration a co-justification owner of L03, with approval through architecture-governance.

### K-SYSTEMS-2 · major · omission
- Target: RES.MGMT.arbitration (missing), RND.MEM.residency, CORE.MEM.uma, resource-streaming-architect, ray-tracing-infrastructure, geometry-pipeline, render-graph-scheduling, shader-system
- Finding: `RND.MEM.residency` says "(policy in RES.MGMT.arbitration)", but no such capability exists. 00-design-principles §4 and §6 say the cross-pool arbiter in resource-streaming-architect sets residency policy under "one physical budget", but the map has no capability that owns this. M3's exit criterion ("within the arbitration budget") depends on it. The `RES.MGMT.*` capabilities cover per-request streaming only. Several large GPU pools also never consume C-RES, so they never register with any arbiter:
  - ray-tracing-infrastructure (BLAS/TLAS memory; §6 names "BVH pools" explicitly)
  - geometry-pipeline (instance/geometry buffers)
  - render-graph-scheduling (transient heaps)
  - shader-system (PSO caches)
  On UMA consoles and mobile, each pool will then hard-code its own budget, which is the "independent streaming pools that compete" legacy the framework claims to replace.
- Evidence: Frostbite and Decima (Guerrilla, "Streaming the World of Horizon Zero Dawn", GDC 2017) use one memory budget arbitrated across texture, mesh, audio and BVH pools on PS4/PS5 UMA. D3D12 residency (`SetResidencyPriority`, `QueryVideoMemoryInfo` budget callbacks) and VK_EXT_memory_budget report one budget per heap, not per subsystem.
- Proposed change:
  - Add `RES.MGMT.arbitration`: "Cross-pool memory arbitration under one physical budget (CPU, GPU and UMA): pool registration, priority/deadline-weighted eviction, pressure fan-out, shrink requests", owned by resource-streaming-architect, maturity E. Contributors: gpu-memory-resources, memory-allocators, texture-streaming-vt, ray-tracing-infrastructure, audio-dsp-mixing, performance-architect.
  - Add `C-RES` (pool-registration module, e.g. `C-RES@pool`) to the consumes of ray-tracing-infrastructure, geometry-pipeline, render-graph-scheduling (transients) and shader-system (PSO cache).
  - Make `CORE.MEM.uma` report into the arbiter; it must not arbitrate on its own.

### K-SYSTEMS-3 · major · dependency-error
- Target: C-FRAME, C-FLOW, audio-architect, spatial-transforms, scripting-runtime, navigation-pathfinding, ai-behavior-perception, ui-architect, ml-inference-runtime, prediction-rollback, replication
- Finding: The central stance says ordering is derived from declared reads and writes (C-FRAME) and that runtime data moves through channels (C-FLOW). But only **one** skill (render-architect) consumes C-FLOW. Several runtime skills whose work must be ordered or handed across rates declare neither C-FRAME nor a required C-ECS:
  - audio-architect: a real-time audio thread, plus a game→audio command channel and an audio→game clock.
  - spatial-transforms: its own contract promises "per-phase change sets".
  - scripting-runtime: "per-worker VMs, deferred mutation" (L22).
  - navigation-pathfinding and ai-behavior-perception: asynchronous path and perception queries spanning frames.
  - ui-architect: its own update and layout phase.
  - ml-inference-runtime: "scheduling within frame budgets".
  - prediction-rollback: resimulation of N ticks.
  With the dependency undeclared, each agent will invent its own queues, double-buffers and threads. The derived-ordering model then cannot see these accesses, so races and implicit ordering come back silently.
- Evidence: Frame and task-graph schedulers are only as sound as their declarations. Bevy's ambiguity detector and Unity's job safety system can only flag accesses they know about. Audio is the classic undeclared cross-rate channel: the Wwise and FMOD command queues feed a real-time mixer thread.
- Proposed change:
  - Add C-FRAME to consumes for audio-architect, spatial-transforms, scripting-runtime, navigation-pathfinding, ai-behavior-perception, ui-architect, ml-inference-runtime and prediction-rollback.
  - Add C-FLOW to consumes for audio-architect, physics-architect, animation-architect, network-architect/replication, ai-behavior-perception and input-system; these are the multi-rate producers and consumers.
  - Add a check.py rule: every runtime skill at L3 or above whose capabilities schedule per-frame work must consume C-FRAME (or C-ECS non-optionally).

### K-SYSTEMS-4 · major · wrong-boundary
- Target: CORE.FRAME.access-model, CORE.ECS.scheduling, ecs-runtime purpose, frame-orchestration non-responsibilities
- Finding: The frame has two ordering authorities. frame-orchestration owns the "unified access declarations for all phase work ... with derived ordering". But its non-responsibility hands "System ordering inside a phase" to ecs-runtime, and ecs-runtime's purpose includes "system scheduling with access-conflict analysis" (plus `CORE.ECS.safety` "system-order ambiguity detection"). A phase that mixes ECS systems with registered service resources (physics queries, the audio command channel, transform change sets) then has two schedulers deciding conflicts over the same data. In the minimal profile (no ECS), nothing orders work inside a phase.
- Evidence: Unity DOTS mixes ECS-tracked dependencies with manual `JobHandle` chaining for non-ECS data, a well-known source of missed dependencies. Bevy moved to a single executor over systems and resources for this reason.
- Proposed change: frame-orchestration becomes the only scheduler that compiles the per-frame graph and resolves conflicts, both across and inside phases. ecs-runtime only lowers systems to access declarations (`CORE.ECS.scheduling`) and owns ECS-specific ambiguity diagnostics. Replace the frame-orchestration non-responsibility with "ECS query/storage semantics → ecs-runtime", and remove "system scheduling" from the ecs-runtime purpose.

### K-SYSTEMS-5 · major · wrong-owner
- Target: CORE.LIFE.ownership-model, C-LIFETIME, core-runtime-architect, concurrency-primitives, C-SYNC ("safe reclamation"), CORE.CONC.*
- Finding: The framework defines two deferred-reclamation mechanisms with two owners:
  - The C-LIFETIME retirement service keyed to completion tokens. Its implementation belongs to `CORE.LIFE.ownership-model` inside the *lead* core-runtime-architect.
  - "Safe memory reclamation", named in the concurrency-primitives purpose and in the C-SYNC summary. No `CORE.CONC.*` capability owns it.
  These are the same algorithmic problem: epoch- or token-based deferral of frees until every reader or consumer has retired. Implementing them separately duplicates the concurrency-critical code, and the reclamation piece has no validated owner. A lead also ends up implementing hot-path concurrent runtime code, which breaks the leads-arbitrate/experts-implement split.
- Evidence: Epoch-based reclamation (Fraser 2004), hazard pointers (Michael 2004; P2530 in C++26) and GPU-fence retirement queues (the D3D12MA/VMA deferred-free patterns) share one design: a monotonic retire epoch compared against the oldest live consumer. Engines implement one retire queue per token source, not two frameworks.
- Proposed change:
  - Add `CORE.CONC.reclamation` ("Safe memory reclamation: epoch/hazard-pointer and completion-token retirement queues"), owned by concurrency-primitives.
  - Narrow `CORE.LIFE.ownership-model` to *policy* (ownership and cross-thread reference rules), with concurrency-primitives implementing the retirement service. Either move C-LIFETIME to concurrency-primitives, or keep the policy owner and list the implementer explicitly.

### K-SYSTEMS-6 · major · missing-contract
- Target: C-LIFETIME consumers, rhi-core, render-graph-scheduling, texture-streaming-vt, geometry-pipeline, ray-tracing-infrastructure, audio-architect, physics-architect, network-transport
- Finding: C-LIFETIME (retirement keyed to "task completion, frames in flight, GPU fences") has only four consumers: entity-object-model, resource-streaming-architect, gpu-memory-resources and scripting-runtime. rhi-core does not consume it. rhi-core is both the source of GPU fence tokens and the largest user of deferred destruction (descriptors, PSOs, command allocators, query heaps). Other skills that retire memory still referenced by in-flight GPU or async work also skip it:
  - render-graph-scheduling (history resources)
  - texture-streaming-vt and geometry-pipeline (evicted pages still read by in-flight frames)
  - ray-tracing-infrastructure (BLAS compaction and rebuild)
  - audio-architect (voices reading streamed buffers on the mixer thread)
  - physics-architect (bodies referenced by async queries)
  Without the dependency these agents will write frame-count-based `delete-after-N-frames` code, which is L15.
- Evidence: Frame-count retirement breaks under variable frames in flight, async compute spanning frames and suspend/resume. Explicit fence-keyed retirement is standard in D3D12/Vulkan backends (for example the timeline-semaphore deferred-deletion queues in Granite and The Forge).
- Proposed change: Make C-LIFETIME `universal: runtime` (L1, so every L2+ module may consume it), or at minimum add it to the listed skills. Change L15's `justification_owner` from resource-streaming-architect to the C-LIFETIME owner.

### K-SYSTEMS-7 · major · missing-contract
- Target: C-MOD, C-CFG, universal-contract set
- Finding: "No hidden globals: services and self-registration run through an init graph" and "config is read through immutable snapshots" are default stances, but neither contract is universal:
  - C-MOD (module descriptors, init graph, service registration) is consumed by only hot-reload-iteration and plugin-system.
  - C-CFG is consumed by only 7 skills.
  Every runtime skill registers services and reads cvars. Undeclared, agents fall back to static singletons and global cvar reads (L08, L09). The gate then cannot check bootstrap ordering, because the init-graph edges are not in the data.
- Evidence: Parallel boot through an init DAG (as in id Tech 7 and Frostbite service registries) only works when every module declares its dependencies. One undeclared module that self-initializes in a static constructor reintroduces static-init-order bugs.
- Proposed change: Add C-MOD and C-CFG to the `universal: runtime` set for L2+ (both are L1, so there is no layering violation). Extend the acyclic-bootstrap check to cover them.

### K-SYSTEMS-8 · major · dependency-error
- Target: milestones.json (M0–M5), C-LIFETIME, C-FLOW, C-MOD, C-CFG, C-TYPES, C-IO, C-VFS, C-GPUMEM, C-PRESENT, C-DET, C-SNAPSHOT, C-CRASH, C-SCALE, C-IPC
- Finding: Many foundation contracts are never drafted or frozen in any milestone. The list includes C-MOD, C-CFG, C-TYPES, C-CRASH, C-LIFETIME, C-FLOW, C-IO, C-VFS, C-GPUMEM, C-PRESENT, C-DET, C-SNAPSHOT, C-SCALE and C-IPC. M0 freezes C-MEM, C-SYNC and C-TASK, yet C-TYPES, the containers everyone codes against, has no freeze point. M0's exit also requires loading "one cooked asset from a package" (C-IO and C-VFS) and "determinism smoke lanes" (C-DET), none of which is scheduled. For many autonomous agents, an unfrozen foundation contract means continuous churn at the base of the dependency graph.
- Evidence: The framework's own rule is that consumers start against contract-first fakes (`QA.STRAT.contract-fakes`). That rule requires a published freeze schedule for exactly these L1/L2 contracts.
- Proposed change:
  - M0 contracts_frozen: add C-TYPES, C-MOD, C-CFG, C-CRASH, C-LIFETIME. M0 contracts_draft: add C-IO, C-VFS, C-GPUMEM, C-PRESENT, C-FLOW, C-DET, C-SCALE, C-IPC.
  - M1 contracts_frozen: add C-IO, C-VFS, C-FLOW, C-DET, C-SNAPSHOT, C-SCALE, C-IPC. M2 contracts_frozen: add C-GPUMEM and C-PRESENT.
  - Add a gate rule: every contract at layer 0–2 must be frozen by the first milestone whose configuration includes its owner.

### K-SYSTEMS-9 · major · missing-contract
- Target: RES.IO.gpu-decompress, RND.MEM.upload, RND.GRAPH.async, RND.GRAPH.readback, async-io-storage, gpu-memory-resources, render-graph-scheduling
- Finding: The GPU half of the async path (decompress → upload → first use) has no ordering contract.
  - async-io-storage owns GPU decompression but consumes only `C-GPUMEM?`. It does not consume C-RHI or C-RG. Compute-based GDeflate on Vulkan, Metal or consoles without a fixed-function unit is a compute dispatch that must be placed on a queue.
  - gpu-memory-resources owns upload rings (and readback, which overlaps with `RND.GRAPH.readback`).
  - render-graph-scheduling owns multi-queue scheduling.
  Nobody owns copy/async-compute queue arbitration between streaming uploads, GPU decompression, BVH builds, ML passes and the frame graph. Queue-family ownership transfers and acquire barriers at first use (Vulkan) also have no owner. The result is unsynchronized first use, or a global "wait for uploads" barrier.
- Evidence:
  - DirectStorage on PC runs its own queue, but the Vulkan and console paths do not.
  - UE5's RDG and Frostbite both import externally uploaded resources through graph-declared external access with explicit queue-transfer barriers.
  - Vulkan spec §7.7.4 (queue family ownership transfer) requires release and acquire pairs.
- Proposed change:
  - Add `RND.GRAPH.external-work`: "External GPU submissions (streaming uploads, GPU decompression, AS builds): queue arbitration, import/export of externally written resources, ownership transfers and first-use acquire". Owner render-graph-scheduling; contributors async-io-storage, gpu-memory-resources, ray-tracing-infrastructure.
  - Add `C-RHI?` to async-io-storage's consumes for its GPU-decompression module.
  - Keep readback *rings* in gpu-memory-resources, and move the "readback" wording out of `RND.MEM.upload`'s latency ownership: the latency contract stays with `RND.GRAPH.readback`.

### K-SYSTEMS-10 · major · scale-down
- Target: job-system-task-graph, frame-orchestration, platform-web (PLAT.WEB.runtime), platform-mobile, xr-runtime; configurations minimal-client, indie-2d-client (web)
- Finding: No capability owns a host-driven, non-blocking frame loop or a production scheduler degenerate case. On the web, the browser main thread cannot block (`Atomics.wait` is forbidden there), and the frame is driven by `requestAnimationFrame`. Without cross-origin isolation there are no worker threads at all. iOS (CADisplayLink), Android (Choreographer) and OpenXR (`xrWaitFrame`/`xrBeginFrame`) likewise drive or gate the frame from the host. The scheduler must also run efficiently with 1–2 usable cores (low-end mobile, web). `CORE.JOBS.test-modes` provides serial execution *for tests* only. minimal-client and indie-2d-client both target web, so the closure proof passes while the actual execution model for those targets is unowned.
- Evidence: Emscripten documents the main-loop inversion (`emscripten_set_main_loop`) and the prohibition on main-thread blocking waits. Unity WebGL runs a single-threaded job-system fallback. OpenXR 1.0 §10 frame timing requires the app loop to be paced by `xrWaitFrame`.
- Proposed change:
  - Add `CORE.FRAME.host-loop` ("Host-driven frame entry (rAF, display link, Choreographer, xrWaitFrame) with a non-blocking cooperative frame step"), owned by frame-orchestration; contributors platform-web, platform-mobile, xr-runtime.
  - Add `CORE.JOBS.degenerate` ("Production execution with 0–2 workers: inline/cooperative execution, no main-thread blocking waits, yield-to-host"), owned by job-system-task-graph; contributor platform-web.

### K-SYSTEMS-11 · major · maturity-error
- Target: RND.GRAPH.work-graphs, RND.RHI.gpu-work, radar entry "Work graphs & mesh nodes"
- Finding: `RND.GRAPH.work-graphs` is labelled **E** in capabilities.json, while its radar entry classes it **X** ("no shipped titles"). 00-design-principles §7 also treats work graphs as an optional extension. `RND.RHI.gpu-work` (E) bundles "work-graph programs" into an established capability. This makes an experimental GPU execution model a required part of established scheduling ownership. check.py does not compare the radar class with capability maturity, so the gate cannot catch this.
- Evidence: D3D12 Work Graphs 1.0 shipped in 2024. Mesh nodes are still preview, Vulkan has no ratified equivalent (only AMDX), and no shipped-title postmortem exists (see the framework's own gap analysis A6).
- Proposed change:
  - Set `RND.GRAPH.work-graphs` maturity to X.
  - Split `RND.RHI.gpu-work` into `RND.RHI.gpu-work` (indirect and device-generated commands, E) and `RND.RHI.work-graph-programs` (X, added to the radar entry).
  - Add a check.py rule: radar `class` must equal capability maturity. This also exposes `RND.ARCH.multiview`, whose radar class is M while the capability is E.

### K-SYSTEMS-12 · minor · overlap
- Target: CORE.TYPES.codecs, RES.IO.cpu-decompress, RES.PKG.compression, RES.IO.hw-decompress
- Finding: The ownership of the decoder implementation for packaged data is ambiguous. `CORE.TYPES.codecs` is "for non-package users". `RES.PKG.compression` owns codec *selection*, and `RES.IO.cpu-decompress` owns the decompression *stage*. Nobody owns the integration, vetting and SIMD tuning of the package decoders themselves (zstd, LZ4, Kraken class) or their fuzzing surface. That surface is declared untrusted under package-formats-vfs.
- Evidence: A decompressor is the primary fuzz target of any package format (see the zstd and Oodle CVE history). A single owner is needed so the fuzz registration and the implementation match.
- Proposed change: Put all codec implementations (package and non-package) in one library owned by containers-core-types (`CORE.TYPES.codecs`, dropping "non-package"). Keep `RES.PKG.compression` as selection and `RES.IO.cpu-decompress` as stage scheduling only.

### K-SYSTEMS-13 · minor · omission
- Target: PLAT.PAL.lifecycle, PLAT.CON.suspend, async-io-storage, rhi-core, frame-orchestration, network-transport
- Finding: The process lifecycle (suspend, quick-resume, constrained mode) has only platform contributors. The in-flight systems that must quiesce and resume have no declared role:
  - async-io-storage: outstanding IO requests and file handles invalidated on resume
  - rhi-core: GPU idle, and device-lost or recreate on resume
  - frame-orchestration: clock-domain jumps and fixed-step catch-up clamping
  - network-transport: connection loss
  Quick-resume bugs are a leading certification failure and cross every one of these systems.
- Evidence: Xbox Quick Resume and PlayStation rest-mode requirements expect title-side handling of invalidated handles and time discontinuities. Android `onTrimMemory` and the iOS background lifecycle impose the same constraints.
- Proposed change: Add async-io-storage, rhi-core, frame-orchestration and network-transport as contributors to `PLAT.PAL.lifecycle`. Add "suspend/resume quiesce protocol and time-discontinuity handling" to the C-PAL or C-FRAME summary.
