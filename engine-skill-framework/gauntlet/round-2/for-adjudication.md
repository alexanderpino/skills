# Round 2 — findings for independent adjudication

Each entry: the critic's finding verbatim, then the builder's disposition. Rule on whether the disposition resolves the material problem (uphold) or not (overturn), judging against the current `data/` and docs.

---

### K-ARCH-14 · major · wrong-boundary
- Target: non-responsibilities of network-architect, dedicated-server, network-transport, water-ocean, navigation-pathfinding; purposes of spatial-audio-acoustics, build-release-architect
- Finding: Several non-responsibility routes and purposes contradict the capability owners. Agents route work by NR, so these send change requests to the wrong skill:
  - `network-architect` sends "Matchmaking services" to `platform-services`, but `PLAT.SVC.matchmaking` is owned by `online-services-liveops`.
  - `dedicated-server` sends "Fleet operation" to `platform-services`, and `NET.SRV.orchestration` lists `platform-services` as contributor. Fleet hosting is third-party or own backend (`online-services-liveops` / `external:backend`), not first-party.
  - `network-transport` sends "Relay service operation" to `platform-services`. It should go to `online-services-liveops` or `external:backend`.
  - `water-ocean` sends "Buoyancy dynamics" to `character-physics`, but `PHY.DYN.buoyancy` is owned by `rigid-body-dynamics`. `WLD.ENV.buoyancy` (a water query service) also lists `character-physics` as contributor.
  - `navigation-pathfinding` sends "Crowd avoidance" to `crowd-simulation`, but it owns `GAM.AI.local-avoidance` (ORCA/RVO) itself, and `crowd-simulation`'s purpose also claims "crowd avoidance". This is a real overlap hidden by wording.
  - `spatial-audio-acoustics`' purpose starts "Panning and distance", but `AUD.DSP.panning` is owned by `audio-dsp-mixing`.
  - `build-release-architect`'s purpose claims "orchestration of the code → content → package pipeline", but `BLD.CI.orchestration` is owned by `ci-cd-automation`.
- Evidence: See the listed data. 00 §1 says non-responsibilities exist to "prevent overlapping agents". The gate checks only that NR targets exist, not that they own the named work.
- Proposed change: Retarget the three platform-services NRs to `online-services-liveops` or `external:backend`. Set the water-ocean NR to `rigid-body-dynamics` and the `WLD.ENV.buoyancy` contributor to `rigid-body-dynamics` (rename the cap id to `water-queries`). Remove "crowd avoidance" from crowd-simulation's purpose and state "local avoidance → navigation-pathfinding; flow-field/mass avoidance → crowd-simulation". Drop "Panning and distance" from spatial-audio's purpose. Reword build-release-architect's purpose to "pipeline architecture (execution by ci-cd-automation)". Add a gate lint: an NR target must own or contribute to at least one capability whose name shares a keyword with the NR text, flagged for review.

**Disposition:** partial — All listed routes and purposes corrected. The proposed keyword lint on non-responsibility text is rejected as unreliable; the authoring, legacy-stance and oracle rules cover the structural part. — -cap PHY.FLUID.shallow; ~cap WLD.ENV.water-interaction: name='Interactive shallow-water / heightfield water simulation (local surface waves, wakes, flooding)'; water-ocean non-responsibilities rewritten

---

### K-ARCH-17 · minor · wrong-boundary
- Target: modding-ugc and plugin-system (parent api-lifecycle-migration), anti-cheat-integrity (parent security-engineering)
- Finding: Runtime experts are parented under process cross-cutting skills whose workstream differs from their own. `modding-ugc` is in workstream gameplay under the governance skill, and `anti-cheat-integrity` is in workstream online under quality. 00 §2 says intra-subtree disputes are settled by the subtree's lead. That puts VFS, scripting and packaging disputes of modding-ugc before an API-versioning policy skill, and anti-cheat versus replication disputes before a threat-model skill. Neither has the runtime coupling to decide them. `plugin-system` is coupled to C-MOD (core-runtime-architect), not to versioning.
- Proposed change: Reparent `plugin-system` to `core-runtime-architect`, `modding-ugc` to `gameplay-architect` (or `content-pipeline-architect`), and `anti-cheat-integrity` to `network-architect`. Keep api-lifecycle-migration and security-engineering as reviewing contributors.

**Disposition:** partial — plugin-system and modding-ugc reparented. anti-cheat-integrity stays under security-engineering: it also owns offline score integrity, attestation and privacy-sensitive client code; networking reaches it through C-INTEGRITY. — ~skill plugin-system: parent; ~skill modding-ugc: parent

---

### K-COMPLETE-4 · major · omission
- Sweep: 3 (RTS/4X, roguelikes, MOBA, tactics), 4 (anti-maphack)
- Target: GAM / NET.REP; new capability owned by crowd-simulation or ai-behavior-perception (contributors replication, render-2d-vector, anti-cheat-integrity)
- Finding: There is no per-team visibility / fog-of-war / line-of-sight field-of-view computation. `GAM.AI.perception` is NPC sensing. It is not a shared per-faction visibility grid that drives rendering (fog overlay), minimap, AI knowledge and replication relevancy. Servers must withhold units a team cannot see, which is the core anti-maphack measure.
- Evidence: The rts-2d-massim and rts-3d-massim configurations exist and have no owner for this. It spans four or more domains (render, net interest, AI, UI, anti-cheat, lockstep determinism), so it meets §C's engine-scope test. It is a staple of StarCraft/AoE/Dota-class engines and a standard roguelike FOV algorithm.
- Proposed change: `GAM.AI.team-visibility` "Per-faction visibility fields & line-of-sight/FOV computation (grid/hex/navmesh), deterministic, feeding render fog, AI knowledge and C-REP relevancy" (owner crowd-simulation; contributors replication, anti-cheat-integrity, render-2d-vector).

**Disposition:** partial — Added as GAM.AI.team-visibility under ai-behavior-perception (merged with K-GAMEPLAY-12) instead of crowd-simulation, which exists only in openworld/massim. — +cap GAM.AI.team-visibility 'Per-faction visibility fields & line-of-sight/FOV (grid/hex/navmesh, GPU variant), explored state, deterministic, feeding fog rendering, AI knowledge and replication relevancy' → ai-behavior-perception [E]; +cap GAM.SYS.markers 'POI/marker registry shared by gameplay, UI and map rendering' → gameplay-systems-toolkit [E]

---

### K-FUTURE-1 · major · maturity-error
- Target: RND.GRAPH.work-graphs, RND.RHI.gpu-work, radar "Work graphs & mesh nodes", seed-map brief_hardware "work graphs or equivalent execution models"
- Finding: `RND.GRAPH.work-graphs` is labelled **E** in capabilities.json. The radar entry that lists it is class **X**, with the evidence "no shipped titles". `docs/06` A6 says "almost no shipped-title postmortems … adopt behind a capability tier with an indirect fallback". `RND.RHI.gpu-work` (E) bundles three things with different maturity: established indirect/ExecuteIndirect, emerging device-generated commands, and experimental work-graph programs. Because the owning capability says E, a phase-2 render-graph-scheduling agent would treat work graphs as a production baseline. It could then freeze C-RG/C-RHI around them, even though principle §7 promises that work graphs remain "an optional part of C-RG".
- Evidence: D3D12 Work Graphs 1.0 shipped in 2024 and mesh nodes are still preview. There is no Vulkan KHR equivalent (only vendor AMDX), and no Metal equivalent. No shipped title has published a work-graph postmortem. The radar's own revisit trigger ("≥2 APIs + one shipped-title postmortem") has not fired.
- Proposed change: Relabel `RND.GRAPH.work-graphs` to X. Split `RND.RHI.gpu-work` into `RND.RHI.indirect` (E: indirect draw/dispatch, multi-draw-indirect-count), `RND.RHI.dgc` (M: VK_EXT_device_generated_commands / D3D12 ExecuteIndirect state changes) and `RND.RHI.work-graphs` (X), and put the last two on the radar. Add a check.py rule: every capability listed in a radar entry must carry that entry's class (see K-FUTURE-11).

**Disposition:** seed/partial — Seed S13; residual accepted (work-graph programs split out as X, radar class = maturity rule). Device-generated commands stay inside the established RND.RHI.gpu-work: ExecuteIndirect state changes and VK_EXT_device_generated_commands are shipped, cross-vendor APIs.

---

### K-FUTURE-7 · major · scale-down
- Target: ml-inference-runtime (profiles ["lite3d","std3d"], parent gpu-platform-architect, workstream rendering, milestone M5)
- Finding: The ML runtime cannot exist in `minimal` or `min2d` configurations. Yet its consumers are in profile `all`: ai-behavior-perception (LLM NPCs), audio-content-runtime (runtime TTS/ASR), and accessibility (TTS/STT). Narrative, card and 2D games are exactly the genres most likely to adopt LLM dialogue and neural TTS. In those configurations the framework allows only remote inference through C-LIVE, which rules out offline or on-device play. The skill is parented under the GPU platform lead and the rendering workstream, but it owns CPU and NPU backends and its main non-rendering consumers are audio, AI and gameplay. Arbitration of its budget would therefore sit with a lead whose remit is GPUs.
- Evidence: skills.json shows ml-inference-runtime profiles as ["lite3d","std3d"]. ai-behavior-perception and audio-content-runtime are ["all"] and consume `C-ML?`. The C-ML contract itself is layer 2 and requires only C-TASK and C-MEM, with no GPU dependency.
- Proposed change: Set the ml-inference-runtime profiles to ["all"]. Keep C-MLGPU gated by a GPU tier, not by the base profile. Reparent the skill under core-runtime-architect or engine-architect (workstream foundation), and keep gpu-platform-architect as the arbiter only for C-MLGPU. Add a configuration such as `narrative-llm-client` (minimal + on-device ML, platforms pc and mobile) to prove the path closes.

**Disposition:** partial — ml-inference-runtime is now profile 'all' under core-runtime-architect; the extra narrative-llm configuration is not added because minimal-client now contains the ML runtime and proves the path. — ~skill ml-inference-runtime: parent, profiles, workstream; ml-inference-runtime non-responsibility += GPU queue/budget arbitration of C-MLGPU work → gpu-platform-architect

---

### K-GAMEPLAY-2 · major · missing-contract
- Target: gameplay-systems-toolkit, crowd-simulation, cinematics-sequencer, C-GAME, C-ANIM, ai-behavior-perception, gameplay-architect
- Finding: three gameplay-facing experts provide no contract, and the lead contract they would sit behind does not describe their surface. `C-GAME` covers only "module entry points, rules/session state, control binding, scheduled systems, extension hooks". Abilities/effects/attributes, gameplay tags, spawning, volumes/markers and hit resolution (gameplay-systems-toolkit), crowd spawn/query/LOD (crowd-simulation), and sequence playback/binding/event tracks (cinematics-sequencer, whose `C-ANIM` covers only pose output) all have no contract. So:
  - AI cannot activate abilities or query tags. Behavior-tree tasks and state-tree conditions on tags and abilities are the standard pattern.
  - UI view-models cannot bind attributes.
  - Narrative conditions cannot test tags.
  - Game code cannot start or bind a cutscene or receive its events.
  - Nothing can drive a crowd.
  
  Under the "contracts, never internals" rule (00 §3), the only way to reach these surfaces is through internals.
- Evidence: UE GameplayAbilities and GameplayTags are consumed by AI (StateTree and BT tag decorators), UI (attribute binding) and animation. UE Mass exposes crowd spawning and queries through processors and subsystems. Level Sequence exposes a player/binding API to gameplay. None of this is internal-only.
- Proposed change: add `C-ABILITY` (L4, owner gameplay-systems-toolkit: abilities, effects, attributes, tag queries, messages, hit results), `C-CROWD` (L4, owner crowd-simulation: agent spawn/despawn, batched queries, LOD and tier hooks) and `C-SEQ` (L3, owner cinematics-sequencer: sequence playback, actor binding, event and track callbacks, skip/blend policy). Wire consumers: ai-behavior-perception → `C-ABILITY?`; gameplay-architect → `C-SEQ?`, `C-CROWD?`; narrative-dialogue conditions → tags via `C-GAMEDATA` or a new L3 `C-TAGS`. Tags must live at L3 if narrative (L3) is to read them.

**Disposition:** partial — C-ABILITY, C-CROWD and C-SEQ added; tags are exposed through C-GAMEDATA instead of a new C-TAGS contract. — +contract C-ABILITY L4 (gameplay-systems-toolkit): Abilities, effects & attributes; +contract C-CROWD L4 (crowd-simulation): Crowds & mass agents; +contract C-SEQ L4 (cinematics-sequencer): Sequences

---

### K-GAMEPLAY-3 · major · missing-contract
- Target: C-AIAGENT, ai-behavior-perception, C-MOVE, navigation-pathfinding (GAM.AI.following), crowd-simulation, character-movement
- Finding: `C-AIAGENT` is described as "optional decision providers (learned policies, LLM agents)". The established AI surface has no contract: behavior/state-tree assignment, perception stimulus registration (noise, sight sources that gameplay must emit), smart-object claim/release, and EQS-style queries. Movement is also broken. Nav owns "path following & steering" at L3, but it cannot consume `C-MOVE` (L4), and `ai-behavior-perception` does not consume `C-MOVE` either. So the framework has no path from a computed path to character locomotion: the only `C-MOVE` consumer is motion-synthesis. NPC locomotion through the same predicted and reconciled movement API as players (GAM.MOVE.networked) is therefore unreachable.
- Evidence: UE's AIController → PathFollowingComponent → CharacterMovement `RequestDirectMove`. Mass/StateTree smart-object claims. Perception stimuli are registered by gameplay objects (UE `AIPerceptionStimuliSource`). All of these are cross-skill surfaces.
- Proposed change: rename `C-AIAGENT` to "AI agents & decision providers" and extend it with brain assignment, stimulus sources, smart-object claims, query service, and the optional learned/LLM providers as one sub-part. Add `C-MOVE` to ai-behavior-perception `consumes` (optional in the minimal profile). State in the `C-NAV` summary that nav produces path corridors and steering intents and does not move bodies, and that the consumer converts intents to `C-MOVE` requests.

**Disposition:** partial — Established AI surface added as a new contract C-AI; C-AIAGENT stays the gated optional extension point for learned/LLM providers instead of being renamed. — +contract C-AI L4 (ai-behavior-perception): AI agents; gameplay-architect consumes += C-AI?; gameplay-systems-toolkit consumes += C-AI?

---

### K-GAMEPLAY-5 · major · overlap
- Target: GAM.SAVE.settings, CORE.LIFE.config (C-CFG "user" source), C-SAVE, C-A11YRT (settings), input-system, accessibility, runtime-scalability
- Finding: player settings have two homes. `C-CFG` has a "user" configuration layer owned by core-runtime-architect. `GAM.SAVE.settings` (persistence-save) owns "player settings/options model, scopes (device/user/cloud) & first-boot availability". `C-A11YRT` separately owns "accessibility settings and change events". The `C-SAVE` summary does not mention settings. None of the three contributors to GAM.SAVE.settings (input-system for bindings, accessibility, runtime-scalability for graphics) consume `C-SAVE`, so none of them can register a setting. The result will be three persistence paths for options, with different precedence and different first-boot behavior.
- Evidence: console certification requires settings to survive user switches and to be available before sign-in (the XR/TRC user-profile rules). Lyra's shared-vs-local settings split shows the usual pattern: one settings registry that feeds the config layer.
- Proposed change: make persistence-save the single owner of the persisted player-settings store and add "settings registry (per scope)" to the `C-SAVE` summary, or add a separate `C-SETTINGS` (L3). Make the `C-CFG` user layer a read-only projection that this store populates. `C-A11YRT` settings register there. Add `C-SAVE` (or `C-SETTINGS`) to `consumes` of input-system, accessibility and runtime-scalability.

**Disposition:** partial — One settings mechanism: settings are declared as scoped C-CFG entries and persisted by persistence-save into the C-CFG user layer. No new C-SETTINGS: runtime-scalability (L1) cannot consume C-SAVE (L3). — ~contract C-CFG: summary; ~contract C-SAVE: summary; ~contract C-A11YRT: summary

---

### K-GAMEPLAY-12 · major · omission
- Target: capability map GAM/UI/RND; configs rts-2d-massim-client, rts-3d-massim-client, open-world-client
- Finding: no capability covers fog of war / team visibility, or maps (minimap, world map, compass, POI/marker registry). Both are staples of the RTS and open-world configurations the framework names. Fog of war spans gameplay (per-team vision computation, often on the GPU), rendering (fog overlay, explored state), replication (visibility-driven relevancy and anti-maphack, where lockstep is inherently vulnerable) and AI perception. Maps need a marker registry that gameplay, UI (UI.FW.world-ui) and render (map capture/tiles) share. Without an owner, each reference game will reinvent them across four skills.
- Evidence: StarCraft II and AoE IV fog/vision systems. Valorant's fog-of-war server-side visibility for anti-wallhack (Riot tech blog, 2020). The open-world map and marker systems in Ubisoft and Guerrilla titles.
- Proposed change: add `GAM.SYS.visibility` "Team visibility / fog of war (grid & GPU variants), explored state, visibility-driven relevancy hook" (owner gameplay-systems-toolkit; contributors replication, render-2d-vector, ai-behavior-perception; profile massim) and `GAM.SYS.markers` "POI/marker registry, minimap and world-map data" (owner gameplay-systems-toolkit; contributors ui-architect, render-architect). Add `C-REP` relevancy hook consumption for the visibility item.

**Disposition:** partial — Team visibility owned by ai-behavior-perception (all profiles; roguelikes need it) instead of the toolkit; markers in the toolkit and the map service in ui-architect. — +cap GAM.AI.team-visibility 'Per-faction visibility fields & line-of-sight/FOV (grid/hex/navmesh, GPU variant), explored state, deterministic, feeding fog rendering, AI knowledge and replication relevancy' → ai-behavior-perception [E]; +cap GAM.SYS.markers 'POI/marker registry shared by gameplay, UI and map rendering' → gameplay-systems-toolkit [E]

---

### K-LEGACY-7 · major · wrong-boundary
- Target: CORE.ECS.baking (ecs-runtime), WLD.PART.cook, WLD.PART.hlod (world-architect), RND.ARCH.editor-rendering (render-architect), L23, check.py tool-side rule
- Finding: Four cook-side or editor-side capabilities are owned by runtime skills whose `tool_consumes` is empty. The cook steps never consume C-COOK, and editor rendering never reaches C-EDHOST. So nothing places that code in a tools-only module, and it defaults into the skill's runtime module. That module ships in the client and server targets, which is the L23 editor-in-runtime monolith, and it also contradicts the "format owner vs pipeline host through C-COOK" pattern in §4. The check.py guarantee ("tool-logic owners reach the editor through contracts") covers only `*.TOOL.*` capability ids, so cook and editor-rendering territory escapes it.
- Evidence: `ecs-runtime`, `world-architect` and `render-architect` all have `tool_consumes = []`, and `render-architect` targets `client` and `tools`. UE's historic WITH_EDITOR/WITH_EDITORONLY_DATA sprawl is the production example of editor code bleeding into runtime modules when module placement is not enforced.
- Proposed change: Add `tool_consumes: ["C-COOK"]` to `ecs-runtime` and `world-architect`, and `["C-EDHOST"]` to `render-architect`. Add a per-capability `side: runtime|tool` attribute, or derive it from the id pattern (cook, bake, build, editor, TOOL). Extend check.py so that every tool-side capability's owner consumes a tool contract, and so that tool-side modules never appear in the client or server closure.

**Disposition:** partial — Tool contracts added and enforced for cook/bake/editor territory; the tool side is derived from capability wording instead of a new per-capability 'side' field. — ~skill geometry-pipeline: expertise; K-RENDER check qualified per tier; ecs-runtime tool_consumes += C-COOK

---

### K-LEGACY-12 · major · scale-down
- Target: WLD.PART.grid, WLD.PART.sources, WLD.PART.activation, WLD.PART.hlod, WLD.PART.sim-tiers, WLD.PART.server (no profile tags); world-architect (profiles: all); L18
- Finding: Every WLD.PART capability is untagged, so cell streaming, HLOD orchestration, off-bubble simulation tiers and server-side world streaming are all in the `minimal` (card/UI game) and `min2d` closures. L18's stance ("cell streaming with budgeted activation") is written as universal. That is new dogma (L27): for a 2D platformer or a card game, one asynchronously loaded, non-blocking world unit is the correct design, and the legacy part of level-as-a-file is *blocking* the load, not having one file.
- Evidence: The capability-level profile tags exist precisely for this (for example VSM and cluster LOD are `std3d`), but they are not applied to world partitioning. Many shipped 2D and indie games use per-scene async loads well.
- Proposed change: Tag WLD.PART.grid, sources, hlod, sim-tiers and server as `openworld` (keep `lite3d`/`std3d` where useful). Add `WLD.MODEL.unit-load` ("async non-blocking whole-unit load with loading-screen hand-off"), E, for minimal and min2d. Reword L18 to "Blocking whole-level load before play; default: async non-blocking loading; cell streaming for openworld".

**Disposition:** partial — Grid/sources/HLOD tagged lite3d+std3d (linear 3D games stream too), server streaming openworld, simulation tiers openworld+massim; WLD.MODEL.unit-load added for minimal/2D. — ~cap WLD.PART.grid: profiles=['lite3d', 'std3d']; ~cap WLD.PART.sources: profiles=['lite3d', 'std3d']; ~cap WLD.PART.hlod: profiles=['lite3d', 'std3d']

---

### K-NET-8 · major · overlap
- Target: NET.ARCH.validation (network-architect), QA.SIM.netsim (simulation-validation), QA.FUNC.network (functional-automation-soak), NET.TRANS.simulation
- Finding: Four capabilities overlap on "deterministic network simulation, harnesses and correctness metrics", with no stated split. The netcode **oracle suite** is owned by the lead of the skills it judges. That contradicts the framework's own rule ("Implementers must not control the oracles that judge them", QA.AGENT.*; docs/00 §8).
- Evidence: It is the same class of self-grading risk that the framework removed for rendering (render-validation) and simulation (simulation-validation).
- Proposed change: Merge NET.ARCH.validation into QA.SIM.netsim, owned by simulation-validation, with contributors network-architect (acceptance thresholds), replication and prediction-rollback. Keep NET.TRANS.simulation as the link-conditioner mechanism only. Rename QA.FUNC.network to "Multi-client bot harness & scripted network sessions".

**Disposition:** partial — Boundaries of the four capabilities made explicit (scenarios, runner, bot harness, link conditioner); scenario definitions stay with network-architect but every change needs simulation-validation co-signature (QA.AGENT.oracle-change-control) instead of moving the oracle. — ~cap NET.ARCH.validation: name='Netcode oracle scenarios & acceptance thresholds (co-signed by simulation-validation per QA.AGENT.oracle-change-control)', +contrib simulation-validation; ~cap QA.SIM.netsim: name='Deterministic single-process network-simulation runner, metrics & tolerance store'; ~cap QA.FUNC.network: name='Multi-client bot harness & scripted network sessions'

---

### K-NET-19 · minor · maturity-error
- Target: NET.ARCH.meshing, radar.json, docs/06 A5
- Finding: (a) The labels disagree: docs/06 A5 says "Keep [server meshing] as `emerging`", while capabilities.json and radar.json classify it X. (b) The radar has no networking entries beyond meshing and QUIC. Missing are: the kernel-mode anti-cheat trajectory (Microsoft's 2025 Windows Resiliency Initiative moving security vendors out of kernel mode, and Proton/Steam Deck incompatibility), which directly affects XC.SEC.anticheat; server-side ML cheat detection (M); L4S low-latency congestion signalling (RFC 9330–9332, X); and Media-over-QUIC for spectator and broadcast streams (X).
- Evidence: As cited in each item.
- Proposed change: Change the A5 text to "keep experimental". Add radar entries with owners anti-cheat-integrity (kernel AC trajectory, ML detection), network-transport (L4S) and replication (MoQ spectator), each with a fallback.

**Disposition:** partial — Radar entries added (L4S, MoQ, behavioral detection, user-mode anti-cheat). Server meshing is aligned to M rather than X in data, radar and A5, because a live deployment exists. — +cap NET.TRANS.l4s 'L4S low-latency congestion signalling' → network-transport [X]; +cap NET.REP.moq-spectator 'Media-over-QUIC spectator/broadcast streams' → replication [X]; +cap XC.SEC.behavioral-detection 'Server-side behavioral / ML cheat detection from telemetry' → anti-cheat-integrity [M]

---

### K-PLATFORM-3 · major · missing-contract
- Target: C-PAL, platform-architect, platform-desktop, platform-mobile, platform-web, platform-console, ARCH.STRUCT.platform-backends, PLAT.PAL.*
- Finding: the "registered platform backend slot" rule exists only as prose (C-PAL summary; ARCH.STRUCT.platform-backends). C-PAL has no `needs_implementer`, and every per-platform skill *consumes* C-PAL instead of implementing it. As a result, the lead `platform-architect` owns the per-OS implementation of all 24 PAL capabilities (windowing, threads, clocks, display, power, permissions, HTTP/TLS, fs-watch). The OS experts (`platform-desktop` "Windows/Linux/SteamOS/macOS integration", `platform-mobile` "iOS/Android integration") own overlapping integration territory, and nothing says who writes Win32 windowing versus who writes the PAL windowing interface. Two agents will both write that code.
- Evidence: contracts.json C-PAL (no `needs_implementer`); skills.json `consumes: ["C-PAL"]` on all four platform skills; PLAT.PAL.windowing/display/power are owned by platform-architect while PLAT.DESK.os-integration and PLAT.MOB.os are owned by the experts. C-RHI already uses the correct owner/implementer pattern, and C-PAL should follow it.
- Proposed change: mark C-PAL `needs_implementer: true`. Make platform-desktop, platform-console, platform-mobile, platform-web and a server-host implementer (K-PLATFORM-4) `implements: ["C-PAL"]`. Relabel the PLAT.PAL.* capabilities as "interface & policy" owned by platform-architect, and add per-platform "PAL implementation" capabilities to each expert. Add a `slots` list on ARCH.STRUCT.platform-backends in data (RHI, IO, audio endpoint, device input, sockets, crash, save storage, service SDK, IME/a11y bridge) with the interface owner for each. The per-platform rule from K-PLATFORM-2 then proves each configuration has a PAL backend per platform.

**Disposition:** partial — C-PAL now needs a per-platform implementer and the platform experts implement it; the per-platform closure check proves one backend per platform. A separate 'slots' data field is not added: ARCH.STRUCT.platform-backends keeps the slot list. — ~contract C-PAL: needs_implementer; ~contract C-PAL: summary; +cap PLAT.DESK.pal 'PAL implementation for Windows/Linux/SteamOS/macOS (C-PAL backend: OS services, windowing, threads, clocks, IO, display, power, events)' → platform-desktop [E]

---

### K-PLATFORM-6 · major · omission
- Target: platform-console, async-io-storage (RES.IO.backends "console APIs", RES.IO.hw-decompress), audio-architect (AUD.ARCH.devices), persistence-save (GAM.SAVE.platform), crash-diagnostics, text-fonts (UI.TXT.ime), PLAT.PAL.confidential-extensions, C-ORCH access classes
- Finding: NDA access is per platform holder (Sony, Microsoft and Nintendo agreements are separate, and a contractor licensed for one may not see another). The framework has one `platform-console` agent spanning every holder. Registered-slot implementations that touch confidential SDKs (console IO and decompression units, audio endpoints, save storage, crash upload, IME/system keyboard, entitlement SDKs) are owned by domain skills that have no access class. The C-ORCH ledger has "access classes", but no skill or capability declares one, so program-orchestration cannot route NDA work or keep it away from uncleared agents.
- Evidence: capabilities listed above; skills.json has no access/confidentiality field; PLAT.PAL.confidential-extensions describes the mechanism but nothing binds to it. docs/06 §"Parameters behind NDAs" admits console content cannot be filled yet, but the *structure* (who may touch it) must exist before phase 2.
- Proposed change: add `access_class` to skills (`public` | `nda:<holder>`) and a `confidential_slots` list on capabilities. Split `platform-console` into `platform-console-<holder>` experts (or a parameterized template skill instantiated per holder) under a console lead. For each slot, have the domain skill own the public interface and stub, and have the holder skill implement the confidential variant. Add a check.py rule that no `public` skill owns a capability marked `nda:*`.

**Disposition:** partial — NDA access class added and enforced; console skills are instantiated per platform holder ('instances' field) instead of duplicated per holder in the data; confidential slot implementations consolidated in PLAT.CON.confidential-slots instead of a per-capability field. — ~skill platform-console: access, instances; +cap PLAT.CON.confidential-slots 'Confidential implementations of registered slots (IO/decompression units, audio endpoints, save storage, crash upload, system keyboard, entitlement SDK) behind public interfaces owned by domain skills' → platform-console [E]; ~contract C-ORCH: summary

---

### K-PLATFORM-12 · minor · wrong-boundary
- Target: platform-mobile, platform-console (targets), platform-web (targets)
- Finding: `platform-mobile` and `platform-console` list targets `headless-client` and `server`, and `platform-web` lists `tools`. No mobile/console server or web-hosted tools exist in any configuration. The tags would pull these modules into a hypothetical console server build and blur what "server-host" means.
- Evidence: skills.json targets.
- Proposed change: `platform-mobile.targets = ["client"]`, `platform-console.targets = ["client"]` (plus tools-side modules via K-PLATFORM-7), `platform-web.targets = ["client"]`.

**Disposition:** partial — headless-client/server targets removed; the tools target is kept because the platform skills now implement C-TARGETPLAT tool modules (K-PLATFORM-7). — ~skill platform-mobile: targets; ~skill platform-console: targets; ~skill platform-web: targets

---

### K-PROD-3 · major · omission
- Target: reference-games, QA.REF.ladder, QA.REF.content, QA.REF.dogfood
- Finding: The reference-game ladder is one reference game per configuration (22 configurations), up to an AAA open-world online slice with production-scale content. It is both the milestone gate and the release gate. It is owned by one *process* expert with no build targets, no write set for game code and no content-acquisition capability.
  - Nobody owns building the reference games' game code: it is excluded as `external:*` game content everywhere else.
  - Nobody owns acquiring or generating production-scale content (licensed marketplace packs, scan libraries, procedural or synthetic content, with rights through CNT.ID.rights).
  - Nobody owns keeping those games alive across engine versions.
  
  This is the largest single production effort in the program, and it is modelled as a three-capability expert.
- Evidence: Every engine vendor staffs its dogfood content as full game teams: Epic's Fortnite and The Matrix Awakens/Valley of the Ancient, Unity's Demo Team (Enemies, The Heretic, Megacity), EA SEED's PICA PICA, Frostbite's first-party titles. Megacity-scale content alone took a dedicated team. Agents writing reference-game code are also the first real consumers of the public API (C-API). That is exactly the dogfooding the ladder is supposed to provide.
- Proposed change: Promote reference-games to a lead of a new `reference-production` workstream with runtime/tool kind and targets. Add experts, or at minimum capabilities:
  - `QA.REF.game-code`: reference-game gameplay code written only against public API. It is a build skill in each reference configuration.
  - `QA.REF.content-acquisition`: licensed, purchased, scanned, procedural and generated content sets with a rights manifest. Contributors: CNT.ID.rights, procedural-generation, ai-assisted-authoring.
  - `QA.REF.upkeep`: migrating reference games on every engine release, feeding ARCH.PROD.customer-corpus.
  
  Add reference-game content milestones to milestones.json.

**Disposition:** partial — reference-games becomes a build skill with game-code, content-acquisition and upkeep capabilities; it is not promoted to a lead with a new workstream (one agent per reference configuration is a staffing decision under ARCH.ORG.staffing). — ~skill reference-games: kind, targets, consumes, purpose; +cap QA.REF.game-code 'Reference-game gameplay code written only against the public API (a build skill in each reference configuration)' → reference-games [E]; +cap QA.REF.content-acquisition 'Licensed, purchased, scanned, procedural and generated reference content with a rights manifest' → reference-games [E]

---

### K-PROD-7 · major · other
- Target: data/milestones.json, ARCH.ORG.milestones, QA.STRAT.release-criteria, certification-compliance, packaging-release-patching, api-lifecycle-migration
- Finding: The ladder stops at "AAA reference slice" (M5). It has no engine-as-product or ship-lifecycle milestones:
  - No first title passing *console certification* or store review. Console appears only at M2 as "runs on one console tier", and the only cert criterion is "pre-checks for online features" at M4, even though indie-2d-client targets console, mobile and web.
  - No milestone exercises patch, DLC, rollback or staged rollout on a shipped reference game.
  - No engine alpha, beta, 1.0 or LTS release with a tested upgrade path over the customer corpus.
  - No live-ops rehearsal and no end-of-service rehearsal.
  
  Separately, M1 adds 44 skills at once (76 build skills by M1): editor, graph editors, cinematics, media, AI, navigation, narrative and platform services. It is a big-bang integration labelled "vertical slice".
- Evidence: Late platform bring-up is the most common cause of AAA port crunch. Engines such as id Tech and Decima bring consoles up with the core. The cert/TRC failure loop typically takes 2–6 weeks per submission, and it must be rehearsed before any external team depends on it. Vertical slice practice (thin, full-depth path) comes from Keith, *Agile Game Development*, and Chandler, *The Game Production Handbook*.
- Proposed change:
  - Split M1 into M1a (playable 2D runtime on pc) and M1b (editor/tools, localization, accessibility, services).
  - Bring platform-console and platform-mobile bring-up into M1b, with a TRC/store-review dry run of the indie-2d reference game in its exit.
  - Add M4 exit items: patch plus DLC plus staged rollout plus rollback executed on the online reference game.
  - Add M6 "Engine 1.0 / first LTS": customer-corpus upgrade from the previous release, release notes, backport stream open, console cert pass of at least one reference game.
  - Add a live-ops/end-of-service rehearsal milestone.
  - Record milestone exit ownership as test-architect evidence plus a human gate.

**Disposition:** partial — Ladder rebuilt M0–M7 (runtime-on-PC vs all platforms + tools, patch/DLC/rollback at M4, engine 1.0/LTS at M7). M1 still adds 44 skills because its claimed configuration requires them (check.py proves it); live-ops and end-of-service rehearsal folded into M7. — milestone ladder rebuilt: M0–M7, configurations claimed per milestone, skills placed by closure, contract freezes derived (110 code contracts); leftovers placed late: []; check.py: milestone configuration closure, full-claim coverage, contract freeze order, gates exist

---

### K-SEC-14 · minor · omission
- Target: C-IPC ("dev-only port security"), PLAT.PAL.devlink, OBS.LOG.remote, ED.ARCH.remote, ED.DEBUG.console, XC.ITER.live-coding, ED.ARCH.agent-api, XC.SEC.testing, BLD.SYS.configs
- Finding: Dev-only remote and code-loading surfaces (devlink, remote diagnostics, remote live editing, console and cheat commands, live coding, automation API, script debugger over DAP) are spread over six owners. The only shipping safeguard is an after-the-fact "shipping-build hardening audit" (XC.SEC.testing). No build-time mechanism ensures that shipping configurations contain none of them, such as a declared dev-surface manifest checked by a fitness function. Where they must exist in shipping, such as a server remote console, nothing requires authentication.
- Proposed change: Add BLD.SYS.dev-surface-exclusion (owner build-system-toolchains, contributors security-engineering, architecture-governance): every skill declares its dev surfaces in data, and the shipping configuration is verified by fitness function and binary scan to contain none. Any surface allowed in shipping must be authenticated through C-IPC.

**Disposition:** partial — Dev surfaces declared on their owning skills and an exclusion capability with fitness function and binary scan added; the scan is that capability's deliverable, not a check.py rule. — +cap BLD.SYS.dev-surface-exclusion 'Dev-surface manifest per skill, fitness function and binary scan proving shipping configurations contain none; allowed shipping surfaces authenticated via C-IPC' → build-system-toolchains [E]; ~skill visual-debugging-tools: dev_surfaces; ~skill hot-reload-iteration: dev_surfaces

---

### K-SIM-1 · major · obsolete-assumption
- Target: CORE.FRAME.pipelining (frame-orchestration), legacy-patterns L03, C-FRAME
- Finding: The capability that defines how simulation, render and GPU work overlap is worded "Frame pipelining with a dedicated game thread and a dedicated render thread". That is the pattern the framework itself lists as legacy L03 ("Game-thread / render-thread dichotomy … render work as tasks; dedicated threads only by ADR"), and it contradicts 00-design-principles ("The frame is a task graph"). The simulation schedule (CORE.FRAME.sim-schedule, PHY.ARCH.stepping, PHY.ARCH.async) sits on top of this capability. An agent implementing frame-orchestration from this label would build a two-thread engine and put physics, animation and gameplay on "the game thread" by default.
- Evidence: Destiny's task-graph frame (Tatarchuk/Genova, GDC 2015 "Multithreading the Entire Destiny Engine"). Naughty Dog's fiber job system (Gyrich, GDC 2015 "Parallelizing the Naughty Dog Engine Using Fibers") has no dedicated game or render thread. Frostbite's frame graph (O'Donnell, GDC 2017). The framework's own L03 and the task-graph principle.
- Proposed change: Rename CORE.FRAME.pipelining to "Frame pipelining across simulation, render-build and GPU stages expressed as overlapping task-graph frames; any dedicated thread only by ADR (L03)". Add a check.py rule that no capability name matches a legacy-pattern detection string without an ADR reference.

**Disposition:** seed/partial — Seed S12. The proposed rule (capability names must not match legacy detection strings) is replaced by a stronger one: every legacy pattern names the capabilities that carry its modern stance, and check.py verifies them (r2_y).

---

### K-SIM-3 · major · scale-down
- Target: fluid-simulation.profiles, PHY.FLUID.*, capability map (no cellular/2D fluid capability)
- Finding: Fluids are gated on `aaa`, a production-scale add-on, not a feature. As a result, no min2d, lite3d or plain std3d configuration can include any fluid solver. There is also no capability at all for the fluid and material simulation class that defines whole 2D and sandbox genres: cellular automata or falling sand, grid-based liquids and gases, and heat or pressure diffusion.
- Evidence: Noita (per-pixel falling-sand simulation, GDC 2019 "Exploring the Tech and Design of Noita"), Oxygen Not Included (gas/liquid/heat grid), Terraria liquids, Dwarf Fortress fluids. None of these are AAA; all are min2d- or sandbox-scale. The framework's own principle, "not every configuration needs every subsystem", argues for gating on features, not budget.
- Proposed change: Change fluid-simulation.profiles to ["min2d","lite3d","std3d"], included on demand (or gate it on `sandbox`/`massim` in addition to `aaa`). Add PHY.FLUID.cellular "Grid/cellular material & fluid simulation (falling-sand, liquid/gas/heat grids), 2D-capable, deterministic" (E) owned by fluid-simulation, with contributor physics-2d. Add a configuration or reference game that exercises it (e.g. extend indie-2d-client or add a 2D sandbox configuration).

**Disposition:** partial — Cellular/falling-sand fluids added and a min2d+sandbox configuration proves them. fluid-simulation is gated on the sandbox/massim/aaa add-ons rather than every base profile, because profile membership means 'available in every such build'. — ~skill fluid-simulation: profiles; +cap PHY.FLUID.cellular 'Grid/cellular material & fluid simulation (falling sand, liquid/gas/heat grids), 2D-capable, deterministic' → fluid-simulation [E]; configuration sandbox-2d-client (min2d + sandbox) added

---

### K-SYSTEMS-3 · major · dependency-error
- Target: C-FRAME, C-FLOW, audio-architect, spatial-transforms, scripting-runtime, navigation-pathfinding, ai-behavior-perception, ui-architect, ml-inference-runtime, prediction-rollback, replication
- Finding: The central stance says ordering is derived from declared reads and writes (C-FRAME) and that runtime data moves through channels (C-FLOW). But only **one** skill (render-architect) consumes C-FLOW. Several runtime skills whose work must be ordered or handed across rates declare neither C-FRAME nor a required C-ECS:
  - audio-architect: a real-time audio thread, plus a game→audio command channel and an audio→game clock.
  - spatial-transforms: its own contract promises "per-phase change sets".
  - scripting-runtime: "per-worker VMs, deferred mutation" (L22).
  - navigation-pathfinding and ai-behavior-perception: asynchronous path and perception queries spanning frames.
  - ui-architect: its own update and layout phase.
  - ml-inference-runtime: "scheduling within frame budgets".
  - prediction-rollback: resimulation of N ticks.
  With the dependency undeclared, each agent will invent its own queues, double-buffers and threads. The derived-ordering model then cannot see these accesses, so races and implicit ordering come back silently.
- Evidence: Frame and task-graph schedulers are only as sound as their declarations. Bevy's ambiguity detector and Unity's job safety system can only flag accesses they know about. Audio is the classic undeclared cross-rate channel: the Wwise and FMOD command queues feed a real-time mixer thread.
- Proposed change:
  - Add C-FRAME to consumes for audio-architect, spatial-transforms, scripting-runtime, navigation-pathfinding, ai-behavior-perception, ui-architect, ml-inference-runtime and prediction-rollback.
  - Add C-FLOW to consumes for audio-architect, physics-architect, animation-architect, network-architect/replication, ai-behavior-perception and input-system; these are the multi-rate producers and consumers.
  - Add a check.py rule: every runtime skill at L3 or above whose capabilities schedule per-frame work must consume C-FRAME (or C-ECS non-optionally).

**Disposition:** partial — Explicit C-FRAME/C-FLOW edges added to the eight multi-rate skills. The proposed check.py rule is rejected: 'schedules per-frame work' is not decidable from the data without a new per-capability field, and C-FRAME is consumed by every skill that registers phase work. — audio-architect consumes += C-FRAME; spatial-transforms consumes += C-FRAME; scripting-runtime consumes += C-FRAME

---

### K-TEST-2 · major · overlap
- Target: QA.SIM.stability-suite / PHY.ARCH.validation; QA.SIM.animation / ANM.ARCH.validation; QA.SIM.audio / AUD.ARCH.validation; QA.SIM.netsim / NET.ARCH.validation / QA.FUNC.network / NET.TRANS.simulation; simulation-validation
- Finding: The same suites have two owners under nearly identical names. For example, "Audio oracle suite: bit-exact offline render, loudness, glitch & latency" is owned by audio-architect, while "Audio offline-render, loudness & glitch suites" is owned by simulation-validation. Animation, physics stability and net simulation follow the same pattern. The "define vs run" split exists only in simulation-validation's prose. "Running" a suite is CI (ci-cd-automation), so simulation-validation owns no distinct artifact, and both agents will write the same test sources. Network testing is split four ways with no stated boundary: NET.ARCH.validation, QA.SIM.netsim, QA.FUNC.network ("Network test harnesses") and NET.TRANS.simulation (link simulation). simulation-validation also consumes no contracts (C-PHYS, C-ANIM, C-AUDIO, C-NET, C-REPLAY), although it runs suites against all of them. Its non-responsibility points to `owning-skill`, which is not a real owner.
- Evidence: Compare render-validation. It owns distinct artifacts (image metrics, per-GPU tolerance tables, the comparison harness), and material-system's furnace tests are named as the input it runs. The QA.SIM caps have no equivalent distinct artifact.
- Proposed change: Rename the QA.SIM caps to the artifacts simulation-validation actually uniquely owns: the metric library (pose error, loudness per ITU-R BS.1770, penetration/energy drift), the tolerance/baseline store, the cross-platform comparison harness and the result dashboards. Keep scene and scenario definitions in the *.ARCH.validation caps. Make the boundaries explicit: QA.FUNC.network = multi-process bot harness; QA.SIM.netsim = deterministic single-process net simulation; NET.TRANS.simulation = the link-conditioner seam. Add consumes `C-PHYS, C-ANIM, C-AUDIO, C-NET?, C-REPLAY`. Replace `owning-skill` with explicit owners.

**Disposition:** partial — QA.SIM capabilities renamed to the artifacts simulation-validation uniquely owns and its contract access added; scenario definitions stay in the domain *.ARCH.validation capabilities with co-signature. — ~cap NET.ARCH.validation: name='Netcode oracle scenarios & acceptance thresholds (co-signed by simulation-validation per QA.AGENT.oracle-change-control)', +contrib simulation-validation; ~cap QA.SIM.netsim: name='Deterministic single-process network-simulation runner, metrics & tolerance store'; ~cap QA.FUNC.network: name='Multi-client bot harness & scripted network sessions'

---

### K-TOOLS-8 · major · missing-contract
- Target: C-EDCMD/C-EDHOST/C-GRAPH (L5, tool-only), modding-ugc, XC.EXT.mod-sdk, XC.EXT.ugc, GAM.SYS.building, RND.SHADER.untrusted
- Finding: All edit, undo and graph authoring infrastructure is L5 tool-only, and check.py forbids runtime code from consuming it. In-game creation tools (UGC level editors of the Roblox/Dreams/Mario Maker/Fortnite Creative class, player construction, photo-mode editing, in-client graph authoring for the UGC shaders `RND.SHADER.untrusted` already anticipates) must ship in client builds. They have no owner for runtime-side edit transactions, undo or selection, and no runtime graph-compile path. separately, `modding-ugc` has `tool_consumes: []`. `XC.EXT.mod-sdk` ("Mod SDK & tooling") escapes check.py's tool-logic rule because it is not named `.TOOL`. No capability covers producing a redistributable modder editor (stripping NDA console backends, middleware SDK licences and internal plugins, per BLD.REL.engine-distribution being engine-user oriented).
- Evidence: The Creation Kit, Source SDK, UEFN and Roblox Studio all ship an editor to end users. Dreams, Mario Maker and Fortnite Creative ship authoring inside the client. The `ugc` profile exists, but its authoring path is undefined.
- Proposed change: Add `C-EDIT` (L4, owner gameplay-architect or a new owner designated by editor-architect): "Runtime edit session: serializable commands, undo, selection, permissions and budgets for in-game creation". Make `C-EDCMD` a tool-side extension of it so commands are shared. Add `XC.EXT.mod-editor` ("Redistributable modder editor/SDK build: licence/NDA stripping, sandboxed tool plugins", owner modding-ugc, contributors packaging-release-patching, platform-architect, security-engineering, profile ugc). Give modding-ugc `tool_consumes: [C-EDCMD, C-EDHOST, C-COOK]`, and extend check.py's rule to capabilities whose name denotes tooling (`mod-sdk`).

**Disposition:** partial — Runtime edit sessions (C-EDIT) owned by modding-ugc, which owns in-game creation; the command schema is shared through ED.ARCH.transactions instead of C-EDCMD extending C-EDIT, so the editor has no dependency on the UGC runtime. The 'mod-sdk' name rule is replaced by the general tool-side rule. — +contract C-EDIT L4 (modding-ugc): Runtime edit session; +cap XC.EXT.player-creation 'Player-facing in-game creation mode (runtime editing subset, gamepad/touch placement, budgets, undo, publish/versioning) in client targets' → modding-ugc [E]; +cap XC.EXT.ugc-discovery 'UGC browse/rate/play boundary with moderation & entitlement hooks' → modding-ugc [E]

