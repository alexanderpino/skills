"""Round-2 revision, part E: K-TOOLS, K-ARCH and K-LEGACY findings (editor contracts, authoring paths, wording
legacy, runtime automation, governance independence). The legacy catalogue itself is extended in r2_y."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _tool(ed, sid, tags, *extra):
    ed.use(sid, "C-EDCMD", "C-EDHOST", *extra, tool=True, tags=tags)


def apply(ed):
    # ================================================================ TOOLS
    t = "K-TOOLS-1"   # seed S05; residual: journal/out-of-process forms of commands
    c = ed.contract("C-EDCMD")
    ed.contract_set("C-EDCMD", requires=c["requires"] + ["C-IPC"],
                    summary="Serializable, diff-based commands and transactions, undo/redo scopes (world, asset "
                            "editor, PIE exclusion), selection, tool registration; journal feed for recovery and "
                            "multi-user; cross-process transactions.", tags=t)

    t = "K-TOOLS-2"
    ed.contract_add("C-EDVIEW", 5, "world-editor-viewport", "Viewport tool modes",
                    "Viewport tool modes, brush/stroke input and world raycast picking, gizmo/manipulator extension, "
                    "viewport overlays, 2D/ortho mode, preview-world creation.", requires=["C-EDCMD"],
                    conformance=True, tags=t)
    c = ed.contract("C-EDHOST")
    ed.contract_set("C-EDHOST", summary="Asset-editor host (panel embedding of preview worlds from C-EDVIEW), thumbnail "
                    "caching, inspector customization, shared curve/timeline widgets; every asset editor registers a "
                    "diff/merge provider (C-VCS).", tags=t)
    world_tool_owners = set()
    for d in ed.doc["cap"]["domains"]:
        for a in d["areas"]:
            for cap in a["caps"]:
                if a["id"] == "WLD.TOOL" or cap[0] in ("RND.TOOL.lighting", "RND.TOOL.tilemap-sprite",
                                                       "GAM.TOOL.nav", "RND.TOOL.decals") or a["id"] == "PHY.TOOL":
                    world_tool_owners.add(cap[2])
    for sid in sorted(world_tool_owners - {"world-editor-viewport"}):
        ed.use(sid, "C-EDVIEW", tool=True, tags=t)
    ed.note(t, "check.py: owners of WLD.TOOL capabilities must reach C-EDVIEW")

    t = "K-TOOLS-3"
    ed.contract_add("C-VCS", 5, "collaboration-version-control", "Version control",
                    "Workspace/changelist model, status and lock queries, checkout-on-write hook, semantic diff/merge "
                    "provider registration, sparse-sync payload requests, partner-scoped access.",
                    requires=["C-ASSET", "C-SER"], conformance=True, tags=t)
    for sid in ("editor-architect", "editor-ui-framework", "graph-editor-framework", "world-data-model",
                "gameplay-data", "ci-cd-automation"):
        ed.use(sid, "C-VCS", tool=True, tags=t)

    t = "K-TOOLS-4"
    ed.skill_set("ai-assisted-authoring", profiles=["aaa"], tags=t)
    ed.note(t, "tool contracts and tools configurations get milestones in r2_z")

    t = "K-TOOLS-6"
    for cid, prof in (("ED.ARCH.pie-net", ["online", "online-lockstep", "online-rollback"]),
                      ("ED.WORLD.partitioned", ["openworld"]),
                      ("PHY.TOOL.physics-asset", ["lite3d", "std3d"]),
                      ("CNT.IMP.scans", ["lite3d", "std3d"]), ("CNT.IMP.caches", ["lite3d", "std3d"]),
                      ("CNT.IMP.usd", ["lite3d", "std3d"]), ("CNT.IMP.materialx", ["lite3d", "std3d"]),
                      ("CNT.IMP.procedural", ["lite3d", "std3d"]), ("CNT.IMP.splats", ["aaa"]),
                      ("CNT.IMP.geospatial", ["openworld"])):
        ed.cap_set(cid, profiles=prof, tags=t)
    cfgs = ed.doc["skill"]["configurations"]
    cfgs["minimal-tools"] = {"profiles": ["minimal"], "target": "tools", "platforms": ["pc"],
                             "target_platforms": ["pc", "mobile", "web"]}
    cfgs["lite-3d-mobile-tools"] = {"profiles": ["lite3d"], "target": "tools", "platforms": ["pc"],
                                    "target_platforms": ["mobile"]}
    cfgs["online-3d-tools"] = {"profiles": ["std3d", "online"], "target": "tools", "platforms": ["pc"],
                               "target_platforms": ["pc", "console", "server-host"]}
    ed.note(t, "tools configurations minimal-tools, lite-3d-mobile-tools, online-3d-tools added")

    t = "K-TOOLS-7 K-PROD-9"
    ed.cap_set("ED.COLLAB.locking", profiles=[], tags=t)

    t = "K-TOOLS-8 K-COMPLETE-6"
    ed.contract_add("C-EDIT", 4, "modding-ugc", "Runtime edit session",
                    "In-game creation sessions: serializable commands (schema shared with C-EDCMD per "
                    "ED.ARCH.transactions), undo, selection, permissions and per-creation budgets, publish/version.",
                    requires=["C-SER", "C-ID", "C-FRAME"], conformance=True, tags=t)
    ed.cap("XC.EXT.player-creation", "Player-facing in-game creation mode (runtime editing subset, gamepad/touch "
           "placement, budgets, undo, publish/versioning) in client targets", "modding-ugc",
           contrib=["world-editor-viewport", "editor-architect"], tags=t)
    ed.cap("XC.EXT.ugc-discovery", "UGC browse/rate/play boundary with moderation & entitlement hooks", "modding-ugc",
           contrib=["online-services-liveops"], tags=t)
    ed.cap("XC.EXT.mod-editor", "Redistributable modder editor/SDK build (licence/NDA stripping, sandboxed tool "
           "plugins)", "modding-ugc", contrib=["packaging-release-patching", "platform-architect",
                                               "security-engineering"], tags=t)
    _tool(ed, "modding-ugc", t, "C-COOK")
    ed.use("gameplay-systems-toolkit", "C-EDIT?", tags=t)
    ed.cap_set("ED.ARCH.transactions", add_contrib=["modding-ugc", "collaboration-version-control",
                                                    "serialization-schema"], tags=t)

    t = "K-TOOLS-9 K-COMPLETE-18"
    ed.cap("ANM.TOOL.sequencer-editor", "Sequencer authoring: tracks, bindings, shots/sub-sequences, keyframing, "
           "preview & scrub", "cinematics-sequencer", contrib=["editor-ui-framework"], tags=t)
    ed.cap("ANM.TOOL.take-recorder", "Take recording of gameplay, live-link body/face mocap and virtual cameras into "
           "sequences", "cinematics-sequencer", contrib=["asset-import-interchange", "determinism-replay"], tags=t)

    t = "K-TOOLS-10 K-COMPLETE-19"
    ed.area("INP.TOOL", "Input tooling", tags=t)
    for cid, name, owner, con, prof in [
            ("AUD.TOOL.acoustics", "Reverb-zone & occlusion authoring, acoustic propagation baking",
             "spatial-audio-acoustics", [], None),
            ("AUD.TOOL.profiler", "Audio profiler/debugger (voices, buses, loudness)", "audio-architect", [], None),
            ("PHY.TOOL.cloth", "Cloth asset authoring & weight/max-distance painting", "cloth-deformables", [], None),
            ("GAM.TOOL.crowd-lanes", "Crowd zone & lane-graph authoring, spawners", "crowd-simulation", [], None),
            ("WLD.TOOL.voxel", "Voxel brush editing & pre-generated structures", "voxel-worlds", [], None),
            ("UI.TOOL.localization", "String-table editor, localization dashboard, in-context preview with "
             "pseudo-loc & overflow", "localization-i18n", [], None),
            ("INP.TOOL.actions", "Action/context mapping editor & device preview", "input-system", [], None),
            ("PHY.TOOL.fluids", "Fluid simulation setup & cache baking", "fluid-simulation", [], None),
            ("UI.TOOL.preview", "UI preview across resolution, safe area, locale & input device", "ui-architect", [],
             None),
            ("UI.TOOL.binding-debug", "UI data-binding debugger", "ui-architect", [], None),
            ("ED.WORLD.mesh-paint", "Mesh vertex-color & texture painting", "world-editor-viewport", [], None)]:
        ed.cap(cid, name, owner, contrib=con, profiles=prof, tags=t)
    for sid in ("spatial-audio-acoustics", "audio-architect", "cloth-deformables", "crowd-simulation", "voxel-worlds",
                "localization-i18n", "input-system", "fluid-simulation"):
        _tool(ed, sid, t)
    ed.use("spatial-audio-acoustics", "C-COOK", "C-EDVIEW", tool=True, tags=t)
    ed.use("voxel-worlds", "C-EDVIEW", tool=True, tags=t)
    ed.use("crowd-simulation", "C-EDVIEW", tool=True, tags=t)
    ed.note(t, "check.py: runtime skills in authoring workstreams own/contribute a *.TOOL capability or declare "
               "`authoring` justification")

    t = "K-TOOLS-11"
    ed.cap_set("ED.WORLD.preview-scenes", name="Isolated preview-world creation & lifetime (exposed via C-EDVIEW)",
               tags=t)
    ed.cap_set("ED.UI.asset-editor-host", name="Generic asset-editor host (tabs, preview-panel embedding, viewers, "
               "inspection modes)", tags=t)
    ed.cap_set("ED.UI.thumbnails", name="Thumbnail caching & display", tags=t)
    ed.cap_set("RND.ARCH.editor-rendering", name="Editor render features: GPU picking, selection outline, editor "
               "primitives", tags=t)

    t = "K-TOOLS-13"
    ed.cap_set("ED.COLLAB.multiuser", name="Session-based multi-user editing (small sessions)", tags=t)
    ed.cap("ED.COLLAB.concurrent-world", "Conflict-free concurrent world editing at studio scale (CRDT/OT class)",
           "collaboration-version-control", "M", profiles=["team-large"], tags=t)
    ed.doc["radar"]["entries"].append({
        "tech": "Conflict-free concurrent world editing", "class": "M", "capabilities": ["ED.COLLAB.concurrent-world"],
        "owner": "collaboration-version-control", "evidence": "CRDT editing outside games (Figma, Omniverse live layers)",
        "revisit": "Two engine postmortems at 100+ concurrent editors",
        "fallback": "Cell/actor-granular locks + one-file-per-object"})

    t = "K-TOOLS-14"
    ed.cap_move("PHY.TOOL.tuning", "PHY.TOOL.vehicle-tuning", tags=t)
    ed.cap_set("PHY.TOOL.vehicle-tuning", name="Vehicle tuning tools (telemetry graphs, tire/suspension editors)",
               owner="vehicle-physics", rm_contrib=["vehicle-physics", "character-physics"], profiles=["vehicles"],
               tags=t)
    ed.cap("PHY.TOOL.controller-tuning", "Character-controller tuning tools", "character-physics", tags=t)
    ed.cap_set("PHY.TOOL.2d-shapes", owner="physics-2d", tags=t)
    for sid in ("vehicle-physics", "character-physics", "physics-2d"):
        _tool(ed, sid, t)
    ed.use("physics-2d", "C-EDVIEW", tool=True, tags=t)
    s = ed.skill("physics-tools")
    ed.skill_set("physics-tools", purpose="Cross-cutting physics tooling: collision authoring, physics-asset/ragdoll "
                 "and constraint editors, the physics visual debugger/recorder and simulate-in-editor. Domain tuning "
                 "tools stay with their domain skills (vehicle, controller, 2D shapes, fracture, cloth, fluids).",
                 tags=t)

    t = "K-TOOLS-15 K-ARCH-16"
    s = ed.skill("editor-ui-framework")
    ed.skill_set("editor-ui-framework", purpose="Tool UI toolkit (docking, panels), reflection-driven inspectors, asset "
                 "browser, hosting of C-DEVUI panels in the editor, editor UX standards.", tags=t)
    ed.nonresp_add("editor-ui-framework", "Developer/debug immediate-mode UI", "visual-debugging-tools", tags=t)
    ed.skill_set("ui-architect", purpose="Game UI architecture (retained, change-notified view models with resolved "
                 "bindings), layout, styling, focus and navigation, animation, in-world UI, designer tool logic, UI "
                 "performance.", tags=t)
    ed.nonresp_add("ui-architect", "Developer/debug immediate-mode UI", "visual-debugging-tools", tags=t)

    t = "K-TOOLS-17"
    ed.cap("ED.ARCH.telemetry", "Studio tool telemetry: usage, slow tasks, crash and DDC/cook health dashboards",
           "editor-architect", contrib=["observability-telemetry", "crash-diagnostics",
                                        "loading-streaming-performance"], profiles=["team-large"], tags=t)

    # ================================================================ ARCH
    t = "K-ARCH-1"   # seed S07; residual: capability-reference check + GPU residency obeys arbiter
    ed.note(t, "check.py: every capability id quoted in a capability name must exist")
    _append(ed, "C-GPUMEM", "residency obeys arbiter pressure/shrink requests delivered through the C-RES pool "
            "registration hook.", t)

    t = "K-ARCH-4 K-LEGACY-3"
    ed.skill_set("gameplay-architect", purpose="Gameplay framework: rules and session state, players and data-oriented "
                 "control binding (control model per game by ADR B25), extension points and game-module structure, "
                 "game flow and transitions, local players.", tags=t)
    s = ed.skill("gameplay-systems-toolkit")
    ed.skill_set("gameplay-systems-toolkit", purpose=s["purpose"].replace("spawning and pooling",
                 "batched deferred spawning (pooling only where measured)"), tags=t)

    t = "K-ARCH-5"   # seed S01; residual: producers of motion vectors as contributors
    ed.cap_set("RND.RECON.motion-vectors", add_contrib=["post-color-hdr", "deformation-skinning", "geometry-pipeline"],
               tags=t)

    t = "K-ARCH-9 K-FUTURE-9 K-TEST-6"
    ed.contract_add("C-AUTOMATION", 3, "visual-debugging-tools", "Runtime automation & introspection",
                    "Structured command/query/observe protocol, discovery of exposed debug state and controls, frame "
                    "stepping, capture triggers, capability negotiation, versioned schema from C-REFL, dev-only "
                    "authentication; compiled out of shipping builds.", requires=["C-IPC", "C-REFL"],
                    conformance=True, tags=t)
    ed.cap_move("ED.ARCH.agent-api", "ED.DEBUG.automation-protocol", tags=t)
    ed.cap_set("ED.DEBUG.automation-protocol", name="Runtime automation & introspection protocol (C-AUTOMATION) for "
               "editor, clients, servers and devices", owner="visual-debugging-tools", mat="E",
               rm_contrib=["visual-debugging-tools"], add_contrib=["editor-architect", "observability-telemetry"],
               tags=t)
    ed.cap("ED.ARCH.llm-agent-frontend", "LLM/agent front end (MCP class) over C-AUTOMATION and editor commands",
           "editor-architect", "M", contrib=["visual-debugging-tools"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "ED.DEBUG.automation-protocol" in e.get("capabilities", []) or "ED.ARCH.agent-api" in e.get("capabilities", []):
            e["capabilities"] = ["ED.ARCH.llm-agent-frontend" if x in ("ED.ARCH.agent-api",
                                 "ED.DEBUG.automation-protocol") else x for x in e["capabilities"]]
    ed.use("editor-architect", "C-AUTOMATION", "C-ML?", tags=t)
    ed.use("visual-debugging-tools", "C-REFL", tags=t)
    for c in ed.doc["cross"]["concerns"]:
        if c["concern"] == "agent operability":
            c["owner"] = "visual-debugging-tools"
            c["obligation"] = "Expose debug state and controls through C-AUTOMATION with structured results; dev-only."
    ed.note(t, "crosscutting agent operability → visual-debugging-tools via C-AUTOMATION")
    s = ed.skill("visual-debugging-tools")
    s["untrusted_inputs"] = sorted(set(s.get("untrusted_inputs") or []) | {"automation-commands"})

    t = "K-ARCH-11"
    ed.contract_add("C-INTEGRITY", 3, "anti-cheat-integrity", "Integrity validation hooks",
                    "Validator registration per authoritative action (movement deltas, hits, economy), anomaly-signal "
                    "sink, rate-limit policy, client anti-cheat middleware boundary, attestation results.",
                    requires=["C-ID", "C-FRAME"], conformance=True, tags=t)
    for sid in ("character-movement", "gameplay-systems-toolkit", "prediction-rollback", "platform-services"):
        ed.use(sid, "C-INTEGRITY?", tags=t)
    ed.use("dedicated-server", "C-INTEGRITY", tags=t)
    ed.unuse("anti-cheat-integrity", "C-GAME", tags=t)
    ed.note(t, "anti-cheat no longer consumes C-GAME: gameplay registers validators through C-INTEGRITY (inversion)")

    t = "K-ARCH-13 K-PROD-2"
    for cid in ("ARCH.ORG.adjudication", "ARCH.ORG.critic-calibration"):
        ed.cap_set(cid, owner="architecture-governance", add_contrib=["program-orchestration"], tags=t)
    ed.cap("ARCH.ORG.independence", "Independence matrix: never-same-agent pairs (decider vs governance reviewer, "
           "implementer vs oracle author, builder vs adjudicator, security reviewer vs reviewed code, milestone "
           "owner vs gate owner) enforced by staffing at every organization tier; co-hosting capped by capability "
           "count", "architecture-governance", contrib=["program-orchestration", "test-architect"], tags=t)
    ed.nonresp_add("program-orchestration", "Adjudicating findings & calibrating critics", "architecture-governance",
                   tags=t)
    ed.skill_set("reference-games", parent="test-architect", tags=t)
    ed.doc["cross"].setdefault("independence", [
        ["engine-architect", "architecture-governance", "decider vs governance reviewer"],
        ["program-orchestration", "architecture-governance", "builder/scheduler vs adjudicator"],
        ["program-orchestration", "reference-games", "milestone owner vs gate content"],
        ["security-engineering", "owning-skill", "security reviewer vs reviewed code"],
        ["test-architect", "owning-skill", "oracle author vs implementer"]])
    ed.note(t, "crosscutting.independence matrix added (checked: skills exist, different workstreams)")

    t = "K-ARCH-14 K-GAMEPLAY-8"
    s = ed.skill("navigation-pathfinding")
    ed.nonresp("navigation-pathfinding", [x for x in s["non_responsibilities"] if x[0] != "Crowd avoidance"]
               + [["Flow-field & mass-agent avoidance", "crowd-simulation"]], tags=t)
    s = ed.skill("crowd-simulation")
    ed.skill_set("crowd-simulation", purpose="Flow fields, mass-agent simulation and LOD, traffic; individual-agent "
                 "local avoidance consumed from C-NAV.",
                 expertise=[x if "ORCA" not in x else "mass-scale avoidance variants" for x in s["expertise"]], tags=t)
    s = ed.skill("spatial-audio-acoustics")
    ed.skill_set("spatial-audio-acoustics", purpose=s["purpose"].replace("Panning and distance, ", ""), tags=t)

    t = "K-ARCH-15"
    ed.cap_set("ARCH.STRUCT.registration", name="Registration policy: what must self-register (phases, render "
               "features, services, cvars, codegen inputs) and the ban on central tables (mechanism in C-MOD)",
               add_contrib=["core-runtime-architect"], tags=t)

    t = "K-ARCH-17"
    ed.skill_set("plugin-system", parent="core-runtime-architect", tags=t)
    ed.skill_set("modding-ugc", parent="gameplay-architect", tags=t)

    t = "K-ARCH-18"
    ed.cap_set("NET.PRED.input-commands", name="Network delivery of C-INPUT command frames: redundancy, jitter "
               "buffering, server-side validation hooks (format owned by input-system)", tags=t)

    # ================================================================ LEGACY (wording; catalogue in r2_y)
    t = "K-LEGACY-4"
    ed.cap_set("UI.FW.logic", name="UI logic hosting: handlers resolved at load/compile time (script or visual script "
               "via C-SCRIPT); reflection only for authoring", tags=t)
    ed.cap_set("UI.FW.architecture", name="Game UI architecture: retained UI with change-notified view models and "
               "compiled/resolved bindings (no per-frame polling)", tags=t)
    _append(ed, "C-UI", "bindings resolved at load time and driven by change notification.", t)

    t = "K-LEGACY-5 K-GAMEPLAY-20"
    ed.cap_set("GAM.SCR.level-scripting", name="Script binding for world-, cell-, data-layer- or instance-scoped "
               "logic with streaming-safe references (soft IDs resolved on activation)",
               add_contrib=["world-architect"], tags=t)
    ed.cap_set("GAM.SYS.volumes", name="Trigger & gameplay volumes, gameplay markers, cell/instance-scoped logic "
               "wiring (soft references via C-WORLD activation)", add_contrib=["world-architect"], tags=t)

    t = "K-LEGACY-6"   # seed S13; residual: X label also covered established indirect scheduling
    ed.cap_set("RND.GRAPH.work-graphs", name="Work-graph scheduling, barriers & backing memory", tags=t)
    ed.cap("RND.GRAPH.gpu-generated-work", "Scheduling, barriers & memory for GPU-generated work (indirect, "
           "device-generated commands)", "render-graph-scheduling", contrib=["geometry-pipeline"], tags=t)

    t = "K-LEGACY-7"
    for sid in ("ecs-runtime", "world-architect"):
        ed.use(sid, "C-COOK", tool=True, tags=t)
    ed.note(t, "check.py: owners of cook/bake/editor capabilities must reach a tool contract")

    t = "K-LEGACY-8 K-SIM-6"
    ed.cap("CORE.OBJ.world-instances", "Multiple isolated world instances per process; world-scoped state reachable "
           "only through a world handle; no current-world global", "entity-object-model",
           contrib=["ecs-runtime", "world-architect", "editor-architect"], tags=t)

    t = "K-LEGACY-9"
    ed.cap_set("NET.REP.state", name="Entity & property replication with push/dirty-tracked change detection "
               "(consuming C-ECS change versions and C-SPATIAL change sets), serialized once per object", tags=t)

    t = "K-LEGACY-10"
    _append(ed, "C-ENV", "queries submitted as batched streams per phase; provider bound per region/cell at activation "
            "(no per-query dispatch across providers).", t)
    _append(ed, "C-SPATIAL", "batched query API.", t)
    _append(ed, "C-NAV", "batched path/query requests; nav produces path corridors and steering intents and never "
            "moves bodies.", t)
    _append(ed, "C-ARCH", "every query contract declares its batch granularity.", t)

    t = "K-LEGACY-11"
    ed.cap_set("CORE.JOBS.degenerate", name="Shipping inline/cooperative mode: the same task graph on 0–2 workers, no "
               "blocking waits on host threads, yield to the host event loop", add_contrib=["frame-orchestration"],
               tags=t)
    ed.cap_set("PLAT.WEB.runtime", name="WASM threads, cross-origin isolation, no-threads fallback & memory limits",
               tags=t)

    t = "K-LEGACY-12"
    for cid, prof in (("WLD.PART.grid", ["lite3d", "std3d"]), ("WLD.PART.sources", ["lite3d", "std3d"]),
                      ("WLD.PART.hlod", ["lite3d", "std3d"]), ("WLD.PART.sim-tiers", ["openworld", "massim"]),
                      ("WLD.PART.server", ["openworld"])):
        ed.cap_set(cid, profiles=prof, tags=t)
    ed.cap("WLD.MODEL.unit-load", "Async non-blocking whole-unit load with loading-screen hand-off (minimal/2D "
           "default)", "world-architect", contrib=["resource-streaming-architect"], tags=t)

    t = "K-LEGACY-14"
    ed.note(t, "L11 split in r2_y (coarse locks → concurrency-primitives; renderer sync → render-graph-scheduling)")

    t = "K-LEGACY-16"
    _append(ed, "C-SCRIPT", "execution on task-graph workers via per-worker VMs/isolates; world mutation only through "
            "deferred command buffers; weak handles to engine objects.", t)
    s = ed.skill("scripting-runtime")
    ed.skill_set("scripting-runtime", purpose=s["purpose"].rstrip(".") + ", VM concurrency model.", tags=t)

    t = "K-LEGACY-17"
    ed.cap_set("RES.MGMT.no-stall", name="Fully asynchronous loading: no blocking waits on frame-critical tasks or "
               "host/OS-bound threads; completions via C-TASK tokens", tags=t)
