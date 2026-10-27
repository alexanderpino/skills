"""Round-4 revision, part A: architecture, rendering and systems findings
(K-ARCH-1,3,4,5,7..9,11,12; K-RENDER-2..5,7,8; K-SYSTEMS-1..8)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-3"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402


def apply(ed):
    # ================================================================ RENDER
    t = "K-RENDER-2"
    ed.use("atmosphere-weather", "C-SCENETEX?", "C-COLOR?", "C-GI?", tags=t)
    ed.use("terrain", "C-LIGHT?", "C-RT?", "C-GI?", "C-SCENETEX?", tags=t)
    ed.use("vegetation-foliage", "C-SCENETEX?", tags=t)
    for cid in ("RND.RT.instances", "RND.RT.lod"):
        ed.cap_set(cid, add_contrib=["terrain", "water-ocean", "vegetation-foliage"], tags=t)
    _cap(ed, "WLD.ENV.terrain-rt", "Terrain in ray tracing and SDF scenes: heightfield/clipmap to BLAS or SDF proxy",
         "terrain", contrib=["ray-tracing-infrastructure"], tags=t)

    t = "K-RENDER-3"
    _cap(ed, "RND.LOD.instanced-clusters", "Instance sharing inside a cluster hierarchy (assemblies, per-instance bounds "
         "expansion for WPO)", "virtualized-geometry-lod", contrib=["vegetation-foliage", "geometry-pipeline"], tags=t)
    _cap(ed, "RND.LOD.foliage", "Dense masked and thin-geometry LOD in the virtualized tier (voxel/impostor transition)",
         "virtualized-geometry-lod", contrib=["vegetation-foliage", "geometry-pipeline"], tags=t)
    ed.nonresp_add("vegetation-foliage", "Cluster LOD of foliage geometry", "virtualized-geometry-lod", tags=t)

    t = "K-RENDER-4"
    _cap(ed, "RND.ARCH.depth-convention", "Depth and projection conventions (reverse-Z, float depth, infinite far plane, "
         "clip-space jitter, pixel-centre and Y-flip differences across D3D/Vulkan/Metal/WebGPU), referenced by C-SCENETEX",
         "render-architect", contrib=["math-simd-numerics", "reconstruction-upscaling", "xr-runtime"], tags=t)
    _append(ed, "C-SCENETEX", "depth and projection conventions per RND.ARCH.depth-convention.", t)

    t = "K-RENDER-5"
    _cap(ed, "RND.SHADER.precision", "Shader numeric-precision policy per tier and pass (FP16/min16, packed math, subgroup "
         "size assumptions) with FP32-reference validation", "shader-system",
         contrib=["platform-mobile", "material-system", "render-validation"], tags=t)

    t = "K-RENDER-7"
    ed.cap_set("RND.GEO.precomputed-visibility", profiles=["lite3d"], tags=t)
    ed.doc["legacy"]["patterns"].append(
        {"id": "L75", "pattern": "Baked visibility (PVS/portals) on GPU-driven tiers", "detection": "precomputed visibility "
         "sets used where HZB culling is available", "default_stance": "GPU HZB culling; baked visibility only on the "
         "CPU-culled tier by ADR", "justification_owner": "geometry-pipeline",
         "stance_capabilities": ["RND.GEO.culling", "RND.GEO.cpu-occlusion", "RND.GEO.precomputed-visibility"],
         "contradiction_terms": [r"baked pvs (?:everywhere|default)"]})

    t = "K-RENDER-8"
    _cap(ed, "RND.MAT.pso-miss-policy", "Behaviour when a PSO is not ready: per-pass and material-domain policy table "
         "(skip, hold, fallback material, block), telemetry to PRF.LOAD.hitch-gate", "material-system",
         contrib=["rhi-core", "shader-system", "render-architect"], tags=t)
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == "L29":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"RND.MAT.pso-miss-policy"})

    # ================================================================ ARCH
    t = "K-ARCH-1"
    ed.use("render-2d-vector", "C-VT?", tags=t)
    ed.use("material-system", "C-VT?", tags=t)
    ed.use("post-color-hdr", "C-TEMPORAL?", "C-SCENETEX?", tags=t)
    ed.use("vfx-particles", "C-RSCENE?", "C-MATIF?", "C-SCENETEX?", tags=t)

    t = "K-ARCH-3"
    _cap(ed, "CORE.REFL.state-classes", "State classes on reflected properties (transient, derived, saved, replicated, "
         "predicted, persisted, stripped from shipping) declared once; registries derive from them", "reflection-metadata",
         contrib=["ecs-runtime", "replication", "persistence-save", "prediction-rollback"], tags=t)
    ed.contract_add("C-STATECLASS", 2, "reflection-metadata", "State-class declaration",
                    "One declaration of the state class of every component and reflected property; C-SNAPSHOT, C-REP, "
                    "C-PREDICT, C-SAVE and C-SRVDATA registries derive from it; a fitness function requires every declared "
                    "component or property to have a class.", requires=["C-REFL"], conformance=True,
                    oracle_author="functional-automation-soak", oracle_reference=[
                        "property round-trip cases per class; registry-derivation golden cases"], tags=t)
    for sid in ("ecs-runtime", "replication", "persistence-save", "prediction-rollback"):
        ed.use(sid, "C-STATECLASS", tags=t)
    for cid in ("C-SNAPSHOT", "C-REP", "C-PREDICT", "C-SAVE", "C-SRVDATA"):
        c = ed.contract(cid)
        ed.contract_set(cid, requires=c["requires"] + ["C-STATECLASS"], tags=t)

    t = "K-ARCH-4"
    for cid in ("PHY.ARCH.validation", "ANM.ARCH.validation", "AUD.ARCH.validation", "GAM.AI.validation",
                "RES.MGMT.validation", "UI.FW.validation"):
        _rename(ed, cid, " (hooks, reference scenes and threshold proposals only; suite authorship belongs to the "
                "contract's oracle_author)", tags=t)
    _cap(ed, "QA.SIM.navigation", "Navigation/AI validation runs (navmesh connectivity, path optimality)",
         "simulation-validation", contrib=["navigation-pathfinding"], tags=t)
    _cap(ed, "QA.SIM.streaming", "Streaming-correctness validation runs (no required cell missing at traversal speed)",
         "simulation-validation", contrib=["resource-streaming-architect"], tags=t)

    t = "K-ARCH-5"
    for sid, name, parent, expertise in (
            ("foundation-conformance", "Foundation Conformance", "test-architect",
             ["memory-model litmus tests", "numeric reference vectors", "container and allocator model tests"]),
            ("ui-text-conformance", "UI & Text Conformance", "test-architect",
             ["text shaping and CLDR corpora", "layout and focus-graph oracles"])):
        ed.skill_add(tags=t, id=sid, name=name, tier="expert", parent=parent, profiles=["all"], kind="process", targets=[],
                     workstream="quality", purpose=f"Independent authoring of conformance suites for {name.lower()} "
                     "contracts, distinct from their owners and implementers.",
                     non_responsibilities=[["Contract implementation", "owning-skill"],
                                           ["Fuzz campaigns", "robustness-fuzzing"]],
                     expertise=expertise, consumes=["C-TEST"])
    _cap(ed, "QA.CONF.foundation", "Foundation conformance suites (memory model, numeric references, containers, allocators, "
         "config, ECS model tests)", "foundation-conformance", contrib=["test-architect"], tags=t)
    _cap(ed, "QA.CONF.ui-text", "UI and text conformance suites (shaping, CLDR, layout, focus)", "ui-text-conformance",
         contrib=["test-architect"], tags=t)
    for cid, nm, o in (("QA.CONF.memory-model", "Memory-model litmus and model-checking lanes for foundation contracts", "foundation-conformance"),
                       ("QA.CONF.numerics", "Numeric reference vectors and precision oracles", "foundation-conformance"),
                       ("QA.CONF.text-shaping", "Text shaping, bidi and CLDR corpora", "ui-text-conformance"),
                       ("QA.CONF.layout-focus", "Layout, safe-area and focus-graph oracles", "ui-text-conformance")):
        _cap(ed, cid, nm, o, contrib=["test-architect"], tags=t)
    for cid in ("C-MATH", "C-MEM", "C-TYPES", "C-ECS", "C-CFG", "C-ERR", "C-BASE"):
        ed.contract_set(cid, oracle_author="foundation-conformance", tags=t)
    for cid in ("C-TEXT", "C-LOC", "C-UI", "C-A11YRT"):
        ed.contract_set(cid, oracle_author="ui-text-conformance", tags=t)

    t = "K-ARCH-8"
    _cap(ed, "NET.PRED.rewound-world-query", "Hit volumes with poses as of tick T: composite of collider history and pose "
         "history with declared consistency and memory cost per tick of history", "prediction-rollback",
         contrib=["rigid-body-dynamics", "animation-runtime", "gameplay-systems-toolkit"], tags=t)
    ed.contract_add("C-REWIND", 3, "prediction-rollback", "Rewound world queries",
                    "Hit volumes with poses as of tick T: collider-history and pose-history providers, consistency and "
                    "memory-cost declaration per tick of history.", requires=["C-SNAPSHOT", "C-NET"], conformance=True,
                    oracle_author="simulation-validation", tags=t)
    ed.use("gameplay-systems-toolkit", "C-REWIND?", tags=t)
    ed.use("rigid-body-dynamics", "C-REWIND?", tags=t)
    ed.use("animation-runtime", "C-REWIND?", tags=t)

    t = "K-ARCH-9"
    _cap(ed, "GAM.DATA.surface-types", "Surface-type taxonomy (IDs, hierarchy, parameters) shared by physics, terrain, audio, "
         "VFX, decals, projectiles and haptics", "gameplay-data",
         contrib=["physics-architect", "terrain", "audio-content-runtime", "vfx-particles", "material-system"], tags=t)
    ed.cap_set("PHY.ARCH.materials", name="Physics parameters bound to shared surface types (GAM.DATA.surface-types)",
               tags=t)
    _append(ed, "C-GAMEDATA", "surface-type IDs (GAM.DATA.surface-types) referenced by C-ENV, audio, VFX and materials.", t)

    t = "K-ARCH-11"
    ed.skill_set("visual-debugging-tools", parent="core-runtime-architect", tags=t)

    t = "K-ARCH-12"
    ed.cap_set("ARCH.ORG.escalation", name="Escalation tiers & decision SLAs; a non-party lead of the workstream is the "
               "first-instance arbiter of intra-workstream disputes; engine-architect decides cross-workstream disputes "
               "and disputes in which the arbitrating lead is a party", tags=t)

    # ================================================================ SYSTEMS
    t = "K-SYSTEMS-1"
    _cap(ed, "CORE.JOBS.cancellation", "Task cancellation: stop tokens, propagation to dependents, cancelling in-flight IO/GPU "
         "work, cancel-vs-completion and cancel-vs-retire ordering", "job-system-task-graph",
         contrib=["async-io-storage", "resource-streaming-architect", "concurrency-primitives"], tags=t)
    _append(ed, "C-TASK", "cancel/stop-token and cancel-vs-completion semantics (CORE.JOBS.cancellation).", t)

    t = "K-SYSTEMS-2"
    _cap(ed, "RES.IO.write", "Durable write primitives: write queues and coalescing, durability classes (fsync/F_FULLFSYNC, "
         "directory sync), atomic replace, quota and disk-full errors, read-deadline protection", "async-io-storage",
         contrib=["platform-architect", "persistence-save"], tags=t)
    _append(ed, "C-IO", "write path with durability classes and atomic replace; power-cut crash-consistency oracle.", t)
    ed.cap_set("GAM.SAVE.atomic", name="Save-format atomicity policy on RES.IO.write", tags=t)

    t = "K-SYSTEMS-3"
    ed.cap_set("CORE.MEM.allocators", name="Allocator family with scoped arenas: reset keyed to a completion token or "
               "frame-in-flight slot (C-LIFETIME), pools, thread caches", tags=t)
    ed.use("memory-allocators", "C-LIFETIME", tags=t)

    t = "K-SYSTEMS-4"
    _cap(ed, "RND.MEM.cpu-visible", "CPU-visible GPU memory rules: memory-type and coherence matrix per platform (write-"
         "combined vs cached, ReBAR), no CPU reads from upload memory (lint), cache maintenance on non-coherent paths",
         "gpu-memory-resources", contrib=["memory-allocators"], tags=t)
    ed.cap_set("CORE.MEM.uma", add_contrib=["gpu-memory-resources"], tags=t)

    t = "K-SYSTEMS-5"
    _rename(ed, "CORE.CONC.sync", "; priority inheritance/donation where the OS offers it, no spinning across QoS classes, "
            "lock-class registry (frame-critical, RT-forbidden)", tags=t)
    _rename(ed, "CORE.JOBS.thread-model", "; forbidden-primitive lint for real-time threads", tags=t)

    t = "K-SYSTEMS-6"
    _cap(ed, "CORE.MEM.field-detection", "Field detection of heap corruption in shipping builds: sampled guard allocator (E) "
         "and hardware memory-tagging mode (M), overhead budgets in C-BUDGET", "memory-allocators",
         contrib=["crash-diagnostics", "security-engineering"], tags=t)

    t = "K-SYSTEMS-7"
    _cap(ed, "CORE.CONC.layout", "Cross-thread data layout: per-target destructive-interference size, padding and sharding "
         "rules, per-worker sharded counters and queues, padding lint", "concurrency-primitives",
         contrib=["containers-core-types", "platform-architect"], tags=t)

    t = "K-SYSTEMS-8"
    _cap(ed, "OBS.CRASH.safe-path", "Crash-time safety: async-signal-safe/SEH-safe code, pre-reserved emergency heap, "
         "alternate stack, out-of-process capture over PAL pipes, OOM inside the handler", "crash-diagnostics",
         contrib=["platform-architect", "memory-allocators"], tags=t)
    _append(ed, "C-CRASH", "the handler uses PAL process/pipe primitives via C-BASE only and is not a C-IPC dependency; "
            "crash-in-OOM and crash-with-lock-held conformance cases.", t)
    c = ed.contract("C-IPC")
    ed.contract_set("C-IPC", summary=c["summary"].replace("crash handler, ", ""), tags=t)
