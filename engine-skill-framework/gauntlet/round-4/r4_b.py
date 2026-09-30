"""Round-4 revision, part B: simulation, networking and tools findings
(K-SIM-1..4,7,10..14; K-NET-2,3,5,8,9,10; K-TOOLS-1,2,3,4,6..10)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-3"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402


def apply(ed):
    # ================================================================ SIM
    t = "K-SIM-1"
    ed.cap_set("PHY.2D.dynamics", name="2D rigid bodies and dynamics solver (stacking, restitution, friction)", tags=t)
    _cap(ed, "PHY.2D.queries-filtering", "2D scene queries, collision layers and filtering", "physics-2d", tags=t)
    _cap(ed, "PHY.2D.joints-ropes", "2D joints, ropes and sleeping", "physics-2d", tags=t)
    _cap(ed, "PHY.2D.ccd-sensors", "2D continuous collision, sensors, kinematic bodies and platform riding", "physics-2d", tags=t)
    _cap(ed, "PHY.2D.tilemap-collision", "Tilemap and one-way collision", "physics-2d", contrib=["render-2d-vector"], tags=t)
    _cap(ed, "PHY.2D.runtime-build", "Runtime collision generation for destructible and edited 2D terrain", "physics-2d",
         contrib=["terrain", "destruction-fracture"], tags=t)

    t = "K-SIM-2"
    ed.contract_add("C-CHARCTRL", 3, "physics-architect", "Character controller primitive",
                    "Collide-and-slide, step/slope/ledge handling, up-vector, platform carry and push-vs-dynamic-body as a "
                    "re-steppable controller: resimulating N moves from a snapshot reproduces state; middleware backends "
                    "implement it through PHY.ARCH.middleware-layer.", requires=["C-PHYS"], conformance=True,
                    oracle_author="simulation-validation", needs_implementer=True, tags=t)
    for sid in ("character-physics", "physics-2d"):
        _add(ed, sid, "implements", "C-CHARCTRL")
    c = ed.contract("C-MOVE")
    ed.contract_set("C-MOVE", requires=c["requires"] + ["C-CHARCTRL"], tags=t)
    ed.use("character-movement", "C-CHARCTRL", tags=t)

    t = "K-SIM-3"
    ed.cap_set("NET.PRED.physics", name="Networked physics: server-authoritative replicated dynamic bodies with "
               "interpolation, extrapolation and smoothing", tags=t)
    _cap(ed, "NET.PRED.physics-rollback", "Predicted physics with rollback and partial-island resimulation (restorable "
         "solver caches required)", "prediction-rollback", "M", contrib=["rigid-body-dynamics", "physics-architect"], tags=t)
    _cap(ed, "NET.PRED.physics-lockstep", "Deterministic lockstep physics (backends declaring the deterministic level only)",
         "prediction-rollback", contrib=["determinism-replay"], tags=t)
    _radar(ed, "Predicted rigid-body physics with rollback", "M", "prediction-rollback", ["NET.PRED.physics-rollback"],
           "PhysX/Jolt do not restore solver warm-start caches or partial islands; Chaos network-physics prediction is beta",
           "A shipped title predicts general rigid bodies over a restorable backend",
           "NET.PRED.physics (server-authoritative bodies with interpolation)")

    t = "K-SIM-4"
    _cap(ed, "NET.REP.physics-bodies", "Physics-body replication: active-set/change-set from C-PHYS, sleep flags, quantized "
         "pose/velocity, significance priority, prop extrapolation, prop and vehicle ownership hand-off",
         "replication", contrib=["physics-architect", "prediction-rollback"], tags=t)
    ed.use("replication", "C-PHYS?", tags=t)
    _append(ed, "C-PHYS", "active-set/change-set output for replication.", t)

    t = "K-SIM-7"
    _cap(ed, "PHY.ARCH.budget-degradation", "Simulation actuators (substeps, solver iterations, active-body cap, CCD and "
         "query budgets, cloth/fluid particle counts) registered in CORE.SCALE.actuators", "physics-architect",
         contrib=["runtime-scalability", "crowd-simulation", "systems-simulation"], tags=t)
    ed.cap_set("CORE.FRAME.fixed-step", name="Fixed-step simulation with interpolation; bounded catch-up (max substeps, "
               "dilation vs drop) with cadence fixed for lockstep", tags=t)

    t = "K-SIM-10"
    ed.cap_move("PHY.2D.cellular", "GAM.SIM.cellular", tags=t)
    ed.cap_set("GAM.SIM.cellular", name="Discrete grid/cellular simulation (falling sand, liquid/gas/heat grids, 2D and 3D "
               "voxel), deterministic", owner="systems-simulation", add_contrib=["physics-2d", "voxel-worlds"],
               rm_contrib=["fluid-simulation"], tags=t)
    ed.nonresp("systems-simulation", [["Mass agents & traffic", "crowd-simulation"],
                                      ["Continuum and particle fluids", "fluid-simulation"],
                                      ["Game rules", "external:game"]], tags=t)
    ed.nonresp_add("physics-2d", "Discrete cellular material simulation", "systems-simulation", tags=t)

    t = "K-SIM-11"
    _input(ed, "physics-assets", "collision-detection", ["package-formats-vfs", "modding-ugc"], "hostile-remote",
           "hull vertices, triangles, cook time, body/constraint counts; UGC cooking async, budgeted and sandboxed")

    t = "K-SIM-12"
    _cap(ed, "PRF.BENCH.sim-worst-case", "Simulation worst-case cost: contact storms, pile-ups, explosion-to-debris bursts, "
         "query storms, mass-agent surges", "perf-benchmarking",
         contrib=["physics-architect", "crowd-simulation", "destruction-fracture"], tags=t)
    _rename(ed, "PRF.METH.budgets", "; per-tier simulation step budgets tied to PHY.ARCH.budget-degradation", tags=t)

    t = "K-SIM-13"
    ed.doc["legacy"]["patterns"] += [
        {"id": "L76", "pattern": "Discrete-only collision with speed clamps", "detection": "speed caps or thick walls "
         "to stop tunnelling", "default_stance": "Continuous collision for fast bodies", "justification_owner":
         "physics-architect", "stance_capabilities": ["PHY.COL.ccd"], "contradiction_terms": [r"speed clamps? instead of"]},
        {"id": "L77", "pattern": "Unbounded always-awake physics world", "detection": "no sleeping, active set or "
         "simulation LOD", "default_stance": "Islands and sleeping, physics LOD, tier transitions",
         "justification_owner": "physics-architect",
         "stance_capabilities": ["PHY.DYN.islands", "PHY.ARCH.lod", "PHY.ARCH.tier-transitions"],
         "contradiction_terms": [r"always-awake"]},
        {"id": "L78", "pattern": "Rollback over non-restorable physics state", "detection": "rollback or lockstep over "
         "a backend that cannot restore solver caches", "default_stance": "Restore/resimulate conformance and sync tests",
         "justification_owner": "physics-architect", "stance_capabilities": ["PHY.ARCH.rewind", "NET.PRED.sync-test"],
         "contradiction_terms": [r"rollback over non-restorable"]}]

    t = "K-SIM-14"
    ed.cap_set("PHY.ARCH.gpu", name="GPU physics offload; gameplay-visible GPU results are tick-stamped, latched and "
               "excluded from deterministic state; registered as external-work producers", tags=t)
    ed.cap_set("RND.GRAPH.external-work", add_contrib=["physics-architect", "fluid-simulation", "cloth-deformables",
                                                      "crowd-simulation"], tags=t)

    # ================================================================ NET
    t = "K-NET-2"
    _append(ed, "C-NETSESSION", "participant interface (on_join_ready, provide_baseline, on_travel, on_reconnect, "
            "on_disconnect) implemented by replication, prediction-rollback and determinism-replay.", t)
    ed.use("replication", "C-NETSESSION", tags=t)
    ed.unuse("net-session", "C-REP", tags=t)

    t = "K-NET-3"
    ed.use("net-session", "C-INTEGRITY?", tags=t)
    ed.use("anti-cheat-integrity", "C-HOSTAUTH?", tags=t)
    _append(ed, "C-INTEGRITY", "verdict types (kick, ban, quarantine, flag) applied through C-HOSTAUTH; listen-host kick "
            "conformance case.", t)

    t = "K-NET-5"
    ed.skill_set("dedicated-server", purpose="Headless server builds and stripping, host lifecycle (C-SERVER) for rolling "
                 "deploys, tick cost and multi-instance density, the authenticated admin surface, fleet orchestration "
                 "boundary and server observability.", tags=t)
    c = ed.contract("C-HOSTAUTH")
    ed.contract_set("C-HOSTAUTH", summary=c["summary"].replace("kick/ban and the host-local admin surface",
                    "kick/ban primitives and the local console only (RBAC, audit and remote transport are NET.SRV.admin)"),
                    tags=t)

    t = "K-NET-8"
    _cap(ed, "NET.SESS.host-migration", "Host migration: replicated state or snapshot, prediction state and authority "
         "transfer; host-drop scenario", "net-session",
         contrib=["replication", "prediction-rollback", "determinism-replay"], tags=t)
    ed.cap_set("NET.ARCH.validation", name="Netcode oracle scenarios & acceptance thresholds incl. host-drop (co-signed by "
               "simulation validation)", tags=t)

    t = "K-NET-9"
    _append(ed, "C-BUDGET", "network lines (per-connection bytes/s, server egress per CCU, tick cost per player, packet rate) "
            "and named link-class profiles (home Wi-Fi, cellular, console NAT) with values supplied by NET.ARCH.budgets.", t)

    t = "K-NET-10"
    _input(ed, "server-list-entries", "net-session", ["network-transport"], "hostile-remote",
           "length/count/rate; endpoint allow-list; pre-auth")

    # ================================================================ TOOLS
    t = "K-TOOLS-1"
    ed.contract_add("C-EDPREVIEW", 5, "world-editor-viewport", "Editor preview worlds",
                    "Preview-world lifetime, orbit viewport widget, picking and basic gizmos for asset editors; requires only "
                    "C-EDCMD; C-EDHOST embeds its panels.", requires=["C-EDCMD"], conformance=True,
                    oracle_author="functional-automation-soak", oracle_reference=["preview-world lifecycle cases"], tags=t)
    for sid in ("material-system", "animation-runtime", "animation-graphs", "vfx-particles", "cinematics-sequencer",
                "character-rendering", "terrain", "destruction-fracture", "audio-content-runtime"):
        ed.use(sid, "C-EDPREVIEW", tool=True, tags=t)

    t = "K-TOOLS-2"
    ed.contract_add("C-IMPORT", 5, "asset-import-interchange", "Asset import",
                    "Importer registration, per-asset-type import-settings schema, domain asset-factory hook, "
                    "reimport-preserve rules, batch entry and schema version.", requires=["C-ASSET", "C-SER", "C-COOK"],
                    conformance=True, oracle_author="functional-automation-soak",
                    oracle_reference=["round-trip import corpora (FBX/glTF/USD samples), reimport-preserve cases"], tags=t)
    for sid in ("animation-runtime", "material-system", "rigid-body-dynamics", "virtualized-geometry-lod",
                "audio-content-runtime", "collision-detection"):
        ed.use(sid, "C-IMPORT", tool=True, tags=t)

    t = "K-TOOLS-3"
    ed.note(t, "tool contracts freeze at M3 by design: earlier tool halves run through headless commandlets over C-CMD "
               "(frozen at M1); a minimal editor before M2 is not added (partial)")

    t = "K-TOOLS-4"
    _rename(ed, "RND.GI.bake-pipeline", " (implemented as C-COOK world-scope processors; orchestration belongs to "
            "CNT.COOK.world-build)", tags=t)
    _rename(ed, "WLD.PART.hlod", " (builder implemented as a C-COOK world-scope processor; invalidation and "
            "distribution belong to CNT.COOK.world-build)", tags=t)
    ed.cap_set("CNT.COOK.world-build", add_contrib=["fluid-simulation", "spatial-audio-acoustics",
                                                    "navigation-pathfinding", "global-illumination"], tags=t)

    t = "K-TOOLS-6"
    ed.cap_set("CNT.COOK.shared-cache", profiles=["team-mid", "team-large"], tags=t)

    t = "K-TOOLS-7"
    _cap(ed, "RND.TOOL.direct-lights", "Direct-light authoring: placement and units, IES/cookies, light functions, shadow "
         "budget and light-complexity views", "direct-lighting-shadows",
         contrib=["world-editor-viewport", "global-illumination"], tags=t)
    ed.use("direct-lighting-shadows", "C-EDCMD", "C-EDHOST", tool=True, tags=t)

    t = "K-TOOLS-8"
    _cap(ed, "GAM.TOOL.save-inspector", "Save inspector: inspect, edit, diff and upgrade dry-run over C-SAVE and "
         "CORE.SER.evolution", "persistence-save", contrib=["visual-debugging-tools"], tags=t)
    ed.use("persistence-save", "C-EDCMD", "C-EDHOST", tool=True, tags=t)
    ed.skill_set("platform-web", authoring="Platform integration; web preview via C-TARGETPLAT deploy-to-browser and the "
                 "web tier in RND.TOOL.scalability-preview.", tags=t)
    ed.cap_set("RND.TOOL.scalability-preview", add_contrib=["platform-web"], tags=t)

    t = "K-TOOLS-9"
    _cap(ed, "ED.UI.settings-editor", "Schema-driven project-settings editor over layered per-platform C-CFG (diff, validate)",
         "editor-ui-framework", tags=t)
    _cap(ed, "ED.UI.workspace", "Workspace: layouts, keybindings, command palette and preferences; domain tools register "
         "commands and settings through C-EDHOST", "editor-ui-framework", tags=t)

    t = "K-TOOLS-10"
    for iid, owner, why in (("tabular-imports", "gameplay-data", "zip-bomb, XXE and formula-injection limits"),
                            ("localization-exchange", "localization-i18n", "XLIFF/PO size/depth limits"),
                            ("narrative-imports", "narrative-dialogue", "screenplay import size/depth limits"),
                            ("vendor-deliveries", "content-pipeline-architect", "package manifest and size limits"),
                            ("tracker-webhooks", "collaboration-version-control", "signature and schema verification")):
        _input(ed, iid, owner, [], "hostile-local" if iid != "tracker-webhooks" else "hostile-remote", why)
