# K-PERF · Performance Critic · Round 3

### K-PERF-1 · major · obsolete-assumption
- **Target:** PRF.METH.budgets, C-BUDGET, performance-architect
- **Finding:** PRF.METH.budgets says budgets are "measured on the reference high-end PC and scaled proportionally to lower tiers". That is the old one-reference-machine model, and it contradicts C-BUDGET, which says budgets are per hardware tier × configuration × refresh class and come from the performance model. Scaling one number proportionally assumes every tier has the same bottleneck. That is wrong for TBDR mobile, where bandwidth and on-chip tile memory dominate. It is wrong for UMA consoles and portables, where one physical memory pool is shared with the OS reserve. It is wrong for thermally throttled handhelds, where sustained clocks are well below peak. It is wrong for fixed-hardware consoles, whose budgets are absolute per SKU. It is wrong for servers, which have tick and CCU budgets.
- **Evidence:** Budgets in console-certification practice are absolute per SKU (memory reserve, frame time). Arm and Qualcomm mobile best-practice guides give bandwidth-per-frame budgets that have no PC counterpart. Android ADPF and Apple thermal-state documentation show that sustained performance differs from peak. The framework's own RND.ARCH.submission-strategy says the bottleneck differs per tier, so proportional scaling contradicts its own premise.
- **Proposed change:** Rename PRF.METH.budgets to "Budgets per hardware tier × configuration × refresh class, measured on each tier's reference device at thermally sustained state, derived from PRF.METH.model and reconciled against measurement; no cross-tier proportional scaling". Add legacy pattern L58 "Single reference-machine budgets scaled down" with stance capability PRF.METH.budgets.

### K-PERF-2 · major · obsolete-assumption
- **Target:** CORE.JOBS.blocking, job-system-task-graph, C-TASK
- **Finding:** CORE.JOBS.blocking requires blocking and long-running tasks to run inline on work-stealing workers, with no dedicated lanes and no compensating threads. A blocking task (OS-bound call, middleware wait, network or file API without an async form) parks a worker. A long-running task (navmesh rebuild, PCG, shader compile in the editor, AS builds) holds a worker across frames. On a 6–8 worker console or a 2-worker web or low-end tier this takes frame-critical parallelism away and causes frame-time spikes and priority inversion. It also contradicts CORE.JOBS.priorities (latency-critical lanes), CORE.JOBS.pinned and RES.MGMT.no-stall.
- **Evidence:** Intel oneTBB and the C++ executors guidance say not to block inside tasks. Go's scheduler hands off its P on a blocking syscall. The .NET thread pool injects compensating threads. Naughty Dog, "Parallelizing the Naughty Dog Engine Using Fibers" (GDC 2015), switches fibers on waits and never blocks a worker. Unreal's task system has separate background priorities and a dedicated thread pool for long work.
- **Proposed change:** Rewrite CORE.JOBS.blocking to: "Blocking and long-running work: waits yield (fiber/continuation) and never park a worker; OS-blocking calls go to a bounded blocking lane or compensation policy recorded in the thread inventory; long-running work runs in background QoS lanes with preemption points; frame-critical lanes are never starved". Add the blocking rule to C-TASK conformance, and add a legacy pattern "Blocking inside work-stealing workers" whose stance capabilities are CORE.JOBS.blocking and CORE.JOBS.priorities.

### K-PERF-3 · major · wrong-boundary
- **Target:** CORE.OBJ.events, entity-object-model, legacy pattern L19, C-FLOW, C-FRAME
- **Finding:** CORE.OBJ.events is defined as a "global event bus with immediate synchronous listener dispatch by default". That is legacy pattern L19 (immediate synchronous observer callbacks), and the capability is also listed as L19's own stance capability. A global bus with synchronous dispatch is a hidden serialization point. Listeners run on the producer's thread in the middle of a phase and write data the access model never saw. This defeats derived ordering (CORE.FRAME.access-model) and phase-violation detection. It also forces locks or a single thread, and its cost scales with listener count on the hot path.
- **Evidence:** The framework's own principles (§3: data flows through C-FLOW channels, and a global barrier needs an ADR) and its L19 stance ("deferred batched events at declared consumption points"). Unity DOTS and Bevy use buffered events that are read in declared systems. Timothy Ford, "Overwatch Gameplay Architecture and Netcode" (GDC 2017), explains why deferred effects are needed to keep ordering deterministic.
- **Proposed change:** Rename CORE.OBJ.events to "Events & messaging: deferred, batched, world-scoped event streams consumed at declared C-FRAME phases (C-FLOW mailboxes); immediate dispatch only intra-phase and single-owner, by ADR". Add C-FLOW to entity-object-model's consumes.

### K-PERF-4 · major · obsolete-assumption
- **Target:** CNT.COOK.ddc, content-pipeline-architect, CNT.COOK.shared-cache, CNT.COOK.incremental-equivalence, PRF.METH.pipeline-budgets
- **Finding:** The derived-data cache is "keyed by source path & file modification time". Mtime keys produce false misses on every VCS sync, checkout or branch switch, and on every CI and farm machine. That destroys the team and cloud cache hit rate that PRF.METH.pipeline-budgets budgets. Path keys cannot be shared across workspaces. Mtime keys also produce false hits when processor code, settings or platform variants change and the source does not. That breaks CNT.COOK.incremental-equivalence. Cook throughput at team-large scale depends on this key.
- **Evidence:** Content-addressed build caches are standard: Bazel and Buck remote caches, Unreal's DDC keys (content hash + processor version GUID), Unity Accelerator and the Unity Asset Database v2 (content hash + importer version + platform + dependencies).
- **Proposed change:** Rename CNT.COOK.ddc to "Content-addressed derived-data cache: key = hash(source content, transitive input hashes, processor version, settings, target platform/tier variant)". Add an obligation to C-COOK that processors declare every key input. Add the legacy pattern "Timestamp/path-keyed build caches".

### K-PERF-5 · major · missing-contract
- **Target:** C-GOVERN, CORE.SCALE.governor, runtime-scalability, NET.SRV.overload, dedicated-server, C-FRAME
- **Finding:** C-GOVERN names its control inputs as GPU frame time, present feedback, pool pressure and thermal/power. There is no shipping-grade CPU signal: critical-path time per frame, per-phase tick overrun, or server tick overrun from C-FRAME. As a result:
  - (a) On CPU-bound frames the governor sees only GPU and present signals. It will drive GPU actuators such as dynamic resolution that cannot help, and it cannot choose CPU actuators (significance, animation rate, worker count). This is the classic GPU-only dynamic-resolution failure.
  - (b) On the server target, which runtime-scalability ships in, there is no GPU or present signal at all. Overload control is therefore left to NET.SRV.overload as a second, independent control loop. It actuates tick rate and relevancy with no shared priorities or hysteresis. PLAT.MOB.thermal explicitly forbids an independent loop; the server path does not.
- **Evidence:** Unreal's dynamic resolution reacts only to GPU time and is documented as ineffective when a game is CPU-bound. Server overload control in production (time dilation in EVE Online, adaptive tick in large Unreal titles) is a governor over CPU tick time. Two uncoordinated feedback loops on shared actuators oscillate, which is standard control theory.
- **Proposed change:** Extend the C-GOVERN summary with "CPU critical-path and per-phase tick-overrun signals from C-FRAME (shipping-grade, not C-INSTR); CPU-vs-GPU bound classification selects actuators; on server targets tick overrun is the primary input". Rewrite NET.SRV.overload as "Server overload actuators (time dilation, adaptive tick, relevancy throttling) registered with CORE.SCALE.actuators; no independent control loop", and add runtime-scalability as a contributor.

### K-PERF-6 · major · omission
- **Target:** online-performance (profiles), C-SNAPSHOT, C-PREDICT, NET.PRED.rollback, NET.PRED.lockstep, C-BUDGET
- **Finding:** online-performance is scoped to the `online` profile only, which is server-authoritative. The `online-rollback` and `online-lockstep` configurations (fighting-2d-rollback-client, rts-2d-massim-client) have no performance analyst. No capability budgets or analyzes resimulation cost. Rollback is feasible only if (rollback window × per-tick simulation cost) + per-tick snapshot save and restore fits inside one frame. C-SNAPSHOT asks each participant to declare its cost, but nothing sums those costs against a budget, and no gate measures them. The M2 rollback gate ("8 frames under 150 ms / 5% loss") is functional, not a frame-time gate. Lockstep turn latency and command-delay analysis are also unowned.
- **Evidence:** Michael Stallone, "8 Frames in 16ms: Rollback Networking in Mortal Kombat and Injustice 2" (GDC 2018): making resimulation fit the frame was the main engineering cost. GGPO documentation says the same about save/load cost. Rocket League (Jared Cone, GDC 2018) limited physics resimulation for cost.
- **Proposed change:** Set online-performance profiles to [online, online-rollback, online-lockstep]. Add PRF.NET.resim-cost: "Worst-case resimulation cost (window × tick cost + snapshot save/restore) against the frame budget, per rollback/prediction configuration", with contributors prediction-rollback and determinism-replay. Add a C-BUDGET line for the resimulation window per configuration and add PRF.NET.resim-cost as an M2 gate.

### K-PERF-7 · major · omission
- **Target:** C-BUDGET, performance-architect, memory-performance, packaging-release-patching, platform-web, platform-mobile
- **Finding:** Size is not an owned performance dimension. The framework has patch-size budgets (BLD.REL.patching) only. Nothing owns budgets or analysis for:
  - executable/code size and WASM module size, which drive web startup through download and streaming compile;
  - initial download and install size (mobile store cellular limits and base-module limits; console install footprint);
  - shader cache and PSO cache size on disk;
  - per-module binary contribution from templates and permutations.

  These dominate time-to-first-frame and conversion on web and mobile, which are the scale-down tiers the framework claims.
- **Evidence:** Google Play's base-module and asset-pack limits, Apple's cellular download threshold, and the Unity and Godot web export guidance (WASM size drives load time). Tools such as Bloaty and SizeBench exist because code size regresses silently.
- **Proposed change:** Add PRF.MEM.size: "Binary/WASM, install, download and on-disk cache size analysis and attribution per module, asset class and configuration", owned by memory-performance, with contributors build-system-toolchains, packaging-release-patching and platform-web. Add size lines (binary, initial download, install) per configuration × platform to C-BUDGET, and add a size gate to the M2 exit (web and mobile ship).

### K-PERF-8 · major · omission
- **Target:** C-BUDGET, C-BENCH, PRF.GPU.power, PRF.CPU.hybrid, performance-architect
- **Finding:** Budgets and benchmark rules ignore energy and thermally sustained performance. C-BUDGET covers time, transfer bytes and queue occupancy. C-BENCH covers warm-up and variance, but not thermal soak. On mobile, portable consoles and handheld PCs, a benchmark passes cold and then fails after 10–20 minutes of throttling. Battery drain per hour and frame rate under a TDP cap are shipping requirements with no budget line. PRF.GPU.power analyzes GPU power only. Nothing owns whole-device energy: CPU, GPU, radio and display.
- **Evidence:** Android ADPF thermal headroom and sustained-performance mode, Apple's thermal state guidance, and Steam Deck Verified expectations around battery and TDP. Arm and Qualcomm profiling guides require thermally soaked measurement.
- **Proposed change:** Add to C-BUDGET "energy per frame / battery-hours and sustained-state frame-time budgets per battery-powered tier". Add to C-BENCH "thermal-soak preconditioning and sustained-window measurement for battery/thermal-limited tiers". Add PRF.METH.energy: "Whole-device energy & sustained-performance methodology", owned by performance-architect with contributors gpu-performance, cpu-performance and platform-mobile.

### K-PERF-9 · major · omission
- **Target:** PRF.METH.pipeline-budgets, PRF.BENCH.tools, loading-streaming-performance, content-pipeline-architect, build-system-toolchains, shader-system
- **Finding:** Pipeline budgets (cook throughput, DDC hit rate, shader compile time, build times) have an owner, and pipeline benchmarks exist (PRF.BENCH.tools). No skill analyzes pipeline performance or routes findings through C-PERF:
  - worker utilization and critical path in distributed cook;
  - DDC miss root causes;
  - shader permutation compile cost per material;
  - C++ build critical path and header cost;
  - CI wall-clock.

  PRF.LOAD.editor covers editor startup, PIE and viewport only. For runtime there are four analysts; for tooling there are none. The brief requires tooling to be as thorough as runtime.
- **Evidence:** Clang -ftime-trace, ClangBuildAnalyzer and Incredibuild/FASTBuild monitors are standard build-time analysis. The Unreal Zen/DDC and cook-stats tooling and shader-compile stats commandlets exist because cook throughput regresses with content.
- **Proposed change:** Add PRF.PIPE.cook ("Cook/DDC throughput & hit-rate analysis and attribution"), PRF.PIPE.shader-compile ("Shader compile & permutation cost analysis"), PRF.PIPE.build ("C++ build critical-path & header-cost analysis") and PRF.PIPE.ci ("CI lane wall-clock analysis"). Own them in a new process expert, `pipeline-performance` (parent performance-architect, workstream performance), and move PRF.LOAD.editor into it. The alternative is to add them to loading-streaming-performance, which would then be renamed. Either way, add a pipeline gate on PRF.METH.pipeline-budgets at M3 (standard-3d-tools).

### K-PERF-10 · major · other
- **Target:** milestones.json gates (M0–M7), PRF.MEM.*, PRF.LOAD.pacing-latency, PRF.METH.pipeline-budgets, PRF.GPU.baselines, PRF.METH.asymptotics
- **Finding:** The milestone gates cover hitches (M1), PSO coverage (M3), the governor (M3), network bandwidth (M4) and scale content (M5). No milestone gates on:
  - memory footprint or peaks (PRF.MEM.*), even though M2 ships on console and mobile, where OOM is a certification failure;
  - frame pacing and latency (PRF.LOAD.pacing-latency), even though its capability defines a "pacing gate";
  - GPU per-pass baselines;
  - pipeline budgets.

  M6, the AAA slice and the most expensive configuration, has no perf gate at all. Exit text such as "Perf: mobile tier within budget" is prose, not a gate that check.py verifies.
- **Evidence:** Console TRCs and XRs treat OOM and hangs as certification failures. Frame pacing (percentile and jitter), not average FPS, is how Digital Foundry and platform holders judge releases. The framework's own principle says instrumentation and budgets exist before features, and are gated.
- **Proposed change:** Add gates PRF.MEM.footprint and PRF.MEM.peaks at M2. Add PRF.LOAD.pacing-latency at M2 (all platforms) and again at M5 for XR. Add PRF.GPU.baselines at M3, PRF.METH.pipeline-budgets (or the new PRF.PIPE.* gate) at M3, and PRF.METH.asymptotics plus PRF.NET.server-density at M6. Add a memory-gate capability PRF.MEM.gate ("memory budget gate over snapshots per configuration"), owned by memory-performance.

### K-PERF-11 · major · scale-down
- **Target:** PLAT.WEB.runtime, platform-web, CORE.JOBS.degenerate
- **Finding:** PLAT.WEB.runtime makes WASM threads mandatory ("SharedArrayBuffer required; cross-origin isolation assumed on every host"). Many web distribution hosts cannot serve COOP/COEP headers, including iframe-embedded game portals and some CDNs, or they break third-party embeds when they do. A web build that requires SharedArrayBuffer does not start there. This contradicts the framework's own stance that the same task graph runs inline on 0–2 workers (CORE.JOBS.degenerate) and undermines the indie-2d-online-web-client scale-down claim.
- **Evidence:** MDN and web.dev documentation on cross-origin isolation requirements for SharedArrayBuffer. Unity's and Godot's web exports keep a single-threaded variant because portals often cannot enable COOP/COEP.
- **Proposed change:** Rewrite PLAT.WEB.runtime as "WASM threads where cross-origin isolated; single-threaded inline build variant (CORE.JOBS.degenerate, 0 workers) where not; runtime detection & memory limits". Add a web configuration or platform variant with threads off to the M2 claim.

### K-PERF-12 · minor · other
- **Target:** C-GOVERN (oracle_author)
- **Finding:** The acceptance suite for the closed-loop governor is written by visual-debugging-tools. Governor correctness means stability without oscillation, settle time under step loads, hysteresis and actuator priority. Those need a control-systems and frame-pacing oracle, not a debug-UI expert. The M3 gate "governor closed-loop test" depends on this oracle.
- **Evidence:** A closed-loop controller is validated with step and ramp workload tests and oscillation criteria, which is standard control engineering. loading-streaming-performance already owns pacing analysis and the pacing gate.
- **Proposed change:** Set C-GOVERN oracle_author to loading-streaming-performance, or to perf-benchmarking.

### K-PERF-13 · minor · omission
- **Target:** perf-benchmarking, BLD.CI.devices, BLD.CI.device-lanes
- **Finding:** Nobody owns perf-grade reference hardware per tier: a clock-locked, thermally controlled, exclusive, inventoried machine or device for every tier in ARCH.REQ.hardware-tiers (min-spec PC, each console SKU and mode, reference phones, handheld). BLD.CI.devices schedules and pools shared devices, which adds noise to benchmarks, and PRF.BENCH.stats can only model variance after the fact.
- **Evidence:** Perf labs at large studios, and Mozilla and Chromium perf infrastructure, use dedicated, pinned-configuration machines separate from functional CI.
- **Proposed change:** Add PRF.BENCH.lab: "Reference perf hardware per tier: inventory, clock/thermal control, exclusivity and noise qualification", owned by perf-benchmarking with contributor ci-cd-automation.
