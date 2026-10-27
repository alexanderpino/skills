# K-LEGACY round 4 findings

### K-LEGACY-1 · major · obsolete-assumption
- Target: CORE.FRAME.sim-schedule, ANM.ARCH.sync, C-FRAME, L01, docs/00 section 6 row 1
- Finding: CORE.FRAME.sim-schedule is worded "fixed sequence per tick; declared access used only for validation". That is the central sequential update loop (L01) reintroduced for the entire simulation, the most expensive part of the frame, under modern vocabulary. It also contradicts CORE.FRAME.access-model/phases ("ordering derived from declared access") and docs/00 section 6, which says "canonical simulation dependency order". No adr_exceptions entry exists and L01's stance_capabilities do not include it, so check.py cannot see the conflict. ANM.ARCH.sync inherits the wording ("within the canonical simulation schedule").
- Evidence: Determinism needs a reproducible order, not a fixed sequence. A DAG derived from access declarations with a stable tie-break (Unity DOTS system ordering, Bevy schedules with ambiguity detection, Overwatch ECS determinism talk GDC 2017) is deterministic and overlaps independent subsystems. A fixed sequence serializes physics, animation, AI and navigation on hybrid many-core CPUs.
- Proposed change: reword to "canonical simulation dependency order: partial order derived from C-FRAME access declarations plus declared hard edges (e.g. input, gameplay, physics, animation, root motion), deterministic tie-break; a total fixed sequence only per-domain at determinism L2+ by ADR". Add CORE.FRAME.sim-schedule to L01 stance_capabilities and add contradiction_terms such as 'fixed sequence per tick'. Align C-FRAME summary and ANM.ARCH.sync.

### K-LEGACY-2 · major · omission
- Target: legacy-patterns.json (new pattern), RND.GEO.precomputed-visibility, RND.GI.baked, RND.GI.lightmap-uv, RND.GI.bake-pipeline, WLD.MODEL.travel
- Finding: The catalogue has no entry for Quake-lineage "static world" assumptions: baked PVS/portal visibility and lightmap-only lighting as the base. Both are listed as plain E capabilities with no tier restriction or stance. They conflict with destruction (PHY.DEST), dynamic time of day (C-LIGHTENV), runtime PCG and user-generated worlds (C-EDIT), and they force full re-bake (L41 covers only the cook side).
- Evidence: Modern open-world engines (UE5 Lumen/Nanite, Frostbite, RE Engine) default to dynamic GI and GPU occlusion. Baked GI and PVS are retained as low-tier, mobile and stylized fallbacks (e.g. Unity Progressive Lightmapper on mobile).
- Proposed change: add L75 "Baked static visibility/lighting as the world model" with the stance "dynamic GI and GPU/HZB occlusion on capable tiers; baked GI/PVS is a per-tier fallback with dynamic-object and invalidation rules (RND.ARCH.invalidation)", owner render-architect, stance_capabilities RND.GI.baked and RND.GEO.precomputed-visibility. Reword both capabilities to say "tier fallback for lite3d/static-world products".

### K-LEGACY-3 · major · omission
- Target: legacy-patterns.json (new patterns), CORE.JOBS.thread-model, NET.TRANS, GAM.SAVE, CORE.FRAME.time
- Finding: The catalogue misses several concrete legacy patterns whose stances are only implicit. (a) Fixed thread-per-subsystem models (physics thread, animation thread, network thread, thread-per-connection blocking sockets on servers). L03 covers only game/render. (b) Wall-clock and sleep-based gameplay timers (Delay/Sleep/Timer by real time), tied to L30 only for the step. L57 covers only tests. (c) Fixed hard capacity limits (max actors/lights/emitters/connections compiled in). (d) Synchronous save and autosave that hitch the frame (only L64, the schema, is listed).
- Evidence: Thread-per-subsystem is the pre-2015 engine layout (Unreal 3, early Source). Task-based engines (Destiny, Frostbite, id Tech 6+) moved off it. Save hitches are a common certification and quality bug class (Xbox and PlayStation TRC async-save guidance). Compiled-in caps break scale-up and scale-down.
- Proposed change: add L75+ entries: "Fixed per-subsystem or per-connection threads" (stance: pool plus pinned lanes, owner job-system-task-graph, CORE.JOBS.thread-model); "Wall-clock gameplay timers" (game-time timers on time domains, CORE.FRAME.time); "Compiled-in capacity caps" (budget-declared, config-sized pools, CORE.MEM.budget-enforcement); "Synchronous save/autosave" (async atomic save with snapshot, GAM.SAVE.atomic). Add contradiction_terms for each.

### K-LEGACY-4 · minor · wrong-boundary
- Target: L27, ARCH.GOV.adr, legacy-patterns.json
- Finding: L27 packs two new dogmas ("ECS for everything" and "GPU-driven everywhere") into one pattern whose only stance capability is ARCH.GOV.adr. It cannot be checked against the capabilities that actually carry either stance (CORE.OBJ.hybrid, RND.ARCH.submission-strategy). Other new dogmas are unrecorded: "async/decoupled everything" (PHY.ARCH.async is E although rollback and determinism need synchronous stepping), "ML or neural techniques replacing analytic ones by default" (RND.GI.neural-cache X, RND.TEX.ntc X, ML.RT.*), and "server meshing or cloud-first by default" (NET.ARCH.meshing M).
- Evidence: The mission brief names "new dogma" explicitly. Only the ECS and GPU-driven forms are in the catalogue and neither is anchored to the owning capabilities.
- Proposed change: split L27 into L27a (ECS, stance CORE.OBJ.hybrid, CORE.ECS.bridges) and L27b (GPU-driven, RND.ARCH.submission-strategy), and add "neural/ML by default" and "async-by-default physics" dogma entries. Each needs an evidence-based-ADR stance and an owner.

### K-LEGACY-5 · minor · wrong-boundary
- Target: C-SEQ, C-ANIM, C-PHYS, C-ID, L19
- Finding: L19 (immediate observer callbacks) anchors only CORE.OBJ.events, and its contradiction_terms are a narrow regex. Contract text reintroduces callback semantics: C-SEQ "event/track callbacks", plus C-ANIM "animation events" and C-PHYS "contact events" with no delivery-mode statement. C-ID lists "events" under identity, a placement leftover. Nothing forces these producers to use the deferred, batched delivery at declared consumption points.
- Evidence: Anim notifies and sequencer event tracks invoking gameplay code synchronously mid-evaluation are the classic mutation-during-iteration and non-determinism source (UE anim notifies, Unity animation events). Deferred event streams are the established remedy.
- Proposed change: reword C-SEQ to "event/track outputs delivered as batched events via C-FLOW/CORE.OBJ.events"; state the delivery mode in C-ANIM and C-PHYS; add these capabilities to L19 stance_capabilities, and add 'callbacks?' to L19 contradiction_terms with exceptions; remove "events" from C-ID.

### K-LEGACY-6 · minor · omission
- Target: CNT.ID.registry, C-ASSET, legacy-patterns.json
- Finding: There is no scale stance for the asset registry. As worded ("Asset registry & queries"), a runtime registry that is resident in full or scanned at boot is allowed. At AAA open-world scale (millions of assets) this is the known Unreal AssetRegistry boot and memory problem. The catalogue lists no pattern for "whole-project registry resident or enumerated at startup".
- Evidence: UE5 moved to on-demand asset registry state and cook-time registry chunking. Open-world projects report multi-second scans and hundreds of MB of resident state.
- Proposed change: add a pattern "Full asset-registry scan or residency at boot" with the stance "cooked, chunked, on-demand registry; queries served from streamed indexes; editor registry incremental (ED.ARCH.scale)", owner content-pipeline-architect, stance_capabilities CNT.ID.registry. Reword CNT.ID.registry and C-ASSET to say so.

### K-LEGACY-7 · minor · wrong-boundary
- Target: WLD.MODEL.document, WLD.MODEL.travel, C-PCG
- Finding: Wording leaves the "level" as an authoritative unit ("World / level document format", "Level transitions & seamless travel", C-PCG "per cell/chunk/level"), while WLD.MODEL.strategy and L18/L39 stance the world as partitioned data. This leaves a hole for level-as-file to re-enter as the default authoring and travel unit for 3D. It would need a "level" definition as one load-unit configuration, distinct from a cell.
- Evidence: The World Partition and One File Per Actor transition in Unreal exists precisely because level-as-file broke collaboration and streaming.
- Proposed change: rename to "World document (unit or partitioned)" and "World-unit transition and seamless travel"; add "level" to L39 contradiction_terms with the exception for minimal 2D configurations (WLD.MODEL.unit-load).

### K-LEGACY-8 · minor · other
- Target: CORE.ECS.singletons, C-ECS
- Finding: "Shared / singleton components & resources" mirrors the hidden global (L08/L32). There is no statement that singletons are world-scoped and reachable only through a world handle. CORE.OBJ.world-instances says that only for world state generally, and the ECS capability could contradict it.
- Evidence: Bevy Resources and Unity singleton entities are per-World. Process-global ECS singletons block multi-world PIE, servers hosting many instances, and test isolation.
- Proposed change: reword to "World-scoped shared components/resources (no process-global singletons)"; add the capability to L32 stance_capabilities.
