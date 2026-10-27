# K-COMPLETE · Completeness Critic · Round 2

Scope: only omissions from the capability map (1145 capabilities, 143 skills). Before reporting anything, I searched capability ids and names, skill purposes and expertise, contracts and seed-map terms. No whole domain is missing, so there are no blockers. The map is unusually complete across engine modules, pipeline, platform/legal and disciplines. The items below are what remains. docs/06 §C (game-specific systems are game code; backend is out of scope) was applied. Where I argue against it, I use the doc's own test: formats shared across four or more engine domains.

### K-COMPLETE-1 · major · omission
- Sweep: 1 (UE5 Mutable/Customizable Object, Frostbite and RE Engine character creators), 3 (MMO, RPG, sports, UGC-avatar platforms)
- Target: ANM/RND.CHAR/CNT; owner deformation-skinning (contributors character-rendering, material-system, animation-runtime, persistence-save, replication)
- Finding: There is no runtime character customization or modular character assembly. Missing pieces: modular part swapping, skeletal-mesh merging, morph/bone-driven body sliders, runtime texture/material compositing and baking, and a customization descriptor that is saved, replicated and streamed. Runtime retargeting onto variable proportions appears only in the animation-runtime purpose. There is no capability for it; only `ANM.TOOL.retarget-editor` exists.
- Evidence: This passes the §C test for engine-owned formats. The descriptor touches rendering (draw-call and material merging), animation (retarget, shared skeletons), streaming (part assets), save, replication and UGC. UE ships Mutable as an engine plugin for this reason. Without it, the aaa-open-world-online and ugc configurations have no owner for avatar data.
- Proposed change: `ANM.DEF.modular-assembly` "Modular character assembly, mesh merging & runtime material/texture baking" (owner deformation-skinning; contributors character-rendering, material-system). `ANM.RT.runtime-retarget` "Runtime retargeting onto variable skeleton proportions" (owner animation-runtime). `GAM.FW.customization-descriptor` "Character customization descriptor with save/replication/stream participation" (owner gameplay-architect; contributors persistence-save, replication).

### K-COMPLETE-2 · major · omission
- Sweep: 1 (UE5 Motion Warping and Contextual Animation, Decima/RE melee sync kills), 3 (action, fighting throws, sports tackles, stealth takedowns)
- Target: ANM.SYN / ANM.IK; owner motion-synthesis (contributors ik-procedural-animation, character-movement, prediction-rollback)
- Finding: Two capabilities are missing. The first is synchronized multi-actor animation: paired or contextual scenes, alignment, and role assignment for takedowns, grabs, throws, hand-offs and mounts. The second is motion warping, which adjusts root motion to hit a target (vault/mantle alignment, attack magnetism). `GAM.MOVE.transitions` covers only mount state, not the pose alignment.
- Evidence: Every third-person action title uses these. In online games the paired scene must be predicted and replicated as one unit, which crosses animation, movement, net and physics (ragdoll release). A grep for warp, paired, synced and contextual finds nothing.
- Proposed change: `ANM.SYN.motion-warping` "Motion warping of root motion to gameplay targets" (owner motion-synthesis; contributor character-movement). `ANM.SYN.multi-actor` "Synchronized multi-actor animation scenes (paired, contextual; alignment, roles, replication)" (owner motion-synthesis; contributors ik-procedural-animation, prediction-rollback).

### K-COMPLETE-3 · major · omission
- Sweep: 1 (Source 2 VIS, Unity/Umbra occlusion, UE precomputed visibility and software occlusion for mobile, id Tech portals), 3 (indoor shooters, mobile)
- Target: RND.GEO; owner geometry-pipeline
- Finding: The only occlusion culling in the map is GPU two-phase HZB (`RND.GEO.culling`). The CPU-culled tier (`RND.GEO.cpu-submission`, first-class for lite3d/mobile/web) has no occlusion technique: no software-rasterized occluders (masked-occlusion class), no portal/cell visibility, no baked PVS.
- Evidence: A grep for PVS, portal, occluder and "software occlusion" returns nothing. The lite-3d-mobile and xr-standalone configurations, and WebGPU without robust indirect, cannot rely on GPU HZB. Without CPU-side occlusion, dense interiors blow draw-call budgets on exactly the tiers where draws are most expensive.
- Proposed change: `RND.GEO.cpu-occlusion` "CPU occlusion culling for the CPU-submitted tier (software occluder rasterization, portals/cells, optional baked PVS with cook step)" (owner geometry-pipeline; contributors world-data-model, render-architect).

### K-COMPLETE-4 · major · omission
- Sweep: 3 (RTS/4X, roguelikes, MOBA, tactics), 4 (anti-maphack)
- Target: GAM / NET.REP; new capability owned by crowd-simulation or ai-behavior-perception (contributors replication, render-2d-vector, anti-cheat-integrity)
- Finding: There is no per-team visibility / fog-of-war / line-of-sight field-of-view computation. `GAM.AI.perception` is NPC sensing. It is not a shared per-faction visibility grid that drives rendering (fog overlay), minimap, AI knowledge and replication relevancy. Servers must withhold units a team cannot see, which is the core anti-maphack measure.
- Evidence: The rts-2d-massim and rts-3d-massim configurations exist and have no owner for this. It spans four or more domains (render, net interest, AI, UI, anti-cheat, lockstep determinism), so it meets §C's engine-scope test. It is a staple of StarCraft/AoE/Dota-class engines and a standard roguelike FOV algorithm.
- Proposed change: `GAM.AI.team-visibility` "Per-faction visibility fields & line-of-sight/FOV computation (grid/hex/navmesh), deterministic, feeding render fog, AI knowledge and C-REP relevancy" (owner crowd-simulation; contributors replication, anti-cheat-integrity, render-2d-vector).

### K-COMPLETE-5 · major · omission
- Sweep: 3 (party/local multiplayer, LAN RTS/esports, handheld co-op), 4 (Switch local-wireless requirements)
- Target: NET.TRANS; owner network-transport (contributors platform-console, platform-services)
- Finding: There is no local-network play: LAN session discovery (broadcast/mDNS), serverless LAN hosting without online services, or console local-wireless/ad-hoc sessions between nearby handhelds. The transport caps assume internet paths (NAT, relays, IPv6/NAT64).
- Evidence: A grep for LAN, ad-hoc and "local wireless" returns nothing. Portable-console local wireless is a platform-certified feature with its own APIs and constraints. LAN is required by esports venues and offline events, and is expected in PC RTS and survival games. It is also what keeps a game playable after end-of-service (`BLD.REL.end-of-service`).
- Proposed change: `NET.TRANS.local-network` "LAN/local-wireless session discovery & hosting without online services (broadcast/mDNS, console ad-hoc)" (owner network-transport; contributors platform-console, dedicated-server).

### K-COMPLETE-6 · major · omission
- Sweep: 3 (user-created-worlds platforms: Roblox, Fortnite Creative, Dreams, Mario Maker, Minecraft), 1 (UEFN)
- Target: XC.EXT / ED; owner modding-ugc (contributors editor-architect, world-editor-viewport, platform-services, online-services-liveops)
- Finding: UGC in the map is developer-facing: a mod SDK, upload, and a sandbox. There is no player-facing in-game creation mode. Missing: a runtime subset of the editor that ships in client builds on console and mobile, with gamepad and touch placement, undo, a per-creation cost budget ("memory meter"), save/publish/version, and discovery/playback of creations under the moderation boundary.
- Evidence: A grep for in-game editor, creation mode and creator finds nothing. The editor capabilities are tools-target only (kind: tool), so nothing owns creation tooling inside the client target. The ugc addon and the aaa-open-world-online configuration include ugc, and user-created-worlds platforms are an explicit target genre.
- Proposed change: `XC.EXT.player-creation` "Player-facing in-game creation mode (runtime editing subset, budgets, undo, publish/versioning) in client targets" (owner modding-ugc; contributors world-editor-viewport, editor-architect). `XC.EXT.ugc-discovery` "UGC browse/rate/play boundary with moderation & entitlement hooks" (owner modding-ugc; contributor online-services-liveops).

### K-COMPLETE-7 · major · omission
- Sweep: 1 (OpenXR face/body/eye-tracking extensions, Meta Movement SDK), 3 (social VR, VR UGC platforms, VTuber-style avatars)
- Target: PLAT.XR / ANM.IK; owner xr-runtime (contributors ik-procedural-animation, facial-animation, replication)
- Finding: XR input has hands and gaze but no body and face tracking, and no avatar embodiment. Missing: full-body IK from 3-point or partial tracking, tracked facial expressions driving the facial rig, and networked low-bandwidth avatar pose streams. A grep for face/body tracking and avatar finds nothing.
- Evidence: The xr-standalone and xr-pc configurations. Embodied avatars are the core of social XR, and the pose stream needs its own compression and privacy class (facial data is biometric under several privacy regimes).
- Proposed change: `PLAT.XR.body-face` "Body, face & eye-expression tracking inputs (OpenXR extensions) with biometric privacy class" (owner xr-runtime). `ANM.IK.avatar-embodiment` "Full-body avatar IK from sparse tracking & tracked-expression retargeting" (owner ik-procedural-animation; contributors facial-animation, replication).

### K-COMPLETE-8 · minor · omission
- Sweep: 1 (every editor), 5 (HCI)
- Target: ED.ARCH; owner editor-architect
- Finding: Undo/redo and the transaction/command system appear only in the editor-architect purpose and a contract. The seed-map maps "undo/redo" and "command systems" to `ED.ARCH.selection` ("Selection model"), which is a mis-hosting. `ED.ARCH.recovery` covers only the journal.
- Evidence: Undo transactions must be universal across every tool skill (critics.json already demands this), so they need their own capability with conformance tests.
- Proposed change: `ED.ARCH.transactions` "Transaction, undo/redo & command system (universal across tools, multi-user aware)" (owner editor-architect); repoint seed-map.

### K-COMPLETE-9 · minor · omission
- Sweep: 2 (launch/live ops), 4 (platform patch-size rules)
- Target: BLD.REL; owner packaging-release-patching
- Finding: Delta/chunk patching and patch-size minimization are in the skill purpose ("binary diffing") but have no capability. `BLD.REL.dlc` "DLC & content updates" is vague on this.
- Evidence: Patch size is a cert and store concern on consoles and mobile, and a day-one patch requirement. Layout decisions (`RES.PKG.install-layout`) must be tested against patch deltas.
- Proposed change: `BLD.REL.delta-patching` "Delta patch generation, patch-size budgets & layout stability across builds" (owner packaging-release-patching; contributor package-formats-vfs).

### K-COMPLETE-10 · minor · omission
- Sweep: 3 (shooters, military sims, Tarkov/Arma/Battlefield class)
- Target: GAM.SYS; owner gameplay-systems-toolkit (contributors prediction-rollback, collision-detection)
- Finding: There is no projectile/ballistics simulation. Missing: bullet drop, drag, penetration by physics material, ricochet, and networked projectiles (client-predicted spawn, server reconciliation, lag-compensated hit). `GAM.SYS.hit-detection` covers hitboxes and frame data, not flight models.
- Evidence: The online-3d configurations include shooters, and projectile prediction is a distinct, much-published netcode problem.
- Proposed change: `GAM.SYS.projectiles` "Projectile & ballistics simulation with predicted/replicated projectiles" (owner gameplay-systems-toolkit; contributors prediction-rollback, physics-architect).

### K-COMPLETE-11 · minor · omission
- Sweep: 1 (UE planar reflections/scene captures, Portal/Prey/Splitgate), 3 (flight-sim MFDs, horror mirrors, puzzle portals)
- Target: RND.GI / RND.ARCH; owner global-illumination (reflections) and render-architect (portal views)
- Finding: `RND.GI.reflections` lists screen-space, RT and probes only. Planar reflections, the standard answer on lite3d/mobile/XR tiers without RT, are absent. Recursive portal views that carry physics, audio and AI queries through the portal are covered only vaguely by "captures" in `RND.ARCH.multiview`.
- Evidence: On mobile and XR tiers, water and mirrors need planar reflections. Seamless portals also need a transform-through-portal contract for collision, audio and navigation.
- Proposed change: `RND.GI.planar` "Planar reflections (clip-plane re-render, tier-scaled)" (owner global-illumination). `RND.ARCH.portals` "Portal views with recursive rendering and spatial-query transform through portals" (owner render-architect; contributors collision-detection, spatial-audio-acoustics).

### K-COMPLETE-12 · minor · omission
- Sweep: 3 (rhythm games), 1 (UE Quartz, FMOD/Wwise beat callbacks)
- Target: AUD.CONTENT; owner audio-content-runtime
- Finding: There is no sample-accurate musical clock that schedules gameplay and audio events on beats/bars (quantized triggers, beat callbacks into gameplay). `AUD.ARCH.clock` is A/V/input sync, and `music` is adaptive music. The seed-map's "rhythm" term maps only to calibration.
- Evidence: Rhythm games and music-synchronized combat (Hi-Fi Rush class) depend on this, as do quantized music transitions.
- Proposed change: `AUD.CONTENT.music-clock` "Sample-accurate musical clock, quantized scheduling & beat events to gameplay" (owner audio-content-runtime; contributor frame-orchestration).

### K-COMPLETE-13 · minor · omission
- Sweep: 3 (fighting games, action combos, touch-stroke games)
- Target: INP.ACT; owner input-system
- Finding: There is no input-sequence recognition: motion inputs (quarter-circle), charge inputs, combo strings with leniency windows, negative edge, and stroke/gesture recognizers. `INP.ACT.latency` covers only buffering.
- Evidence: Every fighting-game engine has a command interpreter. It must be deterministic for rollback and replay.
- Proposed change: `INP.ACT.sequences` "Deterministic input-sequence & gesture recognition (motion/charge commands, leniency windows)" (owner input-system).

### K-COMPLETE-14 · minor · omission
- Sweep: 3 (card, board, 4X, tactics, puzzle AI)
- Target: GAM.AI; owner ai-behavior-perception
- Finding: `GAM.AI.decisions` enumerates BT/utility/HTN/GOAP/state trees but not game-tree search: minimax/alpha-beta, MCTS, and hidden-information search over a cloneable rules state.
- Evidence: This is the standard AI for the minimal profile (card/board) and for turn-based 4X/tactics. It needs a cheap state-clone/apply-move contract, which ties it to `CORE.ECS.snapshot`.
- Proposed change: `GAM.AI.search` "Game-tree search AI (minimax, MCTS, information-set search) over clonable rule state" (owner ai-behavior-perception).

### K-COMPLETE-15 · minor · omission
- Sweep: 4 (store/business: demos, game trials, subscription trials)
- Target: PLAT.SVC; owner platform-services (contributor packaging-release-patching)
- Finding: There are no trial/demo SKUs: content-stripped demo builds, time-limited trials enforced by entitlement/trusted time, and save carry-over to the full game.
- Evidence: Platform trial programs and storefront demo festivals are routine launch-marketing requirements with platform-defined behaviour.
- Proposed change: `PLAT.SVC.trials` "Demo & time-limited trial SKUs with entitlement gating and save carry-over" (owner platform-services; contributor packaging-release-patching).

### K-COMPLETE-16 · minor · omission
- Sweep: 1 (Unity/UE/Godot desktop), 3 (RTS edge scrolling, PC strategy/sims)
- Target: PLAT.DESK / PLAT.PAL; owner platform-architect
- Finding: Desktop pointer and shell services have no capability: hardware/custom cursors, cursor confinement and relative mode (pointer lock exists only for web), clipboard, native file dialogs, and drag-and-drop. These are hidden at most inside `PLAT.PAL.windowing`.
- Evidence: RTS and sim configurations need confinement across multi-monitor setups. Chat needs clipboard, and tools need dialogs and drag-drop.
- Proposed change: `PLAT.PAL.pointer-shell` "Cursor management (hardware cursors, confinement, relative mode), clipboard, file dialogs, drag-and-drop" (owner platform-architect).

### K-COMPLETE-17 · minor · omission
- Sweep: 3 (party games: Jackbox/AirConsole/PlayLink class; Remote Play Together)
- Target: INP.DEV; owner input-devices-haptics (contributor network-transport, platform-web)
- Finding: There are no companion/second-screen devices as controllers, such as phones joining through a browser or app and acting as input devices with their own UI.
- Evidence: This is a distinct input path (network-latency input device, per-player private screens) used by a whole party-game sub-genre.
- Proposed change: `INP.DEV.companion` "Companion/second-screen devices as networked input devices" (owner input-devices-haptics; contributor network-transport).

### K-COMPLETE-18 · minor · omission
- Sweep: 2 (cinematics/previs content creation), 1 (UE Take Recorder, VCam, Live Link mocap)
- Target: ANM.CINE / CNT.IMP; owner cinematics-sequencer (contributor asset-import-interchange)
- Finding: Live body-mocap streaming into the engine, take recording of gameplay/sequencer state into editable tracks, and virtual camera operation are absent. "Virtual production" appears only in expertise, and facial capture import exists but body capture does not.
- Evidence: Previs and cinematic layout for std3d/aaa rely on recording gameplay into sequences and on hand-held VCam, and these exist in shipped engine toolsets.
- Proposed change: `ANM.CINE.take-recording` "Take recorder, live mocap streaming & virtual camera" (owner cinematics-sequencer; contributor asset-import-interchange).

### K-COMPLETE-19 · minor · omission
- Sweep: 2 (character/environment content creation), 1 (UE Chaos Cloth editor, Mesh Paint mode)
- Target: PHY.TOOL / ED.WORLD; owners cloth-deformables and world-editor-viewport
- Finding: Cloth authoring has no capability: sim-mesh setup, max-distance/weight painting, and preview. Every other simulation has a tool capability. In-editor mesh vertex-color/texture painting is also missing.
- Evidence: Cloth parameters are authored in-engine on every AAA character. Vertex painting is the standard environment-art blend workflow.
- Proposed change: `PHY.TOOL.cloth` "Cloth asset authoring & weight painting" (owner cloth-deformables). `ED.WORLD.mesh-paint` "Mesh vertex-color & texture painting" (owner world-editor-viewport).

### K-COMPLETE-20 · minor · omission
- Sweep: 2 (production management, outsourcing), 4 (IP access control)
- Target: ED.COLLAB; owner collaboration-version-control
- Finding: There is no production-tracking integration (asset/shot status, task-tracker links, ShotGrid/ftrack class) and no scoped access for external vendors (outsourcer workspaces restricted to their content). `PLAT.PAL.confidential-extensions` covers only NDA platform code.
- Evidence: At team-large scale, most art is outsourced, and vendor access control plus status tracking are pipeline requirements.
- Proposed change: `ED.COLLAB.production-tracking` "Production-tracking integration & scoped external-vendor workspaces" (owner collaboration-version-control; contributor security-engineering).

### K-COMPLETE-21 · minor · omission
- Sweep: 3 (mobile F2P live ops, especially Asian markets)
- Target: GAM.SCR; owner scripting-runtime (contributors packaging-release-patching, certification-compliance)
- Finding: Only data hotfixes exist (`GAM.DATA.hotfix`). There is no policy or mechanism for script/logic hotfix delivery (downloaded script patches), the platform-policy boundary on executable content, or signing.
- Evidence: Script hotfixing is common in mobile live ops. Its store-policy limits need a single owner.
- Proposed change: `GAM.SCR.hotfix` "Script/logic hotfix delivery within store policy (signed, versioned, rollback)" (owner scripting-runtime).

### K-COMPLETE-22 · minor · omission
- Sweep: 3 (open world, RTS, survival: minimap/world map)
- Target: UI.FW; owner ui-architect (contributor world-architect)
- Finding: There is no map service: cooked top-down map tiles from the world, marker/POI layers streamed with world cells, and a fog/discovery overlay.
- Evidence: Nearly every open-world and strategy game builds this, and it reuses world-partition cells. Its absence invites per-game reimplementation against the streaming system.
- Proposed change: `UI.FW.maps` "World map/minimap service (cooked map tiles, streamed markers, discovery overlay)" (owner ui-architect; contributor world-architect).

### K-COMPLETE-23 · minor · omission
- Sweep: 5 (numerics), 3 (idle/incremental)
- Target: CORE.MATH; owner math-simd-numerics
- Finding: There is no arbitrary-precision or large-magnitude number type (mantissa-exponent "big number") with formatting through CLDR.
- Evidence: Idle games exceed double range routinely. Formatting and serialization also need a canonical form.
- Proposed change: `CORE.MATH.bignum` "Large-magnitude/arbitrary-precision numeric types with canonical serialization" (owner math-simd-numerics).

### K-COMPLETE-24 · minor · omission
- Sweep: 4 (regional market access), 5 (HCI)
- Target: ED.UI; owner editor-ui-framework (contributor localization-i18n)
- Finding: Localization covers game content only. There is no capability for localizing the editor, tools and error messages, even though `ARCH.PROD.licensing-model` treats the engine as a product for external game teams.
- Evidence: Commercial engines ship localized editors (CJK markets). This needs string extraction across all tool skills.
- Proposed change: `ED.UI.localization` "Editor & tool UI localization" (owner editor-ui-framework; contributor localization-i18n).
