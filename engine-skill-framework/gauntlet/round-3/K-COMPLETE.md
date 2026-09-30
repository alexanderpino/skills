# K-COMPLETE — Completeness Critic, round 3

Mandate: engine capabilities or disciplines missing from `data/capabilities.json`. Every finding has type omission. Before reporting, I searched ids, names, skill purposes, contracts and radar for each item. The docs/06 §C scope decisions (backend services, game-specific content, NDA parameters) are respected.

### K-COMPLETE-1 · major · omission
- **Target:** RND.LIGHT (direct-lighting-shadows); profiles lite3d, min2d; configurations lite-3d-mobile-client, lite-3d-portable-console-client, xr-standalone-client
- **Finding:** The map has no conventional shadow-map capability: no cascaded/directional shadow maps, and no spot/point shadow atlas or cube shadows. RND.LIGHT.vsm and RND.LIGHT.rt-shadows are both profiled `std3d`, so lite3d configurations (mobile, portable console, standalone XR) have only contact shadows and baked lighting for dynamic shadowing. The `direct-lighting-shadows` purpose says "cascaded … shadows", and the radar fallback says "Clustered lighting + shadow maps", but neither points to a capability row. (Sweep 1: shipped engines. Unity URP/HDRP, Godot 4, UE5 mobile renderer, Snowdrop and Decima all ship CSM plus local-light atlases, and VSM is UE5 desktop/console only.)
- **Evidence:** VSM needs sparse/virtual page tables and GPU-driven culling. That is impractical on TBDR mobile, Switch-class and Quest-class GPUs, where CSM with 2–4 cascades, texel snapping and cached static cascades is the established technique (Valient, "Stable Rendering of Cascaded Shadow Maps", ShaderX6; Engel, PSSM; Unity URP / UE mobile renderer docs). The radar fallback for VSM refers to a capability that doesn't exist.
- **Proposed change:** Add `RND.LIGHT.shadow-maps` "Conventional shadow maps: cascaded directional (stabilized, cached static cascades), spot/point shadow atlas & cube maps, filtering (PCF/PCSS/EVSM class); lite3d default and std3d fallback", owner direct-lighting-shadows, E, no profile restriction. Point the radar VSM fallback at it.

### K-COMPLETE-2 · major · omission
- **Target:** CNT.COOK / asset-cook-processors; AUD.DSP.codecs; RND.MEDIA
- **Finding:** There's no cook step for audio or video. CNT.COOK has processors for textures, meshes, images and geometry. AUD.DSP.codecs is runtime decoding. CNT.IMP.audio covers source formats only. Nothing owns:
  - per-platform audio encode (Opus/Vorbis/ADPCM/hardware codecs) with quality per tier, seek tables, stream chunking and sample-rate conversion, and loudness normalization at cook
  - video transcode for playback assets: codec and bitrate ladder per platform and tier, muxed audio/subtitle tracks, HDR metadata
  - runtime video encode for replay-to-clip export and movie-render output containers

  Every configuration, including indie-2d, ships audio. (Sweep 2: pipeline, cook stage. Sweep 1: UE audio cook/stream caching, Wwise/FMOD bank build, Unity AudioImporter per-platform settings, Bink/Video Toolbox encode.)
- **Evidence:** Audio is often the second-largest shipped payload. Platform hardware codecs (e.g., console hardware decoders) need encoder-side formats chosen at cook, and incremental-equals-clean determinism (CNT.COOK.incremental-equivalence) can't be enforced on a step that has no owner. `media-playback` hands off "producing video", but the only destination is ANM.CINE.movie-render, which says nothing about encoding.
- **Proposed change:** Add `CNT.COOK.audio` "Audio cook processor: per-platform/tier encode, SRC, loudness normalization, seek tables & stream chunking" (owner audio-dsp-mixing, contributor asset-cook-processors, E). Add `CNT.COOK.video` "Video transcode cook: per-platform codec/bitrate ladder, muxed tracks, HDR metadata" (owner media-playback, E). Add `RND.MEDIA.encode` "Runtime/offline video encode (clip export, movie-render output)" (owner media-playback, contributor cinematics-sequencer, E).

### K-COMPLETE-3 · major · omission
- **Target:** QA.CERT, PLAT.SVC, UI.FW (legal surfaces)
- **Finding:** Nothing owns the legal surfaces players see:
  - Terms of Service/EULA and privacy-policy presentation, with versioned acceptance records and re-acceptance gating on update
  - in-game display of third-party/OSS attribution notices required by MIT/BSD/Apache-NOTICE licences
  - contractual middleware logo and splash obligations

  QA.CERT.licenses stops at compliance and SBOM, and OBS.LOG.consent covers telemetry only. (Sweep 4: platform/legal/business.)
- **Evidence:** Apache-2.0 §4(d) and BSD/MIT require the notice to ship in a form end users can read. Online titles gate features on ToS acceptance and must prove which version each user accepted (GDPR Art. 7(1) burden of proof for consent). Store policies (Apple 5.1.1, Google Play User Data) require the privacy policy to be reachable in-app. Middleware licences (Havok, Bink, Wwise) carry logo-display clauses.
- **Proposed change:** Add `QA.CERT.legal-surfaces` "Player-facing legal surfaces: ToS/EULA/privacy-policy presentation, versioned acceptance records & re-acceptance gating, OSS attribution notices generated from the SBOM, middleware logo/splash obligations" (owner certification-compliance, contributors ui-architect, platform-services, privacy-data-protection, E).

### K-COMPLETE-4 · major · omission
- **Target:** PLAT.MOB, PLAT.XR (location-based play)
- **Finding:** There's no device geolocation capability: GNSS/fused location, geofencing, background-location permission and battery policy, or location privacy classes. There's also no geospatial/VPS localization (Earth-anchored content). CNT.IMP.geospatial covers cook-time ingestion only, and PLAT.XR.anchors covers local and shared anchors. (Sweep 3: genres. Location-based AR games such as Pokémon GO and Monster Hunter Now are a major mobile genre.)
- **Evidence:** Niantic Lightship VPS and ARCore Geospatial API (VPS + Streetscape Geometry) are production APIs. iOS CoreLocation "precise/approximate" and Android background-location rules are store-review gates. Location is a sensitive data class under GDPR/CPRA, and XC.SEC.data-rights lists "spatial" data but has no producer.
- **Proposed change:** Add `PLAT.MOB.location` "Device geolocation: fused location, geofences, background/approximate permissions, battery policy, location privacy class" (owner platform-mobile, contributor privacy-data-protection, E). Add `PLAT.XR.geospatial` "Geospatial/VPS localization & Earth-anchored content" (owner xr-runtime, M, with a radar entry).

### K-COMPLETE-5 · major · omission
- **Target:** INP.DEV.gamepads, INP.ACT, GAM.SYS
- **Finding:** The map doesn't cover analog stick processing (radial/axial deadzones, anti-deadzone, response curves, per-device calibration and drift compensation). It also has no aim-assist capability: target magnetism/friction/slowdown, predicted and server-validated in networked play, with fairness across input devices in crossplay (input-device reporting to matchmaking, detection of spoofed controllers). (Sweep 3: shooters and crossplay. Sweep 1: Frostbite/Destiny/Halo proprietary aim assist, Lyra aim-assist plugin, Unity/UE Enhanced Input modifiers.)
- **Evidence:** Aim assist is a shipping requirement for every console/crossplay shooter. It crosses input, gameplay, NET.PRED (it must be predicted consistently) and anti-cheat (Cronus/XIM adapters exploit it; CoD and Apex ship detection). Deadzone shape is a documented accessibility and quality issue ("Doing Thumbstick Dead Zones Right", Third Helix; Xbox Accessibility Guideline 107).
- **Proposed change:** Add `INP.ACT.stick-processing` "Analog stick deadzones, response curves, calibration & drift compensation" (owner input-system, E). Add `GAM.SYS.aim-assist` "Aim assist: magnetism/friction/slowdown, prediction-consistent & server-validated, per-input-device tuning and crossplay fairness signals" (owner gameplay-systems-toolkit, contributors input-system, prediction-rollback, anti-cheat-integrity, E).

### K-COMPLETE-6 · major · omission
- **Target:** NET.SESS, XC.EXT (modding-ugc), NET.SRV; configurations indie-2d-online-moddable-*, sandbox-online-server
- **Finding:** Community and player-hosted dedicated servers have no capability for:
  - redistributing the server binary to players
  - server config and ruleset files
  - internet server listing/browser registration (listing, query protocol, favourites)
  - join-time content/mod manifest negotiation and download ("download required mods on join")

  NET.SESS.handshake negotiates versions and capabilities, not content. NET.TRANS.local-network covers LAN discovery only. BLD.REL.end-of-service releases servers only at sunset. (Sweep 3: survival and sandbox games such as Minecraft, Rust, ARK, Valheim, Garry's Mod and CS2 community servers.)
- **Evidence:** Source/Source 2 (A2S query protocol, FastDL/Workshop auto-download), Unreal (online beacon/session settings), Minecraft (server.properties, resource-pack push) and Steam Game Server API all ship this. A moddable online configuration without join-time mod sync can't join a modded server, which is the configuration's reason to exist.
- **Proposed change:** Add `NET.SESS.content-sync` "Join-time content/mod manifest negotiation, download & verification via C-SIGN before load" (owner net-session, contributor modding-ugc, E). Add `NET.SRV.community-hosting` "Player-hosted dedicated servers: redistributable server build, config/ruleset files, listing registration & query protocol" (owner dedicated-server, contributors packaging-release-patching, online-services-liveops, E). Register the query protocol and the mod manifest in untrusted-inputs.json.

### K-COMPLETE-7 · minor · omission
- **Target:** UI.FW, PLAT.SVC.identity
- **Finding:** There's no embedded web-view capability (CEF/WKWebView/WebView2 class: news, store pages, help, surveys). There are also no external-browser and device-code OAuth flows for account linking on TV and console (RFC 8628). PLAT.SVC.identity names account linking but not the browser surface it needs. (Sweep 1: UE WebBrowser module. Sweep 4: account-linking flows.)
- **Evidence:** Web views are a large untrusted-input and security surface (script, cookies, navigation allow-lists). Apple ASWebAuthenticationSession and Android Custom Tabs are mandated for OAuth, not embedded views (RFC 8252).
- **Proposed change:** Add `UI.FW.web-view` "Embedded web view & external-browser/device-code auth flows (navigation allow-lists, isolation)" (owner ui-architect, contributors platform-services, security-engineering, E). Add a matching untrusted-inputs entry.

### K-COMPLETE-8 · minor · omission
- **Target:** RND.VFX
- **Finding:** Only GPU particle simulation exists. There's no CPU simulation path for low-count, sprite/2D, deterministic or gameplay-readable particles, or for CPU-submitted-tier budgets. (Sweep 1: Niagara CPU sim, Unity Shuriken (CPU) vs VFX Graph (GPU), Godot CPUParticles.)
- **Evidence:** GPU sim adds readback latency for gameplay-coupled effects. It isn't deterministic for rollback/lockstep configurations, and it costs dispatch/barrier overhead that dominates at low particle counts on mobile and web.
- **Proposed change:** Add `RND.VFX.cpu-sim` "CPU (SIMD) particle simulation path: low-count, deterministic & gameplay-readable emitters, same graph semantics" (owner vfx-particles, E).

### K-COMPLETE-9 · minor · omission
- **Target:** ANM.DEF, RND.CHAR, PHY.DEST, PHY.CTRL.vehicles
- **Finding:** The map has no visual damage models:
  - skinned-mesh dismemberment/slicing with cap geometry and physics hand-off
  - layered wound/damage masks on characters
  - vehicle body deformation and part detachment

  PHY.DEST covers rigid fracture only. (Sweep 3: action/horror/shooter and racing. Sweep 1: RE Engine, id Tech 7 GORE system, Dead Space (2023) peeling, Forza/GT/BeamNG damage.)
- **Evidence:** This needs data shared across skinning, rendering, physics, replication and ratings toggles (gore settings). By the docs/06 §C2 rule (formats shared across four or more domains), it belongs in the engine.
- **Proposed change:** Add `ANM.DEF.damage` "Skinned-mesh dismemberment/slicing & layered damage masks" (owner deformation-skinning, contributors character-rendering, destruction-fracture, E). Add `PHY.CTRL.vehicle-damage` "Vehicle body deformation & part detachment with replication" (owner vehicle-physics, E).

### K-COMPLETE-10 · minor · omission
- **Target:** AUD.CONTENT, AUD.SPAT; profile openworld
- **Finding:** Nothing owns world-placed emitter management at open-world scale: area, spline and volume emitters, ambience beds, emitter streaming with world cells and spatial culling before voice allocation. AUD.ARCH.voices virtualizes voices, not emitters. (Sweep 1: Wwise Spatial Audio rooms/portals and spline emitters, UE Soundscape and audio-gameplay volumes, Frostbite/Decima ambience systems.)
- **Evidence:** Open worlds place 10^5 or more emitters (rivers, wind, crowds). Without emitter partitioning, cost scales with placed emitters rather than audible ones, which conflicts with PRF.METH.asymptotics.
- **Proposed change:** Add `AUD.CONTENT.emitters` "World emitter management: area/spline/volume emitters, ambience beds, cell-streamed emitter partitions & pre-voice culling" (owner audio-content-runtime, contributors spatial-audio-acoustics, world-architect, E).

### K-COMPLETE-11 · minor · omission
- **Target:** BLD.CI.build-distribution, XC.SEC
- **Finding:** Nothing protects pre-release builds from leaks: no per-recipient forensic watermarking of builds and assets, no visible watermarks on QA, press and playtest builds, and no leak attribution. (Sweep 2: pipeline, beta/press stage.)
- **Evidence:** High-profile AAA leaks of pre-release builds and footage are common. Per-recipient watermarking (Irdeto/Denuvo forensic watermarking, visible tester-ID overlays) is standard for review and QA builds.
- **Proposed change:** Add `BLD.CI.leak-protection` "Per-recipient forensic & visible watermarking of distributed pre-release builds, leak attribution" (owner ci-cd-automation, contributor security-engineering, E).

### K-COMPLETE-12 · minor · omission
- **Target:** ED.UI / ED.WORLD
- **Finding:** There's no scene outliner/hierarchy panel: a virtualized entity list over millions of entities with folders, filtering, search, and partition/layer awareness. ED.WORLD.ld-utilities covers filters and layer visibility, not the hierarchy view. (Sweep 1: UE Outliner, Unity Hierarchy, Godot Scene dock.)
- **Evidence:** It's the primary navigation surface in every editor. Performance at world scale is a known pain point (UE5 World Partition outliner changes).
- **Proposed change:** Add `ED.UI.outliner` "Scene outliner: virtualized hierarchy/list over world and partition data, filtering, folders" (owner editor-ui-framework, contributor world-editor-viewport, E).

### K-COMPLETE-13 · minor · omission
- **Target:** ED.UI.ux
- **Finding:** The accessibility of the editor and creator tools themselves isn't mapped: screen-reader support, keyboard-only operation, colour-safe tool themes and scalable tool UI. UI.A11Y covers game UI only. (Sweep 5: engineering disciplines, tooling as thorough as runtime.)
- **Evidence:** Tools are workplace software, which brings employer accessibility obligations (ADA / Section 508 procurement / EN 301 549). Both Unity and Unreal have received documented editor-accessibility requests.
- **Proposed change:** Add `ED.UI.accessibility` "Editor & tool accessibility: screen-reader tree, keyboard-only operation, scalable/colour-safe themes" (owner editor-ui-framework, contributor accessibility, E).

### K-COMPLETE-14 · minor · omission
- **Target:** CNT.IMP
- **Finding:** There's no import path for vector and motion-graphics UI assets (SVG, Lottie/Rive), even though RND.2D.vector renders vector paths. (Sweep 1: Unity Vector Graphics, Godot SVG import, Rive runtime in shipped mobile UIs.)
- **Evidence:** Mobile and UI-centric (minimal-profile) games author UI in these formats, and they are untrusted-structured inputs in UGC contexts.
- **Proposed change:** Add `CNT.IMP.vector` "SVG & Lottie/Rive-class vector/motion-graphics import" (owner asset-import-interchange, contributor render-2d-vector, E).

### K-COMPLETE-15 · minor · omission
- **Target:** RND.GEO / WLD.PCG
- **Finding:** Spline-deformed meshes (roads, rails, pipes, cables, fences) are missing, as is road-network generation with terrain conforming and intersections. ED.WORLD.splines is a generic path editor. (Sweep 3: racing and open world.)
- **Evidence:** UE SplineMesh and Landscape splines, Unity Splines, and Houdini road tools are all used by racing and open-world titles. Road generation needs cooking, collision and navigation (GAM.AI.lanes) output from one source.
- **Proposed change:** Add `RND.GEO.spline-mesh` "Spline-deformed mesh instances (runtime & cooked)" (owner geometry-pipeline, E). Add `WLD.PCG.roads` "Road/rail network generation: terrain conforming, intersections, lane-graph export" (owner procedural-generation, contributors terrain, navigation-pathfinding, E).

### K-COMPLETE-16 · minor · omission
- **Target:** RND.ARCH.multiview, INP.DEV.specialty; profile vehicles
- **Finding:** Two sim-rig needs aren't covered: multi-display spanned output with per-display off-axis projection and bezel correction (triple screen), and head tracking (IR/webcam, TrackIR/OpenTrack) as a view input. (Sweep 3: sim racing and flight in the vehicles profile.)
- **Evidence:** iRacing, ACC, MSFS and DCS all ship triple-screen projection and head tracking. Single-frustum stretching across ultrawide screens is incorrect.
- **Proposed change:** Add `RND.ARCH.multi-display` "Spanned multi-display output with per-display off-axis projection" (owner render-architect, E). Add `INP.DEV.head-tracking` "Head-tracking devices as C-VIEW input" (owner input-devices-haptics, E).

### K-COMPLETE-17 · minor · omission
- **Target:** ED.COLLAB, ARCH.ORG
- **Finding:** Nothing owns backup and disaster recovery for the source/asset depot, derived-data caches, the ownership ledger and signing infrastructure (RPO/RTO, restore drills). BLD.REL.archival covers shipped builds only. (Sweep 5: engineering disciplines, operations of the development environment.)
- **Evidence:** An autonomous multi-agent program writes to the depot continuously, and losing the depot or ledger means losing the program's state. Restore drills are standard SRE practice (Google SRE book, chapter 26).
- **Proposed change:** Add `ED.COLLAB.backup` "Depot, ledger & cache backup and disaster recovery with restore drills" (owner collaboration-version-control, contributor program-orchestration, E).
