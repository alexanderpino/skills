# K-FUTURE · Future-Technology Critic · Round 1 (blind)

Scope: this review checks whether the framework prevents technologies likely to matter over the next ~5 years, and whether its maturity labels are honest. Basis: data/*.json and docs/00. `check.py` reports 0 errors and 2 warnings, so the structure is not re-derived here.

### K-FUTURE-1 · major · missing-contract
- Target: GAM.AI.llm, GAM.AI.learned (ai-behavior-perception); WLD.PCG.ml (procedural-generation); PHY.SOFT.ml (cloth-deformables); RND.MAT.neural (material-system); C-ML
- Finding: Five of the 43 non-established capabilities are owned by skills that have no contract path to the inference runtime. These are all 5 X-class capabilities, which covers every ML item the framework labels experimental. `ai-behavior-perception` consumes only `C-GAME, C-NAV?, C-SPATIAL, C-PHYS`. `procedural-generation` has `C-WORLD, C-COOK?, C-DET, C-GRAPH?`. `cloth-deformables` has `C-PHYS, C-ANIM, C-RG?`. `material-system` has `C-SHADER, C-GRAPH?, C-ASSET`. None of them consumes `C-ML?`. Principle 3 says skills depend only on contracts. An agent assigned any of these capabilities therefore has two options: reach into `ml-inference-runtime` internals, or build a private runtime. Principle 8 prohibits the second ("several private runtimes would compete for the GPU unscheduled"). The "extension point" that principle 7 promises for experimental items does not exist for exactly the items it is meant to protect.
- Evidence: The consume lists in skills.json, compared with the owners in capabilities.json. Other skills with ML capabilities do declare `C-ML?` (texture-streaming-vt, reconstruction-upscaling, deformation-skinning, motion-synthesis, facial-animation, ai-assisted-authoring), so the omission is inconsistent rather than deliberate.
- Proposed change: Add `C-ML?` to the consumes of ai-behavior-perception, procedural-generation, cloth-deformables and material-system. Add a fitness function to check.py: every skill that owns a capability whose name or maturity marks it ML/neural (or that lists ml-inference-runtime as a contributor) must consume `C-ML` or `C-ML?`. Also add `C-SVC?` to ai-behavior-perception (see K-FUTURE-5).

### K-FUTURE-2 · major · dependency-error
- Target: C-ML, ml-inference-runtime, ML.RT.*
- Finding: The inference contract has five problems.
  - (a) Layering. `C-ML` is layer 2 and declares `requires: [C-RHI, C-TASK]`, but its owner consumes `C-RG`, which is layer 3. The contract hides an upward dependency that the checker does not see, because it checks contract `requires` and not the owner's consumes.
  - (b) GPU-only. `C-ML` requires `C-RHI`, which is client-only. The `dedicated-server` configuration therefore cannot run inference at all: no learned bots, no ML cheat detection (XC.SEC.abuse), and no server-side NPC policies.
  - (c) No NPU. ML.RT.inference lists "GPU cooperative-vector / tensor paths, CPU paths". NPUs are absent, although they ship in every Apple/Qualcomm/MediaTek SoC, in Copilot+ PCs (Windows ML / DirectML NPU EPs) and in AMD/Intel client CPUs. Running audio ML, lip sync or LLM on the NPU keeps the GPU frame budget free.
  - (d) Profile. The skill is tagged `aaa` only. Neither mobile-3d, whose devices have the best NPUs, nor standard-3d can use the shared runtime, although their skills declare `C-ML?`.
  - (e) No remote inference path (see K-FUTURE-5).
- Evidence: contracts.json lists C-ML at layer 2 with `requires` [C-RHI, C-TASK]. skills.json lists ml-inference-runtime with consumes [C-RHI, C-RG, C-TASK] and profiles [aaa]. Production precedent: UE NNE exposes CPU, GPU and RDG backends separately, with the render-graph backend as its own interface. Windows ML (2025) targets NPUs. Apple Core ML and ANE are used for on-device games features.
- Proposed change: Split the contract.
  - `C-ML` stays at layer 2 and requires only `C-TASK` and `C-MEM`. It covers model format, CPU and NPU backends, and async invocation.
  - New `C-ML-GPU` at layer 3 requires `C-RG` and `C-ML`. It covers inference as a render-graph pass on the same async-compute and budget scheduling.
  - Add capabilities `ML.RT.npu` (NPU backends, M, owner ml-inference-runtime, contributor platform-architect) and `ML.RT.remote-boundary` (remote/cloud inference invocation boundary, M, owner platform-online-services, contributor ml-inference-runtime).
  - Change the ml-inference-runtime profiles to `["all"]`, with every backend individually optional. It stays absent unless a consumer is present, and the closure proof handles that.

### K-FUTURE-3 · major · wrong-boundary
- Target: ML.RT.inference, RND.SHADER.*, C-SHADER, RND.MAT.neural, RND.TEX.ntc
- Finding: Principle 8 assumes that inference is a separately dispatched workload with "one runtime, one budget". The dominant next-generation form is the opposite: neural evaluation fused into ordinary shaders. Examples are neural texture decompression at sample time, neural materials evaluated in the pixel or hit shader, and neural radiance caches queried from path-tracing shaders. These use cooperative-vector or tensor intrinsics inside HLSL/Slang code, which is shader-system territory: intrinsics, weight buffer layout, permutations, fallbacks. Yet ML.RT.inference claims "GPU cooperative-vector / tensor paths", and C-SHADER ("modules, permutations, binding layouts, interop") has no notion of it. Two agents would both believe they own in-shader neural evaluation. The one that owns the shader compiler (shader-system) is not named.
- Evidence: D3D12 Cooperative Vectors (Shader Model 6.9 preview, 2025); VK_NV_cooperative_vector and the cross-vendor Vulkan cooperative-matrix work; the NVIDIA RTX Neural Shaders SDK and NTC SDK ("inference on sample"); Slang's autodiff and neural modules. Also "Real-Time Neural Appearance Models" (Zeltner et al., SIGGRAPH 2024) and "Random-Access Neural Compression of Material Textures" (Vaidyanathan et al., SIGGRAPH 2023). All of these run inside material and texture shaders, not as separate dispatches.
- Proposed change:
  - Add `RND.SHADER.neural`: "In-shader neural evaluation: cooperative-vector/tensor intrinsics, weight layout and quantization in shader-visible buffers, non-matrix-hardware fallbacks". It is M, owned by shader-system, with contributor ml-inference-runtime.
  - Add `RND.SHADER.autodiff`: "Differentiable shader compilation for training and optimization (Slang-class autodiff)". It is M, owned by shader-system.
  - Restrict ML.RT.inference to standalone network dispatch.
  - Extend the C-SHADER summary with "neural/tensor intrinsics tier". C-ML keeps model packaging, so neural shaders consume weights through C-ML.
  - Amend principle 8 to say that the runtime owns scheduling and budget for standalone networks, and that the shader system owns fused networks, whose cost falls in the host pass budget.

### K-FUTURE-4 · major · omission
- Target: CNT.COOK.architecture, CNT.COOK.determinism-check, CNT.COOK.distributed, ML.RT.training-boundary
- Finding: Several near-term features require GPU training or optimization at cook time, not only inference at runtime. Per-material NTC encoding is an optimization loop per texture set. Neural materials are trained per material. ML deformers are trained from offline cloth or muscle simulations. Learned motion matching compresses the database into networks. The cook architecture is "deterministic, incremental", includes a cook determinism check, and distributes to "remote cooking" with no GPU worker class. GPU training is not bit-deterministic across drivers or GPUs. As written, the determinism check (owned by content-pipeline-architect, with contributor test-architect) will reject these cook steps, or the agents will bypass it silently. ML.RT.training-boundary is only a "boundary" with no owner of the training-in-cook step.
- Evidence: NTC is compressed by per-texture-set network optimization (NVIDIA RTX NTC SDK). The UE ML Deformer is trained from Houdini/Chaos simulation datasets. Learned Motion Matching (Holden et al., SIGGRAPH 2020) trains decompressor, stepper and projector networks per database.
- Proposed change: Add `CNT.COOK.gpu-steps`: "GPU and training cook steps: GPU worker pools, pinned-output (content-addressed) determinism for non-bit-reproducible steps, dataset lineage". It is M, owned by content-pipeline-architect, with contributors ml-inference-runtime and ci-cd-automation. Amend CNT.COOK.contract so that a processor declares its determinism class: bit-exact, tolerance, or pinned-artifact.

### K-FUTURE-5 · major · omission
- Target: GAM.AI.llm, PLAT.SVC.moderation, C-SVC, C-TRUST, QA.CERT.ratings, AUD.CONTENT.dialogue, XC.DET.replay
- Finding: The framework represents LLM-driven NPCs and runtime generative content as a single X capability, "LLM-driven NPC dialogue & behavior". Every constraint that makes such content shippable is missing:
  - The cloud vs on-device inference choice, with its cost-per-player and latency budget (no capability; C-SVC does not mention inference).
  - Moderation of *model output*. PLAT.SVC.moderation covers only "UGC & text chat".
  - Prompt injection as a trust boundary. Player text and voice become model input, and C-TRUST lists no such input.
  - Runtime speech. Conversational NPCs need neural TTS and ASR. AUD.CONTENT.dialogue covers recorded VO, and UI.A11Y.screen-reader covers TTS for accessibility only.
  - Age-rating and store disclosure of live-generated content.
  - Deterministic authored fallback when the model is unavailable.
  - Recording nondeterministic model outputs as inputs for replay, desync debugging and bug reproduction.
- Evidence: Titles are already shipping with it: inZOI "Smart Zoi" (2025, on-device NVIDIA ACE), PUBG Ally (2025), and Where Winds Meet (2025, LLM-driven NPC conversation at MMO scale). Steam's content survey has required disclosure and guardrails for "Live-Generated AI content" since January 2024. OWASP LLM Top 10 lists prompt injection as LLM01. The label X is therefore also dishonest (see K-FUTURE-14).
- Proposed change: Add the following capabilities.
  - `PLAT.SVC.genai-boundary`: remote generative-AI service boundary (auth, quotas, cost metering, latency SLOs, regional routing). M, owned by platform-online-services.
  - `XC.SEC.genai`: generative-input/output trust rules (prompt injection, output filtering, PII). M, owned by security-engineering.
  - `PLAT.SVC.genai-moderation`: runtime moderation of generated text/voice/images. M, owned by platform-online-services, with contributor certification-compliance.
  - `QA.CERT.genai`: store and rating disclosure for live-generated content. E, owned by certification-compliance.
  - `AUD.CONTENT.speech`: runtime neural TTS/ASR for gameplay dialogue. M, owned by audio-content-runtime, with contributor ml-inference-runtime.
  - `XC.DET.external-inputs`: record external and nondeterministic results (model outputs, service replies) into the replay stream. E, owned by determinism-replay.

  Also change GAM.AI.llm to M, and add `C-ML?` and `C-SVC?` to ai-behavior-perception.

### K-FUTURE-6 · major · obsolete-assumption
- Target: ray-tracing-infrastructure (profiles [aaa]), path-tracing (profiles [aaa]), RND.RT.software, RND.PT.reference, QA.RENDER.reference, render-validation
- Finding: Hardware RT is gated behind the `aaa` add-on, so the `standard-3d`, `open-world`, `online-3d`, `xr-3d` and `mobile-3d` configurations cannot contain C-RT at all.
  - Every console in `platform-console` (std3d) has hardware RT. So do all current desktop GPUs and flagship mobile GPUs (Apple A17 Pro/M3+, Adreno 7xx/8xx, Mali Immortalis).
  - Shipped non-"AAA open-world online" games now *require* RT: Avatar: Frontiers of Pandora (Snowdrop, 2023), Indiana Jones and the Great Circle (id Tech, 2024), DOOM: The Dark Ages (2025).
  - The software-RT fallback (RND.RT.software) sits in the same aaa-only skill, so SDF/software tracing is also unavailable to std3d, even though Lumen-class software tracing is the scalable baseline.
  - The reference path tracer (RND.PT.reference, E) is the ground-truth oracle that render-validation (profile client) is meant to compare against (QA.RENDER.reference). In every non-aaa configuration the oracle is absent. That is a tooling hole, not a runtime choice.
- Evidence: The profile tags in skills.json. Configurations std3d, openworld and online contain no RT provider.
- Proposed change: Change the ray-tracing-infrastructure profiles to `["mobile3d","std3d"]` (consumers keep `C-RT?`). Split path-tracing so that RND.PT.reference is available to every client configuration as a dev-only, non-shipping module: set the profiles to `["client"]` with `runtime` false for the reference mode, and keep RND.PT.realtime gated by aaa. Allow a configuration to declare "RT required" as a hardware-tier floor in ARCH.REQ.hardware-tiers.

### K-FUTURE-7 · major · obsolete-assumption
- Target: C-RHI, RND.RHI.bindless, RND.RHI.pso, RND.SHADER.pso-lists, RND.RHI.backends (WebGPU), PLAT.PAL.web
- Finding: The C-RHI summary fixes today's API model in the contract text: "command lists, sync, bindless, PSOs, presentation".
  - There is no binding-model tier. Bindless is "the default" (principle 6) with no fallback capability. WebGPU, which is a listed backend, and older mobile Vulkan have no bindless. The web target (PLAT.PAL.web) and low-tier mobile therefore have no owned binding path.
  - The pipeline-state model is fixed to monolithic PSOs, with PSO lists gathered from play traces. The trend moves away from that: Vulkan graphics pipeline libraries and VK_EXT_shader_object, dynamic state, and D3D12 state objects and generic programs (work graphs).
  - The descriptor model is also moving (VK_EXT_descriptor_buffer, the new Vulkan descriptor-heap work). A contract that names the mechanism instead of the capability tier has to change for every one of these, which forces a C-ORCH change request across all render skills.
- Evidence: WebGPU v1 has no bindless (a bindless proposal is still in the gpuweb repo). VK_EXT_shader_object shipped in 2023 and exists specifically to escape PSO combinatorics. D3D12 Work Graphs 1.0 uses state objects and generic programs.
- Proposed change:
  - Rewrite the C-RHI summary in capability terms: "binding-model tier (bindless / descriptor-buffer / bind-group), pipeline-state model tier (monolithic PSO / pipeline libraries / shader objects / state-object programs), queue topology from caps".
  - Add `RND.RHI.binding-tiers` (E, owner rhi-core, contributor shader-system).
  - Rename RND.RHI.pso to "Pipeline-state models & caches (PSO, libraries, shader objects)".
  - Require render features to declare the minimum binding and pipeline tier in the C-RSCENE feature contract.

### K-FUTURE-8 · major · wrong-boundary
- Target: RND.GRAPH.work-graphs (render-graph-scheduling), RND.GEO.indirect (gpu-driven-pipeline), rhi-core, C-RG, C-RHI
- Finding: GPU-generated work has three owners, and the hardware surface has none.
  - gpu-driven-pipeline owns "ExecuteIndirect / device-generated commands", which is an RHI-level API abstraction held by a feature skill.
  - render-graph-scheduling owns "work graphs execution model integration".
  - Work graphs with mesh nodes are the successor to indirect and DGC draw generation. The gpu-driven agent and the render-graph agent will both build the same geometry path.
  - rhi-core owns no capability for GPU-generated work at all.
  - C-RG ("pass/resource declaration") assumes that work and resource usage are known when the graph compiles. Work graphs allocate backing memory and produce work dynamically on the GPU, so the contract gives no place to declare that.
- Evidence: D3D12 Work Graphs 1.0 (2024), with mesh nodes in preview in 2024–25. VK_EXT_device_generated_commands (2024). AMD GPUOpen samples use work-graph mesh nodes as a replacement for indirect draw pipelines for procedural geometry.
- Proposed change:
  - Add `RND.RHI.gpu-work` ("GPU-generated work primitives: indirect, DGC, work-graph programs, backing memory") as E/M, owned by rhi-core.
  - Move the "device-generated commands" wording out of RND.GEO.indirect.
  - Add `RND.GEO.mesh-nodes` ("work-graph mesh-node geometry pipeline"), M, owned by gpu-driven-pipeline.
  - Narrow RND.GRAPH.work-graphs to "scheduling, barriers and memory for GPU-generated work inside the graph".
  - Extend the C-RG summary with "dynamic GPU-generated work nodes".

### K-FUTURE-9 · major · omission
- Target: RND.* (no owner), CNT.IMP.scans, C-RSCENE
- Finding: Gaussian splatting and other captured or learned scene representations (3DGS, 2DGS, triangle splatting, NeRF-derived assets) appear nowhere. CNT.IMP.scans ingests photogrammetry only as input to meshes. No skill owns non-mesh primitive rendering: sorted or stochastic splat rasterization, ray-traced splats, LOD, streaming, relighting or compositing with raster/RT content. Without an owner, the first agent asked for it will add it wherever it fits worst, for example as a VFX particle type or a translucency hack.
- Evidence: 3D Gaussian Splatting (Kerbl et al., SIGGRAPH 2023) and "3D Gaussian Ray Tracing" (Moenne-Loccoz et al., SIGGRAPH Asia 2024). Khronos is working on a glTF Gaussian-splat extension (KHR_gaussian_splatting, 2025). Splat capture ships in consumer products (Meta Horizon Hyperscape, 2025). UE/Unity/PlayCanvas splat renderers exist.
- Proposed change: Add area `RND.CAPTURE` with these capabilities:
  - `RND.CAPTURE.splats`: splat/radiance-field rendering, sorting, LOD and streaming. M, owned by virtualized-geometry-lod or a new expert `captured-scene-rendering` under render-architect. The new expert is preferred if relighting and RT are included.
  - `RND.CAPTURE.relight`: relightable/dynamic splats and hybrid composition with raster/RT. X.
  - `CNT.IMP.splats`: splat/radiance-field import (PLY/SPZ/glTF extension). M, owned by asset-import-interchange.

  Add a "non-mesh primitive" kind to C-RSCENE.

### K-FUTURE-10 · major · omission
- Target: PLAT.XR.*, xr-runtime, profile `xr` ("VR / MR")
- Finding: The xr profile claims MR, but no capability covers mixed reality or spatial computing: passthrough compositing, scene understanding (planes, meshes, semantic labels), spatial anchors and their persistence and sharing, environment-depth occlusion, real-world lighting estimation, and XR compositor layers (quad/cylinder layers for legible text). Eye tracking appears only as a foveation input and not as an interaction input (gaze plus pinch). Shared or colocated MR also needs an anchor-sharing boundary with networking.
- Evidence: OpenXR 1.1 and the XR_FB/META scene, anchor and passthrough extensions; XR_ANDROID_* for Android XR (2024–25). Meta Quest 3 Depth API occlusion. visionOS gaze-and-pinch as the primary input model. Composition layers are an OpenXR core feature and are required for readable UI in current headsets.
- Proposed change: Under PLAT.XR, add:
  - `PLAT.XR.passthrough` (E)
  - `PLAT.XR.scene-understanding` (M)
  - `PLAT.XR.anchors` (M, contributors network-architect and persistence-save)
  - `PLAT.XR.depth-occlusion` (M, contributor render-architect)
  - `PLAT.XR.layers` (E)
  - `PLAT.XR.gaze-input` (M, contributor input-system)

  All are owned by xr-runtime. Split xr-runtime into `xr-runtime` (session, frame, reprojection, layers) and `mixed-reality` (scene, anchors, passthrough) if the count exceeds the expert-size norm.

### K-FUTURE-11 · major · omission
- Target: RES.IO.backends, C-IO, C-VFS, PLAT.PAL.cloud-streaming, BLD.REL.on-demand
- Finding: The framework has no network-sourced world data and no cloud-hybrid compute.
  - All IO backends are local: io_uring, IOCP, DirectStorage, console. BLD.REL.on-demand covers installing, not runtime streaming of world content from a CDN or service, with caching, prefetch and offline behavior.
  - PLAT.PAL.cloud-streaming covers only whole-game video streaming.
  - Offloading simulation or precomputation to the cloud (hybrid rendering, cloud-baked lighting, server-side world generation) has no owner and no explicit non-goal.
- Evidence: Microsoft Flight Simulator 2020/2024 streams petabyte-scale terrain, photogrammetry and the 2024 content from the cloud at runtime, with a local rolling cache. Roblox streams all experience content on demand. Cloud physics and destruction were attempted in Crackdown 3 (2019), which is evidence that this is X, not a legitimate omission.
- Proposed change:
  - Add `RES.IO.remote`: HTTP/CDN IO backend with persistent content cache, prefetch, bandwidth and offline policy. M, owned by async-io-storage, with contributor platform-online-services.
  - Add a "remote mount" layer kind in RES.PKG.vfs and C-VFS.
  - Add `PLAT.PAL.cloud-hybrid`: split client/cloud compute boundary. X, owned by platform-architect. Alternatively, list it explicitly in ARCH.REQ.non-goals.

### K-FUTURE-12 · major · omission
- Target: program-orchestration, ED.ARCH.*, BLD.CI.cli, QA.FUNC.automation, XC.DX.*
- Finding: The framework's own implementers are AI agents, but no capability makes the engine and editor *operable by agents*. Missing are:
  - A stable machine-facing control and introspection protocol (drive editor and runtime, query world and ECS state, capture frames and traces, run commandlets, with structured results), in the MCP-tool class.
  - Machine-readable diagnostics and error schemas. XC.DX.errors is about human message quality.
  - Deterministic "reproduce this bug" bundles an agent can consume.
  - Agent-driven exploratory testing. QA.FUNC.automation covers scripted playthroughs and bots, not RL or LLM exploration agents.

  Without an owner, every implementation agent will build its own scraping harness against logs and screenshots.
- Evidence: MCP-server integrations for Unity, Unreal, Godot and Blender became common in 2025, and Unity's AI assistant drives the editor through tool APIs. EA SEED and Ubisoft La Forge have published RL/agent-based game testing (e.g., "Augmenting automated game testing with deep reinforcement learning", EA SEED, IEEE CoG 2020).
- Proposed change:
  - Add `ED.ARCH.agent-api`: agent/automation control and introspection protocol for editor and runtime. E/M, owned by editor-architect, with contributors visual-debugging-tools and observability-telemetry.
  - Add `XC.DX.machine-diagnostics`: structured, schema'd diagnostics and repro bundles. E, owned by developer-experience-docs, with contributor crash-diagnostics.
  - Add `QA.FUNC.agent-exploration`: RL/LLM exploratory test agents. M, owned by functional-automation-soak.
  - Add an obligation to crosscutting.json: "every skill exposes its debug state through the agent API".

### K-FUTURE-13 · major · other
- Target: ARCH.GOV.radar, ARCH.REQ.non-goals, maturity data, check.py
- Finding: The radar and promotion process has no data territory.
  - Of 739 capabilities, 0 are marked S and only 5 are marked X, so "speculative" is an empty class.
  - The non-goal register (ARCH.REQ.non-goals) is a capability with no entries anywhere in data/.
  - No record links a technology to "owned by capability X" or "explicit non-goal".
  - Nothing states a promotion trigger for any X or M item.

  So the mandated test ("each future technology has either an owner and extension point, or an explicit non-goal") cannot be evaluated or enforced. Technologies such as BCI, CXL memory tiers, light-field displays, RISC-V, cloud physics, eye-tracked desktop input and on-device LLMs silently fall through.
- Evidence: A maturity-class count of capabilities.json gives E=696, M=38, X=5, S=0. `grep non-goal data/` returns only the capability definition.
- Proposed change: Add `data/radar.json` with entries of the form {tech, class E/M/X/S, capability ids or "non-goal", owner, evidence refs, promotion/revisit trigger, fallback}. Extend check.py:
  - Every X/S capability and every M capability must have a radar entry.
  - Every radar entry must resolve to a capability or be listed as a non-goal.
  - An M capability consumed non-optionally must name its fallback.

  Seed it with the technologies in this critic's mandate.

### K-FUTURE-14 · major · obsolete-assumption
- Target: CORE.LIFE.language, ARCH.GOV.coding-standard, XC.SEC.coding, CORE.LIFE.asserts, BLD.SYS.toolchains, CORE.REFL.generation
- Finding: The language capability is pinned in its name ("C++20/23, exceptions/RTTI policy"). No capability owns multi-language interop or adoption of memory-safe languages, which covers:
  - Rust or other safe components, the FFI/ABI boundary, and cargo-class build integration.
  - Safe-subset and hardening profiles: hardened libc++, C++26 erroneous behavior, and C++26 contracts as the substrate for CORE.LIFE.asserts.

  The engine's highest-risk code is its parsers of untrusted packets, mods, fonts, saves and UGC (listed in QA.ROBUST.fuzzing). Moving those parsers to memory-safe code is the strongest currently demonstrated mitigation, but there is no territory in which an agent could adopt it without an unowned cross-skill change.
- Evidence: Android reports memory-safety vulnerabilities falling from 76% to 24% (2019 to 2024) as new code moved to Rust. Chrome replaced its FreeType font path with Rust Skrifa (2025). C++26 adopted static reflection (P2996), contracts (P2900) and erroneous behavior (P2795). CISA/NSA memory-safety roadmap guidance (2023–25).
- Proposed change:
  - Rename CORE.LIFE.language to "Language standards & compiler feature policy (C++ baseline, C++26 adoption plan)".
  - Add `CORE.LIFE.interop`: multi-language interop & safe-language components (FFI/ABI rules, ownership across boundaries). M, owned by core-runtime-architect, with contributors security-engineering and build-system-toolchains.
  - Add `XC.SEC.safe-parsers`: policy that untrusted-input parsers use memory-safe language or hardened subset. E, owned by security-engineering.
  - Add C++26 contracts to CORE.LIFE.asserts as an adoption path, M.

### K-FUTURE-15 · minor · maturity-error
- Target: GAM.AI.llm (X), GAM.AI.learned (X), RES.IO.gpu-decompress (M), PLAT.XR.foveation (M), RND.RECON.framegen (M), RND.TEX.ntc (M)
- Finding: Several labels do not match production evidence as of 2026.
  - Under-labelled:
    - GAM.AI.llm has shipped titles (K-FUTURE-5).
    - GAM.AI.learned has shipped: GT Sophy in Gran Turismo 7 (2023, expanded 2025).
    - GPU/hardware decompression is established on PS5 and Xbox Series hardware and in DirectStorage 1.1+ titles such as Ratchet & Clank: Rift Apart PC (2023). RES.PKG.compression already lists GDeflate as E, so the map is internally inconsistent.
    - Fixed foveation has been E on Quest since 2019. Only eye-tracked foveation is M.
    - Frame generation (DLSS 3/4, FSR 3, XeSS-FG) ships in hundreds of titles and is E on PC, though M for input-latency-sensitive genres.
  - Over-labelled: NTC (M) has an SDK and demos. Its inference-on-sample path depends on cooperative vectors that were still in preview, and there is no graded shipped-title evidence in the artifact. Principle 7 requires production evidence for M, so NTC should be X, or M with "transcode-to-BCn-on-load" named as the production mode.
- Evidence: As cited above. The two GDeflate entries in capabilities.json.
- Proposed change: GAM.AI.llm → M. GAM.AI.learned → M. RES.IO.gpu-decompress → E. Split PLAT.XR.foveation into fixed (E) and eye-tracked (M). RND.RECON.framegen → E. RND.TEX.ntc → X, or split into ntc-transcode (M) and ntc-inference-on-sample (X). Record each change in radar.json (K-FUTURE-13).

### K-FUTURE-16 · minor · omission
- Target: RND.GI.*, RND.PT.realtime, global-illumination
- Finding: Neural radiance caching is absent. It is the neural-rendering technique with the clearest production path for path-traced and ReSTIR pipelines, but RND.GI lists caches only as "surface / radiance-cache hybrid". It also needs a place that consumes the fused-shader path from K-FUTURE-3, and online training during the frame, which is a budget item that ML.RT.scheduling does not describe.
- Evidence: "Real-time Neural Radiance Caching for Path Tracing" (Müller et al., SIGGRAPH 2021). It shipped in RTX Remix titles (Portal with RTX; Half-Life 2 RTX, 2025).
- Proposed change: Add `RND.GI.neural-cache` ("neural radiance caching with online training"), M, owned by global-illumination, with contributors ml-inference-runtime and path-tracing. Extend ML.RT.scheduling to cover "online in-frame training".

### K-FUTURE-17 · minor · obsolete-assumption
- Target: CORE.MATH.linear, CORE.MATH.spmd, C-MATH, PLAT.PAL.cpu-topology, PLAT.DESK.os-integration
- Finding: The SIMD capabilities say "wide-SIMD" with runtime ISA dispatch but do not name vector-length-agnostic ISAs. ARM SVE/SVE2/SME (on server Graviton/Grace, Apple M4 SME) and RISC-V RVV are length-agnostic, so a C-MATH design built on compile-time-width vector types cannot target them. Windows on ARM specifics are also unowned: ARM64EC and x64 emulation interop for third-party middleware, and anti-cheat availability. RISC-V has neither an owner nor a non-goal entry.
- Evidence: Windows on Snapdragon X (2024). The Arm SVE/SME and RVV 1.0 specifications. Highway (Google) exists specifically to span fixed and scalable vectors.
- Proposed change: Extend CORE.MATH.spmd to "fixed and scalable (VLA) vector ISAs". Add `PLAT.DESK.arm64`: Windows-on-ARM/ARM64EC and emulation interop, owned by platform-desktop. Add RISC-V to radar.json as X or as a non-goal.

### K-FUTURE-18 · minor · scale-down
- Target: ai-assisted-authoring (profiles [aaa]), ED.AI.*
- Finding: AI-assisted authoring (generative asset tools, editor copilots, ML retopology/UV/LOD) is gated to the aaa add-on, so indie-2d, mobile-3d and standard-3d configurations cannot include it. Small teams are the heaviest adopters of these tools because they lack artist headcount. The tool is also non-runtime, so it costs the shipped game nothing.
- Evidence: The profile tag in skills.json. Unity AI (2025) and Roblox Cube/Assistant (2024–25) both target small creators.
- Proposed change: Change the ai-assisted-authoring profiles to `["all"]` (non-runtime) and keep `C-ML?` optional.

### K-FUTURE-19 · minor · omission
- Target: INP.DEV.*, RND.ARCH.multiview, PLAT.DESK.display
- Finding: Two display and input technologies have neither an owner nor a non-goal entry. First, eye tracking as an input device outside XR (Tobii-class desktop and laptop trackers, which is also an accessibility input). Second, multiview displays beyond stereo HMDs: autostereoscopic and light-field monitors that need N-view rendering with head tracking. BCI input (speculative) is likewise not recorded. RND.ARCH.multiview covers split-screen/PiP, and PLAT.XR.stereo is HMD-only.
- Evidence: Samsung Odyssey 3D and Acer SpatialLabs autostereo displays (2024–25) with game-integration SDKs. The Tobii Game Integration SDK. OpenBCI/Valve Galea exists only as research (S).
- Proposed change: Add `INP.DEV.eye-tracking` (E, owner input-devices-haptics, contributor accessibility). Extend RND.ARCH.multiview to "N-view outputs (stereo, autostereo/light-field)", M. Record BCI in radar.json as S or as a non-goal.
