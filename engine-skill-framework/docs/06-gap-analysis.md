# 06 · Gap Analysis

This document covers two things:

- **Thin evidence.** Where authoritative information is scarce, so an agent cannot "look up the answer".
- **Competing approaches.** Where several credible approaches compete, so the choice must be an ADR with evidence and revisit conditions, never a habit.

Each row names the owning skill and how the owner must close the gap. That is usually a **spike** (a prototype that produces evidence), a **benchmark** (a measured comparison on representative workloads), or a **deferred decision** with an explicit revisit condition.

Evidence tiers used below: **T1** production postmortems and engineering presentations; **T2** platform-holder documentation; **T3** engine documentation; **T4** peer-reviewed research; **T5** reproducible benchmarks; **T6** hardware architecture documentation. Blogs, forums and popularity are not evidence (see `research-evidence`).

## A. Where authoritative information is scarce

| # | Area | Why evidence is thin | Owner | How to close it |
|---|---|---|---|---|
| A1 | Console platform internals (memory reservations, IO and decompression hardware, certification rules, OS scheduling) | NDA-gated. Public material covers only the headline architecture (e.g. platform-holder keynotes). | platform-console, certification-compliance | Treat as *interfaces with unknown parameters*: design the PAL against the public architecture, and fill the parameters from platform-holder documentation when licensed. Never invent console numbers. |
| A2 | Editor architecture at AAA scale (process model, transaction systems, world editing for 100+ concurrent editors) | Few talks; most knowledge is proprietary and folklore. | editor-architect, collaboration-version-control | Spike: out-of-process vs in-process runtime with a live-link prototype. Measure editor start time, crash isolation and PIE latency on a synthetic 10⁶-object world. |
| A3 | Large-scale streaming for *authoring* (not just runtime) | Runtime streaming is well described (world partition docs, open-world GDC talks). Editor-side partial loading, and conflict-free editing at scale, is rarely published. | world-architect, world-editor-viewport | Spike with generated worlds at 3 scales; measure load and save times and merge-conflict rates. |
| A4 | Cross-platform floating-point determinism in production | Most shipped rollback titles are same-platform or use fixed-point. Cross-platform float reproducibility depends on compilers, FMA contraction and transcendental functions. | determinism-replay, math-simd-numerics | Build a determinism test matrix (compilers × ISAs × flags) with state hashing. Decide per subsystem between fixed-point, restricted float and "same binary only". |
| A5 | Spatially sharded multi-server worlds ("server meshing") | One live deployment (Star Citizen, since late 2024), sparse technical publication, and high vendor marketing content. | server-scaleout-persistence | `emerging` (M) in data and radar. `C-SHARD` must not preclude authority transfer; zoning is the fallback. Revisit when two or more shipped titles publish technical postmortems. |
| A6 | Work graphs in production | The spec is shipped and vendor samples exist, but there are almost no shipped-title postmortems. Performance varies by vendor and driver. | render-graph-scheduling | Benchmark work-graph vs indirect-dispatch implementations of one GPU-driven culling pipeline on all three desktop vendors. Adopt behind a capability tier with an indirect fallback. |
| A7 | Neural rendering in shipped games (neural texture compression, neural materials, neural radiance caching) | Research and SDK demos exist; production evidence is limited and depends on tensor/cooperative-vector support. | texture-streaming-vt, material-system, ml-inference-runtime | Capability-tiered opt-in only. Benchmark decode cost vs BCn at equal quality (perceptual metric) on min-spec GPUs. Revisit on cross-vendor shader-model support for cooperative vectors. |
| A8 | Learned animation in production (learned motion matching, neural controllers) | Strong research (SIGGRAPH), few production postmortems; memory/runtime vs quality trade-offs are title-specific. | motion-synthesis | Keep classic motion matching as the baseline. A learned variant needs an ADR comparing memory, runtime cost and quality on the same dataset. |
| A9 | GPU-driven rendering on mobile and TBDR GPUs | Mesh-shader and indirect support and performance vary widely; published guidance is vendor-specific. | geometry-pipeline, platform-mobile | Keep the CPU-driven fallback as a first-class path. Device-capability database drives selection; benchmark on representative devices. |
| A10 | Shader compilation stutter on PC | Root cause is well understood; the best mitigation (PSO precompilation, pipeline libraries, graphics pipeline libraries, driver caches) is API- and vendor-dependent and changes with driver releases. | rhi-core, shader-system, loading-streaming-performance | Measured hitch budget per first-encounter PSO. Automated PSO-coverage gathering from play traces; regression test on a clean driver cache. |
| A11 | Memory-safety posture for a C++ engine | Guidance exists (hardening modes, safe subsets, Rust interop), but there is little production evidence for engines specifically. | security-engineering, core-runtime-architect | ADR: which layers must accept untrusted input, and therefore get hardened containers, bounds checking in shipping builds and fuzzing. Evaluate Rust/Swift interop only for parsers of untrusted data. |
| A12 | LLM-driven NPCs | Generated dialogue on non-authoritative state has shipped (2025, cloud/hybrid); model decisions on authoritative state have not. Latency, cost, moderation, determinism and rating remain largely unresolved. | ai-behavior-perception | Split: `GAM.AI.llm-dialogue` is emerging (M), `GAM.AI.llm-decision` is experimental (X, `experimental` profile). Both only behind `C-AIAGENT` (gated, optional) with moderation (`online-services-liveops`, or `GAM.AI.local-guardrails` offline), a budget, an authored fallback, and outputs recorded as external inputs for replay. |
| A14 | Cross-pool memory arbitration | Engines publish pool-specific streaming talks; few describe the arbiter that balances texture, geometry, shadow, audio and BVH pools on UMA hardware. | resource-streaming-architect | Spike: two pools under synthetic pressure; measure oscillation and starvation with and without a central priority space. |
| A15 | Dedicated-server world streaming and persistence boundary | Little published about server-side cell activation and write-behind persistence for open worlds. | world-architect, server-scaleout-persistence | Spike on the aaa-open-world-online-server configuration with bot clients (online-3d-bot-client). |
| A13 | Validation of autonomous-agent-produced engine code | New discipline; little evidence on failure modes of agent-written systems code at this scale. | test-architect, program-orchestration | Mutation testing to detect vacuous tests; independent critic gates per stage; "a guard never seen to fail is not a guard" (every check has a red case). |

## B. Where significant competing approaches exist

Each row is a decision that an owning skill must record as an ADR. The phase-2 SKILL.md for the owner must present the alternatives with evidence rather than a default by habit.

| # | Decision | Competing approaches | Owner | What decides it |
|---|---|---|---|---|
| B1 | ECS storage | Archetype/chunk (Unity Entities, Flecs) vs sparse set (EnTT) vs hybrid | ecs-runtime | Iteration-heavy vs structural-change-heavy workloads; benchmark both on the engine's representative entity mixes. |
| B2 | Task model | Work-stealing thread pool + task graph vs fiber-based jobs (Naughty Dog GDC 2015) vs C++20 coroutines | job-system-task-graph | Blocking/waiting patterns, debugger/profiler support, platform fiber support, hybrid-core scheduling behavior. |
| B3 | Shading path | Deferred vs forward+ vs visibility buffer | render-architect | Material complexity, MSAA/transparency needs, bandwidth on TBDR, virtualized geometry. A per-tier answer is allowed. |
| B4 | Shadows | Virtual shadow maps vs ray-traced shadows vs cascades; stochastic many-light shadowing | direct-lighting-shadows | Tier: RT hardware availability, geometry density, light count. |
| B5 | Dynamic GI | Probe volumes (DDGI class) vs surface/radiance-cache hybrid (Lumen class) vs ReSTIR GI vs baked | global-illumination | Hardware tier, dynamic-content needs, memory. Baked stays for low tiers. |
| B6 | Physics engine | Integrate (Jolt, PhysX, Havok, Box2D v3) vs build | physics-architect | Determinism needs, source access, licensing, feature coverage, performance on target workloads. |
| B7 | Audio engine | Own mixer vs middleware (Wwise, FMOD) | audio-architect | Sound-designer workflow, licensing, platform support, spatial-audio feature needs. |
| B8 | Scripting | Luau/Lua vs .NET (C#) vs Wasm vs visual-only vs none | scripting-runtime | Console AOT constraints, sandboxing (mods), iteration speed, GC pauses, team skills. |
| B9 | Shading language | HLSL (DXC) vs Slang vs cross-compiled | shader-system | Multi-backend reach (SPIR-V, Metal, DXIL), modules/generics, tooling maturity, Khronos governance of Slang. |
| B10 | Netcode model | Server-authoritative + prediction vs rollback vs lockstep vs hybrid | network-architect | Genre, player count, determinism budget, bandwidth. |
| B11 | Game UI | Retained with data binding vs immediate vs embedded web tech | ui-architect | Designer tooling, performance on consoles, accessibility API integration, localization layout. |
| B12 | Interchange | OpenUSD as authoring backbone vs glTF/FBX import only | asset-import-interchange, content-pipeline-architect | DCC ecosystem, composition needs, pipeline scale. |
| B13 | Reflection | Code generation vs C++26 static reflection vs macros | reflection-metadata | Toolchain availability across all target compilers (revisit condition: C++26 reflection on every platform compiler). |
| B14 | Build system | CMake vs FASTBuild vs Bazel/Buck2-class with remote execution | build-system-toolchains | Distributed build, cache hit rates, console SDK integration. |
| B15 | Version control | Perforce vs Git + LFS vs newer large-binary VCS | collaboration-version-control | Binary scale, locking, branching model, cost. |
| B16 | Engine editor process model | Editor hosts runtime in-process vs out-of-process runtime with live link | editor-architect | Crash isolation, iteration latency, memory, platform live editing. |
| B17 | Texture streaming | Mip streaming vs sampler-feedback streaming vs full virtual texturing | texture-streaming-vt | Hardware tier, memory, content scale. |
| B18 | Package compression | Kraken/Oodle-class vs zstd vs LZ4 vs GPU (GDeflate) | package-formats-vfs | Decode throughput vs ratio on target CPUs and GPU decompression availability; licensing. |
| B19 | Upscaling | Vendor ML upscalers vs in-house temporal upscaler vs both behind one interface | reconstruction-upscaling | Platform coverage (consoles, mobile), quality, latency. |
| B20 | Transform/LWC representation | 64-bit world positions everywhere vs cell-relative 32-bit + origin rebasing | world-architect, spatial-transforms | World size, physics/GPU precision, network quantization. |
| B21 | Submission strategy per tier | GPU-driven (culling, indirect, mesh shaders, visibility buffer) vs CPU-culled batched/instanced | render-architect, geometry-pipeline | GPU tier (TBDR vs immediate-mode), indirect/mesh-shader support, bandwidth. |
| B22 | Binding model per tier | Bindless vs descriptor buffers vs bounded bind groups | gpu-platform-architect, rhi-core | Backend and device limits (WebGPU, Android descriptor indexing). |
| B23 | Physics middleware mode | In-house vs integrated middleware with an engine-side integration layer | physics-architect | Rewind/snapshot support, determinism level, source access (see PHY.ARCH.middleware-layer). |
| B24 | Server scale-out | Single-server vs zoning/instancing vs seamless meshing | server-scaleout-persistence | Player density, world size, authority-transfer cost; meshing is emerging with zoning as fallback. |
| B27 | Netcode family per game | Server-authoritative + prediction vs lockstep vs rollback vs async | network-architect | Genre, player count, determinism budget; each family is a separate add-on profile with its own configuration. |
| B28 | Mod execution model | Sandboxed scripts/graphs only vs native plugins behind opt-in | modding-ugc, security-engineering | Distribution-channel risk (signed updates, revocation), platform policy; sandboxed by default. |
| B25 | Gameplay control model | Possession-style controller/pawn vs data-oriented control binding vs genre-specific | gameplay-architect | Genre, multiplayer model, input-to-entity cardinality. |
| B26 | Game UI technology | Retained engine UI vs embedded web UI; editor toolkit shared with game UI or not | ui-architect, editor-ui-framework | Console performance, accessibility tree export, designer tooling. |

## C. Known coverage weaknesses of this framework itself

These are admitted limits of phase 1 that critics should keep testing:

1. **Parameters behind NDAs.** Console-specific skills can be *structured* now but not *filled*. Phase 2 must mark console content as "requires licensed platform documentation".
2. **Game-specific systems.** Quest *content*, inventory rules and economy design are game code on top of `C-GAME`. Round 1 moved some of this territory into the engine: the dialogue line model and narrative state (`narrative-dialogue`), designer data (`gameplay-data`) and character movement (`character-movement`), because each carries formats shared across four or more engine domains. The boundary may still be challenged per genre.
3. **Backend services.** Backend services are outside engine scope by decision (`engine-architect` non-goal register). The engine owns only the integration boundary, the server process lifecycle (`C-SERVER`) and server artifacts.
4. **Membership is "may be built", not "must be built".** A configuration's members are the skills available to it; a game built on that configuration uses a subset. Milestones therefore prove availability, and the reference game of each configuration proves use.
5. **Critic misses.** Round 2 critics missed three planted seeds in their own mandates (continuous collision, lag compensation, golden-image tests). Those critics are on a first strike (PROTOCOL.md).
