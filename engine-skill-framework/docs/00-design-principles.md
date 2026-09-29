# 00 · Design Principles of the Skill Framework

This document explains *why* the capability map and skill graph are shaped the way they are. The data in `data/` is the source of truth; this is the reasoning a critic should attack.

## 1. What a skill is

A skill is the smallest unit that satisfies all four of these conditions:

1. **Distinct expertise.** It needs a body of knowledge (literature, APIs, hardware behavior) that a neighboring skill does not need. For example, a tire model and a solver share a physics lead but not a literature.
2. **Owned territory.** It owns at least one capability outright, and no other skill owns that capability.
3. **A contract surface.** What it offers to others can be stated as a contract, or it consumes contracts only. Nobody reaches into its internals.
4. **Independent validation.** A critic can decide whether it is correct without evaluating the whole engine.

**Split** a candidate when two parts need different literatures or change at different rates, or when they can be validated separately. **Merge** candidates when they share hot data with no stable interface between them, or when neither can be validated alone. Both rules are applied against the capability map, not against historical engine module lists.

That rule produced 124 skills. The two nearest failure modes are:
- **Too coarse.** "Rendering" as one skill mixes GPU synchronization, color science and strand-hair shading, which are different literatures that are validated differently.
- **Too fine.** "Cascaded shadow maps" as a skill has no contract of its own. It is one technique choice inside `direct-lighting-shadows`, recorded in an ADR.

## 2. Tiers

| Tier | Count | Role |
|---|---|---|
| Orchestrator | 3 | `engine-architect` (boundaries, profiles, arbitration), `architecture-governance` (ADR and fitness-function process), `program-orchestration` (agent coordination). |
| Cross-cutting | 11 | Disciplines that impose an obligation on every skill and review against it: performance, testing, security, observability, crash diagnostics, determinism, hot reload, accessibility, API lifecycle, research evidence, developer experience. |
| Domain lead | 14 | Owns intra-domain architecture and the domain's primary contract, *and* real capabilities. A lead never exists only to coordinate. |
| Expert | 96 | Owns a focused territory; implements; validated independently. |

A lead exists only where a domain has at least three experts with internal contracts. Input, for example, has two skills and no lead. Its action contract is owned by `input-system`, under the platform lead.

## 3. Skills depend on contracts, never on skills

Every dependency edge goes through a **contract** (`data/contracts.json`). This does four things:

- **Replaceability.** It makes subsystems replaceable. `C-PHYS` can be served by an integrated middleware or an in-house solver without touching consumers.
- **Change control.** Contract changes go through the change-request protocol (`C-ORCH`), so parallel agents cannot silently break each other.
- **Layering.** Contracts carry a layer: 0 platform, 1 foundation, 2 engine services, 3 subsystems, 4 game framework, 5 tools, and P for process. Build-level `requires` edges must be acyclic and never point upward. `check.py` enforces this.
- **Cycles.** Runtime data does flow both ways. Animation feeds physics (kinematic bodies) and physics feeds animation (ragdoll, foot IK). Those flows go through frame phases declared in `C-FRAME`, never through direct calls. Required-edge cycles between skills are listed in `02-skill-dependency-graph.md` so each gets an explicit phase-mediated design.

Universal contracts (`C-ERR`, `C-MEM`, `C-INSTR`, `C-CRASH`, `C-BUDGET` for runtime skills; the process contracts for all skills) are consumed implicitly. That keeps the graph readable while still counting them in the configuration-closure proof.

## 4. Ownership patterns used to resolve overlaps

Three patterns resolve almost every boundary dispute. Each is applied by name so that a critic can check it was applied consistently.

- **Format owner vs pipeline host.** The skill that defines a runtime format owns its builder algorithm. The content pipeline hosts the step through `C-COOK`. The cluster-DAG builder belongs to `virtualized-geometry-lod`; animation compression to `animation-runtime`; shader compilation to `shader-system`. `asset-cook-processors` owns only format-neutral processing. This avoids a pipeline team that must understand every runtime format.
- **Policy vs implementation.** One skill decides and another implements when their expertise differs. For example, `world-architect` owns the large-world-coordinate *policy* and `spatial-transforms` the *implementation*; `performance-architect` owns budgets and `memory-allocators` the enforcement mechanism. The two capabilities are separate map entries, so neither is ambiguous.
- **End-to-end feature ownership.** An environment feature (terrain, water, vegetation, atmosphere) is owned end to end by one skill: representation, simulation, rendering and tool logic. It consumes render, physics and editor contracts. The alternative, splitting terrain rendering from terrain data from terrain tools, creates three agents who must change in lock-step for every terrain feature.

## 5. Scaling down is proven, not asserted

Skills carry profile tags. **Configurations** combine a base profile with add-ons (`indie-2d`, `mobile-3d`, `standard-3d`, `open-world`, `online-3d`, `aaa-open-world-online`, `dedicated-server`, `xr-3d`, `indie-2d-online-moddable`). `check.py` proves each configuration is **closed**: every required contract of every member skill is owned by a member skill. A 2D indie configuration therefore cannot require ray-tracing infrastructure. If a skill needs a heavy subsystem only for a high-end feature, it must mark that dependency optional (`C-RT?`) and degrade without it.

The same mechanism shows where scale-down is *not* yet achieved. In round 0, `indie-2d` still contained 86 of 124 skills. Much of that is the development organization itself (testing, build, governance), which every configuration needs. The runtime share is what the critics should examine.

## 6. Default architectural stances

These are the **defaults** that phase-2 skills inherit. Each can be overridden only by an ADR with evidence. Each default exists to prevent a specific legacy pattern.

| Default | Legacy pattern it replaces | Justification |
|---|---|---|
| The engine loop is a task graph of phases with explicit sync points (`frame-orchestration`). | Central `Update()` loop calling subsystems in sequence. | Many-core and hybrid CPUs need dependency-driven scheduling. A sequential loop serializes the frame and hides data races behind ordering. |
| World data is data-oriented and partitioned; hierarchy exists only where attachment requires it (`world-architect`, `spatial-transforms`). | A universal scene graph as the world representation. | Scene-graph traversal is pointer-chasing and serializes transform updates. Open worlds need cell streaming and bulk-parallel updates. |
| Hybrid object model: ECS for bulk homogeneous runtime simulation; services, asset objects and UI objects elsewhere (`entity-object-model`). | Deep inheritance hierarchies, or "ECS for everything". | ECS pays off where many entities share component sets and are processed in bulk. Assets, services and UI trees have different access patterns. Dogmatic ECS inflates structural-change cost and harms tool code. |
| GPU-driven rendering with a CPU-driven fallback path (`gpu-driven-pipeline`). | Draw-call-centric CPU submission. | Moving visibility and command generation to the GPU removes CPU submission cost that grows with scene size. The fallback exists because low-tier and older mobile GPUs lack indirect or mesh-shader features. |
| The render graph owns barriers, aliasing and queue scheduling (`render-graph-scheduling`). Bindless is the default binding model (`rhi-core`). | Global renderer synchronization; slot-based binding inherited from DX11/OpenGL. | Explicit APIs make synchronization the engine's job. A graph can derive it from declared access instead of from hand-placed barriers, and bindless removes per-draw binding cost. |
| Resource lifetimes are explicit and independent of frame boundaries (`resource-streaming-architect`, `gpu-memory-resources`). | "Everything lives until the end of the frame / level". | Streaming worlds and async compute keep resources alive across frames and release them early. Frame-tied lifetimes waste memory and force stalls. |
| All IO and loading is asynchronous, with priorities and deadlines (`async-io-storage`). | Synchronous file reads; blocking level loads. | NVMe throughput is only reached with deep queues. Synchronous waits cause hitches. |
| No hidden globals: services are registered and initialized through an init dependency graph (`core-runtime-architect`). | Singletons initialized in an implicit order. | Parallel boot, testability and the ability to omit modules in small configurations all need explicit dependencies. |
| Instrumentation, tests and budgets exist before features (`C-INSTR`, `C-TEST`, `C-BUDGET` are universal). | Profiling added late. | Performance claims need measurement, and a subsystem that cannot be observed cannot be tuned or debugged. |
| Determinism is a declared level per subsystem (`determinism-replay`). | Determinism as an accident or as a global requirement. | Rollback, lockstep and replay need it where they are used. Requiring it everywhere constrains parallelism for no gain. |

## 7. Technique maturity

Every capability carries a maturity class (established, emerging, experimental, speculative). The class is enforced as follows:

- An **experimental** or **speculative** capability can never be a *required* dependency of an established one. It is always reached through an optional contract or extension point.
- **Emerging** capabilities (work graphs, sampler-feedback streaming, neural texture compression, ReSTIR-class sampling, ML deformers) may be adopted only by an ADR. The ADR must name the evidence, the fallback path, and a *revisit condition*.
- The technology radar (`architecture-governance`) owns promotion between classes. Promotion requires production evidence graded by `research-evidence`, not popularity.

## 8. Specific boundary decisions

| Decision | Reason |
|---|---|
| `render-2d-vector` is also the UI and debug-overlay draw backend. | Sprite batching, SDF text and vector paths share one technique set. Without this, three 2D renderers would be built. |
| Input is split into `input-devices-haptics` and `input-system` (actions). | Device work is platform/HID expertise; action mapping is UX and accessibility expertise. The action contract is what gameplay, UI and accessibility consume. |
| First-party platform services and third-party online backends are one skill (`platform-online-services`). | Both are asynchronous, token-authenticated external service integrations with the same failure modes. Consumers should not care which backend fulfils an entitlement or a session. |
| `anti-cheat-integrity` sits under security, not networking. | It is an adversarial discipline with its own literature. Networking supplies authority and validation hooks through `C-NET`. |
| `ml-inference-runtime` is standalone. | Neural textures, deformers, learned animation, audio and AI all need one inference runtime with one budget. Several private runtimes would compete for the GPU unscheduled. |
| All geometric LOD belongs to `virtualized-geometry-lod`. | Discrete LOD, HLOD, impostors and cluster LOD share simplification algorithms and error metrics. Splitting them repeats the simplifier. |
| `physics-2d` is separate from 3D dynamics. | 2D engines (Box2D class) use different data layouts and solvers. The 2D configuration must not carry the 3D engine. |
| `graph-editor-framework` is shared. | Material, animation, VFX, audio, PCG and visual-script graphs would otherwise produce six node editors with six undo and diff implementations. |
| Determinism, hot reload and API lifecycle are cross-cutting skills, not features of one subsystem. | Each property only holds if every participant follows one protocol. A property owned by one subsystem is violated by the others. |
| CPU/GPU/loading performance experts are separate from subsystem owners. | Owners optimize their own code. Performance experts carry microarchitecture and vendor-tool expertise across subsystems and review it; they do not own the code. |
| Online backend services (matchmaking servers, economy, fleet operation) are outside engine scope. | The engine owns the integration boundary, not the backend. The boundary is explicit so no agent builds a backend by accident. |

## 9. What phase 1 deliberately does not decide

- **Technique selection inside a skill.** For example, archetype vs sparse-set ECS, or virtual shadow maps vs ray-traced shadows as the default. Those are phase-2 SKILL.md content and implementation-time ADRs. Phase 1 only guarantees that each question has exactly one owner and that the alternatives are visible (see `06-gap-analysis.md`).
- **Contract APIs.** A contract here is a named responsibility with a layer and dependencies, not an interface definition.
- **Technology choices** such as language, shading language or middleware. They are ADRs owned by the skills named in the map.
