### K-TOOLS-1 · major · dependency-error
- Target: C-EDCMD, C-EDHOST, C-GRAPH, editor-architect, milestones M0/M1/M2; C-SER, C-REFL, C-WORLD, C-ECS, C-ANIM, C-GAMEDATA
- Finding: Editor contracts are drafted and frozen only at M2 (C-EDCMD/C-EDHOST both draft and freeze in M2; C-EDVIEW/C-GRAPH/C-VCS freeze M3), yet about 30 M0/M1 skills (material-system, render-2d-vector, animation-graphs, cinematics-sequencer, world-data-model, gameplay-data, narrative-dialogue, procedural-generation, ui-architect, localization-i18n, vfx-particles, scripting-runtime...) already carry tool_consumes of them, and the data contracts the editor depends on (C-SER, C-REFL, C-WORLD, C-ECS, C-ANIM, C-GAMEDATA, C-ASSET, C-IMPORT) freeze at M1 with no editor consumer having exercised them. Editor-driven requirements (per-property change journal, stable ids, override/prefab layering, diffable canonical form, undo scopes) are found only after the freezes.
- Evidence: Every engine with an editor retrofitted these late at high cost (Unity SerializedObject/undo layering, UE transaction and package/actor-file changes for One File Per Actor). The M1 exit is playable indie reference games with hot reload and localization but no authoring path other than hand-edited data.
- Proposed change: Put editor-architect in M1 and draft C-EDCMD/C-CMD (transactions, journal, selection, headless commandlet authoring loop, ED.ARCH.headless/separation/transactions) at M0/M1. Require editor-architect as a mandatory reviewer of the C-SER, C-REFL, C-WORLD, C-ASSET and C-ECS freezes, with an "editor-conformance" freeze criterion (round-trip do/undo/redo over the contract's data). Keep the full GUI editor at M2.

### K-TOOLS-2 · major · obsolete-assumption
- Target: ED.ARCH.transactions
- Finding: The capability text says "each undo step stores a full copy of the affected scene or asset state". That is snapshot-based undo, the pattern L38 forbids (default stance: serializable diff-based commands). check.py only matches the exact phrase "snapshot-based undo", so the wording evades the contradiction check. C-EDCMD's own summary says "serializable, diff-based commands", so the row contradicts its contract. Full copies do not scale to 10^6-object worlds or multi-user merge, and cannot feed the journal used for recovery.
- Evidence: UE FTransaction stores property-level deltas; Unity's Undo.RecordObject snapshots are a known scaling and merge limitation; CRDT/OT editing needs operation logs, not states.
- Proposed change: Reword to "diff/command-based transactions with inverse operations; snapshots only as checkpoints for journal compaction". Add contradiction_terms "full copy" and "stores a copy" to L38.

### K-TOOLS-3 · major · scale-down
- Target: configurations (tools), voxel-worlds, WLD.TOOL.voxel, fluid-simulation, systems-simulation, CNT.IMP.splats, hwrt profile, online-async
- Finding: Add-on profiles `sandbox`, `hwrt`, `online-async` and `experimental` appear in no tools-target configuration. voxel-worlds (sandbox-only) is in the M2 skill set but in no tools closure, so WLD.TOOL.voxel and the sandbox side of PHY.TOOL.fluids/GAM.TOOL.sim-debug are never proven to close with the editor. Experimental tool-side capabilities (CNT.IMP.splats, other X rows) and RT-only lighting authoring have no tools configuration, so their opt-in path is proven for client only.
- Evidence: Terraria/Minecraft-class tooling is a distinct authoring stack (brush editing, pre-generated structures); tool closure differs from client closure.
- Proposed change: Add `sandbox-2d-tools` (min2d+sandbox), `rt-required-3d-tools` (std3d+hwrt) and `aaa-experimental-tools`, claimed at M2/M6 respectively; add `online-async` to a tools config or mark it tool-neutral.

### K-TOOLS-4 · major · omission
- Target: CNT.IMP.*, RND.TOOL.tilemap-sprite, RND.2D.tilemaps, ANM.RT.2d-import
- Finding: No importer capability covers the source formats indie 2D teams actually author in: layered sprite/animation sources (Aseprite, Krita/PSD layers to atlas plus animation tags), sprite-sheet import, and tile-level editors (Tiled TMX, LDtk, Ogmo). CNT.IMP.textures lists only EXR/PNG/TIFF/PSD; tilemaps have runtime and painting tools but no import path; 2D skeletal import lives in a runtime skill (animation-runtime) rather than under C-IMPORT. The min2d scale-down path therefore has no route from the artists' tools into the cook.
- Evidence: Aseprite, Tiled and LDtk are the de facto interchange of 2D indie production (Godot, Unity, GameMaker and Defold all ship or plug in importers).
- Proposed change: Add CNT.IMP.sprites-2d (layered sprite/anim-tag import) and CNT.IMP.tilemaps (Tiled/LDtk) owned by asset-import-interchange with contributors render-2d-vector, physics-2d; route ANM.RT.2d-import through C-IMPORT. Also add font source import/MSDF atlas generation as a cook step, since UI.TXT.fonts is runtime-only.

### K-TOOLS-5 · major · omission
- Target: NET (network-architect, replication, net-session), NET.DBG.*, ED.ARCH.pie-net
- Finding: The networking domain has no authoring path. There is no *.TOOL capability for replication and relevancy authoring (per-class/component replication conditions, priority, relevancy/cull, RPC/authority annotations, ownership), and NET.DBG.visualize/NET.DBG.profiler/NET.DBG.session-replay viewers are owned by runtime skills whose tool_consumes are empty, so they have no declared editor hosting through C-EDHOST/C-EDVIEW. The user-facing-domain authoring-path proof passes only because the check is name-pattern based.
- Evidence: UE exposes replication settings and Network Profiler in the editor; Unity NGO/Netcode and Overwatch-style ECS netcode need per-component ghost/replication authoring; lockstep/rollback games need input-delay and rollback-window tuning UI.
- Proposed change: Add NET.TOOL.replication-authoring (schema/relevancy/priority settings over C-REFL annotations, with validation via CNT.VAL.submit-gate), NET.TOOL.net-debug (hosts NET.DBG.* viewers) owned by replication with contributors editor-ui-framework, and give replication/net-session tool_consumes of C-EDCMD/C-EDHOST.

### K-TOOLS-6 · major · missing-contract
- Target: ED.ARCH.pie, ED.ARCH.pie-net
- Finding: PIE contributors list only world-editor-viewport. PIE isolation depends on input focus/capture routing and device ownership (input-system), audio focus/listener/mixer isolation (audio-architect), save-profile and persistence sandboxing so a PIE session cannot write real saves or player data (persistence-save), online-service isolation via emulation (online-services-liveops, PLAT.SVC.emulation), state preservation on reload (hot-reload-iteration) and simulate-vs-play state restore (ecs-runtime CORE.ECS.snapshot). World/physics/frame multi-instance rows exist, but nothing forces these owners to coordinate through the PIE owner's contract.
- Evidence: PIE data-corruption and stale-global bugs are classic (Unity domain-reload-off static state, UE PIE writing to config/save; audio bleed between PIE and editor previews).
- Proposed change: Add contributors input-system, audio-architect, persistence-save, online-services-liveops, ecs-runtime, hot-reload-iteration to ED.ARCH.pie, and state in C-EDCMD/C-EDPREVIEW the PIE-isolation obligations (no process-global state, sandboxed profile, emulated services).

### K-TOOLS-7 · minor · timing / dependency-error
- Target: C-EDCMD, C-EDIT, C-CMD (milestones M2, M4, M5)
- Finding: C-EDIT is documented as sharing its command schema with C-EDCMD, but C-EDCMD freezes at M2 while C-EDIT is drafted at M4 and frozen at M5. The shared schema (permissions, per-creation budgets, network replication of edits) freezes before its second consumer exists.
- Evidence: freeze rule requires an owner and one consumer; a shared schema needs both consumers.
- Proposed change: Move C-CMD schema freeze after a C-EDIT prototype, or freeze C-EDCMD's editor-only layer at M2 and the shared C-CMD command schema at M5 with a compatibility ADR.

### K-TOOLS-8 · minor · omission
- Target: ml-inference-runtime, ML.RT.packaging, CNT.COOK.gpu-steps, ED.AI.evaluation
- Finding: The ml profile has no authoring or asset tool path: no importer for model formats (ONNX-class), no model-asset inspector, quantization/backend preview, tolerance-report UI, or dataset management surface. ml-inference-runtime has no tool_consumes.
- Evidence: Unity Sentis/Inference Engine and UE NNE import and inspect ONNX models in-editor.
- Proposed change: Add ML.TOOL.model-assets (import, inspect, quantize, per-backend preview) owned by ml-inference-runtime with contributors editor-ui-framework, asset-import-interchange.

### K-TOOLS-9 · minor · omission
- Target: online-services-liveops, PLAT.SVC.remote-config, NET.SRV.admin
- Finding: Live-service content (feature flags, event schedules, store/catalog and economy tables, staged rollouts) has runtime boundaries but no authoring/validation/publish tool path, and no link to CNT.VAL.submit-gate or ED.COLLAB.review for backend-delivered data.
- Evidence: Live-service studios ship dedicated liveops tooling; bad remote-config pushes are a common outage class.
- Proposed change: Add PLAT.SVC.liveops-authoring (schema-validated config/catalog editing, diff, staged publish, rollback), contributors gameplay-data, editor-ui-framework, content-pipeline-architect.

### K-TOOLS-10 · minor · overlap
- Target: ED.ARCH.process, ED.ARCH.async-jobs
- Finding: Both rows define asynchronous cancellable editor jobs with progress (process: "asynchronous cancellable editor jobs with progress; UI thread never blocks"). L37 points only to async-jobs, so process carries a duplicate, unowned-by-legacy-check stance.
- Evidence: same owner, same sentence.
- Proposed change: Reduce ED.ARCH.process to the in-/out-of-process runtime ADR and crash isolation; leave job semantics to ED.ARCH.async-jobs.

### K-TOOLS-11 · minor · scale-down
- Target: ED.WORLD.blockout, ED.WORLD.mesh-paint, ED.WORLD.gizmos, ED.WORLD.splines, ED.WORLD.color-management, ED.UI.outliner
- Finding: These 3D-only or large-world editor capabilities carry no profile tags, so minimal-tools and indie-2d-tools inherit 3D manipulation, booleans/UV modeling, mesh painting and 10^6-object outliner scaffolding. Capability-level tags exist precisely for this and are used on ED.WORLD.partitioned.
- Evidence: tools scale-down goal; Tiled/LDtk-class 2D tools have none of these.
- Proposed change: Tag blockout, mesh-paint, splines(3D) and 3D gizmos [lite3d, std3d]; tag ED.WORLD.color-management [std3d] (HDR); tag ED.UI.outliner virtualization tier [openworld, team-mid] with a simple tree for small projects.
