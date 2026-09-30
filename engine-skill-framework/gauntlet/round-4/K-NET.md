# K-NET findings (Networking Critic, round 4)

### K-NET-1 · major · dependency-error
- Target: milestones M2/M4, C-REP, C-PREDICT, C-HOSTAUTH, C-NETSESSION, NET.PRED.lagcomp, NET.REP.*
- Finding: C-REP, C-PREDICT, C-NETSESSION and C-HOSTAUTH are frozen at M2, but no configuration claimed by M2 contains replication (fighting-2d-rollback-* , mobile-async-*, indie-2d, sandbox-2d, minimal all exclude it). The first configurations with replication, lag compensation, server-authoritative reconciliation, listen and dedicated hosting are claimed at M4. C-REP and the server-authoritative half of C-PREDICT are frozen without a consumer configuration. check.py only proves an owner skill and some consumer skill exist, not that a claimed configuration exercises the contract.
- Evidence: M2 exit proves only rollback (8 frames, 150 ms, 5% loss) and async play. Snapshot interpolation, interest management, RPC authority, lag compensation and prediction reconciliation appear first in the M4 exit ("dedicated-server shooter with prediction and lag compensation"). C-SERVER is deliberately frozen after M4 (M5), which shows the ladder is meant to freeze after proof.
- Proposed change: freeze C-REP at M4 (draft M1-M3). Split C-PREDICT freeze: keep the rollback and lockstep obligations at M2 and add a server-authoritative obligation set (reconciliation, rewind queries, lag compensation) that freezes at M4. Or add a server-authoritative config to M2. Add a freeze-proof rule to check.py: a contract may be frozen only at a milestone that claims a configuration containing its owner and a consumer.

### K-NET-2 · major · missing-contract
- Target: C-NETSESSION, C-REP, C-PREDICT, net-session, replication, NET.SESS.baseline/reconnect/travel/join
- Finding: session-level events (join-ready, baseline start, travel, reconnect with ownership restore, disconnect) have no declared direction into replication. replication consumes C-NET, C-NETLINK and C-HOSTAUTH? but not C-NETSESSION. net-session consumes C-REP? optionally and C-SNAPSHOT/C-DET not at all, although NET.SESS.baseline is "replicated snapshot or C-SNAPSHOT + command catch-up". Only prediction-rollback consumes C-NETSESSION. Replication cannot know when to start per-connection baseline, reset relevancy on travel, or restore ownership, and net-session cannot request a baseline, unless a cycle is introduced.
- Evidence: Unreal (NetDriver/PlayerController join, seamless travel), Unity Netcode/Mirror (connection-ready callbacks), Photon Fusion (late-join snapshots) all give the replication layer session lifecycle callbacks.
- Proposed change: define in C-NETSESSION a participant interface (on_join_ready, provide_baseline, on_travel, on_reconnect, on_disconnect) that replication, prediction-rollback and determinism-replay implement. Add C-NETSESSION to replication.consumes (required). net-session then does not consume C-REP.

### K-NET-3 · major · missing-contract
- Target: anti-cheat-integrity, net-session, C-INTEGRITY, C-HOSTAUTH, NET.SESS.disconnect
- Finding: NET.SESS.disconnect owns the "ban hook", and C-HOSTAUTH claims kick/ban "in every host mode", but no skill declares the edge from an integrity verdict to kick/ban. anti-cheat-integrity does not consume C-HOSTAUTH and net-session does not consume C-INTEGRITY. Only dedicated-server consumes both, so listen, P2P host, rollback and lockstep hosts have no path from anomaly signal to enforcement.
- Evidence: EOS Anti-Cheat and Steam VAC integrations register kick callbacks with the session layer; server-side validators (Valve Source/CS2 sv_ validation) act through the connection layer.
- Proposed change: net-session consumes C-INTEGRITY? and applies verdicts through C-HOSTAUTH. C-INTEGRITY declares a verdict type (kick, ban, quarantine, flag). Add a conformance case for listen-host kick.

### K-NET-4 · major · overlap
- Target: NET.TRANS.crypto, NET.SESS.auth, NET.SESS.handshake, NET.ARCH.versioning, auth-tickets input
- Finding: auth-ticket and service-identity validation is stated in two capabilities with different owners (NET.TRANS.crypto by network-transport, "auth-ticket / service-identity validation", and NET.SESS.auth by net-session, "Auth-ticket & service-identity validation in every host mode"). The handshake is in three (NET.ARCH.versioning "policy & handshake", NET.SESS.handshake, and the transport crypto handshake). The registry names net-session as the validating owner of auth-tickets. No text says where the transport handshake ends, where the session handshake starts, or who binds the ticket to the transport session key (channel binding).
- Evidence: EOS/Steam auth-ticket flows, QUIC/DTLS 1.3 handshakes and Source/Unreal "login after connect" are a known source of unauthenticated-state windows and replay of tickets across sessions.
- Proposed change: NET.TRANS.crypto covers only channel encryption and peer key establishment. Delete ticket/service-identity from its text. NET.SESS.auth is the sole owner of ticket validation and channel binding. Add a C-NETLINK "authenticated-channel" state exposing the key-binding token. NET.ARCH.versioning keeps policy only, and NET.SESS.handshake the mechanism.

### K-NET-5 · major · overlap
- Target: dedicated-server purpose, NET.SESS.budgets, NET.SESS.overload, NET.SRV.admin, C-HOSTAUTH, C-SERVER, admin-commands input
- Finding: dedicated-server's purpose still claims "overload degradation, per-connection budgets, the authenticated admin surface", but per-connection budgets and overload actuators are net-session capabilities (NET.SESS.budgets/overload, C-HOSTAUTH). The admin surface is in both C-HOSTAUTH ("host-local admin surface") and C-SERVER/NET.SRV.admin ("authenticated admin command surface"). Two contracts, two owners, one RBAC/audit surface, and listen hosts get neither.
- Evidence: purpose text vs capabilities in skills.json/capabilities.json.
- Proposed change: rewrite dedicated-server purpose to drop budgets and overload. Make one admin surface: C-HOSTAUTH keeps kick/ban and quota primitives, NET.SRV.admin (C-SERVER) owns RBAC, audit and remote transport, and states that listen hosts expose only the local console.

### K-NET-6 · major · scale-down
- Target: configurations, dedicated-server profiles, NET.SESS.host-mode, NET.PRED.spectator, QA.FUNC.network
- Finding: no configuration has a headless/server target for lockstep or rollback. dedicated-server, replication and server-scaleout carry only the "online" profile. rts-2d-massim-client, rts-3d-massim-client, fighting-2d-rollback-* and rts-massim-lockstep-tools are client or tools only. So relay-hosted or authoritative-referee hosting, server-side desync arbitration, server-run input-stream spectators, replay verification, and a headless bot for CI soak (the M4 "desync-free 2 h lockstep soak", M2 rollback proof) are not proven closed. online-3d-bot-client exists only for std3d state replication.
- Evidence: Photon/Riot-style hosted rollback and lockstep relays (League of Legends spectator servers, Age of Empires relay, GGPO-based games with relay), tournament referee servers.
- Proposed change: add rts-2d-lockstep-server (min2d, massim, online-lockstep, server) and fighting-2d-rollback-headless-client (min2d, online-rollback, headless-client, server-host). Give dedicated-server the online-lockstep and online-rollback profiles or a slim "relay/referee" variant. Claim both at M2/M4.

### K-NET-7 · major · missing-contract
- Target: NET.PRED.lagcomp, NET.REP.interpolation, C-INPUT, C-PREDICT, C-REP, PHY.ARCH.rewind, ANM.RT.pose-history
- Finding: lag compensation needs the client view time (interpolation tick pair and delay) at fire time. That value is produced by replication (interpolation), carried by input command frames (C-INPUT format owned by input-system), consumed by prediction-rollback, and applied through C-PHYS collider history and C-ANIM pose history. No contract carries it: C-INPUT is only "tick-stamped input-command frames", C-PREDICT no longer requires C-REP, and the rewind query API is split between "rewind queries" (C-PREDICT), "collider history" (C-PHYS) and "pose history" (C-ANIM) with no owner for the composed rewound query. The history window and memory budget per collider/pose (max RTT plus interpolation delay) has no budget line either.
- Evidence: Valve "Source Multiplayer Networking" (cmd view interp fields in usercmd), Overwatch GDC 2017 (server-side rewind window), Unreal Character/Mover with NetworkPhysics/Lag comp plugin.
- Proposed change: add an extensible command-metadata field (view stamp) to C-INPUT. C-REP exposes client view time as a readable value. Add a C-PREDICT rewound-query facade that composes C-PHYS+C-ANIM histories. Add rewind window and memory line to C-BUDGET per configuration.

### K-NET-8 · minor · omission
- Target: NET.SESS.host-mode, NET.ARCH.distributed-authority, QA.SIM.netsim
- Finding: host migration is one clause inside NET.SESS.host-mode, with contributors network-architect and dedicated-server only. Migration needs replicated state or snapshot (replication, determinism-replay), prediction state and authority transfer (NET.ARCH.distributed-authority), none of them contributors, and it has no oracle scenario.
- Evidence: Halo Reach/Destiny P2P host migration post-mortems; Unreal/Photon host migration requires state hand-off of authoritative objects.
- Proposed change: split NET.SESS.host-migration (net-session) with contributors replication, prediction-rollback, determinism-replay, and add a netsim host-drop scenario to NET.ARCH.validation.

### K-NET-9 · minor · omission
- Target: NET.ARCH.budgets, C-BUDGET, PRF.NET.bandwidth, NET.TRANS.simulation
- Finding: NET.ARCH.budgets is owned by network-architect, but C-BUDGET (performance-architect, "budget numbers per tier x configuration") names no network line (per-connection bytes/s, server egress per CCU, tick cost per player, packet rate). No set of named link-condition profiles (home Wi-Fi, cellular, console NAT, transcontinental) per tier feeds NET.TRANS.simulation, QA.SIM.netsim and PRF.NET.*. Two sources of budget truth and no shared network-condition vocabulary.
- Evidence: Unreal/Unity network emulation profiles (Bad/Average/Lossy presets), Riot Valorant netcode talk (per-tier bandwidth).
- Proposed change: add network lines and named link-class profiles to C-BUDGET; NET.ARCH.budgets supplies values, C-BUDGET stores them; QA and PRF read the stored table.

### K-NET-10 · minor · omission
- Target: untrusted-inputs.json, NET.SESS.server-browser, NET.TRANS.local-network
- Finding: LAN discovery replies, master-server and community server-list entries (names, endpoints, content URLs) are pre-auth hostile-remote data rendered in UI and used to pick connect addresses, but are registered nowhere (packets covers frames, service-responses covers backends).
- Evidence: Quake-family master server and Source A2S query exploits; server-name injection in UI.
- Proposed change: register server-list-entries (validating owner net-session, parser network-transport, limits: length, count, rate, endpoint allow-list).

### K-NET-11 · minor · scale-down
- Target: ANM.RT.pose-history, NET.PRED.lagcomp, indie-2d-online-moddable-server
- Finding: ANM.RT.pose-history is restricted to lite3d/std3d, while min2d online configurations contain prediction-rollback with lagcomp; animated 2D hitboxes (skeletal 2D, frame-data sprites) have no history owner.
- Evidence: 2D skeletal shooters with server rewind need hitbox history (Spine/DragonBones hitboxes).
- Proposed change: add min2d to the capability profiles, or add a 2D hitbox-history obligation in physics-2d through PHY.ARCH.rewind.

## Sweep notes (no finding)
- Interest management vs anti-cheat hiding: covered (NET.REP.interest + XC.SEC.info-hiding + C-REP filter).
- Prediction reconciliation vs rollback: one owner (prediction-rollback), boundary with character-movement stated.
- Transport reliability classes: covered (NET.TRANS.reliability, L42).
- Replay/spectator: split by netcode model, coherent.
- Crossplay: policy in platform-services, versioning in NET.ARCH.versioning; acceptable.
- Online configs contain their skills except as in K-NET-6.
