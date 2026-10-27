# K-NET — Networking Critic, round 1

### K-NET-1 · blocker · wrong-boundary
- Target: skills.json `profiles.base.server`, configuration `dedicated-server`; skills `physics-2d`, `terrain`, `procedural-generation`, `destruction-fracture`, `crowd-simulation`, `modding-ugc`, `ik-procedural-animation`, `motion-synthesis`
- Finding: `server` is modelled as a fourth *base* profile, parallel to min2d/mobile3d/std3d, so a server build cannot inherit the game type it serves. When membership is computed, `dedicated-server` = {server, online} leaves out `physics-2d` (tag `min2d`), `terrain`, `procedural-generation` and `crowd-simulation` (tag `openworld`), `destruction-fracture` (tag `aaa`), `modding-ugc` (tag `ugc`) and `ik-procedural-animation`/`motion-synthesis`. As a result:
  (a) the authoritative server for `indie-2d-online-moddable` has no 2D physics and cannot load server-side mods;
  (b) the server for `aaa-open-world-online` has no heightfield collision, no deterministic stream-in PCG, no authoritative destruction (even though `PHY.DEST.replication` assumes a server runs it), and no crowd or mass-agent simulation;
  (c) root motion driven by motion matching cannot be reproduced on the server.
  No configuration pairs `server` with `openworld`/`min2d`/`aaa`/`ugc`, so `check.py` closure never tests the server builds that matter. A headless *client* (bot-swarm load test, `QA.FUNC.load`) cannot be expressed either.
- Evidence: every shipping server-authoritative engine derives the server target from the same game module, minus presentation. Examples: UE `Server` target type with `IsRunningDedicatedServer` stripping, Unity DOTS NetCode server worlds, and Frostbite/Snowdrop dedicated servers for BF/Division open worlds. Minecraft, Rust, Valheim and Arma host mods mainly on dedicated servers. Agents following the current tags will build servers that cannot simulate the game.
- Proposed change: make build target an orthogonal axis. Add `targets: {client, server, headless-client, editor}` and let configurations be (base + addons) × target. Replace the tag `server` on skills with a per-skill `targets` field: presentation skills (render, audio, UI, input devices, deformation-skinning) get `client`; simulation skills (physics-2d, terrain collision/data, PCG runtime, destruction runtime, crowd, animation graph/IK/motion synthesis, modding-ugc loading) get `client, server`. Add named configurations `dedicated-server-2d` (min2d+online+ugc @server), `dedicated-server-open-world` (std3d+openworld+online+aaa+ugc @server) and `bot-client` (@headless-client), and have check.py prove closure for each.

### K-NET-2 · major · missing-contract
- Target: contract `C-NET`; skills `network-transport`, `replication`, `prediction-rollback`, `dedicated-server`, `audio-dsp-mixing`
- Finding: networking exposes exactly one contract, `C-NET` "Replication & authority", owned by the lead. `network-transport`, `replication`, `prediction-rollback` and `dedicated-server` provide nothing. There is no transport/session contract (connections, channels, reliability classes, bandwidth estimate, MTU budget, connection events). So:
  - `replication` consumes no transport interface at all.
  - `audio-dsp-mixing` declares "Voice-chat transport → network-transport" as a non-responsibility but has no contract to reach it, and does not consume C-NET.
  - `anti-cheat-integrity`, `dedicated-server`, `gameplay-systems-toolkit` and `functional-automation-soak` all bind to one blob that mixes transport, replicated-state declaration, prediction hooks and server lifecycle.
  Four expert agents will implement behind one interface they do not own. The lead will have to arbitrate every change.
- Evidence: production stacks keep these layers separate, e.g. UE NetDriver/Connection/Channel vs Iris replication vs NetworkPrediction plugin, Unity Transport vs NetCode for Entities, and Valve GameNetworkingSockets vs game replication. Voice, telemetry streams and rollback input exchange use transport without replication.
- Proposed change: split `C-NET` into four contracts:
  - `C-NETLINK` (layer 2, owner `network-transport`): sessions, channels, reliability/ordering classes, send budgets, link stats, connection events.
  - `C-REP` (layer 3, owner `replication`): replicated state declaration, relevancy hooks, RPCs, net IDs; requires C-NETLINK, C-ECS, C-SER.
  - `C-PREDICT` (layer 3, owner `prediction-rollback`): predicted/rollback-able state registration, input history, resim hooks, rewind queries; requires C-REP, C-DET.
  - `C-NET` (owner `network-architect`): model/authority/tick policy only.
  Then make `audio-dsp-mixing` consume `C-NETLINK?` and `dedicated-server` consume `C-NETLINK`.

### K-NET-3 · major · missing-contract
- Target: `C-ECS`, `C-PHYS`, `C-ANIM`, `NET.PRED.rollback`, `NET.PRED.lagcomp`, `NET.PRED.physics`; skill `prediction-rollback`
- Finding: rollback and resimulation need the simulation to save and restore its state many times per frame. Lag compensation needs a history of past collision/hitbox state. None of the contracts it relies on carry these obligations:
  - C-ECS: "Components, queries, systems, access declarations, command buffers". No snapshot/restore and no marking of rollback-able components.
  - C-PHYS: "Bodies, shapes, queries, contact events, stepping phases". No state save/restore, no deterministic resim of a subset, no rewind/historical queries.
  - C-ANIM: no pose/hitbox history.
  `prediction-rollback` does not consume C-ECS or C-ANIM (only C-NET, C-DET, C-PHYS?, C-INPUT?). ECS, physics and animation agents will not build these hooks, and retrofitting them is the classic large rework.
- Evidence: GGPO-class rollback needs save/load state in well under 1 ms per rolled-back frame, often 7–8 frames per tick. Examples: Overwatch GDC 2017 ECS netcode (Ford), Rocket League physics resim (Cone, GDC 2018), Unity NetCode ghost prediction and snapshot history, Jolt `SaveState/RestoreState`, Photon Quantum's frame-copying ECS, and CS2/Valorant server-side hitbox rewind buffers.
- Proposed change: add obligations to three contracts and make prediction-rollback consume the new contracts.
  - C-ECS: "world/component snapshot & restore, rollback-able component marking, deterministic structural-change replay".
  - C-PHYS: "state save/restore, partial resimulation, historical query window".
  - C-ANIM: "hitbox pose history for rewind".
  - Add capability `CORE.ECS.snapshot` (owner `ecs-runtime`, contributor `prediction-rollback`) and `PHY.ARCH.state` (owner `physics-architect`, contributor `prediction-rollback`).
  - Make `prediction-rollback` consume `C-ECS`, `C-ANIM?`, and C-PREDICT (see K-NET-2).

### K-NET-4 · major · missing-contract
- Target: skill `input-system` (profile `client`), `C-INPUT`, `NET.PRED.prediction`, `NET.PRED.rollback`, `NET.PRED.lockstep`
- Finding: server-authoritative, rollback and lockstep models all simulate from *networked input commands*: action values stamped with a sim tick, then serialized, redundantly sent and buffered. No capability or contract owns this command stream. `input-system` (owner of C-INPUT) is tagged `client`, so C-INPUT is absent from `dedicated-server`. The server therefore has no owner for the action schema it must simulate. Gameplay systems on the server will read inputs from an ad hoc format.
- Evidence: Quake/Source `usercmd`, the UE CharacterMovement `SavedMove`/NetworkPrediction input cmds, Unity NetCode `IInputComponentData`, and GGPO input exchange with delay/prediction. The command format is a first-class protocol element and a prime cheat surface (input validation).
- Proposed change: add capability `NET.PRED.input-commands` ("Tick-stamped networked input command stream, redundancy, buffering and server-side input validation hooks"). Owner `prediction-rollback`, contributors `input-system` and `anti-cheat-integrity`. Split C-INPUT into a device-free action-schema part (all targets incl. server) and device binding (client), or tag `input-system`'s action-schema part for the server target.

### K-NET-5 · major · omission
- Target: crosscutting.json; `GAM.SYS.abilities`, `ANM.ARCH.sync`, `RND.VFX`/`vfx-particles`, `AUD.CONTENT`, `GAM.SYS.spawning`
- Finding: no cross-cutting concern states "network behavior". Nothing obliges gameplay-facing skills to declare which state they replicate, who is authoritative, what is predicted versus cosmetic, and whether they are rollback-safe. Ownership of *predicted gameplay* is ambiguous. Predicted abilities (prediction keys, effect rollback), predicted projectile spawning, montage/root-motion replication under prediction, and cosmetic-only VFX/audio re-trigger suppression during resim sit between `gameplay-systems-toolkit` (consumes only `C-NET?`), `animation-architect` (no C-NET dependency at all), `vfx-particles`/audio (no C-NET) and `prediction-rollback`.
- Evidence: in UE, GAS prediction keys, CharacterMovement/Mover and montage replication were each hand-built for networking and are the most rework-prone systems. Rollback games must suppress VFX/SFX re-spawn during resim (GGPO/Street Fighter/Killer Instinct postmortems). Overwatch 2017 talk: every ECS system is classified as predicted or not.
- Proposed change: add concern `{"concern":"network authority & replication","owner":"network-architect","obligation":"Declare replicated state, authority, prediction/rollback participation, cosmetic-vs-simulated split, and server-target behavior."}`. Add capability `GAM.SYS.predicted-abilities` (owner `gameplay-systems-toolkit`, contributor `prediction-rollback`) and `ANM.ARCH.net-sync` (owner `animation-architect`, contributor `replication`). Add `C-NET?`/`C-PREDICT?` to animation-architect, vfx-particles and audio-content-runtime.

### K-NET-6 · major · omission
- Target: NET domain, `ED.ARCH.pie`, `QA.FUNC.network`, `OBS.LOG.*`
- Finding: there is no network debugging or profiling tooling. Missing items:
  - a network profiler with per-connection, per-entity and per-property bandwidth attribution;
  - packet capture/inspection with a protocol dissector;
  - relevancy/priority visualization;
  - prediction-error and correction visualization;
  - desync/rollback timelines;
  - multi-client play-in-editor (server plus N clients in one editor session, each with simulated link conditions).
  `NET.SRV.observability` covers servers only. `ED.ARCH.pie` says "simulation isolation" but nothing about multiple net peers. Networked games cannot be tuned against `NET.ARCH.budgets` without attribution tooling. The brief names network profiler, replay of network sessions and packet inspection explicitly.
- Evidence: UE Network Profiler / Networking Insights and PIE "Number of Players / Net Mode / Network Emulation"; Unity Multiplayer Tools (Network Profiler, Network Simulator, Runtime Net Stats Monitor); Overwatch's replay-based netcode debugging; Valve GNS dissector and `net_graph`.
- Proposed change: add area `NET.DBG` with owner `replication` unless noted:
  - `NET.DBG.profiler`: bandwidth attribution per connection/entity/property.
  - `NET.DBG.inspect`: packet capture and dissector. Owner `network-transport`.
  - `NET.DBG.visualize`: relevancy, priority and prediction-error overlays. Contributor `visual-debugging-tools`.
  - `NET.DBG.session-replay`: record/replay of a full network session for debugging. Contributor `determinism-replay`.
  Add `ED.ARCH.pie-multiplayer` "Multi-peer PIE with net emulation" (owner `editor-architect`, contributor `network-architect`).

### K-NET-7 · major · wrong-boundary
- Target: `GAM.SAVE.world-state`, `persistence-save`, `platform-online-services`, `C-SVC`, design principle "Online backend services ... outside engine scope"
- Finding: the framework excludes the backend, which is fine. But it also leaves the *game-server side* of the backend boundary unowned:
  - server-authoritative persistence of player/character/inventory data to a backend store (write-behind, crash-consistent flush, ownership leases);
  - transactional and idempotent economy/inventory/grant operations;
  - validation of player auth tickets at the server;
  - server service identity.
  `persistence-save` is a save-game skill: platform save APIs, cloud save, checkpoints. C-SVC is described client-side ("identity tokens, entitlements, sessions"). MMO, persistent-survival, extraction-shooter and live-service games will need these, and agents will put them in whichever skill is closest.
- Evidence: examples of server-side persistence gateways in engine/SDK: Destiny/WoW-class character persistence, SpatialOS and Improbable postmortems, PlayFab/EOS/Nakama server SDKs (auth ticket validation, server-authoritative inventory APIs), and Rust/Valheim server world saves. Duplicate-item exploits come from non-idempotent grants.
- Proposed change: add capabilities with owner `dedicated-server` and contributor `platform-online-services`:
  - `NET.SRV.persistence` "Server-authoritative persistent player/world data boundary (write-behind, leases, crash consistency)". Also contributor `persistence-save`.
  - `NET.SRV.transactions` "Idempotent economy/inventory transaction boundary". Also contributor `anti-cheat-integrity`.
  - `NET.SRV.auth` "Server-side auth-ticket and service-identity validation". Also contributor `network-transport`.
  Extend C-SVC's summary with a server-side service surface.

### K-NET-8 · major · maturity-error
- Target: `NET.ARCH.sharding` (owner `network-architect`, M), `WLD.PART.server`
- Finding: one capability, labelled "emerging" and owned by the lead as "evaluation", covers everything from zoned or instanced multi-server worlds to seamless dynamic server meshing. Zoning, instancing and handoff is *established*: WoW, EVE, FFXIV and many MMOs. Seamless dynamic meshing with cross-server entity authority transfer is *experimental*: Star Citizen server meshing (2024–25), SpatialOS (commercially withdrawn), and UE's Multi-Server Replication plugin (experimental). No expert owns implementation of cross-server entity handoff, cross-boundary interest or proxy entities, or the coupling to world cells.
- Proposed change: split into `NET.ARCH.zoning` "Zoned/instanced multi-server worlds & player handoff" (E, owner `dedicated-server`, contributors `world-architect`, `replication`) and `NET.ARCH.meshing` "Seamless dynamic server meshing / cross-server entity authority" (X, owner `network-architect`, reachable only via an optional contract). Add contributor `network-architect` to `WLD.PART.server`.

### K-NET-9 · major · omission
- Target: area `PLAT.SVC`; `QA.CERT.platform`
- Finding: platform multiplayer and social requirements have no capabilities. Missing items:
  - parties;
  - invites and join-in-progress from system UI / activities;
  - joinable presence;
  - privilege and permission checks for multiplayer, crossplay, voice/text communication and UGC, including parental controls;
  - platform block lists enforced in matchmaking and chat;
  - required handling of network connectivity loss and sign-out mid-session;
  - session resume after suspend/quick-resume.
  Leaderboards and stats are also absent. These are online-certification requirements on every console (Xbox XR, PlayStation TRC, Nintendo lotcheck). Their lack forces late rework in session and UI flow.
- Evidence: Xbox Requirements XR-015/045/074 (privileges, communication, block lists), PSN TRCs for session/invitation/activities, Steam lobby join via `GameLobbyJoinRequested`, and EOS/PlayFab party APIs.
- Proposed change: add capabilities, owner `platform-online-services` unless noted:
  - `PLAT.SVC.social`: parties, invites, joinable presence, friends, block lists.
  - `PLAT.SVC.privileges`: multiplayer, crossplay, communication and UGC privileges plus parental controls. Contributor `certification-compliance`.
  - `PLAT.SVC.leaderboards`: stats and leaderboards.
  - `NET.ARCH.connectivity`: connectivity loss, sign-out and suspend/resume session policy. Owner `network-architect`; contributors `platform-console`, `platform-mobile-portable`, `gameplay-architect`.

### K-NET-10 · major · omission
- Target: `AUD.DSP.voip`, `audio-dsp-mixing`, `network-transport`, `platform-online-services`
- Finding: only voice *capture/processing* is a capability. Nothing owns the rest of voice chat:
  - voice transport (a non-responsibility pointing to network-transport, which has no voice capability);
  - voice channels and sessions (team/proximity);
  - integration with platform or third-party voice services;
  - positional voice through the spatializer;
  - mute/block enforcement;
  - legally required speech-to-text/text-to-speech for communications (US CVAA, EAA).
  The feature has no end-to-end owner, and three skills will each assume another did it.
- Evidence: Vivox/EOS Voice/PlayStation party chat are service-hosted, not game-transport. CVAA applies to in-game communication (FCC 2019 enforcement). Proximity voice is established (Rust, Lethal Company, Sea of Thieves).
- Proposed change: add capability `PLAT.SVC.voice` "Voice/text chat sessions, channels, service integration, mute/block, STT/TTS for comms" (owner `platform-online-services`, contributors `audio-dsp-mixing`, `accessibility`, `certification-compliance`). Add `NET.TRANS.voice` "Game-transport voice path (P2P/server-relayed)" (owner `network-transport`, contributor `audio-dsp-mixing`). Make `audio-dsp-mixing` consume `C-NETLINK?` (K-NET-2).

### K-NET-11 · major · omission
- Target: `NET.ARCH.model`; skills.json configurations
- Finding: the netcode model taxonomy lists authoritative server, lockstep, rollback and P2P/relay. It omits:
  - asynchronous and turn-based backend-mediated play (mobile async, card, strategy, chess);
  - distributed or shared authority (per-object ownership transfer, host-authoritative P2P in co-op, e.g. Destiny/Sea of Thieves/Unity Distributed Authority);
  - MMO persistent-world architecture.
  No configuration combines `mobile3d` with `online`, although mobile online is the largest online segment. So closure is never proven for a mobile online build (mobile platform + transport + online services).
- Evidence: genre survey: Clash Royale (server-authoritative deterministic lockstep on mobile), Words with Friends-class async, Unity Netcode Distributed Authority (2024), Halo/Destiny hybrid host models.
- Proposed change: add `NET.ARCH.async` "Asynchronous/turn-based backend-mediated play" (E, owner `network-architect`, contributor `platform-online-services`) and `NET.ARCH.distributed-authority` "Per-object ownership transfer & shared authority" (E, owner `network-architect`, contributor `replication`). Add configurations `mobile-online` (mobile3d+online) and `indie-2d-online` without ugc.

### K-NET-12 · major · overlap
- Target: `NET.ARCH.versioning` (network-architect, contributor api-lifecycle-migration) vs `BLD.REL.compat` (packaging-release-patching, contributor network-architect); `C-PKG` "version compatibility"
- Finding: two capabilities with two owners describe the same policy: which client, server and content versions may connect. Live-ops cases include staggered console cert approval producing cross-platform patch skew, rolling server fleet deploys with mixed versions, and hotfix content without a client patch. No one owns the compatibility *window* policy or the handshake negotiation. Both agents will define it.
- Proposed change: keep `NET.ARCH.versioning` as the single owner of the compatibility-window policy and connection handshake (add to name: "incl. live-ops version skew, crossplay patch skew, rolling server deploys"). Reduce `BLD.REL.compat` to "Emit version/compat manifests into packages per NET.ARCH.versioning policy", or delete it and add `packaging-release-patching` as a contributor to NET.ARCH.versioning. Make `packaging-release-patching` consume `C-NET?`.

### K-NET-13 · minor · dependency-error
- Target: skills `replication`, `dedicated-server`; `NET.REP.interest`, `WLD.PART.server`
- Finding: interest management and relevancy at open-world scale are spatial: grid/cell relevancy, and replication graphs keyed on world cells. Yet `replication` consumes neither `C-SPATIAL` nor `C-WORLD`. `dedicated-server` runs server-side world streaming but does not consume `C-WORLD`.
- Evidence: UE ReplicationGraph and Iris spatial filter use grid cells, and World Partition server streaming feeds relevancy (Fortnite).
- Proposed change: `replication` consumes `C-SPATIAL`, `C-WORLD?`. `dedicated-server` consumes `C-WORLD?`. Add contributor `world-architect` to `NET.REP.interest`.

### K-NET-14 · minor · omission
- Target: area `NET.TRANS`
- Finding: nothing covers connection-level DoS and abuse resistance: stateless connect challenges/tokens, amplification limits, per-address rate limiting, hiding server IPs behind relays. `NET.TRANS.crypto` covers encryption/authentication only. The rate limiting under `anti-cheat-integrity` is gameplay-level.
- Evidence: netcode.io connect tokens, Valve SDR relays (hide game-server IPs from DDoS), and QUIC retry tokens.
- Proposed change: add `NET.TRANS.dos` "Connection DoS/amplification resistance, stateless challenges, relay-shielded addressing" (owner `network-transport`, contributor `security-engineering`).

### K-NET-15 · minor · omission
- Target: `NET.TRANS.sockets`, `NET.TRANS.quic`, `PLAT.PAL.web`
- Finding: the web target (`PLAT.PAL.web`) cannot use UDP sockets. Only QUIC/WebTransport (M) is listed. There is no established browser path: WebSocket for client/server, and WebRTC data channels (unreliable/unordered) for browser P2P. A web online configuration has no established transport.
- Proposed change: add `NET.TRANS.web` "Browser transports (WebSocket, WebRTC data channels; WebTransport where available)" (E, owner `network-transport`, contributor `platform-architect`).

### K-NET-16 · minor · omission
- Target: `NET.REP.replays`, `XC.DET.replay`, `INP.ACT.recording`
- Finding: player-facing replay features have no owner:
  - spectator/broadcast mode (delayed, relevancy-free view);
  - killcam, which needs a server-held recent-history buffer sent to a client;
  - shipping *input-stream* replays for lockstep games (RTS), since `XC.DET.replay` is scoped "for debugging".
- Evidence: StarCraft/AoE ship input-log replays; CS/Valorant killcams and GOTV/SourceTV spectator relays.
- Proposed change: rename `NET.REP.replays` to "Replays, spectator & killcam from the replication stream". Add `NET.PRED.lockstep-replay` "Shipping input-stream replays for lockstep games" (owner `prediction-rollback`, contributor `determinism-replay`).

### K-NET-17 · minor · overlap
- Target: `XC.SEC.tamper` (security-engineering) vs `XC.SEC.anticheat` (anti-cheat-integrity); skill `anti-cheat-integrity` consumes
- Finding: "Anti-tamper & DRM boundary" and "Client anti-cheat middleware integration boundary" both own client binary-integrity middleware integration: EAC/BattlEye/Vanguard vs Denuvo-class tools, each with launcher, signing and kernel-driver interplay. Neither lists the other as contributor. Separately, `anti-cheat-integrity` claims server validation of "movement, hits, economy" while consuming only `C-NET` and `C-INSTR`. It has no `C-PHYS`, `C-GAME` or C-SVC access to validate against.
- Proposed change: add `anti-cheat-integrity` as contributor to `XC.SEC.tamper`, and state in both non-responsibilities that client integrity middleware is anti-cheat and DRM is security. `anti-cheat-integrity` consumes `C-PHYS?`, `C-GAME?`, `C-SVC?` and C-PREDICT (K-NET-4 input validation).
