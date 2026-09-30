# K-SYSTEMS — Systems Critic, round 3

### K-SYSTEMS-1 · major · obsolete-assumption
- **Target:** CORE.JOBS.blocking, C-TASK, CORE.JOBS.pinned, RES.MGMT.no-stall, CORE.JOBS.degenerate
- **Finding:** CORE.JOBS.blocking says blocking and long-running tasks "run inline on work-stealing workers (no dedicated lanes or compensating threads)". That is the classic way to starve a pool. N blocked workers leave the frame-critical graph with fewer cores, and on 0–2-worker tiers (web, low-end mobile) a single blocking task stalls the frame outright. The capability also contradicts RES.MGMT.no-stall and CORE.JOBS.degenerate ("no blocking waits"), and it makes CORE.JOBS.pinned lanes pointless for blocking OS calls.
- **Evidence:** Production schedulers never block workers without compensation. TBB uses arenas and dedicated blocking threads. The Go runtime hands off its P on a syscall. The .NET ThreadPool injects compensating threads (hill climbing). Naughty Dog's fiber job system (GDC 2015, Gyrling) parks the fiber instead of the thread. Unreal Tasks sends long work to background-priority named threads. Long-running work such as shader compiles, navmesh builds or LLM inference must not share frame-critical lanes (CORE.JOBS.priorities).
- **Proposed change:** Rename CORE.JOBS.blocking to "Blocking & long-running work policy: frame-critical workers never block; waits suspend (fiber/coroutine) or move to a bounded blocking/background lane with compensation accounting; long-running tasks run on low-QoS lanes with cancellation and budget". Add the rule to the C-TASK summary. Add a legacy pattern "blocking calls on frame-critical workers" whose stance capability is CORE.JOBS.blocking.

### K-SYSTEMS-2 · major · obsolete-assumption
- **Target:** CORE.OBJ.events, C-ID, legacy L19, CORE.FRAME.channels / C-FLOW
- **Finding:** CORE.OBJ.events reads "global event bus with immediate synchronous listener dispatch by default". That is exactly the legacy pattern that L19 says CORE.OBJ.events replaces, and it breaks three other rules in the framework: it adds a hidden global (§6 "no hidden globals"), it runs callbacks on the producer's thread in the middle of a phase (C-FRAME ordering comes from declared access), and it spans worlds when worlds must be isolated (CORE.OBJ.world-instances). Messaging also has two owners: entity-object-model (C-ID "events") and frame-orchestration (C-FLOW "mailboxes").
- **Evidence:** Re-entrancy and ordering bugs from synchronous observers are well documented (Bevy moved to buffered Events/Observers with explicit points; Unity DOTS removed immediate callbacks in favour of command buffers or event components). Callbacks that run mid-phase cannot be checked by CORE.FRAME.phase-violations or CORE.ECS.safety.
- **Proposed change:** Rename CORE.OBJ.events to "Events & messaging semantics: world-scoped, deferred, batched events consumed at declared C-FRAME consumption points; immediate dispatch only for same-thread, same-phase local observers by ADR". Record in C-ID that event transport is a C-FLOW mailbox, so the policy stays with entity-object-model and the channel mechanism with frame-orchestration. Remove "global" from the name.

### K-SYSTEMS-3 · major · obsolete-assumption
- **Target:** PHY.ARCH.stepping, CORE.FRAME.fixed-step, CORE.FRAME.sim-schedule, legacy L30
- **Finding:** PHY.ARCH.stepping is "Variable-timestep stepping on the render frame delta & frame sync". That is the frame-coupled variable-timestep pattern that L30 forbids. It also creates a second authority over simulation cadence: physics chooses its own step from the render delta, while frame-orchestration owns fixed-step, time domains and the canonical sim schedule. Determinism (C-DET), rollback (C-SNAPSHOT) and server/client parity all depend on a declared fixed step.
- **Evidence:** "Fix Your Timestep" (Fiedler) is the standard reference. Every modern physics middleware (Jolt, PhysX, Havok) recommends fixed substeps. Variable dt makes constraint solvers unstable and breaks replay and prediction.
- **Proposed change:** Rename PHY.ARCH.stepping to "Physics stepping within the C-FRAME fixed/declared step (substeps, max-catch-up, interpolation hand-off); variable step only by ADR for non-networked, non-deterministic games". Add PHY.ARCH.stepping to L30 stance_capabilities.

### K-SYSTEMS-4 · major · obsolete-assumption
- **Target:** PLAT.WEB.runtime, CORE.JOBS.degenerate, platform-web
- **Finding:** PLAT.WEB.runtime states "SharedArrayBuffer required; cross-origin isolation assumed on every host". That is false for many real distribution hosts: iframe-embedded web portals, ad and aggregator sites, and hosts without COOP/COEP headers or credentialless iframes. It also contradicts CORE.JOBS.degenerate, which designs the same graph to run on 0 workers. As written, the web target fails wherever it has no isolation, when the degenerate mode should apply.
- **Evidence:** SharedArrayBuffer is gated on crossOriginIsolated (in effect since Chrome 92 and Firefox 79). Embedding pages must opt in with COEP. Emscripten and Unity WebGL both keep single-threaded builds for this reason.
- **Proposed change:** Rename PLAT.WEB.runtime to "WASM threads when cross-origin isolated (COOP/COEP or credentialless), with runtime detection and fallback to the 0-worker cooperative mode (CORE.JOBS.degenerate); memory limits (memory64 where available)". Make the web configurations prove the 0-worker path (the M2 exit criterion).

### K-SYSTEMS-5 · major · omission
- **Target:** CORE.FRAME (frame-orchestration), C-FRAME, CORE.OBJ.world-instances, NET.SRV.density, PHY.ARCH.multi-world, ED.ARCH.pie
- **Finding:** The framework requires several isolated worlds per process (server density, PIE plus editor world plus preview worlds, match instances), each with its own time domain and tick rate. Yet C-FRAME describes "the single frame scheduler that compiles the per-frame graph". No capability owns how N concurrent world schedules share one worker pool. That includes per-world graphs with independent cadences, fairness and priority between worlds (one overloaded match must not starve its neighbours), per-world pause and time dilation, and global versus per-world sync points. NET.SRV.density measures density but does not own the scheduler.
- **Evidence:** Unreal ticks multiple UWorlds serially inside one engine loop, the legacy default. Dense server hosting (many sessions per process on Linux fleets) needs weighted fair scheduling across instances. The pattern is well known from the actor runtimes (Orleans, Akka) that inspired server meshing.
- **Proposed change:** Add CORE.FRAME.multi-world "Concurrent per-world frame graphs on one worker pool: independent time domains/cadences, cross-world priority and fair-share, per-world overload isolation, process-global vs world-scoped sync points", owned by frame-orchestration with contributors dedicated-server, editor-architect and physics-architect. Add "multiple world schedules" to the C-FRAME summary.

### K-SYSTEMS-6 · major · wrong-owner
- **Target:** C-SYNC (oracle_author entity-object-model), C-TASK (oracle_author animation-architect), robustness-fuzzing, QA.ROBUST.concurrency
- **Finding:** The conformance oracles for the two hardest foundation contracts belong to skills that lack the expertise to judge them. The memory model, lock-free structures and reclamation (C-SYNC) are overseen by the object-model skill. Work stealing, QoS, blocking rules and schedule perturbation (C-TASK) are overseen by the animation lead. Independence is satisfied, but the oracles cannot test linearizability, memory-ordering bugs (weak-memory ARM) or ABA and reclamation races, so implementers are graded by suites that cannot find their defects. robustness-fuzzing already owns QA.ROBUST.concurrency, contributes to CORE.CONC.correctness and sits in a different workstream (quality).
- **Evidence:** Lock-free bugs surface only under model checking (Relacy, CDSChecker, GenMC) or ARM weak-memory stress (the herd7/litmus suites). Loom (Rust/tokio) is a production precedent for oracle-grade concurrency testing.
- **Proposed change:** Set oracle_author for C-SYNC and C-TASK to robustness-fuzzing. Keep entity-object-model and animation-architect as consumer reviewers (performance and API fitness). Require litmus and model-checking lanes on ARM64 and x86 in the conformance suite.

### K-SYSTEMS-7 · major · omission
- **Target:** C-IPC, CORE.LIFE.ipc, untrusted-inputs.json, BLD.SYS.dev-surface-exclusion
- **Finding:** C-IPC carries editor↔runtime, tool worker (shader compile, cook) and profiler traffic, plus the crash handler, which is an out-of-process surface that ships. BLD.SYS.dev-surface-exclusion explicitly allows shipping surfaces "authenticated via C-IPC". Yet the untrusted-input registry has no IPC entry: no validating owner, no fuzz target and no limits for IPC frames or shared-memory rings. Only dev-endpoints and automation-commands are registered.
- **Evidence:** Crash handlers and local IPC brokers are a recurring local privilege-escalation and injection vector (Chromium's Mojo validation and fuzzing exist for this reason). Shared-memory rings are also exposed to TOCTOU attacks.
- **Proposed change:** Add an untrusted input "ipc-messages" with validating_owner core-runtime-architect, parser_owners crash-diagnostics and editor-architect, trust hostile-local, mode harness, and limits frame size/rate/schema version, including TOCTOU-safe copy-out for shared memory. Add "untrusted-frame validation" to the C-IPC summary.

### K-SYSTEMS-8 · major · obsolete-assumption
- **Target:** PRF.METH.budgets, CORE.MEM.budget-enforcement, RES.MGMT.arbitration
- **Finding:** Budgets are "measured on the reference high-end PC and scaled proportionally to lower tiers". Memory, bandwidth and latency budgets do not scale proportionally. Console and mobile UMA pools are fixed physical ceilings with OS reservations, TBDR bandwidth behaves differently, and minimum-spec cache sizes and core counts change which bottleneck binds. Proportional scaling yields memory budgets that are infeasible or wasteful, and the arbiter then enforces them.
- **Evidence:** Shipping practice measures and sets budgets on each tier's reference device, with min-spec as the binding constraint (console TRC memory limits; Android low-RAM device classes).
- **Proposed change:** Rename PRF.METH.budgets to "Per-tier budgets set and measured on each tier's reference hardware (min-spec binding); memory budgets derived from the tier's physical/OS-reserved ceilings; cross-tier scaling only as an initial estimate".

### K-SYSTEMS-9 · minor · dependency-error
- **Target:** memory-allocators, C-MEM, C-SYNC
- **Finding:** memory-allocators consumes only C-PAL and C-BASE, yet it implements thread caches, NUMA-aware allocation, cross-thread frees and defragmentation. Those need atomics, futex locks and the thread-safety annotation conventions. As written, the allocator either duplicates concurrency primitives or falls outside CORE.CONC.correctness review and model checking. C-SYNC depends only on C-BASE, so adding the edge creates no cycle.
- **Proposed change:** Add C-SYNC to the memory-allocators consumes list and to the C-MEM requires list, and state in C-SYNC that its lock-free node storage uses the C-BASE raw allocator.

### K-SYSTEMS-10 · minor · overlap
- **Target:** C-TYPES, CORE.TYPES.crypto, C-SIGN
- **Finding:** The C-TYPES summary still claims a "vetted hashinggraphic primitives wrapper" (a garbled leftover of "crypto primitives"). CORE.TYPES.crypto is owned by security-runtime and delivered through C-SIGN. Two contracts now appear to provide crypto primitives.
- **Proposed change:** Remove crypto from the C-TYPES summary ("… keyed/stable hashing, …"). Move CORE.TYPES.crypto into an XC.SEC or security-runtime area, or say in its name that C-SIGN provides it.

### K-SYSTEMS-11 · minor · omission
- **Target:** CORE.MEM.virtual, PLAT.SRV.host-os
- **Finding:** Large and huge pages appear only for server hosts. On clients, TLB pressure from multi-GB streaming pools, 2 MB and 64 KB page granularity on consoles, Windows large pages (SeLockMemoryPrivilege) and Linux THP policy all change allocator design and GPU-visible mapping. No client capability owns page-size policy.
- **Proposed change:** Rename CORE.MEM.virtual to "Virtual memory reservation, mapping & page-size policy (4K/64K/2M, large/huge pages, commit/decommit granularity per platform)".
