# K-FUTURE · Future-Technology Critic · round 2

Scope: whether any technology likely to matter within about 5 years is prevented, and whether maturity labels are honest. `check.py` is green (0 errors, 0 warnings). Every finding below is something the gate cannot see.

### K-FUTURE-1 · major · maturity-error
- Target: RND.GRAPH.work-graphs, RND.RHI.gpu-work, radar "Work graphs & mesh nodes", seed-map brief_hardware "work graphs or equivalent execution models"
- Finding: `RND.GRAPH.work-graphs` is labelled **E** in capabilities.json. The radar entry that lists it is class **X**, with the evidence "no shipped titles". `docs/06` A6 says "almost no shipped-title postmortems … adopt behind a capability tier with an indirect fallback". `RND.RHI.gpu-work` (E) bundles three things with different maturity: established indirect/ExecuteIndirect, emerging device-generated commands, and experimental work-graph programs. Because the owning capability says E, a phase-2 render-graph-scheduling agent would treat work graphs as a production baseline. It could then freeze C-RG/C-RHI around them, even though principle §7 promises that work graphs remain "an optional part of C-RG".
- Evidence: D3D12 Work Graphs 1.0 shipped in 2024 and mesh nodes are still preview. There is no Vulkan KHR equivalent (only vendor AMDX), and no Metal equivalent. No shipped title has published a work-graph postmortem. The radar's own revisit trigger ("≥2 APIs + one shipped-title postmortem") has not fired.
- Proposed change: Relabel `RND.GRAPH.work-graphs` to X. Split `RND.RHI.gpu-work` into `RND.RHI.indirect` (E: indirect draw/dispatch, multi-draw-indirect-count), `RND.RHI.dgc` (M: VK_EXT_device_generated_commands / D3D12 ExecuteIndirect state changes) and `RND.RHI.work-graphs` (X), and put the last two on the radar. Add a check.py rule: every capability listed in a radar entry must carry that entry's class (see K-FUTURE-11).

### K-FUTURE-2 · major · maturity-error
- Target: QA.AGENT.oracle-independence, QA.AGENT.baseline-governance, QA.AGENT.test-integrity, QA.AGENT.mutation-gate, ARCH.ORG.provenance, ARCH.ORG.critic-calibration, ARCH.ORG.adjudication, XC.SEC.agent-boundary
- Finding: The capabilities that decide whether autonomous agents' output can be trusted are all labelled **E**, so none of them is on the radar and none has a fallback. The framework's own gap analysis contradicts this. `docs/06` A13 says validation of agent-produced engine code is a "new discipline; little evidence on failure modes of agent-written systems code at this scale". The whole coordination model depends on these mechanisms: independent oracles, seeded-defect calibration, adjudication, detecting weakened tests, and a prompt-injection threat model for development agents. If they are labelled "established", nobody owns watching them fail and there is no defined degraded mode.
- Evidence: Mutation testing, SLSA provenance and code review are established. Using them to police LLM coding agents is not. Public evidence of agents gaming tests and tampering with rewards (reward hacking in agentic coding benchmarks; METR and SWE-bench analyses in 2025) shows these failure modes are real and still being characterised. Prompt injection against coding agents through repository content has no settled mitigation (OWASP LLM01 is still ranked first in 2025).
- Proposed change: Relabel these eight capabilities to M. Add a radar entry "Validation & governance of autonomous-agent development" (owner test-architect; contributors program-orchestration, security-engineering). Give it these contents:
  - Evidence: A13.
  - Revisit trigger: measured escape rate of seeded defects below threshold across N milestones.
  - Fallback: mandatory human review sampling rate per tier in `ARCH.ORG.human-gates`, plus a freeze on agent authority over oracles and baselines.

### K-FUTURE-3 · major · maturity-error
- Target: GAM.AI.llm, GAM.AI.learned, radar "Learned & LLM-driven agents", docs/06 A12
- Finding: The data labels LLM-driven NPCs **M**. `docs/06` A12 labels the same thing "`experimental` … evidence is mostly demos … never on a required path" and names `platform-services` as the moderation owner, but moderation is owned by `online-services-liveops` (PLAT.SVC.moderation). One capability also mixes two technologies with very different maturity. Cloud-hosted LLM dialogue on non-authoritative state has shipped. On-device language models that drive gameplay-affecting decisions in authoritative, replayable simulation have not. `GAM.AI.learned` (RL policies) is a third maturity profile placed in the same radar entry.
- Evidence: Cloud or hybrid LLM companions and dialogue shipped in 2025 (inZOI Smart Zoi, PUBG Ally, Where Winds Meet, and NVIDIA ACE titles such as Mecha BREAK). None has published how they handled determinism, rollback, rating or cost. GT Sophy is a research deployment that was never shipped as a shipped-game NPC system.
- Proposed change: Split into `GAM.AI.llm-dialogue` (M: generated barks and dialogue on cosmetic or non-authoritative state) and `GAM.AI.llm-decision` (X: model output that changes authoritative simulation state). Keep `GAM.AI.learned` as M only if an RL-policy shipping precedent is cited; otherwise make it X. Correct A12 to match the data, and point it to online-services-liveops for moderation.

### K-FUTURE-4 · major · maturity-error
- Target: RND.SHADER.neural, RND.GI.neural-cache, C-SHADER, radar "In-shader neural evaluation & differentiable shaders", radar "Neural radiance caching"
- Finding: `RND.SHADER.neural` is labelled M, but its own radar evidence is "SM 6.9 cooperative vectors (**preview**)" and its revisit trigger is "non-preview cross-vendor support". That trigger has not fired, so the honest class is X. `RND.GI.neural-cache` is M and tagged into the `aaa` profile, while `docs/06` A7 says neural radiance caching has "limited production evidence and depends on tensor/cooperative-vector support". Its radar fallback and trigger ("cross-vendor tensor support") confirm it is single-vendor today. The capability name also hard-codes one preview API shape ("cooperative-vector"). That API surface is still moving: vendor extensions (VK_NV_cooperative_vector), a DXIL preview, and Metal 4 tensor ops each have different semantics.
- Evidence: Shipped neural-shading and NRC uses are NVIDIA-only and mostly RTX Remix mods and tech demos. There is no cross-vendor, non-preview in-shader matrix-vector API on D3D12, Vulkan KHR or consoles as of 2026.
- Proposed change: Relabel `RND.SHADER.neural` to X and `RND.GI.neural-cache` to X, or keep neural-cache at M only if the radar cites a shipped non-mod title. Rename the capability to "In-shader small-network evaluation (matrix-vector/tensor intrinsics tier; API-neutral)". Make the C-SHADER "neural/tensor intrinsics tier" explicitly an optional tier with a mandatory standalone-dispatch fallback through C-MLGPU.

### K-FUTURE-5 · major · scale-down
- Target: RND.GEO.mesh-nodes (X, [aaa]), RND.TEX.ntc (X, [aaa]); configurations aaa-open-world-online-{client,server,tools}
- Finding: Two experimental capabilities carry the `aaa` capability-profile tag. Under `Model.cap_in_configuration` this makes them members of the closure of every aaa configuration. The flagship configuration therefore proves itself closed only if work-graph mesh nodes (preview API) and neural texture compression (SDK beta) are present. This breaks principle §7 ("never a required dependency") and the brief ("experimental items must not be required dependencies"). The schema cannot express "optional in this configuration", so the gate treats X features as part of the shipping bill of materials.
- Evidence: model.py `cap_in_configuration` returns true for any capability whose profile tag intersects the configuration's profiles. Maturity is never consulted.
- Proposed change: Add an add-on profile token `experimental` (or a configuration flag `allow_maturity: [E,M]`). Move X and S capabilities from `aaa` to `experimental`. Add a check.py rule that no named configuration without `experimental` contains an X or S capability. Add one `aaa-experimental-client` configuration to prove the opt-in path closes.

### K-FUTURE-6 · major · omission
- Target: ML.RT.* (ml-inference-runtime), C-ML, C-MLGPU, RES.MGMT (cross-pool arbitration)
- Finding: The ML runtime is shaped around small, fixed-cost, per-frame networks (upscalers, deformers, radiance caches). It has no capability for **autoregressive and generative models running on-device**, such as small language models, speech models and diffusion. These models have properties the current contracts do not cover:
  - multi-GB weights that must be arbitrated against texture, geometry and BVH pools on UMA/VRAM
  - a KV cache that grows per conversation
  - token-streaming output with cancellation and pre-emption across many frames
  - tokenizers and structured or constrained decoding (grammar-constrained output mapped to game actions)
  - model-variant selection per device tier (quantization level, NPU vs GPU vs CPU)
  - switching between local and cloud execution for the same feature

  None of these is owned. They will fall between ml-inference-runtime, resource-streaming-architect and online-services-liveops, each of which will assume another owns them.
- Evidence: On-device language and speech models shipped or were demonstrated in games in 2025 (inZOI on-device model via ACE, Mecha BREAK). Windows ML GA (2025), Apple Foundation Models framework (2025) and Android AICore expose OS-level on-device LLMs, which are a distinct integration surface from ONNX-style inference. Memory co-residency with rendering is the dominant practical constraint.
- Proposed change: Add these capabilities, all owned by ml-inference-runtime:
  - `ML.RT.sequence-models` (X): autoregressive/diffusion execution, KV-cache budgets, streaming, cancellation, constrained decoding.
  - `ML.RT.os-models` (M): OS-provided foundation-model APIs as a backend.
  - `ML.RT.residency` (M): weight residency registered as a pool in C-RES arbitration, with contributor resource-streaming-architect.
  - `ML.RT.local-remote` (M): the same model interface served locally or through the C-LIVE generative boundary, with a routing policy and fallback; contributor online-services-liveops.

  Extend C-ML with "sequence sessions, streaming results, residency class, local/remote routing".

### K-FUTURE-7 · major · scale-down
- Target: ml-inference-runtime (profiles ["lite3d","std3d"], parent gpu-platform-architect, workstream rendering, milestone M5)
- Finding: The ML runtime cannot exist in `minimal` or `min2d` configurations. Yet its consumers are in profile `all`: ai-behavior-perception (LLM NPCs), audio-content-runtime (runtime TTS/ASR), and accessibility (TTS/STT). Narrative, card and 2D games are exactly the genres most likely to adopt LLM dialogue and neural TTS. In those configurations the framework allows only remote inference through C-LIVE, which rules out offline or on-device play. The skill is parented under the GPU platform lead and the rendering workstream, but it owns CPU and NPU backends and its main non-rendering consumers are audio, AI and gameplay. Arbitration of its budget would therefore sit with a lead whose remit is GPUs.
- Evidence: skills.json shows ml-inference-runtime profiles as ["lite3d","std3d"]. ai-behavior-perception and audio-content-runtime are ["all"] and consume `C-ML?`. The C-ML contract itself is layer 2 and requires only C-TASK and C-MEM, with no GPU dependency.
- Proposed change: Set the ml-inference-runtime profiles to ["all"]. Keep C-MLGPU gated by a GPU tier, not by the base profile. Reparent the skill under core-runtime-architect or engine-architect (workstream foundation), and keep gpu-platform-architect as the arbiter only for C-MLGPU. Add a configuration such as `narrative-llm-client` (minimal + on-device ML, platforms pc and mobile) to prove the path closes.

### K-FUTURE-8 · major · missing-contract
- Target: C-DIALOGUE, C-AIAGENT, C-REPLAY, C-REP, narrative-dialogue, PLAT.SVC.moderation
- Finding: Generated content has no defined path through the runtime.
  - C-DIALOGUE models line records as authored assets: stable IDs, "text per locale", "VO per locale" and lip-sync data. A runtime-generated line has none of these. It has no stable ID, it is produced in one locale (or machine-translated), its audio comes from TTS, lip sync is derived at runtime, and it must pass moderation before it is displayed, voiced or captioned.
  - C-AIAGENT promises "moderation and authored fallback" but says nothing about how nondeterministic model output enters simulation. For replay, rollback, server authority and save/load it has to be recorded as an external input and replicated, not re-derived.
  - C-AIAGENT also assumes moderation is available, but the only moderation owner (PLAT.SVC.moderation) is a remote service boundary. An offline on-device model has no local moderation owner.
- Evidence: A generated line pipeline typically runs: text generation, then safety classification, then TTS, then audio-driven lip sync, then captions. That chain touches narrative-dialogue, audio-content-runtime, facial-animation, accessibility and online-services-liveops. Today none of their contracts accepts a non-asset line. Precedent: shipped LLM-NPC titles gate every output through a classifier before display.
- Proposed change:
  - Extend C-DIALOGUE with "runtime line records: provenance = generated, transient ID, locale, moderation verdict, TTS/lip-sync-at-runtime flags, caption obligations".
  - Extend C-AIAGENT with: "provider outputs enter simulation only as recorded external inputs (C-REPLAY external stream; replicated from authority); providers are never re-invoked on resimulate".
  - Add `GAM.AI.local-guardrails` (M, owner ai-behavior-perception, contributor security-engineering) for on-device safety classification when C-LIVE is absent.

### K-FUTURE-9 · major · wrong-owner
- Target: ED.ARCH.agent-api (owner editor-architect, kind tool, targets ["tools"]), C-IPC, visual-debugging-tools
- Finding: The agent/automation control and introspection protocol is described as covering both "editor and runtime", but its owner is tools-only and cannot ship code in client, headless-client or server builds. The runtime endpoint has no owner. That endpoint is what an AI developer or test agent would use to query entity state, drive a dev build on a console or phone, step frames or read traces. No contract exists for the protocol either, so it cannot be versioned or conformance-tested like other surfaces. Agents are the engine's primary developers under this framework, so the surface they operate through is critical infrastructure. Without a contract it will turn into per-skill ad-hoc hooks.
- Evidence: skills.json: editor-architect kind "tool", targets ["tools"]. visual-debugging-tools (runtime, all targets) is only a contributor. Agent tool protocols such as MCP are versioned and capability-negotiated. They need schema stability, auth and dev-only port security (already in C-IPC) and a runtime presence on non-PC dev targets.
- Proposed change: Create contract `C-AGENTCTL` (layer 2 runtime part plus layer 5 editor part, owner visual-debugging-tools or core-runtime-architect) covering introspection queries, command execution, frame stepping, capture triggers, capability negotiation, dev-only gating, and a versioned schema generated from C-REFL. Move ownership of the runtime half of ED.ARCH.agent-api to that owner and keep the editor half with editor-architect. Add a conformance suite under C-TEST.

### K-FUTURE-10 · major · dependency-error
- Target: milestones.json (C-RHI frozen at M2; ml-inference-runtime joins at M5), C-RHI, C-GPUTIER
- Finding: C-RHI freezes at M2, but the first consumer of tensor or ML GPU functionality (ml-inference-runtime, via C-MLGPU) only joins at M5. The C-RHI summary lists nothing ML-related: no tensor or matrix resource types, no optimal weight-layout conversion, no queue priority for long-running inference alongside frame work. C-GPUTIER does name a "tensor" tier. The contract therefore freezes around today's graphics-only API shape before its one forward-looking consumer exists, which guarantees a breaking change or an ad-hoc side channel later. The same applies to ML-assisted reconstruction and denoising, which reconstruction-upscaling (M1) wires to vendor SDKs because no engine inference path exists yet.
- Evidence: Cooperative-vector and tensor APIs need device-side weight-layout conversion and dedicated resource or buffer usage flags. Metal 4 introduced first-class `MTLTensor` resources. These are RHI-level concerns.
- Proposed change: Either move ml-inference-runtime (C-ML/C-MLGPU draft) to M2, or add to M2's exit criteria "C-RHI reviewed against the C-GPUTIER tensor tier by ml-inference-runtime before freeze". Add "tensor/matrix resource types and layout conversion (optional tier)" to the C-RHI summary.

### K-FUTURE-11 · minor · maturity-error
- Target: RND.ARCH.multiview (E) vs radar "Autostereo / light-field displays" (M); RND.PT.realtime (owner path-tracing) listed under radar owner global-illumination; NET.ARCH.meshing (X) vs docs/06 A5 ("Keep as `emerging`"); RND.RHI.webgpu (M) vs RND.RHI.webgpu-validation/quirks (E)
- Finding: The radar, the capability labels and the gap analysis disagree in several places. check.py only proves that non-E capabilities appear on the radar. It never proves that a radar entry's class and owner agree with the capabilities it lists, so these contradictions pass the gate. `RND.ARCH.multiview` bundles established split-screen and stereo with emerging N-view light-field output under E. For server meshing, Star Citizen has run it in its live environment since late 2024. That is production evidence (M under this framework's own definition) even though the postmortems are missing.
- Proposed change: Split `RND.ARCH.multiview` into an E part (split-screen, PiP, stereo/multiview) and `RND.ARCH.nview` (M). Set the radar owner of RND.PT.realtime to path-tracing, or give it its own entry. Choose one class for server meshing and align A5. Add check.py rules: radar class equals the maturity of every listed capability; radar owner equals the owner of each listed capability or is its lead.

### K-FUTURE-12 · minor · maturity-error
- Target: ML.RT.npu, radar "ML runtime (inference, packaging, scheduling, NPU)"
- Finding: One radar entry covers six ML capabilities with a single class (M) and one evidence line ("UE NNE; Windows ML; Core ML"). NPU backends in games have essentially no shipping evidence. The platform API surface is also churning: Android NNAPI was deprecated in Android 15 in favour of LiteRT/vendor delegates, Windows ML only reached GA in 2025, and UE NNE is still experimental or beta. Folding NPU into the M bundle hides that.
- Proposed change: Give ML.RT.npu its own radar entry at X, with the revisit trigger "one shipped title offloads a frame-relevant network to an NPU on two platforms" and the fallback "GPU/CPU backend". Replace NNE as the evidence for the bundle with a shipping reference.

### K-FUTURE-13 · minor · omission
- Target: radar non-goal "Explicit multi-GPU", PLAT.PAL.cpu-topology, RND.RHI.caps
- Finding: The non-goal is written as "explicit multi-GPU / vendor support withdrawn". That describes AFR/SLI-style rendering. It silently also excludes **heterogeneous adapter use**: running ML, video encode or async work on the integrated GPU or NPU while the discrete GPU renders, and adapter selection on hybrid laptops. The brief names "discrete + integrated GPUs" together, and hybrid-graphics laptops and handhelds are a large share of the PC base.
- Proposed change: Narrow the non-goal to "linked/AFR multi-GPU rendering". Add `RND.RHI.adapter-selection` (E: choosing the high-performance or low-power adapter, cross-adapter present on hybrid laptops) and put heterogeneous-adapter offload on the radar as X, owner gpu-platform-architect, fallback single adapter.

### K-FUTURE-14 · minor · omission
- Target: xr-runtime, C-XRVIEW, C-PRESENT
- Finding: The XR contracts assume the engine owns rendering and hands frames to an OpenXR-style compositor. OS-composited shared-space models, where the OS renders a replicated scene description and the app does not own the frame, cannot be expressed. Examples are visionOS Shared Space with RealityKit, and Android XR / Horizon OS panels and volumes. The framework neither owns this nor records it as a non-goal, so a phase-2 XR agent has no guidance.
- Evidence: Unity PolySpatial exists precisely because visionOS shared space does not accept engine-rendered frames. Full-space Metal (CompositorServices) is the only engine-owned path.
- Proposed change: Add a radar entry "OS-composited spatial scenes (shared space)" (M, owner xr-runtime). Either record it as an explicit non-goal with fallback "full/immersive space only", or add `PLAT.XR.scene-export` with render-architect as contributor, bridged through C-RSCENE change streams.

### K-FUTURE-15 · minor · obsolete-assumption
- Target: platform-web (profiles ["minimal","min2d","lite3d"]), rhi-webgpu, radar "WebGPU backend & web 3D"
- Finding: The web target is excluded from `std3d` by profile, which structurally hard-codes the 2025 WebGPU feature set. WebGPU already ships compute, indirect draws, subgroups (2025), timestamp queries and larger limits tiers. Bindless and WASM memory64 are in progress. A GPU-driven std3d-class tier on the web is plausible within the 5-year horizon. The radar's revisit trigger ("bindless/timestamp features") exists but has no structural consequence, because a trigger firing would still need profile surgery.
- Proposed change: Keep web out of any std3d configuration for now, but make the gate a C-GPUTIER tier rather than a profile exclusion. Allow platform-web in std3d and let features declare their minimum tier. Record "std3d on web" on the radar (X, trigger: WebGPU bindless plus memory64 shipped in two browsers).

### K-FUTURE-16 · minor · omission
- Target: modding-ugc, CNT.COOK.on-demand, ED.AI.generative, WLD.PCG.ml, radar
- Finding: Generative content is only covered at authoring time (ED.AI, tools only) and for PCG (X, `openworld`-only skill). Player-prompted **runtime** asset generation has no owner. This means meshes, textures or behaviours generated in-session and ingested as UGC, which requires runtime ingestion of untrusted generated geometry, validation, moderation and budget. There is also no radar entry, even as a speculative non-goal, for generative "world-model" rendering or simulation.
- Evidence: Roblox shipped Cube 3D text-to-mesh generation to creators and the runtime in 2025. Interactive world-model research (Genie 3, Muse/WHAM, 2025) is speculative for engines but is the most-cited long-term threat to the classic pipeline.
- Proposed change: Add `UGC.GEN.runtime-assets` (M, owner modding-ugc; contributors asset-cook-processors, security-engineering, online-services-liveops) covering runtime validation and cooking of generated assets under XC.SEC.genai. Add radar entry "Generative world models as renderer or simulator" (S, non-goal, owner render-architect, revisit trigger: controllable, deterministic model at interactive rates on consumer hardware).
