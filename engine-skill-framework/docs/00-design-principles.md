# 00 · Design Principles of the Skill Framework

This document explains *why* the capability map and skill graph are shaped the way they are. The data in `data/` is the source of truth; this is the reasoning a critic should attack. Schema v1 (after G1 round 1) is described here; `gauntlet/round-1/` records what changed and why.

## 1. What a skill is

A skill is the smallest unit that satisfies all four of these conditions:

1. **Distinct expertise.** It needs knowledge that a neighbor does not: literature, APIs, hardware behavior. For example, tire models and constraint solvers share a physics lead but not a literature, which is why vehicle physics is a separate skill.
2. **Owned territory.** It owns at least one capability outright, and no other skill owns it.
3. **A contract surface.** Anything it offers to others is a contract, and it reaches others only through their contracts.
4. **Independent validation.** A critic can decide whether it is correct without evaluating the whole engine.

**Split** a unit when its parts need different literatures, change at different rates, or are validated separately. **Merge** units that share hot data without a stable interface, or that cannot be validated alone. Both rules are applied to the capability map, never to historical engine module lists.

The rules produced **154 skills** (round 2 added sessions, server scale-out, server host PAL, console RHI backends, gameplay camera, systems simulation, test runtime harness, security runtime, online performance and privacy). `check.py` warns on experts that own fewer than three capabilities (too fine) and on skills that own more than thirty (too coarse).

## 2. Tiers and kinds

| Tier | Count | Role |
|---|---|---|
| Orchestrator | 4 | `engine-architect` (boundaries, profiles, arbitration across workstreams), `architecture-governance` (ADRs, fitness functions, radar, anti-legacy catalogue, critic calibration, adjudication and the independence matrix), `program-orchestration` (agent coordination, milestones, ledger, triage), `engine-product-management` (roadmap and game-team intake: the engine as a product). |
| Cross-cutting | 11 | Disciplines that impose an obligation on every skill and review against it: research evidence, performance, testing, security, observability, crash diagnostics, determinism, hot reload, accessibility, API lifecycle, developer experience. |
| Domain lead | 15 | Owns the architecture inside its domain and at least one contract. `check.py` rejects a lead that provides no contract. |
| Expert | 123 | Owns a focused territory, implements it, and is validated on its own. |

**Kinds** are independent of tiers:

- **runtime** (118): code that ships in builds.
- **tool** (12): ships only in the tools target, i.e. the editor, cooker and pipeline.
- **process** (23): organizational (governance, testing, performance analysis, documentation) and never part of a build.

The configuration-closure proof therefore measures *engine* scale-down separately from the organization that builds the engine.

**Workstreams** (foundation, platform, content, world, rendering, simulation, audio, online, gameplay, UI, tools, release, quality, performance, governance, assurance) group skills for delegated arbitration and staffing. They are also the co-hosting unit, so the independence matrix (`data/crosscutting.json`: decider vs reviewer, builder vs adjudicator, implementer vs oracle author) is enforced by keeping each pair in different workstreams. A dispute inside one lead's subtree is settled by that lead. Only cross-workstream disputes reach `engine-architect` (`ARCH.ORG.escalation`).

## 3. Skills depend on contracts, never on skills

Every dependency edge goes through a **contract** (`data/contracts.json`, 129 contracts). Contracts carry a layer: 0 platform, 1 foundation, 2 engine services, 3 subsystems, 4 game framework, 5 tools, and P for process contracts. `check.py` enforces the following properties.

- **Contract layering.** Build-level `requires` edges are acyclic and never point upward.
- **No upward module links.** A runtime skill's code may only consume contracts at or below the layer of the module doing the consuming. A skill that ships several modules attributes each dependency to one of them. For example, `C-SER@C-SNAPSHOT` means the snapshot module (L2) needs serialization, while the L1 determinism-rules module does not.
- **Tool code stays on the tool side.** Tool contracts (L5) may only be consumed from `tool_consumes`, so editor code can never enter a shipping or server build.
- **Acyclic bootstrap.** The foundation tier (L0/L1 modules) is acyclic even when the implicit universal contracts are counted. The proof runs at module granularity: a skill's higher module (for example the governor, `C-GOVERN`) may depend on skills that depend on its lower module (`C-SCALE`). `C-BASE` breaks the classic allocator↔logging↔config cycle: a raw allocator, raw sinks and hook tables that higher layers install later.
- **Universal contracts.** For runtime skills at L2 and above these are `C-ERR`, `C-MEM`, `C-INSTR`, `C-CRASH`, `C-SCALE`, `C-LIFETIME`, `C-MOD`, `C-CFG` and `C-TESTHOST`. For every skill they are the process contracts, including the `C-CERT` requirement register and the `C-PERF`/`C-BENCH` protocols.
- **Skills without a module of their own** take their lead's highest code layer as floor, so an animation expert cannot link into the gameplay layer.
- **Data flow between subsystems.** Runtime data travels through **channels** (`C-FLOW`: versioned snapshots, buffered hand-off, mailboxes, multi-rate resampling) under an engine-wide **access model** (`C-FRAME`). Ordering is derived from declared reads and writes. A global barrier needs an ADR.

## 4. Ownership patterns used to resolve overlaps

Five patterns resolve almost every boundary dispute. Each is applied by name, so a critic can check that it was applied consistently.

- **Format owner vs pipeline host.** The skill that defines a runtime format owns the builder algorithm that produces it. For example, the cluster-DAG builder belongs to `virtualized-geometry-lod`, lightmap UVs to `global-illumination`, and sprite atlases to `render-2d-vector`. The content pipeline hosts these builders through `C-COOK`, and `asset-cook-processors` owns only format-neutral processing.
- **Policy vs implementation.** When the expertise differs, one skill decides and another implements.
  - Large-world-coordinate policy belongs to `world-architect`; the implementation belongs to `spatial-transforms`.
  - Budget numbers belong to `performance-architect`; the runtime governor belongs to `runtime-scalability`.
  - Residency policy belongs to the cross-pool arbiter in `resource-streaming-architect`; the residency mechanism belongs to `gpu-memory-resources`.
- **End-to-end feature ownership.** One skill owns an environment or feature system end to end: representation, simulation, rendering and tool logic. Environment skills keep their render dependencies optional, so their simulation and query halves still build headless.
- **Domain editor = domain tool logic + editor host.** Every user-facing runtime domain owns its authoring logic in a `<DOMAIN>.TOOL` capability, for example `RND.TOOL.material-editor`, `ANM.TOOL.retarget-editor` or `GAM.TOOL.ai-editors`. The editor skills provide the host through `C-EDCMD` (serializable commands, undo, selection), `C-EDHOST` (asset-editor host, thumbnails, curves and timelines), `C-EDVIEW` (viewport tool modes, brushes, picking, gizmos, preview worlds), `C-GRAPH` and `C-VCS`. `check.py` fails any skill that owns tool logic but reaches the editor through no contract, any world tool that does not reach `C-EDVIEW`, and any user-facing runtime domain whose subtree owns no authoring capability and records no reason.
- **Contract owner vs implementer.** A contract can have one owner and several implementers.
  - `C-RHI` is owned by `rhi-core` and implemented by the D3D12, Vulkan, Metal, WebGPU and confidential console (`rhi-console`, one agent per platform holder) backends.
  - `C-PAL` is owned by `platform-architect` (interfaces and policy) and implemented by `platform-desktop`, `platform-console`, `platform-mobile`, `platform-web` and `platform-server-host`. `C-TARGETPLAT` (tool side) is implemented by the same skills for cooking, packaging and deploying to each target.
  - `C-ENV` is owned by `world-architect` and implemented by terrain, water, atmosphere and voxel worlds.
  - Where a contract needs an implementer, `check.py` proves that every configuration contains one for each of its platforms (a tools configuration also covers its `target_platforms`).

## 5. Scaling down is proven, not asserted

A **configuration** is a point on three independent axes:

- **Scale/feature profiles.** A base profile (`minimal`, `min2d`, `lite3d`, `std3d`) plus add-ons (`openworld`, `online` (server-authoritative), `online-lockstep`, `online-rollback`, `online-async`, `aaa`, `xr`, `ugc`, `massim`, `sandbox`, `vehicles`, `team-large`, `experimental`).
- **A build target.** `client`, `headless-client`, `server` or `tools`.
- **Target platforms.** `pc`, `console`, `mobile`, `web`, `xr-standalone` or `server-host`.

Round 0 mixed these three axes. That made it impossible to express, for example, the server half of an open-world game or a 2D indie game shipping on console.

`check.py` proves all 39 named configurations are closed. These run from `indie-2d-online-moddable-server` (61 build skills), `online-3d-bot-client` (68), `mobile-async-client` (70) and `minimal-client` (75) up to `aaa-open-world-online-tools` (123). Every configuration is claimed by exactly one milestone, which proves it buildable by then. Capability-level profile tags provide finer gating inside a skill:
- Virtual shadow maps, cluster LOD and visibility buffers are `std3d`.
- Strand hair and real-time path tracing are `aaa`.
- Multi-user editing, distributed cooking and build farms are `team-large`; locking and artifact retention are not.
- Every experimental (X/S) capability carries only the `experimental` profile, so no shipping configuration depends on one (`aaa-experimental-client` proves the opt-in path).

Organizational scale-down is handled separately. A small effort co-hosts the skills of one workstream in one agent (`ARCH.ORG.staffing`), and the governance weight per organization tier is defined in `ARCH.GOV.process-tiers`.

## 6. Default architectural stances

These are the **defaults** that phase-2 skills inherit. Each one can be overridden only by an ADR with evidence. This table is a summary: the full catalogue (74 patterns, including editor, networking, simulation, security and validation legacy) is `data/legacy-patterns.json`, where every pattern names the capabilities that carry its stance and `check.py` verifies that they exist, are owned in the justification owner's subtree, and that no capability name, contract text or skill purpose matches a pattern's `contradiction_terms` (unless `adr_exceptions` records an ADR).

| Default | Legacy pattern it replaces | Justification |
|---|---|---|
| The frame is a task graph compiled by one scheduler (frame-orchestration). Ordering comes from declared data access (`C-FRAME`), phases are ordering constraints rather than barriers, data moves through channels (`C-FLOW`), and the canonical simulation dependency order and multi-rate domains are explicit. The same graph runs inline on 0–2 workers (web, low-end). | A central `Update()` loop, or a fixed sequence of tick groups with barriers. | Many-core and hybrid CPUs need dependency-driven overlap. Phase barriers serialize the frame and hide races. |
| No fixed game, render or RHI threads. Render work runs as tasks in overlapping task-graph frames. The thread inventory has one owner (`CORE.JOBS.thread-model`); a dedicated thread requires an ADR, and OS-thread-affine APIs sit behind PAL queues. | The game-thread/render-thread split; main-thread-only APIs. | A fixed-thread split caps parallelism at the thread count and forces per-frame hand-off copies. |
| World data is data-oriented; 3D worlds are partitioned and streamed, small games load whole units asynchronously. Multiple isolated worlds per process, no current-world global. Hierarchy exists only where attachment requires it. | A universal scene graph; a process-global current world. | Traversing a scene graph chases pointers and serializes transform updates, and open worlds need cell streaming anyway. |
| Hybrid object model: ECS where bulk homogeneous simulation benefits. Subsystem contracts are ECS-independent (handles plus batched streams) and bridged to ECS by adapters. | Deep inheritance hierarchies, or "ECS for everything". | ECS pays off only for bulk homogeneous access. Making physics, audio or transforms depend on ECS would prevent middleware integration and force ECS into minimal games. |
| The gameplay framework is built from composed components, systems and services. Control binding is data, and the control model is chosen per game. | Actor→Pawn→Controller "possession" adopted by habit; per-object `Tick()`. | Possession does not fit RTS, card, simulation or MMO games, and per-object ticking is a known scaling limit. |
| The submission strategy is chosen per hardware tier by ADR. The GPU-driven path is the default on desktop and console. The CPU-culled batched path is first-class on TBDR/lite3d. 2D draws through batched draw lists by design. | Draw-call-centric CPU submission on capable tiers, or GPU-driven dogma on mobile. | GPU-driven submission removes CPU cost that grows with scene size on capable GPUs. On TBDR GPUs, indirect draws and extra compute passes often cost more than they save. |
| The render graph owns barriers, aliasing and queues. Binding follows tiers: bindless where the hardware supports it, bounded bind groups on WebGPU and low-end mobile. | Global renderer synchronization; DX11/OpenGL slot binding. | Explicit APIs make synchronization the engine's job. WebGPU and part of Android lack bindless. |
| Simulation-to-render extraction is change-tracked, with delta upload into a persistent instance scene. Cost is O(changes). | Per-object render proxy mirrors. | Per-proxy synchronization scales with object count instead of change count. |
| Explicit lifetimes: generational handles plus a retirement service keyed to completion tokens for tasks, frames in flight and GPU fences. There is no tracing GC over engine objects. | Frame-tied lifetimes; GC-managed engine objects. | Streaming and async compute keep resources alive across frames, and GC causes hitches. |
| All IO is asynchronous and staged (IO → decompress → fixup → upload → publish), with deadlines and cross-pool arbitration under one physical budget; GPU-side transfers and decompression are arbitrated by the render graph (`RND.GRAPH.external-work`). | Synchronous loads; page-fault streaming; independent streaming pools that compete. | NVMe throughput requires deep queues. On UMA hardware, texture, geometry, audio and BVH pools share one memory. |
| No hidden globals: services and self-registration run through an init graph, and config is read through immutable snapshots. | Implicitly initialized singletons; global cvars read from any thread. | These are required for parallel boot, testability and small configurations. |
| Contracts are bound at compile, link or load time and are batch-granular. | Virtual dispatch per draw, body or query across a contract. | Removes per-item overhead on hot paths while keeping subsystems replaceable. |
| Instrumentation, tests, budgets and determinism levels exist before features (milestone gates from M0). Every code contract has an oracle author who is not its sole implementer; acceptance suites are read-only for implementers and have sealed holdouts. | Profiling and testing added late; implementers grading their own tests. | Performance claims need measurement, and autonomous implementers can game tests they control. |

## 7. Technique maturity and the radar

Every capability carries a maturity class: established, emerging, experimental or speculative. `data/radar.json` lists every non-established capability with its owner, evidence, a revisit/promotion trigger and a fallback. Explicit non-goals are also recorded there: backend services, RISC-V, BCI, CXL, linked/AFR multi-GPU, GLES/WebGL backends (web targets require WebGPU; the revisit trigger is the measured browser-capability share, `PLAT.WEB.audience-share`) and generative world models. `check.py` fails any non-established capability that is missing from the radar, any radar entry whose class differs from its capabilities' maturity or whose owner neither owns nor leads them, and any M/X/S entry without a fallback.

Emerging and experimental techniques are reached through optional contracts or extension points. The gated contracts `C-ML`, `C-MLGPU`, `C-RT`, `C-RTAS` and `C-AIAGENT` may only be consumed optionally, and no non-gated contract may require one (`check.py`), so non-RT and non-ML builds stay buildable. Products that require hardware RT or tensor support are expressed as the `hwrt` add-on plus the `rt` and `rt+tensor` GPU tiers of `C-GPUTIER` (configuration `rt-required-3d-client`), not by making the contract mandatory. Experimental capabilities are additionally confined to the `experimental` profile. Work graphs are an optional part of `C-RG` (`RND.GRAPH.work-graphs`, X).

## 8. Specific boundary decisions

| Decision | Reason |
|---|---|
| `gpu-platform-architect` leads the RHI, the API backends (including console), GPU memory, the render graph, shaders and acceleration structures (`C-RTAS`; the render-scene binding `C-RT` is a separate module). ML inference sits under `core-runtime-architect` because its main consumers (audio, AI, accessibility) are not rendering. `render-architect` leads the pipeline and its features. | The GPU platform and render features have different literatures and change at different rates, and the split halves the render lead's span of control. |
| One skill per graphics API backend. Console backends are `rhi-console`; console skills carry an NDA access class and are instantiated per platform holder. | Each API has its own specification, validation layers and release cadence. NDA access is per platform holder (`PLAT.PAL.confidential-extensions`); `check.py` confines NDA skills to the console platform. |
| `render-2d-vector` is the draw backend for 2D games, UI and developer overlays. `visual-debugging-tools` owns the in-game developer UI (`C-DEVUI`). | One batching, SDF and vector technique set. Developer UI must exist in development builds on every target, including servers. |
| Input is split into devices (`C-DEVICE`) and actions (`C-INPUT`). The action schema and tick-stamped command frames exist on every target. | Servers simulate from networked input commands; device binding exists only on clients. |
| Views are arbitrated in `spatial-transforms` (`C-VIEW`). Gameplay cameras, cinematics, editor, photo mode and XR are sources of views. | The editor and XR must drive views without the gameplay layer, and listeners, streaming sources and LWC origins derive from the active view. |
| First-party platform services (`platform-services`) are separate from third-party and live-ops backends (`online-services-liveops`). | The first is NDA SDKs plus certification. The second is web-service and live-operations engineering. |
| `ml-inference-runtime` owns standalone networks (`C-ML` for CPU/NPU, `C-MLGPU` for render-graph passes). `shader-system` owns in-shader neural evaluation. | One runtime keeps a single budget for standalone networks. Fused networks are shader code, and their cost belongs to the pass that hosts them. |
| Character movement, gameplay data, narrative & dialogue, the gameplay camera and systems simulation are engine skills. | Each sits at the junction of four or more domains, with shared formats that no single game team can own. Quest *content* stays game code. |
| Determinism, snapshot/resimulate and replay are one cross-cutting skill with three contracts: `C-DET` (L1 rules), `C-SNAPSHOT` (L2) and `C-REPLAY` (L3). | The properties hold only if every participant follows the same protocol. The split keeps each module on its correct layer. |
| Performance experts analyze and route findings through `C-PERF` to the owning skills. They own analyzers, gates and baselines, not subsystem code. | Two agents must never own one file set. Findings become change requests or time-boxed territory loans. |
| Validation of agent-produced work is owned separately (`QA.AGENT.*`): independent oracles, governed baselines, detection of weakened tests, and mutation gates. | Implementers must not control the oracles that judge them. |
| Netcode is split by lifecycle: `net-session` (handshake, join, reconnect, travel, hosting modes in every build), `dedicated-server` (headless builds, host lifecycle, density, admin surface), `server-scaleout-persistence` (zoning, meshing, persistence, transactions). Netcode families are separate add-ons (`online`, `online-lockstep`, `online-rollback`, `online-async`), and `C-PREDICT` no longer requires `C-REP`. | Listen servers and P2P hosts run inside clients; input-only netcode must not link state replication; multi-server authority needs one contract (`C-SHARD`). |
| Runtime automation and introspection (`C-AUTOMATION`) is owned by `visual-debugging-tools`, a runtime skill; the LLM/agent front end is an editor capability. | Agents drive device, server and soak builds, not only the editor; the protocol must ship in development builds on every target. |
| Security-critical runtime code (crypto, signed artifacts, anti-rollback) is `security-runtime` (`C-SIGN`); policy stays with the process skill `security-engineering`, privacy with `privacy-data-protection`. | Six verifiers must share one envelope and trust store; a process skill cannot own code. |
| Test infrastructure that ships as code is `test-runtime-harness` (`C-TESTHOST`, universal); strategy stays with `test-architect`. Every code contract names an oracle author. | Test runners and fault points must build on every target; implementers must not write the suites that judge them. |
| Backends, game-specific content and model training are outside scope, marked by explicit `external:*` sentinels in non-responsibilities. | The engine owns the integration boundaries, and the sentinels stop agents from routing out-of-scope work to the root architect. |

## 9. What phase 1 deliberately does not decide

- **Technique selection inside a skill.** Examples are ECS storage, the default shadowing technique and the scripting language. These are ADRs owned by the skills named in `06-gap-analysis.md` §B.
- **Contract APIs.** A contract here is a named responsibility with a layer, dependencies and obligations, not an interface definition. Contract specifications are the first step of phase 2.
- **Per-module file globs.** Write sets follow the convention `src/<skill-id>/`, `tools/<skill-id>/`, with tests owned by the test-owning skill. Concrete globs arrive with code at M0.
