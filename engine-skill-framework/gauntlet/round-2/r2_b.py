"""Round-2 revision, part B: K-SYSTEMS and K-PERF findings (concurrency, frame, memory, IO, performance organisation)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _legacy(ed, lid, tags, **kw):
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == lid:
            p.update(kw)
            ed.note(tags, f"legacy {lid}: " + ", ".join(kw))
            return
    raise KeyError(lid)


def apply(ed):
    # ---- frame model: no phase barriers by default; single thread-inventory authority; single scheduler
    t = "K-SYSTEMS-1 K-PERF-2"
    ed.cap_set("CORE.FRAME.phases", name="Tick phases & the minimal set of named global sync points (each justified by "
               "ADR); ordering otherwise derived from C-FRAME access declarations", tags=t)
    ed.nonresp_add("gpu-platform-architect", "Thread inventory (which threads exist)", "job-system-task-graph", tags=t)
    s = ed.skill("render-architect")
    ed.skill_set("render-architect", purpose=s["purpose"].replace(", render threading", ""), tags=t)
    ed.nonresp_add("render-architect", "Render threading / command-recording model", "gpu-platform-architect", tags=t)
    ed.cap_set("CORE.JOBS.thread-model", name="Engine thread inventory (sole authority on which threads exist), core "
               "reservation, OS priority/QoS mapping, real-time thread rules, middleware pool adapters, oversubscription "
               "detection", tags=t)
    _legacy(ed, "L03", t, justification_owner="frame-orchestration",
            default_stance="Render work as tasks in overlapping task-graph frames; dedicated threads only by ADR "
                           "(thread inventory in CORE.JOBS.thread-model)")

    t = "K-SYSTEMS-4"
    ed.cap_set("CORE.FRAME.access-model", name="Unified access declarations for all phase work (ECS systems and service "
               "resources); the single frame scheduler that compiles the per-frame graph and resolves conflicts across "
               "and inside phases", tags=t)
    ed.cap_set("CORE.ECS.scheduling", name="Lowering ECS systems into the frame access model (no separate ECS "
               "scheduler)", tags=t)
    s = ed.skill("ecs-runtime")
    ed.skill_set("ecs-runtime", purpose=s["purpose"].replace("system scheduling with access-conflict analysis",
                 "lowering systems to frame access declarations, ECS-specific ambiguity diagnostics"), tags=t)
    s = ed.skill("frame-orchestration")
    ed.nonresp("frame-orchestration", [x for x in s["non_responsibilities"] if x[0] != "System ordering inside a phase"]
               + [["ECS query/storage semantics", "ecs-runtime"]], tags=t)

    # ---- explicit frame and channel dependencies of multi-rate runtime skills
    t = "K-SYSTEMS-3"
    for sid in ("audio-architect", "spatial-transforms", "scripting-runtime", "navigation-pathfinding",
                "ai-behavior-perception", "ui-architect", "ml-inference-runtime", "prediction-rollback"):
        ed.use(sid, "C-FRAME", tags=t)
    for sid in ("audio-architect", "physics-architect", "animation-architect", "replication",
                "ai-behavior-perception", "input-system"):
        ed.use(sid, "C-FLOW", tags=t)

    # ---- lifetime / retirement: one implementation, available to every runtime module
    t = "K-SYSTEMS-5 K-SYSTEMS-6"
    ed.cap_set("CORE.LIFE.ownership-model", name="Engine-wide ownership & cross-thread reference rules (policy; "
               "retirement service implemented in CORE.CONC.retirement)", tags=t)
    ed.cap("CORE.CONC.retirement", "Retirement service (C-LIFETIME): completion-token, fence and epoch retire queues "
           "shared with safe memory reclamation", "concurrency-primitives", contrib=["core-runtime-architect",
           "rhi-core", "gpu-memory-resources"], tags=t)
    ed.contract_set("C-LIFETIME", owner="concurrency-primitives", universal="runtime", tags=t)
    _legacy(ed, "L15", t, justification_owner="concurrency-primitives")
    s = ed.skill("concurrency-primitives")
    ed.skill_set("concurrency-primitives", purpose=s["purpose"].replace("safe memory reclamation",
                 "safe memory reclamation and the engine retirement service (C-LIFETIME)"), tags=t)

    t = "K-SYSTEMS-7"
    for cid in ("C-MOD", "C-CFG"):
        ed.contract_set(cid, universal="runtime", tags=t)

    # ---- cross-pool registration of GPU pools (arbiter exists as RES.MGMT.arbitration)
    t = "K-SYSTEMS-2"
    for sid in ("ray-tracing-infrastructure", "geometry-pipeline", "render-graph-scheduling", "shader-system"):
        ed.use(sid, "C-RES", tags=t)
    ed.cap_set("CORE.MEM.uma", name="Unified-memory CPU/GPU accounting, reported into RES.MGMT.arbitration (no "
               "independent arbitration)", tags=t)
    _append(ed, "C-RES", "every CPU/GPU pool registers with the arbiter and never sizes itself.", t)

    # ---- GPU half of the async path + per-frame transfer arbitration
    t = "K-SYSTEMS-9 K-PERF-6"
    ed.cap("RND.GRAPH.external-work", "External GPU work & transfer arbitration: streaming uploads, GPU decompression, "
           "scene deltas, AS builds and VT pages as registered producers with priority/deadline/byte budgets per tier; "
           "copy/async-queue placement; import of externally written resources, queue-ownership transfer & first-use "
           "acquire", "render-graph-scheduling", contrib=["async-io-storage", "gpu-memory-resources",
           "ray-tracing-infrastructure", "resource-streaming-architect"], tags=t)
    ed.use("render-graph-scheduling", "C-IO?", tags=t)
    _append(ed, "C-IO", "GPU decompression is declared as external work items executed as render-graph nodes where no "
            "dedicated decompression queue exists.", t)
    ed.cap_set("RND.MEM.upload", name="Upload, staging & readback rings (readback latency contract in "
               "RND.GRAPH.readback)", tags=t)
    _append(ed, "C-BUDGET", "transfer bytes per frame and async-queue occupancy per tier.", t)

    # ---- host-driven loops and degenerate schedulers
    t = "K-SYSTEMS-10"
    ed.cap("CORE.FRAME.host-loop", "Host-driven frame entry (requestAnimationFrame, display link, Choreographer, "
           "xrWaitFrame) with a non-blocking cooperative frame step", "frame-orchestration",
           contrib=["platform-web", "platform-mobile", "xr-runtime"], tags=t)
    ed.cap("CORE.JOBS.degenerate", "Production execution with 0–2 workers: inline/cooperative execution, no main-thread "
           "blocking waits, yield-to-host", "job-system-task-graph", contrib=["platform-web"], tags=t)

    # ---- work-graph programs are experimental; radar class must match maturity
    t = "K-SYSTEMS-11 K-PERF-4"
    ed.cap_set("RND.RHI.gpu-work", name="GPU-generated work primitives (indirect, device-generated commands, backing "
               "memory)", tags=t)
    ed.cap("RND.RHI.work-graph-programs", "Work-graph programs & mesh nodes (fallback: indirect dispatch)", "rhi-core",
           "X", contrib=["render-graph-scheduling"], profiles=["aaa"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.GRAPH.work-graphs" in e.get("capabilities", []):
            e["capabilities"].append("RND.RHI.work-graph-programs")
    ed.cap_set("RND.ARCH.multiview", name="Multi-view rendering: split-screen, PiP, captures, stereo/multiview",
               tags=t)
    ed.cap("RND.ARCH.multiview-nview", "N-view outputs (autostereo / light-field displays)", "render-architect", "M",
           contrib=["xr-runtime"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.ARCH.multiview" in e.get("capabilities", []):
            e["capabilities"] = ["RND.ARCH.multiview-nview" if x == "RND.ARCH.multiview" else x
                                 for x in e["capabilities"]]
    ed.note(t, "check.py: a radar entry's class must equal the maturity of every capability it lists")

    # ---- codecs, lifecycle quiesce
    t = "K-SYSTEMS-12"
    ed.cap_set("CORE.TYPES.codecs", name="Compression codec library for all users (package and non-package): "
               "vetted zstd/LZ4/Kraken-class decoders, SIMD tuning, fuzz registration", tags=t)
    ed.cap_set("RES.PKG.compression", name="Compression codec selection per package (implementations in "
               "CORE.TYPES.codecs)", tags=t)
    ed.cap_set("RES.IO.cpu-decompress", name="CPU decompression as an IO stage (scheduling only; codecs in "
               "CORE.TYPES.codecs)", tags=t)

    t = "K-SYSTEMS-13"
    ed.cap_set("PLAT.PAL.lifecycle", add_contrib=["async-io-storage", "rhi-core", "frame-orchestration",
               "network-transport"], tags=t)
    _append(ed, "C-PAL", "suspend/resume quiesce protocol (outstanding IO, GPU idle/device recreate, connection loss) "
            "and time-discontinuity events.", t)

    # ---- governor needs shipping-grade L2 signals
    t = "K-PERF-5"
    ed.contract_add("C-GOVERN", 2, "runtime-scalability", "Runtime governor",
                    "Governor control inputs from shipping-grade signals (GPU frame time, present feedback, pool "
                    "pressure, thermal/power) independent of C-INSTR; actuator commands through C-SCALE; decision log.",
                    requires=["C-SCALE", "C-PRESENT", "C-RES"], conformance=True, tags=t)
    ed.use("runtime-scalability", "C-PRESENT@C-GOVERN", "C-RES@C-GOVERN", "C-GPUMEM?@C-GOVERN", "C-FRAME@C-GOVERN",
           tags=t)
    ed.use("visual-debugging-tools", "C-GOVERN?", tags=t)
    ed.cap_set("CORE.SCALE.governor", name="Closed-loop runtime performance/power governor (C-GOVERN module; "
               "shipping-grade inputs)", tags=t)
    _append(ed, "C-PRESENT", "shipping-grade GPU-frame-time and present-feedback signals that do not depend on C-INSTR.", t)
    _append(ed, "C-RHI", "shipping-grade GPU timestamp signal for the governor.", t)

    # ---- in-process measurement hooks live in a built skill
    t = "K-PERF-7"
    ed.cap("OBS.LOG.bench-runtime", "In-process benchmark runner, capture triggers & memory-snapshot hooks (dev/profile "
           "builds on every target; registered via C-BENCH)", "observability-telemetry",
           contrib=["perf-benchmarking", "memory-performance", "gpu-performance", "loading-streaming-performance"],
           tags=t)
    ed.use("memory-performance", "C-MEM", "C-RES", "C-GPUMEM?", "C-INSTR", "C-BUDGET", tags=t)
    _append(ed, "C-BENCH", "runs through the in-process runner in OBS.LOG.bench-runtime, present in every "
            "configuration.", t)

    # ---- replication cost obligations
    t = "K-PERF-8"
    ed.cap("NET.REP.change-tracking", "Change-driven replication: dirty tracking at the write site, per-object "
           "serialized deltas shared across connections, batch-parallel filtering/prioritization; cost O(changes + "
           "relevant set per connection)", "replication", tags=t)
    _append(ed, "C-REP", "producers mark dirty state; no per-connection full-state comparison.", t)
    _append(ed, "C-SIGNIF", "significance/relevancy computed over a spatial bucketing (C-SPATIAL index) with declared "
            "cost per player.", t)
    ed.cap_set("PRF.METH.asymptotics", name="Declared asymptotic cost per world-scale dimension (incl. replicated "
               "entities and connections) for every runtime skill", tags=t)

    # ---- independent online performance analysis
    t = "K-PERF-9"
    ed.skill_add(tags=t, id="online-performance", name="Online & Server Performance", tier="expert",
                 parent="performance-architect", profiles=["online"], kind="process", targets=[],
                 workstream="performance",
                 purpose="Independent analysis of online cost: bandwidth per player/entity/property against network "
                         "budgets, server tick cost and instance density, cost per concurrent user, and load-test "
                         "analysis reconciled with the capacity model; routes findings via C-PERF.",
                 non_responsibilities=[["Network profiler instrument", "replication"],
                                       ["Server implementation", "dedicated-server"],
                                       ["Load-test execution", "functional-automation-soak"]],
                 expertise=["network bandwidth analysis", "server capacity planning", "load-test statistics"],
                 consumes=["C-INSTR", "C-BUDGET", "C-NET", "C-REP"])
    ed.area("PRF.NET", "Online & server performance", tags=t)
    ed.cap("PRF.NET.bandwidth", "Per-connection/entity/property bandwidth analysis against NET.ARCH.budgets",
           "online-performance", contrib=["replication"], tags=t)
    ed.cap("PRF.NET.server-density", "Server tick cost, instances per host and cost per CCU against server hardware "
           "classes", "online-performance", contrib=["dedicated-server"], tags=t)
    ed.cap("PRF.NET.load-analysis", "Load-test analysis & capacity-model reconciliation with PRF.METH.model",
           "online-performance", contrib=["functional-automation-soak", "performance-architect"], tags=t)

    # ---- performance exit criteria per milestone (contract freezing handled in r2_z)
    t = "K-PERF-10"
    perf_exit = {
        "M0": " Perf: trace capture and the C-BENCH runner on the skeleton; C-BUDGET v0 for indie-2d tiers; CI perf "
              "lane (frame time, startup, memory).",
        "M1": " Perf: indie-2d reference game within budget on min-spec PC and mobile tiers; hitch gate active.",
        "M2": " Perf: std3d and lite3d budgets per tier on PC, console and mobile; PSO first-encounter hitch gate; "
              "governor closed-loop test.",
        "M3": " Perf: arbiter under synthetic pressure without oscillation or starvation (A14); scale-content stress "
              "worlds within declared asymptotics.",
        "M4": " Perf: bandwidth per player and server density budgets met under load test.",
    }
    for m in ed.doc["milestone"]["milestones"]:
        if m["id"] in perf_exit:
            m["exit"] += perf_exit[m["id"]]
    ed.note(t, "performance exit criteria added to M0–M4")

    t = "K-PERF-11"
    ed.cap_set("PRF.LOAD.editor", name="Editor startup, asset-open, PIE-start & large-world viewport analysis and "
               "hitch attribution (budgets in PRF.METH.pipeline-budgets)", tags=t)

    t = "K-PERF-12"
    ed.cap_set("BLD.SYS.configs", name="Build configurations (debug, development, test, profile = shipping "
               "optimization with C-INSTR on, shipping)", add_contrib=["perf-benchmarking"], tags=t)
    _append(ed, "C-INSTR", "declared overhead per zone/counter class, overhead budget in C-BUDGET.", t)
    _append(ed, "C-BENCH", "gates run on the profile build configuration.", t)

    t = "K-PERF-13"
    ed.cap("PRF.LOAD.pacing-latency", "Frame pacing & end-to-end latency analysis (percentile frame times, present "
           "jitter, input-to-photon by hardware/marker measurement) with a pacing gate",
           "loading-streaming-performance", contrib=["frame-orchestration", "input-system",
           "reconstruction-upscaling"], tags=t)
    s = ed.skill("loading-streaming-performance")
    ed.skill_set("loading-streaming-performance", name="Loading, Hitch & Pacing Performance",
                 purpose=s["purpose"].rstrip(".") + "; steady-state frame pacing and input-to-photon latency "
                 "analysis.", tags=t)

    t = "K-PERF-14"
    ed.cap("RES.PKG.ordering", "Access-order package layout from load/stream traces (co-location, request "
           "coalescing), validated by PRF.LOAD.load-time", "package-formats-vfs",
           contrib=["loading-streaming-performance", "content-pipeline-architect"], tags=t)
