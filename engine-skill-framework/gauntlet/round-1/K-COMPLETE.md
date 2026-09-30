# K-COMPLETE · Completeness Critic · Round 1

Scope: only capabilities or disciplines that are **missing** from `data/capabilities.json` (739 capabilities, 21 domains). For each candidate, the capability ids and names, `skills.json` purposes and non-responsibilities, and all `docs/` were searched first. Anything covered under another name was dropped. Two deliberate scope decisions in `06-gap-analysis.md` §C were taken into account: backend services are outside scope (only integration boundaries are in scope), and game-specific systems count as game code. Findings that go against the second decision explain why the item is engine territory. `check.py`: 0 errors, 2 warnings.

Counts: 1 blocker, 19 major, 9 minor.

---

### K-COMPLETE-1 · blocker · omission
- Sweep: 4 (platform/legal/business)
- Target: PLAT.SVC (platform & online services integration), owner `platform-online-services`
- Finding: There is no monetization or commerce integration boundary. Nothing in data or docs matches IAP, purchase, ads, monetization, virtual currency, receipt or loot-box odds. `PLAT.SVC.entitlements` ("Entitlements, store, DLC ownership") only covers owning DLC. It does not cover consumable purchases, receipt validation, the purchase-flow UI that platforms require, ad-SDK integration (rewarded/interstitial, consent-gated), or legal disclosure of randomized-item odds.
- Evidence: The mission brief names "monetization boundaries (IAP, ads — as integration boundaries)". Every mobile F2P title needs this, and so does every console title with a microtransaction store. Precedents: Unity IAP and Unity Ads/LevelPlay, UE Online Subsystem purchase interfaces (`IOnlinePurchase`, `IOnlineStoreV2`), and the StoreKit 2 and Play Billing requirements. Platform certification also checks commerce flows: first-party store UI must be used, and restore-purchases is mandatory on iOS. Loot-box odds disclosure is law or regulation in China, South Korea and elsewhere. Because this is a whole business domain named in the brief, it is not a missing detail.
- Proposed change: Add area `PLAT.COMM` "Commerce & monetization integration boundary", owner `platform-online-services`:
  - `PLAT.COMM.iap`: Consumable, non-consumable and subscription purchases via first-party stores
  - `PLAT.COMM.receipts`: Receipt/entitlement validation boundary, with server-side validation hand-off. Contributors: `anti-cheat-integrity`, `security-engineering`
  - `PLAT.COMM.currency`: Virtual-currency and wallet integration boundary. The backend stays outside scope.
  - `PLAT.COMM.ads`: Ad-SDK integration boundary: consent, mediation, rewarded-ad callbacks, frame/memory isolation. Contributors: `observability-telemetry` (consent)
  - `PLAT.COMM.disclosure`: Randomized-item odds disclosure and regional spending rules. Contributor: `certification-compliance`

  Also add "monetization boundaries" to `seed-map.json` so the check is machine-enforced.

### K-COMPLETE-2 · major · omission
- Sweep: 1 (UE Media Framework/Bink, Unity VideoPlayer, Godot VideoStreamPlayer) and 2 (cinematics, launch: logo/legal splash screens)
- Target: new area under RND or ANM.CINE, owner `cinematics-sequencer`. Contributors: `audio-dsp-mixing`, `texture-streaming-vt`, `platform-architect`.
- Finding: Nothing covers playing pre-rendered video. Searches for video, FMV, Bink and "media play" find only `ANM.CINE.movie-render`, which *produces* movies. Missing: decoding with hardware decoders (NVDEC, VideoToolbox, MediaCodec, console decoders, AV1/H.265/VP9), audio/video sync, video-to-texture for in-world screens, streaming from packages, and HDR video.
- Evidence: Almost every configuration needs this, indie 2D included: splash and logo screens, pre-rendered cutscenes, tutorial clips, in-world TVs. Every listed shipped engine has a media player. Bink is middleware in most AAA titles, so there is also a build/buy decision to record.
- Proposed change: `ANM.CINE.video`: Video playback (hardware decode, A/V sync, video textures, HDR video, package streaming), owner `cinematics-sequencer`, contributors as above. Add `ARCH.STRUCT.build-buy` coverage for Bink-class middleware.

### K-COMPLETE-3 · major · omission
- Sweep: 5 (networking discipline) and 4 (every online-service boundary)
- Target: NET.TRANS, owner `network-transport`. Contributor: `security-engineering`.
- Finding: There is no HTTP(S), REST, WebSocket or TLS client capability. `NET.TRANS` covers UDP, reliability and QUIC evaluation only. Yet `PLAT.SVC.*`, `OBS.LOG.telemetry`, `OBS.CRASH.pipeline`, `BLD.REL.cdn`, `BLD.REL.on-demand`, remote config and UGC download all need an HTTPS client with a certificate store, pinning, retries, proxies, background downloads, and the platform HTTP stacks that consoles require. There is also no shared cryptographic-primitives capability: `CORE.TYPES.hashing` is non-cryptographic only, and CSPRNG and TLS library selection are unowned.
- Evidence: Precedents: UE `HTTP`/`WebSockets`/`SSL` modules, Unity `UnityWebRequest`, Godot `HTTPRequest`/`WebSocketPeer`. Console certification requires the platform network stack and TLS configuration. The web target (`PLAT.PAL.web`) cannot open UDP at all, so it needs WebSocket or WebTransport.
- Proposed change:
  - `NET.TRANS.http`: HTTP(S)/REST client & background downloads (platform stacks, retries, proxies)
  - `NET.TRANS.websocket`: WebSocket/WebRTC transport for web and service push
  - `XC.SEC.crypto`: Cryptographic primitives, CSPRNG & TLS/certificate policy, owner `security-engineering`

### K-COMPLETE-4 · major · omission
- Sweep: 4 (parental controls, regional rules, certification)
- Target: PLAT.SVC, owner `platform-online-services`. Contributor: `certification-compliance`.
- Finding: Nothing covers parental controls, platform privilege checks or regional play-time rules. There are no hits for parental, privilege, age gate, anti-addiction or block list. Missing: checking platform privileges (multiplayer, UGC, communication, cross-play) before each feature, honoring platform block and mute lists, age-based feature restriction, and regional play-time and spending limits such as China's minor anti-addiction rules. `QA.CERT.privacy` and `QA.CERT.ratings` are compliance tracking. They are not the runtime capability that enforces these rules.
- Evidence: The brief names parental controls and regional rules. Console TRC/XR/Lotcheck-class requirements make privilege and block-list checks mandatory for any online feature. COPPA and the UK Age Appropriate Design Code require age-appropriate defaults.
- Proposed change: `PLAT.SVC.privileges`: Privilege, parental-control & block-list enforcement at feature boundaries. `PLAT.SVC.regional-limits`: Age gating, play-time & spending limits per region. Contributors: `certification-compliance`, `gameplay-architect`.

### K-COMPLETE-5 · major · omission
- Sweep: 3 (party/local and online multiplayer, MMO) and 4 (CVAA)
- Target: PLAT.SVC and NET.TRANS
- Finding: Social and communication features are missing:
  - (a) Social graph: friends, parties, invites, join-in-progress from the platform overlay. Only rich presence and a matchmaking/lobby boundary exist.
  - (b) Voice-chat transport or service. `audio-dsp-mixing` lists "Voice-chat transport → network-transport" as a non-responsibility, but no `NET.TRANS` capability exists for it, so the pointer leads nowhere.
  - (c) Text chat (only its moderation boundary exists).
  - (d) Speech-to-text/text-to-speech of chat for accessibility. `UI.A11Y.screen-reader` covers UI and not player-to-player communication.
- Evidence: Every console multiplayer title must support platform invites and join sessions (certification). CVAA requires communication functionality to be accessible, including chat transcription. Precedents: Vivox (UE/Unity), EOS voice, the platform party-chat APIs.
- Proposed change:
  - `PLAT.SVC.social`: Friends, parties, invites & join-session integration
  - `NET.TRANS.voice`: Voice-chat transport/service integration (P2P vs service, per-channel routing), owner `network-transport`
  - `PLAT.SVC.text-chat`: Text-chat integration boundary
  - `UI.A11Y.comms`: Accessible communications (chat TTS/STT transcription), owner `accessibility`

### K-COMPLETE-6 · major · omission
- Sweep: 3 (AR/MR) and 1 (Unity AR Foundation, UE ARKit/ARCore/OpenXR MR, Meta Presence Platform)
- Target: PLAT.XR, owner `xr-runtime`
- Finding: The XR area covers only VR. There are no capabilities for passthrough compositing, spatial anchors (local and shared), plane and scene-mesh understanding, real-world occlusion (environment depth), light estimation, or phone AR (ARKit/ARCore camera session). Camera-frame input is also absent from INP.
- Evidence: MR headsets (Quest 3 class, Vision Pro class) and mobile AR are shipping platforms. The genre sweep includes AR/MR explicitly. Scene mesh must feed physics and navigation, and light estimation must feed `global-illumination`. These are new cross-domain contracts that no current capability owns.
- Proposed change:
  - `PLAT.XR.passthrough`: Passthrough & MR compositing
  - `PLAT.XR.anchors`: Spatial anchors (persistent, shared)
  - `PLAT.XR.scene`: Scene understanding (planes, scene mesh, environment depth occlusion). Contributors: `collision-detection`, `navigation-pathfinding`.
  - `PLAT.XR.light-estimation`: Real-world light estimation. Contributor: `global-illumination`.
  - `PLAT.XR.mobile-ar`: Phone/tablet AR sessions (ARKit/ARCore class)

  All owned by `xr-runtime`, maturity E/M.

### K-COMPLETE-7 · major · omission
- Sweep: 1 (UE Persona/Skeletal Mesh editor, Physics Asset Editor, Niagara editor, Static Mesh editor, Control Rig; Unity Animation window, Timeline; Source 2 ModelDoc) and 2 (animation, VFX, character content)
- Target: ED domain, with the domain skills as owners
- Finding: Production tooling for most domains stops at runtime plus a shared graph editor. The only domain-specific tool capabilities are `WLD.ENV.terrain-tools`, `UI.FW.authoring`, the world editor and the graph editor framework. Missing asset editors:
  - skeleton/skeletal-mesh/animation-clip editing and preview (sockets, notifies, retarget setup, compression preview)
  - in-engine keyframe or rig-based animation authoring (Control Rig class)
  - physics-asset/ragdoll/collision-setup editor
  - VFX editor. `ED.GRAPH` covers the node graph, not emitter timeline, preview or bounds tooling.
  - static-mesh/LOD/collision setup editor
  - navmesh and nav-agent authoring tools

  The definition of done says "production tooling as thorough as runtime".
- Evidence: All AAA engines ship these as first-class editors, and content teams (animators, technical artists, VFX artists) spend most of their time in them. Without an owner, each runtime agent either builds its own editor inconsistently or builds nothing.
- Proposed change: Add `*.tools` capabilities owned by each domain skill, hosted through `C-EDCMD`/editor-ui-framework:
  - `ANM.TOOLS.asset-editor`: Skeleton/animation asset editor & preview, owner `animation-runtime`
  - `ANM.TOOLS.rig-authoring`: In-engine rig & keyframe authoring (M), owner `ik-procedural-animation`
  - `PHY.TOOLS.physics-asset`: Physics-asset/ragdoll & collision setup editor, owner `physics-architect`
  - `RND.VFX.editor`: VFX authoring & preview tool logic, owner `vfx-particles`
  - `RND.LOD.editor`: Mesh/LOD setup & preview, owner `virtualized-geometry-lod`
  - `GAM.AI.tools`: Nav authoring & debug tooling, owner `navigation-pathfinding`

### K-COMPLETE-8 · major · omission
- Sweep: 2 (prototyping, level design) and 1 (UE Modeling Mode/Geometry Script, Unity ProBuilder, Godot CSG, Source 2 Hammer mesh editing)
- Target: ED.WORLD, owner `world-editor-viewport`. Contributors: `math-simd-numerics` (`CORE.MATH.compgeo`), `collision-detection`.
- Finding: There is no in-engine geometry authoring: blockout/greybox primitives, CSG or mesh modeling, UV and lightmap-UV generation, and a runtime dynamic-mesh representation for procedural or editable geometry. `CORE.MATH.compgeo` provides the algorithms but no user-facing capability or runtime mesh type.
- Evidence: Level designers greybox inside the engine in every modern pipeline. Runtime dynamic meshes are also needed for PCG output, building games and destruction previews. Every engine in sweep 1 ships some version of this.
- Proposed change:
  - `ED.WORLD.blockout`: Blockout & in-engine mesh modeling (CSG, primitives, UV/lightmap-UV generation), owner `world-editor-viewport`
  - `RND.GEO.dynamic-mesh`: Runtime-editable dynamic mesh representation & GPU upload, owner `gpu-driven-pipeline`. Contributor: `procedural-generation`.

### K-COMPLETE-9 · major · omission
- Sweep: 2 (design, balancing) and 3 (RPG, strategy, F2P, card games)
- Target: GAM or CNT, owner `gameplay-systems-toolkit`. Contributors: `content-pipeline-architect`, `asset-import-interchange`.
- Finding: There is no capability for authoring tabular or curve game data (stats, balance tables, loot tables, difficulty curves), for import from and round-trip to spreadsheets (CSV/Sheets), or for referencing that data from gameplay. No hits for data table, spreadsheet, game data or balance. This is engine infrastructure, not game-specific code: every game uses it, and designers edit it without programmers.
- Evidence: UE DataTables/CurveTables/DataAssets, Unity ScriptableObjects plus spreadsheet importers, and Decima and Frostbite data-driven databases all serve this role. It is the core of live-ops balance hotfixes (with `PLAT.SVC.remote-config`).
- Proposed change: `GAM.SYS.data-tables`: Designer data tables, curve tables & spreadsheet round-trip. `GAM.SYS.data-hotfix`: Server-deliverable data overrides for balance. Contributor: `platform-online-services`.

### K-COMPLETE-10 · major · omission
- Sweep: 2 (narrative content discipline) and 3 (narrative/adventure, RPG, horror)
- Target: GAM, new area `GAM.NARR`, owner `gameplay-systems-toolkit` or a new `narrative-dialogue` skill
- Finding: There is no narrative or dialogue system. `AUD.CONTENT.dialogue` is VO playback. `06-gap-analysis.md` §C.2 classes dialogue trees and quests as game code and invites genre challenges. The challenge: branching-dialogue runtime, localization-aware line IDs (tying `UI.LOC.strings`, VO, lip sync and subtitles to one line), bark/response selection, and integration with narrative middleware (Ink, Yarn, articy:draft class) are shared engine infrastructure. They carry cross-domain contracts across localization, audio, facial animation and subtitles that no game team can own alone.
- Evidence: Source's Response Rules system, Northlight's and Decima's dialogue tooling, and the UE ecosystem's reliance on articy and Ink plugins. Without an owner, the VO → subtitle → lip-sync → localization chain has no coordinator.
- Proposed change: `GAM.NARR.dialogue`: Dialogue/line database & branching runtime with stable line IDs. `GAM.NARR.barks`: Contextual bark/response selection. `GAM.NARR.middleware`: Narrative-tool interchange (Ink/Yarn/articy class). Contributors: `localization-i18n`, `audio-content-runtime`, `facial-animation`, `accessibility`.

### K-COMPLETE-11 · major · omission
- Sweep: 2 (QA, playtesting, UX research) and 5 (HCI/UX)
- Target: QA or OBS, owner `functional-automation-soak`. Contributors: `observability-telemetry`, `crash-diagnostics`.
- Finding: Everything under QA is automated. Missing:
  - an in-game bug reporter that captures a screenshot or video, logs, position, build ID and a replay or save, and integrates with a bug tracker (Jira class)
  - playtest capture and UX-research instrumentation (heatmaps, session recordings, surveys)
  - build distribution to testers and playtesters (TestFlight, Play tracks, store beta branches, devkit fleet deploy)

  No hits for bug report, playtest or heatmap.
- Evidence: Manual QA and playtesting are a large share of AAA production cost, and repro capture is the main lever on that cost. The UE Gameplay Debugger plus studio bug tools and Unity Cloud Diagnostics user reporting are precedents. `ED.UI.ux` covers usability of the editor only, not players.
- Proposed change:
  - `QA.FUNC.bug-capture`: In-game bug reporting with repro capture & tracker integration
  - `QA.FUNC.playtest`: Playtest capture, heatmaps & UX-research instrumentation
  - `BLD.REL.test-distribution`: Tester/beta build distribution, owner `packaging-release-patching`

### K-COMPLETE-12 · major · omission
- Sweep: 3 (MMO/persistent, survival servers) and 5 (databases)
- Target: NET.SRV, owner `dedicated-server`. Contributor: `persistence-save`.
- Finding: There is no server-side persistence boundary. `GAM.SAVE.*` is client save-game (platform APIs, cloud save), and `GAM.SAVE.world-state` stores world deltas with no server context. Missing: database-backed character, world and entity persistence for dedicated servers (write-behind, transactional item grants, crash-consistent checkpoints, schema migration against live data). The backend itself is out of scope, but the engine-side boundary that server simulation writes through is not. Databases are the only discipline in sweep 5 with no representation at all.
- Evidence: Every persistent-world title (MMOs; survival titles such as Rust and ARK; persistent shooters) needs server persistence with duplication-safe transactions. Item-duplication exploits usually come from this boundary.
- Proposed change: `NET.SRV.persistence`: Server-side persistence boundary (database-backed entities, transactional grants, write-behind, live schema migration). Contributors: `persistence-save`, `serialization-schema`, `anti-cheat-integrity`.

### K-COMPLETE-13 · major · omission
- Sweep: 3 (shooters, fighting, MOBA/esports, sports) and 4 (streaming/creator policy)
- Target: NET.REP, owner `replication`, with `gameplay-architect` for the UX side
- Finding: `NET.REP.replays` records replays. Missing: live spectator/observer mode (delayed-broadcast clients, observer-only interest management, many spectators per match), kill-cam and instant replay (short local rewind buffers), replay playback UX (scrubbing, free camera), and streamer mode (copyright-safe music toggle, hiding personal info). No hits for spectator.
- Evidence: Precedents: CS2/Dota 2 GOTV-class broadcast (Source 2), UE `DemoNetDriver` with a kill-cam replay scrub, and the observer tools of every esports title.
- Proposed change: `NET.REP.spectator`: Spectator/broadcast clients with delay & observer relevancy. `NET.REP.killcam`: Short-horizon instant replay/kill-cam. `GAM.FW.streamer-mode`: Streamer-safe mode (music licensing, PII hiding). Contributor: `audio-content-runtime`.

### K-COMPLETE-14 · major · omission
- Sweep: 3 (flight/space sims) and 5 (physics/numerics)
- Target: PHY.CTRL, owner `character-vehicle-physics`
- Finding: The vehicle capabilities cover wheeled vehicles and buoyancy only. Missing: aerodynamics and flight models (lift/drag surfaces, blade-element rotor models), orbital and n-body mechanics (patched conics, high-precision integration), and watercraft hydrodynamics beyond buoyancy. No hits for aero or flight in physics.
- Evidence: Flight simulation is named in the genre sweep. Precedents: MSFS's CFD-based flight model, Star Citizen and Elite (flight and orbital), Kerbal (orbital), and flight-model plugins in UE and Unity. Chaos Vehicles covers wheeled vehicles only, which shows these are separate capabilities.
- Proposed change: `PHY.CTRL.aero`: Aerodynamic surfaces & flight models. `PHY.CTRL.orbital`: Orbital/n-body mechanics with double-precision integration. Contributor: `math-simd-numerics`.

### K-COMPLETE-15 · major · omission
- Sweep: 3 (flight sim, space, large-scale simulation) and 1 (MSFS/Asobo, Cesium for UE/Unity, Star Citizen planet tech, No Man's Sky)
- Target: WLD, owner `world-architect`. Contributors: `terrain`, `spatial-transforms`, `atmosphere-weather`.
- Finding: Large-world coordinates exist, but planet-scale and geospatial worlds do not. Missing: spherical or cube-sphere terrain and LOD, geodetic frames (WGS84 ↔ local ENU), real-world data ingestion (DEM, imagery, OSM, OGC 3D Tiles streaming), and planet-scale atmosphere seen from orbit. (The only "planet"-related hits were `sky` and `registry` false positives.)
- Evidence: This is a specific class of world representation that planar heightfield partitioning cannot handle. The brief's "large-scale simulation" and "future AAA open-world" targets (earth-scale flight sims, seamless planets) need it. The OGC 3D Tiles standard and Cesium integrations in UE and Unity are production precedents.
- Proposed change: `WLD.MODEL.planetary`: Planetary/spherical world representation & geodetic frames, owner `world-architect`. `WLD.ENV.terrain-planetary`: Spherical terrain LOD, owner `terrain`. `CNT.IMP.geospatial`: Geospatial data ingestion (DEM, 3D Tiles, OSM), owner `asset-import-interchange`.

### K-COMPLETE-16 · major · omission
- Sweep: 3 (survival/crafting/voxel/destructible sandboxes, city/colony builders, user-created worlds)
- Target: WLD.ENV, with a new owner split from `terrain` or a new `voxel-worlds` skill
- Finding: Voxels appear only as one alternative in `WLD.ENV.terrain-rep`. Also, `RND.GI.sdf` uses voxels only as a lighting-trace structure. Missing:
  - chunked voxel/block storage and compression (sparse voxel DAGs, palettes)
  - meshing (greedy, surface nets, dual contouring) at stream-in and on edit
  - runtime edit replication and persistence
  - block light propagation
  - player construction systems (snap/socket building, structural integrity) as reusable engine features

  `WLD.ENV.terrain-deform` covers terrain only.
- Evidence: Precedents: Minecraft, Teardown, Enshrouded, Valheim building, Fortnite building. This is a whole genre family with its own rendering, physics, networking and save contracts. Hiding it inside one terrain capability means no single agent coordinates those contracts.
- Proposed change:
  - `WLD.VOX.storage`: Chunked/sparse voxel storage & compression
  - `WLD.VOX.meshing`: Voxel meshing & remeshing on edit
  - `WLD.VOX.edits`: Runtime world edits (replication & persistence hand-off). Contributors: `replication`, `persistence-save`.
  - `GAM.SYS.building`: Player construction (sockets, snapping, structural integrity)

  Owner is a new `voxel-worlds` skill or `terrain`.

### K-COMPLETE-17 · major · omission
- Sweep: 3 (racing, flight sims, fighting) and 1 (SDL/DirectInput FFB, GameInput)
- Target: INP.DEV, owner `input-devices-haptics`
- Finding: Simulation and specialty controllers are not covered. `INP.DEV.haptics` is gamepad-oriented ("rumble, HD haptics, adaptive triggers"). Missing: steering wheels with force feedback (condition/periodic effects driven from tire forces), pedals and shifters, HOTAS and flight sticks with many axes, arcade sticks and hitboxes (SOCD handling, 1 kHz polling), and dance pads and instruments. No hits for force feedback.
- Evidence: Racing sims cannot ship without force feedback (Gran Turismo, Forza, iRacing). Fighting-game SOCD handling is required by tournament rules. Wheel FFB also needs a contract with `character-vehicle-physics` for the source forces.
- Proposed change: `INP.DEV.force-feedback`: Force-feedback devices (wheels, sticks) & effect model. Contributor: `character-vehicle-physics`. `INP.DEV.specialty`: Specialty/high-rate controllers (HOTAS, arcade, pedals, SOCD policy).

### K-COMPLETE-18 · major · omission
- Sweep: 3 (rhythm) and 5 (audio DSP/OS latency)
- Target: AUD.ARCH, owner `audio-architect`. Contributors: `frame-orchestration`, `input-system`.
- Finding: There is no audio/video/input synchronization or latency-calibration capability. `CORE.FRAME.latency` covers input-to-photon but not the audio output path. Missing: a sample-accurate audio clock exposed to gameplay, measurement of output-device latency (Bluetooth, TV processing), user A/V and input calibration flows, and beat/tempo-synchronized scheduling. The only calibration hit is HDR display calibration.
- Evidence: Every rhythm game (Beat Saber, Hi-Fi Rush, Guitar Hero-class) depends on this. Lip sync with FMV and interactive music quantization also need a shared audio clock. Platform APIs expose output latency differently on each OS, so this has to be an engine capability.
- Proposed change: `AUD.ARCH.clock`: Audio clock, latency measurement & A/V/input sync contract. `UI.A11Y.calibration` or `INP.ACT.calibration`: User latency-calibration flow.

### K-COMPLETE-19 · major · omission
- Sweep: 3 (indie, 2.5D, stylized titles) and 1 (Unity URP toon/Shader Graph custom lighting, Godot, Arc System Works' UE toon pipeline, Genshin-class)
- Target: RND.MAT or RND.POST, owner `material-system`. Contributor: `post-color-hdr`.
- Finding: There is no non-photorealistic or stylized rendering capability. The material model is OpenPBR-class. Missing: custom lighting models (cel/ramp shading), outline and edge detection (inverted-hull, depth/normal/ID-based), hatching and painterly post, and stylized shadows. No hits for stylized, toon or NPR. An engine meant to scale down to indie and 2.5D needs this as a first-class path, not as a workaround through a PBR material graph.
- Evidence: A large share of shipped indie titles, anime-styled AAA (Guilty Gear, Genshin, Zelda) and 2.5D games use NPR. It needs lighting-model extensibility, which is an architecture decision for the shading path and visibility buffer, so it has to be owned.
- Proposed change: `RND.MAT.custom-lighting`: Custom/stylized lighting models across shading paths, owner `material-system`. Contributor: `render-architect`. `RND.POST.stylized`: Outline, edge & stylized post effects, owner `post-color-hdr`.

### K-COMPLETE-20 · major · omission
- Sweep: 5 (recent graphics research) and 2 (scan-based environment content)
- Target: RND, owner `virtualized-geometry-lod` or `global-illumination`, maturity M/X
- Finding: Gaussian splatting and radiance-field scene representations are absent (no hits for splat, radiance field or NeRF). `CNT.IMP.scans` ingests photogrammetry, but nothing renders, sorts, relights, streams or LODs 3D Gaussian splats, or composites them with raster and RT geometry.
- Evidence: 3DGS (SIGGRAPH 2023) and its follow-ups (LOD, compression, RT-based splats) are research that production is adopting quickly. UE and Unity plugins exist, splat-based capture is used in virtual production, and the Khronos glTF splat extension work is under way. The brief asks for recent rendering research to be considered and classified. Leaving it out altogether means it is not even on the radar at X.
- Proposed change: `RND.GEO.splats`: Gaussian-splat / radiance-field rendering & compositing (M), owner `gpu-driven-pipeline`. `CNT.IMP.splats`: Splat asset import & compression (M), owner `asset-import-interchange`.

### K-COMPLETE-21 · minor · omission
- Sweep: 4 (store requirements) and 3 (arcade, racing, roguelikes, idle)
- Target: PLAT.SVC, owner `platform-online-services`
- Finding: Leaderboards, stats and tournaments are not named. `PLAT.SVC.achievements` covers achievements and presence, but platform leaderboards and stats APIs are a separate integration with their own anti-cheat needs (score validation).
- Proposed change: `PLAT.SVC.leaderboards`: Leaderboards, player stats & tournament integration boundary. Contributor: `anti-cheat-integrity`.

### K-COMPLETE-22 · minor · omission
- Sweep: 4 (analytics) and 2 (live ops)
- Target: OBS.LOG, owner `observability-telemetry`
- Finding: Product and game analytics (a player event taxonomy, funnels, retention) and A/B experimentation (cohort assignment tied to remote config) are hidden inside `OBS.LOG.telemetry`, "Development & live telemetry pipeline". That capability name describes engineering telemetry. Live-ops scheduling of seasonal or time-limited content is also only implicit.
- Proposed change: `OBS.LOG.analytics`: Game analytics event schema & analytics-SDK boundary. `PLAT.SVC.experiments`: A/B cohort & live-event scheduling boundary.

### K-COMPLETE-23 · minor · omission
- Sweep: 3 (mobile F2P, idle) and 4 (store requirements)
- Target: PLAT.MOB, owner `platform-mobile-portable`
- Finding: Mobile platform services are missing: local and push notifications, deep and universal links, install attribution (consent-gated, ATT), and store review prompts. Idle games also need trusted server time for offline progress.
- Proposed change: `PLAT.MOB.notifications`: Local/push notifications. `PLAT.MOB.links`: Deep links & attribution boundary (ATT consent). `PLAT.SVC.trusted-time`: Trusted server time for offline progression.

### K-COMPLETE-24 · minor · omission
- Sweep: 1 (UE trigger volumes/Level Blueprint, Source I/O entity logic, Godot Area nodes) and 2 (level design)
- Target: GAM.FW, owner `gameplay-architect`
- Finding: Level logic primitives (trigger and gameplay volumes, level-scoped scripting, designer-wired entity I/O) are hidden inside `GAM.SCR.visual` and `GAM.FW.extension`. Level designers depend on them from prototyping onward.
- Proposed change: `GAM.FW.level-logic`: Trigger/gameplay volumes & level-scoped logic wiring. Contributors: `collision-detection`, `scripting-runtime`.

### K-COMPLETE-25 · minor · omission
- Sweep: 4 (console certification) and 3 (couch/TV play)
- Target: UI.FW, owner `ui-architect`
- Finding: Title-safe and action-safe areas, display cutouts (notches, punch-holes) and aspect-ratio policy (ultrawide, 4:3, handheld) are hidden in `UI.FW.layout`. No hits for safe area, safe zone or aspect. TV safe-area compliance is a certification check.
- Proposed change: `UI.FW.safe-area`: Safe areas, cutouts & aspect-ratio adaptation. Contributor: `platform-architect`.

### K-COMPLETE-26 · minor · omission
- Sweep: 1 (UE GameUserSettings/scalability auto-detect, Unity QualitySettings) and 3 (PC)
- Target: PRF.METH or GAM.FW
- Finding: The player-facing settings layer is hidden in `PRF.METH.scalability` and `CORE.LIFE.config`. Missing: persisting user options, graphics presets, first-run hardware auto-detect/benchmark, and applying changes live without restart.
- Proposed change: `GAM.FW.user-settings`: User settings model, persistence & first-run hardware auto-detect. Contributors: `performance-architect`, `persistence-save`.

### K-COMPLETE-27 · minor · omission
- Sweep: 3 (fighting, action, shooters)
- Target: GAM.SYS, owner `gameplay-systems-toolkit`
- Finding: There is no capability for hit detection and hitbox/hurtbox authoring driven by animation frames, frame data, hit-stop, or hitscan/projectile hit resolution. It is implicit in `GAM.SYS.abilities` and `NET.PRED.lagcomp`, but fighting games need frame-exact authoring tools and a deterministic evaluation contract.
- Proposed change: `GAM.SYS.hit-detection`: Hit/hurtbox authoring, frame data & hit resolution. Contributors: `collision-detection`, `animation-runtime`, `prediction-rollback`.

### K-COMPLETE-28 · minor · omission
- Sweep: 3 (sports stadiums, city sims, RTS armies)
- Target: RND.GEO or ANM.ARCH
- Finding: Rendering massive animated crowds (vertex-animation textures, GPU-instanced skinning, animation impostors) is hidden inside `RND.GEO.instancing` and `ANM.ARCH.lod`. Neither says who owns tens of thousands of animated instances. `GAM.AI.mass` covers simulation only.
- Proposed change: `ANM.DEF.crowd`: Crowd animation rendering (VAT, instanced skinning, impostors), owner `deformation-skinning`. Contributor: `crowd-simulation`.

### K-COMPLETE-29 · minor · omission
- Sweep: 2 (sunset) and 4 (consumer-protection expectations, e.g. EU "Stop Killing Games" pressure)
- Target: BLD.REL, owner `packaging-release-patching`. Contributor: `dedicated-server`.
- Finding: Nothing covers end-of-service. Missing: offline-mode conversion of online-required titles, releasing server binaries for community hosting, final data export, and graceful behavior when backends are unreachable. The lifecycle in the map stops at live ops and rollback.
- Proposed change: `BLD.REL.end-of-service`: End-of-service plan (offline fallback, community server release, data export).

---

## Sweeps with no material omissions found
- **Sweep 5, core disciplines** (math, containers, concurrency, compilers/languages, OS, audio DSP, ML inference, security, testing, release engineering, documentation): covered, apart from the HTTP/crypto item (K-COMPLETE-3) and the database boundary (K-COMPLETE-12).
- **Rendering core** (GPU-driven, RT, GI, reconstruction, HDR/color), **physics core**, **animation runtime**, **build/CI**, **observability/crash**, and **localization/accessibility**: thorough. No omissions beyond those listed above.
