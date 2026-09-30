# K-QUALITY · Round 1 findings (Quality & Security Critic, blind)

### K-QUALITY-1 · blocker · omission
- Target: test-architect, program-orchestration, C-TEST, C-ORCH, QA.STRAT.*, QA.RENDER.golden, PRF.BENCH.regression
- Finding: Nothing owns verifying what the autonomous implementers produce. The only validation obligation is "meet the test definition of done" (crosscutting.json `testing`), and the same agent that writes the code also writes the tests that satisfy that DoD. The map has no capability and no contract covering:
  - who authors acceptance tests and oracles, and whether that author must be independent of the implementer;
  - who may edit, loosen or re-baseline golden images, perceptual tolerances, perf thresholds, fuzz corpora and expected state hashes;
  - detection of vacuous or gamed tests: assert-free tests, special-casing test inputs, `skip`/`xfail`/quarantine used to turn a gate green, widened tolerances, deleted cases;
  - any rule that mutation score or oracle strength counts toward the DoD. QA.STRAT.coverage says "coverage & mutation testing" but no gate consumes it.
  QA.STRAT.flaky (quarantine policy) is a direct green-washing channel with no guard. ARCH.ORG.critic-gates only *schedules* gates. Nobody defines what evidence an agent must hand an S3/S4 critic.
- Evidence: Reward hacking by coding agents is documented. Models special-case tests or edit them to pass: METR's 2025 reports on reward hacking in frontier models, and the Claude 3.7 Sonnet system card on "special-casing tests". Golden-image suites are only as strong as their re-baseline discipline; a baseline refreshed in the same change as the feature makes the test meaningless. Google's mutation-testing practice (Petrović & Ivanković, ICSE-SEIP 2018) exists because coverage alone does not show oracle strength. The brief's bar is that "an independent critic can objectively determine correctness", and that is not met while the implementer controls the oracle.
- Proposed change: Add area `QA.AGENT` owned by `test-architect`:
  - `QA.AGENT.oracle-independence`: acceptance tests and oracles are authored or approved by an agent other than the implementer. Contributor: program-orchestration.
  - `QA.AGENT.baseline-governance`: changes to goldens, tolerances, perf thresholds, expected hashes and corpora need a separate reviewed change with a justification. Contributors: render-validation, perf-benchmarking.
  - `QA.AGENT.test-integrity`: automated detection of weakened tests (deleted or skipped cases, loosened tolerances, assert-free tests, input special-casing) as a merge gate. Contributor: ci-cd-automation.
  - `QA.AGENT.mutation-gate`: a mutation-score threshold per skill tier, as part of the DoD.
  Extend the `C-TEST` summary to "evidence bundle an implementer must hand to S3/S4 critics". Add to `C-ORCH` a territory rule: test and oracle files are owned by the test-owning skill in the ledger, not by the implementer.

### K-QUALITY-2 · major · other
- Target: critics.json (K-GAMEPLAY, K-PLATFORM, K-QUALITY stages); 25 skills at S3, 15 at S4
- Finding: I computed the coverage from the scope and stage fields in critics.json.
  - **S3 (implementation review):** 25 skills get no domain critic. They are all of animation (animation-architect, animation-runtime, animation-graphs, motion-synthesis, facial-animation), audio-dsp-mixing, spatial-audio-acoustics, audio-content-runtime, all of gameplay (gameplay-architect, gameplay-systems-toolkit, navigation-pathfinding, ai-behavior-perception), platform-architect, platform-desktop, platform-console, platform-mobile-portable, input-system, input-devices-haptics, text-fonts, localization-i18n and accessibility. The cause is that K-GAMEPLAY and K-PLATFORM lack stage S3. Real-time audio DSP code, console platform code, text shaping and bidi get only generalist review (PERF, LEGACY, QUALITY).
  - **S4 (validation & release):** none of the core runtime has a domain critic: job-system-task-graph, concurrency-primitives, memory-allocators, ecs-runtime, serialization-schema, frame-orchestration, package-formats-vfs, resource-streaming-architect, observability-telemetry and the others. K-SYSTEMS lacks S4.
  - **S1/S2:** test-architect, functional-automation-soak, robustness-fuzzing and security-engineering have no domain critic, because K-QUALITY has no S1/S2.
- Evidence: 00-design-principles §1 condition 4 says "a critic can decide whether it is correct". The stage matrix shows that for S3/S4 there is no critic with the literature to decide it. Two examples: lock-free audio-thread correctness (no allocation or locks on the audio callback), and console TRC-relevant platform code.
- Proposed change: Add `S3` to K-GAMEPLAY and K-PLATFORM, `S4` to K-SYSTEMS, and `S1`, `S2` to K-QUALITY (or to the split critics in K-QUALITY-3). Add a `check.py` rule: every skill with `runtime: true` has at least one scoped (non-`all`) critic at each of S2, S3 and S4, and every skill has one at S1.

### K-QUALITY-3 · major · other
- Target: K-QUALITY, security-engineering subtree, critics.json
- Finding: One critic carries both "testing/validation" and "security" for all 124 skills. Neither specialty has a dedicated reviewer, and security is never reviewed at the design stages (S1/S2), which is where threat models and trust boundaries are decided. These skills handle untrusted input or secrets but have only K-QUALITY as their security reviewer: network-transport crypto and auth, scripting-runtime sandbox, modding-ugc, plugin-system, package-formats-vfs signing, packaging-release-patching signing, ci-cd-automation secrets, and observability-telemetry privacy.
- Evidence: Threat modeling (STRIDE, Microsoft SDL) is a design-time activity. SDL puts threat modeling and security design review before implementation. A security review that first happens at code review finds boundary errors after contracts are frozen.
- Proposed change: Split K-QUALITY into:
  - **K-TEST** (validation, oracles, determinism and concurrency testing, agent-output integrity): scope all plus subtree test-architect; stages G1, G2, S2, S3, S4.
  - **K-SEC** (threat model, trust boundaries, memory safety, supply chain, privacy, incident response): scope subtree security-engineering, network-transport, scripting-runtime, modding-ugc, plugin-system, serialization-schema, package-formats-vfs, persistence-save, platform-online-services, packaging-release-patching, ci-cd-automation, build-system-toolchains, observability-telemetry, crash-diagnostics, editor-architect, ai-assisted-authoring, ai-behavior-perception, dedicated-server; stages G1, G2, S1, S2, S3, S4.

### K-QUALITY-4 · major · other
- Target: PROTOCOL.md convergence rule; ARCH.ORG.critic-gates; critics.json
- Finding: The builder can game the G1 stop rule, and the same design is reused for S-stage gates:
  1. **Self-adjudication of rejections.** Convergence counts only *accepted* blocker and major findings, and the builder alone decides accept or reject. Rejecting a finding with a plausible "technical reason" lowers the count without anyone independent checking it.
  2. **Builder decides "new evidence".** A re-raised rejected finding is non-material unless it brings new evidence, and the builder judges that. Blind critics cannot know a finding was rejected, so they cannot present it as new.
  3. **No critic calibration.** A lazy or weak critic instance that finds nothing counts as a clean round, and condition B then rewards it.
  No capability owns the critic framework's own validity (critic definitions, calibration, adjudication). ARCH.ORG.critic-gates is scheduling only.
- Evidence: Software-inspection literature uses defect seeding and capture–recapture to estimate the defects that remain and the reviewers' yield (Eick et al., ICSE 1992; Briand et al., TSE 2000). Mutation testing of critics is the same idea. Separating the adjudicator from the author is standard in safety-critical review (DO-178C independence objectives).
- Proposed change:
  - Add `ARCH.ORG.critic-calibration` (owner program-orchestration, contributor test-architect). Each round seeds N known defects into a mutated copy of the artifact (omissions, double owners that check.py cannot see, wrong owners), and a round counts toward convergence only if the seeded-defect recall is at or above a threshold.
  - Add `ARCH.ORG.adjudication`: every rejected blocker or major finding goes to a fresh-context adjudicator (not the builder), and convergence counts findings that the adjudicator upheld.
  - Record rejected findings in data so the gate can match re-raises mechanically.
  - Apply the same calibration and adjudication to S3/S4 gates on agent code.

### K-QUALITY-5 · major · omission
- Target: physics-architect, rigid-body-dynamics, cloth-deformables, fluid-simulation, animation-architect, animation-runtime, audio-architect, audio-dsp-mixing, spatial-audio-acoustics, network-architect, replication, prediction-rollback, test-architect
- Finding: Rendering has a dedicated validation expert with a reference oracle: QA.RENDER.* plus RND.PT.reference and RND.MAT.validation. No other domain has a validation capability or an oracle owner. Nobody owns:
  - simulation validation against analytic references (energy and momentum conservation, drift, restitution, stacking stability, joint error, CCD tunnelling cases);
  - animation validation (compression error against raw clips, retarget error, IK reachability and error);
  - audio correctness (bit-exact DSP against a reference implementation, loudness conformance, glitch and underrun detection, latency measurement, objective HRTF and spatialization tests);
  - netcode correctness (prediction-misprediction rate, reconciliation convergence, deterministic simulation of the network and server, replication consistency under loss and reorder).
  QA.FUNC.network is only "network test harnesses", not a correctness oracle.
- Evidence:
  - Physics: Box2D v3 ships benchmark scenes and a cross-platform determinism hash test, and Jolt has an extensive sample and unit-test corpus with performance-test scenes. Those are the oracle suites a physics agent must be validated against.
  - Animation: ACL validates compression against per-bone object-space error on a clip corpus (the CMU database).
  - Audio: ITU-R BS.1770 / EBU R128 define objective loudness measurement, and null tests plus offline bit-exact render are standard DSP regression methods.
  - Netcode: deterministic simulation testing is proven practice (FoundationDB simulation, TigerBeetle VOPR), and Overwatch's GDC 2017 netcode talk describes replay-based validation.
- Proposed change: Follow the existing RND.MAT.validation pattern (the domain owner defines the oracle, a QA skill runs it):
  - `PHY.ARCH.validation`: analytic and reference-scene oracle suite. Owner physics-architect, contributor test-architect.
  - `ANM.ARCH.validation`: pose and compression error metrics against raw data. Owner animation-architect.
  - `AUD.ARCH.validation`: offline bit-exact render, loudness, glitch and latency oracles. Owner audio-architect.
  - `NET.ARCH.validation`: deterministic net-simulation harness and prediction/replication correctness metrics. Owner network-architect, contributor functional-automation-soak.
  - `QA.STRAT.oracles`: oracle taxonomy and policy (analytic, reference implementation, metamorphic, differential, golden). Owner test-architect.

### K-QUALITY-6 · major · wrong-owner
- Target: QA.STRAT.contracts (test-architect); contracts.json (all 62 contracts)
- Finding: test-architect owns "contract tests between subsystems" for all 62 contracts. Writing a conformance suite for C-PHYS, C-RG, C-NET or C-TEMPORAL takes each domain's expertise, so the test-architect becomes a bottleneck. It is also the wrong owner for replaceability: 00 §3 claims C-PHYS "can be served by an integrated middleware or an in-house solver", and that claim is only verifiable if C-PHYS has a normative conformance suite. No contract records who owns its conformance suite, and no rule gives consumers a say in what is tested.
- Evidence: Consumer-driven contract testing (the Pact model) exists because provider-written tests encode the provider's assumptions. Replaceable-backend ecosystems depend on conformance test suites owned by the spec owner: Khronos Vulkan CTS, the WebGPU CTS, OpenXR CTS.
- Proposed change:
  - Add a `conformance` field to every contract in contracts.json, with owner = contract owner. Add a `check.py` rule that every non-P contract has one.
  - Narrow QA.STRAT.contracts to "contract-test framework & consumer-driven test policy" (test-architect).
  - Add a C-ORCH rule: each consumer skill contributes consumer-driven tests to the provider's suite, and a provider change must pass them.

### K-QUALITY-7 · major · omission
- Target: XC.DX.samples (developer-experience-docs), ARCH.ORG.integration (program-orchestration), BLD.CI.gating, configurations in skills.json
- Finding: Cross-skill integration testing has no owner. The only integration suite in the map is the sample ladder, and it is owned by the documentation skill ("doubling as integration tests"). A docs agent optimizes samples for readability, not for fault coverage. Two more gaps:
  - Nobody owns building and testing each of the 9 named configurations in CI. check.py proves closure on paper, but nothing proves that `indie-2d` links and runs without the 3D modules, or that `dedicated-server` runs without the client.
  - Nobody owns failure attribution. When a shared integration test or nightly soak fails, no rule routes it to an owning agent (a "build cop" or ledger lookup), so with parallel agents a red build becomes everyone's and no one's.
- Evidence: With many concurrent committers, attributing failures to culprit changes is a core CI function (Google TAP culprit finding; Chromium's sheriff rotation). Here the committers are agents, and there is no human sheriff to fall back on.
- Proposed change:
  - Add `QA.STRAT.integration`: cross-skill integration suites and per-configuration build/boot/test matrix, one CI lane per `configurations` entry. Owner test-architect, contributor ci-cd-automation.
  - Make XC.DX.samples a contributor to QA.STRAT.integration, not the integration-test owner.
  - Add `ARCH.ORG.triage`: failure attribution, bisection, routing to the owning agent via the ledger, and a revert-first policy. Owner program-orchestration, contributors ci-cd-automation, perf-benchmarking.

### K-QUALITY-8 · major · omission
- Target: CORE.ECS.scheduling (ecs-runtime), CORE.JOBS.graph (job-system-task-graph), RND.GRAPH.declare / RND.GRAPH.barriers (render-graph-scheduling), CORE.FRAME.phases
- Finding: The central architectural default is dependency-driven execution from *declared* access: ECS access-conflict analysis, task-graph dependencies, render-graph-derived barriers. Nothing validates that the declared access matches the actual access. An agent that under-declares access produces a data race or a missing barrier that works on its test machine and fails on other core counts or GPUs. General TSan (QA.ROBUST.concurrency) cannot see logical-access violations on ECS chunks, GPU resource hazards, or phase violations.
- Evidence:
  - Unity's job safety system (AtomicSafetyHandle / NativeContainer checks) exists precisely to catch undeclared access in debug builds, and Bevy has system-order ambiguity detection.
  - Vulkan Synchronization Validation and D3D12 GPU-Based Validation catch hazards that hand-declared or graph-derived barriers miss. RND.RHI/QA.RENDER.api-validation turns API validation layers on in CI, but checking the graph's own declared-vs-actual access is a different job.
  - Frostbite's FrameGraph (O'Donnell, GDC 2017) relies on declared reads and writes.
- Proposed change: Add:
  - `CORE.ECS.safety`: debug-build declared-vs-actual component and resource access checking, plus system-order ambiguity detection. Owner ecs-runtime.
  - `CORE.JOBS.safety`: dependency-race detection and schedule-perturbation hooks. Owner job-system-task-graph, contributor robustness-fuzzing.
  - `RND.GRAPH.validation`: render-graph access validation against executed commands, plus hazard checking via sync-validation layers. Owner render-graph-scheduling, contributor render-validation.
  - A `frame-orchestration` capability for phase-violation detection (writing to data owned by another phase).

### K-QUALITY-9 · major · omission
- Target: determinism-replay (XC.DET.*), math-simd-numerics (CORE.MATH.deterministic), physics-2d (PHY.2D.determinism), ci-cd-automation
- Finding: Determinism is a declared level per subsystem, and the crosscutting obligation says "declare… how it is tested". Nobody owns the *conformance infrastructure* that proves a declared level: the same scenario run across compilers, optimization levels, ISAs (x64 AVX2/AVX-512 vs ARM NEON), platforms, core counts and thread schedules, with state hashes compared per tick in CI. XC.DET.desync is the runtime hashing mechanism, not the test matrix. Without it, "cross-platform deterministic" is a claim nobody verifies, and the lockstep, rollback and replay configurations fail in the field.
- Evidence: Box2D v3 runs a cross-platform determinism hash test in CI. Factorio's developer blogs describe desync hunting with a heavy-mode determinism checker. The usual root causes (FMA contraction, compiler differences in transcendentals, x87 remnants, differences between SIMD widths) show up only in a cross-toolchain matrix.
- Proposed change: Add `XC.DET.conformance`: a determinism conformance matrix (toolchain × ISA × platform × core count × schedule perturbation) with per-tick state-hash comparison as a CI gate for every subsystem that declares same-binary or cross-platform determinism. Owner determinism-replay, contributors ci-cd-automation, test-architect, robustness-fuzzing.

### K-QUALITY-10 · major · omission
- Target: rhi-core, audio-architect, input-devices-haptics / input-system, platform-online-services, frame-orchestration, QA.FUNC.automation
- Finding: Nothing requires the external-dependency seams that headless, deterministic CI needs, and nobody owns them:
  - a null or software GPU device for headless render tests (WARP, lavapipe or SwiftShader class);
  - an offline, faster-than-real-time, bit-exact audio render mode and a null audio device;
  - virtual input device injection for bots (QA.FUNC.automation needs it, but the input skills have no capability for it);
  - platform and online service emulators or test doubles, since CI cannot call real platform services and needs to inject outages;
  - a controllable test clock in the frame and time domains.
  Without these, every test agent builds its own ad-hoc stubs inside other skills' territory, which is exactly the overlap that non-responsibilities are meant to prevent.
- Evidence: Chromium and ANGLE run GPU tests on SwiftShader in CI, and Mesa lavapipe is used for Vulkan CI. Wwise and FMOD both provide offline or non-realtime output modes for automated tests. Console SDKs ship service emulation and "network conditioner" tools because cert tests require outage behavior.
- Proposed change: Add:
  - `RND.RHI.software-device` (owner rhi-core);
  - `AUD.ARCH.offline-render` (owner audio-architect);
  - `INP.DEV.injection` (owner input-devices-haptics, contributor functional-automation-soak);
  - `PLAT.SVC.emulation`: service test doubles and fault/outage injection (owner platform-online-services, contributor robustness-fuzzing);
  - `CORE.FRAME.test-clock` (owner frame-orchestration).
  Add an obligation to crosscutting.json: "testability: declare the test seam each external dependency uses" (owner test-architect).

### K-QUALITY-11 · major · missing-contract
- Target: C-TRUST, XC.SEC.trust, QA.ROBUST.fuzzing, skills.json (no per-skill untrusted-input data)
- Finding: C-TRUST is a universal process contract ("untrusted inputs list"), but the list lives nowhere in the data, so the checker cannot verify that every trust boundary has an owner, a validation contract and a fuzz target. The fuzz scope in QA.ROBUST.fuzzing lists only "assets, packets, saves, scripts, mods". These real untrusted inputs are missing:
  - replay and demo files shared by players (NET.REP.replays, XC.DET.replay);
  - remote config and feature flags pushed from servers (PLAT.SVC.remote-config);
  - chat and player-entered text through shaping and bidi (UI.TXT.*);
  - fonts and emoji from UGC or the system;
  - image, audio and video decoders reached from UGC or crossplay avatars;
  - decompressors (RES.PKG.compression, RES.IO.gpu-decompress);
  - cloud saves arriving from another platform;
  - invites, deep links and URL/protocol handlers;
  - UGC material, shader and VFX graphs (GPU hangs and TDR DoS);
  - LLM output (GAM.AI.llm).
  Save *integrity* (tamper and exploit resistance, not only parse safety) has no owner, and save exploits are a platform-security and cert concern on consoles.
- Evidence: Minecraft Log4Shell (CVE-2021-44228) was triggered by a chat message. CVE-2021-30481 was a Source engine RCE through a Steam game invite and server content. libwebp CVE-2023-4863 and FreeType CVE-2025-27363 were decoder and font bugs exploited in the wild. Console save-game exploits have been a recurring jailbreak vector, from the Wii Twilight Hack onward.
- Proposed change:
  - Add an `untrusted_inputs` field to skills.json (for example: replication → packets; persistence-save → saves; text-fonts → fonts, text; platform-online-services → remote-config, invites).
  - Add `check.py` rules: every listed input names a validating owner and has a `QA.ROBUST.fuzzing` target, and every skill that lists one consumes C-TRUST explicitly.
  - Add `GAM.SAVE.integrity`: save signing and tamper policy. Owner persistence-save, contributor security-engineering.
  - Add `RND.SHADER.untrusted`: GPU-DoS limits for UGC-authored graphs. Owner shader-system, contributor modding-ugc.
  - Extend QA.ROBUST.fuzzing's scope text to the full register.

### K-QUALITY-12 · major · omission
- Target: security-engineering (XC.SEC.*), packaging-release-patching, api-lifecycle-migration (XC.EXT.lts)
- Finding: No capability owns vulnerability handling and incident response for the engine or for games shipped on it. Missing pieces:
  - a security intake and disclosure policy (a PSIRT, CVE assignment, coordinated disclosure, optionally bug bounty);
  - severity triage and embargo handling;
  - security backports to LTS branches;
  - an emergency patch path that reaches *already shipped* titles, and customer notification;
  - live-incident runbooks for online games (credential leak, exploit in the wild, economy breach).
  An engine is shared infrastructure, so one runtime bug is a fleet-wide vulnerability.
- Evidence: Unity CVE-2025-59489 (disclosed October 2025) affected Unity runtime builds going back to 2017. Remediation needed an engine patch, a binary patcher for already-built games, re-releases by studios, and platform-side mitigations from Valve and Microsoft. That is exactly the process the framework does not cover.
- Proposed change: Add:
  - `XC.SEC.vuln-response`: PSIRT intake, CVE and disclosure, severity SLAs, and a patch path for shipped titles. Owner security-engineering, contributors packaging-release-patching, api-lifecycle-migration, build-release-architect.
  - `XC.SEC.incident`: live incident response runbooks for online titles. Owner security-engineering, contributors platform-online-services, anti-cheat-integrity.
  - An `XC.EXT.lts` link that makes security backports a named LTS obligation.

### K-QUALITY-13 · major · omission
- Target: XC.SEC.coding, CORE.LIFE.language, build-system-toolchains, memory-allocators
- Finding: Memory safety appears only as a "policy" line (XC.SEC.coding). No capability owns exploit mitigations and hardened build modes. Missing:
  - control-flow integrity and shadow stacks (CET/CFG);
  - hardened standard-library modes (libc++ hardening, `_GLIBCXX_ASSERTIONS`);
  - bounds-safety;
  - memory tagging (ARM MTE on Android; Apple Memory Integrity Enforcement on 2025 iPhones) and pointer authentication (PAC);
  - allocator hardening (a tagged, hardened allocator for the untrusted-input path);
  - a hardened shipping configuration.
  Separately, capability names bake in C++: CORE.LIFE.language "(C++20/23…)", CORE.JOBS.fibers "C++20 coroutines", XC.ITER.live-coding "C++ live coding". That contradicts 00 §9, which says language is an ADR, and it leaves no explicit decision point for memory-safe languages (Rust class, Wasm-sandboxed parsers) at the untrusted-input boundaries.
- Evidence: CISA, NSA and partners' "The Case for Memory Safe Roadmaps" (Dec 2023) and CISA's 2025 guidance ask vendors for exactly such roadmaps. Android reports that memory-safety bugs fell below 20% of vulnerabilities after adopting Rust for new code (Google Security Blog, 2024). Chromium ships MiraclePtr and a hardened libc++ in production.
- Proposed change: Add `XC.SEC.hardening`: exploit-mitigation and hardened-build matrix per platform. Owner security-engineering, contributors build-system-toolchains, memory-allocators.
  Rename the three capabilities to be language-neutral:
  - CORE.LIFE.language → "implementation language(s) & compiler feature policy";
  - CORE.JOBS.fibers → "fibers & language coroutines";
  - XC.ITER.live-coding → "native-code live coding".
  Add to XC.SEC.coding an explicit ADR question: "memory-safe implementation for untrusted-input parsers and sandboxes".

### K-QUALITY-14 · major · omission
- Target: plugin-system (XC.EXT.plugins), editor-architect (ED.ARCH.extension), asset-import-interchange, XC.SEC.sandbox
- Finding: The sandbox policy covers mods and UGC (the player side) only. The developer-side trust boundary has no owner:
  - editor plugins and marketplace packages;
  - Python-class editor tool scripting (ED.ARCH.extension);
  - opening an untrusted project, which can auto-run code;
  - DCC files imported from third-party sources (the FBX SDK and image importers run on artists' and build machines).
  These inputs run with developer and CI credentials, which can include signing keys and devkit access. Plugin "isolation" appears only in plugin-system's purpose text, with no capability behind it.
- Evidence: VS Code added Workspace Trust because opening a folder could execute code. Blender disables auto-running Python in .blend files by default for the same reason. The Autodesk FBX SDK has had several memory-corruption CVEs (for example CVE-2023-27909/27910/27911). Malicious packages in developer ecosystems (npm, PyPI, Open VSX, 2024–2025) are a routine supply-chain vector.
- Proposed change: Add `XC.SEC.dev-trust`: project and workspace trust, plugin signing and permission manifests, and sandboxed import of untrusted source assets. Owner security-engineering, contributors plugin-system, editor-architect, asset-import-interchange. Add `XC.EXT.plugin-trust`: signature and permission fields in the C-PLUGIN manifest. Owner plugin-system.

### K-QUALITY-15 · major · omission
- Target: program-orchestration, ci-cd-automation, XC.SEC.secrets, XC.SEC.supply-chain, BLD.REL.packaging
- Finding: The engine is built by autonomous agents, but the threat model does not include the agents. Nobody owns:
  - agent least privilege (which agent can reach signing keys, platform and devkit credentials, release channels, network egress);
  - agent sandboxing;
  - prompt injection through repository content, third-party docs, issue text or assets the agents read;
  - provenance attestation of agent-authored commits (which agent, model and prompt produced a change);
  - a hard human or multi-party gate on release signing.
  XC.SEC.secrets is generic secrets management. Platform signing keys and devkit credentials in particular need custody separate from any implementing agent.
- Evidence: The OWASP Top 10 for LLM Applications (2025) ranks prompt injection (LLM01) first. Invariant Labs (May 2025) showed a GitHub MCP agent exfiltrating private-repo data through an injected issue. SLSA provenance levels require build and authorship attestation that an agent pipeline has to produce deliberately.
- Proposed change: Add:
  - `XC.SEC.agent-boundary`: agent capability scoping, sandboxing, egress policy and prompt-injection threat model for the development agents. Owner security-engineering, contributors program-orchestration, ci-cd-automation.
  - `XC.SEC.key-custody`: platform signing keys, devkit credentials, release-signing ceremony, no agent-held keys. Owner security-engineering, contributors packaging-release-patching, platform-console.
  - `ARCH.ORG.provenance`: per-change agent/model/task attestation in the ledger. Owner program-orchestration.

### K-QUALITY-16 · major · omission
- Target: GAM.AI.llm (ai-behavior-perception), ED.AI.generative (ai-assisted-authoring), certification-compliance
- Finding: The map contains LLM-driven NPC dialogue and behavior (GAM.AI.llm) and editor copilots (ED.AI.generative), with no threat model or validation obligation for them. Missing:
  - player-supplied prompt injection;
  - unbounded or unsafe generated output against age rating and moderation (QA.CERT.ratings assumes fixed content);
  - data exfiltration through tool-calling NPCs;
  - cost and latency DoS on inference backends;
  - privacy of player utterances sent to a model;
  - non-deterministic output colliding with replay, lockstep and certification.
- Evidence: The OWASP LLM Top 10 (2025) covers LLM01 prompt injection, LLM05 improper output handling and LLM10 unbounded consumption. Age-rating bodies rate fixed content, and dynamically generated dialogue is the reason several platforms now ask about generative AI disclosure at submission (Steam's AI content disclosure rules, from 2024).
- Proposed change: Add `XC.SEC.genai`: generative-feature threat model, output moderation boundary and prompt-injection defenses. Owner security-engineering, contributors ai-behavior-perception, ai-assisted-authoring, platform-online-services (moderation). Add `QA.CERT.genai`: rating and platform-disclosure compliance for runtime-generated content. Owner certification-compliance.

### K-QUALITY-17 · major · omission
- Target: network-transport (NET.TRANS.*), dedicated-server, security-engineering
- Finding: Transport owns encryption and authentication, but nobody owns denial-of-service resilience of internet-exposed game servers and relays. Missing:
  - UDP reflection and amplification limits in the handshake;
  - stateless connect tokens and cookies against connection floods;
  - per-address rate limits;
  - protection against slow-client resource exhaustion;
  - behavior under volumetric attack at the fleet boundary.
  An unauthenticated UDP handshake that answers with more bytes than it received makes every server an amplifier.
- Evidence: QUIC (RFC 9000 §8.1) caps an unvalidated server at 3× the received bytes. DTLS uses HelloVerifyRequest cookies (RFC 6347 §4.2.1). netcode.io uses connect tokens for the same purpose. Game servers have historically been used as amplification vectors (Steam/Source A2S query reflection).
- Proposed change: Add `NET.TRANS.dos`: anti-amplification handshake, stateless challenge tokens, rate limiting and flood behavior. Owner network-transport, contributors security-engineering, dedicated-server. Add it to the robustness-fuzzing fault-injection scope (flood and slowloris soak in QA.FUNC.load).

### K-QUALITY-18 · major · omission
- Target: crash-diagnostics (OBS.CRASH.*), observability-telemetry (OBS.LOG.consent), XC.SEC.privacy, QA.CERT.privacy
- Finding: Crash dumps and logs are the largest uncontrolled flow of player data, and nobody owns scrubbing, retention or data-subject handling for them. Minidumps with heap memory contain auth tokens, chat text, usernames in paths and IPs, and logs carry the same. Privacy is spread over three capabilities (consent in observability, engineering in security, law in certification), and none covers PII and secret scrubbing of diagnostics, retention limits, or deletion and export requests (GDPR Art. 15/17), including for children's data.
- Evidence: Crashpad and Breakpad annotations, and commercial crash services (Sentry, Backtrace), ship server-side and client-side scrubbing because dumps routinely capture credentials. GDPR Art. 5(1)(e) (storage limitation) and Art. 17 apply to diagnostic data tied to an account.
- Proposed change: Add `OBS.CRASH.privacy`: client-side redaction of secrets and PII in dumps and logs, annotation allow-lists, and retention. Owner crash-diagnostics, contributors security-engineering, observability-telemetry. Add `XC.SEC.data-rights`: data inventory, retention and data-subject request flow across telemetry, crash, save and UGC data. Owner security-engineering, contributor certification-compliance.

### K-QUALITY-19 · minor · scale-down
- Target: anti-cheat-integrity (profiles: online), XC.SEC.server-validation, PLAT.SVC.achievements, PLAT.SVC.entitlements
- Finding: Anti-cheat and integrity are gated on the `online` add-on. Single-player titles in every base configuration still submit leaderboard scores, achievements and entitlement checks through C-SVC, and those need score-plausibility validation and client-integrity signals. With no integrity owner, a `standard-3d` configuration has leaderboards that are trivially forgeable.
- Evidence: Offline speedrun and score leaderboards are routinely polluted by memory-edited submissions. Platform leaderboard APIs expect the title to validate submissions.
- Proposed change: Add `XC.SEC.score-integrity`: leaderboard and achievement submission validation. Owner anti-cheat-integrity. Change anti-cheat-integrity's profiles to `["all"]`, keeping XC.SEC.server-validation and XC.SEC.anticheat reachable only through `online` (or split the offline part into the new capability, with the skill tagged `all` and its online-only capabilities documented as optional).

### K-QUALITY-20 · minor · omission
- Target: security-engineering, robustness-fuzzing, BLD.SYS.static-analysis
- Finding: Security *testing* beyond fuzzing has no owner. Missing: penetration testing and protocol red-teaming of servers and online flows, secret scanning of repositories and build artifacts, and verification that shipped packages are stripped (no dev consoles, cheat commands such as ED.DEBUG.console, or debug symbols in shipping). robustness-fuzzing disclaims the threat model, and security-engineering disclaims fuzzing, so pen testing and shipping-build audits fall between them.
- Evidence: Leftover debug consoles and cheat commands in shipped builds are a recurring exploit and cert issue. Leaked symbols and debug builds speed up cheat development.
- Proposed change: Add `XC.SEC.testing`: pen test and red-team program, secret scanning, and shipping-build hardening audit (debug features stripped per BLD.SYS.configs). Owner security-engineering, contributors robustness-fuzzing, ci-cd-automation, visual-debugging-tools.
