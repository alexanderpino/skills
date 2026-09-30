# K-FUTURE · Future-Technology Critic · round 3

Blind review. I read only files inside the framework directory. `check.py` passes (0 errors). None of the findings below repeats something check.py proves.

### K-FUTURE-1 · major · wrong-boundary
- **Target:** C-RT, C-RTAS, C-MLGPU (the `gated` flag), C-GPUTIER, RND.GI.hybrid, RND.PT.realtime, configurations
- **Finding:** Gating is absolute. check.py only lets a skill consume C-RT, C-RTAS or C-MLGPU optionally, in every configuration, so no tier or configuration can ever *require* hardware ray tracing or GPU inference. Every std3d/aaa lighting, shadow, reflection and reconstruction feature therefore has to keep a non-RT, non-ML path permanently, and pay to validate it. The framework cannot express the RT-only renderer that current AAA work is already moving to, or the RT+ML baseline that next-generation consoles will very likely have within about five years.
- **Evidence:** HW RT is already required by shipped titles: Metro Exodus Enhanced Edition (2021, RT-only GI), Indiana Jones and the Great Circle (2024) and Doom: The Dark Ages (2025). Every current console, Switch 2 and recent Apple and Android flagship GPUs have HW RT. ML reconstruction is now platform-standard: PSSR on PS5 Pro, DLSS on Switch 2 and FSR 4. RND.RT.software already gives the non-HW fallback where a tier needs one.
- **Proposed change:** Make gating depend on the tier. Add GPU tiers `rt` and `rt+tensor` to C-GPUTIER, and a profile add-on `hwrt` (or let `aaa` declare it). Change the gate rule so that C-RT/C-RTAS/C-MLGPU may be consumed non-optionally by modules whose capabilities carry that profile. Add a configuration `rt-required-3d-client` (std3d+aaa+hwrt, pc+console), claimed at M6. Record in docs/00 §7 that "gated" means "optional below the declaring tier".

### K-FUTURE-2 · major · other (contract freeze hard-codes current API)
- **Target:** milestones.json M1.contracts_frozen (C-RHI, C-SHADER, C-GPUTIER, C-RG, C-PRESENT), M2.contracts_frozen (C-ML, C-MLGPU, C-AIAGENT)
- **Finding:** The fastest-moving API surfaces are frozen at the earliest milestones, before any consumer of those surfaces exists.
  - M1 freezes C-RHI at the indie-2D-on-PC milestone. That freeze covers tensor/matrix resource types, "state-object programs" and the mesh/RT/tensor tiers of C-GPUTIER, yet std3d arrives at M3, RT at M4 and the neural features at M6.
  - M2, another 2D milestone, freezes C-ML/C-MLGPU (NPU backends, sequence sessions, KV-cache/token streaming, local/remote routing, in-shader weights) and C-AIAGENT (LLM providers). No ML consumer is exercised by then.
  - The freeze model has no carve-out for extensions, so each tier change to these contracts becomes a breaking change on a frozen contract.
- **Evidence:** In 2025 alone, DXR 1.2 added OMM/SER, cooperative vectors stayed in preview while Microsoft signalled a broader linear-algebra successor, Vulkan split cooperative-matrix and cooperative-vector extensions, and work graphs added mesh nodes. NNAPI was deprecated (Android 15), Windows ML reached GA and Apple shipped the Foundation Models API. A surface frozen at M1/M2 would have been wrong within a year.
- **Proposed change:** Add `extension_tiers` to contracts.json (for example C-RHI: tensor, work-graph, cluster-AS, descriptor-heap; C-ML: npu, sequence, remote). Let milestones freeze only a contract's core. Each extension tier freezes at the milestone that first claims a configuration consuming it (C-RHI.rt at M4, C-RHI.tensor and C-ML.sequence at M6). Extend check.py's freeze rule to tiers. Tiers containing X capabilities stay unfrozen until those capabilities are promoted.

### K-FUTURE-3 · major · maturity-error
- **Target:** RND.GEO.splat-relight (E, std3d), RND.GEO.splats (M), CNT.IMP.splats (X, experimental)
- **Finding:** The maturity labels on the splat work are inverted.
  - The most research-grade part, relightable/dynamic splats with hybrid raster/RT composition, is labelled Established. It therefore bypasses the radar, has no fallback, and is included in every std3d configuration (confirmed: it sits in standard-3d-client).
  - Static splat rendering is M, but the only way to get splats in, import, is X and confined to the experimental profile. Non-experimental configurations can render splats but cannot import them.
- **Evidence:** Relightable Gaussians are still SIGGRAPH/CVPR research in 2024–2025 (Relightable 3D Gaussians, GS³, 3DGRT/3DGUT). Static-splat viewers and importers do ship (PlayCanvas SuperSplat, Niantic .spz, the Khronos KHR_gaussian_splatting extension work in 2025). Import cannot be less mature than the renderer that consumes it.
- **Proposed change:** Set RND.GEO.splat-relight to X with profile ['experimental'] and add a radar entry (fallback: static splats composited unlit, or mesh proxies). Set CNT.IMP.splats to M with no profile, or to the same profile as RND.GEO.splats, and name the format candidates (PLY/.spz/KHR_gaussian_splatting) in the evidence.

### K-FUTURE-4 · major · maturity-error (radar content)
- **Target:** radar.json entries whose tech name carries a capability id in parentheses: RND.SHADER.autodiff, QA.FUNC.agent-exploration, CNT.COOK.ml-assisted, PHY.SOFT.hair-sim, RND.PT.realtime, PLAT.WEB.webgpu-target, CNT.IMP.materialx, CNT.IMP.geospatial, XC.SEC.memory-safety, CNT.IMP.splats, RND.GEO.splats, XC.SEC.genai
- **Finding:** These entries copy another entry's evidence, trigger and fallback word for word, and the copied text does not fit the capability. Promotion triggers and fallbacks that agents will act on are therefore wrong:
  - RND.SHADER.autodiff (a compile-time transform) is to be promoted on "non-preview cross-vendor support", with fallback "standalone inference dispatch".
  - QA.FUNC.agent-exploration falls back to "CLI/commandlets".
  - CNT.COOK.ml-assisted falls back to "manual authoring".
  - PHY.SOFT.hair-sim (simulation) falls back to "hair cards" (rendering).
  - RND.PT.realtime falls back to "probe GI", although path tracing replaces shadows and reflections as well.
  - PLAT.WEB.webgpu-target is promoted on "bindless in WebGPU", which is unrelated to how mature the target is.
- **Evidence:** A radar is useful only if each trigger is observable for the capability it governs (ThoughtWorks radar practice). WebGPU shipped in all four major engines in 2025 (Safari 26, Firefox 141), so the real target trigger is essentially met while the copied one never will be.
- **Proposed change:** Rewrite each of these as its own entry. Examples: autodiff: evidence "Slang autodiff in production tools", trigger "two tool-side consumers", fallback "hand-derived gradients". agent-exploration: fallback "scripted bots + random-walk monkeys". ml-assisted cook: fallback "classical processors". hair-sim: fallback "bone-chain dynamics". PT: fallback "hybrid raster + RT effects". webgpu-target: trigger "WebGPU on by default in all major desktop and mobile browsers". Add a check that fails any two radar entries with identical evidence+revisit+fallback unless they list the same capabilities.

### K-FUTURE-5 · major · omission
- **Target:** ARCH.GOV.radar, architecture-governance, research-evidence
- **Finding:** Nothing owns the transitions between maturity classes. Promotion X→M→E would mean dropping the `experimental` profile, removing an optional `?`, freezing an extension tier, adding conformance and budgets, and re-running critics. Demotion or deprecation would cover vendor withdrawal such as NNAPI, AFR multi-GPU or Azure Remote Rendering (retired 2025), including moving the technique into legacy-patterns.json. The radar has "revisit" text but no cadence, watcher, checklist or data change. An E label is never re-examined, which is how K-FUTURE-3 passed.
- **Evidence:** In a five-year horizon several X entries (work graphs, NTC, neural materials, cluster BLAS) will cross their triggers and some M entries will die. Without a protocol, each crossing becomes an ad-hoc ADR fought across workstreams.
- **Proposed change:** Add ARCH.GOV.radar-transitions (E, owner architecture-governance, contributors research-evidence and api-lifecycle-migration): trigger review at every milestone exit, a promotion checklist (evidence bundle, profile retag, gate/optional change, extension-tier freeze, conformance, budget), demotion into legacy-patterns.json with a removal plan, and a required radar-style citation for any E capability introduced after G1.

### K-FUTURE-6 · major · dependency-error
- **Target:** ML.RT.sequence-models (X, experimental), AUD.CONTENT.speech (M), GAM.AI.llm-dialogue (M), GAM.AI.local-guardrails (M), ML.RT.os-models (M), C-ML summary
- **Finding:** Several default-profile M capabilities need the machinery for running autoregressive models on the device: on-device TTS/ASR, the offline branch of LLM dialogue with local guardrails, and OS foundation-model sessions that stream tokens. That machinery (KV cache, token streaming, cancellation, constrained decoding) is ML.RT.sequence-models, which is X and experimental-only. Meanwhile the frozen C-ML contract already includes "sequence sessions, streaming results". So either M features silently rely on an X capability, or the X label is stale.
- **Evidence:** Whisper-class ASR and on-device TTS ship widely. inZOI (early access, March 2025) shipped on-device SLM characters through NVIDIA ACE. Apple's Foundation Models framework (2025) exposes streaming sessions. The radar evidence "2025 on-device SLM demos" is out of date.
- **Proposed change:** Split ML.RT.sequence-models into ML.RT.sequence-exec (M: KV-cache budgets, streaming, cancellation; evidence ASR/TTS/inZOI) and ML.RT.constrained-decoding-in-frame (X, experimental). Add sequence-exec as the dependency named by AUD.CONTENT.speech and GAM.AI.local-guardrails.

### K-FUTURE-7 · major · omission
- **Target:** crosscutting.json independence, ARCH.ORG.independence, ARCH.ORG.critic-calibration, ARCH.ORG.provenance
- **Finding:** Independence is enforced only by skill and workstream. If the implementer, the oracle author and the critic all run on the same foundation model, their errors are correlated and "independence" is nominal. Nothing requires diversity of model lineage, and nothing re-qualifies critics or oracles when the agents' model or prompt version changes. Over a multi-year build this will happen several times.
- **Evidence:** LLM evaluators favour their own generations (Panickssery et al., NeurIPS 2024). LLM-as-judge biases are documented (Zheng et al., 2023). LLM errors are correlated across models of the same provider or lineage (Kim et al., "Correlated Errors in LLMs", ICML 2025). Model generations turn over roughly every 6–12 months.
- **Proposed change:** Add a lineage dimension to the independence matrix (implementer vs oracle_author and S3/S4 critics: different model family or version, or a higher ARCH.ORG.human-audit rate if not). Add ARCH.ORG.model-requalification (M, architecture-governance): any change of agent model or prompt re-runs seeded-defect calibration and holdout suites before the agent counts as a gate. Record the model in ARCH.ORG.provenance.

### K-FUTURE-8 · major · maturity-error
- **Target:** ARCH.ORG.staffing, ARCH.ORG.ownership-ledger, ARCH.ORG.change-requests, ARCH.ORG.escalation, ARCH.ORG.skill-lifecycle, ARCH.ORG.independence, QA.AGENT.holdout, QA.AGENT.gate-canaries, QA.AGENT.oracle-change-control, QA.CERT.code-provenance, ED.ARCH.automation-security
- **Finding:** These capabilities organise and constrain around 150 autonomous agents: co-hosting, territory locks, agent-to-agent change requests, decision SLAs, holdouts against reward hacking, and agent action security. They are labelled E, so they escape the radar and have no fallback. Only seven agent capabilities are M. The human-team analogues are established; applied to autonomous agents at engine scale they have no production precedent.
- **Evidence:** The framework's own radar cites "reward-hacking reports in agentic coding (2025)" and dates prompt-injection CVEs to 2025. No 2026 engine or program of comparable size has published results for an agent organisation.
- **Proposed change:** Relabel these capabilities M. Add one radar entry, "Autonomous multi-agent engine program", with measurable triggers (seeded-defect escape rate, rework per change request, frozen-contract churn per milestone) and the fallback "human lead per workstream and human-authored oracles for S4 contracts".

### K-FUTURE-9 · major · obsolete-assumption
- **Target:** CORE.LIFE.language, CORE.LIFE.interop, CORE.LIFE.asserts, BLD.SYS.compile-speed, XC.ITER.live-coding, RND.SHADER.interop, CORE.REFL.generation, core-runtime-architect.expertise
- **Finding:** C++ is fixed as the implementation language through capability wording ("C++26 adoption plan", "C++ modules, unity builds, PCH", "C++ live coding", "C++/shader interop headers") and the lead's expertise ("C++20/23"). Memory-safe languages appear only as M "interop components" and "parsers". docs/00 §9 leaves only the *scripting* language open. An engine started in 2026 and written by agents should treat the language as an evidence-backed ADR. Compiler-checked ownership also directly limits a class of defects agents introduce (UB, data races) that tests catch poorly.
- **Evidence:** Memory-safety vulnerabilities in Android fell from 76% to 24% as new code moved to Rust (Google, 2024). CISA/NSA memory-safety roadmap guidance. Tiny Glade shipped on Bevy ECS (2024). Rust is in production in the Windows kernel and Chromium. Console toolchains for Rust exist under NDA, but only some platforms support them first-party. That is a real risk, and it belongs in an ADR rather than capability names.
- **Proposed change:** Rename to language-neutral wording: CORE.LIFE.language "Implementation language(s) ADR (C++, Rust, mixed) with standard/edition baseline". BLD.SYS.compile-speed "Compile-time scalability (modules/unity/PCH or crate-graph partitioning)". XC.ITER.live-coding "Native-code live coding". RND.SHADER.interop "Host/shader interop headers". Add a B-list ADR in docs/06 owned by core-runtime-architect with security-engineering, and add Rust/FFI expertise to core-runtime-architect.

### K-FUTURE-10 · major · scale-down
- **Target:** PLAT.WEB.runtime, platform-web, CORE.JOBS.degenerate, indie-2d-online-web-client
- **Finding:** PLAT.WEB.runtime makes SharedArrayBuffer *required* and "cross-origin isolation assumed on every host". Many real web-game hosts cannot set COOP/COEP: iframe portals, ad and payment SDK embeds, social and messenger game surfaces. Requiring it contradicts CORE.JOBS.degenerate (0-worker inline mode), which exists for exactly this case. Web builds would fail on the hosts where 2D and indie web games actually ship.
- **Evidence:** Godot 4.3 (2024) reintroduced single-threaded web exports because threaded exports could not run on many hosts. Unity Web keeps threading opt-in. COEP `credentialless` is not universal across browsers.
- **Proposed change:** Reword PLAT.WEB.runtime to "WASM threads when cross-origin isolated; host-capability probe selects threaded vs inline (CORE.JOBS.degenerate) build/runtime mode". Add a web configuration variant or C-TARGETPLAT flag for non-isolated hosts, and a gate proving that indie-2d-online-web-client runs without SharedArrayBuffer.

### K-FUTURE-11 · major · omission
- **Target:** ANM.IK.physical, rigid-body-dynamics, ik-procedural-animation, physics-architect, PHY.SOFT.ml
- **Finding:** There is no extension point for learned policies or surrogates *inside the physics step*: RL-trained physics-based characters, and learned simulators for destruction or fluids. Only cloth-deformables consumes C-ML in the physics domain, and rigid-body-dynamics and ik-procedural-animation do not consume it at all. Inference inside the substep loop has distinctive constraints: latency inside the solver, a batch per substep, and determinism or recorded outputs under rollback. Retrofitting that later means reopening C-PHYS.
- **Evidence:** Physics-based learned character control is advancing fast (MaskedMimic, SIGGRAPH Asia 2024; PHC 2023; Ubisoft La Forge and EA SEED work). Learned deformation and simulation surrogates are already shipping in tools (UE ML Deformer). This is highly likely to matter within five years.
- **Proposed change:** Add ANM.IK.learned-physics (X, experimental; owner ik-procedural-animation; contributors rigid-body-dynamics and ml-inference-runtime) and PHY.ARCH.learned-surrogates (X, experimental; owner physics-architect). Add optional consumption `C-ML?` to ik-procedural-animation and physics-architect. Add a C-PHYS obligation: a substep policy hook with recorded or deterministic outputs.

### K-FUTURE-12 · major · omission
- **Target:** untrusted-inputs.json, GAM.AI.llm-dialogue, AUD.CONTENT.speech, XC.SEC.genai
- **Finding:** The registry covers model *outputs* (`generated-content`) and player-to-player `chat-text`. It does not cover player free text or voice sent *to* an in-game model: prompts to LLM NPCs, voice through ASR into a dialogue model, and player prompts for generated assets. That is the direct prompt-injection surface (jailbreak to off-rating content, spoiler or system-prompt extraction, cost DoS, manipulating a tool-using NPC). It has no validating owner, red-team corpus or limits.
- **Evidence:** OWASP LLM01 (prompt injection) and LLM10 (unbounded consumption). Public jailbreaks of voiced AI NPCs after launch in 2025 (for example, the Fortnite Darth Vader NPC, which needed an emergency patch).
- **Proposed change:** Add input `player-model-prompts` with validating_owner ai-behavior-perception, parser_owners [audio-content-runtime, online-services-liveops, modding-ugc], trust hostile-remote, mode redteam+harness, limits "length/rate/token budget/moderation pre-filter". Reference it from XC.SEC.genai and GAM.AI.local-guardrails.

### K-FUTURE-13 · minor · scale-down
- **Target:** ml-inference-runtime.profiles ['all']
- **Finding:** Every configuration contains the ML runtime and its M capabilities (inference, OS-model backends, weight residency), including minimal-client, indie-2d-client and the web 2D client (confirmed with model.cap_in_configuration). This is so even though every consumer uses `C-ML?` optionally and the radar fallback is "no ML features".
- **Evidence:** An ONNX-class runtime adds MBs of binary to WASM and mobile 2D builds, and on OS-model platforms it brings permissions and privacy review with it.
- **Proposed change:** Give ml-inference-runtime its own add-on profile (`ml`), or derive membership from an enabled consumer capability. Keep it in `experimental`, `aaa` and `xr` by default.

### K-FUTURE-14 · minor · overlap
- **Target:** ML.RT.npu (ml-inference-runtime), RND.GPU.hetero-offload (gpu-platform-architect)
- **Finding:** Both claim inference offload to the NPU or integrated GPU. RND.GPU.hetero-offload's name lists "inference … on the integrated GPU/NPU". Two agents would each build an NPU/iGPU placement policy.
- **Evidence:** Windows ML and DirectML route to NPU and iGPU through one execution-provider API, so the placement decision is a single decision.
- **Proposed change:** Reword RND.GPU.hetero-offload to "non-inference async work and encode on a secondary adapter". Add gpu-platform-architect as a contributor to ML.RT.npu for adapter selection.

### K-FUTURE-15 · minor · maturity-error
- **Target:** WLD.PCG.ml (X, experimental)
- **Finding:** Two things are conflated. Tool-side ML generation whose output is cooked and cached is deterministic by construction and is M. Runtime ML generation at stream-in is X. Putting everything in the experimental profile blocks the tool-side use that already ships.
- **Evidence:** ML-assisted terrain, texture and layout generation ships in editors (Unity AI, Roblox Cube 3D in 2025). The trigger "deterministic models" only matters at runtime.
- **Proposed change:** Split into WLD.PCG.ml-bake (M, tool-side via C-COOK with provenance through ED.AI.provenance) and WLD.PCG.ml-runtime (X, experimental).

### K-FUTURE-16 · minor · obsolete-assumption
- **Target:** ml-inference-runtime.purpose/expertise ("cooperative-vector"), radar "In-shader neural evaluation" evidence ("SM 6.9 cooperative vectors (preview)"), RES.IO.gpu-decompress ("GDeflate class")
- **Finding:** The briefs of the agents who will write SKILL.md name preview or vendor API constructs, even though the capabilities themselves are API-neutral. Cooperative vectors did not leave preview in SM 6.9 and are being superseded by a broader linear-algebra API. GPU decompression is gaining Zstandard alongside GDeflate (DirectStorage 1.4 announcement, 2025).
- **Evidence:** DirectX developer blog 2025 (SM 6.9 release notes and linear-algebra roadmap); DirectStorage Zstd announcement (GDC 2025).
- **Proposed change:** Use "matrix/tensor intrinsics tier" in ml-inference-runtime, and "GPU-decodable codecs (GDeflate/Zstd class)" in RES.IO.gpu-decompress. Refresh the radar evidence to the 2025 state.

### K-FUTURE-17 · minor · wrong-owner
- **Target:** PLAT.PAL.cloud-hybrid (owner platform-architect)
- **Finding:** Splitting simulation between client and cloud is an authority, latency-hiding and replication problem (what runs where, reconciliation, what happens on disconnect), not an OS abstraction. Leaving it with the PAL lead means the capability will be designed without netcode expertise.
- **Evidence:** Crackdown 3's cloud destruction was built as a server-authoritative replication problem. Azure Remote Rendering was retired in 2025 over cost and latency, which is networking and ops territory.
- **Proposed change:** Move ownership to network-architect, with contributors platform-architect, frame-orchestration and online-services-liveops. Update the radar owner.
