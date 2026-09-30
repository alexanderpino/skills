### K-PERF-1 · major · dependency-error
- Target: milestones.json M4 exit and M6 gates, PRF.NET.server-density, online-3d-server
- Finding: The M4 exit text says "server density is gated at M4 (PRF.NET.server-density)", but the only gate for that capability is in M6. online-3d-server closes at M4, so M4 through M5 ship dedicated servers whose tick cost, instances per host and cost per CCU are never gated. The M6 gate then measures density for the first time on the AAA server, after netcode and replication design are frozen.
- Evidence: Tick cost per player and instances per host are architectural (relevancy, replication cost, per-entity bytes) and are expensive to fix after freeze. The exit text and the gate list disagree.
- Proposed change: Add the PRF.NET.server-density gate (validator QA.FUNC.load) to M4 for online-3d-server. Keep an M6 gate under a distinct capability, or split into a density gate per server config. Have the check verify that exit-text perf claims map to gates.
### K-PERF-2 · major · scale-down
- Target: M2 (mobile-async-client), CORE.SCALE.governor, PRF.METH.energy, PRF.GPU.power, C-BENCH thermal-soak
- Finding: M2 ships mobile-async-client and exits with "mobile tier within budget". The thermal and sustained-state machinery is gated one milestone later (CORE.SCALE.governor and PRF.METH.energy at M3). Mobile on M2 is judged only by footprint, pacing and size gates, so a cold-device burst passes while a device that throttles after 10 minutes is never tested.
- Evidence: Sustained-versus-peak throttling on phones is the dominant mobile perf failure (ADPF and iOS thermal-state guidance, Android Dynamic Performance Framework talks).
- Proposed change: Add an M2 gate for a sustained-state frame-time line on the mobile tier (thermal-soak run through C-BENCH, validator PRF.BENCH.stats). Also gate the governor or thermal-signal backend on mobile at M2. Otherwise move the mobile "within budget" claim to M3.
### K-PERF-3 · major · omission
- Target: C-BENCH (profile build), C-BUDGET, BLD.SYS.configs, PRF.BENCH.regression, XC.SEC.hardening
- Finding: Every perf gate runs on the "profile" configuration (shipping optimization with C-INSTR on). Nothing measures the delta between profile and the real shipping artifact. Shipping differs in instrumentation compiled out (which changes inlining and code layout), LTO/PGO, the hardening flags mandated at M1 (CFG, stack protectors, memory tagging), signed-package verification, anti-cheat and encryption. The budgets are therefore validated on a binary that never ships.
- Evidence: Well-known profile-versus-retail divergence. Console retail builds differ in memory, and hardening costs a few percent of CPU. Field telemetry (PRF.METH.field) only sees this after release.
- Proposed change: Add PRF.BENCH.shipping-delta (perf-benchmarking, contributors build-system-toolchains and security-engineering). It runs a shipping-build smoke benchmark per tier with an overhead line for C-INSTR, hardening and DRM in C-BUDGET, and a gate at M1 for PC and M2 for the other platforms.
### K-PERF-4 · major · omission
- Target: PRF.BENCH.lab, PRF.BENCH.proxy-metrics, PRF.BENCH.lab-scheduling, milestones M0/M1 gates
- Finding: The M0 and M1 exits require CI perf lanes and "within budget on min-spec PC", but no gate names PRF.BENCH.lab, proxy-metrics or lab-scheduling. The gate is OBS.LOG.bench-runtime, validated by PRF.BENCH.regression, which needs quiet reference hardware. Without a lab gate, agents could pass regression detection on noisy shared runners.
- Evidence: Noisy shared-runner benchmark failures (Chromium and Mozilla perf infrastructure require a dedicated lab). Rust's rustc-perf uses instruction counts for this reason.
- Proposed change: Add gates at M0 for PRF.BENCH.proxy-metrics (validator PRF.BENCH.regression) and at M1 for PRF.BENCH.lab (min-spec PC noise qualification). Add per-platform lab gates at M2 and M3 for the console and mobile devices.
### K-PERF-5 · major · omission
- Target: M5 gates, xr-standalone-client, xr-pc-client, xr-console-client, C-BUDGET, PLAT.XR.reprojection
- Finding: XR is the tightest pacing regime (72 to 120 Hz hard deadlines, where a missed frame is a comfort failure). M5 claims three XR configurations, but the only M5 perf gate is scale-content. C-BUDGET has "input-to-photon per refresh class" but no XR line (missed-frame rate, reprojection and late-latch headroom, compositor deadline margin), and no perf owner is named for XR pacing.
- Evidence: OpenXR frame timing and the Meta and Valve guidance on ASW and reprojection quotas: dropped-frame percentage is a certification criterion.
- Proposed change: Add C-BUDGET XR lines (missed deadlines per hour, GPU headroom at the reprojection deadline, motion-to-photon per device class). Add an M5 gate for PRF.LOAD.pacing-latency on the XR configurations, and make loading-streaming-performance and platform XR co-own the measurement method.
### K-PERF-6 · major · omission
- Target: M3 to M5 gates, PRF.CPU.parallel-scaling, PRF.BENCH.sim-worst-case, PRF.MEM.bandwidth, PRF.METH.model
- Finding: The following PRF capabilities have no milestone gate at any stage: parallel-scaling (2 to 64 workers, P/E), sim-worst-case, MEM.bandwidth (UMA and portable console, claimed at M3), METH.model (capacity model) and PIPE.cook (the M6 distributed cook). These are exactly the structural bottlenecks (serialization and bandwidth) the mandate names. The M3 CPU-submission and GPU-driven paths, and the M6 team-large cook, are claimed with no gate on parallel efficiency or cook throughput.
- Evidence: The claimed configurations include lite-3d-portable-console (UMA) at M3 and a distributed cook at M6. A parallel-efficiency line exists in C-BUDGET but nothing enforces it.
- Proposed change: Gate PRF.CPU.parallel-scaling at M3 (validator PRF.BENCH.stats), PRF.MEM.bandwidth at M3 (portable console), PRF.BENCH.sim-worst-case at M5 (validator QA.SIM.mass-agents), and PRF.PIPE.cook and PRF.METH.model at M6.
### K-PERF-7 · minor · wrong-boundary
- Target: PRF.LOAD.pacing-latency, PRF.NET.latency, loading-streaming-performance
- Finding: Steady-state frame pacing and input-to-photon latency (an input, present and display chain) are owned by the skill whose expertise is load and hitch analysis. PRF.NET.latency separately accounts end-to-end networked latency with a different contributor set. The two latency accountings share no stated common budget line or ownership.
- Evidence: A latency stack (input, sim, render, present, display, plus network) is one chain. Splitting it produces double counting in C-BUDGET.
- Proposed change: Make PRF.LOAD.pacing-latency the local segment, with PRF.NET.latency listing it as a required input. Add loading-streaming-performance as a contributor to PRF.NET.latency. Or move the pacing rows to a dedicated latency expert.
### K-PERF-8 · minor · maturity-error
- Target: OBS.LOG.hw-counters, PRF.BENCH.proxy-metrics
- Finding: Both are labeled E. Programmatic PMU and GPU counter capture is unavailable or restricted in common CI (virtualized PMUs are often not exposed by cloud VMs). GPU counters need admin rights, locked clocks or vendor SDKs on PC, and are NDA-gated on consoles. The proxy-metrics gate relies on instruction and cache-miss counts.
- Evidence: Cloud VM PMU restrictions (many providers expose no PMU), NVIDIA Nsight Perf SDK requirements, GPUPerfAPI licensing.
- Proposed change: Relabel the GPU-counter portion as M, keep the CPU PMU E where bare-metal lab hosts are used, and add a fallback rule (proxy metrics on lab hosts only; simulated cache counts via Cachegrind or Valgrind-class tools elsewhere).
### K-PERF-9 · minor · missing-contract
- Target: C-BUDGET, C-PERF, QA.AGENT.baseline-governance
- Finding: There is no defined process for budget exceptions or waivers with an expiry. QA.AGENT.baseline-governance governs threshold changes, but C-PERF covers only findings and territory loans. A subsystem over budget on one tier has no recorded waiver-and-recover path, so agents will either block the milestone or quietly relax C-BUDGET.
- Evidence: Production studios track budget debt with a named waiver, owner and expiry date.
- Proposed change: Add to C-PERF a budget-waiver record (line, tier, owner, expiry, recovery plan) that the gate reads, and require a human or architect signature for waivers that cross a milestone.
