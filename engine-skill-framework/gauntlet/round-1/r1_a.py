"""G1 round-1 revision, part A: schema axes, foundation/core, resources/IO, world."""

PROCESS = ["engine-architect", "architecture-governance", "program-orchestration", "research-evidence",
           "performance-architect", "perf-benchmarking", "cpu-performance", "gpu-performance",
           "loading-streaming-performance", "test-architect", "render-validation", "functional-automation-soak",
           "robustness-fuzzing", "certification-compliance", "security-engineering", "api-lifecycle-migration",
           "developer-experience-docs", "build-release-architect"]
TOOL = ["asset-import-interchange", "asset-cook-processors", "editor-architect", "editor-ui-framework",
        "world-editor-viewport", "graph-editor-framework", "collaboration-version-control", "ai-assisted-authoring",
        "build-system-toolchains", "ci-cd-automation", "packaging-release-patching"]
# presentation-only runtime skills: shipped in client (and the editor), never in headless builds
PRESENTATION = ["render-architect", "rhi-core", "gpu-memory-resources", "render-graph-scheduling", "shader-system",
                "material-system", "gpu-driven-pipeline", "virtualized-geometry-lod", "texture-streaming-vt",
                "direct-lighting-shadows", "global-illumination", "ray-tracing-infrastructure", "path-tracing",
                "reconstruction-upscaling", "post-color-hdr", "translucency-decals", "character-rendering",
                "render-2d-vector", "vfx-particles", "audio-architect", "audio-dsp-mixing", "spatial-audio-acoustics",
                "audio-content-runtime", "ui-architect", "text-fonts", "localization-i18n", "accessibility",
                "input-devices-haptics", "xr-runtime", "deformation-skinning", "facial-animation"]
WORKSTREAM = {
    "governance": ["engine-architect", "architecture-governance", "program-orchestration", "research-evidence",
                   "api-lifecycle-migration", "developer-experience-docs"],
    "foundation": ["core-runtime-architect", "math-simd-numerics", "memory-allocators", "containers-core-types",
                   "concurrency-primitives", "job-system-task-graph", "frame-orchestration", "entity-object-model",
                   "ecs-runtime", "reflection-metadata", "serialization-schema", "observability-telemetry",
                   "crash-diagnostics", "determinism-replay", "hot-reload-iteration", "plugin-system"],
    "platform": ["platform-architect", "platform-desktop", "platform-console", "platform-mobile-portable",
                 "platform-online-services", "input-system", "input-devices-haptics", "xr-runtime"],
    "content": ["content-pipeline-architect", "asset-import-interchange", "asset-cook-processors",
                "resource-streaming-architect", "async-io-storage", "package-formats-vfs"],
    "world": ["world-architect", "world-data-model", "spatial-transforms", "terrain", "vegetation-foliage",
              "water-ocean", "atmosphere-weather", "procedural-generation"],
    "rendering": ["render-architect", "rhi-core", "gpu-memory-resources", "render-graph-scheduling", "shader-system",
                  "material-system", "gpu-driven-pipeline", "virtualized-geometry-lod", "texture-streaming-vt",
                  "direct-lighting-shadows", "global-illumination", "ray-tracing-infrastructure", "path-tracing",
                  "reconstruction-upscaling", "post-color-hdr", "translucency-decals", "character-rendering",
                  "render-2d-vector", "vfx-particles", "ml-inference-runtime"],
    "simulation": ["physics-architect", "collision-detection", "rigid-body-dynamics", "character-vehicle-physics",
                   "cloth-deformables", "destruction-fracture", "fluid-simulation", "physics-2d",
                   "animation-architect", "animation-runtime", "deformation-skinning", "animation-graphs",
                   "motion-synthesis", "ik-procedural-animation", "facial-animation", "cinematics-sequencer"],
    "audio": ["audio-architect", "audio-dsp-mixing", "spatial-audio-acoustics", "audio-content-runtime"],
    "online": ["network-architect", "network-transport", "replication", "prediction-rollback", "dedicated-server",
               "anti-cheat-integrity"],
    "gameplay": ["gameplay-architect", "gameplay-systems-toolkit", "scripting-runtime", "navigation-pathfinding",
                 "crowd-simulation", "ai-behavior-perception", "persistence-save", "modding-ugc"],
    "ui": ["ui-architect", "text-fonts", "localization-i18n", "accessibility"],
    "tools": ["editor-architect", "editor-ui-framework", "world-editor-viewport", "graph-editor-framework",
              "collaboration-version-control", "visual-debugging-tools", "ai-assisted-authoring"],
    "release": ["build-release-architect", "build-system-toolchains", "ci-cd-automation", "packaging-release-patching"],
    "quality": ["test-architect", "render-validation", "functional-automation-soak", "robustness-fuzzing",
                "certification-compliance", "security-engineering"],
    "performance": ["performance-architect", "perf-benchmarking", "cpu-performance", "gpu-performance",
                    "loading-streaming-performance"],
}


def schema(ed):
    T = "K-NET-1 K-SIM-1 K-ARCH-1 K-PLATFORM-2 K-TOOLS-2 K-TOOLS-19 K-PROD-9 K-PROD-13 K-SIM-5 K-GAMEPLAY-14"
    sk = ed.doc["skill"]
    sk["_doc"] = ("Skill graph (schema v1). kind: runtime | tool | process. Runtime skills ship in builds; tool skills "
                  "ship only in the tools target; process skills are organizational and outside build closure. "
                  "targets: build targets a runtime skill ships in. platforms: platform-specific skills only. "
                  "consumes: runtime-side contract dependencies ('?' optional, '@C-Y' = consumed by the module that "
                  "provides C-Y). tool_consumes: editor/cook-side dependencies (tools target only). implements: "
                  "contracts this skill implements without owning (e.g. RHI backends). workstream: integration group.")
    sk["profiles"] = {
        "base": {
            "minimal": "UI-, card- or narrative-centric games without a physics world",
            "min2d": "Small 2D games (sprite/tile renderer, 2D physics)",
            "lite3d": "Lightweight 3D: mobile, portable, 2.5D, stylized; CPU-submitted rendering tier",
            "std3d": "Modern 3D on PC/console (GPU-driven rendering tier)"},
        "addons": {
            "openworld": "Large streamed worlds",
            "online": "Networked multiplayer",
            "aaa": "High-end AAA feature set",
            "xr": "VR / MR",
            "ugc": "Mods & user-generated content",
            "massim": "Large-scale agent simulation (RTS, colony, city, crowds)",
            "sandbox": "Voxel / buildable sandbox worlds",
            "vehicles": "Vehicle simulation (wheeled, flight, space)",
            "team-large": "Large production team infrastructure (multi-user, distributed builds, farms)"}}
    cfg = {}

    def c(name, profiles, target, platforms):
        cfg[name] = {"profiles": profiles, "target": target, "platforms": platforms}
    c("minimal-client", ["minimal"], "client", ["pc", "console", "mobile", "web"])
    c("indie-2d-client", ["min2d"], "client", ["pc", "console", "mobile", "web"])
    c("indie-2d-tools", ["min2d"], "tools", ["pc"])
    c("indie-2d-online-moddable-client", ["min2d", "online", "ugc"], "client", ["pc", "console", "mobile"])
    c("indie-2d-online-moddable-server", ["min2d", "online", "ugc"], "server", ["server-host"])
    c("rts-2d-massim-client", ["min2d", "massim", "online"], "client", ["pc"])
    c("lite-3d-mobile-client", ["lite3d"], "client", ["mobile"])
    c("lite-3d-mobile-online-client", ["lite3d", "online"], "client", ["mobile"])
    c("standard-3d-client", ["std3d"], "client", ["pc", "console"])
    c("standard-3d-tools", ["std3d"], "tools", ["pc"])
    c("open-world-client", ["std3d", "openworld"], "client", ["pc", "console"])
    c("online-3d-client", ["std3d", "online"], "client", ["pc", "console"])
    c("online-3d-server", ["std3d", "online"], "server", ["server-host"])
    c("online-3d-bot-client", ["std3d", "online"], "headless-client", ["server-host"])
    c("racing-3d-client", ["std3d", "vehicles"], "client", ["pc", "console"])
    c("rts-3d-massim-client", ["std3d", "massim", "online"], "client", ["pc"])
    c("sandbox-online-server", ["std3d", "sandbox", "online"], "server", ["server-host"])
    c("xr-standalone-client", ["lite3d", "xr"], "client", ["xr-standalone"])
    c("xr-pc-client", ["std3d", "xr"], "client", ["pc"])
    aaa = ["std3d", "openworld", "online", "aaa", "ugc", "vehicles", "team-large"]
    c("aaa-open-world-online-client", aaa, "client", ["pc", "console"])
    c("aaa-open-world-online-server", aaa, "server", ["server-host"])
    c("aaa-open-world-online-tools", aaa, "tools", ["pc"])
    sk["configurations"] = cfg

    for s in sk["skills"]:
        sid = s["id"]
        prof = s["profiles"]
        new = []
        for p in prof:
            if p in ("client", "all"):
                new = ["all"]
                break
            if p == "server":
                continue
            new.append("lite3d" if p == "mobile3d" else p)
        s["profiles"] = new or ["all"]
        runtime = s.pop("runtime", False)
        s["kind"] = "process" if sid in PROCESS else "tool" if sid in TOOL else ("runtime" if runtime else "process")
        if s["kind"] == "runtime":
            s["targets"] = ["client", "tools"] if sid in PRESENTATION else ["client", "headless-client", "server", "tools"]
        elif s["kind"] == "tool":
            s["targets"] = ["tools"]
        else:
            s["targets"] = []
        s.setdefault("tool_consumes", [])
        s.setdefault("implements", [])
        for ws, members in WORKSTREAM.items():
            if sid in members:
                s["workstream"] = ws
    ed.note(T, "schema v1: four configuration axes (profiles × target × platforms), skill kinds, tool-side "
               "consumption, implementers, workstreams; 22 named configurations incl. server/tools/headless targets")
    # tool contracts consumed from runtime code move to the tool side
    for s in sk["skills"]:
        keep, tool = [], list(s["tool_consumes"])
        for d in s["consumes"]:
            base = d.rstrip("?")
            if base in ("C-COOK", "C-EDCMD", "C-GRAPH"):
                if s["kind"] == "tool":
                    keep.append(base)
                else:
                    tool.append(base)
            else:
                keep.append(d)
        s["consumes"], s["tool_consumes"] = keep, tool
    ed.note("K-ARCH-5 K-TOOLS-2 K-SYSTEMS-2", "every runtime skill's C-COOK/C-EDCMD/C-GRAPH dependency moved to tool_consumes")


def foundation(ed):
    T1 = "K-SYSTEMS-1"
    ed.contract_add("C-BASE", 0, "platform-architect", "Bootstrap base",
                    "Raw page allocator, raw log/assert/abort sink, monotonic clock, raw thread primitives and "
                    "late-bound hook tables that higher layers install (allocator, log sink, assert handler, crash "
                    "annotator). Depends on nothing.", [], tags=T1)
    ed.contract_set("C-PAL", requires=["C-BASE"], tags=T1 + " K-PLATFORM-1 K-PLATFORM-14 K-SYSTEMS-7 K-LEGACY-5",
                    summary="OS services, CPU/GPU capability discovery and device database, windowing, display & safe "
                            "area, lifecycle and system events (memory pressure, thermal/power, network reachability, "
                            "audio endpoint, locale, OS accessibility settings, overlay/focus, storage, page size), "
                            "clocks and clock-domain correlation, processes/pipes/shared memory/dev sockets, HTTP(S)/TLS "
                            "client, permissions, thread creation/affinity/QoS and main-thread dispatch. Platform code "
                            "lives only in the PAL or in a registered platform backend slot.")
    for cid in ("C-ERR", "C-MEM", "C-INSTR", "C-CFG"):
        ed.contract_set(cid, requires=["C-BASE"], tags=T1)
    ed.contract_set("C-CRASH", requires=["C-BASE", "C-INSTR"], tags=T1)
    ed.contract_set("C-SYNC", requires=["C-BASE"], tags=T1 + " K-SYSTEMS-8",
                    summary="Atomics, locks, lock-free queues, safe reclamation, thread-safety annotation conventions, "
                            "OS-waitable completion tokens that IO/GPU fences plug into.")
    ed.contract_set("C-TASK", tags="K-SYSTEMS-4 K-SYSTEMS-12 K-PERF-12 K-LEGACY-5",
                    summary="Task creation, dependencies, priorities/QoS, blocking rules, completion-token integration, "
                            "process-wide thread inventory with pinned/affinity lanes and middleware adapters, serial "
                            "deterministic test mode and schedule-perturbation hooks, task tracing.")
    ed.contract_set("C-MOD", requires=["C-ERR", "C-TASK"], tags=T1,
                    summary="Module descriptors, serial bootstrap then parallel init dependency graph, service "
                            "registration, shutdown order, declarative self-registration (no central tables).")
    ed.contract_set("C-CFG", tags="K-LEGACY-12 K-PROD-16",
                    summary="Layered config sources (defaults, platform, device profile, remote/live, user) with "
                            "precedence, typed cvars read through versioned immutable snapshots latched at sync "
                            "points, queued change notification.")
    ed.contract_add("C-LIFETIME", 1, "core-runtime-architect", "Ownership & retirement",
                    "Engine-wide ownership and cross-thread reference rules; deferred-destruction/retirement service "
                    "keyed to completion tokens (task completion, frames in flight, GPU fences).", ["C-SYNC"],
                    tags="K-SYSTEMS-9")
    ed.contract_add("C-IPC", 2, "core-runtime-architect", "Engine IPC",
                    "Process model and IPC/RPC transport for editor↔runtime, tool workers, crash handler, profiler "
                    "and script debugger; dev-only port security.", ["C-PAL", "C-TASK"], tags="K-SYSTEMS-7")
    # budgets: process numbers vs runtime mechanism
    ed.contract_set("C-BUDGET", layer="P", requires=[], universal="all", tags="K-SYSTEMS-14 K-PERF-1",
                    name="Budgets & performance gates",
                    summary="Budget numbers per hardware tier × configuration × refresh class, derived from the "
                            "performance model; perf gate thresholds.")
    ed.contract_set("C-DET", tags="K-SYSTEMS-2",
                    summary="Determinism levels, floating-point rules, ordered-execution rules, state-hash hooks.")
    ed.contract_set("C-TYPES", requires=["C-MEM"], tags="K-SYSTEMS-6 K-SYSTEMS-15",
                    summary="Containers, strings, versioned stable hashing, general-purpose compression codecs, "
                            "vetted cryptographic primitives wrapper, ownership/view types.")
    ed.contract_set("C-MATH", tags="K-FUTURE-17",
                    summary="Vector/matrix types, precision classes, deterministic-math variants, fixed and "
                            "scalable (vector-length-agnostic) SIMD kernels, convention enforcement.")

    # explicit foundation dependencies (acyclic bootstrap tier)
    ed.skill_set("platform-architect", consumes=[], tags=T1)
    ed.skill_set("memory-allocators", consumes=["C-PAL", "C-BASE"], tags=T1)
    ed.skill_set("concurrency-primitives", consumes=["C-PAL", "C-BASE"], tags=T1)
    ed.skill_set("containers-core-types", consumes=["C-MEM", "C-BASE"], tags=T1)
    ed.skill_set("math-simd-numerics", consumes=["C-PAL"], tags=T1)
    ed.skill_set("job-system-task-graph", consumes=["C-SYNC", "C-PAL", "C-BASE", "C-MEM"], tags=T1)
    ed.skill_set("observability-telemetry", consumes=["C-PAL", "C-BASE", "C-SYNC"], tags=T1)
    ed.skill_set("crash-diagnostics", consumes=["C-PAL", "C-BASE", "C-INSTR"], tags=T1)
    ed.skill_set("core-runtime-architect",
                 consumes=["C-PAL", "C-BASE", "C-MEM", "C-TYPES", "C-SYNC", "C-TASK", "C-INSTR"], tags=T1)
    ed.skill_set("plugin-system", consumes=["C-MOD", "C-BASE", "C-API"], tags=T1)

    # runtime scalability: new runtime skill; performance-architect becomes a process skill
    ed.skill_add(id="runtime-scalability", name="Runtime Scalability & Governor", tier="expert",
                 parent="core-runtime-architect", profiles=["all"], kind="runtime",
                 targets=["client", "headless-client", "server", "tools"], workstream="foundation",
                 purpose="Runtime scalability machinery: device-profile application, the registry of scalability "
                         "knobs and actuators, first-run hardware auto-detect, and the closed-loop runtime governor "
                         "that consumes frame-time, thermal/power and memory-pressure signals and drives registered "
                         "actuators (dynamic resolution, significance, VFX, animation rate, worker count) with "
                         "priorities and hysteresis.",
                 non_responsibilities=[["Budget numbers and tier definitions", "performance-architect"],
                                       ["Hardware→tier device database", "platform-architect"],
                                       ["Each actuator's own implementation", "owning-skill"]],
                 consumes=["C-CFG", "C-PAL", "C-INSTR", "C-TASK"],
                 expertise=["control systems", "adaptive performance APIs (ADPF, Apple thermal state)", "scalability design"],
                 tags="K-SYSTEMS-13 K-SYSTEMS-14 K-PERF-8")
    ed.contract_add("C-SCALE", 1, "runtime-scalability", "Scalability & governor",
                    "Device-profile knobs, scalability cvars, budget query/report API, actuator registration and "
                    "governor control signals.", ["C-CFG"], universal="runtime", tags="K-SYSTEMS-14 K-PERF-8")
    ed.area("CORE.SCALE", "Runtime scalability", tags="K-SYSTEMS-13")
    ed.cap("CORE.SCALE.profiles", "Device-profile application & scalability knob registry", "runtime-scalability",
           contrib=["performance-architect", "platform-architect"], tags="K-SYSTEMS-14 K-PLATFORM-7")
    ed.cap("CORE.SCALE.governor", "Closed-loop runtime performance/power governor", "runtime-scalability",
           contrib=["frame-orchestration", "platform-mobile-portable", "performance-architect"], tags="K-SYSTEMS-13 K-PERF-8")
    ed.cap("CORE.SCALE.actuators", "Actuator registration (dynres, significance, VFX, animation rate, workers)",
           "runtime-scalability", contrib=["reconstruction-upscaling", "world-architect"], tags="K-PERF-8")
    ed.cap("CORE.SCALE.autodetect", "First-run hardware auto-detect & graphics presets", "runtime-scalability",
           contrib=["persistence-save"], tags="K-COMPLETE-26")
    ed.skill_set("performance-architect", provides=["C-BUDGET"], consumes=[], tags="K-SYSTEMS-14")

    # core lifecycle capabilities
    ed.cap("CORE.LIFE.bootstrap", "Serial bootstrap phase until the scheduler is live; hand-off to parallel init",
           "core-runtime-architect", contrib=["platform-architect"], tags=T1)
    ed.cap("CORE.LIFE.ownership-model", "Engine-wide ownership, cross-thread reference rules & retirement service",
           "core-runtime-architect",
           contrib=["entity-object-model", "resource-streaming-architect", "gpu-memory-resources", "concurrency-primitives",
                    "scripting-runtime"], tags="K-SYSTEMS-9")
    ed.cap("CORE.LIFE.ipc", "Engine IPC/RPC transport & process model for tools, workers, crash handler, profiler",
           "core-runtime-architect", contrib=["editor-architect", "crash-diagnostics", "security-engineering"],
           tags="K-SYSTEMS-7")
    ed.cap("CORE.LIFE.config-snapshots", "Config reads via immutable snapshots latched at sync points; queued change "
           "notification", "core-runtime-architect", contrib=["frame-orchestration"], tags="K-LEGACY-12")
    ed.cap("CORE.LIFE.interop", "Multi-language interop & memory-safe components (FFI/ABI rules, ownership across "
           "boundaries)", "core-runtime-architect", mat="M", contrib=["security-engineering", "build-system-toolchains"],
           tags="K-FUTURE-14 K-QUALITY-13")
    ed.cap_set("CORE.LIFE.language", name="Implementation language(s), standard baseline & compiler feature policy "
               "(incl. C++26 adoption plan, coding standard)", add_contrib=["architecture-governance", "security-engineering"],
               tags="K-SYSTEMS-11 K-FUTURE-14 K-QUALITY-13")
    ed.cap_del("ARCH.GOV.coding-standard", tags="K-SYSTEMS-11 (merged into CORE.LIFE.language)")
    ed.cap_set("CORE.LIFE.asserts", name="Assertion tiers & contract checks (C++26 contracts as adoption path)",
               tags="K-FUTURE-14")
    ed.cap_set("CORE.LIFE.config", name="Layered configuration, cvars, command line, per-platform/device and remote "
               "layers with precedence", add_contrib=["platform-online-services"], tags="K-PROD-16")

    # jobs
    ed.cap_set("CORE.JOBS.fibers", name="Fibers & language coroutines (fiber-safe TLS, debugger/profiler/sanitizer "
               "annotations)", add_contrib=["crash-diagnostics", "observability-telemetry", "robustness-fuzzing"],
               tags="K-QUALITY-13 K-SYSTEMS-17")
    ed.cap("CORE.JOBS.thread-model", "Engine thread inventory, core reservation, OS priority/QoS mapping, real-time "
           "thread rules, middleware pool adapters, oversubscription detection", "job-system-task-graph",
           contrib=["platform-architect", "audio-architect", "cpu-performance"], tags="K-SYSTEMS-4 K-PERF-12")
    ed.cap("CORE.JOBS.pinned", "Pinned-thread lanes for OS-thread-affine work", "job-system-task-graph",
           contrib=["platform-architect"], tags="K-LEGACY-5")
    ed.cap("CORE.JOBS.test-modes", "Serial/deterministic execution mode & seeded schedule perturbation hooks",
           "job-system-task-graph", contrib=["robustness-fuzzing"], tags="K-SYSTEMS-12")
    ed.cap("CORE.JOBS.introspection", "Task tracing, critical-path & utilization analysis, OS scheduler correlation",
           "job-system-task-graph", contrib=["observability-telemetry"], tags="K-SYSTEMS-12")
    ed.cap("CORE.JOBS.safety", "Dependency-race detection for declared task dependencies", "job-system-task-graph",
           contrib=["robustness-fuzzing"], tags="K-QUALITY-8")

    # frame orchestration
    ed.contract_set("C-FRAME", tags="K-SYSTEMS-3 K-PERF-2 K-LEGACY-2 K-SIM-7 K-QUALITY-10",
                    summary="Time domains and multi-rate cadences, pipelining depth, the minimal set of named global "
                            "sync points, frame-wide access declarations (ECS components and registered service "
                            "resources) from which ordering is derived, the canonical simulation schedule, injectable "
                            "test clock.")
    ed.contract_add("C-FLOW", 2, "frame-orchestration", "Cross-subsystem data channels",
                    "Versioned snapshots, double/triple-buffered hand-off, mailboxes and multi-rate resampling "
                    "between subsystems; producer/consumer declared per channel. The default for runtime data flow; "
                    "global barriers need an ADR.", ["C-FRAME"], tags="K-LEGACY-2")
    ed.contract_add("C-PRESENT", 2, "frame-orchestration", "Present timeline",
                    "Present timeline and display-time prediction, latency markers, interposed presenters (frame "
                    "generation, XR compositor, cloud encoder), GPU-frame-complete and present-feedback sink "
                    "implemented by the RHI (dependency inversion).", ["C-FRAME"], tags="K-ARCH-10 K-SYSTEMS-8")
    fo = "frame-orchestration"
    ed.cap("CORE.FRAME.access-model", "Unified access declarations for all phase work (ECS and service resources) with "
           "derived ordering", fo, contrib=["ecs-runtime", "physics-architect", "render-architect"],
           tags="K-SYSTEMS-3 K-PERF-2")
    ed.cap("CORE.FRAME.channels", "Cross-subsystem data channels (C-FLOW)", fo, tags="K-LEGACY-2")
    ed.cap("CORE.FRAME.sim-schedule", "Canonical simulation phase order (pre/post-physics, substeps, net snapshot, "
           "render extract)", fo, contrib=["physics-architect", "animation-architect", "network-architect"], tags="K-SIM-7")
    ed.cap("CORE.FRAME.amortized", "Time-sliced / rate-bucketed ticking & per-phase tick budgets", fo, tags="K-SIM-4")
    ed.cap("CORE.FRAME.critical-path", "Frame critical-path analysis & phase-overlap reporting", fo,
           contrib=["performance-architect"], tags="K-PERF-2")
    ed.cap("CORE.FRAME.test-clock", "Injectable/controllable clocks for tests", fo, tags="K-QUALITY-10 K-SYSTEMS-12")
    ed.cap("CORE.FRAME.phase-violations", "Detection of writes to data owned by another phase", fo,
           contrib=["robustness-fuzzing"], tags="K-QUALITY-8")
    ed.cap("CORE.FRAME.present-timeline", "Present timeline, pacing feedback & interposed presenters (C-PRESENT)", fo,
           contrib=["rhi-core", "reconstruction-upscaling", "xr-runtime", "platform-desktop"],
           tags="K-ARCH-10 K-SYSTEMS-8")
    ed.cap_set("CORE.FRAME.pipelining", name="Frame pipelining & frames in flight (incl. whether any dedicated "
               "render/RHI thread exists, by ADR)", tags="K-SYSTEMS-3 K-LEGACY-4")
    ed.skill_set(fo, consumes=["C-TASK", "C-CFG", "C-PAL"], tags="K-SYSTEMS-8")

    # ECS / object model / reflection
    ed.cap("CORE.ECS.bridges", "ECS ↔ subsystem bulk-sync adapters (physics, animation, audio, render, transforms)",
           "ecs-runtime", contrib=["physics-architect", "animation-architect", "audio-architect", "spatial-transforms"],
           tags="K-ARCH-3 K-SYSTEMS-10 K-LEGACY-1")
    ed.cap("CORE.ECS.snapshot", "World/component snapshot & restore, rollback-able component marking",
           "ecs-runtime", contrib=["prediction-rollback", "determinism-replay"], tags="K-NET-3 K-ARCH-4")
    ed.cap("CORE.ECS.safety", "Debug declared-vs-actual access checking & system-order ambiguity detection",
           "ecs-runtime", tags="K-QUALITY-8")
    ed.cap_set("CORE.ECS.scheduling", name="Lowering ECS systems into the frame access model", tags="K-SYSTEMS-3")
    ed.cap_set("CORE.OBJ.events", name="Events & messaging: deferred, batched delivery at declared consumption points "
               "by default", tags="K-LEGACY-11")
    ed.cap_set("CORE.OBJ.references", name="Reference kinds & explicit lifetime (owner + generational handles; no "
               "tracing GC over engine objects; script references are weak handles)", tags="K-LEGACY-14")
    ed.cap("CORE.REFL.static-default", "Static/compile-time reflection & resolved IDs on runtime paths; string lookup "
           "only at tool, script and serialization boundaries", "reflection-metadata", contrib=["ui-architect"],
           tags="K-LEGACY-13")
    ed.use("ecs-runtime", "C-SNAPSHOT", tags="K-ARCH-4")
    ed.use("ecs-runtime", "C-RELOAD?", tags="K-TOOLS-14")

    # types, math
    ed.cap("CORE.TYPES.codecs", "General-purpose compression codec library for non-package users", "containers-core-types",
           contrib=["package-formats-vfs"], tags="K-SYSTEMS-6")
    ed.cap("CORE.TYPES.crypto", "Vetted cryptographic primitives wrapper, CSPRNG, per-platform selection",
           "containers-core-types", contrib=["security-engineering"], tags="K-SYSTEMS-15 K-COMPLETE-3")
    ed.cap_set("CORE.TYPES.hashing", name="Non-cryptographic & stable content hashing with versioned algorithm/seed "
               "guarantees", tags="K-SYSTEMS-15")
    ed.cap_set("CORE.MATH.spmd", name="Wide-SIMD / SPMD kernels for fixed and scalable (VLA) vector ISAs, runtime ISA "
               "dispatch", tags="K-FUTURE-17")

    # determinism & replay: snapshot and replay contracts
    ed.contract_add("C-SNAPSHOT", 2, "determinism-replay", "Frame-state snapshot & resimulation",
                    "Snapshot/restore, resimulate N ticks, history ring, per-participant cost declaration.",
                    ["C-FRAME", "C-SER"], tags="K-ARCH-4 K-NET-3 K-SIM-6")
    ed.contract_add("C-REPLAY", 3, "determinism-replay", "Replay container & streams",
                    "Replay container, timeline, stream registration (input, replication, visual log, animation "
                    "debug, external/nondeterministic inputs) and cross-build versioning.",
                    ["C-SNAPSHOT", "C-SER"], tags="K-ARCH-9 K-SYSTEMS-2")
    ed.skill_set("determinism-replay", consumes=["C-MATH", "C-TASK", "C-SER@C-SNAPSHOT", "C-FRAME@C-SNAPSHOT"],
                 tags="K-SYSTEMS-2")
    ed.cap("XC.DET.snapshot", "Frame-state snapshot/restore/resimulate protocol (C-SNAPSHOT)", "determinism-replay",
           contrib=["ecs-runtime", "physics-architect", "animation-architect"], tags="K-ARCH-4")
    ed.cap("XC.DET.replay-format", "Replay container, timeline, stream registration & versioning (C-REPLAY)",
           "determinism-replay", contrib=["input-system", "replication", "visual-debugging-tools"], tags="K-ARCH-9")
    ed.cap("XC.DET.conformance", "Determinism conformance matrix (toolchain × ISA × platform × cores × schedule) as CI "
           "gate", "determinism-replay", contrib=["ci-cd-automation", "test-architect", "robustness-fuzzing"],
           tags="K-QUALITY-9 K-SIM-14")
    ed.cap("XC.DET.external-inputs", "Recording nondeterministic external results (services, model outputs) into "
           "replays", "determinism-replay", tags="K-FUTURE-5")
    ed.cap_set("INP.ACT.recording", name="Input stream capture for C-REPLAY", tags="K-ARCH-9")

    # hot reload
    ed.nonresp("hot-reload-iteration", [["Each system's own reload implementation (via C-RELOAD)", "owning-skill"],
                                        ["Build system", "build-system-toolchains"]], tags="K-TOOLS-14 K-ARCH-20")
    ed.use("hot-reload-iteration", "C-BUILD", tool=True, tags="K-TOOLS-14")


def resources(ed):
    rs = "resource-streaming-architect"
    ed.contract_set("C-RES", tags="K-SYSTEMS-5 K-SYSTEMS-6 K-PERF-5 K-PERF-6 K-LEGACY-11",
                    summary="Resource handles and explicit lifetime; load requests with priority/deadline; the staged "
                            "load pipeline (IO → decompress → fixup → GPU upload → publish) that every resource type "
                            "implements; pool registration, pressure signals and shrink-by-deadline requests; residency "
                            "notifications drained at a declared C-FRAME phase; fallbacks.")
    ed.contract_set("C-VFS", summary="Package format, mount layering (base, patch, DLC, mods, remote), chunk IDs, "
                    "integrity; codec per target constrained by available hardware decompressors.",
                    tags="K-FUTURE-11 K-PLATFORM-17")
    ed.cap("RES.MGMT.arbitration", "Cross-pool memory & IO-bandwidth arbitration (textures, geometry pages, shadow "
           "pages, audio, animation, world cells, BVH, ML weights); single physical budget on UMA; OS pressure signals",
           rs, contrib=["gpu-memory-resources", "memory-allocators", "performance-architect", "platform-architect"],
           tags="K-ARCH-6 K-SYSTEMS-5 K-PERF-6")
    ed.cap("RES.MGMT.gpu-requests", "Batched GPU-originated streaming requests (feedback buffers) & latency contract",
           rs, contrib=["render-graph-scheduling"], tags="K-PERF-6")
    ed.cap("RES.MGMT.pipeline", "Staged load pipeline, per-stage queues, staging-memory budget, batching, cancellation",
           rs, contrib=["async-io-storage", "gpu-memory-resources"], tags="K-SYSTEMS-6")
    ed.use(rs, "C-GPUMEM?", "C-FRAME", tags="K-SYSTEMS-5")
    ed.cap_set("RND.MEM.residency", name="Residency mechanism & budget reporting (policy in RES.MGMT.arbitration)",
               tags="K-SYSTEMS-5")
    ed.cap_set("RND.MEM.budget", name="GPU memory budget enforcement & defragmentation", tags="K-ARCH-6")
    io = "async-io-storage"
    ed.cap("RES.IO.cpu-decompress", "CPU decompression as an IO stage", io, tags="K-SYSTEMS-6")
    ed.cap("RES.IO.hw-decompress", "Fixed-function hardware decompression units", io,
           contrib=["platform-console", "package-formats-vfs"], tags="K-PLATFORM-17")
    ed.cap("RES.IO.remote", "HTTP/CDN IO backend with persistent content cache, prefetch & offline policy", io,
           mat="M", contrib=["platform-online-services"], tags="K-FUTURE-11")
    ed.cap_set("RES.IO.gpu-decompress", mat="E", tags="K-FUTURE-15")
    ed.cap_set("RES.IO.mmap", name="Memory-mapped IO restricted to prefetched/locked or tool-side use", tags="K-LEGACY-15")


def world(ed):
    wa, st = "world-architect", "spatial-transforms"
    ed.contract_set("C-SPATIAL", requires=["C-MATH", "C-ID"], tags="K-ARCH-3 K-SYSTEMS-10 K-LEGACY-1 K-PERF-4",
                    summary="Transform representation incl. large-world coordinates, hierarchy, generic spatial "
                            "queries, per-phase change sets (moved/attached/teleported) consumed by all spatial replicas.")
    ed.contract_add("C-VIEW", 2, st, "Views & view arbitration",
                    "View registry: view sources (gameplay camera, cinematic, editor, photo mode, XR pose) with "
                    "priority/blend stack and shake/FOV channels, per-local-player views, view origin for LWC "
                    "rebasing; derived listener and streaming-source signals for sinks.", ["C-SPATIAL"],
                    tags="K-ARCH-11 K-GAMEPLAY-4")
    ed.contract_add("C-SIGNIF", 2, wa, "Significance & simulation tiers",
                    "Per-entity significance, simulation tier and update budget, computed once from views/players "
                    "(all players on a server) and consumed by each domain's LOD policy.", ["C-VIEW"], tags="K-SIM-4")
    ed.contract_add("C-ENV", 3, wa, "Environment queries",
                    "Environment query service: ground height/surface type, water surface/volume (height, velocity, "
                    "depth, body id), wind field, weather parameters, deformation deltas; implemented by terrain, "
                    "water, atmosphere and voxel providers; headless-capable.", ["C-SPATIAL"],
                    tags="K-ARCH-1 K-SIM-9 K-SIM-13")
    ed.contract_set("C-WORLD", tags="K-PERF-5",
                    summary="Cells, streaming sources, world data activation in budgeted, time-sliced batches with "
                            "bulk registration.")
    ed.skill_set(wa, consumes=["C-SPATIAL", "C-RES", "C-ECS?", "C-VIEW", "C-FRAME"], tags="K-ARCH-3")
    ed.skill_set(st, consumes=["C-MATH", "C-ECS?", "C-TASK", "C-ID"], tags="K-ARCH-3")
    ed.cap("WLD.SPACE.views", "View registry & arbitration, view origin, listener/streaming-source derivation (C-VIEW)",
           st, contrib=["gameplay-systems-toolkit", "cinematics-sequencer", "xr-runtime", "render-architect"],
           tags="K-ARCH-11 K-GAMEPLAY-4")
    ed.cap("WLD.SPACE.change-sets", "Per-phase transform change sets published once to all spatial replicas", st,
           contrib=["ecs-runtime", "physics-architect"], tags="K-PERF-4")
    ed.cap("WLD.PART.activation", "Budgeted, time-sliced cell activation with bulk registration", wa,
           contrib=["ecs-runtime", "physics-architect", "gpu-driven-pipeline", "navigation-pathfinding"], tags="K-PERF-5")
    ed.cap("WLD.PART.cook", "World → streaming-cell cook step", wa, contrib=["ecs-runtime", "world-data-model"],
           tags="K-ARCH-19")
    ed.cap("WLD.PART.sim-tiers", "Off-bubble simulation tiers (abstract/statistical sim, promotion/demotion, remote "
           "server regions)", wa, contrib=["crowd-simulation", "dedicated-server"], tags="K-SIM-4")
    ed.cap_set("WLD.PART.sim-lod", name="Significance & simulation-LOD signal (C-SIGNIF)", tags="K-SIM-4")
    ed.cap("WLD.MODEL.planetary", "Planetary/spherical worlds & geodetic frames", wa, mat="M",
           contrib=["spatial-transforms", "terrain", "atmosphere-weather"], tags="K-COMPLETE-15")
    ed.cap("WLD.ENV.queries", "Environment query service (C-ENV)", wa,
           contrib=["terrain", "water-ocean", "atmosphere-weather"], tags="K-ARCH-1 K-SIM-9")
    ed.cap("WLD.ENV.terrain-planetary", "Spherical terrain LOD", "terrain", mat="M", tags="K-COMPLETE-15")
    ed.cap_set("WLD.ENV.wind", name="Vegetation wind response & interaction", tags="K-SIM-13")
    ed.cap("WLD.ENV.wind-field", "Global wind field state & queries (via C-ENV)", "atmosphere-weather",
           contrib=["vegetation-foliage", "cloth-deformables", "vfx-particles"], tags="K-SIM-13")
    ed.cap_set("WLD.ENV.buoyancy", name="Water query service (C-ENV provider)", tags="K-SIM-9")
    ed.cap("WLD.ENV.water-interaction", "Local interactive water surface simulation", "water-ocean",
           contrib=["fluid-simulation"], tags="K-SIM-9")
    for s_ in ("terrain", "water-ocean", "atmosphere-weather"):
        ed.skill(s_)["implements"] = ["C-ENV"]
    # environment skills: present in all 3D tiers, render deps optional so they close headless
    ed.skill_set("terrain", profiles=["lite3d", "std3d"],
                 consumes=["C-WORLD?", "C-RSCENE?", "C-PHYS?", "C-RES", "C-MATIF?", "C-ENV", "C-INSTANCES?", "C-VT?"],
                 tags="K-RENDER-6 K-ARCH-1")
    ed.skill_set("water-ocean", profiles=["lite3d", "std3d"],
                 consumes=["C-WORLD?", "C-RSCENE?", "C-RG?", "C-ENV", "C-LIGHT?", "C-GI?", "C-TEMPORAL?"],
                 tags="K-RENDER-6 K-SIM-9 K-RENDER-1 K-RENDER-2")
    ed.skill_set("vegetation-foliage", profiles=["lite3d", "std3d"],
                 consumes=["C-WORLD?", "C-RSCENE?", "C-RES", "C-ENV?", "C-INSTANCES?", "C-TEMPORAL?"],
                 tags="K-RENDER-6 K-PERF-3 K-RENDER-2")
    ed.skill_set("atmosphere-weather",
                 consumes=["C-RSCENE?", "C-RG?", "C-FRAME", "C-ENV", "C-LIGHT?", "C-TEMPORAL?"], targets=["client", "headless-client", "server", "tools"],
                 tags="K-RENDER-1 K-SIM-13")
    for cid in ("WLD.ENV.terrain-render", "WLD.ENV.terrain-materials"):
        pass
    ed.cap_set("WLD.PART.server", add_contrib=["network-architect"], tags="K-NET-8")
    ed.use("procedural-generation", "C-ML?", tags="K-FUTURE-1")
    ed.use("procedural-generation", "C-INSTANCES?", tags="K-PERF-3")

    # voxel / sandbox worlds
    ed.skill_add(id="voxel-worlds", name="Voxel & Buildable Worlds", tier="expert", parent=wa, profiles=["sandbox"],
                 kind="runtime", targets=["client", "headless-client", "server", "tools"], workstream="world",
                 purpose="Chunked voxel/block worlds end to end: sparse storage and compression, meshing and remeshing "
                         "on edit, runtime edit replication and persistence hand-off, block light propagation.",
                 non_responsibilities=[["Player construction gameplay (snapping, structural integrity)", "gameplay-systems-toolkit"],
                                       ["Heightfield terrain", "terrain"], ["Replication mechanics", "replication"]],
                 consumes=["C-WORLD", "C-ENV", "C-SPATIAL", "C-RES", "C-RSCENE?", "C-PHYS?", "C-REP?", "C-SAVE?"],
                 implements=["C-ENV"],
                 expertise=["sparse voxel structures", "surface extraction (greedy, surface nets, dual contouring)", "edit replication"],
                 tags="K-COMPLETE-16")
    ed.area("WLD.VOX", "Voxel worlds", tags="K-COMPLETE-16")
    ed.cap("WLD.VOX.storage", "Chunked/sparse voxel storage & compression", "voxel-worlds", tags="K-COMPLETE-16")
    ed.cap("WLD.VOX.meshing", "Voxel meshing & remeshing on edit", "voxel-worlds", tags="K-COMPLETE-16")
    ed.cap("WLD.VOX.edits", "Runtime world edits with replication & persistence hand-off", "voxel-worlds",
           contrib=["replication", "persistence-save"], tags="K-COMPLETE-16")
    ed.cap("WLD.VOX.lighting", "Block light propagation", "voxel-worlds", tags="K-COMPLETE-16")


def apply(ed):
    schema(ed)
    foundation(ed)
    resources(ed)
    world(ed)
