### K-SYSTEMS-1 · major · other
- Target: CORE.JOBS.degenerate, RES.MGMT.no-stall, CORE.FRAME.host-loop, PLAT.WEB.runtime, C-TASK
- Finding: CORE.JOBS.degenerate says "blocking waits on the host thread allowed for IO completion", while RES.MGMT.no-stall forbids blocking waits on host/OS-bound threads and CORE.FRAME.host-loop demands a non-blocking cooperative step. On the browser main thread Atomics.wait is disallowed and a synchronous IO wait starves the event loop that delivers the IO completion, so the shipping web configuration deadlocks or is killed by the browser.
- Evidence: HTML/WASM threading rules (main thread cannot block on Atomics.wait; fetch/OPFS completions arrive on the event loop). Mobile watchdogs also kill a blocked main thread.
- Proposed change: rewrite CORE.JOBS.degenerate: in host-driven mode IO and GPU completions arrive only as event-loop callbacks converted to C-TASK tokens, and no wait primitive is legal on the host thread. Permit blocking waits only in non-host-driven cooperative targets (CLI tools, offline cook). Add a C-TASK conformance case, "0-worker host-driven graph completes a load with no blocking wait".

### K-SYSTEMS-2 · major · omission
- Target: ARCH.REQ.hardware-tiers, RES.IO.scheduling, RES.MGMT.arbitration, C-BUDGET, PLAT.PAL.system-events
- Finding: There is no storage-class dimension. Tiers, IO scheduling and IO-bandwidth arbitration assume NVMe-like random access. Minimum-spec PC HDDs (Steam Deck SD cards, eMMC, UFS, game cards, network-mounted or cloud-hosted volumes) need seek-aware ordering, low queue depth, asset duplication or clustering and different streaming budgets. C-BUDGET has bytes per frame but no sustained-read and IOPS lines per storage class. RES.PKG.ordering and RES.IO.scheduling name no such policy.
- Evidence: Cyberpunk 2077 and Spider-Man PC HDD hitching. Helldivers 2 shrank its install by dropping HDD asset duplication. Steam Deck SD-card load-time variance. DirectStorage and GPU decompression are gated on NVMe.
- Proposed change: add PLAT.PAL.storage-class (rotational / SATA-SSD / NVMe / removable / network, measured throughput and latency probe). Add RES.IO.media-policy (seek-aware ordering, depth, duplication policy) owned by async-io-storage, with package-formats-vfs contributing to layout. Add a storage-class axis to the ARCH.REQ.hardware-tiers records and sustained-read and IOPS lines to C-BUDGET. Feed the probe into RES.MGMT.arbitration as the IO-bandwidth pool.

### K-SYSTEMS-3 · major · overlap
- Target: CORE.OBJ.events, CORE.FRAME.channels, GAM.SYS.messages, PHY.ARCH.events
- Finding: Two owners define event delivery ordering. CORE.OBJ.events (entity-object-model) owns "deferred, batched delivery at declared consumption points". CORE.FRAME.channels (frame-orchestration) owns "gameplay event dispatch, subscriptions and delivery ordering". Neither row lists the other as a contributor. Under C-FLOW, a gameplay event may be a channel item or an OBJ event queue entry, and ordering across the two is unowned, which breaks the determinism claim for replay and rollback.
- Evidence: Ordering authority must be unique for C-DET replay. Unity DOTS and Bevy have one event/channel mechanism scheduled by the same access graph, so the two do not diverge.
- Proposed change: make CORE.FRAME.channels the sole mechanism and ordering authority. Redefine CORE.OBJ.events as the event type, ID and payload schema only, and add frame-orchestration as its contributor. State in C-FLOW that GAM.SYS.messages and PHY.ARCH.events are channel producers.

### K-SYSTEMS-4 · major · wrong-owner
- Target: CORE.LIFE.ownership-model, C-LIFETIME, CORE.OBJ.references, C-ID
- Finding: Ownership policy is split across three owners. C-LIFETIME (concurrency-primitives) summarizes "engine-wide ownership and cross-thread reference rules". The row CORE.LIFE.ownership-model with the same words is owned by core-runtime-architect. CORE.OBJ.references and C-ID own "reference kinds and lifetime rules". An agent changing a rule does not know which contract change request to file. The implementer of C-LIFETIME (concurrency-primitives) also becomes the author of a policy it consumes.
- Evidence: Rust ownership rules and Unreal UObject-vs-raw ownership disputes show that a single policy owner is required, and that retirement mechanism and policy must be separable.
- Proposed change: give C-LIFETIME the mechanism only (retirement service, tokens, epochs). Move the policy text to a core-runtime-architect contract section, or make C-LIFETIME owner core-runtime-architect with concurrency-primitives as implementer. Reduce CORE.OBJ.references to entity handle semantics that cite the policy.

### K-SYSTEMS-5 · major · dependency-error
- Target: C-CRASH, C-BASE, PLAT.PAL.process, OBS.CRASH.safe-path
- Finding: C-CRASH says its handler "uses PAL process/pipe primitives via C-BASE only". C-BASE lists only the raw page allocator, raw sink, monotonic clock, raw threads and hook tables. Pipes and process spawn live in PLAT.PAL.process, which is C-PAL and includes the HTTP/TLS client. The async-signal-safe crash path therefore either depends on full C-PAL, which is fragile in crash-with-lock-held and OOM, or has no defined primitive.
- Evidence: Breakpad/Crashpad out-of-process design: the handler needs pre-opened pipe/socket fds, a raw write, an alternate stack and an exception port, all of which must exist before any layered init.
- Proposed change: add to C-BASE a signal-safe subset (pre-opened fd/pipe write, raw file write, alternate-stack reservation, exception-port/handler registration hook, process-spawn for the monitor). Keep PAL.process for the rest. Update the C-CRASH requires and summary to match, and add a C-BASE conformance case "crash path with no C-PAL initialized".

### K-SYSTEMS-6 · major · missing-contract
- Target: C-CFG, C-MEM, C-RES, C-GPUMEM, C-LIFETIME, milestones freeze ordering
- Finding: Build-level requires understate real dependencies, and freeze ordering is proved only against requires. C-CFG requires only C-BASE, but typed cvars, strings and snapshots need C-TYPES and C-MEM. CORE.MEM.allocators keys arena reset to C-LIFETIME and memory-allocators consumes C-LIFETIME, but C-MEM does not require it. C-RES drains residency at a declared C-FRAME phase and its pipeline stage is GPU upload, but its requires omit C-FRAME. C-GPUMEM obeys pool hooks declared in C-RES but does not require it, and neither the direction nor the inversion is stated. The proof can then let C-CFG or C-MEM freeze before what they depend on.
- Evidence: The framework's own rule that a freeze never precedes its requirements is only as strong as the requires data.
- Proposed change: add requires C-CFG→[C-TYPES] (or state a no-allocator subset of C-TYPES used pre-C-MEM), C-MEM→[C-LIFETIME], C-RES→[C-FRAME]. Declare the C-GPUMEM→C-RES hook as an inversion in C-RES, with C-RES owning the hook interface. Re-run check.py to confirm the SCCs remain acyclic.

### K-SYSTEMS-7 · minor · wrong-boundary
- Target: CORE.JOBS.thread-model, CORE.FRAME.pipelining, AUD.ARCH.engine, RES.IO.backends
- Finding: CORE.JOBS.thread-model claims to be the "sole authority on which threads exist", while CORE.FRAME.pipelining decides "whether any dedicated render/RHI thread exists, by ADR". Audio, IO backend and network threads are also created by their owners. Two rows can each decide thread existence, and oversubscription detection has no complete inventory.
- Evidence: Frostbite, Destiny and UE each keep a single central thread and priority table. Ad-hoc threads created per subsystem cause oversubscription on hybrid-core and 4-core low-tier devices.
- Proposed change: reword the FRAME.pipelining row so the ADR specifies the pipeline depth and lane roles, and the thread-model row registers the resulting threads. Require every other skill to request threads or lanes through the thread-model inventory only (a lint under CORE.JOBS.thread-model), with real-time lanes named.

### K-SYSTEMS-8 · minor · omission
- Target: PRF.CPU.parallel-scaling, QA.HOST, ARCH.REQ.hardware-tiers, CI lanes
- Finding: No capability owns emulating a lower hardware tier on stronger dev/CI machines: core-count and SMT/P-E affinity masks, a hard process memory ceiling at the target-tier budget, IO throttling, GPU clock caps. The scale-down proof exists only as data closure; nothing runs the min-spec configuration under real constraints. Devkits with extra RAM and PCs with 32 GB hide OOM and hitch regressions until late.
- Evidence: Console devkits carry extra memory compared with retail. Unity and UE "device profile" preview and cgroup-limited CI containers are the common workaround.
- Proposed change: add PRF.METH.tier-emulation (owner performance-architect, contributors test-runtime-harness, ci-cd-automation, memory-allocators, async-io-storage). It defines memory ceiling and throttle hooks through CORE.MEM.budget-enforcement and a PAL fault-injection hook, and it runs in a CI lane per configuration, gating the perf lines in C-BUDGET.

### K-SYSTEMS-9 · minor · omission
- Target: CORE.MEM.virtual, GAM.SCR.aot, PLAT.PAL.os
- Finding: Executable-memory policy (W^X, JIT entitlement, code-page allocation, icache flush) has no memory-side row. GAM.SCR.aot mentions JIT constraints, but CORE.MEM.virtual lists only page size and commit granularity. Native live coding, script JIT, shader/ML kernel JIT and Wasm runtimes all need one place that states per platform whether writable-executable mappings exist.
- Evidence: iOS and consoles forbid JIT except by entitlement. macOS hardened runtime needs the JIT entitlement. Windows CFG and ACG restrict dynamic code.
- Proposed change: extend CORE.MEM.virtual (or add CORE.MEM.exec-pages) with per-platform executable-mapping capability queries from PAL. Make GAM.SCR.aot, XC.ITER.live-coding and XC.SEC.hardening consume it.
