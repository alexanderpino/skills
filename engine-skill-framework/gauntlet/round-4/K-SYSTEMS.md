# K-SYSTEMS findings (Systems Critic, round 4)

### K-SYSTEMS-1 · major · missing-contract
- Target: C-TASK, CORE.JOBS.*, job-system-task-graph, RES.MGMT.pipeline, ED.ARCH.async-jobs, ML.RT.sequence-exec
- Finding: No capability or C-TASK obligation covers task cancellation (cancellation tokens, propagation to dependents, cancel of in-flight IO/GPU work, cancel-vs-retire ordering). Cancellation appears only as local words in RES.MGMT.pipeline, ED.ARCH.async-jobs and ML.RT.sequence-exec, so three owners will invent three semantics on the async path (IO, decompress, fixup, upload, publish), each racing publish against cancel and against handle release.
- Evidence: Structured concurrency and cancellation tokens (.NET CancellationToken, C++26 std::execution stop_token, Rust drop-cancel hazards, Swift task cancellation); Naughty Dog and Frostbite job talks; DirectStorage and io_uring expose cancel, but the race with completion must be defined once.
- Proposed change: add CORE.JOBS.cancellation (owner job-system-task-graph, contributors async-io-storage, resource-streaming-architect, concurrency-primitives) and add cancel/stop-token and cancel-vs-completion semantics to the C-TASK summary. RES.MGMT.pipeline, ED.ARCH.async-jobs and ML.RT.sequence-exec reference it; add a cancellation-race case to the C-TASK and C-RES oracle references.

### K-SYSTEMS-2 · major · omission
- Target: C-IO, RES.IO.*, C-PAL, PLAT.PAL.os, GAM.SAVE.atomic (persistence-save, L4)
- Finding: The IO stack is read-only. There is no owner for durable write primitives (write scheduling and coalescing, fsync/F_FULLFSYNC, directory sync, atomic rename, disk-full behaviour, write-vs-read deadline arbitration). The only atomic-write capability is GAM.SAVE.atomic at layer 4, which lower consumers cannot use. The editor journal (ED.ARCH.recovery), DDC, PSO/shader caches, crash dumps, telemetry spool, server write-behind (NET.SRV.persistence) and cook outputs each need it. Each will reimplement it, or call raw PAL files and bypass IO arbitration.
- Evidence: SQLite and LMDB durability documentation (fsync semantics differ by OS; macOS needs F_FULLFSYNC); LevelDB/RocksDB WAL practice; Windows FlushFileBuffers behaviour; SSD write endurance concerns for logging-heavy builds.
- Proposed change: add RES.IO.write (owner async-io-storage; contributors platform-architect, persistence-save) covering write queues, durability classes (none, flush, full), atomic replace, quota and disk-full errors, and read-deadline protection. Add it to the C-IO summary. persistence-save, DDC, editor recovery and the crash writer consume it. Keep GAM.SAVE.atomic for the save-format policy only. Add a crash-consistency oracle (power-cut simulation) to the C-IO reference.

### K-SYSTEMS-3 · major · wrong-boundary
- Target: CORE.MEM.allocators, C-MEM, C-LIFETIME, memory-allocators (consumes only C-PAL, C-BASE, C-SYNC)
- Finding: The allocator family lists "linear/frame" allocators. The framework's own model has overlapping frames in flight, multi-frame tasks (CORE.FRAME.async-work) and per-world cadences (CORE.FRAME.multi-world), so "frame" is not a lifetime. memory-allocators does not consume C-LIFETIME or any completion token. Nothing states that scratch arenas are scoped to a frame-in-flight slot or a task-graph completion and reset only when that token retires. This is the frame-tied lifetime pattern the anti-legacy catalogue rejects, and it will surface as use-after-reset bugs once frames overlap.
- Evidence: Frostbite and Destiny frame-graph and transient-allocator talks; UE FMemStack scoped to task lifetime; Vulkan/D3D12 per-frame-in-flight upload and constant ring buffers reset by fence.
- Proposed change: rename to "scoped arenas: reset keyed to a completion token or frame-in-flight slot (C-LIFETIME), never to wall-clock frames". Add C-LIFETIME to memory-allocators consumes (same layer L1, no cycle). Add a torture-corpus item, "arena reuse under 3 overlapping frames and a cancelled task", to the C-MEM and C-LIFETIME oracle references.

### K-SYSTEMS-4 · minor · omission
- Target: CORE.MEM.uma, RND.MEM.upload, RND.MEM.heaps, memory-allocators, gpu-memory-resources
- Finding: CPU-visible GPU memory rules are unowned. That covers memory-type and coherence policy (write-combined vs cached, host-visible device-local/ReBAR, non-temporal streaming stores, no CPU reads from WC memory, cache maintenance on non-coherent mobile and console paths). CORE.MEM.uma is accounting only and RND.MEM.upload names rings only. UMA consoles, Apple silicon and mobile depend on this; misuse gives silent 10-100x CPU-read slowdowns or stale data.
- Evidence: AMD GPUOpen memory-allocation guidance for Vulkan/D3D12 (HOST_VISIBLE|DEVICE_LOCAL, ReBAR); Apple Metal storage modes (shared/managed/private); Arm Mali and Adreno best practices on cache maintenance.
- Proposed change: add RND.MEM.cpu-visible (owner gpu-memory-resources; contributor memory-allocators) with a per-platform memory-type matrix and an "upload writes sequential and reads forbidden" lint. State that CORE.MEM.uma consumes it. Add it to the C-GPUMEM summary.

### K-SYSTEMS-5 · minor · omission
- Target: CORE.CONC.sync, CORE.JOBS.thread-model, CORE.JOBS.priorities, AUD.ARCH.engine
- Finding: Priority inversion is not addressed. CORE.CONC.sync specifies futex-backed locks and spin-with-backoff, but not priority inheritance or donation. The framework mixes real-time audio, latency-critical lanes and QoS classes with shared locks, and thread-model has "real-time thread rules" without lock rules. Spinning on a preempted lower-priority holder, or on an E-core, stalls a latency-critical lane.
- Evidence: Mars Pathfinder; Linux PI-futex; Apple os_unfair_lock priority donation; Windows scheduler boosts; Ross Bencina's "Real-time audio programming 101"; Android ADPF guidance on spinning.
- Proposed change: extend CORE.CONC.sync with "priority-inheritance/donation where the OS offers it; no spinning across QoS classes; a lock-class registry (frame-critical, RT-forbidden) checked by CORE.CONC.correctness". Add an RT-thread forbidden-primitive lint to the thread-model rules.

### K-SYSTEMS-6 · minor · omission
- Target: CORE.MEM.debugging, XC.SEC.hardening, OBS.CRASH.oom, memory-allocators
- Finding: The framework has dev-time memory debugging and hardening matrices, but no field detection of memory corruption in shipping builds (sampled guard-page allocator, hardware memory tagging, and their crash annotations). MTE/PAC is mentioned only inside a security capability marked M. The dev/shipping split leaves heap bugs that only appear on player hardware with no detection path, and the allocator owner has no obligation to expose it.
- Evidence: GWP-ASan (LLVM, deployed in Chrome and Android); Arm MTE async mode in Android, Scudo hardened allocator; PartitionAlloc guard-page design.
- Proposed change: add CORE.MEM.field-detection (owner memory-allocators; contributors crash-diagnostics, security-engineering). It covers a sampled guard allocator and MTE tag-check mode with per-config overhead budgets in C-BUDGET, and feeds OBS.CRASH.capture bucketing. Radar class M for MTE, E for sampled guard pages.

### K-SYSTEMS-7 · minor · omission
- Target: CORE.CONC.*, CORE.TYPES.containers, PRF.CPU.contention
- Finding: False sharing and cache-line contention appear only as an analysis capability (PRF.CPU.contention, after the fact). No design-side owner defines cache-line size discovery use, padding and alignment rules for cross-thread data, and per-worker sharded counters and queues. Cache size comes from PLAT.PAL.cpu-topology, but the rule is never stated. Independent agents writing atomics and MPMC structures will produce false sharing that is found late.
- Evidence: Disruptor (LMAX) padding practice; Folly and Abseil cache-line-aligned sharding; C++17 hardware_destructive_interference_size; Apple M-series 128-byte lines.
- Proposed change: add CORE.CONC.layout (owner concurrency-primitives; contributors containers-core-types, platform-architect) covering destructive-interference size per target, sharding rules and padding lint; hand analysis to PRF.CPU.contention.

### K-SYSTEMS-8 · minor · omission
- Target: OBS.CRASH.capture, C-CRASH, C-IPC, PLAT.PAL.signals, CORE.MEM.oom
- Finding: C-CRASH is layer 1 and requires only C-BASE and C-INSTR, but C-IPC (layer 2) lists the crash handler as an endpoint. No capability owns crash-time safety: async-signal-safe or SEH-safe code only, a pre-reserved emergency heap, an alternate signal stack for stack overflow, an out-of-process capture path over PAL pipes rather than the engine IPC, and handling of OOM inside the handler. Crash capture done through the engine allocator or scheduler fails exactly in OOM and deadlock crashes.
- Evidence: Crashpad and Breakpad design docs (out-of-process, no allocation in the handler); the POSIX async-signal-safe list; Windows stack-overflow SEH constraints.
- Proposed change: add OBS.CRASH.safe-path (owner crash-diagnostics; contributors platform-architect, memory-allocators) and state that the crash handler process uses PAL process/pipe primitives via C-BASE only, with C-IPC not a dependency. Correct the C-IPC summary. Add a crash-in-OOM and crash-in-lock-held case to the C-CRASH conformance.
