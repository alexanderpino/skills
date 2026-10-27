# K-SYSTEMS · Round 1 · Systems Critic findings

Scope: concurrency, memory, scheduling, IO, low-level architecture and core contract layering. Evidence was gathered from `data/*.json` and `docs/00`. The graph checks below were computed with `scripts/model.py` and are reproducible.

---

### K-SYSTEMS-1 · blocker · dependency-error
- Target: C-PAL, C-ERR, C-MEM, C-INSTR, C-CRASH, C-BUDGET, C-CFG, C-MOD; skills platform-architect, core-runtime-architect, memory-allocators, observability-telemetry, crash-diagnostics, performance-architect
- Finding: Once the implicit `universal: runtime` contracts are counted as dependencies, the foundation has a build-level cycle. `check.py` does not see it, because it checks only the `requires` edges of contracts and never the universal consumption. Computing the skill graph over code contracts plus runtime universals gives one strongly connected component: {platform-architect, core-runtime-architect, memory-allocators, observability-telemetry, crash-diagnostics, performance-architect}. Examples:
  - `memory-allocators → C-INSTR → observability-telemetry → C-MEM → memory-allocators`
  - `platform-architect` (provides L0 `C-PAL`) implicitly consumes the L1 contracts C-ERR, C-MEM, C-INSTR, C-CRASH and C-BUDGET. That is an upward dependency out of layer 0.
  - `C-BUDGET → C-CFG`, and C-CFG's implementation consumes C-MEM (universal), whose owner consumes C-BUDGET (universal).
  
  A second bootstrap problem sits alongside it. `CORE.LIFE.boot` is "parallel boot via init dependency graph", but `C-MOD` does not require `C-TASK`, and the job system is itself a module that C-MOD initializes. Nothing states who runs the boot before workers exist.
- Evidence: These are the first six skills any agent swarm builds. With a cycle, no agent can freeze its API first, and each will invent a private logging, assert or allocation shim. That is exactly the "hidden globals" pattern §6 forbids. Shipping engines break the cycle with an explicit bootstrap tier: a raw OS page allocator and a raw log/assert sink inside the platform layer, plus late-bound hook tables (allocator hook, log sink, assert handler, crash annotator) that higher layers install at init. Examples are UE's `FPlatformMemory`/`FMallocBinned` split with `GLog` redirection, and the hook-based design of the EASTL/EABase allocator.
- Proposed change: (a) Add contract `C-BASE` (L0, owner platform-architect). It holds a raw page allocator, a raw sink for log/assert/abort, a monotonic clock and thread primitives, and it requires nothing. (b) Redefine `C-MEM`, `C-INSTR`, `C-CRASH` and `C-ERR` as hook interfaces over C-BASE whose implementations bind late. (c) Make universals apply only to skills whose lowest provided contract layer is ≥ 2. Skills at L0 and L1 must list what they consume explicitly, and those lists must be acyclic. (d) Add capability `CORE.LIFE.bootstrap` ("Serial bootstrap phase until the scheduler is live; the hand-off to parallel init") under core-runtime-architect, and make `C-MOD` require `C-TASK`. (e) Extend `check.py` to include universal edges in the cycle and layering checks.

### K-SYSTEMS-2 · major · dependency-error
- Target: determinism-replay (C-DET L1 → C-SER L2), ml-inference-runtime (C-ML L2 → C-RG L3), shader-system (C-SHADER L3 → C-COOK L5), material-system (C-MATIF L3 → C-GRAPH? L5), localization-i18n (C-LOC L3 → C-COOK? L5), platform-architect (see K-SYSTEMS-1)
- Finding: The layering rule is enforced only on contract `requires`, not on what the skill that *provides* a contract consumes. Six skills provide a lower-layer contract while consuming a higher-layer one. Unless the skill is split into separate modules, the runtime module behind the lower-layer contract links against the higher layer. Two cases matter most:
  - `C-DET` sits at L1 and is consumed by physics and math, yet its owner needs `C-SER` (L2) for record/replay.
  - `C-ML` sits at L2 but needs the render graph (L3) for scheduling. It also requires `C-RHI` outright, so no configuration without a GPU can run CPU inference (for example learned AI on a dedicated server).
- Evidence: "Format owner vs pipeline host" (§4) is a legitimate reason for one *skill* to span runtime and cook. It is not a reason for one *module* to span layers. Nothing in the data records that the skill ships two modules, so an agent will build one.
- Proposed change: Add a skill field `modules: [{contract, layer}]`, or split the contracts, and make `check.py` verify that every consumed contract is at or below the layer of the module that consumes it. Specific fixes:
  - Split `C-DET` into `C-DET` (L1: rules, FP policy, state-hash hooks) and `C-REPLAY` (L3: record/replay, desync reports; requires C-SER, C-INPUT).
  - Move `C-ML` to L3, make `C-RHI`/`C-RG` optional, and add a CPU-only backend path so dedicated-server can use it.
  - Declare the shader, material and localization cook-side modules as L5 modules of their skills.

### K-SYSTEMS-3 · major · wrong-boundary
- Target: CORE.JOBS.graph (job-system-task-graph), CORE.FRAME.phases (frame-orchestration), CORE.ECS.scheduling (ecs-runtime), RND.ARCH.threading (render-architect), ANM.ARCH.pipeline, AUD.ARCH.engine, PHY.DYN.parallel, ML.RT.scheduling, GAM.AI.lod; contracts C-TASK, C-FRAME, C-ECS
- Finding: Three schedulers are named, and ordering authority is only partly split among them.
  - frame-orchestration owns the phase list and delegates "System ordering inside a phase" to ecs-runtime.
  - ecs-runtime's access-conflict analysis covers only ECS component and singleton access.
  - Nobody owns ordering or conflict detection *inside a phase* for non-ECS work: the physics world step, animation evaluation, render extraction, audio parameter update, the spatial-index rebuild, network send/receive and ML inference jobs. Their data (the physics world, the spatial index, the render scene, the pose buffers) are services, not ECS components (§6 hybrid model).
  - The runtime cycles resolved "through frame phases" (animation↔physics and others) need exactly this ordering, and it has no owner.
  - In addition, frame pipelining (frame-orchestration) and "render threading model" (render-architect) overlap on who decides whether a render thread exists and how many frames are in flight.
- Evidence: Races between ECS systems and non-ECS subsystems are the classic failure of hybrid engines. Unity DOTS had to add JobHandle dependency chaining alongside the system dependency graph. Bevy models non-component state as `Resource`s so its scheduler can see the conflicts. Destiny's (Bungie, GDC 2015 "Multithreading the Entire Destiny Engine") and Naughty Dog's (GDC 2015 "Parallelizing the Naughty Dog Engine Using Fibers") frame graphs are single authorities over all jobs in a frame. Without one access-declaration model, each lead invents its own ordering and the conflicts show up only under TSan or in soak testing.
- Proposed change:
  - Add capability `CORE.FRAME.access-model`, owned by frame-orchestration with ecs-runtime as contributor: "Unified access declaration for all phase work (ECS components, singletons *and* registered service resources such as the physics world, spatial index and render scene) with conflict analysis and ordering within phases".
  - Narrow `CORE.ECS.scheduling` to "lowering ECS systems into the unified phase model".
  - Make `C-FRAME` expose resource access declarations, and require every skill that runs per-frame work to declare its phase placement and accesses through it.
  - Move the "frames in flight / render-thread existence" decision out of `RND.ARCH.threading` into `CORE.FRAME.pipelining`. render-architect keeps parallel command recording only.

### K-SYSTEMS-4 · major · omission
- Target: CORE.JOBS.*, PLAT.PAL.os, AUD.ARCH.engine, RND.ARCH.threading, crosscutting "concurrency"
- Finding: No capability owns the engine's *thread inventory and core allocation*. The engine needs, among others:
  - worker pools sized per tier;
  - dedicated or long-lived threads (the real-time audio device callback, IO completion, render submit/present, network receive, the OS-affine main/UI thread for the Win32 pump, Cocoa, Android looper and the iOS main queue);
  - reserved cores on consoles;
  - a mapping of each thread to OS priority and QoS class (MMCSS on Windows, Apple QoS classes, Android thread priorities and ADPF hints, SCHED_* on Linux servers);
  - rules for which threads may block, allocate or take locks (audio RT threads must never block on a job or allocate);
  - priority-inversion policy.
  
  `CORE.JOBS.priorities` covers task priority inside the scheduler, not OS threads. The cross-cutting "concurrency" obligation is assigned to concurrency-primitives, which owns atomics and locks, not placement. Without an owner, audio, render, IO and network will each create their own threads, oversubscribe hybrid CPUs and bypass P/E-core placement.
- Evidence: On console-class hardware, titles are given a fixed set of cores with OS reservations. Intel Thread Director and Apple AMP route work by QoS class, so a thread with the wrong class lands on E-cores. Audio glitches from priority inversion are a well-known shipping bug class (Ross Bencina, "Real-time audio programming 101: time waits for nothing"). Every high-end engine keeps a central thread registry (for example UE's named threads plus `FRunnableThread` priorities).
- Proposed change:
  - Add `CORE.JOBS.thread-model` ("Engine thread inventory, core reservation, OS priority/QoS mapping, OS-thread-affine work marshaling, real-time thread rules and priority-inversion policy"). Owner: job-system-task-graph; contributors: platform-architect, audio-architect, render-architect.
  - Reassign the cross-cutting "concurrency" obligation's *threading model / placement* half to job-system-task-graph, and keep the synchronization-review half with concurrency-primitives.
  - Add `PLAT.PAL.threads` ("thread creation, affinity and QoS APIs per OS, main-thread dispatch") under platform-architect.

### K-SYSTEMS-5 · major · wrong-boundary
- Target: RES.MGMT.streaming (resource-streaming-architect), RND.MEM.residency / RND.MEM.budget (gpu-memory-resources), CORE.MEM.uma / CORE.MEM.oom / CORE.MEM.budget-enforcement (memory-allocators), RND.TEX.mip-streaming, RND.LOD.streaming, AUD.DSP.streaming, PRF.METH.budgets; contract C-RES
- Finding: At least five eviction and budget loops exist with no arbiter between them:
  - the streaming manager's budgets and eviction;
  - GPU residency and overcommit;
  - texture mip and VT page pools (texture-streaming-vt);
  - virtualized-geometry page pools;
  - audio streaming, plus RT acceleration-structure memory and ML weights.
  
  On UMA consoles, mobile and Apple silicon all of these draw from one physical pool. On discrete PCs, VRAM pressure is signalled by the OS (DXGI `QueryVideoMemoryInfo` budget changes; Vulkan `VK_EXT_memory_budget`). Nobody owns runtime arbitration between pools, such as "evict texture mips to make room for BVH growth". `resource-streaming-architect` does not even consume `C-GPUMEM`, so the "streaming manager (budgets, eviction)" cannot see GPU memory. OS memory-pressure notifications are also unowned: iOS memory warnings/jetsam, Android `onTrimMemory`, Windows low-memory notification, and the console title-memory limit.
- Evidence: Frostbite, UE's texture streaming plus Nanite page pool, and Snowdrop each ended up with a central memory-pressure/priority broker because independent pools oscillate or deadlock (one pool refuses to shrink while another starves). UE's `r.Streaming.PoolSize` and Nanite streaming pool have documented interference, and UE5 later introduced shared budget handling. The mission brief explicitly lists "GPU/CPU shared budgets" and UMA.
- Proposed change:
  - Add `RES.MGMT.pressure` ("Cross-pool memory-pressure arbitration: CPU heap, GPU local, UMA; priority-based eviction requests to pool owners; OS memory-pressure signal handling"), owned by resource-streaming-architect, with contributors memory-allocators, gpu-memory-resources, performance-architect and platform-architect.
  - Add `C-GPUMEM` (budget queries only, via a narrow `C-MEMBUDGET-GPU` view) to resource-streaming-architect's consumes.
  - Reword `RND.MEM.residency` to "residency *mechanism* and budget reporting". The *policy* moves to the arbiter, following the §4 policy-vs-implementation pattern.
  - Add a C-RES clause that makes every pool owner implement a "shrink to N bytes by deadline" request.

### K-SYSTEMS-6 · major · missing-contract
- Target: C-IO, C-VFS, C-SER, C-RES, C-GPUMEM; RES.PKG.compression, RES.IO.gpu-decompress, CORE.SER.relocatable, RND.MEM.upload
- Finding: The async load path IO → decompression → deserialization/fixup → GPU upload → publish/residency is spread across five owners, and no contract defines the *staged pipeline* between them.
  - CPU decompression has no owner. package-formats-vfs owns codec *selection* only, and async-io-storage owns *GPU* decompression only. Hardware decompression units on consoles and DirectStorage CPU fallback decode are also unassigned.
  - There is no resource-type loader contract stating the stages a type handler implements (read, decompress, fixup, upload, finalize) and on which queues and threads each runs.
  - In-flight staging memory (IO buffers, decompression scratch, upload rings) has no budget owner.
  - "Publish to simulation" (when a loaded asset becomes visible to game phases) is not tied to a C-FRAME phase.
  - C-RES summarizes the whole path as "residency callbacks".
- Evidence: DirectStorage 1.1+ and the PS5 IO complex require the engine to express loads as batched requests with a GPU or hardware destination and a completion fence. A pipeline defined as ad hoc callbacks cannot reach NVMe throughput or avoid main-thread hitches; UE's IoStore/Zen loader rewrite existed precisely to replace per-type async loading with a staged, batched pipeline ("Zen Loader", Unreal Fest 2022). The same codecs (zstd/LZ4/Oodle class) are also needed by the DDC, saves, crash upload, replay files and network snapshots. Only packages have an owner.
- Proposed change:
  - Add `RES.MGMT.pipeline` ("Staged load pipeline: request → IO → decompress → fixup → GPU upload → publish; per-stage queues, staging-memory budget, batching, cancellation"), owned by resource-streaming-architect.
  - Add `RES.IO.cpu-decompress` ("CPU and hardware-unit decompression as an IO stage"), owned by async-io-storage.
  - Add `CORE.TYPES.codecs` ("General-purpose compression codec library for non-package users"), owned by containers-core-types. package-formats-vfs keeps selection for packages.
  - Add contract `C-LOADER` (L3, owner resource-streaming-architect, requires C-RES, C-GPUMEM?, C-FRAME) that every resource type implements.
  - Add a C-FRAME phase "resource publish".

### K-SYSTEMS-7 · major · omission
- Target: PLAT.PAL.os, ED.ARCH.process, ED.ARCH.remote, CNT.COOK.distributed, RND.SHADER.cache, OBS.LOG.remote, OBS.CRASH.capture, GAM.SCR.debug, BLD.CI.devices
- Finding: No capability owns process management or IPC/local RPC. At least eight consumers need them:
  - an out-of-process editor↔runtime link (shared memory plus a message channel);
  - remote on-device live editing;
  - distributed and local cook worker processes;
  - shader compiler worker processes;
  - an out-of-process crash handler (crashpad-class; a crashing process cannot reliably report itself);
  - the profiler connection (Tracy/Perfetto-class);
  - the script debugger (DAP over a socket);
  - device-farm automation control.
  
  `PLAT.PAL.os` lists threads, VM, files, time and dynamic libraries, but not processes, pipes, shared memory or sockets. The only socket owner is network-transport, which is profile `online`/`server` only, so indie-2d has *no* skill that can open a dev socket for profiling or remote debugging.
- Evidence: UE (UnrealTrace server, ShaderCompileWorker, CrashReportClient, Zen server), Unity (out-of-process AssetImportWorkers) and Chromium (crashpad) all run a multi-process development model over shared IPC infrastructure. Leave it unowned and each of the eight consumers will build its own transport, with its own security posture: these ports are an attack surface on dev kits.
- Proposed change:
  - Add `PLAT.PAL.process` ("Process spawn/supervision, pipes, shared memory, local and dev sockets, HTTP(S) client primitive"), owned by platform-architect.
  - Add `CORE.LIFE.ipc` ("Engine IPC/RPC transport and process model for tools, workers, crash handler and profiler; dev-only port security"), owned by core-runtime-architect, with contributors editor-architect, crash-diagnostics and security-engineering.
  - Add contract `C-IPC` (L2, requires C-PAL, C-TASK, C-SER), consumed by editor-architect, content-pipeline-architect, shader-system, observability-telemetry, crash-diagnostics and scripting-runtime.

### K-SYSTEMS-8 · major · missing-contract
- Target: C-FRAME, C-RHI, C-TASK; CORE.FRAME.latency, CORE.FRAME.pipelining, CORE.JOBS.completions, RND.RHI.present
- Finding: frame-orchestration owns frame pipelining across simulation, render *and GPU* and owns "input-to-photon latency & frame pacing (Reflex / Anti-Lag class)". Yet `C-FRAME` requires only `C-TASK`, frame-orchestration does not consume `C-RHI`, and rhi-core does not consume `C-FRAME`. No declared path lets GPU completion, present timing or latency markers reach the pacer. That is correct for servers (rhi-core is client-only), but it means the needed interface is unstated. The same applies to `CORE.JOBS.completions`: C-TASK (L1) integrates "IO & GPU completion" from L2 owners with no layer-1 waitable abstraction declared for it.
- Evidence: Reflex and Anti-Lag 2 need sim-start, render-submit and present markers plus a pacing sleep issued from the frame loop. Frame pacing on VRR and fixed-refresh displays needs present statistics (`DXGI_FRAME_STATISTICS`, `VK_GOOGLE_display_timing` / `VK_KHR_present_wait`, Android Swappy). Without a declared inverted interface, an agent will either make C-FRAME depend on C-RHI, which breaks server scale-down, or poll on the render thread, which is the legacy pattern.
- Proposed change:
  - Add to `C-FRAME` a *provided* "frame pacing/present-feedback sink" interface: markers, GPU-frame-complete and present-time events. `rhi-core` consumes `C-FRAME` and implements it (dependency inversion).
  - Add to `C-SYNC` (L1) an OS-waitable/completion-token abstraction that C-TASK integrates, so IO and GPU fences plug in from L2 without an upward edge.
  - Add `CORE.FRAME.pacing-feedback` under frame-orchestration, with rhi-core and platform-desktop as contributors.

### K-SYSTEMS-9 · major · omission
- Target: CORE.OBJ.references, CORE.TYPES.ownership, CORE.CONC.reclamation, RES.MGMT.handles, RND.MEM.lifetime, CORE.ECS.structural; core-runtime-architect
- Finding: Lifetime rules are defined per domain, with no engine-wide ownership and deferred-destruction model:
  - entities: generational IDs plus structural-change command buffers;
  - resources: handles;
  - GPU objects: fence-deferred release;
  - lock-free structures: epochs and hazard pointers;
  - the script GC.
  
  Nothing owns the rules that make these compose:
  - which reference kinds may cross threads or phase boundaries (handle vs raw pointer vs span);
  - when a destroy request takes effect relative to in-flight jobs, frames in flight (C-FRAME pipelining depth) and GPU fences;
  - the retirement order when an asset unload, an entity destroy and a GPU release all depend on one another.
  
  §6 claims "resource lifetimes are explicit and independent of frame boundaries", but only GPU and streaming resources have an owner for that.
- Evidence: Use-after-free across the sim/render boundary is the dominant crash class in multithreaded engines (UE's render-proxy and `FGCObject` lifetime rules exist for exactly this). A single epoch/retirement service tied to frame and GPU timelines is the established fix. Destiny's and Frostbite's handle-only cross-thread rules make the same point (Tatarchuk et al., "Destiny's Multithreaded Rendering Architecture", GDC 2015).
- Proposed change: Add `CORE.LIFE.ownership-model` ("Engine-wide ownership and cross-thread reference rules; unified deferred-destruction/retirement service keyed to task completion, frame-in-flight and GPU-fence timelines"), owned by core-runtime-architect, with contributors entity-object-model, resource-streaming-architect, gpu-memory-resources, concurrency-primitives and scripting-runtime. Expose it in `C-MOD` or a new `C-LIFETIME` (L1).

### K-SYSTEMS-10 · major · wrong-boundary
- Target: C-SPATIAL, C-PHYS, C-ANIM, C-AUDIO (each requires or consumes C-ECS); CORE.OBJ.hybrid; §3 replaceability claim
- Finding: Four foundational subsystem contracts hard-require `C-ECS`. This contradicts two stated principles. The hybrid, "not dogmatic" object model (§6) is undermined because transforms, physics, audio emitters and animation poses become unusable outside ECS (editor tools, UI world anchors, services). The replaceability claim ("`C-PHYS` can be served by an integrated middleware … without touching consumers", §3) fails because middleware such as Jolt, PhysX or Havok cannot implement an ECS-bound contract. It also forces ECS into every configuration, including indie-2d and dedicated-server, even where the policy might choose otherwise.
- Evidence: Production physics and audio middleware are ECS-agnostic, and engines bind them through adapter layers: Unity Physics/Havok via DOTS baking systems, UE Chaos via proxies, Bevy via plugin systems. Placing the ECS binding in the core contract couples a replaceable subsystem to the ECS storage choice (archetype vs sparse set), which §9 leaves open.
- Proposed change: Remove `C-ECS` from the `requires` of `C-SPATIAL`, `C-PHYS`, `C-ANIM` and `C-AUDIO`. Each becomes an ECS-independent data/service contract (handles and batched SoA APIs). Add per-domain ECS adapter capabilities: `PHY.ARCH.ecs-binding`, `WLD.SPACE.ecs-binding`, `ANM.ARCH.ecs-binding` and `AUD.ARCH.ecs-binding`, owned by the respective leads, all consuming `C-ECS`. Adapters are configuration-optional.

### K-SYSTEMS-11 · major · overlap
- Target: CORE.LIFE.language (core-runtime-architect), ARCH.GOV.coding-standard (architecture-governance), XC.SEC.coding (security-engineering), CORE.MEM.debugging (memory-allocators), QA.ROBUST.sanitizers (robustness-fuzzing)
- Finding: Language and memory-safety posture has three owners: language standard plus exceptions/RTTI policy, "coding standard & language subset", and "secure coding & memory-safety policy". Two agents can legitimately issue conflicting rules on the same question, for example whether bounds-checked containers or hardened libc++ are on in shipping builds, or whether exceptions are banned. The map also has no capability for the currently demonstrated memory-safety measures:
  - hardened standard library modes (libc++ hardening, `_GLIBCXX_ASSERTIONS`);
  - `-fbounds-safety` / `std::span` bounds checks;
  - a memory-safe language option for untrusted-input parsers (packets, saves, mods), as in the Chromium "Rule of Two" and Android Rust adoption;
  - hardware memory tagging (Arm MTE on mobile).
- Evidence: CISA/NSA memory-safety guidance (2023–2024) and Android's reported fall in memory-safety CVEs after moving new parsers to Rust are current production evidence. Game engines parse untrusted packets, saves and mods (C-TRUST lists them), which is exactly where this applies.
- Proposed change: Merge `ARCH.GOV.coding-standard` into `CORE.LIFE.language`, owned by core-runtime-architect. architecture-governance keeps only enforcement via fitness functions. Keep `XC.SEC.coding` as *requirements*, with security-engineering listed as a contributor to CORE.LIFE.language, not a second owner. Add `XC.SEC.memory-safety` ("Memory-safety posture: hardened STL modes, bounds checking in shipping, memory-safe-language option for untrusted parsers, MTE/PAC use"), maturity M, owned by security-engineering.

### K-SYSTEMS-12 · major · omission
- Target: QA.ROBUST.concurrency, QA.STRAT.frameworks, C-TASK, C-IO, C-FRAME, OBS.LOG.tracing, PRF.CPU.contention
- Finding: Systems-level testability and observability seams are not contract obligations. No contract requires:
  - a deterministic or serial execution mode in `C-TASK` (needed for reproducible tests, schedule perturbation, single-threaded web/WASM-without-threads targets and debugging);
  - injectable clocks in `C-FRAME` or C-PAL time;
  - fake or fault-injecting backends for `C-IO`, which `QA.ROBUST.faults` assumes exist;
  - scheduler introspection: per-task tracing, frame task-graph critical-path analysis, worker idle/steal statistics, OS context-switch and core-migration capture (ETW, perf sched, Perfetto).
  
  robustness-fuzzing owns "schedule perturbation", but nothing obliges job-system-task-graph to expose the hooks it needs. Critical-path analysis of the frame graph, the key metric for many-core scaling, has no owner.
- Evidence: Deterministic simulation testing (FoundationDB; TigerBeetle's VOPR) and seeded schedule fuzzing (Loom, Coyote) rely on exactly these seams. Naughty Dog's and Bungie's job-system talks both centre on critical-path and idle visualization as the tool that made parallelism tractable.
- Proposed change: Add `CORE.JOBS.test-modes` ("Serial/deterministic execution mode, seeded schedule perturbation hooks"). Add `CORE.JOBS.introspection` ("Task-level tracing, critical-path and utilization analysis, OS scheduler event correlation"), owned by job-system-task-graph with observability-telemetry as contributor. Add C-PAL/C-FRAME clause "clock injectable" and C-IO clause "pluggable backend incl. fault-injecting". Add these seams to `C-TEST`'s definition of done for L0–L2 skills.

### K-SYSTEMS-13 · major · omission
- Target: PLAT.MOB.thermal, PRF.CPU.hybrid, PRF.GPU.power, RND.RECON.dynres, CORE.FRAME.latency, CORE.JOBS.priorities, PLAT.DESK.handheld
- Finding: Power, thermal and QoS behavior is split across five capabilities. Three of them belong to reviewers (the performance experts), who by §8 do not own code. No one owns the *runtime governor*: the closed-loop controller that consumes platform performance hints and thermal headroom and sets frame-rate caps, dynamic-resolution targets, worker count and P/E placement, and simulation-LOD pressure. The platform APIs it consumes include Android ADPF (`PerformanceHintManager`, thermal headroom), Apple thermal state and QoS, Windows EcoQoS/power throttling and Game Mode, and the handheld TDP of Steam Deck/ROG Ally-class devices. Scaling down to mobile, portable and handheld depends on it.
- Evidence: Android ADPF is the Google-recommended path for sustained performance. Mobile titles (Genshin, CoD Mobile) ship adaptive governors. Console portables and handheld PCs expose power modes. Without one owner, dynres (reconstruction-upscaling), job placement (job-system) and thermal handling (platform-mobile) run three uncoordinated control loops.
- Proposed change: Add `CORE.FRAME.governor` ("Runtime performance/power governor: consumes thermal/power/perf-hint signals and budgets; drives frame-rate cap, dynres target, worker count/placement and sim-LOD pressure"), owned by frame-orchestration, with contributors platform-mobile-portable, platform-desktop, reconstruction-upscaling, job-system-task-graph and performance-architect. Add `PLAT.PAL.power` ("Power, thermal and performance-hint APIs") under platform-architect.

### K-SYSTEMS-14 · minor · wrong-owner
- Target: C-BUDGET (owner performance-architect, universal runtime, L1)
- Finding: A runtime code contract (scalability hooks, device profiles) is owned by a cross-cutting reviewer skill that §8 says "does not own the code". C-BUDGET also mixes that runtime API with process data ("perf gate thresholds"). As a result, performance-architect is a runtime skill inside the foundation cycle (K-SYSTEMS-1).
- Evidence: The policy-vs-implementation pattern (§4) already puts budget *numbers* with performance-architect and enforcement with memory-allocators. The runtime scalability and device-profile hook is configuration machinery.
- Proposed change: Split C-BUDGET into two:
  - a runtime `C-SCALE` (L1): device profiles, scalability cvars, budget query and report API, owned by core-runtime-architect next to C-CFG;
  - a process `C-BUDGET` (layer P): budget numbers per tier and gate thresholds, owned by performance-architect.
  
  Set performance-architect `runtime: false`.

### K-SYSTEMS-15 · minor · omission
- Target: CORE.TYPES.hashing, RES.PKG.crypto, NET.TRANS.crypto, XC.SEC.supply-chain, CNT.COOK.ddc, GAM.SAVE.atomic
- Finding: No owner for the shared cryptographic primitives: cryptographic hashes (SHA-256/BLAKE3), AEAD, signatures and CSPRNG. Package signing (package-formats-vfs), transport encryption (network-transport, online/server profile only), save-integrity checks, DDC and content-addressed keys, and telemetry and crash upload over TLS each need them, so at least two implementations will be built. Also unowned is the rule that stable hash algorithms and seeds are versioned across builds and platforms, which is needed for DDC keys and replay compatibility.
- Evidence: Mixing crypto implementations is a standard source of security defects. A silent hash-algorithm change invalidates every DDC entry and breaks cross-build replay (XC.DET.compat).
- Proposed change: Add `CORE.TYPES.crypto` ("Vetted cryptographic primitives wrapper, CSPRNG; selection per platform"), owned by containers-core-types with security-engineering as contributor. Extend `CORE.TYPES.hashing` to "…with versioned algorithm and seed stability guarantees".

### K-SYSTEMS-16 · minor · omission
- Target: PLAT.PAL.os, CORE.FRAME.time, NET.PRED.clock, INP.ACT.latency, RND.RHI.queries, AUD.ARCH.devices
- Finding: The raw-clock and clock-domain correlation layer has no owner. The engine needs a monotonic high-resolution clock and a steady wall clock, plus correlation between the CPU clock and the GPU timestamp domain (`VK_KHR_calibrated_timestamps`, D3D12 `GetClockCalibration`), the audio device sample clock (drift), display vblank/present time, input-event OS timestamps and server time. Input latency accounting, A/V sync, profiler CPU/GPU alignment and network clock sync all depend on it. `CORE.FRAME.time` covers game time domains, and "time" in PAL.os is undifferentiated.
- Evidence: Profilers such as PIX, Tracy and Perfetto require calibrated timestamps to align CPU and GPU tracks. Audio/video drift in long cutscenes is a known shipping bug when the audio clock is not the master.
- Proposed change: Add `PLAT.PAL.clocks` ("Monotonic/high-resolution clocks, sleep and timer precision, hardware clock-domain correlation: CPU↔GPU↔audio↔display↔input"), owned by platform-architect, with contributors rhi-core, audio-architect and frame-orchestration. `CORE.FRAME.time` consumes it.

### K-SYSTEMS-17 · minor · omission
- Target: PLAT.PAL.os, OBS.CRASH.capture, GAM.SCR.vm, XC.SEC.anticheat, QA.ROBUST.sanitizers, CORE.JOBS.fibers, RES.MGMT.reload
- Finding: Several low-level OS integrations have no owner:
  - **Signal and structured-exception handler chaining.** The crash handler, script VMs (Mono/.NET/LuaJIT use signals or SEH), anti-cheat middleware, sanitizers and the GPU driver all install handlers, and the order in which they chain is not owned.
  - **Fiber awareness in tooling.** When a task migrates between threads, `thread_local` access becomes unsafe and debuggers and crash stack walks lose the logical call stack. ASan and TSan also need fiber-switch annotations. None of this is an obligation of crash-diagnostics, observability or robustness-fuzzing.
  - **Platform file-system change notification** (inotify, ReadDirectoryChangesW, FSEvents), which hot reload and the editor asset browser both depend on.
- Evidence: Handler-chaining conflicts are a recurring integration bug with Mono/Unity and anti-cheat drivers. Naughty Dog's fiber talk records the TLS hazard and the tooling work it forced.
- Proposed change:
  - Add `PLAT.PAL.signals` ("Signal/SEH handler registry and chaining order") under platform-architect, with crash-diagnostics as contributor.
  - Add `PLAT.PAL.fs-watch` under platform-architect, with hot-reload-iteration as contributor.
  - Add to `CORE.JOBS.fibers` the contributors crash-diagnostics, observability-telemetry and robustness-fuzzing, plus an obligation note: "fiber-safe TLS rules; debugger/profiler/sanitizer fiber annotations".

### K-SYSTEMS-18 · minor · dependency-error
- Target: ml-inference-runtime (profile `aaa`, consumes C-RHI required), GAM.AI.learned, AUD (ML audio), dedicated-server configuration
- Finding: The one inference runtime (§8: "one inference runtime with one budget") hard-requires `C-RHI`, which is client-only, and belongs to profile `aaa` only. CPU inference therefore cannot exist in the dedicated-server configuration or in non-AAA configurations. Examples are learned AI or anti-cheat anomaly models on the server, and small ML denoisers or audio models on mobile via NPU. NPUs, a current heterogeneous-hardware trend (Apple ANE, Qualcomm Hexagon, Intel/AMD NPUs via DirectML/ONNX EPs), are also absent from `ML.RT.inference`.
- Evidence: CPU and NPU inference runtimes (ONNX Runtime, Core ML, NNAPI/LiteRT) are established production components independent of a graphics device.
- Proposed change: Make `C-RHI` and `C-RG` optional in ml-inference-runtime, and add profiles `server` and `mobile3d`, or split the CPU/NPU backend into a separately tagged module. Add `ML.RT.npu` ("NPU backends via platform ML APIs") at maturity M. See also K-SYSTEMS-2 on moving C-ML to L3.
