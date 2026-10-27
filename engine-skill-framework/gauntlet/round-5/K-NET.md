# K-NET (Networking Critic), round 5

Sweep notes (no finding): reconciliation vs rollback has one owner (prediction-rollback, NET.PRED.prediction/rollback); transport reliability classes (NET.TRANS.reliability, C-NETLINK) present; host migration, spectator and replay streams have owners and contracts; interest management vs information hiding is joined by the relevancy-filter hook in C-REP and XC.SEC.info-hiding; each online configuration was checked for the skills it requires and is closed except where noted below.

### K-NET-1 · major · missing-contract
- Target: C-SHARD, NET.SRV.cross-server, NET.SRV.zoning, C-SIGNIF, physics-architect, character-movement, gameplay-systems-toolkit, ai-behavior-perception
- Finding: C-SHARD defines an "entity migration protocol" but has no participant interface. Only replication consumes it (optionally). Every domain that holds runtime state (physics islands and contacts, movement state, active abilities and effects, AI and script state, timers) has no hook to serialize, hand off and restore mid-flight state. C-NETSESSION has participants and C-SIGNIF has per-domain promote/demote handlers, but C-SHARD has neither.
- Evidence: EVE Online node hand-off, SpatialOS entity-component authority delegation and BigWorld cell migration all require per-component hand-off callbacks. Only replicated properties travel otherwise, so hand-off silently drops non-replicated simulation state.
- Proposed change: add a participant interface to the C-SHARD summary (on_migrate_out / on_migrate_in / ghost_border), implemented by physics-architect, character-movement, gameplay-systems-toolkit and the AI skills. Add matching consumes edges, C-SHARD@module. Make the migration-state class part of C-STATECLASS.

### K-NET-2 · major · scale-down
- Target: dedicated-server, net-session, configurations for online-lockstep and online-rollback, NET.PRED.spectator, NET.SESS.host-mode, NET.ARCH.async-validation
- Finding: no configuration has target server or headless-client for online-lockstep or online-rollback. dedicated-server, and with it all NET.SRV.*, is gated to the `online` profile only. Relay-hosted rollback, dedicated or tournament lockstep hosts, input-stream spectator fan-out and ranked-result validation are therefore never proven buildable. NET.ARCH.async-validation covers only async play.
- Evidence: Age of Empires DE and StarCraft II use lockstep with a relay or host. Fighting games use relay-based rollback (Steam Datagram Relay-class). Ranked lockstep results cannot be trusted by hash vote between two peers (A4 and L47 in this framework), so a server-side re-simulation or observer is needed.
- Proposed change: add the `online-lockstep`/`online-rollback` profiles to dedicated-server, or add a lean `command-relay-server` skill or capability. Add configurations `rts-2d-lockstep-server` and `fighting-2d-rollback-relay-server` (server-host), and a headless observer/validator client for lockstep. Extend NET.ARCH.async-validation to ranked lockstep and rollback replays.

### K-NET-3 · major · omission
- Target: NET.TRANS.nat, NET.SESS.server-browser, NET.SRV.community-hosting, network-transport non_responsibilities ("Relay service operation")
- Finding: only operation of the relay is external. No skill or capability owns the server-side implementation of the relay (a packet forwarder that validates auth tickets and hides addresses) or of the master/directory server. Yet server-browser names a master server, and community-hosting requires listing and auth without a first-party backend. Platform-SDK relays are only backends registered to C-NETLINK. An engine built from scratch has none for P2P, rollback or community-hosted play.
- Evidence: Valve SDR and master server, Photon relay and Unity Relay, and Nakama are all shipped components with server-side code. L46 (relay-shielded addressing) is otherwise unimplementable without a reference relay.
- Proposed change: add a capability NET.TRANS.relay-service (reference relay and directory implementation, stateless, ticket-validating, DoS-hardened) owned by network-transport with contributors dedicated-server and net-session. Build it in a server-host configuration and register its inputs (relay control messages) in untrusted-inputs.

### K-NET-4 · major · scale-down
- Target: NET.SRV.community-hosting, PLAT.SRV.host-os, platform-desktop, all server configurations (platforms ["server-host"])
- Finding: every server configuration is built only for `server-host` (Linux and containers). platform-desktop targets client, headless-client, server and tools but is never part of a server-target build. Player-hosted dedicated servers commonly run on Windows PCs, and the redistributable build in NET.SRV.community-hosting is unproven there, including the sockets, IO, PAL, crash and update paths.
- Evidence: Valheim, Palworld and Rust community servers and the Steam dedicated-server tools ship Windows builds; Valve's SteamCMD serves both platforms.
- Proposed change: add a `community-server-pc` configuration (profiles online plus ugc, target server, platforms ["pc", "server-host"]), or extend the platforms of indie-2d-online-moddable-server, and claim it in M4.

### K-NET-5 · major · overlap
- Target: C-REWIND, C-PHYS, C-ANIM, PHY.ARCH.rewind, NET.PRED.rewound-world-query, physics-2d, character-movement, vehicle-physics
- Finding: "collider history" is specified in C-PHYS and PHY.ARCH.rewind. "Pose history" is specified in C-ANIM. Both are specified again as providers in C-REWIND and NET.PRED.rewound-world-query. Only rigid-body-dynamics (lite3d/std3d), animation-runtime and gameplay-systems-toolkit consume C-REWIND, all optionally. physics-2d, character-movement (capsule history) and vehicle-physics do not consume it. Nothing proves that a lag-compensation configuration contains a provider for the hit volumes it rewinds. In 2D, physics-2d supplies the only collider store.
- Evidence: Valve's lag compensation in the Source Multiplayer Networking docs rewinds player hit volumes and pose. Overwatch (GDC 2017) rewinds hitbox poses per tick. The capsule is the most common rewound volume.
- Proposed change: make C-REWIND the only definition (C-PHYS and C-ANIM point to it). Add C-REWIND consumption to physics-2d, character-movement and vehicle-physics. Mark C-REWIND as needs_implementer where NET.PRED.lagcomp is claimed, so the config-closure check proves a provider exists per platform and config.

### K-NET-6 · major · other
- Target: NET.ARCH.distributed-authority (maturity E), NET.REP.physics-bodies ownership hand-off, legacy L43
- Finding: shared or per-object client authority is the pattern L43 calls legacy, yet it is registered as E with only `replication` as contributor. It has no anti-cheat-integrity contributor, no eligibility rule (cosmetic, co-op, non-competitive), and is not among L43's stance_capabilities. Client-owned props and vehicles have the same gap. The legacy catalogue could then be satisfied while client authority is chosen by habit.
- Evidence: Unity Netcode for GameObjects distributed authority and Photon Fusion Shared mode explicitly trade cheat resistance for convenience and are recommended only for co-op or low-stakes games. Rust and Fortnite server-validate client-owned vehicles.
- Proposed change: add anti-cheat-integrity and network-architect as contributors, and add NET.ARCH.distributed-authority to L43's stance_capabilities. Add an ADR condition (allowed only with a declared trust tier and C-INTEGRITY validators on state deltas). Re-label the maturity as M for competitive use.

### K-NET-7 · major · dependency-error
- Target: C-NETSESSION, determinism-replay, NET.SESS.baseline, NET.SESS.reconnect
- Finding: the C-NETSESSION summary says the participant interface (provide_baseline, on_reconnect) is "implemented by replication, prediction-rollback and determinism-replay". determinism-replay has no consumes or implements edge to C-NETSESSION. Baseline hand-off via C-SNAPSHOT plus command catch-up therefore has no provider on the contract path in lockstep and rollback configurations, where replication is absent. Direct consumption from the C-DET/C-SNAPSHOT layers would be upward, so the edge must go through the C-REPLAY module.
- Evidence: contracts.json C-NETSESSION vs skills.json determinism-replay (consumes ["C-MATH","C-TASK","C-SER@C-SNAPSHOT","C-FRAME@C-SNAPSHOT"]). Late-join in lockstep needs a snapshot provider (StarCraft II, Factorio map download).
- Proposed change: add "C-NETSESSION@C-REPLAY" to determinism-replay consumes (module-level, layer 3), or move the participant role to prediction-rollback and correct the C-NETSESSION text.

### K-NET-8 · minor · dependency-error
- Target: NET.TRANS.web, network-transport profiles, mobile-async-client, mobile-async-validator, NET.ARCH.async
- Finding: NET.TRANS.web names WebSocket as the fallback "for async/turn-based play". network-transport is not in the online-async profile, so mobile-async-client and mobile-async-validator do not contain it. The async client-to-backend channel (HTTPS, WebSocket, push) and its versioning and auth are covered only by PAL's HTTP client and NET.ARCH.versioning. The wording places async transport in a skill the async configurations lack.
- Evidence: capability profile gating in configurations; check.py cannot see this because the capability has no profile tag.
- Proposed change: either add "online-async" to network-transport's profiles (reduced module), or move the WebSocket/async clause into NET.ARCH.async under online-services-liveops, and state that the async channel is HTTPS via C-PAL.

### K-NET-9 · minor · maturity-error
- Target: NET.TRANS.web (E), NET.TRANS.quic (M), radar "QUIC/WebTransport game transport"
- Finding: the E-labelled NET.TRANS.web prefers "WebTransport datagrams" while the radar and NET.TRANS.quic call QUIC/WebTransport emerging (M) with a revisit condition. An established row depends on an emerging technology without the M fallback.
- Evidence: WebTransport reached cross-browser support only recently and has no long-run production record, while WebRTC DataChannel with unreliable mode (Google Stadia-era and Agar.io-class web games) is established.
- Proposed change: split the row. Keep WebRTC unreliable channels and WebSocket at E. Move the WebTransport preference to NET.TRANS.quic (M) with the radar fallback WebRTC.

### K-NET-10 · minor · maturity-error
- Target: docs/06-gap-analysis.md row A5, NET.ARCH.meshing (X), radar "Seamless server meshing"
- Finding: the hand-written gap analysis says meshing is "`emerging` (M) in data and radar". The data and radar say X, experimental. The stale text tells the phase-2 owner that meshing is a production option.
- Evidence: capabilities.json and radar.json both give class X with two-postmortem revisit condition.
- Proposed change: correct A5 to X (experimental, opt-in profile) or change the data if M is intended.

### K-NET-11 · minor · overlap
- Target: NET.ARCH.versioning, NET.SESS.handshake, NET.TRANS.dos, NET.TRANS.crypto, NET.REP.compat, NET.SESS.auth
- Finding: "handshake" appears in five rows with three owners. The pre-auth wire sequence (cookie or challenge, crypto handshake, auth ticket, version and window check, capability and layout negotiation) has no single owner of the order or state machine. That is the most attacked surface.
- Evidence: QUIC and DTLS cookie exchange followed by an application handshake is the standard layering; ordering errors give amplification and pre-auth resource-exhaustion bugs.
- Proposed change: assign the composite connect state machine to NET.SESS.handshake, with the other rows declared as steps of it. Add a conformance case in C-NETSESSION that no state is allocated before the challenge passes.

### K-NET-12 · minor · overlap
- Target: NET.SESS.host-mode, NET.SESS.host-migration
- Finding: NET.SESS.host-mode's name includes "& host migration" while NET.SESS.host-migration is a separate row with the same owner. Two rows describe one deliverable.
- Evidence: capabilities.json rows.
- Proposed change: remove "& host migration" from NET.SESS.host-mode.

### K-NET-13 · minor · omission
- Target: NET.ARCH.budgets, PRF.METH.budgets, ARCH.REQ.hardware-tiers, NET.TRANS.simulation
- Finding: hardware tiers define only server instance classes. Network budgets are stated as players, entities and bandwidth, with no client link classes (cellular and metered, home broadband, console limits) or listen-host uplink. Bandwidth per connection for coop-3d-listen-client is bounded by the host's home upload divided by peers, and mobile has data caps and radio-state costs. Budgets per configuration are not tied to the link-condition trace corpus.
- Evidence: Overwatch GDC 2017 and Rocket League listen and mobile bandwidth figures; console cert rules on bandwidth and NAT type.
- Proposed change: extend NET.ARCH.budgets to per-configuration budgets per link class (downlink, uplink, host uplink share, radio-wake cost), keyed to the NET.TRANS.simulation trace classes and checked by PRF.NET.bandwidth.

### K-NET-14 · minor · scale-down
- Target: indie-2d-online-web-client, indie-2d-online-moddable-server, lite-3d-mobile-openworld-online-client, sandbox-online-server, milestones M4/M5
- Finding: client and server configurations are not paired. The web client has no `ugc` while the only matching server does, so content-set agreement (NET.SESS.content-set) is never exercised. lite-3d-mobile-openworld-online-client has no server counterpart, and sandbox-online-server has no client configuration with sandbox and online.
- Evidence: configurations in skills.json.
- Proposed change: add an optional `pairs_with` field to configurations. Add a `sandbox-online-client` and a note that the mobile client is served by online-3d-server, and check in check.py that every online client names a claimed server.

### K-NET-15 · minor · omission
- Target: NET.TRANS.qos-probe, untrusted-inputs.json
- Finding: probe replies from regions, data centres and relays are spoofable UDP responses that steer matchmaking region choice. They are not registered as an untrusted input (unlike lan-discovery and server-list-entries).
- Evidence: registry lists lan-discovery, server-list-entries, packets but no probe replies.
- Proposed change: register `qos-probe-replies` (validating owner network-transport, size, rate and signature limits, harness fuzzing).

### K-NET-16 · minor · omission
- Target: NET.PRED.lagcomp, L43
- Finding: NET.PRED.lagcomp has no contributors. The rewind cap, per-weapon hit-registration policy and validation that L43's stance ("bounded-rewind validation") depends on cross anti-cheat-integrity, gameplay-systems-toolkit and physics-architect.
- Evidence: Valve caps rewind (sv_maxunlag 1s); Overwatch and CS2 sub-tick bound and audit rewind.
- Proposed change: add contributors anti-cheat-integrity, gameplay-systems-toolkit and physics-architect. State the maximum rewind window as a budget in NET.ARCH.budgets.
