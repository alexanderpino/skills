# Findings for adjudication (round 1)

### K-COMPLETE-3 · major · omission
- Sweep: 5 (networking discipline) and 4 (every online-service boundary)
- Target: NET.TRANS, owner `network-transport`. Contributor: `security-engineering`.
- Finding: There is no HTTP(S), REST, WebSocket or TLS client capability. `NET.TRANS` covers UDP, reliability and QUIC evaluation only. Yet `PLAT.SVC.*`, `OBS.LOG.telemetry`, `OBS.CRASH.pipeline`, `BLD.REL.cdn`, `BLD.REL.on-demand`, remote config and UGC download all need an HTTPS client with a certificate store, pinning, retries, proxies, background downloads, and the platform HTTP stacks that consoles require. There is also no shared cryptographic-primitives capability: `CORE.TYPES.hashing` is non-cryptographic only, and CSPRNG and TLS library selection are unowned.
- Evidence: Precedents: UE `HTTP`/`WebSockets`/`SSL` modules, Unity `UnityWebRequest`, Godot `HTTPRequest`/`WebSocketPeer`. Console certification requires the platform network stack and TLS configuration. The web target (`PLAT.PAL.web`) cannot open UDP at all, so it needs WebSocket or WebTransport.
- Proposed change:
  - `NET.TRANS.http`: HTTP(S)/REST client & background downloads (platform stacks, retries, proxies)
  - `NET.TRANS.websocket`: WebSocket/WebRTC transport for web and service push
  - `XC.SEC.crypto`: Cryptographic primitives, CSPRNG & TLS/certificate policy, owner `security-engineering`

**Builder disposition:** HTTP(S)/TLS client placed in the PAL (platform stacks are mandatory on consoles) and crypto primitives in containers-core-types with a security-owned policy capability (XC.SEC.crypto-policy), instead of security owning the primitives.

---

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

**Builder disposition:** All proposed MR capabilities added to xr-runtime; splitting a mixed-reality skill rejected for now (xr-runtime owns 14 capabilities, below the size warning). Revisit if G2 shows distinct literature load.

---

### K-GAMEPLAY-4 · major · missing-contract
- Target: GAM.SYS.camera (gameplay-systems-toolkit), ANM.CINE.cameras (cinematics-sequencer), GAM.SYS.photo, RND.POST.camera (post-color-hdr), PLAT.XR.* (xr-runtime), RND.ARCH.multiview, WLD.PART.sources, C-AUDIO listener, C-RSCENE "views"
- Finding: Six skills own parts of "the camera", and no contract arbitrates which camera drives each view. Nothing defines:
  - blending gameplay camera ↔ cinematic camera ↔ photo mode ↔ XR head pose;
  - per-local-player views for split-screen;
  - camera shake and FOV kick, and accessibility reduction of them;
  - the camera-relative origin for large-world coordinates;
  - the streaming source and audio listener derived from the active view.

  `gameplay-systems-toolkit` provides **no** contract at all, so cinematics-sequencer (which does not consume C-GAME) and render-architect cannot consume the camera system except by reaching into it. The audio side has the same gap: there is no capability for multiple listeners or split-screen audio, although RND.ARCH.multiview and GAM.FW.local-players exist.
- Evidence: UE's PlayerCameraManager, view-target blending and Sequencer camera-cut takeover, and Unity Cinemachine's CinemachineBrain priority and blending, are exactly this arbitration layer. Split-screen audio (listener-per-player weighting, as in Wwise multi-listener) is a known certification and usability issue for local co-op.
- Proposed change:
  - Add contract `C-CAMERA` (layer 3: view descriptors per local player, including transform, projection and physical-camera parameters; priority and blend stack; shake channel; LWC origin) owned by gameplay-systems-toolkit.
  - Add capability GAM.SYS.camera-arbitration.
  - Make these skills consume C-CAMERA: render-architect (views), cinematics-sequencer (provides a camera source), xr-runtime (override), world-architect (streaming source), audio-architect (listeners), accessibility (shake and FOV limits).
  - Add AUD.ARCH.listeners "Multiple listeners & split-screen mixing" to audio-architect.

**Builder disposition:** View/camera arbitration placed in C-VIEW (L2, spatial-transforms) rather than a gameplay-owned C-CAMERA, so the editor, XR and cinematics can drive views without the gameplay layer; gameplay camera rigs are C-VIEW sources; shake/FOV channels and per-local-player views are in C-VIEW; AUD.ARCH.listeners added.

---

### K-GAMEPLAY-15 · major · maturity-error
- Target: GAM.AI.learned (X), GAM.AI.llm (X), ai-behavior-perception consumes, 06-gap-analysis A12
- Finding: 06 A12 says LLM NPCs are allowed "only behind an optional contract with moderation (platform-online-services), a budget, and an offline fallback". The data implements none of this.
  - ai-behavior-perception (profile `all`, an established skill) owns both experimental capabilities directly and consumes neither `C-ML?` nor `C-SVC?`.
  - There is no extension point, so 00 §7's rule that experimental work is reached only via an optional contract is violated and not machine-checked.
  - These concerns have no owner: generated-text localization and TTS voicing, rating and certification exposure (with a contributor from certification-compliance), player-data privacy, and persistence of conversational memory (C-SAVE).
  - The skill's expertise list has no ML competence.
- Evidence: Public demos (NVIDIA ACE, Inworld integrations, Ubisoft NEO NPC, 2024) all use cloud or GPU inference with latency, cost and safety constraints. Age ratings (ESRB/PEGI) and platform policies treat unmoderated generated content as UGC-class risk.
- Proposed change:
  - Add optional contract `C-AIAGENT` (layer 4: decision-provider extension point with budget, timeout and fallback) owned by ai-behavior-perception, and add `C-ML?` and `C-SVC?` to its consumes.
  - Move GAM.AI.llm and GAM.AI.learned behind that extension, and add GAM.AI.llm-guardrails with contributors security-engineering, certification-compliance and localization-i18n.
  - Add a check.py rule that an X/S capability owned by a skill tagged `all` or `client` requires a `?` contract.

**Builder disposition:** C-AIAGENT extension point, maturity changes and guardrail capabilities added; the proposed generic check.py rule for X/S capabilities is replaced by the radar rule (every non-E capability needs owner, revisit trigger and fallback).

---

### K-LEGACY-7 · major · scale-down
- Target: 00-design-principles §6 row 4, gpu-driven-pipeline profiles [mobile3d, std3d], RND.GEO.fallback, RND.GEO.visbuffer
- Finding: The stance "GPU-driven rendering with a CPU-driven fallback path" is new dogma for mobile. The justification, that the fallback exists because "low-tier and older mobile GPUs lack indirect or mesh-shader features", is technically incomplete. On tile-based mobile GPUs, CPU-side culling plus instanced/batched submission is often the *preferred* path even when indirect draws are supported. The reasons are: indirect draws defeat some drivers' binning optimizations; GPU culling adds compute passes and bandwidth that TBDR cannot hide in tile memory; mesh shaders are largely absent; and visibility-buffer shading is bandwidth-hostile on TBDR. Making the CPU path a "fallback" inside the GPU-culling expert's territory makes mobile a second-class path, owned by an agent whose expertise and critic checks ("no draw-call-centric assumptions") push the other way. The stance also does not say that 2D (C-DRAW2D batched draw lists) is legitimately CPU-batched.
- Evidence: Arm Mali and Qualcomm Adreno best-practice guides (indirect-draw and compute-to-graphics costs on TBDR). The mobile renderers of UE5 and Unity URP use CPU culling and instancing by default, and Nanite-class paths are desktop/console only. The Frostbite and Activision visibility-buffer talks target desktop/console bandwidth.
- Proposed change: Rewrite §6 row 4 as "Submission strategy (GPU-driven vs CPU-culled batched) chosen per hardware tier by render-architect ADR; GPU-driven is default for desktop/console tiers." Rename RND.GEO.fallback to RND.GEO.cpu-submission "CPU-culled batched/instanced submission path as a first-class tier path with its own budgets and tests", and move it to render-architect or give it an explicit mobile-tier owner with platform-mobile-portable as a contributor. Add an explicit "2D uses batched draw lists by design" line to §6. Add to RND.GEO.visbuffer a required TBDR suitability ADR.

**Builder disposition:** Stance rewritten and CPU submission made first-class, but kept in the same skill (renamed geometry-pipeline) because both paths serve one contract (C-INSTANCES); the per-tier choice is an ADR owned by render-architect (RND.ARCH.submission-strategy).

---

### K-PERF-8 · major · omission
- Target: reconstruction-upscaling (RND.RECON.dynres), world-architect (WLD.PART.sim-lod), platform-mobile-portable (PLAT.MOB.thermal), gpu-performance (PRF.GPU.power), cpu-performance (PRF.CPU.hybrid), vfx-particles (RND.VFX.budgets), animation-architect (ANM.ARCH.lod), performance-architect (PRF.METH.scalability)
- Finding: Runtime scalability actuators are spread across eight owners, and there is no closed-loop controller. Dynamic resolution, the significance/simulation LOD, VFX budgets, animation update rate, thermal adaptation and frame pacing would each react to frame time or power on their own. Independent controllers oscillate or fight each other, e.g. dynres dropping while VFX LOD also drops, then both overshoot. PRF.METH.scalability is a static framework of device profiles. Power and thermal ownership is split three ways (PLAT.MOB.thermal, PRF.GPU.power, PRF.CPU.hybrid), and "runtime power governor" is owned by none of them. Handhelds (PLAT.DESK.handheld) and mobile depend on this mechanism most.
- Evidence: Android's Adaptive Performance / ADPF (thermal headroom, performance hint sessions), Apple's thermal-state API and Unity's Adaptive Performance package all provide one governor that drives many knobs. UE combines Dynamic Resolution with the Significance Manager, but they are separate loops, which licensees coordinate by hand.
- Proposed change: Add PRF.METH.governor, "Runtime performance governor: consumes frame-time, GPU-time, thermal/power headroom and memory-pressure signals; drives registered scalability actuators with priorities and hysteresis". Owner: `performance-architect` (already runtime=true); contributors: `frame-orchestration`, `platform-mobile-portable`. Extend C-BUDGET with "actuator registration and control signals". RND.RECON.dynres, WLD.PART.sim-lod, RND.VFX.budgets and ANM.ARCH.lod then become registered actuators.

**Builder disposition:** Governor added, but owned by the new runtime skill runtime-scalability: performance-architect became a process skill (K-SYSTEMS-14), so it cannot own runtime code.

---

### K-PROD-2 · blocker · missing-contract
- Target: C-ORCH, ARCH.ORG.ownership-ledger, skills.json schema, contributors field in capabilities.json
- Finding: Territory is defined only as capabilities, and agents edit files and modules, not capabilities. No skill declares the code modules, directories or namespaces it may write. There is no rule for inherently shared files: root build scripts, module registration, shared shader include headers across 18 render experts, common component definitions, the reflection codegen output, and the project config. "Contributors" appear on many capabilities (for example CNT.COOK.variants ← performance-architect, WLD.ENV.buoyancy ← character-vehicle-physics), but nothing says whether a contributor may write the owner's code or only files change requests. The "ownership ledger & territory locks" therefore has no schema to lock against. check.py proves the capabilities are disjoint, but that does not prove that write sets are disjoint.
- Evidence: Real multi-team engines enforce module ownership mechanically (CODEOWNERS or Perforce protections, Unreal's module/plugin boundaries, Frostbite's per-team module ownership). Conflicting writes between parallel agents most often happen in shared registration and build files, not inside feature code.
- Proposed change: Add a `modules` field (module or namespace path globs) to every skill in skills.json, and have check.py verify the globs are disjoint. Extend the C-ORCH summary to cover the ledger schema, a shared-file protocol (named integration files have a single owner, program-orchestration or build-system-toolchains, and change only through a CR), and contributor semantics ("contributor = may submit CR and review; never writes owner module"). Add `ARCH.ORG.write-sets` ("Module/file write-set definition & shared-file protocol", owner program-orchestration).

**Builder disposition:** Write sets defined by module convention (src/<skill-id>/, tools/<skill-id>/, tests by the test-owning skill) and a shared-file protocol in C-ORCH + ARCH.ORG.write-sets; per-skill path globs are deferred until code exists (revisit at M0).

---

### K-PROD-8 · major · scale-down
- Target: skills.json configurations/profiles, program-orchestration, architecture-governance, docs/00 §5
- Finding: Scale-down is modeled only as runtime skill inclusion, and even that is blurred. indie-2d contains 87 of 124 skills, including research-evidence, architecture-governance, four performance experts, certification-compliance and collaboration-version-control, and the principles document admits this. There is no organizational scale-down. Nothing defines which skills one agent can host together when running a small effort, and nothing defines a lightweight governance tier. Every emerging technique needs an ADR with evidence, every change goes through the CR protocol, and every critic stage runs. The result is that the framework cannot be staffed economically for an indie-scale engine build, or during bootstrap when only a few agents are active.
- Evidence: Small engines (Godot, Bevy, Defold) succeed with a handful of maintainers who each span many domains, and with lightweight RFC processes. Process weight has to scale with team size just as runtime weight scales with configuration.
- Proposed change: Add `ARCH.ORG.staffing` ("Agent staffing tiers: which skills may be co-hosted by one agent per org scale", owner program-orchestration). Add a `host_group` field to skills.json for solo, small and large tiers, for example "core-runtime-* co-hosted" or "all perf experts co-hosted by performance-architect". Add `ARCH.GOV.process-tiers` ("Governance weight per org tier: which ADR/CR/critic stages are mandatory", owner architecture-governance). Report runtime-skill membership separately from process-skill membership in the configuration matrix so runtime scale-down becomes measurable.

**Builder disposition:** workstream field on every skill, ARCH.ORG.staffing and ARCH.GOV.process-tiers added; a per-skill host_group field is deferred to the staffing capability (revisit at M0 planning).

---

### K-QUALITY-6 · major · wrong-owner
- Target: QA.STRAT.contracts (test-architect); contracts.json (all 62 contracts)
- Finding: test-architect owns "contract tests between subsystems" for all 62 contracts. Writing a conformance suite for C-PHYS, C-RG, C-NET or C-TEMPORAL takes each domain's expertise, so the test-architect becomes a bottleneck. It is also the wrong owner for replaceability: 00 §3 claims C-PHYS "can be served by an integrated middleware or an in-house solver", and that claim is only verifiable if C-PHYS has a normative conformance suite. No contract records who owns its conformance suite, and no rule gives consumers a say in what is tested.
- Evidence: Consumer-driven contract testing (the Pact model) exists because provider-written tests encode the provider's assumptions. Replaceable-backend ecosystems depend on conformance test suites owned by the spec owner: Khronos Vulkan CTS, the WebGPU CTS, OpenXR CTS.
- Proposed change:
  - Add a `conformance` field to every contract in contracts.json, with owner = contract owner. Add a `check.py` rule that every non-P contract has one.
  - Narrow QA.STRAT.contracts to "contract-test framework & consumer-driven test policy" (test-architect).
  - Add a C-ORCH rule: each consumer skill contributes consumer-driven tests to the provider's suite, and a provider change must pass them.

**Builder disposition:** Conformance ownership stated in C-TEST/C-ORCH and a conformance flag on every code contract (checked); a separate conformance-owner field is redundant because the owner is always the contract owner.

---

### K-RENDER-7 · major · scale-down
- Target: configuration indie-2d / indie-2d-online-moddable (profile `min2d` = "Small 2D / 2.5D"); RND.GEO.fallback, RND.GEO.instancing (gpu-driven-pipeline), RND.TEX.formats, RND.TEX.mip-streaming (texture-streaming-vt), RND.LIGHT.units
- Finding: The min2d profile claims 2.5D, but no skill in it draws a 3D mesh. gpu-driven-pipeline, direct-lighting-shadows and translucency are all mobile3d/std3d. No skill in min2d owns runtime GPU texture formats or texture residency either, because RND.TEX.formats lives in texture-streaming-vt next to VT and sampler feedback. The closure check passes only because these dependencies are implicit rather than declared contracts.
- Evidence: 2.5D games are 3D-rendered with constrained cameras: Hollow Knight: Silksong-class layered scenes, Octopath-style HD-2D, and Ori (the last with unlit/lit meshes). Every 2D game still loads BCn/ASTC textures. Bundling the basic texture path with virtual texturing forces 2D to either carry VT or have no texture owner.
- Proposed change: Split texture-streaming-vt. Either give RND.TEX.formats and RND.TEX.mip-streaming a `client`-profile owner (e.g. gpu-memory-resources, or a new "texture-runtime" capability set), with VT, feedback and NTC as std3d/aaa tiers. Or retag texture-streaming-vt to `client` and declare VT optional. Add a `min2d`-profile "simple forward mesh path" capability (RND.GEO.simple-forward, owner gpu-driven-pipeline, retagged `client` with GPU-driven features as tiers). Alternatively, drop "2.5D" from the min2d description and add a `min25d` profile.

**Builder disposition:** texture-streaming-vt retagged 'all' with VT/feedback/NTC gated by capability-level profiles instead of splitting the skill; 2.5D handled by the lite3d base profile with first-class CPU submission (RND.GEO.cpu-submission) and planar physics (PHY.DYN.dof-lock).

---

### K-SYSTEMS-13 · major · omission
- Target: PLAT.MOB.thermal, PRF.CPU.hybrid, PRF.GPU.power, RND.RECON.dynres, CORE.FRAME.latency, CORE.JOBS.priorities, PLAT.DESK.handheld
- Finding: Power, thermal and QoS behavior is split across five capabilities. Three of them belong to reviewers (the performance experts), who by §8 do not own code. No one owns the *runtime governor*: the closed-loop controller that consumes platform performance hints and thermal headroom and sets frame-rate caps, dynamic-resolution targets, worker count and P/E placement, and simulation-LOD pressure. The platform APIs it consumes include Android ADPF (`PerformanceHintManager`, thermal headroom), Apple thermal state and QoS, Windows EcoQoS/power throttling and Game Mode, and the handheld TDP of Steam Deck/ROG Ally-class devices. Scaling down to mobile, portable and handheld depends on it.
- Evidence: Android ADPF is the Google-recommended path for sustained performance. Mobile titles (Genshin, CoD Mobile) ship adaptive governors. Console portables and handheld PCs expose power modes. Without one owner, dynres (reconstruction-upscaling), job placement (job-system) and thermal handling (platform-mobile) run three uncoordinated control loops.
- Proposed change: Add `CORE.FRAME.governor` ("Runtime performance/power governor: consumes thermal/power/perf-hint signals and budgets; drives frame-rate cap, dynres target, worker count/placement and sim-LOD pressure"), owned by frame-orchestration, with contributors platform-mobile-portable, platform-desktop, reconstruction-upscaling, job-system-task-graph and performance-architect. Add `PLAT.PAL.power` ("Power, thermal and performance-hint APIs") under platform-architect.

**Builder disposition:** Governor added under runtime-scalability instead of frame-orchestration, to keep one owner for the actuator registry and the control loop (merged with K-PERF-8).

---

### K-SYSTEMS-14 · minor · wrong-owner
- Target: C-BUDGET (owner performance-architect, universal runtime, L1)
- Finding: A runtime code contract (scalability hooks, device profiles) is owned by a cross-cutting reviewer skill that §8 says "does not own the code". C-BUDGET also mixes that runtime API with process data ("perf gate thresholds"). As a result, performance-architect is a runtime skill inside the foundation cycle (K-SYSTEMS-1).
- Evidence: The policy-vs-implementation pattern (§4) already puts budget *numbers* with performance-architect and enforcement with memory-allocators. The runtime scalability and device-profile hook is configuration machinery.
- Proposed change: Split C-BUDGET into two:
  - a runtime `C-SCALE` (L1): device profiles, scalability cvars, budget query and report API, owned by core-runtime-architect next to C-CFG;
  - a process `C-BUDGET` (layer P): budget numbers per tier and gate thresholds, owned by performance-architect.
  
  Set performance-architect `runtime: false`.

**Builder disposition:** C-BUDGET split as proposed; the runtime C-SCALE is owned by the new expert runtime-scalability under core-runtime-architect rather than by the lead itself.

---

### K-TOOLS-12 · major · omission
- Target: ED.WORLD, `world-editor-viewport`, `world-data-model`
- Finding: Level-design workflows are missing: blockout and greyboxing, in-editor geometry and modeling tools (primitive brushes, booleans, polygon editing, basic UVs, mesh baking from blockout), and level-design utilities (measure, grid, markers, layer/actor visibility filters, bulk replace). ED.WORLD holds six capabilities covering viewport, gizmo, placement, partition, splines and mode hosting. This is thin compared with the 40-capability WLD domain it edits.
- Evidence: UE5 Modeling Mode and CubeGrid, Hammer/Radiant-lineage brush tools and Unity ProBuilder are standard blockout paths. Level designers iterate there long before art exists.
- Proposed change: Add `ED.WORLD.blockout` ("Blockout & in-editor modeling tools")→world-editor-viewport (contributor asset-cook-processors for mesh operations) and `ED.WORLD.ld-utilities` ("Level-design utilities: measure, filters, bulk replace, layer visibility")→world-editor-viewport. If the modeling-tool literature (geometry processing) is judged distinct, split out an expert `mesh-modeling-tools` under editor-architect.

**Builder disposition:** Blockout and level-design utilities added to world-editor-viewport and geometry operations to asset-cook-processors; a separate mesh-modeling-tools skill is deferred (revisit in G2).

---
